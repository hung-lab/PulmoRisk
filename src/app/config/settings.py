from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PRIMARY_LIGHT = "#1e7f8c"
PRIMARY_DARK = "#2b3d4f"
ACCENT_LIGHT = "#cc0033"
ACCENT_DARK = "#ffb38a"

BORDER_LIGHT = "#20343a"
BORDER_DARK = "#c8d2e0"

TEXT_COLOUR = ("#20343a", "#ffffff")
DISABLED_TEXT_COLOUR = ("#8d9aab", "#8d9aab")

INFO_COLOUR = ("#3a7bd5", "#bfeaf2")
SUCCESS_COLOUR = (PRIMARY_LIGHT, "#9BE7B1")
BORDER_COLOUR = (BORDER_LIGHT, BORDER_DARK)
ERROR_COLOUR = (ACCENT_LIGHT, ACCENT_DARK)
WARNING_COLOUR = ("#FF5a5f", ACCENT_DARK)
WARNING_COLOUR_HOVER = (ACCENT_DARK, "#FF5a5f")
ERROR_COLOUR_HOVER = (ACCENT_DARK, ACCENT_LIGHT)

# Colour per log level — mirrors LogPanel's palette
LEVEL_COLOURS: dict[str, tuple[str, str]] = {
    "INFO": INFO_COLOUR,
    "SUCCESS": SUCCESS_COLOUR,
    "WARNING": WARNING_COLOUR,
    "ERROR": ERROR_COLOUR,
}
LEVEL_PREFIX: dict[str, str] = {
    "INFO": ("i", "info"),
    "SUCCESS": ("✓", "success"),
    "WARNING": ("⚠", "warning"),
    "ERROR": ("✗", "error"),
}
