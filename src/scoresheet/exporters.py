"""Export helpers for arranged scores."""

from __future__ import annotations

from pathlib import Path

from typing import Any

SUPPORTED_FORMATS = {"mid", "midi", "musicxml", "xml"}


class ExportError(RuntimeError):
    """Raised when a score cannot be exported."""


def normalize_format(output_format: str) -> str:
    """Normalize user-facing output formats to music21 writer formats."""

    normalized = output_format.lower().lstrip(".")
    if normalized not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise ExportError(f"Unsupported output format '{output_format}'. Supported: {supported}")
    if normalized == "midi":
        return "mid"
    if normalized == "xml":
        return "musicxml"
    return normalized


def infer_format(output_path: str | Path) -> str:
    """Infer the output format from a file extension."""

    suffix = Path(output_path).suffix
    if not suffix:
        raise ExportError("Cannot infer output format from a path without an extension")
    return normalize_format(suffix)


def export_score(score: Any, output_path: str | Path, output_format: str | None = None) -> Path:
    """Write a score to MIDI or MusicXML and return the output path."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer_format = normalize_format(output_format) if output_format else infer_format(path)
    written = score.write(writer_format, fp=path)
    return Path(written)
