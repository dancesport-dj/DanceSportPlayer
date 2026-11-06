"""🤸 The Eintanzen / party dialog — what the warm-up generator is asked to build.

Split off the generator mixin, where it was one 288-line method: the dialog
needs the library's titles (for the party-length estimate) and the folder to
browse from, not the window. So it is a function of those here, tested without
one; the window binds its library and settings to it.
"""
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import planner.models
from gui.dialogs import M3uDropDialog, load_settings, save_settings
from gui.dialogs.folder_scope_dialog import ask_library_folders
from gui.dialogs.warmup_estimate import WarmupEstimateBox
from planner import i18n
from planner.generate.warmup import WARMUP_MODE, warmup_lengths
from planner.terms import dance_name


class _CurrentPageStack(QWidget):
    """Shows one page at a time and is as tall as that page. A QStackedWidget
    is as tall as its tallest page, hidden ones included (also in its
    height-for-width), so the party page left an empty band under Practice.
    Here the pages not shown are hidden, and hidden widgets leave the layout."""

    def __init__(self):
        super().__init__()
        self._lyt = QVBoxLayout(self)
        self._lyt.setContentsMargins(0, 0, 0, 0)

    def addWidget(self, page):
        self._lyt.addWidget(page)
        page.setVisible(self._lyt.count() == 1)

    def setCurrentIndex(self, index):
        for i in range(self._lyt.count()):
            item = self._lyt.itemAt(i)
            if item is not None and (page := item.widget()) is not None:
                page.setVisible(i == index)
        self.updateGeometry()


def _add_mode_box(dlg, lyt):
    """🏆 practice or 🎉 party: the two modes' radio buttons."""
    mode_box = QGroupBox("What to build")
    mode_lyt = QVBoxLayout(mode_box)
    rb_class = QRadioButton("🏆  Practice for a tournament class "
                            "(round-robin through the class's dances)")
    rb_etds = QRadioButton("🎉  Party playlist "
                           "(alternating 3-dance rounds, all dances)")
    rb_comp = QRadioButton("🏁  Competition training list "
                           "(heats per dance, then the final)")
    rb_comp.setObjectName("mode_competition")
    rb_class.setChecked(True)
    mode_grp = QButtonGroup(dlg)
    mode_grp.addButton(rb_class, 0)
    mode_grp.addButton(rb_etds, 1)
    mode_grp.addButton(rb_comp, 2)
    mode_lyt.addWidget(rb_class)
    mode_lyt.addWidget(rb_etds)
    mode_lyt.addWidget(rb_comp)
    lyt.addWidget(mode_box)
    return rb_class, mode_grp


def _build_class_page():
    """Page 0, practice for a class: style, class, length and fresh mix."""
    class_page = QWidget()
    cp = QVBoxLayout(class_page)
    cp.setContentsMargins(0, 0, 0, 0)
    row1 = QHBoxLayout()
    row1.addWidget(QLabel("Style:"))
    style_combo = QComboBox()
    for s in ("Standard", "Latin"):
        style_combo.addItem(s, s)
    style_combo.setCurrentText("Latin")
    row1.addWidget(style_combo)
    row1.addSpacing(12)
    row1.addWidget(QLabel("Class:"))
    class_combo = QComboBox()
    for c in ("D", "C", "B", "A", "S"):
        class_combo.addItem(c, c)
    class_combo.setCurrentText("S")
    row1.addWidget(class_combo)
    row1.addStretch(1)
    cp.addLayout(row1)
    dance_lbl = QLabel()
    dance_lbl.setStyleSheet("color:#555;")
    dance_lbl.setWordWrap(True)
    cp.addWidget(dance_lbl)

    row2 = QHBoxLayout()
    row2.addWidget(QLabel("Max tracks:"))
    max_spin = QSpinBox()
    max_spin.setRange(5, 2000)
    max_spin.setValue(100)
    max_spin.setSingleStep(10)
    max_spin.setToolTip("Upper limit. The list stops here or when the "
                        "TSO-conform pool runs dry — whichever comes first.")
    row2.addWidget(max_spin)
    row2.addSpacing(12)
    row2.addWidget(QLabel("Fresh mix:"))
    fresh_spin = QSpinBox()
    fresh_spin.setRange(0, 100)
    fresh_spin.setValue(25)
    fresh_spin.setSuffix(" %")
    fresh_spin.setToolTip(
        "Share of slots that lean FRESH (least-played) instead of proven "
        "favourites.\nHigher = more never/barely-played tracks — at 100 % the "
        "list is\nbuilt from the least-played tracks upward (not just the few "
        "with zero plays).")
    row2.addWidget(fresh_spin)
    row2.addStretch(1)
    cp.addLayout(row2)
    cp.addWidget(QLabel(
        "All picks are TSO-conform (T24 Rumba / T58-59 Paso allowed, like the "
        "normal playlist)."))
    return (class_page, style_combo, class_combo, dance_lbl, max_spin,
            fresh_spin)


