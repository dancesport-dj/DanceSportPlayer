"""pytest-only setup for the unittest suite. unittest itself never reads this
file, so nothing here may be needed for a test to pass on its own.

It sits at the repo root, not in tests/: pytest imports a tests/conftest.py as
`tests.conftest`, which runs tests/__init__.py in the pytest-xdist controller.
That sets DANCEPLAYLIST_DATA_DIR there, every worker inherits it, and all of
them share one audio_features.db: click tests then stall on its locks."""
import os
import sys

import pytest

# 🧪 Tests that fail under load and pass alone (11-11 and 11-12 reviews, T2).
# They are marked `flaky`: CI runs `-m "not flaky"` as the gate and `-m flaky`
# in a step of its own that may fail. Off the list once one is fixed;
# tests/app/test_flaky_quarantine.py catches a renamed entry.
FLAKY = (
    "tests/gui/window/test_crash_resume.py::CrashResumeTest"
    "::test_a_greyed_title_writes_the_evening_down",
    "tests/planner/music/test_scan_chunked_commits.py::ScanChunkedCommitsTest"
    "::test_writes_run_in_a_few_transactions",
    "tests/gui/test_background_analysis.py::FinishTest"
    "::test_stopping_ends_the_run_and_applies_nothing",
    "tests/shared/remote/test_remote_server.py::ServerTest::test_unknown_paths_are_404",
    "tests/shared/remote/test_remote_server.py::EventTest"
    "::test_a_phone_that_only_sends_commands_is_logged_in_too",
    "tests/gui/test_click_05_playing.py::PlayingClickTest"
    "::test_the_pause_calls_the_next_dance_before_it_starts",
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "flaky: fails under load, passes alone; CI runs it apart (conftest.FLAKY)")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.nodeid in FLAKY:
            item.add_marker(pytest.mark.flaky)


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
    worker ends without running atexit, which does it under unittest.

    Not under HypoFuzz (tools/dev/hypofuzz_run.py sets the variable): it
    collects with a pytest run of its own and then runs the tests in the same
    process, which would find TEMP gone. The runner removes the temp folder
    of the whole run. Not "hypofuzz" in sys.modules: Hypothesis loads it as a
    plugin in every run once it is installed."""
    suite = sys.modules.get("tests")
    if suite is not None and not os.environ.get("DANCEPLAYLIST_HYPOFUZZ"):
        suite.remove_temp_root()
