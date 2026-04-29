import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if getattr(sys, "frozen", False):
    BASE_PATH = Path(sys._MEIPASS)
else:
    BASE_PATH = PROJECT_ROOT

__version__ = "1.0.0"
__build_date__ = "2026-04-28"
__author__ = "Wisam Al Abed"

# Colour per log level — mirrors LogPanel's palette
LEVEL_COLOURS: dict[str, str] = {
    "INFO": "#569fd3",
    "SUCCESS": "#bed600",
    "WARNING": "#ec7a08",
    "ERROR": "#cc0033",
}
LEVEL_PREFIX: dict[str, str] = {
    "INFO": ("i", "info"),
    "SUCCESS": ("✓", "success"),
    "WARNING": ("⚠", "warning"),
    "ERROR": ("✗", "error"),
}

PRIMARY_BLUE = "#00467f"
SECONDARY_BLUE = "#569fd3"
RED_ACCENT = "#cc0033"
ORANGE_ACCENT = "#ec7a08"

_ERROR_COLOUR = (RED_ACCENT, ORANGE_ACCENT)
