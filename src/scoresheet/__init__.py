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
"""scoresheet: rule-based MIDI piano-to-ensemble arrangement tools."""

from .arranger import ArrangedNote, ArrangedScore, NoteEvent, PianoAnalysis, analyze_midi, arrange_analysis, arrange_file, classify_piano_layers
from .exporters import export_arrangement, infer_export_format, to_music21_score
from .instrumentation import ALIASES, ENSEMBLES, Ensemble, InstrumentSpec, get_ensemble

__all__ = [
    "ALIASES",
    "ENSEMBLES",
    "ArrangedNote",
    "ArrangedScore",
    "Ensemble",
    "InstrumentSpec",
    "NoteEvent",
    "PianoAnalysis",
    "analyze_midi",
    "arrange_analysis",
    "arrange_file",
    "classify_piano_layers",
    "export_arrangement",
    "get_ensemble",
    "infer_export_format",
    "to_music21_score",
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
