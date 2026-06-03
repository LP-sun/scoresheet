from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from music21 import converter, stream

from scoresheet.midi_parser import ParsedNote
from scoresheet.musicxml_exporter import build_score, export_midi, export_musicxml, export_parts_musicxml
from scoresheet.orchestrator import InstrumentSpec, MusicalRole, OrchestrationConfig, OrchestrationResult, OrchestratedNote


def _note(
    pitch: int,
    start: float,
    duration_beats: float,
    *,
    velocity: int = 80,
    instrument_spec: InstrumentSpec,
) -> OrchestratedNote:
    return OrchestratedNote(
        source=ParsedNote(pitch, start, start + duration_beats, duration_beats, velocity, None, 0, instrument_spec.name, instrument_spec.midi_program),
        pitch=pitch,
        start_beat=start,
        duration_beats=duration_beats,
        velocity=velocity,
        role=MusicalRole.MELODY,
        instrument=instrument_spec,
    )


def _result_9_8(*, pitch_mode: str = "written") -> OrchestrationResult:
    clarinet = InstrumentSpec("Clarinet", 71, "treble", (50, 94), (50, 94), transposition=2)
    horn = InstrumentSpec("Horn", 60, "treble", (41, 77), (41, 77), transposition=7)
    flute = InstrumentSpec("Flute", 73, "treble", (60, 96), (60, 96))
    instruments = (clarinet, horn, flute)
    notes_by_instrument = {
        "Clarinet": [_note(60, 0.0, 3.0, instrument_spec=clarinet), _note(62, 3.0, 1.5, instrument_spec=clarinet)],
        "Horn": [_note(55, 0.0, 5.0, instrument_spec=horn)],
        "Flute": [_note(72, 0.0, 1.0, instrument_spec=flute)],
    }
    return OrchestrationResult(
        config=OrchestrationConfig(target_ensemble="small_orchestra"),
        instruments=instruments,
        notes_by_instrument=notes_by_instrument,
        tempo_bpm=120.0,
        time_signature=(9, 8),
        key_signature="C",
        concert_key="C major",
    )


def _load_musicxml(path: Path) -> stream.Score:
    return converter.parse(str(path))


