import subprocess
import sys
import tkinter.font as tkfont
import webbrowser
from pathlib import Path

import customtkinter as ctk

from app.config.settings import PROJECT_ROOT


def get_mono_font(size=14):
    available = set(tkfont.families())

    candidates = [
        "Cascadia Code",
        "SF Mono",
        "Menlo",
        "Consolas",
        "DejaVu Sans Mono",
        "Liberation Mono",
        "Courier New",
    ]

    for font in candidates:
        if font in available:
            return ctk.CTkFont(family=font, size=size)

    return ctk.CTkFont(family="Courier New", size=size)


def resolve_color(light: str, dark: str) -> str:
    return dark if ctk.get_appearance_mode() == "Dark" else light


def open_url(url: str) -> None:
    if sys.platform.startswith("linux"):
        try:
            subprocess.Popen(["xdg-open", url])
        except FileNotFoundError:
            webbrowser.open(url)  # fallback if xdg-open not available
    else:
        webbrowser.open(url)


def bounded_float(label, min_val, max_val):
    def check(val):
        f = float(val)
        if f < min_val or f > max_val:
            raise ValueError(f"{label} must be between {min_val} and {max_val}")
        return f

    return check


def center_window(
    win,
    fraction: float = 1.0,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """Resize *win* and centre it on the screen.

    Size is resolved in this order:
      1. Explicit *width* / *height* if both are provided.
      2. *fraction* of the screen when fraction < 1.0.
      3. The window's own requested size (winfo_req*) as the default.

    Args:
        win:      Any Tk/CTk window (CTk, CTkToplevel, Toplevel ...).
        fraction: Proportion of the screen to occupy (0 < fraction <= 1).
        width:    Explicit pixel width (overrides fraction).
        height:   Explicit pixel height (overrides fraction).
    """
    win.update_idletasks()

    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()

    if width is not None and height is not None:
        w, h = width, height
    elif fraction < 1.0:
        w = int(sw * fraction)
        h = int(sh * fraction)
    else:
        # winfo_reqwidth/height returns the size Tk calculated from widget
        # layout -- reliable even before the window has been displayed.
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()

    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


def resource_path(*parts):
    base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else PROJECT_ROOT
    return base.joinpath(*parts)


def validate_ct_path(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "Path does not exist"
    if not path.is_dir():
        return False, "Not a directory"
    if not any(path.iterdir()):
        return False, "Directory is empty"
    return True, ""
