from __future__ import annotations

import json
import os
import subprocess  # nosec B404
import tempfile
import threading
import traceback
from pathlib import Path

import pandas as pd

from app.controllers.base_controller import BaseController
from app.models.individual_model import IntegralClinicalData
from app.utils.event_bus import AppEvent
from app.utils.field_options import (
    INTEGRAL_CATEGORICAL_OPTIONS,
    INTEGRAL_FIELD_DISPLAY_NAMES,
    INTEGRAL_NUMERIC_FIELD_OPTIONS,
    INTEGRAL_OPTIONAL_FIELDS,
)
from app.utils.helpers import (
    InvalidFileError,
    clean_r_subprocess_env,
    find_rscript,
    format_percent,
    validate_file_path,
)
from app.utils.validators import BatchIntegralRowParser, ParseError, find_blank_fields

SEX_OPTIONS = {
    "Male": 0,
    "Female": 1,
}


class IntegralController(BaseController):
    def __init__(self, root, bus):
        super().__init__(root, bus)

        self._pending = None
        self._ambiguous_field: str | None = None
        self._ambiguous_values: dict[str, int | str] | None = None
        self._running = False
        self._batch_active = False
        self._batch_cancel = False

    # ─────────────────────────────── RUN ───────────────────────────────

    def run(
        self,
        data: IntegralClinicalData,
        ambiguous_field: str | None = None,
        ambiguous_values: dict[str, int | str] | None = None,
    ) -> None:
        self._pending = data
        self._ambiguous_field = ambiguous_field
        self._ambiguous_values = ambiguous_values
        self._set_state("running_single")

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

            option_labels: list[str] = []
            if self._ambiguous_field and self._ambiguous_values:
                # One field was left "Not available" — score every option
                # in a single R call (predict_integral_radiomics already
                # accepts multi-row input for batch mode) instead of
                # spawning a separate subprocess per option. Note: unlike
                # Sybil-Epi, integralrad has no exported way to reuse a
                # cached radiomics extraction across rows, so each option
                # still re-extracts features for the same image/mask.
                rows = []
                for label, value in self._ambiguous_values.items():
                    rows.append(
                        self._payload_to_row({**payload, self._ambiguous_field: value})
                    )
                    option_labels.append(label)
            else:
                rows = [self._payload_to_row(payload)]

            preds = self._predict_rows(rows)
            self._progress(0.8)

            if option_labels:
                results = [
                    (label, float(row["pred_malignant"]))
                    for label, row in zip(option_labels, preds, strict=True)
                ]
                self._log(f"Prediction results: {results}")
                self._on_complete_multi(results)
            else:
                row = preds[0]  # single row expected
                self._log(f"Prediction result: {row}")
                probability = float(row["pred_malignant"])
                self._on_complete(probability)

        except Exception as exc:
            self._error(f"Inference error: {exc}")
            self._set_state("error")

    def _predict_rows(self, rows: list[dict]) -> list[dict]:
        """Run predict_integral_radiomics on a batch of R-ready rows in a
        single Rscript subprocess call. Returns one prediction dict per row,
        in the same order as *rows*."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_csv = Path(f.name)

        df = pd.DataFrame(rows)
        df.to_csv(tmp_csv, index=False)

        r_path = str(tmp_csv).replace("\\", "/")

        # R code to predict and output JSON
        r_code = f"""
        .libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
        library(integralrad)
        library(jsonlite)

        preds <- predict_integral_radiomics("{r_path}")
        cat(toJSON(preds, dataframe="rows"))
        """

        # Passing R code via `-e` on the command line crashes the R process
        # outright (access violation) once integralrad spawns its own
        # reticulate/uv subprocess — writing it to a script file and running
        # that instead avoids whatever Windows argv quirk causes this.
        script_file = Path(tempfile.gettempdir()) / f"{tmp_csv.stem}_predict.R"
        script_file.write_text(r_code, encoding="utf-8")

        try:
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
            env = clean_r_subprocess_env(env)

            rscript_path = find_rscript()

            result = subprocess.run(  # nosec B603
                [rscript_path, "--vanilla", str(script_file)],
                env=env,
                cwd=tempfile.gettempdir(),
                capture_output=True,
                text=True,
                check=True,
            )

            self._log(f"Raw R stdout:\n{result.stdout}")
            self._log(f"Raw R stderr:\n{result.stderr}")

            stdout = result.stdout.strip()
            if not stdout:
                raise RuntimeError("integral-radiomics returned empty output")

            return json.loads(stdout)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"integral-radiomics process failed: {e.stderr}") from e

        finally:
            if tmp_csv.exists():
                tmp_csv.unlink()
            if script_file.exists():
                script_file.unlink()

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

    def _payload_to_row(self, payload: dict) -> dict:
        return {
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

    def _on_complete_multi(self, results: list[tuple[str, float]]) -> None:
        for label, probability in results:
            self._log(
                f"{self._ambiguous_field}={label}: "
                f"lung cancer probability={format_percent(probability)}",
                "SUCCESS",
            )

        self._progress(1.0)

        self._emit(
            AppEvent(
                type="radiomics_result",
                data={"field": self._ambiguous_field, "results": results},
            )
        )

        self._set_state("idle")

    def _row_to_individual(self, row) -> IntegralClinicalData:
        try:
            parsed = BatchIntegralRowParser.parse(dict(row))
        except ParseError as exc:
            # surface the exact column that failed
            raise ValueError(f"Column '{exc.field}': {exc.message}") from exc

        # ModelValidationError (out-of-range etc.) propagates naturally —
        # the batch loop already catches Exception and logs it per-row.
        return IntegralClinicalData(**parsed)

    @staticmethod
    def _candidates_for(field: str) -> dict:
        """Label → value options for whichever field is missing in a row."""
        return INTEGRAL_NUMERIC_FIELD_OPTIONS.get(field) or INTEGRAL_CATEGORICAL_OPTIONS[field]

    def _blank_row_result(self, row_dict: dict, error: str) -> dict:
        return {
            **row_dict,
            "pred_benign": None,
            "pred_malignant": None,
            "missing_field": None,
            "error": error,
        }

    def _run_batch_worker(self, csv_path: str) -> None:
        try:
            self._batch_active = True
            self._batch_cancel = False

            df = pd.read_csv(csv_path)
            output_rows: list[dict] = []

            total = len(df)

            self._set_state("running_batch")
            self._log(f"Starting batch run: {total} individuals")

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
                self._log(f"Completed {i + 1}/{total}")

                if self._batch_cancel:
                    self._log("Batch cancelled by user", "WARNING")
                    for j in range(i, total):
                        output_rows.append(
                            self._blank_row_result(dict(df.iloc[j]), "cancelled")
                        )
                    break

                row_dict = dict(row)

                # At most one field (besides image_file / mask_file, which
                # stay strictly required) may be blank — mirrors the
                # single-patient form's rule.
                blank = find_blank_fields(row_dict, INTEGRAL_OPTIONAL_FIELDS)
                if len(blank) > 1:
                    names = ", ".join(
                        INTEGRAL_FIELD_DISPLAY_NAMES.get(f, f) for f in blank
                    )
                    msg = f"Only one field may be missing. Currently missing: {names}."
                    self._warn(f"Row {i + 1} skipped: {msg}")
                    output_rows.append(self._blank_row_result(row_dict, msg))
                    continue

                ambiguous_field = blank[0] if blank else None

                missing_files = find_blank_fields(row_dict, ("image_file", "mask_file"))
                if missing_files:
                    names = " and ".join(missing_files)
                    verb = "is" if len(missing_files) == 1 else "are"
                    msg = f"{names} {verb} required."
                    self._warn(f"Row {i + 1} skipped: {msg}")
                    output_rows.append(self._blank_row_result(row_dict, msg))
                    continue

                try:
                    parse_row = dict(row_dict)
                    if ambiguous_field:
                        # A placeholder for parsing/validation below — every
                        # candidate value gets its own row sent to R.
                        placeholder = next(iter(self._candidates_for(ambiguous_field).values()))
                        parse_row[ambiguous_field] = str(placeholder)

                    individual = self._row_to_individual(parse_row)

                    try:
                        validate_file_path(Path(individual.image_file), "image_file")
                        validate_file_path(Path(individual.mask_file), "mask_file")
                    except InvalidFileError as e:
                        msg = f"{e.field_name} invalid ({e.reason})"
                        self._warn(f"Row {i + 1} skipped: {msg}")
                        output_rows.append(self._blank_row_result(row_dict, msg))
                        continue

                    self._log(f"Running inference on row {i + 1} for individual: ")

                    payload = self._prepare_payload(individual)

                    if ambiguous_field:
                        # One R call scores every option for this row — unlike
                        # Sybil-Epi, integralrad has no exported way to reuse a
                        # cached radiomics extraction, so each option still
                        # re-extracts features for the same image/mask.
                        field_label = INTEGRAL_FIELD_DISPLAY_NAMES.get(
                            ambiguous_field, ambiguous_field
                        )
                        values = list(self._candidates_for(ambiguous_field).values())
                        rows = [
                            self._payload_to_row({**payload, ambiguous_field: value})
                            for value in values
                        ]
                        preds = self._predict_rows(rows)

                        for value, pred_row in zip(values, preds, strict=True):
                            output_rows.append(
                                {
                                    **row_dict,
                                    ambiguous_field: value,
                                    "pred_benign": float(pred_row["pred_benign"]),
                                    "pred_malignant": float(pred_row["pred_malignant"]),
                                    "missing_field": field_label,
                                    "error": None,
                                }
                            )
                    else:
                        preds = self._predict_rows([self._payload_to_row(payload)])
                        pred_row = preds[0]
                        output_rows.append(
                            {
                                **row_dict,
                                "pred_benign": float(pred_row["pred_benign"]),
                                "pred_malignant": float(pred_row["pred_malignant"]),
                                "missing_field": None,
                                "error": None,
                            }
                        )

                except Exception as e:
                    self._log_error(f"Row {i + 1} failed: {e}")
                    self._log_error(traceback.format_exc())
                    output_rows.append(self._blank_row_result(row_dict, str(e)))

            output_df = pd.DataFrame(output_rows)

            output_path = str(Path(csv_path).with_suffix(""))
            output_path = output_path + "_scored.csv"

            output_df.to_csv(output_path, index=False)

            self._batch_active = False
            self._set_state("idle")

            self._emit(
                AppEvent(type="radiomics_result", data={"output_path": output_path})
            )
        except Exception as e:
            self._error("Batch crashed completely")
            self._error(str(e))
            self._error(traceback.format_exc())
            self._set_state("idle")
