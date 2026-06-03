"""Instrumentation presets for score arrangement."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
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
