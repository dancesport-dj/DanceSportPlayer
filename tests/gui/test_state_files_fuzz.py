"""🗂️ Fuzz: the state files a start reads back.

Settings, the autosaved desk, the cartwall, the tournament tree, the evening
played so far, the crash note, own looks and the presenter's timetable all sit
in the state folder, where a sync client, a hand edit, a newer build or a full
disk can leave anything. JsonStore.read already turns a file that does not
parse into the default (planner/store.py), so the risk is the file that does
parse, with the wrong things in it.

Two layers. Each loader on its own, many inputs: it returns what its callers
expect and raises nothing, since none of them catches anything (the start
calls them bare), and the file's bytes survive the read - unchanged, or in
the copy the store keeps aside. Then a few real windows started on such
files, on the monkey's silent library: no exception may escape into the event
loop and no critical box may open.
"""
import contextlib
import datetime as dt
import json
import os
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from hypothesis import example, given
from hypothesis import strategies as st
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from gui import dialogs
from gui import tournament_tree as tree
from gui.window.session_env import ALL_DECK_KEYS, WISH_KEYS
from planner.playing import cartwall, play_session
from player.presenter import timetable
from player.window.main_load import TrackLoadMixin
from shared import stores
from shared.appearance import looks, user_looks
from tests.fuzz_support import fuzz, json_docs, mutated, perturbed
from tests.gui.monkey_support import ExceptionTrap, LoadedWindow

NOW = dt.datetime(2026, 11, 17, 22, 0)


@contextlib.contextmanager
def fresh_state():
    """A state folder of its own for one input."""
    with tempfile.TemporaryDirectory(prefix="dp_state_fuzz_") as d, \
            mock.patch.dict(os.environ, {"DANCEPLAYLIST_STATE_DIR": d}):
        yield d


def dump(doc) -> bytes:
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def keys_of(doc) -> set[str]:
    """Every key anywhere in a document."""
    if isinstance(doc, dict):
        return set(doc) | {k for v in doc.values() for k in keys_of(v)}
    if isinstance(doc, list):
        return {k for v in doc for k in keys_of(v)}
    return set()


def files(seed: dict, extra=()) -> st.SearchStrategy:
    """What could be in one state file: any bytes, the app's own document
    with bytes or parts changed, or any JSON over its keys."""
    return st.one_of(st.binary(max_size=200), mutated(dump(seed)),
                     perturbed(seed).map(dump),
                     json_docs(sorted(keys_of(seed) | set(extra))).map(dump))


with fresh_state():
    SETTINGS = dialogs.load_settings()
    LOOK = user_looks.to_dict(user_looks.copy_of(next(iter(looks.LOOKS.values())),
                                                 "Fuzz look"))

AUTOSAVE = {
    "version": dialogs.AUTOSAVE_VERSION, "deck_count": 2, "dual": True,
    "dual_wish": False, "wish_state": 1, "wish_grid": False,
    "deck_a": {"mode": "Favorites", "ui_mode": "Favorites", "style": "Standard",
               "dance_class": "S", "age": "Hgr", "dances": ["LW", "TG"],
               "rounds": [], "dynamic": False, "dynamic_capacity": []},
    "wishlist": ["C:\\music\\Song 01 (LW 29).mp3"],
    "names": {"deck_a": "Hgr S Standard", "wishlist": "Ideas"},
    "warmup": {}, "day_tab": "", "group_tabs": ["", ""], "day_tab_keep": False,
    "deck_modes": {"deck_a": "static"}, "list_play": {"deck_a": {"LW": 90}},
    "m3u_paths": {"deck_a": "C:\\lists\\a.m3u"}, "deck_advance": {},
}
AUTOSAVE_KEYS = (*ALL_DECK_KEYS, *WISH_KEYS, "theme_entries", "paths", "heat_plan")

