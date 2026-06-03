from __future__ import annotations

import pytest

from scoresheet.midi_parser import ParsedMidi
from scoresheet.orchestrator import (
    INSTRUMENTS,
    MusicalRole,
    OrchestrationConfig,
    bar_length_from_time_signature,
    fit_pitch_to_range,
    orchestrate,
    snap_to_barline,
)


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


@pytest.mark.parametrize(
    "time_signature, expected",
    [((4, 4), 4.0), ((3, 4), 3.0), ((6, 8), 3.0), ((9, 8), 4.5), ((12, 8), 6.0)],
)
def test_bar_length_from_time_signature(time_signature, expected) -> None:
    assert bar_length_from_time_signature(time_signature) == expected


def test_snap_to_barline_only_snaps_within_tolerance() -> None:
    assert snap_to_barline(4.499999, 4.5, 1e-4) == 4.5
    assert snap_to_barline(4.51, 4.5, 1e-4) == 4.51


def test_orchestrator_quantizes_start_and_end_stably(tmp_path) -> None:
    from scoresheet.midi_parser import MidiMeta, ParsedNote

    parsed = ParsedMidi(
        path=tmp_path / "fp.mid",
        notes=[
                ParsedNote(
                    pitch=60,
                    start=0.999999,
                    end=1.250001,
                    duration=0.500002,
                    velocity=80,
                    channel=None,
                track=0,
                instrument="Piano",
                program=0,
            )
        ],
        meta=MidiMeta(tempos=[(0.0, 120.0)], time_signatures=[(0.0, 4, 4)], key_signatures=[]),
        length_seconds=3.0,
    )

    result = orchestrate(parsed, OrchestrationConfig(target_ensemble="small_orchestra", quantization_unit=0.25))
    note = next(n for notes in result.notes_by_instrument.values() for n in notes)

    assert note.start_beat == pytest.approx(2.0)
    assert note.start_beat + note.duration_beats == pytest.approx(2.5)
    assert note.duration_beats > 0
