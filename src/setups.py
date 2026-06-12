from __future__ import annotations

from dataclasses import dataclass

from core import (
    DEFAULT_BALL_SENSITIVITY,
    DEFAULT_BEAM_THRESHOLD,
    DEFAULT_PIXEL_SIZE_MM,
)


@dataclass(frozen=True)
class AnalysisSetup:
    name: str
    gantry_angle: float
    collimator_angle: float
    couch_angle: float
    dx_positive_label: str = "+dx"
    dx_negative_label: str = "-dx"
    dy_positive_label: str = "+dy"
    dy_negative_label: str = "-dy"
    field_size_px: int | None = None
    target_size_px: int | None = None
    pixel_size_mm: float = DEFAULT_PIXEL_SIZE_MM
    beam_threshold: int = DEFAULT_BEAM_THRESHOLD
    ball_sensitivity: int = DEFAULT_BALL_SENSITIVITY


@dataclass(frozen=True)
class SetupPreset:
    name: str
    description: str
    setups: tuple[AnalysisSetup, ...]


DAILY_14 = SetupPreset(
    name="daily-14",
    description="14 image daily Winston-Lutz order in sample/set",
    setups=(
        AnalysisSetup("gantry_180(-)", 180.0, 0.0, 0.0, dx_positive_label="270", dx_negative_label="90", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("gantry_90", 90.0, 0.0, 0.0, dx_positive_label="P", dx_negative_label="A", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("gantry_0", 0.0, 0.0, 0.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("gantry_270", 270.0, 0.0, 0.0, dx_positive_label="A", dx_negative_label="P", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("gantry_180(+)", 180.0, 0.0, 0.0, dx_positive_label="270", dx_negative_label="90", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("collimator_180", 0.0, 180.0, 0.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("collimator_90", 0.0, 90.0, 0.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("collimator_0", 0.0, 0.0, 0.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("collimator_270", 0.0, 270.0, 0.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("couch_90", 0.0, 0.0, 90.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("couch_45", 0.0, 0.0, 45.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("couch_0", 0.0, 0.0, 0.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("couch_315", 0.0, 0.0, 315.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
        AnalysisSetup("couch_270", 0.0, 0.0, 270.0, dx_positive_label="90", dx_negative_label="270", dy_positive_label="G", dy_negative_label="T"),
    ),
)


BUILTIN_PRESETS = (DAILY_14,)
