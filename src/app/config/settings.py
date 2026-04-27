import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if getattr(sys, "frozen", False):
    BASE_PATH = Path(sys._MEIPASS)
else:
    BASE_PATH = PROJECT_ROOT

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
