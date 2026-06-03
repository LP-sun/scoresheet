"""Piano MIDI analysis and rule-based ensemble arrangement."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Iterable, Literal

from .instrumentation import Ensemble, InstrumentSpec, get_ensemble

LayerName = Literal["melody", "bass", "harmony"]


@dataclass(frozen=True)
class NoteEvent:
    """A normalized note extracted from a MIDI/MusicXML score."""

    pitch: int
    start: float
    duration: float
    velocity: int = 64
    part_index: int = 0
    part_name: str = "Piano"
    layer: LayerName = "harmony"

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass(frozen=True)
class PianoAnalysis:
    """Result of source MIDI parsing and piano-role classification."""

    source_path: Path
    original_score: object
    notes: tuple[NoteEvent, ...]
    melody: tuple[NoteEvent, ...]
    bass: tuple[NoteEvent, ...]
    harmony: tuple[NoteEvent, ...]


@dataclass
class ArrangedScore:
    """Notes assigned to an ensemble."""

    analysis: PianoAnalysis
    ensemble: Ensemble
    assignments: dict[str, list[NoteEvent]] = field(default_factory=dict)

    @property
    def instrument_names(self) -> tuple[str, ...]:
        return tuple(i.name for i in self.ensemble.instruments)


def _require_music21():
    try:
        import music21  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "scoresheet requires music21 to read and write MIDI/MusicXML. "
            "Install it with: pip install music21"
        ) from exc
    return music21


def _volume_from_music21_note(n: object) -> int:
    volume = getattr(n, "volume", None)
    velocity = getattr(volume, "velocity", None)
    if velocity is None:
        return 64
    try:
        return max(1, min(127, int(velocity)))
    except (TypeError, ValueError):
        return 64


def _iter_music21_notes(score: object) -> Iterable[NoteEvent]:
    music21 = _require_music21()
    parts = getattr(score, "parts", [])
    source_parts = list(parts) if parts else [score]
    for part_index, part in enumerate(source_parts):
        part_name = getattr(part, "partName", None) or getattr(part, "id", None) or f"Part {part_index + 1}"
        for element in part.recurse().notes:
            start = float(element.getOffsetInHierarchy(score))
            duration = float(element.quarterLength or 0.25)
            if duration <= 0:
                duration = 0.25
            if isinstance(element, music21.chord.Chord):
                velocity = _volume_from_music21_note(element)
                for p in element.pitches:
                    yield NoteEvent(int(p.midi), start, duration, velocity, part_index, str(part_name))
            elif isinstance(element, music21.note.Note):
                yield NoteEvent(
                    int(element.pitch.midi),
                    start,
                    duration,
                    _volume_from_music21_note(element),
                    part_index,
                    str(part_name),
                )


def _onset_key(start: float, quantum: float = 1 / 24) -> int:
    return round(start / quantum)


def classify_piano_layers(notes: Iterable[NoteEvent]) -> tuple[NoteEvent, ...]:
    """Classify notes as melody, bass, or harmony using simple piano heuristics.

    The classifier groups notes by onset.  The highest salient note at an onset is
    treated as melody, the lowest low-register note is bass, and all remaining
    material becomes harmony/accompaniment.  Pitch, duration, velocity, and part
    position all influence the score so imported multi-track piano MIDIs still get
    useful separation.
    """

    note_list = sorted(notes, key=lambda n: (n.start, n.pitch, -n.duration))
    if not note_list:
        return ()

    avg_pitch = mean(n.pitch for n in note_list)
    groups: dict[int, list[NoteEvent]] = defaultdict(list)
    for n in note_list:
        groups[_onset_key(n.start)].append(n)

    classified: list[NoteEvent] = []
    for group in groups.values():
        ordered = sorted(group, key=lambda n: (n.pitch, n.velocity, n.duration))
        low = ordered[0]
        high = ordered[-1]

        bass_candidates = [n for n in ordered if n.pitch <= 52 or n.pitch <= avg_pitch - 14]
        bass = bass_candidates[0] if bass_candidates else None

        def melody_score(n: NoteEvent) -> float:
            track_bonus = 4 if n.part_index == 0 else 0
            return n.pitch * 1.4 + n.velocity * 0.25 + n.duration * 2 + track_bonus

        melody = max(ordered, key=melody_score)
        if high.pitch >= avg_pitch + 5 and melody.pitch < high.pitch:
            melody = high

        for n in ordered:
            layer: LayerName = "harmony"
            if bass is not None and n is bass and n is not melody:
                layer = "bass"
            elif n is melody or (n.pitch >= 72 and n is high):
                layer = "melody"
            classified.append(
                NoteEvent(n.pitch, n.start, n.duration, n.velocity, n.part_index, n.part_name, layer)
            )

    return tuple(sorted(classified, key=lambda n: (n.start, n.layer, n.pitch)))


def analyze_midi(path: str | Path) -> PianoAnalysis:
    """Read a MIDI file and extract melody, bass, and harmony layers."""

    music21 = _require_music21()
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    score = music21.converter.parse(str(source_path))
    notes = classify_piano_layers(_iter_music21_notes(score))
    return PianoAnalysis(
        source_path=source_path,
        original_score=score,
        notes=notes,
        melody=tuple(n for n in notes if n.layer == "melody"),
        bass=tuple(n for n in notes if n.layer == "bass"),
        harmony=tuple(n for n in notes if n.layer == "harmony"),
    )


def _nearest_instrument(note: NoteEvent, candidates: Iterable[InstrumentSpec]) -> InstrumentSpec:
    pool = tuple(candidates)
    if not pool:
        raise ValueError("No instruments available for assignment")

    def cost(spec: InstrumentSpec) -> float:
        if spec.contains(note.pitch):
            range_penalty = 0
        else:
            range_penalty = min(abs(note.pitch - spec.low_midi), abs(note.pitch - spec.high_midi)) * 8
        center_penalty = abs(note.pitch - spec.center)
        return range_penalty + center_penalty

    return min(pool, key=cost)


def _transpose_into_range(note: NoteEvent, spec: InstrumentSpec) -> NoteEvent:
    pitch = note.pitch
    while pitch < spec.low_midi:
        pitch += 12
    while pitch > spec.high_midi:
        pitch -= 12
    pitch = max(spec.low_midi, min(spec.high_midi, pitch))
    return NoteEvent(pitch, note.start, note.duration, note.velocity, note.part_index, note.part_name, note.layer)


def arrange_analysis(analysis: PianoAnalysis, ensemble: str | Ensemble) -> ArrangedScore:
    """Assign analyzed piano layers to a target ensemble."""

    target = get_ensemble(ensemble) if isinstance(ensemble, str) else ensemble
    assignments: dict[str, list[NoteEvent]] = {i.name: [] for i in target.instruments}

    melody_targets = target.melody_instruments or target.instruments[:1]
    bass_targets = target.bass_instruments or target.instruments[-1:]
    harmony_targets = target.harmony_instruments or tuple(
        i for i in target.instruments if i not in melody_targets and i not in bass_targets
    ) or target.instruments

    for note in analysis.notes:
        if note.layer == "melody":
            spec = _nearest_instrument(note, melody_targets)
        elif note.layer == "bass":
            spec = _nearest_instrument(note, bass_targets)
        else:
            spec = _nearest_instrument(note, harmony_targets)
        assignments[spec.name].append(_transpose_into_range(note, spec))

    for instrument_notes in assignments.values():
        instrument_notes.sort(key=lambda n: (n.start, n.pitch, n.duration))
    return ArrangedScore(analysis=analysis, ensemble=target, assignments=assignments)


def arrange_file(input_path: str | Path, ensemble: str | Ensemble) -> ArrangedScore:
    """Analyze ``input_path`` and arrange it for ``ensemble``."""

    return arrange_analysis(analyze_midi(input_path), ensemble)