def _build_etds_page(entries):
    """Page 1, the party: its dances, rules, length and ⏱ estimate."""
    etds_page = QWidget()
    ep = QVBoxLayout(etds_page)
    ep.setContentsMargins(0, 0, 0, 0)
    ep.addWidget(QLabel("Dances come in alternating 3-dance rounds "
                        "(not competition rounds)."))

    def chk(parent_lyt, text, checked, tip="", name=""):
        c = QCheckBox(text)
        c.setObjectName(name)
        c.setChecked(checked)
        if tip:
            c.setToolTip(tip)
        parent_lyt.addWidget(c)
        return c

    c_std = chk(ep, "Standard dances", True, name="party_std")
    c_lat = chk(ep, "Latin dances", True, name="party_lat")
    c_mode = chk(ep, "Social Modetänze (Discofox, Salsa, Bachata, WCS, …)", True,
                 "Interleave short social-dance rounds — needs those tracks "
                 "in your library.", name="party_modetaenze")
    # Indented sub-selection: which social dances may appear.
    mode_box = QVBoxLayout()
    mode_box.setContentsMargins(24, 0, 0, 0)
    mode_box.setSpacing(2)
    mode_checks = {}
    _mode_default_on = {"DISCOFOX", "SALSA"}
    for code in WARMUP_MODE:
        cb = QCheckBox(dance_name(code, code))
        cb.setObjectName(f"party_mode_{code}")
        cb.setChecked(code in _mode_default_on)
        mode_box.addWidget(cb)
        mode_checks[code] = cb
    ep.addLayout(mode_box)

    def sync_modetaenze():
        for cb in mode_checks.values():
            cb.setEnabled(c_mode.isChecked())
    c_mode.toggled.connect(lambda *_: sync_modetaenze())
    sync_modetaenze()

    c_paso = chk(ep, "No Paso Doble", False, name="party_nopaso")
    c_latfirst = chk(ep, "Start with a Latin round", False, name="party_latfirst")
    c_lww = chk(ep, "Late Wiener Walzer (hold back early / not back-to-back)", True,
               name="party_lww")
    c_lpd = chk(ep, "Late Paso Doble (not in the first ~40 songs)", True,
               name="party_lpd")
    erow = QHBoxLayout()
    erow.addWidget(QLabel("Max tracks:"))
    etds_max_spin = QSpinBox()
    etds_max_spin.setRange(0, 5000)
    # A multiple of 30 — the length of one full turn of the round cycle —
    # so the default comes out exact. Any other number still ends on a
    # whole round, it just runs a title or two over (see `cap_reached`).
    etds_max_spin.setValue(120)
    etds_max_spin.setSpecialValueText("No limit")
    etds_max_spin.setSingleStep(10)
    etds_max_spin.setToolTip(
        "Cap the party-list length — handy when drawing from the whole "
        "library.\nThe round it lands in is played out, so the list can "
        "run a title or two over.\n0 = No limit (use every eligible "
        "track).")
    erow.addWidget(etds_max_spin)
    erow.addStretch(1)
    ep.addLayout(erow)

    def etds_options():
        return dict(
            include_standard=c_std.isChecked(),
            include_latin=c_lat.isChecked(),
            include_modetaenze=c_mode.isChecked(),
            modetaenze=[c for c, cb in mode_checks.items() if cb.isChecked()],
            no_paso=c_paso.isChecked(),
            start_with_latin=c_latfirst.isChecked(),
            late_ww=c_lww.isChecked(),
            late_pd=c_lpd.isChecked(),
        )

    # ⏱ Songs per dance for a party of N hours, from the library's lengths.
    estimate = WarmupEstimateBox(
        warmup_lengths(entries), etds_options)
    for cb in (c_std, c_lat, c_mode, c_paso, c_latfirst, c_lww, c_lpd,
               *mode_checks.values()):
        cb.toggled.connect(lambda *_: estimate.refresh())
    # Picking the party's hours sets the list length those hours need.
    estimate.songsNeeded.connect(etds_max_spin.setValue)
    ep.addWidget(estimate)
    return (etds_page, c_std, c_lat, etds_max_spin, estimate,
            etds_options)


