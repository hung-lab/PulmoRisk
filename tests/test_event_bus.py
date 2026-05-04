"""Tests for EventBus."""

from unittest.mock import MagicMock

import pytest

from app.utils.event_bus import AppEvent, EventBus


@pytest.fixture
def root():
    """Fake Tk root that captures after() callbacks and runs them immediately."""
    r = MagicMock()
    # Execute the scheduled callback immediately so we don't need a real mainloop
    r.after.side_effect = lambda delay, fn: fn()
    return r


@pytest.fixture
def bus(root):
    return EventBus(root)


# ── AppEvent defaults ─────────────────────────────────────────────────────────


class TestAppEvent:
    def test_defaults(self):
        e = AppEvent(type="log")
        assert e.message is None
        assert e.level == "INFO"
        assert e.value is None
        assert e.data is None

    def test_all_fields(self):
        e = AppEvent(
            type="result", message="done", level="SUCCESS", value=1.0, data={"x": 1}
        )
        assert e.type == "result"
        assert e.message == "done"
        assert e.level == "SUCCESS"
        assert e.value == 1.0
        assert e.data == {"x": 1}


# ── subscribe / unsubscribe ───────────────────────────────────────────────────


class TestSubscribe:
    def test_unsubscribe_nonexistent_handler_does_not_raise(self, bus):
        handler = MagicMock()
        bus.unsubscribe(handler)  # never subscribed — should not raise


# ── emit ordering ─────────────────────────────────────────────────────────────


# ── error isolation ───────────────────────────────────────────────────────────


# ── empty queue ───────────────────────────────────────────────────────────────
