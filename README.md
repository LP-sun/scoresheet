# scoresheet

`scoresheet` is a Python 3.11+ MVP for turning a piano-oriented MIDI file into a
rule-based ensemble arrangement and exporting it as MusicXML and, optionally,
MIDI.  The long-term project goal is to generate orchestra versions, full
scores, parts, and editable MusicXML files from `.mid` piano sheets.

## Design references

The project is inspired by the public APIs and architecture of well-known open
source music software, but it does **not** vendor or copy their implementations:

- `music21`: symbolic score objects and MusicXML export ideas.
- `pretty-midi`: MIDI note/instrument extraction and performance-time data.
- `mido`: low-level MIDI meta-message fallback for tempo, meter, and key.
- `partitura`: score/performance separation, voice separation, and pitch spelling
  concepts to improve in future versions.
- MuseScore: recommended external editor/exporter after MusicXML generation.
- Verovio and OpenSheetMusicDisplay: possible future preview backends for SVG or
  browser-based display.

MuseScore GPL code is not included.  MuseScore, Verovio, and OSMD are optional
external tools/workflows rather than hard runtime dependencies.

## Current MVP

The current pipeline can:

1. Read a `.mid`/`.midi` file with `pretty_midi`.
2. Recover tempo, time signature, and key signature where possible, with `mido`
   fallback for meta messages.
3. Quantize note starts and durations to a configurable beat grid.
4. Heuristically label notes as `melody`, `bass`, `harmony`, or `rhythm`.
5. Arrange those roles into rule-based ensembles:
   - `string_quartet`
   - `string_ensemble`
   - `wind_quintet`
   - `wind_band`
   - `small_orchestra`
   - `orchestra`
6. Check target instrument ranges and octave-shift notes into a playable range
   when possible.
7. Export a full-score MusicXML file with `music21`.
8. Optionally export a MIDI realization and one MusicXML file per part.

## What it cannot do yet

MIDI is not a complete notation format.  It often lacks slurs, phrase marks,
beam grouping, enharmonic spelling intent, voices, articulations, pedal meaning,
page layout, and part extraction decisions.  This project uses warnings and
heuristics instead of pretending that a MIDI file can be perfectly restored to a
publishable score automatically.

The MVP does **not** implement deep-learning orchestration, advanced harmonic
analysis, professional engraving, or automatic PDF generation.
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

Runtime dependencies are declared in `pyproject.toml`: `pretty_midi`, `music21`,
`mido`, and `numpy`.

## CLI usage

Module form:

```bash
python -m scoresheet "飞鼠进行曲.mid" -o output --ensemble small_orchestra --format musicxml
```

Console script form after installation:

```bash
scoresheet "飞鼠进行曲.mid" --ensemble orchestra --format both --parts -o output
```

Useful options:

```bash
scoresheet input.mid --ensemble wind_quintet --format musicxml -o output
scoresheet input.mid --ensemble string_quartet --format mid -o output
scoresheet input.mid --ensemble small_orchestra --format both --parts -o output
```

Generated files follow this pattern:

- `output/<input_stem>_<ensemble>.musicxml`
- `output/<input_stem>_<ensemble>.mid` when `--format mid` or `--format both` is used
- `output/parts/*.musicxml` when `--parts` is used
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
3. Review range warnings, voice crossings, enharmonic spelling, articulations,
   dynamics, and measure layout.
4. Use MuseScore to export PDF, MSCZ, individual parts, or manually refined MIDI.

For the repository sample recommended during development:

```bash
scoresheet "飞鼠进行曲.mid" --ensemble small_orchestra --format both --parts -o output/flying_mouse
3. Review range warnings, voice crossings, note spelling, articulations,
   dynamics, measures, and layout.
4. Export PDF, MSCZ, or cleaned parts from MuseScore if needed.

Example with the repository's recommended sample:

```bash
scoresheet arrange "飞鼠进行曲.mid" --ensemble small_orchestra --output output/flying_mouse.musicxml
```

## Development

Run tests:

```bash
pytest
```

## Next TODOs

- Add batch conversion for every MIDI file in a directory.
- Improve voice separation beyond onset/register heuristics.
- Add pitch spelling and key-aware enharmonic cleanup.
- Add measure-aware rhythm simplification and tie generation.
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
`scoresheet` is a Python project for turning MIDI piano-sheet files into score outputs such as MIDI (`.mid`) or MusicXML (`.musicxml`).

## Installation

Install the project in editable mode from the repository root:

```bash
python -m pip install -e .
```

To include the optional `partitura` dependency, install the optional extra:

```bash
python -m pip install -e ".[partitura]"
```

## Usage

After installation, use the `scoresheet` command:

```bash
scoresheet INPUT.mid OUTPUT.mid
scoresheet INPUT.mid OUTPUT.musicxml
```

The output format is inferred from the output file extension. You can also provide it explicitly:

```bash
scoresheet INPUT.mid OUTPUT --format mid
scoresheet INPUT.mid OUTPUT --format musicxml
```

### Convert MIDI to MIDI

```bash
scoresheet "飞鼠进行曲.mid" "build/飞鼠进行曲.arranged.mid"
```

### Convert MIDI to MusicXML

```bash
scoresheet "飞鼠进行曲.mid" "build/飞鼠进行曲.musicxml"
```

## Development layout

The project uses a standard `src` layout:

```text
src/scoresheet/
  __init__.py
  arranger.py
  cli.py
  exporters.py
  instrumentation.py
`scoresheet` turns a piano-oriented MIDI file into a simple ensemble arrangement
and writes either MIDI or MusicXML.

## Features

- Reads MIDI input through `music21`.
- Analyzes piano texture into melody, bass, and harmony/accompaniment layers using
  pitch range, velocity, duration, onset grouping, and source part/track position.
- Supports target ensembles:
  - `wind_band`
  - `string_orchestra`
  - `wind_quintet` (`Flute`, `Oboe`, `Clarinet`, `Bassoon`, `Horn`)
  - `string_quartet` (`Violin I`, `Violin II`, `Viola`, `Cello`)
  - `orchestra`
- Assigns melody to lead instruments, bass to low instruments, and harmony to
  mid-range/accompaniment instruments.
- Writes General MIDI programs for every target instrument.
- Preserves common score metadata such as tempo marks, time signatures, and key
  signatures when exporting through `music21`.

## Usage

```bash
python -m scoresheet arrange 飞鼠进行曲.mid --ensemble string_quartet --output out.mid
python -m scoresheet arrange 飞鼠进行曲.mid --ensemble orchestra --output out.musicxml
```

Install locally with runtime dependencies:

```bash
python -m pip install -e .
```

Then the console script is also available:

```bash
scoresheet arrange 飞鼠进行曲.mid --ensemble wind_quintet --output out.mid
```
