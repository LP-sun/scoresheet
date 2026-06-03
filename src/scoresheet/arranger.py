"""Arrangement helpers for converting MIDI material into score streams."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ArrangementError(RuntimeError):
    """Raised when an input file cannot be arranged."""


def load_midi(input_path: str | Path) -> Any:
    """Load a MIDI file as a music21 score."""

    try:
        from music21 import converter, stream
    except ModuleNotFoundError as exc:
        raise ArrangementError("music21 is required; install the project dependencies first") from exc

    path = Path(input_path)
    if not path.exists():
        raise ArrangementError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise ArrangementError(f"Input path is not a file: {path}")

    parsed = converter.parse(path)
    if isinstance(parsed, stream.Score):
        return parsed

    score = stream.Score()
    score.insert(0, parsed)
    return score


def arrange(input_path: str | Path) -> Any:
    """Create an arranged score from a MIDI input.

    The current implementation preserves the parsed MIDI content as a score.
    This function is the extension point for future orchestration logic.
    """

    return load_midi(input_path)
