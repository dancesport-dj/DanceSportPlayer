#!/usr/bin/env python3
"""🔬 The five library analysis passes report in German, not just start in it.

Run:  py -m unittest tests.gui.test_analyze_i18n -v

librosa, 📊 loudness, 🔇 silences, 🎙️ Demucs vocals and 🐂 PD highlights all
run through one shared `_run_library_pass(worker, caption, glyph, noun, unit)`,
and that is where this went wrong. The five nouns — "Audio analysis",
"Loudness analysis", "Silence probe", "Vocal separation", "PD highlight
detection" — have been in the catalog all along, because each is also a
QMessageBox title and the static IS patched. But the progress line, the done
line and the cancelled line put the very same noun into an f-string:

    f"{noun} done — {ok} {unit}"

so the box that opened the pass was German and every line it then wrote to the
status bar was English. Same class as 2c58d61 and a74ee70: nothing here is a
missing catalog entry, because nothing reaches a widget as a whole literal.

`noun` and `unit` stay English at the call sites, for the same reason
`_ALLCACHE_NAMES` does: the noun is handed to QMessageBox.warning as the title
of the error box too, and translating it twice would then look the string up
in German. Translation happens where the line is assembled.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_analyze_i18n_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from gui import main_analyze as man  # noqa: E402
from planner import i18n  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _entry(name, dance="SA"):
    return MusicEntry(path=Path(f"C:/lib/lateincd/{dance}/{name}.mp3"),
                      title=name, dance=dance, bpm=51)


class _Signal:
    def __init__(self):
        self.slot = None

    def connect(self, slot):
        self.slot = slot

    def emit(self, *args):
        self.slot(*args)


class _Worker:
    """A pass that never starts a thread — the four signals are fired by hand."""

    def __init__(self):
        self.progress = _Signal()
        self.done = _Signal()
        self.cancelled = _Signal()
        self.error = _Signal()
        self.started = False

    def cancel(self):
        pass

    def start(self):
        self.started = True


class _Instance:
    """The 🐂 pass is the one that builds a box instead of calling a static —
    it needs a checkbox in it. Same recording, one object further along."""

    def __init__(self, owner):
        self._owner = owner
        self._title = ""

    def setWindowTitle(self, title):
        self._title = title

    def setIcon(self, icon):
        pass

    def setText(self, text):
        self._owner.shown.append(("question", self._title, text))

    def setCheckBox(self, box):
        self.checkbox = box

    def setStandardButtons(self, buttons):
        pass

    def setDefaultButton(self, button):
        pass

    def exec(self):
        return _Box.StandardButton.Yes


class _Check:
    """QCheckBox without a QApplication behind it."""

    def __init__(self, label=""):
        self.label = label
        self.tip = ""

    def setToolTip(self, tip):
        self.tip = tip

    def isChecked(self):
        return False


class _Box:
    """Records what a QMessageBox was asked to show, and answers Yes.

    It translates the title and the text itself, because that is precisely
    what the real static does — planner/i18n.py patches
    QMessageBox.question / information / warning on arguments 1 and 2 — and
    replacing the static takes that with it. Mirroring it is what keeps the
    assertions meaningful: a body still assembled by an f-string goes through
    i18n.t() unchanged and comes out English, which is the bug under test.
    """

    class StandardButton:
        Yes = 1
        No = 0

    class Icon:
        Question = 4

    def __init__(self):
        self.shown = []

    def __call__(self, parent=None):
        return _Instance(self)

    def question(self, parent, title, text, buttons=None, default=None):
        self.shown.append(("question", i18n.t(title), i18n.t(text)))
        return self.StandardButton.Yes

    def information(self, parent, title, text):
        self.shown.append(("information", i18n.t(title), i18n.t(text)))

    def warning(self, parent, title, text):
        self.shown.append(("warning", i18n.t(title), i18n.t(text)))

    def last(self):
        return self.shown[-1][2]

    def last_title(self):
        return self.shown[-1][1]


class _Bar:
    def __init__(self):
        self.msg = None

    def showMessage(self, msg):
        self.msg = msg


class _Cache:
    """Nothing measured yet, so every pass has work to do."""

    def get_silences(self, path, touch_disk=True):
        return None

    def get_vocal_share(self, path):
        return None


class _Lib:
    def __init__(self, entries):
        self.entries = list(entries)


class _Win(QWidget):
    """MainWindow reduced to what a pass reports through.

    A real QWidget, because BusyDialog is the real one: it puts its caption
    through `QLabel(message)`, a patched constructor, so a stub dialog would
    quietly remove the only thing BusyCaptionI18nTest tests.
    """

    _library_paths = man.AnalysisMixin._library_paths
    _run_library_pass = man.AnalysisMixin._run_library_pass
    _analyze_audio = man.AnalysisMixin._analyze_audio
    _analyze_loudness = man.AnalysisMixin._analyze_loudness
    _analyze_silences = man.AnalysisMixin._analyze_silences
    _analyze_vocals = man.AnalysisMixin._analyze_vocals
    _analyze_pd_highlights = man.AnalysisMixin._analyze_pd_highlights

    def __init__(self, entries=None, dance="SA"):
        super().__init__()
        self._lib = _Lib(entries if entries is not None
                         else [_entry("A", dance), _entry("B", dance)])
        self._cache = _Cache()
        self._busy = None
        self._bar = _Bar()
        self.worker = _Worker()

    def statusBar(self):
        return self._bar

    def _librosa_unavailable(self, targets):
        return ""

    def _apply_analysis_results(self, ok):
        pass

    def _sync_loudness_available(self):
        pass

    def _repaint_silence_flags(self, paths):
        pass

    def _apply_vocals_results(self, ok):
        pass

    def _apply_pd_results(self, ok):
        pass


class _AnalyzeCase(unittest.TestCase):
    """Every worker class replaced by the one that fires signals by hand."""

    WORKERS = ("AudioAnalyzer", "LoudnessAnalyzer", "SilenceAnalyzer",
               "VocalShareAnalyzer", "PdHighlightAnalyzer")

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.box = _Box()
        self.patch(man, "QMessageBox", self.box)
        self.patch(man, "QCheckBox", _Check)
        self.patch(man, "find_ffmpeg", lambda: "C:/ffmpeg.exe")
        self.patch(man, "demucs_available", lambda: True)
        self.patch(man, "learn_instrumental_probs", lambda *a: None)
        self.win = _Win()
        self.addCleanup(reap_widget, self.win)
        for name in self.WORKERS:
            self.patch(man, name, lambda *a, **kw: self.win.worker)

    def patch(self, module, name, value):
        real = getattr(module, name)
        setattr(module, name, value)
        self.addCleanup(setattr, module, name, real)

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def use(self, language):
        """The hook only reaches widgets built after it — and only ever
        installs itself once a non-English language is active."""
        i18n.set_active(language)
        i18n.install_text_hook()

    def run_pass(self, language, start):
        """Start one pass and hand back the window it reports through."""
        self.use(language)
        start(self.win)
        self.assertTrue(self.win.worker.started, "the pass never started")
        return self.win


class ProgressLineI18nTest(_AnalyzeCase):
    """The line the status bar shows while a pass runs."""

    def line(self, language, done=3, total=10, errors=0, eta=-1):
        win = self.run_pass(language, _Win._analyze_loudness)
        win.worker.progress.emit(done, total, errors, "a.mp3", eta)
        return win._bar.msg

    def test_english_is_unchanged(self):
        self.assertEqual(self.line("en"), "Lautheits-Analyse: 3/10  "
                         .replace("Lautheits-Analyse", "Loudness analysis"))

    def test_the_noun_speaks_german(self):
        self.assertTrue(self.line("de").startswith("Lautheits-Analyse: 3/10"))

    def test_the_eta_speaks_german(self):
        self.assertIn("übrig", self.line("de", eta=90))

    def test_the_error_count_speaks_german(self):
        self.assertIn("(2 Fehler)", self.line("de", errors=2))


class DoneLineI18nTest(_AnalyzeCase):

    def line(self, language, ok=7, errors=0):
        win = self.run_pass(language, _Win._analyze_loudness)
        win.worker.done.emit(ok, errors)
        return win._bar.msg

    def test_english_is_unchanged(self):
        self.assertEqual(self.line("en"),
                         "Loudness analysis done — 7 tracks measured")

    def test_german(self):
        self.assertEqual(self.line("de"),
                         "Lautheits-Analyse fertig — 7 Titel gemessen")

    def test_the_error_tail_speaks_german(self):
        self.assertIn(", 2 Fehler", self.line("de", errors=2))

    def test_nothing_to_do_speaks_german(self):
        self.assertIn("(alles war schon zwischengespeichert)",
                      self.line("de", ok=0))


class CancelAndErrorI18nTest(_AnalyzeCase):

    def test_cancelling_speaks_german(self):
        win = self.run_pass("de", _Win._analyze_silences)
        win.worker.cancelled.emit(4)
        self.assertEqual(win._bar.msg,
                         "Stille-Prüfung abgebrochen — 4 Titel geprüft bisher.")

    def test_english_cancel_is_unchanged(self):
        win = self.run_pass("en", _Win._analyze_silences)
        win.worker.cancelled.emit(4)
        self.assertEqual(win._bar.msg,
                         "Silence probe cancelled — 4 tracks probed so far.")

    def test_a_failure_speaks_german(self):
        win = self.run_pass("de", _Win._analyze_silences)
        win.worker.error.emit("no decoder")
        self.assertIn("fehlgeschlagen", self.box.last())
        self.assertIn("no decoder", self.box.last())

    def test_the_failure_box_title_is_translated_by_the_static(self):
        """The call site hands `warning` the English noun on purpose: the
        static translates it there. A pre-translated one would be looked up in
        German, find nothing and fall back to itself — still German by luck
        here, but the same move is what left "Caches" English elsewhere."""
        win = self.run_pass("de", _Win._analyze_silences)
        win.worker.error.emit("no decoder")
        self.assertEqual(self.box.last_title(), "Stille-Prüfung")
        self.assertEqual(i18n.t("Stille-Prüfung"), "Stille-Prüfung")


class EveryUnitIsTranslatedTest(_AnalyzeCase):
    """One done-line per pass, so no unit is left behind."""

    PASSES = (
        (_Win._analyze_audio, "Audio-Analyse", "Dateien zwischengespeichert"),
        (_Win._analyze_loudness, "Lautheits-Analyse", "Titel gemessen"),
        (_Win._analyze_silences, "Stille-Prüfung", "Titel geprüft"),
        (_Win._analyze_vocals, "Gesangstrennung", "Titel gemessen"),
        (_Win._analyze_pd_highlights, "PD-Höhepunkt-Erkennung",
         "Titel analysiert"),
    )

    def test_every_pass_reports_in_german(self):
        for start, noun, unit in self.PASSES:
            with self.subTest(noun=noun):
                self.setUp()
                if start is _Win._analyze_pd_highlights:
                    self.win._lib = _Lib([_entry("A", "PD")])
                win = self.run_pass("de", start)
                win.worker.done.emit(5, 0)
                self.assertEqual(win._bar.msg, f"{noun} fertig — 5 {unit}")


class BusyCaptionI18nTest(_AnalyzeCase):
    """The please-wait line over the progress bar."""

    def test_every_caption_speaks_german(self):
        for start in (_Win._analyze_audio, _Win._analyze_loudness,
                      _Win._analyze_silences, _Win._analyze_vocals):
            with self.subTest(start=start.__name__):
                self.setUp()
                win = self.run_pass("de", start)
                caption = win._busy._lbl.text()
                self.assertTrue(caption.endswith("…"))
                for english in ("Analyzing", "Measuring", "Probing",
                                "Separating"):
                    self.assertNotIn(english, caption)


class QuestionBoxI18nTest(_AnalyzeCase):
    """The box each pass opens before it starts."""

    def ask(self, language, start, **kw):
        self.use(language)
        for key, value in kw.items():
            setattr(self.win, key, value)
        start(self.win)
        return self.box.last()

    def test_the_loudness_question_speaks_german(self):
        text = self.ask("de", _Win._analyze_loudness)
        self.assertIn("Die Lautheit der ganzen Bibliothek über 2 Titel messen?",
                      text)
        self.assertIn("Bereits gemessene Titel werden übersprungen", text)

    def test_english_loudness_is_unchanged(self):
        self.assertEqual(self.ask("en", _Win._analyze_loudness), (
            "Measure the loudness of the whole library (2 tracks)?\n\n"
            "Already-measured tracks are skipped — only new ones are\n"
            "decoded (≈1 s each). You can cancel anytime; results so far\n"
            "are kept."))

    def test_the_silence_question_names_both_counts_in_german(self):
        text = self.ask("de", _Win._analyze_silences)
        self.assertIn("2 Titel, 2 noch nicht geprüft", text)

    def test_the_vocals_question_speaks_german(self):
        text = self.ask("de", _Win._analyze_vocals)
        self.assertIn("Den Gesang von 2 noch nicht gemessenen Titeln trennen",
                      text)

    def test_the_audio_question_speaks_german(self):
        text = self.ask("de", _Win._analyze_audio)
        self.assertIn("2 Dateien", text)
        self.assertIn("Jetzt starten?", text)

    def test_an_unloaded_library_says_so_in_german(self):
        self.win._lib = None
        self.assertEqual(self.ask("de", _Win._analyze_loudness),
                         "Die Musikbibliothek ist noch nicht geladen.")

    def test_a_missing_ffmpeg_says_so_in_german(self):
        self.patch(man, "find_ffmpeg", lambda: None)
        self.assertIn("ffmpeg wurde nicht gefunden",
                      self.ask("de", _Win._analyze_loudness))

    def test_a_library_without_paso_doble_says_so_in_german(self):
        self.win._lib = _Lib([_entry("A", "SA")])
        self.assertEqual(self.ask("de", _Win._analyze_pd_highlights),
                         "Keine Paso-Doble-Titel in der Bibliothek.")


if __name__ == "__main__":
    unittest.main()
