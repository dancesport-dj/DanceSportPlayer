"""The Playing-mode panel shown in place of the ConfigPanel during a tournament.

Extracted from dancesport_gui.py (view split). Its control groups are built in
player/widgets/play_mode_setup.py, its small widgets (the switch, the rows,
the flow layout) are in player/widgets/panel_parts.py.
"""
import logging

from planner.playing.play_sets import (
    _LEN_MAX,
    _LEN_STEP,
    _LEN_TYPED_MAX,
    _LEN_TYPED_MIN,
    parse_play_length,
)

from PySide6.QtCore import (
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path
from shared.widgets import (
    _hsep,
)
from player.presenter.presenter import (  # auto-resolved
    screen_choices,
)
from planner import i18n
from planner.playlist.playlist_text import PlaylistEncodingError, read_playlist_text
from player.widgets.panel_parts import _FlowLayout, _InlineEdit, _Rows, _Toggle
from player.widgets.play_mode_setup import PlayModeSetupMixin

log = logging.getLogger("dancesport.gui.play_mode")

# The wide strip's skin — the BigPlayerWidget's own dark chrome, so the panel
# riding in it reads as part of the same machine instead of a light board
# screwed to its side. Kept here rather than imported: the player card sets it
# on itself with an #BigPlayer id rule, and a panel is not that widget.
_STRIP_QSS = (
    # The panel itself must not paint: a widget with a style sheet fills its
    # background from the palette, and the palette here is the window's light
    # grey — which is exactly the pale board this skin exists to get rid of.
    "#PlayModePanel { background:transparent; }"
    "QLabel { color:#dfe8f6; background:transparent; }"
    "QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {"
    " background:#2a3346; color:#e6edf8; border:1px solid #3a4a68;"
    " border-radius:4px; padding:1px 3px; }"
    # Off is grey, not a dimmer navy: next to the live boxes a #232a39
    # did not read as switched off at all.
    "QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {"
    " color:#8d9097; background:#4b4e55; border-color:#5a5d64; }"
    "QComboBox QAbstractItemView { background:#232a39; color:#e6edf8;"
    " selection-background-color:#1565c0; }"
    "QPushButton { background:#2a3346; color:#cfe0f5; border:1px solid #3a4a68;"
    " border-radius:5px; padding:2px 8px; }"
    "QPushButton:hover { background:#3a4a68; }"
    "QPushButton:pressed { background:#1565c0; }"
    "QToolButton { color:#cfe0f5; background:#2a3346; border:none;"
    " border-radius:4px; padding:2px 5px; }"
    "QToolButton:hover { background:#3a4a68; }")


class PlayModePanel(PlayModeSetupMixin, QWidget):
    """Tournament-floor controls: timed play length with auto fade-out.

    Shown instead of the ConfigPanel when the user flips the left-side mode
    switch to ▶ Playing. Everything is built for quick on-the-fly adjustment:
    a big readable length display, a coarse slider plus −5/+5 s nudge buttons,
    and a live countdown of the song currently playing."""

    settingsChanged = Signal()           # any control changed → MainWindow persists
    danceLenChanged = Signal(str, int)   # −/+ on a dance's own 🏆 length: dance, secs
    pdLearnRequested = Signal()          # 🎯 button → mark current playhead as a highlight
    pdClearRequested = Signal()          # ✖ button → forget current track's highlights
    pdEditToggled = Signal(bool)         # ✏️ Edit highlights on/off (suspends the stop)
    pdMarkDeleteRequested = Signal(float)   # ✕ on a mark chip → drop that mark
    presenterToggled = Signal(bool)      # 🖥 Presenter screen on/off
    presenterScreenChanged = Signal(int)   # another monitor picked for it
    timetableRequested = Signal()          # 🕒 edit the evening's running order
    remoteRequested = Signal()           # 📱 the phone remote's window
    partySetToggled = Signal(bool)       # 🎉 party play set on/off
    tournamentSetRequested = Signal()    # 🏆 back to the competition values
    rememberToggled = Signal(bool)       # ↩ remembering where a title stopped on/off
    settingsRequested = Signal()         # ⚙ — only shown in a player-only install

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setMaximumWidth(640)
        self.setObjectName("PlayModePanel")   # see _STRIP_QSS
        # What the panel stood on before 🎉/🏆 was pressed, on a desk with no
        # lists — the way back when the lit set is clicked off (`_leave_set`).
        self._before_set: dict | None = None
        lyt = self._lyt = QVBoxLayout(self)
        lyt.setContentsMargins(8, 8, 8, 8)
        lyt.setSpacing(6)

        self._title_row = QLabel("▶  Playing mode")
        self._title_row.setStyleSheet("font-weight:bold; font-size:14px;")
        lyt.addWidget(self._title_row)
        lyt.addWidget(_hsep())
        self._setup_length_row(lyt, settings)
        self._setup_paso_doble(lyt, settings)
        self._setup_auto_advance(lyt, settings)
        self._setup_announce(lyt, settings)
        self._setup_play_options(lyt, settings)
        self._setup_play_set_buttons(lyt)
        self._setup_presenter(lyt, settings)
        self._setup_awake_and_countdown(lyt, settings)
        self._setup_gear(lyt)
        self._connect_signals(settings)
        self._setup_sections()

    def _setup_sections(self):
        """Cut the panel into sections the wide strip can lay out."""
        # Everything above went straight into the panel's own layout, one
        # group under the next, because down a side panel that is the only
        # shape there is. Cut at the rules, those groups become blocks that
        # can just as well be dealt out side by side — which is what the wide
        # player strip does with them: it has width to spare and no height.
        self._sections = self._harvest_sections()
        self._wide = False
        self._parked = set()    # rows this shape has no place for
        self._body = QWidget()
        self._lyt.addWidget(self._body)
        self._relayout()

    def _harvest_sections(self):
        """Take the panel apart at its ─── rules.

        Each run of controls between two of them is one group the eye already
        reads as a unit; kept whole, a group can be stacked or laid on its
        side without anything drifting away from its own label. What comes
        back is the rows themselves, not a box around them — the box belongs
        to a shape, and the panel has two: (rule above it, its rows, does it
        soak up spare height)."""
        lyt = self._lyt
        sections = []
        sep = None
        rows = []
        grow = False

        def _close():
            if rows:
                sections.append((sep, list(rows), grow))

        while lyt.count():
            item = lyt.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if isinstance(w, QFrame) and w.frameShape() == QFrame.Shape.HLine:
                _close()
                sep = w
                rows, grow = [], False
            elif w is not None:
                # Parked on the panel while it has no body: a widget with no
                # parent at all is a window of its own on the desktop.
                w.setParent(self)
                rows.append(w)
            elif item.spacerItem() is not None:   # the stretch pinning ⚙ down
                grow = True
        _close()
        return sections

    def set_wide(self, on: bool):
        """Lay the panel out in columns instead of down one — how it stands
        when it rides in the wide player strip above the decks."""
        on = bool(on)
        if on != self._wide:
            self._wide = on
            self._relayout()

    def is_wide(self) -> bool:
        return self._wide

    def sizeHint(self) -> QSize:
        """Across the strip, how deep the panel is IS a question about width.

        The rows wrap, so every width has its own depth. Qt's hint is a single
        number — the depth at the panel's own preferred width — and the strip
        is hardly ever exactly that wide: short of it the bottom line of
        switches is cut off, past it the panel steals a row of playlists. A
        Mac gets the short end at every width, its fallback for a missing
        Consolas being wider than the font the number was measured with.

        Down the side nothing wraps, so there the plain hint is the answer.
        """
        hint = super().sizeHint()
        if not self._wide:
            return hint
        return QSize(hint.width(), self.heightForWidth(self.width()
                                                       or hint.width()))

    def _relayout(self):
        """Re-deal the rows into a fresh body. They are re-parented by being
        added, so nothing is rebuilt — only the shape they stand in."""
        # The sub-groups lie down with the panel: a Paso Doble block four rows
        # deep would set the height of the whole strip on its own.
        for group in self.findChildren(_Rows):
            group.set_wide(self._wide)
        # Built with its parent from the start: a parentless widget shown is a
        # window of its own on the desktop.
        body = QWidget(self)
        dealt = set()
        if self._wide:
            lyt = _FlowLayout(body)
            lyt.setContentsMargins(0, 0, 0, 0)
            # Row by row, not group by group. Kept whole, a group is one word
            # in the paragraph — but the widest of them is half the strip on
            # its own, so every line broke early and the panel came out a rung
            # deeper than the width called for. Loose rows pack tight; they
            # keep their reading order, so a group still reads as a group
            # wherever the line doesn't break through it.
            for sep, rows, _grow in self._sections:
                for w in rows:
                    if w in self._strip_drops():
                        continue
                    lyt.addWidget(w)
                    dealt.add(w)
                if sep is not None:
                    sep.setParent(self)     # rules divide columns, not lines
                    sep.hide()
        else:
            lyt = QVBoxLayout(body)
            lyt.setContentsMargins(0, 0, 0, 0)
            lyt.setSpacing(6)
            for sep, rows, grow in self._sections:
                if sep is not None:
                    # Into the layout first, shown second: a widget shown
                    # while it still hangs off the panel flashes where it used
                    # to be before the body takes it.
                    lyt.addWidget(sep)
                    sep.setVisible(True)
                for w in rows:
                    lyt.addWidget(w)
                    dealt.add(w)
                if grow:
                    lyt.addStretch(1)
        # Whatever this shape has no place for keeps the panel as its parent:
        # left in the old body it would be destroyed with it, and there would
        # be nothing to deal back on the way over.
        for w in self._all_rows():
            if w not in dealt:
                w.setParent(self)
                w.hide()
                self._parked.add(w)
            elif w in self._parked:
                w.show()
                self._parked.discard(w)
        # Down the side it is one column and wants its 250; across the strip
        # it takes the width it is given and answers with a height.
        self.setMinimumWidth(0 if self._wide else 250)
        self.setMaximumWidth(16777215 if self._wide else 640)
        pol = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred if self._wide
            else QSizePolicy.Policy.Expanding)
        # A layout reads the wrapping off the panel's own layout, but whoever
        # sizes it by the POLICY — a splitter, a scroll area — has to be told,
        # or it takes the hint's one number for the depth at every width.
        pol.setHeightForWidth(self._wide)
        self.setSizePolicy(pol)
        self._lyt.setContentsMargins(*((10, 6, 10, 6) if self._wide
                                       else (8, 8, 8, 8)))
        old, self._body = self._body, body
        self._lyt.replaceWidget(old, body)
        # A widget built parentless starts out hidden, and a panel that is
        # already on screen has no show() left to come and reveal it.
        body.show()
        old.setParent(None)
        old.deleteLater()
        self._apply_skin()

    def _apply_skin(self):
        """Down the side the panel is a panel — the window's own light grey.
        In the strip it is part of the player: a pale board bolted to the side
        of a black deck reads as two devices, and the operator's eye has to
        cross the seam every time. Dark, the strip is one machine.

        Only what a stylesheet cannot reach is set by hand: the readouts and
        the labels carry their own colours from the build."""
        self.setStyleSheet(_STRIP_QSS if self._wide else "")
        ink = "#7fb2f0" if self._wide else "#1565c0"
        self.len_lbl.setStyleSheet(
            "QLabel#playLen{font-size:34px; font-weight:bold;"
            f"font-family:Consolas,monospace; color:{ink};}}")
        self.pause_music_lbl.setStyleSheet(
            f"color:{'#9fb0c8' if self._wide else '#555'}; font-style:italic;")
        for pill in self.findChildren(_Toggle):
            pill.set_ink(QColor("#dfe8f6") if self._wide else None)

    def _all_rows(self):
        return [w for _sep, rows, _grow in self._sections for w in rows]

    def _strip_drops(self) -> set:
        """What the strip does not repeat.

        The heading names a mode the strip itself is announcing, and the
        countdown is the player's own clock a hand's width to the left —
        twice the same second, in two different fonts."""
        return {self._title_row, self.countdown_lbl}


    def set_announce_style(self, voice: str, heat: bool, wait: bool):
        """🎙 The voice, the heat number and the lead as ⚙ Settings saved them."""
        self._announce_voice = voice
        self._announce_heat = bool(heat)
        self._announce_wait = bool(wait)
        self._refresh_announce_style()

    def _refresh_announce_style(self):
        """The line under 🔈 that names the voice: 'Mixed voices · with heat
        · over the music'. The lead is left out while titles cross over —
        the crossfade names the dance after the crossover, whatever it says."""
        text = {"female": i18n.t("Female voice"),
                "male": i18n.t("Male voice")}.get(self._announce_voice,
                                                  i18n.t("Mixed voices"))
        if self._announce_heat:
            text += " · " + i18n.t("with heat")
        if not self._crossfade_runs():
            text += " · " + i18n.t("before the music" if self._announce_wait
                                   else "over the music")
        self.announce_style_lbl.setText(text)

    def set_settings_visible(self, on: bool):
        """Show the ⚙ gear — only a player-only install needs its own."""
        self._gear_box.setVisible(on)

    def set_player_widget(self, w: QWidget):
        """Dock the big master player on top of the panel (UltraMixer-style)."""
        self._lyt.insertWidget(0, w)

    def _pick_pause_music(self):
        start = (str(Path(self._pause_music[0]).parent)
                 if self._pause_music else "")
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose pause music", start,
            "Audio / playlist (*.mp3 *.wav *.flac *.m4a *.ogg *.m3u *.m3u8);;"
            "All files (*)")
        if not paths:
            return
        files: list[str] = []
        for p in paths:
            if p.lower().endswith((".m3u", ".m3u8")):
                files.extend(self._read_m3u(p))
            else:
                files.append(p)
        if files:
            self._set_pause_music(files)

    @staticmethod
    def _read_m3u(path: str) -> list[str]:
        """Every non-comment line of the playlist is a file path; relative
        ones resolve against the playlist's own folder."""
        try:
            lines = read_playlist_text(path)[0].splitlines()
        except (OSError, PlaylistEncodingError) as exc:
            log.warning("🎵 Could not read pause playlist\n"
                        "file: %s\n"
                        "error: %s", path, exc)
            return []
        base = Path(path).parent
        out: list[str] = []
        for ln in lines:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            p = Path(ln)
            if not p.is_absolute():
                p = base / p
            out.append(str(p))
        return out

    def _set_pause_music(self, paths: list[str]):
        self._pause_music = list(paths)
        self._refresh_pause_music_lbl()
        self.settingsChanged.emit()

    def _refresh_pause_music_lbl(self):
        if self._pause_music:
            fm = self.pause_music_lbl.fontMetrics()
            first = Path(self._pause_music[0]).stem
            n = len(self._pause_music)
            text = first if n == 1 else f"{n} titles · {first}…"
            self.pause_music_lbl.setText(
                fm.elidedText(text, Qt.TextElideMode.ElideRight, 160))
            self.pause_music_lbl.setToolTip(
                "\n".join(Path(p).stem for p in self._pause_music))
        else:
            self.pause_music_lbl.setText("none")
            self.pause_music_lbl.setToolTip("")

    @staticmethod
    def _load_secs(settings: dict) -> int:
        """The stored play length, kept exactly as it was left.

        It used to snap to the nearest ladder rung — a migration for the
        pre-ladder free slider. It cannot any more: a length typed into the
        readout is deliberately off the ladder, and snapping would quietly
        turn 1:37 back into 1:30 on the next start. An unticked pre-ladder
        on/off box is still the modern 'full'."""
        if not settings.get("timed_enabled", True):
            return 0
        secs = int(settings.get("play_secs", 105))
        if secs <= 0:
            return 0
        return max(_LEN_TYPED_MIN, min(_LEN_TYPED_MAX, secs))

    def _step_len(self, direction: int):
        """One rung up or down. Up from 2:30 lands on 'full'; down from 'full'
        comes back to 2:30. Both ends stop there instead of wrapping around —
        a mis-tap must never jump from full length to 15 s."""
        secs = self._shown_secs()
        if direction > 0:
            secs = 0 if secs == 0 or secs >= _LEN_MAX else secs + _LEN_STEP
        elif secs == 0:
            secs = _LEN_MAX
        else:
            secs = max(_LEN_STEP, secs - _LEN_STEP)
        self._set_len(secs)

    def _shown_secs(self) -> int:
        """The length the readout shows: a dance's own, or the list's."""
        return self._dance_len[2] if self._dance_len is not None else self._secs

    def _set_len(self, secs: int):
        """A new length from −/+ or typing. While a dance's own length is shown
        it is that one that moves — the 🏆 set's, kept in ⚙ Settings — and the
        list's own length stays where it was."""
        if self._dance_len is not None:
            code, name, _old = self._dance_len
            self._dance_len = (code, name, secs)
            self._refresh_len_lbl()
            self.danceLenChanged.emit(code, secs)
            return
        self._secs = secs
        self._refresh_len_lbl()
        self.settingsChanged.emit()

    def set_dance_len(self, code: str, name: str, secs: int | None):
        """Show the 🏆 set's own length of dance `code` (named `name`), or —
        with no `secs` — the list's one length again."""
        self._dance_len = (code, name, int(secs)) if code and secs is not None else None
        self._refresh_len_lbl()

    def _on_len_typed(self, _event=None):
        """Double-click on the readout: type the length into the big blue
        digits themselves, rather than into a box on top of them.

        In place because the desk is already looking at that number, and a
        modal dialog over the panel mid-heat is one thing too many to dismiss.
        The editor is made once and then reused."""
        if self._len_edit is None:
            self._len_edit = _InlineEdit(self.len_lbl)
            self._len_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # The label's own type, so the digits do not jump on the switch.
            # Transparent, so the panel background shows through whatever the
            # theme has made it; the border is what says "this is editable".
            # Styled by its name only, like the readout: the tooltip takes the
            # editor's style sheet too and would come up in 34 px bold.
            self._len_edit.setObjectName("playLenEdit")
            self._len_edit.setStyleSheet(
                "QLineEdit#playLenEdit{font-size:34px; font-weight:bold; color:#1565c0;"
                "font-family:Consolas,monospace; background:transparent;"
                "border:2px solid #1565c0; border-radius:6px;}")
            self._len_edit.setToolTip("m:ss, seconds, or 'full' — "
                                      "Enter to keep, Esc to abandon")
            self._len_edit.editingFinished.connect(self._commit_len_typed)
            self._len_edit.escaped.connect(self._close_len_edit)
        self._len_edit.setGeometry(self.len_lbl.rect())
        self._len_edit.setText(self.len_lbl.text())
        # The editor is transparent so the panel's own background shows through
        # it — which means the label's digits would show through too, printed
        # underneath the ones being typed. Blank it for as long as it is open.
        self.len_lbl.setText("")
        self._len_edit.show()
        self._len_edit.selectAll()
        self._len_edit.setFocus()

    def _close_len_edit(self):
        """Put the editor away and the readout back. Also the Esc path."""
        if self._len_edit is not None:
            self._len_edit.hide()
        self._refresh_len_lbl()

    def _commit_len_typed(self):
        """Enter, or the focus moving on to something else.

        Unparseable input is refused rather than guessed at, so an abandoned
        half-typed '1:' leaves the length exactly as it was."""
        # isHidden, not isVisible: the question is whether the editor is open,
        # and isVisible would also answer "no" for a panel that is merely on a
        # tab nobody is looking at.
        edit = self._len_edit
        if edit is None or edit.isHidden():
            return          # editingFinished comes again on the focus-out
        text = edit.text()
        self._close_len_edit()
        secs = parse_play_length(text)
        if secs is None:
            log.info("⏱️ Play length not understood\n"
                     "typed: %s\n"
                     "keeping: %s s", text, self._secs)
            return
        if secs == self._shown_secs():
            return
        self._set_len(secs)

    def _on_pd_on(self, on: bool):
        """Fold the Paso Doble's fine print away with its switch.

        Edit mode goes with it: left running behind a hidden button it would
        keep the highlight stop suspended with nothing on screen saying so."""
        if not on and self.pd_edit_btn.isChecked():
            self.pd_edit_btn.setChecked(False)
        self.pd_sub_box.setVisible(on)

    def _on_pd_edit(self, on: bool):
        self.pd_edit_btn.setText("✔  Done editing" if on else "✏️  Edit highlights")
        self.pd_marks_box.setVisible(on)
        self.pdEditToggled.emit(on)

    def pd_editing(self) -> bool:
        return self.pd_edit_btn.isChecked()

    def set_pd_edit(self, on: bool):
        """Leave edit mode from the outside (a new title cancels it, so its
        highlight stop isn't left suspended)."""
        self.pd_edit_btn.setChecked(on)

    def set_pd_marks(self, marks: list[float]):
        """Rebuild the deletable mark chips. Only visible while editing."""
        while self.pd_marks_lyt.count():
            item = self.pd_marks_lyt.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
        for t in marks:
            chip = QToolButton()
            chip.setText(f"{int(t) // 60}:{int(t) % 60:02d}  ✕")
            chip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            chip.setToolTip(i18n.t("Delete the highlight at %s s") % f"{t:.1f}")
            chip.setStyleSheet(
                "QToolButton { background:#ffe0b2; border:1px solid #ff9800;"
                " border-radius:9px; padding:1px 6px; }")
            chip.clicked.connect(lambda _=False, v=float(t):
                                 self.pdMarkDeleteRequested.emit(v))
            self.pd_marks_lyt.addWidget(chip)
        if not marks:
            hint = QLabel("no marks — scrub to a crash and hit 🎯")
            hint.setStyleSheet("color:#777; font-style:italic; font-size:11px;")
            self.pd_marks_lyt.addWidget(hint)
        self.pd_marks_lyt.addStretch(1)

    def _fill_screens(self, select: int | None = None):
        """(Re)list the connected monitors. The wanted one is found by name
        wherever the list now has it; while it is unplugged the index stands
        in, clamped to what is there. `select` is that index from a setting
        written before names were kept."""
        combo = self.presenter_screen_combo
        want = combo.currentIndex() if select is None else select
        combo.blockSignals(True)
        combo.clear()
        for label, name in screen_choices():
            combo.addItem(label, name)
        n = combo.count()
        if n:
            found = combo.findData(self._screen_name) if self._screen_name else -1
            combo.setCurrentIndex(found if found >= 0 else max(0, min(n - 1, want)))
            if not self._screen_name:
                self._screen_name = str(combo.currentData() or "")
        combo.blockSignals(False)

    def _on_screen_picked(self, _index: int):
        self._screen_name = str(self.presenter_screen_combo.currentData() or "")

    def presenter_screen(self) -> int:
        return max(0, self.presenter_screen_combo.currentIndex())

    def presenter_screen_name(self) -> str:
        """The monitor picked for the presenter — also while it is unplugged."""
        return self._screen_name

    def keep_awake(self) -> bool:
        """Whether the screensaver and the display timeout are held off while
        something is playing or the presenter screen is open."""
        return self.awake_check.isChecked()

    def set_presenter_on(self, on: bool):
        """Reflect the presenter window's real state (it can be closed with Esc
        or its window button, not only via the toggle)."""
        self.presenter_btn.setChecked(bool(on))

    # ── 🎉 Party play set ─────────────────────────────────────────────────────

    def play_set(self) -> dict:
        """The controls a play set overrides, as they stand now."""
        return {"secs": self._secs,
                "fade": self.fade_secs(),
                "fade_inside": self.fade_inside(),
                "advance": self.advance_check.isChecked(),
                "pause_off": not self.pause_check.isChecked(),
                "loudness": self.loudness_check.isChecked(),
                "announce": self.announce_check.isChecked(),
                "dblclick": self.dblclick_check.isChecked(),
                "xfade": self.xfade_setting_secs(),
                "xfade_on": self.xfade_on(),
                "xfade_curve": self.xfade_curve()}

    def apply_play_set(self, secs: int, advance: bool, pause_off: bool,
                       loudness: bool | None = None, announce: bool | None = None,
                       fade: float | None = None, dblclick: bool | None = None,
                       xfade: float | None = None,
                       xfade_on: bool | None = None,
                       xfade_curve: str | None = None,
                       fade_inside: bool | None = None) -> list[str]:
        """Put them onto the given values and report what really changed,
        phrased for a toast ("play length → full"). `loudness`, `announce`,
        `fade`, `dblclick` and the crossfade's are optional: a list stored
        before they joined the set doesn't carry them, and must then leave
        those controls alone."""
        changed: list[str] = []
        if secs != self._secs:
            self._secs = secs
            self._refresh_len_lbl()
            changed.append(i18n.t("play length → %s")
                           % (i18n.t("full") if secs == 0
                              else "%d:%02d" % (secs // 60, secs % 60)))
        if fade is not None and float(fade) != self.fade_spin.value():
            self.fade_spin.setValue(float(fade))
            # :g so a whole second reads "3 s" and not "3.0 s".
            changed.append(i18n.t("fade-out → %s s") % ("%g" % float(fade)))
        if (fade_inside is not None
                and bool(fade_inside) != self.fade_inside_check.isChecked()):
            self.fade_inside_check.setChecked(bool(fade_inside))
            changed.append(i18n.t("fade-out → within the length") if fade_inside
                           else i18n.t("fade-out → after the length"))
        if advance != self.advance_check.isChecked():
            self.advance_check.setChecked(advance)
            changed.append(i18n.t("auto-advance → on") if advance
                           else i18n.t("auto-advance → off"))
        if pause_off == self.pause_check.isChecked():
            self.pause_check.setChecked(not pause_off)
            changed.append(i18n.t("pause between songs → off (no break music)")
                           if pause_off else i18n.t("pause between songs → on"))
        if loudness is not None and loudness != self.loudness_check.isChecked():
            self.loudness_check.setChecked(loudness)
            changed.append(i18n.t("equalize volume → on") if loudness
                           else i18n.t("equalize volume → off"))
        if announce is not None and announce != self.announce_check.isChecked():
            self.announce_check.setChecked(announce)
            changed.append(i18n.t("announce next dance → on") if announce
                           else i18n.t("announce next dance → off"))
        if dblclick is not None and dblclick != self.dblclick_check.isChecked():
            self.dblclick_check.setChecked(dblclick)
            changed.append(i18n.t("double-click → starts the title") if dblclick
                           else i18n.t("double-click → cues it"))
        # 🔀 Said as it is heard: the seconds of a crossfade that stays off
        # change nothing on the floor, so they are not reported.
        was, was_curve = self.xfade_secs(), self.xfade_curve()
        if xfade is not None:
            self.xfade_spin.setValue(float(xfade))
        if xfade_on is not None:
            self.xfade_check.setChecked(bool(xfade_on))
        if xfade_curve is not None:
            self.xfade_curves.set_curve(xfade_curve)
        now = self.xfade_secs()
        if now != was:
            changed.append(i18n.t("crossfade → %s s") % ("%g" % now)
                           if now > 0 else i18n.t("crossfade → off"))
        if now > 0 and self.xfade_curve() != was_curve:
            changed.append(i18n.t("crossfade curve → %s")
                           % self.xfade_curves.curve_name())
        if changed:
            self.settingsChanged.emit()
        return changed

    def set_party_on(self, on: bool):
        """Reflect the party set's real state without re-firing the toggle."""
        self.party_btn.blockSignals(True)
        self.party_btn.setChecked(bool(on))
        self.party_btn.blockSignals(False)
        if on:
            self.set_tournament_on(False)   # the two sets are never both on

    def set_tournament_on(self, on: bool):
        """Light the 🏆 button while the panel stands on the tournament values.

        A click already toggles the button by itself, so this is also what puts
        it back on after someone presses it while it is lit.
        """
        self.tournament_btn.blockSignals(True)
        self.tournament_btn.setChecked(bool(on))
        self.tournament_btn.blockSignals(False)

    def tournament_on(self) -> bool:
        return self.tournament_btn.isChecked()

    def _on_pause_on(self, on: bool):
        """The pause was switched on or off: follow it in the row, and let the
        engine see a pause of 0 while it is off (the seconds stay stored)."""
        self._sync_pause_row()
        self.settingsChanged.emit()

    def _sync_pause_row(self):
        """Take off what cannot happen, grey out what merely has no effect.

        Without ⏭ auto-advance the operator starts every song by hand: there is
        no gap between two songs and no end to run past, so the pause row and
        the 🔁 tick are not dead options — they are no options at all, and they
        leave the panel entirely. With the pause itself switched off, its
        seconds and the filler music only grey out, because that switch is
        right there to click again. Nothing is forgotten either way — the
        values stay where they are and come back with the checkbox."""
        advancing = self.advance_check.isChecked()
        pausing = advancing and self.pause_check.isChecked()
        self.pause_row_box.setVisible(advancing)
        # 🔀 A crossfade is the opposite of a pause: it needs the titles to
        # follow with no gap at all. Under a pause it is no option, so it
        # leaves the panel, and what the pause shows sits under its switch.
        self.xfade_row_box.setVisible(advancing and not pausing)
        # Same reason, one line up: nothing runs on by itself without ⏭, so
        # neither can the list start over.
        self.repeat_check.setVisible(advancing)
        self.pause_spin.setEnabled(pausing)
        self.pause_music_box.setEnabled(pausing)
        self.pause_vol_box.setEnabled(pausing)
        # No pause means no gap to fill — take the filler controls off the
        # panel rather than leave two dead rows in the way.
        self.pause_sub_box.setVisible(pausing)
        self._sync_announce_when()

    def _refresh_len_lbl(self):
        secs = self._shown_secs()
        self.len_lbl.setText("full" if secs == 0
                             else f"{secs // 60}:{secs % 60:02d}")
        self.len_plus.setEnabled(secs != 0)
        dance = self._dance_len
        self.len_dance_lbl.setVisible(dance is not None)
        if dance is not None:
            self.len_dance_lbl.setText(i18n.t("🏆 %s — its own length") % dance[1])

    # ── Values read by MainWindow's playback engine ──

    def play_secs(self) -> int:
        """Seconds per song, 0 = play to the track's own end (see
        `timed_enabled`, which every caller checks first)."""
        return self._secs

    def fade_secs(self) -> float:
        return self.fade_spin.value()

    def fade_inside(self) -> bool:
        """Whether the fade-out ends at the play length (else after it)."""
        return self.fade_inside_check.isChecked()

    def xfade_secs(self) -> float:
        """🔀 Crossfade length as playback runs it, 0 = switched off."""
        return self.xfade_spin.value() if self.xfade_check.isChecked() else 0.0

    def xfade_setting_secs(self) -> float:
        """The crossfade seconds as shown, kept across an off/on switch."""
        return self.xfade_spin.value()

    def xfade_on(self) -> bool:
        return self.xfade_check.isChecked()

    def xfade_curve(self) -> str:
        """🔀 The crossfade's shape, by the name the sets store."""
        return self.xfade_curves.curve()

    def _sync_xfade_row(self, *_):
        """The seconds and the curve count only while the switch is on; the
        picture shows what is heard — the fade, or the hard cut."""
        on = self.xfade_check.isChecked()
        self.xfade_spin.setEnabled(on)
        self.xfade_curves.setEnabled(on)
        self.xfade_view.set_curve(self.xfade_curve())
        self.xfade_view.set_secs(self.xfade_secs())
        self._sync_announce_when()

    def _crossfade_runs(self) -> bool:
        """Whether titles cross over: the switch on, ⏭ auto-advance and no
        pause — under one the crossfade row is not even on the panel."""
        return (self.xfade_check.isChecked() and self.advance_check.isChecked()
                and not self.pause_check.isChecked())

    def _sync_announce_when(self):
        """🔀 A crossfade names the dance when the crossover is through,
        after the music started, so over/before has nothing to say and leaves
        the caption. Its choice stays and comes back with it."""
        if hasattr(self, "announce_style_lbl"):    # built after the crossfade row
            self._refresh_announce_style()

    def timed_enabled(self) -> bool:
        """'full' on the ladder is the off position — no cut, no fade-out."""
        return self._secs > 0

    def auto_advance(self) -> bool:
        return self.advance_check.isChecked()

    def _follow_advance_with_announce(self, advancing: bool):
        """✋ Manual means the operator starts every song themselves, so an
        announcement would call a dance nothing then plays. Off it goes, and
        ⏭ Auto puts back what was configured — not simply "on", so an evening
        run without announcements stays without them.

        A value switched on by hand in the meantime is left alone: what is
        remembered is what to restore, never what to enforce."""
        if advancing:
            if self._announce_before_manual:
                self.announce_check.setChecked(True)
            self._announce_before_manual = False
        else:
            self._announce_before_manual = self.announce_check.isChecked()
            self.announce_check.setChecked(False)

    def repeat_list(self) -> bool:
        """Whether the end of the list is followed by its own beginning.

        Its own tick is not enough — without ⏭ auto-advance nothing follows
        anything, and the tick then stays checked but off the panel (the rule
        `pause_available` follows for the same reason)."""
        return self.auto_advance() and self.repeat_check.isChecked()

    def repeat_setting_on(self) -> bool:
        """The tick as shown, kept across an auto-advance off/on toggle."""
        return self.repeat_check.isChecked()

    def pause_secs(self) -> int:
        """Pause between songs, 0 while the ⏭ off switch is engaged — the next
        song then starts as soon as the current one ends."""
        return self.pause_spin.value() if self.pause_check.isChecked() else 0

    def pause_enabled(self) -> bool:
        return self.pause_check.isChecked()

    def pause_available(self) -> bool:
        """Whether a between-songs pause can actually happen.

        Its own tick is not enough: without ⏭ auto-advance the operator starts
        every song by hand, so there is no gap for a pause to fill — and the
        tick box stays checked but off the panel in that state, which is why
        both halves have to be asked."""
        return self.auto_advance() and self.pause_check.isChecked()

    def pause_setting_secs(self) -> int:
        """The configured seconds as shown, kept across an off/on toggle."""
        return self.pause_spin.value()

    def announce_next(self) -> bool:
        return self.announce_check.isChecked()

    def announce_wait(self) -> bool:
        """Whether the music waits for the start call instead of coming in
        under it, as ⚙ Settings has it. Never while titles cross over: a
        title the crossfade does not reach (the first, the one after a 🐂
        highlight) is named over its first bars like the rest."""
        return self._announce_wait and not self._crossfade_runs()

    def announce_wait_setting_on(self) -> bool:
        """The lead as ⚙ Settings saved it, kept while a crossfade runs."""
        return self._announce_wait

    def announce_heat(self) -> bool:
        return self._announce_heat

    def announce_voice(self) -> str:
        """'female', 'male' or 'random' — which recorded voice to announce in."""
        return self._announce_voice

    def dblclick_plays(self) -> bool:
        """True where a double-click in a deck starts the title, False where it
        only cues it on the player."""
        return self.dblclick_check.isChecked()

    def remember_pos(self) -> bool:
        """True where the spot a title stopped at is kept and played from again.

        The marks themselves live only as long as the app does — this is the
        switch, not the marks."""
        return self.remember_check.isChecked()

    def loudness_eq(self) -> bool:
        """User's stored intent (persisted), independent of whether loudness
        data is available yet — so the preference survives a restart."""
        return self.loudness_check.isChecked()

    def loudness_active(self) -> bool:
        """Whether equalization should be applied right now. Per-track: active
        whenever the box is ticked — `_loudness_gain` then pulls each MEASURED
        track towards the target and leaves unmeasured tracks at unity (original
        volume), so the dB readout shows for any measured track being played."""
        return self.loudness_check.isChecked()

    def pd_highlight_stop(self) -> bool:
        return self.pd_check.isChecked()

    def set_pd_highlight_stop(self, on: bool) -> list[str]:
        """Switch the 🐂 stop and report it the way `apply_play_set` does — the
        🏆 tournament set switches it off, its detection being too unreliable to
        cut a competition Paso Doble on."""
        if bool(on) == self.pd_check.isChecked():
            return []
        self.pd_check.setChecked(bool(on))   # …which reports the change itself
        return [i18n.t("🐂 Paso Doble highlight stop → on") if on
                else i18n.t("🐂 Paso Doble highlight stop → off")]

    def pd_highlight_n(self) -> int:
        return self.pd_spin.value()

    def set_pd_highlight_n(self, n: int) -> list[str]:
        """Set which highlight stops the dance and report it the way
        `apply_play_set` does — the 🏆 set carries its own."""
        if int(n) == self.pd_spin.value():
            return []
        self.pd_spin.setValue(int(n))
        return [i18n.t("🐂 Paso Doble stop after highlight → %d") % int(n)]

    def pd_start_delay(self) -> int:
        """Seconds a Paso Doble waits after the call before the music starts
        (0 = start at once)."""
        return self.pd_delay_spin.value()

    def set_pd_start_delay(self, secs: int) -> list[str]:
        """Set 'Start after' and report it the way `apply_play_set` does — the
        🏆 tournament set puts it at 0 s, the chairman's call being the wait."""
        if int(secs) == self.pd_delay_spin.value():
            return []
        self.pd_delay_spin.setValue(int(secs))
        return [i18n.t("🐂 Paso Doble start after → %s s") % int(secs)]

    def pause_music(self) -> list[str]:
        return list(self._pause_music)

    def pause_music_vol(self) -> int:
        """Filler loudness in percent of the normal playback volume."""
        return self.pause_vol_spin.value()

    def set_loudness_available(self, available: bool, missing: int = 0):
        """Equalize-volume is only offerable when every playlist track has a
        measured loudness (`missing` = unanalyzed count, -1 = no data at all) —
        a partially equalized playlist would jump in level between songs."""
        # Per-track equalization: the box always works (measured tracks are pulled
        # to the target, unmeasured ones play untouched), so this only updates the
        # tooltip to flag how many open-playlist tracks aren't measured yet.
        self._loudness_available = available
        base = ("Compensate loudness differences between tracks on playback:\n"
                "each song's measured EBU R128 loudness is pulled towards a\n"
                "common target, so quiet old recordings and loud modern\n"
                "masters play at a similar level.")
        if available:
            self.loudness_check.setToolTip(base)
        elif missing < 0:
            self.loudness_check.setToolTip(
                i18n.t(base) + "\n\n" + i18n.t("ℹ No loudness measured yet — tracks play at their\n"
                                                 "original volume. Run 📊 Analyze loudness (⚙ Settings)\n"
                                                 "to equalize them."))
        else:
            self.loudness_check.setToolTip(
                i18n.t(base) + "\n\n"
                + (i18n.t("ℹ %d open-playlist track not measured yet — it plays at original volume.\nRun 📊 Analyze loudness (⚙ Settings) to equalize it too.") if missing == 1
                   else i18n.t("ℹ %d open-playlist tracks not measured yet — they play at original volume.\nRun 📊 Analyze loudness (⚙ Settings) to equalize them too.")) % missing)

    def set_countdown(self, text: str):
        # Fit-to-width: start at the full 22px clock font and only step down
        # as far as needed so longer statuses ("🐂 detecting highlights…",
        # "🏁 Hauptrunde finished") stay fully visible at maximum size.
        if text == self._countdown_text:
            return
        self._countdown_text = text
        if text:
            avail = max(self.countdown_lbl.width() - 8, 160)
            font = QFont("Consolas")
            size = 22
            while size > 11:
                font.setPixelSize(size)
                if QFontMetrics(font).horizontalAdvance(text) <= avail:
                    break
                size -= 1
            self.countdown_lbl.setStyleSheet(
                f"font-size:{size}px; font-family:Consolas,monospace;"
                " color:#444;")
        self.countdown_lbl.setText(text)
