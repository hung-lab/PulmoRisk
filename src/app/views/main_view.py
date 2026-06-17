from __future__ import annotations

import customtkinter as ctk

from app.config.settings import ERROR_COLOUR
from app.utils.helpers import open_url
from app.utils.ui_config import CARD_PAD_X, CARD_PAD_Y, SPACE_MD, SPACE_XS


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
            text="Lung Cancer Risk Estimation",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(
            row=0, column=0, sticky="w", padx=CARD_PAD_X, pady=(CARD_PAD_Y, SPACE_XS)
        )

        content = ctk.CTkFrame(parent, border_width=0)
        content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=CARD_PAD_Y,
            pady=CARD_PAD_Y,
        )
        content.grid_rowconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=0)
        content.grid_columnconfigure(0, weight=1)

        # ── intro textbox ─────────────────────────────────────────────────────

        text = ctk.CTkTextbox(
            content, wrap="word", border_width=0, fg_color="transparent"
        )
        text.grid(
            row=0, column=0, sticky="nsew", padx=SPACE_MD, pady=(SPACE_MD, SPACE_XS)
        )

        def _add_link(label: str, url: str) -> None:
            tag = f"link_{url}"  # unique per URL, not per label
            text._textbox.tag_config(
                tag,
                foreground="#FF5a5f",
                underline=True,
            )  # config BEFORE insert
            text.insert("end", label, tag)
            text._textbox.tag_bind(tag, "<Button-1>", lambda _, u=url: open_url(u))
            text._textbox.tag_bind(
                tag, "<Enter>", lambda _: text._textbox.configure(cursor="hand2")
            )
            text._textbox.tag_bind(
                tag, "<Leave>", lambda _: text._textbox.configure(cursor="")
            )

        text.insert(
            "end",
            "This software tool implements two validated machine learning models, "
            "which can estimate lung cancer risk based on low-dose CT (LDCT) images and clinical and epidemiologic factors."
            "Two validated models are available:\n\n",
        )

        text.insert("end", "Sybil-Epi\n\n", "heading")
        text.insert(
            "end",
            "Sybil-Epi is a lung cancer risk prediction model that integrates key clinical and epidemiologic factors with deep learning model. "
            "The analysis with Sybil-Epi requires only one single LDCT series, with no additional nodule annotation or segmentation, "
            "combined with other 11 clinical risk factors, which are: age, BMI, education level, ethnicity, COPD history, "
            "family lung cancer history, personal cancer history, smoking status, smoking duration, smoking intensity, "
            "and smoking quit time.  "
            "More information on Sybil-Epi can be a found at ",
        )
        _add_link(
            "https://journal.chestnet.org/article/S0012-3692(26)00296-5/fulltext.",
            "https://journal.chestnet.org/article/S0012-3692(26)00296-5/fulltext",
        )
        text.insert("end", "\n\n")
        _add_link("View on GitHub", "https://github.com/hung-lab/Sybil-Epi")
        text.insert("end", "\n\n")

        text.insert("end", "INTEGRAL-Radiomics\n\n", "heading")
        text.insert(
            "end",
            "Applies radiomic feature extraction to quantify imaging biomarkers "
            "from CT scans, providing a complementary risk estimate based on "
            "tumour texture, shape, and intensity patterns. ",
        )
        _add_link("View on GitHub", "https://github.com/hung-lab/INTEGRAL-Radiomics")
        text.insert("end", "\n\n\n\n")

        text.insert(
            "end",
            "Select a model from the tabs above to begin. Ensure a valid CT "
            "scan folder is available before running either model.",
        )

        # style the heading tag
        text._textbox.tag_config("heading", font=("", 13, "bold"))

        text.configure(state="disabled")

        # ── disclaimer ────────────────────────────────────────────────────────
        disclaimer_label = ctk.CTkLabel(
            content,
            text="⚠  This tool is intended for research and clinical decision support only. "
            "Results should be interpreted by a qualified clinician and do not constitute a diagnosis.",
            justify="left",
            anchor="w",
            text_color=ERROR_COLOUR,
            font=ctk.CTkFont(size=12),
        )
        disclaimer_label.grid(
            row=1, column=0, sticky="ew", padx=SPACE_MD, pady=(SPACE_XS, SPACE_MD)
        )

        def _update_disclaimer_wrap(event):
            disclaimer_label.configure(wraplength=max(100, event.width - 2 * SPACE_MD))

        content.bind("<Configure>", _update_disclaimer_wrap)
