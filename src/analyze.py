from __future__ import annotations

import argparse
from pathlib import Path

from core import (
    AnalysisParameters,
    analyze_path,
    format_result_line,
    save_debug_output,
)
from database import (
    AnalysisMetadata,
    connect_database,
    create_session,
    init_db,
    list_condition_presets,
    list_condition_steps,
    list_analysis_results,
    list_machines,
    metadata_for_preset,
    save_analysis_results,
)
from workflow import (
    analyze_plan,
    build_analysis_plan_from_preset,
    format_plan,
)


def main() -> int:
    args = parse_args()
    if args.list_presets:
        connection = connect_database(args.db)
        try:
            init_db(connection)
            print_condition_presets(connection)
        finally:
            connection.close()
        return 0

    if args.list_machines:
        connection = connect_database(args.db)
        try:
            init_db(connection)
            print_machines(list_machines(connection))
        finally:
            connection.close()
        return 0

    if args.list_db:
        connection = connect_database(args.db)
        try:
            init_db(connection)
            print_db_results(list_analysis_results(connection, args.limit))
        finally:
            connection.close()
        return 0

    parameters = AnalysisParameters(
        beam_threshold=args.beam_threshold,
        ball_sensitivity=args.ball_sensitivity,
        pixel_size_mm=args.pixel_size,
    )

    plan = None
    if args.preset is not None:
        connection = connect_database(args.db)
        try:
            init_db(connection)
            plan = build_analysis_plan_from_preset(args.input, connection, args.preset)
        finally:
            connection.close()
        if args.preview_plan:
            print_plan(plan)
            return 0
        analyses = analyze_plan(plan, parameters)
    else:
        if args.preview_plan:
            print("--preview-plan requires --preset")
            return 1
        analyses = analyze_path(args.input, parameters)

    if not analyses:
        print(f"no supported images found: {args.input}")
        return 1

    save_debug_output(analyses, args.output, write_images=not args.no_images)

    if args.save_db:
        metadata = build_metadata(args, len(analyses))
        connection = connect_database(args.db)
        try:
            init_db(connection)
            session_id = create_session(
                connection,
                inspection_type=args.inspection_type,
                machine_name=args.machine_name,
                note=args.session_note,
            )
            save_analysis_results(connection, session_id, analyses, metadata)
        finally:
            connection.close()
        print(f"saved database results: {args.db} (session_id={session_id})")

    for analysis in analyses:
        print(format_result_line(analysis.result))
    print(f"saved debug output: {args.output}")
    return 0


def build_metadata(args, image_count: int) -> AnalysisMetadata | list[AnalysisMetadata]:
    if args.preset is not None:
        connection = connect_database(args.db)
        try:
            init_db(connection)
            metadata = metadata_for_preset(connection, args.preset, image_count)
        finally:
            connection.close()
        if args.result_note is not None:
            metadata = [
                AnalysisMetadata(
                    gantry_angle=item.gantry_angle,
                    collimator_angle=item.collimator_angle,
                    couch_angle=item.couch_angle,
                    note=f"{item.note}: {args.result_note}",
                )
                for item in metadata
            ]
        return metadata

    return AnalysisMetadata(
        gantry_angle=args.gantry_angle,
        collimator_angle=args.collimator_angle,
        couch_angle=args.couch_angle,
        note=args.result_note,
    )


def print_plan(plan) -> None:
    for line in format_plan(plan):
        print(line)


def print_condition_presets(connection) -> None:
    for preset in list_condition_presets(connection):
        builtin = " builtin" if preset["is_builtin"] else ""
        print(
            f'{preset["name"]}: {preset["description"]} '
            f'({preset["step_count"]} steps{builtin})'
        )
        for step in list_condition_steps(connection, int(preset["id"])):
            print(
                f'  {step["step_order"]:02d}. {step["label"]} '
                f'G={step["gantry_angle"]} '
                f'C={step["collimator_angle"]} '
                f'Cou={step["couch_angle"]}'
            )


def print_db_results(rows) -> None:
    if not rows:
        print("no database results")
        return
    for row in rows:
        status = status_text(row["succeeded"], row["dx_mm"], row["dy_mm"])
        print(
            f'{row["id"]}: {row["analyzed_at"]} '
            f'{row["image_name"]} '
            f'machine={row["machine_name"]} '
            f'G={row["gantry_angle"]} '
            f'C={row["collimator_angle"]} '
            f'Cou={row["couch_angle"]} '
            f'dx={row["dx_mm"]} dy={row["dy_mm"]} '
            f'[{status}]'
        )


def status_text(succeeded, dx_mm, dy_mm) -> str:
    if not succeeded:
        return "NG"
    try:
        dx = float(dx_mm)
        dy = float(dy_mm)
    except (TypeError, ValueError):
        return "NG"
    return "OK" if abs(dx) <= 1.0 and abs(dy) <= 1.0 else "NG"


def print_machines(rows) -> None:
    if not rows:
        print("no machines")
        return
    for row in rows:
        print(f'{row["id"]}: {row["name"]}')


def parse_args() -> argparse.Namespace:
    default_input = Path("sample/size")
    if not default_input.exists():
        default_input = Path(".")

    parser = argparse.ArgumentParser(
        description="Analyze Winston-Lutz images and write debug images."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=default_input,
        help="image file or directory. default: sample/size when available",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("log/core_debug"),
        help="output directory for result.csv, result.json, and debug images",
    )
    parser.add_argument(
        "--beam-threshold",
        type=int,
        default=0,
        help="beam threshold. 0 uses Otsu thresholding",
    )
    parser.add_argument(
        "--ball-sensitivity",
        type=int,
        default=10,
        help="Hough circle sensitivity for ball detection. smaller values detect more candidates",
    )
    parser.add_argument(
        "--pixel-size",
        type=float,
        default=0.242,
        help="pixel size in millimeters",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="write only JSON and CSV results",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/wanalyzer.sqlite"),
        help="SQLite database path. default: data/wanalyzer.sqlite",
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="save analysis results to the SQLite database",
    )
    parser.add_argument(
        "--list-db",
        action="store_true",
        help="list recent database results and exit",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="list database condition presets and exit",
    )
    parser.add_argument(
        "--list-machines",
        action="store_true",
        help="list machines and exit",
    )
    parser.add_argument(
        "--preset",
        help="analysis condition preset name. Example: daily-14",
    )
    parser.add_argument(
        "--preview-plan",
        action="store_true",
        help="show image-to-condition mapping and exit. Requires --preset",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="number of database rows to show with --list-db",
    )
    parser.add_argument(
        "--inspection-type",
        default="unspecified",
        help="inspection type saved in the session",
    )
    parser.add_argument(
        "--machine-name",
        help="machine name saved in the session",
    )
    parser.add_argument(
        "--session-note",
        help="note saved in the session",
    )
    parser.add_argument(
        "--result-note",
        help="note saved on each analysis result",
    )
    parser.add_argument(
        "--gantry-angle",
        type=float,
        help="gantry angle saved on each analysis result",
    )
    parser.add_argument(
        "--collimator-angle",
        type=float,
        help="collimator angle saved on each analysis result",
    )
    parser.add_argument(
        "--couch-angle",
        type=float,
        help="couch angle saved on each analysis result",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
