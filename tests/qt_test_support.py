"""Shared setup and teardown for tests that build real Qt windows.

Not named test_*.py on purpose — unittest discovery would import it as a
test module.
"""
from unittest import mock

import shiboken6
from PySide6.QtCore import QEventLoop, QThread
from PySide6.QtWidgets import QApplication


def reap_widget(w):
    """Destroy `w` now, rather than whenever an event loop next runs.

    `deleteLater()` only posts a DeferredDelete event, and a unittest run never
    spins an event loop to deliver it. So a plain `addCleanup(win.deleteLater)`
    frees nothing: every window a test builds stays alive for the whole process
    — timers, event filters and media players included — and each later test
    pays to walk the pile. Measured on test_app_mode, that took the same ten
    tests from 0.7s to 7.5s apiece and left 494 top-level widgets standing.

    Let the queue run dry first, while `w` is still whole. The grid defers a
    lot of its own work to `QTimer.singleShot(0, …)`, and a callback that fires
    after its widget is gone raises out of whatever event dispatch happens to be
    running — in the next test's module, which is a memorable way to spend an
    afternoon. Note the ordering: it is safe to drain *before* destroying
    anything and never after.

    Cancel and join the worker threads next: a test that plays a track arms a
    background SilenceWorker, and Qt aborts the whole process if a QThread is
    destroyed while its parent goes with it. MainWindow does the same on quit
    (`_stop_workers`), but a bare widget has no such teardown, so do it here
    for anything we are handed.

    Then close, so MainWindow.closeEvent stops the announcer engine and the
    cartwall voices, and destroy `w` outright.

    shiboken6.delete rather than deleteLater + a drained DeferredDelete queue:
    that queue is process-wide, so draining it also destroys every dialog other
    tests had merely queued, and their pending singleShot timers then fire on
    dead buttons. This touches nothing but `w`.
    """
    if not shiboken6.isValid(w):
        return          # a parent reaped earlier already took this one with it
    app = QApplication.instance()
    if app is not None:
        app.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
    for worker in w.findChildren(QThread):
        if not worker.isRunning():
            continue
        cancel = getattr(worker, "cancel", None)
        if callable(cancel):
            cancel()
        worker.wait(10_000)
    w.close()
    shiboken6.delete(w)


class StubLoader:
    """Stands in for LibraryLoader: connectable signals, start() only notes
    that it was asked to."""

    class _Sig:
        def connect(self, *_a, **_kw):
            pass

    def __init__(self, *_a, **_kw):
        self.status = self._Sig()
        self.finished_ok = self._Sig()
        self.error = self._Sig()
        self.started = False

    def start(self):
        self.started = True

    def isRunning(self):
        return False

    def wait(self, *_a):
        return True


def stub_window_startup(cls, settings=None):
    """For a test class that builds MainWindow: no library scan in the
    background, and `settings` in place of the settings file. Both are put back
    after the class, also when a test swapped `load_settings` again on its own.

    Returns the dancesport_gui module, imported only here so that Qt stays out
    of the test module's import."""
    import dancesport_gui
    for name, value in (("LibraryLoader", StubLoader),
                        ("load_settings",
                         lambda *_a, **_kw: dict(settings or {}))):
        patcher = mock.patch.object(dancesport_gui, name, value)
        patcher.start()
        cls.addClassCleanup(patcher.stop)
    return dancesport_gui