def _build_competition_page():
    """Page 2, a competition training list: heats of the class's dances, then
    the final. Returns the page and a function giving its settings."""
    page = QWidget()
    pl = QVBoxLayout(page)
    pl.setContentsMargins(0, 0, 0, 0)
    row1 = QHBoxLayout()
    row1.addWidget(QLabel("Style:"))
    style_combo = QComboBox()
    style_combo.setObjectName("comp_style")
    for s in ("Standard", "Latin"):
        style_combo.addItem(s, s)
    style_combo.setCurrentText("Latin")
    row1.addWidget(style_combo)
    row1.addSpacing(12)
    row1.addWidget(QLabel("Class:"))
    class_combo = QComboBox()
    class_combo.setObjectName("comp_class")
    for c in ("D", "C", "B", "A", "S"):
        class_combo.addItem(c, c)
    class_combo.setCurrentText("S")
    row1.addWidget(class_combo)
    row1.addStretch(1)
    pl.addLayout(row1)

    pl.addWidget(QLabel("Dances (untick the ones you do not need):"))
    dance_row = QHBoxLayout()
    pl.addLayout(dance_row)
    checks: dict[str, QCheckBox] = {}

    row2 = QHBoxLayout()
    row2.addWidget(QLabel("Heats per round:"))
    heats_spin = QSpinBox()
    heats_spin.setObjectName("comp_heats")
    heats_spin.setRange(1, 20)
    heats_spin.setValue(3)
    heats_spin.setToolTip("Every dance gets this many tracks in a round, one per heat.")
    row2.addWidget(heats_spin)
    row2.addSpacing(12)
    row2.addWidget(QLabel("Rounds:"))
    rounds_spin = QSpinBox()
    rounds_spin.setObjectName("comp_rounds")
    rounds_spin.setRange(1, 10)
    rounds_spin.setValue(2)
    rounds_spin.setToolTip("The last round is the final.")
    row2.addWidget(rounds_spin)
    row2.addSpacing(12)
    row2.addWidget(QLabel("Final heats:"))
    final_spin = QSpinBox()
    final_spin.setObjectName("comp_final")
    final_spin.setRange(1, 20)
    final_spin.setValue(1)
    final_spin.setToolTip("Heats per dance in the final.")
    row2.addWidget(final_spin)
    row2.addStretch(1)
    pl.addLayout(row2)
    timbre_chk = QCheckBox("Use Timbre Similarity")
    timbre_chk.setObjectName("comp_timbre")
    timbre_chk.setChecked(True)
    timbre_chk.setToolTip(
        "The heats of a dance in a round sound alike: the first track is the\n"
        "anchor, the others are its nearest by timbre. The final and semifinal\n"
        "prefer the titles you played there before.")
    pl.addWidget(timbre_chk)
    fresh_row = QHBoxLayout()
    fresh_row.addWidget(QLabel("Fresh titles in the early rounds:"))
    comp_fresh = QSpinBox()
    comp_fresh.setObjectName("comp_fresh")
    comp_fresh.setRange(0, 100)
    comp_fresh.setSingleStep(10)
    comp_fresh.setSuffix(" %")
    comp_fresh.setToolTip("Share of the heats in the rounds before the semifinal "
                          "that go to fresh titles. The semifinal and the "
                          "final keep to the titles you know.")
    fresh_row.addWidget(comp_fresh)
    fresh_mode = QComboBox()
    fresh_mode.setObjectName("comp_fresh_mode")
    fresh_mode.addItem("New (at most 2 years in the library)", "fresh")
    fresh_mode.addItem("Rarely played (any age)", "rarely")
    fresh_mode.setToolTip("Which titles count as fresh: new ones, or any title "
                          "that was hardly ever played.")
    fresh_row.addWidget(fresh_mode)
    fresh_row.addStretch(1)
    pl.addLayout(fresh_row)
    total_lbl = QLabel()
    total_lbl.setStyleSheet("color:#555;")
    pl.addWidget(total_lbl)

    def dances():
        return [d for d, cb in checks.items() if cb.isChecked()]

    def heat_count():
        return (rounds_spin.value() - 1) * heats_spin.value() + final_spin.value()

    def refresh_total():
        n = len(dances())
        total_lbl.setText(i18n.t("%d tracks: %d dances x %d heats")
                          % (n * heat_count(), n, heat_count()))

    def refill():
        while dance_row.count():
            item = dance_row.takeAt(0)
            gone = item.widget() if item is not None else None
            if gone is not None:
                gone.setParent(None)   # gone now, not at the next event loop
                gone.deleteLater()
        checks.clear()
        defaults = planner.models.DEFAULT_DANCES.get(
            style_combo.currentData(), {}).get(class_combo.currentData(), [])
        for d in defaults:
            cb = QCheckBox(dance_name(d, d))
            cb.setObjectName(f"dance_{d}")
            cb.setChecked(True)
            cb.toggled.connect(lambda *_: refresh_total())
            dance_row.addWidget(cb)
            checks[d] = cb
        dance_row.addStretch(1)
        refresh_total()
    refill()
    style_combo.currentIndexChanged.connect(lambda *_: refill())
    class_combo.currentIndexChanged.connect(lambda *_: refill())
    heats_spin.valueChanged.connect(lambda *_: refresh_total())
    rounds_spin.valueChanged.connect(lambda *_: refresh_total())
    final_spin.valueChanged.connect(lambda *_: refresh_total())

    def settings():
        return dict(style=style_combo.currentData(),
                    dance_class=class_combo.currentData(),
                    dances=dances(), heats=heats_spin.value(),
                    rounds=rounds_spin.value(), final_heats=final_spin.value(),
                    use_timbre=timbre_chk.isChecked(),
                    fresh_ratio=comp_fresh.value() / 100.0,
                    fresh_mode=fresh_mode.currentData())
    return page, settings


