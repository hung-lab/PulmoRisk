"""Startup splash screen shown while the Sybil model loads.

Usage (in main.py)
------------------
    root.withdraw()                         # hide main window
    splash = SplashScreen(root, bus)        # show splash
    root.after(100, sybil_ctrl.load_model)  # start loading
    root.mainloop()
    # SplashScreen subscribes to startup events and calls root.deiconify()
    # when both Sybil and Integral initialization have reached a terminal state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.config.settings import ERROR_COLOUR, ERROR_COLOUR_HOVER, SUCCESS_COLOUR
from app.utils.helpers import center_window
from app.utils.ui_config import SPACE_SM, SPACE_XL, SPACE_XS

if TYPE_CHECKING:
    from app.utils.event_bus import AppEvent, EventBus


class SplashScreen:
    """Centered startup splash shown until application initialization completes.

    The splash waits for both the Sybil model and INTEGRAL-Radiomics setup.
    If the Integral setup cannot be completed, the user can continue with
    that feature unavailable.
    """

    _WIDTH = 600
    _HEIGHT = 400

    @property
    def window(self) -> ctk.CTkToplevel:
        return self._win

    def __init__(self, root: ctk.CTk, bus: EventBus) -> None:
        self._root = root
        self._bus = bus

        self._sybil_done = False
        self._integral_done = False
        self._integral_error = False
        self._fatal_error = False
        self._closed = False
        self._elapsed = 0

        self._win = ctk.CTkToplevel(root)
        self._win.title("Loading…")
        self._win.resizable(False, False)
        self._win.protocol("WM_DELETE_WINDOW", lambda: None)  # prevent manual close

        self._continue_button: ctk.CTkButton | None = None

        self._build()

        # Size to content and centre on screen.
        center_window(self._win, width=self._WIDTH, height=self._HEIGHT)

        # Keep on top of the (hidden) root
        self._win.lift()
        self._win.focus_force()

        bus.subscribe(self._handle_event)
        self._tick()

    # ── build ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = ctk.CTkFrame(self._win)
        outer.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(outer, fg_color="transparent", border_width=0)
        inner.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            inner,
            text="Lung Cancer Risk Estimation",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(0, SPACE_XS))

        ctk.CTkLabel(
            inner,
            text="Powered by Sybil-Epi · INTEGRAL-Radiomics Ensemble",
            font=ctk.CTkFont(size=13),
            text_color="gray60",
        ).pack(pady=(0, SPACE_XL))

        self._bar = ctk.CTkProgressBar(inner, width=340, height=8)
        self._bar.pack()
        self._bar.configure(mode="indeterminate")
        self._bar.start()

        self._sybil_status = ctk.CTkLabel(
            inner,
            text="⏳ Loading Sybil model weights…",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor="w",
        )
        self._sybil_status.pack(pady=(SPACE_SM, 0), fill="x")

        self._integral_status = ctk.CTkLabel(
            inner,
            text="⏳ Checking R / INTEGRAL-Radiomics setup…",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor="w",
        )
        self._integral_status.pack(pady=(2, 0), fill="x")

        self._elapsed_label = ctk.CTkLabel(
            inner,
            text="0s elapsed",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self._elapsed_label.pack(pady=(SPACE_SM, 0))

        self._first_run_label = ctk.CTkLabel(
            inner,
            text=(
                "First run: model weights are downloaded to ~/.sybil/ and R "
                "packages may be installed — this can take a few minutes."
            ),
            font=ctk.CTkFont(size=11),
            text_color="gray50",
            justify="center",
            wraplength=400,
        )
        self._first_run_label.pack(pady=(SPACE_SM, 0))

    # ── elapsed timer ──────────────────────────────────────────────────

    def _tick(self) -> None:
        if self._closed:
            return
        self._elapsed += 1
        mins, secs = divmod(self._elapsed, 60)
        text = f"{mins}m {secs:02d}s elapsed" if mins else f"{secs}s elapsed"
        self._elapsed_label.configure(text=text)
        self._root.after(1000, self._tick)

    # ── event handling ──────────────────────────────────────────────────────

    def _handle_event(self, event: AppEvent) -> None:
        # Unsubscribed after close — guard against any in-flight events.
        if self._closed:
            return

        if event.type == "log" and event.message:
            if event.data and event.data.get("channel") == "integral":
                self._integral_status.configure(text=f"⏳ {event.message}")
            else:
                self._sybil_status.configure(text=f"⏳ {event.message}")

        elif event.type == "model_ready":
            self._sybil_done = True
            self._sybil_status.configure(
                text="✓ Sybil model ready", text_color=SUCCESS_COLOUR
            )
            self._maybe_finish()

        elif event.type == "model_error":
            self._fatal_error = True
            self._show_fatal_error(event.message or "Model failed to load.")

        elif event.type == "ui_state":
            if event.message in ("integral_radiomics_ready", "install_complete"):
                self._integral_done = True
                self._integral_status.configure(
                    text="✓ INTEGRAL-Radiomics ready", text_color=SUCCESS_COLOUR
                )
                self._maybe_finish()

            elif event.message == "install_failed":
                self._integral_done = True
                self._integral_error = True
                self._integral_status.configure(
                    text="✗ INTEGRAL-Radiomics install failed — see Activity Log. "
                    "That feature will be unavailable.",
                    text_color=ERROR_COLOUR,
                )
                self._maybe_finish()

            elif event.message == "R_missing":
                self._integral_done = True
                self._integral_error = True
                self._integral_status.configure(
                    text="✗ R not found — INTEGRAL-Radiomics will be unavailable.",
                    text_color=ERROR_COLOUR,
                )
                self._maybe_finish()

    # ── finish logic ──────────────────────────────────────────────────────

    def _maybe_finish(self) -> None:
        if self._fatal_error:
            return
        if not (self._sybil_done and self._integral_done):
            return

        if self._integral_error:
            self._show_continue()
        else:
            self._close_and_show()

    def _show_continue(self) -> None:
        if self._closed:
            return

        self._bar.stop()
        self._bar.configure(mode="determinate")
        self._bar.set(1.0)

        if self._continue_button is not None:
            return

        self._continue_button = ctk.CTkButton(
            self._win,
            text="Continue",
            width=120,
            command=self._close_and_show,
        )
        self._continue_button.place(
            relx=0.5,
            rely=0.88,
            anchor="center",
        )

    def _close_and_show(self) -> None:
        self._closed = True
        self._bus.unsubscribe(self._handle_event)
        self._bar.stop()
        self._win.grab_release()
        self._win.destroy()
        self._root.deiconify()

    def _show_fatal_error(self, message: str) -> None:
        self._bar.stop()
        self._bar.configure(mode="determinate")
        self._bar.set(0)

        self._sybil_status.configure(
            text=f"✗ Error: {message}", text_color=ERROR_COLOUR
        )

        ctk.CTkButton(
            self._win,
            text="Quit",
            width=100,
            command=self._root.quit,
        ).place(relx=0.5, rely=0.88, anchor="center")

    def show_r_setup(self) -> None:
        """Return the splash to the normal startup state while R setup runs."""

        # Remove the R-selection controls.
        self.hide_r_missing()

        # Restore normal startup information.
        self._elapsed_label.pack(pady=(SPACE_SM, 0))
        self._first_run_label.pack(pady=(SPACE_SM, 0))

        # Restore the progress bar.
        self._bar.configure(mode="indeterminate")
        self._bar.start()

        self._integral_status.configure(
            text="⏳ Setting up INTEGRAL-Radiomics…",
            text_color="gray60",
        )

    def show_r_missing(self, on_browse, on_cancel):
        """Show the R selection UI inside the startup splash."""

        self._bar.stop()
        self._bar.configure(mode="determinate")
        self._bar.set(0)

        self._elapsed_label.pack_forget()
        self._first_run_label.pack_forget()

        self._integral_status.configure(
            text="✗ R was not found",
            text_color=ERROR_COLOUR,
        )

        self._r_message = ctk.CTkLabel(
            self._win,
            text=(
                "INTEGRAL-Radiomics requires R.\n\n"
                "Rscript could not be found in the standard "
                "installation locations.\n\n"
                "If R is already installed, locate Rscript manually."
            ),
            justify="center",
            wraplength=450,
        )
        self._r_message.place(
            relx=0.5,
            rely=0.60,
            anchor="center",
        )

        self._r_error_label = ctk.CTkLabel(
            self._win,
            text="",
            text_color=ERROR_COLOUR,
        )
        self._r_error_label.place(
            relx=0.5,
            rely=0.70,
            anchor="center",
        )

        self._r_browse_button = ctk.CTkButton(
            self._win,
            text="Locate Rscript",
            width=180,
            command=on_browse,
        )
        self._r_browse_button.place(
            relx=0.5,
            rely=0.78,
            anchor="center",
        )

        self._r_cancel_button = ctk.CTkButton(
            self._win,
            text="Continue Without R",
            width=180,
            fg_color=ERROR_COLOUR,
            hover_color=ERROR_COLOUR_HOVER,
            border_width=1,
            command=on_cancel,
        )
        self._r_cancel_button.place(
            relx=0.5,
            rely=0.88,
            anchor="center",
        )

    def hide_r_missing(self) -> None:
        for widget_name in (
            "_r_message",
            "_r_error_label",
            "_r_browse_button",
            "_r_cancel_button",
        ):
            widget = getattr(self, widget_name, None)

            if widget is not None:
                widget.destroy()
                setattr(self, widget_name, None)

    def show_r_error(self, message: str) -> None:
        self._r_error_label.configure(
            text=message,
            text_color=ERROR_COLOUR,
        )

    def continue_without_r(self) -> None:
        """Close the splash and continue without INTEGRAL-Radiomics."""
        self._integral_done = True
        self._integral_error = True
        self._close_and_show()
