from __future__ import annotations

import csv
import signal
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import cv2
from PySide6.QtCore import QDate, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from setups import AnalysisSetup, SetupPreset
from core import (
    Analysis,
    AnalysisParameters,
    analyze_image,
    list_images,
    save_debug_output,
)
from database import (
    AnalysisMetadata,
    connect_database,
    create_session,
    get_setup,
    get_setup_preset,
    get_default_machine_name,
    get_setting,
    get_or_create_machine,
    init_db,
    deactivate_setup,
    list_setups,
    list_setup_presets,
    list_setup_steps,
    list_machines,
    save_analysis_results,
    set_default_machine_name,
    set_setting,
    update_setup_by_id,
    upsert_setup,
    upsert_setup_preset,
)
from report import (
    ReportPoint,
    focused_overlay_pixmap,
    load_report_data,
    render_grouped_report_pages,
    write_grouped_pdf,
)
from workflow import AnalysisPlanItem, analyze_plan, build_analysis_plan_from_preset


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


@dataclass
class AnalysisSeries:
    name: str
    plan: list[AnalysisPlanItem]
    analyses: list[Analysis]
    inspection_type: str
    machine_name: str | None
    saved: bool = False
    started_at: str = ""
    source: str = "current"
    session_id: int | None = None
    points: list[ReportPoint] = field(default_factory=list)
    output_active: bool = True


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WanaLyzer")
        self.resize(1070, 700)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self.tabs = QTabWidget()
        self.daily_tab = DailyTab()
        self.manage_tab = ManageTab(self.refresh_analysis_tabs)
        self.tabs.addTab(self.daily_tab, "Analyze")
        self.tabs.addTab(self.manage_tab, "Setting")
        layout.addWidget(self.tabs, stretch=1)

    def refresh_analysis_tabs(self) -> None:
        self.daily_tab.refresh_database_options()


