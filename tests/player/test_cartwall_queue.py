"""▶ The cartwall pad queue: Ctrl+click pads into a list that plays itself.

Run:  py -m unittest tests.player.test_cartwall_queue -v

The order lives ON the pad (`CartPad.queue`, 0 = not queued), so every move,
swap, page move, turn or resize carries it along without a line of rekeying,
and clearing a pad takes it out of the queue with it.
"""
import os
import sys
import tempfile
import unittest
from typing import Any
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cart_queue_"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from planner.playing.cartwall import CartPad, Page
from player.audio import cart_voices
from player.widgets import cartwall as gc
from player.window.main_cartwall import CartwallMixin
from tests.player.test_cartwall_voices import _factory, _pad, _VoiceCase
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


def _wall(*cells) -> list[Page]:
    """One page, a pad per (row, col) named after its cell."""
    return [Page(pads={cell: CartPad(path=f"{cell[0]}{cell[1]}.mp3")
                       for cell in cells}), pc.blank_page()]


class ToggleTest(unittest.TestCase):

    def test_order_is_the_order_of_the_clicks(self):
        pages = _wall((0, 0), (0, 1), (1, 0))
        for cell in ((1, 0), (0, 0), (0, 1)):
            self.assertTrue(pc.toggle_queue(pages, 0, cell))
        self.assertEqual([c for _p, c, _pad in pc.queued(pages)],
                         [(1, 0), (0, 0), (0, 1)])
        self.assertEqual(pc.queue_ranks(pages),
                         {(0, (1, 0)): 1, (0, (0, 0)): 2, (0, (0, 1)): 3})

    def test_a_second_click_takes_it_out_and_closes_the_gap(self):
        pages = _wall((0, 0), (0, 1), (1, 0))
        for cell in ((0, 0), (0, 1), (1, 0)):
            pc.toggle_queue(pages, 0, cell)
        self.assertFalse(pc.toggle_queue(pages, 0, (0, 1)))
        self.assertEqual(pages[0].pads[(0, 1)].queue, 0)
        self.assertEqual(pc.queue_ranks(pages),
                         {(0, (0, 0)): 1, (0, (1, 0)): 2})

    def test_back_in_goes_to_the_end(self):
        pages = _wall((0, 0), (0, 1))
        pc.toggle_queue(pages, 0, (0, 0))
        pc.toggle_queue(pages, 0, (0, 1))
        pc.toggle_queue(pages, 0, (0, 0))
        pc.toggle_queue(pages, 0, (0, 0))
        self.assertEqual(pc.queue_ranks(pages),
                         {(0, (0, 1)): 1, (0, (0, 0)): 2})

    def test_an_empty_cell_is_not_queued(self):
        pages = _wall((0, 0))
        self.assertFalse(pc.toggle_queue(pages, 0, (1, 1)))
        self.assertEqual(pc.queued(pages), [])

    def test_the_queue_spans_pages(self):
        pages = _wall((0, 0))
        pages[1].pads[(0, 0)] = CartPad(path="p2.mp3")
        pc.toggle_queue(pages, 1, (0, 0))
        pc.toggle_queue(pages, 0, (0, 0))
        self.assertEqual([(p, c) for p, c, _pad in pc.queued(pages)],
                         [(1, (0, 0)), (0, (0, 0))])

    def test_a_full_volume_bed_joins_at_the_bed_volume(self):
        # Marcel: "if i have 3 backgroudn items in list queue and add a 4 it
        # doent get the 50% value" - only a 🎶 pad still at 100 % is turned down.
        pages = _wall((0, 0), (0, 1), (1, 0))
        pages[0].pads[(0, 0)].background = True
        pages[0].pads[(0, 1)].background = True
        pages[0].pads[(0, 1)].volume = 0.8
        for cell in ((0, 0), (0, 1), (1, 0)):
            pc.toggle_queue(pages, 0, cell, bed_volume=0.5)
        self.assertEqual(pages[0].pads[(0, 0)].volume, 0.5)
        self.assertEqual(pages[0].pads[(0, 1)].volume, 0.8)   # set by hand
        self.assertEqual(pages[0].pads[(1, 0)].volume, 1.0)   # not a bed

    def test_taking_a_bed_out_leaves_its_volume(self):
        pages = _wall((0, 0))
        pad = pages[0].pads[(0, 0)]
        pad.background = True
        pad.queue = 1
        self.assertFalse(pc.toggle_queue(pages, 0, (0, 0), bed_volume=0.5))
        self.assertEqual(pad.volume, 1.0)


