"""Minimal `imp` shim for Python 3.12+ (the stdlib `imp` module was removed).

Some legacy packages — notably OpenL3 — still do `import imp` in their setup.py
purely to read a `version.py` via `imp.load_source`. This provides just enough of
the old API to let those builds run on Python 3.13. Put this directory on
PYTHONPATH and install with `--no-build-isolation` so the build picks it up.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import sys


def load_source(name, pathname, file=None):
    """Re-implementation of the removed imp.load_source()."""
    loader = importlib.machinery.SourceFileLoader(name, pathname)
    spec = importlib.util.spec_from_file_location(name, pathname, loader=loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def load_dynamic(name, pathname, file=None):
    loader = importlib.machinery.ExtensionFileLoader(name, pathname)
    spec = importlib.util.spec_from_file_location(name, pathname, loader=loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


# Constants a few callers reference.
PY_SOURCE = 1
PY_COMPILED = 2
C_EXTENSION = 3
