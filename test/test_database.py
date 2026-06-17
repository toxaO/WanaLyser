from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import ALGORITHM_VERSION, analyze_image  # noqa: E402
from database import (  # noqa: E402
    AnalysisMetadata,
    connect_database,
    create_session,
    delete_machine_results,
    delete_setup_preset,
    get_default_machine_name,
    init_db,
    list_analysis_results,
    list_machines,
    list_setup_presets,
    rename_machine_results,
    save_analysis_results,
    set_default_machine_name,
    update_session_series,
)


class DatabaseTest(unittest.TestCase):
    def test_save_analysis_result(self) -> None:
        analysis = analyze_image(ROOT / "sample" / "size" / "2.bmp")

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "wanalyzer.sqlite"
            connection = connect_database(db_path)
            try:
                init_db(connection)
                session_id = create_session(
                    connection,
                    inspection_type="daily",
                    machine_name="test-machine",
                    note="session note",
                )
                metadata = AnalysisMetadata(
                    gantry_angle=0.0,
                    collimator_angle=90.0,
                    couch_angle=270.0,
                    note="result note",
                )
                save_analysis_results(connection, session_id, [analysis], metadata)

                row = connection.execute(
                    "SELECT * FROM analysis_results WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["image_name"], "2.bmp")
                self.assertEqual(row["gantry_angle"], 0.0)
                self.assertEqual(row["collimator_angle"], 90.0)
                self.assertEqual(row["couch_angle"], 270.0)
                self.assertAlmostEqual(row["dx_mm"], 0.242, places=3)
                self.assertAlmostEqual(row["dy_mm"], 0.605, places=3)
                self.assertEqual(row["algorithm_version"], ALGORITHM_VERSION)
                self.assertEqual(row["succeeded"], 1)
                self.assertIsNone(row["failure_reason"])

                rows = list_analysis_results(connection)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["inspection_type"], "daily")
                self.assertEqual(rows[0]["machine_name"], "test-machine")
            finally:
                connection.close()

    def test_init_db_is_repeatable(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            init_db(connection)
            init_db(connection)
        finally:
            connection.close()

    def test_machine_names_are_listed_from_sessions_and_default(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            create_session(
                connection,
                inspection_type="daily",
                machine_name="linac-a",
            )

            machines = list_machines(connection)
            machine_names = [machine["name"] for machine in machines]
            self.assertIn("machine1", machine_names)
            self.assertIn("linac-a", machine_names)
            self.assertEqual(get_default_machine_name(connection), "machine1")

            set_default_machine_name(connection, "linac-a")
            self.assertEqual(get_default_machine_name(connection), "linac-a")
        finally:
            connection.close()

    def test_machine_results_can_be_renamed(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            create_session(connection, inspection_type="daily", machine_name="typo")
            set_default_machine_name(connection, "typo")
            rename_machine_results(connection, "typo", "VERSA1")
            connection.commit()

            machine_names = [machine["name"] for machine in list_machines(connection)]
            self.assertIn("VERSA1", machine_names)
            self.assertNotIn("typo", machine_names)
            self.assertEqual(get_default_machine_name(connection), "VERSA1")
        finally:
            connection.close()

    def test_machine_results_can_be_deleted(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            create_session(connection, inspection_type="daily", machine_name="delete-me")
            delete_machine_results(connection, "delete-me")
            connection.commit()
            machine_names = [machine["name"] for machine in list_machines(connection)]
            self.assertNotIn("delete-me", machine_names)
        finally:
            connection.close()

    def test_builtin_presets_are_seeded_only_once(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            presets = list_setup_presets(connection)
            self.assertTrue(presets)
            original_name = presets[0]["name"]
            connection.execute(
                "UPDATE setup_presets SET name = ? WHERE id = ?",
                ("renamed-preset", int(presets[0]["id"])),
            )
            connection.commit()

            init_db(connection)
            preset_names = [preset["name"] for preset in list_setup_presets(connection)]
            self.assertIn("renamed-preset", preset_names)
            self.assertNotIn(original_name, preset_names)
        finally:
            connection.close()

    def test_preset_can_be_deleted(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            preset = list_setup_presets(connection)[0]
            delete_setup_preset(connection, int(preset["id"]))
            preset_names = [row["name"] for row in list_setup_presets(connection)]
            self.assertNotIn(preset["name"], preset_names)
        finally:
            connection.close()

    def test_session_series_metadata_can_be_updated(self) -> None:
        analysis = analyze_image(ROOT / "sample" / "size" / "2.bmp")

        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            session_id = create_session(
                connection,
                inspection_type="daily",
                series_name="set_01",
            )
            save_analysis_results(connection, session_id, [analysis])
            update_session_series(
                connection,
                session_id,
                started_at="2026-06-16T10:30",
                series_name="morning_qc",
            )
            session = connection.execute(
                "SELECT started_at, series_name FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            result = connection.execute(
                "SELECT analyzed_at FROM analysis_results WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            self.assertEqual(session["started_at"], "2026-06-16T10:30")
            self.assertEqual(session["series_name"], "morning_qc")
            self.assertEqual(result["analyzed_at"], "2026-06-16T10:30")
        finally:
            connection.close()

    def test_save_per_image_metadata(self) -> None:
        analyses = [
            analyze_image(ROOT / "sample" / "size" / "2.bmp"),
            analyze_image(ROOT / "sample" / "size" / "5.bmp"),
        ]
        metadata = [
            AnalysisMetadata(gantry_angle=0.0, collimator_angle=0.0, couch_angle=0.0),
            AnalysisMetadata(gantry_angle=90.0, collimator_angle=0.0, couch_angle=0.0),
        ]

        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            session_id = create_session(connection, inspection_type="daily")
            save_analysis_results(connection, session_id, analyses, metadata)
            rows = connection.execute(
                """
                SELECT image_name, gantry_angle
                FROM analysis_results
                ORDER BY id
                """
            ).fetchall()
            self.assertEqual(rows[0]["image_name"], "2.bmp")
            self.assertEqual(rows[0]["gantry_angle"], 0.0)
            self.assertEqual(rows[1]["image_name"], "5.bmp")
            self.assertEqual(rows[1]["gantry_angle"], 90.0)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
