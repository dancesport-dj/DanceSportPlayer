"""🏷 The editor's MP3 side — extended table, form, app fields — written into the file.

Run:  py -m unittest tests.gui.test_raw_tag_write -v

What matters is the window's part. The write changes the file's content
fingerprint, the key every analysed row and every in-app tag edit hangs off —
so the stars set in the app must still be there afterwards, the rows must show
what the file says now, and the file the player has loaded is left alone.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_raw_tags_"))

from mutagen.id3 import ID3, POPM, TIT2, TPE1, TXXX
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer

from dancesport_planner import MusicLibrary, PlaylistSuggester, RoundConfig
from gui.dialogs.tag_edit_dialog import FILENAME_TITLE
from planner.models import MusicEntry
from planner.music import tag_edits
from planner.music.db import AudioCache
from planner.terms import dance_name
from shared.columns import _COL_DANCE, _COL_TITLE, COL_HEAT
from shared.widgets import WARN_TOAST_MS
from tests.db_support import use_scratch_db
from tests.qt_test_support import reap_widget, stub_window_startup

_AUDIO = b"\xff\xfb\x90\x00" + bytes(range(256)) * 40


class _Answer:
    """A TagEditDialog after Save, without opening one."""

    def __init__(self, raw=None, changes=None, form=None, mp3s=(), raw_for=None,
                 write_app=False):
        self._raw = raw
        self._raw_for = raw_for     # {path: raw edits} for a selection
        self._changes = changes or {}
        self._form = form or {}
        self._mp3s = list(mp3s)
        self.reset_requested = False
        self._write_app = write_app   # "Also write these into the MP3 file"

    def write_app_to_mp3(self):
        return self._write_app

    def form_changes(self):
        return dict(self._form)

    def form_mp3s(self):
        return list(self._mp3s)

    def changes_for(self, entry):
        return dict(self._changes)

    def raw_edits(self, entry=None):
        if self._raw_for is not None:
            return self._raw_for.get(str(entry.path))
        return self._raw


class _WindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_raw_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        tmp = Path(tempfile.mkdtemp(prefix="dp_raw_db_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        use_scratch_db(self, tmp / "scratch.db")

        self.path = tmp / "Cha One (CC 30).mp3"
        self.path.write_bytes(_AUDIO)
        tags = ID3()
        for f in (TIT2(encoding=1, text="Cha One"), TPE1(encoding=1, text="Old Band"),
                  TXXX(encoding=1, desc="ultramixer_meter", text="4/4"),
                  POPM(email="Windows Media Player 9 Series", rating=64, count=0)):
            tags.add(f)
        tags.update_to_v23()
        tags.save(self.path, v2_version=3)
        # The file was written well before the app saw it, as in a library.
        os.utime(self.path, (1_700_000_000, 1_700_000_000))

        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._library.cache = AudioCache()
        lib = MusicLibrary()
        self.entry = lib._make_entry(self.path, lib._get_scan_cache(self.win._library.cache))
        lib.entries.append(self.entry)
        self.win._library.lib = lib
        self.win._deckset.tableB.load(
            {"Runde 1": [[self.entry]]}, ["CC"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")], "S",
            play_cb=self.win._play_or_stop, suggester=PlaylistSuggester(lib),
            use_timbre=False, style="Latin", dynamic=True, capacity=[1])
        self.toasts, self.toast_ms, self.toast_kw = [], [], []
        patcher = mock.patch("gui.window.main_tags.show_toast",
                             lambda _w, text, *a, **kw: (self.toasts.append(text),
                                                         self.toast_ms.append(a),
                                                         self.toast_kw.append(kw)))
        patcher.start()
        self.addCleanup(patcher.stop)


class RawWriteTest(_WindowTest):

    def test_the_file_is_written_and_the_rows_show_it(self):
        self.assertEqual(self.entry.tag_artist, "Old Band")
        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"TPE1": "New Band"}, "deletes": [], "adds": []}))
        self.assertEqual(ID3(self.path)["TPE1"].text, ["New Band"])
        self.assertEqual(ID3(self.path)["TXXX:ultramixer_meter"].text, ["4/4"])
        self.assertEqual(self.entry.tag_artist, "New Band")

    def test_stars_set_in_the_app_survive_the_new_fingerprint(self):
        cache = self.win._library.cache
        self.win._apply_tag_dialog([self.entry], _Answer(changes={"rating": 5}))
        old_fp = cache.fingerprint(self.path)
        self.assertEqual(tag_edits.load(old_fp), {"rating": 5})

        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"POPM:Windows Media Player 9 Series": "255",
                          "TPE1": "New Band"}, "deletes": [], "adds": []}))
        new_fp = cache.fingerprint(self.path)
        self.assertNotEqual(new_fp, old_fp)
        self.assertEqual(tag_edits.load(new_fp), {"rating": 5})
        self.assertEqual(self.entry.rating, 5)

    def test_raw_and_app_edits_in_one_save(self):
        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"TPE1": "New Band"}, "deletes": [], "adds": []},
            changes={"classes_ok": ["S"]}))
        self.assertEqual(self.entry.tag_artist, "New Band")
        self.assertEqual(self.entry.classes_ok, ["S"])
        self.assertEqual(tag_edits.load(self.win._library.cache.fingerprint(self.path)),
                         {"classes_ok": ["S"]})

    def test_the_playing_track_is_not_written(self):
        before = self.path.read_bytes()
        for state in (QMediaPlayer.PlaybackState.PlayingState,
                      QMediaPlayer.PlaybackState.PausedState):
            with mock.patch.object(self.win._player, "source",
                                   return_value=QUrl.fromLocalFile(str(self.path))), \
                    mock.patch.object(self.win._player, "playbackState",
                                      return_value=state):
                self.win._apply_tag_dialog([self.entry], _Answer(
                    raw={"sets": {"TPE1": "New Band"}, "deletes": [], "adds": []}))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.entry.tag_artist, "Old Band")
        self.assertEqual(len(self.toasts), 2)
        # F12: long enough to read why.
        self.assertEqual(self.toast_ms, [(WARN_TOAST_MS,)] * 2)
        self.assertEqual(self.toast_kw, [{"error": True}] * 2)   # F13: in red

    def test_a_cued_track_is_written_and_loaded_again(self):
        """Every deck load cues its first title, so refusing those would block
        the most common case — the source is set again after the write."""
        player = self.win._player
        player.setSource(QUrl.fromLocalFile(str(self.path)))
        seen = []
        player.sourceChanged.connect(lambda url: seen.append(url.toLocalFile()))
        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"TPE1": "New Band"}, "deletes": [], "adds": []}))
        self.assertEqual(ID3(self.path)["TPE1"].text, ["New Band"])
        self.assertEqual(Path(player.source().toLocalFile()), self.path)
        self.assertEqual([Path(s) for s in seen if s], [self.path])

    def test_a_bad_value_writes_nothing_and_says_why(self):
        before = self.path.read_bytes()
        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"POPM:Windows Media Player 9 Series": "999"},
                 "deletes": [], "adds": []}))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.toasts), 1)
        self.assertIn("255", self.toasts[0])


class AppFieldsWriteTest(_WindowTest):
    """Stars, classes, instrumental and markers into the MP3 too — when the
    dialog's "Also write these into the MP3 file" is ticked."""

    def test_the_window_no_longer_asks(self):
        self.assertFalse(hasattr(self.win, "_ask_write_to_mp3"))

    def test_ticked_writes_them_and_the_file_is_the_truth_again(self):
        cache = self.win._library.cache
        self.win._apply_tag_dialog([self.entry], _Answer(changes={
            "rating": 4, "classes_ok": ["A", "S"], "comment_tags": ["vocal_f"]},
            write_app=True))
        tags = ID3(self.path)
        self.assertEqual(tags["POPM:Windows Media Player 9 Series"].rating, 196)
        self.assertEqual(tags["COMM::eng"].text, ["A;S;vocal_f"])
        self.assertEqual(tags["TXXX:ultramixer_meter"].text, ["4/4"])
        self.assertEqual((self.entry.rating, self.entry.classes_ok, self.entry.comment_tags),
                         (4, ["A", "S"], ["vocal_f"]))
        self.assertEqual(tag_edits.load(cache.fingerprint(self.path)), {})

    def test_unticked_keeps_them_in_the_app_only(self):
        before = self.path.read_bytes()
        self.win._apply_tag_dialog([self.entry], _Answer(changes={"rating": 4}))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(tag_edits.load(self.win._library.cache.fingerprint(self.path)),
                         {"rating": 4})
        self.assertEqual(self.entry.rating, 4)

    def test_what_the_file_cant_say_stays_in_the_app(self):
        """'(Instr.)' in a title makes a track instrumental whatever the comment
        says, so a "not instrumental" can only live in the DB."""
        self.entry.is_instrumental = True
        with mock.patch("planner.music.library.title_marks_instrumental", return_value=True):
            self.win._apply_tag_dialog([self.entry], _Answer(changes={
                "is_instrumental": False, "rating": 3}, write_app=True))
            self.assertEqual(tag_edits.load(self.win._library.cache.fingerprint(self.path)),
                             {"is_instrumental": False})
        self.assertFalse(self.entry.is_instrumental)
        self.assertEqual(self.entry.rating, 3)

    def test_back_to_the_file_writes_nothing_even_ticked(self):
        before = self.path.read_bytes()
        answer = _Answer(changes={"rating": 4}, write_app=True)
        answer.reset_requested = True
        self.win._apply_tag_dialog([self.entry], answer)
        self.assertEqual(self.path.read_bytes(), before)

    def test_a_playing_track_keeps_the_edit_in_the_app(self):
        before = self.path.read_bytes()
        with mock.patch.object(self.win._player, "source",
                               return_value=QUrl.fromLocalFile(str(self.path))), \
                mock.patch.object(self.win._player, "playbackState",
                                  return_value=QMediaPlayer.PlaybackState.PlayingState):
            self.win._apply_tag_dialog([self.entry], _Answer(changes={"rating": 4},
                                                             write_app=True))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.toasts), 1)
        self.assertEqual(tag_edits.load(self.win._library.cache.fingerprint(self.path)),
                         {"rating": 4})


