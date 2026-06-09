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
    condition_label: str | None
    gantry_angle: float | None
    collimator_angle: float | None
    couch_angle: float | None


def build_analysis_plan(
    image_input: str | Path,
    metadata: list[AnalysisMetadata],
) -> list[AnalysisPlanItem]:
    image_paths = list_images(image_input)
    if len(image_paths) != len(metadata):
        raise ValueError(
            f"metadata count must match image count: {len(metadata)} != {len(image_paths)}"
        )

    return [
        AnalysisPlanItem(
            order=index,
            image_path=image_path,
            image_name=image_path.name,
            condition_label=item.note,
            gantry_angle=item.gantry_angle,
            collimator_angle=item.collimator_angle,
            couch_angle=item.couch_angle,
        )
        for index, (image_path, item) in enumerate(zip(image_paths, metadata), start=1)
    ]


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
    return [analyze_image(item.image_path, parameters) for item in plan]


def format_plan(plan: list[AnalysisPlanItem]) -> list[str]:
    return [
        (
            f"{item.order:02d}  {item.image_name}  "
            f"{item.condition_label or '-'}  "
            f"G={item.gantry_angle} "
            f"C={item.collimator_angle} "
            f"Cou={item.couch_angle}"
        )
        for item in plan
    ]
