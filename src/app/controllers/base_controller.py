from app.utils.event_bus import AppEvent, EventBus


class BaseController:
    def __init__(self, root, bus: EventBus):
        self.root = root
        self.bus = bus

    def _emit(self, event: AppEvent):
        self.bus.emit(event)

    def _log(self, message: str, level: str = "INFO"):
        self._emit(AppEvent(type="log", message=message, level=level))

    def _progress(self, value: float):
        self._emit(AppEvent(type="progress", value=value))

    def _error(self, message: str):
        self._emit(AppEvent(type="log", message=message, level="ERROR"))
        self._emit(AppEvent(type="ui_state", message="error"))

    def _warn(self, message: str):
        self._emit(AppEvent(type="log", message=message, level="WARNING"))

    def _set_state(self, state: str):
        self._emit(AppEvent(type="ui_state", message=state))
