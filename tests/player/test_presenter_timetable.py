"""🕒 The evening's running order: that a programme survives the round trip
through its file, that "which line is now" is decided on the wall clock, and
that the presenter's second page only exists while something is typed.
"""
import dataclasses
import os
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest import mock

# Offscreen BEFORE any QApplication, state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_timetable_"))

from PySide6.QtCore import QTime  # noqa: E402

from player.presenter_theme import (  # noqa: E402
    DEFAULT_KEY,
    THEMES,
    logo_paths,
    theme_for,
)
from player.timetable import (  # noqa: E402
    DEFAULT_ROTATE_SECS,
    DEFAULT_TITLE,
    MAX_ROTATE_SECS,
    MIN_ROTATE_SECS,
    Entry,
    Timetable,
    load_timetable,
    offset_for,
    save_timetable,
)
from tests.qt_test_support import reap_widget   # noqa: E402


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


_STATE = ("LW", "Titel", ("00:10", "− 02:00", False, 0.1),
          [("TG", "Zweiter")], ("", ""))


def _presenter():
    from player.presenter import PresenterWindow
    return PresenterWindow(lambda: _STATE)


# A theme that carries a mark: no shipped theme does any more, so the light
# one lends its colours to a copy that has one.
_MARK = "assets/test/mark.png"


def _marked_theme(test) -> None:
    """Make "light" a theme with a mark, for the length of the test."""
    marked = dataclasses.replace(THEMES["light"], logo=(_MARK,))
    patcher = mock.patch.dict(THEMES, {"light": marked})
    patcher.start()
    test.addCleanup(patcher.stop)


def _own_marks(test) -> None:
    """…and put its image on disk, under a temp asset root."""
    from PySide6.QtGui import QImage
    _marked_theme(test)
    root = Path(tempfile.mkdtemp(prefix="dp_marks_"))
    (root / _MARK).parent.mkdir(parents=True, exist_ok=True)
    img = QImage(40, 20, QImage.Format.Format_ARGB32)
    img.fill(0xffc9a84c)
    img.save(str(root / _MARK))
    patcher = mock.patch("player.presenter_theme.ASSET_ROOT", root)
    patcher.start()
    test.addCleanup(patcher.stop)


def _evening():
    return Timetable(title="Ablauf", entries=[
        Entry("18:00", "Sektempfang", ""),
        Entry("19:00", "Dinner", "Buffet im Saal"),
        Entry("20:30", "Eröffnungstanz", ""),
        Entry("ca. 23 Uhr", "Mitternachtssnack", "")])


def _long_evening():
    """Ten lines, all before midnight — `current_index` reads the wall clock as
    minutes past midnight, so a programme running past it is a question of its
    own and not what these tests are about."""
    return Timetable(title="Ablauf", entries=[
        Entry(f"{h:02d}:00", f"Punkt {h}") for h in range(14, 24)])


def _shown(w) -> list:
    return [i for i, (row, *_) in enumerate(w.time_page._rows)
            if not row.isHidden()]


def _gold(w) -> list:
    """What the accent is standing on, read off the page itself."""
    up = w.time_page._theme.up
    return [what.text() for _row, _time, what, _note in w.time_page._rows
            if up in what.styleSheet()]


def _at(hh, mm):
    return datetime(2026, 9, 19, hh, mm)


def _resize(w, width, height):
    """A window that was never shown takes the new geometry but gets no resize
    event for it, so the pass that sizes the fonts off the height never runs.
    Hand it the event the platform would have sent."""
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QResizeEvent
    from PySide6.QtWidgets import QApplication
    old = w.size()
    w.resize(width, height)
    QApplication.sendEvent(w, QResizeEvent(QSize(width, height), old))


class EntryTimeTest(unittest.TestCase):
    """`minutes()` — what counts as a clock time on a programme."""

    def test_colon_and_dot_both_read(self):
        """"20.30" is as normal a spelling as "20:30" on a German programme."""
        self.assertEqual(Entry("20:30").minutes(), 20 * 60 + 30)
        self.assertEqual(Entry("20.30").minutes(), 20 * 60 + 30)
        self.assertEqual(Entry(" 9:05 ").minutes(), 9 * 60 + 5)

    def test_free_text_is_no_clock_time(self):
        """It is printed, it just never becomes the current line."""
        for text in ("", "im Anschluss", "ca. 23 Uhr", "abends", "25:00",
                     "20:75", "xx:yy"):
            self.assertIsNone(Entry(text).minutes(), text)

    def test_trailing_text_after_the_time_survives(self):
        """"20:30 Uhr" is a time somebody typed the unit onto."""
        self.assertEqual(Entry("20:30 Uhr").minutes(), 20 * 60 + 30)


