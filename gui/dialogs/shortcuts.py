"""❔ F1 — the cheat sheet of every keyboard shortcut and mouse trick.

Split off the main window, which only opens it: the rows, the table they are
glued into and the dialog showing it need nothing of the window.
"""
import html

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout

from planner import i18n
from planner.playing import controller as pctl


def _desk_key_rows(saved) -> tuple:
    """⌨ The desk keys as they are bound now (planner.playing.controller),
    an action's keys on one row."""
    labels = dict(pctl.ACTIONS)
    return tuple(("  /  ".join(pctl.key_text(k) for k in keys), labels[action])
                 for action, keys in pctl.desk_keys(saved).items() if keys)


def shortcut_rows(desk_keys=None):
    """Every line of the cheat sheet — a row with no right half is a
    section heading. Both halves are catalog keys; `setHtml` cannot be
    patched for them, so `shortcut_sheet_html` translates them itself.
    `desk_keys` is the setting of that name (None: the defaults)."""
    return (
        ("⌨  Keyboard", ""),
        ("Space", "Play / stop the selected song"),
        ("Enter", "Play / stop the selected song — in Playing mode also in "
                  "the list playing, where Space pauses the player"),
        ("Ctrl + ← / →", "Seek 30 s back / forward while playing"),
        *_desk_key_rows(desk_keys),
        ("Ctrl + R  or  Ctrl + N", "Re-roll (regenerate) the selected song"),
        ("Ctrl + S", "Save the focused playlist / wishlist as M3U"),
        ("Ctrl + Shift + S", "Save the whole session state (decks, wishlists, layout)"),
        ("Ctrl + Z  /  Ctrl + Y", "Undo / redo (also Ctrl + Shift + Z)"),
        ("Ctrl + X  or  Ctrl + W", "Close the active dialog or the preview "
                                   "mini player"),
        ("Del", "Remove the selected rows (wishlist) / empty the selected "
                "heat slots (deck)"),
        ("Del  with nothing selected", "Clear that whole playlist / wishlist "
                                       "(confirmed) — same when every song is "
                                       "selected at once"),
        ("Ctrl + Shift + Del", "Clear the focused playlist / wishlist "
                               "(confirmed), wherever the cursor is"),
        ("Ctrl + Del", "Dynamic deck: remove the whole heat under the cursor "
                       "(on a ↳ backup row: just that backup)"),
        ("Ctrl + M", "Dynamic deck or free running order: mark / unmark the "
                     "selected song(s) for potential replace (❗ orange). "
                     "Ctrl + 1 does the same, but only while the 🎛 cartwall "
                     "is hidden — the wall claims that key for its first pad"),
        ("Alt + S", "Warm-up list: swap the two selected titles of one dance"),
        ("F2  in the 📅 tournament tree", "Rename the entry under the cursor "
                                          "(Del removes it)"),
        ("Ctrl + A  in 🏆 Tournaments", "Mark every slot of the folder, or "
                                       "every entry of the tree — Del and a "
                                       "drag then take them all"),
        ("Ctrl + F", "Find a title or a genre in the focused list. A title steps "
                     "to the next match; a genre highlights every row of it at once"),
        ("Esc  in the 🖥 presenter window", "Close the presenter screen"),
        ("F12  /  Ctrl + Alt + S", "Open ⚙ Settings"),
        ("F1", "This cheat sheet"),
        ("F11", "Fullscreen on / off — with date and time in the status bar"),
        ("🖱  Mouse", ""),
        ("Click a round / dance header", "Collapse or expand that section"),
        ("Double-click a deck title", "Rename the playlist / wishlist"),
        ("▾ / ▸ arrow in a deck header", "Fold the deck to a header tab "
                                         "(click the tab to reopen)"),
        ("Drag a row", "Move a song to another slot, deck, wishlist — or "
                       "drop it into Explorer / UltraMixer"),
        ("Drag a dance header", "Reorder the dance columns of a static deck"),
        ("Right-click ▸ 🔍 Find a genre", "Jump to a song by name; or highlight "
                                          "every row of a genre at once"),
        ("Ctrl + drag onto a filled slot", "Dynamic deck: replace the song in "
                                           "that slot with the dragged one"),
        ("Drop a file from outside", "Replace a slot / add to a wishlist "
                                     "(.m3u on a deck imports it)"),
        ("▶ or Space on a 📚 library row", "Preview that track in the "
                                          "mini player"),
        ("Double-click a 📚 library row", "Open the track in your external "
                                          "audio player — when ⚙ Settings → "
                                          "🔊 Sound & player allow it"),
        ("▶ / ■ in a row", "Play / stop exactly that song"),
        ("Click a star in the ★ column", "Rate the title; click the star the "
                                         "rating ends on to clear it"),
        ("↺ in a row / header", "Re-roll that song / every song of the "
                                "dance or round"),
        ("🎛  Cartwall", ""),
        ("Drop files on a pad", "Assign that sample — a multi-select fills "
                                "the free pads after it (an empty pad can "
                                "also be clicked to browse)"),
        ("Click a pad", "Fire it over the running music; click again to "
                        "fade it out"),
        ("Ctrl+1 … Ctrl+9", "Fire the first nine pads of the page on screen "
                            "(works from anywhere while the wall is shown, "
                            "and takes Ctrl + 1 away from the mark shortcut "
                            "above)"),
        ("Right-click a pad", "🎨 colour straight away, or Settings… for "
                              "label, volume, its own key, 🔁 endless "
                              "repeat and whether it ducks the music"),
        ("Drag a pad onto another", "Swap the two pads"),
        ("Esc", "Stop every pad (same as ⏹ Stop all)"),
    )


