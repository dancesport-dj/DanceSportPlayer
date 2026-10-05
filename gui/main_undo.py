"""↶ Undo / redo over whole autosave environments, and saying what changed.

Split off gui/main_persist.py as a MainWindow mixin. An undo step is a complete
state, so what the operator gets told — "3 tracks moved", the rows flashing —
has to be worked out by comparing two of them. What is IN such a state, and how
two of them differ, is gui.session_env's; what is left here is the timeline and
the widgets it tints.
"""
import logging

from collections import Counter
from shared.widgets import (
    _show_toast,
)
from gui.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from gui.session_env import (
    ALL_DECK_KEYS,
    SessionEnv,
    WISH_KEYS,
    deck_paths,
    deck_slots,
)
from planner import i18n

log = logging.getLogger("dancesport.gui.undo")


class UndoMixin:
    """↶ The undo/redo stack and the change description it shows."""

    # ----- undo / redo --------------------------------------------------------
    def _push_undo(self, env: dict):
        """Record a fresh snapshot on the undo timeline, discarding any redo branch."""
        if self._undo_timeline.push(env):
            self._update_undo_actions()

    def _seed_undo_baseline(self):
        """Set the initial snapshot after the session's playlist is restored, so the
        very first edit is undoable back to this baseline."""
        self._undo_timeline.seed(self._build_env())
        self._update_undo_actions()

    def _undo(self):
        step = self._undo_timeline.undo()
        if step is None:
            _show_toast(self, "↶  Nothing to undo")
            return
        self._show_step(i18n.t("↶  Undo — %s"), *step)

    def _redo(self):
        step = self._undo_timeline.redo()
        if step is None:
            _show_toast(self, "↷  Nothing to redo")
            return
        self._show_step(i18n.t("↷  Redo — %s"), *step)

    def _show_step(self, template: str, before: dict | None, after: dict):
        """Put the state an undo/redo step landed on into the window and say
        what it changed."""
        self._apply_env(after)
        self._flash_changed(before, after)
        msg = template % self._describe_env_change(before, after)
        self.statusBar().showMessage(msg)
        _show_toast(self, msg)
        self._update_undo_actions()

    def _describe_env_change(self, before: dict | None,
                             after: dict | None) -> str:
        """What an undo/redo step did, in words, for the toast + button tooltip."""
        return SessionEnv(after).describe_change_from(SessionEnv(before))

    def _flash_new_rows(self, table: PlaylistTable, before_paths: list[str],
                        before_slots: dict[tuple[str, str, str], str] | None = None,
                        positional: bool = False):
        """Tint the rows whose track wasn't present (at that multiplicity) before —
        i.e. the songs this undo/redo just added or replaced in `table` — plus, when
        `before_slots` / `positional` is given, rows whose track merely MOVED to a
        different grid slot / list position (so reorders and swaps flash too)."""
        bc = Counter(before_paths)
        rows = []
        pos = 0   # position among entry rows (for order-based lists)
        for row, m in enumerate(table._row_meta):
            if not m or m.entry is None:
                continue
            e = m.entry
            p = str(e.path) if e.path else None
            if p is None:
                continue
            moved = False
            if positional:
                moved = pos >= len(before_paths) or before_paths[pos] != p
                pos += 1
            elif (before_slots is not None and not m.backup
                  and not m.theme and m.round_name is not None):
                slot = (str(m.round_name), str(m.h_idx), str(m.d_idx))
                moved = before_slots.get(slot) != p
            if bc.get(p, 0) > 0:
                bc[p] -= 1          # a copy that already existed → flash only if moved
                if moved:
                    rows.append(row)
            else:
                rows.append(row)    # new / replaced song → highlight it
        table.flash_rows(rows)

    def _flash_changed(self, before: dict | None, after: dict | None):
        """After an undo/redo, highlight the changed songs in each visible deck +
        wishlist + the Eintanzen panel so the user sees exactly what the step altered."""
        if not after:
            return
        for key, table in zip(ALL_DECK_KEYS, self._decks + self._day_decks):
            if not table.isVisible():
                continue
            denv = (before or {}).get(key)
            self._flash_new_rows(table, deck_paths(denv),
                                 before_slots=deck_slots(denv),
                                 positional=(denv or {}).get("mode") == "Theme")
        for key, table in zip(WISH_KEYS, self._wishlists):
            if not table.isVisible():
                continue
            before_paths = [p for p in ((before or {}).get(key) or []) if p]
            self._flash_new_rows(table, before_paths, positional=True)
        wt = getattr(self, "_warmup_table", None)
        if wt is not None and wt.isVisible():
            before_paths = [p for p in (((before or {}).get("warmup") or {}).get("paths") or []) if p]
            self._flash_new_rows(wt, before_paths, positional=True)

    def _update_undo_actions(self):
        """Sync the ↶/↷ buttons: show the step count + tooltip, and enable/disable so
        it's obvious whether an undo / redo is currently possible."""
        timeline = self._undo_timeline
        n_undo = timeline.undo_count
        n_redo = timeline.redo_count
        btn = getattr(self, "_undo_btn", None)
        if btn is not None:
            btn.setEnabled(n_undo > 0)
            btn.setText(f"↶ {n_undo}" if n_undo else "↶")
            if n_undo:
                desc = self._describe_env_change(timeline.current, timeline.next_undo())
                btn.setToolTip(i18n.t("Undo: %s\n%s step(s) available  ·  Ctrl+Z")
                               % (desc, n_undo))
            else:
                btn.setToolTip("Nothing to undo yet")
        btn = getattr(self, "_redo_btn", None)
        if btn is not None:
            btn.setEnabled(n_redo > 0)
            btn.setText(f"↷ {n_redo}" if n_redo else "↷")
            if n_redo:
                desc = self._describe_env_change(timeline.current, timeline.next_redo())
                btn.setToolTip(i18n.t("Redo: %s\n%s step(s) available  ·  Ctrl+Y")
                               % (desc, n_redo))
            else:
                btn.setToolTip("Nothing to redo")
