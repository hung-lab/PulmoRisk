from __future__ import annotations

import contextlib
import tkinter as tk
from functools import partial
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.config.settings import (
    BORDER_COLOUR,
    ERROR_COLOUR,
    WARNING_COLOUR,
    WARNING_COLOUR_HOVER,
)
from app.models.individual_model import (
    IntegralClinicalData,
    ModelValidationError,
)
from app.utils.event_bus import AppEvent
from app.utils.helpers import format_percent
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
from app.utils.validators import FieldParser, ParseError
from app.views.components.loading_overlay import RunningOverlay

if TYPE_CHECKING:
    from app.controllers.integral_controller import IntegralController


# ─────────────────────────────── OPTIONS ───────────────────────────────

NOT_AVAILABLE = "Not available"

SEX_OPTIONS = {
    "Male": 0,
    "Female": 1,
}

# Shared by every tri-state Yes/No field (family history, COPD/emphysema,
# former smoker).
YES_NO_OPTIONS: dict[str, int] = {"No": 0, "Yes": 1}

_FIELD_DISPLAY_NAMES: dict[str, str] = {
    "age": "Age",
    "bmi": "BMI",
    "duration": "Smoking duration",
    "cigday": "Cigarettes per day",
    "quittime": "Smoking quit time",
    "female": "Sex",
    "fhlc": "Family history of lung cancer",
    "copdemph": "COPD / emphysema",
    "formersmk": "Former smoker",
}


