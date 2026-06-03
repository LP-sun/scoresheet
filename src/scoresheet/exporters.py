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
"""Export arranged scores to MIDI and MusicXML."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Literal

from .arranger import ArrangedScore, NoteEvent, _require_music21
from .instrumentation import InstrumentSpec

ExportFormat = Literal["midi", "musicxml"]


def _make_music21_instrument(spec: InstrumentSpec):
    music21 = _require_music21()
    inst = None
    if spec.music21_class and hasattr(music21.instrument, spec.music21_class):
        cls = getattr(music21.instrument, spec.music21_class)
        inst = cls()
    else:
        inst = music21.instrument.Instrument()
    inst.partName = spec.name
    inst.instrumentName = spec.name
    inst.midiProgram = spec.gm_program
    return inst


def _copy_global_metadata(source_score: object, target_score: object) -> None:
    """Copy tempo, meter, key, and score metadata from a source stream."""

    music21 = _require_music21()
    if getattr(source_score, "metadata", None) is not None:
        target_score.metadata = copy.deepcopy(source_score.metadata)

    global_classes = (
        music21.tempo.MetronomeMark,
        music21.meter.TimeSignature,
        music21.key.KeySignature,
        music21.key.Key,
    )
    seen: set[tuple[str, float, str]] = set()
    for element in source_score.recurse().getElementsByClass(global_classes):
        try:
            offset = float(element.getOffsetInHierarchy(source_score))
        except Exception:  # pragma: no cover - defensive for unusual streams
            offset = float(getattr(element, "offset", 0.0) or 0.0)
        key = (element.classes[0], offset, str(element))
        if key in seen:
            continue
        seen.add(key)
        target_score.insert(offset, copy.deepcopy(element))


def _insert_note(part: object, event: NoteEvent) -> None:
    music21 = _require_music21()
    note = music21.note.Note(event.pitch)
    note.quarterLength = max(0.0625, event.duration)
    note.volume.velocity = max(1, min(127, event.velocity))
    part.insert(event.start, note)


def to_music21_score(arranged: ArrangedScore):
    """Build a :class:`music21.stream.Score` from an arrangement."""

    music21 = _require_music21()
    score = music21.stream.Score()
    _copy_global_metadata(arranged.analysis.original_score, score)

    for spec in arranged.ensemble.instruments:
        part = music21.stream.Part(id=spec.name.replace(" ", "_"))
        part.partName = spec.name
        part.insert(0, _make_music21_instrument(spec))
        for event in arranged.assignments.get(spec.name, []):
            _insert_note(part, event)
        part.makeRests(inPlace=True, fillGaps=True)
        part.makeMeasures(inPlace=True)
        score.insert(0, part)
    return score


def infer_export_format(path: str | Path, explicit: str | None = None) -> ExportFormat:
    """Infer export format from CLI option or output suffix."""

    if explicit:
        normalized = explicit.lower().replace("-", "")
        if normalized in {"midi", "mid"}:
            return "midi"
        if normalized in {"musicxml", "xml", "mxl"}:
            return "musicxml"
        raise ValueError("format must be one of: midi, mid, musicxml, xml, mxl")

    suffix = Path(path).suffix.lower()
    if suffix in {".mid", ".midi"}:
        return "midi"
    if suffix in {".musicxml", ".xml", ".mxl"}:
        return "musicxml"
    raise ValueError("Could not infer output format; use --format midi or --format musicxml")


def export_arrangement(arranged: ArrangedScore, output_path: str | Path, format: str | None = None) -> Path:
    """Write an arrangement as MIDI or MusicXML and return the written path."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    export_format = infer_export_format(output, format)
    score = to_music21_score(arranged)
    if export_format == "midi":
        written = score.write("midi", fp=str(output))
    else:
        written = score.write("musicxml", fp=str(output))
    return Path(written)
