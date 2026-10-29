# 3 · Wiedergabelisten

[Zurück zur Übersicht](README.md) · zurück: [Bibliothek und Turniere](02-library-and-tournaments.md)

Der Player hält seine Musik in drei Arten von Listen:

- die **Decks**, eins pro Turnier oder pro Teil des Abends;
- den **Party-Bereich**, für einen langen Tanzabend;
- die **Wunschlisten**, für Titel, die du griffbereit halten willst.

## Die Decks

**⧉ *n* Listen** in der Werkzeugleiste legt fest, wie viele Decks auf dem
Bildschirm stehen. Jedes Deck ist ein **Ablauf**: die Titel laufen von oben
nach unten.

- Eine Turnier-Wiedergabeliste erscheint weiterhin nach Runden und Tänzen
  gegliedert. Ein Klick auf einen Runden- oder Tanzkopf klappt ihn zu.
- Jede Zeile lässt sich überallhin ziehen, auch in ein anderes Deck.
- Ein Titel, den du auf ein Deck ziehst, aus der Bibliothek, einer
  Wunschliste oder dem Explorer, wird dort **eingefügt**, wo du ihn ablegst.
  Er ersetzt nie den Titel, der dort stand.
- **Entf** nimmt die markierten Titel nach einer Rückfrage aus dem Ablauf.
- **Strg + Z / Strg + Y** machen jede Änderung rückgängig und wiederholen sie.
  Die Knöpfe ↶ / ↷ unten zeigen, wie viele Schritte es gibt.
- Ein Doppelklick auf den Decktitel benennt das Deck um. **▾** im Kopf klappt
  das Deck zu einem Reiter ein.

Die Spalten:

- **Tanz / Gruppe**: welcher Tanz und welche Gruppe die Zeile ist.
- **▶**: spielt oder stoppt genau diesen Titel.
- **Titel**: das Titel-Tag der MP3. Eine Datei ohne zeigt ihren bereinigten
  Dateinamen.
- **BPM**: das Tempo in Takten pro Minute. Es wird zuerst aus dem Dateinamen
  gelesen (`[T51]`), dann aus dem BPM-Tag der MP3, dann aus einem Tempo im
  Titel-Tag. Ein BPM-Tag zählt Schläge, darum wird es in Takte pro Minute
  umgerechnet, und es zählt nur, wenn es nahe am TSO-Bereich des Tanzes
  landet. Der Tooltip der Zelle sagt, woher das Tempo kommt. `[?BPM]` heißt,
  die Datei trägt kein Tempo.
- **⏱**: die Länge. Sie ist **orange**, wenn der Titel kürzer ist als die
  Spieldauer oder wenn an einem Rand 5 s oder mehr Stille übersprungen werden.
- **Pop**: `★58` heißt, der Titel steht in 58 deiner Turnier-Wiedergabelisten.
  **✦neu** heißt, er steht in keiner.
- **Klasse**: die Klassen-Tags aus dem MP3-Kommentar, zum Beispiel `[B,A,S]`.

Fünf weitere Spalten sind anfangs ausgeblendet. Ein Rechtsklick auf den
Spaltenkopf blendet sie ein: **★** bewertet einen Titel mit einem Klick,
**Custom** hält einen freien Text pro Titel, **Dateiname** zeigt den
bereinigten Dateinamen, mit dem vollen Pfad im Tooltip, **Album** den
Album-Tag der MP3 und **Kommentar** ihren Kommentar, wie er drinsteht (etwa
„vocal AS“). ★ und Custom
beschreibt [Kapitel 5](05-tags.md).

**Gespielt** (ebenfalls anfangs ausgeblendet) zählt, wie oft ein Titel in den
letzten 24 Stunden gespielt wurde, aus jeder Liste: „2“ in jeder Liste, die
ihn enthält, egal wo er lief. Ein Titel zählt, sobald er im Spielmodus 10
Sekunden zu hören war, dieselbe Regel wie bei 📜 Gespielte Titel. **Zähler
für Gespielt zurücksetzen** im Rechtsklick-Menü des Spaltenkopfs setzt alle
Zähler auf null; 📜 Gespielte Titel behält trotzdem jeden Titel. Die
Bibliothek und die 🏆 Titelliste haben dieselbe Spalte.

