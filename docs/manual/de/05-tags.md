# 5 · Tags: Sterne, Klassen und der MP3-Editor

[Zurück zur Übersicht](README.md) · zurück: [Den Abend fahren](04-playing.md)

Das meiste, was die App über einen Titel weiß, kommt aus seinen MP3-Tags: die
Klassen-Tags und Marker im Kommentar, Titel und Interpret. Der
**🏷 Tag-Editor** ändert sie ohne zweites Programm. Er bearbeitet auch die
eigenen Felder der MP3, so wie Mp3tag.

Ein Tag liegt an einem von zwei Orten:

- **In der App**: Sterne, Klassen, Instrumental, Marker und das Feld Custom.
  Eine Änderung wird in der Datenbank der App gespeichert, nicht in der Datei.
  Sie gewinnt gegen das Tag der Datei selbst und zeigt sich bei jeder Kopie
  derselben Datei, in jedem Deck und in der Bibliothek.
- **In der MP3-Datei**: Titel, Interpret, Album und die anderen ID3-Felder.
  Eine Änderung wird in die Datei selbst geschrieben.

## Den Editor öffnen

Rechtsklick auf einen Titel in einem Deck, einer Wunschliste oder der
📚 Bibliothek ▸ **🏷 Tags bearbeiten…**. Sind mehrere Titel markiert und
klickst du in die Markierung, heißt der Eintrag
**🏷 Tags von n Titeln bearbeiten…** und bearbeitet alle auf einmal.

## Der Reiter Tags

### In der MP3-Datei

Ein Formular wie bei Mp3tag: **Titel, Interpret, Album, Jahr, Track, Genre,
Kommentar, Album-Interpret, Komponist, CD-Nummer** und **Replay Gain**, dazu
das Cover (angezeigt, nicht bearbeitbar). Ein geändertes Feld wird beim
**Speichern** in jede markierte MP3 geschrieben. Der Kasten ist nur für
MP3-Dateien auf der Platte aktiv.

Bei mehreren Titeln steht in einem Feld, in dem sie sich unterscheiden,
**< beibehalten >**, und es bleibt in jeder Datei, wie es ist, bis du es
änderst. **< leer >** oder ein geleertes Feld löscht das Feld aus den Dateien.

### In der App

- **Sterne**: keine Sterne oder ein bis fünf ★.
- **Klassen**: die Startklassen D bis S, zu denen der Titel passt. Ist keine
  angehakt, passt er zu jeder Klasse.
- **Instrumental (ohne Gesang)**.
- **Marker**: freie Marker wie `classic` oder `vocal_f`, durch Kommas
  getrennt. Die meistbenutzten Marker der Bibliothek stehen unter der Zeile
  als Knöpfe. Ein Klick fügt einen hinzu, noch ein Klick nimmt ihn wieder
  heraus. Ein leuchtender Knopf ist gesetzt.
