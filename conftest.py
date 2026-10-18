"""pytest-only setup for the unittest suite. unittest itself never reads this
file, so nothing here may be needed for a test to pass on its own.

It sits at the repo root, not in tests/: pytest imports a tests/conftest.py as
`tests.conftest`, which runs tests/__init__.py in the pytest-xdist controller.
That sets DANCEPLAYLIST_DATA_DIR there, every worker inherits it, and all of
them share one audio_features.db: click tests then stall on its locks."""
import sys

import pytest


@pytest.fixture(autouse=True)
def release_stuck_modifiers():
    """Let go of a modifier key a QTest key click left held.

    `QTest.keyClick(w, key, Ctrl | Shift)` leaves Qt's process-wide
    `keyboardModifiers()` at Shift afterwards (Ctrl alone: at Ctrl). Every later
    test in the same process then runs with that key down: `setCurrentCell`
    becomes a Shift range or a Ctrl toggle and drops the selection, and a drop
    reads Ctrl as copy. Which tests share a process changes with every
    pytest-xdist run, so the victim changes too. Seen: the presenter grouping
    test after the event-compare picker's Ctrl+Shift+→.

    A key release with no modifier sets the state back. Qt-free tests skip it.
    """
    yield
    widgets = sys.modules.get("PySide6.QtWidgets")
    if widgets is None or widgets.QApplication.instance() is None:
        return
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    if widgets.QApplication.keyboardModifiers() != Qt.KeyboardModifier.NoModifier:
        QTest.keyRelease(widgets.QWidget(), Qt.Key.Key_Shift)


def pytest_unconfigure(config):
    """Remove the temp root tests/__init__.py made in this process: an xdist
    worker ends without running atexit, which does it under unittest."""
    suite = sys.modules.get("tests")
    if suite is not None:
        suite.remove_temp_root()
