# scoresheet

`scoresheet` is a small Python 3.11+ project for turning piano-oriented MIDI
files into simple rule-based ensemble arrangements.  It exports editable
MusicXML or MIDI so the result can be inspected and refined in notation software
such as MuseScore.

This is an MVP repair branch: the goal is a clean, installable, importable,
runnable, and testable baseline rather than a professional automatic arranger.

## What the MVP does

- Reads `.mid`/`.midi` files with `pretty_midi`, with `mido` fallback for MIDI
  metadata and malformed files.
- Classifies notes into rough `melody`, `bass`, `harmony`, and `rhythm` layers.
- Assigns layers to a selected ensemble using deterministic rules.
- Checks target instrument ranges and octave-shifts notes where possible.
- Exports an arranged score to MusicXML or MIDI through `music21`.
- Provides single-file and batch CLI workflows.

## What it does not do

MIDI does not reliably contain slurs, phrasing, notation voices, beaming,
articulation intent, enharmonic spelling, pedal meaning, or page layout.  This
project uses heuristics and warnings; it does **not** produce professional
finished orchestration or engraving automatically, and it does not use deep
learning.

## Installation

```bash
python -m pip install -e '.[dev]'
```

Runtime dependencies are declared in `pyproject.toml`: `music21`,
`pretty_midi`, `mido`, and `numpy`.  The optional `partitura` extra is reserved
for future score/performance research workflows.

## CLI usage

### Single file

Export MusicXML:

```bash
scoresheet arrange INPUT.mid --ensemble string_quartet --output out.musicxml
```

Export MIDI:

```bash
scoresheet arrange INPUT.mid --ensemble orchestra --output out.mid
```

The output format can be inferred from `.musicxml`, `.xml`, `.mxl`, `.mid`, or
`.midi`, or explicitly set with `--format`.

### Batch processing

Arrange every MIDI file in a directory for one ensemble:

```bash
scoresheet batch-arrange INPUT_DIR --ensemble orchestra --format musicxml --out-dir arranged
```

Arrange every MIDI file for every supported canonical ensemble:

```bash
scoresheet batch-arrange INPUT_DIR --all-ensembles --format mid --out-dir arranged
```

Batch output is written under `OUT_DIR/<ensemble>/<input_stem>_<ensemble>.<ext>`.

## Supported ensembles

Canonical ensemble names:

- `string_quartet`
- `string_ensemble`
- `wind_quintet`
- `wind_band`
- `small_orchestra`
- `orchestra`

Several aliases are also accepted, including `quartet`, `strings`,
`woodwind_quintet`, `winds`, `band`, `small`, `full_orchestra`, `管弦乐团`,
`弦乐四重奏`, `木管五重奏`, `管乐团`, and `弦乐团`.

## Recommended workflow

1. Generate MusicXML with `scoresheet`.
2. Open the MusicXML in MuseScore.
3. Review range warnings, voice crossings, note spelling, articulations,
   dynamics, measures, and layout.
4. Export PDF, MSCZ, or cleaned parts from MuseScore if needed.

Example with the repository's recommended sample:

```bash
scoresheet arrange "飞鼠进行曲.mid" --ensemble small_orchestra --output output/flying_mouse.musicxml
```

## Development

```bash
python -m compileall -q src tests
python -m pytest -q
```

## Future TODO

- Improve voice separation beyond simple onset/register heuristics.
- Add key-aware pitch spelling and rhythm simplification with ties.
- Add configurable orchestration presets in YAML/TOML.
- Add optional MuseScore CLI validation/export hooks.
- Add optional Verovio or OpenSheetMusicDisplay preview backends.
