# 4 · Den Abend fahren

[Zurück zur Übersicht](README.md) · zurück: [Playlists](03-playlists.md)

Die Seitenleiste hält die Player-Karte und darunter den Wiedergabe-Bereich.
Du spielst direkt aus den Decks, dem Party-Bereich und den Wunschlisten.

![Das Hauptfenster beim Abspielen](../img/main-playing.png)

## 🚦 Bereit? vor dem Abend

**🚦 Prüfen ▸ 🚦 Bereit?** in der Werkzeugleiste prüft jedes Deck, das Titel
hält, und die Partyliste in einem Durchgang. Es zeigt eine Ampel pro Prüfung
und ein Gesamturteil: 🟢 *Bereit*, 🟡 *Spielbar, mit offenen Punkten* oder
🔴 *Nicht bereit, manche Titel werden nicht spielen*.

| Zeile | Prüft |
|---|---|
| 📁 Musikdateien | Jede Datei ist da. Ein Laufwerk, das nicht angesteckt ist, wird als solches genannt. Titel, die nicht unter dem Referenzpfad liegen, färben die Zeile gelb. |
| 📊 Lautheit | Jeder Titel ist gemessen, so kann 🔊 Lautstärke angleichen an bleiben. |
| 🔇 Stille-Prüfung | Jeder Titel ist geprüft, so werden seine stillen Ränder übersprungen. |
| 🐂 Paso-Doble-Highlights | Jeder Paso Doble kennt seine Höhepunkte. |
| 🔁 Doppelte | Kein Titel steht in zwei Listen. |
| 🎶 Playlisten | Es gibt überhaupt etwas zu spielen. |

Eine Zeile, die nicht grün ist, hat einen Knopf, der sie behebt:
**📊 Lautheit messen…**, **🐂 Highlights finden…** oder **🔁 Doppelte
auflösen…**. **🧭 Pfade reparieren…** steht jedes Mal in der Zeile
📁 Musikdateien, ob grün oder nicht. Das Fenster bleibt offen, während eine
Behebung läuft; **↻ Nochmal prüfen** bewertet neu. Die volle App ergänzt eine
Zeile 🎵 Musikprüfung für Tempo, Länge und den Aufbau der Runden.

## Einen Titel starten

- **▶** in einer Zeile spielt genau diesen Titel. **■** stoppt ihn.
- Die **Leertaste** pausiert den Player und setzt ihn fort, egal wo der Fokus
  ist, außer in einem Textfeld.
- Ein **Doppelklick** auf eine Zeile startet sie entweder sofort oder legt sie
  nur *bereit*: sie wird geladen und angezeigt, stumm, und ⏯ startet sie. Der
  Schalter dafür ist **▶️ Doppelklick startet den Titel** im
  Wiedergabe-Bereich, siehe unten.
- **Strg + Umschalt + ← / →** springt zum vorigen oder nächsten Titel, und
  **Strg + ← / →** springt 30 s.

Jedes Deck hat in seiner unteren Leiste einen eigenen Schalter
**✋ Manuell / ⏭ Auto**:

- **⏭ Auto**: auf einen fertigen Titel folgt die nächste Zeile, so läuft eine
  ganze Runde ohne Handgriff.
- **✋ Manuell**: du startest jeden Titel selbst. Die gesprochene Ansage ist
  dann ebenfalls aus.

Jede Liste merkt sich ihre eigene Einstellung. Die Partyliste kann von selbst
laufen, während das Turnier-Deck daneben von Hand gestartet wird.

### Ein Titel, der nicht spielt

Ist eine Datei beschädigt oder weg, lässt der Player die Fläche nicht in der
Stille stehen: Er nennt den Titel in einer kurzen Meldung, färbt seine Zeile
rot mit dem Grund im Tooltip und startet den nächsten Titel derselben Runde.
Am Ende einer Runde hält er an, wie nach jedem letzten Titel. Die Markierung
verschwindet, sobald die Datei wieder spielt.

## Die Player-Karte

Die Karte oben in der Seitenleiste zeigt den laufenden Titel, seinen Tanz und
die Restzeit.

