"""Every list its own play values, and the 🎉 / 🏆 play sets that put them.

One player, several lists: the 🤸 party list runs full length and
hands-free while the tournament deck beside it cuts at 1:30 and is started
title by title. So the values a play set covers belong to the LIST — the
panel shows (and edits) those of the list last clicked, and playback runs
on those of the list that is playing, which need not be the same one.

Extracted from player/window/main_player.py as a MainWindow mixin.
"""
import logging
from typing import TYPE_CHECKING

from planner import i18n
from planner.playing.play_sets import (
    DANCE_SECS_KEY,
    ROUND_DANCE_SECS_KEY,
    XFADE_DEFAULT_SECS,
    dance_secs_of,
    dblclick_ask_of,
    pd_of,
    play_set_of,
    round_dance_secs_of,
    round_kind,
    round_pd_n_of,
    same_play_values,
    tso_of,
)
from planner.terms import dance_name, round_name, rules_name
from shared.stores import save_settings
from shared.widgets import show_toast

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.player")


# ⭐ A wishlist takes neither set: it holds requests and background music, so
# each title plays to its own end and nothing starts by itself — the next one
# is picked by hand. No voice and no TSO pitch either: these are songs, not a
# heat. A double-click plays at once, the way a request is answered.
_WISHLIST_VALS = {"secs": 0, "fade": 3.0, "fade_inside": True,
                  "advance": False, "pause_off": True,
                  "loudness": True, "announce": False, "dblclick": True,
                  "dblclick_ask": True, "xfade": XFADE_DEFAULT_SECS, "xfade_on": False,
                  "xfade_curve": "equal", "tso": False}

# 🐂 A list's own Paso Doble pick per kind of round, turned on the panel over
# the round's pick in ⚙ Settings: round kind → highlight.
ROUND_PD_OWN_KEY = "pd_round_n"

# A list's values the panel has no control for: 🎚 the TSO pitch sits on the
# player card, ❓ the double-click ask only in ⚙ Settings → 🎛 Play sets, and
# 🐂 the list's own round picks, which the spin shows only over their round.
OFF_PANEL_KEYS = ("tso", "dblclick_ask", ROUND_PD_OWN_KEY)


