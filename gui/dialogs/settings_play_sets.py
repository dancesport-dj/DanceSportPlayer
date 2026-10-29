"""🎛 The Settings dialog's Play sets tab: the 🏆 and 🎉 sets, the TSO
pitch target and the lengths per dance and per round.

Split off gui/dialogs/settings_dialog.py: building the tab, and reading
its settings back for SettingsDialog.values().
"""
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.settings_look import _DialogHost
from planner import i18n
from planner.models import TEMPO_RANGES, TsoBand
from planner.playing.celebration import (
    CELEBRATE_MAX_SECS,
    CELEBRATE_PCT_MIN,
    celebrate_dip_pct,
    celebrate_down_secs,
    celebrate_hold_secs,
    celebrate_mode,
    celebrate_pct,
    celebrate_up_secs,
)
from planner.playing.play_sets import (
    DANCE_SECS_KEY,
    LEN_MAX,
    LEN_STEP,
    ROUND_DANCE_SECS_KEY,
    ROUND_KINDS,
    ROUND_PD_KEY,
    XFADE_MAX_SECS,
    XFADE_MIN_SECS,
    dance_secs_of,
    dblclick_ask_of,
    parse_play_length,
    pd_of,
    play_set_of,
    round_dance_secs_of,
    round_pd_n_of,
    tso_of,
)
from planner.terms import dance_name, round_name, rules_name
from shared.widgets import hsep
from shared.xfade_view import CrossfadeCurveButton, CrossfadeView