class NextTest(unittest.TestCase):

    def setUp(self):
        self.pages = _wall((0, 0), (0, 1), (1, 0))
        for cell in ((0, 0), (0, 1), (1, 0)):
            pc.toggle_queue(self.pages, 0, cell)

    def nxt(self, cell):
        return pc.queue_next(self.pages, self.pages[0].pads[cell].queue)[:2]

    def test_the_next_one_in_click_order(self):
        self.assertEqual(self.nxt((0, 0)), (0, (0, 1)))
        self.assertEqual(self.nxt((0, 1)), (0, (1, 0)))

    def test_after_the_last_it_wraps_to_the_first(self):
        self.assertEqual(self.nxt((1, 0)), (0, (0, 0)))

    def test_a_single_queued_pad_follows_itself(self):
        pages = _wall((0, 0), (0, 1))
        pc.toggle_queue(pages, 0, (0, 1))
        pos = pages[0].pads[(0, 1)].queue
        self.assertEqual(pc.queue_next(pages, pos)[:2], (0, (0, 1)))

    def test_the_running_pad_taken_out_still_hands_on_to_its_follower(self):
        pos = self.pages[0].pads[(0, 1)].queue
        pc.toggle_queue(self.pages, 0, (0, 1))
        self.assertEqual(pc.queue_next(self.pages, pos)[:2], (0, (1, 0)))

    def test_the_running_pad_cleared_still_hands_on_to_its_follower(self):
        pos = self.pages[0].pads[(1, 0)].queue
        pc.clear_pad(self.pages, 0, (1, 0))
        self.assertEqual(pc.queue_next(self.pages, pos)[:2], (0, (0, 0)))

    def test_nothing_queued_is_none(self):
        self.assertIsNone(pc.queue_next(_wall((0, 0)), 0))


class TheQueueFollowsThePadTest(unittest.TestCase):

    def setUp(self):
        self.pages = _wall((0, 0), (0, 1), (1, 1))
        pc.toggle_queue(self.pages, 0, (0, 1))
        pc.toggle_queue(self.pages, 0, (0, 0))

    def order(self, pages=None):
        return [pad.path for _p, _c, pad in pc.queued(pages or self.pages)]

    def test_a_swap_keeps_the_order_with_the_pads(self):
        pc.move_pad(self.pages, 0, (0, 0), 0, (0, 1))
        self.assertEqual(self.order(), ["01.mp3", "00.mp3"])

    def test_a_move_to_another_page_keeps_it_queued(self):
        pc.move_to_page(self.pages, [(0, (0, 1))], 1, (2, 2))
        self.assertEqual(self.order(), ["01.mp3", "00.mp3"])
        self.assertEqual(pc.queued(self.pages)[0][0], 1)

    def test_turning_the_wall_keeps_it(self):
        _grid, pages = pc.transpose((2, 2), self.pages)
        self.assertEqual(self.order(pages), ["01.mp3", "00.mp3"])

    def test_a_cleared_pad_leaves_the_queue(self):
        pc.clear_pad(self.pages, 0, (0, 1))
        self.assertEqual(self.order(), ["00.mp3"])

    def test_it_is_saved_and_read_back(self):
        doc = pc.load_doc(pc.dump_doc((2, 2), self.pages, 0))
        self.assertEqual(self.order(doc.pages), ["01.mp3", "00.mp3"])

    def test_a_pad_that_is_not_queued_writes_nothing_extra(self):
        doc = pc.dump_doc((2, 2), self.pages, 0)
        self.assertNotIn("queue", doc["pages"][0]["pads"]["1,1"])

    def test_a_junk_number_in_the_file_is_not_queued(self):
        for junk in ("x", -3, None, 2.5j):
            pad = pc.load_doc({"version": pc.CARTWALL_VERSION, "pages": [
                {"pads": {"0,0": {"path": "a.mp3", "queue": junk}}}]}).pages[0].pads[(0, 0)]
            self.assertEqual(pad.queue, 0, junk)


