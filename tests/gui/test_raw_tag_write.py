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
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_raw_tags_"))

from mutagen.id3 import ID3, POPM, TIT2, TPE1, TXXX  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402

import planner.db as pdb  # noqa: E402
from dancesport_planner import MusicLibrary, PlaylistSuggester, RoundConfig  # noqa: E402
from planner import tag_edits  # noqa: E402
from planner.db import AudioCache  # noqa: E402
from tests.qt_test_support import reap_widget, stub_window_startup  # noqa: E402

_AUDIO = b"\xff\xfb\x90\x00" + bytes(range(256)) * 40


class _Answer:
    """A TagEditDialog after Save, without opening one."""

    def __init__(self, raw=None, changes=None, form=None, mp3s=()):
        self._raw = raw
        self._changes = changes or {}
        self._form = form or {}
        self._mp3s = list(mp3s)
        self.reset_requested = False

    def form_changes(self):
        return dict(self._form)

    def form_mp3s(self):
        return list(self._mp3s)

    def changes_for(self, entry):
        return dict(self._changes)

    def raw_edits(self):
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
        saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = tmp / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False

        def restore():
            try:
                pdb._DB_LOCAL.conn.close()
            except Exception:
                pass
            pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = saved
        self.addCleanup(restore)

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
        self.win._cache = AudioCache()
        lib = MusicLibrary()
        self.entry = lib._make_entry(self.path, lib._get_scan_cache(self.win._cache))
        lib.entries.append(self.entry)
        self.win._lib = lib
        self.win._tableB.load(
            {"Runde 1": [[self.entry]]}, ["CC"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")], "S",
            play_cb=self.win._play_or_stop, suggester=PlaylistSuggester(lib),
            use_timbre=False, style="Latin", dynamic=True, capacity=[1])
        self.toasts = []
        patcher = mock.patch("gui.main_music._show_toast",
                             lambda _w, text, *a, **kw: self.toasts.append(text))
        patcher.start()
        self.addCleanup(patcher.stop)
        # "Also write into the MP3?" answered No unless a test says otherwise.
        self.asked = []
        self.answer = False
        self.win._ask_write_to_mp3 = lambda n, fields: (
            self.asked.append((n, fields)) or self.answer)


class RawWriteTest(_WindowTest):

    def test_the_file_is_written_and_the_rows_show_it(self):
        self.assertEqual(self.entry.tag_artist, "Old Band")
        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"TPE1": "New Band"}, "deletes": [], "adds": []}))
        self.assertEqual(ID3(self.path)["TPE1"].text, ["New Band"])
        self.assertEqual(ID3(self.path)["TXXX:ultramixer_meter"].text, ["4/4"])
        self.assertEqual(self.entry.tag_artist, "New Band")

    def test_stars_set_in_the_app_survive_the_new_fingerprint(self):
        cache = self.win._cache
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
        self.assertEqual(tag_edits.load(self.win._cache.fingerprint(self.path)),
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
    """Stars, classes, instrumental and markers into the MP3 too — after asking."""

    def test_yes_writes_them_and_the_file_is_the_truth_again(self):
        self.answer = True
        cache = self.win._cache
        self.win._apply_tag_dialog([self.entry], _Answer(changes={
            "rating": 4, "classes_ok": ["A", "S"], "comment_tags": ["vocal_f"]}))
        self.assertEqual(self.asked, [(1, ["stars", "classes", "markers"])])
        tags = ID3(self.path)
        self.assertEqual(tags["POPM:Windows Media Player 9 Series"].rating, 196)
        self.assertEqual(tags["COMM::eng"].text, ["A;S;vocal_f"])
        self.assertEqual(tags["TXXX:ultramixer_meter"].text, ["4/4"])
        self.assertEqual((self.entry.rating, self.entry.classes_ok, self.entry.comment_tags),
                         (4, ["A", "S"], ["vocal_f"]))
        self.assertEqual(tag_edits.load(cache.fingerprint(self.path)), {})

    def test_no_keeps_them_in_the_app_only(self):
        before = self.path.read_bytes()
        self.win._apply_tag_dialog([self.entry], _Answer(changes={"rating": 4}))
        self.assertEqual(len(self.asked), 1)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(tag_edits.load(self.win._cache.fingerprint(self.path)),
                         {"rating": 4})
        self.assertEqual(self.entry.rating, 4)

    def test_what_the_file_cant_say_stays_in_the_app(self):
        """'(Instr.)' in a title makes a track instrumental whatever the comment
        says, so a "not instrumental" can only live in the DB."""
        self.answer = True
        self.entry.is_instrumental = True
        with mock.patch("planner.library.title_marks_instrumental", return_value=True):
            self.win._apply_tag_dialog([self.entry], _Answer(changes={
                "is_instrumental": False, "rating": 3}))
            self.assertEqual(tag_edits.load(self.win._cache.fingerprint(self.path)),
                             {"is_instrumental": False})
        self.assertFalse(self.entry.is_instrumental)
        self.assertEqual(self.entry.rating, 3)

    def test_not_asked_without_a_change_to_them(self):
        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"TPE1": "New Band"}, "deletes": [], "adds": []}))
        self.assertEqual(self.asked, [])

    def test_not_asked_for_back_to_the_file(self):
        answer = _Answer(changes={"rating": 4})
        answer.reset_requested = True
        self.win._apply_tag_dialog([self.entry], answer)
        self.assertEqual(self.asked, [])

    def test_a_playing_track_keeps_the_edit_in_the_app(self):
        self.answer = True
        before = self.path.read_bytes()
        with mock.patch.object(self.win._player, "source",
                               return_value=QUrl.fromLocalFile(str(self.path))), \
                mock.patch.object(self.win._player, "playbackState",
                                  return_value=QMediaPlayer.PlaybackState.PlayingState):
            self.win._apply_tag_dialog([self.entry], _Answer(changes={"rating": 4}))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.toasts), 1)
        self.assertEqual(tag_edits.load(self.win._cache.fingerprint(self.path)),
                         {"rating": 4})


class FormWriteTest(_WindowTest):
    """The Mp3tag-style form: one change, written into every selected MP3."""

    def second(self):
        path = self.path.with_name("Cha Two (CC 30).mp3")
        shutil.copyfile(self.path, path)
        tags = ID3(path)
        tags["TIT2"].text = ["Cha Two"]
        tags.save(path, v2_version=3)
        lib = self.win._lib
        entry = lib._make_entry(path, lib._get_scan_cache(self.win._cache))
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
        self.assertEqual(self.asked, [])

    def test_form_table_and_app_fields_in_one_save(self):
        self.answer = True
        cache = self.win._cache
        self.win._apply_tag_dialog([self.entry], _Answer(
            raw={"sets": {"TXXX:ultramixer_meter": "3/4"}, "deletes": [], "adds": []},
            form={"comment": "Erscheinungsdatum 2016"}, changes={"classes_ok": ["C"]},
            mp3s=[self.entry]))
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
        self.assertEqual(tag_edits.load(self.win._cache.fingerprint(self.path)),
                         {"rating": 5})


if __name__ == "__main__":
    unittest.main(verbosity=2)