| Bedienelement | Macht |
|---|---|
| **\|◀** | Springt zurück auf 0:00 dieses Titels. |
| **⏮ / ⏭** | Voriger / nächster Titel. |
| **◀◀ / ▶▶** | 10 s zurück / vor. |
| **⏯** | Pause / weiter. |
| **🔁** | Wiederholt *diesen* Titel endlos, wenn die Fläche noch voll ist oder eine Rede länger dauert. Das geht auch mit ausgeschaltetem ⏭ Auto. |
| Ausblend-Knopf (durchgestrichener Lautsprecher) | Blendet den Titel jetzt über die Ausblendzeit aus und beendet ihn dann. |
| **☕** | Beendet den Titel und geht direkt zur Pausenmusik. |
| Verlängern-Knopf | Hängt eine weitere Pausenlänge an, wenn der Gruppenwechsel länger dauert. |
| **⊗** | Notfall: blendet die Musik aus und *hält* sie an. Nichts endet und nichts geht weiter. **⏯** setzt genau an dieser Stelle fort. |
| **🔊** | Senkt auf 20 % und wieder auf voll. Die Pausenmusik geht mit herunter. |
| Lautstärkeregler | Gesamtlautstärke. |

### 〰 Die Wellenform

Unter der Zeit liegt die **Wellenform** des laufenden Titels: die leisen
Stellen, die Stille, die übersprungen wird, die Paso-Doble-Höhepunkte und wo
das Ausblenden eines gekürzten Titels beginnt. In den letzten Sekunden wird
sie rot.

- Ein **Klick** springt an diese Stelle. **Ziehen** spult: Abspielkopf und
  Zeiten folgen der Maus, und die Musik springt beim Loslassen. Über den
  linken Rand hinaus gezogen geht es auf 0:00.
- Standardmäßig ersetzt die Wellenform den Suchbalken, der dieselbe Strecke
  abdeckt. Zwei Schalter im Wiedergabe-Bereich, unter *Klang und Anzeige*,
  ändern das: **〰 Wellenform anzeigen** und **…Suchbalken ersetzen**. Ist die
  Wellenform aus, kommt der Suchbalken immer zurück.

Die Tempo-Zeile darunter:

- **Tempo-Regler**: −16 % bis +16 %, ohne die Tonhöhe zu ändern (Time
  Stretch), zum Beispiel um einen Titel auf das Tempo zu ziehen, das das
  Turnier braucht. **− / +** gehen in Schritten, gedrückt gehalten gleiten
  sie. **0** oder ein Doppelklick auf den Regler setzt ihn zurück.
- **TSO**: solange an, wird jeder Titel auf das mittlere Tempo seines Tanzes in
  dieser Runde gezogen, innerhalb des TSO-Bereichs. Eine Rumba mit 23 wird
  T24, ein Paso Doble mit 57 wird T58.
- **📌**: hält das Tempo fest, so bleibt der Regler dort, wo du ihn gelassen
  hast, wenn der nächste Titel startet.
- **♪**: klick im Takt mit, um das tatsächliche Tempo von Hand zu messen. Das
  ist nur eine Anzeige und ändert nichts.

## Der Wiedergabe-Bereich

![Der Wiedergabe-Bereich](../img/playing-panel.png)

### Spieldauer und Ausblenden

- Die große Zahl ist die **Spieldauer**: jeder Titel stoppt nach dieser Zeit.
  **− / +** ändern sie in Schritten. Nach dem letzten Schritt läuft der Titel
  bis zu seinem Ende (**komplett**). Ein Doppelklick auf die Zahl lässt dich
  eine genaue Länge eintippen, zum Beispiel `1:37`.
- **Ausblenden**: die Lautstärke fährt über die letzten Sekunden auf 0.

Sobald die Analyse sie gemessen hat, wird Stille am Anfang und Ende eines
Titels übersprungen.

### 🐂 Paso Doble

**🐂 Paso Doble: Stopp am Höhepunkt**: ein Paso Doble wird nicht ausgeblendet.
Er stoppt an einem Höhepunkt, dem musikalischen Break, auf den die Paare
tanzen.

- **Stopp nach Highlight** wählt welchen, meist den 2.
- Die Höhepunkte findet die Analyse. Fehlt einer oder sitzt er falsch, klick
  während des Abspielens genau auf dem Höhepunkt auf
  **🎯 Highlight jetzt markieren**. **✖** vergisst die gelernten Marken dieses
  Titels.
- **✏️ Highlights bearbeiten** pausiert die Musik und setzt den Stopp aus, so
  kannst du durch den ganzen Titel spulen und seine Marken setzen.