class PadEndedTest(_VoiceCase):
    """padEnded is the queue's cue: only a pad that ran out on its own."""

    def setUp(self):
        super().setUp()
        self.ended = []
        self.v.padEnded.connect(self.ended.append)

    def test_a_pad_that_runs_out_says_so(self):
        self.v.fire((0, 0, 0), _pad())
        self._end_of_media(self._voice((0, 0, 0)))
        self.assertEqual(self.ended, [(0, 0, 0)])
        self.assertEqual(self._live(), [])   # its voice is free for the next one

    def test_a_looping_pad_never_runs_out(self):
        self.v.fire((0, 0, 0), _pad(loop=True))
        self._end_of_media(self._voice((0, 0, 0)))
        self.assertEqual(self.ended, [])

    def test_a_stopped_pad_did_not_run_out(self):
        self.v.fire((0, 0, 0), _pad())
        self.v.stop((0, 0, 0))
        self._end_of_media(self._voice((0, 0, 0)))   # the tail of its fade
        self._drain_fades()
        self.assertEqual(self.ended, [])

    def test_a_file_that_cannot_play_did_not_run_out(self):
        from PySide6.QtMultimedia import QMediaPlayer
        self.v.fire((0, 0, 0), _pad())
        self._voice((0, 0, 0)).player.mediaStatusChanged.emit(
            QMediaPlayer.MediaStatus.InvalidMedia)
        self.assertEqual(self.ended, [])


def _samples(*names) -> dict[str, str]:
    """Real files: a pad whose sample is gone is skipped by the run."""
    folder = tempfile.mkdtemp(prefix="dp_cart_queue_fx_")
    out = {}
    for name in names:
        out[name] = os.path.join(folder, f"{name}.mp3")
        open(out[name], "wb").close()
    return out


class _QueueWallCase(unittest.TestCase):
    """A 2 × 2 wall with pads a, b, c on its first page."""

    def setUp(self):
        self.files = _samples("a", "b", "c")
        page = Page(pads={(0, 0): CartPad(path=self.files["a"]),
                          (0, 1): CartPad(path=self.files["b"]),
                          (1, 0): CartPad(path=self.files["c"])})
        self.w = gc.CartwallWidget()
        self.addCleanup(reap_widget, self.w)
        self.w.set_wall((2, 2), [page])
        self.saved = []
        self.w.changed.connect(lambda: self.saved.append(1))

    def button(self, key):
        return self.w._buttons[key]

    def ctrl_click(self, key):
        QTest.mouseClick(self.button(key), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.ControlModifier)

    def badge(self, key):
        lbl = self.button(key)._queue_lbl
        if lbl.isHidden():
            return ""
        text = lbl.text()   # ▶ and ≡ are pictures: read them back as the glyph
        for glyph in "▶≡":
            text = text.replace(gc.queue_mark_html(glyph), glyph)
        return text


