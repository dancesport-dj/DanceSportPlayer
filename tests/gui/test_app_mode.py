#!/usr/bin/env python3
"""Tests for the app mode — planner / player / both.

Run:  py -m unittest tests.gui.test_app_mode -v

The mode is asked once on the first start and only ever hides UI. Three things
therefore have to hold, and all three are easy to break: a player-only install
must still be able to reach ⚙ Settings (otherwise the choice is a one-way
door), a settings file written before the option existed must read as 'both'
rather than silently stripping half the app, and switching the mode back has to
bring the other side straight back without a restart.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_appmode_"))

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QTabWidget  # noqa: E402

from gui import dialogs  # noqa: E402
from planner import config  # noqa: E402
from gui.dialogs import (  # noqa: E402
    APP_MODES, PLAYER_FIRST_START, AppModeDialog, SettingsDialog, app_mode_of,
    app_title, ensure_app_mode,
)
from gui.main_persist import layout_settings  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class _PlayerBuild:
    """Pretend this process is a player-only .exe.

    `player_build()` asks `build_flavor()` through the module global, so
    replacing that one name is enough — no need to fake a frozen sys."""

    def __enter__(self):
        self._real = config.build_flavor
        config.build_flavor = lambda: "player"
        return self

    def __exit__(self, *_exc):
        config.build_flavor = self._real


class _Qt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


class TitleTest(unittest.TestCase):

    def test_each_mode_names_its_side(self):
        self.assertEqual(app_title("both"), "DanceSport Planner & Player")
        self.assertEqual(app_title("player"), "DanceSport Player")
        self.assertEqual(app_title("planner"), "DanceSport Planner")


class ModeOfTest(unittest.TestCase):

    def test_every_known_mode_survives(self):
        for mode in APP_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(app_mode_of({"app_mode": mode}), mode)

    def test_an_older_settings_file_reads_as_both(self):
        """No key = written before the option existed = show everything."""
        self.assertEqual(app_mode_of({}), "both")

    def test_garbage_reads_as_both(self):
        self.assertEqual(app_mode_of({"app_mode": "dj"}), "both")
        self.assertEqual(app_mode_of({"app_mode": None}), "both")


class ChooserDialogTest(_Qt):

    def _dlg(self, *args):
        dlg = AppModeDialog(*args)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_opens_on_the_current_mode(self):
        self.assertEqual(self._dlg("player").mode(), "player")

    def test_it_defaults_to_both(self):
        self.assertEqual(self._dlg().mode(), "both")

    def test_picking_a_mode_is_what_it_reports(self):
        dlg = self._dlg()
        dlg._radios["planner"].setChecked(True)
        self.assertEqual(dlg.mode(), "planner")

    def test_the_choices_are_exactly_the_known_modes(self):
        self.assertEqual(set(self._dlg()._radios), set(APP_MODES))

    def test_no_html_entity_leaks_into_a_plain_label(self):
        """A QLabel only reads markup when the text holds a tag — an escaped
        '&amp;' in a tagless string is shown to the user verbatim."""
        from PySide6.QtWidgets import QLabel

        texts = [lbl.text() for lbl in self._dlg().findChildren(QLabel)]
        self.assertTrue(any("Paths & search" in t for t in texts), texts)
        self.assertFalse(any("&amp;" in t for t in texts), texts)


class EnsureAppModeTest(_Qt):
    """`ensure_app_mode` must ask exactly once — never again on later starts."""

    def setUp(self):
        self.settings = {}
        self.saved = []
        self.shown = []
        self.warned = []
        self.pick = "player"
        # The ffmpeg warning is patched out for the same reason as the chooser:
        # on a machine without ffmpeg (CI) the real one is a modal box.
        for name, repl in (("load_settings", lambda: dict(self.settings)),
                           ("save_settings", self.saved.append),
                           ("AppModeDialog", self._make_dialog),
                           ("warn_if_ffmpeg_missing",
                            lambda *a: self.warned.append(True))):
            self.addCleanup(setattr, dialogs, name,
                            getattr(dialogs, name))
            setattr(dialogs, name, repl)

    def _make_dialog(self, *_a, **_kw):
        """A chooser that never enters an event loop — a real exec() offscreen
        would hang the whole test run with no output."""
        self.shown.append(True)
        pick = self.pick
        return type("_Stub", (), {"exec": lambda s: 0,
                                  "mode": lambda s: pick})()

    def test_the_first_start_asks_and_persists(self):
        self.assertEqual(ensure_app_mode(), "player")
        self.assertEqual(self.shown, [True])
        self.assertEqual(self.saved[0]["app_mode"], "player")

    def test_choosing_player_arms_the_venue_layout(self):
        ensure_app_mode()
        self.assertTrue(self.saved[0][PLAYER_FIRST_START])

    def test_the_other_modes_arm_nothing(self):
        for mode in ("planner", "both"):
            with self.subTest(mode=mode):
                self.pick = mode
                self.saved.clear()   # the patched save_settings holds this list
                ensure_app_mode()
                self.assertNotIn(PLAYER_FIRST_START, self.saved[0])

    def test_the_first_start_checks_for_ffmpeg(self):
        """Right after the welcome question, while the machine is being set
        up — that is when a missing ffmpeg is cheap to fix."""
        ensure_app_mode()
        self.assertEqual(self.warned, [True])

    def test_a_later_start_never_asks_again(self):
        self.settings = {"app_mode": "planner"}
        self.assertEqual(ensure_app_mode(), "planner")
        self.assertEqual(self.shown, [])
        self.assertEqual(self.saved, [])
        self.assertEqual(self.warned, [])   # and never nags about ffmpeg again

    def test_an_unusable_stored_mode_asks_again(self):
        self.settings = {"app_mode": "dj"}
        self.assertEqual(ensure_app_mode(), "player")
        self.assertEqual(self.shown, [True])

    def test_a_player_build_never_asks(self):
        """That .exe has no planning half to switch to — the question would
        have exactly one answer."""
        with _PlayerBuild():
            self.assertEqual(ensure_app_mode(), "player")
        self.assertEqual(self.shown, [])
        self.assertEqual(self.saved[0]["app_mode"], "player")

    def test_a_player_build_still_arms_the_venue_layout(self):
        with _PlayerBuild():
            ensure_app_mode()
        self.assertTrue(self.saved[0][PLAYER_FIRST_START])

    def test_a_player_build_still_checks_for_ffmpeg(self):
        with _PlayerBuild():
            ensure_app_mode()
        self.assertEqual(self.warned, [True])

    def test_a_player_build_settles_after_the_first_start(self):
        """Once 'player' is on file there is nothing left to write — otherwise
        every launch would re-arm the venue layout and wipe the user's own."""
        self.settings = {"app_mode": "player"}
        with _PlayerBuild():
            self.assertEqual(ensure_app_mode(), "player")
        self.assertEqual(self.saved, [])
        self.assertEqual(self.warned, [])

    def test_a_player_build_overrules_a_carried_over_setting(self):
        """A gui_settings.json copied from a full install must not hand this
        .exe a planning UI whose generator it cannot run."""
        self.settings = {"app_mode": "both"}
        with _PlayerBuild():
            self.assertEqual(ensure_app_mode(), "player")
            self.assertEqual(app_mode_of({"app_mode": "both"}), "player")
        self.assertEqual(self.shown, [])


