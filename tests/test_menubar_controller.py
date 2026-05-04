"""Tests for MenuBarController."""

from unittest.mock import MagicMock

import pytest

from app.controllers.menubar_controller import MenuBarController
from app.utils.event_bus import AppEvent


@pytest.fixture
def bus():
    return MagicMock()


@pytest.fixture
def app_controller():
    return MagicMock()


@pytest.fixture
def controller(bus, app_controller):
    return MenuBarController(root=MagicMock(), bus=bus, controller=app_controller)


# ── delegation ────────────────────────────────────────────────────────────────


class TestToggleLog:
    def test_delegates_to_app_controller(self, controller, app_controller):
        controller.toggle_log()
        app_controller.toggle_log.assert_called_once()


class TestNewRun:
    def test_delegates_to_app_controller(self, controller, app_controller):
        controller.new_run()
        app_controller.new_run.assert_called_once()


class TestChangeAppearance:
    def test_delegates_with_mode(self, controller, app_controller):
        controller.change_appearance("Dark")
        app_controller.change_appearance.assert_called_once_with("Dark")

    def test_delegates_light(self, controller, app_controller):
        controller.change_appearance("Light")
        app_controller.change_appearance.assert_called_once_with("Light")


class TestQuitApp:
    def test_delegates_to_app_controller(self, controller, app_controller):
        controller.quit_app()
        app_controller.quit_app.assert_called_once()


# ── menu bar locking ──────────────────────────────────────────────────────────


class TestSetMenuBar:
    def test_set_menu_bar_stores_reference(self, controller):
        menu_bar = MagicMock()
        controller.set_menu_bar(menu_bar)
        assert controller._menu_bar is menu_bar


class TestHandleEvent:
    def test_running_state_disables_menu(self, controller):
        menu_bar = MagicMock()
        controller.set_menu_bar(menu_bar)
        controller._handle_event(AppEvent(type="ui_state", message="running"))
        menu_bar.set_enabled.assert_called_once_with(False)

    def test_idle_state_enables_menu(self, controller):
        menu_bar = MagicMock()
        controller.set_menu_bar(menu_bar)
        controller._handle_event(AppEvent(type="ui_state", message="idle"))
        menu_bar.set_enabled.assert_called_once_with(True)

    def test_error_state_enables_menu(self, controller):
        menu_bar = MagicMock()
        controller.set_menu_bar(menu_bar)
        controller._handle_event(AppEvent(type="ui_state", message="error"))
        menu_bar.set_enabled.assert_called_once_with(True)

    def test_no_menu_bar_set_does_not_raise(self, controller):
        # Should not raise even if set_menu_bar was never called
        controller._handle_event(AppEvent(type="ui_state", message="running"))

    def test_non_ui_state_event_ignored(self, controller):
        menu_bar = MagicMock()
        controller.set_menu_bar(menu_bar)
        controller._handle_event(AppEvent(type="log", message="hello"))
        menu_bar.set_enabled.assert_not_called()

    def test_subscribes_to_bus_on_init(self, bus, app_controller):
        MenuBarController(root=MagicMock(), bus=bus, controller=app_controller)
        bus.subscribe.assert_called()
