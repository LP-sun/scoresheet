"""Export ArrangedScore objects to MusicXML or MIDI via music21."""
"""Export helpers for arranged scores."""

from __future__ import annotations

from pathlib import Path

from music21 import clef, duration, instrument, key, metadata, midi, note, stream, tempo, meter

from .arranger import ArrangedNote, ArrangedScore
from .instrumentation import InstrumentSpec

MIDI_FORMATS = {"mid", "midi"}
MUSICXML_FORMATS = {"musicxml", "xml", "mxl"}


def to_music21_score(arrangement: ArrangedScore, title: str | None = None) -> stream.Score:
    """Convert an ArrangedScore into a music21 Score."""

    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = title or f"{arrangement.source.stem} - {arrangement.ensemble.name}"
    score.insert(0, tempo.MetronomeMark(number=arrangement.tempo_bpm))
    score.insert(0, meter.TimeSignature(f"{arrangement.time_signature[0]}/{arrangement.time_signature[1]}"))
    if arrangement.key_signature:
        maybe_key = _parse_key(arrangement.key_signature)
        if maybe_key is not None:
            score.insert(0, maybe_key)

    for spec in arrangement.ensemble.instruments:
        part = stream.Part(id=_safe_id(spec.name))
        part.partName = spec.name
        part.insert(0, _to_music21_instrument(spec))
        part.insert(0, _to_clef(spec.clef))
        part.insert(0, meter.TimeSignature(f"{arrangement.time_signature[0]}/{arrangement.time_signature[1]}"))
        for arranged_note in arrangement.notes_by_instrument.get(spec.name, ()):
            part.insert(arranged_note.start_beat, _to_note(arranged_note))
        part.makeMeasures(inPlace=True)
        score.insert(0, part)
    return score


def infer_export_format(output_path: str | Path, explicit_format: str | None = None) -> str:
    """Infer normalized export format from an explicit value or output suffix."""

    raw = explicit_format or Path(output_path).suffix.lstrip(".")
    normalized = raw.lower()
    if normalized in MIDI_FORMATS:
        return "midi"
    if normalized in MUSICXML_FORMATS:
        return "musicxml"
    allowed = ", ".join(sorted((*MIDI_FORMATS, *MUSICXML_FORMATS)))
    raise ValueError(f"Cannot infer export format from '{raw}'. Use one of: {allowed}")


def export_arrangement(arrangement: ArrangedScore, output_path: str | Path, export_format: str | None = None) -> Path:
    """Export an arrangement as MusicXML or MIDI and return the written path."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = infer_export_format(output, export_format)
    score = to_music21_score(arrangement)
    if normalized == "musicxml":
        return Path(score.write("musicxml", fp=str(output)))
    if normalized == "midi":
        midi_file = midi.translate.music21ObjectToMidiFile(score)
        midi_file.open(str(output), "wb")
        try:
            midi_file.write()
        finally:
            midi_file.close()
        return output
    raise AssertionError(f"Unhandled normalized export format: {normalized}")


def _to_note(arranged_note: ArrangedNote) -> note.Note:
    n = note.Note(arranged_note.pitch)
    n.duration = duration.Duration(arranged_note.duration_beats)
    n.volume.velocity = arranged_note.velocity
    n.editorial.role = arranged_note.role
    return n


def _to_music21_instrument(spec: InstrumentSpec) -> instrument.Instrument:
    inst = instrument.fromString(spec.name)
    inst.instrumentName = spec.name
    inst.partName = spec.name
    inst.midiProgram = spec.midi_program
    return inst


def _to_clef(name: str) -> clef.Clef:
    if name == "bass":
        return clef.BassClef()
    if name == "alto":
        return clef.AltoClef()
    if name == "tenor":
        return clef.TenorClef()
    return clef.TrebleClef()


def _parse_key(value: str) -> key.Key | None:
    try:
        return key.Key(value)
    except Exception:
        return None


def _safe_id(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_") or "part"
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
