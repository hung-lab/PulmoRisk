from __future__ import annotations

import customtkinter as ctk

from app.config.settings import (
    ERROR_COLOUR,
    ERROR_COLOUR_HOVER,
    PRIMARY_DARK,
    WARNING_COLOUR,
)
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
        content.grid_rowconfigure(2, weight=0)
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

        def copy_citation():
            self.root.clipboard_clear()
            self.root.clipboard_append(citation)
            copy_button.configure(text="✓ Copied!")
            self.root.after(
                2000, lambda: copy_button.configure(text="📋 Copy Citation")
            )

        text.insert(
            "end",
            "This software tool implements two validated machine learning models, "
            "which can estimate lung cancer risk based on low-dose CT (LDCT) images and clinical and epidemiologic factors.\n\n"
            "Two validated models are available:\n\n",
        )

        text.insert("end", "Sybil-Epi\n", "heading")
        text.insert(
            "end",
            "Sybil-Epi is a lung cancer risk prediction model that integrates key clinical and epidemiologic factors with deep learning model. "
            "The analysis with Sybil-Epi requires only one single LDCT series, with no additional nodule annotation or segmentation, "
            "combined with other 11 clinical risk factors, which are: \n\n"
            "- age\n"
            "- BMI\n"
            "- education level\n"
            "- ethnicity\n"
            "- COPD history\n"
            "- family lung cancer history\n"
            "- personal cancer history\n"
            "- smoking status\n"
            "- smoking duration\n"
            "- smoking intensity\n"
            "- smoking quit time\n\n"
            "More information on Sybil-Epi can be a found at ",
        )
        _add_link(
            "https://journal.chestnet.org/article/S0012-3692(26)00296-5/fulltext.",
            "https://journal.chestnet.org/article/S0012-3692(26)00296-5/fulltext",
        )
        text.insert("end", "\n\n")
        _add_link("View on GitHub", "https://github.com/hung-lab/Sybil-Epi")
        text.insert("end", "\n\n")

        text.insert("end", "INTEGRAL-Radiomics\n", "heading")
        text.insert(
            "end",
            "INTEGRAL-Radiomics is a machine-learning model that estimates pulmonary nodule malignancy "
            "risk based on a set of radiomic and epidemiological features. "
            "The high-dimensional radiomic features are automatically calculated using PyRadiomics "
            "based on the user-provided image (LDCT) and nodule mask. "
            "The user must also provide a set of epidemiological features including: age, sex, body mass index (BMI), "
            "family history of lung cancer, personal history of COPD/emphysema, smoking status, smoking duration, "
            "smoking intensity, and smoking quit time."
            "More information on INTEGRAL-Radiomics can be a found at ",
        )
        _add_link(
            "https://thorax.bmj.com/content/79/4/307.long.",
            "https://thorax.bmj.com/content/79/4/307.long",
        )
        text.insert("end", "\n\n")
        text.insert(
            "end",
            "If you have questions about the INTEGRAL-Radiomics model, please file an issue on GitHub ",
        )
        _add_link(
            "(https://github.com/mattwarkentin/INTEGRAL-Radiomics)",
            "https://github.com/mattwarkentin/INTEGRAL-Radiomics",
        )
        text.insert("end", "\n\n")

        text.insert(
            "end",
            "If you use this model in your work, please cite:\n\n",
        )
        citation = (
            "Warkentin MT, Al-Sawaihey H, Lam S, Liu G, Diergaarde B, Yuan JM, "
            "Wilson DO, Atkar-Khattra S, Grant B, Brhane Y, Khodayari-Moez E, "
            "Murison KR, Tammemägi MC, Campbell KR, Hung RJ. "
            "Radiomics analysis to predict pulmonary nodule malignancy using "
            "machine learning approaches. Thorax. 2024 Apr 1;79(4):307-15.\n\n"
        )

        text.insert(
            "end",
            citation,
        )

        copy_button = ctk.CTkButton(
            text._textbox,
            text="📋 Copy Citation",
            command=copy_citation,
            width=110,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=ERROR_COLOUR,
            hover_color=ERROR_COLOUR_HOVER,
        )

        text._textbox.window_create("end", window=copy_button)
        text.insert("end", "\n\n")

        text.insert("end", "\n\n\n\n")

        # style the heading tag
        text._textbox.tag_config(
            "heading",
            font=("", 16, "bold"),
            spacing1=12,
            spacing3=8,
        )
        text._textbox.tag_config(
            "subheading",
            font=("", 13, "bold"),
            foreground="#FF5a5f",
            spacing1=8,
            spacing3=4,
        )

        text.configure(state="disabled")

        # ── banner ────────────────────────────────────────────────────────
        instruction_banner = ctk.CTkFrame(
            content,
            fg_color=PRIMARY_DARK,
            corner_radius=8,
            border_width=1,
            border_color=WARNING_COLOUR,
        )

        instruction_banner.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=SPACE_MD,
            pady=(SPACE_XS, SPACE_XS),
        )

        instruction_banner.grid_columnconfigure(0, weight=1)

        instruction_label = ctk.CTkLabel(
            instruction_banner,
            text=(
                "⚠  Select a model from the tabs above to begin.\n"
                "Ensure you have valid CT scans before running either model. "
                "Sybil-Epi requires DICOM files; INTEGRAL-Radiomics requires "
                "an NRRD image and nodule mask."
            ),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=WARNING_COLOUR,
            justify="left",
            anchor="w",
            wraplength=800,
        )

        instruction_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=10,
        )
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
            row=2, column=0, sticky="ew", padx=SPACE_MD, pady=(SPACE_XS, SPACE_MD)
        )

        def _update_disclaimer_wrap(event):
            disclaimer_label.configure(wraplength=max(100, event.width - 2 * SPACE_MD))

        content.bind("<Configure>", _update_disclaimer_wrap)
