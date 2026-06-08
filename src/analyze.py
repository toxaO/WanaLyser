from __future__ import annotations

import argparse
from pathlib import Path

from core import (
    AnalysisParameters,
    analyze_path,
    format_result_line,
    save_debug_output,
)


def main() -> int:
    args = parse_args()
    parameters = AnalysisParameters(
        beam_threshold=args.beam_threshold,
        ball_sensitivity=args.ball_sensitivity,
        pixel_size_mm=args.pixel_size,
    )

    analyses = analyze_path(args.input, parameters)
    if not analyses:
        print(f"no supported images found: {args.input}")
        return 1

    save_debug_output(analyses, args.output, write_images=not args.no_images)

    for analysis in analyses:
        print(format_result_line(analysis.result))
    print(f"saved debug output: {args.output}")
    return 0


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
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
