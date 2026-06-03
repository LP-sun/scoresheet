from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scoresheet import musescore_backend as backend


def test_find_musescore_executable_reads_scoresheet_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "MuseScore4.exe"
    executable.write_text("fake", encoding="utf-8")
    monkeypatch.setenv("SCORESHEET_MUSESCORE", str(executable))
    monkeypatch.delenv("MUSESCORE_EXECUTABLE", raising=False)
    monkeypatch.setattr(backend.shutil, "which", lambda name: None)

    assert backend.find_musescore_executable() == executable


def test_convert_midi_with_musescore_skips_when_executable_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_midi = tmp_path / "input.mid"
    input_midi.write_bytes(b"MThd")
    output_path = tmp_path / "out.mscz"
    monkeypatch.delenv("SCORESHEET_MUSESCORE", raising=False)
    monkeypatch.delenv("MUSESCORE_EXECUTABLE", raising=False)
    monkeypatch.setattr(backend.shutil, "which", lambda name: None)

    result = backend.convert_midi_with_musescore(input_midi, output_path)

    assert result.skipped is True
    assert result.ok is False
    assert result.reason == "MuseScore executable not found"
    assert result.executable is None


def test_convert_midi_with_musescore_ok_when_returncode_zero_and_output_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_midi = tmp_path / "input.mid"
    input_midi.write_bytes(b"MThd")
    output_path = tmp_path / "out.mscz"
    executable = tmp_path / "mscore"
    executable.write_text("fake", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(args)
        assert isinstance(args, list)
        assert kwargs.get("shell") in (None, False)
        output_path.write_bytes(b"mscz")
        return SimpleNamespace(returncode=0, stdout="import ok", stderr="")

    monkeypatch.setattr(backend.subprocess, "run", fake_run)

    result = backend.convert_midi_with_musescore(input_midi, output_path, executable=executable)

    assert result.ok is True
    assert result.skipped is False
    assert calls == [[str(executable), str(input_midi), "-o", str(output_path)]]


def test_convert_midi_with_musescore_fails_on_nonzero_returncode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_midi = tmp_path / "input.mid"
    input_midi.write_bytes(b"MThd")
    output_path = tmp_path / "out.musicxml"
    output_path.write_text("musicxml", encoding="utf-8")
    executable = tmp_path / "mscore"
    executable.write_text("fake", encoding="utf-8")

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="failed")

    monkeypatch.setattr(backend.subprocess, "run", fake_run)

    result = backend.convert_midi_with_musescore(input_midi, output_path, executable=executable)

    assert result.ok is False
    assert result.skipped is False
    assert result.returncode == 1
    assert result.reason == "MuseScore exited with return code 1"


def test_convert_midi_with_musescore_fails_on_error_keywords(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_midi = tmp_path / "input.mid"
    input_midi.write_bytes(b"MThd")
    output_path = tmp_path / "out.musicxml"
    executable = tmp_path / "mscore"
    executable.write_text("fake", encoding="utf-8")

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        output_path.write_text("musicxml", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="incomplete measure / 不完整小节")

    monkeypatch.setattr(backend.subprocess, "run", fake_run)

    result = backend.convert_midi_with_musescore(input_midi, output_path, executable=executable)

    assert result.ok is False
    assert result.skipped is False
    assert result.reason == "MuseScore output contained an error keyword"


def test_convert_midi_with_musescore_uses_list_args_without_shell_and_midi_operations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_midi = tmp_path / "input.mid"
    input_midi.write_bytes(b"MThd")
    output_path = tmp_path / "out.mscz"
    operations = tmp_path / "midi_import_options.xml"
    operations.write_text("<midi-import-options />", encoding="utf-8")
    executable = tmp_path / "MuseScore 4" / "bin" / "MuseScore4.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("fake", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(args)
        assert isinstance(args, list)
        assert kwargs.get("shell") in (None, False)
        output_path.write_bytes(b"mscz")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(backend.subprocess, "run", fake_run)

    result = backend.convert_midi_with_musescore(
        input_midi,
        output_path,
        executable=executable,
        midi_operations=operations,
    )

    assert result.ok is True
    assert calls == [[str(executable), "-M", str(operations), str(input_midi), "-o", str(output_path)]]
