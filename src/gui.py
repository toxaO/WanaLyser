from __future__ import annotations

import csv
import signal
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import cv2
from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from setups import AnalysisSetup
from core import (
    Analysis,
    AnalysisParameters,
    DEFAULT_BALL_SENSITIVITY,
    DEFAULT_BEAM_THRESHOLD,
    DEFAULT_PIXEL_SIZE_MM,
    analyze_image,
    list_images,
    save_debug_output,
)
from database import (
    AnalysisMetadata,
    connect_database,
    create_session,
    count_machine_results,
    delete_machine_results,
    delete_setup_preset,
    get_setup,
    get_setup_preset,
    get_default_machine_name,
    get_setting,
    init_db,
    deactivate_setup,
    list_setups,
    list_setup_presets,
    list_setup_steps,
    list_machines,
    rename_machine_results,
    save_analysis_results,
    set_default_machine_name,
    set_setting,
    update_session_series,
    update_setup_by_id,
    upsert_setup,
)
from report import (
    ReportPoint,
    focused_overlay_pixmap,
    load_report_data,
    render_grouped_report_pages,
    write_grouped_pdf,
)
from workflow import AnalysisPlanItem, analyze_plan, build_analysis_plan_from_preset
from gui_config import (
    ANALYSE_DAILY_STYLE,
    ANALYSE_TEST_STYLE,
    APP_STYLE,
    DEFAULT_DB_PATH,
    DEFAULT_DEBUG_OUTPUT,
    DEFAULT_OK_THRESHOLD_MM,
    DEFAULT_PRESET_SETTING,
    INPUT_PATH_SETTING,
    LEGACY_OK_THRESHOLD_SETTING,
    MODE_WIDGET_SIZE,
    OK_THRESHOLD_SETTING,
    OUTPUT_PATH_SETTING,
    PRIMARY_BUTTON_STYLE,
    RESULT_TABLE_HEADERS,
    SERIES_PANEL_WIDTH,
    SETTING_PAGE_STYLE,
)
from gui_helpers import (
    analysis_setup_from_row,
    apply_status_style,
    compact_field,
    configure_result_table,
    delete_session_results,
    load_app_setting,
    load_recent_saved_series,
    ok_threshold_mm,
    one_decimal_text,
    optional_int_text,
    optional_parameter_text,
    optional_spin_value,
    overlay_analysis_text,
    overlay_unanalyzed_text,
    parse_datetime_or_none,
    pixmap_from_bgr,
    plan_item_with_setup,
    raise_error,
    report_point_from_row,
    RoundedComboBox,
    same_setup_angles,
    save_app_setting,
    series_display_name,
    show_error,
    status_text,
    table_text,
    value_label,
    value_text,
)
from gui_dialogs import (
    ManualTuningDialog,
    PagePreviewDialog,
    ParamTestDialog,
    PresetEditorDialog,
)
from gui_models import AnalysisSeries


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WanaLyzer")
        self.resize(1070, 700)

        root = QWidget()
        root.setObjectName("AppRoot")
        root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.root = root
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setObjectName("MainTabs")
        self.tabs.tabBar().setDrawBase(False)
        self.daily_tab = DailyTab()
        self.manage_tab = ManageTab(self.refresh_analysis_tabs)
        self.tabs.addTab(self.daily_tab, "Analyse")
        self.tabs.addTab(self.manage_tab, "Setting")
        self.tabs.setProperty("analysisMode", "daily")
        self.tabs.setProperty("pageKind", "daily")
        self.root.setProperty("pageKind", "daily")
        self.tabs.currentChanged.connect(self.update_tab_page_style)
        layout.addWidget(self.tabs, stretch=1)

    def refresh_analysis_tabs(self) -> None:
        self.daily_tab.refresh_database_options()

    def update_tab_page_style(self) -> None:
        if self.tabs.currentWidget() is self.manage_tab:
            page_kind = "setting"
        else:
            page_kind = "test" if self.daily_tab.analysis_mode == "simple_test" else "daily"
        self.root.setProperty("pageKind", page_kind)
        self.tabs.setProperty("pageKind", page_kind)
        self.root.style().unpolish(self.root)
        self.root.style().polish(self.root)
        self.root.update()
        self.tabs.style().unpolish(self.tabs)
        self.tabs.style().polish(self.tabs)
        self.tabs.tabBar().style().unpolish(self.tabs.tabBar())
        self.tabs.tabBar().style().polish(self.tabs.tabBar())
        self.tabs.update()


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
        self.updating_series_list = False
        self.create_preview_series_on_plan_load = False
        self.suppress_plan_load = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)
        self.settings_group = self.build_settings_group(default_image_path)
        layout.addWidget(self.settings_group)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.build_table_group())
        splitter.addWidget(self.build_preview_group())
        splitter.setSizes([820, 240])
        layout.addWidget(splitter, stretch=1)

        self.refresh_database_options()
        self.suppress_plan_load = False

    def build_settings_group(self, default_image_path: str) -> QWidget:
        group = QFrame()
        group.setObjectName("SettingsSection")
        group.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        self.add_settings_leading_widgets(layout)
        layout.addSpacing(12)

        self.input_default_path = load_app_setting(INPUT_PATH_SETTING, default_image_path)
        self.image_path = QLineEdit()
        self.image_path.setMinimumWidth(60)
        self.image_path.editingFinished.connect(self.input_path_edited)
        image_button = QPushButton("Browse")
        image_button.clicked.connect(self.browse_images)
        input_label = QLabel("Input")
        input_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(input_label)
        layout.addWidget(self.image_path, stretch=1)
        layout.addWidget(image_button)
        layout.addSpacing(12)

        self.output_path = QLineEdit(load_app_setting(OUTPUT_PATH_SETTING, str(DEFAULT_DEBUG_OUTPUT)))
        self.output_path.editingFinished.connect(self.output_path_edited)

        self.machine_combo = RoundedComboBox()
        self.machine_combo.setEditable(True)
        self.machine_combo.setMinimumWidth(148)
        self.machine_combo.setMaximumWidth(200)
        self.machine_combo.currentTextChanged.connect(self.machine_selection_changed)
        layout.addWidget(self.machine_combo)

        self.inspection_type = RoundedComboBox()
        self.inspection_type.setEditable(True)
        self.inspection_type.addItems(["daily", "temporary", "post_adjustment"])
        self.inspection_type.setCurrentText(self.default_inspection)
        self.inspection_type.setMinimumWidth(110)
        self.inspection_type.setMaximumWidth(150)
        if self.show_inspection:
            layout.addWidget(compact_field("Inspection", self.inspection_type))

        self.preset_combo = RoundedComboBox()
        self.preset_combo.currentTextChanged.connect(self.load_plan_preview)
        self.preset_combo.setMinimumWidth(110)
        self.preset_combo.setMaximumWidth(150)
        preset_label = QLabel("Preset")
        layout.addWidget(preset_label)
        layout.addWidget(self.preset_combo)
        layout.addSpacing(12)

        self.analyze_button = QPushButton("Analyse")
        self.analyze_button.setObjectName("primaryButton")
        self.analyze_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.analyze_button.clicked.connect(self.analyze_clicked)
        self.output_count = QSpinBox()
        self.output_count.setRange(1, 50)
        self.output_count.setValue(15)
        self.output_count.setMinimumWidth(64)
        self.output_count_widget = compact_field("Recent", self.output_count)
        self.output_count_widget.setVisible(False)
        self.analyze_button.setMinimumSize(max(96, self.analyze_button.sizeHint().width()), 32)
        layout.addWidget(self.analyze_button)

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
        self.series_panel.setObjectName("SeriesPanel")
        self.series_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.series_panel.setFrameShadow(QFrame.Shadow.Plain)
        self.configure_series_panel_width(show_series_list)
        self.series_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        series_layout = QVBoxLayout(self.series_panel)
        series_layout.setContentsMargins(8, 8, 8, 8)
        series_layout.setSpacing(6)
        self.series_query_mode = RoundedComboBox()
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
        self.series_list = QTableWidget(0, 2)
        self.series_list.setHorizontalHeaderLabels(["Date", "Series"])
        self.series_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.series_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.series_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.series_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.series_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.series_list.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
            | QTableWidget.EditTrigger.SelectedClicked
        )
        self.series_list.itemChanged.connect(self.series_item_changed)
        self.series_list.setVisible(show_series_list)
        series_layout.addWidget(self.series_list, stretch=1)
        self.save_series_button = QPushButton("Series Save")
        self.save_series_button.setObjectName("seriesSaveButton")
        self.save_series_button.setVisible(show_series_list)
        self.save_series_button.setMinimumHeight(56)
        self.save_series_button.clicked.connect(self.save_selected_series)
        series_layout.addWidget(self.save_series_button)
        self.active_toggle_button = QPushButton("Active / Inactive")
        self.active_toggle_button.setVisible(show_series_list)
        self.active_toggle_button.clicked.connect(self.toggle_selected_series_active)
        series_layout.addWidget(self.active_toggle_button)
        self.remove_series_button = QPushButton("Series Delete")
        self.remove_series_button.setObjectName("seriesDeleteButton")
        self.remove_series_button.setVisible(show_series_list)
        self.remove_series_button.clicked.connect(self.remove_selected_series)
        series_layout.addWidget(self.remove_series_button)
        layout.addWidget(self.series_panel, stretch=1)

        table_group = QFrame()
        table_group.setObjectName("AnalysisTablePanel")
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setSpacing(6)
        self.table = QTableWidget(0, len(RESULT_TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(RESULT_TABLE_HEADERS)
        self.table.setAlternatingRowColors(True)
        configure_result_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.update_preview_from_selection)
        table_layout.addWidget(self.table)
        table_button_row = QHBoxLayout()
        table_button_row.setContentsMargins(0, 4, 0, 0)
        self.clear_table_button = QPushButton("Clear Table")
        self.clear_table_button.clicked.connect(self.clear_analysis_table)
        self.setup_review_button = QPushButton("Setup Review")
        self.setup_review_button.clicked.connect(self.setup_review_clicked)
        self.series_review_button = QPushButton("Series Review")
        self.series_review_button.clicked.connect(self.export_pdf_clicked)
        self.delete_row_button = QPushButton("Delete Row")
        self.delete_row_button.clicked.connect(self.delete_selected_analysis_row)
        self.delete_row_button.setVisible(False)
        self.csv_button = QPushButton("Export CSV")
        self.csv_button.clicked.connect(self.export_current_table_csv)
        table_button_row.addWidget(self.csv_button)
        table_button_row.addWidget(self.clear_table_button)
        table_button_row.addWidget(self.delete_row_button)
        table_button_row.addStretch()
        table_button_row.addWidget(self.setup_review_button)
        table_button_row.addWidget(self.series_review_button)
        table_layout.addLayout(table_button_row)
        layout.addWidget(table_group, stretch=5)
        return group

    def configure_series_panel_width(self, visible: bool) -> None:
        if visible:
            self.series_panel.setMinimumWidth(SERIES_PANEL_WIDTH)
            self.series_panel.setMaximumWidth(SERIES_PANEL_WIDTH + 110)
        else:
            self.series_panel.setMinimumWidth(0)
            self.series_panel.setMaximumWidth(0)

    def build_preview_group(self) -> QWidget:
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        image_group = QGroupBox("Analysed Images")
        image_layout = QVBoxLayout(image_group)
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
        image_layout.addWidget(self.preview, stretch=2)
        image_layout.addLayout(navigation)
        layout.addWidget(image_group, stretch=2)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(110)
        self.log_output.setFrameShape(QFrame.Shape.NoFrame)
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(4, 0, 4, 2)
        log_layout.setSpacing(0)
        log_layout.addWidget(self.log_output)
        layout.addWidget(log_group, stretch=1)
        return group

    def remove_selected_series(self) -> None:
        return

    def save_selected_series(self) -> bool:
        return False

    def series_item_changed(self, item: QTableWidgetItem) -> None:
        return

    def delete_selected_simple_row(self) -> None:
        return

    def delete_selected_analysis_row(self) -> None:
        self.delete_selected_simple_row()

    def setup_review_clicked(self) -> None:
        return

    def clear_analysis_table(self) -> None:
        self.current_series = None
        self.table.setRowCount(0)
        self.reset_preview()
        self.update_save_button_state()

    def reset_preview(self, message: str = "解析後、行を選択してください") -> None:
        self.preview.clear()
        self.preview.setText(message)

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
            preset_names = [preset["name"] for preset in presets]
            for preset in presets:
                self.preset_combo.addItem(preset["name"])
            if current_preset in preset_names:
                self.preset_combo.setCurrentText(current_preset)
            elif default_preset in preset_names:
                self.preset_combo.setCurrentText(default_preset)

            current_machine = self.machine_combo.currentText()
            self.machine_combo.clear()
            machine_names = [machine["name"] for machine in machines]
            for machine in machines:
                self.machine_combo.addItem(machine["name"])
            if current_machine in machine_names:
                self.machine_combo.setCurrentText(current_machine)
            elif default_machine in machine_names:
                self.machine_combo.setCurrentText(default_machine)
            elif machine_names:
                self.machine_combo.setCurrentText(machine_names[0])
            elif current_machine:
                self.machine_combo.setCurrentText(current_machine)
        finally:
            self.loading_options = False

        if not self.suppress_plan_load:
            self.load_plan_preview()
        self.update_save_button_state()

    def machine_selection_changed(self, *_args) -> None:
        if self.loading_options:
            return
        if hasattr(self, "load_recent_saved_series"):
            self.load_recent_saved_series()
        self.update_save_button_state()

    def browse_images(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Images", str(self.image_path_value()))
        if path:
            self.image_path.setText(path)
            self.input_default_path = path
            save_app_setting(INPUT_PATH_SETTING, path)
            self.create_preview_series_on_plan_load = True
            self.load_plan_preview()
            self.update_save_button_state()

    def browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Debug Output", self.output_path.text())
        if path:
            self.output_path.setText(path)
            save_app_setting(OUTPUT_PATH_SETTING, path)

    def input_path_edited(self) -> None:
        text = self.image_path.text().strip()
        if text:
            self.input_default_path = text
            save_app_setting(INPUT_PATH_SETTING, text)
        self.create_preview_series_on_plan_load = False
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
            name=self.series_name(plan),
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
            self.reset_preview()
            self.log(f"解析計画の読み込みに失敗しました: {exc}")
            self.update_save_button_state()
            self.update_analyse_button_state()
            return
        self.current_series = None
        self.render_plan_preview(self.loaded_plan)
        self.reset_preview()
        self.log(f"解析計画を読み込みました: {len(self.loaded_plan)} images.")
        self.update_save_button_state()
        self.update_analyse_button_state()

    def discard_current_unsaved_series(self) -> None:
        if self.current_series is not None and not self.current_series.saved and self.current_series.source != "history":
            if hasattr(self, "series") and self.current_series in self.series:
                self.series.remove(self.current_series)
                self.render_series_list()
        self.current_series = None

    def series_name(self, plan: list[AnalysisPlanItem]) -> str:
        image_dir = self.image_path_value().name or str(self.image_path_value())
        return image_dir

    def set_current_series(self, series: AnalysisSeries) -> None:
        self.current_series = series
        self.render_series(series)
        self.update_save_button_state()
        self.update_analyse_button_state()

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
                series_name=series.name,
            )
            save_analysis_results(connection, session_id, series.analyses, metadata)
            if series.started_at:
                update_session_series(connection, session_id, started_at=series.started_at, series_name=series.name)
                connection.commit()
            return session_id
        finally:
            connection.close()

    def update_save_button_state(self) -> None:
        if hasattr(self, "save_button"):
            can_save = (
                self.current_series is not None
                and not self.current_series.saved
                and bool(self.current_series.analyses)
            )
            self.save_button.setEnabled(can_save)
        self.update_analyse_button_state()

    def update_analyse_button_state(self) -> None:
        if not hasattr(self, "analyze_button"):
            return
        selected_history = self.current_series is not None and self.current_series.source == "history"
        self.analyze_button.setEnabled(not selected_history)

    def analysis_row_values(self, plan_item: AnalysisPlanItem, analysis: Analysis) -> list[str]:
        result = analysis.result
        return [
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

    def point_row_values(self, row: int, point: ReportPoint) -> list[str]:
        return [
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

    def plan_row_values(self, plan_item: AnalysisPlanItem) -> list[str]:
        parameters = plan_item.parameters
        return [
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
            optional_parameter_text(parameters.beam_size_px if parameters else None),
            optional_parameter_text(parameters.target_size_px if parameters else None),
            f"{parameters.pixel_size_mm:.4f}" if parameters else "",
            ("otsu" if parameters and parameters.beam_threshold == 0 else str(parameters.beam_threshold)) if parameters else "",
            str(parameters.ball_sensitivity) if parameters else "",
        ]

    def set_result_table_row_values(self, row: int, values: list[str]) -> None:
        for column, value in enumerate(values):
            table_item = QTableWidgetItem(value)
            if column == 0:
                table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if column == 3:
                apply_status_style(table_item, value)
            self.table.setItem(row, column, table_item)

    def setup_combo_for_plan_item(
        self,
        plan_item: AnalysisPlanItem,
        setups: list[AnalysisSetup],
        row: int,
    ) -> QComboBox:
        combo = RoundedComboBox()
        combo.addItem("", None)
        for setup in setups:
            combo.addItem(setup.name, setup)
        if plan_item.setup_label:
            combo.setCurrentText(plan_item.setup_label)
        combo.currentIndexChanged.connect(lambda _index, table_row=row: self.plan_setup_changed(table_row))
        return combo

    def render_series(self, series: AnalysisSeries) -> None:
        if series.points and not series.analyses:
            self.render_persisted_series(series)
            return
        if series.plan and not series.analyses:
            self.render_plan_preview(series.plan)
            return
        self.table.setRowCount(len(series.plan))
        for row, (plan_item, analysis) in enumerate(zip(series.plan, series.analyses)):
            self.set_result_table_row_values(row, self.analysis_row_values(plan_item, analysis))
        configure_result_table(self.table)
        if series.analyses:
            self.select_preview_row(0)

    def render_persisted_series(self, series: AnalysisSeries) -> None:
        self.table.setRowCount(len(series.points))
        for row, point in enumerate(series.points):
            self.set_result_table_row_values(row, self.point_row_values(row, point))
        configure_result_table(self.table)
        if series.points:
            self.select_preview_row(0)

    def render_plan_preview(self, plan: list[AnalysisPlanItem]) -> None:
        self.updating_plan_table = True
        self.table.setRowCount(len(plan))
        setups = self.available_setups()
        for row, plan_item in enumerate(plan):
            self.set_result_table_row_values(row, self.plan_row_values(plan_item))
            self.table.setCellWidget(row, 2, self.setup_combo_for_plan_item(plan_item, setups, row))
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
            self.reset_preview()
            return
        if hasattr(self, "series") and self.current_series in self.series:
            self.series.remove(self.current_series)
            self.render_series_list()
        self.current_series = None
        self.render_plan_preview(self.loaded_plan)
        self.reset_preview("setupが変更されたため解析結果をクリアしました。")

    def update_preview_from_selection(self) -> None:
        if self.current_series is None:
            row = self.selected_row()
            if row is not None and self.show_unanalyzed_plan_preview(row):
                return
            self.reset_preview()
            return
        row = self.selected_row()
        if row is None:
            self.reset_preview("行を選択してください")
            return
        if row < 0 or row >= len(self.current_series.analyses):
            if self.current_series.points and 0 <= row < len(self.current_series.points):
                pixmap = focused_overlay_pixmap(self.current_series.points[row])
                if pixmap is None:
                    self.reset_preview("プレビュー画像を生成できません")
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
            self.reset_preview("解析済みの行を選択してください")
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
                        series_name=series.name,
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
        return Path(self.image_path.text().strip() or self.input_default_path).expanduser()

    def output_path_value(self) -> Path:
        return Path(self.output_path.text()).expanduser()

    def machine_name(self) -> str | None:
        return self.machine_combo.currentText().strip() or None

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
            default_image_path="sample/set_01",
            show_inspection=False,
        )
        self.setObjectName("AnalysePage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.delete_row_button.setVisible(True)
        self.apply_mode_style()
        self.series_list.currentCellChanged.connect(lambda row, _column, _previous_row, _previous_column: self.select_series(row))
        self.configure_series_panel_width(True)
        self.series_list.setVisible(True)
        self.save_series_button.setVisible(True)
        self.remove_series_button.setVisible(True)
        self.active_toggle_button.setVisible(True)
        self.load_recent_saved_series()
        self.clear_analysis_table()
        self.update_series_buttons()

    def build_table_group(self) -> QWidget:
        return self.build_series_table_group(show_series_list=True)

    def add_settings_leading_widgets(self, layout: QHBoxLayout) -> None:
        self.mode_combo = RoundedComboBox()
        self.mode_combo.setFixedWidth(MODE_WIDGET_SIZE[0] - 40)
        self.mode_combo.addItem("Daily", "daily")
        self.mode_combo.addItem("Test", "simple_test")
        self.mode_combo.currentIndexChanged.connect(self.mode_changed)
        layout.addWidget(self.mode_combo)

    def mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        if mode == self.analysis_mode:
            return
        previous_mode = self.analysis_mode
        if not self.confirm_unsaved_before_mode_change():
            self.mode_combo.blockSignals(True)
            try:
                index = self.mode_combo.findData(previous_mode)
                if index >= 0:
                    self.mode_combo.setCurrentIndex(index)
            finally:
                self.mode_combo.blockSignals(False)
            return
        self.analysis_mode = str(mode)
        self.reset_temporary_modes()
        if self.analysis_mode == "daily":
            self.inspection_type.setCurrentText("daily")
            self.configure_series_panel_width(True)
            self.series_query_toggle.setVisible(True)
            self.series_list.setVisible(True)
            self.save_series_button.setVisible(True)
            self.remove_series_button.setVisible(True)
            self.active_toggle_button.setVisible(True)
            self.delete_row_button.setVisible(True)
            self.series_review_button.setEnabled(True)
            self.load_plan_preview()
            self.load_recent_saved_series()
            self.update_series_buttons()
            self.log("Daily modeを開始しました。")
        elif self.analysis_mode == "set_test":
            self.start_set_test_mode()
        elif self.analysis_mode == "simple_test":
            self.start_simple_test_mode()
        self.apply_mode_style()
        self.update_save_button_state()

    def apply_mode_style(self) -> None:
        mode = "test" if self.analysis_mode == "simple_test" else "daily"
        self.setProperty("mode", mode)
        self.setStyleSheet(ANALYSE_TEST_STYLE if self.analysis_mode == "simple_test" else ANALYSE_DAILY_STYLE)
        parent = self.parent()
        while parent is not None and not isinstance(parent, QTabWidget):
            parent = parent.parent()
        if isinstance(parent, QTabWidget):
            parent.setProperty("analysisMode", mode)
            if parent.currentWidget() is self:
                parent.setProperty("pageKind", mode)
                root = parent.parent()
                if root is not None:
                    root.setProperty("pageKind", mode)
                    root.style().unpolish(root)
                    root.style().polish(root)
                    root.update()
            parent.style().unpolish(parent)
            parent.style().polish(parent)
            parent.tabBar().style().unpolish(parent.tabBar())
            parent.tabBar().style().polish(parent.tabBar())
            parent.update()
        widgets = [self, *self.findChildren(QWidget)]
        for widget in widgets:
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def confirm_unsaved_before_mode_change(self) -> bool:
        unsaved = self.unsaved_analysis_series()
        if not unsaved:
            return True
        reply = QMessageBox.question(
            self,
            "未保存の解析結果",
            "未保存の解析結果があります。保存してからモードを変更しますか？",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        if reply == QMessageBox.StandardButton.No:
            return True
        for series in unsaved:
            self.current_series = series
            if not self.save_result_from_preview(series):
                return False
        return True

    def unsaved_analysis_series(self) -> list[AnalysisSeries]:
        candidates: list[AnalysisSeries] = []
        if self.current_series is not None:
            candidates.append(self.current_series)
        candidates.extend(getattr(self, "series", []))
        unique: list[AnalysisSeries] = []
        for series in candidates:
            if series in unique:
                continue
            if series.source == "history" or series.saved:
                continue
            if not series.analyses:
                continue
            unique.append(series)
        return unique

    def reset_temporary_modes(self) -> None:
        self.series.clear()
        self.series_list.setRowCount(0)
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
        self.reset_preview()

    def start_set_test_mode(self) -> None:
        self.temp_mode_active = True
        self.inspection_type.setCurrentText("temporary")
        self.series_review_button.setEnabled(True)
        self.configure_series_panel_width(True)
        self.series_query_toggle.setVisible(True)
        self.series_list.setVisible(True)
        self.remove_series_button.setVisible(True)
        self.active_toggle_button.setVisible(True)
        self.delete_row_button.setVisible(False)
        self.update_set_test_series_buttons()
        self.render_plan_preview(self.loaded_plan)
        self.log("Set Test modeを開始しました。")

    def start_simple_test_mode(self) -> None:
        self.temp_mode_active = False
        self.inspection_type.setCurrentText("simple_test")
        self.series_review_button.setEnabled(False)
        self.delete_row_button.setVisible(True)
        self.delete_row_button.setEnabled(True)
        self.series_query_toggle.setChecked(False)
        self.series_query_toggle.setVisible(False)
        self.series_query_frame.setVisible(False)
        self.series_list.setVisible(False)
        self.save_series_button.setVisible(False)
        self.remove_series_button.setVisible(False)
        self.active_toggle_button.setVisible(False)
        self.configure_series_panel_width(False)
        self.loaded_plan = []
        self.simple_series.plan = []
        self.simple_series.analyses = []
        self.simple_analysis_by_row = {}
        self.simple_loaded_inputs = []
        self.clear_analysis_table()
        self.load_plan_preview()
        self.log("Test modeを開始しました。")

    def load_plan_preview(self) -> None:
        if getattr(self, "analysis_mode", "daily") == "simple_test":
            self.append_simple_images_from_input()
            return
        show_preview_series = self.create_preview_series_on_plan_load
        self.create_preview_series_on_plan_load = False
        super().load_plan_preview()
        if hasattr(self, "series_list") and self.analysis_mode in ("daily", "set_test"):
            if show_preview_series:
                self.show_unanalyzed_series_for_loaded_plan()
            else:
                self.remove_unanalyzed_preview_series()
                self.render_series_list()
                self.set_series_current_row(-1)

    def analyze_clicked(self) -> None:
        if self.current_series is not None and self.current_series.source == "history":
            return
        if self.analysis_mode == "simple_test":
            self.analyze_simple_clicked()
            return
        super().analyze_clicked()

    def clear_analysis_table(self) -> None:
        super().clear_analysis_table()
        if hasattr(self, "series_list"):
            self.series_list.blockSignals(True)
            self.set_series_current_row(-1)
            self.series_list.blockSignals(False)
            self.update_series_buttons()

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
        self.update_analyse_button_state()

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
            analysis_setup_from_row(step)
            for step in steps
        ]

    def after_analysis(self, series: AnalysisSeries) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            self.current_series = series
            super().after_analysis(series)
            return
        self.remove_unanalyzed_preview_series()
        self.series.insert(0, series)
        self.series = self.series[:10]
        self.render_series_list()
        self.set_series_current_row(0)
        self.update_series_buttons()
        self.log(f"解析シリーズに追加しました: {series.name}")

    def remove_unanalyzed_preview_series(self) -> None:
        self.series = [series for series in self.series if series.source != "preview"]

    def show_unanalyzed_series_for_loaded_plan(self) -> None:
        self.remove_unanalyzed_preview_series()
        if not self.loaded_plan:
            self.render_series_list()
            self.set_series_current_row(-1)
            return
        series = AnalysisSeries(
            name=self.series_name(self.loaded_plan),
            plan=self.loaded_plan,
            analyses=[],
            inspection_type=self.inspection_type.currentText(),
            machine_name=self.machine_name(),
            saved=False,
            started_at="",
            source="preview",
        )
        self.series.insert(0, series)
        self.current_series = series
        self.render_series_list()
        self.set_series_current_row(0)

    def render_simple_table(self) -> None:
        self.updating_plan_table = True
        self.table.setRowCount(len(self.loaded_plan))
        setups = self.available_setups()
        for row, plan_item in enumerate(self.loaded_plan):
            analysis = self.simple_analysis_by_row.get(row)
            if analysis is None:
                values = self.plan_row_values(plan_item)
            else:
                values = self.analysis_row_values(plan_item, analysis)
            self.set_result_table_row_values(row, values)
            self.table.setCellWidget(row, 2, self.setup_combo_for_plan_item(plan_item, setups, row))
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
        self.reset_preview("setupが変更されたため、この行の解析結果をクリアしました。")

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
            self.reset_preview()

    def delete_selected_analysis_row(self) -> None:
        if self.analysis_mode == "simple_test":
            self.delete_selected_simple_row()
            return
        if self.analysis_mode != "daily":
            return
        self.delete_selected_daily_row()

    def delete_selected_daily_row(self) -> None:
        series = self.selected_series()
        row = self.selected_row()
        if series is None:
            self.delete_loaded_plan_row(row)
            return
        if series.saved or series.source == "history":
            show_error(self, "行削除エラー", ValueError("保存済みseriesの行は削除できません。"))
            return
        if row is None or row < 0 or row >= len(series.plan):
            show_error(self, "行削除エラー", ValueError("削除する行を選択してください。"))
            return
        del series.plan[row]
        if row < len(series.analyses):
            del series.analyses[row]
        series.plan = [
            replace(item, order=index + 1)
            for index, item in enumerate(series.plan)
        ]
        if series.source == "preview" or not series.analyses:
            self.loaded_plan = series.plan
        self.current_series = series
        self.render_series(series)
        if series.plan:
            self.select_preview_row(min(row, len(series.plan) - 1))
        else:
            self.reset_preview()
        self.update_series_buttons()
        self.log(f"Daily seriesから行を削除しました: {series.name}")

    def delete_loaded_plan_row(self, row: int | None) -> None:
        if row is None or row < 0 or row >= len(self.loaded_plan):
            show_error(self, "行削除エラー", ValueError("削除する行を選択してください。"))
            return
        del self.loaded_plan[row]
        self.loaded_plan = [
            replace(item, order=index + 1)
            for index, item in enumerate(self.loaded_plan)
        ]
        self.render_plan_preview(self.loaded_plan)
        if self.loaded_plan:
            self.select_preview_row(min(row, len(self.loaded_plan) - 1))
        else:
            self.reset_preview()
        self.update_series_buttons()
        self.log("Dailyの未解析行を削除しました。")

    def update_preview_from_selection(self) -> None:
        if self.analysis_mode != "simple_test":
            super().update_preview_from_selection()
            return
        row = self.selected_row()
        if row is None:
            self.reset_preview("行を選択してください")
            return
        analysis = self.simple_analysis_by_row.get(row)
        if analysis is None or row >= len(self.loaded_plan):
            if self.show_unanalyzed_plan_preview(row):
                return
            self.reset_preview("解析済みの行を選択してください")
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
            self.current_series = None
            self.update_analyse_button_state()
            self.update_series_buttons()
            return
        self.set_current_series(self.series[row])
        self.update_series_buttons()

    def update_series_buttons(self) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            return
        row = self.series_list.currentRow()
        has_selection = 0 <= row < len(self.series)
        can_save = has_selection and bool(self.series[row].analyses) and not self.series[row].saved
        can_delete_row = (
            has_selection
            and self.series[row].source != "history"
            and not self.series[row].saved
            and bool(self.series[row].plan)
        ) or (
            self.analysis_mode == "daily"
            and not has_selection
            and bool(self.loaded_plan)
        )
        self.remove_series_button.setEnabled(has_selection)
        self.save_series_button.setEnabled(can_save)
        self.active_toggle_button.setEnabled(has_selection)
        self.delete_row_button.setEnabled(can_delete_row)
        self.update_analyse_button_state()

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
        self.series_list.removeRow(row)
        if self.series:
            next_row = min(row, len(self.series) - 1)
            self.set_series_current_row(next_row)
        else:
            self.current_series = None
            self.render_plan_preview(self.loaded_plan)
            self.reset_preview()
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
            self.reset_preview()

    def selected_series(self) -> AnalysisSeries | None:
        row = self.series_list.currentRow()
        if row < 0 or row >= len(self.series):
            return None
        return self.series[row]

    def series_label(self, series: AnalysisSeries) -> str:
        prefix = "" if series.saved else "* "
        inactive = "" if series.output_active else " [inactive]"
        return f"{prefix}{series.name}{inactive}"

    def series_date_label(self, series: AnalysisSeries) -> str:
        if not series.saved and not series.analyses and not series.points:
            return "未解析"
        return series_display_name(series.started_at) if series.started_at else ""

    def apply_series_item_style(self, series: AnalysisSeries, *items: QTableWidgetItem) -> None:
        background = QColor("#e7f4df" if series.saved else "#ffe9c7")
        foreground = QColor("#777777" if not series.output_active else "#20242a")
        for item in items:
            item.setBackground(background)
            item.setForeground(foreground)
        if not series.saved:
            font = items[0].font()
            font.setBold(True)
            for item in items:
                item.setFont(font)

    def render_series_list(self) -> None:
        current_series = self.selected_series()
        self.updating_series_list = True
        self.series_list.blockSignals(True)
        self.series_list.setRowCount(len(self.series))
        for row, series in enumerate(self.series):
            date_item = QTableWidgetItem(self.series_date_label(series))
            name_item = QTableWidgetItem(series.name)
            self.apply_series_item_style(series, date_item, name_item)
            self.series_list.setItem(row, 0, date_item)
            self.series_list.setItem(row, 1, name_item)
        self.series_list.resizeColumnsToContents()
        self.series_list.blockSignals(False)
        self.updating_series_list = False
        if current_series in self.series:
            self.set_series_current_row(self.series.index(current_series))
        else:
            self.set_series_current_row(-1)
        self.update_series_buttons()

    def set_series_current_row(self, row: int) -> None:
        if row < 0 or row >= len(self.series):
            self.series_list.clearSelection()
            self.series_list.setCurrentCell(-1, -1)
            return
        self.series_list.setCurrentCell(row, 0)
        self.series_list.selectRow(row)

    def series_item_changed(self, item: QTableWidgetItem) -> None:
        if self.updating_series_list or self.analysis_mode not in ("daily", "set_test"):
            return
        row = item.row()
        column = item.column()
        if row < 0 or row >= len(self.series):
            return
        series = self.series[row]
        if column == 0:
            parsed = self.parse_series_datetime(item.text())
            if parsed is None:
                show_error(self, "日時エラー", ValueError("日時は YYYY/MM/DD HH:MM の形式で入力してください。"))
                self.reset_series_row(row)
                return
            series.started_at = parsed.isoformat(timespec="minutes")
            self.update_series_points(series)
            self.persist_series_metadata(series, started_at=series.started_at)
        elif column == 1:
            name = item.text().strip()
            if not name:
                show_error(self, "Seriesエラー", ValueError("series名を入力してください。"))
                self.reset_series_row(row)
                return
            series.name = name
            self.update_series_points(series)
            self.persist_series_metadata(series, series_name=series.name)
        self.series_list.resizeColumnsToContents()

    def parse_series_datetime(self, value: str) -> datetime | None:
        text = value.strip()
        for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
        parsed = parse_datetime_or_none(text)
        if parsed is None:
            return None
        return parsed.replace(second=0, microsecond=0)

    def reset_series_row(self, row: int) -> None:
        if row < 0 or row >= len(self.series):
            return
        series = self.series[row]
        self.updating_series_list = True
        self.series_list.blockSignals(True)
        try:
            date_item = self.series_list.item(row, 0)
            if date_item is not None:
                date_item.setText(self.series_date_label(series))
            name_item = self.series_list.item(row, 1)
            if name_item is not None:
                name_item.setText(series.name)
            if date_item is not None and name_item is not None:
                self.apply_series_item_style(series, date_item, name_item)
        finally:
            self.series_list.blockSignals(False)
            self.updating_series_list = False

    def persist_series_metadata(
        self,
        series: AnalysisSeries,
        started_at: str | None = None,
        series_name: str | None = None,
    ) -> None:
        if not series.saved or series.session_id is None:
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            update_session_series(
                connection,
                series.session_id,
                started_at=started_at,
                series_name=series_name,
            )
            connection.commit()
        except Exception as exc:
            show_error(self, "Series更新エラー", exc)
        finally:
            connection.close()

    def update_series_points(self, series: AnalysisSeries) -> None:
        if series.points:
            series.points = [
                replace(point, analyzed_at=series.started_at or point.analyzed_at, series_name=series.name)
                for point in series.points
            ]

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
        selected_machine = self.machine_name()
        current = [
            series
            for series in self.series
            if series.source != "history" and series.machine_name == selected_machine
        ]
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
            show_error(self, "保存エラー", ValueError("過去データはAnalyseタブでは保存できません。"))
            return False
        if not series.analyses:
            show_error(self, "保存エラー", ValueError("未解析seriesは保存できません。解析後に保存してください。"))
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
        self.set_series_current_row(0)
        return self.save_selected_series()

    def mark_series_saved(self, series: AnalysisSeries) -> None:
        super().mark_series_saved(series)
        if self.analysis_mode in ("daily", "set_test"):
            for row, item_series in enumerate(self.series):
                if item_series is series:
                    self.reset_series_row(row)
                    break
            self.update_series_buttons()

    def save_clicked(self) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            super().save_clicked()
            return
        self.save_selected_series()

    def setup_review_clicked(self) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            show_error(self, "プレビューエラー", ValueError("Setup Reviewできる解析結果がありません。"))
            return
        try:
            selected_point = self.selected_setup_review_point()
        except Exception as exc:
            show_error(self, "プレビューエラー", exc)
            return
        review_state: dict[str, object] = {"x_axis_mode": "series", "count": 10}

        def build_review(count: int) -> tuple[list[QPixmap], list[str]]:
            review_state["count"] = count
            grouped = self.setup_review_data(selected_point, count)
            review_state["grouped"] = grouped
            return (
                render_grouped_report_pages(
                    grouped,
                    self.machine_name(),
                    show_mode_boundary=False,
                    x_axis_mode=str(review_state["x_axis_mode"]),
                ),
                list(grouped.keys()),
            )

        def change_x_axis(mode: str) -> tuple[list[QPixmap], list[str]]:
            review_state["x_axis_mode"] = mode
            return build_review(int(review_state["count"]))

        try:
            pages, outline_titles = build_review(10)
        except Exception as exc:
            show_error(self, "プレビューエラー", exc)
            return
        PagePreviewDialog(
            "Setup Review",
            pages,
            outline_titles,
            self,
            export_pdf_handler=lambda: self.export_saved_pdf_from_preview(
                review_state["grouped"],
                x_axis_mode=str(review_state["x_axis_mode"]),
            ),
            show_save_result_button=False,
            review_count=10,
            count_changed_handler=build_review,
            review_x_axis_mode=str(review_state["x_axis_mode"]),
            x_axis_changed_handler=change_x_axis,
        ).exec()

    def export_pdf_clicked(self) -> None:
        if self.analysis_mode not in ("daily", "set_test"):
            super().export_pdf_clicked()
            return
        review_state: dict[str, object] = {"x_axis_mode": "series", "count": self.output_count.value()}

        def build_review(count: int) -> tuple[list[QPixmap], list[str]]:
            review_state["count"] = count
            series_list = self.saved_series_for_output(count)
            if series_list is None:
                return [], []
            if not series_list:
                raise ValueError("出力できる保存済みseriesがありません。")
            grouped = self.report_data_from_series_list(series_list)
            review_state["grouped"] = grouped
            return (
                render_grouped_report_pages(
                    grouped,
                    self.machine_name(),
                    show_mode_boundary=False,
                    x_axis_mode=str(review_state["x_axis_mode"]),
                ),
                list(grouped.keys()),
            )

        def change_x_axis(mode: str) -> tuple[list[QPixmap], list[str]]:
            review_state["x_axis_mode"] = mode
            return build_review(int(review_state["count"]))

        try:
            pages, outline_titles = build_review(self.output_count.value())
        except Exception as exc:
            show_error(self, "プレビューエラー", exc)
            return
        if not pages:
            return
        PagePreviewDialog(
            "Series Review",
            pages,
            outline_titles,
            self,
            export_pdf_handler=lambda: self.export_saved_pdf_from_preview(
                review_state["grouped"],
                x_axis_mode=str(review_state["x_axis_mode"]),
            ),
            show_save_result_button=False,
            review_count=self.output_count.value(),
            count_changed_handler=build_review,
            review_x_axis_mode=str(review_state["x_axis_mode"]),
            x_axis_changed_handler=change_x_axis,
        ).exec()

    def saved_series_for_output(self, count: int | None = None) -> list[AnalysisSeries] | None:
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
                "最新の解析結果が保存されていません。保存してSeries Reviewを続行しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return None
            self.current_series = selected
            if not self.save_result_from_preview(selected):
                return []
        limit = count if count is not None else self.output_count.value()
        return [
            series
            for series in self.series[selected_row:]
            if series.saved and series.output_active
        ][:limit]

    def export_saved_pdf_from_preview(
        self,
        grouped: dict[str, list[ReportPoint]],
        x_axis_mode: str = "series",
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
                x_axis_mode=x_axis_mode,
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

    def selected_setup_review_point(self) -> ReportPoint:
        series = self.current_series
        if series is None:
            raise ValueError("Setup Reviewする解析結果を選択してください。")
        row = self.selected_row()
        if row is None:
            raise ValueError("Setup Reviewする解析表の行を選択してください。")
        if series.points:
            if row < 0 or row >= len(series.points):
                raise ValueError("Setup Reviewできる行を選択してください。")
            return series.points[row]
        if row < 0 or row >= min(len(series.plan), len(series.analyses)):
            raise ValueError("Setup Reviewできる解析済み行を選択してください。")
        return self.report_point_from_analysis(
            series.plan[row],
            series.analyses[row],
            series.started_at or datetime.now().isoformat(timespec="seconds"),
            series.inspection_type,
            series.name,
        )

    def setup_review_data(self, selected_point: ReportPoint, count: int) -> dict[str, list[ReportPoint]]:
        label = selected_point.setup_label or selected_point.image_name
        points = self.load_matching_history_for_point(
            selected_point,
            self.machine_name(),
            count,
        )
        if selected_point not in points:
            points.append(selected_point)
        points = points[-count:]
        if not points:
            raise ValueError("Setup Reviewできる解析結果がありません。")
        return {label: points}

    def report_data_with_current_series(self, series: AnalysisSeries) -> dict[str, list[ReportPoint]]:
        if self.analysis_mode == "simple_test":
            return super().report_data_with_current_series(series)
        labels = self.current_preset_setup_labels()
        grouped: dict[str, list[ReportPoint]] = {label: [] for label in labels}
        selected_machine_series = [
            item
            for item in self.series
            if item.machine_name == self.machine_name()
        ][:10]
        for item in reversed(selected_machine_series):
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
            points.append(self.report_point_from_analysis(plan_item, analysis, analyzed_at, series.inspection_type, series.name))
        return points

    def report_point_from_analysis(
        self,
        plan_item: AnalysisPlanItem,
        analysis: Analysis,
        analyzed_at: str,
        inspection_type: str,
        series_name: str = "",
    ) -> ReportPoint:
        label = plan_item.setup_label or plan_item.image_name
        result = analysis.result
        return ReportPoint(
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
            inspection_type=inspection_type,
            series_name=series_name,
        )

    def load_matching_history_for_point(
        self,
        point: ReportPoint,
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
                    sessions.series_name,
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
                WHERE analysis_results.succeeded = 1
                  AND sessions.inspection_type = 'daily'
                  AND analysis_results.note = ?
                  AND analysis_results.analyzed_at <= ?
                  AND (? IS NULL OR sessions.machine_name = ?)
                  AND ((? IS NULL AND analysis_results.gantry_angle IS NULL) OR ABS(analysis_results.gantry_angle - ?) < 0.000001)
                  AND ((? IS NULL AND analysis_results.collimator_angle IS NULL) OR ABS(analysis_results.collimator_angle - ?) < 0.000001)
                  AND ((? IS NULL AND analysis_results.couch_angle IS NULL) OR ABS(analysis_results.couch_angle - ?) < 0.000001)
                ORDER BY analysis_results.analyzed_at DESC, analysis_results.id DESC
                LIMIT ?
                """,
                (
                    point.setup_label,
                    point.analyzed_at,
                    machine_name,
                    machine_name,
                    point.gantry_angle,
                    point.gantry_angle,
                    point.collimator_angle,
                    point.collimator_angle,
                    point.couch_angle,
                    point.couch_angle,
                    limit,
                ),
            ).fetchall()
        finally:
            connection.close()
        return [report_point_from_row(row) for row in reversed(rows)]

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
                    sessions.series_name,
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
                WHERE analysis_results.succeeded = 1
                  AND sessions.inspection_type = 'daily'
                  AND (? IS NULL OR sessions.machine_name = ?)
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
                        series_name=series.name,
                    )
                )
        return points[-limit:]

class ManageTab(QWidget):
    def __init__(self, on_changed) -> None:
        super().__init__()
        self.setObjectName("SettingPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(SETTING_PAGE_STYLE)
        self.on_changed = on_changed
        self.setup_edit_row: int | None = None
        self.setup_edit_mode: str | None = None
        self.selected_machine_name: str | None = None
        self.loading_setups = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)
        left = QWidget()
        left.setObjectName("SettingsPanel")
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

        self.machine_select = RoundedComboBox()
        self.machine_select.currentTextChanged.connect(self.select_machine)
        self.machine_name = QLineEdit()
        self.machine_save_button = QPushButton("Rename")
        self.machine_save_button.clicked.connect(self.save_machine)
        self.machine_delete_button = QPushButton("Delete")
        self.machine_delete_button.clicked.connect(self.delete_machine)
        self.default_machine_select = RoundedComboBox()
        self.default_machine_select.setEditable(True)
        self.default_machine_select.activated.connect(
            lambda _index: self.default_machine_changed(self.default_machine_select.currentText())
        )
        if self.default_machine_select.lineEdit() is not None:
            self.default_machine_select.lineEdit().editingFinished.connect(
                lambda: self.default_machine_changed(self.default_machine_select.currentText())
            )
        layout.addWidget(self.machine_select)
        machine_fields = QHBoxLayout()
        machine_fields.setSpacing(6)
        name_label = QLabel("Name")
        name_label.setObjectName("PlainLabel")
        name_label.setFixedWidth(44)
        machine_fields.addWidget(name_label)
        machine_fields.addWidget(self.machine_name, stretch=1)
        machine_fields.addWidget(self.machine_save_button)
        machine_fields.addWidget(self.machine_delete_button)
        layout.addLayout(machine_fields)
        default_row = QHBoxLayout()
        default_row.setSpacing(6)
        default_label = QLabel("default:")
        default_label.setObjectName("PlainLabel")
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
        self.preset_select = RoundedComboBox()
        self.preset_select.currentTextChanged.connect(self.update_preset_action_label)
        self.preset_edit_button = QPushButton("Register")
        self.preset_edit_button.clicked.connect(self.edit_selected_preset)
        self.preset_delete_button = QPushButton("Delete")
        self.preset_delete_button.clicked.connect(self.delete_preset)
        self.default_preset_select = RoundedComboBox()
        self.default_preset_select.currentTextChanged.connect(self.default_preset_changed)
        self.preset_select.setFixedHeight(self.preset_edit_button.sizeHint().height())
        preset_top.addWidget(self.preset_select, stretch=1)
        preset_top.addWidget(self.preset_edit_button)
        preset_top.addWidget(self.preset_delete_button)
        layout.addLayout(preset_top)
        default_row = QHBoxLayout()
        default_row.setSpacing(6)
        default_label = QLabel("default:")
        default_label.setObjectName("PlainLabel")
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
        label.setObjectName("PlainLabel")
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
        machine_names = [machine["name"] for machine in machines]
        for machine in machines:
            self.machine_select.addItem(machine["name"], machine["name"])
        if current_machine in machine_names:
            self.machine_select.setCurrentText(current_machine)
        elif default_machine in machine_names:
            self.machine_select.setCurrentText(default_machine)
        elif machine_names:
            self.machine_select.setCurrentText(machine_names[0])
        self.machine_select.blockSignals(False)
        self.default_machine_select.blockSignals(True)
        self.default_machine_select.clear()
        for machine in machines:
            self.default_machine_select.addItem(machine["name"], machine["name"])
        if default_machine in machine_names:
            self.default_machine_select.setCurrentText(default_machine)
        elif default_machine:
            self.default_machine_select.setEditText(default_machine)
        elif machine_names:
            self.default_machine_select.setCurrentText(machine_names[0])
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
        preset_names = [preset["name"] for preset in presets]
        for preset in presets:
            self.preset_select.addItem(preset["name"])
        if current in preset_names:
            self.preset_select.setCurrentText(current)
        self.preset_select.blockSignals(False)
        self.update_preset_action_label()
        self.default_preset_select.blockSignals(True)
        self.default_preset_select.clear()
        self.default_preset_select.addItem("")
        for preset in presets:
            self.default_preset_select.addItem(preset["name"])
        if default_preset in preset_names:
            self.default_preset_select.setCurrentText(default_preset)
        self.default_preset_select.blockSignals(False)
        self.ok_threshold.blockSignals(True)
        self.ok_threshold.setValue(ok_threshold)
        self.ok_threshold.blockSignals(False)

    def select_machine(self, *_args) -> None:
        selected = self.machine_select.currentText().strip()
        self.selected_machine_name = selected or None
        self.machine_name.setText(selected)
        self.machine_save_button.setEnabled(bool(selected))
        self.machine_delete_button.setEnabled(bool(selected))

    def update_preset_action_label(self, *_args) -> None:
        is_new = self.preset_select.currentText() == "New"
        self.preset_edit_button.setText("Register" if is_new else "Edit")
        self.preset_delete_button.setEnabled(not is_new)

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
        values = [
            "",
            "0",
            "0",
            "0",
            "+dx",
            "-dx",
            "+dy",
            "-dy",
            "auto",
            "auto",
            value_text(DEFAULT_PIXEL_SIZE_MM),
            str(DEFAULT_BEAM_THRESHOLD),
            str(DEFAULT_BALL_SENSITIVITY),
        ]
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
                pixel_size_mm=float(table_text(self.setup_table, row, 10) or DEFAULT_PIXEL_SIZE_MM),
                beam_threshold=int(float(table_text(self.setup_table, row, 11) or DEFAULT_BEAM_THRESHOLD)),
                ball_sensitivity=int(float(table_text(self.setup_table, row, 12) or DEFAULT_BALL_SENSITIVITY)),
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

    def save_machine(self) -> None:
        name = self.machine_name.text().strip()
        if not name:
            show_error(self, "装置エラー", ValueError("装置名を入力してください。"))
            return
        selected = (self.selected_machine_name or "").strip()
        if not selected:
            show_error(self, "装置エラー", ValueError("変更する装置名を選択してください。"))
            return
        if selected == name:
            return
        reply = QMessageBox.question(
            self,
            "装置名変更",
            f"{selected} の既存解析結果を {name} に一括変更しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            rename_machine_results(connection, selected, name)
            connection.commit()
        except Exception as exc:
            show_error(self, "装置エラー", exc)
            return
        finally:
            connection.close()
        self.refresh()
        self.machine_select.setCurrentText(name)
        self.select_machine()
        self.on_changed()

    def delete_machine(self) -> None:
        selected_name = (self.selected_machine_name or "").strip()
        if not selected_name:
            show_error(self, "装置削除エラー", ValueError("削除する装置を選択してください。"))
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            result_count = count_machine_results(connection, selected_name)
            reply = QMessageBox.question(
                self,
                "装置削除",
                f"{selected_name} の解析結果 {result_count} series を削除しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            delete_machine_results(connection, selected_name)
            default_machine = get_default_machine_name(connection)
            if default_machine == selected_name:
                remaining = [
                    machine["name"]
                    for machine in list_machines(connection)
                    if machine["name"] != selected_name
                ]
                set_default_machine_name(connection, remaining[0] if remaining else "machine1")
            connection.commit()
        except Exception as exc:
            show_error(self, "装置削除エラー", exc)
            return
        finally:
            connection.close()
        self.refresh()
        self.on_changed()

    def save_default_machine(self) -> None:
        name = self.machine_name.text().strip() or self.machine_select.currentText().strip()
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

    def delete_preset(self) -> None:
        name = self.preset_select.currentText().strip()
        if not name or name == "New":
            show_error(self, "Preset削除エラー", ValueError("削除するpresetを選択してください。"))
            return
        connection = connect_database(DEFAULT_DB_PATH)
        try:
            init_db(connection)
            preset = get_setup_preset(connection, name)
            if preset is None:
                raise ValueError("登録済みpresetを選択してください。")
            reply = QMessageBox.question(
                self,
                "Preset削除",
                f"{name} を削除しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            delete_setup_preset(connection, int(preset["id"]))
            remaining = [
                preset_row
                for preset_row in list_setup_presets(connection)
                if int(preset_row["id"]) != int(preset["id"])
            ]
            if (get_setting(connection, DEFAULT_PRESET_SETTING) or "") == name:
                set_setting(connection, DEFAULT_PRESET_SETTING, remaining[0]["name"] if remaining else "")
            connection.commit()
        except Exception as exc:
            show_error(self, "Preset削除エラー", exc)
            return
        finally:
            connection.close()
        self.refresh()
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


def run() -> int:
    app = QApplication([])
    app.setStyleSheet(APP_STYLE)
    signal.signal(signal.SIGINT, lambda *_args: app.quit())
    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(100)
    window = MainWindow()
    window.show()
    return app.exec()