class FfmpegHintTest(unittest.TestCase):
    """Which install instructions a platform gets. Pure text, no Qt."""

    def test_every_platform_python_reports_is_mapped(self):
        for platform, want in (("win32", "windows"), ("win64", "windows"),
                               ("darwin", "macos"), ("linux", "linux")):
            with self.subTest(platform=platform):
                self.assertEqual(dialogs.ffmpeg_platform(platform), want)

    def test_an_unknown_unix_still_gets_a_package_manager(self):
        """A BSD installs ffmpeg from a package manager like any Linux — an
        empty dialog would be worse than a nearly-right one."""
        self.assertEqual(dialogs.ffmpeg_platform("freebsd14"), "linux")

    @staticmethod
    def _cmds(platform):
        return [cmd for _cap, cmd in dialogs.ffmpeg_install_steps(platform)]

    def test_each_platform_names_its_own_tool_and_no_others(self):
        cmds = {p: " ".join(self._cmds(p))
                for p in ("win32", "darwin", "linux")}
        self.assertIn("winget install Gyan.FFmpeg", cmds["win32"])
        self.assertIn("brew install ffmpeg", cmds["darwin"])
        for mgr in ("apt install ffmpeg", "dnf install ffmpeg", "pacman -S ffmpeg"):
            self.assertIn(mgr, cmds["linux"])
        self.assertNotIn("brew", cmds["win32"])
        self.assertNotIn("winget", cmds["darwin"])
        self.assertNotIn("winget", cmds["linux"])

    def test_a_brew_command_always_brings_homebrew_itself(self):
        """`brew install` is no use on a machine that has no brew yet — the
        bootstrap one-liner has to sit right under it, on both platforms that
        offer brew at all."""
        for platform in ("darwin", "linux"):
            with self.subTest(platform=platform):
                cmds = self._cmds(platform)
                self.assertIn("brew install ffmpeg", cmds)
                boot = cmds[-1]
                self.assertTrue(boot.startswith("/bin/bash -c"), boot)
                self.assertIn("https://raw.githubusercontent.com/Homebrew/"
                              "install/HEAD/install.sh", boot)

    def test_linux_offers_brew_after_its_own_package_managers(self):
        """Homebrew runs on Linux and needs no root, but it is the fallback —
        a Debian box should reach for apt first."""
        cmds = self._cmds("linux")
        self.assertLess(cmds.index("sudo apt install ffmpeg"),
                        cmds.index("brew install ffmpeg"))

    def test_a_command_is_bare_shell_text_and_nothing_else(self):
        """Each one lands in a copy field and goes straight into a terminal —
        markup or a caption mixed in would be pasted along with it."""
        for platform in ("win32", "darwin", "linux"):
            for cmd in self._cmds(platform):
                with self.subTest(cmd=cmd):
                    self.assertNotIn("<", cmd)
                    self.assertNotIn("&nbsp;", cmd)
                    self.assertEqual(cmd, cmd.strip())

    def test_only_windows_has_a_manual_download_note(self):
        self.assertIn("gyan.dev", dialogs.ffmpeg_install_note("win32"))
        self.assertEqual(dialogs.ffmpeg_install_note("darwin"), "")
        self.assertEqual(dialogs.ffmpeg_install_note("linux"), "")


