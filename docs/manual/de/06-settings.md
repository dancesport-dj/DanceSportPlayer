# 6 · Einstellungen

[Zurück zur Übersicht](README.md) · zurück: [Tags](05-tags.md)

Öffne **⚙ Einstellungen** unten im Wiedergabe-Bereich. Die Änderungen gelten,
sobald du auf **OK** klickst. Erscheinungsbild, Akzentfarbe, Sprache und das
Audio-Backend werden beim Start gelesen: für diese fragt die App nach einem
Neustart.

Die Reiter, der Reihe nach: **⚙ Allgemein**, **📁 Pfade**, **🎨 Aussehen**,
**🔊 Ton & Player**, **🎛 Cartwall**, **⚗ Analyse**, **🎛 Spiel-Sets** und
**📦 Hallenpaket**. Die volle App ergänzt **🎵 Prüfungen**, die
Schwellenwerte ihrer Musikprüfung; der Player blendet ihn aus. Öffnest du
die Einstellungen wieder, stehen sie auf dem Reiter, auf dem du sie
geschlossen hast, bis die App beendet wird.

## Allgemein

Der Reiter **⚙ Allgemein**.

| Einstellung | Macht |
|---|---|
| **App-Modus** | Welche Seite der App zu sehen ist: *Beides*, *Nur Planer* oder *Nur Player*. Zurückschalten bringt alles wieder. Der Player-Build hat diese Zeile nicht. |
| **📱 Handy-Fernbedienung** | **📱 Server starten** startet die Handy-Fernbedienung und öffnet ihr Fenster über den Einstellungen. Solange sie läuft, heißt der Knopf **📱 Server stoppen**. Siehe [Kapitel 4](04-playing.md#-die-handy-fernbedienung). |
| **🎛 DJ-Controller** | **🎛 Einrichten…** öffnet das Fenster für einen USB-MIDI- oder HID-Controller. Siehe [Kapitel 4](04-playing.md#-ein-dj-controller). **⌨ Tasten…** legt dieselben Aktionen auf Tasten und enthält auch die Tasten der Cartwall, siehe [Kapitel 4](04-playing.md#-pult-tasten). |
| **🐞 Fehlerberichte senden** | Nur in Builds, die sie senden können. Stößt die App auf einen Fehler, schickt sie die technischen Details an den Entwickler: den Fehler, die letzten Protokollzeilen, das System und die App-Version. Nie deine Musik oder Wiedergabelisten. Standardmäßig aus. |
| **🐞 Fehler & Ideen** | Keine Einstellung: ❔ ▸ ℹ Über… verlinkt auf ein neues GitHub-Issue für einen Fehler oder eine Funktion, die du dir wünschst, und nennt eine Mailadresse für alle ohne GitHub-Konto. |
| **🔔 Nach neuen Versionen suchen** | Einmal pro Start bei GitHub (api.github.com) fragen, ob ein neueres Release erschienen ist, und es einmal mit einem Link zur Downloadseite ankündigen. Die Anfrage enthält nichts über dich oder deine Musik; GitHub sieht die IP-Adresse, von der sie kommt. Es wird nichts heruntergeladen oder installiert. Standardmäßig aus; der erste Start fragt. Gilt ab dem nächsten Start. |

## Pfade

Der Reiter **📁 Pfade**.

![Einstellungen, Reiter Pfade](../img/settings-paths.png)

Die Ordner beschreibt
[Kapitel 1](01-getting-started.md#der-app-deine-musik-zeigen). Zwischen ihnen
sitzt das **Wiedergabelisten-Dateiformat**: *UTF-8 (.m3u)*, *UTF-8 mit BOM (.m3u)*
oder *UTF-8 (.m3u8)*, siehe
[Kapitel 3](03-playlists.md#das-wiedergabelisten-dateiformat).

**Ausgeschlossene Ordner**, einer pro Zeile (oder über **Hinzufügen…**
gewählt), halten einen Ordner samt allem darunter aus der Bibliothek
heraus: ⭐ Favoriten und 🌐 Ganze Bibliothek lassen diese Titel in der
Liste, der Suche und den Vorschlägen weg. Auf der Platte ändert sich
nichts. Eine Änderung wirkt ab dem nächsten Start, die App bietet den
Neustart an.

**🏅 Hintergrund: Einmarsch & Siegerehrung** sammelt die Musik für den
Einmarsch der Paare und die Siegerehrung in einer eigenen Kategorie der
Bibliothek. Ein Titel gehört dazu, wenn eines der Wörter, durch Komma
getrennt, in seinem Datei- oder Ordnernamen, seinem Titel oder seinem
Kommentar steht: ab Werk *Einmarsch, Siegerehrung, Entrance, Award,
Ceremony*. Groß- und Kleinschreibung spielen keine Rolle, und ein Teil
eines Wortes reicht: *Award* findet auch *(Background Award)*. Jeder Titel
in den Ordnern darunter, einer pro Zeile, gehört ebenfalls dazu. Diese
Titel stehen unter 🏅 im Kategoriefilter der Bibliothek und bleiben aus
erzeugten Wiedergabelisten heraus. Die Kategorie hat Vorrang vor einem
🎶 Hintergrund-Ordner.

## Aussehen

Der Reiter **🎨 Aussehen**.

![Einstellungen, Reiter Aussehen](../img/settings-look.png)

- **🎨 Erscheinungsbild**: eine Liste aller Looks, jeder mit einem Bild des
  Hauptfensters darin neben der Liste.
  - **Standard**: das klassische *Hell*, die Vorgabe, und *Dunkel* für eine
    dunkle Halle. Sie
    behalten die Emoji auf den Knöpfen und nehmen die Akzentfarbe von unten.
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
- **🔠 Schriftgröße**: jeder Text der App, Menüs und Tabellen
  eingeschlossen, mit 100 % (die Vorgabe), 105, 110, 115, 130 oder 150 %.
  Über 115 % wachsen die Knöpfe mit. Gilt ab dem Start der App, wie das
  Erscheinungsbild.
- **🎚 Akzentfarbe**: das Blau der Knöpfe, Regler und des Player-Bereichs,
  für *Hell* und *Dunkel*. **↺ Standardblau** setzt es zurück. Farben, die
  etwas bedeuten, etwa rote Warnungen, behalten ihren Ton.
- **🌐 Sprache**: English, Deutsch, Español, Nederlands oder Русский.
  Titelnamen und alles, was aus deinen Dateien gelesen wird, bleiben, wie sie
  sind.
- **Deutsche Tanz- und Rundennamen auch in einer anderssprachigen
  Oberfläche**: *Langsamer Walzer*, *Vorrunde*, *Eintanzen* statt *Slow
  Waltz*, *Round 1*, *Practice*. Der Präsentationsbildschirm und die
  aufgenommenen Ansagen sind dann ebenfalls deutsch.

Erscheinungsbild, Akzentfarbe und Sprache wirken nach einem Neustart.

- **⛶ Uhr im Vollbild: nur die Uhrzeit (20:45:12), ohne Datum**: die Uhr in
  der Statusleiste, solange das Fenster im
  [Vollbild](01-getting-started.md#-vollbild) ist. Sie wechselt innerhalb
  einer Sekunde nach dem Speichern.
- **🖥 Präsentation**: die Farben der
  [Präsentation](04-playing.md#-präsentation). *Default* ist die schwarze
  Hallenanzeige. *Light* ist cremefarbenes Papier mit warmer brauner Schrift,
  für einen hellen Raum. Eine offene Präsentation wechselt, sobald du
  speicherst.

## Ton und Player

Der Reiter **🔊 Ton & Player**.

| Einstellung | Macht |
|---|---|
| **🔊 Audio-Backend** | Die Engine, über die jeder Titel spielt. Unter Windows: *FFmpeg* (die Vorgabe) oder *Windows Media Foundation*. Ändere es nur, wenn ein Titel nicht spielt oder ein Tempowechsel eine Lücke reißt. Wirkt nach einem Neustart. |
| **🔇 Die Soundkarte zwischen den Titeln freigeben** | Eine Onboard-Soundkarte legt ein Rauschen auf die Anlage, solange eine App sie offen hält. Diese Einstellung gibt das Gerät nach ein paar Sekunden Stille zurück. Der Preis ist ein leises Klicken, wenn der nächste Titel startet, schalte sie also nur ein, wenn du das Rauschen hörst. |
| **🔕 Systemklänge stummschalten, solange der Abend läuft** | Kein Fehler-Ding und kein Benachrichtigungston über die Lautsprecher. Die Systemklänge kommen zurück, wenn du die App schließt. |
| **🎧 Vorhör-Player** | Ein Mini-Player (Spulen, Springen, Lautstärke) schwebt über dem Deck, wenn du auf ein ▶ in einer Zeile klickst. |
| **🖼 Cover anzeigen** | Ein Cover neben dem Titel auf der Player-Karte. Es nimmt das eigene Bild der Wiedergabeliste (`#EXTIMG`), eine Cover-Datei im Ordner oder das Bild in der MP3. |
| **〰 Wellenform anzeigen** | Die [Wellenform](04-playing.md#-die-wellenform) des Titels auf der Player-Karte anstelle des Suchbalkens. |
| **➕ Lautstärke − / + neben dem Regler von Player und Cartwall** | Ab Werk an. Ein − und ein + neben dem Lautstärkeregler des Players und der Cartwall: 2 % je Klick, gehalten gleiten sie. Ein Doppelklick auf die %-Anzeige lässt dich einen Wert eintippen. |
| **⏱ Titel über einer Stunde** | Wie Player und Mini-Player einen Titel zeigen, der länger als 59 Minuten ist, etwa einen langen Mix: **1:04:00 (Stunden)**, die Vorgabe, oder **64:00 (Minuten)**. |
| **🎙 Ansagestimme** | Wer [🔈 Nächsten Tanz ansagen](04-playing.md#-nächsten-tanz-ansagen) spricht: *Weiblich*, *Männlich* oder *Gemischt* (die Vorgabe), was die beiden abwechselt. **…mit Gruppe** fügt die Nummer der Gruppe hinzu, standardmäßig aus. **🔈 Test** spricht ein Beispiel in der gezeigten Stimme, noch vor OK. |
| **📣 „Nächster Tanz“ vor dem Tanz sagen** | Ab Werk aus: Die Pausenansage nennt nur den Tanz, „Rumba“. An, sagt sie „Nächster Tanz: Rumba“ (deutsche Ansagen) bzw. „Next dance: Rumba“ (englische). |
| **🔢 Nur die Gruppe** | Ab Werk aus. An, sagt jede Ansage nur die Gruppe, „Gruppe 1“, nie den Tanz, für einen Trainingsabend: die Pausenansage, die Startansage und die Paso-Doble-Ansage. **…mit Gruppe** und **📣 „Nächster Tanz“** sind dabei ausgegraut. Wo es keine Gruppe zu sagen gibt, wird der Tanz wie sonst angesagt. |
| **🗣 Tanz wird angesagt** | Wo die Ansage sitzt, wenn ein Titel ohne Pause seinen Tanz beim Start nennt: **über den ersten Takten** (die Vorgabe; die Musik wird unter der Stimme leiser) oder **vor dem Musikstart** (die Musik folgt der Ansage). Das ▶ Abspielen-Panel nennt die Wahl kurz: *über der Musik* oder *vor der Musik*. |
| **▶ Player-Position** | Wo die Player-Karte steht: *neben den Wiedergabelisten*, am Kopf des Wiedergabe-Bereichs, oder *über den Wiedergabelisten*, als ein breiter Streifen über den Decks. |
| **📂 Doppelklick auf einen Titel in 📚 der Bibliothek** | Zuletzt auf dem Reiter, unter **📚 Bibliothek**, weil es um die Bibliothek geht, nicht um den Player. Was ein Doppelklick beim Planen in 📚 der Bibliothek und in den Listen unter 🏆 Turniere tut: **Nichts** (ab Werk; ▶ spielt den Titel), **In externem Player öffnen** (das Programm, mit dem dein System Musik abspielt, auf dem Mac Musik; dann auch für eine Deckzeile beim Planen und in den Dialogen) oder **Tags bearbeiten** (der [🏷 Tags-Editor](05-tags.md#den-editor-öffnen), geöffnet auf dem Feld der Spalte, auf die du doppelgeklickt hast; dort wählst du, was Speichern in die Datei schreibt). Beim Planen spielt ein Doppelklick auf eine Deckzeile den Titel im Mini-Player, außer *In externem Player öffnen* ist gewählt. Rechtsklick bietet immer alles davon, und im Abspielmodus spielt oder legt ein Doppelklick den Titel immer bereit. |

### ▸ Erweitert: Absenken und Ausblendzeiten

Unter den Zeilen zur Stimme eingeklappt: die meisten Abende laufen mit den
Vorgaben. Ein Klick auf **▸ Erweitert: Absenken und Ausblendzeiten** öffnet
es.

| Einstellung | Macht |
|---|---|
| **🔉 Absenken auf** | Wie weit 🔊 Absenken alles leiser macht, auf der Player-Karte, im Mini-Player und auf dem Präsentationsbildschirm: 10 % ab Werk (etwa −20 dB), 0 % (Stille) bis 90 %. Eine Änderung gilt auch für ein Absenken, das gerade an ist. |
| **🔈 Unter Ansage oder Pad absenken über … wieder hoch über** | Wie schnell die Musik Platz macht, wenn die Ansage spricht oder ein 🎛 Cartwall-Pad spielt, und wie schnell sie danach zurückkommt: ab Werk 0,2 s hinunter und 0,6 s hinauf, je 0,1 bis 5 s. Der Knopf 🔉 Absenken selbst wirkt sofort. |
| **🌅 Jeden Titel einblenden über** | Ab Werk aus. Der große Player startet jeden Titel in der Stille und blendet ihn über 0,5 bis 10 s Musik ein. Ein Titel, den ein 🔀 Überblenden hereinholt, behält seine eigene Rampe. Paare starten auf dem ersten Taktschlag, lass es für ein Turnier also aus. |
| **🔉↓ Von Hand ausblenden über** | Wie lange 🔉↓ Jetzt ausblenden, 🛑 Ausblenden und halten, ein ⏹ Stopp zu einer Uhrzeit und das Ausblenden vor dem Beenden dauern, bis 10 s. Ab Werk *wie das Ausblenden der Liste*. Das Ausblenden am Ende der Spieldauer behält immer die eigene Ausblendzeit der Liste. |
| **⏩ Jeden Titel so weit drin starten** | Ab Werk aus. Der große Player überspringt die ersten 1 bis 30 s jedes Titels, und diese Sekunden zählen nicht zur Spieldauer. Ein Titel, der an seiner ↩ Marke weiterläuft, startet stattdessen dort, und ein stilles Intro wird zusätzlich übersprungen. |

### 🔈 Ausgänge

Wo welcher Teil des Abends zu hören ist. Jeder Ausgang, den das
Betriebssystem listet, lässt sich wählen, unter Windows, macOS und Linux.

![Einstellungen, Reiter Ton & Player mit den Ausgängen](../img/settings-sound.png)

| Ausgang | Spielt |
|---|---|
| **🎵 Musik** | Die Titel. *Systemstandard (folgt dem System)* geht dorthin, wohin Windows seinen Ton schickt. |
| **🎧 Vorhören** | ▶ in der 📚 Bibliothek und im Bereich 🏆 Turniere, mit einem eigenen Mini-Player, während die Musik weiterläuft. Siehe [Kapitel 4](04-playing.md#-vorhören-über-kopfhörer). |
| **🎛 Cartwall** | Die Pads. |
| **🔈 Ansagen** | Die gesprochenen Ansagen. |

- Jeder Ausgang außer der Musik beginnt auf **Wie die Musik**.
  *Systemstandard* hält einen davon auf dem Standard fest, während die Musik
  woanders spielt.
- Auf einer Soundkarte mit mehreren Ausgängen kann jedes Paar, das das System
  als eigenes Gerät zeigt („Out 3/4“ neben „Out 1/2“), eine eigene Quelle
  bekommen. Ein Gerät, das Windows als *ein* Mehrkanalgerät
  listet, bietet für jede Quelle, die Musik eingeschlossen, „<Karte> — Out
  3/4“ an. Auf einem solchen Kanalpaar verschiebt der Tempo-Regler die
  Tonhöhe mit der Geschwindigkeit, wie ein Plattenspieler, statt sie zu
  halten.
- Eine Karte, die nicht angeschlossen ist, spielt mit einer Meldung auf dem
  Systemstandard, und der Ton geht zurück auf die Karte, sobald sie wieder da
  ist. Das Vorhören ist die Ausnahme, wenn dieser Standard der Ausgang der
  Musik ist: es wird abgelehnt, damit nichts, was für die Kopfhörer gedacht
  ist, über die Anlage geht. Mit nur einem Ausgang gibt es keinen anderen zur
  Wahl, und das Vorhören spielt dort.
- Windows gibt einer neu angesteckten Karte manchmal eine neue Nummer, aus
  `2- ESI Audio Device` wird `3- ESI Audio Device`. Die App findet die Karte
  dann an ihrem Namen wieder, solange nur eine angeschlossene Karte so
  heißt.
- Solange die Karte für die 🎵 Musik angeschlossen ist, zeigt die
  Statusleiste ein kleines **🔊** mit ihrem Namen. Ein Klick darauf öffnet
  diesen Reiter.
- Die Wahl wirkt, sobald du OK klickst, ohne Neustart.

## Cartwall

Der Reiter **🎛 Cartwall** hält, was jedes Pad der
[🎛 Cartwall](04-playing.md#-die-cartwall) befolgt, solange es nichts
Eigenes bekommen hat. Der Modus *Nur Planer* blendet ihn aus.

![Einstellungen, Reiter Cartwall](../img/settings-cartwall.png)

**🎛 Alle Pads**

| Einstellung | Macht |
|---|---|
| **🔈 Während ein 🔈-Pad spielt, wird die Musik abgesenkt auf** | Wie laut die Musik bleibt, solange ein Cartwall-Pad läuft, das die Musik leiser macht: 10 % ab Werk (etwa −20 dB, eine Fanfare setzt sich durch), 0 % (Stille) bis 90 %. Wie 🔉 Absenken auf im Reiter 🔊 Ton & Player ist es ein Anteil an der Lautstärke der Musik, nicht an ihrer Lautheit; der Dialog zeigt die dB daneben. |
| **⏱ Erneut angetippt oder ⏹ — Pad ausblenden über** | Wie lange ein Pad zum Ausklingen braucht, wenn es noch einmal angeklickt wird oder ⏹ Alles stoppen die Wand ausblendet: 1,0 s ab Werk, 0 s (es stoppt sofort) bis 8 s. Auch ein 🎶 Hintergrund-Pad folgt dem. **Eigenes Ausblenden** in den **⚙ Einstellungen…** eines Pads überschreibt es für dieses Pad. |
| **🖌 Standardfarbe der Cartwall** | Die Farbe jedes Pads, das auf 🎨 Farbe ▸ **Cartwall-Standard** steht: ab Werk weiß. Ein Pad mit eigener Farbe behält sie. |

**🎶 Pads mit 🎶 Hintergrund**, in der Reihenfolge, in der ein Hintergrund-Pad sie erlebt:

| Einstellung | Macht |
|---|---|
| **🔉 Haken bei 🎶 Hintergrund setzt die Lautstärke des Pads auf** | Die Bett-Lautstärke, die ein Pad bekommt, wenn man in seinen Einstellungen 🎶 Hintergrund anhakt oder ein Pad auf voller Lautstärke per Strg+Klick in die Warteschlange legt: ab Werk 50 %, denn ein Bett auf voller Lautstärke ist so laut wie die Tanzmusik, die es überbrückt. Nur der Haken setzt sie; ein erneut geöffnetes Bett behält seinen Pegel. |
| **▶ Beim Abfeuern — Pad einblenden über** | Wie lange das Pad braucht, um aus der Stille hochzukommen, wenn es abgefeuert wird: 0,2 s ab Werk. 0 s startet es gleich mit voller Lautstärke. |
| **🎵 Wenn der Hauptplayer einen Titel startet** | Was das Pad tut, sobald die Musik startet: **Stumm weiterlaufen** (ab Werk; es läuft leise weiter und blendet sich wieder ein, wenn die Musik endet) oder **Pausieren** (es hält an seiner Stelle an und läuft von dort weiter, wenn die Musik endet). |
| **🌙 …Pad dabei ausblenden über** | Wie schnell es Platz macht, wenn ein Titel startet: 0,5 s ab Werk. Auch ein Pad auf **Pausieren** blendet erst aus und hält dann an. Hier gibt es nie eine Wartezeit, damit der Teppich nicht über die ersten Töne des Titels spielt. |
| **⏳ Wenn der Hauptplayer stoppt — warten** | Wie lange die Musik gestoppt sein muss, bevor das Pad zurückkommt: 0,3 s ab Werk. Zwischen zwei Titeln stoppt das Deck kurz; die Wartezeit verhindert, dass der Teppich in jeder solchen Lücke anschwillt und gleich wieder abtaucht. Startet während der Wartezeit ein Titel, bleibt der Teppich unten. 0 s holt ihn zurück, sobald die Musik stoppt, auch in den Lücken; viel länger als ab Werk wirkt, als hinke der Teppich hinterher. |
| **🎚 Hauptplayer-Titel schon starten, während der Hintergrund ausblendet** | Ab Werk aus: der Titel wartet, bis das Pad ganz ausgeblendet ist, und startet dann in die Stille. Die Wartezeit ist die Ausblendzeit oben, oder weniger, wenn der Teppich schon nach unten geht. Eingeschaltet startet der Titel sofort und spielt über das Ausblenden. |
| **🌅 …dann Pad wieder einblenden über** | Wie lange es danach braucht, bis es wieder voll da ist: 2,0 s ab Werk. |
| **🐂 Pad unten lassen, solange ein Paso Doble auf den Start wartet** | Ab Werk an. Steht *Start nach* für den 🐂 Paso Doble, hält das Deck zwischen Ansage und erstem Takt an, während die Paare auf die Fläche gehen; das Pad bleibt diese Wartezeit über unten, als liefe die Musik schon. Auch in der Pause vor einem Paso Doble bleibt es unten. Aus kommt es in der Wartezeit zurück wie nach jedem anderen Titel. |

Jede Zeit auf diesem Reiter reicht von 0 s bis 8 s in Schritten von 0,1 s;
0 s heißt sofort, ohne Blende.

Ausblendzeit und Farbe gehören zur Wand, nicht zum PC: eine Cartwall, die
in einem [Hallenpaket](#hallenpaket) auf einen anderen PC geht, nimmt sie
mit.

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

Die von Hand gesetzten PD-Marken, die in der App geänderten Tags und das
Protokoll der [gespielten Titel](04-playing.md#-gespielte-titel) sind die
einzigen Daten, die keine Analyse wiederfindet, deshalb sichert die App sie
selbst: beim ersten Start jedes Tages schreibt sie eine kleine Datei in den
Ordner `backups` neben ihrer Datenbank, bringt sie beim Beenden auf den
neuesten Stand und hebt die letzten sieben auf.
**Sicherungsordner** legt sie stattdessen woanders ab, etwa in einem
Dropbox-Ordner, damit sie nicht nur auf diesem PC liegen; jeder PC schreibt in
einen eigenen Unterordner mit seinem Namen.
**♻ Sicherung der eigenen Daten zurückholen…** spielt eine davon wieder ein;
sie wirkt nach einem Neustart.

**🧱 ALLE Caches aufbauen…** lässt jede Analyse der Reihe nach laufen, für
eine Bibliothek deiner Wahl. Sie lässt sich abbrechen.

**🧹 Datenbank aufräumen…** entfernt zwischengespeicherte Zeilen für Dateien,
die es nicht mehr gibt, und verdichtet die Datenbank. Sie läuft nicht, wenn
das Musiklaufwerk nicht eingebunden aussieht, damit die Analyse nicht aus
Versehen gelöscht wird.

**🗑 Datenbank zurücksetzen…** leert gewählte Teile der Datenbank und startet
die App neu. Ein Dialog fragt, welche, und nichts ist vorab angehakt: **🏷 Aus
den Musikdateien gelesene Tags** (der nächste Bibliotheks-Scan liest sie neu,
Minuten), **🎚 Audio-Analyse** (⚗ Analyse baut sie neu auf, Stunden) und
**✋ Meine eigenen Daten** (Tag-Änderungen, von Hand gesetzte PD-Marken, das
📜 Abspielprotokoll). Deine eigenen Daten werden in jedem Fall vorher
gesichert, **♻ Sicherung der eigenen Daten zurückholen…** holt sie zurück.

## Spiel-Sets

Der Reiter **🎛 Spiel-Sets** legt fest, was die Knöpfe **🏆 Turnier-Set** und
**🎉 Party-Set** im Wiedergabe-Bereich anwenden (siehe
[Kapitel 4](04-playing.md#abspiel-sets)).

![Einstellungen, Reiter Spiel-Sets](../img/settings-play-sets.png)

Eine Liste, die auf einem Set steht, zieht mit, wenn du das Set hier
änderst: jeder Wert, den sie noch vom Set hat, nimmt den neuen an, und ein
Wert, den du an der Liste von Hand geändert hast, bleibt. Die Decks folgen
dem 🏆 Set, der 🤸 Party-Bereich dem 🎉 Set.

Für jedes Set:

- **Spieldauer**: wähl eine, tipp `m:ss` oder Sekunden, oder wähl
  *komplett*.
- **Ausblenden**, in Schritten von einer halben Sekunde, und **innerhalb der
  Spieldauer**: angehakt endet das Ausblenden mit der Spieldauer, nicht
  angehakt kommt es danach. Die Spieldauern je Tanz im 🏆 Set folgen dem
  ebenfalls. Ab Werk blendet das 🏆 Set nach der Spieldauer aus, das 🎉 Set
  darin.
- **🔀 Überblenden**: ein Schalter und 0,5 bis 10 s in Schritten von einer
  halben Sekunde, mit demselben Kurvenknopf (gleiche Leistung, geradlinig oder
  S-Kurve) und Bild wie im Wiedergabe-Bereich. Ab Werk in beiden Sets aus,
  eingeschaltet mit 4 s und gleicher Leistung.
- **⏭ Automatisch weiter**,
  **⏸ Keine Pause zwischen den Titeln**, **🔈 Nächsten Tanz ansagen**,
  **🔊 Lautstärke angleichen**, **▶️ Doppelklick startet den Titel**,
  **❓ Fragen, bevor ein Doppelklick den Titel anhält** und
  **🎚 TSO: auf den Takt der Gruppe ziehen**.

Das Turnier-Set hat außerdem eine Liste mit einer Länge je Tanz, mit einer
Auswahl darüber, **⏱ Längen**: **Pro Tanz — der Standard** oder **Pro
Runde — überschreibt ihn**. Nur bei pro Runde erscheint eine zweite
Auswahl für die Art von Runde: die Vorrunde, die Zwischenrunden (eine
Einstellung für alle), das Semifinale oder das Finale. Die Liste darunter
zeigt die Längen dieser Wahl. Beide gelten, egal welche gerade zu sehen ist.

- **Pro Tanz**: lass einen Tanz auf *— Länge des Sets*, wähl *komplett* oder
  eine Stufe, oder tipp `m:ss`. Ein Tanz mit eigener Dauer wird dort
  geschnitten, solange eine Liste die Dauer des 🏆 Sets spielt, egal was ihre
  anderen Schalter sagen. Ab Werk: 1:30 für Langsamen Walzer, Wiener Walzer,
  Quickstep und Jive, 1:37 für Tango, Slowfox, Samba, Cha-Cha-Cha und Rumba,
  der Paso Doble *komplett*.
- **Paso Doble**: *komplett* oder *nach Highlight 1* oder *2*. Ein
  Schnitt nach Zeit würde ihn mitten in einer Phrase beenden, darum gibt es
  nichts anderes, und ein 3. Highlight kommt so spät, dass es als *komplett*
  gilt. Ein Highlight hakt **🐂 Paso Doble: Stopp nach Highlight** des
  Turnier-Sets an und stellt ein, welches; *komplett* nimmt den Haken weg.
  Wer den Haken setzt, zieht diese Auswahl mit. Jede Liste pro Runde hat
  ihre eigene Paso-Doble-Auswahl: auf *— Länge des Tanzes* läuft er wie hier
  eingestellt; *komplett* oder ein Highlight gilt stattdessen in dieser Art
  von Runde, so kann ein Finale komplett laufen und eine Vorrunde nach dem
  2. Highlight stoppen. Wie die Länge einer Runde zählt sie nur, solange die
  Liste die Dauer des 🏆 Sets spielt.
- **Pro Runde**: ein Tanz kann in dieser Art von Runde anders lang laufen,
  in jeder ihrer Gruppen gleich. Ein Tanz auf *— Länge des Tanzes* spielt
  seine Länge pro Tanz, und ab Werk stehen alle so. Hat eine Runde ihre
  eigene Länge, nennt der Wiedergabe-Bereich die Runde unter den Ziffern,
  z. B. *Wiener Walzer, Finale — eigene Länge*. Eine Liste ohne Runden,
  etwa eine Partyliste, nimmt nur die Längen pro Tanz.

Beide Sets haben auch den 🐂 Paso Doble: **Stopp nach Highlight** (und nach
welchem) und **Start nach**. Von Haus aus ist im Turnier-Set der Stopp aus,
weil die Erkennung nicht zuverlässig genug ist, um einen Paso Doble im
Turnier zu schneiden, und Start nach steht auf 0 s. Das Party-Set stoppt
nach dem 2. Highlight und wartet 1 s, damit die Paare ihre Ausgangsposition
einnehmen können.

**🥇 Finale: Die Musik spielt weiter** gehört zum Turnier-Set. Hat die
Spieldauer einen Titel des Finales ausgeblendet, kommt er als Hintergrund
wieder hoch, während die Paare feiern, bis 🔉↓ ihn ausblendet, der nächste
Titel startet oder die Datei endet. Zwischen zwei Tänzen des Finales spielt
er statt der ⏸ Pausenmusik. Eine Runde ist das Finale, wenn sie *Finale*,
*Final* oder *Endrunde* heißt.

| Einstellung | Macht |
|---|---|
| **Aus / Nach dem letzten Tanz des Finales / Nach jedem Tanz des Finales** | Welche Titel des Finales wieder hochkommen. Ab Werk aus. |
| **Lautstärke** | Wie laut er wiederkommt, in % der Lautstärke der Musik: 60 % ab Werk. |
| **Absenken auf** | Wie weit die Ausblendung am Ende der Spieldauer ihn zuerst absenkt: 5 % ab Werk, 0 % ganz hinunter, höchstens die Lautstärke, mit der er wiederkommt. |
| **Halten** | Wie lange er unten bleibt: 2,0 s ab Werk, 0 s kommt sofort hoch. |
| **Einblenden über** | Wie lange er braucht, um wieder hochzukommen: 3,0 s ab Werk. |
| **Ausblenden über** | Wie lange er an seinem Ende braucht, um zu verklingen, durch 🔉↓ oder bevor der nächste Tanz des Finales startet: 3,0 s ab Werk. |

Die drei Zeiten reichen bis 10 s.

**🎚 TSO-Zieltakt** steht direkt unter dem Turnier-Set. Es legt pro Tanz
fest, auf welches Tempo der Knopf TSO eine Gruppe zieht:

- **Mittelwert der Runde**: bringt die ganze Runde auf ein Tempo, dort, wo
  die meisten ihrer Titel schon liegen. Kein Titel bewegt sich um mehr als
  einen Takt pro Minute.
- **Unten / Mitte / Oben**: ein festes Tempo innerhalb des TSO-Bereichs. Das
  lohnt sich bei den langsamen Tänzen, wo ein Takt pro Minute eine viel
  größere Tempoänderung ist.

## Hallenpaket

Das **📦 Hallenpaket** bringt das ganze Pult in einer Datei auf einen anderen
PC: die Einstellungen, jedes Deck und jede Wunschliste und die 🎛 Cartwall mit
ihren Pads und Tasten. Wenn du willst, kommt auch die Musik mit, die sie
benutzen.

- **📦 Hallenpaket exportieren…** schreibt die Datei. Ein Fortschrittsfenster
  zeigt, wie weit es ist, und kann abbrechen. Vorgeschlagen wird
  `venue-<Datum>.dpvenue`, oder `venue-<Datum>-with-music.dpvenue`, wenn die
  Musik mit hineinkommt.
- **📥 Hallenpaket importieren…** lädt es auf dem anderen PC. Es übernimmt
  Einstellungen, Decks und Cartwall beim nächsten Start; was es ersetzt, wird
  in einem Ordner `before-venue-import` daneben aufgehoben. Musik im Paket
  wird in einen Ordner deiner Wahl ausgepackt, und jedes Deck und jedes Pad
  wird darauf umgehängt.

Ordner-Einstellungen wie die Bibliothek, der Wiedergabelisten- und der
Speichern-unter-Ordner, der Präsentationsbildschirm und das Audio-Backend
bleiben bei jedem PC.

Weiter: [Tastatur und Maus](07-shortcuts.md)