class PlaySetsTabMixin(_DialogHost):
    """The 🎛 Play sets tab of SettingsDialog."""

    def _setup_play_sets_tab(self, settings, tabs):
        """🎛 Play sets: what the two buttons on the ▶ panel apply."""
        # ═══ Tab 4: Play sets — what the two buttons on the ▶ panel apply ═══
        sets_tab = QWidget()
        tlyt = QVBoxLayout(sets_tab)
        tlyt.setSpacing(8)
        tlyt.addWidget(QLabel(
            "<b>🎛 Play sets</b> — the two buttons on the ▶ Playing panel put "
            "the controls on these values in one press:"))

        self._set_widgets = {}
        for which, caption, blurb in (
                ("tournament", "🏆  Tournament set",
                 "The values a heat is run with — pressed to get back to them "
                 "after a party list has pulled the panel somewhere else."),
                ("party", "🎉  Party set",
                 "Applied by itself as soon as you play from the 🤸 Practice / "
                 "party list, and switched back when a tournament deck takes over.")):
            self._add_play_set_box(tlyt, settings, which, caption, blurb)
            # 🎚 The pitch target belongs to the heat: right under 🏆.
            if which == "tournament":
                self._add_tso_band_grid(tlyt, settings)

        pd_note = QLabel(
            "🐂 Each set carries its own Paso Doble values. Under 🏆 the "
            "highlight stop is <i>off</i> by default: the detection is not good "
            "enough yet to cut a competition Paso Doble on, and a heat stopped "
            "in the wrong bar is danced twice. Under 🎉 it stops after the 2nd "
            "highlight and waits 3 s, so the couples can take their position.")
        pd_note.setWordWrap(True)
        pd_note.setStyleSheet("color:#666; font-size:11px;")
        tlyt.addWidget(pd_note)

        tlyt.addStretch()
        sets_idx = tabs.addTab(sets_tab, "🎛 Play sets")
        return sets_idx

    def _add_play_set_box(self, tlyt, settings, which, caption, blurb):
        """🏆/🎉 One play set's box: length, fades, crossfade and switches."""
        cur = dict(play_set_of(settings, which), tso=tso_of(settings, which),
                   dblclick_ask=dblclick_ask_of(settings, which))
        box = QGroupBox(caption)
        blyt = QVBoxLayout(box)
        hint = QLabel(blurb)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#777; font-size:11px;")
        blyt.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("Play length:"))
        length = QComboBox()
        length.addItem("full — to each title's own end", 0)
        for s in range(LEN_STEP, LEN_MAX + 1, LEN_STEP):
            length.addItem(f"{s // 60}:{s % 60:02d}", s)
        # Typable as well as pickable — the rungs are 15 s apart and a heat
        # that wants 1:37 has to be able to say so here too, not only on the
        # panel. NoInsert: a typed length is read back from the text, it
        # must not grow the list.
        length.setEditable(True)
        length.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        length.setToolTip("Pick a length or type one: m:ss, seconds, "
                          "or 'full'")
        idx = length.findData(cur["secs"])
        if idx >= 0:
            length.setCurrentIndex(idx)
        else:
            # An off-ladder length typed in earlier: show it as it is, or
            # reopening the dialog would silently snap it to a rung.
            length.setEditText(
                f"{cur['secs'] // 60}:{cur['secs'] % 60:02d}")
        row.addWidget(length)
        row.addSpacing(12)
        row.addWidget(QLabel("Fade-out:"))
        fade = QDoubleSpinBox()
        fade.setRange(0, 10)
        fade.setDecimals(1)
        fade.setSingleStep(0.5)
        fade.setSuffix(" s")
        fade.setValue(float(cur["fade"]))
        fade.setToolTip("How long the volume takes to ramp down to 0 when\n"
                        "the play length cuts a title — half-second steps")
        row.addWidget(fade)
        fade_inside = QCheckBox("within the length")
        fade_inside.setChecked(bool(cur["fade_inside"]))
        fade_inside.setToolTip(
            "Ticked: the fade-out ends at the play length.\n"
            "Unticked: the title plays its full length, then fades out.")
        row.addWidget(fade_inside)
        row.addSpacing(12)
        xfade_on, xfade, curves = self._add_crossfade_controls(row, cur)
        row.addStretch(1)
        blyt.addLayout(row)

        boxes = self._add_play_set_checks(blyt, cur)
        boxes["fade_inside"] = fade_inside
        self._set_widgets[which] = {"length": length, "fade": fade,
                                    "xfade": xfade, "xfade_on": xfade_on,
                                    "xfade_curve": curves,
                                    "boxes": boxes, "secs": cur["secs"]}
        self._set_widgets[which]["pd"] = self._add_pd_row(blyt, settings, which)
        if which == "tournament":
            self._add_dance_len_grid(blyt, settings)
            # 🥇 Only a competition has a final to play on after.
            self._add_celebrate_box(blyt, settings)
        tlyt.addWidget(box)

    def _add_celebrate_box(self, set_lyt, settings):
        """🥇 The final plays on: which of its titles come back up after the
        play length faded them out, how loud, and over how long."""
        box = QGroupBox("🥇  Final: the music plays on")
        self._celebrate_box = box
        blyt = QVBoxLayout(box)
        hint = QLabel(
            "After the play length has faded a title of the final out, it "
            "comes back up as background while the couples celebrate — until "
            "🔉↓ fades it, the next title starts or the file ends. Only under "
            "✋ Manual: with ⏭ Auto the ⏸ pause and its music follow each "
            "title, and a title of the final ends as always.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#777; font-size:11px;")
        self._celebrate_hint = hint
        blyt.addWidget(hint)

        row = QHBoxLayout()
        mode = QComboBox()
        for caption, key in (("Off", "off"),
                             ("After the last dance of the final", "last"),
                             ("After every dance of the final", "all")):
            mode.addItem(caption, key)
        mode.setCurrentIndex(mode.findData(celebrate_mode(settings)))
        mode.setToolTip("Which titles of the final come back up after the play\n"
                        "length has faded them out. A round is the final when it\n"
                        "is named Finale, Final or Endrunde.")
        self._celebrate_mode = mode
        row.addWidget(mode)
        row.addSpacing(12)
        row.addWidget(QLabel("Level:"))
        pct = QSpinBox()
        pct.setRange(CELEBRATE_PCT_MIN, 100)
        pct.setSuffix(" %")
        pct.setValue(celebrate_pct(settings))
        pct.setToolTip("How loud it comes back, in % of the music's level.")
        self._celebrate_pct = pct
        row.addWidget(pct)
        row.addSpacing(12)
        row.addWidget(QLabel("Dip to:"))
        dip = QSpinBox()
        dip.setRange(0, 100)
        dip.setSuffix(" %")
        dip.setValue(celebrate_dip_pct(settings))
        dip.setToolTip("How low the play-length fade takes it before it comes\n"
                       "back up, in % of the music's level. 0 = all the way down.\n"
                       "At most the level it comes back at.")
        self._celebrate_dip = dip
        row.addWidget(dip)
        spins = []
        for caption, value, tip in (
                ("Hold:", celebrate_hold_secs(settings),
                 "How long it stays at its dip before it comes back up.\n"
                 "0 = it comes up at once."),
                ("Up over:", celebrate_up_secs(settings),
                 "How long it takes to come back up. 0 = at once."),
                ("Down over:", celebrate_down_secs(settings),
                 "How long it takes to go down when 🔉↓ fades it.")):
            row.addSpacing(12)
            row.addWidget(QLabel(caption))
            spin = QDoubleSpinBox()
            spin.setRange(0.0, CELEBRATE_MAX_SECS)
            spin.setDecimals(1)
            spin.setSingleStep(0.5)
            spin.setSuffix(" s")
            spin.setValue(value)
            spin.setToolTip(tip)
            row.addWidget(spin)
            spins.append(spin)
        self._celebrate_hold, self._celebrate_up, self._celebrate_down = spins
        row.addStretch(1)
        blyt.addLayout(row)

        def sync(*_):
            on = mode.currentData() != "off"
            for w in (pct, dip, *spins):
                w.setEnabled(on)
        mode.currentIndexChanged.connect(sync)
        sync()
        set_lyt.addWidget(box)

    def _add_pd_row(self, blyt, settings, which):
        """🐂 One set's Paso Doble: the highlight stop, which highlight, and
        the wait after the call."""
        pd = pd_of(settings, which)
        row = QHBoxLayout()
        stop = QCheckBox("🐂  Paso Doble: stop after highlight")
        stop.setChecked(pd["pd_stop"])
        if which == "tournament":
            stop.setToolTip("Shut the music off at the chosen highlight instead of\n"
                            "the play length. Off by default: a highlight detected\n"
                            "in the wrong bar cuts the heat short.")
        else:
            stop.setToolTip("Shut the music off at the chosen highlight instead of\n"
                            "the play length. On by default: at a party the\n"
                            "Paso Doble ends on its 2nd highlight.")
        row.addWidget(stop)
        n = QSpinBox()
        n.setRange(1, 3)
        n.setValue(pd["pd_n"])
        n.setToolTip("Which highlight ends the Paso Doble — usually the 2nd,\n"
                     "in rare cases the 3rd.")
        row.addWidget(n)
        row.addSpacing(12)
        row.addWidget(QLabel("Start after:"))
        delay = QSpinBox()
        delay.setRange(0, 60)
        delay.setSuffix(" s")
        delay.setValue(pd["pd_delay"])
        if which == "tournament":
            delay.setToolTip("Hold a Paso Doble back this long before the music\n"
                             "starts. 0 s = at once: at a competition the couples\n"
                             "stand before the music, the chairman's call is the wait.")
        else:
            delay.setToolTip("Hold a Paso Doble back this long before the music\n"
                             "starts, so the couples can take their position.")
        row.addWidget(delay)
        stop.toggled.connect(n.setEnabled)
        n.setEnabled(stop.isChecked())
        row.addStretch(1)
        blyt.addLayout(row)
        return stop, n, delay

    def _add_crossfade_controls(self, row, cur):
        """🔀 A play set's crossfade switch, seconds, curve and preview."""
        # 🔀 Its own switch, as on the panel: off keeps the seconds.
        xfade_on = QCheckBox("🔀  Crossfade:")
        xfade_on.setChecked(bool(cur["xfade_on"]))
        xfade_on.setToolTip("The next title comes in under the end of the\n"
                            "last one — only where the list walks on with\n"
                            "no pause. Off: one ends, the next starts.")
        row.addWidget(xfade_on)
        xfade = QDoubleSpinBox()
        xfade.setRange(XFADE_MIN_SECS, XFADE_MAX_SECS)
        xfade.setDecimals(1)
        xfade.setSingleStep(0.5)
        xfade.setSuffix(" s")
        xfade.setValue(float(cur["xfade"]))
        xfade.setToolTip(
            "How long the two titles play together — half-second steps")
        row.addWidget(xfade)
        curves = CrossfadeCurveButton()
        curves.set_curve(str(cur["xfade_curve"]))
        row.addWidget(curves)
        xfade_view = CrossfadeView()
        row.addWidget(xfade_view)

        def sync_xfade(*_, on=xfade_on, spin=xfade, curves=curves,
                       view=xfade_view):
            spin.setEnabled(on.isChecked())
            curves.setEnabled(on.isChecked())
            view.set_curve(curves.curve())
            view.set_secs(spin.value() if on.isChecked() else 0.0)
        xfade_on.toggled.connect(sync_xfade)
        xfade.valueChanged.connect(sync_xfade)
        curves.curveChanged.connect(sync_xfade)
        sync_xfade()
        return xfade_on, xfade, curves

    def _add_play_set_checks(self, blyt, cur):
        """A play set's switches (⏭ ⏸ 🔈 🔊 ▶️ ❓ 🎚), keyed by setting."""
        boxes = {}
        for key, label, tip in (
                ("advance", "⏭  Auto-advance to next song", ""),
                ("pause_off", "⏸  No pause between songs", ""),
                ("announce", "🔈  Announce next dance", ""),
                ("loudness", "🔊  Equalize volume (R128)", ""),
                ("dblclick", "▶️  Double-click starts the title",
                 "On: a double-click in a deck plays the title at once.\n"
                 "Off: it is only cued on the player (loaded, shown,\n"
                 "silent) and ⏯ starts it — the heat begins when the\n"
                 "couples stand."),
                ("dblclick_ask", "❓  Ask before a double-click stops the title",
                 "On: a double-click on another title while one is playing\n"
                 "asks first — No keeps the music on the floor.\n"
                 "Off: the new title takes over at once."),
                ("tso", "🎚  TSO pitch to the heat tempo",
                 "Pitch every title to the mean tempo of its dance in the\n"
                 "current round, kept inside the TSO range — what a heat is\n"
                 "danced to. Wrong for a party, where the next song is a\n"
                 "different dance at whatever tempo it was recorded at.")):
            # 🎚 TSO, or the WDSF CR outside the German terms.
            chk = QCheckBox(rules_name(i18n.t(label)))
            chk.setChecked(bool(cur[key]))
            if tip:
                chk.setToolTip(rules_name(i18n.t(tip)))
            blyt.addWidget(chk)
            boxes[key] = chk
        return boxes

    def _add_dance_len_grid(self, blyt, settings):
        """⏱ The 🏆 set's own play length per dance — a heat is timed per
        dance, a Viennese Waltz shorter than a Waltz — and a dance's length
        in one kind of round on top of it: equal in every heat of a round,
        free to change between rounds — a final Waltz at 2:00 — but nothing
        set is no change. A selector above picks which of the lists shows;
        every one of them counts, shown or not."""
        self._add_len_selector(blyt)
        self._dance_len_lbl = QLabel(
            "<b>⏱ Per dance</b> — a dance given a length of its own is cut "
            "there instead, as long as a list plays this set's length. The ▶ "
            "Playing panel names the dance under its length.")
        self._round_len_lbl = QLabel(
            "<b>⏱ Per round</b> — the lengths of one kind of round, every "
            "heat of it alike, on top of the per-dance ones. Left on “— the "
            "dance's length”, a dance runs its per-dance length in that "
            "round. One setting covers every intermediate round.")
        for lbl in (self._dance_len_lbl, self._round_len_lbl):
            lbl.setWordWrap(True)
            blyt.addWidget(lbl)
        dances = [d for d in ("LW", "TG", "WW", "SF", "QS",
                              "SA", "CC", "RB", "PD", "JI")
                  if d in TEMPO_RANGES]
        # Page 0 is the per-dance list, then one page per kind of round in
        # the order of the round combo.
        self._len_stack = QStackedWidget()
        page, self._dance_len_combos = self._len_page(
            dances, "— the set's length", dance_secs_of(settings),
            self._pd_len_combo(self._set_widgets["tournament"]["pd"]))
        self._len_stack.addWidget(page)
        stored = round_dance_secs_of(settings)
        stored_pd = round_pd_n_of(settings)
        self._round_len_combos: dict[tuple[str, str],
                                     tuple[QComboBox, int | None]] = {}
        self._round_pd_combos: dict[str, QComboBox] = {}
        for kind in ROUND_KINDS:
            self._round_pd_combos[kind] = self._pd_round_combo(
                "— the dance's length", stored_pd.get(kind))
            page, combos = self._len_page(dances, "— the dance's length",
                                          stored.get(kind, {}),
                                          self._round_pd_combos[kind])
            # The Paso Doble's pick is a highlight, not a length.
            combos.pop("PD", None)
            self._round_len_combos.update(
                {(kind, d): c for d, c in combos.items()})
            self._len_stack.addWidget(page)
        blyt.addWidget(self._len_stack)
        self._show_len_page()

    def _add_len_selector(self, blyt):
        """⏱ Per dance or per round, and which round: the list the grid
        below shows."""
        row = QHBoxLayout()
        self._len_scope_lbl = QLabel("⏱  Lengths:")
        row.addWidget(self._len_scope_lbl)
        self._len_scope_combo = QComboBox()
        self._len_scope_combo.addItem("Per dance — the standard", "dance")
        self._len_scope_combo.addItem("Per round — overrides it", "round")
        self._len_scope_combo.setToolTip(
            "Which lengths the list below shows. The per-dance ones are the "
            "standard; a round's own lengths override them in that kind of "
            "round. Both count, whichever is on screen.")
        row.addWidget(self._len_scope_combo)
        self._len_round_combo = QComboBox()
        heads = dict(zip(ROUND_KINDS, ("Vorrunde", "Zwischenrunde",
                                       "Semifinale", "Finale"), strict=True))
        for kind in ROUND_KINDS:
            self._len_round_combo.addItem(round_name(heads[kind]), kind)
        self._len_round_combo.setToolTip(
            "The kind of round whose lengths the list shows. Every "
            "intermediate round shares one.")
        row.addWidget(self._len_round_combo)
        row.addStretch(1)
        blyt.addLayout(row)
        self._len_scope_combo.currentIndexChanged.connect(self._show_len_page)
        self._len_round_combo.currentIndexChanged.connect(self._show_len_page)

    def _show_len_page(self, *_):
        """Show the list and the text the selector picks."""
        per_round = self._len_scope_combo.currentData() == "round"
        self._len_round_combo.setVisible(per_round)
        self._dance_len_lbl.setVisible(not per_round)
        self._round_len_lbl.setVisible(per_round)
        self._len_stack.setCurrentIndex(
            1 + self._len_round_combo.currentIndex() if per_round else 0)

    def _len_page(self, dances, unset, stored, pd_combo):
        """One list of the length grid: a length pick per dance, opened on
        `stored`, in two columns of five. The Paso Doble's is `pd_combo`:
        full or a highlight, never a time."""
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        combos: dict[str, tuple[QComboBox, int | None]] = {}
        for i, dance in enumerate(dances):
            secs = stored.get(dance)
            if dance == "PD":
                combo, secs = pd_combo, None
            else:
                combo = self._len_combo(unset, secs)
            combos[dance] = (combo, secs)
            row, col = i % 5, (i // 5) * 2
            grid.addWidget(QLabel(f"{dance_name(dance, dance)}:"), row, col)
            grid.addWidget(combo, row, col + 1)
        # The spare width goes to an empty column on the right: a stretched
        # combo stood 400 px wide for a length of four characters.
        grid.setColumnStretch(4, 1)
        return page, combos

    @staticmethod
    def _len_combo(unset: str, secs: int | None) -> QComboBox:
        """A length pick for the per-dance grids, opened on `secs`: `unset`
        (None) first, then full (0) and the 15 s rungs — typable, since
        1:37 is not a rung."""
        combo = QComboBox()
        combo.addItem(unset, None)
        combo.addItem("full", 0)
        for s in range(LEN_STEP, LEN_MAX + 1, LEN_STEP):
            combo.addItem(f"{s // 60}:{s % 60:02d}", s)
        # Typable like the set's own length: 1:37 is not a rung.
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setToolTip("Pick a length or type one: m:ss, seconds, "
                         "or 'full'")
        idx = combo.findData(secs) if secs is not None else 0
        if idx >= 0:
            combo.setCurrentIndex(idx)
        elif secs is not None:
            combo.setEditText(f"{secs // 60}:{secs % 60:02d}")
        return combo

    @staticmethod
    def _pd_combo() -> QComboBox:
        """🐂 A Paso Doble pick: full, or after its 1st or 2nd highlight — a
        timed cut would end it in the middle of a phrase, and the 3rd
        highlight is the music's end (Marcel: "3 = full")."""
        combo = QComboBox()
        # Its own width, as the other picks: narrower than theirs, the
        # grid's column would stretch it.
        combo.setSizePolicy(QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed)
        return combo

    @classmethod
    def _pd_round_combo(cls, unset: str, n: int | None) -> QComboBox:
        """🐂 The Paso Doble in one kind of round, opened on `n`: `unset`
        (None, the 🏆 set's highlight stop), full (0) or a highlight."""
        combo = cls._pd_combo()
        combo.addItem(unset, None)
        combo.addItem("full", 0)
        for k in (1, 2):
            combo.addItem(i18n.t("after highlight %d") % k, k)
        combo.setToolTip("Full, or stop after a highlight in this kind of "
                         "round — a final in full, a Vorrunde after the 2nd.")
        combo.setCurrentIndex(max(0, combo.findData(n)) if n is not None else 0)
        return combo

    @classmethod
    def _pd_len_combo(cls, pd) -> QComboBox:
        """🐂 The Paso Doble's per-dance pick, tied to the 🏆 set's highlight
        stop `pd`: a highlight ticks it and picks which, full unticks it. A
        3rd highlight in the set reads as full. Every pick is a full length
        (0): the highlight stop ends it."""
        combo = cls._pd_combo()
        combo.addItem("full", 0)
        for k in (1, 2):
            combo.addItem(i18n.t("after highlight %d") % k, 0)
        combo.setToolTip("Full, or stop after a highlight — the same as "
                         "🐂 Paso Doble: stop after highlight above.")
        stop, n, _delay = pd

        def from_set(*_):
            with QSignalBlocker(combo):
                combo.setCurrentIndex(n.value() if stop.isChecked()
                                      and n.value() < combo.count() else 0)

        def to_set(idx):
            if idx > 0:
                n.setValue(idx)
            stop.setChecked(idx > 0)
        from_set()
        stop.toggled.connect(from_set)
        n.valueChanged.connect(from_set)
        combo.currentIndexChanged.connect(to_set)
        return combo

    @staticmethod
    def _dance_len_secs(combo: QComboBox, opened: int | None) -> int | None:
        """One dance's length in the grid: None = the set's, 0 = full. An item
        picked or its caption typed comes first — "— the set's length" is
        not something the parser takes — then a typed length; anything else
        keeps the value the dialog opened on."""
        idx = combo.findText(combo.currentText().strip())
        if idx >= 0:
            return combo.itemData(idx)
        secs = parse_play_length(combo.currentText())
        return secs if secs is not None else opened

    def _add_tso_band_grid(self, tlyt, settings):
        """🎚 Which takt of its TSO band each dance is pitched to."""
        # ── 🎚 Where in its TSO band each dance is pitched ──
        tlyt.addWidget(hsep())
        band_lbl = QLabel(rules_name(i18n.t(
            "<b>🎚 TSO pitch target</b> — which takt the 🎚 button pitches a "
            "heat to. <i>Middle of the round</i> puts the round on one takt: "
            "the takt most of its titles are on where a step of one gets the "
            "rest there cheaply (T30+T31+T31 Cha-Chas → 31), the middle of "
            "its takte where it does not (T24+T25+T25 Rumbas → 24.5, "
            "T50+T52+T52 Quicksteps → 51). Nothing moves more than a takt. A fixed takt "
            "puts every title of that dance on the same tempo instead — worth "
            "setting on the slow dances, where one takt out of 24 is twice "
            "the pitch shift one takt out of 50 is.")))
        band_lbl.setWordWrap(True)
        tlyt.addWidget(band_lbl)

        stored_bands = settings.get("tso_band") or {}
        band_grid = QGridLayout()
        band_grid.setHorizontalSpacing(14)
        self._band_combos: dict[str, QComboBox] = {}
        dances = [d for d in ("LW", "TG", "WW", "SF", "QS",
                              "SA", "CC", "RB", "PD", "JI")
                  if d in TEMPO_RANGES]
        for i, dance in enumerate(dances):
            lo, hi = TEMPO_RANGES[dance]["S"]
            combo = QComboBox()
            combo.addItem("Middle of the round", TsoBand.MEAN)
            combo.addItem(i18n.t("Lower — T%s") % f"{lo:g}", TsoBand.LOWER)
            combo.addItem(i18n.t("Middle — T%s") % f"{(lo + hi) / 2:g}",
                          TsoBand.MIDDLE)
            combo.addItem(i18n.t("Upper — T%s") % f"{hi:g}", TsoBand.UPPER)
            idx = combo.findData(TsoBand.of(stored_bands.get(dance)))
            combo.setCurrentIndex(max(0, idx))
            # A Mac draws the popup button's frame past its size hint: at
            # exactly the hint its right edge was cut off.
            combo.setMinimumWidth(combo.sizeHint().width() + 10)
            self._band_combos[dance] = combo
            row, col = i % 5, (i // 5) * 2
            band_grid.addWidget(
                QLabel(f"{dance_name(dance, dance)}:"), row, col)
            band_grid.addWidget(combo, row, col + 1)
        # Spare width to an empty column, as in the per-dance lengths.
        band_grid.setColumnStretch(4, 1)
        tlyt.addLayout(band_grid)

    def _play_sets_values(self) -> dict:
        """The tab's settings, for values(): the pitch targets, the lengths
        per dance and per round, and the two sets."""
        vals = {}
        # Only the dances that are NOT on the heat mean: the default is what
        # the button does without the setting, and writing ten "mean" entries
        # would freeze today's default into the settings file.
        vals["tso_band"] = {d: c.currentData()
                            for d, c in self._band_combos.items()
                            if c.currentData() != TsoBand.MEAN}
        # Only the dances given a length of their own: the rest run on the set's.
        lens = {d: self._dance_len_secs(c, opened)
                for d, (c, opened) in self._dance_len_combos.items()}
        vals[DANCE_SECS_KEY] = {d: s for d, s in lens.items() if s is not None}
        # …and only the rounds given one: the rest run on the dance's length.
        rounds: dict[str, dict[str, int]] = {}
        for (kind, d), (c, opened) in self._round_len_combos.items():
            secs = self._dance_len_secs(c, opened)
            if secs is not None:
                rounds.setdefault(kind, {})[d] = secs
        vals[ROUND_DANCE_SECS_KEY] = rounds
        vals[ROUND_PD_KEY] = {kind: c.currentData()
                              for kind, c in self._round_pd_combos.items()
                              if c.currentData() is not None}
        vals["celebrate_mode"] = self._celebrate_mode.currentData()
        vals["celebrate_pct"] = self._celebrate_pct.value()
        vals["celebrate_dip_pct"] = self._celebrate_dip.value()
        vals["celebrate_hold_secs"] = self._celebrate_hold.value()
        vals["celebrate_up_secs"] = self._celebrate_up.value()
        vals["celebrate_down_secs"] = self._celebrate_down.value()
        for which, w in self._set_widgets.items():
            vals[f"{which}_set"] = dict(
                {k: chk.isChecked() for k, chk in w["boxes"].items()},
                secs=self._play_set_secs(w),
                fade=w["fade"].value(),
                xfade=w["xfade"].value(),
                xfade_on=w["xfade_on"].isChecked(),
                xfade_curve=w["xfade_curve"].curve())
            if "pd" in w:
                stop, n, delay = w["pd"]
                vals[f"{which}_set"].update(pd_stop=stop.isChecked(),
                                            pd_n=n.value(), pd_delay=delay.value())
        return vals

    @staticmethod
    def _play_set_secs(w) -> int:
        """The play length of one set: a rung picked, or a length typed in.

        The text is asked first because a typed one leaves the combo on no
        index at all; the picked item's data covers "full", whose caption
        spells out more than the parser will take."""
        secs = parse_play_length(w["length"].currentText())
        if secs is not None:
            return secs
        data = w["length"].currentData()
        # Neither parseable nor a rung: something was typed that is not a
        # length, and the value the dialog opened on stands.
        return int(data) if data is not None else int(w["secs"])
