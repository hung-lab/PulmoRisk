from app.utils.event_bus import AppEvent, EventBus


class BaseController:
    def __init__(self, root, bus: EventBus):
        self.root = root
        self.bus = bus

    def _emit(self, event: AppEvent):
        self.bus.emit(event)

    def _log(self, message: str, level: str = "INFO", data: dict | None = None):
        self._emit(AppEvent(type="log", message=message, level=level, data=data))

    def _progress(self, value: float):
        self._emit(AppEvent(type="progress", value=value))

    def _error(self, message: str):
        self._emit(AppEvent(type="log", message=message, level="ERROR"))
        self._emit(AppEvent(type="ui_state", message="error"))

    def _log_error(self, message: str):
        """Log-only error — unlike _error(), this does not flip ui_state to
        "error". A batch worker uses this for a single row's failure, since
        that row is already handled (an error row in the output); the
        "error" ui_state is for a run that stopped entirely, and would
        otherwise hide the batch overlay/results while the worker thread
        keeps processing the remaining rows."""
        self._emit(AppEvent(type="log", message=message, level="ERROR"))

    def _warn(self, message: str):
        self._emit(AppEvent(type="log", message=message, level="WARNING"))

    def _set_state(self, state: str):
        self._emit(AppEvent(type="ui_state", message=state))
