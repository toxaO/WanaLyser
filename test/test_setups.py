from __future__ import annotations

import sys
import unittest
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from database import (  # noqa: E402
    get_setup_preset,
    init_db,
    list_setup_presets,
    list_setup_steps,
    metadata_for_preset,
    replace_setup_preset_steps,
)
from setups import AnalysisSetup, SetupPreset  # noqa: E402


class SetupPresetTest(unittest.TestCase):
    def test_daily_14_setups(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            presets = list_setup_presets(connection)
            self.assertEqual(len(presets), 1)
            self.assertEqual(presets[0]["name"], "daily-14")
            self.assertEqual(presets[0]["step_count"], 14)

            metadata = metadata_for_preset(connection, "daily-14", 14)
            self.assertEqual(metadata[0].gantry_angle, 180.0)
            self.assertEqual(metadata[4].gantry_angle, 180.0)
            self.assertEqual(metadata[5].collimator_angle, 180.0)
            self.assertEqual(metadata[13].couch_angle, 270.0)
        finally:
            connection.close()

    def test_metadata_count_mismatch_is_allowed_for_manual_assignment(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            metadata = metadata_for_preset(connection, "daily-14", 3)
            self.assertEqual(len(metadata), 14)
        finally:
            connection.close()

    def test_replace_setup_preset_steps(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            preset = get_setup_preset(connection, "daily-14")
            self.assertIsNotNone(preset)

            replacement = SetupPreset(
                name="daily-14",
                description="replacement",
                setups=(
                    AnalysisSetup("test_a", 0.0, 0.0, 0.0),
                    AnalysisSetup("test_b", 90.0, 0.0, 0.0),
                ),
            )
            replace_setup_preset_steps(connection, int(preset["id"]), replacement)

            steps = list_setup_steps(connection, int(preset["id"]))
            self.assertEqual([step["label"] for step in steps], ["test_a", "test_b"])
            self.assertEqual(steps[1]["gantry_angle"], 90.0)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
