import webbrowser

import customtkinter as ctk

from app.utils.helpers import center_window
from app.utils.ui_config import BUTTON_GAP, SPACE_LG, SPACE_MD


class InfoDialog:
    """Display a simple modal information dialog."""

    def __init__(
        self, parent: ctk.CTk, title: str, message: str, github_url: str
    ) -> None:

        dialog = ctk.CTkToplevel(parent)
        dialog.title(title)
        dialog.geometry("420x220")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.focus_force()

        ctk.CTkLabel(
            dialog,
            text=message,
            wraplength=380,
            justify="left",
        ).pack(padx=SPACE_LG, pady=(SPACE_LG, SPACE_MD), anchor="w")

        github_link = ctk.CTkLabel(
            dialog,
            text="GitHub Repository",
            text_color="#1f6aa5",
            cursor="hand2",
        )
        github_link.pack(pady=(0, SPACE_MD))

        github_link.bind("<Button-1>", lambda _: webbrowser.open(github_url))

        ctk.CTkButton(dialog, text="OK", width=100, command=dialog.destroy).pack(
            pady=(0, BUTTON_GAP)
        )

        dialog.update_idletasks()  # force geometry to resolve before centering
        center_window(dialog, fraction=0.15)
