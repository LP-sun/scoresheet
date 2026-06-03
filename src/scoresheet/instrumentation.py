"""Target ensemble definitions and General MIDI instrumentation.

MIDI programs below are zero-based General MIDI program numbers, matching the
convention used by :mod:`music21`'s ``Instrument.midiProgram`` field.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    """A named collection of target instruments."""

    name: str
    instruments: tuple[InstrumentSpec, ...]

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
