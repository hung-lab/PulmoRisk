import customtkinter as ctk

from app.controllers.base_controller import BaseController
from app.utils.event_bus import AppEvent, EventBus


class AppController(BaseController):
    """Handles top-level UI events: layout toggles, theme, lifecycle."""

    def __init__(self, root, bus: EventBus, split_view, sybil_form):
        super().__init__(root, bus)
        self._split = split_view
        self._form = sybil_form
        bus.subscribe(self._handle_event)

    def _handle_event(self, event: AppEvent):
        if event.type == "ui_toggle":
            if event.message == "log_panel":
                self._split.toggle_right_panel()

        elif event.type == "ui_state":
            if event.message in ("running", "running_single", "running_batch"):
                self._split.lock_tabs()
            elif event.message in ("idle", "error"):
                self._split.unlock_tabs()

        elif event.type == "action":
            if event.message == "new_run":
                self._form.reset()

        elif event.type == "ui_theme":
            ctk.set_appearance_mode(event.message or "System")

        elif event.type == "app" and event.message == "quit":
            self.root.quit()

    # called by menubar view
    def toggle_log(self):
        self.bus.emit(AppEvent(type="ui_toggle", message="log_panel"))

    def new_run(self):
        self.bus.emit(AppEvent(type="action", message="new_run"))

    def change_appearance(self, mode: str):
        self.bus.emit(AppEvent(type="ui_theme", message=mode))

    def quit_app(self):
        self.bus.emit(AppEvent(type="app", message="quit"))
