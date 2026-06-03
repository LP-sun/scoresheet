"""scoresheet: rule-based MIDI piano-to-ensemble orchestration tools."""

from .midi_parser import ParsedMidi, ParsedNote, parse_midi
from .orchestrator import (
    InstrumentSpec,
    MusicalRole,
    OrchestrationConfig,
    OrchestrationResult,
    orchestrate,
)
from .musicxml_exporter import export_musicxml, export_parts_musicxml

__all__ = [
    "InstrumentSpec",
    "MusicalRole",
    "OrchestrationConfig",
    "OrchestrationResult",
    "ParsedMidi",
    "ParsedNote",
    "export_musicxml",
    "export_parts_musicxml",
    "orchestrate",
    "parse_midi",
]
