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
from pathlib import Path

import pytest

from scoresheet import cli


def test_batch_output_path_names_structured_mid_and_musicxml(tmp_path: Path) -> None:
    source = tmp_path / "飞鼠进行曲.mid"

    mid_path = cli.batch_output_path(source, tmp_path / "arranged", "orchestra", "mid")
    musicxml_path = cli.batch_output_path(
        source,
        tmp_path / "arranged",
        "string_quartet",
        "musicxml",
    )

    assert mid_path == tmp_path / "arranged" / "orchestra" / "mid" / "飞鼠进行曲.mid"
    assert musicxml_path == (
        tmp_path / "arranged" / "string_quartet" / "musicxml" / "飞鼠进行曲.musicxml"
    )


def test_batch_arrange_skips_output_dir_and_records_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "scores"
    out_dir = input_dir / "arranged"
    input_dir.mkdir()
    good = input_dir / "good.mid"
    bad = input_dir / "bad.mid"
    generated = out_dir / "orchestra" / "mid" / "already.mid"
    good.write_bytes(b"good")
    bad.write_bytes(b"bad")
    generated.parent.mkdir(parents=True)
    generated.write_bytes(b"generated")

    calls: list[tuple[Path, str, str, Path]] = []

    def fake_arrange(source: Path, ensemble: str, output_format: str, destination: Path) -> None:
        calls.append((source, ensemble, output_format, destination))
        if source.name == "bad.mid":
            raise RuntimeError("cannot arrange")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    monkeypatch.setattr(cli, "arrange_midi", fake_arrange)

    report = cli.batch_arrange(
        input_dir,
        ensembles=("orchestra",),
        output_format="mid",
        out_dir=out_dir,
    )

    assert report.succeeded == 1
    assert report.failed == 1
    assert report.failures[0].source == bad
    assert report.failures[0].ensemble == "orchestra"
    assert "RuntimeError: cannot arrange" == report.failures[0].error
    assert [call[0].name for call in calls] == ["bad.mid", "good.mid"]
    assert generated not in [call[0] for call in calls]
    assert (out_dir / "orchestra" / "mid" / "good.mid").read_bytes() == b"good"


def test_batch_arrange_all_ensembles_writes_each_supported_ensemble(tmp_path: Path) -> None:
    input_dir = tmp_path / "scores"
    out_dir = tmp_path / "arranged"
    input_dir.mkdir()
    (input_dir / "song.mid").write_bytes(b"midi")

    report = cli.batch_arrange(
        input_dir,
        ensembles=cli.SUPPORTED_ENSEMBLES,
        output_format="mid",
        out_dir=out_dir,
    )

    assert report.succeeded == len(cli.SUPPORTED_ENSEMBLES)
    assert report.failed == 0
    for ensemble in cli.SUPPORTED_ENSEMBLES:
        assert (out_dir / ensemble / "mid" / "song.mid").read_bytes() == b"midi"
