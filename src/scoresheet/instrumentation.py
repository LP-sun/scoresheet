"""Instrument and ensemble definitions for rule-based arranging."""

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


@dataclass(frozen=True)
class Ensemble:
    """A named group of instruments used by the arranger."""

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
