from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from setups import BUILTIN_PRESETS, AnalysisSetup, SetupPreset
from core import ALGORITHM_VERSION, Analysis


@dataclass(frozen=True)
class AnalysisMetadata:
    gantry_angle: float | None = None
    collimator_angle: float | None = None
    couch_angle: float | None = None
    note: str | None = None
    x_axis_label: str | None = None
    y_axis_label: str | None = None
    dx_positive_label: str | None = None
    dx_negative_label: str | None = None
    dy_positive_label: str | None = None
    dy_negative_label: str | None = None
    x_inverted: bool = False
    beam_size_px: int | None = None
    target_size_px: int | None = None
    pixel_size_mm: float | None = None
    beam_threshold: int | None = None
    ball_sensitivity: int | None = None


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
            x_axis_label TEXT,
            y_axis_label TEXT,
            dx_positive_label TEXT,
            dx_negative_label TEXT,
            dy_positive_label TEXT,
            dy_negative_label TEXT,
            x_inverted INTEGER NOT NULL DEFAULT 0,
            algorithm_version TEXT NOT NULL,
            succeeded INTEGER NOT NULL,
            failure_reason TEXT,
            note TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS setup_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            gantry_angle REAL NOT NULL,
            collimator_angle REAL NOT NULL,
            couch_angle REAL NOT NULL,
            dx_positive_label TEXT NOT NULL DEFAULT '+dx',
            dx_negative_label TEXT NOT NULL DEFAULT '-dx',
            dy_positive_label TEXT NOT NULL DEFAULT '+dy',
            dy_negative_label TEXT NOT NULL DEFAULT '-dy',
            field_size_px INTEGER,
            target_size_px INTEGER,
            pixel_size_mm REAL NOT NULL,
            beam_threshold INTEGER NOT NULL,
            ball_sensitivity INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS setup_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preset_id INTEGER NOT NULL,
            step_order INTEGER NOT NULL,
            setup_id INTEGER NOT NULL,
            FOREIGN KEY(preset_id) REFERENCES setup_presets(id) ON DELETE CASCADE,
            FOREIGN KEY(setup_id) REFERENCES setups(id),
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
    ensure_column(connection, "analysis_results", "x_axis_label", "TEXT")
    ensure_column(connection, "analysis_results", "y_axis_label", "TEXT")
    ensure_column(connection, "analysis_results", "dx_positive_label", "TEXT")
    ensure_column(connection, "analysis_results", "dx_negative_label", "TEXT")
    ensure_column(connection, "analysis_results", "dy_positive_label", "TEXT")
    ensure_column(connection, "analysis_results", "dy_negative_label", "TEXT")
    ensure_column(connection, "analysis_results", "x_inverted", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "setups", "dx_positive_label", "TEXT NOT NULL DEFAULT '+dx'")
    ensure_column(connection, "setups", "dx_negative_label", "TEXT NOT NULL DEFAULT '-dx'")
    ensure_column(connection, "setups", "dy_positive_label", "TEXT NOT NULL DEFAULT '+dy'")
    ensure_column(connection, "setups", "dy_negative_label", "TEXT NOT NULL DEFAULT '-dy'")
    seed_builtin_setups(connection)
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
        upsert_setup_preset(connection, preset, is_builtin=True)


def seed_builtin_setups(connection: sqlite3.Connection) -> None:
    for preset in BUILTIN_PRESETS:
        for setup in preset.setups:
            upsert_setup(connection, setup)


