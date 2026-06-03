"""Rule layer for MIDI-to-ensemble orchestration based on music21.

The module intentionally keeps the rules deterministic and small: callers can
feed extracted melody/bass/harmony lines from a MIDI reduction and receive a
practical first-pass instrumentation plan.  All pitches are represented with
``music21.pitch.Pitch`` so the rules can be plugged into music21 streams,
notes, chords, and MusicXML/MIDI export code without an adapter layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Iterable, Mapping, Sequence

from music21 import chord, dynamics, note, pitch

PitchLike = pitch.Pitch | note.Note | int | str


@dataclass(frozen=True)
class InstrumentRange:
    """Comfortable and extreme ranges for one target instrument."""

    name: str
    comfortable_low: pitch.Pitch
    comfortable_high: pitch.Pitch
    extreme_low: pitch.Pitch
    extreme_high: pitch.Pitch
    families: tuple[str, ...] = ()

    def contains_extreme(self, p: pitch.Pitch) -> bool:
        return self.extreme_low.midi <= p.midi <= self.extreme_high.midi

    def contains_comfortable(self, p: pitch.Pitch) -> bool:
        return self.comfortable_low.midi <= p.midi <= self.comfortable_high.midi


@dataclass(frozen=True)
class MusicalLine:
    """A MIDI-derived musical line tagged with an orchestration role."""

    role: str
    pitches: tuple[pitch.Pitch, ...]
    velocity: int = 80
    name: str | None = None


@dataclass(frozen=True)
class PitchCorrection:
    """Result of correcting a pitch for an instrument range."""

    original: pitch.Pitch
    corrected: pitch.Pitch
    instrument: str
    action: str
    transferred_from: str | None = None


@dataclass(frozen=True)
class Assignment:
    """Instrument assignment for one musical line."""

    line: MusicalLine
    instrument: str
    corrected_pitches: tuple[pitch.Pitch, ...]
    dynamic: dynamics.Dynamic
    doubled_by: tuple[str, ...] = field(default_factory=tuple)
    corrections: tuple[PitchCorrection, ...] = field(default_factory=tuple)


# Practical written/concert-pitch ranges for orchestration planning.  They are
# intentionally conservative in the comfortable band and permissive at extremes.
def _range(
    name: str,
    comfortable_low: str,
    comfortable_high: str,
    extreme_low: str,
    extreme_high: str,
    *families: str,
) -> InstrumentRange:
    return InstrumentRange(
        name=name,
        comfortable_low=pitch.Pitch(comfortable_low),
        comfortable_high=pitch.Pitch(comfortable_high),
        extreme_low=pitch.Pitch(extreme_low),
        extreme_high=pitch.Pitch(extreme_high),
        families=tuple(families),
    )


INSTRUMENT_RANGES: Mapping[str, InstrumentRange] = {
    "Flute": _range("Flute", "C4", "A6", "C4", "D7", "woodwind", "soprano"),
    "Oboe": _range("Oboe", "Bb3", "G5", "Bb3", "A6", "woodwind", "soprano"),
    "Clarinet": _range("Clarinet", "E3", "C6", "E3", "G6", "woodwind", "alto"),
    "Bassoon": _range("Bassoon", "Bb1", "D4", "Bb1", "E5", "woodwind", "bass"),
    "Horn": _range("Horn", "F3", "G5", "C2", "C6", "brass", "alto"),
    "Trumpet": _range("Trumpet", "G3", "C6", "F#3", "D6", "brass", "soprano"),
    "Trombone": _range("Trombone", "E2", "Bb4", "E2", "F5", "brass", "tenor"),
    "Tuba": _range("Tuba", "D1", "F3", "D1", "F4", "brass", "bass"),
    "Violin I": _range("Violin I", "G3", "E6", "G3", "A7", "string", "soprano"),
    "Violin II": _range("Violin II", "G3", "D6", "G3", "A7", "string", "soprano"),
    "Viola": _range("Viola", "C3", "A5", "C3", "E6", "string", "alto"),
    "Cello": _range("Cello", "C2", "G4", "C2", "C6", "string", "bass"),
    "Double Bass": _range("Double Bass", "E1", "C4", "E1", "G4", "string", "bass"),
}

ENSEMBLES: Mapping[str, tuple[str, ...]] = {
    "string_quartet": ("Violin I", "Violin II", "Viola", "Cello"),
    "wind_quintet": ("Flute", "Oboe", "Clarinet", "Horn", "Bassoon"),
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

MELODY_TARGETS: Mapping[str, tuple[str, ...]] = {
    "string_quartet": ("Violin I",),
    "wind_quintet": ("Flute", "Oboe", "Clarinet"),
    "orchestra": ("Violin I", "Flute", "Oboe", "Trumpet"),
}

BASS_TARGETS: Mapping[str, tuple[str, ...]] = {
    "string_quartet": ("Cello",),
    "wind_quintet": ("Bassoon", "Horn", "Clarinet"),
    "orchestra": ("Cello", "Bassoon", "Tuba", "Double Bass", "Trombone"),
}

HARMONY_TARGETS: Mapping[str, tuple[str, ...]] = {
    "string_quartet": ("Violin II", "Viola"),
    "wind_quintet": ("Oboe", "Clarinet", "Horn"),
    "orchestra": ("Violin II", "Viola", "Clarinet", "Horn", "Trombone"),
}

ORCHESTRAL_MELODY_DOUBLINGS: tuple[str, ...] = ("Flute", "Oboe", "Violin II")


class UnknownInstrumentError(KeyError):
    """Raised when a rule references an instrument with no registered range."""


class UnknownEnsembleError(KeyError):
    """Raised when an ensemble preset is unknown."""


def as_pitch(value: PitchLike) -> pitch.Pitch:
    """Convert a supported value to a detached ``music21.pitch.Pitch``."""

    if isinstance(value, pitch.Pitch):
        return pitch.Pitch(value.nameWithOctave)
    if isinstance(value, note.Note):
        return pitch.Pitch(value.pitch.nameWithOctave)
    if isinstance(value, int):
        p = pitch.Pitch()
        p.midi = value
        return p
    return pitch.Pitch(value)


def get_instrument_range(instrument: str) -> InstrumentRange:
    """Return the configured range for an instrument."""

    try:
        return INSTRUMENT_RANGES[instrument]
    except KeyError as exc:
        raise UnknownInstrumentError(instrument) from exc


def get_ensemble_instruments(ensemble: str) -> tuple[str, ...]:
    """Return instrument names for a named ensemble preset."""

    try:
        return ENSEMBLES[ensemble]
    except KeyError as exc:
        raise UnknownEnsembleError(ensemble) from exc


def dynamic_from_velocity(velocity: int) -> dynamics.Dynamic:
    """Map MIDI velocity (0-127) to a music21 dynamic mark."""

    clamped = max(0, min(127, int(velocity)))
    if clamped <= 20:
        mark = "ppp"
    elif clamped <= 35:
        mark = "pp"
    elif clamped <= 50:
        mark = "p"
    elif clamped <= 65:
        mark = "mp"
    elif clamped <= 85:
        mark = "mf"
    elif clamped <= 105:
        mark = "f"
    elif clamped <= 120:
        mark = "ff"
    else:
        mark = "fff"
    return dynamics.Dynamic(mark)


def _octave_candidates(source: pitch.Pitch) -> list[pitch.Pitch]:
    candidates: list[pitch.Pitch] = []
    for octave_delta in range(-5, 6):
        p = pitch.Pitch(source.nameWithOctave)
        p.midi = source.midi + (12 * octave_delta)
        candidates.append(p)
    return candidates


def _best_octave_in_range(
    source: pitch.Pitch,
    instrument_range: InstrumentRange,
) -> tuple[pitch.Pitch, str] | None:
    candidates = [p for p in _octave_candidates(source) if instrument_range.contains_extreme(p)]
    if not candidates:
        return None

    comfortable = [p for p in candidates if instrument_range.contains_comfortable(p)]
    pool = comfortable or candidates
    center = (instrument_range.comfortable_low.midi + instrument_range.comfortable_high.midi) / 2
    best = min(pool, key=lambda p: (abs(p.midi - source.midi), abs(p.midi - center)))
    if best.midi == source.midi:
        return best, "unchanged"
    return best, "octave_shift"


def correct_pitch_for_instrument(
    value: PitchLike,
    instrument: str,
    alternatives: Sequence[str] = (),
) -> PitchCorrection:
    """Fit a pitch to an instrument by octave shift, or transfer it.

    The rule first tries octave transposition within the requested instrument's
    extreme range, preferring the comfortable range.  If no octave placement can
    fit, alternatives are searched in order and the first feasible instrument is
    selected.
    """

    source = as_pitch(value)
    primary_range = get_instrument_range(instrument)
    primary = _best_octave_in_range(source, primary_range)

    # Prefer a true low/high instrument over a drastic multi-octave rewrite when
    # the caller supplies transfer candidates.  This preserves register intent
    # for MIDI reductions while still allowing simple octave repair by default.
    for alternative in alternatives:
        alternative_range = get_instrument_range(alternative)
        transferred = _best_octave_in_range(source, alternative_range)
        if transferred is None:
            continue
        corrected, action = transferred
        primary_shift = None if primary is None else abs(primary[0].midi - source.midi)
        transfer_shift = abs(corrected.midi - source.midi)
        if primary_shift is None or (primary_shift > 24 and transfer_shift <= 24):
            return PitchCorrection(source, corrected, alternative, f"transfer_{action}", instrument)

    if primary is not None:
        corrected, action = primary
        return PitchCorrection(source, corrected, instrument, action)

    # Last resort: clamp to the nearest extreme pitch instead of producing an
    # unplayable assignment.  Callers can inspect ``action`` to flag it.
    low = primary_range.extreme_low
    high = primary_range.extreme_high
    corrected = pitch.Pitch(low.nameWithOctave if source.midi < low.midi else high.nameWithOctave)
    return PitchCorrection(source, corrected, instrument, "clamped")


def _line_average(line: MusicalLine) -> float:
    return mean(p.midi for p in line.pitches) if line.pitches else 60.0


def _normalize_line(line: MusicalLine | Mapping[str, object]) -> MusicalLine:
    if isinstance(line, MusicalLine):
        return line
    raw_pitches = line.get("pitches", ())
    return MusicalLine(
        role=str(line.get("role", "harmony")),
        pitches=tuple(as_pitch(p) for p in raw_pitches),
        velocity=int(line.get("velocity", 80)),
        name=str(line.get("name")) if line.get("name") is not None else None,
    )


def _infer_roles(lines: list[MusicalLine]) -> list[MusicalLine]:
    if any(line.role != "auto" for line in lines):
        return lines
    if not lines:
        return []
    ordered = sorted(enumerate(lines), key=lambda item: _line_average(item[1]))
    roles = ["harmony"] * len(lines)
    roles[ordered[-1][0]] = "melody"
    roles[ordered[0][0]] = "bass"
    return [MusicalLine(roles[i], line.pitches, line.velocity, line.name) for i, line in enumerate(lines)]


def _pick_instrument(line: MusicalLine, ensemble: str, used: set[str]) -> str:
    role = line.role.lower()
    if role == "melody":
        targets = MELODY_TARGETS[ensemble]
    elif role == "bass":
        targets = BASS_TARGETS[ensemble]
    else:
        targets = HARMONY_TARGETS[ensemble]

    for instrument in targets:
        if instrument not in used:
            return instrument
    return targets[-1]


def _wind_quintet_low_stack_guard(
    line: MusicalLine,
    instrument: str,
    corrections: list[PitchCorrection],
) -> tuple[str, list[PitchCorrection]]:
    """Avoid dense low-register harmony in woodwind quintet writing."""

    if line.role.lower() == "bass" or not corrections:
        return instrument, corrections
    too_low = [c for c in corrections if c.corrected.midi < pitch.Pitch("C3").midi]
    if not too_low:
        return instrument, corrections

    # Horn tolerates the low-middle register better than upper woodwinds.  If a
    # harmony line still sits below C3, move it to Horn when possible; otherwise
    # raise the offending pitches by octaves until they clear the stack.
    if instrument != "Horn" and "Horn" in HARMONY_TARGETS["wind_quintet"]:
        instrument = "Horn"
        corrections = [correct_pitch_for_instrument(c.original, instrument) for c in corrections]

    raised: list[PitchCorrection] = []
    for correction in corrections:
        corrected = correction.corrected
        action = correction.action
        while corrected.midi < pitch.Pitch("C3").midi:
            corrected = pitch.Pitch(corrected.nameWithOctave)
            corrected.midi += 12
            action = "low_stack_octave_shift"
        raised.append(
            PitchCorrection(
                correction.original,
                corrected,
                instrument,
                action,
                correction.transferred_from,
            )
        )
    return instrument, raised


def assign_voices(
    lines: Iterable[MusicalLine | Mapping[str, object]],
    ensemble: str,
    *,
    allow_doubling: bool | None = None,
) -> tuple[Assignment, ...]:
    """Assign melody, bass, and harmony lines to an ensemble.

    Rules implemented:
    * melody prefers the highest/main instrument of the ensemble;
    * bass prefers Cello, Bassoon, Tuba, or Double Bass style instruments;
    * harmony fills inner instruments;
    * each pitch is corrected by octave shift or transfer candidates;
    * orchestral melody may be doubled by strings and woodwinds;
    * wind quintet harmony avoids an over-dense low register.
    """

    get_ensemble_instruments(ensemble)
    normalized = _infer_roles([_normalize_line(line) for line in lines])
    used: set[str] = set()
    assignments: list[Assignment] = []
    doubling_enabled = ensemble == "orchestra" if allow_doubling is None else allow_doubling

    for line in normalized:
        instrument = _pick_instrument(line, ensemble, used)
        used.add(instrument)
        alternatives = tuple(i for i in get_ensemble_instruments(ensemble) if i != instrument)
        corrections = [correct_pitch_for_instrument(p, instrument, alternatives) for p in line.pitches]

        # A transfer caused by range repair changes ownership of the whole line.
        transferred = next((c.instrument for c in corrections if c.instrument != instrument), None)
        if transferred is not None:
            instrument = transferred
            corrections = [correct_pitch_for_instrument(p, instrument, alternatives) for p in line.pitches]

        if ensemble == "wind_quintet":
            instrument, corrections = _wind_quintet_low_stack_guard(line, instrument, corrections)

        doubled_by: tuple[str, ...] = ()
        if doubling_enabled and line.role.lower() == "melody":
            doubled_by = tuple(i for i in ORCHESTRAL_MELODY_DOUBLINGS if i != instrument)

        assignments.append(
            Assignment(
                line=line,
                instrument=instrument,
                corrected_pitches=tuple(c.corrected for c in corrections),
                dynamic=dynamic_from_velocity(line.velocity),
                doubled_by=doubled_by,
                corrections=tuple(corrections),
            )
        )

    return tuple(assignments)


def split_harmony(
    pitches: Iterable[PitchLike],
    instruments: Sequence[str],
    *,
    spacing: str = "closed",
) -> tuple[PitchCorrection, ...]:
    """Split a chord across instruments in closed or open position."""

    if spacing not in {"closed", "open"}:
        raise ValueError("spacing must be 'closed' or 'open'")

    chord_pitches = [as_pitch(p) for p in pitches]
    if not chord_pitches or not instruments:
        return ()

    # Let music21 normalize chord pitch spelling/order, then assign from top
    # instrument to lower instruments.  Open spacing drops every lower alternate
    # voice an octave before range correction, creating orchestral space.
    normalized = sorted(
        chord.Chord(chord_pitches).pitches,
        key=lambda p: p.midi,
        reverse=True,
    )
    selected = normalized[: len(instruments)]
    results: list[PitchCorrection] = []
    for index, (instrument, source) in enumerate(zip(instruments, selected, strict=False)):
        planned = pitch.Pitch(source.nameWithOctave)
        if spacing == "open" and index >= 2:
            planned.midi -= 12
        alternatives = tuple(i for i in instruments if i != instrument)
        results.append(correct_pitch_for_instrument(planned, instrument, alternatives))
    return tuple(results)