def _build_source_box(dlg, wishlists=()):
    """Where the titles come from: ⭐ Favorites, wishlists or an .m3u."""
    src_box = QGroupBox("Draw tracks from")
    src_lyt = QVBoxLayout(src_box)
    # Same wording as the left panel's "Favorites" mode: this draws from the
    # scored library, not from an ad-hoc file. The source key stays "library".
    rb_lib = QRadioButton("⭐  Favorites")
    rb_lib.setToolTip(
        "Draw from your library, exactly like the left panel's "
        "Favorites mode.")
    rb_m3u = QRadioButton("An .m3u playlist file")
    rb_lib.setChecked(True)
    rb_wish = QRadioButton("Open wishlists")
    rb_wish.setToolTip(
        "Draw only from the tracks currently parked in your open ⭐ wishlists.")
    src_grp = QButtonGroup(dlg)
    src_grp.addButton(rb_lib, 0)
    src_grp.addButton(rb_m3u, 1)
    src_grp.addButton(rb_wish, 2)
    src_lyt.addWidget(rb_lib)
    src_lyt.addWidget(rb_wish)
    # One tick per wishlist that has titles; the rest are not offered.
    rb_wish.setEnabled(bool(wishlists))
    wish_checks = []
    for name, count in wishlists:
        cb = QCheckBox(f"{name} ({count})")
        cb.setChecked(True)
        cb.setEnabled(False)
        cb.setStyleSheet("margin-left:24px;")
        src_lyt.addWidget(cb)
        wish_checks.append(cb)
    m3u_row = QHBoxLayout()
    m3u_row.addWidget(rb_m3u)
    m3u_edit = QLineEdit()
    m3u_edit.setPlaceholderText("Choose an .m3u file…")
    m3u_edit.setEnabled(False)
    m3u_btn = QPushButton("Browse…")
    m3u_btn.setEnabled(False)
    m3u_row.addWidget(m3u_edit, stretch=1)
    m3u_row.addWidget(m3u_btn)
    src_lyt.addLayout(m3u_row)
    # 📁 A fourth source: only the titles in the library folders ticked in a list.
    rb_folders = QRadioButton("📁  Chosen library folders")
    rb_folders.setToolTip(
        "Draw only from the titles in the library folders you tick."
        " A folder counts for the titles directly in it, not below it.")
    src_grp.addButton(rb_folders, 3)
    folders_row = QHBoxLayout()
    folders_row.addWidget(rb_folders)
    dlg.folders_chosen = []
    dlg.folders_lbl = QLabel(i18n.t("No folder chosen"))
    dlg.folders_btn = QPushButton("Choose…")
    dlg.folders_btn.setEnabled(False)
    folders_row.addWidget(dlg.folders_lbl, stretch=1)
    folders_row.addWidget(dlg.folders_btn)
    src_lyt.addLayout(folders_row)
    dlg.rb_folders = rb_folders
    # Whatever the source: leave out what another deck holds already.
    unused_chk = QCheckBox("Skip greyed titles")
    unused_chk.setObjectName("source_unused")
    unused_chk.setChecked(True)
    unused_chk.setToolTip(
        "Leave out the titles another deck already holds — planned or"
        " played (played ones stay in their deck, greyed).")
    src_lyt.addWidget(unused_chk)
    return (src_box, rb_lib, rb_m3u, rb_wish, src_grp, unused_chk, m3u_edit,
            m3u_btn, wish_checks)


