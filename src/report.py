from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter, QPen, QPixmap

from core import (
    AnalysisParameters,
    DEFAULT_BALL_SENSITIVITY,
    DEFAULT_BEAM_THRESHOLD,
    DEFAULT_PIXEL_SIZE_MM,
    analyze_image,
)
from database import connect_database, init_db


@dataclass(frozen=True)
class ReportPoint:
    analyzed_at: str
    image_name: str
    setup_label: str
    dx_mm: float
    dy_mm: float
    distance_mm: float
    gantry_angle: float | None
    collimator_angle: float | None
    couch_angle: float | None
    image_path: str = ""
    pixel_size_mm: float = DEFAULT_PIXEL_SIZE_MM
    beam_threshold: int = DEFAULT_BEAM_THRESHOLD
    ball_sensitivity: int = DEFAULT_BALL_SENSITIVITY
    beam_size_px: int | None = None
    target_size_px: int | None = None
    x_axis_label: str = ""
    y_axis_label: str = ""
    dx_positive_label: str = "+dx"
    dx_negative_label: str = "-dx"
    dy_positive_label: str = "+dy"
    dy_negative_label: str = "-dy"
    x_inverted: bool = False
    inspection_type: str = ""


@dataclass(frozen=True)
class ReportOrientation:
    x_axis: str
    y_axis: str
    left_label: str
    right_label: str
    up_label: str = "G"
    down_label: str = "T"
    invert_x: bool = False


def generate_pdf_report(
    db_path: str | Path,
    output_path: str | Path,
    machine_name: str | None = None,
    limit: int = 10,
) -> None:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    connection = connect_database(db_path)
    try:
        init_db(connection)
        grouped = load_report_data(connection, machine_name=machine_name, limit=limit)
    finally:
        connection.close()

    if not grouped:
        raise ValueError("No analysis results are available for report output.")

    write_grouped_pdf(grouped, output_path, machine_name)