class FormWriteTest(_WindowTest):
    """The Mp3tag-style form: one change, written into every selected MP3."""

    def second(self):
        path = self.path.with_name("Cha Two (CC 30).mp3")
        shutil.copyfile(self.path, path)
        tags = ID3(path)
        tags["TIT2"].text = ["Cha Two"]
        tags.save(path, v2_version=3)
        lib = self.win._library.lib
        entry = lib._make_entry(path, lib._get_scan_cache(self.win._library.cache))
        lib.entries.append(entry)
        return entry

    def test_every_selected_mp3_gets_the_change_and_shows_it(self):
        two = self.second()
        self.win._apply_tag_dialog([self.entry, two], _Answer(
            form={"artist": "New Band", "album": "Latin"}, mp3s=[self.entry, two]))
        for e in (self.entry, two):
            tags = ID3(e.path)
            self.assertEqual((tags["TPE1"].text, tags["TALB"].text), (["New Band"], ["Latin"]))
            self.assertEqual(e.tag_artist, "New Band")
        self.assertEqual(ID3(two.path)["TIT2"].text, ["Cha Two"])

    def test_the_file_name_as_title_is_each_files_own(self):
        """F12: the title arrow's "< filename >" across a selection."""
        two = self.second()
        self.win._apply_tag_dialog([self.entry, two], _Answer(
            form={"title": FILENAME_TITLE}, mp3s=[self.entry, two]))
        for e in (self.entry, two):
            self.assertEqual(ID3(e.path)["TIT2"].text, [Path(e.path).stem])

    def test_each_selected_mp3_gets_its_own_table_edit(self):
        """The Extended tab with several tracks: one field typed for all of
        them is set where a file has it and added where it doesn't."""
        two = self.second()
        self.win._apply_tag_dialog([self.entry, two], _Answer(raw_for={
            str(self.entry.path): {"sets": {"TXXX:ultramixer_meter": "3/4"},
                                   "deletes": [], "adds": []},
            str(two.path): {"sets": {}, "deletes": ["TXXX:ultramixer_meter"],
                            "adds": [("TXXX", "um_dance", "CC")]}}))
        self.assertEqual(ID3(self.path)["TXXX:ultramixer_meter"].text, ["3/4"])
        tags = ID3(two.path)
        self.assertNotIn("TXXX:ultramixer_meter", tags)
        self.assertEqual(tags["TXXX:um_dance"].text, ["CC"])

    def test_form_table_and_app_fields_in_one_save(self):
        cache = self.win._library.cache
        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"TXXX:ultramixer_meter": "3/4"}, "deletes": [], "adds": []},
            form={"comment": "Erscheinungsdatum 2016"}, changes={"classes_ok": ["C"]},
            mp3s=[self.entry], write_app=True))
        tags = ID3(self.path)
        self.assertEqual(tags["COMM::eng"].text, ["C;Erscheinungsdatum 2016"])
        self.assertEqual(tags["TXXX:ultramixer_meter"].text, ["3/4"])
        self.assertEqual(self.entry.classes_ok, ["C"])
        self.assertEqual(tag_edits.load(cache.fingerprint(self.path)), {})

    def test_a_form_change_with_no_keeps_the_app_fields_in_the_app(self):
        self.win._apply_tag_dialog([self.entry], _Answer(
            form={"title": "Cha Neu"}, changes={"rating": 5}, mp3s=[self.entry]))
        self.assertEqual(ID3(self.path)["TIT2"].text, ["Cha Neu"])
        self.assertEqual(ID3(self.path)["POPM:Windows Media Player 9 Series"].rating, 64)
        self.assertEqual(tag_edits.load(self.win._library.cache.fingerprint(self.path)),
                         {"rating": 5})


