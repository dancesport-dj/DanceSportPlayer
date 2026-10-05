#!/usr/bin/env python3
"""Tests for the EN/DE chrome translation.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_i18n -v

The catalog is keyed by the English string, so the two promises worth pinning
are the mirror image of the theme's:

* **English is the identity.** Nothing is patched and nothing is rewritten
  unless a translated language is active, so the app as it ships is untouched.
* **A miss falls back to English.** An f-string, a track name, a key nobody has
  translated yet — all come back exactly as they went in, so a half-finished
  catalog is a half-translated app and never a broken one.

The third is the awkward one: the hook patches Qt classes process-wide. Every
test that installs it MUST take it back off, or the 2900 tests that run after
it in the same process start seeing German buttons.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_i18n_"))

import PySide6.QtCore as qtcore  # noqa: E402
from PySide6.QtGui import QAction, QFontMetrics  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox, QComboBox, QDialogButtonBox, QDoubleSpinBox,
    QGroupBox, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QSpinBox,
    QTableWidget, QTabWidget, QWidget,
)

from planner import i18n  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _FakeLocale:
    """Stands in for QLocale so a test can be on a machine it is not on.

    `system_language` imports QLocale at call time, so swapping the name on
    the PySide6.QtCore module is enough."""

    def __init__(self, tags):
        self._tags = list(tags)

    def system(self):
        return self

    def uiLanguages(self):
        return list(self._tags)

    def name(self):
        return self._tags[0] if self._tags else "C"


class LanguageSettingTest(unittest.TestCase):
    """Reading the setting — no Qt involved."""

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_a_language_nobody_offers_falls_back_to_english(self):
        """Stored, but not one of ours — a hand-edited file, or a language
        that was dropped. Not the same as having said nothing."""
        self.assertEqual(i18n.language_of({"language": "klingon"}), "en")

    def test_saying_nothing_takes_the_language_the_computer_is_in(self):
        """First start: there is no setting yet, and guessing English on a
        German Windows is the one guess that is certainly wrong."""
        self.addCleanup(setattr, i18n, "system_language", i18n.system_language)
        for os_says in ("de", "en"):
            i18n.system_language = lambda _s=os_says: _s
            for settings in ({}, None, {"language": ""}, {"language": "   "}):
                with self.subTest(os=os_says, settings=settings):
                    self.assertEqual(i18n.language_of(settings), os_says)

    def test_the_computers_language_is_one_the_app_can_activate(self):
        """Whatever this machine is really set to, the answer is usable."""
        self.assertIn(i18n.system_language(), [c for c, _c, _b in i18n.LANGUAGES])

    def test_the_region_is_dropped_and_a_language_we_lack_is_skipped(self):
        """Swiss German is German; French is nothing we have, so the next
        tag the OS offers gets its turn, and English if none of them fit."""
        self.addCleanup(setattr, qtcore, "QLocale", qtcore.QLocale)
        for tags, want in ((["de-CH", "en-US"], "de"),
                           (["fr-FR", "de-DE"], "de"),
                           (["fr-FR"], "en"),
                           (["en-GB"], "en"),
                           ([], "en")):
            qtcore.QLocale = _FakeLocale(tags)
            with self.subTest(tags=tags):
                self.assertEqual(i18n.system_language(), want)

    def test_a_computer_that_will_not_say_leaves_the_app_english(self):
        """No Qt, no display, no locale — never a crash on the way in."""
        self.addCleanup(setattr, qtcore, "QLocale", qtcore.QLocale)

        class _Broken:
            @staticmethod
            def system():
                raise RuntimeError("no locale here")

        qtcore.QLocale = _Broken
        self.assertEqual(i18n.system_language(), "en")

    def test_a_named_language_is_read(self):
        self.assertEqual(i18n.language_of({"language": "de"}), "de")
        self.assertEqual(i18n.language_of({"language": "  DE  "}), "de")

    def test_every_offered_language_can_actually_be_activated(self):
        """A combo entry with no catalog behind it would silently do nothing."""
        for code, caption, _blurb in i18n.LANGUAGES:
            i18n.set_active(code)
            self.assertEqual(i18n.active_language(), code)
            self.assertTrue(caption.strip())
            if code != i18n.DEFAULT_LANGUAGE:
                self.assertTrue(i18n.is_translated(),
                                f"{code} is offered but has no catalog")

    def test_english_translates_nothing(self):
        i18n.set_active("en")
        self.assertFalse(i18n.is_translated())
        for text in ("Close", "Cancel", "Settings"):
            self.assertEqual(i18n.t(text), text)

    def test_a_miss_falls_back_to_the_english_it_was_keyed_by(self):
        i18n.set_active("de")
        for text in ("Mambo No. 5", "17 tracks queued", ""):
            self.assertEqual(i18n.t(text), text)

    def test_non_strings_pass_through_untouched(self):
        i18n.set_active("de")
        for value in (None, 17, 3.5, ["Close"]):
            self.assertIs(i18n.t(value), value)

    def test_german_actually_translates_something(self):
        i18n.set_active("de")
        self.assertNotEqual(i18n.t("Cancel"), "Cancel")

    def test_verbatim_hands_everything_back_untouched(self):
        """The escape hatch for data. Keying by the English string means a
        song actually called "Time" would otherwise come back as "Zeit"."""
        i18n.set_active("de")
        self.assertNotEqual(i18n.t("Cancel"), "Cancel")
        with i18n.verbatim():
            self.assertEqual(i18n.t("Cancel"), "Cancel")
        self.assertNotEqual(i18n.t("Cancel"), "Cancel")

    def test_verbatim_puts_the_catalog_back_even_after_a_raise(self):
        i18n.set_active("de")
        with self.assertRaises(ValueError):
            with i18n.verbatim():
                raise ValueError
        self.assertNotEqual(i18n.t("Cancel"), "Cancel")


class ArgumentRewriteTest(unittest.TestCase):
    """The positional rule, which is what lets one table cover every shape."""

    def setUp(self):
        i18n.set_active("de")

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_it_translates_the_first_string_at_or_after_the_start(self):
        self.assertEqual(i18n._translated_args(("Cancel",), 0, 1),
                         (i18n.t("Cancel"),))

    def test_an_icon_in_front_does_not_shift_the_text_out_of_reach(self):
        """`addAction("Stop")` and `addAction(icon, "Stop")` are one entry."""
        icon = object()
        self.assertEqual(i18n._translated_args((icon, "Cancel"), 0, 1),
                         (icon, i18n.t("Cancel")))

    def test_only_as_many_strings_as_asked_for_are_touched(self):
        """`addItem(caption, data)` — a string data role is not chrome."""
        args = i18n._translated_args(("Cancel", "Cancel"), 0, 1)
        self.assertEqual(args, (i18n.t("Cancel"), "Cancel"))

    def test_a_start_offset_skips_the_leading_arguments(self):
        """`addTab(widget, "Look")` — and a widget is not a string anyway."""
        self.assertEqual(i18n._translated_args(("Cancel", "Cancel"), 1, 1),
                         ("Cancel", i18n.t("Cancel")))

    def test_the_message_boxes_translate_both_title_and_body(self):
        parent = object()
        args = i18n._translated_args((parent, "Cancel", "Close"), 1, 2)
        self.assertEqual(args, (parent, i18n.t("Cancel"), i18n.t("Close")))


class TextHookTest(unittest.TestCase):
    """The hook itself. Every test here restores it in tearDown."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def german(self, text):
        return i18n.t(text)

    def test_english_installs_no_patch_at_all(self):
        """The identity promise, checked at the strongest point: not "it
        returns the same string" but "the hook never touched Qt"."""
        before = QLabel.__init__
        i18n.set_active("en")
        i18n.install_text_hook()
        self.assertIs(QLabel.__init__, before)
        self.assertEqual(i18n._originals, [])
        self.assertEqual(QPushButton("Cancel").text(), "Cancel")

    def test_the_constructors_are_translated(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        for cls in (QLabel, QPushButton, QCheckBox, QGroupBox):
            widget = cls("Cancel")
            got = widget.title() if cls is QGroupBox else widget.text()
            self.assertEqual(got, self.german("Cancel"), cls.__name__)
        self.assertEqual(QAction("Cancel").text(), self.german("Cancel"))

    def test_a_python_subclass_is_translated_too(self):
        """The app has several, and they never call a patched base directly."""
        class DeckButton(QPushButton):
            pass

        i18n.set_active("de")
        i18n.install_text_hook()
        self.assertEqual(DeckButton("Cancel").text(), self.german("Cancel"))

    def test_the_setters_are_translated(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        lbl = QLabel()
        lbl.setText("Cancel")
        self.assertEqual(lbl.text(), self.german("Cancel"))
        w = QWidget()
        w.setWindowTitle("Cancel")
        self.assertEqual(w.windowTitle(), self.german("Cancel"))

    def test_the_factories_are_translated(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        menu = QMenu()
        self.assertEqual(menu.addAction("Cancel").text(), self.german("Cancel"))
        tabs = QTabWidget()
        tabs.addTab(QWidget(), "Cancel")
        self.assertEqual(tabs.tabText(0), self.german("Cancel"))

    def test_a_tables_column_headers_are_translated(self):
        """Dance / Artist / Title are set in one list, and a list is exactly
        what the positional (start, count) scheme cannot reach into — so the
        headers stayed English while every button around them turned German."""
        i18n.set_active("de")
        i18n.install_text_hook()
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Cancel", "Close"])
        self.assertEqual(table.horizontalHeaderItem(0).text(),
                         self.german("Cancel"))
        self.assertEqual(table.horizontalHeaderItem(1).text(),
                         self.german("Close"))

    def test_a_dialog_button_box_translates_its_own_button(self):
        """The standard buttons come from Qt's translation, but a button the
        app names itself ("🖨  Export PDF") is ours."""
        i18n.set_active("de")
        i18n.install_text_hook()
        box = QDialogButtonBox()
        btn = box.addButton("Cancel", QDialogButtonBox.ButtonRole.ActionRole)
        self.assertEqual(btn.text(), self.german("Cancel"))

    def test_a_spin_box_suffix_is_translated(self):
        """" tracks", " s", " dB" — a word sitting inside the spin box."""
        i18n.set_active("de")
        i18n.install_text_hook()
        for cls in (QSpinBox, QDoubleSpinBox):
            spin = cls()
            spin.setSuffix("Cancel")
            self.assertEqual(spin.suffix(), self.german("Cancel"), cls.__name__)

    def test_a_message_boxs_informative_text_is_translated(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        box = QMessageBox()
        box.setInformativeText("Cancel")
        self.assertEqual(box.informativeText(), self.german("Cancel"))

    def test_a_message_boxs_own_text_and_buttons_are_translated(self):
        """A message box built by hand — `box.setText(...)`,
        `box.addButton("Replace", role)` — goes through QMessageBox's own
        methods, not QLabel's or QDialogButtonBox's, so it needs its own
        patch."""
        i18n.set_active("de")
        i18n.install_text_hook()
        box = QMessageBox()
        box.setText("Cancel")
        self.assertEqual(box.text(), self.german("Cancel"))
        btn = box.addButton("Close", QMessageBox.ButtonRole.ActionRole)
        self.assertEqual(btn.text(), self.german("Close"))
        std = box.addButton(QMessageBox.StandardButton.Ok)
        self.assertIsNotNone(std)

    def test_a_message_boxs_own_window_title_is_translated(self):
        """QMessageBox overrides setWindowTitle, so QWidget's patch never
        reaches it: the 🐞 first-start question read "Error reports" above a
        German body."""
        i18n.set_active("de")
        i18n.install_text_hook()
        box = QMessageBox()
        box.setWindowTitle("Cancel")
        self.assertEqual(box.windowTitle(), self.german("Cancel"))

    def test_a_song_titled_like_a_catalog_key_keeps_its_own_name(self):
        """The collision this module's docstring warns about, met in the real
        library: one track is called "Time" and another "Action", and both are
        column headers elsewhere in the app. The presenter screen is what the
        hall reads the song name off, so a title must never be translated."""
        from player.presenter import _ScrollLabel

        i18n.set_active("de")
        i18n.install_text_hook()
        lbl = _ScrollLabel("#ffffff")
        self.addCleanup(lbl.deleteLater)
        lbl.set_full_text("Cancel")
        self.assertEqual(lbl.text(), "Cancel")

    def test_a_combo_filled_in_one_go_is_deliberately_left_alone(self):
        """`addItems` is NOT patched, and must not be.

        Every one of its call sites fills a combo the app then reads back by
        text — `mode_combo.currentText() == "Past Competitions"` decides
        whether the replay mode runs. Translating the caption would silently
        break the comparison while the screen looked perfectly German. Those
        combos need `addItem(caption, data)` pairs first; until then the
        captions stay English on purpose."""
        i18n.set_active("de")
        i18n.install_text_hook()
        combo = QComboBox()
        combo.addItems(["Cancel"])
        self.assertEqual(combo.itemText(0), "Cancel")

    def test_a_combo_keeps_the_data_role_the_app_navigates_by(self):
        """Every settings combo reads `currentData()`. Translating a string
        data role would break the setting while the caption looked right."""
        i18n.set_active("de")
        i18n.install_text_hook()
        combo = QComboBox()
        combo.addItem("Cancel", "cancel")
        self.assertEqual(combo.itemText(0), self.german("Cancel"))
        self.assertEqual(combo.itemData(0), "cancel")

    def test_what_the_user_typed_is_never_translated(self):
        """A QLineEdit carries data, not chrome: its setText stays untouched
        even though QLabel's and every button's are patched."""
        i18n.set_active("de")
        i18n.install_text_hook()
        edit = QLineEdit()
        edit.setText("Cancel")
        self.assertEqual(edit.text(), "Cancel")

    def test_dynamic_text_survives_the_hook(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        count = 17
        self.assertEqual(QLabel(f"{count} tracks").text(), "17 tracks")

    def test_installing_twice_does_not_stack_wrappers(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        depth = len(i18n._originals)
        i18n.install_text_hook()
        self.assertEqual(len(i18n._originals), depth)

    def test_restoring_really_puts_qt_back(self):
        """The guard the rest of the suite depends on."""
        before = (QLabel.__init__, QLabel.setText, QMenu.addAction)
        i18n.set_active("de")
        i18n.install_text_hook()
        self.assertIsNot(QLabel.__init__, before[0])
        i18n._restore_text_hook()
        self.assertIs(QLabel.__init__, before[0])
        self.assertIs(QLabel.setText, before[1])
        self.assertIs(QMenu.addAction, before[2])
        self.assertEqual(QPushButton("Cancel").text(), "Cancel")


class CatalogQualityTest(unittest.TestCase):
    """What a catalog must not contain, checked rather than trusted."""

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_no_entry_translates_to_itself(self):
        """A key mapped to its own English text is either an oversight or
        noise; either way it costs a lookup and says nothing."""
        i18n.set_active("de")
        same = [k for k, v in i18n._catalog.items() if k == v]
        self.assertEqual(same, [], f"{len(same)} entries translate to themselves")

    def test_no_entry_is_empty(self):
        i18n.set_active("de")
        empty = [k for k, v in i18n._catalog.items() if not str(v).strip()]
        self.assertEqual(empty, [], "a blank translation erases the chrome")

    def test_a_heat_is_called_gruppe_on_a_german_floor(self):
        """The catalog first said "Durchgang", which was chosen without
        asking anybody who runs a tournament. It is the wrong word, and a
        wrong term reads as right — worse than leaving the string English,
        which at least looks untranslated. Checked across every entry and not
        only the "Heat" key, because the word also sits inside two dozen
        tooltips where a stale one would go unnoticed."""
        i18n.set_active("de")
        self.assertEqual(i18n.t("Heat"), "Gruppe")
        stale = [k for k, v in i18n._catalog.items()
                 if "urchgang" in str(v) or "urchgäng" in str(v)]
        self.assertEqual(stale, [], f"{len(stale)} entries still say Durchgang")

    def test_timbre_stays_timbre(self):
        """The catalog translated "timbre" as "Klangfarbe" — a correct
        dictionary answer and the wrong word here. Marcel uses Timbre, the
        method names in the app are Timbre + Rhythm and Timbre Gaussian / KL,
        and the literature is English; a German reader of this app knows
        Timbre and has to stop and think at Klangfarbe.

        Checked over every entry rather than the obvious keys, because the
        word also sat inside long method tooltips — and because "Klangfarbe"
        was not the only rendering: four more entries had quietly dropped to
        "Klangähnlichkeit" for "timbral similarity". Klang on its own stays:
        it translates "sound" (Klangteppich, klanglich ähnlich), not timbre.
        """
        i18n.set_active("de")
        stale = [k for k, v in i18n._catalog.items() if "Klangfarbe" in str(v)
                 or "Klangfarben" in str(v) or "Klangähnlichkeit" in str(v)]
        self.assertEqual(stale, [], f"{len(stale)} entries still avoid Timbre")
        self.assertEqual(i18n.t("Use Timbre Similarity"),
                         "Timbre-Ähnlichkeit nutzen")

    def test_the_accelerator_and_placeholder_shape_survives(self):
        """`&&` is a literal ampersand in Qt chrome and `%s`/`{}` are filled in
        later — a translation that drops one changes what the widget does."""
        i18n.set_active("de")
        for key, value in i18n._catalog.items():
            for token in ("&&", "%s", "%d", "{}"):
                self.assertEqual(
                    key.count(token), str(value).count(token),
                    f"{key!r} -> {value!r} changed the count of {token!r}")


class SwitchCaptionWidthTest(unittest.TestCase):
    """A switch caption that grows in German is lost, not wrapped.

    `_Toggle` (player/play_mode_panel.py) draws its own text and elides it on
    the right, and its sizeHint counts the track and six average characters —
    never the caption. So a switch can not widen the panel to make room: a
    German caption longer than the English one it replaces simply ends in an
    ellipsis at a panel width where the English fitted.

    Only the Paso Doble switch is pinned, because it is the one that was seen
    cut on the floor. `↩ Remember where a title stopped` is wider still in
    German (528px against 396px) and is not shortened yet — pinning it would
    turn a known-open defect into a promise this suite says is kept.
    """

    _PD = "🐂  Stop Paso Doble after highlight"

    def setUp(self):
        self.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_the_paso_doble_switch_fits_where_the_english_one_did(self):
        i18n.set_active("de")
        german = i18n.t(self._PD)
        self.assertNotEqual(german, self._PD, "the caption left the catalog")
        fm = QFontMetrics(self.app.font())
        self.assertLessEqual(
            fm.horizontalAdvance(german), fm.horizontalAdvance(self._PD),
            f"{german!r} is wider than the English caption, so the panel "
            f"width that shows the English one elides this one")


class GermanInTheSourceTest(unittest.TestCase):
    """Two widgets were typed in German and so stayed German in every
    language — the catalog could never reach them, because a catalog is keyed
    by the English string. They ship English now and get to the hall the same
    way the rest of the chrome does."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def german_mode(self):
        i18n.set_active("de")
        i18n.install_text_hook()

    def takt_meter(self):
        from player.takt_meter import TaktMeterOverlay
        w = TaktMeterOverlay()
        self.addCleanup(reap_widget, w)
        return w

    def presenter(self):
        from player.presenter import PresenterWindow
        w = PresenterWindow(lambda: ("LW", "Titel", ("00:10", "− 02:00", False, 0.1),
                                     [("TG", "Zweiter")], ("", "")))
        self.addCleanup(reap_widget, w)
        return w

    def labels(self, w):
        return {lbl.text() for lbl in w.findChildren(QLabel)}

    def test_the_takt_meter_ships_english(self):
        w = self.takt_meter()
        self.assertLessEqual(
            {"♪ Takt meter", "Takt count:", "Target:", "Correction needed:"},
            self.labels(w))
        self.assertEqual(w._apply_btn.text(), "Apply")
        self.assertEqual(w._apply_btn.toolTip(),
                         "Apply this correction to the tempo fader.")
        self.assertEqual(w._sollwert_spin.suffix(), " Takt/min")

    def test_the_takt_meter_reaches_german_through_the_catalog(self):
        self.german_mode()
        w = self.takt_meter()
        self.assertLessEqual(
            {"♪ Takt-Messung", "Taktzahl:", "Sollwert:",
             "Notwendige Taktkorrektur:"},
            self.labels(w))
        self.assertEqual(w._apply_btn.text(), "Übernehmen")
        self.assertEqual(w._apply_btn.toolTip(),
                         "Diese Korrektur auf den Tempo-Fader anwenden.")
        self.assertEqual(w._sollwert_spin.suffix(), " Takte/Min")

    def test_the_presenters_queue_heads_ship_english(self):
        w = self.presenter()
        self.assertEqual(w.last_hdr.text(), "Last")
        self.assertEqual(w.next_hdr.text(), "Next dances")

    def test_the_presenters_queue_heads_reach_german(self):
        self.german_mode()
        w = self.presenter()
        self.assertEqual(w.last_hdr.text(), "Zuletzt")
        self.assertEqual(w.next_hdr.text(), "Nächste Tänze")

    def test_the_german_dance_terms_put_the_presenter_into_german(self):
        # An English desk, but the hall is read German dance names — the
        # screen around them must not be English.
        from planner import terms
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)
        self.addCleanup(setattr, terms, "_english_terms", terms._english_terms)
        terms.apply_settings({"german_dance_terms": True})
        w = self.presenter()
        self.assertEqual(w.last_hdr.text(), "Zuletzt")
        self.assertEqual(w.next_hdr.text(), "Nächste Tänze")
        self.assertEqual(w.hint_lbl.text(),
                         "Esc schließt  ·  Doppelklick verlässt den Vollbildmodus")
        self.assertEqual(w.close_btn.toolTip(),
                         "Den Moderations-Bildschirm schließen")
        self.assertEqual(w.prev_btn.toolTip(), "Vorheriger Titel")


if __name__ == "__main__":
    unittest.main(verbosity=2)