class FindFfmpegTest(unittest.TestCase):
    """Locating ffmpeg when PATH alone does not have it."""

    def test_every_package_manager_prefix_we_recommend_is_probed(self):
        """A .app started from Finder inherits launchd's PATH, which holds no
        /opt/homebrew/bin — a brew-installed ffmpeg is there and invisible to
        shutil.which, so the prefixes have to be checked directly. Anything the
        install dialog tells the user to run has to be findable afterwards."""
        from shared import audio_probes

        cands = [str(p).replace("\\", "/")
                 for p in audio_probes._FFMPEG_CANDIDATES]
        for prefix in ("/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin",
                       "/home/linuxbrew/.linuxbrew/bin"):
            with self.subTest(prefix=prefix):
                self.assertIn(prefix + "/ffmpeg", cands)

    def test_a_candidate_stands_in_for_an_empty_path(self):
        import shutil
        from pathlib import Path

        from shared import audio_probes

        exe = Path(tempfile.mkdtemp(prefix="dp_ffmpeg_")) / "ffmpeg"
        exe.write_text("")
        self.addCleanup(setattr, audio_probes, "_FFMPEG_CANDIDATES",
                        audio_probes._FFMPEG_CANDIDATES)
        self.addCleanup(setattr, shutil, "which", shutil.which)
        audio_probes._FFMPEG_CANDIDATES = (Path("/nowhere/ffmpeg"), exe)
        shutil.which = lambda *_a, **_kw: None
        self.assertEqual(audio_probes.find_ffmpeg(), str(exe))

    def test_an_unpacked_build_of_any_version_is_found_newest_first(self):
        """The docs say to unpack the gyan build next to the app; its folder
        name carries the version, so an update must not need a code change."""
        from pathlib import Path

        from shared import audio_probes

        root = Path(tempfile.mkdtemp(prefix="dp_ffmpeg_"))
        for version in ("8.1.1", "10.0", "9.0.2"):
            bin_dir = root / f"ffmpeg-{version}-essentials_build" / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "ffmpeg.exe").write_text("")
        found = [p.parents[1].name for p in audio_probes.unpacked_ffmpeg_builds(root)]
        self.assertEqual(found, ["ffmpeg-10.0-essentials_build",
                                 "ffmpeg-9.0.2-essentials_build",
                                 "ffmpeg-8.1.1-essentials_build"])


class _StubDialog:
    """A dialog that records instead of opening — a real exec() offscreen would
    hang the run with no output."""

    last = None

    def __init__(self, *_a, **_kw):
        self.shown = 0
        _StubDialog.last = self

    def exec(self):
        self.shown += 1


class FfmpegWarningTest(unittest.TestCase):
    """The first-start warning fires only when ffmpeg really is missing."""

    def _patch(self, exe):
        for name, repl in (("find_ffmpeg", lambda: exe),
                           ("FfmpegMissingDialog", _StubDialog)):
            self.addCleanup(setattr, dialogs, name,
                            getattr(dialogs, name))
            setattr(dialogs, name, repl)
        _StubDialog.last = None

    def test_an_installed_ffmpeg_says_nothing(self):
        self._patch("/usr/bin/ffmpeg")
        self.assertFalse(dialogs.warn_if_ffmpeg_missing())
        self.assertIsNone(_StubDialog.last)

    def test_a_missing_ffmpeg_opens_the_dialog(self):
        self._patch(None)
        self.assertTrue(dialogs.warn_if_ffmpeg_missing())
        self.assertEqual(_StubDialog.last.shown, 1)


class FfmpegDialogTest(_Qt):
    """The dialog itself — built offscreen, never exec'd."""

    def _dlg(self, platform):
        dlg = dialogs.FfmpegMissingDialog(platform)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_says_what_still_works_and_what_does_not(self):
        from PySide6.QtWidgets import QLabel

        texts = " ".join(lbl.text()
                         for lbl in self._dlg("win32").findChildren(QLabel))
        self.assertIn("still build and play", texts)
        self.assertIn("loudness", texts)
        self.assertIn("restart the app", texts)

    def test_every_command_gets_its_own_copy_row(self):
        for platform in ("win32", "darwin", "linux"):
            with self.subTest(platform=platform):
                dlg = self._dlg(platform)
                self.assertEqual([r.field.text() for r in dlg.rows],
                                 [c for _cap, c in
                                  dialogs.ffmpeg_install_steps(platform)])

    def test_a_command_field_cannot_be_edited_into_something_else(self):
        self.assertTrue(all(r.field.isReadOnly() for r in self._dlg("linux").rows))

    def test_the_button_puts_the_command_on_the_clipboard(self):
        """The whole point: the Homebrew bootstrap is 90 characters of URL that
        nobody should be retyping off a dialog."""
        row = self._dlg("darwin").rows[-1]
        row.btn.click()
        self.assertEqual(QApplication.clipboard().text(), row.field.text())

    def test_the_button_confirms_the_copy_and_goes_back(self):
        """A clipboard write is invisible — without feedback the user clicks
        again wondering whether it took."""
        row = self._dlg("win32").rows[0]
        row.btn.click()
        self.assertEqual(row.btn.text(), "✓")
        QTest.qWait(row._COPIED_MS + 200)
        self.assertEqual(row.btn.text(), "⧉")

    def test_closing_right_after_a_copy_leaves_no_timer_on_a_dead_button(self):
        """Copy, then close within the 1.2 s: the reset used to fire on the
        deleted button and raise "Internal C++ object already deleted"."""
        import sys
        from unittest import mock

        import shiboken6

        errors = []
        dlg = self._dlg("win32")
        row = dlg.rows[0]
        row.btn.click()
        shiboken6.delete(dlg)
        with mock.patch.object(sys, "excepthook",
                               lambda *exc: errors.append(exc[1])):
            QTest.qWait(dialogs._CopyRow._COPIED_MS + 200)
        self.assertEqual(errors, [])


