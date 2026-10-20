"""🏷 The app was DancePlaylist; what other programs see says DanceSport
Player now: the MIDI client a DJ controller tool lists, and the Server header
of the phone remote and the guest page.

Run:  py -m unittest tests.app.test_new_name_off_screen -v
"""
import unittest
from unittest import mock

from shared.controllers import midi_alsa, midi_coremidi
from shared.remote import guest_server, remote_server


class MidiClientNameTest(unittest.TestCase):
    def test_alsa(self):
        lib = mock.MagicMock()
        lib.snd_seq_open.return_value = 0
        with mock.patch.object(midi_alsa, "_load", return_value=lib):
            midi_alsa._open()
        self.assertEqual(lib.snd_seq_set_client_name.call_args[0][1],
                         b"DanceSport Player")

    def test_coremidi(self):
        midi, cf = mock.MagicMock(), mock.MagicMock()
        midi.MIDIClientCreate.return_value = 0
        with mock.patch.object(midi_coremidi, "_load", return_value=(midi, cf)), \
                mock.patch.object(midi_coremidi, "_client", None):
            midi_coremidi._client_ref()
        self.assertEqual(cf.CFStringCreateWithCString.call_args[0][1],
                         b"DanceSport Player")


class ServerHeaderTest(unittest.TestCase):
    def test_remote(self):
        self.assertEqual(remote_server._Handler.server_version,
                         "DanceSportPlayerRemote")

    def test_guests(self):
        self.assertEqual(guest_server._Handler.server_version,
                         "DanceSportPlayerGuests")


if __name__ == "__main__":
    unittest.main()
