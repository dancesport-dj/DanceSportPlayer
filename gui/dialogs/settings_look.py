"""🎨 The Settings dialog's Look tab: the theme list, own looks and the accent.

Split off gui/dialogs/settings_dialog.py: building the tab, listing the
built-in and own looks, making, editing, importing, exporting and deleting
an own look, and picking the accent colour.
"""
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from planner import i18n
from shared.appearance import looks, theme, user_looks
from shared.widgets import _hsep
from gui.dialogs import THEME_CHOICES, ThemePreview
from gui.dialogs.look_editor import LookEditor, LookPreview
from shared.appearance.presenter_theme import DEFAULT_KEY, theme_choices

# Typed as the dialog it is mixed into, so `self` passes as a parent widget.
if TYPE_CHECKING:
    _DialogHost = QDialog
else:
    _DialogHost = object


class LookTabMixin(_DialogHost):
    """The 🎨 Look tab of SettingsDialog."""

    # ── 🎨 Look ───────────────────────────────────────────────────────────────
    _OWN_BLURB = ("A look of your own, kept on this computer. ✎ Edit changes it, "
                  "Export passes it on.")
    # What ＋ New copies when Light or Dark is selected: the look nearest to it.
    _NEW_FROM_CLASSIC = {"light": "paper", "dark": "graphite"}

    def _setup_look_tab(self, settings, tabs):
        """🎨 Look: the theme list, its preview and the accent colour."""
        # ═══ Tab 2: Look — theme and accent colour ═══
        look_tab = QWidget()
        llyt = QVBoxLayout(look_tab)
        llyt.setSpacing(10)

        llyt.addWidget(QLabel(
            "<b>🎨 Theme</b> — the classic light or dark, or one of the looks:"))
        pick_row = self._make_theme_picker()
        llyt.addLayout(pick_row, stretch=1)

        llyt.addWidget(_hsep())

        llyt.addWidget(QLabel(
            "<b>🎚 Accent colour</b> — the blue the buttons, sliders and the "
            "▶ player panel are built around:"))
        self._accent = theme.accent_of(settings)
        accent_row = QHBoxLayout()
        self._accent_btn = QPushButton("  Pick a colour…")
        self._accent_btn.setToolTip(
            "Only the accent's own family of tints follows this colour.\n"
            "A red warning, a green proven mark and the popularity amber mean\n"
            "something, so they keep their hue.")
        self._accent_btn.clicked.connect(self._pick_accent)
        accent_row.addWidget(self._accent_btn, stretch=1)
        self._accent_reset = QPushButton("↺  Default blue")
        self._accent_reset.clicked.connect(
            lambda: self._set_accent(theme.ACCENT_DEFAULT))
        accent_row.addWidget(self._accent_reset)
        llyt.addLayout(accent_row)
        self._accent_note = QLabel(
            "A look brings its own accent colour — this one is for Light and Dark.")
        self._accent_note.setStyleSheet("color:#666; font-size:11px;")
        llyt.addWidget(self._accent_note)
        self._set_accent(self._accent)
        self._theme_list.currentItemChanged.connect(self._on_theme_picked)
        self._select_theme(theme.theme_of(settings))

        llyt.addWidget(_hsep())

        llyt.addWidget(QLabel(
            "<b>🌐 Language</b> — menus, buttons and dialogs:"))
        self._language_combo = QComboBox()
        for code, caption, blurb in i18n.LANGUAGES:
            self._language_combo.addItem(caption, code)
            # The caption reaches German through the patched addItem; the
            # blurb rides setItemData, which stays unpatched on purpose, so
            # it asks for itself.
            self._language_combo.setItemData(
                self._language_combo.count() - 1, i18n.t(blurb),
                Qt.ItemDataRole.ToolTipRole)
        self._language_combo.setCurrentIndex(
            max(0, self._language_combo.findData(i18n.language_of(settings))))
        llyt.addWidget(self._language_combo)

        self._german_terms_chk = QCheckBox(
            "Keep the German dance and round names on a screen in another language "
            "(Langsamer Walzer, Vorrunde, Standardrunde 1, Eintanzen …)")
        self._german_terms_chk.setToolTip(
            "On: the presenter screen and the recorded announcements are "
            "German too, and a 🤸 practice list is called Eintanzen, also "
            "in its saved file.\n"
            "Off: Slow Waltz, Round 1, Standard round 1, Practice … — the "
            "playlists and exports keep the German dance and round names "
            "either way.")
        self._german_terms_chk.setChecked(bool(settings.get("german_dance_terms")))
        llyt.addWidget(self._german_terms_chk)

        look_note = QLabel(
            "Theme, accent and language are read when the app starts, so a "
            "change takes effect after a restart — you are asked once you save.")
        look_note.setWordWrap(True)
        look_note.setStyleSheet("color:#666; font-size:11px;")
        llyt.addWidget(look_note)

        llyt.addWidget(_hsep())
        self._clock_time_only_chk = QCheckBox(
            "⛶  Fullscreen clock: only the time (20:45:12), no date")
        self._clock_time_only_chk.setChecked(
            bool(settings.get("clock_time_only", False)))
        llyt.addWidget(self._clock_time_only_chk)

        # 🖥 …and the palette the presenter screen wears: a hall wants the
        # black screen, a wedding the creme one — set once per venue.
        llyt.addWidget(_hsep())
        llyt.addWidget(QLabel(
            "<b>🖥 Presenter screen</b> — the colours it wears:"))
        self._presenter_theme_combo = QComboBox()
        self._presenter_theme_combo.setToolTip(
            "The colours of the presenter screen. 'Default' is the black hall\n"
            "display; 'Light' is creme paper with warm brown type and rose\n"
            "gold for the next dance — made for a lit room, where black on a\n"
            "beamer is just a grey rectangle. Applies straight away.")
        for key, label in theme_choices():
            self._presenter_theme_combo.addItem(label, key)
        want = str(settings.get("presenter_theme", DEFAULT_KEY))
        self._presenter_theme_combo.setCurrentIndex(
            max(0, self._presenter_theme_combo.findData(want)))
        llyt.addWidget(self._presenter_theme_combo)

        tabs.addTab(look_tab, "🎨 Look")

    def _make_theme_picker(self):
        """The theme list with its own-look buttons, beside the previews."""
        pick_row = QHBoxLayout()
        # One list with section headers rather than a combo: the classic pair
        # stands apart from the looks, and every entry is visible at once.
        # QListWidgetItem is not among the hooked setters, so each caption asks
        # for its translation itself.
        self._theme_list = QListWidget()
        self._theme_list.setMinimumWidth(230)
        self._theme_blurbs: dict[str, str] = {}
        # Keys of looks of your own made, changed or deleted while this is
        # open: when the running look is among them, saving offers a restart.
        self._looks_touched: set[str] = set()
        self._fill_theme_list()
        list_col = QVBoxLayout()
        list_col.addWidget(self._theme_list, stretch=1)
        own_row = QGridLayout()
        self._look_new = QPushButton("＋  New look…")
        self._look_new.setToolTip(
            "A look of your own, starting as a copy of the selected one.")
        self._look_new.clicked.connect(self._new_look)
        self._look_edit = QPushButton("✎  Edit…")
        self._look_edit.clicked.connect(self._edit_look)
        self._look_delete = QPushButton("🗑  Delete")
        self._look_delete.clicked.connect(self._delete_look)
        self._look_import = QPushButton("Import…")
        self._look_import.setToolTip("Add a look someone exported.")
        self._look_import.clicked.connect(self._import_look)
        self._look_export = QPushButton("Export…")
        self._look_export.setToolTip("Save the selected look of your own as a "
                                     "file, to pass it on.")
        self._look_export.clicked.connect(self._export_look)
        own_row.addWidget(self._look_new, 0, 0, 1, 2)
        own_row.addWidget(self._look_edit, 1, 0)
        own_row.addWidget(self._look_delete, 1, 1)
        own_row.addWidget(self._look_import, 2, 0)
        own_row.addWidget(self._look_export, 2, 1)
        list_col.addLayout(own_row)
        pick_row.addLayout(list_col)
        preview_col = QVBoxLayout()
        self._theme_preview = ThemePreview()
        preview_col.addWidget(self._theme_preview)
        # A look of your own has no picture of the main window: these controls,
        # dressed in it, stand in.
        self._look_preview = LookPreview()
        self._look_preview.hide()
        preview_col.addWidget(self._look_preview)
        self._theme_blurb = QLabel()
        self._theme_blurb.setWordWrap(True)
        preview_col.addWidget(self._theme_blurb)
        preview_col.addStretch()
        pick_row.addLayout(preview_col, stretch=1)
        return pick_row

    def _fill_theme_list(self) -> None:
        """The sections: the classic pair, the built-in groups, your own looks.
        Own captions are names you gave, so they are shown as they are."""
        self._theme_list.blockSignals(True)
        self._theme_list.clear()
        self._theme_blurbs.clear()
        sections = [("Standard", [(k, i18n.t(c), i18n.t(b))
                                  for k, c, b in THEME_CHOICES])]
        for group, label in looks.GROUPS:
            sections.append((label, [(look.key, i18n.t(look.caption), i18n.t(look.blurb))
                                     for look in looks.LOOKS.values()
                                     if look.group == group]))
        sections.append(("Own looks", [(look.key, look.caption, i18n.t(self._OWN_BLURB))
                                       for look in user_looks.mine()]))
        for label, entries in sections:
            head = QListWidgetItem(i18n.t(label))
            head.setFlags(Qt.ItemFlag.NoItemFlags)
            font = head.font()
            font.setBold(True)
            head.setFont(font)
            self._theme_list.addItem(head)
            for key, caption, blurb in entries:
                item = QListWidgetItem("   " + caption)
                item.setData(Qt.ItemDataRole.UserRole, key)
                self._theme_list.addItem(item)
                self._theme_blurbs[key] = blurb
        if not user_looks.mine():
            empty = QListWidgetItem("   " + i18n.t("none yet — ＋ New look…"))
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._theme_list.addItem(empty)
        self._theme_list.blockSignals(False)

    def _selected_own(self) -> "looks.Look | None":
        look = looks.get(self.selected_theme())
        return look if look is not None and look.group == user_looks.GROUP else None

    def running_look_touched(self) -> bool:
        """Whether the look the app runs in was changed or deleted here — saved
        at once, so the app has to restart to show it even with the same pick."""
        return theme.active_theme() in self._looks_touched

    def _relist(self, select: str) -> None:
        self._fill_theme_list()
        self._select_theme(select)
        self._on_theme_picked()

    def _new_look(self) -> None:
        key = self.selected_theme()
        source = looks.get(self._NEW_FROM_CLASSIC.get(key, key))
        if source is None:
            return
        own = source.group == user_looks.GROUP
        name = i18n.t("%s (own)") % (source.caption if own else i18n.t(source.caption))
        self._edit(user_looks.copy_of(source, name))

    def _edit_look(self) -> None:
        look = self._selected_own()
        if look is not None:
            self._edit(look)

    def _edit(self, look: looks.Look) -> None:
        editor = LookEditor(look, self)
        if editor.exec() != QDialog.DialogCode.Accepted:
            return
        look = editor.look()
        if not user_looks.put(look):
            QMessageBox.warning(self, "Look not saved",
                                "The looks file could not be written. "
                                "The log names the reason.")
        self._looks_touched.add(look.key)
        self._relist(look.key)

    def _delete_look(self) -> None:
        look = self._selected_own()
        if look is None:
            return
        answer = QMessageBox.question(
            self, "Delete look",
            i18n.t("Delete the look “%s”? This cannot be undone; "
                   "an exported file of it stays.") % look.caption)
        if answer != QMessageBox.StandardButton.Yes:
            return
        user_looks.remove(look.key)
        self._looks_touched.add(look.key)
        self._relist("light")

    def _import_look(self) -> None:
        # QFileDialog is not one of the patched statics: its texts ask here.
        path, _filter = QFileDialog.getOpenFileName(
            self, i18n.t("Import a look"), "", i18n.t("Looks (*.json)"))
        if not path:
            return
        try:
            look = user_looks.import_file(Path(path))
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Look not imported",
                                i18n.t("This file holds no look the app can use:\n%s")
                                % exc)
            return
        self._relist(look.key)

    def _export_look(self) -> None:
        look = self._selected_own()
        if look is None:
            return
        name = (user_looks.slug(look.caption) or "look") + ".json"
        path, _filter = QFileDialog.getSaveFileName(
            self, i18n.t("Export the look"), name, i18n.t("Looks (*.json)"))
        if not path:
            return
        try:
            user_looks.export(look, Path(path))
        except OSError as exc:
            QMessageBox.warning(self, "Look not exported",
                                i18n.t("The file could not be written:\n%s") % exc)

    def presenter_theme(self) -> str:
        """The key of the palette picked for the presenter screen."""
        return str(self._presenter_theme_combo.currentData() or DEFAULT_KEY)

    def selected_theme(self) -> str:
        item = self._theme_list.currentItem()
        key = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return key or "light"

    def _select_theme(self, key: str) -> None:
        for row in range(self._theme_list.count()):
            item = self._theme_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                self._theme_list.setCurrentItem(item)
                return

    def _on_theme_picked(self, _item=None, _previous=None):
        key = self.selected_theme()
        mine = self._selected_own()
        if mine is None:
            self._theme_preview.show_theme(key)
        else:
            self._look_preview.set_look(mine)
        self._theme_preview.setVisible(mine is None)
        self._look_preview.setVisible(mine is not None)
        for button in (self._look_edit, self._look_delete, self._look_export):
            button.setEnabled(mine is not None)
        self._theme_blurb.setText(self._theme_blurbs.get(key, ""))
        # A look's accent is part of its design; the picker is for the classic pair.
        own = looks.get(key) is None
        self._accent_btn.setEnabled(own)
        self._accent_reset.setEnabled(own)
        self._accent_note.setVisible(not own)
        # The swatch is painted in the picked colour on purpose, so it shows no
        # disabled state of its own; fade it instead.
        fade = None if own else QGraphicsOpacityEffect(self._accent_btn)
        if fade is not None:
            fade.setOpacity(0.35)
        # None drops the effect; the stubs only take an effect.
        self._accent_btn.setGraphicsEffect(cast(QGraphicsEffect, fade))

    def _pick_accent(self):
        # Not one of the patched statics — only QMessageBox and QInputDialog
        # are — so the picker's own title is translated here.
        chosen = QColorDialog.getColor(
            QColor(self._accent), self, i18n.t("Accent colour"))
        if chosen.isValid():
            self._set_accent(chosen.name())

    def _set_accent(self, color: str):
        """Remember the accent and paint the button in it.

        The swatch is the only preview there is — the app itself only picks the
        accent up on the next start — so the button has to show the colour
        honestly, with text that stays readable on whatever was picked."""
        self._accent = theme.rgb_to_hex(theme.hex_to_rgb(color))
        on_dark = theme.contrast_ratio(self._accent, "#ffffff") >= 3.0
        ink = "#ffffff" if on_dark else "#141414"
        # Not via the themed setStyleSheet hook: this swatch must be exactly the
        # colour that was picked, not that colour shaded for the active theme.
        theme.set_stylesheet_unthemed(
            self._accent_btn,
            f"background:{self._accent}; color:{ink};"
            f" border:1px solid #888; padding:6px; font-weight:bold;")
        self._accent_btn.setText(i18n.t("  %s  —  pick a colour…") % self._accent)
