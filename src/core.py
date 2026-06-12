from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image


DEFAULT_PIXEL_SIZE_MM = 0.242
DEFAULT_BEAM_THRESHOLD = 0
DEFAULT_BALL_SENSITIVITY = 10
ALGORITHM_VERSION = "core-bright-blob-v1"
SUPPORTED_IMAGE_EXTENSIONS = {".bmp", ".png", ".tif", ".tiff"}


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def top_left(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def bottom_right(self) -> tuple[int, int]:
        return (self.x + self.width - 1, self.y + self.height - 1)


@dataclass(frozen=True)
class Circle:
    x: int
    y: int
    radius: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass(frozen=True)
class AnalysisParameters:
    beam_threshold: int = DEFAULT_BEAM_THRESHOLD
    ball_sensitivity: int = DEFAULT_BALL_SENSITIVITY
    pixel_size_mm: float = DEFAULT_PIXEL_SIZE_MM
    beam_size_px: int | None = None
    target_size_px: int | None = None


@dataclass(frozen=True)
class AnalysisResult:
    image_path: str
    image_name: str
    beam: Rect | None
    ball: Circle | None
    dx_mm: float | None
    dy_mm: float | None
    distance_mm: float | None
    angle_degrees: float | None
    parameters: AnalysisParameters

    @property
    def succeeded(self) -> bool:
        return self.dx_mm is not None and self.dy_mm is not None

    def to_row(self) -> dict[str, object]:
        return {
            "image_name": self.image_name,
            "image_path": self.image_path,
            "succeeded": self.succeeded,
            "beam_center_x": None if self.beam is None else self.beam.center[0],
            "beam_center_y": None if self.beam is None else self.beam.center[1],
            "ball_center_x": None if self.ball is None else self.ball.center[0],
            "ball_center_y": None if self.ball is None else self.ball.center[1],
            "dx_mm": self.dx_mm,
            "dy_mm": self.dy_mm,
            "distance_mm": self.distance_mm,
            "angle_degrees": self.angle_degrees,
            "beam_threshold": self.parameters.beam_threshold,
            "ball_sensitivity": self.parameters.ball_sensitivity,
            "pixel_size_mm": self.parameters.pixel_size_mm,
            "beam_size_px": self.parameters.beam_size_px,
            "target_size_px": self.parameters.target_size_px,
            "algorithm_version": ALGORITHM_VERSION,
        }


@dataclass(frozen=True)
class DebugImages:
    raw: np.ndarray
    gray: np.ndarray
    beam_binary: np.ndarray
    ball_edges: np.ndarray
    overlay: np.ndarray
    beam_binary_overlay: np.ndarray
    ball_edges_overlay: np.ndarray
    focused_overlay: np.ndarray


@dataclass(frozen=True)
class Analysis:
    result: AnalysisResult
    debug_images: DebugImages


class ImageAnalysisError(RuntimeError):
    pass


def list_images(path: str | Path) -> list[Path]:
    input_path = Path(path)
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise ImageAnalysisError(f"input path does not exist: {input_path}")

    images = [
        child
        for child in input_path.iterdir()
        if child.is_file() and child.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda p: p.name)


def analyze_path(
    path: str | Path,
    parameters: AnalysisParameters | None = None,
) -> list[Analysis]:
    return [analyze_image(image_path, parameters) for image_path in list_images(path)]


def analyze_image(
    image_path: str | Path,
    parameters: AnalysisParameters | None = None,
) -> Analysis:
    params = parameters or AnalysisParameters()
    path = Path(image_path)
    raw = load_image(path)
    gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)

    beam_binary = make_beam_binary(gray, params.beam_threshold)

    beam = detect_rect(beam_binary, params.beam_size_px)
    ball, ball_edges = detect_ball(gray, beam, params.ball_sensitivity, params.target_size_px)
    result = build_result(path, beam, ball, params)
    debug_images = build_debug_images(raw, gray, beam_binary, ball_edges, beam, ball)
    return Analysis(result=result, debug_images=debug_images)


def load_image(path: Path) -> np.ndarray:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ImageAnalysisError(f"unsupported image type: {path.suffix}")

    try:
        pil_image = Image.open(path).convert("RGB")
    except OSError as exc:
        raise ImageAnalysisError(f"failed to read image: {path}") from exc

    rgb = np.array(pil_image)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def make_beam_binary(gray: np.ndarray, threshold: int) -> np.ndarray:
    if threshold == 0:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    else:
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        binary = cv2.bitwise_not(binary)
    return binary


