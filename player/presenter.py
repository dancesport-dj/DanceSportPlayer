"""🖥 Presenter screen: the running dance with its title and the next three,
big enough to read from across the hall, on any monitor.

Laid out after the iPad app's "Now dancing" view — black, the dance name as the
hero, the title small and grey under it, a capsule progress bar with elapsed
and remaining time, and the up-next list as numbered rows.
"""
import logging
from datetime import datetime, timedelta

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from shared.icons import pixmap as icon_pixmap
from planner import i18n, terms
from player.presenter_theme import DEFAULT_KEY, logo_paths, theme_for
from player.sf_icons import (
    backward,
    forward,
    pause,
    pause_circle,
    play_circle,
    sliders,
    speaker,
    speaker_low,
    xmark_circle,
)

log = logging.getLogger("dancesport.gui.presenter")

# The clock is read off this poll, so the poll IS the clock's resolution: at
# 400 ms the displayed second changed 0.8 s after one boundary and 1.2 s after
# the next, which reads as a stopwatch running unevenly next to the player's
# own. 100 ms keeps the step within a tenth. The tick itself stays cheap —
# a refresh that changes nothing but the time skips the fitting pass.
_REFRESH_MS = 100
_NEXT_COUNT = 3
# How much of the running order stands on the screen at once: the line the
# evening is on, the one behind it and the next two. A programme on a wall is
# not read end to end — the hall looks up to see where it is and what comes
# next, and four lines it can read from the back are worth more than twelve it
# cannot. One line behind rather than two puts the evening near the top of the
# block, where the eye goes first.
_TT_PAST = 1
_TT_NEXT = 2
_TT_ROWS = _TT_PAST + 1 + _TT_NEXT
# A line of type stands this much taller than its pixel size (Segoe UI at 33 px
# fills 44). The running order divides the screen up in these before it knows
# what size it is setting, so it has to be a number rather than a measurement.
_LINE = 1.35
# The dance is the hero line; it may shrink to this fraction of its size to fit.
# Every other line keeps its size and scrolls instead.
_MIN_SCALE = 0.4
# …and everything together may step down to this fraction to stay inside a
# short screen. Below it the screen is too small for what it is asked to show.
_MIN_FIT = 0.6
# The colours live in player.presenter_theme now — the screen is built in the
# default theme and repainted by `set_theme`.
_BLINK_MS = 450
# How long one page takes to fade out, and the next one in.
_FADE_MS = 550
# The hero line the desk sends for the between-songs break. No emoji in it: it
# would be the one glyph on the screen coming out of somebody else's font, next
# to a foot row of hand-painted icons. The painted ⏸ that replaced it is off for
# now — the word alone is what the hall gets; flip _PAUSE_MARK to bring it back.
PAUSE_TEXT = "Pause"
_PAUSE_MARK = False
# The face the running order sets its times in: a column of times only lines up
# under itself in a mono one.
_MONO = ("Consolas", "monospace")
# The centre column, as a fraction of the window width (the iPad caps it too —
# a queue running the full width of a beamer is unreadable).
_COL_FRAC = 0.62


def _hall(text: str) -> str:
    """A label or tooltip of this screen in the hall's language: German when
    the German dance terms are kept, so the names it shows and the frame
    around them agree (planner.terms.hall_language)."""
    return i18n.translate(text, terms.hall_language())


def _baseline_pads(mono, text) -> tuple:
    """Top padding for two fonts so their first lines sit on one baseline.

    A label aligned to the top of its box draws its first line one ascent down,
    and two faces set to the same pixel size do not share an ascent: Consolas
    at 33 px rises 30, Segoe UI 36. Top-align both and the time stands six
    pixels above the line it belongs to — small, and impossible to un-see once
    noticed. Pad whichever of them starts higher by the difference."""
    d = QFontMetrics(mono).ascent() - QFontMetrics(text).ascent()
    return max(0, -d), max(0, d)


