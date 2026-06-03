"""MIDI ingestion and lightweight metadata recovery.

The parser intentionally keeps MIDI information close to its performance form:
absolute seconds, velocity, program, channel, and track.  Later pipeline stages
quantize these values into a score-like grid.  This mirrors the separation used
by projects such as pretty-midi (performance data) and music21/partitura
(symbolic score data), without copying their implementations.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import warnings

import mido
import pretty_midi


@dataclass(frozen=True)
class ParsedNote:
    """A normalized note event extracted from a MIDI file."""

    pitch: int
    start: float
    end: float
    duration: float
    velocity: int
    channel: int | None
    track: int
    instrument: str
    program: int
    is_drum: bool = False


@dataclass(frozen=True)
class MidiMeta:
    """Metadata read from pretty_midi plus mido fallbacks."""

    tempos: list[tuple[float, float]] = field(default_factory=list)
    time_signatures: list[tuple[float, int, int]] = field(default_factory=list)
    key_signatures: list[tuple[float, str]] = field(default_factory=list)
    ticks_per_beat: int | None = None


@dataclass(frozen=True)
class ParsedMidi:
    """Parsed MIDI container used by the orchestration pipeline."""

    path: Path
    notes: list[ParsedNote]
    meta: MidiMeta
    length_seconds: float


def parse_midi(path: str | Path) -> ParsedMidi:
    """Read a MIDI file and return normalized notes plus musical metadata.

    pretty_midi is the primary reader because it exposes a convenient note and
    instrument API.  mido is used as a fallback for meta messages that are often
    important for producing readable MusicXML.
    """

    midi_path = Path(path)
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI file does not exist: {midi_path}")
    if not midi_path.is_file():
        raise ValueError(f"MIDI path is not a file: {midi_path}")

    try:
        pm = pretty_midi.PrettyMIDI(str(midi_path))
    except (OSError, ValueError, EOFError) as exc:
        warnings.warn(
            f"pretty_midi could not parse {midi_path.name}; falling back to clipped mido parser: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return _parse_midi_with_mido(midi_path)

    notes: list[ParsedNote] = []
    for track_index, instrument in enumerate(pm.instruments):
        channel = _channel_from_instrument(instrument)
        for note in instrument.notes:
            if note.end <= note.start:
                warnings.warn(
                    f"Skipping non-positive duration note in track {track_index}: "
                    f"pitch={note.pitch} start={note.start} end={note.end}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            notes.append(
                ParsedNote(
                    pitch=int(note.pitch),
                    start=float(note.start),
                    end=float(note.end),
                    duration=float(note.end - note.start),
                    velocity=int(note.velocity),
                    channel=channel,
                    track=track_index,
                    instrument=instrument.name or pretty_midi.program_to_instrument_name(instrument.program),
                    program=int(instrument.program),
                    is_drum=bool(instrument.is_drum),
                )
            )

    notes.sort(key=lambda n: (n.start, n.pitch, n.end))
    meta = _read_meta(pm, midi_path)
    return ParsedMidi(path=midi_path, notes=notes, meta=meta, length_seconds=float(pm.get_end_time()))


def _channel_from_instrument(instrument: pretty_midi.Instrument) -> int | None:
    """Best-effort channel recovery.

    pretty_midi does not expose channel as a public stable field on Instrument.
    Keep this optional rather than relying on private internals.
    """

    return None


def _read_meta(pm: pretty_midi.PrettyMIDI, path: Path) -> MidiMeta:
    tempos = _tempos_from_pretty_midi(pm)
    time_signatures = [
        (float(ts.time), int(ts.numerator), int(ts.denominator)) for ts in pm.time_signature_changes
    ]
    key_signatures = [(float(ks.time), _pretty_midi_key_name(ks)) for ks in pm.key_signature_changes]
    ticks_per_beat: int | None = getattr(pm, "resolution", None)

    fallback_tempos, fallback_time_sigs, fallback_key_sigs, fallback_tpb = _read_mido_meta(path)
    if not tempos:
        tempos = fallback_tempos
    if not time_signatures:
        time_signatures = fallback_time_sigs
    if not key_signatures:
        key_signatures = fallback_key_sigs
    if ticks_per_beat is None:
        ticks_per_beat = fallback_tpb

    if not tempos:
        warnings.warn("No tempo found in MIDI; defaulting to 120 BPM.", RuntimeWarning, stacklevel=2)
        tempos = [(0.0, 120.0)]
    if not time_signatures:
        warnings.warn("No time signature found in MIDI; defaulting to 4/4.", RuntimeWarning, stacklevel=2)
        time_signatures = [(0.0, 4, 4)]

    return MidiMeta(
        tempos=tempos,
        time_signatures=time_signatures,
        key_signatures=key_signatures,
        ticks_per_beat=ticks_per_beat,
    )


def _tempos_from_pretty_midi(pm: pretty_midi.PrettyMIDI) -> list[tuple[float, float]]:
    tempo_times, tempi = pm.get_tempo_changes()
    return [(float(t), float(bpm)) for t, bpm in zip(tempo_times, tempi, strict=False)]


def _pretty_midi_key_name(key_signature: pretty_midi.KeySignature) -> str:
    key_name = getattr(key_signature, "key_name", None)
    if key_name is not None:
        return str(key_name)
    return str(pretty_midi.key_number_to_key_name(int(key_signature.key_number)))


def _read_mido_meta(path: Path) -> tuple[list[tuple[float, float]], list[tuple[float, int, int]], list[tuple[float, str]], int | None]:
    """Read meta messages with mido using absolute seconds."""

    midi = mido.MidiFile(path)
    ticks_per_beat = int(midi.ticks_per_beat)
    tempos: list[tuple[float, float]] = []
    time_signatures: list[tuple[float, int, int]] = []
    key_signatures: list[tuple[float, str]] = []

    for track in midi.tracks:
        absolute_ticks = 0
        current_tempo = 500000
        absolute_seconds = 0.0
        for message in track:
            delta_ticks = int(message.time)
            absolute_seconds += mido.tick2second(delta_ticks, ticks_per_beat, current_tempo)
            absolute_ticks += delta_ticks
            if message.type == "set_tempo":
                current_tempo = int(message.tempo)
                tempos.append((absolute_seconds, float(mido.tempo2bpm(message.tempo))))
            elif message.type == "time_signature":
                time_signatures.append((absolute_seconds, int(message.numerator), int(message.denominator)))
            elif message.type == "key_signature":
                key_signatures.append((absolute_seconds, str(message.key)))

    return (
        _dedupe_meta(tempos),
        _dedupe_meta(time_signatures),
        _dedupe_meta(key_signatures),
        ticks_per_beat,
    )


def _dedupe_meta(items):
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped



def _parse_midi_with_mido(path: Path) -> ParsedMidi:
    """Fallback note extraction for malformed MIDI files.

    Some files contain out-of-range data bytes.  mido can read these with
    `clip=True`; pretty_midi intentionally cannot.  This fallback keeps the MVP
    usable while warning the user that the source file needed repair-like
    handling.
    """

    midi = mido.MidiFile(path, clip=True)
    ticks_per_beat = int(midi.ticks_per_beat)
    notes: list[ParsedNote] = []
    current_program: dict[int, int] = defaultdict(int)
    active: dict[tuple[int, int], list[tuple[float, int, int]]] = defaultdict(list)
    max_seconds = 0.0

    for track_index, track in enumerate(midi.tracks):
        absolute_seconds = 0.0
        current_tempo = 500000
        for message in track:
            absolute_seconds += mido.tick2second(int(message.time), ticks_per_beat, current_tempo)
            max_seconds = max(max_seconds, absolute_seconds)
            if message.type == "set_tempo":
                current_tempo = int(message.tempo)
            elif message.type == "program_change":
                current_program[int(message.channel)] = int(message.program)
            elif message.type == "note_on" and int(message.velocity) > 0:
                channel = int(message.channel)
                pitch = int(message.note)
                active[(channel, pitch)].append((absolute_seconds, int(message.velocity), current_program[channel]))
            elif message.type in {"note_off", "note_on"}:
                channel = int(message.channel)
                pitch = int(message.note)
                pending = active.get((channel, pitch))
                if not pending:
                    continue
                start, velocity, program = pending.pop(0)
                if absolute_seconds <= start:
                    continue
                is_drum = channel == 9
                notes.append(
                    ParsedNote(
                        pitch=pitch,
                        start=start,
                        end=absolute_seconds,
                        duration=absolute_seconds - start,
                        velocity=velocity,
                        channel=channel,
                        track=track_index,
                        instrument="Drums" if is_drum else pretty_midi.program_to_instrument_name(program),
                        program=program,
                        is_drum=is_drum,
                    )
                )

    notes.sort(key=lambda n: (n.start, n.pitch, n.end))
    fallback_tempos, fallback_time_sigs, fallback_key_sigs, fallback_tpb = _read_mido_meta_clipped(path)
    if not fallback_tempos:
        fallback_tempos = [(0.0, 120.0)]
    if not fallback_time_sigs:
        fallback_time_sigs = [(0.0, 4, 4)]
    meta = MidiMeta(
        tempos=fallback_tempos,
        time_signatures=fallback_time_sigs,
        key_signatures=fallback_key_sigs,
        ticks_per_beat=fallback_tpb,
    )
    return ParsedMidi(path=path, notes=notes, meta=meta, length_seconds=max_seconds)


def _read_mido_meta_clipped(path: Path) -> tuple[list[tuple[float, float]], list[tuple[float, int, int]], list[tuple[float, str]], int | None]:
    midi = mido.MidiFile(path, clip=True)
    ticks_per_beat = int(midi.ticks_per_beat)
    tempos: list[tuple[float, float]] = []
    time_signatures: list[tuple[float, int, int]] = []
    key_signatures: list[tuple[float, str]] = []
    for track in midi.tracks:
        current_tempo = 500000
        absolute_seconds = 0.0
        for message in track:
            absolute_seconds += mido.tick2second(int(message.time), ticks_per_beat, current_tempo)
            if message.type == "set_tempo":
                current_tempo = int(message.tempo)
                tempos.append((absolute_seconds, float(mido.tempo2bpm(message.tempo))))
            elif message.type == "time_signature":
                time_signatures.append((absolute_seconds, int(message.numerator), int(message.denominator)))
            elif message.type == "key_signature":
                key_signatures.append((absolute_seconds, str(message.key)))
    return _dedupe_meta(tempos), _dedupe_meta(time_signatures), _dedupe_meta(key_signatures), ticks_per_beat
