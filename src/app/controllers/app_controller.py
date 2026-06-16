import os
import shutil
import subprocess
from pathlib import Path

import certifi
import customtkinter as ctk

from app.controllers.base_controller import BaseController
from app.utils.event_bus import AppEvent, EventBus
from app.utils.helpers import find_integral_cli

os.environ["CURL_CA_BUNDLE"] = certifi.where()


class AppController(BaseController):
    """Handles top-level UI events: layout toggles, theme, lifecycle."""

    def __init__(self, root, bus: EventBus, split_view, sybil_form):
        super().__init__(root, bus)
        self._split = split_view
        self._form = sybil_form
        bus.subscribe(self._handle_event)

    def _handle_event(self, event: AppEvent):
        if event.type == "ui_toggle":
            if event.message == "log_panel":
                self._split.toggle_right_panel()

        elif event.type == "ui_state":
            if event.message in ("running", "running_single", "running_batch"):
                self._split.lock_tabs()
            elif event.message in ("idle", "error"):
                self._split.unlock_tabs()

        elif event.type == "action":
            if event.message == "new_run":
                self._form.reset()

        elif event.type == "ui_theme":
            ctk.set_appearance_mode(event.message or "System")

        elif event.type == "app" and event.message == "quit":
            self.root.quit()

    # called by menubar view
    def toggle_log(self):
        self.bus.emit(AppEvent(type="ui_toggle", message="log_panel"))

    def new_run(self):
        self.bus.emit(AppEvent(type="action", message="new_run"))

    def change_appearance(self, mode: str):
        self.bus.emit(AppEvent(type="ui_theme", message=mode))

    def quit_app(self):
        self.bus.emit(AppEvent(type="app", message="quit"))

    def check_and_install_integral(self):
        """Check/install integralrad safely on app launch."""
        CH = {"channel": "integral"}

        try:
            self._log("Checking R dependencies", data=CH)

            # ───────────────────────────────
            # 1. Check R exists
            # ───────────────────────────────
            if not shutil.which("Rscript"):
                self._log("R is not installed", level="ERROR", data=CH)
                self._emit(AppEvent(type="ui_state", message="R_missing"))
                return

            # ───────────────────────────────
            # 2. PATH for CLI
            # ───────────────────────────────
            user_bin = Path.home() / ".local" / "bin"
            os.environ["PATH"] = f"{user_bin}:{os.environ.get('PATH', '')}"

            if find_integral_cli():
                self._log("integral-radiomics already installed", data=CH)
                self._emit(
                    AppEvent(type="ui_state", message="integral_radiomics_ready")
                )
                return

            self._log("Installing integralrad (first run setup)…", data=CH)

            # ───────────────────────────────
            # 3. Stable R library path
            # ───────────────────────────────
            r_lib = Path.home() / "R" / "library"
            r_lib.mkdir(parents=True, exist_ok=True)

            # ───────────────────────────────
            # 4. CLEAN R SCRIPT (NO INDENTATION, NO MIXED SYSTEMS)
            # ───────────────────────────────
            r_script = f"""
        options(repos = c(CRAN = "https://cloud.r-project.org"))

        Sys.setenv(R_LIBS_USER = "{r_lib}")
        .libPaths(c("{r_lib}", .libPaths()))

        if (!requireNamespace("remotes", quietly = TRUE)) {{
            install.packages("remotes")
        }}

        remotes::install_github("mattwarkentin/INTEGRAL-Radiomics", upgrade = "never")

        library(integralrad)

        integralrad::install_integralrad_cli()
        """

            script_path = Path("/tmp/install_integralrad.R")
            script_path.write_text(r_script)

            # ───────────────────────────────
            # 5. SAFE ENV
            # ───────────────────────────────
            env = os.environ.copy()
            env["R_LIBS_USER"] = str(r_lib)
            env["TMPDIR"] = "/tmp"
            env["HOME"] = str(Path.home())

            try:
                subprocess.run(
                    ["Rscript", "--vanilla", str(script_path)],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                )

            except subprocess.CalledProcessError as e:
                self._log(f"Install failed:\n{e.stderr}", level="ERROR", data=CH)
                self._emit(AppEvent(type="ui_state", message="install_failed"))
                return

            # ───────────────────────────────
            # 6. VERIFY
            # ───────────────────────────────
            if find_integral_cli():
                self._log("integralrad installed successfully", data=CH)
                self._emit(AppEvent(type="ui_state", message="install_complete"))
            else:
                self._log("Install finished but CLI not found", level="ERROR", data=CH)
                self._emit(AppEvent(type="ui_state", message="install_failed"))

        except Exception as exc:
            # Safety net so the splash screen never waits forever if
            # something unexpected blows up here.
            self._log(f"Unexpected error during R setup: {exc}", level="ERROR", data=CH)
            self._emit(AppEvent(type="ui_state", message="install_failed"))
