"""EN/DE chrome translation, keyed by the English string itself.

The app was written in English, with its visible text sitting as literals at
roughly 500 call sites across gui/ and player/. Two ways to translate that:
rewrite every site to `tr("Save")` and carry a Qt Linguist round-trip, or leave
the sites alone and translate the strings on their way into Qt. This is the
second, for the same reason shared/theme.py rewrites colours in a hook rather than
at 330 call sites — and it buys three properties that matter more here:

* **The key IS the English string.** A missing entry falls back to English on
  its own, so a half-finished catalog is a half-translated app, never a
  crashing one and never a screen of `MISSING_KEY_47`.
* **English is the identity function.** `install_text_hook()` returns before it
  patches anything unless a translated language is active, so the default app
  runs byte-for-byte the code it always did.
* **Dynamic text passes through untouched.** `setText(f"{n} tracks")` is not a
  catalog key, so it misses and is returned as-is. That is also the one hazard
  worth naming: a *data* string that happens to equal a catalog key — a song
  actually titled "Close" — would be translated. The keys are chrome phrases
  and the collision has not been seen, but it is the price of keying by text.

The catalog for a language lives in its own module (`planner/lang_de.py`), so
it is bundled by PyInstaller like any other import and needs no data-file entry
in the spec.

Qt's own chrome — the OK/Cancel on a message box, the file dialog, the colour
picker — is not ours to translate and is not in the catalog. PySide6 ships
`qtbase_de.qm`; `install_qt_translator()` loads it.

Nothing here imports PySide6 at module level: planner/ is the no-Qt core, and
`t()` has to stay callable from anywhere. The Qt imports live inside the two
install functions, which only ever run under a QApplication.
"""
import contextlib
import importlib
import logging

log = logging.getLogger("dancesport.i18n")

DEFAULT_LANGUAGE = "en"

# (code, what the ⚙ Settings combo shows, the tooltip under it)
LANGUAGES = (
    ("en", "🇬🇧  English — the language the app is written in (default)",
     "Every label exactly as the app ships it."),
    ("de", "🇩🇪  Deutsch — Menüs, Knöpfe und Dialoge auf Deutsch",
     "Menus, buttons and dialogs are translated. Track names, dance names and "
     "anything read from your files stay as they are."),
)
_LANGUAGE_CODES = tuple(code for code, _caption, _blurb in LANGUAGES)

_active_language = DEFAULT_LANGUAGE
_catalog = {}
_verbatim = False
# Catalogs of languages other than the active one, loaded on first use.
_other_catalogs = {}


# ── The catalog ──────────────────────────────────────────────────────────────

def _load_catalog(lang: str) -> dict:
    """The translations for a language, or an empty dict for English.

    A missing or broken catalog module is not worth taking the app down for —
    every lookup simply misses and the app stays English."""
    if lang == DEFAULT_LANGUAGE:
        return {}
    try:
        module = importlib.import_module(f"planner.lang_{lang}")
        catalog = dict(module.CATALOG)
    except (ImportError, AttributeError) as exc:
        log.warning("🌐 No catalog for %s, staying English: %s", lang, exc)
        return {}
    log.info("🌐 Language %s\n"
             "entries: %d", lang, len(catalog))
    return catalog


def system_language() -> str:
    """The language this computer is set to, if the app speaks it.

    Qt is imported here rather than at module level, the same way the two
    install functions below do it: planner/ is the no-Qt core, and this is
    only ever reached under a QApplication. Without one — or on a build
    with no Qt at all — the answer is simply English.

    `uiLanguages()` is the list the OS hands out in preference order, so a
    machine set to Swiss German ("de-CH") before English still lands on
    German: the region is dropped and only the language kept."""
    try:
        from PySide6.QtCore import QLocale
        system = QLocale.system()
        tags = list(system.uiLanguages()) or [system.name()]
    except Exception as exc:                    # no Qt, no display, no locale
        log.warning("🌐 Could not read the system language, staying "
                    "English: %s", exc)
        return DEFAULT_LANGUAGE
    for tag in tags:
        code = tag.replace("_", "-").split("-")[0].lower()
        if code in _LANGUAGE_CODES:
            return code
    return DEFAULT_LANGUAGE


def language_of(settings: dict) -> str:
    """The language named in the settings, or the computer's on a first run.

    Two different silences, and they do not mean the same thing. A setting
    that names a language the app does not have — hand-edited, or one that
    was dropped since — is a wrong answer, and English is the safe one. A
    setting that names nothing at all is a first start, where guessing
    English on a German Windows is the one guess certain to be wrong."""
    want = str((settings or {}).get("language") or "").strip().lower()
    if not want:
        return system_language()
    return want if want in _LANGUAGE_CODES else DEFAULT_LANGUAGE


def set_active(lang: str = DEFAULT_LANGUAGE) -> None:
    global _active_language, _catalog
    _active_language = lang if lang in _LANGUAGE_CODES else DEFAULT_LANGUAGE
    _catalog = _load_catalog(_active_language)


