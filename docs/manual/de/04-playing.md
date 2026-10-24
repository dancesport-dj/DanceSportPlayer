# 4 · Den Abend fahren

[Zurück zur Übersicht](README.md) · zurück: [Playlists](03-playlists.md)

Die Seitenleiste hält die Player-Karte und darunter den Wiedergabe-Bereich.
Du spielst direkt aus den Decks, dem Party-Bereich und den Wunschlisten.

![Das Hauptfenster beim Abspielen](../img/main-playing.png)

## 🚦 Bereit? vor dem Abend

**🚦 Prüfen ▸ 🚦 Bereit?** in der Werkzeugleiste prüft jedes Deck, das Titel
hält, und die Partyliste in einem Durchgang. Es zeigt eine Ampel pro Prüfung
und ein Gesamturteil: 🟢 *Bereit*, 🟡 *Spielbar, mit offenen Punkten* oder
🔴 *Nicht bereit*: Manche Titel werden nicht spielen, oder ein Audioausgang
ist nicht angeschlossen.

| Zeile | Prüft |
|---|---|
| 📁 Musikdateien | Jede Datei ist da. Ein Laufwerk, das nicht angesteckt ist, wird als solches genannt. Titel, die nicht unter dem Referenzpfad liegen, färben die Zeile gelb. |
| 📊 Lautheit | Jeder Titel ist gemessen, so kann 🔊 Lautstärke angleichen an bleiben. |
| 🔇 Stille-Prüfung | Jeder Titel ist geprüft, so werden seine stillen Ränder übersprungen. |
| 🐂 Paso-Doble-Highlights | Jeder Paso Doble kennt seine Höhepunkte. |
| 🔁 Doppelte | Kein Titel steht in zwei Listen. |
| 🎶 Playlisten | Es gibt überhaupt etwas zu spielen. |
| 🔈 Audioausgänge | Jeder Ausgang, der in ⚙ Einstellungen → 🔊 Ton & Player gewählt ist, ist angeschlossen. Fehlt die Karte für die Musik, die Pausenmusik, die Cartwall oder die Ansagen, ist die Zeile rot: Diese Quelle spielt dann auf dem Systemstandard. Fehlt die Karte fürs 🎧 Vorhören, ist sie gelb, ebenso wenn das Vorhören auf dem Ausgang der Musik läge, denn dann würde jedes Vorhören abgelehnt. Steht das Vorhören auf *Wie die Musik*, ist sie auch gelb, denn der Saal hört jedes Vorhören mit. Mit nur einem Ausgang gibt es keinen anderen zur Wahl, dann meldet die Zeile nichts. |
| 🎛 Controller | Der gewählte Hardware-Controller ist verbunden. Nicht jeder Abend braucht einen, darum ist diese Zeile höchstens gelb, und sie fehlt, solange kein Controller eingerichtet ist. |
| ☀ Bildschirm und Ruhezustand | ☀ Bildschirm wach halten ist an, also bleiben Bildschirm, Beamer und Computer wach, solange Musik läuft oder der Präsentationsbildschirm offen ist. |

Eine Zeile, die nicht grün ist, hat einen Knopf, der sie behebt:
**📊 Lautheit messen…**, **🐂 Highlights finden…**, **🔁 Doppelte
auflösen…**, **⚙ Ausgänge wählen…**, **🎛 Controller öffnen…** oder
**☀ Wach halten**. **🧭 Pfade reparieren…** steht jedes Mal in der Zeile
📁 Musikdateien, ob grün oder nicht. Das Fenster bleibt offen, während eine
Behebung läuft; **↻ Nochmal prüfen** bewertet neu. Die volle App ergänzt eine
Zeile 🎵 Musikprüfung für Tempo, Länge und den Aufbau der Runden.

## Einen Titel starten

- **▶** in einer Zeile spielt genau diesen Titel. **■** stoppt ihn.
- Die **Leertaste** pausiert den Player und setzt ihn fort, egal wo der Fokus
  ist, außer in einem Textfeld und in einer anderen Liste mit einem gewählten
  Titel: dort startet sie diesen Titel.
- **Eingabe** startet den in der Liste im Fokus gewählten Titel, auch in der
  Liste, die gerade spielt.
