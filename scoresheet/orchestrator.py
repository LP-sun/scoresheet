"""Rule-based musical role analysis and orchestration.

This MVP is deliberately heuristic.  MIDI does not contain reliable notation
voices, slurs, beaming, phrase marks, or page layout, so the pipeline labels
notes by register, onset density, and duration rather than pretending to recover
an authoritative score.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
import math
import warnings

from .midi_parser import ParsedMidi, ParsedNote


class MusicalRole(StrEnum):
    MELODY = "melody"
    BASS = "bass"
    HARMONY = "harmony"
    RHYTHM = "rhythm"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InstrumentSpec:
    """Target instrument configuration.

    Ranges are MIDI pitch numbers.  `written_range` is currently informational;
    `sounding_range` is enforced for orchestration.
    """

    name: str
    midi_program: int
    clef: str
    written_range: tuple[int, int]
    sounding_range: tuple[int, int]
    transposition: int = 0


@dataclass(frozen=True)
class OrchestrationConfig:
    target_ensemble: str = "small_orchestra"
    quantization_unit: float = 0.25
    max_voices: int = 8
    concert_key: str | None = None
    output_musicxml: bool = True
    output_midi: bool = False
    output_parts: bool = False
    melody_instruments: tuple[str, ...] = ("Flute", "Oboe", "Violin I", "Trumpet")
    bass_instruments: tuple[str, ...] = ("Cello", "Bassoon", "Double Bass", "Trombone", "Tuba")
    harmony_instruments: tuple[str, ...] = ("Violin II", "Viola", "Clarinet", "Horn")
    rhythm_instruments: tuple[str, ...] = ("Viola", "Clarinet")


@dataclass(frozen=True)
class OrchestratedNote:
    """A note assigned by the heuristic arranger.

    `pitch` is always sounding/concert pitch. Exporters decide whether to keep
    that pitch or convert it to written pitch for MusicXML.
    """

    source: ParsedNote
    pitch: int
    start_beat: float
    duration_beats: float
    velocity: int
    role: MusicalRole
    instrument: InstrumentSpec


@dataclass(frozen=True)
class OrchestrationResult:
    config: OrchestrationConfig
    instruments: tuple[InstrumentSpec, ...]
    notes_by_instrument: dict[str, list[OrchestratedNote]]
    tempo_bpm: float
    time_signature: tuple[int, int]
    key_signature: str | None
    concert_key: str | None
    warnings: tuple[str, ...] = field(default_factory=tuple)


INSTRUMENTS: dict[str, InstrumentSpec] = {
    "Flute": InstrumentSpec("Flute", 73, "treble", (60, 96), (60, 96)),
    "Oboe": InstrumentSpec("Oboe", 68, "treble", (58, 91), (58, 91)),
    "Clarinet": InstrumentSpec("Clarinet", 71, "treble", (50, 94), (50, 94), transposition=2),
    "Bassoon": InstrumentSpec("Bassoon", 70, "bass", (34, 75), (34, 75)),
    "Horn": InstrumentSpec("Horn", 60, "treble", (41, 77), (41, 77), transposition=7),
    "Trumpet": InstrumentSpec("Trumpet", 56, "treble", (55, 82), (55, 82), transposition=2),
    "Trombone": InstrumentSpec("Trombone", 57, "bass", (40, 72), (40, 72)),
    "Tuba": InstrumentSpec("Tuba", 58, "bass", (28, 58), (28, 58)),
    "Violin I": InstrumentSpec("Violin I", 40, "treble", (55, 103), (55, 103)),
    "Violin II": InstrumentSpec("Violin II", 40, "treble", (55, 100), (55, 100)),
    "Viola": InstrumentSpec("Viola", 41, "alto", (48, 88), (48, 88)),
    "Cello": InstrumentSpec("Cello", 42, "bass", (36, 76), (36, 76)),
    "Double Bass": InstrumentSpec("Double Bass", 43, "bass", (28, 67), (28, 67)),
}

ENSEMBLES: dict[str, tuple[str, ...]] = {
    "string_quartet": ("Violin I", "Violin II", "Viola", "Cello"),
    "string_ensemble": ("Violin I", "Violin II", "Viola", "Cello", "Double Bass"),
    "wind_quintet": ("Flute", "Oboe", "Clarinet", "Bassoon", "Horn"),
    "wind_band": ("Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet", "Trombone", "Tuba"),
    "small_orchestra": (
        "Flute",
        "Oboe",
        "Clarinet",
        "Bassoon",
        "Horn",
        "Trumpet",
        "Violin I",
        "Violin II",
        "Viola",
        "Cello",
        "Double Bass",
    ),
    "orchestra": (
        "Flute",
        "Oboe",
        "Clarinet",
        "Bassoon",
        "Horn",
        "Trumpet",
        "Trombone",
        "Tuba",
        "Violin I",
        "Violin II",
        "Viola",
        "Cello",
        "Double Bass",
    ),
}


def orchestrate(parsed: ParsedMidi, config: OrchestrationConfig | None = None) -> OrchestrationResult:
    """Convert parsed MIDI notes into an ensemble assignment."""

    config = config or OrchestrationConfig()
    instrument_names = ENSEMBLES.get(config.target_ensemble)
    if instrument_names is None:
        allowed = ", ".join(sorted(ENSEMBLES))
        raise ValueError(f"Unknown ensemble '{config.target_ensemble}'. Available ensembles: {allowed}")

    instruments = tuple(INSTRUMENTS[name] for name in instrument_names)
    tempo_bpm = parsed.meta.tempos[0][1] if parsed.meta.tempos else 120.0
    seconds_per_beat = 60.0 / tempo_bpm
    time_signature = _first_time_signature(parsed)
    bar_length = bar_length_from_time_signature(time_signature)
    key_signature = _resolve_concert_key(config.concert_key)
    if key_signature is None:
        if parsed.meta.key_signatures:
            key_signature = _resolve_concert_key(parsed.meta.key_signatures[0][1])
        if key_signature is None:
            key_signature = "C major"
            warnings.warn("No key signature found; defaulting to C major. Use --concert-key to override.", RuntimeWarning, stacklevel=2)

    non_drum_notes = [n for n in parsed.notes if not n.is_drum]
    if not non_drum_notes:
        warnings.warn("Input MIDI contains no pitched non-drum notes.", RuntimeWarning, stacklevel=2)

    role_by_note = analyze_roles(non_drum_notes, seconds_per_beat, config.quantization_unit)
    result: dict[str, list[OrchestratedNote]] = {instrument.name: [] for instrument in instruments}
    warning_messages: list[str] = []

    role_counters: dict[MusicalRole, int] = defaultdict(int)
    for note in non_drum_notes:
        role = role_by_note[id(note)]
        target = _choose_instrument(role, note, instruments, config, role_counters[role])
        role_counters[role] += 1
        adjusted_pitch, range_warning = fit_pitch_to_range(note.pitch, target)
        if range_warning:
            warning_messages.append(range_warning)
        raw_start_beat = note.start / seconds_per_beat
        raw_end_beat = note.end / seconds_per_beat
        start_beat = quantize(raw_start_beat, config.quantization_unit)
        end_beat = quantize(raw_end_beat, config.quantization_unit)
        tolerance = max(1e-6, config.quantization_unit / 8)
        start_beat = snap_to_barline(start_beat, bar_length, tolerance)
        end_beat = snap_to_barline(end_beat, bar_length, tolerance)
        if end_beat <= start_beat:
            end_beat = start_beat + config.quantization_unit
        duration_beats = end_beat - start_beat
        result[target.name].append(
            OrchestratedNote(
                source=note,
                pitch=adjusted_pitch,
                start_beat=start_beat,
                duration_beats=duration_beats,
                velocity=note.velocity,
                role=role,
                instrument=target,
            )
        )

    for notes in result.values():
        notes.sort(key=lambda n: (n.start_beat, n.pitch, n.duration_beats))

    for message in sorted(set(warning_messages)):
        warnings.warn(message, RuntimeWarning, stacklevel=2)

    return OrchestrationResult(
        config=config,
        instruments=instruments,
        notes_by_instrument=result,
        tempo_bpm=tempo_bpm,
        time_signature=time_signature,
        key_signature=key_signature,
        concert_key=key_signature,
        warnings=tuple(sorted(set(warning_messages))),
    )


def analyze_roles(notes: list[ParsedNote], seconds_per_beat: float, quantization_unit: float) -> dict[int, MusicalRole]:
    """Assign each note a coarse musical role.

    The heuristic groups notes by quantized onset.  The lowest pitch at an onset
    tends to be bass, the highest longer note tends to be melody, dense repeated
    short events become rhythm, and remaining chord tones become harmony.
    """

    onsets: dict[float, list[ParsedNote]] = defaultdict(list)
    for note in notes:
        onset = quantize(note.start / seconds_per_beat, quantization_unit)
        onsets[onset].append(note)

    roles: dict[int, MusicalRole] = {}
    for onset_notes in onsets.values():
        ordered = sorted(onset_notes, key=lambda n: (n.pitch, n.duration, n.velocity))
        if len(ordered) == 1:
            note = ordered[0]
            roles[id(note)] = MusicalRole.BASS if note.pitch < 52 else MusicalRole.MELODY
            continue

        bass = ordered[0]
        melody = max(ordered, key=lambda n: (n.pitch, n.duration, n.velocity))
        roles[id(bass)] = MusicalRole.BASS
        roles[id(melody)] = MusicalRole.MELODY
        for note in ordered[1:]:
            if id(note) in roles:
                continue
            beat_duration = note.duration / seconds_per_beat
            roles[id(note)] = MusicalRole.RHYTHM if beat_duration <= quantization_unit * 1.5 and len(ordered) >= 4 else MusicalRole.HARMONY

    return roles


def quantize(value: float, unit: float) -> float:
    if unit <= 0:
        raise ValueError("quantization_unit must be positive")
    return round(value / unit) * unit


def snap_to_barline(value: float, bar_length: float, tolerance: float) -> float:
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    if bar_length <= 0:
        raise ValueError("bar_length must be positive")
    nearest = round(value / bar_length) * bar_length
    if abs(value - nearest) <= tolerance:
        return nearest
    return value


def fit_pitch_to_range(pitch: int, instrument: InstrumentSpec) -> tuple[int, str | None]:
    """Move a pitch by octaves until it fits the target sounding range.

    If octave movement cannot fit exactly, clamp to the nearest range boundary and
    return a warning.  This keeps output playable while making the compromise
    explicit to callers and users.
    """

    low, high = instrument.sounding_range
    adjusted = int(pitch)
    while adjusted < low:
        adjusted += 12
    while adjusted > high:
        adjusted -= 12
    if low <= adjusted <= high:
        if adjusted != pitch:
            return adjusted, f"Shifted pitch {pitch} to {adjusted} for {instrument.name} range {low}-{high}."
        return adjusted, None

    clamped = min(max(adjusted, low), high)
    return clamped, f"Clamped pitch {pitch} to {clamped} for {instrument.name}; octave shift could not fit range {low}-{high}."


def _choose_instrument(
    role: MusicalRole,
    note: ParsedNote,
    instruments: tuple[InstrumentSpec, ...],
    config: OrchestrationConfig,
    counter: int,
) -> InstrumentSpec:
    preferred_names = {
        MusicalRole.MELODY: config.melody_instruments,
        MusicalRole.BASS: config.bass_instruments,
        MusicalRole.HARMONY: config.harmony_instruments,
        MusicalRole.RHYTHM: config.rhythm_instruments,
        MusicalRole.UNKNOWN: tuple(i.name for i in instruments),
    }[role]
    candidates = [i for i in instruments if i.name in preferred_names]
    if not candidates:
        candidates = list(instruments)

    in_range = [i for i in candidates if i.sounding_range[0] <= note.pitch <= i.sounding_range[1]]
    pool = in_range or candidates
    return pool[counter % len(pool)]


def _first_time_signature(parsed: ParsedMidi) -> tuple[int, int]:
    if parsed.meta.time_signatures:
        _, numerator, denominator = parsed.meta.time_signatures[0]
        return numerator, denominator
    return (4, 4)


def bar_length_from_time_signature(time_signature: tuple[int, int]) -> float:
    numerator, denominator = time_signature
    return numerator * 4.0 / denominator


def _resolve_concert_key(raw_key: str | None) -> str | None:
    if raw_key is None:
        return None
    normalized = raw_key.strip()
    return normalized or None
