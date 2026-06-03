from __future__ import annotations

from pathlib import Path

import pretty_midi

from scoresheet.cli import main
from scoresheet.midi_parser import parse_midi
from scoresheet.musicxml_exporter import export_musicxml
from scoresheet.orchestrator import INSTRUMENTS, MusicalRole, OrchestrationConfig, fit_pitch_to_range, orchestrate


def _write_simple_piano_midi(path: Path) -> None:
    midi = pretty_midi.PrettyMIDI(initial_tempo=100)
    piano = pretty_midi.Instrument(program=0, name="Piano")
    piano.notes.extend(
        [
            pretty_midi.Note(velocity=92, pitch=72, start=0.0, end=1.0),
            pretty_midi.Note(velocity=80, pitch=48, start=0.0, end=1.0),
            pretty_midi.Note(velocity=64, pitch=55, start=0.0, end=1.0),
            pretty_midi.Note(velocity=90, pitch=74, start=1.0, end=2.0),
            pretty_midi.Note(velocity=78, pitch=43, start=1.0, end=2.0),
        ]
    )
    midi.instruments.append(piano)
    midi.write(str(path))


def test_can_read_simple_midi(tmp_path: Path) -> None:
    midi_path = tmp_path / "simple.mid"
    _write_simple_piano_midi(midi_path)

    parsed = parse_midi(midi_path)

    assert len(parsed.notes) == 5
    assert parsed.meta.tempos
    assert parsed.length_seconds > 0


def test_generates_non_empty_musicxml(tmp_path: Path) -> None:
    midi_path = tmp_path / "simple.mid"
    _write_simple_piano_midi(midi_path)
    result = orchestrate(parse_midi(midi_path), OrchestrationConfig(target_ensemble="string_quartet"))

    output = export_musicxml(result, tmp_path / "score.musicxml")

    assert output.exists()
    assert output.stat().st_size > 100
    assert "Violin" in output.read_text(encoding="utf-8")


def test_melody_and_bass_go_to_different_instruments(tmp_path: Path) -> None:
    midi_path = tmp_path / "simple.mid"
    _write_simple_piano_midi(midi_path)

    result = orchestrate(parse_midi(midi_path), OrchestrationConfig(target_ensemble="small_orchestra"))
    melody_instruments = {
        name for name, notes in result.notes_by_instrument.items() if any(n.role == MusicalRole.MELODY for n in notes)
    }
    bass_instruments = {
        name for name, notes in result.notes_by_instrument.items() if any(n.role == MusicalRole.BASS for n in notes)
    }

    assert melody_instruments
    assert bass_instruments
    assert melody_instruments.isdisjoint(bass_instruments)


def test_range_check_octave_shifts() -> None:
    adjusted, warning = fit_pitch_to_range(24, INSTRUMENTS["Flute"])

    assert INSTRUMENTS["Flute"].sounding_range[0] <= adjusted <= INSTRUMENTS["Flute"].sounding_range[1]
    assert adjusted == 60
    assert warning is not None


def test_cli_missing_file_returns_clear_error(capsys) -> None:
    exit_code = main(["does-not-exist.mid"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "does not exist" in captured.err