def apply_settings(settings: dict) -> None:
    set_active(language_of(settings))


def active_language() -> str:
    return _active_language


def is_translated() -> bool:
    """Whether anything is being rewritten at all."""
    return bool(_catalog)


def translate(text, lang: str):
    """`text` in `lang`, whatever language the rest of the app is in — for the
    one window the hall reads (see planner.terms.hall_language). Misses come
    back unchanged, exactly as with `t`."""
    if lang == _active_language:
        return t(text)
    if not isinstance(text, str):
        return text
    if lang not in _other_catalogs:
        _other_catalogs[lang] = _load_catalog(lang)
    return _other_catalogs[lang].get(text, text)


def t(text):
    """The active language's version of an English chrome string.

    Anything unknown — a track name, an f-string, a number, None — comes back
    exactly as it went in."""
    if _verbatim or not _catalog or not isinstance(text, str):
        return text
    return _catalog.get(text, text)


@contextlib.contextmanager
def verbatim():
    """Inside this block nothing is translated, whatever the catalog says.

    The escape hatch for **data**. Keying by the English string is what makes a
    missing entry harmless, and the price is that a data string which happens
    to equal a key gets translated too. That is not hypothetical: the library
    this was written for holds a track called "Time" and one called "Action",
    and both words are column headers elsewhere in the app. Without this, the
    presenter screen the hall reads the song name off would say "Zeit".

    So the rule is: chrome goes through the hook, data goes through here."""
    global _verbatim
    before = _verbatim
    _verbatim = True
    try:
        yield
    finally:
        _verbatim = before


# ── Wiring it into Qt ────────────────────────────────────────────────────────

# Constructors whose first string argument is the text the user reads. Patched
# per concrete class: `cls.__init__` is a shiboken slot, so a patch on a base
# class is not what a subclass constructor actually calls.
_CTOR_CLASSES = ("QLabel", "QPushButton", "QCheckBox", "QRadioButton",
                 "QGroupBox", "QToolButton", "QMenu", "QCommandLinkButton")

# (class, method, where to start looking, how many strings to translate).
# Positions are a starting point rather than an index, so one entry covers
# `addAction("Stop")` and `addAction(icon, "Stop")` alike — and so `addItem`
# translates the caption without touching a string passed as its data role.
_PATCHED_METHODS = (
    ("QWidget", "setWindowTitle", 0, 1),
    ("QWidget", "setToolTip", 0, 1),
    ("QWidget", "setStatusTip", 0, 1),
    ("QLabel", "setText", 0, 1),
    ("QAbstractButton", "setText", 0, 1),     # every button and check box
    ("QGroupBox", "setTitle", 0, 1),
    ("QLineEdit", "setPlaceholderText", 0, 1),
    ("QMenu", "addAction", 0, 1),
    ("QMenu", "addMenu", 0, 1),
    ("QMenuBar", "addMenu", 0, 1),
    ("QTabWidget", "addTab", 1, 1),           # (widget, text)
    ("QTabWidget", "setTabText", 1, 1),       # (index, text)
    ("QComboBox", "addItem", 0, 1),
    ("QStatusBar", "showMessage", 0, 1),
    ("QProgressDialog", "setLabelText", 0, 1),
    ("QDialogButtonBox", "addButton", 0, 1),  # a button the app names itself
    ("QSpinBox", "setSuffix", 0, 1),          # " tracks", " s", " dB"
    ("QDoubleSpinBox", "setSuffix", 0, 1),
    ("QMessageBox", "setInformativeText", 0, 1),
    ("QMessageBox", "setText", 0, 1),         # a box built by hand
    ("QMessageBox", "setWindowTitle", 0, 1),  # its own override, not QWidget's
    ("QMessageBox", "addButton", 0, 1),       # ("Replace", role); a StandardButton passes
)

# The same idea for a method handed a LIST of strings. `setHorizontalHeaderLabels`
# is the reason this table exists: 42 call sites carry the column headers of
# every table in the app — Dance, Artist, Title, Heat, Takt — and a positional
# (start, count) cannot reach inside a list, so they all stayed English.
#
# `QComboBox.addItems` is the conspicuous absentee. Every call site fills a
# combo the app later reads back BY TEXT (`style_combo.currentText()` is the
# key a dance style is stored under), so translating those captions would
# break the comparison while the screen looked perfectly German. They need
# `addItem(caption, data)` pairs before they can be translated at all — which
# is how the mode combo was moved over; `addItem` above then does the rest.
_PATCHED_LIST_METHODS = (
    ("QTableWidget", "setHorizontalHeaderLabels", 0),
)

# QAction lives in QtGui, not QtWidgets, and carries most of the menu text.
_PATCHED_GUI_METHODS = (
    ("QAction", "setText", 0, 1),
    ("QAction", "setToolTip", 0, 1),
)

