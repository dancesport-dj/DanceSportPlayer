#!/usr/bin/env python3
"""🎧 Pre-listen: a second player on an output of its own.

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_cue_player -v

With a pre-listen output chosen in ⚙ Settings → 🔊 Sound & player, a title
played from the library pane, the 🏆 pane, the Similar window or the event plan
goes to the operator's headphones while the hall's music keeps running. When
the pre-listen output is the one the music plays on, it is refused: that would
put the preview on the PA.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cue_"))

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import dancesport_gui as gui
from player.audio.cue_player import CuePlayer
from tests.player.audio.test_audio_outputs import SPEAKERS, USB34, _Desk
from tests.qt_test_support import reap_widget

_SONG = Path("C:/music/lateincd/Samba/song.mp3")


class CueDeviceTest(unittest.TestCase):
    """AudioDevice.cue_device: the pre-listen output, or None."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_none_chosen_is_none(self):
        self.assertIsNone(_Desk().device.cue_device())

    def test_a_chosen_output_is_found(self):
        desk = _Desk()
        desk.choose("cue", USB34)
        self.assertIs(desk.device.cue_device(), USB34)

    def test_the_system_default_can_be_chosen(self):
        desk = _Desk()
        desk.choose("cue", "system")
        self.assertIs(desk.device.cue_device(), SPEAKERS)

    def test_a_card_not_plugged_in_falls_back_to_the_system_default(self):
        """As its toast says: the system default until the card is back."""
        desk = _Desk()
        desk.choose("cue", USB34)
        desk.devices.outputs.remove(USB34)
        self.assertIs(desk.device.cue_device(), SPEAKERS)
        self.assertIs(desk.device.cue_device(), SPEAKERS)
        self.assertEqual(len(desk.warnings), 1)
        self.assertTrue(desk.device.missing("cue"))
        desk.devices.outputs.append(USB34)
        self.assertIs(desk.device.cue_device(), USB34)
        self.assertFalse(desk.device.missing("cue"))

    def test_the_cue_is_not_a_source_that_follows(self):
        """Nothing chosen is OFF, not "same as the music": sync never moves
        anything for it."""
        desk = _Desk()
        desk.device.sync()
        self.assertNotIn("cue", desk.device._applied)


class CuePlayerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_stop_says_so_once(self):
        cue = CuePlayer()
        seen = []
        cue.stopped.connect(lambda: seen.append(1))
        cue._path = _SONG
        cue.stop()
        cue.stop()
        self.assertIsNone(cue.path)
        self.assertEqual(seen, [1])

    def test_stop_lets_go_of_the_card(self):
        """The idle release (AudioDevice.release) leaves this player alone:
        an empty source is what frees its card. Qt's FFmpeg backend drops
        the playback engine, and with it the audio sink, on an empty
        setSource (QFFmpegMediaPlayer::setMedia, Qt 6.11.2); a stop alone
        keeps both."""
        cue = CuePlayer()
        song = Path(tempfile.mkdtemp(prefix="dp_cue_song_")) / "song.mp3"
        song.write_bytes(b"x")
        with mock.patch.object(cue._player, "play"):
            cue.play(song, cue.audio_output.device())
        self.assertFalse(cue.media_player.source().isEmpty())
        cue.stop()
        self.assertTrue(cue.media_player.source().isEmpty())

    def test_a_title_that_will_not_decode_stops(self):
        """It never reaches EndOfMedia: ▶/■ and the mini player stayed on
        "playing" and Ctrl+←/→ kept steering the dead pre-listen."""
        cue = CuePlayer()
        seen = []
        cue.stopped.connect(lambda: seen.append(1))
        cue._path = _SONG
        cue._player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.InvalidMedia)
        self.assertIsNone(cue.path)
        self.assertEqual(seen, [1])

    def test_a_player_error_stops(self):
        cue = CuePlayer()
        seen = []
        cue.stopped.connect(lambda: seen.append(1))
        cue._path = _SONG
        cue._player.errorOccurred.emit(QMediaPlayer.Error.ResourceError,
                                       "file not found")
        self.assertIsNone(cue.path)
        self.assertEqual(seen, [1])

    def test_seek_stays_inside_the_title(self):
        cue = CuePlayer()
        player = mock.Mock()
        player.duration.return_value = 60000
        cue._player = player
        for pos, delta, landed in ((10000, 30000, 40000), (10000, -30000, 0),
                                   (50000, 30000, 60000)):
            player.position.return_value = pos
            cue.seek(delta)
            player.setPosition.assert_called_with(landed)


