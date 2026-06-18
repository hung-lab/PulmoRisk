"""Application entry point."""

import platform
import threading

import customtkinter as ctk
from PIL import Image, ImageTk

from app.controllers.app_controller import AppController
from app.controllers.integral_controller import IntegralController
from app.controllers.menubar_controller import MenuBarController
from app.controllers.sybil_controller import SybilController
from app.utils.event_bus import EventBus
from app.utils.helpers import center_window, get_mono_font, resource_path
from app.views.components.log_panel import LogPanel
from app.views.components.menu_bar import MenuBar
from app.views.components.split_view import SplitView
from app.views.integral_view import IntegralView
from app.views.main_view import MainWindow
from app.views.splash_screen import SplashScreen
from app.views.sybil_view import SybilView


def _set_icon(root: ctk.CTk) -> None:
    """Set taskbar/dock icon cross-platform."""

    system = platform.system()

    try:
        if system == "Windows":
            # Windows uses .ico natively via iconbitmap
            ico_path = resource_path("assets", "icons", "app_icon.ico")
            root.iconbitmap(str(ico_path))

        elif system == "Darwin":
            # Mac — iconbitmap doesn't work, use iconphoto
            # The dock icon is better set via the .app bundle Info.plist
            # but iconphoto works for the window titlebar
            img_path = resource_path("assets", "icons", "app_icon.png")
            img = ImageTk.PhotoImage(Image.open(img_path).resize((512, 512)))
            root.iconphoto(True, img)
            root._icon_ref = img  # prevent garbage collection

        else:
            # Linux — iconphoto with multiple sizes for best rendering
            img_path = resource_path("assets", "icons", "app_icon.png")
            base = Image.open(img_path)
            icons = [
                ImageTk.PhotoImage(base.resize((sz, sz)))
                for sz in (16, 32, 48, 64, 128, 256)
            ]
            root.iconphoto(True, *icons)
            root._icon_refs = icons  # prevent garbage collection
    except Exception as e:
        print(f"[ICON] Failed to set icon: {e}")


def main() -> None:
    ctk.set_appearance_mode("System")

    full_theme_path = resource_path("assets", "themes", "AccessibleContrast.json")
    ctk.set_default_color_theme(full_theme_path)

    if platform.system() == "Linux":
        ctk.deactivate_automatic_dpi_awareness()
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

    root = ctk.CTk()

    root.option_add("*Font", get_mono_font())
    root.title("PulmoRisk")
    _set_icon(root)
    center_window(root, fraction=0.9)

    # Hide the main window until the Sybil model has finished loading.
    root.withdraw()

    bus = EventBus(root)
    bus.start()

    split = SplitView(root)

    log_panel = LogPanel(split.log_panel)
    bus.subscribe(log_panel.handle_event)

    # ── Views — each gets its own frame inside tab views ───────────────
    MainWindow(split.home_tab)

    sybil_ctrl = SybilController(root, bus)
    sybil_form = SybilView(split.sybil_tab, sybil_ctrl)
    bus.subscribe(sybil_form.handle_event)

    integral_ctrl = IntegralController(root, bus)
    integral_form = IntegralView(split.integral_tab, integral_ctrl)
    bus.subscribe(integral_form.handle_event)

    # ── Controllers ───────────────────────────────────────────────────────
    app_ctrl = AppController(root, bus, split, sybil_form, integral_form)

    menubar_ctrl = MenuBarController(root, bus, app_ctrl)
    menu = MenuBar(root, menubar_ctrl)
    menubar_ctrl.set_menu_bar(menu)

    # ── Splash screen — shown before the main window, closes on model_ready
    # Must be created AFTER all bus subscribers are registered so splash
    # also sees all log events during model loading.
    SplashScreen(root, bus)

    # ── Load model AFTER all subscribers are registered ────────────────────
    # root.after ensures the mainloop is running and the UI is fully rendered
    # before the background thread starts emitting log events.
    root.after(100, sybil_ctrl.load_model)

    root.after(
        100,
        lambda: threading.Thread(
            target=app_ctrl.check_and_install_integral, daemon=True
        ).start(),
    )

    def on_close():
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
