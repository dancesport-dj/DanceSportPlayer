"""🆘 The crash note's trip to disk, away from the music.

A JsonStore write syncs the file to disk and waits out a virus scanner's lock
on it for up to ¾ s (planner.config._replace). On the GUI thread that would
hold up the tick and the fade ramps right as a title starts, so the note goes
through a thread of its own at the lowest priority — lowest, not idle: the
thread takes the Python lock for a moment too (see lower_thread_priority).
"""
import threading

from planner.system_info import lower_thread_priority
from shared.stores import ON_AIR


class OnAirNote:
    """Writes and removes the crash note in the background. Only the last
    request counts: one still waiting is replaced by the next write or a
    remove, since only what is on disk at a crash matters."""

    def __init__(self, store=ON_AIR):
        self._store = store
        self._cond = threading.Condition()
        self._op = None        # ("write", note) | ("remove", None) waiting
        self._busy = False     # one being carried out
        self._thread = None

    def write(self, note: dict):
        self._post(("write", note))

    def remove(self):
        self._post(("remove", None))

    def flush(self, timeout: float = 2.0) -> bool:
        """Wait until every request is on disk — for a clean quit. False if
        the disk took longer than `timeout`."""
        with self._cond:
            return self._cond.wait_for(lambda: self._op is None and not self._busy,
                                       timeout)

    def _post(self, op):
        with self._cond:
            self._op = op
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="on-air note",
                                                daemon=True)
                self._thread.start()
            self._cond.notify_all()

    def _run(self):
        lower_thread_priority()
        while True:
            with self._cond:
                self._cond.wait_for(lambda: self._op is not None)
                op, self._op = self._op, None
                if op is None:      # wait_for saw one; for the type checker
                    continue
                kind, note = op
                self._busy = True
            if kind == "write":
                self._store.write(note)
            else:
                self._store.remove()
            with self._cond:
                self._busy = False
                self._cond.notify_all()


NOTE = OnAirNote()
