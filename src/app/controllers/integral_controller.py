from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from app.controllers.base_controller import BaseController
from app.utils.event_bus import AppEvent
from app.utils.helpers import find_rscript, format_percent

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
                        "age": int(payload["epi_age"]),
                        "sex": 1 if payload["epi_female"] else 0,
                        "bmi": float(payload["epi_bmi"]),
                        "fhlc": int(payload["epi_fhlc"]),
                        "copdemph": int(payload["epi_copdemph"]),
                        "formersmk": int(payload["epi_formersmk"]),
                        "duration": int(payload["epi_duration"]),
                        "cigday": int(payload["epi_cigday"]),
                        "quittime": int(payload["epi_quittime"]),
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
            "image": data.clinical.image_file,
            "mask": data.clinical.mask_file,
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
