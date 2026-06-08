from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image


DEFAULT_PIXEL_SIZE_MM = 0.242
DEFAULT_BEAM_THRESHOLD = 0
DEFAULT_BALL_SENSITIVITY = 10
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

    beam = detect_rect(beam_binary)
    ball, ball_edges = detect_ball(gray, beam, params.ball_sensitivity)
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


def detect_rect(binary: np.ndarray) -> Rect | None:
    contour = find_largest_contour(binary)
    if contour is None:
        return None
    x, y, width, height = cv2.boundingRect(contour)
    return Rect(x=x, y=y, width=width, height=height)


def detect_ball(
    gray: np.ndarray,
    beam: Rect | None,
    sensitivity: int,
) -> tuple[Circle | None, np.ndarray]:
    blurred = cv2.medianBlur(gray, 5)
    edges = cv2.Canny(blurred, 50, 150)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=20,
        param1=50,
        param2=max(1, sensitivity),
        minRadius=3,
        maxRadius=30,
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


def is_circle_inside_rect(circle: Circle, rect: Rect) -> bool:
    return (
        rect.x <= circle.x <= rect.x + rect.width
        and rect.y <= circle.y <= rect.y + rect.height
    )


def find_largest_contour(binary: np.ndarray) -> np.ndarray | None:
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
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
        dx_mm = (beam.center[0] - ball.center[0]) * parameters.pixel_size_mm
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
        cv2.rectangle(image, beam.top_left, beam.bottom_right, (0, 255, 0), 2)
        center_x, center_y = int(beam.center[0]), int(beam.center[1])
        cv2.line(image, (center_x, beam.y), (center_x, beam.y + beam.height), (0, 255, 0), 1)
        cv2.line(image, (beam.x, center_y), (beam.x + beam.width, center_y), (0, 255, 0), 1)

    if ball is not None:
        cv2.circle(image, ball.center, ball.radius, (0, 0, 255), 2)
        cv2.line(image, (ball.x - ball.radius, ball.y), (ball.x + ball.radius, ball.y), (0, 0, 255), 1)
        cv2.line(image, (ball.x, ball.y - ball.radius), (ball.x, ball.y + ball.radius), (0, 0, 255), 1)


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
