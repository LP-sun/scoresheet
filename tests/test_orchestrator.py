from __future__ import annotations

import pytest

from scoresheet.midi_parser import ParsedMidi
from scoresheet.orchestrator import INSTRUMENTS, MusicalRole, OrchestrationConfig, fit_pitch_to_range, orchestrate


def test_orchestrator_assigns_basic_roles(parsed_midi: ParsedMidi) -> None:
    result = orchestrate(parsed_midi, OrchestrationConfig(target_ensemble="small_orchestra"))
    roles_by_instrument = {
        instrument: {note.role for note in notes}
        for instrument, notes in result.notes_by_instrument.items()
        if notes
    }

    assert any(MusicalRole.MELODY in roles for roles in roles_by_instrument.values())
    assert any(MusicalRole.BASS in roles for roles in roles_by_instrument.values())
    assert any(MusicalRole.HARMONY in roles for roles in roles_by_instrument.values())
    assert any(MusicalRole.RHYTHM in roles for roles in roles_by_instrument.values())
    assert result.concert_key == "C major"


def test_orchestrator_defaults_to_c_major_when_missing_key_signature(tmp_path) -> None:
    from scoresheet.midi_parser import MidiMeta, ParsedNote

    parsed = ParsedMidi(
        path=tmp_path / "no_key.mid",
        notes=[ParsedNote(60, 0.0, 1.0, 1.0, 80, None, 0, "Piano", 0)],
        meta=MidiMeta(tempos=[(0.0, 120.0)], time_signatures=[(0.0, 4, 4)], key_signatures=[]),
        length_seconds=1.0,
    )

    with pytest.warns(RuntimeWarning, match="No key signature found; defaulting to C major"):
        result = orchestrate(parsed, OrchestrationConfig(target_ensemble="small_orchestra"))

    assert result.concert_key == "C major"


def test_fit_pitch_to_range_octave_shifts_into_flute_range() -> None:
    adjusted, warning = fit_pitch_to_range(24, INSTRUMENTS["Flute"])

    assert adjusted == 60
    assert INSTRUMENTS["Flute"].sounding_range[0] <= adjusted <= INSTRUMENTS["Flute"].sounding_range[1]
    assert warning is not None


def test_unknown_ensemble_raises(parsed_midi: ParsedMidi) -> None:
    with pytest.raises(ValueError, match="Unknown ensemble"):
        orchestrate(parsed_midi, OrchestrationConfig(target_ensemble="not_real"))