class TimetableDataTest(unittest.TestCase):
    """The programme as data: reading it back, and reading junk back."""

    def test_round_trip_through_a_dict(self):
        t = _evening()
        t.rotate, t.rotate_secs = True, 45
        back = Timetable.from_dict(t.as_dict())
        self.assertEqual(back.title, t.title)
        self.assertEqual([e.as_dict() for e in back.entries],
                         [e.as_dict() for e in t.entries])
        self.assertTrue(back.rotate)
        self.assertEqual(back.rotate_secs, 45)

    def test_junk_becomes_an_empty_programme(self):
        """Decoration on a screen is never a reason to lose the evening."""
        for junk in (None, [], "kaputt", 7, {"entries": "nope"}):
            table = Timetable.from_dict(junk)
            self.assertTrue(table.is_empty(), junk)
            self.assertEqual(table.rotate_secs, DEFAULT_ROTATE_SECS)

    def test_rotate_secs_is_clamped(self):
        self.assertEqual(
            Timetable.from_dict({"rotate_secs": 1}).rotate_secs,
            MIN_ROTATE_SECS)
        self.assertEqual(
            Timetable.from_dict({"rotate_secs": 99999}).rotate_secs,
            MAX_ROTATE_SECS)
        self.assertEqual(
            Timetable.from_dict({"rotate_secs": "viel"}).rotate_secs,
            DEFAULT_ROTATE_SECS)

    def test_a_time_set_as_now_becomes_a_shift_of_the_clock(self):
        """"It is only 20:00" said at 20:45 means the whole evening runs
        three quarters of an hour behind, not that the clock stops."""
        self.assertEqual(offset_for(time(20, 0), _at(20, 45)),
                         timedelta(minutes=-45))
        self.assertEqual(offset_for(time(21, 30), _at(20, 45)),
                         timedelta(minutes=45))

    def test_a_time_set_as_now_takes_the_nearer_of_the_two_days(self):
        """00:30 typed at 23:50 is forty minutes on, not a day back — the
        small hours belong to the evening that is running."""
        self.assertEqual(offset_for(time(0, 30), _at(23, 50)),
                         timedelta(minutes=40))
        self.assertEqual(offset_for(time(23, 50), _at(0, 30)),
                         timedelta(minutes=-40))

    def test_a_time_set_as_now_is_no_shift_at_all(self):
        self.assertEqual(offset_for(time(20, 45), _at(20, 45)),
                         timedelta(0))

    def test_a_blank_title_falls_back(self):
        self.assertEqual(Timetable.from_dict({"title": ""}).title,
                         DEFAULT_TITLE)

    def test_is_empty_sees_through_blank_rows(self):
        """Rows somebody cleared out instead of removing are not entries."""
        self.assertTrue(Timetable().is_empty())
        self.assertTrue(Timetable(entries=[Entry(), Entry("", "", "x")])
                        .is_empty())
        self.assertFalse(Timetable(entries=[Entry("", "Tanz frei")]).is_empty())

    def test_current_index_follows_the_clock(self):
        t = _evening()
        self.assertEqual(t.current_index(_at(17, 0)), -1)   # before the first
        self.assertEqual(t.current_index(_at(18, 0)), 0)    # on the minute
        self.assertEqual(t.current_index(_at(19, 30)), 1)
        self.assertEqual(t.current_index(_at(23, 59)), 2)   # free text is no row

    def test_the_evening_runs_past_midnight(self):
        """"01:00 Ende" reads as sixty minutes past midnight, which is earlier
        than every line above it — so the moment the party began, the accent
        jumped to the last row and the hall was told the evening was over. A
        row keeps it until the next row's time comes."""
        t = Timetable(entries=[Entry("16:00", "Trauung"),
                               Entry("18:00", "Party"),
                               Entry("01:00", "Ende")])
        self.assertEqual(t.current_index(_at(15, 0)), -1)
        self.assertEqual(t.current_index(_at(16, 30)), 0)
        self.assertEqual(t.current_index(_at(19, 15)), 1)   # not "Ende"
        self.assertEqual(t.current_index(_at(23, 59)), 1)
        self.assertEqual(t.current_index(_at(0, 30)), 1)    # still the party
        self.assertEqual(t.current_index(_at(1, 30)), 2)
        self.assertEqual(t.current_index(_at(4, 0)), 2)

    def test_the_afternoon_before_is_not_the_night_after(self):
        """13:00 on the day of an evening that ends at 01:00 stands before it,
        not twelve hours past its last line."""
        t = Timetable(entries=[Entry("16:00", "Trauung"),
                               Entry("01:00", "Ende")])
        self.assertEqual(t.current_index(_at(13, 0)), -1)

    def test_free_text_does_not_break_the_evening_open(self):
        """A line without a clock time is skipped, not read as a fall back to
        midnight that puts everything under it on the next day."""
        t = Timetable(entries=[Entry("16:00", "Trauung"),
                               Entry("im Anschluss", "Kaffee"),
                               Entry("01:00", "Ende")])
        self.assertEqual(t.current_index(_at(19, 15)), 0)
        self.assertEqual(t.current_index(_at(2, 0)), 2)

    def test_a_point_keeps_the_accent_however_far_off_the_next_one_is(self):
        """A point used to go done half an hour on when the next was more than
        an hour away. On the programme this is for, that left the screen with
        nothing lit from 19:30 to 01:00 — the whole party. The point the
        evening has reached keeps it until the next one relieves it."""
        t = Timetable(entries=[Entry("18:00", "Party"),
                               Entry("20:00", "Hochzeitstanz"),
                               Entry("01:00", "Ende")])
        self.assertEqual(t.current_index(_at(20, 15)), 1)
        self.assertEqual(t.current_index(_at(20, 30)), 1)
        self.assertEqual(t.current_index(_at(23, 0)), 1)

    def test_the_last_point_of_the_evening_keeps_it_too(self):
        """Nothing follows it, so nothing can relieve it."""
        t = Timetable(entries=[Entry("20:30", "Eröffnungstanz")])
        self.assertEqual(t.current_index(_at(20, 45)), 0)
        self.assertEqual(t.current_index(_at(21, 15)), 0)

    def test_nothing_is_lit_before_the_evening_starts(self):
        t = _evening()
        self.assertEqual(t.current_index(_at(17, 0)), -1)

    def test_current_index_without_clock_times(self):
        """Then nothing is highlighted and every line reads the same."""
        t = Timetable(entries=[Entry("später", "Tanz frei"),
                               Entry("", "Ende offen")])
        self.assertEqual(t.current_index(_at(22, 0)), -1)

    def test_saved_and_loaded_back(self):
        t = _evening()
        t.rotate, t.rotate_secs = True, 30
        self.assertTrue(save_timetable(t))
        back = load_timetable()
        self.assertEqual(back.title, "Ablauf")
        self.assertEqual([e.what for e in back.entries],
                         [e.what for e in t.entries])
        self.assertTrue(back.rotate)
        self.assertEqual(back.rotate_secs, 30)


