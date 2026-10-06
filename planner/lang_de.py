"""German chrome, keyed by the English string as it stands in the code.

Rules this catalog follows, so that adding to it stays mechanical:

* **The key is copied from the source, character for character** — leading
  spaces, double spaces after an emoji, the `&&` that Qt renders as one
  ampersand, and the tab that separates a menu caption from its shortcut hint
  are all part of the key. `tests/gui/test_i18n.py` checks the ones that carry
  meaning.
* **The emoji stays put.** It is the icon, not the text; a German label with a
  different pictogram reads as a different button.
* **Only chrome.** Anything the app reads out of the user's files — track
  titles, artists, folder names, dance codes — never passes through here, and
  a string not listed simply stays English.

Dancesport vocabulary follows what a German tournament actually says:
Turnier, Runde, Gruppe, Startgruppe, Eintanzen. "Playlist", "Deck",
"Cartwall" and "Pad" are left as they are — they are the words used in German
practice too, and translating them would make the app harder to read, not
easier.
"""

CATALOG = {
    # ── Buttons and words that turn up everywhere ────────────────────────────
    "Cancel": "Abbrechen",
    "Nb.": "Nr.",
    "none": "keine",
    "e.g. 6-3-2-1": "z. B. 6-3-2-1",
    "Group A–D": "Gruppe A–D",
    "Group E–H": "Gruppe E–H",
    "Preview-player options": "Optionen des Vorschau-Players",
    "Fade every running pad out (Esc)": "Alle laufenden Pads ausblenden (Esc)",
    "Fade between music and timetable every":
        "Zwischen Musik und Zeitplan wechseln alle",
    "    Only tracks not already in my open playlists":
        "    Nur Titel, die noch in keiner offenen Playlist sind",
    "Close": "Schließen",
    "Replace": "Ersetzen",
    "Reset": "Zurücksetzen",
    "Generate": "Erzeugen",
    "Parse": "Einlesen",
    "Colour": "Farbe",
    "Label": "Beschriftung",
    "Heading": "Überschrift",
    "A new line at the end": "Eine neue Zeile am Ende",
    "Take the selected line out": "Die ausgewählte Zeile herausnehmen",
    "Move the selected line up": "Die ausgewählte Zeile nach oben schieben",
    "Move the selected line down": "Die ausgewählte Zeile nach unten schieben",
    "Shortcut": "Tastenkürzel",
    "Class": "Klasse",
    "Class:": "Klasse:",
    "Style:": "Sektion:",
    "Method:": "Verfahren:",
    "Model:": "Modell:",
    "Voice:": "Stimme:",
    "Count:": "Anzahl:",
    "Context:": "Kontext:",
    "Volume": "Lautstärke",
    "Master volume": "Gesamtlautstärke",
    "Fade out": "Ausblenden",
    "Fade-out:": "Ausblenden:",
    "Own fade-out": "Eigenes Ausblenden",
    "Wall fade-out": "Cartwall-Ausblendzeit",
    "Play length:": "Spieldauer:",
    "Start after:": "Start nach:",
    "Stop after highlight:": "Stopp nach Highlight:",
    "Max tracks:": "Maximale Titel:",
    "Proven": "Bewährt",
    "Top Proven": "Top bewährt",
    "Fresh": "Frisch",
    # Five of these combos stack in a panel laid out around the English
    # captions, so the German ones have to stay inside the widest of them.
    # What each strategy actually does is in its tooltip.
    "Mostly Proven": "Meist bewährt",
    "Even Mix": "Ausgewogen",
    "Songs you have played before (fresh as fallback).":
        "Titel, die du schon gespielt hast (frische als Ersatz).",
    "Only your most-played songs.": "Nur deine meistgespielten Titel.",
    "Unused songs first (proven as fallback).":
        "Ungespielte Titel zuerst (bewährte als Ersatz).",
    "Proven + fresh together, but favors songs you have played before.":
        "Bewährte und frische zusammen, bevorzugt aber Titel, die du schon gespielt hast.",
    "Proven + fresh with no preference — equal chance, maximum variety.":
        "Bewährte und frische ohne Vorzug — gleiche Chance, größte Abwechslung.",
    "🌐  Search mode: Global — whole repository":
        "🌐  Suchmodus: Global — gesamtes Repository",
    "🎯  Search mode: Favorites library only":
        "🎯  Suchmodus: nur Favoriten-Bibliothek",
    "Library: %d files": "Bibliothek: %d Dateien",
    "Favorites: %d": "Favoriten: %d",
    "Library loaded — %s MP3 files, %s favorites songs, %s audio cached.":
        "Bibliothek geladen — %s MP3-Dateien, %s Favoriten-Titel, "
        "%s im Audio-Cache.",
    "— Indexes (analyzed / total) —":
        "— Indizes (analysiert / gesamt) —",
    "🔗 Fingerprints: %s": "🔗 Fingerabdrücke: %s",
    "📊 Loudness: %s": "📊 Lautheit: %s",
    "🔇 Silences: %s": "🔇 Stillen: %s",
    "🐂 PD highlights: %s": "🐂 PD-Höhepunkte: %s",
    "🎙️ Demucs vocals: %s measured":
        "🎙️ Demucs-Gesang: %s gemessen",
    "🌐 Global index: %s files, %s analyzed":
        "🌐 Globaler Index: %s Dateien, %s analysiert",
    "🌐 Global index: %s files built "
    "(loads on first global search)":
        "🌐 Globaler Index: %s Dateien gebaut "
        "(lädt bei der ersten globalen Suche)",
    "🌐 Global index: not built (⚙ Settings to build)":
        "🌐 Globaler Index: nicht gebaut (⚙ Einstellungen zum Bauen)",
    "(OpenL3 not available)": "(OpenL3 nicht verfügbar)",
    "(chroma not available)": "(Chroma nicht verfügbar)",
    "no Paso Doble in the library": "kein Paso Doble in der Bibliothek",
    "%s file(s) in the favorites library have no\n"
    "analysis yet":
        "%s Datei(en) der Favoriten-Bibliothek sind noch nicht\n"
        "analysiert",
    "an index of the favorites library is not complete yet":
        "ein Index der Favoriten-Bibliothek ist noch nicht vollständig",
    "🧱 Build ALL caches — %s. Asks for the scope\n"
    "first; reuses everything already cached and can be cancelled.":
        "🧱 ALLE Caches aufbauen — %s. Fragt zuerst nach dem Umfang;\n"
        "nutzt alles bereits Zwischengespeicherte und kann abgebrochen werden.",
    "audio fingerprints": "Audio-Fingerabdrücke",
    "loudness": "Lautheit",
    "silences": "Stillen",
    "PD highlights": "PD-Höhepunkte",
    "librosa audio analysis (no working audio decoder)":
        "librosa-Audioanalyse (kein funktionierender Decoder)",
    "loudness + silences (no ffmpeg)": "Lautheit + Stillen (kein ffmpeg)",
    "%s (not installed)": "%s (nicht installiert)",
    "\n\nSkipped: %s": "\n\nÜbersprungen: %s",
    "Nothing can be built on this machine right now.":
        "Auf diesem Rechner kann gerade nichts gebaut werden.",
    "Build every index over %s tracks from %s?":
        "Jeden Index über %s Titel aufbauen?\nUmfang: %s",
    "Runs %s back-to-back. Each is slow the first time, then "
    "cached; reuses anything already built. You can cancel "
    "between or within steps.":
        "Läuft: %s nacheinander. Jeder ist beim ersten Mal langsam, "
        "danach zwischengespeichert; nutzt alles bereits Gebaute. Du "
        "kannst zwischen den Schritten oder mitten darin abbrechen.",
    "Read-only — your audio files are never modified.":
        "Nur lesend — deine Audiodateien werden nie verändert.",
    "the favorites library": "die Favoriten-Bibliothek",
    "the whole repository": "das gesamte Repository",
    "the whole repository + favorites library":
        "das gesamte Repository + die Favoriten-Bibliothek",
    # The librosa index build, end to end: the two questions before it, the
    # progress line, and the three ways it can finish. The scope label above
    # is what fills the "%s in" slot in several of them.
    "All %s files in %s are already analyzed.":
        "Alle %s Dateien in %s sind bereits analysiert.",
    "%s of %s files in %s need analysis (~%s min).\n\n"
    "Analysis only reads your files — never modifies them. "
    "Results are cached.\n\nRun now?":
        "%s von %s Dateien in %s brauchen eine Analyse (~%s Min.).\n\n"
        "Die Analyse liest deine Dateien nur — sie verändert sie nie. "
        "Ergebnisse werden zwischengespeichert.\n\nJetzt starten?",
    "Audio index: analyzing %s files…":
        "Audio-Index: %s Dateien werden analysiert…",
    "Building audio index (%s)…": "Audio-Index wird gebaut (%s)…",
    "Global index: %s/%s%s": "Globaler Index: %s/%s%s",
    "  (%s errors)": "  (%s Fehler)",
    " (%s errors)": " (%s Fehler)",
    "Audio index built — %s files analyzed":
        "Audio-Index gebaut — %s Dateien analysiert",
    "Analyzed %s files in %s": "%s Dateien in %s analysiert",
    ".\nSimilarity search will now match across them.":
        ".\nDie Ähnlichkeitssuche findet jetzt über sie hinweg.",
    "Audio index cancelled — %s files analyzed so far "
    "(progress is cached).":
        "Audio-Index abgebrochen — bisher %s Dateien analysiert "
        "(der Fortschritt bleibt gespeichert).",
    "🧹  Checking which files are still on disk…":
        "🧹  Prüfen, welche Dateien noch auf der Platte sind…",
    "🧱  Looking for ffmpeg and the AI backends…":
        "🧱  Suche nach ffmpeg und den KI-Backends…",
    "🧱  Checking what this machine can build…":
        "🧱  Prüfen, was dieser Rechner bauen kann…",
    "librosa is not installed, so tempo and timbre cannot be "
    "measured and similar-track search stays unavailable.\n\n"
    "Install it, then restart the app:\n"
    "    pip install librosa":
        "librosa ist nicht installiert, daher können Tempo und Timbre "
        "nicht gemessen werden und die Suche nach ähnlichen Titeln "
        "bleibt nicht verfügbar.\n\n"
        "Installiere es und starte die App neu:\n"
        "    pip install librosa",
    "Nothing on this computer can decode an MP3, so tempo and "
    "timbre cannot be measured and similar-track search stays "
    "unavailable.\n\nInstall ffmpeg and make sure it is on PATH "
    "(not just next to the app), then restart.":
        "Nichts auf diesem Rechner kann eine MP3 dekodieren, daher "
        "können Tempo und Timbre nicht gemessen werden und die Suche "
        "nach ähnlichen Titeln bleibt nicht verfügbar.\n\n"
        "Installiere ffmpeg und sorge dafür, dass es im PATH steht "
        "(nicht nur neben der App), dann neu starten.",
    "The audio decoder could not read %s, so the analysis "
    "would fail for every file. See the log for the error.":
        "Der Audio-Decoder konnte %s nicht lesen, die Analyse würde "
        "also bei jeder Datei fehlschlagen. Der Fehler steht im Log.",
    "Nothing could be built for these, and nothing will be:":
        "Dafür konnte nichts gebaut werden, und daran ändert sich nichts:",
    "Caches built for %s — with problems, see the log.":
        "Caches gebaut für %s — mit Problemen, siehe Log.",
    "Finished for %s, but not everything worked:":
        "Fertig für %s, aber nicht alles hat geklappt:",
    "Ran: %s.": "Gelaufen: %s.",
    "All caches built for %s.": "Alle Caches gebaut für %s.",
    "All caches are built for %s.": "Alle Caches sind gebaut für %s.",
    "Build all caches — librosa: analyzing %s files…":
        "Alle Caches aufbauen — librosa: %s Dateien werden analysiert…",
    "Build all caches — %s…": "Alle Caches aufbauen — %s…",
    "Build all caches — %s embeddings…":
        "Alle Caches aufbauen — %s-Embeddings…",
    "mostly: %s": "meist: %s",
    "%s: %s file(s) failed": "%s: %s Datei(en) fehlgeschlagen",
    ", %s cached": ", %s zwischengespeichert",
    "%s: %s file(s) skipped — not on disk any more":
        "%s: %s Datei(en) übersprungen — nicht mehr auf der Platte",
    "Build all caches cancelled during %s — %s done so far "
    "(cached).":
        "Alle Caches aufbauen — abgebrochen bei %s, %s bisher fertig "
        "(zwischengespeichert).",
    "🎛  Both — plan and play":
        "🎛  Beides — planen und abspielen",
    "The full app: build playlists at home, run them at the tournament.":
        "Die volle App: Playlists zu Hause bauen, sie auf dem Turnier "
        "abspielen.",
    "📝  Planner only": "📝  Nur Planer",
    "Build and curate playlists. The tournament floor's playing panel, "
    "its timed play / announcements and the 🎛 cartwall stay hidden.":
        "Playlists bauen und pflegen. Der Abspielbereich für die "
        "Turnierfläche, sein zeitgesteuertes Abspielen / die Ansagen "
        "und die 🎛 Cartwall bleiben ausgeblendet.",
    "▶  Player only": "▶  Nur Player",
    "Run prepared playlists at the venue. Everything that generates or "
    "checks a playlist stays hidden.":
        "Vorbereitete Playlists in der Halle abspielen. Alles, was eine "
        "Playlist erzeugt oder prüft, bleibt ausgeblendet.",
    "◧  Beside the playlists — at the head of the ▶ Playing panel":
        "◧  Neben den Playlists — am Kopf des Bereichs ▶ "
        "Abspielen",
    "The player card stands in the left panel, above the timed-play "
    "controls.":
        "Die Player-Karte steht im linken Bereich, über den "
        "Bedienelementen für zeitgesteuertes Abspielen.",
    "▤  Above the playlists — one wide strip over the decks":
        "▤  Über den Playlists — ein breiter Streifen über den Decks",
    "The same player, laid out along the width above the decks — the "
    "shape a DJ desk uses. It shows in ▶ Playing mode.":
        "Derselbe Player, über die ganze Breite über den Decks "
        "ausgelegt — die Form, die ein DJ-Pult benutzt. Er zeigt sich "
        "im Modus ▶ Abspielen.",
    "🎬  FFmpeg — Qt's own engine (default)":
        "🎬  FFmpeg — Qts eigene Maschine (Standard)",
    "🎬  FFmpeg — Qt's own engine":
        "🎬  FFmpeg — Qts eigene Maschine",
    "🪟  Windows Media Foundation — the OS's own":
        "🪟  Windows Media Foundation — die des Betriebssystems",
    "🔊  Automatic — whatever this system uses (default)":
        "🔊  Automatisch — was dieses System benutzt (Standard)",
    "☀  Light (default)": "☀  Hell (Standard)",
    "White decks, dark text: the look every colour in the app was picked "
    "for.":
        "Weiße Decks, dunkler Text: das Aussehen, für das jede "
        "Farbe der App ausgesucht wurde.",
    "🌙  Dark": "🌙  Dunkel",
    # ── 🎨 The looks (shared/looks.py): sections, captions, blurbs ──
    "Platform looks": "Plattform-Looks",
    "Desk looks": "Pult-Looks",
    "Modern looks": "Modern Looks",
    "No preview picture for this theme.":
        "Kein Vorschaubild für dieses Erscheinungsbild.",
    "A look brings its own accent colour — this one is for Light and Dark.":
        "Ein Look bringt seine eigene Akzentfarbe mit — diese hier gilt für "
        "Hell und Dunkel.",
    "Windows 11 · Light": "Windows 11 · Hell",
    "Fluent: 4 px corners, Segoe UI Variable, the Windows blue and an "
    "accent line under the active field.":
        "Fluent: 4-px-Ecken, Segoe UI Variable, das Windows-Blau und eine "
        "Akzentlinie unter dem aktiven Feld.",
    "Windows 11 · Dark": "Windows 11 · Dunkel",
    "Fluent in dark: the Windows 11 dark greys with the light blue accent.":
        "Fluent in dunkel: die dunklen Grautöne von Windows 11 mit dem "
        "hellblauen Akzent.",
    "macOS · Light": "macOS · Hell",
    "Aqua as of Sonoma: 6 px corners, a solid blue selection with white "
    "text and an accent ring around the active field.":
        "Aqua wie in Sonoma: 6-px-Ecken, eine kräftig blaue Auswahl mit weißer "
        "Schrift und ein Akzentring um das aktive Feld.",
    "macOS · Dark": "macOS · Dunkel",
    "Aqua in dark mode: charcoal panes, grey keys, the bright system blue.":
        "Aqua im Dunkelmodus: anthrazitfarbene Flächen, graue Tasten, das "
        "helle Systemblau.",
    "Linux GNOME · Light": "Linux GNOME · Hell",
    "Adwaita: 6 px corners, flat grey buttons without a frame, the GNOME blue.":
        "Adwaita: 6-px-Ecken, flache graue Knöpfe ohne Rahmen, das GNOME-Blau.",
    "Linux GNOME · Dark": "Linux GNOME · Dunkel",
    "Adwaita dark: soft charcoal, flat buttons, the GNOME blue.":
        "Adwaita dunkel: weiches Anthrazit, flache Knöpfe, das GNOME-Blau.",
    "Console": "Konsole",
    "Graphite, keys lit from above like a mixing desk, a pressed key "
    "glows blue. Lettering in Bahnschrift.":
        "Graphit, Tasten mit Licht von oben wie am Mischpult, eine gedrückte "
        "Taste leuchtet blau. Schrift Bahnschrift.",
    "Jet black with metal gradients and orange as the light: harder and "
    "higher in contrast, like a hardware controller in a dark hall.":
        "Tiefschwarz mit Metall-Verläufen und Orange als Leuchtfarbe: härter "
        "und kontrastreicher, wie ein Hardware-Controller im dunklen Saal.",
    "Flat night blue with cyan as the light: whatever is on gets a "
    "glowing rim instead of a fill. Rounder corners.":
        "Flaches Nachtblau mit Cyan als Leuchtfarbe: Was eingeschaltet ist, "
        "bekommt einen leuchtenden Rand statt einer Füllung. Rundere Ecken.",
    "The bright desk: brushed aluminium, keys lit from above, orange as "
    "the accent. For daylight and bright halls.":
        "Das helle Pult: gebürstetes Aluminium, Tasten mit Licht von oben, "
        "Orange als Akzent. Für Tageslicht und helle Hallen.",
    "Graphite": "Graphit",
    "Calm neutral dark: near-white text on graphite, soft filled buttons "
    "with round corners, a clear blue. Easy on the eyes for a long evening.":
        "Ruhiges, neutrales Dunkel: fast weiße Schrift auf Graphit, weich "
        "gefüllte Knöpfe mit runden Ecken, ein klares Blau. Schont die Augen "
        "an einem langen Abend.",
    "Midnight": "Mitternacht",
    "Deep navy with a teal accent and pill-shaped buttons: modern and "
    "quiet, the text stays crisp against the dark blue.":
        "Tiefes Marineblau mit Petrol als Akzent und pillenförmigen Knöpfen: "
        "modern und ruhig, die Schrift bleibt scharf vor dem dunklen Blau.",
    "Dark with a violet accent: soft filled buttons, warm dark greys, "
    "light lavender for links and focus.":
        "Dunkel mit violettem Akzent: weich gefüllte Knöpfe, warme dunkle "
        "Grautöne, helles Lavendel für Links und Fokus.",
    "Paper": "Papier",
    "Clean and bright: white panes, nearly black text, soft grey buttons "
    "with round corners and a strong blue. Crisp in daylight.":
        "Klar und hell: weiße Flächen, fast schwarze Schrift, weiche graue "
        "Knöpfe mit runden Ecken und ein kräftiges Blau. Scharf bei Tageslicht.",
    "High contrast · Dark": "Hoher Kontrast · Dunkel",
    "Black and white with a yellow accent, 2 px frames and a yellow "
    "selection: readable from across the hall and in bright stage light.":
        "Schwarz und Weiß mit gelbem Akzent, 2-px-Rahmen und gelber Auswahl: "
        "lesbar quer durch die Halle und im hellen Bühnenlicht.",
    "High contrast · Light": "Hoher Kontrast · Hell",
    "Black on white with a deep blue accent and 2 px frames: the most "
    "readable light look, also on a weak projector or laptop screen.":
        "Schwarz auf Weiß mit tiefblauem Akzent und 2-px-Rahmen: der am "
        "besten lesbare helle Look, auch auf einem schwachen Beamer oder "
        "Laptop-Bildschirm.",
    "The same colours put through a lightness flip, so a warning stays "
    "red and the ▶ player panel — dark already — is left as it is.":
        "Dieselben Farben durch eine Helligkeitsumkehr geschickt, damit "
        "eine Warnung rot bleibt und der ▶ Player-Bereich — "
        "ohnehin dunkel — so bleibt, wie er ist.",
    "  %s  —  pick a colour…": "  %s  —  Farbe wählen…",
    "Accent colour": "Akzentfarbe",
    "  ~%s left": "  ~%s übrig",
    "(%s errors)": "(%s Fehler)",
    ", %s errors": ", %s Fehler",
    "%s done — %s %s": "%s fertig — %s %s",
    " (all were already cached)":
        " (alles war schon zwischengespeichert)",
    "%s cancelled — %s %s so far.":
        "%s abgebrochen — %s %s bisher.",
    "%s failed:\n%s": "%s fehlgeschlagen:\n%s",
    "files cached": "Dateien zwischengespeichert",
    "tracks measured": "Titel gemessen",
    "tracks probed": "Titel geprüft",
    "tracks analyzed": "Titel analysiert",
    "All %s files are already cached.\n\n"
    "Re-analyze the whole library anyway to refresh the measured tempo "
    "with the current method?":
        "Alle %s Dateien sind bereits zwischengespeichert.\n\n"
        "Die ganze Bibliothek trotzdem neu analysieren, um das gemessene "
        "Tempo mit der aktuellen Methode aufzufrischen?",
    "%s files will be re-analyzed (~%s min, cached afterwards).\n\n"
    "Run now?":
        "%s Dateien werden neu analysiert (~%s Min., danach "
        "zwischengespeichert).\n\nJetzt starten?",
    "%s files need librosa analysis (~%s min, cached afterwards).\n\n"
    "Run now?":
        "%s Dateien brauchen eine librosa-Analyse (~%s Min., danach "
        "zwischengespeichert).\n\nJetzt starten?",
    "Audio analysis started — %s files…":
        "Audio-Analyse gestartet — %s Dateien…",
    "Analyze Audio (Timbre)": "Audio analysieren (Timbre)",
    "Re-analyze All Audio": "Alles Audio neu analysieren",
    "Measure the loudness of the whole library (%s tracks)?\n\n"
    "Already-measured tracks are skipped — only new ones are\n"
    "decoded (≈1 s each). You can cancel anytime; results so far\n"
    "are kept.":
        "Die Lautheit der ganzen Bibliothek über %s Titel messen?\n\n"
        "Bereits gemessene Titel werden übersprungen — nur neue\n"
        "werden dekodiert (≈1 s je Titel). Du kannst jederzeit\n"
        "abbrechen; bisherige Ergebnisse bleiben erhalten.",
    "Probe the silent stretches of the whole library (%s tracks, %s not "
    "probed yet)?\n\n"
    "Already-probed tracks are skipped — only new ones are\n"
    "decoded (≈0.3 s each). You can cancel anytime; results so far\n"
    "are kept.":
        "Die stillen Stellen der ganzen Bibliothek prüfen (%s Titel, "
        "%s noch nicht geprüft)?\n\n"
        "Bereits geprüfte Titel werden übersprungen — nur neue\n"
        "werden dekodiert (≈0,3 s je Titel). Du kannst jederzeit\n"
        "abbrechen; bisherige Ergebnisse bleiben erhalten.",
    "All %s tracks already have a measured vocal share.":
        "Alle %s Titel haben bereits einen gemessenen Gesangsanteil.",
    "Separate the vocals of %s not-yet-measured tracks (~%s min)?\n\n"
    "Demucs actually extracts the singing from each track — slow\n"
    "(~7 s per track) but far more reliable than the heuristics.\n"
    "You can cancel anytime; results so far are kept.":
        "Den Gesang von %s noch nicht gemessenen Titeln trennen (~%s Min.)?\n\n"
        "Demucs holt den Gesang wirklich aus jedem Titel heraus —\n"
        "langsam (~7 s je Titel), aber weit verlässlicher als die\n"
        "Heuristiken. Du kannst jederzeit abbrechen; bisherige\n"
        "Ergebnisse bleiben erhalten.",
    "Detect the highlights of every Paso Doble in the library (%s tracks)?\n\n"
    "Already-analyzed tracks are skipped — only new ones are\n"
    "decoded (a few seconds each). You can cancel anytime;\n"
    "results so far are kept.":
        "Die Höhepunkte jedes Paso Doble der Bibliothek erkennen (%s Titel)?\n\n"
        "Bereits analysierte Titel werden übersprungen — nur neue\n"
        "werden dekodiert (ein paar Sekunden je Titel). Du kannst\n"
        "jederzeit abbrechen; bisherige Ergebnisse bleiben erhalten.",
    "Fresh mix:": "Frische-Mischung:",
    "Pause music:": "Pausenmusik:",
    "Pause music volume:": "Lautstärke Pausenmusik:",
    "No pause music": "Keine Pausenmusik",
    "Set clock to": "Uhr stellen auf",
    "Draw tracks from": "Titel auswählen aus",
    "Songs needed for:": "Titel benötigt für:",
    "What to build": "Was erzeugt werden soll",
    "Round Strategy": "Rundenstrategie",
    "Middle of the round": "Mittelwert der Runde",
    "Lower — T%s": "Unten — T%s",
    "Middle — T%s": "Mitte — T%s",
    "Upper — T%s": "Oben — T%s",
    "Please wait": "Bitte warten",
    "Failed.": "Fehlgeschlagen.",
    "Add a page": "Seite hinzufügen",
    "Next page": "Nächste Seite",
    "Previous page": "Vorherige Seite",
    "Keep all": "Alle behalten",
    "Keep both": "Beide behalten",
    "Keep existing": "Vorhandenen behalten",
    "No key": "Keine Taste",
    "Print / Export": "Drucken / Exportieren",
    "USB export": "USB-Export",
    "Duplicate titles": "Doppelte Titel",
    "Possible duplicate": "Möglicherweise doppelt",
    "Check duplicates": "Auf Doppelte prüfen",
    "Cartwall shortcuts": "Cartwall-Tastenkürzel",
    "Pad settings": "Pad-Einstellungen",
    "Clear this pad": "Dieses Pad leeren",
    "Columns in the library": "Spalten der Bibliothek",
    "Open wishlists": "Offene Wunschlisten",
    "Analyze PD highlights": "PD-Highlights analysieren",
    "Vocal + instr.": "Gesang + Instr.",
    "Use Timbre Similarity": "Timbre-Ähnlichkeit nutzen",
    "Load models": "Modelle laden",
    "Copy to clipboard": "In die Zwischenablage",
    "Press the keys you want": "Gewünschte Tasten drücken",
    "Restore slot defaults": "Standardbelegung wiederherstellen",
    # Its tooltip. The two %s are the first and last slot key, which are keys
    # on the keyboard and are shown as they are pressed.
    "Back to %s…%s, leaving the pad keys alone":
        "Zurück auf %s…%s, die Pad-Tasten bleiben unberührt",
    # A pad's own tooltip is built up in pieces: the title and the path lead,
    # and these two are glued on behind them. The %s is the slot key, which is
    # a key on the keyboard and is shown as it is pressed.
    "\nKey: %s": "\nTaste: %s",
    "\n⚠️ File not found": "\n⚠️ Datei nicht gefunden",
    "Remove this page": "Diese Seite entfernen",
    "Remove this competition": "Dieses Turnier entfernen",
    "Save all playlists": "Alle Playlists speichern",
    "Save tournament day": "Turniertag speichern",
    "Clear all tournament-day playlists": "Alle Turniertag-Playlists leeren",
    "All dances": "Alle Tänze",
    "All classes": "Alle Klassen",
    "All categories": "Alle Kategorien",
    "Added: all": "Hinzugefügt: alle",
    "Plays: all": "Gespielt: alle",
    "Parse schedule": "Zeitplan einlesen",
    "Filter by the instrumental tag": "Nach Instrumental-Kennzeichen filtern",
    "Short dance names  (LW, SB)": "Kurze Tanznamen  (LW, SB)",
    "Auto re-roll round on strategy change":
        "Runde bei Strategiewechsel neu würfeln",
    "Re-analyze tracks that already have highlights":
        "Titel mit vorhandenen Highlights neu analysieren",
    "An .m3u playlist file": "Eine .m3u-Playlist-Datei",
    "Focused playlist (current deck)": "Aktive Playlist (aktuelles Deck)",
    "Number of titles in this wishlist": "Anzahl Titel in dieser Wunschliste",

    # ── 🎨 Looks of your own: ⚙ Settings › Look and the editor (gui/look_editor.py) ──
    "Own looks": "Eigene Looks",
    "none yet — ＋ New look…": "noch keine — ＋ Neuer Look…",
    "＋  New look…": "＋  Neuer Look…",
    "A look of your own, starting as a copy of the selected one.":
        "Ein eigener Look, zunächst eine Kopie des ausgewählten.",
    "✎  Edit…": "✎  Bearbeiten…",
    "🗑  Delete": "🗑  Löschen",
    "Import…": "Importieren…",
    "Add a look someone exported.":
        "Einen Look hinzufügen, den jemand exportiert hat.",
    "Export…": "Exportieren…",
    "Save the selected look of your own as a file, to pass it on.":
        "Den ausgewählten eigenen Look als Datei speichern, um ihn "
        "weiterzugeben.",
    "A look of your own, kept on this computer. ✎ Edit changes it, Export "
    "passes it on.":
        "Ein eigener Look, auf diesem Computer gespeichert. ✎ Bearbeiten "
        "ändert ihn, Exportieren gibt ihn weiter.",
    "%s (own)": "%s (eigen)",
    "Look not saved": "Look nicht gespeichert",
    "The looks file could not be written. The log names the reason.":
        "Die Look-Datei ließ sich nicht schreiben. Das Protokoll nennt den "
        "Grund.",
    "Delete look": "Look löschen",
    "Delete the look “%s”? This cannot be undone; an exported file "
    "of it stays.":
        "Den Look „%s“ löschen? Das lässt sich nicht rückgängig "
        "machen; eine exportierte Datei davon bleibt erhalten.",
    "Import a look": "Einen Look importieren",
    "Look not imported": "Look nicht importiert",
    "This file holds no look the app can use:\n%s":
        "Diese Datei enthält keinen Look, den die App verwenden kann:\n%s",
    "Export the look": "Den Look exportieren",
    "Look not exported": "Look nicht exportiert",
    "The file could not be written:\n%s":
        "Die Datei ließ sich nicht schreiben:\n%s",
    "🎨  Edit look": "🎨  Look bearbeiten",
    "Family: %s. The details it shares with the built-in looks of that "
    "group stay: faders, checkboxes, headers.":
        "Familie: %s. Was er mit den eingebauten Looks dieser Gruppe teilt, "
        "bleibt: Fader, Kontrollkästchen, Kopfzeilen.",
    "Grounds": "Flächen",
    "Window": "Fenster",
    "The ground of the main window and the dialogs.":
        "Der Grund des Hauptfensters und der Dialoge.",
    "Lists and fields": "Listen und Felder",
    "Tables, lists and text fields.": "Tabellen, Listen und Textfelder.",
    "Every other row": "Jede zweite Zeile",
    "The second row colour of a table.": "Die zweite Zeilenfarbe einer Tabelle.",
    "Headers": "Kopfzeilen",
    "Table headers and the menu bar.": "Tabellenköpfe und die Menüleiste.",
    "The ground of a tooltip.": "Der Grund eines Tooltips.",
    "Buttons": "Schaltflächen",
    "Button face": "Schaltfläche",
    "A button at rest.": "Eine Schaltfläche in Ruhe.",
    "Under the mouse": "Unter der Maus",
    "A button the mouse is over.": "Eine Schaltfläche unter dem Mauszeiger.",
    "Pressed": "Gedrückt",
    "A button held down.": "Eine gedrückt gehaltene Schaltfläche.",
    "Light from above": "Licht von oben",
    "Set, a button fades from this colour down to its face, like a key on a "
    "mixing desk. Off, the face is flat.":
        "Gesetzt, verläuft eine Schaltfläche von dieser Farbe nach unten in "
        "ihre Fläche, wie eine Taste an einem Mischpult. Aus, ist die Fläche "
        "eben.",
    "Header light from above": "Kopfzeilen-Licht von oben",
    "The same fade for the table headers and the deck title strips.":
        "Derselbe Verlauf für die Tabellenköpfe und die Titelleisten der Decks.",
    "Lines": "Linien",
    "Hairlines": "Haarlinien",
    "Frames, the table grid and separators.":
        "Rahmen, das Tabellengitter und Trennlinien.",
    "Outlines": "Umrisse",
    "A control's frame and the scrollbar handle.":
        "Der Rahmen eines Bedienelements und der Griff der Bildlaufleiste.",
    "All ordinary text.": "Aller gewöhnliche Text.",
    "Dim text": "Blasser Text",
    "Disabled text, placeholders and side notes.":
        "Deaktivierter Text, Platzhalter und Randnotizen.",
    "Accent": "Akzent",
    "The default button and a switched-on toggle.":
        "Die Standardschaltfläche und ein eingeschalteter Schalter.",
    "Text on the accent": "Text auf dem Akzent",
    "The caption on an accent fill.": "Die Beschriftung auf einer Akzentfläche.",
    "Accent as text": "Akzent als Text",
    "Links, focus rings and the round bands' lettering.":
        "Links, Fokusringe und die Schrift der Rundenbänder.",
    "Selection": "Auswahl",
    "Selected row": "Ausgewählte Zeile",
    "The band of the selected row.": "Das Band der ausgewählten Zeile.",
    "Text on the selection": "Text auf der Auswahl",
    "The text in that band.": "Der Text in diesem Band.",
    "Fade": "Verlauf",
    "off": "aus",
    "Shape and lettering": "Form und Schrift",
    "Corners:": "Ecken:",
    "Buttons:": "Schaltflächen:",
    "Tabs:": "Reiter:",
    "Focus:": "Fokus:",
    "Font:": "Schrift:",
    "Outlined": "Umrandet",
    "Flat, no frame": "Flach, ohne Rahmen",
    "Desk key, lit from above": "Pult-Taste, von oben beleuchtet",
    "Dark, glowing rim when on": "Dunkel, leuchtender Rand wenn an",
    "Soft filled": "Sanft gefüllt",
    "Pill, fully rounded": "Pille, ganz gerundet",
    "2 px frame, high contrast": "2-px-Rahmen, hoher Kontrast",
    "Underlined": "Unterstrichen",
    "Segmented": "Segmentiert",
    "Desk keys": "Pult-Tasten",
    "Pills": "Pillen",
    "Ring around the field": "Ring um das Feld",
    "Line under the field": "Linie unter dem Feld",
    "Saved looks are kept on this computer. The app takes a changed look on "
    "its next start.":
        "Gespeicherte Looks bleiben auf diesem Computer. Die App übernimmt "
        "einen geänderten Look beim nächsten Start.",
    "⚠ Hard to read:": "⚠ Schwer lesbar:",
    "✓ Every text reads clearly against its ground.":
        "✓ Jeder Text hebt sich deutlich von seinem Grund ab.",
    "%s: %.1f : 1, should be at least %.1f":
        "%s: %.1f : 1, sollte mindestens %.1f sein",
    "Text on lists": "Text auf Listen",
    "Text on every other row": "Text auf jeder zweiten Zeile",
    "Text on the window": "Text auf dem Fenster",
    "Text on buttons": "Text auf Schaltflächen",
    "Dim text on lists": "Blasser Text auf Listen",
    "Planning": "Planung",
    "Playing": "Wiedergabe",
    "Group": "Gruppe",
    "Heat %d": "Gruppe %d",
    "▼  PRELIMINARY ROUND  (2 heats)": "▼  VORRUNDE  (2 Gruppen)",
    "▼  Slow Waltz": "▼  Langsamer Walzer",
    "Button": "Schaltfläche",
    "Switched on": "Eingeschaltet",
    "Disabled": "Deaktiviert",
    "Search…": "Suchen…",
    "Ticked": "Angehakt",
    "Dim text: a hint, a placeholder.": "Blasser Text: ein Hinweis, ein Platzhalter.",

    # ── Window and dialog titles ─────────────────────────────────────────────
    "Welcome to DanceSport Planner & Player": "Willkommen bei DanceSport Planner & Player",
    "AI Song Suggestions (OpenRouter)": "KI-Titelvorschläge (OpenRouter)",
    "Previous session crashed": "Letzte Sitzung ist abgestürzt",
    "Settings — app mode, library paths & analysis":
        "Einstellungen — Modus, Bibliothekspfade & Analyse",
    "Settings — library paths, global search & analysis":
        "Einstellungen — Bibliothekspfade, globale Suche & Analyse",
    "⌨  Keyboard shortcuts  (F1)": "⌨  Tastenkürzel  (F1)",
    "Shortcuts (F1) and about this app": "Tastenkürzel (F1) und Über diese App",
    "ℹ  About…": "ℹ  Über…",
    "About": "Über",
    "Project": "Projekt",
    "Author": "Autor",
    "License": "Lizenz",
    "Which library should this index cover?":
        "Welche Bibliothek soll dieser Index abdecken?",
    "What should go into the venue bundle?":
        "Was soll in das Hallen-Paket?",

    # ── Status messages ──────────────────────────────────────────────────────
    "Settings saved.": "Einstellungen gespeichert.",
    "Database cleanup done.": "Datenbank-Aufräumen abgeschlossen.",
    "Loading library…": "Bibliothek wird geladen…",
    "Loading music library…": "Musikbibliothek wird geladen…",
    "Library: loading…": "Bibliothek: wird geladen…",
    "Generating playlist…": "Playlist wird erzeugt…",
    "Asking the model…": "Modell wird gefragt…",
    "Asking the model for a playlist…": "Modell wird nach einer Playlist gefragt…",
    "Fetching the model list…": "Modellliste wird geholt…",
    "Cancelling…": "Wird abgebrochen…",
    "Analysis failed.": "Analyse fehlgeschlagen.",
    "AI playlist failed.": "KI-Playlist fehlgeschlagen.",
    "AI playlist: nothing usable.": "KI-Playlist: nichts Verwertbares.",
    "Eintanzen failed.": "Eintanzen fehlgeschlagen.",
    "Eintanzen: no matching tracks.": "Eintanzen: keine passenden Titel.",
    "Global index failed.": "Globaler Index fehlgeschlagen.",
    "Similar-track analysis failed.": "Ähnlichkeitsanalyse fehlgeschlagen.",
    "Repository scan cancelled.": "Durchsuchen des Repositorys abgebrochen.",
    "Import: no tracks detected": "Import: keine Titel erkannt",
    "No parseable suggestions returned.":
        "Keine auswertbaren Vorschläge erhalten.",
    "Could not fetch models (using fallback list).":
        "Modelle konnten nicht geladen werden (Ersatzliste wird genutzt).",
    "Load the music library first.": "Bitte zuerst die Musikbibliothek laden.",
    "Nothing to clear — all playlists are empty.":
        "Nichts zu leeren — alle Playlists sind leer.",
    "Nothing to export — all playlists are empty.":
        "Nichts zu exportieren — alle Playlists sind leer.",
    "Nothing to save — all playlists are empty.":
        "Nichts zu speichern — alle Playlists sind leer.",
    "Nothing to save — the day decks are empty.":
        "Nichts zu speichern — die Tagesdecks sind leer.",
    "Nothing to save yet.": "Noch nichts zu speichern.",
    "Nothing to undo yet": "Noch nichts rückgängig zu machen",
    "Nothing to redo": "Nichts zu wiederholen",
    # The %s is what the step did, from describe_change_from below.
    "Undo: %s\n%s step(s) available  ·  Ctrl+Z":
        "Rückgängig: %s\n%s Schritt(e) verfügbar  ·  Strg+Z",
    "Redo: %s\n%s step(s) available  ·  Ctrl+Y":
        "Wiederholen: %s\n%s Schritt(e) verfügbar  ·  Strg+Y",
    "↶  Undo — %s": "↶  Rückgängig — %s",
    "↷  Redo — %s": "↷  Wiederholen — %s",
    # What an undo/redo step did, in words — the ↶/↷ tooltip and its toast are
    # built around these, so they have to travel together. Track names inside
    # the %s stay as they are.
    "restored %s": "%s wiederhergestellt",
    "removed %s": "%s entfernt",
    "replaced %s → %s": "%s ersetzt → %s",
    "moved %s": "%s verschoben",
    "playlist rename": "Playlist umbenannt",
    "deck layout change": "Deck-Aufteilung geändert",
    "view / settings change": "Ansicht / Einstellungen geändert",
    "“%s” and “%s”": "„%s“ und „%s“",
    "%s tracks (“%s”, “%s”, …)": "%s Titel („%s“, „%s“, …)",
    "No files added yet.": "Noch keine Dateien hinzugefügt.",
    "No song selected": "Kein Titel ausgewählt",
    "No playing row found.": "Keine spielende Zeile gefunden.",
    "No dances for this class.": "Keine Tänze für diese Klasse.",
    "No similar tracks found.": "Keine ähnlichen Titel gefunden.",
    "No similar tracks found for that file.":
        "Keine ähnlichen Titel zu dieser Datei gefunden.",
    "No reference playlist yet.": "Noch keine Referenz-Playlist.",
    "No auto-advance pause is running to extend.":
        "Es läuft keine Auto-Weiter-Pause, die verlängert werden könnte.",
    "This wall has no pads yet.": "Diese Cartwall hat noch keine Pads.",
    "Your wishlist is empty — add tracks to a wishlist first.":
        "Die Wunschliste ist leer — bitte zuerst Titel aufnehmen.",
    "Saved — it takes effect the next time you start the app.":
        "Gespeichert — wirksam beim nächsten Start der App.",
    "Then restart the app — nothing else to configure.":
        "Dann die App neu starten — sonst ist nichts einzustellen.",
    "ffmpeg not found": "ffmpeg nicht gefunden",
    "(multimedia unavailable)": "(Multimedia nicht verfügbar)",
    "Play a title first — then TSO sets its heat tempo.":
        "Erst einen Titel abspielen — dann setzt TSO das Tempo der Gruppe.",
    "This title has no detected tempo — can't equalize.":
        "Für diesen Titel wurde kein Tempo erkannt — kein Angleichen möglich.",
    "The fader can't reach that tempo for this title.":
        "Der Fader erreicht dieses Tempo für diesen Titel nicht.",
    "Preview player disabled — re-enable it in ⚙ Settings.":
        "Vorschau-Player deaktiviert — in ⚙ Einstellungen wieder einschalten.",
    "Pick a playlist again to choose a different track":
        "Erneut eine Playlist wählen, um einen anderen Titel zu nehmen",
    "Pick “Replace…” again to choose a different track":
        "Erneut „Ersetzen…“ wählen, um einen anderen Titel zu nehmen",
    # The round name comes from the config and stays as the user typed it; the
    # strategy is a catalog key of its own (STRATEGY_LABELS, translated at the
    # combo), so it arrives here already German.
    "%s: strategy set to %s — ↺ a song or dance to apply":
        "%s: Strategie auf %s gesetzt — ↺ an einem Titel oder Tanz wendet sie an",
    "%s: %s · %s — ↺ a song or dance to apply":
        "%s: %s · %s — ↺ an einem Titel oder Tanz wendet sie an",
    "↻ %s re-rolled — %s": "↻ %s neu gewürfelt — %s",
    "↻ %s re-rolled — %s · %s": "↻ %s neu gewürfelt — %s · %s",
    "Re-roll failed: %s": "Neu würfeln fehlgeschlagen: %s",
    "this comp": "dieses Turnier",
    "all playlists": "alle Playlists",

    # ── Tooltips and hints on the desk ───────────────────────────────────────
    "Listen to this track": "Diesen Titel anhören",
    "Play / stop this track": "Diesen Titel abspielen / stoppen",
    "Play / stop this file": "Diese Datei abspielen / stoppen",
    "Play / stop the base track these results are based on":
        "Ausgangstitel dieser Ergebnisse abspielen / stoppen",
    "Listen to this pad while you set its level":
        "Dieses Pad anhören, während der Pegel eingestellt wird",
    "Jump back to the start (0:00) of this track":
        "Zurück an den Anfang (0:00) dieses Titels",
    "Click to collapse / expand": "Klicken zum Ein- / Ausklappen",
    "Click to focus · right-click or double-click to rename":
        "Klicken zum Aktivieren · Rechtsklick oder Doppelklick zum Umbenennen",
    "Double-click to rename this page": "Doppelklick benennt diese Seite um",
    "Double-click to type a value": "Doppelklick, um einen Wert einzugeben",
    "Drag here to move": "Zum Verschieben hier ziehen",
    "Drag here to move the preview player":
        "Vorschau-Player zum Verschieben hier ziehen",
    "Unfold this playlist": "Diese Playlist aufklappen",
    "Fold the library pane to its header":
        "Bibliotheksbereich auf die Kopfzeile einklappen",
    # %s is a deck's or the 🤸 panel's own name, which stays as it is.
    "%s — folded.  Click to unfold.": "%s — eingeklappt.  Klicken zum Aufklappen.",
    "%s — folded.  Click to open.": "%s — eingeklappt.  Klicken zum Öffnen.",
    "Open the %s panel.": "Den %s-Bereich öffnen.",
    # %s is the 🤸 panel's own name (Eintanzen), which stays as it is.
    "Compact the %s panel to its header tab —\n"
    "click the tab (or this arrow) to open it again.":
        "Den %s-Bereich auf seinen Kopf-Reiter einklappen —\n"
        "auf den Reiter (oder diesen Pfeil) klicken öffnet ihn wieder.",
    "Close the preview and stop playback  (Ctrl+X)":
        "Vorschau schließen und Wiedergabe stoppen  (Strg+X)",
    "Close the tournament day — clears all 📅 day decks":
        "Turniertag schließen — leert alle 📅 Tagesdecks",
    "Back to this slot's default key": "Zurück zur Standardtaste dieses Platzes",
    "Export or import this wall": "Diese Cartwall exportieren oder importieren",
    "Duck to 20 % / back to full": "Auf 20 % absenken / zurück auf voll",
    "Reset the tempo to ±0 % (or double-click the fader)":
        "Tempo auf ±0 % zurücksetzen (oder Doppelklick auf den Fader)",
    "Volume adjustment of this track by Equalize volume (R128)":
        "Lautstärkeanpassung dieses Titels durch Lautstärke angleichen (R128)",
    "When this file was created in the library":
        "Wann diese Datei in der Bibliothek angelegt wurde",
    "Replace via the similar-tracks picker":
        "Über die Auswahl ähnlicher Titel ersetzen",
    "Put the shipped rule set back.": "Mitgeliefertes Regelwerk wiederherstellen.",
    "Put the whole transcript on the clipboard.":
        "Den gesamten Verlauf in die Zwischenablage legen.",
    "Esc closes  ·  double-click leaves full screen":
        "Esc schließt  ·  Doppelklick verlässt den Vollbildmodus",
    "Pick a length or type one: m:ss, seconds, or 'full'":
        "Länge wählen oder eingeben: m:ss, Sekunden oder 'komplett'",
    "m:ss, seconds, or 'full' — Enter to keep, Esc to abandon":
        "m:ss, Sekunden oder 'komplett' — Enter übernimmt, Esc verwirft",
    "full — to each title's own end": "komplett — bis zum eigenen Ende jedes Titels",
    # The play-length readout in its off position; typed back, it parses to 0.
    "full": "komplett",
    "no marks — scrub to a crash and hit 🎯":
        "keine Marken — zu einem Schlag spulen und 🎯 drücken",
    "“Proven” = songs in any of your playlists · “New” = in none.":
        "„Bewährt“ = Titel aus einer deiner Playlists · „Neu“ = aus keiner.",
    "e.g. a song title, mood, or leave blank":
        "z. B. ein Titel, eine Stimmung — oder leer lassen",
    "API base URL:": "API-Basis-URL:",
    "API key  (free OpenRouter key from openrouter.ai/keys):":
        "API-Schlüssel  (kostenloser OpenRouter-Schlüssel auf openrouter.ai/keys):",

    # ── Drop zones ───────────────────────────────────────────────────────────
    "Drag in playlists / files…": "Playlists / Dateien hineinziehen…",
    "Drop .m3u playlists or audio files here, or click to browse":
        "*.m3u-Playlists oder Audiodateien hierher ziehen oder klicken zum Suchen",
    "Drop an audio file here, or click to browse":
        "Audiodatei hierher ziehen oder klicken zum Suchen",
    "Drop saved .m3u playlists here, or click to browse":
        "Gespeicherte .m3u-Playlists hierher ziehen oder klicken zum Suchen",
    "Drop playlists above to check them.":
        "Playlists oben ablegen, um sie zu prüfen.",
    "Drop some files above to check them.":
        "Dateien oben ablegen, um sie zu prüfen.",
    "Saved playlists dragged in (.m3u)…":
        "Hineingezogene gespeicherte Playlists (.m3u)…",
    "Choose an .m3u file…": "Eine .m3u-Datei wählen…",
    "Browse…": "Durchsuchen…",
    "Add…": "Hinzufügen…",
    "Build / refresh…": "Erstellen / auffrischen…",
    "  Pick a colour…": "  Farbe wählen…",
    "…or pick one from the list": "…oder eine aus der Liste wählen",
    "pick a key…": "Taste wählen…",
    "↑ resolved above": "↑ oben gelöst",
    "— Latin —": "— Latein —",

    # ── The menus, buttons and tabs with an emoji in front ────────────────────
    "⚙  Settings": "⚙  Einstellungen",
    "⚗ Analysis": "⚗ Analyse",
    "🎨 Look": "🎨 Aussehen",
    "🎨  Theme": "🎨  Design",
    "📁 Paths && search": "📁 Pfade && Suche",
    "📁  New folder…": "📁  Neuer Ordner…",
    "⌨  Shortcuts…": "⌨  Tastenkürzel…",
    "❔  Shortcuts": "❔  Tastenkürzel",
    "▶  Playing": "▶  Wiedergabe",
    "▶  Playing mode": "▶  Wiedergabe-Modus",
    "▶  Load onto the focused deck": "▶  Auf das aktive Deck laden",
    "▴  Fold decks": "▴  Decks",
    "⊟  Collapse all": "⊟  Einklappen",
    "⏹  Stop all": "⏹  Alles stoppen",
    "⏹  Stop the music": "⏹  Musik stoppen",
    "⏭  Skip to the next title": "⏭  Zum nächsten Titel springen",
    "⏸  Auto-advance…": "⏸  Auto-Weiter…",
    "⏱  Wall fade-out…": "⏱  Cartwall-Ausblendzeit…",
    "⏱ calculating…": "⏱ wird berechnet…",
    "⏳  Comparing…": "⏳  Vergleiche…",
    "⚡  Generate Playlist": "⚡  Playlist erzeugen",
    "✅  Apply": "✅  Übernehmen",
    "✅  Keep": "✅  Behalten",
    "✅  Keep all": "✅  Alle behalten",
    "✅  Use this track as replacement": "✅  Diesen Titel als Ersatz nehmen",
    "✅  No duplicate songs across your open playlist(s).":
        "✅  Keine doppelten Titel in den offenen Playlists.",
    "✎  Rename…": "✎  Umbenennen…",
    "✏  Rename": "✏  Umbenennen",
    "📅  New tournament day…": "📅  Neuer Turniertag…",
    "✏️  Rename tab…": "✏️  Reiter umbenennen…",
    "✏️  Edit highlights": "✏️  Highlights bearbeiten",
    "✏  Editing — pads do not play": "✏  Bearbeiten — Pads spielen nicht",
    "✕  Close tournament day": "✕  Turniertag schließen",
    "✦  Only never played": "✦  Nur nie gespielte",
    "✦ Never played": "✦ Nie gespielt",
    "➕  Add": "➕  Hinzufügen",
    "➕  Add a heat to this round": "➕  Gruppe zu dieser Runde",
    "➕  Add files…": "➕  Dateien hinzufügen…",
    "➕  Both": "➕  Beide",
    "➕ Add competition": "➕ Turnier hinzufügen",
    "➖  Remove selected": "➖  Auswahl entfernen",
    "＋  Add playlists…": "＋  Playlists hinzufügen…",
    "⬆  Move backup up into this empty slot":
        "⬆  Reserve in diesen freien Platz hochziehen",
    "⇅  Swap these two titles\tAlt+S": "⇅  Diese beiden Titel tauschen\tAlt+S",
    "♊  Remove duplicate titles in this list":
        "♊  Doppelte Titel in dieser Liste entfernen",
    "⭐  Favorites": "⭐  Favoriten",
    "⭐  Favorites library": "⭐  Favoriten-Bibliothek",
    "🎯  Favorites library": "🎯  Favoriten-Bibliothek",
    "⭐  Open wishlists": "⭐  Offene Wunschlisten",
    "⭐  Only tracks in my wishlist(s)": "⭐  Nur Titel aus meinen Wunschlisten",
    "⭐  Find similar (in my wishlist only)":
        "⭐  Ähnliche finden (nur in der Wunschliste)",
    "⭐  Find similar in wishlist (run Audio Analysis first)":
        "⭐  Ähnliche in der Wunschliste (erst Audio-Analyse ausführen)",
    "⭐  Find similar in wishlist (wishlist is empty)":
        "⭐  Ähnliche in der Wunschliste (Wunschliste ist leer)",
    "🌱  Find similar (never played)": "🌱  Ähnliche finden (nie gespielt)",
    "🌱  Find similar, never played (run Audio Analysis first)":
        "🌱  Ähnliche, nie gespielt (erst Audio-Analyse ausführen)",
    "🌱  Freshness: all tracks": "🌱  Frische: alle Titel",
    "🔎  Find similar tracks": "🔎  Ähnliche Titel finden",
    "🔎  Find similar (run Audio Analysis first)":
        "🔎  Ähnliche finden (erst Audio-Analyse ausführen)",
    "🔍  Compare": "🔍  Vergleichen",
    "🔍  Filter title / artist / comment tag…":
        "🔍  Titel / Interpret / Kommentar filtern…",
    "🔍  Find a title in this list…\tCtrl+F":
        "🔍  Titel in dieser Liste suchen…\tStrg+F",
    "🆕 Last 30 days": "🆕 Letzte 30 Tage",
    "🆕 Last 90 days": "🆕 Letzte 90 Tage",
    "🆕 Last 12 months": "🆕 Letzte 12 Monate",
    "🆕 Last 18 months": "🆕 Letzte 18 Monate",
    "🆕 Unplanned": "🆕 Ungeplant",
    "📅  Only not since 1 y": "📅  Nur seit 1 J. nicht gespielt",
    "📅 Not since 1 y": "📅 Seit 1 J. nicht",
    "📅  Day plan": "📅  Tagesplan",
    "📅 Plan tournament day": "📅 Turniertag planen",
    "📅 Tournament day": "📅 Turniertag",
    "📅 Tournament day closed.": "📅 Turniertag geschlossen.",
    "📜  Find planned before": "📜  Früher geplante finden",
    "📜  Find planned before (load library first)":
        "📜  Früher geplante finden (erst Bibliothek laden)",
    "📜  Re-learn playlist popularity…": "📜  Playlist-Beliebtheit neu lernen…",
    "📚  Library": "📚  Bibliothek",
    "📚  Show never-played tracks": "📚  Nie gespielte Titel zeigen",
    "📋  Copy": "📋  Kopieren",
    "📋  Copy file path": "📋  Dateipfad kopieren",
    "📋  Copy file path (unavailable)": "📋  Dateipfad kopieren (nicht verfügbar)",
    "📋  Copy file path (not in your library)":
        "📋  Dateipfad kopieren (nicht in deiner Bibliothek)",
    "📋  Based on my playlist history (tracks I play together)":
        "📋  Nach meiner Playlist-Historie (Titel, die ich zusammen spiele)",
    "📝  Copy details": "📝  Details kopieren",
    "📝  Planning": "📝  Planung",
    "📝  Wish list — the titles below, in that order":
        "📝  Wunschliste — die Titel unten, in dieser Reihenfolge",
    "📂  Open folder": "📂  Ordner öffnen",
    "📂  Show in Explorer": "📂  Im Explorer zeigen",
    "📂  Show in Explorer (unavailable)": "📂  Im Explorer zeigen (nicht verfügbar)",
    "📂  Import M3U…": "📂  M3U importieren…",
    "📂  Add a folder of playlists…": "📂  Ordner mit Playlists hinzufügen…",
    "📂  Import — track paths": "📂  Import — Titelpfade",
    "📂  Drag files in": "📂  Dateien hineinziehen",
    "📂  Assign files…": "📂  Dateien zuordnen…",
    "📂  An .m3u playlist file": "📂  Eine .m3u-Playlist-Datei",
    "📂  Drop saved .m3u playlists here, or click to browse":
        "📂  Gespeicherte .m3u-Playlists hierher ziehen oder klicken",
    "📄  All pads on one page": "📄  Alle Pads auf einer Seite",
    "📊  Analyze loudness (R128)…": "📊  Lautheit analysieren (R128)…",
    "📊  Library gaps…": "📊  Lücken der Bibliothek…",
    "📊 Library gaps": "📊 Lücken der Bibliothek",
    "📤  Export wall…": "📤  Cartwall exportieren…",
    "📥  Import wall…": "📥  Cartwall importieren…",
    "📌  Save state": "📌  Zustand",
    "📌 Cartwall docked": "📌 Cartwall angedockt",
    "💾  Save M3U": "💾  M3U speichern",
    "💾  Save as M3U…": "💾  Speichern als M3U…",
    "💾  Save all": "💾  Speichern",
    "💾  Save all competition M3Us": "💾  Alle Turnier-M3Us speichern",
    "💾  Save all playlists as M3U": "💾  Alle Playlists als M3U speichern",
    "🏆  Save all and add to Tournaments":
        "🏆  Alle speichern und in „Turniere“ eintragen",
    "🏆  Save and add to Tournaments…": "🏆  Speichern und in „Turniere“ eintragen…",
    "🏆 Saved and added %d playlist to Tournaments":
        "🏆 Gespeichert und %d Playlist in „Turniere“ eingetragen",
    "🏆 Saved and added %d playlists to Tournaments":
        "🏆 Gespeichert und %d Playlists in „Turniere“ eingetragen",
    "🏆 Saved — already in Tournaments": "🏆 Gespeichert — steht schon in „Turniere“",
    "🔁  Check duplicates": "🔁  Doppelte",
    "🔁  Endless repeat": "🔁  Endlos wiederholen",
    "🔁  Replace…": "🔁  Ersetzen…",
    "🔁  Reset all replacement marks": "🔁  Alle Ersetzungsmarken zurücksetzen",
    "🔇  Probe silences…": "🔇  Stillen prüfen…",
    "🔇 No audio backend — the cartwall cannot play here.":
        "🔇 Kein Audio-Backend — die Cartwall kann hier nicht abspielen.",
    "🔈  Pull the music down while this pad plays":
        "🔈  Musik absenken, solange dieses Pad läuft",
    "🔈 No speech engine available on this system.":
        "🔈 Auf diesem System ist keine Sprachausgabe verfügbar.",
    "🖌  Wall colour": "🖌  Cartwall-Farbe",
    "🖥  Presenter": "🖥  Präsentation",
    "🖥  Presenter — DancePlaylist": "🖥  Präsentation — DancePlaylist",
    "🕒 Timetable — presenter screen": "🕒 Zeitplan — Präsentationsbildschirm",
    "✖  Remove": "✖  Entfernen",
    "🖨  Print": "🖨  Drucken",
    "🖨  Export PDF": "🖨  PDF exportieren",
    "🗑  Clear": "🗑  Leeren",
    "🗑  Remove": "🗑  Entfernen",
    "🗑  Remove this title (keep slot)":
        "🗑  Diesen Titel entfernen (Platz bleibt frei)",
    "🗑  Remove %d selected titles (keep slots)":
        "🗑  %d ausgewählte Titel entfernen (Plätze bleiben frei)",
    "🗑  Remove this title": "🗑  Diesen Titel entfernen",
    "🗑  Remove %d selected titles": "🗑  %d ausgewählte Titel entfernen",
    "🗑  Remove from tree": "🗑  Aus dem Baum entfernen",
    "🗑  Remove from wishlist": "🗑  Aus der Wunschliste entfernen",
    "🗑  Remove this backup\tCtrl+Del": "🗑  Diese Reserve entfernen\tStrg+Entf",
    "🗑  Remove this empty slot": "🗑  Diesen leeren Platz entfernen",
    "🗑  Remove this heat (all dances)\tCtrl+Del":
        "🗑  Diese Gruppe entfernen (alle Tänze)\tStrg+Entf",
    "🗑  Remove this round (all heats)":
        "🗑  Diese Runde entfernen (alle Gruppen)",
    "🗜  Compact": "🗜  Kompakt",
    "🚫  No groups": "🚫  Keine Gruppen",
    "🔢  Numbers": "🔢  Nummern",
    "🧹  Clear all": "🧹  Leeren",
    "🧹  Clear all playlists": "🧹  Alle Playlists leeren",
    "🧹  Empty this playlist": "🧹  Diese Playlist leeren",
    "🧹  Clean up database…": "🧹  Datenbank aufräumen…",
    "🧹  Export unused": "🧹  Unbenutzte exportieren",
    "🧹  Reference base": "🧹  Referenz-Basis",
    "🧹  Remove": "🧹  Entfernen",
    "🧹  Remove tracks already in a playlist":
        "🧹  Titel entfernen, die schon in einer Playlist sind",
    "🧹 Cleared all playlists.": "🧹 Alle Playlists geleert.",
    "🧹 Tournament-day playlists cleared.": "🧹 Turniertag-Playlists geleert.",
    "🧳  USB export": "🧳  USB-Export",
    "🧳 USB export": "🧳 USB-Export",
    "🧳 USB export aborted — incomplete bundle removed.":
        "🧳 USB-Export abgebrochen — unvollständiges Paket entfernt.",
    "🧭  Fix paths": "🧭  Pfade",
    "🧭  Fix (overwrite)": "🧭  Reparieren (überschreiben)",
    "🧭  Fix (swap in playlists)": "🧭  Reparieren (in Playlists tauschen)",
    "🧱  Build ALL caches…": "🧱  ALLE Caches aufbauen…",
    "🧠  Rebuild index…": "🧠  Index neu aufbauen…",
    "🤖  AI Playlist…": "🤖  KI-Playlist…",
    "🤖  AI playlist": "🤖  KI-Playlist",
    "🤖  Build": "🤖  Erzeugen",
    "🤖  Get Suggestions": "🤖  Vorschläge holen",
    "🤖  Conversation with the model": "🤖  Unterhaltung mit dem Modell",
    "🤸  Eintanzen / party playlist": "🤸  Eintanzen- / Party-Playlist",
    "🎉  Party set": "🎉  Party-Set",
    "🎉  Party playlist (alternating 3-dance rounds, all dances)":
        "🎉  Party-Playlist (abwechselnde 3-Tanz-Runden, alle Tänze)",
    "🏆  Tournaments": "🏆  Turniere",
    "🏆  Tournament set": "🏆  Turnier-Set",
    "🏆 Tournament only": "🏆 Nur Turnier",
    "🏷  Re-read MP3 tags": "🏷  MP3-Tags neu einlesen",
    "🏷  Re-read MP3 tags (unavailable)":
        "🏷  MP3-Tags neu einlesen (nicht verfügbar)",
    "🐂  Analyze PD highlights…": "🐂  PD-Highlights analysieren…",
    "🎯  Mark highlight now": "🎯  Highlight jetzt markieren",
    "🎯 Highlights cleared — 🐂 auto-detection will run again.":
        "🎯 Highlights gelöscht — 🐂 die Automatik läuft wieder.",
    "🎯 Last mark deleted — 🐂 auto-detection takes over again.":
        "🎯 Letzte Marke gelöscht — 🐂 die Automatik übernimmt wieder.",
    "🎯 Play a Paso Doble first, then click when a highlight hits.":
        "🎯 Erst einen Paso Doble abspielen, dann beim Höhepunkt klicken.",
    "🎵  Check Music": "🎵  Musik prüfen",
    "🎵  Check music speed": "🎵  Musiktempo prüfen",
    "🎵  Check music speed (unavailable)":
        "🎵  Musiktempo prüfen (nicht verfügbar)",
    "🎵  Music check": "🎵  Musikprüfung",
    "🎵 Checks": "🎵 Prüfungen",
    "🎵 Music speed": "🎵 Musiktempo",
    "🎵 Music check aborted.": "🎵 Musikprüfung abgebrochen.",
    "🎵  One flat list of": "🎵  Eine flache Liste mit",
    "🎵  Show its tracks": "🎵  Seine Titel zeigen",
    "🎵 0 titles": "🎵 0 Titel",
    "🎵 %d title": "🎵 %d Titel",
    "🎵 %d titles": "🎵 %d Titel",
    "  ·  ✦ %d new": "  ·  ✦ %d neu",
    "🎼  Build chroma cover / remix index…":
        "🎼  Chroma-Cover- / Remix-Index aufbauen…",
    "🎚️  Open playlists": "🎚️  Offene Playlists",
    "🎚️  Timbre + Rhythm (librosa)": "🎚️  Timbre + Rhythmus (librosa)",
    "🎛 Play sets": "🎛 Spiel-Sets",
    "🎛 No free pad voice — every voice holds a looping pad.":
        "🎛 Keine freie Pad-Stimme — jede Stimme hält ein laufendes Pad.",
    "🎤 Vocal": "🎤 Gesang",
    "🎙️  Only instrumental tracks (no vocals)":
        "🎙️  Nur instrumentale Titel (ohne Gesang)",
    "🎧  Open in external player": "🎧  In externem Player öffnen",
    "🌐  Whole repository": "🌐  Gesamtes Repository",
    "🌐  Build librosa index (needs librosa)":
        "🌐  Librosa-Index aufbauen (benötigt librosa)",
    "🌐  Build / refresh librosa audio index (whole repo)…":
        "🌐  Librosa-Audio-Index aufbauen / auffrischen (ganzes Repo)…",
    "🔬  Timbre Gaussian / KL (Mandel-Ellis)":
        "🔬  Timbre Gauß / KL (Mandel-Ellis)",
    "⚠  That spot is no longer in an open deck.":
        "⚠  Diese Stelle liegt in keinem offenen Deck mehr.",
    "↺  Default blue": "↺  Standardblau",
    "↺  Default rules": "↺  Standardregeln",
    # ── The chrome that was still English ─────────────────────────────────────
    "1 playlist": "1 Playlist",
    # The three counting buttons on the right of the toolbar. The deck
    # count asks for itself as a template (any number of decks fits);
    # the wishlist captions are a fixed tuple and are keyed whole.
    "%d playlist": "%d Playlist",
    "%d playlists": "%d Playlists",
    "No playlist": "Keine Playlist",
    "No wishlist": "Keine Wunschliste",
    "1 wishlist": "1 Wunschliste",
    "2 wishlists": "2 Wunschlisten",
    "3 wishlists": "3 Wunschlisten",
    "4 wishlists": "4 Wunschlisten",
    "4 wishlists (2×2)": "4 Wunschlisten (2×2)",
    "Build a practice playlist into the focused deck:\n"
    "• Eintanzen for a tournament class — the class's dances round-robin\n"
    "  (e.g. Latin S: SA, CC, RB, PD, JI …), TSO-conform, popular + fresh.\n"
    "• Party — alternating 3-dance rounds across all dances.\n"
    "Draw from your ⭐ Favorites (unused tracks), the open wishlists\n"
    "or a chosen .m3u file.":
        "Eine Übungs-Playlist in das fokussierte Deck bauen:\n"
        "• Eintanzen für eine Startgruppe — die Tänze der Gruppe im\n"
        "  Rundlauf (z. B. Latein S: SA, CC, RB, PD, JI …), TSO-konform,\n"
        "  beliebt + frisch.\n"
        "• Party — abwechselnde 3-Tanz-Runden über alle Tänze.\n"
        "Quelle: deine ⭐ Favoriten (ungenutzte Titel), die offenen\n"
        "Wunschlisten oder eine gewählte .m3u-Datei.",
    "Check every deck track for tournament problems:\n"
    "• Tempo: filename label (T51 = takt/bars per minute, via the dance's\n"
    "  meter) vs the tempo librosa measured — catches mislabeled files.\n"
    "• TSO range: is the tempo inside the official per-dance takt range.\n"
    "• Length: warns when a song is shorter than the 1:30–1:45 play time\n"
    "  or longer than 4:00.\n"
    "• Round structure: uneven dance counts in a round and final/semifinal\n"
    "  heat-count deviations.\n"
    "Suspects can be listened to, removed or replaced from the report.\n"
    "Tempo/range checks need 🔬 Audio Analysis for the measured tempo.":
        "Jeden Titel in den Decks auf Turnierprobleme prüfen:\n"
        "• Tempo: Angabe im Dateinamen (T51 = Takte pro Minute, über die\n"
        "  Taktart des Tanzes) gegen das von librosa gemessene Tempo —\n"
        "  findet falsch beschriftete Dateien.\n"
        "• TSO-Bereich: liegt das Tempo im offiziellen Taktbereich des Tanzes.\n"
        "• Länge: warnt, wenn ein Titel kürzer als die Spielzeit von\n"
        "  1:30–1:45 oder länger als 4:00 ist.\n"
        "• Rundenaufbau: ungleiche Tanzanzahl in einer Runde und\n"
        "  Abweichungen bei der Gruppenzahl in Finale/Semifinale.\n"
        "Verdächtige Titel lassen sich aus dem Bericht anhören, entfernen\n"
        "oder ersetzen.\n"
        "Tempo- und Bereichsprüfung brauchen 🔬 Audio-Analyse für das\n"
        "gemessene Tempo.",
    "Collapse every round and dance header of every playlist —\n"
    "click again to open them all.":
        "Alle Runden- und Tanzüberschriften aller Playlists zuklappen —\n"
        "nochmal klicken öffnet sie wieder.",
    "Cycle the playlist headers: full → 🗜 Compact (per-dance header rows\n"
    "hidden, each round lists its songs directly) → 🚫 No groups (round and\n"
    "─── section headers dropped too, so the list — an Eintanzen / party\n"
    "list above all — is one flat run of songs) → 🔢 Numbers (no groups,\n"
    "plus an Nb. column up front counting the titles).":
        "Die Playlist-Überschriften durchschalten: voll → 🗜 Kompakt\n"
        "(Tanz-Überschriften ausgeblendet, jede Runde listet ihre Titel\n"
        "direkt) → 🚫 Ohne Gruppen (auch Runden- und ───-Überschriften\n"
        "fallen weg, die Liste — vor allem eine Eintanz- / Partyliste —\n"
        "ist ein durchgehender Lauf) → 🔢 Nummern (ohne Gruppen, dazu\n"
        "vorne eine Nr.-Spalte, die die Titel zählt).",
    "Cycle the wishlist area: off → 1 → 2 → 3 → 4 → 4 stacked 2×2.\n"
    "Right click walks it backwards.\n"
    "Off hides it entirely, even with multiple decks.\n"
    "Double-click any deck/wishlist title to rename it.":
        "Den Wunschlisten-Bereich durchschalten: aus → 1 → 2 → 3 → 4 →\n"
        "4 gestapelt 2×2.\n"
        "Rechtsklick läuft rückwärts.\n"
        "Aus blendet ihn ganz aus, auch bei mehreren Decks.\n"
        "Doppelklick auf einen Deck-/Wunschlistentitel benennt ihn um.",
    "Empty every playlist deck (wishlists are kept).\n"
    "Tip: Del on a deck's title clears just that one playlist;\n"
    "Del on a wishlist's title clears that wishlist.":
        "Alle Playlist-Decks leeren (Wunschlisten bleiben erhalten).\n"
        "Tipp: Entf auf dem Titel eines Decks leert nur diese eine Playlist,\n"
        "Entf auf dem Titel einer Wunschliste leert diese Wunschliste.",
    "Export every non-empty playlist deck to its own .m3u in the\n"
    "playlist folder at once (wishlists are not included).\n"
    "Each file is named after its deck title.":
        "Jedes nicht leere Playlist-Deck auf einmal als eigene .m3u in den\n"
        "Playlist-Ordner exportieren (Wunschlisten sind nicht dabei).\n"
        "Jede Datei wird nach ihrem Decktitel benannt.",
    "Export playlists as a self-contained venue bundle — asks first\n"
    "whether to take all open decks, only the 📅 tournament day, or\n"
    "saved .m3u files dragged in (wishlists are never bundled).\n"
    "One sub-folder per playlist holding its tracks copied in numbered\n"
    "play order (0_0_1 - Title WW29.mp3) plus the playlist's .m3u — each\n"
    "folder plays in order even without the M3U, from any drive,\n"
    "laptop or UltraMixer at the venue (no path fixing needed there).":
        "Playlists als eigenständiges Turnierpaket exportieren — fragt\n"
        "zuerst, ob alle offenen Decks, nur der 📅 Turniertag oder\n"
        "hineingezogene .m3u-Dateien genommen werden (Wunschlisten kommen\n"
        "nie mit).\n"
        "Ein Unterordner je Playlist mit ihren Titeln, kopiert in\n"
        "nummerierter Spielreihenfolge (0_0_1 - Titel WW29.mp3), dazu die\n"
        ".m3u der Playlist — jeder Ordner spielt auch ohne die M3U in der\n"
        "richtigen Reihenfolge, von jedem Laufwerk, Laptop oder UltraMixer\n"
        "vor Ort (dort ist keine Pfadkorrektur nötig).",
    "Export the focused playlist as a printable PDF\n"
    "(rounds, heats, titles, lengths) into the playlist folder.":
        "Die fokussierte Playlist als druckbares PDF\n"
        "(Runden, Gruppen, Titel, Längen) in den Playlist-Ordner exportieren.",
    "Fold every visible playlist deck and wishlist to its header tab —\n"
    "click again to open them all.\n"
    "Click a single tab (or its arrow) to open just that one.":
        "Alle sichtbaren Playlist-Decks und Wunschlisten auf ihren\n"
        "Kopfreiter einklappen — nochmal klicken öffnet sie wieder.\n"
        "Ein Klick auf einen einzelnen Reiter (oder seinen Pfeil) öffnet\n"
        "nur diesen.",
    "Plan a whole tournament day: define the day's competitions\n"
    "(style, age, class, round pattern) and generate them all at once\n"
    "into the 📅 Tournament-day tab — eight dedicated day decks in two\n"
    "sub-tabs, separate from the normal playlists; more than 8\n"
    "competitions stack several per deck. All share one no-repeat\n"
    "pool, so a song never appears in two of the day's competitions\n"
    "(Paso excepted). Exports write one M3U per competition.":
        "Einen ganzen Turniertag planen: die Turniere des Tages festlegen\n"
        "(Sektion, Altersgruppe, Startklasse, Rundenschema) und alle auf\n"
        "einmal in den Reiter 📅 Turniertag erzeugen — acht eigene\n"
        "Tagesdecks in zwei Unterreitern, getrennt von den normalen\n"
        "Playlists; bei mehr als 8 Turnieren liegen mehrere je Deck.\n"
        "Alle teilen sich einen Pool ohne Wiederholung, damit ein Titel\n"
        "nie in zwei Turnieren des Tages auftaucht (Paso ausgenommen).\n"
        "Der Export schreibt eine M3U je Turnier.",
    "Relocate broken track references in the visible deck(s) to matching\n"
    "real files in the library — fixes moved folders / changed drive\n"
    "letters after an import. Anything still unresolved is reported.":
        "Kaputte Titelverweise in den sichtbaren Decks auf passende echte\n"
        "Dateien in der Bibliothek umbiegen — behebt verschobene Ordner /\n"
        "geänderte Laufwerksbuchstaben nach einem Import. Was danach noch\n"
        "offen ist, wird gemeldet.",
    "Save the whole working session right now — every deck, wishlist and the\n"
    "window layout — so it comes back exactly on the next launch.  "
    "(Ctrl+Shift+S)\n"
    "(This also happens automatically on every edit and on close.)":
        "Die ganze Arbeitssitzung jetzt sichern — jedes Deck, jede\n"
        "Wunschliste und die Fensteraufteilung — damit sie beim nächsten\n"
        "Start genau so wiederkommt.  (Strg+Umschalt+S)\n"
        "(Das passiert ohnehin bei jeder Änderung und beim Schließen.)",
    "Scan the visible playlist deck(s) for songs that appear more than once,\n"
    "then resolve each: keep the ones you want and replace the rest with a\n"
    "similar track (chosen from the Similar-Tracks picker).":
        "Die sichtbaren Playlist-Decks nach mehrfach vorkommenden Titeln\n"
        "durchsuchen und jeden Fall auflösen: die gewünschten behalten und\n"
        "den Rest durch einen ähnlichen Titel ersetzen (aus der Auswahl\n"
        "ähnlicher Titel).",
    "Show / hide the library browser under the wishlists:\n"
    "filter the whole competition library and drag tracks\n"
    "straight into a deck or wishlist.":
        "Den Bibliotheksbrowser unter den Wunschlisten ein- / ausblenden:\n"
        "die ganze Turnierbibliothek filtern und Titel direkt in ein Deck\n"
        "oder eine Wunschliste ziehen.",
    "Show / hide the 🎛 sample-pad wall:\n"
    "drop Tusch, applause or a background bed onto a pad and tap it —\n"
    "it plays on top of the running music instead of replacing it.\n"
    "Drag its title bar to dock it left / right / below, or float it.":
        "Die 🎛 Sample-Pad-Wand ein- / ausblenden:\n"
        "Tusch, Applaus oder einen Klangteppich auf ein Pad ziehen und\n"
        "antippen — es läuft über der laufenden Musik, statt sie zu\n"
        "ersetzen.\n"
        "Die Titelleiste ziehen, um sie links / rechts / unten anzudocken\n"
        "oder frei schweben zu lassen.",
    "Space: play / stop the selected song\n"
    "Ctrl + ← / → : seek 30 s back / forward\n"
    "Click a round / dance header to collapse or expand it":
        "Leertaste: den gewählten Titel abspielen / stoppen\n"
        "Strg + ← / → : 30 s zurück / vor springen\n"
        "Klick auf eine Runden- / Tanzüberschrift klappt sie zu oder auf",
    "💥  The app did not shut down cleanly last time.\n"
    "\n"
    "The crash log of that session is under 'Show Details…' (it is overwritten "
    "on every start).":
        "💥  Die App wurde beim letzten Mal nicht sauber beendet.\n"
        "\n"
        "Das Absturzprotokoll dieser Sitzung steht unter „Details anzeigen…“ (es "
        "wird bei jedem Start überschrieben).",
    "AI Error": "KI-Fehler",
    "API key needed": "API-Schlüssel nötig",
    "CLAUDE_CONFIG_DIR — which claude login the CLI uses.\n"
    "Empty leaves it to the CLI (~/.claude).":
        "CLAUDE_CONFIG_DIR — welche claude-Anmeldung die CLI benutzt.\n"
        "Leer überlässt das der CLI (~/.claude).",
    "Enter a free OpenRouter API key (openrouter.ai/keys).":
        "Einen kostenlosen OpenRouter-API-Schlüssel eintragen (openrouter.ai/keys).",
    "Free text. The tempo table, the track catalog and the answer\n"
    "format are added automatically — describe only what makes a\n"
    "playlist good in your eyes.":
        "Freier Text. Die Tempotabelle, der Titelkatalog und das\n"
        "Antwortformat kommen automatisch dazu — beschreibe nur, was für\n"
        "dich eine gute Playlist ausmacht.",
    "How much text this run moves.\n"
    "\n"
    "Sent is everything the model was given (the rules, the library summary, "
    "the catalog rows), back is what it answered. The biggest turn is the one "
    "that has to fit the model's context window: one prompt plus its reply.\n"
    "\n"
    "Token counts are estimated at ~4 characters each — no backend here "
    "reports its real usage.":
        "Wie viel Text dieser Lauf bewegt.\n"
        "\n"
        "Gesendet ist alles, was das Modell bekommen hat (die Regeln, die "
        "Zusammenfassung der Bibliothek, die Katalogzeilen), zurück ist seine "
        "Antwort. Der größte Zug ist der, der in das Kontextfenster des Modells "
        "passen muss: eine Anfrage samt Antwort.\n"
        "\n"
        "Die Token werden mit ~4 Zeichen je Token geschätzt — kein Backend hier "
        "meldet seinen echten Verbrauch.",
    "Name the tracks yourself. The model does the looking up: it finds\n"
    "the library title behind every shortened or mistyped wish.":
        "Die Titel selbst benennen. Das Nachschlagen übernimmt das Modell:\n"
        "es findet zu jedem abgekürzten oder vertippten Wunsch den Titel\n"
        "aus der Bibliothek.",
    "Style, age, start class, dances and the round pattern come from\n"
    "the panel on the left. The model only picks and orders the music.":
        "Sektion, Altersgruppe, Startklasse, Tänze und Rundenschema kommen\n"
        "aus dem Bereich links. Das Modell wählt und ordnet nur die Musik.",
    "Write the wishes however you like — one per line, a sentence, or a whole "
    "sheet pasted in with a column per dance:\n"
    "\n"
    "lw            t               ww        qs\n"
    "White wings   a new life      Willow    quit playing games !!\n"
    "melancolia !  Dance of love   Kiss me   youre so fine\n"
    "\n"
    "Short names and typos are fine. A two-letter code beside a title names "
    "its dance, ! or !! marks the ones you really want, and anything else you "
    "write here is read as an instruction.":
        "Schreib die Wünsche, wie du magst — einen je Zeile, als Satz oder als "
        "ganze Tabelle, hineinkopiert mit einer Spalte je Tanz:\n"
        "\n"
        "lw            t               ww        qs\n"
        "White wings   a new life      Willow    quit playing games !!\n"
        "melancolia !  Dance of love   Kiss me   youre so fine\n"
        "\n"
        "Kurze Namen und Tippfehler sind kein Problem. Ein Zwei-Buchstaben-Kürzel "
        "neben einem Titel nennt seinen Tanz, ! oder !! markiert die, die du "
        "wirklich willst, und alles andere, was du hier schreibst, wird als "
        "Anweisung gelesen.",
    "e.g. 'club evening, keep it modern', 'no covers in the final',\n"
    "'the wishes are for a show — put the two marked ones last'":
        "z. B. „Vereinsabend, eher modern“, „keine Coverversionen im Finale“,\n"
        "„die Wünsche sind für eine Show — die zwei markierten zum Schluss“",
    "🏆  Competition playlist — rounds and heats from the left panel":
        "🏆  Turnier-Playlist — Runden und Gruppen aus dem Bereich links",
    "Drag .m3u playlists or audio files here; drag a title out (e.g. to the "
    "reference field) to remove it":
        "Ziehe .m3u-Playlists oder Audiodateien hierher; einen Titel herausziehen "
        "(z. B. in das Referenzfeld) entfernt ihn",
    "Open file": "Datei öffnen",
    "Open folder": "Ordner öffnen",
    "Show in Explorer": "Im Explorer anzeigen",
    "📂  Drop .m3u playlists (or audio files) here, or click to browse":
        "📂  .m3u-Playlists (oder Audiodateien) hierher ziehen oder klicken zum "
        "Auswählen",
    "Could not parse any competition lines from the pasted text.\n"
    "Each line needs a class label, a style (STD/LAT) and the\n"
    "heat counts, e.g.  'U21 STD (50) 4 - 4 - 3 - 2 - 1'.":
        "Aus dem eingefügten Text ließ sich keine Turnierzeile lesen.\n"
        "Jede Zeile braucht eine Startklasse, eine Sektion (STD/LAT) und\n"
        "die Gruppenzahlen, z. B.  „U21 STD (50) 4 - 4 - 3 - 2 - 1“.",
    "Let a model build the playlist instead of the scoring algorithm.\n"
    "You give it the rules (a default set is filled in), it picks and\n"
    "orders the music — either into the rounds/heats configured above\n"
    "or as one flat list.\n"
    "Runs on your Claude subscription via the claude CLI, with\n"
    "OpenRouter as fallback.":
        "Die Playlist von einem Modell bauen lassen statt vom\n"
        "Bewertungsalgorithmus. Du gibst die Regeln vor (ein Standardsatz\n"
        "ist vorausgefüllt), es wählt und ordnet die Musik — entweder in\n"
        "die oben eingestellten Runden/Gruppen oder als eine flache\n"
        "Liste.\n"
        "Läuft über dein Claude-Abo mittels der claude-CLI, mit\n"
        "OpenRouter als Rückfallweg.",
    # The AI dialog's login hint reaches its label through a variable.
    "Runs through the claude CLI on your Claude subscription — no API key. "
    "Falls back to OpenRouter if that fails.":
        "Läuft über die claude-CLI mit deinem Claude-Abo — ohne API-Schlüssel. "
        "Klappt das nicht, springt OpenRouter ein.",
    "⚠ claude CLI not found — OpenRouter will be used. Set the "
    "CLAUDE_BIN environment variable to use your subscription.":
        "⚠ claude-CLI nicht gefunden — OpenRouter wird benutzt. Setze die "
        "Umgebungsvariable CLAUDE_BIN, um dein Abo zu nutzen.",
    "Load an existing .m3u into the focused deck or wishlist.\n"
    "Decks detect rounds, dances and heats automatically — a final\n"
    "with extra backup variants (e.g. two Sambas) is handled too.\n"
    "A focused wishlist appends the tracks flat.":
        "Eine vorhandene .m3u in das fokussierte Deck oder die fokussierte\n"
        "Wunschliste laden. Decks erkennen Runden, Tänze und Gruppen\n"
        "automatisch — auch ein Finale mit zusätzlichen Ersatzvarianten\n"
        "(z. B. zwei Sambas). Eine fokussierte Wunschliste hängt die Titel\n"
        "flach an.",
    "No competitions parsed": "Keine Turniere erkannt",
    "On: changing a round's strategy re-rolls that whole round.\n"
    "Off: keep the current grid and change only the songs you want\n"
    "via the ↺ buttons (they use the newly selected strategy).":
        "An: die Strategie einer Runde zu ändern würfelt die ganze Runde\n"
        "neu.\n"
        "Aus: das bestehende Raster bleibt, und nur die gewünschten Titel\n"
        "werden über die ↺-Knöpfe getauscht (sie benutzen die neu\n"
        "gewählte Strategie).",
    "Open the last conversation with the model again.\n"
    "It is kept until the next AI run starts.":
        "Das letzte Gespräch mit dem Modell wieder öffnen.\n"
        "Es bleibt erhalten, bis der nächste KI-Lauf startet.",
    "When enabled, songs within a round are scored for\n"
    "timbral similarity to the round's first song.\n"
    "Disable for more varied song choices.":
        "Wenn aktiv, werden die Titel einer Runde nach ihrer Timbre-Ähnlichkeit\n"
        "zum ersten Titel der Runde bewertet.\n"
        "Ausschalten für abwechslungsreichere Titelauswahl.",
    "Which titles ⚡ Generate may pick from.\n"
    "Favorites library — everything scanned from your library folder.\n"
    "Open wishlists — only what you parked in the ⭐ wishlists.\n"
    "An .m3u file — only the tracks in that one playlist.\n"
    "With the last two, a dance the pool cannot cover stays blank.":
        "Aus welchen Titeln ⚡ Erzeugen wählen darf.\n"
        "Favoriten-Bibliothek — alles, was aus deinem Bibliotheksordner\n"
        "eingelesen wurde.\n"
        "Offene Wunschlisten — nur das, was in den ⭐ Wunschlisten liegt.\n"
        "Eine .m3u-Datei — nur die Titel dieser einen Playlist.\n"
        "Bei den letzten beiden bleibt ein Tanz leer, den der Pool nicht\n"
        "abdecken kann.",
    "“Proven” = songs you played in THIS competition's past lists · “New” = "
    "never played.  🎯 keeps a round to this competition; untick it to draw "
    "that round from ALL your playlists.":
        "„Bewährt“ = Titel, die du in früheren Listen DIESES Turniers gespielt "
        "hast · „Neu“ = nie gespielt.  🎯 hält eine Runde bei diesem Turnier; "
        "abwählen zieht diese Runde aus ALLEN deinen Playlists.",
    "🎯 ticked: draw this round's songs from THIS competition's past lists "
    "only.\n"
    "Unticked: draw from ALL your playlists.":
        "🎯 gesetzt: die Titel dieser Runde nur aus den früheren Listen DIESES "
        "Turniers ziehen.\n"
        "Nicht gesetzt: aus ALLEN deinen Playlists ziehen.",
    "<b>App mode</b> — which side of the app is shown:":
        "<b>App-Modus</b> — welche Seite der App gezeigt wird:",
    "<b>Favorites library</b> — scanned on start (your tanzcds folder):":
        "<b>Favoriten-Bibliothek</b> — wird beim Start eingelesen (dein "
        "tanzcds-Ordner):",
    "<b>Referenzpfad</b> — base folder the playlist files live in on THIS PC; "
    "🧭 Fix paths re-roots broken references here (e.g. C:\\Users\\…\\my "
    "music\\tanzcds):":
        "<b>Referenzpfad</b> — Basisordner, in dem die Playlist-Dateien auf DIESEM "
        "PC liegen; 🧭 Pfade korrigieren hängt kaputte Verweise hier wieder ein (z. "
        "B. C:\\Users\\…\\my music\\tanzcds):",
    "<b>Save-as folder</b> — where 'Save as M3U…' starts (e.g. "
    "D:\\Dropbox\\Turniere):":
        "<b>Speichern-unter-Ordner</b> — wo „Als M3U speichern…“ beginnt (z. B. "
        "D:\\Dropbox\\Turniere):",
    "<b>Search folders</b> — where else to look for a track when a playlist "
    "was written on another PC, one folder per line (e.g. F:\\my music and "
    "C:\\Users\\…\\Documents\\datein\\my music):":
        "<b>Suchordner</b> — wo sonst nach einem Titel gesucht wird, wenn eine "
        "Playlist auf einem anderen PC geschrieben wurde, ein Ordner je Zeile (z. "
        "B. F:\\my music und C:\\Users\\…\\Documents\\datein\\my music):",
    "<b>Tournament playlists</b> — learned for popularity: .m3u files and/or "
    "tournament folders with copied music (e.g. H:\\DM Latein 2026):":
        "<b>Turnier-Playlists</b> — für die Beliebtheit gelernt: .m3u-Dateien "
        "und/oder Turnierordner mit kopierter Musik (z. B. H:\\DM Latein 2026):",
    "<b>What do you want to use this app for?</b>":
        "<b>Wofür willst du diese App benutzen?</b>",
    "<b>Whole music repository</b> — used by global search (e.g. F:\\my music):":
        "<b>Gesamter Musikbestand</b> — von der globalen Suche benutzt (z. B. "
        "F:\\my music):",
    "<b>▶ Player position</b> — where the master player stands in ▶ Playing "
    "mode:":
        "<b>▶ Player-Position</b> — wo der Hauptplayer im Modus ▶ Abspielen steht:",
    "<b>🌐 Language</b> — menus, buttons and dialogs:":
        "<b>🌐 Sprache</b> — Menüs, Knöpfe und Dialoge:",
    # The 🌐 combo under that heading. Each row NAMES its language in that
    # language and keeps that name — a picker one cannot read is no picker —
    # so only the explanation after the dash is translated. There is
    # deliberately no entry for "🇩🇪  Deutsch — Menüs, Knöpfe und Dialoge auf
    # Deutsch": it is already German, and an entry mapping it to itself is
    # the one thing test_no_entry_translates_to_itself forbids. It therefore
    # also stays German on an English desk, which is the same rule seen from
    # the other side.
    "🇬🇧  English — the language the app is written in (default)":
        "🇬🇧  English — die Sprache, in der die App geschrieben ist (Standard)",
    "Every label exactly as the app ships it.":
        "Jede Beschriftung genau so, wie die App sie ausliefert.",
    "Menus, buttons and dialogs are translated. Track names, dance names and "
    "anything read from your files stay as they are.":
        "Menüs, Knöpfe und Dialoge werden übersetzt. Titelnamen, Tanznamen und "
        "alles, was aus deinen Dateien gelesen wird, bleiben wie sie sind.",
    "<b>🎚 Accent colour</b> — the blue the buttons, sliders and the ▶ player "
    "panel are built around:":
        "<b>🎚 Akzentfarbe</b> — das Blau, um das herum Knöpfe, Regler und der ▶ "
        "Player-Bereich gebaut sind:",
    "<b>🎚 TSO pitch target</b> — which takt the 🎚 button pitches a heat to. "
    "<i>Middle of the round</i> puts the round on one takt: the takt most of "
    "its titles are on where a step of one gets the rest there cheaply "
    "(T30+T31+T31 Cha-Chas → 31), the middle of its takte where it does not "
    "(T24+T25+T25 Rumbas → 24.5, T50+T52+T52 Quicksteps → 51). Nothing moves "
    "more than a takt. A fixed takt puts every title of that dance on the same "
    "tempo instead — worth setting on the slow dances, where one takt out of "
    "24 is twice the pitch shift one takt out of 50 is.":
        "<b>🎚 TSO-Zieltakt</b> — auf welchen Takt der 🎚 Knopf eine Gruppe "
        "zieht. <i>Mittelwert der Runde</i> bringt die Runde auf einen Takt: auf den "
        "Takt, auf dem die meisten ihrer Titel liegen, wenn ein Schritt von einem "
        "Takt den Rest günstig dorthin bringt (T30+T31+T31 Cha-Chas → 31), sonst "
        "auf die Mitte ihrer Takte (T24+T25+T25 Rumben → 24,5, T50+T52+T52 "
        "Quicksteps → 51). Nichts wird um mehr als einen Takt verschoben. Ein "
        "fester Takt bringt stattdessen jeden Titel dieses Tanzes auf dasselbe "
        "Tempo — lohnt sich bei den langsamen Tänzen, wo ein Takt von 24 doppelt "
        "so viel Tonhöhenänderung ist wie ein Takt von 50.",
    "<b>🎛 Play sets</b> — the two buttons on the ▶ Playing panel put the "
    "controls on these values in one press:":
        "<b>🎛 Abspiel-Sets</b> — die zwei Knöpfe im Bereich ▶ Abspielen stellen "
        "die Bedienelemente mit einem Druck auf diese Werte:",
    "<b>🎨 Theme</b> — the classic light or dark, or one of the looks:":
        "<b>🎨 Erscheinungsbild</b> — das klassische Hell oder Dunkel oder "
        "einer der Looks:",
    "<b>🎵 Check music</b> — thresholds used by the tournament checks (open "
    "decks and dragged-in files):":
        "<b>🎵 Musik prüfen</b> — Schwellenwerte der Turnierprüfungen (offene Decks "
        "und hineingezogene Dateien):",
    "<b>🔊 Audio backend</b> — the engine every title is played through:":
        "<b>🔊 Audio-Backend</b> — die Maschine, über die jeder Titel abgespielt "
        "wird:",
    "Build everything on this tab in one go for a chosen library, in turn:\n"
    "🎚 librosa → 📊 loudness → 🔇 silences → 🐂 PD highlights → 🧠 OpenL3 →\n"
    "🎼 Chroma. Reuses anything already cached and can be cancelled\n"
    "between/within steps. Read-only; your audio files are never modified.\n"
    "Skips models that aren't installed — and 🎙 Demucs vocals, which are far\n"
    "slower than the rest and stay a deliberate choice.":
        "Alles auf diesem Reiter in einem Durchlauf für eine gewählte\n"
        "Bibliothek bauen, der Reihe nach:\n"
        "🎚 librosa → 📊 Lautheit → 🔇 Stillen → 🐂 PD-Höhepunkte → 🧠 OpenL3 →\n"
        "🎼 Chroma. Nutzt bereits Zwischengespeichertes weiter und lässt sich\n"
        "zwischen und innerhalb der Schritte abbrechen. Nur lesend; deine\n"
        "Audiodateien werden nie verändert.\n"
        "Überspringt nicht installierte Modelle — und 🎙 Demucs-Gesang, der\n"
        "weit langsamer ist als der Rest und bewusst eine eigene\n"
        "Entscheidung bleibt.",
    "Chroma vectors match melody/harmony instead of sound, so the\n"
    "Similar-Tracks window can find remixes & covers of the same tune.\n"
    "librosa-only; reuses anything already cached.":
        "Chroma-Vektoren vergleichen Melodie/Harmonie statt Klang, damit\n"
        "das Fenster für ähnliche Titel Remixe und Coverversionen desselben\n"
        "Stücks findet.\n"
        "Nur mit librosa; nutzt bereits Zwischengespeichertes weiter.",
    "Close this and filter the library pane to the selected\n"
    "row's dance + class, showing only tracks you have never played.":
        "Dieses Fenster schließen und den Bibliotheksbereich auf Tanz und\n"
        "Startklasse der gewählten Zeile filtern — gezeigt werden nur nie\n"
        "gespielte Titel.",
    "Compute the selected similarity index over the library (global repo\n"
    "when global search is on, else the favorites library). Reuses anything\n"
    "already cached; only missing vectors are added.":
        "Den gewählten Ähnlichkeitsindex über die Bibliothek berechnen (den\n"
        "globalen Bestand, wenn die globale Suche an ist, sonst die\n"
        "Favoriten-Bibliothek). Nutzt bereits Zwischengespeichertes weiter;\n"
        "nur fehlende Vektoren kommen dazu.",
    "Detect the highlights of every Paso Doble in the music library\n"
    "and store them in the local database, so the highlight stop is\n"
    "armed instantly on playback (already-analyzed tracks are skipped).":
        "Die Höhepunkte jedes Paso Doble in der Musikbibliothek erkennen\n"
        "und in der lokalen Datenbank ablegen, damit der Höhepunkt-Stopp\n"
        "beim Abspielen sofort scharf ist (bereits analysierte Titel\n"
        "werden übersprungen).",
    "Find the silent stretches of every track of the music library\n"
    "(via ffmpeg; already-probed tracks are skipped, results are\n"
    "cached). Playback probes each new title itself — doing it up\n"
    "front keeps that decode off the disk during a tournament.":
        "Die stillen Abschnitte jedes Titels der Musikbibliothek finden\n"
        "(über ffmpeg; bereits geprüfte Titel werden übersprungen, die\n"
        "Ergebnisse werden zwischengespeichert). Beim Abspielen prüft\n"
        "jeder neue Titel das selbst — vorab erledigt, hält das die\n"
        "Dekodierung während eines Turniers von der Platte fern.",
    "Global search needs the repo's audio analyzed once (⚗ Analysis tab). "
    "Analysis only <i>reads</i> your files — it never modifies them. Results "
    "are cached, so repeat searches are fast.":
        "Die globale Suche braucht den Bestand einmal analysiert (Reiter ⚗ "
        "Analyse). Die Analyse <i>liest</i> deine Dateien nur — sie verändert sie "
        "nie. Die Ergebnisse werden zwischengespeichert, wiederholte Suchen sind "
        "also schnell.",
    # The − / + beside the play-length display. The %s are the step in seconds
    # and the m:ss the length stops cutting at — numbers, not words.
    "Shorter by %s s": "%s s kürzer",
    "Longer by %s s — past %s the title plays to its end":
        "%s s länger — ab %s spielt der Titel bis zum Ende",
    # The − / + beside the tempo fader. The first %s is the step with its
    # percent sign, the second is the direction below.
    "Tempo %s %s — hold to glide": "Tempo %s %s — zum Gleiten halten",
    "slower": "langsamer",
    "faster": "schneller",
    "How long the volume takes to ramp down to 0 when\n"
    "the play length cuts a title — half-second steps":
        "Wie lange die Lautstärke braucht, um auf 0 abzufallen, wenn\n"
        "die Spielzeit einen Titel abschneidet — in halben Sekunden",
    "Invalid rounds": "Ungültige Runden",
    "Library gap dashboard: per dance × class — pool size, tournament-\n"
    "tempo compliance, proven/fresh split and staleness. Thin pools\n"
    "are marked red.":
        "Lückenübersicht der Bibliothek: je Tanz × Startklasse — Poolgröße,\n"
        "Einhaltung des Turniertempos, Verhältnis bewährt/frisch und\n"
        "Überalterung. Dünne Pools sind rot markiert.",
    "Measure each track's vocal share by actually separating the vocals\n"
    "from the music (Demucs source separation) — far more reliable than\n"
    "the tag/filename heuristics for the Vocal/Instrumental filter.\n"
    "~7 s per track, cached; already-measured tracks are skipped.":
        "Den Gesangsanteil jedes Titels messen, indem der Gesang wirklich\n"
        "von der Musik getrennt wird (Demucs-Quellentrennung) — für den\n"
        "Filter Gesang/Instrumental weit verlässlicher als die Heuristik\n"
        "über Tags und Dateinamen.\n"
        "~7 s je Titel, zwischengespeichert; bereits gemessene Titel\n"
        "werden übersprungen.",
    "Measure the EBU R128 loudness of every track of the music\n"
    "library (via ffmpeg; already-measured tracks are skipped,\n"
    "results are cached). Enables 🔊 Equalize volume in Playing mode.":
        "Die EBU-R128-Lautheit jedes Titels der Musikbibliothek messen\n"
        "(über ffmpeg; bereits gemessene Titel werden übersprungen, die\n"
        "Ergebnisse werden zwischengespeichert). Schaltet 🔊 Lautstärke\n"
        "angleichen im Abspielmodus frei.",
    "One row per competition — each fills its own 📅 day deck on the\n"
    "Tournament-day tab; more than 8 competitions share decks (labeled\n"
    "round headers). All competitions share one no-repeat pool for the day "
    "(Paso Doble may repeat).":
        "Eine Zeile je Turnier — jedes füllt sein eigenes 📅 Tagesdeck im\n"
        "Reiter Turniertag; bei mehr als 8 Turnieren teilen sie sich Decks\n"
        "(mit beschrifteten Rundenüberschriften). Alle Turniere teilen sich einen "
        "Pool ohne Wiederholung für den Tag (Paso Doble darf sich wiederholen).",
    "Only change this if the sound gives you trouble: a title that\n"
    "won't play, or the short gap a pitch change costs — the two\n"
    "engines handle that differently. Takes effect on the next start.":
        "Ändere das nur, wenn der Ton Ärger macht: ein Titel, der nicht\n"
        "spielt, oder die kurze Lücke, die eine Tonhöhenänderung kostet —\n"
        "die beiden Maschinen gehen damit unterschiedlich um. Wirkt ab\n"
        "dem nächsten Start.",
    "Only the accent's own family of tints follows this colour.\n"
    "A red warning, a green proven mark and the popularity amber mean\n"
    "something, so they keep their hue.":
        "Nur die Tönungen der Akzentfarbe selbst folgen dieser Farbe.\n"
        "Eine rote Warnung, ein grünes Bewährt-Zeichen und das Bernstein\n"
        "der Beliebtheit bedeuten etwas und behalten deshalb ihren Ton.",
    "Planner only hides the tournament floor's playing panel;\n"
    "Player only hides everything that generates or checks a playlist.\n"
    "Nothing is removed — switching back brings it all straight back.":
        "Planer blendet nur den Abspielbereich für die Turnierfläche aus;\n"
        "Player blendet nur alles aus, was eine Playlist erzeugt oder\n"
        "prüft.\n"
        "Es wird nichts entfernt — ein Zurückschalten bringt alles sofort\n"
        "wieder.",
    "Playlists still build and play without it. These need it and stay "
    "unavailable:<ul><li>analysing the library — tempo, similar "
    "tracks</li><li>🔊 loudness levelling (EBU R128)</li><li>🔇 silence "
    "detection at the start and end of a track</li></ul>":
        "Playlists lassen sich auch ohne ffmpeg bauen und abspielen. Dies hier "
        "braucht es und bleibt nicht verfügbar:<ul><li>die Bibliothek analysieren "
        "— Tempo, ähnliche Titel</li><li>🔊 Lautheitsangleich (EBU R128)</li><li>🔇 "
        "Stilleerkennung am Anfang und Ende eines Titels</li></ul>",
    "Re-read every M3U and tournament music folder in the tournament\n"
    "playlist folder and rebuild the popularity / co-occurrence index from\n"
    "it — WITHOUT rescanning files or audio. Use after exporting a played\n"
    "tournament so it counts right away.":
        "Jede M3U und jeden Turnier-Musikordner im Turnier-Playlist-Ordner\n"
        "neu einlesen und den Index für Beliebtheit / gemeinsames Auftreten\n"
        "daraus neu aufbauen — OHNE Dateien oder Audio neu einzulesen.\n"
        "Nach dem Export eines gespielten Turniers benutzen, damit es\n"
        "sofort mitzählt.",
    "Remove cached rows for music files that no longer exist (features,\n"
    "embeddings, loudness, …) and compact the database file (VACUUM).\n"
    "Slow on a big library; refuses to run when the music drive looks\n"
    "unmounted so cached analysis can't be wiped by accident.":
        "Zwischengespeicherte Zeilen zu nicht mehr vorhandenen Musikdateien\n"
        "entfernen (Merkmale, Embeddings, Lautheit, …) und die Datenbank\n"
        "verdichten (VACUUM).\n"
        "Bei einer großen Bibliothek langsam; verweigert den Lauf, wenn das\n"
        "Musiklaufwerk nicht eingebunden scheint, damit die gespeicherte\n"
        "Analyse nicht versehentlich gelöscht wird.",
    "Run librosa on the favorites library's MP3 files not yet cached.\n"
    "Required for timbral similarity scoring; when everything is cached\n"
    "a click offers a full re-analysis (e.g. after a tempo-method change).":
        "librosa über die noch nicht zwischengespeicherten MP3-Dateien der\n"
        "Favoriten-Bibliothek laufen lassen.\n"
        "Nötig für die Bewertung der Timbre-Ähnlichkeit; ist alles\n"
        "gespeichert, bietet ein Klick eine vollständige Neuanalyse an\n"
        "(z. B. nach einem Wechsel der Tempomethode).",
    "Scan the whole repository and analyze any files not yet cached, using the\n"
    "fast librosa timbre+rhythm features (the default similarity method).\n"
    "Read-only; runs in the background and can be left to finish.":
        "Den gesamten Bestand einlesen und alle noch nicht gespeicherten Dateien "
        "analysieren, mit den\n"
        "schnellen librosa-Merkmalen für Timbre und Rhythmus (die Standardmethode "
        "für Ähnlichkeit).\n"
        "Nur lesend; läuft im Hintergrund und kann durchlaufen.",
    "Takes effect after restarting the app. If the sound stays away "
    "afterwards, switch back here — the setting is only read at start, so "
    "nothing else in the app depends on it.":
        "Wirkt nach einem Neustart der App. Bleibt der Ton danach weg, hier wieder "
        "zurückschalten — die Einstellung wird nur beim Start gelesen, sonst hängt "
        "nichts in der App daran.",
    "The 🐂 Paso Doble highlight stop is <i>switched off</i> by the 🏆 "
    "tournament set: its detection is not good enough yet to cut a competition "
    "Paso Doble on, and a heat stopped in the wrong bar is danced twice. It is "
    "not configurable here — the 🎉 party set leaves it wherever you set it on "
    "the Playing panel, and you can switch it back on there for a demo.":
        "Der 🐂 Höhepunkt-Stopp beim Paso Doble wird vom Set 🏆 Turnier "
        "<i>ausgeschaltet</i>: seine Erkennung ist noch nicht gut genug, um einen "
        "Turnier-Paso darauf zu schneiden, und eine im falschen Takt gestoppte "
        "Gruppe wird zweimal getanzt. Hier ist das nicht einstellbar — das Set "
        "🎉 Party lässt ihn so, wie du ihn im Abspielbereich gesetzt hast, und dort "
        "kannst du ihn für eine Vorführung wieder einschalten.",
    "Theme, accent and language are read when the app starts, so a change "
    "takes effect after a restart — you are asked once you save.":
        "Erscheinungsbild, Akzentfarbe und Sprache werden beim Start der App "
        "gelesen, eine Änderung wirkt also nach einem Neustart — du wirst nach dem "
        "Speichern gefragt.",
    "Keep the German dance and round names on an English screen "
    "(Langsamer Walzer, Vorrunde, Standardrunde 1 …)":
        "Deutsche Tanz- und Rundennamen auch in der englischen Oberfläche "
        "(Langsamer Walzer, Vorrunde, Standardrunde 1 …)",
    "On: the presenter screen and the recorded announcements are "
    "German too.\n"
    "Off: Slow Waltz, Round 1, Standard round 1 … — the playlists "
    "and exports keep the German words either way.":
        "An: Auch der Moderations-Bildschirm und die aufgenommenen Ansagen "
        "sind deutsch.\n"
        "Aus: Slow Waltz, Round 1, Standard round 1 … — Playlists und "
        "Exporte behalten die deutschen Begriffe in jedem Fall.",
    "Three switches that are set once and then never touched again,\n"
    "in the busiest column of the desk. Hidden they keep whatever they\n"
    "were set to — only the controls go away.":
        "Drei Schalter, die einmal gesetzt und dann nie wieder angefasst\n"
        "werden, in der vollsten Spalte des Pults. Ausgeblendet behalten\n"
        "sie, worauf sie gesetzt waren — nur die Bedienelemente\n"
        "verschwinden.",
    "You can change this later under ⚙ Settings → 📁 Paths & search.":
        "Das lässt sich später unter ⚙ Einstellungen → 📁 Pfade & Suche ändern.",
    "lower": "unten",
    "middle": "mittig",
    "upper": "oben",
    "⚠️  <b>ffmpeg is not installed on this computer.</b>":
        "⚠️  <b>ffmpeg ist auf diesem Rechner nicht installiert.</b>",
    "🌐  Global search — match dropped files against the whole repository "
    "(default: favorites library only)":
        "🌐  Globale Suche — hineingezogene Dateien gegen den gesamten Bestand "
        "abgleichen (Standard: nur die Favoriten-Bibliothek)",
    "🎙  Advanced voice controls — show '…with takt', '…with heat' and 🔈 Test "
    "under 'Announce next dance'":
        "🎙  Erweiterte Ansagesteuerung — „…mit Takt“, „…mit Gruppe“ und 🔈 Test "
        "unter „Nächsten Tanz ansagen“ zeigen",
    "🎧  Preview player — float a mini player (seek / skip / volume) over the "
    "deck when a ▶ button is clicked":
        "🎧  Vorhör-Player — beim Klick auf ▶ einen Mini-Player (Spulen / Springen "
        "/ Lautstärke) über dem Deck einblenden",
    "🐘 Heavy — AI models, needs the FULL build (or the requirements-full.txt "
    "extras)":
        "🐘 Schwer — KI-Modelle, braucht den VOLLEN Build (oder die Extras aus "
        "requirements-full.txt)",
    "🔇  Release the sound card between titles — takes away the hiss an onboard "
    "output puts on the PA while the app holds it open":
        "🔇  Die Soundkarte zwischen den Titeln freigeben — nimmt das Rauschen weg, "
        "das ein Onboard-Ausgang auf die Anlage legt, solange die App ihn offen "
        "hält",
    "🔕  Mute system sounds while the evening runs — no error ding or "
    "notification chime over the speakers":
        "🔕  Systemklänge stummschalten, solange der Abend läuft — kein "
        "Fehler-Ding und kein Benachrichtigungston über die Lautsprecher",
    "🐞  Send error reports — when the app hits an error, send its "
    "technical details to the developer":
        "🐞  Fehlerberichte senden — wenn in der App ein Fehler auftritt, "
        "gehen seine technischen Details an den Entwickler",
    "Sent: the error and where in the program it happened, the last\n"
    "log lines before it (they can name the title that was playing),\n"
    "the operating system and the app version.\n\n"
    "Not sent: your music, your playlists, your computer's name.\n"
    "Your user folder is cut out of every path.\n\n"
    "Off by default. Applies as soon as you save.":
        "Gesendet: der Fehler und wo im Programm er passiert ist, die letzten\n"
        "Logzeilen davor (sie können den laufenden Titel nennen),\n"
        "das Betriebssystem und die App-Version.\n\n"
        "Nicht gesendet: deine Musik, deine Playlisten, der Name deines Computers.\n"
        "Dein Benutzerordner wird aus jedem Pfad herausgeschnitten.\n\n"
        "Standardmäßig aus. Gilt, sobald du speicherst.",
    "Error reports": "Fehlerberichte",
    "Send error reports to the developer?":
        "Fehlerberichte an den Entwickler senden?",
    "When the app hits an error, it can send the technical details,\n"
    "so the error gets fixed.\n\n"
    "Sent: the error and where in the program it happened, the last\n"
    "log lines before it (they can name the title that was playing),\n"
    "the operating system and the app version.\n\n"
    "Not sent: your music, your playlists, your computer's name.\n"
    "Your user folder is cut out of every path.\n\n"
    "You can change this at any time under ⚙ Settings → 📁 Paths & search.":
        "Wenn in der App ein Fehler auftritt, kann sie die technischen Details\n"
        "senden, damit der Fehler behoben wird.\n\n"
        "Gesendet: der Fehler und wo im Programm er passiert ist, die letzten\n"
        "Logzeilen davor (sie können den laufenden Titel nennen),\n"
        "das Betriebssystem und die App-Version.\n\n"
        "Nicht gesendet: deine Musik, deine Playlisten, der Name deines Computers.\n"
        "Dein Benutzerordner wird aus jedem Pfad herausgeschnitten.\n\n"
        "Das kannst du jederzeit unter ⚙ Einstellungen → 📁 Pfade & Suche ändern.",
    "Send reports": "Berichte senden",
    "Don't send": "Nicht senden",
    "The music and the computer share the one sound card, so every\n"
    "sound the system makes goes out over the PA too.\n\n"
    "Muted all through Playing mode and whenever something plays,\n"
    "put back when you return to planning or close the app.\n"
    "Windows: the System Sounds slider of the volume mixer.\n"
    "macOS: the alert volume. Linux (GNOME): event sounds.":
        "Musik und Computer teilen sich die eine Soundkarte, also geht\n"
        "jeder Klang des Systems ebenfalls über die Anlage.\n\n"
        "Stumm im ganzen Spielmodus und immer, wenn etwas läuft,\n"
        "zurückgestellt beim Wechsel ins Planen oder beim Schließen.\n"
        "Windows: der Regler „Systemsounds“ im Lautstärkemixer.\n"
        "macOS: die Warntonlautstärke. Linux (GNOME): Ereignisklänge.",
    "🧭 Fix paths tries the Referenzpfad first and then these folders,\n"
    "in order, cutting the foreign path down until what is left lands on a\n"
    "real file underneath one of them. A path is only ever rewritten to a\n"
    "file that is actually there.":
        "🧭 Pfade korrigieren versucht zuerst den Referenzpfad und dann\n"
        "diese Ordner der Reihe nach, wobei der fremde Pfad gekürzt wird,\n"
        "bis der Rest unter einem von ihnen auf einer echten Datei landet.\n"
        "Ein Pfad wird nur je auf eine Datei umgeschrieben, die wirklich\n"
        "da ist.",
    "Drag <b>.m3u playlists</b> here (audio files work too) to check whether "
    "any of their tracks are duplicates of <b>each other</b> — across the "
    "dropped playlists, by audio content, else title.":
        "Ziehe <b>.m3u-Playlists</b> hierher (Audiodateien gehen auch), um zu "
        "prüfen, ob sich Titel <b>untereinander</b> doppeln — über die "
        "hineingezogenen Playlists hinweg, nach Audioinhalt, sonst nach Titel.",
    "Drop a <b>reference playlist</b> (.m3u) and the <b>tournament files</b> "
    "(.m3u playlists or audio) below. The reference is compared against the "
    "tournament tracks and every <b>hard duplicate</b> (byte-identical audio) "
    "is removed; the leftover <b>unused</b> tracks are exported to a new .m3u. "
    "<span style='color:#666'>Paso Doble is excluded from the comparison and "
    "always kept.</span>":
        "Lege unten eine <b>Referenz-Playlist</b> (.m3u) und die "
        "<b>Turnierdateien</b> (.m3u-Playlists oder Audio) ab. Die Referenz wird "
        "mit den Turniertiteln verglichen und jedes <b>harte Duplikat</b> "
        "(byteweise identisches Audio) entfernt; die übrigen <b>ungenutzten</b> "
        "Titel werden in eine neue .m3u exportiert. <span style='color:#666'>Paso "
        "Doble bleibt vom Vergleich ausgenommen und immer erhalten.</span>",
    "Duplicate songs across your open playlist(s), in playlist order.<br><span "
    "style='color:#666'>🟰 <b>Exact</b> = identical audio. ≈ <b>Similar</b> = "
    "same title, a different recording. Keep the ones you want; switch the "
    "others to <b>Replace</b> and pick a track for each, or to <b>Remove</b>.</span>":
        "Doppelte Titel über deine offenen Playlists hinweg, in der Reihenfolge "
        "der Playlist.<br><span style='color:#666'>🟰 <b>Exakt</b> = identisches "
        "Audio. ≈ <b>Ähnlich</b> = derselbe Titel, eine andere Aufnahme. Behalte "
        "die gewünschten; stelle die übrigen auf <b>Ersetzen</b> und wähle je "
        "einen Titel dafür, oder auf <b>Entfernen</b>.</span>",
    "Every copy of this song is already controlled by the within-playlist\n"
    "section above, so there is nothing left to resolve on this row.":
        "Jede Kopie dieses Titels wird bereits vom Abschnitt innerhalb der\n"
        "Playlist weiter oben gesteuert, in dieser Zeile bleibt also nichts\n"
        "mehr aufzulösen.",
    "Export unused tracks": "Ungenutzte Titel exportieren",
    "No hard duplicates of the tournament files were found in the reference — "
    "nothing to remove.":
        "In der Referenz wurden keine harten Duplikate der Turnierdateien gefunden "
        "— es gibt nichts zu entfernen.",
    "Nothing to change — no occurrence is set to Replace or Remove.":
        "Nichts zu ändern — kein Vorkommen steht auf Ersetzen oder Entfernen.",
    "Reference base": "Referenzgrundlage",
    "Resolve duplicates": "Duplikate auflösen",
    "Sort the exported tracks by dance?\n"
    "\n"
    "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)":
        "Die exportierten Titel nach Tanz sortieren?\n"
        "\n"
        "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)",
    "The reference base must be a single .m3u playlist.":
        "Die Referenzgrundlage muss eine einzelne .m3u-Playlist sein.",
    "This list holds some titles more than once.<br><span "
    "style='color:#666'>For each title, pick the file to keep — the others are "
    "removed. <b>Keep all</b> leaves that title alone.</span>":
        "Diese Liste enthält manche Titel mehrfach.<br><span "
        "style='color:#666'>Wähle je Titel die Datei, die bleiben soll — die "
        "anderen werden entfernt. <b>Alle behalten</b> lässt diesen Titel "
        "unangetastet.</span>",
    "Browse by library category — 🏆 Tournament hides the non-tournament\n"
    "folders (anthems, background, wrong-tempo, duplicates, seasonal);\n"
    "pick a category to look only at those (handy for parties).":
        "Nach Bibliothekskategorie stöbern — 🏆 Turnier blendet die\n"
        "turnierfremden Ordner aus (Hymnen, Hintergrund, falsches Tempo,\n"
        "Duplikate, Saisonales); wähle eine Kategorie, um nur diese zu\n"
        "sehen (praktisch für Partys).",
    "Drag a track onto a deck or wishlist to use it.\n"
    "▶ to preview · double-click to open in your external player\n"
    "· right-click for more.":
        "Ziehe einen Titel auf ein Deck oder eine Wunschliste, um ihn zu\n"
        "benutzen.\n"
        "▶ zum Vorhören · Doppelklick öffnet ihn im externen Player\n"
        "· Rechtsklick für mehr.",
    "Only tracks suited for this starting class\n"
    "(tracks without a class tag are always shown)":
        "Nur Titel, die zu dieser Startklasse passen\n"
        "(Titel ohne Klassenangabe werden immer gezeigt)",
    "Only tracks whose file was created in the library that\n"
    "recently. Combine with ✦ Never played to see what you\n"
    "copied in but have never actually used.":
        "Nur Titel, deren Datei so kurz zuvor in der Bibliothek angelegt\n"
        "wurde. Zusammen mit ✦ Nie gespielt zeigt das, was du\n"
        "hineinkopiert, aber nie wirklich benutzt hast.",
    "Show only tracks not already used in any open playlist deck —\n"
    "handy for finding fresh music while building rounds.":
        "Nur Titel zeigen, die in keinem offenen Playlist-Deck schon\n"
        "benutzt werden — praktisch, um beim Rundenbau frische Musik zu\n"
        "finden.",
    "Substring of the title, the artist, or a comment marker\n"
    "(vocal_f, classic, eintanzen, …)":
        "Teil des Titels, des Interpreten oder einer Kommentarmarkierung\n"
        "(vocal_f, classic, eintanzen, …)",
    "proven": "bewährt",
    "rare": "selten",
    "Audio analysis unavailable": "Audio-Analyse nicht verfügbar",
    "Audio cache not ready yet — try again shortly.":
        "Der Audio-Zwischenspeicher ist noch nicht bereit — gleich noch einmal "
        "versuchen.",
    "Build ALL caches": "ALLE Caches aufbauen",
    "Build all caches": "Alle Caches aufbauen",
    "Analyze loudness": "Lautheit analysieren",
    "Analyze vocals (Demucs)": "Gesang analysieren (Demucs)",
    "No Paso Doble tracks in the library.":
        "Keine Paso-Doble-Titel in der Bibliothek.",
    "Probe silences": "Stillen prüfen",
    "Re-analyze Audio": "Audio neu analysieren",
    "Redo the 🐂 auto-detection for the whole library — for after the\n"
    "detector changed. Hand-set 🎯 marks are kept untouched.":
        "Die 🐂 automatische Erkennung für die ganze Bibliothek neu laufen\n"
        "lassen — für den Fall, dass sich der Erkenner geändert hat. Von\n"
        "Hand gesetzte 🎯 Marken bleiben unangetastet.",
    "The music library is not loaded yet.":
        "Die Musikbibliothek ist noch nicht geladen.",
    "ffmpeg was not found (neither on PATH nor the copy bundled\n"
    "with the project) — loudness cannot be measured.":
        "ffmpeg wurde nicht gefunden (weder im PATH noch die mit dem\n"
        "Projekt gelieferte Kopie) — die Lautheit lässt sich nicht messen.",
    "ffmpeg was not found (neither on PATH nor the copy bundled\n"
    "with the project) — silences cannot be probed.":
        "ffmpeg wurde nicht gefunden (weder im PATH noch die mit dem\n"
        "Projekt gelieferte Kopie) — die Stillen lassen sich nicht prüfen.",
    "Clear playlists": "Playlists leeren",
    "Clear tournament day": "Turniertag leeren",
    "Close tournament day": "Turniertag schließen",
    "Competition name (empty = default):": "Turniername (leer = Standard):",
    "Competition name:": "Turniername:",
    "Free order": "Freie Reihenfolge",
    "None of these tracks says which dance it is, so there is no grid to build "
    "from them — the list stays a free running order.":
        "Keiner dieser Titel sagt, welcher Tanz er ist, also lässt sich daraus "
        "kein Raster bauen — die Liste bleibt eine freie Reihenfolge.",
    "New tournament day": "Neuer Turniertag",
    "Rename tournament day": "Turniertag umbenennen",
    "Shuffle — put the same titles in a fresh order,\n"
    "as if the party list were built again from scratch.":
        "Mischen — dieselben Titel in eine neue Reihenfolge bringen,\n"
        "als würde die Partyliste noch einmal von vorn gebaut.",
    "Total play time of this playlist\n"
    "(↳ backup rows not counted — they only play as stand-ins)\n"
    "Click ▸ for the songs per dance":
        "Gesamte Spielzeit dieser Playlist\n"
        "(↳ Ersatzzeilen zählen nicht mit — sie spielen nur als Vertretung)\n"
        "Klick auf ▸ zeigt die Titel je Tanz",
    "Every similar track is already in an open playlist.":
        "Jeder ähnliche Titel steht schon in einer offenen Playlist.",
    "No similar tracks found — the song may not be audio-analyzed yet.":
        "Keine ähnlichen Titel gefunden — der Titel ist vielleicht noch nicht "
        "audio-analysiert.",
    "Replace duplicate": "Duplikat ersetzen",
    "Audio index": "Audio-Index",
    "Audio index ready": "Audio-Index fertig",
    "Build audio index": "Audio-Index bauen",
    "Embedding index error": "Fehler im Embedding-Index",
    "Favorites library isn't loaded yet.":
        "Die Favoriten-Bibliothek ist noch nicht geladen.",
    "The whole-repository library isn't loaded yet. Drop a file (or build the "
    "librosa index over the repository) once to load it, then retry.":
        "Die Bibliothek des Gesamtbestands ist noch nicht geladen. Ziehe einmal "
        "eine Datei hinein (oder baue den librosa-Index über den Bestand), um sie "
        "zu laden, und versuche es dann erneut.",
    "Not on the Referenzpfad": "Nicht im Referenzpfad",
    "Save Error": "Speicherfehler",
    "Save as M3U": "Als M3U speichern",
    "This deck is empty.": "Dieses Deck ist leer.",
    "Fold this playlist to a tab —\n"
    "the other open playlists get its space.":
        "Diese Playlist auf einen Reiter einklappen —\n"
        "ihren Platz bekommen die anderen offenen Playlists.",
    "AI playlist": "KI-Playlist",
    "AI playlist failed": "KI-Playlist fehlgeschlagen",
    "All picks are TSO-conform (T24 Rumba / T58-59 Paso allowed, like the "
    "normal playlist).":
        "Alle Titel sind TSO-konform (T24 Rumba / T58-59 Paso erlaubt, wie bei der "
        "normalen Playlist).",
    "Cap the party-list length — handy when drawing from the whole library.\n"
    "The round it lands in is played out, so the list can run a title or two "
    "over.\n"
    "0 = No limit (use every eligible track).":
        "Die Länge der Partyliste begrenzen — praktisch, wenn aus der ganzen "
        "Bibliothek gezogen wird.\n"
        "Die Runde, in die sie fällt, wird zu Ende gespielt — die Liste kann "
        "also ein, zwei Titel darüber hinausgehen.\n"
        "0 = Keine Grenze (jeden geeigneten Titel benutzen).",
    "Choose an .m3u file first.": "Wähle zuerst eine .m3u-Datei.",
    "Dances come in alternating 3-dance rounds (not competition rounds).":
        "Die Tänze kommen in abwechselnden 3-Tanz-Runden (keine Turnierrunden).",
    "Day plan": "Tagesplan",
    "Draw from your library, exactly like the left panel's Favorites mode.":
        "Aus deiner Bibliothek ziehen, genau wie im Favoriten-Modus des linken "
        "Bereichs.",
    "Draw only from the tracks currently parked in your open ⭐ wishlists.":
        "Nur aus den Titeln ziehen, die gerade in deinen offenen ⭐ Wunschlisten "
        "liegen.",
    "Eintanzen Error": "Eintanzen-Fehler",
    "Enter a valid round pattern (e.g. 6-3-2-1).":
        "Gib ein gültiges Rundenschema ein (z. B. 6-3-2-1).",
    "Generate Error": "Fehler beim Erzeugen",
    "History Error": "Verlaufsfehler",
    "Library gaps": "Lücken der Bibliothek",
    "No Competition": "Kein Turnier",
    "No Dances": "Keine Tänze",
    "No Matches": "Keine Treffer",
    "No Rounds": "Keine Runden",
    "No Theme": "Kein Thema",
    "No candidate tracks for those settings — check the dances, the\n"
    "start class and that the library actually holds those tempos.":
        "Keine Titel für diese Einstellungen — prüfe die Tänze, die\n"
        "Startklasse und ob die Bibliothek diese Tempi überhaupt hat.",
    "No matching tracks for the chosen options — check the class, the source "
    "and that the library / .m3u actually has those dances.":
        "Keine passenden Titel für die gewählten Optionen — prüfe die Startklasse, "
        "die Quelle und ob die Bibliothek / .m3u diese Tänze überhaupt hat.",
    "No resolvable tracks in that .m3u file.":
        "In dieser .m3u-Datei ließ sich kein Titel auflösen.",
    "Paste a schedule and click 'Parse schedule', then pick a competition.":
        "Füge einen Zeitplan ein, klicke „Zeitplan lesen“ und wähle dann ein "
        "Turnier.",
    "Pick at least Standard or Latin dances.":
        "Wähle mindestens Standard- oder Lateintänze.",
    "Please select a theme.": "Bitte wähle ein Thema.",
    "Please select at least one dance.": "Bitte wähle mindestens einen Tanz.",
    "Replace day plan": "Tagesplan ersetzen",
    "Share of slots that lean FRESH (least-played) instead of proven "
    "favourites.\n"
    "Higher = more never/barely-played tracks — at 100 % the list is\n"
    "built from the least-played tracks upward (not just the few with zero "
    "plays).":
        "Anteil der Plätze, die zu FRISCH (am wenigsten gespielt) neigen statt zu "
        "bewährten Favoriten.\n"
        "Höher = mehr nie oder kaum gespielte Titel — bei 100 % wird die Liste\n"
        "von den am wenigsten gespielten Titeln aufwärts gebaut (nicht nur aus den "
        "wenigen ohne jedes Spiel).",
    "The Tournament-day tab still holds an earlier day plan.\n"
    "\n"
    "Replace it with the new one?":
        "Im Reiter Turniertag liegt noch ein früherer Tagesplan.\n"
        "\n"
        "Durch den neuen ersetzen?",
    "The library is still loading — try again in a moment.":
        "Die Bibliothek lädt noch — versuche es gleich noch einmal.",
    "The model answered, but none of its picks matched the\n"
    "catalog. Try again — or lower the round count.":
        "Das Modell hat geantwortet, aber keiner seiner Titel passte zum\n"
        "Katalog. Versuche es erneut — oder senke die Rundenzahl.",
    "The model answered, but none of its picks matched the catalog.":
        "Das Modell hat geantwortet, aber keiner seiner Titel passte zum Katalog.",
    "The selected competition has no valid heat counts.":
        "Das gewählte Turnier hat keine gültigen Gruppenzahlen.",
    "The wish list is empty — write the titles you want, one\n"
    "per line or a column per dance.":
        "Die Wunschliste ist leer — schreibe die gewünschten Titel hinein,\n"
        "einen je Zeile oder eine Spalte je Tanz.",
    "Theme Error": "Themenfehler",
    "Upper limit. The list stops here or when the TSO-conform pool runs dry — "
    "whichever comes first.":
        "Obergrenze. Die Liste endet hier oder wenn der TSO-konforme Pool leer ist "
        "— was zuerst eintritt.",
    "Your open wishlists are empty — park some tracks there first.":
        "Deine offenen Wunschlisten sind leer — lege dort zuerst ein paar Titel ab.",
    "🆕 This competition has no saved work yet — press ⚡ Generate from History "
    "to seed it":
        "🆕 Zu diesem Turnier ist noch nichts gespeichert — drücke ⚡ Aus Verlauf "
        "erzeugen, um es anzulegen",
    "🏆  Eintanzen for a tournament class (round-robin through the class's "
    "dances)":
        "🏆  Eintanzen für eine Startgruppe (Rundlauf durch die Tänze der Gruppe)",
    "Analysis Error": "Analysefehler",
    "Build librosa index": "librosa-Index bauen",
    "Clean up database": "Datenbank aufräumen",
    "Could not start a new instance — please start the app again yourself.":
        "Es ließ sich keine neue Instanz starten — bitte starte die App selbst "
        "noch einmal.",
    "Finding similar tracks for a file needs librosa + ffmpeg.\n"
    "Install them, then retry.":
        "Ähnliche Titel zu einer Datei zu finden braucht librosa + ffmpeg.\n"
        "Installiere beides und versuche es dann erneut.",
    "Global Index Error": "Fehler im globalen Index",
    "Global search": "Globale Suche",
    "Library Load Error": "Fehler beim Laden der Bibliothek",
    "Re-learn playlists": "Playlists neu lernen",
    "Set a valid music repository folder first.":
        "Lege zuerst einen gültigen Ordner für den Musikbestand fest.",
    "Set a valid music repository folder in ⚙ Settings first.":
        "Lege zuerst unter ⚙ Einstellungen einen gültigen Ordner für den "
        "Musikbestand fest.",
    "Settings saved": "Einstellungen gespeichert",
    "Similar Tracks": "Ähnliche Titel",
    "The favorites library path changed.\n"
    "Restart the app to load the new library.":
        "Der Pfad der Favoriten-Bibliothek hat sich geändert.\n"
        "Starte die App neu, um die neue Bibliothek zu laden.",
    "Couldn't detect any danceable tracks in that playlist.":
        "In dieser Playlist ließ sich kein tanzbarer Titel erkennen.",
    "Import Error": "Importfehler",
    "Import M3U": "M3U importieren",
    "Not enough free playlists": "Nicht genug freie Playlists",
    "Nothing imported": "Nichts importiert",
    "Remove from the playlist(s) — the slot stays empty (Ctrl+Z undoes)":
        "Aus den Playlists entfernen — der Platz bleibt leer (Strg+Z macht es "
        "rückgängig)",
    "Drop <b>.m3u playlists</b> here — only playlists carry track paths to fix.":
        "Lege hier <b>.m3u-Playlists</b> ab — nur Playlists tragen Titelpfade, die "
        "sich korrigieren lassen.",
    "Fix & overwrite": "Korrigieren & überschreiben",
    "Fix paths": "Pfade korrigieren",
    "No track paths that can be re-rooted under the search folders.":
        "Keine Titelpfade, die sich unter den Suchordnern neu einhängen lassen.",
    "Set a Referenzpfad or a search folder in Settings before fixing dropped "
    "playlists.":
        "Lege in den Einstellungen einen Referenzpfad oder einen Suchordner fest, "
        "bevor du hineingezogene Playlists korrigierst.",
    "⚠  No <b>search folder</b> set — open Settings and name the base "
    "folder(s) the music lives in on this PC.":
        "⚠  Kein <b>Suchordner</b> gesetzt — öffne die Einstellungen und nenne die "
        "Basisordner, in denen die Musik auf diesem PC liegt.",
    "Clear all playlists": "Alle Playlists leeren",
    "Nothing to print — no songs found.":
        "Nichts zu drucken — keine Titel gefunden.",
    "Print playlist": "Playlist drucken",
    "Add folder": "Ordner hinzufügen",
    "No alternative Eintanzen track found.":
        "Kein anderer Eintanz-Titel gefunden.",
    "No alternative song found.": "Kein anderer Titel gefunden.",
    "Re-roll this song — best timbre match first  (Ctrl+R / Ctrl+N)":
        "Diesen Titel neu würfeln — die beste Timbre-Übereinstimmung zuerst  (Strg+R "
        "/ Strg+N)",
    # The ↺ button's other three states, and the ⚠ a dead file shows in the
    # title cell as well. The dance name filling %s stays as it is — it is a
    # dance, not chrome.
    "Swap with a %s from the end of the list — a "
    "leftover that fits no round first, else one from "
    "the last third  (Ctrl+R / Ctrl+N)":
        "Gegen einen %s vom Ende der Liste tauschen — zuerst einen Rest, der "
        "in keine Runde passt, sonst einen aus dem letzten Drittel  (Strg+R / "
        "Strg+N)",
    "↺ click to swap it with a %s from the end "
    "of the list":
        "↺ klicken, um ihn gegen einen %s vom Ende der Liste zu tauschen",
    "↺ click to re-roll a replacement":
        "↺ klicken, um einen Ersatz neu zu würfeln",
    "🔁 Marked for potential replace  "
    "(Ctrl+M to toggle)":
        "🔁 Zum möglichen Austausch markiert  (Strg+M schaltet um)",
    "⚠ File not found on disk:\n%s":
        "⚠ Datei nicht auf der Platte gefunden:\n%s",
    "Regenerate": "Neu erzeugen",
    "Regenerate Error": "Fehler beim Neuerzeugen",
    "Track length (m:ss)\n"
    "orange = shorter than the configured play length, or 5 s or more\n"
    "of stillness at an edge that the player skips (the cell's own\n"
    "tooltip says which, and how long it really plays)":
        "Titellänge (m:ss)\n"
        "orange = kürzer als die eingestellte Spielzeit, oder 5 s und mehr\n"
        "Stille an einem Rand, die der Player überspringt (der Tooltip der\n"
        "Zelle sagt, was davon, und wie lange er wirklich spielt)",
    "Wishlist": "Wunschliste",
    "Rating — click a star to set it, the last lit one again to clear it.\n"
    "Kept in the app's database; the MP3 itself is not changed.":
        "Bewertung — ein Klick auf einen Stern setzt sie, ein erneuter Klick\n"
        "auf den letzten leuchtenden löscht sie.\n"
        "Gespeichert in der Datenbank der App; die MP3 selbst bleibt unverändert.",
    "≈  timbral similarity to round anchor\n"
    "    (only shown after running Audio Analysis)\n"
    "[D,C,…]  class tags from MP3 COMM field":
        "≈  Timbre-Ähnlichkeit zum Anker der Runde\n"
        "    (erst nach einer Audio-Analyse sichtbar)\n"
        "[D,C,…]  Klassenangaben aus dem COMM-Feld der MP3",
    "Audio cache/library not available for this search.":
        "Audio-Zwischenspeicher / Bibliothek stehen für diese Suche nicht zur "
        "Verfügung.",
    "Embedding error": "Embedding-Fehler",
    "Gaussian/KL: per-song MFCC distribution (mean+covariance)\n"
    "compared by symmetric KL — the Mandel-Ellis model, like the old Java\n"
    "app. Cleanest sound-alike ranking; genuine matches read ≳ 80 %.\n"
    "Librosa: fast hand-crafted timbre+rhythm vector (cosine).\n"
    "OpenL3: a pretrained neural music embedding — often closer to\n"
    "perceived 'sounds-alike'. Needs:  pip install openl3 tensorflow\n"
    "Chroma cover/remix: matches MELODY/harmony, not timbre — finds\n"
    "remixes & covers of the same tune even with a different sound,\n"
    "key or tempo. librosa only; build its index once like the others.\n"
    "Combined (default): where a title ranks by Gaussian/KL, librosa and chroma,\n"
    "averaged — the ones all three rank high come first.":
        "Gauß/KL: die MFCC-Verteilung je Titel (Mittelwert +\n"
        "Kovarianz), verglichen über symmetrisches KL — das Mandel-Ellis-Modell,\n"
        "wie in der alten Java-App. Die sauberste Rangfolge für Klangzwillinge;\n"
        "echte Treffer liegen bei ≳ 80 %.\n"
        "Librosa: schneller, von Hand gebauter Vektor aus Timbre und Rhythmus\n"
        "(Kosinus).\n"
        "OpenL3: ein vortrainiertes neuronales Musik-Embedding — oft näher am\n"
        "empfundenen „klingt ähnlich“. Braucht:  pip install openl3 tensorflow\n"
        "Chroma Cover/Remix: vergleicht MELODIE und Harmonie statt Timbre —\n"
        "findet Remixe und Coverversionen desselben Stücks auch bei anderem\n"
        "Klang, anderer Tonart oder anderem Tempo. Nur mit librosa; den Index\n"
        "einmal bauen wie bei den anderen.\n"
        "Kombiniert (Standard): der Mittelwert, wie weit oben ein Titel bei Gauß/KL,\n"
        "librosa und Chroma steht — die, die alle drei hoch einstufen, kommen\n"
        "zuerst.",
    "Off: sound-alike tracks (audio timbre).\n"
    "On: tracks that keep appearing in the same old playlists as this one.":
        "Aus: klanglich ähnliche Titel (Audio-Timbre).\n"
        "An: Titel, die immer wieder in denselben alten Playlists auftauchen\n"
        "wie dieser.",
    "Replace the duplicate with the selected track (Enter, or double-click a "
    "row)":
        "Das Duplikat durch den gewählten Titel ersetzen (Eingabe oder Doppelklick "
        "auf eine Zeile)",
    "Several copies of a song often exist under slightly different names\n"
    "(e.g. '… DJ Ice', 'jive(43) - Bim Bam', '16 Bim Bam'). When on, only the\n"
    "first copy of each song title is shown.":
        "Oft gibt es von einem Titel mehrere Kopien unter leicht abweichenden\n"
        "Namen (z. B. „… DJ Ice“, „jive(43) - Bim Bam“, „16 Bim Bam“). Wenn an,\n"
        "wird je Titelname nur die erste Kopie gezeigt.",
    "Show only tracks considered instrumental: an explicit 'instr' tag /\n"
    "'(Instr.)' filename marker, a Demucs-measured vocal share (🎙️ Analyze\n"
    "vocals), or the learned audio probability. Unknown tracks count as\n"
    "vocal, so they are hidden while this is on.":
        "Nur Titel zeigen, die als instrumental gelten: ein ausdrückliches\n"
        "„instr“-Tag / die Markierung „(Instr.)“ im Dateinamen, ein von Demucs\n"
        "gemessener Gesangsanteil (🎙️ Gesang analysieren) oder die\n"
        "gelernte Audio-Wahrscheinlichkeit. Unbekannte Titel zählen als\n"
        "gesungen und bleiben deshalb ausgeblendet, solange das an ist.",
    "Space: play / stop the selected track\n"
    "Ctrl + ← / → : seek 30 s back / forward":
        "Leertaste: den gewählten Titel abspielen / stoppen\n"
        "Strg + ← / → : 30 s zurück / vor springen",
    "This track isn't in any of your old playlists yet — nothing to learn "
    "from. Switch the toggle off for sound-alike tracks.":
        "Dieser Titel steht in keiner deiner alten Playlists — daraus lässt sich "
        "nichts lernen. Schalte den Schalter aus, um klanglich ähnliche Titel zu "
        "sehen.",
    "🧹  Hide duplicate copies (same song, ignoring DJ / dance / BPM tags)":
        "🧹  Doppelte Kopien ausblenden (derselbe Titel, ohne Rücksicht auf DJ- / "
        "Tanz- / BPM-Angaben)",
    "Clear playlist": "Playlist leeren",
    "Clear wishlist": "Wunschliste leeren",
    "Find in list": "In der Liste suchen",
    "Find planned before": "Frühere Planungen finden",
    "Find title:": "Titel suchen:",
    "No similar tracks found (audio features may be missing).":
        "Keine ähnlichen Titel gefunden (vielleicht fehlen die Audio-Merkmale).",
    "Select exactly two titles of the same dance to swap them.":
        "Wähle genau zwei Titel desselben Tanzes, um sie zu tauschen.",
    "Swap titles": "Titel tauschen",
    "Already planned": "Schon geplant",
    "Different dance": "Anderer Tanz",
    "Move Error": "Fehler beim Verschieben",
    "Move track": "Titel verschieben",
    "Replace Error": "Fehler beim Ersetzen",
    "Different style": "Andere Sektion",
    "Load playlist": "Playlist laden",
    "Name (competition, day, tournament):":
        "Name (Turnier, Tag, Veranstaltung):",
    "New folder": "Neuer Ordner",
    "Remove": "Entfernen",
    "Remove this song from its slot? The slot stays empty.":
        "Diesen Titel von seinem Platz entfernen? Der Platz bleibt frei.",
    "Remove %d songs from their slots? The slots stay empty.":
        "%d Titel von ihren Plätzen entfernen? Die Plätze bleiben frei.",
    "Remove this song from the running order?":
        "Diesen Titel aus dem Ablauf entfernen?",
    "Remove %d songs from the running order?":
        "%d Titel aus dem Ablauf entfernen?",
    "Rename": "Umbenennen",
    "Songs and total play time of the selected playlist\n"
    "(tracks this library doesn't know count, but add no time)":
        "Titel und gesamte Spielzeit der gewählten Playlist\n"
        "(Titel, die diese Bibliothek nicht kennt, zählen mit, bringen aber\n"
        "keine Zeit ein)",
    "The playlists filed in the selected folder, one slot each.\n"
    "Drag a slot onto a deck to load that round · double-click it to\n"
    "load it onto the focused deck · right-click to rename, remove or\n"
    "read its tracks.":
        "Die im gewählten Ordner abgelegten Playlists, je ein Platz.\n"
        "Ziehe einen Platz auf ein Deck, um diese Runde zu laden · Doppelklick\n"
        "lädt sie auf das fokussierte Deck · Rechtsklick zum Umbenennen,\n"
        "Entfernen oder Einlesen ihrer Titel.",
    "The tracks of the selected playlist, in playing order.\n"
    "▶ or Space previews · drag them onto a deck or the player list ·\n"
    "double-click to open in your external player.":
        "Die Titel der gewählten Playlist, in Spielreihenfolge.\n"
        "▶ oder Leertaste hört vor · ziehe sie auf ein Deck oder die Playerliste ·\n"
        "Doppelklick öffnet sie im externen Player.",
    "Your competitions, days and tournaments — folders are labels,\n"
    "the 🎵 entries point at .m3u files wherever they lie.\n"
    "\n"
    "Drop .m3u files or a whole folder in from Explorer · pick a folder\n"
    "to lay its playlists out as slots on the right · drag a slot onto\n"
    "a deck to load the round · double-click it to load it onto the\n"
    "focused deck.":
        "Deine Turniere, Tage und Veranstaltungen — Ordner sind nur Etiketten,\n"
        "die 🎵 Einträge zeigen auf .m3u-Dateien, wo immer sie liegen.\n"
        "\n"
        "Ziehe .m3u-Dateien oder einen ganzen Ordner aus dem Explorer herein ·\n"
        "wähle einen Ordner, um seine Playlists rechts als Plätze auszulegen ·\n"
        "ziehe einen Platz auf ein Deck, um die Runde zu laden · Doppelklick\n"
        "lädt sie auf das fokussierte Deck.",
    "📂  (not in a folder)": "📂  (in keinem Ordner)",
    "Party play time, songs at full length with no pause.\n"
    "The count simulates the party generator with your library's\n"
    "track lengths per dance (3.5 min where none are known).":
        "Spielzeit der Party, Titel in voller Länge ohne Pause.\n"
        "Die Zahl bildet den Party-Generator mit den Titellängen deiner\n"
        "Bibliothek je Tanz nach (3,5 min, wo keine bekannt sind).",
    "Per dance: songs to have ready — enough for 9 of 10 generated lists.":
        "Je Tanz: Titel, die bereitliegen sollten — genug für 9 von 10 erzeugten "
        "Listen.",
    "A key given to a pad follows it wherever it is moved and works\n"
    "from any page. Empty = that pad answers to its slot's key.":
        "Eine Taste, die einem Pad gegeben wird, folgt ihm, wohin es auch\n"
        "verschoben wird, und wirkt von jeder Seite aus. Leer = das Pad\n"
        "hört auf die Taste seines Platzes.",
    "Export cartwall": "Cartwall exportieren",
    "How long a pad takes to let go when it is tapped again\n"
    "or ⏹ stops the wall. A pad can override this in its own settings.":
        "Wie lange ein Pad zum Ausblenden braucht, wenn es erneut angetippt\n"
        "wird oder ⏹ die Wand stoppt. Ein Pad kann das in seinen eigenen\n"
        "Einstellungen übergehen.",
    "Import cartwall": "Cartwall importieren",
    "Pads per page. Making the grid smaller never loses a pad —\n"
    "whatever no longer fits moves to the first free slot.":
        "Pads je Seite. Ein kleineres Raster verliert nie ein Pad —\n"
        "was nicht mehr passt, rückt auf den ersten freien Platz.",
    "Page name:": "Seitenname:",
    "Play this pad over and over until it is stopped —\n"
    "for a background bed under a ceremony.":
        "Dieses Pad immer wieder abspielen, bis es gestoppt wird —\n"
        "für einen Klangteppich unter einer Zeremonie.",
    "Remove page": "Seite entfernen",
    "Rename page": "Seite umbenennen",
    "Snap the wall back into the main window.\n"
    "It returns to the edge it was last docked at.":
        "Die Wand zurück in das Hauptfenster holen.\n"
        "Sie kehrt an den Rand zurück, an dem sie zuletzt angedockt war.",
    "That file is not a cartwall this version can read.":
        "Diese Datei ist keine Cartwall, die diese Version lesen kann.",
    "The key fires whichever pad sits in that slot on the page you are\n"
    "looking at, so the same finger hits the same corner on every page.":
        "Die Taste löst das Pad aus, das auf der gerade sichtbaren Seite\n"
        "an diesem Platz liegt — derselbe Finger trifft so auf jeder Seite\n"
        "dieselbe Ecke.",
    "No pause started — enable auto-advance and have a next song queued.":
        "Keine Pause gestartet — schalte den Autovorlauf ein und sorge für einen "
        "nächsten Titel in der Warteschlange.",
    "⏹ The playing title is no longer in its deck — the music was stopped.":
        "⏹ Der laufende Titel ist nicht mehr in seinem Deck — die Musik wurde "
        "gestoppt.",
    "✏️ Title ended — still loaded for editing; scrub back and ⏯ to listen.":
        "✏️ Titel zu Ende — für das Bearbeiten noch geladen; zurückspulen und ⏯ "
        "zum Anhören.",
    "A Paso Doble under this switch is never faded out and ignores\n"
    "the play length — it is danced to its choreographed highlights.\n"
    "the highlights (crescendo → dramatic drop) are auto-detected\n"
    "in the background and the music shuts off at once when the\n"
    "chosen one (its closing gong) hits. A highlight detection\n"
    "can't pin down falls back to the standard phrasing\n"
    "(1st ≈ 0:45, 2nd ≈ 1:15).\n"
    "\n"
    "Off, a Paso Doble is an ordinary title: the play length cuts it\n"
    "and the fade takes it out, like every other dance.":
        "Ein Paso Doble unter diesem Schalter wird nie ausgeblendet und\n"
        "ignoriert die Spielzeit — er wird auf seine choreografierten\n"
        "Höhepunkte getanzt.\n"
        "Die Höhepunkte (Crescendo → dramatischer Einbruch) werden im\n"
        "Hintergrund automatisch erkannt, und die Musik bricht sofort ab,\n"
        "wenn der gewählte (sein abschließender Gong) kommt. Ein Höhepunkt,\n"
        "den die Erkennung nicht festmachen kann, fällt auf die\n"
        "Standardphrasierung zurück (1. ≈ 0:45, 2. ≈ 1:15).\n"
        "\n"
        "Aus ist ein Paso Doble ein gewöhnlicher Titel: die Spielzeit\n"
        "schneidet ihn und die Blende nimmt ihn heraus, wie bei jedem\n"
        "anderen Tanz.",
    "Append the bars per minute (\"…, 29 Takt\") — useful in training,\n"
    "usually just noise on a tournament floor.\n"
    "\n"
    "Ticking this hands the WHOLE announcement to the Windows voice:\n"
    "the recordings have clips for the dances and the heats, none for\n"
    "a tempo, and two voices in one announcement sound like two\n"
    "announcers.":
        "Die Takte pro Minute anhängen („…, 29 Takt“) — im Training\n"
        "nützlich, auf einer Turnierfläche meist nur Lärm.\n"
        "\n"
        "Wird das gesetzt, übernimmt die Windows-Stimme die GANZE Ansage:\n"
        "die Aufnahmen haben Clips für die Tänze und die Gruppen, keinen\n"
        "für ein Tempo, und zwei Stimmen in einer Ansage klingen nach zwei\n"
        "Ansagern.",
    "Append the heat number (\"…, Heat 3\") — the couples hear which\n"
    "heat they are about to dance.\n"
    "\n"
    "Only a round grid has heats: a theme list, the warm-up and a free\n"
    "running order are announced without one. Recorded for heats 1-8;\n"
    "beyond that the number is left out.":
        "Die Gruppennummer anhängen („…, Gruppe 3“) — die Paare hören,\n"
        "in welcher Gruppe sie gleich tanzen.\n"
        "\n"
        "Nur ein Rundenraster hat Gruppen: eine Themenliste, das\n"
        "Eintanzen und eine freie Reihenfolge werden ohne angesagt.\n"
        "Aufgenommen für die Gruppen 1-8; darüber hinaus entfällt die\n"
        "Nummer.",
    "Choose one or more titles — or an .m3u playlist — that play\n"
    "softly during the pause between songs, faded in at the start\n"
    "and out before the next song. Several titles rotate: a title\n"
    "keeps playing pause after pause until it ends, then the next\n"
    "one takes over.":
        "Wähle einen oder mehrere Titel — oder eine .m3u-Playlist —, die\n"
        "in der Pause zwischen den Titeln leise laufen, am Anfang ein- und\n"
        "vor dem nächsten Titel ausgeblendet. Mehrere Titel wechseln sich\n"
        "ab: ein Titel läuft Pause um Pause weiter, bis er zu Ende ist,\n"
        "dann übernimmt der nächste.",
    "Compensate loudness differences between tracks on playback:\n"
    "each song's measured EBU R128 loudness is pulled towards a common\n"
    "target, so quiet old recordings and loud modern masters play at\n"
    "a similar level. Needs 📊 Analyze loudness (⚙ Settings) first.":
        "Lautheitsunterschiede zwischen den Titeln beim Abspielen ausgleichen:\n"
        "die gemessene EBU-R128-Lautheit jedes Titels wird auf ein gemeinsames\n"
        "Ziel gezogen, damit leise alte Aufnahmen und laute moderne Master\n"
        "ähnlich laut spielen. Braucht vorher 📊 Lautheit analysieren\n"
        "(⚙ Einstellungen).",
    "Forget the current track's learned highlights\n"
    "(falls back to 🐂 auto-detection on the next play).":
        "Die gelernten Höhepunkte des laufenden Titels vergessen\n"
        "(beim nächsten Abspielen greift wieder die 🐂 automatische\n"
        "Erkennung).",
    "Hold a Paso Doble back this long before the music starts, so the\n"
    "couples reach their position after the dance is called. Applies\n"
    "to every way a PD is started — ▶, a double-click, auto-advance.\n"
    "0 s = start at once, like every other dance.\n"
    "\n"
    "With 🔈 Announce next dance on, the app makes the call and the\n"
    "seconds run from it; off, the hall's announcer does and the wait\n"
    "runs silently — counted down on this panel either way.":
        "Einen Paso Doble so lange zurückhalten, bevor die Musik einsetzt,\n"
        "damit die Paare nach dem Aufruf ihre Position erreichen. Gilt für\n"
        "jeden Weg, einen PD zu starten — ▶, Doppelklick, Autovorlauf.\n"
        "0 s = sofort starten, wie bei jedem anderen Tanz.\n"
        "\n"
        "Mit 🔈 Nächsten Tanz ansagen macht die App den Aufruf und die\n"
        "Sekunden laufen ab ihm; aus macht ihn der Ansager im Saal und die\n"
        "Wartezeit läuft still — heruntergezählt wird sie in beiden Fällen\n"
        "in diesem Bereich.",
    "How loud the pause music plays, relative to the normal\n"
    "playback volume — kept lower so it stays in the background.":
        "Wie laut die Pausenmusik spielt, bezogen auf die normale\n"
        "Wiedergabelautstärke — bewusst leiser, damit sie im Hintergrund\n"
        "bleibt.",
    "Keep the screensaver and the display timeout off while music is\n"
    "playing or the presenter screen is open.\n"
    "\n"
    "The system counts idle time from the mouse and the keyboard,\n"
    "never from the speakers — so an hour of music with nobody touching\n"
    "the desk blanks the screen mid-heat, the beamer included. It goes\n"
    "back to its normal timeouts as soon as neither is running.":
        "Bildschirmschoner und Display-Abschaltung aushebeln, solange Musik\n"
        "läuft oder der Moderationsbildschirm offen ist.\n"
        "\n"
        "Das System zählt die Leerlaufzeit an Maus und Tastatur, nie an den\n"
        "Lautsprechern — eine Stunde Musik, ohne dass jemand das Pult\n"
        "anfasst, macht also mitten in der Gruppe den Bildschirm dunkel, den\n"
        "Beamer eingeschlossen. Sobald beides nicht mehr läuft, gelten wieder\n"
        "die normalen Zeiten.",
    "Off: the next song starts the moment the current one ends, with\n"
    "no filler music and no announcement. The configured time is kept\n"
    "for switching back.\n"
    "\n"
    "Needs ⏭ auto-advance — without it the next song waits for the\n"
    "operator anyway, so there is no gap to fill.":
        "Aus: der nächste Titel beginnt in dem Moment, in dem der laufende\n"
        "endet, ohne Füllmusik und ohne Ansage. Die eingestellte Zeit bleibt\n"
        "für das Zurückschalten erhalten.\n"
        "\n"
        "Braucht den ⏭ Autovorlauf — ohne ihn wartet der nächste Titel\n"
        "ohnehin auf den Operator, es gibt also keine Lücke zu füllen.",
    "On: a double-click in a deck puts the title on the speakers at\n"
    "once — what a party wants.\n"
    "Off: it is only CUED on the player (loaded, shown, silent) and ⏯\n"
    "starts it — what a heat wants, where the music begins when the\n"
    "couples are on the floor and not a moment earlier.\n"
    "\n"
    "Part of the play sets: 🏆 tournament switches it off, 🎉 party on.":
        "An: ein Doppelklick in einem Deck legt den Titel sofort auf die\n"
        "Lautsprecher — was eine Party will.\n"
        "Aus: er wird nur auf dem Player VORBEREITET (geladen, angezeigt,\n"
        "still) und ⏯ startet ihn — was eine Gruppe will, bei der die\n"
        "Musik beginnt, wenn die Paare auf der Fläche stehen, und keinen\n"
        "Moment früher.\n"
        "\n"
        "Teil der Abspiel-Sets: 🏆 Turnier schaltet es aus, 🎉 Party ein.",
    "On: a double-click in a deck plays the title at once.\n"
    "Off: it is only cued on the player (loaded, shown,\n"
    "silent) and ⏯ starts it — the heat begins when the\n"
    "couples stand.":
        "An: ein Doppelklick in einem Deck spielt den Titel sofort.\n"
        "Aus: er wird nur auf dem Player vorbereitet (geladen,\n"
        "angezeigt, still) und ⏯ startet ihn — die Gruppe beginnt,\n"
        "wenn die Paare stehen.",
    "Pitch every title to the mean tempo of its dance in the\n"
    "current round, kept inside the TSO range — what a heat is\n"
    "danced to. Wrong for a party, where the next song is a\n"
    "different dance at whatever tempo it was recorded at.":
        "Jeden Titel auf das mittlere Tempo seines Tanzes in der\n"
        "laufenden Runde ziehen, innerhalb des TSO-Bereichs gehalten —\n"
        "so wird eine Gruppe getanzt. Falsch für eine Party, wo der\n"
        "nächste Titel ein anderer Tanz in dem Tempo ist, in dem er\n"
        "aufgenommen wurde.",
    "Open a second, full-screen window showing only the running title\n"
    "with its dance and the next three songs — big and plain, for a\n"
    "beamer or a monitor turned towards the floor. Pick the screen\n"
    "next to it; Esc (or this button) closes it again.":
        "Ein zweites, bildschirmfüllendes Fenster öffnen, das nur den\n"
        "laufenden Titel mit seinem Tanz und die nächsten drei Titel zeigt —\n"
        "groß und schlicht, für einen Beamer oder einen zur Fläche gedrehten\n"
        "Monitor. Den Bildschirm dafür wählst du daneben; Esc (oder dieser\n"
        "Knopf) schließt es wieder.",
    "Pause the music and suspend the highlight stop, so the whole Paso\n"
    "Doble is reachable while you set its marks: scrub to a crash, ⏯ to\n"
    "listen, hit 🎯, delete a wrong mark with its ✕. Marking within 3 s\n"
    "of an existing mark moves that one instead of adding a fourth.\n"
    "\n"
    "Leaving edit mode arms the stop again and PAUSES at it the next\n"
    "time it's reached, so you can hear whether the mark sits right.":
        "Die Musik anhalten und den Höhepunkt-Stopp aussetzen, damit der\n"
        "ganze Paso Doble erreichbar ist, während du seine Marken setzt:\n"
        "zu einem Schlag spulen, ⏯ zum Anhören, 🎯 drücken, eine falsche\n"
        "Marke mit ihrem ✕ löschen. Eine Marke innerhalb von 3 s zu einer\n"
        "bestehenden verschiebt diese, statt eine vierte anzulegen.\n"
        "\n"
        "Das Verlassen des Bearbeitungsmodus schärft den Stopp wieder und\n"
        "HÄLT beim nächsten Erreichen dort an, damit du hören kannst, ob die\n"
        "Marke richtig sitzt.",
    "Put the panel back on the competition values in one go: the\n"
    "configured play length, no pause between songs, no auto-advance\n"
    "and no spoken announcement — the settings a heat is run with.\n"
    "\n"
    "Lit gold while the panel stands on those values, the way 🎉 is lit\n"
    "purple during a party. Switches the 🎉 party set off. What exactly\n"
    "it sets is yours to change: ⚙ Settings → 🎛 Play sets.":
        "Den Bereich mit einem Griff zurück auf die Turnierwerte stellen:\n"
        "die eingestellte Spielzeit, keine Pause zwischen den Titeln, kein\n"
        "Autovorlauf und keine gesprochene Ansage — die Einstellungen, mit\n"
        "denen eine Gruppe gefahren wird.\n"
        "\n"
        "Leuchtet golden, solange der Bereich auf diesen Werten steht, so wie\n"
        "🎉 während einer Party violett leuchtet. Schaltet das Set 🎉 Party\n"
        "aus. Was es genau setzt, kannst du ändern: ⚙ Einstellungen →\n"
        "🎛 Abspiel-Sets.",
    "Say the next dance out loud shortly before the pause ends\n"
    "(\"Nächster Tanz: Langsamer Walzer\"). Without a pause the dance\n"
    "is named as the title starts instead (\"Langsamer Walzer\") —\n"
    "over the first bars or before them, whichever the pair below\n"
    "is set to.":
        "Den nächsten Tanz kurz vor Ende der Pause ansagen\n"
        "(„Nächster Tanz: Langsamer Walzer“). Ohne Pause wird der Tanz\n"
        "stattdessen beim Start des Titels genannt („Langsamer Walzer“) —\n"
        "über den ersten Takten oder davor, je nach dem Paar\n"
        "darunter.",
    "The dance is named while the music is already running, ducked\n"
    "under the voice — the hall hears both at once and the title\n"
    "loses none of its first bars.\n\n"
    "Applies where a title names its dance as it starts: 🔈 Announce\n"
    "next dance on, and no pause between songs (a pause has a gap of\n"
    "its own for the call).":
        "Der Tanz wird genannt, während die Musik schon läuft — sie wird\n"
        "unter der Stimme leiser. Der Saal hört beides zugleich, und dem\n"
        "Titel fehlt kein einziger Takt.\n\n"
        "Gilt, wo ein Titel seinen Tanz beim Start nennt: 🔈 Nächsten Tanz\n"
        "ansagen an und keine Pause zwischen den Titeln (eine Pause hat\n"
        "ihre eigene Lücke für die Ansage).",
    "The dance is called into silence and the music follows when the\n"
    "voice is done — the hall hears WHICH dance before it starts, at\n"
    "the cost of a second or two of quiet.\n\n"
    "Applies where a title names its dance as it starts: 🔈 Announce\n"
    "next dance on, and no pause between songs (a pause has a gap of\n"
    "its own for the call).":
        "Der Tanz wird in die Stille angesagt, die Musik folgt, sobald die\n"
        "Stimme fertig ist — der Saal hört, WELCHER Tanz kommt, bevor er\n"
        "beginnt, um den Preis von ein, zwei Sekunden Ruhe.\n\n"
        "Gilt, wo ein Titel seinen Tanz beim Start nennt: 🔈 Nächsten Tanz\n"
        "ansagen an und keine Pause zwischen den Titeln (eine Pause hat\n"
        "ihre eigene Lücke für die Ansage).",
    "Show a cover picture next to the title on the player.\n"
    "The playlist's own image is used when it has one (an #EXTIMG line\n"
    "in the .m3u or a cover file beside it), otherwise the track's\n"
    "embedded artwork, otherwise a plain ♪ tile.":
        "Ein Coverbild neben dem Titel auf dem Player zeigen.\n"
        "Benutzt wird das eigene Bild der Playlist, wenn sie eines hat\n"
        "(eine #EXTIMG-Zeile in der .m3u oder eine Cover-Datei daneben),\n"
        "sonst das im Titel eingebettete Bild, sonst eine schlichte\n"
        "♪-Kachel.",
    "Speak a sample announcement now — check voice and level\n"
    "before the round, not during it.":
        "Jetzt eine Beispielansage sprechen — Stimme und Pegel vor der\n"
        "Runde prüfen, nicht währenddessen.",
    "Switch the tournament settings over to party playing in one go:\n"
    "every title to its full length, auto-advance to the next one, no\n"
    "pause (so no break music) in between and no spoken announcement.\n"
    "\n"
    "Applied by itself as soon as you play from the 🤸 Eintanzen /\n"
    "party list, and switched back when a tournament deck takes over —\n"
    "a toast says what changed either way. What exactly it sets is\n"
    "yours to change: ⚙ Settings → 🎛 Play sets.":
        "Die Turniereinstellungen mit einem Griff auf Party-Betrieb umstellen:\n"
        "jeden Titel in voller Länge, Autovorlauf zum nächsten, keine Pause\n"
        "(also keine Pausenmusik) dazwischen und keine gesprochene Ansage.\n"
        "\n"
        "Wird von selbst angewandt, sobald du aus der Liste 🤸 Eintanzen /\n"
        "Party spielst, und zurückgeschaltet, wenn ein Turnierdeck übernimmt —\n"
        "ein Hinweis sagt in beiden Fällen, was sich geändert hat. Was es genau\n"
        "setzt, kannst du ändern: ⚙ Einstellungen → 🎛 Abspiel-Sets.",
    "The colours of the presenter screen. 'Default' is the black hall\n"
    "display; 'Light' is creme paper with warm brown type and rose\n"
    "gold for the next dance — made for a lit room, where black on a\n"
    "beamer is just a grey rectangle. Applies straight away.":
        "Die Farben des Moderationsbildschirms. „Default“ ist die schwarze\n"
        "Saalanzeige; „Light“ ist cremefarbenes Papier mit warmbrauner\n"
        "Schrift und Roségold für den nächsten Tanz — gemacht für einen\n"
        "beleuchteten Raum, in dem Schwarz auf einem Beamer nur ein graues\n"
        "Rechteck ist. Wirkt sofort.",
    "The evening's running order — when dinner is, when the opening\n"
    "dance is — as a second page on the presenter screen.\n"
    "\n"
    "Type it here; on the screen itself, T (or its 🕒 button) switches\n"
    "to it, and it can fade between the two pages by itself.":
        "Der Ablauf des Abends — wann das Essen ist, wann der Eröffnungstanz\n"
        "ist — als zweite Seite auf dem Moderationsbildschirm.\n"
        "\n"
        "Hier wird er eingetippt; auf dem Bildschirm selbst schaltet T (oder\n"
        "sein 🕒 Knopf) dorthin um, und er kann auch von allein zwischen den\n"
        "beiden Seiten überblenden.",
    "There is one player for every deck, so leaving a title to hear\n"
    "another one loses your place in it. On: the spot a title stopped\n"
    "at is kept and it starts there again — marked by a tick on the\n"
    "seek bar and by ↩ mm:ss on its row.\n"
    "\n"
    "A title played to its end keeps no mark, and the marks are\n"
    "forgotten when the app closes.":
        "Es gibt einen Player je Deck, wer einen Titel verlässt, um einen\n"
        "anderen zu hören, verliert also seine Stelle darin. An: die Stelle,\n"
        "an der ein Titel gestoppt wurde, bleibt erhalten und er beginnt dort\n"
        "wieder — markiert durch einen Strich auf dem Spulbalken und durch\n"
        "↩ mm:ss in seiner Zeile.\n"
        "\n"
        "Ein bis zum Ende gespielter Titel behält keine Marke, und die Marken\n"
        "gehen verloren, wenn die App schließt.",
    "Time for the couples to change / catch breath before the next song":
        "Zeit für die Paare zum Wechseln / Durchatmen vor dem nächsten Titel",
    "Volume ramps to 0 over the last N seconds,\n"
    "in steps of half a second":
        "Die Lautstärke fällt über die letzten N Sekunden auf 0,\n"
        "in Schritten von einer halben Sekunde",
    "When a song ends (fade-out or natural end), pause for the\n"
    "configured time, then play the next song row of the deck —\n"
    "so a whole round runs through hands-free. Stops at the end\n"
    "of the round (🏁) — the next round is started manually.\n"
    "\n"
    "Switching it off stops 🔈 Announce next dance too: nothing\n"
    "should call a dance that nothing then plays. Switching it\n"
    "back on restores the announcement you had.\n"
    "\n"
    "Every playlist keeps its own answer: this is the one of the\n"
    "list last clicked, the same as the ⏭/✋ under that deck.":
        "Wenn ein Titel endet (Ausblende oder natürliches Ende), die\n"
        "eingestellte Zeit pausieren und dann die nächste Titelzeile des\n"
        "Decks spielen — so läuft eine ganze Runde ohne Zutun durch. Hält\n"
        "am Ende der Runde (🏁) an — die nächste Runde wird von Hand\n"
        "gestartet.\n"
        "\n"
        "Beim Ausschalten hält auch 🔈 Nächsten Tanz ansagen an: Es soll\n"
        "kein Tanz angesagt werden, den dann nichts spielt. Beim Wieder-\n"
        "einschalten kehrt die vorherige Ansage zurück.\n"
        "\n"
        "Jede Playlist behält ihre eigene Antwort: Dies ist die der\n"
        "zuletzt angeklickten Liste, dieselbe wie ⏭/✋ unter dem Deck.",
    # No entry for "⏭  Auto": Auto is the German word here too, and the
    # toggle sits on a deck header where "Automatik" was simply longer.
    # A "⏭  Auto": "⏭  Auto" line would be the obvious way to say that and
    # is the one thing forbidden — test_no_entry_translates_to_itself. An
    # absent key falls through to the English, which is what is wanted.
    "✋  Manual": "✋  Manuell",
    "Auto: a finished song is followed by the next row of the deck, so\n"
    "a whole round runs hands-free.\n"
    "Manual: every song is started by the operator, and 🔈 Announce\n"
    "next dance stops with it — back on Auto it returns.\n"
    "\n"
    "This playlist's own answer, remembered for it: the party list can\n"
    "run hands-free while the round next to it is started by hand.\n"
    "⏭ Auto-advance on the play panel is the same answer while this\n"
    "list is the one last clicked.":
        "Automatik: Auf einen fertigen Titel folgt die nächste Zeile des\n"
        "Decks, so läuft eine ganze Runde ohne Zutun.\n"
        "Manuell: Jeder Titel wird von Hand gestartet, und 🔈 Nächsten\n"
        "Tanz ansagen hält mit an — zurück auf Automatik kommt es wieder.\n"
        "\n"
        "Die eigene Antwort dieser Playlist, für sie gemerkt: Die\n"
        "Party-Liste kann ohne Zutun laufen, während die Runde daneben\n"
        "von Hand gestartet wird. ⏭ Automatisch zum nächsten Titel auf\n"
        "dem Spiel-Panel ist dieselbe Antwort, solange diese Liste die\n"
        "zuletzt angeklickte ist.",
    "Manual: every song is started by the operator, and 🔈 Announce\n"
    "next dance is off with it.\n"
    "Auto: a finished song is followed by the next row of the deck, so\n"
    "a whole round runs hands-free — and the announcement returns.\n"
    "\n"
    "This playlist's own answer, remembered for it: the party list can\n"
    "run hands-free while the round next to it is started by hand.\n"
    "⏭ Auto-advance on the play panel is the same answer while this\n"
    "list is the one last clicked.":
        "Manuell: Jeder Titel wird von Hand gestartet, und 🔈 Nächsten\n"
        "Tanz ansagen ist mit aus.\n"
        "Automatik: Auf einen fertigen Titel folgt die nächste Zeile des\n"
        "Decks, so läuft eine ganze Runde ohne Zutun — und die Ansage\n"
        "kommt wieder.\n"
        "\n"
        "Die eigene Antwort dieser Playlist, für sie gemerkt: Die\n"
        "Party-Liste kann ohne Zutun laufen, während die Runde daneben\n"
        "von Hand gestartet wird. ⏭ Automatisch zum nächsten Titel auf\n"
        "dem Spiel-Panel ist dieselbe Antwort, solange diese Liste die\n"
        "zuletzt angeklickte ist.",
    "When the LAST title of the list has finished, carry on with its\n"
    "first one instead of stopping — so a party keeps its music going\n"
    "without anybody at the desk.\n"
    "\n"
    "The 🏁 end of a round is untouched: that one happens between\n"
    "rounds, and still waits for the operator.\n"
    "\n"
    "Needs ⏭ auto-advance.":
        "Wenn der LETZTE Titel der Liste zu Ende ist, mit ihrem ersten\n"
        "weitermachen, statt zu stoppen — so bleibt auf einer Party die\n"
        "Musik in Gang, ohne dass jemand am Pult steht.\n"
        "\n"
        "Das 🏁 Ende einer Runde bleibt unangetastet: das liegt zwischen\n"
        "den Runden und wartet weiterhin auf den Operator.\n"
        "\n"
        "Braucht den ⏭ Autovorlauf.",
    "Which highlight ends the Paso Doble — usually the 2nd,\n"
    "in rare cases the 3rd.":
        "Welcher Höhepunkt den Paso Doble beendet — meist der 2.,\n"
        "in seltenen Fällen der 3.",
    "Which monitor the presenter screen fills. Same screen as the app\n"
    "is fine too — double-click the presenter window to shrink it back\n"
    "out of full screen.":
        "Welchen Monitor der Moderationsbildschirm füllt. Derselbe Bildschirm\n"
        "wie die App geht auch — ein Doppelklick auf das Moderationsfenster\n"
        "holt es wieder aus dem Vollbild heraus.",
    "Which recorded voice announces the dance. “Mixed” alternates them\n"
    "— she, he, she, he — so an evening doesn't run on a single voice.\n"
    "\n"
    "A dance that was never recorded is not announced.":
        "Welche aufgenommene Stimme den Tanz ansagt. „Gemischt“ wechselt sie\n"
        "ab — sie, er, sie, er — damit ein Abend nicht auf einer einzigen\n"
        "Stimme läuft.\n"
        "\n"
        "Ein Tanz, der nie aufgenommen wurde, wird nicht angesagt.",
    "While a Paso Doble plays, click exactly when a highlight (the\n"
    "dramatic gong / drop) hits to teach its position. Click again at\n"
    "the 2nd / 3rd highlight. Manually learned highlights are flagged\n"
    "in the database and are never overwritten by 🐂 auto-detection.":
        "Klicke, während ein Paso Doble läuft, genau dann, wenn ein Höhepunkt\n"
        "(der dramatische Gong / Einbruch) kommt, um seine Position zu lernen.\n"
        "Beim 2. / 3. Höhepunkt erneut klicken. Von Hand gelernte Höhepunkte\n"
        "werden in der Datenbank markiert und nie von der 🐂 automatischen\n"
        "Erkennung überschrieben.",
    "Adjusted play length (timed play / Paso Doble highlight stop)\n"
    "next to the track's full length":
        "Angepasste Spielzeit (getaktetes Spielen / Höhepunkt-Stopp beim\n"
        "Paso Doble) neben der vollen Länge des Titels",
    "Auto-equalize the heat tempo (toggle):\n"
    "while on, every title is pitched to the average tempo of its\n"
    "dance in this round, kept inside the TSO range (e.g. a Rumba\n"
    "at 23 → T24, a Paso Doble at 57 → T58).":
        "Das Tempo der Gruppe automatisch angleichen (Schalter):\n"
        "solange an, wird jeder Titel auf das mittlere Tempo seines Tanzes\n"
        "in dieser Runde gezogen, innerhalb des TSO-Bereichs gehalten\n"
        "(z. B. eine Rumba bei 23 → T24, ein Paso Doble bei 57 → T58).",
    "Disable preview player  (re-enable in Settings)":
        "Vorhör-Player abschalten  (in den Einstellungen wieder einschaltbar)",
    "Duck to 20 % / back to full — the filler music comes down too":
        "Auf 20 % absenken / zurück auf voll — die Pausenmusik geht mit herunter",
    "Endless repeat of THIS title (toggle):\n"
    "while on, the running title starts again every time it ends —\n"
    "for the moment the floor is still full or the speech runs long.\n"
    "\n"
    "It holds the evening on one title, so it beats the 🏁 end of a\n"
    "round and works with ⏭ auto-advance off too. Switch it off and\n"
    "the list carries on where it stands.":
        "Endlose Wiederholung DIESES Titels (Schalter):\n"
        "solange an, beginnt der laufende Titel jedes Mal neu, wenn er endet —\n"
        "für den Moment, in dem die Fläche noch voll ist oder die Rede länger\n"
        "dauert.\n"
        "\n"
        "Er hält den Abend auf einem Titel, schlägt damit das 🏁 Ende einer\n"
        "Runde und wirkt auch bei ausgeschaltetem ⏭ Autovorlauf. Schalte ihn\n"
        "aus, und die Liste läuft weiter, wo sie steht.",
    "Extend the auto-advance pause (add another pause length) —\n"
    "use it when the heat change is taking longer than planned.":
        "Die Pause des Autovorlaufs verlängern (eine weitere Pausenlänge\n"
        "anhängen) — für den Fall, dass der Gruppenwechsel länger dauert\n"
        "als geplant.",
    "Fade the music out and HOLD it there (over the fade time).\n"
    "Nothing ends and nothing advances — ⏯ resumes at exactly the\n"
    "spot it went quiet. For an announcement or an incident on the floor.":
        "Die Musik ausblenden und dort HALTEN (über die Blendzeit).\n"
        "Nichts endet und nichts rückt vor — ⏯ setzt genau an der Stelle\n"
        "wieder ein, an der es still wurde. Für eine Durchsage oder einen\n"
        "Zwischenfall auf der Fläche.",
    "Fade this song out now (over the configured fade time), then end it\n"
    "— for a quick, clean finish on the floor.":
        "Diesen Titel jetzt ausblenden (über die eingestellte Blendzeit) und\n"
        "dann beenden — für einen schnellen, sauberen Schluss auf der\n"
        "Fläche.",
    "Jump straight to the pause music — end this song now and start\n"
    "the between-songs pause (e.g. the dancers are already leaving).":
        "Direkt zur Pausenmusik springen — diesen Titel jetzt beenden und\n"
        "die Pause zwischen den Titeln starten (z. B. weil die Tänzer die\n"
        "Fläche schon verlassen).",
    "Tap along to the beat to measure this track's live tempo by hand,\n"
    "against a target for its dance (Sollwert) — display only, does not\n"
    "touch the fader.":
        "Im Takt mitklicken, um das Tempo dieses Titels von Hand zu messen,\n"
        "gegen einen Sollwert für seinen Tanz — nur Anzeige, der Fader wird\n"
        "nicht angefasst.",
    "Tempo −16 % … +16 % without changing the pitch (time stretch) —\n"
    "e.g. to pull a track onto the takt the tournament needs.\n"
    "Stays set across tracks; a double-click on the fader (or the\n"
    "button below) resets it.":
        "Tempo −16 % … +16 % ohne Änderung der Tonhöhe (Zeitdehnung) —\n"
        "z. B. um einen Titel auf den Takt zu ziehen, den das Turnier braucht.\n"
        "Bleibt über die Titel hinweg gesetzt; ein Doppelklick auf den Fader\n"
        "(oder der Knopf darunter) stellt ihn zurück.",
    "📌 Pin the tempo: the fader stays where you left it when the next\n"
    "title starts.\n"
    "Off: every new title begins at ±0 %.\n"
    "Switching TSO on takes the pin off — TSO pitches each title itself.":
        "📌 Das Tempo festnageln: der Fader bleibt, wo du ihn gelassen hast,\n"
        "wenn der nächste Titel beginnt.\n"
        "Aus: jeder neue Titel beginnt bei ±0 %.\n"
        "TSO einzuschalten nimmt die Nadel heraus — TSO zieht jeden Titel\n"
        "selbst.",
    "Off, the running order goes by this machine's clock.\n"
    "\n"
    "On, it goes by the time you set here — from the moment you save,\n"
    "and running on from there. An evening half an hour behind stays\n"
    "half an hour behind; the screen does not stand still.\n"
    "\n"
    "This is not saved with the programme: the next start of the app\n"
    "is back on the machine's clock.":
        "Aus richtet sich der Ablauf nach der Uhr dieses Rechners.\n"
        "\n"
        "An richtet er sich nach der Zeit, die du hier setzt — ab dem\n"
        "Moment des Speicherns, und von dort weiterlaufend. Ein Abend, der\n"
        "eine halbe Stunde hinterherhinkt, bleibt eine halbe Stunde hinten;\n"
        "der Bildschirm steht nicht still.\n"
        "\n"
        "Das wird nicht mit dem Programm gespeichert: beim nächsten Start\n"
        "der App gilt wieder die Uhr des Rechners.",
    "Off, the screen stays on whichever page you picked (T on the\n"
    "presenter screen, or its 🕒 button, switches by hand).\n"
    "\n"
    "On, it fades from one to the other by itself — so the hall sees\n"
    "both without anybody at the desk touching anything.":
        "Aus bleibt der Bildschirm auf der Seite, die du gewählt hast\n"
        "(T auf dem Moderationsbildschirm oder sein 🕒 Knopf schaltet von\n"
        "Hand um).\n"
        "\n"
        "An blendet er von selbst von der einen zur anderen — so sieht der\n"
        "Saal beide, ohne dass jemand am Pult etwas anfasst.",
    "What the presenter screen shows on its second page — the evening's\n"
    "running order. The line the clock has reached is highlighted, the\n"
    "ones before it are greyed out.\n"
    "\n"
    "A time may be anything you would write on a programme; only real\n"
    "clock times (20:30, 20.30) take part in the highlighting.\n"
    "\n"
    "\"Until\" is optional and is what lets one point hold another: give\n"
    "the party 19:00–01:00 and the opening dance 19:30–19:50, and when\n"
    "the dance is over the highlight goes back to the party. Either an\n"
    "end time (01:00) or a length in minutes (20).":
        "Was der Moderationsbildschirm auf seiner zweiten Seite zeigt — den\n"
        "Ablauf des Abends. Die Zeile, die die Uhr erreicht hat, wird\n"
        "hervorgehoben, die davor werden ausgegraut.\n"
        "\n"
        "Eine Zeit darf alles sein, was du auf ein Programm schreiben würdest;\n"
        "nur echte Uhrzeiten (20:30, 20.30) nehmen an der Hervorhebung teil.\n"
        "\n"
        "„Bis“ ist freiwillig und lässt einen Punkt einen anderen umschließen:\n"
        "gib der Party 19:00–01:00 und dem Eröffnungstanz 19:30–19:50, und\n"
        "wenn der Tanz vorbei ist, springt die Hervorhebung zurück auf die\n"
        "Party. Entweder eine Endzeit (01:00) oder eine Länge in Minuten (20).",
    # ── The chrome the hook could not reach before ───────────────────────────
    "Dance": "Tanz",
    "Title": "Titel",
    "📋  Path copied to clipboard": "📋  Pfad in die Zwischenablage kopiert",
    "Artist": "Interpret",
    "🏷 MP3 tag": "🏷 MP3-Tag",
    "🔬 Measured": "🔬 Gemessen",
    "🔀  Shared between playlists": "🔀  In mehreren Playlists",
    "Action": "Aktion",
    "Nothing usable — the decks were left alone.":
        "Nichts Verwertbares — die Decks blieben unverändert.",
    "Issue(s)": "Probleme",
    "Remove song": "Titel entfernen",
    "Remove dance": "Tanz entfernen",
    " tracks": " Titel",
    "In your own words — what this list is for (optional):":
        "In eigenen Worten — wofür diese Liste gedacht ist (optional):",
    "Rules the model has to follow:":
        "Regeln, an die sich das Modell halten muss:",
    "Claude login:": "Claude-Anmeldung:",
    "📝  Details copied to clipboard":
        "📝  Details in die Zwischenablage kopiert",
    "Mode:": "Modus:",
    "Favorites": "Favoriten",
    "Theme": "Thema",
    "Past Competitions": "Frühere Turniere",
    "Draw tracks from:": "Titel nehmen aus:",
    "Dance Style:": "Tanzart:",
    "Age Class:": "Altersgruppe:",
    "Start Class:": "Startklasse:",
    "Dances:": "Tänze:",
    "Rounds  (e.g. 6-3-2-1):": "Runden  (z. B. 6-3-2-1):",
    "Paste competition schedule:": "Turnierplan einfügen:",
    "Competition:": "Turnier:",
    "Seeds the grid from songs you played at this\n"
    "class before (matching per-class M3U files).":
        "Füllt das Raster mit Titeln, die du in dieser\n"
        "Klasse schon gespielt hast (passende M3U-Dateien je Klasse).",
    "Theme:": "Thema:",
    "Number of tracks:": "Anzahl Titel:",
    "Themes use ID3 year tags + themes.json overrides.\n"
    "Decade themes need year data in your MP3s.":
        "Themen nutzen ID3-Jahresangaben und Überschreibungen in themes.json.\n"
        "Jahrzehnt-Themen brauchen Jahresangaben in deinen MP3s.",
    "⏱  Too short — at or below:": "⏱  Zu kurz — bei oder unter:",
    "The cut must cover the 1:30–1:45 TSO play time; default 1:45.":
        "Der Schnitt muss die TSO-Spielzeit von 1:30–1:45 abdecken; Standard 1:45.",
    "⏳  Too long — above:": "⏳  Zu lang — über:",
    "Only flagged when the ⏳ checkbox in the Music-check window is on "
    "(Eintanzen playlists); default 4:00.":
        "Wird nur gemeldet, wenn im Musik-Check-Fenster das Häkchen ⏳ gesetzt ist "
        "(Eintanzen-Playlists); Standard 4:00.",
    "⚡  Tempo mismatch — deviation above:":
        "⚡  Tempo weicht ab — Abweichung über:",
    "Measured tempo vs the filename label (detector ×2, ×3, ×1.5 … slips are "
    "excused first); default 10 %.":
        "Gemessenes Tempo gegen die Angabe im Dateinamen (Ausrutscher des "
        "Detektors um ×2, ×3, ×1,5 … werden vorher verziehen); Standard 10 %.",
    "🔇  Hiss — noise floor above:": "🔇  Rauschen — Grundrauschen über:",
    "How quiet a track must get somewhere. A clean file reaches its lead-in "
    "silence, a tape rip never gets below its own hiss; default −50 dB. Only "
    "flagged when the 🔇 checkbox in the Music-check window is on.":
        "Wie leise ein Titel irgendwo werden muss. Eine saubere Datei erreicht "
        "ihre Stille vor dem Einsatz, ein Bandmitschnitt kommt nie unter sein "
        "eigenes Rauschen; Standard −50 dB. Wird nur gemeldet, wenn im "
        "Musik-Check-Fenster das Häkchen 🔇 gesetzt ist.",
    "📄 File name": "📄 Dateiname",
    "Source": "Quelle",
    "Speed": "Tempo",
    "— (no BPM tag)": "— (kein BPM-Tag)",
    "— (not measured)": "— (nicht gemessen)",
    "🔁  Doubled inside one playlist": "🔁  Doppelt in einer Playlist",
    "File": "Datei",
    "📌  Reference base (single .m3u)": "📌  Referenz-Basis (eine .m3u)",
    "🎯  Tournament files (compared against)":
        "🎯  Turnierdateien (dagegen wird verglichen)",
    "🔁  Doubled inside a playlist": "🔁  Doppelt in einer Playlist",
    "Added": "Hinzugefügt",
    "Last": "Zuletzt",
    "Build all caches — librosa…": "Alle Caches aufbauen — librosa…",
    "Analyzing audio (timbre)…": "Audio wird analysiert (Timbre)…",
    "Audio analysis": "Audio-Analyse",
    "Measuring loudness (EBU R128)…": "Lautheit wird gemessen (EBU R128)…",
    "Loudness analysis": "Lautheits-Analyse",
    "Probing silent stretches…": "Stille Passagen werden geprüft…",
    "Silence probe": "Stille-Prüfung",
    "Separating vocals (Demucs)…": "Gesang wird getrennt (Demucs)…",
    "Vocal separation": "Gesangstrennung",
    "Detecting Paso Doble highlights…":
        "Paso-Doble-Höhepunkte werden erkannt…",
    "PD highlight detection": "PD-Höhepunkt-Erkennung",
    "✅  No other open playlist to compare against":
        "✅  Keine andere offene Playlist zum Vergleichen",
    "✅  Nothing here is in another open playlist":
        "✅  Nichts davon steht in einer anderen offenen Playlist",
    "Remove duplicates": "Doppelte entfernen",
    "🌐  Whole repository — every file under your music repo (global search).\n"
    "🎯  Favorites library — just your tanzcds folder.\n"
    "➕  Both — the repository and the favorites library.":
        "🌐  Ganzes Repository — jede Datei unter deinem Musik-Repo (globale "
        "Suche).\n"
        "🎯  Favoriten-Bibliothek — nur dein tanzcds-Ordner.\n"
        "➕  Beides — das Repository und die Favoriten-Bibliothek.",
    "Standard dances": "Standardtänze",
    "Latin dances": "Lateintänze",
    "Interleave short social-dance rounds — needs those tracks in your library.":
        "Kurze Modetanz-Runden dazwischenschieben — braucht diese Titel in deiner "
        "Bibliothek.",
    "No Paso Doble": "Kein Paso Doble",
    "Start with a Latin round": "Mit einer Lateinrunde beginnen",
    "Late Wiener Walzer (hold back early / not back-to-back)":
        "Wiener Walzer spät (früh zurückhalten / nicht direkt hintereinander)",
    "Late Paso Doble (not in the first ~40 songs)":
        "Paso Doble spät (nicht in den ersten ~40 Titeln)",
    "Failed — nothing was changed.":
        "Fehlgeschlagen — es wurde nichts geändert.",
    "♻️  Restoring your last session…":
        "♻️  Letzte Sitzung wird wiederhergestellt…",
    "Indexing whole repository…": "Ganzes Repository wird indiziert…",
    "Build / refresh librosa audio index":
        "librosa-Audioindex aufbauen / auffrischen",
    "Scanning repository…": "Repository wird durchsucht…",
    "Cleaning up database…": "Datenbank wird aufgeräumt…",
    "Re-learning playlist popularity…":
        "Playlist-Beliebtheit wird neu gelernt…",
    "Loading repository from cache…": "Repository wird aus dem Cache geladen…",
    "🔊 Audio backend": "🔊 Audio-Backend",
    "The audio backend is chosen when the app starts, so the new one takes "
    "over after a restart.\n"
    "\n"
    "Restart now?":
        "Das Audio-Backend wird beim Start der App gewählt, das neue greift also "
        "erst nach einem Neustart.\n"
        "\n"
        "Jetzt neu starten?",
    "The theme, the accent colour and the language are applied while the app "
    "starts, so they take over after a restart.\n"
    "\n"
    "Restart now?":
        "Das Erscheinungsbild, die Akzentfarbe und die Sprache werden beim Start "
        "der App angewendet, sie greifen also erst nach einem Neustart.\n"
        "\n"
        "Jetzt neu starten?",
    "📂  Nothing new — all tracks already in the wishlist":
        "📂  Nichts Neues — alle Titel stehen schon auf der Wunschliste",
    "Length": "Länge",
    "Drag <b>.m3u playlists</b> (or audio files) here to check their tracks "
    "for the same issues — tempo label vs measured, TSO takt range, play "
    "length — plus the playlists' round structure (heat tempo spread).":
        "Ziehe <b>.m3u-Playlists</b> (oder Audiodateien) hierher, um ihre Titel "
        "auf dieselben Probleme zu prüfen — Tempoangabe gegen Messung, "
        "TSO-Taktbereich, Spiellänge — dazu den Rundenaufbau der Playlists "
        "(Tempospanne je Gruppe).",
    "Drag <b>.m3u playlists</b> here to check their track paths against the "
    "<b>search folders</b> (Settings). Broken references <b>and valid paths on "
    "a different root</b> (e.g. C:) that can be re-rooted there are listed per "
    "playlist; <b>🧭 Fix &amp; overwrite</b> rewrites those path lines <b>in "
    "place</b> — only the file path changes, every #EXTINF / comment line is "
    "kept exactly as-is.":
        "Ziehe <b>.m3u-Playlists</b> hierher, um ihre Titelpfade gegen die "
        "<b>Suchordner</b> (Einstellungen) zu prüfen. Kaputte Verweise <b>und "
        "gültige Pfade auf einem anderen Laufwerk</b> (z. B. C:), die sich dorthin "
        "umbiegen lassen, werden je Playlist aufgelistet; <b>🧭 Reparieren &amp; "
        "überschreiben</b> schreibt diese Pfadzeilen <b>an Ort und Stelle</b> um — "
        "nur der Dateipfad ändert sich, jede #EXTINF-/Kommentarzeile bleibt exakt "
        "erhalten.",
    "↶  Nothing to undo": "↶  Nichts rückgängig zu machen",
    "↷  Nothing to redo": "↷  Nichts zu wiederholen",
    "✅  No wishlist tracks are in an open playlist":
        "✅  Keine Wunschlisten-Titel stehen in einer offenen Playlist",
    "Heat": "Gruppe",
    "🔁  Cleared all replacement marks":
        "🔁  Alle Austausch-Markierungen gelöscht",
    "✅  Kept all titles": "✅  Alle Titel behalten",
    "✅  No duplicate titles in this list":
        "✅  Keine doppelten Titel in dieser Liste",
    "Already in the list — nothing added":
        "Steht schon in der Liste — nichts hinzugefügt",
    "⭐  Already in the wishlist — nothing added":
        "⭐  Steht schon auf der Wunschliste — nichts hinzugefügt",
    "Replace the existing track with this one?":
        "Den vorhandenen Titel durch diesen ersetzen?",
    "Remove heat": "Gruppe entfernen",
    "Remove round": "Runde entfernen",
    "Remove backup": "Ersatztitel entfernen",
    "Remove this backup song?": "Diesen Ersatztitel entfernen?",
    "⬆  Backup moved up into the empty slot":
        "⬆  Ersatztitel ist in den freien Platz nachgerückt",
    "Couldn't read the dropped track(s).":
        "Die abgelegten Titel konnten nicht gelesen werden.",
    "📊 Loudness probe failed": "📊 Lautheits-Messung fehlgeschlagen",
    "🔇 Silence probe failed": "🔇 Stille-Prüfung fehlgeschlagen",
    "Slot defaults — apply to every page":
        "Slot-Vorgaben — gelten für jede Seite",
    "Pad keys — travel with the pad": "Pad-Tasten — wandern mit dem Pad",
    "🔈  announcing…": "🔈  Ansage läuft…",
    "🛑  held": "🛑  angehalten",
    "🐂  detecting highlights…": "🐂  Höhepunkte werden erkannt…",
    "🐂  plays to the end": "🐂  spielt bis zum Ende",
    "🎯  stop reached — ⏯ to go on": "🎯  Stopp erreicht — ⏯ zum Weiterspielen",
    "🐂  Stop Paso Doble after highlight": "🐂  Paso Doble: Stopp am Höhepunkt",
    "⏭  Auto-advance to next song": "⏭  Automatisch zum nächsten Titel",
    # Kept short: the pair sits in a panel 250px wide at its narrowest, and
    # what each one actually does is in the tooltip.
    "over the first bars": "über den ersten Takten",
    "before the music starts": "vor dem Musikstart",
    "⏸  No pause between songs": "⏸  Keine Pause zwischen den Titeln",
    "🔁  Start again at the end": "🔁  Am Ende von vorn beginnen",
    "Pause between songs:": "Pause zwischen den Titeln:",
    "🔈  Announce next dance": "🔈  Nächsten Tanz ansagen",
    "…with takt": "…mit Takt",
    "…with heat": "…mit Gruppe",
    "🔊  Equalize volume (R128)": "🔊  Lautstärke angleichen (R128)",
    "🖼  Show artwork": "🖼  Cover anzeigen",
    "▶️  Double-click starts the title": "▶️  Doppelklick startet den Titel",
    "🎚  TSO pitch to the heat tempo": "🎚  TSO: auf den Takt der Gruppe ziehen",
    "↩  Remember where a title stopped":
        "↩  Merken, wo ein Titel stehen geblieben ist",
    "☀  Keep the screen awake": "☀  Bildschirm wach halten",
    "Show the transport on this screen":
        "Die Steuerung auf diesem Bildschirm zeigen",
    "Show the title played before this one": "Den Titel davor anzeigen",
    "Show the timetable  ·  T\n"
    "Right-click to edit it":
        "Den Zeitplan anzeigen  ·  T\n"
        "Rechtsklick zum Bearbeiten",
    "Close the presenter screen": "Den Moderations-Bildschirm schließen",
    "Previous title": "Vorheriger Titel",
    "Play / pause": "Wiedergabe / Pause",
    "Next title": "Nächster Titel",
    "Over to the break music": "Hinüber zur Pausenmusik",
    "Time": "Zeit",
    "Until": "Bis",
    "What": "Was",
    "Note": "Notiz",
    # ── The two widgets that were written in German ──────────────────────────
    "♪ Takt meter": "♪ Takt-Messung",
    "Takt count:": "Taktzahl:",
    "Target:": "Sollwert:",
    " Takt/min": " Takte/Min",
    "Correction needed:": "Notwendige Taktkorrektur:",
    "Apply": "Übernehmen",
    "Apply this correction to the tempo fader.":
        "Diese Korrektur auf den Tempo-Fader anwenden.",
    "Next dances": "Nächste Tänze",
    # ── ❔ F1, the cheat sheet — glued into HTML, so every row asks for itself ──
    "⌨  Keyboard": "⌨  Tastatur",
    "Space": "Leertaste",
    "Play / stop the selected song":
        "Den gewählten Titel abspielen / stoppen",
    "Ctrl + ← / →": "Strg + ← / →",
    "Seek 30 s back / forward while playing":
        "Während der Wiedergabe 30 s zurück / vor springen",
    "Ctrl + Shift + ← / →": "Strg + Umschalt + ← / →",
    "Previous / next title — same as ⏮ / ⏭ on the player (⏭ also ends a "
    "running pause)":
        "Vorheriger / nächster Titel — dasselbe wie ⏮ / ⏭ am Player (⏭ "
        "beendet auch eine laufende Pause)",
    "Ctrl + R  or  Ctrl + N": "Strg + R  oder  Strg + N",
    "Re-roll (regenerate) the selected song":
        "Den gewählten Titel neu würfeln",
    "Ctrl + S": "Strg + S",
    "Save the focused playlist / wishlist as M3U":
        "Die aktive Playlist / Wunschliste als M3U speichern",
    "Ctrl + Shift + S": "Strg + Umschalt + S",
    "Save the whole session state (decks, wishlists, layout)":
        "Den ganzen Sitzungsstand speichern (Decks, Wunschlisten, Anordnung)",
    "Ctrl + Z  /  Ctrl + Y": "Strg + Z  /  Strg + Y",
    "Undo / redo (also Ctrl + Shift + Z)":
        "Rückgängig / Wiederholen (auch Strg + Umschalt + Z)",
    "Ctrl + X  or  Ctrl + W": "Strg + X  oder  Strg + W",
    "Close the active dialog or the preview mini player":
        "Den aktiven Dialog oder den Vorhör-Miniplayer schließen",
    "Del": "Entf",
    "Remove the selected rows (wishlist) / empty the selected heat slots "
    "(deck)":
        "Die gewählten Zeilen entfernen (Wunschliste) / die gewählten "
        "Gruppenplätze leeren (Deck)",
    "Del  with nothing selected": "Entf  ohne Auswahl",
    "Clear that whole playlist / wishlist (confirmed) — same when every "
    "song is selected at once":
        "Diese ganze Playlist / Wunschliste leeren (mit Rückfrage) — genauso, "
        "wenn alle Titel auf einmal gewählt sind",
    "Clear the focused playlist / wishlist (confirmed), wherever the cursor is":
        "Die gewählte Playlist / Wunschliste leeren (mit Rückfrage), egal wo "
        "der Cursor steht",
    "Ctrl + Shift + Del": "Strg + Umschalt + Entf",
    "Ctrl + Del": "Strg + Entf",
    "Dynamic deck: remove the whole heat under the cursor (on a ↳ backup "
    "row: just that backup)":
        "Dynamisches Deck: die ganze Gruppe unter dem Zeiger entfernen (auf "
        "einer ↳ Reserve-Zeile: nur diese Reserve)",
    "Ctrl + M": "Strg + M",
    "Dynamic deck or free running order: mark / unmark the selected "
    "song(s) for potential replace (❗ orange). Ctrl + 1 does the same, "
    "but only while the 🎛 cartwall is hidden — the wall claims that key "
    "for its first pad":
        "Dynamisches Deck oder freier Ablauf: die gewählten Titel zum "
        "möglichen Austausch markieren (❗ orange) oder die Markierung wieder "
        "wegnehmen. Strg + 1 macht dasselbe, aber nur solange die 🎛 Cartwall "
        "ausgeblendet ist — die Wall nimmt diese Taste für ihr erstes Pad",
    "F2  in the 📅 tournament tree": "F2  im 📅 Turnierbaum",
    "Rename the entry under the cursor (Del removes it)":
        "Den Eintrag unter dem Zeiger umbenennen (Entf entfernt ihn)",
    "Ctrl + A  in 🏆 Tournaments": "Strg + A  in 🏆 Turniere",
    "Mark every slot of the folder, or every entry of the tree — Del and a "
    "drag then take them all":
        "Alle Slots des Ordners markieren, oder alle Einträge des Baums — Entf "
        "und Ziehen nehmen dann alle mit",
    "Click a star in the ★ column": "Klick auf einen Stern in ★",
    "Rate the title; click the star the rating ends on to clear it":
        "Den Titel bewerten; ein Klick auf den letzten vergebenen Stern löscht "
        "die Bewertung",
    "Ctrl + F": "Strg + F",
    "Find a title in the focused list (repeat to step to the next match)":
        "Einen Titel in der aktiven Liste suchen (nochmal drücken springt zum "
        "nächsten Treffer)",
    "Esc  in the 🖥 presenter window": "Esc  im 🖥 Moderations-Fenster",
    "This cheat sheet": "Diese Übersicht",
    "🖱  Mouse": "🖱  Maus",
    "Click a round / dance header":
        "Klick auf eine Überschrift",
    "Collapse or expand that section":
        "Diesen Abschnitt ein- oder ausklappen",
    "Double-click a deck title": "Doppelklick auf Deck-Namen",
    "Rename the playlist / wishlist": "Die Playlist / Wunschliste umbenennen",
    "▾ / ▸ arrow in a deck header": "▾ / ▸ in einer Deck-Kopfzeile",
    "Fold the deck to a header tab (click the tab to reopen)":
        "Das Deck auf einen Kopfzeilen-Reiter einklappen (Klick auf den "
        "Reiter öffnet es wieder)",
    "Drag a row": "Eine Zeile ziehen",
    "Move a song to another slot, deck, wishlist — or drop it into "
    "Explorer / UltraMixer":
        "Einen Titel auf einen anderen Platz, in ein anderes Deck oder eine "
        "Wunschliste ziehen — oder in den Explorer / UltraMixer ablegen",
    "Drag a dance header": "Eine Tanz-Überschrift ziehen",
    "Reorder the dance columns of a static deck":
        "Die Tanzspalten eines statischen Decks umsortieren",
    "Right-click ▸ 🔍 Find a title": "Rechtsklick ▸ 🔍 Titel suchen",
    "Jump to a song by name; repeat to step to the next match":
        "Zu einem Titel per Name springen; nochmal für den nächsten Treffer",
    "Ctrl + drag onto a filled slot":
        "Strg + Ziehen auf einen Platz",
    "Dynamic deck: replace the song in that slot with the dragged one":
        "Dynamisches Deck: den Titel auf diesem Platz durch den gezogenen "
        "ersetzen",
    "Drop a file from outside": "Eine Datei von außen ablegen",
    "Replace a slot / add to a wishlist (.m3u on a deck imports it)":
        "Einen Platz ersetzen / zu einer Wunschliste hinzufügen (eine .m3u "
        "auf einem Deck wird importiert)",
    "▶ or Space on a 📚 library row":
        "▶ / Leertaste in 📚 Bibliothek",
    "Preview that track in the mini player":
        "Diesen Titel im Miniplayer vorhören",
    "Double-click a 📚 library row":
        "Doppelklick in 📚 Bibliothek",
    "Open the track in your external audio player":
        "Den Titel im externen Audioplayer öffnen",
    "▶ / ■ in a row": "▶ / ■ in einer Zeile",
    "Play / stop exactly that song": "Genau diesen Titel abspielen / stoppen",
    "↺ in a row / header": "↺ in einer Zeile / Überschrift",
    "Re-roll that song / every song of the dance or round":
        "Diesen Titel neu würfeln / alle Titel des Tanzes oder der Runde",
    "Drop files on a pad": "Dateien auf ein Pad ablegen",
    "Assign that sample — a multi-select fills the free pads after it (an "
    "empty pad can also be clicked to browse)":
        "Dieses Sample zuweisen — eine Mehrfachauswahl füllt die freien Pads "
        "dahinter (ein leeres Pad lässt sich auch anklicken, um zu suchen)",
    "Click a pad": "Klick auf ein Pad",
    "Fire it over the running music; click again to fade it out":
        "Es über die laufende Musik starten; nochmal klicken blendet es aus",
    "Ctrl+1 … Ctrl+9": "Strg+1 … Strg+9",
    "Fire the first nine pads of the page on screen (works from anywhere "
    "while the wall is shown, and takes Ctrl + 1 away from the mark "
    "shortcut above)":
        "Die ersten neun Pads der angezeigten Seite starten (funktioniert von "
        "überall, solange die Wall zu sehen ist, und nimmt Strg + 1 dem "
        "Markieren-Kürzel oben weg)",
    "Right-click a pad": "Rechtsklick auf ein Pad",
    "🎨 colour straight away, or Settings… for label, volume, its own key, "
    "🔁 endless repeat and whether it ducks the music":
        "🎨 Farbe direkt, oder Einstellungen… für Beschriftung, Lautstärke, "
        "eigene Taste, 🔁 Endlosschleife und ob es die Musik absenkt",
    "Drag a pad onto another": "Ein Pad auf ein anderes ziehen",
    "Swap the two pads": "Die beiden Pads tauschen",
    "Stop every pad (same as ⏹ Stop all)":
        "Alle Pads stoppen (dasselbe wie ⏹ Alle stoppen)",
    # ── 🎛 the right-click on a pad: three captions, a count, eight swatches ──
    "⚙  Settings…": "⚙  Einstellungen…",
    "🎨  Colour": "🎨  Farbe",
    "🗑  Clear pad": "🗑  Pad leeren",
    "  (%s pads)": "  (%s Pads)",
    # Display only — the signal carries the colour value, not the name.
    "Wall default": "Cartwall-Standard",
    "Grey": "Grau",
    "Green": "Grün",
    "Red": "Rot",
    "Olive": "Oliv",
    "Purple": "Violett",
    "Amber": "Bernstein",
    "White": "Weiß",
    # ── menu captions that only show in one state, so they hid in a ternary ──
    "📂  Show in Explorer (not saved as a file yet)":
        "📂  Im Explorer zeigen (noch nicht als Datei gespeichert)",
    # "Unfold this playlist" is up there already — the fold tab's own tooltip.
    "Unfold this wishlist": "Diese Wunschliste aufklappen",
    "Fold to a tab": "Auf einen Reiter einklappen",
    "🔁  Mark for potential replace\tCtrl+M":
        "🔁  Für möglichen Austausch markieren\tStrg+M",
    "🔁  Unmark (potential replace)\tCtrl+M":
        "🔁  Markierung wegnehmen (möglicher Austausch)\tStrg+M",
    "➕  Create new round": "➕  Neue Runde anlegen",
    # The round the new one goes behind — a name, so it stays as it is.
    "➕  Insert new round after %s": "➕  Neue Runde nach %s einfügen",
    "🗑  Remove %s from this round (keep other dances)":
        "🗑  %s aus dieser Runde entfernen (andere Tänze bleiben)",
    "🗑  Remove %s from all rounds and heats":
        "🗑  %s aus allen Runden und Gruppen entfernen",
    "🔒  Back to a planned grid": "🔒  Zurück zum geplanten Raster",
    "🔒  Switch to static mode": "🔒  In den statischen Modus wechseln",
    "🔓  Switch to dynamic mode": "🔓  In den dynamischen Modus wechseln",
    "🧹  Empty this wishlist": "🧹  Diese Wunschliste leeren",
    "Columns in every playlist": "Spalten in jeder Playlist",
    "Columns in every wishlist": "Spalten in jeder Wunschliste",
    "Columns in every party list": "Spalten in jeder Partyliste",
    # ── the Σ bar under a deck ──
    "Σ  %d song": "Σ  %d Lied",
    "Σ  %d songs": "Σ  %d Lieder",
    # The second line of the same badge: a track of no known dance.
    "other": "andere",
    # ── the Pop column, where a track nobody has played yet says a word ──
    # Spelled like the ✦ filter that hides everything else ("  ·  ✦ %d neu").
    "✦new": "✦neu",
    "new": "neu",
    # ── 🏆 the tournament pane's track list ──
    # This one used to BE "Runde", in a row of otherwise English headers.
    "Round": "Runde",
    # ── 🔈 which recorded voice announces the dance ──
    # The combo is read back by data ('female'/'male'/'random'), never by
    # text, so the captions are free to translate.
    "Female": "Weiblich",
    "Male": "Männlich",
    "Mixed": "Gemischt",
    # ── 🎉 the party check: the report, and every sentence in it ──
    # Built by `%` in planner/party_check.py, so none of them is a key the
    # hook could have found on its own — they ask for themselves.
    #
    # No article in front of a dance: `der` Tango, `die` Rumba and `der`
    # Langsame Walzer all differ and the name arrives through a %s, so a
    # template that carried one would be wrong for half the catalogue.
    "🎉  Party check": "🎉  Party-Check",
    "Check the party list — rounds, the late WW / PD rules,\n"
    "duplicates, takt and over-long titles.":
        "Die Partyliste prüfen — Runden, die Regeln „Wiener Walzer spät“ /\n"
        "„Paso Doble spät“, Doppelte, Takt und zu lange Titel.",
    "Party list": "Partyliste",
    "🎉 <b>%s</b> — %d titles, 1 finding":
        "🎉 <b>%s</b> — %d Titel, 1 Befund",
    "🎉 <b>%s</b> — %d titles, %d findings":
        "🎉 <b>%s</b> — %d Titel, %d Befunde",
    "✅  Nothing to report — the list reads like one the "
    "party builder would have made.":
        "✅  Nichts zu melden — die Liste liest sich wie eine, die der "
        "Party-Generator gebaut hätte.",
    "↻  Check again": "↻  Nochmal prüfen",
    # The group each finding is filed under. The Takt heading is the same
    # word in both languages and has no entry, the way a key that equals
    # its value never does.
    "🔁 Rounds": "🔁 Runden",
    "⏳ Spacing": "⏳ Abstände",
    "👯 Duplicates": "👯 Doppelte",
    "⏱ Length": "⏱ Länge",
    # The jump link every finding ends on.
    "row %d": "Zeile %d",
    # The rounds of a section, as a whole phrase. The bare word "Latin" is the
    # style name the combos are read back by — translating THAT would break
    # style selection, which is why the sentences substitute this instead.
    "Standard rounds": "Standardrunden",
    "Latin rounds": "Lateinrunden",
    "Social rounds": "Socialrunden",
    # 🔁 Runden
    "“%s” is %d title long, not 3 — from ":
        "„%s“ ist nur %d Titel lang statt 3 — ab ",
    "“%s” is %d titles long, not 3 — from ":
        "„%s“ ist nur %d Titel lang statt 3 — ab ",
    "a round": "eine Runde",
    "the Samba plays two %s running, the second at ":
        "die Samba läuft in zwei %s hintereinander, die zweite bei ",
    "“%s” opens the section with %s, not %s — from ":
        "„%s“ eröffnet die Sektion mit %s statt mit %s — ab ",
    "nothing": "nichts",
    "two %s run back to back — “%s” starts at ":
        "zwei %s laufen direkt hintereinander — „%s“ beginnt bei ",
    ", with no round of the other section between them.":
        ", ohne eine Runde der anderen Sektion dazwischen.",
    "the %s never plays — %d %s and not one of them.":
        "%s kommt nie vor — in %d %s kein einziges Mal.",
    "the %s sits out %d %s running, from ":
        "%s setzt %d %s hintereinander aus, ab ",
    # ⏳ Abstände. The two option names are spelled the way their check
    # boxes are ("„Wiener Walzer spät“", "„Paso Doble spät“).
    "the Wiener Walzer opens the evening at ":
        "der Wiener Walzer eröffnet den Abend bei ",
    " — “late WW” holds it back until %d titles have played.":
        " — „Wiener Walzer spät“ hält ihn zurück, bis %d Titel "
        "gelaufen sind.",
    "a Paso Doble plays at ": "ein Paso Doble läuft bei ",
    " — “late PD” holds the first one back until %d titles have played.":
        " — „Paso Doble spät“ hält den ersten zurück, bis %d Titel "
        "gelaufen sind.",
    "two Paso Dobles sit %d Latin round apart, the second at ":
        "zwischen zwei Paso Dobles liegt nur %d Lateinrunde, der zweite bei ",
    "two Paso Dobles sit %d Latin rounds apart, the second at ":
        "zwischen zwei Paso Dobles liegen nur %d Lateinrunden, der zweite "
        "bei ",
    " — the rule is %d.": " — die Regel sagt %d.",
    # The doubles, the takt and the length
    "“%s” plays %d times, at ": "„%s“ läuft %d mal, bei ",
    "“%s” and “%s” look like the same song, at ":
        "„%s“ und „%s“ sehen nach demselben Lied aus, bei ",
    "“%s” is a %s at T%d, outside T%d–T%d — ":
        "„%s“ ist ein %s mit T%d, außerhalb von T%d–T%d — ",
    "“%s” runs %d:%02d, past %d:%02d — ":
        "„%s“ läuft %d:%02d, länger als %d:%02d — ",
    # ── 📚 the library pane ──
    # The filter captions that a number goes into are built by `%` at the
    # site, so the template is the key. "— Standard —" is the same word in
    # both languages and gets NO entry, the way a key equal to its value
    # never does.
    "Class %s": "Klasse %s",
    "★ Rarely (1–%d)": "★ Selten (1–%d)",
    "★ Proven (≥%d)": "★ Bewährt (≥%d)",
    "Filter by how the track was used so far:\n"
    "✦ never — in none of your playlists\n"
    "★ rarely / proven — in 1–%d vs. %d+ of them\n"
    "📅 not since — played, but the newest playlist\n"
    "carrying it is that old (the year comes from the\n"
    "playlist's path; undated lists don't count as old).":
        "Filtern danach, wie der Titel bisher benutzt wurde:\n"
        "✦ nie — in keiner deiner Playlists\n"
        "★ selten / bewährt — in 1–%d gegenüber %d+ davon\n"
        "📅 seit — gelaufen, aber die neueste Playlist\n"
        "damit ist so alt (das Jahr kommt aus dem Pfad der\n"
        "Playlist; undatierte Listen zählen nicht als alt).",
    # The five non-tournament folders (planner/models.py LIBRARY_CATEGORIES).
    # The combo is read back by `currentData()` everywhere, so the caption is
    # free to change.
    "🎄 Seasonal / Christmas": "🎄 Saison / Weihnachten",
    "🎺 Anthems": "🎺 Hymnen",
    "🎶 Background / non-dance": "🎶 Hintergrund / kein Tanz",
    "⏱️ Wrong tempo / not tournament":
        "⏱️ Falsches Tempo / kein Turnier",
    "👥 Duplicates / raw versions":
        "👥 Doppelte / Rohfassungen",
    # The count beside the 📚 header.
    "(%d/%d tracks)": "(%d/%d Titel)",
    # The header's tick list: the columns whose caption is a glyph.
    "▶  Play": "▶  Abspielen",
    "⏱  Length": "⏱  Länge",
    "★  Rating": "★  Bewertung",
    # Cell tooltips. QTableWidgetItem is neither a QWidget nor a patched
    # constructor, so these needed an explicit t() at the site before the
    # entry could do anything — two of them were already here and unused.
    "Class tags from the MP3 comment field":
        "Klassen-Tags aus dem MP3-Kommentarfeld",
    "Newest playlist carrying this track":
        "Neueste Playlist mit diesem Titel",
    "Never played": "Nie gelaufen",
    "Played, but none of those playlists is dated":
        "Gelaufen, aber keine dieser Playlists ist datiert",
    # ── ⚗ the analysis tab of ⚙ Settings ──
    # Its 🐘 Heavy sibling was German already; what stayed English here is
    # everything a count or an availability check goes into, because that
    # makes the finished string unique and no catalog can hold it.
    "⚡ Light — librosa/ffmpeg, works in every install (lite build)":
        "⚡ Leicht — librosa/ffmpeg, läuft in jeder Installation "
        "(Lite-Build)",
    "⚡ Light — ffmpeg, works in every install (player build)":
        "⚡ Leicht — ffmpeg, läuft in jeder Installation (Player-Build)",
    "🔬  Analyze audio (timbre) — %d files to do":
        "🔬  Audio analysieren (Timbre) — %d Dateien offen",
    "🔬  Re-analyze audio (timbre)  ✓ all cached":
        "🔬  Audio neu analysieren (Timbre)  ✓ alles im Cache",
    # The six grey coverage captions. `_index_label` glues the prefix to the
    # coverage, so the PREFIX is the key and the coverage stays data.
    "🎚️  librosa indexed": "🎚️  librosa indiziert",
    "🎼  Chroma indexed": "🎼  Chroma indiziert",
    "📊  Loudness measured": "📊  Lautheit gemessen",
    "🐂  PD highlights detected": "🐂  PD-Höhepunkte erkannt",
    "🔇  Silences probed": "🔇  Stillen geprüft",
    "🧠  OpenL3 indexed": "🧠  OpenL3 indiziert",
    # A model that is not there says so — glued on, in both places, so the
    # suffix is its own key.
    "🧠  OpenL3 'sounds-alike' index":
        "🧠  OpenL3-Index „klingt ähnlich“",
    "🎙️  Analyze vocals (Demucs)…":
        "🎙️  Gesang analysieren (Demucs)…",
    "  – not installed": "  – nicht installiert",
    # 🎛 The two grey lines under the play sets.
    "The values a heat is run with — pressed to get back to them "
    "after a party list has pulled the panel somewhere else.":
        "Die Werte, mit denen eine Runde läuft — gedrückt, um sie "
        "zurückzuholen, nachdem eine Partyliste das Panel woandershin "
        "gezogen hat.",
    "Applied by itself as soon as you play from the 🤸 Eintanzen / "
    "party list, and switched back when a tournament deck takes over.":
        "Wird von selbst angewandt, sobald du aus der 🤸 Eintanzen-/"
        "Partyliste abspielst, und zurückgeschaltet, wenn ein Turnier-Deck "
        "übernimmt.",
    # 🔇 The sound-card tooltip. The idle seconds went in through an
    # f-string, which is why the caption above it was German and this was not.
    "An onboard sound card un-mutes its output stage the moment an app\n"
    "opens it, and the amplifier carries that hiss across the hall — you\n"
    "hear it start with the app and stop when it closes, whether or not\n"
    "anything is playing.\n\n"
    "Handing the device back after %.0f s of silence takes it "
    "away. The cost is the soft click the card makes re-opening it\n"
    "for the next title, so only switch this on if you hear the hiss.":
        "Eine Onboard-Soundkarte hebt die Stummschaltung ihrer Ausgangsstufe\n"
        "in dem Moment auf, in dem eine App sie öffnet, und der Verstärker\n"
        "trägt dieses Rauschen durch den ganzen Saal — du hörst es mit der\n"
        "App anfangen und mit ihr aufhören, ob gerade etwas läuft oder nicht.\n\n"
        "Das Gerät nach %.0f s Stille zurückzugeben nimmt es weg. Der Preis "
        "ist das leise Klacken der Karte beim erneuten Öffnen\n"
        "für den nächsten Titel, schalte das also nur ein, wenn du das "
        "Rauschen hörst.",
    # ── Toasts built at runtime (i18n.t + %) ──────────────────────────────
    "⚠️  Not read — %s":
        "⚠️  Nicht gelesen — %s",
    "🧹  Removed %d title already in another playlist":
        "🧹  %d Titel entfernt — stand schon in einer anderen Playlist",
    "🧹  Removed %d titles already in another playlist":
        "🧹  %d Titel entfernt — standen schon in einer anderen Playlist",
    "🔁  Replaced %d duplicate":
        "🔁  %d Duplikat ersetzt",
    "🔁  Replaced %d duplicates":
        "🔁  %d Duplikate ersetzt",
    "⚠  %d duplicate was no longer in its playlist — left as it is":
        "⚠  %d Duplikat stand nicht mehr in seiner Playlist — nicht geändert",
    "⚠  %d duplicates were no longer in their playlist — left as they are":
        "⚠  %d Duplikate standen nicht mehr in ihrer Playlist — nicht geändert",
    "💾  Saved → %s":
        "💾  Gespeichert → %s",
    "💾  Saved %d competition playlist(s)":
        "💾  %d Turnier-Playlist(s) gespeichert",
    "📅  Planned %d competition(s) into %d deck(s)":
        "📅  %d Turnier(e) in %d Deck(s) geplant",
    "📂  Added %d track(s) from %d file(s)":
        "📂  %d Titel aus %d Datei(en) hinzugefügt",
    "📂  Imported %d playlists into %d free slot(s)":
        "📂  %d Playlists in %d freie Plätze importiert",
    "%d extra final-round track(s) kept as backups (stacked under their dance)":
        "%d zusätzliche Finaltitel als Reserve behalten (unter ihrem Tanz gestapelt)",
    "%s line(s) name a file the list already had (imported again, not skipped)":
        "%s Zeile(n) nennen eine Datei, die schon in der Liste war (erneut importiert, nicht übersprungen)",
    "%s file(s) not found on disk":
        "%s Datei(en) nicht auf dem Datenträger gefunden",
    "%s track(s) with no recognizable dance (skipped)":
        "%s Titel ohne erkennbaren Tanz (übersprungen)",
    "%s track(s) left out — no round/dance column to put them in":
        "%s Titel weggelassen — keine Runden-/Tanzspalte, in die sie passen",
    "%s of %s songs":
        "%s von %s Titeln",
    "%s songs":
        "%s Titel",
    "📂 Imported %s · %d round(s) · %d dance(s) (markers)":
        "📂 %s importiert · %d Runde(n) · %d Tanz/Tänze (Marker)",
    "📂 Imported %s · %d round(s) · %d dance(s) (auto-detected)":
        "📂 %s importiert · %d Runde(n) · %d Tanz/Tänze (automatisch erkannt)",
    "📂 Imported %s · %d round(s)":
        "📂 %s importiert · %d Runde(n)",
    "⚠ %d row(s) marked red — play-length / takt issues (hover a red title for details)":
        "⚠ %d Zeile(n) rot markiert — Probleme mit Spieldauer / Takt (Maus auf einen roten Titel zeigt die Details)",
    "🏷  %s is not on disk any more":
        "🏷  %s ist nicht mehr auf dem Datenträger",
    "🏷  Couldn't re-read %s: %s":
        "🏷  %s konnte nicht neu gelesen werden: %s",
    "★  Couldn't store the rating: %s":
        "★  Die Bewertung konnte nicht gespeichert werden: %s",
    "🏷  Couldn't store the tags: %s":
        "🏷  Die Tags konnten nicht gespeichert werden: %s",
    "🏷  Edit tags…": "🏷  Tags bearbeiten…",
    "🏷  Edit tags of %d tracks…": "🏷  Tags von %d Titeln bearbeiten…",
    "🏷  Edit tags": "🏷  Tags bearbeiten",
    "🏷  Edit tags of %d tracks": "🏷  Tags von %d Titeln bearbeiten",
    "%d tracks — a field they differ in is kept per track until you change it.":
        "%d Titel — ein Feld, in dem sie sich unterscheiden, bleibt je Titel "
        "erhalten, bis du es änderst.",
    "keep (differs per track)": "beibehalten (je Titel verschieden)",
    "no stars": "keine Sterne",
    "Stars:": "Sterne:",
    "Classes:": "Klassen:",
    "None ticked = suits every class.": "Keine angehakt = passt zu jeder Klasse.",
    "Instrumental (no vocals)": "Instrumental (ohne Gesang)",
    "differs per track — typing here replaces them all":
        "je Titel verschieden — eine Eingabe hier ersetzt sie bei allen",
    "e.g. classic, vocal_f": "z. B. classic, vocal_f",
    "Markers:": "Marker:",
    "Add this marker, or take it out again":
        "Diesen Marker hinzufügen oder wieder herausnehmen",
    "↺  Back to the file's tags": "↺  Zurück zu den Tags der Datei",
    "Forget every change made here in the app — stars, classes,\n"
    "instrumental, markers and Custom read from the MP3 again.":
        "Alle hier in der App gemachten Änderungen vergessen — Sterne, Klassen,\n"
        "Instrumental, Marker und Custom werden wieder aus der MP3 gelesen.",
    "Filled from the MP3 tag %s. What is typed here wins over it.":
        "Gefüllt aus dem MP3-Tag %s. Was hier eingegeben wird, hat Vorrang.",
    "Kept in the app only. Right-click a column header to fill it from an MP3 tag.":
        "Nur in der App gespeichert. Ein Rechtsklick auf einen Spaltenkopf füllt "
        "es aus einem MP3-Tag.",
    "Changed in the Custom field on the first tab":
        "Wird im Feld Custom auf dem ersten Reiter geändert",
    "Map Custom to an MP3 tag…": "Custom einem MP3-Tag zuordnen…",
    "🏷  Custom field": "🏷  Feld Custom",
    "🏷  Fill Custom from this tag": "🏷  Custom aus diesem Tag füllen",
    "In none of the %d sampled MP3s": "In keiner der %d geprüften MP3s",
    "In %d of %d sampled MP3s, e.g. “%s”": "In %d von %d geprüften MP3s, z. B. „%s“",
    "The Custom column shows this tag of each MP3. A value typed in the "
    "🏷 editor wins over it, and on Save it can be written into it.":
        "Die Spalte Custom zeigt diesen Tag jeder MP3. Ein im 🏷-Editor "
        "eingegebener Wert hat Vorrang und kann beim Speichern hineingeschrieben werden.",
    "In the app only": "Nur in der App",
    "Frame:": "Feld:",
    "Description:": "Beschreibung:",
    "e.g. ultramixer_last_played": "z. B. ultramixer_last_played",
    "Custom — a free field per track, typed in the 🏷 editor.\n"
    "Right-click the header to fill it from an MP3 tag.":
        "Custom — ein freies Feld je Titel, eingegeben im 🏷-Editor.\n"
        "Rechtsklick auf den Spaltenkopf füllt es aus einem MP3-Tag.",
    "Custom goes into the tag it is mapped to.":
        "Custom kommt in den Tag, dem es zugeordnet ist.",
    "Extended tags": "Erweiterte Tags",
    "Every frame of the MP3, written straight into the file on Save. "
    "The fields of the form on the first tab are changed there.":
        "Jedes Feld der MP3, beim Speichern direkt in die Datei geschrieben. "
        "Die Felder des Formulars auf dem ersten Reiter werden dort geändert.",
    "Changed in the form on the first tab": "Wird im Formular auf dem ersten Reiter geändert",
    "In the MP3 file": "In der MP3-Datei",
    "In the app": "In der App",
    "Only for MP3 files on disk": "Nur für MP3-Dateien auf dem Datenträger",
    "Covers differ": "Cover unterschiedlich",
    "Cover can't be shown": "Cover lässt sich nicht anzeigen",
    "No cover": "Kein Cover",
    "< keep >": "< beibehalten >",
    "< blank >": "< leer >",
    # The form's labels (gui.tag_edit_dialog._FORM_ROWS); Album:, Track:,
    # Genre: and Replay Gain: are the same in German.
    "Title:": "Titel:",
    "Artist:": "Interpret:",
    "Year:": "Jahr:",
    "Comment:": "Kommentar:",
    "Album artist:": "Album-Interpret:",
    "Composer:": "Komponist:",
    "Disc number:": "CD-Nummer:",
    "Description": "Beschreibung",
    "Value": "Wert",
    "➕  Add field": "➕  Feld hinzufügen",
    "Only for one track at a time": "Nur für einen Titel auf einmal",
    "Only for an MP3 file on disk": "Nur für eine MP3-Datei auf dem Datenträger",
    "Couldn't read the MP3 tags: %s": "Die MP3-Tags konnten nicht gelesen werden: %s",
    "Can only be removed, not edited here": "Lässt sich hier nur entfernen, nicht bearbeiten",
    "🏷  %s is in the player — stop it to write its MP3 tags":
        "🏷  %s ist im Player — erst stoppen, dann lassen sich die MP3-Tags schreiben",
    "🏷  Couldn't write the MP3 tags: %s":
        "🏷  Die MP3-Tags konnten nicht geschrieben werden: %s",
    "🏷  Write into the MP3?": "🏷  In die MP3 schreiben?",
    "Also write %s into the MP3 file?": "%s auch in die MP3-Datei schreiben?",
    "Also write %s into the %d MP3 files?": "%s auch in die %d MP3-Dateien schreiben?",
    "Stars go into the Windows rating; classes, instrumental and markers "
    "into the comment, where other programs see them too. With No they "
    "stay in the app only.":
        "Sterne kommen in die Windows-Bewertung, Klassen, Instrumental und Marker "
        "in den Kommentar, wo auch andere Programme sie sehen. Bei Nein bleiben "
        "sie nur in der App.",
    "stars": "Sterne",
    "custom": "Custom",
    # ID3 frame names (planner.id3_frames.FRAME_NAMES); Title/Artist exist above.
    "Custom text": "Eigener Text",
    "Comment": "Kommentar",
    "Custom link": "Eigener Link",
    "Rating": "Bewertung",
    "Picture": "Bild",
    "Private data": "Private Daten",
    "Embedded object": "Eingebettetes Objekt",
    "CD identifier": "CD-Kennung",
    "Unique file id": "Eindeutige Datei-ID",
    "Lyrics": "Liedtext",
    "Play count": "Wiedergabezähler",
    "Volume adjustment": "Lautstärkeanpassung",
    "Grouping": "Gruppierung",
    "Subtitle": "Untertitel",
    "Album artist": "Album-Interpret",
    "Conductor": "Dirigent",
    "Remixed by": "Remix von",
    "Key": "Tonart",
    "Composer": "Komponist",
    "Lyricist": "Texter",
    "Track number": "Titelnummer",
    "Disc number": "CD-Nummer",
    "Year": "Jahr",
    "Recording date": "Aufnahmedatum",
    "Publisher": "Verlag",
    "Language": "Sprache",
    "Length (ms)": "Länge (ms)",
    "Encoded by": "Kodiert von",
    "Encoder settings": "Encoder-Einstellungen",
    "Media type": "Medientyp",
    "Grouping (iTunes)": "Gruppierung (iTunes)",
    "🏷  %s: tags unchanged":
        "🏷  %s: Tags unverändert",
    "⚠  Track no longer in any open deck":
        "⚠  Der Titel ist in keinem offenen Deck mehr",
    "🗑  Removed “%s” from 1 slot — Ctrl+Z undoes":
        "🗑  „%s“ aus 1 Platz entfernt — Strg+Z macht es rückgängig",
    "🗑  Removed “%s” from %d slots — Ctrl+Z undoes":
        "🗑  „%s“ aus %d Plätzen entfernt — Strg+Z macht es rückgängig",
    "↺  Replaced “%s” with “%s” in 1 slot — Ctrl+Z undoes":
        "↺  „%s“ durch „%s“ ersetzt, an 1 Platz — Strg+Z macht es rückgängig",
    "↺  Replaced “%s” with “%s” in %d slots — Ctrl+Z undoes":
        "↺  „%s“ durch „%s“ ersetzt, an %d Plätzen — Strg+Z macht es rückgängig",
    "🧭  Fixed %d track path":
        "🧭  %d Titelpfad repariert",
    "🧭  Fixed %d track paths":
        "🧭  %d Titelpfade repariert",
    "🧭  Moved %d track onto the Referenzpfad":
        "🧭  %d Titel auf den Referenzpfad verschoben",
    "🧭  Moved %d tracks onto the Referenzpfad":
        "🧭  %d Titel auf den Referenzpfad verschoben",
    "🧭  Fixed 1 path in 1 file":
        "🧭  1 Pfad in 1 Datei repariert",
    "🧭  Fixed %d paths in 1 file":
        "🧭  %d Pfade in 1 Datei repariert",
    "🧭  Fixed %d paths in %d files":
        "🧭  %d Pfade in %d Dateien repariert",
    "🧹  Removed %d track(s) already in a playlist":
        "🧹  %d Titel entfernt — schon in einer Playlist",
    "↺  No other %s near the end of the list":
        "↺  Am Listenende steht kein weiterer Titel für %s",
    "🔍  No title matching “%s”":
        "🔍  Kein Titel passt zu „%s“",
    "🔁  Marked %d track for replace":
        "🔁  %d Titel zum Ersetzen markiert",
    "🔁  Marked %d tracks for replace":
        "🔁  %d Titel zum Ersetzen markiert",
    "🔁  Unmarked %d track":
        "🔁  Markierung von %d Titel entfernt",
    "🔁  Unmarked %d tracks":
        "🔁  Markierung von %d Titeln entfernt",
    "🧹  Removed %d duplicate title":
        "🧹  %d doppelten Titel entfernt",
    "🧹  Removed %d duplicate titles":
        "🧹  %d doppelte Titel entfernt",
    "⭐  Moved %d track(s) to the wishlist":
        "⭐  %d Titel auf die Wunschliste verschoben",
    "⭐  Added %d track(s) to the wishlist":
        "⭐  %d Titel zur Wunschliste hinzugefügt",
    "  ·  🧹 %d already in a playlist removed":
        "  ·  🧹 %d schon in einer Playlist, entfernt",
    "➕  Added %d track(s)":
        "➕  %d Titel hinzugefügt",
    "➕  Added %d track(s) — rounds re-cut":
        "➕  %d Titel hinzugefügt — Runden neu aufgeteilt",
    "🎯  Placed %d track(s)":
        "🎯  %d Titel platziert",
    "  (%d skipped — no free slot)":
        "  (%d übersprungen — kein freier Platz)",
    "… plus %d more":
        "… und %d weitere",
    "🔁  Replaced “%s” with “%s”":
        "🔁  „%s“ durch „%s“ ersetzt",
    "⚠  “%s” is already in this playlist — not replaced":
        "⚠  „%s“ ist schon in dieser Playlist — nicht ersetzt",
    "🔁  Replaced %d track(s)":
        "🔁  %d Titel ersetzt",
    "🔁  Replaced %d, ➕ added %d track(s)":
        "🔁  %d ersetzt, ➕ %d Titel hinzugefügt",
    "  (%s — skipped)":
        "  (%s — übersprungen)",
    "%d already planned":
        "%d schon eingeplant",
    "%d with no dance":
        "%d ohne Tanz",
    "⚠  Couldn't tell what dance “%s” is — nothing added":
        "⚠  Welcher Tanz „%s“ ist, war nicht zu erkennen — nichts hinzugefügt",
    "⚠  “%s” is already in this playlist — nothing added":
        "⚠  „%s“ ist schon in dieser Playlist — nichts hinzugefügt",
    "Nothing added — %s":
        "Nichts hinzugefügt — %s",
    "TSO tempo equalize → on":
        "TSO-Tempoangleich → an",
    "TSO tempo equalize → off":
        "TSO-Tempoangleich → aus",
    "🎉  Party set — %s":
        "🎉  Party-Set — %s",
    "🏆  Tournament set — %s":
        "🏆  Turnier-Set — %s",
    "🎚  Own settings — %s":
        "🎚  Eigene Einstellungen — %s",
    "🎉  Party set applied":
        "🎉  Party-Set übernommen",
    "🏆  Tournament set back":
        "🏆  Zurück auf dem Turnier-Set",
    "🏆  Tournament set applied":
        "🏆  Turnier-Set übernommen",
    "nothing to change":
        "nichts zu ändern",
    ", running at %s":
        ", Uhr steht auf %s",
    "🕒  Timetable saved — %d entries":
        "🕒  Zeitplan gespeichert — %d Einträge",
    ", fading every %ss":
        ", Überblendung alle %s s",
    "play length → %s":
        "Spieldauer → %s",
    "fade-out → %s s":
        "Ausblenden → %s s",
    "auto-advance → on":
        "Automatisch zum nächsten Titel → an",
    "auto-advance → off":
        "Automatisch zum nächsten Titel → aus",
    "pause between songs → on":
        "Pause zwischen den Titeln → an",
    "pause between songs → off (no break music)":
        "Pause zwischen den Titeln → aus (keine Pausenmusik)",
    "equalize volume → on":
        "Lautstärke angleichen → an",
    "equalize volume → off":
        "Lautstärke angleichen → aus",
    "announce next dance → on":
        "Nächsten Tanz ansagen → an",
    "announce next dance → off":
        "Nächsten Tanz ansagen → aus",
    "double-click → starts the title":
        "Doppelklick → startet den Titel",
    "double-click → cues it":
        "Doppelklick → lädt ihn nur vor",
    "🐂 Paso Doble highlight stop → on":
        "🐂 Paso Doble: Stopp am Höhepunkt → an",
    "🐂 Paso Doble highlight stop → off":
        "🐂 Paso Doble: Stopp am Höhepunkt → aus",
    "📌 Session saved — decks, wishlists, 🎛 cartwall and layout.":
        "📌 Sitzung gespeichert — Decks, Wunschlisten, 🎛 Cartwall und Layout.",

    # ── Status bar and message boxes built at runtime (i18n.t + %) ───────────
    "Error generating playlist: %s":
        "Fehler beim Erzeugen der Playlist: %s",
    "  (iteration %d)":
        "  (Iteration %d)",
    " — from %s":
        " — aus %s",
    "Generated %d songs — %s, %s, %s":
        "%d Titel erzeugt — %s, %s, %s",
    "Skipped competition(s):":
        "Übersprungene Turniere:",
    "📅 Day plan: %d generated, %d skipped":
        "📅 Tagesplan: %d erzeugt, %d übersprungen",
    "📅 Day plan: %d competition(s) generated":
        "📅 Tagesplan: %d Turnier(e) erzeugt",
    "Seeding '%s' from past playlists…":
        "Befülle „%s“ aus früheren Playlists…",
    "Error reading past playlists: %s":
        "Fehler beim Lesen früherer Playlists: %s",
    "Generated %d songs — %s":
        "%d Titel erzeugt — %s",
    "Timbre similarity on for ↺ regenerations":
        "Timbre-Ähnlichkeit an für ↺ Neuwürfeln",
    "Timbre similarity off for ↺ regenerations":
        "Timbre-Ähnlichkeit aus für ↺ Neuwürfeln",
    "Building '%s' playlist…":
        "Erzeuge Playlist „%s“…",
    "No tracks matched theme '%s'.":
        "Kein Titel passt zum Thema „%s“.",
    "Decade themes require year tags in your MP3s; you can also map\nsongs to themes in themes.json (track_themes).":
        "Jahrzehnt-Themen brauchen Jahres-Tags in deinen MP3s; du kannst Titel\nauch in themes.json (track_themes) Themen zuordnen.",
    "No tracks matched '%s'.":
        "Kein Titel passt zu „%s“.",
    "Theme '%s' — %d tracks":
        "Thema „%s“ — %d Titel",
    "🤸 Building %s…":
        "🤸 Erzeuge %s…",
    "Building %s…":
        "Erzeuge %s…",
    "%s — %d tracks":
        "%s — %d Titel",
    "🔀 %s shuffled — %d tracks":
        "🔀 %s gemischt — %d Titel",
    "🤸 Eintanzen: nothing loadable from %s":
        "🤸 Eintanzen: nichts Ladbares in %s",
    "🎧 Nothing loadable from %s":
        "🎧 Nichts Ladbares in %s",
    "🤖 %d/%d slots filled by %s":
        "🤖 %d/%d Plätze gefüllt von %s",
    "🤖 %d tracks by %s":
        "🤖 %d Titel von %s",
    "%s not installed":
        "%s ist nicht installiert",
    "Build %s index":
        "%s-Index aufbauen",
    "Build the %s index over %s tracks from %s?":
        "Den %s-Index über %s Titel aus %s aufbauen?",
    "Analyses the melody/harmony of each track once (slow the first time, then cached).":
        "Analysiert Melodie/Harmonie jedes Titels einmal (beim ersten Mal langsam, danach gespeichert).",
    "Loads a neural model and embeds each track once (slow the first time, then cached).":
        "Lädt ein neuronales Modell und bettet jeden Titel einmal ein (beim ersten Mal langsam, danach gespeichert).",
    "Reuses anything already computed.":
        "Bereits Berechnetes wird wiederverwendet.",
    "Building %s index…":
        "%s-Index wird aufgebaut…",
    "%s indexing failed":
        "%s-Indizierung fehlgeschlagen",
    "All %d file(s) failed to embed.\n\nFirst error:\n%s\n\nSee the console log for the full traceback.":
        "Keine der %d Datei(en) ließ sich einbetten.\n\nErster Fehler:\n%s\n\nDen vollständigen Traceback zeigt das Konsolen-Log.",
    "unknown":
        "unbekannt",
    "%s indexing failed.":
        "%s-Indizierung fehlgeschlagen.",
    "%s index built — %d embedded, %d failed.":
        "%s-Index aufgebaut — %d eingebettet, %d fehlgeschlagen.",
    "%s index built — %d embedded.":
        "%s-Index aufgebaut — %d eingebettet.",
    "%s index ready":
        "%s-Index bereit",
    "Embedded %d track(s) (%d failed — see log).":
        "%d Titel eingebettet (%d fehlgeschlagen — siehe Log).",
    "Embedded %d track(s).":
        "%d Titel eingebettet.",
    "The %s method is now ready in the Similar-Tracks window.":
        "Die Methode %s ist jetzt im Fenster „Ähnliche Titel“ verfügbar.",
    "%s indexing cancelled — %d embedded so far (cached).":
        "%s-Indizierung abgebrochen — bisher %d eingebettet (gespeichert).",
    "Library error: %s":
        "Bibliotheksfehler: %s",
    "Analyzing %s …":
        "Analysiere %s …",
    "Only %s of %s tracks are analyzed so far (analysis is still running). Let analysis finish and try again.":
        "Erst %s von %s Titeln sind analysiert (die Analyse läuft noch). Lass die Analyse fertig laufen und versuch es dann noch einmal.",
    "Only %s of %s tracks are analyzed so far. Let analysis finish and try again.":
        "Erst %s von %s Titeln sind analysiert. Lass die Analyse fertig laufen und versuch es dann noch einmal.",
    "Global search is on but the repository isn't analyzed yet — open ⚙ Settings → “Build / refresh global audio index”.":
        "Die globale Suche ist an, aber das Repository ist noch nicht analysiert — öffne ⚙ Einstellungen → „Globalen Audio-Index aufbauen / auffrischen“.",
    "No tracks are analyzed yet — run 'Analyze Audio' first.":
        "Noch kein Titel ist analysiert — führe zuerst „Audio analysieren“ aus.",
    "All tracks are analyzed — this file just has no close match.":
        "Alle Titel sind analysiert — zu dieser Datei gibt es einfach keinen nahen Treffer.",
    "No similar tracks found in %s.":
        "Keine ähnlichen Titel gefunden (%s).",
    "Found %d similar to %s (%s)":
        "%d ähnliche Titel zu %s gefunden (%s)",
    "Global library ready from cache — %s files.":
        "Globale Bibliothek aus dem Cache geladen — %s Dateien.",
    "Global index: %s files, %s analyzed.":
        "Globaler Index: %s Dateien, %s analysiert.",
    "Scanning repository… %s/%s  (%s left)":
        "Repository wird gescannt… %s/%s  (%s übrig)",
    "Remove cached data of deleted music files and compact %s (%s MB)?":
        "Gespeicherte Daten gelöschter Musikdateien entfernen und %s (%s MB) verdichten?",
    "Feature vectors, embeddings and loudness of files that no longer exist on disk are removed for good (they would simply be re-analyzed if the files ever come back). Compacting can take a few minutes.":
        "Merkmalsvektoren, Embeddings und Lautheit von Dateien, die es auf der Platte nicht mehr gibt, werden endgültig entfernt (tauchen die Dateien wieder auf, werden sie einfach neu analysiert). Das Verdichten kann einige Minuten dauern.",
    "deleted tracks":
        "gelöschte Titel",
    "tag records":
        "Tag-Einträge",
    "feature vectors":
        "Merkmalsvektoren",
    "AI embeddings":
        "KI-Embeddings",
    "loudness values":
        "Lautheitswerte",
    "silence maps":
        "Stille-Karten",
    "vocal shares":
        "Gesangsanteile",
    "noise floors":
        "Grundrauschen",
    "playlist index entries":
        "Playlist-Indexeinträge",
    "stale index markers":
        "veraltete Index-Marker",
    "🧹 Database compacted: %s MB → %s MB (%s MB freed).":
        "🧹 Datenbank verdichtet: %s MB → %s MB (%s MB frei geworden).",
    "Removed rows: %s.":
        "Entfernte Zeilen: %s.",
    "none — everything is still in use":
        "keine — alles wird noch gebraucht",
    "Cleanup did not run:":
        "Das Aufräumen ist nicht gelaufen:",
    "📤  Export manual PD marks…": "📤  Manuelle PD-Marken exportieren…",
    "📥  Import manual PD marks…": "📥  Manuelle PD-Marken importieren…",
    "Export manual PD marks": "Manuelle PD-Marken exportieren",
    "Import manual PD marks": "Manuelle PD-Marken importieren",
    "Save the Paso Doble highlights you set by hand (🎯) to a file,\n"
    "to take them to another PC. Detected highlights are not included —\n"
    "🐂 finds those again by itself.":
        "Die von Hand gesetzten Paso-Doble-Highlights (🎯) in eine Datei speichern,\n"
        "um sie auf einen anderen PC mitzunehmen. Erkannte Highlights sind nicht dabei —\n"
        "die findet 🐂 von selbst wieder.",
    "Load hand-set Paso Doble highlights exported on another PC.\n"
    "They are matched by the music itself, not by the file path, and\n"
    "replace what this PC has for those tracks.":
        "Von Hand gesetzte Paso-Doble-Highlights laden, die auf einem anderen PC exportiert wurden.\n"
        "Zugeordnet wird über die Musik selbst, nicht über den Dateipfad, und\n"
        "sie ersetzen, was dieser PC für diese Titel hat.",
    "No Paso Doble highlight has been set by hand yet.":
        "Es wurde noch kein Paso-Doble-Highlight von Hand gesetzt.",
    "Could not write the file:":
        "Die Datei konnte nicht geschrieben werden:",
    "📤 %d hand-set Paso Doble highlight(s) saved to:\n%s":
        "📤 %d von Hand gesetzte(s) Paso-Doble-Highlight(s) gespeichert in:\n%s",
    "This is no manual-PD-marks file:":
        "Das ist keine Datei mit manuellen PD-Marken:",
    "📥 %d hand-set Paso Doble highlight(s) imported — %d of them belong to a track this PC already knows.\n\nThe others are kept and apply as soon as that music turns up here.":
        "📥 %d von Hand gesetzte(s) Paso-Doble-Highlight(s) importiert — %d davon gehören zu einem Titel, den dieser PC schon kennt.\n\nDie übrigen bleiben gespeichert und greifen, sobald diese Musik hier auftaucht.",
    "Playlist popularity re-learned from %s playlists.":
        "Playlist-Beliebtheit aus %s Playlists neu gelernt.",
    "📜 %s playlists analyzed (M3U files + tournament folders) — popularity and co-occurrence are up to date, so a just-exported tournament counts now.\n\nRows already in the grid keep their old Pop value until regenerated.":
        "📜 %s Playlists analysiert (M3U-Dateien + Turnierordner) — Beliebtheit und gemeinsames Vorkommen sind aktuell, ein gerade exportiertes Turnier zählt also schon mit.\n\nZeilen, die schon im Raster stehen, behalten ihren alten Pop-Wert, bis sie neu gewürfelt werden.",
    "Re-learn failed:":
        "Neu lernen fehlgeschlagen:",
    "  … and %d more":
        "  … und %d weitere",
    "⚠ %d title(s) are not on the Referenzpfad\n%s\nand were saved with their own path:":
        "⚠ %d Titel liegen nicht auf dem Referenzpfad\n%s\nund wurden mit ihrem eigenen Pfad gespeichert:",
    "💾 Saved %d playlist → %s":
        "💾 %d Playlist gespeichert → %s",
    "💾 Saved %d playlists → %s":
        "💾 %d Playlists gespeichert → %s",
    "Saved %d playlist(s) to:\n%s":
        "%d Playlist(s) gespeichert in:\n%s",
    "Saved %d wishlist(s) to:\n%s":
        "%d Wunschliste(n) gespeichert in:\n%s",
    "Skipped (empty): %s":
        "Übersprungen (leer): %s",
    "Errors:":
        "Fehler:",
    "“%s” already exists in the target folder.\nReplace it, or keep both?":
        "„%s“ gibt es im Zielordner schon.\nErsetzen oder beide behalten?",
    "🧳 Bundle: %d playlist folder(s), %d track(s), %s MB → %s":
        "🧳 Paket: %d Playlist-Ordner, %d Titel, %s MB → %s",
    "Bundle written to:\n%s":
        "Paket geschrieben nach:\n%s",
    "%d playlist folder(s) · %d track(s) · %s MB — each folder holds the tracks numbered in play order plus the playlist's M3U, so it plays even without the M3U.":
        "%d Playlist-Ordner · %d Titel · %s MB — jeder Ordner enthält die Titel in Spielreihenfolge nummeriert plus die M3U der Playlist, er spielt also auch ohne die M3U.",
    "⚠ %d track(s) were missing on disk and kept their original absolute path.":
        "⚠ %d Titel fehlten auf der Platte und haben ihren ursprünglichen absoluten Pfad behalten.",
    "💾 Saved %d competition playlist → %s":
        "💾 %d Turnier-Playlist gespeichert → %s",
    "💾 Saved %d competition playlists → %s":
        "💾 %d Turnier-Playlists gespeichert → %s",
    "Saved %d competition playlist(s) to:\n%s":
        "%d Turnier-Playlist(s) gespeichert in:\n%s",
    "Nothing to save.":
        "Nichts zu speichern.",
    "Saved → %s":
        "Gespeichert → %s",
    "Saved %d competition playlist(s) → %s":
        "%d Turnier-Playlist(s) gespeichert → %s",
    "Close the tournament-day view? This clears %d day playlist.":
        "Die Turniertag-Ansicht schließen? Das leert %d Tages-Playlist.",
    "Close the tournament-day view? This clears %d day playlists.":
        "Die Turniertag-Ansicht schließen? Das leert %d Tages-Playlists.",
    "Clear the %d day playlist?":
        "Die %d Tages-Playlist leeren?",
    "Clear all %d day playlists?":
        "Alle %d Tages-Playlists leeren?",
    "Clear the %d playlist on “%s”?":
        "Die %d Playlist auf „%s“ leeren?",
    "Clear all %d playlists on “%s”?":
        "Alle %d Playlists auf „%s“ leeren?",
    "🧹 %s playlists cleared.":
        "🧹 Playlists auf %s geleert.",
    " — %d track(s) of no known dance left out":
        " — %d Titel ohne bekannten Tanz weggelassen",
    "🔒 Static mode — a drop now replaces a single slot":
        "🔒 Statischer Modus — ein Ablegen ersetzt jetzt einen einzelnen Platz",
    "🔓 Dynamic mode — drag songs from the wishlist or another deck to build rounds & heats":
        "🔓 Dynamischer Modus — zieh Titel aus der Wunschliste oder einem anderen Deck, um Runden & Gruppen aufzubauen",
    "✋ Free order — every row can be dragged anywhere, and a dropped song lands where you drop it":
        "✋ Freie Reihenfolge — jede Zeile lässt sich überallhin ziehen, und ein abgelegter Titel landet genau dort",
    "%d of these %d tracks say nothing about which dance they are. A grid has no column to put them in, so building one leaves them out of the deck.\n\nBuild the grid without them?":
        "%d dieser %d Titel sagen nicht, welcher Tanz sie sind. Ein Raster hat keine Spalte für sie, beim Aufbau fallen sie also aus dem Deck.\n\nDas Raster ohne sie aufbauen?",
    "🤸 %s panel shown — drop an .m3u here or build one with 🤸 %s.":
        "🤸 %s-Bereich eingeblendet — leg hier eine .m3u ab oder erzeuge eine mit 🤸 %s.",
    "🤸 %s panel hidden":
        "🤸 %s-Bereich ausgeblendet",
    "📚 Library filtered: %s":
        "📚 Bibliothek gefiltert: %s",
    "all dances":
        "alle Tänze",
    " · class %s":
        " · Klasse %s",
    " · never played":
        " · nie gespielt",
    "<b>%d</b> of %d checked tracks have at least one issue.":
        "<b>%d</b> von %d geprüften Titeln haben mindestens ein Problem.",
    "Plus <b>%d</b> 🧩 round-structure issue — see the yellow box below.":
        "Dazu <b>%d</b> 🧩 Problem im Rundenaufbau — siehe gelber Kasten unten.",
    "Plus <b>%d</b> 🧩 round-structure issues — see the yellow box below.":
        "Dazu <b>%d</b> 🧩 Probleme im Rundenaufbau — siehe gelber Kasten unten.",
    "%d tracks skipped — no label/dance/length or not audio-analyzed.":
        "%d Titel übersprungen — ohne Angabe/Tanz/Länge oder nicht audio-analysiert.",
    "⚡ tempo label vs measured off > %.0f%% (×2, ×3, ×1.5 … slips excused) · 🐢/🐇 takt outside the official TSO range · ⏱ real play ≤ %s":
        "⚡ Tempoangabe weicht > %.0f%% von der Messung ab (×2, ×3, ×1,5 … werden toleriert) · 🐢/🐇 Takt außerhalb des offiziellen TSO-Bereichs · ⏱ echte Spielzeit ≤ %s",
    "⏳ longer than %s":
        "⏳ länger als %s",
    "🔇 noise floor above %.0f dB":
        "🔇 Grundrauschen über %.0f dB",
    "Thresholds: ⚙ Settings → 🎵 Checks.":
        "Schwellen: ⚙ Einstellungen → 🎵 Prüfungen.",
    "⏳  Also flag long tracks (> %s) — only relevant when building an Eintanzen playlist":
        "⏳  Auch lange Titel markieren (> %s) — nur für eine Eintanzen-Playlist wichtig",
    "🔇  Also flag hissy tracks (never quieter than %.0f dB) — measures each track once with ffmpeg, so the first run takes a moment":
        "🔇  Auch rauschende Titel markieren (nie leiser als %.0f dB) — misst jeden Titel einmal mit ffmpeg, der erste Lauf dauert daher etwas",
    "🧩 <b>Round structure</b> — click a spot to jump to it":
        "🧩 <b>Rundenaufbau</b> — klicke eine Stelle an, um dorthin zu springen",
    "In playlist: %s":
        "In Playlist: %s",
    "⚠  “%s” is no longer in an open deck.":
        "⚠  „%s“ liegt in keinem offenen Deck mehr.",
    "<b>%d</b> of %d checked tracks have an issue.":
        "<b>%d</b> von %d geprüften Titeln haben ein Problem.",
    "%d skipped — not found / not audio-analyzed.":
        "%d übersprungen — nicht gefunden / nicht audio-analysiert.",
    "⚡ tempo label vs measured · 🐢/🐇 takt outside the TSO range · ⏱ short · ⏳ long · 🔇 hiss · 🧩 round structure (uneven dances, heat taper, heat tempo spread).":
        "⚡ Tempoangabe gegen Messung · 🐢/🐇 Takt außerhalb des TSO-Bereichs · ⏱ kurz · ⏳ lang · 🔇 Rauschen · 🧩 Rundenaufbau (ungleiche Tänze, schrumpfende Gruppen, Tempospanne je Gruppe).",
    "🧩 <b>Round structure</b>":
        "🧩 <b>Rundenaufbau</b>",
    "%d valid · %d unresolved across %d playlist.":
        "%d gültig · %d ungelöst in %d Playlist.",
    "%d valid · %d unresolved across %d playlists.":
        "%d gültig · %d ungelöst in %d Playlists.",
    "🔧 %d path line to fix":
        "🔧 %d Pfadzeile zu korrigieren",
    "🔧 %d path lines to fix":
        "🔧 %d Pfadzeilen zu korrigieren",
    "✅ Nothing to fix":
        "✅ Nichts zu korrigieren",
    "🔧 %d track can be moved onto the Referenzpfad":
        "🔧 %d Titel kann auf den Referenzpfad verschoben werden",
    "🔧 %d tracks can be moved onto the Referenzpfad":
        "🔧 %d Titel können auf den Referenzpfad verschoben werden",
    "%d tracks — <span style='color:#2a7a45;'>%d valid</span> · <b style='color:#e07b00; font-size:13px;'>🔧 %d to fix</b> · <span style='color:#a33;'>%d unresolved</span>":
        "%d Titel — <span style='color:#2a7a45;'>%d gültig</span> · <b style='color:#e07b00; font-size:13px;'>🔧 %d zu korrigieren</b> · <span style='color:#a33;'>%d ungelöst</span>",
    "⚠  unresolved (no match under the search folders):":
        "⚠  ungelöst (kein Treffer unter den Suchordnern):",
    "Rewrite %d path line(s) across %d playlist(s) in place?\n\nOnly the file-path lines change — #EXTINF and every other line stay exactly as-is. This overwrites the .m3u files on disk; each original is kept next to it as <name>.m3u.bak.":
        "%d Pfadzeile(n) in %d Playlist(s) direkt umschreiben?\n\nNur die Dateipfad-Zeilen ändern sich — #EXTINF und alle anderen Zeilen bleiben genau erhalten. Die .m3u-Dateien auf der Platte werden überschrieben; jedes Original bleibt daneben als <name>.m3u.bak liegen.",
    "🧭  Rewrote %d path line(s) in %d playlist(s).":
        "🧭  %d Pfadzeile(n) in %d Playlist(s) umgeschrieben.",
    "⚠  Left unchanged:":
        "⚠  Unverändert gelassen:",
    "… and %d more":
        "… und %d weitere",
    "Could not apply snapshot: %s":
        "Schnappschuss konnte nicht angewendet werden: %s",
    "Could not restore saved playlist: %s":
        "Gespeicherte Playlist konnte nicht wiederhergestellt werden: %s",
    "⚠  %d saved track(s) not found — is the music drive plugged in?":
        "⚠  %d gespeicherte(r) Titel nicht gefunden — ist das Musiklaufwerk angeschlossen?",
    "The saved session is kept as %s.":
        "Die gespeicherte Sitzung bleibt als %s erhalten.",
    "↩  Restored your in-progress playlist — %d songs (%s, %s)":
        "↩  Deine angefangene Playlist ist wiederhergestellt — %d Titel (%s, %s)",
    "↩  Restored your running order — %d tracks":
        "↩  Dein Ablauf ist wiederhergestellt — %d Titel",
    "↩  Restored your themed playlist — %d tracks":
        "↩  Deine Themenliste ist wiederhergestellt — %d Titel",
    "All %d playlists already hold tracks — there's no free slot to import into.\n\nClear a playlist first, or pick a single file to overwrite the focused deck.":
        "Alle %d Playlists enthalten schon Titel — es gibt keinen freien Platz für den Import.\n\nLeere zuerst eine Playlist oder wähle eine einzelne Datei, um das fokussierte Deck zu überschreiben.",
    "You picked %d files but only %d playlist slot(s) are free.\n\nImport the first %d into the free slots and skip the rest?":
        "Du hast %d Dateien gewählt, aber nur %d Playlist-Plätze sind frei.\n\nDie ersten %d in die freien Plätze importieren und den Rest überspringen?",
    "Importing %s …":
        "Importiere %s …",
    "Import failed: %s":
        "Import fehlgeschlagen: %s",
    "Remove %d title from %s?\nIt is already planned in: %s":
        "%d Titel aus %s entfernen?\nEr ist schon eingeplant in: %s",
    "Remove %d titles from %s?\nThey are already planned in: %s":
        "%d Titel aus %s entfernen?\nSie sind schon eingeplant in: %s",
    "Empty %d playlist? This can't be undone.":
        "%d Playlist leeren? Das lässt sich nicht rückgängig machen.",
    "Empty %d playlists? This can't be undone.":
        "%d Playlists leeren? Das lässt sich nicht rückgängig machen.",
    "↩  Restored your worked playlist for “%s” — %d songs":
        "↩  Deine bearbeitete Playlist für „%s“ ist wiederhergestellt — %d Titel",
    "this competition":
        "dieses Turnier",
    "⚠  Session not saved — the snapshot failed: %r":
        "⚠  Sitzung nicht gespeichert — der Schnappschuss ist fehlgeschlagen: %r",
    "Could not write the PDF:\n%s":
        "Das PDF konnte nicht geschrieben werden:\n%s",
    "🖨 Playlist saved — %s":
        "🖨 Playlist gespeichert — %s",
    "Playlist saved as\n%s\n\nOpen it now?":
        "Playlist gespeichert als\n%s\n\nJetzt öffnen?",
    "Cycle 1 → 2 → 4 → 8 → no playlists (and back).":
        "Durchschalten 1 → 2 → 4 → 8 → keine Playlists (und zurück).",
    "Cycle 1 → 2 → 4 → no playlists (and back).":
        "Durchschalten 1 → 2 → 4 → keine Playlists (und zurück).",
    "Right click walks the cycle backwards.":
        "Rechtsklick schaltet rückwärts durch.",
    "8 splits into two tabs of four (Group A–D / Group E–H).":
        "8 teilt sich in zwei Reiter zu je vier (Gruppe A–D / Gruppe E–H).",
    "No-playlist hides every deck so the Eintanzen / wishlist / library panes take over.":
        "„Keine Playlist“ blendet alle Decks aus, sodass Eintanzen / Wunschliste / Bibliothek den Platz übernehmen.",
    "Two or more decks also reveal the wishlist below.":
        "Ab zwei Decks erscheint darunter auch die Wunschliste.",
    "Generate / Save / ↺ / play act on whichever deck has focus.":
        "Erzeugen / Speichern / ↺ / Abspielen wirken auf das Deck mit dem Fokus.",
    "Show / hide the %s panel.\nOpens an empty panel — drop an existing .m3u onto it, or build a fresh list with 🤸 %s.":
        "Bereich %s ein-/ausblenden.\nÖffnet einen leeren Bereich — zieh eine vorhandene .m3u darauf oder erstelle eine neue Liste mit 🤸 %s.",
    "⭐ Swapped %s ⇄ %s":
        "⭐ %s ⇄ %s getauscht",
    "Show only the %d track(s) currently in your wishlist(s),\nranked by how well they match this song — pick the best one to add.\nMatches by song (title / fingerprint), so a different copy still counts.":
        "Zeigt nur die %d Titel, die gerade in deinen Wunschlisten stehen,\nsortiert danach, wie gut sie zu diesem Titel passen — nimm den besten.\nVerglichen wird der Song (Titel / Fingerabdruck), eine andere Kopie zählt also mit.",
    "🎼  Chroma cover / remix (melody/harmony, same tune)":
        "🎼  Chroma Cover / Remix (Melodie/Harmonie, gleiche Melodie)",
    "🧠  OpenL3 (deep embedding)":
        "🧠  OpenL3 (Deep Embedding)",
    "🎧 Hear and choose — %s": "🎧 Anhören und auswählen — %s",
    "🎧 Hear and choose…": "🎧 Anhören und auswählen…",
    "Now: %s": "Jetzt: %s",
    "Now: —": "Jetzt: —",
    "Where from": "Woher",
    "Offered for this slot": "Für diesen Platz angeboten",
    "Play / stop this title": "Diesen Titel abspielen / stoppen",
    "▶ or Space plays a title, again stops it, Ctrl+←/→ seeks 30 s, "
    "Ctrl+Shift+←/→ plays the title before or after it; a double click or "
    "\"Take\" puts it into the slot.":
        "▶ oder Leertaste spielt einen Titel, noch einmal stoppt ihn, Strg+←/→ "
        "spult 30 s, Strg+Umschalt+←/→ spielt den Titel davor oder danach; ein "
        "Doppelklick oder „Übernehmen“ setzt ihn in den Platz.",
    "Take": "Übernehmen",
    "⚖️  Combined: timbre + groove + melody (mean)":
        "⚖️  Kombiniert: Timbre + Groove + Melodie (Mittelwert)",
    "⚖️ Combined — the mean of where each title ranks by timbre, groove and melody.":
        "⚖️ Kombiniert — der Mittelwert, wie weit oben jeder Titel bei Timbre, "
        "Groove und Melodie steht.",
    "★  Only rarely played (1–%d playlists)":
        "★  Nur selten gespielte (1–%d Playlists)",
    "The same three picks as 📚 the library's ★ Plays selector.\n'Never played': the track is in none of your old playlists.\n'Rarely played': in 1–%d of them — %d+ is a proven title.\n'Not since 1 y': it is played, but the newest playlist carrying\nit is from an earlier year — the year comes from the playlist's\npath, so lists without a date never count as old.":
        "Dieselben drei Filter wie der ★-Gespielt-Wähler der 📚 Bibliothek.\n„Nie gespielt“: der Titel steht in keiner deiner alten Playlists.\n„Selten gespielt“: in 1–%d davon — ab %d ist er ein bewährter Titel.\n„Seit 1 J. nicht“: er wird gespielt, aber die neueste Playlist mit ihm\nstammt aus einem früheren Jahr — das Jahr kommt aus dem Pfad der\nPlaylist, Listen ohne Datum gelten also nie als alt.",
    "%d %s tracks most often played together with this one — ▶ to preview, double-click to open, drag rows into another app":
        "%d %s-Titel, die am häufigsten mit diesem zusammen gespielt wurden — ▶ zum Anhören, Doppelklick zum Öffnen, Zeilen in eine andere App ziehen",
    "%d %s tracks most similar (sound-alike) to this one — ▶ to preview, double-click to open, drag rows into another app":
        "%d %s-Titel, die diesem am ähnlichsten klingen — ▶ zum Anhören, Doppelklick zum Öffnen, Zeilen in eine andere App ziehen",
    "⭐ wishlist only":
        "⭐ nur Wunschliste",
    "📜 played in this round before":
        "📜 früher in dieser Runde gespielt",
    "📜  Only titles I played in this round before (%s)":
        "📜  Nur Titel, die ich früher in dieser Runde gespielt habe (%s)",
    "Show only titles your past competitions played in this round —\n"
    "any heat of it, from lists of a class and age category that fit\n"
    "this deck (the same history as 📜 Find planned before).\n"
    "Still ranked by how much they sound like this one.":
        "Nur Titel zeigen, die deine früheren Turniere in dieser Runde gespielt\n"
        "haben — in irgendeinem Heat, aus Listen einer Klasse und Altersgruppe,\n"
        "die zu diesem Deck passen (dieselbe Historie wie 📜 Früher geplante finden).\n"
        "Weiter danach sortiert, wie ähnlich sie diesem klingen.",
    "🎙 instrumental only (%d vocal hidden)":
        "🎙 nur instrumental (%d mit Gesang ausgeblendet)",
    "%s (%d hidden)":
        "%s (%d ausgeblendet)",
    "%d duplicate hidden":
        "%d Duplikat ausgeblendet",
    "%d duplicates hidden":
        "%d Duplikate ausgeblendet",
    "%d track(s) you planned for this dance &amp; round in past competitions — best competition match first (see Class) — ▶ to preview, drag a row onto the slot, double-click to open":
        "%d Titel, die du für diesen Tanz &amp; diese Runde bei früheren Turnieren eingeplant hast — bester Turniertreffer zuerst (siehe Klasse) — ▶ zum Anhören, Zeile auf den Platz ziehen, Doppelklick zum Öffnen",
    "Similar to: %s":
        "Ähnlich wie: %s",
    "📋 Learned from your playlists — %d often played together.":
        "📋 Aus deinen Playlists gelernt — %d oft zusammen gespielt.",
    "🧠  Rebuild %s index…":
        "🧠  %s-Index neu aufbauen…",
    "%s vectors for these %d tracks haven't been built yet.\n\nBuilding analyses each track once (slow the first time, then cached).\nBuild now?":
        "%s-Vektoren für diese %d Titel sind noch nicht aufgebaut.\n\nDer Aufbau analysiert jeden Titel einmal (beim ersten Mal langsam, danach gespeichert).\nJetzt aufbauen?",
    "Building %s embedding index…":
        "%s-Embedding-Index wird aufgebaut…",
    "All %d file(s) failed to embed.\n\nFirst error:\n%s\n\nCommon causes: the neural model couldn't load, or the deps are mismatched. See the console log for the full traceback.":
        "Keine der %d Datei(en) ließ sich einbetten.\n\nErster Fehler:\n%s\n\nHäufige Ursachen: das neuronale Modell ließ sich nicht laden, oder die Abhängigkeiten passen nicht zusammen. Den vollständigen Traceback zeigt das Konsolen-Log.",
    "🧠 %s index ready (%d embedded, %d failed).":
        "🧠 %s-Index bereit (%d eingebettet, %d fehlgeschlagen).",
    "🧠 %s index ready (%d embedded).":
        "🧠 %s-Index bereit (%d eingebettet).",
    "%s indexing cancelled — showing librosa results.":
        "%s-Indizierung abgebrochen — zeige librosa-Ergebnisse.",
    "Ranking by %s embedding…":
        "Sortiere nach %s-Embedding…",
    "No %s matches yet — try building the index over more tracks.":
        "Noch keine %s-Treffer — baue den Index über mehr Titel auf.",
    "🧠 %s — %d deep-embedding matches.":
        "🧠 %s — %d Deep-Embedding-Treffer.",
    "Refreshed — %d similar to %s":
        "Aktualisiert — %d ähnlich wie %s",
    "%s / %s  (%s left)":
        "%s / %s  (%s übrig)",
    "~%s remaining":
        "noch ~%s",
    "Listing files…":
        "Dateien werden aufgelistet…",
    "This is not an audio file, so it won't be opened:\n%s":
        "Das ist keine Audiodatei, sie wird nicht geöffnet:\n%s",
    "File not found:\n%s":
        "Datei nicht gefunden:\n%s",
    "Couldn't open the file:\n%s":
        "Die Datei ließ sich nicht öffnen:\n%s",
    "Folder not found:\n%s":
        "Ordner nicht gefunden:\n%s",
    "Couldn't open the folder:\n%s":
        "Der Ordner ließ sich nicht öffnen:\n%s",
    "Couldn't reveal the file:\n%s":
        "Die Datei ließ sich nicht anzeigen:\n%s",
    "✅  No duplicates among the %d file added.":
        "✅  Keine Duplikate unter der %d hinzugefügten Datei.",
    "✅  No duplicates among the %d files added.":
        "✅  Keine Duplikate unter den %d hinzugefügten Dateien.",
    "Comparison failed:\n%s":
        "Vergleich fehlgeschlagen:\n%s",
    "✅  %d hard duplicate(s) to remove, %d unused track(s) to export (of %d; %d Paso Doble kept). Review below, then export.":
        "✅  %d harte(s) Duplikat(e) zu entfernen, %d ungenutzte(r) Titel zu exportieren (von %d; %d Paso Doble behalten). Unten prüfen, dann exportieren.",
    "Could not write file:\n%s":
        "Datei konnte nicht geschrieben werden:\n%s",
    "The reference playlist itself was overwritten with the cleaned list.":
        "Die Referenz-Playlist selbst wurde mit der bereinigten Liste überschrieben.",
    "The reference playlist was left unchanged.":
        "Die Referenz-Playlist blieb unverändert.",
    "📤  Exported %d track(s) (sorted by dance) → %s":
        "📤  %d Titel exportiert (nach Tanz sortiert) → %s",
    "📤  Exported %d track(s) → %s":
        "📤  %d Titel exportiert → %s",
    "Exported %d unused track(s) to:\n%s\n\n%d hard duplicate(s) removed. %s":
        "%d ungenutzte(n) Titel exportiert nach:\n%s\n\n%d harte(s) Duplikat(e) entfernt. %s",
    "🔁  Replace in %s":
        "🔁  Ersetzen in %s",
    "This song is in %d open playlists. Replacing it on one\nrow leaves the other copies — pick a copy on each of its rows to\nreplace them all (the choices are merged when you press Apply).":
        "Dieser Titel steht in %d offenen Playlists. Ersetzt du ihn in einer\nZeile, bleiben die anderen Kopien — wähle in jeder seiner Zeilen eine\nKopie, um alle zu ersetzen (die Auswahl wird beim Übernehmen zusammengeführt).",
    "%d occurrence(s) are set to Replace but have no replacement track yet.\nPick a track for each, or switch them back to Keep.":
        "%d Vorkommen steht/stehen auf Ersetzen, haben aber noch keinen Ersatztitel.\nWähle für jedes einen Titel oder stelle es zurück auf Behalten.",
    "%d copy/copies are set to two different changes on different rows.\nChoose the same on each, or set one back to Keep all.":
        "%d Kopie(n) sollen in verschiedenen Zeilen unterschiedlich geändert werden.\nWähle überall dasselbe oder stelle eine zurück auf Alle behalten.",
    "🗑  Remove from %s":
        "🗑  Entfernen aus %s",
    "🗑  Removed %d duplicate":
        "🗑  %d Duplikat entfernt",
    "🗑  Removed %d duplicates":
        "🗑  %d Duplikate entfernt",
    "A track named “%s” is already in this playlist,\nbut it’s a different file.":
        "Ein Titel namens „%s“ ist schon in dieser Playlist,\naber es ist eine andere Datei.",
    "“%s” is already in this playlist —\n“%s” looks like the same title in another file.":
        "„%s“ ist schon in dieser Playlist —\n„%s“ scheint derselbe Titel in einer anderen Datei zu sein.",
    "“%s” is already in this playlist.\n\nRemove it from the wishlist anyway?":
        "„%s“ ist schon in dieser Playlist.\n\nTrotzdem aus der Wunschliste entfernen?",
    "“%s” is already in this playlist.\n\nRemove it from the playlist anyway?":
        "„%s“ ist schon in dieser Playlist.\n\nTrotzdem aus der Playlist entfernen?",
    "%d dragged track(s) are already in this playlist.\n\nRemove them from the wishlist anyway?":
        "%d gezogene(r) Titel ist/sind schon in dieser Playlist.\n\nTrotzdem aus der Wunschliste entfernen?",
    "%d dragged track(s) are already in this playlist.\n\nRemove them from the playlist anyway?":
        "%d gezogene(r) Titel ist/sind schon in dieser Playlist.\n\nTrotzdem aus der Playlist entfernen?",
    "“%s” looks like a %s track, but this slot is %s.\n\nReplace anyway?":
        "„%s“ sieht nach einem %s-Titel aus, aber dieser Platz ist %s.\n\nTrotzdem ersetzen?",
    "Remove this whole heat (all dances) from %s?":
        "Diese ganze Gruppe (alle Tänze) aus %s entfernen?",
    "⬆  %d song(s) moved up into empty slots":
        "⬆  %d Titel in freie Plätze nachgerückt",
    "Remove the entire round “%s” and all %d of its heats?":
        "Die ganze Runde „%s“ mit allen %d Gruppen entfernen?",
    "Remove %s from %s?\n%d song(s) in this round will be cleared.":
        "%s aus %s entfernen?\n%d Titel in dieser Runde werden geleert.",
    "Hide the empty %s from %s?":
        "%s (leer) in %s ausblenden?",
    "Remove %s from all rounds and heats?\n%d song(s) across the playlist will be cleared.":
        "%s aus allen Runden und Gruppen entfernen?\n%d Titel in der ganzen Playlist werden geleert.",
    "Hide the empty %s from all rounds?":
        "%s (leer) in allen Runden ausblenden?",
    "%d dropped track(s) look like %s dances, but this is a %s list.\n\nAdd them anyway?":
        "%d abgelegte(r) Titel sieht/sehen nach %s-Tänzen aus, aber dies ist eine %s-Liste.\n\nTrotzdem hinzufügen?",
    "All open playlists (%d deck)":
        "Alle offenen Playlists (%d Deck)",
    "All open playlists (%d decks)":
        "Alle offenen Playlists (%d Decks)",
    "%d file added.":
        "%d Datei hinzugefügt.",
    "%d files added.":
        "%d Dateien hinzugefügt.",
    "📅 Tournament day only (%d playlist)":
        "📅 Nur Turniertag (%d Playlist)",
    "📅 Tournament day only (%d playlists)":
        "📅 Nur Turniertag (%d Playlists)",
    "Dance: %s":
        "Tanz: %s",
    "%s (%d beats/bar)":
        "%s (%d Schläge/Takt)",
    "'%s' is not a valid round pattern for %s %s — use heat counts like 6-3-2-1.":
        "„%s“ ist kein gültiges Rundenmuster für %s %s — nutze Gruppenzahlen wie 6-3-2-1.",
    "Red: the pool can't carry a competition (pool < %d or proven < %d — a 6-3-2-1 needs 12 per dance).  Orange: < 80 %% of the takt-labelled tracks are tournament tempo, or over half the pool is stale (no dateable playlist in ≥ 3 years; 'never played' always counts as stale).  Double-click a row to browse its never-played tracks in 📚 the library.":
        "Rot: der Pool trägt kein Turnier (Pool < %d oder bewährt < %d — ein 6-3-2-1 braucht 12 je Tanz).  Orange: < 80 %% der Titel mit Taktangabe haben Turniertempo, oder über die Hälfte des Pools ist veraltet (keine datierbare Playlist in ≥ 3 Jahren; „nie gespielt“ zählt immer als veraltet).  Doppelklick auf eine Zeile zeigt ihre nie gespielten Titel in 📚 der Bibliothek.",
    "⚠️ %d gap(s) found":
        "⚠️ %d Lücke(n) gefunden",
    "(%d playlist)":
        "(%d Playlist)",
    "(%d playlists)":
        "(%d Playlists)",
    "%d song":
        "%d Titel",
    "%d songs":
        "%d Titel",
    "The playlist file is gone:\n\n%s":
        "Die Playlist-Datei ist nicht mehr da:\n\n%s",
    "No .m3u playlists found under “%s”.":
        "Keine .m3u-Playlists unter „%s“ gefunden.",
    "Remove “%s” from the tree?\n\n%d playlist file(s) are listed under it — they stay on disk, only this entry goes.":
        "„%s“ aus dem Baum entfernen?\n\nDarunter stehen %d Playlist-Datei(en) — sie bleiben auf der Platte, nur dieser Eintrag verschwindet.",
    "Remove %d entries from the tree?\n\n%d playlist file(s) are listed under them — they stay on disk, only these entries go.":
        "%d Einträge aus dem Baum entfernen?\n\nDarunter stehen %d Playlist-Datei(en) — sie bleiben auf der Platte, nur diese Einträge verschwinden.",
    "%s and %s are different dances.\n\nOnly titles of the same dance can swap places, so every round keeps its dances.":
        "%s und %s sind verschiedene Tänze.\n\nNur Titel desselben Tanzes können die Plätze tauschen, damit jede Runde ihre Tänze behält.",
    "No past competition plans found for %s in %s.":
        "Keine früheren Turnierplanungen für %s in %s gefunden.",
    "Remove all %d track(s) from wishlist%s?":
        "Alle %d Titel aus der Wunschliste%s entfernen?",
    "Remove the entire playlist%s? The table will be blank again.":
        "Die ganze Playlist%s entfernen? Die Tabelle ist danach wieder leer.",
    "Couldn't read as an audio track:":
        "Ließ sich nicht als Audiotitel lesen:",
    "This list":
        "Diese Liste",
    "%s holds %d title twice — the same audio, e.g. a copy of the file on another drive:\n\n%s\n\nRemove the earlier copy? The last one stays.":
        "%s enthält %d Titel doppelt — dieselbe Audiodatei, z. B. eine Kopie auf einem anderen Laufwerk:\n\n%s\n\nDie frühere Kopie entfernen? Die letzte bleibt.",
    "%s holds %d titles twice — the same audio, e.g. a copy of the file on another drive:\n\n%s\n\nRemove the earlier copies? The last one stays.":
        "%s enthält %d Titel doppelt — dieselbe Audiodatei, z. B. eine Kopie auf einem anderen Laufwerk:\n\n%s\n\nDie früheren Kopien entfernen? Die letzte bleibt.",
    "Any OpenAI-compatible /chat/completions host.":
        "Jeder OpenAI-kompatible /chat/completions-Host.",
    "%d models loaded.":
        "%d Modelle geladen.",
    "%d suggestions — %d in your library.":
        "%d Vorschläge — %d in deiner Bibliothek.",
    "▾  %d more lines":
        "▾  %d weitere Zeilen",
    "thinking…":
        "denkt nach…",
    "Couldn't read “%s” as an audio track.":
        "„%s“ ließ sich nicht als Audiotitel lesen.",
    "“%s” holds %d tracks (subfolders included).\n\nReading them all takes a moment — every file's tags are read on the way in.\n\nAdd them?":
        "„%s“ enthält %d Titel (Unterordner eingeschlossen).\n\nSie alle einzulesen dauert einen Moment — beim Einlesen werden die Tags jeder Datei gelesen.\n\nHinzufügen?",
    "↩ Left at %s — starts there again":
        "↩ Bei %s verlassen — startet dort wieder",
    "Plays %s — the stillness at the edges of the file is skipped":
        "Spielt %s — die Stille an den Rändern der Datei wird übersprungen",
    "Shorter than the configured play length (%s)":
        "Kürzer als die eingestellte Spiellänge (%s)",
    "%s already holds %d track(s).\n\nImporting %s REPLACES them — the list is loaded fresh from the file, the tracks in it now are dropped.\n\nImport anyway?":
        "%s enthält schon %d Titel.\n\n%s zu importieren ERSETZT sie — die Liste wird frisch aus der Datei geladen, die Titel darin jetzt fallen weg.\n\nTrotzdem importieren?",
    "“%s” is already used in this playlist.":
        "„%s“ ist in dieser Playlist schon verwendet.",
    "A %s track can only move into another %s slot — not a %s slot.":
        "Ein %s-Titel kann nur auf einen anderen %s-Platz — nicht auf einen %s-Platz.",
    "Dances (%d): %s":
        "Tänze (%d): %s",
    "Order: %s, %s, …":
        "Reihenfolge: %s, %s, …",
    "🟰  Identical files — the earlier copy is removed, the last stays (%d)":
        "🟰  Identische Dateien — die frühere Kopie wird entfernt, die letzte bleibt (%d)",
    "✏  %d pads selected — colour, volume, fade, 🔁 and 🔈 apply to all of them.\nLabel and shortcut stay with this pad.":
        "✏  %d Pads ausgewählt — Farbe, Lautstärke, Ausblenden, 🔁 und 🔈 gelten für alle.\nBeschriftung und Tastenkürzel bleiben bei diesem Pad.",
    "Empty = this slot's default (%s)":
        "Leer = Vorgabe dieses Slots (%s)",
    "Empty = no key (this slot has no default)":
        "Leer = keine Taste (dieser Slot hat keine Vorgabe)",
    "cut":
        "harter Schnitt",
    "%s (wall)":
        "%s (Cartwall)",
    "⚠ already used by %s":
        "⚠ schon belegt von %s",
    "%d key claimed twice — the marked ones will not fire. Pad keys win over slot keys.":
        "%d Taste doppelt vergeben — die markierten lösen nicht aus. Pad-Tasten gehen vor Slot-Tasten.",
    "%d keys claimed twice — the marked ones will not fire. Pad keys win over slot keys.":
        "%d Tasten doppelt vergeben — die markierten lösen nicht aus. Pad-Tasten gehen vor Slot-Tasten.",
    "Page %d":
        "Seite %d",
    "page %d":
        "Seite %d",
    "%d pads need %d pages at %d × %d; the wall keeps at most %d.\nClear some pads or pick a bigger layout.":
        "%d Pads brauchen %d Seiten bei %d × %d; die Cartwall fasst höchstens %d.\nLeere einige Pads oder wähle ein größeres Raster.",
    "Remove %s and the %d pads on it?\nThe sample files are left alone — only the pads go.":
        "%s und die %d Pads darauf entfernen?\nDie Sample-Dateien bleiben unberührt — nur die Pads gehen.",
    "%d pads do not fit one %d × %d page.\nPick a bigger layout first.":
        "%d Pads passen nicht auf eine Seite mit %d × %d.\nWähle zuerst ein größeres Raster.",
    "Could not write the wall:\n%s":
        "Die Cartwall konnte nicht geschrieben werden:\n%s",
    "%d pads written to\n%s\n\nThe sample files themselves are not copied — the wall stores their paths.":
        "%d Pads geschrieben nach\n%s\n\nDie Sample-Dateien selbst werden nicht kopiert — die Cartwall speichert ihre Pfade.",
    "Replace the current wall with %d pads from\n%s?":
        "Die aktuelle Cartwall durch %d Pads ersetzen aus\n%s?",
    "The wall is full: %d of %d tracks were placed.\nClear some pads or pick a bigger layout for the rest.":
        "Die Cartwall ist voll: %d von %d Titeln wurden platziert.\nLeere einige Pads oder wähle ein größeres Raster für den Rest.",
    "🔇 Only stillness left from %s — song ended.":
        "🔇 Ab %s nur noch Stille — Titel beendet.",
    "🔇 Skipped %ss of leading silence.":
        "🔇 %s s Stille am Anfang übersprungen.",
    "⚠️ Sample not found: %s":
        "⚠️ Sample nicht gefunden: %s",
    "⏱ Auto-advance pause extended by %ss.":
        "⏱ Auto-Weiter-Pause um %s s verlängert.",
    "⏸ Auto-advance…  🎵 %s":
        "⏸ Auto-Weiter…  🎵 %s",
    "🎯 Highlight at %s — %d mark(s). ✔ Done editing arms the stop.":
        "🎯 Höhepunkt bei %s — %d Marke(n). ✔ Bearbeitung beenden schärft den Stopp.",
    "🎯 PD highlight %d marked at %s (stop set to #%s)":
        "🎯 PD-Höhepunkt %d bei %s markiert (Stopp auf #%s gesetzt)",
    "🏁  %s finished":
        "🏁  %s beendet",
    "🏁 %s finished — auto-advance stopped.":
        "🏁 %s beendet — Auto-Weiter angehalten.",
    "Can't cue — file not found: %s":
        "Kann nicht bereitstellen — Datei nicht gefunden: %s",
    "⏸ Cued %s — press ⏯ to play. — ⏭ walks the playlist":
        "⏸ %s bereitgestellt — ⏯ spielt ab. — ⏭ geht die Playlist entlang",
    "⏸ Cued %s — press ⏯ to play.":
        "⏸ %s bereitgestellt — ⏯ spielt ab.",
    "the %s %s of this round":
        "den %s %s dieser Runde",
    "this %s":
        "diesem %s",
    "🎚 TSO tempo: %s %s → T%s (target T%s from %s)":
        "🎚 TSO-Tempo: %s %s → T%s (Ziel T%s aus %s)",
    "⏸  cued: %s":
        "⏸  bereit: %s",
    "↩ Picked up at %s.":
        "↩ Bei %s fortgesetzt.",
    "⏸  editing: %s":
        "⏸  Bearbeiten: %s",
    "⏸  editing":
        "⏸  Bearbeiten",
    "Play length per song: each song is stopped after this time,\n"
    "ramping down over the fade time first. Steps of %s s\n"
    "up to %s; one step further is\n"
    "'full' — no cut, every title plays to its own end.\n\n"
    "Double-click to type an exact length (e.g. 1:37).":
        "Spielzeit pro Titel: Jeder Titel wird nach dieser Zeit gestoppt\n"
        "und vorher über die Ausblendzeit leiser. In Schritten von %s s\n"
        "bis %s; ein Schritt weiter ist\n"
        "'komplett' — kein Schnitt, jeder Titel läuft bis zu seinem Ende.\n\n"
        "Doppelklick, um eine genaue Länge einzugeben (z. B. 1:37).",
    "Delete the highlight at %s s":
        "Den Höhepunkt bei %s s löschen",
    "Compensate loudness differences between tracks on playback:\neach song's measured EBU R128 loudness is pulled towards a\ncommon target, so quiet old recordings and loud modern\nmasters play at a similar level.":
        "Lautheitsunterschiede zwischen den Titeln beim Abspielen ausgleichen:\ndie gemessene EBU-R128-Lautheit jedes Titels wird auf ein\ngemeinsames Ziel gezogen, damit leise alte Aufnahmen und laute\nmoderne Master ähnlich laut spielen.",
    "ℹ No loudness measured yet — tracks play at their\noriginal volume. Run 📊 Analyze loudness (⚙ Settings)\nto equalize them.":
        "ℹ Noch keine Lautheit gemessen — die Titel spielen in ihrer\nOriginallautstärke. Starte 📊 Lautheit analysieren (⚙ Einstellungen),\num sie anzugleichen.",
    "ℹ %d open-playlist track not measured yet — it plays at original volume.\nRun 📊 Analyze loudness (⚙ Settings) to equalize it too.":
        "ℹ %d Titel der offenen Playlists ist noch nicht gemessen — er spielt in Originallautstärke.\nStarte 📊 Lautheit analysieren (⚙ Einstellungen), um ihn auch anzugleichen.",
    "ℹ %d open-playlist tracks not measured yet — they play at original volume.\nRun 📊 Analyze loudness (⚙ Settings) to equalize them too.":
        "ℹ %d Titel der offenen Playlists sind noch nicht gemessen — sie spielen in Originallautstärke.\nStarte 📊 Lautheit analysieren (⚙ Einstellungen), um sie auch anzugleichen.",
    "⚡ Tempo: measured ~%s vs label %s bpm (off %s%%)":
        "⚡ Tempo: gemessen ~%s statt Label %s bpm (%s %% daneben)",
    "label":
        "Label",
    "measured":
        "gemessen",
    "🐢 Too slow: T%s (%s), TSO %s-%s":
        "🐢 Zu langsam: T%s (%s), TSO %s-%s",
    "🐇 Too fast: T%s (%s), TSO %s-%s":
        "🐇 Zu schnell: T%s (%s), TSO %s-%s",
    "⏱ Short: real play %s — %s file minus %ss silence (≤ %s)":
        "⏱ Kurz: echte Spielzeit %s — %s Datei minus %s s Stille (≤ %s)",
    "⏱ Short: %s (≤ %s play length)":
        "⏱ Kurz: %s (≤ %s Spiellänge)",
    "⏳ Long: %s (> %s)":
        "⏳ Lang: %s (> %s)",
    "🔇 Hiss: never quieter than %s dB (> %s dB)":
        "🔇 Rauschen: nie leiser als %s dB (> %s dB)",
    "“%s”: uneven dance counts — ":
        "„%s“: ungleiche Tanzanzahl — ",
    "%s %d/%d (missing in heat ":
        "%s %d/%d (fehlt in Gruppe ",
    "Final ":
        "Finale ",
    "Semifinal ":
        "Semifinale ",
    "“%s”":
        "„%s“",
    " has %d heats, expected 1.":
        " hat %d Gruppen, erwartet 1.",
    " has %d heats, expected 2.":
        " hat %d Gruppen, erwartet 2.",
    "“%s”: %s heats differ by %d takte (allowed: 1) — ":
        "„%s“: Die %s-Gruppen weichen um %d Takte ab (erlaubt: 1) — ",
    "heat %d: T%s “%s”":
        "Gruppe %d: T%s „%s“",
    "“%s” — %s":
        "„%s“ — %s",
    "🧩 “%s” %s heats differ by %d takte (allowed: 1)":
        "🧩 „%s“: Die %s-Gruppen weichen um %d Takte ab (erlaubt: 1)",
    "title":
        "Titel",
    "dance":
        "Tanz",
    "takt":
        "Takt",
    "year":
        "Jahr",
    "genre":
        "Genre",
    "classes":
        "Klassen",
    "instrumental":
        "Instrumental",
    "christmas":
        "Weihnachten",
    "ID3 title":
        "ID3-Titel",
    "artist":
        "Interpret",
    "length":
        "Länge",
    "album":
        "Album",
    "markers":
        "Marker",
    "⚠ %s: only %d proven song(s) — finals need %d; expect fresh fill-ins.":
        "⚠ %s: nur %d bewährte(r) Titel — Finals brauchen %d; rechne mit neuen Lückenfüllern.",
    "♪ %s: no track near the ideal %s bpm.":
        "♪ %s: kein Titel nahe am idealen Tempo von %s bpm.",
    "✦ %d/%d songs are fresh (%d%% new).":
        "✦ %d/%d Titel sind neu (%d %%).",
    "⚠ %s could not fill %d of %d slots (%s) — park more tracks there or switch the source back to the Favorites library.":
        "⚠ Aus %s ließen sich %d von %d Slots nicht füllen (%s) — parke dort mehr Titel oder stell die Quelle zurück auf die Favoriten-Bibliothek.",
    "⭐ the open wishlists":
        "⭐ den offenen Wunschlisten",
    "📅 Day plan: %d competition(s) generated — %d songs locked for the day (Paso Doble may repeat)":
        "📅 Tagesplan: %d Turnier(e) erstellt — %d Titel für den Tag gesperrt (Paso Doble darf sich wiederholen)",
    "🕑 Seeded from %d past “%s” list(s) — round pool sizes: %s":
        "🕑 Aus %d früheren „%s“-Liste(n) befüllt — Pool-Größe je Runde: %s",
    "⚠️ No past “%s” lists found — used the whole favorites library instead":
        "⚠️ Keine früheren „%s“-Listen gefunden — stattdessen die ganze Favoriten-Bibliothek genutzt",
    "🎯 %s: %d tracks  (%s)":
        "🎯 %s: %d Titel  (%s)",
    "↺ swaps with a title from the end, drag-drop replaces":
        "↺ tauscht mit einem Titel vom Ende, Hineinziehen ersetzt",
    "↺ / drag-drop to replace by timbre":
        "↺ / Hineinziehen ersetzt nach Timbre",
    "🤸 %s: %d tracks  (%s)  — %s":
        "🤸 %s: %d Titel  (%s)  — %s",
    "📂 Importing %s…":
        "📂 Importiere %s…",
    "%d tracks are on the table, %d of them already in an open deck.":
        "%d Titel stehen zur Auswahl, %d davon schon in einem offenen Deck.",
    "%d tracks are on the table.":
        "%d Titel stehen zur Auswahl.",
    "💾 Saving %s…":
        "💾 Speichere %s…",
    "➕  Adding %s tracks…":
        "➕  Füge %s Titel hinzu…",
    "🐂  Paso Doble in %d s":
        "🐂  Paso Doble startet in %d s",
    "⏸  %d s  (paused)":
        "⏸  %d s  (pausiert)",
    "⚠ Could not play: %s":
        "⚠ Konnte nicht abspielen: %s",
    "⚠ Playback failed: %s":
        "⚠ Wiedergabe fehlgeschlagen: %s",
    "unknown error":
        "unbekannter Fehler",
    "▴  fold back":
        "▴  wieder einklappen",
    "⏹  Stop":
        "⏹  Stopp",
    "Stop the run. A model that is still thinking is cut off and nothing is changed.":
        "Den Lauf abbrechen. Ein Modell, das noch nachdenkt, wird unterbrochen, und nichts wird geändert.",
    "Waiting for the model…":
        "Warte auf das Modell…",
    "Working…":
        "Arbeite…",
    "Stopping…":
        "Wird gestoppt…",
    "Check cancelled — drop or ➕ add files to run it again.":
        "Prüfung abgebrochen — zieh Dateien herein oder füge sie mit ➕ hinzu, um sie erneut zu starten.",
    "🧳  Export":
        "🧳  Exportieren",
    "✅ No gaps — every dance × class pool is healthy":
        "✅ Keine Lücken — jeder Pool aus Tanz × Klasse ist gut gefüllt",
    "Unfold the library pane":
        "Den Bibliotheksbereich aufklappen",
    "📚 Library browser shown":
        "📚 Bibliotheks-Browser eingeblendet",
    "📚 Library browser hidden":
        "📚 Bibliotheks-Browser ausgeblendet",
    "💾 Saving all playlists…":
        "💾 Speichere alle Playlists…",
    "🧳 Exporting venue bundle…":
        "🧳 Exportiere das Hallen-Paket…",
    "💾 Saving tournament-day playlists…":
        "💾 Speichere die Playlists des Turniertags…",
    "This list is empty.":
        "Diese Liste ist leer.",
    "This wishlist is empty.":
        "Diese Wunschliste ist leer.",
    "💾 Saving playlist…":
        "💾 Speichere die Playlist…",
    "💾 Saving wishlist…":
        "💾 Speichere die Wunschliste…",
    "▴ All playlists folded to tabs — click a tab to open one":
        "▴ Alle Playlists zu Reitern eingeklappt — klick auf einen Reiter, um eine zu öffnen",
    "▾ All playlists unfolded":
        "▾ Alle Playlists aufgeklappt",
    "Open the library pane back up":
        "Den Bibliotheksbereich wieder öffnen",
    "Collapse the whole pane —\n📚 Library and 🏆 Tournaments together":
        "Den ganzen Bereich einklappen —\n📚 Bibliothek und 🏆 Turniere zusammen",
    "📚 Library pane collapsed — the arrow in the tab bar opens it":
        "📚 Bibliotheksbereich eingeklappt — der Pfeil in der Reiterleiste öffnet ihn",
    "📚 Library pane open":
        "📚 Bibliotheksbereich offen",
    "It failed":
        "Fehlgeschlagen",
    "Stopped — nothing was changed.":
        "Gestoppt — nichts wurde geändert.",
    "AI playlist stopped.":
        "KI-Playlist gestoppt.",
    "Why these tracks":
        "Warum diese Titel",
    "📅 Planning tournament day…":
        "📅 Plane den Turniertag…",
    "Playlist not read":
        "Playlist nicht gelesen",
    "🎵 Checking music…":
        "🎵 Prüfe die Musik…",
    "✅  No tempo / length issues in the current tracks.":
        "✅  Keine Tempo- oder Längenprobleme in den aktuellen Titeln.",
    "No tracks in any open playlist — drag playlists into the 📂 tab to check loose files.":
        "Keine Titel in einer offenen Playlist — zieh Playlists in den 📂-Reiter, um lose Dateien zu prüfen.",
    "Method <span style='color:#b00'>(not used in playlist mode)</span>:":
        "Verfahren <span style='color:#b00'>(im Playlist-Modus nicht verwendet)</span>:",
    "📁 Reading the dropped folder…":
        "📁 Lese den hineingezogenen Ordner…",
    "Drop one or more audio files here, or click to browse":
        "Eine oder mehrere Audiodateien hier ablegen oder zum Auswählen klicken",
    "Empty — switch ✏ Edit on to fill it":
        "Leer — schalte ✏ Bearbeiten ein, um es zu füllen",
    "Editing ON — drop, drag, recolour and reshape the wall.\nSwitch off before the tournament so nothing moves by accident.":
        "Bearbeiten AN — Pads ablegen, verschieben, umfärben und die Wand umbauen.\nVor dem Turnier ausschalten, damit nichts versehentlich verrutscht.",
    "Locked: pads only fire. Click to edit the wall.":
        "Gesperrt: Pads spielen nur ab. Klicken, um die Wand zu bearbeiten.",
    "🎛 Cartwall shown":
        "🎛 Cartwall eingeblendet",
    "🎛 Cartwall hidden":
        "🎛 Cartwall ausgeblendet",
    "✏️ Editing highlights — playback paused; scrub to a crash, ⏯ to listen, 🎯 sets a mark at the playhead.":
        "✏️ Höhepunkte bearbeiten — Wiedergabe pausiert; spul zu einem Crash, ⏯ zum Anhören, 🎯 setzt eine Marke an der Abspielposition.",
    "✔ Highlights armed — playback pauses at the stop once so you can check it.":
        "✔ Höhepunkte scharf — die Wiedergabe hält einmal am Stopp, damit du ihn prüfen kannst.",
    "🖥 The presenter's screen was disconnected — it opens again when the screen is back.":
        "🖥 Der Bildschirm der Präsentation wurde getrennt — sie öffnet sich wieder, sobald er zurück ist.",
    "⏹ The next title was removed during the pause — nothing was started.":
        "⏹ Der nächste Titel wurde während der Pause entfernt — nichts wurde gestartet.",
    "✔  Done editing":
        "✔  Bearbeitung beenden",
    "No pause to jump to — tick 'Pause between songs' (and ⏭\nauto-advance) in the Playing-mode panel first.":
        "Keine Pause zum Anspringen — setz zuerst im Wiedergabe-Modus den Haken bei\n„Pause zwischen den Titeln“ (und ⏭ Auto-Weiter).",
    "duck":
        "leise",
    "instrumental (🎙️ Demucs-measured)":
        "Instrumental (🎙️ per Demucs gemessen)",
    "instrumental (🎙️ audio-detected)":
        "Instrumental (🎙️ am Audio erkannt)",
    "🎄 Christmas":
        "🎄 Weihnachten",
    "Similarity":
        "Ähnlichkeit",
    "Match":
        "Treffer",
    "Played together":
        "Zusammen gespielt",
    "Classes: %s":
        "Klassen: %s",
    "In these matching past lists:":
        "In diesen passenden früheren Listen:",
    "… +%d more":
        "… +%d weitere",
    "In %d of your playlists":
        "In %d deiner Playlists",
    "Played in: %s":
        "Gespielt in: %s",
    "▶ This list is playing: this switch decides what follows the title.":
        "▶ Diese Liste spielt gerade: Dieser Schalter entscheidet, was nach dem Titel kommt.",
    "in the archive since %s":
        "im Archiv seit %s",
    "%s, sounds like %s (%d%%)":
        "%s, klingt wie %s (%d %%)",
    "%s, sounds like %s (%s)":
        "%s, klingt wie %s (%s)",
    "sounds like '%s' of the first heat (%s)":
        "klingt wie „%s“ aus der ersten Gruppe (%s)",
    "sounds like '%s' of the first heat":
        "klingt wie „%s“ aus der ersten Gruppe",
    "timbre top %d %%":
        "Timbre Top %d %%",
    "groove top %d %%":
        "Groove Top %d %%",
    "melody top %d %%":
        "Melodie Top %d %%",
    "played %d× at the class":
        "%d× in der Startklasse gespielt",
    "never played at the class":
        "in der Startklasse nie gespielt",
    "a version of %s, played %d× at the class":
        "eine Version von %s — das Original lief %d× in der Startklasse",
    "a version of %s, never played at the class":
        "eine Version von %s — das Original lief nie in der Startklasse",
    # ── 🏆 the event plan's run ──
    "Titles to choose from":
        "Titel zur Auswahl",
    "%d from this event's past years, %d from other events' lists of the "
    "class, %d new in the archive, %d rarely played at the class (new ones "
    "included)":
        "%d aus früheren Jahren dieser Veranstaltung, %d von Listen anderer "
        "Turniere derselben Startklasse, %d neu im Archiv, %d selten in der "
        "Startklasse gespielt (neue eingeschlossen)",
    # ── 🏆 the event mode of the AI dialog ──
    "🏆  Event — a whole day of competitions, planned from its history":
        "🏆  Veranstaltung — ein ganzer Turniertag, geplant aus seiner Geschichte",
    "Paste the event's schedule. Every competition gets up to three\n"
    "variants, drawn from the event's earlier editions, the class's\n"
    "lists at other events and titles that sound like those.":
        "Füge den Zeitplan der Veranstaltung ein. Jedes Turnier bekommt bis zu drei\n"
        "Varianten, aus früheren Ausgaben der Veranstaltung, den Listen der Klasse\n"
        "bei anderen Veranstaltungen und Titeln, die ähnlich klingen.",
    "Paste the event's schedule, one competition per line:\n"
    "\n"
    "Sa: 10:00 HGR S STD 3-2-1\n"
    "So: 14:00 SEN I S STD (24) 2-1\n"
    "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6":
        "Füge den Zeitplan der Veranstaltung ein, ein Turnier pro Zeile:\n"
        "\n"
        "Sa: 10:00 HGR S STD 3-2-1\n"
        "So: 14:00 SEN I S STD (24) 2-1\n"
        "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6",
    "Competition":
        "Turnier",
    "Dances":
        "Tänze",
    "Heats per round":
        "Gruppen pro Runde",
    "What was read from the schedule. Double-click a cell to correct\n"
    "it — the class (S, A … D), the dance codes, the heats per round.":
        "Was aus dem Zeitplan gelesen wurde. Doppelklick auf eine Zelle, um sie zu\n"
        "korrigieren — die Klasse (S, A … D), die Tanzkürzel, die Gruppen pro Runde.",
    "Event:":
        "Veranstaltung:",
    "%d editions":
        "%d Ausgaben",
    "The event whose earlier editions are its history — the folders\n"
    "of that name in the playlist folder, whatever the year.":
        "Die Veranstaltung, deren frühere Ausgaben ihre Geschichte sind — die Ordner\n"
        "dieses Namens im Playlist-Ordner, egal aus welchem Jahr.",
    "Year planned:":
        "Geplantes Jahr:",
    "Editions of this year and later are not used as history.":
        "Ausgaben aus diesem und späteren Jahren zählen nicht als Geschichte.",
    "Earlier editions of the event":
        "Frühere Ausgaben der Veranstaltung",
    "Lists of the same class from other events":
        "Listen derselben Klasse von anderen Veranstaltungen",
    "New titles:":
        "Neue Titel:",
    "How much of a variant may be titles that came into the archive in\n"
    "the last 18 months and were never played at the class. \"Like last\n"
    "year\" takes none — it offers them as replacements instead.":
        "Wie viel einer Variante Titel sein dürfen, die in den letzten 18 Monaten\n"
        "ins Archiv kamen und in der Startklasse nie gespielt wurden. „Wie letztes\n"
        "Jahr“ nimmt keine — es bietet sie stattdessen als Ersatz an.",
    "Rarely played:":
        "Selten gespielt:",
    "How much of a variant may be titles played at most twice at the\n"
    "class so far, new ones included, the ones that sound like the\n"
    "played ones first. \"Like last year\" takes none.":
        "Wie viel einer Variante Titel sein dürfen, die in der Startklasse bisher\n"
        "höchstens zweimal gespielt wurden, neue eingeschlossen — die, die wie\n"
        "die gespielten klingen, zuerst. „Wie letztes Jahr“ nimmt keine.",
    "Variants:":
        "Varianten:",
    "Like last year":
        "Wie letztes Jahr",
    "Last year, renewed":
        "Wie letztes Jahr, erneuert",
    "Proven + fresh":
        "Bewährt + frisch",
    "Variety":
        "Abwechslung",
    "🤖  Let the AI check the drafts":
        "🤖  Die KI die Entwürfe prüfen lassen",
    "The model reads every draft and proposes swaps; each one is\n"
    "checked against the day before it goes in. Without it the\n"
    "computed plan is shown as it is.":
        "Das Modell liest jeden Entwurf und schlägt Tausche vor; jeder wird gegen\n"
        "den Tag geprüft, bevor er übernommen wird. Ohne die KI wird der\n"
        "berechnete Plan so gezeigt, wie er ist.",

    # ── 🏆 the event plan in the main window ──
    "Event plan":
        "Veranstaltungsplan",
    "No competition could be read from the schedule. Each line\n"
    "needs a class, a style (STD/LAT) or its dances in brackets,\n"
    "and the heats per round, e.g.  'HGR S STD 3-2-1'.":
        "Aus dem Zeitplan ließ sich kein Turnier lesen. Jede Zeile\n"
        "braucht eine Startklasse, eine Sektion (STD/LAT) oder ihre Tänze in Klammern\n"
        "und die Gruppen pro Runde, z. B.  „HGR S STD 3-2-1“.",
    "Tick at least one variant to plan.":
        "Hake mindestens eine Variante zum Planen an.",
    "no earlier edition found — the class lists carry the plan":
        "keine frühere Ausgabe gefunden — die Klassenlisten tragen den Plan",
    "not used":
        "nicht genutzt",
    "%d competitions. Earlier editions: %s":
        "%d Turniere. Frühere Ausgaben: %s",
    "Asking again about: %s":
        "Erneut gefragt zu: %s",
    "Event":
        "Veranstaltung",
    "The plan":
        "Der Plan",
    "🏆 Planning the event…":
        "🏆 Plane die Veranstaltung…",
    "🏆 %d competitions planned in %d variants":
        "🏆 %d Turniere in %d Varianten geplant",
    "The AI's limit held back: %s\n\n%s\n\n"
    "Wait and ask again by itself in %d minutes?":
        "Das Limit der KI hat zurückgehalten: %s\n\n%s\n\n"
        "Warten und in %d Minuten selbst erneut fragen?",
    "🏆 Asking the AI again at %s":
        "🏆 Frage die KI um %s erneut",
    "1 swap not applied, kept for your choice":
        "1 Tausch nicht übernommen, für deine Wahl aufbewahrt",
    "%d swaps not applied, kept for your choice":
        "%d Tausche nicht übernommen, für deine Wahl aufbewahrt",
    "the AI could not check it — the plan stands":
        "die KI konnte es nicht prüfen — der Plan steht",
    "held back by the AI's limit — ask again later":
        "vom Limit der KI zurückgehalten — frag später erneut",

    # ── 🏆 the event plan side by side ──
    "🏆 Event plan":
        "🏆 Veranstaltungsplan",
    "🟦 This event's lists":
        "🟦 Listen dieser Veranstaltung",
    "🟩 The class lists":
        "🟩 Listen der Klasse",
    "🟨 New titles":
        "🟨 Neue Titel",
    "🟧 Rarely played":
        "🟧 Selten gespielt",
    "⬜ Library":
        "⬜ Bibliothek",
    "AI: %s":
        "KI: %s",
    "↺ Replaces '%s' of last year — %s":
        "↺ Ersetzt „%s“ vom letzten Jahr — %s",
    "↻ Suggested instead: %s — %s":
        "↻ Stattdessen vorgeschlagen: %s — %s",
    "✋ The AI wanted '%s': %s":
        "✋ Die KI wollte „%s“: %s",
    "⏳ Ask about the held back now":
        "⏳ Zurückgehaltene jetzt fragen",
    "🔁 Second round":
        "🔁 2. Runde",
    "Ask the AI again where a swap was lost, to fill or improve those slots.":
        "Die KI erneut fragen, wo ein Tausch verloren ging, um diese Plätze\n"
        "zu füllen oder zu verbessern.",
    "Variant:":
        "Variante:",
    "The earlier editions had no list of this competition — "
    "'like similar competitions' fills it from the class lists 🟩":
        "Die früheren Ausgaben hatten keine Liste dieses Turniers — "
        "„wie ähnliche Turniere“ füllt es aus den Listen der Startklasse 🟩",
    "Like similar competitions":
        "Wie ähnliche Turniere",
    "The variant of the competition in front — each tab keeps its own, ✔ in "
    "its header; a click on a column header chooses it too":
        "Die Variante des vorne liegenden Turniers — jeder Tab behält seine "
        "eigene, ✔ in ihrem Spaltenkopf; ein Klick auf einen Spaltenkopf wählt "
        "sie auch",
    "Drag a title onto the same dance in another variant to take it over "
    "there, within its variant to swap the two":
        "Zieh einen Titel auf denselben Tanz einer anderen Variante, um ihn dort "
        "zu übernehmen, innerhalb seiner Variante, um die beiden zu tauschen",
    "'%s' ⇄ '%s': %s.\n\nSwap anyway?":
        "„%s“ ⇄ „%s“: %s.\n\nTrotzdem tauschen?",
    "▶ A title's ▶ or Space plays it, again stops it; Ctrl+click in the menu "
    "one to choose from":
        "▶ Das ▶ eines Titels oder die Leertaste spielt ihn, noch einmal stoppt "
        "ihn; Strg+Klick im Menü einen zur Auswahl",
    "📅 Into the tournament-day decks":
        "📅 In die Turniertag-Decks übernehmen",
    "🏆  Open the last plan":
        "🏆  Letzten Plan öffnen",
    "Show the last event plan side by side again, as you left it —\n"
    "nothing is planned or asked anew.":
        "Zeigt den letzten Veranstaltungsplan wieder im Vergleich, so wie du\n"
        "ihn verlassen hast — nichts wird neu geplant oder gefragt.",
    "⏳ Held back by the AI's limit: %s":
        "⏳ Vom Limit der KI zurückgehalten: %s",
    "⚠ The AI could not check: %s — the plan stands":
        "⚠ Die KI konnte nicht prüfen: %s — der Plan steht",
    "🔁 A swap was lost at: %s — a second round can fill or improve those slots":
        "🔁 Ein Tausch ging verloren bei: %s — eine 2. Runde kann diese Plätze "
        "füllen oder verbessern",
    "Double-click or right-click a title for what else fits there.  🟦 event  "
    "🟩 class lists  🟨 new  🟧 rarely played  ⬜ library  "
    "↺ replaces last year's title  ↻ a replacement is offered  "
    "✋ the AI wanted another":
        "Doppel- oder Rechtsklick auf einen Titel zeigt, was sonst dorthin passt.  "
        "🟦 Veranstaltung  🟩 Klassenlisten  🟨 neu  🟧 selten gespielt  ⬜ Bibliothek  "
        "↺ ersetzt einen Titel vom letzten Jahr  "
        "↻ ein Ersatz wird angeboten  ✋ die KI wollte einen anderen",
    "'Last year, renewed' found no sound-alike to swap here — the same as 'Like last year'":
        "„Wie letztes Jahr, erneuert“ fand hier keinen Klangzwilling zum Tauschen — "
        "gleich wie „Wie letztes Jahr“",
    "↺ Back to last year: %s":
        "↺ Zurück zum letzten Jahr: %s",
    "↻ Take the suggestion: %s":
        "↻ Vorschlag übernehmen: %s",
    "✋ The AI wanted: %s (%s)":
        "✋ Die KI wollte: %s (%s)",
    "'%s' %s.\n\nPut it in anyway?":
        "„%s“ %s.\n\nTrotzdem einsetzen?",
    "🏆  %s: %d competitions into %d deck(s)":
        "🏆  %s: %d Turniere in %d Deck(s)",
    # why a title did not go in — the planner's reasons, shown in the window
    "already plays that day":
        "läuft an dem Tag schon",
    "already plays in that round":
        "läuft in der Runde schon",
    "is offered for another slot":
        "ist für einen anderen Platz vorgeschlagen",
    "too many swaps":
        "zu viele Tausche",
    "that slot is swapped already":
        "der Platz ist schon getauscht",
}
