#!/usr/bin/env python3
"""Click-through, chapter 05: Playing.

Run:  py -m unittest tests.gui.test_click_05_playing -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/05-playing.md
"""

import csv
import unittest
from pathlib import Path
from unittest import mock

import shiboken6
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QApplication, QDialogButtonBox, QFileDialog, QMessageBox, QTabWidget

from shared.audio.playback import device_id
from shared.columns import _COL_PLAY

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, describe


class _Plug:
    """QMediaDevices with a hand on the cable: the outputs the OS lists, less
    `card` while it is pulled."""

    def __init__(self, card):
        self.card = card
        self.pulled = False

    def defaultAudioOutput(self):
        from PySide6.QtMultimedia import QMediaDevices
        return QMediaDevices.defaultAudioOutput()

    def audioOutputs(self):
        from PySide6.QtMultimedia import QMediaDevices
        return [d for d in QMediaDevices.audioOutputs()
                if not (self.pulled and device_id(d) == device_id(self.card))]


class PlayingClickTest(ClickThrough):
    """05 Playing."""

    def test_play_a_song_then_back_to_planning(self):
        with self.clicking():
            self.generate()
            self.click(self.win._mode_play_btn)
            self.play_row(self.song_rows()[0])
            self.click(self.win._mode_plan_btn)
            self.assertTrue(self.win._mode_plan_btn.isChecked())

    def test_next_title_then_stop(self):
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            table = self.win._deckset.table
            first, second = self.song_rows()[:2]
            self.play_row(first)
            self.click(self.button("Next title"))
            self.assertTrue(self.wait_until(lambda: table._current_play_row == second),
                            f"playing row {table._current_play_row}, not {second}")
            self.win._on_stop_btn()
            self.assertTrue(self.wait_until(lambda: table._current_play_row < 0),
                            "the title kept playing")

    def test_the_play_length_cuts_the_title_after_a_fade(self):
        # − / + step the length, past the last rung lies "full"; a
        # double-click types an exact one. A title fades over the last
        # seconds, stops at the length, and ⏭ Auto walks on.
        from PySide6.QtMultimedia import QMediaPlayer
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            panel = self.win._play_panel
            table = self.win._deckset.table
            for _ in range(12):
                if panel.len_plus.isEnabled():
                    self.click(panel.len_plus)
            self.assertEqual(panel.len_lbl.text(), "full")
            self.click(panel.len_minus)
            self.assertEqual(panel.len_lbl.text(), "2:30")
            QTest.mouseDClick(panel.len_lbl, Qt.MouseButton.LeftButton)
            self.type_into(panel._len_edit, "0:12")
            self.assertEqual(panel.len_lbl.text(), "0:12")
            first = self.song_rows()[0]
            self.play_row(first)
            self.assertTrue(self.wait_until(
                lambda: self.win._player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState))
            self.win._player.setPosition(int((12 - panel.fade_secs() / 2) * 1000))
            self.assertTrue(self.wait_until(lambda: 0 < self.win._mix.fade < 1),
                            "no fade before the cut")
            self.assertTrue(self.wait_until(lambda: table._current_play_row != first,
                                            ms=5000),
                            "the title played past its length")

    def test_ctrl_shift_arrows_step_through_the_titles(self):
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            table = self.win._deckset.table
            first, second = self.song_rows()[:2]
            self.play_row(first)
            mods = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
            self.key(Qt.Key.Key_Right, mods)
            self.assertTrue(self.wait_until(lambda: table._current_play_row == second))
            self.key(Qt.Key.Key_Left, mods)
            self.assertTrue(self.wait_until(lambda: table._current_play_row == first))

    def test_every_button_once_in_each_mode(self):  # overconfidence:short-test-ok - asserts in the helper
        with self.clicking() as op:
            self.generate()
            for mode in (self.win._mode_plan_btn, self.win._mode_play_btn):
                self.click(mode)
                buttons = [b for b in self.win.findChildren(QAbstractButton)
                           if b.isVisible() and b.isEnabled()]
                for op.step, b in enumerate(buttons):
                    if not self.win.isVisible():
                        self.win.show()
                    if shiboken6.isValid(b) and b.isVisible() and b.isEnabled():
                        op.note(f"click {describe(b)}")
                        self.click(b)

    def test_party_set_then_tournament_set(self):
        with self.clicking():
            self.click(self.win._mode_play_btn)
            panel = self.win._play_panel
            self.click(panel.party_btn)
            self.assertTrue(panel.party_btn.isChecked())
            self.assertFalse(panel.tournament_btn.isChecked())
            self.assertEqual(panel.play_secs(), 0, "a party plays every title in full")
            self.assertTrue(panel.auto_advance())
            self.click(panel.tournament_btn)
            self.assertTrue(panel.tournament_btn.isChecked())
            self.assertFalse(panel.party_btn.isChecked())
            self.assertEqual(panel.play_secs(), 105, "the tournament set plays 1:45")

    def test_the_auto_switch_flips_what_follows_a_title(self):
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            table = self.win._deckset.table
            switch = table._advance_btn
            self.assertTrue(switch.isVisible(), "no ⏭ Auto / ✋ Manual switch")
            before = bool(table._advance_get())
            self.click(switch)
            self.assertEqual(bool(table._advance_get()), not before)
            self.assertNotEqual(switch.text(), "")
            self.click(switch)
            self.assertEqual(bool(table._advance_get()), before)

    def test_endless_repeat_holds_the_running_title(self):
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            self.play_row(self.song_rows()[0])
            player = self.win._big_player
            repeat = self.button("Endless repeat of THIS title")
            self.click(repeat)
            self.assertTrue(player.loop_mode())
            self.click(repeat)
            self.assertFalse(player.loop_mode())

    def test_the_presenter_opens_and_esc_closes_it(self):
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            self.click(self.win._play_panel.presenter_btn)
            presenter = self.win._presenter
            self.assertIsNotNone(presenter)
            self.assertTrue(presenter.isVisible())
            QTest.keyClick(presenter, Qt.Key.Key_Escape)
            self.assertTrue(self.wait_until(lambda: self.win._presenter is None))
            self.assertFalse(self.win._play_panel.presenter_btn.isChecked())

    def test_panic_holds_the_title_and_play_resumes_it(self):
        from PySide6.QtMultimedia import QMediaPlayer
        state = QMediaPlayer.PlaybackState
        with self.clicking():
            self.generate(rounds="1")
            self.click(self.win._mode_play_btn)
            table = self.win._deckset.table
            row = self.song_rows()[0]
            self.play_row(row)
            player, card = self.win._player, self.win._big_player
            self.assertTrue(self.wait_until(
                lambda: player.playbackState() == state.PlayingState))
            self.click(card._panic_btn)
            self.assertTrue(self.wait_until(
                lambda: player.playbackState() == state.PausedState, 8000),
                "⊗ did not bring the title to a hold")
            held = player.position()
            QTest.qWait(300)
            self.assertEqual(player.position(), held, "the hold drifts")
            self.assertEqual(table._current_play_row, row, "⊗ ended or advanced the title")
            self.click(card._pause_btn)
            self.assertTrue(self.wait_until(
                lambda: player.playbackState() == state.PlayingState),
                "⏯ did not resume")
            self.assertGreaterEqual(player.position(), held)
            self.assertEqual(table._current_play_row, row)

    def test_the_music_card_pulled_mid_title_plays_on_and_comes_back(self):
        # The USB card chosen for the music comes loose while a title runs:
        # the title goes on over the system default, the desk is told once,
        # the 🔊 badge goes and 🚦 Ready? names the card. Plugged back in, the
        # music returns to it. Real outputs, so it needs two of them.
        from PySide6.QtMultimedia import QMediaDevices, QMediaPlayer
        default = device_id(QMediaDevices.defaultAudioOutput())
        cards = [d for d in QMediaDevices.audioOutputs() if device_id(d) != default]
        if not cards:
            self.skipTest("needs a second audio output next to the default")
        card = cards[0]
        win = self.win
        plug = _Plug(card)
        win._audio_device._devices = plug

        def on(dev_id):
            return device_id(win._audio_out.device()) == dev_id

        def badge():
            return win.statusBar().findChild(QAbstractButton, "soundBadge")

        def choose(dlg):
            combo = dlg._output_combos["music"]
            combo.setCurrentIndex(combo.findData(device_id(card).hex()))

        def told():
            return [c for c in toast.call_args_list if card.description() in c.args[1]]

        playing = QMediaPlayer.PlaybackState.PlayingState
        with self.clicking() as op, mock.patch.object(self.gui, "show_toast") as toast:
            self.generate(rounds="1")
            self.edit_settings(op, choose)
            self.assertTrue(self.wait_until(lambda: on(device_id(card)), 5000),
                            "the music never went onto the chosen card")
            self.assertTrue(self.wait_until(lambda: badge() is not None
                                            and badge().isVisible(), 5000))
            self.click(win._mode_play_btn)
            row = self.song_rows()[0]
            self.play_row(row)
            self.assertTrue(self.wait_until(lambda: win._player.playbackState() == playing))

            plug.pulled = True
            win._media_devices.audioOutputsChanged.emit()
            self.assertTrue(on(default), "the music stayed on the pulled card")
            self.assertFalse(badge().isVisible(), "the badge still shows the pulled card")
            self.assertEqual(win._audio_device.unplugged(), [("music", card.description())])
            self.assertEqual(len(told()), 1, toast.call_args_list)
            pos = win._player.position()
            self.assertTrue(self.wait_until(lambda: win._player.position() > pos),
                            "the title stopped with the card")
            self.assertEqual(win._deckset.table._current_play_row, row)
            win._audio_device.watch_default()
            self.assertEqual(len(told()), 1, "the next tick told the desk again")

            plug.pulled = False
            win._media_devices.audioOutputsChanged.emit()
            self.assertTrue(on(device_id(card)), "the music did not come back to the card")
            self.assertTrue(badge().isVisible())
            self.assertEqual(win._audio_device.unplugged(), [])
            self.assertEqual(win._player.playbackState(), playing)
            win._on_stop_btn()

    def test_after_a_crash_the_title_on_air_is_cued_again_from_its_start(self):
        # The app dies on the second title of the evening. The next start
        # brings the deck back from the autosave and asks once: yes cues that
        # title on its row from its start, and the first one greys again.
        from PySide6.QtMultimedia import QMediaPlayer

        from player.audio.on_air_note import NOTE
        from player.window.main_resume import EVENING
        from shared.stores import ON_AIR
        self.addCleanup(ON_AIR.remove)

        asked = []

        def yes(box):
            asked.append(box.text())
            self.click(box.button(QMessageBox.StandardButton.Yes))

        with self.clicking() as op:
            self.generate(rounds="1")
            titles = self.titles()
            self.click(self.win._mode_play_btn)
            first, second = self.song_rows()[:2]
            heard = str(self.entry_at(first).path)
            self.play_row(first)
            table = self.win._deckset.table
            self.assertTrue(self.wait_until(
                lambda: self.win._player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState))
            self.win._player.setPosition(12_000)
            self.assertTrue(self.wait_until(lambda: heard in table._played_paths, 5000),
                            "the first title never counted as heard")
            self.click(self.button("Next title"))
            self.assertTrue(self.wait_until(lambda: table._current_play_row == second))
            on_air = self.entry_at(second).path
            self.assertTrue(self.wait_until(lambda: ON_AIR.exists(), 5000) and NOTE.flush())
            self.assertTrue(EVENING.flush())

            op.answer(lambda w: isinstance(w, QMessageBox)
                      and w.windowTitle() == "Pick up after a crash?", yes)
            # The crash: the window is torn down, but neither saves on quit nor
            # takes the note away. What is on disk is what the evening wrote
            # as it went.
            with (mock.patch.object(self.gui.MainWindow, "save_on_quit"),
                  mock.patch.object(NOTE, "remove")):
                self.restart()
            self.assertTrue(self.wait_until(lambda: asked, 5000), "nothing was offered")
            self.assertIn(on_air.stem, asked[0])
            table = self.win._deckset.table
            self.assertEqual(self.titles(), titles, "the autosave lost the deck")
            self.assertTrue(self.win._is_playing_mode())
            self.assertEqual(table._current_play_row, second)
            self.assertEqual(self.win._playback.path, on_air)
            self.assertIn(heard, table._played_paths, "the first title is not grey again")
            self.assertFalse(ON_AIR.exists(), "the note is still there for the next start")
            self.click(self.win._big_player._pause_btn)
            self.assertTrue(self.wait_until(
                lambda: self.win._player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState), "⏯ did not start it")
            self.assertLess(self.win._player.position(), 5_000, "not from its start")
            self.win._on_stop_btn()

    def test_a_cartwall_pad_plays_over_the_running_title(self):
        from planner.playing import cartwall as pc
        from player.audio.cart_voices import FIRE_GAP_MS
        from player.widgets.cartwall import CartPadButton
        win = self.win
        with self.clicking():
            self.generate(rounds="1")
            self.click(win._mode_play_btn)
            if not win._cart_btn.isChecked():
                self.click(win._cart_btn)
            wall, voices = win._cartwall, win._cart_voices
            self.assertTrue(wall.isVisible(), "🎛 shows no wall")
            key = (wall.current_page(), *next(pc.cells_in_order(wall.grid())))

            def pad() -> CartPadButton:
                # Assigning a sample builds the grid anew: never keep a button.
                return wall._buttons[key]

            # ✏ on, an empty pad browses for its sample, ✏ off again.
            sample = sorted(Path(self.settings["library_dir"]).rglob("*.mp3"))[0]
            self.click(wall._edit_btn)
            with mock.patch.object(QFileDialog, "getOpenFileNames",
                                   lambda *_a, **_kw: ([str(sample)], "")):
                self.click(pad())
            self.assertEqual(Path(wall.pad_at(key).path), sample)
            self.click(wall._edit_btn)

            row = self.song_rows()[0]
            self.play_row(row)
            self.click(pad())
            self.assertTrue(self.wait_until(lambda: voices.is_playing(key)), "the pad is silent")
            self.assertEqual(win._deckset.table._current_play_row, row, "the pad stopped the title")

            pad().setFocus()
            self.key(Qt.Key.Key_Escape, widget=pad())
            self.assertTrue(self.wait_until(lambda: not voices.is_playing(key)),
                            "Esc left the pad running")
            QTest.qWait(FIRE_GAP_MS + 50)    # two fires inside it are one tap
            self.key(Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier, widget=win)
            self.assertTrue(self.wait_until(lambda: voices.is_playing(key)),
                            "Ctrl+1 did not fire the first pad")
            self.click(pad())
            self.assertTrue(self.wait_until(lambda: not voices.is_playing(key)),
                            "a second tap left the pad running")
            self.assertEqual(win._deckset.table._current_play_row, row)

    def test_a_background_pad_dips_under_the_first_title(self):
        """🎶 The first deck is wired at start-up, not by a crossfade swap —
        the bed has to hear that one too."""
        win = self.win
        with self.clicking():
            self.generate(rounds="1")
            self.click(win._mode_play_btn)
            voices = win._cart_voices
            self.play_row(self.song_rows()[0])
            self.assertTrue(self.wait_until(lambda: voices._bg_target == 0.0),
                            "the running title left background pads up")
            win._on_stop_btn()
            self.assertTrue(self.wait_until(lambda: voices._bg_hold.isActive()
                                            or voices._bg_target == 1.0),
                            "⏹ never lets background pads back up")

    def test_a_paso_doble_stops_on_the_highlight_marked_by_hand(self):
        from PySide6.QtMultimedia import QMediaPlayer
        state = QMediaPlayer.PlaybackState
        win, panel = self.win, self.win._play_panel
        with self.clicking():
            self.generate(rounds="1")
            self.click(win._mode_play_btn)
            self.assertTrue(panel.pd_highlight_stop(), "🐂 is off out of the box")
            table, player, card = win._deckset.table, win._player, win._big_player
            row = next(r for r in self.song_rows() if self.entry_at(r).dance == "PD")
            path = self.entry_at(row).path
            self.addCleanup(lambda: (win._library.cache.clear_pd_highlights(path),
                                     win._library.cache.save()))
            self.play_row(row)
            self.assertTrue(self.wait_until(
                lambda: player.playbackState() == state.PlayingState))

            # ✏️ holds the music and suspends the stop; scrub to the crash, 🎯.
            self.click(panel.pd_edit_btn)
            self.assertTrue(self.wait_until(
                lambda: player.playbackState() == state.PausedState),
                "✏️ Edit highlights left the music running")
            self.assertIsNone(win._pd_stop_at, "the stop is armed while editing")
            player.setPosition(6000)
            self.assertTrue(self.wait_until(lambda: abs(player.position() - 6000) < 100))
            self.click(panel.pd_learn_btn)
            [mark] = win._pd_highlights[str(path)]
            self.assertAlmostEqual(mark, 6.0, delta=0.1)
            self.assertTrue(win._library.cache.is_pd_manual(path))

            # ✔ arms the stop, and the first time it comes the music waits on it.
            self.click(panel.pd_edit_btn)
            self.assertEqual(win._pd_stop_at, mark)
            player.setPosition(4000)
            self.click(card._pause_btn)
            self.assertTrue(self.wait_until(
                lambda: player.playbackState() == state.PlayingState))
            self.assertTrue(self.wait_until(
                lambda: player.playbackState() == state.PausedState, 6000),
                "the stop did not hold the music to be checked")
            self.assertGreaterEqual(player.position(), 5800)
            self.assertEqual(table._current_play_row, row)

            # From here on the highlight ends the Paso Doble.
            self.click(card._pause_btn)
            self.assertTrue(self.wait_until(lambda: win._playback.path != path, 3000),
                            "the Paso Doble ran on past its highlight")

    def cha_cha_row(self) -> int:
        """The Cha Cha: its clip is named after its code, as not every
        dance's is (the Samba's "SA" speaks SB.mp3)."""
        return next(r for r in self.song_rows() if self.entry_at(r).dance == "CC")

    def voice(self, secs: float = 0.6) -> list[list[str]]:
        """🔈 The recorded announcements, played to nobody: each call notes
        the clips it would play, in order, and speaks for `secs`."""
        ann, said = self.win._announcer, []

        def play_clips(clips):
            said.append([c.stem for c in clips])
            ann._set_speaking(True)
            QTimer.singleShot(int(secs * 1000), lambda: ann._set_speaking(False))
            return True
        p = mock.patch.object(ann, "_play_clips", play_clips)
        p.start()
        self.addCleanup(p.stop)
        return said

    def test_the_dance_is_named_over_its_first_bars(self):
        from PySide6.QtMultimedia import QMediaPlayer
        playing = QMediaPlayer.PlaybackState.PlayingState
        win, panel = self.win, self.win._play_panel
        said = self.voice()
        with self.clicking():
            self.generate(rounds="1")
            self.click(win._mode_play_btn)
            self.assertFalse(panel.pause_check.isChecked())
            self.click(panel.announce_check)
            self.assertFalse(panel.announce_wait())
            self.play_row(self.cha_cha_row())
            self.assertTrue(self.wait_until(lambda: said), "the title started uncalled")
            # The bare dance, not "Nächster Tanz: …": it is starting now.
            self.assertEqual(said, [["CC"]])
            self.assertTrue(self.wait_until(lambda: win._player.playbackState() == playing))
            self.assertLess(win._mix.duck_target, 1.0, "the music is not ducked under the voice")
            self.assertTrue(self.wait_until(lambda: win._mix.duck_target == 1.0),
                            "the music stays down after the call")

    def test_before_the_music_starts_the_title_waits_for_the_call(self):
        from PySide6.QtMultimedia import QMediaPlayer
        playing = QMediaPlayer.PlaybackState.PlayingState
        win, panel = self.win, self.win._play_panel
        said = self.voice(secs=0.8)
        with self.clicking() as op:
            self.generate(rounds="1")

            # ⚙ Settings → 🔊 Sound & player: the dance is named before the music.
            def wait_first(dlg):
                bar = dlg.findChild(QTabWidget).tabBar()
                sound = next(i for i in range(bar.count()) if "Sound" in bar.tabText(i))
                QTest.mouseClick(bar, Qt.MouseButton.LeftButton,
                                 Qt.KeyboardModifier.NoModifier, bar.tabRect(sound).center())
                self.click(dlg._lead_wait_radio)
                self.click(dlg.findChild(QDialogButtonBox).button(
                    QDialogButtonBox.StandardButton.Ok))
            op.answer(self.titled("⚙  Settings"), wait_first)
            self.click(win._cfg.settings_btn)
            self.assertTrue(self.wait_until(lambda: not op.script), op.script)

            self.click(win._mode_play_btn)
            self.click(panel.announce_check)
            self.assertTrue(panel.announce_wait())
            self.play_row(self.cha_cha_row())
            self.assertTrue(self.wait_until(lambda: said), "the title started uncalled")
            self.assertEqual(said, [["CC"]])
            while win._announcer.speaking:
                self.assertNotEqual(win._player.playbackState(), playing,
                                    "the music came in under the call")
                QTest.qWait(10)
            self.assertTrue(self.wait_until(lambda: win._player.playbackState() == playing),
                            "the music never followed the call")

    def test_the_pause_calls_the_next_dance_before_it_starts(self):
        from PySide6.QtMultimedia import QMediaPlayer
        playing = QMediaPlayer.PlaybackState.PlayingState
        win, panel = self.win, self.win._play_panel
        said = self.voice(secs=0.5)
        with self.clicking():
            self.generate(rounds="1")
            self.click(win._mode_play_btn)
            self.click(panel.announce_check)
            # The lead is opt-in (announce_lead, off by default); this test wants it said.
            panel.set_announce_style(panel.announce_voice(), panel.announce_heat(),
                                     panel.announce_wait(), lead=True)
            self.click(panel.pause_check)
            panel.pause_spin.setValue(2)
            rows = self.song_rows()
            cha_cha = self.cha_cha_row()
            before = rows[rows.index(cha_cha) - 1]
            self.play_row(before)
            self.assertTrue(self.wait_until(lambda: win._player.playbackState() == playing))
            self.assertEqual(said, [], "a start with a pause ahead was called over the music")
            self.click(win._big_player._topause_btn)
            self.assertTrue(self.wait_until(lambda: said), "the pause called nothing")
            self.assertEqual(said, [["next_dance", "CC"]])
            self.assertTrue(self.wait_until(
                lambda: win._deckset.table._current_play_row == cha_cha, 8000),
                "the next title never came")
            self.assertFalse(win._announcer.speaking, "the title came in over the call")

    def test_played_titles_lists_both_plays_in_order_and_saves_them(self):
        from PySide6.QtMultimedia import QMediaPlayer
        state = QMediaPlayer.PlaybackState
        win = self.win
        report = self.out / "played.csv"
        seen, left = [], []
        with self.clicking() as op:
            self.generate(rounds="1")
            self.click(win._mode_play_btn)
            first, second = self.song_rows()[:2]
            # Scrubbed past the 10 s a title has to run to count as heard; the
            # first one further, so the two starts lie seconds apart.
            for row, at_ms in ((first, 12000), (second, 10500)):
                path = Path(self.entry_at(row).path)
                self.play_row(row)
                self.assertTrue(self.wait_until(
                    lambda: win._playback.path == path
                    and win._player.playbackState() == state.PlayingState))
                win._player.setPosition(at_ms)
                self.assertTrue(self.wait_until(lambda: win._played_marked),
                                f"row {row} was never logged")
            self.click_cell(win._deckset.table, second, _COL_PLAY)     # ⏸ before its end
            self.assertTrue(self.wait_until(
                lambda: win._player.playbackState() == state.PausedState))

            def look(dlg):
                table = dlg.plays_table
                seen.extend(table.item(r, 2).text() for r in range(table.rowCount()))
                with mock.patch.object(QFileDialog, "getSaveFileName",
                                       lambda *_a, **_kw: (str(report), "")):
                    self.click(dlg.save_btn)
                self.click(dlg.delete_btn)
                left.append(dlg.evening_list.count())
                dlg.reject()
            op.pick("📜  Played titles…")
            op.answer(self.titled("📜 Played titles"), look)
            self.click(win._help_btn)
            self.assertTrue(self.wait_until(lambda: not op.script), op.script)
        titles = [self.entry_at(r).title for r in (first, second)]
        # The evening holds what the earlier scenarios of this run played too.
        self.assertEqual(seen[-2:], titles)
        rows = list(csv.reader(report.read_text(encoding="utf-8-sig").splitlines(),
                               delimiter=";"))
        self.assertEqual(rows[0][3], "Title")
        self.assertEqual([r[3] for r in rows[1:]], seen)
        self.assertEqual(left, [0], "🗑 left the evening in the log")

    def test_the_preview_player_closes_with_ctrl_w_and_ctrl_x(self):
        from PySide6.QtMultimedia import QMediaPlayer
        state = QMediaPlayer.PlaybackState
        win = self.win
        # 📚 plays on the 🎧 pre-listen player and its own mini player, never
        # the main one (474ae96).
        cue = win._cue_player()
        preview, player = cue.view, cue.media_player
        lib = win._lib_browser._table
        win.show()
        win.activateWindow()
        self.assertTrue(self.wait_until(lambda: QApplication.activeWindow() is win),
                        "the window never became active")
        with self.clicking():
            self.assertTrue(win._lib_btn.isChecked(), "📚 is hidden out of the box")
            self.assertGreater(lib.rowCount(), 1)
            # ▶ in a row, then Space on the selected one: each opens the mini
            # player; Ctrl+W, then Ctrl+X close it and stop the music.
            for start, key in ((lambda: self.click_cell(lib, 0, 0), Qt.Key.Key_W),
                               (lambda: (lib.selectRow(1),
                                         self.key(Qt.Key.Key_Space, widget=lib)),
                                Qt.Key.Key_X)):
                start()
                self.assertTrue(self.wait_until(
                    lambda: preview.isVisible()
                    and player.playbackState() == state.PlayingState),
                    "the preview did not open playing")
                self.key(key, Qt.KeyboardModifier.ControlModifier, widget=lib)
                self.assertTrue(self.wait_until(lambda: not preview.isVisible()),
                                f"Ctrl+{key.name[-1]} left the mini player open")
                self.assertEqual(player.playbackState(), state.StoppedState)
            self.assertTrue(win.isVisible(), "Ctrl+W closed the app")

    def test_a_quick_second_preview_keeps_the_mini_player(self):
        """A second ▶ right after the first moves the pre-listen to the
        second title, and its mini player stays open for it."""
        from PySide6.QtMultimedia import QMediaPlayer
        win = self.win
        cue = win._cue_player()
        preview = cue.view
        lib = win._lib_browser._table
        second = lib.item(1, 0).data(Qt.ItemDataRole.UserRole)
        win.show()
        with self.clicking():
            self.click_cell(lib, 0, 0)
            self.click_cell(lib, 1, 0)
            self.assertTrue(self.wait_until(
                lambda: cue.path == Path(second)
                and cue.media_player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState),
                "the second title did not start")
            QTest.qWait(300)
            self.assertTrue(preview.isVisible(),
                            "the mini player vanished under the second title")
            self.assertEqual(preview.title(), Path(second).stem)
            self.assertIsNone(win._playback.path, "📚 reached the main player")
            cue.stop()


if __name__ == "__main__":
    unittest.main()
