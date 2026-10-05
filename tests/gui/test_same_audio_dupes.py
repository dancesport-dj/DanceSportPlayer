#!/usr/bin/env python3
"""Tests for ♊ the same audio twice in one list, wherever the file lies.

Run:  py -m unittest tests.gui.test_same_audio_dupes -v

The library lives on C: and on F:, and the DB knows both copies carry the very
same audio. A path-only "already in this list?" let the F: copy of a title in
next to its C: twin. Whatever the path, a title whose audio is already in the
list must not be added again — and a list that arrives holding such a pair
(an .m3u written before) is offered a clean-up, as is any list on demand.
"""
import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sameaudio_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import planner.db as pdb  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_AUDIO = bytes(range(256)) * 2048          # 512 KB of "music"


def _synchsafe_bytes(n: int) -> bytes:
    return bytes(((n >> 21) & 0x7f, (n >> 14) & 0x7f, (n >> 7) & 0x7f, n & 0x7f))


def _mp3(audio: bytes = _AUDIO, tag: int = 0) -> bytes:
    """[ID3v2 tag of `tag` bytes] + audio — an edited tag changes the bytes only."""
    if not tag:
        return audio
    return b"ID3\x04\x00\x00" + _synchsafe_bytes(tag) + b"T" * tag + audio


