import os
import platform
import subprocess  # nosec B404
import tempfile
from pathlib import Path

import certifi
import customtkinter as ctk

from app.controllers.base_controller import BaseController
from app.utils.event_bus import AppEvent, EventBus
from app.utils.helpers import find_integral_cli, find_rscript, r_package_installed

os.environ["CURL_CA_BUNDLE"] = certifi.where()


class AppController(BaseController):
    """Handles top-level UI events: layout toggles, theme, lifecycle."""

    def __init__(self, root, bus: EventBus, split_view, sybil_form, integral_form):
        super().__init__(root, bus)
        self._split = split_view
        self._form_sybil = sybil_form
        self._form_integral = integral_form
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
                self._form_sybil.reset()
                self._form_integral.reset()

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

    # ─────────────────────────────── R SETUP ──────────────────────────────

    @staticmethod
    def _ubuntu_codename() -> str:
        """Return the Ubuntu release codename (e.g. 'jammy', 'focal').

        Used to pick the correct Posit Package Manager binary URL.
        Falls back to 'jammy' (22.04 LTS) if the release cannot be detected.
        """
        try:
            lines = Path("/etc/os-release").read_text().splitlines()
            for line in lines:
                if line.startswith("UBUNTU_CODENAME="):
                    return line.split("=", 1)[1].strip().strip('"')
                if line.startswith("VERSION_CODENAME="):
                    return line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass
        return "jammy"

    def _cran_repo(self, CH):
        system = platform.system().lower()

        if system == "linux":
            codename = self._ubuntu_codename()
            ppm_url = (
                f"https://packagemanager.posit.co/cran/__linux__/{codename}/latest"
            )
            self._log(f"Using PPM binary repo for Linux {codename}: {ppm_url}", data=CH)
            return ppm_url

        if system == "darwin":
            ppm_url = "https://packagemanager.posit.co/cran/latest"
            self._log(f"Using PPM CRAN repo for macOS: {ppm_url}", data=CH)
            return ppm_url

        if system == "windows":
            ppm_url = "https://packagemanager.posit.co/cran/latest"
            self._log(f"Using PPM CRAN repo for Windows: {ppm_url}", data=CH)
            return ppm_url

        ppm_url = "https://cloud.r-project.org"
        self._log(f"Using fallback CRAN repo: {ppm_url}", data=CH)
        return ppm_url

    def check_and_install_integral(self):
        """Check / install integralrad safely on app launch.

        Uses Posit Package Manager (PPM) to fetch pre-compiled Linux binaries
        so that packages like openssl, curl, fs and yaml12 do NOT need to be
        compiled from source — avoiding the libssl-dev / libuv / rustc deps.
        """
        CH = {"channel": "integral"}

        try:
            self._log("Checking R dependencies", data=CH)

            # ── 1. Rscript ────────────────────────────────────────────────
            rscript_path = find_rscript()
            if not rscript_path:
                self._log(
                    "R is not installed or Rscript could not be found",
                    level="ERROR",
                    data=CH,
                )
                self._emit(AppEvent(type="ui_state", message="R_missing"))
                self._emit(AppEvent(type="integral_status", message="R_missing"))
                return

            self._log(f"Using Rscript at: {rscript_path}", data=CH)

            # ── 2. PATH for CLI ───────────────────────────────────────────
            user_bin = Path.home() / ".local" / "bin"
            os.environ["PATH"] = f"{user_bin}:{os.environ.get('PATH', '')}"

            if not r_package_installed(rscript_path, "integralrad"):
                self._log(
                    "integralrad not found in R library — will install now…",
                    level="WARNING",
                    data=CH,
                )
                # falls through to the install script below

            cli_path = find_integral_cli()
            if cli_path:
                self._log(
                    f"integral-radiomics already installed at: {cli_path}", data=CH
                )
                self._emit(
                    AppEvent(type="ui_state", message="integral_radiomics_ready")
                )
                self._emit(AppEvent(type="integral_status", message="ready"))
                return

            self._log("Installing integralrad (first run setup)…", data=CH)

            # ── 3. Writable R library ─────────────────────────────────────
            r_lib = Path.home() / ".pulmorisk" / "r" / "library"
            r_lib.mkdir(parents=True, exist_ok=True)

            # ── 4. Detect PPM  URL by OS ──────────────
            ppm_url = self._cran_repo(CH)

            # ── 5. R install script ───────────────────────────────────────
            #
            # Key points:
            #   • PPM is set as the PRIMARY repo so R downloads pre-built
            #     .deb-style binaries instead of compiling from source.
            #     This avoids needing libssl-dev, libcurl4-openssl-dev,
            #     libuv1-dev, rustc, etc.
            #   • CRAN is kept as a fallback for packages PPM doesn't have.
            #   • pak is used for dependency resolution; it respects the
            #     binary-first repos option automatically.
            #   • integralrad is installed only if not already present.
            #   • install_integralrad_cli() installs the CLI binary to
            #     ~/.local/bin for later subprocess use.
            #
            r_script = f"""
lib <- "{r_lib}"
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))

# ── Use Posit Package Manager for pre-compiled Linux binaries ──────────────
# This prevents source compilation of openssl, curl, fs, yaml12, etc.
options(
  repos = c(
    PPM  = "{ppm_url}",
    CRAN = "https://cloud.r-project.org"
  )
)

if (Sys.info()[["sysname"]] == "Darwin") {{
    options(pkgType = "source")
}}

# ── Install pak if missing (pak itself comes as a binary from PPM) ─────────
if (!requireNamespace("pak", quietly = TRUE)) {{
    install.packages("pak", lib = lib)
}}

# ── Install integralrad and all its dependencies via pak ──────────────────
# pak resolves the full dependency tree and downloads binaries in parallel.
if (!requireNamespace("integralrad", quietly = TRUE)) {{
    pak::pak(
        "mattwarkentin/INTEGRAL-Radiomics",
        lib = lib,
        upgrade = FALSE
    )
}}

# ── Verify and install CLI ─────────────────────────────────────────────────
library(integralrad)

if (is.function(integralrad::install_integralrad_cli)) {{
    integralrad::install_integralrad_cli()
}}

cat("integralrad OK\\n")
"""

            script_path = Path.home() / ".pulmorisk" / "r" / "install_integralrad.R"
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(r_script)

            # ── 6. Run R ──────────────────────────────────────────────────
            env = os.environ.copy()
            env.update(
                {
                    "R_LIBS_USER": str(r_lib),
                    "R_LIBS": str(r_lib),
                    "HOME": str(Path.home()),
                    "TMPDIR": tempfile.gettempdir(),
                    # Prevent R from opening a browser for package vignettes
                    "R_BROWSER": "false",
                }
            )

            try:
                result = subprocess.run(
                    [rscript_path, "--vanilla", str(script_path)],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                # Surface R's stderr to the log so progress is visible
                if result.stderr:
                    for line in result.stderr.strip().splitlines():
                        self._log(line, data=CH)

            except subprocess.CalledProcessError as e:
                # Log both streams so the user can see exactly what failed
                if e.stderr:
                    for line in e.stderr.strip().splitlines():
                        self._log(line, level="ERROR", data=CH)
                self._emit(AppEvent(type="ui_state", message="install_failed"))
                self._emit(AppEvent(type="integral_status", message="install_failed"))
                return

            # ── 7. Verify CLI exists ──────────────────────────────────────
            cli_path = find_integral_cli()
            if cli_path:
                self._log(f"integralrad installed successfully at: {cli_path}", data=CH)
                self._emit(AppEvent(type="ui_state", message="install_complete"))
                self._emit(AppEvent(type="integral_status", message="install_complete"))
            else:
                self._log(
                    "Install finished but integral-radiomics CLI not found in PATH",
                    level="ERROR",
                    data=CH,
                )
                self._emit(AppEvent(type="ui_state", message="install_failed"))
                self._emit(AppEvent(type="integral_status", message="install_failed"))

        except Exception as exc:
            # Safety net — if anything unexpected throws, unblock the splash.
            self._log(f"Unexpected error during R setup: {exc}", level="ERROR", data=CH)
            self._emit(AppEvent(type="ui_state", message="install_failed"))
            self._emit(AppEvent(type="integral_status", message="install_failed"))
