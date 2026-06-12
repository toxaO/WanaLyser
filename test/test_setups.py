from __future__ import annotations

import sys
import unittest
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from database import init_db, list_setup_presets, metadata_for_preset  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