def _qcolor(spec: str) -> QColor:
    """A theme colour as a QColor, including the `rgba(r,g,b,a)` form QColor
    itself doesn't parse (it wants the alpha as a byte, CSS wants a fraction)."""
    s = str(spec).strip()
    if s.lower().startswith("rgba("):
        parts = [p.strip() for p in s[5:s.rindex(")")].split(",")]
        r, g, b = (int(float(p)) for p in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return QColor(r, g, b, int(round(a * 255)) if a <= 1 else int(a))
    return QColor(s)


class _ScrollLabel(QLabel):
    """A line that scrolls sideways when it is too long for the screen.

    Nothing is cut off and nothing shrinks: the whole title reaches the floor,
    it just takes a moment. Short lines are plain labels — the scroll timer
    only runs while something really doesn't fit."""

    _GAP = 120        # px of clear space before the text comes round again
    _STEP_MS = 30
    _STEP_PX = 2

    _ICON_GAP = 0.25   # air between an icon and its word, in icon widths

    def __init__(self, color: str, css: str = "", parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._css = css
        self._full = ""
        self._icon = None
        self._offset = 0
        self.setStyleSheet(f"color:{color};{css}")
        # Ignored: at these font sizes one album-length title would otherwise
        # widen the window right off the screen.
        self.setSizePolicy(QSizePolicy.Policy.Ignored,
                           QSizePolicy.Policy.Preferred)
        self._timer = QTimer(self)
        self._timer.setInterval(self._STEP_MS)
        self._timer.timeout.connect(self._advance)

    def full_text(self) -> str:
        return self._full

    def set_color(self, color: str):
        """Recolour the line (the last seconds of a title blink red)."""
        if QColor(color) != self._color:
            self.restyle(color)

    def restyle(self, color: str, css: str | None = None):
        """Colour and, on a theme change, the rest of the line's CSS too."""
        if css is not None:
            self._css = css
        self._color = QColor(color)
        self.setStyleSheet(f"color:{color};{self._css}")
        self.update()

    def set_full_text(self, text: str):
        if text != self._full:
            self._full = text
            self._offset = 0
            # Every line this label carries is data — the song, the artist, the
            # dance, the one played before. `QLabel.setText` is translated on
            # its way into Qt, and a track really called "Time" would come out
            # as "Zeit" on the screen the hall is reading.
            with i18n.verbatim():
                super().setText(text)
        self.sync_scroll()

    def set_icon(self, pixmap):
        """A glyph in front of the word, on the same line (the break's ⏸).
        `None` takes it away again. Beside the text, not over it: stacked, the
        two together are a head taller than the hero line is meant to be."""
        if pixmap is self._icon:
            return
        self._icon = pixmap
        self.sync_scroll()   # …which repaints

    def icon_width(self) -> int:
        """What the icon costs the text — itself plus the air behind it."""
        if self._icon is None:
            return 0
        dpr = self._icon.devicePixelRatio() or 1.0
        w = self._icon.width() / dpr
        return int(w * (1 + self._ICON_GAP))

    def text_width(self) -> int:
        return (QFontMetrics(self.font()).horizontalAdvance(self._full)
                + self.icon_width())

    def sync_scroll(self):
        """Start / stop the scroll for the current text, font and width."""
        if self.text_width() > self.width():
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self._offset = 0
        self.update()

    def _advance(self):
        self._offset = (self._offset + self._STEP_PX) % max(
            1, self.text_width() + self._GAP)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_scroll()

    def _draw_run(self, p: QPainter, x: int, span: int):
        """One pass of icon + text, with its left edge at x."""
        if self._icon is not None:
            dpr = self._icon.devicePixelRatio() or 1.0
            h = self._icon.height() / dpr
            p.drawPixmap(int(x), int((self.height() - h) / 2), self._icon)
        p.drawText(x + self.icon_width(), 0, span, self.height(),
                   int(Qt.AlignmentFlag.AlignVCenter
                       | Qt.AlignmentFlag.AlignLeft), self._full)

    def paintEvent(self, event):
        if self._icon is None and not self._timer.isActive():
            super().paintEvent(event)   # fits — plain label, honours alignment
            return
        span = self.text_width() + self._GAP
        p = QPainter(self)
        p.setFont(self.font())
        p.setPen(self._color)
        if self._timer.isActive():
            for x in (-self._offset, -self._offset + span):
                self._draw_run(p, x, span)
            return
        # Icon and word are centred as one block — the icon is part of the
        # line, so the pair sits where the word alone would have.
        self._draw_run(p, int((self.width() - self.text_width()) / 2), span)


class _ProgressBar(QWidget):
    """How far the title has run, as the iPad app's capsule: a dim track with
    a white fill. Read-only — this screen presents, it doesn't scrub."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frac = 0.0
        self._track = QColor(255, 255, 255, 51)     # white @ 20 %
        self._fill = QColor("#ffffff")
        self.setFixedHeight(8)

    def set_colors(self, track: str, fill: str):
        self._track = _qcolor(track)
        self._fill = QColor(fill)
        self.update()

    def set_fraction(self, frac: float):
        frac = max(0.0, min(1.0, float(frac)))
        if abs(frac - self._frac) > 0.001:
            self._frac = frac
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        r = self.height() / 2
        p.setBrush(self._track)
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), r, r)
        if self._frac > 0:
            p.setBrush(self._fill)
            p.drawRoundedRect(
                QRectF(0, 0, self.width() * self._frac, self.height()), r, r)


class _TimetableView(QWidget):
    """🕒 The evening's running order as the presenter's second page.

    One row per entry: the time in the mono face on the left, what happens next
    to it, an optional note under that. The row the evening is standing on is
    the accent colour, everything before it is spent and greyed — the same
    reading the up-next column already uses, so the two pages answer "where are
    we" in one language.

    It builds its rows when it is handed a timetable and sizes them off the
    window height: a programme of twelve lines has to fit the same screen a
    programme of four does."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._table = None
        self._theme = theme_for(DEFAULT_KEY)
        # Which rows were last drawn as (stood on, happening) — -2 = never
        # drawn. Two numbers because the accent can go out while the evening
        # keeps standing where it stands.
        self._cur = -2
        # How far the page's reading of the clock is moved from the machine's.
        # Zero on a normal evening; see `set_now_offset`.
        self._offset = timedelta()
        self._rows = []     # (row widget, time lbl, what lbl, note lbl or None)
        self._entry_at = []  # for each of them, its place in table.entries

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(0)
        # No stretch above the mark: the page stands at the top of the screen
        # and the air is left under it, where the lines are. Centred, the
        # heading came down into the middle of the screen and took the rows
        # with it.
        # 💍 The theme's mark, crowning the heading. Two labels rather than one
        # composed image: the rings and the lettering are separate files and
        # want different heights, the way the print pieces set them.
        self._logo_lbls = []
        for _ in range(2):
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setVisible(False)
            lyt.addWidget(lbl)
            self._logo_lbls.append(lbl)
        self._logo_src = []     # the QPixmaps at full size, scaled per repaint
        self.title_lbl = QLabel("")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lyt.addWidget(self.title_lbl)
        lyt.addSpacing(10)
        self._col = QWidget()
        self._col_lyt = QVBoxLayout(self._col)
        self._col_lyt.setContentsMargins(0, 0, 0, 0)
        self._col_lyt.setSpacing(0)
        # …and under the rows, the sign that the evening goes on below them.
        # Four lines out of twelve look like the whole programme otherwise, and
        # a guest reading "Mitternachtssnack" as the last thing of the night is
        # reading the window, not the evening. Shaped like a row so it stands
        # under the same column: an empty time cell, then the mark.
        self._more = QWidget()
        ml = QHBoxLayout(self._more)
        ml.setContentsMargins(0, 6, 0, 6)
        ml.setSpacing(18)
        self._more_pad = QLabel("")
        self._more_lbl = QLabel("…")
        ml.addWidget(self._more_pad)
        ml.addWidget(self._more_lbl, 1)
        self._col_lyt.addWidget(self._more)
        centred = QHBoxLayout()
        centred.addStretch(1)
        centred.addWidget(self._col)
        centred.addStretch(1)
        lyt.addLayout(centred)
        lyt.addStretch(1)

    def set_timetable(self, table):
        """Take a new programme and rebuild the rows for it."""
        self._table = table
        # The programme's own name, typed by whoever built it — data, not chrome.
        with i18n.verbatim():
            self.title_lbl.setText(table.title if table is not None else "")
        for row, *_ in self._rows:
            row.setParent(None)
        self._rows, self._entry_at = [], []
        for i, entry in enumerate(table.entries if table is not None else []):
            if not (entry.time.strip() or entry.what.strip()):
                continue        # a blank line typed and left behind
            self._rows.append(self._build_row(entry))
            self._entry_at.append(i)
        # Last in the column again, whatever was added above it.
        self._col_lyt.removeWidget(self._more)
        self._col_lyt.addWidget(self._more)
        self._cur = -2
        self.apply_theme(self._theme)

    def _build_row(self, entry):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 6, 0, 6)
        rl.setSpacing(18)
        time_lbl = QLabel(entry.time)
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        what_lbl = QLabel(entry.what)
        what_lbl.setSizePolicy(QSizePolicy.Policy.Ignored,
                               QSizePolicy.Policy.Preferred)
        col.addWidget(what_lbl)
        note_lbl = None
        if entry.note.strip():
            note_lbl = QLabel(entry.note)
            note_lbl.setSizePolicy(QSizePolicy.Policy.Ignored,
                                   QSizePolicy.Policy.Preferred)
            col.addWidget(note_lbl)
        rl.addWidget(time_lbl)
        rl.addLayout(col, 1)
        self._col_lyt.addWidget(row)
        return (row, time_lbl, what_lbl, note_lbl)

    def row_count(self) -> int:
        return len(self._rows)

    def set_column_width(self, width: int):
        """The same centred column the up-next list stands in, so the two pages
        line up rather than jumping sideways under the fade."""
        self._col.setFixedWidth(width)

    def apply_theme(self, theme):
        self._theme = theme
        # The heading is the page's own name, not a caption under something —
        # so it takes the theme's strong text colour, the same one the rows
        # still to come are set in, rather than the grey of a subtitle.
        self.title_lbl.setStyleSheet(f"color:{theme.hero};font-weight:600;")
        self._load_logo(theme)
        self._more_lbl.setStyleSheet(f"color:{theme.sub};")
        self._cur = -2    # every row's colour is the theme's — redraw all
        self.sync_now()

    def _load_logo(self, theme):
        """Read the theme's marks once, at full size. They are re-scaled on
        every font pass, and scaling down from the original each time is what
        keeps the thin gold rings from going to mush."""
        self._logo_src = []
        for path in logo_paths(theme):
            pix = QPixmap(str(path))
            if not pix.isNull():
                self._logo_src.append(pix)
        for i, lbl in enumerate(self._logo_lbls):
            if i >= len(self._logo_src):
                lbl.clear()
                lbl.setVisible(False)

    def _window_start(self, cur: int) -> int:
        """The first of the rows the screen shows.

        Anchored one line behind the evening, and pulled back off the end so
        the block stays full: the last line of a programme standing alone under
        the heading reads as a screen that has lost its content."""
        return max(0, min(cur - _TT_PAST, len(self._rows) - _TT_ROWS))

    def set_now_offset(self, offset):
        """Run the page on a clock of its own, `offset` away from the machine's.

        An evening that started late is the reason: told "it is only 20:00" at
        20:45, the page carries that three-quarter hour for the rest of the
        night rather than standing still on one minute. None puts it back on
        the machine's clock."""
        self._offset = offset or timedelta()
        self._cur = -2     # the clock moved under it — redraw
        self.sync_now()

    def sync_now(self, now=None):
        """Recolour for the wall clock and move the window with it: the row the
        evening stands on, the one behind it spent, the next two still to come,
        and the rest of the programme off the screen under a "…". Cheap and
        idempotent — nothing is touched while the clock says the same thing.

        One row carries the accent and it is the row that has begun and not
        ended — it holds the window, and it keeps the gold until something
        else takes it. Which rows are behind it is a second answer, not the
        same one: an opening dance written under the party it happens inside
        is over while the party runs on, so it is drawn spent even though it
        stands below the line with the accent."""
        # The offset moves the reading, not the source: a time handed in is
        # shifted the same way the machine's clock is, so the page answers on
        # one clock however it was asked.
        now = (now or datetime.now()) + self._offset
        if self._table is not None:
            cur, spent = self._table.state(now)
        else:
            cur, spent = -1, set()
        key = (cur, tuple(sorted(spent)))
        if key == self._cur:
            return
        self._cur = key
        # The clock answers in entries, the screen holds rows, and the rows
        # skip whatever was typed and cleared again — so the answers are
        # carried across before they colour anything.
        cur = self._entry_at.index(cur) if cur in self._entry_at else -1
        spent = {self._entry_at.index(i) for i in spent if i in self._entry_at}
        first = self._window_start(cur)
        self._more.setVisible(first + _TT_ROWS < len(self._rows))
        t = self._theme
        for i, (row, time_lbl, what_lbl, note_lbl) in enumerate(self._rows):
            row.setVisible(first <= i < first + _TT_ROWS)
            if i == cur:
                col, weight = t.up, "700"
            elif i in spent:
                col, weight = t.past, "400"
            else:
                col, weight = t.hero, "400"
            time_lbl.setStyleSheet(f"color:{t.up if i == cur else t.sub};")
            what_lbl.setStyleSheet(f"color:{col};font-weight:{weight};")
            if note_lbl is not None:
                note_lbl.setStyleSheet(
                    f"color:{t.past if i in spent else t.sub};")

    def apply_fonts(self, h: int, scale: float):
        """Size the page off the window height — and off how many rows there
        are: twelve lines have to stand on the same screen four do, so the rows
        give up size before the column gives up a line."""
        title_px = max(9, int(h * 0.075 * scale))
        logo_h = self._scale_logo(h, scale)
        top = max(6, int(h * 0.035 * scale))
        self.layout().setContentsMargins(0, top, 0, 0)
        # Off what the screen shows, not off what was typed: the window holds
        # five lines however long the programme is, so the tenth entry no longer
        # costs the first five their size.
        n = max(1, min(len(self._rows), _TT_ROWS))
        # What those rows weigh, in units of the type size being looked for: a
        # line each, plus 0.62 of a line again under every one that carries a
        # note. Sizing off that rather than off a fraction guessed for the
        # average row is what lets the type fill the screen — five lines of
        # which two carry a note leave room for a good deal more than five
        # that do not.
        #
        # Counted over the whole programme rather than over the five on the
        # screen, and capped at five: the window moves through the evening, and
        # a size that depended on which notes it happened to be standing over
        # would change under the hall for no reason it could see.
        notes = min(n, sum(1 for r in self._rows if r[3] is not None))
        # The "…" costs a line of its own whenever the programme is longer than
        # the window. Counted off the programme rather than off whether it is
        # showing this minute, for the same reason the notes are: the size must
        # not change under the hall as the window moves.
        more = 1 if len(self._rows) > _TT_ROWS else 0
        weight = (n + more) * _LINE + notes * _LINE * 0.62
        pad = (n + more) * 12   # the 6 px above and below each row
        # What the page has left after the mark, the heading and their air.
        # 0.88 of the window rather than all of it: the foot row and the bar
        # take the rest, and the model above is an estimate — measured, a
        # programme whose every line carries a note lands ten pixels inside
        # the page at 1280×720 and one at 1920×1080. Anything over and the
        # last line of the evening is cut off at the bottom of the screen.
        room = max(1, int(h * 0.88 * scale)
                   - top - int(title_px * _LINE) - 10 - logo_h - pad)
        row_px = max(9, min(int(h * 0.075 * scale), int(room / weight)))
        f = self.title_lbl.font()
        f.setPixelSize(title_px)
        f.setFamilies(list(self._theme.hero_families) or [self.font().family()])
        self.title_lbl.setFont(f)
        for _row, time_lbl, what_lbl, note_lbl in self._rows:
            for lbl, px in ((time_lbl, row_px), (what_lbl, row_px),
                            (note_lbl, max(9, int(row_px * 0.62)))):
                if lbl is None:
                    continue
                lf = lbl.font()
                lf.setPixelSize(px)
                # The time's own face, carried on the font rather than left to
                # the stylesheet: the baseline below is measured off this font,
                # and a family that only arrives with the polish is not in it
                # yet when it is measured.
                if lbl is time_lbl:
                    lf.setFamilies(list(_MONO))
                lbl.setFont(lf)
            # …and the two of them on one line, which the mono face otherwise
            # breaks by rising less far than the one beside it.
            t_pad, w_pad = _baseline_pads(time_lbl.font(), what_lbl.font())
            time_lbl.setContentsMargins(0, t_pad, 0, 0)
            what_lbl.setContentsMargins(0, w_pad, 0, 0)
        # One width for every time, so the column is a column — but taken from
        # the widest one actually typed, not from "HH:MM": "ca. 02 Uhr" is a
        # time somebody really writes, and it may not come out as ". 02 Uhr".
        mf = self._more_lbl.font()
        mf.setPixelSize(row_px)
        self._more_lbl.setFont(mf)
        wide = max((lbl.sizeHint().width() for _r, lbl, *_ in self._rows),
                   default=0)
        wide = max(wide, int(row_px * 4.2))
        for _row, time_lbl, *_ in self._rows:
            time_lbl.setFixedWidth(wide)
        # The mark stands where the names do, not where the times do.
        self._more_pad.setFixedWidth(wide)

    def _scale_logo(self, h: int, scale: float) -> int:
        """Fit the theme's marks to the window and say how much height they
        took, so the rows can be sized off what is left. The rings get more room
        than the lettering — they are the taller shape, and a name set as big as
        the rings stops being a mark and becomes a second heading."""
        total = 0
        for i, lbl in enumerate(self._logo_lbls):
            if i >= len(self._logo_src):
                continue
            src = self._logo_src[i]
            want = max(12, int(h * (0.14 if i == 0 else 0.055) * scale))
            # Scale at the device ratio and tell Qt about it, or the thin gold
            # ring lands on a low-res pixmap and stipples on a HiDPI screen.
            dpr = self.devicePixelRatioF() or 1.0
            pix = src.scaledToHeight(int(want * dpr),
                                     Qt.TransformationMode.SmoothTransformation)
            pix.setDevicePixelRatio(dpr)
            lbl.setPixmap(pix)
            lbl.setVisible(True)
            # Air under the last mark, so rings-over-lettering read as one
            # block and the heading below as the next. Without it all three
            # sit at the same distance and the mark stops being a mark.
            gap = int(want * 0.35) if i == len(self._logo_src) - 1 else 0
            lbl.setContentsMargins(0, 0, 0, gap)
            total += want + gap
        return total


def screen_labels() -> list:
    """'1 · 1920×1080 (primary)' per connected monitor, in screen order."""
    primary = QGuiApplication.primaryScreen()
    out = []
    for i, s in enumerate(QGuiApplication.screens(), 1):
        g = s.geometry()
        out.append(f"{i} · {g.width()}×{g.height()}"
                   + ("  (primary)" if s is primary else ""))
    return out


def screen_choices() -> list:
    """(label, name) per connected monitor. The name is what a pick is kept
    by: the list's order changes when a beamer comes and goes."""
    return list(zip(screen_labels(),
                    (s.name() for s in QGuiApplication.screens())))


class PresenterWindow(QWidget):
    """Audience-facing display, driven by a state callback.

    `state_cb()` returns (dance, title, (played, left, ending, fraction),
    [(dance, title), …], (dance, title)) — what plays now, how far it is in,
    what is queued behind it and what was played before it. Polled rather than pushed: this is a pure display, and the
    playback state it mirrors changes from a dozen places."""

    closed = Signal()
    controlsToggled = Signal(bool)   # 🎛 transport shown / hidden (persisted)
    lastToggled = Signal(bool)       # 🕘 last-played line shown / hidden
    timetableRequested = Signal()    # 🕒 open the timetable editor
    prevRequested = Signal()         # ⏮ previous title
    playPauseRequested = Signal()    # ⏯ play / pause
    nextRequested = Signal()         # ⏭ next title
    breakRequested = Signal()        # ☕ over to the break music
    duckToggled = Signal(bool)       # 🔉 pull everything down to _DESK_DUCK

    def __init__(self, state_cb, parent=None):
        # An own top-level window, but owned by the main window: it then closes
        # with the app instead of keeping it alive on a second monitor.
        super().__init__(parent, Qt.WindowType.Window)
        self._state_cb = state_cb
        self._last_state = None
        self._font_h = None   # what the fonts were last sized for
        self._last_shown = False   # …is the 🕘 block really on the screen?
        self._rows_shown = 0       # …and how many queue rows stand under it
        self._base_px = {}   # label → its font size for the current height
        # Set by MainWindow: whether the music is running, for the ⏯ glyph.
        self.playing_cb = None
        self._controls_on = False
        self._last_on = False
        self._has_upcoming = False
        self._upcoming = []        # the queue as last handed over
        self._play_shown = None   # the state the ⏯ icon currently shows
        self._ducked = False
        self._btn_px = 24
        self._pause_mark = None   # the ⏸ of the break, at the current size
        self._timetable = None    # 🕒 the evening's running order, once handed over
        self._fade_target = None  # the page a running fade is on its way to
        self._anim = None
        # The palette everything below is built in. Two registries record which
        # theme colour each widget wears, so a theme change repaints them all
        # from one place instead of restating the mapping a second time.
        self._theme = theme_for(DEFAULT_KEY)
        # What the hero line falls back to when a theme names no face of its own.
        self._base_family = self.font().family()
        self._styled = []   # (_ScrollLabel, theme field, css)
        self._plain = []    # (widget, theme field, css template with {c})
        self.setWindowTitle("🖥  Presenter — DancePlaylist")
        # An explicit minimum, small: without one the window inherits the
        # layout's, and a block switched on could then force it wider than the
        # monitor it is shown on. The sizing pass below keeps the content
        # inside instead.
        self.setMinimumSize(320, 240)
        self.setStyleSheet(f"background:{self._theme.bg};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 36, 48, 26)
        outer.setSpacing(10)
        # 🎵 ⇄ 🕒 Two pages under one foot row: what is playing, and the
        # evening's running order. Stacked rather than swapped in and out, so
        # the fade between them has both of them to fade.
        self.stack = QStackedWidget()
        self.music_page = QWidget()
        self.time_page = _TimetableView()
        # The running order does not get a vote on the fitting pass. A stack is
        # as tall as its tallest page, so without this the programme's own
        # height would size the music page's fonts — and the running order has
        # no minimum worth defending: it sets itself to whatever height it is
        # given, which is exactly the height the music page needs.
        self.time_page.setSizePolicy(QSizePolicy.Policy.Preferred,
                                     QSizePolicy.Policy.Ignored)
        self.stack.addWidget(self.music_page)
        self.stack.addWidget(self.time_page)
        outer.addWidget(self.stack, 1)

        lyt = QVBoxLayout(self.music_page)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(10)
        lyt.addStretch(1)

        # ── The running dance, big, with its title under it ──────────────────
        self.dance_lbl = self._line("hero", "font-weight:800;")
        self.dance_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl = self._line("sub")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lyt.addWidget(self.dance_lbl)
        lyt.addWidget(self.title_lbl)

        # ── Progress: bar, elapsed left, remaining right ─────────────────────
        self.bar = _ProgressBar()
        lyt.addSpacing(6)
        lyt.addWidget(self.bar)
        time_row = QHBoxLayout()
        self.played_lbl = self._line("sub", "font-family:Consolas,monospace;")
        self.left_lbl = self._line("left", "font-family:Consolas,monospace;")
        self.left_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        time_row.addWidget(self.played_lbl, 1)
        time_row.addWidget(self.left_lbl, 1)
        lyt.addLayout(time_row)

        lyt.addStretch(1)

        # ── Up next, as numbered rows in a centred column ────────────────────
        self.next_box = QWidget()
        box = QVBoxLayout(self.next_box)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        # ── 🕘 What was played before this, at the head of the same column ──
        # Same width, same indent, the same two lines as a queue row — only
        # greyer, and with no number: it is not step 0 of the running order,
        # it is what the running order has already spent.
        self.last_wrap = QWidget()
        lb = QVBoxLayout(self.last_wrap)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.setSpacing(0)
        self.last_hdr = QLabel(_hall("Last"))
        self._tint(self.last_hdr, "sub", "color:{c};font-weight:600;")
        lb.addWidget(self.last_hdr)
        lb.addSpacing(6)
        last_row = QWidget()
        lrl = QHBoxLayout(last_row)
        lrl.setContentsMargins(0, 7, 0, 7)
        lrl.setSpacing(14)
        self.last_num = QLabel("")     # blank, but as wide as the queue's "1"
        lcol = QVBoxLayout()
        lcol.setContentsMargins(0, 0, 0, 0)
        lcol.setSpacing(0)
        self.last_lbl = self._line("sub", "font-weight:700;")
        self.last_sub_lbl = self._line("past")
        lcol.addWidget(self.last_lbl)
        lcol.addWidget(self.last_sub_lbl)
        lrl.addWidget(self.last_num)
        lrl.addLayout(lcol, 1)
        lb.addWidget(last_row)
        lb.addSpacing(18)
        self.last_wrap.setVisible(False)
        box.addWidget(self.last_wrap)

        self.next_hdr = QLabel(_hall("Next dances"))
        self._tint(self.next_hdr, "sub", "color:{c};font-weight:600;")
        box.addWidget(self.next_hdr)
        box.addSpacing(6)

        self.next_lbls = []        # the dance of each queued title
        self.next_sub_lbls = []    # …and the title itself, small and grey
        self.next_num_lbls = []
        self._next_rows = []       # (row widget, divider above it or None)
        for i in range(_NEXT_COUNT):
            div = None
            if i:
                div = QFrame()
                div.setFrameShape(QFrame.Shape.HLine)
                div.setFixedHeight(1)
                self._tint(div, "div", "background:{c};border:none;")
                box.addWidget(div)
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 7, 0, 7)
            rl.setSpacing(14)
            num = QLabel(str(i + 1))
            self._tint(num, "sub", "color:{c};font-family:Consolas,monospace;")
            num.setAlignment(Qt.AlignmentFlag.AlignRight
                             | Qt.AlignmentFlag.AlignVCenter)
            col = QVBoxLayout()
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(0)
            # The one coming up next is the orange one — the same accent the
            # iPad app puts on the head of its queue.
            dance = self._line("up" if i == 0 else "hero",
                               "font-weight:700;" if i == 0 else "")
            sub = self._line("sub")
            col.addWidget(dance)
            col.addWidget(sub)
            rl.addWidget(num)
            rl.addLayout(col, 1)
            box.addWidget(row)
            self.next_lbls.append(dance)
            self.next_sub_lbls.append(sub)
            self.next_num_lbls.append(num)
            self._next_rows.append((row, div))
        centred = QHBoxLayout()
        centred.addStretch(1)
        centred.addWidget(self.next_box)
        centred.addStretch(1)
        lyt.addLayout(centred)

        self._lines = (self.dance_lbl, self.title_lbl, self.played_lbl,
                       self.left_lbl, self.last_lbl, self.last_sub_lbl,
                       *self.next_lbls, *self.next_sub_lbls)

        # ── Foot: the controls switch, what the keys do, and the dismiss ─────
        # Three equal columns rather than stretches: the transport belongs in
        # the middle of the *screen*, and the hint on the left is wider than
        # the ✕ on the right.
        foot = QGridLayout()
        foot.setContentsMargins(0, 0, 0, 0)
        self.ctl_btn = self._foot_btn("Show the transport on this screen")
        self.ctl_btn.clicked.connect(self._toggle_controls)
        self.last_btn = self._foot_btn("Show the title played before this one")
        self.last_btn.clicked.connect(self._toggle_last)
        # 🕒 …and the page with the evening's running order on it. Hidden while
        # no timetable has been typed — a button onto an empty screen is worse
        # than no button.
        self.time_btn = self._foot_btn(
            "Show the timetable  ·  T\n"
            "Right-click to edit it")
        self.time_btn.clicked.connect(self._toggle_timetable)
        self.time_btn.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.time_btn.customContextMenuRequested.connect(
            lambda _p: self.timetableRequested.emit())
        self.time_btn.setVisible(False)
        self.hint_lbl = QLabel(
            _hall("Esc closes  ·  double-click leaves full screen"))
        self._tint(self.hint_lbl, "div", "color:{c};")
        self.hint_lbl.setSizePolicy(QSizePolicy.Policy.Ignored,
                                    QSizePolicy.Policy.Preferred)
        self.close_btn = self._foot_btn("Close the presenter screen")
        self.close_btn.clicked.connect(self.close)
        hint_row = QHBoxLayout()
        hint_row.addWidget(self.ctl_btn)
        hint_row.addWidget(self.last_btn)
        hint_row.addWidget(self.time_btn)
        hint_row.addWidget(self.hint_lbl, 1)
        foot.addLayout(hint_row, 0, 0)
        foot.addWidget(self._build_controls(), 0, 1,
                       Qt.AlignmentFlag.AlignHCenter)
        foot.addWidget(self.close_btn, 0, 2, Qt.AlignmentFlag.AlignRight)
        for col in range(3):
            foot.setColumnStretch(col, 1)
        outer.addSpacing(10)
        outer.addLayout(foot)

        self._scale_fonts()   # base sizes for a first _refresh before any resize

        self._blink_on = False
        self._blink = QTimer(self)
        self._blink.setInterval(_BLINK_MS)
        self._blink.timeout.connect(self._blink_left)

        # 🕒 ⇄ 🎵 The optional rotation between the two pages.
        self._rotate = QTimer(self)
        self._rotate.timeout.connect(self._rotate_view)

        self._timer = QTimer(self)
        self._timer.setInterval(_REFRESH_MS)
        self._timer.timeout.connect(self._refresh)

    def _line(self, field: str, css: str = "") -> _ScrollLabel:
        """A scrolling line wearing the theme colour `field`, registered so a
        theme change finds it again."""
        lbl = _ScrollLabel(getattr(self._theme, field), css)
        self._styled.append((lbl, field, css))
        return lbl

    def _tint(self, widget, field: str, css: str):
        """Same for a plain widget: `css` is a template with one `{c}` in it."""
        widget.setStyleSheet(css.format(c=getattr(self._theme, field)))
        self._plain.append((widget, field, css))
        return widget

    def _foot_btn(self, tip: str) -> QToolButton:
        """A chrome-less icon button for the foot row."""
        b = QToolButton()
        b.setToolTip(_hall(tip))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet("QToolButton{background:transparent;border:none;}")
        return b

    def _build_controls(self) -> QWidget:
        """The minimal transport, for halls where the machine driving the
        presenter screen is also the console. Off by default: a presentation
        screen has no buttons on it."""
        self.ctl_box = QWidget()
        row = QHBoxLayout(self.ctl_box)
        row.setContentsMargins(0, 0, 0, 0)
        # The duck sits left of the transport: the one control needed WHILE a
        # title runs (someone has to be heard over the music).
        self.duck_btn = self._foot_btn("Duck to 20 % / back to full")
        self.duck_btn.setCheckable(True)   # stays pressed while ducked
        self.duck_btn.clicked.connect(self._toggle_duck)
        self.prev_btn = self._foot_btn("Previous title")
        self.prev_btn.clicked.connect(self.prevRequested)
        self.play_btn = self._foot_btn("Play / pause")
        self.play_btn.clicked.connect(self.playPauseRequested)
        self.next_btn = self._foot_btn("Next title")
        self.next_btn.clicked.connect(self.nextRequested)
        self.break_btn = self._foot_btn("Over to the break music")
        self.break_btn.clicked.connect(self.breakRequested)
        for b in (self.duck_btn, self.prev_btn, self.play_btn, self.next_btn,
                  self.break_btn):
            row.addWidget(b)
        self.ctl_box.setVisible(False)
        return self.ctl_box

    # ── 🕒 The timetable page ────────────────────────────────────────────────
    def set_timetable(self, table):
        """Hand the screen the evening's running order — also how the saved one
        is restored when it opens. An empty programme takes the 🕒 button away
        again and stops any rotation: there is nothing to fade to."""
        self._timetable = table
        self.time_page.set_timetable(table)
        empty = table is None or table.is_empty()
        self.time_btn.setVisible(not empty)
        if empty and self.stack.currentWidget() is self.time_page:
            self.show_timetable(False)
        self._font_h = None
        self._scale_fonts()
        self._sync_rotation()
        self._paint_buttons()

    def set_now_offset(self, offset):
        """Run the running order on a clock `offset` away from the machine's —
        what the timetable dialog sets when the evening is behind."""
        self.time_page.set_now_offset(offset)

    def timetable_shown(self) -> bool:
        return self.stack.currentWidget() is self.time_page

    def _timetable_wanted(self) -> bool:
        """The page the screen is on — or the one it is on its way to.

        The swap happens when the fade *finishes*, so for half a second
        `timetable_shown()` still answers for the page being left. Anything
        that shows which page you are looking at has to ask this instead, or
        it lights up for the page you just left."""
        if self._fade_target is not None:
            return self._fade_target is self.time_page
        return self.timetable_shown()

    def show_timetable(self, on: bool, fade: bool = True):
        """Switch the page. Nothing to switch to while the programme is empty."""
        on = bool(on) and not (self._timetable is None
                               or self._timetable.is_empty())
        if on == self._timetable_wanted():
            return
        self._fade_to(self.time_page if on else self.music_page, fade)
        self._sync_controls()
        self._paint_buttons()

    def _toggle_timetable(self):
        """The 🕒 button and the T key. A hand on the screen also re-starts the
        rotation clock: whoever just picked a page means to look at it, not to
        have it fade out half a second later."""
        self.show_timetable(not self._timetable_wanted())
        self._sync_rotation()

    def _fade_to(self, page, fade: bool = True):
        """Cross to `page` — out, switch, in. Sequential rather than a true
        cross-fade: one opacity effect at a time, so the two pages never share
        the screen half-transparent on top of each other.

        Asked again while the old page is still fading out: for that same page
        it is already on its way; for the page being left, the fade turns round
        and brings it back from wherever it had got to."""
        current = self.stack.currentWidget()
        if self._fade_target is not None:
            if page is not current:
                self._fade_target = page
                return
            self._fade_target = None
            self._anim.stop()          # its end would still swap the pages
            if not fade or not self.isVisible():
                current.setGraphicsEffect(None)
                return
            self._run_fade(current, self._opacity(current), 1.0, None)
            return
        if page is current:
            return
        if not fade or not self.isVisible():
            self.stack.setCurrentWidget(page)
            return
        self._fade_target = page
        self._run_fade(current, self._opacity(current), 0.0, self._fade_in)

    @staticmethod
    def _opacity(page) -> float:
        """How far a page is faded in: a fade cut short leaves it part way."""
        effect = page.graphicsEffect()
        return effect.opacity() if effect is not None else 1.0

    def _fade_in(self):
        page, self._fade_target = self._fade_target, None
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self._run_fade(page, 0.0, 1.0, None)

    def _run_fade(self, page, start: float, end: float, done):
        if self._anim is not None:
            self._anim.stop()   # a fade-in still running: this one takes over
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(_FADE_MS)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        def _finish():
            # Drop the effect again: a widget kept behind one repaints through
            # an offscreen pixmap for the rest of its life, and the scrolling
            # title lines redraw ten times a second.
            page.setGraphicsEffect(None)
            if done is not None:
                done()

        anim.finished.connect(_finish)
        self._anim = anim       # a QPropertyAnimation that isn't held is collected
        anim.start()

    def _sync_rotation(self):
        """Run (or stop) the timer that fades between the two pages."""
        t = self._timetable
        on = bool(t is not None and t.rotate and not t.is_empty())
        if on:
            self._rotate.setInterval(max(1, int(t.rotate_secs)) * 1000)
            self._rotate.start()
        else:
            self._rotate.stop()

    def _rotate_view(self):
        self.show_timetable(not self._timetable_wanted())
        self._paint_buttons()

    def set_theme(self, key: str):
        """Wear the named palette — also how the saved setting is restored when
        the screen opens. An unknown name falls back to the default one."""
        theme = theme_for(key)
        if theme is self._theme:
            return
        self._theme = theme
        self._apply_theme()

    def theme_key(self) -> str:
        return self._theme.key

    def _apply_theme(self):
        """Repaint every registered widget in the current theme, then re-size:
        the hero font family is the theme's too, so the fitting pass has to run
        again on a switch between a serif and the system font."""
        t = self._theme
        self.setStyleSheet(f"background:{t.bg};")
        for lbl, field, css in self._styled:
            lbl.restyle(getattr(t, field), css)
        for widget, field, css in self._plain:
            widget.setStyleSheet(css.format(c=getattr(t, field)))
        self.time_page.apply_theme(t)
        self.bar.set_colors(t.track, t.fill)
        self._font_h = None       # …so _scale_fonts really runs
        self._scale_fonts()       # which repaints the foot icons as well
        self._fit()

    def set_controls_shown(self, on: bool):
        """Show or hide the transport — also how the saved setting is restored
        when the screen opens."""
        self._controls_on = bool(on)
        self._sync_controls()
        self._paint_buttons()

    def _sync_controls(self):
        """The transport belongs to the music page.

        Under a printed running order a row of play buttons is the one thing
        that stops the screen looking like a programme, so the running order
        gets the foot to itself. The setting is not touched — the transport
        comes back with the music."""
        self.ctl_box.setVisible(self._controls_on
                                and not self._timetable_wanted())

    def set_last_played_shown(self, on: bool):
        """Show or hide the 🕘 last-played block — also how the saved setting is
        restored when the screen opens."""
        self._last_on = bool(on)
        self._sync_last()
        self._fit()
        self._paint_buttons()

    def _sync_last(self):
        """The 🕘 block shows when it is switched on and has something to name —
        and it opens the column by itself, so the last dance of an evening is
        still readable with nothing queued behind it.

        It takes the last queue row's place rather than standing on top of it:
        the column then holds the same number of rows either way, and the whole
        screen keeps the height — and with it the font sizes — it had before
        the history was switched on."""
        shown = self._last_on and bool(self.last_lbl.full_text()
                                       or self.last_sub_lbl.full_text())
        self.last_wrap.setVisible(shown)
        room = len(self._next_rows) - (1 if shown else 0)
        self._rows_shown = min(len(self._upcoming), room)
        for i, (row, div) in enumerate(self._next_rows):
            on = i < self._rows_shown
            row.setVisible(on)
            if div is not None:
                div.setVisible(on)
        self._has_upcoming = self._rows_shown > 0
        self.next_hdr.setVisible(self._has_upcoming)
        self.next_box.setVisible(shown or self._has_upcoming)
        self._last_shown = shown
        self._scale_fonts()   # one block traded for another, or one less

    def _toggle_last(self):
        self.set_last_played_shown(not self._last_on)
        self.lastToggled.emit(self._last_on)

    def _toggle_controls(self):
        self.set_controls_shown(not self._controls_on)
        self.controlsToggled.emit(self._controls_on)

    def _toggle_duck(self):
        """Ask for the duck; the answer comes back through `set_ducked`, so the
        button follows the desk even when it was ducked from the player card."""
        self.duck_btn.setChecked(self._ducked)
        self.duckToggled.emit(not self._ducked)

    def set_ducked(self, on: bool):
        """The desk's duck state, mirrored onto this screen's button."""
        self._ducked = bool(on)
        self.duck_btn.setChecked(self._ducked)
        px = self._btn_px
        t = self._theme
        self.duck_btn.setIcon(QIcon(
            (speaker_low if self._ducked else speaker)(
                px, t.up if self._ducked else t.hero)))
        self.duck_btn.setIconSize(QSize(px, px))

    def _playing(self) -> bool:
        return bool(self.playing_cb and self.playing_cb())

    def _paint_buttons(self):
        """(Re)paint the foot icons for the current size and state."""
        px = self._btn_px
        t = self._theme
        for btn, pm in ((self.close_btn, xmark_circle(px, t.hero)),
                        (self.ctl_btn, sliders(
                            px, t.hero if self._controls_on else t.sub)),
                        (self.last_btn, icon_pixmap(
                            "history", px,
                            t.hero if self._last_on else t.sub)),
                        (self.time_btn, icon_pixmap(
                            "calendar", px,
                            t.up if self._timetable_wanted() else t.sub)),
                        (self.prev_btn, backward(px, t.hero)),
                        (self.next_btn, forward(px, t.hero)),
                        # ☕ break: the drawn cup of the new set, which reads at
                        # this size where the hand-painted one turned to mush.
                        (self.break_btn, icon_pixmap("break_music", px, t.hero))):
            btn.setIcon(QIcon(pm))
            btn.setIconSize(QSize(px, px))
        self.set_ducked(self._ducked)
        self._play_shown = None   # force the ⏯ glyph to be painted too
        self._sync_transport()

    def _sync_transport(self):
        """▶ ⇄ ⏸ on the big middle button. Polled rather than driven by the
        state tuple: that one stands still while the music is paused."""
        if not self._controls_on:
            return
        playing = self._playing()
        if playing == self._play_shown:
            return
        self._play_shown = playing
        big = int(self._btn_px * 1.5)
        hero = self._theme.hero
        self.play_btn.setIcon(QIcon(pause_circle(big, hero) if playing
                                    else play_circle(big, hero)))
        self.play_btn.setIconSize(QSize(big, big))

    def show_on_screen(self, index: int):
        """Fill the monitor with the given index (clamped to what's connected)."""
        screens = QGuiApplication.screens()
        if screens:
            scr = screens[max(0, min(len(screens) - 1, int(index)))]
            # A full-screen window ignores setGeometry — drop out of it first,
            # so switching monitors mid-tournament really moves the screen.
            if self.isFullScreen():
                self.showNormal()
            self.setGeometry(scr.geometry())
        self.showFullScreen()
        self.raise_()
        self._refresh()
        self._timer.start()
        log.info("🖥 Presenter screen opened\n"
                 "screen: %s", index + 1)

    def _refresh(self):
        self._sync_transport()
        self.time_page.sync_now()
        state = self._state_cb()
        if state == self._last_state:
            return
        prev, self._last_state = self._last_state, state
        dance, title, times, upcoming, last = state
        played, left, ending, frac = times
        self._set_ending(ending)
        self.bar.set_fraction(frac)
        self.dance_lbl.set_icon(
            self._pause_mark if _PAUSE_MARK and dance == PAUSE_TEXT else None)
        self.dance_lbl.set_full_text(dance or "—")
        self.title_lbl.set_full_text(title)
        self.last_lbl.set_full_text(last[0])
        self.last_sub_lbl.set_full_text(last[1])
        self.played_lbl.set_full_text(played)
        self.left_lbl.set_full_text(left)
        for i in range(len(self._next_rows)):
            d, t = upcoming[i] if i < len(upcoming) else ("", "")
            self.next_lbls[i].set_full_text(d)
            self.next_sub_lbls[i].set_full_text(t)
        self._upcoming = list(upcoming)
        self._sync_last()   # …which decides how many of those rows are shown
        # Only the measured lines need the fitting pass. The clock moves on
        # every tick and its width is fixed, so re-fitting for it would be the
        # entire cost of the fast refresh — ten times a second, for nothing.
        if prev is None or ((dance, title, upcoming, last)
                            != (prev[0], prev[1], prev[3], prev[4])):
            self._fit()

    def _set_ending(self, ending: bool):
        """Blink the remaining time red over the last seconds of a title."""
        if ending == self._blink.isActive():
            return
        if ending:
            self._blink.start()
        else:
            self._blink.stop()
            self.left_lbl.set_color(self._theme.left)

    def _blink_left(self):
        self._blink_on = not self._blink_on
        self.left_lbl.set_color(self._theme.end if self._blink_on
                                else self._theme.left)

    def _fit(self):
        """The dance is the one line that may shrink (down to _MIN_SCALE) to
        stay readable in one piece; everything else keeps the size of its block
        and scrolls when a title is too long."""
        # New fonts and newly shown rows only reach the widgets on the next
        # layout pass — and every decision below measures against their width.
        self.layout().activate()
        lbl = self.dance_lbl
        base = self._base_px.get(lbl, 12)
        font = lbl.font()
        size, floor = base, max(9, int(base * _MIN_SCALE))
        room = lbl.width() - lbl.icon_width()
        while size > floor:
            font.setPixelSize(size)
            if QFontMetrics(font).horizontalAdvance(lbl.full_text()) <= room:
                break
            size -= 2
        font.setPixelSize(size)
        lbl.setFont(font)
        for line in self._lines:
            line.sync_scroll()

    def _scale_fonts(self):
        """Size everything off the window height, so the same screen works on a
        13\" laptop panel and on a hall beamer."""
        h = max(240, self.height())
        # Keyed on what the screen is actually showing, not on what is switched
        # on: the 🕘 block costs nothing until it has a title to name, so the
        # first one to reach it is exactly when the column grows — and the
        # queue's own rows come and go with the end of a round.
        key = (h, self._last_shown, self._rows_shown)
        if key == self._font_h:
            return
        self._font_h = key
        # What is switched on has to fit the screen it stands on: the 🕘 block
        # costs a queue row, and on a short panel that is more than the height
        # has to give. Step everything down a notch at a time until the column
        # stands inside the window — never let the window grow instead, a
        # presenter screen bigger than its monitor loses its foot to the
        # taskbar and drops out of full screen.
        scale = 1.0
        while True:
            self._apply_fonts(h, scale)
            self._size_column()
            if scale <= _MIN_FIT or self._measure_h() <= h:
                break
            scale -= 0.05

    def _measure_h(self) -> int:
        """The height the screen needs at the sizes just set.

        Every cached hint in the window is dropped first, and that is the whole
        point. A font change reaches the outer layout only through a posted
        LayoutRequest, which is never delivered inside a synchronous loop — so
        `activate()` alone re-runs the pass against the *first* guess, hands
        back the same number every time, and the fitting loop shrinks the
        screen to its floor without ever seeing that it already fits. Widgets
        as well as layouts: a page in the stack caches its own minimum hint,
        and invalidating the layouts under it does not touch that.
        """
        for lyt in self.findChildren(QLayout):
            lyt.invalidate()
        for child in self.findChildren(QWidget):
            child.updateGeometry()
        self.layout().invalidate()
        self.layout().activate()
        return self.layout().minimumSize().height()

    def _apply_fonts(self, h: int, scale: float):
        """One sizing pass, at `scale` of the nominal fractions of `h`."""
        for lbl, frac in ((self.dance_lbl, 0.135), (self.title_lbl, 0.045),
                          (self.played_lbl, 0.052), (self.left_lbl, 0.052),
                          (self.next_hdr, 0.030), (self.hint_lbl, 0.020),
                          (self.last_hdr, 0.030), (self.last_lbl, 0.048),
                          (self.last_sub_lbl, 0.030), (self.last_num, 0.040),
                          *((lbl, 0.048) for lbl in self.next_lbls),
                          *((lbl, 0.030) for lbl in self.next_sub_lbls),
                          *((lbl, 0.040) for lbl in self.next_num_lbls)):
            px = max(9, int(h * frac * scale))
            self._base_px[lbl] = px
            f = lbl.font()
            f.setPixelSize(px)
            # The hero carries the theme's own face (the Light one is a
            # serif). Set on the font rather than in the stylesheet: every
            # width below is measured with QFontMetrics(lbl.font()), and a
            # family that only reaches the widget through a stylesheet polish
            # is not in that font yet when the fitting pass measures it.
            if lbl is self.dance_lbl:
                f.setFamilies(list(self._theme.hero_families)
                              or [self._base_family])
            lbl.setFont(f)
        for num in (*self.next_num_lbls, self.last_num):
            num.setFixedWidth(int(self._base_px[num] * 1.4))
        self.time_page.apply_fonts(h, scale)
        self.bar.setFixedHeight(max(4, int(h * 0.010)))
        # The ⏸ sits IN the hero line: sized off that font, not off the window,
        # so its bars come out as tall as the letters beside them (the glyph
        # fills about 0.6 of its own square — see _BOX in player.sf_icons).
        self._pause_mark = pause(int(self._base_px[self.dance_lbl] * 1.15),
                                 self._theme.hero)
        self._btn_px = max(16, int(h * 0.040 * scale))
        self._paint_buttons()
        # The transport spaces itself off its own buttons, so it stays a row
        # and not a huddle when the screen is a beamer.
        self.ctl_box.layout().setSpacing(int(self._btn_px * 1.1))

    def _size_column(self):
        """Pin the up-next column to its share of the width. Fixed, not maximal:
        its lines are Ignored-width scrollers, so a free layout would let the
        centring stretches squeeze the whole block to nothing."""
        width = max(360, int(self.width() * _COL_FRAC))
        self.next_box.setFixedWidth(width)
        self.time_page.set_column_width(width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scale_fonts()
        self._size_column()
        self._fit()

    def mouseDoubleClickEvent(self, event):
        """Full screen ⇄ window — so the screen can be dragged to another
        monitor by hand when the combo's guess isn't the wanted one."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        if event.key() == Qt.Key.Key_T:
            self._toggle_timetable()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._timer.stop()
        self._blink.stop()
        self._rotate.stop()
        self.closed.emit()
        super().closeEvent(event)
