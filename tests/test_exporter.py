from __future__ import annotations

from pathlib import Path

from scoresheet.musicxml_exporter import export_musicxml, export_parts_musicxml


def test_export_musicxml_writes_non_empty_score(orchestration_result, tmp_path: Path) -> None:
    output = export_musicxml(orchestration_result, tmp_path / "score.musicxml", title="Test Score")
    text = output.read_text(encoding="utf-8")

    assert output.exists()
    assert output.stat().st_size > 100
    assert "Flute" in text
    assert "Violin" in text


def test_export_parts_musicxml_writes_part_files(orchestration_result, tmp_path: Path) -> None:
    paths = export_parts_musicxml(orchestration_result, tmp_path / "parts", title_prefix="Fixture")

    assert paths
    assert all(path.exists() and path.stat().st_size > 0 for path in paths)
