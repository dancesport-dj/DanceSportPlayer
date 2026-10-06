# 6 · Einstellungen

[Zurück zur Übersicht](README.md) · zurück: [Tags](05-tags.md)

Öffne **⚙ Einstellungen** unten im Wiedergabe-Bereich. Die Änderungen gelten,
sobald du auf **OK** klickst. Erscheinungsbild, Akzentfarbe, Sprache und das
Audio-Backend werden beim Start gelesen: für diese fragt die App nach einem
Neustart.

## Pfade und Suche

Der Reiter **📁 Pfade & Suche**.

![Einstellungen, Reiter Pfade & Suche](../img/settings-paths.png)

Die Ordner oben beschreibt
[Kapitel 1](01-getting-started.md#der-app-deine-musik-zeigen). Darunter:

| Einstellung | Macht |
|---|---|
| **▶ Player-Position** | Wo die Player-Karte steht: *neben den Playlists*, am Kopf des Wiedergabe-Bereichs, oder *über den Playlists*, als ein breiter Streifen über den Decks. |
| **🎙 Erweiterte Ansagesteuerung** | Zeigt *…mit Takt*, *…mit Gruppe* und *🔈 Test* unter *Nächsten Tanz ansagen*. Ausgeblendet behalten sie ihre Werte. |
| **🔊 Audio-Backend** | Die Engine, über die jeder Titel spielt. Unter Windows: *FFmpeg* (die Vorgabe) oder *Windows Media Foundation*. Ändere es nur, wenn ein Titel nicht spielt oder ein Tempowechsel eine Lücke reißt. Wirkt nach einem Neustart. |
| **🔇 Die Soundkarte zwischen den Titeln freigeben** | Eine Onboard-Soundkarte legt ein Rauschen auf die Anlage, solange eine App sie offen hält. Diese Einstellung gibt das Gerät nach ein paar Sekunden Stille zurück. Der Preis ist ein leises Klicken, wenn der nächste Titel startet, schalte sie also nur ein, wenn du das Rauschen hörst. |
| **🔕 Systemklänge stummschalten, solange der Abend läuft** | Kein Fehler-Ding und kein Benachrichtigungston über die Lautsprecher. Die Systemklänge kommen zurück, wenn du die App schließt. |

## Aussehen

Der Reiter **🎨 Aussehen**.

![Einstellungen, Reiter Aussehen](../img/settings-look.png)

- **🎨 Erscheinungsbild**: eine Liste aller Looks, jeder mit einem Bild des
  Hauptfensters darin neben der Liste.
  - **Standard**: das klassische *Hell*, die Vorgabe, und *Dunkel* für eine
    dunkle Halle. Sie behalten die Emoji auf den Knöpfen und nehmen die
    Akzentfarbe von unten.
  - **Plattform-Looks**: Windows 11, macOS und Linux GNOME, jeweils hell und
    dunkel. Jeder Look lässt sich auf jedem System wählen.
  - **Pult-Looks**: *Konsole*, *Carbon*, *Neon* und *Studio*, dunkel wie ein
    Mischpult.
  - **Modern Looks**: *Graphit*, *Mitternacht*, *Aurora*, *Papier* und zwei
    Looks mit hohem Kontrast, vor allem auf Lesbarkeit hin ausgesucht.

  Ein Look gestaltet Knöpfe, Felder, Reiter und Menüs neu, bringt seine eigene
  Schrift und Akzentfarbe mit und tauscht die Emoji auf den Knöpfen gegen
  gezeichnete Symbole. Warnungen bleiben in jedem Theme rot.
  - **Eigene Looks**: Looks, die du selbst baust, gespeichert auf diesem
    Computer. **＋ Neuer Look…** kopiert den markierten Look (*Hell* und
    *Dunkel* beginnen bei *Papier* und *Graphit*) und öffnet den Editor: jede
    Farbe, die Ecken, der Stil von Knöpfen, Reitern und Fokus und die Schrift,
    mit einer Live-Vorschau daneben. Text, der sich zu schwach von seinem
    Hintergrund abhebt, wird als Warnung gelistet. **✎ Bearbeiten…** und
    **🗑 Löschen** ändern oder entfernen einen eigenen Look,
    **Exportieren…** speichert einen als `.json`-Datei und **Importieren…**
    fügt einen hinzu, den dir jemand gegeben hat. Diese Knöpfe speichern
    sofort. Änderst du den Look, in dem die App läuft, bietet sie beim
    Schließen der Einstellungen mit OK einen Neustart an.
- **🎚 Akzentfarbe**: das Blau der Knöpfe, Regler und des Player-Bereichs,
  für *Hell* und *Dunkel*. **↺ Standardblau** setzt es zurück. Farben, die
  etwas bedeuten, etwa rote Warnungen, behalten ihren Ton.
- **🌐 Sprache**: Englisch oder Deutsch.

Alle drei wirken nach einem Neustart.

## Analyse

Der Reiter **⚗ Analyse** sammelt jede Analyse. Sie *liest* deine Dateien nur.
Alles wird zwischengespeichert, ein zweiter Lauf macht also nur, was neu ist.

![Einstellungen, Reiter Analyse](../img/settings-analysis.png)

Der Player braucht drei davon:

- **📊 Lautheit analysieren (R128)**: für *Lautstärke angleichen*.
- **🐂 PD-Highlights analysieren**: für den Paso-Doble-Stopp.
- **🔇 Stillen prüfen**: zum Überspringen von Stille am Anfang und Ende.

**📤 Manuelle PD-Marken exportieren / 📥 importieren** bringt die Höhepunkte,
die du von Hand markiert hast, auf einen anderen PC. Aus der vollen App
gestartet, listet der Reiter weitere Analysen; der Player-Build zeigt nur
diese.

**🧱 ALLE Caches aufbauen…** lässt jede Analyse der Reihe nach laufen, für
eine Bibliothek deiner Wahl. Sie lässt sich abbrechen.

**🧹 Datenbank aufräumen…** entfernt zwischengespeicherte Zeilen für Dateien,
die es nicht mehr gibt, und verdichtet die Datenbank. Sie läuft nicht, wenn
das Musiklaufwerk nicht eingebunden aussieht, damit die Analyse nicht aus
Versehen gelöscht wird.

## Spiel-Sets

Der Reiter **🎛 Spiel-Sets** legt fest, was die Knöpfe **🏆 Turnier-Set** und
**🎉 Party-Set** im Wiedergabe-Bereich anwenden (siehe
[Kapitel 4](04-playing.md#abspiel-sets)).

![Einstellungen, Reiter Spiel-Sets](../img/settings-play-sets.png)

Für jedes Set:

- **Spieldauer**: wähl eine, tipp `m:ss` oder Sekunden, oder wähl
  *komplett*.
- **Ausblenden**, in Schritten von einer halben Sekunde.
- **⏭ Automatisch zum nächsten Titel**,
  **⏸ Keine Pause zwischen den Titeln**, **🔈 Nächsten Tanz ansagen**,
  **🔊 Lautstärke angleichen**, **▶️ Doppelklick startet den Titel** und
  **🎚 TSO: auf den Takt der Gruppe ziehen**.

Das Turnier-Set schaltet den 🐂 Paso-Doble-Stopp immer aus: die Erkennung ist
nicht zuverlässig genug, um einen Paso Doble im Turnier zu schneiden. Das
Party-Set lässt ihn, wie er ist.

**🎚 TSO-Zieltakt** legt pro Tanz fest, auf welches Tempo der Knopf TSO eine
Gruppe zieht:

- **Mittelwert der Runde**: bringt die ganze Runde auf ein Tempo, dort, wo
  die meisten ihrer Titel schon liegen. Kein Titel bewegt sich um mehr als
  einen Takt pro Minute.
- **Unten / Mitte / Oben**: ein festes Tempo innerhalb des TSO-Bereichs. Das
  lohnt sich bei den langsamen Tänzen, wo ein Takt pro Minute eine viel
  größere Tempoänderung ist.

Weiter: [Tastatur und Maus](07-shortcuts.md)
