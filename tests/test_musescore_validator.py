from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scoresheet import musescore_validator as validator


def test_find_musescore_executable_reads_scoresheet_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "MuseScore4.exe"
    executable.write_text("fake", encoding="utf-8")
    monkeypatch.setenv("SCORESHEET_MUSESCORE", str(executable))
    monkeypatch.delenv("MUSESCORE_EXECUTABLE", raising=False)
    monkeypatch.setattr(validator.shutil, "which", lambda name: None)

    assert validator.find_musescore_executable() == executable


def test_validate_with_musescore_skips_when_executable_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_score = tmp_path / "input.musicxml"
    input_score.write_text("<score-partwise />", encoding="utf-8")
    monkeypatch.delenv("SCORESHEET_MUSESCORE", raising=False)
    monkeypatch.delenv("MUSESCORE_EXECUTABLE", raising=False)
    monkeypatch.setattr(validator.shutil, "which", lambda name: None)

    result = validator.validate_with_musescore(input_score)

    assert result.skipped is True
    assert result.ok is False
    assert result.reason == "MuseScore executable not found"
    assert result.executable is None


def test_validate_with_musescore_ok_when_returncode_zero_and_output_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_score = tmp_path / "input.musicxml"
    input_score.write_text("<score-partwise />", encoding="utf-8")
    executable = tmp_path / "mscore"
    executable.write_text("fake", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(args)
        assert isinstance(args, list)
        assert kwargs.get("shell") in (None, False)
        output_path = Path(args[2])
        output_path.write_bytes(b"mscz")
        return SimpleNamespace(returncode=0, stdout="import ok", stderr="")

    monkeypatch.setattr(validator.subprocess, "run", fake_run)

    result = validator.validate_with_musescore(input_score, executable=executable)

    assert result.ok is True
    assert result.skipped is False
    assert result.output_path == tmp_path / "input.validated.mscz"
    assert calls == [[str(executable), "-o", str(tmp_path / "input.validated.mscz"), str(input_score)]]


def test_validate_with_musescore_fails_on_nonzero_incomplete_measure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_score = tmp_path / "input.musicxml"
    input_score.write_text("<score-partwise />", encoding="utf-8")
    output_path = tmp_path / "custom.mscz"
    output_path.write_bytes(b"mscz")
    executable = tmp_path / "mscore"
    executable.write_text("fake", encoding="utf-8")

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="Incomplete Measure at bar 1")

    monkeypatch.setattr(validator.subprocess, "run", fake_run)

    result = validator.validate_with_musescore(input_score, output_path=output_path, executable=executable)

    assert result.ok is False
    assert result.skipped is False
    assert result.returncode == 1
    assert result.reason == "MuseScore exited with return code 1"


def test_validate_with_musescore_fails_on_chinese_error_keyword(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_score = tmp_path / "input.musicxml"
    input_score.write_text("<score-partwise />", encoding="utf-8")
    output_path = tmp_path / "input.validated.mscz"
    executable = tmp_path / "mscore"
    executable.write_text("fake", encoding="utf-8")

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        output_path.write_bytes(b"mscz")
        return SimpleNamespace(returncode=0, stdout="发现不完整小节", stderr="")

    monkeypatch.setattr(validator.subprocess, "run", fake_run)

    result = validator.validate_with_musescore(input_score, executable=executable)

    assert result.ok is False
    assert result.skipped is False
    assert result.reason == "MuseScore output contained an error keyword"


def test_validate_with_musescore_uses_list_args_without_shell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_score = tmp_path / "input.musicxml"
    input_score.write_text("<score-partwise />", encoding="utf-8")
    executable = tmp_path / "MuseScore 4" / "bin" / "MuseScore4.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("fake", encoding="utf-8")

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        assert isinstance(args, list)
        assert kwargs.get("shell") in (None, False)
        Path(args[2]).write_bytes(b"mscz")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(validator.subprocess, "run", fake_run)

    result = validator.validate_with_musescore(input_score, executable=executable)

    assert result.ok is True
