from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import traceback
from pathlib import Path

import pandas as pd

from app.controllers.base_controller import BaseController
from app.models.patient_model import IntegralClinicalData
from app.utils.event_bus import AppEvent
from app.utils.helpers import (
    InvalidFileError,
    find_rscript,
    format_percent,
    validate_file_path,
)
from app.utils.integral_inference import run_inference_pipeline
from app.utils.validators import BatchIntegralRowParser, ParseError

SEX_OPTIONS = {
    "Male": 0,
    "Female": 1,
}


class IntegralController(BaseController):
    def __init__(self, root, bus):
        super().__init__(root, bus)

        self._pending = None
        self._running = False
        self._batch_active = False
        self._batch_cancel = False

    # ─────────────────────────────── RUN ───────────────────────────────

    def run(self, data: IntegralClinicalData) -> None:
        self._pending = data
        self._set_state("running")

        self._log("Running INTEGRAL model (R subprocess)...")
        self._progress(0.3)

        threading.Thread(target=self._infer, daemon=True).start()

    def run_batch(self, csv_path: str) -> None:
        thread = threading.Thread(
            target=self._run_batch_worker, args=(csv_path,), daemon=True
        )
        thread.start()

    def cancel_batch(self):
        self._batch_cancel = True
        self._log("Cancelling batch...", "WARNING")

    # ─────────────────────────────── INFERENCE ─────────────────────────

    def _infer(self) -> None:
        """
        Run INTEGRAL-Radiomics prediction using R library and parse results.
        """
        try:
            payload = self._prepare_payload(self._pending)

            # Build temporary CSV for R
            with tempfile.NamedTemporaryFile(
                suffix=".csv",
                delete=False,
            ) as f:
                tmp_csv = Path(f.name)

            df = pd.DataFrame(
                [
                    {
                        "image": payload["image"],
                        "mask": payload["mask"],
                        "age": int(payload["age"]),
                        "sex": 1 if payload["female"] else 0,
                        "bmi": float(payload["bmi"]),
                        "fhlc": int(payload["fhlc"]),
                        "copdemph": int(payload["copdemph"]),
                        "formersmk": int(payload["formersmk"]),
                        "duration": int(payload["duration"]),
                        "cigday": int(payload["cigday"]),
                        "quittime": int(payload["quittime"]),
                    }
                ]
            )
            df.to_csv(tmp_csv, index=False)

            # R code to predict and output JSON
            r_code = f"""
            .libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
            library(integralrad)
            library(jsonlite)

            preds <- predict_integral_radiomics("{tmp_csv}")
            cat(toJSON(preds, dataframe="rows"))
            """

            # jsonlite::toJSON(result) pred_benign and pred_malignant

            self._log("Calling integral-radiomics R library via Rscript...")
            self._log(
                "Temporary CSV created",
                data={
                    "path": str(tmp_csv),
                    "size_bytes": tmp_csv.stat().st_size,
                },
            )
            self._log(
                "CSV preview",
                data={
                    "rows": len(df),
                    "columns": list(df.columns),
                    "preview": df.head().to_dict(orient="records"),
                },
            )

            env = os.environ.copy()
            env["R_LIBS_USER"] = str(Path.home() / ".pulmorisk" / "r" / "library")

            rscript_path = find_rscript()

            # Run R subprocess
            result = subprocess.run(
                [rscript_path, "-e", r_code],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            self._log(f"Raw R stdout:\n{result.stdout}")
            self._log(f"Raw R stderr:\n{result.stderr}")

            stdout = result.stdout.strip()
            if not stdout:
                self._error("integral-radiomics returned empty output")
                self._set_state("error")
                return

            # Parse JSON
            preds = json.loads(stdout)
            row = preds[0]  # single row expected

            self._log(f"Prediction result: {row}")

            # Find probability column
            probability = None

            probability = float(row["pred_malignant"])

            if probability is None:
                raise RuntimeError(
                    f"Could not locate probability column in output: {list(row.keys())}"
                )

            self._progress(0.8)

            self._on_complete(probability)

        except subprocess.CalledProcessError as e:
            self._error(f"integral-radiomics process failed: {e.stderr}")
            self._set_state("error")

        except Exception as exc:
            self._error(f"Inference error: {exc}")
            self._set_state("error")

        finally:
            if tmp_csv.exists():
                tmp_csv.unlink()

    # ─────────────────────────────── DATA PREP ─────────────────────────

    def _prepare_payload(self, data: IntegralClinicalData) -> dict:
        return {
            "age": data.age,
            "female": data.female,
            "fhlc": data.fhlc,
            "copdemph": data.copdemph,
            "formersmk": data.formersmk,
            "duration": data.duration,
            "cigday": data.cigday,
            "quittime": data.quittime,
            "bmi": data.bmi,
            "image": data.image_file,
            "mask": data.mask_file,
        }

    # ─────────────────────────────── RESULT ─────────────────────────────

    def _on_complete(self, probability: float) -> None:
        self._log(
            f"Prediction → lung cancer probability={format_percent(probability)}",
            "SUCCESS",
        )

        self._progress(1.0)

        self._emit(
            AppEvent(
                type="radiomics_result",
                data={
                    "probability": probability,
                },
            )
        )

        self._set_state("idle")

    def _row_to_patient(self, row) -> IntegralClinicalData:
        try:
            parsed = BatchIntegralRowParser.parse(dict(row))
        except ParseError as exc:
            # surface the exact column that failed
            raise ValueError(f"Column '{exc.field}': {exc.message}") from exc

        # ModelValidationError (out-of-range etc.) propagates naturally —
        # the batch loop already catches Exception and logs it per-row.
        return IntegralClinicalData(**parsed)

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
                        [
                            {
                                "pred_benign": None,
                                "pred_malignant": None,
                                "error": "cancelled",
                            }
                            for _ in range(remaining)
                        ]
                    )
                    break

                try:
                    patient = self._row_to_patient(row)

                    try:
                        validate_file_path(Path(patient.image_file), "image_file")
                        validate_file_path(Path(patient.mask_file), "mask_file")
                    except InvalidFileError as e:
                        self._warn(
                            f"Row {i + 1} skipped: {e.field_name} invalid ({e.reason})"
                        )
                        results.append(
                            {
                                "pred_benign": None,
                                "pred_malignant": None,
                                "error": f"{e.field_name} invalid ({e.reason})",
                            }
                        )
                        continue

                    self._log(f"Running inference on row {i + 1} for patient: ")

                    prediction = run_inference_pipeline(patient)

                    results.append(
                        {
                            "pred_benign": prediction[0],
                            "pred_malignant": prediction[1],
                            "error": None,
                        }
                    )

                except Exception as e:
                    self._error(f"Row {i + 1} failed: {e}")
                    self._error(traceback.format_exc())
                    results.append(
                        {
                            "pred_benign": None,
                            "pred_malignant": None,
                            "error": str(e),
                        }
                    )
                    break

            df["pred_benign"] = [r["pred_benign"] for r in results]
            df["pred_malignant"] = [r["pred_malignant"] for r in results]
            df["error"] = [r["error"] for r in results]

            output_path = str(Path(csv_path).with_suffix(""))
            output_path = output_path + "_scored.csv"

            df.to_csv(output_path, index=False)

            self._batch_active = False
            self._set_state("idle")

            self._emit(
                AppEvent(type="radiomics_result", data={"output_path": output_path})
            )
        except Exception as e:
            self._error("Batch crashed completely")
            self._error(str(e))
            self._error(traceback.format_exc())
