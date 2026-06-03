from __future__ import annotations

from pathlib import Path

import pytest

from scoresheet import cli
from scoresheet.midi_parser import MidiMeta, ParsedMidi
from scoresheet.orchestrator import OrchestrationConfig, OrchestrationResult


def _fake_parsed(path: Path) -> ParsedMidi:
    return ParsedMidi(
        path=path,
        notes=[],
        meta=MidiMeta(tempos=[(0.0, 120.0)], time_signatures=[(0.0, 4, 4)]),
        length_seconds=0.0,
    )


def _fake_result(config: OrchestrationConfig) -> OrchestrationResult:
    return OrchestrationResult(
        config=config,
        instruments=(),
        notes_by_instrument={},
        tempo_bpm=120.0,
        time_signature=(4, 4),
        key_signature=None,
    )


def _patch_pipeline(monkeypatch: pytest.MonkeyPatch, calls: list[tuple[str, object]]) -> None:
    def fake_parse(path: Path) -> ParsedMidi:
        calls.append(("parse", path))
        return _fake_parsed(path)

    def fake_orchestrate(parsed: ParsedMidi, config: OrchestrationConfig) -> OrchestrationResult:
        calls.append(("orchestrate", config))
        return _fake_result(config)

    def fake_export_musicxml(result: OrchestrationResult, path: Path, title: str) -> Path:
        calls.append(("musicxml", path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("musicxml", encoding="utf-8")
        return path

    def fake_export_midi(result: OrchestrationResult, path: Path, title: str) -> Path:
        calls.append(("mid", path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"MThd")
        return path

    def fake_export_parts(result: OrchestrationResult, path: Path, title_prefix: str) -> list[Path]:
        calls.append(("parts", path))
        path.mkdir(parents=True, exist_ok=True)
        part_path = path / "flute.musicxml"
        part_path.write_text("part", encoding="utf-8")
        return [part_path]

    monkeypatch.setattr(cli, "parse_midi", fake_parse)
    monkeypatch.setattr(cli, "orchestrate", fake_orchestrate)
    monkeypatch.setattr(cli, "export_musicxml", fake_export_musicxml)
    monkeypatch.setattr(cli, "export_midi", fake_export_midi)
    monkeypatch.setattr(cli, "export_parts_musicxml", fake_export_parts)


def test_cli_missing_input_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["does-not-exist.mid"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "does not exist" in captured.err


def test_cli_musicxml_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    calls: list[tuple[str, object]] = []
    _patch_pipeline(monkeypatch, calls)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--ensemble", "small_orchestra", "--format", "musicxml"])

    assert exit_code == 0
    assert [name for name, _ in calls] == ["parse", "orchestrate", "musicxml"]


def test_cli_mid_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    calls: list[tuple[str, object]] = []
    _patch_pipeline(monkeypatch, calls)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--format", "mid"])

    assert exit_code == 0
    assert [name for name, _ in calls] == ["parse", "orchestrate", "mid"]


def test_cli_both_and_parts_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    calls: list[tuple[str, object]] = []
    _patch_pipeline(monkeypatch, calls)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--format", "both", "--parts"])

    assert exit_code == 0
    assert [name for name, _ in calls] == ["parse", "orchestrate", "musicxml", "mid", "parts"]
