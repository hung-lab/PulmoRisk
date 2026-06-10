from __future__ import annotations

import subprocess
import threading
from typing import TYPE_CHECKING

from app.controllers.base_controller import BaseController
from app.utils.event_bus import AppEvent

if TYPE_CHECKING:
    from app.models.patient_model import IntegralRadiomicsInput


class IntegralController(BaseController):
    def __init__(self, root, bus):
        super().__init__(root, bus)

        self._pending = None
        self._running = False

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

            cmd = [
                "integral-radiomics",
                f"--image={payload['image']}",
                f"--mask={payload['mask']}",
                f"--age={int(payload['epi_age'])}",
                f"--sex={1 if payload['epi_female'] else 0}",
                f"--fhlc={int(payload['epi_fhlc'])}",
                f"--copdemph={int(payload['epi_copdemph'])}",
                f"--formersmk={int(payload['epi_formersmk'])}",
                f"--duration={int(payload['epi_duration'])}",
                f"--cigday={int(payload['epi_cigday'])}",
                f"--quittime={int(payload['epi_quittime'])}",
                f"--bmi={float(payload['epi_bmi'])}",
            ]

            self._log("Calling integral-radiomics R CLI subprocess...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.returncode != 0:
                self._error(f"integral-radiomics process failed: {result.stderr}")
                return

            stdout = result.stdout.strip()

            self._log(f"result is: {stdout}")

            self._progress(0.8)

            self._on_complete(stdout)

        except subprocess.CalledProcessError as e:
            self._error(f"integral-radiomics process failed: {e.stderr}")

        except Exception as exc:
            self._error(f"Inference error: {exc}")
            self._set_state("error")

    # ─────────────────────────────── DATA PREP ─────────────────────────

    def _prepare_payload(self, data: IntegralRadiomicsInput) -> dict:
        return {
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
            "image": data.clinical.image_file,
            "mask": data.clinical.mask_file,
        }

    # ─────────────────────────────── RESULT ─────────────────────────────

    def _on_complete(self, result: str) -> None:
        lung_cancer_prob = float(result)

        self._log(
            f"Prediction → lung cancer probability={lung_cancer_prob:.3f}", "SUCCESS"
        )

        self._progress(1.0)

        self._emit(
            AppEvent(
                type="radiomics_result",
                data={
                    "probability": lung_cancer_prob,
                },
            )
        )

        self._set_state("idle")