class IntegralView:
    def __init__(self, root: ctk.CTkFrame, controller: IntegralController) -> None:
        self.root = root
        self.controller = controller

        self._running = False

        # ── clinical vars ───────────────────────────────
        self._age_var = tk.StringVar()
        self._gender_var = tk.StringVar(value=NOT_AVAILABLE)
        self._fhlc_var = tk.StringVar(value=NOT_AVAILABLE)
        self._copd_var = tk.StringVar(value=NOT_AVAILABLE)
        self._former_smoker_var = tk.StringVar(value=NOT_AVAILABLE)

        self._duration_var = tk.StringVar()
        self._cigday_var = tk.StringVar()
        self._quit_var = tk.StringVar()
        self._bmi_var = tk.StringVar()

        # ── "exactly one field may be missing" support ─────────────────────
        self._ambiguous_field: str | None = None
        self._ambiguous_values: dict[str, int | str] | None = None

        # ── files (image and mask scans) ────────────────
        self._image_file_var = tk.StringVar(value="No file selected")
        self._mask_file_var = tk.StringVar(value="No file selected")

        # ── errors ───────────────────────────────────────
        self._age_error = tk.StringVar()
        self._bmi_error = tk.StringVar()
        self._image_file_error = tk.StringVar()
        self._mask_file_error = tk.StringVar()
        self._smoking_duration_error_var = tk.StringVar()
        self._smoking_intensity_error_var = tk.StringVar()
        self._smoking_quit_time_error_var = tk.StringVar()

        self.run_button: ctk.CTkButton | None = None
        self._results_frame: ctk.CTkFrame | None = None

        self._mode_var = tk.StringVar(value="single")

        self._entries: dict[str, ctk.CTkEntry] = {}

        self._setup_ui()

    # ─────────────────────────────── event helper ─────────────────────────

    def _emit(self, type_: str, message: str = "", level: str = "INFO") -> None:
        self.controller.bus.emit(AppEvent(type=type_, message=message, level=level))

    # ─────────────────────────────── UI SETUP ────────────────────────────

    def _setup_ui(self) -> None:
        self.root.grid_rowconfigure(0, weight=0)  # status
        self.root.grid_rowconfigure(1, weight=1)  # main content
        self.root.grid_columnconfigure(0, weight=1)

        # ─────────────────────────────────────────────────────────────
        # Status Banner
        # ─────────────────────────────────────────────────────────────
        self._status_frame = ctk.CTkFrame(self.root)
        self._status_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=SECTION_GAP_TOP,
            pady=(SPACE_XS, 0),
        )
        self._status_label = ctk.CTkLabel(
            self._status_frame,
            text="",
            justify="left",
            anchor="w",
        )
        self._status_label.pack(fill="x", padx=20, pady=20)
        self._status_frame.grid_forget()

        # ─────────────────────────────────────────────────────────────
        # Scroll container
        # ─────────────────────────────────────────────────────────────

        self.container = ctk.CTkScrollableFrame(self.root, border_width=0)
        self.container.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=SECTION_GAP_TOP,
            pady=SECTION_GAP_BOTTOM,
        )
        self.container.grid_columnconfigure(0, weight=1)

        # ─────────────────────────────────────────────────────────────
        # MODE SELECTOR
        # ─────────────────────────────────────────────────────────────

        top = ctk.CTkFrame(self.container, fg_color="transparent", border_width=0)
        top.pack(fill="x", pady=(10, 0), padx=0)

        ctk.CTkLabel(
            top,
            text="Run Mode",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", pady=(0, SPACE_XS))

        self._mode_switch = ctk.CTkSegmentedButton(
            top,
            values=["single", "batch"],
            variable=self._mode_var,
            command=self._on_mode_changed,
        )
        self._mode_switch.pack(anchor="w")

        # ─────────────────────────────────────────────────────────────
        # Header
        # ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self.container,
            text="INTEGRAL-Radiomics Pulmonary Nodule Malignancy Model",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(SPACE_MD, SPACE_XS))

        self._subtitle = ctk.CTkLabel(
            self.container,
            text="Enter clinical and demographic features",
            text_color=("gray40", "gray90"),
        )
        self._subtitle.pack(anchor="w", pady=(0, SPACE_LG))

        # ─────────────────────────────────────────────────────────────
        # Single individual UI
        # ─────────────────────────────────────────────────────────────
        self._single_frame = ctk.CTkFrame(
            self.container,
            fg_color="transparent",
            border_width=0,
        )
        self._single_frame.pack(fill="both", expand=True)

        self._card("Clinical Data", self._build_clinical, self._single_frame)
        self._card("Smoking History", self._build_smoking, self._single_frame)
        self._card(
            "Image files (Must be NRRD files with .nrrd extension)",
            self._build_ct,
            self._single_frame,
        )

        # ─────────────────────────────────────────────────────────────
        # Batch UI
        # ─────────────────────────────────────────────────────────────
        self._batch_frame = ctk.CTkFrame(
            self.container,
            fg_color="transparent",
            border_width=0,
        )

        batch_card = ctk.CTkFrame(self._batch_frame)
        batch_card.pack(fill="x", pady=CARD_PAD_Y, padx=CARD_PAD_X)

        ctk.CTkLabel(
            batch_card,
            text="Batch CSV Processing",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=SECTION_GAP_BOTTOM, pady=(SPACE_SM, SPACE_XS))

        ctk.CTkLabel(
            batch_card,
            text=(
                "Upload a CSV containing individual metadata and CT scan image and mask files.\n\n"
                "Required columns:\n"
                "- image_file (Full path to image in NRRD format)\n"
                "- mask_file (Full path to nodule mask in NRRD format)\n"
                "- age (In years, 0 to 100)\n"
                "- female (0 = male, 1 = female)\n"
                "- bmi (Body mass index in kg/m^2, 0 to 100)\n"
                "- fhlc (Family history of lung cancer, 0 = No, 1 = Yes)\n"
                "- copdemph (Chronic obstructive pulmonary disease, 0 = No, 1 = Yes)\n"
                "- formersmk (Former smoker, 0 = No, 1 = Yes)\n"
                "- duration (Smoking duration, in years, 0 to 100)\n"
                "- cigday (Cigarettes per day, 0 to 10000)\n"
                "- quittime (Years since quitting, 0 to 100)\n"
            ),
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=SECTION_GAP_BOTTOM, pady=(0, SPACE_MD))

        self.batch_select_button = ctk.CTkButton(
            batch_card,
            text="Select CSV File",
            command=self._on_batch_submit,
            fg_color=WARNING_COLOUR,
            hover_color=WARNING_COLOUR_HOVER,
        )
        self.batch_select_button.pack(
            anchor="w",
            padx=SECTION_GAP_BOTTOM,
            pady=(0, SPACE_MD),
        )

        # ── Example CSV ────────────────────────────────────────────────────────

        ctk.CTkLabel(
            batch_card,
            text="Example CSV",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(
            anchor="w",
            padx=SECTION_GAP_BOTTOM,
            pady=(SPACE_SM, SPACE_XS),
        )

        csv_example = (
            "image_file,mask_file,age,female,bmi,fhlc,copdemph,formersmk,"
            "duration,cigday,quittime\n"
            "/data/patient_001/image.nrrd,/data/patient_001/mask.nrrd,"
            "65,0,27.4,1,0,1,30,20,5\n"
            "/data/patient_002/image.nrrd,/data/patient_002/mask.nrrd,"
            "58,1,31.2,0,1,0,35,15,0\n"
            "/data/patient_003/image.nrrd,/data/patient_003/mask.nrrd,"
            "72,0,25.8,1,0,1,40,25,2"
        )

        example_box = ctk.CTkTextbox(
            batch_card,
            height=100,
            font=ctk.CTkFont(family="Courier", size=11),
        )

        example_box.pack(
            fill="x",
            padx=SECTION_GAP_BOTTOM,
            pady=(0, SPACE_SM),
        )

        example_box.insert("1.0", csv_example)
        example_box.configure(state="disabled")

        # hidden initially
        self._batch_frame.pack_forget()

        # ─────────────────────────────────────────────────────────────
        # Results card
        # ─────────────────────────────────────────────────────────────

        # hidden until a run completes

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

        # ─────────────────────────────────────────────────────────────
        # Bottom action bar
        # ─────────────────────────────────────────────────────────────

        bottom = ctk.CTkFrame(self.root, fg_color="transparent", border_width=0)
        bottom.grid(
            row=2, column=0, sticky="ew", padx=BUTTON_GAP, pady=(SPACE_XS, BUTTON_GAP)
        )
        bottom.grid_columnconfigure(0, weight=1)

        # General validation error (e.g. more than one field left blank) —
        # placed outside the scrollable form so it's always visible without
        # needing the Activity Log panel open.
        self._general_error_var = tk.StringVar()
        self._general_error_label = ctk.CTkLabel(
            bottom,
            textvariable=self._general_error_var,
            text_color=ERROR_COLOUR,
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=600,
            justify="left",
            anchor="w",
        )
        self._general_error_label.grid(row=0, column=0, sticky="ew", pady=(0, SPACE_XS))
        self._general_error_label.grid_remove()

        self.run_button = ctk.CTkButton(
            bottom,
            text="Run INTEGRAL-Radiomics",
            height=44,
            command=self._on_submit,
        )
        self.run_button.grid(row=1, column=0, sticky="ew")

        # ── overlay (lifted during a run) ────────────────────────────────
        self._overlay = RunningOverlay(self.root)

    # ─────────────────────────────── CARD HELPER ─────────────────────────

    def _card(self, title: str, builder, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
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

    def _build_clinical(self, p: ctk.CTkFrame):
        self._entry(p, "age", "Age (years)", self._age_var, self._age_error)
        self._entry(p, "bmi", "BMI (kg/m^2) ", self._bmi_var, self._bmi_error)
        self._dropdown(p, "Sex", self._gender_var, [NOT_AVAILABLE, *SEX_OPTIONS])

        self._tri_state(p, "Family history of lung cancer", self._fhlc_var)
        self._tri_state(p, "COPD / emphysema", self._copd_var)

    def _build_smoking(self, p: ctk.CTkFrame):
        self._tri_state(p, "Former smoker", self._former_smoker_var)
        self._entry(
            p,
            "duration",
            "Smoking duration (years)",
            self._duration_var,
            self._smoking_duration_error_var,
        )
        self._entry(
            p,
            "cigday",
            "Smoking intensity (cig/day)",
            self._cigday_var,
            self._smoking_intensity_error_var,
        )
        self._entry(
            p,
            "quittime",
            "Quit time (years)",
            self._quit_var,
            self._smoking_quit_time_error_var,
        )

    def _build_ct(self, p: ctk.CTkFrame) -> None:
        r = self._row(p)
        self._label(r, "CT Image")

        container = ctk.CTkFrame(
            r, width=INPUT_WIDTH, fg_color="transparent", border_width=0
        )
        container.grid(row=0, column=1, sticky="w")
        container.grid_propagate(False)

        # Path label
        path_label = ctk.CTkLabel(
            container, textvariable=self._image_file_var, anchor="w"
        )
        path_label.pack(fill="both", expand=True)

        # Browse button (same row, new column)
        browse_btn = ctk.CTkButton(
            container,
            text="Browse",
            command=partial(self._browse, self._image_file_var, self._image_file_error),
        )
        browse_btn.pack(anchor="w", pady=(SPACE_XS, 0))

        # Error row
        err_row = self._row(p)

        error = ctk.CTkLabel(
            err_row,
            textvariable=self._image_file_error,
            text_color=ERROR_COLOUR,
            font=ctk.CTkFont(size=12),
        )
        error.grid(row=0, column=1, sticky="w", pady=(SPACE_XS, 0))

        r = self._row(p)
        self._label(r, "Nodule Mask")

        container = ctk.CTkFrame(
            r, width=INPUT_WIDTH, fg_color="transparent", border_width=0
        )
        container.grid(row=0, column=1, sticky="w")
        container.grid_propagate(False)

        # Path label
        path_label = ctk.CTkLabel(
            container, textvariable=self._mask_file_var, anchor="w"
        )
        path_label.pack(fill="both", expand=True)

        # Browse button (same row, new column)
        browse_btn = ctk.CTkButton(
            container,
            text="Browse",
            command=partial(self._browse, self._mask_file_var, self._mask_file_error),
        )
        browse_btn.pack(anchor="w", pady=(SPACE_XS, 0))

        # Error row
        err_row = self._row(p)

        error = ctk.CTkLabel(
            err_row,
            textvariable=self._mask_file_error,
            text_color=ERROR_COLOUR,
            font=ctk.CTkFont(size=12),
        )
        error.grid(row=0, column=1, sticky="w", pady=(SPACE_XS, 0))

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

    def _tri_state(self, parent: ctk.CTkFrame, label: str, var: tk.StringVar) -> None:
        """A No / Yes / Not available selector — defaults to Not available."""
        r = self._row(parent)
        self._label(r, label)

        segmented = ctk.CTkSegmentedButton(
            r, values=[NOT_AVAILABLE, "No", "Yes"], variable=var
        )
        segmented.grid(row=0, column=1, sticky="w")

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

    def _show_overlay(self, batch_mode=False) -> None:
        self._running = True
        self.run_button.configure(state="disabled")
        self._set_widgets_state("disabled")

        # reset overlay to initial state
        self._overlay.show(
            title="Running model...",
            stage="Preparing inference pipeline",
            batch_mode=batch_mode,
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
                ctk.CTkSegmentedButton,
            )
            if isinstance(widget, with_state):
                with contextlib.suppress(Exception):
                    widget.configure(state=state)
            for child in widget.winfo_children():
                _recurse(child)

        _recurse(self.container)

    # ─────────────────────────────── Banner Control ──────────────────────────────
    def _show_unavailable(self, message: str) -> None:
        self._status_label.configure(
            text=message,
            text_color=ERROR_COLOUR,
        )

        self._status_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=SECTION_GAP_TOP,
            pady=(SPACE_XS, 0),
        )

        self.run_button.configure(state="disabled")
        self._set_widgets_state("disabled")

    def _hide_unavailable(self) -> None:
        self._status_frame.grid_forget()

        self.run_button.configure(state="normal")
        self._set_widgets_state("normal")

    # ─────────────────────────────── ACTIONS ──────────────────────────────

    def _browse(self, file_var, file_error) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("NRRD files", "*.nrrd")])
        if file_path:
            file_var.set(file_path)
            file_error.set("")
            self._emit("log", f"Selected file: {file_path}")

    def _on_submit(self):
        if self._running:
            return

        self._clear_errors()

        try:
            data = self._collect()
        except ValueError as exc:
            self._emit("log", str(exc), "ERROR")
            self._set_general_error(str(exc))
            self._results_frame.pack_forget()
            return

        self._show_overlay()
        self.controller.run(
            data,
            ambiguous_field=self._ambiguous_field,
            ambiguous_values=self._ambiguous_values,
        )

    def _on_batch_submit(self) -> None:
        if self._running:
            return

        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])

        if not file_path:
            return

        self._emit("log", f"Selected batch file: {file_path}")

        self._overlay.set_cancel_callback(self.controller.cancel_batch)

        self.controller.run_batch(file_path)

    def _on_mode_changed(self, _=None) -> None:
        mode = self._mode_var.get()

        if mode == "single":
            self._batch_frame.pack_forget()
            self._single_frame.pack(fill="both", expand=True)

            self.run_button.grid()

            self._subtitle.configure(text="Enter clinical + radiomics features")

        else:
            self._single_frame.pack_forget()
            self._batch_frame.pack(fill="both", expand=True)

            self.run_button.grid_remove()

            self._subtitle.configure(
                text="Run INTEGRAL-Radiomics on multiple individuals"
            )

    def reset(self) -> None:
        """Clear all inputs and results — called by new_run action."""
        self._age_var.set("")
        self._gender_var.set(NOT_AVAILABLE)
        self._fhlc_var.set(NOT_AVAILABLE)
        self._copd_var.set(NOT_AVAILABLE)
        self._former_smoker_var.set(NOT_AVAILABLE)
        self._duration_var.set("")
        self._cigday_var.set("")
        self._bmi_var.set("")
        self._image_file_var.set("No file selected")
        self._mask_file_var.set("No file selected")
        self._ambiguous_field = None
        self._ambiguous_values = None
        self._clear_errors()
        self._results_frame.pack_forget()

    def _clear_errors(self) -> None:
        self._age_error.set("")
        self._bmi_error.set("")
        self._image_file_error.set("")
        self._mask_file_error.set("")
        self._smoking_duration_error_var.set("")
        self._smoking_intensity_error_var.set("")
        self._smoking_quit_time_error_var.set("")
        self._set_general_error("")

    def _set_general_error(self, message: str) -> None:
        """Show/hide the always-visible banner above the Run button."""
        self._general_error_var.set(message)
        if message:
            self._general_error_label.grid()
        else:
            self._general_error_label.grid_remove()

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

    def _collect(self) -> IntegralClinicalData:
        """Collect and return validated form data.

        Exactly one field (other than the CT image / nodule mask, which stay
        strictly required) may be left blank / "Not available". A missing
        numeric field is treated as 0; a missing categorical field is
        recorded on self._ambiguous_field / self._ambiguous_values so the
        caller can run the analysis once per option instead of a single
        pass.
        """
        self._ambiguous_field = None
        self._ambiguous_values = None

        parse_errors: dict[str, str] = {}
        fields: dict = {}

        int_fields = [
            ("age", self._age_var, "Age"),
            ("duration", self._duration_var, "Smoking duration"),
            ("cigday", self._cigday_var, "Cig/day"),
            ("quittime", self._quit_var, "Smoking quit time"),
        ]
        categorical_fields = [
            ("female", self._gender_var, SEX_OPTIONS),
            ("fhlc", self._fhlc_var, YES_NO_OPTIONS),
            ("copdemph", self._copd_var, YES_NO_OPTIONS),
            ("formersmk", self._former_smoker_var, YES_NO_OPTIONS),
        ]

        blank_numeric = [f for f, var, _ in int_fields if not var.get().strip()]
        blank_numeric += ["bmi"] if not self._bmi_var.get().strip() else []
        blank_categorical = [
            f for f, var, _ in categorical_fields if var.get() == NOT_AVAILABLE
        ]
        blank_fields = blank_numeric + blank_categorical

        if len(blank_fields) > 1:
            names = ", ".join(_FIELD_DISPLAY_NAMES.get(f, f) for f in blank_fields)
            raise ValueError(
                f"Only one field may be left blank or Not available. "
                f"Currently missing: {names}."
            )

        # ── 1. Numeric fields — the one allowed-blank one becomes 0 ────────
        for field, var, label in int_fields:
            if field in blank_numeric:
                fields[field] = 0
                continue
            try:
                fields[field] = FieldParser.int(field, var.get(), label)
            except ParseError as exc:
                parse_errors[exc.field] = exc.message

        if "bmi" in blank_numeric:
            fields["bmi"] = 0.0
        else:
            try:
                fields["bmi"] = FieldParser.float("bmi", self._bmi_var.get(), "BMI")
            except ParseError as exc:
                parse_errors[exc.field] = exc.message

        if parse_errors:
            self._show_field_errors(parse_errors)  # highlight bad fields
            raise ValueError("Please fix the highlighted fields.")

        # ── 2. Categorical fields — the one allowed-blank one gets a
        #      placeholder value for this run, and every real option is
        #      recorded so the controller can score all of them.
        ambiguous_field = blank_categorical[0] if blank_categorical else None
        if ambiguous_field:
            self._ambiguous_field = ambiguous_field
            self._ambiguous_values = dict(
                next(opts for f, _, opts in categorical_fields if f == ambiguous_field)
            )

        for field, var, opts in categorical_fields:
            fields[field] = (
                next(iter(opts.values())) if field == ambiguous_field else opts[var.get()]
            )

        fields["image_file"] = (
            self._image_file_var.get()
            if self._image_file_var.get() != "No file selected"
            else None
        )
        fields["mask_file"] = (
            self._mask_file_var.get()
            if self._mask_file_var.get() != "No file selected"
            else None
        )

        # ── 3. Construct model — __post_init__ validates business rules ─────
        try:
            return IntegralClinicalData(**fields)
        except ModelValidationError as exc:
            self._show_field_errors(exc.field_errors)  # same helper, same UI path
            raise ValueError("Please fix the highlighted fields.") from exc

    def _show_field_errors(self, errors: dict[str, str]) -> None:
        """Update error StringVars and highlight entry borders."""
        # map model field names → (error_var, entry_key)
        _MAP = {
            "age": (self._age_error, "age"),
            "bmi": (self._bmi_error, "bmi"),
            "duration": (self._smoking_duration_error_var, "smoking_duration"),
            "cigday": (
                self._smoking_intensity_error_var,
                "smoking_intensity",
            ),
            "quittime": (self._smoking_quit_time_error_var, "smoking_quit"),
            "image_file": (self._image_file_error, None),
            "mask_file": (self._mask_file_error, None),
        }
        self._clear_errors()
        for field, msg in errors.items():
            if field in _MAP:
                err_var, entry_key = _MAP[field]
                err_var.set(f"• {msg}")
                if entry_key:
                    self.set_entry_error_state(entry_key, err_var)

    # ─────────────────────────────── RESULTS ─────────────────────────────
    def _format_result(self, lung_cancer_prob):
        return {
            "Lung Cancer Probability": lung_cancer_prob,
            "Lung Cancer Probability Percentage": format_percent(lung_cancer_prob),
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

        elif event.type == "batch_progress":
            current = event.data["current"]
            total = event.data["total"]
            self._overlay.set_batch_progress(
                current,
                total,
            )
            self._overlay.set_stage(f"Running individual {current} of {total}")
        # ───────────────────────────── LOGGING ──────────────────────────────
        elif event.type == "log":
            if self._running and event.message:
                self._overlay.append_log(event.message, event.level)

        # ───────────────────────────── STATE ────────────────────────────────
        elif event.type == "ui_state":
            if event.message == "running_single":
                self._show_overlay(batch_mode=False)

            elif event.message == "running_batch":
                self._show_overlay(batch_mode=True)

            elif event.message == "idle":
                self._hide_overlay()

            elif event.message == "error":
                self._hide_overlay()
                self._results_frame.pack_forget()

        elif event.type == "integral_status":
            if event.message == "R_missing":
                self._show_unavailable(
                    "INTEGRAL-Radiomics is unavailable.\n\nR installation not found."
                )
            elif event.message == "install_failed":
                self._show_unavailable(
                    "INTEGRAL-Radiomics is unavailable.\n\n"
                    "The required R package could not be installed."
                )
            elif event.message in (
                "ready",
                "install_complete",
            ):
                self._hide_unavailable()
        # ───────────────────────────── RESULT ───────────────────────────────
        elif event.type == "radiomics_result":
            if isinstance(event.data, dict) and "output_path" in event.data:
                self._show_results(f"Batch complete. Results saved in:\n{event.data['output_path']}")
                self._hide_overlay()

            elif event.data and event.data.get("results"):
                rows: list[tuple[str, float]] = event.data["results"]
                field_name = _FIELD_DISPLAY_NAMES.get(
                    event.data.get("field"), event.data.get("field")
                )
                width = max(len(label) for label, _ in rows)
                lines = [
                    f"{field_name} was Not available — showing the result for "
                    "every option:",
                    "",
                ]
                lines += [
                    f"  {label.ljust(width)} : {format_percent(prob)}"
                    for label, prob in rows
                ]
                self._show_results("\n".join(lines))
                self._hide_overlay()

            elif not event.data or "probability" not in event.data:
                return

            else:
                lung_cancer_prob = event.data.get("probability", 0.0)
                # format display
                result_dict = self._format_result(lung_cancer_prob)
                lines = "\n".join(f"{k}: {v}" for k, v in result_dict.items())
                self._show_results(lines)
                self._hide_overlay()

        elif event.type == "ui_theme":
            self._overlay.update_tag_colours(event.message)
