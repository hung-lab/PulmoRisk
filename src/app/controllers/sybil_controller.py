from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from pathlib import Path

from sybil import Sybil
from sybil.serie import Serie

from app.controllers.base_controller import BaseController
from app.utils.event_bus import AppEvent, EventBus
from app.utils.sybil_epi import calculate_sybil_epi_score, epi_input_from_patient_data


class SybilController(BaseController):
    def __init__(self, root, bus: EventBus):
        super().__init__(root, bus)
        self._model = None
        self._pending = None
        self._infer_active = False  # heartbeat guard

    def load_model(self):
        self._log("Loading Sybil model...")

        def _task():
            try:
                self._model = Sybil("sybil_ensemble")
                self._log("Sybil model ready.", "SUCCESS")
                self._emit(AppEvent(type="model_ready"))
            except Exception as exc:
                self._error(f"Model load failed: {exc}")
                # Signal splash screen to switch to its error state.
                self._emit(AppEvent(type="model_error", message=str(exc)))

        threading.Thread(target=_task, daemon=True).start()

    def run(self, data) -> None:
        if not self._model:
            self._error("Model not loaded.")
            return

        path = Path(data.ct_scan_dir)
        if not path.is_dir():
            self._error("Invalid CT folder.")
            return

        dicoms = sorted(path.glob("*.dcm"))
        if not dicoms:
            self._error("No DICOM files found.")
            return

        self._pending = data
        self._set_state("running")
        self._log(f"Running Sybil on {len(dicoms)} slices…")
        self._progress(0.2)

        self._infer_active = True
        threading.Thread(
            target=self._infer,
            args=([str(f) for f in dicoms],),
            daemon=True,
        ).start()
        threading.Thread(target=self._heartbeat, daemon=True).start()

    # ── inference heartbeat ───────────────────────────────────────────────

    def _heartbeat(self) -> None:
        """Emit a log line every 8 s while inference is running so the
        overlay never appears frozen during a long model.predict() call."""
        elapsed = 0
        interval = 8
        while self._infer_active:
            time.sleep(interval)
            if self._infer_active:
                elapsed += interval
                mins, secs = divmod(elapsed, 60)
                label = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
                self._log(f"CT inference in progress… ({label} elapsed)")

    # ── inference ─────────────────────────────────────────────────────────
    def _infer(self, paths: list[str]) -> None:
        try:
            serie = Serie(paths)
            prediction = self._model.predict([serie])
            scores = prediction.scores[0]
            self._on_complete(scores)
        except Exception as exc:
            self._infer_active = False
            self._error(f"Inference failed: {exc}")

    def _on_complete(self, yearly) -> None:
        self._infer_active = False  # stop heartbeat
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

        # Structured result for the results panel
        self._emit(
            AppEvent(
                type="result",
                data={
                    "yearly": list(yearly),
                    "epi": epi,
                },
            )
        )
        self._set_state("idle")
