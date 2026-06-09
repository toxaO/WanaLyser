from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisCondition:
    name: str
    gantry_angle: float
    collimator_angle: float
    couch_angle: float


@dataclass(frozen=True)
class ConditionPreset:
    name: str
    description: str
    conditions: tuple[AnalysisCondition, ...]


DAILY_14 = ConditionPreset(
    name="daily-14",
    description="14 image daily Winston-Lutz order in sample/set",
    conditions=(
        AnalysisCondition("gantry_180_1", 180.1, 0.0, 0.0),
        AnalysisCondition("gantry_270", 270.0, 0.0, 0.0),
        AnalysisCondition("gantry_0", 0.0, 0.0, 0.0),
        AnalysisCondition("gantry_90", 90.0, 0.0, 0.0),
        AnalysisCondition("gantry_179_9", 179.9, 0.0, 0.0),
        AnalysisCondition("collimator_270", 0.0, 270.0, 0.0),
        AnalysisCondition("collimator_0", 0.0, 0.0, 0.0),
        AnalysisCondition("collimator_90", 0.0, 90.0, 0.0),
        AnalysisCondition("collimator_180", 0.0, 180.0, 0.0),
        AnalysisCondition("couch_90", 0.0, 0.0, 90.0),
        AnalysisCondition("couch_45", 0.0, 0.0, 45.0),
        AnalysisCondition("couch_0", 0.0, 0.0, 0.0),
        AnalysisCondition("couch_315", 0.0, 0.0, 315.0),
        AnalysisCondition("couch_270", 0.0, 0.0, 270.0),
    ),
)


BUILTIN_PRESETS = (DAILY_14,)
