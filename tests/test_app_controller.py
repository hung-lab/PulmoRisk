"""Tests for AppController."""

from unittest.mock import MagicMock, patch

import pytest

from app.controllers.app_controller import AppController
from app.utils.event_bus import AppEvent


@pytest.fixture
def bus():
    return MagicMock()


@pytest.fixture
def split_view():
    return MagicMock()


@pytest.fixture
def sybil_form():
    return MagicMock()


@pytest.fixture
def controller(bus, split_view, sybil_form):
    return AppController(
        root=MagicMock(),
        bus=bus,
        split_view=split_view,
        sybil_form=sybil_form,
    )


# ── public API → event emission ───────────────────────────────────────────────


class TestToggleLog:
    def test_emits_ui_toggle_log_panel(self, controller, bus):
        controller.toggle_log()
        event = bus.emit.call_args[0][0]
        assert event.type == "ui_toggle"
        assert event.message == "log_panel"


class TestNewRun:
    def test_emits_action_new_run(self, controller, bus):
        controller.new_run()
        event = bus.emit.call_args[0][0]
        assert event.type == "action"
        assert event.message == "new_run"


class TestChangeAppearance:
    def test_emits_ui_theme_with_mode(self, controller, bus):
        controller.change_appearance("Dark")
        event = bus.emit.call_args[0][0]
        assert event.type == "ui_theme"
        assert event.message == "Dark"

    def test_emits_ui_theme_light(self, controller, bus):
        controller.change_appearance("Light")
        assert bus.emit.call_args[0][0].message == "Light"

    def test_emits_ui_theme_system(self, controller, bus):
        controller.change_appearance("System")
        assert bus.emit.call_args[0][0].message == "System"


class TestQuitApp:
    def test_emits_app_quit(self, controller, bus):
        controller.quit_app()
        event = bus.emit.call_args[0][0]
        assert event.type == "app"
        assert event.message == "quit"


# ── _handle_event ─────────────────────────────────────────────────────────────


class TestHandleEventUiToggle:
    def test_toggle_log_panel_calls_split_view(self, controller, split_view):
        controller._handle_event(AppEvent(type="ui_toggle", message="log_panel"))
        split_view.toggle_right_panel.assert_called_once()

    def test_unknown_ui_toggle_message_does_nothing(self, controller, split_view):
        controller._handle_event(AppEvent(type="ui_toggle", message="unknown"))
        split_view.toggle_right_panel.assert_not_called()


class TestHandleEventAction:
    def test_new_run_resets_form(self, controller, sybil_form):
        controller._handle_event(AppEvent(type="action", message="new_run"))
        sybil_form.reset.assert_called_once()

    def test_unknown_action_does_not_reset_form(self, controller, sybil_form):
        controller._handle_event(AppEvent(type="action", message="something_else"))
        sybil_form.reset.assert_not_called()


class TestHandleEventUiTheme:
    @patch("app.controllers.app_controller.ctk")
    def test_sets_appearance_mode(self, mock_ctk, controller):
        controller._handle_event(AppEvent(type="ui_theme", message="Dark"))
        mock_ctk.set_appearance_mode.assert_called_once_with("Dark")

    @patch("app.controllers.app_controller.ctk")
    def test_none_message_defaults_to_system(self, mock_ctk, controller):
        controller._handle_event(AppEvent(type="ui_theme", message=None))
        mock_ctk.set_appearance_mode.assert_called_once_with("System")


class TestHandleEventApp:
    def test_quit_calls_root_quit(self, controller):
        controller._handle_event(AppEvent(type="app", message="quit"))
        controller.root.quit.assert_called_once()

    def test_non_quit_message_does_not_quit(self, controller):
        controller._handle_event(AppEvent(type="app", message="other"))
        controller.root.quit.assert_not_called()


class TestHandleEventUiState:
    def test_running_locks_tabs(self, controller, split_view):
        controller._handle_event(AppEvent(type="ui_state", message="running"))
        split_view.lock_tabs.assert_called_once()

    def test_idle_unlocks_tabs(self, controller, split_view):
        controller._handle_event(AppEvent(type="ui_state", message="idle"))
        split_view.unlock_tabs.assert_called_once()

    def test_error_unlocks_tabs(self, controller, split_view):
        controller._handle_event(AppEvent(type="ui_state", message="error"))
        split_view.unlock_tabs.assert_called_once()


class TestBusSubscription:
    def test_subscribes_to_bus_on_init(self, bus, split_view, sybil_form):
        AppController(
            root=MagicMock(),
            bus=bus,
            split_view=split_view,
            sybil_form=sybil_form,
        )
        bus.subscribe.assert_called()
