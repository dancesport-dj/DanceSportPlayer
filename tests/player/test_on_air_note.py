#!/usr/bin/env python3
"""The crash note goes to disk away from the music.

Run:  py -m unittest tests.player.test_on_air_note -v

A JsonStore write syncs the file to disk and waits out a virus scanner's lock
for up to ¾ s. On the GUI thread that would hold up the tick and the fade
ramps the moment a title starts, so OnAirNote hands every write and remove to
a thread of its own at the lowest priority, and only the last request counts.
"""

import threading
import unittest
from unittest import mock

from player.audio import on_air_note
from player.audio.on_air_note import OnAirNote


class _Store:
    """A JsonStore stand-in: records each call and the thread it ran on."""

    def __init__(self, hold=None):
        self.calls = []
        self.started = threading.Event()
        self._hold = hold

    def write(self, note):
        self.calls.append(("write", note, threading.current_thread()))
        self.started.set()
        if self._hold is not None:
            self._hold.wait(5)
        return True

    def remove(self):
        self.calls.append(("remove", None, threading.current_thread()))


class OnAirNoteTest(unittest.TestCase):

    def test_the_write_runs_on_a_thread_of_its_own_at_the_lowest_priority(self):
        store = _Store()
        lowered = []
        with mock.patch.object(on_air_note, "lower_thread_priority",
                               side_effect=lambda: lowered.append(threading.current_thread())):
            note = OnAirNote(store)
            note.write({"row": 1})
            self.assertTrue(note.flush())
        (kind, data, thread), = store.calls
        self.assertEqual((kind, data), ("write", {"row": 1}))
        self.assertIsNot(thread, threading.current_thread())
        self.assertEqual(lowered, [thread])

    def test_only_the_last_request_counts(self):
        hold = threading.Event()
        store = _Store(hold)
        with mock.patch.object(on_air_note, "lower_thread_priority"):
            note = OnAirNote(store)
            note.write({"row": 1})
            self.assertTrue(store.started.wait(5))
            note.write({"row": 3})   # replaced by the remove before it ran
            note.remove()
            hold.set()
            self.assertTrue(note.flush())
        self.assertEqual([(k, d) for k, d, _ in store.calls],
                         [("write", {"row": 1}), ("remove", None)])

    def test_flush_with_nothing_asked_is_done_at_once(self):
        self.assertTrue(OnAirNote(_Store()).flush(0.1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