- Ein **Doppelklick** auf eine Zeile startet sie entweder sofort oder legt sie
  nur *bereit*: sie wird geladen und angezeigt, stumm, und ⏯ startet sie. Der
  Schalter dafür ist **▶️ Doppelklick startet den Titel** im
  Wiedergabe-Bereich, siehe unten.
  Während ein Titel läuft, fragt der Doppelklick erst nach (**Laufenden Titel
  anhalten?**), und **Nein** lässt die Musik an. Ob er fragt, legt jedes
  Spiel-Set fest, mit **❓ Fragen, bevor ein Doppelklick den Titel anhält**
  unter [⚙ Einstellungen ▸ 🎛 Spiel-Sets](06-settings.md#spiel-sets); in
  beiden an.
- **Strg + Umschalt + ← / →** springt zum vorigen oder nächsten Titel, und
  **Strg + ← / →** springt 30 s.

Jedes Deck hat in seiner unteren Leiste einen eigenen Schalter
**✋ Manuell / ⏭ Auto**:

- **⏭ Auto**: auf einen fertigen Titel folgt die nächste Zeile, so läuft eine
  ganze Runde ohne Handgriff.
- **✋ Manuell**: du startest jeden Titel selbst. Die gesprochene Ansage ist
  dann ebenfalls aus. Endet ein Titel, durch Ausblenden, die Spieldauer oder
  sein natürliches Ende, liegt die nächste Zeile stumm bei 0:00 auf der
  Player-Karte bereit, ihre Zeile markiert. **⏯** startet sie, und **⏭** geht
  von dort weiter.

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
| **☕** | Beendet den Titel und geht direkt zur Pausenmusik. Nur da, solange **Pause zwischen den Titeln** an ist. |
| Verlängern-Knopf | Hängt eine weitere Pausenlänge an, wenn der Gruppenwechsel länger dauert. |
| **⊗** | Notfall: blendet die Musik aus und *hält* sie an. Nichts endet und nichts geht weiter. **⏯** setzt genau an dieser Stelle fort. |
| **🔊** | Senkt auf 20 % und wieder auf voll. Die Pausenmusik geht mit herunter. Wie weit, stellst du unter ⚙ Einstellungen ▸ 🔊 Ton & Player ▸ **🔉 Absenken auf** ein. |
| Lautstärkeregler | Gesamtlautstärke. |

### 〰 Die Wellenform

Unter der Zeit liegt die **Wellenform** des laufenden Titels: die leisen
Stellen, die Stille, die übersprungen wird, die Paso-Doble-Höhepunkte und wo
das Ausblenden eines gekürzten Titels beginnt. In den letzten Sekunden wird
sie rot.

Eine **grüne Linie** markiert, wo der Titel beginnt, wenn er nicht bei 0:00
startet: nach einem Vorlauf, an einem Fortsetzungspunkt oder hinter einem
übersprungenen stillen Intro. Die Strecke davor ist abgedunkelt. Mit
🌅 Einblenden ist das Einblenden **gold** getönt, das Spiegelbild des rötlich
getönten Ausblendens. Ein Titel, den eine 🔀 Überblendung hereinholt, hat
keine Goldtönung, denn die Überblendung blendet ihn ein.

- Ein **Klick** springt an diese Stelle. **Ziehen** spult: Abspielkopf und
  Zeiten folgen der Maus, und die Musik springt beim Loslassen. Über den
  linken Rand hinaus gezogen geht es auf 0:00.
- Die Wellenform ersetzt den Suchbalken, der dieselbe Strecke abdeckt: Man
  sieht das eine oder das andere, nie beides. Den Suchbalken bringt
  **〰 Wellenform anzeigen** zurück, ausgeschaltet unter
  [⚙ Einstellungen ▸ 🔊 Ton und Player](06-settings.md#ton-und-player).

Die Tempo-Zeile darunter:

- **Tempo-Regler**: −16 % bis +16 %, ohne die Tonhöhe zu ändern (Time
  Stretch), zum Beispiel um einen Titel auf das Tempo zu ziehen, das das
  Turnier braucht. **− / +** gehen in Schritten, gedrückt gehalten gleiten
  sie. **0** oder ein Doppelklick auf den Regler setzt ihn zurück. Auch
  [Pult-Tasten](#-pult-tasten) und ein Drehregler am
  [DJ-Controller](#-ein-dj-controller) bewegen ihn.
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
- **innerhalb der Spieldauer**: angehakt endet das Ausblenden mit der
  Spieldauer, ein Titel mit 1:45 und 3 s Ausblenden wird also ab 1:42 leiser.
  Nicht angehakt läuft der Titel die vollen 1:45 und wird danach ausgeblendet,
  er endet also bei 1:48.

Sobald die Analyse sie gemessen hat, wird Stille am Anfang und Ende eines
Titels übersprungen.

### 🐂 Paso Doble

**🐂 Paso Doble: Stopp am Höhepunkt**: ein Paso Doble wird nicht ausgeblendet.
Er stoppt an einem Höhepunkt, dem musikalischen Break, auf den die Paare
tanzen.

- **Stopp nach Highlight** wählt welchen, meist den 2.
  Hat eine Runde in ⚙ Einstellungen → 🎛 Spiel-Sets einen eigenen Wert,
  zeigt die Zahl diesen, solange die Liste die Länge des 🏆-Sets spielt
  (eine Runde *ganz* zeigt 3). Wer sie dort ändert, ändert den Wert nur
  für diese Liste; zurückgedreht, oder mit dem 🏆-Set neu gesetzt, gilt
  wieder der Wert der Runde.
- Die Höhepunkte stehen in der Wellenform und unter **✏️ Highlights
  bearbeiten** auch dann, wenn der Paso Doble ganz läuft.
- Die Höhepunkte findet die Analyse. Fehlt einer oder sitzt er falsch, klick
  während des Abspielens genau auf dem Höhepunkt auf
  **🎯 Highlight jetzt markieren**. **✖** vergisst die gelernten Marken dieses
  Titels.
- **✏️ Highlights bearbeiten** pausiert die Musik und setzt den Stopp aus, so
  kannst du durch den ganzen Titel spulen und seine Marken setzen.
- **Start nach** hält einen Paso Doble vor dem Musikstart zurück, damit die
  Paare ihre Ausgangsposition einnehmen können. Die Player-Karte zählt die
  Wartezeit dort herunter, wo die Werte des Titels stehen, mit dem Takt, in dem er läuft, *🐂 PD T60 in 5 s*,
  wie sie eine Pause herunterzählt; die Werte kommen zurück, sobald die
  Musik startet. Ein Paso Doble, der an seiner
  ↩-Marke wieder aufgenommen wird, startet sofort: die Paare stehen noch auf
  der Fläche.

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
  laut sie spielt. Ein 🎶 Hintergrund-Pad der Cartwall weicht der
  Pausenmusik wie einem Titel.
- **🔀 Überblenden**: die letzten Sekunden eines Titels und die ersten des
  nächsten spielen zusammen. Der alte blendet aus, während der neue einblendet,
  so hört die Fläche nie eine Lücke. Die Beschriftung ist ein Schalter: aus,
  endet ein Titel und dann beginnt der nächste. Die Sekunden daneben (0,5 bis
  10, in halben Sekunden) bleiben eingestellt, solange er aus ist, sodass er
  beim Einschalten auf ihnen weitermacht; beim ersten Mal sind es 4 s. Das
  kleine Bild zeigt die
  Überblendung wie ein DJ-Mixer: rot der ausgehende Titel, grün der kommende,
  und je steiler das Kreuz, desto kürzer die Überblendung. *aus* ist ein harter
  Schnitt.

  Der Knopf links vom Bild wählt die Form der Überblendung, und das Bild folgt
  ihm:
  - **gleiche Leistung** (Standard): die beiden Titel ergeben zusammen einen
    gleichmäßigen Pegel über die ganze Strecke, richtig für zwei verschiedene
    Songs.
  - **geradlinig**: zwei gerade Linien, wie ein einfacher Mischpult-Fader es
    macht, in der Mitte etwas leiser.
  - **S-Kurve**: gleichmäßig wie gleiche Leistung, aber an beiden Enden
    langsam: der neue Titel ist anfangs kaum da, der alte klingt noch nach.

  Eine Überblendung, die schon läuft, behält die Form, mit der sie begann.
  Rund um sie wandert eine gelbe Linie durch das Bild, mit einem Punkt auf
  jeder Kurve, wo die beiden Titel gerade stehen. Sie kommt einige Sekunden
  vor der Überblendung am linken Rand herein, erreicht die Rampe genau, wenn
  der nächste Titel einsetzt, und geht danach am rechten Rand hinaus. So
  sieht man eine Überblendung kommen.

  Sie passiert nur, wo die Liste von selbst ohne Pause weiterläuft. Eine Pause,
  ⏭ automatisches Weiterschalten aus, das 🏁 Ende einer Runde, ein 🔁 Titel,
  ein 🐂 Paso Doble bis zum Höhepunkt und ein 🔉↓ Ausblenden von Hand behalten
  das gewohnte Ende. Solange eine Pause an ist, verschwindet die Zeile: eine
  Pause braucht kein Überblenden, und was der Pausenschalter zeigt, steht
  direkt unter ihm. ⏭ blendet genauso in
  den nächsten Titel über, auch in die nächste Runde. ⏹, ⏭ oder ein Klick
  auf einen anderen Titel während der Überblendung schneidet den alten
  Titel sofort ab. Jede Playlist behält ihren eigenen Wert.

### 🔈 Nächsten Tanz ansagen

Die App sagt den nächsten Tanz laut an: „Nächster Tanz: Langsamer Walzer“.

- Mit Pause kommt die Ansage kurz bevor die Pause endet.
- Ohne Pause wird der Tanz genannt, wenn der Titel startet: **über den ersten
  Takten** (die Musik wird unter der Stimme leiser) oder **vor dem
  Musikstart** (die Musik folgt der Ansage), je nach ⚙ Einstellungen ▸
  🔊 Ton & Player.
- Mit 🔀 Überblenden wird der Tanz genannt, sobald die Überblendung durch
  ist, über der Musik, egal was eingestellt ist. Ein 🐂 Paso Doble mit
  Wartezeit vor dem Start wird nur einmal genannt, zu Beginn der Wartezeit.
- Stimme, Gruppennummer und über/vor der Musik werden unter ⚙ Einstellungen
  ▸ 🔊 Ton & Player eingestellt (siehe [Einstellungen](06-settings.md)).
  Solange der Schalter an ist, nennt eine Zeile darunter die Wahl kurz, etwa
  *Gemischte Stimmen · mit Gruppe · über der Musik*. Beim Überblenden fehlt
  der letzte Teil. Ein Tanz, der nie aufgenommen wurde, wird nicht angesagt.
- Die Ansage ist deutsch bei deutscher Oberfläche, und bei einer anderen, wenn
  **Deutsche Tanz- und Rundennamen auch in einer anderssprachigen Oberfläche**
  angehakt ist. Sonst ist sie englisch („Next dance: Slow Waltz“); eine
  Aufnahme, die bei den englischen fehlt, kommt aus den deutschen.

### Klang und Anzeige

- **🔊 Lautstärke angleichen (R128)**: gleicht die Lautheit zwischen den
  Titeln an. Braucht die Lautheitsanalyse.
  Dabei bleibt der True Peak jedes Titels bei höchstens −1 dBTP: ein
  leiser Titel, der beim Anheben übersteuern würde, wird weniger
  angehoben, und einer, der über die Grenze gemastert ist, wird leiser.
  Ein Titel, den eine ältere Version gemessen hat, wird im Hintergrund
  neu gemessen.
- **▶️ Doppelklick startet den Titel**: an, spielt ein Doppelklick sofort. Aus,
  legt er den Titel nur bereit, und ⏯ startet ihn. Das ist es, was eine Gruppe
  braucht.
- **↩ Merken, wo ein Titel stehen geblieben ist**: ein Titel, den du verlassen
  hast, startet wieder an dieser Stelle. Die Zeile zeigt **↩ mm:ss**. Die
  Marken werden vergessen, wenn die App schließt.

### Abspiel-Sets

Zwei Knöpfe stellen den ganzen Bereich auf einmal um:

- **🏆 Turnier-Set**: 1:45 Spieldauer, danach 2,5 s Ausblenden, keine Pause,
  kein Überblenden, kein automatisches Weiterschalten, keine Ansage, angeglichene Lautstärke.
  Es stellt auch den 🐂 Paso Doble auf die Werte des Sets: von Haus aus den
  Stopp aus und Start nach auf 0 s. Es leuchtet golden, solange der Bereich
  auf diesen Werten steht.
- **🎉 Party-Set**: jeder Titel in voller Länge mit 3 s Ausblenden darin,
  kein 🔀 Überblenden, automatisch weiter, keine Pause, keine Ansage und angeglichene Lautstärke.
  Der 🐂 Paso Doble stoppt nach seinem 2. Highlight und startet nach 3 s.
  Es wird von selbst angewandt, wenn du aus dem 🤸 Party-Bereich spielst, und
  zurückgeschaltet, wenn ein Turnier-Deck übernimmt.

Ein leuchtendes Set schaltest du mit einem zweiten Klick wieder aus: die
Liste kehrt zu den Werten zurück, auf denen sie vorher stand. Gibt es nichts
zum Zurückkehren, etwa nach einem Neustart der App, bleibt das Set an, und ein
Hinweis sagt das.

Was jedes Set enthält, legst du selbst fest, unter
[⚙ Einstellungen ▸ 🎛 Spiel-Sets](06-settings.md#spiel-sets).

Das Turnier-Set kann einem Tanz auch **eine eigene Spieldauer** geben, zum
Beispiel 1:30 für den Wiener Walzer und 1:37 für den Tango. Solange
eine Liste die Dauer des 🏆 Sets spielt, zeigt die große Zahl die Dauer dieses Tanzes,
und darunter steht der Tanz in Gold. Das ist der Tanz, der gerade spielt, sonst
die gewählte Zeile. **− / +** und Eintippen ändern dann die Dauer dieses Tanzes,
nicht die der Liste. Nur die Dauer zählt: ⏭ Auto, die Pause oder jeder andere
Schalter darf vom Set abweichen. Änderst du die Dauer der Liste von Hand, gilt
ab dann ihre eine Dauer für jeden Tanz. Ab Werk spielt das
🏆 Set 1:30 für Langsamen Walzer, Wiener Walzer, Quickstep und Jive und 1:37
für Tango, Slowfox, Samba, Cha-Cha-Cha und Rumba. Der Paso Doble läuft
komplett oder bis zu seinem Highlight, siehe
[⚙ Einstellungen ▸ 🎛 Spiel-Sets](06-settings.md#spiel-sets).

### 🖥 Präsentation

**🖥 Präsentation** öffnet ein zweites Vollbildfenster für einen Beamer oder
einen Monitor, der zur Fläche zeigt. Es zeigt den laufenden Titel mit seinem
Tanz und die nächsten drei Titel.

![Der Präsentationsbildschirm](../img/presenter.png)

- Das Feld daneben wählt den Bildschirm.
- **🕒**, am Ende derselben Zeile, hält einen Zeitplan für den Abend, etwa Essen oder den
  Eröffnungstanz. Er ist eine zweite Seite der Präsentation. **T** schaltet
  dort zwischen den Seiten um.
- **Esc** schließt die Präsentation. Ein Doppelklick darauf verlässt den
  Vollbildmodus.

Ihre Farben stellst du unter
[⚙ Einstellungen ▸ 🎨 Aussehen](06-settings.md#aussehen) ein.

**☀ Bildschirm wach halten** hält Bildschirmschoner und Bildschirm-Abschaltung
auf, solange Musik läuft oder die Präsentation offen ist.

## 🎧 Vorhören über Kopfhörer

Mit einem zweiten Ausgang, zum Beispiel Kopfhörern am Pult, hörst du einen
Titel vor, während der Saal die Musik hört. Wähl diesen Ausgang unter
[⚙ Einstellungen ▸ 🔊 Ton & Player ▸ 🔈 Ausgänge ▸ 🎧 Vorhören](06-settings.md#-ausgänge).

- **▶** in der 📚 Bibliothek und im Bereich 🏆 Turniere spielt dann auf dem
  Vorhör-Ausgang. Die Musik läuft weiter.
- Das Vorhören hat einen eigenen Mini-Player mit Suchbalken, ⏮ / ⏭ und
  Lautstärke. **✕** darauf stoppt nur das Vorhören.
- **Strg+←/→** springt im Vorhören um 30 s, solange es läuft, in den
  Bereichen und Fenstern, die vorhören. Auf einer Deck-Zeile springen sie
  weiter in der Musik.
- **▶** in einer Deck-Zeile startet weiterhin die Musik für den Saal.
- Ist der Vorhör-Ausgang nicht angeschlossen, spielt er auf dem
  Systemstandard. Ist dieser Standard der Ausgang der Musik, wird das
  Vorhören mit einer Meldung abgelehnt: ein Vorhören über die Anlage ist
  schlimmer als keins. Ein Computer mit nur einem Ausgang hat keinen
  anderen zur Wahl, dort spielt das Vorhören auf ihm.
- Steht er auf **Wie die Musik**, spielt ▶ in der 📚 Bibliothek und im Bereich
  🏆 Turniere trotzdem in diesem Mini-Player, auf dem Ausgang der Musik und
  neben ihr. Der Haupt-Player und seine Karte bleiben, wie sie sind. Ein ▶ im
  Deck stoppt es.

## 🎛 Die Cartwall

**🎛 Cartwall** in der Werkzeugleiste zeigt eine Wand aus Sample-Pads:
Fanfaren, ein Trommelwirbel, die Nationalhymne, ein Jingle für die
Siegerehrung.

![Die Cartwall rechts neben den Decks angedockt](../img/main-cartwall.png)

- Ein **Klick auf ein Pad** feuert es über die laufende Musik. Noch ein Klick
  blendet es aus, in 1 s. ⚙ Einstellungen ▸ 🎛 Cartwall ▸
  **⏱ Pads blenden aus über** stellt diese Zeit für die ganze Wand ein; **Eigenes Ausblenden** in den
  **⚙ Einstellungen…** eines Pads gibt ihm eine eigene.
- **Strg + 1 … 9** feuern die ersten neun Pads der sichtbaren Seite.
- **⏹ Alles stoppen** oder **Esc** blendet jedes Pad aus.
- **🔊** daneben ist die eigene Lautstärke der Cartwall, für alle Pads. Sie
  ist von der Musiklautstärke getrennt: wird die Musik leiser gezogen,
  bleiben die Pads, wo sie sind. Die Lautstärke eines Pads (in seinen
  **⚙ Einstellungen…**) gilt relativ dazu. Die Tasten
  **Strg + Alt + ↑ / ↓** und ein Controller-Fader stellen sie auch.
- **✏** entsperrt die Wand zum Bauen. Zieh Audiodateien auf ein Pad, um es zu
  füllen. Eine Mehrfachauswahl füllt die freien Pads danach. Zieh ein Pad auf
  ein anderes, um die beiden zu tauschen. Sperr die Wand vor dem Turnier
  wieder, damit nichts aus Versehen verrutscht.
- Bei eingeschaltetem **✏** bietet ein **Rechtsklick auf ein Pad** seine
  🎨 Farbe, 🗑 Leeren oder **⚙ Einstellungen…** für Beschriftung,
  Lautstärke, eigene Taste, 🔁 endlose Wiederholung und ob es die Musik
  leiser macht. Bei gesperrter Wand bietet der Rechtsklick
  **⚙ Cartwall-Einstellungen…**, das die ⚙ Einstellungen auf ihrem Reiter
  [🎛 Cartwall](06-settings.md#cartwall) öffnet, und **⌨ Tastenkürzel…**.
- **🎶 Hintergrund** dreht das um: Das Pad selbst verstummt, solange ein
  Titel läuft, und blendet sich wieder ein, sobald der Titel zu Ende ist. Das passt für eine
  Hintergrundmusik, die den ganzen Abend läuft. Ein Hintergrund-Pad macht
  die Musik nie leiser. Soll es stattdessen pausieren, siehe ⚙ Einstellungen ▸
  🎛 Cartwall ▸ **🎶 Hintergrund-Pads, wenn ein Titel startet**.
- **S Die anderen Pads stoppen** in den **⚙ Einstellungen…** eines Pads
  blendet alle anderen laufenden Pads aus, sobald dieses startet. Das passt
  für eine Hymne oder eine Siegerfanfare, die den Raum braucht.
- Die Fläche eines Pads zeigt, wie es sich verhält: 🔁 endlose Wiederholung,
  ↓ macht die Musik leiser, ♫ Hintergrund, 🅂 stoppt die anderen Pads, dazu
  seine Lautstärke, wenn sie unter 100 % liegt.
- Mit **✏** wählt ein Klick ein Pad aus, statt es abzufeuern, und
  **Strg+Klick** oder **Umschalt+Klick** nimmt weitere dazu. Ein Rechtsklick
  auf ein ausgewähltes Pad wirkt dann auf alle: 🎨 Farbe, 🗑 Pad leeren oder
  **⚙ Einstellungen…**. Dort geht nur, was du änderst, auf die anderen Pads
  über, zum Beispiel 🔈 Musik leiser oder 🅂 für sechs Pads auf einmal.
  Beschriftung und Taste bleiben bei jedem Pad.
- Die Seitenpfeile, sichtbar ab einer zweiten Seite, schalten die Seiten um, **Strg + Alt + ← / →** ebenso. Ein Doppelklick auf den Seitennamen
  benennt die Seite um. Das Größenfeld legt das Raster fest, zum Beispiel
  2 × 7. Ein kleineres Raster verliert nie ein Pad.
- **🗂** exportiert oder importiert die Wand oder packt alle Pads auf eine
  Seite.
- Zieh die Wand links oder rechts ans Fenster, unter die Decks oder als
  eigenes Fenster hinaus. **📌** holt eine schwebende Wand zurück.

### ⌨ Die Tasten der Cartwall

Bei gesperrter Wand öffnet **Rechtsklick auf ein Pad ▸ ⌨ Tastenkürzel…** das Fenster
**⌨ Tasten** auf seinem Reiter **🎛 Cartwall**. Ist die Wand mit ✏
entsperrt, öffnet es auch der Knopf **⌨** neben ✏. Der Reiter listet jede
Taste, auf die die Wand hört:

- **Slot-Vorgaben** feuern das Pad, das auf der sichtbaren Seite in diesem
  Slot sitzt, so trifft derselbe Finger auf jeder Seite dieselbe Ecke. Slot 1
  bis 9 beginnen auf **Strg + 1 … 9**.
- **Pad-Tasten** wandern mit ihrem Pad, wohin es auch verschoben wird, und
  gehen von jeder Seite aus. Ein Pad ohne eigene Taste hört auf die Taste
  seines Slots.

![Die Tasten der Cartwall, eine Taste doppelt vergeben](../img/cartwall-keys.png)

Für eine Taste klickst du **Anlernen** und drückst sie. Jede Taste geht, auch
F13 bis F24 von einem Stream Deck oder einem Makro-Keypad. Solange es wartet,
heißt **Anlernen** **Abbrechen**: ein zweiter Klick behält die alte Taste.
**✕** nimmt die Taste weg.

Eine doppelt vergebene Taste wird in ihrer Zeile markiert.
**⚠ schon belegt von Anthem (p1)** nennt das Pad oder den Slot, der sie hat,
und **⚠ Die App nutzt diese Taste: …** nennt eine [Pult-Taste](#-pult-tasten)
oder ein Tastenkürzel der App. Eine Taste mit zwei Besitzern löst bei keinem
aus, darum zählt die Zeile unten, welche Tasten noch doppelt vergeben sind.
Eine Pad-Taste geht vor einer Slot-Taste. **Standardbelegung
wiederherstellen** legt die Slots wieder auf Strg + 1 … 9 und lässt die
Pad-Tasten, wie sie sind.

Der andere Reiter des Fensters enthält die [Pult-Tasten](#-pult-tasten), und
ein **OK** speichert beide Reiter. Eine Taste, die du auf einem Reiter
anlernst, wird auf dem anderen sofort markiert, noch bevor etwas gespeichert
ist.

## 📱 Die Handy-Fernbedienung

Die Handy-Fernbedienung steuert das Pult aus dem Browser eines Handys, im
selben Netz wie der PC. Eine App musst du nicht installieren. Vom Handy aus
kannst du:

- sehen, was läuft und was als Nächstes kommt;
- einen Titel unter *Weiter* antippen, um ihn sofort zu spielen. Das Handy
  fragt vorher nach. Bei Ja wird der laufende Titel ausgeblendet, während der
  angetippte kommt, über die Überblendlänge, oder über die Ausblendzeit, wenn
  das Überblenden aus ist. Läuft nichts, oder in einer Pause zwischen den
  Tänzen, startet er einfach;
- abspielen und pausieren, zum vorigen oder nächsten Titel gehen;
- ausblenden, oder ausblenden und halten;
- **🔈 Nächsten Tanz ansagen** ein- oder ausschalten. Es ist derselbe
  Schalter wie im Wiedergabe-Bereich, Stimme und Zeitpunkt folgen also;
- zwischen **⏭ Auto** und **✋ Manuell** wechseln und **🔀 Überblenden**
  ein- oder ausschalten. Es sind die Schalter des Wiedergabe-Bereichs. Unter
  ✋ Manuell oder mit einer Pause zwischen den Titeln zeigt das Handy keinen
  Überblenden-Knopf, so wie der Bereich dann keine Überblenden-Zeile zeigt;
- den Fortschrittsbalken ziehen, um zu spulen. Die Stelle unter deinem
  Finger ist die Stelle, die die Fläche hört;
- die Pads der sichtbaren Cartwall-Seite feuern oder alle stoppen.

![Die Handy-Fernbedienung im Browser eines Handys](../img/phone-remote.png)

**Zum Starten** klickst du **📱 Handy-Fernbedienung…** im Wiedergabe-Bereich
oder **📱 Server starten** unter ⚙ Einstellungen ▸ ⚙ Allgemein. Das Fenster
der Fernbedienung öffnet sich:

- **● Läuft / ○ Gestoppt** mit **▶ Starten / ■ Stoppen**;
- **Das Handy erreicht das Pult:** **Nur WLAN**, oder **WLAN und mobile Daten
  (Cloudflare-Tunnel)** für den Fall, dass das Handy Internet hat, aber nicht
  im Netz des PCs ist. Der Tunnel funktioniert wie der der Gästeseite (siehe
  unten): kein Konto, das kostenlose Programm `cloudflared`, das der erste
  Start zum Herunterladen anbietet, und bei jedem Start eine neue Adresse
  `https://….trycloudflare.com`, die das Fenster als erste nennt. Bis
  Cloudflare antwortet, zeigt das Fenster „warte auf Cloudflare…“ und keinen
  QR-Code. Durch den Tunnel wächst die PIN auf 8 Stellen, weil die Adresse
  dem ganzen Internet offensteht; der QR-Code tippt sie für dich. Eine andere
  Wahl startet einen laufenden Server neu;
- ein **QR-Code**: scann ihn mit der Kamera des Handys, und das Handy ist
  drin, ohne die PIN zu tippen;
- die Adresse, mit einer Auswahl, wenn der PC in mehr als einem Netz hängt,
  und ein Link, der die Fernbedienung zum schnellen Test im Browser dieses
  PCs öffnet;
- die **PIN** und **Neue PIN**, die ein laufender Server sofort übernimmt;
- ein **Protokoll** dessen, was beim Server ankam: Handys, die die Seite
  geöffnet haben, Anmeldungen, falsche PINs und jeder Befehl.

Solange der Server läuft, trägt die Statusleiste ein grünes Abzeichen
**📱 Fernbedienung**; ein Klick darauf holt das Fenster zurück. In ⚙ Einstellungen heißt
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

## 📨 Gästewünsche

Gäste wünschen sich Titel vom eigenen Handy aus. Sie durchsuchen die
Bibliothek und wünschen sich einen Titel, oder schreiben ein paar Worte, wenn
er nicht dabei ist. Nichts, was ein Gast schickt, läuft von selbst: es landet
in einem Posteingang, und du entscheidest.

**Zum Starten** klickst du **📨 Gästewünsche…** unter ⚙ Einstellungen ▸
⚙ Allgemein, neben der Handy-Fernbedienung. Das Fenster enthält:

- **▶ Starten / ■ Stoppen** und **Gäste erreichen die Seite:** mit drei Wegen
  (siehe unten);
- einen **QR-Code** für die Kameras der Gäste, die Adresse und den
  **Event-Code**. **Neuer Code** sperrt jeden älteren Link und jedes Foto des
  QR-Codes aus;
- **🖥 QR-Code auf dem Präsentationsbildschirm zeigen** (von Haus aus an):
  solange Gäste wünschen können, trägt der Präsentationsbildschirm denselben
  Code unten rechts, unter „Musikwunsch? Hier scannen“, und die Gäste scannen
  ihn von der Fläche aus;
- den **Posteingang**: eine Zeile je Titel oder Wunsch, mit der Zahl, wie oft
  er kam. **⭐ Auf die Wunschliste** (oder ein Doppelklick) setzt einen Titel
  auf die erste ⭐ Wunschliste; **✕ Verwerfen** nimmt eine Zeile heraus;
- ein **Protokoll** dessen, was beim Server ankam.

Solange Gäste wünschen können oder Wünsche warten, trägt die Statusleiste ein
blaues Abzeichen **📨** mit der Zahl der wartenden Wünsche. Ein Klick darauf
öffnet das Fenster. Kommt ein neuer Wunsch, während das Fenster zu ist, nennt
ihn eine kurze Meldung, und das Abzeichen blinkt orange, bis du das Fenster
öffnest.

**Wie Gäste die Seite erreichen:**

| Weg | Was er braucht | Die Adresse |
|---|---|---|
| **Nur WLAN** | Gäste im selben WLAN wie der PC oder in seinem Hotspot. | Die dieses PCs im lokalen Netz. |
| **WLAN und mobile Daten (Cloudflare-Tunnel)** | Das kostenlose Programm `cloudflared`. Ein schon installiertes (Installer, winget, Homebrew) wird von selbst gefunden. Sonst bietet der erste Start an, es herunterzuladen (etwa 55 MB), oder du legst es neben das Programm. Kein Konto. | Bei jedem Start eine neue `https://….trycloudflare.com`. |

- Jeder Gast darf in zehn Minuten zehn Wünsche schicken, alle Gäste zusammen
  120. Ein falscher oder alter Event-Code zählt dabei mit.
- Stoppen schließt die Seite für die Gäste. Wie die Handy-Fernbedienung
  laufen Gästewünsche nur so lange wie die App.
- Solange der Tunnel sich verbindet, auch nach einem Wechsel des
  Wegs bei offenen Wünschen, zeigt das Fenster *Verbinde…* statt eines
  QR-Codes. Der Code erscheint, sobald Gäste die Seite erreichen; so
  kopiert niemand eine Adresse, die (noch) nicht geht.

## ⌨ Pult-Tasten

Jede Aktion der Handy-Fernbedienung und des Controllers, außer den Fadern und
den Pads, hat auch eine Taste. Die Tasten gehen von überall im Fenster, so
kann alles, was tippt, das Pult steuern: ein Stream Deck im Hotkey-Modus oder
ein Makro-Keypad braucht dafür keinen Treiber.

| Aktion | Taste zu Beginn |
|---|---|
| ⏯ Abspielen / Pause | **Strg + Umschalt + P** |
| ⏭ Nächster Titel / ⏮ Vorheriger Titel | **Strg + Umschalt + → / ←** |
| 🔉↓ Jetzt ausblenden | **Strg + Umschalt + F** |
| 🛑 Ausblenden und halten | **Strg + Umschalt + H** |
| 🔉 Musik absenken an / aus | **Strg + Umschalt + D** |
| 🔈 Nächsten Tanz ansagen an / aus | **Strg + Umschalt + A** |
| 🔼 / 🔽 Musik lauter / leiser, 5 % pro Schritt | **Strg + Umschalt + ↑ / ↓** |
| 🔼 / 🔽 Cartwall lauter / leiser, 5 % pro Schritt | **Strg + Alt + ↑ / ↓** |
| ◀ / ▶ Vorherige / nächste Cartwall-Seite | **Strg + Alt + ← / →** |
| ⏫ / ⏬ Tempo schneller / langsamer, 0,1 % pro Schritt | **Strg + Umschalt + Bild ↑ / Bild ↓** |
| 🎯 Tempo zurück auf ±0 % | **Strg + Umschalt + Pos1** |
| ⏹ Alle Pads stoppen | **Strg + Umschalt + X** |
| 🎯 Playlist 1–8 fokussieren | **Alt + 1** … **Alt + 8** |
| 🎯 Wunschliste 1–4 fokussieren | **Alt + Q**, **W**, **E**, **R** |
| 📚 Bibliothek fokussieren | **Alt + L** |
| ⬆ / ⬇ Nach oben / unten blättern | **Alt + ↑ / ↓** |
| ▶ Gewählten Titel abspielen | **Alt + P** |
| ➕ Gewählten Titel in die Playlist | **Alt + A** |
| ⭐ Gewählten Titel in die Wunschliste | **Alt + D** |

Ändern kannst du sie über **⌨ Tasten…** in ⚙ Einstellungen ▸
⚙ Allgemein ▸ 🎛 DJ-Controller oder in der Übersicht unter **F1**, die die
Tasten so listet, wie sie belegt sind. Beide öffnen das Fenster **⌨ Tasten**
auf seinem Reiter **⌨ Pult-Tasten**. Sein Reiter **🎛 Cartwall** enthält die
[Tasten der Cartwall](#-die-tasten-der-cartwall), so stellst du alle Tasten an
einer Stelle ein.

![Die Pult-Tasten, eine davon auch auf einem Cartwall-Pad](../img/desk-keys.png)

- **Anlernen**, dann die Taste drücken. Noch einmal Anlernen bricht ab und
  behält die alte Taste. **✕** lässt die Aktion ohne Taste.
- **＋** neben der Taste einer Aktion fügt ein Feld für eine weitere Taste
  hinzu. Jede Taste der Aktion macht dasselbe, und der F1-Spickzettel listet
  sie in einer Zeile. **−** neben einem hinzugefügten Feld nimmt es samt
  seiner Taste wieder weg.
- Ein Stream Deck oder ein Makro-Keypad kann **F13 bis F24** senden. Keine
  Tastatur hat diese Tasten, also kommen sie nie mit etwas anderem ins Gehege.
- Eine Taste, die schon vergeben ist, sagt das in ihrer Zeile.
  **⚠ Die App nutzt diese Taste: …** nennt, was die App oder ein Cartwall-Pad
  damit macht. Änder eine der beiden: eine Taste mit zwei Besitzern löst bei
  keinem aus.
- **↺ Standard wiederherstellen** legt jede Taste zurück auf die Tabelle oben.

## 🎛 Ein DJ-Controller

Ein USB-MIDI- oder HID-Controller kann das Pult mit echten Tasten und einem
Fader steuern. Eingerichtet wird er unter ⚙ Einstellungen ▸ ⚙ Allgemein ▸
🎛 DJ-Controller ▸ **🎛 Einrichten…**.

Was er auslösen kann:

- ⏯ Abspielen / Pause, ⏭ Nächster Titel, ⏮ Vorheriger Titel;
- 🔉↓ Jetzt ausblenden, 🛑 Ausblenden und halten;
- 🔉 Musik absenken an / aus, 🔈 Nächsten Tanz ansagen an / aus;
- 🔊 Musiklautstärke, über einen Fader oder einen Regler, und 🔼 / 🔽 Musik
  lauter / leiser in 5-%-Schritten, für Tasten;
- 🎛 Cartwall-Lautstärke, über einen Fader oder einen Regler, und 🔼 / 🔽
  Cartwall lauter / leiser, dasselbe für die Pads; ◀ / ▶ Vorherige /
  nächste Cartwall-Seite;
- 🎚 Tempo / Pitch, über einen Fader oder einen Drehregler: seine Mitte ist
  ±0 %, seine Enden −16 % und +16 %. Für Tasten ⏫ / ⏬ Tempo schneller /
  langsamer in 0,1-%-Schritten und 🎯 Tempo zurück auf ±0 %. Das Tempo
  ändert sich, sobald der Regler stillsteht, nicht bei jedem Schritt: so
  stockt die Musik nicht, während du drehst;
- 🎯 Playlist 1–8 fokussieren und 🎯 Wunschliste 1–4 fokussieren: eine
  Taste pro Liste holt sie auf den Schirm und macht sie zur aktiven Liste.
  Die Ansicht wird breiter, wenn diese Playlist verborgen ist, und es gehen
  mehr Wunschlisten auf, wenn weniger zu sehen sind. Der Player-Build zeigt
  vier Playlists, dort tun 5–8 nichts. Sie haben auch
  [Pult-Tasten](#-pult-tasten);
- 📚 Bibliothek fokussieren holt den Bibliotheksbereich auf den Schirm und
  macht ihn zur aktiven Liste;
- 🔄 Durch die Liste blättern, über einen Endlosregler, und ⬆ / ⬇ Nach oben
  / unten blättern, für Tasten, bewegen die Auswahl in der Liste mit dem
  Fokus, wie die Pfeiltasten. Durch die Liste blättern nimmt einen
  MIDI-Regler, der Schritte sendet (1, 2, … in die eine Richtung und 127,
  126, … in die andere, oder 65, 66, … und 63, 62, …); ein Regler mit
  Anfang und Ende kann nicht blättern;
- ▶ Gewählten Titel abspielen spielt ihn ab, wie **Eingabe** in dieser
  Liste;
- ➕ Gewählten Titel in die Playlist und ⭐ Gewählten Titel in die
  Wunschliste hängen ihn ans Ende der aktiven Playlist oder der zuletzt
  fokussierten Wunschliste (Wunschliste 1, wenn noch keine fokussiert war),
  als wäre er dorthin gezogen. Die Liste, aus der er kommt, behält ihn. Eine
  geplante Auslosung nimmt einen Titel nur auf einen Platz, darum sagt ➕
  dort das und fügt nichts hinzu. Auch diese haben
  [Pult-Tasten](#-pult-tasten);
- ⏹ Alle Pads stoppen, und sechzehn Cartwall-Pads: Pad *n* ist das *n*-te
  Pad der sichtbaren Seite, wie bei **Strg + *n***.

Im Fenster:

![Das Controller-Fenster mit dem Profil für den nanoKONTROL2](../img/controller.png)

1. Wähl den Controller unter **Gerät**. **↻** sucht nach neuen. Hak **Alle
   HID-Geräte zeigen, nicht nur DJ-Controller** an, wenn deiner fehlt.
2. **Vorlagen ▾** hält ein fertiges Profil für den Korg nanoKONTROL2. Dort
   steuert die Transportreihe den Player, Fader 1 ist die Musiklautstärke,
   Fader 2 die Cartwall-Lautstärke, der Drehregler über Fader 1 das Tempo, und **S1** setzt das Tempo zurück auf
   ±0 % (die Drehregler lassen sich nicht drücken). **TRACK ▶** fokussiert
   die Bibliothek, **MARKER ◀ / ▶** blättern in der Liste mit dem Fokus
   nach oben und unten, und **S2**, **S3**, **S4** spielen den gewählten
   Titel ab oder schicken ihn in die Playlist oder die Wunschliste. Seine
   Drehregler haben Anschläge, darum blättert keiner davon. Die
   Cartwall-Pads liegen auf den Tasten S, M und R der Kanäle 5–8 und auf
   M1–M4.
3. Für jeden anderen Controller klickst du **Anlernen** neben einer Aktion
   und drückst die Taste oder bewegst den Fader, auf die sie hören soll.
   Solange es wartet, heißt der Knopf **Abbrechen**: noch ein Klick darauf,
   oder **✕**, beendet das Anlernen und behält die bisherige Zuordnung.
   **✕** in jeder anderen Zeile löst die Zuordnung dieser Aktion. Die Zeile
   unter der Tabelle zeigt das zuletzt berührte Bedienelement.
4. **💾 Profil speichern…** und **📂 Profil laden…** halten eine Belegung als
   Datei fest, zum Beispiel für den PC in der Halle.

- Ein Bedienelement macht nur eine Sache. Nimmt Anlernen ein Bedienelement,
  das eine andere Aktion hatte, steht in deren Zeile **⚠ verschoben auf …**
  mit der Aktion, die es jetzt hat. Lern diese Zeile neu an oder lass sie
  leer.
- Anlernen unterscheidet eine Taste von einem Drehregler oder Fader daran,
  wie sie sich bewegen. Eine Tasten-Aktion nimmt nur einen Druck an, ein
  Drehregler, der dabei gedreht wird, zählt nicht. Lautstärken und Tempo
  nehmen nur einen Drehregler oder Fader, nie eine Taste.
- 🔼 / 🔽 Musik lauter / leiser ohne eigene Taste zeigen in Grau
  **über den Fader — CC 0 · ch 1**: der 🔊 Fader stellt die Lautstärke schon.
  Die Vorlage für den nanoKONTROL2 lässt sie so, und ebenso 🔼 / 🔽 der
  Cartwall unter ihrem Fader.

Solange der Controller verbunden ist, trägt die Statusleiste ein grünes
Abzeichen mit seinem Namen, etwa **🎛 nanoKONTROL2**. Ein Klick darauf öffnet
das Controller-Fenster.

![Das Controller-Abzeichen in der Statusleiste](../img/controller-badge.png)

Der Controller wirkt, sobald du ihn einrichtest, und wird gemerkt. Wird er
abgezogen, verschwindet das Abzeichen nach wenigen Sekunden, und die App
sucht alle paar Sekunden wieder nach ihm; wieder eingesteckt, wird er von
selbst wieder benutzt. MIDI geht unter Windows, macOS und Linux.

## 📜 Gespielte Titel

Im Spielmodus schreibt die App jeden Titel auf, sobald er 10 Sekunden
gelaufen ist, also in dem Moment, in dem seine Zeile grau wird: mit
Startzeit, Interpret, Tanz und Liste. Vorhören beim Planen wird nie
protokolliert. **❔ ▸ 📜 Gespielte Titel…** listet die Abende, der neueste
oben; eine Pause von mehr als vier Stunden beginnt einen neuen, damit eine
Party über Mitternacht ein Abend bleibt.

- Klick auf einen Abend, um seine Titel zu sehen und wie lange jeder lief.
- **💾 Als CSV speichern…** speichert den Abend als Tabelle für Excel, zum
  Beispiel für eine GEMA-Meldung: Datum, Start, Interpret, Titel, Komponist, Tanz, Liste
  und Dauer.
- **🗑 Abend löschen** entfernt ihn nach einer Rückfrage aus dem Protokoll.

Weiter: [Tags](05-tags.md)
