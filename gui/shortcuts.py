"""❔ F1 — the cheat sheet of every keyboard shortcut and mouse trick.

Split off the main window, which only opens it: the rows, the table they are
glued into and the dialog showing it need nothing of the window.
"""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QTextBrowser, QVBoxLayout

from planner import i18n


def shortcut_rows():
    """Every line of the cheat sheet — a row with no right half is a
    section heading. Both halves are catalog keys; `setHtml` cannot be
    patched for them, so `shortcut_sheet_html` translates them itself."""
    return (
        ("⌨  Keyboard", ""),
        ("Space", "Play / stop the selected song"),
        ("Ctrl + ← / →", "Seek 30 s back / forward while playing"),
        ("Ctrl + Shift + ← / →", "Previous / next title — same as ⏮ / ⏭ on "
                                 "the player (⏭ also ends a running pause)"),
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
        ("F2  in the 📅 tournament tree", "Rename the entry under the cursor "
                                          "(Del removes it)"),
        ("Ctrl + A  in 🏆 Tournaments", "Mark every slot of the folder, or "
                                       "every entry of the tree — Del and a "
                                       "drag then take them all"),
        ("Ctrl + F", "Find a title in the focused list (repeat to step to "
                     "the next match)"),
        ("Esc  in the 🖥 presenter window", "Close the presenter screen"),
        ("F1", "This cheat sheet"),
        ("🖱  Mouse", ""),
        ("Click a round / dance header", "Collapse or expand that section"),
        ("Double-click a deck title", "Rename the playlist / wishlist"),
        ("▾ / ▸ arrow in a deck header", "Fold the deck to a header tab "
                                         "(click the tab to reopen)"),
        ("Drag a row", "Move a song to another slot, deck, wishlist — or "
                       "drop it into Explorer / UltraMixer"),
        ("Drag a dance header", "Reorder the dance columns of a static deck"),
        ("Right-click ▸ 🔍 Find a title", "Jump to a song by name; repeat to "
                                          "step to the next match"),
        ("Ctrl + drag onto a filled slot", "Dynamic deck: replace the song in "
                                           "that slot with the dragged one"),
        ("Drop a file from outside", "Replace a slot / add to a wishlist "
                                     "(.m3u on a deck imports it)"),
        ("▶ or Space on a 📚 library row", "Preview that track in the "
                                          "mini player"),
        ("Double-click a 📚 library row", "Open the track in your external "
                                          "audio player"),
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


def shortcut_sheet_html() -> str:
    """The rows as one HTML table, each half translated on its way in."""
    esc = html.escape
    body = ["<table cellspacing=0 cellpadding=4>"]
    for left, right in shortcut_rows():
        if not right:   # section heading
            body.append(
                f"<tr><td colspan=2 style='background:#dbe6f4;'>"
                f"<b>{esc(i18n.t(left))}</b></td></tr>")
        else:
            body.append(
                f"<tr><td style='white-space:nowrap;'>"
                f"<b>{esc(i18n.t(left))}</b>&nbsp;&nbsp;</td>"
                f"<td>{esc(i18n.t(right))}</td></tr>")
    body.append("</table>")
    return "".join(body)


def show_shortcuts(parent):
    """F1 / ❔: cheat sheet of every keyboard shortcut and mouse trick."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("❔  Shortcuts")
    dlg.resize(620, 520)
    lyt = QVBoxLayout(dlg)
    browser = QTextBrowser()
    browser.setHtml(shortcut_sheet_html())
    lyt.addWidget(browser)
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dlg.accept)
    lyt.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
    dlg.exec()
