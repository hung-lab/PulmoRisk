"""Menubar view using CustomTkinter."""

from __future__ import annotations

import sys
import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.config.settings import (
    _ERROR_COLOUR,
    __author__,
    __build_date__,
    __version__,
)
from app.utils.ui_config import BUTTON_GAP, CARD_PAD_X, SPACE_LG, SPACE_MD, SPACE_SM
from app.views.dialogs.info_dialog import InfoDialog

if TYPE_CHECKING:
    from app.controllers.menubar_controller import MenuBarController


class MenuBar:
    """Native menu bar wired to :class:`MenuBarController`."""

    def __init__(self, parent: ctk.CTkFrame, controller: MenuBarController) -> None:
        self.root = parent
        self.controller = controller
        self._setup_ui()

    # ──────────────────────────────────────────────── build ──

    def _setup_ui(self) -> None:
        menubar = tk.Menu(self.root)

        self._build_file_menu(menubar)
        self._build_view_menu(menubar)
        self._build_help_menu(menubar)

        self.root.config(menu=menubar)

        # Keyboard shortcuts
        _mod = "Command" if sys.platform == "darwin" else "Control"
        self.root.bind(f"<{_mod}-n>", lambda _e: self.start_a_new_run())
        self.root.bind(f"<{_mod}-q>", lambda _e: self.destroy())
        self.root.bind(f"<{_mod}-1>", lambda _e: self.toggle_sidepanel())
        self.root.bind(f"<{_mod}-2>", lambda _e: self.toggle_log_visibility())

    def _build_file_menu(self, menubar: tk.Menu) -> None:
        _acc = "Cmd" if sys.platform == "darwin" else "Ctrl"
        menu = tk.Menu(menubar, tearoff=0)

        menu.add_command(
            label="New Run",
            command=self.start_a_new_run,
            accelerator=f"{_acc}+N",
        )
        menu.add_separator()
        menu.add_command(
            label="Exit",
            command=self.destroy,
            accelerator=f"{_acc}+Q",
        )
        menubar.add_cascade(label="File", menu=menu)

    def _build_view_menu(self, menubar: tk.Menu) -> None:
        _acc = "Cmd" if sys.platform == "darwin" else "Ctrl"
        menu = tk.Menu(menubar, tearoff=0)

        menu.add_command(
            label="Toggle Side Panel",
            command=self.toggle_sidepanel,
            accelerator=f"{_acc}+1",
        )
        menu.add_command(
            label="Toggle Activity Log",
            command=self.toggle_log_visibility,
            accelerator=f"{_acc}+2",
        )
        menu.add_separator()

        # Appearance submenu
        appearance_sub = tk.Menu(menu, tearoff=0)
        appearance_sub.add_command(
            label="Light", command=lambda: self.change_appearance_mode("Light")
        )
        appearance_sub.add_command(
            label="Dark", command=lambda: self.change_appearance_mode("Dark")
        )
        appearance_sub.add_command(
            label="System", command=lambda: self.change_appearance_mode("System")
        )
        menu.add_cascade(label="Appearance", menu=appearance_sub)

        menubar.add_cascade(label="View", menu=menu)

    def _build_help_menu(self, menubar: tk.Menu) -> None:
        menu = tk.Menu(menubar, tearoff=0)
        menu.add_command(label="About Lung Cancer Screening", command=self.show_about)
        menu.add_command(label="About This App", command=self.show_app_info)
        menubar.add_cascade(label="Help", menu=menu)

    # ──────────────────────────────────────────────── commands ──

    def start_a_new_run(self) -> None:
        """Reset the Sybil form for a fresh patient entry."""
        self.controller.new_run()

    def destroy(self) -> None:
        """Confirm and exit the application."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Exit")
        dialog.geometry("300x130")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.focus_force()

        ctk.CTkLabel(dialog, text="Exit the application?").pack(
            pady=(CARD_PAD_X, SPACE_MD)
        )

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent", border_width=0)
        btn_row.pack()
        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100,
            command=dialog.destroy,
        ).pack(side="left", padx=SPACE_SM)
        ctk.CTkButton(
            btn_row,
            text="Exit",
            width=100,
            command=self.controller.quit_app,
            fg_color=_ERROR_COLOUR,
        ).pack(side="left", padx=SPACE_SM)

    def toggle_sidepanel(self) -> None:
        self.controller.toggle_sidepanel()

    def toggle_log_visibility(self) -> None:
        self.controller.toggle_log()

    def change_appearance_mode(self, mode: str) -> None:
        self.controller.change_appearance(mode)

    def show_about(self) -> None:
        """Display a brief info dialog about lung cancer screening."""
        InfoDialog(
            self.root,
            title="About Lung Cancer Screening",
            message=(
                "Low-dose CT screening is recommended for adults aged 50-80 "
                "with a 20 pack-year smoking history who currently smoke or "
                "have quit within the past 15 years.\n\n"
                "This tool uses the Sybil model combined with epidemiological "
                "risk factors to estimate 6-year lung cancer risk."
            ),
        )

    def show_app_info(self) -> None:
        """Display application version and author info."""
        InfoDialog(
            self.root,
            title="About This App",
            message=(
                f"Version:     {__version__}\n"
                f"Build date:  {__build_date__}\n"
                f"Author:      {__author__}"
            ),
        )


# ──────────────────────────────────────────────── utility ──


def _show_info_dialog(root: ctk.CTk, title: str, message: str) -> None:
    """Display a simple modal information dialog."""
    dialog = ctk.CTkToplevel(root)
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
