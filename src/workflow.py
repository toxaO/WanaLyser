from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core import Analysis, AnalysisParameters, analyze_image, list_images
from database import AnalysisMetadata, metadata_for_preset


@dataclass(frozen=True)
class AnalysisPlanItem:
    order: int
    image_path: Path
    image_name: str
    setup_label: str | None
    gantry_angle: float | None
    collimator_angle: float | None
    couch_angle: float | None
    x_axis_label: str | None
    y_axis_label: str | None
    dx_positive_label: str | None = None
    dx_negative_label: str | None = None
    dy_positive_label: str | None = None
    dy_negative_label: str | None = None
    x_inverted: bool = False
    parameters: AnalysisParameters | None = None


def build_analysis_plan(
    image_input: str | Path,
    metadata: list[AnalysisMetadata],
) -> list[AnalysisPlanItem]:
    image_paths = list_images(image_input)

    plan: list[AnalysisPlanItem] = []
    for index, image_path in enumerate(image_paths, start=1):
        item = metadata[index - 1] if index - 1 < len(metadata) else AnalysisMetadata()
        plan.append(
        AnalysisPlanItem(
            order=index,
            image_path=image_path,
            image_name=image_path.name,
            setup_label=item.note,
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
            parameters=AnalysisParameters(
                beam_threshold=0 if item.beam_threshold is None else item.beam_threshold,
                ball_sensitivity=10 if item.ball_sensitivity is None else item.ball_sensitivity,
                pixel_size_mm=0.242 if item.pixel_size_mm is None else item.pixel_size_mm,
                beam_size_px=item.beam_size_px,
                target_size_px=item.target_size_px,
            ),
        )
        )
    return plan


def build_analysis_plan_from_preset(
    image_input: str | Path,
    connection,
    preset_name: str,
) -> list[AnalysisPlanItem]:
    image_paths = list_images(image_input)
    metadata = metadata_for_preset(connection, preset_name, len(image_paths))
    return build_analysis_plan(image_input, metadata)


def analyze_plan(
    plan: list[AnalysisPlanItem],
    parameters: AnalysisParameters | None = None,
) -> list[Analysis]:
    return [
        analyze_image(item.image_path, item.parameters or parameters)
        for item in plan
    ]


def format_plan(plan: list[AnalysisPlanItem]) -> list[str]:
    return [
        (
            f"{item.order:02d}  {item.image_name}  "
            f"{item.setup_label or '-'}  "
            f"G={item.gantry_angle} "
            f"C={item.collimator_angle} "
            f"Cou={item.couch_angle}"
        )
        for item in plan
    ]
