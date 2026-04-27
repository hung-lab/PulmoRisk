def bounded_float(label, min_val, max_val):
    def check(val):
        f = float(val)
        if f < min_val or f > max_val:
            raise ValueError(f"{label} must be in [{min_val}, {max_val}]")
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
