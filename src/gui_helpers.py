from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListView,
    QMessageBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from core import (
    Analysis,
    AnalysisParameters,
    DEFAULT_BALL_SENSITIVITY,
    DEFAULT_BEAM_THRESHOLD,
    DEFAULT_PIXEL_SIZE_MM,
)
from database import (
    connect_database,
    get_setting,
    init_db,
    replace_setup_preset_steps,
    set_setting,
)
from gui_config import (
    DEFAULT_DB_PATH,
    DEFAULT_OK_THRESHOLD_MM,
    LEGACY_OK_THRESHOLD_SETTING,
    OK_THRESHOLD_SETTING,
)
from gui_models import AnalysisSeries
from report import ReportPoint
from setups import AnalysisSetup, SetupPreset
from workflow import AnalysisPlanItem


class RoundedComboBox(QComboBox):
    POPUP_STYLESHEET = """
        QAbstractItemView {
            color: #111827;
            background: #ffffff;
            selection-background-color: #dbeafe;
            selection-color: #111827;
            outline: 0;
        }
        QAbstractItemView::item {
            color: #111827;
            background: #ffffff;
            min-height: 24px;
        }
        QAbstractItemView::item:selected,
        QAbstractItemView::item:selected:active,
        QAbstractItemView::item:selected:!active,
        QAbstractItemView::item:hover {
            color: #111827;
            background: #dbeafe;
        }
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        view = QListView(self)
        view.setMouseTracking(True)
        view.setUniformItemSizes(False)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setStyleSheet(self.POPUP_STYLESHEET)
        self.setView(view)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QColor("#64748b"))
        painter.drawText(
            self.rect().adjusted(0, 0, -10, 0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "▼",
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
    title.setObjectName("PlainLabel")
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
    widths = [
        58,
        130,
        190,
        78,
        70,
        70,
        104,
        82,
        108,
        76,
        58,
        58,
        58,
        58,
        84,
        88,
        86,
        88,
        92,
    ]
    header.setMinimumSectionSize(56)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
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
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def analysis_setup_from_row(row) -> AnalysisSetup:
    keys = row.keys()
    return AnalysisSetup(
        name=row["name"] if "name" in keys else row["label"],
        gantry_angle=float(row["gantry_angle"]),
        collimator_angle=float(row["collimator_angle"]),
        couch_angle=float(row["couch_angle"]),
        dx_positive_label=row["dx_positive_label"] if "dx_positive_label" in keys else "+dx",
        dx_negative_label=row["dx_negative_label"] if "dx_negative_label" in keys else "-dx",
        dy_positive_label=row["dy_positive_label"] if "dy_positive_label" in keys else "+dy",
        dy_negative_label=row["dy_negative_label"] if "dy_negative_label" in keys else "-dy",
        field_size_px=setup_field_size_px(row, keys),
        target_size_px=row["target_size_px"] if "target_size_px" in keys else None,
        pixel_size_mm=(
            float(row["pixel_size_mm"])
            if "pixel_size_mm" in keys
            else DEFAULT_PIXEL_SIZE_MM
        ),
        beam_threshold=(
            int(row["beam_threshold"])
            if "beam_threshold" in keys
            else DEFAULT_BEAM_THRESHOLD
        ),
        ball_sensitivity=(
            int(row["ball_sensitivity"])
            if "ball_sensitivity" in keys
            else DEFAULT_BALL_SENSITIVITY
        ),
    )


def setup_field_size_px(row, keys) -> int | None:
    if "field_size_px" in keys:
        return row["field_size_px"]
    if "beam_size_px" in keys:
        return row["beam_size_px"]
    return None


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
    replace_setup_preset_steps(connection, preset_id, preset)


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
        pixel_size_mm=(
            float(row["pixel_size_mm"])
            if "pixel_size_mm" in keys
            else DEFAULT_PIXEL_SIZE_MM
        ),
        beam_threshold=(
            int(row["beam_threshold"])
            if "beam_threshold" in keys
            else DEFAULT_BEAM_THRESHOLD
        ),
        ball_sensitivity=(
            int(row["ball_sensitivity"])
            if "ball_sensitivity" in keys
            else DEFAULT_BALL_SENSITIVITY
        ),
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
