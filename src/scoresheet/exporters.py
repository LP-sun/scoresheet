"""Export ArrangedScore objects to MusicXML or MIDI via music21."""

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