def upsert_setup(connection: sqlite3.Connection, setup: AnalysisSetup) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    row = connection.execute(
        "SELECT id FROM setups WHERE name = ?",
        (setup.name,),
    ).fetchone()
    insert_values = (
        setup.name,
        setup.gantry_angle,
        setup.collimator_angle,
        setup.couch_angle,
        setup.dx_positive_label,
        setup.dx_negative_label,
        setup.dy_positive_label,
        setup.dy_negative_label,
        setup.field_size_px,
        setup.target_size_px,
        setup.pixel_size_mm,
        setup.beam_threshold,
        setup.ball_sensitivity,
        now,
        now,
    )
    update_values = (
        setup.name,
        setup.gantry_angle,
        setup.collimator_angle,
        setup.couch_angle,
        setup.dx_positive_label,
        setup.dx_negative_label,
        setup.dy_positive_label,
        setup.dy_negative_label,
        setup.field_size_px,
        setup.target_size_px,
        setup.pixel_size_mm,
        setup.beam_threshold,
        setup.ball_sensitivity,
        now,
    )
    if row is None:
        cursor = connection.execute(
            """
            INSERT INTO setups (
                name,
                gantry_angle,
                collimator_angle,
                couch_angle,
                dx_positive_label,
                dx_negative_label,
                dy_positive_label,
                dy_negative_label,
                field_size_px,
                target_size_px,
                pixel_size_mm,
                beam_threshold,
                ball_sensitivity,
                created_at,
                updated_at,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            insert_values,
        )
        return int(cursor.lastrowid)
    setup_id = int(row["id"] if isinstance(row, sqlite3.Row) else row[0])
    connection.execute(
        """
        UPDATE setups
        SET name = ?,
            gantry_angle = ?,
            collimator_angle = ?,
            couch_angle = ?,
            dx_positive_label = ?,
            dx_negative_label = ?,
            dy_positive_label = ?,
            dy_negative_label = ?,
            field_size_px = ?,
            target_size_px = ?,
            pixel_size_mm = ?,
            beam_threshold = ?,
            ball_sensitivity = ?,
            updated_at = ?,
            is_active = 1
        WHERE id = ?
        """,
        update_values + (setup_id,),
    )
    return setup_id


def update_setup_by_id(
    connection: sqlite3.Connection,
    setup_id: int,
    setup: AnalysisSetup,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    row = connection.execute(
        "SELECT id FROM setups WHERE name = ? AND id != ?",
        (setup.name, setup_id),
    ).fetchone()
    if row is not None:
        raise ValueError("同じsetup名がすでに存在します。別の名前を使用してください。")
    connection.execute(
        """
        UPDATE setups
        SET name = ?,
            gantry_angle = ?,
            collimator_angle = ?,
            couch_angle = ?,
            dx_positive_label = ?,
            dx_negative_label = ?,
            dy_positive_label = ?,
            dy_negative_label = ?,
            field_size_px = ?,
            target_size_px = ?,
            pixel_size_mm = ?,
            beam_threshold = ?,
            ball_sensitivity = ?,
            updated_at = ?,
            is_active = 1
        WHERE id = ?
        """,
        (
            setup.name,
            setup.gantry_angle,
            setup.collimator_angle,
            setup.couch_angle,
            setup.dx_positive_label,
            setup.dx_negative_label,
            setup.dy_positive_label,
            setup.dy_negative_label,
            setup.field_size_px,
            setup.target_size_px,
            setup.pixel_size_mm,
            setup.beam_threshold,
            setup.ball_sensitivity,
            now,
            setup_id,
        ),
    )


def list_setups(connection: sqlite3.Connection, active_only: bool = True) -> list[sqlite3.Row]:
    where = "WHERE is_active = 1" if active_only else ""
    return list(connection.execute(
        f"""
        SELECT
            id,
            name,
            gantry_angle,
            collimator_angle,
            couch_angle,
            dx_positive_label,
            dx_negative_label,
            dy_positive_label,
            dy_negative_label,
            field_size_px,
            target_size_px,
            pixel_size_mm,
            beam_threshold,
            ball_sensitivity,
            is_active
        FROM setups
        {where}
        ORDER BY name
        """
    ).fetchall())


def get_setup(connection: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM setups
        WHERE name = ? AND is_active = 1
        """,
        (name,),
    ).fetchone()


def deactivate_setup(connection: sqlite3.Connection, setup_id: int) -> None:
    connection.execute(
        "UPDATE setups SET is_active = 0, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(timespec="seconds"), setup_id),
    )


def seed_default_machines(connection: sqlite3.Connection) -> None:
    get_or_create_machine(connection, "machine1")
    get_or_create_machine(connection, "machine2")
    connection.execute(
        """
        UPDATE machines
        SET is_active = 0, updated_at = ?
        WHERE name IN ('1', '2')
          AND id NOT IN (
              SELECT machine_id FROM sessions WHERE machine_id IS NOT NULL
          )
        """,
        (datetime.now().isoformat(timespec="seconds"),),
    )
    default_machine = get_setting(connection, "default_machine_name")
    if default_machine is None or default_machine in {"1", "2"}:
        set_setting(connection, "default_machine_name", "machine1")


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
    return get_setting(connection, "default_machine_name") or "machine1"


def set_default_machine_name(connection: sqlite3.Connection, machine_name: str) -> None:
    get_or_create_machine(connection, machine_name)
    set_setting(connection, "default_machine_name", machine_name)


