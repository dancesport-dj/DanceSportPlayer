"""🎚 The equalizer as a floating card, opened from the player's 🎚 and from
the 🎧 pre-listen mini player's, like the ♪ Takt meter.

Tabs Music | Voice | Cue, each a shared.audio.eq_panel.EqPanel. Every edit
goes out as `settingsChanged` with the new "equalizer" value; the window
merges it into its settings, has the device apply it (AudioDevice.sync_eq)
and saves. The Cue tab is greyed while the pre-listen plays on the music's
output ("Same as the music"): the music's EQ is what is heard there. All of
it is greyed where the backend can have no EQ (shared.audio.playback.eq_available).
"""
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTabWidget, QToolButton, QVBoxLayout

from planner import i18n
from planner.playing import equalizer as eqs
from player.audio import eq
from player.widgets.floating_card import ACCENT, CARD_QSS, DIM, INK, FloatingCard
from shared.appearance.icons import button as icon_button
from shared.audio.eq_panel import EQ_TABS, EqPanel
from shared.audio.eq_question import confirm_music_eq
from shared.audio.playback import eq_available
from shared.stores import save_settings

# What the ♪ Takt card has no need of: the tabs, the switches, the preset list.
_EQ_QSS = (
    "QTabWidget::pane { background:#2c3752; border:1px solid #55668f;"
    " border-radius:4px; top:-1px; }"
    "QTabBar::tab { color:%(dim)s; background:#333d54; border:1px solid #55668f;"
    " border-bottom:none; border-top-left-radius:4px; border-top-right-radius:4px;"
    " padding:3px 10px; margin-right:2px; }"
    "QTabBar::tab:selected { color:%(ink)s; background:#3d4b6e; }"
    "QTabBar::tab:hover { background:#4f5f88; }"
    "QTabBar::tab:disabled { color:#5d6a8c; }"
    "QCheckBox { color:%(ink)s; background:transparent; }"
    "QCheckBox:disabled, QLabel:disabled { color:#6b7a9c; }"
    "QCheckBox::indicator { width:12px; height:12px; border:1px solid #6a7cab;"
    " border-radius:3px; background:#3d4b6e; }"
    "QCheckBox::indicator:hover { border-color:%(ink)s; }"
    "QCheckBox::indicator:checked { background:%(accent)s; border-color:#6a9de0; }"
    "QCheckBox::indicator:disabled { background:#333d54; border-color:#45526f; }"
    "QComboBox { color:%(ink)s; background:#3d4b6e; border:1px solid #55668f;"
    " border-radius:4px; padding:2px 6px; }"
    "QComboBox:hover { background:#4f5f88; }"
    "QComboBox QAbstractItemView { color:%(ink)s; background:#2c3752;"
    " selection-background-color:%(accent)s; }"
    % {"ink": INK, "dim": DIM, "accent": ACCENT}
)


def headroom_of(cfg: dict) -> float:
    """What `cfg`'s boosts turn the output down by, as if it were on."""
    bands = eqs.audible_bands({**cfg, "on": True, "bypass": False})
    return eq.headroom_db(tuple(eq.Band(*b) for b in bands))


