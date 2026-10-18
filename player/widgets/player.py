"""The big bottom player bar and the hover preview overlay.

Extracted from dancesport_gui.py (view split): BigPlayerWidget and
PreviewOverlay. The card's parts are built in player/widgets/player_setup.py;
the sliders, colours and format helpers both use are in
player/widgets/player_parts.py.
"""
import logging
import shiboken6

import math
from PySide6.QtCore import (
    QEvent,
    QPoint,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path
from collections.abc import Callable
from player.widgets.artwork import cover
from shared.appearance.icons import (
    WARN,
    button as icon_button,
    html as icon_html,
    icon,
    pixmap as icon_pixmap,
)
from player.widgets.player_parts import (
    _ART_PX,
    _CARD_INK,
    _ClickSlider,
    _fmt_ms,
    _OVERLAY_INK,
    _takt_text,
    _TEMPO_STEP,
)
from player.widgets.player_setup import BigPlayerSetupMixin

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

log = logging.getLogger("dancesport.gui.player")

class PreviewOverlay(QFrame):
    """Small floating player shown right below the row whose ▶ was clicked:
    title, seek bar, restart / ±10 s skip, elapsed + remaining time and a
    volume slider. Drag anywhere on its background to move it — the chosen
    spot is reused the next time it pops up. The ⚙ menu can disable the
    overlay (re-enable in ⚙ Settings → 'Preview player')."""

    closeRequested = Signal()    # ✕ clicked → MainWindow stops playback
    disableRequested = Signal()  # ⚙ → Disable → MainWindow persists the setting
    prevRequested = Signal()     # ⏮ → MainWindow plays the previous song row
    nextRequested = Signal()     # ⏭ → MainWindow plays the next song row
    duckToggled = Signal(bool)   # 🔉 → MainWindow pulls everything down (_DESK_DUCK)

    def __init__(self, player: QMediaPlayer, audio_out: QAudioOutput,
                 get_vol: Callable[[], float] | None = None,
                 set_vol: Callable[[float], None] | None = None,
                 duck: bool = True):
        super().__init__(None)   # reparented into a deck's viewport on show_for()
        self._player = player
        self._audio_out = audio_out
        # MainWindow routes the slider through its base-volume factor so the
        # fade-out / loudness gains stay multiplied in; without callables the
        # slider drives the audio output directly (standalone use).
        self._get_vol = get_vol or audio_out.volume
        self._set_vol = set_vol or audio_out.setVolume
        self._dragging = False
        self._full_title = ""
        self._ducked = False
        self._drag_off: QPoint | None = None   # press point while moving the overlay
        self._user_pos: QPoint | None = None   # sticky position after a manual drag
        self._anchor: QPoint | None = None     # where it must stay while shown
        self.setObjectName("PreviewOverlay")
        # Light card in the app's palette (row blue-gray + undo-button blues).
        self.setStyleSheet(
            "#PreviewOverlay { background:#f3f6fc;"
            " border:1px solid #9aa6c0; border-radius:6px; }"
            "QLabel { color:#333; font-size:10px; background:transparent; }"
            "QToolButton { color:#1565c0; background:transparent; border:none;"
            " font-size:11px; font-weight:bold; padding:0px 3px; border-radius:3px; }"
            "QToolButton:hover { background:#d6e6fa; }"
            "QSlider::groove:horizontal { height:5px; border-radius:2px;"
            " background:#dde4f0; }"
            "QSlider::sub-page:horizontal { background:#4a82d2; border-radius:2px; }"
            "QSlider::handle:horizontal { width:9px; margin:-3px 0;"
            " border-radius:4px; background:#1565c0; }"
            # Seek bar: same slim look as the volume slider, but the widget is
            # taller — the whole 18 px strip is click/drag-sensitive.
            "QSlider#seek { min-height:18px; }"
        )

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(6, 3, 6, 4)
        lyt.setSpacing(1)

        self._build_title_row(lyt)

        self._build_seek_row(lyt, duck)

        # The decks own Space / Ctrl+←→ shortcuts — never steal keyboard focus.
        for w in self.findChildren(QWidget):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        player.durationChanged.connect(self._on_duration)
        player.positionChanged.connect(self._on_position)

    def _build_title_row(self, lyt):
        """Row 1: ✕, the title (the drag handle) and ⚙."""
        # ── Row 1: ✕ | title | ⚙ ──
        top = QHBoxLayout()
        top.setSpacing(4)
        close_btn = QToolButton()
        icon_button(close_btn, "close", 11, _OVERLAY_INK)
        close_btn.setToolTip("Close the preview and stop playback  (Ctrl+X)")
        close_btn.clicked.connect(self.closeRequested.emit)
        top.addWidget(close_btn)
        self._title = QLabel("")
        # A title comes from an ID3 tag or an .m3u line, i.e. from whoever made
        # the file. Under the AutoText default Qt would parse markup in it and
        # its resource loader would fetch an <img src>, including over UNC.
        self._title.setTextFormat(Qt.TextFormat.PlainText)
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._title.setStyleSheet("font-weight:bold; color:#2c3e60;")
        self._title.setToolTip("Drag here to move the preview player")
        self._title.setCursor(Qt.CursorShape.OpenHandCursor)
        top.addWidget(self._title, stretch=1)
        gear_btn = QToolButton()
        icon_button(gear_btn, "gear", 12, _OVERLAY_INK)
        gear_btn.setToolTip("Preview-player options")
        gear_btn.clicked.connect(lambda: self._gear_menu(gear_btn))
        top.addWidget(gear_btn)
        lyt.addLayout(top)

    def _build_seek_row(self, lyt, duck):
        """Row 2: the seek bar, the transport, the times and the volume."""
        # ── Row 2: seek slider | ⏮ ◀◀ ▶▶ | times | 🔊 volume ──
        bot = QHBoxLayout()
        bot.setSpacing(4)
        self._slider = _ClickSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("seek")
        self._slider.setRange(0, 0)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderMoved.connect(self._on_slider_moved)
        self._slider.sliderReleased.connect(self._on_slider_released)
        # Click = seek, on whichever player the overlay follows by then.
        self._slider.clickJumped.connect(lambda ms: self._player.setPosition(ms))
        bot.addWidget(self._slider, stretch=1)

        for name, tip, cb in (
                ("prev", "Previous title", self.prevRequested.emit),
                ("rewind", "Back 10 s", lambda: self._skip(-10_000)),
                ("forward", "Forward 10 s", lambda: self._skip(+10_000)),
                ("next", "Next title", self.nextRequested.emit)):
            b = QToolButton()
            icon_button(b, name, 12, _OVERLAY_INK)
            b.setToolTip(tip)
            b.clicked.connect(cb)
            bot.addWidget(b)

        self._time_lbl = QLabel("00:00  -00:00")
        self._time_lbl.setStyleSheet(
            "font-family:Consolas,monospace; font-size:10px; color:#555;")
        bot.addWidget(self._time_lbl)

        self._duck_btn = QToolButton()
        icon_button(self._duck_btn, "volume", 12, _OVERLAY_INK)
        self._duck_btn.setCheckable(True)   # stays pressed while ducked
        self._duck_btn.setToolTip("Duck to 20 % / back to full")
        self._duck_btn.clicked.connect(self._toggle_duck)
        bot.addWidget(self._duck_btn)
        # 🎧 The pre-listen's mini player has none: 🔉 ducks the hall.
        if not duck:
            self._duck_btn.hide()
        self._vol = _ClickSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setFixedWidth(50)
        self._vol.setToolTip("Volume")
        self._vol.valueChanged.connect(lambda v: self._set_vol(v / 100.0))
        bot.addWidget(self._vol)
        lyt.addLayout(bot)

    def set_player(self, player: QMediaPlayer):
        """Follow another QMediaPlayer — a 🔀 crossfade makes the second
        player the deck, and this overlay drives the deck."""
        if player is self._player:
            return
        old = self._player
        old.durationChanged.disconnect(self._on_duration)
        old.positionChanged.disconnect(self._on_position)
        self._player = player
        player.durationChanged.connect(self._on_duration)
        player.positionChanged.connect(self._on_position)
        self._on_duration(player.duration())
        self._on_position(player.position())

    # ── Placement ──

    def show_for(self, table: QTableView, row: int, title: str):
        """Float the overlay inside `table`'s viewport, just below `row`
        (above it when the row sits at the bottom edge). After the user has
        dragged it somewhere, that spot is reused instead."""
        vp = table.viewport()
        if self.parentWidget() is not vp:
            self.setParent(vp)
        self._full_title = title
        self.resize(min(380, max(260, vp.width() - 12)), self.sizeHint().height())
        self._elide_title()
        self._vol.blockSignals(True)
        self._vol.setValue(round(self._get_vol() * 100))
        self._vol.blockSignals(False)
        self.set_ducked(self._ducked)
        if self._user_pos is not None:
            self.move(self._clamped(self._user_pos))
        else:
            y = table.rowViewportPosition(row) + table.rowHeight(row) + 2
            if y + self.height() > vp.height() - 2:
                y = table.rowViewportPosition(row) - self.height() - 2
            self.move(self._clamped(QPoint(6, y)))
        self._anchor = self.pos()
        self.show()
        self.raise_()

    def _clamped(self, p: QPoint) -> QPoint:
        """Keep the overlay fully inside its parent viewport."""
        vp = self.parentWidget()
        if not vp:
            return p
        return QPoint(
            max(2, min(p.x(), max(2, vp.width() - self.width() - 2))),
            max(2, min(p.y(), max(2, vp.height() - self.height() - 2))))

    # ── Drag-to-move (also swallows clicks so they don't hit the table below) ──
    # Only the TITLE BAR starts a move — the slider row is left alone so a
    # slightly-missed seek can never fling the overlay around.

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if (event.button() == Qt.MouseButton.LeftButton
                and pos.y() <= self._title.geometry().bottom() + 2):
            self._drag_off = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_off is not None:
            self.move(self._clamped(
                self.pos() + event.position().toPoint() - self._drag_off))
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_off is not None:
            self._drag_off = None
            self._user_pos = self._anchor = self.pos()   # spot for the next show
            self.unsetCursor()
        event.accept()

    def moveEvent(self, event):
        """Stay where it was put when the list scrolls underneath.

        A scroll area scrolls by MOVING its viewport's children, so one turn of
        the wheel over a long library list used to carry the overlay off the top
        edge — it looked like the player had vanished mid-song. Only a drag may
        move it; anything else is put straight back."""
        super().moveEvent(event)
        if (self._drag_off is None and self._anchor is not None
                and self.pos() != self._anchor):
            self.move(self._anchor)

    def mouseDoubleClickEvent(self, event):
        event.accept()   # don't let double-clicks reach the table either

    def title(self) -> str:
        """The full title it shows — not the elided caption."""
        return self._full_title

    def _elide_title(self):
        fm = self._title.fontMetrics()
        avail = max(40, self.width() - 90)
        self._title.setText(fm.elidedText(self._full_title, Qt.TextElideMode.ElideRight, avail))

    # ── Player feedback ──

    def _on_duration(self, dur: int):
        self._slider.setRange(0, max(0, dur))
        self._update_time(self._player.position())

    def _on_position(self, pos: int):
        if not self._dragging:
            self._slider.blockSignals(True)
            self._slider.setValue(pos)
            self._slider.blockSignals(False)
            self._update_time(pos)

    def _update_time(self, pos: int):
        dur = self._slider.maximum()   # kept in sync by durationChanged
        self._time_lbl.setText(f"{_fmt_ms(pos)}  -{_fmt_ms(dur - pos)}")

    # ── Controls ──

    def _on_slider_pressed(self):
        self._dragging = True

    def _on_slider_moved(self, value: int):
        self._update_time(value)   # live readout while scrubbing

    def _on_slider_released(self):
        self._dragging = False
        self._player.setPosition(self._slider.value())

    def _skip(self, delta_ms: int):
        dur = self._player.duration()
        pos = max(0, self._player.position() + delta_ms)
        if dur > 0:
            pos = min(pos, dur)
        self._player.setPosition(pos)

    def _toggle_duck(self):
        """🔉 Down to a fifth for a word over the music. MainWindow owns the
        factor, so this overlay and the big card always agree — and the button
        follows that answer, not the click, so the two never drift apart."""
        self.duckToggled.emit(not self._ducked)
        self._duck_btn.setChecked(self._ducked)

    def set_ducked(self, on: bool):
        self._ducked = bool(on)
        self._duck_btn.setIcon(icon("volume_low" if self._ducked else "volume",
                                    12, _OVERLAY_INK))
        self._duck_btn.setChecked(self._ducked)

    def _gear_menu(self, anchor: QToolButton):
        menu = QMenu(self)
        act = menu.addAction(icon("blocked"),
                             "Disable preview player  (re-enable in Settings)")
        act.triggered.connect(self.disableRequested.emit)
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))