def write_grouped_pdf(
    grouped: dict[str, list[ReportPoint]],
    output_path: str | Path,
    machine_name: str | None = None,
    show_mode_boundary: bool = False,
) -> None:
    if not grouped:
        raise ValueError("No analysis results are available for report output.")

    writer = QPdfWriter(str(output_path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Portrait)
    writer.setResolution(96)

    painter = QPainter(writer)
    try:
        first_page = True
        for setup_label, points in grouped.items():
            if not first_page:
                writer.newPage()
            first_page = False
            draw_setup_page(
                painter,
                writer,
                setup_label,
                points,
                machine_name,
                show_mode_boundary,
            )
    finally:
        painter.end()


def render_report_pages(
    db_path: str | Path,
    machine_name: str | None = None,
    limit: int = 10,
) -> list[QPixmap]:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    connection = connect_database(db_path)
    try:
        init_db(connection)
        grouped = load_report_data(connection, machine_name=machine_name, limit=limit)
    finally:
        connection.close()

    if not grouped:
        raise ValueError("No analysis results are available for report preview.")

    return render_grouped_report_pages(grouped, machine_name)


def render_grouped_report_pages(
    grouped: dict[str, list[ReportPoint]],
    machine_name: str | None = None,
    show_mode_boundary: bool = False,
) -> list[QPixmap]:
    pages: list[QPixmap] = []
    page_rect = QRectF(0, 0, 794, 1123)
    for setup_label, points in grouped.items():
        pixmap = QPixmap(int(page_rect.width()), int(page_rect.height()))
        painter = QPainter(pixmap)
        try:
            draw_setup_content(
                painter,
                page_rect,
                setup_label,
                points,
                machine_name,
                show_mode_boundary,
            )
        finally:
            painter.end()
        pages.append(pixmap)
    return pages


def load_report_data(
    connection: sqlite3.Connection,
    machine_name: str | None = None,
    limit: int = 10,
) -> dict[str, list[ReportPoint]]:
    setup_rows = connection.execute(
        """
        SELECT DISTINCT analysis_results.note AS setup_label
        FROM analysis_results
        JOIN sessions ON sessions.id = analysis_results.session_id
        LEFT JOIN machines ON machines.id = sessions.machine_id
        WHERE analysis_results.note IS NOT NULL
          AND (? IS NULL OR COALESCE(machines.name, sessions.machine_name) = ?)
        ORDER BY analysis_results.note
        """,
        (machine_name, machine_name),
    ).fetchall()

    grouped: dict[str, list[ReportPoint]] = {}
    for setup_row in setup_rows:
        label = setup_row["setup_label"]
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
            WHERE analysis_results.note = ?
              AND analysis_results.succeeded = 1
              AND (? IS NULL OR COALESCE(machines.name, sessions.machine_name) = ?)
            ORDER BY analysis_results.analyzed_at DESC, analysis_results.id DESC
            LIMIT ?
            """,
            (label, machine_name, machine_name, limit),
        ).fetchall()
        points = [
            ReportPoint(
                analyzed_at=row["analyzed_at"],
                image_name=row["image_name"],
                setup_label=row["setup_label"],
                dx_mm=float(row["dx_mm"]),
                dy_mm=float(row["dy_mm"]),
                distance_mm=float(row["distance_mm"]),
                gantry_angle=row["gantry_angle"],
                collimator_angle=row["collimator_angle"],
                couch_angle=row["couch_angle"],
                image_path=row["image_path"],
                pixel_size_mm=float(row["pixel_size_mm"]),
                beam_threshold=int(row["beam_threshold"]),
                ball_sensitivity=int(row["ball_sensitivity"]),
                beam_size_px=row["beam_size_px"],
                target_size_px=row["target_size_px"],
                x_axis_label=row["x_axis_label"] or "",
                y_axis_label=row["y_axis_label"] or "",
                dx_positive_label=row["dx_positive_label"] or "+dx",
                dx_negative_label=row["dx_negative_label"] or "-dx",
                dy_positive_label=row["dy_positive_label"] or "+dy",
                dy_negative_label=row["dy_negative_label"] or "-dy",
                x_inverted=bool(row["x_inverted"]),
                inspection_type=row["inspection_type"] or "",
            )
            for row in reversed(rows)
        ]
        if points:
            grouped[label] = points
    return grouped


def draw_setup_page(
    painter: QPainter,
    writer: QPdfWriter,
    setup_label: str,
    points: list[ReportPoint],
    machine_name: str | None,
    show_mode_boundary: bool,
) -> None:
    page = writer.pageLayout().paintRectPixels(writer.resolution())
    draw_setup_content(
        painter,
        QRectF(page),
        setup_label,
        points,
        machine_name,
        show_mode_boundary,
    )


def draw_setup_content(
    painter: QPainter,
    page: QRectF,
    setup_label: str,
    points: list[ReportPoint],
    machine_name: str | None,
    show_mode_boundary: bool = False,
) -> None:
    margin = 48
    width = page.width()

    painter.fillRect(page, QColor("white"))
    painter.setPen(QColor("#222222"))
    painter.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
    draw_text(
        painter,
        QRectF(margin, margin, width - margin * 2, 32),
        f"WanaLyzer Report - {setup_label}",
    )

    painter.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
    subtitle = f"Machine: {machine_name or 'All'}    Analyzed: {analysis_datetime_text(points[-1].analyzed_at)}"
    draw_text(painter, QRectF(margin, margin + 34, width - margin * 2, 24), subtitle)

    orientation = report_orientation(points[-1])
    chart_width = width - margin * 2
    trend_x_rect = QRectF(margin, 104, chart_width, 220)
    trend_y_rect = QRectF(margin, 326, chart_width, 220)
    distance_rect = QRectF(margin, 548, chart_width, 220)
    bottom_top = 798
    bottom_height = 245
    position_rect = QRectF(margin, bottom_top, 210, bottom_height)
    overlay_rect = QRectF(margin + 238, bottom_top, 210, bottom_height)
    table_rect = QRectF(margin + 476, bottom_top, chart_width - 476, bottom_height)

    draw_single_trend_chart(
        painter,
        trend_x_rect,
        f"dx trend  {orientation.x_axis}",
        [display_x(point, orientation) for point in points],
        points,
        QColor("#1f77b4"),
        y_min=-1.5,
        y_max=1.5,
        reference_lines=[-1.0, 0.0, 1.0],
        show_mode_boundary=show_mode_boundary,
    )
    draw_single_trend_chart(
        painter,
        trend_y_rect,
        f"dy trend  {orientation.y_axis}",
        [point.dy_mm for point in points],
        points,
        QColor("#d62728"),
        y_min=-1.5,
        y_max=1.5,
        reference_lines=[-1.0, 0.0, 1.0],
        show_mode_boundary=show_mode_boundary,
    )
    draw_single_trend_chart(
        painter,
        distance_rect,
        "distance trend",
        [point.distance_mm for point in points],
        points,
        QColor("#2ca02c"),
        y_min=-1.5,
        y_max=1.5,
        reference_lines=[-1.0, 0.0, 1.0],
        show_mode_boundary=show_mode_boundary,
    )
    draw_position_chart(painter, position_rect, points)
    draw_value_table(painter, table_rect, points, orientation)
    draw_focused_overlay(painter, overlay_rect, points[-1])


def draw_single_trend_chart(
    painter: QPainter,
    rect: QRectF,
    title: str,
    values: list[float],
    points: list[ReportPoint],
    color: QColor,
    y_min: float,
    y_max: float,
    reference_lines: list[float],
    show_mode_boundary: bool = False,
) -> None:
    draw_chart_frame(painter, rect, title)
    if not values:
        return

    draw_plot_background(painter, rect)
    draw_horizontal_guides(painter, rect, y_min, y_max, reference_lines)
    if show_mode_boundary:
        draw_mode_boundary_lines(painter, rect, points)
    draw_line_series(painter, rect, values, points, y_min, y_max, color)

    painter.setPen(QColor("#444444"))
    for index, label in enumerate(axis_labels(points)):
        x = series_x(rect, index, len(points))
        if index == 0:
            x += 12
        elif index == len(points) - 1:
            x -= 18
        painter.save()
        painter.translate(x - 8, rect.bottom() - 50)
        painter.rotate(60)
        draw_text(painter, QRectF(0, 0, 80, 14), label)
        painter.restore()


def draw_position_chart(
    painter: QPainter,
    rect: QRectF,
    points: list[ReportPoint],
) -> None:
    draw_chart_frame(painter, rect, "center position")
    max_abs = max(max(abs(point.dx_mm), abs(point.dy_mm)) for point in points)
    limit = max(1.0, math.ceil(max_abs * 10) / 10)

    center_x = rect.left() + rect.width() / 2
    center_y = rect.top() + rect.height() / 2
    scale = (min(rect.width(), rect.height()) * 0.42) / limit

    painter.setPen(QPen(QColor("#dddddd"), 1))
    painter.drawLine(QLineF(center_x, rect.top() + 28, center_x, rect.bottom() - 18))
    painter.drawLine(QLineF(rect.left() + 18, center_y, rect.right() - 18, center_y))
    painter.setPen(QPen(QColor("#cccccc"), 1))
    radius = scale
    painter.drawEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
    painter.setFont(QFont("Helvetica", 9))
    painter.setPen(QColor("#555555"))
    latest = points[-1]
    draw_text(painter, QRectF(center_x - 35, rect.top() + 30, 70, 16), latest.dy_positive_label or "+dy", Qt.AlignmentFlag.AlignCenter)
    draw_text(painter, QRectF(center_x - 35, rect.bottom() - 28, 70, 16), latest.dy_negative_label or "-dy", Qt.AlignmentFlag.AlignCenter)
    draw_text(painter, QRectF(rect.left() + 8, center_y - 8, 70, 16), latest.dx_negative_label or "-dx", Qt.AlignmentFlag.AlignCenter)
    draw_text(painter, QRectF(rect.right() - 78, center_y - 8, 70, 16), latest.dx_positive_label or "+dx", Qt.AlignmentFlag.AlignCenter)

    for index, point in enumerate(points):
        color = QColor("#1f77b4") if index < len(points) - 1 else QColor("#d62728")
        size = 5 if index < len(points) - 1 else 8
        x = center_x + point.dx_mm * scale
        y = center_y - point.dy_mm * scale
        painter.setPen(QtNoPen())
        painter.setBrush(color)
        painter.drawEllipse(QRectF(x - size / 2, y - size / 2, size, size))
    painter.setBrush(QColor("transparent"))


def draw_value_table(
    painter: QPainter,
    rect: QRectF,
    points: list[ReportPoint],
    orientation: ReportOrientation,
) -> None:
    latest = points[-1]
    rows = [
        ("Latest", short_date(latest.analyzed_at)),
        ("Image", latest.image_name),
        ("Gantry", value_text(latest.gantry_angle)),
        ("Collimator", value_text(latest.collimator_angle)),
        ("Couch", value_text(latest.couch_angle)),
        (signed_axis_label("dx", latest.dx_mm, latest.dx_positive_label, latest.dx_negative_label), value_text(display_x(latest, orientation))),
        (signed_axis_label("dy", latest.dy_mm, latest.dy_positive_label, latest.dy_negative_label), value_text(latest.dy_mm)),
        ("distance mm", value_text(latest.distance_mm)),
    ]

    painter.setPen(QColor("#222222"))
    painter.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
    draw_text(painter, QRectF(rect.left(), rect.top(), rect.width(), 24), "Latest value")
    painter.setFont(QFont("Helvetica", 10))
    row_height = 26
    top = rect.top() + 36
    for index, (label, value) in enumerate(rows):
        y = top + index * row_height
        painter.setPen(QColor("#dddddd"))
        painter.drawLine(QLineF(rect.left(), y + row_height - 4, rect.right(), y + row_height - 4))
        painter.setPen(QColor("#555555"))
        draw_text(painter, QRectF(rect.left(), y, 120, row_height), label)
        painter.setPen(QColor("#222222"))
        draw_text(painter, QRectF(rect.left() + 130, y, rect.width() - 130, row_height), value)


def draw_focused_overlay(
    painter: QPainter,
    rect: QRectF,
    point: ReportPoint,
) -> None:
    draw_chart_frame(painter, rect, "focused overlay")
    if not point.image_path:
        painter.setPen(QColor("#666666"))
        draw_text(painter, rect.adjusted(16, 36, -16, -16), "No image path is available.")
        return

    pixmap = focused_overlay_pixmap(point)
    if pixmap is None:
        painter.setPen(QColor("#666666"))
        draw_text(painter, rect.adjusted(16, 36, -16, -16), "Focused overlay could not be generated.")
        return

    image_rect = rect.adjusted(16, 42, -16, -16)
    scaled = pixmap.scaled(
        int(image_rect.width()),
        int(image_rect.height()),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = image_rect.left() + (image_rect.width() - scaled.width()) / 2
    y = image_rect.top() + (image_rect.height() - scaled.height()) / 2
    painter.drawPixmap(int(x), int(y), scaled)


def focused_overlay_pixmap(point: ReportPoint) -> QPixmap | None:
    path = Path(point.image_path)
    if not path.exists():
        return None
    try:
        analysis = analyze_image(
            path,
            AnalysisParameters(
                beam_threshold=point.beam_threshold,
                ball_sensitivity=point.ball_sensitivity,
                pixel_size_mm=point.pixel_size_mm,
                beam_size_px=point.beam_size_px,
                target_size_px=point.target_size_px,
            ),
        )
    except Exception:
        return None
    return pixmap_from_bgr(analysis.debug_images.focused_overlay)


def report_orientation(point: ReportPoint) -> ReportOrientation:
    if point.x_axis_label or point.y_axis_label:
        return orientation_from_labels(point)

    return ReportOrientation(
        x_axis="dx",
        y_axis="dy",
        left_label="-dx",
        right_label="+dx",
        up_label="+dy",
        down_label="-dy",
        invert_x=False,
    )


def orientation_from_labels(point: ReportPoint) -> ReportOrientation:
    x_axis = point.x_axis_label or "(-)270 <- -> 90(+)"
    y_axis = point.y_axis_label or "(-)T <- -> G(+)"
    left_label, right_label = horizontal_labels_from_axis(x_axis, point.x_inverted)
    return ReportOrientation(
        x_axis=x_axis,
        y_axis=y_axis,
        left_label=left_label,
        right_label=right_label,
        invert_x=point.x_inverted,
    )


def horizontal_labels_from_axis(axis_label: str, inverted: bool) -> tuple[str, str]:
    if "P" in axis_label and "A" in axis_label:
        left, right = "P", "A"
    elif "270" in axis_label and "90" in axis_label:
        left, right = "270", "90"
    else:
        left, right = "-", "+"
    if inverted:
        return right, left
    return left, right


def display_x(point: ReportPoint, orientation: ReportOrientation) -> float:
    return -point.dx_mm if orientation.invert_x else point.dx_mm


def pixmap_from_bgr(image) -> QPixmap:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    qimage = QImage(
        rgb.data,
        width,
        height,
        channels * width,
        QImage.Format.Format_RGB888,
    ).copy()
    return QPixmap.fromImage(qimage)


def draw_chart_frame(painter: QPainter, rect: QRectF, title: str) -> None:
    painter.setPen(QPen(QColor("#dddddd"), 1))
    painter.setBrush(QColor("#fafafa"))
    painter.drawRect(rect)
    painter.setBrush(QColor("transparent"))
    painter.setPen(QColor("#222222"))
    painter.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
    draw_text(painter, QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 22), title)


def draw_plot_background(painter: QPainter, rect: QRectF) -> None:
    plot_rect = QRectF(
        rect.left() + 28,
        rect.top() + 42,
        rect.width() - 46,
        rect.height() - 100,
    )
    painter.setPen(QtNoPen())
    painter.setBrush(QColor("white"))
    painter.drawRect(plot_rect)
    painter.setBrush(QColor("transparent"))


def draw_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    flags: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
) -> None:
    painter.drawText(rect, int(flags), text)


def draw_horizontal_guides(
    painter: QPainter,
    rect: QRectF,
    y_min: float,
    y_max: float,
    reference_lines: list[float],
) -> None:
    for value in reference_lines:
        if value < y_min or value > y_max:
            continue
        y = series_y(rect, value, y_min, y_max)
        color = QColor("#999999") if abs(value) == 1.0 else QColor("#bbbbbb")
        pen = QPen(color, 1)
        if abs(value) == 1.0:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QLineF(rect.left() + 28, y, rect.right() - 18, y))

    painter.setFont(QFont("Helvetica", 8))
    painter.setPen(QColor("#666666"))
    draw_text(painter, QRectF(rect.left() + 4, rect.top() + 30, 60, 14), value_text(y_max))
    if y_min < 0 < y_max:
        zero_y = series_y(rect, 0, y_min, y_max)
        draw_text(painter, QRectF(rect.left() + 4, zero_y - 7, 60, 14), "0")
    draw_text(painter, QRectF(rect.left() + 4, rect.bottom() - 56, 60, 14), value_text(y_min))


def draw_line_series(
    painter: QPainter,
    rect: QRectF,
    values: list[float],
    points: list[ReportPoint],
    y_min: float,
    y_max: float,
    color: QColor,
) -> None:
    painter.setPen(QPen(color, 2))
    for index in range(len(values) - 1):
        painter.drawLine(QLineF(
            series_x(rect, index, len(values)),
            series_y(rect, values[index], y_min, y_max),
            series_x(rect, index + 1, len(values)),
            series_y(rect, values[index + 1], y_min, y_max),
        ))
    painter.setBrush(color)
    painter.setPen(QtNoPen())
    for index, value in enumerate(values):
        x = series_x(rect, index, len(values))
        y = series_y(rect, value, y_min, y_max)
        if index < len(points) and points[index].inspection_type not in ("", "daily"):
            draw_double_circle_marker(painter, x, y, color)
        else:
            painter.drawEllipse(QRectF(x - 3, y - 3, 6, 6))
    painter.setBrush(QColor("transparent"))


def draw_double_circle_marker(painter: QPainter, x: float, y: float, color: QColor) -> None:
    painter.setBrush(QColor("transparent"))
    painter.setPen(QPen(color, 2))
    painter.drawEllipse(QRectF(x - 5, y - 5, 10, 10))
    painter.drawEllipse(QRectF(x - 2, y - 2, 4, 4))
    painter.setBrush(color)
    painter.setPen(QtNoPen())


def draw_mode_boundary_lines(
    painter: QPainter,
    rect: QRectF,
    points: list[ReportPoint],
) -> None:
    for index in range(1, len(points)):
        if points[index - 1].inspection_type in ("", "daily") and points[index].inspection_type not in ("", "daily"):
            x = (series_x(rect, index - 1, len(points)) + series_x(rect, index, len(points))) / 2
            pen = QPen(QColor("#777777"), 1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(QLineF(x, plot_top(rect), x, plot_bottom(rect)))


def series_x(rect: QRectF, index: int, count: int) -> float:
    left = rect.left() + 36
    right = rect.right() - 24
    if count <= 1:
        return (left + right) / 2
    return left + (right - left) * index / (count - 1)


def series_y(rect: QRectF, value: float, y_min: float, y_max: float) -> float:
    top = plot_top(rect)
    bottom = plot_bottom(rect)
    value = max(y_min, min(y_max, value))
    return bottom - ((value - y_min) / (y_max - y_min)) * (bottom - top)


def plot_top(rect: QRectF) -> float:
    return rect.top() + 42


def plot_bottom(rect: QRectF) -> float:
    return rect.bottom() - 58


def short_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%m/%d")
    except ValueError:
        return value[:10]


def axis_labels(points: list[ReportPoint]) -> list[str]:
    date_counts: dict[str, int] = {}
    labels: list[str] = []
    for point in points:
        label = short_date(point.analyzed_at)
        date_counts[label] = date_counts.get(label, 0) + 1
        count = date_counts[label]
        labels.append(label if count == 1 else f"{label}_({count})")
    return labels


def analysis_datetime_text(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y/%m/%d %H:%M")
    except ValueError:
        return value[:16]


def value_text(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def signed_axis_label(axis: str, value: float | None, positive_label: str, negative_label: str) -> str:
    if value is None:
        return f"{axis} axis mm"
    direction = positive_label if value >= 0 else negative_label
    return f"{axis} {direction} mm"


def QtNoPen():
    return QPen(Qt.PenStyle.NoPen)