class SettingsDialogTest(_Qt):

    def _dlg(self, settings):
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def _checks_tab(dlg):
        tabs = dlg.findChild(QTabWidget)
        idx = [i for i in range(tabs.count())
               if tabs.tabText(i).endswith("Checks")][0]
        return tabs, idx

    def test_the_mode_round_trips(self):
        for mode in APP_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(self._dlg({"app_mode": mode}).values()["app_mode"],
                                 mode)

    def test_an_older_settings_file_comes_back_as_both(self):
        self.assertEqual(self._dlg({}).values()["app_mode"], "both")

    def test_foreign_keys_still_ride_along(self):
        """values() is saved as the WHOLE settings dict — the play settings of
        other panels must not be dropped by this addition."""
        self.assertEqual(self._dlg({"app_mode": "both",
                                    "pause_secs": 42}).values()["pause_secs"], 42)

    def test_the_checks_tab_is_hidden_for_a_player(self):
        tabs, idx = self._checks_tab(self._dlg({"app_mode": "player"}))
        self.assertFalse(tabs.isTabVisible(idx))

    def test_the_checks_tab_is_there_for_a_planner(self):
        tabs, idx = self._checks_tab(self._dlg({"app_mode": "planner"}))
        self.assertTrue(tabs.isTabVisible(idx))

    def test_switching_the_combo_reveals_the_checks_tab(self):
        dlg = self._dlg({"app_mode": "player"})
        tabs, idx = self._checks_tab(dlg)
        dlg._app_mode_combo.setCurrentIndex(dlg._app_mode_combo.findData("both"))
        self.assertTrue(tabs.isTabVisible(idx))

    def test_the_tso_band_of_a_dance_round_trips(self):
        self.assertEqual(
            self._dlg({"tso_band": {"RB": "lower"}}).values()["tso_band"],
            {"RB": "lower"})

    def test_the_dances_left_on_the_heat_mean_are_not_written_out(self):
        """The mean is what the 🎚 button does without the setting; ten "mean"
        entries would freeze today's default into the file."""
        self.assertEqual(self._dlg({}).values()["tso_band"], {})

    def test_picking_a_takt_reaches_the_settings(self):
        dlg = self._dlg({})
        combo = dlg._band_combos["RB"]
        combo.setCurrentIndex(combo.findData("middle"))
        self.assertEqual(dlg.values()["tso_band"], {"RB": "middle"})

    def test_the_choices_name_the_takt_they_pitch_to(self):
        """"Lower" is a word; T24 is what the hall hears."""
        combo = self._dlg({})._band_combos["RB"]
        self.assertEqual([combo.itemText(i) for i in range(combo.count())],
                         ["Middle of the round", "Lower — T24", "Middle — T25",
                          "Upper — T26"])

    def test_the_audio_backend_round_trips(self):
        """🔊 Only read at the next start — but it has to survive being saved."""
        self.assertEqual(
            self._dlg({"media_backend": "ffmpeg"}).values()["media_backend"],
            "ffmpeg")

    def test_an_older_settings_file_comes_back_on_the_default_backend(self):
        from gui.dialogs import media_backend_of

        self.assertEqual(self._dlg({}).values()["media_backend"],
                         media_backend_of({}))


class NoStrayWindowsTest(_Qt):
    """⚙ Settings must open as ONE window.

    A widget shown before it is put into a layout has no parent yet, and Qt
    gives a parentless widget shown a window of its own — half a dozen of them
    flashed up over the desk and vanished again as the dialog was built. Every
    row that is switched on or off (App mode, the librosa jobs) is now added
    first and only then made visible."""

    def test_building_it_flashes_no_windows_over_the_desk(self):
        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtWidgets import QWidget

        strays = []

        class _Spy(QObject):
            def eventFilter(self, obj, ev):
                if (ev.type() == QEvent.Type.Show
                        and isinstance(obj, QWidget) and obj.parent() is None):
                    strays.append(obj)
                return False

        spy = _Spy()
        self.app.installEventFilter(spy)
        self.addCleanup(self.app.removeEventFilter, spy)
        dlg = SettingsDialog({})
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(strays, [])