CARTWALL = {
    "version": cartwall.CARTWALL_VERSION, "cols": 4, "rows": 3, "page": 0,
    "default_colour": cartwall.DEFAULT_PAD_COLOUR,
    "pages": [{"name": "Fanfares", "pads": {
        cartwall.cell_key((0, 0)): {"path": "C:\\fx\\horn.mp3", "label": "Horn",
                                    "volume": 80, "loop": False, "queue": 1},
        cartwall.cell_key((1, 2)): {"path": "C:\\fx\\bed.mp3", "background": True,
                                    "duck": True, "fade_ms": 400}}}],
}

TOURNAMENTS = {
    "version": 1, "view": tree.VIEW_LIST,
    "columns": {"hidden": [1], "order": [0, 1, 2], "count": 3},
    "tournaments": [{"name": "Autumn Cup", "source": "C:\\lists", "children": [
        {"name": "Hgr S", "m3u": "C:\\lists\\hgr_s.m3u"}, {"name": "Empty"}]}],
}

PLAY_SESSION = play_session.to_json(play_session.Session(
    NOW - dt.timedelta(hours=1), ["C:\\music\\Song 01 (LW 29).mp3"]))

TIMETABLE = timetable.Timetable.from_dict({
    "title": "Autumn Ball", "rotate": True, "rotate_secs": 20,
    "entries": [{"time": "20:30", "what": "Opening", "until": "21:00"},
                {"time": "ca. 23 Uhr", "what": "Midnight show", "note": "PD"}],
}).as_dict()

ON_AIR = {"table": 0, "row": 3, "path": "C:\\music\\Song 01 (LW 29).mp3"}


class LoaderFuzzTest(unittest.TestCase):
    """Each loader on its own."""

    def read_back(self, name: str, data: bytes, load):
        """`load()` over `data` as the file `name`; the bytes must survive it."""
        with fresh_state() as d:
            path = os.path.join(d, name)
            with open(path, "wb") as f:
                f.write(data)
            got = load()
            kept = [p for p in os.scandir(d) if p.is_file()]
            survived = False
            for p in kept:
                with open(p.path, "rb") as f:
                    survived = survived or f.read() == data
            self.assertTrue(survived, f"{name} was lost on reading: "
                            f"{sorted(p.name for p in kept)}")
            return got

    @fuzz(60)
    @given(files(SETTINGS))
    def test_settings(self, data):
        got = self.read_back("gui_settings.json", data, dialogs.load_settings)
        self.assertIsInstance(got, dict)
        stores.player_layout_of(got)

    @fuzz(60)
    @given(files(AUTOSAVE, AUTOSAVE_KEYS))
    @example(dump({**AUTOSAVE, "version": 99}))
    def test_autosave(self, data):
        got = self.read_back("autosave_playlist.json", data, dialogs.load_autosave)
        self.assertIsInstance(got, (dict, type(None)))

    @fuzz(60)
    @given(files(CARTWALL))
    def test_cartwall(self, data):
        doc = self.read_back("cartwall.json", data,
                             lambda: cartwall.load_doc(stores.load_cartwall_file()))
        self.assertIsInstance(doc, cartwall.WallDoc)
        self.assertTrue(doc.pages)

    @fuzz(60)
    @given(files(TOURNAMENTS, ("m3u", "name", "children", "source")))
    @example(dump({**TOURNAMENTS, "columns": {"hidden": [1], "order": [None, 1]}}))
    def test_tournament_tree(self, data):
        store = dialogs.TOURNAMENTS
        nodes, view, columns = self.read_back("tournaments.json", data, lambda: (
            tree.load_tree(store), tree.load_view(store), tree.load_columns(store)))
        self.assertIsInstance(nodes, list)
        self.assertIn(view, (tree.VIEW_LIST, tree.VIEW_SLOTS))
        self.assertIsInstance(columns["hidden"], list)
        self.assertIsInstance(columns["order"], list)

    @fuzz(60)
    @given(files(PLAY_SESSION))
    def test_evening_played_so_far(self, data):
        got = self.read_back("play_session.json", data, lambda: play_session.load(NOW))
        self.assertIsInstance(got, (play_session.Session, type(None)))

    @fuzz(60)
    @given(files({"looks": [LOOK]}))
    def test_own_looks(self, data):
        try:
            got = self.read_back("looks.json", data, user_looks.load_looks)
            self.assertIsInstance(got, list)
        finally:
            for look in user_looks.mine():
                del looks.LOOKS[look.key]

    @fuzz(60)
    @given(files(TIMETABLE))
    def test_presenter_timetable(self, data):
        got = self.read_back("presenter_timetable.json", data, timetable.load_timetable)
        self.assertIsInstance(got, timetable.Timetable)

    @fuzz(60)
    @given(files(ON_AIR))
    @example(dump({**ON_AIR, "table": float("inf")}))
    def test_crash_note(self, data):
        """main_load's _offer_crash_resume: the note as read, into _on_air_row."""
        desk = NS(_deckset=NS(all_tables=[NS(_row_meta=NS(numbered=list))] * 3))

        def offer():
            note = stores.ON_AIR.read()
            return TrackLoadMixin._on_air_row(desk, note) if isinstance(note, dict) else None
        self.assertIsNone(self.read_back("on_air.json", data, offer))


