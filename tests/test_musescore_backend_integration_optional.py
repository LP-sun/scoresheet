from __future__ import annotations

from pathlib import Path

import pytest

from scoresheet import cli
from scoresheet.musescore_backend import find_musescore_executable


def test_musescore_backend_cli_optional_integration(tmp_path: Path) -> None:
    pretty_midi = pytest.importorskip("pretty_midi")
    executable = find_musescore_executable()
    if executable is None:
        pytest.skip("MuseScore executable not found")

    input_mid = tmp_path / "tiny.mid"
    midi = pretty_midi.PrettyMIDI(initial_tempo=120)
    piano = pretty_midi.Instrument(program=0, name="Piano")
    piano.notes.append(pretty_midi.Note(velocity=80, pitch=60, start=0.0, end=1.0))
    midi.instruments.append(piano)
    midi.write(str(input_mid))

    output_dir = tmp_path / "out"
    exit_code = cli.main(
        [
            str(input_mid),
            "-o",
            str(output_dir),
            "--backend",
            "musescore",
            "--format",
            "mscz",
            "--musescore-executable",
            str(executable),
        ]
    )

    output_path = output_dir / "tiny_small_orchestra.mscz"
    assert exit_code == 0
    assert output_path.exists()
    assert output_path.stat().st_size > 0
