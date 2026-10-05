"""🤸 The Eintanzen / party dialog — what the warm-up generator is asked to build.

Split off the generator mixin, where it was one 288-line method: the dialog
needs the library's titles (for the party-length estimate) and the folder to
browse from, not the window. So it is a function of those here, tested without
one; the window binds its library and settings to it.
"""
import planner.models
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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from gui.dialogs import M3uDropDialog
from gui.warmup_estimate import WarmupEstimateBox
from planner import i18n
from planner.terms import dance_name
from planner.warmup import _WARMUP_MODE, warmup_lengths


def ask_warmup_options(parent, entries: list, library_dir: str):
    """Dialog for the warm-up / party-playlist generator. Returns a settings
    dict (see keys below) or None if the user cancelled.

    Two modes: a per-class WARM-UP (the class's dances round-robin, TSO-conform,
    popular + fresh mix) and the ETDS PARTY playlist (alternating 3-dance rounds).
    Either can draw from the whole library or a chosen .m3u file."""
    dlg = M3uDropDialog(parent)
    dlg.setWindowTitle("🤸  Eintanzen / party playlist")
    lyt = QVBoxLayout(dlg)

    # ── Mode ──────────────────────────────────────────────────────────────
    mode_box = QGroupBox("What to build")
    mode_lyt = QVBoxLayout(mode_box)
    rb_class = QRadioButton("🏆  Eintanzen for a tournament class "
                            "(round-robin through the class's dances)")
    rb_etds = QRadioButton("🎉  Party playlist "
                           "(alternating 3-dance rounds, all dances)")
    rb_class.setChecked(True)
    mode_grp = QButtonGroup(dlg)
    mode_grp.addButton(rb_class, 0)
    mode_grp.addButton(rb_etds, 1)
    mode_lyt.addWidget(rb_class)
    mode_lyt.addWidget(rb_etds)
    lyt.addWidget(mode_box)

    stack = QStackedWidget()
    lyt.addWidget(stack)

    # ── Page 0: per-class warm-up ───────────────────────────────────────────
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
    stack.addWidget(class_page)

    # ── Page 1: ETDS party ──────────────────────────────────────────────────
    etds_page = QWidget()
    ep = QVBoxLayout(etds_page)
    ep.setContentsMargins(0, 0, 0, 0)
    ep.addWidget(QLabel("Dances come in alternating 3-dance rounds "
                        "(not competition rounds)."))

    def chk(parent_lyt, text, checked, tip=""):
        c = QCheckBox(text)
        c.setChecked(checked)
        if tip:
            c.setToolTip(tip)
        parent_lyt.addWidget(c)
        return c

    c_std = chk(ep, "Standard dances", True)
    c_lat = chk(ep, "Latin dances", True)
    c_mode = chk(ep, "Social Modetänze (Discofox, Salsa, Bachata, WCS, …)", True,
                 "Interleave short social-dance rounds — needs those tracks "
                 "in your library.")
    # Indented sub-selection: which social dances may appear.
    mode_box = QVBoxLayout()
    mode_box.setContentsMargins(24, 0, 0, 0)
    mode_box.setSpacing(2)
    mode_checks = {}
    _mode_default_on = {"DISCOFOX", "SALSA"}
    for code in _WARMUP_MODE:
        cb = QCheckBox(dance_name(code, code))
        cb.setChecked(code in _mode_default_on)
        mode_box.addWidget(cb)
        mode_checks[code] = cb
    ep.addLayout(mode_box)

    def sync_modetaenze():
        for cb in mode_checks.values():
            cb.setEnabled(c_mode.isChecked())
    c_mode.toggled.connect(lambda *_: sync_modetaenze())
    sync_modetaenze()

    c_paso = chk(ep, "No Paso Doble", False)
    c_latfirst = chk(ep, "Start with a Latin round", False)
    c_lww = chk(ep, "Late Wiener Walzer (hold back early / not back-to-back)", True)
    c_lpd = chk(ep, "Late Paso Doble (not in the first ~40 songs)", True)
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
    stack.addWidget(etds_page)

    # ── Source (shared) ──────────────────────────────────────────────────────
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
    unused_chk = QCheckBox("    Only tracks not already in my open playlists")
    unused_chk.setChecked(True)
    src_lyt.addWidget(unused_chk)
    src_lyt.addWidget(rb_wish)
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
    mode_grp.idToggled.connect(
        lambda _id, on: stack.setCurrentIndex(mode_grp.checkedId()))

    def sync_source():
        use_m3u = rb_m3u.isChecked()
        m3u_edit.setEnabled(use_m3u)
        m3u_btn.setEnabled(use_m3u)
        unused_chk.setEnabled(rb_lib.isChecked())
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

    accepted = dlg.exec() == QDialog.DialogCode.Accepted
    estimate.stop()
    if not accepted:
        return None

    is_class = rb_class.isChecked()
    use_m3u = rb_m3u.isChecked()
    m3u_path = m3u_edit.text().strip()
    if use_m3u and not m3u_path:
        QMessageBox.warning(parent, "Eintanzen", "Choose an .m3u file first.")
        return None
    if not is_class and not (c_std.isChecked() or c_lat.isChecked()):
        QMessageBox.warning(parent, "Eintanzen",
                            "Pick at least Standard or Latin dances.")
        return None

    source = ("m3u" if use_m3u
              else "wishlists" if rb_wish.isChecked()
              else "library")
    return dict(
        mode="class" if is_class else "etds",
        source=source,
        m3u_path=m3u_path if use_m3u else None,
        unused_only=unused_chk.isChecked() and source == "library",
        # class mode
        style=style_combo.currentData(),
        dance_class=class_combo.currentData(),
        max_tracks=max_spin.value(),
        fresh_ratio=fresh_spin.value() / 100.0,
        relax=True,
        # etds mode
        etds=dict(etds_options(), max_tracks=etds_max_spin.value() or None),
    )
