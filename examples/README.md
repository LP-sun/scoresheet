# Examples

Try the repository's recommended sample after installing dependencies:

```bash
scoresheet "../飞鼠进行曲.mid" --ensemble small_orchestra --format both -o ./out --parts
```

The generated MusicXML is intended to be opened in MuseScore for manual cleanup,
PDF export, or extracted parts.
After installing the package, try:

```bash
scoresheet arrange "../飞鼠进行曲.mid" --ensemble small_orchestra --output ./out/flying_mouse.musicxml
scoresheet batch-arrange .. --ensemble string_quartet --format musicxml --out-dir ./out/batch
```

Open the generated MusicXML in MuseScore for manual cleanup, PDF export, or part
extraction.
