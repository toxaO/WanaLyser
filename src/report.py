from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPageLayout, QPageSize, QPainter, QPdfWriter, QPen, QPixmap

from database import connect_database, init_db


@dataclass(frozen=True)
class ReportPoint:
    analyzed_at: str
    image_name: str
    condition_label: str
    dx_mm: float
    dy_mm: float
    distance_mm: float
    gantry_angle: float | None
    collimator_angle: float | None
    couch_angle: float | None


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
        for condition_label, points in grouped.items():
            if not first_page:
                writer.newPage()
            first_page = False
            draw_condition_page(painter, writer, condition_label, points, machine_name)
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
) -> list[QPixmap]:
    pages: list[QPixmap] = []
    page_rect = QRectF(0, 0, 794, 1123)
    for condition_label, points in grouped.items():
        pixmap = QPixmap(int(page_rect.width()), int(page_rect.height()))
        painter = QPainter(pixmap)
        try:
            draw_condition_content(painter, page_rect, condition_label, points, machine_name)
        finally:
            painter.end()
        pages.append(pixmap)
    return pages


def load_report_data(
    connection: sqlite3.Connection,
    machine_name: str | None = None,
    limit: int = 10,
) -> dict[str, list[ReportPoint]]:
    condition_rows = connection.execute(
        """
        SELECT DISTINCT analysis_results.note AS condition_label
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
    for condition_row in condition_rows:
        label = condition_row["condition_label"]
        rows = connection.execute(
            """
            SELECT
                analysis_results.analyzed_at,
                analysis_results.image_name,
                analysis_results.note AS condition_label,
                analysis_results.dx_mm,
                analysis_results.dy_mm,
                analysis_results.distance_mm,
                analysis_results.gantry_angle,
                analysis_results.collimator_angle,
                analysis_results.couch_angle
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
                condition_label=row["condition_label"],
                dx_mm=float(row["dx_mm"]),
                dy_mm=float(row["dy_mm"]),
                distance_mm=float(row["distance_mm"]),
                gantry_angle=row["gantry_angle"],
                collimator_angle=row["collimator_angle"],
                couch_angle=row["couch_angle"],
            )
            for row in reversed(rows)
        ]
        if points:
            grouped[label] = points
    return grouped


def draw_condition_page(
    painter: QPainter,
    writer: QPdfWriter,
    condition_label: str,
    points: list[ReportPoint],
    machine_name: str | None,
) -> None:
    page = writer.pageLayout().paintRectPixels(writer.resolution())
    draw_condition_content(painter, QRectF(page), condition_label, points, machine_name)


def draw_condition_content(
    painter: QPainter,
    page: QRectF,
    condition_label: str,
    points: list[ReportPoint],
    machine_name: str | None,
) -> None:
    margin = 48
    width = page.width()

    painter.fillRect(page, QColor("white"))
    painter.setPen(QColor("#222222"))
    painter.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
    draw_text(
        painter,
        QRectF(margin, margin, width - margin * 2, 32),
        f"WanaLyzer Report - {condition_label}",
    )

    painter.setFont(QFont("Helvetica", 10))
    subtitle = f"Machine: {machine_name or 'All'}    Points: {len(points)}"
    draw_text(painter, QRectF(margin, margin + 34, width - margin * 2, 22), subtitle)

    trend_rect = QRectF(margin, 120, width - margin * 2, 260)
    position_rect = QRectF(margin, 420, 300, 300)
    table_rect = QRectF(margin + 330, 420, width - margin * 2 - 330, 300)

    draw_trend_chart(painter, trend_rect, points)
    draw_position_chart(painter, position_rect, points)
    draw_value_table(painter, table_rect, points)