class PlayValuesMixin(MainWindowHost):
    """Per-list play values, the play panel bound to them, and the play sets."""

    def _panel_list(self):
        """The list whose values the play panel shows and edits. None on a desk
        with no lists, where the panel's own values are the only ones."""
        return getattr(self, "_panel_table", None)

    def _card_tso(self) -> bool:
        """The TSO pitch as the player card has it — it is not on the panel."""
        card = getattr(self, "_big_player", None)
        if card is not None:
            return bool(card.tso_mode())
        return bool(getattr(self, "_settings", {}).get("tso_equalize", True))

    def _list_vals(self, table) -> dict:
        """The play values ONE list runs with: `play_set()`'s keys plus
        `OFF_PANEL_KEYS`.

        A list is given them the first time anything asks, and never again
        behind the operator's back: the set of its kind — 🎉 party for the 🤸
        list, 🏆 tournament for every deck, the fixed `_WISHLIST_VALS` for a ⭐
        wishlist — or, for the list the panel was already standing on
        (start-up, a desk no list was ever bound to), what the panel shows.
        After that only a hand changes them: the panel while it shows this
        list, the ⏭/✋ in the list's corner, or 🎉/🏆."""
        if table._play_vals is None:
            panel_list = self._panel_list()
            settings = getattr(self, "_settings", {})
            kind = ("party" if table is self._deckset.warmup_table
                    else "tournament")
            if panel_list is None or table is panel_list:
                vals = self._play_panel.play_set()
                vals["tso"] = self._card_tso()
                vals["dblclick_ask"] = dblclick_ask_of(settings, kind)
            elif any(table is t for t in self._deckset.wishlists):
                vals = dict(_WISHLIST_VALS)
            else:
                vals = play_set_of(settings, kind)
                vals["tso"] = tso_of(settings, kind)
                vals["dblclick_ask"] = dblclick_ask_of(settings, kind)
            table._play_vals = vals
        return table._play_vals

    def _engine_list(self):
        """The list playback runs on: the one playing, else the one on the
        panel — which is then what the next ▶ will most likely start."""
        t, _row = self._playing_row()
        return t if t is not None else self._panel_list()

    def _pv(self, key: str):
        """One play value as playback has to obey it right now."""
        t = self._engine_list()
        if t is None:
            return self._play_panel.play_set()[key]
        return self._list_vals(t)[key]

    def _play_limit_secs(self) -> int:
        """Seconds per title for the playing list, 0 = to the track's own end —
        the 🏆 set's own length for the title's dance, where it has one."""
        if self._closing_on_air():
            return 0   # 🌙 the closing song plays to its end
        playing, row = self._playing_row()
        rnd = playing.round_at(row) if playing is not None else ""
        own = self._dance_secs(self._engine_list(), self._playback.dance, rnd)
        return own if own is not None else int(self._pv("secs"))

    def _play_end_secs(self) -> float:
        """Seconds of music until the timed cut, 0 = none: the play length,
        or — with the fade-out set to come after it — the length plus the
        fade, so the title is heard in full before it ramps down."""
        limit = self._play_limit_secs()
        if limit > 0 and not self._pv("fade_inside"):
            return limit + float(self._pv("fade"))
        return limit

    def _on_tournament_length(self, table) -> bool:
        """Whether `table` (None: the panel) plays the 🏆 set's length — the
        only place the set's per-dance lengths count. A length nudged by hand
        takes a list off them, and then its one length is every dance's. ⏭,
        the pause and the rest are how a list walks on, not how long a title
        runs: a Vorrunde on ⏭ Auto cut every dance at the set's 1:45."""
        vals = (self._play_panel.play_set() if table is None
                else self._list_vals(table))
        return vals.get("secs") == play_set_of(self._settings, "tournament")["secs"]

    def _round_secs(self, dance: str, round_name: str) -> int | None:
        """The 🏆 set's length for `dance` in rounds like `round_name` (0 =
        full), or None where that round runs on the dance's own length."""
        kind = round_kind(round_name)
        if kind is None:
            return None
        return round_dance_secs_of(self._settings).get(kind, {}).get(dance)

    def _pd_highlight(self) -> tuple[bool, int]:
        """🐂 (stop, which highlight) for the Paso Doble playing: its round's
        pick while the list plays the 🏆 set's length, like the per-round
        lengths — a final in full, a Vorrunde after the 2nd — else the
        panel's highlight stop."""
        p = self._play_panel
        playing, row = self._playing_row()
        n = self._round_pd(self._engine_list(),
                           playing.round_at(row) if playing is not None else "")
        if n is None:
            return p.pd_highlight_stop(), p.pd_highlight_n()
        return n > 0, n or p.pd_highlight_n()

    def _round_pd(self, table, rnd: str) -> int | None:
        """🐂 The Paso Doble pick for rounds like `rnd` on `table` while it
        plays the 🏆 set's length: the list's own, turned on the panel, else
        the round's in ⚙ Settings (0 = in full). None where the round has no
        pick or the list another length — the panel's own stop decides."""
        kind = round_kind(rnd)
        n = round_pd_n_of(self._settings).get(kind) if kind else None
        if n is None or not self._on_tournament_length(table):
            return None
        if table is not None:
            own = self._list_vals(table).get(ROUND_PD_OWN_KEY)
            if isinstance(own, dict) and isinstance(own.get(kind), int):
                return own[kind]
        return n

    def _on_round_pd_picked(self, n: int) -> None:
        """🐂 The spin turned while it showed the round's pick: the list on
        the panel stops after highlight `n` in rounds of that kind — that list
        alone. Marcel: "it should still be able to be overwriten". Back on
        the round's own pick, the list follows the round again."""
        table = self._panel_list()
        _dance, rnd = self._slot_in_focus(table)
        kind = round_kind(rnd)
        pick = round_pd_n_of(self._settings).get(kind) if kind else None
        if table is None or kind is None or pick is None:
            return
        vals = self._list_vals(table)
        own = dict(vals.get(ROUND_PD_OWN_KEY) or {})
        if int(n) == (pick or 3):
            own.pop(kind, None)
        else:
            own[kind] = int(n)
        vals[ROUND_PD_OWN_KEY] = own
        self._autosave_playlist()

    def _dance_secs(self, table, dance: str, round_name: str = "") -> int | None:
        """The 🏆 set's own length for `dance` on `table` (0 = full) — its
        length in `round_name`'s kind of round first — or None where the
        list's one length applies."""
        if not dance:
            return None
        own = self._round_secs(dance, round_name)
        if own is None:
            own = dance_secs_of(self._settings).get(dance)
        if own is None or not self._on_tournament_length(table):
            return None
        return own

    def _slot_in_focus(self, table) -> tuple[str, str]:
        """(dance, round) the panel's length is about: the title playing from
        the list on the panel, else the row picked in it — what ▶ starts next."""
        playing, row = self._playing_row()
        if self._playback.path is not None and (playing is table or table is None):
            return (self._playback.dance,
                    playing.round_at(row) if playing is not None else "")
        if table is None:
            return "", ""
        row = table.currentRow()
        meta = table._row_meta.at(row)
        return (meta.dance, table.round_at(row)) if meta is not None else ("", "")

    def _sync_dance_len(self) -> None:
        """Show on the panel which length is valid right now: the dance's own
        from the 🏆 set, named under the digits — with the round, where the
        round has its own — or the list's one length."""
        table = self._panel_list()
        dance, rnd = self._slot_in_focus(table)
        own = self._dance_secs(table, dance, rnd)
        name = dance_name(dance, dance) if own is not None else ""
        if name and self._round_secs(dance, rnd) is not None:
            name = f"{name}, {round_name(rnd)}"
        # 🥇 Only about the title playing: what comes after its cut.
        playing, _row = self._playing_row()
        plays_on = (self._playback.path is not None
                    and (playing is table or table is None)
                    and self._celebration_due())
        self._play_panel.set_dance_len(
            dance if own is not None else "", name, own, plays_on)
        self._sync_round_pd(table, dance, rnd)

    def _sync_round_pd(self, table, dance: str, rnd: str) -> None:
        """🐂 Show on the panel the round's own Paso Doble pick, where it is
        the one `_pd_highlight` stops on — a final in full, a Vorrunde after
        the 2nd — else the panel's own number again."""
        n = self._round_pd(table, rnd) if dance == "PD" else None
        if n is None:
            self._play_panel.set_round_pd_n(None)
            return
        self._play_panel.set_round_pd_n(n, round_name(rnd))

    def _on_dance_len_changed(self, dance: str, secs: int) -> None:
        """−/+ or a typed length on the panel while it shows a dance's own
        length: that is the 🏆 set's value for the dance, in ⚙ Settings —
        its value for the round in focus, where that round has one."""
        _dance, rnd = self._slot_in_focus(self._panel_list())
        if self._round_secs(dance, rnd) is not None:
            rounds = round_dance_secs_of(self._settings)
            rounds[str(round_kind(rnd))][dance] = int(secs)
            self._settings[ROUND_DANCE_SECS_KEY] = rounds
            save_settings(self._settings)
            log.info("⏱️ Round dance play length set\n"
                     "round: %s\n"
                     "dance: %s\n"
                     "secs: %s", rnd, dance, secs)
            self._sync_big_player_limit()
            return
        # From the read side, so a fresh install keeps the shipped lengths of
        # the other dances beside this one.
        stored = dance_secs_of(self._settings)
        stored[dance] = int(secs)
        self._settings[DANCE_SECS_KEY] = stored
        save_settings(self._settings)
        log.info("⏱️ Dance play length set\n"
                 "dance: %s\n"
                 "secs: %s", dance, secs)
        self._sync_big_player_limit()

    def _engine_pause_secs(self) -> int:
        """The between-titles pause for the playing list: the panel's seconds
        (they are global), 0 where this list has the pause switched off."""
        return 0 if self._pv("pause_off") else self._play_panel.pause_setting_secs()

    def _engine_pause_available(self) -> bool:
        """Whether a pause can happen at all — only a list that walks on has
        a gap to put one in."""
        return bool(self._playing_advance() and not self._pv("pause_off"))

    def _configured_play_secs(self, table=None, dance: str = "",
                              round_name: str = "") -> int:
        """Play length a deck's ⏱ column flags short tracks against (0 = off)
        — that deck's own, where it is given, and the 🏆 set's for `dance`
        in `round_name` while the deck stands on it."""
        if table is not None:
            own = self._dance_secs(table, dance, round_name)
            return own if own is not None else int(self._list_vals(table)["secs"])
        return self._play_limit_secs()

    def _bind_panel(self, table) -> None:
        """A list was clicked: the panel now shows ITS values, and edits there
        go into it. Nothing is written into the list by the switch itself."""
        if table is None or table is self._panel_list():
            return
        vals = self._list_vals(table)
        self._panel_table = table
        self._binding_panel = True
        try:
            changed = self._play_panel.apply_play_set(
                **{k: v for k, v in vals.items() if k not in OFF_PANEL_KEYS})
        finally:
            self._binding_panel = False
        # The TSO toggle sits on the player card, which serves the list that
        # is playing — it follows the click only while nothing plays.
        if self._playing_row()[0] is None:
            if bool(vals["tso"]) != self._card_tso():
                changed.append(rules_name(
                    i18n.t("TSO tempo equalize → on") if vals["tso"]
                    else i18n.t("TSO tempo equalize → off"), short=True))
            self._sync_card_tso(vals["tso"], table)
        self._refresh_set_lights()
        self._sync_dance_len()
        # Other values on the panel get the toast 🎉/🏆 get. Not while the
        # window is not up: start-up binds the panel too, and nobody clicked.
        if changed and self.isVisible():
            show_toast(self, self._list_set_head(table)
                        + "\n" + "\n".join(changed), 4000)

    def _list_set_head(self, table) -> str:
        """The toast's first line for a list the panel switched to: the set
        it stands on, or that it has values of its own."""
        name = self.deck(table).title
        if self._on_play_set("party"):
            return i18n.t("🎉  Party set — %s") % name
        if self._on_play_set("tournament"):
            return i18n.t("🏆  Tournament set — %s") % name
        return i18n.t("🎚  Own settings — %s") % name

    def _sync_card_tso(self, want: bool, table=None) -> None:
        """Move the card's TSO toggle for `table`. Its signal stores the value
        into a list — this one, named here because while a title is only just
        starting the playing row is not marked yet."""
        card = getattr(self, "_big_player", None)
        if card is None or bool(want) == card.tso_mode():
            return
        self._tso_list = table
        try:
            card.set_tso_mode(bool(want))
        finally:
            self._tso_list = None

    def _store_panel_into_list(self) -> None:
        """The panel moved (by hand or by 🎉/🏆): write it into its list."""
        t = self._panel_list()
        if t is None or getattr(self, "_binding_panel", False):
            return
        vals = self._list_vals(t)
        new = self._play_panel.play_set()
        if any(vals.get(k) != v for k, v in new.items()):
            vals.update(new)
            self._autosave_playlist()

    def _deck_advance(self, table) -> bool:
        """⏭ Auto / ✋ Manual as it stands for ONE list."""
        if table is None:
            return self._play_panel.auto_advance()
        return bool(self._list_vals(table)["advance"])

    def _playing_advance(self) -> bool:
        """…for the list the evening is on right now (see `_engine_list`)."""
        return self._deck_advance(self._engine_list())

    def _set_deck_advance(self, table, on: bool):
        """⏭/✋ in a list's corner was clicked: it is that list's own value, so
        the panel follows only when it is showing this very list."""
        self._list_vals(table)["advance"] = bool(on)
        if table is self._panel_list():
            self._play_panel.advance_check.setChecked(bool(on))
        table.refresh_advance_toggle()
        self._autosave_playlist()

    def _wire_advance_switch(self):
        """Repaint the corner switch when the panel's ⏭ moves — it is the same
        value whenever the panel shows that list."""
        self._play_panel.advance_check.toggled.connect(
            lambda _: self._refresh_advance_toggles())

    def _refresh_advance_toggles(self):
        """Repaint the corner switch on every list."""
        # getattr: the panel exists before the decks do, and a play set applied
        # during start-up flips this switch before there is anything to repaint.
        for t in self._deckset.all_tables:
            t.refresh_advance_toggle()

    def _set_party_tso(self, want) -> list[str]:
        """Put the TSO pitch where the set wants it, for the list on the panel
        (None = leave alone, for a set saved before TSO joined it). Reports
        like the panel does.

        TSO pitches every title to the heat's mean tempo — right for a round of
        Quicksteps, wrong for a party, where the next song is a different dance
        at whatever tempo it was recorded. The toggle itself sits on the player
        card and serves the list that plays, so it only moves when that is the
        list the set was applied to."""
        if want is None:
            return []
        t = self._panel_list()
        was = self._list_vals(t)["tso"] if t is not None else self._card_tso()
        if t is not None:
            self._list_vals(t)["tso"] = bool(want)
        if t is None or t is self._engine_list():
            if self._big_player is None:
                return []
            self._sync_card_tso(want, t)
            self._settings["tso_equalize"] = bool(want)
        if bool(was) == bool(want):
            return []
        return [rules_name(i18n.t("TSO tempo equalize → on") if want
                           else i18n.t("TSO tempo equalize → off"), short=True)]

    def _set_list_ask(self, want: bool) -> list[str]:
        """❓ Put the double-click ask into the list on the panel and report
        it when it moved. No list on the panel: nothing to put it in."""
        t = self._panel_list()
        if t is None:
            return []
        vals = self._list_vals(t)
        if vals.get("dblclick_ask", True) == want:
            return []
        vals["dblclick_ask"] = want
        return [i18n.t("double-click → asks before it stops a title") if want
                else i18n.t("double-click → stops a title without asking")]

    def _set_set_pd(self, which: str) -> list[str]:
        """🐂 Put the panel's Paso Doble on the 🎉 party / 🏆 tournament set's
        own values (`pd_of`) and report what moved. A party stops after the
        2nd highlight and waits 3 s by default, a heat neither. The list's
        own round picks go: each round stops on its own pick again."""
        pd = pd_of(self._settings, which)
        table = self._panel_list()
        dropped: list[str] = []
        if table is not None and self._list_vals(table).pop(ROUND_PD_OWN_KEY, None):
            dropped = [i18n.t("🐂 Paso Doble → each round's own pick")]
        return dropped + (self._play_panel.set_pd_highlight_stop(pd["pd_stop"])
                          + self._play_panel.set_pd_highlight_n(pd["pd_n"])
                          + self._play_panel.set_pd_start_delay(pd["pd_delay"]))

    def _on_play_set(self, which: str) -> bool:
        """Is the panel standing on the 🎉 party / 🏆 tournament set right now?

        The TSO pitch is not part of the answer: its toggle sits on the player
        card, so neither `play_set()` nor `play_set_of` carries it."""
        return same_play_values(self._play_panel.play_set(),
                                play_set_of(self._settings, which))

    def _refresh_set_lights(self) -> None:
        """Light the button of the set the panel is standing ON — every time a
        control moves, whoever moved it.

        Both tooltips have always promised exactly this ("lit gold while the
        panel stands on those values"), but the lights used to be set when a
        set was applied and then left alone, so they went on reporting the last
        button pressed while the values underneath them were nudged by hand.
        Both dark is an answer too: the panel is on the operator's own values.
        """
        party = self._on_play_set("party")
        self._play_panel.set_party_on(party)
        if not party:
            self._play_panel.set_tournament_on(self._on_play_set("tournament"))

    def _put_set_on(self, which: str) -> list[str]:
        """Put the list on the panel on the 🎉 party / 🏆 tournament set —
        panel values, TSO pitch, ❓ ask and 🐂 Paso Doble — and report it."""
        changed = self._play_panel.apply_play_set(
            **play_set_of(self._settings, which))
        changed += self._set_party_tso(tso_of(self._settings, which))
        changed += self._set_list_ask(dblclick_ask_of(self._settings, which))
        changed += self._set_set_pd(which)
        return changed

    def _follow_play_sets(self, old: dict, new: dict) -> None:
        """⚙ Settings saved: every list moves along with its set — each value
        still equal to the set's OLD one is the set's and takes the new one, a
        value changed by hand stays. Marcel: a list played before the play
        time was changed "still applies the old logic" — its copy kept the old
        length, fell off the 🏆 set and so off the per-dance lengths. The
        panel's 🐂 Paso Doble follows the set of the list it shows."""
        def whole(settings, which):
            return dict(play_set_of(settings, which),
                        tso=tso_of(settings, which),
                        dblclick_ask=dblclick_ask_of(settings, which))

        warmup = self._deckset.warmup_table
        for t in self._deckset.all_tables:
            if t._play_vals is None or any(t is w for w in self._deckset.wishlists):
                continue
            which = "party" if t is warmup else "tournament"
            before, after = whole(old, which), whole(new, which)
            for k, v in before.items():
                if t._play_vals.get(k) == v:
                    t._play_vals[k] = after[k]
            t.refresh_advance_toggle()
        p = self._play_panel
        which = "party" if self._panel_list() is warmup else "tournament"
        before, after = pd_of(old, which), pd_of(new, which)
        if p.pd_highlight_stop() == before["pd_stop"]:
            p.set_pd_highlight_stop(after["pd_stop"])
        if p.pd_highlight_n() == before["pd_n"]:
            p.set_pd_highlight_n(after["pd_n"])
        if p.pd_start_delay() == before["pd_delay"]:
            p.set_pd_start_delay(after["pd_delay"])
        panel_list = self._panel_list()
        if panel_list is not None:
            self._panel_table = None
            self._bind_panel(panel_list)

    def _remember_before_set(self) -> None:
        """Keep what the list on the panel stands on right before a set is
        pressed, for the way back when that set is clicked off again.

        Kept on the list (on the panel when the desk has none), and only in
        memory: a snapshot that outlived the evening is how secs 15 with
        announcements once came back onto the panel at every round's start."""
        t = self._panel_list()
        p = self._play_panel
        before = dict(p.play_set(), pd_stop=p.pd_highlight_stop(),
                      pd_n=p.pd_highlight_n(), pd_delay=p.pd_start_delay())
        if t is None:
            before["tso"] = self._card_tso()
            p._before_set = before
            return
        vals = self._list_vals(t)
        before.update(tso=vals["tso"],
                      dblclick_ask=vals.get("dblclick_ask", True))
        t._before_set = before

    def _leave_set(self, which: str) -> None:
        """The lit 🎉 / 🏆 was clicked: switch that set off by putting the list
        back on what it had before the set was pressed. With nothing kept
        (the list started out on the set) the set stays on — applied again,
        so the pitch, ❓ and 🐂 beside it are where it wants them."""
        t = self._panel_list()
        owner = t if t is not None else self._play_panel
        before = getattr(owner, "_before_set", None)
        if before is None:
            changed = self._put_set_on(which)
            head = (i18n.t("🎉  Party set stays on — no earlier values to go back to")
                    if which == "party" else
                    i18n.t("🏆  Tournament set stays on — no earlier values to go back to"))
            lines = [i18n.t("change a value by hand, or press the other set")]
            self._report_set(head, lines + changed)
            return
        owner._before_set = None
        p = self._play_panel
        changed = p.apply_play_set(**{k: before[k] for k in p.play_set()})
        changed += self._set_party_tso(before["tso"])
        if "dblclick_ask" in before:
            changed += self._set_list_ask(before["dblclick_ask"])
        changed += (p.set_pd_highlight_stop(before["pd_stop"])
                    + p.set_pd_highlight_n(before["pd_n"])
                    + p.set_pd_start_delay(before["pd_delay"]))
        head = (i18n.t("🎉  Party set off — earlier values back")
                if which == "party" else
                i18n.t("🏆  Tournament set off — earlier values back"))
        self._report_set(head, changed or [i18n.t("nothing to change")])

    def _report_set(self, head: str, lines: list[str]) -> None:
        """After a set button: relight, save and say what changed."""
        self._refresh_set_lights()
        self._save_play_settings()
        show_toast(self, head + "\n" + "\n".join(lines), 4000)
        log.info("%s\n"
                 "changed: %s", head, lines)

    def _set_party_mode(self, on: bool) -> None:
        """🎉 clicked: put the list on the panel on the party settings (full
        length, auto-advance, no pause, equalized volume, TSO off, the 🐂
        Paso Doble stopped after its 2nd highlight, 3 s late) — or, when
        the lit button is clicked off, back on what it had before — and say so.

        Only a hand does this, and only to the list on the panel. Switching
        lists used to re-apply the set of the list's kind on every title, which
        undid a play length nudged between two heats (1:55 came back as 1:40
        after one party song); a list now keeps what it was given."""
        if not on:
            self._leave_set("party")
            return
        if not self._on_play_set("party"):
            self._remember_before_set()
        changed = self._put_set_on("party")
        self._report_set(i18n.t("🎉  Party set applied"),
                         changed or [i18n.t("nothing to change")])

    def _apply_tournament_set(self):
        """🏆 button: put the list on the panel on the competition values and
        say so — or, pressed while lit, switch the set off again and go back
        to what the list had before (`_leave_set`).

        🐂 The Paso Doble takes the set's own values (`pd_of`): by default
        the highlight stop goes off — the detection is not good enough yet to
        cut a competition Paso Doble on, and a heat stopped in the wrong bar
        is danced twice — and 'Start after' goes to 0 s: at a competition the
        couples stand before the music, the chairman's call is the wait.
        """
        if self._on_play_set("tournament"):
            self._leave_set("tournament")
            return
        self._remember_before_set()
        changed = self._put_set_on("tournament")
        self._report_set(i18n.t("🏆  Tournament set applied"),
                         changed or [i18n.t("nothing to change")])

    def _on_list_play(self, table) -> None:
        """A title started from `table`: playback now runs on that list's own
        values. Nothing is applied TO the list — it keeps what it was given —
        but the player card serves the list that plays, so its TSO toggle and
        its ⏸♪ button take this list's answers."""
        if table is None:
            return
        vals = self._list_vals(table)
        for t in self._deckset.all_tables:
            t.set_advance_live(t is table)
        self._sync_card_tso(vals["tso"], table)
        if self._big_player is not None:
            self._big_player.set_pause_available(
                bool(vals["advance"] and not vals["pause_off"]))
        self._sync_dance_len()
