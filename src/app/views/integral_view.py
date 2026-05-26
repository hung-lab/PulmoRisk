from __future__ import annotations

import contextlib
import tkinter as tk
from typing import TYPE_CHECKING

from app.config.settings import BORDER_COLOUR, ERROR_COLOUR
from app.utils.event_bus import AppEvent
import customtkinter as ctk

from app.models.patient_model import (
    IntegralClinicalData,
    IntegralRadiomicsInput,
    RadiomicsFeatures,
)
from app.utils.ui_config import (
    BUTTON_GAP,
    CARD_PAD_X,
    CARD_PAD_Y,
    INPUT_WIDTH,
    LABEL_WIDTH,
    SECTION_GAP_BOTTOM,
    SECTION_GAP_TOP,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
)
from app.utils.validators import IntegralValidator  # reuse validator logic
from app.views.components.loading_overlay import RunningOverlay

if TYPE_CHECKING:
    from app.controllers.integral_controller import IntegralController

import json

# ─────────────────────────────── OPTIONS ───────────────────────────────

SEX_OPTIONS = {
    "Male": 0,
    "Female": 1,
}

_SAMPLE_FEATURES = {
  "epi_age": 67,
  "epi_female": 0,
  "epi_fhlc": 1,
  "epi_copdemph": 0,
  "epi_formersmk": 1,
  "epi_duration": 38,
  "epi_cigday": 18,
  "epi_quittime": 6,
  "epi_bmi": 27.4,

  "original_shape_Elongation": 0.71,
  "original_shape_Flatness": 0.43,
  "original_shape_LeastAxisLength": 12.8,
  "original_shape_Sphericity": 0.84,

  "original_firstorder_10Percentile": -812.5,
  "original_firstorder_Kurtosis": 3.92,
  "original_firstorder_Maximum": 245.7,
  "original_firstorder_MeanAbsoluteDeviation": 84.2,
  "original_firstorder_Mean": -523.8,
  "original_firstorder_Minimum": -1024.0,
  "original_firstorder_Range": 1269.7,
  "original_firstorder_Skewness": -0.61,

  "original_glcm_ClusterShade": -1240.5,
  "original_glcm_ClusterTendency": 18.4,
  "original_glcm_DifferenceAverage": 1.92,
  "original_glcm_Idm": 0.83,
  "original_glcm_Idn": 0.91,
  "original_glcm_Imc1": -0.37,
  "original_glcm_Imc2": 0.82,
  "original_glcm_InverseVariance": 0.24,
  "original_glcm_MCC": 0.74,

  "original_glrlm_GrayLevelNonUniformity": 152.7,
  "original_glrlm_LongRunLowGrayLevelEmphasis": 0.0042,
  "original_glrlm_RunEntropy": 4.82,
  "original_glrlm_RunPercentage": 0.31,
  "original_glrlm_ShortRunLowGrayLevelEmphasis": 0.87,

  "original_glszm_GrayLevelNonUniformity": 138.4,
  "original_glszm_HighGrayLevelZoneEmphasis": 22.5,
  "original_glszm_ZonePercentage": 0.18,

  "original_gldm_DependenceNonUniformityNormalized": 0.14,
  "original_gldm_LargeDependenceEmphasis": 12.9,
  "original_gldm_LargeDependenceHighGrayLevelEmphasis": 45.7,
  "original_gldm_LargeDependenceLowGrayLevelEmphasis": 0.0061,

  "original_ngtdm_Busyness": 1.84,
  "original_ngtdm_Complexity": 324.5,
  "original_ngtdm_Contrast": 0.027,
  "original_ngtdm_Strength": 0.92,
  "original_ngtdm_Coarseness": 0.0048,

  "wavelet-LLH_firstorder_10Percentile": -645.2,
  "wavelet-LLH_firstorder_Maximum": 312.8,
  "wavelet-LLH_firstorder_MeanAbsoluteDeviation": 73.1,
  "wavelet-LLH_firstorder_Mean": -401.5,

  "wavelet-LLH_glcm_ClusterProminence": 1840.2,
  "wavelet-LLH_glcm_ClusterTendency": 14.6,
  "wavelet-LLH_glcm_DifferenceAverage": 2.11,
  "wavelet-LLH_glcm_Idm": 0.79,
  "wavelet-LLH_glcm_Idn": 0.88,
  "wavelet-LLH_glcm_Imc1": -0.41,
  "wavelet-LLH_glcm_Imc2": 0.76,
  "wavelet-LLH_glcm_InverseVariance": 0.19,
  "wavelet-LLH_glcm_MCC": 0.69,

  "wavelet-LLH_glrlm_GrayLevelNonUniformity": 164.3,
  "wavelet-LLH_glrlm_LongRunLowGrayLevelEmphasis": 0.0031,
  "wavelet-LLH_glrlm_RunEntropy": 5.02,
  "wavelet-LLH_glrlm_RunPercentage": 0.27,
  "wavelet-LLH_glrlm_RunVariance": 8.6,
  "wavelet-LLH_glrlm_ShortRunLowGrayLevelEmphasis": 0.81,

  "wavelet-LLH_glszm_GrayLevelNonUniformity": 142.8,
  "wavelet-LLH_glszm_ZonePercentage": 0.22,

  "wavelet-LLH_gldm_DependenceNonUniformityNormalized": 0.17,
  "wavelet-LLH_gldm_LargeDependenceEmphasis": 10.8,
  "wavelet-LLH_gldm_LargeDependenceHighGrayLevelEmphasis": 39.2,

  "wavelet-LLH_ngtdm_Busyness": 2.12,
  "wavelet-LLH_ngtdm_Contrast": 0.033,
  "wavelet-LLH_ngtdm_Strength": 0.81,
  "wavelet-LLH_ngtdm_Coarseness": 0.0039,

  "wavelet-LHL_firstorder_10Percentile": -688.1,
  "wavelet-LHL_firstorder_Kurtosis": 4.15,
  "wavelet-LHL_firstorder_Maximum": 287.2,
  "wavelet-LHL_firstorder_MeanAbsoluteDeviation": 69.7,
  "wavelet-LHL_firstorder_Mean": -437.9,
  "wavelet-LHL_firstorder_Minimum": -1011.0,
  "wavelet-LHL_firstorder_Range": 1298.2,
  "wavelet-LHL_firstorder_Skewness": -0.42,

  "wavelet-LHL_glcm_ClusterProminence": 1721.4,
  "wavelet-LHL_glcm_ClusterTendency": 16.1,
  "wavelet-LHL_glcm_DifferenceAverage": 1.88,
  "wavelet-LHL_glcm_Idm": 0.82,
  "wavelet-LHL_glcm_Idn": 0.89,
  "wavelet-LHL_glcm_Imc1": -0.39,
  "wavelet-LHL_glcm_Imc2": 0.79,
  "wavelet-LHL_glcm_InverseVariance": 0.22,
  "wavelet-LHL_glcm_MCC": 0.72,

  "wavelet-LHL_glrlm_GrayLevelNonUniformity": 149.5,
  "wavelet-LHL_glrlm_LongRunLowGrayLevelEmphasis": 0.0048,
  "wavelet-LHL_glrlm_RunEntropy": 4.76,
  "wavelet-LHL_glrlm_RunPercentage": 0.29,
  "wavelet-LHL_glrlm_ShortRunLowGrayLevelEmphasis": 0.84,

  "wavelet-LHL_glszm_GrayLevelNonUniformity": 136.7,
  "wavelet-LHL_glszm_HighGrayLevelZoneEmphasis": 25.4,
  "wavelet-LHL_glszm_ZonePercentage": 0.19,

  "wavelet-LHL_gldm_DependenceNonUniformityNormalized": 0.16,
  "wavelet-LHL_gldm_LargeDependenceEmphasis": 11.7,
  "wavelet-LHL_gldm_LargeDependenceHighGrayLevelEmphasis": 42.1,
  "wavelet-LHL_gldm_LargeDependenceLowGrayLevelEmphasis": 0.0054,

  "wavelet-LHL_ngtdm_Busyness": 1.96,
  "wavelet-LHL_ngtdm_Complexity": 341.2,
  "wavelet-LHL_ngtdm_Contrast": 0.029,
  "wavelet-LHL_ngtdm_Strength": 0.88,
  "wavelet-LHL_ngtdm_Coarseness": 0.0042,

  "log-sigma-1-0-mm-3D_firstorder_10Percentile": -590.4,
  "log-sigma-1-0-mm-3D_firstorder_Kurtosis": 3.71,
  "log-sigma-1-0-mm-3D_firstorder_Maximum": 201.6,
  "log-sigma-1-0-mm-3D_firstorder_MeanAbsoluteDeviation": 62.5,
  "log-sigma-1-0-mm-3D_firstorder_Mean": -410.7,
  "log-sigma-1-0-mm-3D_firstorder_Minimum": -998.0,
  "log-sigma-1-0-mm-3D_firstorder_Range": 1199.6,

  "log-sigma-1-0-mm-3D_glcm_DifferenceAverage": 1.63,
  "log-sigma-1-0-mm-3D_glcm_Idm": 0.86,
  "log-sigma-1-0-mm-3D_glcm_Idn": 0.92,
  "log-sigma-1-0-mm-3D_glcm_Imc1": -0.31,
  "log-sigma-1-0-mm-3D_glcm_Imc2": 0.74,
  "log-sigma-1-0-mm-3D_glcm_InverseVariance": 0.28,
  "log-sigma-1-0-mm-3D_glcm_MCC": 0.77,

  "square_firstorder_10Percentile": 22500.0,
  "square_firstorder_Kurtosis": 5.12,
  "square_firstorder_Maximum": 1048576.0,
  "square_firstorder_Mean": 312450.8,
  "square_firstorder_Minimum": 0.0,
  "square_firstorder_Range": 1048576.0,
  "square_firstorder_Skewness": 1.21,

  "squareroot_firstorder_Kurtosis": 2.91,
  "squareroot_firstorder_Maximum": 31.8,
  "squareroot_firstorder_MeanAbsoluteDeviation": 5.4,
  "squareroot_firstorder_Mean": 19.7,
  "squareroot_firstorder_Minimum": 0.0,
  "squareroot_firstorder_Range": 31.8,

  "logarithm_firstorder_Kurtosis": 3.22,
  "logarithm_firstorder_Maximum": 6.81,
  "logarithm_firstorder_MeanAbsoluteDeviation": 0.92,
  "logarithm_firstorder_Mean": 4.37,
  "logarithm_firstorder_Minimum": 0.0,
  "logarithm_firstorder_Range": 6.81,
  "logarithm_firstorder_Skewness": -0.14,

  "exponential_firstorder_Kurtosis": 6.45,
  "exponential_firstorder_Maximum": 4821.6,
  "exponential_firstorder_Mean": 714.2,
  "exponential_firstorder_Minimum": 1.0,
  "exponential_firstorder_Range": 4820.6,
  "exponential_firstorder_Skewness": 1.94,

  "gradient_firstorder_10Percentile": 4.2,
  "gradient_firstorder_Kurtosis": 3.57,
  "gradient_firstorder_Maximum": 198.4,
  "gradient_firstorder_MeanAbsoluteDeviation": 18.7,
  "gradient_firstorder_Mean": 41.5,
  "gradient_firstorder_Minimum": 0.0,
  "gradient_firstorder_Range": 198.4,
  "gradient_firstorder_Skewness": 0.88,

  "lbp-3D-m1_firstorder_10Percentile": 2.0,
  "lbp-3D-m1_firstorder_Maximum": 255.0,
  "lbp-3D-m1_firstorder_MeanAbsoluteDeviation": 41.6,
  "lbp-3D-m1_firstorder_Mean": 118.3,
  "lbp-3D-m1_firstorder_Minimum": 0.0,
  "lbp-3D-m1_firstorder_Range": 255.0,
  "lbp-3D-m1_firstorder_Skewness": 0.37,

  "lbp-3D-k_firstorder_10Percentile": 1.0,
  "lbp-3D-k_firstorder_Kurtosis": 2.84,
  "lbp-3D-k_firstorder_Maximum": 255.0,
  "lbp-3D-k_firstorder_MeanAbsoluteDeviation": 44.9,
  "lbp-3D-k_firstorder_Mean": 126.8,
  "lbp-3D-k_firstorder_Minimum": 0.0,
  "lbp-3D-k_firstorder_Range": 255.0,
  "lbp-3D-k_firstorder_Skewness": 0.12
}


