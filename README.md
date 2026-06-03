# scoresheet

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
