from pathlib import Path
from types import SimpleNamespace

import pytest

from scoresheet.arranger import NoteEvent, PianoAnalysis, arrange_analysis, classify_piano_layers
from scoresheet.exporters import infer_export_format
from scoresheet.instrumentation import get_ensemble


def test_classify_piano_layers_splits_chord_texture():
    notes = [
        NoteEvent(48, 0, 1, 60),
        NoteEvent(60, 0, 1, 55),
        NoteEvent(67, 0, 1, 58),
        NoteEvent(76, 0, 1.5, 90),
        NoteEvent(50, 1, 1, 64),
        NoteEvent(69, 1, 1, 70),
        NoteEvent(79, 1, 2, 82),
    ]

    classified = classify_piano_layers(notes)
    layers = {(n.start, n.pitch): n.layer for n in classified}

    assert layers[(0, 76)] == "melody"
    assert layers[(0, 48)] == "bass"
    assert layers[(0, 60)] == "harmony"
    assert layers[(1, 79)] == "melody"
    assert layers[(1, 50)] == "bass"


def test_arrange_string_quartet_assigns_layers_to_expected_roles():
    classified = classify_piano_layers(
        [
            NoteEvent(40, 0, 1),
            NoteEvent(60, 0, 1),
            NoteEvent(72, 0, 1),
            NoteEvent(84, 0, 1),
        ]
    )
    analysis = PianoAnalysis(
        source_path=Path("example.mid"),
        original_score=SimpleNamespace(),
        notes=classified,
        melody=tuple(n for n in classified if n.layer == "melody"),
        bass=tuple(n for n in classified if n.layer == "bass"),
        harmony=tuple(n for n in classified if n.layer == "harmony"),
    )

    arranged = arrange_analysis(analysis, "string_quartet")

    assert arranged.assignments["Violin I"]
    assert arranged.assignments["Cello"]
    assert any(arranged.assignments[name] for name in ("Violin II", "Viola"))


def test_get_ensemble_accepts_aliases():
    assert get_ensemble("quartet").name == "string_quartet"
    assert get_ensemble("symphony").name == "orchestra"


def test_infer_export_format():
    assert infer_export_format("out.mid") == "midi"
    assert infer_export_format("out.musicxml") == "musicxml"
    assert infer_export_format("unknown", "xml") == "musicxml"
    with pytest.raises(ValueError):
        infer_export_format("unknown")
