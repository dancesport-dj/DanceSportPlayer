#!/usr/bin/env python3
"""A player's QMediaPlayer and QAudioOutput no longer need the GIL to be disconnected.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_media_disconnect_prime -v

When Qt's FFmpeg backend drops its audio renderer, the renderer's ~QObject (on
its own thread, holding a signal-slot mutex) calls disconnectNotify on the
QAudioOutput it listened to. That object was made in Python, so PySide asks
Python for an override first and waits for the GIL - while the main thread,
holding the GIL in a stop or seek, waits for that same mutex. The click tests
hung there for good, now and then.

PySide remembers per object that there is no override, and then never takes
the GIL for it again. prime_disconnect_notify makes it look once, on the main
thread. A class-level override added afterwards shows whether it still asks.
"""
import unittest

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from shared.audio.playback import prime_disconnect_notify
from tests.qt_test_support import qapp


def _noop():
    pass


def _disconnect_one(obj):
    obj.destroyed.connect(_noop)
    obj.destroyed.disconnect(_noop)


class PrimeDisconnectNotifyTest(unittest.TestCase):

    def setUp(self):
        qapp()

        class Player(QMediaPlayer):
            pass

        class Out(QAudioOutput):
            pass
        self.player, self.out = Player(), Out()
        self.addCleanup(self.player.deleteLater)
        self.addCleanup(self.out.deleteLater)
        self.asked = []

    def _override_now(self):
        for obj in (self.player, self.out):
            type(obj).disconnectNotify = lambda me, sig: self.asked.append(type(me).__name__)

    def test_a_primed_player_and_output_no_longer_ask_python(self):
        prime_disconnect_notify(self.player, self.out)
        self._override_now()
        _disconnect_one(self.player)
        _disconnect_one(self.out)
        self.assertEqual(self.asked, [])

    def test_without_priming_they_still_ask(self):
        self._override_now()
        _disconnect_one(self.player)
        _disconnect_one(self.out)
        self.assertEqual(sorted(set(self.asked)), ["Out", "Player"])


if __name__ == "__main__":
    unittest.main()