def _wire_source(dlg, library_dir, rb_lib, rb_m3u, rb_wish, src_grp, unused_chk,
                 m3u_edit, m3u_btn, wish_checks):
    """The source box's enabling, its Browse… and a dropped playlist."""
    def sync_source():
        use_m3u = rb_m3u.isChecked()
        m3u_edit.setEnabled(use_m3u)
        m3u_btn.setEnabled(use_m3u)
        dlg.folders_btn.setEnabled(dlg.rb_folders.isChecked())
        for cb in wish_checks:
            cb.setEnabled(rb_wish.isChecked())
            # Ticked-looking boxes under another choice read as part of it.
            cb.setVisible(rb_wish.isChecked())
    src_grp.idToggled.connect(lambda *_: sync_source())
    sync_source()

    def browse_m3u():
        start = library_dir
        path, _ = QFileDialog.getOpenFileName(
            dlg, "Choose an .m3u playlist", start,
            "Playlists (*.m3u *.m3u8)")
        if path:
            m3u_edit.setText(path)
    m3u_btn.clicked.connect(browse_m3u)

    def on_m3u_dropped(path):
        # Dropping a playlist onto the dialog picks the .m3u source and fills it.
        rb_m3u.setChecked(True)
        sync_source()
        m3u_edit.setText(path)
    dlg.m3uDropped.connect(on_m3u_dropped)

    def choose_folders():
        picked = ask_library_folders(dlg, library_dir, dlg.library_entries,
                                     dlg.folders_chosen)
        if picked is not None:
            dlg.folders_chosen = picked
            n = len(picked)
            dlg.folders_lbl.setText(i18n.t("%d folders chosen") % n if n
                                    else i18n.t("No folder chosen"))
    dlg.folders_btn.clicked.connect(choose_folders)