def upsert_setup_preset(
    connection: sqlite3.Connection,
    preset: SetupPreset,
    is_builtin: bool = False,
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    row = connection.execute(
        "SELECT id FROM setup_presets WHERE name = ?",
        (preset.name,),
    ).fetchone()
    if row is None:
        cursor = connection.execute(
            """
            INSERT INTO setup_presets (
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
            UPDATE setup_presets
            SET description = ?, updated_at = ?, is_builtin = ?, is_active = 1
            WHERE id = ?
            """,
            (preset.description, now, int(is_builtin), preset_id),
        )

    connection.execute("DELETE FROM setup_steps WHERE preset_id = ?", (preset_id,))
    setup_ids = [
        upsert_setup(connection, setup)
        for setup in preset.setups
    ]
    connection.executemany(
        """
        INSERT INTO setup_steps (
            preset_id,
            step_order,
            setup_id
        )
        VALUES (?, ?, ?)
        """,
        [
            (
                preset_id,
                index,
                setup_id,
            )
            for index, setup_id in enumerate(setup_ids, start=1)
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


def list_setup_presets(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT
            setup_presets.id,
            setup_presets.name,
            setup_presets.description,
            setup_presets.is_builtin,
            setup_presets.is_active,
            COUNT(setup_steps.id) AS step_count
        FROM setup_presets
        LEFT JOIN setup_steps
            ON setup_steps.preset_id = setup_presets.id
        WHERE setup_presets.is_active = 1
        GROUP BY setup_presets.id
        ORDER BY setup_presets.name
        """
    )
    return list(cursor.fetchall())


def get_setup_preset(
    connection: sqlite3.Connection,
    name: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id, name, description, is_builtin, is_active
        FROM setup_presets
        WHERE name = ? AND is_active = 1
        """,
        (name,),
    ).fetchone()


def list_setup_steps(
    connection: sqlite3.Connection,
    preset_id: int,
) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT
            setup_steps.id,
            setup_steps.preset_id,
            setup_steps.step_order,
            setups.id AS setup_id,
            setups.name AS label,
            setups.gantry_angle,
            setups.collimator_angle,
            setups.couch_angle,
            ('(-)' || setups.dx_negative_label || ' <- -> ' || setups.dx_positive_label || '(+)') AS x_axis_label,
            ('(-)' || setups.dy_negative_label || ' <- -> ' || setups.dy_positive_label || '(+)') AS y_axis_label,
            setups.dx_positive_label,
            setups.dx_negative_label,
            setups.dy_positive_label,
            setups.dy_negative_label,
            0 AS x_inverted,
            setups.field_size_px AS beam_size_px,
            setups.target_size_px,
            setups.pixel_size_mm,
            setups.beam_threshold,
            setups.ball_sensitivity
        FROM setup_steps
        JOIN setups ON setups.id = setup_steps.setup_id
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
    preset = get_setup_preset(connection, preset_name)
    if preset is None:
        rows = list_setup_presets(connection)
        available = ", ".join(row["name"] for row in rows)
        raise ValueError(f"unknown preset: {preset_name}. available: {available}")

    steps = list_setup_steps(connection, int(preset["id"]))
    return [
        AnalysisMetadata(
            gantry_angle=step["gantry_angle"],
            collimator_angle=step["collimator_angle"],
            couch_angle=step["couch_angle"],
            note=step["label"],
            x_axis_label=step["x_axis_label"],
            y_axis_label=step["y_axis_label"],
            dx_positive_label=step["dx_positive_label"],
            dx_negative_label=step["dx_negative_label"],
            dy_positive_label=step["dy_positive_label"],
            dy_negative_label=step["dy_negative_label"],
            x_inverted=bool(step["x_inverted"]),
            beam_size_px=step["beam_size_px"],
            target_size_px=step["target_size_px"],
            pixel_size_mm=step["pixel_size_mm"],
            beam_threshold=step["beam_threshold"],
            ball_sensitivity=step["ball_sensitivity"],
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
            x_axis_label,
            y_axis_label,
            dx_positive_label,
            dx_negative_label,
            dy_positive_label,
            dy_negative_label,
            x_inverted,
            algorithm_version,
            succeeded,
            failure_reason,
            note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        metadata.x_axis_label,
        metadata.y_axis_label,
        metadata.dx_positive_label,
        metadata.dx_negative_label,
        metadata.dy_positive_label,
        metadata.dy_negative_label,
        int(metadata.x_inverted),
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
