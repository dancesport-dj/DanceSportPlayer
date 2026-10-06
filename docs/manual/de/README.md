# DanceSport Player — Benutzerhandbuch

Dieses Handbuch geht den Player so durch, wie er auf einem Turnier oder einem
Tanzabend benutzt wird: einmal einrichten, die Playlists laden, dann die Musik
auf der Fläche fahren.

Das ganze Handbuch gibt es auch als eine einzige Webseite,
[manual.html](manual.html). Nach einer Änderung an einem Kapitel baust du sie
mit `py -m tools.build_manual_html` neu.

![Das Hauptfenster beim Abspielen](../img/main-playing.png)

## Kapitel

1. [Erste Schritte](01-getting-started.md): der Player, seine Ordner, die
   Analyse und ein Rundgang durch das Hauptfenster.
2. [Bibliothek und Turniere](02-library-and-tournaments.md): die
   Musikbibliothek durchsuchen und filtern, und der Baum deiner
   Turnier-Playlists.
3. [Playlists](03-playlists.md): die Decks als Ablaufpläne, der
   Party-Bereich, Wunschlisten, `.m3u`-Playlists laden und speichern, und
   Playlists von einem anderen PC.
4. [Den Abend fahren](04-playing.md): die Player-Karte, der
   Wiedergabe-Bereich, Abspiel-Sets, Ansagen, der Paso-Doble-Stopp, die
   Cartwall und der Präsentationsbildschirm.
5. [Tags](05-tags.md): der 🏷 Tag-Editor, ★ Bewertungen, das Feld *Custom*
   und Tags in die MP3 schreiben.
6. [Einstellungen](06-settings.md): Pfade, das Aussehen (Themes, eigene
   Looks, Akzentfarbe, Sprache), Analyse und Abspiel-Sets.
7. [Tastatur und Maus](07-shortcuts.md): alle Tastenkürzel in einer Liste.

Installation und Konfigurationsdateien beschreibt die
[README](../../../README.md#installation) des Projekts.

## Schreibweisen

- **Knöpfe und Menüeinträge** stehen so da, wie sie in der App heißen, mit
  Symbol, wo es beim Finden hilft: **🎛 Cartwall**, **📚 Bibliothek**.
- **Rechtsklick ▸ 💾 Speichern als M3U…** heißt: rechts klicken, dann diesen
  Eintrag im Kontextmenü wählen.
- Fast jedes Bedienelement hat einen Tooltip. Wo dieses Handbuch bei einem
  Detail knapp ist, fahr mit der Maus darüber.
- **F1** öffnet in der App die Übersicht aller Tastenkürzel. Es ist dieselbe
  Liste wie in [Kapitel 7](07-shortcuts.md).
- Die App gibt es auf Deutsch und Englisch (⚙ Einstellungen ▸ 🎨 Aussehen).
  Die Bilder zeigen die englische Oberfläche. Dort sind auch die Tanz- und
  Rundennamen englisch: *Slow Waltz*, *Round 1*, *Final*. Mit dem Haken
  **Deutsche Tanz- und Rundennamen auch in der englischen Oberfläche** unter
  der Sprache bleiben es *Langsamer Walzer*, *Vorrunde*, *Finale*; der
  Präsentationsbildschirm und die aufgenommenen Ansagen sind dann ebenfalls
  deutsch. Playlists und Exporte behalten die deutschen Wörter in jedem Fall.

## Begriffe

| Begriff | Bedeutung |
|---|---|
| **Deck** | Eine Playlist auf dem Bildschirm, beschriftet mit A, B, C und so weiter. Es hält den Ablauf eines Turniers oder eines Teils des Abends. |
| **Party-Bereich** | Eine lange Playlist für einen Tanzabend, zwischen den Decks und den Wunschlisten. |
| **Wunschliste** | Eine flache Liste von Titeln, die du für später parkst: Musikwünsche, ein neues Album. Sie liegt unter den Decks. |
| **Runde** | *Vorrunde*, *Zwischenrunde*, *Semifinale*, *Finale*. Eine Turnier-Playlist ist nach ihren Runden gegliedert. |
| **Gruppe** | Paare, die gleichzeitig tanzen (englisch *Heat*). Jede Gruppe einer Runde bekommt pro Tanz ihren eigenen Titel. |
| **Takt / BPM** | Tempo in **Takten** pro Minute, wie die TSO es festlegt (Samba 50–52, Langsamer Walzer 28–30). `[T51]` in einem Deck heißt 51 Takte pro Minute. |
| **TSO-Bereich** | Das Tempo, das die Turnierordnung für einen Tanz erlaubt. |
