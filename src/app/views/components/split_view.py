from __future__ import annotations

import customtkinter as ctk

from app.views.components.side_bar import SideBar


class SplitView:
    """3-column root layout: sidebar | main content | log panel.

    The sidebar drives navigation; callers register views with
    :meth:`add_view` and the sidebar button for each view is created
    automatically.  :meth:`toggle_right_panel` shows/hides the log panel.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        self.root = parent

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=0)  # sidebar — fixed
        self.root.grid_columnconfigure(1, weight=1)  # content — expands
        self.root.grid_columnconfigure(2, weight=0)  # log panel — fixed

        self.root.grid_columnconfigure(0, minsize=200)
        self.root.grid_columnconfigure(2, minsize=400)
        # ── sidebar ───────────────────────────────────────────────────────
        self.sidebar = SideBar(self.root)
        self.sidebar.frame.grid(row=0, column=0, sticky="nsew")

        # ── main content area ─────────────────────────────────────────────
        self.middle = ctk.CTkFrame(self.root, border_width=0)
        self.middle.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)
        self.middle.grid_rowconfigure(0, weight=1)
        self.middle.grid_columnconfigure(0, weight=1)

        # ── log panel ─────────────────────────────────────────────────────
        self.right = ctk.CTkFrame(self.root, width=400, border_width=0)
        self.right.grid(row=0, column=2, sticky="nsew", padx=(4, 0), pady=0)
        self.right.grid_propagate(False)

        self._views: dict[str, ctk.CTkFrame] = {}
        self._active: str | None = None
        self._log_visible = True

    # ── view registration ─────────────────────────────────────────────────

    def add_view(self, label: str, frame: ctk.CTkFrame, imageName: str) -> None:
        """Register *frame* as a named view and add a sidebar button for it.

        The frame must be a direct child of ``self.middle``.
        The first view registered is shown immediately.
        """
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_remove()  # hidden until selected

        self._views[label] = frame
        self.sidebar.add_item(label, imageName, lambda l=label: self._show(l))

        if self._active is None:
            self._show(label)

    def _show(self, label: str) -> None:
        if self._active:
            self._views[self._active].grid_remove()
        self._views[label].grid()
        self._active = label
        self.sidebar.set_active(label)

    # ── log panel toggle ──────────────────────────────────────────────────

    def toggle_right_panel(self) -> None:
        if self._log_visible:
            self.right.grid_remove()
        else:
            self.right.grid()
        self._log_visible = not self._log_visible
