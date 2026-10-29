#!/usr/bin/env python3
"""Click-through, chapter 14: Player only.

Run:  py -m unittest tests.gui.test_click_14_player_only -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/14-player-only.md
"""

import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QPointF

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, DropFrom, printable


class PlayerOnlyClickTest(ClickThrough):
    """14 Player only."""

    def test_the_player_build_opens_on_the_venue_layout_and_plays_a_list(self):
        from PySide6.QtCore import QMimeData, QUrl
        from PySide6.QtMultimedia import QMediaPlayer

        import planner.config
        from gui.dialogs import PLAYER_FIRST_START
        # The first start of DanceSport-Player, as ensure_app_mode leaves it.
        for p in (mock.patch.object(planner.config, "build_flavor", lambda: "player"),
                  mock.patch.dict(self.settings, {"app_mode": "player",
                                                  PLAYER_FIRST_START: True})):
            p.start()
            self.addCleanup(p.stop)
        self.restart()
        win = self.win
        panel, play = win._deckset.warmup_table, win._play_panel
        music = sorted(Path(self.settings["library_dir"], "LateinCD").glob("*.mp3"))[:4]
        m3u = self.out / "Samstag Party.m3u"
        m3u.write_text("\n".join(["#EXTM3U", *map(str, music)]) + "\n",
                       encoding="utf-8")
        with self.clicking():
            self.assertTrue(win.windowTitle().startswith("DanceSport Player"),
                            win.windowTitle())
            # ▶ Playing, with no 📝 / ▶ switch and no planning buttons.
            self.assertTrue(win._mode_play_btn.isChecked())
            self.assertTrue(win._mode_row_w.isHidden(), "the 📝 / ▶ switch shows")
            for b in win._planner_btns + win._player_build_hidden:
                self.assertTrue(b.isHidden(), f"{printable(b.text())} shows")
            # The venue layout: no decks, no wishlists, the Party list armed,
            # 📚 open, 🎛 closed, 🎉 the party set on.
            self.assertEqual((win._deckset.deck_count, win._wish_state), (0, 0))
            self.assertFalse(win._grid.warmup_box.isHidden(), "no Party panel")
            self.assertIn("the Party panel", win._warmup_toggle_btn.toolTip())
            self.assertTrue(win._lib_btn.isChecked(), "📚 is closed")
            self.assertFalse(win._cart_btn.isChecked(), "🎛 is open")
            self.assertTrue(play.party_btn.isChecked(), "🎉 is not lit")
            self.assertEqual(play._secs, 0, "the party set plays a cut length")
            self.assertTrue(play.advance_check.isChecked(), "no auto-advance")
            self.assertFalse(play.pause_check.isChecked(), "a pause between songs")
            self.assertTrue(play.loudness_check.isChecked(), "volume not equalized")
            # An .m3u dropped on the Party list plays from its first title.
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(m3u))])
            panel.dropEvent(DropFrom(QPointF(20, 20), mime, None))
            self.assertTrue(self.wait_until(lambda: len(self.titles(panel)) == 4),
                            f"loaded {printable(self.titles(panel))}")
            self.play_row(self.song_rows(panel)[0], panel)
            self.assertTrue(self.wait_until(
                lambda: win._player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState
                and Path(win._playback.path) == music[0]),
                f"playing {win._playback.path}")
            win._on_stop_btn()
            # ⧉ stops at four decks.
            counts = []
            for _ in range(5):
                self.click(win._dual_btn)
                counts.append(win._deckset.deck_count)
            self.assertEqual(counts, [1, 2, 4, 0, 1])


if __name__ == "__main__":
    unittest.main()
