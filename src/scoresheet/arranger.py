"""Core rule-based MIDI-to-ensemble arranging pipeline.

The arranger intentionally stays small and deterministic.  MIDI cannot reliably
encode notation voices, phrasing, slurs, or page layout, so this module uses
simple, explicit heuristics and emits warnings when it has to guess.
"""
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
"""Piano MIDI analysis and rule-based ensemble arrangement."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import warnings

import mido
import pretty_midi

from .instrumentation import Ensemble, InstrumentSpec, get_ensemble


Role = str
from statistics import mean
from typing import Iterable, Literal

from .instrumentation import Ensemble, InstrumentSpec, get_ensemble

LayerName = Literal["melody", "bass", "harmony"]


@dataclass(frozen=True)
class NoteEvent:
    """A performance-time note extracted from MIDI."""

    pitch: int
    start: float
    end: float
    duration: float
    velocity: int
    track: int = 0
    channel: int | None = None
    program: int = 0
    instrument: str = "Piano"
    role: Role = "unknown"
    """A normalized note extracted from a MIDI/MusicXML score."""

    pitch: int
    start: float
    duration: float
    velocity: int = 64
    part_index: int = 0
    part_name: str = "Piano"
    layer: LayerName = "harmony"

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass(frozen=True)
class PianoAnalysis:
    """Parsed MIDI metadata plus coarse piano-layer classification."""

    source: Path
    notes: tuple[NoteEvent, ...]
    tempo_bpm: float = 120.0
    time_signature: tuple[int, int] = (4, 4)
    key_signature: str | None = None
    layers: dict[Role, tuple[NoteEvent, ...]] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArrangedNote:
    """A note assigned to a target instrument on a quantized beat grid."""

    pitch: int
    start_beat: float
    duration_beats: float
    velocity: int
    role: Role
    instrument: InstrumentSpec
    source: NoteEvent


@dataclass(frozen=True)
class ArrangedScore:
    """An arranged score ready for MusicXML/MIDI export."""

    source: Path
    ensemble: Ensemble
    notes_by_instrument: dict[str, tuple[ArrangedNote, ...]]
    tempo_bpm: float
    time_signature: tuple[int, int]
    key_signature: str | None = None
    warnings: tuple[str, ...] = ()


def analyze_midi(path: str | Path) -> PianoAnalysis:
    """Read a MIDI file and classify its piano-like layers."""

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Input MIDI file does not exist: {source}")
    if not source.is_file():
        raise ValueError(f"Input path is not a file: {source}")

    parse_warnings: list[str] = []
    try:
        notes, tempo_bpm, time_signature, key_signature = _read_with_pretty_midi(source)
    except (OSError, ValueError, EOFError) as exc:
        message = f"pretty_midi could not parse {source.name}; using clipped mido fallback: {exc}"
        warnings.warn(message, RuntimeWarning, stacklevel=2)
        parse_warnings.append(message)
        notes, tempo_bpm, time_signature, key_signature = _read_with_mido(source, clip=True)

    layers = classify_piano_layers(notes, tempo_bpm=tempo_bpm)
    return PianoAnalysis(
        source=source,
        notes=tuple(notes),
        tempo_bpm=tempo_bpm,
        time_signature=time_signature,
        key_signature=key_signature,
        layers=layers,
        warnings=tuple(parse_warnings),
    )


def classify_piano_layers(notes: list[NoteEvent] | tuple[NoteEvent, ...], tempo_bpm: float = 120.0) -> dict[Role, tuple[NoteEvent, ...]]:
    """Classify notes into melody, bass, harmony, rhythm, and unknown layers.

    Heuristic: group by quantized onset; the lowest pitch at each onset is bass,
    the highest/strongest pitch is melody, short dense notes are rhythm, and the
    remainder are harmony.  Single high notes are treated as melody; single low
    notes as bass.
    """

    grouped: dict[float, list[NoteEvent]] = defaultdict(list)
    seconds_per_beat = 60.0 / tempo_bpm if tempo_bpm > 0 else 0.5
    for note in notes:
        grouped[quantize(note.start / seconds_per_beat)].append(note)

    by_role: dict[Role, list[NoteEvent]] = {"melody": [], "bass": [], "harmony": [], "rhythm": [], "unknown": []}
    for onset_notes in grouped.values():
        ordered = sorted(onset_notes, key=lambda n: (n.pitch, n.velocity, n.duration))
        if len(ordered) == 1:
            note = ordered[0]
            role = "bass" if note.pitch < 52 else "melody"
            by_role[role].append(_with_role(note, role))
            continue

        bass = ordered[0]
        melody = max(ordered, key=lambda n: (n.pitch, n.velocity, n.duration))
        by_role["bass"].append(_with_role(bass, "bass"))
        by_role["melody"].append(_with_role(melody, "melody"))
        for note in ordered[1:]:
            if note is melody:
                continue
            role = "rhythm" if len(ordered) >= 4 and note.duration / seconds_per_beat <= 0.375 else "harmony"
            by_role[role].append(_with_role(note, role))

    return {role: tuple(sorted(items, key=lambda n: (n.start, n.pitch))) for role, items in by_role.items()}


def arrange_analysis(analysis: PianoAnalysis, ensemble: str | Ensemble = "small_orchestra", quantization_unit: float = 0.25) -> ArrangedScore:
    """Arrange analyzed piano layers for an ensemble."""

    if quantization_unit <= 0:
        raise ValueError("quantization_unit must be positive")
    target = get_ensemble(ensemble) if isinstance(ensemble, str) else ensemble
    seconds_per_beat = 60.0 / analysis.tempo_bpm if analysis.tempo_bpm > 0 else 0.5
    notes_by_instrument: dict[str, list[ArrangedNote]] = {instrument.name: [] for instrument in target.instruments}
    warnings_out = list(analysis.warnings)
    role_counts: dict[Role, int] = defaultdict(int)

    for role in ("melody", "bass", "harmony", "rhythm", "unknown"):
        for note_event in analysis.layers.get(role, ()):
            instrument = _select_instrument(role, note_event, target, role_counts[role])
            role_counts[role] += 1
            pitch, range_warning = fit_pitch_to_range(note_event.pitch, instrument)
            if range_warning:
                warnings.warn(range_warning, RuntimeWarning, stacklevel=2)
                warnings_out.append(range_warning)
            arranged = ArrangedNote(
                pitch=pitch,
                start_beat=quantize(note_event.start / seconds_per_beat, quantization_unit),
                duration_beats=max(quantization_unit, quantize(note_event.duration / seconds_per_beat, quantization_unit)),
                velocity=note_event.velocity,
                role=role,
                instrument=instrument,
                source=note_event,
            )
            notes_by_instrument[instrument.name].append(arranged)

    frozen_notes = {
        name: tuple(sorted(notes, key=lambda n: (n.start_beat, n.pitch, n.duration_beats)))
        for name, notes in notes_by_instrument.items()
    }
    return ArrangedScore(
        source=analysis.source,
        ensemble=target,
        notes_by_instrument=frozen_notes,
        tempo_bpm=analysis.tempo_bpm,
        time_signature=analysis.time_signature,
        key_signature=analysis.key_signature,
        warnings=tuple(sorted(set(warnings_out))),
    )


def arrange_file(path: str | Path, ensemble: str | Ensemble = "small_orchestra", quantization_unit: float = 0.25) -> ArrangedScore:
    """Analyze and arrange a MIDI file in one call."""

    return arrange_analysis(analyze_midi(path), ensemble=ensemble, quantization_unit=quantization_unit)


def quantize(value: float, unit: float = 0.25) -> float:
    """Round beat values to a readable grid."""

    return round(value / unit) * unit


def fit_pitch_to_range(pitch: int, instrument: InstrumentSpec) -> tuple[int, str | None]:
    """Octave-shift a MIDI pitch into an instrument range when possible."""

    low, high = instrument.sounding_range
    adjusted = int(pitch)
    while adjusted < low:
        adjusted += 12
    while adjusted > high:
        adjusted -= 12
    if low <= adjusted <= high:
        if adjusted == pitch:
            return adjusted, None
        return adjusted, f"Shifted pitch {pitch} to {adjusted} for {instrument.name} range {low}-{high}."
    clamped = min(max(adjusted, low), high)
    return clamped, f"Clamped pitch {pitch} to {clamped} for {instrument.name} range {low}-{high}."


def _select_instrument(role: Role, note: NoteEvent, ensemble: Ensemble, counter: int) -> InstrumentSpec:
    preferences = {
        "melody": ("Flute", "Oboe", "Violin I", "Trumpet", "Clarinet"),
        "bass": ("Cello", "Bassoon", "Double Bass", "Trombone", "Tuba"),
        "harmony": ("Violin II", "Viola", "Clarinet", "Horn", "Trombone"),
        "rhythm": ("Viola", "Clarinet", "Violin II", "Horn"),
        "unknown": tuple(instrument.name for instrument in ensemble.instruments),
    }
    preferred = preferences.get(role, preferences["unknown"])
    candidates = [instrument for instrument in ensemble.instruments if instrument.name in preferred] or list(ensemble.instruments)
    in_range = [instrument for instrument in candidates if instrument.sounding_range[0] <= note.pitch <= instrument.sounding_range[1]]
    pool = in_range or candidates
    return pool[counter % len(pool)]


def _with_role(note: NoteEvent, role: Role) -> NoteEvent:
    return NoteEvent(
        pitch=note.pitch,
        start=note.start,
        end=note.end,
        duration=note.duration,
        velocity=note.velocity,
        track=note.track,
        channel=note.channel,
        program=note.program,
        instrument=note.instrument,
        role=role,
    )


def _read_with_pretty_midi(path: Path) -> tuple[list[NoteEvent], float, tuple[int, int], str | None]:
    pm = pretty_midi.PrettyMIDI(str(path))
    notes: list[NoteEvent] = []
    for track_index, instrument in enumerate(pm.instruments):
        if instrument.is_drum:
            continue
        instrument_name = instrument.name or pretty_midi.program_to_instrument_name(instrument.program)
        for note in instrument.notes:
            if note.end <= note.start:
                warnings.warn(f"Skipping non-positive duration note pitch={note.pitch} in {path.name}.", RuntimeWarning, stacklevel=2)
                continue
            notes.append(
                NoteEvent(
                    pitch=int(note.pitch),
                    start=float(note.start),
                    end=float(note.end),
                    duration=float(note.end - note.start),
                    velocity=int(note.velocity),
                    track=track_index,
                    channel=None,
                    program=int(instrument.program),
                    instrument=instrument_name,
                )
            )
    notes.sort(key=lambda n: (n.start, n.pitch, n.end))
    tempo_times, tempi = pm.get_tempo_changes()
    tempo_bpm = float(tempi[0]) if len(tempi) else 120.0
    time_signature = (4, 4)
    if pm.time_signature_changes:
        ts = pm.time_signature_changes[0]
        time_signature = (int(ts.numerator), int(ts.denominator))
    key_signature = None
    if pm.key_signature_changes:
        key_signature = pretty_midi.key_number_to_key_name(int(pm.key_signature_changes[0].key_number))
    meta_tempo, meta_ts, meta_key = _read_mido_meta(path, clip=False)
    return notes, meta_tempo or tempo_bpm, meta_ts or time_signature, meta_key or key_signature


def _read_with_mido(path: Path, clip: bool) -> tuple[list[NoteEvent], float, tuple[int, int], str | None]:
    midi = mido.MidiFile(path, clip=clip)
    notes: list[NoteEvent] = []
    current_program: dict[int, int] = defaultdict(int)
    active: dict[tuple[int, int], list[tuple[float, int, int]]] = defaultdict(list)
    ticks_per_beat = int(midi.ticks_per_beat)
    tempo_bpm = 120.0
    time_signature = (4, 4)
    key_signature: str | None = None

    for track_index, track in enumerate(midi.tracks):
        absolute_seconds = 0.0
        current_tempo = 500000
        for message in track:
            absolute_seconds += mido.tick2second(int(message.time), ticks_per_beat, current_tempo)
            if message.type == "set_tempo":
                current_tempo = int(message.tempo)
                tempo_bpm = float(mido.tempo2bpm(message.tempo))
            elif message.type == "time_signature":
                time_signature = (int(message.numerator), int(message.denominator))
            elif message.type == "key_signature":
                key_signature = str(message.key)
            elif message.type == "program_change":
                current_program[int(message.channel)] = int(message.program)
            elif message.type == "note_on" and int(message.velocity) > 0:
                channel = int(message.channel)
                if channel == 9:
                    continue
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
                notes.append(
                    NoteEvent(
                        pitch=pitch,
                        start=start,
                        end=absolute_seconds,
                        duration=absolute_seconds - start,
                        velocity=velocity,
                        track=track_index,
                        channel=channel,
                        program=program,
                        instrument=pretty_midi.program_to_instrument_name(program),
                    )
                )
    notes.sort(key=lambda n: (n.start, n.pitch, n.end))
    return notes, tempo_bpm, time_signature, key_signature


def _read_mido_meta(path: Path, clip: bool) -> tuple[float | None, tuple[int, int] | None, str | None]:
    try:
        midi = mido.MidiFile(path, clip=clip)
    except (OSError, ValueError, EOFError):
        return None, None, None
    ticks_per_beat = int(midi.ticks_per_beat)
    tempo_bpm: float | None = None
    time_signature: tuple[int, int] | None = None
    key_signature: str | None = None
    for track in midi.tracks:
        current_tempo = 500000
        absolute_seconds = 0.0
        for message in track:
            absolute_seconds += mido.tick2second(int(message.time), ticks_per_beat, current_tempo)
            if message.type == "set_tempo" and tempo_bpm is None:
                current_tempo = int(message.tempo)
                tempo_bpm = float(mido.tempo2bpm(message.tempo))
            elif message.type == "time_signature" and time_signature is None:
                time_signature = (int(message.numerator), int(message.denominator))
            elif message.type == "key_signature" and key_signature is None:
                key_signature = str(message.key)
    return tempo_bpm, time_signature, key_signature
    """Result of source MIDI parsing and piano-role classification."""

    source_path: Path
    original_score: object
    notes: tuple[NoteEvent, ...]
    melody: tuple[NoteEvent, ...]
    bass: tuple[NoteEvent, ...]
    harmony: tuple[NoteEvent, ...]


@dataclass
class ArrangedScore:
    """Notes assigned to an ensemble."""

    analysis: PianoAnalysis
    ensemble: Ensemble
    assignments: dict[str, list[NoteEvent]] = field(default_factory=dict)

    @property
    def instrument_names(self) -> tuple[str, ...]:
        return tuple(i.name for i in self.ensemble.instruments)


def _require_music21():
    try:
        import music21  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "scoresheet requires music21 to read and write MIDI/MusicXML. "
            "Install it with: pip install music21"
        ) from exc
    return music21


def _volume_from_music21_note(n: object) -> int:
    volume = getattr(n, "volume", None)
    velocity = getattr(volume, "velocity", None)
    if velocity is None:
        return 64
    try:
        return max(1, min(127, int(velocity)))
    except (TypeError, ValueError):
        return 64


def _iter_music21_notes(score: object) -> Iterable[NoteEvent]:
    music21 = _require_music21()
    parts = getattr(score, "parts", [])
    source_parts = list(parts) if parts else [score]
    for part_index, part in enumerate(source_parts):
        part_name = getattr(part, "partName", None) or getattr(part, "id", None) or f"Part {part_index + 1}"
        for element in part.recurse().notes:
            start = float(element.getOffsetInHierarchy(score))
            duration = float(element.quarterLength or 0.25)
            if duration <= 0:
                duration = 0.25
            if isinstance(element, music21.chord.Chord):
                velocity = _volume_from_music21_note(element)
                for p in element.pitches:
                    yield NoteEvent(int(p.midi), start, duration, velocity, part_index, str(part_name))
            elif isinstance(element, music21.note.Note):
                yield NoteEvent(
                    int(element.pitch.midi),
                    start,
                    duration,
                    _volume_from_music21_note(element),
                    part_index,
                    str(part_name),
                )


def _onset_key(start: float, quantum: float = 1 / 24) -> int:
    return round(start / quantum)


def classify_piano_layers(notes: Iterable[NoteEvent]) -> tuple[NoteEvent, ...]:
    """Classify notes as melody, bass, or harmony using simple piano heuristics.

    The classifier groups notes by onset.  The highest salient note at an onset is
    treated as melody, the lowest low-register note is bass, and all remaining
    material becomes harmony/accompaniment.  Pitch, duration, velocity, and part
    position all influence the score so imported multi-track piano MIDIs still get
    useful separation.
    """

    note_list = sorted(notes, key=lambda n: (n.start, n.pitch, -n.duration))
    if not note_list:
        return ()

    avg_pitch = mean(n.pitch for n in note_list)
    groups: dict[int, list[NoteEvent]] = defaultdict(list)
    for n in note_list:
        groups[_onset_key(n.start)].append(n)

    classified: list[NoteEvent] = []
    for group in groups.values():
        ordered = sorted(group, key=lambda n: (n.pitch, n.velocity, n.duration))
        low = ordered[0]
        high = ordered[-1]

        bass_candidates = [n for n in ordered if n.pitch <= 52 or n.pitch <= avg_pitch - 14]
        bass = bass_candidates[0] if bass_candidates else None

        def melody_score(n: NoteEvent) -> float:
            track_bonus = 4 if n.part_index == 0 else 0
            return n.pitch * 1.4 + n.velocity * 0.25 + n.duration * 2 + track_bonus

        melody = max(ordered, key=melody_score)
        if high.pitch >= avg_pitch + 5 and melody.pitch < high.pitch:
            melody = high

        for n in ordered:
            layer: LayerName = "harmony"
            if bass is not None and n is bass and n is not melody:
                layer = "bass"
            elif n is melody or (n.pitch >= 72 and n is high):
                layer = "melody"
            classified.append(
                NoteEvent(n.pitch, n.start, n.duration, n.velocity, n.part_index, n.part_name, layer)
            )

    return tuple(sorted(classified, key=lambda n: (n.start, n.layer, n.pitch)))


def analyze_midi(path: str | Path) -> PianoAnalysis:
    """Read a MIDI file and extract melody, bass, and harmony layers."""

    music21 = _require_music21()
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    score = music21.converter.parse(str(source_path))
    notes = classify_piano_layers(_iter_music21_notes(score))
    return PianoAnalysis(
        source_path=source_path,
        original_score=score,
        notes=notes,
        melody=tuple(n for n in notes if n.layer == "melody"),
        bass=tuple(n for n in notes if n.layer == "bass"),
        harmony=tuple(n for n in notes if n.layer == "harmony"),
    )


def _nearest_instrument(note: NoteEvent, candidates: Iterable[InstrumentSpec]) -> InstrumentSpec:
    pool = tuple(candidates)
    if not pool:
        raise ValueError("No instruments available for assignment")

    def cost(spec: InstrumentSpec) -> float:
        if spec.contains(note.pitch):
            range_penalty = 0
        else:
            range_penalty = min(abs(note.pitch - spec.low_midi), abs(note.pitch - spec.high_midi)) * 8
        center_penalty = abs(note.pitch - spec.center)
        return range_penalty + center_penalty

    return min(pool, key=cost)


def _transpose_into_range(note: NoteEvent, spec: InstrumentSpec) -> NoteEvent:
    pitch = note.pitch
    while pitch < spec.low_midi:
        pitch += 12
    while pitch > spec.high_midi:
        pitch -= 12
    pitch = max(spec.low_midi, min(spec.high_midi, pitch))
    return NoteEvent(pitch, note.start, note.duration, note.velocity, note.part_index, note.part_name, note.layer)


def arrange_analysis(analysis: PianoAnalysis, ensemble: str | Ensemble) -> ArrangedScore:
    """Assign analyzed piano layers to a target ensemble."""

    target = get_ensemble(ensemble) if isinstance(ensemble, str) else ensemble
    assignments: dict[str, list[NoteEvent]] = {i.name: [] for i in target.instruments}

    melody_targets = target.melody_instruments or target.instruments[:1]
    bass_targets = target.bass_instruments or target.instruments[-1:]
    harmony_targets = target.harmony_instruments or tuple(
        i for i in target.instruments if i not in melody_targets and i not in bass_targets
    ) or target.instruments

    for note in analysis.notes:
        if note.layer == "melody":
            spec = _nearest_instrument(note, melody_targets)
        elif note.layer == "bass":
            spec = _nearest_instrument(note, bass_targets)
        else:
            spec = _nearest_instrument(note, harmony_targets)
        assignments[spec.name].append(_transpose_into_range(note, spec))

    for instrument_notes in assignments.values():
        instrument_notes.sort(key=lambda n: (n.start, n.pitch, n.duration))
    return ArrangedScore(analysis=analysis, ensemble=target, assignments=assignments)


def arrange_file(input_path: str | Path, ensemble: str | Ensemble) -> ArrangedScore:
    """Analyze ``input_path`` and arrange it for ``ensemble``."""

    return arrange_analysis(analyze_midi(input_path), ensemble)
