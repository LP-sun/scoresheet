from __future__ import annotations

from pathlib import Path

import pretty_midi

from scoresheet.arranger import arrange_file, fit_pitch_to_range
from scoresheet.exporters import export_arrangement, infer_export_format
from scoresheet.instrumentation import FLUTE


def write_simple_midi(path: Path) -> None:
    midi = pretty_midi.PrettyMIDI(initial_tempo=120)
    piano = pretty_midi.Instrument(program=0, name="Piano")
    piano.notes.extend(
        [
            pretty_midi.Note(velocity=90, pitch=72, start=0.0, end=0.5),
            pretty_midi.Note(velocity=80, pitch=48, start=0.0, end=1.0),
            pretty_midi.Note(velocity=70, pitch=60, start=0.0, end=1.0),
        ]
    )
    midi.instruments.append(piano)
    midi.write(str(path))


def test_arrange_file_assigns_melody_and_bass(tmp_path: Path) -> None:
    midi_path = tmp_path / "simple.mid"
    write_simple_midi(midi_path)

    arranged = arrange_file(midi_path, ensemble="small_orchestra")
    roles_by_instrument = {
        name: {note.role for note in notes}
        for name, notes in arranged.notes_by_instrument.items()
        if notes
    }

    assert any("melody" in roles for roles in roles_by_instrument.values())
    assert any("bass" in roles for roles in roles_by_instrument.values())


def test_export_arrangement_infers_formats(tmp_path: Path) -> None:
    midi_path = tmp_path / "simple.mid"
    write_simple_midi(midi_path)
    arranged = arrange_file(midi_path, ensemble="string_quartet")

    assert infer_export_format("score.mid") == "midi"
    assert infer_export_format("score.musicxml") == "musicxml"
    assert export_arrangement(arranged, tmp_path / "score.musicxml").exists()


def test_fit_pitch_to_range_octave_shifts() -> None:
    adjusted, message = fit_pitch_to_range(24, FLUTE)

    assert adjusted == 60
    assert message is not None
