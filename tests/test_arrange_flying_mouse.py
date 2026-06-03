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
