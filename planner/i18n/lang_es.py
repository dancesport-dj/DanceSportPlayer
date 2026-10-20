"""Spanish chrome, keyed by the English string as it stands in the code.

Built against planner/i18n/lang_de.py, which holds the full key set and the rules
(keys copied character for character, the emoji stays, only chrome). A key
missing here falls back to English on its own.

Vocabulary: tú throughout. Heat = grupo, Round = ronda, Playlist = lista,
Track = tema (título for a title), Settings = Ajustes, Reference path =
ruta de referencia, Practice = práctica. Deck, Cartwall and Pad are left as
they are; dances and rounds keep their international English names.
"""

CATALOG = {
    "Cancel": "Cancelar",
    "Nb.": "N.º",
    "none": "ninguno",
    "e.g. 6-3-2-1": "p. ej. 6-3-2-1",
    "Group A–D": "Grupo A–D",
    "Group E–H": "Grupo E–H",
    "Preview-player options": "Opciones del reproductor de vista previa",
    "Fade every running pad out (Esc)": "Fundir todos los pads en curso (Esc)",
    "Fade between music and timetable every":
        "Alternar entre música y horario cada",
    "    Only tracks not already in my open playlists":
        "    Solo temas que aún no están en mis listas abiertas",
    "Close": "Cerrar",
    "Replace": "Reemplazar",
    "Reset": "Restablecer",
    "Generate": "Generar",
    "Parse": "Leer",
    "Colour": "Color",
    "Label": "Etiqueta",
    "Heading": "Encabezado",
    "A new line at the end": "Una línea nueva al final",
    "Take the selected line out": "Quitar la línea seleccionada",
    "Move the selected line up": "Subir la línea seleccionada",
    "Move the selected line down": "Bajar la línea seleccionada",
    "Shortcut": "Atajo",
    "Class": "Clase",
    "Class:": "Clase:",
    "Style:": "Estilo:",
    "Method:": "Método:",
    "Model:": "Modelo:",
    "Count:": "Cantidad:",
    "Context:": "Contexto:",
    "Volume": "Volumen",
    "Master volume": "Volumen general",
    "Fade out": "Fundido de salida",
    "within the length": "dentro de la duración",
    "Ticked: the fade-out ends at the play length.\n"
    "Unticked: the title plays its full length, then fades out.":
        "Marcado: el fundido de salida termina con la duración.\n"
        "Sin marcar: el título suena toda la duración y luego se funde.",
    "fade-out → within the length": "fundido de salida → dentro de la duración",
    "fade-out → after the length": "fundido de salida → después de la duración",
    "Fade-out:": "Fundido de salida:",
    "Own fade-out": "Fundido propio",
    "Wall fade-out": "Fundido de la Cartwall",
    "Play length:": "Duración:",
    "Start after:": "Empezar tras:",
    "Stop after highlight:": "Parar tras el clímax:",
    "Max tracks:": "Máx. temas:",
    "Proven": "Probados",
    "Top Proven": "Los más probados",
    "Fresh": "Nuevos",
    "Mostly Proven": "Sobre todo probados",
    "Even Mix": "Mezcla equilibrada",
    "Songs you have played before (fresh as fallback).":
        "Temas que ya has puesto antes (nuevos como reserva).",
    "Only your most-played songs.": "Solo tus temas más puestos.",
    "Unused songs first (proven as fallback).":
        "Primero temas sin usar (probados como reserva).",
    "Proven + fresh together, but favors songs you have played before.":
        "Probados + nuevos juntos, pero prefiere temas que ya has puesto.",
    "Proven + fresh with no preference — equal chance, maximum variety.":
        "Probados + nuevos sin preferencia — misma probabilidad, máxima variedad.",
    "🌐  Search mode: Global — whole repository":
        "🌐  Modo de búsqueda: Global — todo el repositorio",
    "🎯  Search mode: Favorites library only":
        "🎯  Modo de búsqueda: solo la biblioteca de favoritos",
    "Library: %d files": "Biblioteca: %d archivos",
    "Favorites: %d": "Favoritos: %d",
    "Library loaded — %s MP3 files, %s favorites songs, %s audio cached.":
        "Biblioteca cargada — %s archivos MP3, %s temas favoritos, %s en la caché de audio.",
    "— Indexes (analyzed / total) —": "— Índices (analizados / total) —",
    "🔗 Fingerprints: %s": "🔗 Huellas: %s",
    "📊 Loudness: %s": "📊 Sonoridad: %s",
    "🔇 Silences: %s": "🔇 Silencios: %s",
    "🐂 PD highlights: %s": "🐂 Clímax de PD: %s",
    "🎙️ Demucs vocals: %s measured": "🎙️ Voces Demucs: %s medidos",
    "🌐 Global index: %s files, %s analyzed":
        "🌐 Índice global: %s archivos, %s analizados",
    "🌐 Global index: %s files built (loads on first global search)":
        "🌐 Índice global: %s archivos construidos (se carga en la primera búsqueda global)",
    "🌐 Global index: not built (⚙ Settings to build)":
        "🌐 Índice global: sin construir (⚙ Ajustes para construirlo)",
    "(MERT not available)": "(MERT no disponible)",
    "(chroma not available)": "(Chroma no disponible)",
    "no Paso Doble in the library": "no hay Paso Doble en la biblioteca",
    "%s file(s) in the favorites library have no\n"
    "analysis yet":
        "%s archivo(s) de la biblioteca de favoritos aún\n"
        "sin analizar",
    "an index of the favorites library is not complete yet":
        "un índice de la biblioteca de favoritos aún no está completo",
    "🧱 Build ALL caches — %s. Asks for the scope\n"
    "first; reuses everything already cached and can be cancelled.":
        "🧱 Construir TODAS las cachés — %s. Pregunta primero por el\n"
        "alcance; reutiliza todo lo que ya está en caché y se puede cancelar.",
    "audio fingerprints": "huellas de audio",
    "loudness": "sonoridad",
    "silences": "silencios",
    "PD highlights": "clímax de PD",
    "librosa audio analysis (no working audio decoder)":
        "análisis de audio librosa (ningún decodificador de audio funciona)",
    "loudness + silences (no ffmpeg)": "sonoridad + silencios (sin ffmpeg)",
    "%s (not installed)": "%s (no instalado)",
    "\n"
    "\n"
    "Skipped: %s":
        "\n"
        "\n"
        "Omitido: %s",
    "Nothing can be built on this machine right now.":
        "Ahora mismo no se puede construir nada en este equipo.",
    "Build every index over %s tracks from %s?":
        "¿Construir todos los índices sobre %s temas de %s?",
    "Runs %s back-to-back. Each is slow the first time, then cached; reuses anything already built. You can cancel between or within steps.":
        "Ejecuta %s uno tras otro. Cada uno es lento la primera vez y luego queda en caché; reutiliza todo lo ya construido. Puedes cancelar entre pasos o durante uno.",
    "Read-only — your audio files are never modified.":
        "Solo lectura — tus archivos de audio nunca se modifican.",
    "the favorites library": "la biblioteca de favoritos",
    "the whole repository": "todo el repositorio",
    "the whole repository + favorites library":
        "todo el repositorio + la biblioteca de favoritos",
    "All %s files in %s are already analyzed.":
        "Los %s archivos de %s ya están analizados.",
    "%s of %s files in %s need analysis (~%s min).\n"
    "\n"
    "Analysis only reads your files — never modifies them. Results are cached.\n"
    "\n"
    "Run now?":
        "%s de %s archivos de %s necesitan análisis (~%s min).\n"
        "\n"
        "El análisis solo lee tus archivos — nunca los modifica. Los resultados se guardan en caché.\n"
        "\n"
        "¿Empezar ahora?",
    "Audio index: analyzing %s files…":
        "Índice de audio: analizando %s archivos…",
    "Building audio index (%s)…": "Construyendo el índice de audio (%s)…",
    "Global index: %s/%s%s": "Índice global: %s/%s%s",
    "  (%s errors)": "  (%s errores)",
    " (%s errors)": " (%s errores)",
    "Audio index built — %s files analyzed":
        "Índice de audio construido — %s archivos analizados",
    "Analyzed %s files in %s": "%s archivos analizados en %s",
    ".\n"
    "Similarity search will now match across them.":
        ".\n"
        "La búsqueda de similares ahora compara entre todos ellos.",
    "Audio index cancelled — %s files analyzed so far (progress is cached).":
        "Índice de audio cancelado — %s archivos analizados hasta ahora (el progreso queda en caché).",
    "🧹  Checking which files are still on disk…":
        "🧹  Comprobando qué archivos siguen en el disco…",
    "🧱  Looking for ffmpeg and the AI backends…":
        "🧱  Buscando ffmpeg y los motores de IA…",
    "🧱  Checking what this machine can build…":
        "🧱  Comprobando qué puede construir este equipo…",
    "librosa is not installed, so tempo and timbre cannot be measured and similar-track search stays unavailable.\n"
    "\n"
    "Install it, then restart the app:\n"
    "    pip install librosa":
        "librosa no está instalado, así que no se pueden medir el tempo ni el timbre y la búsqueda de temas similares no está disponible.\n"
        "\n"
        "Instálalo y reinicia la app:\n"
        "    pip install librosa",
    "Nothing on this computer can decode an MP3, so tempo and timbre cannot be measured and similar-track search stays unavailable.\n"
    "\n"
    "Install ffmpeg and make sure it is on PATH (not just next to the app), then restart.":
        "Nada en este equipo puede decodificar un MP3, así que no se pueden medir el tempo ni el timbre y la búsqueda de temas similares no está disponible.\n"
        "\n"
        "Instala ffmpeg y asegúrate de que esté en el PATH (no solo junto a la app), luego reinicia.",
    "The audio decoder could not read %s, so the analysis would fail for every file. See the log for the error.":
        "El decodificador de audio no pudo leer %s, así que el análisis fallaría con cada archivo. El error está en el registro.",
    "Nothing could be built for these, and nothing will be:":
        "Para estos no se pudo construir nada, y no se podrá:",
    "Caches built for %s — with problems, see the log.":
        "Cachés construidas para %s — con problemas, mira el registro.",
    "Finished for %s, but not everything worked:":
        "Terminado para %s, pero no todo funcionó:",
    "Ran: %s.": "Ejecutado: %s.",
    "All caches built for %s.": "Todas las cachés construidas para %s.",
    "All caches are built for %s.":
        "Todas las cachés están construidas para %s.",
    "Build all caches — librosa: analyzing %s files…":
        "Construir todas las cachés — librosa: analizando %s archivos…",
    "Build all caches — %s…": "Construir todas las cachés — %s…",
    "Build all caches — %s embeddings…":
        "Construir todas las cachés — embeddings de %s…",
    "mostly: %s": "sobre todo: %s",
    "%s: %s file(s) failed": "%s: %s archivo(s) fallaron",
    ", %s cached": ", %s en caché",
    "%s: %s file(s) skipped — not on disk any more":
        "%s: %s archivo(s) omitidos — ya no están en el disco",
    "Build all caches cancelled during %s — %s done so far (cached).":
        "Construcción de cachés cancelada durante %s — %s hechos hasta ahora (en caché).",
    "🎛  Both — plan and play": "🎛  Ambos — planificar y reproducir",
    "The full app: build playlists at home, run them at the tournament.":
        "La app completa: crea las listas en casa y ponlas en el torneo.",
    "📝  Planner only": "📝  Solo planificador",
    "Build and curate playlists. The tournament floor's playing panel, its timed play / announcements and the 🎛 cartwall stay hidden.":
        "Crear y cuidar listas. El panel de reproducción de la pista del torneo, su reproducción temporizada / anuncios y la 🎛 Cartwall quedan ocultos.",
    "▶  Player only": "▶  Solo reproductor",
    "Run prepared playlists at the venue. Everything that generates or checks a playlist stays hidden.":
        "Poner las listas preparadas en el lugar del evento. Todo lo que genera o comprueba una lista queda oculto.",
    "◧  Beside the playlists — at the head of the ▶ Playing panel":
        "◧  Junto a las listas — en la cabecera del panel ▶ Reproducción",
    "The player card stands in the left panel, above the timed-play controls.":
        "La tarjeta del reproductor está en el panel izquierdo, encima de los controles de reproducción temporizada.",
    "▤  Above the playlists — one wide strip over the decks":
        "▤  Encima de las listas — una franja ancha sobre los decks",
    "The same player, laid out along the width above the decks — the shape a DJ desk uses. It shows in ▶ Playing mode.":
        "El mismo reproductor, extendido a lo ancho encima de los decks — la forma de una mesa de DJ. Se muestra en el modo ▶ Reproducción.",
    "🎬  FFmpeg — Qt's own engine (default)":
        "🎬  FFmpeg — el motor propio de Qt (predeterminado)",
    "🎬  FFmpeg — Qt's own engine": "🎬  FFmpeg — el motor propio de Qt",
    "🪟  Windows Media Foundation — the OS's own":
        "🪟  Windows Media Foundation — el del sistema operativo",
    "🔊  Automatic — whatever this system uses (default)":
        "🔊  Automático — lo que use este sistema (predeterminado)",
    "☀  Light (default)": "☀  Claro (predeterminado)",
    "White decks, dark text: the look every colour in the app was picked for.":
        "Decks blancos, texto oscuro: el aspecto para el que se eligió cada color de la app.",
    "🌙  Dark": "🌙  Oscuro",
    "Platform looks": "Aspectos de plataforma",
    "Desk looks": "Aspectos de mesa",
    "Modern looks": "Aspectos modernos",
    "No preview picture for this theme.":
        "No hay imagen de vista previa para este tema.",
    "A look brings its own accent colour — this one is for Light and Dark.":
        "Un aspecto trae su propio color de acento — este es para Claro y Oscuro.",
    "Windows 11 · Light": "Windows 11 · Claro",
    "Fluent: 4 px corners, Segoe UI Variable, the Windows blue and an accent line under the active field.":
        "Fluent: esquinas de 4 px, Segoe UI Variable, el azul de Windows y una línea de acento bajo el campo activo.",
    "Windows 11 · Dark": "Windows 11 · Oscuro",
    "Fluent in dark: the Windows 11 dark greys with the light blue accent.":
        "Fluent en oscuro: los grises oscuros de Windows 11 con el acento azul claro.",
    "macOS · Light": "macOS · Claro",
    "Aqua as of Sonoma: 6 px corners, a solid blue selection with white text and an accent ring around the active field.":
        "Aqua como en Sonoma: esquinas de 6 px, una selección azul intensa con texto blanco y un anillo de acento alrededor del campo activo.",
    "macOS · Dark": "macOS · Oscuro",
    "Aqua in dark mode: charcoal panes, grey keys, the bright system blue.":
        "Aqua en modo oscuro: paneles antracita, teclas grises, el azul brillante del sistema.",
    "Linux GNOME · Light": "Linux GNOME · Claro",
    "Adwaita: 6 px corners, flat grey buttons without a frame, the GNOME blue.":
        "Adwaita: esquinas de 6 px, botones grises planos sin marco, el azul de GNOME.",
    "Linux GNOME · Dark": "Linux GNOME · Oscuro",
    "Adwaita dark: soft charcoal, flat buttons, the GNOME blue.":
        "Adwaita oscuro: antracita suave, botones planos, el azul de GNOME.",
    "Console": "Consola",
    "Graphite, keys lit from above like a mixing desk, a pressed key glows blue. Lettering in Bahnschrift.":
        "Grafito, teclas iluminadas desde arriba como en una mesa de mezclas, una tecla pulsada brilla en azul. Letra Bahnschrift.",
    "Jet black with metal gradients and orange as the light: harder and higher in contrast, like a hardware controller in a dark hall.":
        "Negro azabache con degradados metálicos y naranja como luz: más duro y con más contraste, como un controlador de hardware en una sala oscura.",
    "Flat night blue with cyan as the light: whatever is on gets a glowing rim instead of a fill. Rounder corners.":
        "Azul noche plano con cian como luz: lo que está encendido recibe un borde brillante en lugar de un relleno. Esquinas más redondas.",
    "The bright desk: brushed aluminium, keys lit from above, orange as the accent. For daylight and bright halls.":
        "La mesa clara: aluminio cepillado, teclas iluminadas desde arriba, naranja como acento. Para la luz del día y salas luminosas.",
    "Graphite": "Grafito",
    "Calm neutral dark: near-white text on graphite, soft filled buttons with round corners, a clear blue. Easy on the eyes for a long evening.":
        "Oscuro neutro y tranquilo: texto casi blanco sobre grafito, botones rellenos suaves con esquinas redondas, un azul claro. Descansa la vista en una noche larga.",
    "Midnight": "Medianoche",
    "Deep navy with a teal accent and pill-shaped buttons: modern and quiet, the text stays crisp against the dark blue.":
        "Azul marino profundo con acento verde azulado y botones en forma de píldora: moderno y tranquilo, el texto se mantiene nítido sobre el azul oscuro.",
    "Dark with a violet accent: soft filled buttons, warm dark greys, light lavender for links and focus.":
        "Oscuro con acento violeta: botones rellenos suaves, grises oscuros cálidos, lavanda claro para enlaces y foco.",
    "Paper": "Papel",
    "Clean and bright: white panes, nearly black text, soft grey buttons with round corners and a strong blue. Crisp in daylight.":
        "Limpio y claro: paneles blancos, texto casi negro, botones grises suaves con esquinas redondas y un azul intenso. Nítido a la luz del día.",
    "High contrast · Dark": "Alto contraste · Oscuro",
    "Black and white with a yellow accent, 2 px frames and a yellow selection: readable from across the hall and in bright stage light.":
        "Blanco y negro con acento amarillo, marcos de 2 px y selección amarilla: legible desde el otro lado de la sala y con luz de escenario intensa.",
    "High contrast · Light": "Alto contraste · Claro",
    "Black on white with a deep blue accent and 2 px frames: the most readable light look, also on a weak projector or laptop screen.":
        "Negro sobre blanco con acento azul profundo y marcos de 2 px: el aspecto claro más legible, también en un proyector débil o en la pantalla de un portátil.",
    "The same colours put through a lightness flip, so a warning stays red and the ▶ player panel — dark already — is left as it is.":
        "Los mismos colores pasados por una inversión de luminosidad, para que una advertencia siga roja y el panel del reproductor ▶ — ya oscuro — quede como está.",
    "  %s  —  pick a colour…": "  %s  —  elegir un color…",
    "Accent colour": "Color de acento",
    "  ~%s left": "  ~%s restantes",
    "(%s errors)": "(%s errores)",
    ", %s errors": ", %s errores",
    "%s done — %s %s": "%s terminado — %s %s",
    " (all were already cached)": " (todo estaba ya en caché)",
    "%s cancelled — %s %s so far.": "%s cancelado — %s %s hasta ahora.",
    "%s failed:\n"
    "%s":
        "%s falló:\n"
        "%s",
    "files cached": "archivos en caché",
    "tracks measured": "temas medidos",
    "tracks probed": "temas sondeados",
    "tracks analyzed": "temas analizados",
    "All %s files are already cached.\n"
    "\n"
    "Re-analyze the whole library anyway to refresh the measured tempo with the current method?":
        "Los %s archivos ya están en caché.\n"
        "\n"
        "¿Volver a analizar toda la biblioteca de todos modos para actualizar el tempo medido con el método actual?",
    "%s files will be re-analyzed (~%s min, cached afterwards).\n"
    "\n"
    "Run now?":
        "Se volverán a analizar %s archivos (~%s min, luego en caché).\n"
        "\n"
        "¿Empezar ahora?",
    "%s files need librosa analysis (~%s min, cached afterwards).\n"
    "\n"
    "Run now?":
        "%s archivos necesitan análisis con librosa (~%s min, luego en caché).\n"
        "\n"
        "¿Empezar ahora?",
    "Audio analysis started — %s files…":
        "Análisis de audio iniciado — %s archivos…",
    "Analyze Audio (Timbre)": "Analizar audio (timbre)",
    "Re-analyze All Audio": "Volver a analizar todo el audio",
    "Measure the loudness of the whole library (%s tracks)?\n"
    "\n"
    "Already-measured tracks are skipped — only new ones are\n"
    "decoded (≈1 s each). You can cancel anytime; results so far\n"
    "are kept.":
        "¿Medir la sonoridad de toda la biblioteca (%s temas)?\n"
        "\n"
        "Los temas ya medidos se omiten — solo se decodifican\n"
        "los nuevos (≈1 s cada uno). Puedes cancelar cuando quieras;\n"
        "los resultados obtenidos se conservan.",
    "Probe the silent stretches of the whole library (%s tracks, %s not probed yet)?\n"
    "\n"
    "Already-probed tracks are skipped — only new ones are\n"
    "decoded (≈0.3 s each). You can cancel anytime; results so far\n"
    "are kept.":
        "¿Sondear los tramos silenciosos de toda la biblioteca (%s temas, %s aún sin sondear)?\n"
        "\n"
        "Los temas ya sondeados se omiten — solo se decodifican\n"
        "los nuevos (≈0,3 s cada uno). Puedes cancelar cuando quieras;\n"
        "los resultados obtenidos se conservan.",
    "All %s tracks already have a measured vocal share.":
        "Los %s temas ya tienen una proporción de voz medida.",
    "Separate the vocals of %s not-yet-measured tracks (~%s min)?\n"
    "\n"
    "Demucs actually extracts the singing from each track — slow\n"
    "(~7 s per track) but far more reliable than the heuristics.\n"
    "You can cancel anytime; results so far are kept.":
        "¿Separar las voces de %s temas aún sin medir (~%s min)?\n"
        "\n"
        "Demucs extrae de verdad el canto de cada tema — lento\n"
        "(~7 s por tema) pero mucho más fiable que las heurísticas.\n"
        "Puedes cancelar cuando quieras; los resultados obtenidos se conservan.",
    "Detect the highlights of every Paso Doble in the library (%s tracks)?\n"
    "\n"
    "Already-analyzed tracks are skipped — only new ones are\n"
    "decoded (a few seconds each). You can cancel anytime;\n"
    "results so far are kept.":
        "¿Detectar los clímax de cada Paso Doble de la biblioteca (%s temas)?\n"
        "\n"
        "Los temas ya analizados se omiten — solo se decodifican\n"
        "los nuevos (unos segundos cada uno). Puedes cancelar cuando quieras;\n"
        "los resultados obtenidos se conservan.",
    "Fresh mix:": "Mezcla de nuevos:",
    "Pause music:": "Música de pausa:",
    "Pause music volume:": "Volumen de la música de pausa:",
    "No pause music": "Sin música de pausa",
    "Set clock to": "Poner el reloj a",
    "Draw tracks from": "Tomar temas de",
    "Songs needed for:": "Temas necesarios para:",
    "What to build": "Qué crear",
    "Round Strategy": "Estrategia de ronda",
    "Middle of the round": "Media de la ronda",
    "Lower — T%s": "Bajo — T%s",
    "Middle — T%s": "Medio — T%s",
    "Upper — T%s": "Alto — T%s",
    "Please wait": "Espera, por favor",
    "Failed.": "Falló.",
    "Add a page": "Añadir una página",
    "Next page": "Página siguiente",
    "Previous page": "Página anterior",
    "Keep all": "Conservar todos",
    "Keep both": "Conservar ambos",
    "Keep existing": "Conservar el existente",
    "No key": "Sin tecla",
    "Print / Export": "Imprimir / Exportar",
    "USB export": "Exportar a USB",
    "Duplicate titles": "Títulos duplicados",
    "Possible duplicate": "Posible duplicado",
    "Check duplicates": "Buscar duplicados",
    "Pad settings": "Ajustes del pad",
    "Clear this pad": "Vaciar este pad",
    "Columns in the library": "Columnas de la biblioteca",
    "Open wishlists": "Listas de deseos abiertas",
    "Analyze PD highlights": "Analizar clímax de PD",
    "Vocal + instr.": "Voz + instr.",
    "Use Timbre Similarity": "Usar similitud de timbre",
    "Load models": "Cargar modelos",
    "Copy to clipboard": "Copiar al portapapeles",
    "Press the keys you want": "Pulsa las teclas que quieras",
    "Click, then press the key that should do it": "Haz clic y pulsa la tecla que debe hacerlo",
    "Restore slot defaults": "Restaurar las teclas predeterminadas",
    "Back to %s…%s, leaving the pad keys alone":
        "Volver a %s…%s, sin tocar las teclas de los pads",
    "\n"
    "Key: %s":
        "\n"
        "Tecla: %s",
    "\n"
    "⚠️ File not found":
        "\n"
        "⚠️ Archivo no encontrado",
    "Remove this page": "Quitar esta página",
    "Remove this competition": "Quitar esta competición",
    "Save all playlists": "Guardar todas las listas",
    "Save tournament day": "Guardar el día de torneo",
    "Clear all tournament-day playlists":
        "Vaciar todas las listas del día de torneo",
    "All dances": "Todos los bailes",
    "All classes": "Todas las clases",
    "All categories": "Todas las categorías",
    "Added: all": "Añadidos: todos",
    "Plays: all": "Reproducidos: todos",
    "Parse schedule": "Leer el horario",
    "Filter by the instrumental tag": "Filtrar por la marca de instrumental",
    "Short dance names  (LW, SB)": "Nombres de baile cortos  (LW, SB)",
    "Auto re-roll round on strategy change":
        "Volver a sortear la ronda al cambiar de estrategia",
    "Re-analyze tracks that already have highlights":
        "Volver a analizar temas que ya tienen clímax",
    "An .m3u playlist file": "Un archivo de lista .m3u",
    "Focused playlist (current deck)": "Lista activa (deck actual)",
    "Number of titles in this wishlist":
        "Número de títulos en esta lista de deseos",
    "Own looks": "Aspectos propios",
    "none yet — ＋ New look…": "ninguno todavía — ＋ Nuevo aspecto…",
    "＋  New look…": "＋  Nuevo aspecto…",
    "A look of your own, starting as a copy of the selected one.":
        "Un aspecto propio, que empieza como copia del seleccionado.",
    "✎  Edit…": "✎  Editar…",
    "🗑  Delete": "🗑  Eliminar",
    "Import…": "Importar…",
    "Add a look someone exported.": "Añadir un aspecto que alguien exportó.",
    "Export…": "Exportar…",
    "Save the selected look of your own as a file, to pass it on.":
        "Guardar el aspecto propio seleccionado como archivo, para compartirlo.",
    "A look of your own, kept on this computer. ✎ Edit changes it, Export passes it on.":
        "Un aspecto propio, guardado en este ordenador. ✎ Editar lo cambia, Exportar lo comparte.",
    "%s (own)": "%s (propio)",
    "Look not saved": "Aspecto no guardado",
    "The looks file could not be written. The log names the reason.":
        "No se pudo escribir el archivo de aspectos. El registro indica el motivo.",
    "Delete look": "Eliminar aspecto",
    "Delete the look “%s”? This cannot be undone; an exported file of it stays.":
        "¿Eliminar el aspecto «%s»? No se puede deshacer; un archivo exportado de él se conserva.",
    "Import a look": "Importar un aspecto",
    "Look not imported": "Aspecto no importado",
    "This file holds no look the app can use:\n"
    "%s":
        "Este archivo no contiene ningún aspecto que la app pueda usar:\n"
        "%s",
    "Export the look": "Exportar el aspecto",
    "Look not exported": "Aspecto no exportado",
    "The file could not be written:\n"
    "%s":
        "No se pudo escribir el archivo:\n"
        "%s",
    "🎨  Edit look": "🎨  Editar aspecto",
    "Family: %s. The details it shares with the built-in looks of that group stay: faders, checkboxes, headers.":
        "Familia: %s. Lo que comparte con los aspectos integrados de ese grupo se mantiene: faders, casillas, cabeceras.",
    "Grounds": "Fondos",
    "Window": "Ventana",
    "The ground of the main window and the dialogs.":
        "El fondo de la ventana principal y de los diálogos.",
    "Lists and fields": "Listas y campos",
    "Tables, lists and text fields.": "Tablas, listas y campos de texto.",
    "Every other row": "Una fila de cada dos",
    "The second row colour of a table.":
        "El segundo color de fila de una tabla.",
    "Headers": "Cabeceras",
    "Table headers and the menu bar.":
        "Cabeceras de tabla y la barra de menús.",
    "The ground of a tooltip.": "El fondo de un tooltip.",
    "Buttons": "Botones",
    "Button face": "Cara del botón",
    "A button at rest.": "Un botón en reposo.",
    "Under the mouse": "Bajo el ratón",
    "A button the mouse is over.": "Un botón con el ratón encima.",
    "Pressed": "Pulsado",
    "A button held down.": "Un botón mantenido pulsado.",
    "Light from above": "Luz desde arriba",
    "Set, a button fades from this colour down to its face, like a key on a mixing desk. Off, the face is flat.":
        "Activado, un botón pasa de este color hacia abajo a su cara, como una tecla de mesa de mezclas. Desactivado, la cara es plana.",
    "Header light from above": "Luz de cabecera desde arriba",
    "The same fade for the table headers and the deck title strips.":
        "El mismo degradado para las cabeceras de tabla y las franjas de título de los decks.",
    "Lines": "Líneas",
    "Hairlines": "Líneas finas",
    "Frames, the table grid and separators.":
        "Marcos, la cuadrícula de la tabla y los separadores.",
    "Outlines": "Contornos",
    "A control's frame and the scrollbar handle.":
        "El marco de un control y el tirador de la barra de desplazamiento.",
    "All ordinary text.": "Todo el texto normal.",
    "Dim text": "Texto atenuado",
    "Disabled text, placeholders and side notes.":
        "Texto desactivado, marcadores de posición y notas al margen.",
    "Accent": "Acento",
    "The default button and a switched-on toggle.":
        "El botón predeterminado y un interruptor encendido.",
    "Text on the accent": "Texto sobre el acento",
    "The caption on an accent fill.": "El rótulo sobre un relleno de acento.",
    "Accent as text": "Acento como texto",
    "Links, focus rings and the round bands' lettering.":
        "Enlaces, anillos de foco y las letras de las bandas de ronda.",
    "Selection": "Selección",
    "Selected row": "Fila seleccionada",
    "The band of the selected row.": "La banda de la fila seleccionada.",
    "Text on the selection": "Texto sobre la selección",
    "The text in that band.": "El texto en esa banda.",
    "Fade": "Degradado",
    "off": "no",
    "Shape and lettering": "Forma y letra",
    "Corners:": "Esquinas:",
    "Buttons:": "Botones:",
    "Tabs:": "Pestañas:",
    "Focus:": "Foco:",
    "Font:": "Letra:",
    "Outlined": "Con contorno",
    "Flat, no frame": "Plano, sin marco",
    "Desk key, lit from above": "Tecla de mesa, iluminada desde arriba",
    "Dark, glowing rim when on": "Oscuro, borde brillante al encender",
    "Soft filled": "Relleno suave",
    "Pill, fully rounded": "Píldora, totalmente redondeado",
    "2 px frame, high contrast": "Marco de 2 px, alto contraste",
    "Underlined": "Subrayado",
    "Segmented": "Segmentado",
    "Desk keys": "Teclas de mesa",
    "Pills": "Píldoras",
    "Ring around the field": "Anillo alrededor del campo",
    "Line under the field": "Línea bajo el campo",
    "Saved looks are kept on this computer. The app takes a changed look on its next start.":
        "Los aspectos guardados se quedan en este ordenador. La app aplica un aspecto modificado en su próximo inicio.",
    "⚠ Hard to read:": "⚠ Difícil de leer:",
    "✓ Every text reads clearly against its ground.":
        "✓ Todo el texto se distingue bien de su fondo.",
    "%s: %.1f : 1, should be at least %.1f":
        "%s: %.1f : 1, debería ser al menos %.1f",
    "Text on lists": "Texto sobre listas",
    "Text on every other row": "Texto sobre una fila de cada dos",
    "Text on the window": "Texto sobre la ventana",
    "Text on buttons": "Texto sobre botones",
    "Dim text on lists": "Texto atenuado sobre listas",
    "Planning": "Planificación",
    "Playing": "Reproducción",
    "Group": "Grupo",
    "Heat %d": "Grupo %d",
    "▼  PRELIMINARY ROUND  (2 heats)": "▼  PRELIMINARY ROUND  (2 grupos)",
    "Button": "Botón",
    "Switched on": "Encendido",
    "Disabled": "Desactivado",
    "Search…": "Buscar…",
    "Ticked": "Marcado",
    "Dim text: a hint, a placeholder.":
        "Texto atenuado: una pista, un marcador de posición.",
    "Welcome to DanceSport Planner & Player":
        "Bienvenido a DanceSport Planner & Player",
    "AI Song Suggestions (OpenRouter)":
        "Sugerencias de temas por IA (OpenRouter)",
    "Previous session crashed": "La sesión anterior se cerró inesperadamente",
    "Settings — app mode, library paths & analysis":
        "Ajustes — modo, rutas de la biblioteca y análisis",
    "Settings — library paths, global search & analysis":
        "Ajustes — rutas de la biblioteca, búsqueda global y análisis",
    "⌨  Keyboard shortcuts  (F1)": "⌨  Atajos de teclado  (F1)",
    "⛶  Fullscreen  (F11)": "⛶  Pantalla completa  (F11)",
    "⛶  Exit Fullscreen  (F11)": "⛶  Salir de pantalla completa  (F11)",
    "⛶  Fullscreen clock: only the time (20:45:12), no date":
        "⛶  Reloj en pantalla completa: solo la hora (20:45:12), sin fecha",
    "Shortcuts (F1), manual and about this app":
        "Atajos (F1), manual y acerca de esta app",
    "ℹ  About…": "ℹ  Acerca de…",
    "About": "Acerca de",
    "Project": "Proyecto",
    "Music is playing": "Está sonando música",
    "Music is playing. Quit anyway and stop it?":
        "Está sonando música. ¿Salir de todos modos y detenerla?",
    "Author": "Autor",
    "License": "Licencia",
    "App icon": "Icono de la app",
    "Icons": "Iconos",
    "Voices": "Voces",
    "AI-generated, non-commercial use":
        "Generado por IA, solo uso no comercial",
    "Model": "Modelo",
    "Libraries": "Bibliotecas",
    "all licences": "todas las licencias",
    "Which library should this index cover?":
        "¿Qué biblioteca debe cubrir este índice?",
    "What should go into the venue bundle?":
        "¿Qué debe ir en el paquete del local?",
    "Settings saved.": "Ajustes guardados.",
    "Database cleanup done.": "Limpieza de la base de datos terminada.",
    "Loading library…": "Cargando la biblioteca…",
    "Loading music library…": "Cargando la biblioteca de música…",
    "Library: loading…": "Biblioteca: cargando…",
    "Generating playlist…": "Generando la lista…",
    "Asking the model…": "Preguntando al modelo…",
    "Asking the model for a playlist…": "Pidiendo una lista al modelo…",
    "Fetching the model list…": "Obteniendo la lista de modelos…",
    "Cancelling…": "Cancelando…",
    "Analysis failed.": "El análisis falló.",
    "AI playlist failed.": "La lista por IA falló.",
    "AI playlist: nothing usable.": "Lista por IA: nada aprovechable.",
    "Practice failed.": "La práctica falló.",
    "Practice: no matching tracks.": "Práctica: no hay temas que encajen.",
    "Global index failed.": "El índice global falló.",
    "Similar-track analysis failed.": "El análisis de temas similares falló.",
    "Repository scan cancelled.": "Exploración del repositorio cancelada.",
    "Import: no tracks detected": "Importar: no se detectaron temas",
    "No parseable suggestions returned.":
        "No se recibieron sugerencias aprovechables.",
    "Could not fetch models (using fallback list).":
        "No se pudieron obtener los modelos (se usa la lista de reserva).",
    "Load the music library first.": "Primero carga la biblioteca de música.",
    "Nothing to clear — all playlists are empty.":
        "Nada que vaciar — todas las listas están vacías.",
    "Nothing to export — all playlists are empty.":
        "Nada que exportar — todas las listas están vacías.",
    "Nothing to save — all playlists are empty.":
        "Nada que guardar — todas las listas están vacías.",
    "Nothing to save — the day decks are empty.":
        "Nada que guardar — los decks del día están vacíos.",
    "Nothing to save yet.": "Todavía no hay nada que guardar.",
    "Nothing to undo yet": "Todavía no hay nada que deshacer",
    "Nothing to redo": "Nada que rehacer",
    "Undo: %s\n"
    "%s step(s) available  ·  Ctrl+Z":
        "Deshacer: %s\n"
        "%s paso(s) disponible(s)  ·  Ctrl+Z",
    "Redo: %s\n"
    "%s step(s) available  ·  Ctrl+Y":
        "Rehacer: %s\n"
        "%s paso(s) disponible(s)  ·  Ctrl+Y",
    "↶  Undo — %s": "↶  Deshacer — %s",
    "↷  Redo — %s": "↷  Rehacer — %s",
    "restored %s": "%s restaurado",
    "removed %s": "%s quitado",
    "replaced %s → %s": "%s reemplazado → %s",
    "moved %s": "%s movido",
    "playlist rename": "lista renombrada",
    "deck layout change": "cambio de distribución de decks",
    "view / settings change": "cambio de vista / ajustes",
    "“%s” and “%s”": "«%s» y «%s»",
    "%s tracks (“%s”, “%s”, …)": "%s temas («%s», «%s», …)",
    "No files added yet.": "Todavía no se han añadido archivos.",
    "No song selected": "Ningún tema seleccionado",
    "No playing row found.": "No se encontró ninguna fila en reproducción.",
    "No dances for this class.": "No hay bailes para esta clase.",
    "No similar tracks found.": "No se encontraron temas similares.",
    "No similar tracks found for that file.":
        "No se encontraron temas similares a ese archivo.",
    "No reference playlist yet.": "Todavía no hay lista de referencia.",
    "No auto-advance pause is running to extend.":
        "No hay ninguna pausa de avance automático en curso que alargar.",
    "This wall has no pads yet.": "Esta Cartwall todavía no tiene pads.",
    "Your wishlist is empty — add tracks to a wishlist first.":
        "Tu lista de deseos está vacía — primero añade temas a una lista de deseos.",
    "Saved — it takes effect the next time you start the app.":
        "Guardado — se aplica la próxima vez que inicies la app.",
    "Then restart the app — nothing else to configure.":
        "Luego reinicia la app — no hay nada más que configurar.",
    "ffmpeg not found": "ffmpeg no encontrado",
    "(multimedia unavailable)": "(multimedia no disponible)",
    "Play a title first — then TSO sets its heat tempo.":
        "Reproduce primero un título — entonces TSO fija el tempo de su grupo.",
    "This title has no detected tempo — can't equalize.":
        "Este título no tiene tempo detectado — no se puede igualar.",
    "The fader can't reach that tempo for this title.":
        "El fader no alcanza ese tempo para este título.",
    "Preview player disabled — re-enable it in ⚙ Settings.":
        "Reproductor de vista previa desactivado — vuelve a activarlo en ⚙ Ajustes.",
    "Pick a playlist again to choose a different track":
        "Elige de nuevo una lista para tomar otro tema",
    "Pick “Replace…” again to choose a different track":
        "Elige de nuevo «Reemplazar…» para tomar otro tema",
    "%s: strategy set to %s — ↺ a song or dance to apply":
        "%s: estrategia fijada en %s — ↺ en un tema o baile la aplica",
    "%s: %s · %s — ↺ a song or dance to apply":
        "%s: %s · %s — ↺ en un tema o baile la aplica",
    "↻ %s re-rolled — %s": "↻ %s sorteado de nuevo — %s",
    "↻ %s re-rolled — %s · %s": "↻ %s sorteado de nuevo — %s · %s",
    "Re-roll failed: %s": "Falló el nuevo sorteo: %s",
    "this comp": "esta competición",
    "all playlists": "todas las listas",
    "Listen to this track": "Escuchar este tema",
    "Play / stop this track": "Reproducir / detener este tema",
    "Play / stop this file": "Reproducir / detener este archivo",
    "Play / stop the base track these results are based on":
        "Reproducir / detener el tema base de estos resultados",
    "Listen to this pad while you set its level":
        "Escuchar este pad mientras ajustas su nivel",
    "Jump back to the start (0:00) of this track":
        "Volver al inicio (0:00) de este tema",
    "Click to collapse / expand": "Clic para contraer / expandir",
    "Click to focus · right-click or double-click to rename":
        "Clic para activar · clic derecho o doble clic para renombrar",
    "Double-click to rename this page":
        "Doble clic para renombrar esta página",
    "Double-click to type a value": "Doble clic para escribir un valor",
    "Drag here to move": "Arrastra aquí para mover",
    "Drag here to move the preview player":
        "Arrastra aquí para mover el reproductor de vista previa",
    "Unfold this playlist": "Desplegar esta lista",
    "Fold the library pane to its header":
        "Plegar el panel de la biblioteca a su cabecera",
    "%s — folded.  Click to unfold.": "%s — plegado.  Clic para desplegar.",
    "%s — folded.  Click to open.": "%s — plegado.  Clic para abrir.",
    "Open the %s panel.": "Abrir el panel %s.",
    "Compact the %s panel to its header tab —\n"
    "click the tab (or this arrow) to open it again.":
        "Compactar el panel %s a su pestaña de cabecera —\n"
        "haz clic en la pestaña (o en esta flecha) para abrirlo de nuevo.",
    "Close the preview and stop playback  (Ctrl+X)":
        "Cerrar la vista previa y detener la reproducción  (Ctrl+X)",
    "Close the tournament day — clears all 📅 day decks":
        "Cerrar el día de torneo — vacía todos los 📅 decks del día",
    "Back to this slot's default key":
        "Volver a la tecla predeterminada de esta posición",
    "Export or import this wall": "Exportar o importar esta Cartwall",
    "Duck to 20 % / back to full": "Bajar al 20 % / volver al máximo",
    "Reset the tempo to ±0 % (or double-click the fader)":
        "Restablecer el tempo a ±0 % (o doble clic en el fader)",
    "Volume adjustment of this track by Equalize volume (R128)":
        "Ajuste de volumen de este tema por Igualar volumen (R128)",
    "When this file was created in the library":
        "Cuándo se creó este archivo en la biblioteca",
    "Replace via the similar-tracks picker":
        "Reemplazar mediante el selector de temas similares",
    "Put the shipped rule set back.": "Restaurar el reglamento incluido.",
    "Put the whole transcript on the clipboard.":
        "Copiar toda la conversación al portapapeles.",
    "Esc closes  ·  double-click leaves full screen":
        "Esc cierra  ·  doble clic sale de pantalla completa",
    "Pick a length or type one: m:ss, seconds, or 'full'":
        "Elige una duración o escríbela: m:ss, segundos o 'completo'",
    "%s — its own length":
        "%s — duración propia",
    "This dance has its own play length in the 🏆 tournament set\n(⚙ Settings → 🎛 Play sets). − / + and typing change it there.":
        "Este baile tiene su propia duración en el set 🏆 de torneo\n(⚙ Ajustes → 🎛 Sets de reproducción). − / + y escribir la cambian allí.",
    "<b>⏱ Per dance</b> — a dance given a length of its own is cut there instead, as long as a list stands on this set. The ▶ Playing panel names the dance under its length.":
        "<b>⏱ Por baile</b> — un baile con duración propia se corta ahí, mientras una lista esté en este set. El panel ▶ Reproducción nombra el baile bajo su duración.",
    "— the set's length":
        "— la duración del set",
    "m:ss, seconds, or 'full' — Enter to keep, Esc to abandon":
        "m:ss, segundos o 'completo' — Intro la conserva, Esc la descarta",
    "full — to each title's own end":
        "completo — hasta el final propio de cada título",
    "full": "completo",
    "no marks — scrub to a crash and hit 🎯":
        "sin marcas — avanza hasta un golpe y pulsa 🎯",
    "“Proven” = songs in any of your playlists · “New” = in none.":
        "«Probados» = temas de alguna de tus listas · «Nuevos» = de ninguna.",
    "e.g. a song title, mood, or leave blank":
        "p. ej. un título, un ambiente, o déjalo en blanco",
    "API base URL:": "URL base de la API:",
    "API key  (free OpenRouter key from openrouter.ai/keys):":
        "Clave de API  (clave gratuita de OpenRouter en openrouter.ai/keys):",
    "Drag in playlists / files…": "Arrastra listas / archivos aquí…",
    "Drop .m3u playlists or audio files here, or click to browse":
        "Suelta aquí listas .m3u o archivos de audio, o haz clic para buscar",
    "Drop an audio file here, or click to browse":
        "Suelta aquí un archivo de audio, o haz clic para buscar",
    "Drop saved .m3u playlists here, or click to browse":
        "Suelta aquí listas .m3u guardadas, o haz clic para buscar",
    "Drop playlists above to check them.":
        "Suelta listas arriba para comprobarlas.",
    "Drop some files above to check them.":
        "Suelta archivos arriba para comprobarlos.",
    "Saved playlists dragged in (.m3u)…":
        "Listas guardadas arrastradas (.m3u)…",
    "Choose an .m3u file…": "Elegir un archivo .m3u…",
    "Browse…": "Examinar…",
    "Add…": "Añadir…",
    "Build / refresh…": "Crear / actualizar…",
    "  Pick a colour…": "  Elegir un color…",
    "↑ resolved above": "↑ resuelto arriba",
    "— Latin —": "— Latino —",
    "⚙  Settings": "⚙  Ajustes",
    "⚗ Analysis": "⚗ Análisis",
    "🎨 Look": "🎨 Aspecto",
    "📁 Paths": "📁 Rutas",
    "🔊 Sound && player": "🔊 Sonido && reproductor",
    "📁  New folder…": "📁  Nueva carpeta…",
    "⌨  Shortcuts…": "⌨  Atajos…",
    "❔  Shortcuts": "❔  Atajos",
    "▶  Playing": "▶  Reproducción",
    "▶  Playing mode": "▶  Modo reproducción",
    "▶  Load onto the focused deck": "▶  Cargar en el deck activo",
    "▴  Fold decks": "▴  Decks",
    "⊟  Collapse all": "⊟  Contraer",
    "⏹  Stop all": "⏹  Detener todo",
    "⏸  Auto-advance…": "⏸  Avance automático…",
    "⏱  Wall fade-out…": "⏱  Fundido de la Cartwall…",
    "⏱ calculating…": "⏱ calculando…",
    "⏳  Comparing…": "⏳  Comparando…",
    "⚡  Generate Playlist": "⚡  Generar lista",
    "✅  Apply": "✅  Aplicar",
    "✅  Keep": "✅  Conservar",
    "✅  Keep all": "✅  Conservar todos",
    "✅  Use this track as replacement": "✅  Usar este tema como reemplazo",
    "✅  No duplicate songs across your open playlist(s).":
        "✅  No hay temas duplicados en tus listas abiertas.",
    "✎  Rename…": "✎  Renombrar…",
    "✏  Rename": "✏  Renombrar",
    "📅  New tournament day…": "📅  Nuevo día de torneo…",
    "✏️  Rename tab…": "✏️  Renombrar pestaña…",
    "✏️  Edit highlights": "✏️  Editar clímax",
    "✏  Editing — pads do not play": "✏  Editando — los pads no suenan",
    "✕  Close tournament day": "✕  Cerrar el día de torneo",
    "✦  Only never played": "✦  Solo nunca reproducidos",
    "✦ Never played": "✦ Nunca reproducido",
    "➕  Add": "➕  Añadir",
    "➕  Add a heat to this round": "➕  Añadir un grupo a esta ronda",
    "➕  Add files…": "➕  Añadir archivos…",
    "➕  Both": "➕  Ambos",
    "➕ Add competition": "➕ Añadir competición",
    "➖  Remove selected": "➖  Quitar selección",
    "＋  Add playlists…": "＋  Añadir listas…",
    "⬆  Move backup up into this empty slot":
        "⬆  Subir la reserva a este hueco libre",
    "⇅  Swap these two titles\tAlt+S":
        "⇅  Intercambiar estos dos títulos\tAlt+S",
    "♊  Remove duplicate titles in this list":
        "♊  Quitar títulos duplicados de esta lista",
    "⭐  Favorites": "⭐  Favoritos",
    "⭐  Favorites library": "⭐  Biblioteca de favoritos",
    "🎯  Favorites library": "🎯  Biblioteca de favoritos",
    "⭐  Open wishlists": "⭐  Listas de deseos abiertas",
    "⭐  Only tracks in my wishlist(s)":
        "⭐  Solo temas de mis listas de deseos",
    "⭐  Find similar (in my wishlist only)":
        "⭐  Buscar similares (solo en mi lista de deseos)",
    "⭐  Find similar in wishlist (run Audio Analysis first)":
        "⭐  Buscar similares en la lista de deseos (primero ejecuta el análisis de audio)",
    "⭐  Find similar in wishlist (wishlist is empty)":
        "⭐  Buscar similares en la lista de deseos (la lista de deseos está vacía)",
    "🌱  Find similar (never played)":
        "🌱  Buscar similares (nunca reproducidos)",
    "🌱  Find similar, never played (run Audio Analysis first)":
        "🌱  Buscar similares nunca reproducidos (primero ejecuta el análisis de audio)",
    "🌱  Freshness: all tracks": "🌱  Novedad: todos los temas",
    "🔎  Find similar tracks": "🔎  Buscar temas similares",
    "🔎  Find similar (run Audio Analysis first)":
        "🔎  Buscar similares (primero ejecuta el análisis de audio)",
    "🔍  Compare": "🔍  Comparar",
    "🔍  Filter title / artist / comment tag…":
        "🔍  Filtrar título / artista / comentario…",
    "🔍  Find a title in this list…\tCtrl+F":
        "🔍  Buscar un título en esta lista…\tCtrl+F",
    "🆕 Last 30 days": "🆕 Últimos 30 días",
    "🆕 Last 90 days": "🆕 Últimos 90 días",
    "🆕 Last 12 months": "🆕 Últimos 12 meses",
    "🆕 Last 18 months": "🆕 Últimos 18 meses",
    "🆕 Unplanned": "🆕 Sin planificar",
    "📅  Only not since 1 y": "📅  Solo no reproducidos desde hace 1 año",
    "📅 Not since 1 y": "📅 No desde hace 1 año",
    "📅  Day plan": "📅  Plan del día",
    "📅 Plan tournament day": "📅 Planificar el día de torneo",
    "📅 Tournament day": "📅 Día de torneo",
    "📅 Tournament day closed.": "📅 Día de torneo cerrado.",
    "📜  Find planned before": "📜  Buscar planificados antes",
    "📜  Find planned before (load library first)":
        "📜  Buscar planificados antes (primero carga la biblioteca)",
    "📜  Re-learn playlist popularity…":
        "📜  Volver a aprender la popularidad de las listas…",
    "📚  Library": "📚  Biblioteca",
    "📚  Show never-played tracks": "📚  Mostrar temas nunca reproducidos",
    "📋  Copy": "📋  Copiar",
    "📋  Copy file path": "📋  Copiar ruta del archivo",
    "📋  Copy file path (unavailable)":
        "📋  Copiar ruta del archivo (no disponible)",
    "📋  Copy file path (not in your library)":
        "📋  Copiar ruta del archivo (no está en tu biblioteca)",
    "📋  Based on my playlist history (tracks I play together)":
        "📋  Según mi historial de listas (temas que pongo juntos)",
    "📝  Copy details": "📝  Copiar detalles",
    "📝  Planning": "📝  Planificación",
    "📝  Wish list — the titles below, in that order":
        "📝  Lista de deseos — los títulos de abajo, en ese orden",
    "📂  Open folder": "📂  Abrir carpeta",
    "📂  Show in Explorer": "📂  Mostrar en el Explorador",
    "📂  Show in Explorer (unavailable)":
        "📂  Mostrar en el Explorador (no disponible)",
    "📂  Import M3U…": "📂  Importar M3U…",
    "📂  Add a folder of playlists…": "📂  Añadir una carpeta de listas…",
    "📂  Import — track paths": "📂  Importar — rutas de temas",
    "📂  Drag files in": "📂  Arrastrar archivos aquí",
    "📂  Assign files…": "📂  Asignar archivos…",
    "📂  An .m3u playlist file": "📂  Un archivo de lista .m3u",
    "📂  Drop saved .m3u playlists here, or click to browse":
        "📂  Suelta aquí listas .m3u guardadas, o haz clic para buscar",
    "📄  All pads on one page": "📄  Todos los pads en una página",
    "📊  Analyze loudness (R128)…": "📊  Analizar sonoridad (R128)…",
    "📊  Library gaps…": "📊  Huecos de la biblioteca…",
    "📊 Library gaps": "📊 Huecos de la biblioteca",
    "📤  Export wall…": "📤  Exportar Cartwall…",
    "📥  Import wall…": "📥  Importar Cartwall…",
    "📌  Save state": "📌  Estado",
    "📌 Cartwall docked": "📌 Cartwall acoplada",
    "💾  Save M3U": "💾  Guardar M3U",
    "💾  Save as M3U…": "💾  Guardar como M3U…",
    "💾  Save all": "💾  Guardar",
    "💾  Save all competition M3Us": "💾  Guardar todos los M3U de competición",
    "💾  Save all playlists as M3U": "💾  Guardar todas las listas como M3U",
    "🏆  Save all and add to Tournaments": "🏆  Guardar todo y añadir a Torneos",
    "🏆  Save and add to Tournaments…": "🏆  Guardar y añadir a Torneos…",
    "🏆 Saved and added %d playlist to Tournaments":
        "🏆 Guardada y añadida %d lista a Torneos",
    "🏆 Saved and added %d playlists to Tournaments":
        "🏆 Guardadas y añadidas %d listas a Torneos",
    "🏆 Saved — already in Tournaments": "🏆 Guardado — ya está en Torneos",
    "🔁  Check duplicates": "🔁  Comprobar duplicados",
    "🔁  Endless repeat": "🔁  Repetición sin fin",
    "🔁  Replace…": "🔁  Reemplazar…",
    "🔁  Reset all replacement marks":
        "🔁  Restablecer todas las marcas de reemplazo",
    "🔇  Probe silences…": "🔇  Sondear silencios…",
    "🔇 No audio backend — the cartwall cannot play here.":
        "🔇 Sin motor de audio — la Cartwall no puede sonar aquí.",
    "🔈  Pull the music down while this pad plays":
        "🔈  Bajar la música mientras suena este pad",
    "S  Stop the other pads when this one starts":
        "S  Detener los demás pads cuando este empieza",
    "Every other running pad fades out as this one starts —\n"
    "for an anthem or a winners' fanfare that needs the room.":
        "Todos los demás pads en marcha se desvanecen cuando este empieza —\n"
        "para un himno o una fanfarria de ganadores que necesita el espacio.",
    "🎶  Background: dip under the music while a title plays":
        "🎶  Fondo: bajar bajo la música mientras suena un título",
    "The other way round from 🔈: this pad goes silent while the\n"
    "main player plays and comes back up in the pauses.":
        "Al revés que 🔈: este pad se calla mientras suena el\n"
        "reproductor principal y vuelve a subir en las pausas.",
    "🔈 No announcement recordings found for this voice.":
        "🔈 No se encontraron grabaciones de anuncios para esta voz.",
    "🖌  Wall colour": "🖌  Color de la Cartwall",
    "🖥  Presenter": "🖥  Presentación",
    "🖥  Presenter — DanceSport Player": "🖥  Presentación — DanceSport Player",
    "🕒 Timetable — presenter screen": "🕒 Horario — pantalla de presentación",
    "✖  Remove": "✖  Quitar",
    "🖨  Print": "🖨  Imprimir",
    "🖨  Export PDF": "🖨  Exportar PDF",
    "🗑  Clear": "🗑  Vaciar",
    "🗑  Remove": "🗑  Quitar",
    "🗑  Remove this title (keep slot)":
        "🗑  Quitar este título (mantener la posición)",
    "🗑  Remove %d selected titles (keep slots)":
        "🗑  Quitar %d títulos seleccionados (mantener las posiciones)",
    "🗑  Remove this title": "🗑  Quitar este título",
    "🗑  Remove %d selected titles": "🗑  Quitar %d títulos seleccionados",
    "🗑  Remove from tree": "🗑  Quitar del árbol",
    "🗑  Remove from wishlist": "🗑  Quitar de la lista de deseos",
    "🗑  Remove this backup\tCtrl+Del": "🗑  Quitar esta reserva\tCtrl+Supr",
    "🗑  Remove this empty slot": "🗑  Quitar este hueco vacío",
    "🗑  Remove this heat (all dances)\tCtrl+Del":
        "🗑  Quitar este grupo (todos los bailes)\tCtrl+Supr",
    "🗑  Remove this round (all heats)":
        "🗑  Quitar esta ronda (todos los grupos)",
    "🗜  Compact": "🗜  Compacto",
    "🚫  No groups": "🚫  Sin grupos",
    "🔢  Numbers": "🔢  Números",
    "🧹  Clear all": "🧹  Vaciar",
    "🧹  Clear all playlists": "🧹  Vaciar todas las listas",
    "🧹  Empty this playlist": "🧹  Vaciar esta lista",
    "🧹  Clean up database…": "🧹  Limpiar la base de datos…",
    "🧹  Export unused": "🧹  Exportar no usados",
    "🧹  Reference base": "🧹  Base de referencia",
    "🧹  Remove": "🧹  Quitar",
    "🧹  Remove tracks already in a playlist":
        "🧹  Quitar temas que ya están en una lista",
    "🧹 Cleared all playlists.": "🧹 Todas las listas vaciadas.",
    "🧹 Tournament-day playlists cleared.":
        "🧹 Listas del día de torneo vaciadas.",
    "🧳  USB export": "🧳  Exportar USB",
    "🧳 USB export": "🧳 Exportar a USB",
    "🧳 USB export aborted — incomplete bundle removed.":
        "🧳 Exportación a USB cancelada — paquete incompleto eliminado.",
    "🧭  Fix paths": "🧭  Corregir rutas",
    "🧭  Fix (overwrite)": "🧭  Corregir (sobrescribir)",
    "🧭  Fix (swap in playlists)": "🧭  Corregir (cambiar en las listas)",
    "🧱  Build ALL caches…": "🧱  Crear TODAS las cachés…",
    "🧠  Rebuild index…": "🧠  Reconstruir índice…",
    "🤖  AI Playlist…": "🤖  Lista por IA…",
    "🤖  AI playlist": "🤖  Lista por IA",
    "🤖  Build": "🤖  Crear",
    "🤖  Get Suggestions": "🤖  Obtener sugerencias",
    "🤖  Conversation with the model": "🤖  Conversación con el modelo",
    "🤸  Practice / party playlist": "🤸  Lista de práctica / fiesta",
    "🎉  Party set": "🎉  Set de fiesta",
    "🎉  Party playlist (alternating 3-dance rounds, all dances)":
        "🎉  Lista de fiesta (rondas alternas de 3 bailes, todos los bailes)",
    "🏆  Tournaments": "🏆  Torneos",
    "🏆  Tournament set": "🏆  Set de torneo",
    "🏆 Tournament only": "🏆 Solo torneo",
    "🏷  Re-read MP3 tags": "🏷  Volver a leer etiquetas MP3",
    "🏷  Re-read MP3 tags (unavailable)":
        "🏷  Volver a leer etiquetas MP3 (no disponible)",
    "🐂  Analyze PD highlights…": "🐂  Analizar clímax de PD…",
    "🎯  Mark highlight now": "🎯  Marcar clímax ahora",
    "🎯 Highlights cleared — 🐂 auto-detection will run again.":
        "🎯 Clímax borrados — 🐂 la detección automática volverá a ejecutarse.",
    "🎯 Last mark deleted — 🐂 auto-detection takes over again.":
        "🎯 Última marca borrada — 🐂 la detección automática vuelve a encargarse.",
    "🎯 Play a Paso Doble first, then click when a highlight hits.":
        "🎯 Reproduce primero un Paso Doble y haz clic cuando llegue un clímax.",
    "🎵  Check music": "🎵  Comprobar música",
    "🎵  Check music speed": "🎵  Comprobar velocidad de la música",
    "🎵  Check music speed (unavailable)":
        "🎵  Comprobar velocidad de la música (no disponible)",
    "🎵  Music check": "🎵  Comprobación de música",
    "🎵 Checks": "🎵 Comprobaciones",
    "🎵 Music speed": "🎵 Velocidad de la música",
    "🎵 Music check aborted.": "🎵 Comprobación de música cancelada.",
    "🎵  One flat list of": "🎵  Una lista plana de",
    "🎵  Show its tracks": "🎵  Mostrar sus temas",
    "🎵 0 titles": "🎵 0 títulos",
    "🎵 %d title": "🎵 %d título",
    "🎵 %d titles": "🎵 %d títulos",
    "  ·  ✦ %d new": "  ·  ✦ %d nuevos",
    "🎼  Build chroma cover / remix index…":
        "🎼  Crear índice chroma de versiones / remixes…",
    "🎚️  Open playlists": "🎚️  Listas abiertas",
    "🎚️  Timbre + Rhythm (librosa)": "🎚️  Timbre + ritmo (librosa)",
    "🎛 Play sets": "🎛 Sets de reproducción",
    "🎛 No free pad voice — every voice holds a looping pad.":
        "🎛 No hay voz de pad libre — cada voz tiene un pad en bucle.",
    "🎤 Vocal": "🎤 Voz",
    "🎙️  Only instrumental tracks (no vocals)":
        "🎙️  Solo temas instrumentales (sin voz)",
    "🎧  Open in external player": "🎧  Abrir en reproductor externo",
    "🌐  Whole repository": "🌐  Todo el repositorio",
    "🌐  Build librosa index (needs librosa)":
        "🌐  Crear índice librosa (necesita librosa)",
    "🌐  Build / refresh librosa audio index (whole repo)…":
        "🌐  Crear / actualizar índice de audio librosa (todo el repositorio)…",
    "🔬  Timbre Gaussian / KL (Mandel-Ellis)":
        "🔬  Timbre gaussiano / KL (Mandel-Ellis)",
    "⚠  That spot is no longer in an open deck.":
        "⚠  Ese punto ya no está en ningún deck abierto.",
    "↺  Default blue": "↺  Azul predeterminado",
    "↺  Default rules": "↺  Reglas predeterminadas",
    "1 playlist": "1 lista",
    "%d playlist": "%d lista",
    "%d playlists": "%d listas",
    "No playlist": "Ninguna lista",
    "No wishlist": "Ninguna lista de deseos",
    "1 wishlist": "1 lista de deseos",
    "2 wishlists": "2 listas de deseos",
    "3 wishlists": "3 listas de deseos",
    "4 wishlists": "4 listas de deseos",
    "4 wishlists (2×2)": "4 listas de deseos (2×2)",
    "Build a practice playlist into the focused deck:\n"
    "• Practice for a tournament class — the class's dances round-robin\n"
    "  (e.g. Latin S: SA, CC, RB, PD, JI …), TSO-conform, popular + fresh.\n"
    "• Party — alternating 3-dance rounds across all dances.\n"
    "Draw from your ⭐ Favorites (unused tracks), the open wishlists\n"
    "or a chosen .m3u file.":
        "Crear una lista de práctica en el deck activo:\n"
        "• Práctica para una clase de torneo — los bailes de la clase por turnos\n"
        "  (p. ej. Latin S: SA, CC, RB, PD, JI …), conforme al TSO, populares + nuevos.\n"
        "• Fiesta — rondas alternas de 3 bailes con todos los bailes.\n"
        "Toma los temas de tus ⭐ Favoritos (temas sin usar), de las listas de deseos\n"
        "abiertas o de un archivo .m3u elegido.",
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
        "Comprobar cada tema de los decks en busca de problemas de torneo:\n"
        "• Tempo: etiqueta del nombre de archivo (T51 = compases por minuto, según\n"
        "  el compás del baile) frente al tempo medido por librosa — detecta archivos mal etiquetados.\n"
        "• Rango TSO: si el tempo está dentro del rango oficial de compases del baile.\n"
        "• Duración: avisa si un tema es más corto que el tiempo de baile de 1:30–1:45\n"
        "  o más largo que 4:00.\n"
        "• Estructura de ronda: número desigual de bailes en una ronda y desviaciones\n"
        "  en el número de grupos de final/semifinal.\n"
        "Los sospechosos se pueden escuchar, quitar o reemplazar desde el informe.\n"
        "Las comprobaciones de tempo/rango necesitan 🔬 Análisis de audio para el tempo medido.",
    "Collapse every round and dance header of every playlist —\n"
    "click again to open them all.":
        "Contraer todas las cabeceras de ronda y de baile de todas las listas —\n"
        "haz clic de nuevo para abrirlas todas.",
    "Cycle the playlist headers: full → 🗜 Compact (per-dance header rows\n"
    "hidden, each round lists its songs directly) → 🚫 No groups (round and\n"
    "─── section headers dropped too, so the list — a Practice / party\n"
    "list above all — is one flat run of songs) → 🔢 Numbers (no groups,\n"
    "plus an Nb. column up front counting the titles).":
        "Alternar las cabeceras de las listas: completo → 🗜 Compacto (filas de cabecera\n"
        "por baile ocultas, cada ronda lista sus temas directamente) → 🚫 Sin grupos (también\n"
        "se quitan las cabeceras de ronda y de sección ───, así que la lista — sobre todo una\n"
        "lista de práctica / fiesta — es una serie continua de temas) → 🔢 Números (sin grupos,\n"
        "más una columna Nº delante que cuenta los títulos).",
    "Cycle the wishlist area: off → 1 → 2 → 3 → 4 → 4 stacked 2×2.\n"
    "Right click walks it backwards.\n"
    "Off hides it entirely, even with multiple decks.\n"
    "Double-click any deck/wishlist title to rename it.":
        "Alternar la zona de listas de deseos: apagada → 1 → 2 → 3 → 4 → 4 en 2×2.\n"
        "El clic derecho la recorre hacia atrás.\n"
        "Apagada la oculta por completo, incluso con varios decks.\n"
        "Doble clic en el título de un deck o lista de deseos para renombrarlo.",
    "Empty every playlist deck (wishlists are kept).\n"
    "Tip: Del on a deck's title clears just that one playlist;\n"
    "Del on a wishlist's title clears that wishlist.":
        "Vaciar todos los decks de listas (las listas de deseos se conservan).\n"
        "Consejo: Supr sobre el título de un deck vacía solo esa lista;\n"
        "Supr sobre el título de una lista de deseos vacía esa lista de deseos.",
    "Export every non-empty playlist deck to its own .m3u in the\n"
    "playlist folder at once (wishlists are not included).\n"
    "Each file is named after its deck title.":
        "Exportar de una vez cada deck de lista no vacío a su propio .m3u en la\n"
        "carpeta de listas (las listas de deseos no se incluyen).\n"
        "Cada archivo lleva el nombre del título de su deck.",
    "Export playlists as a self-contained venue bundle — asks first\n"
    "whether to take all open decks, only the 📅 tournament day, or\n"
    "saved .m3u files dragged in, with the ⭐ wishlists if ticked.\n"
    "One sub-folder per playlist holding its tracks copied in numbered\n"
    "play order (0_0_1 - Title WW29.mp3) plus the playlist's .m3u — each\n"
    "folder plays in order even without the M3U, from any drive,\n"
    "laptop or UltraMixer at the venue (no path fixing needed there).\n"
    "Also offers the 📦 venue pack: this desk in one file for another PC.":
        "Exportar las listas como un paquete autónomo para el local — pregunta primero\n"
        "si tomar todos los decks abiertos, solo el 📅 día de torneo o\n"
        "los archivos .m3u guardados que arrastres (las ⭐ listas de deseos, si se marcan).\n"
        "Una subcarpeta por lista con sus temas copiados en orden de\n"
        "reproducción numerado (0_0_1 - Title WW29.mp3) más el .m3u de la lista — cada\n"
        "carpeta suena en orden incluso sin el M3U, desde cualquier unidad,\n"
        "portátil o UltraMixer en el local (allí no hace falta corregir rutas).\n"
        "También ofrece el 📦 paquete de sala: esta mesa en un archivo para otro PC.",
    "Export the focused playlist as a printable PDF\n"
    "(rounds, heats, titles, lengths) into the playlist folder.":
        "Exportar la lista activa como PDF imprimible\n"
        "(rondas, grupos, títulos, duraciones) a la carpeta de listas.",
    "Fold every visible playlist deck and wishlist to its header tab —\n"
    "click again to open them all.\n"
    "Click a single tab (or its arrow) to open just that one.":
        "Plegar cada deck de lista y cada lista de deseos visible a su pestaña de cabecera —\n"
        "haz clic de nuevo para abrirlos todos.\n"
        "Haz clic en una sola pestaña (o en su flecha) para abrir solo esa.",
    "Plan a whole tournament day: define the day's competitions\n"
    "(style, age, class, round pattern) and generate them all at once\n"
    "into the 📅 Tournament-day tab — eight dedicated day decks in two\n"
    "sub-tabs, separate from the normal playlists; more than 8\n"
    "competitions stack several per deck. All share one no-repeat\n"
    "pool, so a song never appears in two of the day's competitions\n"
    "(Paso excepted). Exports write one M3U per competition.":
        "Planificar un día de torneo completo: define las competiciones del día\n"
        "(estilo, edad, clase, esquema de rondas) y genéralas todas a la vez\n"
        "en la pestaña 📅 Día de torneo — ocho decks del día propios en dos\n"
        "subpestañas, separados de las listas normales; con más de 8\n"
        "competiciones se apilan varias por deck. Todas comparten un mismo\n"
        "fondo sin repeticiones, así que un tema nunca aparece en dos competiciones\n"
        "del día (salvo el Paso). La exportación escribe un M3U por competición.",
    "Relocate broken track references in the visible deck(s) to matching\n"
    "real files in the library — fixes moved folders / changed drive\n"
    "letters after an import. Anything still unresolved is reported.":
        "Redirigir las referencias rotas de los decks visibles a los archivos\n"
        "reales que coincidan en la biblioteca — corrige carpetas movidas / letras de unidad\n"
        "cambiadas tras una importación. Lo que siga sin resolver se informa.",
    "Save the whole working session right now — every deck, wishlist and the\n"
    "window layout — so it comes back exactly on the next launch.  (Ctrl+Shift+S)\n"
    "(This also happens automatically on every edit and on close.)":
        "Guardar ahora toda la sesión de trabajo — cada deck, lista de deseos y la\n"
        "distribución de la ventana — para que vuelva exactamente igual en el próximo inicio.  (Ctrl+Shift+S)\n"
        "(Esto también ocurre automáticamente con cada cambio y al cerrar.)",
    "Scan the visible playlist deck(s) for songs that appear more than once,\n"
    "then resolve each: keep the ones you want and replace the rest with a\n"
    "similar track (chosen from the Similar-Tracks picker).":
        "Buscar en los decks visibles temas que aparecen más de una vez\n"
        "y resolver cada caso: conserva los que quieras y reemplaza el resto por un\n"
        "tema similar (elegido en el selector de temas similares).",
    "Show / hide the library browser under the wishlists:\n"
    "filter the whole competition library and drag tracks\n"
    "straight into a deck or wishlist.":
        "Mostrar / ocultar el explorador de la biblioteca bajo las listas de deseos:\n"
        "filtra toda la biblioteca de competición y arrastra temas\n"
        "directamente a un deck o lista de deseos.",
    "Show / hide the 🎛 sample-pad wall:\n"
    "drop Tusch, applause or a background bed onto a pad and tap it —\n"
    "it plays on top of the running music instead of replacing it.\n"
    "Drag its title bar to dock it left / right / below, or float it.":
        "Mostrar / ocultar la pared de pads 🎛:\n"
        "suelta un Tusch, aplausos o un fondo sonoro en un pad y púlsalo —\n"
        "suena encima de la música en curso en lugar de reemplazarla.\n"
        "Arrastra su barra de título para acoplarla a la izquierda / derecha / abajo, o déjala flotante.",
    "Space: play / stop the selected song\n"
    "Ctrl + ← / → : seek 30 s back / forward\n"
    "Click a round / dance header to collapse or expand it":
        "Espacio: reproducir / detener el tema seleccionado\n"
        "Ctrl + ← / → : saltar 30 s atrás / adelante\n"
        "Clic en una cabecera de ronda / baile para contraerla o expandirla",
    "💥  The app did not shut down cleanly last time.\n"
    "\n"
    "The crash log of that session is under 'Show Details…' (it is overwritten on every start).":
        "💥  La app no se cerró correctamente la última vez.\n"
        "\n"
        "El registro del fallo de esa sesión está en 'Mostrar detalles…' (se sobrescribe en cada inicio).",
    "AI Error": "Error de IA",
    "API key needed": "Se necesita una clave de API",
    "CLAUDE_CONFIG_DIR — which claude login the CLI uses.\n"
    "Empty leaves it to the CLI (~/.claude).":
        "CLAUDE_CONFIG_DIR — qué inicio de sesión de claude usa la CLI.\n"
        "Vacío lo deja a la CLI (~/.claude).",
    "Enter a free OpenRouter API key (openrouter.ai/keys).":
        "Introduce una clave de API gratuita de OpenRouter (openrouter.ai/keys).",
    "Free text. The tempo table, the track catalog and the answer\n"
    "format are added automatically — describe only what makes a\n"
    "playlist good in your eyes.":
        "Texto libre. La tabla de tempos, el catálogo de temas y el formato\n"
        "de respuesta se añaden automáticamente — describe solo lo que para ti\n"
        "hace buena una lista.",
    "How much text this run moves.\n"
    "\n"
    "Sent is everything the model was given (the rules, the library summary, the catalog rows), back is what it answered. The biggest turn is the one that has to fit the model's context window: one prompt plus its reply.\n"
    "\n"
    "Token counts are estimated at ~4 characters each — no backend here reports its real usage.":
        "Cuánto texto mueve esta ejecución.\n"
        "\n"
        "Enviado es todo lo que recibió el modelo (las reglas, el resumen de la biblioteca, las filas del catálogo), recibido es lo que respondió. El turno más grande es el que tiene que caber en la ventana de contexto del modelo: una petición más su respuesta.\n"
        "\n"
        "Los tokens se estiman a ~4 caracteres cada uno — ningún backend aquí informa de su uso real.",
    "Name the tracks yourself. The model does the looking up: it finds\n"
    "the library title behind every shortened or mistyped wish.":
        "Nombra tú los temas. El modelo se encarga de buscarlos: encuentra\n"
        "el título de la biblioteca detrás de cada deseo abreviado o mal escrito.",
    "Style, age, start class, dances and the round pattern come from\n"
    "the panel on the left. The model only picks and orders the music.":
        "Estilo, edad, clase, bailes y el esquema de rondas vienen del\n"
        "panel de la izquierda. El modelo solo elige y ordena la música.",
    "Write the wishes however you like — one per line, a sentence, or a whole sheet pasted in with a column per dance:\n"
    "\n"
    "lw            t               ww        qs\n"
    "White wings   a new life      Willow    quit playing games !!\n"
    "melancolia !  Dance of love   Kiss me   youre so fine\n"
    "\n"
    "Short names and typos are fine. A two-letter code beside a title names its dance, ! or !! marks the ones you really want, and anything else you write here is read as an instruction.":
        "Escribe los deseos como quieras — uno por línea, una frase o una hoja entera pegada con una columna por baile:\n"
        "\n"
        "lw            t               ww        qs\n"
        "White wings   a new life      Willow    quit playing games !!\n"
        "melancolia !  Dance of love   Kiss me   youre so fine\n"
        "\n"
        "Los nombres cortos y las erratas no son problema. Un código de dos letras junto a un título indica su baile, ! o !! marca los que de verdad quieres, y todo lo demás que escribas aquí se lee como una instrucción.",
    "e.g. 'club evening, keep it modern', 'no covers in the final',\n"
    "'the wishes are for a show — put the two marked ones last'":
        "p. ej. 'velada del club, que sea moderno', 'sin versiones en la final',\n"
        "'los deseos son para un espectáculo — pon los dos marcados al final'",
    "🏆  Competition playlist — rounds and heats from the left panel":
        "🏆  Lista de competición — rondas y grupos del panel izquierdo",
    "Drag .m3u playlists or audio files here; drag a title out (e.g. to the reference field) to remove it":
        "Arrastra aquí listas .m3u o archivos de audio; arrastra un título fuera (p. ej. al campo de referencia) para quitarlo",
    "Open file": "Abrir archivo",
    "Open folder": "Abrir carpeta",
    "Show in Explorer": "Mostrar en el Explorador",
    "📂  Drop .m3u playlists (or audio files) here, or click to browse":
        "📂  Suelta aquí listas .m3u (o archivos de audio), o haz clic para buscar",
    "Could not parse any competition lines from the pasted text.\n"
    "Each line needs a class label, a style (STD/LAT) and the\n"
    "heat counts, e.g.  'U21 STD (50) 4 - 4 - 3 - 2 - 1'.":
        "No se pudo leer ninguna línea de competición del texto pegado.\n"
        "Cada línea necesita una etiqueta de clase, un estilo (STD/LAT) y el\n"
        "número de grupos, p. ej.  'U21 STD (50) 4 - 4 - 3 - 2 - 1'.",
    "Let a model build the playlist instead of the scoring algorithm.\n"
    "You give it the rules (a default set is filled in), it picks and\n"
    "orders the music — either into the rounds/heats configured above\n"
    "or as one flat list.\n"
    "Runs on your Claude subscription via the claude CLI, with\n"
    "OpenRouter as fallback.":
        "Deja que un modelo cree la lista en lugar del algoritmo de puntuación.\n"
        "Tú le das las reglas (hay un conjunto predeterminado), él elige y\n"
        "ordena la música — en las rondas/grupos configurados arriba\n"
        "o como una única lista plana.\n"
        "Funciona con tu suscripción de Claude mediante la CLI claude, con\n"
        "OpenRouter como alternativa.",
    "Runs through the claude CLI on your Claude subscription — no API key. Falls back to OpenRouter if that fails.":
        "Funciona mediante la CLI claude con tu suscripción de Claude — sin clave de API. Si falla, recurre a OpenRouter.",
    "⚠ claude CLI not found — OpenRouter will be used. Set the CLAUDE_BIN environment variable to use your subscription.":
        "⚠ CLI claude no encontrada — se usará OpenRouter. Define la variable de entorno CLAUDE_BIN para usar tu suscripción.",
    "Load an existing .m3u into the focused deck or wishlist.\n"
    "Decks detect rounds, dances and heats automatically — a final\n"
    "with extra backup variants (e.g. two Sambas) is handled too.\n"
    "A focused wishlist appends the tracks flat.":
        "Cargar un .m3u existente en el deck o la lista de deseos activos.\n"
        "Los decks detectan rondas, bailes y grupos automáticamente — también una final\n"
        "con variantes de reserva adicionales (p. ej. dos Sambas).\n"
        "Una lista de deseos activa añade los temas sin estructura.",
    "No competitions parsed": "No se reconoció ninguna competición",
    "On: changing a round's strategy re-rolls that whole round.\n"
    "Off: keep the current grid and change only the songs you want\n"
    "via the ↺ buttons (they use the newly selected strategy).":
        "Activado: cambiar la estrategia de una ronda vuelve a sortear toda la ronda.\n"
        "Desactivado: se mantiene la cuadrícula actual y solo cambias los temas que quieras\n"
        "con los botones ↺ (usan la estrategia recién elegida).",
    "Open the last conversation with the model again.\n"
    "It is kept until the next AI run starts.":
        "Volver a abrir la última conversación con el modelo.\n"
        "Se conserva hasta que empieza la siguiente ejecución de IA.",
    "When enabled, songs within a round are scored for\n"
    "timbral similarity to the round's first song.\n"
    "Disable for more varied song choices.":
        "Si está activado, los temas de una ronda se puntúan por\n"
        "similitud de timbre con el primer tema de la ronda.\n"
        "Desactívalo para una selección más variada.",
    "Which titles ⚡ Generate may pick from.\n"
    "Favorites library — everything scanned from your library folder.\n"
    "Open wishlists — only what you parked in the ⭐ wishlists.\n"
    "An .m3u file — only the tracks in that one playlist.\n"
    "With the last two, a dance the pool cannot cover stays blank.":
        "De qué títulos puede elegir ⚡ Generar.\n"
        "Biblioteca de favoritos — todo lo explorado en tu carpeta de biblioteca.\n"
        "Listas de deseos abiertas — solo lo que dejaste en las ⭐ listas de deseos.\n"
        "Un archivo .m3u — solo los temas de esa lista.\n"
        "Con las dos últimas, un baile que el fondo no puede cubrir queda vacío.",
    "“Proven” = songs you played in THIS competition's past lists · “New” = never played.  🎯 keeps a round to this competition; untick it to draw that round from ALL your playlists.":
        "«Probados» = temas que pusiste en listas anteriores de ESTA competición · «Nuevos» = nunca reproducidos.  🎯 mantiene una ronda en esta competición; desmárcalo para sacar esa ronda de TODAS tus listas.",
    "🎯 ticked: draw this round's songs from THIS competition's past lists only.\n"
    "Unticked: draw from ALL your playlists.":
        "🎯 marcado: tomar los temas de esta ronda solo de las listas anteriores de ESTA competición.\n"
        "Desmarcado: tomarlos de TODAS tus listas.",
    "<b>App mode</b> — which side of the app is shown:":
        "<b>Modo de la app</b> — qué parte de la app se muestra:",
    "<b>Favorites library</b> — scanned on start (your tanzcds folder):":
        "<b>Biblioteca de favoritos</b> — se explora al iniciar (tu carpeta tanzcds):",
    "<b>Reference path</b> — base folder the playlist files live in on THIS PC; 🧭 Fix paths re-roots broken references here (e.g. C:\\Users\\…\\my music\\tanzcds):":
        "<b>Ruta de referencia</b> — carpeta base donde están los archivos de las listas en ESTE PC; 🧭 Corregir rutas vuelve a enlazar aquí las referencias rotas (p. ej. C:\\Users\\…\\my music\\tanzcds):",
    "<b>Save-as folder</b> — where 'Save as M3U…' starts (e.g. D:\\Dropbox\\Turniere):":
        "<b>Carpeta de Guardar como</b> — donde empieza 'Guardar como M3U…' (p. ej. D:\\Dropbox\\Turniere):",
    "<b>Playlist file format</b> — what 'Save as M3U' and the exports write:":
        "<b>Formato de archivo de lista</b> — lo que escriben 'Guardar como M3U' y las exportaciones:",
    "UTF-8 (.m3u) — default": "UTF-8 (.m3u) — predeterminado",
    "UTF-8 with BOM (.m3u) — for Windows tools that guess ANSI":
        "UTF-8 con BOM (.m3u) — para herramientas de Windows que suponen ANSI",
    "UTF-8 (.m3u8) — the encoding named in the extension":
        "UTF-8 (.m3u8) — la codificación indicada en la extensión",
    "UTF-8 keeps every umlaut and is what current players read.\n"
    "Pick the BOM variant only if an older Windows tool shows 'Ã¼' instead\n"
    "of 'ü'; .m3u8 is the same UTF-8 under the extension some players expect.":
        "UTF-8 conserva cada tilde y diéresis y es lo que leen los reproductores actuales.\n"
        "Elige la variante con BOM solo si una herramienta antigua de Windows muestra 'Ã¼' en lugar\n"
        "de 'ü'; .m3u8 es el mismo UTF-8 con la extensión que esperan algunos reproductores.",
    "<b>Search folders</b> — where else to look for a track when a playlist was written on another PC, one folder per line (e.g. F:\\my music and C:\\Users\\…\\Documents\\datein\\my music):":
        "<b>Carpetas de búsqueda</b> — dónde más buscar un tema cuando una lista se escribió en otro PC, una carpeta por línea (p. ej. F:\\my music y C:\\Users\\…\\Documents\\datein\\my music):",
    "<b>Tournament playlists</b> — learned for popularity: .m3u files and/or tournament folders with copied music (e.g. H:\\DM Latein 2026):":
        "<b>Listas de torneo</b> — se aprenden para la popularidad: archivos .m3u y/o carpetas de torneo con música copiada (p. ej. H:\\DM Latein 2026):",
    "<b>What do you want to use this app for?</b>":
        "<b>¿Para qué quieres usar esta app?</b>",
    "<b>Whole music repository</b> — used by global search (e.g. F:\\my music):":
        "<b>Todo el repositorio de música</b> — lo usa la búsqueda global (p. ej. F:\\my music):",
    "<b>▶ Player position</b> — where the master player stands in ▶ Playing mode:":
        "<b>▶ Posición del reproductor</b> — dónde está el reproductor principal en el modo ▶ Reproducción:",
    "<b>🌐 Language</b> — menus, buttons and dialogs:":
        "<b>🌐 Idioma</b> — menús, botones y diálogos:",
    "🇬🇧  English — the language the app is written in (default)":
        "🇬🇧  English — el idioma en el que está escrita la app (predeterminado)",
    "Every label exactly as the app ships it.":
        "Cada rótulo exactamente como lo trae la app.",
    "Menus, buttons and dialogs are translated. Track names, dance names and anything read from your files stay as they are.":
        "Los menús, botones y diálogos se traducen. Los nombres de los temas, de los bailes y todo lo que se lee de tus archivos se queda como está.",
    "<b>🖥 Presenter screen</b> — the colours it wears:":
        "<b>🖥 Presentación</b> — los colores que lleva:",
    "<b>🎚 Accent colour</b> — the blue the buttons, sliders and the ▶ player panel are built around:":
        "<b>🎚 Color de acento</b> — el azul en torno al que se construyen los botones, los deslizadores y el panel ▶ del reproductor:",
    "<b>🎚 TSO pitch target</b> — which takt the 🎚 button pitches a heat to. <i>Middle of the round</i> puts the round on one takt: the takt most of its titles are on where a step of one gets the rest there cheaply (T30+T31+T31 Cha-Chas → 31), the middle of its takte where it does not (T24+T25+T25 Rumbas → 24.5, T50+T52+T52 Quicksteps → 51). Nothing moves more than a takt. A fixed takt puts every title of that dance on the same tempo instead — worth setting on the slow dances, where one takt out of 24 is twice the pitch shift one takt out of 50 is.":
        "<b>🎚 Objetivo de tono TSO</b> — a qué compás lleva el botón 🎚 un grupo. <i>Media de la ronda</i> pone la ronda en un solo compás: el compás en el que están la mayoría de sus títulos, si un paso de uno lleva al resto allí con poco coste (Cha-Chas T30+T31+T31 → 31), y el punto medio de sus compases si no (Rumbas T24+T25+T25 → 24,5, Quicksteps T50+T52+T52 → 51). Nada se mueve más de un compás. Un compás fijo pone en cambio cada título de ese baile en el mismo tempo — vale la pena en los bailes lentos, donde un compás de 24 es el doble de cambio de tono que un compás de 50.",
    "<b>🎛 Play sets</b> — the two buttons on the ▶ Playing panel put the controls on these values in one press:":
        "<b>🎛 Sets de reproducción</b> — los dos botones del panel ▶ Reproducción ponen los controles en estos valores con una sola pulsación:",
    "<b>🎨 Theme</b> — the classic light or dark, or one of the looks:":
        "<b>🎨 Tema</b> — el clásico claro u oscuro, o uno de los aspectos:",
    "<b>🎵 Check music</b> — thresholds used by the tournament checks (open decks and dragged-in files):":
        "<b>🎵 Comprobar música</b> — umbrales de las comprobaciones de torneo (decks abiertos y archivos arrastrados):",
    "<b>🔊 Audio backend</b> — the engine every title is played through:":
        "<b>🔊 Motor de audio</b> — el motor con el que se reproduce cada título:",
    "Build everything on this tab in one go for a chosen library, in turn:\n"
    "🎚 librosa → 📊 loudness → 🔇 silences → 🐂 PD highlights → 🧠 MERT →\n"
    "🎼 Chroma. Reuses anything already cached and can be cancelled\n"
    "between/within steps. Read-only; your audio files are never modified.\n"
    "Skips models that aren't installed — and 🎙 Demucs vocals, which are far\n"
    "slower than the rest and stay a deliberate choice.":
        "Crear todo lo de esta pestaña de una vez para una biblioteca elegida, por turnos:\n"
        "🎚 librosa → 📊 sonoridad → 🔇 silencios → 🐂 clímax de PD → 🧠 MERT →\n"
        "🎼 Chroma. Reutiliza todo lo que ya está en caché y se puede cancelar\n"
        "entre pasos o durante ellos. Solo lectura; tus archivos de audio nunca se modifican.\n"
        "Omite los modelos no instalados — y las voces 🎙 Demucs, que son mucho\n"
        "más lentas que el resto y quedan como decisión aparte.",
    "Chroma vectors match melody/harmony instead of sound, so the\n"
    "Similar-Tracks window can find remixes & covers of the same tune.\n"
    "librosa-only; reuses anything already cached.":
        "Los vectores chroma comparan melodía/armonía en lugar de sonido, para que\n"
        "la ventana de temas similares encuentre remixes y versiones de la misma canción.\n"
        "Solo con librosa; reutiliza todo lo que ya está en caché.",
    "Close this and filter the library pane to the selected\n"
    "row's dance + class, showing only tracks you have never played.":
        "Cerrar esto y filtrar el panel de la biblioteca por el baile + clase\n"
        "de la fila seleccionada, mostrando solo temas que nunca has puesto.",
    "Compute the selected similarity index over the library (global repo\n"
    "when global search is on, else the favorites library). Reuses anything\n"
    "already cached; only missing vectors are added.":
        "Calcular el índice de similitud elegido sobre la biblioteca (el repositorio global\n"
        "si la búsqueda global está activada, si no la biblioteca de favoritos). Reutiliza todo\n"
        "lo que ya está en caché; solo se añaden los vectores que faltan.",
    "Detect the highlights of every Paso Doble in the music library\n"
    "and store them in the local database, so the highlight stop is\n"
    "armed instantly on playback (already-analyzed tracks are skipped).":
        "Detectar los clímax de cada Paso Doble de la biblioteca de música\n"
        "y guardarlos en la base de datos local, para que la parada en el clímax\n"
        "esté lista al instante al reproducir (los temas ya analizados se omiten).",
    "Find the silent stretches of every track of the music library\n"
    "(via ffmpeg; already-probed tracks are skipped, results are\n"
    "cached). Playback probes each new title itself — doing it up\n"
    "front keeps that decode off the disk during a tournament.":
        "Encontrar los tramos silenciosos de cada tema de la biblioteca de música\n"
        "(con ffmpeg; los temas ya sondeados se omiten, los resultados se\n"
        "guardan en caché). La reproducción sondea cada título nuevo por sí misma — hacerlo\n"
        "antes evita esa decodificación en el disco durante un torneo.",
    "Global search needs the repo's audio analyzed once (⚗ Analysis tab). Analysis only <i>reads</i> your files — it never modifies them. Results are cached, so repeat searches are fast.":
        "La búsqueda global necesita analizar el audio del repositorio una vez (pestaña ⚗ Análisis). El análisis solo <i>lee</i> tus archivos — nunca los modifica. Los resultados se guardan en caché, así que las búsquedas repetidas son rápidas.",
    "Shorter by %s s": "%s s más corto",
    "Longer by %s s — past %s the title plays to its end":
        "%s s más largo — a partir de %s el título suena hasta el final",
    "Tempo %s %s — hold to glide":
        "Tempo %s %s — mantén pulsado para deslizar",
    "slower": "más lento",
    "faster": "más rápido",
    "How long the volume takes to ramp down to 0 when\n"
    "the play length cuts a title — half-second steps":
        "Cuánto tarda el volumen en bajar a 0 cuando\n"
        "la duración de reproducción corta un título — en pasos de medio segundo",
    "Invalid rounds": "Rondas no válidas",
    "Library gap dashboard: per dance × class — pool size, tournament-\n"
    "tempo compliance, proven/fresh split and staleness. Thin pools\n"
    "are marked red.":
        "Panel de huecos de la biblioteca: por baile × clase — tamaño del fondo, cumplimiento\n"
        "del tempo de torneo, reparto probados/nuevos y antigüedad. Los fondos escasos\n"
        "se marcan en rojo.",
    "Measure each track's vocal share by actually separating the vocals\n"
    "from the music (Demucs source separation) — far more reliable than\n"
    "the tag/filename heuristics for the Vocal/Instrumental filter.\n"
    "~7 s per track, cached; already-measured tracks are skipped.":
        "Medir la proporción de voz de cada tema separando de verdad las voces\n"
        "de la música (separación de fuentes Demucs) — mucho más fiable que\n"
        "las heurísticas de etiquetas/nombre de archivo para el filtro Voz/Instrumental.\n"
        "~7 s por tema, en caché; los temas ya medidos se omiten.",
    "Measure the EBU R128 loudness of every track of the music\n"
    "library (via ffmpeg; already-measured tracks are skipped,\n"
    "results are cached). Enables 🔊 Equalize volume in Playing mode.":
        "Medir la sonoridad EBU R128 de cada tema de la biblioteca\n"
        "de música (con ffmpeg; los temas ya medidos se omiten,\n"
        "los resultados se guardan en caché). Activa 🔊 Igualar volumen en el modo Reproducción.",
    "One row per competition — each fills its own 📅 day deck on the\n"
    "Tournament-day tab; more than 8 competitions share decks (labeled\n"
    "round headers). All competitions share one no-repeat pool for the day (Paso Doble may repeat).":
        "Una fila por competición — cada una llena su propio 📅 deck del día en la\n"
        "pestaña Día de torneo; con más de 8 competiciones comparten decks (con\n"
        "cabeceras de ronda rotuladas). Todas las competiciones comparten un fondo sin repeticiones para el día (el Paso Doble puede repetirse).",
    "Only change this if the sound gives you trouble: a title that\n"
    "won't play, or the short gap a pitch change costs — the two\n"
    "engines handle that differently. Takes effect on the next start.":
        "Cámbialo solo si el sonido da problemas: un título que\n"
        "no suena, o el pequeño corte que cuesta un cambio de tono — los dos\n"
        "motores lo manejan de forma distinta. Se aplica en el próximo inicio.",
    "Only the accent's own family of tints follows this colour.\n"
    "A red warning, a green proven mark and the popularity amber mean\n"
    "something, so they keep their hue.":
        "Solo la propia familia de tonos del acento sigue este color.\n"
        "Una advertencia roja, una marca verde de probado y el ámbar de popularidad\n"
        "significan algo, así que conservan su tono.",
    "Planner only hides the tournament floor's playing panel;\n"
    "Player only hides everything that generates or checks a playlist.\n"
    "Nothing is removed — switching back brings it all straight back.":
        "Solo planificador oculta solo el panel de reproducción de la pista del torneo;\n"
        "Solo reproductor oculta solo lo que genera o comprueba una lista.\n"
        "No se quita nada — al volver atrás todo reaparece al instante.",
    "Playlists still build and play without it. These need it and stay unavailable:<ul><li>analysing the library — tempo, similar tracks</li><li>🔊 loudness levelling (EBU R128)</li><li>🔇 silence detection at the start and end of a track</li></ul>":
        "Las listas se pueden crear y reproducir sin él. Esto lo necesita y queda no disponible:<ul><li>analizar la biblioteca — tempo, temas similares</li><li>🔊 nivelación de sonoridad (EBU R128)</li><li>🔇 detección de silencio al principio y al final de un tema</li></ul>",
    "Re-read every M3U and tournament music folder in the tournament\n"
    "playlist folder and rebuild the popularity / co-occurrence index from\n"
    "it — WITHOUT rescanning files or audio. Use after exporting a played\n"
    "tournament so it counts right away.":
        "Volver a leer cada M3U y cada carpeta de música de torneo en la carpeta de\n"
        "listas de torneo y reconstruir con ellos el índice de popularidad / coaparición\n"
        "— SIN volver a explorar archivos ni audio. Úsalo tras exportar un torneo\n"
        "ya celebrado para que cuente de inmediato.",
    "Remove cached rows for music files that no longer exist (features,\n"
    "embeddings, loudness, …) and compact the database file (VACUUM).\n"
    "Slow on a big library; refuses to run when the music drive looks\n"
    "unmounted so cached analysis can't be wiped by accident.":
        "Quitar las filas en caché de archivos de música que ya no existen (características,\n"
        "embeddings, sonoridad, …) y compactar el archivo de la base de datos (VACUUM).\n"
        "Lento en una biblioteca grande; se niega a ejecutarse si la unidad de música parece\n"
        "desmontada, para que el análisis guardado no se borre por accidente.",
    "Run librosa on the favorites library's MP3 files not yet cached.\n"
    "Required for timbral similarity scoring; when everything is cached\n"
    "a click offers a full re-analysis (e.g. after a tempo-method change).":
        "Ejecutar librosa sobre los MP3 de la biblioteca de favoritos aún sin caché.\n"
        "Necesario para puntuar la similitud de timbre; cuando todo está en caché\n"
        "un clic ofrece un nuevo análisis completo (p. ej. tras cambiar el método de tempo).",
    "Scan the whole repository and analyze any files not yet cached, using the\n"
    "fast librosa timbre+rhythm features (the default similarity method).\n"
    "Read-only; runs in the background and can be left to finish.":
        "Explorar todo el repositorio y analizar los archivos aún sin caché, con las\n"
        "rápidas características de timbre+ritmo de librosa (el método de similitud predeterminado).\n"
        "Solo lectura; se ejecuta en segundo plano y puede dejarse terminar.",
    "Takes effect after restarting the app. If the sound stays away afterwards, switch back here — the setting is only read at start, so nothing else in the app depends on it.":
        "Se aplica tras reiniciar la app. Si después sigue sin haber sonido, vuelve a cambiarlo aquí — el ajuste solo se lee al iniciar, así que nada más en la app depende de él.",
    "🐂 Each set carries its own Paso Doble values. Under 🏆 the highlight stop is <i>off</i> by default: the detection is not good enough yet to cut a competition Paso Doble on, and a heat stopped in the wrong bar is danced twice. Under 🎉 it stops after the 2nd highlight and waits 3 s, so the couples can take their position.":
        "Cada set tiene sus propios valores 🐂 de Paso Doble. En 🏆 la parada en el clímax está <i>desactivada</i> por defecto: la detección aún no es lo bastante buena para cortar un Paso Doble de competición, y una ronda parada en el compás equivocado se baila dos veces. En 🎉 para tras el 2.º clímax y espera 3 s, para que las parejas tomen su posición.",
    "Shut the music off at the chosen highlight instead of\nthe play length. On by default: at a party the\nPaso Doble ends on its 2nd highlight.":
        "Apagar la música en el clímax elegido en lugar de en la\nduración. Activado por defecto: en una fiesta el\nPaso Doble termina en su 2.º clímax.",
    "Hold a Paso Doble back this long before the music\nstarts, so the couples can take their position.":
        "Retener un Paso Doble este tiempo antes de que empiece\nla música, para que las parejas tomen su posición.",
    "🐂  Paso Doble: stop after highlight":
        "🐂  Paso Doble: parar tras el clímax",
    "Shut the music off at the chosen highlight instead of\nthe play length. Off by default: a highlight detected\nin the wrong bar cuts the heat short.":
        "Apagar la música en el clímax elegido en lugar de en la\nduración. Desactivado por defecto: un clímax detectado\nen el compás equivocado corta la ronda antes de tiempo.",
    "Hold a Paso Doble back this long before the music\nstarts. 0 s = at once: at a competition the couples\nstand before the music, the chairman's call is the wait.":
        "Retener un Paso Doble este tiempo antes de que empiece\nla música. 0 s = enseguida: en competición las parejas\nesperan antes de la música, la llamada del juez es la espera.",
    "Theme, accent and language are read when the app starts, so a change takes effect after a restart — you are asked once you save.":
        "El tema, el acento y el idioma se leen al iniciar la app, así que un cambio se aplica tras reiniciar — se te pregunta al guardar.",
    "Keep the German dance and round names on a screen in another language (Langsamer Walzer, Vorrunde, Standardrunde 1, Eintanzen …)":
        "Mantener los nombres alemanes de bailes y rondas en una pantalla en otro idioma (Langsamer Walzer, Vorrunde, Standardrunde 1, Eintanzen …)",
    "On: the presenter screen and the recorded announcements are German too, a 🤸 practice list is called Eintanzen, also in its saved file, and the tempo rules are named TSO (off: WDSF CR).\n"
    "Off: Slow Waltz, Round 1, Standard round 1, Practice … — the playlists and exports keep the German dance and round names either way.":
        "Activado: la pantalla de presentación y los anuncios grabados también son en alemán, una lista 🤸 de práctica se llama Eintanzen, también en su archivo guardado, y las reglas de tempo se llaman TSO (desactivado: WDSF CR).\n"
        "Desactivado: Slow Waltz, Round 1, Standard round 1, Práctica … — las listas y exportaciones conservan los nombres alemanes de bailes y rondas en cualquier caso.",
    "You can change this later under ⚙ Settings → ⚙ General.":
        "Puedes cambiarlo más tarde en ⚙ Ajustes → ⚙ General.",
    "lower": "bajo",
    "middle": "medio",
    "upper": "alto",
    "⚠️  <b>ffmpeg is not installed on this computer.</b>":
        "⚠️  <b>ffmpeg no está instalado en este ordenador.</b>",
    "🌐  Global search — match dropped files against the whole repository (default: favorites library only)":
        "🌐  Búsqueda global — comparar los archivos soltados con todo el repositorio (predeterminado: solo la biblioteca de favoritos)",
    "🎧  Preview player — float a mini player (seek / skip / volume) over the deck when a ▶ button is clicked":
        "🎧  Reproductor de vista previa — mostrar un mini reproductor (avance / salto / volumen) sobre el deck al pulsar un botón ▶",
    "🐘 Heavy — AI models, needs the FULL build (or the requirements-full.txt extras)":
        "🐘 Pesado — modelos de IA, necesita la versión COMPLETA (o los extras de requirements-full.txt)",
    "🔇  Release the sound card between titles — takes away the hiss an onboard output puts on the PA while the app holds it open":
        "🔇  Liberar la tarjeta de sonido entre títulos — quita el siseo que una salida integrada mete en el equipo de sonido mientras la app la mantiene abierta",
    "🔕  Mute system sounds while the evening runs — no error ding or notification chime over the speakers":
        "🔕  Silenciar los sonidos del sistema durante la velada — ningún aviso de error ni de notificación por los altavoces",
    "🐞  Send error reports — when the app hits an error, send its technical details to the developer":
        "🐞  Enviar informes de errores — cuando la app encuentra un error, envía sus detalles técnicos al desarrollador",
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
        "Se envía al proyecto GlitchTip del desarrollador (app.glitchtip.com),\n"
        "que también ve la dirección IP de la que procede un informe.\n"
        "\n"
        "Se envía: el error y en qué parte del programa ocurrió, las últimas\n"
        "líneas del registro antes de él (pueden nombrar el título que sonaba),\n"
        "el sistema operativo y la versión de la app.\n"
        "\n"
        "No se envía: tu música, tus listas, el nombre de tu ordenador.\n"
        "Tu carpeta de usuario se recorta de cada ruta.\n"
        "\n"
        "Desactivado por defecto. Se aplica en cuanto guardas.",
    "Error reports": "Informes de errores",
    "Send error reports to the developer?":
        "¿Enviar informes de errores al desarrollador?",
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
        "Cuando la app encuentra un error, puede enviar los detalles técnicos\n"
        "al proyecto GlitchTip del desarrollador (app.glitchtip.com),\n"
        "para que el error se corrija. GlitchTip también ve la dirección IP\n"
        "de la que procede un informe.\n"
        "\n"
        "Responsable: marcelkb, el desarrollador. Preguntas sobre tus datos\n"
        "o borrado de informes: github.com/dancesport-dj/DanceSportPlayer/issues\n"
        "\n"
        "Se envía: el error y en qué parte del programa ocurrió, las últimas\n"
        "líneas del registro antes de él (pueden nombrar el título que sonaba),\n"
        "el sistema operativo y la versión de la app.\n"
        "\n"
        "No se envía: tu música, tus listas, el nombre de tu ordenador.\n"
        "Tu carpeta de usuario se recorta de cada ruta.\n"
        "\n"
        "Puedes cambiarlo en cualquier momento en ⚙ Ajustes → ⚙ General.",
    "Send reports": "Enviar informes",
    "Don't send": "No enviar",
    "Once per start, the app asks GitHub (api.github.com) for the latest\n"
    "release. The request carries nothing about you or your music; GitHub\n"
    "sees the IP address it comes from. A newer version is announced once,\n"
    "with a link to its download page. Nothing is downloaded or installed.\n"
    "\n"
    "You can change this at any time under ⚙ Settings → ⚙ General.":
        "Una vez por inicio, la app pregunta a GitHub (api.github.com) por la\n"
        "última versión publicada. La petición no lleva nada sobre ti ni sobre tu\n"
        "música; GitHub ve la dirección IP de la que procede. Una versión más\n"
        "nueva se anuncia una sola vez, con un enlace a su página de descarga.\n"
        "No se descarga ni se instala nada.\n"
        "\n"
        "Puedes cambiarlo en cualquier momento en ⚙ Ajustes → ⚙ General.",
    "🔔  Also tell me when a new version is out":
        "🔔  Avísame también cuando salga una versión nueva",
    "New versions": "Versiones nuevas",
    "Tell you when a new version is out?": "¿Avisarte cuando salga una versión nueva?",
    "Check for new versions": "Buscar versiones nuevas",
    "Don't check": "No buscar",
    "🔔  Check for new versions — once per start, ask GitHub whether a newer release is out":
        "🔔  Buscar versiones nuevas — una vez por inicio, preguntar a GitHub si hay una versión más reciente",
    "Asks api.github.com for the latest release. The request carries\n"
    "nothing about you or your music; GitHub sees the IP address it\n"
    "comes from. A newer version is announced once, with a link to\n"
    "its download page. Nothing is downloaded or installed.\n"
    "\n"
    "Off by default. Applies from the next start.":
        "Pregunta a api.github.com por la última versión publicada. La petición\n"
        "no lleva nada sobre ti ni sobre tu música; GitHub ve la dirección IP de\n"
        "la que procede. Una versión más nueva se anuncia una sola vez, con un\n"
        "enlace a su página de descarga. No se descarga ni se instala nada.\n"
        "\n"
        "Desactivado por defecto. Se aplica a partir del próximo inicio.",
    "New version": "Versión nueva",
    "Version %s is out.": "Ya está disponible la versión %s.",
    "You are running %s. The download page lists what changed.":
        "Usas la %s. La página de descarga indica qué ha cambiado.",
    "Open download page": "Abrir página de descarga",
    "Later": "Más tarde",
    "The music and the computer share the one sound card, so every\n"
    "sound the system makes goes out over the PA too.\n"
    "\n"
    "Muted all through Playing mode and whenever something plays,\n"
    "put back when you return to planning or close the app.\n"
    "Windows: the System Sounds slider of the volume mixer.\n"
    "macOS: the alert volume. Linux (GNOME): event sounds.":
        "La música y el ordenador comparten la misma tarjeta de sonido, así que\n"
        "cada sonido del sistema sale también por la megafonía.\n"
        "\n"
        "Silenciado durante todo el modo Reproducir y siempre que algo suena,\n"
        "restablecido al volver a planificar o al cerrar la app.\n"
        "Windows: el control Sonidos del sistema del mezclador de volumen.\n"
        "macOS: el volumen de alertas. Linux (GNOME): sonidos de eventos.",
    "🧭 Fix paths tries the Reference path first and then these folders,\n"
    "in order, cutting the foreign path down until what is left lands on a\n"
    "real file underneath one of them. A path is only ever rewritten to a\n"
    "file that is actually there.":
        "🧭 Reparar rutas prueba primero la ruta de referencia y luego estas carpetas,\n"
        "en orden, recortando la ruta ajena hasta que lo que queda cae en un\n"
        "archivo real debajo de una de ellas. Una ruta solo se reescribe hacia\n"
        "un archivo que existe de verdad.",
    "Drag <b>.m3u playlists</b> here (audio files work too) to check whether any of their tracks are duplicates of <b>each other</b> — across the dropped playlists, by audio content, else title.":
        "Arrastra aquí <b>listas .m3u</b> (también sirven archivos de audio) para comprobar si alguno de sus temas es un duplicado de <b>otro</b> — entre las listas soltadas, por contenido de audio, si no por título.",
    "Drop a <b>reference playlist</b> (.m3u) and the <b>tournament files</b> (.m3u playlists or audio) below. The reference is compared against the tournament tracks and every <b>hard duplicate</b> (byte-identical audio) is removed; the leftover <b>unused</b> tracks are exported to a new .m3u. <span style='color:#666'>Paso Doble is excluded from the comparison and always kept.</span>":
        "Suelta abajo una <b>lista de referencia</b> (.m3u) y los <b>archivos del torneo</b> (listas .m3u o audio). La referencia se compara con los temas del torneo y se quita cada <b>duplicado exacto</b> (audio idéntico byte a byte); los temas <b>sin usar</b> que quedan se exportan a un nuevo .m3u. <span style='color:#666'>El Paso Doble queda fuera de la comparación y siempre se conserva.</span>",
    "Duplicate songs across your open playlist(s), in playlist order.<br><span style='color:#666'>🟰 <b>Exact</b> = identical audio. ≈ <b>Similar</b> = same title, a different recording. Keep the ones you want; switch the others to <b>Replace</b> and pick a track for each, or to <b>Remove</b>.</span>":
        "Canciones duplicadas en tus listas abiertas, en el orden de la lista.<br><span style='color:#666'>🟰 <b>Exacto</b> = audio idéntico. ≈ <b>Similar</b> = mismo título, otra grabación. Conserva las que quieras; pon las demás en <b>Reemplazar</b> y elige un tema para cada una, o en <b>Quitar</b>.</span>",
    "Every copy of this song is already controlled by the within-playlist\n"
    "section above, so there is nothing left to resolve on this row.":
        "Cada copia de esta canción ya la controla la sección\n"
        "«dentro de la lista» de arriba, así que en esta fila no queda nada que resolver.",
    "Export unused tracks": "Exportar temas sin usar",
    "No hard duplicates of the tournament files were found in the reference — nothing to remove.":
        "No se encontraron duplicados exactos de los archivos del torneo en la referencia — nada que quitar.",
    "Nothing to change — no occurrence is set to Replace or Remove.":
        "Nada que cambiar — ninguna aparición está en Reemplazar o Quitar.",
    "Reference base": "Base de referencia",
    "Resolve duplicates": "Resolver duplicados",
    "Sort the exported tracks by dance?\n"
    "\n"
    "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)":
        "¿Ordenar los temas exportados por baile?\n"
        "\n"
        "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)",
    "The reference base must be a single .m3u playlist.":
        "La base de referencia debe ser una sola lista .m3u.",
    "This list holds some titles more than once.<br><span style='color:#666'>For each title, pick the file to keep — the others are removed. <b>Keep all</b> leaves that title alone.</span>":
        "Esta lista contiene algunos títulos más de una vez.<br><span style='color:#666'>Para cada título, elige el archivo que se queda — los demás se quitan. <b>Conservar todos</b> deja ese título como está.</span>",
    "Browse by library category — 🏆 Tournament hides the non-tournament\n"
    "folders (anthems, background, wrong-tempo, duplicates, seasonal);\n"
    "pick a category to look only at those (handy for parties).":
        "Explorar por categoría de la biblioteca — 🏆 Torneo oculta las carpetas\n"
        "ajenas al torneo (himnos, fondo, tempo erróneo, duplicados, de temporada);\n"
        "elige una categoría para ver solo esa (práctico para fiestas).",
    "Drag a track onto a deck or wishlist to use it.\n"
    "▶ to preview · double-click to open in your external player\n"
    "· right-click for more.":
        "Arrastra un tema a un deck o a una lista de deseos para usarlo.\n"
        "▶ para escuchar · doble clic para abrirlo en tu reproductor externo\n"
        "· clic derecho para más.",
    "Only tracks suited for one of the ticked starting classes\n(tick several; tracks without a class tag show only with all classes)":
        "Solo pistas adecuadas para una de las clases de inicio marcadas\n(se pueden marcar varias; las pistas sin clase solo con todas las clases)",
    "Only tracks whose file was created in the library that\n"
    "recently. Combine with ✦ Never played to see what you\n"
    "copied in but have never actually used.":
        "Solo temas cuyo archivo se creó en la biblioteca hace tan poco.\n"
        "Combínalo con ✦ Nunca sonado para ver lo que copiaste\n"
        "pero nunca llegaste a usar.",
    "Show only tracks not already used in any open playlist deck —\n"
    "handy for finding fresh music while building rounds.":
        "Mostrar solo temas que no se usan ya en ningún deck de lista abierto —\n"
        "práctico para encontrar música nueva al montar rondas.",
    "Substring of the title, the artist, or a comment marker\n"
    "(vocal_f, classic, eintanzen, …)":
        "Parte del título, del artista o de una marca de comentario\n"
        "(vocal_f, classic, eintanzen, …)",
    "proven": "probado",
    "rare": "raro",
    "Audio analysis unavailable": "Análisis de audio no disponible",
    "Audio cache not ready yet — try again shortly.":
        "La caché de audio aún no está lista — inténtalo de nuevo en un momento.",
    "Build ALL caches": "Construir TODAS las cachés",
    "Build all caches": "Construir todas las cachés",
    "Analyze loudness": "Analizar sonoridad",
    "Analyze vocals (Demucs)": "Analizar voces (Demucs)",
    "No Paso Doble tracks in the library.":
        "No hay temas de Paso Doble en la biblioteca.",
    "Probe silences": "Sondear silencios",
    "Re-analyze Audio": "Reanalizar audio",
    "Redo the 🐂 auto-detection for the whole library — for after the\n"
    "detector changed. Hand-set 🎯 marks are kept untouched.":
        "Repetir la detección automática 🐂 para toda la biblioteca — para cuando\n"
        "el detector haya cambiado. Las marcas 🎯 puestas a mano no se tocan.",
    "The music library is not loaded yet.":
        "La biblioteca de música aún no está cargada.",
    "ffmpeg was not found (neither on PATH nor the copy bundled\n"
    "with the project) — loudness cannot be measured.":
        "No se encontró ffmpeg (ni en el PATH ni la copia incluida\n"
        "con el proyecto) — no se puede medir la sonoridad.",
    "ffmpeg was not found (neither on PATH nor the copy bundled\n"
    "with the project) — silences cannot be probed.":
        "No se encontró ffmpeg (ni en el PATH ni la copia incluida\n"
        "con el proyecto) — no se pueden sondear los silencios.",
    "Clear playlists": "Vaciar listas",
    "Clear tournament day": "Vaciar el día de torneo",
    "Close tournament day": "Cerrar el día de torneo",
    "Competition name (empty = default):":
        "Nombre de la competición (vacío = predeterminado):",
    "Competition name:": "Nombre de la competición:",
    "Free order": "Orden libre",
    "None of these tracks says which dance it is, so there is no grid to build from them — the list stays a free running order.":
        "Ninguno de estos temas indica qué baile es, así que no hay cuadrícula que montar con ellos — la lista sigue siendo un orden libre.",
    "New tournament day": "Nuevo día de torneo",
    "Rename tournament day": "Renombrar el día de torneo",
    "Shuffle — put the same titles in a fresh order,\n"
    "as if the party list were built again from scratch.":
        "Mezclar — poner los mismos títulos en un orden nuevo,\n"
        "como si la lista de fiesta se creara otra vez desde cero.",
    "Total play time of this playlist\n"
    "(↳ backup rows not counted — they only play as stand-ins)\n"
    "Click ▸ for the songs per dance":
        "Duración total de esta lista\n"
        "(las filas ↳ de reserva no cuentan — solo suenan como sustitutas)\n"
        "Haz clic en ▸ para ver las canciones por baile",
    "Every similar track is already in an open playlist.":
        "Todos los temas similares ya están en una lista abierta.",
    "No similar tracks found — the song may not be audio-analyzed yet.":
        "No se encontraron temas similares — puede que la canción aún no tenga análisis de audio.",
    "Replace duplicate": "Reemplazar duplicado",
    "Audio index": "Índice de audio",
    "Audio index ready": "Índice de audio listo",
    "Build audio index": "Construir índice de audio",
    "Embedding index error": "Error del índice de embeddings",
    "Favorites library isn't loaded yet.":
        "La biblioteca de favoritos aún no está cargada.",
    "The whole-repository library isn't loaded yet. Drop a file (or build the librosa index over the repository) once to load it, then retry.":
        "La biblioteca de todo el repositorio aún no está cargada. Suelta un archivo (o construye el índice librosa sobre el repositorio) una vez para cargarla y vuelve a intentarlo.",
    "Not on the Reference path": "No está en la ruta de referencia",
    "Save Error": "Error al guardar",
    "Save as M3U": "Guardar como M3U",
    "This deck is empty.": "Este deck está vacío.",
    "Fold this playlist to a tab —\n"
    "the other open playlists get its space.":
        "Plegar esta lista en una pestaña —\n"
        "las otras listas abiertas ocupan su espacio.",
    "AI playlist": "Lista con IA",
    "AI playlist failed": "La lista con IA falló",
    "All picks are TSO-conform (T24 Rumba / T58-59 Paso allowed, like the normal playlist).":
        "Todas las elecciones cumplen el TSO (se permiten Rumba T24 / Paso T58-59, como en la lista normal).",
    "Cap the party-list length — handy when drawing from the whole library.\n"
    "The round it lands in is played out, so the list can run a title or two over.\n"
    "0 = No limit (use every eligible track).":
        "Limitar la longitud de la lista de fiesta — práctico al tomar de toda la biblioteca.\n"
        "La ronda en la que cae se toca entera, así que la lista puede pasarse uno o dos títulos.\n"
        "0 = Sin límite (usar todos los temas aptos).",
    "Choose an .m3u file first.": "Elige primero un archivo .m3u.",
    "Dances come in alternating 3-dance rounds (not competition rounds).":
        "Los bailes llegan en rondas alternas de 3 bailes (no rondas de competición).",
    "Day plan": "Plan del día",
    "Draw from your library, exactly like the left panel's Favorites mode.":
        "Tomar de tu biblioteca, exactamente como el modo Favoritos del panel izquierdo.",
    "Draw only from the tracks currently parked in your open ⭐ wishlists.":
        "Tomar solo de los temas que ahora están en tus ⭐ listas de deseos abiertas.",
    "Practice Error": "Error de práctica",
    "Enter a valid round pattern (e.g. 6-3-2-1).":
        "Introduce un esquema de rondas válido (p. ej. 6-3-2-1).",
    "Generate Error": "Error al generar",
    "History Error": "Error del historial",
    "Library gaps": "Huecos de la biblioteca",
    "No Competition": "Sin competición",
    "No Dances": "Sin bailes",
    "No Matches": "Sin coincidencias",
    "No Rounds": "Sin rondas",
    "No Theme": "Sin temática",
    "No candidate tracks for those settings — check the dances, the\n"
    "start class and that the library actually holds those tempos.":
        "No hay temas candidatos para estos ajustes — revisa los bailes, la\n"
        "clase de inicio y que la biblioteca tenga de verdad esos tempos.",
    "No matching tracks for the chosen options — check the class, the source and that the library / .m3u actually has those dances.":
        "No hay temas que encajen con las opciones elegidas — revisa la clase, la fuente y que la biblioteca / el .m3u tenga de verdad esos bailes.",
    "No resolvable tracks in that .m3u file.":
        "Ningún tema de ese archivo .m3u se pudo resolver.",
    "Paste a schedule and click 'Parse schedule', then pick a competition.":
        "Pega un horario, haz clic en «Analizar horario» y luego elige una competición.",
    "Pick at least Standard or Latin dances.":
        "Elige al menos bailes Standard o Latin.",
    "Please select a theme.": "Elige una temática.",
    "Please select at least one dance.": "Elige al menos un baile.",
    "Replace day plan": "Reemplazar el plan del día",
    "Share of slots that lean FRESH (least-played) instead of proven favourites.\n"
    "Higher = more never/barely-played tracks — at 100 % the list is\n"
    "built from the least-played tracks upward (not just the few with zero plays).":
        "Proporción de huecos que se inclinan a lo NUEVO (lo menos tocado) en vez de a favoritos probados.\n"
        "Más alto = más temas nunca o apenas tocados — al 100 % la lista se\n"
        "monta desde los temas menos tocados hacia arriba (no solo los pocos sin ninguna reproducción).",
    "The Tournament-day tab still holds an earlier day plan.\n"
    "\n"
    "Replace it with the new one?":
        "La pestaña Día de torneo aún contiene un plan del día anterior.\n"
        "\n"
        "¿Reemplazarlo por el nuevo?",
    "The library is still loading — try again in a moment.":
        "La biblioteca aún se está cargando — inténtalo de nuevo en un momento.",
    "The model answered, but none of its picks matched the\n"
    "catalog. Try again — or lower the round count.":
        "El modelo respondió, pero ninguna de sus elecciones coincidió con el\n"
        "catálogo. Inténtalo de nuevo — o baja el número de rondas.",
    "The model answered, but none of its picks matched the catalog.":
        "El modelo respondió, pero ninguna de sus elecciones coincidió con el catálogo.",
    "The selected competition has no valid heat counts.":
        "La competición elegida no tiene números de grupos válidos.",
    "The wish list is empty — write the titles you want, one\n"
    "per line or a column per dance.":
        "La lista de deseos está vacía — escribe los títulos que quieras, uno\n"
        "por línea o una columna por baile.",
    "Theme Error": "Error de temática",
    "Upper limit. The list stops here or when the TSO-conform pool runs dry — whichever comes first.":
        "Límite superior. La lista se detiene aquí o cuando se agota el conjunto conforme al TSO — lo que ocurra primero.",
    "Your open wishlists are empty — park some tracks there first.":
        "Tus listas de deseos abiertas están vacías — deja primero algunos temas allí.",
    "🆕 This competition has no saved work yet — press ⚡ Generate from History to seed it":
        "🆕 Esta competición aún no tiene trabajo guardado — pulsa ⚡ Generar desde el historial para iniciarla",
    "🏆  Practice for a tournament class (round-robin through the class's dances)":
        "🏆  Práctica para una clase de torneo (los bailes de la clase por turnos)",
    "Analysis Error": "Error de análisis",
    "Build librosa index": "Construir índice librosa",
    "Clean up database": "Limpiar la base de datos",
    "Could not start a new instance — please start the app again yourself.":
        "No se pudo iniciar una nueva instancia — inicia la app tú mismo de nuevo.",
    "Finding similar tracks for a file needs librosa + ffmpeg.\n"
    "Install them, then retry.":
        "Buscar temas similares a un archivo necesita librosa + ffmpeg.\n"
        "Instálalos y vuelve a intentarlo.",
    "Global Index Error": "Error del índice global",
    "Global search": "Búsqueda global",
    "Library Load Error": "Error al cargar la biblioteca",
    "Re-learn playlists": "Reaprender listas",
    "Set a valid music repository folder first.":
        "Define primero una carpeta válida para el repositorio de música.",
    "Set a valid music repository folder in ⚙ Settings first.":
        "Define primero una carpeta válida para el repositorio de música en ⚙ Ajustes.",
    "Settings saved": "Ajustes guardados",
    "Similar Tracks": "Temas similares",
    "The favorites library path changed.\n"
    "Restart the app to load the new library.":
        "La ruta de la biblioteca de favoritos cambió.\n"
        "Reinicia la app para cargar la nueva biblioteca.",
    "Couldn't detect any danceable tracks in that playlist.":
        "No se pudo reconocer ningún tema bailable en esa lista.",
    "Import Error": "Error de importación",
    "Import M3U": "Importar M3U",
    "Not enough free playlists": "No hay suficientes listas libres",
    "Nothing imported": "Nada importado",
    "Remove from the playlist(s) — the slot stays empty (Ctrl+Z undoes)":
        "Quitar de la(s) lista(s) — el hueco queda vacío (Ctrl+Z lo deshace)",
    "Drop <b>.m3u playlists</b> here — only playlists carry track paths to fix.":
        "Suelta aquí <b>listas .m3u</b> — solo las listas llevan rutas de temas que corregir.",
    "Fix & overwrite": "Corregir y sobrescribir",
    "Fix paths": "Reparar rutas",
    "No track paths that can be re-rooted under the search folders.":
        "No hay rutas de temas que se puedan reubicar bajo las carpetas de búsqueda.",
    "Set a Reference path or a search folder in Settings before fixing dropped playlists.":
        "Define una ruta de referencia o una carpeta de búsqueda en Ajustes antes de corregir las listas soltadas.",
    "⚠  No <b>search folder</b> set — open Settings and name the base folder(s) the music lives in on this PC.":
        "⚠  No hay <b>carpeta de búsqueda</b> — abre Ajustes e indica la(s) carpeta(s) base donde está la música en este PC.",
    "Clear all playlists": "Vaciar todas las listas",
    "Nothing to print — no songs found.":
        "Nada que imprimir — no se encontraron canciones.",
    "Print playlist": "Imprimir lista",
    "Add folder": "Añadir carpeta",
    "No alternative Practice track found.":
        "No se encontró otro tema de práctica.",
    "No alternative song found.": "No se encontró otra canción.",
    "Re-roll this song — best timbre match first  (Ctrl+R / Ctrl+N)":
        "Volver a sortear esta canción — primero la que mejor coincide en timbre  (Ctrl+R / Ctrl+N)",
    "Swap with a %s from the end of the list — a leftover that fits no round first, else one from the last third  (Ctrl+R / Ctrl+N)":
        "Cambiar por un %s del final de la lista — primero un sobrante que no encaja en ninguna ronda, si no uno del último tercio  (Ctrl+R / Ctrl+N)",
    "↺ click to swap it with a %s from the end of the list":
        "↺ clic para cambiarlo por un %s del final de la lista",
    "↺ click to re-roll a replacement": "↺ clic para sortear un sustituto",
    "🔁 Marked for potential replace  (Ctrl+M to toggle)":
        "🔁 Marcado para un posible cambio  (Ctrl+M lo alterna)",
    "⚠ File not found on disk:\n"
    "%s":
        "⚠ Archivo no encontrado en el disco:\n"
        "%s",
    "Regenerate": "Regenerar",
    "Regenerate Error": "Error al regenerar",
    "Track length (m:ss)\n"
    "orange = shorter than the configured play length, or 5 s or more\n"
    "of stillness at an edge that the player skips (the cell's own\n"
    "tooltip says which, and how long it really plays)":
        "Duración del tema (m:ss)\n"
        "naranja = más corto que la duración de reproducción configurada, o 5 s o más\n"
        "de silencio en un extremo que el reproductor salta (el tooltip de la\n"
        "propia celda dice cuál, y cuánto suena realmente)",
    "Wishlist": "Lista de deseos",
    "Rating — click a star to set it, the last lit one again to clear it.\n"
    "Kept in the app's database; the MP3 itself is not changed.":
        "Valoración — haz clic en una estrella para ponerla, otra vez en la última encendida para quitarla.\n"
        "Se guarda en la base de datos de la app; el MP3 no se modifica.",
    "≈  timbral similarity to round anchor\n"
    "    (only shown after running Audio Analysis)\n"
    "[D,C,…]  class tags from MP3 COMM field":
        "≈  similitud de timbre con el ancla de la ronda\n"
        "    (solo visible tras ejecutar el análisis de audio)\n"
        "[D,C,…]  clases del campo COMM del MP3",
    "Audio cache/library not available for this search.":
        "Caché de audio / biblioteca no disponible para esta búsqueda.",
    "Embedding error": "Error de embeddings",
    "Gaussian/KL: per-song MFCC distribution (mean+covariance)\n"
    "compared by symmetric KL — the Mandel-Ellis model, like the old Java\n"
    "app. Cleanest sound-alike ranking; genuine matches read ≳ 80 %.\n"
    "Librosa: fast hand-crafted timbre+rhythm vector (cosine).\n"
    "MERT: a pretrained neural music embedding — often closer to\n"
    "perceived 'sounds-alike'. Needs:  pip install torch transformers\n"
    "Chroma cover/remix: matches MELODY/harmony, not timbre — finds\n"
    "remixes & covers of the same tune even with a different sound,\n"
    "key or tempo. librosa only; build its index once like the others.\n"
    "Combined (default): where a title ranks by Gaussian/KL, librosa and chroma,\n"
    "averaged — the ones all three rank high come first.\n"
    "Combined + MERT: the same, with MERT as a fourth view.":
        "Gaussiano/KL: distribución MFCC por canción (media+covarianza)\n"
        "comparada por KL simétrica — el modelo Mandel-Ellis, como la antigua\n"
        "app Java. La clasificación más limpia de parecidos; las coincidencias reales dan ≳ 80 %.\n"
        "Librosa: vector rápido de timbre+ritmo hecho a mano (coseno).\n"
        "MERT: un embedding musical neuronal preentrenado — a menudo más cercano\n"
        "al ‘suena parecido’ percibido. Necesita:  pip install torch transformers\n"
        "Chroma cover/remix: compara MELODÍA/armonía, no timbre — encuentra\n"
        "remixes y versiones de la misma canción aunque cambien sonido,\n"
        "tonalidad o tempo. Solo librosa; construye su índice una vez como los demás.\n"
        "Combinado (predeterminado): el puesto medio de un título en Gaussiano/KL,\n"
        "librosa y chroma — los que los tres sitúan arriba van primero.\n"
        "Combinado + MERT: lo mismo, con MERT como cuarta vista.",
    "Off: sound-alike tracks (audio timbre).\n"
    "On: tracks that keep appearing in the same old playlists as this one.":
        "Apagado: temas que suenan parecido (timbre del audio).\n"
        "Encendido: temas que aparecen una y otra vez en las mismas listas antiguas que este.",
    "Replace the duplicate with the selected track (Enter, or double-click a row)":
        "Reemplazar el duplicado por el tema seleccionado (Intro, o doble clic en una fila)",
    "Several copies of a song often exist under slightly different names\n"
    "(e.g. '… DJ Ice', 'jive(43) - Bim Bam', '16 Bim Bam'). When on, only the\n"
    "first copy of each song title is shown.":
        "A menudo hay varias copias de una canción con nombres algo distintos\n"
        "(p. ej. ‘… DJ Ice’, ‘jive(43) - Bim Bam’, ‘16 Bim Bam’). Si está activo,\n"
        "solo se muestra la primera copia de cada título.",
    "Show only tracks considered instrumental: an explicit 'instr' tag /\n"
    "'(Instr.)' filename marker, a Demucs-measured vocal share (🎙️ Analyze\n"
    "vocals), or the learned audio probability. Unknown tracks count as\n"
    "vocal, so they are hidden while this is on.":
        "Mostrar solo temas considerados instrumentales: una etiqueta ‘instr’ explícita /\n"
        "la marca ‘(Instr.)’ en el nombre del archivo, una proporción de voz medida con Demucs (🎙️ Analizar\n"
        "voces) o la probabilidad de audio aprendida. Los temas desconocidos cuentan como\n"
        "cantados, así que se ocultan mientras esto esté activo.",
    "Space: play / stop the selected track\n"
    "Ctrl + ← / → : seek 30 s back / forward":
        "Espacio: reproducir / detener el tema seleccionado\n"
        "Ctrl + ← / → : saltar 30 s atrás / adelante",
    "This track isn't in any of your old playlists yet — nothing to learn from. Switch the toggle off for sound-alike tracks.":
        "Este tema aún no está en ninguna de tus listas antiguas — no hay nada que aprender. Apaga el interruptor para ver temas que suenan parecido.",
    "🧹  Hide duplicate copies (same song, ignoring DJ / dance / BPM tags)":
        "🧹  Ocultar copias duplicadas (misma canción, sin tener en cuenta DJ / baile / BPM)",
    "Clear playlist": "Vaciar lista",
    "Clear wishlist": "Vaciar lista de deseos",
    "Find in list": "Buscar en la lista",
    "Find planned before": "Buscar planificaciones anteriores",
    "Find title:": "Buscar título:",
    "No similar tracks found (audio features may be missing).":
        "No se encontraron temas similares (puede que falten las características de audio).",
    "Select exactly two titles of the same dance to swap them.":
        "Selecciona exactamente dos títulos del mismo baile para intercambiarlos.",
    "Swap titles": "Intercambiar títulos",
    "Already planned": "Ya planificado",
    "Different dance": "Otro baile",
    "Move Error": "Error al mover",
    "Move track": "Mover tema",
    "Replace Error": "Error al reemplazar",
    "Different style": "Otra sección",
    "Load playlist": "Cargar lista",
    "Name (competition, day, tournament):":
        "Nombre (competición, día, torneo):",
    "New folder": "Nueva carpeta",
    "Remove": "Quitar",
    "Remove this song from its slot? The slot stays empty.":
        "¿Quitar esta canción de su hueco? El hueco queda vacío.",
    "Remove %d songs from their slots? The slots stay empty.":
        "¿Quitar %d canciones de sus huecos? Los huecos quedan vacíos.",
    "Remove this song from the running order?":
        "¿Quitar esta canción del orden de reproducción?",
    "Remove %d songs from the running order?":
        "¿Quitar %d canciones del orden de reproducción?",
    "Rename": "Renombrar",
    "Songs and total play time of the selected playlist\n"
    "(tracks this library doesn't know count, but add no time)":
        "Canciones y duración total de la lista seleccionada\n"
        "(los temas que esta biblioteca no conoce cuentan, pero no suman tiempo)",
    "The playlists filed in the selected folder, one slot each.\n"
    "Drag a slot onto a deck to load that round · double-click it to\n"
    "load it onto the focused deck · right-click to rename, remove or\n"
    "read its tracks.":
        "Las listas archivadas en la carpeta seleccionada, una por hueco.\n"
        "Arrastra un hueco a un deck para cargar esa ronda · doble clic para\n"
        "cargarla en el deck activo · clic derecho para renombrar, quitar o\n"
        "leer sus temas.",
    "The tracks of the selected playlist, in playing order.\n"
    "▶ or Space previews · drag them onto a deck or the player list ·\n"
    "double-click to open in your external player.":
        "Los temas de la lista seleccionada, en orden de reproducción.\n"
        "▶ o Espacio para escuchar · arrástralos a un deck o a la lista del reproductor ·\n"
        "doble clic para abrir en tu reproductor externo.",
    "Your competitions, days and tournaments — folders are labels,\n"
    "the 🎵 entries point at .m3u files wherever they lie.\n"
    "\n"
    "Drop .m3u files or a whole folder in from Explorer · pick a folder\n"
    "to lay its playlists out as slots on the right · drag a slot onto\n"
    "a deck to load the round · double-click it to load it onto the\n"
    "focused deck.":
        "Tus competiciones, días y torneos — las carpetas son etiquetas,\n"
        "las entradas 🎵 apuntan a archivos .m3u estén donde estén.\n"
        "\n"
        "Suelta archivos .m3u o una carpeta entera desde el Explorador · elige una carpeta\n"
        "para mostrar sus listas como huecos a la derecha · arrastra un hueco a\n"
        "un deck para cargar la ronda · doble clic para cargarla en el\n"
        "deck activo.",
    "📂  (not in a folder)": "📂  (sin carpeta)",
    "Party play time, songs at full length with no pause.\n"
    "The count simulates the party generator with your library's\n"
    "track lengths per dance (3.5 min where none are known).":
        "Duración de la fiesta, canciones completas sin pausa.\n"
        "El cálculo simula el generador de fiestas con las duraciones de los\n"
        "temas de tu biblioteca por baile (3,5 min donde no se conoce ninguna).",
    "Per dance: songs to have ready — enough for 9 of 10 generated lists.":
        "Por baile: canciones que conviene tener listas — suficientes para 9 de cada 10 listas generadas.",
    "A key given to a pad follows it wherever it is moved and works\n"
    "from any page. Empty = that pad answers to its slot's key.":
        "Una tecla asignada a un pad lo sigue allá donde se mueva y funciona\n"
        "desde cualquier página. Vacía = ese pad responde a la tecla de su hueco.",
    "Export cartwall": "Exportar cartwall",
    "How long a pad takes to let go when it is tapped again\n"
    "or ⏹ stops the wall. A pad can override this in its own settings.":
        "Cuánto tarda un pad en apagarse cuando se vuelve a pulsar\n"
        "o ⏹ detiene la pared. Un pad puede cambiarlo en sus propios ajustes.",
    "Import cartwall": "Importar cartwall",
    "Pads per page. Making the grid smaller never loses a pad —\n"
    "whatever no longer fits moves to the first free slot.":
        "Pads por página. Reducir la cuadrícula nunca pierde un pad —\n"
        "lo que ya no cabe pasa al primer hueco libre.",
    "Page name:": "Nombre de la página:",
    "Play this pad over and over until it is stopped —\n"
    "for a background bed under a ceremony.":
        "Reproducir este pad una y otra vez hasta que se detenga —\n"
        "para un fondo musical bajo una ceremonia.",
    "Remove page": "Quitar página",
    "Rename page": "Renombrar página",
    "Snap the wall back into the main window.\n"
    "It returns to the edge it was last docked at.":
        "Volver a encajar la pared en la ventana principal.\n"
        "Vuelve al borde donde estuvo acoplada por última vez.",
    "That file is not a cartwall this version can read.":
        "Ese archivo no es una cartwall que esta versión pueda leer.",
    "The key fires whichever pad sits in that slot on the page you are\n"
    "looking at, so the same finger hits the same corner on every page.":
        "La tecla dispara el pad que esté en ese hueco de la página que estás\n"
        "mirando, así el mismo dedo da en la misma esquina en todas las páginas.",
    "No pause started — enable auto-advance and have a next song queued.":
        "No se inició ninguna pausa — activa el avance automático y ten una siguiente canción en cola.",
    "⏹ The playing title is no longer in its deck — the music was stopped.":
        "⏹ El título en reproducción ya no está en su deck — la música se detuvo.",
    "✏️ Title ended — still loaded for editing; scrub back and ⏯ to listen.":
        "✏️ Título terminado — sigue cargado para editar; retrocede y ⏯ para escuchar.",
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
        "Un Paso Doble bajo este interruptor nunca se funde y no hace caso\n"
        "de la duración de reproducción — se baila hasta sus momentos culminantes coreografiados.\n"
        "los momentos culminantes (crescendo → caída dramática) se detectan solos\n"
        "en segundo plano y la música se corta en seco cuando llega\n"
        "el elegido (su gong final). Un momento culminante que la detección\n"
        "no logra fijar recurre al fraseo estándar\n"
        "(1.º ≈ 0:45, 2.º ≈ 1:15).\n"
        "\n"
        "Apagado, un Paso Doble es un título normal: la duración de reproducción lo corta\n"
        "y el fundido lo saca, como cualquier otro baile.",
    "Append the heat number (\"…, Heat 3\") — the couples hear which\n"
    "heat they are about to dance.\n"
    "\n"
    "Only a round grid has heats: a theme list, the warm-up and a free\n"
    "running order are announced without one. Recorded for heats 1-8;\n"
    "beyond that the number is left out.":
        "Añadir el número de grupo («…, Gruppe 3») — las parejas oyen en qué\n"
        "grupo van a bailar.\n"
        "\n"
        "Solo una cuadrícula de rondas tiene grupos: una lista temática, el calentamiento y un\n"
        "orden libre se anuncian sin él. Grabado para los grupos 1-8;\n"
        "más allá se omite el número.",
    "Choose one or more titles — or an .m3u playlist — that play\n"
    "softly during the pause between songs, faded in at the start\n"
    "and out before the next song. Several titles rotate: a title\n"
    "keeps playing pause after pause until it ends, then the next\n"
    "one takes over.":
        "Elige uno o más títulos — o una lista .m3u — que suenen\n"
        "suaves durante la pausa entre canciones, con fundido de entrada al inicio\n"
        "y de salida antes de la siguiente canción. Varios títulos se turnan: un título\n"
        "sigue sonando pausa tras pausa hasta que termina, luego el siguiente\n"
        "toma el relevo.",
    "Compensate loudness differences between tracks on playback:\n"
    "each song's measured EBU R128 loudness is pulled towards a common\n"
    "target, so quiet old recordings and loud modern masters play at\n"
    "a similar level. Needs 📊 Analyze loudness (⚙ Settings) first.":
        "Compensar las diferencias de sonoridad entre temas al reproducir:\n"
        "la sonoridad EBU R128 medida de cada canción se lleva hacia un objetivo\n"
        "común, así las grabaciones antiguas flojas y los masters modernos fuertes suenan a\n"
        "un nivel parecido. Necesita antes 📊 Analizar sonoridad (⚙ Ajustes).",
    "Forget the current track's learned highlights\n"
    "(falls back to 🐂 auto-detection on the next play).":
        "Olvidar los momentos culminantes aprendidos del tema actual\n"
        "(vuelve a la 🐂 detección automática en la siguiente reproducción).",
    "Hold a Paso Doble back this long before the music starts, so the\n"
    "couples reach their position after the dance is called. Applies\n"
    "to every way a PD is started — ▶, a double-click, auto-advance.\n"
    "0 s = start at once, like every other dance.\n"
    "\n"
    "With 🔈 Announce next dance on, the app makes the call and the\n"
    "seconds run from it; off, the hall's announcer does and the wait\n"
    "runs silently — counted down on this panel either way.":
        "Retener un Paso Doble este tiempo antes de que empiece la música, para que\n"
        "las parejas lleguen a su posición después de anunciarse el baile. Vale\n"
        "para cualquier forma de iniciar un PD — ▶, un doble clic, el avance automático.\n"
        "0 s = empezar enseguida, como cualquier otro baile.\n"
        "\n"
        "Con 🔈 Anunciar el siguiente baile activo, la app hace el anuncio y los\n"
        "segundos cuentan desde él; si no, lo hace el locutor de la sala y la espera\n"
        "transcurre en silencio — con cuenta atrás en este panel en ambos casos.",
    "How loud the pause music plays, relative to the normal\n"
    "playback volume — kept lower so it stays in the background.":
        "Lo fuerte que suena la música de pausa, respecto al volumen\n"
        "normal de reproducción — más baja para que quede de fondo.",
    "Keep the screensaver and the display timeout off while music is\n"
    "playing or the presenter screen is open.\n"
    "\n"
    "The system counts idle time from the mouse and the keyboard,\n"
    "never from the speakers — so an hour of music with nobody touching\n"
    "the desk blanks the screen mid-heat, the beamer included. It goes\n"
    "back to its normal timeouts as soon as neither is running.":
        "Mantener apagados el salvapantallas y el apagado de pantalla mientras suena\n"
        "música o está abierta la pantalla del presentador.\n"
        "\n"
        "El sistema cuenta el tiempo de inactividad del ratón y el teclado,\n"
        "nunca de los altavoces — así que una hora de música sin que nadie toque\n"
        "la mesa apaga la pantalla en mitad de un grupo, proyector incluido. Vuelve\n"
        "a sus tiempos normales en cuanto ninguno de los dos está activo.",
    "Off: the next song starts the moment the current one ends, with\n"
    "no filler music and no announcement. The configured time is kept\n"
    "for switching back.\n"
    "\n"
    "Needs ⏭ auto-advance — without it the next song waits for the\n"
    "operator anyway, so there is no gap to fill.":
        "Apagado: la siguiente canción empieza en el momento en que termina la actual, sin\n"
        "música de relleno ni anuncio. El tiempo configurado se conserva\n"
        "para cuando vuelvas a activarlo.\n"
        "\n"
        "Necesita ⏭ avance automático — sin él la siguiente canción espera\n"
        "de todos modos al operador, así que no hay hueco que llenar.",
    "On: a double-click in a deck puts the title on the speakers at\n"
    "once — what a party wants.\n"
    "Off: it is only CUED on the player (loaded, shown, silent) and ⏯\n"
    "starts it — what a heat wants, where the music begins when the\n"
    "couples are on the floor and not a moment earlier.\n"
    "\n"
    "Part of the play sets: 🏆 tournament switches it off, 🎉 party on.":
        "Encendido: un doble clic en un deck pone el título en los altavoces\n"
        "al instante — lo que pide una fiesta.\n"
        "Apagado: solo se PREPARA en el reproductor (cargado, visible, en silencio) y ⏯\n"
        "lo inicia — lo que pide un grupo, donde la música empieza cuando las\n"
        "parejas están en la pista y ni un momento antes.\n"
        "\n"
        "Parte de los conjuntos de reproducción: 🏆 torneo lo apaga, 🎉 fiesta lo enciende.",
    "On: a double-click in a deck plays the title at once.\n"
    "Off: it is only cued on the player (loaded, shown,\n"
    "silent) and ⏯ starts it — the heat begins when the\n"
    "couples stand.":
        "Encendido: un doble clic en un deck reproduce el título al instante.\n"
        "Apagado: solo se prepara en el reproductor (cargado, visible,\n"
        "en silencio) y ⏯ lo inicia — el grupo empieza cuando las\n"
        "parejas están en su sitio.",
    "Pitch every title to the mean tempo of its dance in the\n"
    "current round, kept inside the TSO range — what a heat is\n"
    "danced to. Wrong for a party, where the next song is a\n"
    "different dance at whatever tempo it was recorded at.":
        "Ajustar cada título al tempo medio de su baile en la\n"
        "ronda actual, dentro del rango TSO — así se baila\n"
        "un grupo. Incorrecto para una fiesta, donde la siguiente canción es otro\n"
        "baile al tempo en que se grabó.",
    "Open a second, full-screen window showing only the running title\n"
    "with its dance and the next three songs — big and plain, for a\n"
    "beamer or a monitor turned towards the floor. Pick the screen\n"
    "next to it; Esc (or this button) closes it again.":
        "Abrir una segunda ventana a pantalla completa que muestra solo el título en curso\n"
        "con su baile y las tres canciones siguientes — grande y sencillo, para un\n"
        "proyector o un monitor girado hacia la pista. Elige la pantalla\n"
        "al lado; Esc (o este botón) la vuelve a cerrar.",
    "Pause the music and suspend the highlight stop, so the whole Paso\n"
    "Doble is reachable while you set its marks: scrub to a crash, ⏯ to\n"
    "listen, hit 🎯, delete a wrong mark with its ✕. Marking within 3 s\n"
    "of an existing mark moves that one instead of adding a fourth.\n"
    "\n"
    "Leaving edit mode arms the stop again and PAUSES at it the next\n"
    "time it's reached, so you can hear whether the mark sits right.":
        "Pausar la música y suspender la parada en el momento culminante, para que todo el Paso\n"
        "Doble sea accesible mientras pones sus marcas: busca un golpe, ⏯ para\n"
        "escuchar, pulsa 🎯, borra una marca errónea con su ✕. Marcar a menos de 3 s\n"
        "de una marca existente mueve esa en vez de añadir una cuarta.\n"
        "\n"
        "Salir del modo de edición vuelve a armar la parada y se DETIENE en ella la siguiente\n"
        "vez que se alcanza, para que puedas oír si la marca está bien puesta.",
    "Put the panel back on the competition values in one go: the\n"
    "configured play length, no pause between songs, no auto-advance\n"
    "and no spoken announcement — the settings a heat is run with.\n"
    "\n"
    "Lit gold while the panel stands on those values, the way 🎉 is lit\n"
    "purple during a party. Switches the 🎉 party set off. What exactly\n"
    "it sets is yours to change: ⚙ Settings → 🎛 Play sets.\n"
    "\n"
    "Clicked while lit, it switches itself off: the list goes back to\n"
    "the values it had before the set was pressed.":
        "Devolver el panel a los valores de competición de una vez: la\n"
        "duración de reproducción configurada, sin pausa entre canciones, sin avance automático\n"
        "y sin anuncio hablado — los ajustes con los que se lleva un grupo.\n"
        "\n"
        "Se ilumina en dorado mientras el panel está en esos valores, igual que 🎉 se ilumina\n"
        "en morado durante una fiesta. Desactiva el conjunto 🎉 fiesta. Lo que pone\n"
        "exactamente lo decides tú: ⚙ Ajustes → 🎛 Conjuntos de reproducción.\n"
        "\n"
        "Si está encendido, un clic lo apaga: la lista vuelve a los\n"
        "valores que tenía antes de pulsar el conjunto.",
    "Say the next dance out loud shortly before the pause ends\n"
    "(\"Nächster Tanz: Langsamer Walzer\"). Without a pause the dance\n"
    "is named as the title starts instead (\"Langsamer Walzer\") —\n"
    "over the first bars or before them, as ⚙ Settings → 🔊 Sound &\n"
    "player has it.":
        "Decir en voz alta el siguiente baile poco antes de que acabe la pausa\n"
        "(«Nächster Tanz: Langsamer Walzer»). Sin pausa, el baile\n"
        "se nombra al empezar el título («Langsamer Walzer») —\n"
        "sobre los primeros compases o antes de ellos, según esté en\n"
        "⚙ Ajustes → 🔊 Sonido & reproductor.",
    "The dance is named while the music is already running, ducked\n"
    "under the voice — the hall hears both at once and the title\n"
    "loses none of its first bars.\n"
    "\n"
    "Applies where a title names its dance as it starts: 🔈 Announce\n"
    "next dance on, and no pause between songs (a pause has a gap of\n"
    "its own for the call).":
        "El baile se nombra cuando la música ya está sonando, bajada\n"
        "bajo la voz — la sala oye ambos a la vez y el título\n"
        "no pierde ninguno de sus primeros compases.\n"
        "\n"
        "Se aplica cuando un título nombra su baile al empezar: 🔈 Anunciar el\n"
        "siguiente baile activo, y sin pausa entre canciones (una pausa tiene un hueco\n"
        "propio para el anuncio).",
    "The dance is called into silence and the music follows when the\n"
    "voice is done — the hall hears WHICH dance before it starts, at\n"
    "the cost of a second or two of quiet.\n"
    "\n"
    "Applies where a title names its dance as it starts: 🔈 Announce\n"
    "next dance on, and no pause between songs (a pause has a gap of\n"
    "its own for the call).":
        "El baile se anuncia en silencio y la música sigue cuando la\n"
        "voz termina — la sala oye QUÉ baile viene antes de que empiece, a\n"
        "costa de un segundo o dos de silencio.\n"
        "\n"
        "Se aplica cuando un título nombra su baile al empezar: 🔈 Anunciar el\n"
        "siguiente baile activo, y sin pausa entre canciones (una pausa tiene un hueco\n"
        "propio para el anuncio).",
    "Show a cover picture next to the title on the player.\n"
    "The playlist's own image is used when it has one (an #EXTIMG line\n"
    "in the .m3u or a cover file beside it), otherwise the track's\n"
    "embedded artwork, otherwise a plain ♪ tile.":
        "Mostrar una imagen de portada junto al título en el reproductor.\n"
        "Se usa la imagen propia de la lista cuando la tiene (una línea #EXTIMG\n"
        "en el .m3u o un archivo de portada al lado), si no la carátula\n"
        "incrustada del tema, si no un simple mosaico ♪.",
    "Speak a sample announcement now — check voice and level\n"
    "before the round, not during it.":
        "Pronunciar ahora un anuncio de ejemplo — comprueba voz y nivel\n"
        "antes de la ronda, no durante ella.",
    "Switch the tournament settings over to party playing in one go:\n"
    "every title to its full length, auto-advance to the next one, no\n"
    "pause (so no break music) in between and no spoken announcement.\n"
    "\n"
    "Applied by itself as soon as you play from the 🤸 Practice /\n"
    "party list, and switched back when a tournament deck takes over —\n"
    "a toast says what changed either way. What exactly it sets is\n"
    "yours to change: ⚙ Settings → 🎛 Play sets.\n"
    "\n"
    "Clicked while lit, it switches itself off: the list goes back to\n"
    "the values it had before the set was pressed.":
        "Cambiar los ajustes de torneo a modo fiesta de una vez:\n"
        "cada título a su duración completa, avance automático al siguiente, sin\n"
        "pausa (y por tanto sin música de pausa) entre medias y sin anuncio hablado.\n"
        "\n"
        "Se aplica solo en cuanto reproduces desde la lista 🤸 Práctica /\n"
        "fiesta, y se revierte cuando un deck de torneo toma el relevo —\n"
        "un aviso dice qué cambió en ambos casos. Lo que pone exactamente\n"
        "lo decides tú: ⚙ Ajustes → 🎛 Conjuntos de reproducción.\n"
        "\n"
        "Si está encendido, un clic lo apaga: la lista vuelve a los\n"
        "valores que tenía antes de pulsar el conjunto.",
    "The colours of the presenter screen. 'Default' is the black hall\n"
    "display; 'Light' is creme paper with warm brown type and rose\n"
    "gold for the next dance — made for a lit room, where black on a\n"
    "beamer is just a grey rectangle. Applies straight away.":
        "Los colores de la pantalla del presentador. ‘Default’ es la pantalla negra\n"
        "de sala; ‘Light’ es papel crema con letra marrón cálida y oro\n"
        "rosa para el siguiente baile — pensado para una sala iluminada, donde el negro en un\n"
        "proyector es solo un rectángulo gris. Se aplica al instante.",
    "The evening's running order — when dinner is, when the opening\n"
    "dance is — as a second page on the presenter screen.\n"
    "\n"
    "Type it here; on the screen itself, T (or its 🕒 button) switches\n"
    "to it, and it can fade between the two pages by itself.":
        "El programa de la velada — cuándo es la cena, cuándo el baile\n"
        "de apertura — como segunda página en la pantalla del presentador.\n"
        "\n"
        "Escríbelo aquí; en la propia pantalla, T (o su botón 🕒) cambia\n"
        "a él, y puede alternar solo entre las dos páginas con un fundido.",
    "There is one player for every deck, so leaving a title to hear\n"
    "another one loses your place in it. On: the spot a title stopped\n"
    "at is kept and it starts there again — marked by a tick on the\n"
    "seek bar and by ↩ mm:ss on its row.\n"
    "\n"
    "A title played to its end keeps no mark, and the marks are\n"
    "forgotten when the app closes.":
        "Hay un reproductor para cada deck, así que dejar un título para oír\n"
        "otro hace perder tu sitio en él. Encendido: el punto donde se detuvo un título\n"
        "se conserva y vuelve a empezar ahí — marcado con una raya en la\n"
        "barra de búsqueda y con ↩ mm:ss en su fila.\n"
        "\n"
        "Un título tocado hasta el final no guarda marca, y las marcas se\n"
        "olvidan al cerrar la app.",
    "Time for the couples to change / catch breath before the next song":
        "Tiempo para que las parejas cambien / tomen aire antes de la siguiente canción",
    "Volume ramps to 0 over the last N seconds,\n"
    "in steps of half a second":
        "El volumen baja a 0 durante los últimos N segundos,\n"
        "en pasos de medio segundo",
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
        "Cuando termina una canción (fundido o final natural), pausar el\n"
        "tiempo configurado y luego reproducir la siguiente fila de canción del deck —\n"
        "así una ronda entera corre sin tocar nada. Se detiene al final\n"
        "de la ronda (🏁) — la siguiente ronda se inicia a mano.\n"
        "\n"
        "Apagarlo detiene también 🔈 Anunciar el siguiente baile: nada\n"
        "debería anunciar un baile que luego nada reproduce. Volver a\n"
        "encenderlo restaura el anuncio que tenías.\n"
        "\n"
        "Cada lista guarda su propia respuesta: esta es la de la\n"
        "lista en la que hiciste clic por última vez, la misma que ⏭/✋ bajo ese deck.",
    "Auto: a finished song is followed by the next row of the deck, so\n"
    "a whole round runs hands-free.\n"
    "Manual: every song is started by the operator, and 🔈 Announce\n"
    "next dance stops with it — back on Auto it returns.\n"
    "\n"
    "This playlist's own answer, remembered for it: the party list can\n"
    "run hands-free while the round next to it is started by hand.\n"
    "⏭ Auto-advance on the play panel is the same answer while this\n"
    "list is the one last clicked.":
        "Auto: a una canción terminada le sigue la siguiente fila del deck, así\n"
        "una ronda entera corre sin tocar nada.\n"
        "Manual: el operador inicia cada canción, y 🔈 Anunciar el\n"
        "siguiente baile se detiene con ello — al volver a Auto regresa.\n"
        "\n"
        "La respuesta propia de esta lista, recordada para ella: la lista de fiesta puede\n"
        "correr sola mientras la ronda de al lado se inicia a mano.\n"
        "⏭ Avance automático en el panel de reproducción es la misma respuesta mientras esta\n"
        "lista sea la última en la que hiciste clic.",
    "Manual: every song is started by the operator, and 🔈 Announce\n"
    "next dance is off with it.\n"
    "Auto: a finished song is followed by the next row of the deck, so\n"
    "a whole round runs hands-free — and the announcement returns.\n"
    "\n"
    "This playlist's own answer, remembered for it: the party list can\n"
    "run hands-free while the round next to it is started by hand.\n"
    "⏭ Auto-advance on the play panel is the same answer while this\n"
    "list is the one last clicked.":
        "Manual: el operador inicia cada canción, y 🔈 Anunciar el\n"
        "siguiente baile se apaga con ello.\n"
        "Auto: a una canción terminada le sigue la siguiente fila del deck, así\n"
        "una ronda entera corre sin tocar nada — y el anuncio vuelve.\n"
        "\n"
        "La respuesta propia de esta lista, recordada para ella: la lista de fiesta puede\n"
        "correr sola mientras la ronda de al lado se inicia a mano.\n"
        "⏭ Avance automático en el panel de reproducción es la misma respuesta mientras esta\n"
        "lista sea la última en la que hiciste clic.",
    "When the LAST title of the list has finished, carry on with its\n"
    "first one instead of stopping — so a party keeps its music going\n"
    "without anybody at the desk.\n"
    "\n"
    "The 🏁 end of a round is untouched: that one happens between\n"
    "rounds, and still waits for the operator.\n"
    "\n"
    "Needs ⏭ auto-advance.":
        "Cuando el ÚLTIMO título de la lista ha terminado, seguir con el\n"
        "primero en vez de detenerse — así una fiesta mantiene la música\n"
        "sin nadie en la mesa.\n"
        "\n"
        "El final de ronda 🏁 no se toca: ese ocurre entre\n"
        "rondas y sigue esperando al operador.\n"
        "\n"
        "Necesita ⏭ avance automático.",
    "Which highlight ends the Paso Doble — usually the 2nd,\n"
    "in rare cases the 3rd.":
        "Qué momento culminante termina el Paso Doble — normalmente el 2.º,\n"
        "en raros casos el 3.º.",
    "Which monitor the presenter screen fills. Same screen as the app\n"
    "is fine too — double-click the presenter window to shrink it back\n"
    "out of full screen.":
        "Qué monitor ocupa la pantalla del presentador. La misma pantalla que la app\n"
        "también sirve — doble clic en la ventana del presentador para sacarla\n"
        "de la pantalla completa.",
    "Which recorded voice announces the dance. “Mixed” alternates them\n"
    "— she, he, she, he — so an evening doesn't run on a single voice.\n"
    "\n"
    "A dance that was never recorded is not announced.":
        "Qué voz grabada anuncia el baile. «Mezclada» las alterna\n"
        "— ella, él, ella, él — para que una velada no vaya con una sola voz.\n"
        "\n"
        "Un baile que nunca se grabó no se anuncia.",
    "While a Paso Doble plays, click exactly when a highlight (the\n"
    "dramatic gong / drop) hits to teach its position. Click again at\n"
    "the 2nd / 3rd highlight. Manually learned highlights are flagged\n"
    "in the database and are never overwritten by 🐂 auto-detection.":
        "Mientras suena un Paso Doble, haz clic justo cuando llega un momento culminante (el\n"
        "gong / caída dramática) para enseñar su posición. Vuelve a hacer clic en\n"
        "el 2.º / 3.º momento culminante. Los momentos culminantes aprendidos a mano se marcan\n"
        "en la base de datos y la 🐂 detección automática nunca los sobrescribe.",
    "Adjusted play length (timed play / Paso Doble highlight stop)\n"
    "next to the track's full length":
        "Duración de reproducción ajustada (reproducción temporizada / parada en el momento culminante del Paso Doble)\n"
        "junto a la duración completa del tema",
    "Auto-equalize the heat tempo (toggle):\n"
    "while on, every title is pitched to the average tempo of its\n"
    "dance in this round, kept inside the TSO range (e.g. a Rumba\n"
    "at 23 → T24, a Paso Doble at 57 → T58).":
        "Igualar automáticamente el tempo del grupo (interruptor):\n"
        "mientras esté activo, cada título se ajusta al tempo medio de su\n"
        "baile en esta ronda, dentro del rango TSO (p. ej. una Rumba\n"
        "a 23 → T24, un Paso Doble a 57 → T58).",
    "Disable preview player  (re-enable in Settings)":
        "Desactivar el reproductor de escucha previa  (se reactiva en Ajustes)",
    "Duck to 20 % / back to full — the filler music comes down too":
        "Bajar al 20 % / volver al máximo — la música de relleno también baja",
    "Endless repeat of THIS title (toggle):\n"
    "while on, the running title starts again every time it ends —\n"
    "for the moment the floor is still full or the speech runs long.\n"
    "\n"
    "It holds the evening on one title, so it beats the 🏁 end of a\n"
    "round and works with ⏭ auto-advance off too. Switch it off and\n"
    "the list carries on where it stands.":
        "Repetición infinita de ESTE tema (interruptor):\n"
        "mientras esté activo, el tema en curso vuelve a empezar cada vez que termina —\n"
        "para cuando la pista sigue llena o el discurso se alarga.\n"
        "\n"
        "Mantiene la velada en un solo tema, así que se impone al 🏁 final de\n"
        "una ronda y funciona también con ⏭ avance automático desactivado. Desactívalo y\n"
        "la lista sigue donde está.",
    "Extend the auto-advance pause (add another pause length) —\n"
    "use it when the heat change is taking longer than planned.":
        "Alargar la pausa del avance automático (añadir otra duración de pausa) —\n"
        "úsalo cuando el cambio de grupo tarde más de lo previsto.",
    "Fade the music out and HOLD it there (over the fade time).\n"
    "Nothing ends and nothing advances — ⏯ resumes at exactly the\n"
    "spot it went quiet. For an announcement or an incident on the floor.":
        "Bajar la música con un fundido y MANTENERLA ahí (durante el tiempo de fundido).\n"
        "Nada termina y nada avanza — ⏯ continúa exactamente en el\n"
        "punto donde se quedó en silencio. Para un aviso o un incidente en la pista.",
    "Fade this song out now (over the configured fade time), then end it\n"
    "— for a quick, clean finish on the floor.":
        "Hacer un fundido de salida de este tema ahora (durante el tiempo de fundido configurado) y terminarlo\n"
        "— para un final rápido y limpio en la pista.",
    "Jump straight to the pause music — end this song now and start\n"
    "the between-songs pause (e.g. the dancers are already leaving).":
        "Saltar directamente a la música de pausa — terminar este tema ahora e iniciar\n"
        "la pausa entre temas (p. ej. los bailarines ya están saliendo).",
    "Tap along to the beat to measure this track's live tempo by hand,\n"
    "against a target for its dance (Sollwert) — display only, does not\n"
    "touch the fader.":
        "Marca el ritmo con clics para medir a mano el tempo real de este tema,\n"
        "frente a un valor objetivo para su baile (Sollwert) — solo se muestra, no\n"
        "toca el fader.",
    "Tempo −16 % … +16 % without changing the pitch (time stretch) —\n"
    "e.g. to pull a track onto the takt the tournament needs.\n"
    "Stays set across tracks; a double-click on the fader (or the\n"
    "button below) resets it.":
        "Tempo −16 % … +16 %, sin cambiar el tono (time stretch) —\n"
        "p. ej. para llevar un tema al compás que necesita el torneo.\n"
        "Se mantiene entre temas; un doble clic en el fader (o el\n"
        "botón de abajo) lo restablece.",
    "📌 Pin the tempo: the fader stays where you left it when the next\n"
    "title starts.\n"
    "Off: every new title begins at ±0 %.\n"
    "Switching TSO on takes the pin off — TSO pitches each title itself.":
        "📌 Fijar el tempo: el fader se queda donde lo dejaste cuando empieza\n"
        "el siguiente tema.\n"
        "Desactivado: cada tema nuevo empieza en ±0 %.\n"
        "Activar TSO quita la fijación — TSO ajusta cada tema por sí mismo.",
    "Off, the running order goes by this machine's clock.\n"
    "\n"
    "On, it goes by the time you set here — from the moment you save,\n"
    "and running on from there. An evening half an hour behind stays\n"
    "half an hour behind; the screen does not stand still.\n"
    "\n"
    "This is not saved with the programme: the next start of the app\n"
    "is back on the machine's clock.":
        "Desactivado, el programa sigue el reloj de este equipo.\n"
        "\n"
        "Activado, sigue la hora que pongas aquí — desde el momento en que guardas,\n"
        "y avanzando a partir de ahí. Una velada con media hora de retraso sigue\n"
        "con media hora de retraso; la pantalla no se detiene.\n"
        "\n"
        "Esto no se guarda con el programa: el próximo inicio de la app\n"
        "vuelve al reloj del equipo.",
    "Off, the screen stays on whichever page you picked (T on the\n"
    "presenter screen, or its 🕒 button, switches by hand).\n"
    "\n"
    "On, it fades from one to the other by itself — so the hall sees\n"
    "both without anybody at the desk touching anything.":
        "Desactivado, la pantalla se queda en la página que elegiste (T en la\n"
        "pantalla del presentador, o su botón 🕒, cambia a mano).\n"
        "\n"
        "Activado, pasa de una a otra con un fundido por sí sola — así la sala ve\n"
        "ambas sin que nadie en la mesa toque nada.",
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
        "Lo que muestra la pantalla del presentador en su segunda página — el\n"
        "programa de la velada. La línea a la que ha llegado el reloj se resalta,\n"
        "las anteriores se muestran en gris.\n"
        "\n"
        "Una hora puede ser cualquier cosa que escribirías en un programa; solo las horas\n"
        "reales (20:30, 20.30) participan en el resaltado.\n"
        "\n"
        "«Hasta» es opcional y es lo que permite que un punto contenga a otro: pon\n"
        "a la fiesta 19:00–01:00 y al baile de apertura 19:30–19:50, y cuando\n"
        "termine el baile el resaltado vuelve a la fiesta. Una hora de\n"
        "fin (01:00) o una duración en minutos (20).",
    "Dance": "Baile",
    "Title": "Título",
    "📋  Path copied to clipboard": "📋  Ruta copiada al portapapeles",
    "Artist": "Artista",
    "🏷 MP3 tag": "🏷 Etiqueta MP3",
    "🔬 Measured": "🔬 Medido",
    "🔀  Shared between playlists": "🔀  Compartido entre listas",
    "Action": "Acción",
    "Nothing usable — the decks were left alone.":
        "Nada aprovechable — los decks no se tocaron.",
    "Issue(s)": "Problema(s)",
    "Remove song": "Quitar tema",
    "Remove dance": "Quitar baile",
    " tracks": " temas",
    "In your own words — what this list is for (optional):":
        "Con tus propias palabras — para qué es esta lista (opcional):",
    "Rules the model has to follow:": "Reglas que el modelo debe seguir:",
    "Claude login:": "Inicio de sesión de Claude:",
    "📝  Details copied to clipboard": "📝  Detalles copiados al portapapeles",
    "Mode:": "Modo:",
    "Favorites": "Favoritos",
    "Theme": "Temática",
    "Past Competitions": "Competiciones anteriores",
    "Draw tracks from:": "Tomar temas de:",
    "Dance Style:": "Estilo de baile:",
    "Age Class:": "Categoría de edad:",
    "Start Class:": "Clase de inicio:",
    "Dances:": "Bailes:",
    "Rounds  (e.g. 6-3-2-1):": "Rondas  (p. ej. 6-3-2-1):",
    "Paste competition schedule:": "Pegar el horario de la competición:",
    "Competition:": "Competición:",
    "Seeds the grid from songs you played at this\n"
    "class before (matching per-class M3U files).":
        "Llena la cuadrícula con temas que ya pusiste en esta\n"
        "clase (archivos M3U por clase que coincidan).",
    "Theme:": "Temática:",
    "Number of tracks:": "Número de temas:",
    "Themes use ID3 year tags + themes.json overrides.\n"
    "Decade themes need year data in your MP3s.":
        "Las temáticas usan las etiquetas ID3 de año + ajustes de themes.json.\n"
        "Las temáticas por década necesitan el año en tus MP3.",
    "⏱  Too short — at or below:": "⏱  Demasiado corto — igual o inferior a:",
    "The cut must cover the 1:30–1:45 TSO play time; default 1:45.":
        "El corte debe cubrir el tiempo de reproducción TSO de 1:30–1:45; por defecto 1:45.",
    "⏳  Too long — above:": "⏳  Demasiado largo — más de:",
    "Only flagged when the ⏳ checkbox in the Music-check window is on (Practice playlists); default 4:00.":
        "Solo se marca si la casilla ⏳ de la ventana de revisión musical está activada (listas de práctica); por defecto 4:00.",
    "⚡  Tempo mismatch — deviation above:":
        "⚡  Tempo no coincide — desviación de más de:",
    "Measured tempo vs the filename label (detector ×2, ×3, ×1.5 … slips are excused first); default 10 %.":
        "Tempo medido frente a la etiqueta del nombre de archivo (antes se perdonan los deslices del detector ×2, ×3, ×1,5 …); por defecto 10 %.",
    "🔇  Hiss — noise floor above:": "🔇  Siseo — ruido de fondo por encima de:",
    "How quiet a track must get somewhere. A clean file reaches its lead-in silence, a tape rip never gets below its own hiss; default −50 dB. Only flagged when the 🔇 checkbox in the Music-check window is on.":
        "Lo silencioso que debe llegar a ser un tema en algún punto. Un archivo limpio alcanza su silencio inicial, una copia de cinta nunca baja de su propio siseo; por defecto −50 dB. Solo se marca si la casilla 🔇 de la ventana de revisión musical está activada.",
    "📄 File name": "📄 Nombre de archivo",
    "Source": "Origen",
    "Speed": "Velocidad",
    "— (no BPM tag)": "— (sin etiqueta BPM)",
    "— (not measured)": "— (sin medir)",
    "🔁  Doubled inside one playlist": "🔁  Duplicado dentro de una lista",
    "File": "Archivo",
    "📌  Reference base (single .m3u)": "📌  Base de referencia (un solo .m3u)",
    "🎯  Tournament files (compared against)":
        "🎯  Archivos del torneo (con los que se compara)",
    "🔁  Doubled inside a playlist": "🔁  Duplicado dentro de una lista",
    "Added": "Añadido",
    "Last": "Último",
    "Build all caches — librosa…": "Crear todas las cachés — librosa…",
    "Analyzing audio (timbre)…": "Analizando audio (timbre)…",
    "Audio analysis": "Análisis de audio",
    "Measuring loudness (EBU R128)…": "Midiendo la sonoridad (EBU R128)…",
    "Loudness analysis": "Análisis de sonoridad",
    "Probing silent stretches…": "Comprobando tramos en silencio…",
    "Silence probe": "Comprobación de silencios",
    "Separating vocals (Demucs)…": "Separando voces (Demucs)…",
    "Vocal separation": "Separación de voces",
    "Detecting Paso Doble highlights…":
        "Detectando los momentos culminantes del Paso Doble…",
    "PD highlight detection": "Detección de culminaciones del PD",
    "✅  No other open playlist to compare against":
        "✅  No hay otra lista abierta con la que comparar",
    "✅  Nothing here is in another open playlist":
        "✅  Nada de esto está en otra lista abierta",
    "Remove duplicates": "Quitar duplicados",
    "🌐  Whole repository — every file under your music repo (global search).\n"
    "🎯  Favorites library — just your tanzcds folder.\n"
    "➕  Both — the repository and the favorites library.":
        "🌐  Repositorio completo — todos los archivos de tu repositorio de música (búsqueda global).\n"
        "🎯  Biblioteca de favoritos — solo tu carpeta tanzcds.\n"
        "➕  Ambos — el repositorio y la biblioteca de favoritos.",
    "Standard dances": "Bailes estándar",
    "Latin dances": "Bailes latinos",
    "Interleave short social-dance rounds — needs those tracks in your library.":
        "Intercalar rondas cortas de bailes sociales — necesita esos temas en tu biblioteca.",
    "No Paso Doble": "Sin Paso Doble",
    "Start with a Latin round": "Empezar con una ronda latina",
    "Late Wiener Walzer (hold back early / not back-to-back)":
        "Vals vienés tarde (retenerlo al principio / no seguidos)",
    "Late Paso Doble (not in the first ~40 songs)":
        "Paso Doble tarde (no en los primeros ~40 temas)",
    "Failed — nothing was changed.": "Error — no se ha cambiado nada.",
    "♻️  Restoring your last session…": "♻️  Restaurando tu última sesión…",
    "Indexing whole repository…": "Indexando el repositorio completo…",
    "Build / refresh librosa audio index":
        "Crear / actualizar el índice de audio de librosa",
    "Scanning repository…": "Explorando el repositorio…",
    "Cleaning up database…": "Limpiando la base de datos…",
    "Re-learning playlist popularity…":
        "Volviendo a aprender la popularidad de las listas…",
    "Loading repository from cache…":
        "Cargando el repositorio desde la caché…",
    "🔊 Audio backend": "🔊 Motor de audio",
    "The audio backend is chosen when the app starts, so the new one takes over after a restart.\n"
    "\n"
    "Restart now?":
        "El motor de audio se elige al iniciar la app, así que el nuevo se aplica tras reiniciar.\n"
        "\n"
        "¿Reiniciar ahora?",
    "The theme, the accent colour and the language are applied while the app starts, so they take over after a restart.\n"
    "\n"
    "Restart now?":
        "El aspecto, el color de acento y el idioma se aplican al iniciar la app, así que se aplican tras reiniciar.\n"
        "\n"
        "¿Reiniciar ahora?",
    "📂  Nothing new — all tracks already in the wishlist":
        "📂  Nada nuevo — todos los temas ya están en la lista de deseos",
    "Length": "Duración",
    "Drag <b>.m3u playlists</b> (or audio files) here to check their tracks for the same issues — tempo label vs measured, TSO takt range, play length — plus the playlists' round structure (heat tempo spread).":
        "Arrastra aquí <b>listas .m3u</b> (o archivos de audio) para revisar sus temas con los mismos criterios — etiqueta de tempo frente a medición, rango de compás TSO, duración — además de la estructura de rondas de las listas (dispersión del tempo por grupo).",
    "Drag <b>.m3u playlists</b> here to check their track paths against the <b>search folders</b> (Settings). Broken references <b>and valid paths on a different root</b> (e.g. C:) that can be re-rooted there are listed per playlist; <b>🧭 Fix &amp; overwrite</b> rewrites those path lines <b>in place</b> — only the file path changes, every #EXTINF / comment line is kept exactly as-is.":
        "Arrastra aquí <b>listas .m3u</b> para comprobar las rutas de sus temas frente a las <b>carpetas de búsqueda</b> (Ajustes). Las referencias rotas <b>y las rutas válidas en otra unidad</b> (p. ej. C:) que pueden reubicarse allí se listan por lista; <b>🧭 Corregir &amp; sobrescribir</b> reescribe esas líneas de ruta <b>en el mismo archivo</b> — solo cambia la ruta, cada línea #EXTINF / de comentario se conserva tal cual.",
    "↶  Nothing to undo": "↶  Nada que deshacer",
    "↷  Nothing to redo": "↷  Nada que rehacer",
    "✅  No wishlist tracks are in an open playlist":
        "✅  Ningún tema de la lista de deseos está en una lista abierta",
    "Heat": "Grupo",
    "🔁  Cleared all replacement marks":
        "🔁  Se borraron todas las marcas de reemplazo",
    "✅  Kept all titles": "✅  Se mantuvieron todos los títulos",
    "✅  No duplicate titles in this list":
        "✅  No hay títulos duplicados en esta lista",
    "Already in the list — nothing added":
        "Ya está en la lista — no se añadió nada",
    "⭐  Already in the wishlist — nothing added":
        "⭐  Ya está en la lista de deseos — no se añadió nada",
    "Replace the existing track with this one?":
        "¿Reemplazar el tema existente por este?",
    "Remove heat": "Quitar grupo",
    "Remove round": "Quitar ronda",
    "Remove backup": "Quitar reserva",
    "Remove this backup song?": "¿Quitar este tema de reserva?",
    "⬆  Backup moved up into the empty slot":
        "⬆  La reserva subió al hueco libre",
    "Couldn't read the dropped track(s).":
        "No se pudieron leer los temas soltados.",
    "📊 Loudness probe failed": "📊 Falló la medición de sonoridad",
    "🔇 Silence probe failed": "🔇 Falló la comprobación de silencios",
    "Slot defaults — apply to every page":
        "Valores por defecto de las casillas — se aplican a todas las páginas",
    "Pad keys — travel with the pad": "Teclas de pad — viajan con el pad",
    "🔈  announcing…": "🔈  anunciando…",
    "🛑  held": "🛑  en espera",
    "🐂  detecting highlights…": "🐂  detectando culminaciones…",
    "🐂  plays to the end": "🐂  suena hasta el final",
    "🎯  stop reached — ⏯ to go on": "🎯  parada alcanzada — ⏯ para seguir",
    "🐂  Stop Paso Doble after highlight":
        "🐂  Parar el Paso Doble tras la culminación",
    "⏭  Auto-advance to next song": "⏭  Avance automático al siguiente tema",
    "over the first bars": "sobre los primeros compases",
    "before the music starts": "antes de que empiece la música",
    "⏸  No pause between songs": "⏸  Sin pausa entre temas",
    "🔁  Start again at the end": "🔁  Volver a empezar al final",
    "Pause between songs:": "Pausa entre temas:",
    "🔈  Announce next dance": "🔈  Anunciar el siguiente baile",
    "…with heat": "…con grupo",
    "🔊  Equalize volume (R128)": "🔊  Igualar volumen (R128)",
    "🖼  Show artwork — a cover next to the title on the player card":
        "🖼  Mostrar carátula — una portada junto al título en la tarjeta del reproductor",
    "〰  Show waveform — the title's waveform in place of the player card's seek bar":
        "〰  Mostrar forma de onda — la forma de onda del título en lugar de la barra de posición de la tarjeta del reproductor",
    "Draw the playing title's waveform in place of the seek bar: quiet\n"
    "passages, the skipped silence, the Paso Doble highlights and\n"
    "where the fade-out of a timed cut begins. Click it to jump.":
        "Dibujar la forma de onda del tema en curso en lugar de la barra de búsqueda: pasajes\n"
        "suaves, el silencio que se salta, las culminaciones del Paso Doble y\n"
        "dónde empieza el fundido de un corte por tiempo. Haz clic para saltar.",
    "The waveform of the title — what has played is blue, all of it\n"
    "red in the final seconds. The broad orange bar is where it plays.\n"
    "Shaded: silence the player skips · thin orange: Paso Doble\n"
    "highlights · red-tinted: the fade-out of a timed cut.\n"
    "Click to jump there.":
        "La forma de onda del tema — lo que ya ha sonado está en azul, todo\n"
        "en rojo en los últimos segundos. La barra naranja ancha marca dónde suena.\n"
        "Sombreado: silencio que el reproductor salta · naranja fino: culminaciones\n"
        "del Paso Doble · tono rojizo: el fundido de un corte por tiempo.\n"
        "Haz clic para saltar allí.",
    "▶️  Double-click starts the title": "▶️  El doble clic inicia el tema",
    "🎚  TSO pitch to the heat tempo": "🎚  TSO: ajustar al tempo del grupo",
    "↩  Remember where a title stopped": "↩  Recordar dónde se detuvo un tema",
    "☀  Keep the screen awake": "☀  Mantener la pantalla encendida",
    "Show the transport on this screen":
        "Mostrar los controles en esta pantalla",
    "Show the title played before this one": "Mostrar el tema anterior",
    "Show the timetable  ·  T\n"
    "Right-click to edit it":
        "Mostrar el horario  ·  T\n"
        "Clic derecho para editarlo",
    "Close the presenter screen": "Cerrar la pantalla del presentador",
    "Previous title": "Tema anterior",
    "Play / pause": "Reproducir / pausa",
    "Next title": "Tema siguiente",
    "Over to the break music": "Pasar a la música de pausa",
    "Time": "Hora",
    "Until": "Hasta",
    "What": "Qué",
    "Note": "Nota",
    "♪ Takt meter": "♪ Medidor de compás",
    "Takt count:": "Compases contados:",
    "Target:": "Objetivo:",
    " Takt/min": " compases/min",
    "Correction needed:": "Corrección necesaria:",
    "Apply": "Aplicar",
    "Apply this correction to the tempo fader.":
        "Aplicar esta corrección al fader de tempo.",
    "Next dances": "Próximos bailes",
    "⌨  Keyboard": "⌨  Teclado",
    "Space": "Espacio",
    "Play / stop the selected song":
        "Reproducir / detener el tema seleccionado",
    "Seek 30 s back / forward while playing":
        "Saltar 30 s atrás / adelante durante la reproducción",
    "Ctrl + R  or  Ctrl + N": "Ctrl + R  o  Ctrl + N",
    "Re-roll (regenerate) the selected song":
        "Volver a elegir (regenerar) el tema seleccionado",
    "Save the focused playlist / wishlist as M3U":
        "Guardar la lista / lista de deseos activa como M3U",
    "Ctrl + Shift + S": "Ctrl + Mayús + S",
    "Save the whole session state (decks, wishlists, layout)":
        "Guardar todo el estado de la sesión (decks, listas de deseos, disposición)",
    "Undo / redo (also Ctrl + Shift + Z)":
        "Deshacer / rehacer (también Ctrl + Mayús + Z)",
    "Ctrl + X  or  Ctrl + W": "Ctrl + X  o  Ctrl + W",
    "Close the active dialog or the preview mini player":
        "Cerrar el diálogo activo o el minirreproductor de escucha previa",
    "Del": "Supr",
    "Remove the selected rows (wishlist) / empty the selected heat slots (deck)":
        "Quitar las filas seleccionadas (lista de deseos) / vaciar los huecos de grupo seleccionados (deck)",
    "Del  with nothing selected": "Supr  sin nada seleccionado",
    "Clear that whole playlist / wishlist (confirmed) — same when every song is selected at once":
        "Vaciar toda esa lista / lista de deseos (con confirmación) — igual cuando todos los temas están seleccionados a la vez",
    "Clear the focused playlist / wishlist (confirmed), wherever the cursor is":
        "Vaciar la lista / lista de deseos activa (con confirmación), esté donde esté el cursor",
    "Ctrl + Shift + Del": "Ctrl + Mayús + Supr",
    "Ctrl + Del": "Ctrl + Supr",
    "Dynamic deck: remove the whole heat under the cursor (on a ↳ backup row: just that backup)":
        "Deck dinámico: quitar todo el grupo bajo el cursor (en una fila de reserva ↳: solo esa reserva)",
    "Dynamic deck or free running order: mark / unmark the selected song(s) for potential replace (❗ orange). Ctrl + 1 does the same, but only while the 🎛 cartwall is hidden — the wall claims that key for its first pad":
        "Deck dinámico u orden libre: marcar / desmarcar los temas seleccionados para un posible reemplazo (❗ naranja). Ctrl + 1 hace lo mismo, pero solo mientras la 🎛 cartwall está oculta — la cartwall reserva esa tecla para su primer pad",
    "F2  in the 📅 tournament tree": "F2  en el árbol 📅 de torneos",
    "Rename the entry under the cursor (Del removes it)":
        "Renombrar la entrada bajo el cursor (Supr la quita)",
    "Ctrl + A  in 🏆 Tournaments": "Ctrl + A  en 🏆 Torneos",
    "Mark every slot of the folder, or every entry of the tree — Del and a drag then take them all":
        "Marcar todas las casillas de la carpeta, o todas las entradas del árbol — Supr y arrastrar se las llevan todas",
    "Click a star in the ★ column": "Clic en una estrella de la columna ★",
    "Rate the title; click the star the rating ends on to clear it":
        "Valorar el tema; clic en la estrella donde termina la valoración para borrarla",
    "Find a title in the focused list (repeat to step to the next match)":
        "Buscar un título en la lista activa (repite para ir a la siguiente coincidencia)",
    "Esc  in the 🖥 presenter window": "Esc  en la ventana 🖥 del presentador",
    "This cheat sheet": "Esta chuleta",
    "Nothing found": "No se encontró nada",
    "🔍  Find a key or an action…": "🔍  Buscar una tecla o una acción…",
    "⚙  Settings…  (F12 / Ctrl+Alt+S)": "⚙  Ajustes…  (F12 / Ctrl+Alt+S)",
    "Open ⚙ Settings": "Abrir ⚙ Ajustes",
    "Fullscreen on / off — with date and time in the status bar":
        "Pantalla completa sí / no — con fecha y hora en la barra de estado",
    "🖱  Mouse": "🖱  Ratón",
    "Click a round / dance header": "Clic en una cabecera de ronda / baile",
    "Collapse or expand that section": "Plegar o desplegar esa sección",
    "Double-click a deck title": "Doble clic en el nombre de un deck",
    "Rename the playlist / wishlist": "Renombrar la lista / lista de deseos",
    "▾ / ▸ arrow in a deck header": "Flecha ▾ / ▸ en la cabecera de un deck",
    "Fold the deck to a header tab (click the tab to reopen)":
        "Plegar el deck a una pestaña de cabecera (clic en la pestaña para reabrirlo)",
    "Drag a row": "Arrastrar una fila",
    "Move a song to another slot, deck, wishlist — or drop it into Explorer / UltraMixer":
        "Mover un tema a otro hueco, deck o lista de deseos — o soltarlo en el Explorador / UltraMixer",
    "Drag a dance header": "Arrastrar una cabecera de baile",
    "Reorder the dance columns of a static deck":
        "Reordenar las columnas de baile de un deck estático",
    "Right-click ▸ 🔍 Find a title": "Clic derecho ▸ 🔍 Buscar un título",
    "Jump to a song by name; repeat to step to the next match":
        "Saltar a un tema por su nombre; repite para ir a la siguiente coincidencia",
    "Ctrl + drag onto a filled slot":
        "Ctrl + arrastrar sobre un hueco ocupado",
    "Dynamic deck: replace the song in that slot with the dragged one":
        "Deck dinámico: reemplazar el tema de ese hueco por el arrastrado",
    "Drop a file from outside": "Soltar un archivo desde fuera",
    "Replace a slot / add to a wishlist (.m3u on a deck imports it)":
        "Reemplazar un hueco / añadir a una lista de deseos (un .m3u sobre un deck lo importa)",
    "▶ or Space on a 📚 library row":
        "▶ o Espacio en una fila de la 📚 biblioteca",
    "Preview that track in the mini player":
        "Escuchar ese tema en el minirreproductor",
    "Double-click a 📚 library row":
        "Doble clic en una fila de la 📚 biblioteca",
    "Open the track in your external audio player":
        "Abrir el tema en tu reproductor de audio externo",
    "▶ / ■ in a row": "▶ / ■ en una fila",
    "Play / stop exactly that song":
        "Reproducir / detener exactamente ese tema",
    "↺ in a row / header": "↺ en una fila / cabecera",
    "Re-roll that song / every song of the dance or round":
        "Volver a elegir ese tema / todos los temas del baile o la ronda",
    "Drop files on a pad": "Soltar archivos sobre un pad",
    "Assign that sample — a multi-select fills the free pads after it (an empty pad can also be clicked to browse)":
        "Asignar ese sample — una selección múltiple llena los pads libres siguientes (también se puede hacer clic en un pad vacío para buscar)",
    "Click a pad": "Clic en un pad",
    "Fire it over the running music; click again to fade it out":
        "Lanzarlo sobre la música en curso; clic de nuevo para hacer un fundido de salida",
    "Fire the first nine pads of the page on screen (works from anywhere while the wall is shown, and takes Ctrl + 1 away from the mark shortcut above)":
        "Lanzar los nueve primeros pads de la página en pantalla (funciona desde cualquier sitio mientras la cartwall está visible, y le quita Ctrl + 1 al atajo de marcar de arriba)",
    "Right-click a pad": "Clic derecho en un pad",
    "🎨 colour straight away, or Settings… for label, volume, its own key, 🔁 endless repeat and whether it ducks the music":
        "🎨 color directamente, o Ajustes… para etiqueta, volumen, su propia tecla, 🔁 repetición infinita y si baja la música",
    "Drag a pad onto another": "Arrastrar un pad sobre otro",
    "Swap the two pads": "Intercambiar los dos pads",
    "Stop every pad (same as ⏹ Stop all)":
        "Detener todos los pads (igual que ⏹ Detener todo)",
    "⚙  Settings…": "⚙  Ajustes…",
    "🎨  Colour": "🎨  Color",
    "🗑  Clear pad": "🗑  Vaciar pad",
    "Wall default": "Por defecto de la cartwall",
    "Grey": "Gris",
    "Green": "Verde",
    "Red": "Rojo",
    "Olive": "Oliva",
    "Purple": "Morado",
    "Amber": "Ámbar",
    "White": "Blanco",
    "📂  Show in Explorer (not saved as a file yet)":
        "📂  Mostrar en el Explorador (aún no guardada como archivo)",
    "Unfold this wishlist": "Desplegar esta lista de deseos",
    "Fold to a tab": "Plegar a una pestaña",
    "🔁  Mark for potential replace\tCtrl+M":
        "🔁  Marcar para posible reemplazo\tCtrl+M",
    "🔁  Unmark (potential replace)\tCtrl+M":
        "🔁  Quitar la marca (posible reemplazo)\tCtrl+M",
    "➕  Create new round": "➕  Crear una ronda nueva",
    "➕  Insert new round after %s":
        "➕  Insertar una ronda nueva después de %s",
    "🗑  Remove %s from this round (keep other dances)":
        "🗑  Quitar %s de esta ronda (los demás bailes se quedan)",
    "🗑  Remove %s from all rounds and heats":
        "🗑  Quitar %s de todas las rondas y grupos",
    "🔒  Back to a planned grid": "🔒  Volver a una cuadrícula planificada",
    "🔒  Switch to static mode": "🔒  Cambiar al modo estático",
    "🔓  Switch to dynamic mode": "🔓  Cambiar al modo dinámico",
    "🧹  Empty this wishlist": "🧹  Vaciar esta lista de deseos",
    "Columns in every playlist": "Columnas en cada lista",
    "Columns in every wishlist": "Columnas en cada lista de deseos",
    "Columns in every party list": "Columnas en cada lista de fiesta",
    "Σ  %d song": "Σ  %d tema",
    "Σ  %d songs": "Σ  %d temas",
    "other": "otro",
    "✦new": "✦nuevo",
    "new": "nuevo",
    "Round": "Ronda",
    "Female": "Femenino",
    "Male": "Masculino",
    "Mixed": "Mixto",
    # ── 🎙 the voice line under 🔈 Announce next dance ──
    "🎙  Announcement voice:": "🎙  Voz de los anuncios:",
    "The voice, the heat number and whether the dance is\nnamed over the music or before it are set in\n⚙ Settings → 🔊 Sound & player.": "La voz, el número de grupo y si el baile se nombra sobre la música\no antes de ella se ajustan en\n⚙ Ajustes → 🔊 Sonido & reproductor.",
    "Female voice": "Voz femenina",
    "Male voice": "Voz masculina",
    "Mixed voices": "Voces mixtas",
    "with heat": "con grupo",
    "🗣  Dance is named:": "🗣  El baile se nombra:",
    "over the music": "sobre la música",
    "before the music": "antes de la música",
    "🎉  Party check": "🎉  Revisión de fiesta",
    "Check the party list — rounds, the late WW / PD rules,\n"
    "duplicates, takt and over-long titles.":
        "Revisar la lista de fiesta — rondas, las reglas «vals vienés tarde» / «Paso Doble tarde»,\n"
        "duplicados, compás y títulos demasiado largos.",
    "Party list": "Lista de fiesta",
    "🎉 <b>%s</b> — %d titles, 1 finding":
        "🎉 <b>%s</b> — %d títulos, 1 hallazgo",
    "🎉 <b>%s</b> — %d titles, %d findings":
        "🎉 <b>%s</b> — %d títulos, %d hallazgos",
    "✅  Nothing to report — the list reads like one the party builder would have made.":
        "✅  Nada que señalar — la lista parece una que habría hecho el generador de fiestas.",
    "↻  Check again": "↻  Revisar de nuevo",
    "🔁 Rounds": "🔁 Rondas",
    "⏳ Spacing": "⏳ Distancias",
    "👯 Duplicates": "👯 Duplicados",
    "⏱ Length": "⏱ Duración",
    "row %d": "fila %d",
    "Standard rounds": "Rondas de Standard",
    "Latin rounds": "Rondas latinas",
    "Social rounds": "Rondas sociales",
    "“%s” is %d title long, not 3 — from ":
        "«%s» tiene %d título, no 3 — desde ",
    "“%s” is %d titles long, not 3 — from ":
        "«%s» tiene %d títulos, no 3 — desde ",
    "a round": "una ronda",
    "the Samba plays two %s running, the second at ":
        "la Samba suena en dos %s seguidas, la segunda en ",
    "“%s” opens the section with %s, not %s — from ":
        "«%s» abre la sección con %s, no con %s — desde ",
    "nothing": "nada",
    "two %s run back to back — “%s” starts at ":
        "dos %s seguidas — «%s» empieza en ",
    ", with no round of the other section between them.":
        ", sin una ronda de la otra sección entre ellas.",
    "the %s never plays — %d %s and not one of them.":
        "el %s no suena nunca — %d %s y en ninguna.",
    "the %s sits out %d %s running, from ":
        "el %s descansa %d %s seguidas, desde ",
    "the Wiener Walzer opens the evening at ":
        "el Wiener Walzer abre la velada en ",
    " — “late WW” holds it back until %d titles have played.":
        " — «vals vienés tarde» lo retiene hasta que hayan sonado %d títulos.",
    "a Paso Doble plays at ": "un Paso Doble suena en ",
    " — “late PD” holds the first one back until %d titles have played.":
        " — «Paso Doble tarde» retiene el primero hasta que hayan sonado %d títulos.",
    "two Paso Dobles sit %d Latin round apart, the second at ":
        "dos Paso Dobles están a %d ronda latina de distancia, el segundo en ",
    "two Paso Dobles sit %d Latin rounds apart, the second at ":
        "dos Paso Dobles están a %d rondas latinas de distancia, el segundo en ",
    " — the rule is %d.": " — la regla dice %d.",
    "“%s” plays %d times, at ": "«%s» suena %d veces, en ",
    "“%s” and “%s” look like the same song, at ":
        "«%s» y «%s» parecen el mismo tema, en ",
    "“%s” is a %s at T%d, outside T%d–T%d — ":
        "«%s» es un %s a T%d, fuera de T%d–T%d — ",
    "“%s” runs %d:%02d, past %d:%02d — ":
        "«%s» dura %d:%02d, más de %d:%02d — ",
    "Class %s": "Clase %s",
    "★ Rarely (1–%d)": "★ Pocas veces (1–%d)",
    "★ Proven (≥%d)": "★ Probado (≥%d)",
    "Filter by how the track was used so far:\n"
    "✦ never — in none of your playlists\n"
    "★ rarely / proven — in 1–%d vs. %d+ of them\n"
    "📅 not since — played, but the newest playlist\n"
    "carrying it is that old (the year comes from the\n"
    "playlist's path; undated lists don't count as old).":
        "Filtrar según cómo se ha usado el tema hasta ahora:\n"
        "✦ nunca — en ninguna de tus listas\n"
        "★ pocas veces / probado — en 1–%d frente a %d+ de ellas\n"
        "📅 no desde — sonó, pero la lista más reciente\n"
        "que lo lleva es así de antigua (el año sale de la\n"
        "ruta de la lista; las listas sin fecha no cuentan como antiguas).",
    "🎄 Seasonal / Christmas": "🎄 Temporada / Navidad",
    "🎺 Anthems": "🎺 Himnos",
    "🎶 Background / non-dance": "🎶 Fondo / no bailable",
    "⏱️ Wrong tempo / not tournament": "⏱️ Tempo incorrecto / no de torneo",
    "👥 Duplicates / raw versions": "👥 Duplicados / versiones en bruto",
    # The deck/library column with the cleaned-up file name.
    "File name": "Nombre de archivo",
    # …and the one with the ID3 album tag.
    "Album": "Álbum",
    # ⚙ Settings → 🔊 Sound & player: an output per source.
    "<b>🔈 Outputs</b> — where each part of the evening is heard:":
        "<b>🔈 Salidas</b> — dónde se oye cada parte de la velada:",
    "🎵  Music:":
        "🎵  Música:",
    "⏸  Filler music:":
        "⏸  Música de pausa:",
    "🔈  Announcements:":
        "🔈  Anuncios:",
    "System default (follows the OS)":
        "Predeterminado del sistema (sigue al sistema)",
    "Same as the music":
        "Igual que la música",
    "Every output the operating system lists can be chosen. On a sound card\n"
    "with several outputs, each pair that shows up as a device of its own\n"
    "(\"Out 3/4\" next to \"Out 1/2\") can take a source of its own; channels\n"
    "3/4 of ONE multichannel device cannot be picked separately.\n"
    "\n"
    "A card that is not plugged in plays on the system default until it is back.":
        "Se puede elegir cualquier salida que muestre el sistema operativo. En una\n"
        "tarjeta de sonido con varias salidas, cada par que aparece como dispositivo\n"
        "propio (\"Out 3/4\" junto a \"Out 1/2\") puede llevar su propia fuente; los\n"
        "canales 3/4 de UN dispositivo multicanal no se pueden elegir por separado.\n"
        "\n"
        "Una tarjeta no conectada suena en el predeterminado del sistema hasta que vuelva.",
    "⚠  %s (not connected)":
        "⚠  %s (no conectado)",
    "The music plays on %s — click for the sound settings.":
        "La música suena en %s — clic para los ajustes de sonido.",
    "🔈 %s is not connected — playing on the system default until it is back.":
        "🔈 %s no está conectado — suena en el predeterminado del sistema hasta que vuelva.",
    # ⚙ Settings → 🔊 Sound & player: 🎧 pre-listen.
    "🎧  Pre-listen:":
        "🎧  Preescucha:",
    "▶ in the library pane, the 🏆 pane, the Similar window and the\n"
    "event plan plays here, with a mini player of its own, and the\n"
    "music keeps running. Refused while it is the output the music\n"
    "plays on. \"Same as the music\": they play on the music's player.":
        "▶ en el panel de biblioteca, el panel 🏆, la ventana de pistas similares\n"
        "y el plan del evento suena aquí, con un minirreproductor propio, y la\n"
        "música sigue. Se rechaza mientras sea la salida de la música.\n"
        "«Igual que la música»: suenan en el reproductor de la música.",
    "🎧 The pre-listen output is not connected, and the system default is the music's own output.":
        "🎧 La salida de preescucha no está conectada y la salida predeterminada del sistema es la de la música.",
    "🎧 Pre-listen refused — its output is the one the music plays on. Choose another in ⚙ Settings.":
        "🎧 Preescucha rechazada — su salida es la de la música. Elige otra en ⚙ Ajustes.",
    # ⌨ Desk keys: the dialog, the volume steps and the F1 sheet.
    "🔼  Music volume up":
        "🔼  Subir el volumen de la música",
    "🔽  Music volume down":
        "🔽  Bajar el volumen de la música",
    "🎛  Cartwall volume (fader or knob)":
        "🎛  Volumen del cartwall (fader o potenciómetro)",
    "🔼  Cartwall volume up":
        "🔼  Subir el volumen del cartwall",
    "🔽  Cartwall volume down":
        "🔽  Bajar el volumen del cartwall",
    "◀  Previous cartwall page":
        "◀  Página anterior del cartwall",
    "▶  Next cartwall page":
        "▶  Página siguiente del cartwall",
    "Cartwall volume — every pad, apart from the music volume.\n"
    "Also on a controller fader and the desk keys (⌨).":
        "Volumen del cartwall — todos los pads, aparte del volumen de la música.\n"
        "También con un fader del controlador y las teclas de mesa (⌨).",
    "🎚  Tempo / pitch (fader or knob)":
        "🎚  Tempo / pitch (fader o potenciómetro)",
    "⏫  Tempo up":
        "⏫  Subir el tempo",
    "⏬  Tempo down":
        "⏬  Bajar el tempo",
    "🎯  Tempo back to ±0 %":
        "🎯  Tempo de vuelta a ±0 %",
    "⌨  Keys":
        "⌨  Teclas",
    "Keys: the pads' and the desk's, in one window":
        "Teclas: las de los pads y las de la mesa, en una sola ventana",
    "⌨  Desk keys":
        "⌨  Teclas de la mesa",
    "⌨  Keys…":
        "⌨  Teclas…",
    "The player's actions on the keyboard, from anywhere in the window — the same ones the 📱 phone and a 🎛 controller run.":
        "Las acciones del reproductor en el teclado, desde cualquier parte de la ventana — las mismas que ejecutan el 📱 móvil y un 🎛 controlador.",
    "💡 A Stream Deck or a macro keypad can send F13–F24: no keyboard has them, so they never clash. A MIDI pad goes through 🎛 Controller instead (on Windows via loopMIDI).":
        "💡 Un Stream Deck o un teclado de macros puede enviar F13–F24: ningún teclado las tiene, así que nunca chocan. Un pad MIDI va por 🎛 Controlador (en Windows con loopMIDI).",
    "↺  Restore defaults":
        "↺  Restablecer valores predeterminados",
    "⚠ moved to %s": "⚠ movido a %s",
    "⚠ The app uses this key":
        "⚠ La app usa esta tecla",
    "Remove this key": "Quitar esta tecla",
    "Another key for this action": "Otra tecla para esta acción",
    "⚠ Also on %s — that one keeps it":
        "⚠ También en %s — esa la conserva",
    "Ctrl + Shift + →":
        "Ctrl + Mayús + →",
    "Ctrl + Shift + ←":
        "Ctrl + Mayús + ←",
    "Ctrl + Shift + P":
        "Ctrl + Mayús + P",
    "Ctrl + Shift + F":
        "Ctrl + Mayús + F",
    "Ctrl + Shift + H":
        "Ctrl + Mayús + H",
    "Ctrl + Shift + D":
        "Ctrl + Mayús + D",
    "Ctrl + Shift + A":
        "Ctrl + Mayús + A",
    "Ctrl + Shift + ↑":
        "Ctrl + Mayús + ↑",
    "Ctrl + Shift + ↓":
        "Ctrl + Mayús + ↓",
    "Ctrl + Shift + PgUp":
        "Ctrl + Mayús + RePág",
    "Ctrl + Shift + PgDown":
        "Ctrl + Mayús + AvPág",
    "Ctrl + Shift + Home":
        "Ctrl + Mayús + Inicio",
    "Ctrl + Shift + X":
        "Ctrl + Mayús + X",
    "Shift":
        "Mayús",
    "🏷 No class": "🏷 Sin clase",
    "🏷  Leave titles without a class out of generated playlists":
        "🏷  Dejar fuera de las listas generadas los temas sin clase",
    "Competition titles whose comment carries no class tag are listed\n"
    "under the '🏷 No class' library category either way. Ticked, they\n"
    "also stay out of the generated playlists, the warm-up and the AI search.":
        "Los temas de competición sin etiqueta de clase en el comentario aparecen\n"
        "siempre en la categoría '🏷 Sin clase' de la biblioteca. Si se marca, también\n"
        "quedan fuera de las listas generadas, el calentamiento y la búsqueda con IA.",
    "🏷 Only with a class": "🏷 Solo con clase",
    "Hide competition titles without a class tag — the class filter\n"
    "shows those for every class.":
        "Ocultar temas de competición sin etiqueta de clase — el filtro\n"
        "de clase los muestra en todas las clases.",
    "(%d/%d tracks)": "(%d/%d temas)",
    "▶  Play": "▶  Reproducir",
    "⏱  Length": "⏱  Duración",
    "★  Rating": "★  Valoración",
    "Class tags from the MP3 comment field":
        "Etiquetas de clase del campo de comentario del MP3",
    "Newest playlist carrying this track":
        "La lista más reciente que lleva este tema",
    "Never played": "Nunca sonó",
    "Played, but none of those playlists is dated":
        "Sonó, pero ninguna de esas listas tiene fecha",
    "⚡ Light — librosa/ffmpeg, works in every install (lite build)":
        "⚡ Ligero — librosa/ffmpeg, funciona en cualquier instalación (versión lite)",
    "⚡ Light — ffmpeg, works in every install (player build)":
        "⚡ Ligero — ffmpeg, funciona en cualquier instalación (versión reproductor)",
    "🔬  Analyze audio (timbre) — %d files to do":
        "🔬  Analizar audio (timbre) — faltan %d archivos",
    "🔬  Re-analyze audio (timbre)  ✓ all cached":
        "🔬  Volver a analizar audio (timbre)  ✓ todo en caché",
    "🎚️  librosa indexed": "🎚️  librosa indexado",
    "🎼  Chroma indexed": "🎼  Chroma indexado",
    "📊  Loudness measured": "📊  Sonoridad medida",
    "🐂  PD highlights detected": "🐂  Culminaciones de PD detectadas",
    "🔇  Silences probed": "🔇  Silencios comprobados",
    "🧠  MERT indexed": "🧠  MERT indexado",
    "🧠  MERT 'sounds-alike' index": "🧠  Índice MERT «suena parecido»",
    "🎙️  Analyze vocals (Demucs)…": "🎙️  Analizar voces (Demucs)…",
    "  – not installed": "  – no instalado",
    "The values a heat is run with — pressed to get back to them after a party list has pulled the panel somewhere else.":
        "Los valores con los que suena un grupo — púlsalo para recuperarlos después de que una lista de fiesta haya llevado el panel a otra parte.",
    "Applied by itself as soon as you play from the 🤸 Practice / party list, and switched back when a tournament deck takes over.":
        "Se aplica solo en cuanto reproduces desde la lista 🤸 Práctica / de fiesta, y vuelve atrás cuando un deck de torneo toma el relevo.",
    "An onboard sound card un-mutes its output stage the moment an app\n"
    "opens it, and the amplifier carries that hiss across the hall — you\n"
    "hear it start with the app and stop when it closes, whether or not\n"
    "anything is playing.\n"
    "\n"
    "Handing the device back after %.0f s of silence takes it away. The cost is the soft click the card makes re-opening it\n"
    "for the next title, so only switch this on if you hear the hiss.":
        "Una tarjeta de sonido integrada quita el silencio de su etapa de salida en el momento\n"
        "en que una aplicación la abre, y el amplificador lleva ese siseo por toda la sala — lo\n"
        "oyes empezar con la aplicación y parar cuando se cierra, suene algo o no.\n"
        "\n"
        "Devolver el dispositivo tras %.0f s de silencio lo elimina. El precio es el leve clic que hace la tarjeta al reabrirse\n"
        "para el siguiente título, así que actívalo solo si oyes el siseo.",
    "⚠️  Not read — %s": "⚠️  No leído — %s",
    "🧹  Removed %d title already in another playlist":
        "🧹  Quitado %d título que ya estaba en otra lista",
    "🧹  Removed %d titles already in another playlist":
        "🧹  Quitados %d títulos que ya estaban en otra lista",
    "🔁  Replaced %d duplicate": "🔁  Reemplazado %d duplicado",
    "🔁  Replaced %d duplicates": "🔁  Reemplazados %d duplicados",
    "⚠  %d duplicate was no longer in its playlist — left as it is":
        "⚠  %d duplicado ya no estaba en su lista — se deja como está",
    "⚠  %d duplicates were no longer in their playlist — left as they are":
        "⚠  %d duplicados ya no estaban en su lista — se dejan como están",
    "💾  Saved → %s": "💾  Guardado → %s",
    "💾  Saved %d competition playlist(s)":
        "💾  Guardadas %d lista(s) de competición",
    "📅  Planned %d competition(s) into %d deck(s)":
        "📅  Planificada(s) %d competición(es) en %d deck(s)",
    "📂  Added %d track(s) from %d file(s)":
        "📂  Añadido(s) %d tema(s) de %d archivo(s)",
    "📂  Imported %d playlists into %d free slot(s)":
        "📂  Importadas %d listas en %d hueco(s) libre(s)",
    "%d extra final-round track(s) kept as backups (stacked under their dance)":
        "%d tema(s) extra de la final guardado(s) como reserva (apilados bajo su baile)",
    "%s line(s) name a file the list already had (imported again, not skipped)":
        "%s línea(s) nombran un archivo que la lista ya tenía (importado de nuevo, no omitido)",
    "%s file(s) not found on disk":
        "%s archivo(s) no encontrado(s) en el disco",
    "%s track(s) with no recognizable dance (skipped)":
        "%s tema(s) sin baile reconocible (omitidos)",
    "%s track(s) left out — no round/dance column to put them in":
        "%s tema(s) omitido(s) — no hay columna de ronda/baile donde ponerlos",
    "%s of %s songs": "%s de %s temas",
    "%s songs": "%s temas",
    "📂 Imported %s · %d round(s) · %d dance(s) (markers)":
        "📂 Importado %s · %d ronda(s) · %d baile(s) (marcadores)",
    "📂 Imported %s · %d round(s) · %d dance(s) (auto-detected)":
        "📂 Importado %s · %d ronda(s) · %d baile(s) (detectado automáticamente)",
    "📂 Imported %s · %d round(s)": "📂 Importado %s · %d ronda(s)",
    "⚠ %d row(s) marked red — play-length / takt issues (hover a red title for details)":
        "⚠ %d fila(s) marcada(s) en rojo — problemas de duración / compás (pasa el ratón por un título rojo para ver los detalles)",
    "🏷  %s is not on disk any more": "🏷  %s ya no está en el disco",
    "🏷  Couldn't re-read %s: %s": "🏷  No se pudo volver a leer %s: %s",
    "★  Couldn't store the rating: %s":
        "★  No se pudo guardar la valoración: %s",
    "🏷  Couldn't store the tags: %s":
        "🏷  No se pudieron guardar las etiquetas: %s",
    "🏷  Edit tags…": "🏷  Editar etiquetas…",
    "🏷  Edit tags of %d tracks…": "🏷  Editar etiquetas de %d temas…",
    "🏷  Edit tags": "🏷  Editar etiquetas",
    "🏷  Edit tags of %d tracks": "🏷  Editar etiquetas de %d temas",
    "%d tracks — a field they differ in is kept per track until you change it.":
        "%d temas — un campo en el que difieren se mantiene por tema hasta que lo cambies.",
    "keep (differs per track)": "mantener (distinto en cada tema)",
    "no stars": "sin estrellas",
    "Stars:": "Estrellas:",
    "Classes:": "Clases:",
    "None ticked = suits every class.":
        "Ninguna marcada = vale para todas las clases.",
    "Instrumental (no vocals)": "Instrumental (sin voz)",
    "differs per track — typing here replaces them all":
        "distinto en cada tema — escribir aquí los reemplaza todos",
    "e.g. classic, vocal_f": "p. ej. classic, vocal_f",
    "Markers:": "Marcadores:",
    "Add this marker, or take it out again":
        "Añadir este marcador, o quitarlo de nuevo",
    "↺  Back to the file's tags": "↺  Volver a las etiquetas del archivo",
    "Forget every change made here in the app — stars, classes,\n"
    "instrumental, markers and Custom read from the MP3 again.":
        "Olvidar todos los cambios hechos aquí en la aplicación — estrellas, clases,\n"
        "instrumental, marcadores y Custom se vuelven a leer del MP3.",
    "Filled from the MP3 tag %s. What is typed here wins over it.":
        "Rellenado desde la etiqueta MP3 %s. Lo que se escribe aquí tiene prioridad.",
    "Kept in the app only. Right-click a column header to fill it from an MP3 tag.":
        "Guardado solo en la aplicación. Clic derecho en la cabecera de una columna para rellenarla desde una etiqueta MP3.",
    "Changed in the Custom field on the first tab":
        "Se cambia en el campo Custom de la primera pestaña",
    "Map Custom to an MP3 tag…": "Asignar Custom a una etiqueta MP3…",
    "🏷  Custom field": "🏷  Campo Custom",
    "🏷  Fill Custom from this tag": "🏷  Rellenar Custom desde esta etiqueta",
    "In none of the %d sampled MP3s": "En ninguno de los %d MP3 muestreados",
    "In %d of %d sampled MP3s, e.g. “%s”":
        "En %d de %d MP3 muestreados, p. ej. «%s»",
    "The Custom column shows this tag of each MP3. A value typed in the 🏷 editor wins over it, and on Save it can be written into it.":
        "La columna Custom muestra esta etiqueta de cada MP3. Un valor escrito en el editor 🏷 tiene prioridad y al guardar se puede escribir en ella.",
    "In the app only": "Solo en la aplicación",
    "Frame:": "Marco:",
    "Description:": "Descripción:",
    "e.g. ultramixer_last_played": "p. ej. ultramixer_last_played",
    "Custom — a free field per track, typed in the 🏷 editor.\n"
    "Right-click the header to fill it from an MP3 tag.":
        "Custom — un campo libre por tema, escrito en el editor 🏷.\n"
        "Clic derecho en la cabecera para rellenarlo desde una etiqueta MP3.",
    "Custom goes into the tag it is mapped to.":
        "Custom va a la etiqueta a la que está asignado.",
    "Extended tags": "Etiquetas ampliadas",
    "Every frame of the MP3, written straight into the file on Save. The fields of the form on the first tab are changed there.":
        "Cada marco del MP3, escrito directamente en el archivo al guardar. Los campos del formulario de la primera pestaña se cambian allí.",
    "Changed in the form on the first tab":
        "Se cambia en el formulario de la primera pestaña",
    "In the MP3 file": "En el archivo MP3",
    "In the app": "En la aplicación",
    "Only for MP3 files on disk": "Solo para archivos MP3 en el disco",
    "Covers differ": "Las carátulas difieren",
    "Cover can't be shown": "La carátula no se puede mostrar",
    "No cover": "Sin carátula",
    "< keep >": "< mantener >",
    "< blank >": "< vacío >",
    "Title:": "Título:",
    "Artist:": "Artista:",
    "Year:": "Año:",
    "Comment:": "Comentario:",
    "Album artist:": "Artista del álbum:",
    "Composer:": "Compositor:",
    "Disc number:": "Número de disco:",
    "Description": "Descripción",
    "Value": "Valor",
    "➕  Add field": "➕  Añadir campo",
    "Only for an MP3 file on disk": "Solo para un archivo MP3 en el disco",
    "Couldn't read the MP3 tags: %s":
        "No se pudieron leer las etiquetas MP3: %s",
    "Can only be removed, not edited here":
        "Aquí solo se puede quitar, no editar",
    "🏷  %s is in the player — stop it to write its MP3 tags":
        "🏷  %s está en el reproductor — detenlo para escribir sus etiquetas MP3",
    "🏷  Couldn't write the MP3 tags: %s":
        "🏷  No se pudieron escribir las etiquetas MP3: %s",
    "🏷  Write into the MP3?": "🏷  ¿Escribir en el MP3?",
    "Also write %s into the MP3 file?":
        "¿Escribir también %s en el archivo MP3?",
    "Also write %s into the %d MP3 files?":
        "¿Escribir también %s en los %d archivos MP3?",
    "Stars go into the Windows rating; classes, instrumental and markers into the comment, where other programs see them too. With No they stay in the app only.":
        "Las estrellas van a la valoración de Windows; las clases, instrumental y marcadores al comentario, donde otros programas también los ven. Con No se quedan solo en la aplicación.",
    "stars": "estrellas",
    "custom": "Custom",
    "Custom text": "Texto propio",
    "Comment": "Comentario",
    "Custom link": "Enlace propio",
    "Rating": "Valoración",
    "Picture": "Imagen",
    "Private data": "Datos privados",
    "Embedded object": "Objeto incrustado",
    "CD identifier": "Identificador de CD",
    "Unique file id": "Id. único de archivo",
    "Lyrics": "Letra",
    "Play count": "Contador de reproducciones",
    "Volume adjustment": "Ajuste de volumen",
    "Grouping": "Agrupación",
    "Subtitle": "Subtítulo",
    "Album artist": "Artista del álbum",
    "Conductor": "Director",
    "Remixed by": "Remezclado por",
    "Key": "Tonalidad",
    "Composer": "Compositor",
    "Lyricist": "Letrista",
    "Track number": "Número de pista",
    "Disc number": "Número de disco",
    "Year": "Año",
    "Recording date": "Fecha de grabación",
    "Publisher": "Editorial",
    "Language": "Idioma",
    "Length (ms)": "Duración (ms)",
    "Encoded by": "Codificado por",
    "Encoder settings": "Ajustes del codificador",
    "Media type": "Tipo de medio",
    "Grouping (iTunes)": "Agrupación (iTunes)",
    "🏷  %s: tags unchanged": "🏷  %s: etiquetas sin cambios",
    "⚠  Track no longer in any open deck":
        "⚠  El tema ya no está en ningún deck abierto",
    "🗑  Removed “%s” from 1 slot — Ctrl+Z undoes":
        "🗑  Quitado «%s» de 1 hueco — Ctrl+Z lo deshace",
    "🗑  Removed “%s” from %d slots — Ctrl+Z undoes":
        "🗑  Quitado «%s» de %d huecos — Ctrl+Z lo deshace",
    "↺  Replaced “%s” with “%s” in 1 slot — Ctrl+Z undoes":
        "↺  Reemplazado «%s» por «%s» en 1 hueco — Ctrl+Z lo deshace",
    "↺  Replaced “%s” with “%s” in %d slots — Ctrl+Z undoes":
        "↺  Reemplazado «%s» por «%s» en %d huecos — Ctrl+Z lo deshace",
    "🧭  Fixed %d track path": "🧭  Corregida %d ruta de tema",
    "🧭  Fixed %d track paths": "🧭  Corregidas %d rutas de temas",
    "🧭  Moved %d track onto the Reference path":
        "🧭  Movido %d tema a la ruta de referencia",
    "🧭  Moved %d tracks onto the Reference path":
        "🧭  Movidos %d temas a la ruta de referencia",
    "No tracks in the visible playlists or the wishlists.":
        "No hay temas en las listas visibles ni en las listas de deseos.",
    "Checked %d tracks — %d already valid.":
        "%d temas comprobados — %d ya válidos.",
    "🧭  Relocated %d broken reference to their real files (Ctrl+Z undoes).":
        "🧭  Reubicada %d referencia rota en su archivo real (Ctrl+Z lo deshace).",
    "🧭  Relocated %d broken references to their real files (Ctrl+Z undoes).":
        "🧭  Reubicadas %d referencias rotas en sus archivos reales (Ctrl+Z lo deshace).",
    "⚠  %d still unresolved — no matching file in the library:":
        "⚠  %d siguen sin resolver — ningún archivo coincidente en la biblioteca:",
    "⚠  %d valid track is not on the Reference path %s":
        "⚠  %d tema válido no está en la ruta de referencia %s",
    "⚠  %d valid tracks are not on the Reference path %s":
        "⚠  %d temas válidos no están en la ruta de referencia %s",
    "↪ %d has a copy there — 🧭 Fix swaps them in the playlists.":
        "↪ %d tiene una copia allí — 🧭 Corregir lo cambia en las listas.",
    "↪ %d have a copy there — 🧭 Fix swaps them in the playlists.":
        "↪ %d tienen una copia allí — 🧭 Corregir los cambia en las listas.",
    "⚠ %d has no copy there:":
        "⚠ %d no tiene copia allí:",
    "⚠ %d have no copy there:":
        "⚠ %d no tienen copia allí:",
    "✅  All track paths are valid.":
        "✅  Todas las rutas de temas son válidas.",
    "🎛  Re-pointed %d cartwall pad at its real sample.":
        "🎛  %d Pad de la Cartwall apunta de nuevo a su sample real.",
    "🎛  Re-pointed %d cartwall pads at their real samples.":
        "🎛  %d Pads de la Cartwall apuntan de nuevo a sus samples reales.",
    "🧭  Fixed 1 path in 1 file": "🧭  Corregida 1 ruta en 1 archivo",
    "🧭  Fixed %d paths in 1 file": "🧭  Corregidas %d rutas en 1 archivo",
    "🧭  Fixed %d paths in %d files": "🧭  Corregidas %d rutas en %d archivos",
    "🧹  Removed %d track(s) already in a playlist":
        "🧹  Quitado(s) %d tema(s) que ya estaba(n) en una lista",
    "↺  No other %s near the end of the list":
        "↺  No hay otro %s cerca del final de la lista",
    "🔍  No title matching “%s”": "🔍  Ningún título coincide con «%s»",
    "🔁  Marked %d track for replace": "🔁  Marcado %d tema para reemplazar",
    "🔁  Marked %d tracks for replace": "🔁  Marcados %d temas para reemplazar",
    "🔁  Unmarked %d track": "🔁  Desmarcado %d tema",
    "🔁  Unmarked %d tracks": "🔁  Desmarcados %d temas",
    "📌  Pin — keep this title when the round is re-rolled":
        "📌  Fijar — conservar este título al volver a sortear la ronda",
    "📌  Unpin": "📌  Soltar",
    "📌  Pinned — unpin the title to re-roll it":
        "📌  Fijado — suelta el título para volver a sortearlo",
    "📌  Pinned %d title — the round's ↻ keeps it":
        "📌  Fijado %d título — el ↻ de la ronda lo conserva",
    "📌  Pinned %d titles — the round's ↻ keeps them":
        "📌  Fijados %d títulos — el ↻ de la ronda los conserva",
    "📌  Unpinned %d title": "📌  Soltado %d título",
    "📌  Unpinned %d titles": "📌  Soltados %d títulos",
    "🚦  Check ▾": "🚦  Revisar ▾",
    "🚦 Ready? — the pre-flight before the event, one traffic light per\n"
    "check: missing files, loudness, silence probe, Paso Doble highlights,\n"
    "duplicates and the music check, each with its fix.\n"
    "The menu also opens 🔁 Check duplicates, 🎵 Check music and\n"
    "🧭 Fix paths on their own.":
        "🚦 ¿Listo? — la comprobación previa al evento, un semáforo por\n"
        "prueba: archivos que faltan, sonoridad, prueba de silencios, culminaciones\n"
        "del Paso Doble, duplicados y la comprobación de música, cada uno con su solución.\n"
        "El menú también abre por separado 🔁 Comprobar duplicados, 🎵 Comprobar música y\n"
        "🧭 Corregir rutas.",
    "🚦  Ready?": "🚦  ¿Listo?",
    "Pre-flight before the event, one traffic light per check — over every\n"
    "deck that holds titles and the Practice list, each with its fix.\n"
    "A heading in the report opens its full tool.":
        "Comprobación previa al evento, un semáforo por prueba — en cada\n"
        "deck con títulos y en la lista de práctica, cada uno con su solución.\n"
        "Un encabezado del informe abre su herramienta completa.",
    "No tempo, length or round-structure problem in the decks.":
        "Ningún problema de tempo, duración o estructura de rondas en los decks.",
    "%d titles with a tempo or length problem: %s":
        "%d títulos con un problema de tempo o duración: %s",
    "%d playlists with uneven rounds or heats: %s":
        "%d listas con rondas o grupos desiguales: %s",
    "🎵  Show the report…": "🎵  Mostrar el informe…",
    "Click the heading to open the full tool.":
        "Haz clic en el encabezado para abrir la herramienta completa.",
    "🚦  Ready for the event?": "🚦  ¿Listo para el evento?",
    "🟢  Ready — every check is green.":
        "🟢  Listo — todas las pruebas están en verde.",
    "🟡  Playable, with loose ends.": "🟡  Se puede tocar, con cabos sueltos.",
    "🔴  Not ready — some titles will not play.":
        "🔴  No está listo — algunos títulos no sonarán.",
    "🧭  Fix paths…": "🧭  Corregir rutas…",
    "📊  Measure loudness…": "📊  Medir sonoridad…",
    "🐂  Find highlights…": "🐂  Buscar momentos culminantes…",
    "🔁  Resolve duplicates…": "🔁  Resolver duplicados…",
    "📁  Music files": "📁  Archivos de música",
    "Every title is where the list says.":
        "Cada título está donde dice la lista.",
    "%d titles are not on the Reference path.":
        "%d títulos no están en la ruta de referencia.",
    "%d have a copy there — 🧭 Fix paths swaps them in.":
        "%d tienen allí una copia — 🧭 Corregir rutas las sustituye.",
    "%d have no copy there: %s": "%d no tienen copia allí: %s",
    "Drive %s is not connected — %d titles live there.":
        "La unidad %s no está conectada — allí hay %d títulos.",
    "%d titles not found: %s": "%d títulos no encontrados: %s",
    "🎶  Playlists": "🎶  Listas",
    "Nothing to play yet — load or build a playlist first.":
        "Aún no hay nada que tocar — primero carga o crea una lista.",
    "📊  Loudness": "📊  Sonoridad",
    "Every title is measured — 🔊 Equalize volume can stay on.":
        "Todos los títulos están medidos — 🔊 Igualar volumen puede seguir activado.",
    "%d of %d titles have no loudness measurement — 🔊 Equalize volume stays off.":
        "%d de %d títulos no tienen medición de sonoridad — 🔊 Igualar volumen sigue desactivado.",
    "🔇  Silence probe": "🔇  Prueba de silencios",
    "Every title is probed — playback skips its silent edges.":
        "Todos los títulos están comprobados — la reproducción salta sus bordes en silencio.",
    "%d of %d titles are not probed — each is decoded when it starts.":
        "%d de %d títulos no están comprobados — cada uno se decodifica al empezar.",
    "🐂  Paso Doble highlights": "🐂  Momentos culminantes del Paso Doble",
    "Every Paso Doble knows its highlights.":
        "Cada Paso Doble conoce sus momentos culminantes.",
    "No Paso Doble in tonight's lists.":
        "No hay Paso Doble en las listas de esta noche.",
    "%d of %d Paso Dobles have no highlights — 🐂 cannot stop at one.":
        "%d de %d Pasos Dobles no tienen momentos culminantes — 🐂 no puede parar en ninguno.",
    "🔁  Duplicates": "🔁  Duplicados",
    "%d duplicates across the decks and the Practice list.":
        "%d duplicados entre los decks y la lista de práctica.",
    "No title is planned twice.": "Ningún título está previsto dos veces.",
    "🧹  Removed %d duplicate title": "🧹  Quitado %d título duplicado",
    "🧹  Removed %d duplicate titles": "🧹  Quitados %d títulos duplicados",
    "⭐  Moved %d track(s) to the wishlist":
        "⭐  Movido(s) %d tema(s) a la lista de deseos",
    "⭐  Added %d track(s) to the wishlist":
        "⭐  Añadido(s) %d tema(s) a la lista de deseos",
    "  ·  🧹 %d already in a playlist removed":
        "  ·  🧹 %d ya en una lista, quitado(s)",
    "➕  Added %d track(s)": "➕  Añadido(s) %d tema(s)",
    "➕  Added %d track(s) — rounds re-cut":
        "➕  Añadido(s) %d tema(s) — rondas redistribuidas",
    "🎯  Placed %d track(s)": "🎯  Colocado(s) %d tema(s)",
    "  (%d skipped — no free slot)": "  (%d omitido(s) — no hay hueco libre)",
    "… plus %d more": "… y %d más",
    "🔁  Replaced “%s” with “%s”": "🔁  Reemplazado «%s» por «%s»",
    "⚠  “%s” is already in this playlist — not replaced":
        "⚠  «%s» ya está en esta lista — no se reemplazó",
    "🔁  Replaced %d track(s)": "🔁  Reemplazado(s) %d tema(s)",
    "🔁  Replaced %d, ➕ added %d track(s)":
        "🔁  Reemplazados %d, ➕ añadido(s) %d tema(s)",
    "  (%s — skipped)": "  (%s — omitido)",
    "%d already planned": "%d ya previstos",
    "%d with no dance": "%d sin baile",
    "⚠  Couldn't tell what dance “%s” is — nothing added":
        "⚠  No se pudo saber qué baile es «%s» — no se añadió nada",
    "⚠  “%s” is already in this playlist — nothing added":
        "⚠  «%s» ya está en esta lista — no se añadió nada",
    "Nothing added — %s": "No se añadió nada — %s",
    "TSO tempo equalize → on": "Igualar tempo TSO → activado",
    "TSO tempo equalize → off": "Igualar tempo TSO → desactivado",
    "🎉  Party set — %s": "🎉  Ajuste de fiesta — %s",
    "🏆  Tournament set — %s": "🏆  Ajuste de torneo — %s",
    "🎚  Own settings — %s": "🎚  Ajustes propios — %s",
    "🎉  Party set applied": "🎉  Ajuste de fiesta aplicado",
    "🏆  Tournament set applied": "🏆  Ajuste de torneo aplicado",
    "nothing to change": "nada que cambiar",
    ", running at %s": ", reloj en %s",
    "🕒  Timetable saved — %d entries": "🕒  Horario guardado — %d entradas",
    ", fading every %ss": ", fundido cada %s s",
    "play length → %s": "duración → %s",
    "fade-out → %s s": "fundido de salida → %s s",
    "auto-advance → on": "avance automático → activado",
    "auto-advance → off": "avance automático → desactivado",
    "pause between songs → on": "pausa entre temas → activada",
    "pause between songs → off (no break music)":
        "pausa entre temas → desactivada (sin música de pausa)",
    "equalize volume → on": "igualar volumen → activado",
    "equalize volume → off": "igualar volumen → desactivado",
    "announce next dance → on": "anunciar el siguiente baile → activado",
    "announce next dance → off": "anunciar el siguiente baile → desactivado",
    "double-click → starts the title": "doble clic → inicia el título",
    "double-click → cues it": "doble clic → solo lo prepara",
    "🐂 Paso Doble highlight stop → on":
        "🐂 Parada en el momento culminante del Paso Doble → activada",
    "🐂 Paso Doble highlight stop → off":
        "🐂 Parada en el momento culminante del Paso Doble → desactivada",
    "🐂 Paso Doble start after → %s s":
        "🐂 Paso Doble: empezar tras → %s s",
    "🐂 Paso Doble stop after highlight → %d":
        "🐂 Paso Doble parar tras el clímax → %d",
    "📌 Session saved — decks, wishlists, 🎛 cartwall and layout.":
        "📌 Sesión guardada — decks, listas de deseos, 🎛 Cartwall y diseño.",
    "Error generating playlist: %s": "Error al generar la lista: %s",
    "  (iteration %d)": "  (iteración %d)",
    " — from %s": " — de %s",
    "Generated %d songs — %s, %s, %s": "Generados %d temas — %s, %s, %s",
    "Skipped competition(s):": "Competiciones omitidas:",
    "📅 Day plan: %d generated, %d skipped":
        "📅 Plan del día: %d generada(s), %d omitida(s)",
    "📅 Day plan: %d competition(s) generated":
        "📅 Plan del día: %d competición(es) generada(s)",
    "Seeding '%s' from past playlists…":
        "Rellenando «%s» con listas anteriores…",
    "Error reading past playlists: %s": "Error al leer listas anteriores: %s",
    "Generated %d songs — %s": "Generados %d temas — %s",
    "Timbre similarity on for ↺ regenerations":
        "Similitud de timbre activada para volver a sortear ↺",
    "Timbre similarity off for ↺ regenerations":
        "Similitud de timbre desactivada para volver a sortear ↺",
    "Building '%s' playlist…": "Creando la lista «%s»…",
    "No tracks matched theme '%s'.":
        "Ningún tema coincide con la temática «%s».",
    "Decade themes require year tags in your MP3s; you can also map\n"
    "songs to themes in themes.json (track_themes).":
        "Las temáticas por décadas necesitan etiquetas de año en tus MP3; también puedes asignar\n"
        "temas a temáticas en themes.json (track_themes).",
    "No tracks matched '%s'.": "Ningún tema coincide con «%s».",
    "Theme '%s' — %d tracks": "Temática «%s» — %d temas",
    "🤸 Building %s…": "🤸 Creando %s…",
    "Building %s…": "Creando %s…",
    "%s — %d tracks": "%s — %d temas",
    "🔀 %s shuffled — %d tracks": "🔀 %s mezclado — %d temas",
    "🤸 Practice: nothing loadable from %s":
        "🤸 Práctica: nada que se pueda cargar desde %s",
    "🎧 Nothing loadable from %s": "🎧 Nada que se pueda cargar desde %s",
    "🤖 %d/%d slots filled by %s": "🤖 %d/%d huecos rellenados por %s",
    "🤖 %d tracks by %s": "🤖 %d temas de %s",
    "%s not installed": "%s no está instalado",
    "Build %s index": "Crear índice %s",
    "Build the %s index over %s tracks from %s?":
        "¿Crear el índice %s con %s temas de %s?",
    "Analyses the melody/harmony of each track once (slow the first time, then cached).":
        "Analiza la melodía/armonía de cada tema una vez (lento la primera vez, luego en caché).",
    "Loads a neural model and embeds each track once (slow the first time, then cached).":
        "Carga un modelo neuronal e incrusta cada tema una vez (lento la primera vez, luego en caché).",
    "Reuses anything already computed.": "Se reutiliza todo lo ya calculado.",
    "Building %s index…": "Creando el índice %s…",
    "%s indexing failed": "Falló la indexación %s",
    "All %d file(s) failed to embed.\n"
    "\n"
    "First error:\n"
    "%s\n"
    "\n"
    "See the console log for the full traceback.":
        "Ninguno de los %d archivo(s) se pudo incrustar.\n"
        "\n"
        "Primer error:\n"
        "%s\n"
        "\n"
        "El registro de la consola muestra la traza completa.",
    "unknown": "desconocido",
    "%s indexing failed.": "Falló la indexación %s.",
    "%s index built — %d embedded, %d failed.":
        "Índice %s creado — %d incrustados, %d fallidos.",
    "%s index built — %d embedded.": "Índice %s creado — %d incrustados.",
    "%s index ready": "Índice %s listo",
    "Embedded %d track(s) (%d failed — see log).":
        "%d tema(s) incrustado(s) (%d fallido(s) — ver registro).",
    "Embedded %d track(s).": "%d tema(s) incrustado(s).",
    "The %s method is now ready in the Similar-Tracks window.":
        "El método %s ya está disponible en la ventana Temas similares.",
    "%s indexing cancelled — %d embedded so far (cached).":
        "Indexación %s cancelada — %d incrustados hasta ahora (en caché).",
    "Library error: %s": "Error de biblioteca: %s",
    "Analyzing %s …": "Analizando %s …",
    "Only %s of %s tracks are analyzed so far (analysis is still running). Let analysis finish and try again.":
        "Solo %s de %s temas están analizados hasta ahora (el análisis sigue en marcha). Deja que termine el análisis e inténtalo de nuevo.",
    "Only %s of %s tracks are analyzed so far. Let analysis finish and try again.":
        "Solo %s de %s temas están analizados hasta ahora. Deja que termine el análisis e inténtalo de nuevo.",
    "Global search is on but the repository isn't analyzed yet — open ⚙ Settings → “Build / refresh global audio index”.":
        "La búsqueda global está activada, pero el repositorio aún no está analizado — abre ⚙ Ajustes → «Crear / actualizar el índice de audio global».",
    "No tracks are analyzed yet — run 'Analyze Audio' first.":
        "Aún no hay temas analizados — ejecuta primero «Analizar audio».",
    "All tracks are analyzed — this file just has no close match.":
        "Todos los temas están analizados — este archivo simplemente no tiene una coincidencia cercana.",
    "No similar tracks found in %s.":
        "No se encontraron temas similares en %s.",
    "Found %d similar to %s (%s)": "Encontrados %d similares a %s (%s)",
    "Global library ready from cache — %s files.":
        "Biblioteca global lista desde la caché — %s archivos.",
    "Global index: %s files, %s analyzed.":
        "Índice global: %s archivos, %s analizados.",
    "Scanning repository… %s/%s  (%s left)":
        "Escaneando el repositorio… %s/%s  (quedan %s)",
    "Remove cached data of deleted music files and compact %s (%s MB)?":
        "¿Quitar los datos guardados de archivos de música eliminados y compactar %s (%s MB)?",
    "Feature vectors, embeddings and loudness of files that no longer exist on disk are removed for good (they would simply be re-analyzed if the files ever come back). Compacting can take a few minutes.":
        "Los vectores de características, embeddings y sonoridad de archivos que ya no existen en el disco se eliminan para siempre (si los archivos vuelven, simplemente se analizan de nuevo). Compactar puede tardar unos minutos.",
    "deleted tracks": "temas eliminados",
    "tag records": "registros de etiquetas",
    "feature vectors": "vectores de características",
    "AI embeddings": "embeddings de IA",
    "loudness values": "valores de sonoridad",
    "silence maps": "mapas de silencios",
    "vocal shares": "proporciones de voz",
    "noise floors": "niveles de ruido de fondo",
    "playlist index entries": "entradas del índice de listas",
    "stale index markers": "marcadores de índice obsoletos",
    "🧹 Database compacted: %s MB → %s MB (%s MB freed).":
        "🧹 Base de datos compactada: %s MB → %s MB (%s MB liberados).",
    "Removed rows: %s.": "Filas eliminadas: %s.",
    "none — everything is still in use": "ninguna — todo se sigue usando",
    "Cleanup did not run:": "La limpieza no se ejecutó:",
    "🗑  Reset database…":
        "🗑  Restablecer la base de datos…",
    "Empty chosen parts of the database: the tags read from the files,\nthe audio analysis, your own data. A dialog asks which; your own\ndata is backed up first, and the app restarts afterwards.":
        "Vacía las partes elegidas de la base de datos: las etiquetas leídas de los\narchivos, el análisis de audio, tus propios datos. Un diálogo pregunta cuáles;\ntus datos se respaldan antes y la app se reinicia después.",
    "🗑  Reset database":
        "🗑  Restablecer la base de datos",
    "🗑 Reset database":
        "🗑 Restablecer la base de datos",
    "🏷  Tags read from the music files":
        "🏷  Etiquetas leídas de los archivos de música",
    "🎚  Audio analysis":
        "🎚  Análisis de audio",
    "✋  My own data":
        "✋  Mis propios datos",
    "Dance, BPM, class and title of every file, the file list and the learned playlist index. The next library scan reads them again (minutes).":
        "Baile, BPM, clase y título de cada archivo, la lista de archivos y el índice de playlists aprendido. El próximo escaneo de la biblioteca los vuelve a leer (minutos).",
    "Features, AI embeddings, loudness, silences, waveforms, vocal shares and detected PD highlights. ⚗ Analysis builds them again (hours).":
        "Features, embeddings de IA, sonoridad, silencios, formas de onda, partes vocales y highlights PD detectados. ⚗ Análisis los vuelve a crear (horas).",
    "Your tag edits, hand-set PD marks and the 📜 play log. Nothing rebuilds them; only ♻ Restore user data backup brings them back.":
        "Tus ediciones de etiquetas, las marcas PD puestas a mano y el 📜 registro de reproducción. Nada los reconstruye; solo ♻ Restaurar la copia de datos propios los recupera.",
    "Empty the chosen parts of the database. Your own data is backed up first either way, and the app restarts afterwards.":
        "Vacía las partes elegidas de la base de datos. Tus propios datos se respaldan antes en cualquier caso, y la app se reinicia después.",
    "Reset and restart":
        "Restablecer y reiniciar",
    "Resetting database…":
        "Restableciendo la base de datos…",
    "The app still shows the old data until it restarts. Restart now?":
        "La app muestra los datos antiguos hasta que se reinicie. ¿Reiniciar ahora?",
    "Reset did not run:":
        "El restablecimiento no se ejecutó:",
    "<b>Excluded folders</b> — titles in these folders and below stay out of the library, one folder per line:":
        "<b>Carpetas excluidas</b> — los títulos de estas carpetas y sus subcarpetas quedan fuera de la biblioteca, una carpeta por línea:",
    "Left out of ⭐ Favorites and 🌐 Whole library alike: not shown, not\nsearched, never suggested. Nothing on disk changes, and the tags\nread so far stay cached, so a folder taken off the list is back\nafter a restart.":
        "Fuera de ⭐ Favoritos y de 🌐 Toda la biblioteca por igual: no se muestran,\nno se buscan, nunca se sugieren. Nada cambia en el disco y las etiquetas\nleídas siguen guardadas, así que una carpeta quitada de la lista vuelve\ntras un reinicio.",
    "Hide a folder from the library":
        "Ocultar una carpeta de la biblioteca",
    "🙈 Excluded folders":
        "🙈 Carpetas excluidas",
    "The library is loaded when the app starts, so the excluded folders change with the next start.\n\nRestart now?":
        "La biblioteca se carga al iniciar la app, así que las carpetas excluidas cambian con el próximo inicio.\n\n¿Reiniciar ahora?",
    "📤  Export manual PD marks…": "📤  Exportar marcas PD manuales…",
    "📥  Import manual PD marks…": "📥  Importar marcas PD manuales…",
    "Export manual PD marks": "Exportar marcas PD manuales",
    "Import manual PD marks": "Importar marcas PD manuales",
    "Save the Paso Doble highlights you set by hand (🎯) to a file,\n"
    "to take them to another PC. Detected highlights are not included —\n"
    "🐂 finds those again by itself.":
        "Guarda en un archivo los momentos culminantes del Paso Doble puestos a mano (🎯),\n"
        "para llevarlos a otro PC. Los detectados no se incluyen —\n"
        "🐂 los vuelve a encontrar solo.",
    "Load hand-set Paso Doble highlights exported on another PC.\n"
    "They are matched by the music itself, not by the file path, and\n"
    "replace what this PC has for those tracks.":
        "Carga momentos culminantes del Paso Doble puestos a mano y exportados en otro PC.\n"
        "Se asignan por la propia música, no por la ruta del archivo, y\n"
        "reemplazan lo que este PC tiene para esos temas.",
    "No Paso Doble highlight has been set by hand yet.":
        "Aún no se ha puesto a mano ningún momento culminante del Paso Doble.",
    "Could not write the file:": "No se pudo escribir el archivo:",
    "📤 %d hand-set Paso Doble highlight(s) saved to:\n"
    "%s":
        "📤 %d momento(s) culminante(s) del Paso Doble puesto(s) a mano guardado(s) en:\n"
        "%s",
    "This is no manual-PD-marks file:":
        "Este no es un archivo de marcas PD manuales:",
    "📥 %d hand-set Paso Doble highlight(s) imported — %d of them belong to a track this PC already knows.\n"
    "\n"
    "The others are kept and apply as soon as that music turns up here.":
        "📥 %d momento(s) culminante(s) del Paso Doble puesto(s) a mano importado(s) — %d de ellos pertenecen a un tema que este PC ya conoce.\n"
        "\n"
        "Los demás se guardan y se aplican en cuanto esa música aparezca aquí.",
    "<b>Backup folder</b> — where the daily backup of your own data goes (e.g. D:\\Dropbox\\DanceSportPlayer). Empty: next to the database.":
        "<b>Carpeta de copias</b> — dónde va la copia diaria de los datos propios (p. ej. D:\\Dropbox\\DanceSportPlayer). Vacío: junto a la base de datos.",
    "♻  Restore user data backup…": "♻  Restaurar copia de los datos propios…",
    "Restore user data backup": "Restaurar copia de los datos propios",
    "Merge a daily backup of your tag edits, hand-set Paso Doble\n"
    "highlights and play log back in. The app keeps one per day for the last 7 days.\n"
    "Everything else in the database is left as it is.":
        "Recupera una copia diaria de tus cambios de etiquetas, momentos culminantes\n"
        "del Paso Doble puestos a mano y registro de reproducción. La aplicación guarda una por día durante los últimos 7 días.\n"
        "Todo lo demás de la base de datos queda como está.",
    "This is no user data backup:":
        "Esta no es una copia de los datos propios:",
    "♻ %d tag edit(s) and %d hand-set Paso Doble highlight(s) restored, %d played title(s) added to the play log.\n"
    "\n"
    "They take effect after a restart of the app.":
        "♻ Restaurado(s) %d cambio(s) de etiquetas y %d momento(s) culminante(s) del Paso Doble puesto(s) a mano, %d título(s) tocado(s) añadido(s) al registro.\n"
        "\n"
        "Surten efecto tras reiniciar la aplicación.",
    "Date": "Fecha",
    "List": "Lista",
    "Duration": "Duración",
    "📜 Played titles": "📜 Títulos tocados",
    "📜  Played titles…": "📜  Títulos tocados…",
    "Nothing has been played yet. A title is logged in playing mode\n"
    "once it has run for 10 seconds, the moment its row greys out.":
        "Aún no se ha tocado nada. Un título se registra en el modo de reproducción\n"
        "en cuanto lleva 10 segundos sonando, el momento en que su fila se vuelve gris.",
    "💾  Save as CSV…": "💾  Guardar como CSV…",
    "Save this evening as a table for Excel: date, start, artist, title,\n"
    "composer, dance, list and how long each title ran — e.g. for a GEMA report.":
        "Guarda esta noche como tabla para Excel: fecha, inicio, artista, título,\n"
        "compositor, baile, lista y cuánto sonó cada título — p. ej. para un informe a la entidad de derechos.",
    "🗑  Delete evening": "🗑  Borrar noche",
    "Delete evening": "Borrar noche",
    "%d title(s)": "%d título(s)",
    "Save played titles": "Guardar títulos tocados",
    "CSV files (*.csv);;All files (*)":
        "Archivos CSV (*.csv);;Todos los archivos (*)",
    "Delete the evening of %s with its %d title(s) from the play log?\n"
    "\n"
    "Its daily backups still hold it for 7 days.":
        "¿Borrar del registro la noche del %s con sus %d título(s)?\n"
        "\n"
        "Las copias diarias la conservan aún 7 días.",
    "Playlist popularity re-learned from %s playlists.":
        "Popularidad de listas reaprendida de %s listas.",
    "📜 %s playlists analyzed (M3U files + tournament folders) — popularity and co-occurrence are up to date, so a just-exported tournament counts now.\n"
    "\n"
    "Rows already in the grid keep their old Pop value until regenerated.":
        "📜 %s listas analizadas (archivos M3U + carpetas de torneos) — la popularidad y la coincidencia están al día, así que un torneo recién exportado ya cuenta.\n"
        "\n"
        "Las filas que ya están en la cuadrícula conservan su valor Pop anterior hasta que se vuelvan a sortear.",
    "Re-learn failed:": "Falló el reaprendizaje:",
    "  … and %d more": "  … y %d más",
    "⚠ %d title(s) are not on the Reference path\n"
    "%s\n"
    "and were saved with their own path:":
        "⚠ %d título(s) no están en la ruta de referencia\n"
        "%s\n"
        "y se guardaron con su propia ruta:",
    "💾 Saved %d playlist → %s": "💾 Guardada %d lista → %s",
    "💾 Saved %d playlists → %s": "💾 Guardadas %d listas → %s",
    "Saved %d playlist(s) to:\n"
    "%s":
        "%d lista(s) guardada(s) en:\n"
        "%s",
    "Saved %d wishlist(s) to:\n"
    "%s":
        "%d lista(s) de deseos guardada(s) en:\n"
        "%s",
    "Skipped (empty): %s": "Omitidas (vacías): %s",
    "Errors:": "Errores:",
    "“%s” already exists in the target folder.\n"
    "Replace it, or keep both?":
        "«%s» ya existe en la carpeta de destino.\n"
        "¿Reemplazarla o conservar ambas?",
    "🧳 Bundle: %d playlist folder(s), %d track(s), %s MB → %s":
        "🧳 Paquete: %d carpeta(s) de listas, %d tema(s), %s MB → %s",
    "Bundle written to:\n"
    "%s":
        "Paquete escrito en:\n"
        "%s",
    "%d playlist folder(s) · %d track(s) · %s MB — each folder holds the tracks numbered in play order plus the playlist's M3U, so it plays even without the M3U.":
        "%d carpeta(s) de listas · %d tema(s) · %s MB — cada carpeta contiene los temas numerados en orden de reproducción más el M3U de la lista, así que suena incluso sin el M3U.",
    "⚠ %d track(s) were missing on disk and kept their original absolute path.":
        "⚠ %d tema(s) faltaban en el disco y conservaron su ruta absoluta original.",
    "💾 Saved %d competition playlist → %s":
        "💾 Guardada %d lista de competición → %s",
    "💾 Saved %d competition playlists → %s":
        "💾 Guardadas %d listas de competición → %s",
    "Saved %d competition playlist(s) to:\n"
    "%s":
        "%d lista(s) de competición guardada(s) en:\n"
        "%s",
    "Nothing to save.": "Nada que guardar.",
    "Saved → %s": "Guardado → %s",
    "Saved %d competition playlist(s) → %s":
        "%d lista(s) de competición guardada(s) → %s",
    "Close the tournament-day view? This clears %d day playlist.":
        "¿Cerrar la vista del día de torneo? Esto vacía %d lista del día.",
    "Close the tournament-day view? This clears %d day playlists.":
        "¿Cerrar la vista del día de torneo? Esto vacía %d listas del día.",
    "Clear the %d day playlist?": "¿Vaciar la %d lista del día?",
    "Clear all %d day playlists?": "¿Vaciar las %d listas del día?",
    "Clear the %d playlist on “%s”?": "¿Vaciar la %d lista de «%s»?",
    "Clear all %d playlists on “%s”?": "¿Vaciar las %d listas de «%s»?",
    "🧹 %s playlists cleared.": "🧹 Listas de %s vaciadas.",
    " — %d track(s) of no known dance left out":
        " — %d tema(s) sin baile conocido omitido(s)",
    "🔒 Static mode — a drop now replaces a single slot":
        "🔒 Modo estático — soltar ahora reemplaza un solo hueco",
    "🔓 Dynamic mode — drag songs from the wishlist or another deck to build rounds & heats":
        "🔓 Modo dinámico — arrastra temas desde la lista de deseos u otro deck para montar rondas y grupos",
    "✋ Free order — every row can be dragged anywhere, and a dropped song lands where you drop it":
        "✋ Orden libre — cada fila se puede arrastrar a cualquier sitio, y un tema soltado queda justo donde lo sueltas",
    "%d of these %d tracks say nothing about which dance they are. A grid has no column to put them in, so building one leaves them out of the deck.\n"
    "\n"
    "Build the grid without them?":
        "%d de estos %d temas no dicen qué baile son. Una cuadrícula no tiene columna para ellos, así que al montarla quedan fuera del deck.\n"
        "\n"
        "¿Montar la cuadrícula sin ellos?",
    "🤸 %s panel shown — drop an .m3u here or build one with 🤸 %s.":
        "🤸 Panel %s visible — suelta aquí un .m3u o crea uno con 🤸 %s.",
    "🤸 %s panel hidden": "🤸 Panel %s oculto",
    "📚 Library filtered: %s": "📚 Biblioteca filtrada: %s",
    "all dances": "todos los bailes",
    " · class %s": " · clase %s",
    " · never played": " · nunca tocado",
    "<b>%d</b> of %d checked tracks have at least one issue.":
        "<b>%d</b> de %d temas comprobados tienen al menos un problema.",
    "Plus <b>%d</b> 🧩 round-structure issue — see the yellow box below.":
        "Además <b>%d</b> problema 🧩 de estructura de rondas — ver el recuadro amarillo de abajo.",
    "Plus <b>%d</b> 🧩 round-structure issues — see the yellow box below.":
        "Además <b>%d</b> problemas 🧩 de estructura de rondas — ver el recuadro amarillo de abajo.",
    "%d tracks skipped — no label/dance/length or not audio-analyzed.":
        "%d temas omitidos — sin indicación/baile/duración o sin análisis de audio.",
    "⚡ tempo label vs measured off > %.0f%% (×2, ×3, ×1.5 … slips excused) · 🐢/🐇 takt outside the official TSO range · ⏱ real play ≤ %s":
        "⚡ tempo indicado frente al medido > %.0f%% (se toleran ×2, ×3, ×1,5 …) · 🐢/🐇 compás fuera del rango oficial TSO · ⏱ duración real ≤ %s",
    "⏳ longer than %s": "⏳ más largo que %s",
    "🔇 noise floor above %.0f dB": "🔇 ruido de fondo por encima de %.0f dB",
    "Thresholds: ⚙ Settings → 🎵 Checks.":
        "Umbrales: ⚙ Ajustes → 🎵 Comprobaciones.",
    "⏳  Also flag long tracks (> %s) — only relevant when building a Practice playlist":
        "⏳  Marcar también los temas largos (> %s) — solo importa al crear una lista de práctica",
    "🔇  Also flag hissy tracks (never quieter than %.0f dB) — measures each track once with ffmpeg, so the first run takes a moment":
        "🔇  Marcar también los temas con ruido (nunca por debajo de %.0f dB) — mide cada tema una vez con ffmpeg, así que la primera pasada tarda un poco",
    "🧩 <b>Round structure</b> — click a spot to jump to it":
        "🧩 <b>Estructura de rondas</b> — haz clic en un punto para saltar a él",
    "In playlist: %s": "En la lista: %s",
    "⚠  “%s” is no longer in an open deck.":
        "⚠  «%s» ya no está en ningún deck abierto.",
    "<b>%d</b> of %d checked tracks have an issue.":
        "<b>%d</b> de %d temas comprobados tienen un problema.",
    "%d skipped — not found / not audio-analyzed.":
        "%d omitidos — no encontrados / sin análisis de audio.",
    "⚡ tempo label vs measured · 🐢/🐇 takt outside the TSO range · ⏱ short · ⏳ long · 🔇 hiss · 🧩 round structure (uneven dances, heat taper, heat tempo spread).":
        "⚡ tempo indicado frente al medido · 🐢/🐇 compás fuera del rango TSO · ⏱ corto · ⏳ largo · 🔇 ruido · 🧩 estructura de rondas (bailes desiguales, grupos que menguan, dispersión de tempo por grupo).",
    "🧩 <b>Round structure</b>": "🧩 <b>Estructura de rondas</b>",
    "%d valid · %d unresolved across %d playlist.":
        "%d válidos · %d sin resolver en %d lista.",
    "%d valid · %d unresolved across %d playlists.":
        "%d válidos · %d sin resolver en %d listas.",
    "🔧 %d path line to fix": "🔧 %d línea de ruta por corregir",
    "🔧 %d path lines to fix": "🔧 %d líneas de ruta por corregir",
    "✅ Nothing to fix": "✅ Nada que corregir",
    "🔧 %d track can be moved onto the Reference path":
        "🔧 %d tema se puede mover a la ruta de referencia",
    "🔧 %d tracks can be moved onto the Reference path":
        "🔧 %d temas se pueden mover a la ruta de referencia",
    "%d tracks — <span style='color:#2a7a45;'>%d valid</span> · <b style='color:#e07b00; font-size:13px;'>🔧 %d to fix</b> · <span style='color:#a33;'>%d unresolved</span>":
        "%d temas — <span style='color:#2a7a45;'>%d válidos</span> · <b style='color:#e07b00; font-size:13px;'>🔧 %d por corregir</b> · <span style='color:#a33;'>%d sin resolver</span>",
    "⚠  unresolved (no match under the search folders):":
        "⚠  sin resolver (ninguna coincidencia en las carpetas de búsqueda):",
    "Rewrite %d path line(s) across %d playlist(s) in place?\n"
    "\n"
    "Only the file-path lines change — #EXTINF and every other line stay exactly as-is. This overwrites the .m3u files on disk; each original is kept next to it as <name>.m3u.bak.":
        "¿Reescribir %d línea(s) de ruta en %d lista(s) directamente?\n"
        "\n"
        "Solo cambian las líneas de ruta de archivo — #EXTINF y todas las demás líneas quedan exactamente igual. Esto sobrescribe los archivos .m3u en el disco; cada original se conserva al lado como <name>.m3u.bak.",
    "🧭  Rewrote %d path line(s) in %d playlist(s).":
        "🧭  %d línea(s) de ruta reescrita(s) en %d lista(s).",
    "⚠  Left unchanged:": "⚠  Sin cambios:",
    "… and %d more": "… y %d más",
    "Could not apply snapshot: %s": "No se pudo aplicar la instantánea: %s",
    "Could not restore saved playlist: %s":
        "No se pudo restaurar la lista guardada: %s",
    "⚠  %d saved track(s) not found — is the music drive plugged in?":
        "⚠  %d tema(s) guardado(s) no encontrado(s) — ¿está conectada la unidad de música?",
    "The saved session is kept as %s.":
        "La sesión guardada se conserva como %s.",
    "↩  Restored your in-progress playlist — %d songs (%s, %s)":
        "↩  Tu lista en curso se ha restaurado — %d temas (%s, %s)",
    "↩  Restored your running order — %d tracks":
        "↩  Tu orden de actuación se ha restaurado — %d temas",
    "↩  Restored your themed playlist — %d tracks":
        "↩  Tu lista temática se ha restaurado — %d temas",
    "All %d playlists already hold tracks — there's no free slot to import into.\n"
    "\n"
    "Clear a playlist first, or pick a single file to overwrite the focused deck.":
        "Las %d listas ya contienen temas — no hay ningún hueco libre para importar.\n"
        "\n"
        "Vacía primero una lista o elige un solo archivo para sobrescribir el deck enfocado.",
    "You picked %d files but only %d playlist slot(s) are free.\n"
    "\n"
    "Import the first %d into the free slots and skip the rest?":
        "Has elegido %d archivos, pero solo hay %d hueco(s) de lista libre(s).\n"
        "\n"
        "¿Importar los primeros %d en los huecos libres y omitir el resto?",
    "Importing %s …": "Importando %s …",
    "Import failed: %s": "Falló la importación: %s",
    "Remove %d title from %s?\n"
    "It is already planned in: %s":
        "¿Quitar %d título de %s?\n"
        "Ya está planificado en: %s",
    "Remove %d titles from %s?\n"
    "They are already planned in: %s":
        "¿Quitar %d títulos de %s?\n"
        "Ya están planificados en: %s",
    "Empty %d playlist? This can't be undone.":
        "¿Vaciar %d lista? No se puede deshacer.",
    "Empty %d playlists? This can't be undone.":
        "¿Vaciar %d listas? No se puede deshacer.",
    "↩  Restored your worked playlist for “%s” — %d songs":
        "↩  Tu lista trabajada para «%s» se ha restaurado — %d temas",
    "this competition": "esta competición",
    "⚠  Session not saved — the snapshot failed: %r":
        "⚠  Sesión no guardada — falló la instantánea: %r",
    "Could not write the PDF:\n"
    "%s":
        "No se pudo escribir el PDF:\n"
        "%s",
    "🖨 Playlist saved — %s": "🖨 Lista guardada — %s",
    "Playlist saved as\n"
    "%s\n"
    "\n"
    "Open it now?":
        "Lista guardada como\n"
        "%s\n"
        "\n"
        "¿Abrirla ahora?",
    "Cycle 1 → 2 → 4 → 8 → no playlists (and back).":
        "Alterna 1 → 2 → 4 → 8 → sin listas (y vuelta).",
    "Cycle 1 → 2 → 4 → no playlists (and back).":
        "Alterna 1 → 2 → 4 → sin listas (y vuelta).",
    "Right click walks the cycle backwards.":
        "El clic derecho recorre el ciclo hacia atrás.",
    "8 splits into two tabs of four (Group A–D / Group E–H).":
        "8 se divide en dos pestañas de cuatro (Grupo A–D / Grupo E–H).",
    "No-playlist hides every deck so the Practice / wishlist / library panes take over.":
        "«Sin listas» oculta todos los decks para que los paneles de práctica / lista de deseos / biblioteca ocupen el espacio.",
    "Two or more decks also reveal the wishlist below.":
        "Con dos o más decks también aparece debajo la lista de deseos.",
    "Generate / Save / ↺ / play act on whichever deck has focus.":
        "Generar / Guardar / ↺ / reproducir actúan sobre el deck que tenga el foco.",
    "Show / hide the %s panel.\n"
    "Opens an empty panel — drop an existing .m3u onto it, or build a fresh list with 🤸 %s.":
        "Mostrar / ocultar el panel %s.\n"
        "Abre un panel vacío — suelta en él un .m3u existente o crea una lista nueva con 🤸 %s.",
    "⭐ Swapped %s ⇄ %s": "⭐ Intercambiados %s ⇄ %s",
    "Show only the %d track(s) currently in your wishlist(s),\n"
    "ranked by how well they match this song — pick the best one to add.\n"
    "Matches by song (title / fingerprint), so a different copy still counts.":
        "Muestra solo los %d tema(s) que están ahora en tus listas de deseos,\n"
        "ordenados por lo bien que encajan con este tema — elige el mejor para añadirlo.\n"
        "Se compara por canción (título / huella), así que otra copia también cuenta.",
    "🎼  Chroma cover / remix (melody/harmony, same tune)":
        "🎼  Chroma versión / remix (melodía/armonía, la misma melodía)",
    "🧠  MERT (deep embedding)": "🧠  MERT (embedding profundo)",
    "🎧 Hear and choose — %s": "🎧 Escuchar y elegir — %s",
    "🎧 Hear and choose…": "🎧 Escuchar y elegir…",
    "Now: %s": "Ahora: %s",
    "Now: —": "Ahora: —",
    "Where from": "De dónde",
    "Offered for this slot": "Ofrecido para este hueco",
    "Play / stop this title": "Reproducir / detener este título",
    "▶ or Space plays a title, again stops it, Ctrl+←/→ seeks 30 s, Ctrl+Shift+←/→ plays the title before or after it; a double click or \"Take\" puts it into the slot.":
        "▶ o Espacio reproduce un título, otra vez lo detiene, Ctrl+←/→ salta 30 s, Ctrl+Mayús+←/→ reproduce el título anterior o siguiente; un doble clic o «Tomar» lo pone en el hueco.",
    "Take": "Tomar",
    "⚖️  Combined: timbre + groove + melody (mean)":
        "⚖️  Combinado: timbre + groove + melodía (media)",
    "⚖️  Combined + MERT: timbre + groove + melody + MERT (mean)":
        "⚖️  Combinado + MERT: timbre + groove + melodía + MERT (media)",
    "⚖️ Combined + MERT — the mean of where each title ranks by timbre, groove, melody and MERT.":
        "⚖️ Combinado + MERT — la media de la posición de cada título por timbre, groove, melodía y MERT.",
    "⚖️ Combined — the mean of where each title ranks by timbre, groove and melody.":
        "⚖️ Combinado — la media de la posición de cada título por timbre, groove y melodía.",
    "★  Only rarely played (1–%d playlists)":
        "★  Solo los poco tocados (1–%d listas)",
    "The same three picks as 📚 the library's ★ Plays selector.\n"
    "'Never played': the track is in none of your old playlists.\n"
    "'Rarely played': in 1–%d of them — %d+ is a proven title.\n"
    "'Not since 1 y': it is played, but the newest playlist carrying\n"
    "it is from an earlier year — the year comes from the playlist's\n"
    "path, so lists without a date never count as old.":
        "Los mismos tres filtros que el selector ★ Tocado de la 📚 biblioteca.\n"
        "«Nunca tocado»: el tema no está en ninguna de tus listas antiguas.\n"
        "«Poco tocado»: en 1–%d de ellas — a partir de %d es un título probado.\n"
        "«No desde hace 1 año»: se toca, pero la lista más reciente que lo lleva\n"
        "es de un año anterior — el año sale de la ruta de la lista,\n"
        "así que las listas sin fecha nunca cuentan como antiguas.",
    "%d %s tracks most often played together with this one — ▶ to preview, double-click to open, drag rows into another app":
        "%d temas de %s tocados más a menudo junto con este — ▶ para escuchar, doble clic para abrir, arrastra filas a otra aplicación",
    "%d %s tracks most similar (sound-alike) to this one — ▶ to preview, double-click to open, drag rows into another app":
        "%d temas de %s que más se parecen (suenan igual) a este — ▶ para escuchar, doble clic para abrir, arrastra filas a otra aplicación",
    "⭐ wishlist only": "⭐ solo lista de deseos",
    "📜 played in this round before": "📜 tocado antes en esta ronda",
    "📜  Only titles I played in this round before (%s)":
        "📜  Solo títulos que toqué antes en esta ronda (%s)",
    "Show only titles your past competitions played in this round —\n"
    "any heat of it, from lists of a class and age category that fit\n"
    "this deck (the same history as 📜 Find planned before).\n"
    "Still ranked by how much they sound like this one.":
        "Muestra solo títulos que tus competiciones anteriores tocaron en esta ronda —\n"
        "en cualquier grupo, de listas de una clase y categoría de edad que encajen\n"
        "con este deck (el mismo historial que 📜 Buscar planificados antes).\n"
        "Siguen ordenados por lo mucho que suenan como este.",
    "🎙 instrumental only (%d vocal hidden)":
        "🎙 solo instrumental (%d con voz ocultos)",
    "%s (%d hidden)": "%s (%d ocultos)",
    "%d duplicate hidden": "%d duplicado oculto",
    "%d duplicates hidden": "%d duplicados ocultos",
    "%d track(s) you planned for this dance &amp; round in past competitions — best competition match first (see Class) — ▶ to preview, drag a row onto the slot, double-click to open":
        "%d tema(s) que planificaste para este baile &amp; ronda en competiciones anteriores — mejor coincidencia de competición primero (ver Clase) — ▶ para escuchar, arrastra una fila al hueco, doble clic para abrir",
    "Similar to: %s": "Similar a: %s",
    "📋 Learned from your playlists — %d often played together.":
        "📋 Aprendido de tus listas — %d tocados a menudo juntos.",
    "🧠  Rebuild %s index…": "🧠  Reconstruir el índice %s…",
    "%s vectors for these %d tracks haven't been built yet.\n"
    "\n"
    "Building analyses each track once (slow the first time, then cached).\n"
    "Build now?":
        "Los vectores %s de estos %d temas aún no se han creado.\n"
        "\n"
        "Crearlos analiza cada tema una vez (lento la primera vez, luego en caché).\n"
        "¿Crearlos ahora?",
    "Building %s embedding index…": "Creando el índice de embeddings %s…",
    "All %d file(s) failed to embed.\n"
    "\n"
    "First error:\n"
    "%s\n"
    "\n"
    "Common causes: the neural model couldn't load, or the deps are mismatched. See the console log for the full traceback.":
        "Falló la incrustación de los %d archivo(s).\n"
        "\n"
        "Primer error:\n"
        "%s\n"
        "\n"
        "Causas habituales: el modelo neuronal no se pudo cargar o las dependencias no encajan. El registro de la consola muestra la traza completa.",
    "🧠 %s index ready (%d embedded, %d failed).":
        "🧠 Índice %s listo (%d incrustados, %d fallidos).",
    "🧠 %s index ready (%d embedded).": "🧠 Índice %s listo (%d incrustados).",
    "%s indexing cancelled — showing librosa results.":
        "Indexación %s cancelada — se muestran los resultados de librosa.",
    "Ranking by %s embedding…": "Ordenando por embedding %s…",
    "No %s matches yet — try building the index over more tracks.":
        "Aún no hay coincidencias %s — prueba a crear el índice sobre más temas.",
    "🧠 %s — %d deep-embedding matches.":
        "🧠 %s — %d coincidencias por embedding profundo.",
    "Refreshed — %d similar to %s": "Actualizado — %d similares a %s",
    "%s / %s  (%s left)": "%s / %s  (quedan %s)",
    "~%s remaining": "quedan ~%s",
    "Listing files…": "Listando archivos…",
    "⬇ Downloading the MERT model (once) — MB":
        "⬇ Descargando el modelo MERT (una sola vez) — MB",
    "This is not an audio file, so it won't be opened:\n"
    "%s":
        "Esto no es un archivo de audio, así que no se abrirá:\n"
        "%s",
    "File not found:\n"
    "%s":
        "Archivo no encontrado:\n"
        "%s",
    "Couldn't open the file:\n"
    "%s":
        "No se pudo abrir el archivo:\n"
        "%s",
    "Folder not found:\n"
    "%s":
        "Carpeta no encontrada:\n"
        "%s",
    "Couldn't open the folder:\n"
    "%s":
        "No se pudo abrir la carpeta:\n"
        "%s",
    "Couldn't reveal the file:\n"
    "%s":
        "No se pudo mostrar el archivo:\n"
        "%s",
    "✅  No duplicates among the %d file added.":
        "✅  Ningún duplicado en el %d archivo añadido.",
    "✅  No duplicates among the %d files added.":
        "✅  Ningún duplicado entre los %d archivos añadidos.",
    "Comparison failed:\n"
    "%s":
        "Falló la comparación:\n"
        "%s",
    "✅  %d hard duplicate(s) to remove, %d unused track(s) to export (of %d; %d Paso Doble kept). Review below, then export.":
        "✅  %d duplicado(s) exacto(s) por quitar, %d tema(s) sin usar por exportar (de %d; %d Paso Doble conservados). Revisa abajo y luego exporta.",
    "Could not write file:\n"
    "%s":
        "No se pudo escribir el archivo:\n"
        "%s",
    "The reference playlist itself was overwritten with the cleaned list.":
        "La propia lista de referencia se sobrescribió con la lista limpia.",
    "The reference playlist was left unchanged.":
        "La lista de referencia quedó sin cambios.",
    "📤  Exported %d track(s) (sorted by dance) → %s":
        "📤  %d tema(s) exportado(s) (ordenados por baile) → %s",
    "📤  Exported %d track(s) → %s": "📤  %d tema(s) exportado(s) → %s",
    "Exported %d unused track(s) to:\n"
    "%s\n"
    "\n"
    "%d hard duplicate(s) removed. %s":
        "%d tema(s) sin usar exportado(s) a:\n"
        "%s\n"
        "\n"
        "%d duplicado(s) exacto(s) quitado(s). %s",
    "🔁  Replace in %s": "🔁  Reemplazar en %s",
    "This song is in %d open playlists. Replacing it on one\n"
    "row leaves the other copies — pick a copy on each of its rows to\n"
    "replace them all (the choices are merged when you press Apply).":
        "Este tema está en %d listas abiertas. Reemplazarlo en una\n"
        "fila deja las otras copias — elige una copia en cada una de sus filas para\n"
        "reemplazarlas todas (las elecciones se combinan al pulsar Aplicar).",
    "%d occurrence(s) are set to Replace but have no replacement track yet.\n"
    "Pick a track for each, or switch them back to Keep.":
        "%d aparición(es) están en Reemplazar pero aún no tienen tema de reemplazo.\n"
        "Elige un tema para cada una o vuelve a ponerlas en Conservar.",
    "%d copy/copies are set to two different changes on different rows.\n"
    "Choose the same on each, or set one back to Keep all.":
        "%d copia(s) tienen dos cambios distintos en filas diferentes.\n"
        "Elige lo mismo en cada una o vuelve a poner una en Conservar todo.",
    "🗑  Remove from %s": "🗑  Quitar de %s",
    "🗑  Removed %d duplicate": "🗑  %d duplicado quitado",
    "🗑  Removed %d duplicates": "🗑  %d duplicados quitados",
    "A track named “%s” is already in this playlist,\n"
    "but it’s a different file.":
        "Un tema llamado «%s» ya está en esta lista,\n"
        "pero es otro archivo.",
    "“%s” is already in this playlist —\n"
    "“%s” looks like the same title in another file.":
        "«%s» ya está en esta lista —\n"
        "«%s» parece el mismo título en otro archivo.",
    "“%s” is already in this playlist.\n"
    "\n"
    "Remove it from the wishlist anyway?":
        "«%s» ya está en esta lista.\n"
        "\n"
        "¿Quitarlo de la lista de deseos de todos modos?",
    "“%s” is already in this playlist.\n"
    "\n"
    "Remove it from the playlist anyway?":
        "«%s» ya está en esta lista.\n"
        "\n"
        "¿Quitarlo de la lista de todos modos?",
    "%d dragged track(s) are already in this playlist.\n"
    "\n"
    "Remove them from the wishlist anyway?":
        "%d tema(s) arrastrado(s) ya están en esta lista.\n"
        "\n"
        "¿Quitarlos de la lista de deseos de todos modos?",
    "%d dragged track(s) are already in this playlist.\n"
    "\n"
    "Remove them from the playlist anyway?":
        "%d tema(s) arrastrado(s) ya están en esta lista.\n"
        "\n"
        "¿Quitarlos de la lista de todos modos?",
    "“%s” looks like a %s track, but this slot is %s.\n"
    "\n"
    "Replace anyway?":
        "«%s» parece un tema de %s, pero este hueco es %s.\n"
        "\n"
        "¿Reemplazar de todos modos?",
    "Remove this whole heat (all dances) from %s?":
        "¿Quitar este grupo entero (todos los bailes) de %s?",
    "⬆  %d song(s) moved up into empty slots":
        "⬆  %d tema(s) subido(s) a huecos libres",
    "Remove the entire round “%s” and all %d of its heats?":
        "¿Quitar la ronda entera «%s» con sus %d grupos?",
    "Remove %s from %s?\n"
    "%d song(s) in this round will be cleared.":
        "¿Quitar %s de %s?\n"
        "Se vaciarán %d tema(s) de esta ronda.",
    "Hide the empty %s from %s?": "¿Ocultar %s (vacío) en %s?",
    "Remove %s from all rounds and heats?\n"
    "%d song(s) across the playlist will be cleared.":
        "¿Quitar %s de todas las rondas y grupos?\n"
        "Se vaciarán %d tema(s) en toda la lista.",
    "Hide the empty %s from all rounds?":
        "¿Ocultar %s (vacío) en todas las rondas?",
    "%d dropped track(s) look like %s dances, but this is a %s list.\n"
    "\n"
    "Add them anyway?":
        "%d tema(s) soltado(s) parecen bailes de %s, pero esta es una lista de %s.\n"
        "\n"
        "¿Añadirlos de todos modos?",
    "All open playlists (%d deck)": "Todas las listas abiertas (%d deck)",
    "All open playlists (%d decks)": "Todas las listas abiertas (%d decks)",
    "%d file added.": "%d archivo añadido.",
    "%d files added.": "%d archivos añadidos.",
    "📅 Tournament day only (%d playlist)":
        "📅 Solo el día de torneo (%d lista)",
    "📅 Tournament day only (%d playlists)":
        "📅 Solo el día de torneo (%d listas)",
    "Dance: %s": "Baile: %s",
    "%s (%d beats/bar)": "%s (%d tiempos/compás)",
    "'%s' is not a valid round pattern for %s %s — use heat counts like 6-3-2-1.":
        "«%s» no es un patrón de rondas válido para %s %s — usa números de grupos como 6-3-2-1.",
    "Red: the pool can't carry a competition (pool < %d or proven < %d — a 6-3-2-1 needs 12 per dance).  Orange: < 80 %% of the takt-labelled tracks are tournament tempo, or over half the pool is stale (no dateable playlist in ≥ 3 years; 'never played' always counts as stale).  Double-click a row to browse its never-played tracks in 📚 the library.":
        "Rojo: el repertorio no da para una competición (repertorio < %d o probados < %d — un 6-3-2-1 necesita 12 por baile).  Naranja: < 80 %% de los temas con compás indicado tienen tempo de torneo, o más de la mitad del repertorio está anticuado (ninguna lista fechable en ≥ 3 años; «nunca tocado» siempre cuenta como anticuado).  Doble clic en una fila para ver sus temas nunca tocados en 📚 la biblioteca.",
    "⚠️ %d gap(s) found": "⚠️ %d hueco(s) encontrado(s)",
    "(%d playlist)": "(%d lista)",
    "(%d playlists)": "(%d listas)",
    "%d song": "%d tema",
    "%d songs": "%d temas",
    "The playlist file is gone:\n"
    "\n"
    "%s":
        "El archivo de la lista ya no existe:\n"
        "\n"
        "%s",
    "No .m3u playlists found under “%s”.":
        "No se encontraron listas .m3u en «%s».",
    "Remove “%s” from the tree?\n"
    "\n"
    "%d playlist file(s) are listed under it — they stay on disk, only this entry goes.":
        "¿Quitar «%s» del árbol?\n"
        "\n"
        "Debajo hay %d archivo(s) de lista — se quedan en el disco, solo desaparece esta entrada.",
    "Remove %d entries from the tree?\n"
    "\n"
    "%d playlist file(s) are listed under them — they stay on disk, only these entries go.":
        "¿Quitar %d entradas del árbol?\n"
        "\n"
        "Debajo hay %d archivo(s) de lista — se quedan en el disco, solo desaparecen estas entradas.",
    "%s and %s are different dances.\n"
    "\n"
    "Only titles of the same dance can swap places, so every round keeps its dances.":
        "%s y %s son bailes distintos.\n"
        "\n"
        "Solo los títulos del mismo baile pueden intercambiar sitio, para que cada ronda conserve sus bailes.",
    "No past competition plans found for %s in %s.":
        "No se encontraron planificaciones de competiciones anteriores para %s en %s.",
    "Remove all %d track(s) from wishlist%s?":
        "¿Quitar los %d tema(s) de la lista de deseos%s?",
    "Remove the entire playlist%s? The table will be blank again.":
        "¿Quitar la lista entera%s? La tabla quedará vacía de nuevo.",
    "Couldn't read as an audio track:": "No se pudo leer como tema de audio:",
    "This list": "Esta lista",
    "%s holds %d title twice — the same audio, e.g. a copy of the file on another drive:\n"
    "\n"
    "%s\n"
    "\n"
    "Remove the earlier copy? The last one stays.":
        "%s contiene %d título dos veces — el mismo audio, p. ej. una copia del archivo en otra unidad:\n"
        "\n"
        "%s\n"
        "\n"
        "¿Quitar la copia anterior? La última se queda.",
    "%s holds %d titles twice — the same audio, e.g. a copy of the file on another drive:\n"
    "\n"
    "%s\n"
    "\n"
    "Remove the earlier copies? The last one stays.":
        "%s contiene %d títulos dos veces — el mismo audio, p. ej. una copia del archivo en otra unidad:\n"
        "\n"
        "%s\n"
        "\n"
        "¿Quitar las copias anteriores? La última se queda.",
    "Any OpenAI-compatible /chat/completions host.":
        "Cualquier host /chat/completions compatible con OpenAI.",
    "%d models loaded.": "%d modelos cargados.",
    "%d suggestions — %d in your library.":
        "%d sugerencias — %d en tu biblioteca.",
    "▾  %d more lines": "▾  %d líneas más",
    "thinking…": "pensando…",
    "Couldn't read “%s” as an audio track.":
        "No se pudo leer «%s» como tema de audio.",
    "“%s” holds %d tracks (subfolders included).\n"
    "\n"
    "Reading them all takes a moment — every file's tags are read on the way in.\n"
    "\n"
    "Add them?":
        "«%s» contiene %d temas (subcarpetas incluidas).\n"
        "\n"
        "Leerlos todos tarda un momento — al entrar se leen las etiquetas de cada archivo.\n"
        "\n"
        "¿Añadirlos?",
    "↩ Left at %s — starts there again":
        "↩ Dejado en %s — vuelve a empezar ahí",
    "Plays %s — the stillness at the edges of the file is skipped":
        "Reproduce %s — se omite el silencio en los bordes del archivo",
    "Shorter than the configured play length (%s)":
        "Más corto que la duración de reproducción configurada (%s)",
    "%s already holds %d track(s).\n"
    "\n"
    "Importing %s REPLACES them — the list is loaded fresh from the file, the tracks in it now are dropped.\n"
    "\n"
    "Import anyway?":
        "%s ya contiene %d tema(s).\n"
        "\n"
        "Importar %s los REEMPLAZA — la lista se carga de nuevo desde el archivo y los temas que tiene ahora desaparecen.\n"
        "\n"
        "¿Importar de todos modos?",
    "“%s” is already used in this playlist.": "«%s» ya se usa en esta lista.",
    "A %s track can only move into another %s slot — not a %s slot.":
        "Un tema de %s solo puede moverse a otro hueco de %s — no a un hueco de %s.",
    "Dances (%d): %s": "Bailes (%d): %s",
    "Order: %s, %s, …": "Orden: %s, %s, …",
    "🟰  Identical files — the earlier copy is removed, the last stays (%d)":
        "🟰  Archivos idénticos — se quita la copia anterior, la última se queda (%d)",
    "✏  %d pads selected — what you change here (colour, volume, fade, 🔁, 🔈, 🎶, S) applies to all of them.\n"
    "Label and shortcut stay with this pad.":
        "✏  %d pads seleccionados — lo que cambies aquí (color, volumen, fundido, 🔁, 🔈, 🎶, S) se aplica a todos.\n"
        "La etiqueta y el atajo se quedan con este pad.",
    "Empty = this slot's default (%s)":
        "Vacío = valor predeterminado de este slot (%s)",
    "Empty = no key (this slot has no default)":
        "Vacío = sin tecla (este slot no tiene valor predeterminado)",
    "cut": "corte seco",
    "%s (wall)": "%s (Cartwall)",
    "⚠ already used by %s": "⚠ ya usado por %s",
    "%d key claimed twice — the marked ones will not fire. Pad keys win over slot keys.":
        "%d tecla asignada dos veces — las marcadas no se dispararán. Las teclas de pad tienen prioridad sobre las de slot.",
    "%d keys claimed twice — the marked ones will not fire. Pad keys win over slot keys.":
        "%d teclas asignadas dos veces — las marcadas no se dispararán. Las teclas de pad tienen prioridad sobre las de slot.",
    "Page %d": "Página %d",
    "page %d": "página %d",
    "%d pads need %d pages at %d × %d; the wall keeps at most %d.\n"
    "Clear some pads or pick a bigger layout.":
        "%d pads necesitan %d páginas en %d × %d; la Cartwall admite como máximo %d.\n"
        "Vacía algunos pads o elige una cuadrícula mayor.",
    "Remove %s and the %d pads on it?\n"
    "The sample files are left alone — only the pads go.":
        "¿Quitar %s y los %d pads que contiene?\n"
        "Los archivos de muestra no se tocan — solo se van los pads.",
    "%d pads do not fit one %d × %d page.\n"
    "Pick a bigger layout first.":
        "%d pads no caben en una página de %d × %d.\n"
        "Elige primero una cuadrícula mayor.",
    "Could not write the wall:\n"
    "%s":
        "No se pudo escribir la Cartwall:\n"
        "%s",
    "%d pads written to\n"
    "%s\n"
    "\n"
    "The sample files themselves are not copied — the wall stores their paths.":
        "%d pads escritos en\n"
        "%s\n"
        "\n"
        "Los archivos de muestra no se copian — la Cartwall guarda sus rutas.",
    "Replace the current wall with %d pads from\n"
    "%s?":
        "¿Reemplazar la Cartwall actual por %d pads de\n"
        "%s?",
    "The wall is full: %d of %d tracks were placed.\n"
    "Clear some pads or pick a bigger layout for the rest.":
        "La Cartwall está llena: se colocaron %d de %d temas.\n"
        "Vacía algunos pads o elige una cuadrícula mayor para el resto.",
    "🔇 Only stillness left from %s — song ended.":
        "🔇 Solo silencio a partir de %s — tema terminado.",
    "🔇 Skipped %ss of leading silence.":
        "🔇 Omitidos %s s de silencio inicial.",
    "⚠️ Sample not found: %s": "⚠️ Muestra no encontrada: %s",
    "⏱ Auto-advance pause extended by %ss.":
        "⏱ Pausa de avance automático alargada %s s.",
    "⏸ Auto-advance…  🎵 %s": "⏸ Avance automático…  🎵 %s",
    "🎯 Highlight at %s — %d mark(s). ✔ Done editing arms the stop.":
        "🎯 Momento culminante en %s — %d marca(s). ✔ Terminar edición activa la parada.",
    "🎯 PD highlight %d marked at %s (stop set to #%s)":
        "🎯 Momento culminante PD %d marcado en %s (parada en #%s)",
    "🏁  %s finished": "🏁  %s terminado",
    "🏁 %s finished — auto-advance stopped.":
        "🏁 %s terminado — avance automático detenido.",
    "Can't cue — file not found: %s":
        "No se puede preparar — archivo no encontrado: %s",
    "⏸ Cued %s — press ⏯ to play. — ⏭ walks the playlist":
        "⏸ %s preparado — pulsa ⏯ para reproducir. — ⏭ recorre la lista",
    "⏸ Cued %s — press ⏯ to play.":
        "⏸ %s preparado — pulsa ⏯ para reproducir.",
    "the %s %s of this round": "el %s %s de esta ronda",
    "this %s": "este %s",
    "🎚 TSO tempo: %s %s → T%s (target T%s from %s)":
        "🎚 Tempo TSO: %s %s → T%s (objetivo T%s de %s)",
    "⏸  cued: %s": "⏸  preparado: %s",
    "↩ Picked up at %s.": "↩ Retomado en %s.",
    "⏸  editing: %s": "⏸  editando: %s",
    "⏸  editing": "⏸  editando",
    "Play length per song: each song is stopped after this time,\n"
    "ramping down over the fade time first. Steps of %s s\n"
    "up to %s; one step further is\n"
    "'full' — no cut, every title plays to its own end.\n"
    "\n"
    "Double-click to type an exact length (e.g. 1:37).":
        "Duración por tema: cada tema se detiene tras este tiempo,\n"
        "bajando antes durante el tiempo de fundido. Pasos de %s s\n"
        "hasta %s; un paso más es\n"
        "«completo» — sin corte, cada título suena hasta su final.\n"
        "\n"
        "Doble clic para escribir una duración exacta (p. ej. 1:37).",
    "Delete the highlight at %s s": "Borrar el momento culminante en %s s",
    "Compensate loudness differences between tracks on playback:\n"
    "each song's measured EBU R128 loudness is pulled towards a\n"
    "common target, so quiet old recordings and loud modern\n"
    "masters play at a similar level.":
        "Compensa al reproducir las diferencias de sonoridad entre temas:\n"
        "la sonoridad EBU R128 medida de cada tema se lleva hacia un\n"
        "objetivo común, para que las grabaciones antiguas flojas y los\n"
        "másteres modernos fuertes suenen a un nivel parecido.",
    "ℹ No loudness measured yet — tracks play at their\n"
    "original volume. Run 📊 Analyze loudness (⚙ Settings)\n"
    "to equalize them.":
        "ℹ Aún no se ha medido la sonoridad — los temas suenan a su\n"
        "volumen original. Ejecuta 📊 Analizar sonoridad (⚙ Ajustes)\n"
        "para igualarlos.",
    "ℹ %d open-playlist track not measured yet — it plays at original volume.\n"
    "Run 📊 Analyze loudness (⚙ Settings) to equalize it too.":
        "ℹ %d tema de las listas abiertas aún no está medido — suena a volumen original.\n"
        "Ejecuta 📊 Analizar sonoridad (⚙ Ajustes) para igualarlo también.",
    "ℹ %d open-playlist tracks not measured yet — they play at original volume.\n"
    "Run 📊 Analyze loudness (⚙ Settings) to equalize them too.":
        "ℹ %d temas de las listas abiertas aún no están medidos — suenan a volumen original.\n"
        "Ejecuta 📊 Analizar sonoridad (⚙ Ajustes) para igualarlos también.",
    "⚡ Tempo: measured ~%s vs label %s bpm (off %s%%)":
        "⚡ Tempo: medido ~%s frente a %s bpm indicado (desvío %s%%)",
    "label": "indicado",
    "measured": "medido",
    "🐢 Too slow: T%s (%s), TSO %s-%s":
        "🐢 Demasiado lento: T%s (%s), TSO %s-%s",
    "🐇 Too fast: T%s (%s), TSO %s-%s":
        "🐇 Demasiado rápido: T%s (%s), TSO %s-%s",
    "⏱ Short: real play %s — %s file minus %ss silence (≤ %s)":
        "⏱ Corto: duración real %s — archivo de %s menos %s s de silencio (≤ %s)",
    "⏱ Short: %s (≤ %s play length)": "⏱ Corto: %s (≤ %s de duración)",
    "⏳ Long: %s (> %s)": "⏳ Largo: %s (> %s)",
    "🔇 Hiss: never quieter than %s dB (> %s dB)":
        "🔇 Ruido: nunca por debajo de %s dB (> %s dB)",
    "“%s”: uneven dance counts — ": "«%s»: número de bailes desigual — ",
    "%s %d/%d (missing in heat ": "%s %d/%d (falta en el grupo ",
    "“%s”": "«%s»",
    " has %d heats, expected 1.": " tiene %d grupos, se esperaba 1.",
    " has %d heats, expected 2.": " tiene %d grupos, se esperaban 2.",
    "“%s”: %s heats differ by %d takte (allowed: 1) — ":
        "«%s»: los grupos de %s difieren en %d compases (permitido: 1) — ",
    "heat %d: T%s “%s”": "grupo %d: T%s «%s»",
    "“%s” — %s": "«%s» — %s",
    "🧩 “%s” %s heats differ by %d takte (allowed: 1)":
        "🧩 «%s»: los grupos de %s difieren en %d compases (permitido: 1)",
    "title": "título",
    "dance": "baile",
    "takt": "compás",
    "year": "año",
    "genre": "género",
    "classes": "clases",
    "christmas": "Navidad",
    "ID3 title": "título ID3",
    "artist": "intérprete",
    "length": "duración",
    "album": "álbum",
    "markers": "marcas",
    "⚠ %s: only %d proven song(s) — finals need %d; expect fresh fill-ins.":
        "⚠ %s: solo %d tema(s) probado(s) — las finales necesitan %d; cuenta con relleno nuevo.",
    "♪ %s: no track near the ideal %s bpm.":
        "♪ %s: ningún tema cerca del tempo ideal de %s bpm.",
    "✦ %d/%d songs are fresh (%d%% new).":
        "✦ %d/%d temas son nuevos (%d%% nuevos).",
    "⚠ %s could not fill %d of %d slots (%s) — park more tracks there or switch the source back to the Favorites library.":
        "⚠ %s no pudo llenar %d de %d huecos (%s) — aparca más temas ahí o vuelve a poner como fuente la biblioteca de favoritos.",
    "⭐ the open wishlists": "⭐ las listas de deseos abiertas",
    "📅 Day plan: %d competition(s) generated — %d songs locked for the day (Paso Doble may repeat)":
        "📅 Plan del día: %d competición(es) generada(s) — %d temas bloqueados para el día (el Paso Doble puede repetirse)",
    "🕑 Seeded from %d past “%s” list(s) — round pool sizes: %s":
        "🕑 Sembrado a partir de %d lista(s) anterior(es) de «%s» — tamaño del repertorio por ronda: %s",
    "⚠️ No past “%s” lists found — used the whole favorites library instead":
        "⚠️ No se encontraron listas anteriores de «%s» — se usó en su lugar toda la biblioteca de favoritos",
    "🎯 %s: %d tracks  (%s)": "🎯 %s: %d temas  (%s)",
    "↺ swaps with a title from the end, drag-drop replaces":
        "↺ intercambia con un título del final, arrastrar y soltar reemplaza",
    "↺ / drag-drop to replace by timbre":
        "↺ / arrastrar y soltar reemplaza por timbre",
    "🤸 %s: %d tracks  (%s)  — %s": "🤸 %s: %d temas  (%s)  — %s",
    "📂 Importing %s…": "📂 Importando %s…",
    "%d tracks are on the table, %d of them already in an open deck.":
        "Hay %d temas para elegir, %d de ellos ya en un deck abierto.",
    "%d tracks are on the table.": "Hay %d temas para elegir.",
    "💾 Saving %s…": "💾 Guardando %s…",
    "➕  Adding %s tracks…": "➕  Añadiendo %s temas…",
    "🐂  Paso Doble in %d s": "🐂  Paso Doble en %d s",
    "⏸  %d s  (paused)": "⏸  %d s  (en pausa)",
    "⚠ Could not play: %s": "⚠ No se pudo reproducir: %s",
    "⚠ Playback failed: %s": "⚠ Falló la reproducción: %s",
    "unknown error": "error desconocido",
    "did not start": "no arrancó",
    "⚠ “%s” would not play — skipped to the next title.":
        "⚠ «%s» no se pudo reproducir — se pasó al siguiente título.",
    "🔇 would not play: %s": "🔇 no se pudo reproducir: %s",
    "▴  fold back": "▴  plegar de nuevo",
    "⏹  Stop": "⏹  Detener",
    "Stop the run. A model that is still thinking is cut off and nothing is changed.":
        "Detener la ejecución. Un modelo que aún está pensando se interrumpe y no se cambia nada.",
    "Waiting for the model…": "Esperando al modelo…",
    "Working…": "Trabajando…",
    "Stopping…": "Deteniendo…",
    "Check cancelled — drop or ➕ add files to run it again.":
        "Comprobación cancelada — suelta archivos o añádelos con ➕ para ejecutarla de nuevo.",
    "🧳  Export": "🧳  Exportar",
    "✅ No gaps — every dance × class pool is healthy":
        "✅ Sin huecos — cada repertorio de baile × clase está bien surtido",
    "Unfold the library pane": "Desplegar el panel de la biblioteca",
    "📚 Library browser shown": "📚 Explorador de la biblioteca visible",
    "📚 Library browser hidden": "📚 Explorador de la biblioteca oculto",
    "💾 Saving all playlists…": "💾 Guardando todas las listas…",
    "🧳 Exporting venue bundle…": "🧳 Exportando el paquete del local…",
    "💾 Saving tournament-day playlists…":
        "💾 Guardando las listas del día de torneo…",
    "This list is empty.": "Esta lista está vacía.",
    "This wishlist is empty.": "Esta lista de deseos está vacía.",
    "💾 Saving playlist…": "💾 Guardando la lista…",
    "💾 Saving wishlist…": "💾 Guardando la lista de deseos…",
    "▴ All playlists folded to tabs — click a tab to open one":
        "▴ Todas las listas plegadas en pestañas — haz clic en una pestaña para abrirla",
    "▾ All playlists unfolded": "▾ Todas las listas desplegadas",
    "Open the library pane back up":
        "Volver a abrir el panel de la biblioteca",
    "Collapse the whole pane —\n"
    "📚 Library and 🏆 Tournaments together":
        "Plegar todo el panel —\n"
        "📚 Biblioteca y 🏆 Torneos juntos",
    "📚 Library pane collapsed — the arrow in the tab bar opens it":
        "📚 Panel de la biblioteca plegado — la flecha de la barra de pestañas lo abre",
    "📚 Library pane open": "📚 Panel de la biblioteca abierto",
    "It failed": "Ha fallado",
    "Stopped — nothing was changed.": "Detenido — no se cambió nada.",
    "AI playlist stopped.": "Lista IA detenida.",
    "Why these tracks": "Por qué estos temas",
    "📅 Planning tournament day…": "📅 Planificando el día de torneo…",
    "Playlist not read": "Lista no leída",
    "🎵 Checking music…": "🎵 Comprobando la música…",
    "✅  No tempo / length issues in the current tracks.":
        "✅  Sin problemas de tempo / duración en los temas actuales.",
    "No tracks in any open playlist — drag playlists into the 📂 tab to check loose files.":
        "No hay temas en ninguna lista abierta — arrastra listas a la pestaña 📂 para comprobar archivos sueltos.",
    "Method <span style='color:#b00'>(not used in playlist mode)</span>:":
        "Método <span style='color:#b00'>(no se usa en el modo lista)</span>:",
    "📁 Reading the dropped folder…": "📁 Leyendo la carpeta soltada…",
    "Drop one or more audio files here, or click to browse":
        "Suelta aquí uno o varios archivos de audio, o haz clic para buscar",
    "Empty — switch ✏ Edit on to fill it":
        "Vacío — activa ✏ Editar para llenarlo",
    "Editing ON — drop, drag, recolour and reshape the wall.\n"
    "Switch off before the tournament so nothing moves by accident.":
        "Edición ACTIVADA — suelta, arrastra, cambia colores y remodela la pared.\n"
        "Desactívala antes del torneo para que nada se mueva por accidente.",
    "Locked: pads only fire. Click to edit the wall.":
        "Bloqueada: los pads solo se disparan. Haz clic para editar la pared.",
    "🎛 Cartwall shown": "🎛 Cartwall visible",
    "🎛 Cartwall hidden": "🎛 Cartwall oculta",
    "✏️ Editing highlights — playback paused; scrub to a crash, ⏯ to listen, 🎯 sets a mark at the playhead.":
        "✏️ Editando momentos culminantes — reproducción en pausa; desplázate hasta un golpe, ⏯ para escuchar, 🎯 pone una marca en la posición actual.",
    "✔ Highlights armed — playback pauses at the stop once so you can check it.":
        "✔ Momentos culminantes activados — la reproducción se detiene una vez en la parada para que la compruebes.",
    "🖥 The presenter's screen was disconnected — it opens again when the screen is back.":
        "🖥 Se desconectó la pantalla del presentador — se vuelve a abrir cuando la pantalla vuelve.",
    "⏹ The next title was removed during the pause — nothing was started.":
        "⏹ El siguiente título se quitó durante la pausa — no se inició nada.",
    "✔  Done editing": "✔  Terminar edición",
    "No pause to jump to — tick 'Pause between songs' (and ⏭\n"
    "auto-advance) in the Playing-mode panel first.":
        "No hay pausa a la que saltar — marca primero «Pausa entre temas» (y ⏭\n"
        "avance automático) en el panel del modo reproducción.",
    "duck": "atenuar",
    "instrumental (🎙️ Demucs-measured)": "instrumental (🎙️ medido con Demucs)",
    "instrumental (🎙️ audio-detected)":
        "instrumental (🎙️ detectado en el audio)",
    "🎄 Christmas": "🎄 Navidad",
    "Similarity": "Similitud",
    "Match": "Coincidencia",
    "Played together": "Tocados juntos",
    "Classes: %s": "Clases: %s",
    "In these matching past lists:":
        "En estas listas anteriores que coinciden:",
    "… +%d more": "… +%d más",
    "In %d of your playlists": "En %d de tus listas",
    "Played in: %s": "Tocado en: %s",
    "▶ This list is playing: this switch decides what follows the title.":
        "▶ Esta lista está sonando: este interruptor decide qué sigue al título.",
    "in the archive since %s": "en el archivo desde %s",
    "%s, sounds like %s (%d%%)": "%s, suena como %s (%d%%)",
    "%s, sounds like %s (%s)": "%s, suena como %s (%s)",
    "sounds like '%s' of the first heat (%s)":
        "suena como «%s» del primer grupo (%s)",
    "sounds like '%s' of the first heat": "suena como «%s» del primer grupo",
    "melody top %d %%": "melodía top %d %%",
    "played %d× at the class": "tocado %d× en la clase",
    "never played at the class": "nunca tocado en la clase",
    "a version of %s, played %d× at the class":
        "una versión de %s — el original sonó %d× en la clase",
    "a version of %s, never played at the class":
        "una versión de %s — el original nunca sonó en la clase",
    "Titles to choose from": "Títulos para elegir",
    "%d from this event's past years, %d from other events' lists of the class, %d new in the archive, %d rarely played at the class (new ones included)":
        "%d de años anteriores de este evento, %d de listas de la clase en otros eventos, %d nuevos en el archivo, %d poco tocados en la clase (nuevos incluidos)",
    "🏆  Event — a whole day of competitions, planned from its history":
        "🏆  Evento — un día entero de competiciones, planificado a partir de su historia",
    "Paste the event's schedule. Every competition gets up to three\n"
    "variants, drawn from the event's earlier editions, the class's\n"
    "lists at other events and titles that sound like those.":
        "Pega el horario del evento. Cada competición recibe hasta tres\n"
        "variantes, sacadas de ediciones anteriores del evento, de las listas\n"
        "de la clase en otros eventos y de títulos que suenan parecido.",
    "Paste the event's schedule, one competition per line:\n"
    "\n"
    "Sa: 10:00 HGR S STD 3-2-1\n"
    "So: 14:00 SEN I S STD (24) 2-1\n"
    "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6":
        "Pega el horario del evento, una competición por línea:\n"
        "\n"
        "Sa: 10:00 HGR S STD 3-2-1\n"
        "So: 14:00 SEN I S STD (24) 2-1\n"
        "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6",
    "Competition": "Competición",
    "Dances": "Bailes",
    "Heats per round": "Grupos por ronda",
    "What was read from the schedule. Double-click a cell to correct\n"
    "it — the class (S, A … D), the dance codes, the heats per round.":
        "Lo que se leyó del horario. Doble clic en una celda para corregirla\n"
        "— la clase (S, A … D), los códigos de baile, los grupos por ronda.",
    "Event:": "Evento:",
    "%d editions": "%d ediciones",
    "The event whose earlier editions are its history — the folders\n"
    "of that name in the playlist folder, whatever the year.":
        "El evento cuyas ediciones anteriores son su historia — las carpetas\n"
        "con ese nombre en la carpeta de listas, sea cual sea el año.",
    "Year planned:": "Año planificado:",
    "Editions of this year and later are not used as history.":
        "Las ediciones de este año y posteriores no se usan como historia.",
    "Earlier editions of the event": "Ediciones anteriores del evento",
    "Lists of the same class from other events":
        "Listas de la misma clase en otros eventos",
    "New titles:": "Títulos nuevos:",
    "How much of a variant may be titles that came into the archive in\n"
    "the last 18 months and were never played at the class. \"Like last\n"
    "year\" takes none — it offers them as replacements instead.":
        "Cuánto de una variante pueden ser títulos que entraron en el archivo en\n"
        "los últimos 18 meses y nunca se tocaron en la clase. «Como el año\n"
        "pasado» no toma ninguno — en su lugar los ofrece como sustitutos.",
    "Rarely played:": "Poco tocados:",
    "How much of a variant may be titles played at most twice at the\n"
    "class so far, new ones included, the ones that sound like the\n"
    "played ones first. \"Like last year\" takes none.":
        "Cuánto de una variante pueden ser títulos tocados como mucho dos veces\n"
        "en la clase hasta ahora, nuevos incluidos — primero los que suenan como\n"
        "los tocados. «Como el año pasado» no toma ninguno.",
    "Variants:": "Variantes:",
    "Like last year": "Como el año pasado",
    "Last year, renewed": "El año pasado, renovado",
    "Proven + fresh": "Probados + frescos",
    "Variety": "Variedad",
    "🤖  Let the AI check the drafts": "🤖  Que la IA revise los borradores",
    "The model reads every draft and proposes swaps; each one is\n"
    "checked against the day before it goes in. Without it the\n"
    "computed plan is shown as it is.":
        "El modelo lee cada borrador y propone cambios; cada uno se\n"
        "comprueba contra el día antes de entrar. Sin ella el plan\n"
        "calculado se muestra tal cual.",
    "Event plan": "Plan del evento",
    "No competition could be read from the schedule. Each line\n"
    "needs a class, a style (STD/LAT) or its dances in brackets,\n"
    "and the heats per round, e.g.  'HGR S STD 3-2-1'.":
        "No se pudo leer ninguna competición del horario. Cada línea\n"
        "necesita una clase, un estilo (STD/LAT) o sus bailes entre paréntesis,\n"
        "y los grupos por ronda, p. ej.  «HGR S STD 3-2-1».",
    "Tick at least one variant to plan.":
        "Marca al menos una variante para planificar.",
    "no earlier edition found — the class lists carry the plan":
        "no se encontró ninguna edición anterior — las listas de la clase sostienen el plan",
    "not used": "no usado",
    "%d competitions. Earlier editions: %s":
        "%d competiciones. Ediciones anteriores: %s",
    "Asking again about: %s": "Preguntando de nuevo por: %s",
    "Event": "Evento",
    "The plan": "El plan",
    "🏆 Planning the event…": "🏆 Planificando el evento…",
    "🏆 %d competitions planned in %d variants":
        "🏆 %d competiciones planificadas en %d variantes",
    "The AI's limit held back: %s\n"
    "\n"
    "%s\n"
    "\n"
    "Wait and ask again by itself in %d minutes?":
        "El límite de la IA retuvo: %s\n"
        "\n"
        "%s\n"
        "\n"
        "¿Esperar y volver a preguntar solo dentro de %d minutos?",
    "🏆 Asking the AI again at %s": "🏆 Se vuelve a preguntar a la IA a las %s",
    "1 swap not applied, kept for your choice":
        "1 cambio no aplicado, guardado para que elijas",
    "%d swaps not applied, kept for your choice":
        "%d cambios no aplicados, guardados para que elijas",
    "the AI could not check it — the plan stands":
        "la IA no pudo revisarlo — el plan se mantiene",
    "held back by the AI's limit — ask again later":
        "retenido por el límite de la IA — vuelve a preguntar más tarde",
    "🏆 Event plan": "🏆 Plan del evento",
    "🟦 This event's lists": "🟦 Listas de este evento",
    "🟩 The class lists": "🟩 Listas de la clase",
    "🟨 New titles": "🟨 Títulos nuevos",
    "🟧 Rarely played": "🟧 Poco tocados",
    "⬜ Library": "⬜ Biblioteca",
    "AI: %s": "IA: %s",
    "↺ Replaces '%s' of last year — %s":
        "↺ Reemplaza «%s» del año pasado — %s",
    "↻ Suggested instead: %s — %s": "↻ Propuesto en su lugar: %s — %s",
    "✋ The AI wanted '%s': %s": "✋ La IA quería «%s»: %s",
    "⏳ Ask about the held back now": "⏳ Preguntar ahora por lo retenido",
    "🔁 Second round": "🔁 Segunda ronda",
    "Ask the AI again where a swap was lost, to fill or improve those slots.":
        "Volver a preguntar a la IA donde se perdió un cambio, para llenar o mejorar esos huecos.",
    "Variant:": "Variante:",
    "The earlier editions had no list of this competition — 'like similar competitions' fills it from the class lists 🟩":
        "Las ediciones anteriores no tenían lista de esta competición — «Como competiciones similares» la llena con las listas de la clase 🟩",
    "Like similar competitions": "Como competiciones similares",
    "The variant of the competition in front — each tab keeps its own, ✔ in its header; a click on a column header chooses it too":
        "La variante de la competición de delante — cada pestaña guarda la suya, ✔ en su cabecera; un clic en una cabecera de columna también la elige",
    "Drag a title onto the same dance in another variant to take it over there, within its variant to swap the two":
        "Arrastra un título sobre el mismo baile en otra variante para llevarlo allí, o dentro de su variante para intercambiar los dos",
    "'%s' ⇄ '%s': %s.\n"
    "\n"
    "Swap anyway?":
        "«%s» ⇄ «%s»: %s.\n"
        "\n"
        "¿Intercambiar de todos modos?",
    "▶ A title's ▶ or Space plays it, again stops it; Ctrl+click in the menu one to choose from":
        "▶ El ▶ de un título o Espacio lo reproduce, otra vez lo detiene; Ctrl+clic en el menú, uno para elegir",
    "📅 Into the tournament-day decks": "📅 A los decks del día de torneo",
    "🏆  Open the last plan": "🏆  Abrir el último plan",
    "Show the last event plan side by side again, as you left it —\n"
    "nothing is planned or asked anew.":
        "Muestra de nuevo el último plan del evento lado a lado, tal como lo dejaste —\n"
        "no se planifica ni se pregunta nada de nuevo.",
    "⏳ Held back by the AI's limit: %s":
        "⏳ Retenido por el límite de la IA: %s",
    "⚠ The AI could not check: %s — the plan stands":
        "⚠ La IA no pudo revisar: %s — el plan se mantiene",
    "🔁 A swap was lost at: %s — a second round can fill or improve those slots":
        "🔁 Se perdió un cambio en: %s — una segunda ronda puede llenar o mejorar esos huecos",
    "Double-click or right-click a title for what else fits there.  🟦 event  🟩 class lists  🟨 new  🟧 rarely played  ⬜ library  ↺ replaces last year's title  ↻ a replacement is offered  ✋ the AI wanted another":
        "Doble clic o clic derecho en un título para ver qué más encaja ahí.  🟦 evento  🟩 listas de la clase  🟨 nuevo  🟧 poco tocado  ⬜ biblioteca  ↺ reemplaza el título del año pasado  ↻ se ofrece un sustituto  ✋ la IA quería otro",
    "'Last year, renewed' found no sound-alike to swap here — the same as 'Like last year'":
        "«El año pasado, renovado» no encontró aquí nada que suene parecido para cambiar — igual que «Como el año pasado»",
    "↺ Back to last year: %s": "↺ Volver al año pasado: %s",
    "↻ Take the suggestion: %s": "↻ Aceptar la propuesta: %s",
    "✋ The AI wanted: %s (%s)": "✋ La IA quería: %s (%s)",
    "'%s' %s.\n"
    "\n"
    "Put it in anyway?":
        "«%s» %s.\n"
        "\n"
        "¿Ponerlo de todos modos?",
    "🏆  %s: %d competitions into %d deck(s)":
        "🏆  %s: %d competiciones en %d deck(s)",
    "already plays that day": "ya suena ese día",
    "already plays in that round": "ya suena en esa ronda",
    "is offered for another slot": "se propone para otro hueco",
    "too many swaps": "demasiados cambios",
    "that slot is swapped already": "ese hueco ya está cambiado",
    "📦 Venue pack": "📦 Paquete de sala",
    "Take this desk to another PC in one file: the settings, every deck "
    "and wishlist, the 🎛 cartwall with its pads and keys — and, if you "
    "want, the music they use. Folder settings stay with each PC.":
        "Llevar esta mesa a otro PC en un solo archivo: los ajustes, cada deck "
        "y lista de deseos, el 🎛 Cartwall con sus pads y teclas — y, si "
        "quieres, la música que usan. Los ajustes de carpetas se quedan en cada PC.",
    "📦  Export venue pack…": "📦  Exportar paquete de sala…",
    "📥  Import venue pack…": "📥  Importar paquete de sala…",
    "Save this desk to one file to take to another PC: the settings,\n"
    "every deck and wishlist, the 🎛 cartwall with its pads and keys —\n"
    "and, if you want, the music they use. Folder settings stay with\n"
    "each PC.":
        "Guarda esta mesa en un archivo para llevarla a otro PC: los ajustes,\n"
        "cada deck y lista de deseos, la 🎛 Cartwall con sus pads y teclas —\n"
        "y, si quieres, la música que usan. Los ajustes de carpetas se quedan\n"
        "en cada PC.",
    "Load a venue pack made on another PC. It replaces this PC's\n"
    "settings, decks and cartwall at the next start; what it replaces\n"
    "is kept in a before-venue-import folder next to them.":
        "Carga un paquete de sala hecho en otro PC. Reemplaza los ajustes,\n"
        "los decks y la Cartwall de este PC en el próximo inicio; lo que reemplaza\n"
        "se guarda en una carpeta before-venue-import junto a ellos.",
    "Export venue pack": "Exportar paquete de sala",
    "Import venue pack": "Importar paquete de sala",
    "Include the music files?\n"
    "\n"
    "Yes: the %d track(s) the decks and the cartwall use go into the pack too (%s MB) — the other PC needs nothing else.\n"
    "No: settings, decks and cartwall only — the other PC has the music already.":
        "¿Incluir los archivos de música?\n"
        "\n"
        "Sí: los %d tema(s) que usan los decks y la Cartwall también van al paquete (%s MB) — el otro PC no necesita nada más.\n"
        "No: solo ajustes, decks y Cartwall — el otro PC ya tiene la música.",
    "Venue packs": "Paquetes de sala",
    "📦 Writing the venue pack…": "📦 Escribiendo el paquete de sala…",
    "📥 Unpacking the venue pack…": "📥 Desempaquetando el paquete de sala…",
    "All files": "Todos los archivos",
    "📦 Venue pack cancelled — nothing was written.":
        "📦 Paquete de sala cancelado — no se escribió nada.",
    "📦 Venue pack saved to:\n"
    "%s":
        "📦 Paquete de sala guardado en:\n"
        "%s",
    "%d track(s) included.": "%d tema(s) incluido(s).",
    "⚠ %d track(s) were missing on disk and are not in the pack.":
        "⚠ Faltaban %d tema(s) en el disco y no están en el paquete.",
    "This is no venue pack:": "Esto no es un paquete de sala:",
    "The pack carries %d music file(s).\n"
    "\n"
    "Yes: unpack them into a folder of this PC — the decks and the cartwall then play them from there.\n"
    "No: leave them in the pack — this PC has the music already (🧭 Fix paths finds it if it lives elsewhere).":
        "El paquete trae %d archivo(s) de música.\n"
        "\n"
        "Sí: desempaquétalos en una carpeta de este PC — los decks y la Cartwall los reproducen desde ahí.\n"
        "No: déjalos en el paquete — este PC ya tiene la música (🧭 Corregir rutas la encuentra si está en otro sitio).",
    "Folder for the venue pack's music":
        "Carpeta para la música del paquete de sala",
    "📥 Venue pack import cancelled.":
        "📥 Importación del paquete de sala cancelada.",
    "The import did not run:": "La importación no se ejecutó:",
    "The venue pack takes over at the next start: settings, decks and cartwall are replaced then, and what they replace is kept in a before-venue-import folder.\n"
    "\n"
    "Anything you change before that is lost.\n"
    "\n"
    "Restart now?":
        "El paquete de sala toma el control en el próximo inicio: entonces se reemplazan los ajustes, los decks y la Cartwall, y lo reemplazado se guarda en una carpeta before-venue-import.\n"
        "\n"
        "Lo que cambies antes se pierde.\n"
        "\n"
        "¿Reiniciar ahora?",
    "Play, skip, fade and fire pads from a phone's browser on this network — no app to install. The server's window shows the address, a QR code that logs the phone in, and the PIN.":
        "Reproducir, saltar, fundir y disparar pads desde el navegador de un móvil en esta red — sin instalar ninguna app. La ventana del servidor muestra la dirección, un código QR que inicia sesión en el móvil y el PIN.",
    "📱  Start Server": "📱  Iniciar servidor",
    "📱  Stop Server": "📱  Detener servidor",
    "Stops the phone remote's server — connected phones lose the remote.":
        "Detiene el servidor del mando del móvil — los móviles conectados pierden el mando.",
    "The phone remote's server is running — click for its window.":
        "El servidor del mando del móvil está en marcha — haz clic para ver su ventana.",
    "The hardware controller is connected — click for its window.":
        "El controlador de hardware está conectado — haz clic para ver su ventana.",
    "Starts the server and opens its window — stop it there again.\n"
    "\n"
    "Only phones on the same network get in, and only with the PIN;\n"
    "wrong PINs lock the phone out for a while.\n"
    "Windows may ask once whether the app may use the network —\n"
    "allow it for private networks.":
        "Inicia el servidor y abre su ventana — se detiene allí mismo.\n"
        "\n"
        "Solo entran móviles de la misma red, y solo con el PIN;\n"
        "los PIN incorrectos bloquean el móvil un rato.\n"
        "Windows puede preguntar una vez si la app puede usar la red —\n"
        "permítelo para redes privadas.",
    "New PIN": "Nuevo PIN",
    "Make up a new PIN — phones that know the old one have to enter it again.":
        "Inventar un PIN nuevo — los móviles que conocen el anterior tienen que introducirlo de nuevo.",
    "📱 Remote":
        "📱 Mando",
    "📱 The phone remote could not start: %s":
        "📱 El mando del móvil no pudo arrancar: %s",
    "📱 Phone remote on — open %s on the phone, PIN %s":
        "📱 Mando del móvil activo — abre %s en el móvil, PIN %s",
    "📱  Phone remote": "📱  Mando del móvil",
    "📱  Phone remote…": "📱  Mando del móvil…",
    "Play, skip, fade and fire pads from a phone's browser on this\n"
    "network — no app to install. Opens the window to start the\n"
    "server, with a QR code that logs the phone in and a log of what\n"
    "reached it.":
        "Reproducir, saltar, fundir y disparar pads desde el navegador de un móvil\n"
        "en esta red — sin instalar ninguna app. Abre la ventana que inicia el\n"
        "servidor, con un código QR que inicia sesión en el móvil y un registro\n"
        "de lo que le llegó.",
    "Scan the code with the phone's camera — it opens the remote, logged in. Or type the address:":
        "Escanea el código con la cámara del móvil — abre el mando con la sesión ya iniciada. O escribe la dirección:",
    "This PC is on more than one network. The first one is the way to\n"
    "the internet, usually the Wi-Fi the phone is on as well.":
        "Este PC está en más de una red. La primera es la salida a\n"
        "internet, normalmente la wifi en la que también está el móvil.",
    "Opens the remote in this PC's browser — a quick test that the server answers.":
        "Abre el mando en el navegador de este PC — una prueba rápida de que el servidor responde.",
    "Nothing turns up in the log when the phone tries? Then a firewall on this PC drops it: allow the program below for private networks (Windows Defender Firewall, or your security suite's own, e.g. Norton → Firewall → Program Control). The phone must be on the same Wi-Fi.%s":
        "¿No aparece nada en el registro cuando el móvil lo intenta? Entonces un cortafuegos de este PC lo descarta: permite el programa de abajo para redes privadas (Firewall de Windows Defender, o el de tu suite de seguridad, p. ej. Norton → Firewall → Control de programas). El móvil debe estar en la misma wifi.%s",
    "Log": "Registro",
    "● Running — port %d": "● En marcha — puerto %d",
    "○ Stopped": "○ Detenido",
    "■  Stop": "■  Detener",
    "▶  Start": "▶  Iniciar",
    "No network found — is this PC on the Wi-Fi?":
        "No se encontró ninguna red — ¿está este PC en la wifi?",
    "Press Start — the code to scan shows up here.":
        "Pulsa Iniciar — aquí aparecerá el código para escanear.",
    "Connecting… the code to scan shows up as soon as guests can reach the page.":
        "Conectando… el código para escanear aparece en cuanto los invitados puedan llegar a la página.",
    "No QR code: the segno package is missing. Type the address instead.":
        "Sin código QR: falta el paquete segno. Escribe la dirección.",
    "▶ Server started on port %(detail)s":
        "▶ Servidor iniciado en el puerto %(detail)s",
    "■ Server stopped": "■ Servidor detenido",
    "%(ip)s opened the page": "%(ip)s abrió la página",
    "✔ %(ip)s logged in with the PIN": "✔ %(ip)s inició sesión con el PIN",
    "✖ %(ip)s sent a wrong PIN": "✖ %(ip)s envió un PIN incorrecto",
    "⛔ %(ip)s locked out for %(detail)s s — too many wrong PINs":
        "⛔ %(ip)s bloqueado durante %(detail)s s — demasiados PIN incorrectos",
    "⛔ New phones paused for %(detail)s s — too many wrong PINs from the network":
        "⛔ Nuevos móviles en pausa durante %(detail)s s — demasiados PIN incorrectos desde la red",
    "⛔ %(ip)s refused — not on the local network":
        "⛔ %(ip)s rechazado — no está en la red local",
    "⚠ Could not start: %(detail)s": "⚠ No se pudo iniciar: %(detail)s",
    "DanceSport Player remote": "Mando de DanceSport Player",
    "Connect": "Conectar",
    "Wrong PIN": "PIN incorrecto",
    "Too many wrong PINs — wait a minute":
        "Demasiados PIN incorrectos — espera un minuto",
    "No connection to the desk": "Sin conexión con la mesa",
    "Nothing is playing": "No suena nada",
    "Play \"%s\" now? The playing title fades out.":
        "¿Poner \"%s\" ahora? El tema que suena se desvanece.",
    "Stop all pads": "Detener todos los pads",
    "Next": "Siguiente",
    "Fade & hold": "Fundir y mantener",
    "Announce next dance": "Anunciar el siguiente baile",
    "Crossfade": "Fundido cruzado",
    "Menus, buttons and dialogs are in Spanish. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Menús, botones y diálogos en español. Los bailes y las rondas conservan sus nombres internacionales en inglés; los títulos y todo lo que se lee de tus archivos se quedan como están.",
    "Menus, buttons and dialogs are in Dutch. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Menús, botones y diálogos en neerlandés. Los bailes y las rondas conservan sus nombres internacionales en inglés; los títulos y todo lo que se lee de tus archivos se quedan como están.",
    "Menus, buttons and dialogs are in Russian. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Menús, botones y diálogos en ruso. Los bailes y las rondas conservan sus nombres internacionales en inglés; los títulos y todo lo que se lee de tus archivos se quedan como están.",
    '🎛  Controller':
        '🎛  Controlador',
    'Play, skip, fade, set the volume and fire cartwall pads from a USB MIDI controller (e.g. Korg nanoKONTROL2) or a HID one (e.g. a Traktor controller in its native mode). Pick the device, load a profile or click Learn and press the button that should do it.':
        'Reproduce, salta, funde, ajusta el volumen y dispara pads de la cartwall desde un controlador MIDI USB (p. ej. Korg nanoKONTROL2) o uno HID (p. ej. un controlador Traktor en su modo nativo). Elige el dispositivo, carga un perfil o pulsa Aprender y luego el botón que debe hacerlo.',
    '— none —':
        '— ninguno —',
    'Device:':
        'Dispositivo:',
    'Look for devices again':
        'Buscar dispositivos de nuevo',
    'Show all HID devices, not only DJ controllers':
        'Mostrar todos los dispositivos HID, no solo controladores DJ',
    'Presets ▾':
        'Preajustes ▾',
    '📂  Load profile…':
        '📂  Cargar perfil…',
    '💾  Save profile…':
        '💾  Guardar perfil…',
    'Learn':
        'Aprender',
    'Unbind this action':
        'Quitar la asignación',
    '%s — not plugged in':
        '%s — no conectado',
    '● Connected — %s':
        '● Conectado — %s',
    '○ Not connected — %s':
        '○ No conectado — %s',
    'No controller chosen.':
        'Ningún controlador elegido.',
    'Profile: %s':
        'Perfil: %s',
    'own':
        'propio',
    'Press or move a control…':
        'Pulsa o mueve un control…',
    'on the fader — %s':
        'con el fader — %s',
    'Load controller profile':
        'Cargar perfil del controlador',
    'Controller profiles (*.json)':
        'Perfiles de controlador (*.json)',
    'This file is not a controller profile:\n%s':
        'Este archivo no es un perfil de controlador:\n%s',
    'Save controller profile':
        'Guardar perfil del controlador',
    'Could not save the profile:\n%s':
        'No se pudo guardar el perfil:\n%s',
    'not bound':
        'sin asignar',
    'Last: %(control)s = %(value)d%% → %(action)s':
        'Último: %(control)s = %(value)d%% → %(action)s',
    '🎛  Cartwall pad %d':
        '🎛  Pad %d de la cartwall',
    '⏯  Play / pause':
        '⏯  Reproducir / pausa',
    '⏭  Next title':
        '⏭  Siguiente tema',
    '⏮  Previous title':
        '⏮  Tema anterior',
    '🔉↓  Fade out now':
        '🔉↓  Fundir ahora',
    '🛑  Fade out and hold':
        '🛑  Fundir y mantener',
    '🔉  Duck the music on / off':
        '🔉  Bajar la música sí / no',
    '🔈  Announce the next dance on / off':
        '🔈  Anunciar el siguiente baile sí / no',
    '🔊  Music volume (fader or knob)':
        '🔊  Volumen de la música (fader o potenciómetro)',
    '⏹  Stop all pads':
        '⏹  Detener todos los pads',
    'Play, skip, fade, set the volume and fire cartwall pads from a USB MIDI or HID controller — a profile for the Korg nanoKONTROL2 is built in, any other is learned by pressing its buttons.':
        'Reproduce, salta, funde, ajusta el volumen y dispara pads de la cartwall desde un controlador MIDI o HID USB — el perfil del Korg nanoKONTROL2 viene incluido, cualquier otro se aprende pulsando sus botones.',
    '🎛  Set up…':
        '🎛  Configurar…',
    # 🤸 the practice panel's own name
    "Practice": "Práctica",
    "Practice / Party": "Práctica / Fiesta",
    "🤸  Practice / Party": "🤸  Práctica / Fiesta",
    "🤸  Practice / Party ▾": "🤸  Práctica / Fiesta ▾",
    "Tempo from the file name": "Tempo del nombre de archivo",
    "Tempo from the BPM tag (%s bpm)": "Tempo de la etiqueta BPM (%s bpm)",
    "Tempo from the title tag": "Tempo de la etiqueta de título",
    "🔈  Sound outputs":
        "🔈  Salidas de audio",
    "%s %s is not connected — it plays on the system default.":
        "%s %s no está conectado — suena en el predeterminado del sistema.",
    "🎧 Pre-listen is on the music's own output — every preview is refused.":
        "🎧 La preescucha está en la salida de la música — se rechaza cada preescucha.",
    "Every chosen output is plugged in.":
        "Cada salida elegida está conectada.",
    "%s is connected.":
        "%s está conectado.",
    "%s is not connected — plug it in if tonight needs it.":
        "%s no está conectado — conéctalo si esta noche lo necesita.",
    "☀  Screen and sleep":
        "☀  Pantalla y suspensión",
    "While music plays or the presenter screen is up, the screen, the beamer and the computer stay awake.":
        "Mientras suena música o la pantalla del presentador está abierta, la pantalla, el proyector y el ordenador siguen despiertos.",
    "☀ Keep the screen awake is off — an hour nobody touches the desk blanks the screen and the beamer, and may put the computer to sleep.":
        "☀ Mantener la pantalla encendida está desactivado — una hora sin tocar la mesa apaga la pantalla y el proyector, y puede suspender el ordenador.",
    "🔴  Not ready — a sound output is not connected.":
        "🔴  No está listo — una salida de audio no está conectada.",
    "⚙  Choose outputs…":
        "⚙  Elegir salidas…",
    "🎛  Open the controller…":
        "🎛  Abrir el controlador…",
    "☀  Keep it awake":
        "☀  Mantener despierto",
    "🔀  Crossfade:":
        "🔀  Fundido cruzado:",
    "crossfade → %s s":
        "fundido cruzado → %s s",
    "crossfade → off":
        "fundido cruzado → desactivado",
    "🔀 The last %s s of a title and the first %s s of the next play together:\nred the one going out, green the one coming in.":
        "🔀 Los últimos %s s de un título y los primeros %s s del siguiente suenan juntos:\nrojo el que sale, verde el que entra.",
    "🔀 No crossfade: one title ends, then the next starts.":
        "🔀 Sin fundido cruzado: un título termina y luego empieza el siguiente.",
    "The next title comes in under the end of the\nlast one — only where the list walks on with\nno pause. Off: one ends, the next starts.":
        "El siguiente título entra bajo el final del\nanterior — solo donde la lista sigue sin\npausa. Desactivado: uno termina, empieza el siguiente.",
    "The last seconds of a title and the first of the next play\ntogether: the old one fades out while the new one fades in,\nso the floor never hears a gap. Only where the list walks on\nby itself with no pause — a heat keeps its gap. Not after a\n🏁 round, a 🔁 title or a 🐂 Paso Doble run to its highlight.\n\nOff: one title ends, then the next starts. Every playlist\nkeeps its own answer.":
        "Los últimos segundos de un título y los primeros del siguiente\nsuenan juntos: el viejo se desvanece mientras entra el nuevo,\nasí la pista nunca oye un hueco. Solo donde la lista sigue\nsola sin pausa — una ronda de competición conserva su hueco.\nNo tras una 🏁 ronda, un título 🔁 ni un 🐂 Paso Doble hasta su clímax.\n\nDesactivado: un título termina y luego empieza el siguiente.\nCada lista conserva su propia respuesta.",
    "How long the two titles play together — half-second steps":
        "Cuánto tiempo suenan juntos los dos títulos — en medios segundos",
    "crossfade curve → %s":
        "curva del fundido → %s",
    "equal power":
        "potencia constante",
    "linear":
        "lineal",
    "S-curve":
        "curva en S",
    "🔀 Equal power: the two titles add up to one steady level\nall the way across — right for two unrelated songs.":
        "🔀 Potencia constante: los dos títulos suman un nivel estable\nde principio a fin — lo adecuado para dos canciones distintas.",
    "🔀 Linear: two straight lines, the way a plain mixer fader\ndoes it — a little quieter in the middle.":
        "🔀 Lineal: dos líneas rectas, como lo hace un fader de mezclador\nsencillo — un poco más bajo en el medio.",
    "🔀 S-curve: steady like equal power, but slow off both ends —\nthe new title is barely there at first, the old one lingers.":
        "🔀 Curva en S: estable como la potencia constante, pero lenta en ambos extremos —\nel título nuevo apenas se oye al principio, el viejo se queda un poco.",
    # ── 📨 Guest requests ──
    "📨  Guest requests":
        "📨  Peticiones de invitados",
    "📨  Guest requests…":
        "📨  Peticiones de invitados…",
    "Guests search the library on their phones and ask for a title, or\nleave a few words — it lands in an inbox, and you put it on the\nwishlist or dismiss it. Nothing a guest sends is played on its own.":
        "Los invitados buscan en la biblioteca desde el móvil y piden un título, o\ndejan unas palabras — llega a una bandeja de entrada, y tú lo pones en la\nlista de deseos o lo descartas. Nada de lo que envía un invitado suena solo.",
    "Guests scan the code with their phone's camera — it opens the request page. Or show them the address:":
        "Los invitados escanean el código con la cámara del móvil — abre la página de peticiones. O enséñales la dirección:",
    "This PC is on more than one network. The first one is the way to\nthe internet, usually the Wi-Fi the guests are on as well.":
        "Este PC está en más de una red. La primera es la salida a\ninternet, normalmente la wifi en la que están también los invitados.",
    "Opens the request page in this PC's browser — a quick test that the server answers.":
        "Abre la página de peticiones en el navegador de este PC — una prueba rápida de que el servidor responde.",
    "New code":
        "Código nuevo",
    "Make up a new event code — older links and photos of the QR code stop working.":
        "Inventar un código de evento nuevo — los enlaces y fotos anteriores del código QR dejan de funcionar.",
    "⭐  To wishlist":
        "⭐  A la lista de deseos",
    "Put the requested title on the first ⭐ wishlist.":
        "Poner el título pedido en la primera ⭐ lista de deseos.",
    "✕  Dismiss":
        "✕  Descartar",
    "Take the request out of the inbox.":
        "Quitar la petición de la bandeja de entrada.",
    "Inbox":
        "Bandeja de entrada",
    "○ Closed":
        "○ Cerrado",
    "● Open — port %d":
        "● Abierto — puerto %d",
    "Event code: %s":
        "Código del evento: %s",
    "▶ Guest requests open on port %(detail)s":
        "▶ Peticiones de invitados abiertas en el puerto %(detail)s",
    "■ Guest requests closed":
        "■ Peticiones de invitados cerradas",
    "📨 %(ip)s asks for %(detail)s":
        "📨 %(ip)s pide %(detail)s",
    "📨 %(ip)s wishes: %(detail)s":
        "📨 %(ip)s desea: %(detail)s",
    "✖ %(ip)s came with an old code":
        "✖ %(ip)s llegó con un código antiguo",
    "⛔ %(ip)s sent too many requests":
        "⛔ %(ip)s envió demasiadas peticiones",
    "Guest requests — click for the inbox.":
        "Peticiones de invitados — haz clic para la bandeja de entrada.",
    "⭐ On the wishlist: %s":
        "⭐ En la lista de deseos: %s",
    "⭐ Already on the wishlist: %s":
        "⭐ Ya está en la lista de deseos: %s",
    "📨 Guest request: %s": "📨 Petición de invitado: %s",
    "📨 Guest wish: %s": "📨 Deseo de invitado: %s",
    "📨 Guest requests could not start: %s":
        "📨 Las peticiones de invitados no pudieron arrancar: %s",
    "Song requests":
        "Peticiones de canciones",
    "Now playing":
        "Suena ahora",
    "Search a title or artist":
        "Busca un título o artista",
    "Loading the titles…":
        "Cargando los títulos…",
    "No matching title — write it as a wish below":
        "Ningún título coincide — escríbelo abajo como deseo",
    "Request":
        "Pedir",
    "Not in the list? Write your wish:":
        "¿No está en la lista? Escribe tu deseo:",
    "Send":
        "Enviar",
    "Thank you — the DJ has your request":
        "Gracias — el DJ tiene tu petición",
    "That was a lot of requests — please wait a few minutes":
        "Han sido muchas peticiones — espera unos minutos, por favor",
    "Requests are closed right now":
        "Las peticiones están cerradas ahora mismo",
    "This link is out of date — scan the current QR code":
        "Este enlace está caducado — escanea el código QR actual",
    "No connection to the DJ — try again in a moment":
        "Sin conexión con el DJ — inténtalo de nuevo en un momento",
    "Guests must be on the same Wi-Fi as this PC — or on its hotspot.":
        "Los invitados deben estar en la misma Wi-Fi que este PC — o en su punto de acceso.",
    "Nothing turns up in the log when a phone on the Wi-Fi tries? Then a firewall on this PC drops it: allow the program below for private networks.%s":
        "¿No aparece nada en el registro cuando lo intenta un móvil en la Wi-Fi? Entonces un cortafuegos de este PC lo bloquea: permite el programa de abajo en redes privadas.%s",
    "The https address works on mobile data too, and on any Wi-Fi. It is new on every start — show the fresh QR code.":
        "La dirección https funciona también con datos móviles y en cualquier Wi-Fi. Cambia en cada inicio — muestra el código QR nuevo.",
    "Guests reach the page:":
        "Los invitados llegan a la página:",
    "Wi-Fi only":
        "Solo Wi-Fi",
    "Wi-Fi and mobile data (Cloudflare tunnel)":
        "Wi-Fi y datos móviles (túnel de Cloudflare)",
    "Wi-Fi only: guests must be on the same Wi-Fi as this PC, or on its hotspot.\nCloudflare tunnel: a public https address leads to this PC as well —\nno account and no router setup; it changes with every start.\nNeeds the free cloudflared program (asked for on the first start).":
        "Solo Wi-Fi: los invitados deben estar en la misma Wi-Fi que este PC o en su punto de acceso.\nTúnel de Cloudflare: una dirección https pública también lleva a este PC —\nsin cuenta y sin configurar el router; cambia en cada inicio.\nNecesita el programa gratuito cloudflared (se pregunta en el primer inicio).",
    "The tunnel needs Cloudflare's free cloudflared program (about 55 MB). Download it now from Cloudflare's releases on GitHub?\n\nIt goes to: %s":
        "El túnel necesita el programa gratuito cloudflared de Cloudflare (unos 55 MB). ¿Descargarlo ahora desde las versiones de Cloudflare en GitHub?\n\nSe guarda en: %s",
    "Then download cloudflared yourself from\n%s\nand put it next to the program, as %s in:\n%s\n\nUntil then choose Wi-Fi only.":
        "Entonces descarga cloudflared tú mismo desde\n%s\ny ponlo junto al programa, como %s en:\n%s\n\nHasta entonces elige «Solo Wi-Fi».",
    "Downloading cloudflared…":
        "Descargando cloudflared…",
    "Download it yourself instead from <a href=\"%s\">Cloudflare's releases on GitHub</a>:":
        "Descárgalo tú mismo desde <a href=\"%s\">las versiones de Cloudflare en GitHub</a>:",
    "Take <b>%s</b>, double-click it to unpack it, and put the <b>cloudflared</b> inside into:":
        "Toma <b>%s</b>, haz doble clic para descomprimirlo y pon el <b>cloudflared</b> que contiene en:",
    "Take <b>%s</b> and save it as <b>%s</b> in:":
        "Toma <b>%s</b> y guárdalo como <b>%s</b> en:",
    "Then make it runnable: <code>chmod +x %s</code>":
        "Después hazlo ejecutable: <code>chmod +x %s</code>",
    "Or, with Homebrew: <code>brew install cloudflared</code>":
        "O con Homebrew: <code>brew install cloudflared</code>",
    "Then start again. Until then choose Wi-Fi only.":
        "Después inicia de nuevo. Hasta entonces elige «Solo Wi-Fi».",
    "The download failed: %s":
        "La descarga ha fallado: %s",
    "● Open — port %d, waiting for Cloudflare…":
        "● Abierto — puerto %d, esperando a Cloudflare…",
    "🌐 Connecting to Cloudflare…":
        "🌐 Conectando con Cloudflare…",
    "🌐 Public address: %(detail)s":
        "🌐 Dirección pública: %(detail)s",
    "⚠ The tunnel ended (exit code %(detail)s) — guests on mobile data are cut off":
        "⚠ El túnel se ha cerrado (código de salida %(detail)s) — los invitados con datos móviles quedan fuera",
    "⚠ cloudflared not found — guests reach the page on the Wi-Fi only":
        "⚠ No se encontró cloudflared — los invitados solo llegan a la página por Wi-Fi",
    "⚠ The tunnel could not start: %(detail)s":
        "⚠ El túnel no pudo iniciarse: %(detail)s",
    "The phone reaches the desk:":
        "El móvil llega a la mesa:",
    "Wi-Fi only: the phone must be on the same Wi-Fi as this PC, or on its hotspot.\nCloudflare tunnel: a public https address leads to this PC as well —\nno account and no router setup; it changes with every start, and\nthe PIN grows to 8 digits. Needs the free cloudflared program.":
        "Solo Wi-Fi: el móvil debe estar en la misma Wi-Fi que este PC o en su punto de acceso.\nTúnel de Cloudflare: una dirección https pública también lleva a este PC —\nsin cuenta y sin configurar el router; cambia en cada inicio, y\nel PIN pasa a 8 cifras. Necesita el programa gratuito cloudflared.",
    "The https address works on mobile data too, and on any Wi-Fi. It is new on every start — scan the fresh QR code. Whoever has the address still needs the PIN.":
        "La dirección https funciona también con datos móviles y en cualquier Wi-Fi. Es nueva en cada inicio: escanea el código QR nuevo. Quien tenga la dirección sigue necesitando el PIN.",
    "● Running — port %d, waiting for Cloudflare…":
        "● En marcha — puerto %d, esperando a Cloudflare…",
    "Connecting… the code to scan shows up as soon as the phone can reach the desk.":
        "Conectando… el código para escanear aparece en cuanto el móvil pueda llegar a la mesa.",
    "⚠ The tunnel ended (exit code %(detail)s) — the phone reaches the desk on the Wi-Fi only":
        "⚠ El túnel terminó (código de salida %(detail)s) — el móvil llega a la mesa solo por Wi-Fi",
    "⚠ cloudflared not found — the phone reaches the desk on the Wi-Fi only":
        "⚠ cloudflared no encontrado — el móvil llega a la mesa solo por Wi-Fi",
    "Song request? Scan here":
        "¿Peticiones? Escanea aquí",
    "🖥  Show the QR code on the presenter screen":
        "🖥  Mostrar el código QR en la pantalla del presentador",
    "While guest requests are open, the presenter screen shows the code in\nits corner — guests scan it from the floor.":
        "Mientras las peticiones están abiertas, la pantalla del presentador\nmuestra el código en su esquina — los invitados lo escanean desde la pista.",
    "refused":
        "rechazado",
    "Music folder":
        "Carpeta de música",
    "Where is your dance music?":
        "¿Dónde está tu música de baile?",
    "Use this folder":
        "Usar esta carpeta",
    "Choose another folder…":
        "Elegir otra carpeta…",
    "Every start reads the MP3 files in this folder and in all\n"
    "folders below it. The first start reads each file once,\n"
    "which takes long on a whole drive or an external disk,\n"
    "so pick the folder that holds your dance music.\n\n"
    "Found: %s\n\n"
    "You can change it at any time under ⚙ Settings → 📁 Paths.":
        "Cada inicio lee los archivos MP3 de esta carpeta y de todas\n"
        "las carpetas que contiene. El primer inicio lee cada archivo una vez,\n"
        "lo que tarda mucho en una unidad entera o un disco externo,\n"
        "así que elige la carpeta que contiene tu música de baile.\n\n"
        "Encontrada: %s\n\n"
        "Puedes cambiarlo en cualquier momento en ⚙ Ajustes → 📁 Rutas.",
    "Name the folder for the bundle on “%s”:":
        "Nombre de la carpeta del paquete en «%s»:",
    "Make a folder named after the tournament in “%s”?":
        "¿Crear una carpeta con el nombre del torneo en «%s»?",
    "📁  Create folder":
        "📁  Crear carpeta",
    "Straight into “%s”":
        "Directamente en «%s»",
    "📦 Venue pack: this desk for another PC…":
        "📦 Paquete de sala: esta mesa para otro PC…",
    "⭐ Include wishlists (%d)":
        "⭐ Incluir listas de deseos (%d)",
    "Each ⭐ wishlist with titles in it gets its own numbered\n"
    "folder in the bundle, beside the playlists.":
        "Cada ⭐ lista de deseos con temas tiene su propia carpeta\n"
        "numerada en el paquete, junto a las listas.",
    "One file with the settings, every deck and wishlist and the\n"
    "cartwall, the music they use if you want: the same as\n"
    "⚙ Settings → 📦 Venue pack → Export venue pack….":
        "Un archivo con los ajustes, cada deck y lista de deseos y la\n"
        "Cartwall, con la música que usan si quieres: lo mismo que\n"
        "⚙ Ajustes → 📦 Paquete de sala → Exportar paquete de sala….",
    "📚 Listing the library folder…":
        "📚 Leyendo la carpeta de música…",
    "📚 Library: %s / %s files":
        "📚 Biblioteca: %s / %s archivos",
    "📚 The library is still loading — this works once it is done.":
        "📚 La biblioteca aún se está cargando; esto funciona cuando termine.",
    "🎯  Focus playlist 1":
        "🎯  Enfocar la lista de reproducción 1",
    "🎯  Focus playlist 2":
        "🎯  Enfocar la lista de reproducción 2",
    "🎯  Focus playlist 3":
        "🎯  Enfocar la lista de reproducción 3",
    "🎯  Focus playlist 4":
        "🎯  Enfocar la lista de reproducción 4",
    "🎯  Focus playlist 5":
        "🎯  Enfocar la lista de reproducción 5",
    "🎯  Focus playlist 6":
        "🎯  Enfocar la lista de reproducción 6",
    "🎯  Focus playlist 7":
        "🎯  Enfocar la lista de reproducción 7",
    "🎯  Focus playlist 8":
        "🎯  Enfocar la lista de reproducción 8",
    "🎯  Focus wishlist 1":
        "🎯  Enfocar la lista de deseos 1",
    "🎯  Focus wishlist 2":
        "🎯  Enfocar la lista de deseos 2",
    "🎯  Focus wishlist 3":
        "🎯  Enfocar la lista de deseos 3",
    "🎯  Focus wishlist 4":
        "🎯  Enfocar la lista de deseos 4",
    "📚  Focus the library":
        "📚  Enfocar la biblioteca",
    "🔄  Browse the list (endless knob)":
        "🔄  Recorrer la lista (mando sin fin)",
    "⬆  Browse up":
        "⬆  Subir en la lista",
    "⬇  Browse down":
        "⬇  Bajar en la lista",
    "▶  Play the selected title":
        "▶  Reproducir el título seleccionado",
    "➕  Selected title to the playlist":
        "➕  Título seleccionado a la lista de reproducción",
    "⭐  Selected title to the wishlist":
        "⭐  Título seleccionado a la lista de deseos",
    "➕  This playlist takes a title only dragged onto a slot.":
        "➕  Esta lista solo acepta un título arrastrado a una posición.",
    "Warm-up list: swap the two selected titles of one dance":
        "Lista de calentamiento: intercambiar los dos títulos seleccionados de un baile",
    "Enter":
        "Intro",
    "Play / stop the selected song — in Playing mode also in the list playing, where Space pauses the player":
        "Reproducir / detener el tema seleccionado — en modo Reproducción también en la lista que suena, donde Espacio pausa el reproductor",
    "⏸ Library scan paused: %s / %s files":
        "⏸ Escaneo de la biblioteca en pausa: %s / %s archivos",
    "⏹ Stopping the library scan…":
        "⏹ Deteniendo el escaneo de la biblioteca…",
    "Pause the library scan":
        "Pausar el escaneo de la biblioteca",
    "Go on with the library scan":
        "Continuar el escaneo de la biblioteca",
    "Stop the library scan and use the titles read so far; the next start scans the rest":
        "Detener el escaneo de la biblioteca y usar los temas leídos hasta ahora; el próximo inicio escanea el resto",
    "⭐ Favorites":
        "⭐ Favoritos",
    "🌐 Whole library":
        "🌐 Toda la biblioteca",
    "⏳ Whole library…":
        "⏳ Toda la biblioteca…",
    "The whole library is still loading in the background.\nIt is listed here when it is there; keep working meanwhile.":
        "Toda la biblioteca aún se está cargando en segundo plano.\nAparecerá aquí en cuanto esté lista; mientras tanto puedes seguir trabajando.",
    "🌐 The whole library is still loading — it is listed when it is there.":
        "🌐 Toda la biblioteca aún se está cargando — aparecerá en cuanto esté lista.",
    "🌐 Loading the whole library…":
        "🌐 Cargando toda la biblioteca…",
    "🌐 Listing the whole library: %s / %s titles":
        "🌐 Listando toda la biblioteca: %s / %s títulos",
    "📚 Listing the library: %s / %s titles":
        "📚 Listando la biblioteca: %s / %s títulos",
    "Listing the whole music repository.\nClick to go back to the favorites library.":
        "Muestra todo el repositorio de música.\nHaz clic para volver a la biblioteca de favoritos.",
    "Listing the favorites library.\nClick to list the whole music repository instead.":
        "Muestra la biblioteca de favoritos.\nHaz clic para mostrar todo el repositorio de música.",
    '🔄  Scan repository for new titles':
        '🔄  Buscar títulos nuevos en el repositorio',
    'Walk the whole music repository folder and read the tags of new and\nchanged files, so 🌐 Whole library in the library pane and the global\nsearch know every title. No audio analysis; the scan runs in the\nbackground, its progress in the status bar.':
        'Recorrer toda la carpeta del repositorio musical y leer las etiquetas de los\narchivos nuevos y modificados, para que 🌐 Toda la biblioteca en el panel de\nla biblioteca y la búsqueda global conozcan todos los títulos. Sin análisis\nde audio; el escaneo se ejecuta en segundo plano, su progreso en la barra de estado.',
    'Scan the whole music repository again for new and changed titles.\nReads the tags only, no audio analysis; the progress shows in the\nstatus bar.':
        'Volver a escanear todo el repositorio musical en busca de títulos nuevos y modificados.\nSolo lee las etiquetas, sin análisis de audio; el progreso aparece en la\nbarra de estado.',
    '🌐 Repository: %s / %s files':
        '🌐 Repositorio: %s / %s archivos',
    'Go on with the repository scan':
        'Continuar el escaneo del repositorio',
    'Pause the repository scan':
        'Pausar el escaneo del repositorio',
    'Stop the repository scan and use the titles read so far; the next scan reads the rest':
        'Detener el escaneo del repositorio y usar los títulos leídos hasta ahora; el próximo escaneo lee el resto',
    '⏹ Stopping the repository scan…':
        '⏹ Deteniendo el escaneo del repositorio…',
    '⏸ Repository scan paused: %s / %s files':
        '⏸ Escaneo del repositorio en pausa: %s / %s archivos',
    '🌐 Listing the repository folder…':
        '🌐 Listando la carpeta del repositorio…',
    '🌐 The repository is being scanned already.':
        '🌐 El repositorio ya se está escaneando.',
    'Scan repository':
        'Escanear repositorio',
}
