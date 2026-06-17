from __future__ import annotations

import contextlib
import tkinter as tk
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.config.settings import (
    BORDER_COLOUR,
    ERROR_COLOUR,
    WARNING_COLOUR,
    WARNING_COLOUR_HOVER,
)
from app.models.patient_model import ModelValidationError, SybilInputData
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
from app.utils.validators import FieldParser, ParseError
from app.views.components.loading_overlay import RunningOverlay

if TYPE_CHECKING:
    from app.controllers.sybil_controller import SybilController


# ── Option maps (display label → integer code stored in SybilInputData) ──────

EDUCATION_OPTIONS: dict[str, int] = {
    "Less than high school graduate": 1,
    "High school graduate": 2,
    "Some training after high school": 3,
    "Some college": 4,
    "College graduate": 5,
    "Postgraduate / professional degree": 6,
}

ETHNICITY_OPTIONS: dict[str, int] = {
    "White": 1,
    "Black": 2,
    "Asian": 3,
    "Others": 4,
}

# Overlay stage labels keyed by the log messages the controller emits.
_STAGE_LABELS: dict[str, str] = {
    "Running Sybil": "Running CT analysis…",
    "Computing EPI": "Computing risk score…",
    "Sybil model ready": "Model ready — starting inference…",
}


class SybilView:
    def __init__(self, root: ctk.CTkFrame, controller: SybilController) -> None:
        self.root = root
        self.controller = controller

        self._running = False

        # ── form state vars ───────────────────────────────────────────────
        self._age_var = tk.StringVar()
        self._bmi_var = tk.StringVar()
        self._copd_var = tk.BooleanVar(value=False)
        self._education_var = tk.StringVar(value=next(iter(EDUCATION_OPTIONS)))
        self._ethnicity_var = tk.StringVar(value=next(iter(ETHNICITY_OPTIONS)))
        self._family_lc_var = tk.BooleanVar(value=False)
        self._personal_cancer_var = tk.BooleanVar(value=False)
        self._smoking_duration_var = tk.StringVar()
        self._smoking_intensity_var = tk.StringVar()
        self._smoking_quit_time_var = tk.StringVar(value="0")
        self._smoking_status_var = tk.BooleanVar(value=False)
        self._ct_dir_var = tk.StringVar(value="No folder selected")
        self._six_year_risk = tk.StringVar()

        # ── validation error vars ─────────────────────────────────────────
        self._age_error_var = tk.StringVar()
        self._bmi_error_var = tk.StringVar()
        self._ct_error_var = tk.StringVar()
        self._smoking_duration_error_var = tk.StringVar()
        self._smoking_intensity_error_var = tk.StringVar()
        self._smoking_quit_time_error_var = tk.StringVar()
        self._six_year_risk_error_var = tk.StringVar()

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
            text="Sybil-Epi Lung Cancer Risk Model",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(SPACE_MD, SPACE_XS))

        self._subtitle = ctk.CTkLabel(
            self.container,
            text="Enter information to compute risk score",
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

        self._card("Demographics", self._build_patient, self._single_frame)
        self._card("Medical History", self._build_history, self._single_frame)
        self._card("Smoking History", self._build_smoking, self._single_frame)
        self._card("CT Scan", self._build_ct, self._single_frame)

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
                "Upload a CSV containing patient metadata and CT scan folder paths.\n\n"
                "Required columns:\n"
                "- age\n"
                "- bmi\n"
                "- copd\n"
                "- education\n"
                "- ethnicity\n"
                "- family_lc_history\n"
                "- personal_cancer_history\n"
                "- smoking_duration\n"
                "- smoking_intensity\n"
                "- smoking_quit_time\n"
                "- smoking_status\n"
                "- ct_scan_dir\n\n"
                "Optional:\n"
                "- six_year_risk"
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
            row=2,
            column=0,
            sticky="ew",
            padx=BUTTON_GAP,
            pady=(SPACE_XS, BUTTON_GAP),
        )
        bottom.grid_columnconfigure(0, weight=1)

        self.run_button = ctk.CTkButton(
            bottom,
            text="Run Sybil-Epi",
            height=44,
            command=self._on_submit,
        )
        self.run_button.grid(row=0, column=0, sticky="ew")

        # ── overlay (lifted during a run) ────────────────────────────────
        self._overlay = RunningOverlay(self.root)

    # ─────────────────────────────── CARD HELPER ─────────────────────────

    def _card(self, title: str, builder, parent) -> None:
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

    # ─────────────────────────────── FORM SECTIONS ───────────────────────

    def _build_patient(self, p: ctk.CTkFrame) -> None:
        self._entry(p, "age", "Age (years)", self._age_var, self._age_error_var)
        self._entry(p, "bmi", "BMI (kg/m2)", self._bmi_var, self._bmi_error_var)
        self._dropdown(p, "Education", self._education_var, list(EDUCATION_OPTIONS))
        self._dropdown(p, "Ethnicity", self._ethnicity_var, list(ETHNICITY_OPTIONS))

    def _build_history(self, p: ctk.CTkFrame) -> None:
        self._switch(p, "COPD", self._copd_var)
        self._switch(p, "Family history of lung cancer", self._family_lc_var)
        self._switch(p, "Personal history of any cancer", self._personal_cancer_var)

    def _build_smoking(self, p: ctk.CTkFrame) -> None:
        self._switch(p, "Current smoker", self._smoking_status_var)
        self._entry(
            p,
            "smoking_duration",
            "Smoking duration (years)",
            self._smoking_duration_var,
            self._smoking_duration_error_var,
        )
        self._entry(
            p,
            "smoking_intensity",
            "Smoking intensity (cig/day)",
            self._smoking_intensity_var,
            self._smoking_intensity_error_var,
        )
        self._entry(
            p,
            "smoking_quit",
            "Quit time (years)",
            self._smoking_quit_time_var,
            self._smoking_quit_time_error_var,
        )

    def _build_ct(self, p: ctk.CTkFrame) -> None:
        r = self._row(p)
        self._label(r, "CT Scan Folder")

        container = ctk.CTkFrame(
            r, width=INPUT_WIDTH, fg_color="transparent", border_width=0
        )
        container.grid(row=0, column=1, sticky="w")
        container.grid_propagate(False)

        # Path label
        path_label = ctk.CTkLabel(container, textvariable=self._ct_dir_var, anchor="w")
        path_label.pack(fill="both", expand=True)

        # Browse button (same row, new column)
        browse_btn = ctk.CTkButton(container, text="Browse", command=self._browse)
        browse_btn.pack(anchor="w", pady=(SPACE_XS, 0))

        # Error row
        err_row = self._row(p)

        error = ctk.CTkLabel(
            err_row,
            textvariable=self._ct_error_var,
            text_color=ERROR_COLOUR,
            font=ctk.CTkFont(size=12),
        )
        error.grid(row=0, column=1, sticky="w", pady=(SPACE_XS, 0))
        self._entry(
            p,
            "risk",
            "6-year Risk Sybil",
            self._six_year_risk,
            self._six_year_risk_error_var,
        )

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

    # ─────────────────────────────── ACTIONS ─────────────────────────────

    def _browse(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self._ct_dir_var.set(folder)
            self._ct_error_var.set("")
            self._emit("log", f"Selected CT folder: {folder}")

    def _on_submit(self) -> None:
        if self._running:
            return

        self._clear_errors()

        try:
            data = self._collect()
        except ValueError as exc:
            self._emit("log", str(exc), "ERROR")
            return

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

            self._subtitle.configure(text="Enter information to compute risk score")

        else:
            self._single_frame.pack_forget()
            self._batch_frame.pack(fill="both", expand=True)

            self.run_button.grid_remove()

            self._subtitle.configure(text="Run Sybil-Epi on multiple individuals")

    def reset(self) -> None:
        """Clear all inputs and results — called by new_run action."""
        self._age_var.set("")
        self._bmi_var.set("")
        self._copd_var.set(False)
        self._education_var.set(next(iter(EDUCATION_OPTIONS)))
        self._ethnicity_var.set(next(iter(ETHNICITY_OPTIONS)))
        self._family_lc_var.set(False)
        self._personal_cancer_var.set(False)
        self._smoking_duration_var.set("")
        self._smoking_intensity_var.set("")
        self._smoking_quit_time_var.set("0")
        self._smoking_status_var.set(False)
        self._ct_dir_var.set("No folder selected")
        self._six_year_risk.set("")
        self._clear_errors()
        self._results_frame.pack_forget()

    def _clear_errors(self) -> None:
        self._age_error_var.set("")
        self._bmi_error_var.set("")
        self._ct_error_var.set("")
        self._smoking_duration_error_var.set("")
        self._smoking_intensity_error_var.set("")
        self._smoking_quit_time_error_var.set("")
        self._six_year_risk_error_var.set("")

        self._clear_error_state()

    def _clear_error_state(self) -> None:
        for entry in self._entries.values():
            if entry.winfo_exists():
                entry.configure(border_color=BORDER_COLOUR)

    # ─────────────────────────────── VALIDATION ──────────────────────────

    def set_entry_error_state(self, key: str, error_var: tk.StringVar):
        entry = self._entries.get(key)
        if not entry or not entry.winfo_exists():
            return

        has_error = bool(error_var.get().strip())
        if has_error:
            entry.configure(border_color=ERROR_COLOUR)
        else:
            entry.configure(border_color=BORDER_COLOUR)

    def _collect(self) -> SybilInputData:
        """Collect and return validated form data."""
        parse_errors: dict[str, str] = {}

        # ── 1. Parse strings → Python types ────────────────────────────────
        # Collect ALL parse errors before raising so every bad field is shown.
        fields: dict = {}

        for field, var, label in [
            ("age", self._age_var, "Age"),
            ("bmi", self._bmi_var, "BMI"),
            ("smoking_duration", self._smoking_duration_var, "Smoking duration"),
            ("smoking_intensity", self._smoking_intensity_var, "Smoking intensity"),
            ("smoking_quit_time", self._smoking_quit_time_var, "Smoking quit time"),
        ]:
            try:
                fields[field] = FieldParser.float(field, var.get(), label)
            except ParseError as exc:
                parse_errors[exc.field] = exc.message

        try:
            fields["six_year_risk"] = FieldParser.optional_float(
                "six_year_risk", self._six_year_risk.get(), "6-year Sybil risk"
            )
        except ParseError as exc:
            parse_errors[exc.field] = exc.message

        if parse_errors:
            self._show_field_errors(parse_errors)  # highlight bad fields
            raise ValueError("Please fix the highlighted fields.")

        # ── 2. Map dropdowns / booleans ────────────────────────────────────
        fields.update(
            copd=int(self._copd_var.get()),
            education=EDUCATION_OPTIONS.get(self._education_var.get(), 1),
            ethnicity=ETHNICITY_OPTIONS.get(self._ethnicity_var.get(), 1),
            family_lc_history=int(self._family_lc_var.get()),
            personal_cancer_history=int(self._personal_cancer_var.get()),
            smoking_status=int(self._smoking_status_var.get()),
            ct_scan_dir=self._ct_dir_var.get()
            if self._ct_dir_var.get() != "No folder selected"
            else None,
        )

        # ── 3. Construct model — __post_init__ validates business rules ─────
        try:
            return SybilInputData(**fields)
        except ModelValidationError as exc:
            self._show_field_errors(exc.field_errors)  # same helper, same UI path
            raise ValueError("Please fix the highlighted fields.") from exc

    def _show_field_errors(self, errors: dict[str, str]) -> None:
        """Update error StringVars and highlight entry borders."""
        # map model field names → (error_var, entry_key)
        _MAP = {
            "age": (self._age_error_var, "age"),
            "bmi": (self._bmi_error_var, "bmi"),
            "smoking_duration": (self._smoking_duration_error_var, "smoking_duration"),
            "smoking_intensity": (
                self._smoking_intensity_error_var,
                "smoking_intensity",
            ),
            "smoking_quit_time": (self._smoking_quit_time_error_var, "smoking_quit"),
            "ct_scan_dir": (self._ct_error_var, None),
            "six_year_risk": (self._six_year_risk_error_var, "risk"),
        }
        self._clear_errors()
        for field, msg in errors.items():
            if field in _MAP:
                err_var, entry_key = _MAP[field]
                err_var.set(f"• {msg}")
                if entry_key:
                    self.set_entry_error_state(entry_key, err_var)

    # ─────────────────────────────── RESULTS ─────────────────────────────

    def _show_results(self, status_text: str) -> None:
        """Render the results card at the bottom of the form."""
        self._results_label.configure(text=status_text)
        self._results_frame.pack(fill="x", pady=SPACE_SM)

        # scroll to bottom so results are immediately visible
        self.container.after(50, lambda: self.container._parent_canvas.yview_moveto(1))

    # ─────────────────────────────── EVENT HANDLER ───────────────────────

    def handle_event(self, event: AppEvent) -> None:
        """Subscribed to the EventBus — always called on the Tk main thread."""
        if not self.root.winfo_exists():
            return

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

        elif event.type == "log":
            if self._running and event.message:
                # Forward every log line to the overlay's live feed
                self._overlay.append_log(event.message, event.level)

                # Also update the stage subtitle for key milestones
                for key, label in _STAGE_LABELS.items():
                    if key in event.message:
                        self._overlay.set_stage(label)
                        break

        elif event.type == "ui_state":
            if event.message == "running_single":
                self._show_overlay(batch_mode=False)

            elif event.message == "running_batch":
                self._show_overlay(batch_mode=True)

            elif event.message in ("idle", "error"):
                self._hide_overlay()

        elif event.type == "sybil_result":
            if isinstance(event.data, dict) and "output_path" in event.data:
                self._show_results(f"Batch complete:\n{event.data['output_path']}")
                # self._hide_overlay()
            elif event.data:
                yearly = event.data.get("yearly", [])
                epi = event.data.get("epi", 0.0)
                lines = [f"Year {i + 1}: {v:.1%}" for i, v in enumerate(yearly)]
                lines += ["", f"Final 6-year risk: {epi:.1%}"]
                self._show_results("\n".join(lines))
