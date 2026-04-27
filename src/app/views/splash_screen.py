"""Startup splash screen shown while the Sybil model loads.

Usage (in main.py)
------------------
    root.withdraw()                         # hide main window
    splash = SplashScreen(root, bus)        # show splash
    root.after(100, sybil_ctrl.load_model)  # start loading
    root.mainloop()
    # SplashScreen subscribes to "model_ready" and calls root.deiconify()
    # automatically when the model finishes loading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.utils.helpers import center_window

if TYPE_CHECKING:
    from app.utils.event_bus import AppEvent, EventBus


class SplashScreen:
    """Centered toplevel splash that blocks until the model is ready.

    Subscribes to the EventBus and reacts to two event types:
      - ``log``        → updates the status line
      - ``model_ready``→ closes the splash and reveals the main window
      - ``model_error``→ shows an error message with a Quit button
    """

    _WIDTH = 480
    _HEIGHT = 280

    def __init__(self, root: ctk.CTk, bus: EventBus) -> None:
        self._root = root
        self._bus = bus

        self._win = ctk.CTkToplevel(root)
        self._win.title("Loading…")
        self._win.resizable(False, False)
        self._win.protocol("WM_DELETE_WINDOW", lambda: None)  # prevent manual close

        self._build()

        # Size to content and centre on screen.
        center_window(self._win, width=self._WIDTH, height=self._HEIGHT)

        # Keep on top of the (hidden) root
        self._win.lift()
        self._win.focus_force()
        self._win.grab_set()

        bus.subscribe(self._handle_event)

    # ── build ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = ctk.CTkFrame(self._win, fg_color=("gray95", "#1A1F2E"))
        outer.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            inner,
            text="Lung Cancer Risk Model",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            inner,
            text="Powered by Sybil · EPI Ensemble",
            font=ctk.CTkFont(size=13),
            text_color="gray60",
        ).pack(pady=(0, 28))

        self._bar = ctk.CTkProgressBar(inner, width=340, height=8)
        self._bar.pack()
        self._bar.configure(mode="indeterminate")
        self._bar.start()

        self._status = ctk.CTkLabel(
            inner,
            text="Loading model weights…",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self._status.pack(pady=(10, 0))

        ctk.CTkLabel(
            inner,
            text="First run: model weights will be downloaded to ~/.sybil/",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        ).pack(pady=(6, 0))

    # ── event handling ──────────────────────────────────────────────────────

    def _handle_event(self, event: AppEvent) -> None:
        if event.type == "log" and event.message:
            self._status.configure(text=event.message)

        elif event.type == "model_ready":
            self._close_and_show()

        elif event.type == "model_error":
            self._show_error(event.message or "Model failed to load.")

    def _close_and_show(self) -> None:
        self._bar.stop()
        self._win.grab_release()
        self._win.destroy()
        self._root.deiconify()

    def _show_error(self, message: str) -> None:
        """Replace the progress bar with an error message + quit button."""
        self._bar.stop()
        self._bar.configure(mode="determinate")
        self._bar.set(0)

        self._status.configure(
            text=f"Error: {message}",
            text_color=("#C62828", "#f7c485"),
        )

        ctk.CTkButton(
            self._win,
            text="Quit",
            width=100,
            command=self._root.quit,
        ).place(relx=0.5, rely=0.88, anchor="center")
