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
from app.models.patient_model import (
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

SEX_OPTIONS = {
    "Male": 0,
    "Female": 1,
}


class IntegralView:
    def __init__(self, root: ctk.CTkFrame, controller: IntegralController) -> None:
        self.root = root
        self.controller = controller

        self._running = False

        # ── clinical vars ───────────────────────────────
        self._age_var = tk.StringVar()
        self._gender_var = tk.StringVar(value="Male")
        self._fhlc_var = tk.BooleanVar(value=False)
        self._copd_var = tk.BooleanVar(value=False)
        self._former_smoker_var = tk.BooleanVar(value=False)

        self._duration_var = tk.StringVar()
        self._cigday_var = tk.StringVar()
        self._quit_var = tk.StringVar()
        self._bmi_var = tk.StringVar()

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
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # ─────────────────────────────────────────────────────────────
        # MODE SELECTOR
        # ─────────────────────────────────────────────────────────────

        top = ctk.CTkFrame(self.root, fg_color="transparent", border_width=0)
        top.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=SECTION_GAP_TOP,
            pady=(SECTION_GAP_TOP, 0),
        )

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
        # Single patient UI
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
                "Upload a CSV containing patient metadata and CT scan image and mask files.\n\n"
                "Required columns:\n"
                "- image_file (Path to image (NRRD format))\n"
                "- mask_file (Path to nodule mask (NRRD format))\n"
                "- age (Years [0 - 100])\n"
                "- female (0 = male, 1 = female)\n"
                "- bmi (Body mass index (kg/m^2) [15.0 - 50.0])\n"
                "- fhlc (family lung cancer history: 0 or 1)\n"
                "- copdemph (OPD / emphysema: 0 or 1)\n"
                "- formersmk (former smoker: 0 or 1)\n"
                "- duration (smoking duration (years) [0 - age])\n"
                "- cigday (cigarettes per day [0 - 100])\n"
                "- quittime (years since quitting [0 - age])\n\n"
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

        self.run_button = ctk.CTkButton(
            bottom,
            text="Run INTEGRAL-Radiomics",
            height=44,
            command=self._on_submit,
        )
        self.run_button.grid(row=0, column=0, sticky="ew")

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
        self._dropdown(p, "Sex", self._gender_var, list(SEX_OPTIONS.keys()))

        self._switch(p, "Family history of lung cancer", self._fhlc_var)
        self._switch(p, "COPD / emphysema", self._copd_var)

    def _build_smoking(self, p: ctk.CTkFrame):
        self._switch(p, "Former smoker", self._former_smoker_var)
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
            )
            if isinstance(widget, with_state):
                with contextlib.suppress(Exception):
                    widget.configure(state=state)
            for child in widget.winfo_children():
                _recurse(child)

        _recurse(self.container)

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
            return

        self._show_overlay()
        self.controller.run(data)

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
        self._gender_var.set(SEX_OPTIONS["Male"])
        self._fhlc_var.set(False)
        self._copd_var.set(False)
        self._former_smoker_var.set(False)
        self._duration_var.set("")
        self._cigday_var.set("")
        self._quit_var.set("0")
        self._bmi_var.set("")
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

    def _collect(self) -> IntegralClinicalData:
        """Collect and return validated form data."""
        parse_errors: dict[str, str] = {}

        # ── 1. Parse strings → Python types ────────────────────────────────
        # Collect ALL parse errors before raising so every bad field is shown.
        fields: dict = {}

        for field, var, label in [
            ("age", self._age_var, "Age"),
            ("duration", self._duration_var, "Smoking duration"),
            ("cigday", self._cigday_var, "Cig/day"),
            ("quittime", self._quit_var, "Smoking quit time"),
        ]:
            try:
                fields[field] = FieldParser.int(field, var.get(), label)
            except ParseError as exc:
                parse_errors[exc.field] = exc.message

        try:
            fields["bmi"] = FieldParser.float("bmi", self._bmi_var.get(), "BMI")
        except ParseError as exc:
            parse_errors[exc.field] = exc.message

        if parse_errors:
            self._show_field_errors(parse_errors)  # highlight bad fields
            raise ValueError("Please fix the highlighted fields.")

        # ── 2. Map dropdowns / booleans ────────────────────────────────────
        fields.update(
            female=SEX_OPTIONS[self._gender_var.get()],
            fhlc=int(self._fhlc_var.get()),
            copdemph=int(self._copd_var.get()),
            formersmk=int(self._former_smoker_var.get()),
            image_file=self._image_file_var.get()
            if self._image_file_var.get() != "No file selected"
            else None,
            mask_file=self._mask_file_var.get()
            if self._mask_file_var.get() != "No file selected"
            else None,
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
            self._overlay.set_stage(f"Running patient {current} of {total}")
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

            elif event.message in ("idle", "error"):
                self._hide_overlay()

        # ───────────────────────────── RESULT ───────────────────────────────
        elif event.type == "radiomics_result":
            if isinstance(event.data, dict) and "output_path" in event.data:
                self._show_results(f"Batch complete:\n{event.data['output_path']}")

            elif not event.data or "probability" not in event.data:
                return

            else:
                lung_cancer_prob = event.data.get("probability", 0.0)
                # format display
                result_dict = self._format_result(lung_cancer_prob)
                lines = "\n".join(f"{k}: {v}" for k, v in result_dict.items())
                self._show_results(lines)
                self._hide_overlay()
