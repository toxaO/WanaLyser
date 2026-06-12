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
    get_default_machine_name,
    get_or_create_machine,
    init_db,
    list_analysis_results,
    list_machines,
    save_analysis_results,
    set_default_machine_name,
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

    def test_machine_is_created_and_reused(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            init_db(connection)
            first_id = get_or_create_machine(connection, "linac-a")
            second_id = get_or_create_machine(connection, "linac-a")
            self.assertEqual(first_id, second_id)

            create_session(
                connection,
                inspection_type="daily",
                machine_name="linac-a",
            )
            row = connection.execute(
                """
                SELECT sessions.machine_id, machines.name
                FROM sessions
                JOIN machines ON machines.id = sessions.machine_id
                """
            ).fetchone()
            self.assertEqual(row["machine_id"], first_id)
            self.assertEqual(row["name"], "linac-a")

            machines = list_machines(connection)
            machine_names = [machine["name"] for machine in machines]
            self.assertIn("machine1", machine_names)
            self.assertIn("machine2", machine_names)
            self.assertIn("linac-a", machine_names)
            self.assertEqual(get_default_machine_name(connection), "machine1")

            set_default_machine_name(connection, "linac-a")
            self.assertEqual(get_default_machine_name(connection), "linac-a")
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
