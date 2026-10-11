"""Dutch chrome, keyed by the English string as it stands in the code.

Built against planner/lang_de.py, which holds the full key set and the rules
(keys copied character for character, the emoji stays, only chrome). A key
missing here falls back to English on its own.

Vocabulary: je throughout. Heat = heat, Round = ronde, Playlist =
afspeellijst, Track = nummer (titel for a title), Settings = Instellingen,
Reference path = referentiepad, Practice = oefenen (oefen- in compounds).
Deck, Cartwall and Pad are left as they are; dances and rounds keep their
international English names.
"""

CATALOG = {
    "Cancel": "Annuleren",
    "Nb.": "Nr.",
    "none": "geen",
    "e.g. 6-3-2-1": "bijv. 6-3-2-1",
    "Group A–D": "Groep A–D",
    "Group E–H": "Groep E–H",
    "Preview-player options": "Opties van de voorbeeldspeler",
    "Fade every running pad out (Esc)": "Alle lopende pads uitfaden (Esc)",
    "Fade between music and timetable every":
        "Wisselen tussen muziek en tijdschema elke",
    "    Only tracks not already in my open playlists":
        "    Alleen nummers die nog in geen open afspeellijst staan",
    "Close": "Sluiten",
    "Replace": "Vervangen",
    "Reset": "Herstellen",
    "Generate": "Genereren",
    "Parse": "Inlezen",
    "Colour": "Kleur",
    "Heading": "Kop",
    "A new line at the end": "Een nieuwe regel aan het eind",
    "Take the selected line out": "De geselecteerde regel verwijderen",
    "Move the selected line up": "De geselecteerde regel omhoog",
    "Move the selected line down": "De geselecteerde regel omlaag",
    "Shortcut": "Sneltoets",
    "Class": "Klasse",
    "Class:": "Klasse:",
    "Style:": "Stijl:",
    "Method:": "Methode:",
    "Voice:": "Stem:",
    "Count:": "Aantal:",
    "Master volume": "Hoofdvolume",
    "Fade out": "Uitfaden",
    "Fade-out:": "Uitfaden:",
    "Own fade-out": "Eigen uitfade",
    "Wall fade-out": "Uitfade van de Cartwall",
    "Play length:": "Speelduur:",
    "Start after:": "Start na:",
    "Stop after highlight:": "Stop na hoogtepunt:",
    "Max tracks:": "Max. nummers:",
    "Proven": "Beproefd",
    "Top Proven": "Top beproefd",
    "Fresh": "Nieuw",
    "Mostly Proven": "Vooral beproefd",
    "Even Mix": "Gelijke mix",
    "Songs you have played before (fresh as fallback).":
        "Nummers die je al eerder hebt gedraaid (nieuwe als reserve).",
    "Only your most-played songs.": "Alleen je meest gedraaide nummers.",
    "Unused songs first (proven as fallback).":
        "Ongebruikte nummers eerst (beproefde als reserve).",
    "Proven + fresh together, but favors songs you have played before.":
        "Beproefd + nieuw samen, maar met voorkeur voor nummers die je al eerder hebt gedraaid.",
    "Proven + fresh with no preference — equal chance, maximum variety.":
        "Beproefd + nieuw zonder voorkeur — gelijke kans, maximale afwisseling.",
    "🌐  Search mode: Global — whole repository":
        "🌐  Zoekmodus: Globaal — de hele verzameling",
    "🎯  Search mode: Favorites library only":
        "🎯  Zoekmodus: alleen de favorietenbibliotheek",
    "Library: %d files": "Bibliotheek: %d bestanden",
    "Favorites: %d": "Favorieten: %d",
    "Library loaded — %s MP3 files, %s favorites songs, %s audio cached.":
        "Bibliotheek geladen — %s MP3-bestanden, %s favoriete nummers, %s in de audiocache.",
    "— Indexes (analyzed / total) —": "— Indexen (geanalyseerd / totaal) —",
    "🔗 Fingerprints: %s": "🔗 Vingerafdrukken: %s",
    "📊 Loudness: %s": "📊 Luidheid: %s",
    "🔇 Silences: %s": "🔇 Stiltes: %s",
    "🐂 PD highlights: %s": "🐂 PD-hoogtepunten: %s",
    "🎙️ Demucs vocals: %s measured": "🎙️ Demucs-zang: %s gemeten",
    "🌐 Global index: %s files, %s analyzed":
        "🌐 Globale index: %s bestanden, %s geanalyseerd",
    "🌐 Global index: %s files built (loads on first global search)":
        "🌐 Globale index: %s bestanden gebouwd (laadt bij de eerste globale zoekopdracht)",
    "🌐 Global index: not built (⚙ Settings to build)":
        "🌐 Globale index: niet gebouwd (⚙ Instellingen om te bouwen)",
    "(OpenL3 not available)": "(OpenL3 niet beschikbaar)",
    "(chroma not available)": "(Chroma niet beschikbaar)",
    "no Paso Doble in the library": "geen Paso Doble in de bibliotheek",
    "%s file(s) in the favorites library have no\n"
    "analysis yet":
        "%s bestand(en) in de favorietenbibliotheek zijn nog niet\n"
        "geanalyseerd",
    "an index of the favorites library is not complete yet":
        "een index van de favorietenbibliotheek is nog niet compleet",
    "🧱 Build ALL caches — %s. Asks for the scope\n"
    "first; reuses everything already cached and can be cancelled.":
        "🧱 ALLE caches bouwen — %s. Vraagt eerst naar de\n"
        "omvang; hergebruikt alles wat al in de cache staat en kan worden geannuleerd.",
    "audio fingerprints": "audiovingerafdrukken",
    "loudness": "luidheid",
    "silences": "stiltes",
    "PD highlights": "PD-hoogtepunten",
    "librosa audio analysis (no working audio decoder)":
        "librosa-audioanalyse (geen werkende audiodecoder)",
    "loudness + silences (no ffmpeg)": "luidheid + stiltes (geen ffmpeg)",
    "%s (not installed)": "%s (niet geïnstalleerd)",
    "\n"
    "\n"
    "Skipped: %s":
        "\n"
        "\n"
        "Overgeslagen: %s",
    "Nothing can be built on this machine right now.":
        "Op deze computer kan nu niets worden gebouwd.",
    "Build every index over %s tracks from %s?":
        "Elke index bouwen over %s nummers uit %s?",
    "Runs %s back-to-back. Each is slow the first time, then cached; reuses anything already built. You can cancel between or within steps.":
        "Voert %s na elkaar uit. Elk is de eerste keer traag en daarna gecachet; hergebruikt alles wat al gebouwd is. Je kunt tussen of tijdens de stappen annuleren.",
    "Read-only — your audio files are never modified.":
        "Alleen lezen — je audiobestanden worden nooit gewijzigd.",
    "the favorites library": "de favorietenbibliotheek",
    "the whole repository": "de hele verzameling",
    "the whole repository + favorites library":
        "de hele verzameling + de favorietenbibliotheek",
    "All %s files in %s are already analyzed.":
        "Alle %s bestanden in %s zijn al geanalyseerd.",
    "%s of %s files in %s need analysis (~%s min).\n"
    "\n"
    "Analysis only reads your files — never modifies them. Results are cached.\n"
    "\n"
    "Run now?":
        "%s van %s bestanden in %s moeten worden geanalyseerd (~%s min).\n"
        "\n"
        "De analyse leest je bestanden alleen — wijzigt ze nooit. Resultaten worden gecachet.\n"
        "\n"
        "Nu starten?",
    "Audio index: analyzing %s files…":
        "Audio-index: %s bestanden analyseren…",
    "Building audio index (%s)…": "Audio-index bouwen (%s)…",
    "Global index: %s/%s%s": "Globale index: %s/%s%s",
    "  (%s errors)": "  (%s fouten)",
    " (%s errors)": " (%s fouten)",
    "Audio index built — %s files analyzed":
        "Audio-index gebouwd — %s bestanden geanalyseerd",
    "Analyzed %s files in %s": "%s bestanden geanalyseerd in %s",
    ".\n"
    "Similarity search will now match across them.":
        ".\n"
        "Zoeken naar vergelijkbare nummers werkt nu over al deze bestanden.",
    "Audio index cancelled — %s files analyzed so far (progress is cached).":
        "Audio-index geannuleerd — tot nu toe %s bestanden geanalyseerd (de voortgang blijft bewaard).",
    "🧹  Checking which files are still on disk…":
        "🧹  Controleren welke bestanden nog op de schijf staan…",
    "🧱  Looking for ffmpeg and the AI backends…":
        "🧱  Zoeken naar ffmpeg en de AI-backends…",
    "🧱  Checking what this machine can build…":
        "🧱  Controleren wat deze computer kan bouwen…",
    "librosa is not installed, so tempo and timbre cannot be measured and similar-track search stays unavailable.\n"
    "\n"
    "Install it, then restart the app:\n"
    "    pip install librosa":
        "librosa is niet geïnstalleerd, dus tempo en timbre kunnen niet worden gemeten en zoeken naar vergelijkbare nummers is niet beschikbaar.\n"
        "\n"
        "Installeer het en start de app opnieuw:\n"
        "    pip install librosa",
    "Nothing on this computer can decode an MP3, so tempo and timbre cannot be measured and similar-track search stays unavailable.\n"
    "\n"
    "Install ffmpeg and make sure it is on PATH (not just next to the app), then restart.":
        "Niets op deze computer kan een MP3 decoderen, dus tempo en timbre kunnen niet worden gemeten en zoeken naar vergelijkbare nummers is niet beschikbaar.\n"
        "\n"
        "Installeer ffmpeg en zorg dat het in het PATH staat (niet alleen naast de app), en start dan opnieuw.",
    "The audio decoder could not read %s, so the analysis would fail for every file. See the log for the error.":
        "De audiodecoder kon %s niet lezen, dus de analyse zou bij elk bestand mislukken. De fout staat in het logboek.",
    "Nothing could be built for these, and nothing will be:":
        "Hiervoor kon niets worden gebouwd, en dat blijft zo:",
    "Caches built for %s — with problems, see the log.":
        "Caches gebouwd voor %s — met problemen, zie het logboek.",
    "Finished for %s, but not everything worked:":
        "Klaar voor %s, maar niet alles is gelukt:",
    "Ran: %s.": "Uitgevoerd: %s.",
    "All caches built for %s.": "Alle caches gebouwd voor %s.",
    "All caches are built for %s.": "Alle caches zijn gebouwd voor %s.",
    "Build all caches — librosa: analyzing %s files…":
        "Alle caches bouwen — librosa: %s bestanden analyseren…",
    "Build all caches — %s…": "Alle caches bouwen — %s…",
    "Build all caches — %s embeddings…": "Alle caches bouwen — %s-embeddings…",
    "mostly: %s": "meestal: %s",
    "%s: %s file(s) failed": "%s: %s bestand(en) mislukt",
    ", %s cached": ", %s gecachet",
    "%s: %s file(s) skipped — not on disk any more":
        "%s: %s bestand(en) overgeslagen — niet meer op de schijf",
    "Build all caches cancelled during %s — %s done so far (cached).":
        "Alle caches bouwen geannuleerd tijdens %s — %s tot nu toe klaar (gecachet).",
    "🎛  Both — plan and play": "🎛  Beide — plannen en afspelen",
    "The full app: build playlists at home, run them at the tournament.":
        "De volledige app: maak thuis afspeellijsten, speel ze af op het toernooi.",
    "📝  Planner only": "📝  Alleen planner",
    "Build and curate playlists. The tournament floor's playing panel, its timed play / announcements and the 🎛 cartwall stay hidden.":
        "Afspeellijsten bouwen en bijhouden. Het afspeelpaneel voor de toernooivloer, het getimed afspelen / de aankondigingen en de 🎛 Cartwall blijven verborgen.",
    "▶  Player only": "▶  Alleen speler",
    "Run prepared playlists at the venue. Everything that generates or checks a playlist stays hidden.":
        "Voorbereide afspeellijsten in de zaal afspelen. Alles wat een afspeellijst genereert of controleert blijft verborgen.",
    "◧  Beside the playlists — at the head of the ▶ Playing panel":
        "◧  Naast de afspeellijsten — bovenaan het paneel ▶ Afspelen",
    "The player card stands in the left panel, above the timed-play controls.":
        "De spelerkaart staat in het linkerpaneel, boven de bediening voor getimed afspelen.",
    "▤  Above the playlists — one wide strip over the decks":
        "▤  Boven de afspeellijsten — een brede strook over de decks",
    "The same player, laid out along the width above the decks — the shape a DJ desk uses. It shows in ▶ Playing mode.":
        "Dezelfde speler, over de volle breedte boven de decks — de vorm van een DJ-tafel. Hij verschijnt in de modus ▶ Afspelen.",
    "🎬  FFmpeg — Qt's own engine (default)":
        "🎬  FFmpeg — Qt's eigen engine (standaard)",
    "🎬  FFmpeg — Qt's own engine": "🎬  FFmpeg — Qt's eigen engine",
    "🪟  Windows Media Foundation — the OS's own":
        "🪟  Windows Media Foundation — die van het besturingssysteem",
    "🔊  Automatic — whatever this system uses (default)":
        "🔊  Automatisch — wat dit systeem gebruikt (standaard)",
    "☀  Light (default)": "☀  Licht (standaard)",
    "White decks, dark text: the look every colour in the app was picked for.":
        "Witte decks, donkere tekst: het uiterlijk waarvoor elke kleur van de app is gekozen.",
    "🌙  Dark": "🌙  Donker",
    "Platform looks": "Platformlooks",
    "Desk looks": "Tafellooks",
    "Modern looks": "Moderne looks",
    "No preview picture for this theme.":
        "Geen voorbeeldafbeelding voor dit thema.",
    "A look brings its own accent colour — this one is for Light and Dark.":
        "Een look brengt zijn eigen accentkleur mee — deze geldt voor Licht en Donker.",
    "Windows 11 · Light": "Windows 11 · Licht",
    "Fluent: 4 px corners, Segoe UI Variable, the Windows blue and an accent line under the active field.":
        "Fluent: hoeken van 4 px, Segoe UI Variable, het Windows-blauw en een accentlijn onder het actieve veld.",
    "Windows 11 · Dark": "Windows 11 · Donker",
    "Fluent in dark: the Windows 11 dark greys with the light blue accent.":
        "Fluent in donker: de donkergrijze tinten van Windows 11 met het lichtblauwe accent.",
    "macOS · Light": "macOS · Licht",
    "Aqua as of Sonoma: 6 px corners, a solid blue selection with white text and an accent ring around the active field.":
        "Aqua zoals in Sonoma: hoeken van 6 px, een fel blauwe selectie met witte tekst en een accentring rond het actieve veld.",
    "macOS · Dark": "macOS · Donker",
    "Aqua in dark mode: charcoal panes, grey keys, the bright system blue.":
        "Aqua in donkere modus: antraciet vlakken, grijze toetsen, het heldere systeemblauw.",
    "Linux GNOME · Light": "Linux GNOME · Licht",
    "Adwaita: 6 px corners, flat grey buttons without a frame, the GNOME blue.":
        "Adwaita: hoeken van 6 px, platte grijze knoppen zonder rand, het GNOME-blauw.",
    "Linux GNOME · Dark": "Linux GNOME · Donker",
    "Adwaita dark: soft charcoal, flat buttons, the GNOME blue.":
        "Adwaita donker: zacht antraciet, platte knoppen, het GNOME-blauw.",
    "Graphite, keys lit from above like a mixing desk, a pressed key glows blue. Lettering in Bahnschrift.":
        "Grafiet, toetsen van bovenaf verlicht zoals op een mengtafel, een ingedrukte toets licht blauw op. Letter Bahnschrift.",
    "Jet black with metal gradients and orange as the light: harder and higher in contrast, like a hardware controller in a dark hall.":
        "Gitzwart met metalen verlopen en oranje als licht: harder en met meer contrast, zoals een hardwarecontroller in een donkere zaal.",
    "Flat night blue with cyan as the light: whatever is on gets a glowing rim instead of a fill. Rounder corners.":
        "Plat nachtblauw met cyaan als licht: wat aan staat krijgt een gloeiende rand in plaats van een vulling. Rondere hoeken.",
    "The bright desk: brushed aluminium, keys lit from above, orange as the accent. For daylight and bright halls.":
        "De lichte tafel: geborsteld aluminium, toetsen van bovenaf verlicht, oranje als accent. Voor daglicht en lichte zalen.",
    "Graphite": "Grafiet",
    "Calm neutral dark: near-white text on graphite, soft filled buttons with round corners, a clear blue. Easy on the eyes for a long evening.":
        "Rustig neutraal donker: bijna witte tekst op grafiet, zacht gevulde knoppen met ronde hoeken, een helder blauw. Rustig voor de ogen op een lange avond.",
    "Midnight": "Middernacht",
    "Deep navy with a teal accent and pill-shaped buttons: modern and quiet, the text stays crisp against the dark blue.":
        "Diep marineblauw met een petrol accent en pilvormige knoppen: modern en rustig, de tekst blijft scherp tegen het donkerblauw.",
    "Dark with a violet accent: soft filled buttons, warm dark greys, light lavender for links and focus.":
        "Donker met een violet accent: zacht gevulde knoppen, warme donkergrijze tinten, licht lavendel voor links en focus.",
    "Paper": "Papier",
    "Clean and bright: white panes, nearly black text, soft grey buttons with round corners and a strong blue. Crisp in daylight.":
        "Strak en licht: witte vlakken, bijna zwarte tekst, zachte grijze knoppen met ronde hoeken en een krachtig blauw. Scherp bij daglicht.",
    "High contrast · Dark": "Hoog contrast · Donker",
    "Black and white with a yellow accent, 2 px frames and a yellow selection: readable from across the hall and in bright stage light.":
        "Zwart en wit met een geel accent, randen van 2 px en een gele selectie: leesbaar van de andere kant van de zaal en in fel podiumlicht.",
    "High contrast · Light": "Hoog contrast · Licht",
    "Black on white with a deep blue accent and 2 px frames: the most readable light look, also on a weak projector or laptop screen.":
        "Zwart op wit met een diepblauw accent en randen van 2 px: de best leesbare lichte look, ook op een zwakke beamer of laptopscherm.",
    "The same colours put through a lightness flip, so a warning stays red and the ▶ player panel — dark already — is left as it is.":
        "Dezelfde kleuren door een helderheidsomkering gehaald, zodat een waarschuwing rood blijft en het ▶ spelerpaneel — al donker — blijft zoals het is.",
    "  %s  —  pick a colour…": "  %s  —  kies een kleur…",
    "Accent colour": "Accentkleur",
    "  ~%s left": "  ~%s over",
    "(%s errors)": "(%s fouten)",
    ", %s errors": ", %s fouten",
    "%s done — %s %s": "%s klaar — %s %s",
    " (all were already cached)": " (alles stond al in de cache)",
    "%s cancelled — %s %s so far.": "%s geannuleerd — %s %s tot nu toe.",
    "%s failed:\n"
    "%s":
        "%s mislukt:\n"
        "%s",
    "files cached": "bestanden gecachet",
    "tracks measured": "nummers gemeten",
    "tracks probed": "nummers onderzocht",
    "tracks analyzed": "nummers geanalyseerd",
    "All %s files are already cached.\n"
    "\n"
    "Re-analyze the whole library anyway to refresh the measured tempo with the current method?":
        "Alle %s bestanden staan al in de cache.\n"
        "\n"
        "Toch de hele bibliotheek opnieuw analyseren om het gemeten tempo met de huidige methode te vernieuwen?",
    "%s files will be re-analyzed (~%s min, cached afterwards).\n"
    "\n"
    "Run now?":
        "%s bestanden worden opnieuw geanalyseerd (~%s min, daarna gecachet).\n"
        "\n"
        "Nu starten?",
    "%s files need librosa analysis (~%s min, cached afterwards).\n"
    "\n"
    "Run now?":
        "%s bestanden hebben een librosa-analyse nodig (~%s min, daarna gecachet).\n"
        "\n"
        "Nu starten?",
    "Audio analysis started — %s files…":
        "Audioanalyse gestart — %s bestanden…",
    "Analyze Audio (Timbre)": "Audio analyseren (timbre)",
    "Re-analyze All Audio": "Alle audio opnieuw analyseren",
    "Measure the loudness of the whole library (%s tracks)?\n"
    "\n"
    "Already-measured tracks are skipped — only new ones are\n"
    "decoded (≈1 s each). You can cancel anytime; results so far\n"
    "are kept.":
        "De luidheid van de hele bibliotheek meten (%s nummers)?\n"
        "\n"
        "Al gemeten nummers worden overgeslagen — alleen nieuwe\n"
        "worden gedecodeerd (≈1 s per nummer). Je kunt altijd annuleren;\n"
        "de resultaten tot dan blijven bewaard.",
    "Probe the silent stretches of the whole library (%s tracks, %s not probed yet)?\n"
    "\n"
    "Already-probed tracks are skipped — only new ones are\n"
    "decoded (≈0.3 s each). You can cancel anytime; results so far\n"
    "are kept.":
        "De stille stukken van de hele bibliotheek onderzoeken (%s nummers, %s nog niet onderzocht)?\n"
        "\n"
        "Al onderzochte nummers worden overgeslagen — alleen nieuwe\n"
        "worden gedecodeerd (≈0,3 s per nummer). Je kunt altijd annuleren;\n"
        "de resultaten tot dan blijven bewaard.",
    "All %s tracks already have a measured vocal share.":
        "Alle %s nummers hebben al een gemeten zangaandeel.",
    "Separate the vocals of %s not-yet-measured tracks (~%s min)?\n"
    "\n"
    "Demucs actually extracts the singing from each track — slow\n"
    "(~7 s per track) but far more reliable than the heuristics.\n"
    "You can cancel anytime; results so far are kept.":
        "De zang van %s nog niet gemeten nummers scheiden (~%s min)?\n"
        "\n"
        "Demucs haalt de zang echt uit elk nummer — traag\n"
        "(~7 s per nummer) maar veel betrouwbaarder dan de heuristieken.\n"
        "Je kunt altijd annuleren; de resultaten tot dan blijven bewaard.",
    "Detect the highlights of every Paso Doble in the library (%s tracks)?\n"
    "\n"
    "Already-analyzed tracks are skipped — only new ones are\n"
    "decoded (a few seconds each). You can cancel anytime;\n"
    "results so far are kept.":
        "De hoogtepunten van elke Paso Doble in de bibliotheek detecteren (%s nummers)?\n"
        "\n"
        "Al geanalyseerde nummers worden overgeslagen — alleen nieuwe\n"
        "worden gedecodeerd (een paar seconden per nummer). Je kunt altijd annuleren;\n"
        "de resultaten tot dan blijven bewaard.",
    "Fresh mix:": "Mix van nieuwe:",
    "Pause music:": "Pauzemuziek:",
    "Pause music volume:": "Volume pauzemuziek:",
    "No pause music": "Geen pauzemuziek",
    "Set clock to": "Klok zetten op",
    "Draw tracks from": "Nummers kiezen uit",
    "Songs needed for:": "Nummers nodig voor:",
    "What to build": "Wat er gemaakt wordt",
    "Round Strategy": "Rondestrategie",
    "Middle of the round": "Midden van de ronde",
    "Lower — T%s": "Laag — T%s",
    "Middle — T%s": "Midden — T%s",
    "Upper — T%s": "Hoog — T%s",
    "Please wait": "Even geduld",
    "Failed.": "Mislukt.",
    "Add a page": "Pagina toevoegen",
    "Next page": "Volgende pagina",
    "Previous page": "Vorige pagina",
    "Keep all": "Alles behouden",
    "Keep both": "Beide behouden",
    "Keep existing": "Bestaande behouden",
    "No key": "Geen toets",
    "Print / Export": "Afdrukken / Exporteren",
    "USB export": "USB-export",
    "Duplicate titles": "Dubbele titels",
    "Possible duplicate": "Mogelijk dubbel",
    "Check duplicates": "Op dubbelen controleren",
    "Cartwall shortcuts": "Sneltoetsen van de Cartwall",
    "Pad settings": "Padinstellingen",
    "Clear this pad": "Deze pad leegmaken",
    "Columns in the library": "Kolommen in de bibliotheek",
    "Open wishlists": "Open wensenlijsten",
    "Analyze PD highlights": "PD-hoogtepunten analyseren",
    "Vocal + instr.": "Zang + instr.",
    "Use Timbre Similarity": "Timbre-overeenkomst gebruiken",
    "Load models": "Modellen laden",
    "Copy to clipboard": "Naar het klembord kopiëren",
    "Press the keys you want": "Druk op de gewenste toetsen",
    "Restore slot defaults": "Standaardtoetsen herstellen",
    "Back to %s…%s, leaving the pad keys alone":
        "Terug naar %s…%s, de padtoetsen blijven ongemoeid",
    "\n"
    "Key: %s":
        "\n"
        "Toets: %s",
    "\n"
    "⚠️ File not found":
        "\n"
        "⚠️ Bestand niet gevonden",
    "Remove this page": "Deze pagina verwijderen",
    "Remove this competition": "Deze wedstrijd verwijderen",
    "Save all playlists": "Alle afspeellijsten opslaan",
    "Save tournament day": "Toernooidag opslaan",
    "Clear all tournament-day playlists":
        "Alle afspeellijsten van de toernooidag leegmaken",
    "All dances": "Alle dansen",
    "All classes": "Alle klassen",
    "All categories": "Alle categorieën",
    "Added: all": "Toegevoegd: alle",
    "Plays: all": "Gespeeld: alle",
    "Parse schedule": "Tijdschema inlezen",
    "Filter by the instrumental tag": "Filteren op het instrumentaal-kenmerk",
    "Short dance names  (LW, SB)": "Korte dansnamen  (LW, SB)",
    "Auto re-roll round on strategy change":
        "Ronde opnieuw loten bij strategiewissel",
    "Re-analyze tracks that already have highlights":
        "Nummers met bestaande hoogtepunten opnieuw analyseren",
    "An .m3u playlist file": "Een .m3u-afspeellijstbestand",
    "Focused playlist (current deck)": "Actieve afspeellijst (huidige deck)",
    "Number of titles in this wishlist": "Aantal titels in deze wensenlijst",
    "Own looks": "Eigen looks",
    "none yet — ＋ New look…": "nog geen — ＋ Nieuwe look…",
    "＋  New look…": "＋  Nieuwe look…",
    "A look of your own, starting as a copy of the selected one.":
        "Een eigen look, eerst een kopie van de geselecteerde.",
    "✎  Edit…": "✎  Bewerken…",
    "🗑  Delete": "🗑  Verwijderen",
    "Import…": "Importeren…",
    "Add a look someone exported.":
        "Een look toevoegen die iemand heeft geëxporteerd.",
    "Export…": "Exporteren…",
    "Save the selected look of your own as a file, to pass it on.":
        "De geselecteerde eigen look als bestand opslaan, om hem door te geven.",
    "A look of your own, kept on this computer. ✎ Edit changes it, Export passes it on.":
        "Een eigen look, bewaard op deze computer. ✎ Bewerken wijzigt hem, Exporteren geeft hem door.",
    "%s (own)": "%s (eigen)",
    "Look not saved": "Look niet opgeslagen",
    "The looks file could not be written. The log names the reason.":
        "Het looksbestand kon niet worden geschreven. Het logboek noemt de reden.",
    "Delete look": "Look verwijderen",
    "Delete the look “%s”? This cannot be undone; an exported file of it stays.":
        "De look „%s” verwijderen? Dit kan niet ongedaan worden gemaakt; een geëxporteerd bestand ervan blijft bestaan.",
    "Import a look": "Een look importeren",
    "Look not imported": "Look niet geïmporteerd",
    "This file holds no look the app can use:\n"
    "%s":
        "Dit bestand bevat geen look die de app kan gebruiken:\n"
        "%s",
    "Export the look": "De look exporteren",
    "Look not exported": "Look niet geëxporteerd",
    "The file could not be written:\n"
    "%s":
        "Het bestand kon niet worden geschreven:\n"
        "%s",
    "🎨  Edit look": "🎨  Look bewerken",
    "Family: %s. The details it shares with the built-in looks of that group stay: faders, checkboxes, headers.":
        "Familie: %s. Wat hij deelt met de ingebouwde looks van die groep blijft: faders, selectievakjes, kopregels.",
    "Grounds": "Vlakken",
    "Window": "Venster",
    "The ground of the main window and the dialogs.":
        "De achtergrond van het hoofdvenster en de dialogen.",
    "Lists and fields": "Lijsten en velden",
    "Tables, lists and text fields.": "Tabellen, lijsten en tekstvelden.",
    "Every other row": "Elke tweede rij",
    "The second row colour of a table.": "De tweede rijkleur van een tabel.",
    "Headers": "Kopregels",
    "Table headers and the menu bar.": "Tabelkoppen en de menubalk.",
    "The ground of a tooltip.": "De achtergrond van een tooltip.",
    "Buttons": "Knoppen",
    "Button face": "Knopvlak",
    "A button at rest.": "Een knop in rust.",
    "Under the mouse": "Onder de muis",
    "A button the mouse is over.": "Een knop waar de muis boven hangt.",
    "Pressed": "Ingedrukt",
    "A button held down.": "Een ingedrukt gehouden knop.",
    "Light from above": "Licht van boven",
    "Set, a button fades from this colour down to its face, like a key on a mixing desk. Off, the face is flat.":
        "Aan: een knop verloopt van deze kleur omlaag naar zijn vlak, zoals een toets op een mengtafel. Uit: het vlak is egaal.",
    "Header light from above": "Kopregellicht van boven",
    "The same fade for the table headers and the deck title strips.":
        "Hetzelfde verloop voor de tabelkoppen en de titelbalken van de decks.",
    "Lines": "Lijnen",
    "Hairlines": "Haarlijnen",
    "Frames, the table grid and separators.":
        "Kaders, het tabelraster en scheidingslijnen.",
    "Outlines": "Omtrekken",
    "A control's frame and the scrollbar handle.":
        "Het kader van een bedieningselement en de greep van de schuifbalk.",
    "All ordinary text.": "Alle gewone tekst.",
    "Dim text": "Vage tekst",
    "Disabled text, placeholders and side notes.":
        "Uitgeschakelde tekst, plaatshouders en kanttekeningen.",
    "The default button and a switched-on toggle.":
        "De standaardknop en een ingeschakelde schakelaar.",
    "Text on the accent": "Tekst op het accent",
    "The caption on an accent fill.": "Het opschrift op een accentvlak.",
    "Accent as text": "Accent als tekst",
    "Links, focus rings and the round bands' lettering.":
        "Links, focusringen en de letters van de rondebanden.",
    "Selection": "Selectie",
    "Selected row": "Geselecteerde rij",
    "The band of the selected row.": "De band van de geselecteerde rij.",
    "Text on the selection": "Tekst op de selectie",
    "The text in that band.": "De tekst in die band.",
    "Fade": "Verloop",
    "off": "uit",
    "Shape and lettering": "Vorm en letter",
    "Corners:": "Hoeken:",
    "Buttons:": "Knoppen:",
    "Tabs:": "Tabbladen:",
    "Font:": "Lettertype:",
    "Outlined": "Omlijnd",
    "Flat, no frame": "Plat, zonder kader",
    "Desk key, lit from above": "Tafeltoets, van boven verlicht",
    "Dark, glowing rim when on": "Donker, gloeiende rand als hij aan staat",
    "Soft filled": "Zacht gevuld",
    "Pill, fully rounded": "Pil, helemaal afgerond",
    "2 px frame, high contrast": "Kader van 2 px, hoog contrast",
    "Underlined": "Onderstreept",
    "Segmented": "Gesegmenteerd",
    "Desk keys": "Tafeltoetsen",
    "Pills": "Pillen",
    "Ring around the field": "Ring rond het veld",
    "Line under the field": "Lijn onder het veld",
    "Saved looks are kept on this computer. The app takes a changed look on its next start.":
        "Opgeslagen looks blijven op deze computer. De app neemt een gewijzigde look over bij de volgende start.",
    "⚠ Hard to read:": "⚠ Moeilijk leesbaar:",
    "✓ Every text reads clearly against its ground.":
        "✓ Elke tekst steekt duidelijk af tegen zijn achtergrond.",
    "%s: %.1f : 1, should be at least %.1f":
        "%s: %.1f : 1, zou minstens %.1f moeten zijn",
    "Text on lists": "Tekst op lijsten",
    "Text on every other row": "Tekst op elke tweede rij",
    "Text on the window": "Tekst op het venster",
    "Text on buttons": "Tekst op knoppen",
    "Dim text on lists": "Vage tekst op lijsten",
    "Playing": "Afspelen",
    "Group": "Groep",
    "Button": "Knop",
    "Switched on": "Ingeschakeld",
    "Disabled": "Uitgeschakeld",
    "Search…": "Zoeken…",
    "Ticked": "Aangevinkt",
    "Dim text: a hint, a placeholder.":
        "Vage tekst: een hint, een plaatshouder.",
    "Welcome to DanceSport Planner & Player":
        "Welkom bij DanceSport Planner & Player",
    "AI Song Suggestions (OpenRouter)":
        "AI-suggesties voor nummers (OpenRouter)",
    "Previous session crashed": "Vorige sessie is vastgelopen",
    "Settings — app mode, library paths & analysis":
        "Instellingen — modus, bibliotheekpaden en analyse",
    "Settings — library paths, global search & analysis":
        "Instellingen — bibliotheekpaden, globaal zoeken en analyse",
    "⌨  Keyboard shortcuts  (F1)": "⌨  Sneltoetsen  (F1)",
    "⛶  Fullscreen  (F11)": "⛶  Volledig scherm  (F11)",
    "⛶  Exit Fullscreen  (F11)": "⛶  Volledig scherm verlaten  (F11)",
    "⛶  Fullscreen clock: only the time (20:45:12), no date":
        "⛶  Klok op volledig scherm: alleen de tijd (20:45:12), geen datum",
    "Shortcuts (F1), manual and about this app":
        "Sneltoetsen (F1), handleiding en over deze app",
    "📖  Manual": "📖  Handleiding",
    "ℹ  About…": "ℹ  Over…",
    "About": "Over",
    "Music is playing": "Er speelt muziek",
    "Music is playing. Quit anyway and stop it?":
        "Er speelt muziek. Toch afsluiten en de muziek stoppen?",
    "Author": "Auteur",
    "License": "Licentie",
    "App icon": "App-pictogram",
    "Icons": "Pictogrammen",
    "Voices": "Stemmen",
    "AI-generated, non-commercial use":
        "AI-gegenereerd, alleen niet-commercieel gebruik",
    "Libraries": "Bibliotheken",
    "all licences": "alle licenties",
    "Which library should this index cover?":
        "Welke bibliotheek moet deze index omvatten?",
    "What should go into the venue bundle?": "Wat moet er in het zaalpakket?",
    "Settings saved.": "Instellingen opgeslagen.",
    "Database cleanup done.": "Database opgeruimd.",
    "Loading library…": "Bibliotheek laden…",
    "Loading music library…": "Muziekbibliotheek laden…",
    "Library: loading…": "Bibliotheek: laden…",
    "Generating playlist…": "Afspeellijst maken…",
    "Asking the model…": "Het model vragen…",
    "Asking the model for a playlist…":
        "Het model om een afspeellijst vragen…",
    "Fetching the model list…": "Modellenlijst ophalen…",
    "Cancelling…": "Annuleren…",
    "Analysis failed.": "Analyse mislukt.",
    "AI playlist failed.": "AI-afspeellijst mislukt.",
    "AI playlist: nothing usable.": "AI-afspeellijst: niets bruikbaars.",
    "Practice failed.": "Oefenen mislukt.",
    "Practice: no matching tracks.": "Oefenen: geen passende nummers.",
    "Global index failed.": "Globale index mislukt.",
    "Similar-track analysis failed.":
        "Analyse van vergelijkbare nummers mislukt.",
    "Repository scan cancelled.": "Doorzoeken van de repository geannuleerd.",
    "Import: no tracks detected": "Import: geen nummers herkend",
    "No parseable suggestions returned.":
        "Geen bruikbare suggesties ontvangen.",
    "Could not fetch models (using fallback list).":
        "Modellen konden niet worden opgehaald (reservelijst wordt gebruikt).",
    "Load the music library first.": "Laad eerst de muziekbibliotheek.",
    "Nothing to clear — all playlists are empty.":
        "Niets te legen — alle afspeellijsten zijn leeg.",
    "Nothing to export — all playlists are empty.":
        "Niets te exporteren — alle afspeellijsten zijn leeg.",
    "Nothing to save — all playlists are empty.":
        "Niets op te slaan — alle afspeellijsten zijn leeg.",
    "Nothing to save — the day decks are empty.":
        "Niets op te slaan — de dagdecks zijn leeg.",
    "Nothing to save yet.": "Nog niets op te slaan.",
    "Nothing to undo yet": "Nog niets ongedaan te maken",
    "Nothing to redo": "Niets opnieuw te doen",
    "Undo: %s\n"
    "%s step(s) available  ·  Ctrl+Z":
        "Ongedaan maken: %s\n"
        "%s stap(pen) beschikbaar  ·  Ctrl+Z",
    "Redo: %s\n"
    "%s step(s) available  ·  Ctrl+Y":
        "Opnieuw: %s\n"
        "%s stap(pen) beschikbaar  ·  Ctrl+Y",
    "↶  Undo — %s": "↶  Ongedaan maken — %s",
    "↷  Redo — %s": "↷  Opnieuw — %s",
    "restored %s": "%s hersteld",
    "removed %s": "%s verwijderd",
    "replaced %s → %s": "%s vervangen → %s",
    "moved %s": "%s verplaatst",
    "playlist rename": "afspeellijst hernoemd",
    "deck layout change": "deckindeling gewijzigd",
    "view / settings change": "weergave / instellingen gewijzigd",
    "“%s” and “%s”": "„%s” en „%s”",
    "%s tracks (“%s”, “%s”, …)": "%s nummers („%s”, „%s”, …)",
    "No files added yet.": "Nog geen bestanden toegevoegd.",
    "No song selected": "Geen nummer geselecteerd",
    "No playing row found.": "Geen spelende rij gevonden.",
    "No dances for this class.": "Geen dansen voor deze klasse.",
    "No similar tracks found.": "Geen vergelijkbare nummers gevonden.",
    "No similar tracks found for that file.":
        "Geen vergelijkbare nummers gevonden voor dat bestand.",
    "No reference playlist yet.": "Nog geen referentie-afspeellijst.",
    "No auto-advance pause is running to extend.":
        "Er loopt geen auto-door-pauze die verlengd kan worden.",
    "This wall has no pads yet.": "Deze Cartwall heeft nog geen pads.",
    "Your wishlist is empty — add tracks to a wishlist first.":
        "Je wensenlijst is leeg — voeg eerst nummers toe aan een wensenlijst.",
    "Saved — it takes effect the next time you start the app.":
        "Opgeslagen — het werkt de volgende keer dat je de app start.",
    "Then restart the app — nothing else to configure.":
        "Start de app daarna opnieuw — verder hoef je niets in te stellen.",
    "ffmpeg not found": "ffmpeg niet gevonden",
    "(multimedia unavailable)": "(multimedia niet beschikbaar)",
    "Play a title first — then TSO sets its heat tempo.":
        "Speel eerst een titel af — dan zet TSO het tempo van de heat.",
    "This title has no detected tempo — can't equalize.":
        "Voor deze titel is geen tempo herkend — gelijktrekken niet mogelijk.",
    "The fader can't reach that tempo for this title.":
        "De fader haalt dat tempo voor deze titel niet.",
    "Preview player disabled — re-enable it in ⚙ Settings.":
        "Voorbeeldspeler uitgeschakeld — zet hem weer aan in ⚙ Instellingen.",
    "Pick a playlist again to choose a different track":
        "Kies opnieuw een afspeellijst om een ander nummer te nemen",
    "Pick “Replace…” again to choose a different track":
        "Kies opnieuw „Vervangen…” om een ander nummer te nemen",
    "%s: strategy set to %s — ↺ a song or dance to apply":
        "%s: strategie ingesteld op %s — ↺ op een nummer of dans past hem toe",
    "%s: %s · %s — ↺ a song or dance to apply":
        "%s: %s · %s — ↺ op een nummer of dans past hem toe",
    "↻ %s re-rolled — %s": "↻ %s opnieuw geloot — %s",
    "↻ %s re-rolled — %s · %s": "↻ %s opnieuw geloot — %s · %s",
    "Re-roll failed: %s": "Opnieuw loten mislukt: %s",
    "this comp": "deze wedstrijd",
    "all playlists": "alle afspeellijsten",
    "Listen to this track": "Naar dit nummer luisteren",
    "Play / stop this track": "Dit nummer afspelen / stoppen",
    "Play / stop this file": "Dit bestand afspelen / stoppen",
    "Play / stop the base track these results are based on":
        "Het basisnummer van deze resultaten afspelen / stoppen",
    "Listen to this pad while you set its level":
        "Naar deze pad luisteren terwijl je het niveau instelt",
    "Jump back to the start (0:00) of this track":
        "Terug naar het begin (0:00) van dit nummer",
    "Click to collapse / expand": "Klik om in / uit te klappen",
    "Click to focus · right-click or double-click to rename":
        "Klik om te activeren · rechtsklik of dubbelklik om te hernoemen",
    "Double-click to rename this page":
        "Dubbelklik om deze pagina te hernoemen",
    "Double-click to type a value": "Dubbelklik om een waarde in te typen",
    "Drag here to move": "Hier slepen om te verplaatsen",
    "Drag here to move the preview player":
        "Hier slepen om de voorbeeldspeler te verplaatsen",
    "Unfold this playlist": "Deze afspeellijst uitklappen",
    "Fold the library pane to its header":
        "Het bibliotheekpaneel tot de kopregel inklappen",
    "%s — folded.  Click to unfold.":
        "%s — ingeklapt.  Klik om uit te klappen.",
    "%s — folded.  Click to open.": "%s — ingeklapt.  Klik om te openen.",
    "Open the %s panel.": "Het paneel %s openen.",
    "Compact the %s panel to its header tab —\n"
    "click the tab (or this arrow) to open it again.":
        "Het paneel %s inklappen tot zijn koptab —\n"
        "klik op de tab (of deze pijl) om het weer te openen.",
    "Close the preview and stop playback  (Ctrl+X)":
        "Voorbeeld sluiten en afspelen stoppen  (Ctrl+X)",
    "Close the tournament day — clears all 📅 day decks":
        "De toernooidag sluiten — leegt alle 📅 dagdecks",
    "Back to this slot's default key":
        "Terug naar de standaardtoets van deze plek",
    "Export or import this wall": "Deze Cartwall exporteren of importeren",
    "Duck to 20 % / back to full": "Dempen naar 20 % / terug naar vol",
    "Reset the tempo to ±0 % (or double-click the fader)":
        "Tempo terugzetten op ±0 % (of dubbelklik op de fader)",
    "Volume adjustment of this track by Equalize volume (R128)":
        "Volumeaanpassing van dit nummer door Volume gelijktrekken (R128)",
    "When this file was created in the library":
        "Wanneer dit bestand in de bibliotheek is aangemaakt",
    "Replace via the similar-tracks picker":
        "Vervangen via de keuze van vergelijkbare nummers",
    "Put the shipped rule set back.":
        "Het meegeleverde reglement terugzetten.",
    "Put the whole transcript on the clipboard.":
        "Het hele gesprek naar het klembord kopiëren.",
    "Esc closes  ·  double-click leaves full screen":
        "Esc sluit  ·  dubbelklik verlaat volledig scherm",
    "Pick a length or type one: m:ss, seconds, or 'full'":
        "Kies een lengte of typ er een: m:ss, seconden of 'volledig'",
    "m:ss, seconds, or 'full' — Enter to keep, Esc to abandon":
        "m:ss, seconden of 'volledig' — Enter bewaart, Esc verwerpt",
    "full — to each title's own end":
        "volledig — tot het eigen einde van elke titel",
    "full": "volledig",
    "no marks — scrub to a crash and hit 🎯":
        "geen markeringen — spoel naar een klap en druk op 🎯",
    "“Proven” = songs in any of your playlists · “New” = in none.":
        "„Beproefd” = nummers uit een van je afspeellijsten · „Nieuw” = uit geen enkele.",
    "e.g. a song title, mood, or leave blank":
        "bijv. een titel, een sfeer, of leeg laten",
    "API base URL:": "API-basis-URL:",
    "API key  (free OpenRouter key from openrouter.ai/keys):":
        "API-sleutel  (gratis OpenRouter-sleutel op openrouter.ai/keys):",
    "Drag in playlists / files…":
        "Afspeellijsten / bestanden hierheen slepen…",
    "Drop .m3u playlists or audio files here, or click to browse":
        "Zet hier .m3u-afspeellijsten of audiobestanden neer, of klik om te bladeren",
    "Drop an audio file here, or click to browse":
        "Zet hier een audiobestand neer, of klik om te bladeren",
    "Drop saved .m3u playlists here, or click to browse":
        "Zet hier opgeslagen .m3u-afspeellijsten neer, of klik om te bladeren",
    "Drop playlists above to check them.":
        "Zet afspeellijsten hierboven neer om ze te controleren.",
    "Drop some files above to check them.":
        "Zet bestanden hierboven neer om ze te controleren.",
    "Saved playlists dragged in (.m3u)…":
        "Binnengesleepte opgeslagen afspeellijsten (.m3u)…",
    "Choose an .m3u file…": "Een .m3u-bestand kiezen…",
    "Browse…": "Bladeren…",
    "Add…": "Toevoegen…",
    "Build / refresh…": "Maken / vernieuwen…",
    "  Pick a colour…": "  Kies een kleur…",
    "…or pick one from the list": "…of kies er een uit de lijst",
    "pick a key…": "kies een toets…",
    "↑ resolved above": "↑ hierboven opgelost",
    "⚙  Settings": "⚙  Instellingen",
    "⚗ Analysis": "⚗ Analyse",
    "🎨 Look": "🎨 Uiterlijk",
    "🎨  Theme": "🎨  Thema",
    "⚙ General": "⚙ Algemeen",
    "📁 Paths": "📁 Paden",
    "🔊 Sound && player": "🔊 Geluid && speler",
    "📁  New folder…": "📁  Nieuwe map…",
    "⌨  Shortcuts…": "⌨  Sneltoetsen…",
    "❔  Shortcuts": "❔  Sneltoetsen",
    "▶  Playing": "▶  Afspelen",
    "▶  Playing mode": "▶  Afspeelmodus",
    "▶  Load onto the focused deck": "▶  Op het actieve deck laden",
    "▴  Fold decks": "▴  Decks",
    "⊟  Collapse all": "⊟  Inklappen",
    "⏹  Stop all": "⏹  Alles stoppen",
    "⏹  Stop the music": "⏹  Muziek stoppen",
    "⏭  Skip to the next title": "⏭  Naar de volgende titel",
    "⏸  Auto-advance…": "⏸  Automatisch door…",
    "⏱  Wall fade-out…": "⏱  Uitfaden van de Cartwall…",
    "⏱ calculating…": "⏱ berekenen…",
    "⏳  Comparing…": "⏳  Vergelijken…",
    "⚡  Generate Playlist": "⚡  Afspeellijst maken",
    "✅  Apply": "✅  Toepassen",
    "✅  Keep": "✅  Behouden",
    "✅  Keep all": "✅  Alles behouden",
    "✅  Use this track as replacement":
        "✅  Dit nummer als vervanging gebruiken",
    "✅  No duplicate songs across your open playlist(s).":
        "✅  Geen dubbele nummers in je open afspeellijst(en).",
    "✎  Rename…": "✎  Hernoemen…",
    "✏  Rename": "✏  Hernoemen",
    "📅  New tournament day…": "📅  Nieuwe toernooidag…",
    "✏️  Rename tab…": "✏️  Tab hernoemen…",
    "✏️  Edit highlights": "✏️  Hoogtepunten bewerken",
    "✏  Editing — pads do not play": "✏  Bewerken — pads spelen niet",
    "✕  Close tournament day": "✕  Toernooidag sluiten",
    "✦  Only never played": "✦  Alleen nooit gespeelde",
    "✦ Never played": "✦ Nooit gespeeld",
    "➕  Add": "➕  Toevoegen",
    "➕  Add a heat to this round": "➕  Een heat aan deze ronde toevoegen",
    "➕  Add files…": "➕  Bestanden toevoegen…",
    "➕  Both": "➕  Beide",
    "➕ Add competition": "➕ Wedstrijd toevoegen",
    "➖  Remove selected": "➖  Selectie verwijderen",
    "＋  Add playlists…": "＋  Afspeellijsten toevoegen…",
    "⬆  Move backup up into this empty slot":
        "⬆  Reserve naar deze lege plek omhoog halen",
    "⇅  Swap these two titles\tAlt+S":
        "⇅  Deze twee titels verwisselen\tAlt+S",
    "♊  Remove duplicate titles in this list":
        "♊  Dubbele titels in deze lijst verwijderen",
    "⭐  Favorites": "⭐  Favorieten",
    "⭐  Favorites library": "⭐  Favorietenbibliotheek",
    "🎯  Favorites library": "🎯  Favorietenbibliotheek",
    "⭐  Open wishlists": "⭐  Open wensenlijsten",
    "⭐  Only tracks in my wishlist(s)":
        "⭐  Alleen nummers uit mijn wensenlijst(en)",
    "⭐  Find similar (in my wishlist only)":
        "⭐  Vergelijkbare zoeken (alleen in mijn wensenlijst)",
    "⭐  Find similar in wishlist (run Audio Analysis first)":
        "⭐  Vergelijkbare in de wensenlijst (eerst audioanalyse uitvoeren)",
    "⭐  Find similar in wishlist (wishlist is empty)":
        "⭐  Vergelijkbare in de wensenlijst (wensenlijst is leeg)",
    "🌱  Find similar (never played)":
        "🌱  Vergelijkbare zoeken (nooit gespeeld)",
    "🌱  Find similar, never played (run Audio Analysis first)":
        "🌱  Vergelijkbare, nooit gespeeld (eerst audioanalyse uitvoeren)",
    "🌱  Freshness: all tracks": "🌱  Versheid: alle nummers",
    "🔎  Find similar tracks": "🔎  Vergelijkbare nummers zoeken",
    "🔎  Find similar (run Audio Analysis first)":
        "🔎  Vergelijkbare zoeken (eerst audioanalyse uitvoeren)",
    "🔍  Compare": "🔍  Vergelijken",
    "🔍  Filter title / artist / comment tag…":
        "🔍  Titel / artiest / commentaar filteren…",
    "🔍  Find a title in this list…\tCtrl+F":
        "🔍  Een titel in deze lijst zoeken…\tCtrl+F",
    "🆕 Last 30 days": "🆕 Laatste 30 dagen",
    "🆕 Last 90 days": "🆕 Laatste 90 dagen",
    "🆕 Last 12 months": "🆕 Laatste 12 maanden",
    "🆕 Last 18 months": "🆕 Laatste 18 maanden",
    "🆕 Unplanned": "🆕 Ongepland",
    "📅  Only not since 1 y": "📅  Alleen al 1 jaar niet gespeeld",
    "📅 Not since 1 y": "📅 Al 1 jaar niet",
    "📅  Day plan": "📅  Dagplan",
    "📅 Plan tournament day": "📅 Toernooidag plannen",
    "📅 Tournament day": "📅 Toernooidag",
    "📅 Tournament day closed.": "📅 Toernooidag gesloten.",
    "📜  Find planned before": "📜  Eerder geplande zoeken",
    "📜  Find planned before (load library first)":
        "📜  Eerder geplande zoeken (eerst bibliotheek laden)",
    "📜  Re-learn playlist popularity…":
        "📜  Populariteit van afspeellijsten opnieuw leren…",
    "📚  Library": "📚  Bibliotheek",
    "📚  Show never-played tracks": "📚  Nooit gespeelde nummers tonen",
    "📋  Copy": "📋  Kopiëren",
    "📋  Copy file path": "📋  Bestandspad kopiëren",
    "📋  Copy file path (unavailable)":
        "📋  Bestandspad kopiëren (niet beschikbaar)",
    "📋  Copy file path (not in your library)":
        "📋  Bestandspad kopiëren (niet in je bibliotheek)",
    "📋  Based on my playlist history (tracks I play together)":
        "📋  Op basis van mijn afspeellijstgeschiedenis (nummers die ik samen draai)",
    "📝  Copy details": "📝  Details kopiëren",
    "📝  Wish list — the titles below, in that order":
        "📝  Wensenlijst — de titels hieronder, in die volgorde",
    "📂  Open folder": "📂  Map openen",
    "📂  Show in Explorer": "📂  In Verkenner tonen",
    "📂  Show in Explorer (unavailable)":
        "📂  In Verkenner tonen (niet beschikbaar)",
    "📂  Import M3U…": "📂  M3U importeren…",
    "📂  Add a folder of playlists…":
        "📂  Een map met afspeellijsten toevoegen…",
    "📂  Import — track paths": "📂  Import — nummerpaden",
    "📂  Drag files in": "📂  Bestanden hierheen slepen",
    "📂  Assign files…": "📂  Bestanden toewijzen…",
    "📂  An .m3u playlist file": "📂  Een .m3u-afspeellijstbestand",
    "📂  Drop saved .m3u playlists here, or click to browse":
        "📂  Zet hier opgeslagen .m3u-afspeellijsten neer, of klik om te bladeren",
    "📄  All pads on one page": "📄  Alle pads op één pagina",
    "📊  Analyze loudness (R128)…": "📊  Luidheid analyseren (R128)…",
    "📊  Library gaps…": "📊  Gaten in de bibliotheek…",
    "📊 Library gaps": "📊 Gaten in de bibliotheek",
    "📤  Export wall…": "📤  Cartwall exporteren…",
    "📥  Import wall…": "📥  Cartwall importeren…",
    "📌  Save state": "📌  Status",
    "📌 Cartwall docked": "📌 Cartwall vastgezet",
    "💾  Save M3U": "💾  M3U opslaan",
    "💾  Save as M3U…": "💾  Opslaan als M3U…",
    "💾  Save all": "💾  Opslaan",
    "💾  Save all competition M3Us": "💾  Alle wedstrijd-M3U's opslaan",
    "💾  Save all playlists as M3U": "💾  Alle afspeellijsten als M3U opslaan",
    "🏆  Save all and add to Tournaments":
        "🏆  Alles opslaan en aan Toernooien toevoegen",
    "🏆  Save and add to Tournaments…":
        "🏆  Opslaan en aan Toernooien toevoegen…",
    "🏆 Saved and added %d playlist to Tournaments":
        "🏆 Opgeslagen en %d afspeellijst aan Toernooien toegevoegd",
    "🏆 Saved and added %d playlists to Tournaments":
        "🏆 Opgeslagen en %d afspeellijsten aan Toernooien toegevoegd",
    "🏆 Saved — already in Tournaments":
        "🏆 Opgeslagen — staat al in Toernooien",
    "🔁  Check duplicates": "🔁  Dubbelen controleren",
    "🔁  Endless repeat": "🔁  Eindeloos herhalen",
    "🔁  Replace…": "🔁  Vervangen…",
    "🔁  Reset all replacement marks":
        "🔁  Alle vervangingsmarkeringen resetten",
    "🔇  Probe silences…": "🔇  Stiltes onderzoeken…",
    "🔇 No audio backend — the cartwall cannot play here.":
        "🔇 Geen audio-backend — de Cartwall kan hier niet afspelen.",
    "🔈  Pull the music down while this pad plays":
        "🔈  De muziek dempen zolang deze pad speelt",
    "🔈 No announcement recordings found for this voice.":
        "🔈 Geen aankondigingsopnames gevonden voor deze stem.",
    "🖌  Wall colour": "🖌  Kleur van de Cartwall",
    "🖥  Presenter": "🖥  Presentatie",
    "🖥  Presenter — DancePlaylist": "🖥  Presentatie — DancePlaylist",
    "🕒 Timetable — presenter screen": "🕒 Tijdschema — presentatiescherm",
    "✖  Remove": "✖  Verwijderen",
    "🖨  Print": "🖨  Afdrukken",
    "🖨  Export PDF": "🖨  PDF exporteren",
    "🗑  Clear": "🗑  Leegmaken",
    "🗑  Remove": "🗑  Verwijderen",
    "🗑  Remove this title (keep slot)":
        "🗑  Deze titel verwijderen (plek blijft)",
    "🗑  Remove %d selected titles (keep slots)":
        "🗑  %d geselecteerde titels verwijderen (plekken blijven)",
    "🗑  Remove this title": "🗑  Deze titel verwijderen",
    "🗑  Remove %d selected titles": "🗑  %d geselecteerde titels verwijderen",
    "🗑  Remove from tree": "🗑  Uit de boom verwijderen",
    "🗑  Remove from wishlist": "🗑  Uit de wensenlijst verwijderen",
    "🗑  Remove this backup\tCtrl+Del": "🗑  Deze reserve verwijderen\tCtrl+Del",
    "🗑  Remove this empty slot": "🗑  Deze lege plek verwijderen",
    "🗑  Remove this heat (all dances)\tCtrl+Del":
        "🗑  Deze heat verwijderen (alle dansen)\tCtrl+Del",
    "🗑  Remove this round (all heats)":
        "🗑  Deze ronde verwijderen (alle heats)",
    "🚫  No groups": "🚫  Geen groepen",
    "🔢  Numbers": "🔢  Nummers",
    "🧹  Clear all": "🧹  Leegmaken",
    "🧹  Clear all playlists": "🧹  Alle afspeellijsten leegmaken",
    "🧹  Empty this playlist": "🧹  Deze afspeellijst leegmaken",
    "🧹  Clean up database…": "🧹  Database opruimen…",
    "🧹  Export unused": "🧹  Ongebruikte exporteren",
    "🧹  Reference base": "🧹  Referentiebasis",
    "🧹  Remove": "🧹  Verwijderen",
    "🧹  Remove tracks already in a playlist":
        "🧹  Nummers verwijderen die al in een afspeellijst staan",
    "🧹 Cleared all playlists.": "🧹 Alle afspeellijsten geleegd.",
    "🧹 Tournament-day playlists cleared.":
        "🧹 Afspeellijsten van de toernooidag geleegd.",
    "🧳  USB export": "🧳  USB-export",
    "🧳 USB export": "🧳 USB-export",
    "🧳 USB export aborted — incomplete bundle removed.":
        "🧳 USB-export afgebroken — onvolledig pakket verwijderd.",
    "🧭  Fix paths": "🧭  Paden herstellen",
    "🧭  Fix (overwrite)": "🧭  Herstellen (overschrijven)",
    "🧭  Fix (swap in playlists)": "🧭  Herstellen (in afspeellijsten wisselen)",
    "🧱  Build ALL caches…": "🧱  ALLE caches opbouwen…",
    "🧠  Rebuild index…": "🧠  Index opnieuw opbouwen…",
    "🤖  AI Playlist…": "🤖  AI-afspeellijst…",
    "🤖  AI playlist": "🤖  AI-afspeellijst",
    "🤖  Build": "🤖  Maken",
    "🤖  Get Suggestions": "🤖  Suggesties ophalen",
    "🤖  Conversation with the model": "🤖  Gesprek met het model",
    "🤸  Practice / party playlist": "🤸  Oefen- / feestafspeellijst",
    "🎉  Party set": "🎉  Feestset",
    "🎉  Party playlist (alternating 3-dance rounds, all dances)":
        "🎉  Feestafspeellijst (afwisselende rondes van 3 dansen, alle dansen)",
    "🏆  Tournaments": "🏆  Toernooien",
    "🏆  Tournament set": "🏆  Toernooiset",
    "🏆 Tournament only": "🏆 Alleen toernooi",
    "🏷  Re-read MP3 tags": "🏷  MP3-tags opnieuw inlezen",
    "🏷  Re-read MP3 tags (unavailable)":
        "🏷  MP3-tags opnieuw inlezen (niet beschikbaar)",
    "🐂  Analyze PD highlights…": "🐂  PD-hoogtepunten analyseren…",
    "🎯  Mark highlight now": "🎯  Hoogtepunt nu markeren",
    "🎯 Highlights cleared — 🐂 auto-detection will run again.":
        "🎯 Hoogtepunten gewist — 🐂 de automatische herkenning draait opnieuw.",
    "🎯 Last mark deleted — 🐂 auto-detection takes over again.":
        "🎯 Laatste markering gewist — 🐂 de automatische herkenning neemt het weer over.",
    "🎯 Play a Paso Doble first, then click when a highlight hits.":
        "🎯 Speel eerst een Paso Doble af en klik als er een hoogtepunt komt.",
    "🎵  Check music": "🎵  Muziek controleren",
    "🎵  Check music speed": "🎵  Muzieksnelheid controleren",
    "🎵  Check music speed (unavailable)":
        "🎵  Muzieksnelheid controleren (niet beschikbaar)",
    "🎵  Music check": "🎵  Muziekcontrole",
    "🎵 Checks": "🎵 Controles",
    "🎵 Music speed": "🎵 Muzieksnelheid",
    "🎵 Music check aborted.": "🎵 Muziekcontrole afgebroken.",
    "🎵  One flat list of": "🎵  Eén platte lijst van",
    "🎵  Show its tracks": "🎵  De nummers tonen",
    "🎵 0 titles": "🎵 0 titels",
    "🎵 %d title": "🎵 %d titel",
    "🎵 %d titles": "🎵 %d titels",
    "  ·  ✦ %d new": "  ·  ✦ %d nieuw",
    "🎼  Build chroma cover / remix index…":
        "🎼  Chroma-index voor covers / remixes opbouwen…",
    "🎚️  Open playlists": "🎚️  Open afspeellijsten",
    "🎚️  Timbre + Rhythm (librosa)": "🎚️  Timbre + ritme (librosa)",
    "🎛 Play sets": "🎛 Speelsets",
    "🎛 No free pad voice — every voice holds a looping pad.":
        "🎛 Geen vrije padstem — elke stem houdt een lopende pad vast.",
    "🎤 Vocal": "🎤 Zang",
    "🎙️  Only instrumental tracks (no vocals)":
        "🎙️  Alleen instrumentale nummers (zonder zang)",
    "🎧  Open in external player": "🎧  In externe speler openen",
    "🌐  Whole repository": "🌐  Hele repository",
    "🌐  Build librosa index (needs librosa)":
        "🌐  Librosa-index opbouwen (vereist librosa)",
    "🌐  Build / refresh librosa audio index (whole repo)…":
        "🌐  Librosa-audio-index opbouwen / vernieuwen (hele repo)…",
    "🔬  Timbre Gaussian / KL (Mandel-Ellis)":
        "🔬  Timbre Gauss / KL (Mandel-Ellis)",
    "⚠  That spot is no longer in an open deck.":
        "⚠  Die plek staat niet meer in een open deck.",
    "↺  Default blue": "↺  Standaardblauw",
    "↺  Default rules": "↺  Standaardregels",
    "1 playlist": "1 afspeellijst",
    "%d playlist": "%d afspeellijst",
    "%d playlists": "%d afspeellijsten",
    "No playlist": "Geen afspeellijst",
    "No wishlist": "Geen wensenlijst",
    "1 wishlist": "1 wensenlijst",
    "2 wishlists": "2 wensenlijsten",
    "3 wishlists": "3 wensenlijsten",
    "4 wishlists": "4 wensenlijsten",
    "4 wishlists (2×2)": "4 wensenlijsten (2×2)",
    "Build a practice playlist into the focused deck:\n"
    "• Practice for a tournament class — the class's dances round-robin\n"
    "  (e.g. Latin S: SA, CC, RB, PD, JI …), TSO-conform, popular + fresh.\n"
    "• Party — alternating 3-dance rounds across all dances.\n"
    "Draw from your ⭐ Favorites (unused tracks), the open wishlists\n"
    "or a chosen .m3u file.":
        "Een oefenafspeellijst in het actieve deck bouwen:\n"
        "• Oefenen voor een toernooiklasse — de dansen van de klasse om de beurt\n"
        "  (bijv. Latin S: SA, CC, RB, PD, JI …), TSO-conform, populair + nieuw.\n"
        "• Feest — afwisselende rondes van 3 dansen over alle dansen.\n"
        "Put uit je ⭐ Favorieten (ongebruikte nummers), de open wensenlijsten\n"
        "of een gekozen .m3u-bestand.",
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
        "Elk nummer in de decks controleren op toernooiproblemen:\n"
        "• Tempo: label in de bestandsnaam (T51 = maten per minuut, via de\n"
        "  maatsoort van de dans) tegen het door librosa gemeten tempo — vindt verkeerd gelabelde bestanden.\n"
        "• TSO-bereik: ligt het tempo binnen het officiële maatbereik van de dans.\n"
        "• Lengte: waarschuwt als een nummer korter is dan de speeltijd van 1:30–1:45\n"
        "  of langer dan 4:00.\n"
        "• Rondeopbouw: ongelijk aantal dansen in een ronde en afwijkingen in\n"
        "  het aantal heats in finale/halve finale.\n"
        "Verdachte nummers kun je vanuit het rapport beluisteren, verwijderen of vervangen.\n"
        "Tempo- en bereikcontroles hebben 🔬 audioanalyse nodig voor het gemeten tempo.",
    "Collapse every round and dance header of every playlist —\n"
    "click again to open them all.":
        "Alle ronde- en danskoppen van alle afspeellijsten inklappen —\n"
        "klik nogmaals om ze allemaal te openen.",
    "Cycle the playlist headers: full → 🗜 Compact (per-dance header rows\n"
    "hidden, each round lists its songs directly) → 🚫 No groups (round and\n"
    "─── section headers dropped too, so the list — a Practice / party\n"
    "list above all — is one flat run of songs) → 🔢 Numbers (no groups,\n"
    "plus an Nb. column up front counting the titles).":
        "De koppen van de afspeellijst doorlopen: volledig → 🗜 Compact (kopregels per\n"
        "dans verborgen, elke ronde toont zijn nummers direct) → 🚫 Geen groepen (ook ronde-\n"
        "en ───-sectiekoppen vallen weg, zodat de lijst — vooral een oefen- / feest-\n"
        "lijst — één doorlopende reeks nummers is) → 🔢 Nummers (geen groepen,\n"
        "plus vooraan een Nr.-kolom die de titels telt).",
    "Cycle the wishlist area: off → 1 → 2 → 3 → 4 → 4 stacked 2×2.\n"
    "Right click walks it backwards.\n"
    "Off hides it entirely, even with multiple decks.\n"
    "Double-click any deck/wishlist title to rename it.":
        "Het wensenlijstgebied doorlopen: uit → 1 → 2 → 3 → 4 → 4 gestapeld 2×2.\n"
        "Rechtsklik loopt achteruit.\n"
        "Uit verbergt het helemaal, ook bij meerdere decks.\n"
        "Dubbelklik op een deck- of wensenlijsttitel om hem te hernoemen.",
    "Empty every playlist deck (wishlists are kept).\n"
    "Tip: Del on a deck's title clears just that one playlist;\n"
    "Del on a wishlist's title clears that wishlist.":
        "Alle afspeellijstdecks leegmaken (wensenlijsten blijven).\n"
        "Tip: Del op de titel van een deck leegt alleen die afspeellijst;\n"
        "Del op de titel van een wensenlijst leegt die wensenlijst.",
    "Export every non-empty playlist deck to its own .m3u in the\n"
    "playlist folder at once (wishlists are not included).\n"
    "Each file is named after its deck title.":
        "Elk niet-leeg afspeellijstdeck in één keer naar een eigen .m3u in de\n"
        "afspeellijstmap exporteren (wensenlijsten niet inbegrepen).\n"
        "Elk bestand krijgt de naam van zijn decktitel.",
    "Export playlists as a self-contained venue bundle — asks first\n"
    "whether to take all open decks, only the 📅 tournament day, or\n"
    "saved .m3u files dragged in (wishlists are never bundled).\n"
    "One sub-folder per playlist holding its tracks copied in numbered\n"
    "play order (0_0_1 - Title WW29.mp3) plus the playlist's .m3u — each\n"
    "folder plays in order even without the M3U, from any drive,\n"
    "laptop or UltraMixer at the venue (no path fixing needed there).":
        "Afspeellijsten exporteren als zelfstandig zaalpakket — vraagt eerst\n"
        "of alle open decks, alleen de 📅 toernooidag of binnengesleepte\n"
        "opgeslagen .m3u-bestanden mee moeten (wensenlijsten gaan nooit mee).\n"
        "Eén submap per afspeellijst met haar nummers gekopieerd in genummerde\n"
        "speelvolgorde (0_0_1 - Title WW29.mp3) plus de .m3u van de afspeellijst — elke\n"
        "map speelt in volgorde, ook zonder de M3U, vanaf elke schijf,\n"
        "laptop of UltraMixer in de zaal (daar hoeven geen paden te worden hersteld).",
    "Export the focused playlist as a printable PDF\n"
    "(rounds, heats, titles, lengths) into the playlist folder.":
        "De actieve afspeellijst als afdrukbare PDF\n"
        "(rondes, heats, titels, lengtes) naar de afspeellijstmap exporteren.",
    "Fold every visible playlist deck and wishlist to its header tab —\n"
    "click again to open them all.\n"
    "Click a single tab (or its arrow) to open just that one.":
        "Elk zichtbaar afspeellijstdeck en elke wensenlijst tot zijn koptab inklappen —\n"
        "klik nogmaals om ze allemaal te openen.\n"
        "Klik op één tab (of zijn pijl) om alleen die te openen.",
    "Plan a whole tournament day: define the day's competitions\n"
    "(style, age, class, round pattern) and generate them all at once\n"
    "into the 📅 Tournament-day tab — eight dedicated day decks in two\n"
    "sub-tabs, separate from the normal playlists; more than 8\n"
    "competitions stack several per deck. All share one no-repeat\n"
    "pool, so a song never appears in two of the day's competitions\n"
    "(Paso excepted). Exports write one M3U per competition.":
        "Een hele toernooidag plannen: de wedstrijden van de dag vastleggen\n"
        "(stijl, leeftijd, klasse, rondeschema) en ze allemaal tegelijk\n"
        "in de tab 📅 Toernooidag maken — acht eigen dagdecks in twee\n"
        "subtabs, los van de gewone afspeellijsten; bij meer dan 8\n"
        "wedstrijden komen er meerdere per deck. Ze delen allemaal één pool\n"
        "zonder herhaling, zodat een nummer nooit in twee wedstrijden van de dag\n"
        "voorkomt (Paso uitgezonderd). De export schrijft één M3U per wedstrijd.",
    "Relocate broken track references in the visible deck(s) to matching\n"
    "real files in the library — fixes moved folders / changed drive\n"
    "letters after an import. Anything still unresolved is reported.":
        "Kapotte nummerverwijzingen in de zichtbare deck(s) omleiden naar passende\n"
        "echte bestanden in de bibliotheek — herstelt verplaatste mappen / gewijzigde\n"
        "stationsletters na een import. Wat daarna nog open is, wordt gemeld.",
    "Save the whole working session right now — every deck, wishlist and the\n"
    "window layout — so it comes back exactly on the next launch.  (Ctrl+Shift+S)\n"
    "(This also happens automatically on every edit and on close.)":
        "De hele werksessie nu opslaan — elk deck, elke wensenlijst en de\n"
        "vensterindeling — zodat hij bij de volgende start precies zo terugkomt.  (Ctrl+Shift+S)\n"
        "(Dit gebeurt ook automatisch bij elke wijziging en bij het sluiten.)",
    "Scan the visible playlist deck(s) for songs that appear more than once,\n"
    "then resolve each: keep the ones you want and replace the rest with a\n"
    "similar track (chosen from the Similar-Tracks picker).":
        "De zichtbare afspeellijstdeck(s) doorzoeken op nummers die meer dan eens voorkomen,\n"
        "en elk geval oplossen: behoud wat je wilt en vervang de rest door een\n"
        "vergelijkbaar nummer (gekozen in de keuze van vergelijkbare nummers).",
    "Show / hide the library browser under the wishlists:\n"
    "filter the whole competition library and drag tracks\n"
    "straight into a deck or wishlist.":
        "De bibliotheekbrowser onder de wensenlijsten tonen / verbergen:\n"
        "filter de hele wedstrijdbibliotheek en sleep nummers\n"
        "rechtstreeks naar een deck of wensenlijst.",
    "Show / hide the 🎛 sample-pad wall:\n"
    "drop Tusch, applause or a background bed onto a pad and tap it —\n"
    "it plays on top of the running music instead of replacing it.\n"
    "Drag its title bar to dock it left / right / below, or float it.":
        "De 🎛 samplepad-wand tonen / verbergen:\n"
        "zet een Tusch, applaus of een achtergrondtapijt op een pad en tik erop —\n"
        "het speelt boven op de lopende muziek in plaats van die te vervangen.\n"
        "Sleep de titelbalk om hem links / rechts / onder vast te zetten, of laat hem zweven.",
    "Space: play / stop the selected song\n"
    "Ctrl + ← / → : seek 30 s back / forward\n"
    "Click a round / dance header to collapse or expand it":
        "Spatie: het geselecteerde nummer afspelen / stoppen\n"
        "Ctrl + ← / → : 30 s terug / vooruit\n"
        "Klik op een ronde- / danskop om hem in of uit te klappen",
    "💥  The app did not shut down cleanly last time.\n"
    "\n"
    "The crash log of that session is under 'Show Details…' (it is overwritten on every start).":
        "💥  De app is de vorige keer niet netjes afgesloten.\n"
        "\n"
        "Het crashlog van die sessie staat onder 'Details weergeven…' (het wordt bij elke start overschreven).",
    "AI Error": "AI-fout",
    "API key needed": "API-sleutel nodig",
    "CLAUDE_CONFIG_DIR — which claude login the CLI uses.\n"
    "Empty leaves it to the CLI (~/.claude).":
        "CLAUDE_CONFIG_DIR — welke claude-aanmelding de CLI gebruikt.\n"
        "Leeg laat het aan de CLI over (~/.claude).",
    "Enter a free OpenRouter API key (openrouter.ai/keys).":
        "Voer een gratis OpenRouter-API-sleutel in (openrouter.ai/keys).",
    "Free text. The tempo table, the track catalog and the answer\n"
    "format are added automatically — describe only what makes a\n"
    "playlist good in your eyes.":
        "Vrije tekst. De tempotabel, de nummercatalogus en het antwoord-\n"
        "formaat worden automatisch toegevoegd — beschrijf alleen wat in jouw ogen\n"
        "een goede afspeellijst maakt.",
    "How much text this run moves.\n"
    "\n"
    "Sent is everything the model was given (the rules, the library summary, the catalog rows), back is what it answered. The biggest turn is the one that has to fit the model's context window: one prompt plus its reply.\n"
    "\n"
    "Token counts are estimated at ~4 characters each — no backend here reports its real usage.":
        "Hoeveel tekst deze run verplaatst.\n"
        "\n"
        "Verzonden is alles wat het model kreeg (de regels, de samenvatting van de bibliotheek, de catalogusregels), terug is wat het antwoordde. De grootste beurt is degene die in het contextvenster van het model moet passen: één prompt plus het antwoord.\n"
        "\n"
        "Tokens worden geschat op ~4 tekens per stuk — geen enkele backend hier meldt zijn echte verbruik.",
    "Name the tracks yourself. The model does the looking up: it finds\n"
    "the library title behind every shortened or mistyped wish.":
        "Noem de nummers zelf. Het opzoeken doet het model: het vindt\n"
        "de bibliotheektitel achter elke afgekorte of verkeerd getypte wens.",
    "Style, age, start class, dances and the round pattern come from\n"
    "the panel on the left. The model only picks and orders the music.":
        "Stijl, leeftijd, klasse, dansen en het rondeschema komen uit\n"
        "het paneel links. Het model kiest en ordent alleen de muziek.",
    "Write the wishes however you like — one per line, a sentence, or a whole sheet pasted in with a column per dance:\n"
    "\n"
    "lw            t               ww        qs\n"
    "White wings   a new life      Willow    quit playing games !!\n"
    "melancolia !  Dance of love   Kiss me   youre so fine\n"
    "\n"
    "Short names and typos are fine. A two-letter code beside a title names its dance, ! or !! marks the ones you really want, and anything else you write here is read as an instruction.":
        "Schrijf de wensen zoals je wilt — één per regel, een zin, of een heel blad geplakt met een kolom per dans:\n"
        "\n"
        "lw            t               ww        qs\n"
        "White wings   a new life      Willow    quit playing games !!\n"
        "melancolia !  Dance of love   Kiss me   youre so fine\n"
        "\n"
        "Korte namen en typfouten zijn geen probleem. Een code van twee letters naast een titel noemt zijn dans, ! of !! markeert de nummers die je echt wilt, en al het andere dat je hier schrijft wordt als instructie gelezen.",
    "e.g. 'club evening, keep it modern', 'no covers in the final',\n"
    "'the wishes are for a show — put the two marked ones last'":
        "bijv. 'clubavond, houd het modern', 'geen covers in de finale',\n"
        "'de wensen zijn voor een show — zet de twee gemarkeerde als laatste'",
    "🏆  Competition playlist — rounds and heats from the left panel":
        "🏆  Wedstrijdafspeellijst — rondes en heats uit het linkerpaneel",
    "Drag .m3u playlists or audio files here; drag a title out (e.g. to the reference field) to remove it":
        "Sleep .m3u-afspeellijsten of audiobestanden hierheen; sleep een titel eruit (bijv. naar het referentieveld) om hem te verwijderen",
    "Open file": "Bestand openen",
    "Open folder": "Map openen",
    "Show in Explorer": "In Verkenner tonen",
    "📂  Drop .m3u playlists (or audio files) here, or click to browse":
        "📂  Zet hier .m3u-afspeellijsten (of audiobestanden) neer, of klik om te bladeren",
    "Could not parse any competition lines from the pasted text.\n"
    "Each line needs a class label, a style (STD/LAT) and the\n"
    "heat counts, e.g.  'U21 STD (50) 4 - 4 - 3 - 2 - 1'.":
        "Uit de geplakte tekst kon geen enkele wedstrijdregel worden gelezen.\n"
        "Elke regel heeft een klasselabel, een stijl (STD/LAT) en het\n"
        "aantal heats nodig, bijv.  'U21 STD (50) 4 - 4 - 3 - 2 - 1'.",
    "Let a model build the playlist instead of the scoring algorithm.\n"
    "You give it the rules (a default set is filled in), it picks and\n"
    "orders the music — either into the rounds/heats configured above\n"
    "or as one flat list.\n"
    "Runs on your Claude subscription via the claude CLI, with\n"
    "OpenRouter as fallback.":
        "Laat een model de afspeellijst bouwen in plaats van het scoringsalgoritme.\n"
        "Jij geeft de regels (een standaardset is ingevuld), het kiest en\n"
        "ordent de muziek — in de hierboven ingestelde rondes/heats\n"
        "of als één platte lijst.\n"
        "Draait op je Claude-abonnement via de claude-CLI, met\n"
        "OpenRouter als terugvaloptie.",
    "Runs through the claude CLI on your Claude subscription — no API key. Falls back to OpenRouter if that fails.":
        "Draait via de claude-CLI op je Claude-abonnement — geen API-sleutel. Valt terug op OpenRouter als dat mislukt.",
    "⚠ claude CLI not found — OpenRouter will be used. Set the CLAUDE_BIN environment variable to use your subscription.":
        "⚠ claude-CLI niet gevonden — OpenRouter wordt gebruikt. Stel de omgevingsvariabele CLAUDE_BIN in om je abonnement te gebruiken.",
    "Load an existing .m3u into the focused deck or wishlist.\n"
    "Decks detect rounds, dances and heats automatically — a final\n"
    "with extra backup variants (e.g. two Sambas) is handled too.\n"
    "A focused wishlist appends the tracks flat.":
        "Een bestaande .m3u in het actieve deck of de actieve wensenlijst laden.\n"
        "Decks herkennen rondes, dansen en heats automatisch — ook een finale\n"
        "met extra reservevarianten (bijv. twee Samba's).\n"
        "Een actieve wensenlijst voegt de nummers plat toe.",
    "No competitions parsed": "Geen wedstrijden herkend",
    "On: changing a round's strategy re-rolls that whole round.\n"
    "Off: keep the current grid and change only the songs you want\n"
    "via the ↺ buttons (they use the newly selected strategy).":
        "Aan: de strategie van een ronde wijzigen loot de hele ronde opnieuw.\n"
        "Uit: het huidige raster blijft en je wisselt alleen de nummers die je wilt\n"
        "via de ↺-knoppen (die gebruiken de nieuw gekozen strategie).",
    "Open the last conversation with the model again.\n"
    "It is kept until the next AI run starts.":
        "Het laatste gesprek met het model opnieuw openen.\n"
        "Het blijft bewaard tot de volgende AI-run begint.",
    "When enabled, songs within a round are scored for\n"
    "timbral similarity to the round's first song.\n"
    "Disable for more varied song choices.":
        "Indien aan, worden de nummers binnen een ronde gescoord op\n"
        "timbre-overeenkomst met het eerste nummer van de ronde.\n"
        "Zet uit voor een gevarieerdere keuze.",
    "Which titles ⚡ Generate may pick from.\n"
    "Favorites library — everything scanned from your library folder.\n"
    "Open wishlists — only what you parked in the ⭐ wishlists.\n"
    "An .m3u file — only the tracks in that one playlist.\n"
    "With the last two, a dance the pool cannot cover stays blank.":
        "Uit welke titels ⚡ Maken mag kiezen.\n"
        "Favorietenbibliotheek — alles wat uit je bibliotheekmap is ingelezen.\n"
        "Open wensenlijsten — alleen wat je in de ⭐ wensenlijsten hebt gezet.\n"
        "Een .m3u-bestand — alleen de nummers in die ene afspeellijst.\n"
        "Bij de laatste twee blijft een dans die de pool niet kan dekken leeg.",
    "“Proven” = songs you played in THIS competition's past lists · “New” = never played.  🎯 keeps a round to this competition; untick it to draw that round from ALL your playlists.":
        "„Beproefd” = nummers die je in eerdere lijsten van DEZE wedstrijd draaide · „Nieuw” = nooit gespeeld.  🎯 houdt een ronde bij deze wedstrijd; vink het uit om die ronde uit AL je afspeellijsten te halen.",
    "🎯 ticked: draw this round's songs from THIS competition's past lists only.\n"
    "Unticked: draw from ALL your playlists.":
        "🎯 aangevinkt: de nummers van deze ronde alleen uit eerdere lijsten van DEZE wedstrijd halen.\n"
        "Uitgevinkt: uit AL je afspeellijsten halen.",
    "<b>App mode</b> — which side of the app is shown:":
        "<b>App-modus</b> — welke kant van de app wordt getoond:",
    "<b>Favorites library</b> — scanned on start (your tanzcds folder):":
        "<b>Favorietenbibliotheek</b> — ingelezen bij het starten (je tanzcds-map):",
    "<b>Reference path</b> — base folder the playlist files live in on THIS PC; 🧭 Fix paths re-roots broken references here (e.g. C:\\Users\\…\\my music\\tanzcds):":
        "<b>Referentiepad</b> — basismap waarin de afspeellijstbestanden op DEZE pc staan; 🧭 Paden herstellen hangt kapotte verwijzingen hier opnieuw in (bijv. C:\\Users\\…\\my music\\tanzcds):",
    "<b>Save-as folder</b> — where 'Save as M3U…' starts (e.g. D:\\Dropbox\\Turniere):":
        "<b>Map voor Opslaan als</b> — waar 'Opslaan als M3U…' begint (bijv. D:\\Dropbox\\Turniere):",
    "<b>Playlist file format</b> — what 'Save as M3U' and the exports write:":
        "<b>Bestandsformaat van afspeellijsten</b> — wat 'Opslaan als M3U' en de exports schrijven:",
    "UTF-8 (.m3u) — default": "UTF-8 (.m3u) — standaard",
    "UTF-8 with BOM (.m3u) — for Windows tools that guess ANSI":
        "UTF-8 met BOM (.m3u) — voor Windows-programma's die ANSI gokken",
    "UTF-8 (.m3u8) — the encoding named in the extension":
        "UTF-8 (.m3u8) — de codering staat in de extensie",
    "UTF-8 keeps every umlaut and is what current players read.\n"
    "Pick the BOM variant only if an older Windows tool shows 'Ã¼' instead\n"
    "of 'ü'; .m3u8 is the same UTF-8 under the extension some players expect.":
        "UTF-8 behoudt elk accent en is wat huidige spelers lezen.\n"
        "Kies de BOM-variant alleen als een ouder Windows-programma 'Ã¼' toont in plaats\n"
        "van 'ü'; .m3u8 is dezelfde UTF-8 onder de extensie die sommige spelers verwachten.",
    "<b>Search folders</b> — where else to look for a track when a playlist was written on another PC, one folder per line (e.g. F:\\my music and C:\\Users\\…\\Documents\\datein\\my music):":
        "<b>Zoekmappen</b> — waar verder naar een nummer gezocht wordt als een afspeellijst op een andere pc is geschreven, één map per regel (bijv. F:\\my music en C:\\Users\\…\\Documents\\datein\\my music):",
    "<b>Tournament playlists</b> — learned for popularity: .m3u files and/or tournament folders with copied music (e.g. H:\\DM Latein 2026):":
        "<b>Toernooiafspeellijsten</b> — geleerd voor populariteit: .m3u-bestanden en/of toernooimappen met gekopieerde muziek (bijv. H:\\DM Latein 2026):",
    "<b>What do you want to use this app for?</b>":
        "<b>Waarvoor wil je deze app gebruiken?</b>",
    "<b>Whole music repository</b> — used by global search (e.g. F:\\my music):":
        "<b>Hele muziekrepository</b> — gebruikt door globaal zoeken (bijv. F:\\my music):",
    "<b>▶ Player position</b> — where the master player stands in ▶ Playing mode:":
        "<b>▶ Positie van de speler</b> — waar de hoofdspeler staat in de modus ▶ Afspelen:",
    "<b>🌐 Language</b> — menus, buttons and dialogs:":
        "<b>🌐 Taal</b> — menu's, knoppen en dialogen:",
    "🇬🇧  English — the language the app is written in (default)":
        "🇬🇧  English — de taal waarin de app is geschreven (standaard)",
    "Every label exactly as the app ships it.":
        "Elk label precies zoals de app het levert.",
    "Menus, buttons and dialogs are translated. Track names, dance names and anything read from your files stay as they are.":
        "Menu's, knoppen en dialogen worden vertaald. Nummernamen, dansnamen en alles wat uit je bestanden wordt gelezen blijven zoals ze zijn.",
    "<b>🎚 Accent colour</b> — the blue the buttons, sliders and the ▶ player panel are built around:":
        "<b>🎚 Accentkleur</b> — het blauw waaromheen de knoppen, schuifregelaars en het ▶ spelerpaneel zijn opgebouwd:",
    "<b>🎚 TSO pitch target</b> — which takt the 🎚 button pitches a heat to. <i>Middle of the round</i> puts the round on one takt: the takt most of its titles are on where a step of one gets the rest there cheaply (T30+T31+T31 Cha-Chas → 31), the middle of its takte where it does not (T24+T25+T25 Rumbas → 24.5, T50+T52+T52 Quicksteps → 51). Nothing moves more than a takt. A fixed takt puts every title of that dance on the same tempo instead — worth setting on the slow dances, where one takt out of 24 is twice the pitch shift one takt out of 50 is.":
        "<b>🎚 TSO-toonhoogtedoel</b> — naar welke maatslag de 🎚 knop een heat trekt. <i>Midden van de ronde</i> zet de ronde op één maatslag: de maatslag waarop de meeste titels staan, als een stap van één de rest er goedkoop heen brengt (T30+T31+T31 Cha-Cha's → 31), anders het midden van de maatslagen (T24+T25+T25 Rumba's → 24,5, T50+T52+T52 Quicksteps → 51). Niets verschuift meer dan één maatslag. Een vaste maatslag zet in plaats daarvan elke titel van die dans op hetzelfde tempo — de moeite waard bij de langzame dansen, waar één maat van 24 twee keer zoveel toonhoogteverschuiving is als één maat van 50.",
    "<b>🎛 Play sets</b> — the two buttons on the ▶ Playing panel put the controls on these values in one press:":
        "<b>🎛 Speelsets</b> — de twee knoppen op het paneel ▶ Afspelen zetten de bediening met één druk op deze waarden:",
    "<b>🎨 Theme</b> — the classic light or dark, or one of the looks:":
        "<b>🎨 Thema</b> — het klassieke licht of donker, of een van de looks:",
    "<b>🎵 Check music</b> — thresholds used by the tournament checks (open decks and dragged-in files):":
        "<b>🎵 Muziek controleren</b> — drempels van de toernooicontroles (open decks en binnengesleepte bestanden):",
    "<b>🔊 Audio backend</b> — the engine every title is played through:":
        "<b>🔊 Audio-backend</b> — de engine waarmee elke titel wordt afgespeeld:",
    "Build everything on this tab in one go for a chosen library, in turn:\n"
    "🎚 librosa → 📊 loudness → 🔇 silences → 🐂 PD highlights → 🧠 OpenL3 →\n"
    "🎼 Chroma. Reuses anything already cached and can be cancelled\n"
    "between/within steps. Read-only; your audio files are never modified.\n"
    "Skips models that aren't installed — and 🎙 Demucs vocals, which are far\n"
    "slower than the rest and stay a deliberate choice.":
        "Alles op deze tab in één keer bouwen voor een gekozen bibliotheek, om de beurt:\n"
        "🎚 librosa → 📊 luidheid → 🔇 stiltes → 🐂 PD-hoogtepunten → 🧠 OpenL3 →\n"
        "🎼 Chroma. Hergebruikt alles wat al gecachet is en kan worden geannuleerd\n"
        "tussen en tijdens de stappen. Alleen-lezen; je audiobestanden worden nooit gewijzigd.\n"
        "Slaat niet-geïnstalleerde modellen over — en 🎙 Demucs-zang, die veel\n"
        "trager is dan de rest en een bewuste eigen keuze blijft.",
    "Chroma vectors match melody/harmony instead of sound, so the\n"
    "Similar-Tracks window can find remixes & covers of the same tune.\n"
    "librosa-only; reuses anything already cached.":
        "Chroma-vectoren vergelijken melodie/harmonie in plaats van klank, zodat\n"
        "het venster met vergelijkbare nummers remixes en covers van hetzelfde lied vindt.\n"
        "Alleen met librosa; hergebruikt alles wat al gecachet is.",
    "Close this and filter the library pane to the selected\n"
    "row's dance + class, showing only tracks you have never played.":
        "Dit sluiten en het bibliotheekpaneel filteren op dans + klasse van de\n"
        "geselecteerde rij, met alleen nummers die je nog nooit hebt gedraaid.",
    "Compute the selected similarity index over the library (global repo\n"
    "when global search is on, else the favorites library). Reuses anything\n"
    "already cached; only missing vectors are added.":
        "De gekozen overeenkomstindex over de bibliotheek berekenen (de globale repo\n"
        "als globaal zoeken aan staat, anders de favorietenbibliotheek). Hergebruikt alles\n"
        "wat al gecachet is; alleen ontbrekende vectoren worden toegevoegd.",
    "Detect the highlights of every Paso Doble in the music library\n"
    "and store them in the local database, so the highlight stop is\n"
    "armed instantly on playback (already-analyzed tracks are skipped).":
        "De hoogtepunten van elke Paso Doble in de muziekbibliotheek detecteren\n"
        "en in de lokale database opslaan, zodat de hoogtepuntstop\n"
        "bij het afspelen meteen klaarstaat (al geanalyseerde nummers worden overgeslagen).",
    "Find the silent stretches of every track of the music library\n"
    "(via ffmpeg; already-probed tracks are skipped, results are\n"
    "cached). Playback probes each new title itself — doing it up\n"
    "front keeps that decode off the disk during a tournament.":
        "De stille stukken van elk nummer in de muziekbibliotheek vinden\n"
        "(via ffmpeg; al onderzochte nummers worden overgeslagen, resultaten\n"
        "worden gecachet). Het afspelen onderzoekt elke nieuwe titel zelf — vooraf\n"
        "gedaan houdt dat het decoderen tijdens een toernooi van de schijf.",
    "Global search needs the repo's audio analyzed once (⚗ Analysis tab). Analysis only <i>reads</i> your files — it never modifies them. Results are cached, so repeat searches are fast.":
        "Globaal zoeken heeft de audio van de repo één keer geanalyseerd nodig (tab ⚗ Analyse). De analyse <i>leest</i> je bestanden alleen — ze wijzigt ze nooit. Resultaten worden gecachet, dus herhaalde zoekopdrachten zijn snel.",
    "Shorter by %s s": "%s s korter",
    "Longer by %s s — past %s the title plays to its end":
        "%s s langer — voorbij %s speelt de titel tot het einde",
    "Tempo %s %s — hold to glide": "Tempo %s %s — vasthouden om te glijden",
    "slower": "langzamer",
    "faster": "sneller",
    "How long the volume takes to ramp down to 0 when\n"
    "the play length cuts a title — half-second steps":
        "Hoe lang het volume nodig heeft om naar 0 te zakken wanneer\n"
        "de speelduur een titel afkapt — in stappen van een halve seconde",
    "Invalid rounds": "Ongeldige rondes",
    "Library gap dashboard: per dance × class — pool size, tournament-\n"
    "tempo compliance, proven/fresh split and staleness. Thin pools\n"
    "are marked red.":
        "Overzicht van gaten in de bibliotheek: per dans × klasse — poolgrootte, naleving\n"
        "van het toernooitempo, verdeling beproefd/nieuw en veroudering. Dunne pools\n"
        "zijn rood gemarkeerd.",
    "Measure each track's vocal share by actually separating the vocals\n"
    "from the music (Demucs source separation) — far more reliable than\n"
    "the tag/filename heuristics for the Vocal/Instrumental filter.\n"
    "~7 s per track, cached; already-measured tracks are skipped.":
        "Het zangaandeel van elk nummer meten door de zang echt van de\n"
        "muziek te scheiden (Demucs-bronscheiding) — veel betrouwbaarder dan\n"
        "de heuristiek op tags/bestandsnaam voor het filter Zang/Instrumentaal.\n"
        "~7 s per nummer, gecachet; al gemeten nummers worden overgeslagen.",
    "Measure the EBU R128 loudness of every track of the music\n"
    "library (via ffmpeg; already-measured tracks are skipped,\n"
    "results are cached). Enables 🔊 Equalize volume in Playing mode.":
        "De EBU R128-luidheid van elk nummer in de muziekbibliotheek\n"
        "meten (via ffmpeg; al gemeten nummers worden overgeslagen,\n"
        "resultaten worden gecachet). Maakt 🔊 Volume gelijktrekken in de afspeelmodus mogelijk.",
    "One row per competition — each fills its own 📅 day deck on the\n"
    "Tournament-day tab; more than 8 competitions share decks (labeled\n"
    "round headers). All competitions share one no-repeat pool for the day (Paso Doble may repeat).":
        "Eén rij per wedstrijd — elke wedstrijd vult een eigen 📅 dagdeck op de\n"
        "tab Toernooidag; bij meer dan 8 wedstrijden delen ze decks (met\n"
        "gelabelde rondekoppen). Alle wedstrijden delen één pool zonder herhaling voor de dag (Paso Doble mag herhalen).",
    "Only change this if the sound gives you trouble: a title that\n"
    "won't play, or the short gap a pitch change costs — the two\n"
    "engines handle that differently. Takes effect on the next start.":
        "Wijzig dit alleen als het geluid problemen geeft: een titel die\n"
        "niet speelt, of het korte gat dat een toonhoogtewijziging kost — de twee\n"
        "engines gaan daar verschillend mee om. Werkt bij de volgende start.",
    "Only the accent's own family of tints follows this colour.\n"
    "A red warning, a green proven mark and the popularity amber mean\n"
    "something, so they keep their hue.":
        "Alleen de eigen tintenfamilie van het accent volgt deze kleur.\n"
        "Een rode waarschuwing, een groen beproefd-teken en het amber van populariteit\n"
        "betekenen iets en houden daarom hun kleur.",
    "Planner only hides the tournament floor's playing panel;\n"
    "Player only hides everything that generates or checks a playlist.\n"
    "Nothing is removed — switching back brings it all straight back.":
        "Alleen planner verbergt alleen het afspeelpaneel voor de toernooivloer;\n"
        "Alleen speler verbergt alleen alles wat een afspeellijst genereert of controleert.\n"
        "Er wordt niets verwijderd — terugschakelen brengt alles meteen terug.",
    "Playlists still build and play without it. These need it and stay unavailable:<ul><li>analysing the library — tempo, similar tracks</li><li>🔊 loudness levelling (EBU R128)</li><li>🔇 silence detection at the start and end of a track</li></ul>":
        "Afspeellijsten kunnen ook zonder worden gemaakt en afgespeeld. Dit heeft het nodig en blijft niet beschikbaar:<ul><li>de bibliotheek analyseren — tempo, vergelijkbare nummers</li><li>🔊 luidheid gelijktrekken (EBU R128)</li><li>🔇 stiltedetectie aan begin en einde van een nummer</li></ul>",
    "Re-read every M3U and tournament music folder in the tournament\n"
    "playlist folder and rebuild the popularity / co-occurrence index from\n"
    "it — WITHOUT rescanning files or audio. Use after exporting a played\n"
    "tournament so it counts right away.":
        "Elke M3U en elke toernooimuziekmap in de toernooi-afspeellijstmap\n"
        "opnieuw inlezen en de index voor populariteit / samen voorkomen daaruit\n"
        "opnieuw opbouwen — ZONDER bestanden of audio opnieuw in te lezen. Gebruik dit na\n"
        "het exporteren van een gespeeld toernooi, zodat het meteen meetelt.",
    "Remove cached rows for music files that no longer exist (features,\n"
    "embeddings, loudness, …) and compact the database file (VACUUM).\n"
    "Slow on a big library; refuses to run when the music drive looks\n"
    "unmounted so cached analysis can't be wiped by accident.":
        "Gecachete rijen verwijderen voor muziekbestanden die niet meer bestaan (kenmerken,\n"
        "embeddings, luidheid, …) en het databasebestand comprimeren (VACUUM).\n"
        "Traag bij een grote bibliotheek; weigert te draaien als de muziekschijf\n"
        "niet gekoppeld lijkt, zodat de opgeslagen analyse niet per ongeluk wordt gewist.",
    "Run librosa on the favorites library's MP3 files not yet cached.\n"
    "Required for timbral similarity scoring; when everything is cached\n"
    "a click offers a full re-analysis (e.g. after a tempo-method change).":
        "librosa laten lopen over de nog niet gecachete MP3-bestanden van de favorietenbibliotheek.\n"
        "Nodig voor de timbre-overeenkomstscore; als alles gecachet is\n"
        "biedt een klik een volledige heranalyse aan (bijv. na een wijziging van de tempomethode).",
    "Scan the whole repository and analyze any files not yet cached, using the\n"
    "fast librosa timbre+rhythm features (the default similarity method).\n"
    "Read-only; runs in the background and can be left to finish.":
        "De hele repository doorzoeken en alle nog niet gecachete bestanden analyseren, met de\n"
        "snelle librosa-kenmerken voor timbre+ritme (de standaardmethode voor overeenkomst).\n"
        "Alleen-lezen; draait op de achtergrond en kan worden afgemaakt.",
    "Takes effect after restarting the app. If the sound stays away afterwards, switch back here — the setting is only read at start, so nothing else in the app depends on it.":
        "Werkt na een herstart van de app. Blijft het geluid daarna weg, schakel hier dan terug — de instelling wordt alleen bij het starten gelezen, dus verder hangt niets in de app ervan af.",
    "The 🐂 Paso Doble highlight stop is <i>switched off</i> by the 🏆 tournament set: its detection is not good enough yet to cut a competition Paso Doble on, and a heat stopped in the wrong bar is danced twice. It is not configurable here — the 🎉 party set leaves it wherever you set it on the Playing panel, and you can switch it back on there for a demo.":
        "De 🐂 hoogtepuntstop van de Paso Doble wordt door de 🏆 toernooiset <i>uitgeschakeld</i>: de herkenning is nog niet goed genoeg om een wedstrijd-Paso Doble op af te kappen, en een heat die in de verkeerde maat stopt wordt twee keer gedanst. Hier is dat niet instelbaar — de 🎉 feestset laat hem zoals je hem op het afspeelpaneel hebt gezet, en daar kun je hem voor een demonstratie weer aanzetten.",
    "Theme, accent and language are read when the app starts, so a change takes effect after a restart — you are asked once you save.":
        "Thema, accent en taal worden gelezen als de app start, dus een wijziging werkt na een herstart — dat wordt je gevraagd zodra je opslaat.",
    "Keep the German dance and round names on a screen in another language (Langsamer Walzer, Vorrunde, Standardrunde 1, Eintanzen …)":
        "De Duitse dans- en rondenamen behouden op een scherm in een andere taal (Langsamer Walzer, Vorrunde, Standardrunde 1, Eintanzen …)",
    "On: the presenter screen and the recorded announcements are German too, and a 🤸 practice list is called Eintanzen, also in its saved file.\n"
    "Off: Slow Waltz, Round 1, Standard round 1, Practice … — the playlists and exports keep the German dance and round names either way.":
        "Aan: ook het presentatiescherm en de opgenomen aankondigingen zijn in het Duits, en een 🤸 oefenlijst heet Eintanzen, ook in het opgeslagen bestand.\n"
        "Uit: Slow Waltz, Round 1, Standard round 1, Oefenen … — de afspeellijsten en exports houden in elk geval de Duitse dans- en rondenamen.",
    "Two controls that are set once and then never touched again,\n"
    "in the busiest column of the desk. Hidden the switch keeps whatever\n"
    "it was set to — only the controls go away.":
        "Twee bedieningselementen die je één keer instelt en daarna nooit meer aanraakt,\n"
        "in de drukste kolom van de tafel. Verborgen houdt de schakelaar de waarde\n"
        "waarop hij stond — alleen de bediening verdwijnt.",
    "You can change this later under ⚙ Settings → ⚙ General.":
        "Je kunt dit later wijzigen onder ⚙ Instellingen → ⚙ Algemeen.",
    "lower": "laag",
    "middle": "midden",
    "upper": "hoog",
    "⚠️  <b>ffmpeg is not installed on this computer.</b>":
        "⚠️  <b>ffmpeg is niet geïnstalleerd op deze computer.</b>",
    "🌐  Global search — match dropped files against the whole repository (default: favorites library only)":
        "🌐  Globaal zoeken — neergezette bestanden vergelijken met de hele repository (standaard: alleen de favorietenbibliotheek)",
    "🎙  Advanced voice controls — show '…with heat' and 🔈 Test under 'Announce next dance'":
        "🎙  Uitgebreide stembediening — ‘…met heat’ en 🔈 Test tonen onder ‘Volgende dans aankondigen’",
    "🎧  Preview player — float a mini player (seek / skip / volume) over the deck when a ▶ button is clicked":
        "🎧  Voorbeeldspeler — een minispeler (spoelen / overslaan / volume) boven het deck tonen als op een ▶-knop wordt geklikt",
    "🐘 Heavy — AI models, needs the FULL build (or the requirements-full.txt extras)":
        "🐘 Zwaar — AI-modellen, vereist de VOLLEDIGE build (of de extra's uit requirements-full.txt)",
    "🔇  Release the sound card between titles — takes away the hiss an onboard output puts on the PA while the app holds it open":
        "🔇  De geluidskaart tussen titels vrijgeven — haalt de ruis weg die een onboard-uitgang op de geluidsinstallatie zet zolang de app hem openhoudt",
    "🔕  Mute system sounds while the evening runs — no error ding or notification chime over the speakers":
        "🔕  Systeemgeluiden dempen zolang de avond loopt — geen foutpiep of meldingsgeluid over de luidsprekers",
    "🐞  Send error reports — when the app hits an error, send its technical details to the developer":
        "🐞  Foutrapporten versturen — als de app een fout tegenkomt, de technische details naar de ontwikkelaar sturen",
    "Goes to the developer's GlitchTip project (app.glitchtip.com),\n"
    "which also sees the IP address a report comes from.\n"
    "\n"
    "Sent: the error and where in the program it happened, the last\n"
    "log lines before it (they can name the title that was playing),\n"
    "the operating system and the app version.\n"
    "\n"
    "Not sent: your music, your playlists, your computer's name.\n"
    "Your user folder is cut out of every path.\n"
    "\n"
    "Off by default. Applies as soon as you save.":
        "Gaat naar het GlitchTip-project van de ontwikkelaar (app.glitchtip.com),\n"
        "dat ook het IP-adres ziet waar een rapport vandaan komt.\n"
        "\n"
        "Verstuurd: de fout en waar in het programma die gebeurde, de laatste\n"
        "logregels ervoor (die kunnen de spelende titel noemen),\n"
        "het besturingssysteem en de app-versie.\n"
        "\n"
        "Niet verstuurd: je muziek, je afspeellijsten, de naam van je computer.\n"
        "Je gebruikersmap wordt uit elk pad geknipt.\n"
        "\n"
        "Standaard uit. Geldt zodra je opslaat.",
    "Error reports": "Foutrapporten",
    "Send error reports to the developer?":
        "Foutrapporten naar de ontwikkelaar sturen?",
    "When the app hits an error, it can send the technical details\n"
    "to the developer's GlitchTip project (app.glitchtip.com),\n"
    "so the error gets fixed. GlitchTip also sees the IP address\n"
    "a report comes from.\n"
    "\n"
    "Responsible: marcelkb, the developer. Questions about your data\n"
    "or deleting reports: github.com/dancesport-dj/DanceSportPlayer/issues\n"
    "\n"
    "Sent: the error and where in the program it happened, the last\n"
    "log lines before it (they can name the title that was playing),\n"
    "the operating system and the app version.\n"
    "\n"
    "Not sent: your music, your playlists, your computer's name.\n"
    "Your user folder is cut out of every path.\n"
    "\n"
    "You can change this at any time under ⚙ Settings → ⚙ General.":
        "Als de app een fout tegenkomt, kan hij de technische details\n"
        "naar het GlitchTip-project van de ontwikkelaar (app.glitchtip.com) sturen,\n"
        "zodat de fout wordt verholpen. GlitchTip ziet daarbij ook het IP-adres\n"
        "waar een rapport vandaan komt.\n"
        "\n"
        "Verantwoordelijk: marcelkb, de ontwikkelaar. Vragen over je gegevens\n"
        "of het verwijderen van rapporten: github.com/dancesport-dj/DanceSportPlayer/issues\n"
        "\n"
        "Verstuurd: de fout en waar in het programma die gebeurde, de laatste\n"
        "logregels ervoor (die kunnen de spelende titel noemen),\n"
        "het besturingssysteem en de app-versie.\n"
        "\n"
        "Niet verstuurd: je muziek, je afspeellijsten, de naam van je computer.\n"
        "Je gebruikersmap wordt uit elk pad geknipt.\n"
        "\n"
        "Je kunt dit altijd wijzigen onder ⚙ Instellingen → ⚙ Algemeen.",
    "Send reports": "Rapporten versturen",
    "Don't send": "Niet versturen",
    "Once per start, the app asks GitHub (api.github.com) for the latest\n"
    "release. The request carries nothing about you or your music; GitHub\n"
    "sees the IP address it comes from. A newer version is announced once,\n"
    "with a link to its download page. Nothing is downloaded or installed.\n"
    "\n"
    "You can change this at any time under ⚙ Settings → ⚙ General.":
        "Eén keer per start vraagt de app GitHub (api.github.com) naar de\n"
        "nieuwste release. Het verzoek bevat niets over jou of je muziek; GitHub\n"
        "ziet het IP-adres waar het vandaan komt. Een nieuwere versie wordt één\n"
        "keer aangekondigd, met een link naar de downloadpagina. Er wordt niets\n"
        "gedownload of geïnstalleerd.\n"
        "\n"
        "Je kunt dit altijd wijzigen onder ⚙ Instellingen → ⚙ Algemeen.",
    "🔔  Also tell me when a new version is out":
        "🔔  Laat me ook weten wanneer er een nieuwe versie is",
    "New versions": "Nieuwe versies",
    "Tell you when a new version is out?": "Je laten weten wanneer er een nieuwe versie is?",
    "Check for new versions": "Naar nieuwe versies zoeken",
    "Don't check": "Niet zoeken",
    "🔔  Check for new versions — once per start, ask GitHub whether a newer release is out":
        "🔔  Naar nieuwe versies zoeken — één keer per start GitHub vragen of er een nieuwere release is",
    "Asks api.github.com for the latest release. The request carries\n"
    "nothing about you or your music; GitHub sees the IP address it\n"
    "comes from. A newer version is announced once, with a link to\n"
    "its download page. Nothing is downloaded or installed.\n"
    "\n"
    "Off by default. Applies from the next start.":
        "Vraagt api.github.com naar de nieuwste release. Het verzoek bevat niets\n"
        "over jou of je muziek; GitHub ziet het IP-adres waar het vandaan komt.\n"
        "Een nieuwere versie wordt één keer aangekondigd, met een link naar de\n"
        "downloadpagina. Er wordt niets gedownload of geïnstalleerd.\n"
        "\n"
        "Standaard uit. Geldt vanaf de volgende start.",
    "New version": "Nieuwe versie",
    "Version %s is out.": "Versie %s is uit.",
    "You are running %s. The download page lists what changed.":
        "Je gebruikt %s. De downloadpagina vermeldt wat er veranderd is.",
    "Open download page": "Downloadpagina openen",
    "The music and the computer share the one sound card, so every\n"
    "sound the system makes goes out over the PA too.\n"
    "\n"
    "Muted all through Playing mode and whenever something plays,\n"
    "put back when you return to planning or close the app.\n"
    "Windows: the System Sounds slider of the volume mixer.\n"
    "macOS: the alert volume. Linux (GNOME): event sounds.":
        "De muziek en de computer delen één geluidskaart, dus elk\n"
        "geluid van het systeem gaat ook over de geluidsinstallatie.\n"
        "\n"
        "Gedempt in de hele afspeelmodus en telkens als er iets speelt,\n"
        "teruggezet als je terugkeert naar plannen of de app sluit.\n"
        "Windows: de schuif Systeemgeluiden in het volumemengpaneel.\n"
        "macOS: het waarschuwingsvolume. Linux (GNOME): gebeurtenisgeluiden.",
    "🧭 Fix paths tries the Reference path first and then these folders,\n"
    "in order, cutting the foreign path down until what is left lands on a\n"
    "real file underneath one of them. A path is only ever rewritten to a\n"
    "file that is actually there.":
        "🧭 Paden herstellen probeert eerst het referentiepad en dan deze mappen,\n"
        "op volgorde, en kort het vreemde pad in tot wat overblijft op een\n"
        "echt bestand onder een ervan uitkomt. Een pad wordt alleen herschreven\n"
        "naar een bestand dat er echt is.",
    "Drag <b>.m3u playlists</b> here (audio files work too) to check whether any of their tracks are duplicates of <b>each other</b> — across the dropped playlists, by audio content, else title.":
        "Sleep hier <b>.m3u-afspeellijsten</b> naartoe (audiobestanden kan ook) om te controleren of nummers <b>onderling</b> dubbel zijn — over de neergezette afspeellijsten heen, op audio-inhoud, anders op titel.",
    "Drop a <b>reference playlist</b> (.m3u) and the <b>tournament files</b> (.m3u playlists or audio) below. The reference is compared against the tournament tracks and every <b>hard duplicate</b> (byte-identical audio) is removed; the leftover <b>unused</b> tracks are exported to a new .m3u. <span style='color:#666'>Paso Doble is excluded from the comparison and always kept.</span>":
        "Zet hieronder een <b>referentie-afspeellijst</b> (.m3u) en de <b>toernooibestanden</b> (.m3u-afspeellijsten of audio) neer. De referentie wordt vergeleken met de toernooinummers en elk <b>hard duplicaat</b> (byte-identieke audio) wordt verwijderd; de overgebleven <b>ongebruikte</b> nummers worden naar een nieuwe .m3u geëxporteerd. <span style='color:#666'>Paso Doble valt buiten de vergelijking en blijft altijd staan.</span>",
    "Duplicate songs across your open playlist(s), in playlist order.<br><span style='color:#666'>🟰 <b>Exact</b> = identical audio. ≈ <b>Similar</b> = same title, a different recording. Keep the ones you want; switch the others to <b>Replace</b> and pick a track for each, or to <b>Remove</b>.</span>":
        "Dubbele nummers in je open afspeellijst(en), in de volgorde van de afspeellijst.<br><span style='color:#666'>🟰 <b>Exact</b> = identieke audio. ≈ <b>Vergelijkbaar</b> = dezelfde titel, een andere opname. Houd de gewenste; zet de andere op <b>Vervangen</b> en kies voor elk een nummer, of op <b>Verwijderen</b>.</span>",
    "Every copy of this song is already controlled by the within-playlist\n"
    "section above, so there is nothing left to resolve on this row.":
        "Elke kopie van dit nummer wordt al geregeld door het onderdeel\n"
        "‘binnen de afspeellijst’ hierboven, dus op deze regel valt niets meer op te lossen.",
    "Export unused tracks": "Ongebruikte nummers exporteren",
    "No hard duplicates of the tournament files were found in the reference — nothing to remove.":
        "Er zijn geen harde duplicaten van de toernooibestanden in de referentie gevonden — niets te verwijderen.",
    "Nothing to change — no occurrence is set to Replace or Remove.":
        "Niets te wijzigen — geen enkel voorkomen staat op Vervangen of Verwijderen.",
    "Reference base": "Referentiebasis",
    "Resolve duplicates": "Duplicaten oplossen",
    "Sort the exported tracks by dance?\n"
    "\n"
    "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)":
        "De geëxporteerde nummers op dans sorteren?\n"
        "\n"
        "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)",
    "The reference base must be a single .m3u playlist.":
        "De referentiebasis moet één .m3u-afspeellijst zijn.",
    "This list holds some titles more than once.<br><span style='color:#666'>For each title, pick the file to keep — the others are removed. <b>Keep all</b> leaves that title alone.</span>":
        "Deze lijst bevat sommige titels meer dan eens.<br><span style='color:#666'>Kies per titel het bestand dat blijft — de andere worden verwijderd. <b>Alle houden</b> laat die titel met rust.</span>",
    "Browse by library category — 🏆 Tournament hides the non-tournament\n"
    "folders (anthems, background, wrong-tempo, duplicates, seasonal);\n"
    "pick a category to look only at those (handy for parties).":
        "Bladeren op bibliotheekcategorie — 🏆 Toernooi verbergt de mappen\n"
        "die niet voor toernooien zijn (hymnes, achtergrond, verkeerd tempo,\n"
        "duplicaten, seizoensgebonden); kies een categorie om alleen die te zien (handig voor feesten).",
    "Drag a track onto a deck or wishlist to use it.\n"
    "▶ to preview · double-click to open in your external player\n"
    "· right-click for more.":
        "Sleep een nummer naar een deck of wensenlijst om het te gebruiken.\n"
        "▶ om voor te luisteren · dubbelklik om het in je externe speler te openen\n"
        "· rechtsklik voor meer.",
    "Only tracks suited for this starting class\n"
    "(tracks without a class tag are always shown)":
        "Alleen nummers die bij deze startklasse passen\n"
        "(nummers zonder klasse-aanduiding worden altijd getoond)",
    "Only tracks whose file was created in the library that\n"
    "recently. Combine with ✦ Never played to see what you\n"
    "copied in but have never actually used.":
        "Alleen nummers waarvan het bestand zo recent in de bibliotheek\n"
        "is aangemaakt. Combineer met ✦ Nooit gespeeld om te zien wat je\n"
        "erin hebt gekopieerd maar nooit echt hebt gebruikt.",
    "Show only tracks not already used in any open playlist deck —\n"
    "handy for finding fresh music while building rounds.":
        "Alleen nummers tonen die nog in geen enkel open afspeellijstdeck\n"
        "staan — handig om verse muziek te vinden bij het bouwen van rondes.",
    "Substring of the title, the artist, or a comment marker\n"
    "(vocal_f, classic, eintanzen, …)":
        "Deel van de titel, de artiest of een commentaarmarkering\n"
        "(vocal_f, classic, eintanzen, …)",
    "proven": "beproefd",
    "rare": "zeldzaam",
    "Audio analysis unavailable": "Audioanalyse niet beschikbaar",
    "Audio cache not ready yet — try again shortly.":
        "De audiocache is nog niet klaar — probeer het zo opnieuw.",
    "Build ALL caches": "ALLE caches bouwen",
    "Build all caches": "Alle caches bouwen",
    "Analyze loudness": "Luidheid analyseren",
    "Analyze vocals (Demucs)": "Zang analyseren (Demucs)",
    "No Paso Doble tracks in the library.":
        "Geen Paso Doble-nummers in de bibliotheek.",
    "Probe silences": "Stiltes onderzoeken",
    "Re-analyze Audio": "Audio opnieuw analyseren",
    "Redo the 🐂 auto-detection for the whole library — for after the\n"
    "detector changed. Hand-set 🎯 marks are kept untouched.":
        "De automatische 🐂-herkenning opnieuw draaien voor de hele bibliotheek —\n"
        "voor als de detector is veranderd. Met de hand gezette 🎯-markeringen blijven onaangeroerd.",
    "The music library is not loaded yet.":
        "De muziekbibliotheek is nog niet geladen.",
    "ffmpeg was not found (neither on PATH nor the copy bundled\n"
    "with the project) — loudness cannot be measured.":
        "ffmpeg is niet gevonden (niet op PATH en ook niet de kopie die\n"
        "bij het project zit) — de luidheid kan niet worden gemeten.",
    "ffmpeg was not found (neither on PATH nor the copy bundled\n"
    "with the project) — silences cannot be probed.":
        "ffmpeg is niet gevonden (niet op PATH en ook niet de kopie die\n"
        "bij het project zit) — stiltes kunnen niet worden onderzocht.",
    "Clear playlists": "Afspeellijsten leegmaken",
    "Clear tournament day": "Toernooidag leegmaken",
    "Close tournament day": "Toernooidag sluiten",
    "Competition name (empty = default):":
        "Naam van de wedstrijd (leeg = standaard):",
    "Competition name:": "Naam van de wedstrijd:",
    "Free order": "Vrije volgorde",
    "None of these tracks says which dance it is, so there is no grid to build from them — the list stays a free running order.":
        "Geen van deze nummers zegt welke dans het is, dus er valt geen raster van te bouwen — de lijst blijft een vrije speelvolgorde.",
    "New tournament day": "Nieuwe toernooidag",
    "Rename tournament day": "Toernooidag hernoemen",
    "Shuffle — put the same titles in a fresh order,\n"
    "as if the party list were built again from scratch.":
        "Schudden — dezelfde titels in een nieuwe volgorde zetten,\n"
        "alsof de feestlijst opnieuw vanaf nul werd gebouwd.",
    "Total play time of this playlist\n"
    "(↳ backup rows not counted — they only play as stand-ins)\n"
    "Click ▸ for the songs per dance":
        "Totale speelduur van deze afspeellijst\n"
        "(↳ reserveregels tellen niet mee — die spelen alleen als invaller)\n"
        "Klik op ▸ voor de nummers per dans",
    "Every similar track is already in an open playlist.":
        "Elk vergelijkbaar nummer staat al in een open afspeellijst.",
    "No similar tracks found — the song may not be audio-analyzed yet.":
        "Geen vergelijkbare nummers gevonden — het nummer is misschien nog niet geanalyseerd.",
    "Replace duplicate": "Duplicaat vervangen",
    "Audio index": "Audio-index",
    "Audio index ready": "Audio-index klaar",
    "Build audio index": "Audio-index bouwen",
    "Embedding index error": "Fout in de embedding-index",
    "Favorites library isn't loaded yet.":
        "De favorietenbibliotheek is nog niet geladen.",
    "The whole-repository library isn't loaded yet. Drop a file (or build the librosa index over the repository) once to load it, then retry.":
        "De bibliotheek van de hele verzameling is nog niet geladen. Zet één keer een bestand neer (of bouw de librosa-index over de verzameling) om hem te laden en probeer het dan opnieuw.",
    "Not on the Reference path": "Niet in het referentiepad",
    "Save Error": "Fout bij opslaan",
    "Save as M3U": "Opslaan als M3U",
    "This deck is empty.": "Dit deck is leeg.",
    "Fold this playlist to a tab —\n"
    "the other open playlists get its space.":
        "Deze afspeellijst tot een tabblad inklappen —\n"
        "de andere open afspeellijsten krijgen de ruimte.",
    "AI playlist": "AI-afspeellijst",
    "AI playlist failed": "AI-afspeellijst mislukt",
    "All picks are TSO-conform (T24 Rumba / T58-59 Paso allowed, like the normal playlist).":
        "Alle keuzes zijn TSO-conform (T24 Rumba / T58-59 Paso toegestaan, zoals bij de normale afspeellijst).",
    "Cap the party-list length — handy when drawing from the whole library.\n"
    "The round it lands in is played out, so the list can run a title or two over.\n"
    "0 = No limit (use every eligible track).":
        "De lengte van de feestlijst begrenzen — handig als je uit de hele bibliotheek put.\n"
        "De ronde waarin de grens valt wordt uitgespeeld, dus de lijst kan een titel of twee langer zijn.\n"
        "0 = Geen grens (elk geschikt nummer gebruiken).",
    "Choose an .m3u file first.": "Kies eerst een .m3u-bestand.",
    "Dances come in alternating 3-dance rounds (not competition rounds).":
        "Dansen komen in afwisselende rondes van 3 dansen (geen wedstrijdrondes).",
    "Day plan": "Dagplan",
    "Draw from your library, exactly like the left panel's Favorites mode.":
        "Uit je bibliotheek putten, precies zoals de modus Favorieten van het linkerpaneel.",
    "Draw only from the tracks currently parked in your open ⭐ wishlists.":
        "Alleen putten uit de nummers die nu in je open ⭐ wensenlijsten staan.",
    "Practice Error": "Oefenfout",
    "Enter a valid round pattern (e.g. 6-3-2-1).":
        "Voer een geldig rondeschema in (bijv. 6-3-2-1).",
    "Generate Error": "Fout bij genereren",
    "History Error": "Fout in de geschiedenis",
    "Library gaps": "Gaten in de bibliotheek",
    "No Competition": "Geen wedstrijd",
    "No Dances": "Geen dansen",
    "No Matches": "Geen treffers",
    "No Rounds": "Geen rondes",
    "No Theme": "Geen thema",
    "No candidate tracks for those settings — check the dances, the\n"
    "start class and that the library actually holds those tempos.":
        "Geen kandidaat-nummers voor deze instellingen — controleer de dansen, de\n"
        "startklasse en of de bibliotheek die tempo's echt heeft.",
    "No matching tracks for the chosen options — check the class, the source and that the library / .m3u actually has those dances.":
        "Geen passende nummers voor de gekozen opties — controleer de klasse, de bron en of de bibliotheek / .m3u die dansen echt heeft.",
    "No resolvable tracks in that .m3u file.":
        "Geen enkel nummer in dat .m3u-bestand kon worden gevonden.",
    "Paste a schedule and click 'Parse schedule', then pick a competition.":
        "Plak een schema, klik op ‘Schema lezen’ en kies dan een wedstrijd.",
    "Pick at least Standard or Latin dances.":
        "Kies ten minste Standard- of Latin-dansen.",
    "Please select a theme.": "Kies een thema.",
    "Please select at least one dance.": "Kies ten minste één dans.",
    "Replace day plan": "Dagplan vervangen",
    "Share of slots that lean FRESH (least-played) instead of proven favourites.\n"
    "Higher = more never/barely-played tracks — at 100 % the list is\n"
    "built from the least-played tracks upward (not just the few with zero plays).":
        "Aandeel van de plaatsen dat naar VERS (minst gespeeld) neigt in plaats van naar beproefde favorieten.\n"
        "Hoger = meer nooit of nauwelijks gespeelde nummers — bij 100 % wordt de lijst\n"
        "opgebouwd vanaf de minst gespeelde nummers (niet alleen de paar zonder enige keer).",
    "The Tournament-day tab still holds an earlier day plan.\n"
    "\n"
    "Replace it with the new one?":
        "Het tabblad Toernooidag bevat nog een eerder dagplan.\n"
        "\n"
        "Vervangen door het nieuwe?",
    "The library is still loading — try again in a moment.":
        "De bibliotheek wordt nog geladen — probeer het zo opnieuw.",
    "The model answered, but none of its picks matched the\n"
    "catalog. Try again — or lower the round count.":
        "Het model antwoordde, maar geen van zijn keuzes paste bij de\n"
        "catalogus. Probeer het opnieuw — of verlaag het aantal rondes.",
    "The model answered, but none of its picks matched the catalog.":
        "Het model antwoordde, maar geen van zijn keuzes paste bij de catalogus.",
    "The selected competition has no valid heat counts.":
        "De gekozen wedstrijd heeft geen geldige aantallen heats.",
    "The wish list is empty — write the titles you want, one\n"
    "per line or a column per dance.":
        "De wensenlijst is leeg — schrijf de gewenste titels op, één\n"
        "per regel of een kolom per dans.",
    "Theme Error": "Themafout",
    "Upper limit. The list stops here or when the TSO-conform pool runs dry — whichever comes first.":
        "Bovengrens. De lijst stopt hier of als de TSO-conforme pool op is — wat het eerst gebeurt.",
    "Your open wishlists are empty — park some tracks there first.":
        "Je open wensenlijsten zijn leeg — zet daar eerst wat nummers neer.",
    "🆕 This competition has no saved work yet — press ⚡ Generate from History to seed it":
        "🆕 Voor deze wedstrijd is nog niets opgeslagen — druk op ⚡ Genereren uit geschiedenis om te beginnen",
    "🏆  Practice for a tournament class (round-robin through the class's dances)":
        "🏆  Oefenen voor een toernooiklasse (de dansen van de klasse om de beurt)",
    "Analysis Error": "Analysefout",
    "Build librosa index": "librosa-index bouwen",
    "Clean up database": "Database opruimen",
    "Could not start a new instance — please start the app again yourself.":
        "Kon geen nieuwe instantie starten — start de app zelf opnieuw.",
    "Finding similar tracks for a file needs librosa + ffmpeg.\n"
    "Install them, then retry.":
        "Vergelijkbare nummers voor een bestand zoeken vereist librosa + ffmpeg.\n"
        "Installeer ze en probeer het opnieuw.",
    "Global Index Error": "Fout in de globale index",
    "Global search": "Globaal zoeken",
    "Library Load Error": "Fout bij laden van de bibliotheek",
    "Re-learn playlists": "Afspeellijsten opnieuw leren",
    "Set a valid music repository folder first.":
        "Stel eerst een geldige map voor de muziekverzameling in.",
    "Set a valid music repository folder in ⚙ Settings first.":
        "Stel eerst in ⚙ Instellingen een geldige map voor de muziekverzameling in.",
    "Settings saved": "Instellingen opgeslagen",
    "Similar Tracks": "Vergelijkbare nummers",
    "The favorites library path changed.\n"
    "Restart the app to load the new library.":
        "Het pad van de favorietenbibliotheek is gewijzigd.\n"
        "Start de app opnieuw om de nieuwe bibliotheek te laden.",
    "Couldn't detect any danceable tracks in that playlist.":
        "Er kon geen dansbaar nummer in die afspeellijst worden herkend.",
    "Import Error": "Importfout",
    "Import M3U": "M3U importeren",
    "Not enough free playlists": "Niet genoeg vrije afspeellijsten",
    "Nothing imported": "Niets geïmporteerd",
    "Remove from the playlist(s) — the slot stays empty (Ctrl+Z undoes)":
        "Uit de afspeellijst(en) verwijderen — de plek blijft leeg (Ctrl+Z maakt het ongedaan)",
    "Drop <b>.m3u playlists</b> here — only playlists carry track paths to fix.":
        "Zet hier <b>.m3u-afspeellijsten</b> neer — alleen afspeellijsten bevatten nummerpaden om te corrigeren.",
    "Fix & overwrite": "Corrigeren & overschrijven",
    "Fix paths": "Paden corrigeren",
    "No track paths that can be re-rooted under the search folders.":
        "Geen nummerpaden die onder de zoekmappen opnieuw te koppelen zijn.",
    "Set a Reference path or a search folder in Settings before fixing dropped playlists.":
        "Stel in Instellingen een referentiepad of een zoekmap in voordat je neergezette afspeellijsten corrigeert.",
    "⚠  No <b>search folder</b> set — open Settings and name the base folder(s) the music lives in on this PC.":
        "⚠  Geen <b>zoekmap</b> ingesteld — open Instellingen en geef de basismap(pen) op waarin de muziek op deze pc staat.",
    "Clear all playlists": "Alle afspeellijsten leegmaken",
    "Nothing to print — no songs found.":
        "Niets af te drukken — geen nummers gevonden.",
    "Print playlist": "Afspeellijst afdrukken",
    "Add folder": "Map toevoegen",
    "No alternative Practice track found.":
        "Geen ander oefennummer gevonden.",
    "No alternative song found.": "Geen ander nummer gevonden.",
    "Re-roll this song — best timbre match first  (Ctrl+R / Ctrl+N)":
        "Dit nummer opnieuw kiezen — beste klankovereenkomst eerst  (Ctrl+R / Ctrl+N)",
    "Swap with a %s from the end of the list — a leftover that fits no round first, else one from the last third  (Ctrl+R / Ctrl+N)":
        "Ruilen met een %s van het einde van de lijst — eerst een restant dat in geen ronde past, anders een uit het laatste derde  (Ctrl+R / Ctrl+N)",
    "↺ click to swap it with a %s from the end of the list":
        "↺ klik om het te ruilen met een %s van het einde van de lijst",
    "↺ click to re-roll a replacement":
        "↺ klik om een vervanger opnieuw te kiezen",
    "🔁 Marked for potential replace  (Ctrl+M to toggle)":
        "🔁 Gemarkeerd voor mogelijke vervanging  (Ctrl+M schakelt om)",
    "⚠ File not found on disk:\n"
    "%s":
        "⚠ Bestand niet gevonden op de schijf:\n"
        "%s",
    "Regenerate": "Opnieuw genereren",
    "Regenerate Error": "Fout bij opnieuw genereren",
    "Track length (m:ss)\n"
    "orange = shorter than the configured play length, or 5 s or more\n"
    "of stillness at an edge that the player skips (the cell's own\n"
    "tooltip says which, and how long it really plays)":
        "Lengte van het nummer (m:ss)\n"
        "oranje = korter dan de ingestelde speelduur, of 5 s of meer\n"
        "stilte aan een rand die de speler overslaat (de tooltip van de\n"
        "cel zegt welke, en hoe lang het echt speelt)",
    "Wishlist": "Wensenlijst",
    "Rating — click a star to set it, the last lit one again to clear it.\n"
    "Kept in the app's database; the MP3 itself is not changed.":
        "Waardering — klik op een ster om die in te stellen, nog eens op de laatste verlichte om ze te wissen.\n"
        "Bewaard in de database van de app; de MP3 zelf wordt niet gewijzigd.",
    "≈  timbral similarity to round anchor\n"
    "    (only shown after running Audio Analysis)\n"
    "[D,C,…]  class tags from MP3 COMM field":
        "≈  klankgelijkenis met het anker van de ronde\n"
        "    (pas zichtbaar na een audioanalyse)\n"
        "[D,C,…]  klassen uit het COMM-veld van de MP3",
    "Audio cache/library not available for this search.":
        "Audiocache/bibliotheek niet beschikbaar voor deze zoekopdracht.",
    "Embedding error": "Embedding-fout",
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
        "Gauss/KL: de MFCC-verdeling per nummer (gemiddelde + covariantie)\n"
        "vergeleken met symmetrische KL — het Mandel-Ellis-model, zoals de oude\n"
        "Java-app. De zuiverste rangorde van klankgenoten; echte treffers scoren ≳ 80 %.\n"
        "Librosa: snelle, met de hand gebouwde vector van klank + ritme (cosinus).\n"
        "OpenL3: een voorgetrainde neurale muziek-embedding — vaak dichter bij het\n"
        "ervaren ‘klinkt hetzelfde’. Vereist:  pip install openl3 tensorflow\n"
        "Chroma cover/remix: vergelijkt MELODIE/harmonie, niet de klank — vindt\n"
        "remixen & covers van hetzelfde stuk, ook met een andere klank,\n"
        "toonsoort of tempo. Alleen librosa; bouw de index één keer, zoals bij de andere.\n"
        "Gecombineerd (standaard): de gemiddelde plaats van een nummer bij Gauss/KL,\n"
        "librosa en chroma — wat alle drie hoog plaatsen, komt eerst.",
    "Off: sound-alike tracks (audio timbre).\n"
    "On: tracks that keep appearing in the same old playlists as this one.":
        "Uit: nummers die hetzelfde klinken (audioklank).\n"
        "Aan: nummers die steeds weer in dezelfde oude afspeellijsten staan als dit nummer.",
    "Replace the duplicate with the selected track (Enter, or double-click a row)":
        "Het duplicaat vervangen door het gekozen nummer (Enter, of dubbelklik op een rij)",
    "Several copies of a song often exist under slightly different names\n"
    "(e.g. '… DJ Ice', 'jive(43) - Bim Bam', '16 Bim Bam'). When on, only the\n"
    "first copy of each song title is shown.":
        "Van een nummer bestaan vaak meerdere kopieën onder licht afwijkende namen\n"
        "(bijv. ‘… DJ Ice’, ‘jive(43) - Bim Bam’, ‘16 Bim Bam’). Als dit aan staat,\n"
        "wordt van elke titel alleen de eerste kopie getoond.",
    "Show only tracks considered instrumental: an explicit 'instr' tag /\n"
    "'(Instr.)' filename marker, a Demucs-measured vocal share (🎙️ Analyze\n"
    "vocals), or the learned audio probability. Unknown tracks count as\n"
    "vocal, so they are hidden while this is on.":
        "Alleen nummers tonen die als instrumentaal gelden: een expliciete ‘instr’-tag /\n"
        "‘(Instr.)’ in de bestandsnaam, een door Demucs gemeten zangaandeel (🎙️ Zang\n"
        "analyseren) of de geleerde audiokans. Onbekende nummers tellen als\n"
        "gezongen en blijven dus verborgen zolang dit aan staat.",
    "Space: play / stop the selected track\n"
    "Ctrl + ← / → : seek 30 s back / forward":
        "Spatie: het gekozen nummer afspelen / stoppen\n"
        "Ctrl + ← / → : 30 s terug / vooruit",
    "This track isn't in any of your old playlists yet — nothing to learn from. Switch the toggle off for sound-alike tracks.":
        "Dit nummer staat nog in geen enkele van je oude afspeellijsten — er valt niets uit te leren. Zet de schakelaar uit voor nummers die hetzelfde klinken.",
    "🧹  Hide duplicate copies (same song, ignoring DJ / dance / BPM tags)":
        "🧹  Dubbele kopieën verbergen (hetzelfde nummer, DJ- / dans- / BPM-tags genegeerd)",
    "Clear playlist": "Afspeellijst leegmaken",
    "Clear wishlist": "Wensenlijst leegmaken",
    "Find in list": "Zoeken in lijst",
    "Find planned before": "Eerder gepland zoeken",
    "Find title:": "Titel zoeken:",
    "No similar tracks found (audio features may be missing).":
        "Geen vergelijkbare nummers gevonden (misschien ontbreken de audiokenmerken).",
    "Select exactly two titles of the same dance to swap them.":
        "Kies precies twee titels van dezelfde dans om ze te ruilen.",
    "Swap titles": "Titels ruilen",
    "Already planned": "Al gepland",
    "Different dance": "Andere dans",
    "Move Error": "Fout bij verplaatsen",
    "Move track": "Nummer verplaatsen",
    "Replace Error": "Fout bij vervangen",
    "Different style": "Andere stijl",
    "Load playlist": "Afspeellijst laden",
    "Name (competition, day, tournament):": "Naam (wedstrijd, dag, toernooi):",
    "New folder": "Nieuwe map",
    "Remove": "Verwijderen",
    "Remove this song from its slot? The slot stays empty.":
        "Dit nummer van zijn plek verwijderen? De plek blijft leeg.",
    "Remove %d songs from their slots? The slots stay empty.":
        "%d nummers van hun plek verwijderen? De plekken blijven leeg.",
    "Remove this song from the running order?":
        "Dit nummer uit de speelvolgorde verwijderen?",
    "Remove %d songs from the running order?":
        "%d nummers uit de speelvolgorde verwijderen?",
    "Rename": "Hernoemen",
    "Songs and total play time of the selected playlist\n"
    "(tracks this library doesn't know count, but add no time)":
        "Nummers en totale speelduur van de gekozen afspeellijst\n"
        "(nummers die deze bibliotheek niet kent tellen mee, maar zonder tijd)",
    "The playlists filed in the selected folder, one slot each.\n"
    "Drag a slot onto a deck to load that round · double-click it to\n"
    "load it onto the focused deck · right-click to rename, remove or\n"
    "read its tracks.":
        "De afspeellijsten in de gekozen map, elk op een eigen plek.\n"
        "Sleep een plek op een deck om die ronde te laden · dubbelklik om\n"
        "hem op het actieve deck te laden · rechtsklik om te hernoemen, te\n"
        "verwijderen of de nummers in te lezen.",
    "The tracks of the selected playlist, in playing order.\n"
    "▶ or Space previews · drag them onto a deck or the player list ·\n"
    "double-click to open in your external player.":
        "De nummers van de gekozen afspeellijst, in speelvolgorde.\n"
        "▶ of Spatie luistert voor · sleep ze op een deck of de spelerlijst ·\n"
        "dubbelklik om ze in je externe speler te openen.",
    "Your competitions, days and tournaments — folders are labels,\n"
    "the 🎵 entries point at .m3u files wherever they lie.\n"
    "\n"
    "Drop .m3u files or a whole folder in from Explorer · pick a folder\n"
    "to lay its playlists out as slots on the right · drag a slot onto\n"
    "a deck to load the round · double-click it to load it onto the\n"
    "focused deck.":
        "Je wedstrijden, dagen en toernooien — mappen zijn alleen labels,\n"
        "de 🎵 items wijzen naar .m3u-bestanden, waar die ook staan.\n"
        "\n"
        "Zet .m3u-bestanden of een hele map neer vanuit Verkenner · kies een map\n"
        "om zijn afspeellijsten rechts als plekken uit te leggen · sleep een plek op\n"
        "een deck om de ronde te laden · dubbelklik om hem op het actieve\n"
        "deck te laden.",
    "📂  (not in a folder)": "📂  (niet in een map)",
    "Party play time, songs at full length with no pause.\n"
    "The count simulates the party generator with your library's\n"
    "track lengths per dance (3.5 min where none are known).":
        "Speelduur van het feest, nummers op volle lengte zonder pauze.\n"
        "De telling bootst de feestgenerator na met de nummerlengtes per dans\n"
        "uit je bibliotheek (3,5 min waar er geen bekend zijn).",
    "Per dance: songs to have ready — enough for 9 of 10 generated lists.":
        "Per dans: nummers om klaar te hebben — genoeg voor 9 van de 10 gegenereerde lijsten.",
    "A key given to a pad follows it wherever it is moved and works\n"
    "from any page. Empty = that pad answers to its slot's key.":
        "Een toets die aan een pad is gegeven, volgt het waarheen het ook wordt\n"
        "verplaatst en werkt vanaf elke pagina. Leeg = het pad luistert naar de toets van zijn plek.",
    "Export cartwall": "Cartwall exporteren",
    "How long a pad takes to let go when it is tapped again\n"
    "or ⏹ stops the wall. A pad can override this in its own settings.":
        "Hoe lang een pad nodig heeft om weg te faden als het opnieuw wordt aangetikt\n"
        "of ⏹ de wand stopt. Een pad kan dit in zijn eigen instellingen overschrijven.",
    "Import cartwall": "Cartwall importeren",
    "Pads per page. Making the grid smaller never loses a pad —\n"
    "whatever no longer fits moves to the first free slot.":
        "Pads per pagina. Een kleiner raster verliest nooit een pad —\n"
        "wat niet meer past, schuift naar de eerste vrije plek.",
    "Page name:": "Paginanaam:",
    "Play this pad over and over until it is stopped —\n"
    "for a background bed under a ceremony.":
        "Dit pad steeds opnieuw afspelen tot het wordt gestopt —\n"
        "als achtergrond onder een ceremonie.",
    "Remove page": "Pagina verwijderen",
    "Rename page": "Pagina hernoemen",
    "Snap the wall back into the main window.\n"
    "It returns to the edge it was last docked at.":
        "De wand terugzetten in het hoofdvenster.\n"
        "Hij keert terug naar de rand waaraan hij het laatst gekoppeld was.",
    "That file is not a cartwall this version can read.":
        "Dat bestand is geen cartwall die deze versie kan lezen.",
    "The key fires whichever pad sits in that slot on the page you are\n"
    "looking at, so the same finger hits the same corner on every page.":
        "De toets activeert het pad dat op die plek ligt op de pagina die je\n"
        "bekijkt, zodat dezelfde vinger op elke pagina dezelfde hoek raakt.",
    "No pause started — enable auto-advance and have a next song queued.":
        "Geen pauze gestart — zet automatisch doorgaan aan en zorg voor een volgend nummer in de wachtrij.",
    "⏹ The playing title is no longer in its deck — the music was stopped.":
        "⏹ Het spelende nummer staat niet meer in zijn deck — de muziek is gestopt.",
    "✏️ Title ended — still loaded for editing; scrub back and ⏯ to listen.":
        "✏️ Nummer afgelopen — nog geladen om te bewerken; spoel terug en ⏯ om te luisteren.",
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
        "Een Paso Doble onder deze schakelaar wordt nooit weggefaded en negeert\n"
        "de speelduur — er wordt op zijn gechoreografeerde hoogtepunten gedanst.\n"
        "De hoogtepunten (crescendo → dramatische val) worden op de achtergrond\n"
        "automatisch herkend en de muziek stopt meteen zodra het\n"
        "gekozen hoogtepunt (zijn slotgong) valt. Een hoogtepunt dat de herkenning\n"
        "niet kan vastpinnen, valt terug op de standaardfrasering\n"
        "(1e ≈ 0:45, 2e ≈ 1:15).\n"
        "\n"
        "Uit is een Paso Doble een gewoon nummer: de speelduur kapt het af\n"
        "en de fade haalt het weg, zoals bij elke andere dans.",
    "Append the heat number (\"…, Heat 3\") — the couples hear which\n"
    "heat they are about to dance.\n"
    "\n"
    "Only a round grid has heats: a theme list, the warm-up and a free\n"
    "running order are announced without one. Recorded for heats 1-8;\n"
    "beyond that the number is left out.":
        "Het heatnummer toevoegen (‘…, Gruppe 3’) — de paren horen in welke\n"
        "heat ze zo gaan dansen.\n"
        "\n"
        "Alleen een rondeschema heeft heats: een themalijst, het oefenen en een vrije\n"
        "speelvolgorde worden zonder aangekondigd. Opgenomen voor heats 1-8;\n"
        "daarboven valt het nummer weg.",
    "Choose one or more titles — or an .m3u playlist — that play\n"
    "softly during the pause between songs, faded in at the start\n"
    "and out before the next song. Several titles rotate: a title\n"
    "keeps playing pause after pause until it ends, then the next\n"
    "one takes over.":
        "Kies een of meer nummers — of een .m3u-afspeellijst — die zacht\n"
        "spelen in de pauze tussen de nummers, aan het begin ingefaded\n"
        "en voor het volgende nummer weggefaded. Meerdere nummers wisselen elkaar af: een nummer\n"
        "speelt pauze na pauze door tot het afgelopen is, dan neemt het\n"
        "volgende het over.",
    "Compensate loudness differences between tracks on playback:\n"
    "each song's measured EBU R128 loudness is pulled towards a common\n"
    "target, so quiet old recordings and loud modern masters play at\n"
    "a similar level. Needs 📊 Analyze loudness (⚙ Settings) first.":
        "Luidheidsverschillen tussen nummers bij het afspelen compenseren:\n"
        "de gemeten EBU R128-luidheid van elk nummer wordt naar een gemeenschappelijk\n"
        "doel getrokken, zodat zachte oude opnames en luide moderne masters op\n"
        "een vergelijkbaar niveau spelen. Vereist eerst 📊 Luidheid analyseren (⚙ Instellingen).",
    "Forget the current track's learned highlights\n"
    "(falls back to 🐂 auto-detection on the next play).":
        "De geleerde hoogtepunten van het huidige nummer vergeten\n"
        "(valt bij het volgende afspelen terug op 🐂 automatische herkenning).",
    "Hold a Paso Doble back this long before the music starts, so the\n"
    "couples reach their position after the dance is called. Applies\n"
    "to every way a PD is started — ▶, a double-click, auto-advance.\n"
    "0 s = start at once, like every other dance.\n"
    "\n"
    "With 🔈 Announce next dance on, the app makes the call and the\n"
    "seconds run from it; off, the hall's announcer does and the wait\n"
    "runs silently — counted down on this panel either way.":
        "Een Paso Doble zo lang tegenhouden voordat de muziek begint, zodat de\n"
        "paren hun positie bereiken nadat de dans is omgeroepen. Geldt\n"
        "voor elke manier waarop een PD start — ▶, een dubbelklik, automatisch doorgaan.\n"
        "0 s = meteen starten, zoals elke andere dans.\n"
        "\n"
        "Met 🔈 Volgende dans aankondigen aan doet de app de omroep en lopen de\n"
        "seconden vanaf daar; uit doet de omroeper in de zaal het en loopt de wachttijd\n"
        "stil — in beide gevallen afgeteld op dit paneel.",
    "How loud the pause music plays, relative to the normal\n"
    "playback volume — kept lower so it stays in the background.":
        "Hoe luid de pauzemuziek speelt, ten opzichte van het normale\n"
        "afspeelvolume — lager gehouden zodat het op de achtergrond blijft.",
    "Keep the screensaver and the display timeout off while music is\n"
    "playing or the presenter screen is open.\n"
    "\n"
    "The system counts idle time from the mouse and the keyboard,\n"
    "never from the speakers — so an hour of music with nobody touching\n"
    "the desk blanks the screen mid-heat, the beamer included. It goes\n"
    "back to its normal timeouts as soon as neither is running.":
        "De schermbeveiliging en het uitschakelen van het scherm tegenhouden zolang er muziek\n"
        "speelt of het presentatiescherm open is.\n"
        "\n"
        "Het systeem telt de inactieve tijd aan muis en toetsenbord,\n"
        "nooit aan de luidsprekers — dus een uur muziek zonder dat iemand de tafel\n"
        "aanraakt, maakt het scherm midden in de heat zwart, de beamer inbegrepen. Het gaat\n"
        "terug naar de normale tijden zodra geen van beide meer loopt.",
    "Off: the next song starts the moment the current one ends, with\n"
    "no filler music and no announcement. The configured time is kept\n"
    "for switching back.\n"
    "\n"
    "Needs ⏭ auto-advance — without it the next song waits for the\n"
    "operator anyway, so there is no gap to fill.":
        "Uit: het volgende nummer begint op het moment dat het huidige eindigt, zonder\n"
        "vulmuziek en zonder aankondiging. De ingestelde tijd blijft bewaard\n"
        "voor als je terugschakelt.\n"
        "\n"
        "Vereist ⏭ automatisch doorgaan — zonder dat wacht het volgende nummer\n"
        "hoe dan ook op de operator, dus er is geen gat te vullen.",
    "On: a double-click in a deck puts the title on the speakers at\n"
    "once — what a party wants.\n"
    "Off: it is only CUED on the player (loaded, shown, silent) and ⏯\n"
    "starts it — what a heat wants, where the music begins when the\n"
    "couples are on the floor and not a moment earlier.\n"
    "\n"
    "Part of the play sets: 🏆 tournament switches it off, 🎉 party on.":
        "Aan: een dubbelklik in een deck zet het nummer meteen op de luidsprekers\n"
        "— wat een feest wil.\n"
        "Uit: het wordt alleen KLAARGEZET op de speler (geladen, getoond, stil) en ⏯\n"
        "start het — wat een heat wil, waar de muziek begint als de\n"
        "paren op de vloer staan en geen moment eerder.\n"
        "\n"
        "Deel van de speelsets: 🏆 toernooi zet het uit, 🎉 feest aan.",
    "On: a double-click in a deck plays the title at once.\n"
    "Off: it is only cued on the player (loaded, shown,\n"
    "silent) and ⏯ starts it — the heat begins when the\n"
    "couples stand.":
        "Aan: een dubbelklik in een deck speelt het nummer meteen.\n"
        "Uit: het wordt alleen klaargezet op de speler (geladen, getoond,\n"
        "stil) en ⏯ start het — de heat begint als de\n"
        "paren staan.",
    "Pitch every title to the mean tempo of its dance in the\n"
    "current round, kept inside the TSO range — what a heat is\n"
    "danced to. Wrong for a party, where the next song is a\n"
    "different dance at whatever tempo it was recorded at.":
        "Elk nummer naar het gemiddelde tempo van zijn dans in de\n"
        "huidige ronde trekken, binnen het TSO-bereik — zo wordt een heat\n"
        "gedanst. Verkeerd voor een feest, waar het volgende nummer een\n"
        "andere dans is in het tempo waarin het is opgenomen.",
    "Open a second, full-screen window showing only the running title\n"
    "with its dance and the next three songs — big and plain, for a\n"
    "beamer or a monitor turned towards the floor. Pick the screen\n"
    "next to it; Esc (or this button) closes it again.":
        "Een tweede venster op volledig scherm openen dat alleen het spelende nummer\n"
        "met zijn dans en de volgende drie nummers toont — groot en eenvoudig, voor een\n"
        "beamer of een monitor die naar de vloer is gedraaid. Kies het scherm\n"
        "ernaast; Esc (of deze knop) sluit het weer.",
    "Pause the music and suspend the highlight stop, so the whole Paso\n"
    "Doble is reachable while you set its marks: scrub to a crash, ⏯ to\n"
    "listen, hit 🎯, delete a wrong mark with its ✕. Marking within 3 s\n"
    "of an existing mark moves that one instead of adding a fourth.\n"
    "\n"
    "Leaving edit mode arms the stop again and PAUSES at it the next\n"
    "time it's reached, so you can hear whether the mark sits right.":
        "De muziek pauzeren en de hoogtepuntstop opschorten, zodat de hele Paso\n"
        "Doble bereikbaar is terwijl je de markeringen zet: spoel naar een klap, ⏯ om te\n"
        "luisteren, druk op 🎯, verwijder een verkeerde markering met haar ✕. Markeren binnen 3 s\n"
        "van een bestaande markering verplaatst die in plaats van een vierde toe te voegen.\n"
        "\n"
        "Bij het verlaten van de bewerkmodus wordt de stop weer ingeschakeld en PAUZEERT de speler daar de volgende\n"
        "keer dat hij wordt bereikt, zodat je hoort of de markering goed zit.",
    "Put the panel back on the competition values in one go: the\n"
    "configured play length, no pause between songs, no auto-advance\n"
    "and no spoken announcement — the settings a heat is run with.\n"
    "\n"
    "Lit gold while the panel stands on those values, the way 🎉 is lit\n"
    "purple during a party. Switches the 🎉 party set off. What exactly\n"
    "it sets is yours to change: ⚙ Settings → 🎛 Play sets.":
        "Het paneel in één keer terugzetten op de wedstrijdwaarden: de\n"
        "ingestelde speelduur, geen pauze tussen nummers, geen automatisch doorgaan\n"
        "en geen gesproken aankondiging — de instellingen waarmee een heat loopt.\n"
        "\n"
        "Goud verlicht zolang het paneel op die waarden staat, zoals 🎉\n"
        "paars oplicht tijdens een feest. Zet de 🎉 feestset uit. Wat het precies\n"
        "instelt, kun je zelf aanpassen: ⚙ Instellingen → 🎛 Speelsets.",
    "Say the next dance out loud shortly before the pause ends\n"
    "(\"Nächster Tanz: Langsamer Walzer\"). Without a pause the dance\n"
    "is named as the title starts instead (\"Langsamer Walzer\") —\n"
    "over the first bars or before them, whichever the pair below\n"
    "is set to.":
        "De volgende dans hardop zeggen kort voordat de pauze eindigt\n"
        "(‘Nächster Tanz: Langsamer Walzer’). Zonder pauze wordt de dans\n"
        "genoemd als het nummer begint (‘Langsamer Walzer’) —\n"
        "over de eerste maten of ervoor, afhankelijk van hoe het paar hieronder\n"
        "is ingesteld.",
    "The dance is named while the music is already running, ducked\n"
    "under the voice — the hall hears both at once and the title\n"
    "loses none of its first bars.\n"
    "\n"
    "Applies where a title names its dance as it starts: 🔈 Announce\n"
    "next dance on, and no pause between songs (a pause has a gap of\n"
    "its own for the call).":
        "De dans wordt genoemd terwijl de muziek al loopt, zachter gezet\n"
        "onder de stem — de zaal hoort beide tegelijk en het nummer\n"
        "verliest geen van zijn eerste maten.\n"
        "\n"
        "Geldt waar een nummer zijn dans bij de start noemt: 🔈 Volgende\n"
        "dans aankondigen aan, en geen pauze tussen nummers (een pauze heeft een eigen\n"
        "gat voor de omroep).",
    "The dance is called into silence and the music follows when the\n"
    "voice is done — the hall hears WHICH dance before it starts, at\n"
    "the cost of a second or two of quiet.\n"
    "\n"
    "Applies where a title names its dance as it starts: 🔈 Announce\n"
    "next dance on, and no pause between songs (a pause has a gap of\n"
    "its own for the call).":
        "De dans wordt in de stilte omgeroepen en de muziek volgt als de\n"
        "stem klaar is — de zaal hoort WELKE dans er komt voordat hij begint, ten koste\n"
        "van een seconde of twee stilte.\n"
        "\n"
        "Geldt waar een nummer zijn dans bij de start noemt: 🔈 Volgende\n"
        "dans aankondigen aan, en geen pauze tussen nummers (een pauze heeft een eigen\n"
        "gat voor de omroep).",
    "Show a cover picture next to the title on the player.\n"
    "The playlist's own image is used when it has one (an #EXTIMG line\n"
    "in the .m3u or a cover file beside it), otherwise the track's\n"
    "embedded artwork, otherwise a plain ♪ tile.":
        "Een hoesafbeelding naast de titel op de speler tonen.\n"
        "De eigen afbeelding van de afspeellijst wordt gebruikt als die er een heeft (een #EXTIMG-regel\n"
        "in de .m3u of een hoesbestand ernaast), anders de ingesloten\n"
        "afbeelding van het nummer, anders een eenvoudige ♪-tegel.",
    "Speak a sample announcement now — check voice and level\n"
    "before the round, not during it.":
        "Nu een voorbeeldaankondiging uitspreken — controleer stem en niveau\n"
        "vóór de ronde, niet tijdens.",
    "Switch the tournament settings over to party playing in one go:\n"
    "every title to its full length, auto-advance to the next one, no\n"
    "pause (so no break music) in between and no spoken announcement.\n"
    "\n"
    "Applied by itself as soon as you play from the 🤸 Practice /\n"
    "party list, and switched back when a tournament deck takes over —\n"
    "a toast says what changed either way. What exactly it sets is\n"
    "yours to change: ⚙ Settings → 🎛 Play sets.":
        "De toernooi-instellingen in één keer omzetten naar feestgebruik:\n"
        "elk nummer op volle lengte, automatisch door naar het volgende, geen\n"
        "pauze (dus geen pauzemuziek) ertussen en geen gesproken aankondiging.\n"
        "\n"
        "Wordt vanzelf toegepast zodra je speelt uit de 🤸 oefen- /\n"
        "feestlijst, en teruggezet als een toernooideck het overneemt —\n"
        "een melding zegt in beide gevallen wat er is veranderd. Wat het precies instelt,\n"
        "kun je zelf aanpassen: ⚙ Instellingen → 🎛 Speelsets.",
    "The colours of the presenter screen. 'Default' is the black hall\n"
    "display; 'Light' is creme paper with warm brown type and rose\n"
    "gold for the next dance — made for a lit room, where black on a\n"
    "beamer is just a grey rectangle. Applies straight away.":
        "De kleuren van het presentatiescherm. ‘Default’ is het zwarte\n"
        "zaalscherm; ‘Light’ is crèmekleurig papier met warmbruine letters en\n"
        "roségoud voor de volgende dans — gemaakt voor een verlichte ruimte, waar zwart op een\n"
        "beamer slechts een grijze rechthoek is. Werkt meteen.",
    "The evening's running order — when dinner is, when the opening\n"
    "dance is — as a second page on the presenter screen.\n"
    "\n"
    "Type it here; on the screen itself, T (or its 🕒 button) switches\n"
    "to it, and it can fade between the two pages by itself.":
        "Het programma van de avond — wanneer het diner is, wanneer de openings-\n"
        "dans is — als tweede pagina op het presentatiescherm.\n"
        "\n"
        "Typ het hier; op het scherm zelf schakelt T (of zijn 🕒-knop) ernaartoe,\n"
        "en het kan vanzelf tussen de twee pagina’s overvloeien.",
    "There is one player for every deck, so leaving a title to hear\n"
    "another one loses your place in it. On: the spot a title stopped\n"
    "at is kept and it starts there again — marked by a tick on the\n"
    "seek bar and by ↩ mm:ss on its row.\n"
    "\n"
    "A title played to its end keeps no mark, and the marks are\n"
    "forgotten when the app closes.":
        "Er is één speler voor alle decks, dus wie een nummer verlaat om een\n"
        "ander te horen, raakt zijn plek erin kwijt. Aan: de plek waar een nummer stopte,\n"
        "wordt bewaard en het begint daar opnieuw — gemarkeerd met een streepje op de\n"
        "zoekbalk en met ↩ mm:ss in zijn rij.\n"
        "\n"
        "Een nummer dat tot het einde is gespeeld, houdt geen markering, en de markeringen worden\n"
        "vergeten als de app sluit.",
    "Time for the couples to change / catch breath before the next song":
        "Tijd voor de paren om te wisselen / op adem te komen voor het volgende nummer",
    "Volume ramps to 0 over the last N seconds,\n"
    "in steps of half a second":
        "Het volume zakt in de laatste N seconden naar 0,\n"
        "in stappen van een halve seconde",
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
        "Als een nummer eindigt (fade-out of natuurlijk einde), de\n"
        "ingestelde tijd pauzeren en dan de volgende nummerrij van het deck spelen —\n"
        "zodat een hele ronde zonder handwerk doorloopt. Stopt aan het einde\n"
        "van de ronde (🏁) — de volgende ronde wordt met de hand gestart.\n"
        "\n"
        "Uitschakelen stopt ook 🔈 Volgende dans aankondigen: niets\n"
        "mag een dans omroepen die daarna niet speelt. Weer\n"
        "inschakelen herstelt de aankondiging die je had.\n"
        "\n"
        "Elke afspeellijst houdt haar eigen antwoord: dit is dat van de\n"
        "laatst aangeklikte lijst, hetzelfde als ⏭/✋ onder dat deck.",
    "✋  Manual": "✋  Handmatig",
    "Auto: a finished song is followed by the next row of the deck, so\n"
    "a whole round runs hands-free.\n"
    "Manual: every song is started by the operator, and 🔈 Announce\n"
    "next dance stops with it — back on Auto it returns.\n"
    "\n"
    "This playlist's own answer, remembered for it: the party list can\n"
    "run hands-free while the round next to it is started by hand.\n"
    "⏭ Auto-advance on the play panel is the same answer while this\n"
    "list is the one last clicked.":
        "Automatisch: op een afgelopen nummer volgt de volgende rij van het deck, zodat\n"
        "een hele ronde zonder handwerk doorloopt.\n"
        "Handmatig: elk nummer wordt door de operator gestart, en 🔈 Volgende\n"
        "dans aankondigen stopt mee — terug op Automatisch komt het terug.\n"
        "\n"
        "Het eigen antwoord van deze afspeellijst, voor haar onthouden: de feestlijst kan\n"
        "zonder handwerk lopen terwijl de ronde ernaast met de hand wordt gestart.\n"
        "⏭ Automatisch doorgaan op het speelpaneel is hetzelfde antwoord zolang deze\n"
        "lijst de laatst aangeklikte is.",
    "Manual: every song is started by the operator, and 🔈 Announce\n"
    "next dance is off with it.\n"
    "Auto: a finished song is followed by the next row of the deck, so\n"
    "a whole round runs hands-free — and the announcement returns.\n"
    "\n"
    "This playlist's own answer, remembered for it: the party list can\n"
    "run hands-free while the round next to it is started by hand.\n"
    "⏭ Auto-advance on the play panel is the same answer while this\n"
    "list is the one last clicked.":
        "Handmatig: elk nummer wordt door de operator gestart, en 🔈 Volgende\n"
        "dans aankondigen staat mee uit.\n"
        "Automatisch: op een afgelopen nummer volgt de volgende rij van het deck, zodat\n"
        "een hele ronde zonder handwerk doorloopt — en de aankondiging komt terug.\n"
        "\n"
        "Het eigen antwoord van deze afspeellijst, voor haar onthouden: de feestlijst kan\n"
        "zonder handwerk lopen terwijl de ronde ernaast met de hand wordt gestart.\n"
        "⏭ Automatisch doorgaan op het speelpaneel is hetzelfde antwoord zolang deze\n"
        "lijst de laatst aangeklikte is.",
    "When the LAST title of the list has finished, carry on with its\n"
    "first one instead of stopping — so a party keeps its music going\n"
    "without anybody at the desk.\n"
    "\n"
    "The 🏁 end of a round is untouched: that one happens between\n"
    "rounds, and still waits for the operator.\n"
    "\n"
    "Needs ⏭ auto-advance.":
        "Als het LAATSTE nummer van de lijst is afgelopen, doorgaan met het\n"
        "eerste in plaats van te stoppen — zo houdt een feest zijn muziek gaande\n"
        "zonder dat iemand aan de tafel staat.\n"
        "\n"
        "Het 🏁 einde van een ronde blijft onaangeroerd: dat ligt tussen\n"
        "rondes en wacht nog steeds op de operator.\n"
        "\n"
        "Vereist ⏭ automatisch doorgaan.",
    "Which highlight ends the Paso Doble — usually the 2nd,\n"
    "in rare cases the 3rd.":
        "Welk hoogtepunt de Paso Doble beëindigt — meestal het 2e,\n"
        "in zeldzame gevallen het 3e.",
    "Which monitor the presenter screen fills. Same screen as the app\n"
    "is fine too — double-click the presenter window to shrink it back\n"
    "out of full screen.":
        "Welke monitor het presentatiescherm vult. Hetzelfde scherm als de app\n"
        "kan ook — dubbelklik op het presentatievenster om het weer\n"
        "uit volledig scherm te halen.",
    "Which recorded voice announces the dance. “Mixed” alternates them\n"
    "— she, he, she, he — so an evening doesn't run on a single voice.\n"
    "\n"
    "A dance that was never recorded is not announced.":
        "Welke opgenomen stem de dans aankondigt. ‘Gemengd’ wisselt ze af\n"
        "— zij, hij, zij, hij — zodat een avond niet op één stem draait.\n"
        "\n"
        "Een dans die nooit is opgenomen, wordt niet aangekondigd.",
    "While a Paso Doble plays, click exactly when a highlight (the\n"
    "dramatic gong / drop) hits to teach its position. Click again at\n"
    "the 2nd / 3rd highlight. Manually learned highlights are flagged\n"
    "in the database and are never overwritten by 🐂 auto-detection.":
        "Klik, terwijl een Paso Doble speelt, precies wanneer een hoogtepunt (de\n"
        "dramatische gong / val) valt om zijn positie te leren. Klik opnieuw bij\n"
        "het 2e / 3e hoogtepunt. Handmatig geleerde hoogtepunten worden gemarkeerd\n"
        "in de database en nooit overschreven door 🐂 automatische herkenning.",
    "Adjusted play length (timed play / Paso Doble highlight stop)\n"
    "next to the track's full length":
        "Aangepaste speelduur (getimed spelen / hoogtepuntstop van de Paso Doble)\n"
        "naast de volle lengte van het nummer",
    "Auto-equalize the heat tempo (toggle):\n"
    "while on, every title is pitched to the average tempo of its\n"
    "dance in this round, kept inside the TSO range (e.g. a Rumba\n"
    "at 23 → T24, a Paso Doble at 57 → T58).":
        "Het heattempo automatisch gelijktrekken (schakelaar):\n"
        "zolang aan, wordt elk nummer naar het gemiddelde tempo van zijn\n"
        "dans in deze ronde getrokken, binnen het TSO-bereik (bijv. een Rumba\n"
        "op 23 → T24, een Paso Doble op 57 → T58).",
    "Disable preview player  (re-enable in Settings)":
        "Voorluisterspeler uitschakelen  (weer aan te zetten in Instellingen)",
    "Duck to 20 % / back to full — the filler music comes down too":
        "Dempen tot 20 % / terug naar vol — de vulmuziek gaat mee omlaag",
    "Endless repeat of THIS title (toggle):\n"
    "while on, the running title starts again every time it ends —\n"
    "for the moment the floor is still full or the speech runs long.\n"
    "\n"
    "It holds the evening on one title, so it beats the 🏁 end of a\n"
    "round and works with ⏭ auto-advance off too. Switch it off and\n"
    "the list carries on where it stands.":
        "Eindeloos herhalen van DIT nummer (schakelaar):\n"
        "zolang aan, begint het spelende nummer opnieuw elke keer dat het eindigt —\n"
        "voor het moment dat de vloer nog vol is of de toespraak uitloopt.\n"
        "\n"
        "Het houdt de avond op één nummer, gaat dus boven het 🏁 einde van een\n"
        "ronde en werkt ook met ⏭ automatisch doorgaan uit. Zet het uit en\n"
        "de lijst gaat verder waar ze staat.",
    "Extend the auto-advance pause (add another pause length) —\n"
    "use it when the heat change is taking longer than planned.":
        "De pauze van automatisch doorgaan verlengen (nog een pauzelengte toevoegen) —\n"
        "gebruik het als de heatwissel langer duurt dan gepland.",
    "Fade the music out and HOLD it there (over the fade time).\n"
    "Nothing ends and nothing advances — ⏯ resumes at exactly the\n"
    "spot it went quiet. For an announcement or an incident on the floor.":
        "De muziek wegfaden en daar VASTHOUDEN (over de fadetijd).\n"
        "Niets eindigt en niets gaat door — ⏯ gaat verder op precies de\n"
        "plek waar het stil werd. Voor een mededeling of een incident op de vloer.",
    "Fade this song out now (over the configured fade time), then end it\n"
    "— for a quick, clean finish on the floor.":
        "Dit nummer nu wegfaden (over de ingestelde fadetijd) en het dan beëindigen\n"
        "— voor een snel, net einde op de vloer.",
    "Jump straight to the pause music — end this song now and start\n"
    "the between-songs pause (e.g. the dancers are already leaving).":
        "Meteen naar de pauzemuziek springen — dit nummer nu beëindigen en\n"
        "de pauze tussen de nummers starten (bijv. de dansers verlaten de vloer al).",
    "Tap along to the beat to measure this track's live tempo by hand,\n"
    "against a target for its dance (Sollwert) — display only, does not\n"
    "touch the fader.":
        "Tik mee op de beat om het werkelijke tempo van dit nummer met de hand te meten,\n"
        "tegen een streefwaarde voor zijn dans (Sollwert) — alleen weergave, de\n"
        "fader wordt niet aangeraakt.",
    "Tempo −16 % … +16 % without changing the pitch (time stretch) —\n"
    "e.g. to pull a track onto the takt the tournament needs.\n"
    "Stays set across tracks; a double-click on the fader (or the\n"
    "button below) resets it.":
        "Tempo −16 % … +16 % zonder de toonhoogte te veranderen (time stretch) —\n"
        "bijv. om een nummer op de maat te trekken die het toernooi nodig heeft.\n"
        "Blijft ingesteld over nummers heen; een dubbelklik op de fader (of de\n"
        "knop eronder) zet hem terug.",
    "📌 Pin the tempo: the fader stays where you left it when the next\n"
    "title starts.\n"
    "Off: every new title begins at ±0 %.\n"
    "Switching TSO on takes the pin off — TSO pitches each title itself.":
        "📌 Het tempo vastzetten: de fader blijft waar je hem liet als het volgende\n"
        "nummer begint.\n"
        "Uit: elk nieuw nummer begint op ±0 %.\n"
        "TSO aanzetten haalt de vastzetting weg — TSO stelt elk nummer zelf bij.",
    "Off, the running order goes by this machine's clock.\n"
    "\n"
    "On, it goes by the time you set here — from the moment you save,\n"
    "and running on from there. An evening half an hour behind stays\n"
    "half an hour behind; the screen does not stand still.\n"
    "\n"
    "This is not saved with the programme: the next start of the app\n"
    "is back on the machine's clock.":
        "Uit volgt het programma de klok van deze computer.\n"
        "\n"
        "Aan volgt het de tijd die je hier instelt — vanaf het moment dat je opslaat,\n"
        "en vanaf daar doorlopend. Een avond die een half uur achterloopt, blijft\n"
        "een half uur achter; het scherm staat niet stil.\n"
        "\n"
        "Dit wordt niet met het programma opgeslagen: bij de volgende start van de app\n"
        "geldt weer de klok van de computer.",
    "Off, the screen stays on whichever page you picked (T on the\n"
    "presenter screen, or its 🕒 button, switches by hand).\n"
    "\n"
    "On, it fades from one to the other by itself — so the hall sees\n"
    "both without anybody at the desk touching anything.":
        "Uit blijft het scherm op de pagina die je koos (T op het\n"
        "presentatiescherm, of zijn 🕒-knop, schakelt met de hand).\n"
        "\n"
        "Aan vloeit het vanzelf van de een naar de ander over — zo ziet de zaal\n"
        "beide zonder dat iemand aan de tafel iets aanraakt.",
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
        "Wat het presentatiescherm op zijn tweede pagina toont — het\n"
        "programma van de avond. De regel die de klok heeft bereikt, wordt gemarkeerd,\n"
        "de regels ervoor worden grijs.\n"
        "\n"
        "Een tijd mag alles zijn wat je op een programma zou schrijven; alleen echte\n"
        "kloktijden (20:30, 20.30) doen mee aan de markering.\n"
        "\n"
        "‘Tot’ is optioneel en laat het ene punt het andere omvatten: geef\n"
        "het feest 19:00–01:00 en de openingsdans 19:30–19:50, en als\n"
        "de dans voorbij is, gaat de markering terug naar het feest. Ofwel een\n"
        "eindtijd (01:00) of een lengte in minuten (20).",
    "Dance": "Dans",
    "Title": "Titel",
    "📋  Path copied to clipboard": "📋  Pad naar het klembord gekopieerd",
    "Artist": "Artiest",
    "🏷 MP3 tag": "🏷 MP3-tag",
    "🔬 Measured": "🔬 Gemeten",
    "🔀  Shared between playlists": "🔀  Gedeeld tussen afspeellijsten",
    "Action": "Actie",
    "Nothing usable — the decks were left alone.":
        "Niets bruikbaars — de decks zijn ongemoeid gelaten.",
    "Issue(s)": "Probleem/problemen",
    "Remove song": "Nummer verwijderen",
    "Remove dance": "Dans verwijderen",
    " tracks": " nummers",
    "In your own words — what this list is for (optional):":
        "In je eigen woorden — waar deze lijst voor is (optioneel):",
    "Rules the model has to follow:":
        "Regels waaraan het model zich moet houden:",
    "Claude login:": "Claude-aanmelding:",
    "📝  Details copied to clipboard":
        "📝  Details naar het klembord gekopieerd",
    "Mode:": "Modus:",
    "Favorites": "Favorieten",
    "Theme": "Thema",
    "Past Competitions": "Eerdere wedstrijden",
    "Draw tracks from:": "Nummers nemen uit:",
    "Dance Style:": "Dansstijl:",
    "Age Class:": "Leeftijdsklasse:",
    "Start Class:": "Startklasse:",
    "Dances:": "Dansen:",
    "Rounds  (e.g. 6-3-2-1):": "Rondes  (bijv. 6-3-2-1):",
    "Paste competition schedule:": "Wedstrijdschema plakken:",
    "Competition:": "Wedstrijd:",
    "Seeds the grid from songs you played at this\n"
    "class before (matching per-class M3U files).":
        "Vult het raster met nummers die je eerder in deze\n"
        "klasse hebt gedraaid (passende M3U-bestanden per klasse).",
    "Theme:": "Thema:",
    "Number of tracks:": "Aantal nummers:",
    "Themes use ID3 year tags + themes.json overrides.\n"
    "Decade themes need year data in your MP3s.":
        "Thema’s gebruiken ID3-jaartags + overschrijvingen in themes.json.\n"
        "Decenniumthema’s hebben jaargegevens in je MP3’s nodig.",
    "⏱  Too short — at or below:": "⏱  Te kort — gelijk aan of onder:",
    "The cut must cover the 1:30–1:45 TSO play time; default 1:45.":
        "De knip moet de TSO-speelduur van 1:30–1:45 dekken; standaard 1:45.",
    "⏳  Too long — above:": "⏳  Te lang — boven:",
    "Only flagged when the ⏳ checkbox in the Music-check window is on (Practice playlists); default 4:00.":
        "Alleen gemeld als het vakje ⏳ in het muziekcontrolevenster aan staat (oefenafspeellijsten); standaard 4:00.",
    "⚡  Tempo mismatch — deviation above:":
        "⚡  Tempo wijkt af — afwijking boven:",
    "Measured tempo vs the filename label (detector ×2, ×3, ×1.5 … slips are excused first); default 10 %.":
        "Gemeten tempo tegen het label in de bestandsnaam (uitschieters van de detector ×2, ×3, ×1,5 … worden eerst vergeven); standaard 10 %.",
    "🔇  Hiss — noise floor above:": "🔇  Ruis — ruisvloer boven:",
    "How quiet a track must get somewhere. A clean file reaches its lead-in silence, a tape rip never gets below its own hiss; default −50 dB. Only flagged when the 🔇 checkbox in the Music-check window is on.":
        "Hoe stil een nummer ergens moet worden. Een schoon bestand bereikt zijn stilte vóór de inzet, een bandopname komt nooit onder zijn eigen ruis; standaard −50 dB. Alleen gemeld als het vakje 🔇 in het muziekcontrolevenster aan staat.",
    "📄 File name": "📄 Bestandsnaam",
    "Source": "Bron",
    "Speed": "Snelheid",
    "— (no BPM tag)": "— (geen BPM-tag)",
    "— (not measured)": "— (niet gemeten)",
    "🔁  Doubled inside one playlist": "🔁  Dubbel in één afspeellijst",
    "File": "Bestand",
    "📌  Reference base (single .m3u)": "📌  Referentiebasis (één .m3u)",
    "🎯  Tournament files (compared against)":
        "🎯  Toernooibestanden (waarmee vergeleken wordt)",
    "🔁  Doubled inside a playlist": "🔁  Dubbel in een afspeellijst",
    "Added": "Toegevoegd",
    "Last": "Laatst",
    "Build all caches — librosa…": "Alle caches opbouwen — librosa…",
    "Analyzing audio (timbre)…": "Audio analyseren (klank)…",
    "Audio analysis": "Audioanalyse",
    "Measuring loudness (EBU R128)…": "Luidheid meten (EBU R128)…",
    "Loudness analysis": "Luidheidsanalyse",
    "Probing silent stretches…": "Stille stukken controleren…",
    "Silence probe": "Stiltecontrole",
    "Separating vocals (Demucs)…": "Zang scheiden (Demucs)…",
    "Vocal separation": "Zangscheiding",
    "Detecting Paso Doble highlights…":
        "Hoogtepunten van de Paso Doble herkennen…",
    "PD highlight detection": "Herkenning van PD-hoogtepunten",
    "✅  No other open playlist to compare against":
        "✅  Geen andere open afspeellijst om mee te vergelijken",
    "✅  Nothing here is in another open playlist":
        "✅  Niets hiervan staat in een andere open afspeellijst",
    "Remove duplicates": "Duplicaten verwijderen",
    "🌐  Whole repository — every file under your music repo (global search).\n"
    "🎯  Favorites library — just your tanzcds folder.\n"
    "➕  Both — the repository and the favorites library.":
        "🌐  Hele repository — elk bestand onder je muziekrepository (globaal zoeken).\n"
        "🎯  Favorietenbibliotheek — alleen je tanzcds-map.\n"
        "➕  Beide — de repository en de favorietenbibliotheek.",
    "Standard dances": "Standaarddansen",
    "Latin dances": "Latijnse dansen",
    "Interleave short social-dance rounds — needs those tracks in your library.":
        "Korte rondes sociale dansen tussenvoegen — vereist die nummers in je bibliotheek.",
    "No Paso Doble": "Geen Paso Doble",
    "Start with a Latin round": "Met een Latijnse ronde beginnen",
    "Late Wiener Walzer (hold back early / not back-to-back)":
        "Weense wals laat (vroeg achterhouden / niet direct na elkaar)",
    "Late Paso Doble (not in the first ~40 songs)":
        "Paso Doble laat (niet in de eerste ~40 nummers)",
    "Failed — nothing was changed.": "Mislukt — er is niets gewijzigd.",
    "♻️  Restoring your last session…": "♻️  Je laatste sessie herstellen…",
    "Indexing whole repository…": "Hele repository indexeren…",
    "Build / refresh librosa audio index":
        "librosa-audio-index opbouwen / vernieuwen",
    "Scanning repository…": "Repository doorzoeken…",
    "Cleaning up database…": "Database opruimen…",
    "Re-learning playlist popularity…":
        "Populariteit van afspeellijsten opnieuw leren…",
    "Loading repository from cache…": "Repository uit de cache laden…",
    "🔊 Audio backend": "🔊 Audio-backend",
    "The audio backend is chosen when the app starts, so the new one takes over after a restart.\n"
    "\n"
    "Restart now?":
        "De audio-backend wordt bij het starten van de app gekozen, dus de nieuwe werkt pas na een herstart.\n"
        "\n"
        "Nu opnieuw starten?",
    "The theme, the accent colour and the language are applied while the app starts, so they take over after a restart.\n"
    "\n"
    "Restart now?":
        "Het uiterlijk, de accentkleur en de taal worden bij het starten van de app toegepast, dus ze werken pas na een herstart.\n"
        "\n"
        "Nu opnieuw starten?",
    "📂  Nothing new — all tracks already in the wishlist":
        "📂  Niets nieuws — alle nummers staan al op de wensenlijst",
    "Length": "Lengte",
    "Drag <b>.m3u playlists</b> (or audio files) here to check their tracks for the same issues — tempo label vs measured, TSO takt range, play length — plus the playlists' round structure (heat tempo spread).":
        "Sleep hier <b>.m3u-afspeellijsten</b> (of audiobestanden) naartoe om hun nummers op dezelfde problemen te controleren — tempolabel tegen meting, TSO-maatbereik, speelduur — plus de rondeopbouw van de afspeellijsten (tempospreiding per heat).",
    "Drag <b>.m3u playlists</b> here to check their track paths against the <b>search folders</b> (Settings). Broken references <b>and valid paths on a different root</b> (e.g. C:) that can be re-rooted there are listed per playlist; <b>🧭 Fix &amp; overwrite</b> rewrites those path lines <b>in place</b> — only the file path changes, every #EXTINF / comment line is kept exactly as-is.":
        "Sleep hier <b>.m3u-afspeellijsten</b> naartoe om hun nummerpaden te controleren tegen de <b>zoekmappen</b> (Instellingen). Kapotte verwijzingen <b>en geldige paden op een andere schijf</b> (bijv. C:) die daar opnieuw gekoppeld kunnen worden, worden per afspeellijst getoond; <b>🧭 Corrigeren &amp; overschrijven</b> herschrijft die padregels <b>ter plekke</b> — alleen het bestandspad verandert, elke #EXTINF- / commentaarregel blijft precies zoals ze is.",
    "↶  Nothing to undo": "↶  Niets om ongedaan te maken",
    "↷  Nothing to redo": "↷  Niets om opnieuw te doen",
    "✅  No wishlist tracks are in an open playlist":
        "✅  Geen nummers van de wensenlijst staan in een open afspeellijst",
    "🔁  Cleared all replacement marks": "🔁  Alle vervangmarkeringen gewist",
    "✅  Kept all titles": "✅  Alle titels behouden",
    "✅  No duplicate titles in this list":
        "✅  Geen dubbele titels in deze lijst",
    "Already in the list — nothing added":
        "Staat al in de lijst — niets toegevoegd",
    "⭐  Already in the wishlist — nothing added":
        "⭐  Staat al op de wensenlijst — niets toegevoegd",
    "Replace the existing track with this one?":
        "Het bestaande nummer door dit nummer vervangen?",
    "Remove heat": "Heat verwijderen",
    "Remove round": "Ronde verwijderen",
    "Remove backup": "Reserve verwijderen",
    "Remove this backup song?": "Dit reservenummer verwijderen?",
    "⬆  Backup moved up into the empty slot":
        "⬆  Reserve is naar de lege plek opgeschoven",
    "Couldn't read the dropped track(s).":
        "De neergezette nummers konden niet worden gelezen.",
    "📊 Loudness probe failed": "📊 Luidheidsmeting mislukt",
    "🔇 Silence probe failed": "🔇 Stiltecontrole mislukt",
    "Slot defaults — apply to every page":
        "Standaardwaarden voor plekken — gelden voor elke pagina",
    "Pad keys — travel with the pad": "Padtoetsen — reizen mee met het pad",
    "🔈  announcing…": "🔈  aankondigen…",
    "🛑  held": "🛑  vastgehouden",
    "🐂  detecting highlights…": "🐂  hoogtepunten herkennen…",
    "🐂  plays to the end": "🐂  speelt tot het einde",
    "🎯  stop reached — ⏯ to go on": "🎯  stop bereikt — ⏯ om door te gaan",
    "🐂  Stop Paso Doble after highlight":
        "🐂  Paso Doble stoppen na hoogtepunt",
    "⏭  Auto-advance to next song": "⏭  Automatisch naar het volgende nummer",
    "over the first bars": "over de eerste maten",
    "before the music starts": "voordat de muziek begint",
    "⏸  No pause between songs": "⏸  Geen pauze tussen nummers",
    "🔁  Start again at the end": "🔁  Aan het einde opnieuw beginnen",
    "Pause between songs:": "Pauze tussen nummers:",
    "🔈  Announce next dance": "🔈  Volgende dans aankondigen",
    "…with heat": "…met heat",
    "🔊  Equalize volume (R128)": "🔊  Volume gelijktrekken (R128)",
    "🖼  Show artwork": "🖼  Hoes tonen",
    "〰  Show waveform": "〰  Golfvorm tonen",
    "Draw the playing title's waveform above the seek bar: quiet\n"
    "passages, the skipped silence, the Paso Doble highlights and\n"
    "where the fade-out of a timed cut begins. Click it to jump.":
        "De golfvorm van het spelende nummer boven de zoekbalk tekenen: stille\n"
        "passages, de overgeslagen stilte, de hoogtepunten van de Paso Doble en\n"
        "waar de fade-out van een getimede knip begint. Klik om te springen.",
    "…replace seek bar": "…zoekbalk vervangen",
    "Hide the seek bar while the waveform is shown — the waveform\n"
    "covers the same stretch of the title and seeks on a click.":
        "De zoekbalk verbergen zolang de golfvorm zichtbaar is — de golfvorm\n"
        "dekt hetzelfde stuk van het nummer en springt met een klik.",
    "The waveform of the title — what has played is blue, all of it\n"
    "red in the final seconds. The broad orange bar is where it plays.\n"
    "Shaded: silence the player skips · thin orange: Paso Doble\n"
    "highlights · red-tinted: the fade-out of a timed cut.\n"
    "Click to jump there.":
        "De golfvorm van het nummer — wat al gespeeld is, is blauw, in de\n"
        "laatste seconden alles rood. De brede oranje balk is waar het speelt.\n"
        "Gearceerd: stilte die de speler overslaat · dun oranje: hoogtepunten\n"
        "van de Paso Doble · roodachtig: de fade-out van een getimede knip.\n"
        "Klik om daarheen te springen.",
    "▶️  Double-click starts the title": "▶️  Dubbelklik start het nummer",
    "🎚  TSO pitch to the heat tempo": "🎚  TSO: naar het heattempo trekken",
    "↩  Remember where a title stopped": "↩  Onthouden waar een nummer stopte",
    "☀  Keep the screen awake": "☀  Het scherm wakker houden",
    "Show the transport on this screen": "De bediening op dit scherm tonen",
    "Show the title played before this one": "Het vorige nummer tonen",
    "Show the timetable  ·  T\n"
    "Right-click to edit it":
        "Het tijdschema tonen  ·  T\n"
        "Rechtsklik om het te bewerken",
    "Close the presenter screen": "Het presentatiescherm sluiten",
    "Previous title": "Vorig nummer",
    "Play / pause": "Afspelen / pauze",
    "Next title": "Volgend nummer",
    "Over to the break music": "Naar de pauzemuziek",
    "Time": "Tijd",
    "Until": "Tot",
    "What": "Wat",
    "Note": "Notitie",
    "♪ Takt meter": "♪ Maatmeter",
    "Takt count:": "Getelde maten:",
    "Target:": "Streefwaarde:",
    " Takt/min": " maten/min",
    "Correction needed:": "Benodigde correctie:",
    "Apply": "Toepassen",
    "Apply this correction to the tempo fader.":
        "Deze correctie op de tempofader toepassen.",
    "Next dances": "Volgende dansen",
    "⌨  Keyboard": "⌨  Toetsenbord",
    "Space": "Spatie",
    "Play / stop the selected song": "Het gekozen nummer afspelen / stoppen",
    "Seek 30 s back / forward while playing":
        "Tijdens het afspelen 30 s terug / vooruit springen",
    "Previous / next title — same as ⏮ / ⏭ on the player (⏭ also ends a running pause)":
        "Vorig / volgend nummer — hetzelfde als ⏮ / ⏭ op de speler (⏭ beëindigt ook een lopende pauze)",
    "Ctrl + R  or  Ctrl + N": "Ctrl + R  of  Ctrl + N",
    "Re-roll (regenerate) the selected song":
        "Het gekozen nummer opnieuw kiezen (opnieuw genereren)",
    "Save the focused playlist / wishlist as M3U":
        "De actieve afspeellijst / wensenlijst als M3U opslaan",
    "Save the whole session state (decks, wishlists, layout)":
        "De hele sessiestatus opslaan (decks, wensenlijsten, indeling)",
    "Undo / redo (also Ctrl + Shift + Z)":
        "Ongedaan maken / opnieuw (ook Ctrl + Shift + Z)",
    "Ctrl + X  or  Ctrl + W": "Ctrl + X  of  Ctrl + W",
    "Close the active dialog or the preview mini player":
        "Het actieve dialoogvenster of de mini-voorluisterspeler sluiten",
    "Remove the selected rows (wishlist) / empty the selected heat slots (deck)":
        "De gekozen rijen verwijderen (wensenlijst) / de gekozen heatplekken leegmaken (deck)",
    "Del  with nothing selected": "Del  zonder selectie",
    "Clear that whole playlist / wishlist (confirmed) — same when every song is selected at once":
        "Die hele afspeellijst / wensenlijst leegmaken (met bevestiging) — hetzelfde als alle nummers tegelijk zijn gekozen",
    "Clear the focused playlist / wishlist (confirmed), wherever the cursor is":
        "De actieve afspeellijst / wensenlijst leegmaken (met bevestiging), waar de cursor ook staat",
    "Dynamic deck: remove the whole heat under the cursor (on a ↳ backup row: just that backup)":
        "Dynamisch deck: de hele heat onder de cursor verwijderen (op een ↳ reserverij: alleen die reserve)",
    "Dynamic deck or free running order: mark / unmark the selected song(s) for potential replace (❗ orange). Ctrl + 1 does the same, but only while the 🎛 cartwall is hidden — the wall claims that key for its first pad":
        "Dynamisch deck of vrije speelvolgorde: de gekozen nummers markeren / ontmarkeren voor mogelijke vervanging (❗ oranje). Ctrl + 1 doet hetzelfde, maar alleen zolang de 🎛 cartwall verborgen is — de wand neemt die toets voor zijn eerste pad",
    "F2  in the 📅 tournament tree": "F2  in de 📅 toernooiboom",
    "Rename the entry under the cursor (Del removes it)":
        "Het item onder de cursor hernoemen (Del verwijdert het)",
    "Ctrl + A  in 🏆 Tournaments": "Ctrl + A  in 🏆 Toernooien",
    "Mark every slot of the folder, or every entry of the tree — Del and a drag then take them all":
        "Elke plek van de map markeren, of elk item van de boom — Del en slepen nemen ze dan allemaal mee",
    "Click a star in the ★ column": "Klik op een ster in de kolom ★",
    "Rate the title; click the star the rating ends on to clear it":
        "Het nummer waarderen; klik op de ster waar de waardering eindigt om ze te wissen",
    "Find a title in the focused list (repeat to step to the next match)":
        "Een titel zoeken in de actieve lijst (herhaal om naar de volgende treffer te gaan)",
    "Esc  in the 🖥 presenter window": "Esc  in het 🖥 presentatievenster",
    "This cheat sheet": "Dit overzicht",
    "Fullscreen on / off — with date and time in the status bar":
        "Volledig scherm aan / uit — met datum en tijd in de statusbalk",
    "🖱  Mouse": "🖱  Muis",
    "Click a round / dance header": "Klik op een ronde- / danskop",
    "Collapse or expand that section": "Die sectie in- of uitklappen",
    "Double-click a deck title": "Dubbelklik op een decknaam",
    "Rename the playlist / wishlist":
        "De afspeellijst / wensenlijst hernoemen",
    "▾ / ▸ arrow in a deck header": "Pijl ▾ / ▸ in een deckkop",
    "Fold the deck to a header tab (click the tab to reopen)":
        "Het deck inklappen tot een koptab (klik op de tab om het weer te openen)",
    "Drag a row": "Een rij slepen",
    "Move a song to another slot, deck, wishlist — or drop it into Explorer / UltraMixer":
        "Een nummer naar een andere plek, ander deck of wensenlijst verplaatsen — of het in Verkenner / UltraMixer neerzetten",
    "Drag a dance header": "Een danskop slepen",
    "Reorder the dance columns of a static deck":
        "De danskolommen van een statisch deck herschikken",
    "Right-click ▸ 🔍 Find a title": "Rechtsklik ▸ 🔍 Titel zoeken",
    "Jump to a song by name; repeat to step to the next match":
        "Op naam naar een nummer springen; herhaal om naar de volgende treffer te gaan",
    "Ctrl + drag onto a filled slot": "Ctrl + slepen naar een gevulde plek",
    "Dynamic deck: replace the song in that slot with the dragged one":
        "Dynamisch deck: het nummer op die plek vervangen door het gesleepte",
    "Drop a file from outside": "Een bestand van buiten neerzetten",
    "Replace a slot / add to a wishlist (.m3u on a deck imports it)":
        "Een plek vervangen / aan een wensenlijst toevoegen (een .m3u op een deck importeert hem)",
    "▶ or Space on a 📚 library row":
        "▶ of Spatie op een rij van de 📚 bibliotheek",
    "Preview that track in the mini player":
        "Dat nummer voorbeluisteren in de minispeler",
    "Double-click a 📚 library row":
        "Dubbelklik op een rij van de 📚 bibliotheek",
    "Open the track in your external audio player":
        "Het nummer openen in je externe audiospeler",
    "▶ / ■ in a row": "▶ / ■ in een rij",
    "Play / stop exactly that song": "Precies dat nummer afspelen / stoppen",
    "↺ in a row / header": "↺ in een rij / kop",
    "Re-roll that song / every song of the dance or round":
        "Dat nummer opnieuw kiezen / elk nummer van de dans of de ronde",
    "Drop files on a pad": "Bestanden op een pad neerzetten",
    "Assign that sample — a multi-select fills the free pads after it (an empty pad can also be clicked to browse)":
        "Dat sample toewijzen — een meervoudige selectie vult de vrije pads erna (op een leeg pad kun je ook klikken om te bladeren)",
    "Click a pad": "Klik op een pad",
    "Fire it over the running music; click again to fade it out":
        "Het over de lopende muziek afvuren; nog eens klikken om het weg te faden",
    "Fire the first nine pads of the page on screen (works from anywhere while the wall is shown, and takes Ctrl + 1 away from the mark shortcut above)":
        "De eerste negen pads van de getoonde pagina afvuren (werkt overal zolang de wand zichtbaar is, en neemt Ctrl + 1 af van de markeersneltoets hierboven)",
    "Right-click a pad": "Rechtsklik op een pad",
    "🎨 colour straight away, or Settings… for label, volume, its own key, 🔁 endless repeat and whether it ducks the music":
        "🎨 meteen een kleur, of Instellingen… voor label, volume, een eigen toets, 🔁 eindeloos herhalen en of het de muziek dempt",
    "Drag a pad onto another": "Een pad op een ander slepen",
    "Swap the two pads": "De twee pads ruilen",
    "Stop every pad (same as ⏹ Stop all)":
        "Alle pads stoppen (hetzelfde als ⏹ Alles stoppen)",
    "⚙  Settings…": "⚙  Instellingen…",
    "🎨  Colour": "🎨  Kleur",
    "🗑  Clear pad": "🗑  Pad leegmaken",
    "Wall default": "Standaard van de cartwall",
    "Grey": "Grijs",
    "Green": "Groen",
    "Red": "Rood",
    "Olive": "Olijf",
    "Purple": "Paars",
    "White": "Wit",
    "📂  Show in Explorer (not saved as a file yet)":
        "📂  Tonen in Verkenner (nog niet als bestand opgeslagen)",
    "Unfold this wishlist": "Deze wensenlijst uitklappen",
    "Fold to a tab": "Inklappen tot een tab",
    "🔁  Mark for potential replace\tCtrl+M":
        "🔁  Markeren voor mogelijke vervanging\tCtrl+M",
    "🔁  Unmark (potential replace)\tCtrl+M":
        "🔁  Markering weghalen (mogelijke vervanging)\tCtrl+M",
    "➕  Create new round": "➕  Nieuwe ronde aanmaken",
    "➕  Insert new round after %s": "➕  Nieuwe ronde invoegen na %s",
    "🗑  Remove %s from this round (keep other dances)":
        "🗑  %s uit deze ronde verwijderen (andere dansen blijven)",
    "🗑  Remove %s from all rounds and heats":
        "🗑  %s uit alle rondes en heats verwijderen",
    "🔒  Back to a planned grid": "🔒  Terug naar een gepland raster",
    "🔒  Switch to static mode": "🔒  Naar de statische modus",
    "🔓  Switch to dynamic mode": "🔓  Naar de dynamische modus",
    "🧹  Empty this wishlist": "🧹  Deze wensenlijst leegmaken",
    "Columns in every playlist": "Kolommen in elke afspeellijst",
    "Columns in every wishlist": "Kolommen in elke wensenlijst",
    "Columns in every party list": "Kolommen in elke feestlijst",
    "Σ  %d song": "Σ  %d nummer",
    "Σ  %d songs": "Σ  %d nummers",
    "other": "ander",
    "✦new": "✦nieuw",
    "new": "nieuw",
    "Round": "Ronde",
    "Female": "Vrouwelijk",
    "Male": "Mannelijk",
    "Mixed": "Gemengd",
    "🎉  Party check": "🎉  Feestcontrole",
    "Check the party list — rounds, the late WW / PD rules,\n"
    "duplicates, takt and over-long titles.":
        "De feestlijst controleren — rondes, de regels ‘Weense wals laat’ / ‘Paso Doble laat’,\n"
        "dubbele nummers, maat en te lange titels.",
    "Party list": "Feestlijst",
    "🎉 <b>%s</b> — %d titles, 1 finding":
        "🎉 <b>%s</b> — %d titels, 1 bevinding",
    "🎉 <b>%s</b> — %d titles, %d findings":
        "🎉 <b>%s</b> — %d titels, %d bevindingen",
    "✅  Nothing to report — the list reads like one the party builder would have made.":
        "✅  Niets te melden — de lijst leest als een die de feestgenerator gemaakt zou hebben.",
    "↻  Check again": "↻  Opnieuw controleren",
    "🔁 Rounds": "🔁 Rondes",
    "⏳ Spacing": "⏳ Afstanden",
    "👯 Duplicates": "👯 Dubbele",
    "⏱ Length": "⏱ Lengte",
    "row %d": "rij %d",
    "Standard rounds": "Standaardrondes",
    "Latin rounds": "Latijnse rondes",
    "Social rounds": "Sociale rondes",
    "“%s” is %d title long, not 3 — from ":
        "‘%s’ is %d titel lang, geen 3 — vanaf ",
    "“%s” is %d titles long, not 3 — from ":
        "‘%s’ is %d titels lang, geen 3 — vanaf ",
    "a round": "een ronde",
    "the Samba plays two %s running, the second at ":
        "de Samba speelt in twee %s achter elkaar, de tweede op ",
    "“%s” opens the section with %s, not %s — from ":
        "‘%s’ opent de sectie met %s, niet met %s — vanaf ",
    "nothing": "niets",
    "two %s run back to back — “%s” starts at ":
        "twee %s direct na elkaar — ‘%s’ begint op ",
    ", with no round of the other section between them.":
        ", zonder een ronde van de andere sectie ertussen.",
    "the %s never plays — %d %s and not one of them.":
        "de %s speelt nooit — %d %s en in geen enkele.",
    "the %s sits out %d %s running, from ":
        "de %s slaat %d %s achter elkaar over, vanaf ",
    "the Wiener Walzer opens the evening at ":
        "de Wiener Walzer opent de avond op ",
    " — “late WW” holds it back until %d titles have played.":
        " — ‘Weense wals laat’ houdt hem tegen tot er %d titels gespeeld zijn.",
    "a Paso Doble plays at ": "een Paso Doble speelt op ",
    " — “late PD” holds the first one back until %d titles have played.":
        " — ‘Paso Doble laat’ houdt de eerste tegen tot er %d titels gespeeld zijn.",
    "two Paso Dobles sit %d Latin round apart, the second at ":
        "twee Paso Dobles liggen %d Latijnse ronde uit elkaar, de tweede op ",
    "two Paso Dobles sit %d Latin rounds apart, the second at ":
        "twee Paso Dobles liggen %d Latijnse rondes uit elkaar, de tweede op ",
    " — the rule is %d.": " — de regel is %d.",
    "“%s” plays %d times, at ": "‘%s’ speelt %d keer, op ",
    "“%s” and “%s” look like the same song, at ":
        "‘%s’ en ‘%s’ lijken hetzelfde nummer, op ",
    "“%s” is a %s at T%d, outside T%d–T%d — ":
        "‘%s’ is een %s op T%d, buiten T%d–T%d — ",
    "“%s” runs %d:%02d, past %d:%02d — ":
        "‘%s’ duurt %d:%02d, langer dan %d:%02d — ",
    "Class %s": "Klasse %s",
    "★ Rarely (1–%d)": "★ Zelden (1–%d)",
    "★ Proven (≥%d)": "★ Beproefd (≥%d)",
    "Filter by how the track was used so far:\n"
    "✦ never — in none of your playlists\n"
    "★ rarely / proven — in 1–%d vs. %d+ of them\n"
    "📅 not since — played, but the newest playlist\n"
    "carrying it is that old (the year comes from the\n"
    "playlist's path; undated lists don't count as old).":
        "Filteren op hoe het nummer tot nu toe gebruikt is:\n"
        "✦ nooit — in geen van je afspeellijsten\n"
        "★ zelden / beproefd — in 1–%d tegen %d+ ervan\n"
        "📅 niet sinds — gespeeld, maar de nieuwste afspeellijst\n"
        "met het nummer is zo oud (het jaar komt uit het\n"
        "pad van de afspeellijst; lijsten zonder datum tellen niet als oud).",
    "🎄 Seasonal / Christmas": "🎄 Seizoen / Kerst",
    "🎺 Anthems": "🎺 Volksliederen",
    "🎶 Background / non-dance": "🎶 Achtergrond / geen dans",
    "⏱️ Wrong tempo / not tournament": "⏱️ Verkeerd tempo / geen toernooi",
    "👥 Duplicates / raw versions": "👥 Dubbele / ruwe versies",
    "(%d/%d tracks)": "(%d/%d nummers)",
    "▶  Play": "▶  Afspelen",
    "⏱  Length": "⏱  Lengte",
    "★  Rating": "★  Waardering",
    "Class tags from the MP3 comment field":
        "Klassetags uit het commentaarveld van de MP3",
    "Newest playlist carrying this track":
        "Nieuwste afspeellijst met dit nummer",
    "Never played": "Nooit gespeeld",
    "Played, but none of those playlists is dated":
        "Gespeeld, maar geen van die afspeellijsten heeft een datum",
    "⚡ Light — librosa/ffmpeg, works in every install (lite build)":
        "⚡ Licht — librosa/ffmpeg, werkt in elke installatie (lite-build)",
    "⚡ Light — ffmpeg, works in every install (player build)":
        "⚡ Licht — ffmpeg, werkt in elke installatie (speler-build)",
    "🔬  Analyze audio (timbre) — %d files to do":
        "🔬  Audio analyseren (klank) — nog %d bestanden",
    "🔬  Re-analyze audio (timbre)  ✓ all cached":
        "🔬  Audio opnieuw analyseren (klank)  ✓ alles in de cache",
    "🎚️  librosa indexed": "🎚️  librosa geïndexeerd",
    "🎼  Chroma indexed": "🎼  Chroma geïndexeerd",
    "📊  Loudness measured": "📊  Luidheid gemeten",
    "🐂  PD highlights detected": "🐂  PD-hoogtepunten herkend",
    "🔇  Silences probed": "🔇  Stiltes gecontroleerd",
    "🧠  OpenL3 indexed": "🧠  OpenL3 geïndexeerd",
    "🧠  OpenL3 'sounds-alike' index": "🧠  OpenL3-index ‘klinkt hetzelfde’",
    "🎙️  Analyze vocals (Demucs)…": "🎙️  Zang analyseren (Demucs)…",
    "  – not installed": "  – niet geïnstalleerd",
    "The values a heat is run with — pressed to get back to them after a party list has pulled the panel somewhere else.":
        "De waarden waarmee een heat speelt — druk erop om ze terug te halen nadat een feestlijst het paneel ergens anders heen heeft getrokken.",
    "Applied by itself as soon as you play from the 🤸 Practice / party list, and switched back when a tournament deck takes over.":
        "Wordt vanzelf toegepast zodra je uit de 🤸 oefen- / feestlijst speelt, en teruggezet als een toernooideck het overneemt.",
    "An onboard sound card un-mutes its output stage the moment an app\n"
    "opens it, and the amplifier carries that hiss across the hall — you\n"
    "hear it start with the app and stop when it closes, whether or not\n"
    "anything is playing.\n"
    "\n"
    "Handing the device back after %.0f s of silence takes it away. The cost is the soft click the card makes re-opening it\n"
    "for the next title, so only switch this on if you hear the hiss.":
        "Een ingebouwde geluidskaart zet de demping van zijn uitgangstrap uit op het moment\n"
        "dat een app hem opent, en de versterker draagt die ruis door de hele zaal — je\n"
        "hoort hem beginnen met de app en stoppen als die sluit, of er nu iets speelt of niet.\n"
        "\n"
        "Het apparaat na %.0f s stilte teruggeven haalt hem weg. De prijs is de zachte klik die de kaart maakt als hij opnieuw opent\n"
        "voor de volgende titel, dus zet dit alleen aan als je de ruis hoort.",
    "⚠️  Not read — %s": "⚠️  Niet gelezen — %s",
    "🧹  Removed %d title already in another playlist":
        "🧹  %d titel verwijderd die al in een andere afspeellijst stond",
    "🧹  Removed %d titles already in another playlist":
        "🧹  %d titels verwijderd die al in een andere afspeellijst stonden",
    "🔁  Replaced %d duplicate": "🔁  %d dubbel nummer vervangen",
    "🔁  Replaced %d duplicates": "🔁  %d dubbele nummers vervangen",
    "⚠  %d duplicate was no longer in its playlist — left as it is":
        "⚠  %d dubbel nummer stond niet meer in zijn afspeellijst — gelaten zoals het is",
    "⚠  %d duplicates were no longer in their playlist — left as they are":
        "⚠  %d dubbele nummers stonden niet meer in hun afspeellijst — gelaten zoals ze zijn",
    "💾  Saved → %s": "💾  Opgeslagen → %s",
    "💾  Saved %d competition playlist(s)":
        "💾  %d wedstrijdafspeellijst(en) opgeslagen",
    "📅  Planned %d competition(s) into %d deck(s)":
        "📅  %d wedstrijd(en) in %d deck(s) gepland",
    "📂  Added %d track(s) from %d file(s)":
        "📂  %d nummer(s) uit %d bestand(en) toegevoegd",
    "📂  Imported %d playlists into %d free slot(s)":
        "📂  %d afspeellijsten in %d vrije plek(ken) geïmporteerd",
    "%d extra final-round track(s) kept as backups (stacked under their dance)":
        "%d extra finalenummer(s) als reserve bewaard (onder hun dans gestapeld)",
    "%s line(s) name a file the list already had (imported again, not skipped)":
        "%s regel(s) noemen een bestand dat de lijst al had (opnieuw geïmporteerd, niet overgeslagen)",
    "%s file(s) not found on disk":
        "%s bestand(en) niet op de schijf gevonden",
    "%s track(s) with no recognizable dance (skipped)":
        "%s nummer(s) zonder herkenbare dans (overgeslagen)",
    "%s track(s) left out — no round/dance column to put them in":
        "%s nummer(s) weggelaten — geen ronde-/danskolom om ze in te zetten",
    "%s of %s songs": "%s van %s nummers",
    "%s songs": "%s nummers",
    "📂 Imported %s · %d round(s) · %d dance(s) (markers)":
        "📂 %s geïmporteerd · %d ronde(s) · %d dans(en) (markeringen)",
    "📂 Imported %s · %d round(s) · %d dance(s) (auto-detected)":
        "📂 %s geïmporteerd · %d ronde(s) · %d dans(en) (automatisch herkend)",
    "📂 Imported %s · %d round(s)": "📂 %s geïmporteerd · %d ronde(s)",
    "⚠ %d row(s) marked red — play-length / takt issues (hover a red title for details)":
        "⚠ %d rij(en) rood gemarkeerd — problemen met speelduur / maat (houd de muis op een rode titel voor details)",
    "🏷  %s is not on disk any more": "🏷  %s staat niet meer op de schijf",
    "🏷  Couldn't re-read %s: %s": "🏷  %s kon niet opnieuw gelezen worden: %s",
    "★  Couldn't store the rating: %s":
        "★  De waardering kon niet opgeslagen worden: %s",
    "🏷  Couldn't store the tags: %s":
        "🏷  De tags konden niet opgeslagen worden: %s",
    "🏷  Edit tags…": "🏷  Tags bewerken…",
    "🏷  Edit tags of %d tracks…": "🏷  Tags van %d nummers bewerken…",
    "🏷  Edit tags": "🏷  Tags bewerken",
    "🏷  Edit tags of %d tracks": "🏷  Tags van %d nummers bewerken",
    "%d tracks — a field they differ in is kept per track until you change it.":
        "%d nummers — een veld waarin ze verschillen, blijft per nummer behouden tot je het wijzigt.",
    "keep (differs per track)": "behouden (verschilt per nummer)",
    "no stars": "geen sterren",
    "Stars:": "Sterren:",
    "Classes:": "Klassen:",
    "None ticked = suits every class.":
        "Niets aangevinkt = past bij elke klasse.",
    "Instrumental (no vocals)": "Instrumentaal (zonder zang)",
    "differs per track — typing here replaces them all":
        "verschilt per nummer — hier typen vervangt ze allemaal",
    "e.g. classic, vocal_f": "bijv. classic, vocal_f",
    "Markers:": "Markeringen:",
    "Add this marker, or take it out again":
        "Deze markering toevoegen, of weer weghalen",
    "↺  Back to the file's tags": "↺  Terug naar de tags van het bestand",
    "Forget every change made here in the app — stars, classes,\n"
    "instrumental, markers and Custom read from the MP3 again.":
        "Elke wijziging die hier in de app is gemaakt vergeten — sterren, klassen,\n"
        "instrumentaal, markeringen en Custom worden opnieuw uit de MP3 gelezen.",
    "Filled from the MP3 tag %s. What is typed here wins over it.":
        "Gevuld uit de MP3-tag %s. Wat hier getypt wordt, gaat voor.",
    "Kept in the app only. Right-click a column header to fill it from an MP3 tag.":
        "Alleen in de app bewaard. Rechtsklik op een kolomkop om hem uit een MP3-tag te vullen.",
    "Changed in the Custom field on the first tab":
        "Wordt gewijzigd in het veld Custom op de eerste tab",
    "Map Custom to an MP3 tag…": "Custom aan een MP3-tag koppelen…",
    "🏷  Custom field": "🏷  Veld Custom",
    "🏷  Fill Custom from this tag": "🏷  Custom uit deze tag vullen",
    "In none of the %d sampled MP3s": "In geen van de %d bekeken MP3’s",
    "In %d of %d sampled MP3s, e.g. “%s”":
        "In %d van %d bekeken MP3’s, bijv. ‘%s’",
    "The Custom column shows this tag of each MP3. A value typed in the 🏷 editor wins over it, and on Save it can be written into it.":
        "De kolom Custom toont deze tag van elke MP3. Een waarde getypt in de 🏷-editor gaat voor en kan bij Opslaan erin geschreven worden.",
    "In the app only": "Alleen in de app",
    "Description:": "Beschrijving:",
    "e.g. ultramixer_last_played": "bijv. ultramixer_last_played",
    "Custom — a free field per track, typed in the 🏷 editor.\n"
    "Right-click the header to fill it from an MP3 tag.":
        "Custom — een vrij veld per nummer, getypt in de 🏷-editor.\n"
        "Rechtsklik op de kop om het uit een MP3-tag te vullen.",
    "Custom goes into the tag it is mapped to.":
        "Custom gaat naar de tag waaraan het gekoppeld is.",
    "Extended tags": "Uitgebreide tags",
    "Every frame of the MP3, written straight into the file on Save. The fields of the form on the first tab are changed there.":
        "Elk frame van de MP3, bij Opslaan direct in het bestand geschreven. De velden van het formulier op de eerste tab worden daar gewijzigd.",
    "Changed in the form on the first tab":
        "Wordt gewijzigd in het formulier op de eerste tab",
    "In the MP3 file": "In het MP3-bestand",
    "In the app": "In de app",
    "Only for MP3 files on disk": "Alleen voor MP3-bestanden op de schijf",
    "Covers differ": "Hoezen verschillen",
    "Cover can't be shown": "Hoes kan niet getoond worden",
    "No cover": "Geen hoes",
    "< keep >": "< behouden >",
    "< blank >": "< leeg >",
    "Title:": "Titel:",
    "Artist:": "Artiest:",
    "Year:": "Jaar:",
    "Comment:": "Commentaar:",
    "Album artist:": "Albumartiest:",
    "Composer:": "Componist:",
    "Disc number:": "Schijfnummer:",
    "Description": "Beschrijving",
    "Value": "Waarde",
    "➕  Add field": "➕  Veld toevoegen",
    "Only for one track at a time": "Alleen voor één nummer tegelijk",
    "Only for an MP3 file on disk": "Alleen voor een MP3-bestand op de schijf",
    "Couldn't read the MP3 tags: %s":
        "De MP3-tags konden niet gelezen worden: %s",
    "Can only be removed, not edited here":
        "Kan hier alleen verwijderd worden, niet bewerkt",
    "🏷  %s is in the player — stop it to write its MP3 tags":
        "🏷  %s staat in de speler — stop het om de MP3-tags te schrijven",
    "🏷  Couldn't write the MP3 tags: %s":
        "🏷  De MP3-tags konden niet geschreven worden: %s",
    "🏷  Write into the MP3?": "🏷  In de MP3 schrijven?",
    "Also write %s into the MP3 file?": "%s ook in het MP3-bestand schrijven?",
    "Also write %s into the %d MP3 files?":
        "%s ook in de %d MP3-bestanden schrijven?",
    "Stars go into the Windows rating; classes, instrumental and markers into the comment, where other programs see them too. With No they stay in the app only.":
        "Sterren gaan naar de Windows-waardering; klassen, instrumentaal en markeringen naar het commentaar, waar andere programma’s ze ook zien. Met Nee blijven ze alleen in de app.",
    "stars": "sterren",
    "custom": "Custom",
    "Custom text": "Eigen tekst",
    "Comment": "Commentaar",
    "Custom link": "Eigen link",
    "Rating": "Waardering",
    "Picture": "Afbeelding",
    "Private data": "Privégegevens",
    "Embedded object": "Ingesloten object",
    "CD identifier": "Cd-kenmerk",
    "Unique file id": "Unieke bestands-id",
    "Lyrics": "Songtekst",
    "Play count": "Aantal keer afgespeeld",
    "Volume adjustment": "Volumeaanpassing",
    "Grouping": "Groepering",
    "Subtitle": "Ondertitel",
    "Album artist": "Albumartiest",
    "Conductor": "Dirigent",
    "Remixed by": "Geremixt door",
    "Key": "Toonsoort",
    "Composer": "Componist",
    "Lyricist": "Tekstschrijver",
    "Track number": "Tracknummer",
    "Disc number": "Schijfnummer",
    "Year": "Jaar",
    "Recording date": "Opnamedatum",
    "Publisher": "Uitgever",
    "Language": "Taal",
    "Length (ms)": "Lengte (ms)",
    "Encoded by": "Gecodeerd door",
    "Encoder settings": "Encoderinstellingen",
    "Media type": "Mediatype",
    "Grouping (iTunes)": "Groepering (iTunes)",
    "🏷  %s: tags unchanged": "🏷  %s: tags ongewijzigd",
    "⚠  Track no longer in any open deck":
        "⚠  Het nummer staat in geen enkel open deck meer",
    "🗑  Removed “%s” from 1 slot — Ctrl+Z undoes":
        "🗑  ‘%s’ uit 1 plek verwijderd — Ctrl+Z maakt het ongedaan",
    "🗑  Removed “%s” from %d slots — Ctrl+Z undoes":
        "🗑  ‘%s’ uit %d plekken verwijderd — Ctrl+Z maakt het ongedaan",
    "↺  Replaced “%s” with “%s” in 1 slot — Ctrl+Z undoes":
        "↺  ‘%s’ vervangen door ‘%s’ op 1 plek — Ctrl+Z maakt het ongedaan",
    "↺  Replaced “%s” with “%s” in %d slots — Ctrl+Z undoes":
        "↺  ‘%s’ vervangen door ‘%s’ op %d plekken — Ctrl+Z maakt het ongedaan",
    "🧭  Fixed %d track path": "🧭  %d nummerpad gecorrigeerd",
    "🧭  Fixed %d track paths": "🧭  %d nummerpaden gecorrigeerd",
    "🧭  Moved %d track onto the Reference path":
        "🧭  %d nummer naar het referentiepad verplaatst",
    "🧭  Moved %d tracks onto the Reference path":
        "🧭  %d nummers naar het referentiepad verplaatst",
    "No tracks in the visible playlists or the wishlists.":
        "Geen nummers in de zichtbare afspeellijsten of de wensenlijsten.",
    "Checked %d tracks — %d already valid.":
        "%d nummers gecontroleerd — %d al geldig.",
    "🧭  Relocated %d broken reference to their real files (Ctrl+Z undoes).":
        "🧭  %d kapotte verwijzing naar het echte bestand omgezet (Ctrl+Z maakt het ongedaan).",
    "🧭  Relocated %d broken references to their real files (Ctrl+Z undoes).":
        "🧭  %d kapotte verwijzingen naar de echte bestanden omgezet (Ctrl+Z maakt het ongedaan).",
    "⚠  %d still unresolved — no matching file in the library:":
        "⚠  %d nog onopgelost — geen passend bestand in de bibliotheek:",
    "⚠  %d valid track is not on the Reference path %s":
        "⚠  %d geldig nummer staat niet in het referentiepad %s",
    "⚠  %d valid tracks are not on the Reference path %s":
        "⚠  %d geldige nummers staan niet in het referentiepad %s",
    "↪ %d has a copy there — 🧭 Fix swaps them in the playlists.":
        "↪ %d heeft daar een kopie — 🧭 Herstellen wisselt ze in de afspeellijsten.",
    "↪ %d have a copy there — 🧭 Fix swaps them in the playlists.":
        "↪ %d hebben daar een kopie — 🧭 Herstellen wisselt ze in de afspeellijsten.",
    "⚠ %d has no copy there:":
        "⚠ %d heeft daar geen kopie:",
    "⚠ %d have no copy there:":
        "⚠ %d hebben daar geen kopie:",
    "✅  All track paths are valid.":
        "✅  Alle nummerpaden zijn geldig.",
    "🎛  Re-pointed %d cartwall pad at its real sample.":
        "🎛  %d Cartwall-Pad wijst weer naar zijn echte sample.",
    "🎛  Re-pointed %d cartwall pads at their real samples.":
        "🎛  %d Cartwall-Pads wijzen weer naar hun echte samples.",
    "🧭  Fixed 1 path in 1 file": "🧭  1 pad in 1 bestand gecorrigeerd",
    "🧭  Fixed %d paths in 1 file": "🧭  %d paden in 1 bestand gecorrigeerd",
    "🧭  Fixed %d paths in %d files":
        "🧭  %d paden in %d bestanden gecorrigeerd",
    "🧹  Removed %d track(s) already in a playlist":
        "🧹  %d nummer(s) verwijderd die al in een afspeellijst stonden",
    "↺  No other %s near the end of the list":
        "↺  Geen andere %s aan het eind van de lijst",
    "🔍  No title matching “%s”": "🔍  Geen titel past bij ‘%s’",
    "🔁  Marked %d track for replace":
        "🔁  %d nummer gemarkeerd om te vervangen",
    "🔁  Marked %d tracks for replace":
        "🔁  %d nummers gemarkeerd om te vervangen",
    "🔁  Unmarked %d track": "🔁  Markering van %d nummer verwijderd",
    "🔁  Unmarked %d tracks": "🔁  Markering van %d nummers verwijderd",
    "📌  Pin — keep this title when the round is re-rolled":
        "📌  Vastzetten — deze titel houden als de ronde opnieuw geloot wordt",
    "📌  Unpin": "📌  Losmaken",
    "📌  Pinned — unpin the title to re-roll it":
        "📌  Vastgezet — maak de titel los om hem opnieuw te loten",
    "📌  Pinned %d title — the round's ↻ keeps it":
        "📌  %d titel vastgezet — de ↻ van de ronde houdt hem",
    "📌  Pinned %d titles — the round's ↻ keeps them":
        "📌  %d titels vastgezet — de ↻ van de ronde houdt ze",
    "📌  Unpinned %d title": "📌  %d titel losgemaakt",
    "📌  Unpinned %d titles": "📌  %d titels losgemaakt",
    "🚦  Check ▾": "🚦  Controle ▾",
    "🚦 Ready? — the pre-flight before the event, one traffic light per\n"
    "check: missing files, loudness, silence probe, Paso Doble highlights,\n"
    "duplicates and the music check, each with its fix.\n"
    "The menu also opens 🔁 Check duplicates, 🎵 Check music and\n"
    "🧭 Fix paths on their own.":
        "🚦 Klaar? — de controle vóór het evenement, één verkeerslicht per\n"
        "controle: ontbrekende bestanden, luidheid, stiltecontrole, Paso Doble-\n"
        "hoogtepunten, dubbele en de muziekcontrole, elk met de oplossing.\n"
        "Het menu opent ook 🔁 Dubbelen controleren, 🎵 Muziek controleren en\n"
        "🧭 Paden herstellen afzonderlijk.",
    "🚦  Ready?": "🚦  Klaar?",
    "Pre-flight before the event, one traffic light per check — over every\n"
    "deck that holds titles and the Practice list, each with its fix.\n"
    "A heading in the report opens its full tool.":
        "Controle vóór het evenement, één verkeerslicht per controle — over elk\n"
        "deck met titels en de oefenlijst, elk met de oplossing.\n"
        "Een kop in het rapport opent het volledige hulpmiddel.",
    "No tempo, length or round-structure problem in the decks.":
        "Geen probleem met tempo, lengte of rondeopbouw in de decks.",
    "%d titles with a tempo or length problem: %s":
        "%d titels met een tempo- of lengteprobleem: %s",
    "%d playlists with uneven rounds or heats: %s":
        "%d afspeellijsten met ongelijke rondes of heats: %s",
    "🎵  Show the report…": "🎵  Rapport tonen…",
    "Click the heading to open the full tool.":
        "Klik op de kop om het volledige hulpmiddel te openen.",
    "🚦  Ready for the event?": "🚦  Klaar voor het evenement?",
    "🟢  Ready — every check is green.": "🟢  Klaar — elke controle is groen.",
    "🟡  Playable, with loose ends.": "🟡  Speelbaar, met losse eindjes.",
    "🔴  Not ready — some titles will not play.":
        "🔴  Niet klaar — sommige titels zullen niet spelen.",
    "🧭  Fix paths…": "🧭  Paden repareren…",
    "📊  Measure loudness…": "📊  Luidheid meten…",
    "🐂  Find highlights…": "🐂  Hoogtepunten zoeken…",
    "🔁  Resolve duplicates…": "🔁  Dubbele oplossen…",
    "📁  Music files": "📁  Muziekbestanden",
    "Every title is where the list says.":
        "Elke titel staat waar de lijst zegt.",
    "%d titles are not on the Reference path.":
        "%d titels staan niet op het referentiepad.",
    "%d have a copy there — 🧭 Fix paths swaps them in.":
        "%d hebben daar een kopie — 🧭 Paden herstellen wisselt ze in.",
    "%d have no copy there: %s": "%d hebben daar geen kopie: %s",
    "Drive %s is not connected — %d titles live there.":
        "Schijf %s is niet aangesloten — daar staan %d titels.",
    "%d titles not found: %s": "%d titels niet gevonden: %s",
    "🎶  Playlists": "🎶  Afspeellijsten",
    "Nothing to play yet — load or build a playlist first.":
        "Nog niets te spelen — laad of maak eerst een afspeellijst.",
    "📊  Loudness": "📊  Luidheid",
    "Every title is measured — 🔊 Equalize volume can stay on.":
        "Elke titel is gemeten — 🔊 Volume gelijktrekken kan aan blijven.",
    "%d of %d titles have no loudness measurement — 🔊 Equalize volume stays off.":
        "%d van %d titels hebben geen luidheidsmeting — 🔊 Volume gelijktrekken blijft uit.",
    "🔇  Silence probe": "🔇  Stiltecontrole",
    "Every title is probed — playback skips its silent edges.":
        "Elke titel is gecontroleerd — het afspelen slaat de stille randen over.",
    "%d of %d titles are not probed — each is decoded when it starts.":
        "%d van %d titels zijn niet gecontroleerd — elk wordt bij de start gedecodeerd.",
    "🐂  Paso Doble highlights": "🐂  Paso Doble-hoogtepunten",
    "Every Paso Doble knows its highlights.":
        "Elke Paso Doble kent zijn hoogtepunten.",
    "No Paso Doble in tonight's lists.":
        "Geen Paso Doble in de lijsten van vanavond.",
    "%d of %d Paso Dobles have no highlights — 🐂 cannot stop at one.":
        "%d van %d Paso Dobles hebben geen hoogtepunten — 🐂 kan bij geen enkele stoppen.",
    "🔁  Duplicates": "🔁  Dubbele",
    "%d duplicates across the decks and the Practice list.":
        "%d dubbele over de decks en de oefenlijst.",
    "No title is planned twice.": "Geen titel is twee keer ingepland.",
    "🧹  Removed %d duplicate title": "🧹  %d dubbele titel verwijderd",
    "🧹  Removed %d duplicate titles": "🧹  %d dubbele titels verwijderd",
    "⭐  Moved %d track(s) to the wishlist":
        "⭐  %d nummer(s) naar de wensenlijst verplaatst",
    "⭐  Added %d track(s) to the wishlist":
        "⭐  %d nummer(s) aan de wensenlijst toegevoegd",
    "  ·  🧹 %d already in a playlist removed":
        "  ·  🧹 %d al in een afspeellijst, verwijderd",
    "➕  Added %d track(s)": "➕  %d nummer(s) toegevoegd",
    "➕  Added %d track(s) — rounds re-cut":
        "➕  %d nummer(s) toegevoegd — rondes opnieuw verdeeld",
    "🎯  Placed %d track(s)": "🎯  %d nummer(s) geplaatst",
    "  (%d skipped — no free slot)": "  (%d overgeslagen — geen vrije plek)",
    "… plus %d more": "… en nog %d",
    "🔁  Replaced “%s” with “%s”": "🔁  ‘%s’ vervangen door ‘%s’",
    "⚠  “%s” is already in this playlist — not replaced":
        "⚠  ‘%s’ staat al in deze afspeellijst — niet vervangen",
    "🔁  Replaced %d track(s)": "🔁  %d nummer(s) vervangen",
    "🔁  Replaced %d, ➕ added %d track(s)":
        "🔁  %d vervangen, ➕ %d nummer(s) toegevoegd",
    "  (%s — skipped)": "  (%s — overgeslagen)",
    "%d already planned": "%d al ingepland",
    "%d with no dance": "%d zonder dans",
    "⚠  Couldn't tell what dance “%s” is — nothing added":
        "⚠  Kon niet zien welke dans ‘%s’ is — niets toegevoegd",
    "⚠  “%s” is already in this playlist — nothing added":
        "⚠  ‘%s’ staat al in deze afspeellijst — niets toegevoegd",
    "Nothing added — %s": "Niets toegevoegd — %s",
    "TSO tempo equalize → on": "TSO-tempo gelijktrekken → aan",
    "TSO tempo equalize → off": "TSO-tempo gelijktrekken → uit",
    "🎉  Party set — %s": "🎉  Feestinstelling — %s",
    "🏆  Tournament set — %s": "🏆  Toernooi-instelling — %s",
    "🎚  Own settings — %s": "🎚  Eigen instellingen — %s",
    "🎉  Party set applied": "🎉  Feestinstelling toegepast",
    "🏆  Tournament set back": "🏆  Terug op de toernooi-instelling",
    "🏆  Tournament set applied": "🏆  Toernooi-instelling toegepast",
    "nothing to change": "niets te wijzigen",
    ", running at %s": ", klok staat op %s",
    "🕒  Timetable saved — %d entries": "🕒  Tijdschema opgeslagen — %d regels",
    ", fading every %ss": ", overgang elke %s s",
    "play length → %s": "speelduur → %s",
    "fade-out → %s s": "uitfaden → %s s",
    "auto-advance → on": "automatisch naar het volgende nummer → aan",
    "auto-advance → off": "automatisch naar het volgende nummer → uit",
    "pause between songs → on": "pauze tussen nummers → aan",
    "pause between songs → off (no break music)":
        "pauze tussen nummers → uit (geen pauzemuziek)",
    "equalize volume → on": "volume gelijktrekken → aan",
    "equalize volume → off": "volume gelijktrekken → uit",
    "announce next dance → on": "volgende dans aankondigen → aan",
    "announce next dance → off": "volgende dans aankondigen → uit",
    "double-click → starts the title": "dubbelklik → start de titel",
    "double-click → cues it": "dubbelklik → zet hem alleen klaar",
    "🐂 Paso Doble highlight stop → on":
        "🐂 Paso Doble: stoppen bij het hoogtepunt → aan",
    "🐂 Paso Doble highlight stop → off":
        "🐂 Paso Doble: stoppen bij het hoogtepunt → uit",
    "📌 Session saved — decks, wishlists, 🎛 cartwall and layout.":
        "📌 Sessie opgeslagen — decks, wensenlijsten, 🎛 Cartwall en indeling.",
    "Error generating playlist: %s":
        "Fout bij het maken van de afspeellijst: %s",
    "  (iteration %d)": "  (iteratie %d)",
    " — from %s": " — uit %s",
    "Generated %d songs — %s, %s, %s": "%d nummers gemaakt — %s, %s, %s",
    "Skipped competition(s):": "Overgeslagen wedstrijd(en):",
    "📅 Day plan: %d generated, %d skipped":
        "📅 Dagplanning: %d gemaakt, %d overgeslagen",
    "📅 Day plan: %d competition(s) generated":
        "📅 Dagplanning: %d wedstrijd(en) gemaakt",
    "Seeding '%s' from past playlists…":
        "‘%s’ vullen uit eerdere afspeellijsten…",
    "Error reading past playlists: %s":
        "Fout bij het lezen van eerdere afspeellijsten: %s",
    "Generated %d songs — %s": "%d nummers gemaakt — %s",
    "Timbre similarity on for ↺ regenerations":
        "Timbre-overeenkomst aan voor opnieuw loten ↺",
    "Timbre similarity off for ↺ regenerations":
        "Timbre-overeenkomst uit voor opnieuw loten ↺",
    "Building '%s' playlist…": "Afspeellijst ‘%s’ maken…",
    "No tracks matched theme '%s'.": "Geen nummers passen bij thema ‘%s’.",
    "Decade themes require year tags in your MP3s; you can also map\n"
    "songs to themes in themes.json (track_themes).":
        "Decennium-thema’s hebben jaartags in je MP3’s nodig; je kunt nummers ook\n"
        "in themes.json (track_themes) aan thema’s koppelen.",
    "No tracks matched '%s'.": "Geen nummers passen bij ‘%s’.",
    "Theme '%s' — %d tracks": "Thema ‘%s’ — %d nummers",
    "🤸 Building %s…": "🤸 %s maken…",
    "Building %s…": "%s maken…",
    "%s — %d tracks": "%s — %d nummers",
    "🔀 %s shuffled — %d tracks": "🔀 %s geschud — %d nummers",
    "🤸 Practice: nothing loadable from %s":
        "🤸 Oefenen: niets te laden uit %s",
    "🎧 Nothing loadable from %s": "🎧 Niets te laden uit %s",
    "🤖 %d/%d slots filled by %s": "🤖 %d/%d plekken gevuld door %s",
    "🤖 %d tracks by %s": "🤖 %d nummers van %s",
    "%s not installed": "%s is niet geïnstalleerd",
    "Build %s index": "%s-index opbouwen",
    "Build the %s index over %s tracks from %s?":
        "De %s-index opbouwen over %s nummers uit %s?",
    "Analyses the melody/harmony of each track once (slow the first time, then cached).":
        "Analyseert de melodie/harmonie van elk nummer één keer (de eerste keer traag, daarna bewaard).",
    "Loads a neural model and embeds each track once (slow the first time, then cached).":
        "Laadt een neuraal model en verwerkt elk nummer één keer (de eerste keer traag, daarna bewaard).",
    "Reuses anything already computed.":
        "Wat al berekend is, wordt hergebruikt.",
    "Building %s index…": "%s-index wordt opgebouwd…",
    "%s indexing failed": "%s-indexering mislukt",
    "All %d file(s) failed to embed.\n"
    "\n"
    "First error:\n"
    "%s\n"
    "\n"
    "See the console log for the full traceback.":
        "Geen van de %d bestand(en) kon worden verwerkt.\n"
        "\n"
        "Eerste fout:\n"
        "%s\n"
        "\n"
        "Het consolelog toont de volledige traceback.",
    "unknown": "onbekend",
    "%s indexing failed.": "%s-indexering mislukt.",
    "%s index built — %d embedded, %d failed.":
        "%s-index opgebouwd — %d verwerkt, %d mislukt.",
    "%s index built — %d embedded.": "%s-index opgebouwd — %d verwerkt.",
    "%s index ready": "%s-index klaar",
    "Embedded %d track(s) (%d failed — see log).":
        "%d nummer(s) verwerkt (%d mislukt — zie log).",
    "Embedded %d track(s).": "%d nummer(s) verwerkt.",
    "The %s method is now ready in the Similar-Tracks window.":
        "De methode %s is nu beschikbaar in het venster Vergelijkbare nummers.",
    "%s indexing cancelled — %d embedded so far (cached).":
        "%s-indexering afgebroken — tot nu toe %d verwerkt (bewaard).",
    "Library error: %s": "Bibliotheekfout: %s",
    "Analyzing %s …": "%s analyseren …",
    "Only %s of %s tracks are analyzed so far (analysis is still running). Let analysis finish and try again.":
        "Pas %s van %s nummers zijn geanalyseerd (de analyse loopt nog). Laat de analyse afmaken en probeer het opnieuw.",
    "Only %s of %s tracks are analyzed so far. Let analysis finish and try again.":
        "Pas %s van %s nummers zijn geanalyseerd. Laat de analyse afmaken en probeer het opnieuw.",
    "Global search is on but the repository isn't analyzed yet — open ⚙ Settings → “Build / refresh global audio index”.":
        "Globaal zoeken staat aan, maar de verzameling is nog niet geanalyseerd — open ⚙ Instellingen → ‘Globale audio-index opbouwen / verversen’.",
    "No tracks are analyzed yet — run 'Analyze Audio' first.":
        "Nog geen nummers geanalyseerd — voer eerst ‘Audio analyseren’ uit.",
    "All tracks are analyzed — this file just has no close match.":
        "Alle nummers zijn geanalyseerd — dit bestand heeft gewoon geen nauwe overeenkomst.",
    "No similar tracks found in %s.":
        "Geen vergelijkbare nummers gevonden in %s.",
    "Found %d similar to %s (%s)": "%d vergelijkbaar met %s gevonden (%s)",
    "Global library ready from cache — %s files.":
        "Globale bibliotheek klaar uit de cache — %s bestanden.",
    "Global index: %s files, %s analyzed.":
        "Globale index: %s bestanden, %s geanalyseerd.",
    "Scanning repository… %s/%s  (%s left)":
        "Verzameling scannen… %s/%s  (nog %s)",
    "Remove cached data of deleted music files and compact %s (%s MB)?":
        "Bewaarde gegevens van verwijderde muziekbestanden weghalen en %s (%s MB) comprimeren?",
    "Feature vectors, embeddings and loudness of files that no longer exist on disk are removed for good (they would simply be re-analyzed if the files ever come back). Compacting can take a few minutes.":
        "Kenmerkvectoren, embeddings en luidheid van bestanden die niet meer op de schijf staan, worden definitief verwijderd (komen de bestanden ooit terug, dan worden ze gewoon opnieuw geanalyseerd). Comprimeren kan enkele minuten duren.",
    "deleted tracks": "verwijderde nummers",
    "tag records": "tagregels",
    "feature vectors": "kenmerkvectoren",
    "AI embeddings": "AI-embeddings",
    "loudness values": "luidheidswaarden",
    "silence maps": "stiltekaarten",
    "vocal shares": "zangaandelen",
    "noise floors": "ruisvloeren",
    "playlist index entries": "regels in de afspeellijstindex",
    "stale index markers": "verouderde indexmarkeringen",
    "🧹 Database compacted: %s MB → %s MB (%s MB freed).":
        "🧹 Database gecomprimeerd: %s MB → %s MB (%s MB vrijgekomen).",
    "Removed rows: %s.": "Verwijderde rijen: %s.",
    "none — everything is still in use": "geen — alles wordt nog gebruikt",
    "Cleanup did not run:": "Het opruimen is niet uitgevoerd:",
    "📤  Export manual PD marks…": "📤  Handmatige PD-markeringen exporteren…",
    "📥  Import manual PD marks…": "📥  Handmatige PD-markeringen importeren…",
    "Export manual PD marks": "Handmatige PD-markeringen exporteren",
    "Import manual PD marks": "Handmatige PD-markeringen importeren",
    "Save the Paso Doble highlights you set by hand (🎯) to a file,\n"
    "to take them to another PC. Detected highlights are not included —\n"
    "🐂 finds those again by itself.":
        "De met de hand gezette Paso Doble-hoogtepunten (🎯) in een bestand opslaan,\n"
        "om ze naar een andere pc mee te nemen. Herkende hoogtepunten zitten er niet bij —\n"
        "die vindt 🐂 zelf opnieuw.",
    "Load hand-set Paso Doble highlights exported on another PC.\n"
    "They are matched by the music itself, not by the file path, and\n"
    "replace what this PC has for those tracks.":
        "Met de hand gezette Paso Doble-hoogtepunten laden die op een andere pc zijn geëxporteerd.\n"
        "Ze worden gekoppeld via de muziek zelf, niet via het bestandspad, en\n"
        "vervangen wat deze pc voor die nummers heeft.",
    "No Paso Doble highlight has been set by hand yet.":
        "Er is nog geen Paso Doble-hoogtepunt met de hand gezet.",
    "Could not write the file:": "Het bestand kon niet geschreven worden:",
    "📤 %d hand-set Paso Doble highlight(s) saved to:\n"
    "%s":
        "📤 %d met de hand gezet(te) Paso Doble-hoogtepunt(en) opgeslagen in:\n"
        "%s",
    "This is no manual-PD-marks file:":
        "Dit is geen bestand met handmatige PD-markeringen:",
    "📥 %d hand-set Paso Doble highlight(s) imported — %d of them belong to a track this PC already knows.\n"
    "\n"
    "The others are kept and apply as soon as that music turns up here.":
        "📥 %d met de hand gezet(te) Paso Doble-hoogtepunt(en) geïmporteerd — %d daarvan horen bij een nummer dat deze pc al kent.\n"
        "\n"
        "De andere blijven bewaard en gelden zodra die muziek hier opduikt.",
    "♻  Restore user data backup…":
        "♻  Back-up van eigen gegevens terugzetten…",
    "Restore user data backup": "Back-up van eigen gegevens terugzetten",
    "Merge a daily backup of your tag edits, hand-set Paso Doble\n"
    "highlights and play log back in. The app keeps one per day for the last 7 days.\n"
    "Everything else in the database is left as it is.":
        "Een dagelijkse back-up van je tagwijzigingen, met de hand gezette\n"
        "Paso Doble-hoogtepunten en afspeellogboek terugzetten. De app bewaart er één per dag voor de laatste 7 dagen.\n"
        "Al het andere in de database blijft zoals het is.",
    "This is no user data backup:": "Dit is geen back-up van eigen gegevens:",
    "♻ %d tag edit(s) and %d hand-set Paso Doble highlight(s) restored, %d played title(s) added to the play log.\n"
    "\n"
    "They take effect after a restart of the app.":
        "♻ %d tagwijziging(en) en %d met de hand gezet(te) Paso Doble-hoogtepunt(en) teruggezet, %d gespeelde titel(s) aan het logboek toegevoegd.\n"
        "\n"
        "Ze werken na een herstart van de app.",
    "Date": "Datum",
    "List": "Lijst",
    "Duration": "Duur",
    "📜 Played titles": "📜 Gespeelde titels",
    "📜  Played titles…": "📜  Gespeelde titels…",
    "Nothing has been played yet. A title is logged in playing mode\n"
    "once it has run for 10 seconds, the moment its row greys out.":
        "Er is nog niets gespeeld. Een titel wordt in de speelmodus vastgelegd\n"
        "zodra hij 10 seconden heeft gelopen, op het moment dat zijn rij grijs wordt.",
    "💾  Save as CSV…": "💾  Opslaan als CSV…",
    "Save this evening as a table for Excel: date, start, artist, title,\n"
    "dance, list and how long each title ran — e.g. for a GEMA report.":
        "Slaat deze avond op als tabel voor Excel: datum, start, artiest, titel,\n"
        "dans, lijst en hoe lang elke titel liep — bijv. voor een melding aan de auteursrechtenorganisatie.",
    "🗑  Delete evening": "🗑  Avond verwijderen",
    "Delete evening": "Avond verwijderen",
    "%d title(s)": "%d titel(s)",
    "Save played titles": "Gespeelde titels opslaan",
    "CSV files (*.csv);;All files (*)":
        "CSV-bestanden (*.csv);;Alle bestanden (*)",
    "Delete the evening of %s with its %d title(s) from the play log?\n"
    "\n"
    "Its daily backups still hold it for 7 days.":
        "De avond van %s met zijn %d titel(s) uit het logboek verwijderen?\n"
        "\n"
        "De dagelijkse back-ups bevatten hem nog 7 dagen.",
    "Playlist popularity re-learned from %s playlists.":
        "Populariteit van afspeellijsten opnieuw geleerd uit %s afspeellijsten.",
    "📜 %s playlists analyzed (M3U files + tournament folders) — popularity and co-occurrence are up to date, so a just-exported tournament counts now.\n"
    "\n"
    "Rows already in the grid keep their old Pop value until regenerated.":
        "📜 %s afspeellijsten geanalyseerd (M3U-bestanden + toernooimappen) — populariteit en samen voorkomen zijn bijgewerkt, dus een net geëxporteerd toernooi telt al mee.\n"
        "\n"
        "Rijen die al in het raster staan, houden hun oude Pop-waarde tot ze opnieuw geloot worden.",
    "Re-learn failed:": "Opnieuw leren mislukt:",
    "  … and %d more": "  … en nog %d",
    "⚠ %d title(s) are not on the Reference path\n"
    "%s\n"
    "and were saved with their own path:":
        "⚠ %d titel(s) staan niet op het referentiepad\n"
        "%s\n"
        "en zijn met hun eigen pad opgeslagen:",
    "💾 Saved %d playlist → %s": "💾 %d afspeellijst opgeslagen → %s",
    "💾 Saved %d playlists → %s": "💾 %d afspeellijsten opgeslagen → %s",
    "Saved %d playlist(s) to:\n"
    "%s":
        "%d afspeellijst(en) opgeslagen in:\n"
        "%s",
    "Saved %d wishlist(s) to:\n"
    "%s":
        "%d wensenlijst(en) opgeslagen in:\n"
        "%s",
    "Skipped (empty): %s": "Overgeslagen (leeg): %s",
    "Errors:": "Fouten:",
    "“%s” already exists in the target folder.\n"
    "Replace it, or keep both?":
        "‘%s’ bestaat al in de doelmap.\n"
        "Vervangen, of beide houden?",
    "🧳 Bundle: %d playlist folder(s), %d track(s), %s MB → %s":
        "🧳 Pakket: %d afspeellijstmap(pen), %d nummer(s), %s MB → %s",
    "Bundle written to:\n"
    "%s":
        "Pakket geschreven naar:\n"
        "%s",
    "%d playlist folder(s) · %d track(s) · %s MB — each folder holds the tracks numbered in play order plus the playlist's M3U, so it plays even without the M3U.":
        "%d afspeellijstmap(pen) · %d nummer(s) · %s MB — elke map bevat de nummers genummerd in speelvolgorde plus de M3U van de afspeellijst, dus hij speelt ook zonder de M3U.",
    "⚠ %d track(s) were missing on disk and kept their original absolute path.":
        "⚠ %d nummer(s) ontbraken op de schijf en hebben hun oorspronkelijke absolute pad behouden.",
    "💾 Saved %d competition playlist → %s":
        "💾 %d wedstrijdafspeellijst opgeslagen → %s",
    "💾 Saved %d competition playlists → %s":
        "💾 %d wedstrijdafspeellijsten opgeslagen → %s",
    "Saved %d competition playlist(s) to:\n"
    "%s":
        "%d wedstrijdafspeellijst(en) opgeslagen in:\n"
        "%s",
    "Nothing to save.": "Niets op te slaan.",
    "Saved → %s": "Opgeslagen → %s",
    "Saved %d competition playlist(s) → %s":
        "%d wedstrijdafspeellijst(en) opgeslagen → %s",
    "Close the tournament-day view? This clears %d day playlist.":
        "De toernooidagweergave sluiten? Dit leegt %d dagafspeellijst.",
    "Close the tournament-day view? This clears %d day playlists.":
        "De toernooidagweergave sluiten? Dit leegt %d dagafspeellijsten.",
    "Clear the %d day playlist?": "De %d dagafspeellijst leegmaken?",
    "Clear all %d day playlists?": "Alle %d dagafspeellijsten leegmaken?",
    "Clear the %d playlist on “%s”?": "De %d afspeellijst op ‘%s’ leegmaken?",
    "Clear all %d playlists on “%s”?":
        "Alle %d afspeellijsten op ‘%s’ leegmaken?",
    "🧹 %s playlists cleared.": "🧹 Afspeellijsten op %s leeggemaakt.",
    " — %d track(s) of no known dance left out":
        " — %d nummer(s) zonder bekende dans weggelaten",
    "🔒 Static mode — a drop now replaces a single slot":
        "🔒 Statische modus — neerzetten vervangt nu één plek",
    "🔓 Dynamic mode — drag songs from the wishlist or another deck to build rounds & heats":
        "🔓 Dynamische modus — sleep nummers uit de wensenlijst of een ander deck om rondes & heats op te bouwen",
    "✋ Free order — every row can be dragged anywhere, and a dropped song lands where you drop it":
        "✋ Vrije volgorde — elke rij kan overal heen gesleept worden, en een neergezet nummer komt precies daar terecht",
    "%d of these %d tracks say nothing about which dance they are. A grid has no column to put them in, so building one leaves them out of the deck.\n"
    "\n"
    "Build the grid without them?":
        "%d van deze %d nummers zeggen niet welke dans ze zijn. Een raster heeft geen kolom voor ze, dus bij het opbouwen vallen ze uit het deck.\n"
        "\n"
        "Het raster zonder ze opbouwen?",
    "🤸 %s panel shown — drop an .m3u here or build one with 🤸 %s.":
        "🤸 %s-paneel getoond — zet hier een .m3u neer of maak er een met 🤸 %s.",
    "🤸 %s panel hidden": "🤸 %s-paneel verborgen",
    "📚 Library filtered: %s": "📚 Bibliotheek gefilterd: %s",
    "all dances": "alle dansen",
    " · class %s": " · klasse %s",
    " · never played": " · nooit gespeeld",
    "<b>%d</b> of %d checked tracks have at least one issue.":
        "<b>%d</b> van %d gecontroleerde nummers hebben minstens één probleem.",
    "Plus <b>%d</b> 🧩 round-structure issue — see the yellow box below.":
        "Plus <b>%d</b> 🧩 probleem in de rondeopbouw — zie het gele vak hieronder.",
    "Plus <b>%d</b> 🧩 round-structure issues — see the yellow box below.":
        "Plus <b>%d</b> 🧩 problemen in de rondeopbouw — zie het gele vak hieronder.",
    "%d tracks skipped — no label/dance/length or not audio-analyzed.":
        "%d nummers overgeslagen — geen label/dans/lengte of niet audio-geanalyseerd.",
    "⚡ tempo label vs measured off > %.0f%% (×2, ×3, ×1.5 … slips excused) · 🐢/🐇 takt outside the official TSO range · ⏱ real play ≤ %s":
        "⚡ tempolabel wijkt > %.0f%% af van de meting (×2, ×3, ×1,5 … worden toegestaan) · 🐢/🐇 maat buiten het officiële TSO-bereik · ⏱ echte speelduur ≤ %s",
    "⏳ longer than %s": "⏳ langer dan %s",
    "🔇 noise floor above %.0f dB": "🔇 ruisvloer boven %.0f dB",
    "Thresholds: ⚙ Settings → 🎵 Checks.":
        "Drempels: ⚙ Instellingen → 🎵 Controles.",
    "⏳  Also flag long tracks (> %s) — only relevant when building a Practice playlist":
        "⏳  Ook lange nummers markeren (> %s) — alleen van belang bij het maken van een oefenafspeellijst",
    "🔇  Also flag hissy tracks (never quieter than %.0f dB) — measures each track once with ffmpeg, so the first run takes a moment":
        "🔇  Ook ruisende nummers markeren (nooit zachter dan %.0f dB) — meet elk nummer één keer met ffmpeg, dus de eerste keer duurt even",
    "🧩 <b>Round structure</b> — click a spot to jump to it":
        "🧩 <b>Rondeopbouw</b> — klik op een plek om erheen te springen",
    "In playlist: %s": "In afspeellijst: %s",
    "⚠  “%s” is no longer in an open deck.":
        "⚠  ‘%s’ staat in geen enkel open deck meer.",
    "<b>%d</b> of %d checked tracks have an issue.":
        "<b>%d</b> van %d gecontroleerde nummers hebben een probleem.",
    "%d skipped — not found / not audio-analyzed.":
        "%d overgeslagen — niet gevonden / niet audio-geanalyseerd.",
    "⚡ tempo label vs measured · 🐢/🐇 takt outside the TSO range · ⏱ short · ⏳ long · 🔇 hiss · 🧩 round structure (uneven dances, heat taper, heat tempo spread).":
        "⚡ tempolabel tegen meting · 🐢/🐇 maat buiten het TSO-bereik · ⏱ kort · ⏳ lang · 🔇 ruis · 🧩 rondeopbouw (ongelijke dansen, krimpende heats, tempospreiding per heat).",
    "🧩 <b>Round structure</b>": "🧩 <b>Rondeopbouw</b>",
    "%d valid · %d unresolved across %d playlist.":
        "%d geldig · %d onopgelost in %d afspeellijst.",
    "%d valid · %d unresolved across %d playlists.":
        "%d geldig · %d onopgelost in %d afspeellijsten.",
    "🔧 %d path line to fix": "🔧 %d padregel te corrigeren",
    "🔧 %d path lines to fix": "🔧 %d padregels te corrigeren",
    "✅ Nothing to fix": "✅ Niets te corrigeren",
    "🔧 %d track can be moved onto the Reference path":
        "🔧 %d nummer kan naar het referentiepad worden verplaatst",
    "🔧 %d tracks can be moved onto the Reference path":
        "🔧 %d nummers kunnen naar het referentiepad worden verplaatst",
    "%d tracks — <span style='color:#2a7a45;'>%d valid</span> · <b style='color:#e07b00; font-size:13px;'>🔧 %d to fix</b> · <span style='color:#a33;'>%d unresolved</span>":
        "%d nummers — <span style='color:#2a7a45;'>%d geldig</span> · <b style='color:#e07b00; font-size:13px;'>🔧 %d te corrigeren</b> · <span style='color:#a33;'>%d onopgelost</span>",
    "⚠  unresolved (no match under the search folders):":
        "⚠  onopgelost (geen treffer onder de zoekmappen):",
    "Rewrite %d path line(s) across %d playlist(s) in place?\n"
    "\n"
    "Only the file-path lines change — #EXTINF and every other line stay exactly as-is. This overwrites the .m3u files on disk; each original is kept next to it as <name>.m3u.bak.":
        "%d padregel(s) in %d afspeellijst(en) ter plekke herschrijven?\n"
        "\n"
        "Alleen de bestandspadregels veranderen — #EXTINF en alle andere regels blijven precies zoals ze zijn. Dit overschrijft de .m3u-bestanden op de schijf; elk origineel blijft ernaast bewaard als <name>.m3u.bak.",
    "🧭  Rewrote %d path line(s) in %d playlist(s).":
        "🧭  %d padregel(s) in %d afspeellijst(en) herschreven.",
    "⚠  Left unchanged:": "⚠  Ongewijzigd gelaten:",
    "… and %d more": "… en nog %d",
    "Could not apply snapshot: %s":
        "Momentopname kon niet worden toegepast: %s",
    "Could not restore saved playlist: %s":
        "Opgeslagen afspeellijst kon niet worden hersteld: %s",
    "⚠  %d saved track(s) not found — is the music drive plugged in?":
        "⚠  %d opgeslagen nummer(s) niet gevonden — is de muziekschijf aangesloten?",
    "The saved session is kept as %s.":
        "De opgeslagen sessie blijft bewaard als %s.",
    "↩  Restored your in-progress playlist — %d songs (%s, %s)":
        "↩  Je onafgemaakte afspeellijst is hersteld — %d nummers (%s, %s)",
    "↩  Restored your running order — %d tracks":
        "↩  Je draaiboek is hersteld — %d nummers",
    "↩  Restored your themed playlist — %d tracks":
        "↩  Je themalijst is hersteld — %d nummers",
    "All %d playlists already hold tracks — there's no free slot to import into.\n"
    "\n"
    "Clear a playlist first, or pick a single file to overwrite the focused deck.":
        "Alle %d afspeellijsten bevatten al nummers — er is geen vrije plek om in te importeren.\n"
        "\n"
        "Maak eerst een afspeellijst leeg, of kies één bestand om het deck met de focus te overschrijven.",
    "You picked %d files but only %d playlist slot(s) are free.\n"
    "\n"
    "Import the first %d into the free slots and skip the rest?":
        "Je hebt %d bestanden gekozen, maar er zijn maar %d afspeellijstplek(ken) vrij.\n"
        "\n"
        "De eerste %d in de vrije plekken importeren en de rest overslaan?",
    "Importing %s …": "%s importeren …",
    "Import failed: %s": "Importeren mislukt: %s",
    "Remove %d title from %s?\n"
    "It is already planned in: %s":
        "%d titel uit %s verwijderen?\n"
        "Hij is al ingepland in: %s",
    "Remove %d titles from %s?\n"
    "They are already planned in: %s":
        "%d titels uit %s verwijderen?\n"
        "Ze zijn al ingepland in: %s",
    "Empty %d playlist? This can't be undone.":
        "%d afspeellijst leegmaken? Dit kan niet ongedaan worden gemaakt.",
    "Empty %d playlists? This can't be undone.":
        "%d afspeellijsten leegmaken? Dit kan niet ongedaan worden gemaakt.",
    "↩  Restored your worked playlist for “%s” — %d songs":
        "↩  Je bewerkte afspeellijst voor ‘%s’ is hersteld — %d nummers",
    "this competition": "deze wedstrijd",
    "⚠  Session not saved — the snapshot failed: %r":
        "⚠  Sessie niet opgeslagen — de momentopname is mislukt: %r",
    "Could not write the PDF:\n"
    "%s":
        "Het pdf-bestand kon niet worden geschreven:\n"
        "%s",
    "🖨 Playlist saved — %s": "🖨 Afspeellijst opgeslagen — %s",
    "Playlist saved as\n"
    "%s\n"
    "\n"
    "Open it now?":
        "Afspeellijst opgeslagen als\n"
        "%s\n"
        "\n"
        "Nu openen?",
    "Cycle 1 → 2 → 4 → 8 → no playlists (and back).":
        "Doorlopen 1 → 2 → 4 → 8 → geen afspeellijsten (en terug).",
    "Cycle 1 → 2 → 4 → no playlists (and back).":
        "Doorlopen 1 → 2 → 4 → geen afspeellijsten (en terug).",
    "Right click walks the cycle backwards.":
        "Rechtsklikken loopt de cyclus achteruit door.",
    "8 splits into two tabs of four (Group A–D / Group E–H).":
        "8 wordt verdeeld over twee tabbladen van vier (Groep A–D / Groep E–H).",
    "No-playlist hides every deck so the Practice / wishlist / library panes take over.":
        "‘Geen afspeellijst’ verbergt alle decks, zodat de panelen Oefenen / wensenlijst / bibliotheek de ruimte innemen.",
    "Two or more decks also reveal the wishlist below.":
        "Vanaf twee decks verschijnt eronder ook de wensenlijst.",
    "Generate / Save / ↺ / play act on whichever deck has focus.":
        "Genereren / Opslaan / ↺ / afspelen werken op het deck met de focus.",
    "Show / hide the %s panel.\n"
    "Opens an empty panel — drop an existing .m3u onto it, or build a fresh list with 🤸 %s.":
        "Het %s-paneel tonen / verbergen.\n"
        "Opent een leeg paneel — zet er een bestaande .m3u op neer, of maak een nieuwe lijst met 🤸 %s.",
    "⭐ Swapped %s ⇄ %s": "⭐ %s ⇄ %s verwisseld",
    "Show only the %d track(s) currently in your wishlist(s),\n"
    "ranked by how well they match this song — pick the best one to add.\n"
    "Matches by song (title / fingerprint), so a different copy still counts.":
        "Toont alleen de %d nummer(s) die nu in je wensenlijst(en) staan,\n"
        "gesorteerd op hoe goed ze bij dit nummer passen — kies het beste om toe te voegen.\n"
        "Vergeleken wordt het nummer (titel / vingerafdruk), dus een andere kopie telt ook mee.",
    "🎼  Chroma cover / remix (melody/harmony, same tune)":
        "🎼  Chroma cover / remix (melodie/harmonie, dezelfde melodie)",
    "🎧 Hear and choose — %s": "🎧 Beluisteren en kiezen — %s",
    "🎧 Hear and choose…": "🎧 Beluisteren en kiezen…",
    "Now: %s": "Nu: %s",
    "Now: —": "Nu: —",
    "Where from": "Waarvandaan",
    "Offered for this slot": "Aangeboden voor deze plek",
    "Play / stop this title": "Deze titel afspelen / stoppen",
    "▶ or Space plays a title, again stops it, Ctrl+←/→ seeks 30 s, Ctrl+Shift+←/→ plays the title before or after it; a double click or \"Take\" puts it into the slot.":
        "▶ of Spatie speelt een titel, nog eens stopt hem, Ctrl+←/→ spoelt 30 s, Ctrl+Shift+←/→ speelt de titel ervoor of erna; een dubbelklik of ‘Overnemen’ zet hem op de plek.",
    "Take": "Overnemen",
    "⚖️  Combined: timbre + groove + melody (mean)":
        "⚖️  Gecombineerd: klankkleur + groove + melodie (gemiddelde)",
    "⚖️ Combined — the mean of where each title ranks by timbre, groove and melody.":
        "⚖️ Gecombineerd — het gemiddelde van waar elke titel staat op klankkleur, groove en melodie.",
    "★  Only rarely played (1–%d playlists)":
        "★  Alleen zelden gespeeld (1–%d afspeellijsten)",
    "The same three picks as 📚 the library's ★ Plays selector.\n"
    "'Never played': the track is in none of your old playlists.\n"
    "'Rarely played': in 1–%d of them — %d+ is a proven title.\n"
    "'Not since 1 y': it is played, but the newest playlist carrying\n"
    "it is from an earlier year — the year comes from the playlist's\n"
    "path, so lists without a date never count as old.":
        "Dezelfde drie filters als de ★ Gespeeld-kiezer van de 📚 bibliotheek.\n"
        "‘Nooit gespeeld’: het nummer staat in geen van je oude afspeellijsten.\n"
        "‘Zelden gespeeld’: in 1–%d ervan — vanaf %d is het een beproefde titel.\n"
        "‘Niet sinds 1 jaar’: het wordt gespeeld, maar de nieuwste afspeellijst ermee\n"
        "is van een eerder jaar — het jaar komt uit het pad van de\n"
        "afspeellijst, dus lijsten zonder datum gelden nooit als oud.",
    "%d %s tracks most often played together with this one — ▶ to preview, double-click to open, drag rows into another app":
        "%d %s-nummers die het vaakst samen met dit nummer zijn gespeeld — ▶ om te beluisteren, dubbelklik om te openen, sleep rijen naar een andere app",
    "%d %s tracks most similar (sound-alike) to this one — ▶ to preview, double-click to open, drag rows into another app":
        "%d %s-nummers die het meest op dit nummer lijken (klinken) — ▶ om te beluisteren, dubbelklik om te openen, sleep rijen naar een andere app",
    "⭐ wishlist only": "⭐ alleen wensenlijst",
    "📜 played in this round before": "📜 eerder in deze ronde gespeeld",
    "📜  Only titles I played in this round before (%s)":
        "📜  Alleen titels die ik eerder in deze ronde heb gespeeld (%s)",
    "Show only titles your past competitions played in this round —\n"
    "any heat of it, from lists of a class and age category that fit\n"
    "this deck (the same history as 📜 Find planned before).\n"
    "Still ranked by how much they sound like this one.":
        "Toon alleen titels die je eerdere wedstrijden in deze ronde speelden —\n"
        "in welke heat dan ook, uit lijsten van een klasse en leeftijdscategorie die\n"
        "bij dit deck passen (dezelfde geschiedenis als 📜 Eerder gepland zoeken).\n"
        "Nog steeds gesorteerd op hoeveel ze als dit nummer klinken.",
    "🎙 instrumental only (%d vocal hidden)":
        "🎙 alleen instrumentaal (%d met zang verborgen)",
    "%s (%d hidden)": "%s (%d verborgen)",
    "%d duplicate hidden": "%d duplicaat verborgen",
    "%d duplicates hidden": "%d duplicaten verborgen",
    "%d track(s) you planned for this dance &amp; round in past competitions — best competition match first (see Class) — ▶ to preview, drag a row onto the slot, double-click to open":
        "%d nummer(s) die je voor deze dans &amp; ronde op eerdere wedstrijden hebt ingepland — beste wedstrijdtreffer eerst (zie Klasse) — ▶ om te beluisteren, sleep een rij op de plek, dubbelklik om te openen",
    "Similar to: %s": "Vergelijkbaar met: %s",
    "📋 Learned from your playlists — %d often played together.":
        "📋 Geleerd uit je afspeellijsten — %d vaak samen gespeeld.",
    "🧠  Rebuild %s index…": "🧠  %s-index opnieuw opbouwen…",
    "%s vectors for these %d tracks haven't been built yet.\n"
    "\n"
    "Building analyses each track once (slow the first time, then cached).\n"
    "Build now?":
        "%s-vectoren voor deze %d nummers zijn nog niet opgebouwd.\n"
        "\n"
        "Opbouwen analyseert elk nummer één keer (de eerste keer traag, daarna bewaard).\n"
        "Nu opbouwen?",
    "Building %s embedding index…": "%s-embeddingindex wordt opgebouwd…",
    "All %d file(s) failed to embed.\n"
    "\n"
    "First error:\n"
    "%s\n"
    "\n"
    "Common causes: the neural model couldn't load, or the deps are mismatched. See the console log for the full traceback.":
        "Alle %d bestand(en) konden niet worden verwerkt.\n"
        "\n"
        "Eerste fout:\n"
        "%s\n"
        "\n"
        "Veelvoorkomende oorzaken: het neurale model kon niet laden, of de afhankelijkheden passen niet bij elkaar. Het consolelog toont de volledige traceback.",
    "🧠 %s index ready (%d embedded, %d failed).":
        "🧠 %s-index klaar (%d verwerkt, %d mislukt).",
    "🧠 %s index ready (%d embedded).": "🧠 %s-index klaar (%d verwerkt).",
    "%s indexing cancelled — showing librosa results.":
        "%s-indexering afgebroken — librosa-resultaten worden getoond.",
    "Ranking by %s embedding…": "Sorteren op %s-embedding…",
    "No %s matches yet — try building the index over more tracks.":
        "Nog geen %s-treffers — bouw de index op over meer nummers.",
    "🧠 %s — %d deep-embedding matches.": "🧠 %s — %d deep-embedding-treffers.",
    "Refreshed — %d similar to %s": "Ververst — %d vergelijkbaar met %s",
    "%s / %s  (%s left)": "%s / %s  (nog %s)",
    "~%s remaining": "nog ~%s",
    "Listing files…": "Bestanden worden opgesomd…",
    "This is not an audio file, so it won't be opened:\n"
    "%s":
        "Dit is geen audiobestand, dus het wordt niet geopend:\n"
        "%s",
    "File not found:\n"
    "%s":
        "Bestand niet gevonden:\n"
        "%s",
    "Couldn't open the file:\n"
    "%s":
        "Het bestand kon niet worden geopend:\n"
        "%s",
    "Folder not found:\n"
    "%s":
        "Map niet gevonden:\n"
        "%s",
    "Couldn't open the folder:\n"
    "%s":
        "De map kon niet worden geopend:\n"
        "%s",
    "Couldn't reveal the file:\n"
    "%s":
        "Het bestand kon niet worden getoond:\n"
        "%s",
    "✅  No duplicates among the %d file added.":
        "✅  Geen duplicaten onder het %d toegevoegde bestand.",
    "✅  No duplicates among the %d files added.":
        "✅  Geen duplicaten onder de %d toegevoegde bestanden.",
    "Comparison failed:\n"
    "%s":
        "Vergelijken mislukt:\n"
        "%s",
    "✅  %d hard duplicate(s) to remove, %d unused track(s) to export (of %d; %d Paso Doble kept). Review below, then export.":
        "✅  %d harde duplica(a)t(en) te verwijderen, %d ongebruikt(e) nummer(s) te exporteren (van %d; %d Paso Doble behouden). Controleer hieronder en exporteer dan.",
    "Could not write file:\n"
    "%s":
        "Het bestand kon niet worden geschreven:\n"
        "%s",
    "The reference playlist itself was overwritten with the cleaned list.":
        "De referentieafspeellijst zelf is overschreven met de opgeschoonde lijst.",
    "The reference playlist was left unchanged.":
        "De referentieafspeellijst is ongewijzigd gebleven.",
    "📤  Exported %d track(s) (sorted by dance) → %s":
        "📤  %d nummer(s) geëxporteerd (op dans gesorteerd) → %s",
    "📤  Exported %d track(s) → %s": "📤  %d nummer(s) geëxporteerd → %s",
    "Exported %d unused track(s) to:\n"
    "%s\n"
    "\n"
    "%d hard duplicate(s) removed. %s":
        "%d ongebruikt(e) nummer(s) geëxporteerd naar:\n"
        "%s\n"
        "\n"
        "%d harde duplica(a)t(en) verwijderd. %s",
    "🔁  Replace in %s": "🔁  Vervangen in %s",
    "This song is in %d open playlists. Replacing it on one\n"
    "row leaves the other copies — pick a copy on each of its rows to\n"
    "replace them all (the choices are merged when you press Apply).":
        "Dit nummer staat in %d open afspeellijsten. Vervang je het in één\n"
        "rij, dan blijven de andere kopieën staan — kies in elk van zijn rijen een\n"
        "kopie om ze allemaal te vervangen (de keuzes worden samengevoegd bij Toepassen).",
    "%d occurrence(s) are set to Replace but have no replacement track yet.\n"
    "Pick a track for each, or switch them back to Keep.":
        "%d keer staat op Vervangen, maar heeft nog geen vervangend nummer.\n"
        "Kies voor elk een nummer, of zet ze terug op Behouden.",
    "%d copy/copies are set to two different changes on different rows.\n"
    "Choose the same on each, or set one back to Keep all.":
        "%d kopie(ën) staan op twee verschillende wijzigingen in verschillende rijen.\n"
        "Kies overal hetzelfde, of zet er één terug op Alles behouden.",
    "🗑  Remove from %s": "🗑  Verwijderen uit %s",
    "🗑  Removed %d duplicate": "🗑  %d duplicaat verwijderd",
    "🗑  Removed %d duplicates": "🗑  %d duplicaten verwijderd",
    "A track named “%s” is already in this playlist,\n"
    "but it’s a different file.":
        "Een nummer met de naam ‘%s’ staat al in deze afspeellijst,\n"
        "maar het is een ander bestand.",
    "“%s” is already in this playlist —\n"
    "“%s” looks like the same title in another file.":
        "‘%s’ staat al in deze afspeellijst —\n"
        "‘%s’ lijkt dezelfde titel in een ander bestand.",
    "“%s” is already in this playlist.\n"
    "\n"
    "Remove it from the wishlist anyway?":
        "‘%s’ staat al in deze afspeellijst.\n"
        "\n"
        "Toch uit de wensenlijst verwijderen?",
    "“%s” is already in this playlist.\n"
    "\n"
    "Remove it from the playlist anyway?":
        "‘%s’ staat al in deze afspeellijst.\n"
        "\n"
        "Toch uit de afspeellijst verwijderen?",
    "%d dragged track(s) are already in this playlist.\n"
    "\n"
    "Remove them from the wishlist anyway?":
        "%d gesleept(e) nummer(s) staan al in deze afspeellijst.\n"
        "\n"
        "Toch uit de wensenlijst verwijderen?",
    "%d dragged track(s) are already in this playlist.\n"
    "\n"
    "Remove them from the playlist anyway?":
        "%d gesleept(e) nummer(s) staan al in deze afspeellijst.\n"
        "\n"
        "Toch uit de afspeellijst verwijderen?",
    "“%s” looks like a %s track, but this slot is %s.\n"
    "\n"
    "Replace anyway?":
        "‘%s’ lijkt een %s-nummer, maar deze plek is %s.\n"
        "\n"
        "Toch vervangen?",
    "Remove this whole heat (all dances) from %s?":
        "Deze hele heat (alle dansen) uit %s verwijderen?",
    "⬆  %d song(s) moved up into empty slots":
        "⬆  %d nummer(s) doorgeschoven naar vrije plekken",
    "Remove the entire round “%s” and all %d of its heats?":
        "De hele ronde ‘%s’ met alle %d heats verwijderen?",
    "Remove %s from %s?\n"
    "%d song(s) in this round will be cleared.":
        "%s uit %s verwijderen?\n"
        "%d nummer(s) in deze ronde worden leeggemaakt.",
    "Hide the empty %s from %s?": "%s (leeg) in %s verbergen?",
    "Remove %s from all rounds and heats?\n"
    "%d song(s) across the playlist will be cleared.":
        "%s uit alle rondes en heats verwijderen?\n"
        "%d nummer(s) in de hele afspeellijst worden leeggemaakt.",
    "Hide the empty %s from all rounds?":
        "%s (leeg) in alle rondes verbergen?",
    "%d dropped track(s) look like %s dances, but this is a %s list.\n"
    "\n"
    "Add them anyway?":
        "%d neergezet(te) nummer(s) lijken %s-dansen, maar dit is een %s-lijst.\n"
        "\n"
        "Toch toevoegen?",
    "All open playlists (%d deck)": "Alle open afspeellijsten (%d deck)",
    "All open playlists (%d decks)": "Alle open afspeellijsten (%d decks)",
    "%d file added.": "%d bestand toegevoegd.",
    "%d files added.": "%d bestanden toegevoegd.",
    "📅 Tournament day only (%d playlist)":
        "📅 Alleen toernooidag (%d afspeellijst)",
    "📅 Tournament day only (%d playlists)":
        "📅 Alleen toernooidag (%d afspeellijsten)",
    "Dance: %s": "Dans: %s",
    "%s (%d beats/bar)": "%s (%d tellen/maat)",
    "'%s' is not a valid round pattern for %s %s — use heat counts like 6-3-2-1.":
        "‘%s’ is geen geldig rondepatroon voor %s %s — gebruik heataantallen zoals 6-3-2-1.",
    "Red: the pool can't carry a competition (pool < %d or proven < %d — a 6-3-2-1 needs 12 per dance).  Orange: < 80 %% of the takt-labelled tracks are tournament tempo, or over half the pool is stale (no dateable playlist in ≥ 3 years; 'never played' always counts as stale).  Double-click a row to browse its never-played tracks in 📚 the library.":
        "Rood: de pool draagt geen wedstrijd (pool < %d of beproefd < %d — een 6-3-2-1 heeft 12 per dans nodig).  Oranje: < 80 %% van de nummers met maatlabel heeft toernooitempo, of meer dan de helft van de pool is verouderd (geen dateerbare afspeellijst in ≥ 3 jaar; ‘nooit gespeeld’ telt altijd als verouderd).  Dubbelklik op een rij om de nooit gespeelde nummers ervan in 📚 de bibliotheek te bekijken.",
    "⚠️ %d gap(s) found": "⚠️ %d gat(en) gevonden",
    "(%d playlist)": "(%d afspeellijst)",
    "(%d playlists)": "(%d afspeellijsten)",
    "%d song": "%d nummer",
    "%d songs": "%d nummers",
    "The playlist file is gone:\n"
    "\n"
    "%s":
        "Het afspeellijstbestand is er niet meer:\n"
        "\n"
        "%s",
    "No .m3u playlists found under “%s”.":
        "Geen .m3u-afspeellijsten gevonden onder ‘%s’.",
    "Remove “%s” from the tree?\n"
    "\n"
    "%d playlist file(s) are listed under it — they stay on disk, only this entry goes.":
        "‘%s’ uit de boom verwijderen?\n"
        "\n"
        "Eronder staan %d afspeellijstbestand(en) — die blijven op de schijf, alleen deze regel verdwijnt.",
    "Remove %d entries from the tree?\n"
    "\n"
    "%d playlist file(s) are listed under them — they stay on disk, only these entries go.":
        "%d regels uit de boom verwijderen?\n"
        "\n"
        "Eronder staan %d afspeellijstbestand(en) — die blijven op de schijf, alleen deze regels verdwijnen.",
    "%s and %s are different dances.\n"
    "\n"
    "Only titles of the same dance can swap places, so every round keeps its dances.":
        "%s en %s zijn verschillende dansen.\n"
        "\n"
        "Alleen titels van dezelfde dans kunnen van plek wisselen, zodat elke ronde haar dansen houdt.",
    "No past competition plans found for %s in %s.":
        "Geen eerdere wedstrijdplanningen gevonden voor %s in %s.",
    "Remove all %d track(s) from wishlist%s?":
        "Alle %d nummer(s) uit wensenlijst%s verwijderen?",
    "Remove the entire playlist%s? The table will be blank again.":
        "De hele afspeellijst%s verwijderen? De tabel is daarna weer leeg.",
    "Couldn't read as an audio track:":
        "Kon niet als audionummer worden gelezen:",
    "This list": "Deze lijst",
    "%s holds %d title twice — the same audio, e.g. a copy of the file on another drive:\n"
    "\n"
    "%s\n"
    "\n"
    "Remove the earlier copy? The last one stays.":
        "%s bevat %d titel dubbel — dezelfde audio, bijv. een kopie van het bestand op een andere schijf:\n"
        "\n"
        "%s\n"
        "\n"
        "De eerdere kopie verwijderen? De laatste blijft.",
    "%s holds %d titles twice — the same audio, e.g. a copy of the file on another drive:\n"
    "\n"
    "%s\n"
    "\n"
    "Remove the earlier copies? The last one stays.":
        "%s bevat %d titels dubbel — dezelfde audio, bijv. een kopie van het bestand op een andere schijf:\n"
        "\n"
        "%s\n"
        "\n"
        "De eerdere kopieën verwijderen? De laatste blijft.",
    "Any OpenAI-compatible /chat/completions host.":
        "Elke OpenAI-compatibele /chat/completions-host.",
    "%d models loaded.": "%d modellen geladen.",
    "%d suggestions — %d in your library.":
        "%d suggesties — %d in je bibliotheek.",
    "▾  %d more lines": "▾  nog %d regels",
    "thinking…": "denkt na…",
    "Couldn't read “%s” as an audio track.":
        "‘%s’ kon niet als audionummer worden gelezen.",
    "“%s” holds %d tracks (subfolders included).\n"
    "\n"
    "Reading them all takes a moment — every file's tags are read on the way in.\n"
    "\n"
    "Add them?":
        "‘%s’ bevat %d nummers (submappen meegeteld).\n"
        "\n"
        "Alles inlezen duurt even — van elk bestand worden onderweg de tags gelezen.\n"
        "\n"
        "Toevoegen?",
    "↩ Left at %s — starts there again":
        "↩ Verlaten bij %s — begint daar weer",
    "Plays %s — the stillness at the edges of the file is skipped":
        "Speelt %s — de stilte aan de randen van het bestand wordt overgeslagen",
    "Shorter than the configured play length (%s)":
        "Korter dan de ingestelde speelduur (%s)",
    "%s already holds %d track(s).\n"
    "\n"
    "Importing %s REPLACES them — the list is loaded fresh from the file, the tracks in it now are dropped.\n"
    "\n"
    "Import anyway?":
        "%s bevat al %d nummer(s).\n"
        "\n"
        "%s importeren VERVANGT ze — de lijst wordt opnieuw uit het bestand geladen, de nummers die er nu in staan vervallen.\n"
        "\n"
        "Toch importeren?",
    "“%s” is already used in this playlist.":
        "‘%s’ wordt al gebruikt in deze afspeellijst.",
    "A %s track can only move into another %s slot — not a %s slot.":
        "Een %s-nummer kan alleen naar een andere %s-plek — niet naar een %s-plek.",
    "Dances (%d): %s": "Dansen (%d): %s",
    "Order: %s, %s, …": "Volgorde: %s, %s, …",
    "🟰  Identical files — the earlier copy is removed, the last stays (%d)":
        "🟰  Identieke bestanden — de eerdere kopie wordt verwijderd, de laatste blijft (%d)",
    "✏  %d pads selected — colour, volume, fade, 🔁 and 🔈 apply to all of them.\n"
    "Label and shortcut stay with this pad.":
        "✏  %d pads geselecteerd — kleur, volume, uitfaden, 🔁 en 🔈 gelden voor allemaal.\n"
        "Label en sneltoets blijven bij deze pad.",
    "Empty = this slot's default (%s)": "Leeg = standaard van dit slot (%s)",
    "Empty = no key (this slot has no default)":
        "Leeg = geen toets (dit slot heeft geen standaard)",
    "cut": "harde knip",
    "%s (wall)": "%s (Cartwall)",
    "⚠ already used by %s": "⚠ al gebruikt door %s",
    "%d key claimed twice — the marked ones will not fire. Pad keys win over slot keys.":
        "%d toets dubbel toegewezen — de gemarkeerde reageren niet. Padtoetsen gaan voor slottoetsen.",
    "%d keys claimed twice — the marked ones will not fire. Pad keys win over slot keys.":
        "%d toetsen dubbel toegewezen — de gemarkeerde reageren niet. Padtoetsen gaan voor slottoetsen.",
    "Page %d": "Pagina %d",
    "page %d": "pagina %d",
    "%d pads need %d pages at %d × %d; the wall keeps at most %d.\n"
    "Clear some pads or pick a bigger layout.":
        "%d pads hebben %d pagina's nodig bij %d × %d; de Cartwall houdt er hoogstens %d.\n"
        "Maak enkele pads leeg of kies een groter raster.",
    "Remove %s and the %d pads on it?\n"
    "The sample files are left alone — only the pads go.":
        "%s en de %d pads erop verwijderen?\n"
        "De samplebestanden blijven ongemoeid — alleen de pads gaan weg.",
    "%d pads do not fit one %d × %d page.\n"
    "Pick a bigger layout first.":
        "%d pads passen niet op één pagina van %d × %d.\n"
        "Kies eerst een groter raster.",
    "Could not write the wall:\n"
    "%s":
        "De Cartwall kon niet worden geschreven:\n"
        "%s",
    "%d pads written to\n"
    "%s\n"
    "\n"
    "The sample files themselves are not copied — the wall stores their paths.":
        "%d pads geschreven naar\n"
        "%s\n"
        "\n"
        "De samplebestanden zelf worden niet gekopieerd — de Cartwall bewaart hun paden.",
    "Replace the current wall with %d pads from\n"
    "%s?":
        "De huidige Cartwall vervangen door %d pads uit\n"
        "%s?",
    "The wall is full: %d of %d tracks were placed.\n"
    "Clear some pads or pick a bigger layout for the rest.":
        "De Cartwall is vol: %d van %d nummers zijn geplaatst.\n"
        "Maak enkele pads leeg of kies een groter raster voor de rest.",
    "🔇 Only stillness left from %s — song ended.":
        "🔇 Vanaf %s alleen nog stilte — nummer afgelopen.",
    "🔇 Skipped %ss of leading silence.":
        "🔇 %s s stilte aan het begin overgeslagen.",
    "⚠️ Sample not found: %s": "⚠️ Sample niet gevonden: %s",
    "⏱ Auto-advance pause extended by %ss.":
        "⏱ Pauze voor automatisch doorgaan met %s s verlengd.",
    "⏸ Auto-advance…  🎵 %s": "⏸ Automatisch doorgaan…  🎵 %s",
    "🎯 Highlight at %s — %d mark(s). ✔ Done editing arms the stop.":
        "🎯 Hoogtepunt bij %s — %d markering(en). ✔ Klaar met bewerken zet de stop scherp.",
    "🎯 PD highlight %d marked at %s (stop set to #%s)":
        "🎯 PD-hoogtepunt %d gemarkeerd bij %s (stop op #%s gezet)",
    "🏁  %s finished": "🏁  %s afgelopen",
    "🏁 %s finished — auto-advance stopped.":
        "🏁 %s afgelopen — automatisch doorgaan gestopt.",
    "Can't cue — file not found: %s":
        "Kan niet klaarzetten — bestand niet gevonden: %s",
    "⏸ Cued %s — press ⏯ to play. — ⏭ walks the playlist":
        "⏸ %s klaargezet — druk op ⏯ om af te spelen. — ⏭ loopt de afspeellijst af",
    "⏸ Cued %s — press ⏯ to play.":
        "⏸ %s klaargezet — druk op ⏯ om af te spelen.",
    "the %s %s of this round": "de %s %s van deze ronde",
    "this %s": "deze %s",
    "🎚 TSO tempo: %s %s → T%s (target T%s from %s)":
        "🎚 TSO-tempo: %s %s → T%s (doel T%s uit %s)",
    "⏸  cued: %s": "⏸  klaar: %s",
    "↩ Picked up at %s.": "↩ Hervat bij %s.",
    "⏸  editing: %s": "⏸  bewerken: %s",
    "⏸  editing": "⏸  bewerken",
    "Play length per song: each song is stopped after this time,\n"
    "ramping down over the fade time first. Steps of %s s\n"
    "up to %s; one step further is\n"
    "'full' — no cut, every title plays to its own end.\n"
    "\n"
    "Double-click to type an exact length (e.g. 1:37).":
        "Speelduur per nummer: elk nummer wordt na deze tijd gestopt\n"
        "en zakt eerst weg over de uitfaadtijd. Stappen van %s s\n"
        "tot %s; één stap verder is\n"
        "‘volledig’ — geen knip, elke titel speelt tot zijn eigen einde.\n"
        "\n"
        "Dubbelklik om een exacte lengte in te typen (bijv. 1:37).",
    "Delete the highlight at %s s": "Het hoogtepunt bij %s s verwijderen",
    "Compensate loudness differences between tracks on playback:\n"
    "each song's measured EBU R128 loudness is pulled towards a\n"
    "common target, so quiet old recordings and loud modern\n"
    "masters play at a similar level.":
        "Luidheidsverschillen tussen nummers bij het afspelen compenseren:\n"
        "de gemeten EBU R128-luidheid van elk nummer wordt naar een\n"
        "gemeenschappelijk doel getrokken, zodat zachte oude opnames en luide\n"
        "moderne masters op een vergelijkbaar niveau spelen.",
    "ℹ No loudness measured yet — tracks play at their\n"
    "original volume. Run 📊 Analyze loudness (⚙ Settings)\n"
    "to equalize them.":
        "ℹ Nog geen luidheid gemeten — nummers spelen op hun\n"
        "oorspronkelijke volume. Voer 📊 Luidheid analyseren (⚙ Instellingen) uit\n"
        "om ze gelijk te trekken.",
    "ℹ %d open-playlist track not measured yet — it plays at original volume.\n"
    "Run 📊 Analyze loudness (⚙ Settings) to equalize it too.":
        "ℹ %d nummer uit de open afspeellijsten is nog niet gemeten — het speelt op oorspronkelijk volume.\n"
        "Voer 📊 Luidheid analyseren (⚙ Instellingen) uit om het ook gelijk te trekken.",
    "ℹ %d open-playlist tracks not measured yet — they play at original volume.\n"
    "Run 📊 Analyze loudness (⚙ Settings) to equalize them too.":
        "ℹ %d nummers uit de open afspeellijsten zijn nog niet gemeten — ze spelen op oorspronkelijk volume.\n"
        "Voer 📊 Luidheid analyseren (⚙ Instellingen) uit om ze ook gelijk te trekken.",
    "⚡ Tempo: measured ~%s vs label %s bpm (off %s%%)":
        "⚡ Tempo: gemeten ~%s tegen label %s bpm (%s%% ernaast)",
    "measured": "gemeten",
    "🐢 Too slow: T%s (%s), TSO %s-%s": "🐢 Te langzaam: T%s (%s), TSO %s-%s",
    "🐇 Too fast: T%s (%s), TSO %s-%s": "🐇 Te snel: T%s (%s), TSO %s-%s",
    "⏱ Short: real play %s — %s file minus %ss silence (≤ %s)":
        "⏱ Kort: echte speelduur %s — bestand van %s min %s s stilte (≤ %s)",
    "⏱ Short: %s (≤ %s play length)": "⏱ Kort: %s (≤ %s speelduur)",
    "⏳ Long: %s (> %s)": "⏳ Lang: %s (> %s)",
    "🔇 Hiss: never quieter than %s dB (> %s dB)":
        "🔇 Ruis: nooit zachter dan %s dB (> %s dB)",
    "“%s”: uneven dance counts — ": "‘%s’: ongelijk aantal dansen — ",
    "%s %d/%d (missing in heat ": "%s %d/%d (ontbreekt in heat ",
    "Final ": "Finale ",
    "Semifinal ": "Halve finale ",
    "“%s”": "‘%s’",
    " has %d heats, expected 1.": " heeft %d heats, verwacht 1.",
    " has %d heats, expected 2.": " heeft %d heats, verwacht 2.",
    "“%s”: %s heats differ by %d takte (allowed: 1) — ":
        "‘%s’: de %s-heats verschillen %d maten (toegestaan: 1) — ",
    "heat %d: T%s “%s”": "heat %d: T%s ‘%s’",
    "“%s” — %s": "‘%s’ — %s",
    "🧩 “%s” %s heats differ by %d takte (allowed: 1)":
        "🧩 ‘%s’: de %s-heats verschillen %d maten (toegestaan: 1)",
    "title": "titel",
    "dance": "dans",
    "takt": "maat",
    "year": "jaar",
    "classes": "klassen",
    "instrumental": "instrumentaal",
    "christmas": "kerst",
    "ID3 title": "ID3-titel",
    "artist": "artiest",
    "length": "lengte",
    "markers": "markeringen",
    "⚠ %s: only %d proven song(s) — finals need %d; expect fresh fill-ins.":
        "⚠ %s: maar %d beproefd(e) nummer(s) — finales hebben er %d nodig; reken op nieuwe opvullers.",
    "♪ %s: no track near the ideal %s bpm.":
        "♪ %s: geen nummer in de buurt van het ideale tempo van %s bpm.",
    "✦ %d/%d songs are fresh (%d%% new).":
        "✦ %d/%d nummers zijn nieuw (%d%% nieuw).",
    "⚠ %s could not fill %d of %d slots (%s) — park more tracks there or switch the source back to the Favorites library.":
        "⚠ %s kon %d van %d plekken niet vullen (%s) — parkeer daar meer nummers of zet de bron terug op de favorietenbibliotheek.",
    "⭐ the open wishlists": "⭐ de open wensenlijsten",
    "📅 Day plan: %d competition(s) generated — %d songs locked for the day (Paso Doble may repeat)":
        "📅 Dagplanning: %d wedstrijd(en) gemaakt — %d nummers voor de dag vergrendeld (Paso Doble mag herhalen)",
    "🕑 Seeded from %d past “%s” list(s) — round pool sizes: %s":
        "🕑 Gevuld uit %d eerdere ‘%s’-lijst(en) — poolgrootte per ronde: %s",
    "⚠️ No past “%s” lists found — used the whole favorites library instead":
        "⚠️ Geen eerdere ‘%s’-lijsten gevonden — in plaats daarvan de hele favorietenbibliotheek gebruikt",
    "🎯 %s: %d tracks  (%s)": "🎯 %s: %d nummers  (%s)",
    "↺ swaps with a title from the end, drag-drop replaces":
        "↺ wisselt met een titel van het einde, slepen en neerzetten vervangt",
    "↺ / drag-drop to replace by timbre":
        "↺ / slepen en neerzetten vervangt op klankkleur",
    "🤸 %s: %d tracks  (%s)  — %s": "🤸 %s: %d nummers  (%s)  — %s",
    "📂 Importing %s…": "📂 %s importeren…",
    "%d tracks are on the table, %d of them already in an open deck.":
        "Er liggen %d nummers klaar, %d daarvan al in een open deck.",
    "%d tracks are on the table.": "Er liggen %d nummers klaar.",
    "💾 Saving %s…": "💾 %s opslaan…",
    "➕  Adding %s tracks…": "➕  %s nummers toevoegen…",
    "🐂  Paso Doble in %d s": "🐂  Paso Doble over %d s",
    "⏸  %d s  (paused)": "⏸  %d s  (gepauzeerd)",
    "⚠ Could not play: %s": "⚠ Kon niet afspelen: %s",
    "⚠ Playback failed: %s": "⚠ Afspelen mislukt: %s",
    "unknown error": "onbekende fout",
    "did not start": "startte niet",
    "⚠ “%s” would not play — skipped to the next title.":
        "⚠ ‘%s’ wilde niet afspelen — door naar de volgende titel.",
    "🔇 would not play: %s": "🔇 wilde niet afspelen: %s",
    "▴  fold back": "▴  weer inklappen",
    "⏹  Stop": "⏹  Stoppen",
    "Stop the run. A model that is still thinking is cut off and nothing is changed.":
        "De run stoppen. Een model dat nog nadenkt wordt afgebroken en er wordt niets veranderd.",
    "Waiting for the model…": "Wachten op het model…",
    "Working…": "Bezig…",
    "Stopping…": "Stoppen…",
    "Check cancelled — drop or ➕ add files to run it again.":
        "Controle afgebroken — zet bestanden neer of voeg ze toe met ➕ om opnieuw te starten.",
    "🧳  Export": "🧳  Exporteren",
    "✅ No gaps — every dance × class pool is healthy":
        "✅ Geen gaten — elke pool van dans × klasse is gezond",
    "Unfold the library pane": "Het bibliotheekpaneel uitklappen",
    "📚 Library browser shown": "📚 Bibliotheekbrowser getoond",
    "📚 Library browser hidden": "📚 Bibliotheekbrowser verborgen",
    "💾 Saving all playlists…": "💾 Alle afspeellijsten opslaan…",
    "🧳 Exporting venue bundle…": "🧳 Zaalpakket exporteren…",
    "💾 Saving tournament-day playlists…":
        "💾 Afspeellijsten van de toernooidag opslaan…",
    "This list is empty.": "Deze lijst is leeg.",
    "This wishlist is empty.": "Deze wensenlijst is leeg.",
    "💾 Saving playlist…": "💾 Afspeellijst opslaan…",
    "💾 Saving wishlist…": "💾 Wensenlijst opslaan…",
    "▴ All playlists folded to tabs — click a tab to open one":
        "▴ Alle afspeellijsten tot tabbladen ingeklapt — klik op een tabblad om er een te openen",
    "▾ All playlists unfolded": "▾ Alle afspeellijsten uitgeklapt",
    "Open the library pane back up": "Het bibliotheekpaneel weer openen",
    "Collapse the whole pane —\n"
    "📚 Library and 🏆 Tournaments together":
        "Het hele paneel inklappen —\n"
        "📚 Bibliotheek en 🏆 Toernooien samen",
    "📚 Library pane collapsed — the arrow in the tab bar opens it":
        "📚 Bibliotheekpaneel ingeklapt — de pijl in de tabbalk opent het",
    "📚 Library pane open": "📚 Bibliotheekpaneel open",
    "It failed": "Het is mislukt",
    "Stopped — nothing was changed.": "Gestopt — er is niets veranderd.",
    "AI playlist stopped.": "AI-afspeellijst gestopt.",
    "Why these tracks": "Waarom deze nummers",
    "📅 Planning tournament day…": "📅 Toernooidag plannen…",
    "Playlist not read": "Afspeellijst niet gelezen",
    "🎵 Checking music…": "🎵 Muziek controleren…",
    "✅  No tempo / length issues in the current tracks.":
        "✅  Geen tempo- of lengteproblemen in de huidige nummers.",
    "No tracks in any open playlist — drag playlists into the 📂 tab to check loose files.":
        "Geen nummers in een open afspeellijst — sleep afspeellijsten naar het 📂-tabblad om losse bestanden te controleren.",
    "Method <span style='color:#b00'>(not used in playlist mode)</span>:":
        "Methode <span style='color:#b00'>(niet gebruikt in afspeellijstmodus)</span>:",
    "📁 Reading the dropped folder…": "📁 De neergezette map inlezen…",
    "Drop one or more audio files here, or click to browse":
        "Zet hier een of meer audiobestanden neer, of klik om te bladeren",
    "Empty — switch ✏ Edit on to fill it":
        "Leeg — zet ✏ Bewerken aan om het te vullen",
    "Editing ON — drop, drag, recolour and reshape the wall.\n"
    "Switch off before the tournament so nothing moves by accident.":
        "Bewerken AAN — neerzetten, slepen, herkleuren en de wand ombouwen.\n"
        "Zet het uit voor het toernooi, zodat er niets per ongeluk verschuift.",
    "Locked: pads only fire. Click to edit the wall.":
        "Vergrendeld: pads spelen alleen af. Klik om de wand te bewerken.",
    "🎛 Cartwall shown": "🎛 Cartwall getoond",
    "🎛 Cartwall hidden": "🎛 Cartwall verborgen",
    "✏️ Editing highlights — playback paused; scrub to a crash, ⏯ to listen, 🎯 sets a mark at the playhead.":
        "✏️ Hoogtepunten bewerken — afspelen gepauzeerd; spoel naar een klap, ⏯ om te luisteren, 🎯 zet een markering op de afspeelpositie.",
    "✔ Highlights armed — playback pauses at the stop once so you can check it.":
        "✔ Hoogtepunten scherp — het afspelen houdt één keer stil bij de stop, zodat je hem kunt controleren.",
    "🖥 The presenter's screen was disconnected — it opens again when the screen is back.":
        "🖥 Het scherm van de presentatie is losgekoppeld — ze opent weer zodra het scherm terug is.",
    "⏹ The next title was removed during the pause — nothing was started.":
        "⏹ De volgende titel is tijdens de pauze verwijderd — er is niets gestart.",
    "✔  Done editing": "✔  Klaar met bewerken",
    "No pause to jump to — tick 'Pause between songs' (and ⏭\n"
    "auto-advance) in the Playing-mode panel first.":
        "Geen pauze om naar te springen — vink eerst ‘Pauze tussen nummers’ (en ⏭\n"
        "automatisch doorgaan) aan in het afspeelmoduspaneel.",
    "duck": "zachter",
    "instrumental (🎙️ Demucs-measured)":
        "instrumentaal (🎙️ gemeten met Demucs)",
    "instrumental (🎙️ audio-detected)":
        "instrumentaal (🎙️ herkend aan de audio)",
    "🎄 Christmas": "🎄 Kerst",
    "Similarity": "Gelijkenis",
    "Match": "Overeenkomst",
    "Played together": "Samen gespeeld",
    "Classes: %s": "Klassen: %s",
    "In these matching past lists:": "In deze passende eerdere lijsten:",
    "… +%d more": "… +%d meer",
    "In %d of your playlists": "In %d van je afspeellijsten",
    "Played in: %s": "Gespeeld in: %s",
    "▶ This list is playing: this switch decides what follows the title.":
        "▶ Deze lijst speelt nu: deze schakelaar bepaalt wat er na de titel komt.",
    "in the archive since %s": "in het archief sinds %s",
    "%s, sounds like %s (%d%%)": "%s, klinkt als %s (%d%%)",
    "%s, sounds like %s (%s)": "%s, klinkt als %s (%s)",
    "sounds like '%s' of the first heat (%s)":
        "klinkt als ‘%s’ uit de eerste heat (%s)",
    "sounds like '%s' of the first heat": "klinkt als ‘%s’ uit de eerste heat",
    "timbre top %d %%": "klankkleur top %d %%",
    "melody top %d %%": "melodie top %d %%",
    "played %d× at the class": "%d× gespeeld in de klasse",
    "never played at the class": "nooit gespeeld in de klasse",
    "a version of %s, played %d× at the class":
        "een versie van %s — het origineel liep %d× in de klasse",
    "a version of %s, never played at the class":
        "een versie van %s — het origineel liep nooit in de klasse",
    "Titles to choose from": "Titels om uit te kiezen",
    "%d from this event's past years, %d from other events' lists of the class, %d new in the archive, %d rarely played at the class (new ones included)":
        "%d uit eerdere jaren van dit evenement, %d uit lijsten van de klasse bij andere evenementen, %d nieuw in het archief, %d zelden gespeeld in de klasse (nieuwe meegeteld)",
    "🏆  Event — a whole day of competitions, planned from its history":
        "🏆  Evenement — een hele dag wedstrijden, gepland uit de eigen geschiedenis",
    "Paste the event's schedule. Every competition gets up to three\n"
    "variants, drawn from the event's earlier editions, the class's\n"
    "lists at other events and titles that sound like those.":
        "Plak het schema van het evenement. Elke wedstrijd krijgt tot drie\n"
        "varianten, uit eerdere edities van het evenement, de lijsten van de klasse\n"
        "bij andere evenementen en titels die daarop lijken.",
    "Paste the event's schedule, one competition per line:\n"
    "\n"
    "Sa: 10:00 HGR S STD 3-2-1\n"
    "So: 14:00 SEN I S STD (24) 2-1\n"
    "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6":
        "Plak het schema van het evenement, één wedstrijd per regel:\n"
        "\n"
        "Sa: 10:00 HGR S STD 3-2-1\n"
        "So: 14:00 SEN I S STD (24) 2-1\n"
        "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6",
    "Competition": "Wedstrijd",
    "Dances": "Dansen",
    "Heats per round": "Heats per ronde",
    "What was read from the schedule. Double-click a cell to correct\n"
    "it — the class (S, A … D), the dance codes, the heats per round.":
        "Wat uit het schema is gelezen. Dubbelklik op een cel om die te\n"
        "corrigeren — de klasse (S, A … D), de danscodes, de heats per ronde.",
    "Event:": "Evenement:",
    "%d editions": "%d edities",
    "The event whose earlier editions are its history — the folders\n"
    "of that name in the playlist folder, whatever the year.":
        "Het evenement waarvan de eerdere edities de geschiedenis vormen — de mappen\n"
        "met die naam in de afspeellijstmap, uit welk jaar ook.",
    "Year planned:": "Gepland jaar:",
    "Editions of this year and later are not used as history.":
        "Edities van dit jaar en later tellen niet als geschiedenis.",
    "Earlier editions of the event": "Eerdere edities van het evenement",
    "Lists of the same class from other events":
        "Lijsten van dezelfde klasse bij andere evenementen",
    "New titles:": "Nieuwe titels:",
    "How much of a variant may be titles that came into the archive in\n"
    "the last 18 months and were never played at the class. \"Like last\n"
    "year\" takes none — it offers them as replacements instead.":
        "Hoeveel van een variant mag bestaan uit titels die in de laatste 18 maanden\n"
        "in het archief kwamen en nooit in de klasse zijn gespeeld. ‘Zoals vorig\n"
        "jaar’ neemt er geen — het biedt ze in plaats daarvan als vervanging aan.",
    "Rarely played:": "Zelden gespeeld:",
    "How much of a variant may be titles played at most twice at the\n"
    "class so far, new ones included, the ones that sound like the\n"
    "played ones first. \"Like last year\" takes none.":
        "Hoeveel van een variant mag bestaan uit titels die tot nu toe hoogstens\n"
        "twee keer in de klasse zijn gespeeld, nieuwe meegeteld — die als de\n"
        "gespeelde klinken eerst. ‘Zoals vorig jaar’ neemt er geen.",
    "Variants:": "Varianten:",
    "Like last year": "Zoals vorig jaar",
    "Last year, renewed": "Vorig jaar, vernieuwd",
    "Proven + fresh": "Beproefd + vers",
    "Variety": "Afwisseling",
    "🤖  Let the AI check the drafts":
        "🤖  De AI de concepten laten controleren",
    "The model reads every draft and proposes swaps; each one is\n"
    "checked against the day before it goes in. Without it the\n"
    "computed plan is shown as it is.":
        "Het model leest elk concept en stelt wissels voor; elke wissel wordt\n"
        "tegen de dag gecontroleerd voordat hij erin gaat. Zonder AI wordt het\n"
        "berekende plan getoond zoals het is.",
    "Event plan": "Evenementplan",
    "No competition could be read from the schedule. Each line\n"
    "needs a class, a style (STD/LAT) or its dances in brackets,\n"
    "and the heats per round, e.g.  'HGR S STD 3-2-1'.":
        "Uit het schema kon geen wedstrijd worden gelezen. Elke regel\n"
        "heeft een klasse nodig, een stijl (STD/LAT) of de dansen tussen haakjes,\n"
        "en de heats per ronde, bijv.  ‘HGR S STD 3-2-1’.",
    "Tick at least one variant to plan.":
        "Vink minstens één variant aan om te plannen.",
    "no earlier edition found — the class lists carry the plan":
        "geen eerdere editie gevonden — de klassenlijsten dragen het plan",
    "not used": "niet gebruikt",
    "%d competitions. Earlier editions: %s":
        "%d wedstrijden. Eerdere edities: %s",
    "Asking again about: %s": "Opnieuw gevraagd naar: %s",
    "Event": "Evenement",
    "The plan": "Het plan",
    "🏆 Planning the event…": "🏆 Evenement plannen…",
    "🏆 %d competitions planned in %d variants":
        "🏆 %d wedstrijden gepland in %d varianten",
    "The AI's limit held back: %s\n"
    "\n"
    "%s\n"
    "\n"
    "Wait and ask again by itself in %d minutes?":
        "De limiet van de AI hield tegen: %s\n"
        "\n"
        "%s\n"
        "\n"
        "Wachten en over %d minuten zelf opnieuw vragen?",
    "🏆 Asking the AI again at %s": "🏆 De AI wordt om %s opnieuw gevraagd",
    "1 swap not applied, kept for your choice":
        "1 wissel niet toegepast, bewaard voor jouw keuze",
    "%d swaps not applied, kept for your choice":
        "%d wissels niet toegepast, bewaard voor jouw keuze",
    "the AI could not check it — the plan stands":
        "de AI kon het niet controleren — het plan blijft staan",
    "held back by the AI's limit — ask again later":
        "tegengehouden door de limiet van de AI — vraag het later opnieuw",
    "🏆 Event plan": "🏆 Evenementplan",
    "🟦 This event's lists": "🟦 Lijsten van dit evenement",
    "🟩 The class lists": "🟩 De klassenlijsten",
    "🟨 New titles": "🟨 Nieuwe titels",
    "🟧 Rarely played": "🟧 Zelden gespeeld",
    "⬜ Library": "⬜ Bibliotheek",
    "↺ Replaces '%s' of last year — %s": "↺ Vervangt ‘%s’ van vorig jaar — %s",
    "↻ Suggested instead: %s — %s": "↻ In plaats daarvan voorgesteld: %s — %s",
    "✋ The AI wanted '%s': %s": "✋ De AI wilde ‘%s’: %s",
    "⏳ Ask about the held back now": "⏳ Nu naar het tegengehoudene vragen",
    "🔁 Second round": "🔁 Tweede ronde",
    "Ask the AI again where a swap was lost, to fill or improve those slots.":
        "De AI opnieuw vragen waar een wissel verloren ging, om die plekken te vullen of te verbeteren.",
    "The earlier editions had no list of this competition — 'like similar competitions' fills it from the class lists 🟩":
        "De eerdere edities hadden geen lijst van deze wedstrijd — ‘Zoals vergelijkbare wedstrijden’ vult hem uit de klassenlijsten 🟩",
    "Like similar competitions": "Zoals vergelijkbare wedstrijden",
    "The variant of the competition in front — each tab keeps its own, ✔ in its header; a click on a column header chooses it too":
        "De variant van de wedstrijd vooraan — elk tabblad houdt de zijne, ✔ in de kop; een klik op een kolomkop kiest hem ook",
    "Drag a title onto the same dance in another variant to take it over there, within its variant to swap the two":
        "Sleep een titel op dezelfde dans in een andere variant om hem daar over te nemen, binnen zijn variant om de twee te wisselen",
    "'%s' ⇄ '%s': %s.\n"
    "\n"
    "Swap anyway?":
        "‘%s’ ⇄ ‘%s’: %s.\n"
        "\n"
        "Toch wisselen?",
    "▶ A title's ▶ or Space plays it, again stops it; Ctrl+click in the menu one to choose from":
        "▶ Het ▶ van een titel of Spatie speelt hem, nog eens stopt hem; Ctrl+klik in het menu een om uit te kiezen",
    "📅 Into the tournament-day decks": "📅 Naar de toernooidag-decks",
    "🏆  Open the last plan": "🏆  Het laatste plan openen",
    "Show the last event plan side by side again, as you left it —\n"
    "nothing is planned or asked anew.":
        "Toont het laatste evenementplan weer naast elkaar, zoals je het verliet —\n"
        "er wordt niets opnieuw gepland of gevraagd.",
    "⏳ Held back by the AI's limit: %s":
        "⏳ Tegengehouden door de limiet van de AI: %s",
    "⚠ The AI could not check: %s — the plan stands":
        "⚠ De AI kon niet controleren: %s — het plan blijft staan",
    "🔁 A swap was lost at: %s — a second round can fill or improve those slots":
        "🔁 Een wissel ging verloren bij: %s — een tweede ronde kan die plekken vullen of verbeteren",
    "Double-click or right-click a title for what else fits there.  🟦 event  🟩 class lists  🟨 new  🟧 rarely played  ⬜ library  ↺ replaces last year's title  ↻ a replacement is offered  ✋ the AI wanted another":
        "Dubbel- of rechtsklik op een titel om te zien wat daar nog meer past.  🟦 evenement  🟩 klassenlijsten  🟨 nieuw  🟧 zelden gespeeld  ⬜ bibliotheek  ↺ vervangt de titel van vorig jaar  ↻ er wordt een vervanging aangeboden  ✋ de AI wilde een andere",
    "'Last year, renewed' found no sound-alike to swap here — the same as 'Like last year'":
        "‘Vorig jaar, vernieuwd’ vond hier niets dat erop lijkt om te wisselen — hetzelfde als ‘Zoals vorig jaar’",
    "↺ Back to last year: %s": "↺ Terug naar vorig jaar: %s",
    "↻ Take the suggestion: %s": "↻ Het voorstel overnemen: %s",
    "✋ The AI wanted: %s (%s)": "✋ De AI wilde: %s (%s)",
    "'%s' %s.\n"
    "\n"
    "Put it in anyway?":
        "‘%s’ %s.\n"
        "\n"
        "Toch plaatsen?",
    "🏆  %s: %d competitions into %d deck(s)":
        "🏆  %s: %d wedstrijden in %d deck(s)",
    "already plays that day": "speelt die dag al",
    "already plays in that round": "speelt al in die ronde",
    "is offered for another slot": "is voorgesteld voor een andere plek",
    "too many swaps": "te veel wissels",
    "that slot is swapped already": "die plek is al gewisseld",
    "📦 Venue pack": "📦 Zaalpakket",
    "Take this desk to another PC in one file: the settings, every deck "
    "and wishlist, the 🎛 cartwall with its pads and keys — and, if you "
    "want, the music they use. Folder settings stay with each PC.":
        "Deze tafel in één bestand meenemen naar een andere pc: de instellingen, "
        "elk deck en elke wensenlijst, de 🎛 Cartwall met pads en toetsen — en, "
        "als je wilt, de muziek die ze gebruiken. Mapinstellingen blijven bij elke pc.",
    "📦  Export venue pack…": "📦  Zaalpakket exporteren…",
    "📥  Import venue pack…": "📥  Zaalpakket importeren…",
    "Save this desk to one file to take to another PC: the settings,\n"
    "every deck and wishlist, the 🎛 cartwall with its pads and keys —\n"
    "and, if you want, the music they use. Folder settings stay with\n"
    "each PC.":
        "Bewaar deze tafel in één bestand om mee te nemen naar een andere pc: de\n"
        "instellingen, elk deck en elke wensenlijst, de 🎛 Cartwall met pads en toetsen —\n"
        "en, als je wilt, de muziek die ze gebruiken. Mapinstellingen blijven bij\n"
        "elke pc.",
    "Load a venue pack made on another PC. It replaces this PC's\n"
    "settings, decks and cartwall at the next start; what it replaces\n"
    "is kept in a before-venue-import folder next to them.":
        "Een zaalpakket laden dat op een andere pc is gemaakt. Het vervangt bij de\n"
        "volgende start de instellingen, decks en Cartwall van deze pc; wat het vervangt\n"
        "blijft bewaard in een map before-venue-import ernaast.",
    "Export venue pack": "Zaalpakket exporteren",
    "Import venue pack": "Zaalpakket importeren",
    "Include the music files?\n"
    "\n"
    "Yes: the %d track(s) the decks and the cartwall use go into the pack too (%s MB) — the other PC needs nothing else.\n"
    "No: settings, decks and cartwall only — the other PC has the music already.":
        "De muziekbestanden meenemen?\n"
        "\n"
        "Ja: de %d nummer(s) die de decks en de Cartwall gebruiken gaan ook in het pakket (%s MB) — de andere pc heeft verder niets nodig.\n"
        "Nee: alleen instellingen, decks en Cartwall — de andere pc heeft de muziek al.",
    "Venue packs": "Zaalpakketten",
    "📦 Writing the venue pack…": "📦 Zaalpakket schrijven…",
    "📥 Unpacking the venue pack…": "📥 Zaalpakket uitpakken…",
    "All files": "Alle bestanden",
    "📦 Venue pack cancelled — nothing was written.":
        "📦 Zaalpakket afgebroken — er is niets geschreven.",
    "📦 Venue pack saved to:\n"
    "%s":
        "📦 Zaalpakket opgeslagen in:\n"
        "%s",
    "%d track(s) included.": "%d nummer(s) meegenomen.",
    "⚠ %d track(s) were missing on disk and are not in the pack.":
        "⚠ %d nummer(s) ontbraken op de schijf en zitten niet in het pakket.",
    "This is no venue pack:": "Dit is geen zaalpakket:",
    "The pack carries %d music file(s).\n"
    "\n"
    "Yes: unpack them into a folder of this PC — the decks and the cartwall then play them from there.\n"
    "No: leave them in the pack — this PC has the music already (🧭 Fix paths finds it if it lives elsewhere).":
        "Het pakket bevat %d muziekbestand(en).\n"
        "\n"
        "Ja: uitpakken in een map op deze pc — de decks en de Cartwall spelen ze dan vanaf daar.\n"
        "Nee: in het pakket laten — deze pc heeft de muziek al (🧭 Paden herstellen vindt hem als hij ergens anders staat).",
    "Folder for the venue pack's music":
        "Map voor de muziek van het zaalpakket",
    "📥 Venue pack import cancelled.":
        "📥 Import van het zaalpakket afgebroken.",
    "The import did not run:": "De import is niet uitgevoerd:",
    "The venue pack takes over at the next start: settings, decks and cartwall are replaced then, and what they replace is kept in a before-venue-import folder.\n"
    "\n"
    "Anything you change before that is lost.\n"
    "\n"
    "Restart now?":
        "Het zaalpakket neemt het over bij de volgende start: dan worden instellingen, decks en Cartwall vervangen, en wat ze vervangen blijft bewaard in een map before-venue-import.\n"
        "\n"
        "Wat je daarvoor nog verandert, gaat verloren.\n"
        "\n"
        "Nu opnieuw starten?",
    "Play, skip, fade and fire pads from a phone's browser on this network — no app to install. The server's window shows the address, a QR code that logs the phone in, and the PIN.":
        "Afspelen, overslaan, uitfaden en pads afvuren vanuit de browser van een telefoon in dit netwerk — geen app te installeren. Het venster van de server toont het adres, een QR-code die de telefoon aanmeldt, en de pincode.",
    "📱  Start Server": "📱  Server starten",
    "📱  Stop Server": "📱  Server stoppen",
    "Stops the phone remote's server — connected phones lose the remote.":
        "Stopt de server van de telefoonbediening — verbonden telefoons verliezen de bediening.",
    "The phone remote's server is running — click for its window.":
        "De server van de telefoonbediening draait — klik voor zijn venster.",
    "Starts the server and opens its window — stop it there again.\n"
    "\n"
    "Only phones on the same network get in, and only with the PIN;\n"
    "wrong PINs lock the phone out for a while.\n"
    "Windows may ask once whether the app may use the network —\n"
    "allow it for private networks.":
        "Start de server en opent zijn venster — daar stop je hem ook weer.\n"
        "\n"
        "Alleen telefoons in hetzelfde netwerk komen erin, en alleen met de pincode;\n"
        "verkeerde pincodes sluiten de telefoon een tijdje buiten.\n"
        "Windows vraagt misschien één keer of de app het netwerk mag gebruiken —\n"
        "sta het toe voor privénetwerken.",
    "New PIN": "Nieuwe pincode",
    "Make up a new PIN — phones that know the old one have to enter it again.":
        "Een nieuwe pincode bedenken — telefoons die de oude kennen, moeten hem opnieuw invoeren.",
    "📱 The phone remote could not start: %s":
        "📱 De telefoonbediening kon niet starten: %s",
    "📱 Phone remote on — open %s on the phone, PIN %s":
        "📱 Telefoonbediening aan — open %s op de telefoon, pincode %s",
    "📱  Phone remote": "📱  Telefoonbediening",
    "📱  Phone remote…": "📱  Telefoonbediening…",
    "Play, skip, fade and fire pads from a phone's browser on this\n"
    "network — no app to install. Opens the window to start the\n"
    "server, with a QR code that logs the phone in and a log of what\n"
    "reached it.":
        "Afspelen, overslaan, uitfaden en pads afvuren vanuit de browser van een\n"
        "telefoon in dit netwerk — geen app te installeren. Opent het venster dat\n"
        "de server start, met een QR-code die de telefoon aanmeldt en een log van\n"
        "wat er binnenkwam.",
    "Scan the code with the phone's camera — it opens the remote, logged in. Or type the address:":
        "Scan de code met de camera van de telefoon — die opent de bediening, al aangemeld. Of typ het adres:",
    "This PC is on more than one network. The first one is the way to\n"
    "the internet, usually the Wi-Fi the phone is on as well.":
        "Deze pc zit in meer dan één netwerk. Het eerste is de weg naar\n"
        "het internet, meestal de wifi waar de telefoon ook op zit.",
    "Opens the remote in this PC's browser — a quick test that the server answers.":
        "Opent de bediening in de browser van deze pc — een snelle test of de server antwoordt.",
    "Nothing turns up in the log when the phone tries? Then a firewall on this PC drops it: allow the program below for private networks (Windows Defender Firewall, or your security suite's own, e.g. Norton → Firewall → Program Control). The phone must be on the same Wi-Fi.%s":
        "Verschijnt er niets in de log als de telefoon het probeert? Dan gooit een firewall op deze pc het weg: sta het programma hieronder toe voor privénetwerken (Windows Defender Firewall, of die van je beveiligingspakket, bijv. Norton → Firewall → Programmabeheer). De telefoon moet op dezelfde wifi zitten.%s",
    "● Running — port %d": "● Draait — poort %d",
    "○ Stopped": "○ Gestopt",
    "■  Stop": "■  Stoppen",
    "▶  Start": "▶  Starten",
    "No network found — is this PC on the Wi-Fi?":
        "Geen netwerk gevonden — zit deze pc op de wifi?",
    "Press Start — the code to scan shows up here.":
        "Druk op Starten — dan verschijnt hier de code om te scannen.",
    "No QR code: the segno package is missing. Type the address instead.":
        "Geen QR-code: het pakket segno ontbreekt. Typ in plaats daarvan het adres.",
    "▶ Server started on port %(detail)s":
        "▶ Server gestart op poort %(detail)s",
    "■ Server stopped": "■ Server gestopt",
    "%(ip)s opened the page": "%(ip)s heeft de pagina geopend",
    "✔ %(ip)s logged in with the PIN":
        "✔ %(ip)s heeft zich aangemeld met de pincode",
    "✖ %(ip)s sent a wrong PIN": "✖ %(ip)s stuurde een verkeerde pincode",
    "⛔ %(ip)s locked out for %(detail)s s — too many wrong PINs":
        "⛔ %(ip)s %(detail)s s buitengesloten — te veel verkeerde pincodes",
    "⛔ New phones paused for %(detail)s s — too many wrong PINs from the network":
        "⛔ Nieuwe telefoons %(detail)s s gepauzeerd — te veel verkeerde pincodes uit het netwerk",
    "⛔ %(ip)s refused — not on the local network":
        "⛔ %(ip)s geweigerd — niet in het lokale netwerk",
    "⚠ Could not start: %(detail)s": "⚠ Kon niet starten: %(detail)s",
    "DancePlaylist remote": "DancePlaylist-bediening",
    "Connect": "Verbinden",
    "Wrong PIN": "Verkeerde pincode",
    "Too many wrong PINs — wait a minute":
        "Te veel verkeerde pincodes — wacht even",
    "No connection to the desk": "Geen verbinding met de tafel",
    "Nothing is playing": "Er speelt niets",
    "Stop all pads": "Alle pads stoppen",
    "Next": "Volgende",
    "Fade & hold": "Uitfaden & vasthouden",
    "Announce next dance": "Volgende dans aankondigen",
    "Menus, buttons and dialogs are in Spanish. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Menu's, knoppen en dialogen in het Spaans. Dansen en rondes houden hun internationale Engelse namen; titels en alles wat uit je bestanden wordt gelezen blijven zoals ze zijn.",
    "Menus, buttons and dialogs are in Dutch. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Menu's, knoppen en dialogen in het Nederlands. Dansen en rondes houden hun internationale Engelse namen; titels en alles wat uit je bestanden wordt gelezen blijven zoals ze zijn.",
    "Menus, buttons and dialogs are in Russian. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Menu's, knoppen en dialogen in het Russisch. Dansen en rondes houden hun internationale Engelse namen; titels en alles wat uit je bestanden wordt gelezen blijven zoals ze zijn.",
    'Play, skip, fade, set the volume and fire cartwall pads from a USB MIDI controller (e.g. Korg nanoKONTROL2) or a HID one (e.g. a Traktor controller in its native mode). Pick the device, load a profile or click Learn and press the button that should do it.':
        'Afspelen, overslaan, uitfaden, het volume instellen en cartwall-pads afvuren vanaf een USB-MIDI-controller (bijv. Korg nanoKONTROL2) of een HID-controller (bijv. een Traktor-controller in zijn eigen modus). Kies het apparaat, laad een profiel of klik op Aanleren en druk op de knop die het moet doen.',
    '— none —':
        '— geen —',
    'Device:':
        'Apparaat:',
    'Look for devices again':
        'Opnieuw naar apparaten zoeken',
    'Show all HID devices, not only DJ controllers':
        'Alle HID-apparaten tonen, niet alleen DJ-controllers',
    '📂  Load profile…':
        '📂  Profiel laden…',
    '💾  Save profile…':
        '💾  Profiel opslaan…',
    'Control':
        'Bedieningselement',
    'Learn':
        'Aanleren',
    'Unbind this action':
        'Toewijzing verwijderen',
    '%s — not plugged in':
        '%s — niet aangesloten',
    '● Connected — %s':
        '● Verbonden — %s',
    '○ Not connected — %s':
        '○ Niet verbonden — %s',
    'No controller chosen.':
        'Geen controller gekozen.',
    'Profile: %s':
        'Profiel: %s',
    'own':
        'eigen',
    'Press or move a control…':
        'Druk op of beweeg een element…',
    'Load controller profile':
        'Controllerprofiel laden',
    'Controller profiles (*.json)':
        'Controllerprofielen (*.json)',
    'This file is not a controller profile:\n%s':
        'Dit bestand is geen controllerprofiel:\n%s',
    'Save controller profile':
        'Controllerprofiel opslaan',
    'Could not save the profile:\n%s':
        'Kon het profiel niet opslaan:\n%s',
    'not bound':
        'niet toegewezen',
    'Last: %(control)s = %(value)d%% → %(action)s':
        'Laatst: %(control)s = %(value)d%% → %(action)s',
    '🎛  Cartwall pad %d':
        '🎛  Cartwall-pad %d',
    '⏯  Play / pause':
        '⏯  Afspelen / pauze',
    '⏭  Next title':
        '⏭  Volgende titel',
    '⏮  Previous title':
        '⏮  Vorige titel',
    '🔉↓  Fade out now':
        '🔉↓  Nu uitfaden',
    '🛑  Fade out and hold':
        '🛑  Uitfaden en vasthouden',
    '🔉  Duck the music on / off':
        '🔉  Muziek dempen aan / uit',
    '🔈  Announce the next dance on / off':
        '🔈  Volgende dans aankondigen aan / uit',
    '🔊  Music volume (fader or knob)':
        '🔊  Muziekvolume (fader of draaiknop)',
    '⏹  Stop all pads':
        '⏹  Alle pads stoppen',
    'Play, skip, fade, set the volume and fire cartwall pads from a USB MIDI or HID controller — a profile for the Korg nanoKONTROL2 is built in, any other is learned by pressing its buttons.':
        'Afspelen, overslaan, uitfaden, het volume instellen en cartwall-pads afvuren vanaf een USB-MIDI- of HID-controller — een profiel voor de Korg nanoKONTROL2 is ingebouwd, elke andere leer je aan door op zijn knoppen te drukken.',
    '🎛  Set up…':
        '🎛  Instellen…',
    # 🤸 the practice panel's own name
    "Practice": "Oefenen",
    "Practice / Party": "Oefenen / Feest",
    "🤸  Practice / Party": "🤸  Oefenen / Feest",
    "🤸  Practice / Party ▾": "🤸  Oefenen / Feest ▾",
}
