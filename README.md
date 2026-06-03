# scoresheet

## Project goal

`scoresheet` is a small, rule-based arranger for turning a piano-oriented MIDI file into a playable ensemble sketch. The project keeps the pipeline intentionally explicit:

1. parse MIDI notes and metadata;
2. classify notes into coarse musical roles such as melody, bass, harmony, and rhythm;
3. assign those roles to an ensemble preset while fitting pitches into instrument ranges;
4. export a full-score MusicXML file, a MIDI realization, and optionally separate MusicXML parts.

The current repository is centered on a single canonical package at `scoresheet/`.

## Current MVP

The MVP can:

- read one `.mid` or `.midi` file with `pretty_midi`, using `mido` for metadata and fallback parsing;
- arrange pitched, non-drum notes for one supported ensemble preset;
- quantize note starts and durations to a configurable beat grid;
- octave-shift pitches into instrument sounding ranges when possible;
- export MusicXML full scores;
- export MIDI realizations;
- export individual MusicXML parts when requested.

## What it cannot do yet

`scoresheet` is not yet a full notation or engraving system. It does **not** currently recover or edit:

- phrase marks, slurs, articulations, beams, or page layout;
- sophisticated voice leading or idiomatic orchestration;
- percussion parts;
- batch arrangement commands;
- a GUI workflow.

The output should be treated as a starting score sketch for review and cleanup in notation software.

## Installation

From a checkout of this repository:

```bash
python -m pip install -e ".[dev]"
```

This installs the `scoresheet` console command and the development test dependency.

## CLI usage

Arrange one MIDI file to MusicXML:

```bash
scoresheet INPUT.mid -o output --ensemble small_orchestra --format musicxml
```

Arrange one MIDI file to both MusicXML and MIDI, also writing individual parts:

```bash
scoresheet INPUT.mid -o output --ensemble orchestra --format both --parts
```

General help:

```bash
scoresheet --help
```

### Options

- `INPUT.mid`: input `.mid` or `.midi` file.
- `-o, --output-dir`: directory for generated files. Defaults to `output`.
- `--ensemble`: one supported ensemble preset. Defaults to `small_orchestra`.
- `--format`: `musicxml`, `mid`, or `both`. Defaults to `musicxml`.
- `--parts`: also export one MusicXML file per instrument part.
- `--quantization-unit`: beat grid unit. Defaults to `0.25`.

## Supported ensembles

- `string_quartet`
- `string_ensemble`
- `wind_quintet`
- `wind_band`
- `small_orchestra`
- `orchestra`

## Recommended workflow with MuseScore

1. Run `scoresheet` on a clean piano MIDI file.
2. Open the generated `.musicxml` file in MuseScore.
3. Review register changes and warning messages printed by the CLI.
4. Clean up notation details such as ties, beams, articulations, dynamics, and page layout.
5. Edit orchestration choices manually where the heuristic assignment is not musical enough.
6. Export final parts or audio from MuseScore.

## Development / tests

Useful local checks:

```bash
python -m compileall -q scoresheet tests
python -m pytest -q
python -m pip install -e ".[dev]"
scoresheet --help
```

GitHub Actions runs the install, compileall, and pytest checks on push and pull_request events.

## Future TODO

- Add a tested batch-arrange command that reuses `parse_midi -> orchestrate -> export` without placeholder copying.
- Add richer role analysis and voice-leading heuristics.
- Add percussion support.
- Add more focused MusicXML assertions and sample fixtures.
- Keep CI coverage aligned with the MVP install/import/test baseline.
