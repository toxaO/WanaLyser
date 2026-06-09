from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from conditions import BUILTIN_PRESETS, ConditionPreset
from core import ALGORITHM_VERSION, Analysis


@dataclass(frozen=True)
class AnalysisMetadata:
    gantry_angle: float | None = None
    collimator_angle: float | None = None
    couch_angle: float | None = None
    note: str | None = None


def connect_database(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            inspection_type TEXT NOT NULL,
            machine_id INTEGER,
            machine_name TEXT,
            note TEXT,
            FOREIGN KEY(machine_id) REFERENCES machines(id)
        );

        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            analyzed_at TEXT NOT NULL,
            image_name TEXT NOT NULL,
            image_path TEXT NOT NULL,
            gantry_angle REAL,
            collimator_angle REAL,
            couch_angle REAL,
            dx_mm REAL,
            dy_mm REAL,
            distance_mm REAL,
            angle_degrees REAL,
            beam_center_x REAL,
            beam_center_y REAL,
            ball_center_x REAL,
            ball_center_y REAL,
            pixel_size_mm REAL NOT NULL,
            beam_threshold INTEGER NOT NULL,
            ball_sensitivity INTEGER NOT NULL,
            beam_size_px INTEGER,
            target_size_px INTEGER,
            algorithm_version TEXT NOT NULL,
            succeeded INTEGER NOT NULL,
            failure_reason TEXT,
            note TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS condition_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS condition_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preset_id INTEGER NOT NULL,
            step_order INTEGER NOT NULL,
            label TEXT NOT NULL,
            gantry_angle REAL NOT NULL,
            collimator_angle REAL NOT NULL,
            couch_angle REAL NOT NULL,
            FOREIGN KEY(preset_id) REFERENCES condition_presets(id) ON DELETE CASCADE,
            UNIQUE(preset_id, step_order)
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_analysis_results_session_id
            ON analysis_results(session_id);
        CREATE INDEX IF NOT EXISTS idx_analysis_results_analyzed_at
            ON analysis_results(analyzed_at);
        CREATE INDEX IF NOT EXISTS idx_analysis_results_angles
            ON analysis_results(gantry_angle, collimator_angle, couch_angle);
        CREATE INDEX IF NOT EXISTS idx_sessions_machine_id
            ON sessions(machine_id);
        """
    )
    ensure_column(connection, "sessions", "machine_id", "INTEGER")
    ensure_column(connection, "analysis_results", "beam_size_px", "INTEGER")
    ensure_column(connection, "analysis_results", "target_size_px", "INTEGER")
    seed_builtin_presets(connection)
    seed_default_machines(connection)
    connection.commit()


def ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {column[1] for column in columns}
    if column_name not in existing:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def seed_builtin_presets(connection: sqlite3.Connection) -> None:
    for preset in BUILTIN_PRESETS:
        upsert_condition_preset(connection, preset, is_builtin=True)


def seed_default_machines(connection: sqlite3.Connection) -> None:
    get_or_create_machine(connection, "1")
    get_or_create_machine(connection, "2")
    if get_setting(connection, "default_machine_name") is None:
        set_setting(connection, "default_machine_name", "1")


def get_setting(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return str(row["value"] if isinstance(row, sqlite3.Row) else row[0])


def set_setting(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_default_machine_name(connection: sqlite3.Connection) -> str:
    return get_setting(connection, "default_machine_name") or "1"


def set_default_machine_name(connection: sqlite3.Connection, machine_name: str) -> None:
    get_or_create_machine(connection, machine_name)
    set_setting(connection, "default_machine_name", machine_name)


def upsert_condition_preset(
    connection: sqlite3.Connection,
    preset: ConditionPreset,
    is_builtin: bool = False,
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    row = connection.execute(
        "SELECT id FROM condition_presets WHERE name = ?",
        (preset.name,),
    ).fetchone()
    if row is None:
        cursor = connection.execute(
            """
            INSERT INTO condition_presets (
                name,
                description,
                created_at,
                updated_at,
                is_builtin,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (preset.name, preset.description, now, now, int(is_builtin)),
        )
        preset_id = int(cursor.lastrowid)
    else:
        preset_id = int(row["id"] if isinstance(row, sqlite3.Row) else row[0])
        connection.execute(
            """
            UPDATE condition_presets
            SET description = ?, updated_at = ?, is_builtin = ?, is_active = 1
            WHERE id = ?
            """,
            (preset.description, now, int(is_builtin), preset_id),
        )

    connection.execute("DELETE FROM condition_steps WHERE preset_id = ?", (preset_id,))
    connection.executemany(
        """
        INSERT INTO condition_steps (
            preset_id,
            step_order,
            label,
            gantry_angle,
            collimator_angle,
            couch_angle
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                preset_id,
                index,
                condition.name,
                condition.gantry_angle,
                condition.collimator_angle,
                condition.couch_angle,
            )
            for index, condition in enumerate(preset.conditions, start=1)
        ],
    )
    return preset_id


def create_session(
    connection: sqlite3.Connection,
    inspection_type: str,
    machine_name: str | None = None,
    note: str | None = None,
    started_at: datetime | None = None,
) -> int:
    started_at = started_at or datetime.now()
    machine_id = None
    if machine_name is not None:
        machine_id = get_or_create_machine(connection, machine_name)
    cursor = connection.execute(
        """
        INSERT INTO sessions (
            started_at,
            inspection_type,
            machine_id,
            machine_name,
            note
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            started_at.isoformat(timespec="seconds"),
            inspection_type,
            machine_id,
            machine_name,
            note,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_or_create_machine(
    connection: sqlite3.Connection,
    name: str,
    note: str | None = None,
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    row = connection.execute(
        "SELECT id FROM machines WHERE name = ?",
        (name,),
    ).fetchone()
    if row is not None:
        machine_id = int(row["id"] if isinstance(row, sqlite3.Row) else row[0])
        connection.execute(
            """
            UPDATE machines
            SET updated_at = ?, is_active = 1
            WHERE id = ?
            """,
            (now, machine_id),
        )
        return machine_id

    cursor = connection.execute(
        """
        INSERT INTO machines (name, created_at, updated_at, is_active, note)
        VALUES (?, ?, ?, 1, ?)
        """,
        (name, now, now, note),
    )
    return int(cursor.lastrowid)


def list_machines(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT
            id,
            name,
            created_at,
            updated_at,
            is_active,
            note
        FROM machines
        WHERE is_active = 1
        ORDER BY name
        """
    )
    return list(cursor.fetchall())


def list_condition_presets(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT
            condition_presets.id,
            condition_presets.name,
            condition_presets.description,
            condition_presets.is_builtin,
            condition_presets.is_active,
            COUNT(condition_steps.id) AS step_count
        FROM condition_presets
        LEFT JOIN condition_steps
            ON condition_steps.preset_id = condition_presets.id
        WHERE condition_presets.is_active = 1
        GROUP BY condition_presets.id
        ORDER BY condition_presets.name
        """
    )
    return list(cursor.fetchall())


def get_condition_preset(
    connection: sqlite3.Connection,
    name: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id, name, description, is_builtin, is_active
        FROM condition_presets
        WHERE name = ? AND is_active = 1
        """,
        (name,),
    ).fetchone()


def list_condition_steps(
    connection: sqlite3.Connection,
    preset_id: int,
) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT
            id,
            preset_id,
            step_order,
            label,
            gantry_angle,
            collimator_angle,
            couch_angle
        FROM condition_steps
        WHERE preset_id = ?
        ORDER BY step_order
        """,
        (preset_id,),
    )
    return list(cursor.fetchall())


def metadata_for_preset(
    connection: sqlite3.Connection,
    preset_name: str,
    image_count: int,
) -> list[AnalysisMetadata]:
    preset = get_condition_preset(connection, preset_name)
    if preset is None:
        rows = list_condition_presets(connection)
        available = ", ".join(row["name"] for row in rows)
        raise ValueError(f"unknown preset: {preset_name}. available: {available}")

    steps = list_condition_steps(connection, int(preset["id"]))
    if len(steps) != image_count:
        raise ValueError(
            f"preset {preset_name} requires {len(steps)} images, "
            f"but {image_count} images were loaded"
        )

    return [
        AnalysisMetadata(
            gantry_angle=step["gantry_angle"],
            collimator_angle=step["collimator_angle"],
            couch_angle=step["couch_angle"],
            note=step["label"],
        )
        for step in steps
    ]


def save_analysis_results(
    connection: sqlite3.Connection,
    session_id: int,
    analyses: Iterable[Analysis],
    metadata: AnalysisMetadata | Iterable[AnalysisMetadata] | None = None,
) -> None:
    analysis_list = list(analyses)
    metadata_list = normalize_metadata(metadata, len(analysis_list))
    rows = [
        build_analysis_row(session_id, analysis, analysis_metadata)
        for analysis, analysis_metadata in zip(analysis_list, metadata_list)
    ]
    connection.executemany(
        """
        INSERT INTO analysis_results (
            session_id,
            analyzed_at,
            image_name,
            image_path,
            gantry_angle,
            collimator_angle,
            couch_angle,
            dx_mm,
            dy_mm,
            distance_mm,
            angle_degrees,
            beam_center_x,
            beam_center_y,
            ball_center_x,
            ball_center_y,
            pixel_size_mm,
            beam_threshold,
            ball_sensitivity,
            beam_size_px,
            target_size_px,
            algorithm_version,
            succeeded,
            failure_reason,
            note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()


def normalize_metadata(
    metadata: AnalysisMetadata | Iterable[AnalysisMetadata] | None,
    count: int,
) -> list[AnalysisMetadata]:
    if metadata is None:
        return [AnalysisMetadata() for _ in range(count)]
    if isinstance(metadata, AnalysisMetadata):
        return [metadata for _ in range(count)]

    metadata_list = list(metadata)
    if len(metadata_list) != count:
        raise ValueError(
            f"metadata count must match analysis count: {len(metadata_list)} != {count}"
        )
    return metadata_list


def build_analysis_row(
    session_id: int,
    analysis: Analysis,
    metadata: AnalysisMetadata,
) -> tuple[object, ...]:
    result = analysis.result
    row = result.to_row()
    return (
        session_id,
        datetime.now().isoformat(timespec="seconds"),
        row["image_name"],
        row["image_path"],
        metadata.gantry_angle,
        metadata.collimator_angle,
        metadata.couch_angle,
        row["dx_mm"],
        row["dy_mm"],
        row["distance_mm"],
        row["angle_degrees"],
        row["beam_center_x"],
        row["beam_center_y"],
        row["ball_center_x"],
        row["ball_center_y"],
        row["pixel_size_mm"],
        row["beam_threshold"],
        row["ball_sensitivity"],
        row["beam_size_px"],
        row["target_size_px"],
        ALGORITHM_VERSION,
        int(result.succeeded),
        failure_reason(analysis),
        metadata.note,
    )


def failure_reason(analysis: Analysis) -> str | None:
    result = analysis.result
    if result.succeeded:
        return None
    if result.beam is None and result.ball is None:
        return "beam and ball were not detected"
    if result.beam is None:
        return "beam was not detected"
    if result.ball is None:
        return "ball was not detected"
    return "analysis failed"


def list_analysis_results(
    connection: sqlite3.Connection,
    limit: int = 20,
) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT
            analysis_results.id,
            sessions.inspection_type,
            COALESCE(machines.name, sessions.machine_name) AS machine_name,
            analysis_results.analyzed_at,
            analysis_results.image_name,
            analysis_results.gantry_angle,
            analysis_results.collimator_angle,
            analysis_results.couch_angle,
            analysis_results.dx_mm,
            analysis_results.dy_mm,
            analysis_results.distance_mm,
            analysis_results.succeeded
        FROM analysis_results
        JOIN sessions ON sessions.id = analysis_results.session_id
        LEFT JOIN machines ON machines.id = sessions.machine_id
        ORDER BY analysis_results.analyzed_at DESC, analysis_results.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return list(cursor.fetchall())
