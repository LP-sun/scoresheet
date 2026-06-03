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
```
