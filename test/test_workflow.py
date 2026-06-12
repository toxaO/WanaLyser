from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from database import init_db  # noqa: E402
from workflow import build_analysis_plan_from_preset, format_plan  # noqa: E402


class WorkflowTest(unittest.TestCase):
    def test_build_analysis_plan_from_preset(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            plan = build_analysis_plan_from_preset(
                ROOT / "sample" / "set",
                connection,
                "daily-14",
            )
            self.assertEqual(len(plan), 14)
            self.assertEqual(plan[0].image_name, "01.bmp")
            self.assertEqual(plan[0].setup_label, "gantry_180(-)")
            self.assertEqual(plan[0].gantry_angle, 180.0)
            self.assertEqual(plan[-1].image_name, "14.bmp")
            self.assertEqual(plan[-1].setup_label, "couch_270")
            self.assertEqual(plan[-1].couch_angle, 270.0)

            lines = format_plan(plan)
            self.assertIn("01.bmp", lines[0])
            self.assertIn("gantry_180(-)", lines[0])
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
