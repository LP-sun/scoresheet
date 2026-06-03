from __future__ import annotations

import compileall
import importlib
from pathlib import Path


def test_package_imports() -> None:
    module = importlib.import_module("scoresheet")

    assert hasattr(module, "arrange_file")


def test_compile_src_and_tests() -> None:
    assert compileall.compile_dir(Path("src"), quiet=1)
    assert compileall.compile_dir(Path("tests"), quiet=1)
