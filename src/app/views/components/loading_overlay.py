"""Reusable full-frame loading overlay component.

Drop it onto any CTkFrame and call show()/hide() to block the UI while a
long-running background task is in progress.

Usage
-----
    overlay = RunningOverlay(parent_frame)

    # show with optional custom title / initial stage text
    overlay.show(title="Running model…", stage="Preparing pipeline")

    # update text as stages progress (called from handle_event)
    overlay.set_stage("Running CT analysis…")

    # append a log line to the live feed
    overlay.append_log("Loaded 312 DICOM slices", level="INFO")

    # update progress bar (keeps animated until value reaches 1.0)
    overlay.set_progress(0.7)

    # hide when done
    overlay.hide()
"""

from __future__ import annotations

import datetime

import customtkinter as ctk

from app.config.settings import ERROR_COLOUR, LEVEL_COLOURS, LEVEL_PREFIX
from app.utils.ui_config import SPACE_LG, SPACE_MD, SPACE_SM

_MAX_LINES = 6  # how many log lines to keep visible at once


class RunningOverlay:
    """Full-frame animated loading overlay with a live log feed.

    Places itself over *parent* using ``place(relwidth=1, relheight=1)``
    and sits below the stacking order until :meth:`show` is called.

    Thread safety: all public methods must be called from the Tk main thread
    (i.e. from an EventBus subscriber or a ``root.after`` callback).
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        self._parent = parent
        self._visible = False
        self._elapsed = 0
        self._cancel_callback = None

        self._build()

    # ── public API ────────────────────────────────────────────────────────

    def show(
        self, title: str = "Running…", stage: str = "Preparing…", batch_mode=False
    ) -> None:
        """Lift the overlay and start the animation + elapsed timer."""
        self._visible = True
        self._elapsed = 0

        self._title_label.configure(text=title)
        self._stage_label.configure(text=stage)
        self._elapsed_label.configure(text="0s elapsed")

        # Clear any log lines from a previous run
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

        # always start in indeterminate mode so the bar animates immediately
        self._bar.configure(mode="indeterminate")
        self._bar.start()

        if batch_mode:
            self.enable_batch_mode()
        else:
            self.disable_batch_mode()

        self._frame.lift()
        self._tick()

    def hide(self) -> None:
        """Lower the overlay and stop the animation."""
        self._visible = False
        self._bar.stop()
        self.disable_batch_mode()
        self._frame.lower()
        self._cancel_callback = None

    def enable_batch_mode(self):
        self._batch_bar.set(0)
        self._batch_label.configure(text="0 / 0 individuals")

        self._cancel_btn.configure(
            text="Cancel Batch",
            state="normal",
        )
        self._batch_frame.pack(pady=(SPACE_MD, 0))

    def disable_batch_mode(self):
        self._batch_frame.pack_forget()

    def set_stage(self, text: str) -> None:
        """Update the stage subtitle (e.g. 'Running CT analysis…')."""
        self._stage_label.configure(text=text)

    def append_log(self, message: str, level: str = "INFO") -> None:
        """Append a timestamped log line to the live feed on the overlay."""
        prefix, tag = LEVEL_PREFIX.get(level.upper(), ("•", "info"))
        timestamp = (
            datetime.datetime.now(datetime.timezone.utc)
            .astimezone()
            .strftime("%H:%M:%S")
        )

        self._log_box.configure(state="normal")

        # Keep the box from growing forever
        lines = int(self._log_box.index("end-1c").split(".")[0])
        if lines >= _MAX_LINES:
            self._log_box.delete("1.0", "2.0")

        self._log_box.insert("end", f"[{timestamp}] {prefix} {message}\n", tag)
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def set_progress(self, value: float) -> None:
        """React to a progress milestone.

        Keeps the bar in indeterminate (animated) mode for all intermediate
        values so it never appears frozen.  Switches to determinate only when
        *value* reaches 1.0 so the user sees a clear completion signal.
        """
        if value >= 1.0:
            self._bar.stop()
            self._bar.configure(mode="determinate")
            self._bar.set(1.0)
            self._stage_label.configure(text="Complete!")

    def set_batch_progress(self, current: int, total: int):
        if total <= 0:
            return

        value = current / total

        self._batch_bar.set(value)
        self._batch_label.configure(text=f"{current} / {total} individuals")

    def set_cancel_callback(self, callback):
        self._cancel_callback = callback

    @property
    def is_visible(self) -> bool:
        return self._visible

    # ── internal ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._frame = ctk.CTkFrame(self._parent, border_width=0)
        self._frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._frame.lower()

        # centred content block
        inner = ctk.CTkFrame(self._frame, fg_color="transparent", border_width=0)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self._title_label = ctk.CTkLabel(
            inner,
            text="Running…",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self._title_label.pack(pady=(0, SPACE_SM))

        self._stage_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="gray60",
        )
        self._stage_label.pack(pady=(0, SPACE_LG))

        self._bar = ctk.CTkProgressBar(inner, width=360, height=10)
        self._bar.pack()
        self._bar.set(0)

        self._batch_frame = ctk.CTkFrame(inner, fg_color="transparent", border_width=0)

        self._batch_frame.pack(pady=(SPACE_MD, 0))

        self._batch_label = ctk.CTkLabel(
            self._batch_frame,
            text="0 / 0 individuals",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self._batch_label.pack()

        self._batch_bar = ctk.CTkProgressBar(
            self._batch_frame,
            width=360,
            height=10,
            mode="determinate",
        )
        self._batch_bar.pack(pady=(4, SPACE_SM))

        self._elapsed_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self._elapsed_label.pack(pady=(SPACE_SM, SPACE_MD))

        self._cancel_btn = ctk.CTkButton(
            self._batch_frame,
            text="Cancel Batch",
            width=140,
            command=self._on_cancel,
            fg_color=ERROR_COLOUR,
        )
        self._cancel_btn.pack()

        # ── live log feed ─────────────────────────────────────────────────
        self._log_box = ctk.CTkTextbox(
            inner,
            width=440,
            height=112,  # ~6 lines at 11pt
            state="disabled",
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=11),
            border_width=1,
        )
        self._log_box.pack()

        # Configure per-level colour tags
        self.update_tag_colours(ctk.get_appearance_mode())

    def _tick(self) -> None:
        """Increment the elapsed-time counter every second while visible."""
        if not self._visible:
            return

        self._elapsed += 1
        mins, secs = divmod(self._elapsed, 60)
        text = f"{mins}m {secs:02d}s elapsed" if mins else f"{secs}s elapsed"
        self._elapsed_label.configure(text=text)

        self._parent.after(1000, self._tick)

    def _on_cancel(self):
        if self._cancel_callback:
            self._cancel_callback()

        self._stage_label.configure(text="Cancelling after current individual...")

        self._cancel_btn.configure(
            text="Cancelling...",
            state="disabled",
        )

    def update_tag_colours(self, mode: str) -> None:
        """Sync log-box tag colours to the current appearance mode."""
        if mode == "System":
            # resolve to what the OS is actually using
            mode = ctk.get_appearance_mode()
        for level, colours in LEVEL_COLOURS.items():
            colour = colours[0] if mode == "Light" else colours[1]
            self._log_box.tag_config(level.lower(), foreground=colour)
