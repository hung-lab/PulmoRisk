import os
import shutil
import subprocess
import sys
import tkinter.font as tkfont
import webbrowser
from pathlib import Path

import customtkinter as ctk

from app.config.settings import PROJECT_ROOT


class InvalidFileError(Exception):
    def __init__(self, field_name: str, reason: str):
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name}: {reason}")


def get_mono_font(size=14):
    available = set(tkfont.families())

    candidates = [
        "Cascadia Code",
        "SF Mono",
        "Menlo",
        "Consolas",
        "DejaVu Sans Mono",
        "Liberation Mono",
        "Courier New",
    ]

    for font in candidates:
        if font in available:
            return ctk.CTkFont(family=font, size=size)

    return ctk.CTkFont(family="Courier New", size=size)


def resolve_color(light: str, dark: str) -> str:
    return dark if ctk.get_appearance_mode() == "Dark" else light


def open_url(url: str) -> None:
    if sys.platform.startswith("linux"):
        try:
            subprocess.Popen(["xdg-open", url])
        except FileNotFoundError:
            webbrowser.open(url)  # fallback if xdg-open not available
    else:
        webbrowser.open(url)


def bounded_float(label, min_val, max_val):
    def check(val):
        f = float(val)
        if f < min_val or f > max_val:
            raise ValueError(f"{label} must be between {min_val} and {max_val}")
        return f

    return check


def center_window(
    win,
    fraction: float = 1.0,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """Resize *win* and centre it on the screen.

    Size is resolved in this order:
      1. Explicit *width* / *height* if both are provided.
      2. *fraction* of the screen when fraction < 1.0.
      3. The window's own requested size (winfo_req*) as the default.

    Args:
        win:      Any Tk/CTk window (CTk, CTkToplevel, Toplevel ...).
        fraction: Proportion of the screen to occupy (0 < fraction <= 1).
        width:    Explicit pixel width (overrides fraction).
        height:   Explicit pixel height (overrides fraction).
    """
    win.update_idletasks()

    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()

    if width is not None and height is not None:
        w, h = width, height
    elif fraction < 1.0:
        w = int(sw * fraction)
        h = int(sh * fraction)
    else:
        # winfo_reqwidth/height returns the size Tk calculated from widget
        # layout -- reliable even before the window has been displayed.
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()

    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


def resource_path(*parts):
    base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else PROJECT_ROOT
    return base.joinpath(*parts)


def validate_ct_path(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "Path does not exist"
    if not path.is_dir():
        return False, "Not a directory"
    if not any(path.iterdir()):
        return False, "Directory is empty"
    return True, ""


def validate_file_path(path: Path, field_name: str) -> None:
    if not path.exists():
        raise InvalidFileError(field_name, "path does not exist")
    if not path.is_file():
        raise InvalidFileError(field_name, "not a file")
    if path.suffix.lower() != ".nrrd":
        raise InvalidFileError(field_name, "not a nrrd file")


def find_rscript() -> str | None:
    """Locate the Rscript executable.

    Search order:
      1. PATH via shutil.which — covers any user-managed install (conda,
         rig, nix, manually built R, etc.) and is the fastest check.
      2. Standard system locations not always on PATH, in order of how
         common the install method is on each platform.

    Returns the first path that exists and successfully runs
    ``Rscript --version``, or None if R is not found.
    """
    # 1. Honour PATH first — shutil.which already verifies existence
    #    and executability, so no extra checks needed for this case.
    path_result = shutil.which("Rscript")
    if path_result:
        return path_result

    # 2. Platform-specific fallback locations
    #    (only reached when Rscript is NOT on PATH)
    candidates: list[Path] = []

    if sys.platform == "darwin":
        candidates = [
            # Apple Silicon Homebrew
            Path("/opt/homebrew/bin/Rscript"),
            # Intel Homebrew
            Path("/usr/local/bin/Rscript"),
            # CRAN .pkg installer — default location
            Path("/Library/Frameworks/R.framework/Resources/bin/Rscript"),
            # rig-managed installs (rig puts the active version here)
            Path(
                "/Library/Frameworks/R.framework/Versions/Current/Resources/bin/Rscript"
            ),
        ]
    elif sys.platform.startswith("linux"):
        candidates = [
            # apt install r-base (Ubuntu/Debian) — most common
            Path("/usr/bin/Rscript"),
            # Some distros install under /usr/local
            Path("/usr/local/bin/Rscript"),
            # rig on Linux
            Path(Path.home() / ".local/share/rig/R/current/bin/Rscript"),
        ]
    elif sys.platform == "win32":
        # On Windows, R is typically installed under Program Files.
        # Walk R-x.y.z sub-directories newest-first so we pick the latest.
        r_root = Path("C:/Program Files/R")
        if r_root.exists():
            for version_dir in sorted(r_root.iterdir(), reverse=True):
                rscript = version_dir / "bin" / "Rscript.exe"
                if rscript.exists():
                    candidates.append(rscript)
                    break  # take only the newest

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            result = subprocess.run(
                [str(candidate), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return str(candidate)
        except Exception:
            continue

    return None


def find_integral_cli() -> str | None:
    """Locate the integral-radiomics CLI binary.

    Checks known install locations in order of likelihood, without any
    recursive filesystem scan, to keep startup time fast.

    The Rapp package (which integralrad uses to install the CLI) places
    the binary in platform-specific locations documented below.

    Returns the path string if found and executable, else None.
    """
    cli_name = "integral-radiomics"
    if sys.platform == "win32":
        cli_name = "integral-radiomics.exe"

    # 1. PATH — covers any install the user has already configured.
    path_result = shutil.which(cli_name)
    if path_result:
        return path_result

    # 2. Known install locations for integralrad::install_integralrad_cli()
    #    (via the Rapp package), checked in order of likelihood.
    candidates: list[Path] = [
        # Linux / macOS — Rapp default user bin
        Path.home() / ".local" / "bin" / cli_name,
        # App-managed install location (used by check_and_install_integral)
        Path.home() / ".pulmorisk" / "bin" / cli_name,
        # macOS — Rapp installs here when ~/.local/bin is not used
        Path.home()
        / "Library"
        / "Application Support"
        / "org.R-project.R"
        / "R"
        / "Rapp"
        / "bin"
        / cli_name,
        # Rapp can also install into the R user data dir on Linux
        Path.home() / ".local" / "share" / "R" / "Rapp" / "bin" / cli_name,
    ]

    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)

    return None


def format_percent(value: float, decimals: int = 3) -> str:
    percent = f"{value * 100:.{decimals}f}"
    return f"{percent.rstrip('0').rstrip('.')}%"
