from __future__ import annotations

import json
import os
import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path

import certifi
import pandas as pd

from app.controllers.base_controller import BaseController
from app.models.patient_model import SybilInputData
from app.utils.event_bus import AppEvent, EventBus
from app.utils.helpers import validate_ct_path
from app.utils.sybil_epi import calculate_sybil_epi_score, epi_input_from_patient_data
from app.utils.sybil_inference import run_sybil_pipeline
from app.utils.validators import BatchSybilRowParser, ParseError

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()


class SybilController(BaseController):
    def __init__(self, root, bus: EventBus):
        super().__init__(root, bus)
        self._model = None
        self._pending = None
        self._infer_active = False
        self._batch_active = False
        self._batch_cancel = False

    def load_model(self):
        self._log("Loading Sybil model...")

        def _task():
            try:
                import torch  # noqa: PLC0415

                torch.set_num_threads(2)
                torch.set_num_interop_threads(1)
                # Force CPU — prevents torch from looking for CUDA at runtime
                os.environ["CUDA_VISIBLE_DEVICES"] = ""
                # lazy import — runs off main thread so GIL contention
                # during import doesn't block the UI
                from sybil import Sybil  # noqa: PLC0415

                self._model = Sybil("sybil_ensemble")
                self._log("Sybil model ready.", "SUCCESS")
                self._emit(AppEvent(type="model_ready"))
            except Exception as exc:
                self._error(f"Model load failed: {exc}")
                self._emit(AppEvent(type="model_error", message=str(exc)))

        threading.Thread(target=_task, daemon=True).start()

    def run(self, data) -> None:
        if data.six_year_risk:
            self._pending = data
            self._set_state("running")
            self._log("Calculating sybil epi score")
            self._progress(0.2)
            threading.Thread(
                target=self._on_complete,
                args=([0, 0, 0, 0, 0, data.six_year_risk],),
                daemon=True,
            ).start()
        else:
            if not self._model:
                self._error("Model not loaded.")
                return

            path = Path(data.ct_scan_dir)
            if not path.is_dir():
                self._error("Invalid CT folder.")
                return

            dicoms = sorted(path.glob("*.*"))
            if not dicoms:
                self._error("No files found.")
                return

            self._pending = data
            self._set_state("running_single")
            self._log(f"Running Sybil on {len(dicoms)} slices…")
            self._progress(0.2)

            self._infer_active = True
            threading.Thread(
                target=self._infer,
                args=([str(f) for f in dicoms],),
                daemon=True,
            ).start()
            threading.Thread(target=self._heartbeat, daemon=True).start()

    def run_batch(self, csv_path: str) -> None:
        thread = threading.Thread(
            target=self._run_batch_worker, args=(csv_path,), daemon=True
        )
        thread.start()

    def cancel_batch(self):
        self._batch_cancel = True
        self._log("Cancelling batch...", "WARNING")

    def _heartbeat(self) -> None:
        elapsed = 0
        interval = 8
        while self._infer_active:
            time.sleep(interval)
            if self._infer_active:
                elapsed += interval
                mins, secs = divmod(elapsed, 60)
                label = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
                self._log(f"CT inference in progress… ({label} elapsed)")

    def _infer(self, paths: list[str]) -> None:
        try:
            from sybil.serie import Serie  # lazy import  # noqa: PLC0415

            serie = Serie(paths)
            prediction = self._model.predict([serie])
            scores = prediction.scores[0]
            self._on_complete(scores)
        except Exception as exc:
            self._infer_active = False
            self._error(f"Inference failed: {exc}")

    def _on_complete(self, yearly) -> None:
        self._infer_active = False
        try:
            self._log(f"Sybil Scores {yearly}")
            self._log(json.dumps(asdict(self._pending)))
            epi_in = epi_input_from_patient_data(self._pending, yearly[5])
            epi = calculate_sybil_epi_score(epi_in)
        except Exception as exc:
            self._error(f"EPI scoring failed: {exc}")
            return

        self._progress(1.0)
        self._log(f"Final 6-year risk: {epi:.1%}", "SUCCESS")
        self._emit(
            AppEvent(
                type="sybil_result",
                data={"yearly": list(yearly), "epi": epi},
            )
        )
        self._set_state("idle")

    def _row_to_patient(self, row) -> SybilInputData:
        try:
            parsed = BatchSybilRowParser.parse(dict(row))
        except ParseError as exc:
            # surface the exact column that failed
            raise ValueError(f"Column '{exc.field}': {exc.message}") from exc

        # ModelValidationError (out-of-range etc.) propagates naturally —
        # the batch loop already catches Exception and logs it per-row.
        return SybilInputData(**parsed)

    def _run_batch_worker(self, csv_path: str) -> None:
        try:
            self._batch_active = True
            self._batch_cancel = False

            df = pd.read_csv(csv_path)
            results = []

            total = len(df)

            self._set_state("running_batch")
            self._log(f"Starting batch run: {total} patients")

            for i, row in df.iterrows():
                self._emit(
                    AppEvent(
                        type="batch_progress",
                        data={
                            "current": i + 1,
                            "total": total,
                        },
                    )
                )
                self._log(f"Completed {i}/{total}")

                if self._batch_cancel:
                    self._log("Batch cancelled by user", "WARNING")

                    remaining = total - len(results)

                    results.extend(
                        [{"epi": None, "error": "cancelled"} for _ in range(remaining)]
                    )
                    break

                try:
                    patient = self._row_to_patient(row)

                    path = Path(patient.ct_scan_dir)

                    ok, msg = validate_ct_path(path)
                    if not ok:
                        self._warn(f"Row {i + 1} skipped: {msg}")
                        results.append(
                            {
                                "epi": None,
                                "error": msg,
                            }
                        )
                        continue

                    self._log(f"Running inference on row {i + 1} for patient: ")
                    self._log(json.dumps(asdict(patient)))

                    epi = run_sybil_pipeline(self._model, patient)

                    results.append(
                        {
                            "epi": epi,
                            "error": None,
                        }
                    )

                except Exception as e:
                    self._error(f"Row {i + 1} failed: {e}")
                    self._error(traceback.format_exc())
                    results.append(
                        {
                            "epi": None,
                            "error": str(e),
                        }
                    )

            df["epi_risk"] = [r["epi"] for r in results]
            df["error"] = [r["error"] for r in results]

            output_path = str(Path(csv_path).with_suffix(""))
            output_path = output_path + "_scored.csv"

            df.to_csv(output_path, index=False)

            self._batch_active = False
            self._set_state("idle")

            self._emit(AppEvent(type="sybil_result", data={"output_path": output_path}))
        except Exception as e:
            self._error("Batch crashed completely")
            self._error(str(e))
            self._error(traceback.format_exc())
