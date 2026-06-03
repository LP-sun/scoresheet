"""Unified command-line interface for scoresheet."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import warnings

from .arranger import arrange_file
from .exporters import export_arrangement, infer_export_format
from .instrumentation import ALIASES, ENSEMBLES, canonical_ensemble_name, get_ensemble


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scoresheet", description="Rule-based MIDI piano-to-ensemble arranger.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    arrange = subparsers.add_parser("arrange", help="Arrange one MIDI file")
    arrange.add_argument("input", type=Path, help="Input .mid/.midi file")
    arrange.add_argument("--ensemble", default="small_orchestra", help="Target ensemble or alias")
    arrange.add_argument("--output", "-o", type=Path, required=True, help="Output .musicxml/.xml/.mxl/.mid file")
    arrange.add_argument("--format", choices=("musicxml", "xml", "mxl", "midi", "mid"), help="Override output format")
    arrange.add_argument("--quantization-unit", type=float, default=0.25, help="Beat grid unit; 0.25 means sixteenth notes")
    arrange.set_defaults(func=_run_arrange)

    batch = subparsers.add_parser("batch-arrange", help="Arrange all MIDI files in a directory")
    batch.add_argument("input_dir", type=Path, help="Directory containing .mid/.midi files")
    batch.add_argument("--ensemble", default="small_orchestra", help="Target ensemble or alias")
    batch.add_argument("--all-ensembles", action="store_true", help="Export every supported canonical ensemble")
    batch.add_argument("--format", default="musicxml", choices=("musicxml", "xml", "mxl", "midi", "mid"), help="Output format")
    batch.add_argument("--out-dir", type=Path, required=True, help="Directory for generated arrangements")
    batch.add_argument("--quantization-unit", type=float, default=0.25, help="Beat grid unit; 0.25 means sixteenth notes")
    batch.set_defaults(func=_run_batch_arrange)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _run_arrange(args: argparse.Namespace) -> int:
    _validate_input_file(args.input)
    get_ensemble(args.ensemble)
    infer_export_format(args.output, args.format)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        arrangement = arrange_file(args.input, ensemble=args.ensemble, quantization_unit=args.quantization_unit)
        written = export_arrangement(arrangement, args.output, args.format)
    _print_warnings(caught)
    print(written)
    return 0


def _run_batch_arrange(args: argparse.Namespace) -> int:
    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {args.input_dir}")
    if not args.input_dir.is_dir():
        raise ValueError(f"Input path is not a directory: {args.input_dir}")
    infer_export_format(f"dummy.{args.format}", args.format)

    ensembles = sorted(ENSEMBLES) if args.all_ensembles else [canonical_ensemble_name(args.ensemble)]
    for ensemble in ensembles:
        get_ensemble(ensemble)

    midi_files = sorted(path for path in args.input_dir.iterdir() if path.is_file() and path.suffix.lower() in {".mid", ".midi"})
    if not midi_files:
        raise ValueError(f"No .mid/.midi files found in input directory: {args.input_dir}")

    extension = _extension_for_format(args.format)
    successes = 0
    failures: list[str] = []
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for midi_file in midi_files:
        for ensemble in ensembles:
            output_dir = args.out_dir / ensemble
            output_path = output_dir / f"{midi_file.stem}_{ensemble}.{extension}"
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    arrangement = arrange_file(midi_file, ensemble=ensemble, quantization_unit=args.quantization_unit)
                    export_arrangement(arrangement, output_path, args.format)
                _print_warnings(caught, prefix=f"{midi_file.name}/{ensemble}")
                print(output_path)
                successes += 1
            except (OSError, ValueError, FileNotFoundError) as exc:
                failures.append(f"{midi_file}: {ensemble}: {exc}")
                print(f"error: {midi_file}: {ensemble}: {exc}", file=sys.stderr)

    print(f"summary: success={successes} failure={len(failures)}")
    return 1 if failures else 0


def _validate_input_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Input MIDI file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")
    if path.suffix.lower() not in {".mid", ".midi"}:
        raise ValueError(f"Input file must end with .mid or .midi: {path}")


def _extension_for_format(export_format: str) -> str:
    normalized = infer_export_format(f"dummy.{export_format}", export_format)
    return "mid" if normalized == "midi" else "musicxml"


def _print_warnings(caught: list[warnings.WarningMessage], prefix: str | None = None) -> None:
    for warning in caught:
        label = f"warning: {prefix}:" if prefix else "warning:"
        print(f"{label} {warning.message}", file=sys.stderr)


def supported_ensembles_text() -> str:
    """Return supported ensembles and aliases for documentation/tests."""

    return ", ".join(sorted((*ENSEMBLES.keys(), *ALIASES.keys())))


if __name__ == "__main__":
    raise SystemExit(main())
