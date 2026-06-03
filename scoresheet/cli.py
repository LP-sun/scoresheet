"""Command-line interface for scoresheet."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import warnings

from .midi_parser import parse_midi
from .musicxml_exporter import export_midi, export_musicxml, export_parts_musicxml
from .musescore_backend import convert_midi_with_musescore
from .musescore_validator import validate_with_musescore
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
        choices=("musicxml", "mid", "mscz", "both"),
        default="musicxml",
        help="Output format for the full score",
    )
    parser.add_argument(
        "--backend",
        choices=("native", "musescore", "both"),
        default="native",
        help="Score export backend: native MusicXML, MuseScore CLI conversion, or both",
    )
    parser.add_argument(
        "--pitch-mode",
        choices=("written", "concert"),
        default="written",
        help="MusicXML pitch handling mode",
    )
    parser.add_argument("--parts", action="store_true", help="Also write individual MusicXML part files")
    parser.add_argument(
        "--validate-musescore",
        action="store_true",
        help="Optionally validate generated MusicXML with MuseScore Studio CLI converter mode",
    )
    parser.add_argument(
        "--musescore-executable",
        type=Path,
        default=None,
        help="Path or command name for MuseScore validation or conversion",
    )
    parser.add_argument(
        "--midi-operations",
        type=Path,
        default=None,
        help="MuseScore MIDI import operations file passed with -M for MuseScore backend conversion",
    )
    parser.add_argument("--quantization-unit", type=float, default=0.25, help="Beat grid unit, e.g. 0.25 = sixteenth note")
    return parser


def _print_musescore_failure(result: object) -> None:
    reason = getattr(result, "reason", None) or "MuseScore conversion failed"
    print(f"error: MuseScore conversion failed: {reason}", file=sys.stderr)
    stdout = getattr(result, "stdout", "")
    stderr = getattr(result, "stderr", "")
    if stdout:
        print(f"MuseScore stdout:\n{stdout.strip()}", file=sys.stderr)
    if stderr:
        print(f"MuseScore stderr:\n{stderr.strip()}", file=sys.stderr)


def _convert_with_musescore_or_fail(
    midi_path: Path,
    output_path: Path,
    executable: Path | None,
    midi_operations: Path | None,
) -> bool:
    result = convert_midi_with_musescore(
        midi_path,
        output_path,
        executable=executable,
        midi_operations=midi_operations,
    )
    if result.skipped or not result.ok:
        _print_musescore_failure(result)
        return False
    print(output_path)
    return True


def run(args: argparse.Namespace) -> int:
    input_path: Path = args.input
    if not input_path.exists():
        print(f"error: input MIDI file does not exist: {input_path}", file=sys.stderr)
        return 2
    if input_path.suffix.lower() not in {".mid", ".midi"}:
        print(f"warning: input file does not end with .mid/.midi: {input_path}", file=sys.stderr)

    if args.backend == "native" and args.format == "mscz":
        print("error: mscz requires --backend musescore or both", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parsed = parse_midi(input_path)
        config = OrchestrationConfig(
            target_ensemble=args.ensemble,
            quantization_unit=args.quantization_unit,
            output_musicxml=args.backend in {"native", "both"} and args.format in {"musicxml", "both"},
            output_midi=args.format in {"mid", "both", "mscz"} or args.backend in {"musescore", "both"},
            output_parts=args.parts,
        )
        arranged = orchestrate(parsed, config)

    for warning in caught:
        print(f"warning: {warning.message}", file=sys.stderr)

    stem = input_path.stem
    title = f"{stem} - {args.ensemble}"

    if args.backend == "native":
        xml_path: Path | None = None
        if args.format in {"musicxml", "both"}:
            xml_path = args.output_dir / f"{stem}_{args.ensemble}.musicxml"
            export_musicxml(arranged, xml_path, title=title, pitch_mode=args.pitch_mode)
            print(xml_path)

            if args.validate_musescore:
                result = validate_with_musescore(xml_path, executable=args.musescore_executable)
                if result.skipped:
                    print(f"warning: MuseScore validation skipped: {result.reason}", file=sys.stderr)
                elif not result.ok:
                    print(f"error: MuseScore validation failed: {result.reason}", file=sys.stderr)
                    if result.stdout:
                        print(f"MuseScore stdout:\n{result.stdout.strip()}", file=sys.stderr)
                    if result.stderr:
                        print(f"MuseScore stderr:\n{result.stderr.strip()}", file=sys.stderr)
                    return 1
                elif result.output_path is not None:
                    print(f"MuseScore validated: {result.output_path}")
        if args.format in {"mid", "both"}:
            midi_path = args.output_dir / f"{stem}_{args.ensemble}.mid"
            export_midi(arranged, midi_path, title=title)
            print(midi_path)
        if args.parts:
            parts_dir = args.output_dir / "parts"
            for path in export_parts_musicxml(arranged, parts_dir, title_prefix=stem, pitch_mode=args.pitch_mode):
                print(path)
        return 0

    midi_path = args.output_dir / f"{stem}_{args.ensemble}.mid"
    export_midi(arranged, midi_path, title=title)
    print(midi_path)

    if args.backend == "musescore":
        conversion_targets: list[Path] = []
        if args.format == "mscz":
            conversion_targets.append(args.output_dir / f"{stem}_{args.ensemble}.mscz")
        elif args.format == "musicxml":
            conversion_targets.append(args.output_dir / f"{stem}_{args.ensemble}.musicxml")
        elif args.format == "both":
            conversion_targets.extend(
                [
                    args.output_dir / f"{stem}_{args.ensemble}.mscz",
                    args.output_dir / f"{stem}_{args.ensemble}.musicxml",
                ]
            )
        elif args.format == "mid":
            conversion_targets = []

        for output_path in conversion_targets:
            if not _convert_with_musescore_or_fail(
                midi_path,
                output_path,
                args.musescore_executable,
                args.midi_operations,
            ):
                return 1
        return 0

    # args.backend == "both"
    native_xml_path = args.output_dir / f"{stem}_{args.ensemble}.native.musicxml"
    export_musicxml(arranged, native_xml_path, title=title, pitch_mode=args.pitch_mode)
    print(native_xml_path)

    musescore_targets = [
        args.output_dir / f"{stem}_{args.ensemble}.musescore.mscz",
        args.output_dir / f"{stem}_{args.ensemble}.musescore.musicxml",
    ]
    for output_path in musescore_targets:
        if not _convert_with_musescore_or_fail(
            midi_path,
            output_path,
            args.musescore_executable,
            args.midi_operations,
        ):
            return 1

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
