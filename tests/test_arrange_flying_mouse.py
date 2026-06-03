from __future__ import annotations

from pathlib import Path

import pytest

from scoresheet.cli import main


def test_cli_arranges_flying_mouse_if_sample_exists(tmp_path: Path) -> None:
    sample = Path("飞鼠进行曲.mid")
    if not sample.exists():
        pytest.skip("Repository sample 飞鼠进行曲.mid is not present in this checkout.")

    exit_code = main([str(sample), "-o", str(tmp_path), "--ensemble", "small_orchestra", "--format", "musicxml"])

    assert exit_code == 0
    output = tmp_path / "飞鼠进行曲_small_orchestra.musicxml"
    assert output.exists()
    assert output.stat().st_size > 100
