from __future__ import annotations

from pathlib import Path


DEFAULT_DB_PATH = Path("data/wanalyzer.sqlite")
DEFAULT_DEBUG_OUTPUT = Path("log/core_debug")
INPUT_PATH_SETTING = "last_input_path"
OUTPUT_PATH_SETTING = "last_output_path"
DEFAULT_PRESET_SETTING = "default_preset_name"
OK_THRESHOLD_SETTING = "ok_abs_threshold_mm"
LEGACY_OK_THRESHOLD_SETTING = "ok_threshold_mm"
DEFAULT_OK_THRESHOLD_MM = 1.0

RESULT_TABLE_HEADERS = [
    "Order",
    "Image",
    "Setup",
    "Status",
    "dx mm",
    "dy mm",
    "Distance mm",
    "Gantry",
    "Collimator",
    "Couch",
    "dx+",
    "dx-",
    "dy+",
    "dy-",
    "Field px",
    "Target px",
    "Pixel mm",
    "Beam th",
    "Ball sens",
]

SERIES_PANEL_WIDTH = 190
MODE_WIDGET_SIZE = (160, 82)
MODE_LABEL_STYLE = (
    "QLabel {"
    " border: none;"
    " background: #f0a63a;"
    " color: #222;"
    " font-weight: bold;"
    " padding: 2px 6px;"
    "}"
)
MODE_TEMP_LABEL_STYLE = MODE_LABEL_STYLE.replace("#f0a63a", "#73b77b")
