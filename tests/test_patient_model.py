"""Tests for patient_model dataclasses."""

from dataclasses import asdict, fields

import pytest

from app.models.patient_model import RiskResult, SybilInputData

# ── SybilInputData ────────────────────────────────────────────────────────────


class TestSybilInputData:
    @pytest.fixture
    def sample(self):
        return SybilInputData(
            age=65,
            bmi=27.5,
            copd=0,
            education=3,
            ethnicity=1,
            family_lc_history=0,
            personal_cancer_history=1,
            smoking_duration=30.0,
            smoking_intensity=20.0,
            smoking_quit_time=5.0,
            smoking_status=0,
            ct_scan_dir="/tmp/scans",
            six_year_risk=None,
        )

    def test_fields_are_stored(self, sample):
        assert sample.age == 65
        assert sample.bmi == pytest.approx(27.5)
        assert sample.copd == 0
        assert sample.education == 3
        assert sample.ethnicity == 1
        assert sample.family_lc_history == 0
        assert sample.personal_cancer_history == 1
        assert sample.smoking_duration == pytest.approx(30.0)
        assert sample.smoking_intensity == pytest.approx(20.0)
        assert sample.smoking_quit_time == pytest.approx(5.0)
        assert sample.smoking_status == 0
        assert sample.ct_scan_dir == "/tmp/scans"
        assert sample.six_year_risk is None

    def test_has_expected_field_count(self):
        assert len(fields(SybilInputData)) == 13

    def test_is_mutable(self, sample):
        sample.age = 70
        assert sample.age == 70

    def test_asdict_contains_all_fields(self, sample):
        d = asdict(sample)
        assert set(d.keys()) == {
            "age",
            "bmi",
            "copd",
            "education",
            "ethnicity",
            "family_lc_history",
            "personal_cancer_history",
            "smoking_duration",
            "smoking_intensity",
            "smoking_quit_time",
            "smoking_status",
            "ct_scan_dir",
            "six_year_risk",
        }

    def test_equality(self, sample):
        duplicate = SybilInputData(
            age=65,
            bmi=27.5,
            copd=0,
            education=3,
            ethnicity=1,
            family_lc_history=0,
            personal_cancer_history=1,
            smoking_duration=30.0,
            smoking_intensity=20.0,
            smoking_quit_time=5.0,
            smoking_status=0,
            ct_scan_dir="/tmp/scans",
            six_year_risk=None,
        )
        assert sample == duplicate

    def test_inequality_on_single_field(self, sample):
        other = SybilInputData(
            age=70,  # different
            bmi=27.5,
            copd=0,
            education=3,
            ethnicity=1,
            family_lc_history=0,
            personal_cancer_history=1,
            smoking_duration=30.0,
            smoking_intensity=20.0,
            smoking_quit_time=5.0,
            smoking_status=0,
            ct_scan_dir="/tmp/scans",
            six_year_risk=None,
        )
        assert sample != other

    def test_missing_required_field_raises(self):
        with pytest.raises(TypeError):
            SybilInputData(age=65)  # all other fields missing


# ── RiskResult ────────────────────────────────────────────────────────────────


class TestRiskResult:
    @pytest.fixture
    def result(self):
        return RiskResult(
            yearly_scores=[0.01, 0.02, 0.03, 0.04, 0.05, 0.06],
            epi_score=0.123,
        )

    def test_fields_stored(self, result):
        assert result.yearly_scores == [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
        assert result.epi_score == pytest.approx(0.123)

    def test_has_expected_field_count(self):
        assert len(fields(RiskResult)) == 2

    def test_is_mutable(self, result):
        result.epi_score = 0.5
        assert result.epi_score == pytest.approx(0.5)

    def test_equality(self, result):
        duplicate = RiskResult(
            yearly_scores=[0.01, 0.02, 0.03, 0.04, 0.05, 0.06],
            epi_score=0.123,
        )
        assert result == duplicate

    def test_inequality(self, result):
        other = RiskResult(
            yearly_scores=[0.01, 0.02, 0.03, 0.04, 0.05, 0.99],
            epi_score=0.123,
        )
        assert result != other

    def test_asdict(self, result):
        d = asdict(result)
        assert "yearly_scores" in d
        assert "epi_score" in d

    def test_empty_yearly_scores(self):
        r = RiskResult(yearly_scores=[], epi_score=0.0)
        assert r.yearly_scores == []

    def test_six_year_score_is_last_element(self, result):
        assert result.yearly_scores[-1] == pytest.approx(0.06)