- **Start nach** hält einen Paso Doble vor dem Musikstart zurück, damit die
  Paare ihre Ausgangsposition einnehmen können.

Mit ausgeschaltetem Schalter ist ein Paso Doble ein gewöhnlicher Titel.

### Weiter und Pause

- **⏭ Automatisch zum nächsten Titel**: derselbe Schalter wie ⏭ Auto auf dem
  Deck, das du zuletzt angeklickt hast.
- **🔁 Am Ende von vorn beginnen**: nach dem letzten Titel beginnt die Liste
  von vorn. Braucht das automatische Weiterschalten.
- **Pause zwischen den Titeln**: Zeit für die Paare zum Wechseln oder
  Durchatmen. Aus, folgt der nächste Titel sofort.
- **Pausenmusik**: 📂 wählt einen oder mehrere Titel oder eine `.m3u`, die in
  der Pause laufen. ✕ entfernt sie. **Lautstärke Pausenmusik** legt fest, wie
  laut sie spielt.

### 🔈 Nächsten Tanz ansagen

Die App sagt den nächsten Tanz laut an: „Nächster Tanz: Langsamer Walzer“.

- Mit Pause kommt die Ansage kurz bevor die Pause endet.
- Ohne Pause wird der Tanz genannt, wenn der Titel startet: **über den ersten
  Takten** (die Musik wird unter der Stimme leiser) oder **vor dem
  Musikstart** (die Musik folgt der Ansage).
- **Stimme**: Weiblich, Männlich oder Gemischt, was die beiden abwechselt. Ein
  Tanz, der nie aufgenommen wurde, wird nicht angesagt.
- Die Ansage ist deutsch bei deutscher Oberfläche, und bei einer anderen, wenn
  **Deutsche Tanz- und Rundennamen auch in einer anderssprachigen Oberfläche**
  angehakt ist. Sonst ist sie englisch („Next dance: Slow Waltz“); eine
  Aufnahme, die bei den englischen fehlt, kommt aus den deutschen.
- Mit der erweiterten Ansagesteuerung (⚙ Einstellungen ▸ 🔊 Ton & Player)
  fügt **…mit Gruppe** die Nummer der Gruppe hinzu. **🔈 Test** spricht ein
  Beispiel.

### Klang und Anzeige

- **🔊 Lautstärke angleichen (R128)**: gleicht die Lautheit zwischen den
  Titeln an. Braucht die Lautheitsanalyse.
- **🖼 Cover anzeigen**: ein Cover neben dem Titel im Player. Es nimmt das
  eigene Bild der Playlist (`#EXTIMG`), eine Cover-Datei im Ordner oder das
  Bild in der MP3.
