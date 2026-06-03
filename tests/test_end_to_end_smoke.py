from __future__ import annotations

from pathlib import Path

import pretty_midi

from scoresheet import cli


EXPECTED_SMALL_ORCHESTRA_NAMES = ("Flute", "Violin", "Cello", "Double Bass")


def _write_tiny_piano_midi(path: Path) -> None:
    midi = pretty_midi.PrettyMIDI(initial_tempo=120)
    piano = pretty_midi.Instrument(program=0, name="Piano")
    piano.notes.extend(
        [
            pretty_midi.Note(velocity=80, pitch=36, start=0.0, end=1.0),  # C2
            pretty_midi.Note(velocity=70, pitch=60, start=0.0, end=1.0),  # C4
            pretty_midi.Note(velocity=72, pitch=64, start=0.0, end=1.0),  # E4
            pretty_midi.Note(velocity=96, pitch=79, start=0.0, end=1.5),  # G5
            pretty_midi.Note(velocity=88, pitch=76, start=1.0, end=2.0),
        ]
    )
    midi.instruments.append(piano)
    midi.write(str(path))


def test_cli_musicxml_smoke_uses_generated_midi(tmp_path: Path) -> None:
    input_mid = tmp_path / "tiny.mid"
    output_dir = tmp_path / "out"
    _write_tiny_piano_midi(input_mid)

    exit_code = cli.main(
        [
            str(input_mid),
            "-o",
            str(output_dir),
            "--ensemble",
            "small_orchestra",
            "--format",
            "musicxml",
        ]
    )

    output = output_dir / "tiny_small_orchestra.musicxml"
    text = output.read_text(encoding="utf-8")
    assert exit_code == 0
    assert output.exists()
    assert output.stat().st_size > 0
    assert any(name in text for name in EXPECTED_SMALL_ORCHESTRA_NAMES)


def test_cli_both_with_parts_smoke_uses_generated_midi(tmp_path: Path) -> None:
    input_mid = tmp_path / "tiny.mid"
    output_dir = tmp_path / "out"
    _write_tiny_piano_midi(input_mid)

    exit_code = cli.main(
        [
            str(input_mid),
            "-o",
            str(output_dir),
            "--ensemble",
            "small_orchestra",
            "--format",
            "both",
            "--parts",
        ]
    )

    musicxml_output = output_dir / "tiny_small_orchestra.musicxml"
    midi_output = output_dir / "tiny_small_orchestra.mid"
    parts_dir = output_dir / "parts"
    part_files = list(parts_dir.glob("*.musicxml"))

    assert exit_code == 0
    assert musicxml_output.exists()
    assert musicxml_output.stat().st_size > 0
    assert midi_output.exists()
    assert midi_output.stat().st_size > 0
    assert parts_dir.is_dir()
    assert part_files
    assert all(path.stat().st_size > 0 for path in part_files)