class _ScratchDbTest(unittest.TestCase):
    """A real AudioCache over a throw-away DB, and files on two 'drives'."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_sameaudio_f_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)
        self.cache = pdb.AudioCache()

    def _restore(self):
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def file(self, drive: str, name: str, data: bytes = _mp3()) -> Path:
        p = self.dir / drive / f"{name}.mp3"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    @staticmethod
    def entry(path: Path, dance: str = "LW") -> MusicEntry:
        return MusicEntry(path=path, title=path.stem, dance=dance, bpm=None)

    def table(self) -> PlaylistTable:
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        t._cache = self.cache
        t.resize(700, 400)
        return t

    def static_deck(self, heats) -> PlaylistTable:
        """A one-round static deck of `heats` (lists of entries, None = empty)."""
        dances = ["LW"] if all(len(h) == 1 for h in heats) else ["LW", "PD"]
        t = self.table()
        t.load({"Vorrunde": [list(h) for h in heats]}, dances,
               [RoundConfig(name="Vorrunde", heats=len(heats), tier="early")],
               "S", play_cb=None, suggester=None, use_timbre=False)
        return t

    def songs(self, t) -> list[str]:
        return [str(e.path) for e in t._row_meta.entries()]


class AddIsRefusedTest(_ScratchDbTest):
    """A copy of a planned title never gets in, whichever way it is added."""

    def test_the_static_deck_refuses_the_copy_from_the_other_drive(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        t = self.static_deck([[self.entry(c)], [None]])
        empty = next(r for r, m in enumerate(t._row_meta)
                     if m and not m.theme and m.entry is None)
        t._entry_for = lambda p: self.entry(Path(p))
        import gui.table_dnd as dnd
        shown = []
        real = dnd.QMessageBox.information
        dnd.QMessageBox.information = lambda *a, **kw: shown.append(a)
        self.addCleanup(setattr, dnd.QMessageBox, "information", real)
        self.assertFalse(t._replace_row_with_path(empty, f))
        self.assertEqual(self.songs(t), [str(c)])
        self.assertTrue(shown, "refused without saying why")

    def test_the_player_list_refuses_the_copy_from_the_other_drive(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        t = self.table()
        t.load_player_list([self.entry(c)], "Order", play_cb=None)
        t._resolve_drop_entries = lambda files: [self.entry(Path(p)) for p in files]
        self.assertEqual(t._insert_warmup_files([f], t.rowCount()), 0)
        self.assertEqual(self.songs(t), [str(c)])

    def test_the_wishlist_refuses_the_copy_from_the_other_drive(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        t = self.table()
        t.load_wishlist([self.entry(c)], play_cb=None, suggester=None)
        t._resolve_drop_entries = lambda files: [self.entry(Path(p)) for p in files]
        self.assertEqual(t._insert_drop_files([f], t.rowCount()), 0)
        self.assertEqual(self.songs(t), [str(c)])

    def test_a_retagged_renamed_copy_is_a_sure_duplicate(self):
        """Tags edited on one drive only: the bytes differ, the audio does not.
        A different file name as well leaves nothing but the audio to go by."""
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "01 Moon River", _mp3(tag=300))
        t = self.static_deck([[self.entry(c)], [None]])
        dup = t._find_duplicate(self.entry(f))
        self.assertIsNotNone(dup)
        self.assertEqual(dup[0], "hard")

    def test_different_audio_under_the_same_name_stays_a_question(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)", _AUDIO[::-1])
        t = self.static_deck([[self.entry(c)], [None]])
        dup = t._find_duplicate(self.entry(f))
        self.assertEqual(dup[0] if dup else None, "soft")

    def test_a_cut_edit_of_a_planned_title_is_a_question(self):
        """'…_cut' is its own encode — no bytes in common, the same song all the same."""
        c = self.file("C", "1-14 A New Life (TG 32)")
        f = self.file("F", "1-14 A New Life (TG 32)_cut", _AUDIO[::-1])
        t = self.static_deck([[self.entry(c, "TG")], [None]])
        dup = t._find_duplicate(self.entry(f, "TG"))
        self.assertEqual(dup[0] if dup else None, "soft")

    def test_a_different_title_is_added(self):
        c = self.file("C", "Moon River (LW 29)")
        other = self.file("F", "Fly Me (LW 29)", _AUDIO[::-1])
        t = self.table()
        t.load_player_list([self.entry(c)], "Order", play_cb=None)
        t._resolve_drop_entries = lambda files: [self.entry(Path(p)) for p in files]
        self.assertEqual(t._insert_warmup_files([other], t.rowCount()), 1)


class CleanupTest(_ScratchDbTest):
    """🧹 Remove the earlier copies of every title the list holds twice — the
    better title sits later in the rounds, so the last identical copy stays."""

    def setUp(self):
        super().setUp()
        import gui.table_actions as ta
        self.toasts = []
        real = ta._show_toast
        ta._show_toast = lambda _w, text, **kw: self.toasts.append(text)
        self.addCleanup(setattr, ta, "_show_toast", real)

    def ask(self, t, answer=True, keep=None):
        """Stand in for both questions: the plain Yes/No over identical copies, and
        the per-title choice — `keep(group)` returns the row to keep (None: all),
        `keep` itself None cancels that dialog."""
        t.asked = None
        t.groups = None

        def confirm(title, text):
            t.asked = text
            return answer
        t._confirm_delete = confirm

        def choose(identical, groups):
            t.asked = "choice"
            t.groups = groups
            t.group_paths = [[str(t._row_meta[r].entry.path) for r in g] for g in groups]
            if keep is None:
                return None
            gone = {r for r, _first in identical}
            for g in groups:
                kept = keep(g)
                if kept is not None:
                    gone |= {r for r in g if r != kept}
            return gone
        t._ask_which_duplicates = choose

    def test_the_player_list_loses_the_earlier_copy(self):
        c = self.file("C", "Moon River (LW 29)")
        other = self.file("C", "Fly Me (LW 29)", _AUDIO[::-1])
        f = self.file("F", "Moon River (LW 29)")
        t = self.table()
        t.load_player_list([self.entry(c), self.entry(other), self.entry(f)],
                           "Order", play_cb=None)
        self.ask(t)
        self.assertEqual(t._remove_duplicate_titles(), 1)
        self.assertEqual(self.songs(t), [str(other), str(f)])
        self.assertIn("Moon River", t.asked)

    def test_of_three_identical_copies_only_the_last_stays(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        d = self.file("D", "Moon River (LW 29)")
        t = self.table()
        t.load_player_list([self.entry(c), self.entry(f), self.entry(d)],
                           "Order", play_cb=None)
        self.ask(t)
        self.assertEqual(t._remove_duplicate_titles(), 2)
        self.assertEqual(self.songs(t), [str(d)])

    def test_a_deck_empties_the_slot_of_the_earlier_copy(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        t = self.static_deck([[self.entry(c)], [self.entry(f)]])
        self.ask(t)
        self.assertEqual(t._remove_duplicate_titles(), 1)
        self.assertEqual(self.songs(t), [str(f)])

    def test_for_another_file_of_the_same_title_the_user_picks_the_one_to_keep(self):
        """A '_cut' edit or a re-encode shares no audio key, only the title — two
        recordings, so which one stays is the user's call, here the later one."""
        c = self.file("C", "1-14 A New Life (TG 32)")
        f = self.file("F", "1-14 A New Life (TG 32)_cut", _AUDIO[::-1])
        t = self.table()
        t.load_player_list([self.entry(c, "TG"), self.entry(f, "TG")], "Order", play_cb=None)
        self.ask(t, keep=lambda group: group[1])
        self.assertEqual(t._remove_duplicate_titles(), 1)
        self.assertEqual(self.songs(t), [str(f)])
        self.assertEqual(len(t.groups), 1)
        self.assertEqual(len(t.groups[0]), 2)

    def test_keeping_all_of_a_title_still_drops_the_identical_copy(self):
        """Which identical byte copy goes doesn't matter, so it goes either way."""
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        new = self.file("C", "1-14 A New Life (TG 32)", _AUDIO[::-1])
        cut = self.file("F", "1-14 A New Life (TG 32)_cut", _AUDIO[1:] + b"x")
        t = self.table()
        t.load_player_list([self.entry(c), self.entry(new, "TG"), self.entry(f),
                            self.entry(cut, "TG")], "Order", play_cb=None)
        self.ask(t, keep=lambda group: None)
        self.assertEqual(t._remove_duplicate_titles(), 1)
        self.assertEqual(self.songs(t), [str(new), str(f), str(cut)])

    def test_the_title_choice_offers_the_copy_that_stays(self):
        """A New Life, its _cut, then the very same _cut again: the first _cut goes
        as an identical copy, so the choice is between A New Life and the last _cut."""
        new = self.file("C", "1-14 A New Life (TG 32)", _AUDIO[::-1])
        cut_c = self.file("C", "1-14 A New Life (TG 32)_cut")
        cut_f = self.file("F", "1-14 A New Life (TG 32)_cut")
        t = self.table()
        t.load_player_list([self.entry(new, "TG"), self.entry(cut_c, "TG"),
                            self.entry(cut_f, "TG")], "Order", play_cb=None)
        self.ask(t, keep=lambda group: None)
        self.assertEqual(t._remove_duplicate_titles(), 1)
        self.assertEqual(t.group_paths, [[str(new), str(cut_f)]])
        self.assertEqual(self.songs(t), [str(new), str(cut_f)])

    def test_a_title_whose_first_file_has_a_later_identical_copy(self):
        """Moon River, another file of it, then the first file again: the choice
        lists the other file and the last copy, in list order."""
        c = self.file("C", "Moon River (LW 29)")
        edit = self.file("C", "Moon River (LW 29)_cut", _AUDIO[::-1])
        f = self.file("F", "Moon River (LW 29)")
        t = self.table()
        t.load_player_list([self.entry(c), self.entry(edit), self.entry(f)],
                           "Order", play_cb=None)
        self.ask(t, keep=lambda group: group[0])
        self.assertEqual(t._remove_duplicate_titles(), 2)
        self.assertEqual(t.group_paths, [[str(edit), str(f)]])
        self.assertEqual(self.songs(t), [str(edit)])

    def test_cancelling_the_choice_removes_nothing(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        new = self.file("C", "1-14 A New Life (TG 32)", _AUDIO[::-1])
        cut = self.file("F", "1-14 A New Life (TG 32)_cut", _AUDIO[1:] + b"x")
        t = self.table()
        t.load_player_list([self.entry(c), self.entry(f), self.entry(new, "TG"),
                            self.entry(cut, "TG")], "Order", play_cb=None)
        self.ask(t, keep=None)
        self.assertEqual(t._remove_duplicate_titles(), 0)
        self.assertEqual(len(self.songs(t)), 4)
        self.assertEqual(t.asked, "choice")

    def test_a_copy_whose_dance_is_unknown_still_counts(self):
        """'1-18 Amame Otra Vez (Love Me Again)_cut' names no dance, and a file
        outside the library has none on record — no dance is no counter-evidence."""
        cut = self.file("C", "1-18 Amame Otra Vez (Love Me Again)_cut")
        orig = self.file("F", "1-18 Amame Otra Vez (Love Me Again)", _AUDIO[::-1])
        t = self.table()
        t.load_player_list([self.entry(cut, None), self.entry(orig, "TG")], "Order",
                           play_cb=None)
        self.ask(t, keep=lambda group: group[0])
        self.assertEqual(t._remove_duplicate_titles(), 1)
        self.assertEqual(self.songs(t), [str(cut)])

    def test_the_same_title_in_another_dance_is_another_song(self):
        """'Candela' as a Cha Cha and 'Candela' as a Rumba are two songs."""
        cc = self.file("C", "Candela (CC 30)")
        rb = self.file("F", "Candela (RB 25)", _AUDIO[::-1])
        t = self.table()
        t.load_player_list([self.entry(cc, "CC"), self.entry(rb, "RB")], "Order", play_cb=None)
        self.ask(t)
        self.assertEqual(t._remove_duplicate_titles(), 0)
        self.assertIsNone(t.asked)

    def test_a_paso_may_come_round_again_in_a_deck(self):
        """ALLOW_REPEAT: the Paso is danced more than once by design."""
        c = self.file("C", "Espana Cani (PD 60)")
        f = self.file("F", "Espana Cani (PD 60)")
        t = self.static_deck([[self.entry(c, "PD")], [self.entry(f, "PD")]])
        self.ask(t)
        self.assertEqual(t._remove_duplicate_titles(), 0)
        self.assertIsNone(t.asked)

    def test_the_wishlist_loses_the_earlier_copy(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        t = self.table()
        t.load_wishlist([self.entry(c), self.entry(f)], play_cb=None, suggester=None)
        self.ask(t)
        self.assertEqual(t._remove_duplicate_titles(), 1)
        self.assertEqual(self.songs(t), [str(f)])

    def test_saying_no_keeps_both(self):
        c = self.file("C", "Moon River (LW 29)")
        f = self.file("F", "Moon River (LW 29)")
        t = self.table()
        t.load_player_list([self.entry(c), self.entry(f)], "Order", play_cb=None)
        self.ask(t, answer=False)
        self.assertEqual(t._remove_duplicate_titles(), 0)
        self.assertEqual(len(self.songs(t)), 2)
        self.assertIsNotNone(t.asked, "removed without asking")

    def test_a_clean_list_asks_nothing_and_says_so(self):
        c = self.file("C", "Moon River (LW 29)")
        t = self.table()
        t.load_player_list([self.entry(c)], "Order", play_cb=None)
        self.ask(t)
        self.assertEqual(t._remove_duplicate_titles(), 0)
        self.assertIsNone(t.asked)
        self.assertTrue(any("No duplicate" in s for s in self.toasts), self.toasts)

    def test_on_load_a_clean_list_stays_quiet(self):
        c = self.file("C", "Moon River (LW 29)")
        t = self.table()
        t.load_player_list([self.entry(c)], "Order", play_cb=None)
        self.ask(t)
        self.assertEqual(t._remove_duplicate_titles(on_load=True), 0)
        self.assertEqual(self.toasts, [])


class LoadOffersCleanupTest(_ScratchDbTest):
    """An .m3u that arrives holding one title from both drives is asked about."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from PySide6.QtCore import QSettings
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_sameaudio_qs_"))
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        super().setUp()
        from planner.library import MusicLibrary
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._lib = MusicLibrary()
        self.win._cache = self.cache
        for t in self.win._all_tables:
            t._cache = self.cache

    def m3u(self) -> Path:
        c = self.file("C", "Moon River (LW 29)")
        other = self.file("C", "Fly Me (TG 32)", _AUDIO[::-1])
        f = self.file("F", "Moon River (LW 29)")
        for p, d in ((c, "LW"), (other, "TG"), (f, "LW")):
            self.win._lib.entries.append(
                MusicEntry(path=p, title=p.stem, dance=d, duration=180))
        m = self.dir / "order.m3u"
        m.write_text("#EXTM3U\n" + "\n".join(map(str, (c, other, f))), encoding="utf-8")
        return m

    def answer(self, table, yes: bool):
        asked = []
        table._confirm_delete = lambda title, text: asked.append(text) or yes
        return asked

    def test_the_player_list_load_asks_and_removes(self):
        table = self.win._decks[0]
        asked = self.answer(table, True)
        self.win._load_player_list_from_m3u(table, self.m3u())
        self.assertEqual(len(asked), 1)
        self.assertEqual(len(table._row_meta.entries()), 2)

    def test_the_deck_import_asks_and_empties_the_slot(self):
        table = self.win._table
        asked = self.answer(table, True)
        self.win._import_playlist_path(str(self.m3u()))
        self.assertEqual(len(asked), 1)
        self.assertEqual(len(table._row_meta.entries()), 2)

    def test_the_eintanzen_load_asks_and_keeps_on_no(self):
        table = self.win._warmup_table
        asked = self.answer(table, False)
        self.win._load_warmup_from_m3u(table, self.m3u())
        self.assertEqual(len(asked), 1)
        self.assertEqual(len(table._row_meta.entries()), 3)


class ChoiceDialogTest(unittest.TestCase):
    """The per-title choice itself: one radio per file plus "Keep all"."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, play_cb=None):
        from gui.duplicate_titles_dialog import DuplicateTitlesDialog
        e = lambda name, dance="TG": MusicEntry(path=Path("C:/m") / name, title=name,
                                                 dance=dance, bpm=None)
        dlg = DuplicateTitlesDialog(
            None,
            identical=[(e("Moon River (LW 29).mp3", "LW"), e("Moon River (LW 29).mp3", "LW"))],
            groups=[[(3, e("A New Life (TG 32).mp3")), (7, e("A New Life (TG 32)_cut.mp3"))],
                    [(4, e("Amame.mp3")), (9, e("Amame_cut.mp3")), (12, e("Amame 2.mp3"))]],
            play_cb=play_cb)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_each_file_has_a_play_button(self):
        played = []
        dlg = self.dialog(play_cb=played.append)
        self.assertEqual(len(dlg.play_buttons), 5)
        dlg.play_buttons[1].click()
        self.assertEqual(played, [Path("C:/m") / "A New Life (TG 32)_cut.mp3"])
        self.assertEqual(dlg.play_buttons[1].text(), "■")

    def test_play_switches_and_a_second_click_stops(self):
        played = []
        dlg = self.dialog(play_cb=played.append)
        dlg.play_buttons[0].click()
        dlg.play_buttons[2].click()
        self.assertEqual(dlg.play_buttons[0].text(), "▶")
        dlg.play_buttons[2].click()
        self.assertEqual(played[-1], None)
        self.assertEqual(dlg.play_buttons[2].text(), "▶")

    def test_closing_the_dialog_stops_the_preview(self):
        played = []
        dlg = self.dialog(play_cb=played.append)
        dlg.play_buttons[3].click()
        dlg.reject()
        self.assertEqual(played[-1], None)

    def test_without_a_player_there_is_no_play_button(self):
        self.assertEqual(self.dialog().play_buttons, [])

    def test_nothing_is_chosen_away_by_default(self):
        self.assertEqual(self.dialog().removed_rows(), set())

    def test_picking_a_file_removes_the_others_of_its_title(self):
        dlg = self.dialog()
        dlg.radios[1][1].setChecked(True)       # keep Amame_cut
        self.assertEqual(dlg.removed_rows(), {4, 12})
        dlg.radios[0][0].setChecked(True)       # keep A New Life
        self.assertEqual(dlg.removed_rows(), {4, 12, 7})

    def test_keep_all_takes_a_choice_back(self):
        dlg = self.dialog()
        dlg.radios[0][1].setChecked(True)
        dlg.radios[0][-1].setChecked(True)      # the last radio is "Keep all"
        self.assertEqual(dlg.removed_rows(), set())

    def test_the_files_are_named_with_their_folder(self):
        from PySide6.QtWidgets import QRadioButton
        texts = [b.text() for b in self.dialog().findChildren(QRadioButton)]
        self.assertTrue(any("A New Life (TG 32)_cut.mp3" in s for s in texts), texts)
        self.assertTrue(any("C:" in s for s in texts), texts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
