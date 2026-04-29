import customtkinter as ctk

from app.utils.helpers import center_window
from app.utils.ui_config import BUTTON_GAP, SPACE_LG, SPACE_MD


class InfoDialog:
    """Display a simple modal information dialog."""

    def __init__(self, parent: ctk.CTk, title: str, message: str) -> None:

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

        ctk.CTkButton(dialog, text="OK", width=100, command=dialog.destroy).pack(
            pady=(0, BUTTON_GAP)
        )

        dialog.update_idletasks()  # force geometry to resolve before centering
        center_window(dialog)
