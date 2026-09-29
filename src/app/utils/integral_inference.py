import json
import os
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import TypeAlias

import pandas as pd

from app.models.individual_model import IntegralClinicalData
from app.utils.helpers import find_rscript

prediction: TypeAlias = tuple[float, float]


def run_inference_pipeline(individual: IntegralClinicalData) -> prediction:
    """
    Pure inference pipeline:
    - no UI
    - no threading
    - no shared state
    - deterministic output
    """

    try:
        path = Path(individual.image_file)

        if not path.exists():
            raise ValueError(f"Image file Path does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"Image not a file: {path}")

        path = Path(individual.mask_file)

        if not path.exists():
            raise ValueError(f"Mask file Path does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"Mask not a file: {path}")

        # Build temporary CSV for R
        with tempfile.NamedTemporaryFile(
            suffix=".csv",
            delete=False,
        ) as f:
            tmp_csv = Path(f.name)

        df = pd.DataFrame(
            [
                {
                    "image": individual.image_file,
                    "mask": individual.mask_file,
                    "age": individual.age,
                    "sex": 1 if individual.female else 0,
                    "bmi": individual.bmi,
                    "fhlc": individual.fhlc,
                    "copdemph": individual.copdemph,
                    "formersmk": individual.formersmk,
                    "duration": individual.duration,
                    "cigday": individual.cigday,
                    "quittime": individual.quittime,
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

        env = os.environ.copy()
        env["R_LIBS_USER"] = str(Path.home() / ".pulmorisk" / "r" / "library")

        rscript_path = find_rscript()

        # Run R subprocess
        result = subprocess.run(  # nosec B603
            [rscript_path, "-e", r_code],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        stdout = result.stdout.strip()
        if not stdout:
            raise RuntimeError("R script returned no output")

        # Parse JSON
        preds = json.loads(stdout)
        row = preds[0]  # single row expected

        # Find probability column
        pred_benign = None
        pred_malignant = None

        pred_benign = float(row["pred_benign"])
        pred_malignant = float(row["pred_malignant"])

        if pred_benign is None or pred_malignant is None:
            raise RuntimeError(
                f"Could not locate probability column in output: {list(row.keys())}"
            )

        return pred_benign, pred_malignant

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"INTEGRAL-radiomics process failed: {e.stderr}")

    except Exception as exc:
        raise RuntimeError(f"Inference error: {exc}")

    finally:
        if tmp_csv.exists():
            tmp_csv.unlink()
