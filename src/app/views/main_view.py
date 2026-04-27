from __future__ import annotations

import customtkinter as ctk


class MainWindow:
    """Static main window (no event system, no controller coupling)."""

    def __init__(self, root: ctk.CTk, controller=None) -> None:
        self.root = root
        self.controller = controller  # optional reference only

        self._setup_ui()

    # ──────────────────────────────────────────────── layout ──

    def _setup_ui(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._main_frame = ctk.CTkFrame(self.root, border_width=0)
        self._main_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self._build_main_panel(self._main_frame)

    def _build_main_panel(self, parent: ctk.CTkFrame) -> None:
        parent.grid_rowconfigure(0, weight=0)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            parent,
            text="Lung Cancer Risk Modelling",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))

        content = ctk.CTkFrame(parent)
        content.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)

        self.status_label = ctk.CTkLabel(content, text="TODO", anchor="w")
        self.status_label.pack(anchor="w", padx=12, pady=12)

    # ──────────────────────────────────────────────── STATIC API ──

    def set_status(self, message: str) -> None:
        """Only direct updates from controller if needed."""
        self.status_label.configure(text=message)
