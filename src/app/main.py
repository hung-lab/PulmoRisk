"""Application entry point."""

import os

import customtkinter as ctk

from app.config.settings import BASE_PATH
from app.controllers.app_controller import AppController
from app.controllers.menubar_controller import MenuBarController
from app.controllers.sybil_controller import SybilController
from app.utils.event_bus import EventBus
from app.utils.helpers import center_window
from app.views.components.log_panel import LogPanel
from app.views.components.menu_bar import MenuBar
from app.views.components.split_view import SplitView
from app.views.main_view import MainWindow
from app.views.splash_screen import SplashScreen
from app.views.sybil_view import SybilView


def main() -> None:

    ctk.set_appearance_mode("System")

    full_theme_path = os.path.join(BASE_PATH, "assets", "themes", "BlueEmber.json")
    ctk.set_default_color_theme(full_theme_path)

    root = ctk.CTk()
    root.title("CustomTkinter App")
    center_window(root, fraction=0.9)

    # Hide the main window until the model has finished loading.
    root.withdraw()

    bus = EventBus(root)
    bus.start()

    split = SplitView(root)

    log_panel = LogPanel(split.right)
    bus.subscribe(log_panel.handle_event)

    # ── Views — each gets its own frame inside split.middle ───────────────
    home_frame = ctk.CTkFrame(split.middle, fg_color="transparent", border_width=0)
    MainWindow(home_frame)
    split.add_view("Home", home_frame, "house.png")

    sybil_ctrl = SybilController(root, bus)
    sybil_frame = ctk.CTkFrame(split.middle, fg_color="transparent", border_width=0)
    sybil_form = SybilView(sybil_frame, sybil_ctrl)
    bus.subscribe(sybil_form.handle_event)
    split.add_view("Sybil Risk Model", sybil_frame, "house.png")

    # ── Controllers ───────────────────────────────────────────────────────
    app_ctrl = AppController(root, bus, split, sybil_form)

    menubar_ctrl = MenuBarController(root, bus, app_ctrl)
    MenuBar(root, menubar_ctrl)

    # ── Splash screen — shown before the main window, closes on model_ready
    # Must be created AFTER all bus subscribers are registered so splash
    # also sees all log events during model loading.
    SplashScreen(root, bus)

    # ── Load model AFTER all subscribers are registered ────────────────────
    # root.after ensures the mainloop is running and the UI is fully rendered
    # before the background thread starts emitting log events.
    root.after(100, sybil_ctrl.load_model)

    root.mainloop()


if __name__ == "__main__":
    main()