- **〰 Wellenform anzeigen** und **…Suchbalken ersetzen**: die Wellenform auf
  der Player-Karte, siehe [oben](#-die-wellenform).
- **▶️ Doppelklick startet den Titel**: an, spielt ein Doppelklick sofort. Aus,
  legt er den Titel nur bereit, und ⏯ startet ihn. Das ist es, was eine Gruppe
  braucht.
- **↩ Merken, wo ein Titel stehen geblieben ist**: ein Titel, den du verlassen
  hast, startet wieder an dieser Stelle. Die Zeile zeigt **↩ mm:ss**. Die
  Marken werden vergessen, wenn die App schließt.

### Abspiel-Sets

Zwei Knöpfe stellen den ganzen Bereich auf einmal um:

- **🏆 Turnier-Set**: 1:45 Spieldauer mit 3 s Ausblenden, keine Pause, kein
  automatisches Weiterschalten, keine Ansage, angeglichene Lautstärke. Es
  leuchtet golden, solange der Bereich auf diesen Werten steht.
- **🎉 Party-Set**: jeder Titel in voller Länge mit 3 s Ausblenden,
  automatisch weiter, keine Pause, keine Ansage und angeglichene Lautstärke.
  Es wird von selbst angewandt, wenn du aus dem 🤸 Party-Bereich spielst, und
  zurückgeschaltet, wenn ein Turnier-Deck übernimmt.

Was jedes Set enthält, legst du selbst fest, unter
[⚙ Einstellungen ▸ 🎛 Spiel-Sets](06-settings.md#spiel-sets).

### 🖥 Präsentation

**🖥 Präsentation** öffnet ein zweites Vollbildfenster für einen Beamer oder
einen Monitor, der zur Fläche zeigt. Es zeigt den laufenden Titel mit seinem
Tanz und die nächsten drei Titel.

![Der Präsentationsbildschirm](../img/presenter.png)

- Das Feld daneben wählt den Bildschirm.
- **🎨 Design**: *Default* ist die schwarze Hallenanzeige. *Light* ist cremefarbenes
  Papier mit warmer brauner Schrift, für einen hellen Raum.
- **🕒** hält einen Zeitplan für den Abend, etwa Essen oder den
  Eröffnungstanz. Er ist eine zweite Seite der Präsentation. **T** schaltet
  dort zwischen den Seiten um.
- **Esc** schließt die Präsentation. Ein Doppelklick darauf verlässt den
  Vollbildmodus.

**☀ Bildschirm wach halten** hält Bildschirmschoner und Bildschirm-Abschaltung
auf, solange Musik läuft oder die Präsentation offen ist.

## 🎛 Die Cartwall

**🎛 Cartwall** in der Werkzeugleiste zeigt eine Wand aus Sample-Pads:
Fanfaren, ein Trommelwirbel, die Nationalhymne, ein Jingle für die
Siegerehrung.

![Die Cartwall rechts neben den Decks angedockt](../img/main-cartwall.png)

- Ein **Klick auf ein Pad** feuert es über die laufende Musik. Noch ein Klick
  blendet es aus.
- **Strg + 1 … 9** feuern die ersten neun Pads der sichtbaren Seite.
- **⏹ Alles stoppen** oder **Esc** blendet jedes Pad aus.
- **✏** entsperrt die Wand zum Bauen. Zieh Audiodateien auf ein Pad, um es zu
  füllen. Eine Mehrfachauswahl füllt die freien Pads danach. Zieh ein Pad auf
  ein anderes, um die beiden zu tauschen. Sperr die Wand vor dem Turnier
  wieder, damit nichts aus Versehen verrutscht.
- Ein **Rechtsklick auf ein Pad** bietet seine 🎨 Farbe oder
  **⚙ Einstellungen…** für Beschriftung, Lautstärke, eigene Taste,
  🔁 endlose Wiederholung und ob es die Musik leiser macht.
- Die Seitenpfeile schalten die Seiten um. Ein Doppelklick auf den Seitennamen
  benennt die Seite um. Das Größenfeld legt das Raster fest, zum Beispiel
  2 × 7. Ein kleineres Raster verliert nie ein Pad.
- **🗂** exportiert oder importiert die Wand oder packt alle Pads auf eine
  Seite.
- Zieh die Wand links oder rechts ans Fenster, unter die Decks oder als
  eigenes Fenster hinaus. **📌** holt eine schwebende Wand zurück.

## 📱 Die Handy-Fernbedienung

Die Handy-Fernbedienung steuert das Pult aus dem Browser eines Handys, im
selben Netz wie der PC. Eine App musst du nicht installieren. Vom Handy aus
kannst du:

- sehen, was läuft und was als Nächstes kommt;
- abspielen und pausieren, zum vorigen oder nächsten Titel gehen;
- ausblenden, oder ausblenden und halten;
- **🔈 Nächsten Tanz ansagen** ein- oder ausschalten. Es ist derselbe
  Schalter wie im Wiedergabe-Bereich, Stimme und Zeitpunkt folgen also;
- den Fortschrittsbalken ziehen, um zu spulen. Die Stelle unter deinem
  Finger ist die Stelle, die die Fläche hört;
- die Pads der sichtbaren Cartwall-Seite feuern oder alle stoppen.

![Die Handy-Fernbedienung im Browser eines Handys](../img/phone-remote.png)

**Zum Starten** klickst du **📱 Handy-Fernbedienung…** im Wiedergabe-Bereich
oder **📱 Server starten** unter ⚙ Einstellungen ▸ ⚙ Allgemein. Das Fenster
der Fernbedienung öffnet sich:

- **● Läuft / ○ Gestoppt** mit **▶ Starten / ■ Stoppen**;
- ein **QR-Code**: scann ihn mit der Kamera des Handys, und das Handy ist
  drin, ohne die PIN zu tippen;
- die Adresse, mit einer Auswahl, wenn der PC in mehr als einem Netz hängt,
  und ein Link, der die Fernbedienung zum schnellen Test im Browser dieses
  PCs öffnet;
- die **PIN** und **Neue PIN**, die ein laufender Server sofort übernimmt;
- ein **Protokoll** dessen, was beim Server ankam: Handys, die die Seite
  geöffnet haben, Anmeldungen, falsche PINs und jeder Befehl.

Solange der Server läuft, trägt die Statusleiste ein grünes Abzeichen
**📱 LIVE**; ein Klick darauf holt das Fenster zurück. In ⚙ Einstellungen heißt
der Knopf dann **📱 Server stoppen**.

- Nur Handys im lokalen Netz kommen hinein, und nur mit der PIN. Falsche PINs
  sperren ein Handy eine Weile aus, und nach 30 falschen PINs aus dem ganzen
  Netz binnen zehn Minuten kommt kein neues Handy mehr hinein; Handys, die schon
  drin sind, laufen weiter.
- Die PIN geht unverschlüsselt übers Netz (einfaches HTTP). Im eigenen Netz ist
  das in Ordnung. In einem offenen WLAN der Halle könnte sie jeder darin
  mitlesen; nimm dort wenn möglich einen Handy-Hotspot oder einen eigenen Router
  für das Pult.
- Beim ersten Mal fragt Windows vielleicht, ob die App das Netz nutzen darf.
  Erlaube es für private Netze. Taucht nichts im Protokoll auf, während das
  Handy es versucht, steht eine Firewall im Weg; das Fenster nennt das
  Programm, das du freigeben musst.
- Der Server läuft nur so lange wie die App. Jeder Start beginnt ohne ihn.

## 🎛 Ein DJ-Controller

Ein USB-MIDI- oder HID-Controller kann das Pult mit echten Tasten und einem
Fader steuern. Eingerichtet wird er unter ⚙ Einstellungen ▸ ⚙ Allgemein ▸
🎛 DJ-Controller ▸ **🎛 Einrichten…**.

Was er auslösen kann:

- ⏯ Abspielen / Pause, ⏭ Nächster Titel, ⏮ Vorheriger Titel;
- 🔉↓ Jetzt ausblenden, 🛑 Ausblenden und halten;
- 🔉 Musik absenken an / aus, 🔈 Nächsten Tanz ansagen an / aus;
- 🔊 Musiklautstärke, über einen Fader oder einen Regler;
- ⏹ Alle Pads stoppen, und sechzehn Cartwall-Pads: Pad *n* ist das *n*-te
  Pad der sichtbaren Seite, wie bei **Strg + *n***.

Im Fenster:

![Das Controller-Fenster mit dem Profil für den nanoKONTROL2](../img/controller.png)

1. Wähl den Controller unter **Gerät**. **↻** sucht nach neuen. Hak **Alle
   HID-Geräte zeigen, nicht nur DJ-Controller** an, wenn deiner fehlt.
2. **Vorlagen ▾** hält ein fertiges Profil für den Korg nanoKONTROL2.
3. Für jeden anderen Controller klickst du **Anlernen** neben einer Aktion
   und drückst die Taste oder bewegst den Fader, auf die sie hören soll.
   **✕** löst die Zuordnung. Die Zeile unter der Tabelle zeigt das zuletzt
   berührte Bedienelement.
4. **💾 Profil speichern…** und **📂 Profil laden…** halten eine Belegung als
   Datei fest, zum Beispiel für den PC in der Halle.

Der Controller wirkt, sobald du ihn einrichtest, und wird gemerkt. Wird er
abgezogen, sucht die App alle paar Sekunden wieder nach ihm. MIDI geht unter
Windows, macOS und Linux.

## 📜 Gespielte Titel

Im Spielmodus schreibt die App jeden Titel auf, sobald er 10 Sekunden
gelaufen ist, also in dem Moment, in dem seine Zeile grau wird: mit
Startzeit, Interpret, Tanz und Liste. Vorhören beim Planen wird nie
protokolliert. **❔ ▸ 📜 Gespielte Titel…** listet die Abende, der neueste
oben; eine Pause von mehr als vier Stunden beginnt einen neuen, damit eine
Party über Mitternacht ein Abend bleibt.

- Klick auf einen Abend, um seine Titel zu sehen und wie lange jeder lief.
- **💾 Als CSV speichern…** speichert den Abend als Tabelle für Excel, zum
  Beispiel für eine GEMA-Meldung: Datum, Start, Interpret, Titel, Tanz, Liste
  und Dauer.
- **🗑 Abend löschen** entfernt ihn nach einer Rückfrage aus dem Protokoll.

Weiter: [Tags](05-tags.md)