class PlaySetsTabTest(_Qt):
    """🎛 Play sets — the defaults behind the 🏆 / 🎉 buttons of the ▶ panel."""

    def _dlg(self, settings):
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def _tab(dlg):
        tabs = dlg.findChild(QTabWidget)
        idx = [i for i in range(tabs.count())
               if tabs.tabText(i).endswith("Play sets")][0]
        return tabs, idx

    def test_the_built_in_sets_are_what_it_starts_on(self):
        from planner.play_sets import _PARTY_SET, _TOURNAMENT_SET
        vals = self._dlg({}).values()
        for key, built_in in (("tournament_set", _TOURNAMENT_SET),
                              ("party_set", _PARTY_SET)):
            got = dict(vals[key])
            got.pop("tso")          # its own default — see below
            self.assertEqual(got, built_in)

    def test_the_tso_pitch_is_one_of_them(self):
        """🎚 On for a heat, where every title of a round is pitched to the
        dance's mean tempo; off for a party of ten different dances."""
        vals = self._dlg({}).values()
        self.assertIs(vals["tournament_set"]["tso"], True)
        self.assertIs(vals["party_set"]["tso"], False)

    def test_a_configured_set_is_shown_and_handed_back(self):
        """Round trip: what is in the file comes up in the tab and out again."""
        mine = {"secs": 105, "fade": 2.5, "advance": True, "pause_off": False,
                "announce": True, "loudness": False, "dblclick": True,
                "tso": False}
        self.assertEqual(self._dlg({"tournament_set": mine}).values()["tournament_set"],
                         mine)

    def test_changing_a_value_is_what_gets_saved(self):
        dlg = self._dlg({})
        w = dlg._set_widgets["party"]
        w["length"].setCurrentIndex(w["length"].findData(45))
        w["boxes"]["advance"].setChecked(False)
        got = dlg.values()["party_set"]
        self.assertEqual(got["secs"], 45)
        self.assertIs(got["advance"], False)

    def test_changing_the_tso_pitch_is_what_gets_saved(self):
        dlg = self._dlg({})
        dlg._set_widgets["party"]["boxes"]["tso"].setChecked(True)
        self.assertIs(dlg.values()["party_set"]["tso"], True)

    def test_full_length_is_offered_and_survives(self):
        """0 is the 'full' rung — it must not read back as 'nothing picked'."""
        dlg = self._dlg({"party_set": {"secs": 0}})
        self.assertEqual(dlg._set_widgets["party"]["length"].currentData(), 0)
        self.assertEqual(dlg.values()["party_set"]["secs"], 0)

    def test_the_fade_out_is_one_of_them(self):
        """A heat and a party want different ramps, so it belongs to the set
        rather than sitting only on the panel."""
        dlg = self._dlg({})
        dlg._set_widgets["party"]["fade"].setValue(1.5)
        self.assertEqual(dlg.values()["party_set"]["fade"], 1.5)

    def test_a_configured_fade_comes_back_up_in_the_tab(self):
        dlg = self._dlg({"tournament_set": {"fade": 2.5}})
        self.assertEqual(dlg._set_widgets["tournament"]["fade"].value(), 2.5)

    def test_a_length_can_be_typed_instead_of_picked(self):
        """The rungs are 15 s apart — 1:37 has to be sayable here too."""
        dlg = self._dlg({})
        dlg._set_widgets["party"]["length"].setEditText("1:37")
        self.assertEqual(dlg.values()["party_set"]["secs"], 97)

    def test_a_typed_length_is_shown_again_next_time(self):
        """findData misses an off-ladder length — without the fallback the tab
        would come up on 'full' and silently save that."""
        dlg = self._dlg({"party_set": {"secs": 97}})
        length = dlg._set_widgets["party"]["length"]
        self.assertEqual(length.currentText(), "1:37")
        self.assertEqual(dlg.values()["party_set"]["secs"], 97)

    def test_typing_full_is_understood(self):
        dlg = self._dlg({"party_set": {"secs": 45}})
        dlg._set_widgets["party"]["length"].setEditText("full")
        self.assertEqual(dlg.values()["party_set"]["secs"], 0)

    def test_typed_nonsense_keeps_what_the_tab_opened_on(self):
        """A slip must not reset the set to 'full'."""
        dlg = self._dlg({"party_set": {"secs": 45}})
        dlg._set_widgets["party"]["length"].setEditText("half past three")
        self.assertEqual(dlg.values()["party_set"]["secs"], 45)

    def test_a_picked_rung_still_wins(self):
        dlg = self._dlg({})
        length = dlg._set_widgets["party"]["length"]
        length.setCurrentIndex(length.findData(60))
        self.assertEqual(dlg.values()["party_set"]["secs"], 60)

    def test_the_paso_doble_stop_is_not_one_of_them(self):
        """Too unreliable to bundle into a button — left on the panel."""
        for key in ("tournament_set", "party_set"):
            self.assertNotIn("pd_highlight_stop", self._dlg({}).values()[key])

    def test_the_other_settings_still_ride_along(self):
        self.assertEqual(self._dlg({"pause_secs": 42}).values()["pause_secs"], 42)

    def test_a_planner_only_install_does_not_see_the_tab(self):
        """No Playing panel — the two buttons it configures are nowhere."""
        tabs, idx = self._tab(self._dlg({"app_mode": "planner"}))
        self.assertFalse(tabs.isTabVisible(idx))

    def test_a_player_only_install_does(self):
        tabs, idx = self._tab(self._dlg({"app_mode": "player"}))
        self.assertTrue(tabs.isTabVisible(idx))


