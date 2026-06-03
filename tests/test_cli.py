from __future__ import annotations

from pathlib import Path

import pretty_midi

from scoresheet.cli import main


def write_simple_midi(path: Path) -> None:
    midi = pretty_midi.PrettyMIDI(initial_tempo=100)
    piano = pretty_midi.Instrument(program=0, name="Piano")
    piano.notes.extend(
        [
            pretty_midi.Note(velocity=96, pitch=72, start=0.0, end=1.0),
            pretty_midi.Note(velocity=80, pitch=48, start=0.0, end=1.0),
            pretty_midi.Note(velocity=64, pitch=55, start=0.0, end=1.0),
            pretty_midi.Note(velocity=90, pitch=74, start=1.0, end=2.0),
            pretty_midi.Note(velocity=78, pitch=43, start=1.0, end=2.0),
        ]
    )
    midi.instruments.append(piano)
    midi.write(str(path))


def test_arrange_cli_uses_real_pipeline(tmp_path: Path, capsys) -> None:
    midi_path = tmp_path / "simple.mid"
    output_path = tmp_path / "out.musicxml"
    write_simple_midi(midi_path)

    exit_code = main(["arrange", str(midi_path), "--ensemble", "string_quartet", "--output", str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert str(output_path) in captured.out
    assert output_path.exists()
    assert output_path.stat().st_size > 100
    assert "Violin" in output_path.read_text(encoding="utf-8")


def test_batch_arrange_cli_uses_real_pipeline(tmp_path: Path, capsys) -> None:
    midi_path = tmp_path / "simple.mid"
    out_dir = tmp_path / "arranged"
    write_simple_midi(midi_path)

    exit_code = main([
        "batch-arrange",
        str(tmp_path),
        "--ensemble",
        "wind_quintet",
        "--format",
        "musicxml",
        "--out-dir",
        str(out_dir),
    ])

    captured = capsys.readouterr()
    output_path = out_dir / "wind_quintet" / "simple_wind_quintet.musicxml"
    assert exit_code == 0
    assert "summary: success=1 failure=0" in captured.out
    assert output_path.exists()
    assert "Flute" in output_path.read_text(encoding="utf-8")


def test_batch_arrange_all_ensembles(tmp_path: Path) -> None:
    midi_path = tmp_path / "simple.mid"
    out_dir = tmp_path / "arranged"
    write_simple_midi(midi_path)

    exit_code = main(["batch-arrange", str(tmp_path), "--all-ensembles", "--format", "mid", "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "orchestra" / "simple_orchestra.mid").exists()
    assert (out_dir / "string_quartet" / "simple_string_quartet.mid").exists()


def test_cli_missing_file_returns_clear_error(capsys) -> None:
    exit_code = main(["arrange", "does-not-exist.mid", "--output", "out.musicxml"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "does not exist" in captured.err
