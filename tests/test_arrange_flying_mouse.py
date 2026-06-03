from __future__ import annotations

from pathlib import Path

import pytest

from scoresheet.cli import main


def test_cli_arranges_flying_mouse_if_sample_exists(tmp_path: Path) -> None:
    sample = Path("飞鼠进行曲.mid")
    if not sample.exists():
        pytest.skip("Repository sample 飞鼠进行曲.mid is not present in this checkout.")

    output = tmp_path / "flying_mouse.musicxml"
    exit_code = main(["arrange", str(sample), "--ensemble", "small_orchestra", "--output", str(output)])

    assert exit_code == 0
    assert output.exists()
    assert output.stat().st_size > 100
"""Structure-level arrangement tests for ``飞鼠进行曲.mid``.

These tests intentionally avoid internet access and MuseScore/GUI rendering.  They
exercise an arranger CLI, then inspect the generated MIDI and MusicXML directly.

By default the tests look for one of these CLIs:

* ``python -m scoresheet arrange ...``
* ``python -m scoresheet.arrange ...``
* ``scoresheet arrange ...``

Projects with a different entry point can set ``ARRANGE_COMMAND``.  The command
may include these placeholders: ``{input}``, ``{target}``, ``{midi}``,
``{musicxml}``, and ``{output_dir}``.  Example::

    ARRANGE_COMMAND='python -m my_arranger --input {input} --target {target} \
      --output-midi {midi} --output-musicxml {musicxml}' pytest
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import shlex
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_MIDI = REPO_ROOT / "飞鼠进行曲.mid"
TARGETS = {
    "string_quartet": {
        "expected_names": {"violin", "viola", "cello", "violoncello"},
        "expected_programs": set(range(41, 50)),
        "min_tracks": 4,
    },
    "wind_quintet": {
        "expected_names": {"flute", "oboe", "clarinet", "bassoon", "horn"},
        "expected_programs": {61, 69, 70, 71, 72, 73, 74},
        "min_tracks": 5,
    },
    "string_ensemble": {
        "expected_names": {"violin", "viola", "cello", "bass", "strings"},
        "expected_programs": set(range(41, 50)),
        "min_tracks": 4,
    },
    "wind_band": {
        "expected_names": {
            "flute",
            "oboe",
            "clarinet",
            "sax",
            "bassoon",
            "trumpet",
            "trombone",
            "tuba",
            "horn",
        },
        "expected_programs": set(range(56, 81)),
        "min_tracks": 5,
    },
    "orchestra": {
        "expected_names": {
            "violin",
            "viola",
            "cello",
            "bass",
            "flute",
            "oboe",
            "clarinet",
            "bassoon",
            "horn",
            "trumpet",
            "trombone",
            "tuba",
        },
        "expected_programs": set(range(41, 50)) | set(range(56, 81)),
        "min_tracks": 8,
    },
}


def _read_varlen(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, offset


def _parse_midi(path: Path) -> dict[str, object]:
    """Return track names and one-based General MIDI programs from an SMF file."""
    data = path.read_bytes()
    assert data[:4] == b"MThd", f"{path} is not a Standard MIDI file"
    header_size = struct.unpack(">I", data[4:8])[0]
    midi_format, track_count, _division = struct.unpack(">HHH", data[8:14])
    assert midi_format in {0, 1, 2}

    offset = 8 + header_size
    track_names: list[str] = []
    programs_by_track: list[set[int]] = []

    for track_index in range(track_count):
        assert data[offset : offset + 4] == b"MTrk", f"missing MTrk chunk #{track_index}"
        track_length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        pos = offset + 8
        end = pos + track_length
        offset = end
        running_status: int | None = None
        track_programs: set[int] = set()

        while pos < end:
            _delta, pos = _read_varlen(data, pos)
            status = data[pos]
            if status & 0x80:
                pos += 1
                if status < 0xF0:
                    running_status = status
            elif running_status is not None:
                status = running_status
            else:
                raise AssertionError(f"running status without previous status in track #{track_index}")

            if status == 0xFF:
                meta_type = data[pos]
                pos += 1
                length, pos = _read_varlen(data, pos)
                payload = data[pos : pos + length]
                pos += length
                if meta_type in {0x03, 0x04}:
                    track_names.append(payload.decode("utf-8", errors="ignore").strip())
                if meta_type == 0x2F:
                    break
            elif status in {0xF0, 0xF7}:
                length, pos = _read_varlen(data, pos)
                pos += length
            else:
                event_type = status & 0xF0
                if event_type in {0xC0, 0xD0}:
                    param = data[pos]
                    pos += 1
                    if event_type == 0xC0:
                        track_programs.add(param + 1)
                else:
                    pos += 2

        if track_programs:
            programs_by_track.append(track_programs)

    return {
        "track_count": track_count,
        "track_names": track_names,
        "programs_by_track": programs_by_track,
        "programs": set().union(*programs_by_track) if programs_by_track else set(),
    }


def _xml_text(path: Path) -> str:
    root = ET.parse(path).getroot()
    texts = [element.text or "" for element in root.iter()]
    return "\n".join(texts).lower()


def _find_spec(name: str):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


def _default_command() -> list[str] | None:
    if _find_spec("scoresheet.__main__") is not None:
        return [sys.executable, "-m", "scoresheet", "arrange"]
    if _find_spec("scoresheet.arrange") is not None:
        return [sys.executable, "-m", "scoresheet.arrange"]
    executable = shutil.which("scoresheet")
    if executable:
        return [executable, "arrange"]
    return None


def _arrange(input_midi: Path, target: str, output_midi: Path, output_musicxml: Path) -> None:
    output_midi.parent.mkdir(parents=True, exist_ok=True)
    output_musicxml.parent.mkdir(parents=True, exist_ok=True)

    command_template = os.environ.get("ARRANGE_COMMAND")
    if command_template:
        command = [
            part.format(
                input=str(input_midi),
                target=target,
                midi=str(output_midi),
                musicxml=str(output_musicxml),
                output_dir=str(output_midi.parent),
            )
            for part in shlex.split(command_template)
        ]
    else:
        base_command = _default_command()
        if base_command is None:
            pytest.skip(
                "No arranger entry point found. Set ARRANGE_COMMAND to run these "
                "contract tests against a custom CLI."
            )
        command = [
            *base_command,
            "--input",
            str(input_midi),
            "--target",
            target,
            "--output-midi",
            str(output_midi),
            "--output-musicxml",
            str(output_musicxml),
        ]

    subprocess.run(command, check=True, cwd=REPO_ROOT, timeout=120)


@pytest.mark.parametrize("target", TARGETS.keys())
def test_arrange_flying_mouse_to_target_instrumentation(tmp_path: Path, target: str) -> None:
    assert INPUT_MIDI.is_file(), "The 飞鼠进行曲.mid fixture must exist in the repository root"
    expected = TARGETS[target]
    output_midi = tmp_path / target / "飞鼠进行曲.arranged.mid"
    output_musicxml = tmp_path / target / "飞鼠进行曲.arranged.musicxml"

    _arrange(INPUT_MIDI, target, output_midi, output_musicxml)

    assert output_midi.is_file(), f"{target} should generate an output MIDI file"
    assert output_midi.stat().st_size > 0, f"{target} output MIDI should not be empty"

    midi = _parse_midi(output_midi)
    assert len(midi["programs_by_track"]) >= expected["min_tracks"], (
        f"{target} MIDI should contain multiple target instrument tracks; "
        f"found programs by track: {midi['programs_by_track']}"
    )
    assert midi["programs"] & expected["expected_programs"], (
        f"{target} MIDI programs should roughly match the requested ensemble; "
        f"found programs: {sorted(midi['programs'])}"
    )

    track_name_text = "\n".join(midi["track_names"]).lower()
    assert expected["expected_names"] & set(track_name_text.replace("-", " ").split()), (
        f"{target} MIDI should include target instrument track names; "
        f"found names: {midi['track_names']}"
    )

    assert output_musicxml.is_file(), f"{target} should generate an output MusicXML file"
    assert output_musicxml.stat().st_size > 0, f"{target} output MusicXML should not be empty"
    musicxml_text = _xml_text(output_musicxml)
    assert expected["expected_names"] & set(musicxml_text.replace("-", " ").split()), (
        f"{target} MusicXML should include target part/instrument names"
    )
