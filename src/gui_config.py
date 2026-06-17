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

SERIES_PANEL_WIDTH = 185
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

APP_STYLE = """
QMainWindow {
    background: #fdfefe;
}
QWidget#AppRoot {
    background: #fdfefe;
}
QWidget#AppRoot[pageKind="daily"] {
    background: #fdfefe;
}
QWidget#AppRoot[pageKind="test"] {
    background: #fdfefe;
}
QWidget#AppRoot[pageKind="setting"] {
    background: #fdfefe;
}
QWidget {
    color: #20242a;
    font-size: 13px;
}
QTabWidget::pane,
QTabWidget#MainTabs::pane {
    border: none;
    background: #fdfefe;
    top: 0px;
}
QTabWidget#MainTabs {
    background: #fdfefe;
}
QTabWidget#MainTabs[pageKind="daily"],
QTabWidget#MainTabs[pageKind="daily"]::pane {
    background: #fdfefe;
}
QTabWidget#MainTabs[pageKind="test"],
QTabWidget#MainTabs[pageKind="test"]::pane {
    background: #fdfefe;
}
QTabWidget#MainTabs[pageKind="setting"],
QTabWidget#MainTabs[pageKind="setting"]::pane {
    background: #fdfefe;
}
QTabWidget#MainTabs::tab-bar {
    background: transparent;
    left: 8px;
}
QTabWidget#MainTabs QTabBar,
QTabBar {
    background: transparent;
    margin-left: 8px;
}
QTabBar::tab {
    background: #fbfcfe;
    border: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 16px;
    margin-right: 2px;
    margin-bottom: 0px;
}
QTabBar::tab:first {
    background: #dcefe0;
}
QTabBar::tab:last {
    background: #c9e1ff;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0f172a;
}
QTabBar::tab:first:selected {
    background: #d2e9d7;
}
QTabWidget#MainTabs[analysisMode="test"] QTabBar::tab:first:selected {
    background: #ffe5c7;
}
QTabBar::tab:last:selected {
    background: #bdd9f8;
}
QGroupBox, QFrame {
    border: none;
    border-radius: 6px;
    background: #ffffff;
}
QFrame#SettingsSection {
    border: none;
    border-radius: 6px;
    background: #ffffff;
}
QFrame#AnalysisTablePanel,
QFrame#SeriesPanel,
QFrame#DialogButtonPanel {
    border: none;
    border-radius: 6px;
    background: #ffffff;
}
QFrame#SettingsSection QLabel {
    border: none;
    background: transparent;
}
QLabel#PlainLabel {
    border: none;
    background: transparent;
}
QWidget#AnalysePage,
QTabWidget#MainTabs QWidget#AnalysePage {
    background: #d2e9d7;
    border-radius: 6px;
}
QWidget#AnalysePage[mode="daily"] QFrame#SettingsSection,
QWidget#AnalysePage[mode="daily"] QFrame#AnalysisTablePanel,
QWidget#AnalysePage[mode="daily"] QFrame#SeriesPanel,
QWidget#AnalysePage[mode="daily"] QGroupBox {
    background: #f8fdf9;
}
QWidget#AnalysePage[mode="test"],
QTabWidget#MainTabs QWidget#AnalysePage[mode="test"] {
    background: #ffe5c7;
    border-radius: 6px;
}
QWidget#AnalysePage[mode="test"] QFrame#SettingsSection,
QWidget#AnalysePage[mode="test"] QFrame#AnalysisTablePanel,
QWidget#AnalysePage[mode="test"] QFrame#SeriesPanel,
QWidget#AnalysePage[mode="test"] QGroupBox {
    background: #fff9f2;
}
QWidget#SettingPage,
QTabWidget#MainTabs QWidget#SettingPage {
    background: #bdd9f8;
    border-radius: 6px;
}
QWidget#SettingPage QGroupBox,
QWidget#SettingPage QWidget#SettingsPanel {
    background: #edf6ff;
}
QGroupBox {
    margin-top: 18px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 2px;
    padding: 0 4px;
    color: #526071;
}
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
    border: 1px solid #cbd3df;
    border-radius: 6px;
    padding: 5px 8px;
    background: #ffffff;
    selection-background-color: #2563eb;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    border: 1px solid #4f83d1;
    background: #ffffff;
}
QTextEdit#LogOutput {
    padding: 2px 3px;
}
QSpinBox, QDoubleSpinBox {
    padding-right: 28px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    border: none;
    border-top-right-radius: 6px;
    background: transparent;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    border: none;
    border-bottom-right-radius: 6px;
    background: transparent;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #edf4ff;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: url(src/assets/spin-up.svg);
    width: 8px;
    height: 5px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: url(src/assets/spin-down.svg);
    width: 8px;
    height: 5px;
}
QComboBox {
    padding-right: 20px;
}
QComboBox::drop-down {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border: none;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background: transparent;
}
QComboBox::drop-down:hover {
    background: #edf4ff;
}
QComboBox::down-arrow {
    image: url(src/assets/spin-down.svg);
    width: 8px;
    height: 5px;
    border: none;
}
QComboBox QAbstractItemView {
    border: 1px solid #cbd3df;
    border-radius: 6px;
    background: #ffffff;
    selection-background-color: #dbeafe;
    selection-color: #111827;
    outline: 0;
    padding: 3px;
}
QPushButton {
    border: 1px solid #c9d8e8;
    border-radius: 7px;
    padding: 7px 13px;
    background: #edf4fb;
    color: #172033;
    font-weight: 500;
}
QPushButton:hover {
    background: #e3eef9;
    border-color: #a9bfd7;
}
QPushButton:pressed {
    background: #d6e5f3;
}
QPushButton:disabled {
    color: #9ca9b8;
    background: #edf2f6;
    border-color: #d7e0ea;
}
QPushButton#primaryButton {
    background: #cfe0f4;
    border-color: #a9bfd7;
    color: #17324f;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background: #bfd4ed;
    border-color: #8faccb;
}
QPushButton#primaryButton:pressed {
    background: #aec8e5;
}
QPushButton#primaryButton:disabled {
    background: #e0e9f3;
    border-color: #c8d5e3;
    color: #8fa0b2;
}
QPushButton#seriesSaveButton {
    background: #e5f3e9;
    border-color: #bfdcc8;
    color: #22543a;
}
QPushButton#seriesSaveButton:hover {
    background: #d8eddf;
    border-color: #9bc9aa;
}
QPushButton#seriesSaveButton:pressed {
    background: #c9e4d2;
}
QPushButton#seriesSaveButton:disabled {
    background: #dff0e5;
    border-color: #b5d2c0;
    color: #7d9d88;
}
QPushButton#seriesDeleteButton {
    background: #fdebdc;
    border-color: #efc6a7;
    color: #7a3f16;
}
QPushButton#seriesDeleteButton:hover {
    background: #fbe0ca;
    border-color: #e4ad82;
}
QPushButton#seriesDeleteButton:pressed {
    background: #f5cfb0;
}
QPushButton#seriesDeleteButton:disabled {
    background: #f7deca;
    border-color: #e6bc9e;
    color: #a9785b;
}
QTableWidget, QListWidget {
    background: #ffffff;
    alternate-background-color: #f8fafc;
    border: 1px solid #d8dde5;
    gridline-color: #e7ebf0;
    selection-background-color: #dbeafe;
    selection-color: #111827;
}
QHeaderView::section {
    background: #eef2f7;
    color: #334155;
    border: none;
    border-right: 1px solid #d8dde5;
    border-bottom: 1px solid #d8dde5;
    padding: 5px 6px;
    font-weight: 600;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #f1f4f8;
    border: none;
    width: 12px;
    height: 12px;
}
QScrollBar::handle {
    background: #c3ccda;
    border-radius: 6px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
"""

