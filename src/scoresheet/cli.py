"""Command line interface for scoresheet."""

from __future__ import annotations

import argparse
from pathlib import Path

from scoresheet.arranger import ArrangementError, arrange
from scoresheet.exporters import ExportError, export_score, infer_format


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="scoresheet",
        description="Convert a MIDI file into an arranged MIDI or MusicXML score.",
    )
    parser.add_argument("input", type=Path, help="Input MIDI file path")
    parser.add_argument("output", type=Path, help="Output .mid, .midi, .musicxml, or .xml file path")
    parser.add_argument(
        "--format",
        "-f",
        choices=("mid", "midi", "musicxml", "xml"),
        help="Output format. Defaults to the output file extension.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the scoresheet command line interface."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        output_format = args.format or infer_format(args.output)
        score = arrange(args.input)
        written_path = export_score(score, args.output, output_format)
    except (ArrangementError, ExportError, OSError) as exc:
        parser.error(str(exc))
        return 2

    print(f"Wrote {written_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