class EqCard(FloatingCard):

    settingsChanged = Signal(dict)   # {"equalizer": …}: merged into the settings

    def __init__(self, settings: Callable[[], dict], cue_on: Callable[[], bool]):
        super().__init__()
        self._settings = settings
        self._cue_on = cue_on
        self.setStyleSheet(CARD_QSS + _EQ_QSS)
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(8, 6, 8, 8)
        top = QHBoxLayout()
        self._title = QLabel(i18n.t("🎚 Equalizer"))
        self._title.setStyleSheet("font-weight:bold; color:#eef3fb;")
        self._title.setCursor(Qt.CursorShape.OpenHandCursor)
        self._title.setToolTip(i18n.t("Drag here to move"))
        top.addWidget(self._title, stretch=1)
        close_btn = QToolButton()
        icon_button(close_btn, "close", 11, INK)
        close_btn.setToolTip(i18n.t("Close"))
        close_btn.clicked.connect(self.closeRequested.emit)
        top.addWidget(close_btn)
        lyt.addLayout(top)
        self._tabs = QTabWidget()
        self.panels: dict[str, EqPanel] = {}
        for source, caption in EQ_TABS:
            panel = EqPanel(
                source, eqs.eq_of(settings() or {}, source), settings=settings,
                headroom=headroom_of,
                # The window, not the card: a child takes the card's dark style.
                confirm_on=(lambda: confirm_music_eq(self._settings(), self.window()))
                if source == "music" else None)
            panel.changed.connect(lambda p=panel: self._on_changed(p))
            panel.presetSaved.connect(self._on_preset_saved)
            self._tabs.addTab(panel, i18n.t(caption))
            # The style fills a tab page with its own light window colour.
            panel.setAutoFillBackground(False)
            self.panels[source] = panel
        lyt.addWidget(self._tabs)
        self._note = QLabel("")
        self._note.setWordWrap(True)
        self._note.setStyleSheet("color:#d8b35c; font-size:11px;")
        lyt.addWidget(self._note)

    def show_for(self, anchor, source: str = "music"):
        """Open beside `anchor` on `source`'s tab, showing the settings as
        they are now (⚙ Settings may have changed them meanwhile)."""
        self.refresh()
        index = [s for s, _c in EQ_TABS].index(source)
        if self._tabs.isTabEnabled(index):
            self._tabs.setCurrentIndex(index)
        self.show_near(anchor)

    def refresh(self):
        settings = self._settings() or {}
        for source, panel in self.panels.items():
            panel.set_cfg(eqs.eq_of(settings, source))
        cue = [s for s, _c in EQ_TABS].index("cue")
        self._tabs.setTabEnabled(cue, self._cue_on())
        self._tabs.setTabToolTip(cue, "" if self._cue_on() else i18n.t(
            "The pre-listen plays on the music's output (\"Same as the music\"):\n"
            "the music's EQ is what is heard there."))
        available = eq_available()
        self._tabs.setEnabled(available)
        self._show_note(available)

    def _show_note(self, available: bool):
        text = "" if available else i18n.t(
            "Only with the FFmpeg engine: ⚙ Settings → 🔊 Sound & player → Audio backend.")
        self._note.setText(text)
        self._note.setVisible(bool(text))

    def _on_changed(self, panel: EqPanel):
        settings = eqs.with_eq(self._settings() or {}, panel.source, panel.cfg())
        self.settingsChanged.emit({"equalizer": settings["equalizer"]})
        if self.isVisible():
            # ⚙ Advanced shows or hides two rows of fields; they count in the
            # size hint only once their show events have run.
            QTimer.singleShot(0, self.refit)

    def _on_preset_saved(self, name: str, gains):
        """💾 / 🗑 an own preset: into the settings, and into every tab's list."""
        settings = eqs.with_user_preset(self._settings() or {}, name, gains)
        self.settingsChanged.emit({"equalizer": settings["equalizer"]})
        for panel in self.panels.values():
            panel.refill_presets()


class EqCardController(QObject):
    """The one card behind both 🎚 buttons, owned here rather than by the
    window (tests/app/test_mainwindow_budget.py). Parented to the window,
    which keeps it alive. An edit goes into the live settings and the device
    at once; the file is written once the edits rest, or when the card closes."""

    def __init__(self, parent, device, settings: Callable[[], dict]):
        super().__init__(parent)
        self._device = device
        self._settings = settings
        self.card: EqCard | None = None
        # A slider drag is many edits: the file is written once it rests.
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(800)
        self.save_timer.timeout.connect(self._save)

    def toggle(self, anchor, source: str = "music"):
        """Open beside `anchor` on `source`'s tab; the same button again closes it."""
        if self.card is None:
            self.card = EqCard(
                settings=self._settings,
                cue_on=lambda: self._device.cue_device() is not None)
            self.card.closeRequested.connect(self.card.hide)
            self.card.closeRequested.connect(self.flush)
            self.card.settingsChanged.connect(self.apply)
        if self.card.isVisible() and self.card.anchor() is anchor:
            self.card.hide()
            self.flush()   # closed as by its ✕: what still waits is written
            return
        self.card.show_for(anchor, source)

    def apply(self, part: dict):
        """Heard at once, saved a moment later."""
        self._settings().update(part)
        self._device.sync_eq()
        self.save_timer.start()

    def flush(self):
        if self.save_timer.isActive():
            self.save_timer.stop()
            self._save()

    def _save(self):
        save_settings(self._settings())