class PadQueueClickTest(_QueueWallCase):

    def test_ctrl_click_queues_and_numbers_without_firing(self):
        fired = []
        self.w.padClicked.connect(fired.append)
        self.ctrl_click((0, 1, 0))
        self.ctrl_click((0, 0, 0))
        self.assertEqual(fired, [])
        self.assertEqual(self.badge((0, 1, 0)), "≡ 1")
        self.assertEqual(self.badge((0, 0, 0)), "≡ 2")
        self.assertEqual(self.badge((0, 0, 1)), "")
        self.assertTrue(self.saved)        # the queue is kept in cartwall.json

    def test_the_queue_edge_is_a_deeper_blue_than_a_running_pad(self):
        # Marcel: orange read too close to ✏'s amber — a queued pad must not
        # look like part of the edit, so it is blue, deeper than "running".
        self.ctrl_click((0, 0, 0))
        accent = gc._QUEUE_ACCENT
        self.assertIn(f"2px solid {accent}", self.button((0, 0, 0)).styleSheet())
        r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
        self.assertGreater(b, max(r, g))
        band = "#{:02x}{:02x}{:02x}".format(*gc._PLAYED_BAND[:3])
        self.assertLess(gc._luma(accent), gc._luma(band))
        self.assertLess(gc._luma(accent), gc._luma(gc._PLAY_BORDER))

    def test_a_full_volume_bed_ctrl_clicked_in_gets_the_bed_volume(self):
        bed = self.w.pad_at((0, 0, 0))
        bed.background = True
        self.w.set_background_volume(0.3)
        refreshed = []
        self.w.padRefreshed.connect(lambda key, pad: refreshed.append(key))
        self.ctrl_click((0, 0, 0))
        self.assertEqual(bed.volume, 0.3)
        self.assertEqual(refreshed, [(0, 0, 0)])    # a playing bed hears it
        self.assertIn("30%", self.button((0, 0, 0))._title.text())

    def test_a_second_ctrl_click_takes_it_out(self):
        self.ctrl_click((0, 0, 0))
        self.ctrl_click((0, 0, 1))
        self.ctrl_click((0, 0, 0))
        self.assertEqual(self.badge((0, 0, 0)), "")
        self.assertEqual(self.badge((0, 0, 1)), "≡ 1")

    def test_a_plain_click_still_fires(self):
        fired = []
        self.w.padClicked.connect(fired.append)
        QTest.mouseClick(self.button((0, 0, 0)), Qt.MouseButton.LeftButton)
        self.assertEqual(fired, [(0, 0, 0)])

    def test_ctrl_click_on_an_empty_pad_does_nothing(self):
        self.ctrl_click((0, 1, 1))
        self.assertEqual(pc.queued(self.w.pages()), [])
        self.assertEqual(self.saved, [])

    def test_in_edit_mode_ctrl_click_still_selects_and_the_badge_hides(self):
        self.ctrl_click((0, 0, 0))
        self.w.set_edit(True)
        self.assertEqual(self.badge((0, 0, 0)), "")
        self.ctrl_click((0, 0, 1))
        self.assertEqual(self.w.selection(), {(0, 0, 1)})
        self.assertEqual(self.w.pad_at((0, 0, 1)).queue, 0)

    def test_the_badge_survives_a_page_turn(self):
        self.ctrl_click((0, 0, 1))
        self.w.step_page(1)
        self.w.step_page(-1)
        self.assertEqual(self.badge((0, 0, 1)), "≡ 1")

    def test_the_running_pad_shows_its_play_mark(self):
        self.ctrl_click((0, 0, 0))
        self.w.set_playing((0, 0, 0), True)
        self.w.set_queue_run((0, 0, 0), self.w.pad_at((0, 0, 0)).queue)
        self.assertEqual(self.badge((0, 0, 0)), "▶ 1")
        self.w.end_queue_run()
        self.assertEqual(self.badge((0, 0, 0)), "≡ 1")

