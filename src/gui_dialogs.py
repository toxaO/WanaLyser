from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core import Analysis, AnalysisParameters, analyze_image
from database import connect_database, get_setup_preset, init_db, list_setup_steps, upsert_setup_preset
from gui_config import DEFAULT_DB_PATH, INPUT_PATH_SETTING
from gui_helpers import (
    analysis_setup_from_row,
    compact_field,
    load_app_setting,
    optional_spin_value,
    pixmap_from_bgr,
    show_error,
    status_text,
    update_setup_preset_by_id,
    value_text,
)
from setups import AnalysisSetup, SetupPreset
from workflow import AnalysisPlanItem

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