def _add_buttons(dlg, lyt):
    """Cancel and Generate."""
    bb = QHBoxLayout()
    bb.addStretch(1)
    ok = QPushButton("Generate")
    cancel = QPushButton("Cancel")
    ok.setDefault(True)
    ok.clicked.connect(dlg.accept)
    cancel.clicked.connect(dlg.reject)
    bb.addWidget(cancel)
    bb.addWidget(ok)
    lyt.addLayout(bb)


_STATE_KEY = "warmup_dialog"


def _restore_choices(dlg, mode_grp, src_grp, state):
    """Put back what the last accepted dialog had: the mode, the source, the
    ticks and the competition's style, class and counts. Anything missing or
    no longer valid keeps its default."""
    if not isinstance(state, dict):
        return
    for grp, key in ((mode_grp, "mode"), (src_grp, "source")):
        btn = grp.button(state.get(key)) if isinstance(state.get(key), int) else None
        if btn is not None and btn.isEnabled():
            btn.setChecked(True)
    saved = state.get("fields")
    if not isinstance(saved, dict):
        return
    # Combos first: a new style or class rebuilds the dance ticks.
    for kind in (QComboBox, QSpinBox, QCheckBox):
        for w in dlg.findChildren(kind):
            name = w.objectName()
            if not name or name not in saved:
                continue
            val = saved[name]
            if kind is QComboBox and isinstance(val, str):
                i = w.findData(val)
                if i >= 0:
                    w.setCurrentIndex(i)
            elif kind is QSpinBox and isinstance(val, int) and not isinstance(val, bool):
                w.setValue(val)
            elif kind is QCheckBox and isinstance(val, bool):
                w.setChecked(val)


def _choices(dlg, mode_grp, src_grp):
    fields = {}
    for kind in (QComboBox, QSpinBox, QCheckBox):
        for w in dlg.findChildren(kind):
            name = w.objectName()
            if not name:
                continue
            if kind is QComboBox:
                fields[name] = w.currentData()
            elif kind is QSpinBox:
                fields[name] = w.value()
            else:
                fields[name] = w.isChecked()
    return dict(mode=mode_grp.checkedId(), source=src_grp.checkedId(),
                fields=fields)


