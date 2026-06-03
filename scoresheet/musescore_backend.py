"""MuseScore CLI conversion backend for arranged MIDI files."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess


_ERROR_KEYWORDS = (
    "incomplete measure",
    "corrupt",
    "failed",
    "error",
    "不完整小节",
    "错误",
)

_EXECUTABLE_CANDIDATES = (
    "MuseScore4.exe",
    "MuseScore4",
    "mscore",
    "musescore",
    "mscore4portable",
)


@dataclass(frozen=True)
class MuseScoreConversionResult:
    """Result from converting an arranged MIDI file through MuseScore CLI."""

    executable: Path | None
    input_midi: Path
    output_path: Path
    returncode: int | None
    stdout: str
    stderr: str
    ok: bool
    skipped: bool
    reason: str | None


def _resolve_executable(candidate: str | Path | None) -> Path | None:
    if candidate is None:
        return None

    candidate_text = str(candidate).strip()
    if not candidate_text:
        return None

    candidate_path = Path(candidate_text).expanduser()
    if candidate_path.exists():
        return candidate_path

    found = shutil.which(candidate_text)
    if found:
        return Path(found)

    return None


def find_musescore_executable(explicit: str | Path | None = None) -> Path | None:
    """Find MuseScore CLI from an explicit path, environment, or PATH."""

    resolved = _resolve_executable(explicit)
    if resolved is not None:
        return resolved

    for env_name in ("SCORESHEET_MUSESCORE", "MUSESCORE_EXECUTABLE"):
        resolved = _resolve_executable(os.environ.get(env_name))
        if resolved is not None:
            return resolved

    for executable_name in _EXECUTABLE_CANDIDATES:
        resolved = _resolve_executable(executable_name)
        if resolved is not None:
            return resolved

    return None


def _contains_error_keyword(stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}".casefold()
    return any(keyword.casefold() in combined for keyword in _ERROR_KEYWORDS)


def convert_midi_with_musescore(
    input_midi: str | Path,
    output_path: str | Path,
    executable: str | Path | None = None,
    midi_operations: str | Path | None = None,
    timeout: int = 120,
) -> MuseScoreConversionResult:
    """Use MuseScore CLI converter mode to import MIDI and export a score file."""

    input_path = Path(input_midi)
    resolved_output = Path(output_path)
    resolved_executable = find_musescore_executable(executable)

    if resolved_executable is None:
        return MuseScoreConversionResult(
            executable=None,
            input_midi=input_path,
            output_path=resolved_output,
            returncode=None,
            stdout="",
            stderr="",
            ok=False,
            skipped=True,
            reason="MuseScore executable not found",
        )

    command = [str(resolved_executable)]
    if midi_operations is not None:
        command.extend(["-M", str(Path(midi_operations))])
    command.extend([str(input_path), "-o", str(resolved_output)])

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output_exists = resolved_output.exists() and resolved_output.stat().st_size > 0
    has_error_output = _contains_error_keyword(completed.stdout, completed.stderr)
    ok = completed.returncode == 0 and output_exists and not has_error_output

    reason = None
    if completed.returncode != 0:
        reason = f"MuseScore exited with return code {completed.returncode}"
    elif not output_exists:
        reason = "MuseScore output file was not created or is empty"
    elif has_error_output:
        reason = "MuseScore output contained an error keyword"

    return MuseScoreConversionResult(
        executable=resolved_executable,
        input_midi=input_path,
        output_path=resolved_output,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        ok=ok,
        skipped=False,
        reason=reason,
    )