class AnalysisTab(QWidget):
    def __init__(
        self,
        default_inspection: str,
        default_image_path: str,
        show_inspection: bool = True,
    ) -> None:
        super().__init__()
        self.current_series: AnalysisSeries | None = None
        self.loaded_plan: list[AnalysisPlanItem] = []
        self.loading_options = False
        self.default_inspection = default_inspection
        self.show_inspection = show_inspection
        self.current_parameters = AnalysisParameters()
        self.updating_plan_table = False
        self.suppress_plan_load = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(2)
        self.settings_group = self.build_settings_group(default_image_path)
        layout.addWidget(self.settings_group)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.build_table_group())
        splitter.addWidget(self.build_preview_group())
        splitter.setSizes([560, 220])
        layout.addWidget(splitter, stretch=1)

        self.refresh_database_options()
        self.suppress_plan_load = False

    def build_settings_group(self, default_image_path: str) -> QGroupBox:
        group = QGroupBox()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.add_settings_leading_widgets(top_row)

        self.path_group = QGroupBox()
        path_row = QVBoxLayout(self.path_group)
        path_row.setContentsMargins(6, 4, 6, 4)
        path_row.setSpacing(4)
        self.image_path = QLineEdit(load_app_setting(INPUT_PATH_SETTING, default_image_path))
        self.image_path.setMinimumWidth(145)
        self.image_path.editingFinished.connect(self.input_path_edited)
        image_button = QPushButton("Browse")
        image_button.clicked.connect(self.browse_images)
        image_group = QHBoxLayout()
        image_group.setSpacing(4)
        input_label = QLabel("Input")
        input_label.setFixedWidth(44)
        input_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        image_group.addWidget(input_label)
        image_group.addWidget(self.image_path, stretch=1)
        image_group.addWidget(image_button)
        path_row.addLayout(image_group)

        self.output_path = QLineEdit(load_app_setting(OUTPUT_PATH_SETTING, str(DEFAULT_DEBUG_OUTPUT)))
        self.output_path.setMinimumWidth(145)
        self.output_path.editingFinished.connect(self.output_path_edited)
        output_button = QPushButton("Browse")
        output_button.clicked.connect(self.browse_output)
        output_group = QHBoxLayout()
        output_group.setSpacing(4)
        output_label = QLabel("Output")
        output_label.setFixedWidth(44)
        output_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        output_group.addWidget(output_label)
        output_group.addWidget(self.output_path, stretch=1)
        output_group.addWidget(output_button)
        path_row.addLayout(output_group)
        top_row.addWidget(self.path_group, stretch=1)

        self.setups_group = QGroupBox()
        option_row = QVBoxLayout(self.setups_group)
        option_row.setContentsMargins(6, 4, 6, 4)
        option_row.setSpacing(4)
        self.machine_combo = QComboBox()
        self.machine_combo.setEditable(True)
        self.machine_combo.setMinimumWidth(110)
        self.machine_combo.setMaximumWidth(150)
        option_row.addWidget(compact_field("Machine", self.machine_combo))

        self.inspection_type = QComboBox()
        self.inspection_type.setEditable(True)
        self.inspection_type.addItems(["daily", "temporary", "post_adjustment"])
        self.inspection_type.setCurrentText(self.default_inspection)
        self.inspection_type.setMinimumWidth(110)
        self.inspection_type.setMaximumWidth(150)
        if self.show_inspection:
            option_row.addWidget(compact_field("Inspection", self.inspection_type))

        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self.load_plan_preview)
        self.preset_combo.setMinimumWidth(110)
        self.preset_combo.setMaximumWidth(150)
        option_row.addWidget(compact_field("Preset", self.preset_combo))
        top_row.addWidget(self.setups_group)

        self.actions_group = QGroupBox()
        actions_row = QGridLayout(self.actions_group)
        actions_row.setContentsMargins(6, 4, 6, 4)
        actions_row.setHorizontalSpacing(6)
        actions_row.setVerticalSpacing(6)
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.clicked.connect(self.analyze_clicked)
        self.export_button = QPushButton("Review & Output")
        self.export_button.clicked.connect(self.export_pdf_clicked)
        self.output_count = QSpinBox()
        self.output_count.setRange(1, 50)
        self.output_count.setValue(15)
        self.output_count.setMinimumWidth(64)
        self.output_count_widget = compact_field("Recent", self.output_count)
        self.output_count_widget.setVisible(False)
        action_button_width = max(
            96,
            self.analyze_button.sizeHint().width(),
            self.export_button.sizeHint().width(),
        )
        for button in [self.analyze_button, self.export_button]:
            button.setMinimumSize(action_button_width, 32)
        actions_row.addWidget(self.analyze_button, 0, 0, 1, 2)
        actions_row.addWidget(self.output_count_widget, 1, 1)
        actions_row.addWidget(self.export_button, 2, 0, 1, 2)
        top_row.addWidget(self.actions_group)
        layout.addLayout(top_row)

        self.pixel_size_value = value_label()
        self.beam_size_value = value_label()
        self.target_size_value = value_label()
        self.beam_threshold_value = value_label()
        self.ball_sensitivity_value = value_label()
        self.update_tuning_parameter_labels()
        self.update_save_button_state()

        return group

    def add_settings_leading_widgets(self, layout: QHBoxLayout) -> None:
        return

    def set_analysis_controls_enabled(self, enabled: bool) -> None:
        self.settings_group.setEnabled(enabled)
        self.table.setEnabled(enabled)
        self.preview.setEnabled(enabled)
        self.previous_preview_button.setEnabled(enabled)
        self.next_preview_button.setEnabled(enabled)
        self.log_output.setEnabled(enabled)

    def build_table_group(self) -> QWidget:
        return self.build_series_table_group(show_series_list=False)

    def build_series_table_group(self, show_series_list: bool) -> QWidget:
        group = QWidget()
        layout = QHBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.series_panel = QFrame()
        self.series_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.series_panel.setFrameShadow(QFrame.Shadow.Plain)
        self.series_panel.setFixedWidth(SERIES_PANEL_WIDTH if show_series_list else 0)
        series_layout = QVBoxLayout(self.series_panel)
        series_layout.setContentsMargins(4, 4, 4, 4)
        series_layout.setSpacing(4)
        self.series_query_mode = QComboBox()
        self.series_query_mode.addItem("Recent count", "count")
        self.series_query_mode.addItem("Date range", "date")
        self.series_query_mode.currentIndexChanged.connect(self.update_series_query_mode)
        self.series_from_date = QDateEdit()
        self.series_from_date.setCalendarPopup(True)
        self.series_from_date.setDate(QDate.currentDate().addDays(-30))
        self.series_to_date = QDateEdit()
        self.series_to_date.setCalendarPopup(True)
        self.series_to_date.setDate(QDate.currentDate())
        self.series_limit = QSpinBox()
        self.series_limit.setRange(1, 10000)
        self.series_limit.setValue(30)
        self.series_query_button = QPushButton("Query")
        self.series_query_button.clicked.connect(self.query_series_list)
        for widget in [self.series_query_mode, self.series_from_date, self.series_to_date, self.series_limit, self.series_query_button]:
            widget.setVisible(show_series_list)

        self.series_query_toggle = QPushButton("Query Options")
        self.series_query_toggle.setCheckable(True)
        self.series_query_toggle.setVisible(show_series_list)
        self.series_query_toggle.toggled.connect(self.toggle_series_query_options)
        series_layout.addWidget(self.series_query_toggle)

        self.series_query_frame = QFrame()
        self.series_query_frame.setVisible(False)
        query_layout = QVBoxLayout(self.series_query_frame)
        query_layout.setContentsMargins(6, 5, 6, 5)
        query_layout.setSpacing(4)
        query_layout.addWidget(compact_field("Query", self.series_query_mode))
        self.series_count_query_widget = compact_field("Count", self.series_limit)
        query_layout.addWidget(self.series_count_query_widget)
        self.series_date_query_widget = QWidget()
        date_query_layout = QVBoxLayout(self.series_date_query_widget)
        date_query_layout.setContentsMargins(0, 0, 0, 0)
        date_query_layout.setSpacing(4)
        date_query_layout.addWidget(compact_field("From", self.series_from_date))
        date_query_layout.addWidget(compact_field("To", self.series_to_date))
        query_layout.addWidget(self.series_date_query_widget)
        query_layout.addWidget(self.series_query_button)
        series_layout.addWidget(self.series_query_frame)
        self.series_count_query_widget.setVisible(show_series_list)
        self.series_date_query_widget.setVisible(False)
        self.series_list = QListWidget()
        self.series_list.setVisible(show_series_list)
        series_layout.addWidget(self.series_list, stretch=1)
        self.save_series_button = QPushButton("Save")
        self.save_series_button.setVisible(show_series_list)
        self.save_series_button.setMinimumHeight(56)
        self.save_series_button.clicked.connect(self.save_selected_series)
        series_layout.addWidget(self.save_series_button)
        self.active_toggle_button = QPushButton("Active / Inactive")
        self.active_toggle_button.setVisible(show_series_list)
        self.active_toggle_button.clicked.connect(self.toggle_selected_series_active)
        series_layout.addWidget(self.active_toggle_button)
        self.remove_series_button = QPushButton("Delete")
        self.remove_series_button.setVisible(show_series_list)
        self.remove_series_button.clicked.connect(self.remove_selected_series)
        series_layout.addWidget(self.remove_series_button)
        layout.addWidget(self.series_panel)

        table_group = QWidget()
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, len(RESULT_TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(RESULT_TABLE_HEADERS)
        configure_result_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.update_preview_from_selection)
        table_layout.addWidget(self.table)
        table_button_row = QHBoxLayout()
        table_button_row.setContentsMargins(0, 4, 0, 0)
        table_button_row.addStretch()
        self.delete_row_button = QPushButton("Delete Row")
        self.delete_row_button.clicked.connect(self.delete_selected_simple_row)
        self.delete_row_button.setVisible(False)
        self.csv_button = QPushButton("Export CSV")
        self.csv_button.clicked.connect(self.export_current_table_csv)
        table_button_row.addWidget(self.delete_row_button)
        table_button_row.addWidget(self.csv_button)
        table_layout.addLayout(table_button_row)
        layout.addWidget(table_group, stretch=1)
        return group

    def build_preview_group(self) -> QGroupBox:
        group = QGroupBox("Analyzed Images")
        layout = QVBoxLayout(group)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(190, 190)
        self.preview.setStyleSheet("background: #111; color: #ddd;")
        self.preview.setText("解析後、行を選択してください")

        navigation = QHBoxLayout()
        self.previous_preview_button = QPushButton("Previous")
        self.previous_preview_button.clicked.connect(self.show_previous_preview)
        self.next_preview_button = QPushButton("Next")
        self.next_preview_button.clicked.connect(self.show_next_preview)
        navigation.addWidget(self.previous_preview_button)
        navigation.addWidget(self.next_preview_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(110)
        layout.addWidget(self.preview, stretch=2)
        layout.addLayout(navigation)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_output, stretch=1)
        return group

    def remove_selected_series(self) -> None:
        return

    def save_selected_series(self) -> bool:
        return False

    def delete_selected_simple_row(self) -> None:
        return

    def refresh_database_options(self) -> None:
        try:
            connection = connect_database(DEFAULT_DB_PATH)
            try:
                init_db(connection)
                presets = list_setup_presets(connection)
                machines = list_machines(connection)
                default_machine = get_default_machine_name(connection)
                default_preset = get_setting(connection, DEFAULT_PRESET_SETTING) or ""
            finally:
                connection.close()
        except Exception as exc:
            show_error(self, "データベースエラー", exc)
            return

        self.loading_options = True
        try:
            current_preset = self.preset_combo.currentText()
            self.preset_combo.clear()
            self.preset_combo.addItem("")
            for preset in presets:
                self.preset_combo.addItem(preset["name"])
            if current_preset:
                self.preset_combo.setCurrentText(current_preset)
            elif default_preset:
                self.preset_combo.setCurrentText(default_preset)

            current_machine = self.machine_combo.currentText()
            self.machine_combo.clear()
            for machine in machines:
                self.machine_combo.addItem(machine["name"])
            self.machine_combo.setCurrentText(current_machine or default_machine)
        finally:
            self.loading_options = False

        if not self.suppress_plan_load:
            self.load_plan_preview()
        self.update_save_button_state()

    def browse_images(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Images", self.image_path.text())
        if path:
            self.image_path.setText(path)
            save_app_setting(INPUT_PATH_SETTING, path)
            self.load_plan_preview()
            self.update_save_button_state()

    def browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Debug Output", self.output_path.text())
        if path:
            self.output_path.setText(path)
            save_app_setting(OUTPUT_PATH_SETTING, path)

    def input_path_edited(self) -> None:
        save_app_setting(INPUT_PATH_SETTING, self.image_path.text())
        self.load_plan_preview()
        self.update_save_button_state()

    def output_path_edited(self) -> None:
        save_app_setting(OUTPUT_PATH_SETTING, self.output_path.text())

    def export_current_table_csv(self) -> None:
        if self.table.rowCount() == 0:
            show_error(self, "CSV出力エラー", ValueError("出力する行がありません。"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "CSVを出力",
            str(Path("log") / "analysis_results.csv"),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(RESULT_TABLE_HEADERS)
            for row in range(self.table.rowCount()):
                writer.writerow([
                    table_text(self.table, row, column)
                    for column in range(self.table.columnCount())
                ])
        self.log(f"CSVを出力しました: {path}")

    def analyze_clicked(self) -> None:
        try:
            series = self.create_series()
        except Exception as exc:
            show_error(self, "解析エラー", exc)
            return
        self.set_current_series(series)
        self.after_analysis(series)
        self.update_save_button_state()

    def create_series(self) -> AnalysisSeries:
        plan = self.loaded_plan or self.build_plan()
        if any(item.setup_label is None for item in plan):
            raise ValueError("setup未選択の画像があります。解析前にsetupを選択してください。")

        analyses = self.analyze_plan_with_progress(plan)
        started_at = datetime.now().isoformat(timespec="seconds")
        return AnalysisSeries(
            name=series_display_name(started_at),
            plan=plan,
            analyses=analyses,
            inspection_type=self.inspection_type.currentText(),
            machine_name=self.machine_name(),
            started_at=started_at,
        )

    def analyze_plan_with_progress(self, plan: list[AnalysisPlanItem]) -> list[Analysis]:
        progress = QProgressDialog("解析を実行しています...", "", 0, 0, self)
        progress.setWindowTitle("解析中")
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()
        try:
            analyses = analyze_plan(plan, self.analysis_parameters())
            save_debug_output(analyses, self.output_path_value(), write_images=True)
            return analyses
        finally:
            progress.close()
            QApplication.processEvents()

    def analysis_parameters(self) -> AnalysisParameters:
        return self.current_parameters

    def set_analysis_parameters(self, parameters: AnalysisParameters) -> None:
        self.current_parameters = parameters
        self.update_tuning_parameter_labels()

    def update_tuning_parameter_labels(self) -> None:
        parameters = self.current_parameters
        self.pixel_size_value.setText(f"{parameters.pixel_size_mm:.4f}")
        self.beam_size_value.setText(optional_parameter_text(parameters.beam_size_px))
        self.target_size_value.setText(optional_parameter_text(parameters.target_size_px))
        self.beam_threshold_value.setText(
            "otsu" if parameters.beam_threshold == 0 else str(parameters.beam_threshold)
        )
        self.ball_sensitivity_value.setText(str(parameters.ball_sensitivity))

    def manual_tuning_clicked(self) -> None:
        plan = self.current_series.plan if self.current_series is not None else self.loaded_plan
        row = self.selected_row() or 0
        if not plan or row < 0 or row >= len(plan):
            show_error(self, "調整エラー", ValueError("画像が選択されていません。"))
            return
        dialog = ManualTuningDialog(plan, row, self.analysis_parameters(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.set_analysis_parameters(dialog.parameters())
            self.log("Manual tuningの解析パラメータを更新しました。")

    def build_plan(self) -> list[AnalysisPlanItem]:
        if not self.preset_combo.currentText():
            return self.build_unassigned_plan()
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            return build_analysis_plan_from_preset(
                self.image_path_value(),
                connection,
                self.preset_combo.currentText(),
            )
        finally:
            connection.close()

    def build_unassigned_plan(self) -> list[AnalysisPlanItem]:
        return [
            AnalysisPlanItem(
                order=index + 1,
                image_path=image_path,
                image_name=image_path.name,
                setup_label=None,
                gantry_angle=None,
                collimator_angle=None,
                couch_angle=None,
                x_axis_label=None,
                y_axis_label=None,
                dx_positive_label=None,
                dx_negative_label=None,
                dy_positive_label=None,
                dy_negative_label=None,
            )
            for index, image_path in enumerate(list_images(self.image_path_value()))
        ]

    def load_plan_preview(self) -> None:
        if self.loading_options or not hasattr(self, "table"):
            return
        self.discard_current_unsaved_series()
        try:
            self.loaded_plan = self.build_plan()
        except Exception as exc:
            self.loaded_plan = []
            self.current_series = None
            self.table.setRowCount(0)
            self.preview.clear()
            self.preview.setText("解析後、行を選択してください")
            self.log(f"解析計画の読み込みに失敗しました: {exc}")
            self.update_save_button_state()
            return
        self.current_series = None
        self.render_plan_preview(self.loaded_plan)
        self.preview.clear()
        self.preview.setText("解析後、行を選択してください")
        self.log(f"解析計画を読み込みました: {len(self.loaded_plan)} images.")
        self.update_save_button_state()

    def discard_current_unsaved_series(self) -> None:
        if self.current_series is not None and not self.current_series.saved and self.current_series.source != "history":
            if hasattr(self, "series") and self.current_series in self.series:
                self.series.remove(self.current_series)
                self.render_series_list()
        self.current_series = None

    def series_name(self, plan: list[AnalysisPlanItem]) -> str:
        image_dir = self.image_path_value().name or str(self.image_path_value())
        return f"{image_dir} ({len(plan)} images)"

    def set_current_series(self, series: AnalysisSeries) -> None:
        self.current_series = series
        self.render_series(series)
        self.update_save_button_state()

    def after_analysis(self, series: AnalysisSeries) -> None:
        self.log(f"解析が完了しました: {series.name}")

    def result_preview_clicked(self) -> None:
        if self.current_series is None:
            show_error(self, "プレビューエラー", ValueError("解析済みシリーズが選択されていません。"))
            return
        try:
            grouped = self.report_data_with_current_series(self.current_series)
            pages = render_grouped_report_pages(grouped, self.current_series.machine_name)
        except Exception as exc:
            show_error(self, "プレビューエラー", exc)
            return
        PagePreviewDialog("Result Preview", pages, list(grouped.keys()), self).exec()

    def save_clicked(self) -> None:
        if self.current_series is None:
            show_error(self, "保存エラー", ValueError("解析済みシリーズが選択されていません。"))
            return
        series = self.current_series
        if series.saved:
            self.log(f"保存済みです: {series.name}")
            return
        try:
            self.save_series(series)
        except Exception as exc:
            show_error(self, "保存エラー", exc)
            return
        series.saved = True
        self.refresh_database_options()
        self.current_series = series
        self.render_series(series)
        self.log(f"保存しました: {series.name}")
        self.update_save_button_state()

    def export_pdf_clicked(self) -> None:
        if self.current_series is None:
            show_error(self, "出力エラー", ValueError("解析済みシリーズが選択されていません。"))
            return
        series = self.current_series
        try:
            grouped = self.report_data_with_current_series(series)
            pages = render_grouped_report_pages(grouped, series.machine_name)
        except Exception as exc:
            show_error(self, "プレビューエラー", exc)
            return
        PagePreviewDialog(
            "Review & Output",
            pages,
            list(grouped.keys()),
            self,
            export_pdf_handler=lambda: self.export_pdf_from_preview(series, grouped),
            show_save_result_button=False,
        ).exec()

    def save_result_from_preview(self, series: AnalysisSeries) -> bool:
        if series.saved:
            self.log(f"保存済みです: {series.name}")
            return True
        try:
            series.session_id = self.save_series(series)
        except Exception as exc:
            show_error(self, "保存エラー", exc)
            return False
        self.mark_series_saved(series)
        self.log(f"保存しました: {series.name}")
        return True

    def export_pdf_from_preview(
        self,
        series: AnalysisSeries,
        grouped: dict[str, list[ReportPoint]],
    ) -> bool:
        if not series.saved:
            reply = QMessageBox.question(
                self,
                "保存と出力",
                "結果を保存してPDFを出力します。",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return False
            if not self.save_result_from_preview(series):
                return False
        default_name = (
            f"{series.machine_name}_report.pdf"
            if series.machine_name
            else "report.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "PDFファイルを保存",
            str(Path("log") / default_name),
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not path:
            return False
        try:
            write_grouped_pdf(grouped, path, machine_name=series.machine_name)
        except Exception as exc:
            show_error(self, "PDF出力エラー", exc)
            return False
        self.refresh_database_options()
        self.current_series = series
        self.render_series(series)
        self.log(f"PDFを出力しました: {path}")
        self.update_save_button_state()
        return True

    def mark_series_saved(self, series: AnalysisSeries) -> None:
        series.saved = True
        self.refresh_database_options()
        self.current_series = series
        self.render_series(series)
        self.update_save_button_state()

    def save_series(self, series: AnalysisSeries) -> int:
        metadata = [
            AnalysisMetadata(
                gantry_angle=item.gantry_angle,
                collimator_angle=item.collimator_angle,
                couch_angle=item.couch_angle,
                note=item.setup_label,
                x_axis_label=item.x_axis_label,
                y_axis_label=item.y_axis_label,
                dx_positive_label=item.dx_positive_label,
                dx_negative_label=item.dx_negative_label,
                dy_positive_label=item.dy_positive_label,
                dy_negative_label=item.dy_negative_label,
                x_inverted=item.x_inverted,
            )
            for item in series.plan
        ]
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            session_id = create_session(
                connection,
                inspection_type=series.inspection_type,
                machine_name=series.machine_name,
                started_at=parse_datetime_or_none(series.started_at),
            )
            save_analysis_results(connection, session_id, series.analyses, metadata)
            return session_id
        finally:
            connection.close()

    def update_save_button_state(self) -> None:
        if hasattr(self, "save_button"):
            self.save_button.setEnabled(self.current_series is not None and not self.current_series.saved)

    def render_series(self, series: AnalysisSeries) -> None:
        if series.points and not series.analyses:
            self.render_persisted_series(series)
            return
        self.table.setRowCount(len(series.plan))
        for row, (plan_item, analysis) in enumerate(zip(series.plan, series.analyses)):
            result = analysis.result
            values = [
                f"{plan_item.order:02d}",
                plan_item.image_name,
                plan_item.setup_label or "",
                status_text(result.succeeded, result.dx_mm, result.dy_mm),
                value_text(result.dx_mm),
                value_text(result.dy_mm),
                value_text(result.distance_mm),
                value_text(plan_item.gantry_angle),
                value_text(plan_item.collimator_angle),
                value_text(plan_item.couch_angle),
                plan_item.dx_positive_label or "",
                plan_item.dx_negative_label or "",
                plan_item.dy_positive_label or "",
                plan_item.dy_negative_label or "",
                optional_parameter_text(result.parameters.beam_size_px),
                optional_parameter_text(result.parameters.target_size_px),
                f"{result.parameters.pixel_size_mm:.4f}",
                "otsu" if result.parameters.beam_threshold == 0 else str(result.parameters.beam_threshold),
                str(result.parameters.ball_sensitivity),
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 3:
                    apply_status_style(table_item, value)
                self.table.setItem(row, column, table_item)
        configure_result_table(self.table)
        if series.analyses:
            self.select_preview_row(0)

    def render_persisted_series(self, series: AnalysisSeries) -> None:
        self.table.setRowCount(len(series.points))
        for row, point in enumerate(series.points):
            values = [
                f"{row + 1:02d}",
                point.image_name,
                point.setup_label or "",
                status_text(True, point.dx_mm, point.dy_mm),
                value_text(point.dx_mm),
                value_text(point.dy_mm),
                value_text(point.distance_mm),
                value_text(point.gantry_angle),
                value_text(point.collimator_angle),
                value_text(point.couch_angle),
                point.dx_positive_label or "",
                point.dx_negative_label or "",
                point.dy_positive_label or "",
                point.dy_negative_label or "",
                optional_parameter_text(point.beam_size_px),
                optional_parameter_text(point.target_size_px),
                f"{point.pixel_size_mm:.4f}",
                "otsu" if point.beam_threshold == 0 else str(point.beam_threshold),
                str(point.ball_sensitivity),
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 3:
                    apply_status_style(table_item, value)
                self.table.setItem(row, column, table_item)
        configure_result_table(self.table)
        if series.points:
            self.select_preview_row(0)

    def render_plan_preview(self, plan: list[AnalysisPlanItem]) -> None:
        self.updating_plan_table = True
        self.table.setRowCount(len(plan))
        for row, plan_item in enumerate(plan):
            values = [
                f"{plan_item.order:02d}",
                plan_item.image_name,
                plan_item.setup_label or "",
                "",
                "",
                "",
                "",
                value_text(plan_item.gantry_angle),
                value_text(plan_item.collimator_angle),
                value_text(plan_item.couch_angle),
                plan_item.dx_positive_label or "",
                plan_item.dx_negative_label or "",
                plan_item.dy_positive_label or "",
                plan_item.dy_negative_label or "",
                optional_parameter_text(plan_item.parameters.beam_size_px if plan_item.parameters else None),
                optional_parameter_text(plan_item.parameters.target_size_px if plan_item.parameters else None),
                f"{plan_item.parameters.pixel_size_mm:.4f}" if plan_item.parameters else "",
                ("otsu" if plan_item.parameters and plan_item.parameters.beam_threshold == 0 else str(plan_item.parameters.beam_threshold)) if plan_item.parameters else "",
                str(plan_item.parameters.ball_sensitivity) if plan_item.parameters else "",
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 3:
                    apply_status_style(table_item, value)
                self.table.setItem(row, column, table_item)
            combo = QComboBox()
            combo.addItem("", None)
            for setup in self.available_setups():
                combo.addItem(setup.name, setup)
            if plan_item.setup_label:
                combo.setCurrentText(plan_item.setup_label)
            combo.currentIndexChanged.connect(lambda _index, table_row=row: self.plan_setup_changed(table_row))
            self.table.setCellWidget(row, 2, combo)
        configure_result_table(self.table)
        self.updating_plan_table = False
        if plan:
            self.select_preview_row(0)

    def available_setups(self) -> list[AnalysisSetup]:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            rows = list_setups(connection)
        finally:
            connection.close()
        return [analysis_setup_from_row(row) for row in rows]

    def plan_setup_changed(self, row: int) -> None:
        if self.updating_plan_table or row < 0 or row >= len(self.loaded_plan):
            return
        widget = self.table.cellWidget(row, 2)
        if not isinstance(widget, QComboBox):
            return
        setup = widget.currentData()
        self.loaded_plan[row] = plan_item_with_setup(
            self.loaded_plan[row],
            setup if isinstance(setup, AnalysisSetup) else None,
        )
        self.update_plan_row_display(row)
        self.clear_current_analysis_results()

    def update_plan_row_display(self, row: int) -> None:
        if row < 0 or row >= len(self.loaded_plan):
            return
        item = self.loaded_plan[row]
        values = {
            3: "",
            4: "",
            5: "",
            6: "",
            7: value_text(item.gantry_angle),
            8: value_text(item.collimator_angle),
            9: value_text(item.couch_angle),
            10: item.dx_positive_label or "",
            11: item.dx_negative_label or "",
            12: item.dy_positive_label or "",
            13: item.dy_negative_label or "",
            14: optional_parameter_text(item.parameters.beam_size_px if item.parameters else None),
            15: optional_parameter_text(item.parameters.target_size_px if item.parameters else None),
            16: f"{item.parameters.pixel_size_mm:.4f}" if item.parameters else "",
            17: ("otsu" if item.parameters and item.parameters.beam_threshold == 0 else str(item.parameters.beam_threshold)) if item.parameters else "",
            18: str(item.parameters.ball_sensitivity) if item.parameters else "",
        }
        for column, value in values.items():
            table_item = self.table.item(row, column)
            if table_item is None:
                table_item = QTableWidgetItem()
                self.table.setItem(row, column, table_item)
            table_item.setText(value)
            if column == 3:
                apply_status_style(table_item, value)

    def clear_current_analysis_results(self) -> None:
        if self.current_series is None or self.current_series.saved or self.current_series.source == "history":
            self.current_series = None
            self.preview.clear()
            self.preview.setText("解析後、行を選択してください")
            return
        if hasattr(self, "series") and self.current_series in self.series:
            self.series.remove(self.current_series)
            self.render_series_list()
        self.current_series = None
        self.render_plan_preview(self.loaded_plan)
        self.preview.clear()
        self.preview.setText("setupが変更されたため解析結果をクリアしました。")

    def update_preview_from_selection(self) -> None:
        if self.current_series is None:
            row = self.selected_row()
            if row is not None and self.show_unanalyzed_plan_preview(row):
                return
            self.preview.clear()
            self.preview.setText("解析後、行を選択してください")
            return
        row = self.selected_row()
        if row is None:
            self.preview.clear()
            self.preview.setText("行を選択してください")
            return
        if row < 0 or row >= len(self.current_series.analyses):
            if self.current_series.points and 0 <= row < len(self.current_series.points):
                pixmap = focused_overlay_pixmap(self.current_series.points[row])
                if pixmap is None:
                    self.preview.clear()
                    self.preview.setText("プレビュー画像を生成できません")
                else:
                    self.preview.setPixmap(
                        pixmap.scaled(
                            self.preview.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                return
            if self.show_unanalyzed_series_preview(row):
                return
            self.preview.clear()
            self.preview.setText("解析済みの行を選択してください")
            return
        pixmap = self.preview_page_pixmap(self.current_series, row)
        self.preview.setPixmap(pixmap)

    def selected_row(self) -> int | None:
        selected = self.table.selectionModel().selectedRows()
        if selected:
            return selected[0].row()
        selected_items = self.table.selectedItems()
        if selected_items:
            return selected_items[0].row()
        return None

    def show_previous_preview(self) -> None:
        self.move_preview_selection(-1)

    def show_next_preview(self) -> None:
        self.move_preview_selection(1)

    def move_preview_selection(self, offset: int) -> None:
        row_count = self.table.rowCount()
        if row_count == 0:
            return
        row = self.selected_row()
        next_row = 0 if row is None else max(0, min(row + offset, row_count - 1))
        self.select_preview_row(next_row)

    def select_preview_row(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        self.table.setCurrentCell(row, 0)
        self.table.selectRow(row)
        item = self.table.item(row, 0)
        if item is not None:
            self.table.scrollToItem(item)
        self.update_preview_from_selection()

    def preview_page_pixmap(self, series: AnalysisSeries, row: int) -> QPixmap:
        pixmap = pixmap_from_bgr(series.analyses[row].debug_images.focused_overlay).scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return overlay_analysis_text(pixmap, series.plan[row], series.analyses[row])

    def show_unanalyzed_plan_preview(self, row: int) -> bool:
        if row < 0 or row >= len(self.loaded_plan):
            return False
        return self.show_unanalyzed_preview(self.loaded_plan[row])

    def show_unanalyzed_series_preview(self, row: int) -> bool:
        if self.current_series is None or row < 0 or row >= len(self.current_series.plan):
            return False
        return self.show_unanalyzed_preview(self.current_series.plan[row])

    def show_unanalyzed_preview(self, plan_item: AnalysisPlanItem) -> bool:
        image = cv2.imread(str(plan_item.image_path), cv2.IMREAD_COLOR)
        if image is None:
            return False
        scaled = pixmap_from_bgr(image).scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(overlay_unanalyzed_text(scaled, plan_item))
        return True

    def series_preview_pages(self, series: AnalysisSeries) -> list[QPixmap]:
        return [
            self.preview_page_pixmap(series, row)
            for row in range(min(len(series.plan), len(series.analyses)))
        ]

    def report_data_with_current_series(self, series: AnalysisSeries) -> dict[str, list[ReportPoint]]:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            grouped = load_report_data(
                connection,
                machine_name=series.machine_name,
                limit=10 if series.saved else 9,
            )
        finally:
            connection.close()

        if not series.saved:
            now = datetime.now().isoformat(timespec="seconds")
            for plan_item, analysis in zip(series.plan, series.analyses):
                if not analysis.result.succeeded:
                    continue
                label = plan_item.setup_label or plan_item.image_name
                grouped.setdefault(label, [])
                grouped[label].append(
                    ReportPoint(
                        analyzed_at=now,
                        image_name=plan_item.image_name,
                        setup_label=label,
                        dx_mm=float(analysis.result.dx_mm),
                        dy_mm=float(analysis.result.dy_mm),
                        distance_mm=float(analysis.result.distance_mm),
                        gantry_angle=plan_item.gantry_angle,
                        collimator_angle=plan_item.collimator_angle,
                        couch_angle=plan_item.couch_angle,
                        image_path=str(plan_item.image_path),
                        pixel_size_mm=analysis.result.parameters.pixel_size_mm,
                        beam_threshold=analysis.result.parameters.beam_threshold,
                        ball_sensitivity=analysis.result.parameters.ball_sensitivity,
                        beam_size_px=analysis.result.parameters.beam_size_px,
                        target_size_px=analysis.result.parameters.target_size_px,
                        x_axis_label=plan_item.x_axis_label or "",
                        y_axis_label=plan_item.y_axis_label or "",
                        dx_positive_label=plan_item.dx_positive_label or "+dx",
                        dx_negative_label=plan_item.dx_negative_label or "-dx",
                        dy_positive_label=plan_item.dy_positive_label or "+dy",
                        dy_negative_label=plan_item.dy_negative_label or "-dy",
                        x_inverted=plan_item.x_inverted,
                        inspection_type=series.inspection_type,
                    )
                )
                grouped[label] = grouped[label][-10:]

        ordered_grouped: dict[str, list[ReportPoint]] = {}
        for plan_item in series.plan:
            label = plan_item.setup_label or plan_item.image_name
            if label in grouped and label not in ordered_grouped:
                ordered_grouped[label] = grouped[label]
        for label, points in grouped.items():
            if label not in ordered_grouped:
                ordered_grouped[label] = points

        if not ordered_grouped:
            raise ValueError("プレビュー可能な成功済み解析結果がありません。")
        return ordered_grouped

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_preview_from_selection()

    def image_path_value(self) -> Path:
        return Path(self.image_path.text()).expanduser()

    def output_path_value(self) -> Path:
        return Path(self.output_path.text()).expanduser()

    def machine_name(self) -> str | None:
        return self.machine_combo.currentText() or None

    def log(self, message: str) -> None:
        self.log_output.append(message)


class DailyTab(AnalysisTab):
    def __init__(self) -> None:
        self.series: list[AnalysisSeries] = []
        self.analysis_mode = "daily"
        self.temp_mode_active = False
        self.simple_analysis_by_row: dict[int, Analysis] = {}
        self.simple_loaded_inputs: list[str] = []
        self.simple_series = AnalysisSeries(
            name="Test",
            plan=[],
            analyses=[],
            inspection_type="simple_test",
            machine_name=None,
        )
        super().__init__(
            default_inspection="daily",
            default_image_path="sample/set",
            show_inspection=False,
        )
        self.series_list.currentRowChanged.connect(self.select_series)
        self.series_panel.setFixedWidth(SERIES_PANEL_WIDTH)
        self.series_list.setVisible(True)
        self.save_series_button.setVisible(True)
        self.remove_series_button.setVisible(True)
        self.active_toggle_button.setVisible(True)
        self.load_recent_saved_series()
        self.update_series_buttons()

    def build_table_group(self) -> QWidget:
        return self.build_series_table_group(show_series_list=True)

    def add_settings_leading_widgets(self, layout: QHBoxLayout) -> None:
        mode_widget = QWidget()
        mode_widget.setFixedWidth(MODE_WIDGET_SIZE[0])
        mode_layout = QVBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(2)
        mode_label = QLabel("Mode")
        mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumHeight(44)
        self.mode_combo.addItem("Daily", "daily")
        self.mode_combo.addItem("Test", "simple_test")
        self.mode_combo.currentIndexChanged.connect(self.mode_changed)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        layout.addWidget(mode_widget)

    def mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        if mode == self.analysis_mode:
            return
        self.analysis_mode = str(mode)
        self.reset_temporary_modes()
        if self.analysis_mode == "daily":
            self.inspection_type.setCurrentText("daily")
            self.series_panel.setFixedWidth(SERIES_PANEL_WIDTH)
            self.series_query_toggle.setVisible(True)
            self.series_list.setVisible(True)
            self.save_series_button.setVisible(True)
            self.remove_series_button.setVisible(True)
            self.active_toggle_button.setVisible(True)
            self.delete_row_button.setVisible(False)
            self.export_button.setEnabled(True)
            self.load_plan_preview()
            self.load_recent_saved_series()
            self.update_series_buttons()
            self.log("Daily modeを開始しました。")
        elif self.analysis_mode == "set_test":
            self.start_set_test_mode()
        elif self.analysis_mode == "simple_test":
            self.start_simple_test_mode()
        self.update_save_button_state()

    def reset_temporary_modes(self) -> None:
        self.series.clear()
        self.series_list.clear()
        self.simple_series = AnalysisSeries(
            name="Test",
            plan=[],
            analyses=[],
            inspection_type="simple_test",
            machine_name=self.machine_name(),
        )
        self.simple_analysis_by_row = {}
        self.simple_loaded_inputs = []
        self.current_series = None
        self.preview.clear()
        self.preview.setText("解析後、行を選択してください")

    def start_set_test_mode(self) -> None:
        self.temp_mode_active = True
        self.inspection_type.setCurrentText("temporary")
        self.export_button.setEnabled(True)
        self.series_panel.setFixedWidth(SERIES_PANEL_WIDTH)
        self.series_query_toggle.setVisible(True)
        self.series_list.setVisible(True)
        self.remove_series_button.setVisible(True)
        self.active_toggle_button.setVisible(True)
        self.update_set_test_series_buttons()
        self.render_plan_preview(self.loaded_plan)
        self.log("Set Test modeを開始しました。")

    def start_simple_test_mode(self) -> None:
        self.temp_mode_active = False
        self.inspection_type.setCurrentText("simple_test")
        self.export_button.setEnabled(False)
        self.delete_row_button.setVisible(True)
        self.series_query_toggle.setChecked(False)
        self.series_query_toggle.setVisible(False)
        self.series_query_frame.setVisible(False)
        self.series_list.setVisible(False)
        self.save_series_button.setVisible(False)
        self.remove_series_button.setVisible(False)
        self.active_toggle_button.setVisible(False)
        self.series_panel.setFixedWidth(0)
        self.loaded_plan = []
        self.simple_series.plan = []
        self.simple_series.analyses = []
        self.simple_analysis_by_row = {}
        self.simple_loaded_inputs = []
        self.load_plan_preview()
        self.log("Test modeを開始しました。")

    def load_plan_preview(self) -> None:
        if getattr(self, "analysis_mode", "daily") == "simple_test":
            self.append_simple_images_from_input()
            return
        super().load_plan_preview()
        if hasattr(self, "series_list") and self.analysis_mode in ("daily", "set_test"):
            self.series_list.setCurrentRow(-1)

    def analyze_clicked(self) -> None:
        if self.analysis_mode == "simple_test":
            self.analyze_simple_clicked()
            return
        super().analyze_clicked()

    def analyze_simple_clicked(self) -> None:
        try:
            plan_rows = [
                row for row, item in enumerate(self.loaded_plan)
                if row not in self.simple_analysis_by_row and item.setup_label is not None
            ]
            plan = [self.loaded_plan[row] for row in plan_rows]
            if not plan:
                raise ValueError("解析対象の未解析画像がありません。setup未選択の行がないか確認してください。")
            analyses = self.analyze_plan_with_progress(plan)
        except Exception as exc:
            show_error(self, "解析エラー", exc)
            return
        for row, analysis in zip(plan_rows, analyses):
            self.simple_analysis_by_row[row] = analysis
        self.simple_series.machine_name = self.machine_name()
        self.simple_series.saved = False
        self.current_series = self.simple_series
        self.render_simple_table()
        self.select_preview_row(plan_rows[0])
        self.log(f"Testに{len(plan)}件の画像を追加しました。")

    def append_simple_images_from_input(self) -> None:
        key = str(self.image_path_value().resolve())
        if key in self.simple_loaded_inputs:
            return
        plan = self.build_simple_plan()
        if not plan:
            self.render_simple_table()
            return
        self.simple_loaded_inputs.append(key)
        self.simple_series.plan.extend(plan)
        self.loaded_plan = self.simple_series.plan
        self.current_series = self.simple_series
        self.render_simple_table()
        self.select_preview_row(len(self.loaded_plan) - len(plan))
        self.log(f"Testに画像を読み込みました: {len(plan)} images.")

    def build_simple_plan(self) -> list[AnalysisPlanItem]:
        start_order = len(self.simple_series.plan) + 1
        setups = self.preset_setups()
        return [
            plan_item_with_setup(
                AnalysisPlanItem(
                    order=start_order + index,
                    image_path=image_path,
                    image_name=image_path.name,
                    setup_label=None,
                    gantry_angle=None,
                    collimator_angle=None,
                    couch_angle=None,
                    x_axis_label=None,
                    y_axis_label=None,
                    dx_positive_label=None,
                    dx_negative_label=None,
                    dy_positive_label=None,
                    dy_negative_label=None,
                ),
                setups[index] if index < len(setups) else None,
            )
            for index, image_path in enumerate(list_images(self.image_path_value()))
        ]

    def preset_setups(self) -> list[AnalysisSetup]:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            preset = get_setup_preset(connection, self.preset_combo.currentText())
            if preset is None:
                return []
            steps = list_setup_steps(connection, int(preset["id"]))
        finally:
            connection.close()
        return [
            AnalysisSetup(
                name=step["label"],
                gantry_angle=float(step["gantry_angle"]),
                collimator_angle=float(step["collimator_angle"]),
                couch_angle=float(step["couch_angle"]),
                dx_positive_label=step["dx_positive_label"],
                dx_negative_label=step["dx_negative_label"],
                dy_positive_label=step["dy_positive_label"],
                dy_negative_label=step["dy_negative_label"],
                field_size_px=step["beam_size_px"],
                target_size_px=step["target_size_px"],
                pixel_size_mm=float(step["pixel_size_mm"]),
                beam_threshold=int(step["beam_threshold"]),
                ball_sensitivity=int(step["ball_sensitivity"]),
            )
            for step in steps
        ]

    def after_analysis(self, series: AnalysisSeries) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            self.current_series = series
            super().after_analysis(series)
            return
        self.series.insert(0, series)
        self.series = self.series[:10]
        self.render_series_list()
        self.series_list.setCurrentRow(0)
        self.update_series_buttons()
        self.log(f"解析シリーズに追加しました: {series.name}")

    def render_simple_table(self) -> None:
        self.updating_plan_table = True
        self.table.setRowCount(len(self.loaded_plan))
        setups = self.available_setups()
        for row, plan_item in enumerate(self.loaded_plan):
            analysis = self.simple_analysis_by_row.get(row)
            if analysis is None:
                values = [
                    f"{plan_item.order:02d}",
                    plan_item.image_name,
                    plan_item.setup_label or "",
                    "",
                    "",
                    "",
                    "",
                    value_text(plan_item.gantry_angle),
                    value_text(plan_item.collimator_angle),
                    value_text(plan_item.couch_angle),
                    plan_item.dx_positive_label or "",
                    plan_item.dx_negative_label or "",
                    plan_item.dy_positive_label or "",
                    plan_item.dy_negative_label or "",
                    optional_parameter_text(plan_item.parameters.beam_size_px if plan_item.parameters else None),
                    optional_parameter_text(plan_item.parameters.target_size_px if plan_item.parameters else None),
                    f"{plan_item.parameters.pixel_size_mm:.4f}" if plan_item.parameters else "",
                    ("otsu" if plan_item.parameters and plan_item.parameters.beam_threshold == 0 else str(plan_item.parameters.beam_threshold)) if plan_item.parameters else "",
                    str(plan_item.parameters.ball_sensitivity) if plan_item.parameters else "",
                ]
            else:
                result = analysis.result
                values = [
                    f"{plan_item.order:02d}",
                    plan_item.image_name,
                    plan_item.setup_label or "",
                    status_text(result.succeeded, result.dx_mm, result.dy_mm),
                    value_text(result.dx_mm),
                    value_text(result.dy_mm),
                    value_text(result.distance_mm),
                    value_text(plan_item.gantry_angle),
                    value_text(plan_item.collimator_angle),
                    value_text(plan_item.couch_angle),
                    plan_item.dx_positive_label or "",
                    plan_item.dx_negative_label or "",
                    plan_item.dy_positive_label or "",
                    plan_item.dy_negative_label or "",
                    optional_parameter_text(result.parameters.beam_size_px),
                    optional_parameter_text(result.parameters.target_size_px),
                    f"{result.parameters.pixel_size_mm:.4f}",
                    "otsu" if result.parameters.beam_threshold == 0 else str(result.parameters.beam_threshold),
                    str(result.parameters.ball_sensitivity),
                ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 3:
                    apply_status_style(table_item, value)
                self.table.setItem(row, column, table_item)
            combo = QComboBox()
            combo.addItem("", None)
            for setup in setups:
                combo.addItem(setup.name, setup)
            if plan_item.setup_label:
                combo.setCurrentText(plan_item.setup_label)
            combo.currentIndexChanged.connect(lambda _index, table_row=row: self.plan_setup_changed(table_row))
            self.table.setCellWidget(row, 2, combo)
        configure_result_table(self.table)
        self.updating_plan_table = False

    def plan_setup_changed(self, row: int) -> None:
        if self.analysis_mode != "simple_test":
            super().plan_setup_changed(row)
            return
        if self.updating_plan_table or row < 0 or row >= len(self.loaded_plan):
            return
        widget = self.table.cellWidget(row, 2)
        if not isinstance(widget, QComboBox):
            return
        setup = widget.currentData()
        self.loaded_plan[row] = plan_item_with_setup(
            self.loaded_plan[row],
            setup if isinstance(setup, AnalysisSetup) else None,
        )
        self.simple_series.plan = self.loaded_plan
        self.simple_analysis_by_row.pop(row, None)
        self.render_simple_table()
        self.select_preview_row(row)
        self.preview.clear()
        self.preview.setText("setupが変更されたため、この行の解析結果をクリアしました。")

    def delete_selected_simple_row(self) -> None:
        if self.analysis_mode != "simple_test":
            return
        row = self.selected_row()
        if row is None or row < 0 or row >= len(self.loaded_plan):
            show_error(self, "行削除エラー", ValueError("削除する行を選択してください。"))
            return
        del self.loaded_plan[row]
        self.simple_analysis_by_row = {
            (index if index < row else index - 1): analysis
            for index, analysis in self.simple_analysis_by_row.items()
            if index != row
        }
        self.loaded_plan = [
            AnalysisPlanItem(
                order=index + 1,
                image_path=item.image_path,
                image_name=item.image_name,
                setup_label=item.setup_label,
                gantry_angle=item.gantry_angle,
                collimator_angle=item.collimator_angle,
                couch_angle=item.couch_angle,
                x_axis_label=item.x_axis_label,
                y_axis_label=item.y_axis_label,
                dx_positive_label=item.dx_positive_label,
                dx_negative_label=item.dx_negative_label,
                dy_positive_label=item.dy_positive_label,
                dy_negative_label=item.dy_negative_label,
                x_inverted=item.x_inverted,
                parameters=item.parameters,
            )
            for index, item in enumerate(self.loaded_plan)
        ]
        self.simple_series.plan = self.loaded_plan
        self.render_simple_table()
        if self.loaded_plan:
            self.select_preview_row(min(row, len(self.loaded_plan) - 1))
        else:
            self.preview.clear()
            self.preview.setText("解析後、行を選択してください")

    def update_preview_from_selection(self) -> None:
        if self.analysis_mode != "simple_test":
            super().update_preview_from_selection()
            return
        row = self.selected_row()
        if row is None:
            self.preview.clear()
            self.preview.setText("行を選択してください")
            return
        analysis = self.simple_analysis_by_row.get(row)
        if analysis is None or row >= len(self.loaded_plan):
            if self.show_unanalyzed_plan_preview(row):
                return
            self.preview.clear()
            self.preview.setText("解析済みの行を選択してください")
            return
        pixmap = pixmap_from_bgr(analysis.debug_images.focused_overlay).scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(
            overlay_analysis_text(
                pixmap,
                self.loaded_plan[row],
                analysis,
            )
        )

    def select_series(self, row: int) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            return
        if row < 0 or row >= len(self.series):
            self.update_series_buttons()
            return
        self.set_current_series(self.series[row])
        self.update_series_buttons()

    def update_series_buttons(self) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            return
        row = self.series_list.currentRow()
        has_selection = 0 <= row < len(self.series)
        self.remove_series_button.setEnabled(has_selection)
        self.save_series_button.setEnabled(has_selection)
        self.active_toggle_button.setEnabled(has_selection)

    def update_set_test_series_buttons(self) -> None:
        self.update_series_buttons()

    def remove_selected_series(self) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            return
        row = self.series_list.currentRow()
        if row < 0 or row >= len(self.series):
            show_error(self, "シリーズエラー", ValueError("シリーズを選択してください。"))
            return
        if self.series[row].source == "history":
            self.delete_saved_series(self.series[row])
            return
        removed = self.series.pop(row)
        self.series_list.takeItem(row)
        if self.series:
            next_row = min(row, len(self.series) - 1)
            self.series_list.setCurrentRow(next_row)
        else:
            self.current_series = None
            self.render_plan_preview(self.loaded_plan)
            self.preview.clear()
            self.preview.setText("解析後、行を選択してください")
            self.update_save_button_state()
        self.log(f"シリーズリストから削除しました: {removed.name}")
        self.update_series_buttons()

    def delete_saved_series(self, series: AnalysisSeries) -> None:
        if series.session_id is None:
            show_error(self, "シリーズ削除エラー", ValueError("削除対象のseries idがありません。"))
            return
        reply = QMessageBox.question(
            self,
            "シリーズ削除",
            "選択した過去seriesと解析結果を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            delete_session_results(connection, series.session_id)
            connection.commit()
        finally:
            connection.close()
        self.log(f"過去seriesを削除しました: {series.name}")
        self.load_recent_saved_series()
        if self.current_series is series:
            self.current_series = None
            self.render_plan_preview(self.loaded_plan)
            self.preview.clear()
            self.preview.setText("解析後、行を選択してください")

    def selected_series(self) -> AnalysisSeries | None:
        row = self.series_list.currentRow()
        if row < 0 or row >= len(self.series):
            return None
        return self.series[row]

    def series_label(self, series: AnalysisSeries) -> str:
        prefix = "" if series.saved else "* "
        inactive = "" if series.output_active else " [inactive]"
        return f"{prefix}{series.name}{inactive}"

    def render_series_list(self) -> None:
        current_series = self.selected_series()
        self.series_list.blockSignals(True)
        self.series_list.clear()
        for series in self.series:
            item = QListWidgetItem(self.series_label(series))
            if series.source == "history":
                item.setBackground(QColor("#dddddd"))
            if not series.output_active:
                item.setForeground(QColor("#777777"))
            self.series_list.addItem(item)
        self.series_list.blockSignals(False)
        if current_series in self.series:
            self.series_list.setCurrentRow(self.series.index(current_series))
        elif self.series:
            self.series_list.setCurrentRow(0)
        self.update_series_buttons()

    def load_recent_saved_series(self) -> None:
        if self.analysis_mode != "daily":
            return
        if self.series_query_mode.currentData() == "date":
            start_date = self.series_from_date.date().toString("yyyy-MM-dd")
            end_date = self.series_to_date.date().toString("yyyy-MM-dd")
            limit = None
        else:
            start_date = "2000-01-01"
            end_date = QDate.currentDate().toString("yyyy-MM-dd")
            limit = self.series_limit.value()
        histories = load_recent_saved_series(
            DEFAULT_DB_PATH,
            self.machine_name(),
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        current = [series for series in self.series if series.source != "history"]
        current_session_ids = {
            series.session_id
            for series in current
            if series.session_id is not None
        }
        histories = [
            series
            for series in histories
            if series.session_id not in current_session_ids
        ]
        self.series = sorted(
            current + histories,
            key=lambda series: series.started_at or "",
            reverse=True,
        )
        self.render_series_list()

    def query_series_list(self) -> None:
        self.load_recent_saved_series()

    def toggle_series_query_options(self, checked: bool) -> None:
        self.series_query_frame.setVisible(checked)
        self.series_query_toggle.setText("Hide Query" if checked else "Query Options")
        if checked:
            self.update_series_query_mode()

    def update_series_query_mode(self) -> None:
        mode = self.series_query_mode.currentData()
        show_date = mode == "date"
        self.series_count_query_widget.setVisible(not show_date)
        self.series_date_query_widget.setVisible(show_date)

    def toggle_selected_series_active(self) -> None:
        series = self.selected_series()
        if series is None:
            show_error(self, "シリーズエラー", ValueError("シリーズを選択してください。"))
            return
        series.output_active = not series.output_active
        self.render_series_list()

    def latest_series(self) -> AnalysisSeries | None:
        if not self.series:
            return None
        return self.series[0]

    def save_selected_series(self) -> bool:
        if self.analysis_mode not in ("daily", "set_test"):
            return False
        series = self.selected_series()
        if series is None:
            show_error(self, "保存エラー", ValueError("保存するシリーズを選択してください。"))
            return False
        if series.source == "history":
            show_error(self, "保存エラー", ValueError("過去データはAnalyzeタブでは保存できません。"))
            return False
        if series.saved:
            show_error(self, "保存エラー", ValueError("このシリーズは保存済みです。"))
            return True
        self.current_series = series
        self.save_result_from_preview(series)
        self.update_series_buttons()
        return series.saved

    def save_latest_series(self) -> bool:
        latest = self.latest_series()
        if latest is None:
            show_error(self, "保存エラー", ValueError("保存できる最新シリーズがありません。"))
            return False
        self.series_list.setCurrentRow(0)
        return self.save_selected_series()

    def mark_series_saved(self, series: AnalysisSeries) -> None:
        super().mark_series_saved(series)
        if self.analysis_mode in ("daily", "set_test"):
            for row, item_series in enumerate(self.series):
                if item_series is series and self.series_list.item(row) is not None:
                    self.series_list.item(row).setText(self.series_label(series))
                    break
            self.update_series_buttons()

    def save_clicked(self) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            super().save_clicked()
            return
        self.save_selected_series()

    def export_pdf_clicked(self) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            super().export_pdf_clicked()
            return
        try:
            series_list = self.saved_series_for_output()
        except Exception as exc:
            show_error(self, "出力エラー", exc)
            return
        if series_list is None:
            return
        if not series_list:
            show_error(self, "出力エラー", ValueError("出力できる保存済みseriesがありません。"))
            return
        try:
            grouped = self.report_data_from_series_list(series_list)
            pages = render_grouped_report_pages(
                grouped,
                self.machine_name(),
                show_mode_boundary=False,
            )
        except Exception as exc:
            show_error(self, "プレビューエラー", exc)
            return
        PagePreviewDialog(
            "Review & Output",
            pages,
            list(grouped.keys()),
            self,
            export_pdf_handler=lambda: self.export_saved_pdf_from_preview(grouped),
            show_save_result_button=False,
        ).exec()

    def saved_series_for_output(self) -> list[AnalysisSeries] | None:
        selected_row = self.series_list.currentRow()
        if selected_row < 0 or selected_row >= len(self.series):
            selected_row = 0
        if not self.series:
            return []
        selected = self.series[selected_row]
        if not selected.saved:
            reply = QMessageBox.question(
                self,
                "保存確認",
                "最新の解析結果が保存されていません。保存してReview & Outputを続行しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return None
            self.current_series = selected
            if not self.save_result_from_preview(selected):
                return []
        return [
            series
            for series in self.series[selected_row:]
            if series.saved and series.output_active
        ][:15]

    def export_saved_pdf_from_preview(
        self,
        grouped: dict[str, list[ReportPoint]],
    ) -> bool:
        default_name = (
            f"{self.machine_name()}_report.pdf"
            if self.machine_name()
            else "report.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "PDFファイルを保存",
            str(Path("log") / default_name),
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not path:
            return False
        try:
            write_grouped_pdf(
                grouped,
                path,
                machine_name=self.machine_name(),
                show_mode_boundary=False,
            )
        except Exception as exc:
            show_error(self, "PDF出力エラー", exc)
            return False
        self.refresh_database_options()
        self.load_recent_saved_series()
        self.log(f"PDFを出力しました: {path}")
        self.update_save_button_state()
        self.update_series_buttons()
        return True

    def report_data_from_series_list(self, series_list: list[AnalysisSeries]) -> dict[str, list[ReportPoint]]:
        labels = self.current_preset_setup_labels()
        grouped: dict[str, list[ReportPoint]] = {label: [] for label in labels}
        for item in reversed(series_list):
            for point in self.series_report_points(item):
                if point.setup_label in grouped:
                    grouped[point.setup_label].append(point)
        grouped = {label: points for label, points in grouped.items() if points}
        if not grouped:
            raise ValueError("条件に一致する保存済み解析結果がありません。")
        return grouped

    def report_data_with_current_series(self, series: AnalysisSeries) -> dict[str, list[ReportPoint]]:
        if self.analysis_mode == "simple_test":
            return super().report_data_with_current_series(series)
        labels = self.current_preset_setup_labels()
        grouped: dict[str, list[ReportPoint]] = {label: [] for label in labels}
        for item in reversed(self.series[:10]):
            for point in self.series_report_points(item):
                if point.setup_label in grouped:
                    grouped[point.setup_label].append(point)
        grouped = {label: points for label, points in grouped.items() if points}
        if not grouped:
            raise ValueError("条件に一致する成功済み解析結果がありません。")
        return grouped

    def current_preset_setup_labels(self) -> list[str]:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            preset = get_setup_preset(connection, self.preset_combo.currentText())
            if preset is None:
                return []
            return [
                step["label"]
                for step in list_setup_steps(connection, int(preset["id"]))
            ]
        finally:
            connection.close()

    def series_report_points(self, series: AnalysisSeries) -> list[ReportPoint]:
        if series.points:
            return series.points
        points: list[ReportPoint] = []
        analyzed_at = series.started_at or datetime.now().isoformat(timespec="seconds")
        for plan_item, analysis in zip(series.plan, series.analyses):
            if not analysis.result.succeeded:
                continue
            label = plan_item.setup_label or plan_item.image_name
            result = analysis.result
            points.append(
                ReportPoint(
                    analyzed_at=analyzed_at,
                    image_name=plan_item.image_name,
                    setup_label=label,
                    dx_mm=float(result.dx_mm),
                    dy_mm=float(result.dy_mm),
                    distance_mm=float(result.distance_mm),
                    gantry_angle=plan_item.gantry_angle,
                    collimator_angle=plan_item.collimator_angle,
                    couch_angle=plan_item.couch_angle,
                    image_path=str(plan_item.image_path),
                    pixel_size_mm=result.parameters.pixel_size_mm,
                    beam_threshold=result.parameters.beam_threshold,
                    ball_sensitivity=result.parameters.ball_sensitivity,
                    beam_size_px=result.parameters.beam_size_px,
                    target_size_px=result.parameters.target_size_px,
                    x_axis_label=plan_item.x_axis_label or "",
                    y_axis_label=plan_item.y_axis_label or "",
                    dx_positive_label=plan_item.dx_positive_label or "+dx",
                    dx_negative_label=plan_item.dx_negative_label or "-dx",
                    dy_positive_label=plan_item.dy_positive_label or "+dy",
                    dy_negative_label=plan_item.dy_negative_label or "-dy",
                    x_inverted=plan_item.x_inverted,
                    inspection_type=series.inspection_type,
                )
            )
        return points

    def load_matching_history(
        self,
        plan_item: AnalysisPlanItem,
        machine_name: str | None,
        limit: int,
    ) -> list[ReportPoint]:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            rows = connection.execute(
                """
                SELECT
                    analysis_results.analyzed_at,
                    analysis_results.image_name,
                    analysis_results.image_path,
                    analysis_results.note AS setup_label,
                    analysis_results.dx_mm,
                    analysis_results.dy_mm,
                    analysis_results.distance_mm,
                    analysis_results.gantry_angle,
                    analysis_results.collimator_angle,
                    analysis_results.couch_angle,
                    analysis_results.pixel_size_mm,
                    analysis_results.beam_threshold,
                    analysis_results.ball_sensitivity,
                    analysis_results.beam_size_px,
                    analysis_results.target_size_px,
                    analysis_results.x_axis_label,
                    analysis_results.y_axis_label,
                    analysis_results.dx_positive_label,
                    analysis_results.dx_negative_label,
                    analysis_results.dy_positive_label,
                    analysis_results.dy_negative_label,
                    analysis_results.x_inverted,
                    sessions.inspection_type
                FROM analysis_results
                JOIN sessions ON sessions.id = analysis_results.session_id
                LEFT JOIN machines ON machines.id = sessions.machine_id
                WHERE analysis_results.succeeded = 1
                  AND sessions.inspection_type = 'daily'
                  AND (? IS NULL OR COALESCE(machines.name, sessions.machine_name) = ?)
                  AND ((? IS NULL AND analysis_results.gantry_angle IS NULL) OR ABS(analysis_results.gantry_angle - ?) < 0.000001)
                  AND ((? IS NULL AND analysis_results.collimator_angle IS NULL) OR ABS(analysis_results.collimator_angle - ?) < 0.000001)
                  AND ((? IS NULL AND analysis_results.couch_angle IS NULL) OR ABS(analysis_results.couch_angle - ?) < 0.000001)
                ORDER BY analysis_results.analyzed_at DESC, analysis_results.id DESC
                LIMIT ?
                """,
                (
                    machine_name,
                    machine_name,
                    plan_item.gantry_angle,
                    plan_item.gantry_angle,
                    plan_item.collimator_angle,
                    plan_item.collimator_angle,
                    plan_item.couch_angle,
                    plan_item.couch_angle,
                    limit,
                ),
            ).fetchall()
        finally:
            connection.close()
        return [report_point_from_row(row) for row in reversed(rows)]

    def current_temp_points(
        self,
        reference: AnalysisPlanItem,
        limit: int,
    ) -> list[ReportPoint]:
        points: list[ReportPoint] = []
        now = datetime.now().isoformat(timespec="seconds")
        for series in self.series:
            for plan_item, analysis in zip(series.plan, series.analyses):
                if not analysis.result.succeeded:
                    continue
                if not same_setup_angles(reference, plan_item):
                    continue
                result = analysis.result
                points.append(
                    ReportPoint(
                        analyzed_at=now,
                        image_name=plan_item.image_name,
                        setup_label=plan_item.setup_label or plan_item.image_name,
                        dx_mm=float(result.dx_mm),
                        dy_mm=float(result.dy_mm),
                        distance_mm=float(result.distance_mm),
                        gantry_angle=plan_item.gantry_angle,
                        collimator_angle=plan_item.collimator_angle,
                        couch_angle=plan_item.couch_angle,
                        image_path=str(plan_item.image_path),
                        pixel_size_mm=result.parameters.pixel_size_mm,
                        beam_threshold=result.parameters.beam_threshold,
                        ball_sensitivity=result.parameters.ball_sensitivity,
                        beam_size_px=result.parameters.beam_size_px,
                        target_size_px=result.parameters.target_size_px,
                        x_axis_label=plan_item.x_axis_label or "",
                        y_axis_label=plan_item.y_axis_label or "",
                        dx_positive_label=plan_item.dx_positive_label or "+dx",
                        dx_negative_label=plan_item.dx_negative_label or "-dx",
                        dy_positive_label=plan_item.dy_positive_label or "+dy",
                        dy_negative_label=plan_item.dy_negative_label or "-dy",
                        x_inverted=plan_item.x_inverted,
                        inspection_type=series.inspection_type,
                    )
                )
        return points[-limit:]

class ManageTab(QWidget):
    def __init__(self, on_changed) -> None:
        super().__init__()
        self.on_changed = on_changed
        self.preset_mode = "inactive"
        self.editing_preset_id: int | None = None
        self.setup_edit_row: int | None = None
        self.setup_edit_mode: str | None = None
        self.loading_setups = False
        layout = QHBoxLayout(self)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.build_machine_group())
        left_layout.addWidget(self.build_preset_group())
        left_layout.addWidget(self.build_judgement_group())
        left_layout.addStretch(1)
        layout.addWidget(left, stretch=3)
        layout.addWidget(self.build_setup_group(), stretch=7)
        self.refresh()

    def build_machine_group(self) -> QGroupBox:
        group = QGroupBox("Machines")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        self.machine_select = QComboBox()
        self.machine_select.currentTextChanged.connect(self.select_machine)
        self.machine_name = QLineEdit()
        self.machine_save_button = QPushButton("Register")
        self.machine_save_button.clicked.connect(self.save_machine)
        self.default_machine_select = QComboBox()
        self.default_machine_select.currentTextChanged.connect(self.default_machine_changed)
        layout.addWidget(self.machine_select)
        machine_fields = QHBoxLayout()
        machine_fields.setSpacing(6)
        name_label = QLabel("Name")
        name_label.setFixedWidth(44)
        machine_fields.addWidget(name_label)
        machine_fields.addWidget(self.machine_name, stretch=1)
        machine_fields.addWidget(self.machine_save_button)
        layout.addLayout(machine_fields)
        default_row = QHBoxLayout()
        default_row.setSpacing(6)
        default_label = QLabel("default:")
        default_label.setFixedWidth(54)
        default_row.addWidget(default_label)
        default_row.addWidget(self.default_machine_select, stretch=1)
        layout.addLayout(default_row)
        return group

    def build_setup_group(self) -> QGroupBox:
        group = QGroupBox("Setups")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        self.setup_table = QTableWidget(0, 13)
        self.setup_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Gantry",
                "Collimator",
                "Couch",
                "dx+",
                "dx-",
                "dy+",
                "dy-",
                "Field",
                "Target",
                "Pixel",
                "Beam th",
                "Ball sens",
            ]
        )
        setup_header = self.setup_table.horizontalHeader()
        for column, width in enumerate([150, 72, 86, 72, 54, 54, 54, 54, 68, 68, 72, 72, 72]):
            setup_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.setup_table.setColumnWidth(column, width)
        self.setup_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setup_table.itemChanged.connect(self.setup_item_changed)
        self.setup_table.currentCellChanged.connect(self.setup_current_cell_changed)
        layout.addWidget(self.setup_table, stretch=1)

        action_row = QHBoxLayout()
        action_row.setSpacing(6)
        self.add_setup_button = QPushButton("Add New Setup")
        self.add_setup_button.clicked.connect(self.add_setup_row)
        self.setup_save_button = QPushButton("Update")
        self.setup_save_button.clicked.connect(self.save_setup)
        self.param_test_button = QPushButton("Param Test")
        self.param_test_button.clicked.connect(self.param_test_setup)
        self.setup_exclude_button = QPushButton("Exclude")
        self.setup_exclude_button.clicked.connect(self.exclude_setup)
        action_row.addWidget(self.add_setup_button)
        action_row.addWidget(self.setup_save_button)
        action_row.addWidget(self.setup_exclude_button)
        action_row.addStretch()
        action_row.addWidget(self.param_test_button)
        layout.addLayout(action_row)
        return group

    def build_preset_group(self) -> QGroupBox:
        group = QGroupBox("Presets")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        preset_top = QHBoxLayout()
        preset_top.setSpacing(6)
        self.preset_select = QComboBox()
        self.preset_select.currentTextChanged.connect(self.update_preset_action_label)
        self.preset_edit_button = QPushButton("Register")
        self.preset_edit_button.clicked.connect(self.edit_selected_preset)
        self.default_preset_select = QComboBox()
        self.default_preset_select.currentTextChanged.connect(self.default_preset_changed)
        self.preset_select.setFixedHeight(self.preset_edit_button.sizeHint().height())
        preset_top.addWidget(self.preset_select, stretch=1)
        preset_top.addWidget(self.preset_edit_button)
        layout.addLayout(preset_top)
        default_row = QHBoxLayout()
        default_row.setSpacing(6)
        default_label = QLabel("default:")
        default_label.setFixedWidth(54)
        default_row.addWidget(default_label)
        default_row.addWidget(self.default_preset_select, stretch=1)
        layout.addLayout(default_row)
        layout.addStretch()
        return group

    def build_judgement_group(self) -> QGroupBox:
        group = QGroupBox("Judgement")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(6)
        label = QLabel("|dx|, |dy| <= mm")
        self.ok_threshold = QDoubleSpinBox()
        self.ok_threshold.setRange(0.01, 99.99)
        self.ok_threshold.setDecimals(2)
        self.ok_threshold.setSingleStep(0.1)
        self.ok_threshold.setValue(DEFAULT_OK_THRESHOLD_MM)
        self.ok_threshold.valueChanged.connect(self.ok_threshold_changed)
        row.addWidget(label)
        row.addWidget(self.ok_threshold, stretch=1)
        layout.addLayout(row)
        return group

    def refresh(self) -> None:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            machines = list_machines(connection)
            setups = list_setups(connection)
            presets = list_setup_presets(connection)
            default_machine = get_default_machine_name(connection)
            default_preset = get_setting(connection, DEFAULT_PRESET_SETTING) or ""
            ok_threshold = float(
                get_setting(connection, OK_THRESHOLD_SETTING)
                or get_setting(connection, LEGACY_OK_THRESHOLD_SETTING)
                or DEFAULT_OK_THRESHOLD_MM
            )
        finally:
            connection.close()

        current_machine = self.machine_select.currentText()
        self.machine_select.blockSignals(True)
        self.machine_select.clear()
        self.machine_select.addItem("New", None)
        for machine in machines:
            self.machine_select.addItem(machine["name"], int(machine["id"]))
        if current_machine and current_machine != "New":
            self.machine_select.setCurrentText(current_machine)
        else:
            self.machine_select.setCurrentText(default_machine)
        self.machine_select.blockSignals(False)
        self.default_machine_select.blockSignals(True)
        self.default_machine_select.clear()
        for machine in machines:
            self.default_machine_select.addItem(machine["name"], int(machine["id"]))
        self.default_machine_select.setCurrentText(default_machine)
        self.default_machine_select.blockSignals(False)
        self.select_machine()

        current_setup_row = self.setup_table.currentRow()
        self.clear_setup_edit_state()
        self.render_setup_table(setups)
        if self.setup_table.rowCount():
            self.setup_table.setCurrentCell(
                min(max(current_setup_row, 0), self.setup_table.rowCount() - 1),
                0,
            )

        current = self.preset_select.currentText()
        self.preset_select.blockSignals(True)
        self.preset_select.clear()
        self.preset_select.addItem("New")
        for preset in presets:
            self.preset_select.addItem(preset["name"])
        if current:
            self.preset_select.setCurrentText(current)
        self.preset_select.blockSignals(False)
        self.update_preset_action_label()
        self.default_preset_select.blockSignals(True)
        self.default_preset_select.clear()
        self.default_preset_select.addItem("")
        for preset in presets:
            self.default_preset_select.addItem(preset["name"])
        self.default_preset_select.setCurrentText(default_preset)
        self.default_preset_select.blockSignals(False)
        self.ok_threshold.blockSignals(True)
        self.ok_threshold.setValue(ok_threshold)
        self.ok_threshold.blockSignals(False)
        self.refresh_preset_setup_choices(setups)

    def select_machine(self, *_args) -> None:
        selected = self.machine_select.currentText()
        self.machine_name.clear() if selected == "New" else self.machine_name.setText(selected)
        self.machine_save_button.setText("Register" if selected == "New" else "Edit")

    def update_preset_action_label(self, *_args) -> None:
        self.preset_edit_button.setText("Register" if self.preset_select.currentText() == "New" else "Edit")

    def render_setup_table(self, setups) -> None:
        self.loading_setups = True
        self.setup_table.setRowCount(len(setups))
        for row, setup in enumerate(setups):
            values = [
                setup["name"],
                one_decimal_text(float(setup["gantry_angle"])),
                one_decimal_text(float(setup["collimator_angle"])),
                one_decimal_text(float(setup["couch_angle"])),
                setup["dx_positive_label"],
                setup["dx_negative_label"],
                setup["dy_positive_label"],
                setup["dy_negative_label"],
                optional_parameter_text(setup["field_size_px"]),
                optional_parameter_text(setup["target_size_px"]),
                value_text(float(setup["pixel_size_mm"])),
                str(int(setup["beam_threshold"])),
                str(int(setup["ball_sensitivity"])),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, int(setup["id"]))
                self.setup_table.setItem(row, column, item)
        self.loading_setups = False
        self.update_setup_row_locks()
        self.update_setup_buttons()

    def add_setup_row(self) -> None:
        if self.setup_edit_row is not None:
            show_error(self, "Setupエラー", ValueError("編集中のsetupを保存またはキャンセルしてください。"))
            return
        row = self.setup_table.rowCount()
        self.loading_setups = True
        self.setup_table.insertRow(row)
        values = ["", "0", "0", "0", "+dx", "-dx", "+dy", "-dy", "auto", "auto", "0.242", "0", "10"]
        for column, value in enumerate(values):
            self.setup_table.setItem(row, column, QTableWidgetItem(value))
        self.loading_setups = False
        self.setup_edit_row = row
        self.setup_edit_mode = "new"
        self.update_setup_row_locks()
        self.update_setup_buttons()
        self.setup_table.setCurrentCell(row, 0)

    def setup_item_changed(self, item: QTableWidgetItem) -> None:
        if self.loading_setups:
            return
        row = item.row()
        if self.setup_edit_row is None:
            self.setup_edit_row = row
            self.setup_edit_mode = "edit"
            self.update_setup_row_locks()
            self.update_setup_buttons()
            return
        if self.setup_edit_row != row:
            self.setup_table.setCurrentCell(self.setup_edit_row, 0)

    def setup_current_cell_changed(
        self,
        current_row: int,
        _current_column: int,
        _previous_row: int,
        _previous_column: int,
    ) -> None:
        if self.setup_edit_row is not None and current_row != self.setup_edit_row:
            self.setup_table.setCurrentCell(self.setup_edit_row, 0)
            return
        self.update_setup_buttons()

    def clear_setup_edit_state(self) -> None:
        self.setup_edit_row = None
        self.setup_edit_mode = None

    def update_setup_row_locks(self) -> None:
        active_row = self.setup_edit_row
        previous_loading = self.loading_setups
        self.loading_setups = True
        try:
            for row in range(self.setup_table.rowCount()):
                row_enabled = active_row is None or row == active_row
                for column in range(self.setup_table.columnCount()):
                    item = self.setup_table.item(row, column)
                    if item is None:
                        continue
                    flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled
                    if not row_enabled:
                        flags = Qt.ItemFlag.NoItemFlags
                        item.setBackground(QColor("#eeeeee"))
                    elif active_row == row:
                        item.setBackground(QColor("#fff4c2" if self.setup_edit_mode == "edit" else "#dff0ff"))
                    else:
                        item.setBackground(QColor("white"))
                    item.setFlags(flags)
        finally:
            self.loading_setups = previous_loading

    def update_setup_buttons(self) -> None:
        editing = self.setup_edit_row is not None
        has_row = self.setup_table.currentRow() >= 0
        self.add_setup_button.setEnabled(not editing)
        self.setup_save_button.setEnabled(editing or has_row)
        self.setup_save_button.setText("Register" if self.setup_edit_mode == "new" else "Update")
        self.setup_exclude_button.setText("Cancel" if editing else "Delete")

    def setup_from_table_row(self, row: int) -> AnalysisSetup | None:
        if row < 0:
            return None
        name = table_text(self.setup_table, row, 0).strip()
        if not name:
            raise_error(self, "Setupエラー", "setup nameを入力してください。")
            return None
        try:
            return AnalysisSetup(
                name=name,
                gantry_angle=float(table_text(self.setup_table, row, 1) or 0),
                collimator_angle=float(table_text(self.setup_table, row, 2) or 0),
                couch_angle=float(table_text(self.setup_table, row, 3) or 0),
                dx_positive_label=table_text(self.setup_table, row, 4).strip() or "+dx",
                dx_negative_label=table_text(self.setup_table, row, 5).strip() or "-dx",
                dy_positive_label=table_text(self.setup_table, row, 6).strip() or "+dy",
                dy_negative_label=table_text(self.setup_table, row, 7).strip() or "-dy",
                field_size_px=optional_int_text(table_text(self.setup_table, row, 8)),
                target_size_px=optional_int_text(table_text(self.setup_table, row, 9)),
                pixel_size_mm=float(table_text(self.setup_table, row, 10) or 0.242),
                beam_threshold=int(float(table_text(self.setup_table, row, 11) or 0)),
                ball_sensitivity=int(float(table_text(self.setup_table, row, 12) or 10)),
            )
        except ValueError as exc:
            show_error(self, "Setupエラー", ValueError(f"{row + 1}行目の数値を確認してください。\n{exc}"))
            return None

    def save_setup(self) -> None:
        row = self.setup_table.currentRow()
        setup = self.setup_from_table_row(row)
        if setup is None:
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            id_item = self.setup_table.item(row, 0)
            setup_id = id_item.data(Qt.ItemDataRole.UserRole) if id_item is not None else None
            if self.setup_edit_mode == "edit" and setup_id is not None:
                update_setup_by_id(connection, int(setup_id), setup)
            else:
                upsert_setup(connection, setup)
            connection.commit()
        finally:
            connection.close()
        self.refresh()
        self.select_setup_row(setup.name)
        self.on_changed()

    def exclude_setup(self) -> None:
        if self.setup_edit_row is not None:
            self.cancel_setup_edit()
            return
        row = self.setup_table.currentRow()
        setup_name = table_text(self.setup_table, row, 0).strip()
        if not setup_name:
            show_error(self, "Setupエラー", ValueError("除外するsetupを選択してください。"))
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            setup = get_setup(connection, setup_name)
            if setup is None:
                raise ValueError("登録済みsetupを選択してください。")
            deactivate_setup(connection, int(setup["id"]))
            connection.commit()
        finally:
            connection.close()
        self.refresh()
        self.on_changed()

    def cancel_setup_edit(self) -> None:
        if self.setup_edit_mode == "new" and self.setup_edit_row is not None:
            self.loading_setups = True
            self.setup_table.removeRow(self.setup_edit_row)
            self.loading_setups = False
            self.clear_setup_edit_state()
            self.update_setup_row_locks()
            self.update_setup_buttons()
            return
        self.clear_setup_edit_state()
        self.refresh()

    def param_test_setup(self) -> None:
        row = self.setup_table.currentRow()
        setup = self.setup_from_table_row(row)
        if setup is None:
            return
        dialog = ParamTestDialog(setup, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        parameters = dialog.parameters()
        values = [
            optional_parameter_text(parameters.beam_size_px),
            optional_parameter_text(parameters.target_size_px),
            value_text(parameters.pixel_size_mm),
            str(parameters.beam_threshold),
            str(parameters.ball_sensitivity),
        ]
        for offset, value in enumerate(values, start=8):
            self.setup_table.setItem(row, offset, QTableWidgetItem(value))

    def select_setup_row(self, name: str) -> None:
        for row in range(self.setup_table.rowCount()):
            if table_text(self.setup_table, row, 0) == name:
                self.setup_table.setCurrentCell(row, 0)
                return

    def refresh_preset_setup_choices(self, setups) -> None:
        if not hasattr(self, "step_table"):
            return
        checked = set(self.checked_preset_setup_names())
        self.step_table.setRowCount(len(setups))
        for row, setup in enumerate(setups):
            use_item = QTableWidgetItem()
            use_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            use_item.setCheckState(
                Qt.CheckState.Checked if setup["name"] in checked else Qt.CheckState.Unchecked
            )
            self.step_table.setItem(row, 0, use_item)
            name_item = QTableWidgetItem(setup["name"])
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.step_table.setItem(row, 1, name_item)

    def checked_preset_setup_names(self) -> list[str]:
        names: list[str] = []
        for row in range(self.step_table.rowCount()):
            item = self.step_table.item(row, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                names.append(table_text(self.step_table, row, 1))
        return names

    def set_preset_checked_names(self, names: list[str]) -> None:
        checked = set(names)
        for row in range(self.step_table.rowCount()):
            item = self.step_table.item(row, 0)
            if item is not None:
                item.setCheckState(
                    Qt.CheckState.Checked
                    if table_text(self.step_table, row, 1) in checked
                    else Qt.CheckState.Unchecked
                )

    def save_machine(self) -> None:
        name = self.machine_name.text().strip()
        if not name:
            show_error(self, "装置エラー", ValueError("装置名を入力してください。"))
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            selected = self.machine_select.currentText()
            selected_id = self.machine_select.currentData()
            if selected_id is not None:
                default_machine = get_default_machine_name(connection)
                connection.execute(
                    """
                    UPDATE machines
                    SET name = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (name, datetime.now().isoformat(timespec="seconds"), int(selected_id)),
                )
                if default_machine == selected:
                    set_default_machine_name(connection, name)
            else:
                get_or_create_machine(connection, name)
            connection.commit()
        finally:
            connection.close()
        self.refresh()
        self.machine_select.setCurrentText(name)
        self.select_machine()
        self.on_changed()

    def save_default_machine(self) -> None:
        name = self.machine_name.text().strip() or self.machine_select.currentText().strip()
        if name == "New":
            name = ""
        if not name:
            show_error(self, "装置エラー", ValueError("デフォルト装置を指定してください。"))
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            set_default_machine_name(connection, name)
            connection.commit()
        finally:
            connection.close()
        self.refresh()
        self.on_changed()

    def default_machine_changed(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            set_default_machine_name(connection, name)
            connection.commit()
        finally:
            connection.close()
        self.on_changed()

    def default_preset_changed(self, name: str) -> None:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            set_setting(connection, DEFAULT_PRESET_SETTING, name.strip())
            connection.commit()
        finally:
            connection.close()
        self.on_changed()

    def ok_threshold_changed(self, value: float) -> None:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            set_setting(connection, OK_THRESHOLD_SETTING, f"{value:.2f}")
            connection.commit()
        finally:
            connection.close()
        self.on_changed()

    def edit_selected_preset(self, *_args) -> None:
        name = self.preset_select.currentText()
        if not name:
            return
        setup_rows: list
        if name == "New":
            connection = connect_database(DEFAULT_DB_PATH)
            try:
                init_db(connection)
                setup_rows = list_setups(connection)
            finally:
                connection.close()
            dialog = PresetEditorDialog(
                setup_rows=setup_rows,
                preset_id=None,
                preset_name="",
                preset_setup_names=[],
                parent=self,
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh()
                self.on_changed()
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            preset = get_setup_preset(connection, name)
            if preset is None:
                return
            preset_id = int(preset["id"])
            steps = list_setup_steps(connection, int(preset["id"]))
            setup_rows = list_setups(connection)
        finally:
            connection.close()
        dialog = PresetEditorDialog(
            setup_rows=setup_rows,
            preset_id=preset_id,
            preset_name=name,
            preset_setup_names=[step["label"] for step in steps],
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.on_changed()

    def new_preset(self) -> None:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            setup_rows = list_setups(connection)
        finally:
            connection.close()
        dialog = PresetEditorDialog(
            setup_rows=setup_rows,
            preset_id=None,
            preset_name="",
            preset_setup_names=[],
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.on_changed()

    def set_preset_editor_enabled(self, enabled: bool) -> None:
        self.preset_editor_group.setEnabled(enabled)
        self.preset_name.setEnabled(enabled)
        if hasattr(self, "preset_update_button"):
            self.preset_update_button.setEnabled(enabled and self.preset_mode == "edit")

    def update_preset(self) -> None:
        if self.preset_mode == "inactive":
            return
        self.save_preset(save_as_new=False)

    def save_as_new_preset(self) -> None:
        if self.preset_mode == "inactive":
            return
        self.save_preset(save_as_new=True)

    def cancel_preset_edit(self) -> None:
        self.preset_mode = "inactive"
        self.editing_preset_id = None
        self.preset_mode_label.setText("Mode: inactive")
        self.preset_name.clear()
        self.set_preset_checked_names([])
        self.set_preset_editor_enabled(False)

    def save_preset(self, save_as_new: bool) -> None:
        name = self.preset_name.text().strip()
        if not name:
            show_error(self, "プリセットエラー", ValueError("プリセット名を入力してください。"))
            return
        setups: list[AnalysisSetup] = []
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            setup_rows = list_setups(connection)
        finally:
            connection.close()
        library = {
            row["name"]: AnalysisSetup(
                name=row["name"],
                gantry_angle=float(row["gantry_angle"]),
                collimator_angle=float(row["collimator_angle"]),
                couch_angle=float(row["couch_angle"]),
                dx_positive_label=row["dx_positive_label"],
                dx_negative_label=row["dx_negative_label"],
                dy_positive_label=row["dy_positive_label"],
                dy_negative_label=row["dy_negative_label"],
                field_size_px=row["field_size_px"],
                target_size_px=row["target_size_px"],
                pixel_size_mm=float(row["pixel_size_mm"]),
                beam_threshold=int(row["beam_threshold"]),
                ball_sensitivity=int(row["ball_sensitivity"]),
            )
            for row in setup_rows
        }
        for label in self.checked_preset_setup_names():
            setup = library.get(label)
            if setup is None:
                show_error(
                    self,
                    "プリセットエラー",
                    ValueError(f"{label}: 登録済みsetupから選択してください。"),
                )
                return
            setups.append(setup)
        if not setups:
            show_error(self, "プリセットエラー", ValueError("条件行を1つ以上入力してください。"))
            return
        duplicate_labels = duplicated_setup_labels(setups)
        if duplicate_labels:
            show_error(
                self,
                "プリセットエラー",
                ValueError(
                    "1つのpreset内でsetup labelは重複できません。\n"
                    f"重複: {', '.join(duplicate_labels)}\n"
                    "Labelを修正してから保存してください。"
                ),
            )
            return

        preset = SetupPreset(name, "", tuple(setups))
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            if self.preset_mode == "edit" and not save_as_new and self.editing_preset_id is not None:
                update_setup_preset_by_id(connection, self.editing_preset_id, preset)
            else:
                if save_as_new and get_setup_preset(connection, name) is not None:
                    show_error(
                        self,
                        "プリセットエラー",
                        ValueError("同じプリセット名がすでに存在します。別の名前を使用してください。"),
                    )
                    return
                upsert_setup_preset(connection, preset, is_builtin=False)
            connection.commit()
        finally:
            connection.close()
        self.refresh()
        self.preset_mode = "inactive"
        self.editing_preset_id = None
        self.preset_mode_label.setText("Mode: inactive")
        self.set_preset_editor_enabled(False)
        self.on_changed()


class HistoryTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, str]] = []
        self.sessions: list[dict[str, str | int]] = []
        layout = QVBoxLayout(self)

        filters = QHBoxLayout()
        filters.setSpacing(12)
        self.machine_filter = QComboBox()
        self.machine_filter.addItem("")
        self.machine_filter.setMinimumWidth(180)
        self.machine_filter.setMaximumWidth(260)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setMinimumWidth(120)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setMinimumWidth(120)
        self.end_date.setDate(QDate.currentDate())
        filters.addWidget(compact_field("Machine", self.machine_filter))
        filters.addWidget(compact_field("From", self.start_date))
        filters.addWidget(compact_field("To", self.end_date))
        query_button = QPushButton("Query")
        query_button.clicked.connect(self.query)
        delete_button = QPushButton("Delete Series")
        delete_button.clicked.connect(self.delete_selected_series)
        export_button = QPushButton("Export CSV")
        export_button.clicked.connect(self.export_csv)
        filters.addWidget(query_button)
        filters.addWidget(delete_button)
        filters.addWidget(export_button)
        filters.addStretch()
        layout.addLayout(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        series_group = QGroupBox("Series")
        series_layout = QVBoxLayout(series_group)
        self.series_list = QListWidget()
        self.series_list.currentRowChanged.connect(self.update_detail_table)
        series_layout.addWidget(self.series_list)
        splitter.addWidget(series_group)

        self.detail_table = QTableWidget(0, 11)
        self.detail_table.setHorizontalHeaderLabels(
            ["Image", "Setup", "Status", "dx", "dy", "Distance", "Gantry", "Collimator", "Couch", "Machine", "Inspection"]
        )
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.detail_table.horizontalHeader().setStretchLastSection(True)
        self.detail_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        detail_group = QGroupBox("Series Results")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.addWidget(self.detail_table)
        splitter.addWidget(detail_group)
        splitter.setSizes([240, 860])
        layout.addWidget(splitter, stretch=1)
        self.refresh_options()
        self.query()

    def refresh_options(self) -> None:
        current = self.machine_filter.currentText() if hasattr(self, "machine_filter") else ""
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            machines = list_machines(connection)
        finally:
            connection.close()
        self.machine_filter.blockSignals(True)
        self.machine_filter.clear()
        self.machine_filter.addItem("")
        for machine in machines:
            self.machine_filter.addItem(machine["name"])
        self.machine_filter.setCurrentText(current)
        self.machine_filter.blockSignals(False)

    def query(self) -> None:
        machine = self.machine_filter.currentText().strip() or None
        start = self.start_date.date().toString("yyyy-MM-dd") + "T00:00:00"
        end = self.end_date.date().toString("yyyy-MM-dd") + "T23:59:59"
        sql = """
            SELECT
                sessions.id AS session_id,
                sessions.started_at AS series_name,
                analysis_results.analyzed_at,
                COALESCE(machines.name, sessions.machine_name, '') AS machine,
                sessions.inspection_type,
                analysis_results.image_name,
                analysis_results.note AS setup_label,
                analysis_results.dx_mm,
                analysis_results.dy_mm,
                analysis_results.distance_mm,
                analysis_results.gantry_angle,
                analysis_results.collimator_angle,
                analysis_results.couch_angle,
                analysis_results.succeeded
            FROM analysis_results
            JOIN sessions ON sessions.id = analysis_results.session_id
            LEFT JOIN machines ON machines.id = sessions.machine_id
            WHERE (? IS NULL OR COALESCE(machines.name, sessions.machine_name) = ?)
              AND sessions.started_at >= ?
              AND sessions.started_at <= ?
            ORDER BY sessions.started_at DESC, analysis_results.id ASC
            LIMIT 500
        """
        params = (
            machine,
            machine,
            start,
            end,
        )
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            rows = connection.execute(sql, params).fetchall()
        finally:
            connection.close()
        self.rows = [history_row_dict(row) for row in rows]
        self.sessions = unique_sessions(self.rows)
        self.render_series_list()
        self.update_detail_table()

    def render_series_list(self) -> None:
        current_row = self.series_list.currentRow()
        self.series_list.blockSignals(True)
        self.series_list.clear()
        for session in self.sessions:
            label = (
                f"{short_series_name(str(session['series_name']))}  "
                f"{session['machine'] or '-'}  {session['inspection_type'] or '-'}"
            )
            self.series_list.addItem(label)
        self.series_list.blockSignals(False)
        if self.sessions:
            self.series_list.setCurrentRow(min(max(current_row, 0), len(self.sessions) - 1))
        else:
            self.detail_table.setRowCount(0)

    def update_detail_table(self) -> None:
        session_id = self.selected_session_id()
        if session_id is None:
            self.detail_table.setRowCount(0)
            return
        details = [row for row in self.rows if int(row["session_id"]) == session_id]
        self.detail_table.setRowCount(len(details))
        keys = [
            "image_name",
            "setup_label",
            "status",
            "dx_mm",
            "dy_mm",
            "distance_mm",
            "gantry_angle",
            "collimator_angle",
            "couch_angle",
            "machine",
            "inspection_type",
        ]
        for row_index, detail in enumerate(details):
            for column, key in enumerate(keys):
                self.detail_table.setItem(row_index, column, QTableWidgetItem(detail[key]))
        self.detail_table.resizeColumnsToContents()

    def selected_session_id(self) -> int | None:
        row = self.series_list.currentRow()
        if row < 0 or row >= len(self.sessions):
            return None
        return int(self.sessions[row]["session_id"])

    def delete_selected_series(self) -> None:
        session_id = self.selected_session_id()
        if session_id is None:
            show_error(self, "履歴エラー", ValueError("シリーズを選択してください。"))
            return
        reply = QMessageBox.question(
            self,
            "シリーズ削除",
            "選択したシリーズと解析結果を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            delete_session_results(connection, session_id)
            connection.commit()
        finally:
            connection.close()
        self.query()

    def export_csv(self) -> None:
        if not self.rows:
            show_error(self, "CSV出力エラー", ValueError("出力する行がありません。"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export CSV",
            str(Path("log") / "analysis_results.csv"),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(self.rows[0].keys()))
            writer.writeheader()
            writer.writerows(self.rows)


class PagePreviewDialog(QDialog):
    def __init__(
        self,
        title: str,
        pages: list[QPixmap],
        outline_titles: list[str] | None = None,
        parent: QWidget | None = None,
        save_result_handler: Callable[[], bool] | None = None,
        export_pdf_handler: Callable[[], bool] | None = None,
        show_save_result_button: bool = True,
    ) -> None:
        super().__init__(parent)
        self.pages = pages
        self.page_widgets: list[QLabel] = []
        self.save_result_handler = save_result_handler
        self.export_pdf_handler = export_pdf_handler

        self.setWindowTitle(title)
        self.resize(900, 760)

        layout = QVBoxLayout(self)
        preview_layout = QHBoxLayout()

        self.outline_list = QListWidget()
        self.outline_list.setFixedWidth(190)
        self.outline_list.currentRowChanged.connect(self.scroll_to_page)
        preview_layout.addWidget(self.outline_list)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(18)

        if not pages:
            empty_label = QLabel("プレビューページがありません")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(empty_label)
        else:
            for index, page in enumerate(pages, start=1):
                outline = outline_titles[index - 1] if outline_titles and index - 1 < len(outline_titles) else ""
                outline_text = f"{index}. {outline}" if outline else f"Page {index}"
                self.outline_list.addItem(outline_text)

                page_count = QLabel(f"Page {index} / {len(pages)}  {outline}")
                page_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
                content_layout.addWidget(page_count)

                page_label = QLabel()
                page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.page_widgets.append(page_label)

                row = QHBoxLayout()
                row.addStretch()
                row.addWidget(page_label)
                row.addStretch()
                content_layout.addLayout(row)

        content_layout.addStretch()
        self.scroll_area.setWidget(content)
        preview_layout.addWidget(self.scroll_area, stretch=1)
        layout.addLayout(preview_layout, stretch=1)

        button_row = QHBoxLayout()
        self.previous_page_button = QPushButton("Previous Page")
        self.previous_page_button.clicked.connect(self.previous_page)
        self.next_page_button = QPushButton("Next Page")
        self.next_page_button.clicked.connect(self.next_page)
        self.save_result_button = QPushButton("Save")
        self.save_result_button.setEnabled(self.save_result_handler is not None)
        self.save_result_button.setVisible(show_save_result_button)
        self.save_result_button.clicked.connect(self.save_result)
        self.export_pdf_button = QPushButton("Export PDF")
        self.export_pdf_button.setEnabled(self.export_pdf_handler is not None)
        self.export_pdf_button.clicked.connect(self.export_pdf)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.previous_page_button)
        button_row.addWidget(self.next_page_button)
        button_row.addStretch()
        if show_save_result_button:
            button_row.addWidget(self.save_result_button)
        button_row.addWidget(self.export_pdf_button)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)
        if pages:
            self.outline_list.setCurrentRow(0)
            QTimer.singleShot(0, self.update_page_sizes)
        self.update_page_buttons()

    def scroll_to_page(self, row: int) -> None:
        if row < 0 or row >= len(self.page_widgets):
            return
        self.scroll_area.ensureWidgetVisible(self.page_widgets[row], 0, 12)
        self.update_page_buttons()

    def previous_page(self) -> None:
        row = self.outline_list.currentRow()
        if row > 0:
            self.outline_list.setCurrentRow(row - 1)

    def next_page(self) -> None:
        row = self.outline_list.currentRow()
        if row < len(self.page_widgets) - 1:
            self.outline_list.setCurrentRow(row + 1)

    def update_page_buttons(self) -> None:
        row = self.outline_list.currentRow()
        has_pages = bool(self.page_widgets)
        self.previous_page_button.setEnabled(has_pages and row > 0)
        self.next_page_button.setEnabled(has_pages and row < len(self.page_widgets) - 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_page_sizes()

    def update_page_sizes(self) -> None:
        if not self.pages:
            return
        available_width = max(120, self.scroll_area.viewport().width() - 32)
        for page, label in zip(self.pages, self.page_widgets):
            if page.width() > available_width:
                scaled = page.scaledToWidth(
                    available_width,
                    Qt.TransformationMode.SmoothTransformation,
                )
            else:
                scaled = page
            label.setPixmap(scaled)
            label.setFixedSize(scaled.size())

    def save_result(self) -> None:
        if self.save_result_handler is None:
            return
        if self.save_result_handler():
            self.save_result_button.setEnabled(False)

    def export_pdf(self) -> None:
        if self.export_pdf_handler is None:
            return
        self.export_pdf_handler()


class PresetEditorDialog(QDialog):
    def __init__(
        self,
        setup_rows: list,
        preset_id: int | None,
        preset_name: str,
        preset_setup_names: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setup_rows = setup_rows
        self.preset_id = preset_id
        self.setup_library = {
            row["name"]: analysis_setup_from_row(row)
            for row in setup_rows
        }

        self.setWindowTitle("Preset Editor")
        self.resize(760, 560)
        layout = QVBoxLayout(self)

        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(8)

        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Registered Setups"))
        self.available_list = QListWidget()
        for row in setup_rows:
            item = QListWidgetItem(row["name"])
            item.setData(Qt.ItemDataRole.UserRole, row["name"])
            self.available_list.addItem(item)
        left_panel.addWidget(self.available_list)
        lists_layout.addLayout(left_panel, stretch=1)

        move_buttons = QVBoxLayout()
        move_buttons.addStretch()
        add_button = QPushButton("->")
        add_button.clicked.connect(self.add_selected_setups)
        remove_button = QPushButton("<-")
        remove_button.clicked.connect(self.remove_selected_setups)
        move_buttons.addWidget(add_button)
        move_buttons.addWidget(remove_button)
        move_buttons.addStretch()
        lists_layout.addLayout(move_buttons)

        right_panel = QVBoxLayout()
        self.preset_name = QLineEdit(preset_name)
        right_panel.addWidget(compact_field("Preset Name", self.preset_name))
        right_panel.addWidget(QLabel("Preset Setups"))
        self.preset_list = QListWidget()
        for setup_name in preset_setup_names:
            self.add_preset_setup(setup_name)
        right_panel.addWidget(self.preset_list)

        action_row = QHBoxLayout()
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.preset_list.clear)
        up_button = QPushButton("↑")
        up_button.clicked.connect(self.move_selected_up)
        down_button = QPushButton("↓")
        down_button.clicked.connect(self.move_selected_down)
        self.update_button = QPushButton("Update")
        self.update_button.setEnabled(self.preset_id is not None)
        self.update_button.clicked.connect(lambda: self.save_preset(save_as_new=False))
        save_as_new_button = QPushButton("Save as New Preset")
        save_as_new_button.clicked.connect(lambda: self.save_preset(save_as_new=True))
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        for button in [clear_button, up_button, down_button, self.update_button, save_as_new_button, cancel_button]:
            action_row.addWidget(button)
        right_panel.addLayout(action_row)
        lists_layout.addLayout(right_panel, stretch=1)

        layout.addLayout(lists_layout, stretch=1)

    def add_preset_setup(self, setup_name: str) -> None:
        if setup_name not in self.setup_library:
            return
        if setup_name in self.preset_setup_names():
            return
        item = QListWidgetItem(setup_name)
        item.setData(Qt.ItemDataRole.UserRole, setup_name)
        self.preset_list.addItem(item)

    def add_selected_setups(self) -> None:
        for item in self.available_list.selectedItems():
            self.add_preset_setup(str(item.data(Qt.ItemDataRole.UserRole)))

    def remove_selected_setups(self) -> None:
        for item in self.preset_list.selectedItems():
            self.preset_list.takeItem(self.preset_list.row(item))

    def move_selected_up(self) -> None:
        self.move_selected_preset_row(-1)

    def move_selected_down(self) -> None:
        self.move_selected_preset_row(1)

    def move_selected_preset_row(self, offset: int) -> None:
        row = self.preset_list.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.preset_list.count():
            return
        item = self.preset_list.takeItem(row)
        self.preset_list.insertItem(target, item)
        self.preset_list.setCurrentRow(target)

    def preset_setup_names(self) -> list[str]:
        return [
            str(self.preset_list.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.preset_list.count())
        ]

    def save_preset(self, save_as_new: bool) -> None:
        name = self.preset_name.text().strip()
        if not name:
            show_error(self, "プリセットエラー", ValueError("プリセット名を入力してください。"))
            return
        setup_names = self.preset_setup_names()
        if not setup_names:
            show_error(self, "プリセットエラー", ValueError("Setupを1つ以上登録してください。"))
            return
        setups = [self.setup_library[setup_name] for setup_name in setup_names]
        preset = SetupPreset(name, "", tuple(setups))

        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            if save_as_new:
                if get_setup_preset(connection, name) is not None:
                    show_error(
                        self,
                        "プリセットエラー",
                        ValueError("同じプリセット名がすでに存在します。別の名前を使用してください。"),
                    )
                    return
                upsert_setup_preset(connection, preset, is_builtin=False)
            else:
                if self.preset_id is None:
                    show_error(self, "プリセットエラー", ValueError("新規presetはSave as New Presetで保存してください。"))
                    return
                update_setup_preset_by_id(connection, self.preset_id, preset)
            connection.commit()
        finally:
            connection.close()
        self.accept()


class ParamTestDialog(QDialog):
    def __init__(self, setup: AnalysisSetup, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Param Test - {setup.name}")
        self.resize(860, 680)
        self.last_overlay_pixmap: QPixmap | None = None
        self.reanalyze_timer = QTimer(self)
        self.reanalyze_timer.setSingleShot(True)
        self.reanalyze_timer.timeout.connect(self.reanalyze)

        layout = QVBoxLayout(self)

        image_row = QHBoxLayout()
        self.image_path = QLineEdit()
        self.image_path.setPlaceholderText("解析対象画像を選択してください")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_image)
        image_row.addWidget(compact_field("Image", self.image_path), stretch=1)
        image_row.addWidget(browse_button)
        layout.addLayout(image_row)

        controls = QGroupBox("Parameters")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(8, 6, 8, 6)
        controls_layout.setHorizontalSpacing(10)
        controls_layout.setVerticalSpacing(6)

        self.field_size = QSpinBox()
        self.field_size.setRange(0, 2000)
        self.field_size.setSpecialValueText("auto")
        self.field_size.setValue(setup.field_size_px or 0)
        self.target_size = QSpinBox()
        self.target_size.setRange(0, 200)
        self.target_size.setSpecialValueText("auto")
        self.target_size.setValue(setup.target_size_px or 0)
        self.pixel_size = QDoubleSpinBox()
        self.pixel_size.setDecimals(4)
        self.pixel_size.setRange(0.0001, 10.0)
        self.pixel_size.setValue(setup.pixel_size_mm)
        self.beam_threshold = QSpinBox()
        self.beam_threshold.setRange(0, 255)
        self.beam_threshold.setSpecialValueText("otsu")
        self.beam_threshold.setValue(setup.beam_threshold)
        self.ball_sensitivity = QSpinBox()
        self.ball_sensitivity.setRange(1, 100)
        self.ball_sensitivity.setValue(setup.ball_sensitivity)
        for widget in [
            self.field_size,
            self.target_size,
            self.pixel_size,
            self.beam_threshold,
            self.ball_sensitivity,
        ]:
            widget.valueChanged.connect(self.schedule_reanalyze)

        controls_layout.addWidget(compact_field("Field", self.field_size), 0, 0)
        controls_layout.addWidget(compact_field("Target", self.target_size), 0, 1)
        controls_layout.addWidget(compact_field("Pixel", self.pixel_size), 0, 2)
        controls_layout.addWidget(compact_field("Beam th", self.beam_threshold), 1, 0)
        controls_layout.addWidget(compact_field("Ball sens", self.ball_sensitivity), 1, 1)
        analyze_button = QPushButton("Analyze")
        analyze_button.clicked.connect(self.reanalyze)
        controls_layout.addWidget(analyze_button, 1, 2)
        layout.addWidget(controls)

        self.status_label = QLabel("画像を選択して Analyze を押してください")
        layout.addWidget(self.status_label)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(420, 360)
        self.preview.setStyleSheet("background: #111; color: #ddd;")
        layout.addWidget(self.preview, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText("Apply")
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Close")
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.reject)
        layout.addWidget(buttons)

    def parameters(self) -> AnalysisParameters:
        return AnalysisParameters(
            beam_threshold=self.beam_threshold.value(),
            ball_sensitivity=self.ball_sensitivity.value(),
            pixel_size_mm=self.pixel_size.value(),
            beam_size_px=optional_spin_value(self.field_size),
            target_size_px=optional_spin_value(self.target_size),
        )

    def browse_image(self) -> None:
        start = load_app_setting(INPUT_PATH_SETTING, str(Path("sample")))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "解析対象画像",
            start,
            "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;All Files (*)",
        )
        if path:
            self.image_path.setText(path)
            self.reanalyze()

    def reanalyze(self) -> None:
        path = self.image_path.text().strip()
        if not path:
            self.status_label.setText("画像を選択してください")
            return
        try:
            analysis = analyze_image(Path(path), self.parameters())
        except Exception as exc:
            self.preview.clear()
            self.preview.setText("解析に失敗しました")
            self.status_label.setText(str(exc))
            return
        result = analysis.result
        self.status_label.setText(
            f"dx={result.dx_mm:.3f} mm  dy={result.dy_mm:.3f} mm  "
            f"distance={result.distance_mm:.3f} mm"
        )
        self.last_overlay_pixmap = pixmap_from_bgr(analysis.debug_images.focused_overlay)
        self.update_preview_pixmap()

    def schedule_reanalyze(self, *_args) -> None:
        if self.image_path.text().strip():
            self.reanalyze_timer.start(250)

    def update_preview_pixmap(self) -> None:
        if self.last_overlay_pixmap is None:
            return
        self.preview.setPixmap(
            self.last_overlay_pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_preview_pixmap()


class ManualTuningDialog(QDialog):
    def __init__(
        self,
        plan: list[AnalysisPlanItem],
        start_row: int,
        parameters: AnalysisParameters,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.plan = plan
        self.current_row = max(0, min(start_row, len(plan) - 1))
        self.current_analysis: Analysis | None = None

        self.setWindowTitle("Manual Tuning")
        self.resize(900, 720)
        layout = QVBoxLayout(self)

        controls = QGroupBox("Parameters")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setHorizontalSpacing(16)
        controls_layout.setVerticalSpacing(8)
        self.pixel_size = QDoubleSpinBox()
        self.pixel_size.setDecimals(4)
        self.pixel_size.setRange(0.0001, 10.0)
        self.pixel_size.setSingleStep(0.001)
        self.pixel_size.setValue(parameters.pixel_size_mm)
        self.pixel_size.setMinimumWidth(100)

        self.beam_threshold = QSpinBox()
        self.beam_threshold.setRange(0, 255)
        self.beam_threshold.setSpecialValueText("otsu")
        self.beam_threshold.setValue(parameters.beam_threshold)
        self.beam_threshold.setMinimumWidth(90)

        self.ball_sensitivity = QSpinBox()
        self.ball_sensitivity.setRange(1, 100)
        self.ball_sensitivity.setValue(parameters.ball_sensitivity)
        self.ball_sensitivity.setMinimumWidth(90)

        self.beam_size = QSpinBox()
        self.beam_size.setRange(0, 2000)
        self.beam_size.setSpecialValueText("auto")
        self.beam_size.setValue(parameters.beam_size_px or 0)
        self.beam_size.setMinimumWidth(90)

        self.target_size = QSpinBox()
        self.target_size.setRange(0, 200)
        self.target_size.setSpecialValueText("auto")
        self.target_size.setValue(parameters.target_size_px or 0)
        self.target_size.setMinimumWidth(90)

        controls_layout.addWidget(compact_field("Pixel mm", self.pixel_size), 0, 0)
        controls_layout.addWidget(compact_field("Field px", self.beam_size), 0, 1)
        controls_layout.addWidget(compact_field("Target px", self.target_size), 0, 2)
        controls_layout.addWidget(compact_field("Beam threshold", self.beam_threshold), 1, 0)
        controls_layout.addWidget(compact_field("Ball sensitivity", self.ball_sensitivity), 1, 1)
        reanalyze_button = QPushButton("Reanalyze")
        reanalyze_button.clicked.connect(self.reanalyze)
        controls_layout.addWidget(reanalyze_button, 1, 2)
        layout.addWidget(controls)

        image_row = QHBoxLayout()
        self.previous_image_button = QPushButton("Previous")
        self.previous_image_button.clicked.connect(self.previous_image)
        self.next_image_button = QPushButton("Next")
        self.next_image_button.clicked.connect(self.next_image)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_row.addWidget(self.previous_image_button)
        image_row.addWidget(self.image_label, stretch=1)
        image_row.addWidget(self.next_image_button)
        layout.addLayout(image_row)

        view_row = QHBoxLayout()
        self.view_select = QComboBox()
        self.view_select.addItems(["focused_overlay", "overlay", "beam_binary_overlay", "ball_edges_overlay", "raw"])
        self.view_select.currentTextChanged.connect(self.update_preview)
        self.status_label = QLabel()
        view_row.addWidget(compact_field("View", self.view_select))
        view_row.addWidget(self.status_label, stretch=1)
        layout.addLayout(view_row)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(520, 420)
        self.preview.setStyleSheet("background: #111; color: #ddd;")
        layout.addWidget(self.preview, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.reanalyze()

    def plan_item(self) -> AnalysisPlanItem:
        return self.plan[self.current_row]

    def parameters(self) -> AnalysisParameters:
        return AnalysisParameters(
            beam_threshold=self.beam_threshold.value(),
            ball_sensitivity=self.ball_sensitivity.value(),
            pixel_size_mm=self.pixel_size.value(),
            beam_size_px=optional_spin_value(self.beam_size),
            target_size_px=optional_spin_value(self.target_size),
        )

    def previous_image(self) -> None:
        if self.current_row <= 0:
            return
        self.current_row -= 1
        self.reanalyze()

    def next_image(self) -> None:
        if self.current_row >= len(self.plan) - 1:
            return
        self.current_row += 1
        self.reanalyze()

    def update_image_navigation(self) -> None:
        plan_item = self.plan_item()
        self.setWindowTitle(f"Manual Tuning - {plan_item.image_name}")
        self.image_label.setText(
            f"{self.current_row + 1} / {len(self.plan)}  "
            f"{plan_item.image_name}  "
            f"ga={value_text(plan_item.gantry_angle) or '-'}  "
            f"col={value_text(plan_item.collimator_angle) or '-'}  "
            f"cou={value_text(plan_item.couch_angle) or '-'}"
        )
        self.previous_image_button.setEnabled(self.current_row > 0)
        self.next_image_button.setEnabled(self.current_row < len(self.plan) - 1)

    def reanalyze(self) -> None:
        self.update_image_navigation()
        plan_item = self.plan_item()
        try:
            self.current_analysis = analyze_image(plan_item.image_path, self.parameters())
        except Exception as exc:
            self.current_analysis = None
            self.preview.setText(str(exc))
            self.status_label.setText("解析に失敗しました")
            return
        result = self.current_analysis.result
        self.status_label.setText(
            f"{status_text(result.succeeded, result.dx_mm, result.dy_mm)}  "
            f"dx={value_text(result.dx_mm)}  dy={value_text(result.dy_mm)}  "
            f"distance={value_text(result.distance_mm)}"
        )
        self.update_preview()

    def update_preview(self) -> None:
        if self.current_analysis is None:
            return
        image_name = self.view_select.currentText()
        image = getattr(self.current_analysis.debug_images, image_name)
        pixmap = pixmap_from_bgr(image)
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


def pixmap_from_bgr(image) -> QPixmap:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    bytes_per_line = channels * width
    qimage = QImage(
        rgb.data,
        width,
        height,
        bytes_per_line,
        QImage.Format.Format_RGB888,
    ).copy()
    return QPixmap.fromImage(qimage)


def compact_field(label: str, widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    title = QLabel(label)
    title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(title)
    layout.addWidget(widget)
    return container


def value_label() -> QLabel:
    label = QLabel()
    label.setMinimumWidth(54)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet("QLabel { border: 1px solid #aaa; padding: 2px 6px; background: #f7f7f7; }")
    return label


def configure_result_table(table: QTableWidget) -> None:
    header = table.horizontalHeader()
    widths = [44, 88, 170, 76, 64, 64, 86, 66, 78, 58, 54, 54, 54, 54, 74, 74, 78, 72, 72]
    for column, width in enumerate(widths):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(column, width)
    header.setStretchLastSection(False)


def optional_spin_value(spinbox: QSpinBox) -> int | None:
    value = spinbox.value()
    return None if value == spinbox.minimum() else value


def optional_parameter_text(value: int | None) -> str:
    return "auto" if value is None else str(value)


def optional_int_text(value: str) -> int | None:
    text = value.strip().lower()
    if not text or text == "auto":
        return None
    return int(float(text))


def status_text(succeeded: bool | int, dx_mm: float | str | None, dy_mm: float | str | None) -> str:
    if not succeeded:
        return "NG"
    try:
        dx = float(dx_mm)
        dy = float(dy_mm)
    except (TypeError, ValueError):
        return "NG"
    threshold = ok_threshold_mm()
    return "OK" if abs(dx) <= threshold and abs(dy) <= threshold else "NG"


def ok_threshold_mm() -> float:
    try:
        return float(
            load_app_setting(
                OK_THRESHOLD_SETTING,
                load_app_setting(LEGACY_OK_THRESHOLD_SETTING, str(DEFAULT_OK_THRESHOLD_MM)),
            )
        )
    except ValueError:
        return DEFAULT_OK_THRESHOLD_MM


def apply_status_style(item: QTableWidgetItem, status: str) -> None:
    if status == "OK":
        item.setBackground(QColor("#dff3df"))
    elif status == "NG":
        item.setBackground(QColor("#f8dada"))
    else:
        item.setBackground(QColor("white"))


def load_app_setting(key: str, default: str) -> str:
    connection = connect_database(DEFAULT_DB_PATH)
    try:
        init_db(connection)
        return get_setting(connection, key) or default
    except Exception:
        return default
    finally:
        connection.close()


def save_app_setting(key: str, value: str) -> None:
    connection = connect_database(DEFAULT_DB_PATH)
    try:
        init_db(connection)
        set_setting(connection, key, value)
        connection.commit()
    finally:
        connection.close()


def delete_session_results(connection, session_id: int) -> None:
    connection.execute("DELETE FROM analysis_results WHERE session_id = ?", (session_id,))
    connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def load_recent_saved_series(
    db_path: Path,
    machine_name: str | None,
    start_date: str,
    end_date: str,
    limit: int | None,
) -> list[AnalysisSeries]:
    connection = connect_database(db_path)
    try:
        init_db(connection)
        sql = """
            SELECT
                sessions.id AS session_id,
                sessions.started_at,
                sessions.inspection_type,
                COALESCE(machines.name, sessions.machine_name) AS machine_name
            FROM sessions
            LEFT JOIN machines ON machines.id = sessions.machine_id
            WHERE sessions.inspection_type = 'daily'
              AND (? IS NULL OR COALESCE(machines.name, sessions.machine_name) = ?)
              AND sessions.started_at >= ?
              AND sessions.started_at <= ?
            ORDER BY sessions.started_at DESC, sessions.id DESC
            """
        params: list[object] = [
            machine_name,
            machine_name,
            f"{start_date}T00:00:00",
            f"{end_date}T23:59:59",
        ]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        session_rows = connection.execute(sql, params).fetchall()
        histories: list[AnalysisSeries] = []
        for session in session_rows:
            point_rows = connection.execute(
                """
                SELECT
                    analysis_results.analyzed_at,
                    analysis_results.image_name,
                    analysis_results.image_path,
                    analysis_results.note AS setup_label,
                    analysis_results.dx_mm,
                    analysis_results.dy_mm,
                    analysis_results.distance_mm,
                    analysis_results.gantry_angle,
                    analysis_results.collimator_angle,
                    analysis_results.couch_angle,
                    analysis_results.pixel_size_mm,
                    analysis_results.beam_threshold,
                    analysis_results.ball_sensitivity,
                    analysis_results.beam_size_px,
                    analysis_results.target_size_px,
                    analysis_results.x_axis_label,
                    analysis_results.y_axis_label,
                    analysis_results.dx_positive_label,
                    analysis_results.dx_negative_label,
                    analysis_results.dy_positive_label,
                    analysis_results.dy_negative_label,
                    analysis_results.x_inverted,
                    sessions.inspection_type
                FROM analysis_results
                JOIN sessions ON sessions.id = analysis_results.session_id
                WHERE analysis_results.session_id = ?
                  AND analysis_results.succeeded = 1
                ORDER BY analysis_results.id ASC
                """,
                (int(session["session_id"]),),
            ).fetchall()
            histories.append(
                AnalysisSeries(
                    name=series_display_name(session["started_at"]),
                    plan=[],
                    analyses=[],
                    inspection_type=session["inspection_type"],
                    machine_name=session["machine_name"],
                    saved=True,
                    started_at=session["started_at"],
                    source="history",
                    session_id=int(session["session_id"]),
                    points=[report_point_from_row(row) for row in point_rows],
                )
            )
        return histories
    finally:
        connection.close()


def series_display_name(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y/%m/%d %H:%M")
    except ValueError:
        return value[:16]


def parse_datetime_or_none(value: str) -> datetime | None:
    if not value:
        return None


def analysis_setup_from_row(row) -> AnalysisSetup:
    return AnalysisSetup(
        name=row["name"],
        gantry_angle=float(row["gantry_angle"]),
        collimator_angle=float(row["collimator_angle"]),
        couch_angle=float(row["couch_angle"]),
        dx_positive_label=row["dx_positive_label"] if "dx_positive_label" in row.keys() else "+dx",
        dx_negative_label=row["dx_negative_label"] if "dx_negative_label" in row.keys() else "-dx",
        dy_positive_label=row["dy_positive_label"] if "dy_positive_label" in row.keys() else "+dy",
        dy_negative_label=row["dy_negative_label"] if "dy_negative_label" in row.keys() else "-dy",
        field_size_px=row["field_size_px"],
        target_size_px=row["target_size_px"],
        pixel_size_mm=float(row["pixel_size_mm"]),
        beam_threshold=int(row["beam_threshold"]),
        ball_sensitivity=int(row["ball_sensitivity"]),
    )


def plan_item_with_setup(
    item: AnalysisPlanItem,
    setup: AnalysisSetup | None,
) -> AnalysisPlanItem:
    if setup is None:
        return AnalysisPlanItem(
            order=item.order,
            image_path=item.image_path,
            image_name=item.image_name,
            setup_label=None,
            gantry_angle=None,
            collimator_angle=None,
            couch_angle=None,
            x_axis_label=None,
            y_axis_label=None,
            dx_positive_label=None,
            dx_negative_label=None,
            dy_positive_label=None,
            dy_negative_label=None,
            parameters=None,
        )
    return AnalysisPlanItem(
        order=item.order,
        image_path=item.image_path,
        image_name=item.image_name,
        setup_label=setup.name,
        gantry_angle=setup.gantry_angle,
        collimator_angle=setup.collimator_angle,
        couch_angle=setup.couch_angle,
        x_axis_label=f"(-){setup.dx_negative_label} <- -> {setup.dx_positive_label}(+)",
        y_axis_label=f"(-){setup.dy_negative_label} <- -> {setup.dy_positive_label}(+)",
        dx_positive_label=setup.dx_positive_label,
        dx_negative_label=setup.dx_negative_label,
        dy_positive_label=setup.dy_positive_label,
        dy_negative_label=setup.dy_negative_label,
        parameters=AnalysisParameters(
            beam_threshold=setup.beam_threshold,
            ball_sensitivity=setup.ball_sensitivity,
            pixel_size_mm=setup.pixel_size_mm,
            beam_size_px=setup.field_size_px,
            target_size_px=setup.target_size_px,
        ),
    )
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def update_setup_preset_by_id(connection, preset_id: int, preset: SetupPreset) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    connection.execute(
        """
        UPDATE setup_presets
        SET name = ?, description = ?, updated_at = ?, is_builtin = 0, is_active = 1
        WHERE id = ?
        """,
        (preset.name, preset.description, now, preset_id),
    )
    connection.execute("DELETE FROM setup_steps WHERE preset_id = ?", (preset_id,))
    setup_ids = [
        upsert_setup(connection, setup)
        for setup in preset.setups
    ]
    connection.executemany(
        """
        INSERT INTO setup_steps (
            preset_id,
            step_order,
            setup_id
        )
        VALUES (?, ?, ?)
        """,
        [
            (
                preset_id,
                index,
                setup_id,
            )
            for index, setup_id in enumerate(setup_ids, start=1)
        ],
    )


def same_setup_angles(left: AnalysisPlanItem, right: AnalysisPlanItem) -> bool:
    return (
        same_optional_float(left.gantry_angle, right.gantry_angle)
        and same_optional_float(left.collimator_angle, right.collimator_angle)
        and same_optional_float(left.couch_angle, right.couch_angle)
    )


def same_optional_float(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return abs(float(left) - float(right)) < 0.000001


def duplicated_setup_labels(setups: list[AnalysisSetup]) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for setup in setups:
        key = setup.name.strip().casefold()
        if key in seen:
            label = seen[key]
            if label not in duplicates:
                duplicates.append(label)
        else:
            seen[key] = setup.name.strip()
    return duplicates


def report_point_from_row(row) -> ReportPoint:
    keys = set(row.keys())
    return ReportPoint(
        analyzed_at=row["analyzed_at"],
        image_name=row["image_name"],
        setup_label=row["setup_label"] or row["image_name"],
        dx_mm=float(row["dx_mm"]),
        dy_mm=float(row["dy_mm"]),
        distance_mm=float(row["distance_mm"]),
        gantry_angle=row["gantry_angle"],
        collimator_angle=row["collimator_angle"],
        couch_angle=row["couch_angle"],
        image_path=row["image_path"] if "image_path" in keys else "",
        pixel_size_mm=float(row["pixel_size_mm"]) if "pixel_size_mm" in keys else 0.242,
        beam_threshold=int(row["beam_threshold"]) if "beam_threshold" in keys else 0,
        ball_sensitivity=int(row["ball_sensitivity"]) if "ball_sensitivity" in keys else 10,
        beam_size_px=row["beam_size_px"] if "beam_size_px" in keys else None,
        target_size_px=row["target_size_px"] if "target_size_px" in keys else None,
        x_axis_label=row["x_axis_label"] if "x_axis_label" in keys else "",
        y_axis_label=row["y_axis_label"] if "y_axis_label" in keys else "",
        dx_positive_label=row["dx_positive_label"] if "dx_positive_label" in keys and row["dx_positive_label"] else "+dx",
        dx_negative_label=row["dx_negative_label"] if "dx_negative_label" in keys and row["dx_negative_label"] else "-dx",
        dy_positive_label=row["dy_positive_label"] if "dy_positive_label" in keys and row["dy_positive_label"] else "+dy",
        dy_negative_label=row["dy_negative_label"] if "dy_negative_label" in keys and row["dy_negative_label"] else "-dy",
        x_inverted=bool(row["x_inverted"]) if "x_inverted" in keys else False,
        inspection_type=row["inspection_type"] if "inspection_type" in keys else "",
    )


def history_row_dict(row) -> dict[str, str]:
    status = status_text(row["succeeded"], row["dx_mm"], row["dy_mm"])
    return {
        "session_id": str(row["session_id"]),
        "series_name": row["series_name"] or row["analyzed_at"],
        "analyzed_at": row["analyzed_at"],
        "machine": row["machine"] or "",
        "inspection_type": row["inspection_type"] or "",
        "image_name": row["image_name"] or "",
        "setup_label": row["setup_label"] or "",
        "status": status,
        "dx_mm": value_text(row["dx_mm"]),
        "dy_mm": value_text(row["dy_mm"]),
        "distance_mm": value_text(row["distance_mm"]),
        "gantry_angle": value_text(row["gantry_angle"]),
        "collimator_angle": value_text(row["collimator_angle"]),
        "couch_angle": value_text(row["couch_angle"]),
    }


def unique_sessions(rows: list[dict[str, str]]) -> list[dict[str, str | int]]:
    sessions: list[dict[str, str | int]] = []
    seen: set[int] = set()
    for row in rows:
        session_id = int(row["session_id"])
        if session_id in seen:
            continue
        seen.add(session_id)
        sessions.append(
            {
                "session_id": session_id,
                "series_name": row["series_name"],
                "machine": row["machine"],
                "inspection_type": row["inspection_type"],
            }
        )
    return sessions


def short_series_name(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y/%m/%d %H:%M")
    except ValueError:
        return value[:16]


def table_text(table: QTableWidget, row: int, column: int) -> str:
    item = table.item(row, column)
    return item.text() if item is not None else ""


def raise_error(parent: QWidget, title: str, message: str) -> None:
    show_error(parent, title, ValueError(message))


def overlay_analysis_text(pixmap: QPixmap, plan_item: AnalysisPlanItem, analysis: Analysis) -> QPixmap:
    output = QPixmap(pixmap)
    painter = QPainter(output)
    try:
        painter.setFont(QFont("Helvetica", max(12, output.width() // 42), QFont.Weight.Bold))
        painter.setPen(QColor("white"))
        result = analysis.result
        draw_overlay_text(painter, 10, 10, [plan_item.image_name])
        draw_overlay_text(
            painter,
            output.width() - 10,
            10,
            [
                f"ga {value_text(plan_item.gantry_angle) or '-'}",
                f"col {value_text(plan_item.collimator_angle) or '-'}",
                f"cou {value_text(plan_item.couch_angle) or '-'}",
            ],
            align_right=True,
        )
        draw_overlay_text(
            painter,
            10,
            output.height() - 10,
            [
                f"dx {value_text(result.dx_mm) or '-'}",
                f"dy {value_text(result.dy_mm) or '-'}",
            ],
            align_bottom=True,
        )
    finally:
        painter.end()
    return output


def overlay_unanalyzed_text(pixmap: QPixmap, plan_item: AnalysisPlanItem) -> QPixmap:
    output = QPixmap(pixmap)
    painter = QPainter(output)
    try:
        painter.setFont(QFont("Helvetica", max(16, min(28, output.width() // 14)), QFont.Weight.Bold))
        painter.setPen(QColor("white"))
        draw_overlay_text(painter, 10, 10, [plan_item.image_name])
        draw_overlay_text(
            painter,
            output.width() - 10,
            10,
            ["未解析"],
            align_right=True,
        )
    finally:
        painter.end()
    return output


def draw_overlay_text(
    painter: QPainter,
    x: int,
    y: int,
    lines: list[str],
    align_right: bool = False,
    align_bottom: bool = False,
) -> None:
    line_height = painter.fontMetrics().height() + 4
    width = max(painter.fontMetrics().horizontalAdvance(line) for line in lines) + 16
    height = line_height * len(lines) + 8
    left = x - width if align_right else x
    top = y - height if align_bottom else y
    rect = QRectF(left, top, width, height)

    painter.fillRect(rect, QColor(0, 0, 0, 160))
    painter.setPen(QColor("white"))
    for index, line in enumerate(lines):
        text_rect = QRectF(left + 8, top + 4 + index * line_height, width - 16, line_height)
        flags = Qt.AlignmentFlag.AlignVCenter
        flags |= Qt.AlignmentFlag.AlignRight if align_right else Qt.AlignmentFlag.AlignLeft
        painter.drawText(text_rect, int(flags), line)


def value_text(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def one_decimal_text(value: float | int | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.1f}"


def show_error(parent: QWidget, title: str, exc: Exception) -> None:
    QMessageBox.critical(parent, title, str(exc))


def run() -> int:
    app = QApplication([])
    signal.signal(signal.SIGINT, lambda *_args: app.quit())
    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(100)
    window = MainWindow()
    window.show()
    return app.exec()