Zieh einen Spaltenkopf zur Seite, um die Spalte zu verschieben. Die neue
Reihenfolge gilt für alle Listen dieser Art (alle Decks, alle Wunschlisten
oder alle Partylisten) und bleibt beim nächsten Start erhalten. **Tanz**
bleibt vorne und **↺** hinten. Ein eingeblendetes **Album** steht anfangs
direkt hinter **Titel**.

Zeilenfarben:

- eine **orange** Zeile ist markiert, zum Beispiel als Titel, der
  später getauscht werden soll (**Strg + M**);
- eine **hellrote** Zeile mit ❗ auf dem ▶ zeigt auf eine Datei, die es nicht
  mehr gibt. Ist die Datei wieder da und läuft der Titel, verschwindet die
  Markierung. Ein Titel, der sich nicht abspielen ließ, wird genauso rot, mit
  dem Grund im Tooltip, siehe
  [Kapitel 4](04-playing.md#ein-titel-der-nicht-spielt);
- eine **fliederfarbene** Zeile mit **📌** vor dem Titel ist angeheftet.

**📌 Einen Titel anheften.** Rechtsklick auf einen Titel einer Runde ▸
**📌 Anheften — Titel beim Neuwürfeln der Runde behalten**. Wird die Runde
oder ihr Tanz auf der Planerseite neu erzeugt, behält ein angehefteter Titel
seinen Platz; das Neuwürfeln seiner eigenen Zeile meldet, dass er angeheftet
ist, statt ihn zu ersetzen. **📌 Lösen** nimmt die Nadel wieder heraus.
Angeheftetes wird mit dem Deck gespeichert und geht, wenn das Deck geleert
wird.

Die Leiste unter dem Deck zeigt die Zahl der Titel **Σ** und die
Gesamtzeit. Ein Klick auf ▸ zeigt die Zahl pro Tanz. Der Schalter
**✋ Manuell / ⏭ Auto** legt fest, ob das Deck von selbst weiterspielt, siehe
[Kapitel 4](04-playing.md#einen-titel-starten).

Ein Rechtsklick auf einen Titel bietet **🏷 MP3-Tags neu einlesen**,
**🏷 Tags bearbeiten…** (siehe [Kapitel 5](05-tags.md)),
**📋 Dateipfad kopieren**, **📂 Im Explorer zeigen** und die Einträge zum
Speichern und Importieren weiter unten.

## 🤸 Der Party-Bereich

Der Party-Bereich hält eine lange Liste für einen Tanzabend. Er sitzt
zwischen den Decks und den Wunschlisten. **🤸 Party ▾** in der
Werkzeugleiste blendet ihn ein oder aus, und **▾** in seinem Kopf klappt ihn
ein.

![Eine Partyliste im Bereich](../img/party-panel.png)

- Zieh eine `.m3u` auf den Bereich, um sie zu laden. Der Bereich trägt dann
  den Namen der Datei. Ein Turnierablauf, den du hier ablegst, wird in die
  Runden aufgeteilt, in denen er gespielt wird, etwa *Vorrunde* und
  *Finale*.
- Eine in Runden gebaute Liste ist nach ihnen gegliedert, zum Beispiel
  *Standardrunde*, *Lateinrunde* und *Socialrunde*.
- **⇅ Diese beiden Titel tauschen** (Rechtsklick oder **Alt + S**) tauscht
  zwei markierte Titel desselben Tanzes, so behält jede Runde ihre Tänze.

Spielst du aus dem Bereich, schaltet die App von selbst auf das
**🎉 Party-Set**: volle Länge, automatisch weiter, keine Pause, siehe
[Kapitel 4](04-playing.md#abspiel-sets).

## ⭐ Wunschlisten

Eine Wunschliste ist eine flache Liste von Titeln, die du griffbereit halten
willst: Wünsche von der Fläche, ein neues Album, das du ausprobieren willst.

- Zieh Titel aus einem Deck, der Bibliothek oder dem Explorer hinein. Zieh
  sie hinaus auf ein Deck.
- **⭐ n Wunschlisten** in der Werkzeugleiste zeigt bis zu vier Wunschlisten
  oder ein 2×2-Raster.
- Ein Doppelklick auf den Titel benennt sie um. Zieh den Kopf einer
  Wunschliste auf einen anderen, um die beiden zu tauschen.
- Die Leiste darunter zählt die Titel und wie viele davon neu (nie gespielt)
  sind.

**🧹 Leeren** lässt die Wunschlisten stehen.

## Laden und speichern

| Um | Tu |
|---|---|
| eine `.m3u` in ein Deck oder eine Wunschliste zu laden | Rechtsklick ▸ **📂 M3U importieren…**, oder zieh die `.m3u` darauf. Mehrere `.m3u` auf einmal gehen in die freien Decks, je eine. |
| eine Wiedergabeliste aus deinem Turnierarchiv zu laden | Zieh ihren Slot aus 🏆 Turniere auf ein Deck, siehe [Kapitel 2](02-library-and-tournaments.md#-turniere). |
| das aktive Deck oder die aktive Wunschliste zu speichern | **Strg + S**, oder Rechtsklick auf einen Titel oder den Kopf ▸ **💾 Speichern als M3U…** |
| sie zu speichern und im Baum Turniere abzulegen | Rechtsklick ▸ **🏆 Speichern und in „Turniere“ eintragen…** |
| jedes Deck auf einmal zu speichern | **💾 Speichern** in der Werkzeugleiste. Jede Datei wird nach ihrem Decktitel benannt. |

Beim Import erkennt ein Deck Runden, Tänze und Gruppen von selbst, auch ein
Finale mit zusätzlichen Ersatztiteln. Eine Wunschliste hängt die Titel als
flache Liste an.

### Das Wiedergabelisten-Dateiformat

Jede Wiedergabeliste, die die App schreibt, ist UTF-8, so überleben Umlaute und
Akzente. Das **Wiedergabelisten-Dateiformat** unter ⚙ Einstellungen ▸ 📁 Pfade wählt
eine von drei Formen:

- **UTF-8 (.m3u)**: der Standard, den aktuelle Player lesen.
- **UTF-8 mit BOM (.m3u)**: für ein älteres Windows-Programm, das `Ã¼` statt
  `ü` zeigt.
- **UTF-8 (.m3u8)**: dasselbe UTF-8, unter der Endung, die manche Player
  erwarten.

Speichern als M3U, 💾 Speichern und die Exporte folgen ihm alle. Die App liest
alle drei wieder ein, und `.m3u8`-Dateien zählen auch für die Spalte **Pop**.

## Wiedergabelisten von einem anderen PC

Eine Wiedergabelisten-Datei speichert den vollen Pfad jedes Titels. Wurde sie auf
einem anderen PC geschrieben oder liegt die Musik inzwischen auf einem anderen
Laufwerk, stimmen diese Pfade nicht. Der Player repariert sie beim Laden der
Wiedergabeliste, mit zwei Einstellungen unter
[⚙ Einstellungen ▸ 📁 Pfade](01-getting-started.md#der-app-deine-musik-zeigen):

- **Referenzpfad**: der Ordner, in dem die Musik auf *diesem* PC liegt;
- **Suchordner**: weitere Orte zum Suchen, einer pro Zeile.

Die App versucht zuerst den Referenzpfad, dann die Suchordner der Reihe nach.
Sie schneidet den alten Pfad von vorn ab, bis der Rest auf eine echte Datei
unter einem davon zeigt. Aus `D:\Musik\tanzcds\lateincd\Samba.mp3` wird so
zum Beispiel `F:\my music\tanzcds\lateincd\Samba.mp3`. Ein Pfad wird nur auf
eine Datei geändert, die es wirklich gibt.

Musste ein Pfad geändert werden, sagt ein Fenster, wie viele Titel umgehängt
wurden und wie viele nicht zu finden waren; **Details anzeigen** listet jeden
alten und neuen Pfad. Ein Titel, der nicht zu finden war, steht rot mit ❗
da. Trag den Ordner, in dem er liegt, unter Suchordner ein und importiere die
Wiedergabeliste dann noch einmal.

Vor dem Abend zählt **🚦 Prüfen ▸ 🚦 Bereit?** die Titel, die fehlen oder
nicht unter dem Referenzpfad liegen. Sein Knopf **🧭 Pfade reparieren…**, in
der Zeile 📁 Musikdateien, hängt die Decks auf die Kopien dort um, siehe
[Kapitel 4](04-playing.md#-bereit-vor-dem-abend).

Weiter: [Den Abend fahren](04-playing.md)