PRIMARY_BUTTON_STYLE = """
QPushButton {
    background: #cfe0f4;
    border: 1px solid #a9bfd7;
    border-radius: 7px;
    color: #17324f;
    font-weight: 600;
    padding: 7px 13px;
}
QPushButton:hover {
    background: #bfd4ed;
    border-color: #8faccb;
}
QPushButton:pressed {
    background: #aec8e5;
}
QPushButton:disabled {
    background: #e0e9f3;
    border-color: #c8d5e3;
    color: #8fa0b2;
}
"""

ANALYSE_DAILY_STYLE = """
QWidget#AnalysePage,
QTabWidget#MainTabs QWidget#AnalysePage {
    background: #d2e9d7;
    border-radius: 6px;
}
QFrame#SettingsSection,
QFrame#AnalysisTablePanel,
QFrame#SeriesPanel,
QFrame#DialogButtonPanel,
QGroupBox {
    background: #f4fbf6;
    border: none;
}
QFrame#SettingsSection,
QFrame#AnalysisTablePanel,
QFrame#SeriesPanel,
QFrame#DialogButtonPanel {
    margin-top: 0;
    padding-top: 0;
}
QGroupBox {
    margin-top: 18px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 2px;
    padding: 0 4px;
    color: #526071;
}
QTableWidget, QListWidget, QTextEdit {
    background: #ffffff;
}
"""

ANALYSE_TEST_STYLE = """
QWidget#AnalysePage,
QTabWidget#MainTabs QWidget#AnalysePage {
    background: #ffe5c7;
    border-radius: 6px;
}
QFrame#SettingsSection,
QFrame#AnalysisTablePanel,
QFrame#SeriesPanel,
QFrame#DialogButtonPanel,
QGroupBox {
    background: #fff5e9;
    border: none;
}
QFrame#SettingsSection,
QFrame#AnalysisTablePanel,
QFrame#SeriesPanel,
QFrame#DialogButtonPanel {
    margin-top: 0;
    padding-top: 0;
}
QGroupBox {
    margin-top: 18px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 2px;
    padding: 0 4px;
    color: #526071;
}
QTableWidget, QListWidget, QTextEdit {
    background: #ffffff;
}
"""

SETTING_PAGE_STYLE = """
QWidget#SettingPage,
QTabWidget#MainTabs QWidget#SettingPage {
    background: #bdd9f8;
    border-radius: 6px;
}
QWidget#SettingsPanel {
    background: transparent;
    border: none;
    margin-top: 0;
    padding-top: 0;
}
QGroupBox {
    background: #f5faff;
    border: none;
    margin-top: 18px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 2px;
    padding: 0 4px;
    color: #526071;
}
QTableWidget, QListWidget, QTextEdit {
    background: #ffffff;
}
"""
