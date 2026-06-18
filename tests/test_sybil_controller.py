"""Tests for SybilController."""

import sys
import threading
from unittest.mock import MagicMock, patch

# Mock sybil before it's imported so cv2/libGL is never touched in tests
sys.modules["sybil"] = MagicMock()
sys.modules["sybil.serie"] = MagicMock()

import pytest  # noqa: E402

from app.controllers.sybil_controller import SybilController  # noqa: E402
from app.models.individual_model import SybilInputData  # noqa: E402


@pytest.fixture
def bus():
    return MagicMock()


@pytest.fixture
def controller(bus):
    return SybilController(root=MagicMock(), bus=bus)


@pytest.fixture
def pending():
    """A real SybilInputData so asdict() works inside _on_complete."""
    return SybilInputData(
        age=65,
        bmi=27.0,
        copd=0,
        education=3,
        ethnicity=1,
        family_lc_history=0,
        personal_cancer_history=0,
        smoking_duration=30.0,
        smoking_intensity=20.0,
        smoking_quit_time=5.0,
        smoking_status=0,
        ct_scan_dir="/tmp/scans",
    )


# ── load_model ────────────────────────────────────────────────────────────────


class TestLoadModel:
    @patch("app.controllers.sybil_controller.Sybil")
    def test_load_model_sets_model(self, mock_sybil, controller):
        mock_instance = MagicMock()
        mock_sybil.return_value = mock_instance

        done = threading.Event()

        def capture(event):
            if event.type in ("model_ready", "model_error"):
                done.set()

        controller.bus.emit.side_effect = capture
        controller.load_model()
        done.wait(timeout=5)

        assert controller._model is mock_instance

    @patch("app.controllers.sybil_controller.Sybil")
    def test_load_model_emits_model_ready(self, mock_sybil, controller):
        mock_sybil.return_value = MagicMock()

        done = threading.Event()
        emitted_types = []

        def capture(event):
            emitted_types.append(event.type)
            if event.type in ("model_ready", "model_error"):
                done.set()

        controller.bus.emit.side_effect = capture
        controller.load_model()
        done.wait(timeout=5)

        assert "model_ready" in emitted_types

    @patch("app.controllers.sybil_controller.Sybil", side_effect=RuntimeError("fail"))
    def test_load_model_emits_model_error_on_exception(self, mock_sybil, controller):
        done = threading.Event()
        emitted_types = []

        def capture(event):
            emitted_types.append(event.type)
            if event.type in ("model_ready", "model_error"):
                done.set()

        controller.bus.emit.side_effect = capture
        controller.load_model()
        done.wait(timeout=5)

        assert "model_error" in emitted_types

    @patch("app.controllers.sybil_controller.Sybil", side_effect=RuntimeError("msg"))
    def test_load_model_error_message_forwarded(self, mock_sybil, controller):
        done = threading.Event()
        error_event = []

        def capture(event):
            if event.type == "model_error":
                error_event.append(event)
                done.set()

        controller.bus.emit.side_effect = capture
        controller.load_model()
        done.wait(timeout=5)

        assert "msg" in error_event[0].message


# ── run — pre-flight validation ───────────────────────────────────────────────


class TestRunValidation:
    def test_run_without_model_emits_error(self, controller):
        controller._model = None
        controller.run(MagicMock(ct_scan_dir="/some/path"))

        error_events = [
            c[0][0]
            for c in controller.bus.emit.call_args_list
            if c[0][0].type == "log" and c[0][0].level == "ERROR"
        ]
        assert error_events

    def test_run_with_invalid_dir_emits_error(self, controller, tmp_path):
        controller._model = MagicMock()
        controller.run(MagicMock(ct_scan_dir=str(tmp_path / "nonexistent")))

        error_events = [
            c[0][0]
            for c in controller.bus.emit.call_args_list
            if c[0][0].type == "log" and c[0][0].level == "ERROR"
        ]
        assert error_events

    def test_run_with_empty_dir_emits_error(self, controller, tmp_path):
        controller._model = MagicMock()
        controller.run(MagicMock(ct_scan_dir=str(tmp_path)))

        error_events = [
            c[0][0]
            for c in controller.bus.emit.call_args_list
            if c[0][0].type == "log" and c[0][0].level == "ERROR"
        ]
        assert error_events


# ── _on_complete ──────────────────────────────────────────────────────────────


class TestOnComplete:
    @patch("app.controllers.sybil_controller.epi_input_from_individual_data")
    @patch("app.controllers.sybil_controller.calculate_sybil_epi_score")
    def test_on_complete_emits_result_event(
        self, mock_epi, mock_epi_input, controller, pending
    ):
        mock_epi.return_value = 0.15
        mock_epi_input.return_value = MagicMock()
        controller._pending = pending
        controller._infer_active = True

        yearly = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
        controller._on_complete(yearly)

        result_events = [
            c[0][0]
            for c in controller.bus.emit.call_args_list
            if c[0][0].type == "result"
        ]
        assert result_events
        assert result_events[0].data["yearly"] == yearly
        assert result_events[0].data["epi"] == pytest.approx(0.15)

    @patch("app.controllers.sybil_controller.epi_input_from_individual_data")
    @patch("app.controllers.sybil_controller.calculate_sybil_epi_score")
    def test_on_complete_emits_idle_state(
        self, mock_epi, mock_epi_input, controller, pending
    ):
        mock_epi.return_value = 0.10
        mock_epi_input.return_value = MagicMock()
        controller._pending = pending

        controller._on_complete([0.01] * 6)

        state_events = [
            c[0][0]
            for c in controller.bus.emit.call_args_list
            if c[0][0].type == "ui_state" and c[0][0].message == "idle"
        ]
        assert state_events

    @patch("app.controllers.sybil_controller.epi_input_from_individual_data")
    @patch("app.controllers.sybil_controller.calculate_sybil_epi_score")
    def test_on_complete_emits_progress_100(
        self, mock_epi, mock_epi_input, controller, pending
    ):
        mock_epi.return_value = 0.10
        mock_epi_input.return_value = MagicMock()
        controller._pending = pending

        controller._on_complete([0.01] * 6)

        progress_events = [
            c[0][0]
            for c in controller.bus.emit.call_args_list
            if c[0][0].type == "progress" and c[0][0].value == 1.0
        ]
        assert progress_events

    @patch("app.controllers.sybil_controller.epi_input_from_individual_data")
    @patch("app.controllers.sybil_controller.calculate_sybil_epi_score")
    def test_on_complete_stops_infer_active(
        self, mock_epi, mock_epi_input, controller, pending
    ):
        mock_epi.return_value = 0.10
        mock_epi_input.return_value = MagicMock()
        controller._pending = pending
        controller._infer_active = True

        controller._on_complete([0.01] * 6)

        assert controller._infer_active is False

    @patch(
        "app.controllers.sybil_controller.calculate_sybil_epi_score",
        side_effect=ValueError("bad input"),
    )
    @patch("app.controllers.sybil_controller.epi_input_from_individual_data")
    def test_on_complete_epi_error_emits_error(
        self, mock_epi_input, mock_epi, controller, pending
    ):
        mock_epi_input.return_value = MagicMock()
        controller._pending = pending

        controller._on_complete([0.01] * 6)

        error_events = [
            c[0][0]
            for c in controller.bus.emit.call_args_list
            if c[0][0].type == "log" and c[0][0].level == "ERROR"
        ]
        assert error_events
