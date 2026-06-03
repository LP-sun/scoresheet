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

    def fake_export_musicxml(result: OrchestrationResult, path: Path, title: str, pitch_mode: str = "written") -> Path:
        calls.append(("musicxml", path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("musicxml", encoding="utf-8")
        return path

    def fake_export_midi(result: OrchestrationResult, path: Path, title: str) -> Path:
        calls.append(("mid", path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"MThd")
        return path

    def fake_export_parts(result: OrchestrationResult, path: Path, title_prefix: str, pitch_mode: str = "written") -> list[Path]:
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
    assert calls[1][1].output_musicxml is True
    assert calls[1][1].output_midi is False


def test_cli_default_pitch_mode_is_written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    captured: dict[str, str] = {}

    def fake_export_musicxml(result: OrchestrationResult, path: Path, title: str, pitch_mode: str = "written") -> Path:
        captured["pitch_mode"] = pitch_mode
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("musicxml", encoding="utf-8")
        return path

    monkeypatch.setattr(cli, "parse_midi", lambda path: _fake_parsed(path))
    monkeypatch.setattr(cli, "orchestrate", lambda parsed, config: _fake_result(config))
    monkeypatch.setattr(cli, "export_musicxml", fake_export_musicxml)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--format", "musicxml"])

    assert exit_code == 0
    assert captured["pitch_mode"] == "written"


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


def test_cli_pitch_mode_flags_are_forwarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    captured: list[str] = []

    def fake_export_musicxml(result: OrchestrationResult, path: Path, title: str, pitch_mode: str = "written") -> Path:
        captured.append(pitch_mode)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("musicxml", encoding="utf-8")
        return path

    monkeypatch.setattr(cli, "parse_midi", lambda path: _fake_parsed(path))
    monkeypatch.setattr(cli, "orchestrate", lambda parsed, config: _fake_result(config))
    monkeypatch.setattr(cli, "export_musicxml", fake_export_musicxml)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--format", "musicxml", "--pitch-mode", "concert"])

    assert exit_code == 0
    assert captured == ["concert"]


def test_cli_warns_but_continues_for_non_midi_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    input_path = tmp_path / "song.txt"
    input_path.write_bytes(b"not really midi")
    calls: list[tuple[str, object]] = []
    _patch_pipeline(monkeypatch, calls)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--format", "musicxml"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "warning: input file does not end with .mid/.midi" in captured.err
    assert [name for name, _ in calls] == ["parse", "orchestrate", "musicxml"]


def test_cli_invalid_quantization_unit_does_not_succeed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    calls: list[Path] = []

    def fake_parse(path: Path) -> ParsedMidi:
        calls.append(path)
        from scoresheet.midi_parser import ParsedNote

        return ParsedMidi(
            path=path,
            notes=[ParsedNote(60, 0.0, 1.0, 1.0, 80, None, 0, "Piano", 0)],
            meta=MidiMeta(tempos=[(0.0, 120.0)], time_signatures=[(0.0, 4, 4)]),
            length_seconds=1.0,
        )

    monkeypatch.setattr(cli, "parse_midi", fake_parse)

    with pytest.raises(ValueError, match="quantization_unit must be positive"):
        cli.main([str(input_path), "-o", str(tmp_path / "out"), "--quantization-unit", "0"])

    assert calls == [input_path]


def test_cli_unknown_ensemble_is_rejected_by_argparse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")

    def fail_if_pipeline_runs(path: Path) -> ParsedMidi:
        pytest.fail(f"argparse should reject unknown ensembles before parsing {path}")

    monkeypatch.setattr(cli, "parse_midi", fail_if_pipeline_runs)

    with pytest.raises(SystemExit) as excinfo:
        cli.main([str(input_path), "--ensemble", "not_real"])

    assert excinfo.value.code == 2


def test_cli_does_not_validate_musescore_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    calls: list[tuple[str, object]] = []
    _patch_pipeline(monkeypatch, calls)

    def fail_validate(*args: object, **kwargs: object) -> object:
        pytest.fail("MuseScore validation should not run unless --validate-musescore is set")

    monkeypatch.setattr(cli, "validate_with_musescore", fail_validate)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--format", "musicxml"])

    assert exit_code == 0
    assert [name for name, _ in calls] == ["parse", "orchestrate", "musicxml"]


def test_cli_validate_musescore_skipped_warns_without_failing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scoresheet.musescore_validator import MuseScoreValidationResult

    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    calls: list[tuple[str, object]] = []
    _patch_pipeline(monkeypatch, calls)

    def fake_validate(path: Path, executable: Path | None = None) -> MuseScoreValidationResult:
        calls.append(("validate", path))
        return MuseScoreValidationResult(
            executable=None,
            input_score=path,
            output_path=path.with_name(f"{path.stem}.validated.mscz"),
            returncode=None,
            stdout="",
            stderr="",
            ok=False,
            skipped=True,
            reason="MuseScore executable not found",
        )

    monkeypatch.setattr(cli, "validate_with_musescore", fake_validate)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--format", "musicxml", "--validate-musescore"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "warning: MuseScore validation skipped: MuseScore executable not found" in captured.err
    assert [name for name, _ in calls] == ["parse", "orchestrate", "musicxml", "validate"]


def test_cli_validate_musescore_failure_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scoresheet.musescore_validator import MuseScoreValidationResult

    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    calls: list[tuple[str, object]] = []
    _patch_pipeline(monkeypatch, calls)

    def fake_validate(path: Path, executable: Path | None = None) -> MuseScoreValidationResult:
        return MuseScoreValidationResult(
            executable=Path("mscore"),
            input_score=path,
            output_path=path.with_name(f"{path.stem}.validated.mscz"),
            returncode=1,
            stdout="started import",
            stderr="incomplete measure",
            ok=False,
            skipped=False,
            reason="MuseScore exited with return code 1",
        )

    monkeypatch.setattr(cli, "validate_with_musescore", fake_validate)

    exit_code = cli.main([str(input_path), "-o", str(tmp_path / "out"), "--format", "musicxml", "--validate-musescore"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "error: MuseScore validation failed: MuseScore exited with return code 1" in captured.err
    assert "MuseScore stdout:" in captured.err
    assert "MuseScore stderr:" in captured.err


def test_cli_musescore_executable_argument_is_forwarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scoresheet.musescore_validator import MuseScoreValidationResult

    input_path = tmp_path / "song.mid"
    input_path.write_bytes(b"midi")
    calls: list[tuple[str, object]] = []
    _patch_pipeline(monkeypatch, calls)
    executable = tmp_path / "MuseScore 4" / "bin" / "MuseScore4.exe"
    captured: dict[str, Path | None] = {}

    def fake_validate(path: Path, executable: Path | None = None) -> MuseScoreValidationResult:
        captured["executable"] = executable
        return MuseScoreValidationResult(
            executable=executable,
            input_score=path,
            output_path=path.with_name(f"{path.stem}.validated.mscz"),
            returncode=0,
            stdout="",
            stderr="",
            ok=True,
            skipped=False,
            reason=None,
        )

    monkeypatch.setattr(cli, "validate_with_musescore", fake_validate)

    exit_code = cli.main(
        [
            str(input_path),
            "-o",
            str(tmp_path / "out"),
            "--format",
            "musicxml",
            "--validate-musescore",
            "--musescore-executable",
            str(executable),
        ]
    )

    assert exit_code == 0
    assert captured["executable"] == executable
