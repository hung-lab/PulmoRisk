from __future__ import annotations

import contextlib
import tkinter as tk
from functools import partial
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.config.settings import BORDER_COLOUR, ERROR_COLOUR
from app.models.patient_model import (
    IntegralClinicalData,
    IntegralRadiomicsInput,
)
from app.utils.event_bus import AppEvent
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


# ─────────────────────────────── OPTIONS ───────────────────────────────

SEX_OPTIONS = {
    "Male": 0,
    "Female": 1,
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
        self._card("Image files", self._build_ct)

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
        self._label(r, "CT Mask")

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

    # ─────────────────────────────── ACTIONS ──────────────────────────────

    def _browse(self, file_var, file_error) -> None:
        file_path = filedialog.askopenfilename()
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
        self._image_file_var.set("No file selected")
        self._mask_file_var.set("No file selected")
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

        ct_errors = []
        image_error = ""
        mask_error = ""

        if self._image_file_var.get() == "No file selected":
            image_error = "Image file is required"
            ct_errors.append(image_error)

        if self._mask_file_var.get() == "No file selected":
            mask_error = "Mask file is required"
            ct_errors.append(mask_error)

        self._image_file_error.set(image_error)
        self._mask_file_error.set(mask_error)

        # ───────────────────────── BLOCK IF INVALID ─────────────────────────
        # ── collect all errors ──────────────────────

        all_errors = (
            age_errors
            + bmi_errors
            + duration_errors
            + cigday_errors
            + quit_errors
            + ct_errors
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
            image_file=self._image_file_var.get(),
            mask_file=self._mask_file_var.get(),
        )

        return IntegralRadiomicsInput(
            clinical=clinical,
        )

    # ─────────────────────────────── RESULTS ─────────────────────────────
    def _format_result(self, lung_cancer_prob):
        return {
            "Lung Cancer Probabilty": f"{lung_cancer_prob:.1%}",
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
        elif event.type == "radiomics_result":
            if not event.data or "probability" not in event.data:
                return

            lung_cancer_prob = event.data.get("probability", 0.0)

            # format display
            result_dict = self._format_result(lung_cancer_prob)
            lines = "\n".join(f"{k}: {v}" for k, v in result_dict.items())
            self._show_results(lines)
            self._hide_overlay()
