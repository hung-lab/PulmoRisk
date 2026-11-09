"""Shared field-option maps for Sybil-Epi and INTEGRAL-Radiomics.

Single source of truth for which values a categorical/numeric field can
take and what each one is called. Used by:
- the single-patient views, to populate dropdowns/segmented buttons and
  enumerate every option when that field is left "Not available", and
- the batch controllers, to enumerate the same options when a CSV row
  leaves exactly one field blank,
so the two code paths can't drift out of sync.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Sybil-Epi
# ---------------------------------------------------------------------------

SYBIL_EDUCATION_OPTIONS: dict[str, int] = {
    "1 - Less than high school graduate": 1,
    "2 - High school graduate": 2,
    "3 - Some training after high school": 3,
    "4 - Some college": 4,
    "5 - College graduate": 5,
    "6 - Postgraduate or professional degree": 6,
}

SYBIL_ETHNICITY_OPTIONS: dict[str, str] = {
    "Asian": "Asian",
    "Black": "Black",
    "White": "White",
    "Others": "Others",
}

# Shared by every tri-state Yes/No field (COPD, family history, personal
# cancer history, current smoker).
SYBIL_YES_NO_OPTIONS: dict[str, int] = {"No": 0, "Yes": 1}

# When a numeric field is the one left blank, the analysis runs once per
# fixed candidate value below (same "table of common values" treatment as
# the categorical fields) instead of substituting a single placeholder.
SYBIL_NUMERIC_FIELD_OPTIONS: dict[str, dict[str, float]] = {
    "age": {"58": 58.0, "63": 63.0, "68": 68.0},
    "bmi": {"24": 24.0, "27": 27.0, "30": 30.0},
    "smoking_duration": {"35": 35.0, "40": 40.0, "45": 45.0},
    "smoking_intensity": {"20": 20.0, "25": 25.0, "30": 30.0},
    "smoking_quit_time": {"0": 0.0, "5": 5.0, "9": 9.0},
}

SYBIL_CATEGORICAL_OPTIONS: dict[str, dict] = {
    "education": SYBIL_EDUCATION_OPTIONS,
    "ethnicity": SYBIL_ETHNICITY_OPTIONS,
    "copd": SYBIL_YES_NO_OPTIONS,
    "family_lc_history": SYBIL_YES_NO_OPTIONS,
    "personal_cancer_history": SYBIL_YES_NO_OPTIONS,
    "smoking_status": SYBIL_YES_NO_OPTIONS,
}

SYBIL_FIELD_DISPLAY_NAMES: dict[str, str] = {
    "age": "Age",
    "bmi": "BMI",
    "smoking_duration": "Smoking duration",
    "smoking_intensity": "Smoking intensity",
    "smoking_quit_time": "Smoking quit time",
    "education": "Education",
    "ethnicity": "Ethnicity",
    "copd": "COPD",
    "family_lc_history": "Family history of lung cancer",
    "personal_cancer_history": "Personal history of any cancer",
    "smoking_status": "Current smoker",
}

# Every field (besides ct_scan_dir / six_year_risk, which has its own
# required-one-of-two rule) that may be the single blank field in a row.
SYBIL_OPTIONAL_FIELDS: tuple[str, ...] = (
    "age",
    "bmi",
    "smoking_duration",
    "smoking_intensity",
    "smoking_quit_time",
    "education",
    "ethnicity",
    "copd",
    "family_lc_history",
    "personal_cancer_history",
    "smoking_status",
)


# ---------------------------------------------------------------------------
# INTEGRAL-Radiomics
# ---------------------------------------------------------------------------

INTEGRAL_SEX_OPTIONS: dict[str, int] = {"Male": 0, "Female": 1}

# Shared by every tri-state Yes/No field (family history, COPD/emphysema,
# former smoker).
INTEGRAL_YES_NO_OPTIONS: dict[str, int] = {"No": 0, "Yes": 1}

# Mirrors Sybil-Epi's values for the fields the two models share.
INTEGRAL_NUMERIC_FIELD_OPTIONS: dict[str, dict[str, int | float]] = {
    "age": {"58": 58, "63": 63, "68": 68},
    "bmi": {"24": 24.0, "27": 27.0, "30": 30.0},
    "duration": {"35": 35, "40": 40, "45": 45},
    "cigday": {"20": 20, "25": 25, "30": 30},
    "quittime": {"0": 0, "5": 5, "9": 9},
}

INTEGRAL_CATEGORICAL_OPTIONS: dict[str, dict] = {
    "female": INTEGRAL_SEX_OPTIONS,
    "fhlc": INTEGRAL_YES_NO_OPTIONS,
    "copdemph": INTEGRAL_YES_NO_OPTIONS,
    "formersmk": INTEGRAL_YES_NO_OPTIONS,
}

INTEGRAL_FIELD_DISPLAY_NAMES: dict[str, str] = {
    "age": "Age",
    "bmi": "BMI",
    "duration": "Smoking duration",
    "cigday": "Cigarettes per day",
    "quittime": "Smoking quit time",
    "female": "Sex",
    "fhlc": "Family history of lung cancer",
    "copdemph": "COPD / emphysema",
    "formersmk": "Former smoker",
}

# Every field (besides image_file / mask_file, which stay strictly
# required) that may be the single blank field in a row.
INTEGRAL_OPTIONAL_FIELDS: tuple[str, ...] = (
    "age",
    "bmi",
    "duration",
    "cigday",
    "quittime",
    "female",
    "fhlc",
    "copdemph",
    "formersmk",
)
