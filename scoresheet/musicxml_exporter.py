"""music21-based score construction and export helpers."""

from __future__ import annotations

from pathlib import Path

from music21 import clef, duration, instrument, key, metadata, midi, note, stream, tempo, meter

from .orchestrator import OrchestratedNote, OrchestrationResult


def build_score(result: OrchestrationResult, title: str = "Orchestrated score") -> stream.Score:
    """Build a music21 Score from an orchestration result."""

    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = title
    score.insert(0, tempo.MetronomeMark(number=result.tempo_bpm))
    score.insert(0, meter.TimeSignature(f"{result.time_signature[0]}/{result.time_signature[1]}"))
    if result.key_signature:
        maybe_key = _key_signature(result.key_signature)
        if maybe_key is not None:
            score.insert(0, maybe_key)

    for spec in result.instruments:
        part = stream.Part(id=_safe_part_id(spec.name))
        part.partName = spec.name
        part.insert(0, _music21_instrument(spec.name, spec.midi_program))
        part.insert(0, _clef(spec.clef))
        part.insert(0, meter.TimeSignature(f"{result.time_signature[0]}/{result.time_signature[1]}"))
        for orch_note in result.notes_by_instrument.get(spec.name, []):
            part.insert(orch_note.start_beat, _note_from_orchestrated(orch_note))
        part.makeMeasures(inPlace=True)
        score.insert(0, part)

    return score


def export_musicxml(result: OrchestrationResult, output_path: str | Path, title: str = "Orchestrated score") -> Path:
    """Write a full score MusicXML file and return its path."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    score = build_score(result, title=title)
    written = score.write("musicxml", fp=str(output))
    return Path(written)


def export_midi(result: OrchestrationResult, output_path: str | Path, title: str = "Orchestrated score") -> Path:
    """Write an optional MIDI realization from the arranged score."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    score = build_score(result, title=title)
    mf = midi.translate.music21ObjectToMidiFile(score)
    mf.open(str(output), "wb")
    mf.write()
    mf.close()
    return output


def export_parts_musicxml(result: OrchestrationResult, output_dir: str | Path, title_prefix: str = "Part") -> list[Path]:
    """Write one MusicXML file per instrument part."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    score = build_score(result, title="Orchestrated parts")
    written: list[Path] = []
    for part in score.parts:
        part_score = stream.Score()
        part_score.metadata = metadata.Metadata()
        part_score.metadata.title = f"{title_prefix} - {part.partName}"
        part_score.insert(0, part)
        path = output / f"{_safe_part_id(part.partName or part.id)}.musicxml"
        written.append(Path(part_score.write("musicxml", fp=str(path))))
    return written


def _note_from_orchestrated(orch_note: OrchestratedNote) -> note.Note:
    n = note.Note(orch_note.pitch)
    n.volume.velocity = orch_note.velocity
    n.duration = duration.Duration(orch_note.duration_beats)
    n.editorial.role = orch_note.role.value
    return n


def _music21_instrument(name: str, midi_program: int) -> instrument.Instrument:
    inst = instrument.fromString(name)
    inst.instrumentName = name
    inst.partName = name
    inst.midiProgram = midi_program
    return inst


def _clef(name: str) -> clef.Clef:
    if name == "bass":
        return clef.BassClef()
    if name == "alto":
        return clef.AltoClef()
    if name == "tenor":
        return clef.TenorClef()
    return clef.TrebleClef()


def _key_signature(key_name: str) -> key.Key | None:
    try:
        return key.Key(key_name)
    except Exception:  # music21 raises several parse-specific exceptions here.
        return None


def _safe_part_id(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_") or "part"
