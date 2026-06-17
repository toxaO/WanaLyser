from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import analyze_image  # noqa: E402
from database import (  # noqa: E402
    AnalysisMetadata,
    connect_database,
    create_session,
    init_db,
    save_analysis_results,
)
from report import ReportPoint, axis_labels, generate_pdf_report  # noqa: E402


class ReportTest(unittest.TestCase):
    def test_axis_labels_can_use_series_name(self) -> None:
        points = [
            ReportPoint(
                analyzed_at="2026-06-16T10:30",
                image_name="a.bmp",
                setup_label="setup_a",
                dx_mm=0.1,
                dy_mm=0.2,
                distance_mm=0.3,
                gantry_angle=0.0,
                collimator_angle=0.0,
                couch_angle=0.0,
                series_name="set_01",
            )
        ]

        self.assertEqual(axis_labels(points, "series"), ["set_01"])
        self.assertEqual(axis_labels(points, "date"), ["06/16"])

    def test_generate_pdf_report(self) -> None:
        analyses = [
            analyze_image(ROOT / "sample" / "size" / "2.bmp"),
            analyze_image(ROOT / "sample" / "size" / "5.bmp"),
        ]
        metadata = [
            AnalysisMetadata(gantry_angle=0.0, collimator_angle=0.0, couch_angle=0.0, note="setup_a"),
            AnalysisMetadata(gantry_angle=90.0, collimator_angle=0.0, couch_angle=0.0, note="setup_b"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "wanalyzer.sqlite"
            pdf_path = Path(temp_dir) / "report.pdf"
            connection = connect_database(db_path)
            try:
                init_db(connection)
                session_id = create_session(
                    connection,
                    inspection_type="daily",
                    machine_name="linac-a",
                )
                save_analysis_results(connection, session_id, analyses, metadata)
            finally:
                connection.close()

            generate_pdf_report(db_path, pdf_path, machine_name="linac-a")
            self.assertTrue(pdf_path.exists())
            self.assertGreater(pdf_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
