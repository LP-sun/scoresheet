"""music21-based score construction and export helpers."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Literal

from music21 import clef, duration, instrument, key, metadata, midi, note, pitch, stream, tempo, meter

from .orchestrator import InstrumentSpec, OrchestratedNote, OrchestrationResult


PitchMode = Literal["written", "concert"]


def build_score(
    result: OrchestrationResult,
    title: str = "Orchestrated score",
    pitch_mode: PitchMode = "written",
    concert_key: str | None = None,
) -> stream.Score:
    """Build a music21 Score from an orchestration result."""

    score = stream.Score()
    score.atSoundingPitch = True
    score.metadata = metadata.Metadata()
    score.metadata.title = title
    score.insert(0, tempo.MetronomeMark(number=result.tempo_bpm))
    score.insert(0, meter.TimeSignature(f"{result.time_signature[0]}/{result.time_signature[1]}"))

    concert_key_obj = _resolve_concert_key(result, concert_key)
    if concert_key_obj is not None:
        score.insert(0, copy.deepcopy(concert_key_obj))

    bar_length = result.time_signature[0] * 4.0 / result.time_signature[1]
    max_end = max(
        (n.start_beat + n.duration_beats for notes in result.notes_by_instrument.values() for n in notes),
        default=0.0,
    )
    total_length = math.ceil(max_end / bar_length) * bar_length if max_end > 0 else bar_length

    for spec in result.instruments:
        part = stream.Part(id=_safe_part_id(spec.name))
        part.partName = spec.name
        part.atSoundingPitch = True
        part.insert(0, _to_music21_instrument(spec, pitch_mode))
        part.insert(0, _clef(spec.clef))
        part.insert(0, meter.TimeSignature(f"{result.time_signature[0]}/{result.time_signature[1]}"))
        if concert_key_obj is not None:
            part.insert(0, copy.deepcopy(concert_key_obj))
        for orch_note in result.notes_by_instrument.get(spec.name, []):
            part.insert(orch_note.start_beat, _note_from_orchestrated(orch_note))
        _prepare_part_notation(part, total_length)
        if pitch_mode == "written":
            part = part.toWrittenPitch(inPlace=False)
        score.insert(0, part)

    return score


def export_musicxml(
    result: OrchestrationResult,
    output_path: str | Path,
    title: str = "Orchestrated score",
    pitch_mode: PitchMode = "written",
    concert_key: str | None = None,
) -> Path:
    """Write a full score MusicXML file and return its path."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    score = build_score(result, title=title, pitch_mode=pitch_mode, concert_key=concert_key)
    written = score.write("musicxml", fp=str(output))
    return Path(written)


def export_midi(result: OrchestrationResult, output_path: str | Path, title: str = "Orchestrated score") -> Path:
    """Write an optional MIDI realization from the arranged score.

    MIDI stays on sounding/concert pitch because it is only a listening aid.
    """

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    score = build_score(result, title=title, pitch_mode="concert")
    mf = midi.translate.music21ObjectToMidiFile(score)
    mf.open(str(output), "wb")
    mf.write()
    mf.close()
    return output


def export_parts_musicxml(
    result: OrchestrationResult,
    output_dir: str | Path,
    title_prefix: str = "Part",
    pitch_mode: PitchMode = "written",
    concert_key: str | None = None,
) -> list[Path]:
    """Write one MusicXML file per instrument part."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    score = build_score(result, title="Orchestrated parts", pitch_mode=pitch_mode, concert_key=concert_key)
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


def _prepare_part_notation(part: stream.Part, total_length: float) -> None:
    part.makeRests(fillGaps=True, refStreamOrTimeRange=[0, total_length], inPlace=True)
    part.makeMeasures(inPlace=True)
    part.makeTies(inPlace=True)
    for measure in part.getElementsByClass(stream.Measure):
        measure.makeRests(fillGaps=True, timeRangeFromBarDuration=True, inPlace=True)


def _to_music21_instrument(spec: InstrumentSpec, pitch_mode: PitchMode) -> instrument.Instrument:
    if pitch_mode == "concert":
        inst = instrument.Instrument()
        inst.instrumentName = spec.name
        inst.partName = spec.name
        inst.midiProgram = spec.midi_program
        inst.transposition = None
        return inst

    inst = instrument.fromString(spec.name)
    inst.instrumentName = spec.name
    inst.partName = spec.name
    inst.midiProgram = spec.midi_program
    return inst


def _resolve_concert_key(result: OrchestrationResult, concert_key: str | None) -> key.Key | None:
    raw = concert_key or result.concert_key or result.key_signature
    if raw is None:
        return None
    return _parse_key(raw)


def _parse_key(raw_key: str) -> key.Key:
    normalized = raw_key.strip()
    if not normalized:
        raise ValueError("concert key cannot be empty")

    parts = normalized.split()
    if len(parts) == 1:
        tonic, mode = _split_legacy_key_token(parts[0])
    else:
        tonic = parts[0]
        mode = parts[1].lower()
        if mode not in {"major", "minor"}:
            raise ValueError(f"Unsupported key mode in {raw_key!r}; expected major or minor")
    try:
        return key.Key(tonic, mode)
    except Exception as exc:  # music21 raises several parse-specific exceptions.
        raise ValueError(f"Could not parse concert key {raw_key!r}: {exc}") from exc


def _split_legacy_key_token(token: str) -> tuple[str, str]:
    lowered = token.lower()
    if lowered.endswith("m") and len(token) > 1:
        return token[:-1], "minor"
    return token, "major"


def _clef(name: str) -> clef.Clef:
    if name == "bass":
        return clef.BassClef()
    if name == "alto":
        return clef.AltoClef()
    if name == "tenor":
        return clef.TenorClef()
    return clef.TrebleClef()


def _safe_part_id(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_") or "part"
