"""Command-line interface for scoresheet."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import warnings

from .midi_parser import parse_midi
from .musicxml_exporter import export_midi, export_musicxml, export_parts_musicxml
from .orchestrator import ENSEMBLES, OrchestrationConfig, orchestrate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scoresheet",
        description="Arrange a piano MIDI file into a rule-based ensemble MusicXML/MIDI score.",
    )
    parser.add_argument("input", type=Path, help="Input piano .mid/.midi file")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("output"), help="Directory for generated files")
    parser.add_argument(
        "--ensemble",
        default="small_orchestra",
        choices=sorted(ENSEMBLES),
        help="Target ensemble preset",
    )
    parser.add_argument(
        "--format",
        choices=("musicxml", "mid", "both"),
        default="musicxml",
        help="Output format for the full score",
    )
    parser.add_argument(
        "--pitch-mode",
        choices=("written", "concert"),
        default="written",
        help="MusicXML pitch handling mode",
    )
    parser.add_argument("--parts", action="store_true", help="Also write individual MusicXML part files")
    parser.add_argument("--quantization-unit", type=float, default=0.25, help="Beat grid unit, e.g. 0.25 = sixteenth note")
    return parser


def run(args: argparse.Namespace) -> int:
    input_path: Path = args.input
    if not input_path.exists():
        print(f"error: input MIDI file does not exist: {input_path}", file=sys.stderr)
        return 2
    if input_path.suffix.lower() not in {".mid", ".midi"}:
        print(f"warning: input file does not end with .mid/.midi: {input_path}", file=sys.stderr)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parsed = parse_midi(input_path)
        config = OrchestrationConfig(
            target_ensemble=args.ensemble,
            quantization_unit=args.quantization_unit,
            output_musicxml=args.format in {"musicxml", "both"},
            output_midi=args.format in {"mid", "both"},
            output_parts=args.parts,
        )
        arranged = orchestrate(parsed, config)

    for warning in caught:
        print(f"warning: {warning.message}", file=sys.stderr)

    stem = input_path.stem
    if args.format in {"musicxml", "both"}:
        xml_path = args.output_dir / f"{stem}_{args.ensemble}.musicxml"
        export_musicxml(arranged, xml_path, title=f"{stem} - {args.ensemble}", pitch_mode=args.pitch_mode)
        print(xml_path)
    if args.format in {"mid", "both"}:
        midi_path = args.output_dir / f"{stem}_{args.ensemble}.mid"
        export_midi(arranged, midi_path, title=f"{stem} - {args.ensemble}")
        print(midi_path)
    if args.parts:
        parts_dir = args.output_dir / "parts"
        for path in export_parts_musicxml(arranged, parts_dir, title_prefix=stem, pitch_mode=args.pitch_mode):
            print(path)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