class _ModeWindowCase(_Qt):
    """The window itself, built offscreen against a stubbed library loader."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        # Every window here is a "fresh install" — drop what the previous one
        # left behind, or e.g. the venue layout leaks into the next test.
        layout_settings().clear()   # in the state dir, not the registry
        dialogs.AUTOSAVE.remove()

    def _win(self, mode, **extra):
        self.gui.load_settings = lambda *a, **kw: dict({"app_mode": mode}, **extra)
        win = self.gui.MainWindow()
        win._loading_dlg.accept()      # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        return win

    @staticmethod
    def _resize_event(win):
        from PySide6.QtGui import QResizeEvent

        return QResizeEvent(win.size(), win.size())


class ModeVisibilityTest(_ModeWindowCase):
    """What each mode shows and hides, and what a switch brings back."""

    def test_the_startup_splash_carries_the_same_name(self):
        """It is the first thing on screen — a player-only install must not be
        greeted by the planner's name."""
        for mode in ("player", "both"):
            with self.subTest(mode=mode):
                win = self._win(mode)
                self.assertEqual(win._loading_dlg.windowTitle(), app_title(mode))

    def test_both_shows_everything_and_names_both_sides(self):
        win = self._win("both")
        self.assertEqual(win.windowTitle(), "DanceSport Planner & Player")
        self.assertTrue(win._mode_row_w.isVisibleTo(win))
        self.assertTrue(all(b.isVisibleTo(win) for b in win._planner_btns))
        self.assertTrue(win._cart_btn.isVisibleTo(win))
        # The ConfigPanel's gear is reachable, so the playing panel needs none.
        self.assertFalse(win._play_panel.settings_btn.isVisibleTo(win._play_panel))

    def test_player_only_hides_every_planning_action(self):
        win = self._win("player")
        self.assertEqual(win.windowTitle(), "DanceSport Player")
        self.assertFalse(any(b.isVisibleTo(win) for b in win._planner_btns))
        self.assertFalse(win._mode_row_w.isVisibleTo(win))
        self.assertTrue(win._is_playing_mode())

    def test_player_only_can_still_reach_the_settings(self):
        """Without this the mode would be a one-way door: the ⚙ gear lives on
        the Planning panel, which is exactly what player-only hides. The
        Playing panel grows its own, in the same corner of the same panel."""
        win = self._win("player")
        panel = win._play_panel
        self.assertTrue(panel.settings_btn.isVisibleTo(panel))

    def test_planner_only_hides_the_tournament_floor(self):
        win = self._win("planner")
        self.assertEqual(win.windowTitle(), "DanceSport Planner")
        self.assertFalse(win._mode_row_w.isVisibleTo(win))
        self.assertFalse(win._cart_btn.isVisibleTo(win))
        self.assertFalse(win._cart_btn.isChecked())
        self.assertFalse(win._is_playing_mode())
        self.assertTrue(all(b.isVisibleTo(win) for b in win._planner_btns))

    def test_switching_the_mode_brings_the_other_side_back(self):
        """No restart: _apply_app_mode only ever toggles visibility."""
        win = self._win("player")
        win._settings["app_mode"] = "both"
        win._apply_app_mode()
        self.assertEqual(win.windowTitle(), "DanceSport Planner & Player")
        self.assertTrue(win._mode_row_w.isVisibleTo(win))
        self.assertTrue(all(b.isVisibleTo(win) for b in win._planner_btns))
        self.assertFalse(win._play_panel.settings_btn.isVisibleTo(win._play_panel))

    def test_a_hidden_action_no_longer_demands_toolbar_width(self):
        """The compaction thresholds are measured from the visible row — a
        player-only toolbar must not collapse to icons over buttons it does
        not even show."""
        both = self._win("both")
        both.resizeEvent(self._resize_event(both))
        wide = both._toolbar_full_width
        player = self._win("player")
        player.resizeEvent(self._resize_event(player))
        self.assertLess(player._toolbar_full_width, wide)


class VenueLayoutTest(_ModeWindowCase):
    """The player-only venue layout: laid out once, then never again."""

    def test_the_venue_layout_is_put_in_place_once(self):
        """A player-only first start opens on a flat party list plus library —
        not on an empty tournament grid."""
        win = self._win("player", **{PLAYER_FIRST_START: True})
        self.assertEqual(win._deck_count, 0)          # no playlist decks
        self.assertEqual(win._wish_state, 0)          # no wishlists
        self.assertEqual(win._compact_state, 2)       # no round/dance grouping
        self.assertTrue(win._warmup_toggle_btn.isChecked())   # party list armed
        self.assertTrue(win._lib_btn.isChecked())
        self.assertFalse(win._cart_btn.isChecked())
        # 🎉 the party set, on the party list the panel now stands on
        self.assertIs(win._panel_list(), win._warmup_table)
        self.assertIs(win._play_panel.party_btn.isChecked(), True)
        self.assertEqual(win._list_vals(win._warmup_table)["secs"], 0)

    def test_the_venue_layout_is_never_applied_twice(self):
        """The flag is consumed — from the second start the layout is the
        user's, and re-opening must not throw their decks away."""
        win = self._win("player", **{PLAYER_FIRST_START: True})
        self.assertNotIn(PLAYER_FIRST_START, win._settings)
        again = self._win("player")
        self.assertEqual(again._deck_count, 1)
        self.assertIs(again._panel_list(), again._tableA)

    def test_the_other_modes_never_get_the_venue_layout(self):
        win = self._win("both")
        self.assertEqual(win._deck_count, 1)
        self.assertIs(win._panel_list(), win._tableA)


