"""Tests for run_sybil_pipeline's CT-folder vs precomputed-risk branching."""

from unittest.mock import MagicMock, patch

import pytest

from app.models.individual_model import SybilInputData
from app.utils.dicom_series import DicomSeries
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
        score, series_label = run_sybil_pipeline(None, individual)
        assert 0.0 < score < 1.0
        assert series_label is None

    def test_higher_precomputed_risk_scores_higher(self, base_patient_kwargs):
        low, _ = run_sybil_pipeline(
            None,
            SybilInputData(**base_patient_kwargs, ct_scan_dir=None, six_year_risk=0.01),
        )
        high, _ = run_sybil_pipeline(
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


class TestMultiSeriesAutoSelection:
    """A multi-series folder picks the series with the most slices, with
    no UI to ask — batch mode has no user to prompt."""

    def test_picks_series_with_most_slices(self, base_patient_kwargs, tmp_path):
        small = DicomSeries(
            series_uid="1", description="Small series", series_number=1,
            files=["a.dcm", "b.dcm"],
        )
        large = DicomSeries(
            series_uid="2", description="Large series", series_number=2,
            files=["c.dcm", "d.dcm", "e.dcm"],
        )

        individual = SybilInputData(
            **base_patient_kwargs, ct_scan_dir=str(tmp_path), six_year_risk=None
        )

        mock_model = MagicMock()
        mock_model.predict.return_value.scores = [[0.1, 0.1, 0.1, 0.1, 0.1, 0.05]]

        with (
            patch(
                "app.utils.sybil_inference.find_dicom_series",
                return_value=[small, large],
            ),
            patch("app.utils.sybil_inference.Serie") as mock_serie,
        ):
            score, series_label = run_sybil_pipeline(mock_model, individual)

        mock_serie.assert_called_once_with(large.files)
        assert series_label == "Large series - 3 slices"
        assert 0.0 < score < 1.0
