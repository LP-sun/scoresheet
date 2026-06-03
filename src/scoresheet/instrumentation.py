"""Instrument and ensemble definitions for rule-based arranging."""
"""Instrumentation presets for score arrangement."""
"""Target ensemble definitions and General MIDI instrumentation.

MIDI programs below are zero-based General MIDI program numbers, matching the
convention used by :mod:`music21`'s ``Instrument.midiProgram`` field.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentSpec:
    """Playable target instrument information.

    Ranges use sounding MIDI pitch numbers.  `transposition` is documented for
    future written-pitch support; the MVP exports concert-pitch scores.
    """

    name: str
    midi_program: int
    clef: str
    sounding_range: tuple[int, int]
    transposition: int = 0
class InstrumentPreset:
    """A simple instrument preset used by arrangers."""

    name: str
    music21_instrument: str


DEFAULT_ORCHESTRA_PRESET: tuple[InstrumentPreset, ...] = (
    InstrumentPreset("Flute", "Flute"),
    InstrumentPreset("Oboe", "Oboe"),
    InstrumentPreset("Clarinet", "Clarinet"),
    InstrumentPreset("Violin", "Violin"),
    InstrumentPreset("Viola", "Viola"),
    InstrumentPreset("Cello", "Cello"),
)
from typing import Mapping


@dataclass(frozen=True)
class InstrumentSpec:
    """Description of an arranging target instrument."""

    name: str
    gm_program: int
    role: str
    low_midi: int
    high_midi: int
    music21_class: str | None = None

    @property
    def center(self) -> float:
        return (self.low_midi + self.high_midi) / 2

    def contains(self, pitch_midi: int) -> bool:
        return self.low_midi <= pitch_midi <= self.high_midi


@dataclass(frozen=True)
class Ensemble:
    """A named group of instruments used by the arranger."""
    """A named collection of target instruments."""

    name: str
    instruments: tuple[InstrumentSpec, ...]


FLUTE = InstrumentSpec("Flute", 73, "treble", (60, 96))
OBOE = InstrumentSpec("Oboe", 68, "treble", (58, 91))
CLARINET = InstrumentSpec("Clarinet", 71, "treble", (50, 94), transposition=2)
BASSOON = InstrumentSpec("Bassoon", 70, "bass", (34, 75))
HORN = InstrumentSpec("Horn", 60, "treble", (41, 77), transposition=7)
TRUMPET = InstrumentSpec("Trumpet", 56, "treble", (55, 82), transposition=2)
TROMBONE = InstrumentSpec("Trombone", 57, "bass", (40, 72))
TUBA = InstrumentSpec("Tuba", 58, "bass", (28, 58))
VIOLIN_I = InstrumentSpec("Violin I", 40, "treble", (55, 103))
VIOLIN_II = InstrumentSpec("Violin II", 40, "treble", (55, 100))
VIOLA = InstrumentSpec("Viola", 41, "alto", (48, 88))
CELLO = InstrumentSpec("Cello", 42, "bass", (36, 76))
DOUBLE_BASS = InstrumentSpec("Double Bass", 43, "bass", (28, 67))

ENSEMBLES: dict[str, Ensemble] = {
    "string_quartet": Ensemble("string_quartet", (VIOLIN_I, VIOLIN_II, VIOLA, CELLO)),
    "string_ensemble": Ensemble("string_ensemble", (VIOLIN_I, VIOLIN_II, VIOLA, CELLO, DOUBLE_BASS)),
    "wind_quintet": Ensemble("wind_quintet", (FLUTE, OBOE, CLARINET, BASSOON, HORN)),
    "wind_band": Ensemble("wind_band", (FLUTE, OBOE, CLARINET, BASSOON, HORN, TRUMPET, TROMBONE, TUBA)),
    "small_orchestra": Ensemble(
        "small_orchestra",
        (FLUTE, OBOE, CLARINET, BASSOON, HORN, TRUMPET, VIOLIN_I, VIOLIN_II, VIOLA, CELLO, DOUBLE_BASS),
    ),
    "orchestra": Ensemble(
        "orchestra",
        (FLUTE, OBOE, CLARINET, BASSOON, HORN, TRUMPET, TROMBONE, TUBA, VIOLIN_I, VIOLIN_II, VIOLA, CELLO, DOUBLE_BASS),
    ),
}

ALIASES: dict[str, str] = {
    "quartet": "string_quartet",
    "strings": "string_ensemble",
    "string": "string_ensemble",
    "woodwind_quintet": "wind_quintet",
    "winds": "wind_band",
    "band": "wind_band",
    "chamber_orchestra": "small_orchestra",
    "small": "small_orchestra",
    "full_orchestra": "orchestra",
    "管弦乐团": "orchestra",
    "弦乐四重奏": "string_quartet",
    "木管五重奏": "wind_quintet",
    "管乐团": "wind_band",
    "弦乐团": "string_ensemble",
}


def canonical_ensemble_name(name: str) -> str:
    """Return a canonical ensemble key from a key or alias."""

    normalized = name.strip()
    return ALIASES.get(normalized, ALIASES.get(normalized.lower(), normalized.lower()))


def get_ensemble(name: str) -> Ensemble:
    """Look up an ensemble by canonical name or alias."""

    canonical = canonical_ensemble_name(name)
    try:
        return ENSEMBLES[canonical]
    except KeyError as exc:
        allowed = ", ".join(sorted((*ENSEMBLES.keys(), *ALIASES.keys())))
        raise ValueError(f"Unknown ensemble '{name}'. Available ensembles/aliases: {allowed}") from exc
    @property
    def melody_instruments(self) -> tuple[InstrumentSpec, ...]:
        return tuple(i for i in self.instruments if i.role in {"melody", "lead"})

    @property
    def bass_instruments(self) -> tuple[InstrumentSpec, ...]:
        return tuple(i for i in self.instruments if i.role == "bass")

    @property
    def harmony_instruments(self) -> tuple[InstrumentSpec, ...]:
        return tuple(i for i in self.instruments if i.role in {"harmony", "accompaniment"})


def _inst(
    name: str,
    gm_program: int,
    role: str,
    low_midi: int,
    high_midi: int,
    music21_class: str | None = None,
) -> InstrumentSpec:
    return InstrumentSpec(name, gm_program, role, low_midi, high_midi, music21_class)


ENSEMBLES: Mapping[str, Ensemble] = {
    "wind_band": Ensemble(
        "wind_band",
        (
            _inst("Flute", 73, "melody", 60, 96, "Flute"),
            _inst("Oboe", 68, "melody", 58, 88, "Oboe"),
            _inst("Clarinet", 71, "harmony", 50, 89, "Clarinet"),
            _inst("Alto Saxophone", 65, "harmony", 49, 80, "AltoSaxophone"),
            _inst("Trumpet", 56, "lead", 55, 82, "Trumpet"),
            _inst("Horn", 60, "harmony", 41, 77, "Horn"),
            _inst("Trombone", 57, "accompaniment", 40, 72, "Trombone"),
            _inst("Tuba", 58, "bass", 28, 58, "Tuba"),
        ),
    ),
    "string_orchestra": Ensemble(
        "string_orchestra",
        (
            _inst("Violin I", 40, "melody", 55, 103, "Violin"),
            _inst("Violin II", 40, "harmony", 55, 100, "Violin"),
            _inst("Viola", 41, "harmony", 48, 88, "Viola"),
            _inst("Cello", 42, "accompaniment", 36, 76, "Violoncello"),
            _inst("Contrabass", 43, "bass", 28, 64, "Contrabass"),
        ),
    ),
    "wind_quintet": Ensemble(
        "wind_quintet",
        (
            _inst("Flute", 73, "melody", 60, 96, "Flute"),
            _inst("Oboe", 68, "melody", 58, 88, "Oboe"),
            _inst("Clarinet", 71, "harmony", 50, 89, "Clarinet"),
            _inst("Bassoon", 70, "bass", 34, 74, "Bassoon"),
            _inst("Horn", 60, "harmony", 41, 77, "Horn"),
        ),
    ),
    "string_quartet": Ensemble(
        "string_quartet",
        (
            _inst("Violin I", 40, "melody", 55, 103, "Violin"),
            _inst("Violin II", 40, "harmony", 55, 100, "Violin"),
            _inst("Viola", 41, "harmony", 48, 88, "Viola"),
            _inst("Cello", 42, "bass", 36, 76, "Violoncello"),
        ),
    ),
    "orchestra": Ensemble(
        "orchestra",
        (
            _inst("Flute", 73, "melody", 60, 96, "Flute"),
            _inst("Oboe", 68, "melody", 58, 88, "Oboe"),
            _inst("Clarinet", 71, "harmony", 50, 89, "Clarinet"),
            _inst("Bassoon", 70, "bass", 34, 74, "Bassoon"),
            _inst("Horn", 60, "harmony", 41, 77, "Horn"),
            _inst("Trumpet", 56, "lead", 55, 82, "Trumpet"),
            _inst("Trombone", 57, "accompaniment", 40, 72, "Trombone"),
            _inst("Timpani", 47, "bass", 36, 60, "Timpani"),
            _inst("Violin I", 40, "melody", 55, 103, "Violin"),
            _inst("Violin II", 40, "harmony", 55, 100, "Violin"),
            _inst("Viola", 41, "harmony", 48, 88, "Viola"),
            _inst("Cello", 42, "accompaniment", 36, 76, "Violoncello"),
            _inst("Contrabass", 43, "bass", 28, 64, "Contrabass"),
        ),
    ),
}

# Friendly aliases accepted by the CLI/API.
ALIASES: Mapping[str, str] = {
    "band": "wind_band",
    "winds": "wind_band",
    "wind_orchestra": "wind_band",
    "strings": "string_orchestra",
    "string_ensemble": "string_orchestra",
    "quintet": "wind_quintet",
    "quartet": "string_quartet",
    "symphony": "orchestra",
    "orchestral": "orchestra",
}


def get_ensemble(name: str) -> Ensemble:
    """Return an ensemble by canonical name or alias."""

    key = name.strip().lower().replace("-", "_")
    key = ALIASES.get(key, key)
    if key not in ENSEMBLES:
        valid = ", ".join(sorted((*ENSEMBLES.keys(), *ALIASES.keys())))
        raise ValueError(f"Unknown ensemble '{name}'. Valid ensembles: {valid}")
    return ENSEMBLES[key]
