from __future__ import annotations

import csv
import signal
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import cv2
from PySide6.QtCore import QDate, QEvent, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
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

from conditions import AnalysisCondition, ConditionPreset
from core import (
    Analysis,
    AnalysisParameters,
    analyze_image,
    save_debug_output,
)
from database import (
    AnalysisMetadata,
    connect_database,
    create_session,
    get_condition_preset,
    get_default_machine_name,
    get_or_create_machine,
    init_db,
    list_condition_presets,
    list_condition_steps,
    list_machines,
    save_analysis_results,
    set_default_machine_name,
    upsert_condition_preset,
)
from report import (
    ReportPoint,
    generate_pdf_report,
    load_report_data,
    render_grouped_report_pages,
)
from workflow import AnalysisPlanItem, analyze_plan, build_analysis_plan_from_preset


DEFAULT_DB_PATH = Path("data/wanalyzer.sqlite")
DEFAULT_DEBUG_OUTPUT = Path("log/core_debug")
RESULT_TABLE_HEADERS = [
    "Order",
    "Image",
    "Condition",
    "Status",
    "dx mm",
    "dy mm",
    "Distance mm",
    "Gantry",
    "Collimator",
    "Couch",
]


@dataclass
class AnalysisSeries:
    name: str
    plan: list[AnalysisPlanItem]
    analyses: list[Analysis]
    inspection_type: str
    machine_name: str | None
    saved: bool = False


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WanaLyzer")
        self.resize(900, 650)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self.tabs = QTabWidget()
        self.daily_tab = DailyTab()
        self.analyze_tab = AnalyzeTab()
        self.manage_tab = ManageTab(self.refresh_analysis_tabs)
        self.history_tab = HistoryTab()
        self.tabs.addTab(self.daily_tab, "Daily")
        self.tabs.addTab(self.analyze_tab, "Temp")
        self.tabs.addTab(self.manage_tab, "Manage")
        self.tabs.addTab(self.history_tab, "History")
        layout.addWidget(self.tabs, stretch=1)

    def refresh_analysis_tabs(self) -> None:
        self.daily_tab.refresh_database_options()
        self.analyze_tab.refresh_database_options()
        self.history_tab.refresh_options()


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

        layout = QVBoxLayout(self)
        layout.addWidget(self.build_settings_group(default_image_path))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.build_table_group())
        splitter.addWidget(self.build_preview_group())
        splitter.setSizes([560, 220])
        layout.addWidget(splitter, stretch=1)

        self.refresh_database_options()

    def build_settings_group(self, default_image_path: str) -> QGroupBox:
        group = QGroupBox("Settings")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        path_group = QGroupBox()
        path_row = QVBoxLayout(path_group)
        path_row.setContentsMargins(6, 4, 6, 4)
        path_row.setSpacing(4)
        self.image_path = QLineEdit(default_image_path)
        self.image_path.setMinimumWidth(145)
        self.image_path.setMaximumWidth(210)
        image_button = QPushButton("Browse")
        image_button.clicked.connect(self.browse_images)
        image_group = QHBoxLayout()
        image_group.setSpacing(4)
        image_group.addWidget(compact_field("Input", self.image_path))
        image_group.addWidget(image_button)
        path_row.addLayout(image_group)

        self.output_path = QLineEdit(str(DEFAULT_DEBUG_OUTPUT))
        self.output_path.setMinimumWidth(145)
        self.output_path.setMaximumWidth(210)
        output_button = QPushButton("Browse")
        output_button.clicked.connect(self.browse_output)
        output_group = QHBoxLayout()
        output_group.setSpacing(4)
        output_group.addWidget(compact_field("Output", self.output_path))
        output_group.addWidget(output_button)
        path_row.addLayout(output_group)
        top_row.addWidget(path_group)

        conditions_group = QGroupBox()
        option_row = QVBoxLayout(conditions_group)
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
        top_row.addWidget(conditions_group)

        actions_group = QGroupBox()
        actions_row = QGridLayout(actions_group)
        actions_row.setContentsMargins(6, 4, 6, 4)
        actions_row.setHorizontalSpacing(6)
        actions_row.setVerticalSpacing(6)
        analyze_button = QPushButton("Analyze")
        analyze_button.clicked.connect(self.analyze_clicked)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_clicked)
        preview_button = QPushButton("Result Preview")
        preview_button.clicked.connect(self.result_preview_clicked)
        export_button = QPushButton("Export PDF")
        export_button.clicked.connect(self.export_pdf_clicked)
        for button in [analyze_button, save_button, preview_button, export_button]:
            button.setMinimumSize(96, 32)
        actions_row.addWidget(analyze_button, 0, 0)
        actions_row.addWidget(preview_button, 0, 1)
        actions_row.addWidget(save_button, 1, 0)
        actions_row.addWidget(export_button, 1, 1)
        top_row.addWidget(actions_group)
        top_row.addStretch()
        layout.addLayout(top_row)

        tuning_group = QGroupBox("Tuning Parameters")
        tuning_group.setCheckable(True)
        tuning_group.setChecked(False)
        tuning_layout = QVBoxLayout(tuning_group)
        tuning_layout.setContentsMargins(6, 4, 6, 4)
        self.tuning_content = QWidget()
        tuning_content_layout = QGridLayout(self.tuning_content)
        tuning_content_layout.setContentsMargins(0, 0, 0, 0)
        tuning_content_layout.setHorizontalSpacing(14)
        tuning_content_layout.setVerticalSpacing(4)
        self.pixel_size_value = value_label()
        self.beam_size_value = value_label()
        self.target_size_value = value_label()
        self.beam_threshold_value = value_label()
        self.ball_sensitivity_value = value_label()
        tuning_content_layout.addWidget(compact_field("Pixel mm", self.pixel_size_value), 0, 0)
        tuning_content_layout.addWidget(compact_field("Field px", self.beam_size_value), 0, 1)
        tuning_content_layout.addWidget(compact_field("Target px", self.target_size_value), 0, 2)
        tuning_content_layout.addWidget(compact_field("Beam th", self.beam_threshold_value), 1, 0)
        tuning_content_layout.addWidget(compact_field("Ball sens", self.ball_sensitivity_value), 1, 1)
        tuning_button = QPushButton("Manual Tuning")
        tuning_button.clicked.connect(self.manual_tuning_clicked)
        tuning_content_layout.addWidget(tuning_button, 1, 2)
        tuning_layout.addWidget(self.tuning_content)
        tuning_group.toggled.connect(self.tuning_content.setVisible)
        self.tuning_content.setVisible(False)
        self.update_tuning_parameter_labels()
        layout.addWidget(tuning_group)

        return group

    def build_table_group(self) -> QGroupBox:
        group = QGroupBox("Plan / Results")
        layout = QVBoxLayout(group)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(RESULT_TABLE_HEADERS)
        configure_result_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.update_preview_from_selection)
        layout.addWidget(self.table)
        return group

    def build_preview_group(self) -> QGroupBox:
        group = QGroupBox("Analyzed Images")
        layout = QVBoxLayout(group)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(190, 190)
        self.preview.setStyleSheet("background: #111; color: #ddd;")
        self.preview.setText("Analyze and select a row")

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

    def refresh_database_options(self) -> None:
        try:
            connection = connect_database(DEFAULT_DB_PATH)
            try:
                init_db(connection)
                presets = list_condition_presets(connection)
                machines = list_machines(connection)
                default_machine = get_default_machine_name(connection)
            finally:
                connection.close()
        except Exception as exc:
            show_error(self, "Database Error", exc)
            return

        self.loading_options = True
        try:
            current_preset = self.preset_combo.currentText()
            self.preset_combo.clear()
            for preset in presets:
                self.preset_combo.addItem(preset["name"])
            if current_preset:
                self.preset_combo.setCurrentText(current_preset)

            current_machine = self.machine_combo.currentText()
            self.machine_combo.clear()
            for machine in machines:
                self.machine_combo.addItem(machine["name"])
            self.machine_combo.setCurrentText(current_machine or default_machine)
        finally:
            self.loading_options = False

        self.load_plan_preview()

    def browse_images(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Images", self.image_path.text())
        if path:
            self.image_path.setText(path)
            self.load_plan_preview()

    def browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Debug Output", self.output_path.text())
        if path:
            self.output_path.setText(path)

    def analyze_clicked(self) -> None:
        try:
            series = self.create_series()
        except Exception as exc:
            show_error(self, "Analysis Error", exc)
            return
        self.set_current_series(series)
        self.after_analysis(series)

    def create_series(self) -> AnalysisSeries:
        plan = self.loaded_plan or self.build_plan()

        analyses = analyze_plan(plan, self.analysis_parameters())
        save_debug_output(analyses, self.output_path_value(), write_images=True)
        return AnalysisSeries(
            name=self.series_name(plan),
            plan=plan,
            analyses=analyses,
            inspection_type=self.inspection_type.currentText(),
            machine_name=self.machine_name(),
        )

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
            show_error(self, "Tuning Error", ValueError("No image is selected."))
            return
        dialog = ManualTuningDialog(plan[row], self.analysis_parameters(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.set_analysis_parameters(dialog.parameters())
            self.log("Updated analysis parameters from manual tuning.")

    def build_plan(self) -> list[AnalysisPlanItem]:
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

    def load_plan_preview(self) -> None:
        if self.loading_options or not hasattr(self, "table"):
            return
        if not self.preset_combo.currentText():
            return
        try:
            self.loaded_plan = self.build_plan()
        except Exception as exc:
            self.loaded_plan = []
            self.current_series = None
            self.table.setRowCount(0)
            self.preview.clear()
            self.preview.setText("Analyze and select a row")
            self.log(f"Plan load failed: {exc}")
            return
        self.current_series = None
        self.render_plan_preview(self.loaded_plan)
        self.preview.clear()
        self.preview.setText("Analyze and select a row")
        self.log(f"Loaded plan: {len(self.loaded_plan)} images.")

    def series_name(self, plan: list[AnalysisPlanItem]) -> str:
        image_dir = self.image_path_value().name or str(self.image_path_value())
        return f"{image_dir} ({len(plan)} images)"

    def set_current_series(self, series: AnalysisSeries) -> None:
        self.current_series = series
        self.render_series(series)

    def after_analysis(self, series: AnalysisSeries) -> None:
        self.log(f"Analyzed {series.name}. Review focused overlays before saving.")

    def result_preview_clicked(self) -> None:
        if self.current_series is None:
            show_error(self, "Preview Error", ValueError("No analyzed series is selected."))
            return
        try:
            grouped = self.report_data_with_current_series(self.current_series)
            pages = render_grouped_report_pages(grouped, self.current_series.machine_name)
        except Exception as exc:
            show_error(self, "Preview Error", exc)
            return
        PagePreviewDialog("Result Preview", pages, self).exec()

    def save_clicked(self) -> None:
        if self.current_series is None:
            show_error(self, "Save Error", ValueError("No analyzed series is selected."))
            return
        series = self.current_series
        if series.saved:
            self.log(f"Already saved: {series.name}.")
            return
        try:
            self.save_series(series)
        except Exception as exc:
            show_error(self, "Save Error", exc)
            return
        series.saved = True
        self.refresh_database_options()
        self.current_series = series
        self.render_series(series)
        self.log(f"Saved {series.name}.")

    def export_pdf_clicked(self) -> None:
        if self.current_series is None:
            show_error(self, "Export Error", ValueError("No analyzed series is selected."))
            return
        series = self.current_series
        if not series.saved:
            reply = QMessageBox.question(
                self,
                "Save Required",
                "Current analysis results are not saved. Save them before exporting PDF?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                self.save_series(series)
            except Exception as exc:
                show_error(self, "Export Error", exc)
                return
            series.saved = True
        default_name = (
            f"{series.machine_name}_report.pdf"
            if series.machine_name
            else "report.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            str(Path("log") / default_name),
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not path:
            return
        try:
            generate_pdf_report(DEFAULT_DB_PATH, path, machine_name=series.machine_name)
        except Exception as exc:
            show_error(self, "Export Error", exc)
            return
        self.refresh_database_options()
        self.current_series = series
        self.render_series(series)
        self.log(f"Exported PDF: {path}")

    def save_series(self, series: AnalysisSeries) -> None:
        metadata = [
            AnalysisMetadata(
                gantry_angle=item.gantry_angle,
                collimator_angle=item.collimator_angle,
                couch_angle=item.couch_angle,
                note=item.condition_label,
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
            )
            save_analysis_results(connection, session_id, series.analyses, metadata)
        finally:
            connection.close()

    def render_series(self, series: AnalysisSeries) -> None:
        self.table.setRowCount(len(series.plan))
        for row, (plan_item, analysis) in enumerate(zip(series.plan, series.analyses)):
            result = analysis.result
            values = [
                f"{plan_item.order:02d}",
                plan_item.image_name,
                plan_item.condition_label or "",
                status_text(result.succeeded, result.dx_mm, result.dy_mm),
                value_text(result.dx_mm),
                value_text(result.dy_mm),
                value_text(result.distance_mm),
                value_text(plan_item.gantry_angle),
                value_text(plan_item.collimator_angle),
                value_text(plan_item.couch_angle),
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, table_item)
        configure_result_table(self.table)
        if series.analyses:
            self.table.selectRow(0)
            self.update_preview_from_selection()

    def render_plan_preview(self, plan: list[AnalysisPlanItem]) -> None:
        self.table.setRowCount(len(plan))
        for row, plan_item in enumerate(plan):
            values = [
                f"{plan_item.order:02d}",
                plan_item.image_name,
                plan_item.condition_label or "",
                "not analyzed",
                "",
                "",
                "",
                value_text(plan_item.gantry_angle),
                value_text(plan_item.collimator_angle),
                value_text(plan_item.couch_angle),
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, table_item)
        configure_result_table(self.table)
        if plan:
            self.table.selectRow(0)

    def update_preview_from_selection(self) -> None:
        if self.current_series is None:
            return
        row = self.selected_row()
        if row is None:
            return
        if row < 0 or row >= len(self.current_series.analyses):
            return
        pixmap = self.preview_page_pixmap(self.current_series, row)
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

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
        self.table.selectRow(next_row)

    def preview_page_pixmap(self, series: AnalysisSeries, row: int) -> QPixmap:
        pixmap = pixmap_from_bgr(series.analyses[row].debug_images.focused_overlay)
        return overlay_analysis_text(pixmap, series.plan[row], series.analyses[row])

    def series_preview_pages(self, series: AnalysisSeries) -> list[QPixmap]:
        return [
            self.preview_page_pixmap(series, row)
            for row in range(min(len(series.plan), len(series.analyses)))
        ]

    def report_data_with_current_series(self, series: AnalysisSeries) -> dict[str, list[ReportPoint]]:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            grouped = load_report_data(connection, machine_name=series.machine_name, limit=9)
        finally:
            connection.close()

        now = datetime.now().isoformat(timespec="seconds")
        for plan_item, analysis in zip(series.plan, series.analyses):
            if not analysis.result.succeeded:
                continue
            label = plan_item.condition_label or plan_item.image_name
            grouped.setdefault(label, [])
            grouped[label].append(
                ReportPoint(
                    analyzed_at=now,
                    image_name=plan_item.image_name,
                    condition_label=label,
                    dx_mm=float(analysis.result.dx_mm),
                    dy_mm=float(analysis.result.dy_mm),
                    distance_mm=float(analysis.result.distance_mm),
                    gantry_angle=plan_item.gantry_angle,
                    collimator_angle=plan_item.collimator_angle,
                    couch_angle=plan_item.couch_angle,
                )
            )
            grouped[label] = grouped[label][-10:]
        if not grouped:
            raise ValueError("No successful analysis results are available for preview.")
        return dict(sorted(grouped.items()))

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
        super().__init__(
            default_inspection="daily",
            default_image_path="sample/set",
            show_inspection=False,
        )


class AnalyzeTab(AnalysisTab):
    def __init__(self) -> None:
        self.series_list: QListWidget
        self.series: list[AnalysisSeries] = []
        super().__init__(
            default_inspection="temporary",
            default_image_path="sample/set",
            show_inspection=False,
        )

    def build_table_group(self) -> QGroupBox:
        group = QGroupBox("Series / Plan / Results")
        layout = QHBoxLayout(group)

        self.series_list = QListWidget()
        self.series_list.currentRowChanged.connect(self.select_series)
        layout.addWidget(self.series_list, stretch=1)

        table_group = QWidget()
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(RESULT_TABLE_HEADERS)
        configure_result_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.update_preview_from_selection)
        table_layout.addWidget(self.table)
        layout.addWidget(table_group, stretch=4)
        return group

    def after_analysis(self, series: AnalysisSeries) -> None:
        self.series.append(series)
        self.series_list.addItem(series.name)
        self.series_list.setCurrentRow(len(self.series) - 1)
        self.log(f"Added {series.name}. Save only the selected series.")

    def load_plan_preview(self) -> None:
        super().load_plan_preview()
        if hasattr(self, "series_list"):
            self.series_list.setCurrentRow(-1)

    def select_series(self, row: int) -> None:
        if row < 0 or row >= len(self.series):
            return
        self.set_current_series(self.series[row])

    def save_clicked(self) -> None:
        row = self.series_list.currentRow()
        if row < 0 or row >= len(self.series):
            show_error(self, "Save Error", ValueError("No series is selected."))
            return
        self.current_series = self.series[row]
        super().save_clicked()
        if self.current_series.saved:
            self.series_list.item(row).setText(self.current_series.name + " [saved]")

    def export_pdf_clicked(self) -> None:
        row = self.series_list.currentRow()
        if row < 0 or row >= len(self.series):
            show_error(self, "Export Error", ValueError("No series is selected."))
            return
        self.current_series = self.series[row]
        super().export_pdf_clicked()
        if self.current_series.saved:
            self.series_list.item(row).setText(self.current_series.name + " [saved]")


class ManageTab(QWidget):
    def __init__(self, on_changed) -> None:
        super().__init__()
        self.on_changed = on_changed
        self.preset_mode = "edit"
        layout = QVBoxLayout(self)
        layout.addWidget(self.build_machine_group())
        layout.addWidget(self.build_preset_group(), stretch=1)
        self.refresh()

    def build_machine_group(self) -> QGroupBox:
        group = QGroupBox("Machines")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.machine_select = QComboBox()
        self.machine_select.currentTextChanged.connect(self.select_machine)
        self.machine_select.setMinimumWidth(90)
        self.machine_name = QLineEdit()
        self.machine_name.setMinimumWidth(120)
        self.current_default_label = QLabel("Current default: -")
        layout.addWidget(compact_field("Select", self.machine_select))
        layout.addWidget(compact_field("Name", self.machine_name))
        save_button = QPushButton("Register / Change Name")
        save_button.clicked.connect(self.save_machine)
        default_button = QPushButton("Set Default")
        default_button.clicked.connect(self.save_default_machine)
        layout.addWidget(save_button)
        layout.addWidget(default_button)
        layout.addWidget(self.current_default_label)
        layout.addStretch()
        return group

    def build_preset_group(self) -> QGroupBox:
        group = QGroupBox("Presets")
        layout = QVBoxLayout(group)

        select_group = QGroupBox("Select")
        top = QHBoxLayout(select_group)
        top.setContentsMargins(8, 6, 8, 6)
        self.preset_select = QComboBox()
        top.addWidget(compact_field("Preset", self.preset_select))
        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self.edit_selected_preset)
        new_button = QPushButton("New Preset")
        new_button.clicked.connect(self.new_preset)
        top.addWidget(edit_button)
        top.addWidget(new_button)
        top.addStretch()
        layout.addWidget(select_group)

        edit_group = QGroupBox("Editor")
        edit_layout = QVBoxLayout(edit_group)
        self.preset_mode_label = QLabel("Mode: edit selected")
        edit_layout.addWidget(self.preset_mode_label)

        fields = QHBoxLayout()
        self.preset_name = QLineEdit()
        self.preset_description = QLineEdit()
        fields.addWidget(compact_field("Name", self.preset_name))
        fields.addWidget(compact_field("Description", self.preset_description), stretch=1)
        edit_layout.addLayout(fields)

        self.step_table = QTableWidget(0, 4)
        self.step_table.setHorizontalHeaderLabels(["Label", "Gantry", "Collimator", "Couch"])
        self.step_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 4):
            self.step_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        edit_layout.addWidget(self.step_table)

        actions_group = QGroupBox("Steps")
        buttons = QHBoxLayout()
        add_row = QPushButton("Add Row")
        add_row.clicked.connect(self.add_step_row)
        remove_row = QPushButton("Remove Row")
        remove_row.clicked.connect(self.remove_step_row)
        save_preset = QPushButton("Save Preset")
        save_preset.clicked.connect(self.save_preset)
        buttons.addWidget(add_row)
        buttons.addWidget(remove_row)
        buttons.addStretch()
        buttons.addWidget(save_preset)
        actions_group.setLayout(buttons)
        edit_layout.addWidget(actions_group)
        layout.addWidget(edit_group)
        return group

    def refresh(self) -> None:
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            machines = list_machines(connection)
            presets = list_condition_presets(connection)
            default_machine = get_default_machine_name(connection)
        finally:
            connection.close()

        current_machine = self.machine_select.currentText()
        self.machine_select.blockSignals(True)
        self.machine_select.clear()
        self.machine_select.addItem("New")
        for machine in machines:
            self.machine_select.addItem(machine["name"])
        if current_machine and current_machine != "New":
            self.machine_select.setCurrentText(current_machine)
        else:
            self.machine_select.setCurrentText(default_machine)
        self.current_default_label.setText(f"Current default: {default_machine}")
        self.machine_select.blockSignals(False)
        self.select_machine()

        current = self.preset_select.currentText()
        self.preset_select.blockSignals(True)
        self.preset_select.clear()
        for preset in presets:
            self.preset_select.addItem(preset["name"])
        if current:
            self.preset_select.setCurrentText(current)
        self.preset_select.blockSignals(False)
        if self.preset_mode == "edit":
            self.edit_selected_preset()

    def select_machine(self, *_args) -> None:
        selected = self.machine_select.currentText()
        self.machine_name.clear() if selected == "New" else self.machine_name.setText(selected)

    def save_machine(self) -> None:
        name = self.machine_name.text().strip()
        if not name:
            show_error(self, "Machine Error", ValueError("Machine name is required."))
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            selected = self.machine_select.currentText()
            if selected and selected != "New" and selected != name:
                default_machine = get_default_machine_name(connection)
                connection.execute(
                    """
                    UPDATE machines
                    SET name = ?, updated_at = ?
                    WHERE name = ?
                    """,
                    (name, datetime.now().isoformat(timespec="seconds"), selected),
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
            show_error(self, "Machine Error", ValueError("Default machine is required."))
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

    def edit_selected_preset(self, *_args) -> None:
        name = self.preset_select.currentText()
        if not name:
            return
        self.preset_mode = "edit"
        self.preset_mode_label.setText("Mode: edit selected")
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            preset = get_condition_preset(connection, name)
            if preset is None:
                return
            steps = list_condition_steps(connection, int(preset["id"]))
        finally:
            connection.close()
        self.preset_name.setText(name)
        self.preset_description.setText(preset["description"] or "")
        self.step_table.setRowCount(len(steps))
        for row, step in enumerate(steps):
            values = [
                step["label"],
                value_text(step["gantry_angle"]),
                value_text(step["collimator_angle"]),
                value_text(step["couch_angle"]),
            ]
            for column, value in enumerate(values):
                self.step_table.setItem(row, column, QTableWidgetItem(value))

    def new_preset(self) -> None:
        self.preset_mode = "new"
        self.preset_mode_label.setText("Mode: new preset")
        self.preset_name.clear()
        self.preset_description.clear()
        self.step_table.setRowCount(0)
        self.add_step_row()

    def add_step_row(self) -> None:
        row = self.step_table.rowCount()
        self.step_table.insertRow(row)
        for column, value in enumerate(["condition", "0", "0", "0"]):
            self.step_table.setItem(row, column, QTableWidgetItem(value))

    def remove_step_row(self) -> None:
        row = self.step_table.currentRow()
        if row >= 0:
            self.step_table.removeRow(row)

    def save_preset(self) -> None:
        name = self.preset_name.text().strip()
        if not name:
            show_error(self, "Preset Error", ValueError("Preset name is required."))
            return
        conditions: list[AnalysisCondition] = []
        for row in range(self.step_table.rowCount()):
            label = table_text(self.step_table, row, 0).strip()
            if not label:
                raise_error(self, "Preset Error", f"Row {row + 1}: label is required.")
                return
            try:
                conditions.append(
                    AnalysisCondition(
                        label,
                        float(table_text(self.step_table, row, 1)),
                        float(table_text(self.step_table, row, 2)),
                        float(table_text(self.step_table, row, 3)),
                    )
                )
            except ValueError:
                raise_error(self, "Preset Error", f"Row {row + 1}: angles must be numbers.")
                return
        if not conditions:
            show_error(self, "Preset Error", ValueError("At least one condition row is required."))
            return

        preset = ConditionPreset(name, self.preset_description.text().strip(), tuple(conditions))
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            upsert_condition_preset(connection, preset, is_builtin=False)
            connection.commit()
        finally:
            connection.close()
        self.refresh()
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
            ["Image", "Condition", "Status", "dx", "dy", "Distance", "Gantry", "Collimator", "Couch", "Machine", "Inspection"]
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
                analysis_results.note AS condition_label,
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
            "condition_label",
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
            show_error(self, "History Error", ValueError("Select a series first."))
            return
        reply = QMessageBox.question(
            self,
            "Delete Series",
            "Delete the selected series and all of its analysis results?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            connection.execute("DELETE FROM analysis_results WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            connection.commit()
        finally:
            connection.close()
        self.query()

    def export_csv(self) -> None:
        if not self.rows:
            show_error(self, "CSV Error", ValueError("No rows to export."))
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
    def __init__(self, title: str, pages: list[QPixmap], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pages = pages
        self.page_index = 0

        self.setWindowTitle(title)
        self.resize(900, 760)

        layout = QVBoxLayout(self)
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.page_label)
        self.scroll_area.viewport().installEventFilter(self)
        layout.addWidget(self.scroll_area, stretch=1)

        navigation = QHBoxLayout()
        self.previous_button = QPushButton("Previous Page")
        self.previous_button.clicked.connect(self.previous_page)
        self.next_button = QPushButton("Next Page")
        self.next_button.clicked.connect(self.next_page)
        self.page_count = QLabel()
        self.page_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        navigation.addWidget(self.previous_button)
        navigation.addWidget(self.page_count, stretch=1)
        navigation.addWidget(self.next_button)
        layout.addLayout(navigation)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.update_page()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.scroll_area.viewport() and event.type() == QEvent.Type.Wheel:
            if event.angleDelta().y() < 0:
                self.next_page()
            else:
                self.previous_page()
            return True
        return super().eventFilter(watched, event)

    def previous_page(self) -> None:
        if self.page_index > 0:
            self.page_index -= 1
            self.update_page()

    def next_page(self) -> None:
        if self.page_index < len(self.pages) - 1:
            self.page_index += 1
            self.update_page()

    def update_page(self) -> None:
        if not self.pages:
            self.page_label.setText("No preview pages")
            self.page_count.setText("0 / 0")
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        page = self.pages[self.page_index]
        self.page_label.setPixmap(page)
        self.page_label.resize(page.size())
        self.page_count.setText(f"{self.page_index + 1} / {len(self.pages)}")
        self.previous_button.setEnabled(self.page_index > 0)
        self.next_button.setEnabled(self.page_index < len(self.pages) - 1)


class ManualTuningDialog(QDialog):
    def __init__(
        self,
        plan_item: AnalysisPlanItem,
        parameters: AnalysisParameters,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.plan_item = plan_item
        self.current_analysis: Analysis | None = None

        self.setWindowTitle(f"Manual Tuning - {plan_item.image_name}")
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

    def parameters(self) -> AnalysisParameters:
        return AnalysisParameters(
            beam_threshold=self.beam_threshold.value(),
            ball_sensitivity=self.ball_sensitivity.value(),
            pixel_size_mm=self.pixel_size.value(),
            beam_size_px=optional_spin_value(self.beam_size),
            target_size_px=optional_spin_value(self.target_size),
        )

    def reanalyze(self) -> None:
        try:
            self.current_analysis = analyze_image(self.plan_item.image_path, self.parameters())
        except Exception as exc:
            self.current_analysis = None
            self.preview.setText(str(exc))
            self.status_label.setText("Analysis failed")
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
    widths = [44, 78, 120, 76, 64, 64, 86, 66, 78, 58]
    for column, width in enumerate(widths):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(column, width)
    header.setStretchLastSection(False)


def optional_spin_value(spinbox: QSpinBox) -> int | None:
    value = spinbox.value()
    return None if value == spinbox.minimum() else value


def optional_parameter_text(value: int | None) -> str:
    return "auto" if value is None else str(value)


def status_text(succeeded: bool | int, dx_mm: float | str | None, dy_mm: float | str | None) -> str:
    if not succeeded:
        return "NG"
    try:
        dx = float(dx_mm)
        dy = float(dy_mm)
    except (TypeError, ValueError):
        return "NG"
    return "OK" if abs(dx) <= 1.0 and abs(dy) <= 1.0 else "NG"


def history_row_dict(row) -> dict[str, str]:
    status = status_text(row["succeeded"], row["dx_mm"], row["dy_mm"])
    return {
        "session_id": str(row["session_id"]),
        "series_name": row["series_name"] or row["analyzed_at"],
        "analyzed_at": row["analyzed_at"],
        "machine": row["machine"] or "",
        "inspection_type": row["inspection_type"] or "",
        "image_name": row["image_name"] or "",
        "condition_label": row["condition_label"] or "",
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
        return datetime.fromisoformat(value).strftime("%m/%d %H:%M")
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
