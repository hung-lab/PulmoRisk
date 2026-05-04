"""Tests for BaseController."""

from unittest.mock import MagicMock

import pytest

from app.controllers.base_controller import BaseController
from app.utils.event_bus import AppEvent


@pytest.fixture
def bus():
    return MagicMock()


@pytest.fixture
def controller(bus):
    return BaseController(root=MagicMock(), bus=bus)


class TestEmit:
    def test_emit_puts_event_on_bus(self, controller, bus):
        event = AppEvent(type="log", message="hello")
        controller._emit(event)
        bus.emit.assert_called_once_with(event)


class TestLog:
    def test_log_emits_log_event_with_default_level(self, controller, bus):
        controller._log("something happened")
        event = bus.emit.call_args[0][0]
        assert event.type == "log"
        assert event.message == "something happened"
        assert event.level == "INFO"

    def test_log_emits_log_event_with_custom_level(self, controller, bus):
        controller._log("watch out", "WARNING")
        event = bus.emit.call_args[0][0]
        assert event.level == "WARNING"


class TestError:
    def test_error_emits_log_event_with_error_level(self, controller, bus):
        controller._error("something broke")
        calls = bus.emit.call_args_list
        log_event = calls[0][0][0]
        assert log_event.type == "log"
        assert log_event.message == "something broke"
        assert log_event.level == "ERROR"

    def test_error_also_emits_ui_state_error(self, controller, bus):
        controller._error("something broke")
        calls = bus.emit.call_args_list
        state_event = calls[1][0][0]
        assert state_event.type == "ui_state"
        assert state_event.message == "error"

    def test_error_emits_exactly_two_events(self, controller, bus):
        controller._error("oops")
        assert bus.emit.call_count == 2


class TestProgress:
    def test_progress_emits_progress_event(self, controller, bus):
        controller._progress(0.5)
        event = bus.emit.call_args[0][0]
        assert event.type == "progress"
        assert event.value == 0.5

    def test_progress_zero(self, controller, bus):
        controller._progress(0.0)
        assert bus.emit.call_args[0][0].value == 0.0

    def test_progress_one(self, controller, bus):
        controller._progress(1.0)
        assert bus.emit.call_args[0][0].value == 1.0


class TestSetState:
    def test_set_state_emits_ui_state_event(self, controller, bus):
        controller._set_state("running")
        event = bus.emit.call_args[0][0]
        assert event.type == "ui_state"
        assert event.message == "running"

    def test_set_state_idle(self, controller, bus):
        controller._set_state("idle")
        assert bus.emit.call_args[0][0].message == "idle"
