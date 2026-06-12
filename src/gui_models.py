from __future__ import annotations

from dataclasses import dataclass, field

from report import ReportPoint
from workflow import AnalysisPlanItem
from core import Analysis


@dataclass
class AnalysisSeries:
    name: str
    plan: list[AnalysisPlanItem]
    analyses: list[Analysis]
    inspection_type: str
    machine_name: str | None
    saved: bool = False
    started_at: str = ""
    source: str = "current"
    session_id: int | None = None
    points: list[ReportPoint] = field(default_factory=list)
    output_active: bool = True
