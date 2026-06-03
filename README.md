# scoresheet

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