class PresenterPageTest(unittest.TestCase):
    """The second page on the screen itself."""

    @classmethod
    def setUpClass(cls):
        _app()

    def test_an_empty_programme_hides_the_button(self):
        """A button onto an empty screen is worse than no button."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        self.assertFalse(w.time_btn.isVisible())
        self.assertFalse(w.timetable_shown())
        w.set_timetable(Timetable())
        self.assertFalse(w.time_btn.isVisibleTo(w))
        w.set_timetable(_evening())
        self.assertTrue(w.time_btn.isVisibleTo(w))

    def test_rows_are_built_from_the_entries(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        self.assertEqual(w.time_page.row_count(), 4)
        self.assertEqual(w.time_page.title_lbl.text(), "Ablauf")
        # A row left blank is dropped rather than printed as a gap.
        w.set_timetable(Timetable(entries=[Entry("18:00", "Sekt"), Entry()]))
        self.assertEqual(w.time_page.row_count(), 1)

    def test_only_a_window_of_the_programme_stands_on_the_screen(self):
        """A programme on a wall is not read end to end — the hall looks up to
        see where the evening is and what comes next. One spent line, the one
        it stands on, and the next two."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_long_evening())
        w.time_page.sync_now(_at(18, 30))     # standing on 18:00, the fifth
        self.assertEqual(_shown(w), [3, 4, 5, 6])

    def test_the_window_opens_at_the_top_before_the_evening_starts(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_long_evening())
        w.time_page.sync_now(_at(9, 0))       # nothing has happened yet
        self.assertEqual(_shown(w), [0, 1, 2, 3])

    def test_the_window_is_pulled_back_off_the_end(self):
        """The last line standing alone under the heading reads as a screen
        that has lost its content, so the block stays full."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_long_evening())
        w.time_page.sync_now(_at(23, 30))     # the last line is now
        self.assertEqual(_shown(w), [6, 7, 8, 9])

    def test_the_evening_goes_on_below_the_window(self):
        """Four lines out of ten look like the whole programme unless the page
        says otherwise, so a mark stands under them while there is more."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_long_evening())
        w.time_page.sync_now(_at(18, 30))
        self.assertFalse(w.time_page._more.isHidden())
        w.time_page.sync_now(_at(23, 30))     # the window has reached the end
        self.assertTrue(w.time_page._more.isHidden())

    def test_the_page_can_be_told_what_time_it_is(self):
        """The screen reads the shifted clock, not the machine's — and it
        keeps running from there rather than standing still."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_long_evening())
        real = _at(14, 30)
        w.time_page.sync_now(real)
        self.assertEqual(_gold(w), ["Punkt 14"])
        # Four hours on, without the machine's clock moving at all.
        w.set_now_offset(timedelta(hours=4))
        w.time_page.sync_now(real)
        self.assertEqual(_gold(w), ["Punkt 18"])
        # …and an hour of real time later it has moved on by an hour too.
        w.time_page.sync_now(_at(15, 30))
        self.assertEqual(_gold(w), ["Punkt 19"])

    def test_the_page_goes_back_to_the_machine_clock(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_long_evening())
        w.set_now_offset(timedelta(hours=4))
        w.set_now_offset(None)
        w.time_page.sync_now(_at(14, 30))
        self.assertEqual(_gold(w), ["Punkt 14"])

    def test_a_short_programme_says_nothing_about_more(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())           # four lines, four rows shown
        w.time_page.sync_now(_at(19, 30))
        self.assertTrue(w.time_page._more.isHidden())

    def test_exactly_one_line_is_ever_lit(self):
        """However long the gap to the next point, the accent stays where the
        evening has reached — the hall is never looking at a programme with
        nothing marked on it."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(Timetable(entries=[Entry("18:00", "Party"),
                                           Entry("20:00", "Hochzeitstanz"),
                                           Entry("01:00", "Ende")]))
        for hh, mm in ((20, 15), (21, 0), (23, 30)):
            w.time_page.sync_now(_at(hh, mm))
            self.assertEqual(_gold(w), ["Hochzeitstanz"], f"{hh}:{mm:02d}")

    def test_a_blank_line_does_not_shift_the_accent(self):
        """The page drops a line somebody typed and cleared again rather than
        printing it as a gap, and the clock counts entries — so one blank row
        above the evening put the accent a line below where it stood."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(Timetable(entries=[
            Entry(),                            # typed and cleared again
            Entry("18:00", "Sektempfang"),
            Entry("19:00", "Dinner"),
            Entry("20:30", "Eröffnungstanz")]))
        w.time_page.sync_now(_at(19, 15))
        self.assertEqual(_gold(w), ["Dinner"])

    def test_a_blank_line_does_not_shift_the_window(self):
        """The window is anchored on the same row, so it moves with it."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(Timetable(entries=[
            Entry(), *_long_evening().entries]))
        w.time_page.sync_now(_at(18, 30))       # standing on 18:00, row four
        self.assertEqual(_shown(w), [3, 4, 5, 6])
        self.assertEqual(_gold(w), ["Punkt 18"])

    def test_a_short_programme_stands_whole(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())           # four lines
        w.time_page.sync_now(_at(19, 30))
        self.assertEqual(_shown(w), [0, 1, 2, 3])

    def test_a_long_programme_sets_as_big_as_a_short_one(self):
        """Five lines stand on the screen either way, so the tenth entry no
        longer costs the first five their size."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        _resize(w, 1280, 720)
        w.set_timetable(Timetable(entries=[
            Entry(f"{h:02d}:00", f"Punkt {h}") for h in range(14, 19)]))
        five = w.time_page._rows[0][2].font().pixelSize()
        w.set_timetable(_long_evening())
        self.assertEqual(w.time_page._rows[0][2].font().pixelSize(), five)

    def test_the_running_order_does_not_size_the_stack(self):
        """A stack is as tall as its tallest page, and the fitting pass shrinks
        every font on the screen until that height fits the window — so a long
        programme would reach across and take the dance down with it. The
        running order has no minimum worth defending: it sets itself to the
        height it is given."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        _resize(w, 1280, 720)
        music = w.stack.minimumSizeHint().height()
        w.set_timetable(Timetable(entries=[
            Entry(f"{h:02d}:00", f"Punkt {h}", "mit Notiz") for h in range(12)]))
        # The page really is the taller of the two…
        self.assertGreater(w.time_page.minimumSizeHint().height(), music)
        # …and the stack is still as tall as the music page alone.
        self.assertEqual(w.stack.minimumSizeHint().height(), music)

    def test_the_heading_stands_at_the_top_of_the_page(self):
        """Centred, it came down into the middle of the screen and took the
        rows with it. The air belongs under the lines, not over the mark."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        _resize(w, 1280, 720)
        w.set_timetable(_evening())
        lyt = w.time_page.layout()
        self.assertGreater(lyt.contentsMargins().top(), 0)
        # …and nothing stretchy above the mark to push it back down.
        self.assertIsNotNone(lyt.itemAt(0).widget())

    def test_the_rows_take_the_size_the_screen_gives_them(self):
        """Same programme, bigger screen, bigger lines — the running order is
        sized off the window, not off a fixed point size."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_long_evening())
        _resize(w, 1280, 720)
        small = w.time_page._rows[0][2].font().pixelSize()
        _resize(w, 1920, 1080)
        self.assertGreater(w.time_page._rows[0][2].font().pixelSize(), small)

    def test_the_pad_that_puts_two_faces_on_one_baseline(self):
        """The mono time rises less far than the title beside it, so the one
        that starts higher is padded down by the difference — and two fonts
        that already agree are left alone."""
        from PySide6.QtGui import QFont, QFontMetrics

        from player.presenter import _baseline_pads
        small, big = QFont(), QFont()
        small.setPixelSize(20)
        big.setPixelSize(40)
        gap = QFontMetrics(big).ascent() - QFontMetrics(small).ascent()
        self.assertGreater(gap, 0)      # …or the case isn't being tested
        self.assertEqual(_baseline_pads(small, big), (gap, 0))
        self.assertEqual(_baseline_pads(big, small), (0, gap))
        self.assertEqual(_baseline_pads(small, small), (0, 0))

    def test_the_time_and_what_it_names_stand_on_one_line(self):
        """Both labels are top-aligned in the same row, so the padding has to
        make up for the faces: first baseline = padding + ascent, and the two
        of them must come out equal on every row."""
        from PySide6.QtGui import QFontMetrics
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.resize(1280, 720)
        w.set_timetable(_evening())
        for i, (_row, time_lbl, what_lbl, _n) in enumerate(w.time_page._rows):
            base = [lbl.contentsMargins().top()
                    + QFontMetrics(lbl.font()).ascent()
                    for lbl in (time_lbl, what_lbl)]
            self.assertEqual(base[0], base[1],
                             f"row {i} sets the time off its own line")

    def test_the_time_carries_its_face_on_the_font(self):
        """Not on the stylesheet: the baseline above is measured off the font,
        and a family that only arrives with the polish is not in it yet."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        _row, time_lbl, *_ = w.time_page._rows[0]
        self.assertIn("Consolas", time_lbl.font().families())
        self.assertNotIn("font-family", time_lbl.styleSheet())

    def test_toggling_switches_the_page(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.show_timetable(True, fade=False)
        self.assertTrue(w.timetable_shown())
        w.show_timetable(False, fade=False)
        self.assertFalse(w.timetable_shown())

    def test_an_empty_programme_cannot_be_shown(self):
        """…and takes the screen back to the music if it is standing on it."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.show_timetable(True, fade=False)
        w.set_timetable(Timetable())
        self.assertFalse(w.timetable_shown())
        w.show_timetable(True, fade=False)
        self.assertFalse(w.timetable_shown())

    def test_rotation_follows_the_programme(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        self.assertFalse(w._rotate.isActive())
        w.set_timetable(Timetable(entries=[Entry("18:00", "Sekt")],
                                  rotate=True, rotate_secs=25))
        self.assertTrue(w._rotate.isActive())
        self.assertEqual(w._rotate.interval(), 25_000)
        w.set_timetable(Timetable(rotate=True))    # nothing to fade to
        self.assertFalse(w._rotate.isActive())

    def test_the_current_row_wears_the_accent(self):
        """The row the evening stands on in `up`, the ones behind it in `past`,
        the ones ahead in `hero` — the same reading the up-next column uses."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_theme("light")
        w.set_timetable(_evening())
        w.time_page.sync_now(_at(19, 15))
        t = w._theme
        _row, _time, what0, _n = w.time_page._rows[0]
        _row, _time, what1, _n = w.time_page._rows[1]
        _row, _time, what2, _n = w.time_page._rows[2]
        self.assertIn(t.past, what0.styleSheet())
        self.assertIn(t.up, what1.styleSheet())
        self.assertIn(t.hero, what2.styleSheet())

    def test_a_free_text_time_is_not_cut_off(self):
        """The time column is one width, but taken from the widest time typed:
        "ca. 02 Uhr" must not come out as ". 02 Uhr"."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.resize(1280, 720)
        w.set_timetable(Timetable(entries=[
            Entry("18:00", "Sektempfang"),
            Entry("ca. 02 Uhr", "Ende offen")]))
        w.time_page.apply_fonts(720, 1.0)
        widths = {lbl.width() for _r, lbl, *_ in w.time_page._rows}
        self.assertEqual(len(widths), 1, "the times still form a column")
        for _row, time_lbl, *_ in w.time_page._rows:
            self.assertGreaterEqual(time_lbl.width(),
                                    time_lbl.sizeHint().width(),
                                    f"{time_lbl.text()!r} is cut off")

    def test_a_theme_switch_reaches_the_page(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.set_theme("light")
        t = w._theme
        self.assertIn(t.hero, w.time_page.title_lbl.styleSheet())
        self.assertIn(t.hero, w.time_page._rows[-1][2].styleSheet())

    def test_the_heading_is_not_the_grey_of_a_subtitle(self):
        """It names the page; on the wedding ground that has to read dark."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.set_theme("light")
        self.assertNotIn(w._theme.sub, w.time_page.title_lbl.styleSheet())

    def test_a_theme_with_a_mark_crowns_the_page_with_it(self):
        """…and the default theme, which has no mark, shows none."""
        _own_marks(self)
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.time_page.apply_fonts(720, 1.0)
        for lbl in w.time_page._logo_lbls:
            self.assertFalse(lbl.isVisibleTo(w.time_page))
        w.set_theme("light")
        w.time_page.apply_fonts(720, 1.0)
        shown = [lbl for lbl in w.time_page._logo_lbls
                 if lbl.isVisibleTo(w.time_page)]
        self.assertEqual(len(shown), 1, "the one mark the theme names")
        for lbl in shown:
            self.assertFalse(lbl.pixmap().isNull())
        # …and back again: the mark must not outlive the theme that brought it.
        w.set_theme(DEFAULT_KEY)
        w.time_page.apply_fonts(720, 1.0)
        for lbl in w.time_page._logo_lbls:
            self.assertFalse(lbl.isVisibleTo(w.time_page))

    def test_the_marks_are_found_under_the_asset_root(self):
        """A theme pointing outside the repo would break once packaged."""
        _own_marks(self)
        t = theme_for("light")
        self.assertTrue(t.logo)
        self.assertEqual(len(logo_paths(t)), len(t.logo),
                         "every mark the theme names is found")

    def test_missing_marks_cost_only_the_crown(self):
        """A mark not on disk: the page then shows none."""
        _marked_theme(self)
        with mock.patch("player.presenter_theme.ASSET_ROOT",
                        Path(tempfile.mkdtemp(prefix="dp_nomarks_"))):
            self.assertEqual(logo_paths(theme_for("light")), [])
            w = _presenter()
            self.addCleanup(reap_widget, w)
            w.set_timetable(_evening())
            w.set_theme("light")
            w.time_page.apply_fonts(720, 1.0)
            for lbl in w.time_page._logo_lbls:
                self.assertFalse(lbl.isVisibleTo(w.time_page))

    def test_the_mark_leaves_the_rows_room(self):
        """The crown is paid for out of the rows' height, not out of the page:
        a programme under the mark must still size smaller, not overflow.
        A full window of noted lines, so the rows are sized by the height left
        and not already held at their cap."""
        _own_marks(self)
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(Timetable(title="Ablauf", entries=[
            Entry(f"{18 + i}:00", f"Punkt {i}", "mit Notiz") for i in range(6)]))
        w.time_page.apply_fonts(720, 1.0)
        plain = w.time_page._rows[0][2].font().pixelSize()
        w.set_theme("light")
        w.time_page.apply_fonts(720, 1.0)
        crowned = w.time_page._rows[0][2].font().pixelSize()
        self.assertLess(crowned, plain)

    def test_the_running_order_gets_the_foot_to_itself(self):
        """A row of play buttons under a printed programme is the one thing
        that stops the screen looking like one, so the transport stays on the
        music page — without the setting itself changing under it."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.set_controls_shown(True)
        self.assertTrue(w.ctl_box.isVisibleTo(w))

        w.show_timetable(True, fade=False)
        self.assertFalse(w.ctl_box.isVisibleTo(w))
        w.show_timetable(False, fade=False)
        self.assertTrue(w.ctl_box.isVisibleTo(w))

        # Switched off while the programme is up, it stays off on the way back.
        w.show_timetable(True, fade=False)
        w.set_controls_shown(False)
        self.assertFalse(w.ctl_box.isVisibleTo(w))
        w.show_timetable(False, fade=False)
        self.assertFalse(w.ctl_box.isVisibleTo(w))

    def test_the_button_lights_for_the_page_it_is_moving_to(self):
        """The pages swap when the fade *ends*, so for half a second the screen
        is still standing on the one it is leaving — and the 🗓 button, painted
        the moment the press lands, lit up for exactly the wrong page."""
        from shared.icons import pixmap as icon_pixmap

        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.show()
        self.addCleanup(w.hide)

        w.show_timetable(True)                    # …with the fade
        self.assertFalse(w.timetable_shown())     # not there yet
        self.assertTrue(w._timetable_wanted())    # but on its way
        t = theme_for(DEFAULT_KEY)
        px = w._btn_px
        lit = icon_pixmap("calendar", px, t.up).toImage()
        self.assertEqual(w.time_btn.icon().pixmap(px, px).toImage(), lit)

        w._fade_in()                              # the fade lands
        self.assertTrue(w.timetable_shown())
        self.assertTrue(w._timetable_wanted())

        w.show_timetable(False)                   # …and away again
        self.assertTrue(w.timetable_shown())      # still standing on it
        self.assertFalse(w._timetable_wanted())   # but already leaving
        w._paint_buttons()
        dim = icon_pixmap("calendar", px, t.sub).toImage()
        self.assertEqual(w.time_btn.icon().pixmap(px, px).toImage(), dim)

    def test_a_second_press_mid_fade_turns_the_fade_back(self):
        """🗓 pressed twice inside the half second: the second press means
        "stay here". It used to ask for the page it was already fading to —
        and restart the fade-out from full."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.show()
        self.addCleanup(w.hide)

        w._toggle_timetable()                     # …fading out the music page
        self.assertTrue(w._timetable_wanted())
        w._toggle_timetable()                     # changed their mind
        self.assertFalse(w._timetable_wanted())
        self.assertEqual(w._anim.endValue(), 1.0, "fading back in")
        w._fade_in()                              # a late end of the fade-out
        self.assertFalse(w.timetable_shown(), "no swap after all")

    def test_the_t_key_toggles(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_timetable(_evening())
        w.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_T,
                                  Qt.KeyboardModifier.NoModifier, "t"))
        self.assertTrue(w.timetable_shown())
        w.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_T,
                                  Qt.KeyboardModifier.NoModifier, "t"))
        self.assertFalse(w.timetable_shown())


if __name__ == "__main__":
    unittest.main()


class TimetableDialogTest(unittest.TestCase):
    """The one control on the dialog that does not go into the file."""

    def _dlg(self, offset=None):
        from player.timetable_dialog import TimetableDialog
        _app()
        dlg = TimetableDialog(_evening(), None, now_offset=offset)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_machine_clock_is_the_default(self):
        dlg = self._dlg()
        self.assertFalse(dlg.now_check.isChecked())
        self.assertFalse(dlg.now_time.isEnabled())
        self.assertIsNone(dlg.now_offset())

    def test_a_set_time_comes_back_as_the_same_shift(self):
        """Opened on a running shift it shows the shifted time, and saving
        without touching anything gives that same shift back — reopening the
        dialog must not quietly put the evening back on the machine."""
        dlg = self._dlg(timedelta(minutes=-45))
        self.assertTrue(dlg.now_check.isChecked())
        self.assertTrue(dlg.now_time.isEnabled())
        shown = dlg.now_time.time()
        want = datetime.now() - timedelta(minutes=45)
        self.assertEqual((shown.hour(), shown.minute()),
                         (want.hour, want.minute))
        back = dlg.now_offset()
        # Both are rounded to the minute, so they may differ by one.
        self.assertLessEqual(abs(back - timedelta(minutes=-45)),
                             timedelta(minutes=1))

    def test_an_untouched_clock_keeps_its_shift_exactly(self):
        """The field only shows whole minutes, and the dialog can sit open
        for a while. Recomputing the shift from it on every save (and every
        live preview) lost up to a minute per round trip plus however long
        the dialog was open — the evening's clock crept back to the
        machine's. A clock nobody touched hands its shift back unchanged."""
        from unittest import mock

        import player.timetable as tt
        offset = timedelta(minutes=-45, seconds=-17)
        dlg = self._dlg(offset)
        later = datetime.now() + timedelta(minutes=10)

        class _Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return later

        with mock.patch.object(tt, "datetime", _Later):
            self.assertEqual(dlg.now_offset(), offset)

    def test_a_retyped_clock_takes_the_new_time(self):
        dlg = self._dlg(timedelta(minutes=-45))
        want = datetime.now() + timedelta(hours=1)
        dlg.now_time.setTime(QTime(want.hour, want.minute))
        back = dlg.now_offset()
        self.assertLessEqual(abs(back - timedelta(hours=1)), timedelta(minutes=1))

    def test_unticking_puts_it_back_on_the_machine(self):
        dlg = self._dlg(timedelta(hours=2))
        dlg.now_check.setChecked(False)
        self.assertIsNone(dlg.now_offset())
        self.assertFalse(dlg.now_time.isEnabled())

    def test_the_shift_is_not_written_into_the_programme(self):
        """It belongs to one evening; a forgotten test time must not be
        waiting in the file on the night."""
        dlg = self._dlg(timedelta(hours=2))
        self.assertNotIn("offset", dlg.timetable().as_dict())
        self.assertNotIn("now", dlg.timetable().as_dict())


class TimetableLiveEditTest(unittest.TestCase):
    """The dialog tells whoever opened it that something was edited, so an
    open presenter screen can follow along instead of waiting for Save."""

    def _dlg(self):
        from player.timetable_dialog import TimetableDialog
        _app()
        dlg = TimetableDialog(_evening(), None)
        self.addCleanup(reap_widget, dlg)
        self.seen = []
        dlg.changed.connect(lambda: self.seen.append(1))
        return dlg

    def test_opening_it_is_not_an_edit(self):
        """Filling the grid with what is already saved must not announce four
        edits before anybody has typed a thing."""
        dlg = self._dlg()
        self.assertEqual(self.seen, [])
        self.assertEqual(len(dlg.timetable().entries), 4)

    def test_typing_in_a_cell_says_so(self):
        dlg = self._dlg()
        from player.timetable_dialog import _COL_WHAT
        dlg.table.item(1, _COL_WHAT).setText("Abendessen")
        self.assertTrue(self.seen)
        self.assertEqual(dlg.timetable().entries[1].what, "Abendessen")

    def test_the_heading_says_so(self):
        dlg = self._dlg()
        dlg.title_ed.setText("Programm")
        self.assertTrue(self.seen)

    def test_a_new_line_says_so(self):
        dlg = self._dlg()
        dlg._add_row()
        self.assertTrue(self.seen)

    def test_taking_a_line_out_says_so(self):
        """removeRow writes no cell, so this one has to speak up by itself."""
        dlg = self._dlg()
        dlg.table.setCurrentCell(1, 0)
        dlg._remove_row()
        self.assertTrue(self.seen)
        self.assertEqual(len(dlg.timetable().entries), 3)

    def test_moving_a_line_says_so(self):
        dlg = self._dlg()
        dlg.table.setCurrentCell(1, 0)
        dlg._move(-1)
        self.assertTrue(self.seen)

    def test_the_rotation_says_so(self):
        dlg = self._dlg()
        dlg.rotate_check.setChecked(not dlg.rotate_check.isChecked())
        self.assertTrue(self.seen)
        self.seen.clear()
        dlg.rotate_secs.setValue(dlg.rotate_secs.value() + 1)
        self.assertTrue(self.seen)

    def test_the_clock_says_so(self):
        dlg = self._dlg()
        dlg.now_check.setChecked(True)
        self.assertTrue(self.seen)
        self.seen.clear()
        t = dlg.now_time.time()
        dlg.now_time.setTime(QTime(t.hour(), (t.minute() + 5) % 60))
        self.assertTrue(self.seen)
        self.assertIsNotNone(dlg.now_offset())


class NestedPointTest(unittest.TestCase):
    """A point with an end can hold other points inside it — the party runs
    from 19:00 to 01:00, the opening dance happens somewhere in the middle of
    it, and when the dance is over the party is what is running again."""

    def _party(self):
        return Timetable(entries=[
            Entry("19:00", "Tanzparty", "", until="01:00"),
            Entry("19:30", "Hochzeitstanz", "", until="19:50"),
            Entry("23:00", "Mitternachtssnack", "", until="23:30")])

    def test_an_end_may_be_a_clock_time(self):
        e = Entry("19:00", "Tanzparty", until="01:00")
        self.assertEqual(e.minutes(), 19 * 60)
        self.assertEqual(e.until_minutes(), 60)

    def test_an_end_may_be_a_count_of_minutes(self):
        """"20" beside a five-minute dance is what somebody types when they
        know how long it takes but not when it lands."""
        self.assertEqual(Entry("19:30", "Tanz", until="20").length(), 20)
        self.assertEqual(Entry("19:30", "Tanz", until="20 min").length(), 20)
        self.assertIsNone(Entry("19:30", "Tanz", until="01:00").length())
        self.assertIsNone(Entry("19:30", "Tanz", until="").length())

    def test_the_point_inside_takes_the_accent_while_it_runs(self):
        t = self._party()
        self.assertEqual(t.current_index(_at(19, 10)), 0)   # party only
        self.assertEqual(t.current_index(_at(19, 30)), 1)   # on the minute
        self.assertEqual(t.current_index(_at(19, 45)), 1)

    def test_the_point_inside_hands_the_accent_back_when_it_is_over(self):
        """The whole reason for the column: at 19:50 the dance is done and the
        party it stands in is what the hall is looking at again."""
        t = self._party()
        self.assertEqual(t.current_index(_at(19, 50)), 0)
        self.assertEqual(t.current_index(_at(22, 0)), 0)
        self.assertEqual(t.current_index(_at(23, 15)), 2)   # the snack
        self.assertEqual(t.current_index(_at(23, 45)), 0)   # …and back again

    def test_a_point_that_is_over_is_drawn_spent(self):
        """Not "still to come" because it stands below the line that has the
        accent — it happened, and the screen has to say so."""
        t = self._party()
        cur, spent = t.state(_at(22, 0))
        self.assertEqual(cur, 0)
        self.assertEqual(spent, {1})          # the dance, over
        cur, spent = t.state(_at(19, 45))
        self.assertEqual(cur, 1)
        self.assertEqual(spent, {0})          # the party, begun

    def test_an_end_past_midnight_belongs_to_the_same_evening(self):
        """"19:00 bis 01:00" runs six hours, not back eighteen."""
        t = self._party()
        self.assertEqual(t.current_index(_at(0, 30)), 0)
        self.assertEqual(t.current_index(_at(1, 30)), -1)

    def test_a_programme_without_ends_reads_as_it_always_did(self):
        """The column is optional; leaving it empty is the old behaviour."""
        t = _evening()
        self.assertEqual(t.current_index(_at(19, 15)), 1)
        self.assertEqual(t.current_index(_at(23, 59)), 2)
        cur, spent = t.state(_at(19, 15))
        self.assertEqual((cur, spent), (1, {0}))

    def test_an_end_survives_the_round_trip(self):
        t = self._party()
        back = Timetable.from_dict(t.as_dict())
        self.assertEqual([e.until for e in back.entries],
                         ["01:00", "19:50", "23:30"])

    def test_an_older_file_without_the_column_still_reads(self):
        back = Timetable.from_dict(
            {"entries": [{"time": "19:00", "what": "Party"}]})
        self.assertEqual(back.entries[0].until, "")
        self.assertEqual(back.current_index(_at(22, 0)), 0)


class UntilColumnTest(unittest.TestCase):
    """The Until column in the dialog — typed in, and read back out."""

    def _dlg(self, table=None):
        from player.timetable_dialog import TimetableDialog
        _app()
        dlg = TimetableDialog(table, None)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_an_end_that_was_saved_comes_back_into_the_grid(self):
        from player.timetable_dialog import _COL_UNTIL
        dlg = self._dlg(Timetable(entries=[
            Entry("19:00", "Tanzparty", "", until="01:00")]))
        self.assertEqual(dlg.table.item(0, _COL_UNTIL).text(), "01:00")
        self.assertEqual(dlg.timetable().entries[0].until, "01:00")

    def test_an_end_typed_into_the_grid_reaches_the_programme(self):
        from player.timetable_dialog import _COL_UNTIL, _COL_WHAT
        dlg = self._dlg(Timetable(entries=[Entry("19:00", "Tanzparty")]))
        dlg.table.item(0, _COL_UNTIL).setText("01:00")
        out = dlg.timetable()
        self.assertEqual(out.entries[0].until, "01:00")
        self.assertEqual(out.entries[0].what, "Tanzparty")
        # …and the columns did not get crossed on the way through.
        self.assertEqual(dlg.table.item(0, _COL_WHAT).text(), "Tanzparty")

    def test_the_example_programme_shows_what_the_column_is_for(self):
        """A first start has to teach the shape, or nobody finds it: the snack
        sits inside "Tanz frei", and hands the highlight back when it ends."""
        t = self._dlg().timetable()
        frei = [e for e in t.entries if e.what == "Tanz frei"][0]
        snack = [e for e in t.entries if e.what == "Mitternachtssnack"][0]
        self.assertEqual(frei.until, "01:00")
        self.assertEqual(snack.until, "23:30")
        self.assertEqual(t.entries.index(frei), t.current_index(_at(22, 0)))
        self.assertEqual(t.entries.index(snack), t.current_index(_at(23, 10)))
        self.assertEqual(t.entries.index(frei), t.current_index(_at(23, 40)))