def detect_rect(binary: np.ndarray, expected_size_px: int | None = None) -> Rect | None:
    contour = find_best_rect_contour(binary, expected_size_px)
    if contour is None:
        return None
    x, y, width, height = cv2.boundingRect(contour)
    return Rect(x=x, y=y, width=width, height=height)


def detect_ball(
    gray: np.ndarray,
    beam: Rect | None,
    sensitivity: int,
    target_size_px: int | None = None,
) -> tuple[Circle | None, np.ndarray]:
    if beam is not None:
        blob_circle, blob_binary = detect_bright_blob_ball(gray, beam, target_size_px=target_size_px)
        if blob_circle is not None:
            return blob_circle, blob_binary

    blurred = cv2.medianBlur(gray, 5)
    edges = cv2.Canny(blurred, 50, 150)
    target_radius = None if target_size_px is None else max(1, int(round(target_size_px / 2)))
    min_radius = 3 if target_radius is None else max(1, int(round(target_radius * 0.5)))
    max_radius = 30 if target_radius is None else max(min_radius + 1, int(round(target_radius * 1.8)))
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=20,
        param1=50,
        param2=max(1, sensitivity),
        minRadius=min_radius,
        maxRadius=max_radius,
    )
    if circles is None:
        return None, edges

    candidates = [Circle(int(round(x)), int(round(y)), int(round(r))) for x, y, r in circles[0]]
    if beam is not None:
        candidates = [circle for circle in candidates if is_circle_inside_rect(circle, beam)]
        beam_center = beam.center
        candidates.sort(
            key=lambda circle: math.hypot(circle.x - beam_center[0], circle.y - beam_center[1])
        )
    else:
        image_center = (gray.shape[1] / 2, gray.shape[0] / 2)
        candidates.sort(
            key=lambda circle: math.hypot(circle.x - image_center[0], circle.y - image_center[1])
        )

    if not candidates:
        return None, edges
    return candidates[0], edges


