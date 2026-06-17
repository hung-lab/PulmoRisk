"""UI-layer input parsing.

These classes only parse raw strings from form widgets into Python types.
Business validation rules (ranges, required fields, mutual exclusion) live
in the model dataclasses via ``__post_init__``.  This keeps the validators
small and makes the models self-validating regardless of which code path
constructs them.

Typical usage in a view::

    try:
        age = FieldParser.float("age", age_str, "Age")
        ...
        data = SybilInputData(age=age, ...)   # validation happens here
    except ParseError as exc:
        # show exc.field / exc.message in the UI before the model is built
        ...
    except ModelValidationError as exc:
        # field_errors maps field name → message for UI highlighting
        for field, msg in exc.field_errors.items():
            ...
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Parse-only error (bad string input before the model is even constructed)
# ---------------------------------------------------------------------------


@dataclass
class ParseError(Exception):
    """Raised when a raw string cannot be converted to the expected type."""

    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.field}: {self.message}"


# ---------------------------------------------------------------------------
# String → Python type parsers
# ---------------------------------------------------------------------------


class FieldParser:
    """Stateless helpers that convert widget strings to typed values.

    Raises :class:`ParseError` on conversion failure so the view can
    surface the problem before attempting to construct a model.
    """

    @staticmethod
    def float(field: str, raw: str, label: str | None = None) -> float:
        display = label or field
        stripped = raw.strip()
        if not stripped:
            raise ParseError(field, f"{display} is required")
        try:
            return float(stripped)
        except ValueError:
            raise ParseError(field, f"{display} must be a number")

    @staticmethod
    def int(field: str, raw: str, label: str | None = None) -> int:
        display = label or field
        stripped = raw.strip()
        if not stripped:
            raise ParseError(field, f"{display} is required")
        try:
            return int(stripped)
        except ValueError:
            raise ParseError(field, f"{display} must be a whole number")

    @staticmethod
    def optional_float(field: str, raw: str, label: str | None = None) -> float | None:
        """Return ``None`` for blank strings; parse otherwise."""
        stripped = raw.strip()
        if not stripped:
            return None
        return FieldParser.float(field, raw, label)

    @staticmethod
    def required_str(field: str, raw: str, label: str | None = None) -> str:
        display = label or field
        stripped = raw.strip()
        if not stripped:
            raise ParseError(field, f"{display} is required")
        return stripped


# ---------------------------------------------------------------------------
# Batch CSV row coercer
# ---------------------------------------------------------------------------


class BatchSybilRowParser:
    """Coerce a CSV row (dict of strings) to typed values for SybilInputData.

    Returns a dict ready to unpack as ``SybilInputData(**row_dict)``.
    Raises :class:`ParseError` on the first malformed cell so the batch
    worker can log the offending column and row index.
    """

    _FLOAT_FIELDS = (
        "age",
        "bmi",
        "smoking_duration",
        "smoking_intensity",
        "smoking_quit_time",
    )
    _INT_FIELDS = (
        "copd",
        "education",
        "ethnicity",
        "family_lc_history",
        "personal_cancer_history",
        "smoking_status",
    )

    @classmethod
    def parse(cls, row: dict) -> dict:
        out: dict = {}

        for f in cls._FLOAT_FIELDS:
            out[f] = FieldParser.float(f, str(row.get(f, "")), f.replace("_", " "))

        for f in cls._INT_FIELDS:
            out[f] = FieldParser.int(f, str(row.get(f, "")), f.replace("_", " "))

        out["ct_scan_dir"] = row.get("ct_scan_dir") or None
        out["six_year_risk"] = FieldParser.optional_float(
            "six_year_risk", str(row.get("six_year_risk", ""))
        )

        return out


class BatchIntegralRowParser:
    """Coerce a CSV row (dict of strings) to typed values for IntegralClinicalData.

    Returns a dict ready to unpack as ``IntegralClinicalData(**row_dict)``.
    Raises :class:`ParseError` on the first malformed cell so the batch
    worker can log the offending column and row index.
    """

    _FLOAT_FIELDS = ("bmi",)
    _INT_FIELDS = (
        "age",
        "female",
        "fhlc",
        "copdemph",
        "formersmk",
        "duration",
        "cigday",
        "quittime",
    )

    @classmethod
    def parse(cls, row: dict) -> dict:
        out: dict = {}

        for f in cls._FLOAT_FIELDS:
            out[f] = FieldParser.float(f, str(row.get(f, "")), f.replace("_", " "))

        for f in cls._INT_FIELDS:
            out[f] = FieldParser.int(f, str(row.get(f, "")), f.replace("_", " "))

        out["image_file"] = row.get("image_file") or None
        out["mask_file"] = row.get("mask_file") or None

        return out
