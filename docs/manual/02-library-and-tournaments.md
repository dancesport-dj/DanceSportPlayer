# 2 · Library and Tournaments

[Manual index](README.md) · previous: [Getting started](01-getting-started.md)

The pane under the wishlists has two tabs. Show or hide it with **📚 Library**
in the toolbar. Drag the splitter above it to give it more room.

## 📚 Library

The whole Favorites library as one sortable table. Filter it, then drag
titles into a deck, the Party panel or a wishlist.

![The library browser](img/library.png)

| Filter | Shows |
|---|---|
| 🔍 text field | Titles whose title, artist or comment tag contains the text. Tags are markers like `vocal_f`, `classic`, `eintanzen`. |
| All dances | One dance, or all Standard or all Latin dances. |
| All classes | Titles suited to that start class. Titles without a class tag always show. |
| Vocal + instr. | Only 🎤 vocal or only 🎻 instrumental titles. |
| All categories | 🏆 **Tournament only** hides anthems, background music, wrong-tempo files, duplicates and seasonal folders. You can also pick one of those categories, which is handy for a party. |
| Plays: all | ✦ **Never played**, ★ **Rarely**, ★ **Proven**, or 📅 **Not since 1 y** (played, but not in any playlist of the last year). |
| Added: all | Files created in the last 30 or 90 days, or the last 12 or 18 months. Combine it with ✦ Never played to find what you copied in but never used. |
| 🆕 Unplanned | Only titles that are in none of the open decks. |

- **▶** in a row plays the title on the player. **Space** does the same for
  the selected row.
- **Double-click** a row to open the file in your external audio player.
- **Right-click** a row for **📋 Copy file path**, **📂 Show in Explorer**,
  **🎧 Open in external player**, **🏷 Re-read MP3 tags** and
  **🏷 Edit tags…**. With several rows selected, the tag editor edits them all.
  See [chapter 5](05-tags.md).
- **Right-click the column header** to choose the columns, or to switch to
  short dance names (LW, SB). The **★** rating and **Custom** columns are
  hidden at first and can be shown here. **Map Custom to an MP3 tag…** fills
  Custom from a tag of your choice.

## 🏆 Tournaments

Your archive of tournament playlists, sorted the way you think about them:
a season, a weekend, a venue, a competition. The folders are only labels. The
🎵 entries point at `.m3u` files wherever those are on disk.

![The Tournaments tab, slots view](img/tournaments.png)

### Filling the tree

- Drop `.m3u` files or a whole folder from Explorer onto the tree.
- **📁** creates a folder: a day, a venue, a competition.
- **＋** adds playlist files to the selected folder. Right-click the tree ▸
  **📂 Add a folder of playlists…** files a whole folder from disk as a
  branch, with every `.m3u` under it, the same way a folder dropped from
  Explorer is filed.
- **✎** (or **F2**) renames the selected entry. **🗑** (or **Del**) removes
  it from the tree. The file on disk is not touched. In the slots view these
  act on the picked slot; click the folder row to act on the folder.
- **Ctrl + A** marks everything: every slot of the folder, or every entry of
  the tree in the tracks view. **Del** and **🗑** then remove all marked
  entries after one question.
- **⊟** collapses every folder, which helps with a long season.
- From a deck: right-click ▸ **🏆 Save and add to Tournaments…** saves the
  playlist and files it here. It goes into the selected folder, next to the
  selected playlist, or at the root. The new entry is picked and shown right
  away.

### Slots view

Pick a folder on the left and its playlists appear on the right as slots.
Each slot shows:

- the playlist name,
- the number of titles (♪),
- the dances,
- the rounds it contains (VR = Vorrunde, ZR = Zwischenrunde, ER = Endrunde).

- **Drag a slot onto a deck** to load that playlist there. Dragging one of
  several marked slots carries them all; they go into the free decks, one
  each. A plain click narrows the marking to one slot.
- **Double-click a slot** to load it onto the focused deck.
- **Right-click a slot** for ▶ Load onto the focused deck, 🎵 Show its tracks,
  ✎ Rename and 🗑 Remove from tree.

### Tracks view

**▤** switches to the tracks view. The tree now lists the playlists
themselves, and the right side shows the titles of the picked playlist in
playing order, with their round and dance. Rounds are written short, the way
the slots write them (VR, 1ZR, ER). Hover over one for the full name.

![The Tournaments tab, tracks view](img/tournaments-tracks.png)

- **▶** or **Space** plays a title. A double-click opens it in your
  external player.
- Drag titles onto a deck, the Party panel or a wishlist.
- The bar underneath shows the songs and total play time. Titles that the
  library doesn't know are counted, but add no time.

**▦** switches back to the slots.

Next: [Playlists](03-playlists.md)