class OverriddenLoopTest(_QueueWallCase):
    """Marcel: a queued pad still showed ∞ and 🔁 though the run plays it
    once — what the queue overrides is struck through in red. The thin
    strike was hard to see on a pad, so it is a bold red ✕ on the 🔁 now:
    painted over it, not set beside it."""

    def setUp(self):
        super().setUp()
        self.w.set_wall((2, 2), [Page(pads={
            (0, 0): CartPad(path=self.files["a"], loop=True)})])

    def title(self):
        return self.button((0, 0, 0))._title.text()

    def test_a_queued_loop_is_crossed_out_in_red(self):
        self.ctrl_click((0, 0, 0))
        self.assertIn(gc.loop_overridden_html(), self.title())
        self.assertIn("<img src='data:image/png;base64,", self.title())
        # One mark, not a 🔁 with a ✕ next to it.
        self.assertNotIn("🔁", self.title())
        self.assertNotIn("✕", self.title())
        self.assertNotIn("<s ", self.title())
        self.assertIn("plays once", self.button((0, 0, 0)).toolTip())

    def test_the_cross_lies_on_the_loop(self):
        """Red where the ✕'s strokes cross, at the 🔁's centre, and the 🔁
        itself drawn under it."""
        img = gc.loop_overridden_image()
        mid = img.pixelColor(img.width() // 2, img.height() // 2)
        self.assertGreater(mid.red(), 180)
        self.assertLess(mid.green(), 90)
        other = {(c.red() // 32, c.green() // 32, c.blue() // 32)
                 for x in range(img.width()) for y in range(img.height())
                 if (c := img.pixelColor(x, y)).alpha() > 200
                 and not (c.red() > 180 and c.green() < 90)}
        self.assertTrue(other, "the 🔁 is under the ✕")

    def test_out_of_the_queue_it_is_a_plain_loop_again(self):
        self.ctrl_click((0, 0, 0))
        self.ctrl_click((0, 0, 0))
        self.assertIn(" 🔁", self.title())
        self.assertNotIn("<img", self.title())

    def test_in_edit_mode_the_loop_is_not_struck(self):
        self.ctrl_click((0, 0, 0))
        self.w.set_edit(True)
        self.assertNotIn("<img", self.title())

    def test_the_run_counts_the_looping_pad_down(self):
        btn = self.button((0, 0, 0))
        btn.set_playing(True)
        btn.set_remaining(5000, 0.5)
        self.assertEqual(btn._time.text(), "∞")
        self.ctrl_click((0, 0, 0))
        self.w.set_queue_run((0, 0, 0), self.w.pad_at((0, 0, 0)).queue)
        btn.set_remaining(5000, 0.5)
        self.assertEqual(btn._time.text(), gc.fmt_ms(5000))


class PadEditQueueTest(_QueueWallCase):

    def test_editing_a_queued_pad_keeps_its_place(self):
        self.ctrl_click((0, 0, 1))
        pad = self.w.pad_at((0, 0, 1))

        class _Dlg:
            def __init__(self, *_a, **_kw):
                self.previewVolume = self.previewFire = mock.Mock()

            def exec(self):
                return gc.QDialog.DialogCode.Accepted

            def pad(self):
                return CartPad(path=pad.path, label="new")

        with mock.patch.object(gc, "CartPadDialog", _Dlg):
            self.w._on_edit((0, 0, 1))
        self.assertEqual(self.w.pad_at((0, 0, 1)).label, "new")
        self.assertEqual(self.badge((0, 0, 1)), "≡ 1")


class _Status:
    def __init__(self):
        self.text = ""

    def showMessage(self, text, *_a):
        self.text = text


class _Desk(CartwallMixin):
    """Just enough window for the wall's fire path, on a stub voice pool."""

    def __init__(self, wall):
        me: Any = self
        me._settings = {}
        me._cartwall = wall
        me._cart_voices = cart_voices.CartVoices(voices=4, factory=_factory)
        me._cart_voices.set_level(1.0)
        me._cart_voices.padStopped.connect(self._on_cart_pad_stopped)
        me._cart_voices.padEnded.connect(self._on_cart_pad_ended)
        wall.padClicked.connect(self._on_pad_clicked)
        wall.stopAll.connect(self._on_cart_stop_all)
        status = _Status()
        me.statusBar = lambda: status


class QueueRunTest(_QueueWallCase):

    def setUp(self):
        super().setUp()
        self.desk: Any = _Desk(self.w)
        self.v = self.desk._cart_voices
        self.addCleanup(self.v.shutdown)
        for key in ((0, 0, 1), (0, 1, 0), (0, 0, 0)):   # b, c, a
            self.ctrl_click(key)

    def tap(self, key):
        QTest.mouseClick(self.button(key), Qt.MouseButton.LeftButton)

    def playing(self):
        return sorted(self.v.playing_keys())

    def run_out(self, key):
        voice = self.v._voice_for(key)
        self.assertIsNotNone(voice, f"{key} is not playing")
        _VoiceCase._end_of_media(voice)

    def test_a_tap_on_a_queued_pad_plays_the_queue_on_from_it(self):
        self.tap((0, 1, 0))                      # c
        self.assertEqual(self.playing(), [(0, 1, 0)])
        self.run_out((0, 1, 0))
        self.assertEqual(self.playing(), [(0, 0, 0)])   # then a
        self.run_out((0, 0, 0))
        self.assertEqual(self.playing(), [(0, 0, 1)])   # wraps to b
        self.assertEqual(self.badge((0, 0, 1)), "▶ 1")

    def test_a_queued_pad_s_loop_is_not_heard_inside_the_run(self):
        self.w.pad_at((0, 0, 1)).loop = True
        self.tap((0, 0, 1))
        self.assertFalse(self.v._voice_for((0, 0, 1)).pad.loop)
        self.run_out((0, 0, 1))
        self.assertEqual(self.playing(), [(0, 1, 0)])
        self.assertTrue(self.w.pad_at((0, 0, 1)).loop)   # the pad keeps its flag

    def test_a_lone_queued_pad_plays_again(self):
        self.ctrl_click((0, 1, 0))
        self.ctrl_click((0, 0, 0))
        self.tap((0, 0, 1))
        self.run_out((0, 0, 1))
        self.assertEqual(self.playing(), [(0, 0, 1)])

    def test_a_tap_on_the_running_pad_ends_the_run(self):
        self.tap((0, 0, 1))
        self.tap((0, 0, 1))
        self.assertIsNone(self.w.queue_run())
        self.run_out((0, 0, 1))                  # the tail of its fade
        self.assertEqual(self.playing(), [])

    def test_stop_all_ends_the_run(self):
        self.tap((0, 0, 1))
        self.w.stopAll.emit()
        self.assertIsNone(self.w.queue_run())

    def test_a_pad_that_stops_the_others_ends_the_run(self):
        self.ctrl_click((0, 0, 0))               # a out of the queue…
        self.w.pad_at((0, 0, 0)).stops_others = True   # …and taking the floor
        self.tap((0, 0, 1))
        self.tap((0, 0, 0))
        self.assertIsNone(self.w.queue_run())

    def test_an_unqueued_pad_on_top_leaves_the_run_alone(self):
        self.ctrl_click((0, 0, 0))               # a out of the queue
        self.tap((0, 0, 1))
        self.tap((0, 0, 0))
        self.assertEqual(self.w.queue_run()[0], (0, 0, 1))
        self.run_out((0, 0, 0))
        self.assertEqual(self.playing(), [(0, 0, 1)])

    def test_a_missing_file_is_skipped_and_said(self):
        os.remove(self.files["c"])
        self.tap((0, 0, 1))
        self.run_out((0, 0, 1))
        self.assertEqual(self.playing(), [(0, 0, 0)])
        self.assertIn(self.files["c"], self.desk.statusBar().text)

    def test_nothing_left_to_play_stops_the_run(self):
        for name in "abc":
            os.remove(self.files[name])
        self.tap((0, 0, 1))
        self.assertEqual(self.playing(), [])
        self.assertIsNone(self.w.queue_run())

    def test_the_running_pad_taken_out_hands_on_to_its_follower(self):
        self.tap((0, 0, 1))                      # b, followed by c
        self.ctrl_click((0, 0, 1))
        self.assertEqual(self.playing(), [(0, 0, 1)])   # it plays to its end
        self.run_out((0, 0, 1))
        self.assertEqual(self.playing(), [(0, 1, 0)])


class HeldPadMarkTest(_QueueWallCase):
    """⏸ A 🎶 pad paused under a title says so: in the ▶ queue the badge's
    ▶ turns into the pause mark ("⏸ 2"), outside it the mark takes the
    time's place and the time follows in grey ("⏸ 01:01").
    Marcel: "style it like the queue buttons if in queue", "the play next to
    desk icon is fine in size and style, paus should be same", "better would
    be instead and in () the time in grey", "show the length in grey,
    remove the ()"."""

    def middle(self, key):
        return self.button(key).held_in_middle()

    def test_a_queued_pad_shows_pause_and_its_number(self):
        self.ctrl_click((0, 0, 0))
        self.w.set_queue_run((0, 0, 0), self.w.pad_at((0, 0, 0)).queue)
        self.w.set_playing((0, 0, 0), True)
        self.assertEqual(self.badge((0, 0, 0)), "▶ 1")
        self.w.set_held((0, 0, 0), True)
        self.assertEqual(
            self.badge((0, 0, 0)),
            f"{gc.held_html('#ffffff', gc._HELD_BADGE_PX, gc._HELD_BADGE_DROP)} 1")
        self.assertFalse(self.middle((0, 0, 0)),
                         "the badge says it, the middle stays the time")
        self.w.set_held((0, 0, 0), False)
        self.assertEqual(self.badge((0, 0, 0)), "▶ 1")

    def test_a_pad_outside_the_queue_shows_pause_and_its_time_in_grey(self):
        button = self.button((0, 0, 1))
        self.w.set_playing((0, 0, 1), True)
        button.set_remaining(61_000, 0.5)
        self.w.set_held((0, 0, 1), True)
        self.assertEqual(self.badge((0, 0, 1)), "")
        self.assertTrue(self.middle((0, 0, 1)))
        mark = gc.held_html(button._fg, gc._HELD_TIME_PX, gc._HELD_TIME_DROP)
        self.assertEqual(button._time.text(),
                         f"{mark} <span style='color:{gc._HELD_TIME_GREY}'>"
                         "01:01</span>")
        self.w.set_held((0, 0, 1), False)
        self.assertFalse(self.middle((0, 0, 1)))
        self.assertEqual(button._time.text(), "01:01")

    def test_the_held_time_keeps_counting_down(self):
        button = self.button((0, 0, 1))
        self.w.set_playing((0, 0, 1), True)
        self.w.set_held((0, 0, 1), True)
        button.set_remaining(59_000, 0.6)
        self.assertIn(">00:59<", button._time.text())

    def test_a_stopped_pad_drops_the_mark(self):
        self.w.set_playing((0, 0, 1), True)
        self.w.set_held((0, 0, 1), True)
        self.w.set_playing((0, 0, 1), False)
        self.assertFalse(self.middle((0, 0, 1)))

    def test_the_mark_survives_a_rebuilt_page(self):
        self.w.set_playing((0, 0, 1), True)
        self.w.set_held((0, 0, 1), True)
        self.w._rebuild()
        self.assertTrue(self.middle((0, 0, 1)))

    def test_the_mark_is_two_bars_no_wider_than_tall(self):
        self.assertIn("width='6'", gc.held_html("#ffffff", 8))

    def test_the_badge_mark_sits_as_low_as_the_play_mark(self):
        """Marcel: "pause icon in badge for queue still to high play icon and
        queue icon are lower positioned" — a clear margin above the bars
        moves the middle the badge aligns on down."""
        self.assertIn(f"height='{gc._HELD_BADGE_PX + gc._HELD_BADGE_DROP}'",
                      gc.held_html("#ffffff", gc._HELD_BADGE_PX, gc._HELD_BADGE_DROP))


class PauseStartsTheQueueTest(_QueueWallCase):
    """⏸ The pause between two titles starts the wall's ▶ queue of 🎶
    background pads, when it is not running. Marcel: "if we have a queue
    which is not running start it when pause song needed" — it replaces the
    pause music picked on the ▶ panel."""

    def setUp(self):
        super().setUp()
        self.desk: Any = _Desk(self.w)
        self.v = self.desk._cart_voices
        self.addCleanup(self.v.shutdown)
        for key in ((0, 0, 1), (0, 1, 0), (0, 0, 0)):   # b, c, a
            self.ctrl_click(key)
            self.w.pad_at(key).background = True

    def playing(self):
        return sorted(self.v.playing_keys())

    def test_it_starts_from_the_first_queued_pad(self):
        self.desk._start_pause_pads()
        self.assertEqual(self.playing(), [(0, 0, 1)])
        self.assertEqual(self.w.queue_run()[0], (0, 0, 1))

    def test_a_running_queue_is_left_alone(self):
        QTest.mouseClick(self.button((0, 1, 0)), Qt.MouseButton.LeftButton)
        self.desk._start_pause_pads()
        self.assertEqual(self.playing(), [(0, 1, 0)])

    def test_it_starts_from_the_first_background_pad(self):
        # A pad that is not 🎶 would go on playing over the next title.
        self.w.pad_at((0, 0, 1)).background = False
        self.desk._start_pause_pads()
        self.assertEqual(self.playing(), [(0, 1, 0)])

    def test_a_queue_without_a_background_pad_is_not_started(self):
        for key in ((0, 0, 1), (0, 1, 0), (0, 0, 0)):
            self.w.pad_at(key).background = False
        self.desk._start_pause_pads()
        self.assertEqual(self.playing(), [])
        self.assertIsNone(self.w.queue_run())

    def test_no_queue_nothing_starts(self):
        for key in ((0, 0, 1), (0, 1, 0), (0, 0, 0)):
            self.ctrl_click(key)
        self.desk._start_pause_pads()
        self.assertEqual(self.playing(), [])


if __name__ == "__main__":
    unittest.main()