class _Fake:
    """A QAudioDevice the window's routing compares by id."""

    def __init__(self, key):
        self._id = key

    def id(self):
        return self._id

    def isNull(self):
        return False

    def description(self):
        return self._id.decode()


class RoutingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.settings = {"app_mode": "both",
                         "audio_outputs": {"cue": {"id": "phones", "name": "Phones"}}}
        patch = mock.patch.object(gui, "load_settings",
                                  lambda *a, **kw: dict(self.settings))
        patch.start()
        self.addCleanup(patch.stop)
        # The suite's settings file is shared: a 🎧 output saved from here
        # would pre-listen in every window the later tests open.
        for target in ("player.window.main_player.save_settings",
                       "player.window.main_load.save_settings",
                       "player.window.main_presenter.save_settings",
                       "player.audio.audio_device.save_settings"):
            saver = mock.patch(target)
            saver.start()
            self.addCleanup(saver.stop)
        self.win = gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        if self.win._audio_device.cue is None:
            self.skipTest("no Qt Multimedia")
        self.win._set_play_mode(True)
        self.music = _Fake(b"pa")
        self.phones = _Fake(b"phones")
        self.addCleanup(mock.patch.stopall)
        dev = self.win._audio_device
        mock.patch.object(dev, "cue_device", lambda: self.phones).start()
        mock.patch.object(dev, "target", lambda source: self.music).start()
        # A desk with a second card, whatever this machine has.
        mock.patch.object(dev, "single_output", lambda: False).start()
        self.play = mock.patch.object(self.win._audio_device.cue, "play").start()
        self.deck = mock.patch.object(self.win, "_play_or_stop").start()

    def test_the_library_pane_pre_listens(self):
        self.win._on_lib_play(_SONG, 0)
        self.play.assert_called_once_with(_SONG, self.phones, 0)
        self.deck.assert_not_called()

    def test_a_preview_window_pre_listens(self):
        self.win._prehear(_SONG)
        self.play.assert_called_once_with(_SONG, self.phones, 0)
        self.deck.assert_not_called()

    def test_none_stops_the_pre_listen_not_the_music(self):
        with mock.patch.object(self.win._audio_device.cue, "stop") as stop:
            self.win._prehear(None)
        stop.assert_called_once()
        self.deck.assert_not_called()

    def test_the_music_output_is_refused(self):
        self.phones = self.music
        self.win._prehear(_SONG)
        self.play.assert_not_called()
        self.deck.assert_not_called()
        self.assertIn("🎧", self.win._toast_lbl.text())

    def test_a_channel_pair_of_the_music_card_pre_listens_there(self):
        """🔀 Out 3/4 of the music's card: not where the music plays (its
        Out 1/2), so the preview goes there instead of being refused."""
        self.phones = self.music
        mock.patch.object(self.win._audio_device, "pair",
                          lambda source: 1 if source == "cue" else 0).start()
        self.win._prehear(_SONG)
        self.play.assert_called_once_with(_SONG, self.music, 1)
        self.deck.assert_not_called()

    def test_the_music_pair_of_its_card_is_refused(self):
        """🔀 The music on Out 3/4 and the preview on Out 3/4 of the same
        card: that is the PA."""
        self.phones = self.music
        mock.patch.object(self.win._audio_device, "pair",
                          lambda source: 1).start()
        self.win._prehear(_SONG)
        self.play.assert_not_called()

    def test_out_1_2_of_the_card_the_music_has_out_3_4_of(self):
        self.phones = self.music
        mock.patch.object(self.win._audio_device, "pair",
                          lambda source: 1 if source == "music" else 0).start()
        self.win._prehear(_SONG)
        self.play.assert_called_once_with(_SONG, self.music, 0)

    def test_the_only_output_pre_listens_there(self):
        """One output and no other to choose: the music's own is the
        default, so the preview plays there instead of being refused."""
        self.phones = self.music
        mock.patch.object(self.win._audio_device, "single_output",
                          lambda: True).start()
        self.win._prehear(_SONG)
        self.play.assert_called_once_with(_SONG, self.music, 0)
        self.deck.assert_not_called()

    def test_a_card_not_plugged_in_pre_listens_on_the_system_default(self):
        self.phones = _Fake(b"default")
        mock.patch.object(self.win._audio_device, "missing",
                          lambda source: True).start()
        self.win._prehear(_SONG)
        self.play.assert_called_once_with(_SONG, self.phones, 0)
        self.deck.assert_not_called()

    def test_not_when_that_default_is_the_music_output(self):
        self.phones = self.music
        mock.patch.object(self.win._audio_device, "missing",
                          lambda source: True).start()
        self.win._prehear(_SONG)
        self.play.assert_not_called()
        self.deck.assert_not_called()
        self.assertEqual("🎧 The pre-listen output is not connected, and the "
                         "system default is the music's own output.",
                         self.win._toast_lbl.text())

    def test_planning_mode_pre_listens_too(self):
        """Planning while the hall's music runs on is the same desk: the
        headphones are where a preview belongs in either mode."""
        self.win._set_play_mode(False)
        self.win._prehear(_SONG)
        self.play.assert_called_once_with(_SONG, self.phones, 0)
        self.deck.assert_not_called()

    def test_leaving_playing_mode_keeps_the_pre_listen(self):
        with mock.patch.object(self.win._audio_device.cue, "stop") as stop:
            self.win._set_play_mode(False)
        stop.assert_not_called()

    def _playing(self):
        """The mocked play() takes the title as the real one does."""
        cue = self.win._audio_device.cue
        self.play.side_effect = lambda path, dev, pair=0: setattr(cue, "_path", Path(path))
        self.addCleanup(setattr, cue, "_path", None)
        return cue

    def test_the_library_pane_shows_the_pre_listen_mini_player(self):
        cue = self._playing()
        self.win._on_lib_play(_SONG, 0)
        self.assertFalse(cue.view.isHidden())
        self.assertEqual(cue.view.title(), _SONG.stem)
        self.assertTrue(self.win._preview.isHidden())

    def test_in_planning_mode_too(self):
        cue = self._playing()
        self.win._set_play_mode(False)
        self.win._on_lib_play(_SONG, 0)
        self.assertFalse(cue.view.isHidden())

    def test_no_mini_player_while_the_preview_player_is_off(self):
        cue = self._playing()
        self.win._settings["preview_player"] = False
        self.win._on_lib_play(_SONG, 0)
        self.assertTrue(cue.view.isHidden())

    def test_a_refused_pre_listen_shows_no_mini_player(self):
        cue = self._playing()
        self.phones = self.music
        self.win._on_lib_play(_SONG, 0)
        self.assertTrue(cue.view.isHidden())

    def test_its_close_stops_the_pre_listen_not_the_music(self):
        cue = self._playing()
        self.win._on_lib_play(_SONG, 0)
        with mock.patch.object(self.win, "_on_stop_btn") as music_stop:
            cue.view.closeRequested.emit()
        music_stop.assert_not_called()
        self.assertIsNone(cue.path)
        self.assertTrue(cue.view.isHidden())

    def test_its_skip_steps_the_pane_not_the_deck(self):
        cue = self._playing()
        self.win._on_lib_play(_SONG, 0)
        with mock.patch.object(self.win._lib_browser, "skip") as skip,                 mock.patch.object(self.win, "_preview_skip") as deck_skip:
            cue.view.nextRequested.emit()
        skip.assert_called_once_with(1)
        deck_skip.assert_not_called()

    def _ctrl(self, table, key):
        """Ctrl+←/→ on `table`, with the deck's and the pre-listen's seek
        watched."""
        cue = self.win._audio_device.cue
        with mock.patch.object(cue, "seek") as cue_seek, \
                mock.patch.object(self.win, "_seek") as deck_seek:
            QTest.keyClick(table, key, Qt.KeyboardModifier.ControlModifier)
        return cue_seek, deck_seek

    def test_ctrl_arrows_in_the_library_pane_seek_the_pre_listen(self):
        """Marcel: "now when i pre listen a music it is not loaded in the main
        player anymore which is fine, but i still want to be able to skip
        trhough it with key shortcuts defined"."""
        self._playing()
        self.win._on_lib_play(_SONG, 0)
        cue_seek, deck_seek = self._ctrl(self.win._lib_browser._table, Qt.Key.Key_Right)
        cue_seek.assert_called_once_with(30000)
        deck_seek.assert_not_called()

    def test_and_in_the_tournament_pane(self):
        self._playing()
        self.win._on_lib_play(_SONG, 0)
        cue_seek, deck_seek = self._ctrl(self.win._tourney_tree._table, Qt.Key.Key_Left)
        cue_seek.assert_called_once_with(-30000)
        deck_seek.assert_not_called()

    def test_with_nothing_pre_listening_they_seek_the_music_as_before(self):
        cue_seek, deck_seek = self._ctrl(self.win._lib_browser._table, Qt.Key.Key_Right)
        cue_seek.assert_not_called()
        deck_seek.assert_called_once_with(30000)

    def test_a_deck_keeps_seeking_the_music(self):
        """A deck plays the hall's music, pre-listen or not."""
        for t in self.win._deckset.all_tables:
            self.assertEqual(t._seek_cb, self.win._seek)

    def test_it_has_no_duck_button(self):
        """🔉 ducks the hall's music: nothing a headphone preview should do."""
        self.assertTrue(self.win._audio_device.cue.view._duck_btn.isHidden())

    def test_no_pre_listen_output_plays_on_the_music_output(self):
        """Marcel: "when i play a title from library i want the mini player,
        do not put it into main player"."""
        self.win._settings["audio_outputs"] = {}
        self.win._on_lib_play(_SONG, 0)
        self.play.assert_called_once_with(_SONG, self.music, 0)
        self.deck.assert_not_called()

    def test_no_pre_listen_output_plays_on_the_music_pair(self):
        self.win._settings["audio_outputs"] = {}
        mock.patch.object(self.win._audio_device, "pair",
                          lambda source: 1).start()
        self.win._on_lib_play(_SONG, 0)
        self.play.assert_called_once_with(_SONG, self.music, 1)

    def test_without_one_the_mini_player_shows_not_the_card(self):
        cue = self._playing()
        self.win._settings["audio_outputs"] = {}
        with mock.patch.object(self.win, "_show_big_now") as card:
            self.win._on_lib_play(_SONG, 0)
        card.assert_not_called()
        self.assertFalse(cue.view.isHidden())
        self.assertTrue(self.win._preview.isHidden())

    def test_without_one_in_planning_mode_too(self):
        self.win._settings["audio_outputs"] = {}
        self.win._set_play_mode(False)
        self.win._on_lib_play(_SONG, 0)
        self.play.assert_called_once_with(_SONG, self.music, 0)
        self.deck.assert_not_called()

    def test_a_deck_starting_stops_it_on_the_shared_output(self):
        """One title at a time on one pair of speakers: a deck's ▶ took
        the library's title over before, and still does."""
        cue = self._playing()
        self.win._settings["audio_outputs"] = {}
        self.win._on_lib_play(_SONG, 0)
        self.win._on_deck_play(self.win._deckset.all_tables[0])
        self.assertIsNone(cue.path)

    def test_but_not_on_its_own_output(self):
        cue = self._playing()
        self.win._on_lib_play(_SONG, 0)
        self.win._on_deck_play(self.win._deckset.all_tables[0])
        self.assertEqual(cue.path, _SONG)

    def test_the_preview_windows_still_play_on_the_deck_without_one(self):
        self.win._settings["audio_outputs"] = {}
        self.win._prehear(_SONG)
        self.play.assert_not_called()
        self.deck.assert_called_once_with(_SONG)

    def test_preview_windows_see_the_pre_listen_title(self):
        """Similar / event plan stop what THEY started: they compare against
        prehear_path(), which is the cue's title while it routes."""
        self.win._audio_device.cue._path = _SONG
        self.addCleanup(setattr, self.win._audio_device.cue, "_path", None)
        self.assertEqual(self.win.prehear_path(), _SONG)

    def test_the_live_decks_keep_their_marker(self):
        table = self.win._deckset.all_tables[0]
        with mock.patch.object(table, "on_playback_stopped") as stopped:
            self.win.release_play_markers()
        stopped.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
