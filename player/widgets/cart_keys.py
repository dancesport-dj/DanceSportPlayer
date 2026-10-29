"""⌨ The cartwall's shortcuts: one key picker per pad and the panel of them.

The desk keys dialog (player.dialogs.desk_keys_dialog) shows the panel next to
the desk's own keys. The wall and its pads are in player.widgets.cartwall.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from planner import i18n
from planner.playing import cartwall as pc


# ─────────────────────────────────────────────────────────────────────────────
# Shortcuts
# ─────────────────────────────────────────────────────────────────────────────
class KeyPicker(QWidget):
    """One shortcut: press it, Learn it, or ✕ it away.

    Learn armed, the next key pressed is the key, whatever it is (F13–F24
    from a Stream Deck too) — no list of keys someone thought of first."""

    changed = Signal()

    def __init__(self, sequence: str = "", parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self._edit = QKeySequenceEdit()
        self._edit.setKeySequence(QKeySequence(sequence))
        # One chord, not a sequence: Qt would otherwise record "Ctrl+1, 2" from
        # a hesitant press, and a pad key that needs two taps is not a pad key.
        self._edit.setMaximumSequenceLength(1)
        # Wide enough for a long chord: on a tab beside a wider one, Qt would
        # otherwise squeeze it down to "ft+P".
        self._edit.setMinimumWidth(
            self._edit.fontMetrics().horizontalAdvance("Ctrl+Shift+Down") + 24)
        self._edit.setToolTip("Press the keys you want")
        self._edit.keySequenceChanged.connect(self._on_edit)
        row.addWidget(self._edit, 1)

        self._before = None   # the key while learning — Cancel puts it back
        self._learn = QPushButton("Learn")
        self._learn.setCheckable(True)
        self._learn.setToolTip("Click, then press the key that should do it")
        self._learn.clicked.connect(self._on_learn)
        row.addWidget(self._learn)

        clear = QToolButton()
        clear.setText("✕")
        clear.setAutoRaise(True)
        clear.setToolTip("No key")
        clear.clicked.connect(self._on_clear)
        row.addWidget(clear)
        # Never squeezed below a readable field: a crowded list scrolls.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    # ── value ──
    def sequence(self) -> str:
        return self._edit.keySequence().toString()

    def set_sequence(self, text: str) -> None:
        self._edit.blockSignals(True)
        self._edit.setKeySequence(QKeySequence(text))
        self._edit.blockSignals(False)

    # ── internals ──
    def _on_edit(self, _seq) -> None:
        if self.sequence():
            self._stop_learning()
        self.changed.emit()

    def _on_clear(self) -> None:
        # Through set_sequence, so clearing reports itself once — clear() alone
        # would fire keySequenceChanged as well.
        self._stop_learning()
        self.set_sequence("")
        self.changed.emit()

    def _on_learn(self) -> None:
        """Arm: the next key pressed is the key. Pressed again, it cancels
        and the key it had stays."""
        if self._before is None:
            self._before = self.sequence()
            self.set_sequence("")
            self._learn.setText(i18n.t("Cancel"))
            self._learn.setChecked(True)
            self._edit.setFocus()
        else:
            self.set_sequence(self._before)
            self._stop_learning()

    def _stop_learning(self) -> None:
        if self._before is None:
            return
        self._before = None
        self._learn.setText(i18n.t("Learn"))
        self._learn.setChecked(False)


class CartKeysPanel(QWidget):
    """Every key the wall answers to: the 🎛 tab of the ⌨ Keys window
    (player.dialogs.desk_keys_dialog), which also holds the desk keys.

    Two layers, because they behave differently and the difference is the whole
    reason both exist: a SLOT key belongs to a position and fires whatever pad
    is sitting there on the page you are looking at, while a PAD key belongs to
    the sample and follows it wherever it is moved, on any page.
    """

    changed = Signal()      # a key was edited — not when set_taken() repaints

    def __init__(self, grid, pages: list[pc.Page], slot_keys, parent=None,
                 taken: dict | None = None):
        super().__init__(parent)
        self._taken = dict(taken or {})  # {key: label} the app or a desk key has
        self._pad_names: dict[tuple, str] = {}
        self._grid = grid
        self._cells = list(pc.cells_in_order(grid))
        self._slot_pickers: list[KeyPicker] = []
        self._pad_pickers: list[tuple[tuple, KeyPicker, QLabel]] = []
        self._slot_warnings: list[QLabel] = []

        lyt = QVBoxLayout(self)
        body = QWidget()
        form = QVBoxLayout(body)
        form.setContentsMargins(0, 0, 0, 0)

        form.addWidget(_section("Slot defaults — apply to every page"))
        form.addWidget(QLabel(
            "The key fires whichever pad sits in that slot on the page you are\n"
            "looking at, so the same finger hits the same corner on every page."))
        grid_lyt = QGridLayout()
        grid_lyt.setColumnStretch(1, 1)
        keys = pc.clean_slot_keys(slot_keys)
        for slot, _cell in enumerate(self._cells):
            picker = KeyPicker(keys[slot] if slot < len(keys) else "")
            picker.changed.connect(self._on_edit)
            warn = _warning_label()
            grid_lyt.addWidget(QLabel(i18n.t("Slot %d") % (slot + 1)), slot, 0)
            grid_lyt.addWidget(picker, slot, 1)
            grid_lyt.addWidget(warn, slot, 2)
            self._slot_pickers.append(picker)
            self._slot_warnings.append(warn)
        form.addLayout(grid_lyt)

        pads = [(page, cell, pad)
                for page, p in enumerate(pages)
                for cell, pad in sorted(p.pads.items())]
        form.addSpacing(10)
        form.addWidget(_section("Pad keys — travel with the pad"))
        if pads:
            form.addWidget(QLabel(
                "A key given to a pad follows it wherever it is moved and works\n"
                "from any page. Empty = that pad answers to its slot's key."))
            pad_lyt = QGridLayout()
            pad_lyt.setColumnStretch(1, 1)
            for line, (page, cell, pad) in enumerate(pads):
                picker = KeyPicker(pad.shortcut)
                picker.changed.connect(self._on_edit)
                warn = _warning_label()
                name = _pad_name(pad)
                self._pad_names[(page, *cell)] = f"{name} (p{page + 1})"
                caption = QLabel(f"p{page + 1}  {name}")
                caption.setToolTip(pad.path)
                pad_lyt.addWidget(caption, line, 0)
                pad_lyt.addWidget(picker, line, 1)
                pad_lyt.addWidget(warn, line, 2)
                self._pad_pickers.append(((page, *cell), picker, warn))
            form.addLayout(pad_lyt)
        else:
            form.addWidget(QLabel("This wall has no pads yet."))

        # The list is as long as the wall is big — 8 pages of a 2×12 grid will
        # not fit on a laptop screen otherwise.
        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(360)
        # As wide as the rows, so Learn, ✕ and a warning are never cut off.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(body.sizeHint().width()
                               + scroll.verticalScrollBar().sizeHint().width()
                               + 2 * scroll.frameWidth())
        lyt.addWidget(scroll)

        self._clash = QLabel("")
        self._clash.setStyleSheet("color:#b26a00;")
        self._clash.setWordWrap(True)
        lyt.addWidget(self._clash)

        restore = QPushButton("Restore slot defaults")
        restore.setToolTip(i18n.t("Back to %s…%s, leaving the pad keys alone")
                           % (pc.SLOT_KEYS[0], pc.SLOT_KEYS[-1]))
        restore.clicked.connect(self._restore_defaults)
        row = QHBoxLayout()
        row.addWidget(restore)
        row.addStretch(1)
        lyt.addLayout(row)
        self._refresh_conflicts()

    # ── results ──
    def slot_keys(self) -> tuple[str, ...]:
        return pc.clean_slot_keys([p.sequence() for p in self._slot_pickers])

    def pad_keys(self) -> dict:
        """{(page, row, col): shortcut} for every pad the dialog listed."""
        return {key: picker.sequence() for key, picker, _w in self._pad_pickers}

    def owners(self) -> dict:
        """{key: "pad or slot"} as the keys stand now, edits included — what
        the desk tab must not hand out a second time. First one wins, pads
        before slots, as on the wall itself."""
        out: dict[str, str] = {}
        for picker, name in self._rows():
            seq = picker.sequence()
            if seq and seq not in out:
                out[seq] = name
        return out

    def set_taken(self, taken: dict) -> None:
        """{key: label} outside the wall changed — the desk tab's, unsaved."""
        self._taken = dict(taken)
        self._refresh_conflicts()

    # ── conflicts ──
    def _rows(self) -> list:
        """(picker, name) in the order the wall binds them: pads, then slots."""
        rows = [(picker, self._pad_names[key])
                for key, picker, _w in self._pad_pickers]
        rows += [(picker, i18n.t("Slot %d") % (slot + 1))
                 for slot, picker in enumerate(self._slot_pickers)]
        return rows

    def _on_edit(self) -> None:
        self._refresh_conflicts()
        self.changed.emit()

    def _refresh_conflicts(self) -> None:
        """Mark every key that a pad or slot ahead of it has already claimed,
        or that the app or a desk key answers to — by name, both.

        The order mirrors _add_shortcut exactly — pads first, then slots — so
        what the dialog warns about is what the wall will actually do, rather
        than a second opinion about it."""
        owners: dict[str, str] = {}
        warnings = [w for _k, _p, w in self._pad_pickers] + self._slot_warnings
        for (picker, name), warn in zip(self._rows(), warnings, strict=True):
            seq = picker.sequence()
            if seq in self._taken:
                warn.setText("%s: %s" % (i18n.t("⚠ The app uses this key"),
                                         i18n.t(self._taken[seq])))
                continue
            owner = owners.get(seq) if seq else None
            warn.setText(i18n.t("⚠ already used by %s") % owner if owner else "")
            if seq and owner is None:
                owners[seq] = name
        clashes = sum(1 for w in self._slot_warnings if w.text())
        clashes += sum(1 for _k, _p, w in self._pad_pickers if w.text())
        self._clash.setText(
            "" if not clashes else
            (i18n.t("%d key claimed twice — the marked ones will not fire. Pad keys win over slot keys.") if clashes == 1
             else i18n.t("%d keys claimed twice — the marked ones will not fire. Pad keys win over slot keys.")) % clashes)

    def _restore_defaults(self) -> None:
        for slot, picker in enumerate(self._slot_pickers):
            picker.set_sequence(pc.SLOT_KEYS[slot]
                                if slot < len(pc.SLOT_KEYS) else "")
        self._on_edit()


def _pad_name(pad: pc.CartPad) -> str:
    """A pad as the ⌨ dialogs name it: its label, else its file's name."""
    return (pad.label.strip() or Path(pad.path).stem)[:pc.LABEL_MAX]


def _warning_label() -> QLabel:
    """A row's clash note: wrapped at a fixed width, so a long one does not
    widen the dialog past its own window."""
    warn = QLabel("")
    warn.setStyleSheet("color:#b26a00; font-size:11px;")
    warn.setWordWrap(True)
    warn.setFixedWidth(220)
    return warn


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-weight:bold;")
    return lbl