# The static message boxes are the single largest block of chrome in the app —
# ~170 calls — and both the window title and the body are literals:
# `QMessageBox.information(parent, title, text)`.
_PATCHED_STATICS = (
    ("QMessageBox", "information", 1, 2),
    ("QMessageBox", "question", 1, 2),
    ("QMessageBox", "warning", 1, 2),
    ("QMessageBox", "critical", 1, 2),
    ("QMessageBox", "about", 1, 2),
    ("QInputDialog", "getText", 1, 2),
    ("QInputDialog", "getItem", 1, 2),
)

_hook_installed = False
_originals = []          # (owner, attribute, what was there before)


def _translated_args(args: tuple, start: int, count: int) -> tuple:
    """Translate up to `count` string arguments at or after position `start`."""
    out = list(args)
    done = 0
    for i in range(start, len(out)):
        if done >= count:
            break
        if isinstance(out[i], str):
            out[i] = t(out[i])
            done += 1
    return tuple(out)


def _translated_list_arg(args: tuple, pos: int) -> tuple:
    """Translate the strings inside the list argument at `pos`.

    Anything that is not a list of strings is handed on untouched — the header
    labels of a table built from data are not catalog keys either."""
    if pos >= len(args) or not isinstance(args[pos], (list, tuple)):
        return args
    out = list(args)
    seq = out[pos]
    out[pos] = type(seq)(t(s) if isinstance(s, str) else s for s in seq)
    return tuple(out)


def _patch_ctor(cls) -> None:
    original = cls.__init__
    _originals.append((cls, "__init__", original))

    def wrapper(self, *args, **kw):
        original(self, *_translated_args(args, 0, 1), **kw)

    cls.__init__ = wrapper


def _patch_method(cls, name: str, start: int, count: int) -> None:
    original = getattr(cls, name)
    _originals.append((cls, name, original))

    def wrapper(self, *args, **kw):
        return original(self, *_translated_args(args, start, count), **kw)

    setattr(cls, name, wrapper)


def _patch_list_method(cls, name: str, pos: int) -> None:
    original = getattr(cls, name)
    _originals.append((cls, name, original))

    def wrapper(self, *args, **kw):
        return original(self, *_translated_list_arg(args, pos), **kw)

    setattr(cls, name, wrapper)


def _patch_static(cls, name: str, start: int, count: int) -> None:
    original = getattr(cls, name)
    _originals.append((cls, name, staticmethod(original)))

    def wrapper(*args, **kw):
        return original(*_translated_args(args, start, count), **kw)

    setattr(cls, name, staticmethod(wrapper))


def _restore_text_hook() -> None:
    """Take every patch back off. **For the test suite only.**

    The app installs the hook once before the first widget and never removes
    it, so nothing in production calls this. The suite is the opposite case:
    2900-odd tests share one process, and a hook left installed would translate
    the chrome that every later test asserts on."""
    global _hook_installed
    for owner, name, original in reversed(_originals):
        setattr(owner, name, original)
    _originals.clear()
    _hook_installed = False


def install_text_hook() -> None:
    """Route the app's chrome through `t()` on its way into Qt.

    A no-op in English, so the default app is untouched — the same promise
    shared/theme.py makes for light mode. Has to run before the first widget is
    built: a label already carrying its English text is not revisited."""
    global _hook_installed
    if _hook_installed or not is_translated():
        return
    from PySide6 import QtGui, QtWidgets

    for name in _CTOR_CLASSES:
        _patch_ctor(getattr(QtWidgets, name))
    _patch_ctor(QtGui.QAction)
    for module, table in ((QtWidgets, _PATCHED_METHODS),
                          (QtGui, _PATCHED_GUI_METHODS)):
        for cls_name, method, start, count in table:
            _patch_method(getattr(module, cls_name), method, start, count)
    for cls_name, method, pos in _PATCHED_LIST_METHODS:
        _patch_list_method(getattr(QtWidgets, cls_name), method, pos)
    for cls_name, method, start, count in _PATCHED_STATICS:
        _patch_static(getattr(QtWidgets, cls_name), method, start, count)

    _hook_installed = True
    log.debug("🌐 Text hook installed (language=%s)", _active_language)


def install_qt_translator(app) -> bool:
    """Translate Qt's OWN chrome: the standard buttons, the file dialog, the
    colour picker. None of that text passes through the app's code, so the
    catalog can never reach it — but PySide6 ships Qt's translations.

    Returns whether one was loaded, which is also "this language has one"."""
    if not is_translated():
        return False
    from PySide6.QtCore import QLibraryInfo, QTranslator

    translator = QTranslator(app)
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if not translator.load(f"qtbase_{_active_language}", path):
        log.debug("🌐 Qt ships no qtbase_%s", _active_language)
        return False
    app.installTranslator(translator)
    # Held on the app, or Python would collect it and Qt would read freed memory.
    app._qt_translator = translator
    return True
