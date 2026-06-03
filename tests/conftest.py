from __future__ import annotations

from pathlib import Path

import pytest

from scoresheet.midi_parser import MidiMeta, ParsedMidi, ParsedNote
from scoresheet.orchestrator import OrchestrationConfig, orchestrate


@pytest.fixture
def parsed_midi(tmp_path: Path) -> ParsedMidi:
    notes = [
        ParsedNote(48, 0.0, 0.5, 0.5, 80, None, 0, "Piano", 0),
        ParsedNote(60, 0.0, 0.5, 0.5, 68, None, 0, "Piano", 0),
        ParsedNote(64, 0.0, 0.5, 0.5, 66, None, 0, "Piano", 0),
        ParsedNote(72, 0.0, 1.0, 1.0, 96, None, 0, "Piano", 0),
        ParsedNote(67, 0.5, 0.55, 0.05, 60, None, 0, "Piano", 0),
        ParsedNote(71, 0.5, 0.55, 0.05, 62, None, 0, "Piano", 0),
        ParsedNote(74, 0.5, 0.55, 0.05, 64, None, 0, "Piano", 0),
        ParsedNote(77, 0.5, 0.55, 0.05, 70, None, 0, "Piano", 0),
    ]
    return ParsedMidi(
        path=tmp_path / "fixture.mid",
        notes=notes,
        meta=MidiMeta(tempos=[(0.0, 120.0)], time_signatures=[(0.0, 4, 4)]),
        length_seconds=1.0,
    )


@pytest.fixture
def orchestration_result(parsed_midi: ParsedMidi):
    return orchestrate(parsed_midi, OrchestrationConfig(target_ensemble="small_orchestra"))