def _key_t(left: str) -> str:
    """A key name in the app's language. A desk key the operator chose has
    no catalog entry of its own, so it is translated part by part — each of
    an action's keys, then each key's parts."""
    text = i18n.t(left)
    if text == left and " + " in left:
        text = "  /  ".join(" + ".join(i18n.t(part) for part in key.split(" + "))
                            for key in left.split("  /  "))
    return text


def shortcut_sheet_html(desk_keys=None, query: str = "") -> str:
    """The rows as one HTML table, each half translated on its way in.
    `query` keeps the rows whose key or description holds it, as shown
    (case aside), and the heading of each section that still has one."""
    esc = html.escape
    needle = query.strip().casefold()
    body = ["<table cellspacing=0 cellpadding=4>"]
    heading = None      # held back until a row of its section is kept
    found = False
    for left, right in shortcut_rows(desk_keys):
        if not right:   # section heading
            heading = (f"<tr><td colspan=2 style='background:#dbe6f4;'>"
                       f"<b>{esc(i18n.t(left))}</b></td></tr>")
            continue
        key, what = _key_t(left), i18n.t(right)
        if needle and needle not in f"{key}\n{what}".casefold():
            continue
        if heading:
            body.append(heading)
            heading = None
        found = True
        body.append(
            f"<tr><td style='white-space:nowrap;'>"
            f"<b>{esc(key)}</b>&nbsp;&nbsp;</td>"
            f"<td>{esc(what)}</td></tr>")
    if not found:
        body.append(f"<tr><td>{esc(i18n.t('Nothing found'))}</td></tr>")
    body.append("</table>")
    return "".join(body)


def show_shortcuts(parent):
    """F1 / ❔: cheat sheet of every keyboard shortcut and mouse trick."""
    shortcuts_dialog(parent).exec()


def shortcuts_dialog(parent) -> QDialog:
    """The cheat sheet's window, a search field over the table."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("❔  Shortcuts")
    dlg.resize(620, 520)
    lyt = QVBoxLayout(dlg)
    search = QLineEdit()
    search.setPlaceholderText("🔍  Find a key or an action…")
    search.setClearButtonEnabled(True)
    browser = QTextBrowser()

    def fill():
        saved = (getattr(parent, "_settings", None) or {}).get("desk_keys")
        browser.setHtml(shortcut_sheet_html(saved, search.text()))

    fill()
    search.textChanged.connect(fill)
    lyt.addWidget(search)
    lyt.addWidget(browser)
    search.setFocus()
    row = QHBoxLayout()
    # ⌨ The desk keys are the operator's own: changed from here, the sheet
    # shows them at once.
    open_keys = getattr(parent, "open_desk_keys_window", None)
    if open_keys is not None:
        keys_btn = QPushButton("⌨  Keys…")
        keys_btn.clicked.connect(lambda: (open_keys(dlg), fill()))
        keys_btn.setAutoDefault(False)  # Enter in the search field opens nothing
        row.addWidget(keys_btn)
    row.addStretch(1)
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dlg.accept)
    close_btn.setAutoDefault(False)
    row.addWidget(close_btn)
    lyt.addLayout(row)
    return dlg