- **Custom**: ein freier Text pro Titel, siehe
  [Das Feld Custom](#das-feld-custom).

Bei mehreren Titeln beginnt ein Feld, in dem sie sich unterscheiden, auf
*beibehalten*: ein halb angehakter Klassen-Kasten, die Sterne auf
*beibehalten (je Titel verschieden)*, eine leere Marker-Zeile. Nur was du
änderst, kommt bei ihnen an. Ein Haken bei **B** an drei Titeln fügt B zu den
Klassen hinzu, die jeder schon hat. Eine Marker-Zeile, die du für mehrere
Titel tippst, ersetzt ihre Marker.

**↺ Zurück zu den Tags der Datei** vergisst jede Änderung, die in der App für
diese Titel gemacht wurde, und liest die MP3 neu.

### Die Tags der App in die MP3 schreiben

Speicherst du geänderte Sterne, Klassen, Instrumental oder Marker von
MP3-Dateien, fragt die App **… auch in die MP3-Datei schreiben?** Die Vorgabe
ist **Nein**: die Änderung bleibt dann nur in der App. Bei **Ja**:

- kommen die Sterne in die Windows-Bewertung der Datei, die der Explorer und
  der Windows Media Player zeigen;
- kommen die Klassen, *instr* und die Marker in den einfachen Kommentar. Text,
  der schon im Kommentar steht, bleibt dort.

Danach hält die Datei die Tags, und die App behält keine eigene Änderung mehr.

## Der Reiter Erweiterte Tags

Nur für eine einzelne MP3. Er listet jedes ID3-Frame der Datei, auch die, die
das Formular nicht zeigt: die eigenen Text-Frames von UltraMixer, die
Kommentare von MediaMonkey, die Windows-Bewertung.

- Bearbeite einen Wert in der Tabelle, **🗑** löscht ein Frame, **➕** fügt
  eins hinzu. Bilder und andere binäre Frames lassen sich nur entfernen.
- Die Frames, die das Formular zeigt, sind hier schreibgeschützt und folgen
  dem Formular, während du tippst.
- Die Beschreibung eines Frames lässt sich nicht ändern, aber kopieren:
  Doppelklick darauf, oder Rechtsklick auf eine beliebige Zelle ▸
  **📋 Kopieren**.
- Rechtsklick auf eine Zeile ▸ **🏷 Custom aus diesem Tag füllen** ordnet das
  Feld Custom diesem Frame zu, siehe unten.

Alles wird beim **Speichern** in die Datei geschrieben. Die Datei behält ihre
Tag-Version, ein ID3v2.3-Tag bleibt also v2.3.

Ein Titel, der im Player läuft oder pausiert, wird nicht geschrieben. Stopp ihn
zuerst. Ein Titel, der nur bereitliegt, wird geschrieben und neu geladen.

## Die Spalte ★

Decks, Wunschlisten und die Bibliothek haben eine Spalte **★**. Sie ist
anfangs ausgeblendet: ein Rechtsklick auf den Spaltenkopf blendet sie ein.

- Ein Klick auf den dritten Stern bewertet den Titel mit 3. Ein Klick auf den
  Stern, auf dem die Bewertung endet, löscht sie.
- Ein Klick auf die Sterne wird sofort in der App gespeichert und fragt
  nichts.
- Ein Doppelklick auf die Sterne spielt weder den Titel ab noch öffnet er die
  Datei.

Bewertungen, die schon in der Datei stehen, werden beim Scan gelesen: die
Windows-Bewertung von Explorer und Windows Media Player und ein
Songs-DB-Kommentar wie `ab C` (Klasse C und höher), aus dem die Klassen C, B,
A und S werden.

## Das Feld Custom

Ein freier Text pro Titel, getippt im 🏷 Editor. Er hat seine eigene Spalte
**Custom** in den Decks und der Bibliothek, anfangs ausgeblendet wie die
Spalte ★.

Das Feld kann auch ein MP3-Tag deiner Wahl zeigen, zum Beispiel das Datum, an
dem UltraMixer einen Titel zuletzt gespielt hat. Rechtsklick auf einen
Spaltenkopf ▸ **Custom einem MP3-Tag zuordnen…**:

- **Feld**: *Nur in der App* (die Vorgabe) oder die Art des Tags, etwa ein
  eigener Text (TXXX) oder ein Kommentar.
- **Beschreibung**: welcher eigene Text oder Kommentar, zum Beispiel
  `ultramixer_last_played`. Die Liste bietet die Beschreibungen an, die eine
  Stichprobe von 80 MP3s deiner Bibliothek wirklich enthält, die häufigste
  zuerst. Eine graue Zeile sagt, wie viele davon die gewählte enthalten, mit
  einem Beispielwert.

Nach **OK** liest die App dieses Tag jedes Bibliothekstitels im Hintergrund
und füllt die Spalte. Ein Wert, den du im 🏷 Editor tippst, gewinnt weiterhin
gegen das Tag. Solange Custom zugeordnet ist, bietet die Frage
**… auch in die MP3-Datei schreiben?** es ebenfalls an. Ohne Zuordnung
berührt Custom die Datei nie.

Der schnellere Weg: öffne den 🏷 Editor auf einem Titel, der das Tag hat, geh
zu **Erweiterte Tags** und klick mit rechts auf die Zeile ▸
**🏷 Custom aus diesem Tag füllen**.

Weiter: [Einstellungen](06-settings.md)
