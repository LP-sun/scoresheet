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
