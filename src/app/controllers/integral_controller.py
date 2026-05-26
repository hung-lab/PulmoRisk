from __future__ import annotations

import json
import subprocess
import threading
from typing import TYPE_CHECKING

from app.controllers.base_controller import BaseController
from app.utils.event_bus import AppEvent
from app.utils.helpers import resource_path

if TYPE_CHECKING:
    from app.models.patient_model import IntegralRadiomicsInput


class IntegralController(BaseController):
    def __init__(self, root, bus):
        super().__init__(root, bus)

        self._pending = None
        self._running = False

        # path to R model + script
        self._model_path = resource_path("models", "INTEGRAL-Radiomics.rds")
        self._r_script = resource_path("utils", "integral_predict.R")

    # ─────────────────────────────── RUN ───────────────────────────────

    def run(self, data: IntegralRadiomicsInput) -> None:
        self._pending = data
        self._set_state("running")

        self._log("Running INTEGRAL model (R subprocess)...")
        self._progress(0.3)

        threading.Thread(target=self._infer, daemon=True).start()

    # ─────────────────────────────── INFERENCE ─────────────────────────

    def _infer(self) -> None:
        try:
            payload = self._prepare_payload(self._pending)
            with open("/tmp/input.json", "w") as f:
                json.dump(payload, f)
            # input_json = json.dumps([payload])
            # print(input_json)

            cmd = [
                "Rscript",
                self._r_script,
                self._model_path,
                "/tmp/input.json",
            ]

            self._log("Calling R subprocess...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.returncode != 0:
                self._error(f"R process failed: {result.stderr}")
                return

            stdout = result.stdout.strip()
            try:
                output = json.loads(stdout)
            except json.JSONDecodeError:
                raise RuntimeError(f"Invalid JSON from R:\n{stdout[:1000]}")
            self._log(f"Result of running R Process {output}", "INFO")

            # Check if R returned a graceful missing-columns error
            if "error" in output:
                missing = output.get("missing", [])
                self._log(
                    f"Missing {len(missing)} required features. First 5: {missing[:5]}",
                    "ERROR",
                )
                # Write missing cols to log so user can see them
                self._log("Full list written to /tmp/required_cols.json", "WARNING")
                raise ValueError(f"Missing required radiomics features: {missing[:5]}")

            self._progress(0.8)

            self._on_complete(output)

        except subprocess.CalledProcessError as e:
            self._error(f"R process failed: {e.stderr}")

        except Exception as exc:
            self._error(f"Inference error: {exc}")
            self._set_state("error")

    # ─────────────────────────────── DATA PREP ─────────────────────────

    def _prepare_payload(self, data: IntegralRadiomicsInput) -> dict:
        clinical = {
            "epi_age": data.clinical.epi_age,
            "epi_female": data.clinical.epi_female,
            "epi_fhlc": data.clinical.epi_fhlc,
            "epi_copdemph": data.clinical.epi_copdemph,
            "epi_formersmk": data.clinical.epi_formersmk,
            "epi_duration": data.clinical.epi_duration,
            "epi_cigday": data.clinical.epi_cigday,
            "epi_quittime": data.clinical.epi_quittime,
            "epi_bmi": data.clinical.epi_bmi,
            "study": data.clinical.study,
            "pid": data.clinical.pid,
            "nid": data.clinical.nid,
        }

        radiomics = data.radiomics.features or {}

        return {**clinical, **radiomics}

    # ─────────────────────────────── RESULT ─────────────────────────────

    def _on_complete(self, result: dict) -> None:
        benign = float(result.get(".pred_0", 0))
        malignant = float(result.get(".pred_1", 0))

        self._log(
            f"Prediction → benign={benign:.3f}, malignant={malignant:.3f}", "SUCCESS"
        )

        self._progress(1.0)

        self._emit(
            AppEvent(
                type="result",
                data={
                    "benign": benign,
                    "malignant": malignant,
                },
            )
        )

        self._set_state("idle")