class IntegralView:
    def __init__(self, root: ctk.CTkFrame, controller: IntegralController) -> None:
        self.root = root
        self.controller = controller

        self._running = False
        self.validator = IntegralValidator()

        # ── clinical vars ───────────────────────────────
        self._age_var = tk.StringVar(value="67")
        self._gender_var = tk.StringVar(value="Male")
        self._fhlc_var = tk.BooleanVar(value=True)
        self._copd_var = tk.BooleanVar(value=False)
        self._former_smoker_var = tk.BooleanVar(value=True)

        self._duration_var = tk.StringVar(value="38")
        self._cigday_var = tk.StringVar(value="18")
        self._quit_var = tk.StringVar(value="6")
        self._bmi_var = tk.StringVar(value="27.4")

        # ── IDs (optional) ──────────────────────────────
        self._study_var = tk.StringVar(value="1")
        self._pid_var = tk.StringVar(value="1")
        self._nid_var = tk.StringVar(value="1")

        # ── radiomics (JSON-style input) ────────────────
        self._radiomics_box: ctk.CTkTextbox | None = None

        # ── errors ───────────────────────────────────────
        self._age_error = tk.StringVar()
        self._bmi_error = tk.StringVar()
        self._rad_error = tk.StringVar()
        self._smoking_duration_error_var = tk.StringVar()
        self._smoking_intensity_error_var = tk.StringVar()
        self._smoking_quit_time_error_var = tk.StringVar()

        self.run_button: ctk.CTkButton | None = None
        self._results_frame: ctk.CTkFrame | None = None
        self._entries: dict[str, ctk.CTkEntry] = {}

        self._setup_ui()

    # ─────────────────────────────── event helper ─────────────────────────

    def _emit(self, type_: str, message: str = "", level: str = "INFO") -> None:
        self.controller.bus.emit(AppEvent(type=type_, message=message, level=level))

    # ─────────────────────────────── UI SETUP ────────────────────────────

    def _setup_ui(self) -> None:
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.container = ctk.CTkScrollableFrame(self.root, border_width=0)
        self.container.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=SECTION_GAP_TOP,
            pady=SECTION_GAP_BOTTOM,
        )

        ctk.CTkLabel(
            self.container,
            text="INTEGRAL Radiomics Risk Model",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(SPACE_MD, SPACE_XS))

        ctk.CTkLabel(
            self.container,
            text="Enter clinical + radiomics features",
            text_color=("gray40", "gray90"),
        ).pack(anchor="w", pady=(0, SPACE_LG))

        self._card("Clinical Data", self._build_clinical)
        self._card("Smoking History", self._build_smoking)
        self._card("Identifiers (optional)", self._build_ids)
        self._card("Radiomics Features (JSON)", self._build_radiomics)

        # results card (hidden until a run completes)
        self._results_frame = ctk.CTkFrame(
            self.container, border_color=ERROR_COLOUR, border_width=3
        )
        self._results_label = ctk.CTkLabel(
            self._results_frame,
            text="",
            font=ctk.CTkFont(family="Courier", size=20),
            justify="left",
            anchor="w",
        )
        self._results_label.pack(anchor="w", padx=SPACE_LG, pady=SPACE_MD)

        bottom = ctk.CTkFrame(self.root, fg_color="transparent")
        bottom.grid(
            row=2, column=0, sticky="ew", padx=BUTTON_GAP, pady=(SPACE_XS, BUTTON_GAP)
        )
        bottom.grid_columnconfigure(0, weight=1)

        self.run_button = ctk.CTkButton(
            bottom,
            text="Run INTEGRAL Model",
            height=44,
            command=self._on_submit,
        )
        self.run_button.grid(row=0, column=0, sticky="ew")

        # ── overlay (lifted during a run) ────────────────────────────────
        self._overlay = RunningOverlay(self.root)

    # ─────────────────────────────── CARD HELPER ─────────────────────────

    def _card(self, title: str, builder) -> None:
        frame = ctk.CTkFrame(self.container)
        frame.pack(fill="x", pady=CARD_PAD_Y, padx=CARD_PAD_X)

        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=SECTION_GAP_BOTTOM, pady=(SPACE_SM, SPACE_XS)
        )

        body = ctk.CTkFrame(frame, fg_color="transparent", border_width=0)
        body.pack(fill="x", padx=SECTION_GAP_BOTTOM, pady=(0, SPACE_SM))
        builder(body)

    # ─────────────────────────────── ROW HELPERS ─────────────────────────

    def _row(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        r = ctk.CTkFrame(parent, fg_color="transparent", border_width=0)
        r.pack(fill="x", pady=SPACE_XS)

        # Define 2-column layout: label | input
        r.grid_columnconfigure(0, weight=0, minsize=LABEL_WIDTH)  # label
        r.grid_columnconfigure(1, weight=0)  # input

        return r

    def _label(self, parent, text: str) -> None:
        ctk.CTkLabel(parent, text=text, anchor="w", width=LABEL_WIDTH).grid(
            row=0, column=0, sticky="w", padx=(0, SPACE_SM)
        )

    # ─────────────────────────────── SECTIONS ────────────────────────────

    def _build_clinical(self, p):
        self._entry(p, "age", "Age", self._age_var, self._age_error)
        self._entry(p, "bmi", "BMI", self._bmi_var, self._bmi_error)
        self._dropdown(p, "Sex", self._gender_var, list(SEX_OPTIONS.keys()))

        self._switch(p, "Family lung cancer history", self._fhlc_var)
        self._switch(p, "COPD / emphysema", self._copd_var)
        self._switch(p, "Former smoker", self._former_smoker_var)

    def _build_smoking(self, p):
        self._entry(
            p,
            "duration",
            "Smoking duration",
            self._duration_var,
            self._smoking_duration_error_var,
        )
        self._entry(
            p,
            "cigday",
            "Cigarettes/day",
            self._cigday_var,
            self._smoking_intensity_error_var,
        )
        self._entry(
            p,
            "quit",
            "Years since quitting",
            self._quit_var,
            self._smoking_quit_time_error_var,
        )

    def _build_ids(self, p):
        self._entry(p, "study", "Study ID", self._study_var)
        self._entry(p, "pid", "Patient ID", self._pid_var)
        self._entry(p, "nid", "Nodule ID", self._nid_var)

    def _build_radiomics(self, p: ctk.CTkFrame) -> None:
        self._radiomics_box = ctk.CTkTextbox(
            p,
            height=200,
            wrap="none",
            font=ctk.CTkFont(family="Courier", size=12),
            border_width=2,
        )
        self._radiomics_box.pack(fill="x", pady=SPACE_XS)
        self._radiomics_box.insert("1.0", '{\n  "feature_name": value,\n  ...\n}')

        error = ctk.CTkLabel(
            p,
            textvariable=self._rad_error,
            text_color=ERROR_COLOUR,
            font=ctk.CTkFont(size=12),
        )
        error.pack(anchor="w", pady=(SPACE_XS, 0))

    # ─────────────────────────────── WIDGET FACTORIES ────────────────────

    def _entry(
        self,
        parent: ctk.CTkFrame,
        key: str,
        label: str,
        var: tk.StringVar,
        error_var: tk.StringVar | None = None,
    ) -> ctk.CTkEntry:
        r = self._row(parent)
        self._label(r, label)

        container = ctk.CTkFrame(
            r, width=INPUT_WIDTH, fg_color="transparent", border_width=0
        )
        container.grid(row=0, column=1, sticky="w")
        container.grid_propagate(False)

        entry = ctk.CTkEntry(container, textvariable=var)
        entry.pack(fill="both", expand=True)

        self._entries[key] = entry

        if error_var:
            error = ctk.CTkLabel(
                r,
                textvariable=error_var,
                text_color=ERROR_COLOUR,
                font=ctk.CTkFont(size=12),
            )
            error.grid(row=1, column=1, sticky="w", pady=(2, SPACE_XS))

        return entry

    def _switch(self, parent: ctk.CTkFrame, label: str, var: tk.BooleanVar) -> None:
        r = self._row(parent)
        self._label(r, label)
        switch = ctk.CTkSwitch(r, text="", variable=var)
        switch.grid(row=0, column=1, sticky="w")

    def _dropdown(
        self,
        parent: ctk.CTkFrame,
        label: str,
        var: tk.StringVar,
        values: list[str],
    ) -> None:
        r = self._row(parent)
        self._label(r, label)
        container = ctk.CTkFrame(
            r, width=INPUT_WIDTH, fg_color="transparent", border_width=0
        )
        container.grid(row=0, column=1, sticky="w")
        container.grid_propagate(False)
        dropdown = ctk.CTkOptionMenu(container, variable=var, values=values)
        dropdown.pack(fill="both", expand=True)

    # ─────────────────────────────── OVERLAY CONTROL ─────────────────────

    def _show_overlay(self) -> None:
        self._running = True
        self.run_button.configure(state="disabled")
        self._set_widgets_state("disabled")

        # reset overlay to initial state
        self._overlay.show(
            title="Running model...", stage="Preparing inference pipeline"
        )

    def _hide_overlay(self) -> None:
        self._running = False
        self._overlay.hide()
        self.run_button.configure(state="normal")
        self._set_widgets_state("normal")

    def _set_widgets_state(self, state: str) -> None:
        """Recursively enable/disable all input widgets in the form."""

        def _recurse(widget):
            with_state = (
                ctk.CTkEntry,
                ctk.CTkButton,
                ctk.CTkSwitch,
                ctk.CTkOptionMenu,
                ctk.CTkCheckBox,
            )
            if isinstance(widget, with_state):
                with contextlib.suppress(Exception):
                    widget.configure(state=state)
            for child in widget.winfo_children():
                _recurse(child)

        _recurse(self.container)

    # ─────────────────────────────── SUBMIT ──────────────────────────────

    def _on_submit(self):
        if self._running:
            return

        self._clear_errors()

        try:
            data = self._collect()
        except ValueError as exc:
            self._emit("log", str(exc), "ERROR")
            return

        self._show_overlay()
        self.controller.run(data)

    def reset(self) -> None:
        """Clear all inputs and results — called by new_run action."""
        self._age_var.set("")
        self._gender_var.set(SEX_OPTIONS["Male"])
        self._fhlc_var.set(False)
        self._copd_var.set(False)
        self._former_smoker_var.set(False)
        self._duration_var.set("")
        self._cigday_var.set("")
        self._quit_var.set("0")
        self._bmi_var.set("")
        self._study_var.set("")
        self._pid_var.set("")
        self._radiomics_box.delete("1.0", "end")
        self._radiomics_box.insert("1.0", '{\n  "feature_name": value,\n  ...\n}')
        self._clear_errors()
        self._results_frame.pack_forget()

    def _clear_errors(self) -> None:
        self._age_error.set("")
        self._bmi_error.set("")
        self._rad_error.set("")
        self._smoking_duration_error_var.set("")
        self._smoking_intensity_error_var.set("")
        self._smoking_quit_time_error_var.set("")

    # ─────────────────────────────── COLLECT ─────────────────────────────
    def set_entry_error_state(self, key: str, error_var: tk.StringVar):
        entry = self._entries.get(key)
        if not entry or not entry.winfo_exists():
            return

        has_error = bool(error_var.get().strip())
        if has_error:
            entry.configure(border_color=ERROR_COLOUR)
        else:
            entry.configure(border_color=BORDER_COLOUR)

    def _collect(self) -> IntegralRadiomicsInput:

        def validate_field(key, var, err_var, name, min_v=None, max_v=None):
            value = var.get()
            result, errors = self.validator.validate_field(value, name, min_v, max_v)

            err_var.set("\n".join(f"• {e}" for e in errors) if errors else "")

            self.set_entry_error_state(key, err_var)

            return result, errors

        # ───────────────────────── CLINICAL ─────────────────────────

        age, age_errors = validate_field(
            "age", self._age_var, self._age_error, "Age", 0, 120
        )

        bmi, bmi_errors = validate_field(
            "bmi", self._bmi_var, self._bmi_error, "BMI", 0, 100
        )

        duration, duration_errors = validate_field(
            "duration",
            self._duration_var,
            self._smoking_duration_error_var,
            "Duration",
            0,
            100,
        )

        cigday, cigday_errors = validate_field(
            "cigday",
            self._cigday_var,
            self._smoking_intensity_error_var,
            "Cig/day",
            0,
            200,
        )

        quit_time, quit_errors = validate_field(
            "quit",
            self._quit_var,
            self._smoking_quit_time_error_var,
            "Quit time",
            0,
            100,
        )

        # ───────────────────────── RADIOMICS ─────────────────────────

        try:
            raw = self._radiomics_box.get("1.0", "end").strip()
            radiomics = json.loads(raw or "{}")
            rad_errors = IntegralValidator.validate_radiomics(radiomics)
        except Exception:
            rad_errors = ["Radiomics must be valid JSON"]
            radiomics = {}

        self._rad_error.set("\n".join(rad_errors))

        if self._radiomics_box:
            self._radiomics_box.configure(
                border_color=ERROR_COLOUR if rad_errors else BORDER_COLOUR
            )

        # ───────────────────────── BLOCK IF INVALID ─────────────────────────
        # ── collect all errors ──────────────────────

        all_errors = (
            age_errors
            + bmi_errors
            + duration_errors
            + cigday_errors
            + quit_errors
            + rad_errors
        )

        if all_errors:
            raise ValueError(" | ".join(all_errors))

        # ───────────────────────── BUILD MODEL INPUT ─────────────────────────

        clinical = IntegralClinicalData(
            epi_age=age,
            epi_female=SEX_OPTIONS[self._gender_var.get()],
            epi_fhlc=int(self._fhlc_var.get()),
            epi_copdemph=int(self._copd_var.get()),
            epi_formersmk=int(self._former_smoker_var.get()),
            epi_duration=duration,
            epi_cigday=cigday,
            epi_quittime=quit_time,
            epi_bmi=bmi,
            study=self._study_var.get() or None,
            pid=self._pid_var.get() or None,
            nid=self._nid_var.get() or None,
        )

        return IntegralRadiomicsInput(
            clinical=clinical,
            radiomics=RadiomicsFeatures(features=radiomics),
        )

    # ─────────────────────────────── RESULTS ─────────────────────────────
    def _format_result(self, benign, malignant):
        return {
            "Benign": f"{benign:.1%}",
            "Malignant": f"{malignant:.1%}",
            "Decision": "Malignant" if malignant > 0.5 else "Benign",
        }

    def _show_results(self, status_text: str) -> None:
        """Render the results card at the bottom of the form."""
        self._results_label.configure(text=status_text)
        self._results_frame.pack(fill="x", pady=SPACE_SM)

        # scroll to bottom so results are immediately visible
        self.container.after(50, lambda: self.container._parent_canvas.yview_moveto(1))

    # ─────────────────────────────── EVENT HANDLER ───────────────────────

    def handle_event(self, event: AppEvent) -> None:
        """Subscribed to EventBus — runs on Tk main thread."""
        if not self.root.winfo_exists():
            return

        # ───────────────────────────── PROGRESS ─────────────────────────────
        if event.type == "progress":
            value = max(0.0, min(1.0, event.value or 0.0))
            self._overlay.set_progress(value)

        # ───────────────────────────── LOGGING ──────────────────────────────
        elif event.type == "log":
            if self._running and event.message:
                self._overlay.append_log(event.message, event.level)

        # ───────────────────────────── STATE ────────────────────────────────
        elif event.type == "ui_state":
            if event.message == "running":
                self._show_overlay()
            elif event.message in ("idle", "error"):
                self._hide_overlay()

        # ───────────────────────────── RESULT ───────────────────────────────
        elif event.type == "result":
            if not event.data or "benign" not in event.data:
                return

            benign = event.data.get("benign", 0.0)
            malignant = event.data.get("malignant", 0.0)

            # format display
            result_dict = self._format_result(benign, malignant)
            lines = "\n".join(f"{k}: {v}" for k, v in result_dict.items())
            self._show_results(lines)
            self._hide_overlay()
