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
