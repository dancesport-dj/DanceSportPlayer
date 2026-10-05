"""🪟 The taskbar mini player: what the buttons are and what a click means.

The shell itself is not here — player.taskbar_win32 is replaced by a recorder, so
every one of these runs on any platform and without a taskbar.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_taskbar_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from player import taskbar as tb  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402

_app = QApplication.instance() or QApplication([])

_S_OK = 0
_E_INVALIDARG = -2147024809


class _FakeShell:
    """Stands in for player.taskbar_win32 and writes down everything asked of it."""

    def __init__(self, *, creates=True, adds=True):
        self._creates = creates
        self._adds = adds
        self.buttons = None
        self.updates = []
        self.destroyed = []
        self.released = False
        self.next_icon = 100
        self.tooltip = None
        self.tooltips = 0

    def small_icon_px(self):
        return 16

    def button_created_message(self):
        return 0xC123

    def msg_fields(self, message):
        return message

    def create(self):
        return 0xABCD if self._creates else None

    def release(self, _tb):
        self.released = True

    def hicon_from_argb(self, _pixels, _w, _h):
        self.next_icon += 1
        return self.next_icon

    def destroy_icon(self, icon):
        self.destroyed.append(icon)

    def add_buttons(self, _tb, _hwnd, buttons):
        if not self._adds:
            return _E_INVALIDARG
        self.buttons = list(buttons)
        return _S_OK

    def update_buttons(self, _tb, _hwnd, buttons):
        self.updates.append(list(buttons))
        return _S_OK

    def set_thumbnail_tooltip(self, _tb, _hwnd, text):
        self.tooltip = text
        self.tooltips += 1
        return _S_OK


class _Recorded:
    """A TaskbarPlayer attached to a real window but a fake shell."""

    def __init__(self, **kw):
        self.shell = _FakeShell(**kw)
        self.window = QWidget()
        self._orig = tb.load_win32
        tb.load_win32 = lambda: self.shell

    def __enter__(self):
        self.player = tb.TaskbarPlayer()
        self.player.attach(self.window)
        return self

    def __exit__(self, *_exc):
        tb.load_win32 = self._orig
        self.player.shutdown()
        self.window.deleteLater()
        return False

    @property
    def hwnd(self):
        return self.player._hwnd

    def taskbar_button_appears(self, hwnd=None):
        """The shell announcing it has made a taskbar button for a window."""
        return self.player.nativeEventFilter(
            b"windows_generic_MSG",
            (self.hwnd if hwnd is None else hwnd,
             self.shell.button_created_message(), 0))

    def click(self, ident, hwnd=None):
        return self.player.nativeEventFilter(
            b"windows_generic_MSG",
            (self.hwnd if hwnd is None else hwnd, 0x0111,
             (0x1800 << 16) | ident))


class DecodeClickTest(unittest.TestCase):

    def test_a_thumb_button_click_names_its_button(self):
        for ident in (tb.ID_PREV, tb.ID_PLAY, tb.ID_NEXT):
            self.assertEqual(tb.decode_click(0x0111, (0x1800 << 16) | ident),
                             ident)

    def test_a_menu_command_is_not_mistaken_for_a_button(self):
        """A plain WM_COMMAND from a menu carries the same low word — only the
        high word tells the two apart, and it must be the thing checked."""
        self.assertIsNone(tb.decode_click(0x0111, tb.ID_NEXT))

    def test_another_message_is_left_alone(self):
        self.assertIsNone(tb.decode_click(0x0100, (0x1800 << 16) | tb.ID_PLAY))

    def test_an_id_we_never_registered_is_refused(self):
        self.assertIsNone(tb.decode_click(0x0111, (0x1800 << 16) | 9))


class ButtonInstallTest(unittest.TestCase):

    def test_nothing_is_installed_before_the_shell_says_it_has_a_button(self):
        """ThumbBarAddButtons has nowhere to put them until then."""
        with _Recorded() as r:
            self.assertIsNone(r.shell.buttons)

    def test_the_three_transport_buttons_go_on(self):
        with _Recorded() as r:
            r.taskbar_button_appears()
            ids = [b[0] for b in r.shell.buttons]
            self.assertEqual(ids, [tb.ID_PREV, tb.ID_PLAY, tb.ID_NEXT])

    def test_every_button_gets_an_icon_and_a_tooltip(self):
        with _Recorded() as r:
            r.taskbar_button_appears()
            for _ident, icon, tip, enabled in r.shell.buttons:
                self.assertIsNotNone(icon)
                self.assertTrue(tip)
                self.assertTrue(enabled)

    def test_an_explorer_restart_puts_the_buttons_back(self):
        """A second button-created message for OUR window means the shell came
        back without them: install them again, on a fresh interface — the old
        one belongs to the Explorer that died — with the caption."""
        with _Recorded() as r:
            r.player.set_title("Tango")
            r.taskbar_button_appears()
            r.shell.buttons = None
            r.shell.tooltip = None
            r.taskbar_button_appears()
            self.assertIsNotNone(r.shell.buttons)
            self.assertTrue(r.shell.released, "the dead interface let go")
            self.assertEqual(r.shell.tooltip, "Tango")

    def test_a_repeat_the_shell_refuses_keeps_the_toolbar_it_has(self):
        """No restart after all — the toolbar is still there, and ⏯ must keep
        following the player."""
        with _Recorded() as r:
            r.taskbar_button_appears()
            r.shell._adds = False
            r.taskbar_button_appears()
            r.player.set_playing(True)
            self.assertEqual(len(r.shell.updates), 1)

    def test_a_shell_that_refuses_the_buttons_leaves_the_app_working(self):
        with _Recorded(adds=False) as r:
            r.taskbar_button_appears()
            r.player.set_playing(True)
            self.assertEqual(r.shell.updates, [])

    def test_a_refusal_can_still_be_retried(self):
        """A failed add did not spend the shell's one attempt, so a later
        WM_TASKBARBUTTONCREATED has to be allowed to try again."""
        with _Recorded(adds=False) as r:
            r.taskbar_button_appears()
            r.shell._adds = True
            r.taskbar_button_appears()
            self.assertIsNotNone(r.shell.buttons)

    def test_no_taskbar_at_all_is_not_an_error(self):
        with _Recorded(creates=False) as r:
            r.taskbar_button_appears()
            self.assertIsNone(r.shell.buttons)


class OtherWindowTest(unittest.TestCase):
    """The filter is installed on the whole app, so it sees every window."""

    def test_another_window_s_taskbar_button_does_not_spend_our_one_add(self):
        """The loading dialog owns the first taskbar button of the run. Adding
        our buttons then targets a main window the shell has no button for —
        accepted with S_OK and thrown away, and the real message never gets a
        second chance."""
        with _Recorded() as r:
            r.taskbar_button_appears(hwnd=r.hwnd + 0x1000)
            self.assertIsNone(r.shell.buttons)
            r.taskbar_button_appears()
            self.assertIsNotNone(r.shell.buttons)

    def test_a_click_meant_for_another_window_is_not_ours(self):
        seen = []
        with _Recorded() as r:
            r.taskbar_button_appears()
            r.player.nextClicked.connect(lambda: seen.append("next"))
            handled, _ = r.click(tb.ID_NEXT, hwnd=r.hwnd + 0x1000)
            self.assertEqual(seen, [])
            self.assertFalse(handled)


class PlayPauseGlyphTest(unittest.TestCase):

    def test_the_middle_button_shows_pause_while_playing(self):
        """It says what pressing it would do, not what is happening."""
        with _Recorded() as r:
            r.taskbar_button_appears()
            self.assertEqual(r.shell.buttons[1][2], "Play")
            r.player.set_playing(True)
            self.assertEqual(r.shell.updates[-1][1][2], "Pause")

    def test_the_glyph_actually_changes_with_the_state(self):
        with _Recorded() as r:
            r.taskbar_button_appears()
            paused_icon = r.shell.buttons[1][1]
            r.player.set_playing(True)
            self.assertNotEqual(r.shell.updates[-1][1][1], paused_icon)

    def test_the_same_state_twice_does_not_talk_to_the_shell_again(self):
        with _Recorded() as r:
            r.taskbar_button_appears()
            r.player.set_playing(True)
            r.player.set_playing(True)
            self.assertEqual(len(r.shell.updates), 1)


class ThumbnailFramingTest(unittest.TestCase):
    """What the hover preview shows. The picture itself is the shell's — a
    small photograph of the window — so the caption over it is the only part
    that is ours to write, and the title lives there."""

    def test_the_running_title_becomes_the_caption(self):
        with _Recorded() as r:
            r.taskbar_button_appears()
            r.player.set_title("Corpo E Tambor  ·  Samba")
            self.assertEqual(r.shell.tooltip, "Corpo E Tambor  ·  Samba")

    def test_a_title_set_before_the_button_exists_is_not_lost(self):
        """Playback can start while the window is still coming up."""
        with _Recorded() as r:
            r.player.set_title("Festa Solar")
            self.assertIsNone(r.shell.tooltip)
            r.taskbar_button_appears()
            self.assertEqual(r.shell.tooltip, "Festa Solar")

    def test_an_empty_title_hands_the_caption_back(self):
        with _Recorded() as r:
            r.taskbar_button_appears()
            r.player.set_title("Festa Solar")
            r.player.set_title("")
            self.assertEqual(r.shell.tooltip, "")


class CaptionTest(unittest.TestCase):
    """Which title MainWindow puts in the caption.

    The picture itself cannot be aimed at the player card — the shell keeps
    showing the whole window — so this line is the entire title on the taskbar
    and it has to be right in every playback state."""

    class _Player:
        def __init__(self, state):
            self._state = state

        def playbackState(self):
            return self._state

    def _desk(self, taskbar, name, playing=True):
        from pathlib import Path

        from PySide6.QtMultimedia import QMediaPlayer

        from player.main_player import PlayerControlMixin
        state = (QMediaPlayer.PlaybackState.PlayingState if playing
                 else QMediaPlayer.PlaybackState.PausedState)
        # __new__: _sync_taskbar_title reads four attributes and nothing else,
        # and a real MainWindow would drag the whole app in behind it.
        desk = PlayerControlMixin.__new__(PlayerControlMixin)
        desk._taskbar = taskbar
        desk._playback = PlaybackState()
        desk._playback.path = Path(rf"C:\music\{name}.mp3") if name else None
        desk._playback.dance = "SA"
        desk._player = self._Player(state)
        return desk

    def test_the_playing_title_names_itself_and_its_dance(self):
        with _Recorded() as r:
            r.taskbar_button_appears()
            self._desk(r.player, "Corpo E Tambor")._sync_taskbar_title()
            self.assertTrue(r.shell.tooltip.startswith("Corpo E Tambor"),
                            r.shell.tooltip)
            self.assertIn("Samba", r.shell.tooltip)

    def test_a_loaded_title_is_named_even_while_it_is_not_running(self):
        """'i still cant see ... the title of music playing' — hovering between
        two heats used to hand back the window's own name, which reads exactly
        like a caption that has never worked."""
        with _Recorded() as r:
            r.taskbar_button_appears()
            self._desk(r.player, "Festa Solar",
                       playing=False)._sync_taskbar_title()
            self.assertTrue(r.shell.tooltip.startswith("⏸"), r.shell.tooltip)
            self.assertIn("Festa Solar", r.shell.tooltip)

    def test_nothing_loaded_hands_the_caption_back(self):
        with _Recorded() as r:
            r.taskbar_button_appears()
            self._desk(r.player, "Festa Solar")._sync_taskbar_title()
            self._desk(r.player, None)._sync_taskbar_title()
            self.assertEqual(r.shell.tooltip, "")

    def test_the_same_title_twice_does_not_talk_to_the_shell_again(self):
        """It is pushed per song AND on every state change — play, pause and
        resume within one title must not be three shell calls."""
        with _Recorded() as r:
            r.taskbar_button_appears()
            self._desk(r.player, "Festa Solar")._sync_taskbar_title()
            self._desk(r.player, "Festa Solar")._sync_taskbar_title()
            self.assertEqual(r.shell.tooltips, 1)


class IconCacheTest(unittest.TestCase):

    def test_a_glyph_is_painted_once_and_kept(self):
        """The shell keeps the HANDLE, not the pixels — an icon rebuilt on
        every update would leak one per tick and blank the old button."""
        with _Recorded() as r:
            r.taskbar_button_appears()
            play_icon = r.shell.buttons[1][1]
            r.player.set_playing(True)
            r.player.set_playing(False)
            self.assertEqual(r.shell.updates[-1][1][1], play_icon)

    def test_shutdown_gives_every_icon_back(self):
        r = _Recorded()
        with r:
            r.taskbar_button_appears()
            r.player.set_playing(True)
            self.assertFalse(r.shell.destroyed)
        self.assertEqual(len(r.shell.destroyed), 4)   # prev, next, play, pause
        self.assertTrue(r.shell.released)


class ClickRoutingTest(unittest.TestCase):

    def _fired(self, ident):
        seen = []
        with _Recorded() as r:
            r.taskbar_button_appears()
            r.player.prevClicked.connect(lambda: seen.append("prev"))
            r.player.playPauseClicked.connect(lambda: seen.append("play"))
            r.player.nextClicked.connect(lambda: seen.append("next"))
            handled, _ = r.click(ident)
        return seen, handled

    def test_each_button_fires_its_own_signal(self):
        for ident, name in ((tb.ID_PREV, "prev"), (tb.ID_PLAY, "play"),
                            (tb.ID_NEXT, "next")):
            seen, handled = self._fired(ident)
            self.assertEqual(seen, [name])
            self.assertTrue(handled)

    def test_an_unrelated_message_is_passed_on_untouched(self):
        """Swallowing it would take the message away from Qt."""
        with _Recorded() as r:
            handled, _ = r.player.nativeEventFilter(
                b"windows_generic_MSG", (r.hwnd, 0x0200, 0))
            self.assertFalse(handled)

    def test_a_non_windows_event_type_is_ignored(self):
        with _Recorded() as r:
            handled, _ = r.player.nativeEventFilter(
                b"xcb_generic_event_t", (r.hwnd, 0x0111, 0))
            self.assertFalse(handled)


class NoShellTest(unittest.TestCase):
    """Off Windows there is no taskbar — the whole class has to fall silent."""

    def setUp(self):
        self._orig = tb.load_win32
        tb.load_win32 = lambda: None

    def tearDown(self):
        tb.load_win32 = self._orig

    def test_attaching_reports_that_it_could_not(self):
        player = tb.TaskbarPlayer()
        win = QWidget()
        self.assertFalse(player.attach(win))
        win.deleteLater()

    def test_every_call_is_a_no_op_rather_than_a_crash(self):
        player = tb.TaskbarPlayer()
        player.set_playing(True)
        player.shutdown()
        self.assertEqual(player.nativeEventFilter(b"windows_generic_MSG",
                                                  (0, 0x0111, 0)), (False, 0))


if __name__ == "__main__":
    unittest.main()