class FlatListRepaintTest(_WindowTest):
    """A wishlist row takes its dance from the title, not from a heat: a tag
    that makes the Cha a Rumba must show there, and the new title with it."""

    def setUp(self):
        super().setUp()
        self.wl = self.win._deckset.wishlist
        self.wl.load_wishlist([self.entry], play_cb=self.win._play_or_stop,
                              suggester=None)

    def cell(self, col):
        return self.wl.item(0, col).text()

    def test_a_new_genre_dance_shows_in_the_wishlist(self):
        self.assertEqual(self.cell(_COL_DANCE), self.wl._dance_label("CC"))
        self.win._apply_tag_dialog([self.entry], _Answer(
            form={"title": "Rumba One", "genre": "Rumba"}, mp3s=[self.entry]))
        self.assertEqual(self.entry.dance, "RB")
        self.assertEqual(self.cell(_COL_DANCE), self.wl._dance_label("RB"))
        self.assertIn("Rumba One", self.cell(_COL_TITLE))


class RunningOrderRepaintTest(_WindowTest):
    """A free running order takes its dance, its ─── strips and its "Heat n"
    from the titles in it, so a tag that makes the Cha a Rumba re-cuts them."""

    def setUp(self):
        super().setUp()
        self.t = self.win._deckset.tableB
        self.rumba = MusicEntry(path=self.path.with_name("Rumba Two (RB 25).mp3"),
                                title="Rumba Two", dance="RB")

    def rows(self):
        return [(r, m) for r, m in self.t._row_meta.numbered()]

    def strips(self):
        return [self.t.item(r, 0).text() for r in sorted(self.t._round_hdr_rows)]

    def test_the_heats_of_a_round_follow_the_new_dance(self):
        sections = {str(self.entry.path): "Finale", str(self.rumba.path): "Finale"}
        self.t.load_player_list([self.entry, self.rumba], "🏁 Order",
                                play_cb=self.win._play_or_stop, sections=sections)
        self.assertEqual([self.t.item(r, COL_HEAT).text() for r, _ in self.rows()],
                         ["", ""])
        self.win._apply_tag_dialog([self.entry], _Answer(
            form={"title": "Rumba One", "genre": "Rumba"}, mp3s=[self.entry]))
        self.assertEqual(self.entry.dance, "RB")
        cells = [(self.t.item(r, _COL_DANCE).text(), self.t.item(r, COL_HEAT).text())
                 for r, _ in self.rows()]
        rb = self.t._dance_label("RB")
        self.assertEqual(cells, [(rb, "Heat 1"), (rb, "Heat 2")])

    def test_a_strip_named_after_the_dance_is_renamed(self):
        self.t.load_player_list([self.entry], "🏁 Order",
                                play_cb=self.win._play_or_stop)
        self.assertIn(dance_name("CC"), self.strips()[0])
        self.win._apply_tag_dialog([self.entry], _Answer(
            form={"title": "Rumba One", "genre": "Rumba"}, mp3s=[self.entry]))
        self.assertIn(dance_name("RB"), self.strips()[0])
        self.assertEqual(self.t.item(self.rows()[0][0], _COL_DANCE).text(),
                         self.t._dance_label("RB"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
