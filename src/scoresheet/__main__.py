"""Command-line interface for scoresheet."""

from __future__ import annotations

import argparse
from pathlib import Path

from .arranger import arrange_file
from .exporters import export_arrangement
from .instrumentation import ENSEMBLES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scoresheet", description="Arrange piano MIDI into ensemble MIDI/MusicXML.")
    subparsers = parser.add_subparsers(dest="command")

    arrange = subparsers.add_parser("arrange", help="arrange an input MIDI file")
    arrange.add_argument("input", type=Path, help="input MIDI path, e.g. 飞鼠进行曲.mid")
    arrange.add_argument(
        "--ensemble",
        default="string_quartet",
        metavar="ENSEMBLE",
        help=f"target ensemble (choices: {', '.join(sorted(ENSEMBLES.keys()))})",
    )
    arrange.add_argument("--output", "-o", required=True, type=Path, help="output .mid/.musicxml path")
    arrange.add_argument("--format", choices=("midi", "mid", "musicxml", "xml", "mxl"), help="override output format")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "arrange":
        parser.print_help()
        return 2

    arranged = arrange_file(args.input, args.ensemble)
    written = export_arrangement(arranged, args.output, args.format)
    print(f"Wrote {written}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
