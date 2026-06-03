from __future__ import annotations

import compileall
import importlib
from pathlib import Path


def test_package_imports() -> None:
    import scoresheet
    from scoresheet import export_musicxml, orchestrate, parse_midi
    from scoresheet.cli import main

    assert scoresheet is not None
    assert callable(parse_midi)
    assert callable(orchestrate)
    assert callable(export_musicxml)
    assert callable(main)


def test_compile_package_and_tests() -> None:
    assert compileall.compile_dir(Path("scoresheet"), quiet=1)
    assert compileall.compile_dir(Path("tests"), quiet=1)


def test_src_layout_package_removed() -> None:
    assert importlib.util.find_spec("scoresheet") is not None
    assert not Path("src/scoresheet").exists()