def _musicxml_root(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def _part_map(root: ET.Element) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for score_part in root.findall("./part-list/score-part"):
        part_id = score_part.attrib["id"]
        part_name = score_part.findtext("./part-name") or part_id
        mapping[part_name] = part_id
    return mapping


def _first_part_measure(root: ET.Element, part_name: str) -> ET.Element:
    mapping = _part_map(root)
    part_id = mapping[part_name]
    return root.find(f"./part[@id='{part_id}']/measure")  # type: ignore[return-value]


def _first_note_pitch(measure: ET.Element) -> str:
    note_el = measure.find("./note[pitch]")
    assert note_el is not None
    step = note_el.findtext("./pitch/step")
    alter = note_el.findtext("./pitch/alter")
    octave = note_el.findtext("./pitch/octave")
    assert step is not None and octave is not None
    accidental = ""
    if alter == "1":
        accidental = "#"
    elif alter == "-1":
        accidental = "-"
    return f"{step}{accidental}{octave}"


def _first_key_fifths(measure: ET.Element) -> int:
    fifths = measure.findtext("./attributes/key/fifths")
    assert fifths is not None
    return int(fifths)


def _first_transpose_chromatic(measure: ET.Element) -> int | None:
    chromatic = measure.findtext("./attributes/transpose/chromatic")
    return int(chromatic) if chromatic is not None else None


def test_build_score_returns_music21_score(orchestration_result) -> None:
    score = build_score(orchestration_result)

    assert isinstance(score, stream.Score)
    assert score.parts


def test_export_musicxml_writes_non_empty_score_with_part_names(orchestration_result, tmp_path: Path) -> None:
    output = export_musicxml(orchestration_result, tmp_path / "score.musicxml", title="Exporter Test")
    text = output.read_text(encoding="utf-8")

    assert output.exists()
    assert output.stat().st_size > 0
    assert any(name in text for name in ("Flute", "Violin", "Cello", "Double Bass"))


def test_export_parts_musicxml_writes_multiple_non_empty_part_files(orchestration_result, tmp_path: Path) -> None:
    parts = export_parts_musicxml(orchestration_result, tmp_path / "parts", title_prefix="Exporter Test")

    assert len(parts) > 1
    assert all(part.exists() for part in parts)
    assert all(part.stat().st_size > 0 for part in parts)


def test_export_midi_writes_non_empty_mid_file(orchestration_result, tmp_path: Path) -> None:
    output = export_midi(orchestration_result, tmp_path / "score.mid", title="Exporter Test")

    assert output.exists()
    assert output.stat().st_size > 0


def test_9_8_last_measure_is_filled_with_rests(tmp_path: Path) -> None:
    result = _result_9_8()
    output = export_musicxml(result, tmp_path / "score.musicxml", title="9/8 completeness")
    score = _load_musicxml(output)
    bar_length = 9 * 4 / 8

    for part in score.parts:
        measures = list(part.getElementsByClass(stream.Measure))
        last_measure = measures[-1] if measures else None
        assert last_measure is not None
        assert last_measure.duration.quarterLength == pytest.approx(bar_length)
        assert last_measure.notesAndRests
        assert sum(item.duration.quarterLength for item in last_measure.notesAndRests) == pytest.approx(bar_length)


def test_sparse_part_writes_full_rest_measures(tmp_path: Path) -> None:
    clarinet = InstrumentSpec("Clarinet", 71, "treble", (50, 94), (50, 94), transposition=2)
    flute = InstrumentSpec("Flute", 73, "treble", (60, 96), (60, 96))
    result = OrchestrationResult(
        config=OrchestrationConfig(target_ensemble="small_orchestra"),
        instruments=(clarinet, flute),
        notes_by_instrument={
            "Clarinet": [_note(60, 0.0, 1.0, instrument_spec=clarinet)],
            "Flute": [],
        },
        tempo_bpm=120.0,
        time_signature=(4, 4),
        key_signature=None,
        concert_key="C major",
    )
    output = export_musicxml(result, tmp_path / "sparse.musicxml", title="Sparse")
    score = _load_musicxml(output)

    flute_part = next(part for part in score.parts if part.partName == "Flute")
    assert flute_part.measure(1).notesAndRests
    assert flute_part.measure(1).duration.quarterLength == pytest.approx(4.0)


def test_long_note_is_split_into_ties(tmp_path: Path) -> None:
    clarinet = InstrumentSpec("Clarinet", 71, "treble", (50, 94), (50, 94), transposition=2)
    result = OrchestrationResult(
        config=OrchestrationConfig(target_ensemble="small_orchestra"),
        instruments=(clarinet,),
        notes_by_instrument={"Clarinet": [_note(60, 0.0, 5.0, instrument_spec=clarinet)]},
        tempo_bpm=120.0,
        time_signature=(4, 4),
        key_signature=None,
        concert_key="C major",
    )
    output = export_musicxml(result, tmp_path / "ties.musicxml", title="Ties")
    score = _load_musicxml(output)
    measures = list(score.parts[0].getElementsByClass(stream.Measure))

    assert len(measures) == 2
    first_notes = list(measures[0].notesAndRests)
    second_notes = list(measures[1].notesAndRests)
    assert first_notes[0].tie is not None and first_notes[0].tie.type in {"start", "continue"}
    assert second_notes[0].tie is not None and second_notes[0].tie.type in {"stop", "continue"}


def test_written_mode_emits_transpose_for_transposing_instrument(tmp_path: Path) -> None:
    clarinet = InstrumentSpec("Clarinet", 71, "treble", (50, 94), (50, 94), transposition=2)
    result = OrchestrationResult(
        config=OrchestrationConfig(target_ensemble="small_orchestra"),
        instruments=(clarinet,),
        notes_by_instrument={"Clarinet": [_note(60, 0.0, 1.0, instrument_spec=clarinet)]},
        tempo_bpm=120.0,
        time_signature=(4, 4),
        key_signature=None,
        concert_key="C major",
    )
    output = export_musicxml(result, tmp_path / "written.musicxml", title="Written", pitch_mode="written")
    text = output.read_text(encoding="utf-8")
    score = _load_musicxml(output)

    assert "<transpose>" in text
    assert "<chromatic>-2</chromatic>" in text
    assert score.parts[0].recurse().notes[0].pitch.nameWithOctave == "D4"


def test_concert_mode_omits_transpose_and_keeps_pitch(tmp_path: Path) -> None:
    clarinet = InstrumentSpec("Clarinet", 71, "treble", (50, 94), (50, 94), transposition=2)
    result = OrchestrationResult(
        config=OrchestrationConfig(target_ensemble="small_orchestra"),
        instruments=(clarinet,),
        notes_by_instrument={"Clarinet": [_note(60, 0.0, 1.0, instrument_spec=clarinet)]},
        tempo_bpm=120.0,
        time_signature=(4, 4),
        key_signature=None,
        concert_key="C major",
    )
    output = export_musicxml(result, tmp_path / "concert.musicxml", title="Concert", pitch_mode="concert")
    text = output.read_text(encoding="utf-8")
    score = _load_musicxml(output)

    assert "<transpose>" not in text
    assert score.parts[0].recurse().notes[0].pitch.nameWithOctave == "C4"


def test_written_mode_adds_key_signatures_for_transposing_instruments(tmp_path: Path) -> None:
    flute = InstrumentSpec("Flute", 73, "treble", (60, 96), (60, 96))
    clarinet = InstrumentSpec("Clarinet", 71, "treble", (50, 94), (50, 94), transposition=2)
    horn = InstrumentSpec("Horn", 60, "treble", (41, 77), (41, 77), transposition=7)
    trumpet = InstrumentSpec("Trumpet", 56, "treble", (55, 82), (55, 82), transposition=2)
    violin = InstrumentSpec("Violin I", 40, "treble", (55, 103), (55, 103))
    result = OrchestrationResult(
        config=OrchestrationConfig(target_ensemble="small_orchestra", concert_key="C major"),
        instruments=(flute, clarinet, horn, trumpet, violin),
        notes_by_instrument={
            "Flute": [_note(60, 0.0, 1.0, instrument_spec=flute)],
            "Clarinet": [_note(60, 0.0, 1.0, instrument_spec=clarinet)],
            "Horn": [_note(60, 0.0, 1.0, instrument_spec=horn)],
            "Trumpet": [_note(60, 0.0, 1.0, instrument_spec=trumpet)],
            "Violin I": [_note(60, 0.0, 1.0, instrument_spec=violin)],
        },
        tempo_bpm=120.0,
        time_signature=(4, 4),
        key_signature="C major",
        concert_key="C major",
    )
    output = export_musicxml(result, tmp_path / "written_keys.musicxml", pitch_mode="written")
    root = _musicxml_root(output)

    expected = {
        "Flute": (0, None),
        "Clarinet": (2, -2),
        "Horn": (1, -7),
        "Trumpet": (2, -2),
        "Violin I": (0, None),
    }
    for part_name, (fifths, chromatic) in expected.items():
        measure = _first_part_measure(root, part_name)
        assert _first_key_fifths(measure) == fifths
        assert _first_note_pitch(measure) == ("D4" if part_name in {"Clarinet", "Trumpet"} else "G4" if part_name == "Horn" else "C4")
        if chromatic is None:
            assert _first_transpose_chromatic(measure) is None
        else:
            assert _first_transpose_chromatic(measure) == chromatic
