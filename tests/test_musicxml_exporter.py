from __future__ import annotations

from pathlib import Path

from music21 import stream

from scoresheet.musicxml_exporter import build_score, export_midi, export_musicxml, export_parts_musicxml


EXPECTED_PART_NAMES = ("Flute", "Violin", "Cello", "Double Bass")


def test_build_score_returns_music21_score(orchestration_result) -> None:
    score = build_score(orchestration_result)

    assert isinstance(score, stream.Score)
    assert score.parts


def test_export_musicxml_writes_non_empty_score_with_part_names(orchestration_result, tmp_path: Path) -> None:
    output = export_musicxml(orchestration_result, tmp_path / "score.musicxml", title="Exporter Test")
    text = output.read_text(encoding="utf-8")

    assert output.exists()
    assert output.stat().st_size > 0
    assert any(name in text for name in EXPECTED_PART_NAMES)


def test_export_parts_musicxml_writes_multiple_non_empty_part_files(orchestration_result, tmp_path: Path) -> None:
    parts = export_parts_musicxml(orchestration_result, tmp_path / "parts", title_prefix="Exporter Test")

    assert len(parts) > 1
    assert all(part.exists() for part in parts)
    assert all(part.stat().st_size > 0 for part in parts)


def test_export_midi_writes_non_empty_mid_file(orchestration_result, tmp_path: Path) -> None:
    output = export_midi(orchestration_result, tmp_path / "score.mid", title="Exporter Test")

    assert output.exists()
    assert output.stat().st_size > 0