def detect_bright_blob_ball(
    gray: np.ndarray,
    beam: Rect,
    margin: int = 10,
    target_size_px: int | None = None,
) -> tuple[Circle | None, np.ndarray]:
    crop = gray[beam.y : beam.y + beam.height, beam.x : beam.x + beam.width]
    if crop.size == 0:
        return None, np.zeros_like(gray)

    inner_margin = min(margin, max(0, min(crop.shape[:2]) // 4))
    inner = crop[
        inner_margin : crop.shape[0] - inner_margin,
        inner_margin : crop.shape[1] - inner_margin,
    ]
    if inner.size == 0:
        inner = crop
        inner_margin = 0

    thresholds = candidate_blob_thresholds(inner)
    candidates = []
    best_binary = np.zeros_like(gray)
    expected_diameter = target_size_px or 18
    expected_radius = max(1, expected_diameter / 2)
    min_diameter = max(3, int(round(expected_diameter * 0.45)))
    max_diameter = max(min_diameter + 1, int(round(expected_diameter * 1.8)))
    expected_area = math.pi * expected_radius * expected_radius
    min_area = max(10, expected_area * 0.25)
    max_area = max(min_area + 1, expected_area * 3.0)
    for threshold in thresholds:
        _, binary_inner = cv2.threshold(inner, threshold, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary_inner, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if not min_area <= area <= max_area:
                continue
            x, y, width, height = cv2.boundingRect(contour)
            if width < min_diameter or height < min_diameter:
                continue
            if width > max_diameter or height > max_diameter:
                continue
            aspect = width / height
            if not 0.6 <= aspect <= 1.6:
                continue

            (circle_x, circle_y), radius = cv2.minEnclosingCircle(contour)
            global_x = beam.x + inner_margin + circle_x
            global_y = beam.y + inner_margin + circle_y
            distance = math.hypot(global_x - beam.center[0], global_y - beam.center[1])
            radius_penalty = abs(radius - expected_radius)
            area_penalty = abs(area - expected_area) / max(1.0, expected_area / 4)
            score = distance + radius_penalty + area_penalty
            candidates.append((score, Circle(int(round(global_x)), int(round(global_y)), int(round(radius))), binary_inner))

    if not candidates:
        return None, best_binary

    _, circle, binary_inner = min(candidates, key=lambda item: item[0])
    debug_binary = np.zeros_like(gray)
    debug_binary[
        beam.y + inner_margin : beam.y + inner_margin + binary_inner.shape[0],
        beam.x + inner_margin : beam.x + inner_margin + binary_inner.shape[1],
    ] = binary_inner
    return circle, debug_binary


def candidate_blob_thresholds(image: np.ndarray) -> list[int]:
    otsu_threshold, _ = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    mean = float(image.mean())
    std = float(image.std())
    values = [
        int(round(otsu_threshold)),
        int(round(mean + 0.5 * std)),
        int(round(mean + 0.8 * std)),
        int(round(mean + 1.0 * std)),
        110,
        115,
        120,
        125,
    ]
    return sorted({max(1, min(254, value)) for value in values})


def is_circle_inside_rect(circle: Circle, rect: Rect) -> bool:
    return (
        rect.x <= circle.x <= rect.x + rect.width
        and rect.y <= circle.y <= rect.y + rect.height
    )


def find_best_rect_contour(binary: np.ndarray, expected_size_px: int | None = None) -> np.ndarray | None:
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    if expected_size_px is not None and expected_size_px > 0:
        def size_score(contour) -> float:
            x, y, width, height = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            expected_area = expected_size_px * expected_size_px
            return (
                abs(width - expected_size_px)
                + abs(height - expected_size_px)
                + abs(area - expected_area) / max(1, expected_size_px)
            )

        return min(contours, key=size_score)
    return max(contours, key=cv2.contourArea)


def build_result(
    image_path: Path,
    beam: Rect | None,
    ball: Circle | None,
    parameters: AnalysisParameters,
) -> AnalysisResult:
    dx_mm = None
    dy_mm = None
    distance_mm = None
    angle_degrees = None
    if beam is not None and ball is not None:
        dx_mm = (ball.center[0] - beam.center[0]) * parameters.pixel_size_mm
        dy_mm = (beam.center[1] - ball.center[1]) * parameters.pixel_size_mm
        distance_mm = math.hypot(dx_mm, dy_mm)
        angle_degrees = math.degrees(math.atan2(dy_mm, dx_mm))

    return AnalysisResult(
        image_path=str(image_path),
        image_name=image_path.name,
        beam=beam,
        ball=ball,
        dx_mm=dx_mm,
        dy_mm=dy_mm,
        distance_mm=distance_mm,
        angle_degrees=angle_degrees,
        parameters=parameters,
    )


def build_debug_images(
    raw: np.ndarray,
    gray: np.ndarray,
    beam_binary: np.ndarray,
    ball_edges: np.ndarray,
    beam: Rect | None,
    ball: Circle | None,
) -> DebugImages:
    overlay = raw.copy()
    beam_binary_overlay = cv2.cvtColor(beam_binary, cv2.COLOR_GRAY2BGR)
    ball_edges_overlay = cv2.cvtColor(ball_edges, cv2.COLOR_GRAY2BGR)

    draw_analysis(overlay, beam, ball)
    draw_analysis(beam_binary_overlay, beam, None)
    draw_analysis(ball_edges_overlay, None, ball)
    focused_overlay = crop_focus(overlay, beam, ball)

    return DebugImages(
        raw=raw,
        gray=gray,
        beam_binary=beam_binary,
        ball_edges=ball_edges,
        overlay=overlay,
        beam_binary_overlay=beam_binary_overlay,
        ball_edges_overlay=ball_edges_overlay,
        focused_overlay=focused_overlay,
    )


def draw_analysis(
    image: np.ndarray,
    beam: Rect | None,
    ball: Circle | None,
) -> None:
    if beam is not None:
        draw_dashed_rect(image, beam.top_left, beam.bottom_right, (0, 255, 0), thickness=1)
        cv2.line(image, beam.top_left, beam.bottom_right, (0, 255, 0), 1)
        cv2.line(image, (beam.x + beam.width, beam.y), (beam.x, beam.y + beam.height), (0, 255, 0), 1)

    if ball is not None:
        draw_dashed_circle(image, ball.center, ball.radius, (0, 0, 255), thickness=1, gap_degrees=18)
        cv2.line(image, (ball.x - ball.radius, ball.y), (ball.x + ball.radius, ball.y), (0, 0, 255), 1)
        cv2.line(image, (ball.x, ball.y - ball.radius), (ball.x, ball.y + ball.radius), (0, 0, 255), 1)


def draw_dashed_rect(
    image: np.ndarray,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int = 1,
    dash: int = 8,
    gap: int = 6,
) -> None:
    x1, y1 = top_left
    x2, y2 = bottom_right
    draw_dashed_line(image, (x1, y1), (x2, y1), color, thickness, dash, gap)
    draw_dashed_line(image, (x2, y1), (x2, y2), color, thickness, dash, gap)
    draw_dashed_line(image, (x2, y2), (x1, y2), color, thickness, dash, gap)
    draw_dashed_line(image, (x1, y2), (x1, y1), color, thickness, dash, gap)


def draw_dashed_line(
    image: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int,
    dash: int,
    gap: int,
) -> None:
    x1, y1 = start
    x2, y2 = end
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    step = dash + gap
    for offset in range(0, int(length), step):
        segment_end = min(offset + dash, length)
        sx = int(round(x1 + (x2 - x1) * offset / length))
        sy = int(round(y1 + (y2 - y1) * offset / length))
        ex = int(round(x1 + (x2 - x1) * segment_end / length))
        ey = int(round(y1 + (y2 - y1) * segment_end / length))
        cv2.line(image, (sx, sy), (ex, ey), color, thickness)


def draw_dashed_circle(
    image: np.ndarray,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    thickness: int = 1,
    dash_degrees: int = 10,
    gap_degrees: int = 8,
) -> None:
    if radius <= 0:
        return
    cx, cy = center
    step = dash_degrees + gap_degrees
    for start_angle in range(0, 360, step):
        end_angle = min(start_angle + dash_degrees, 360)
        points: list[tuple[int, int]] = []
        for angle in range(start_angle, end_angle + 1, 2):
            radians = math.radians(angle)
            points.append((
                int(round(cx + radius * math.cos(radians))),
                int(round(cy + radius * math.sin(radians))),
            ))
        for start, end in zip(points, points[1:]):
            cv2.line(image, start, end, color, thickness)


def crop_focus(
    image: np.ndarray,
    beam: Rect | None,
    ball: Circle | None,
    margin: int = 80,
) -> np.ndarray:
    height, width = image.shape[:2]
    boxes: list[tuple[int, int, int, int]] = []
    if beam is not None:
        boxes.append((beam.x, beam.y, beam.x + beam.width, beam.y + beam.height))
    if ball is not None:
        boxes.append(
            (
                ball.x - ball.radius,
                ball.y - ball.radius,
                ball.x + ball.radius,
                ball.y + ball.radius,
            )
        )
    if not boxes:
        return image.copy()

    left = max(0, min(box[0] for box in boxes) - margin)
    top = max(0, min(box[1] for box in boxes) - margin)
    right = min(width, max(box[2] for box in boxes) + margin)
    bottom = min(height, max(box[3] for box in boxes) + margin)
    return image[top:bottom, left:right].copy()


def save_debug_output(
    analyses: Iterable[Analysis],
    output_dir: str | Path,
    write_images: bool = True,
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []

    for analysis in analyses:
        result = analysis.result
        results.append(result.to_row())
        image_dir = out / Path(result.image_name).stem
        image_dir.mkdir(parents=True, exist_ok=True)

        write_json(image_dir / "result.json", result)
        if write_images:
            write_debug_images(image_dir, analysis.debug_images)

    write_csv(out / "results.csv", results)


def write_debug_images(output_dir: Path, debug_images: DebugImages) -> None:
    for name, image in asdict(debug_images).items():
        cv2.imwrite(str(output_dir / f"{name}.png"), image)


def write_json(path: Path, result: AnalysisResult) -> None:
    data = result.to_row()
    data["beam"] = None if result.beam is None else asdict(result.beam)
    data["ball"] = None if result.ball is None else asdict(result.ball)
    data["parameters"] = asdict(result.parameters)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "image_name",
        "image_path",
        "succeeded",
        "beam_center_x",
        "beam_center_y",
        "ball_center_x",
        "ball_center_y",
        "dx_mm",
        "dy_mm",
        "distance_mm",
        "angle_degrees",
        "beam_threshold",
        "ball_sensitivity",
        "pixel_size_mm",
        "beam_size_px",
        "target_size_px",
        "algorithm_version",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def format_result_line(result: AnalysisResult) -> str:
    if not result.succeeded:
        return f"{result.image_name}: failed"
    return (
        f"{result.image_name}: "
        f"dx={result.dx_mm:.3f} mm, "
        f"dy={result.dy_mm:.3f} mm, "
        f"distance={result.distance_mm:.3f} mm, "
        f"angle={result.angle_degrees:.1f} deg"
    )