class DeckCapTest(_ModeWindowCase):
    """⧉ How many playlist decks the view offers.

    A player build stops at four: a venue runs one competition at a time, and
    the eight-deck view exists so a planner can lay several out side by side."""

    def test_a_normal_build_still_walks_on_to_eight(self):
        win = self._win("both")
        win._deck_count = 4
        win._cycle_deck_view()
        self.assertEqual(win._deck_count, 8)

    def test_a_player_build_folds_four_straight_to_the_no_playlist_view(self):
        with _PlayerBuild():
            win = self._win("player")
            win._deck_count = 4
            win._cycle_deck_view()
            self.assertEqual(win._deck_count, 0)

    def test_a_player_build_walks_the_ring_backwards_the_same_way(self):
        """A right click on ⧉ — 0 must come back to 4, not to 8."""
        with _PlayerBuild():
            win = self._win("player")
            win._deck_count = 0
            win._cycle_deck_view(back=True)
            self.assertEqual(win._deck_count, 4)

    def test_a_carried_over_eight_deck_layout_clamps_to_four(self):
        """Settings written by a planner install, opened by the player .exe:
        the second deck tab would otherwise be the only way to reach decks the
        build no longer offers."""
        with _PlayerBuild():
            win = self._win("player")
            win._deck_count = 8
            win._apply_deck_view()
            self.assertEqual(win._deck_count, 4)
            self.assertFalse(win._deck_tabs.isTabVisible(1))


class CollapseButtonsTest(_ModeWindowCase):
    """The one-button collapse and fold, over decks and party list."""

    def test_collapse_and_fold_reach_the_party_list(self):
        """The 🤸 Eintanzen / ETDS party list is a playlist too — leaving it out
        made ⊟ / ⊞ / ▴ / ▾ look broken in the no-playlist view, where it is the
        only list on screen."""
        win = self._win("player", **{PLAYER_FIRST_START: True})
        win._warmup_table.collapse_all()
        win._fold_all_decks(True)
        self.assertTrue(win._warmup_folded)
        win._fold_all_decks(False)
        self.assertFalse(win._warmup_folded)

    def test_one_button_collapses_and_opens_the_playlists_again(self):
        """⊟ and ⊞ are the same button — its caption says what the next click
        does, so the toolbar carries one of them instead of a pair."""
        win = self._win("both")
        win._toggle_collapse_all()
        self.assertTrue(win._all_collapsed)
        self.assertEqual(win._collapse_btn.property("fullText"), "⊞  Expand all")
        win._toggle_collapse_all()
        self.assertFalse(win._all_collapsed)
        self.assertFalse(win._decks[0]._collapsed)
        self.assertEqual(win._collapse_btn.property("fullText"), "⊟  Collapse all")

    def test_one_button_folds_the_decks_and_opens_them_again(self):
        win = self._win("both")
        win._toggle_fold_all_decks()
        self.assertTrue(win._all_decks_folded())
        self.assertEqual(win._fold_decks_btn.property("fullText"),
                         "▾  Unfold decks")
        win._toggle_fold_all_decks()
        self.assertFalse(win._all_decks_folded())
        self.assertEqual(win._fold_decks_btn.property("fullText"),
                         "▴  Fold decks")

    def test_a_deck_folded_by_hand_is_opened_by_the_same_button(self):
        """Anything folded → the click opens everything: the button never asks
        the operator to first fold the rest to get their deck back."""
        win = self._win("both")
        win._toggle_deck_fold(win._decks[0], True)
        win._toggle_fold_all_decks()
        self.assertFalse(win.deck(win._decks[0]).folded)


class PartyListNameTest(_ModeWindowCase):
    """What the party list is called, per mode."""

    def test_the_party_list_drops_eintanzen_from_its_name_for_a_player(self):
        """'Eintanzen' is what you do before a tournament — a player-only
        install never prepares one, so there the panel is simply the party."""
        win = self._win("player")
        self.assertEqual(win._warmup_default_name(), "Party")
        for btn in (win._warmup_gen_btn, win._warmup_toggle_btn):
            self.assertIn("Party", btn.property("fullText"))
            self.assertNotIn("Eintanzen", btn.property("fullText"))
        # Only the toggle is on screen here (the generator is planner-only), and
        # its tooltip is the one text that would still say the word.
        self.assertNotIn("Eintanzen", win._warmup_toggle_btn.toolTip())
        self.assertNotIn("Eintanzen",
                         win.deck(win._warmup_table).header.text())

    def test_the_party_list_keeps_both_names_where_both_happen(self):
        win = self._win("both")
        self.assertEqual(win._warmup_default_name(), "Eintanzen / Party")
        self.assertEqual(win._warmup_gen_btn.property("fullText"),
                         "🤸  Eintanzen / Party")
        self.assertEqual(win._warmup_toggle_btn.property("fullText"),
                         "🤸  Eintanzen / Party ▾")

    def test_the_two_warmup_buttons_stay_distinct_when_iconized(self):
        """Relabelling must not drop the toggle's ▾ — without it the two 🤸
        buttons are the same square in the compacted toolbar."""
        win = self._win("player")
        self.assertEqual(win._warmup_toggle_btn.property("iconText"), "🤸▾")
        self.assertEqual(win._warmup_gen_btn.property("iconText"), "🤸")

    def test_switching_the_mode_renames_the_party_list(self):
        win = self._win("player")
        win._settings["app_mode"] = "both"
        win._apply_app_mode()
        self.assertIn("Eintanzen", win._warmup_toggle_btn.property("fullText"))
        self.assertEqual(win._warmup_toggle_btn.property("iconText"), "🤸▾")


