"""🎛 MIDI on every platform: the byte parser, name de-duplication, and the
CoreMIDI and ALSA decoders on hand-built buffers — neither system library is
needed (nor loaded) to run these."""
import ctypes
import struct
import sys
import unittest

from shared.controllers import midi_alsa, midi_coremidi, midi_input
from shared.controllers.midi_input import MidiStreamParser, unique_names


class StreamParserTest(unittest.TestCase):
    def test_messages_and_running_status(self):
        p = MidiStreamParser()
        self.assertEqual(p.feed(bytes([0xB0, 41, 127, 41, 0])),
                         [(0xB0, 41, 127), (0xB0, 41, 0)])
        self.assertEqual(p.feed(bytes([44, 127])), [(0xB0, 44, 127)])   # across feeds

    def test_a_message_split_over_two_feeds(self):
        p = MidiStreamParser()
        self.assertEqual(p.feed(bytes([0x91, 60])), [])
        self.assertEqual(p.feed(bytes([100])), [(0x91, 60, 100)])

    def test_real_time_bytes_inside_a_message_are_skipped(self):
        p = MidiStreamParser()
        self.assertEqual(p.feed(bytes([0xB0, 0xF8, 7, 0xFE, 64])), [(0xB0, 7, 64)])

    def test_sysex_is_dropped_and_cancels_running_status(self):
        p = MidiStreamParser()
        self.assertEqual(p.feed(bytes([0xB0, 1, 2, 0xF0, 0x42, 0x40, 0xF7, 3, 4])),
                         [(0xB0, 1, 2)])
        self.assertEqual(p.feed(bytes([0xE0, 0, 64])), [(0xE0, 0, 64)])

    def test_one_data_byte_messages(self):
        p = MidiStreamParser()
        self.assertEqual(p.feed(bytes([0xC2, 5, 6])), [(0xC2, 5, 0), (0xC2, 6, 0)])


class UniqueNamesTest(unittest.TestCase):
    def test_repeats_are_numbered(self):
        self.assertEqual(unique_names(["nano", "Traktor", "nano", "nano"]),
                         ["nano", "Traktor", "nano #2", "nano #3"])


def _packet_list(packets, aligned):
    """A MIDIPacketList as CoreMIDI lays it out (pack 4)."""
    raw = bytearray(struct.pack("=I", len(packets)))
    for data in packets:
        raw += struct.pack("=QH", 0, len(data)) + data
        if aligned:
            raw += bytes(-len(raw) % 4)
    return ctypes.create_string_buffer(bytes(raw) + bytes(8))


class CoreMidiPacketTest(unittest.TestCase):
    PACKETS = [bytes([0xB0, 41, 127]), bytes([0x90, 60]), bytes([0xE0, 0, 64, 1, 2])]

    def test_intel_layout(self):
        buf = _packet_list(self.PACKETS, aligned=False)
        self.assertEqual(midi_coremidi.packet_list_bytes(ctypes.addressof(buf), False),
                         self.PACKETS)

    def test_arm_layout_rounds_each_packet_up_to_4(self):
        buf = _packet_list(self.PACKETS, aligned=True)
        self.assertEqual(midi_coremidi.packet_list_bytes(ctypes.addressof(buf), True),
                         self.PACKETS)

    def test_coremidi_is_absent_off_macos(self):
        if sys.platform == "darwin":
            self.skipTest("macOS has CoreMIDI")
        self.assertEqual(midi_coremidi.list_inputs(), [])
        with self.assertRaises(OSError):
            midi_coremidi.MidiInput("nanoKONTROL2", print)


def _event(kind, ch, *, note=0, vel=0, param=0, value=0):
    """A 28-byte snd_seq_event_t."""
    head = bytes([kind, 0, 0, 0]) + bytes(8) + bytes([20, 0, 128, 0])
    if kind in (6, 7):
        data = bytes([ch, note, vel, 0]) + bytes(8)
    else:
        data = bytes([ch, 0, 0, 0]) + struct.pack("=Ii", param, value)
    return head + data


class AlsaEventTest(unittest.TestCase):
    def test_notes(self):
        self.assertEqual(midi_alsa.event_message(_event(6, 2, note=60, vel=100)),
                         (0x92, 60, 100))
        self.assertEqual(midi_alsa.event_message(_event(7, 0, note=60)), (0x80, 60, 0))

    def test_controller(self):
        self.assertEqual(midi_alsa.event_message(_event(10, 0, param=41, value=127)),
                         (0xB0, 41, 127))

    def test_pitch_bend_is_centred_on_8192(self):
        self.assertEqual(midi_alsa.event_message(_event(13, 1, value=0)), (0xE1, 0, 64))
        self.assertEqual(midi_alsa.event_message(_event(13, 1, value=-8192)), (0xE1, 0, 0))
        self.assertEqual(midi_alsa.event_message(_event(13, 1, value=8191)),
                         (0xE1, 127, 127))

    def test_other_events_are_ignored(self):
        self.assertIsNone(midi_alsa.event_message(_event(11, 0, value=5)))   # program
        self.assertIsNone(midi_alsa.event_message(_event(66, 0)))           # port subscribed


class DispatchTest(unittest.TestCase):
    def test_this_platform_gets_its_backend(self):
        backend = {"win32": "shared.controllers.midi_winmm", "darwin": "shared.controllers.midi_coremidi"}.get(
            sys.platform, "shared.controllers.midi_alsa")
        self.assertEqual(midi_input.MidiInput.__module__, backend)
        self.assertEqual(midi_input.list_inputs.__module__, backend)


if __name__ == "__main__":
    unittest.main()
