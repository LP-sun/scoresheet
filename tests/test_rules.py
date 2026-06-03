from music21 import pitch

from scoresheet.rules import (
    MusicalLine,
    assign_voices,
    correct_pitch_for_instrument,
    dynamic_from_velocity,
    get_instrument_range,
    split_harmony,
)


def _line(role, notes, velocity=80):
    return MusicalLine(role=role, pitches=tuple(pitch.Pitch(n) for n in notes), velocity=velocity)


def test_range_correction_octave_shifts_into_comfortable_register():
    correction = correct_pitch_for_instrument("C7", "Cello")

    assert correction.instrument == "Cello"
    assert correction.action == "octave_shift"
    assert correction.corrected.nameWithOctave == "C4"
    assert get_instrument_range("Cello").contains_comfortable(correction.corrected)


def test_range_correction_transfers_when_alternative_preserves_register():
    correction = correct_pitch_for_instrument("C1", "Flute", alternatives=("Tuba", "Cello"))

    assert correction.instrument == "Tuba"
    assert correction.transferred_from == "Flute"
    assert get_instrument_range("Tuba").contains_comfortable(correction.corrected)


def test_string_quartet_voice_assignment_prefers_standard_roles():
    assignments = assign_voices(
        [
            _line("melody", ["E5", "F5", "G5"], velocity=96),
            _line("harmony", ["C4", "D4", "E4"], velocity=70),
            _line("harmony", ["G3", "A3", "B3"], velocity=64),
            _line("bass", ["C2", "G2", "C3"], velocity=84),
        ],
        "string_quartet",
    )

    assert [assignment.instrument for assignment in assignments] == [
        "Violin I",
        "Violin II",
        "Viola",
        "Cello",
    ]
    assert assignments[0].dynamic.value == "f"
    assert assignments[-1].corrected_pitches[0].nameWithOctave == "C2"


def test_wind_quintet_voice_assignment_keeps_bassoon_bass_and_avoids_low_harmony_stack():
    assignments = assign_voices(
        [
            _line("melody", ["A5", "G5", "F5"]),
            _line("harmony", ["E4", "D4", "C4"]),
            _line("harmony", ["G2", "A2", "B2"]),
            _line("bass", ["Bb1", "F2", "Bb2"]),
        ],
        "wind_quintet",
    )

    assert [assignment.instrument for assignment in assignments] == ["Flute", "Oboe", "Clarinet", "Bassoon"]
    low_harmony = assignments[2]
    assert min(p.midi for p in low_harmony.corrected_pitches) >= pitch.Pitch("C3").midi
    assert assignments[-1].corrected_pitches[0].nameWithOctave == "B-1"


def test_orchestra_allows_string_and_woodwind_melody_doubling():
    assignment = assign_voices([_line("melody", ["C5", "E5"])], "orchestra")[0]

    assert assignment.instrument == "Violin I"
    assert assignment.doubled_by == ("Flute", "Oboe", "Violin II")


def test_split_harmony_supports_closed_and_open_spacing():
    closed = split_harmony(["C4", "E4", "G4", "B4"], ["Flute", "Oboe", "Clarinet", "Bassoon"])
    open_ = split_harmony(
        ["C4", "E4", "G4", "B4"],
        ["Flute", "Oboe", "Clarinet", "Bassoon"],
        spacing="open",
    )

    assert [c.instrument for c in closed] == ["Flute", "Oboe", "Clarinet", "Bassoon"]
    assert open_[2].corrected.midi < closed[2].corrected.midi


def test_dynamic_from_velocity_maps_to_music21_dynamic():
    assert dynamic_from_velocity(10).value == "ppp"
    assert dynamic_from_velocity(80).value == "mf"
    assert dynamic_from_velocity(127).value == "fff"
