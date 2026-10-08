"""Tests for run_sybil_pipeline's CT-folder vs precomputed-risk branching."""

import pytest

from app.models.individual_model import SybilInputData
from app.utils.sybil_inference import run_sybil_pipeline


@pytest.fixture
def base_patient_kwargs():
    return dict(
        age=65,
        bmi=27.0,
        copd=0,
        education=3,
        ethnicity="White",
        family_lc_history=0,
        personal_cancer_history=0,
        smoking_duration=30.0,
        smoking_intensity=20.0,
        smoking_quit_time=5.0,
        smoking_status=0,
    )


class TestPrecomputedRiskSkipsCtInference:
    def test_does_not_require_a_model(self, base_patient_kwargs):
        """model=None proves CT inference is never touched for this row."""
        individual = SybilInputData(
            **base_patient_kwargs, ct_scan_dir=None, six_year_risk=0.05
        )
        score = run_sybil_pipeline(None, individual)
        assert 0.0 < score < 1.0

    def test_higher_precomputed_risk_scores_higher(self, base_patient_kwargs):
        low = run_sybil_pipeline(
            None,
            SybilInputData(**base_patient_kwargs, ct_scan_dir=None, six_year_risk=0.01),
        )
        high = run_sybil_pipeline(
            None,
            SybilInputData(**base_patient_kwargs, ct_scan_dir=None, six_year_risk=0.9),
        )
        assert high > low


class TestCtFolderModeStillValidatesPath:
    def test_missing_folder_raises(self, base_patient_kwargs, tmp_path):
        individual = SybilInputData(
            **base_patient_kwargs,
            ct_scan_dir=str(tmp_path / "does_not_exist"),
            six_year_risk=None,
        )
        with pytest.raises(ValueError, match="does not exist"):
            run_sybil_pipeline(None, individual)

    def test_empty_folder_raises(self, base_patient_kwargs, tmp_path):
        individual = SybilInputData(
            **base_patient_kwargs, ct_scan_dir=str(tmp_path), six_year_risk=None
        )
        with pytest.raises(ValueError, match="No files found"):
            run_sybil_pipeline(None, individual)
