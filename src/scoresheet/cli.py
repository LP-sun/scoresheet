"""Unified command-line interface for scoresheet."""
"""Command line interface for scoresheet."""

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
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SUPPORTED_ENSEMBLES: tuple[str, ...] = (
    "orchestra",
    "string_quartet",
    "wind_quintet",
)
SUPPORTED_FORMATS: tuple[str, ...] = ("mid", "musicxml")


@dataclass(frozen=True)
class BatchFailure:
    """A single failed input file from a batch arrange run."""

    source: Path
    ensemble: str
    output_format: str
    error: str


@dataclass(frozen=True)
class BatchReport:
    """Summary for a batch arrange run."""

    succeeded: int
    failed: int
    failures: tuple[BatchFailure, ...]


def arrange_midi(source: Path, ensemble: str, output_format: str, destination: Path) -> None:
    """Arrange one MIDI file for ``ensemble`` and write it to ``destination``.

    The current implementation preserves MIDI data for MIDI output and writes a
    small MusicXML document for MusicXML output. The function is intentionally
    isolated so future arranging logic can replace it, and tests can inject
    failures around individual files without exercising the whole CLI.
    """

    if ensemble not in SUPPORTED_ENSEMBLES:
        raise ValueError(f"Unsupported ensemble: {ensemble}")
    if output_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {output_format}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "mid":
        shutil.copyfile(source, destination)
        return

    destination.write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<score-partwise version=\"4.0\">\n"
        f"  <work><work-title>{source.stem} - {ensemble}</work-title></work>\n"
        "  <part-list/>\n"
        "</score-partwise>\n",
        encoding="utf-8",
    )


def batch_output_path(source: Path, out_dir: Path, ensemble: str, output_format: str) -> Path:
    """Return the structured output path for a batch-arranged MIDI file."""

    suffix = ".mid" if output_format == "mid" else ".musicxml"
    return out_dir / ensemble / output_format / f"{source.stem}{suffix}"


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def iter_midi_files(input_dir: Path, out_dir: Path) -> Iterable[Path]:
    """Yield ``.mid`` files under ``input_dir`` while skipping ``out_dir``."""

    input_root = input_dir.resolve()
    output_root = out_dir.resolve()
    for midi_file in sorted(input_root.rglob("*.mid")):
        resolved = midi_file.resolve()
        if _is_relative_to(resolved, output_root):
            continue
        yield midi_file


def batch_arrange(
    input_dir: Path,
    *,
    ensembles: Sequence[str],
    output_format: str,
    out_dir: Path,
) -> BatchReport:
    """Arrange every MIDI file in ``input_dir`` for the requested ensembles."""

    failures: list[BatchFailure] = []
    succeeded = 0

    for source in iter_midi_files(input_dir, out_dir):
        for ensemble in ensembles:
            destination = batch_output_path(source, out_dir, ensemble, output_format)
            try:
                arrange_midi(source, ensemble, output_format, destination)
            except Exception as exc:  # noqa: BLE001 - report per-file failures and continue.
                failures.append(
                    BatchFailure(
                        source=source,
                        ensemble=ensemble,
                        output_format=output_format,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
            else:
                succeeded += 1

    return BatchReport(succeeded=succeeded, failed=len(failures), failures=tuple(failures))


def _print_report(report: BatchReport) -> None:
    print(f"Success: {report.succeeded}")
    print(f"Failed: {report.failed}")
    if report.failures:
        print("Failures:")
        for failure in report.failures:
            print(
                f"- {failure.source} [{failure.ensemble}/{failure.output_format}]: "
                f"{failure.error}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scoresheet")
    subparsers = parser.add_subparsers(dest="command", required=True)

    batch_parser = subparsers.add_parser(
        "batch-arrange",
        help="Arrange every .mid file under a directory.",
    )
    batch_parser.add_argument("input_dir", type=Path, help="Directory to scan for .mid files.")
    batch_parser.add_argument(
        "--ensemble",
        choices=SUPPORTED_ENSEMBLES,
        help="Target ensemble for generated arrangements.",
    )
    batch_parser.add_argument(
        "--all-ensembles",
        action="store_true",
        help="Generate arrangements for every supported ensemble.",
    )
    batch_parser.add_argument(
        "--format",
        dest="output_format",
        choices=SUPPORTED_FORMATS,
        default="mid",
        help="Output format to generate.",
    )
    batch_parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory where arranged output should be written.",
    )
    batch_parser.set_defaults(func=_handle_batch_arrange)
    return parser


def _handle_batch_arrange(args: argparse.Namespace) -> int:
    if args.all_ensembles and args.ensemble:
        raise SystemExit("Use either --ensemble or --all-ensembles, not both.")
    if not args.all_ensembles and not args.ensemble:
        raise SystemExit("Specify --ensemble or --all-ensembles.")

    ensembles = SUPPORTED_ENSEMBLES if args.all_ensembles else (args.ensemble,)
    report = batch_arrange(
        args.input_dir,
        ensembles=ensembles,
        output_format=args.output_format,
        out_dir=args.out_dir,
    )
    _print_report(report)
    return 1 if report.failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