class BigPlayerWidget(BigPlayerSetupMixin, QFrame):
    """UltraMixer-style master player docked on top of the Playing-mode panel:
    big readable title + elapsed/remaining time, full-width seek bar and large
    transport buttons — everything sized for a quick glance from a standing
    position at the tournament desk. Drives the shared QMediaPlayer."""

    prevRequested = Signal()   # ⏮ → previous song row of the active deck
    nextRequested = Signal()   # ⏭ → next song row of the active deck
    tempoResetModeChanged = Signal(bool)   # ↺ checkbox → MainWindow persists it
    tsoModeChanged = Signal(bool)          # TSO toggle → auto-equalize the heat tempo
    tempoApplied = Signal()                # rate changed → the ⏳ limit moves with it
    extendPauseRequested = Signal()        # ⏱➕ → lengthen the running auto-advance pause
    toPauseRequested = Signal()            # ⏸♪ → end this song now, jump to the pause music
    fadeOutRequested = Signal()            # 🔉↓ → fade the playing song out now
    panicRequested = Signal()              # 🛑 → fade to silence and HOLD (no advance)
    duckToggled = Signal(bool)             # 🔉 → _DESK_DUCK on everything audible
    fileDropped = Signal(str)              # a track dropped onto the card → play it

    def __init__(self, player: QMediaPlayer, audio_out=None,
                 get_vol: Callable[[], float] | None = None,
                 set_vol: Callable[[float], None] | None = None,
                 parent=None, cache_of: Callable[[], object] | None = None):
        super().__init__(parent)
        self._player = player
        # Volume goes through MainWindow's base-volume factor so the fade-out
        # ramp and the loudness gain stay multiplied in (same wiring as the
        # preview overlay); the 🔉 duck is a factor of its own over there, so
        # the card and the overlay always show the same state.
        self._audio_out = audio_out
        self._get_vol = get_vol or (audio_out.volume if audio_out else (lambda: 1.0))
        self._set_vol = set_vol or (audio_out.setVolume if audio_out else (lambda _v: None))
        self._tempo_player = player   # the fader always targets the MAIN player
        self._ducked = False
        self._dragging = False
        self._full_title = ""
        self._dur = 0   # the track's real duration (slider max may be a limit)
        # Set by MainWindow: after a 🏁 round-end stop the ⏯ button starts
        # the next round's first song (returns True when it handled the tap).
        self.resume_cb: Callable[[], bool] | None = None
        # Walking text for a title or subtitle wider than its label (started
        # by _walk_if_needed).
        self._marquee_pos = 0
        self._sub_pos = 0
        self._marquee = QTimer(self)
        self._marquee.setInterval(300)
        self._marquee.timeout.connect(self._marquee_step)
        self._build_skin()

        # The blocks below stand in a body of their own, so the whole
        # arrangement can be swapped for the wide one (see set_wide) without
        # the frame, its skins or its wiring noticing.
        outer = self._outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._wide = False
        self._extra = None            # guest in the wide strip's middle
        self._lead = None             # …and in its bottom-right corner
        self._body = QWidget()
        outer.addWidget(self._body)

        self._build_head()
        # The title's room changes without the card changing size too — the
        # cover coming in, the wide strip handing its middle to the mode panel.
        self._title.installEventFilter(self)
        self._sub.installEventFilter(self)
        self._build_aux_buttons()
        self._build_time()
        self._build_seek(cache_of)
        self._build_transport()
        self._build_aux_row()
        self._build_volume()
        self._build_tempo()

        # The decks own Space / Ctrl+←→ shortcuts — never steal keyboard focus.
        self._relayout()
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Drop a track from a deck / the library onto the card to play it.
        self.setAcceptDrops(True)

        player.durationChanged.connect(self._on_duration)
        player.positionChanged.connect(self._on_position)
        player.playbackStateChanged.connect(self._on_state)
        self.set_now("")

    def set_wide(self, on: bool):
        """Lay the card out along the width instead of down a panel — the wide
        strip that stands above the decks."""
        on = bool(on)
        if on != self._wide:
            self._wide = on
            self._relayout()

    def set_lead_widget(self, w):
        """Take something into the strip's bottom-right corner.

        The 📝/▶ mode switch stands there while the strip is Playing mode.
        Beside the transport it was 240 px of the player's own column, and
        that column sets how much width is left for the mode panel — the
        panel paid for it a whole line deep. In the corner it costs the strip
        one short row under a panel that is now a row shorter. Ignored while
        the card stands in a panel: there the switch is above it anyway."""
        if w is not self._lead:
            self._lead = w
            self._relayout()

    def set_extra_widget(self, w):
        """Let somebody else have the strip's empty middle.

        Wide, the card holds its own two ends and leaves a monitor's worth of
        nothing between them. That is where the Playing-mode panel goes, so
        the whole of the mode stands in one band and the decks get the side
        panel's width back. Ignored while the card stands in a panel — there
        it is the guest, not the host."""
        if w is not self._extra:
            self._extra = w
            self._relayout()

    def is_wide(self) -> bool:
        return self._wide

    def _corner_row(self):
        """The bottom line of the strip's right-hand end — whatever was handed
        over as the lead widget, pushed into the corner."""
        foot = QHBoxLayout()
        foot.addStretch(1)
        if self._lead is not None:
            foot.addWidget(self._lead, 0, Qt.AlignmentFlag.AlignBottom)
        return foot

    def _relayout(self):
        """Put the blocks into a fresh body in the current arrangement. They are
        re-parented by being added, so the body they leave behind goes out
        empty — nothing of the card is rebuilt, only where it stands."""
        body = QWidget()
        lyt = QVBoxLayout(body)
        pad = 6 if self._wide else 8
        lyt.setContentsMargins(10, pad, 10, pad)
        lyt.setSpacing(4)
        if self._wide:
            row = self._wide_row()
            lyt.addLayout(row)
        else:
            for w in (self._head_box, self._time_box, self._wave, self._slider,
                      self._btn_box, self._aux_box, self._vol_box,
                      self._tempo_box):
                lyt.addWidget(w)
        # Wide, the card asks for ~840 px. Reported as a minimum that would
        # pin the whole window to it and stop it being resized narrower (same
        # reason the deck toolbar yields its width) — so let it shrink and
        # let the blocks elide instead.
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored if self._wide
            else QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred)
        old, self._body = self._body, body
        self._outer.replaceWidget(old, body)
        old.setParent(None)
        old.deleteLater()
        # New body, same rule: the decks own Space / Ctrl+←→, so nothing in
        # the card ever takes the keyboard.
        for w in self.findChildren(QWidget):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _wide_row(self):
        """The wide arrangement: the player on the left, its settings right."""
        # Split down the middle: on the left everything the operator SEES
        # and HITS while a song runs — what is playing, how long it still
        # has, the transport and the seek bar under it, all in one column
        # the eye never has to leave. The settings that are dialled in
        # between songs — the faders, the fade-out, the tempo switches —
        # stand out of that way on the right.
        row = QHBoxLayout()
        row.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(self._head_box)
        # Clock and transport share a row: stacked they would push the
        # strip a third deeper, and every pixel here is one the playlists
        # under it lose. Both sit hard against the left edge — the play
        # button belongs next to the clock it drives, not drifting off
        # towards the middle of the screen because there was room.
        clock = QHBoxLayout()
        clock.setSpacing(10)
        clock.addWidget(self._time_box, 0)
        clock.addWidget(self._btn_box, 0)
        clock.addStretch(1)
        left.addLayout(clock)
        right = QVBoxLayout()
        right.setSpacing(4)
        right.addWidget(self._aux_box)
        right.addWidget(self._vol_box)
        right.addWidget(self._tempo_box)
        right.addStretch(1)
        # Nothing of the card is stretched to fill. Alone, it keeps to
        # the two edges — player left, its own settings right — and the
        # monitor's spare width falls between them. With a guest the card
        # closes up on the left instead and the guest takes the whole
        # right: a light panel wants an edge to sit against, not a hole in
        # the middle of the dark.
        if self._extra is not None:
            # The seek bar runs under BOTH of the player's columns. Left
            # to the first one it would be as narrow as the transport
            # above it — and a scrub bar is only as fine as it is long.
            player = QVBoxLayout()
            player.setSpacing(4)
            top = QHBoxLayout()
            top.setSpacing(16)
            top.addLayout(left, 0)
            top.addLayout(right, 0)
            player.addLayout(top)
            player.addWidget(self._wave)
            player.addWidget(self._slider)
            # The strip is as deep as its deepest guest; the player itself
            # stays the height it is and keeps to the top rather than
            # being pulled apart to fill it.
            player.addStretch(1)
            row.addLayout(player, 0)
            # The guest and the mode switch share the right-hand end: the
            # panel takes all the height it wants and the switch sits in
            # the corner under it, hard against both edges of the card.
            far = QVBoxLayout()
            far.setSpacing(4)
            far.addWidget(self._extra, 1)
            far.addLayout(self._corner_row())
            row.addLayout(far, 1)
        else:
            left.addWidget(self._wave)
            left.addWidget(self._slider)
            left.addStretch(1)
            row.addLayout(left, 0)
            row.addStretch(1)
            right.addLayout(self._corner_row())
            row.addLayout(right, 0)
        return row

    # ── Fed by MainWindow on every play/stop ──

    def set_deck(self, player: QMediaPlayer):
        """🔀 A crossfade made the second player the deck: the card and the
        tempo fader both follow it from now on."""
        self._tempo_player = player
        self.set_player(player)

    def set_player(self, player: QMediaPlayer):
        """Retarget the card (seek bar, times, ⏯) to another QMediaPlayer —
        used for the pause-music filler while the between-songs pause runs,
        so the slider drags the FILLER and not the preloaded next song."""
        if player is self._player:
            return
        # Another player, another timeline — the 🐂 marks of the song that was
        # on the bar mean nothing on the filler (or back again).
        self.set_pd_marks([])
        self.set_waveform_track(None)
        old = self._player
        old.durationChanged.disconnect(self._on_duration)
        old.positionChanged.disconnect(self._on_position)
        old.playbackStateChanged.disconnect(self._on_state)
        self._player = player
        player.durationChanged.connect(self._on_duration)
        player.positionChanged.connect(self._on_position)
        player.playbackStateChanged.connect(self._on_state)
        self._on_duration(player.duration())
        self._on_position(player.position())
        self._on_state(player.playbackState())

    def set_now(self, title: str, subtitle: str = "", status: str = "",
                sub_icon: str = ""):
        """Show the playing song; title '' → idle, displaying `status` (e.g.
        the auto-advance pause) or 'No song selected'. `sub_icon` is a shared.appearance.icons
        name painted in front of the subtitle (the pause state)."""
        self._full_title = title or status or "No song selected"
        self._marquee_pos = 0
        # A real title means a song is playing → offer ⏸♪ jump-to-pause; an
        # empty title is idle or the pause filler (status set), so hide it.
        self._has_song = bool(title)
        self._refresh_aux_buttons()
        if title:
            self._title.setStyleSheet(
                "font-size:13px; font-weight:bold; color:#eef3fb;")
            # The idle branch below zeroed the length. A 🔁 title reloads the
            # SAME file, which sends no new durationChanged — so ask for it,
            # or the seek bar stays 0 long and every drag lands on 0.
            self._on_duration(self._player.duration())
        else:
            self._title.setStyleSheet(
                "font-size:13px; font-style:italic; color:#6e87ad;")
            self._slider.setRange(0, 0)
            self._elapsed.setText("00:00")
            self._remaining.setText("-00:00")
            self._gain_lbl.setText("")
            self._gain_icon.setVisible(False)
            self._dur = 0
            self._limit_ms = None
            self._limit_to_end = False
            self._limit_lbl.setText("")
            self._takt = None
            self._refresh_tempo_lbl()
            self._stop_end_flash()
            self.set_next_up("")   # nothing running → nothing "next"
            self.set_pd_marks([])
            self.set_waveform_track(None)
        if sub_icon:
            self._sub_icon.setPixmap(icon_pixmap(sub_icon, 12, "#8fa3c4"))
        self._sub_icon.setVisible(bool(sub_icon))
        self._full_sub = subtitle
        self._sub_pos = 0
        self._elide_sub()
        # The fade-out / aux buttons may have just (un)hidden, so the subtitle's
        # width changes only after the layout settles — re-elide on the next tick.
        QTimer.singleShot(0, self._elide_sub)
        self._elide_title()

    def set_pause_available(self, on: bool):
        """⏸♪ only works when there IS a between-songs pause to jump into.

        With 'Pause between songs' unticked the button would end the song and
        then report that nothing happened — greyed out it says so before the
        press instead of after it."""
        self._topause_btn.setEnabled(bool(on))
        self._topause_btn.setToolTip(
            "Jump straight to the pause music — end this song now and start\n"
            "the between-songs pause (e.g. the dancers are already leaving)."
            if on else
            "No pause to jump to — tick 'Pause between songs' (and ⏭\n"
            "auto-advance) in the Playing-mode panel first.")

    def set_artwork_enabled(self, on: bool):
        """🖼 Show the cover next to the title, or give the width back."""
        self._art_on = bool(on)
        self._art.setVisible(self._art_on)
        self._refresh_artwork()

    def set_waveform_enabled(self, on: bool):
        """〰 Show the title's waveform in place of the seek bar, or the seek
        bar again: the strip seeks on a click over the same stretch, so never
        both. Off, nothing is decoded; on, the title already playing loads."""
        self._wave_on = bool(on)
        self._wave.setVisible(self._wave_on)
        self._slider.setVisible(not self._wave_on)
        self._load_wave()

    def set_waveform_track(self, track: Path | None):
        """The file whose outline the strip draws; None clears the strip."""
        self._wave_path = str(track) if track is not None else None
        if self._wave_path is None:
            self._wave.set_peaks(None)
            self.set_wave_overlay([], None)
            return
        self._load_wave()

    def _load_wave(self):
        if not self._wave_on or self._wave_path is None:
            return
        self._wave.set_peaks(self._wave_loader.request(Path(self._wave_path)))

    def _on_wave_ready(self, key: str, peaks):
        if key == self._wave_path:
            self._wave.set_peaks(peaks)

    def set_wave_overlay(self, silences_secs, fade_start_ms):
        """The 🔇 spans the player skips and where the ⏳ fade-out begins (file
        time, ms; None = no timed fade)."""
        self._wave.set_silences(silences_secs)
        self._wave.set_fade_start(fade_start_ms)

    def set_artwork(self, track: Path | None, playlist: Path | None = None):
        """The track now playing and the playlist it came from — the picture is
        the playlist's if it has one, the track's own cover otherwise."""
        self._art_track = track
        self._art_list = playlist
        self._refresh_artwork()

    def _refresh_artwork(self):
        if not self._art_on:
            return
        if self._art_track is None:
            self._art.clear()
            return
        self._art.setPixmap(cover(self._art_track, self._art_list, _ART_PX))

    def set_gain(self, factor: float):
        """Show the R128 equalization gain of the playing track (1.0 → none)."""
        if abs(factor - 1.0) < 0.005:
            self._gain_lbl.setText("")
            self._gain_icon.setVisible(False)
            return
        db = 20 * math.log10(factor) if factor > 0 else 0.0
        self._gain_lbl.setText(f"{db:+.1f} dB")
        self._gain_icon.setVisible(True)

    def set_takt(self, takt: int | None):
        """Filename takt (bars/min) of the playing track — lets the tempo
        label show the resulting takt next to the percentage."""
        self._takt = takt
        self._refresh_tempo_lbl()

    def set_current_dance(self, dance: str | None):
        """Playing track's dance code — feeds the ♪ Takt overlay's Sollwert
        default. A no-op until that overlay has been opened at least once."""
        self._current_dance = dance
        if self._takt_overlay is not None:
            self._takt_overlay.set_dance(dance)

    def _toggle_takt_overlay(self, on: bool):
        if on:
            if self._takt_overlay is None:
                from player.widgets.takt_meter import TaktMeterOverlay
                self._takt_overlay = TaktMeterOverlay()
                self._takt_overlay.closeRequested.connect(
                    lambda: self._takt_btn.setChecked(False))
                self._takt_overlay.applyRequested.connect(
                    self.apply_takt_correction)
                self._takt_overlay.set_dance(self._current_dance)
            self._takt_overlay.show_near(self._takt_btn)
        elif self._takt_overlay is not None:
            self._takt_overlay.hide()

    def set_countdown(self, text: str):
        """Mirror the auto-advance pause countdown onto the card (MainWindow
        only feeds it while a pause is running — see _set_countdown)."""
        self._countdown_lbl.setText(text or "")
        self._countdown_lbl.setVisible(bool(text))

    def set_pause_active(self, on: bool):
        """Between-songs pause on/off: swaps the card's context buttons
        (⏸♪ jump-to-pause while playing ↔ ⏱➕ extend while paused) and clears
        the pause countdown when the pause ends."""
        self._is_paused = bool(on)
        if not self._is_paused:
            self.set_countdown("")
        self._refresh_aux_buttons()

    def _refresh_aux_buttons(self):
        playing = self._has_song and not self._is_paused
        self._extend_btn.setVisible(self._is_paused)
        self._topause_btn.setVisible(playing)
        self._fade_btn.setVisible(playing)
        # …and the row with them — its space stays (see _build_aux_row).
        self._aux_box.setVisible(playing or self._is_paused)

    # ── Drag a track onto the card to play it ──

    @staticmethod
    def _dropped_path(md) -> str:
        """Pull a local file path out of a drop's mime data (deck/library drags
        set both file URLs and a plain-text path fallback)."""
        for u in md.urls():
            if u.isLocalFile():
                return u.toLocalFile()
        if md.hasText():
            first = md.text().strip().splitlines()
            if first:
                return first[0].strip()
        return ""

    def dragEnterEvent(self, event):
        if self._dropped_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._dropped_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        path = self._dropped_path(event.mimeData())
        if path:
            event.acceptProposedAction()
            self.fileDropped.emit(path)
        else:
            super().dropEvent(event)

    def set_tempo_reset_on_track(self, on: bool):
        """Restore the reset-per-title preference (no signal) — the 📌 pin is
        its opposite: pinned means the tempo is NOT reset."""
        self._tempo_pin.blockSignals(True)
        self._tempo_pin.setChecked(not bool(on))
        self._tempo_pin.blockSignals(False)
        self._sync_tempo_pin()

    def tempo_reset_on_track(self) -> bool:
        return not self._tempo_pin.isChecked()

    def _sync_tempo_pin(self):
        """TSO owns the pitch while it runs, so the pin has nothing to hold: it
        comes off — and stays off and greyed out — until TSO is switched off."""
        on = self._tso_btn.isChecked()
        if on and self._tempo_pin.isChecked():
            self._tempo_pin.setChecked(False)   # the preference follows the pin
        self._tempo_pin.setEnabled(not on)

    def set_tso_mode(self, on: bool):
        """Restore the TSO auto-equalize toggle (no signal)."""
        self._tso_btn.blockSignals(True)
        self._tso_btn.setChecked(bool(on))
        self._tso_btn.blockSignals(False)
        self._sync_tempo_pin()

    def tso_mode(self) -> bool:
        return self._tso_btn.isChecked()

    def set_loop_mode(self, on: bool):
        """Put the 🔁 button where the caller wants it (the keyboard and the
        taskbar reach the loop through here, as they do the rest)."""
        self._loop_btn.setChecked(bool(on))

    def loop_mode(self) -> bool:
        """Whether the running title starts again instead of the next one.

        Deliberately not persisted anywhere: it is a decision about THIS
        moment, and an app that came back from a restart still looping one
        title would be a trap."""
        return self._loop_btn.isChecked()

    def on_new_track(self):
        """A new title is about to play — zero the fader if the user asked for
        it, so the next track starts at its natural tempo, and end any ♪ Takt
        measurement that is still standing: those taps were tapped along to the
        title that just went, and averaging the next ones against them would
        read a tempo neither track has."""
        if self.tempo_reset_on_track() and self._tempo.value() != 0:
            self._tempo.setValue(0)   # apply_tempo() right after pushes rate 1.0
        if self._takt_overlay is not None:
            self._takt_overlay.reset()

    def set_tempo_to_target(self, target_bpm: float) -> float | None:
        """Move the fader so the playing title (its takt = self._takt) is pitched
        to target_bpm, clamped to the fader's ±16 % range. Returns the takt the
        title now actually plays at — a half takt is a real answer here, so it
        is not rounded — or None when no takt / target is known."""
        if not self._takt or target_bpm <= 0:
            return None
        pct = (target_bpm / self._takt - 1.0) * 100.0
        val = max(-160, min(160, round(pct * 10)))   # fader steps are 0.1 %
        self._tempo.setValue(val)
        self.apply_tempo()   # apply at once — this is a deliberate, single set
        return self._takt * (1.0 + val / 1000.0)

    def apply_takt_correction(self, pct: float):
        """Push the fader by the ♪ Takt overlay's measured correction. The
        current fader position already contributed to the tapped tempo, so
        the correction compounds onto it rather than replacing it."""
        current_rate = 1.0 + self._tempo.value() / 1000.0
        new_rate = current_rate * (1.0 + pct / 100.0)
        val = max(-160, min(160, round((new_rate - 1.0) * 1000)))
        self._tempo.setValue(val)
        self.apply_tempo()   # apply at once — this is a deliberate, single set

    def step_tempo(self, up: bool):
        """⌨ / 🎛 One − / + step from a desk key or a controller button."""
        self._nudge_tempo(_TEMPO_STEP if up else -_TEMPO_STEP)

    def set_tempo_from_knob(self, offset: float):
        """🎛 A controller's tempo knob, −1…+1 across the fader's whole range.
        Through setValue like a − / + step, so the rate lands once the knob
        stops turning (the debounce in _on_tempo), not at every one of its
        readings."""
        self._tempo.setValue(round(offset * self._tempo.maximum()))

    def _nudge_tempo(self, delta: int):
        """Step the fader by one − / + click. setValue clamps to the range, so
        holding a button at either end simply stops there."""
        self._tempo.setValue(self._tempo.value() + delta)

    def _on_tempo(self, _value: int):
        self._refresh_tempo_lbl()   # readout follows the fader instantly
        # While the handle is held, hold off. Applying the rate as the fader
        # moves was tried and is worse: every setPlaybackRate re-inits the
        # backend's resampler, so the music breaks up under the thumb for the
        # whole length of the drag. The readout is what follows live; the sound
        # changes once, when the handle is let go. Only non-drag changes
        # (wheel / arrow keys / the − + buttons) go through the timer.
        if self._tempo.isSliderDown():
            self._tempo_apply.stop()
        else:
            # A click on the groove jumps the fader there but may still turn into
            # a double-click reset — hold the rate change until that is ruled
            # out, so the reset isn't preceded by a gap at a tempo nobody asked
            # for. Wheel / arrow keys keep the short debounce.
            self._tempo_apply.start(
                QApplication.doubleClickInterval() + 60
                if self._tempo.click_pending() else 220)

    def _on_tempo_released(self):
        self._tempo_apply.stop()
        if self._tempo.click_pending():
            # Let go this fast and it was a click, not a drag — and a click can
            # still become the double-click reset. Same hold-off as above: wait
            # it out rather than pitch the song to a value about to be undone.
            self._tempo_apply.start(QApplication.doubleClickInterval() + 60)
            return
        self.apply_tempo()   # one rate change per drag, so one short gap at most

    def reset_tempo(self):
        """Back to the track's natural tempo — the 0 button and a double-click
        on the fader. Applied at once, not debounced: this is a deliberate
        single set, usually made because the pitch is audibly wrong."""
        self._tempo_apply.stop()
        self._tempo.setValue(0)
        self.apply_tempo()

    def apply_tempo(self):
        """Push the fader's rate to the MAIN player — debounced after fader
        moves and re-asserted when a track starts (a rate set while idle can
        be dropped). If the backend hiccups and halts on the rate change,
        kick playback straight back on."""
        p = self._tempo_player
        target = 1.0 + self._tempo.value() / 1000.0
        # The ffmpeg backend re-inits its resampler on every setPlaybackRate,
        # which is the audible gap. Skip the call when the rate is already what
        # we want, so the _on_state re-assert and idle kicks don't hiccup the
        # sound for no reason.
        if abs(p.playbackRate() - target) < 0.0005:
            return
        was_playing = (p.playbackState()
                       == QMediaPlayer.PlaybackState.PlayingState)
        # The rate change is the one thing we do to a RUNNING track that makes
        # the backend tear its session down and build it again — the gap the
        # comment above warns about. If a title falls silent shortly after it
        # started, this line says whether we asked for that.
        log.info("🎛 Playback rate change\n"
                 "from: %.4f\n"
                 "to: %.4f\n"
                 "playing: %s\n"
                 "position: %d ms", p.playbackRate(), target, was_playing,
                 p.position())
        p.setPlaybackRate(target)
        if was_playing and (p.playbackState()
                            != QMediaPlayer.PlaybackState.PlayingState):
            p.play()
        # The timed cut is wall-clock, so the file position it lands on moves
        # with the rate — MainWindow re-computes the ⏳ limit from here.
        self.tempoApplied.emit()

    # ── Master volume ──

    def _on_vol_changed(self, v: int):
        self._set_vol(v / 100.0)
        self._refresh_vol_lbl()

    def _refresh_vol_lbl(self):
        self._vol_lbl.setText("duck" if self._ducked else f"{self._vol.value()}%")
        self._vol_lbl.setStyleSheet(
            "font-size:11px; font-family:Consolas,monospace;"
            + ("color:#d98f3a;" if self._ducked else "color:#8fa3c4;"))

    def toggle_duck(self):
        """🔉 Ask for a fifth of the volume (or full again). Ducking beats
        muting at the desk: a word over the music doesn't need a hole in the
        round."""
        self.duckToggled.emit(not self._ducked)
        self._duck_btn.setChecked(self._ducked)

    def set_ducked(self, on: bool):
        """The state MainWindow settled on — it owns the volume factor, and
        the filler music on its own output follows the same one. The button
        follows this, never the click, so card and overlay can't disagree."""
        self._ducked = bool(on)
        self._duck_btn.setIcon(icon("volume_low" if self._ducked else "volume",
                                    16, _CARD_INK))
        self._duck_btn.setChecked(self._ducked)
        self._refresh_vol_lbl()

    def set_volume_value(self, vol: float):
        """Show a volume set elsewhere (settings restore, preview overlay slider)
        without echoing it back through _set_vol."""
        self._vol.blockSignals(True)
        self._vol.setValue(max(0, min(100, round(vol * 100))))
        self._vol.blockSignals(False)
        self._refresh_vol_lbl()

    def _refresh_tempo_lbl(self):
        v = self._tempo.value()
        txt = f"{v / 10.0:+.1f}%" if v else "±0.0%"
        if self._takt:
            txt += f" → T{_takt_text(self._takt * (1.0 + v / 1000.0))}"
        self._tempo_lbl.setText(txt)
        self._tempo_lbl.setStyleSheet(
            "font-size:11px; font-family:Consolas,monospace;"
            + ("color:#d8b35c;" if v else "color:#8fa3c4;"))

    def set_limit(self, ms: int | None, glyph: str = "hourglass",
                  to_end: bool = False):
        """Adjusted end of playback in ms (timed cut / PD highlight stop); None →
        playback runs to the track's natural end. `glyph` is a shared.appearance.icons name
        (the sand clock for a timed cut, the highlight marker for a PD stop);
        `to_end=True` keeps it visible (as `glyph ⟶ full`) for a stop that
        resolves to the very end — e.g. a PD whose finale highlight is the
        song's own ending."""
        self._limit_ms = int(ms) if ms else None
        self._limit_glyph = glyph
        self._limit_to_end = bool(to_end) and self._limit_ms is None
        self._apply_range()
        self._update_time(self._player.position())
        self._refresh_limit()

    def _end_ms(self) -> int:
        """Where playback ACTUALLY ends: the armed limit, else the track end."""
        if self._limit_ms and 0 < self._limit_ms < self._dur:
            return self._limit_ms
        return self._dur

    def _apply_range(self):
        # The seek bar (and with it the -remaining readout) runs to the
        # actual end of playback, not the file's full length.
        self._slider.setRange(0, self._end_ms())
        self._wave.set_span(self._end_ms(), self._dur)

    def _refresh_limit(self):
        if self._limit_ms and 0 < self._limit_ms < self._dur:
            self._limit_lbl.setText(
                f"{icon_html(self._limit_glyph, 11, WARN)} {_fmt_ms(self._limit_ms)}"
                f" / {_fmt_ms(self._dur)}")
        elif self._limit_to_end and self._dur > 0:
            # Stop armed but it lands on the track's own end → "plays through".
            self._limit_lbl.setText(f"{icon_html(self._limit_glyph, 11, WARN)} "
                                    f"⟶ {_fmt_ms(self._dur)}")
        else:
            self._limit_lbl.setText("")

    def set_pd_marks(self, marks_secs, armed_secs=None):
        """Draw the Paso Doble highlights on the seek bar. Highlights beyond
        the armed stop fall outside the bar's range and simply aren't shown."""
        marks = [int(s * 1000) for s in (marks_secs or [])]
        armed = int(armed_secs * 1000) if armed_secs else None
        self._slider.set_marks(marks, armed)
        self._wave.set_marks(marks, armed)

    def set_next_up(self, text: str):
        """Show what plays after this title (⏭ …) or that the round ends here."""
        self._full_next = text or ""
        self._elide_next()

    def _elide_next(self):
        if not self._labels_alive():
            return
        fm = self._next_lbl.fontMetrics()
        avail = max(20, self._next_lbl.width())
        self._next_lbl.setText(
            fm.elidedText(self._full_next, Qt.TextElideMode.ElideRight, avail))

    def _labels_alive(self):
        """False once Qt has begun deleting this row's children. A window being
        torn down still resizes the row, and set_now_playing leaves a queued
        re-elide behind — both can land after the labels are gone, and eliding a
        destroyed label raises out of the event handler."""
        return all(shiboken6.isValid(lbl)
                   for lbl in (self._title, self._sub, self._next_lbl))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide_title()
        self._elide_sub()
        self._elide_next()

    def eventFilter(self, obj, event):
        if obj is self._title and event.type() == QEvent.Type.Resize:
            self._elide_title()
        elif obj is self._sub and event.type() == QEvent.Type.Resize:
            self._elide_sub()
        return super().eventFilter(obj, event)

    def _walks(self, lbl, text: str) -> bool:
        """Whether `text` is too wide for `lbl` and has to walk."""
        return lbl.fontMetrics().horizontalAdvance(text) > max(20, lbl.width())

    def _elide_sub(self):
        """The subtitle (dance · takt · 🥁 bpm) as it fits its label, or with
        its bpm walking: cut at the right, the bpm was the first thing lost."""
        if not self._labels_alive():
            return
        if not self._walks(self._sub, self._full_sub):
            self._sub.setText(self._full_sub)
        self._walk_if_needed()

    def _elide_title(self):
        if not self._labels_alive():
            return
        if not self._walks(self._title, self._full_title):
            self._title.setText(self._full_title)
        self._walk_if_needed()

    def _walk_if_needed(self):
        """One timer walks whichever of the two is too wide, and stops once
        both fit."""
        if not (self._walks(self._title, self._full_title)
                or self._walks(self._sub, self._full_sub)):
            self._marquee.stop()
            return
        if not self._marquee.isActive():
            self._marquee.start()
        self._marquee_step(advance=False)

    def _standing_sub_head(self, text: str) -> tuple[str, str]:
        """(head, tail) of a too-wide subtitle: the head (dance · takt · 🥁)
        stands and only the value (87 bpm) walks — unless the head leaves
        it no room, then the whole line walks."""
        head, sep, tail = text.rpartition("  ·  ")
        if not sep:
            return "", text
        icon, space, value = tail.partition(" ")
        if space and value[:1].isdigit():
            head, tail = head + sep + icon + space, value
        else:
            head += sep
        room = self._sub.width() - self._sub.fontMetrics().horizontalAdvance(head)
        return (head, tail) if room >= 24 else ("", text)

    def _marquee_step(self, advance: bool = True):
        for lbl, text, attr in ((self._title, self._full_title, "_marquee_pos"),
                                (self._sub, self._full_sub, "_sub_pos")):
            if not self._walks(lbl, text):
                continue
            head = ""
            if lbl is self._sub:
                head, text = self._standing_sub_head(text)
            # A walking bpm loops with a plain gap: a • would walk with it.
            s = text + ("      " if head else "   •   ")
            pos = getattr(self, attr) % len(s)
            if advance:
                setattr(self, attr, pos + 1)
            fm = lbl.fontMetrics()
            room = max(20, lbl.width() - fm.horizontalAdvance(head) - (2 if head else 0))
            lbl.setText(head + fm.elidedText(
                s[pos:] + s[:pos], Qt.TextElideMode.ElideRight, room))

    # ── Player feedback ──

    def _on_duration(self, dur: int):
        self._dur = max(0, dur)
        self._apply_range()   # duration arrives async, after set_limit
        self._update_time(self._player.position())
        self._refresh_limit()

    def _on_position(self, pos: int):
        if not self._dragging:
            self._slider.blockSignals(True)
            self._slider.setValue(pos)
            self._slider.blockSignals(False)
            self._update_time(pos)
        self._wave.set_position(pos)

    def _on_state(self, state):
        if self._pause_btn:
            halted = state != QMediaPlayer.PlaybackState.PlayingState
            self._pause_btn.setIcon(icon(
                "play_circle" if halted else "pause_circle", 24, _CARD_INK))
        if state != QMediaPlayer.PlaybackState.PlayingState:
            self._stop_end_flash()   # never keep blinking once playback halts
        if (state == QMediaPlayer.PlaybackState.PlayingState
                and self._player is self._tempo_player):
            # A rate set while idle may have been dropped — re-assert it, but
            # only when it differs (apply_tempo's play() kick could otherwise
            # ping-pong with this handler on a flaky rate change).
            target = 1.0 + self._tempo.value() / 1000.0
            if abs(self._player.playbackRate() - target) > 0.0005:
                self.apply_tempo()

    def _update_time(self, pos: int):
        dur = self._slider.maximum()
        remaining = max(0, dur - pos)
        self._elapsed.setText(_fmt_ms(pos))
        self._remaining.setText(f"-{_fmt_ms(remaining)}")
        self._update_end_flash(remaining, dur)

    def _update_end_flash(self, remaining: int, dur: int):
        """Blink the card red while the song is in its final seconds, so the
        end is unmissable at a glance from the desk. Only flashes while a track
        is actually playing toward its (possibly limited) end."""
        playing = (self._player.playbackState()
                   == QMediaPlayer.PlaybackState.PlayingState)
        # Only the main player warns — not the pause-music filler the card is
        # temporarily retargeted to between songs.
        warn = (playing and self._player is self._tempo_player
                and dur > 0 and 0 < remaining <= self._END_FLASH_MS)
        if warn:
            if not self._flash.isActive():
                self._flash.start()
                self._flash_step()
            # Not tied to starting the beat: a fade started first has the timer
            # running already, and the seek bar would then stay blue through
            # the final stretch it is supposed to mark.
            if self._slider.styleSheet() != self._seek_end_qss:
                self._slider.setStyleSheet(self._seek_end_qss)
            self._wave.set_ending(True)     # 〰 red with it, just as steady
        elif not warn and self._flash.isActive() and not self._fading:
            self._stop_end_flash()

    def set_fading(self, on: bool):
        """Blink the card ORANGE while a fade-out ramps the song down.

        🔉↓ and 🛑 work silently: the volume slides away over several seconds
        and nothing on the desk says it is happening. This is the same beat as
        the red end-of-track warning in the colour of a deliberate act — and it
        wins over the red while both are true, because the fade is the thing
        the operator just asked for."""
        on = bool(on)
        if on == self._fading:
            return
        self._fading = on
        if on:
            self._flash_on = False
            self._flash.start()
            self._flash_step()
        else:
            # Back to normal; the red end warning restarts itself on the next
            # position tick if the song is still running into its end.
            self._stop_end_flash()

    def _flash_step(self):
        self._flash_on = not self._flash_on
        skin = "fade" if self._fading else "end"
        self._set_skin(skin if self._flash_on else "")

    def _set_skin(self, skin: str):
        """Show the plain card (''), the red end warning ('end') or the orange
        fade ('fade'); re-polishes the card alone, not its children."""
        if self.property("flash") == skin:
            # Every halt lands here, inside the player's stop(). A re-polish
            # takes Qt's signal-slot locks while holding the GIL, and Qt's
            # FFmpeg thread, tearing the old title down, can hold one of them
            # while it waits for the GIL: the desk froze for good.
            return
        self.setProperty("flash", skin)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _stop_end_flash(self):
        self._flash.stop()
        self._flash_on = False
        self._fading = False
        self._set_skin("")
        if self._slider.styleSheet():   # seek bar back to blue (see _set_skin)
            self._slider.setStyleSheet("")
        self._wave.set_ending(False)

    # ── Controls ──

    def _on_slider_pressed(self):
        self._dragging = True

    def _on_slider_moved(self, value: int):
        self._update_time(value)

    def _on_slider_released(self):
        self._dragging = False
        self._player.setPosition(self._slider.value())

    def _on_wave_scrubbed(self, ms: int):
        """A drag on the 〰 strip is a drag on the seek bar: the handle and
        the times follow it, and playback ticks leave them alone."""
        self._dragging = True
        self._slider.blockSignals(True)
        self._slider.setValue(ms)
        self._slider.blockSignals(False)
        self._update_time(ms)

    def _on_wave_released(self, ms: int):
        self._dragging = False
        self._player.setPosition(ms)

    def _skip(self, delta_ms: int):
        dur = self._player.duration()
        pos = max(0, self._player.position() + delta_ms)
        if dur > 0:
            pos = min(pos, dur)
        self._player.setPosition(pos)

    def _toggle_pause(self):
        st = self._player.playbackState()
        if st == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        elif st == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()
        elif self.resume_cb and self.resume_cb():
            pass   # 🏁 round-end stop → started the next round's first song
        elif not self._player.source().isEmpty():
            # Stopped but a track is still loaded → (re)start it from 0:00.
            self._player.play()

    def toggle_play(self):
        """Public play/pause toggle (Space key) — same as clicking ⏯."""
        self._toggle_pause()

    def _seek_to_start(self):
        """Rewind the playhead to 0:00, leaving play/pause state untouched."""
        if not self._player.source().isEmpty():
            self._player.setPosition(0)
