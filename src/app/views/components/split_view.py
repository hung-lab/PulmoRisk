from __future__ import annotations

import customtkinter as ctk

from app.utils.ui_config import SECTION_GAP_TOP, SPACE_MD, SPACE_XS


class SplitView:
    """3-column root layout: sidebar | main content | log panel.

    The sidebar drives navigation; callers register views with
    :meth:`add_view` and the sidebar button for each view is created
    automatically.  :meth:`toggle_right_panel` shows/hides the log panel.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        self.root = parent

        self.root.grid_columnconfigure(0, weight=1)  # content — expands
        self.root.grid_columnconfigure(1, weight=0)  # log panel — fixed
        self.root.grid_rowconfigure(0, weight=1)

        # ── LEFT: TAB AREA ─────────────────────────────
        self.tabs = ctk.CTkTabview(self.root)
        self.tabs.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=SECTION_GAP_TOP,
            pady=SPACE_MD,
        )

        self.home_tab = self.tabs.add("Home")
        self.sybil_tab = self.tabs.add("Sybil Epi")
        self.integral_tab = self.tabs.add("Integral Radiomics")

        # ── log panel ─────────────────────────────────────────────────────
        self.log_panel = ctk.CTkFrame(self.root, width=400, border_width=0)
        self.log_panel.grid(row=0, column=1, sticky="nsew", padx=(SPACE_XS, 0), pady=0)
        self.log_panel.grid_propagate(False)

        self._log_visible = True

    # ── log panel toggle ──────────────────────────────────────────────────

    def toggle_right_panel(self) -> None:
        if self._log_visible:
            self.log_panel.grid_remove()
        else:
            self.log_panel.grid()
        self._log_visible = not self._log_visible

    def lock_tabs(self) -> None:
        self.tabs._segmented_button.configure(state="disabled")

    def unlock_tabs(self) -> None:
        self.tabs._segmented_button.configure(state="normal")
