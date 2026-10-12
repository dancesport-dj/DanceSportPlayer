"""The desk itself: decks, tables, drag & drop, dialogs, layout and
what is restored on the next start.
"""
from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
from PySide6.QtTest import QTest


def _qwait(ms: int):
    """QTest.qWait that lets go of the GIL while it waits, like the app's
    exec() does. PySide's own holds it: a Qt media thread that needs Python
    while it tears down a wrapper then waits for the GIL, while the main
    thread, still in qWait, waits for that thread — a deadlock
    (tests/gui/test_qwait_releases_gil.py)."""
    loop = QEventLoop()
    QTimer.singleShot(max(0, int(ms)), loop.quit)
    loop.exec()
    # …and what qWait does on top of a plain loop: run the deleteLater()s.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


QTest.qWait = staticmethod(_qwait)
