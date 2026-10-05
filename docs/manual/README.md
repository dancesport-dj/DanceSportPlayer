# DanceSport Player — User Manual

This manual walks through the player the way it is used at a tournament or a
dance evening: set it up once, load the playlists, then run the music on the
floor.

The whole manual is also a single web page, [manual.html](manual.html). After
changing a chapter, rebuild it with `py -m tools.build_manual_html`.

![The main window while playing](img/main-playing.png)

## Chapters

1. [Getting started](01-getting-started.md): the player, its folders, the
   analysis, and a tour of the main window.
2. [Library and Tournaments](02-library-and-tournaments.md): browsing and
   filtering the music library, and the tree of your tournament playlists.
3. [Playlists](03-playlists.md): the decks as running orders, the Party
   panel, wishlists, loading and saving `.m3u` playlists, and playlists
   written on another PC.
4. [Playing the evening](04-playing.md): the player card, the Playing panel,
   play sets, announcements, the Paso Doble stop, the cartwall and the
   presenter screen.
5. [Tags](05-tags.md): the 🏷 tag editor, ★ ratings, the Custom field, and
   writing tags into the MP3.
6. [Settings](06-settings.md): paths, look, analysis and play sets.
7. [Keyboard and mouse](07-shortcuts.md): every shortcut in one list.

Installation and the configuration files are described in the project
[README](../../README.md#installation).

## Conventions

- **Buttons and menu entries** are written as they appear in the app, icon
  included where it helps to find them: **🎛 Cartwall**, **📚 Library**.
- **Right-click ▸ 💾 Save as M3U…** means: right-click, then pick that entry
  from the context menu.
- Nearly every control has a tooltip. When this manual is short on a detail,
  hover over the control.
- **F1** in the app opens the cheat sheet of all shortcuts. It is the same list
  as [chapter 7](07-shortcuts.md).
- The app is in English or German (⚙ Settings ▸ 🎨 Look). The screenshots show
  the English interface. On it the dance and round names are English too:
  *Slow Waltz*, *Round 1*, *Final*. Tick **Keep the German dance and round
  names** below the language to keep *Langsamer Walzer*, *Vorrunde*,
  *Finale*; the presenter screen and the recorded announcements are then
  German as well. Playlists and exports keep the German words either way.

## Terms

| Term | Meaning |
|---|---|
| **Deck** | One playlist on the screen, labelled A, B, C and so on. It holds the running order of one competition or one part of the evening. |
| **Party panel** | A long playlist for a social evening, between the decks and the wishlists. |
| **Wishlist** | A flat list of titles you park for later: requests, a new album. It sits under the decks. |
| **Round** | *Vorrunde*, *Zwischenrunde*, *Semifinale*, *Finale*. A competition playlist is grouped into its rounds. |
| **Heat** | One group of couples dancing at the same time. Every heat of a round gets its own title per dance. |
| **Takt / BPM** | Tempo in **bars** per minute, as the TSO defines it (Samba 50–52, Slow Waltz 28–30). `[T51]` in a deck means 51 bars per minute. |
| **TSO range** | The tempo the tournament rules allow for a dance. |
