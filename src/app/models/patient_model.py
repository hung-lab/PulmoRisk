"""Data models with built-in validation.

Validation runs automatically in ``__post_init__`` so every construction
path — single-patient UI, batch CSV, or future API — gets the same checks.

Catch ``ModelValidationError`` to get field-level details for UI highlighting:

    try:
        data = SybilInputData(**kwargs)
    except ModelValidationError as exc:
        for field, msg in exc.field_errors.items():
            ...  # highlight the field in the UI
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import PROJECT_ROOT

# ---------------------------------------------------------------------------
# Structured validation error
# ---------------------------------------------------------------------------


class ModelValidationError(ValueError):
    """Raised when a model dataclass fails ``__post_init__`` validation.

    Attributes:
        field_errors: Mapping of field name → human-readable error message.
                      One entry per invalid field; may contain multiple fields.
    """

    def __init__(self, field_errors: dict[str, str]) -> None:
        self.field_errors = field_errors
        lines = [f"  {f}: {m}" for f, m in field_errors.items()]
        super().__init__("Validation failed:\n" + "\n".join(lines))


# ---------------------------------------------------------------------------
# Shared validation helpers
# ---------------------------------------------------------------------------


def _check_range(
    errors: dict[str, str],
    field_name: str,
    value: float | None,
    min_v: float,
    max_v: float,
    label: str | None = None,
) -> None:
    """Add an error entry if *value* is outside [min_v, max_v]."""
    display = label or field_name
    if value is None:
        errors[field_name] = f"{display} is required"
    elif not (min_v <= value <= max_v):
        errors[field_name] = f"{display} must be between {min_v} and {max_v}"


def _check_choice(
    errors: dict[str, str],
    field_name: str,
    value: int | None,
    choices: tuple[int, ...],
    label: str | None = None,
) -> None:
    display = label or field_name
    if value not in choices:
        errors[field_name] = f"{display} must be one of {choices}"


# ---------------------------------------------------------------------------
# Sybil models
# ---------------------------------------------------------------------------


@dataclass
class SybilInputData:
    """Patient data for the Sybil-EPI lung cancer risk model.

    Raises:
        ModelValidationError: if any field is outside its valid range.
    """

    age: float
    bmi: float
    copd: int  # 0 or 1
    education: int  # 1-6 (NLST codes)
    ethnicity: int  # 1-4 (NLST codes)
    family_lc_history: int  # 0 or 1
    personal_cancer_history: int  # 0 or 1
    smoking_duration: float  # years
    smoking_intensity: float  # cigarettes/day
    smoking_quit_time: float  # years since quitting
    smoking_status: int  # 0 = former, 1 = current
    ct_scan_dir: str | None = str(PROJECT_ROOT)
    six_year_risk: float | None = None  # optional pre-computed Sybil score

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}

        _check_range(errors, "age", self.age, 0, 100)
        _check_range(errors, "bmi", self.bmi, 15, 50, "BMI")
        _check_choice(errors, "copd", self.copd, (0, 1), "COPD")
        _check_range(errors, "education", self.education, 1, 6, "Education")
        _check_range(errors, "ethnicity", self.ethnicity, 1, 4, "Ethnicity")
        _check_choice(
            errors,
            "family_lc_history",
            self.family_lc_history,
            (0, 1),
            "Family lung cancer history",
        )
        _check_choice(
            errors,
            "personal_cancer_history",
            self.personal_cancer_history,
            (0, 1),
            "Personal cancer history",
        )
        _check_range(
            errors,
            "smoking_duration",
            self.smoking_duration,
            0,
            self.age,
            "Smoking duration",
        )
        _check_range(
            errors,
            "smoking_intensity",
            self.smoking_intensity,
            0,
            1000,
            "Smoking intensity",
        )
        _check_range(
            errors,
            "smoking_quit_time",
            self.smoking_quit_time,
            0,
            self.age,
            "Smoking quit time",
        )
        _check_choice(
            errors, "smoking_status", self.smoking_status, (0, 1), "Smoking status"
        )

        # Either a CT folder OR a pre-computed six_year_risk must be present
        if self.six_year_risk is not None:
            _check_range(
                errors,
                "six_year_risk",
                self.six_year_risk,
                0.0,
                1.0,
                "6-year Sybil risk",
            )
        else:
            if not self.ct_scan_dir or str(self.ct_scan_dir) == str(PROJECT_ROOT):
                errors["ct_scan_dir"] = "CT scan folder is required"

        if errors:
            raise ModelValidationError(errors)


@dataclass
class RiskResult:
    yearly_scores: list[float]
    epi_score: float


# ---------------------------------------------------------------------------
# INTEGRAL Radiomics models
# ---------------------------------------------------------------------------


@dataclass
class IntegralClinicalData:
    """Clinical inputs for the INTEGRAL Radiomics model.

    Raises:
        ModelValidationError: if any field is outside its valid range.
    """

    age: int  # Years [0 - 100]
    female: int  # 0 = male, 1 = female
    fhlc: int  # family lung cancer history: 0 or 1
    copdemph: int  # COPD / emphysema: 0 or 1
    formersmk: int  # former smoker: 0 or 1
    duration: int  # smoking duration (years) [0 - age]
    cigday: int  # cigarettes per day [0 - 100]
    quittime: int  # years since quitting [0 - age]
    bmi: float  # Body mass index (kg/m^2) [15 - 50]

    image_file: str | None = None  # Path to image (NRRD format)
    mask_file: str | None = None  # Path to nodule mask (NRRD format)

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}

        _check_range(errors, "age", self.age, 0, 100, "Age")
        _check_range(errors, "bmi", self.bmi, 15, 50, "BMI")
        _check_choice(errors, "female", self.female, (0, 1), "Sex")
        _check_choice(errors, "fhlc", self.fhlc, (0, 1), "Family lung cancer history")
        _check_choice(errors, "copdemph", self.copdemph, (0, 1), "COPD / emphysema")
        _check_choice(errors, "formersmk", self.formersmk, (0, 1), "Former smoker")
        _check_range(errors, "duration", self.duration, 0, self.age, "Smoking duration")
        _check_range(errors, "cigday", self.cigday, 0, 100, "Cigarettes per day")
        _check_range(
            errors, "quittime", self.quittime, 0, self.age, "Years since quitting"
        )

        if not self.image_file:
            errors["image_file"] = "CT image file is required"
        if not self.mask_file:
            errors["mask_file"] = "CT mask file is required"

        if errors:
            raise ModelValidationError(errors)


@dataclass
class IntegralRiskResult:
    benign_probability: float
    malignant_probability: float
