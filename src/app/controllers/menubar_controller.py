from __future__ import annotations

from typing import TYPE_CHECKING

from app.controllers.base_controller import BaseController

if TYPE_CHECKING:
    from app.controllers.app_controller import AppController
    from app.utils.event_bus import EventBus
    from app.views.components.menu_bar import MenuBar


class MenuBarController(BaseController):
    """Event-driven controller for MenuBar."""

    def __init__(self, root: object, bus: EventBus, controller: AppController) -> None:
        super().__init__(root, bus)
        self.controller = controller
        self._menu_bar: MenuBar | None = None
        bus.subscribe(self._handle_event)

    def toggle_log(self):
        self.controller.toggle_log()

    def new_run(self):
        self.controller.new_run()

    def change_appearance(self, mode: str):
        self.controller.change_appearance(mode)

    def quit_app(self):
        self.controller.quit_app()

    def set_menu_bar(self, menu_bar: MenuBar) -> None:
        self._menu_bar = menu_bar

    def _handle_event(self, event) -> None:
        if event.type == "ui_state" and self._menu_bar:
            self._menu_bar.set_enabled(
                event.message not in ("running", "running_single", "running_batch")
            )