class WindowStartFuzzTest(LoadedWindow):
    """A real start on such files. Few inputs: each builds a window."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The desk as the app saves it, with a generated deck on it: the
        # autosave inputs start from this one so the restore gets far.
        with fresh_state():
            win = cls.gui.MainWindow()
            try:
                for _ in range(3000):
                    QTest.qWait(10)
                    if win._cfg.generate_btn.isEnabled():
                        break
                win._cfg.generate_btn.click()
                cls.desk = win._build_env()
                # Without a deck in it the restore would have nothing to get
                # wrong, and the inputs below would test only the settings.
                if not (cls.desk or {}).get("deck_a"):
                    raise AssertionError(f"Generate left no deck to start from: {cls.desk!r}")
            finally:
                win._playback.token += 1
                from tests.qt_test_support import reap_widget
                reap_widget(win)

    def setUp(self):
        """No window here: each input builds its own."""

    def start(self, state: str, extra: dict):
        """A window on the files in `state`, until its start is done."""
        self._before = set(QApplication.topLevelWidgets())
        self.win = self.gui.MainWindow()
        try:
            for _ in range(3000):
                QTest.qWait(10)
                if self.win.isVisible() and not self.win._loading_dlg.isVisible():
                    break
            else:
                self.fail(f"the window never finished starting on {extra!r}")
            QTest.qWait(300)       # the deferred start steps: 🆘, ▶ the evening
        finally:
            self._reap_all()

    @fuzz(4)
    @given(settings=json_docs(sorted(SETTINGS)),
           desk=st.data(),
           others=st.fixed_dictionaries({
               "cartwall.json": files(CARTWALL),
               "tournaments.json": files(TOURNAMENTS),
               "on_air.json": files(ON_AIR),
               "play_session.json": files(PLAY_SESSION)}))
    def test_a_start_on_damaged_state(self, settings, desk, others):
        env = desk.draw(perturbed(self.desk), label="autosave")
        if isinstance(env, dict):
            env["version"] = desk.draw(st.sampled_from(
                (1, 2, 3, dialogs.AUTOSAVE_VERSION)), label="version")
        extra = settings if isinstance(settings, dict) else {}
        # The library folders as the sandbox has them, or there is nothing to
        # restore onto.
        written = {"gui_settings.json": dump({**extra, **self.settings}),
                   "autosave_playlist.json": dump(env), **others}
        trap = ExceptionTrap(NS(log=[f"{k}: {v[:300]!r}" for k, v in written.items()],
                                step=0))

        def critical(parent, title, text, *a, **kw):
            if "monkey test:" in str(text):   # the sandbox's refusal, said right
                return QMessageBox.StandardButton.Ok
            return trap.critical(parent, title, text, *a, **kw)
        with fresh_state() as d, trap, \
                mock.patch.object(self.gui, "load_settings", dialogs.load_settings), \
                mock.patch.object(QMessageBox, "critical", critical):
            for name, data in written.items():
                with open(os.path.join(d, name), "wb") as f:
                    f.write(data)
            self.start(d, extra)
        self.assertFalse(trap.caught, "\n\n".join(trap.caught))


if __name__ == "__main__":
    unittest.main()