class PlayerMenuTest(_Qt):
    """The right-click menu of a playlist, in a player-only install.

    🔎 Find similar and 📜 Find planned before are both planning work — they
    search the library for a better track, or for what an earlier tournament
    used in this slot. A player runs a finished playlist and has neither a
    library nor a tournament history, so the two entries stay off the menu
    instead of standing there greyed out."""

    def _menu(self, mode: str):
        """Open a one-song playlist's menu inside a window of `mode`; return the
        action texts. (`QMenu.exec` swapped out the same way as in
        test_presenter_grouping — a real exec would block the run.)"""
        from pathlib import Path
        from unittest import mock

        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QContextMenuEvent
        from PySide6.QtWidgets import QMenu, QWidget

        from gui import table_actions
        from gui.playlist_table import PlaylistTable
        from planner.models import MusicEntry

        opened = []

        class _Menu(QMenu):
            def exec(self, *_args):
                opened.append([a.text() for a in self.actions()])
                return None

        win = QWidget()
        win._settings = {"app_mode": mode}
        self.addCleanup(reap_widget, win)
        t = PlaylistTable()
        t.setParent(win)
        t.load_warmup([MusicEntry(path=Path(r"C:\music\tanzcds\LW1.mp3"),
                                  title="LW 1", dance="LW", duration=180)],
                      "🤸 Party", "both", "S", False, lambda *a: None, None)
        pos = QPoint(5, t.rowViewportPosition(t.rowCount() - 1) + 2)
        with mock.patch.object(table_actions, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        self.assertTrue(opened, "the context menu never opened")
        return opened[0]

    def test_a_player_is_offered_neither_lookup(self):
        texts = self._menu("player")
        self.assertFalse([t for t in texts if "Find similar" in t])
        self.assertFalse([t for t in texts if "Find planned" in t])

    def test_what_a_player_does_need_is_still_there(self):
        """Guards the fixture: the menu itself is not simply empty."""
        self.assertTrue([t for t in self._menu("player") if "Copy file path" in t])

    def test_a_planner_keeps_them(self):
        self.assertTrue([t for t in self._menu("both") if "Find similar" in t])


class _RestartHost:
    """Just enough window for `_offer_restart`: it asks, closes, restarts."""

    def __init__(self, closes: bool = True):
        self._closes = closes
        self.closed = False
        self.messages = []
        self.log = []

    def statusBar(self):
        host = self

        class _Bar:
            def showMessage(self, msg, *_a):
                host.messages.append(msg)
        return _Bar()

    def close(self) -> bool:
        self.closed = True
        self.log.append("close")
        return self._closes


class RestartOfferTest(unittest.TestCase):
    """🔄 Switching the 🔊 audio backend offers a restart, because Qt reads the
    backend once at startup. The order matters: this window has to be gone
    before a new instance starts, or two apps fight over the audio device."""

    def _offer(self, answer, started=True, closes=True):
        from unittest import mock

        from gui import main_global
        from PySide6.QtWidgets import QMessageBox

        host = _RestartHost(closes=closes)

        def _restart():
            host.log.append("restart")
            return started

        with mock.patch.object(QMessageBox, "question", return_value=answer), \
             mock.patch.object(QMessageBox, "warning") as warn, \
             mock.patch.object(main_global, "restart_app", _restart), \
             mock.patch.object(main_global.QApplication, "quit") as quit_:
            main_global.GlobalIndexMixin._offer_restart(
                host, "🔊 Audio backend", "Restart now?")
        return host, quit_, warn

    def test_saying_no_leaves_the_app_running(self):
        from PySide6.QtWidgets import QMessageBox

        host, quit_, _warn = self._offer(QMessageBox.StandardButton.No)
        self.assertEqual(host.log, [])
        self.assertFalse(host.closed)
        quit_.assert_not_called()
        self.assertTrue([m for m in host.messages if "next time" in m])

    def test_yes_closes_first_and_then_starts_the_new_one(self):
        from PySide6.QtWidgets import QMessageBox

        host, quit_, _warn = self._offer(QMessageBox.StandardButton.Yes)
        self.assertEqual(host.log, ["close", "restart"])
        quit_.assert_called_once()

    def test_a_refused_close_restarts_nothing(self):
        """An unsaved playlist can veto the close — then the operator stays in
        the app they were in, rather than getting a second copy of it."""
        from PySide6.QtWidgets import QMessageBox

        host, quit_, _warn = self._offer(QMessageBox.StandardButton.Yes,
                                         closes=False)
        self.assertEqual(host.log, ["close"])
        quit_.assert_not_called()

    def test_a_new_instance_that_will_not_start_keeps_this_one(self):
        from PySide6.QtWidgets import QMessageBox

        host, quit_, warn = self._offer(QMessageBox.StandardButton.Yes,
                                        started=False)
        quit_.assert_not_called()
        warn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