def ask_warmup_options(parent, entries: list, library_dir: str, wishlists=(),
                       memory: dict | None = None):
    """Dialog for the warm-up / party-playlist generator. Returns a settings
    dict (see keys below) or None if the user cancelled.

    Two modes: a per-class WARM-UP (the class's dances round-robin, TSO-conform,
    popular + fresh mix) and the ETDS PARTY playlist (alternating 3-dance rounds).
    Either can draw from the whole library or a chosen .m3u file.
    `wishlists`: (name, title count) of each wishlist that has titles; the
    answer's `wishlist_picks` holds the positions of the ticked ones.
    `memory`: the settings dict the window keeps and saves later. The choices
    go into that one, or a save of it would drop them again."""
    memory = load_settings() if memory is None else memory
    dlg = M3uDropDialog(parent)
    dlg.library_entries = entries   # for the 📁 folder list
    dlg.setWindowTitle("🤸  Practice / party playlist")
    lyt = QVBoxLayout(dlg)

    # ── Mode ──────────────────────────────────────────────────────────────
    rb_class, mode_grp = _add_mode_box(dlg, lyt)

    stack = _CurrentPageStack()
    lyt.addWidget(stack)

    # ── Page 0: per-class warm-up ───────────────────────────────────────────
    (class_page, style_combo, class_combo, dance_lbl, max_spin,
     fresh_spin) = _build_class_page()
    stack.addWidget(class_page)

    # ── Page 1: ETDS party ──────────────────────────────────────────────────
    (etds_page, c_std, c_lat, etds_max_spin, estimate,
     etds_options) = _build_etds_page(entries)
    stack.addWidget(etds_page)

    # ── Page 2: competition training list ───────────────────────────────────────
    comp_page, comp_settings = _build_competition_page()
    stack.addWidget(comp_page)

    # ── Source (shared) ──────────────────────────────────────────────────────
    (src_box, rb_lib, rb_m3u, rb_wish, src_grp, unused_chk, m3u_edit,
     m3u_btn, wish_checks) = _build_source_box(dlg, wishlists)
    lyt.addWidget(src_box)

    # ── Wiring ────────────────────────────────────────────────────────────────
    def refresh_dances():
        style = style_combo.currentData()
        cls = class_combo.currentData()
        dances = planner.models.DEFAULT_DANCES.get(style, {}).get(cls, [])
        if not dances:
            dance_lbl.setText("No dances for this class.")
            return
        names = ", ".join(dance_name(d, d) for d in dances)
        seq = " → ".join(dances)
        dance_lbl.setText(i18n.t("Dances (%d): %s") % (len(dances), names) + "\n"
                          + i18n.t("Order: %s, %s, …") % (seq, seq))
    refresh_dances()
    style_combo.currentIndexChanged.connect(refresh_dances)
    class_combo.currentIndexChanged.connect(refresh_dances)

    def show_page():
        stack.setCurrentIndex(mode_grp.checkedId())
        stack.updateGeometry()
        dlg.adjustSize()   # shrink or grow to the page now shown
    mode_grp.idToggled.connect(lambda *_: show_page())

    _wire_source(dlg, library_dir, rb_lib, rb_m3u, rb_wish, src_grp, unused_chk,
                 m3u_edit, m3u_btn, wish_checks)

    _add_buttons(dlg, lyt)

    _restore_choices(dlg, mode_grp, src_grp, memory.get(_STATE_KEY))
    show_page()

    is_class = rb_class.isChecked
    is_comp = lambda: mode_grp.checkedId() == 2   # noqa: E731
    use_m3u = rb_m3u.isChecked

    def problem():
        """What is missing, or None. Asked while the dialog is still open: a
        message after it closed lost every setting made (#77)."""
        if use_m3u() and not m3u_edit.text().strip():
            return "Choose an .m3u file first."
        if is_comp() and not comp_settings()["dances"]:
            return "Tick at least one dance."
        if not is_class() and not is_comp() and not (c_std.isChecked() or c_lat.isChecked()):
            return "Pick at least Standard or Latin dances."
        if rb_wish.isChecked() and not any(cb.isChecked() for cb in wish_checks):
            return "Tick at least one wishlist."
        return None

    while True:
        if dlg.exec() != QDialog.DialogCode.Accepted:
            estimate.stop()
            return None
        message = problem()
        if message is None:
            break
        QMessageBox.warning(dlg, "Practice", message)
    estimate.stop()
    memory[_STATE_KEY] = _choices(dlg, mode_grp, src_grp)
    save_settings(memory)

    class_mode = rb_class.isChecked()
    comp_mode = mode_grp.checkedId() == 2
    m3u_mode = rb_m3u.isChecked()
    m3u_path = m3u_edit.text().strip()
    picks = [i for i, cb in enumerate(wish_checks) if cb.isChecked()]
    source = ("m3u" if m3u_mode
              else "wishlists" if rb_wish.isChecked()
              else "folders" if dlg.rb_folders.isChecked()
              else "library")
    return dict(
        mode="class" if class_mode else "competition" if comp_mode else "etds",
        source=source,
        m3u_path=m3u_path if m3u_mode else None,
        unused_only=unused_chk.isChecked(),
        folders=list(dlg.folders_chosen) if source == "folders" else [],
        wishlist_picks=picks,
        # class mode
        style=style_combo.currentData(),
        dance_class=class_combo.currentData(),
        max_tracks=max_spin.value(),
        fresh_ratio=fresh_spin.value() / 100.0,
        relax=True,
        # etds mode
        etds=dict(etds_options(), max_tracks=etds_max_spin.value() or None),
        # competition mode
        competition=comp_settings(),
    )
