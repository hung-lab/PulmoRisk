from __future__ import annotations

import os
from typing import TYPE_CHECKING

import customtkinter as ctk
from PIL import Image

from app.config.settings import (
    BASE_PATH,
    PRIMARY_BLUE,
    SECONDARY_BLUE,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class SideBar:
    """Reusable sidebar navigation panel.

    Buttons are registered via :meth:`add_item`.  The caller provides a
    *command* callback for each entry.  The currently active item is
    highlighted automatically.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._active: str | None = None

        self.frame = ctk.CTkFrame(parent, width=200, border_width=0)
        self.frame.grid_propagate(False)
        self.frame.grid_rowconfigure(0, weight=1)  # push buttons to top
        self.frame.grid_columnconfigure(0, weight=1)

        # inner scrollable column so it never overflows
        # self._inner = ctk.CTkScrollableFrame(
        #     self.frame,
        #     fg_color="transparent",
        #     border_width=0,
        # )
        # self._inner.pack(fill="x", pady=(12, 0), padx=(12, 0))

        full_img_path = os.path.join(BASE_PATH, "assets", "house.png")
        logo_img_data = Image.open(full_img_path)
        logo_img = ctk.CTkImage(
            dark_image=logo_img_data, light_image=logo_img_data, size=(77.68, 85.42)
        )

        ctk.CTkLabel(master=self.frame, text="", image=logo_img).pack(
            pady=(38, 0), anchor="center"
        )

    # ── public API ────────────────────────────────────────────────────────

    def add_item(self, label: str, imageName: str, command: Callable[[], None]) -> None:
        """Add a navigation button.  First item added becomes active."""

        def _on_click():
            self.set_active(label)
            command()

        full_img_path = os.path.join(BASE_PATH, "assets", imageName)
        img_data = Image.open(full_img_path)
        img = ctk.CTkImage(dark_image=img_data, light_image=img_data)

        btn = ctk.CTkButton(
            self.frame,
            image=img,
            text=label,
            anchor="w",
            command=_on_click,
            border_width=0,
            corner_radius=0,
            fg_color="transparent",
            text_color=("#000000", "#f1f5f9"),
        )
        btn.pack(fill="x", padx=8, ipady=8, pady=(16, 0))
        self._buttons[label] = btn
        if self._active is None:
            self.set_active(label)

    def set_active(self, label: str) -> None:
        """Highlight *label* and clear all others."""
        if self._active == label:
            return

        if self._active and self._active in self._buttons:
            self._buttons[self._active].configure(
                fg_color="transparent", text_color=("#000000", "#f1f5f9")
            )

        self._active = label
        if label in self._buttons:
            self._buttons[label].configure(
                fg_color=(PRIMARY_BLUE, SECONDARY_BLUE),
                hover_color=(SECONDARY_BLUE, PRIMARY_BLUE),
                text_color=("#f1f5f9", "#000000"),
            )
