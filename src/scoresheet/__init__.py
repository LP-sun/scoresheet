"""scoresheet orchestration helpers."""

from .rules import (
    Assignment,
    InstrumentRange,
    MusicalLine,
    PitchCorrection,
    assign_voices,
    correct_pitch_for_instrument,
    dynamic_from_velocity,
    get_ensemble_instruments,
    get_instrument_range,
    split_harmony,
)

__all__ = [
    "Assignment",
    "InstrumentRange",
    "MusicalLine",
    "PitchCorrection",
    "assign_voices",
    "correct_pitch_for_instrument",
    "dynamic_from_velocity",
    "get_ensemble_instruments",
    "get_instrument_range",
    "split_harmony",
"""scoresheet package."""

__all__ = ["__version__"]

"""Utilities for arranging MIDI score sheets."""

__all__ = ["__version__"]
__version__ = "0.1.0"
"""scoresheet: arrange piano MIDI files into ensemble scores."""

from .arranger import arrange_file, analyze_midi, arrange_analysis
from .instrumentation import ENSEMBLES, Ensemble, InstrumentSpec, get_ensemble

__all__ = [
    "ENSEMBLES",
    "Ensemble",
    "InstrumentSpec",
    "analyze_midi",
    "arrange_analysis",
    "arrange_file",
    "get_ensemble",
]