def draw_trend_chart(
    painter: QPainter,
    rect: QRectF,
    points: list[ReportPoint],
) -> None:
    draw_chart_frame(painter, rect, "dx/dy trend")
    if len(points) == 1:
        return

    max_abs = max(max(abs(point.dx_mm), abs(point.dy_mm)) for point in points)
    y_limit = max(1.0, math.ceil(max_abs * 10) / 10)
    draw_horizontal_axis(painter, rect, y_limit)
    draw_line_series(painter, rect, [point.dx_mm for point in points], y_limit, QColor("#1f77b4"))
    draw_line_series(painter, rect, [point.dy_mm for point in points], y_limit, QColor("#d62728"))

    painter.setFont(QFont("Helvetica", 9))
    painter.setPen(QColor("#1f77b4"))
    draw_text(painter, QRectF(rect.right() - 120, rect.top() + 8, 50, 16), "dx")
    painter.setPen(QColor("#d62728"))
    draw_text(painter, QRectF(rect.right() - 70, rect.top() + 8, 50, 16), "dy")

    painter.setPen(QColor("#444444"))
    for index, point in enumerate(points):
        x = series_x(rect, index, len(points))
        label = short_date(point.analyzed_at)
        painter.save()
        painter.translate(x - 8, rect.bottom() + 8)
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

    for index, point in enumerate(points):
        color = QColor("#444444") if index < len(points) - 1 else QColor("#d62728")
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
) -> None:
    latest = points[-1]
    rows = [
        ("Latest", short_date(latest.analyzed_at)),
        ("Image", latest.image_name),
        ("Gantry", value_text(latest.gantry_angle)),
        ("Collimator", value_text(latest.collimator_angle)),
        ("Couch", value_text(latest.couch_angle)),
        ("dx mm", value_text(latest.dx_mm)),
        ("dy mm", value_text(latest.dy_mm)),
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


def draw_chart_frame(painter: QPainter, rect: QRectF, title: str) -> None:
    painter.setPen(QPen(QColor("#dddddd"), 1))
    painter.setBrush(QColor("#fafafa"))
    painter.drawRect(rect)
    painter.setBrush(QColor("transparent"))
    painter.setPen(QColor("#222222"))
    painter.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
    draw_text(painter, QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 22), title)


def draw_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    flags: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
) -> None:
    painter.drawText(rect, int(flags), text)


def draw_horizontal_axis(painter: QPainter, rect: QRectF, y_limit: float) -> None:
    zero_y = series_y(rect, 0, y_limit)
    painter.setPen(QPen(QColor("#bbbbbb"), 1))
    painter.drawLine(QLineF(rect.left() + 28, zero_y, rect.right() - 18, zero_y))
    painter.setFont(QFont("Helvetica", 8))
    painter.setPen(QColor("#666666"))
    draw_text(painter, QRectF(rect.left() + 4, rect.top() + 30, 60, 14), f"+{y_limit:.1f}")
    draw_text(painter, QRectF(rect.left() + 4, zero_y - 7, 60, 14), "0")
    draw_text(painter, QRectF(rect.left() + 4, rect.bottom() - 28, 60, 14), f"-{y_limit:.1f}")


def draw_line_series(
    painter: QPainter,
    rect: QRectF,
    values: list[float],
    y_limit: float,
    color: QColor,
) -> None:
    painter.setPen(QPen(color, 2))
    for index in range(len(values) - 1):
        painter.drawLine(QLineF(
            series_x(rect, index, len(values)),
            series_y(rect, values[index], y_limit),
            series_x(rect, index + 1, len(values)),
            series_y(rect, values[index + 1], y_limit),
        ))
    painter.setBrush(color)
    painter.setPen(QtNoPen())
    for index, value in enumerate(values):
        x = series_x(rect, index, len(values))
        y = series_y(rect, value, y_limit)
        painter.drawEllipse(QRectF(x - 3, y - 3, 6, 6))
    painter.setBrush(QColor("transparent"))


def series_x(rect: QRectF, index: int, count: int) -> float:
    left = rect.left() + 36
    right = rect.right() - 24
    if count <= 1:
        return (left + right) / 2
    return left + (right - left) * index / (count - 1)


def series_y(rect: QRectF, value: float, y_limit: float) -> float:
    top = rect.top() + 42
    bottom = rect.bottom() - 36
    value = max(-y_limit, min(y_limit, value))
    return bottom - ((value + y_limit) / (2 * y_limit)) * (bottom - top)


def short_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%m/%d")
    except ValueError:
        return value[:10]


def value_text(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def QtNoPen():
    return QPen(Qt.PenStyle.NoPen)
