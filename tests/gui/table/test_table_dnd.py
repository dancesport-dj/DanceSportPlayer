#!/usr/bin/env python3
"""PlaylistTable drag & drop: what each drag source and drop target is offered.

Run:  py -m unittest tests.gui.table.test_table_dnd -v

`TableDragDropMixin` decides, per pixel of a drag and once more on the drop,
what a drag means on this table: a dance header reorders dances, a wishlist or
warm-up row reorders its list, a deck row moves or swaps slots, and a file
from outside replaces, inserts or builds. The drag events are stand-ins that
answer `source()`, `mimeData()`, `position()` and `modifiers()`; QDrag.exec,
which would block on a real drag, is a mock.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_table_dnd_"))

from PySide6.QtCore import QEvent, QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDragLeaveEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

import gui.table.table_dnd as dnd
from gui.table.playlist_table import PlaylistTable
from gui.table.table_host import TableHost
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_NO_MOD = Qt.KeyboardModifier.NoModifier
_CTRL = Qt.KeyboardModifier.ControlModifier
_SHIFT = Qt.KeyboardModifier.ShiftModifier
_COPY = Qt.DropAction.CopyAction
_MOVE = Qt.DropAction.MoveAction


def _e(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None)


class _Ev:
    """A drag/drop event as far as the mixin asks it anything."""

    def __init__(self, source=None, mime=None, y=0, mods=_NO_MOD):
        self._source = source
        self._mime = QMimeData() if mime is None else mime
        self._y = y
        self._mods = mods
        self.action = None
        self.accepted = None

    def source(self):
        return self._source

    def mimeData(self):
        return self._mime

    def position(self):
        return QPointF(5, self._y)

    def modifiers(self):
        return self._mods

    def setDropAction(self, action):
        self.action = action

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.accepted = False


class _NoModsEv(_Ev):
    def modifiers(self):
        raise RuntimeError("no modifiers on this event")


def _urls(*paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


class _Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="dp_table_dnd_"))
        cls.mp3 = cls.dir / "drop.mp3"
        cls.mp3_b = cls.dir / "drop_b.mp3"
        cls.mp3_c = cls.dir / "drop_c.mp3"
        cls.m3u = cls.dir / "Party.m3u"
        cls.txt = cls.dir / "notes.txt"
        for p in (cls.mp3, cls.mp3_b, cls.mp3_c, cls.txt):
            p.write_bytes(b"")
        cls.m3u.write_text("#EXTM3U\n", encoding="utf-8")
        cls.folder = cls.dir / "folder"
        cls.folder.mkdir()

    def table(self):
        t = PlaylistTable()
        t.resize(700, 900)
        self.addCleanup(reap_widget, t)
        return t

    def deck(self, playlist=None, heats=1, **kw):
        t = self.table()
        playlist = playlist or {
            "Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
            "Finale": [[_e("LW", 3), _e("TG", 4)]],
        }
        rounds = [RoundConfig(name=n, heats=heats, tier="final") for n in playlist]
        t.load(playlist, ["LW", "TG"], rounds, "S",
               play_cb=lambda *a: None, suggester=None, use_timbre=False, **kw)
        return t

    def wishlist(self, *entries):
        t = self.table()
        t.load_wishlist(list(entries) or [_e("LW", 1), _e("TG", 2), _e("SF", 3)],
                        play_cb=lambda *a: None, suggester=None)
        return t

    def warmup(self):
        t = self.table()
        t.load_warmup([_e("LW", 1), _e("TG", 2), _e("SF", 3)], "Eintanzen",
                      style="", dance_class="S", relax=True,
                      play_cb=lambda *a: None, suggester=None)
        return t

    @staticmethod
    def row_of(t, title):
        return next(r for r, m in t._row_meta.numbered()
                    if m.entry is not None and m.entry.title == title)

    @staticmethod
    def y_of(t, row):
        return t.rowViewportPosition(row) + 2

    def ev(self, t, row=None, y=None, **kw):
        if y is None:
            y = self.y_of(t, row) if row is not None else 0
        return _Ev(y=y, **kw)

    def patch(self, target, name, **kw):
        patcher = mock.patch.object(target, name, **kw)
        found = patcher.start()
        self.addCleanup(patcher.stop)
        return found

    def toasts(self):
        return self.patch(dnd, "_show_toast")

    def hdr_row(self, t, dance):
        return next(r for r, d in t._dance_hdr_dance.items() if d == dance)


class DanceHeaderDragTest(_Base):

    def _mouse(self, kind, y, buttons=Qt.MouseButton.LeftButton):
        pos = QPointF(5, y)
        return QMouseEvent(kind, pos, pos, Qt.MouseButton.LeftButton, buttons, _NO_MOD)

    def test_a_press_on_a_dance_header_then_a_long_enough_move_starts_the_drag(self):
        t = self.deck()
        start = self.patch(t, "_start_dance_drag")
        y = self.y_of(t, self.hdr_row(t, "TG"))
        t.mousePressEvent(self._mouse(QEvent.Type.MouseButtonPress, y))
        self.assertIsNotNone(t._hdr_press)
        t.mouseMoveEvent(self._mouse(QEvent.Type.MouseMove, y + 1))
        start.assert_not_called()                # still under the drag distance
        t.mouseMoveEvent(self._mouse(QEvent.Type.MouseMove,
                                     y + QApplication.startDragDistance() + 5))
        start.assert_called_once_with("TG")
        self.assertIsNone(t._hdr_press)

    def test_release_forgets_the_press(self):
        t = self.deck()
        y = self.y_of(t, self.hdr_row(t, "LW"))
        t.mousePressEvent(self._mouse(QEvent.Type.MouseButtonPress, y))
        t.mouseReleaseEvent(self._mouse(QEvent.Type.MouseButtonRelease, y,
                                        Qt.MouseButton.NoButton))
        self.assertIsNone(t._hdr_press)

    def test_the_dance_drag_carries_the_dance_and_cleans_up(self):
        t = self.deck()
        drag_cls = self.patch(dnd, "QDrag")
        seen = []
        drag_cls.return_value.exec.side_effect = lambda *a: seen.append(t._dance_drag)
        t._show_drop_row(self.row_of(t, "LW 1"))
        t._start_dance_drag("LW")
        mime = drag_cls.return_value.setMimeData.call_args.args[0]
        self.assertEqual(bytes(mime.data("application/x-dancesport-dance").data()), b"LW")
        drag_cls.return_value.exec.assert_called_once_with(_MOVE)
        self.assertEqual(seen, ["LW"])
        self.assertIsNone(t._dance_drag)
        self.assertTrue(t._drop_row_hl.isHidden())


class StartDragTest(_Base):

    def test_the_selected_tracks_go_out_as_file_urls_and_text(self):
        t = self.deck()
        drag_cls = self.patch(dnd, "QDrag")
        seen = []
        drag_cls.return_value.exec.side_effect = lambda *a: seen.append(list(t._drag_src_rows))
        row = self.row_of(t, "TG 2")
        t.selectRow(row)
        t.startDrag(_COPY)
        mime = drag_cls.return_value.setMimeData.call_args.args[0]
        self.assertEqual([Path(u.toLocalFile()) for u in mime.urls()],
                         [Path(r"C:\music\TG2.mp3")])
        self.assertEqual(Path(mime.text()), Path(r"C:\music\TG2.mp3"))
        self.assertEqual(seen, [[row]])
        self.assertEqual(t._drag_src_rows, [])

    def test_without_a_selection_the_current_row_is_dragged(self):
        t = self.deck()
        drag_cls = self.patch(dnd, "QDrag")
        row = self.row_of(t, "LW 3")
        t.selectionModel().setCurrentIndex(
            t.model().index(row, 0), t.selectionModel().SelectionFlag.NoUpdate)
        t.clearSelection()
        t.startDrag(_COPY)
        mime = drag_cls.return_value.setMimeData.call_args.args[0]
        self.assertEqual(Path(mime.text()), Path(r"C:\music\LW3.mp3"))

    def test_a_header_row_alone_drags_nothing(self):
        t = self.deck()
        drag_cls = self.patch(dnd, "QDrag")
        t.selectionModel().setCurrentIndex(
            t.model().index(self.hdr_row(t, "LW"), 0),
            t.selectionModel().SelectionFlag.NoUpdate)
        t.clearSelection()
        t.startDrag(_COPY)
        drag_cls.assert_not_called()


class DroppedPathTest(_Base):

    def test_a_path_inside_a_serialized_payload_is_found(self):
        t = self.table()
        mime = QMimeData()
        mime.setData("application/x-java-serialized-object",
                     b"\xac\xed\x00\x05t\x00" + str(self.mp3).encode("utf-8") + b"\x00x")
        self.assertEqual(t._path_from_raw_mime(mime), self.mp3)

    def test_a_raw_path_to_a_missing_file_is_no_path(self):
        mime = QMimeData()
        mime.setData("application/x-other", b"C:\\nowhere\\gone.mp3")
        self.assertIsNone(self.table()._path_from_raw_mime(mime))

    def test_no_payload_or_an_unreadable_format_is_no_path(self):
        t = self.table()
        self.assertIsNone(t._path_from_raw_mime(None))
        broken = mock.Mock()
        broken.formats.return_value = ["x/broken"]
        broken.data.side_effect = RuntimeError("gone")
        self.assertIsNone(t._path_from_raw_mime(broken))

    def test_blank_or_quoted_blank_strings_are_no_path(self):
        t = self.table()
        self.assertIsNone(t._coerce_audio_path(""))
        self.assertIsNone(t._coerce_audio_path("  ''  "))
        self.assertIsNone(t._coerce_audio_path(str(self.txt)))
        self.assertEqual(t._coerce_audio_path(QUrl.fromLocalFile(str(self.mp3)).toString()),
                         self.mp3)

    def test_the_text_payload_is_read_line_by_line(self):
        t = self.table()
        mime = QMimeData()
        mime.setText(f"not a path\n{self.mp3}")
        self.assertEqual(t._droppable_path(_Ev(mime=mime)), self.mp3)

    def test_an_event_without_mime_data_carries_nothing(self):
        ev = _Ev()
        ev._mime = None
        self.assertIsNone(self.table()._droppable_path(ev))

    def test_a_file_or_a_folder_is_droppable_on_a_deck(self):
        t = self.table()
        self.assertTrue(t._has_droppable(_Ev(mime=_urls(self.mp3))))
        self.assertTrue(t._has_droppable(_Ev(mime=_urls(self.folder))))
        self.assertFalse(t._has_droppable(_Ev(mime=_urls(self.txt))))


class DropRowTest(_Base):

    def test_below_the_last_row_snaps_to_the_nearest_visible_row(self):
        t = self.deck()
        last = t.rowCount() - 1
        far = t.rowViewportPosition(last) + t.rowHeight(last) * 20
        self.assertEqual(t._dynamic_drop_row(_Ev(y=far)), last)
        t.setRowHidden(last, True)
        self.assertEqual(t._dynamic_drop_row(_Ev(y=far)), last - 1)

    def test_an_empty_grid_has_no_row(self):
        self.assertEqual(self.table()._dynamic_drop_row(_Ev(y=50)), -1)

    def test_a_drag_of_only_header_rows_has_no_source(self):
        t = self.deck()
        t._drag_src_rows = [self.hdr_row(t, "LW"), 999]
        self.assertIsNone(t._internal_drag_src())

    def test_the_dance_under_a_row(self):
        t = self.deck()
        self.assertEqual(t._dance_at_row(self.hdr_row(t, "TG")), "TG")
        self.assertEqual(t._dance_at_row(self.row_of(t, "LW 3")), "LW")
        round_hdr = next(r for r in range(t.rowCount())
                         if t._row_meta[r] is None and r not in t._dance_hdr_rows)
        self.assertIsNone(t._dance_at_row(round_hdr))


class DragEnterTest(_Base):

    def test_a_dance_header_drag_is_a_move(self):
        t = self.deck()
        t._dance_drag = "LW"
        ev = _Ev(source=t)
        t.dragEnterEvent(ev)
        self.assertEqual((ev.accepted, ev.action), (True, _MOVE))

    def test_a_wishlist_reorder_is_offered_as_copy(self):
        t = self.wishlist()
        t._drag_src_rows = [0]
        ev = _Ev(source=t)
        t.dragEnterEvent(ev)
        self.assertEqual((ev.accepted, ev.action), (True, _COPY))

    def test_a_deck_slot_move_needs_a_song_row(self):
        t = self.deck()
        t._drag_src_rows = [self.row_of(t, "LW 1")]
        ev = _Ev(source=t)
        t.dragEnterEvent(ev)
        self.assertTrue(ev.accepted)
        t._drag_src_rows = [self.hdr_row(t, "LW")]
        ev = _Ev(source=t)
        t.dragEnterEvent(ev)
        self.assertFalse(ev.accepted)

    def test_a_wishlist_takes_files_but_not_other_things(self):
        t = self.wishlist()
        ok, bad = _Ev(mime=_urls(self.mp3)), _Ev(mime=_urls(self.txt))
        t.dragEnterEvent(ok)
        t.dragEnterEvent(bad)
        self.assertEqual((ok.accepted, bad.accepted), (True, False))

    def test_a_deck_takes_an_outside_track_but_not_other_things(self):
        t = self.deck()
        ok, bad = _Ev(mime=_urls(self.mp3)), _Ev(mime=_urls(self.txt))
        t.dragEnterEvent(ok)
        t.dragEnterEvent(bad)
        self.assertEqual((ok.accepted, ok.action, bad.accepted), (True, _COPY, False))


class DropMarkerTest(_Base):

    def test_the_gap_line_below_the_last_row_and_on_an_empty_table(self):
        t = self.deck()
        n = t.rowCount()
        t._show_drop_line(n)
        self.assertEqual(t._drop_line.y(),
                         t.rowViewportPosition(n - 1) + t.rowHeight(n - 1) - 1)
        self.assertFalse(t._drop_line.isHidden())
        self.assertTrue(t._drop_row_hl.isHidden())
        empty = self.table()
        empty._show_drop_line(0)
        self.assertEqual(empty._drop_line.y(), 0)

    def test_a_row_highlight_out_of_range_clears_the_markers(self):
        t = self.deck()
        t._show_drop_line(1)
        t._show_drop_row(t.rowCount() + 3)
        self.assertTrue(t._drop_line.isHidden())
        self.assertTrue(t._drop_row_hl.isHidden())
        t._show_drop_row(1)
        self.assertFalse(t._drop_row_hl.isHidden())
        self.assertTrue(t._drop_line.isHidden())

    def test_modifiers_fall_back_to_the_keyboard_state(self):
        t = self.table()
        with mock.patch.object(QApplication, "keyboardModifiers", return_value=_CTRL):
            self.assertTrue(t._drop_ctrl(_NoModsEv()))
            self.assertFalse(t._drop_shift(_NoModsEv()))

    def test_drag_leave_stops_the_scroll_and_hides_the_markers(self):
        t = self.deck()
        t._show_drop_line(1)
        t._autoscroll_dir = 1
        t._autoscroll_timer.start()
        t.dragLeaveEvent(QDragLeaveEvent())
        self.assertEqual(t._autoscroll_dir, 0)
        self.assertFalse(t._autoscroll_timer.isActive())
        self.assertTrue(t._drop_line.isHidden())


class AutoscrollTest(_Base):

    def setUp(self):
        self.t = self.deck()
        self.patch(self.t, "viewport", return_value=SimpleNamespace(height=lambda: 400))

    def test_the_top_edge_scrolls_up_faster_the_closer_it_gets(self):
        self.t._update_drag_autoscroll(_Ev(y=30))
        slow = self.t._autoscroll_speed
        self.assertEqual(self.t._autoscroll_dir, -1)
        self.assertTrue(self.t._autoscroll_timer.isActive())
        self.t._update_drag_autoscroll(_Ev(y=0))
        self.assertEqual(self.t._autoscroll_speed, self.t._AUTOSCROLL_MAX_PX)
        self.assertLess(slow, self.t._AUTOSCROLL_MAX_PX)

    def test_the_bottom_edge_scrolls_down_and_the_middle_stops(self):
        self.t._update_drag_autoscroll(_Ev(y=395))
        self.assertEqual(self.t._autoscroll_dir, 1)
        self.t._update_drag_autoscroll(_Ev(y=200))
        self.assertEqual(self.t._autoscroll_dir, 0)
        self.assertFalse(self.t._autoscroll_timer.isActive())

    def test_a_tick_moves_the_scrollbar_by_the_speed(self):
        bar = mock.Mock()
        bar.value.return_value = 10
        self.patch(self.t, "verticalScrollBar", return_value=bar)
        self.t._autoscroll_dir, self.t._autoscroll_speed = 1, 6
        self.t._drag_autoscroll()
        bar.setValue.assert_called_once_with(16)

    def test_a_tick_without_a_direction_stops_the_timer(self):
        self.t._autoscroll_timer.start()
        self.t._autoscroll_dir = 0
        self.t._drag_autoscroll()
        self.assertFalse(self.t._autoscroll_timer.isActive())


class DragMoveInternalTest(_Base):

    def test_a_dance_drag_over_another_dance_highlights_its_header(self):
        t = self.deck()
        t._dance_drag = "LW"
        ev = self.ev(t, self.row_of(t, "TG 4"), source=t)
        t.dragMoveEvent(ev)
        self.assertEqual((ev.accepted, ev.action), (True, _MOVE))
        self.assertEqual(t._drop_row_hl.y(),
                         t.rowViewportPosition(t._row_dance_hdr[self.row_of(t, "TG 4")]))

    def test_a_dance_drag_over_its_own_dance_is_refused(self):
        t = self.deck()
        t._dance_drag = "LW"
        ev = self.ev(t, self.row_of(t, "LW 3"), source=t)
        t.dragMoveEvent(ev)
        self.assertFalse(ev.accepted)

    def test_a_wishlist_reorder_shows_a_gap_or_with_ctrl_a_row(self):
        t = self.wishlist()
        t._drag_src_rows = [0]
        ev = self.ev(t, 2, source=t)
        t.dragMoveEvent(ev)
        self.assertTrue(ev.accepted)
        self.assertFalse(t._drop_line.isHidden())
        ev = self.ev(t, 2, source=t, mods=_CTRL)
        t.dragMoveEvent(ev)
        self.assertFalse(t._drop_row_hl.isHidden())
        self.assertTrue(t._drop_line.isHidden())

    def test_a_slot_move_takes_the_same_dance_only(self):
        t = self.deck()
        t._drag_src_rows = [self.row_of(t, "LW 1")]
        ok = self.ev(t, self.row_of(t, "LW 3"), source=t)
        bad = self.ev(t, self.row_of(t, "TG 4"), source=t)
        t.dragMoveEvent(ok)
        t.dragMoveEvent(bad)
        self.assertEqual((ok.accepted, bad.accepted), (True, False))


class DragMoveExternalTest(_Base):

    def test_a_wishlist_shows_the_gap_for_files_and_refuses_the_rest(self):
        t = self.wishlist()
        ok = self.ev(t, 1, mime=_urls(self.mp3))
        bad = self.ev(t, 1, mime=_urls(self.txt))
        t.dragMoveEvent(ok)
        self.assertFalse(t._drop_line.isHidden())
        t.dragMoveEvent(bad)
        self.assertEqual((ok.accepted, bad.accepted), (True, False))
        self.assertTrue(t._drop_line.isHidden())

    def test_an_empty_deck_builds_where_the_drop_can_go_dynamic(self):
        t = self.table()
        can = self.patch(t, "_can_dynamic_drop", return_value=True)
        ev = _Ev(mime=_urls(self.mp3), y=5)
        t.dragMoveEvent(ev)
        self.assertTrue(ev.accepted)
        self.assertTrue(t._drop_row_hl.isHidden())
        can.return_value = False
        ev = _Ev(mime=_urls(self.mp3), y=5)
        t.dragMoveEvent(ev)
        self.assertFalse(ev.accepted)

    def test_a_dynamic_deck_highlights_the_slot_it_snaps_to(self):
        t = self.deck(dynamic=True, capacity=[1, 1])
        self.patch(t, "_can_dynamic_drop", return_value=True)
        row = self.row_of(t, "TG 2")
        t.dragMoveEvent(self.ev(t, row, mime=_urls(self.mp3)))
        self.assertEqual(t._drop_row_hl.y(), t.rowViewportPosition(row))

    def test_the_warmup_list_inserts_or_with_shift_replaces(self):
        t = self.warmup()
        row = self.row_of(t, "TG 2")
        ev = self.ev(t, row, mime=_urls(self.mp3))
        t.dragMoveEvent(ev)
        self.assertTrue(ev.accepted)
        self.assertFalse(t._drop_line.isHidden())
        ev = self.ev(t, row, mime=_urls(self.mp3), mods=_SHIFT)
        t.dragMoveEvent(ev)
        self.assertFalse(t._drop_row_hl.isHidden())
        ev = self.ev(t, row, mime=_urls(self.txt))
        t.dragMoveEvent(ev)
        self.assertFalse(ev.accepted)

    def test_a_static_deck_takes_a_track_on_a_slot_not_on_a_header(self):
        t = self.deck()
        ok = self.ev(t, self.row_of(t, "LW 1"), mime=_urls(self.mp3))
        bad = self.ev(t, self.hdr_row(t, "LW"), mime=_urls(self.mp3))
        t.dragMoveEvent(ok)
        t.dragMoveEvent(bad)
        self.assertEqual((ok.accepted, bad.accepted), (True, False))


class DropInternalTest(_Base):

    def test_a_dance_drop_on_another_dance_reorders(self):
        t = self.deck()
        reorder = self.patch(t, "_reorder_dance")
        t._dance_drag = "LW"
        ev = self.ev(t, self.row_of(t, "TG 2"), source=t)
        t.dropEvent(ev)
        self.assertTrue(ev.accepted)
        reorder.assert_called_once_with("LW", "TG")
        ev = self.ev(t, self.row_of(t, "LW 3"), source=t)
        t.dropEvent(ev)
        self.assertFalse(ev.accepted)

    def test_a_wishlist_reorder_runs_on_the_next_tick(self):
        t = self.wishlist()
        calls = []
        self.patch(t, "_reorder_flat",
                   side_effect=lambda idx: calls.append(("flat", idx, t._drag_src_rows)))
        self.patch(t, "_swap_reorder",
                   side_effect=lambda row: calls.append(("swap", row, t._drag_src_rows)))
        t._drag_src_rows = [0]
        t.dropEvent(self.ev(t, 2, source=t))
        t._drag_src_rows = [1]
        t.dropEvent(self.ev(t, 2, source=t, mods=_CTRL))
        self.assertEqual(calls, [])
        _app.processEvents()
        self.assertEqual([c[0] for c in calls], ["flat", "swap"])
        self.assertEqual(calls[0][2], [0])
        self.assertEqual(calls[1][1:], (2, [1]))
        self.assertEqual(t._drag_src_rows, [])

    def test_a_warmup_reorder_uses_its_own_reorder(self):
        t = self.warmup()
        reorder = self.patch(t, "_reorder_warmup")
        t._drag_src_rows = [self.row_of(t, "LW 1")]
        t.dropEvent(self.ev(t, self.row_of(t, "SF 3"), source=t))
        _app.processEvents()
        reorder.assert_called_once()

    def test_one_slot_moves_alone_several_move_as_a_block(self):
        t = self.deck(playlist={
            "Vorrunde": [[_e("LW", 1), _e("TG", 1)], [_e("LW", 2), _e("TG", 2)]],
            "Finale": [[_e("LW", 3), _e("TG", 3)], [_e("LW", 4), _e("TG", 4)]],
        }, heats=2)
        single = self.patch(t, "_move_or_swap_rows")
        block = self.patch(t, "_move_rows_block")
        src, dst = self.row_of(t, "LW 1"), self.row_of(t, "LW 3")
        t._drag_src_rows = [src]
        ev = self.ev(t, dst, source=t)
        t.dropEvent(ev)
        single.assert_called_once_with(src, dst)
        both = [src, self.row_of(t, "LW 2")]
        t._drag_src_rows = both
        t.dropEvent(self.ev(t, dst, source=t))
        block.assert_called_once_with(both, dst)
        t._drag_src_rows = [src]
        ev = self.ev(t, self.row_of(t, "TG 3"), source=t)
        t.dropEvent(ev)
        self.assertFalse(ev.accepted)


class DropOnWishlistTest(_Base):

    def setUp(self):
        self.toast = self.toasts()
        self.clean = self.patch(TableHost, "clean_wishlist_against_playlists", return_value=0)

    def test_nothing_droppable_is_refused(self):
        t = self.wishlist()
        ev = _Ev(mime=_urls(self.txt))
        t.dropEvent(ev)
        self.assertFalse(ev.accepted)

    def test_a_playlist_on_an_empty_wishlist_names_it(self):
        t = self.wishlist()
        t.load_wishlist([], play_cb=None, suggester=None)
        self.patch(t, "_insert_drop_files", return_value=2)
        named = self.patch(TableHost, "name_after_playlist")
        t.dropEvent(_Ev(mime=_urls(self.m3u)))
        named.assert_called_once_with("Party")
        self.assertIn("Added 2 track(s)", self.toast.call_args.args[1])

    def test_from_another_wishlist_is_a_move_and_the_list_is_cleaned(self):
        t, other = self.wishlist(), self.wishlist()
        other._drag_src_rows = [0]
        remove = self.patch(other, "_remove_rows", return_value=True)
        self.patch(t, "_insert_drop_files", return_value=1)
        self.clean.return_value = 3
        t.dropEvent(_Ev(source=other, mime=_urls(self.mp3)))
        remove.assert_called_once_with([0], select_after=True)
        msg = self.toast.call_args.args[1]
        self.assertIn("Moved 1 track(s)", msg)
        self.assertIn("3 already in a playlist removed", msg)

    def test_from_a_deck_its_slot_is_emptied_and_no_clean_runs(self):
        t, deck = self.wishlist(), self.deck()
        deck._drag_src_rows = [self.row_of(deck, "LW 1")]
        clear = self.patch(deck, "_clear_slots_at", return_value=True)
        self.patch(t, "_insert_drop_files", return_value=1)
        t.dropEvent(_Ev(source=deck, mime=_urls(self.mp3)))
        clear.assert_called_once_with({self.row_of(deck, "LW 1")}, select_after=True)
        self.clean.assert_not_called()

    def test_from_a_warmup_list_the_title_leaves_it_without_a_hole(self):
        """No grid stands behind a warm-up list: an emptied row there is a
        "⚠ No song found" hole nothing fills, gone again at the next edit."""
        t, warm = self.wishlist(), self.warmup()
        warm._drag_src_rows = [self.row_of(warm, "TG 2")]
        self.patch(t, "_insert_drop_files", return_value=1)
        t.dropEvent(_Ev(source=warm, mime=_urls(self.mp3)))
        self.assertEqual([m.entry.title for _r, m in warm._row_meta.numbered()],
                         ["LW 1", "SF 3"])
        self.assertTrue(all(m.entry is not None
                            for m in warm._row_meta if m and not m.theme
                            and m.dance), "an emptied row is left in the list")
        self.assertIn("Moved 1 track(s)", self.toast.call_args.args[1])

    def test_ctrl_copies_from_another_wishlist(self):
        t, other = self.wishlist(), self.wishlist()
        other._drag_src_rows = [0]
        remove = self.patch(other, "_remove_rows")
        self.patch(t, "_insert_drop_files", return_value=1)
        t.dropEvent(_Ev(source=other, mime=_urls(self.mp3), mods=_CTRL))
        remove.assert_not_called()
        self.assertIn("Added 1 track(s)", self.toast.call_args.args[1])

    def test_only_duplicates_say_so(self):
        t = self.wishlist()
        self.patch(t, "_insert_drop_files", return_value=0)
        t.dropEvent(_Ev(mime=_urls(self.mp3)))
        self.assertIn("nothing added", self.toast.call_args.args[1])
        self.clean.return_value = 2
        t.dropEvent(_Ev(mime=_urls(self.mp3)))
        self.assertIn("Removed 2 track(s) already in a playlist", self.toast.call_args.args[1])


class DropOnDeckTest(_Base):

    def setUp(self):
        self.toast = self.toasts()

    def test_an_empty_deck_builds_from_the_drop(self):
        t = self.table()
        self.patch(t, "_can_dynamic_drop", return_value=True)
        build = self.patch(t, "_dynamic_drop")
        move = self.patch(t, "_move_from_drag_source")
        self.patch(t, "_planned_keys", return_value={"k"})
        ev = _Ev(mime=_urls(self.mp3), y=5, mods=_CTRL)
        t.dropEvent(ev)
        self.assertTrue(ev.accepted)
        build.assert_called_once_with(ev, -1, replace=True)
        move.assert_called_once_with(ev, pre_planned={"k"})

    def test_an_empty_deck_refuses_what_cannot_go_dynamic(self):
        t = self.table()
        self.patch(t, "_can_dynamic_drop", return_value=False)
        build = self.patch(t, "_dynamic_drop")
        ev = _Ev(mime=_urls(self.mp3), y=5)
        t.dropEvent(ev)
        self.assertFalse(ev.accepted)
        build.assert_not_called()

    def test_a_playlist_without_a_loader_is_refused(self):
        t = self.deck()
        ev = self.ev(t, self.row_of(t, "LW 1"), mime=_urls(self.m3u))
        t.dropEvent(ev)
        self.assertFalse(ev.accepted)

    def test_several_tracks_fill_the_free_slots_and_say_what_was_skipped(self):
        t = self.deck()
        row = self.row_of(t, "LW 1")
        self.patch(t, "_replace_row_with_path", return_value=True)
        fill = self.patch(t, "_fill_empty_slots_with", return_value=[row + 3])
        move = self.patch(t, "_move_from_drag_source")
        marks = self.patch(t, "_mark_drop_issues")
        ev = self.ev(t, row, mime=_urls(self.mp3, self.mp3_b, self.mp3_c))
        t.dropEvent(ev)
        self.assertTrue(ev.accepted)
        fill.assert_called_once_with([self.mp3_b, self.mp3_c], row + 1)
        msg = self.toast.call_args.args[1]
        self.assertIn("Placed 2 track(s)", msg)
        self.assertIn("1 skipped", msg)
        move.assert_called_once()
        _app.processEvents()
        marks.assert_called_once_with([row, row + 3])

    def test_a_drop_beside_the_grid_is_refused(self):
        t = self.deck()
        ev = _Ev(mime=_urls(self.mp3), y=t.rowViewportPosition(t.rowCount() - 1) * 50)
        t.dropEvent(ev)
        self.assertFalse(ev.accepted)


class DropOnWarmupTest(_Base):

    def setUp(self):
        self.toast = self.toasts()
        self.t = self.warmup()
        self.move = self.patch(self.t, "_move_from_drag_source")

    def test_a_wish_is_inserted_and_the_rounds_recut(self):
        insert = self.patch(self.t, "_insert_warmup_files", return_value=1)
        row = self.row_of(self.t, "TG 2")
        ev = self.ev(self.t, row, mime=_urls(self.mp3))
        self.t.dropEvent(ev)
        self.assertTrue(ev.accepted)
        insert.assert_called_once_with([self.mp3], self.t._drop_index(ev))
        self.move.assert_called_once()
        self.assertIn("rounds re-cut", self.toast.call_args.args[1])

    def test_a_running_order_just_adds(self):
        self.patch(self.t, "_insert_warmup_files", return_value=1)
        self.t._player_list = True
        self.t.dropEvent(self.ev(self.t, 1, mime=_urls(self.mp3)))
        self.assertNotIn("rounds re-cut", self.toast.call_args.args[1])

    def test_a_wish_already_there_adds_nothing(self):
        self.patch(self.t, "_insert_warmup_files", return_value=0)
        self.t.dropEvent(self.ev(self.t, 1, mime=_urls(self.mp3)))
        self.assertIn("nothing added", self.toast.call_args.args[1])
        self.move.assert_not_called()

    def test_nothing_to_insert_is_refused(self):
        ev = self.ev(self.t, 1, mime=_urls(self.txt))
        self.t.dropEvent(ev)
        self.assertFalse(ev.accepted)


class FillAndMarkTest(_Base):

    def test_extra_tracks_go_into_the_first_free_slot_of_their_dance(self):
        t = self.deck(playlist={
            "Vorrunde": [[_e("LW", 1), None]],
            "Finale": [[None, _e("TG", 4)]],
        })
        tg_free = next(r for r, m in enumerate(t._row_meta)
                       if m and m.entry is None and m.dance == "TG")
        lw_free = next(r for r, m in enumerate(t._row_meta)
                       if m and m.entry is None and m.dance == "LW")
        self.patch(t, "_entries_for_paths",
                   return_value=[_e("TG", 9), _e("LW", 9), _e("SF", 9)])
        replace = self.patch(t, "_replace_row_with_path", return_value=True)
        # Scanning starts below the Finale LW slot, so the TG slot above is
        # reached by wrapping round to the top.
        placed = t._fill_empty_slots_with([self.mp3, self.mp3_b, self.mp3_c], lw_free + 1)
        self.assertEqual(placed, [tg_free, lw_free])
        self.assertEqual(replace.call_count, 2)

    def test_the_issue_toast_is_deduplicated_and_capped(self):
        t = self.deck()
        self.patch(t, "refresh_issue_marks", return_value={
            1: ["shared", "a", "b", "c"], 2: ["shared", "d", "e", "f", "g"]})
        toast = self.toasts()
        t._mark_drop_issues([1, 2])
        text = toast.call_args.args[1]
        self.assertEqual(text.count("shared"), 1)
        self.assertIn("plus 2 more", text)

    def test_no_issues_no_toast(self):
        t = self.deck()
        self.patch(t, "refresh_issue_marks", return_value={})
        toast = self.toasts()
        t._mark_drop_issues([1])
        toast.assert_not_called()


class ReplaceRowTest(_Base):

    def setUp(self):
        self.info = self.patch(QMessageBox, "information")
        self.question = self.patch(QMessageBox, "question", return_value=QMessageBox.StandardButton.No)
        self.critical = self.patch(QMessageBox, "critical")

    def suggest(self, t, entry):
        sugg = mock.Mock()
        sugg.lib.entry_for.return_value = entry
        t._suggester = sugg
        return sugg

    def test_a_header_row_is_not_replaced(self):
        t = self.deck()
        self.assertFalse(t._replace_row_with_path(self.hdr_row(t, "LW"), self.mp3))

    def test_an_unreadable_file_says_so(self):
        t = self.deck()
        self.assertFalse(t._replace_row_with_path(self.row_of(t, "LW 1"), self.mp3))
        self.assertIn("drop.mp3", self.info.call_args.args[2])

    def test_another_dance_is_asked_about(self):
        t = self.deck()
        self.suggest(t, _e("TG", 9))
        row = self.row_of(t, "LW 1")
        self.assertFalse(t._replace_row_with_path(row, self.mp3))
        self.assertIn("TG 9", self.question.call_args.args[2])
        self.question.return_value = QMessageBox.StandardButton.Yes
        self.assertTrue(t._replace_row_with_path(row, self.mp3))
        self.assertEqual(t._playlist["Vorrunde"][0][0].title, "TG 9")

    def test_replacing_the_playing_row_keeps_it_playing(self):
        t = self.deck()
        self.suggest(t, _e("LW", 9))
        played = []
        t._play_cb = played.append
        row = self.row_of(t, "LW 1")
        t._current_play_row = row
        self.assertTrue(t._replace_row_with_path(row, self.mp3))
        self.assertEqual(played, [])
        self.assertEqual(t._current_play_row, row)
        _app.processEvents()
        self.assertEqual(t._row_meta[row].entry.title, "LW 9")

    def test_a_failure_is_reported(self):
        t = self.deck()
        self.patch(t, "_entry_for", side_effect=RuntimeError("tags broken"))
        self.assertFalse(t._replace_row_with_path(self.row_of(t, "LW 1"), self.mp3))
        self.assertEqual(self.critical.call_args.args[2], "tags broken")


class ReorderDanceTest(_Base):

    def test_an_unknown_dance_changes_nothing(self):
        t = self.deck()
        load = self.patch(t, "load")
        t._reorder_dance("SF", "LW")
        load.assert_not_called()

    def test_a_dynamic_deck_rebuilds_and_carries_its_backups_along(self):
        t = self.deck(dynamic=True, capacity=[1, 1])
        rebuild = self.patch(t, "_rebuild_dynamic")
        t._dynamic_backups = {("Vorrunde", 0, 0): ["lw backup"]}
        t._reorder_dance("LW", "TG")
        self.assertEqual(t._dynamic_dances, ["TG", "LW"])
        self.assertEqual(t._dynamic_backups, {("Vorrunde", 0, 1): ["lw backup"]})
        self.assertEqual([e.title for e in t._playlist["Vorrunde"][0]], ["TG 2", "LW 1"])
        rebuild.assert_called_once()


class MoveOrSwapTest(_Base):

    def setUp(self):
        self.info = self.patch(QMessageBox, "information")
        self.critical = self.patch(QMessageBox, "critical")

    def test_two_slots_of_a_dance_swap_their_tracks(self):
        t = self.deck()
        src, dst = self.row_of(t, "LW 1"), self.row_of(t, "LW 3")
        t._use_timbre = True
        sugg = t._suggester = mock.Mock()
        t._current_play_row = src
        glyph = self.patch(t, "sync_play_glyph")
        t._move_or_swap_rows(src, dst)
        self.assertEqual(t._playlist["Vorrunde"][0][0].title, "LW 3")
        self.assertEqual(t._playlist["Finale"][0][0].title, "LW 1")
        self.assertEqual(sugg.set_similarity.call_count, 2)
        t._use_timbre, t._suggester = False, None   # the redraw reads real scores
        _app.processEvents()
        self.assertEqual(t.currentRow(), dst)
        glyph.assert_called_once()

    def test_a_move_into_an_empty_slot_leaves_the_source_empty(self):
        t = self.deck(playlist={"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                                "Finale": [[None, _e("TG", 4)]]})
        src = self.row_of(t, "LW 1")
        dst = next(r for r, m in enumerate(t._row_meta)
                   if m and m.entry is None and m.dance == "LW")
        t._move_or_swap_rows(src, dst)
        self.assertIsNone(t._playlist["Vorrunde"][0][0])
        self.assertEqual(t._playlist["Finale"][0][0].title, "LW 1")

    def test_nothing_to_move(self):
        t = self.deck(playlist={"Vorrunde": [[None, _e("TG", 2)]],
                                "Finale": [[_e("LW", 3), _e("TG", 4)]]})
        before = [list(h) for h in t._playlist["Finale"]]
        lw = self.row_of(t, "LW 3")
        empty = next(r for r, m in enumerate(t._row_meta) if m and m.entry is None)
        t._move_or_swap_rows(lw, lw)
        t._move_or_swap_rows(self.hdr_row(t, "LW"), lw)
        t._move_or_swap_rows(empty, lw)
        self.assertEqual(t._playlist["Finale"], before)

    def test_another_dance_is_explained_not_moved(self):
        t = self.deck()
        t._move_or_swap_rows(self.row_of(t, "LW 1"), self.row_of(t, "TG 4"))
        self.assertIn("can only move", self.info.call_args.args[2])
        self.assertEqual(t._playlist["Vorrunde"][0][0].title, "LW 1")

    def test_a_failure_is_reported(self):
        t = self.deck()
        self.patch(t._row_meta, "swap", side_effect=RuntimeError("grid broken"))
        t._move_or_swap_rows(self.row_of(t, "LW 1"), self.row_of(t, "LW 3"))
        self.assertEqual(self.critical.call_args.args[1:], ("Move Error", "grid broken"))


class MoveBlockTest(_Base):

    def setUp(self):
        self.critical = self.patch(QMessageBox, "critical")
        self.t = self.deck(playlist={
            "Vorrunde": [[_e("LW", 1), _e("TG", 1)], [_e("LW", 2), _e("TG", 2)]],
            "Finale": [[_e("LW", 3), _e("TG", 3)], [_e("LW", 4), _e("TG", 4)]],
        }, heats=2)

    def titles(self, rn):
        return [[e.title for e in h] for h in self.t._playlist[rn]]

    def test_a_block_keeps_its_heat_offsets(self):
        t = self.t
        t._use_timbre = True
        sugg = t._suggester = mock.Mock()
        t._move_rows_block([self.row_of(t, "LW 1"), self.row_of(t, "LW 2")],
                           self.row_of(t, "LW 3"))
        self.assertEqual(self.titles("Vorrunde"), [["LW 3", "TG 1"], ["LW 4", "TG 2"]])
        self.assertEqual(self.titles("Finale"), [["LW 1", "TG 3"], ["LW 2", "TG 4"]])
        self.assertEqual(sugg.set_similarity.call_count, 4)

    def test_a_block_that_would_run_off_the_round_moves_what_fits(self):
        t = self.t
        t._move_rows_block([self.row_of(t, "LW 1"), self.row_of(t, "LW 2")],
                           self.row_of(t, "LW 4"))
        self.assertEqual(self.titles("Finale")[1][0], "LW 1")
        self.assertEqual(self.titles("Vorrunde")[1][0], "LW 2")

    def test_no_heat_rows_or_no_target_move_nothing(self):
        t = self.t
        before = self.titles("Vorrunde")
        t._move_rows_block([self.hdr_row(t, "LW")], self.row_of(t, "LW 3"))
        lw1 = self.row_of(t, "LW 1")
        t._move_rows_block([lw1], lw1)
        self.assertEqual(self.titles("Vorrunde"), before)
        self.assertIsNone(t._slot_row("Nowhere", "LW", 0, 0))

    def test_an_anchor_of_another_dance_takes_the_single_row_path(self):
        single = self.patch(self.t, "_move_or_swap_rows")
        src, dst = self.row_of(self.t, "LW 1"), self.row_of(self.t, "TG 3")
        self.t._move_rows_block([src], dst)
        single.assert_called_once_with(src, dst)

    def test_a_failure_is_reported(self):
        t = self.t
        self.patch(t._row_meta, "swap", side_effect=RuntimeError("grid broken"))
        t._move_rows_block([self.row_of(t, "LW 1")], self.row_of(t, "LW 3"))
        self.assertEqual(self.critical.call_args.args[1:], ("Move Error", "grid broken"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
