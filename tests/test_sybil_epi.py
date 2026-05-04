"""Tests for Sybil-EPI scoring logic."""

import math

import pytest

from app.models.patient_model import SybilInputData
from app.utils.sybil_epi import (
    EpiInput,
    calculate_sybil_epi_score,
    epi_input_from_patient_data,
)

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def base_epi_input():
    """A realistic mid-risk patient."""
    return EpiInput(
        age=65.0,
        bmi=27.0,
        copd=0,
        education=3,
        ethnicity="White",
        family_history=0,
        personal_history=0,
        smoking_duration=30.0,
        smoking_intensity=20.0,
        smoking_quit=5.0,
        smoking_status=0,
        risk_sybil_6_year=0.05,
    )


@pytest.fixture
def base_patient():
    return SybilInputData(
        age=65,
        bmi=27.0,
        copd=0,
        education=3,
        ethnicity=1,  # White
        family_lc_history=0,
        personal_cancer_history=0,
        smoking_duration=30.0,
        smoking_intensity=20.0,
        smoking_quit_time=5.0,
        smoking_status=0,
        ct_scan_dir="/tmp/scans",
    )


# ── calculate_sybil_epi_score — output bounds ─────────────────────────────────


class TestOutputBounds:
    def test_score_is_between_0_and_1(self, base_epi_input):
        score = calculate_sybil_epi_score(base_epi_input)
        assert 0.0 < score < 1.0

    def test_high_risk_patient_scores_higher(self, base_epi_input):
        low = calculate_sybil_epi_score(base_epi_input)

        high_risk = EpiInput(
            **{
                **base_epi_input.__dict__,
                "risk_sybil_6_year": 0.9,
                "copd": 1,
                "family_history": 1,
                "personal_history": 1,
                "smoking_duration": 50.0,
                "smoking_intensity": 40.0,
                "smoking_status": 1,
            }
        )
        high = calculate_sybil_epi_score(high_risk)
        assert high > low

    def test_low_sybil_score_lowers_risk(self, base_epi_input):
        high = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "risk_sybil_6_year": 0.9})
        )
        low = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "risk_sybil_6_year": 0.01})
        )
        assert high > low

    def test_score_is_deterministic(self, base_epi_input):
        s1 = calculate_sybil_epi_score(base_epi_input)
        s2 = calculate_sybil_epi_score(base_epi_input)
        assert s1 == s2

    def test_score_is_float(self, base_epi_input):
        assert isinstance(calculate_sybil_epi_score(base_epi_input), float)

    def test_score_not_nan(self, base_epi_input):
        assert not math.isnan(calculate_sybil_epi_score(base_epi_input))


# ── ethnicity handling ────────────────────────────────────────────────────────


class TestEthnicity:
    """Different ethnicities produce different scores (non-zero coefficients)."""

    def _score(self, base, ethnicity):
        return calculate_sybil_epi_score(
            EpiInput(**{**base.__dict__, "ethnicity": ethnicity})
        )

    def test_white_scores_differ_from_black(self, base_epi_input):
        assert self._score(base_epi_input, "White") != self._score(
            base_epi_input, "Black"
        )

    def test_white_scores_differ_from_asian(self, base_epi_input):
        assert self._score(base_epi_input, "White") != self._score(
            base_epi_input, "Asian"
        )

    def test_white_scores_differ_from_others(self, base_epi_input):
        assert self._score(base_epi_input, "White") != self._score(
            base_epi_input, "Others"
        )

    def test_all_ethnicity_scores_in_bounds(self, base_epi_input):
        for eth in ("White", "Black", "Asian", "Others"):
            score = self._score(base_epi_input, eth)
            assert 0.0 < score < 1.0, f"Score out of bounds for {eth}: {score}"


# ── feature monotonicity ──────────────────────────────────────────────────────


class TestMonotonicity:
    """Increasing a risk factor should increase (or not decrease) the score,
    and vice-versa for protective factors."""

    def test_copd_increases_risk(self, base_epi_input):
        without = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "copd": 0})
        )
        with_ = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "copd": 1})
        )
        assert with_ > without

    def test_family_history_increases_risk(self, base_epi_input):
        without = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "family_history": 0})
        )
        with_ = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "family_history": 1})
        )
        assert with_ > without

    def test_personal_history_increases_risk(self, base_epi_input):
        without = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "personal_history": 0})
        )
        with_ = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "personal_history": 1})
        )
        assert with_ > without

    def test_higher_smoking_duration_increases_risk(self, base_epi_input):
        low = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "smoking_duration": 10.0})
        )
        high = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "smoking_duration": 50.0})
        )
        assert high > low

    def test_higher_bmi_decreases_risk(self, base_epi_input):
        """BMI coefficient is negative across all models."""
        low_bmi = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "bmi": 20.0})
        )
        high_bmi = calculate_sybil_epi_score(
            EpiInput(**{**base_epi_input.__dict__, "bmi": 40.0})
        )
        assert high_bmi < low_bmi


# ── epi_input_from_patient_data ───────────────────────────────────────────────


class TestEpiInputFromPatientData:
    def test_ethnicity_white_mapped(self, base_patient):
        epi = epi_input_from_patient_data(base_patient, 0.05)
        assert epi.ethnicity == "White"

    def test_ethnicity_black_mapped(self, base_patient):
        patient = SybilInputData(**{**base_patient.__dict__, "ethnicity": 2})
        epi = epi_input_from_patient_data(patient, 0.05)
        assert epi.ethnicity == "Black"

    def test_ethnicity_asian_mapped(self, base_patient):
        patient = SybilInputData(**{**base_patient.__dict__, "ethnicity": 3})
        epi = epi_input_from_patient_data(patient, 0.05)
        assert epi.ethnicity == "Asian"

    def test_ethnicity_others_mapped(self, base_patient):
        patient = SybilInputData(**{**base_patient.__dict__, "ethnicity": 4})
        epi = epi_input_from_patient_data(patient, 0.05)
        assert epi.ethnicity == "Others"

    def test_invalid_ethnicity_raises(self, base_patient):
        patient = SybilInputData(**{**base_patient.__dict__, "ethnicity": 99})
        with pytest.raises(KeyError):
            epi_input_from_patient_data(patient, 0.05)

    def test_sybil_score_forwarded(self, base_patient):
        epi = epi_input_from_patient_data(base_patient, 0.123)
        assert epi.risk_sybil_6_year == pytest.approx(0.123)

    def test_all_fields_copied(self, base_patient):
        epi = epi_input_from_patient_data(base_patient, 0.05)
        assert epi.age == base_patient.age
        assert epi.bmi == pytest.approx(base_patient.bmi)
        assert epi.copd == base_patient.copd
        assert epi.education == base_patient.education
        assert epi.family_history == base_patient.family_lc_history
        assert epi.personal_history == base_patient.personal_cancer_history
        assert epi.smoking_duration == pytest.approx(base_patient.smoking_duration)
        assert epi.smoking_intensity == pytest.approx(base_patient.smoking_intensity)
        assert epi.smoking_quit == pytest.approx(base_patient.smoking_quit_time)
        assert epi.smoking_status == base_patient.smoking_status

    def test_round_trip_produces_valid_score(self, base_patient):
        epi = epi_input_from_patient_data(base_patient, 0.05)
        score = calculate_sybil_epi_score(epi)
        assert 0.0 < score < 1.0
