"""Russian chrome, keyed by the English string as it stands in the code.

Built against planner/i18n/lang_de.py, which holds the full key set and the rules
(keys copied character for character, the emoji stays, only chrome). A key
missing here falls back to English on its own.

Vocabulary: вы throughout. Heat = заход, Round = тур, Playlist = плейлист,
Track = трек, Pad = пэд, Settings = Настройки, Reference path = опорный
путь, Practice = практика. Counts are written "Label: %d" so no plural
forms are needed. Deck and Cartwall are left as they are; dances and rounds
keep their international English names.
"""

CATALOG = {
    "Cancel": "Отмена",
    "Nb.": "№",
    "none": "нет",
    "e.g. 6-3-2-1": "напр. 6-3-2-1",
    "Group A–D": "Группа A–D",
    "Group E–H": "Группа E–H",
    "Preview-player options": "Настройки плеера предпрослушивания",
    "Fade every running pad out (Esc)":
        "Плавно заглушить все играющие пэды (Esc)",
    "Fade between music and timetable every":
        "Переключаться между музыкой и расписанием каждые",
    "    Only tracks not already in my open playlists":
        "    Только треки, которых ещё нет в моих открытых плейлистах",
    "Close": "Закрыть",
    "Replace": "Заменить",
    "Reset": "Сбросить",
    "Generate": "Создать",
    "Parse": "Разобрать",
    "Colour": "Цвет",
    "Label": "Подпись",
    "Heading": "Заголовок",
    "A new line at the end": "Новая строка в конце",
    "Take the selected line out": "Убрать выбранную строку",
    "Move the selected line up": "Переместить выбранную строку вверх",
    "Move the selected line down": "Переместить выбранную строку вниз",
    "Shortcut": "Сочетание клавиш",
    "Class": "Класс",
    "Class:": "Класс:",
    "Style:": "Программа:",
    "Method:": "Метод:",
    "Model:": "Модель:",
    "Count:": "Количество:",
    "Context:": "Контекст:",
    "Volume": "Громкость",
    "Master volume": "Общая громкость",
    "Fade out": "Затухание",
    "within the length": "в пределах времени звучания",
    "Ticked: the fade-out ends at the play length.\n"
    "Unticked: the title plays its full length, then fades out.":
        "Отмечено: затухание заканчивается вместе со временем звучания.\n"
        "Не отмечено: трек звучит всё время звучания, затем затухает.",
    "fade-out → within the length": "затухание → в пределах времени звучания",
    "fade-out → after the length": "затухание → после времени звучания",
    "Fade-out:": "Затухание:",
    "Own fade-out": "Своё затухание",
    "Play length:": "Длительность:",
    "Start after:": "Старт через:",
    "Stop after highlight:": "Стоп после кульминации:",
    "Max tracks:": "Макс. треков:",
    "Proven": "Проверенные",
    "Top Proven": "Самые проверенные",
    "Fresh": "Новые",
    "Mostly Proven": "В основном проверенные",
    "Even Mix": "Ровная смесь",
    "Songs you have played before (fresh as fallback).":
        "Треки, которые вы уже ставили (новые — в запасе).",
    "Only your most-played songs.": "Только ваши самые частые треки.",
    "Unused songs first (proven as fallback).":
        "Сначала неиспользованные треки (проверенные — в запасе).",
    "Proven + fresh together, but favors songs you have played before.":
        "Проверенные + новые вместе, но с предпочтением уже звучавших треков.",
    "Proven + fresh with no preference — equal chance, maximum variety.":
        "Проверенные + новые без предпочтения — равные шансы, максимум разнообразия.",
    "🌐  Search mode: Global — whole repository":
        "🌐  Режим поиска: глобальный — весь репозиторий",
    "🎯  Search mode: Favorites library only":
        "🎯  Режим поиска: только избранная библиотека",
    "Library: %d files": "Библиотека: %d файлов",
    "Favorites: %d": "Избранное: %d",
    "Library loaded — %s MP3 files, %s favorites songs, %s audio cached.":
        "Библиотека загружена — %s файлов MP3, %s избранных треков, %s в аудиокэше.",
    "— Indexes (analyzed / total) —": "— Индексы (проанализировано / всего) —",
    "🔗 Fingerprints: %s": "🔗 Отпечатки: %s",
    "📊 Loudness: %s": "📊 Громкость (LUFS): %s",
    "🔇 Silences: %s": "🔇 Тишина: %s",
    "🐂 PD highlights: %s": "🐂 Кульминации PD: %s",
    "🎙️ Demucs vocals: %s measured": "🎙️ Вокал Demucs: измерено %s",
    "🌐 Global index: %s files, %s analyzed":
        "🌐 Глобальный индекс: %s файлов, %s проанализировано",
    "🌐 Global index: %s files built (loads on first global search)":
        "🌐 Глобальный индекс: построено %s файлов (загрузится при первом глобальном поиске)",
    "🌐 Global index: not built (⚙ Settings to build)":
        "🌐 Глобальный индекс: не построен (⚙ Настройки, чтобы построить)",
    "(MERT not available)": "(MERT недоступен)",
    "(chroma not available)": "(Chroma недоступна)",
    "no Paso Doble in the library": "в библиотеке нет Пасодобля",
    "%s file(s) in the favorites library have no\n"
    "analysis yet":
        "%s файл(ов) избранной библиотеки ещё\n"
        "не проанализированы",
    "an index of the favorites library is not complete yet":
        "индекс избранной библиотеки ещё не полон",
    "🧱 Build ALL caches — %s. Asks for the scope\n"
    "first; reuses everything already cached and can be cancelled.":
        "🧱 Построить ВСЕ кэши — %s. Сначала спрашивает об\n"
        "объёме; использует всё уже закэшированное, можно отменить.",
    "audio fingerprints": "аудиоотпечатки",
    "loudness": "громкость",
    "silences": "тишина",
    "PD highlights": "кульминации PD",
    "librosa audio analysis (no working audio decoder)":
        "аудиоанализ librosa (нет рабочего аудиодекодера)",
    "loudness + silences (no ffmpeg)": "громкость + тишина (нет ffmpeg)",
    "%s (not installed)": "%s (не установлен)",
    "\n"
    "\n"
    "Skipped: %s":
        "\n"
        "\n"
        "Пропущено: %s",
    "Nothing can be built on this machine right now.":
        "Сейчас на этом компьютере ничего нельзя построить.",
    "Build every index over %s tracks from %s?":
        "Построить все индексы по %s трекам из %s?",
    "Runs %s back-to-back. Each is slow the first time, then cached; reuses anything already built. You can cancel between or within steps.":
        "Выполняет %s по очереди. Каждый шаг медленный в первый раз, потом кэшируется; всё уже построенное используется повторно. Отменить можно между шагами и во время них.",
    "Read-only — your audio files are never modified.":
        "Только чтение — ваши аудиофайлы никогда не изменяются.",
    "the favorites library": "избранная библиотека",
    "the whole repository": "весь репозиторий",
    "the whole repository + favorites library":
        "весь репозиторий + избранная библиотека",
    "All %s files in %s are already analyzed.":
        "Все %s файлов в %s уже проанализированы.",
    "%s of %s files in %s need analysis (~%s min).\n"
    "\n"
    "Analysis only reads your files — never modifies them. Results are cached.\n"
    "\n"
    "Run now?":
        "%s из %s файлов в %s нуждаются в анализе (~%s мин).\n"
        "\n"
        "Анализ только читает ваши файлы — никогда их не изменяет. Результаты кэшируются.\n"
        "\n"
        "Запустить сейчас?",
    "Audio index: analyzing %s files…": "Аудиоиндекс: анализ %s файлов…",
    "Building audio index (%s)…": "Строится аудиоиндекс (%s)…",
    "Global index: %s/%s%s": "Глобальный индекс: %s/%s%s",
    "  (%s errors)": "  (%s ошибок)",
    " (%s errors)": " (%s ошибок)",
    "Audio index built — %s files analyzed":
        "Аудиоиндекс построен — проанализировано %s файлов",
    "Analyzed %s files in %s": "Проанализировано %s файлов в %s",
    ".\n"
    "Similarity search will now match across them.":
        ".\n"
        "Поиск похожих теперь сравнивает их все.",
    "Audio index cancelled — %s files analyzed so far (progress is cached).":
        "Аудиоиндекс отменён — пока проанализировано %s файлов (прогресс сохранён в кэше).",
    "🧹  Checking which files are still on disk…":
        "🧹  Проверяем, какие файлы ещё на диске…",
    "🧱  Looking for ffmpeg and the AI backends…":
        "🧱  Ищем ffmpeg и ИИ-движки…",
    "🧱  Checking what this machine can build…":
        "🧱  Проверяем, что этот компьютер может построить…",
    "librosa is not installed, so tempo and timbre cannot be measured and similar-track search stays unavailable.\n"
    "\n"
    "Install it, then restart the app:\n"
    "    pip install librosa":
        "librosa не установлена, поэтому темп и тембр нельзя измерить, а поиск похожих треков недоступен.\n"
        "\n"
        "Установите её и перезапустите приложение:\n"
        "    pip install librosa",
    "Nothing on this computer can decode an MP3, so tempo and timbre cannot be measured and similar-track search stays unavailable.\n"
    "\n"
    "Install ffmpeg and make sure it is on PATH (not just next to the app), then restart.":
        "На этом компьютере нечем декодировать MP3, поэтому темп и тембр нельзя измерить, а поиск похожих треков недоступен.\n"
        "\n"
        "Установите ffmpeg и убедитесь, что он есть в PATH (а не только рядом с приложением), затем перезапустите.",
    "The audio decoder could not read %s, so the analysis would fail for every file. See the log for the error.":
        "Аудиодекодер не смог прочитать %s, поэтому анализ не удался бы ни для одного файла. Ошибка — в журнале.",
    "Nothing could be built for these, and nothing will be:":
        "Для этого ничего не удалось построить, и не удастся:",
    "Caches built for %s — with problems, see the log.":
        "Кэши построены для %s — с проблемами, см. журнал.",
    "Finished for %s, but not everything worked:":
        "Готово для %s, но не всё получилось:",
    "Ran: %s.": "Выполнено: %s.",
    "All caches built for %s.": "Все кэши построены для %s.",
    "All caches are built for %s.": "Все кэши для %s уже построены.",
    "Build all caches — librosa: analyzing %s files…":
        "Построить все кэши — librosa: анализ %s файлов…",
    "Build all caches — %s…": "Построить все кэши — %s…",
    "Build all caches — %s embeddings…": "Построить все кэши — эмбеддинги %s…",
    "mostly: %s": "в основном: %s",
    "%s: %s file(s) failed": "%s: не удалось обработать %s файл(ов)",
    ", %s cached": ", %s в кэше",
    "%s: %s file(s) skipped — not on disk any more":
        "%s: пропущено %s файл(ов) — их больше нет на диске",
    "Build all caches cancelled during %s — %s done so far (cached).":
        "Построение кэшей отменено на шаге %s — пока готово %s (в кэше).",
    "🎛  Both — plan and play": "🎛  Всё — планировать и играть",
    "The full app: build playlists at home, run them at the tournament.":
        "Полное приложение: составляйте плейлисты дома, запускайте их на турнире.",
    "📝  Planner only": "📝  Только планировщик",
    "Build and curate playlists. The tournament floor's playing panel, its timed play / announcements and the 🎛 cartwall stay hidden.":
        "Составлять и вести плейлисты. Панель воспроизведения для турнирного паркета, воспроизведение по времени / объявления и 🎛 Cartwall скрыты.",
    "▶  Player only": "▶  Только плеер",
    "Run prepared playlists at the venue. Everything that generates or checks a playlist stays hidden.":
        "Запускать готовые плейлисты на площадке. Всё, что создаёт или проверяет плейлист, скрыто.",
    "◧  Beside the playlists — at the head of the ▶ Playing panel":
        "◧  Рядом с плейлистами — в начале панели ▶ Воспроизведение",
    "The player card stands in the left panel, above the timed-play controls.":
        "Карточка плеера стоит в левой панели, над элементами воспроизведения по времени.",
    "▤  Above the playlists — one wide strip over the decks":
        "▤  Над плейлистами — одна широкая полоса над деками",
    "The same player, laid out along the width above the decks — the shape a DJ desk uses. It shows in ▶ Playing mode.":
        "Тот же плеер, растянутый по ширине над деками — как на DJ-пульте. Показывается в режиме ▶ Воспроизведение.",
    "🎬  FFmpeg — Qt's own engine (default)":
        "🎬  FFmpeg — собственный движок Qt (по умолчанию)",
    "🎬  FFmpeg — Qt's own engine": "🎬  FFmpeg — собственный движок Qt",
    "🪟  Windows Media Foundation — the OS's own":
        "🪟  Windows Media Foundation — движок операционной системы",
    "🔊  Automatic — whatever this system uses (default)":
        "🔊  Автоматически — то, что использует эта система (по умолчанию)",
    "☀  Light (default)": "☀  Светлая (по умолчанию)",
    "White decks, dark text: the look every colour in the app was picked for.":
        "Белые деки, тёмный текст: вид, под который подобран каждый цвет приложения.",
    "🌙  Dark": "🌙  Тёмная",
    "Platform looks": "Стили платформ",
    "Desk looks": "Стили пультов",
    "Modern looks": "Современные стили",
    "No preview picture for this theme.":
        "Для этой темы нет картинки предпросмотра.",
    "A look brings its own accent colour — this one is for Light and Dark.":
        "Стиль приносит свой акцентный цвет — этот действует для Светлой и Тёмной.",
    "Windows 11 · Light": "Windows 11 · Светлая",
    "Fluent: 4 px corners, Segoe UI Variable, the Windows blue and an accent line under the active field.":
        "Fluent: углы 4 px, Segoe UI Variable, синий Windows и акцентная линия под активным полем.",
    "Windows 11 · Dark": "Windows 11 · Тёмная",
    "Fluent in dark: the Windows 11 dark greys with the light blue accent.":
        "Fluent в тёмном: тёмно-серые тона Windows 11 со светло-синим акцентом.",
    "macOS · Light": "macOS · Светлая",
    "Aqua as of Sonoma: 6 px corners, a solid blue selection with white text and an accent ring around the active field.":
        "Aqua как в Sonoma: углы 6 px, насыщенно-синее выделение с белым текстом и акцентное кольцо вокруг активного поля.",
    "macOS · Dark": "macOS · Тёмная",
    "Aqua in dark mode: charcoal panes, grey keys, the bright system blue.":
        "Aqua в тёмном режиме: антрацитовые панели, серые клавиши, яркий системный синий.",
    "Linux GNOME · Light": "Linux GNOME · Светлая",
    "Adwaita: 6 px corners, flat grey buttons without a frame, the GNOME blue.":
        "Adwaita: углы 6 px, плоские серые кнопки без рамки, синий GNOME.",
    "Linux GNOME · Dark": "Linux GNOME · Тёмная",
    "Adwaita dark: soft charcoal, flat buttons, the GNOME blue.":
        "Adwaita тёмная: мягкий антрацит, плоские кнопки, синий GNOME.",
    "Console": "Консоль",
    "Graphite, keys lit from above like a mixing desk, a pressed key glows blue. Lettering in Bahnschrift.":
        "Графит, клавиши подсвечены сверху, как на микшерном пульте, нажатая клавиша светится синим. Шрифт Bahnschrift.",
    "Jet black with metal gradients and orange as the light: harder and higher in contrast, like a hardware controller in a dark hall.":
        "Угольно-чёрный с металлическими градиентами и оранжевым светом: жёстче и контрастнее, как аппаратный контроллер в тёмном зале.",
    "Flat night blue with cyan as the light: whatever is on gets a glowing rim instead of a fill. Rounder corners.":
        "Плоский ночной синий с голубым светом: включённое получает светящийся контур вместо заливки. Углы круглее.",
    "The bright desk: brushed aluminium, keys lit from above, orange as the accent. For daylight and bright halls.":
        "Светлый пульт: шлифованный алюминий, клавиши подсвечены сверху, оранжевый акцент. Для дневного света и светлых залов.",
    "Graphite": "Графит",
    "Calm neutral dark: near-white text on graphite, soft filled buttons with round corners, a clear blue. Easy on the eyes for a long evening.":
        "Спокойный нейтральный тёмный: почти белый текст на графите, мягкие залитые кнопки с круглыми углами, чистый синий. Бережёт глаза долгим вечером.",
    "Midnight": "Полночь",
    "Deep navy with a teal accent and pill-shaped buttons: modern and quiet, the text stays crisp against the dark blue.":
        "Глубокий тёмно-синий с бирюзовым акцентом и кнопками-таблетками: современно и спокойно, текст остаётся чётким на тёмно-синем.",
    "Dark with a violet accent: soft filled buttons, warm dark greys, light lavender for links and focus.":
        "Тёмная с фиолетовым акцентом: мягкие залитые кнопки, тёплые тёмно-серые тона, светлая лаванда для ссылок и фокуса.",
    "Paper": "Бумага",
    "Clean and bright: white panes, nearly black text, soft grey buttons with round corners and a strong blue. Crisp in daylight.":
        "Чисто и светло: белые панели, почти чёрный текст, мягкие серые кнопки с круглыми углами и насыщенный синий. Чётко при дневном свете.",
    "High contrast · Dark": "Высокий контраст · Тёмная",
    "Black and white with a yellow accent, 2 px frames and a yellow selection: readable from across the hall and in bright stage light.":
        "Чёрное и белое с жёлтым акцентом, рамки 2 px и жёлтое выделение: читается через весь зал и при ярком сценическом свете.",
    "High contrast · Light": "Высокий контраст · Светлая",
    "Black on white with a deep blue accent and 2 px frames: the most readable light look, also on a weak projector or laptop screen.":
        "Чёрное на белом с тёмно-синим акцентом и рамками 2 px: самый читаемый светлый стиль, в том числе на слабом проекторе или экране ноутбука.",
    "The same colours put through a lightness flip, so a warning stays red and the ▶ player panel — dark already — is left as it is.":
        "Те же цвета с инверсией яркости, чтобы предупреждение осталось красным, а панель плеера ▶ — и так тёмная — осталась как есть.",
    "  %s  —  pick a colour…": "  %s  —  выбрать цвет…",
    "Accent colour": "Акцентный цвет",
    "  ~%s left": "  осталось ~%s",
    "(%s errors)": "(%s ошибок)",
    ", %s errors": ", %s ошибок",
    "%s done — %s %s": "%s готово — %s %s",
    " (all were already cached)": " (всё уже было в кэше)",
    "%s cancelled — %s %s so far.": "%s отменено — пока %s %s.",
    "%s failed:\n"
    "%s":
        "%s не удалось:\n"
        "%s",
    "files cached": "файлов в кэше",
    "tracks measured": "треков измерено",
    "tracks probed": "треков проверено",
    "tracks analyzed": "треков проанализировано",
    "All %s files are already cached.\n"
    "\n"
    "Re-analyze the whole library anyway to refresh the measured tempo with the current method?":
        "Все %s файлов уже в кэше.\n"
        "\n"
        "Всё равно заново проанализировать всю библиотеку, чтобы обновить измеренный темп текущим методом?",
    "%s files will be re-analyzed (~%s min, cached afterwards).\n"
    "\n"
    "Run now?":
        "Будет заново проанализировано %s файлов (~%s мин, затем в кэше).\n"
        "\n"
        "Запустить сейчас?",
    "%s files need librosa analysis (~%s min, cached afterwards).\n"
    "\n"
    "Run now?":
        "%s файлам нужен анализ librosa (~%s мин, затем в кэше).\n"
        "\n"
        "Запустить сейчас?",
    "Audio analysis started — %s files…": "Аудиоанализ запущен — %s файлов…",
    "Analyze Audio (Timbre)": "Анализ аудио (тембр)",
    "Re-analyze All Audio": "Заново проанализировать всё аудио",
    "Measure the loudness of the whole library (%s tracks)?\n"
    "\n"
    "Already-measured tracks are skipped — only new ones are\n"
    "decoded (≈1 s each). You can cancel anytime; results so far\n"
    "are kept.":
        "Измерить громкость всей библиотеки (%s треков)?\n"
        "\n"
        "Уже измеренные треки пропускаются — декодируются только\n"
        "новые (≈1 с на трек). Отменить можно в любой момент;\n"
        "полученные результаты сохранятся.",
    "Probe the silent stretches of the whole library (%s tracks, %s not probed yet)?\n"
    "\n"
    "Already-probed tracks are skipped — only new ones are\n"
    "decoded (≈0.3 s each). You can cancel anytime; results so far\n"
    "are kept.":
        "Проверить тихие участки всей библиотеки (%s треков, %s ещё не проверено)?\n"
        "\n"
        "Уже проверенные треки пропускаются — декодируются только\n"
        "новые (≈0,3 с на трек). Отменить можно в любой момент;\n"
        "полученные результаты сохранятся.",
    "All %s tracks already have a measured vocal share.":
        "У всех %s треков уже измерена доля вокала.",
    "Separate the vocals of %s not-yet-measured tracks (~%s min)?\n"
    "\n"
    "Demucs actually extracts the singing from each track — slow\n"
    "(~7 s per track) but far more reliable than the heuristics.\n"
    "You can cancel anytime; results so far are kept.":
        "Отделить вокал у %s ещё не измеренных треков (~%s мин)?\n"
        "\n"
        "Demucs действительно извлекает пение из каждого трека — медленно\n"
        "(~7 с на трек), но гораздо надёжнее эвристик.\n"
        "Отменить можно в любой момент; полученные результаты сохранятся.",
    "Detect the highlights of every Paso Doble in the library (%s tracks)?\n"
    "\n"
    "Already-analyzed tracks are skipped — only new ones are\n"
    "decoded (a few seconds each). You can cancel anytime;\n"
    "results so far are kept.":
        "Найти кульминации каждого Пасодобля в библиотеке (%s треков)?\n"
        "\n"
        "Уже проанализированные треки пропускаются — декодируются только\n"
        "новые (несколько секунд на трек). Отменить можно в любой момент;\n"
        "полученные результаты сохранятся.",
    "Fresh mix:": "Доля новых:",
    "Set clock to": "Поставить часы на",
    "Draw tracks from": "Брать треки из",
    "Songs needed for:": "Нужно треков для:",
    "What to build": "Что создать",
    "Round Strategy": "Стратегия тура",
    "Middle of the round": "Середина тура",
    "Lower — T%s": "Нижний — T%s",
    "Middle — T%s": "Средний — T%s",
    "Upper — T%s": "Верхний — T%s",
    "Please wait": "Пожалуйста, подождите",
    "Failed.": "Не удалось.",
    "Add a page": "Добавить страницу",
    "Next page": "Следующая страница",
    "Previous page": "Предыдущая страница",
    "Keep all": "Оставить все",
    "Keep both": "Оставить оба",
    "Keep existing": "Оставить существующий",
    "No key": "Без клавиши",
    "Print / Export": "Печать / Экспорт",
    "USB export": "Экспорт на USB",
    "Duplicate titles": "Повторяющиеся названия",
    "Possible duplicate": "Возможный дубликат",
    "Check duplicates": "Проверить дубликаты",
    "Pad settings": "Настройки пэда",
    "Clear this pad": "Очистить этот пэд",
    "Columns in the library": "Столбцы библиотеки",
    "Columns in the track list": "Столбцы списка треков",
    "Open wishlists": "Открытые списки пожеланий",
    "Analyze PD highlights": "Анализ кульминаций PD",
    "Vocal + instr.": "Вокал + инстр.",
    "Use Timbre Similarity": "Использовать сходство тембра",
    "Load models": "Загрузить модели",
    "Copy to clipboard": "Копировать в буфер обмена",
    "Press the keys you want": "Нажмите нужные клавиши",
    "Click, then press the key that should do it": "Нажмите, затем нажмите клавишу, которая должна это делать",
    "Restore slot defaults": "Восстановить стандартные клавиши",
    "Back to %s…%s, leaving the pad keys alone":
        "Вернуть %s…%s, не трогая клавиши пэдов",
    "\n"
    "Key: %s":
        "\n"
        "Клавиша: %s",
    "\n"
    "⚠️ File not found":
        "\n"
        "⚠️ Файл не найден",
    "Remove this page": "Удалить эту страницу",
    "Remove this competition": "Удалить это соревнование",
    "Save all playlists": "Сохранить все плейлисты",
    "Save tournament day": "Сохранить турнирный день",
    "Clear all tournament-day playlists":
        "Очистить все плейлисты турнирного дня",
    "All dances": "Все танцы",
    "All classes": "Все классы",
    "All categories": "Все категории",
    "Added: all": "Добавлено: все",
    "Plays: all": "Сыграно: все",
    "Parse schedule": "Загрузить расписание",
    "Filter by the instrumental tag": "Фильтр по отметке «инструментал»",
    "Short dance names  (LW, SB)": "Короткие названия танцев  (LW, SB)",
    "Auto re-roll round on strategy change":
        "Перетасовать тур при смене стратегии",
    "Re-analyze tracks that already have highlights":
        "Заново анализировать треки, у которых уже есть кульминации",
    "An .m3u playlist file": "Файл плейлиста .m3u",
    "Focused playlist (current deck)": "Активный плейлист (текущий дек)",
    "Number of titles in this wishlist":
        "Количество треков в этом списке пожеланий",
    "Own looks": "Свои стили",
    "none yet — ＋ New look…": "пока нет — ＋ Новый стиль…",
    "＋  New look…": "＋  Новый стиль…",
    "A look of your own, starting as a copy of the selected one.":
        "Свой стиль, сначала копия выбранного.",
    "✎  Edit…": "✎  Изменить…",
    "🗑  Delete": "🗑  Удалить",
    "Import…": "Импорт…",
    "Add a look someone exported.":
        "Добавить стиль, который кто-то экспортировал.",
    "Export…": "Экспорт…",
    "Save the selected look of your own as a file, to pass it on.":
        "Сохранить выбранный свой стиль в файл, чтобы передать его.",
    "A look of your own, kept on this computer. ✎ Edit changes it, Export passes it on.":
        "Свой стиль, хранится на этом компьютере. ✎ Изменить меняет его, Экспорт передаёт.",
    "%s (own)": "%s (свой)",
    "Look not saved": "Стиль не сохранён",
    "The looks file could not be written. The log names the reason.":
        "Не удалось записать файл стилей. Причина указана в журнале.",
    "Delete look": "Удалить стиль",
    "Delete the look “%s”? This cannot be undone; an exported file of it stays.":
        "Удалить стиль «%s»? Это нельзя отменить; экспортированный файл с ним останется.",
    "Import a look": "Импортировать стиль",
    "Look not imported": "Стиль не импортирован",
    "This file holds no look the app can use:\n"
    "%s":
        "В этом файле нет стиля, который может использовать приложение:\n"
        "%s",
    "Export the look": "Экспортировать стиль",
    "Look not exported": "Стиль не экспортирован",
    "The file could not be written:\n"
    "%s":
        "Не удалось записать файл:\n"
        "%s",
    "🎨  Edit look": "🎨  Изменить стиль",
    "Family: %s. The details it shares with the built-in looks of that group stay: faders, checkboxes, headers.":
        "Семейство: %s. То, что он разделяет со встроенными стилями этой группы, остаётся: фейдеры, флажки, заголовки.",
    "Grounds": "Фоны",
    "Window": "Окно",
    "The ground of the main window and the dialogs.":
        "Фон главного окна и диалогов.",
    "Lists and fields": "Списки и поля",
    "Tables, lists and text fields.": "Таблицы, списки и текстовые поля.",
    "Every other row": "Каждая вторая строка",
    "The second row colour of a table.": "Второй цвет строк таблицы.",
    "Headers": "Заголовки",
    "Table headers and the menu bar.": "Заголовки таблиц и строка меню.",
    "The ground of a tooltip.": "Фон всплывающей подсказки.",
    "Buttons": "Кнопки",
    "Button face": "Поверхность кнопки",
    "A button at rest.": "Кнопка в покое.",
    "Under the mouse": "Под мышью",
    "A button the mouse is over.": "Кнопка под указателем мыши.",
    "Pressed": "Нажата",
    "A button held down.": "Удерживаемая кнопка.",
    "Light from above": "Свет сверху",
    "Set, a button fades from this colour down to its face, like a key on a mixing desk. Off, the face is flat.":
        "Если задан, кнопка переходит от этого цвета вниз к своей поверхности, как клавиша на микшерном пульте. Если выключен, поверхность ровная.",
    "Header light from above": "Свет сверху для заголовков",
    "The same fade for the table headers and the deck title strips.":
        "Тот же переход для заголовков таблиц и полос заголовков деков.",
    "Lines": "Линии",
    "Hairlines": "Тонкие линии",
    "Frames, the table grid and separators.":
        "Рамки, сетка таблицы и разделители.",
    "Outlines": "Контуры",
    "A control's frame and the scrollbar handle.":
        "Рамка элемента управления и ползунок полосы прокрутки.",
    "All ordinary text.": "Весь обычный текст.",
    "Dim text": "Бледный текст",
    "Disabled text, placeholders and side notes.":
        "Неактивный текст, заполнители и примечания.",
    "Accent": "Акцент",
    "The default button and a switched-on toggle.":
        "Кнопка по умолчанию и включённый переключатель.",
    "Text on the accent": "Текст на акценте",
    "The caption on an accent fill.": "Надпись на акцентной заливке.",
    "Accent as text": "Акцент как текст",
    "Links, focus rings and the round bands' lettering.":
        "Ссылки, рамки фокуса и надписи на полосах туров.",
    "Selection": "Выделение",
    "Selected row": "Выбранная строка",
    "The band of the selected row.": "Полоса выбранной строки.",
    "Text on the selection": "Текст на выделении",
    "The text in that band.": "Текст в этой полосе.",
    "Fade": "Переход",
    "off": "выкл.",
    "Shape and lettering": "Форма и шрифт",
    "Corners:": "Углы:",
    "Buttons:": "Кнопки:",
    "Tabs:": "Вкладки:",
    "Focus:": "Фокус:",
    "Font:": "Шрифт:",
    "Outlined": "С контуром",
    "Flat, no frame": "Плоские, без рамки",
    "Desk key, lit from above": "Клавиша пульта, подсветка сверху",
    "Dark, glowing rim when on": "Тёмные, светящийся край при включении",
    "Soft filled": "Мягкая заливка",
    "Pill, fully rounded": "Таблетка, полностью скруглённые",
    "2 px frame, high contrast": "Рамка 2 px, высокий контраст",
    "Underlined": "Подчёркнутые",
    "Segmented": "Сегментированные",
    "Desk keys": "Клавиши пульта",
    "Pills": "Таблетки",
    "Ring around the field": "Кольцо вокруг поля",
    "Line under the field": "Линия под полем",
    "Saved looks are kept on this computer. The app takes a changed look on its next start.":
        "Сохранённые стили хранятся на этом компьютере. Приложение применит изменённый стиль при следующем запуске.",
    "⚠ Hard to read:": "⚠ Плохо читается:",
    "✓ Every text reads clearly against its ground.":
        "✓ Весь текст хорошо выделяется на своём фоне.",
    "%s: %.1f : 1, should be at least %.1f":
        "%s: %.1f : 1, должно быть не меньше %.1f",
    "Text on lists": "Текст на списках",
    "Text on every other row": "Текст на каждой второй строке",
    "Text on the window": "Текст на окне",
    "Text on buttons": "Текст на кнопках",
    "Dim text on lists": "Бледный текст на списках",
    "Planning": "Планирование",
    "Playing": "Воспроизведение",
    "Group": "Группа",
    "Heat %d": "Заход %d",
    "▼  PRELIMINARY ROUND  (2 heats)": "▼  PRELIMINARY ROUND  (2 захода)",
    "Button": "Кнопка",
    "Switched on": "Включено",
    "Disabled": "Неактивно",
    "Search…": "Поиск…",
    "Ticked": "Отмечено",
    "Dim text: a hint, a placeholder.":
        "Бледный текст: подсказка, заполнитель.",
    "Welcome to DanceSport Planner & Player":
        "Добро пожаловать в DanceSport Planner & Player",
    "AI Song Suggestions (OpenRouter)": "ИИ-подсказки треков (OpenRouter)",
    "Previous session crashed": "Предыдущий сеанс завершился сбоем",
    "Settings — app mode, library paths & analysis":
        "Настройки — режим, пути библиотеки и анализ",
    "Settings — library paths, global search & analysis":
        "Настройки — пути библиотеки, глобальный поиск и анализ",
    "⌨  Keyboard shortcuts  (F1)": "⌨  Сочетания клавиш  (F1)",
    "⛶  Fullscreen  (F11)": "⛶  Полный экран  (F11)",
    "⛶  Exit Fullscreen  (F11)": "⛶  Выйти из полного экрана  (F11)",
    "⛶  Fullscreen clock: only the time (20:45:12), no date":
        "⛶  Часы в полноэкранном режиме: только время (20:45:12), без даты",
    "Shortcuts (F1), manual and about this app":
        "Сочетания клавиш (F1), руководство и о приложении",
    "📖  Manual": "📖  Руководство",
    "ℹ  About…": "ℹ  О программе…",
    "About": "О программе",
    "Project": "Проект",
    "Closing": "Закрытие",
    "🔉 Fading out the music…\nThe app closes in a moment.":
        "🔉 Музыка затихает…\nПриложение сейчас закроется.",
    "Music is playing": "Играет музыка",
    "Music is playing. Quit anyway and stop it?":
        "Играет музыка. Всё равно выйти и остановить её?",
    "Author": "Автор",
    "License": "Лицензия",
    "App icon": "Значок приложения",
    "Icons": "Значки",
    "Voices": "Голоса",
    "AI-generated, non-commercial use":
        "Создано ИИ, только некоммерческое использование",
    "Model": "Модель",
    "Libraries": "Библиотеки",
    "all licences": "все лицензии",
    "Which library should this index cover?":
        "Какую библиотеку должен охватывать этот индекс?",
    "What should go into the venue bundle?":
        "Что должно войти в пакет для площадки?",
    "Settings saved.": "Настройки сохранены.",
    "Database cleanup done.": "Очистка базы данных завершена.",
    "Loading library…": "Загрузка библиотеки…",
    "Loading music library…": "Загрузка музыкальной библиотеки…",
    "Library: loading…": "Библиотека: загрузка…",
    "Generating playlist…": "Создание плейлиста…",
    "Asking the model…": "Запрос к модели…",
    "Asking the model for a playlist…": "Запрос плейлиста у модели…",
    "Fetching the model list…": "Получение списка моделей…",
    "Cancelling…": "Отмена…",
    "Analysis failed.": "Анализ не удался.",
    "AI playlist failed.": "ИИ-плейлист не удался.",
    "AI playlist: nothing usable.": "ИИ-плейлист: ничего пригодного.",
    "Practice failed.": "Практика не удалась.",
    "Practice: no matching tracks.": "Практика: нет подходящих треков.",
    "Global index failed.": "Глобальный индекс не удался.",
    "Similar-track analysis failed.": "Анализ похожих треков не удался.",
    "Repository scan cancelled.": "Сканирование репозитория отменено.",
    "Import: no tracks detected": "Импорт: треки не распознаны",
    "No parseable suggestions returned.": "Не получено пригодных предложений.",
    "Could not fetch models (using fallback list).":
        "Не удалось получить модели (используется резервный список).",
    "Load the music library first.":
        "Сначала загрузите музыкальную библиотеку.",
    "Nothing to clear — all playlists are empty.":
        "Нечего очищать — все плейлисты пусты.",
    "Nothing to export — all playlists are empty.":
        "Нечего экспортировать — все плейлисты пусты.",
    "Nothing to save — all playlists are empty.":
        "Нечего сохранять — все плейлисты пусты.",
    "Nothing to save — the day decks are empty.":
        "Нечего сохранять — деки дня пусты.",
    "Nothing to save yet.": "Пока нечего сохранять.",
    "Nothing to undo yet": "Пока нечего отменять",
    "Nothing to redo": "Нечего повторять",
    "Undo: %s\n"
    "%s step(s) available  ·  Ctrl+Z":
        "Отменить: %s\n"
        "Доступно шагов: %s  ·  Ctrl+Z",
    "Redo: %s\n"
    "%s step(s) available  ·  Ctrl+Y":
        "Повторить: %s\n"
        "Доступно шагов: %s  ·  Ctrl+Y",
    "↶  Undo — %s": "↶  Отменить — %s",
    "↷  Redo — %s": "↷  Повторить — %s",
    "restored %s": "восстановлено: %s",
    "removed %s": "удалено: %s",
    "replaced %s → %s": "заменено: %s → %s",
    "moved %s": "перемещено: %s",
    "playlist rename": "переименование плейлиста",
    "deck layout change": "изменение раскладки деков",
    "view / settings change": "изменение вида / настроек",
    "“%s” and “%s”": "«%s» и «%s»",
    "%s tracks (“%s”, “%s”, …)": "%s треков («%s», «%s», …)",
    "No files added yet.": "Файлы ещё не добавлены.",
    "No song selected": "Трек не выбран",
    "No playing row found.": "Играющая строка не найдена.",
    "No dances for this class.": "Нет танцев для этого класса.",
    "No similar tracks found.": "Похожие треки не найдены.",
    "No similar tracks found for that file.":
        "Для этого файла похожие треки не найдены.",
    "No reference playlist yet.": "Эталонного плейлиста пока нет.",
    "No auto-advance pause is running to extend.":
        "Нет идущей паузы автоперехода, которую можно продлить.",
    "This wall has no pads yet.": "В этом Cartwall пока нет пэдов.",
    "Your wishlist is empty — add tracks to a wishlist first.":
        "Ваш список пожеланий пуст — сначала добавьте в него треки.",
    "Saved — it takes effect the next time you start the app.":
        "Сохранено — вступит в силу при следующем запуске приложения.",
    "Then restart the app — nothing else to configure.":
        "Затем перезапустите приложение — больше ничего настраивать не нужно.",
    "ffmpeg not found": "ffmpeg не найден",
    "In a terminal:":
        "В терминале:",
    "…no Homebrew yet? That line first:":
        "…ещё нет Homebrew? Сначала эта строка:",
    "…or with Homebrew, on any distro:":
        "…или через Homebrew, в любом дистрибутиве:",
    "…or download a build from <a href='https://www.gyan.dev/ffmpeg/builds/'>gyan.dev/ffmpeg/builds</a> and drop <code>ffmpeg.exe</code> into this app's folder.":
        "…или скачайте сборку с <a href='https://www.gyan.dev/ffmpeg/builds/'>gyan.dev/ffmpeg/builds</a> и положите <code>ffmpeg.exe</code> в папку этого приложения.",
    "(multimedia unavailable)": "(мультимедиа недоступно)",
    "Play a title first — then TSO sets its heat tempo.":
        "Сначала запустите трек — тогда TSO задаст темп его захода.",
    "This title has no detected tempo — can't equalize.":
        "Для этого трека темп не определён — выровнять нельзя.",
    "The fader can't reach that tempo for this title.":
        "Фейдер не достигает этого темпа для этого трека.",
    "Preview player disabled — re-enable it in ⚙ Settings.":
        "Плеер предпрослушивания отключён — включите его снова в ⚙ Настройках.",
    "Pick a playlist again to choose a different track":
        "Снова выберите плейлист, чтобы взять другой трек",
    "Pick “Replace…” again to choose a different track":
        "Снова выберите «Заменить…», чтобы взять другой трек",
    "%s: strategy set to %s — ↺ a song or dance to apply":
        "%s: стратегия установлена на %s — ↺ на треке или танце применяет её",
    "%s: %s · %s — ↺ a song or dance to apply":
        "%s: %s · %s — ↺ на треке или танце применяет её",
    "↻ %s re-rolled — %s": "↻ %s перетасовано — %s",
    "↻ %s re-rolled — %s · %s": "↻ %s перетасовано — %s · %s",
    "Re-roll failed: %s": "Не удалось перетасовать: %s",
    "this comp": "это соревнование",
    "all playlists": "все плейлисты",
    "Listen to this track": "Прослушать этот трек",
    "Play / stop this track": "Воспроизвести / остановить этот трек",
    "Play / stop this file": "Воспроизвести / остановить этот файл",
    "Play / stop the base track these results are based on":
        "Воспроизвести / остановить исходный трек этих результатов",
    "Listen to this pad while you set its level":
        "Слушать этот пэд, пока настраиваете его уровень",
    "Jump back to the start (0:00) of this track":
        "Вернуться к началу (0:00) этого трека",
    "Click to collapse / expand": "Щёлкните, чтобы свернуть / развернуть",
    "Click to focus · right-click or double-click to rename":
        "Щелчок — сделать активным · правый или двойной щелчок — переименовать",
    "Double-click to rename this page":
        "Двойной щелчок переименовывает эту страницу",
    "Double-click to type a value": "Двойной щелчок, чтобы ввести значение",
    "Drag here to move": "Тяните здесь, чтобы переместить",
    "Drag here to move the preview player":
        "Тяните здесь, чтобы переместить плеер предпрослушивания",
    "Unfold this playlist": "Развернуть этот плейлист",
    "Fold the library pane to its header":
        "Свернуть панель библиотеки до заголовка",
    "%s — folded.  Click to unfold.":
        "%s — свёрнуто.  Щёлкните, чтобы развернуть.",
    "%s — folded.  Click to open.": "%s — свёрнуто.  Щёлкните, чтобы открыть.",
    "Open the %s panel.": "Открыть панель %s.",
    "Compact the %s panel to its header tab —\n"
    "click the tab (or this arrow) to open it again.":
        "Свернуть панель %s до вкладки заголовка —\n"
        "щелчок по вкладке (или этой стрелке) откроет её снова.",
    "Close the preview and stop playback  (Ctrl+X)":
        "Закрыть предпрослушивание и остановить воспроизведение  (Ctrl+X)",
    "Close the tournament day — clears all 📅 day decks":
        "Закрыть турнирный день — очищает все 📅 деки дня",
    "Back to this slot's default key":
        "Вернуть стандартную клавишу этой ячейки",
    "Export or import this wall":
        "Экспортировать или импортировать этот Cartwall",
    "Duck to 20 % / back to full": "Приглушить до 20 % / вернуть на полную",
    "🔉  Duck to:": "🔉  Приглушать до:",
    "How loud everything stays while 🔉 Duck is pressed on the player\ncard, the mini player or the presenter screen: low enough to talk\nover, loud enough to keep the floor moving. 0 % is silence.":
        "Насколько громко всё звучит, пока нажата 🔉 на карточке плеера,\nв мини-плеере или на экране презентации: достаточно тихо, чтобы\nговорить поверх, и достаточно громко, чтобы зал продолжал танцевать.\n0 % — тишина.",
    "🎵  When the main player starts a title:":
        "🎵  При старте трека в основном плеере:",
    "🎛 Cartwall":
        "🎛 Картволл",
    "<b>🎛 Cartwall</b> — what the pads do to the music, and what every pad follows unless it was given its own.":
        "<b>🎛 Картволл</b> — что пэды делают с музыкой и что следует каждый пэд, если у него нет своей настройки.",
    "🎛  All pads":
        "🎛  Все пэды",
    "🎶  Pads set to 🎶 Background":
        "🎶  Пэды в режиме 🎶 Фон",
    "Tapped again or ⏹, a background pad fades out like every other pad (⏱ above).":
        "При повторном нажатии или ⏹ фоновый пэд затухает, как и любой другой пэд (⏱ выше).",
    "⏱  Tapped again or ⏹ — fade the pad out over:":
        "⏱  Повторное нажатие или ⏹ — затухание пэда за:",
    "How long a pad takes to let go when it is tapped again or ⏹\nstops the wall. A pad can override this in its own settings.":
        "Сколько затухает пэд, когда его нажимают снова или ⏹\nостанавливает картволл. Пэд может изменить это в своих настройках.",
    "🔉  Ticking 🎶 Background sets the pad's volume to:":
        "🔉  Отметка 🎶 Фон ставит громкость пэда на:",
    "A bed at full volume is as loud as the dance music it fills in\nfor. Pads already set to 🎶 Background keep their own volume.":
        "Фон на полной громкости звучит так же громко, как танцевальная музыка,\nпаузу которой он заполняет. Пэды, уже отмеченные как 🎶 Фон, сохраняют свою громкость.",
    "▶  When fired — fade the pad in over:":
        "▶  При запуске — нарастание пэда за:",
    "How long a 🎛 cartwall pad set to 🎶 Background takes to come\nup from silence when it is fired. 0 s starts it at full volume.":
        "Сколько времени пэду 🎛 картволла с режимом 🎶 Фон нужно, чтобы\nнарасти из тишины при запуске. 0 s запускает его на полной громкости.",
    "🌙  …fading the pad out over:":
        "🌙  …пэд затихает за:",
    "How long a 🎛 cartwall pad set to 🎶 Background takes to go\nsilent once a title starts.":
        "Сколько времени пэду 🎛 картволла с режимом 🎶 Фон нужно, чтобы\nзатихнуть, когда начинается трек.",
    "⏳  When the main player stops — wait:":
        "⏳  Когда основной плеер остановился — ждать:",
    "How long the main player has to stay stopped before a 🎛 cartwall\npad set to 🎶 Background fades back in.\n\nBetween two titles the deck stops for a moment. Without a wait,\nthe bed would swell up in every such gap and dip again as soon as\nthe next title starts. A title starting during the wait keeps the\nbed down.\n\nThere is no wait when a title starts: the bed gets out of the way\nat once, so it never plays over the first notes.\n\n0 s brings it back the moment the music stops, gaps included.\nStandard 0.3 s; much longer feels as if the bed lags behind.":
        "Сколько основной плеер должен стоять, прежде чем пэд 🎛 картволла\nс режимом 🎶 Фон снова нарастёт.\n\nМежду двумя треками дека на мгновение останавливается. Без ожидания\nфон нарастал бы в каждой такой паузе и снова уходил бы вниз со\nследующим треком. Если трек начнётся во время ожидания, фон\nостанется приглушённым.\n\nПри старте трека ожидания нет: фон сразу уступает место и никогда\nне звучит поверх первых нот.\n\n0 s возвращает его сразу, как музыка остановилась, в том числе в паузах.\nСтандарт 0,3 s; намного дольше кажется, что фон запаздывает.",
    "🌅  …then fade the pad back in over:":
        "🌅  …затем пэд возвращается за:",
    "How long a 🎛 cartwall pad set to 🎶 Background takes to come\nback up to its full volume once the music stops.":
        "Сколько времени пэду 🎛 картволла с режимом 🎶 Фон нужно, чтобы\nвернуться к полной громкости, когда музыка стихает.",
    "🖌  Default wall colour:":
        "🖌  Цвет картволла по умолчанию:",
    "The wall's default colour: every pad without a colour of its own\n(🎨 Colour ▸ Wall default) shows it. A pad given its own keeps it.":
        "Цвет картволла по умолчанию: его показывает каждый пэд без своего цвета\n(🎨 Цвет ▸ По умолчанию картволла). Пэд со своим цветом его сохраняет.",
    "Mute and keep playing":
        "Приглушить и играть дальше",
    "Pause":
        "Пауза",
    "What a 🎛 cartwall pad set to 🎶 Background does once the music\nstarts.\n\nMute and keep playing: it runs on silently under the title and\nfades back in when the music stops.\nPause: it holds where it was and carries on from there when\nthe music stops.":
        "Что делает пэд 🎛 картволла с режимом 🎶 Фон, когда начинается\nмузыка.\n\nПриглушить и играть дальше: он беззвучно играет под треком и\nплавно возвращается, когда музыка стихает.\nПауза: он замирает на месте и продолжает оттуда, когда\nмузыка стихает.",
    "🎶  Background: pause while a title plays":
        "🎶  Фон: пауза, пока играет трек",
    "The other way round from 🔈: a title starting on the main\nplayer pauses this pad, and it carries on from where it was\nwhen the music stops.\n(⚙ Settings → 🎛 Cartwall → 🎶 Background pads)":
        "Наоборот к 🔈: когда в основном плеере стартует трек,\nэтот пэд встаёт на паузу и продолжает с того же места,\nкогда музыка стихает.\n(⚙ Настройки → 🎛 Картволл → 🎶 Фоновые пэды)",
    "🔈  While a 🔈 pad plays, the music ducks to:":
        "🔈  Пока играет пэд 🔈, музыка приглушается до:",
    "How loud the music stays while a 🎛 cartwall pad set to 🔈 pull\nthe music down plays, in percent of its volume like 🔉 Duck to.\n10 % is about −20 dB: a fanfare cuts through. 30 % (about −10 dB)\nonly sits the music back. 0 % is silence.":
        "Насколько громко звучит музыка, пока играет пэд 🎛 картволла с\n🔈 приглушением музыки, в процентах её громкости, как у 🔉 Приглушать до.\n10 % — это около −20 dB: фанфары пробиваются. 30 % (около −10 dB)\nлишь отодвигает музыку. 0 % — тишина.",
    "A duck, here or a pad's on the 🎛 Cartwall tab, is a percentage of the music's volume, not of its loudness: 50 % ≈ −6 dB, 30 % ≈ −10 dB (sounds about half as loud), 20 % ≈ −14 dB, 10 % ≈ −20 dB.":
        "Приглушение, здесь или у пэда на вкладке 🎛 Cartwall, — процент от громкости музыки, а не от её воспринимаемой громкости: 50 % ≈ −6 dB, 30 % ≈ −10 dB (звучит примерно вдвое тише), 20 % ≈ −14 dB, 10 % ≈ −20 dB.",
    "🌅  Fade each title in over:":
        "🌅  Плавно вводить каждый трек за:",
    "The big player starts every title at silence and brings it up\nover these seconds of music. Not a title a 🔀 crossfade brings in,\nwhich has its own ramp. Couples start on the first downbeat, so\nleave it off for a competition. 0 = off.":
        "Большой плеер начинает каждый трек с тишины и поднимает его\nза эти секунды музыки. Кроме трека, который вводит 🔀\nкроссфейд, — у него своя рампа. Пары начинают с первой доли,\nпоэтому на турнире оставьте выключенным. 0 = выкл.",
    "⏩  Start each title this far in:":
        "⏩  Начинать каждый трек с:",
    "The big player skips the first seconds of every title. They do\nnot count against the play length. A title picked up where it\nwas left starts there instead, and a silent intro is still\nskipped on top. Cuts the same seconds from every title. 0 = off.":
        "Большой плеер пропускает первые секунды каждого трека. Они не\nвходят в длительность. Трек, продолженный с места остановки,\nначинается оттуда, а тихое вступление пропускается сверх того.\nСрезает одни и те же секунды с каждого трека. 0 = выкл.",
    "Reset the tempo to ±0 % (or double-click the fader)":
        "Сбросить темп на ±0 % (или двойной щелчок по фейдеру)",
    "Volume adjustment of this track by Equalize volume (R128)":
        "Поправка громкости этого трека функцией «Выровнять громкость» (R128)",
    "When this file was created in the library":
        "Когда этот файл появился в библиотеке",
    "Replace via the similar-tracks picker":
        "Заменить через выбор похожих треков",
    "Put the shipped rule set back.": "Вернуть поставляемый свод правил.",
    "Put the whole transcript on the clipboard.":
        "Скопировать весь диалог в буфер обмена.",
    "Esc closes  ·  double-click leaves full screen":
        "Esc закрывает  ·  двойной щелчок выходит из полноэкранного режима",
    "Pick a length or type one: m:ss, seconds, or 'full'":
        "Выберите длительность или введите: м:сс, секунды или 'полностью'",
    "%s — its own length":
        "%s — своя длительность",
    "This dance has its own play length in the 🏆 tournament set\n(⚙ Settings → 🎛 Play sets). − / + and typing change it there.":
        "У этого танца своя длительность в 🏆 турнирном наборе\n(⚙ Настройки → 🎛 Наборы воспроизведения). − / + и ввод меняют её там.",
    "<b>⏱ Per dance</b> — a dance given a length of its own is cut there instead, as long as a list plays this set's length. The ▶ Playing panel names the dance under its length.":
        "<b>⏱ По танцам</b> — танец со своей длительностью обрезается на ней, пока список играет длительность этого набора. Панель ▶ Воспроизведение называет танец под его длительностью.",
    "— the set's length":
        "— длительность набора",
    "⏱  Lengths:":
        "⏱  Длительности:",
    "Per dance — the standard":
        "По танцам — стандарт",
    "Per round — overrides it":
        "По раундам — заменяет его",
    "Which lengths the list below shows. The per-dance ones are the standard; a round's own lengths override them in that kind of round. Both count, whichever is on screen.":
        "Какие длительности показывает список ниже. Длительности по танцам — стандарт; собственные длительности раунда заменяют их в этом виде раунда. Действуют обе, какая бы ни была на экране.",
    "The kind of round whose lengths the list shows. Every intermediate round shares one.":
        "Вид раунда, длительности которого показывает список. Все промежуточные раунды делят одну.",
    "<b>⏱ Per round</b> — the lengths of one kind of round, every heat of it alike, on top of the per-dance ones. Left on “— the dance's length”, a dance runs its per-dance length in that round. One setting covers every intermediate round.":
        "<b>⏱ По раундам</b> — длительности одного вида раунда, одинаковые в каждом заходе, поверх длительностей по танцам. Оставленный на «— длительность танца», танец идёт в этом раунде со своей длительностью по танцам. Одна настройка действует для каждого промежуточного раунда.",
    "after highlight %d":
        "после кульминации %d",
    "Full, or stop after a highlight — the same as 🐂 Paso Doble: stop after highlight above.":
        "Полностью или стоп после кульминации — то же, что 🐂 Пасодобль: стоп после кульминации выше.",
    "Full, or stop after a highlight in this kind of round — a final in full, a Vorrunde after the 2nd.":
        "Полностью или стоп после кульминации в раундах этого типа — финал полностью, первый раунд после 2-й.",
    "— the dance's length":
        "— длительность танца",
    "m:ss, seconds, or 'full' — Enter to keep, Esc to abandon":
        "м:сс, секунды или 'полностью' — Enter сохраняет, Esc отменяет",
    "full — to each title's own end":
        "полностью — до собственного конца каждого трека",
    "full": "полностью",
    "🎯  no marks — scrub to a crash and mark it":
        "🎯  нет меток — перемотайте к удару и отметьте его",
    "“Proven” = songs in any of your playlists · “New” = in none.":
        "«Проверенные» = треки из любого вашего плейлиста · «Новые» = ни из одного.",
    "e.g. a song title, mood, or leave blank":
        "напр. название трека, настроение — или оставьте пустым",
    "API base URL:": "Базовый URL API:",
    "API key  (free OpenRouter key from openrouter.ai/keys):":
        "Ключ API  (бесплатный ключ OpenRouter на openrouter.ai/keys):",
    "Drag in playlists / files…": "Перетащите плейлисты / файлы…",
    "Drop .m3u playlists or audio files here, or click to browse":
        "Перетащите сюда плейлисты .m3u или аудиофайлы или щёлкните для выбора",
    "Drop an audio file here, or click to browse":
        "Перетащите сюда аудиофайл или щёлкните для выбора",
    "Drop saved .m3u playlists here, or click to browse":
        "Перетащите сюда сохранённые плейлисты .m3u или щёлкните для выбора",
    "Drop playlists above to check them.":
        "Перетащите плейлисты наверх, чтобы проверить их.",
    "Drop some files above to check them.":
        "Перетащите файлы наверх, чтобы проверить их.",
    "Saved playlists dragged in (.m3u)…":
        "Перетащенные сохранённые плейлисты (.m3u)…",
    "Choose an .m3u file…": "Выбрать файл .m3u…",
    "Browse…": "Обзор…",
    "Add…": "Добавить…",
    "Build / refresh…": "Построить / обновить…",
    "  Pick a colour…": "  Выбрать цвет…",
    "↑ resolved above": "↑ решено выше",
    "— Latin —": "— Латина —",
    "⚙  Settings": "⚙  Настройки",
    "⚗ Analysis": "⚗ Анализ",
    "🎨 Look": "🎨 Внешний вид",
    "⚙ General": "⚙ Общие",
    "📁 Paths": "📁 Пути",
    "🔊 Sound && player": "🔊 Звук && плеер",
    "📁  New folder…": "📁  Новая папка…",
    "⌨  Shortcuts…": "⌨  Сочетания клавиш…",
    "⚙  Cartwall settings…": "⚙  Настройки Cartwall…",
    "❔  Shortcuts": "❔  Сочетания клавиш",
    "▶  Playing": "▶  Воспроизведение",
    "▶  Playing mode": "▶  Режим воспроизведения",
    "▶  Load onto the focused deck": "▶  Загрузить в активный дек",
    "▴  Fold decks": "▴  Деки",
    "⊟  Collapse all": "⊟  Свернуть",
    "⏹  Stop all": "⏹  Остановить всё",
    "⏸  Auto-advance…": "⏸  Автопереход…",
    "⏱ calculating…": "⏱ вычисляется…",
    "⏳  Comparing…": "⏳  Сравнение…",
    "⚡  Generate Playlist": "⚡  Создать плейлист",
    "✅  Apply": "✅  Применить",
    "✅  Keep": "✅  Оставить",
    "✅  Keep all": "✅  Оставить все",
    "✅  Use this track as replacement": "✅  Взять этот трек для замены",
    "✅  No duplicate songs across your open playlist(s).":
        "✅  В открытых плейлистах нет повторяющихся треков.",
    "✎  Rename…": "✎  Переименовать…",
    "✏  Rename": "✏  Переименовать",
    "📅  New tournament day…": "📅  Новый турнирный день…",
    "✏️  Rename tab…": "✏️  Переименовать вкладку…",
    "✏️  Edit highlights": "✏️  Изменить кульминации",
    "✏  Editing — pads do not play": "✏  Редактирование — пэды не играют",
    "✕  Close tournament day": "✕  Закрыть турнирный день",
    "✦  Only never played": "✦  Только никогда не игравшие",
    "✦ Never played": "✦ Никогда не играл",
    "➕  Add": "➕  Добавить",
    "➕  Add a heat to this round": "➕  Добавить заход в этот тур",
    "➕  Add files…": "➕  Добавить файлы…",
    "➕  Both": "➕  Оба",
    "➕ Add competition": "➕ Добавить соревнование",
    "➖  Remove selected": "➖  Убрать выбранное",
    "＋  Add playlists…": "＋  Добавить плейлисты…",
    "⬆  Move backup up into this empty slot":
        "⬆  Поднять запасной в это свободное место",
    "⇅  Swap these two titles\tAlt+S":
        "⇅  Поменять местами эти два трека\tAlt+S",
    "♊  Remove duplicate titles in this list":
        "♊  Убрать повторяющиеся треки из этого списка",
    "⭐  Favorites": "⭐  Избранное",
    "⭐  Favorites library": "⭐  Избранная библиотека",
    "🎯  Favorites library": "🎯  Избранная библиотека",
    "⭐  Open wishlists": "⭐  Открытые списки пожеланий",
    "⭐  Only tracks in my wishlist(s)":
        "⭐  Только треки из моих списков пожеланий",
    "⭐  Find similar (in my wishlist only)":
        "⭐  Найти похожие (только в моём списке пожеланий)",
    "⭐  Find similar in wishlist (run Audio Analysis first)":
        "⭐  Похожие в списке пожеланий (сначала запустите аудиоанализ)",
    "⭐  Find similar in wishlist (wishlist is empty)":
        "⭐  Похожие в списке пожеланий (список пожеланий пуст)",
    "🌱  Find similar (never played)": "🌱  Найти похожие (никогда не игравшие)",
    "🌱  Find similar, never played (run Audio Analysis first)":
        "🌱  Похожие, никогда не игравшие (сначала запустите аудиоанализ)",
    "🌱  Freshness: all tracks": "🌱  Новизна: все треки",
    "🔎  Find similar tracks": "🔎  Найти похожие треки",
    "🔎  Find similar (run Audio Analysis first)":
        "🔎  Найти похожие (сначала запустите аудиоанализ)",
    "🔍  Compare": "🔍  Сравнить",
    "🔍  Filter title / artist / comment tag…":
        "🔍  Фильтр по названию / исполнителю / комментарию…",
    "🔍  Find a title in this list…\tCtrl+F":
        "🔍  Найти трек в этом списке…\tCtrl+F",
    "🆕 Last 30 days": "🆕 Последние 30 дней",
    "🆕 Last 90 days": "🆕 Последние 90 дней",
    "🆕 Last 12 months": "🆕 Последние 12 месяцев",
    "🆕 Last 18 months": "🆕 Последние 18 месяцев",
    "🆕 Unplanned": "🆕 Не запланированные",
    "📅  Only not since 1 y": "📅  Только не игравшие больше года",
    "📅 Not since 1 y": "📅 Не играл больше года",
    "📅  Day plan": "📅  План дня",
    "📅 Plan tournament day": "📅 Спланировать турнирный день",
    "📅 Tournament day": "📅 Турнирный день",
    "📅 Tournament day closed.": "📅 Турнирный день закрыт.",
    "📜  Find planned before": "📜  Найти запланированные ранее",
    "📜  Find planned before (load library first)":
        "📜  Найти запланированные ранее (сначала загрузите библиотеку)",
    "📜  Re-learn playlist popularity…":
        "📜  Заново изучить популярность плейлистов…",
    "📚  Library": "📚  Библиотека",
    "📚  Show never-played tracks": "📚  Показать никогда не игравшие треки",
    "📋  Copy": "📋  Копировать",
    "📋  Copy file path": "📋  Копировать путь к файлу",
    "📋  Copy file path (unavailable)":
        "📋  Копировать путь к файлу (недоступно)",
    "📋  Copy file path (not in your library)":
        "📋  Копировать путь к файлу (нет в вашей библиотеке)",
    "📋  Based on my playlist history (tracks I play together)":
        "📋  По истории моих плейлистов (треки, которые я ставлю вместе)",
    "📝  Copy details": "📝  Копировать подробности",
    "📝  Planning": "📝  Планирование",
    "📝  Wish list — the titles below, in that order":
        "📝  Список пожеланий — треки ниже, в этом порядке",
    "📂  Open folder": "📂  Открыть папку",
    "📂  Show in Explorer": "📂  Показать в Проводнике",
    "📂  Show in Explorer (unavailable)":
        "📂  Показать в Проводнике (недоступно)",
    "📂  Import M3U…": "📂  Импорт M3U…",
    "📂  Add a folder of playlists…": "📂  Добавить папку с плейлистами…",
    "📂  Import — track paths": "📂  Импорт — пути треков",
    "📂  Drag files in": "📂  Перетащите файлы",
    "📂  Assign files…": "📂  Назначить файлы…",
    "📂  An .m3u playlist file": "📂  Файл плейлиста .m3u",
    "📂  Drop saved .m3u playlists here, or click to browse":
        "📂  Перетащите сюда сохранённые плейлисты .m3u или щёлкните для выбора",
    "📄  All pads on one page": "📄  Все пэды на одной странице",
    "📊  Analyze loudness (R128)…": "📊  Анализ громкости (R128)…",
    "📊  Library gaps…": "📊  Пробелы в библиотеке…",
    "📊 Library gaps": "📊 Пробелы в библиотеке",
    "📤  Export wall…": "📤  Экспорт Cartwall…",
    "📥  Import wall…": "📥  Импорт Cartwall…",
    "📌  Save state": "📌  Состояние",
    "📌 Cartwall docked": "📌 Cartwall закреплён",
    "💾  Save M3U": "💾  Сохранить M3U",
    "💾  Save as M3U…": "💾  Сохранить как M3U…",
    "💾  Save all": "💾  Сохранить",
    "💾  Save all competition M3Us": "💾  Сохранить все M3U соревнований",
    "💾  Save all playlists as M3U": "💾  Сохранить все плейлисты как M3U",
    "🏆  Save all and add to Tournaments":
        "🏆  Сохранить всё и добавить в «Турниры»",
    "🏆  Save and add to Tournaments…": "🏆  Сохранить и добавить в «Турниры»…",
    "🏆 Saved and added %d playlist to Tournaments":
        "🏆 Сохранено, добавлено в «Турниры» плейлистов: %d",
    "🏆 Saved and added %d playlists to Tournaments":
        "🏆 Сохранено, добавлено в «Турниры» плейлистов: %d",
    "🏆 Saved — already in Tournaments": "🏆 Сохранено — уже есть в «Турнирах»",
    "🔁  Check duplicates": "🔁  Проверить дубликаты",
    "🔁  Endless repeat": "🔁  Бесконечный повтор",
    "🔁  Replace…": "🔁  Заменить…",
    "🔁  Reset all replacement marks": "🔁  Сбросить все отметки замены",
    "🔇  Probe silences…": "🔇  Проверить тишину…",
    "🔇 No audio backend — the cartwall cannot play here.":
        "🔇 Нет аудиобэкенда — Cartwall не может здесь играть.",
    "🔈  Pull the music down while this pad plays":
        "🔈  Приглушать музыку, пока играет этот пэд",
    "S  Stop the other pads when this one starts":
        "S  Останавливать другие пэды при запуске этого",
    "Every other running pad fades out as this one starts —\n"
    "for an anthem or a winners' fanfare that needs the room.":
        "Все остальные играющие пэды затухают, когда стартует этот —\n"
        "для гимна или фанфар победителям, которым нужна тишина.",
    "🎶  Background: dip under the music while a title plays":
        "🎶  Фон: уходить под музыку, пока играет трек",
    "The other way round from 🔈: this pad goes silent while the\n"
    "main player plays and comes back up in the pauses.":
        "Наоборот к 🔈: этот пэд замолкает, пока играет\n"
        "основной плеер, и возвращается в паузах.",
    "🔈 No announcement recordings found for this voice.":
        "🔈 Для этого голоса не найдено записей объявлений.",
    "🖥  Presenter": "🖥  Презентация",
    "🖥  Presenter — DanceSport Player": "🖥  Презентация — DanceSport Player",
    "🕒 Timetable — presenter screen": "🕒 Расписание — экран презентации",
    "✖  Remove": "✖  Удалить",
    "🖨  Print": "🖨  Печать",
    "🖨  Export PDF": "🖨  Экспорт в PDF",
    "🗑  Clear": "🗑  Очистить",
    "🗑  Remove": "🗑  Удалить",
    "🗑  Remove this title (keep slot)":
        "🗑  Удалить этот трек (место остаётся)",
    "🗑  Remove %d selected titles (keep slots)":
        "🗑  Удалить выбранные треки: %d (места остаются)",
    "🗑  Remove this title": "🗑  Удалить этот трек",
    "🗑  Remove %d selected titles": "🗑  Удалить выбранные треки: %d",
    "🗑  Remove from tree": "🗑  Удалить из дерева",
    "🗑  Remove from wishlist": "🗑  Удалить из списка пожеланий",
    "🗑  Remove this backup\tCtrl+Del": "🗑  Удалить этот запасной\tCtrl+Del",
    "🗑  Remove this empty slot": "🗑  Удалить это пустое место",
    "🗑  Remove this heat (all dances)\tCtrl+Del":
        "🗑  Удалить этот заход (все танцы)\tCtrl+Del",
    "🗑  Remove this round (all heats)": "🗑  Удалить этот тур (все заходы)",
    "🗜  Compact": "🗜  Компактно",
    "🚫  No groups": "🚫  Без групп",
    "🔢  Numbers": "🔢  Номера",
    "🧹  Clear all": "🧹  Очистить",
    "🧹  Clear all playlists": "🧹  Очистить все плейлисты",
    "🧹  Empty this playlist": "🧹  Очистить этот плейлист",
    "🧹  Clean up database…": "🧹  Очистить базу данных…",
    "🧹  Export unused": "🧹  Экспорт неиспользуемых",
    "🧹  Reference base": "🧹  Эталонная база",
    "🧹  Remove": "🧹  Удалить",
    "🧹  Remove tracks already in a playlist":
        "🧹  Удалить треки, которые уже есть в плейлисте",
    "🧹 Cleared all playlists.": "🧹 Все плейлисты очищены.",
    "🧹 Tournament-day playlists cleared.":
        "🧹 Плейлисты турнирного дня очищены.",
    "🧳  USB export": "🧳  USB-экспорт",
    "🧳 USB export": "🧳 Экспорт на USB",
    "🧳 USB export aborted — incomplete bundle removed.":
        "🧳 Экспорт на USB прерван — неполный пакет удалён.",
    "🧭  Fix paths": "🧭  Исправить пути",
    "🧭  Fix (overwrite)": "🧭  Исправить (перезаписать)",
    "🧭  Fix (swap in playlists)": "🧭  Исправить (заменить в плейлистах)",
    "🧱  Build ALL caches…": "🧱  Построить ВСЕ кэши…",
    "🧠  Rebuild index…": "🧠  Перестроить индекс…",
    "🤖  AI Playlist…": "🤖  ИИ-плейлист…",
    "🤖  AI playlist": "🤖  ИИ-плейлист",
    "🤖  Build": "🤖  Создать",
    "🤖  Get Suggestions": "🤖  Получить предложения",
    "🤖  Conversation with the model": "🤖  Диалог с моделью",
    "🤸  Practice / party playlist": "🤸  Плейлист для практики / вечеринки",
    "🎉  Party set": "🎉  Сет для вечеринки",
    "🎉  Party playlist (alternating 3-dance rounds, all dances)":
        "🎉  Плейлист для вечеринки (чередующиеся туры по 3 танца, все танцы)",
    "🏆  Tournaments": "🏆  Турниры",
    "🏆  Tournament set": "🏆  Турнирный сет",
    "🏆 Tournament only": "🏆 Только турнир",
    "🏷  Re-read MP3 tags": "🏷  Перечитать теги MP3",
    "🏷  Re-read MP3 tags (unavailable)": "🏷  Перечитать теги MP3 (недоступно)",
    "🐂  Analyze PD highlights…": "🐂  Анализ кульминаций PD…",
    "🎯  Mark highlight now": "🎯  Отметить кульминацию сейчас",
    "🎯 Highlights cleared — 🐂 auto-detection will run again.":
        "🎯 Кульминации удалены — 🐂 автоопределение запустится снова.",
    "🎯 Last mark deleted — 🐂 auto-detection takes over again.":
        "🎯 Последняя метка удалена — 🐂 снова работает автоопределение.",
    "🎯 Play a Paso Doble first, then click when a highlight hits.":
        "🎯 Сначала запустите Пасодобль, затем щёлкните в момент кульминации.",
    "🎵  Check music": "🎵  Проверить музыку",
    "🎵  Check music speed": "🎵  Проверить темп музыки",
    "🎵  Check music speed (unavailable)":
        "🎵  Проверить темп музыки (недоступно)",
    "🎵  Music check": "🎵  Проверка музыки",
    "🎵 Checks": "🎵 Проверки",
    "🎵 Music speed": "🎵 Темп музыки",
    "🎵 Music check aborted.": "🎵 Проверка музыки прервана.",
    "🎵  One flat list of": "🎵  Один плоский список из",
    "🎵  Show its tracks": "🎵  Показать его треки",
    "🎵 0 titles": "🎵 0 треков",
    "🎵 %d title": "🎵 Треков: %d",
    "🎵 %d titles": "🎵 Треков: %d",
    "  ·  ✦ %d new": "  ·  ✦ новых: %d",
    "🎼  Build chroma cover / remix index…":
        "🎼  Построить chroma-индекс каверов / ремиксов…",
    "🎚️  Open playlists": "🎚️  Открытые плейлисты",
    "🎚️  Timbre + Rhythm (librosa)": "🎚️  Тембр + ритм (librosa)",
    "🎛 Play sets": "🎛 Игровые сеты",
    "🎛 No free pad voice — every voice holds a looping pad.":
        "🎛 Нет свободного голоса для пэда — каждый голос занят зацикленным пэдом.",
    "🎤 Vocal": "🎤 Вокал",
    "🎙️  Only instrumental tracks (no vocals)":
        "🎙️  Только инструментальные треки (без вокала)",
    "🎧  Open in external player": "🎧  Открыть во внешнем плеере",
    "🌐  Whole repository": "🌐  Весь репозиторий",
    "🌐  Build librosa index (needs librosa)":
        "🌐  Построить индекс librosa (нужна librosa)",
    "🌐  Build / refresh librosa audio index (whole repo)…":
        "🌐  Построить / обновить аудиоиндекс librosa (весь репозиторий)…",
    "🔬  Timbre Gaussian / KL (Mandel-Ellis)":
        "🔬  Тембр: гауссиана / KL (Mandel-Ellis)",
    "⚠  That spot is no longer in an open deck.":
        "⚠  Это место больше не находится в открытом деке.",
    "↺  Default blue": "↺  Стандартный синий",
    "↺  Default rules": "↺  Стандартные правила",
    "1 playlist": "1 плейлист",
    "%d playlist": "Плейлистов: %d",
    "%d playlists": "Плейлистов: %d",
    "No playlist": "Нет плейлиста",
    "No wishlist": "Без пожеланий",
    "1 wishlist": "Пожелания: 1",
    "2 wishlists": "Пожелания: 2",
    "3 wishlists": "Пожелания: 3",
    "4 wishlists": "Пожелания: 4",
    "4 wishlists (2×2)": "Пожелания: 4 (2×2)",
    "Build a practice playlist into the focused deck:\n"
    "• Practice for a tournament class — the class's dances round-robin\n"
    "  (e.g. Latin S: SA, CC, RB, PD, JI …), TSO-conform, popular + fresh.\n"
    "• Party — alternating 3-dance rounds across all dances.\n"
    "Draw from your ⭐ Favorites (unused tracks), the open wishlists\n"
    "or a chosen .m3u file.":
        "Создать тренировочный плейлист в активном деке:\n"
        "• Практика для турнирного класса — танцы класса по кругу\n"
        "  (напр. Latin S: SA, CC, RB, PD, JI …), по TSO, популярные + новые.\n"
        "• Вечеринка — чередующиеся туры по 3 танца из всех танцев.\n"
        "Источник: ваше ⭐ Избранное (неиспользованные треки), открытые списки пожеланий\n"
        "или выбранный файл .m3u.",
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
        "Проверить каждый трек в деках на турнирные проблемы:\n"
        "• Темп: метка в имени файла (T51 = тактов в минуту, через размер\n"
        "  танца) против темпа, измеренного librosa, — находит неверно подписанные файлы.\n"
        "• Диапазон TSO: находится ли темп в официальном диапазоне тактов танца.\n"
        "• Длительность: предупреждает, если трек короче игрового времени 1:30–1:45\n"
        "  или длиннее 4:00.\n"
        "• Структура тура: неравное число танцев в туре и отклонения\n"
        "  числа заходов в финале/полуфинале.\n"
        "Подозрительные треки можно прослушать, удалить или заменить прямо из отчёта.\n"
        "Проверкам темпа/диапазона нужен 🔬 аудиоанализ для измеренного темпа.",
    "Collapse every round and dance header of every playlist —\n"
    "click again to open them all.":
        "Свернуть все заголовки туров и танцев во всех плейлистах —\n"
        "щёлкните ещё раз, чтобы раскрыть их все.",
    "Cycle the playlist headers: full → 🗜 Compact (per-dance header rows\n"
    "hidden, each round lists its songs directly) → 🚫 No groups (round and\n"
    "─── section headers dropped too, so the list — a Practice / party\n"
    "list above all — is one flat run of songs) → 🔢 Numbers (no groups,\n"
    "plus an Nb. column up front counting the titles).":
        "Переключать заголовки плейлиста: полностью → 🗜 Компактно (строки заголовков\n"
        "танцев скрыты, каждый тур сразу перечисляет треки) → 🚫 Без групп (заголовки\n"
        "туров и разделов ─── тоже убраны, так что список — прежде всего список\n"
        "практики / вечеринки — один сплошной ряд треков) → 🔢 Номера (без групп,\n"
        "плюс столбец № впереди, считающий треки).",
    "Cycle the wishlist area: off → 1 → 2 → 3 → 4 → 4 stacked 2×2.\n"
    "Right click walks it backwards.\n"
    "Off hides it entirely, even with multiple decks.\n"
    "Double-click any deck/wishlist title to rename it.":
        "Переключать область списков пожеланий: выкл. → 1 → 2 → 3 → 4 → 4 сеткой 2×2.\n"
        "Правый щелчок — в обратную сторону.\n"
        "Выкл. скрывает её полностью, даже при нескольких деках.\n"
        "Двойной щелчок по заголовку дека или списка пожеланий переименовывает его.",
    "Empty every playlist deck (wishlists are kept).\n"
    "Tip: Del on a deck's title clears just that one playlist;\n"
    "Del on a wishlist's title clears that wishlist.":
        "Очистить все деки плейлистов (списки пожеланий сохраняются).\n"
        "Совет: Del на заголовке дека очищает только этот плейлист;\n"
        "Del на заголовке списка пожеланий очищает этот список.",
    "Export every non-empty playlist deck to its own .m3u in the\n"
    "playlist folder at once (wishlists are not included).\n"
    "Each file is named after its deck title.":
        "Сразу экспортировать каждый непустой дек плейлиста в отдельный .m3u в\n"
        "папке плейлистов (списки пожеланий не включаются).\n"
        "Каждый файл называется по заголовку своего дека.",
    "Export playlists as a self-contained venue bundle — asks first\n"
    "whether to take all open decks, only the 📅 tournament day, or\n"
    "saved .m3u files dragged in, with the ⭐ wishlists if ticked.\n"
    "One sub-folder per playlist holding its tracks copied in numbered\n"
    "play order (0_0_1 - Title WW29.mp3) plus the playlist's .m3u — each\n"
    "folder plays in order even without the M3U, from any drive,\n"
    "laptop or UltraMixer at the venue (no path fixing needed there).\n"
    "Also offers the 📦 venue pack: this desk in one file for another PC.":
        "Экспортировать плейлисты как самодостаточный пакет для площадки — сначала спрашивает,\n"
        "брать ли все открытые деки, только 📅 турнирный день или\n"
        "перетащенные сохранённые файлы .m3u (⭐ списки пожеланий — если отмечено).\n"
        "По подпапке на плейлист с треками, скопированными в пронумерованном\n"
        "порядке воспроизведения (0_0_1 - Title WW29.mp3), плюс .m3u плейлиста — каждая\n"
        "папка играет по порядку даже без M3U, с любого диска,\n"
        "ноутбука или UltraMixer на площадке (исправлять пути там не нужно).\n"
        "Также предлагает 📦 пакет площадки: этот пульт в одном файле для другого ПК.",
    "Export the focused playlist as a printable PDF\n"
    "(rounds, heats, titles, lengths) into the playlist folder.":
        "Экспортировать активный плейлист в PDF для печати\n"
        "(туры, заходы, треки, длительности) в папку плейлистов.",
    "Fold every visible playlist deck and wishlist to its header tab —\n"
    "click again to open them all.\n"
    "Click a single tab (or its arrow) to open just that one.":
        "Свернуть каждый видимый дек плейлиста и список пожеланий до вкладки заголовка —\n"
        "щёлкните ещё раз, чтобы раскрыть их все.\n"
        "Щелчок по одной вкладке (или её стрелке) раскрывает только её.",
    "Plan a whole tournament day: define the day's competitions\n"
    "(style, age, class, round pattern) and generate them all at once\n"
    "into the 📅 Tournament-day tab — eight dedicated day decks in two\n"
    "sub-tabs, separate from the normal playlists; more than 8\n"
    "competitions stack several per deck. All share one no-repeat\n"
    "pool, so a song never appears in two of the day's competitions\n"
    "(Paso excepted). Exports write one M3U per competition.":
        "Спланировать весь турнирный день: задайте соревнования дня\n"
        "(программа, возраст, класс, схема туров) и создайте их все сразу\n"
        "во вкладке 📅 Турнирный день — восемь отдельных деков дня в двух\n"
        "подвкладках, отдельно от обычных плейлистов; при более чем 8\n"
        "соревнованиях на один дек приходится несколько. У всех общий пул\n"
        "без повторов, так что трек никогда не попадёт в два соревнования\n"
        "дня (кроме Пасо). Экспорт пишет по одному M3U на соревнование.",
    "Relocate broken track references in the visible deck(s) to matching\n"
    "real files in the library — fixes moved folders / changed drive\n"
    "letters after an import. Anything still unresolved is reported.":
        "Перенаправить битые ссылки на треки в видимых деках на подходящие\n"
        "настоящие файлы в библиотеке — исправляет перемещённые папки / изменённые буквы\n"
        "дисков после импорта. Всё, что осталось нерешённым, попадает в отчёт.",
    "Save the whole working session right now — every deck, wishlist and the\n"
    "window layout — so it comes back exactly on the next launch.  (Ctrl+Shift+S)\n"
    "(This also happens automatically on every edit and on close.)":
        "Сохранить весь рабочий сеанс прямо сейчас — каждый дек, список пожеланий и\n"
        "раскладку окна — чтобы при следующем запуске всё вернулось точно так же.  (Ctrl+Shift+S)\n"
        "(Это также происходит автоматически при каждом изменении и при закрытии.)",
    "Scan the visible playlist deck(s) for songs that appear more than once,\n"
    "then resolve each: keep the ones you want and replace the rest with a\n"
    "similar track (chosen from the Similar-Tracks picker).":
        "Найти в видимых деках треки, которые встречаются больше одного раза,\n"
        "и разобрать каждый случай: оставить нужные, а остальные заменить\n"
        "похожим треком (из выбора похожих треков).",
    "Show / hide the library browser under the wishlists:\n"
    "filter the whole competition library and drag tracks\n"
    "straight into a deck or wishlist.":
        "Показать / скрыть обозреватель библиотеки под списками пожеланий:\n"
        "фильтруйте всю турнирную библиотеку и перетаскивайте треки\n"
        "прямо в дек или список пожеланий.",
    "Show / hide the 🎛 sample-pad wall:\n"
    "drop Tusch, applause or a background bed onto a pad and tap it —\n"
    "it plays on top of the running music instead of replacing it.\n"
    "Drag its title bar to dock it left / right / below, or float it.":
        "Показать / скрыть стену пэдов 🎛:\n"
        "перетащите туш, аплодисменты или фоновую подложку на пэд и нажмите его —\n"
        "он играет поверх идущей музыки, а не вместо неё.\n"
        "Тяните за заголовок, чтобы закрепить её слева / справа / снизу или оставить плавающей.",
    "Space: play / stop the selected song\n"
    "Ctrl + ← / → : seek 30 s back / forward\n"
    "Click a round / dance header to collapse or expand it":
        "Пробел: воспроизвести / остановить выбранный трек\n"
        "Ctrl + ← / → : перемотка на 30 с назад / вперёд\n"
        "Щелчок по заголовку тура / танца сворачивает или разворачивает его",
    "💥  The app did not shut down cleanly last time.\n"
    "\n"
    "The crash log of that session is under 'Show Details…' (it is overwritten on every start).":
        "💥  В прошлый раз приложение завершилось некорректно.\n"
        "\n"
        "Журнал сбоя того сеанса — в разделе «Показать подробности…» (он перезаписывается при каждом запуске).",
    "AI Error": "Ошибка ИИ",
    "API key needed": "Нужен ключ API",
    "CLAUDE_CONFIG_DIR — which claude login the CLI uses.\n"
    "Empty leaves it to the CLI (~/.claude).":
        "CLAUDE_CONFIG_DIR — какой вход claude использует CLI.\n"
        "Пусто — решает сама CLI (~/.claude).",
    "Enter a free OpenRouter API key (openrouter.ai/keys).":
        "Введите бесплатный ключ API OpenRouter (openrouter.ai/keys).",
    "Free text. The tempo table, the track catalog and the answer\n"
    "format are added automatically — describe only what makes a\n"
    "playlist good in your eyes.":
        "Свободный текст. Таблица темпов, каталог треков и формат\n"
        "ответа добавляются автоматически — опишите только то, что\n"
        "по-вашему делает плейлист хорошим.",
    "How much text this run moves.\n"
    "\n"
    "Sent is everything the model was given (the rules, the library summary, the catalog rows), back is what it answered. The biggest turn is the one that has to fit the model's context window: one prompt plus its reply.\n"
    "\n"
    "Token counts are estimated at ~4 characters each — no backend here reports its real usage.":
        "Сколько текста перемещает этот запуск.\n"
        "\n"
        "Отправлено — всё, что получила модель (правила, сводка библиотеки, строки каталога), получено — её ответ. Самый большой ход — тот, что должен поместиться в контекстное окно модели: один запрос вместе с ответом.\n"
        "\n"
        "Токены оцениваются по ~4 символа на токен — ни один бэкенд здесь не сообщает реальный расход.",
    "Name the tracks yourself. The model does the looking up: it finds\n"
    "the library title behind every shortened or mistyped wish.":
        "Назовите треки сами. Поиск берёт на себя модель: она находит\n"
        "название из библиотеки за каждым сокращённым или опечатанным пожеланием.",
    "Style, age, start class, dances and the round pattern come from\n"
    "the panel on the left. The model only picks and orders the music.":
        "Программа, возраст, класс, танцы и схема туров берутся из\n"
        "панели слева. Модель только выбирает и упорядочивает музыку.",
    "Write the wishes however you like — one per line, a sentence, or a whole sheet pasted in with a column per dance:\n"
    "\n"
    "lw            t               ww        qs\n"
    "White wings   a new life      Willow    quit playing games !!\n"
    "melancolia !  Dance of love   Kiss me   youre so fine\n"
    "\n"
    "Short names and typos are fine. A two-letter code beside a title names its dance, ! or !! marks the ones you really want, and anything else you write here is read as an instruction.":
        "Пишите пожелания как угодно — по одному в строке, фразой или целой таблицей, вставленной со столбцом на танец:\n"
        "\n"
        "lw            t               ww        qs\n"
        "White wings   a new life      Willow    quit playing games !!\n"
        "melancolia !  Dance of love   Kiss me   youre so fine\n"
        "\n"
        "Короткие названия и опечатки — не проблема. Двухбуквенный код рядом с названием указывает танец, ! или !! отмечает то, что вы действительно хотите, а всё остальное, что вы здесь пишете, читается как указание.",
    "e.g. 'club evening, keep it modern', 'no covers in the final',\n"
    "'the wishes are for a show — put the two marked ones last'":
        "напр. «клубный вечер, лучше современное», «без каверов в финале»,\n"
        "«пожелания для шоу — два отмеченных поставить в конец»",
    "🏆  Competition playlist — rounds and heats from the left panel":
        "🏆  Турнирный плейлист — туры и заходы из панели слева",
    "Drag .m3u playlists or audio files here; drag a title out (e.g. to the reference field) to remove it":
        "Перетащите сюда плейлисты .m3u или аудиофайлы; вытащите трек (напр. в поле эталона), чтобы удалить его",
    "Open file": "Открыть файл",
    "Open folder": "Открыть папку",
    "Show in Explorer": "Показать в Проводнике",
    "📂  Drop .m3u playlists (or audio files) here, or click to browse":
        "📂  Перетащите сюда плейлисты .m3u (или аудиофайлы) или щёлкните для выбора",
    "Could not parse any competition lines from the pasted text.\n"
    "Each line needs a class label, a style (STD/LAT) and the\n"
    "heat counts, e.g.  'U21 STD (50) 4 - 4 - 3 - 2 - 1'.":
        "Не удалось разобрать ни одной строки соревнования во вставленном тексте.\n"
        "Каждой строке нужны метка класса, программа (STD/LAT) и\n"
        "число заходов, напр.  'U21 STD (50) 4 - 4 - 3 - 2 - 1'.",
    "Let a model build the playlist instead of the scoring algorithm.\n"
    "You give it the rules (a default set is filled in), it picks and\n"
    "orders the music — either into the rounds/heats configured above\n"
    "or as one flat list.\n"
    "Runs on your Claude subscription via the claude CLI, with\n"
    "OpenRouter as fallback.":
        "Пусть плейлист составит модель, а не алгоритм оценки.\n"
        "Вы задаёте правила (стандартный набор уже заполнен), она выбирает и\n"
        "упорядочивает музыку — по турам/заходам, настроенным выше,\n"
        "или одним плоским списком.\n"
        "Работает по вашей подписке Claude через claude CLI, с\n"
        "OpenRouter в качестве запасного варианта.",
    "Runs through the claude CLI on your Claude subscription — no API key. Falls back to OpenRouter if that fails.":
        "Работает через claude CLI по вашей подписке Claude — без ключа API. Если не получится, переключается на OpenRouter.",
    "⚠ claude CLI not found — OpenRouter will be used. Set the CLAUDE_BIN environment variable to use your subscription.":
        "⚠ claude CLI не найден — будет использован OpenRouter. Задайте переменную окружения CLAUDE_BIN, чтобы использовать подписку.",
    "Load an existing .m3u into the focused deck or wishlist.\n"
    "Decks detect rounds, dances and heats automatically — a final\n"
    "with extra backup variants (e.g. two Sambas) is handled too.\n"
    "A focused wishlist appends the tracks flat.":
        "Загрузить существующий .m3u в активный дек или список пожеланий.\n"
        "Деки автоматически распознают туры, танцы и заходы — в том числе финал\n"
        "с дополнительными запасными вариантами (напр. две Самбы).\n"
        "Активный список пожеланий просто добавляет треки подряд.",
    "No competitions parsed": "Соревнования не распознаны",
    "On: changing a round's strategy re-rolls that whole round.\n"
    "Off: keep the current grid and change only the songs you want\n"
    "via the ↺ buttons (they use the newly selected strategy).":
        "Вкл.: смена стратегии тура перетасовывает весь тур.\n"
        "Выкл.: текущая сетка остаётся, а вы меняете только нужные треки\n"
        "кнопками ↺ (они используют новую выбранную стратегию).",
    "Open the last conversation with the model again.\n"
    "It is kept until the next AI run starts.":
        "Снова открыть последний диалог с моделью.\n"
        "Он хранится до начала следующего запуска ИИ.",
    "When enabled, songs within a round are scored for\n"
    "timbral similarity to the round's first song.\n"
    "Disable for more varied song choices.":
        "Если включено, треки в туре оцениваются по\n"
        "сходству тембра с первым треком тура.\n"
        "Выключите для более разнообразного выбора.",
    "Which titles ⚡ Generate may pick from.\n"
    "Favorites library — everything scanned from your library folder.\n"
    "Open wishlists — only what you parked in the ⭐ wishlists.\n"
    "An .m3u file — only the tracks in that one playlist.\n"
    "With the last two, a dance the pool cannot cover stays blank.":
        "Из каких треков может выбирать ⚡ Создать.\n"
        "Избранная библиотека — всё, что прочитано из вашей папки библиотеки.\n"
        "Открытые списки пожеланий — только то, что вы положили в ⭐ списки пожеланий.\n"
        "Файл .m3u — только треки этого одного плейлиста.\n"
        "В последних двух случаях танец, который пул не может покрыть, остаётся пустым.",
    "“Proven” = songs you played in THIS competition's past lists · “New” = never played.  🎯 keeps a round to this competition; untick it to draw that round from ALL your playlists.":
        "«Проверенные» = треки, которые вы ставили в прошлых списках ЭТОГО соревнования · «Новые» = никогда не игравшие.  🎯 держит тур в рамках этого соревнования; снимите отметку, чтобы брать этот тур из ВСЕХ ваших плейлистов.",
    "🎯 ticked: draw this round's songs from THIS competition's past lists only.\n"
    "Unticked: draw from ALL your playlists.":
        "🎯 отмечено: брать треки этого тура только из прошлых списков ЭТОГО соревнования.\n"
        "Не отмечено: брать из ВСЕХ ваших плейлистов.",
    "<b>App mode</b> — which side of the app is shown:":
        "<b>Режим приложения</b> — какая часть приложения показывается:",
    "<b>Favorites library</b> — scanned on start (your tanzcds folder):":
        "<b>Избранная библиотека</b> — читается при запуске (ваша папка tanzcds):",
    "<b>Reference path</b> — base folder the playlist files live in on THIS PC; 🧭 Fix paths re-roots broken references here (e.g. C:\\Users\\…\\my music\\tanzcds):":
        "<b>Опорный путь</b> — базовая папка, где лежат файлы плейлистов на ЭТОМ ПК; 🧭 Исправить пути перенаправляет сюда битые ссылки (напр. C:\\Users\\…\\my music\\tanzcds):",
    "<b>Save-as folder</b> — where 'Save as M3U…' starts (e.g. D:\\Playlists):":
        "<b>Папка «Сохранить как»</b> — откуда начинается «Сохранить как M3U…» (напр. D:\\Playlists):",
    "<b>Playlist file format</b> — what 'Save as M3U' and the exports write:":
        "<b>Формат файла плейлиста</b> — что пишут «Сохранить как M3U» и экспорты:",
    "UTF-8 (.m3u) — default": "UTF-8 (.m3u) — по умолчанию",
    "UTF-8 with BOM (.m3u) — for Windows tools that guess ANSI":
        "UTF-8 с BOM (.m3u) — для программ Windows, которые угадывают ANSI",
    "UTF-8 (.m3u8) — the encoding named in the extension":
        "UTF-8 (.m3u8) — кодировка указана в расширении",
    "UTF-8 keeps every umlaut and is what current players read.\n"
    "Pick the BOM variant only if an older Windows tool shows 'Ã¼' instead\n"
    "of 'ü'; .m3u8 is the same UTF-8 under the extension some players expect.":
        "UTF-8 сохраняет все символы и читается современными плеерами.\n"
        "Выбирайте вариант с BOM, только если старая программа Windows показывает 'Ã¼' вместо\n"
        "'ü'; .m3u8 — тот же UTF-8 под расширением, которого ждут некоторые плееры.",
    "<b>Search folders</b> — where else to look for a track when a playlist was written on another PC, one folder per line (e.g. F:\\my music and C:\\Users\\…\\Documents\\datein\\my music):":
        "<b>Папки поиска</b> — где ещё искать трек, если плейлист был записан на другом ПК, по одной папке в строке (напр. F:\\my music и C:\\Users\\…\\Documents\\datein\\my music):",
    "<b>Tournament playlists</b> — learned for popularity: .m3u files and/or tournament folders with copied music (e.g. H:\\DM Latein 2026):":
        "<b>Турнирные плейлисты</b> — изучаются для популярности: файлы .m3u и/или турнирные папки со скопированной музыкой (напр. H:\\DM Latein 2026):",
    "<b>What do you want to use this app for?</b>":
        "<b>Для чего вы хотите использовать это приложение?</b>",
    "<b>Whole music repository</b> — used by global search (e.g. F:\\my music):":
        "<b>Весь музыкальный репозиторий</b> — используется глобальным поиском (напр. F:\\my music):",
    "<b>▶ Player position</b> — where the master player stands in ▶ Playing mode:":
        "<b>▶ Положение плеера</b> — где стоит главный плеер в режиме ▶ Воспроизведение:",
    "<b>🌐 Language</b> — menus, buttons and dialogs:":
        "<b>🌐 Язык</b> — меню, кнопки и диалоги:",
    "🇬🇧  English — the language the app is written in (default)":
        "🇬🇧  English — язык, на котором написано приложение (по умолчанию)",
    "Every label exactly as the app ships it.":
        "Каждая надпись в точности такая, как в поставке приложения.",
    "Menus, buttons and dialogs are translated. Track names, dance names and anything read from your files stay as they are.":
        "Меню, кнопки и диалоги переводятся. Названия треков, танцев и всё, что прочитано из ваших файлов, остаются как есть.",
    "<b>🖥 Presenter screen</b> — the colours it wears:":
        "<b>🖥 Презентация</b> — её цвета:",
    "<b>🎚 Accent colour</b> — the blue the buttons, sliders and the ▶ player panel are built around:":
        "<b>🎚 Акцентный цвет</b> — синий, вокруг которого построены кнопки, ползунки и панель плеера ▶:",
    "<b>🎚 TSO pitch target</b> — which takt the 🎚 button pitches a heat to. <i>Middle of the round</i> puts the round on one takt: the takt most of its titles are on where a step of one gets the rest there cheaply (T30+T31+T31 Cha-Chas → 31), the middle of its takte where it does not (T24+T25+T25 Rumbas → 24.5, T50+T52+T52 Quicksteps → 51). Nothing moves more than a takt. A fixed takt puts every title of that dance on the same tempo instead — worth setting on the slow dances, where one takt out of 24 is twice the pitch shift one takt out of 50 is.":
        "<b>🎚 Целевой такт TSO</b> — к какому такту кнопка 🎚 подтягивает заход. <i>Середина тура</i> ставит тур на один такт: на такт, на котором стоит большинство его треков, если шаг в один такт дёшево приводит туда остальные (Ча-ча-ча T30+T31+T31 → 31), иначе на середину его тактов (Румбы T24+T25+T25 → 24,5, Квикстепы T50+T52+T52 → 51). Ничто не сдвигается больше чем на такт. Фиксированный такт вместо этого ставит каждый трек этого танца на один темп — имеет смысл для медленных танцев, где один такт из 24 даёт вдвое больший сдвиг высоты, чем один такт из 50.",
    "<b>🎛 Play sets</b> — the two buttons on the ▶ Playing panel put the controls on these values in one press:":
        "<b>🎛 Игровые сеты</b> — две кнопки на панели ▶ Воспроизведение одним нажатием ставят элементы управления на эти значения:",
    "<b>🎨 Theme</b> — the classic light or dark, or one of the looks:":
        "<b>🎨 Тема</b> — классическая светлая или тёмная либо один из стилей:",
    "<b>🎵 Check music</b> — thresholds used by the tournament checks (open decks and dragged-in files):":
        "<b>🎵 Проверка музыки</b> — пороги турнирных проверок (открытые деки и перетащенные файлы):",
    "<b>🔊 Audio backend</b> — the engine every title is played through:":
        "<b>🔊 Аудиобэкенд</b> — движок, через который воспроизводится каждый трек:",
    "Build everything on this tab in one go for a chosen library, in turn:\n"
    "🎚 librosa → 📊 loudness → 🔇 silences → 🐂 PD highlights → 🧠 MERT →\n"
    "🎼 Chroma. Reuses anything already cached and can be cancelled\n"
    "between/within steps. Read-only; your audio files are never modified.\n"
    "Skips models that aren't installed — and 🎙 Demucs vocals, which are far\n"
    "slower than the rest and stay a deliberate choice.":
        "Построить всё на этой вкладке за один раз для выбранной библиотеки, по очереди:\n"
        "🎚 librosa → 📊 громкость → 🔇 тишина → 🐂 кульминации PD → 🧠 MERT →\n"
        "🎼 Chroma. Использует всё уже закэшированное, отменить можно\n"
        "между шагами и во время них. Только чтение; ваши аудиофайлы никогда не изменяются.\n"
        "Пропускает неустановленные модели — и вокал 🎙 Demucs, который намного\n"
        "медленнее остального и остаётся отдельным осознанным выбором.",
    "Chroma vectors match melody/harmony instead of sound, so the\n"
    "Similar-Tracks window can find remixes & covers of the same tune.\n"
    "librosa-only; reuses anything already cached.":
        "Chroma-векторы сравнивают мелодию/гармонию, а не звучание, поэтому\n"
        "окно похожих треков находит ремиксы и каверы одной и той же мелодии.\n"
        "Только с librosa; использует всё уже закэшированное.",
    "Close this and filter the library pane to the selected\n"
    "row's dance + class, showing only tracks you have never played.":
        "Закрыть это окно и отфильтровать панель библиотеки по танцу + классу\n"
        "выбранной строки, показывая только треки, которые вы никогда не ставили.",
    "Compute the selected similarity index over the library (global repo\n"
    "when global search is on, else the favorites library). Reuses anything\n"
    "already cached; only missing vectors are added.":
        "Вычислить выбранный индекс сходства по библиотеке (глобальный репозиторий,\n"
        "если глобальный поиск включён, иначе избранная библиотека). Использует всё\n"
        "уже закэшированное; добавляются только недостающие векторы.",
    "Detect the highlights of every Paso Doble in the music library\n"
    "and store them in the local database, so the highlight stop is\n"
    "armed instantly on playback (already-analyzed tracks are skipped).":
        "Найти кульминации каждого Пасодобля в музыкальной библиотеке\n"
        "и сохранить их в локальной базе данных, чтобы остановка на кульминации\n"
        "была готова сразу при воспроизведении (уже проанализированные треки пропускаются).",
    "Find the silent stretches of every track of the music library\n"
    "(via ffmpeg; already-probed tracks are skipped, results are\n"
    "cached). Playback probes each new title itself — doing it up\n"
    "front keeps that decode off the disk during a tournament.":
        "Найти тихие участки каждого трека музыкальной библиотеки\n"
        "(через ffmpeg; уже проверенные треки пропускаются, результаты\n"
        "кэшируются). Воспроизведение само проверяет каждый новый трек — сделав это\n"
        "заранее, вы избавите диск от декодирования во время турнира.",
    "Global search needs the repo's audio analyzed once (⚗ Analysis tab). Analysis only <i>reads</i> your files — it never modifies them. Results are cached, so repeat searches are fast.":
        "Глобальному поиску нужно один раз проанализировать аудио репозитория (вкладка ⚗ Анализ). Анализ только <i>читает</i> ваши файлы — он никогда их не изменяет. Результаты кэшируются, поэтому повторные поиски быстрые.",
    "Shorter by %s s": "Короче на %s с",
    "Longer by %s s — past %s the title plays to its end":
        "Длиннее на %s с — после %s трек играет до конца",
    "Tempo %s %s — hold to glide":
        "Темп %s %s — удерживайте для плавного изменения",
    "slower": "медленнее",
    "faster": "быстрее",
    "How long the volume takes to ramp down to 0 when\n"
    "the play length cuts a title — half-second steps":
        "За сколько громкость опускается до 0, когда\n"
        "длительность воспроизведения обрезает трек — шагами по полсекунды",
    "Invalid rounds": "Недопустимые туры",
    "Library gap dashboard: per dance × class — pool size, tournament-\n"
    "tempo compliance, proven/fresh split and staleness. Thin pools\n"
    "are marked red.":
        "Обзор пробелов в библиотеке: по танцу × классу — размер пула, соответствие\n"
        "турнирному темпу, доля проверенных/новых и устаревание. Скудные пулы\n"
        "отмечены красным.",
    "Measure each track's vocal share by actually separating the vocals\n"
    "from the music (Demucs source separation) — far more reliable than\n"
    "the tag/filename heuristics for the Vocal/Instrumental filter.\n"
    "~7 s per track, cached; already-measured tracks are skipped.":
        "Измерить долю вокала каждого трека, действительно отделив вокал\n"
        "от музыки (разделение источников Demucs) — гораздо надёжнее, чем\n"
        "эвристики по тегам/имени файла, для фильтра Вокал/Инструментал.\n"
        "~7 с на трек, кэшируется; уже измеренные треки пропускаются.",
    "Measure the EBU R128 loudness of every track of the music\n"
    "library (via ffmpeg; already-measured tracks are skipped,\n"
    "results are cached). Enables 🔊 Equalize volume in Playing mode.":
        "Измерить громкость EBU R128 каждого трека музыкальной\n"
        "библиотеки (через ffmpeg; уже измеренные треки пропускаются,\n"
        "результаты кэшируются). Включает 🔊 Выровнять громкость в режиме воспроизведения.",
    "One row per competition — each fills its own 📅 day deck on the\n"
    "Tournament-day tab; more than 8 competitions share decks (labeled\n"
    "round headers). All competitions share one no-repeat pool for the day (Paso Doble may repeat).":
        "Одна строка на соревнование — каждое заполняет свой 📅 дек дня на\n"
        "вкладке Турнирный день; при более чем 8 соревнованиях они делят деки (с\n"
        "подписанными заголовками туров). У всех соревнований общий пул без повторов на день (Пасодобль может повторяться).",
    "Only change this if the sound gives you trouble: a title that\n"
    "won't play, or the short gap a pitch change costs — the two\n"
    "engines handle that differently. Takes effect on the next start.":
        "Меняйте это, только если со звуком проблемы: трек, который\n"
        "не играет, или короткий разрыв при смене высоты тона — два\n"
        "движка обрабатывают это по-разному. Вступает в силу при следующем запуске.",
    "Only the accent's own family of tints follows this colour.\n"
    "A red warning, a green proven mark and the popularity amber mean\n"
    "something, so they keep their hue.":
        "Этому цвету следует только собственное семейство оттенков акцента.\n"
        "Красное предупреждение, зелёная отметка «проверено» и янтарный цвет популярности\n"
        "что-то означают, поэтому сохраняют свой оттенок.",
    "Planner only hides the tournament floor's playing panel;\n"
    "Player only hides everything that generates or checks a playlist.\n"
    "Nothing is removed — switching back brings it all straight back.":
        "«Только планировщик» скрывает лишь панель воспроизведения для турнирного паркета;\n"
        "«Только плеер» скрывает лишь всё, что создаёт или проверяет плейлист.\n"
        "Ничего не удаляется — при обратном переключении всё сразу возвращается.",
    "Playlists still build and play without it. These need it and stay unavailable:<ul><li>analysing the library — tempo, similar tracks</li><li>🔊 loudness levelling (EBU R128)</li><li>🔇 silence detection at the start and end of a track</li></ul>":
        "Плейлисты можно составлять и воспроизводить и без него. Вот что без него не работает:<ul><li>анализ библиотеки — темп, похожие треки</li><li>🔊 выравнивание громкости (EBU R128)</li><li>🔇 определение тишины в начале и конце трека</li></ul>",
    "Re-read every M3U and tournament music folder in the tournament\n"
    "playlist folder and rebuild the popularity / co-occurrence index from\n"
    "it — WITHOUT rescanning files or audio. Use after exporting a played\n"
    "tournament so it counts right away.":
        "Заново прочитать каждый M3U и каждую турнирную папку с музыкой в папке\n"
        "турнирных плейлистов и перестроить по ним индекс популярности / совместной встречаемости\n"
        "— БЕЗ повторного сканирования файлов или аудио. Используйте после экспорта\n"
        "сыгранного турнира, чтобы он сразу учитывался.",
    "Remove cached rows for music files that no longer exist (features,\n"
    "embeddings, loudness, …) and compact the database file (VACUUM).\n"
    "Slow on a big library; refuses to run when the music drive looks\n"
    "unmounted so cached analysis can't be wiped by accident.":
        "Удалить кэшированные строки для музыкальных файлов, которых больше нет (признаки,\n"
        "эмбеддинги, громкость, …), и сжать файл базы данных (VACUUM).\n"
        "Медленно на большой библиотеке; не запускается, если музыкальный диск выглядит\n"
        "отключённым, чтобы сохранённый анализ не стёрся случайно.",
    "Run librosa on the favorites library's MP3 files not yet cached.\n"
    "Required for timbral similarity scoring; when everything is cached\n"
    "a click offers a full re-analysis (e.g. after a tempo-method change).":
        "Запустить librosa для ещё не закэшированных MP3-файлов избранной библиотеки.\n"
        "Нужно для оценки сходства тембра; когда всё закэшировано,\n"
        "щелчок предлагает полный повторный анализ (напр. после смены метода темпа).",
    "Scan the whole repository and analyze any files not yet cached, using the\n"
    "fast librosa timbre+rhythm features (the default similarity method).\n"
    "Read-only; runs in the background and can be left to finish.":
        "Просканировать весь репозиторий и проанализировать все ещё не закэшированные файлы\n"
        "быстрыми признаками тембра+ритма librosa (метод сходства по умолчанию).\n"
        "Только чтение; работает в фоне, можно дать ему закончить.",
    "Takes effect after restarting the app. If the sound stays away afterwards, switch back here — the setting is only read at start, so nothing else in the app depends on it.":
        "Вступает в силу после перезапуска приложения. Если звука после этого нет, переключите здесь обратно — настройка читается только при запуске, больше ничего в приложении от неё не зависит.",
    "🐂 Each set carries its own Paso Doble values. Under 🏆 the highlight stop is <i>off</i> by default: the detection is not good enough yet to cut a competition Paso Doble on, and a heat stopped in the wrong bar is danced twice. Under 🎉 it stops after the 2nd highlight and waits 3 s, so the couples can take their position.":
        "У каждого набора свои значения 🐂 пасодобля. В 🏆 стоп на кульминации по умолчанию <i>выключен</i>: распознавание пока недостаточно надёжно, чтобы обрывать по нему турнирный пасодобль, а заход, остановленный не в том такте, танцуют дважды. В 🎉 он останавливается после 2-й кульминации и ждёт 3 с, чтобы пары заняли исходную позицию.",
    "Shut the music off at the chosen highlight instead of\nthe play length. On by default: at a party the\nPaso Doble ends on its 2nd highlight.":
        "Выключать музыку на выбранной кульминации, а не по\nдлительности. По умолчанию включено: на вечеринке\nпасодобль заканчивается на 2-й кульминации.",
    "Hold a Paso Doble back this long before the music\nstarts, so the couples can take their position.":
        "Задержать пасодобль на столько перед началом музыки,\nчтобы пары заняли исходную позицию.",
    "🐂  Paso Doble: stop after highlight":
        "🐂  Пасодобль: стоп после кульминации",
    "Shut the music off at the chosen highlight instead of\nthe play length. Off by default: a highlight detected\nin the wrong bar cuts the heat short.":
        "Выключать музыку на выбранной кульминации, а не по\nдлительности. По умолчанию выключено: кульминация,\nнайденная не в том такте, обрывает заход раньше времени.",
    "Hold a Paso Doble back this long before the music\nstarts. 0 s = at once: at a competition the couples\nstand before the music, the chairman's call is the wait.":
        "Задержать пасодобль на столько перед началом музыки.\n0 с = сразу: на турнире пары стоят до музыки, объявление\nглавного судьи и есть ожидание.",
    "Theme, accent and language are read when the app starts, so a change takes effect after a restart — you are asked once you save.":
        "Тема, акцент и язык читаются при запуске приложения, поэтому изменение вступает в силу после перезапуска — об этом спросят при сохранении.",
    "Keep the German dance and round names on a screen in another language (Langsamer Walzer, Vorrunde, Standardrunde 1, Eintanzen …)":
        "Оставить немецкие названия танцев и туров на экране на другом языке (Langsamer Walzer, Vorrunde, Standardrunde 1, Eintanzen …)",
    "On: the presenter screen and the recorded announcements are German too, a 🤸 practice list is called Eintanzen, also in its saved file, and the tempo rules are named TSO (off: WDSF CR).\n"
    "Off: Slow Waltz, Round 1, Standard round 1, Practice … — the playlists and exports keep the German dance and round names either way.":
        "Вкл.: экран презентации и записанные объявления тоже на немецком, 🤸 список практики называется Eintanzen, в том числе в сохранённом файле, а правила темпа называются TSO (выкл.: WDSF CR).\n"
        "Выкл.: Slow Waltz, Round 1, Standard round 1, Практика … — плейлисты и экспорты в любом случае сохраняют немецкие названия танцев и туров.",
    "You can change this later under ⚙ Settings → ⚙ General.":
        "Изменить это можно позже в ⚙ Настройки → ⚙ Общие.",
    "lower": "нижний",
    "middle": "средний",
    "upper": "верхний",
    "⚠️  <b>ffmpeg is not installed on this computer.</b>":
        "⚠️  <b>ffmpeg не установлен на этом компьютере.</b>",
    "🌐  Global search — match dropped files against the whole repository (default: favorites library only)":
        "🌐  Глобальный поиск — сравнивать перетащенные файлы со всем репозиторием (по умолчанию: только избранная библиотека)",
    "🎧  Preview player — float a mini player (seek / skip / volume) over the deck when a ▶ button is clicked":
        "🎧  Плеер предпрослушивания — при нажатии ▶ показывать над деком мини-плеер (перемотка / переход / громкость)",
    "🐘 Heavy — AI models, needs the FULL build (or the requirements-full.txt extras)":
        "🐘 Тяжёлые — модели ИИ, нужна ПОЛНАЯ сборка (или дополнения из requirements-full.txt)",
    "🔇  Release the sound card between titles — takes away the hiss an onboard output puts on the PA while the app holds it open":
        "🔇  Освобождать звуковую карту между треками — убирает шипение, которое встроенный выход подаёт на звукоусиление, пока приложение держит его открытым",
    "🔕  Mute system sounds while the evening runs — no error ding or notification chime over the speakers":
        "🔕  Отключать системные звуки на время вечера — никаких сигналов ошибок и уведомлений в динамиках",
    "🐞  Send error reports — when the app hits an error, send its technical details to the developer":
        "🐞  Отправлять отчёты об ошибках — когда в приложении возникает ошибка, её технические подробности уходят разработчику",
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
        "Уходит в проект GlitchTip разработчика (app.glitchtip.com),\n"
        "который также видит IP-адрес, с которого пришёл отчёт.\n"
        "\n"
        "Отправляется: ошибка и место в программе, где она произошла, последние\n"
        "строки журнала перед ней (в них может быть название игравшего трека),\n"
        "операционная система и версия приложения.\n"
        "\n"
        "Не отправляется: ваша музыка, ваши плейлисты, имя вашего компьютера.\n"
        "Ваша папка пользователя вырезается из каждого пути.\n"
        "\n"
        "По умолчанию выключено. Действует сразу после сохранения.",
    "Error reports": "Отчёты об ошибках",
    "Send error reports to the developer?":
        "Отправлять отчёты об ошибках разработчику?",
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
        "Когда в приложении возникает ошибка, оно может отправить технические подробности\n"
        "в проект GlitchTip разработчика (app.glitchtip.com),\n"
        "чтобы ошибку исправили. GlitchTip при этом также видит IP-адрес,\n"
        "с которого пришёл отчёт.\n"
        "\n"
        "Ответственный: marcelkb, разработчик. Вопросы о ваших данных\n"
        "или удаление отчётов: github.com/dancesport-dj/DanceSportPlayer/issues\n"
        "\n"
        "Отправляется: ошибка и место в программе, где она произошла, последние\n"
        "строки журнала перед ней (в них может быть название игравшего трека),\n"
        "операционная система и версия приложения.\n"
        "\n"
        "Не отправляется: ваша музыка, ваши плейлисты, имя вашего компьютера.\n"
        "Ваша папка пользователя вырезается из каждого пути.\n"
        "\n"
        "Изменить это можно в любой момент в ⚙ Настройки → ⚙ Общие.",
    "Send reports": "Отправлять отчёты",
    "Don't send": "Не отправлять",
    "Once per start, the app asks GitHub (api.github.com) for the latest\n"
    "release. The request carries nothing about you or your music; GitHub\n"
    "sees the IP address it comes from. A newer version is announced once,\n"
    "with a link to its download page. Nothing is downloaded or installed.\n"
    "\n"
    "You can change this at any time under ⚙ Settings → ⚙ General.":
        "Один раз при каждом запуске приложение спрашивает у GitHub\n"
        "(api.github.com) последний выпуск. Запрос не содержит ничего о вас\n"
        "или вашей музыке; GitHub видит IP-адрес, с которого он пришёл. О более\n"
        "новой версии сообщается один раз, со ссылкой на страницу загрузки.\n"
        "Ничего не скачивается и не устанавливается.\n"
        "\n"
        "Изменить это можно в любой момент в ⚙ Настройки → ⚙ Общие.",
    "🔔  Also tell me when a new version is out":
        "🔔  Также сообщать, когда выйдет новая версия",
    "New versions": "Новые версии",
    "Tell you when a new version is out?": "Сообщать вам, когда выйдет новая версия?",
    "Check for new versions": "Проверять новые версии",
    "Don't check": "Не проверять",
    "🔔  Check for new versions — once per start, ask GitHub whether a newer release is out":
        "🔔  Проверять новые версии — один раз при запуске спрашивать у GitHub, не вышел ли более новый выпуск",
    "Asks api.github.com for the latest release. The request carries\n"
    "nothing about you or your music; GitHub sees the IP address it\n"
    "comes from. A newer version is announced once, with a link to\n"
    "its download page. Nothing is downloaded or installed.\n"
    "\n"
    "Off by default. Applies from the next start.":
        "Спрашивает у api.github.com последний выпуск. Запрос не содержит\n"
        "ничего о вас или вашей музыке; GitHub видит IP-адрес, с которого он\n"
        "пришёл. О более новой версии сообщается один раз, со ссылкой на\n"
        "страницу загрузки. Ничего не скачивается и не устанавливается.\n"
        "\n"
        "По умолчанию выключено. Действует со следующего запуска.",
    "New version": "Новая версия",
    "Version %s is out.": "Вышла версия %s.",
    "You are running %s. The download page lists what changed.":
        "У вас установлена %s. На странице загрузки указано, что изменилось.",
    "Open download page": "Открыть страницу загрузки",
    "Later": "Позже",
    "The music and the computer share the one sound card, so every\n"
    "sound the system makes goes out over the PA too.\n"
    "\n"
    "Muted all through Playing mode and whenever something plays,\n"
    "put back when you return to planning or close the app.\n"
    "Windows: the System Sounds slider of the volume mixer.\n"
    "macOS: the alert volume. Linux (GNOME): event sounds.":
        "Музыка и компьютер используют одну звуковую карту, поэтому каждый\n"
        "звук системы тоже уходит в зал.\n"
        "\n"
        "Отключён на всё время режима воспроизведения и всякий раз, когда что-то играет,\n"
        "возвращается при переходе к планированию или закрытии приложения.\n"
        "Windows: ползунок «Системные звуки» в микшере громкости.\n"
        "macOS: громкость предупреждений. Linux (GNOME): звуки событий.",
    "🧭 Fix paths tries the Reference path first and then these folders,\n"
    "in order, cutting the foreign path down until what is left lands on a\n"
    "real file underneath one of them. A path is only ever rewritten to a\n"
    "file that is actually there.":
        "🧭 Исправить пути сначала пробует опорный путь, затем эти папки\n"
        "по порядку, укорачивая чужой путь, пока остаток не попадёт на\n"
        "настоящий файл в одной из них. Путь переписывается только на файл,\n"
        "который действительно существует.",
    "Drag <b>.m3u playlists</b> here (audio files work too) to check whether any of their tracks are duplicates of <b>each other</b> — across the dropped playlists, by audio content, else title.":
        "Перетащите сюда <b>плейлисты .m3u</b> (аудиофайлы тоже подойдут), чтобы проверить, не дублируют ли их треки <b>друг друга</b> — во всех перетащенных плейлистах, по аудиосодержимому, иначе по названию.",
    "Drop a <b>reference playlist</b> (.m3u) and the <b>tournament files</b> (.m3u playlists or audio) below. The reference is compared against the tournament tracks and every <b>hard duplicate</b> (byte-identical audio) is removed; the leftover <b>unused</b> tracks are exported to a new .m3u. <span style='color:#666'>Paso Doble is excluded from the comparison and always kept.</span>":
        "Положите ниже <b>эталонный плейлист</b> (.m3u) и <b>файлы турнира</b> (плейлисты .m3u или аудио). Эталон сравнивается с треками турнира, и каждый <b>точный дубликат</b> (побайтно одинаковое аудио) удаляется; оставшиеся <b>неиспользованные</b> треки экспортируются в новый .m3u. <span style='color:#666'>Пасодобль в сравнении не участвует и всегда сохраняется.</span>",
    "Duplicate songs across your open playlist(s), in playlist order.<br><span style='color:#666'>🟰 <b>Exact</b> = identical audio. ≈ <b>Similar</b> = same title, a different recording. Keep the ones you want; switch the others to <b>Replace</b> and pick a track for each, or to <b>Remove</b>.</span>":
        "Повторяющиеся треки в открытых плейлистах, в порядке плейлиста.<br><span style='color:#666'>🟰 <b>Точный</b> = одинаковое аудио. ≈ <b>Похожий</b> = то же название, другая запись. Оставьте нужные; остальные переключите на <b>Заменить</b> и выберите для каждого трек, или на <b>Удалить</b>.</span>",
    "Every copy of this song is already controlled by the within-playlist\n"
    "section above, so there is nothing left to resolve on this row.":
        "Каждой копией этого трека уже управляет раздел «внутри плейлиста»\n"
        "выше, поэтому в этой строке решать больше нечего.",
    "Export unused tracks": "Экспортировать неиспользованные треки",
    "No hard duplicates of the tournament files were found in the reference — nothing to remove.":
        "В эталоне не найдено точных дубликатов файлов турнира — удалять нечего.",
    "Nothing to change — no occurrence is set to Replace or Remove.":
        "Нечего менять — ни одно вхождение не стоит на «Заменить» или «Удалить».",
    "Reference base": "Эталонная база",
    "Resolve duplicates": "Разобрать дубликаты",
    "Sort the exported tracks by dance?\n"
    "\n"
    "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)":
        "Отсортировать экспортированные треки по танцам?\n"
        "\n"
        "(LW, TG, WW, SF, QS, SB, CC, RB, PD, JV)",
    "The reference base must be a single .m3u playlist.":
        "Эталонной базой должен быть один плейлист .m3u.",
    "This list holds some titles more than once.<br><span style='color:#666'>For each title, pick the file to keep — the others are removed. <b>Keep all</b> leaves that title alone.</span>":
        "В этом списке некоторые треки встречаются больше одного раза.<br><span style='color:#666'>Для каждого трека выберите файл, который останется, — остальные будут удалены. <b>Оставить все</b> не трогает этот трек.</span>",
    "Browse by library category — 🏆 Tournament hides the non-tournament\n"
    "folders (anthems, background, wrong-tempo, duplicates, seasonal);\n"
    "pick a category to look only at those (handy for parties).":
        "Просмотр по категории библиотеки — 🏆 Турнир скрывает нетурнирные\n"
        "папки (гимны, фон, неверный темп, дубликаты, сезонное);\n"
        "выберите категорию, чтобы видеть только её (удобно для вечеринок).",
    "Drag a track onto a deck or wishlist to use it.\n"
    "▶ to preview · right-click for more · a double-click opens it in\n"
    "the system's music player if ⚙ Settings say so.":
        "Перетащите трек на дек или в список пожеланий, чтобы использовать его.\n"
        "▶ — прослушать · правый щелчок — больше · двойной щелчок открывает трек\n"
        "в музыкальном плеере системы, если так задано в ⚙ Настройки.",
    "Only tracks suited for one of the ticked starting classes\n(tick several; tracks without a class tag show only with all classes)":
        "Только треки, подходящие для одного из отмеченных стартовых классов\n(можно отметить несколько; треки без класса только при всех классах)",
    "Only tracks whose file was created in the library that\n"
    "recently. Combine with ✦ Never played to see what you\n"
    "copied in but have never actually used.":
        "Только треки, файл которых появился в библиотеке настолько недавно.\n"
        "Вместе с ✦ Ни разу не звучал показывает то, что вы скопировали,\n"
        "но так и не использовали.",
    "Show only tracks not already used in any open playlist deck —\n"
    "handy for finding fresh music while building rounds.":
        "Показывать только треки, которых ещё нет ни в одном открытом деке —\n"
        "удобно, чтобы находить свежую музыку при составлении туров.",
    "Substring of the title, the artist, or a comment marker\n"
    "(vocal_f, classic, eintanzen, …)":
        "Часть названия, исполнителя или метки в комментарии\n"
        "(vocal_f, classic, eintanzen, …)",
    "proven": "проверенный",
    "rare": "редкий",
    "Audio analysis unavailable": "Аудиоанализ недоступен",
    "Audio cache not ready yet — try again shortly.":
        "Аудиокэш ещё не готов — попробуйте чуть позже.",
    "Build ALL caches": "Построить ВСЕ кэши",
    "Build all caches": "Построить все кэши",
    "Analyze loudness": "Анализ громкости",
    "Analyze vocals (Demucs)": "Анализ вокала (Demucs)",
    "No Paso Doble tracks in the library.": "В библиотеке нет пасодоблей.",
    "Probe silences": "Проверить тишину",
    "Re-analyze Audio": "Повторный аудиоанализ",
    "Redo the 🐂 auto-detection for the whole library — for after the\n"
    "detector changed. Hand-set 🎯 marks are kept untouched.":
        "Заново выполнить автоопределение 🐂 для всей библиотеки — на случай,\n"
        "если детектор изменился. Вручную поставленные метки 🎯 не трогаются.",
    "The music library is not loaded yet.":
        "Музыкальная библиотека ещё не загружена.",
    "ffmpeg was not found (neither on PATH nor the copy bundled\n"
    "with the project) — loudness cannot be measured.":
        "ffmpeg не найден (ни в PATH, ни копия, поставляемая\n"
        "с проектом) — громкость измерить нельзя.",
    "ffmpeg was not found (neither on PATH nor the copy bundled\n"
    "with the project) — silences cannot be probed.":
        "ffmpeg не найден (ни в PATH, ни копия, поставляемая\n"
        "с проектом) — тишину проверить нельзя.",
    "Clear playlists": "Очистить плейлисты",
    "Clear tournament day": "Очистить турнирный день",
    "Close tournament day": "Закрыть турнирный день",
    "Competition name (empty = default):":
        "Название соревнования (пусто = по умолчанию):",
    "Competition name:": "Название соревнования:",
    "Free order": "Свободный порядок",
    "None of these tracks says which dance it is, so there is no grid to build from them — the list stays a free running order.":
        "Ни один из этих треков не указывает свой танец, поэтому сетку из них построить нельзя — список остаётся свободным порядком.",
    "New tournament day": "Новый турнирный день",
    "Rename tournament day": "Переименовать турнирный день",
    "Shuffle — put the same titles in a fresh order,\n"
    "as if the party list were built again from scratch.":
        "Перемешать — те же треки в новом порядке,\n"
        "как если бы список вечеринки был составлен заново.",
    "Total play time of this playlist\n"
    "(↳ backup rows not counted — they only play as stand-ins)\n"
    "Click ▸ for the songs per dance":
        "Общее время звучания этого плейлиста\n"
        "(резервные строки ↳ не считаются — они играют только как замена)\n"
        "Щёлкните ▸, чтобы увидеть треки по танцам",
    "Every similar track is already in an open playlist.":
        "Все похожие треки уже есть в открытом плейлисте.",
    "No similar tracks found — the song may not be audio-analyzed yet.":
        "Похожих треков не найдено — возможно, трек ещё не прошёл аудиоанализ.",
    "Replace duplicate": "Заменить дубликат",
    "Audio index": "Аудиоиндекс",
    "Audio index ready": "Аудиоиндекс готов",
    "Build audio index": "Построить аудиоиндекс",
    "Embedding index error": "Ошибка индекса эмбеддингов",
    "Favorites library isn't loaded yet.":
        "Избранная библиотека ещё не загружена.",
    "The whole-repository library isn't loaded yet. Drop a file (or build the librosa index over the repository) once to load it, then retry.":
        "Библиотека всего хранилища ещё не загружена. Перетащите один раз файл (или постройте индекс librosa по хранилищу), чтобы загрузить её, затем повторите.",
    "Not on the Reference path": "Не на опорном пути",
    "Save Error": "Ошибка сохранения",
    "Save as M3U": "Сохранить как M3U",
    "This deck is empty.": "Этот дек пуст.",
    "Fold this playlist to a tab —\n"
    "the other open playlists get its space.":
        "Свернуть этот плейлист во вкладку —\n"
        "его место займут другие открытые плейлисты.",
    "AI playlist": "ИИ-плейлист",
    "AI playlist failed": "Не удалось создать ИИ-плейлист",
    "All picks are TSO-conform (T24 Rumba / T58-59 Paso allowed, like the normal playlist).":
        "Все треки соответствуют TSO (Румба T24 / Пасодобль T58-59 разрешены, как в обычном плейлисте).",
    "Cap the party-list length — handy when drawing from the whole library.\n"
    "The round it lands in is played out, so the list can run a title or two over.\n"
    "0 = No limit (use every eligible track).":
        "Ограничить длину списка вечеринки — удобно при выборе из всей библиотеки.\n"
        "Тур, на который приходится граница, доигрывается, поэтому список может выйти на трек-два длиннее.\n"
        "0 = Без ограничения (все подходящие треки).",
    "Choose an .m3u file first.": "Сначала выберите файл .m3u.",
    "Dances come in alternating 3-dance rounds (not competition rounds).":
        "Танцы идут чередующимися турами по 3 танца (не соревновательные туры).",
    "Day plan": "План дня",
    "Draw from your library, exactly like the left panel's Favorites mode.":
        "Брать из вашей библиотеки, точно как в режиме «Избранное» левой панели.",
    "Draw only from the tracks currently parked in your open ⭐ wishlists.":
        "Брать только из треков, которые сейчас лежат в открытых ⭐ списках пожеланий.",
    "Practice Error": "Ошибка практики",
    "Enter a valid round pattern (e.g. 6-3-2-1).":
        "Введите правильную схему туров (напр. 6-3-2-1).",
    "Generate Error": "Ошибка создания",
    "History Error": "Ошибка истории",
    "Library gaps": "Пробелы библиотеки",
    "No Competition": "Нет соревнования",
    "No Dances": "Нет танцев",
    "No Matches": "Нет совпадений",
    "No Rounds": "Нет туров",
    "No Theme": "Нет темы",
    "No candidate tracks for those settings — check the dances, the\n"
    "start class and that the library actually holds those tempos.":
        "Нет подходящих треков для этих настроек — проверьте танцы,\n"
        "класс и есть ли в библиотеке такие темпы.",
    "No matching tracks for the chosen options — check the class, the source and that the library / .m3u actually has those dances.":
        "Нет подходящих треков для выбранных параметров — проверьте класс, источник и есть ли в библиотеке / .m3u эти танцы.",
    "No resolvable tracks in that .m3u file.":
        "Ни один трек из этого файла .m3u не найден.",
    "Paste a schedule and click 'Parse schedule', then pick a competition.":
        "Вставьте расписание, нажмите «Разобрать расписание», затем выберите соревнование.",
    "Pick at least Standard or Latin dances.":
        "Выберите хотя бы танцы Standard или Latin.",
    "Please select a theme.": "Выберите тему.",
    "Please select at least one dance.": "Выберите хотя бы один танец.",
    "Replace day plan": "Заменить план дня",
    "Share of slots that lean FRESH (least-played) instead of proven favourites.\n"
    "Higher = more never/barely-played tracks — at 100 % the list is\n"
    "built from the least-played tracks upward (not just the few with zero plays).":
        "Доля мест, склоняющихся к СВЕЖИМ (реже всего игравшим) трекам вместо проверенных любимых.\n"
        "Выше = больше ни разу или почти не игравших треков — при 100 % список\n"
        "строится от реже всего игравших треков вверх (а не только из немногих, что не звучали ни разу).",
    "The Tournament-day tab still holds an earlier day plan.\n"
    "\n"
    "Replace it with the new one?":
        "Во вкладке «Турнирный день» ещё лежит прежний план дня.\n"
        "\n"
        "Заменить его новым?",
    "The library is still loading — try again in a moment.":
        "Библиотека ещё загружается — попробуйте чуть позже.",
    "The model answered, but none of its picks matched the\n"
    "catalog. Try again — or lower the round count.":
        "Модель ответила, но ни один её выбор не совпал с\n"
        "каталогом. Попробуйте ещё раз — или уменьшите число туров.",
    "The model answered, but none of its picks matched the catalog.":
        "Модель ответила, но ни один её выбор не совпал с каталогом.",
    "The selected competition has no valid heat counts.":
        "У выбранного соревнования нет допустимого числа заходов.",
    "The wish list is empty — write the titles you want, one\n"
    "per line or a column per dance.":
        "Список пожеланий пуст — напишите нужные треки, по одному\n"
        "в строке или по столбцу на танец.",
    "Theme Error": "Ошибка темы",
    "Upper limit. The list stops here or when the TSO-conform pool runs dry — whichever comes first.":
        "Верхняя граница. Список заканчивается здесь или когда пул, соответствующий TSO, исчерпан, — смотря что наступит раньше.",
    "Your open wishlists are empty — park some tracks there first.":
        "Открытые списки пожеланий пусты — сначала положите туда несколько треков.",
    "🆕 This competition has no saved work yet — press ⚡ Generate from History to seed it":
        "🆕 Для этого соревнования ещё ничего не сохранено — нажмите ⚡ Создать из истории, чтобы начать",
    "🏆  Practice for a tournament class (round-robin through the class's dances)":
        "🏆  Практика для турнирного класса (танцы класса по кругу)",
    "Analysis Error": "Ошибка анализа",
    "Build librosa index": "Построить индекс librosa",
    "Clean up database": "Очистить базу данных",
    "Could not start a new instance — please start the app again yourself.":
        "Не удалось запустить новый экземпляр — запустите приложение снова сами.",
    "Finding similar tracks for a file needs librosa + ffmpeg.\n"
    "Install them, then retry.":
        "Для поиска похожих треков по файлу нужны librosa + ffmpeg.\n"
        "Установите их и повторите.",
    "Global Index Error": "Ошибка глобального индекса",
    "Global search": "Глобальный поиск",
    "Library Load Error": "Ошибка загрузки библиотеки",
    "Re-learn playlists": "Заново изучить плейлисты",
    "Set a valid music repository folder first.":
        "Сначала укажите правильную папку музыкального хранилища.",
    "Set a valid music repository folder in ⚙ Settings first.":
        "Сначала укажите правильную папку музыкального хранилища в ⚙ Настройках.",
    "Settings saved": "Настройки сохранены",
    "Similar Tracks": "Похожие треки",
    "The favorites library path changed.\n"
    "Restart the app to load the new library.":
        "Путь к избранной библиотеке изменился.\n"
        "Перезапустите приложение, чтобы загрузить новую библиотеку.",
    "Couldn't detect any danceable tracks in that playlist.":
        "В этом плейлисте не удалось распознать ни одного танцевального трека.",
    "Import Error": "Ошибка импорта",
    "Import M3U": "Импорт M3U",
    "Not enough free playlists": "Недостаточно свободных плейлистов",
    "Nothing imported": "Ничего не импортировано",
    "Remove from the playlist(s) — the slot stays empty (Ctrl+Z undoes)":
        "Убрать из плейлиста(ов) — место останется пустым (Ctrl+Z отменяет)",
    "Drop <b>.m3u playlists</b> here — only playlists carry track paths to fix.":
        "Перетащите сюда <b>плейлисты .m3u</b> — только в плейлистах есть пути к трекам, которые можно исправить.",
    "Fix & overwrite": "Исправить и перезаписать",
    "Fix paths": "Исправить пути",
    "No track paths that can be re-rooted under the search folders.":
        "Нет путей к трекам, которые можно перенести в папки поиска.",
    "Set a Reference path or a search folder in Settings before fixing dropped playlists.":
        "Прежде чем исправлять перетащенные плейлисты, задайте в Настройках опорный путь или папку поиска.",
    "⚠  No <b>search folder</b> set — open Settings and name the base folder(s) the music lives in on this PC.":
        "⚠  <b>Папка поиска</b> не задана — откройте Настройки и укажите базовые папки, где на этом ПК лежит музыка.",
    "Clear all playlists": "Очистить все плейлисты",
    "Nothing to print — no songs found.":
        "Нечего печатать — треки не найдены.",
    "Print playlist": "Печать плейлиста",
    "Add folder": "Добавить папку",
    "No alternative Practice track found.":
        "Другой трек для практики не найден.",
    "No alternative song found.": "Другой трек не найден.",
    "Re-roll this song — best timbre match first  (Ctrl+R / Ctrl+N)":
        "Подобрать этот трек заново — сначала лучший по тембру  (Ctrl+R / Ctrl+N)",
    "Swap with a %s from the end of the list — a leftover that fits no round first, else one from the last third  (Ctrl+R / Ctrl+N)":
        "Поменять на %s из конца списка — сначала остаток, не подходящий ни к одному туру, иначе один из последней трети  (Ctrl+R / Ctrl+N)",
    "↺ click to swap it with a %s from the end of the list":
        "↺ нажмите, чтобы поменять его на %s из конца списка",
    "↺ click to re-roll a replacement":
        "↺ нажмите, чтобы подобрать замену заново",
    "🔁 Marked for potential replace  (Ctrl+M to toggle)":
        "🔁 Отмечен для возможной замены  (Ctrl+M переключает)",
    "⚠ File not found on disk:\n"
    "%s":
        "⚠ Файл не найден на диске:\n"
        "%s",
    "Is the drive unplugged, or was the file moved or renamed? It cannot play until it is back.":
        "Диск отключён, или файл перемещён или переименован? Он не сможет играть, пока не вернётся.",
    "Regenerate": "Сгенерировать заново",
    "Regenerate Error": "Ошибка повторной генерации",
    "Track length (m:ss)\n"
    "orange = shorter than the configured play length, or 5 s or more\n"
    "of stillness at an edge that the player skips (the cell's own\n"
    "tooltip says which, and how long it really plays)":
        "Длина трека (м:сс)\n"
        "оранжевый = короче заданного времени звучания или 5 с и более\n"
        "тишины на краю, которую плеер пропускает (подсказка самой\n"
        "ячейки говорит, где именно и сколько он звучит на самом деле)",
    "Playlist": "Плейлист",
    "Wishlist": "Список пожеланий",
    "Rating — click a star to set it, the last lit one again to clear it.\n"
    "Kept in the app's database; the MP3 itself is not changed.":
        "Оценка — нажмите на звезду, чтобы поставить её, ещё раз на последнюю горящую — чтобы сбросить.\n"
        "Хранится в базе данных приложения; сам MP3 не меняется.",
    "≈  timbral similarity to round anchor\n"
    "    (only shown after running Audio Analysis)\n"
    "[D,C,…]  class tags from MP3 COMM field":
        "≈  сходство тембра с якорем тура\n"
        "    (видно только после аудиоанализа)\n"
        "[D,C,…]  классы из поля COMM в MP3",
    "Audio cache/library not available for this search.":
        "Аудиокэш/библиотека недоступны для этого поиска.",
    "Embedding error": "Ошибка эмбеддинга",
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
        "Гаусс/KL: распределение MFCC каждого трека (среднее + ковариация),\n"
        "сравнение по симметричной KL — модель Манделя–Эллиса, как в старом\n"
        "приложении на Java. Самый чистый поиск похожих по звучанию; настоящие совпадения дают ≳ 80 %.\n"
        "Librosa: быстрый вручную собранный вектор тембра и ритма (косинус).\n"
        "MERT: предобученный нейросетевой музыкальный эмбеддинг — часто ближе\n"
        "к ощущению «звучит похоже». Требует:  pip install torch transformers\n"
        "Chroma кавер/ремикс: сравнивает МЕЛОДИЮ/гармонию, а не тембр — находит\n"
        "ремиксы и каверы той же мелодии даже с другим звуком,\n"
        "тональностью или темпом. Только librosa; индекс строится один раз, как у остальных.\n"
        "Комбинированный (по умолчанию): усреднённое место трека в рейтингах Гаусс/KL,\n"
        "librosa и chroma — первыми идут те, что высоко у всех трёх.\n"
        "Комбинированно + MERT: то же самое, с MERT как четвёртым взглядом.",
    "Off: sound-alike tracks (audio timbre).\n"
    "On: tracks that keep appearing in the same old playlists as this one.":
        "Выкл.: треки, похожие по звучанию (тембр).\n"
        "Вкл.: треки, которые раз за разом попадают в те же старые плейлисты, что и этот.",
    "Replace the duplicate with the selected track (Enter, or double-click a row)":
        "Заменить дубликат выбранным треком (Enter или двойной щелчок по строке)",
    "Several copies of a song often exist under slightly different names\n"
    "(e.g. '… DJ Ice', 'jive(43) - Bim Bam', '16 Bim Bam'). When on, only the\n"
    "first copy of each song title is shown.":
        "У трека часто бывает несколько копий под чуть разными именами\n"
        "(напр. «… DJ Ice», «jive(43) - Bim Bam», «16 Bim Bam»). Если включено,\n"
        "показывается только первая копия каждого названия.",
    "Show only tracks considered instrumental: an explicit 'instr' tag /\n"
    "'(Instr.)' filename marker, a Demucs-measured vocal share (🎙️ Analyze\n"
    "vocals), or the learned audio probability. Unknown tracks count as\n"
    "vocal, so they are hidden while this is on.":
        "Показывать только треки, считающиеся инструментальными: явная метка «instr» /\n"
        "пометка «(Instr.)» в имени файла, доля вокала, измеренная Demucs (🎙️ Анализ\n"
        "вокала), или выученная по аудио вероятность. Неизвестные треки считаются\n"
        "вокальными и поэтому скрыты, пока это включено.",
    "Space: play / stop the selected track\n"
    "Ctrl + ← / → : seek 30 s back / forward":
        "Пробел: воспроизвести / остановить выбранный трек\n"
        "Ctrl + ← / → : перемотка на 30 с назад / вперёд",
    "This track isn't in any of your old playlists yet — nothing to learn from. Switch the toggle off for sound-alike tracks.":
        "Этого трека пока нет ни в одном из ваших старых плейлистов — учиться не на чем. Выключите переключатель, чтобы увидеть похожие по звучанию треки.",
    "🧹  Hide duplicate copies (same song, ignoring DJ / dance / BPM tags)":
        "🧹  Скрыть дубликаты (тот же трек без учёта меток DJ / танца / BPM)",
    "Clear playlist": "Очистить плейлист",
    "Clear wishlist": "Очистить список пожеланий",
    "Find in list": "Найти в списке",
    "Find planned before": "Найти прежние планы",
    "Find title:": "Найти название:",
    "No similar tracks found (audio features may be missing).":
        "Похожие треки не найдены (возможно, нет аудиопризнаков).",
    "Select exactly two titles of the same dance to swap them.":
        "Выберите ровно два трека одного танца, чтобы поменять их местами.",
    "Swap titles": "Поменять треки",
    "Already planned": "Уже запланирован",
    "Different dance": "Другой танец",
    "Move Error": "Ошибка перемещения",
    "Move track": "Переместить трек",
    "Replace Error": "Ошибка замены",
    "Different style": "Другая программа",
    "Load playlist": "Загрузить плейлист",
    "Name (competition, day, tournament):":
        "Название (соревнование, день, турнир):",
    "New folder": "Новая папка",
    "Remove": "Удалить",
    "Remove this song from its slot? The slot stays empty.":
        "Убрать этот трек с его места? Место останется пустым.",
    "Remove %d songs from their slots? The slots stay empty.":
        "Убрать треки с их мест (%d)? Места останутся пустыми.",
    "Remove this song from the running order?":
        "Убрать этот трек из порядка воспроизведения?",
    "Remove %d songs from the running order?":
        "Убрать треки из порядка воспроизведения (%d)?",
    "Rename": "Переименовать",
    "Songs and total play time of the selected playlist\n"
    "(tracks this library doesn't know count, but add no time)":
        "Треки и общее время звучания выбранного плейлиста\n"
        "(треки, неизвестные этой библиотеке, считаются, но время не добавляют)",
    "The playlists filed in the selected folder, one slot each.\n"
    "Drag a slot onto a deck to load that round · double-click it to\n"
    "load it onto the focused deck · right-click to rename, remove or\n"
    "read its tracks.":
        "Плейлисты в выбранной папке, каждый на своём месте.\n"
        "Перетащите место на дек, чтобы загрузить этот тур · двойной щелчок\n"
        "загружает его на активный дек · правый щелчок — переименовать, удалить\n"
        "или прочитать его треки.",
    "The tracks of the selected playlist, in playing order.\n"
    "▶ or Space previews · drag them onto a deck or the player list ·\n"
    "a double-click opens or 🏷 edits them as ⚙ Settings say.":
        "Треки выбранного плейлиста в порядке воспроизведения.\n"
        "▶ или Пробел — прослушать · перетащите их на дек или в список плеера ·\n"
        "двойной щелчок открывает или 🏷 редактирует их, как задано в ⚙ Настройки.",
    "Your competitions, days and tournaments — folders are labels,\n"
    "the 🎵 entries point at .m3u files wherever they lie.\n"
    "\n"
    "Drop .m3u files or a whole folder in from Explorer · pick a folder\n"
    "to lay its playlists out as slots on the right · drag a slot onto\n"
    "a deck to load the round · double-click it to load it onto the\n"
    "focused deck.":
        "Ваши соревнования, дни и турниры — папки служат лишь метками,\n"
        "записи 🎵 указывают на файлы .m3u, где бы они ни лежали.\n"
        "\n"
        "Перетащите файлы .m3u или целую папку из Проводника · выберите папку,\n"
        "чтобы разложить её плейлисты по местам справа · перетащите место на\n"
        "дек, чтобы загрузить тур · двойной щелчок загружает его на активный\n"
        "дек.",
    "📂  (not in a folder)": "📂  (не в папке)",
    "Party play time, songs at full length with no pause.\n"
    "The count simulates the party generator with your library's\n"
    "track lengths per dance (3.5 min where none are known).":
        "Время звучания вечеринки: треки целиком, без пауз.\n"
        "Подсчёт имитирует генератор вечеринки с длинами треков\n"
        "вашей библиотеки по танцам (3,5 мин, где они неизвестны).",
    "Per dance: songs to have ready — enough for 9 of 10 generated lists.":
        "По танцам: сколько треков держать наготове — хватит на 9 из 10 сгенерированных списков.",
    "A key given to a pad follows it wherever it is moved and works\n"
    "from any page. Empty = that pad answers to its slot's key.":
        "Клавиша, назначенная пэду, следует за ним, куда бы его ни перенесли,\n"
        "и работает с любой страницы. Пусто = пэд отвечает на клавишу своего места.",
    "Export cartwall": "Экспорт картволла",
    "Import cartwall": "Импорт картволла",
    "Pads per page. Making the grid smaller never loses a pad —\n"
    "whatever no longer fits moves to the first free slot.":
        "Падов на странице. Уменьшение сетки никогда не теряет пэд —\n"
        "то, что больше не помещается, переезжает на первое свободное место.",
    "Page name:": "Название страницы:",
    "Play this pad over and over until it is stopped —\n"
    "for a background bed under a ceremony.":
        "Играть этот пэд снова и снова, пока его не остановят —\n"
        "как звуковой фон под церемонию.",
    "Remove page": "Удалить страницу",
    "Rename page": "Переименовать страницу",
    "Snap the wall back into the main window.\n"
    "It returns to the edge it was last docked at.":
        "Вернуть стену в главное окно.\n"
        "Она возвращается к краю, у которого была закреплена в последний раз.",
    "That file is not a cartwall this version can read.":
        "Этот файл — не картволл, который может прочитать эта версия.",
    "The key fires whichever pad sits in that slot on the page you are\n"
    "looking at, so the same finger hits the same corner on every page.":
        "Клавиша запускает тот пэд, что лежит на этом месте на открытой\n"
        "странице, — так один и тот же палец попадает в тот же угол на любой странице.",
    "No pause started — enable auto-advance and have a next song queued.":
        "Пауза не началась — включите автопереход и поставьте следующий трек в очередь.",
    "⏹ The playing title is no longer in its deck — the music was stopped.":
        "⏹ Играющего трека больше нет в его деке — музыка остановлена.",
    "✏️ Title ended — still loaded for editing; scrub back and ⏯ to listen.":
        "✏️ Трек закончился — ещё загружен для правки; перемотайте назад и ⏯, чтобы послушать.",
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
        "Пасодобль под этим переключателем никогда не затухает и не учитывает\n"
        "время звучания — его танцуют до поставленных кульминаций.\n"
        "Кульминации (крещендо → драматический обрыв) определяются\n"
        "автоматически в фоне, и музыка сразу обрывается, когда\n"
        "наступает выбранная (её финальный гонг). Кульминация, которую\n"
        "распознавание не может точно найти, берётся по стандартной фразировке\n"
        "(1-я ≈ 0:45, 2-я ≈ 1:15).\n"
        "\n"
        "Если выключено, пасодобль — обычный трек: время звучания обрезает его,\n"
        "а затухание убирает, как у любого другого танца.",
    "Append the heat number (\"…, Heat 3\") — the couples hear which\n"
    "heat they are about to dance.\n"
    "\n"
    "Only a round grid has heats: a theme list, the warm-up and a free\n"
    "running order are announced without one. Recorded for heats 1-8;\n"
    "beyond that the number is left out.":
        "Добавлять номер захода («…, Gruppe 3») — пары слышат, в каком\n"
        "заходе они сейчас танцуют.\n"
        "\n"
        "Заходы есть только в сетке туров: тематический список, практика и свободный\n"
        "порядок объявляются без него. Записано для заходов 1-8;\n"
        "дальше номер опускается.",
    "Compensate loudness differences between tracks on playback:\n"
    "each song's measured EBU R128 loudness is pulled towards a common\n"
    "target, so quiet old recordings and loud modern masters play at\n"
    "a similar level. Needs 📊 Analyze loudness (⚙ Settings) first.":
        "Выравнивать громкость треков при воспроизведении:\n"
        "измеренная громкость EBU R128 каждого трека подтягивается к общей\n"
        "цели, чтобы тихие старые записи и громкие современные мастеры звучали\n"
        "примерно одинаково. Сначала нужен 📊 Анализ громкости (⚙ Настройки).",
    "Forget the current track's learned highlights\n"
    "(falls back to 🐂 auto-detection on the next play).":
        "Забыть выученные кульминации текущего трека\n"
        "(при следующем воспроизведении снова работает 🐂 автоопределение).",
    "Hold a Paso Doble back this long before the music starts, so the\n"
    "couples reach their position after the dance is called. Applies\n"
    "to every way a PD is started — ▶, a double-click, auto-advance.\n"
    "0 s = start at once, like every other dance.\n"
    "\n"
    "With 🔈 Announce next dance on, the app makes the call and the\n"
    "seconds run from it; off, the hall's announcer does and the wait\n"
    "runs silently — counted down on this panel either way.":
        "Задержать пасодобль на столько перед началом музыки, чтобы\n"
        "пары успели встать на позиции после объявления танца. Действует\n"
        "при любом запуске PD — ▶, двойной щелчок, автопереход.\n"
        "0 с = сразу, как у любого другого танца.\n"
        "\n"
        "При включённом 🔈 Объявлять следующий танец объявляет приложение, и\n"
        "секунды идут от объявления; если выключено, объявляет ведущий в зале, и ожидание\n"
        "идёт молча — в обоих случаях с обратным отсчётом на этой панели.",
    "Keep the screensaver and the display timeout off while music is\n"
    "playing or the presenter screen is open.\n"
    "\n"
    "The system counts idle time from the mouse and the keyboard,\n"
    "never from the speakers — so an hour of music with nobody touching\n"
    "the desk blanks the screen mid-heat, the beamer included. It goes\n"
    "back to its normal timeouts as soon as neither is running.":
        "Не включать заставку и не гасить экран, пока играет\n"
        "музыка или открыт экран ведущего.\n"
        "\n"
        "Система отсчитывает простой по мыши и клавиатуре,\n"
        "а не по колонкам — поэтому час музыки, когда никто не трогает\n"
        "пульт, гасит экран посреди захода, включая проектор. Обычные\n"
        "таймауты возвращаются, как только ни то, ни другое не работает.",
    "Off: the next song starts the moment the current one ends, with\n"
    "no pause music and no announcement. The configured time is kept\n"
    "for switching back.\n"
    "\n"
    "Needs ⏭ auto-advance — without it the next song waits for the\n"
    "operator anyway, so there is no gap to fill.":
        "Выкл.: следующий трек начинается в тот момент, когда закончился текущий,\n"
        "без музыки в паузе и без объявления. Заданное время сохраняется\n"
        "на случай обратного переключения.\n"
        "\n"
        "Нужен ⏭ автопереход — без него следующий трек всё равно ждёт\n"
        "оператора, так что заполнять нечего.",
    "On: a double-click in a deck puts the title on the speakers at\n"
    "once — what a party wants.\n"
    "Off: it is only CUED on the player (loaded, shown, silent) and ⏯\n"
    "starts it — what a heat wants, where the music begins when the\n"
    "couples are on the floor and not a moment earlier.\n"
    "\n"
    "Part of the play sets: 🏆 tournament switches it off, 🎉 party on.":
        "Вкл.: двойной щелчок в деке сразу выводит трек в колонки\n"
        "— то, что нужно вечеринке.\n"
        "Выкл.: трек лишь ГОТОВИТСЯ в плеере (загружен, показан, тихо), а ⏯\n"
        "запускает его — то, что нужно заходу, где музыка начинается, когда\n"
        "пары на паркете, и ни мгновением раньше.\n"
        "\n"
        "Часть наборов воспроизведения: 🏆 турнир выключает, 🎉 вечеринка включает.",
    "On: a double-click in a deck plays the title at once.\n"
    "Off: it is only cued on the player (loaded, shown,\n"
    "silent) and ⏯ starts it — the heat begins when the\n"
    "couples stand.":
        "Вкл.: двойной щелчок в деке сразу запускает трек.\n"
        "Выкл.: трек лишь готовится в плеере (загружен, показан,\n"
        "тихо), а ⏯ запускает его — заход начинается, когда\n"
        "пары стоят.",
    "Pitch every title to the mean tempo of its dance in the\n"
    "current round, kept inside the TSO range — what a heat is\n"
    "danced to. Wrong for a party, where the next song is a\n"
    "different dance at whatever tempo it was recorded at.":
        "Подтягивать каждый трек к среднему темпу его танца в\n"
        "текущем туре в пределах диапазона TSO — так танцуют\n"
        "заход. Не подходит для вечеринки, где следующий трек —\n"
        "другой танец в том темпе, в котором он записан.",
    "Open a second, full-screen window showing only the running title\n"
    "with its dance and the next three songs — big and plain, for a\n"
    "beamer or a monitor turned towards the floor. Pick the screen\n"
    "next to it; Esc (or this button) closes it again.":
        "Открыть второе полноэкранное окно, где виден только играющий трек\n"
        "с его танцем и три следующих трека — крупно и просто, для\n"
        "проектора или монитора, повёрнутого к паркету. Экран выбирается\n"
        "рядом; Esc (или эта кнопка) снова закрывает окно.",
    "Pause the music and suspend the highlight stop, so the whole Paso\n"
    "Doble is reachable while you set its marks: scrub to a crash, ⏯ to\n"
    "listen, hit 🎯, delete a wrong mark with its ✕. Marking within 3 s\n"
    "of an existing mark moves that one instead of adding a fourth.\n"
    "\n"
    "Leaving edit mode arms the stop again and PAUSES at it the next\n"
    "time it's reached, so you can hear whether the mark sits right.":
        "Поставить музыку на паузу и приостановить остановку по кульминации, чтобы весь\n"
        "пасодобль был доступен, пока вы ставите метки: перемотайте к удару, ⏯ —\n"
        "послушать, нажмите 🎯, удалите неверную метку её ✕. Метка в пределах 3 с\n"
        "от существующей сдвигает ту, а не добавляет четвёртую.\n"
        "\n"
        "При выходе из режима правки остановка снова включается, и плеер в следующий\n"
        "раз ПРИОСТАНОВИТСЯ на ней, чтобы вы услышали, верно ли стоит метка.",
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
        "Одним действием вернуть панель к соревновательным значениям:\n"
        "заданное время звучания, без пауз между треками, без автоперехода\n"
        "и без голосового объявления — настройки, с которыми идёт заход.\n"
        "\n"
        "Горит золотым, пока панель стоит на этих значениях, так же как 🎉\n"
        "горит фиолетовым во время вечеринки. Выключает набор 🎉 вечеринка. Что именно\n"
        "он задаёт, можно изменить: ⚙ Настройки → 🎛 Наборы воспроизведения.\n"
        "\n"
        "Если кнопка горит, щелчок выключает набор: список возвращается\n"
        "к значениям, которые были до его включения.",
    "Say the next dance out loud shortly before the pause ends\n"
    "(\"Nächster Tanz: Langsamer Walzer\"). Without a pause the dance\n"
    "is named as the title starts instead (\"Langsamer Walzer\") —\n"
    "over the first bars or before them, as ⚙ Settings → 🔊 Sound &\n"
    "player has it.":
        "Объявлять следующий танец вслух незадолго до конца паузы\n"
        "(«Nächster Tanz: Langsamer Walzer»). Без паузы танец\n"
        "называется при старте трека («Langsamer Walzer») —\n"
        "поверх первых тактов или перед ними — как задано в\n"
        "⚙ Настройки → 🔊 Звук & плеер.",
    "The dance is named while the music is already running, ducked\n"
    "under the voice — the hall hears both at once and the title\n"
    "loses none of its first bars.\n"
    "\n"
    "Applies where a title names its dance as it starts: 🔈 Announce\n"
    "next dance on, and no pause between songs (a pause has a gap of\n"
    "its own for the call).":
        "Танец называется, когда музыка уже играет, приглушённая\n"
        "под голосом, — зал слышит и то и другое, и трек\n"
        "не теряет ни одного из первых тактов.\n"
        "\n"
        "Действует, где трек называет свой танец при старте: 🔈 Объявлять\n"
        "следующий танец включено и нет паузы между треками (у паузы своя\n"
        "пауза для объявления).",
    "The dance is called into silence and the music follows when the\n"
    "voice is done — the hall hears WHICH dance before it starts, at\n"
    "the cost of a second or two of quiet.\n"
    "\n"
    "Applies where a title names its dance as it starts: 🔈 Announce\n"
    "next dance on, and no pause between songs (a pause has a gap of\n"
    "its own for the call).":
        "Танец объявляется в тишине, а музыка начинается, когда\n"
        "голос закончил, — зал слышит, КАКОЙ танец будет, до его начала, ценой\n"
        "секунды-двух тишины.\n"
        "\n"
        "Действует, где трек называет свой танец при старте: 🔈 Объявлять\n"
        "следующий танец включено и нет паузы между треками (у паузы своя\n"
        "пауза для объявления).",
    "Show a cover picture next to the title on the player.\n"
    "The playlist's own image is used when it has one (an #EXTIMG line\n"
    "in the .m3u or a cover file beside it), otherwise the track's\n"
    "embedded artwork, otherwise a plain ♪ tile.":
        "Показывать обложку рядом с названием в плеере.\n"
        "Используется собственная картинка плейлиста, если она есть (строка #EXTIMG\n"
        "в .m3u или файл обложки рядом), иначе встроенная\n"
        "обложка трека, иначе простая плитка ♪.",
    "Speak a sample announcement now — check voice and level\n"
    "before the round, not during it.":
        "Произнести пробное объявление сейчас — проверьте голос и уровень\n"
        "до тура, а не во время него.",
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
        "Одним действием переключить турнирные настройки на режим вечеринки:\n"
        "каждый трек целиком, автопереход к следующему, без\n"
        "паузы (а значит, без музыки паузы) между ними и без голосового объявления.\n"
        "\n"
        "Включается само, как только вы играете из списка 🤸 практики /\n"
        "вечеринки, и выключается, когда управление берёт турнирный дек, —\n"
        "в обоих случаях уведомление сообщает, что изменилось. Что именно он задаёт,\n"
        "можно изменить: ⚙ Настройки → 🎛 Наборы воспроизведения.\n"
        "\n"
        "Если кнопка горит, щелчок выключает набор: список возвращается\n"
        "к значениям, которые были до его включения.",
    "The colours of the presenter screen. 'Default' is the black hall\n"
    "display; 'Light' is creme paper with warm brown type and rose\n"
    "gold for the next dance — made for a lit room, where black on a\n"
    "beamer is just a grey rectangle. Applies straight away.":
        "Цвета экрана ведущего. «Default» — чёрный экран\n"
        "для зала; «Light» — кремовая бумага с тёплым коричневым шрифтом и\n"
        "розовым золотом для следующего танца — для светлого зала, где чёрное на\n"
        "проекторе выглядит просто серым прямоугольником. Применяется сразу.",
    "The evening's running order — when dinner is, when the opening\n"
    "dance is — as a second page on the presenter screen.\n"
    "\n"
    "Type it here; on the screen itself, T (or its 🕒 button) switches\n"
    "to it, and it can fade between the two pages by itself.":
        "Программа вечера — когда ужин, когда открывающий\n"
        "танец — второй страницей на экране ведущего.\n"
        "\n"
        "Введите её здесь; на самом экране T (или его кнопка 🕒) переключает\n"
        "на неё, и он может сам плавно сменять две страницы.",
    "There is one player for every deck, so leaving a title to hear\n"
    "another one loses your place in it. On: the spot a title stopped\n"
    "at is kept and it starts there again — marked by a tick on the\n"
    "seek bar and by ↩ mm:ss on its row.\n"
    "\n"
    "A title played to its end keeps no mark, and the marks are\n"
    "forgotten when the app closes.":
        "Плеер один на все деки, поэтому, уйдя с трека, чтобы\n"
        "послушать другой, вы теряете в нём место. Вкл.: место, где трек\n"
        "остановился, запоминается, и он снова начинается оттуда — отмечено чёрточкой на\n"
        "полосе перемотки и ↩ мм:сс в его строке.\n"
        "\n"
        "Трек, доигранный до конца, метки не сохраняет, а метки\n"
        "забываются при закрытии приложения.",
    "Time for the couples to change / catch breath before the next song":
        "Время парам смениться / перевести дух перед следующим треком",
    "Volume ramps to 0 over the last N seconds,\n"
    "in steps of half a second":
        "Громкость спадает до 0 за последние N секунд,\n"
        "шагами по полсекунды",
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
        "Когда трек заканчивается (затухание или естественный конец), выдержать\n"
        "заданную паузу, затем играть следующую строку трека в деке —\n"
        "так весь тур проходит без участия рук. Останавливается в конце\n"
        "тура (🏁) — следующий тур запускается вручную.\n"
        "\n"
        "Выключение останавливает и 🔈 Объявлять следующий танец: нельзя\n"
        "объявлять танец, который потом не зазвучит. Повторное\n"
        "включение возвращает прежнее объявление.\n"
        "\n"
        "У каждого плейлиста свой ответ: здесь — ответ\n"
        "списка, на котором щёлкнули последним, тот же, что ⏭/✋ под этим деком.",
    "✋  Manual": "✋  Вручную",
    "Auto: a finished song is followed by the next row of the deck, so\n"
    "a whole round runs hands-free.\n"
    "Manual: every song is started by the operator, and 🔈 Announce\n"
    "next dance stops with it — back on Auto it returns.\n"
    "\n"
    "This playlist's own answer, remembered for it: the party list can\n"
    "run hands-free while the round next to it is started by hand.\n"
    "⏭ Auto-advance on the play panel is the same answer while this\n"
    "list is the one last clicked.":
        "Авто: за законченным треком следует следующая строка дека, так\n"
        "что весь тур проходит без участия рук.\n"
        "Вручную: каждый трек запускает оператор, и 🔈 Объявлять\n"
        "следующий танец останавливается вместе с ним — при возврате на Авто оно возвращается.\n"
        "\n"
        "Собственный ответ этого плейлиста, запомненный для него: список вечеринки может\n"
        "идти сам, пока тур рядом запускается вручную.\n"
        "⏭ Автопереход на панели воспроизведения — тот же ответ, пока этот\n"
        "список — последний, на котором щёлкнули.",
    "Manual: every song is started by the operator, and 🔈 Announce\n"
    "next dance is off with it.\n"
    "Auto: a finished song is followed by the next row of the deck, so\n"
    "a whole round runs hands-free — and the announcement returns.\n"
    "\n"
    "This playlist's own answer, remembered for it: the party list can\n"
    "run hands-free while the round next to it is started by hand.\n"
    "⏭ Auto-advance on the play panel is the same answer while this\n"
    "list is the one last clicked.":
        "Вручную: каждый трек запускает оператор, и 🔈 Объявлять\n"
        "следующий танец тоже выключено.\n"
        "Авто: за законченным треком следует следующая строка дека, так\n"
        "что весь тур проходит без участия рук, — и объявление возвращается.\n"
        "\n"
        "Собственный ответ этого плейлиста, запомненный для него: список вечеринки может\n"
        "идти сам, пока тур рядом запускается вручную.\n"
        "⏭ Автопереход на панели воспроизведения — тот же ответ, пока этот\n"
        "список — последний, на котором щёлкнули.",
    "When the LAST title of the list has finished, carry on with its\n"
    "first one instead of stopping — so a party keeps its music going\n"
    "without anybody at the desk.\n"
    "\n"
    "The 🏁 end of a round is untouched: that one happens between\n"
    "rounds, and still waits for the operator.\n"
    "\n"
    "Needs ⏭ auto-advance.":
        "Когда ПОСЛЕДНИЙ трек списка закончился, продолжить с\n"
        "первого вместо остановки — так на вечеринке музыка не смолкает,\n"
        "даже если за пультом никого нет.\n"
        "\n"
        "🏁 Конец тура не затрагивается: он бывает между\n"
        "турами и по-прежнему ждёт оператора.\n"
        "\n"
        "Нужен ⏭ автопереход.",
    "Which highlight ends the Paso Doble — usually the 2nd,\n"
    "in rare cases the 3rd.":
        "Какая кульминация завершает пасодобль — обычно 2-я,\n"
        "в редких случаях 3-я.",
    "Which monitor the presenter screen fills. Same screen as the app\n"
    "is fine too — double-click the presenter window to shrink it back\n"
    "out of full screen.":
        "Какой монитор занимает экран ведущего. Можно и тот же экран, что у\n"
        "приложения, — двойной щелчок по окну ведущего выводит его\n"
        "из полноэкранного режима.",
    "Which recorded voice announces the dance. “Mixed” alternates them\n"
    "— she, he, she, he — so an evening doesn't run on a single voice.\n"
    "\n"
    "A dance that was never recorded is not announced.":
        "Какой записанный голос объявляет танец. «Смешанный» чередует их\n"
        "— она, он, она, он, — чтобы вечер не держался на одном голосе.\n"
        "\n"
        "Танец, который не был записан, не объявляется.",
    "While a Paso Doble plays, click exactly when a highlight (the\n"
    "dramatic gong / drop) hits to teach its position. Click again at\n"
    "the 2nd / 3rd highlight. Manually learned highlights are flagged\n"
    "in the database and are never overwritten by 🐂 auto-detection.":
        "Пока играет пасодобль, нажмите точно в момент кульминации\n"
        "(драматический гонг / обрыв), чтобы запомнить её позицию. Нажмите снова на\n"
        "2-й / 3-й кульминации. Кульминации, выученные вручную, помечаются\n"
        "в базе данных и никогда не перезаписываются 🐂 автоопределением.",
    "Adjusted play length (timed play / Paso Doble highlight stop)\n"
    "next to the track's full length":
        "Скорректированное время звучания (игра по времени / остановка пасодобля по кульминации)\n"
        "рядом с полной длиной трека",
    "Auto-equalize the heat tempo (toggle):\n"
    "while on, every title is pitched to the average tempo of its\n"
    "dance in this round, kept inside the TSO range (e.g. a Rumba\n"
    "at 23 → T24, a Paso Doble at 57 → T58).":
        "Автоматически выравнивать темп захода (переключатель):\n"
        "пока включено, каждый трек подтягивается к среднему темпу своего\n"
        "танца в этом туре в пределах диапазона TSO (напр. румба\n"
        "на 23 → T24, пасодобль на 57 → T58).",
    "Disable preview player  (re-enable in Settings)":
        "Отключить плеер предпрослушивания  (включается снова в Настройках)",
    "Endless repeat of THIS title (toggle):\n"
    "while on, the running title starts again every time it ends —\n"
    "for the moment the floor is still full or the speech runs long.\n"
    "\n"
    "It holds the evening on one title, so it beats the 🏁 end of a\n"
    "round and works with ⏭ auto-advance off too. Switch it off and\n"
    "the list carries on where it stands.":
        "Бесконечный повтор ЭТОГО трека (переключатель):\n"
        "пока включено, играющий трек начинается заново каждый раз, когда заканчивается, —\n"
        "на случай, когда паркет ещё полон или речь затянулась.\n"
        "\n"
        "Он держит вечер на одном треке, поэтому важнее 🏁 конца\n"
        "тура и работает и при выключенном ⏭ автопереходе. Выключите его, и\n"
        "список продолжится с того места, где стоит.",
    "Next dance": "Следующий танец",
    "Cut the pause short and go to the next dance. Its announcement\n"
    "still plays first; the pause music fades out, like ⏭.":
        "Сократить паузу и перейти к следующему танцу. Объявление\n"
        "всё равно звучит сначала; музыка паузы затихает, как при ⏭.",
    "Extend the auto-advance pause (add another pause length) —\n"
    "use it when the heat change is taking longer than planned.":
        "Продлить паузу автоперехода (добавить ещё одну длину паузы) —\n"
        "когда смена захода занимает больше времени, чем планировалось.",
    "Fade the music out and HOLD it there (over the fade time).\n"
    "Nothing ends and nothing advances — ⏯ resumes at exactly the\n"
    "spot it went quiet. For an announcement or an incident on the floor.":
        "Увести музыку в затухание и ДЕРЖАТЬ её там (за время затухания).\n"
        "Ничего не заканчивается и ничего не переходит дальше — ⏯ продолжает ровно с\n"
        "того места, где стало тихо. Для объявления или происшествия на паркете.",
    "Fade this song out now (over the configured fade time), then end it\n"
    "— for a quick, clean finish on the floor.":
        "Сейчас увести этот трек в затухание (за заданное время затухания) и завершить его\n"
        "— для быстрого и чистого финиша на паркете.",
    "Go to the pause music — fade this song out (over the configured\n"
    "fade time), then start the between-songs pause (e.g. the dancers\n"
    "are already leaving).":
        "Перейти к музыке паузы — увести этот трек в затухание (за заданное время\n"
        "затухания) и затем начать паузу между треками (напр. танцоры уже уходят).",
    "Tap along to the beat to measure this track's live tempo by hand,\n"
    "against a target for its dance (Sollwert) — display only, does not\n"
    "touch the fader.":
        "Отстукивайте ритм, чтобы вручную измерить реальный темп этого трека\n"
        "против целевого значения для его танца (Sollwert) — только отображение, фейдер\n"
        "не затрагивается.",
    "Tempo −16 % … +16 % without changing the pitch (time stretch) —\n"
    "e.g. to pull a track onto the takt the tournament needs.\n"
    "Stays set across tracks; a double-click on the fader (or the\n"
    "button below) resets it.":
        "Темп −16 % … +16 % без изменения высоты тона (time stretch) —\n"
        "напр. чтобы подтянуть трек к такту, нужному турниру.\n"
        "Сохраняется между треками; двойной щелчок по фейдеру (или\n"
        "кнопка ниже) сбрасывает его.",
    "📌 Pin the tempo: the fader stays where you left it when the next\n"
    "title starts.\n"
    "Off: every new title begins at ±0 %.\n"
    "Switching TSO on takes the pin off — TSO pitches each title itself.":
        "📌 Закрепить темп: фейдер остаётся там, где вы его оставили, когда начинается\n"
        "следующий трек.\n"
        "Выкл.: каждый новый трек начинается с ±0 %.\n"
        "Включение TSO снимает закрепление — TSO подстраивает каждый трек сам.",
    "Off, the running order goes by this machine's clock.\n"
    "\n"
    "On, it goes by the time you set here — from the moment you save,\n"
    "and running on from there. An evening half an hour behind stays\n"
    "half an hour behind; the screen does not stand still.\n"
    "\n"
    "This is not saved with the programme: the next start of the app\n"
    "is back on the machine's clock.":
        "Если выключено, программа идёт по часам этого компьютера.\n"
        "\n"
        "Если включено, она идёт по времени, которое вы задали здесь, — с момента сохранения\n"
        "и дальше вперёд. Вечер, отстающий на полчаса, так и остаётся\n"
        "на полчаса позади; экран не замирает.\n"
        "\n"
        "Это не сохраняется вместе с программой: при следующем запуске приложения\n"
        "снова действуют часы компьютера.",
    "Off, the screen stays on whichever page you picked (T on the\n"
    "presenter screen, or its 🕒 button, switches by hand).\n"
    "\n"
    "On, it fades from one to the other by itself — so the hall sees\n"
    "both without anybody at the desk touching anything.":
        "Если выключено, экран остаётся на выбранной странице (T на\n"
        "экране ведущего или его кнопка 🕒 переключает вручную).\n"
        "\n"
        "Если включено, он сам плавно переходит с одной на другую — так зал видит\n"
        "обе, и никому за пультом не нужно ничего трогать.",
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
        "Что экран ведущего показывает на второй странице — программу\n"
        "вечера. Строка, до которой дошли часы, выделяется,\n"
        "предыдущие становятся серыми.\n"
        "\n"
        "Время может быть любым, как вы написали бы в программе; в выделении\n"
        "участвуют только настоящие время суток (20:30, 20.30).\n"
        "\n"
        "«До» необязательно и позволяет одному пункту охватывать другой: задайте\n"
        "вечеринке 19:00–01:00, а открывающему танцу 19:30–19:50, и когда\n"
        "танец закончится, выделение вернётся к вечеринке. Либо время\n"
        "окончания (01:00), либо длительность в минутах (20).",
    "Dance": "Танец",
    "Title": "Название",
    "📋  Path copied to clipboard": "📋  Путь скопирован в буфер обмена",
    "Artist": "Исполнитель",
    "🏷 MP3 tag": "🏷 Тег MP3",
    "🔬 Measured": "🔬 Измерено",
    "🔀  Shared between playlists": "🔀  Общие для плейлистов",
    "Action": "Действие",
    "Nothing usable — the decks were left alone.":
        "Ничего пригодного — деки не изменены.",
    "Issue(s)": "Проблемы",
    "Remove song": "Убрать трек",
    "Remove dance": "Убрать танец",
    " tracks": " треков",
    "In your own words — what this list is for (optional):":
        "Своими словами — для чего этот список (необязательно):",
    "Rules the model has to follow:":
        "Правила, которым должна следовать модель:",
    "Claude login:": "Вход в Claude:",
    "📝  Details copied to clipboard":
        "📝  Подробности скопированы в буфер обмена",
    "Mode:": "Режим:",
    "Favorites": "Избранное",
    "Theme": "Тема",
    "Past Competitions": "Прошлые соревнования",
    "Draw tracks from:": "Брать треки из:",
    "Dance Style:": "Программа:",
    "Age Class:": "Возрастная группа:",
    "Start Class:": "Класс:",
    "Dances:": "Танцы:",
    "Rounds  (e.g. 6-3-2-1):": "Туры  (напр. 6-3-2-1):",
    "Paste competition schedule:": "Вставить расписание соревнования:",
    "Competition:": "Соревнование:",
    "Seeds the grid from songs you played at this\n"
    "class before (matching per-class M3U files).":
        "Заполняет сетку треками, которые вы уже ставили в этом\n"
        "классе (подходящие M3U-файлы по классам).",
    "Theme:": "Тема:",
    "Number of tracks:": "Количество треков:",
    "Themes use ID3 year tags + themes.json overrides.\n"
    "Decade themes need year data in your MP3s.":
        "Темы используют теги года ID3 + переопределения в themes.json.\n"
        "Темам по десятилетиям нужен год в ваших MP3.",
    "⏱  Too short — at or below:": "⏱  Слишком короткий — не длиннее:",
    "The cut must cover the 1:30–1:45 TSO play time; default 1:45.":
        "Обрезка должна покрывать время звучания TSO 1:30–1:45; по умолчанию 1:45.",
    "⏳  Too long — above:": "⏳  Слишком длинный — длиннее:",
    "Only flagged when the ⏳ checkbox in the Music-check window is on (Practice playlists); default 4:00.":
        "Отмечается, только если в окне проверки музыки включён флажок ⏳ (плейлисты практики); по умолчанию 4:00.",
    "⚡  Tempo mismatch — deviation above:":
        "⚡  Темп не совпадает — отклонение больше:",
    "Measured tempo vs the filename label (detector ×2, ×3, ×1.5 … slips are excused first); default 10 %.":
        "Измеренный темп против метки в имени файла (промахи детектора ×2, ×3, ×1,5 … сначала прощаются); по умолчанию 10 %.",
    "🔇  Hiss — noise floor above:": "🔇  Шипение — уровень шума выше:",
    "How quiet a track must get somewhere. A clean file reaches its lead-in silence, a tape rip never gets below its own hiss; default −50 dB. Only flagged when the 🔇 checkbox in the Music-check window is on.":
        "Насколько тихим трек должен где-то стать. Чистый файл доходит до тишины перед вступлением, оцифровка с плёнки никогда не опускается ниже собственного шипения; по умолчанию −50 dB. Отмечается, только если в окне проверки музыки включён флажок 🔇.",
    "📄 File name": "📄 Имя файла",
    "Source": "Источник",
    "Speed": "Скорость",
    "— (no BPM tag)": "— (нет тега BPM)",
    "— (not measured)": "— (не измерено)",
    "🔁  Doubled inside one playlist": "🔁  Повтор внутри одного плейлиста",
    "File": "Файл",
    "📌  Reference base (single .m3u)": "📌  Эталонная база (один .m3u)",
    "🎯  Tournament files (compared against)":
        "🎯  Турнирные файлы (с ними сравнивается)",
    "🔁  Doubled inside a playlist": "🔁  Повтор внутри плейлиста",
    "Added": "Добавлено",
    "Last": "Последний раз",
    "Build all caches — librosa…": "Построить все кэши — librosa…",
    "Analyzing audio (timbre)…": "Анализ аудио (тембр)…",
    "Audio analysis": "Аудиоанализ",
    "Measuring loudness (EBU R128)…": "Измерение громкости (EBU R128)…",
    "Loudness analysis": "Анализ громкости",
    "Probing silent stretches…": "Проверка тихих участков…",
    "Silence probe": "Проверка тишины",
    "Separating vocals (Demucs)…": "Отделение вокала (Demucs)…",
    "Vocal separation": "Отделение вокала",
    "Detecting Paso Doble highlights…": "Поиск кульминаций пасодобля…",
    "PD highlight detection": "Распознавание кульминаций PD",
    "✅  No other open playlist to compare against":
        "✅  Нет другого открытого плейлиста для сравнения",
    "✅  Nothing here is in another open playlist":
        "✅  Ничего отсюда нет в другом открытом плейлисте",
    "Remove duplicates": "Убрать дубликаты",
    "🌐  Whole repository — every file under your music repo (global search).\n"
    "🎯  Favorites library — just your tanzcds folder.\n"
    "➕  Both — the repository and the favorites library.":
        "🌐  Весь репозиторий — каждый файл в вашем музыкальном репозитории (глобальный поиск).\n"
        "🎯  Избранная библиотека — только ваша папка tanzcds.\n"
        "➕  Оба — репозиторий и избранная библиотека.",
    "Standard dances": "Стандартные танцы",
    "Latin dances": "Латиноамериканские танцы",
    "Interleave short social-dance rounds — needs those tracks in your library.":
        "Вставлять короткие туры социальных танцев — нужны такие треки в библиотеке.",
    "No Paso Doble": "Без пасодобля",
    "Start with a Latin round": "Начать с латинского тура",
    "Late Wiener Walzer (hold back early / not back-to-back)":
        "Венский вальс позже (придержать в начале / не подряд)",
    "Late Paso Doble (not in the first ~40 songs)":
        "Пасодобль позже (не в первых ~40 треках)",
    "Failed — nothing was changed.": "Не удалось — ничего не изменено.",
    "♻️  Restoring your last session…":
        "♻️  Восстановление последнего сеанса…",
    "Indexing whole repository…": "Индексация всего репозитория…",
    "Build / refresh librosa audio index":
        "Построить / обновить аудиоиндекс librosa",
    "Scanning repository…": "Сканирование репозитория…",
    "Cleaning up database…": "Очистка базы данных…",
    "Re-learning playlist popularity…":
        "Повторное изучение популярности плейлистов…",
    "Loading repository from cache…": "Загрузка репозитория из кэша…",
    "🔊 Audio backend": "🔊 Аудиобэкенд",
    "The audio backend is chosen when the app starts, so the new one takes over after a restart.\n"
    "\n"
    "Restart now?":
        "Аудиобэкенд выбирается при запуске приложения, поэтому новый начнёт работать после перезапуска.\n"
        "\n"
        "Перезапустить сейчас?",
    "The theme, the accent colour and the language are applied while the app starts, so they take over after a restart.\n"
    "\n"
    "Restart now?":
        "Оформление, акцентный цвет и язык применяются при запуске приложения, поэтому вступят в силу после перезапуска.\n"
        "\n"
        "Перезапустить сейчас?",
    "📂  Nothing new — all tracks already in the wishlist":
        "📂  Ничего нового — все треки уже в списке пожеланий",
    "Length": "Длина",
    "Drag <b>.m3u playlists</b> (or audio files) here to check their tracks for the same issues — tempo label vs measured, TSO takt range, play length — plus the playlists' round structure (heat tempo spread).":
        "Перетащите сюда <b>плейлисты .m3u</b> (или аудиофайлы), чтобы проверить их треки на те же проблемы — метка темпа против измерения, диапазон тактов TSO, время звучания — плюс структуру туров в плейлистах (разброс темпа в заходе).",
    "Drag <b>.m3u playlists</b> here to check their track paths against the <b>search folders</b> (Settings). Broken references <b>and valid paths on a different root</b> (e.g. C:) that can be re-rooted there are listed per playlist; <b>🧭 Fix &amp; overwrite</b> rewrites those path lines <b>in place</b> — only the file path changes, every #EXTINF / comment line is kept exactly as-is.":
        "Перетащите сюда <b>плейлисты .m3u</b>, чтобы проверить пути их треков по <b>папкам поиска</b> (Настройки). Битые ссылки <b>и рабочие пути на другом диске</b> (напр. C:), которые можно перенести туда, перечисляются по плейлистам; <b>🧭 Исправить &amp; перезаписать</b> переписывает эти строки путей <b>на месте</b> — меняется только путь к файлу, каждая строка #EXTINF / комментария сохраняется как есть.",
    "↶  Nothing to undo": "↶  Нечего отменять",
    "↷  Nothing to redo": "↷  Нечего повторять",
    "✅  No wishlist tracks are in an open playlist":
        "✅  Ни одного трека из списка пожеланий нет в открытом плейлисте",
    "Heat": "Заход",
    "🔁  Cleared all replacement marks": "🔁  Все отметки замены сняты",
    "✅  Kept all titles": "✅  Все треки сохранены",
    "✅  No duplicate titles in this list":
        "✅  В этом списке нет повторяющихся треков",
    "Already in the list — nothing added":
        "Уже в списке — ничего не добавлено",
    "⭐  Already in the wishlist — nothing added":
        "⭐  Уже в списке пожеланий — ничего не добавлено",
    "Replace the existing track with this one?":
        "Заменить существующий трек этим?",
    "Remove heat": "Убрать заход",
    "Remove round": "Убрать тур",
    "Remove backup": "Убрать запасной",
    "Remove this backup song?": "Убрать этот запасной трек?",
    "⬆  Backup moved up into the empty slot":
        "⬆  Запасной трек поднялся на свободное место",
    "Couldn't read the dropped track(s).":
        "Не удалось прочитать перетащенные треки.",
    "📊 Loudness probe failed": "📊 Ошибка измерения громкости",
    "🔇 Silence probe failed": "🔇 Ошибка проверки тишины",
    "Slot defaults — apply to every page":
        "Значения мест по умолчанию — для всех страниц",
    "Pad keys — travel with the pad":
        "Клавиши пэдов — переезжают вместе с пэдом",
    "🔈  announcing…": "🔈  объявление…",
    "🛑  held": "🛑  удержание",
    "🐂  detecting highlights…": "🐂  поиск кульминаций…",
    "🐂  plays to the end": "🐂  играет до конца",
    "🎯  stop reached — ⏯ to go on":
        "🎯  остановка достигнута — ⏯, чтобы продолжить",
    "🐂  Stop Paso Doble after highlight":
        "🐂  Останавливать пасодобль после кульминации",
    "⏭  Auto-advance to next song": "⏭  Автопереход к следующему треку",
    "over the first bars": "поверх первых тактов",
    "before the music starts": "до начала музыки",
    "⏸  No pause between songs": "⏸  Без паузы между треками",
    "🔁  Start again at the end": "🔁  В конце начать сначала",
    "⏹  Stop:":
        "⏹  Стоп:",
    "Never":
        "Никогда",
    "After this title":
        "После этого трека",
    "After … titles":
        "После … треков",
    "At …":
        "В …",
    "Let the music stop by itself: after the title playing now,\nafter a number of titles (the one playing now is the first),\nor with the first title that ends at or after a time of day.\n\nA title is not cut: it plays to its end, then the next one\nwaits on the player for ⏯ — unless an \"At …\" time is set to\nfade it. A ⏭ skip does not count as an end.\n\nSet for this evening only — it is not saved.\n\nNeeds ⏭ auto-advance.":
        "Музыка остановится сама: после текущего трека,\nпосле нескольких треков (текущий — первый)\nили с первым треком, который закончится в заданное время или позже.\n\nТрек не обрывается: он играет до конца, а следующий\nждёт в плеере нажатия ⏯ — если только время «В …» не задано\nс затуханием. Пропуск ⏭ не считается концом.\n\nТолько на этот вечер — не сохраняется.\n\nНужен ⏭ автопереход.",
    "play it to its end":
        "доиграть до конца",
    "fade out at the time":
        "затухание в это время",
    "hybrid: fade if ≥ 1:30 played":
        "гибрид: затухание, если ≥ 1:30",
    "What the title playing at the time does:\n\nPlay it to its end — the first title that ends at or after the\ntime is the last.\nFade out at the time — it fades out the moment the time comes.\nHybrid — it fades if it had played 1:30 by then, a younger\none plays to its end.\n\nA title that starts after the time always plays to its end.\nThis choice is remembered.":
        "Что делает трек, играющий в это время:\n\nДоиграть до конца — последний трек тот, который закончится\nв это время или позже.\nЗатухание в это время — он затухает, как только наступает время.\nГибрид — он затухает, если к тому времени играл 1:30;\nболее короткий доигрывает до конца.\n\nТрек, начавшийся после этого времени, всегда доигрывает до конца.\nЭтот выбор запоминается.",
    "The first title that ends at or after this time is the last.\nA time already past today means after midnight.":
        "Первый трек, который закончится в это время или позже, — последний.\nВремя, уже прошедшее сегодня, означает после полуночи.",
    "⏹  Stops after this title":
        "⏹  Остановка после этого трека",
    "⏹  Stops after %d titles":
        "⏹  Остановка через треков: %d",
    "⏹  Stops at %s":
        "⏹  Остановка в %s",
    "⏹  Stopped as planned":
        "⏹  Остановлено по плану",
    "⏹ Stopped as planned — ⏯ plays the next title.":
        "⏹ Остановлено по плану — ⏯ запускает следующий трек.",
    "The evening stopped %d min ago, with %d titles played.":
        "Вечер прервался %d мин назад, сыграно треков: %d.",
    "Grey them out again? Nothing starts by itself.":
        "Снова отметить их серым? Ничего не начнётся само.",
    "The %d titles played this evening grey out again.":
        "Сыгранные сегодня треки (%d) снова станут серыми.",
    "▶ Pick up the evening?":
        "▶ Продолжить вечер?",
    "▶  Pick up":
        "▶  Продолжить",
    "Start fresh":
        "Начать заново",
    "▶ Evening picked up — %d titles played.":
        "▶ Вечер продолжен — сыграно треков: %d.",
    "Pause between songs:": "Пауза между треками:",
    "🔈  Announce next dance": "🔈  Объявлять следующий танец",
    "…with heat": "…с заходом",
    "🔊  Equalize volume (R128)": "🔊  Выравнивать громкость (R128)",
    "🖼  Show artwork — a cover next to the title on the player card":
        "🖼  Показывать обложку — картинка рядом с названием на карточке плеера",
    "〰  Show waveform — the title's waveform in place of the player card's seek bar":
        "〰  Показывать волну — волна трека вместо полосы перемотки на карточке плеера",
    "Draw the playing title's waveform in place of the seek bar: quiet\n"
    "passages, the skipped silence, the Paso Doble highlights and\n"
    "where the fade-out of a timed cut begins. Click it to jump.":
        "Рисовать волну играющего трека вместо полосы перемотки: тихие\n"
        "места, пропускаемую тишину, кульминации пасодобля и\n"
        "где начинается затухание обрезки по времени. Щелчок — переход.",
    "The waveform of the title — what has played is blue, all of it\n"
    "red in the final seconds. The broad orange bar is where it plays.\n"
    "Shaded: silence the player skips · thin orange: Paso Doble\n"
    "highlights · red-tinted: the fade-out of a timed cut · gold: the\n"
    "fade-in · green line: where the title starts.\n"
    "Click to jump there.":
        "Волна трека — сыгранное окрашено синим, в последние секунды\n"
        "всё красное. Широкая оранжевая полоса — где он играет.\n"
        "Заштриховано: тишина, которую плеер пропускает · тонкий оранжевый:\n"
        "кульминации пасодобля · красноватый: затухание обрезки по времени ·\n"
        "золотой: нарастание · зелёная линия: где начинается трек.\n"
        "Щёлкните, чтобы перейти туда.",
    "▶️  Double-click starts the title": "▶️  Двойной щелчок запускает трек",
    "🎚  TSO pitch to the heat tempo": "🎚  TSO: подтягивать к темпу захода",
    "↩  Remember where a title stopped": "↩  Запоминать, где трек остановился",
    "☀  Keep the screen awake": "☀  Не гасить экран",
    "Show the transport on this screen":
        "Показывать управление на этом экране",
    "Show the title played before this one": "Показывать предыдущий трек",
    "Show the timetable  ·  T\n"
    "Right-click to edit it":
        "Показать расписание  ·  T\n"
        "Правый щелчок — редактировать",
    "Close the presenter screen": "Закрыть экран ведущего",
    "Previous title": "Предыдущий трек",
    "Play / pause": "Воспроизведение / пауза",
    "Next title": "Следующий трек",
    "Over to the break music": "Перейти к музыке паузы",
    "Time": "Время",
    "Until": "До",
    "What": "Что",
    "Note": "Заметка",
    "♪ Takt meter": "♪ Измеритель такта",
    "Takt count:": "Счёт тактов:",
    "Target:": "Цель:",
    " Takt/min": " тактов/мин",
    "Correction needed:": "Нужная коррекция:",
    "Apply": "Применить",
    "Apply this correction to the tempo fader.":
        "Применить эту коррекцию к фейдеру темпа.",
    "Next dances": "Следующие танцы",
    "⌨  Keyboard": "⌨  Клавиатура",
    "Space": "Пробел",
    "Play / stop the selected song":
        "Воспроизвести / остановить выбранный трек",
    "Seek 30 s back / forward while playing":
        "Перемотка на 30 с назад / вперёд во время воспроизведения",
    "Ctrl + R  or  Ctrl + N": "Ctrl + R  или  Ctrl + N",
    "Re-roll (regenerate) the selected song":
        "Подобрать заново (перегенерировать) выбранный трек",
    "Save the focused playlist / wishlist as M3U":
        "Сохранить активный плейлист / список пожеланий как M3U",
    "Save the whole session state (decks, wishlists, layout)":
        "Сохранить всё состояние сеанса (деки, списки пожеланий, раскладку)",
    "Undo / redo (also Ctrl + Shift + Z)":
        "Отменить / повторить (также Ctrl + Shift + Z)",
    "Ctrl + X  or  Ctrl + W": "Ctrl + X  или  Ctrl + W",
    "Close the active dialog or the preview mini player":
        "Закрыть активный диалог или мини-плеер предпрослушивания",
    "Remove the selected rows (wishlist) / empty the selected heat slots (deck)":
        "Убрать выбранные строки (список пожеланий) / очистить выбранные места захода (дек)",
    "Del  with nothing selected": "Del  без выделения",
    "Clear that whole playlist / wishlist (confirmed) — same when every song is selected at once":
        "Очистить весь этот плейлист / список пожеланий (с подтверждением) — так же, когда выбраны сразу все треки",
    "Clear the focused playlist / wishlist (confirmed), wherever the cursor is":
        "Очистить активный плейлист / список пожеланий (с подтверждением), где бы ни стоял курсор",
    "Dynamic deck: remove the whole heat under the cursor (on a ↳ backup row: just that backup)":
        "Динамический дек: убрать весь заход под курсором (на строке запасного ↳ — только этот запасной)",
    "Dynamic deck or free running order: mark / unmark the selected song(s) for potential replace (❗ orange). Ctrl + 1 does the same, but only while the 🎛 cartwall is hidden — the wall claims that key for its first pad":
        "Динамический дек или свободный порядок: отметить / снять отметку возможной замены у выбранных треков (❗ оранжевый). Ctrl + 1 делает то же, но только пока 🎛 картволл скрыт — стена забирает эту клавишу для первого пэда",
    "F2  in the 📅 tournament tree": "F2  в 📅 дереве турниров",
    "Rename the entry under the cursor (Del removes it)":
        "Переименовать запись под курсором (Del удаляет её)",
    "Ctrl + A  in 🏆 Tournaments": "Ctrl + A  в 🏆 Турнирах",
    "Mark every slot of the folder, or every entry of the tree — Del and a drag then take them all":
        "Выделить все места папки или все записи дерева — Del и перетаскивание тогда захватывают их все",
    "Click a star in the ★ column": "Щелчок по звезде в столбце ★",
    "Rate the title; click the star the rating ends on to clear it":
        "Оценить трек; щелчок по звезде, на которой заканчивается оценка, сбрасывает её",
    "Find a title or a genre in the focused list. A title steps to the next "
    "match; a genre highlights every row of it at once":
        "Найти название или жанр в активном списке. Название переходит к "
        "следующему совпадению, жанр подсвечивает все свои строки сразу",
    "Esc  in the 🖥 presenter window": "Esc  в 🖥 окне ведущего",
    "This cheat sheet": "Эта шпаргалка",
    "Nothing found": "Ничего не найдено",
    "🔍  Find a key or an action…": "🔍  Найти клавишу или действие…",
    "⚙  Settings…  (F12 / Ctrl+Alt+S)": "⚙  Настройки…  (F12 / Ctrl+Alt+S)",
    "Open ⚙ Settings": "Открыть ⚙ Настройки",
    "Fullscreen on / off — with date and time in the status bar":
        "Полный экран вкл. / выкл. — с датой и временем в строке состояния",
    "🖱  Mouse": "🖱  Мышь",
    "Click a round / dance header": "Щелчок по заголовку тура / танца",
    "Collapse or expand that section": "Свернуть или развернуть этот раздел",
    "Double-click a deck title": "Двойной щелчок по имени дека",
    "Rename the playlist / wishlist":
        "Переименовать плейлист / список пожеланий",
    "▾ / ▸ arrow in a deck header": "Стрелка ▾ / ▸ в заголовке дека",
    "Fold the deck to a header tab (click the tab to reopen)":
        "Свернуть дек во вкладку заголовка (щелчок по вкладке открывает снова)",
    "Drag a row": "Перетащить строку",
    "Move a song to another slot, deck, wishlist — or drop it into Explorer / UltraMixer":
        "Переместить трек на другое место, в другой дек или список пожеланий — или бросить его в Проводник / UltraMixer",
    "Drag a dance header": "Перетащить заголовок танца",
    "Reorder the dance columns of a static deck":
        "Изменить порядок столбцов танцев статического дека",
    "Right-click ▸ 🔍 Find a genre": "Правый щелчок ▸ 🔍 Найти жанр",
    "Jump to a song by name; or highlight every row of a genre at once":
        "Перейти к треку по названию; или подсветить все строки жанра сразу",
    "Ctrl + drag onto a filled slot": "Ctrl + перетаскивание на занятое место",
    "Dynamic deck: replace the song in that slot with the dragged one":
        "Динамический дек: заменить трек на этом месте перетаскиваемым",
    "Drop a file from outside": "Бросить файл извне",
    "Replace a slot / add to a wishlist (.m3u on a deck imports it)":
        "Заменить место / добавить в список пожеланий (.m3u на деке импортируется)",
    "▶ or Space on a 📚 library row": "▶ или Пробел на строке 📚 библиотеки",
    "Preview that track in the mini player":
        "Прослушать этот трек в мини-плеере",
    "Double-click a 📚 library row": "Двойной щелчок по строке 📚 библиотеки",
    "Open the track in your external audio player — when ⚙ Settings → 🔊 Sound & player allow it":
        "Открыть трек во внешнем аудиоплеере — если это разрешено в ⚙ Настройки → 🔊 Звук & плеер",
    "📂  Double-click on a title in 📚 the library:":
        "📂  Двойной щелчок по треку в 📚 библиотеке:",
    "<b>📚 Library</b>":
        "<b>📚 Библиотека</b>",
    "Only for 📚 the library and the 🏆 lists while planning. In ▶ Playing mode a double-click always plays or cues the title.":
        "Только для 📚 библиотеки и списков 🏆 при планировании. В режиме ▶ Воспроизведение двойной щелчок всегда играет или ставит трек на очередь.",
    "Nothing":
        "Ничего",
    "Open external player":
        "Открыть во внешнем плеере",
    "What a double-click on a title does in 📚 the library and the 🏆\ntournament lists.\n\nNothing: the title stays as it is; ▶ plays it.\nOpen external player: the program your system plays music with\n(on a Mac, Music) — in the decks and the dialogs too.\nEdit tags: the 🏷 Tags editor, where you choose what Save\nwrites into the file and what stays in the app.\n\nRight-click still offers all of it, and in Playing mode a\ndouble-click always plays or cues the title.":
        "Что делает двойной щелчок по треку в 📚 библиотеке и в 🏆\nтурнирных списках.\n\nНичего: трек остаётся как есть; ▶ запускает его.\nОткрыть во внешнем плеере: программа, которой система воспроизводит\nмузыку (на Mac — «Музыка»), — также в деках и диалогах.\nИзменить теги: редактор 🏷 Теги, где вы выбираете, что Сохранить\nзапишет в файл, а что останется в приложении.\n\nПравый щелчок по-прежнему предлагает всё это, а в режиме воспроизведения\nдвойной щелчок всегда запускает или загружает трек.",
    "Edit tags":
        "Изменить теги",
    "Album:":
        "Альбом:",
    "Genre:":
        "Жанр:",
    "▶ / ■ in a row": "▶ / ■ в строке",
    "Play / stop exactly that song":
        "Воспроизвести / остановить именно этот трек",
    "↺ in a row / header": "↺ в строке / заголовке",
    "Re-roll that song / every song of the dance or round":
        "Подобрать заново этот трек / все треки танца или тура",
    "Drop files on a pad": "Бросить файлы на пэд",
    "Assign that sample — a multi-select fills the free pads after it (an empty pad can also be clicked to browse)":
        "Назначить этот сэмпл — множественный выбор заполняет свободные пэды после него (по пустому пэду можно и щёлкнуть, чтобы выбрать файл)",
    "Click a pad": "Щелчок по пэду",
    "Fire it over the running music; click again to fade it out":
        "Запустить его поверх играющей музыки; повторный щелчок уводит его в затухание",
    "Fire the first nine pads of the page on screen (works from anywhere while the wall is shown, and takes Ctrl + 1 away from the mark shortcut above)":
        "Запустить первые девять пэдов показанной страницы (работает откуда угодно, пока стена видна, и забирает Ctrl + 1 у сочетания отметки выше)",
    "Right-click a pad": "Правый щелчок по пэду",
    "🎨 colour straight away, or Settings… for label, volume, its own key, 🔁 endless repeat and whether it ducks the music":
        "🎨 сразу цвет или Настройки… для подписи, громкости, своей клавиши, 🔁 бесконечного повтора и того, приглушает ли он музыку",
    "Drag a pad onto another": "Перетащить пэд на другой",
    "Swap the two pads": "Поменять два пэда местами",
    "Stop every pad (same as ⏹ Stop all)":
        "Остановить все пэды (то же, что ⏹ Остановить все)",
    "⚙  Settings…": "⚙  Настройки…",
    "🎨  Colour": "🎨  Цвет",
    "🗑  Clear pad": "🗑  Очистить пэд",
    "  (%s pads)": "  (пэдов: %s)",
    "Wall default": "По умолчанию картволла",
    "Grey": "Серый",
    "Green": "Зелёный",
    "Red": "Красный",
    "Olive": "Оливковый",
    "Purple": "Фиолетовый",
    "Amber": "Янтарный",
    "White": "Белый",
    "📂  Show in Explorer (not saved as a file yet)":
        "📂  Показать в Проводнике (ещё не сохранено в файл)",
    "Unfold this wishlist": "Развернуть этот список пожеланий",
    "Fold to a tab": "Свернуть во вкладку",
    "🔁  Mark for potential replace\tCtrl+M":
        "🔁  Отметить для возможной замены\tCtrl+M",
    "🔁  Unmark (potential replace)\tCtrl+M":
        "🔁  Снять отметку (возможная замена)\tCtrl+M",
    "➕  Create new round": "➕  Создать новый тур",
    "➕  Insert new round after %s": "➕  Вставить новый тур после %s",
    "🗑  Remove %s from this round (keep other dances)":
        "🗑  Убрать %s из этого тура (другие танцы остаются)",
    "🗑  Remove %s from all rounds and heats":
        "🗑  Убрать %s из всех туров и заходов",
    "🔒  Back to a planned grid": "🔒  Вернуться к запланированной сетке",
    "🔒  Switch to static mode": "🔒  Перейти в статический режим",
    "🔓  Switch to dynamic mode": "🔓  Перейти в динамический режим",
    "🧹  Empty this wishlist": "🧹  Очистить этот список пожеланий",
    "Columns in every playlist": "Столбцы в каждом плейлисте",
    "Columns in every wishlist": "Столбцы в каждом списке пожеланий",
    "Columns in every party list": "Столбцы в каждом списке вечеринки",
    "Σ  %d song": "Σ  треков: %d",
    "Σ  %d songs": "Σ  треков: %d",
    "other": "другое",
    "✦new": "✦новый",
    "new": "новый",
    "Round": "Тур",
    "Female": "Женский",
    "Male": "Мужской",
    "Mixed": "Смешанный",
    # ── 🎙 the voice line under 🔈 Announce next dance ──
    "🎙  Announcement voice:": "🎙  Голос объявлений:",
    "The voice, the heat number and whether the dance is\nnamed over the music or before it are set in\n⚙ Settings → 🔊 Sound & player.": "Голос, номер захода и то, звучит ли объявление поверх музыки\nили перед ней, задаются в\n⚙ Настройки → 🔊 Звук & плеер.",
    "Female voice": "Женский голос",
    "Male voice": "Мужской голос",
    "Mixed voices": "Смешанные голоса",
    "with heat": "с заходом",
    "heat only": "только группа",
    "🔢  Only the heat, not the dance (practice)": "🔢  Только группа, без танца (тренировка)",
    "On: every call says just “Heat 1”, without “Next dance” and\n"
    "without the dance, whatever the two boxes above say.\n"
    "Where there is no heat to call (or one past 8, which was never\n"
    "recorded), the dance is called as usual.":
        "Вкл.: каждое объявление говорит только «Группа 1», без «Следующий танец»\n"
        "и без танца, что бы ни стояло в двух флажках выше.\n"
        "Если группы нет (или она больше 8 — такие не записаны),\n"
        "танец объявляется как обычно.",
    "📣  Say “Next dance” before the dance": "📣  Говорить «Следующий танец» перед танцем",
    "On: the pause announces “Next dance: Rumba”.\n"
    "Off: just “Rumba” (with the heat number, if that is on).\n"
    "\n"
    "A dance named as its music starts is always said without it.":
        "Вкл.: пауза объявляет «Следующий танец: Румба».\n"
        "Выкл.: только «Румба» (с номером захода, если он включён).\n"
        "\n"
        "Танец, объявляемый при старте музыки, всегда без этого.",
    "🗣  Dance is named:": "🗣  Танец объявляется:",
    "over the music": "поверх музыки",
    "before the music": "перед музыкой",
    "🎉  Party check": "🎉  Проверка вечеринки",
    "Check the party list — rounds, the late WW / PD rules,\n"
    "duplicates, takt and over-long titles.":
        "Проверить список вечеринки — туры, правила «венский вальс позже» / «пасодобль позже»,\n"
        "дубликаты, такт и слишком длинные треки.",
    "Party list": "Список вечеринки",
    "🎉 <b>%s</b> — %d titles, 1 finding":
        "🎉 <b>%s</b> — треков: %d, замечаний: 1",
    "🎉 <b>%s</b> — %d titles, %d findings":
        "🎉 <b>%s</b> — треков: %d, замечаний: %d",
    "✅  Nothing to report — the list reads like one the party builder would have made.":
        "✅  Замечаний нет — список выглядит так, будто его составил генератор вечеринок.",
    "↻  Check again": "↻  Проверить снова",
    "🔁 Rounds": "🔁 Туры",
    "⏳ Spacing": "⏳ Интервалы",
    "👯 Duplicates": "👯 Дубликаты",
    "⏱ Length": "⏱ Длина",
    "row %d": "строка %d",
    "Standard rounds": "Туры стандарта",
    "Latin rounds": "Латинские туры",
    "Social rounds": "Туры социальных танцев",
    "“%s” is %d title long, not 3 — from ": "«%s» — треков: %d, а не 3 — с ",
    "“%s” is %d titles long, not 3 — from ": "«%s» — треков: %d, а не 3 — с ",
    "a round": "тур",
    "the Samba plays two %s running, the second at ":
        "самба звучит в двух %s подряд, вторая — на ",
    "“%s” opens the section with %s, not %s — from ":
        "«%s» открывает раздел танцем %s, а не %s — с ",
    "nothing": "ничего",
    "two %s run back to back — “%s” starts at ":
        "два %s подряд — «%s» начинается на ",
    ", with no round of the other section between them.":
        ", без тура другого раздела между ними.",
    "the %s never plays — %d %s and not one of them.":
        "%s не звучит ни разу — %d %s, и ни в одном.",
    "the %s sits out %d %s running, from ":
        "%s пропускает %d %s подряд, начиная с ",
    "the Wiener Walzer opens the evening at ":
        "венский вальс открывает вечер на ",
    " — “late WW” holds it back until %d titles have played.":
        " — «венский вальс позже» придерживает его, пока не прозвучит треков: %d.",
    "a Paso Doble plays at ": "пасодобль звучит на ",
    " — “late PD” holds the first one back until %d titles have played.":
        " — «пасодобль позже» придерживает первый, пока не прозвучит треков: %d.",
    "two Paso Dobles sit %d Latin round apart, the second at ":
        "между двумя пасодоблями латинских туров: %d, второй — на ",
    "two Paso Dobles sit %d Latin rounds apart, the second at ":
        "между двумя пасодоблями латинских туров: %d, второй — на ",
    " — the rule is %d.": " — по правилу: %d.",
    "“%s” plays %d times, at ": "«%s» звучит %d раз(а), на ",
    "“%s” and “%s” look like the same song, at ":
        "«%s» и «%s» похожи на один и тот же трек, на ",
    "“%s” is a %s at T%d, outside T%d–T%d — ":
        "«%s» — %s на T%d, вне T%d–T%d — ",
    "“%s” runs %d:%02d, past %d:%02d — ":
        "«%s» длится %d:%02d, дольше %d:%02d — ",
    "Class %s": "Класс %s",
    "★ Rarely (1–%d)": "★ Редко (1–%d)",
    "★ Proven (≥%d)": "★ Проверенные (≥%d)",
    "Filter by how the track was used so far:\n"
    "✦ never — in none of your playlists\n"
    "★ rarely / proven — in 1–%d vs. %d+ of them\n"
    "📅 not since — played, but the newest playlist\n"
    "carrying it is that old (the year comes from the\n"
    "playlist's path; undated lists don't count as old).":
        "Фильтр по тому, как трек использовался до сих пор:\n"
        "✦ никогда — ни в одном вашем плейлисте\n"
        "★ редко / проверенные — в 1–%d против %d+ из них\n"
        "📅 не с — звучал, но самый новый плейлист\n"
        "с ним настолько стар (год берётся из пути\n"
        "плейлиста; списки без даты не считаются старыми).",
    "🎄 Seasonal / Christmas": "🎄 Сезонные / Рождество",
    "🎺 Anthems": "🎺 Гимны",
    "🎶 Background / non-dance": "🎶 Фон / не для танцев",
    "⏱️ Wrong tempo / not tournament": "⏱️ Неверный темп / не для турнира",
    "👥 Duplicates / raw versions": "👥 Дубликаты / черновые версии",
    # The deck/library column with the cleaned-up file name.
    "Filename": "Имя файла",
    # …and the one with the ID3 album tag.
    "Album": "Альбом",
    # ⚙ Settings → 🔊 Sound & player: an output per source.
    "<b>🔈 Outputs</b> — where each part of the evening is heard:":
        "<b>🔈 Выходы</b> — где звучит каждая часть вечера:",
    "🎵  Music:":
        "🎵  Музыка:",
    "🔈  Announcements:":
        "🔈  Объявления:",
    "System default (follows the OS)":
        "Системное по умолчанию (следует за системой)",
    "Same as the music":
        "Как у музыки",
    "Every output the operating system lists can be chosen. On a sound card\n"
    "with several outputs, each pair that shows up as a device of its own\n"
    "(\"Out 3/4\" next to \"Out 1/2\") can take a source of its own. A card\n"
    "listed as ONE multichannel device offers its further pairs as\n"
    "\"— Out 3/4\" entries. The music on such an entry changes its\n"
    "pitch with the tempo fader, like a turntable.\n"
    "\n"
    "A card that is not plugged in plays on the system default until it is back.":
        "Можно выбрать любой выход, который показывает операционная система. На\n"
        "звуковой карте с несколькими выходами каждая пара, видимая как отдельное\n"
        "устройство (\"Out 3/4\" рядом с \"Out 1/2\"), может получить свой источник.\n"
        "Карта, видимая как ОДНО многоканальное устройство, предлагает остальные пары\n"
        "как пункты «— Out 3/4». Музыка на таком пункте меняет с регулятором темпа\n"
        "и высоту тона, как проигрыватель пластинок.\n"
        "\n"
        "Неподключённая карта играет на системном устройстве, пока она не вернётся.",
    "🔀 A card listed as one multichannel device offers its further outputs (\"— Out 3/4\") to every source. The music on such a pair changes its pitch with the tempo fader, like a turntable: faster sounds higher, slower lower. Only a whole output keeps the pitch while the tempo changes.":
        "🔀 Карта, видимая как одно многоканальное устройство, предлагает остальные выходы («— Out 3/4») всем источникам. Музыка на такой паре меняет с регулятором темпа и высоту тона, как проигрыватель пластинок: быстрее звучит выше, медленнее ниже. Только целый выход сохраняет высоту тона при изменении темпа.",
    "Music on a channel pair":
        "Музыка на паре каналов",
    "On %s the tempo fader changes the pitch along with the speed, like a turntable: faster sounds higher, slower lower.\n\nOnly a whole output keeps the pitch. Play the music on this pair anyway?":
        "На %s регулятор темпа меняет вместе со скоростью и высоту тона, как проигрыватель пластинок: быстрее звучит выше, медленнее ниже.\n\nТолько целый выход сохраняет высоту тона. Всё равно играть музыку на этой паре?",
    "⚠  %s (not connected)":
        "⚠  %s (не подключено)",
    "The music plays on %s — click for the sound settings.":
        "Музыка идёт на %s — нажмите, чтобы открыть настройки звука.",
    "🔈 %s is not connected — playing on the system default until it is back.":
        "🔈 %s не подключено — звук идёт на системное устройство, пока оно не вернётся.",
    # ⚙ Settings → 🔊 Sound & player: 🎧 pre-listen.
    "🎧  Pre-listen:":
        "🎧  Предпрослушивание:",
    "▶ in the library pane, the 🏆 pane, the Similar window and the\n"
    "event plan plays here, with a mini player of its own, and the\n"
    "music keeps running. Refused while it is the output the music\n"
    "plays on, unless it is the only output. \"Same as the music\": they\n"
    "play on the music's player.":
        "▶ в панели библиотеки, панели 🏆, окне похожих треков и плане\n"
        "мероприятия звучит здесь, со своим мини-плеером, а музыка играет\n"
        "дальше. Отклоняется, пока это выход музыки,\n"
        "если он не единственный.\n"
        "«Как у музыки»: они звучат в плеере музыки.",
    "🎧 The pre-listen output is not connected, and the system default is the music's own output.":
        "🎧 Выход предпрослушивания не подключён, а системный выход по умолчанию — тот же, что у музыки.",
    "🎧 Pre-listen refused — its output is the one the music plays on. Choose another in ⚙ Settings.":
        "🎧 Предпрослушивание отклонено — его выход тот же, что у музыки. Выберите другой в ⚙ Настройках.",
    # ⌨ Desk keys: the dialog, the volume steps and the F1 sheet.
    "🔼  Music volume up":
        "🔼  Музыку громче",
    "🔽  Music volume down":
        "🔽  Музыку тише",
    "🎛  Cartwall volume (fader or knob)":
        "🎛  Громкость картволла (фейдер или регулятор)",
    "🔼  Cartwall volume up":
        "🔼  Картволл громче",
    "🔽  Cartwall volume down":
        "🔽  Картволл тише",
    "◀  Previous cartwall page":
        "◀  Предыдущая страница картволла",
    "▶  Next cartwall page":
        "▶  Следующая страница картволла",
    "Cartwall volume — every pad, apart from the music volume.\n"
    "Also on a controller fader and the desk keys (⌨).":
        "Громкость картволла — все пэды, отдельно от громкости музыки.\n"
        "Также фейдером контроллера и клавишами пульта (⌨).",
    "🎚  Tempo / pitch (fader or knob)":
        "🎚  Темп / питч (фейдер или ручка)",
    "⏫  Tempo up":
        "⏫  Темп быстрее",
    "⏬  Tempo down":
        "⏬  Темп медленнее",
    "🎯  Tempo back to ±0 %":
        "🎯  Темп обратно на ±0 %",
    "⌨  Keys":
        "⌨  Клавиши",
    "Keys: the pads' and the desk's, in one window":
        "Клавиши: пэдов и пульта — в одном окне",
    "⌨  Desk keys":
        "⌨  Клавиши пульта",
    "⌨  Keys…":
        "⌨  Клавиши…",
    "The player's actions on the keyboard, from anywhere in the window — the same ones the 📱 phone and a 🎛 controller run.":
        "Действия плеера на клавиатуре, из любого места окна — те же, что выполняют 📱 телефон и 🎛 контроллер.",
    "💡 A Stream Deck or a macro keypad can send F13–F24: no keyboard has them, so they never clash. A MIDI pad goes through 🎛 Controller instead (on Windows via loopMIDI).":
        "💡 Stream Deck или макро-клавиатура могут посылать F13–F24: их нет ни на одной клавиатуре, поэтому они никогда не конфликтуют. MIDI-пэд подключается через 🎛 Контроллер (в Windows через loopMIDI).",
    "↺  Restore defaults":
        "↺  Восстановить по умолчанию",
    "⚠ moved to %s": "⚠ перенесено на %s",
    "⚠ The app uses this key":
        "⚠ Приложение использует эту клавишу",
    "Remove this key": "Убрать эту клавишу",
    "Another key for this action": "Ещё одна клавиша для этого действия",
    "⚠ Also on %s — that one keeps it":
        "⚠ Уже на %s — там и остаётся",
    "🏷 No class": "🏷 Без класса",
    "🏷  Leave titles without a class out of generated playlists":
        "🏷  Не включать треки без класса в создаваемые плейлисты",
    "Competition titles whose comment carries no class tag are listed\n"
    "under the '🏷 No class' library category either way. Ticked, they\n"
    "also stay out of the generated playlists, the warm-up and the AI search.":
        "Турнирные треки без тега класса в комментарии в любом случае попадают\n"
        "в категорию библиотеки «🏷 Без класса». Если отмечено, они также не\n"
        "попадают в создаваемые плейлисты, разминку и поиск с ИИ.",
    "🏷 Only with a class": "🏷 Только с классом",
    "Hide competition titles without a class tag — the class filter\n"
    "shows those for every class.":
        "Скрыть турнирные треки без тега класса — фильтр по классу\n"
        "показывает их для любого класса.",
    "(%d/%d tracks)": "(%d/%d треков)",
    "▶  Play": "▶  Воспроизвести",
    "⏱  Length": "⏱  Длина",
    "★  Rating": "★  Оценка",
    "Class tags from the MP3 comment field":
        "Теги классов из поля комментария MP3",
    "Newest playlist carrying this track":
        "Самый новый плейлист с этим треком",
    "Never played": "Ни разу не звучал",
    "Played, but none of those playlists is dated":
        "Звучал, но ни у одного из этих плейлистов нет даты",
    "⚡ Light — librosa/ffmpeg, works in every install (lite build)":
        "⚡ Лёгкий — librosa/ffmpeg, работает в любой установке (лёгкая сборка)",
    "⚡ Light — ffmpeg, works in every install (player build)":
        "⚡ Лёгкий — ffmpeg, работает в любой установке (сборка плеера)",
    "🔬  Analyze audio (timbre) — %d files to do":
        "🔬  Анализ аудио (тембр) — осталось файлов: %d",
    "🔬  Re-analyze audio (timbre)  ✓ all cached":
        "🔬  Повторный анализ аудио (тембр)  ✓ всё в кэше",
    "🎚️  librosa indexed": "🎚️  librosa проиндексирован",
    "🎼  Chroma indexed": "🎼  Chroma проиндексирован",
    "📊  Loudness measured": "📊  Громкость измерена",
    "🐂  PD highlights detected": "🐂  Кульминации PD найдены",
    "🔇  Silences probed": "🔇  Тишина проверена",
    "🧠  MERT indexed": "🧠  MERT проиндексирован",
    "🧠  MERT 'sounds-alike' index": "🧠  Индекс MERT «звучит похоже»",
    "🎙️  Analyze vocals (Demucs)…": "🎙️  Анализ вокала (Demucs)…",
    "  – not installed": "  – не установлено",
    "The values a heat is run with — pressed to get back to them after a party list has pulled the panel somewhere else.":
        "Значения, с которыми идёт заход, — нажмите, чтобы вернуть их после того, как список вечеринки увёл панель куда-то ещё.",
    "Applied by itself as soon as you play from the 🤸 Practice / party list, and switched back when a tournament deck takes over.":
        "Применяется само, как только вы играете из списка 🤸 практики / вечеринки, и возвращается обратно, когда управление берёт турнирный дек.",
    "An onboard sound card un-mutes its output stage the moment an app\n"
    "opens it, and the amplifier carries that hiss across the hall — you\n"
    "hear it start with the app and stop when it closes, whether or not\n"
    "anything is playing.\n"
    "\n"
    "Handing the device back after %.0f s of silence takes it away. The cost is the soft click the card makes re-opening it\n"
    "for the next title, so only switch this on if you hear the hiss.":
        "Встроенная звуковая карта снимает приглушение выходного каскада в тот момент,\n"
        "когда приложение её открывает, и усилитель разносит это шипение по всему залу — вы\n"
        "слышите, как оно начинается с приложением и прекращается при его закрытии, играет что-то или нет.\n"
        "\n"
        "Отдача устройства после %.0f с тишины убирает его. Цена — тихий щелчок карты при повторном открытии\n"
        "для следующего трека, поэтому включайте это, только если слышите шипение.",
    "⚠️  Not read — %s": "⚠️  Не прочитано — %s",
    "🧹  Removed %d title already in another playlist":
        "🧹  Убрано треков, уже стоящих в другом плейлисте: %d",
    "🧹  Removed %d titles already in another playlist":
        "🧹  Убрано треков, уже стоящих в другом плейлисте: %d",
    "🔁  Replaced %d duplicate": "🔁  Заменено дубликатов: %d",
    "🔁  Replaced %d duplicates": "🔁  Заменено дубликатов: %d",
    "⚠  %d duplicate was no longer in its playlist — left as it is":
        "⚠  Дубликатов, которых уже нет в их плейлисте: %d — оставлены как есть",
    "⚠  %d duplicates were no longer in their playlist — left as they are":
        "⚠  Дубликатов, которых уже нет в их плейлисте: %d — оставлены как есть",
    "💾  Saved → %s": "💾  Сохранено → %s",
    "💾  Saved %d competition playlist(s)":
        "💾  Сохранено плейлистов соревнований: %d",
    "📅  Planned %d competition(s) into %d deck(s)":
        "📅  Соревнований: %d, распланировано в деков: %d",
    "📂  Added %d track(s) from %d file(s)":
        "📂  Добавлено треков: %d из файлов: %d",
    "📂  Imported %d playlists into %d free slot(s)":
        "📂  Импортировано плейлистов: %d в свободных мест: %d",
    "%d extra final-round track(s) kept as backups (stacked under their dance)":
        "Дополнительных треков финала оставлено как запасные: %d (стопкой под своим танцем)",
    "%s line(s) name a file the list already had (imported again, not skipped)":
        "Строк с файлом, который уже был в списке: %s (импортированы снова, не пропущены)",
    "%s file(s) not found on disk": "Файлов не найдено на диске: %s",
    "%s track(s) with no recognizable dance (skipped)":
        "Треков без распознаваемого танца: %s (пропущены)",
    "%s track(s) left out — no round/dance column to put them in":
        "Треков пропущено: %s — нет столбца тура/танца, куда их поставить",
    "%s of %s songs": "%s из %s треков",
    "%s songs": "Треков: %s",
    "📂 Imported %s · %d round(s) · %d dance(s) (markers)":
        "📂 Импортировано %s · туров: %d · танцев: %d (маркеры)",
    "📂 Imported %s · %d round(s) · %d dance(s) (auto-detected)":
        "📂 Импортировано %s · туров: %d · танцев: %d (распознано автоматически)",
    "📂 Imported %s · %d round(s)": "📂 Импортировано %s · туров: %d",
    "⚠ %d row(s) marked red — play-length / takt issues (hover a red title for details)":
        "⚠ Строк отмечено красным: %d — проблемы с временем звучания / тактом (наведите на красный трек, чтобы увидеть подробности)",
    "🏷  %s is not on disk any more": "🏷  %s больше нет на диске",
    "🏷  Couldn't re-read %s: %s": "🏷  Не удалось заново прочитать %s: %s",
    "★  Couldn't store the rating: %s": "★  Не удалось сохранить оценку: %s",
    "🏷  Couldn't store the tags: %s": "🏷  Не удалось сохранить теги: %s",
    "🏷  Edit tags…": "🏷  Изменить теги…",
    "🏷  Edit tags of %d tracks…": "🏷  Изменить теги треков (%d)…",
    "%d tracks — a field they differ in is kept per track until you change it.":
        "Треков: %d — поле, в котором они различаются, сохраняется для каждого трека, пока вы его не измените.",
    "keep (differs per track)": "оставить (у каждого трека своё)",
    "no stars": "без звёзд",
    "Stars:": "Звёзды:",
    "Classes:": "Классы:",
    "None ticked = suits every class.":
        "Ничего не отмечено = подходит для любого класса.",
    "Instrumental (no vocals)": "Инструментал (без вокала)",
    "differs per track — typing here replaces them all":
        "у каждого трека своё — ввод здесь заменит у всех",
    "e.g. classic, vocal_f": "напр. classic, vocal_f",
    "Markers:": "Маркеры:",
    "Add this marker, or take it out again":
        "Добавить этот маркер или снова убрать его",
    "↺  Back to the file's tags": "↺  Вернуться к тегам файла",
    "Forget every change made here in the app — stars, classes,\n"
    "instrumental, markers and Custom read from the MP3 again.":
        "Забыть все изменения, сделанные здесь в приложении, — звёзды, классы,\n"
        "инструментал, маркеры и Custom снова читаются из MP3.",
    "Filled from the MP3 tag %s. What is typed here wins over it.":
        "Заполнено из тега MP3 %s. Введённое здесь имеет приоритет.",
    "Kept in the app only. Right-click a column header to fill it from an MP3 tag.":
        "Хранится только в приложении. Правый щелчок по заголовку столбца заполняет его из тега MP3.",
    "Changed in the Custom field on the first tab":
        "Меняется в поле Custom на первой вкладке",
    "Map Custom to an MP3 tag…": "Связать Custom с тегом MP3…",
    "🏷  Custom field": "🏷  Поле Custom",
    "🏷  Fill Custom from this tag": "🏷  Заполнить Custom из этого тега",
    "In none of the %d sampled MP3s": "Ни в одном из проверенных MP3 (%d)",
    "The old tag's comment is read only: a value typed in the app stays in the app.":
        "Комментарий старого тега только для чтения: значение, введённое в приложении, остаётся в приложении.",
    "In %d of %d sampled MP3s, e.g. “%s”":
        "В %d из %d проверенных MP3, напр. «%s»",
    "The Custom column shows this tag of each MP3. A value typed in the 🏷 editor wins over it, and on Save it can be written into it.":
        "Столбец Custom показывает этот тег каждого MP3. Значение, введённое в редакторе 🏷, имеет приоритет и при сохранении может быть записано в него.",
    "In the app only": "Только в приложении",
    "Frame:": "Фрейм:",
    "Description:": "Описание:",
    "e.g. ultramixer_last_played": "напр. ultramixer_last_played",
    "Custom — a free field per track, typed in the 🏷 editor.\n"
    "Right-click the header to fill it from an MP3 tag.":
        "Custom — свободное поле для каждого трека, вводится в редакторе 🏷.\n"
        "Правый щелчок по заголовку заполняет его из тега MP3.",
    "Custom goes into the tag it is mapped to.":
        "Custom записывается в тег, с которым он связан.",
    "Extended tags": "Расширенные теги",
    "Every frame of the MP3, written straight into the file on Save. The fields of the form on the first tab are changed there.":
        "Каждый фрейм MP3, при сохранении записывается прямо в файл. Поля формы на первой вкладке меняются там.",
    "Changed in the form on the first tab":
        "Меняется в форме на первой вкладке",
    "In the MP3 file": "В файле MP3",
    "In the app": "В приложении",
    "In the app's database": "В базе данных приложения",
    "Kept in the app only — the file itself is not changed.":
        "Хранится только в приложении — сам файл не меняется.",
    "Only for MP3 files on disk": "Только для файлов MP3 на диске",
    "Covers differ": "Обложки различаются",
    "Cover can't be shown": "Обложку не удаётся показать",
    "No cover": "Нет обложки",
    "< keep >": "< оставить >",
    "< blank >": "< пусто >",
    "Title:": "Название:",
    "Artist:": "Исполнитель:",
    "Year:": "Год:",
    "Track:": "Трек:",
    "Comment:": "Комментарий:",
    "Album artist:": "Исполнитель альбома:",
    "Composer:": "Композитор:",
    "Disc number:": "Номер диска:",
    "Description": "Описание",
    "Value": "Значение",
    "➕  Add field": "➕  Добавить поле",
    "Only for an MP3 file on disk": "Только для файла MP3 на диске",
    "Couldn't read the MP3 tags: %s": "Не удалось прочитать теги MP3: %s",
    "Can only be removed, not edited here":
        "Здесь можно только удалить, но не изменить",
    "🏷  %s is in the player — stop it to write its MP3 tags":
        "🏷  %s в плеере — остановите его, чтобы записать теги MP3",
    "🏷  Couldn't write the MP3 tags: %s":
        "🏷  Не удалось записать теги MP3: %s",
    "🏷  Tags":
        "🏷  Теги",
    "🏷  Tags of %d tracks":
        "🏷  Теги треков (%d)",
    "Also write these into the MP3 file":
        "Записать также в файл MP3",
    "Stars go into the Windows rating; classes, instrumental and markers into the comment, where other programs see them too. Unticked, they stay in the app only.":
        "Звёзды идут в оценку Windows; классы, инструментал и маркеры — в комментарий, где их видят и другие программы. Без галочки они остаются только в приложении.",
    "stars": "звёзды",
    "custom": "Custom",
    "Custom text": "Свой текст",
    "Comment": "Комментарий",
    "Plays": "Сыграно",
    "Reset the play counters": "Сбросить счётчики воспроизведений",
    "How often the title has played in the last 24 hours, in any list\n"
    "Right-click the header to reset the counters":
        "Сколько раз трек звучал за последние 24 часа, из любого списка\n"
        "Щелчок правой кнопкой по заголовку сбрасывает счётчики",
    "Custom link": "Своя ссылка",
    "Rating": "Оценка",
    "Picture": "Изображение",
    "Private data": "Личные данные",
    "Embedded object": "Встроенный объект",
    "CD identifier": "Идентификатор CD",
    "Unique file id": "Уникальный id файла",
    "Lyrics": "Текст песни",
    "Play count": "Счётчик воспроизведений",
    "Volume adjustment": "Регулировка громкости",
    "Grouping": "Группировка",
    "Subtitle": "Подзаголовок",
    "Album artist": "Исполнитель альбома",
    "Conductor": "Дирижёр",
    "Remixed by": "Ремикс",
    "Key": "Тональность",
    "Composer": "Композитор",
    "Lyricist": "Автор текста",
    "Track number": "Номер трека",
    "Disc number": "Номер диска",
    "Year": "Год",
    "Recording date": "Дата записи",
    "Publisher": "Издатель",
    "Language": "Язык",
    "Length (ms)": "Длина (мс)",
    "Encoded by": "Кодировщик",
    "Encoder settings": "Настройки кодировщика",
    "Media type": "Тип носителя",
    "Grouping (iTunes)": "Группировка (iTunes)",
    "Comment of the old tag": "Комментарий старого тега",
    "🏷  %s: tags unchanged": "🏷  %s: теги не изменены",
    "⚠  Track no longer in any open deck":
        "⚠  Трека больше нет ни в одном открытом деке",
    "🗑  Removed “%s” from 1 slot — Ctrl+Z undoes":
        "🗑  «%s» убран из 1 места — Ctrl+Z отменяет",
    "🗑  Removed “%s” from %d slots — Ctrl+Z undoes":
        "🗑  «%s» убран из мест: %d — Ctrl+Z отменяет",
    "↺  Replaced “%s” with “%s” in 1 slot — Ctrl+Z undoes":
        "↺  «%s» заменён на «%s» в 1 месте — Ctrl+Z отменяет",
    "↺  Replaced “%s” with “%s” in %d slots — Ctrl+Z undoes":
        "↺  «%s» заменён на «%s» в местах: %d — Ctrl+Z отменяет",
    "🧭  Fixed %d track path": "🧭  Исправлено путей треков: %d",
    "🧭  Fixed %d track paths": "🧭  Исправлено путей треков: %d",
    "🧭  Moved %d track onto the Reference path":
        "🧭  Перенесено треков на опорный путь: %d",
    "🧭  Moved %d tracks onto the Reference path":
        "🧭  Перенесено треков на опорный путь: %d",
    "No tracks in the visible playlists or the wishlists.":
        "В видимых плейлистах и списках пожеланий нет треков.",
    "Checked %d tracks — %d already valid.":
        "Проверено треков: %d — уже в порядке: %d.",
    "🧭  Relocated %d broken reference to their real files (Ctrl+Z undoes).":
        "🧭  Битых ссылок перенаправлено на реальные файлы: %d (Ctrl+Z отменяет).",
    "🧭  Relocated %d broken references to their real files (Ctrl+Z undoes).":
        "🧭  Битых ссылок перенаправлено на реальные файлы: %d (Ctrl+Z отменяет).",
    "⚠  %d still unresolved — no matching file in the library:":
        "⚠  Всё ещё не найдено: %d — в библиотеке нет подходящего файла:",
    "⚠  %d valid track is not on the Reference path %s":
        "⚠  Рабочих треков: %d — не на опорном пути %s",
    "⚠  %d valid tracks are not on the Reference path %s":
        "⚠  Рабочих треков: %d — не на опорном пути %s",
    "↪ %d has a copy there — 🧭 Fix swaps them in the playlists.":
        "↪ С копией там: %d — 🧭 Исправить заменит их в плейлистах.",
    "↪ %d have a copy there — 🧭 Fix swaps them in the playlists.":
        "↪ С копией там: %d — 🧭 Исправить заменит их в плейлистах.",
    "⚠ %d has no copy there:":
        "⚠ Без копии там (%d):",
    "⚠ %d have no copy there:":
        "⚠ Без копии там (%d):",
    "✅  All track paths are valid.":
        "✅  Все пути треков в порядке.",
    "🎛  Re-pointed %d cartwall pad at its real sample.":
        "🎛  Пэдов Cartwall перенаправлено на реальные сэмплы: %d.",
    "🎛  Re-pointed %d cartwall pads at their real samples.":
        "🎛  Пэдов Cartwall перенаправлено на реальные сэмплы: %d.",
    "🧭  Fixed 1 path in 1 file": "🧭  Исправлен 1 путь в 1 файле",
    "🧭  Fixed %d paths in 1 file": "🧭  Исправлено путей в 1 файле: %d",
    "🧭  Fixed %d paths in %d files": "🧭  Исправлено путей: %d, в файлах: %d",
    "🧹  Removed %d track(s) already in a playlist":
        "🧹  Убрано треков, уже стоящих в плейлисте: %d",
    "↺  No other %s near the end of the list":
        "↺  Другого %s у конца списка нет",
    "🔍  No title matching “%s”": "🔍  Нет трека, подходящего к «%s»",
    "🔁  Marked %d track for replace": "🔁  Отмечено для замены: %d",
    "🔁  Marked %d tracks for replace": "🔁  Отмечено для замены: %d",
    "🔁  Unmarked %d track": "🔁  Снята отметка с треков: %d",
    "🔁  Unmarked %d tracks": "🔁  Снята отметка с треков: %d",
    "📌  Pin — keep this title when the round is re-rolled":
        "📌  Закрепить — оставить этот трек при новой жеребьёвке тура",
    "📌  Unpin": "📌  Открепить",
    "📌  Pinned — unpin the title to re-roll it":
        "📌  Закреплён — открепите трек, чтобы разыграть его заново",
    "📌  Pinned %d title — the round's ↻ keeps it":
        "📌  Закреплено треков: %d — ↻ тура их сохранит",
    "📌  Pinned %d titles — the round's ↻ keeps them":
        "📌  Закреплено треков: %d — ↻ тура их сохранит",
    "📌  Unpinned %d title": "📌  Откреплено треков: %d",
    "📌  Unpinned %d titles": "📌  Откреплено треков: %d",
    "🚦  Check ▾": "🚦  Проверка ▾",
    "🚦 Ready? — the pre-flight before the event, one traffic light per\n"
    "check: missing files, loudness, silence probe, Paso Doble highlights,\n"
    "duplicates and the music check, each with its fix.\n"
    "The menu also opens 🔁 Check duplicates, 🎵 Check music and\n"
    "🧭 Fix paths on their own.":
        "🚦 Готово? — проверка перед мероприятием, по светофору на каждую\n"
        "проверку: недостающие файлы, громкость, проверка тишины, кульминации\n"
        "пасодобля, дубликаты и проверка музыки, каждая со своим исправлением.\n"
        "Меню также открывает по отдельности 🔁 Проверить дубликаты, 🎵 Проверить музыку и\n"
        "🧭 Исправить пути.",
    "🚦  Ready?": "🚦  Готово?",
    "Pre-flight before the event, one traffic light per check — over every\n"
    "deck that holds titles and the Practice list, each with its fix.\n"
    "A heading in the report opens its full tool.":
        "Проверка перед мероприятием, по светофору на каждую проверку — по каждому\n"
        "деку с треками и списку практики, каждая со своим исправлением.\n"
        "Заголовок в отчёте открывает полный инструмент.",
    "No tempo, length or round-structure problem in the decks.":
        "В деках нет проблем с темпом, длительностью или структурой туров.",
    "%d titles with a tempo or length problem: %s":
        "Треков с проблемой темпа или длительности: %d — %s",
    "%d playlists with uneven rounds or heats: %s":
        "Плейлистов с неравными турами или заходами: %d — %s",
    "🎵  Show the report…": "🎵  Показать отчёт…",
    "Click the heading to open the full tool.":
        "Щёлкните по заголовку, чтобы открыть полный инструмент.",
    "🚦  Ready for the event?": "🚦  Готовы к мероприятию?",
    "🟢  Ready — every check is green.": "🟢  Готово — все проверки зелёные.",
    "🟡  Playable, with loose ends.": "🟡  Можно играть, но есть хвосты.",
    "🔴  Not ready — some titles will not play.":
        "🔴  Не готово — некоторые треки не заиграют.",
    "🧭  Fix paths…": "🧭  Исправить пути…",
    "📊  Measure loudness…": "📊  Измерить громкость…",
    "🐂  Find highlights…": "🐂  Найти кульминации…",
    "🔁  Resolve duplicates…": "🔁  Разобрать дубликаты…",
    "📁  Music files": "📁  Музыкальные файлы",
    "Every title is where the list says.":
        "Каждый трек лежит там, где указано в списке.",
    "%d titles are not on the Reference path.": "Треков не на опорном пути: %d.",
    "%d have a copy there — 🧭 Fix paths swaps them in.":
        "С копией там: %d — 🧭 Исправить пути подставит их.",
    "%d have no copy there: %s": "Без копии там: %d — %s",
    "Drive %s is not connected — %d titles live there.":
        "Диск %s не подключён — на нём треков: %d.",
    "%d titles not found: %s": "Не найдено треков: %d: %s",
    "🎶  Playlists": "🎶  Плейлисты",
    "Nothing to play yet — load or build a playlist first.":
        "Играть пока нечего — сначала загрузите или создайте плейлист.",
    "📊  Loudness": "📊  Громкость",
    "Every title is measured — 🔊 Equalize volume can stay on.":
        "Все треки измерены — 🔊 Выравнивание громкости может оставаться включённым.",
    "%d of %d titles have no loudness measurement — 🔊 Equalize volume stays off.":
        "Без измерения громкости: %d из %d треков — 🔊 Выравнивание громкости остаётся выключенным.",
    "🔇  Silence probe": "🔇  Проверка тишины",
    "Every title is probed — playback skips its silent edges.":
        "Все треки проверены — воспроизведение пропускает тихие края.",
    "%d of %d titles are not probed — each is decoded when it starts.":
        "Не проверено: %d из %d треков — каждый декодируется при запуске.",
    "🐂  Paso Doble highlights": "🐂  Кульминации пасодобля",
    "Every Paso Doble knows its highlights.":
        "Каждый пасодобль знает свои кульминации.",
    "No Paso Doble in tonight's lists.":
        "В сегодняшних списках нет пасодобля.",
    "%d of %d Paso Dobles have no highlights — 🐂 cannot stop at one.":
        "Без кульминаций: %d из %d пасодоблей — 🐂 не может остановиться ни на одной.",
    "🔁  Duplicates": "🔁  Дубликаты",
    "%d duplicates across the decks and the Practice list.":
        "Дубликатов в деках и списке практики: %d.",
    "No title is planned twice.": "Ни один трек не запланирован дважды.",
    "🧹  Removed %d duplicate title": "🧹  Убрано дубликатов: %d",
    "🧹  Removed %d duplicate titles": "🧹  Убрано дубликатов: %d",
    "⭐  Moved %d track(s) to the wishlist":
        "⭐  Перенесено в список пожеланий: %d",
    "⭐  Added %d track(s) to the wishlist":
        "⭐  Добавлено в список пожеланий: %d",
    "  ·  ⚠ %d already in a playlist (duplicate)":
        "  ·  ⚠ уже в плейлисте (дубль): %d",
    "➕  Added %d track(s)": "➕  Добавлено треков: %d",
    "➕  Added %d track(s) — rounds re-cut":
        "➕  Добавлено треков: %d — туры перераспределены",
    "🎯  Placed %d track(s)": "🎯  Размещено треков: %d",
    "  (%d skipped — no free slot)":
        "  (пропущено: %d — нет свободного места)",
    "… plus %d more": "… и ещё %d",
    "🔁  Replaced “%s” with “%s”": "🔁  «%s» заменён на «%s»",
    "⚠  “%s” is already in this playlist — not replaced":
        "⚠  «%s» уже есть в этом плейлисте — не заменён",
    "🔁  Replaced %d track(s)": "🔁  Заменено треков: %d",
    "🔁  Replaced %d, ➕ added %d track(s)":
        "🔁  Заменено: %d, ➕ добавлено треков: %d",
    "  (%s — skipped)": "  (%s — пропущено)",
    "%d already planned": "уже запланировано: %d",
    "%d with no dance": "без танца: %d",
    "⚠  Couldn't tell what dance “%s” is — nothing added":
        "⚠  Не удалось определить танец «%s» — ничего не добавлено",
    "⚠  “%s” is already in this playlist — nothing added":
        "⚠  «%s» уже есть в этом плейлисте — ничего не добавлено",
    "Nothing added — %s": "Ничего не добавлено — %s",
    "TSO tempo equalize → on": "Выравнивание темпа TSO → вкл.",
    "TSO tempo equalize → off": "Выравнивание темпа TSO → выкл.",
    "🎉  Party set — %s": "🎉  Набор для вечеринки — %s",
    "🏆  Tournament set — %s": "🏆  Турнирный набор — %s",
    "🎚  Own settings — %s": "🎚  Свои настройки — %s",
    "🎉  Party set applied": "🎉  Набор для вечеринки применён",
    "🏆  Tournament set applied": "🏆  Турнирный набор применён",
    "nothing to change": "менять нечего",
    ", running at %s": ", часы показывают %s",
    "🕒  Timetable saved — %d entries": "🕒  Расписание сохранено — записей: %d",
    ", fading every %ss": ", переход каждые %s с",
    "play length → %s": "время звучания → %s",
    "fade-out → %s s": "затухание → %s с",
    "auto-advance → on": "автопереход → вкл.",
    "auto-advance → off": "автопереход → выкл.",
    "pause between songs → on": "пауза между треками → вкл.",
    "pause between songs → off (no break music)":
        "пауза между треками → выкл. (без музыки в паузе)",
    "equalize volume → on": "выравнивание громкости → вкл.",
    "equalize volume → off": "выравнивание громкости → выкл.",
    "announce next dance → on": "объявлять следующий танец → вкл.",
    "announce next dance → off": "объявлять следующий танец → выкл.",
    "double-click → starts the title": "двойной щелчок → запускает трек",
    "double-click → cues it": "двойной щелчок → только подготавливает его",
    "🐂 Paso Doble highlight stop → on":
        "🐂 Пасодобль: остановка на кульминации → вкл.",
    "🐂 Paso Doble highlight stop → off":
        "🐂 Пасодобль: остановка на кульминации → выкл.",
    "🐂 Paso Doble start after → %s s":
        "🐂 Пасодобль: старт через → %s с",
    "🐂 Paso Doble stop after highlight → %d":
        "🐂 Пасодобль стоп после кульминации → %d",
    "📌 Session saved — decks, wishlists, 🎛 cartwall and layout.":
        "📌 Сессия сохранена — деки, списки пожеланий, 🎛 Cartwall и раскладка.",
    "Error generating playlist: %s": "Ошибка при создании плейлиста: %s",
    "  (iteration %d)": "  (итерация %d)",
    " — from %s": " — из %s",
    "Generated %d songs — %s, %s, %s": "Создано треков: %d — %s, %s, %s",
    "Skipped competition(s):": "Пропущенные турниры:",
    "📅 Day plan: %d generated, %d skipped":
        "📅 План дня: создано %d, пропущено %d",
    "📅 Day plan: %d competition(s) generated":
        "📅 План дня: создано турниров: %d",
    "Seeding '%s' from past playlists…":
        "Заполнение «%s» из прежних плейлистов…",
    "Error reading past playlists: %s": "Ошибка чтения прежних плейлистов: %s",
    "Generated %d songs — %s": "Создано треков: %d — %s",
    "Timbre similarity on for ↺ regenerations":
        "Сходство тембра включено для повторной жеребьёвки ↺",
    "Timbre similarity off for ↺ regenerations":
        "Сходство тембра выключено для повторной жеребьёвки ↺",
    "Building '%s' playlist…": "Создание плейлиста «%s»…",
    "No tracks matched theme '%s'.": "Нет треков для темы «%s».",
    "Decade themes require year tags in your MP3s; you can also map\n"
    "songs to themes in themes.json (track_themes).":
        "Темам по десятилетиям нужны теги года в ваших MP3; треки также можно\n"
        "привязать к темам в themes.json (track_themes).",
    "No tracks matched '%s'.": "Нет треков, подходящих к «%s».",
    "Theme '%s' — %d tracks": "Тема «%s» — треков: %d",
    "🤸 Building %s…": "🤸 Создание %s…",
    "Building %s…": "Создание %s…",
    "%s — %d tracks": "%s — треков: %d",
    "🔀 %s shuffled — %d tracks": "🔀 %s перемешан — треков: %d",
    "🤸 Practice: nothing loadable from %s":
        "🤸 Практика: в %s нечего загрузить",
    "🎧 Nothing loadable from %s": "🎧 В %s нечего загрузить",
    "🤖 %d/%d slots filled by %s": "🤖 %d/%d мест заполнено: %s",
    "🤖 %d tracks by %s": "🤖 Треков: %d, источник: %s",
    "%s not installed": "%s не установлен",
    "Build %s index": "Построить индекс %s",
    "Build the %s index over %s tracks from %s?":
        "Построить индекс %s по %s трекам из %s?",
    "Analyses the melody/harmony of each track once (slow the first time, then cached).":
        "Один раз анализирует мелодию/гармонию каждого трека (в первый раз медленно, затем из кэша).",
    "Loads a neural model and embeds each track once (slow the first time, then cached).":
        "Загружает нейросетевую модель и один раз обрабатывает каждый трек (в первый раз медленно, затем из кэша).",
    "Reuses anything already computed.":
        "Всё уже вычисленное используется повторно.",
    "Building %s index…": "Построение индекса %s…",
    "%s indexing failed": "Индексация %s не удалась",
    "All %d file(s) failed to embed.\n"
    "\n"
    "First error:\n"
    "%s\n"
    "\n"
    "See the console log for the full traceback.":
        "Не удалось обработать ни один файл (%d).\n"
        "\n"
        "Первая ошибка:\n"
        "%s\n"
        "\n"
        "Полную трассировку показывает журнал консоли.",
    "unknown": "неизвестно",
    "%s indexing failed.": "Индексация %s не удалась.",
    "%s index built — %d embedded, %d failed.":
        "Индекс %s построен — обработано %d, ошибок %d.",
    "%s index built — %d embedded.": "Индекс %s построен — обработано %d.",
    "%s index ready": "Индекс %s готов",
    "Embedded %d track(s) (%d failed — see log).":
        "Обработано треков: %d (ошибок: %d — см. журнал).",
    "Embedded %d track(s).": "Обработано треков: %d.",
    "The %s method is now ready in the Similar-Tracks window.":
        "Метод %s теперь доступен в окне «Похожие треки».",
    "%s indexing cancelled — %d embedded so far (cached).":
        "Индексация %s прервана — пока обработано %d (сохранено).",
    "Library error: %s": "Ошибка библиотеки: %s",
    "Analyzing %s …": "Анализ %s …",
    "Only %s of %s tracks are analyzed so far (analysis is still running). Let analysis finish and try again.":
        "Пока проанализировано только %s из %s треков (анализ ещё идёт). Дождитесь окончания анализа и попробуйте снова.",
    "Only %s of %s tracks are analyzed so far. Let analysis finish and try again.":
        "Пока проанализировано только %s из %s треков. Дождитесь окончания анализа и попробуйте снова.",
    "Global search is on but the repository isn't analyzed yet — open ⚙ Settings → “Build / refresh global audio index”.":
        "Глобальный поиск включён, но репозиторий ещё не проанализирован — откройте ⚙ Настройки → «Построить / обновить глобальный аудиоиндекс».",
    "No tracks are analyzed yet — run 'Analyze Audio' first.":
        "Ни один трек ещё не проанализирован — сначала запустите «Анализ аудио».",
    "All tracks are analyzed — this file just has no close match.":
        "Все треки проанализированы — у этого файла просто нет близкого совпадения.",
    "No similar tracks found in %s.": "Похожих треков в %s не найдено.",
    "Found %d similar to %s (%s)": "Найдено: %d похожих на %s (%s)",
    "Global library ready from cache — %s files.":
        "Глобальная библиотека загружена из кэша — файлов: %s.",
    "Global index: %s files, %s analyzed.":
        "Глобальный индекс: файлов %s, проанализировано %s.",
    "Scanning repository… %s/%s  (%s left)":
        "Сканирование репозитория… %s/%s  (осталось %s)",
    "Remove cached data of deleted music files and compact %s (%s MB)?":
        "Удалить сохранённые данные удалённых музыкальных файлов и сжать %s (%s МБ)?",
    "Feature vectors, embeddings and loudness of files that no longer exist on disk are removed for good (they would simply be re-analyzed if the files ever come back). Compacting can take a few minutes.":
        "Векторы признаков, эмбеддинги и громкость файлов, которых больше нет на диске, удаляются навсегда (если файлы вернутся, они просто будут проанализированы заново). Сжатие может занять несколько минут.",
    "deleted tracks": "удалённые треки",
    "tag records": "записи тегов",
    "feature vectors": "векторы признаков",
    "AI embeddings": "ИИ-эмбеддинги",
    "loudness values": "значения громкости",
    "silence maps": "карты тишины",
    "vocal shares": "доли вокала",
    "noise floors": "уровни шума",
    "playlist index entries": "записи индекса плейлистов",
    "stale index markers": "устаревшие метки индекса",
    "🧹 Database compacted: %s MB → %s MB (%s MB freed).":
        "🧹 База данных сжата: %s МБ → %s МБ (освобождено %s МБ).",
    "Removed rows: %s.": "Удалено строк: %s.",
    "none — everything is still in use": "нет — всё ещё используется",
    "Cleanup did not run:": "Очистка не выполнена:",
    "🗑  Reset database…":
        "🗑  Сбросить базу данных…",
    "Empty chosen parts of the database: the tags read from the files,\nthe audio analysis, your own data. A dialog asks which; your own\ndata is backed up first, and the app restarts afterwards.":
        "Очистить выбранные части базы данных: теги, прочитанные из файлов,\nаудиоанализ, ваши собственные данные. Диалог спросит, какие; ваши\nданные сначала сохраняются, затем приложение перезапускается.",
    "🗑  Reset database":
        "🗑  Сбросить базу данных",
    "🗑 Reset database":
        "🗑 Сбросить базу данных",
    "🏷  Tags read from the music files":
        "🏷  Теги, прочитанные из музыкальных файлов",
    "🎚  Audio analysis":
        "🎚  Аудиоанализ",
    "✋  My own data":
        "✋  Мои собственные данные",
    "Dance, BPM, class and title of every file, the file list and the learned playlist index. The next library scan reads them again (minutes).":
        "Танец, BPM, класс и название каждого файла, список файлов и изученный индекс плейлистов. Следующее сканирование библиотеки прочитает их заново (минуты).",
    "Features, AI embeddings, loudness, silences, waveforms, vocal shares and detected PD highlights. ⚗ Analysis builds them again (hours).":
        "Признаки, ИИ-эмбеддинги, громкость, паузы, волновые формы, доли вокала и найденные PD-хайлайты. ⚗ Анализ построит их заново (часы).",
    "Your tag edits, hand-set PD marks and the 📜 play log. Nothing rebuilds them; only ♻ Restore user data backup brings them back.":
        "Ваши правки тегов, вручную поставленные метки PD и 📜 журнал воспроизведения. Ничто их не восстановит; только ♻ Восстановление резервной копии своих данных вернёт их.",
    "Empty the chosen parts of the database. Your own data is backed up first either way, and the app restarts afterwards.":
        "Очистить выбранные части базы данных. Ваши собственные данные в любом случае сначала сохраняются, а затем приложение перезапускается.",
    "Reset and restart":
        "Сбросить и перезапустить",
    "Resetting database…":
        "Сброс базы данных…",
    "The app still shows the old data until it restarts. Restart now?":
        "Приложение показывает старые данные до перезапуска. Перезапустить сейчас?",
    "Reset did not run:":
        "Сброс не выполнен:",
    "<b>Excluded folders</b> — titles in these folders and below stay out of the library, one folder per line:":
        "<b>Исключённые папки</b> — треки в этих папках и ниже не попадают в библиотеку, по одной папке на строку:",
    "Left out of ⭐ Favorites and 🌐 Whole library alike: not shown, not\nsearched, never suggested. Nothing on disk changes, and the tags\nread so far stay cached, so a folder taken off the list is back\nafter a restart.":
        "Исключены и из ⭐ Избранного, и из 🌐 Всей библиотеки: не показываются,\nне ищутся, не предлагаются. На диске ничего не меняется, прочитанные\nтеги остаются в кэше, так что папка, убранная из списка, вернётся\nпосле перезапуска.",
    "Hide a folder from the library":
        "Скрыть папку из библиотеки",
    "🙈 Excluded folders":
        "🙈 Исключённые папки",
    "The library is loaded when the app starts, so the excluded folders change with the next start.\n\nRestart now?":
        "Библиотека загружается при запуске приложения, поэтому исключённые папки изменятся при следующем запуске.\n\nПерезапустить сейчас?",
    "📤  Export manual PD marks…": "📤  Экспорт ручных меток PD…",
    "📥  Import manual PD marks…": "📥  Импорт ручных меток PD…",
    "Export manual PD marks": "Экспорт ручных меток PD",
    "Import manual PD marks": "Импорт ручных меток PD",
    "Save the Paso Doble highlights you set by hand (🎯) to a file,\n"
    "to take them to another PC. Detected highlights are not included —\n"
    "🐂 finds those again by itself.":
        "Сохранить в файл кульминации пасодобля, поставленные вручную (🎯),\n"
        "чтобы перенести их на другой ПК. Найденные автоматически не входят —\n"
        "🐂 найдёт их снова сам.",
    "Load hand-set Paso Doble highlights exported on another PC.\n"
    "They are matched by the music itself, not by the file path, and\n"
    "replace what this PC has for those tracks.":
        "Загрузить вручную поставленные кульминации пасодобля, экспортированные на другом ПК.\n"
        "Они сопоставляются по самой музыке, а не по пути к файлу, и\n"
        "заменяют то, что есть на этом ПК для этих треков.",
    "No Paso Doble highlight has been set by hand yet.":
        "Ни одна кульминация пасодобля ещё не поставлена вручную.",
    "Could not write the file:": "Не удалось записать файл:",
    "📤 %d hand-set Paso Doble highlight(s) saved to:\n"
    "%s":
        "📤 Сохранено вручную поставленных кульминаций пасодобля: %d, в:\n"
        "%s",
    "This is no manual-PD-marks file:": "Это не файл ручных меток PD:",
    "📥 %d hand-set Paso Doble highlight(s) imported — %d of them belong to a track this PC already knows.\n"
    "\n"
    "The others are kept and apply as soon as that music turns up here.":
        "📥 Импортировано вручную поставленных кульминаций пасодобля: %d — из них %d относятся к трекам, которые этот ПК уже знает.\n"
        "\n"
        "Остальные сохраняются и применятся, как только эта музыка появится здесь.",
    "<b>Backup folder</b> — where the daily backup of your own data goes (e.g. a Dropbox folder). Empty: next to the database.":
        "<b>Папка резервных копий</b> — куда идёт ежедневная резервная копия своих данных (напр. папка Dropbox). Пусто: рядом с базой данных.",
    "♻  Restore user data backup…":
        "♻  Восстановить резервную копию своих данных…",
    "Restore user data backup": "Восстановить резервную копию своих данных",
    "Merge a daily backup of your tag edits, hand-set Paso Doble\n"
    "highlights and play log back in. The app keeps one per day for the last 7 days.\n"
    "Everything else in the database is left as it is.":
        "Вернуть ежедневную резервную копию ваших правок тегов, вручную поставленных\n"
        "кульминаций пасодобля и журнала воспроизведения. Приложение хранит по одной копии в день за последние 7 дней.\n"
        "Всё остальное в базе данных остаётся как есть.",
    "This is no user data backup:": "Это не резервная копия своих данных:",
    "♻ %d tag edit(s) and %d hand-set Paso Doble highlight(s) restored, %d played title(s) added to the play log.\n"
    "\n"
    "They take effect after a restart of the app.":
        "♻ Восстановлено правок тегов: %d, вручную поставленных кульминаций пасодобля: %d; добавлено в журнал сыгранных треков: %d.\n"
        "\n"
        "Они вступят в силу после перезапуска приложения.",
    "Date": "Дата",
    "List": "Список",
    "Duration": "Длительность",
    "📜 Played titles": "📜 Сыгранные треки",
    "📜  Played titles…": "📜  Сыгранные треки…",
    "📝  Export log…":
        "📝  Экспорт журнала…",
    "Export log — pick a folder":
        "Экспорт журнала — выберите папку",
    "Export log":
        "Экспорт журнала",
    "The log could not be exported:\n%s":
        "Не удалось экспортировать журнал:\n%s",
    "There is no log to export yet.":
        "Журнала для экспорта пока нет.",
    "Log exported to:\n%s":
        "Журнал экспортирован в:\n%s",
    "Nothing has been played yet. A title is logged in playing mode\n"
    "once it has run for 10 seconds, the moment its row greys out.":
        "Ещё ничего не сыграно. Трек записывается в режиме воспроизведения,\n"
        "когда проиграет 10 секунд, — в тот момент, когда его строка становится серой.",
    "💾  Save as CSV…": "💾  Сохранить как CSV…",
    "Save this evening as a table for Excel: date, start, artist, title,\n"
    "composer, dance, list and how long each title ran — e.g. for a GEMA report.":
        "Сохраняет этот вечер таблицей для Excel: дата, начало, исполнитель, название,\n"
        "композитор, танец, список и сколько звучал каждый трек — напр. для отчёта в авторское общество.",
    "🗑  Delete evening": "🗑  Удалить вечер",
    "Delete evening": "Удалить вечер",
    "%d title(s)": "Треков: %d",
    "Save played titles": "Сохранить сыгранные треки",
    "CSV files (*.csv);;All files (*)": "Файлы CSV (*.csv);;Все файлы (*)",
    "Delete the evening of %s with its %d title(s) from the play log?\n"
    "\n"
    "Its daily backups still hold it for 7 days.":
        "Удалить из журнала вечер %s (треков: %d)?\n"
        "\n"
        "Ежедневные резервные копии хранят его ещё 7 дней.",
    "Playlist popularity re-learned from %s playlists.":
        "Популярность заново изучена по плейлистам: %s.",
    "📜 %s playlists analyzed (M3U files + tournament folders) — popularity and co-occurrence are up to date, so a just-exported tournament counts now.\n"
    "\n"
    "Rows already in the grid keep their old Pop value until regenerated.":
        "📜 Проанализировано плейлистов: %s (файлы M3U + папки турниров) — популярность и совместная встречаемость актуальны, так что только что экспортированный турнир уже учитывается.\n"
        "\n"
        "Строки, уже стоящие в сетке, сохраняют старое значение Pop, пока их не разыграют заново.",
    "Re-learn failed:": "Не удалось заново изучить:",
    "  … and %d more": "  … и ещё %d",
    "⚠ %d title(s) are not on the Reference path\n"
    "%s\n"
    "and were saved with their own path:":
        "⚠ Треков не на опорном пути: %d\n"
        "%s\n"
        "они сохранены со своим путём:",
    "💾 Saved %d playlist → %s": "💾 Сохранено плейлистов: %d → %s",
    "💾 Saved %d playlists → %s": "💾 Сохранено плейлистов: %d → %s",
    "Saved %d playlist(s) to:\n"
    "%s":
        "Сохранено плейлистов: %d, в:\n"
        "%s",
    "Saved %d wishlist(s) to:\n"
    "%s":
        "Сохранено списков пожеланий: %d, в:\n"
        "%s",
    "Skipped (empty): %s": "Пропущены (пустые): %s",
    "Errors:": "Ошибки:",
    "“%s” already exists in the target folder.\n"
    "Replace it, or keep both?":
        "«%s» уже есть в целевой папке.\n"
        "Заменить или оставить оба?",
    "“%s” already exists in the target folder and holds more than a USB export, "
    "so it cannot be replaced.\nKeep both?":
        "«%s» уже есть в целевой папке и содержит не только USB-экспорт, "
        "поэтому её нельзя заменить.\nОставить оба?",
    "Could not remove “%s”:\n%s\n\nIt may be partly deleted; nothing was exported.":
        "Не удалось удалить «%s»:\n%s\n\n"
        "Папка, возможно, удалена частично; ничего не экспортировано.",
    "Could not create “%s”:\n%s":
        "Не удалось создать «%s»:\n%s",
    "🧳 Bundle: %d playlist folder(s), %d track(s), %s MB → %s":
        "🧳 Пакет: папок плейлистов %d, треков %d, %s МБ → %s",
    "Bundle written to:\n"
    "%s":
        "Пакет записан в:\n"
        "%s",
    "%d playlist folder(s) · %d track(s) · %s MB — each folder holds the tracks numbered in play order plus the playlist's M3U, so it plays even without the M3U.":
        "Папок плейлистов: %d · треков: %d · %s МБ — в каждой папке треки пронумерованы в порядке воспроизведения, плюс M3U плейлиста, так что она играет и без M3U.",
    "⚠ %d track(s) were missing on disk and kept their original absolute path.":
        "⚠ Треков нет на диске, их исходный абсолютный путь сохранён: %d.",
    "💾 Saved %d competition playlist → %s":
        "💾 Сохранено турнирных плейлистов: %d → %s",
    "💾 Saved %d competition playlists → %s":
        "💾 Сохранено турнирных плейлистов: %d → %s",
    "Saved %d competition playlist(s) to:\n"
    "%s":
        "Сохранено турнирных плейлистов: %d, в:\n"
        "%s",
    "Nothing to save.": "Нечего сохранять.",
    "Saved → %s": "Сохранено → %s",
    "Saved %d competition playlist(s) → %s":
        "Сохранено турнирных плейлистов: %d → %s",
    "Close the tournament-day view? This clears %d day playlist.":
        "Закрыть вид турнирного дня? Будут очищены плейлисты дня: %d.",
    "Close the tournament-day view? This clears %d day playlists.":
        "Закрыть вид турнирного дня? Будут очищены плейлисты дня: %d.",
    "Clear the %d day playlist?": "Очистить плейлисты дня (%d)?",
    "Clear all %d day playlists?": "Очистить все плейлисты дня (%d)?",
    "Clear the %d playlist on “%s”?": "Очистить плейлисты (%d) на «%s»?",
    "Clear all %d playlists on “%s”?": "Очистить все плейлисты (%d) на «%s»?",
    "🧹 %s playlists cleared.": "🧹 Плейлисты на %s очищены.",
    " — %d track(s) of no known dance left out":
        " — пропущено треков без известного танца: %d",
    "🔒 Static mode — a drop now replaces a single slot":
        "🔒 Статический режим — отпускание теперь заменяет одно место",
    "🔓 Dynamic mode — drag songs from the wishlist or another deck to build rounds & heats":
        "🔓 Динамический режим — перетаскивайте треки из списка пожеланий или другого дека, чтобы собрать туры и заходы",
    "✋ Free order — every row can be dragged anywhere, and a dropped song lands where you drop it":
        "✋ Свободный порядок — любую строку можно перетащить куда угодно, и отпущенный трек встаёт ровно туда",
    "%d of these %d tracks say nothing about which dance they are. A grid has no column to put them in, so building one leaves them out of the deck.\n"
    "\n"
    "Build the grid without them?":
        "Треков без указания танца: %d из %d. В сетке нет для них столбца, поэтому при построении они выпадут из дека.\n"
        "\n"
        "Построить сетку без них?",
    "🤸 %s panel shown — drop an .m3u here or build one with 🤸 %s.":
        "🤸 Панель %s показана — перетащите сюда .m3u или создайте её через 🤸 %s.",
    "🤸 %s panel hidden": "🤸 Панель %s скрыта",
    "📚 Library filtered: %s": "📚 Библиотека отфильтрована: %s",
    "all dances": "все танцы",
    " · class %s": " · класс %s",
    " · never played": " · ни разу не играл",
    "<b>%d</b> of %d checked tracks have at least one issue.":
        "У <b>%d</b> из %d проверенных треков есть хотя бы одна проблема.",
    "Plus <b>%d</b> 🧩 round-structure issue — see the yellow box below.":
        "Плюс 🧩 проблем в структуре туров: <b>%d</b> — см. жёлтый блок ниже.",
    "Plus <b>%d</b> 🧩 round-structure issues — see the yellow box below.":
        "Плюс 🧩 проблем в структуре туров: <b>%d</b> — см. жёлтый блок ниже.",
    "%d tracks skipped — no label/dance/length or not audio-analyzed.":
        "Пропущено треков: %d — нет метки/танца/длины или нет аудиоанализа.",
    "⚡ tempo label vs measured off > %.0f%% (×2, ×3, ×1.5 … slips excused) · 🐢/🐇 takt outside the official TSO range · ⏱ real play ≤ %s":
        "⚡ метка темпа расходится с измерением > %.0f%% (×2, ×3, ×1,5 … допускаются) · 🐢/🐇 такт вне официального диапазона TSO · ⏱ реальное время звучания ≤ %s",
    "⏳ longer than %s": "⏳ длиннее %s",
    "🔇 noise floor above %.0f dB": "🔇 уровень шума выше %.0f дБ",
    "Thresholds: ⚙ Settings → 🎵 Checks.": "Пороги: ⚙ Настройки → 🎵 Проверки.",
    "⏳  Also flag long tracks (> %s) — only relevant when building a Practice playlist":
        "⏳  Отмечать и длинные треки (> %s) — важно только при создании плейлиста практики",
    "🔇  Also flag hissy tracks (never quieter than %.0f dB) — measures each track once with ffmpeg, so the first run takes a moment":
        "🔇  Отмечать и шумные треки (никогда не тише %.0f дБ) — каждый трек один раз измеряется через ffmpeg, поэтому первый прогон занимает время",
    "🧩 <b>Round structure</b> — click a spot to jump to it":
        "🧩 <b>Структура туров</b> — щёлкните место, чтобы перейти к нему",
    "In playlist: %s": "В плейлисте: %s",
    "⚠  “%s” is no longer in an open deck.":
        "⚠  «%s» больше нет ни в одном открытом деке.",
    "<b>%d</b> of %d checked tracks have an issue.":
        "Проблема есть у <b>%d</b> из %d проверенных треков.",
    "%d skipped — not found / not audio-analyzed.":
        "Пропущено: %d — не найдены / нет аудиоанализа.",
    "⚡ tempo label vs measured · 🐢/🐇 takt outside the TSO range · ⏱ short · ⏳ long · 🔇 hiss · 🧩 round structure (uneven dances, heat taper, heat tempo spread).":
        "⚡ метка темпа против измерения · 🐢/🐇 такт вне диапазона TSO · ⏱ короткий · ⏳ длинный · 🔇 шум · 🧩 структура туров (неравные танцы, сокращающиеся заходы, разброс темпа в заходе).",
    "🧩 <b>Round structure</b>": "🧩 <b>Структура туров</b>",
    "%d valid · %d unresolved across %d playlist.":
        "Действительных: %d · нерешённых: %d в плейлистах: %d.",
    "%d valid · %d unresolved across %d playlists.":
        "Действительных: %d · нерешённых: %d в плейлистах: %d.",
    "🔧 %d path line to fix": "🔧 Строк путей для исправления: %d",
    "🔧 %d path lines to fix": "🔧 Строк путей для исправления: %d",
    "✅ Nothing to fix": "✅ Исправлять нечего",
    "🔧 %d track can be moved onto the Reference path":
        "🔧 Треков, которые можно перенести на опорный путь: %d",
    "🔧 %d tracks can be moved onto the Reference path":
        "🔧 Треков, которые можно перенести на опорный путь: %d",
    "%d tracks — <span style='color:#2a7a45;'>%d valid</span> · <b style='color:#e07b00; font-size:13px;'>🔧 %d to fix</b> · <span style='color:#a33;'>%d unresolved</span>":
        "Треков: %d — <span style='color:#2a7a45;'>действительных: %d</span> · <b style='color:#e07b00; font-size:13px;'>🔧 исправить: %d</b> · <span style='color:#a33;'>нерешённых: %d</span>",
    "⚠  unresolved (no match under the search folders):":
        "⚠  не решено (нет совпадения в папках поиска):",
    "Rewrite %d path line(s) across %d playlist(s) in place?\n"
    "\n"
    "Only the file-path lines change — #EXTINF and every other line stay exactly as-is. This overwrites the .m3u files on disk; each original is kept next to it as <name>.m3u.bak.":
        "Переписать строки путей (%d) в плейлистах (%d) на месте?\n"
        "\n"
        "Меняются только строки с путями к файлам — #EXTINF и все остальные строки остаются точно как есть. Файлы .m3u на диске будут перезаписаны; каждый оригинал сохраняется рядом как <name>.m3u.bak.",
    "🧭  Rewrote %d path line(s) in %d playlist(s).":
        "🧭  Переписано строк путей: %d в плейлистах: %d.",
    "⚠  Left unchanged:": "⚠  Оставлено без изменений:",
    "… and %d more": "… и ещё %d",
    "Could not apply snapshot: %s": "Не удалось применить снимок: %s",
    "Could not restore saved playlist: %s":
        "Не удалось восстановить сохранённый плейлист: %s",
    "⚠  %d saved track(s) not found — is the music drive plugged in?":
        "⚠  Не найдено сохранённых треков: %d — подключён ли музыкальный диск?",
    "The saved session is kept as %s.": "Сохранённый сеанс остаётся как %s.",
    "↩  Restored your in-progress playlist — %d songs (%s, %s)":
        "↩  Ваш незаконченный плейлист восстановлен — треков: %d (%s, %s)",
    "↩  Restored your running order — %d tracks":
        "↩  Ваш порядок выступлений восстановлен — треков: %d",
    "↩  Restored your themed playlist — %d tracks":
        "↩  Ваш тематический список восстановлен — треков: %d",
    "All %d playlists already hold tracks — there's no free slot to import into.\n"
    "\n"
    "Clear a playlist first, or pick a single file to overwrite the focused deck.":
        "Все плейлисты (%d) уже содержат треки — свободного места для импорта нет.\n"
        "\n"
        "Сначала очистите плейлист или выберите один файл, чтобы перезаписать дек в фокусе.",
    "You picked %d files but only %d playlist slot(s) are free.\n"
    "\n"
    "Import the first %d into the free slots and skip the rest?":
        "Выбрано файлов: %d, но свободных мест для плейлистов только %d.\n"
        "\n"
        "Импортировать первые %d в свободные места и пропустить остальные?",
    "Importing %s …": "Импорт %s …",
    "Import failed: %s": "Импорт не удался: %s",
    "Remove %d title from %s?\n"
    "It is already planned in: %s":
        "Удалить треки (%d) из %s?\n"
        "Он уже запланирован в: %s",
    "Remove %d titles from %s?\n"
    "They are already planned in: %s":
        "Удалить треки (%d) из %s?\n"
        "Они уже запланированы в: %s",
    "Empty %d playlist? This can't be undone.":
        "Очистить плейлисты (%d)? Это нельзя отменить.",
    "Empty %d playlists? This can't be undone.":
        "Очистить плейлисты (%d)? Это нельзя отменить.",
    "↩  Restored your worked playlist for “%s” — %d songs":
        "↩  Ваш доработанный плейлист для «%s» восстановлен — треков: %d",
    "this competition": "этот турнир",
    "⚠  Session not saved — the snapshot failed: %r":
        "⚠  Сеанс не сохранён — снимок не удался: %r",
    "Could not write the PDF:\n"
    "%s":
        "Не удалось записать PDF:\n"
        "%s",
    "🖨 Playlist saved — %s": "🖨 Плейлист сохранён — %s",
    "Playlist saved as\n"
    "%s\n"
    "\n"
    "Open it now?":
        "Плейлист сохранён как\n"
        "%s\n"
        "\n"
        "Открыть его сейчас?",
    "Cycle 1 → 2 → 4 → 8 → no playlists (and back).":
        "Переключение 1 → 2 → 4 → 8 → без плейлистов (и обратно).",
    "Cycle 1 → 2 → 4 → no playlists (and back).":
        "Переключение 1 → 2 → 4 → без плейлистов (и обратно).",
    "Right click walks the cycle backwards.":
        "Правый щелчок проходит цикл в обратную сторону.",
    "8 splits into two tabs of four (Group A–D / Group E–H).":
        "8 делится на две вкладки по четыре (Группа A–D / Группа E–H).",
    "No-playlist hides every deck so the Practice / wishlist / library panes take over.":
        "«Без плейлистов» скрывает все деки, и место занимают панели Практика / список пожеланий / библиотека.",
    "Two or more decks also reveal the wishlist below.":
        "При двух и более деках ниже появляется и список пожеланий.",
    "Generate / Save / ↺ / play act on whichever deck has focus.":
        "Создать / Сохранить / ↺ / воспроизвести действуют на дек в фокусе.",
    "Show / hide the %s panel.\n"
    "Opens an empty panel — drop an existing .m3u onto it, or build a fresh list with 🤸 %s.":
        "Показать / скрыть панель %s.\n"
        "Открывает пустую панель — перетащите на неё существующий .m3u или создайте новый список через 🤸 %s.",
    "⭐ Swapped %s ⇄ %s": "⭐ Поменяны местами %s ⇄ %s",
    "Show only the %d track(s) currently in your wishlist(s),\n"
    "ranked by how well they match this song — pick the best one to add.\n"
    "Matches by song (title / fingerprint), so a different copy still counts.":
        "Показывать только треки (%d), которые сейчас в ваших списках пожеланий,\n"
        "отсортированные по тому, насколько они подходят к этому треку — выберите лучший для добавления.\n"
        "Сравнивается песня (название / отпечаток), так что другая копия тоже считается.",
    "🎼  Chroma cover / remix (melody/harmony, same tune)":
        "🎼  Chroma кавер / ремикс (мелодия/гармония, та же мелодия)",
    "🧠  MERT (deep embedding)": "🧠  MERT (глубокий эмбеддинг)",
    "🎧 Hear and choose — %s": "🎧 Послушать и выбрать — %s",
    "🎧 Hear and choose…": "🎧 Послушать и выбрать…",
    "Now: %s": "Сейчас: %s",
    "Now: —": "Сейчас: —",
    "Where from": "Откуда",
    "Offered for this slot": "Предложено для этого места",
    "Play / stop this title": "Воспроизвести / остановить этот трек",
    "▶ or Space plays a title, again stops it, Ctrl+←/→ seeks 30 s, Ctrl+Shift+←/→ plays the title before or after it; a double click or \"Take\" puts it into the slot.":
        "▶ или Пробел воспроизводит трек, повторно — останавливает, Ctrl+←/→ перематывает на 30 с, Ctrl+Shift+←/→ играет предыдущий или следующий трек; двойной щелчок или «Взять» ставит его на место.",
    "Take": "Взять",
    "⚖️  Combined: timbre + groove + melody (mean)":
        "⚖️  Комбинированно: тембр + грув + мелодия (среднее)",
    "⚖️  Combined + MERT: timbre + groove + melody + MERT (mean)":
        "⚖️  Комбинированно + MERT: тембр + грув + мелодия + MERT (среднее)",
    "⚖️ Combined + MERT — the mean of where each title ranks by timbre, groove, melody and MERT.":
        "⚖️ Комбинированно + MERT — среднее положение каждого трека по тембру, груву, мелодии и MERT.",
    "⚖️ Combined — the mean of where each title ranks by timbre, groove and melody.":
        "⚖️ Комбинированно — среднее положение каждого трека по тембру, груву и мелодии.",
    "★  Only rarely played (1–%d playlists)":
        "★  Только редко игравшиеся (1–%d плейлистов)",
    "The same three picks as 📚 the library's ★ Plays selector.\n"
    "'Never played': the track is in none of your old playlists.\n"
    "'Rarely played': in 1–%d of them — %d+ is a proven title.\n"
    "'Not since 1 y': it is played, but the newest playlist carrying\n"
    "it is from an earlier year — the year comes from the playlist's\n"
    "path, so lists without a date never count as old.":
        "Те же три фильтра, что и селектор ★ Играл в 📚 библиотеке.\n"
        "«Ни разу не играл»: трека нет ни в одном из ваших старых плейлистов.\n"
        "«Редко играл»: в 1–%d из них — от %d это проверенный трек.\n"
        "«Не играл 1 год»: он играется, но самый новый плейлист с ним\n"
        "из более раннего года — год берётся из пути плейлиста,\n"
        "поэтому списки без даты никогда не считаются старыми.",
    "%d %s tracks most often played together with this one — ▶ to preview, double-click to open, drag rows into another app":
        "Треков: %d (%s), чаще всего игравшихся вместе с этим — ▶ для прослушивания, двойной щелчок — открыть, строки можно перетащить в другое приложение",
    "%d %s tracks most similar (sound-alike) to this one — ▶ to preview, double-click to open, drag rows into another app":
        "Треков: %d (%s), больше всего похожих (по звучанию) на этот — ▶ для прослушивания, двойной щелчок — открыть, строки можно перетащить в другое приложение",
    "⭐ wishlist only": "⭐ только список пожеланий",
    "📜 played in this round before": "📜 играл раньше в этом туре",
    "📜  Only titles I played in this round before (%s)":
        "📜  Только треки, которые я играл раньше в этом туре (%s)",
    "Show only titles your past competitions played in this round —\n"
    "any heat of it, from lists of a class and age category that fit\n"
    "this deck (the same history as 📜 Find planned before).\n"
    "Still ranked by how much they sound like this one.":
        "Показывать только треки, которые ваши прошлые турниры играли в этом туре —\n"
        "в любом заходе, из списков класса и возрастной категории, подходящих\n"
        "к этому деку (та же история, что и 📜 Найти запланированные ранее).\n"
        "По-прежнему отсортированы по сходству звучания с этим треком.",
    "🎙 instrumental only (%d vocal hidden)":
        "🎙 только инструментальные (скрыто с вокалом: %d)",
    "%s (%d hidden)": "%s (скрыто: %d)",
    "%d duplicate hidden": "Скрыто дубликатов: %d",
    "%d duplicates hidden": "Скрыто дубликатов: %d",
    "%d track(s) you planned for this dance &amp; round in past competitions — best competition match first (see Class) — ▶ to preview, drag a row onto the slot, double-click to open":
        "Треки (%d), которые вы планировали для этого танца &amp; тура на прошлых турнирах — сначала лучшее турнирное совпадение (см. Класс) — ▶ для прослушивания, перетащите строку на место, двойной щелчок — открыть",
    "Similar to: %s": "Похоже на: %s",
    "📋 Learned from your playlists — %d often played together.":
        "📋 Изучено по вашим плейлистам — часто играются вместе: %d.",
    "🧠  Rebuild %s index…": "🧠  Перестроить индекс %s…",
    "%s vectors for these %d tracks haven't been built yet.\n"
    "\n"
    "Building analyses each track once (slow the first time, then cached).\n"
    "Build now?":
        "Векторы %s для этих треков (%d) ещё не построены.\n"
        "\n"
        "Построение анализирует каждый трек один раз (в первый раз медленно, затем из кэша).\n"
        "Построить сейчас?",
    "Building %s embedding index…": "Построение индекса эмбеддингов %s…",
    "All %d file(s) failed to embed.\n"
    "\n"
    "First error:\n"
    "%s\n"
    "\n"
    "Common causes: the neural model couldn't load, or the deps are mismatched. See the console log for the full traceback.":
        "Не удалось обработать ни один файл (%d).\n"
        "\n"
        "Первая ошибка:\n"
        "%s\n"
        "\n"
        "Частые причины: не удалось загрузить нейронную модель или зависимости не совпадают. Полную трассировку показывает журнал консоли.",
    "🧠 %s index ready (%d embedded, %d failed).":
        "🧠 Индекс %s готов (обработано %d, ошибок %d).",
    "🧠 %s index ready (%d embedded).": "🧠 Индекс %s готов (обработано %d).",
    "%s indexing cancelled — showing librosa results.":
        "Индексация %s прервана — показаны результаты librosa.",
    "Ranking by %s embedding…": "Сортировка по эмбеддингу %s…",
    "No %s matches yet — try building the index over more tracks.":
        "Совпадений %s пока нет — постройте индекс по большему числу треков.",
    "🧠 %s — %d deep-embedding matches.":
        "🧠 %s — совпадений по глубокому эмбеддингу: %d.",
    "Refreshed — %d similar to %s": "Обновлено — найдено %d похожих на %s",
    "%s / %s  (%s left)": "%s / %s  (осталось %s)",
    "~%s remaining": "осталось ~%s",
    "Listing files…": "Составление списка файлов…",
    "⬇ Downloading the MERT model (once) — MB":
        "⬇ Загрузка модели MERT (однократно) — МБ",
    "This is not an audio file, so it won't be opened:\n"
    "%s":
        "Это не аудиофайл, поэтому он не будет открыт:\n"
        "%s",
    "File not found:\n"
    "%s":
        "Файл не найден:\n"
        "%s",
    "Couldn't open the file:\n"
    "%s":
        "Не удалось открыть файл:\n"
        "%s",
    "Folder not found:\n"
    "%s":
        "Папка не найдена:\n"
        "%s",
    "Couldn't open the folder:\n"
    "%s":
        "Не удалось открыть папку:\n"
        "%s",
    "Couldn't reveal the file:\n"
    "%s":
        "Не удалось показать файл:\n"
        "%s",
    "✅  No duplicates among the %d file added.":
        "✅  Среди добавленных файлов (%d) дубликатов нет.",
    "✅  No duplicates among the %d files added.":
        "✅  Среди добавленных файлов (%d) дубликатов нет.",
    "Comparison failed:\n"
    "%s":
        "Сравнение не удалось:\n"
        "%s",
    "✅  %d hard duplicate(s) to remove, %d unused track(s) to export (of %d; %d Paso Doble kept). Review below, then export.":
        "✅  Точных дубликатов к удалению: %d, неиспользуемых треков к экспорту: %d (из %d; пасодоблей сохранено: %d). Проверьте ниже, затем экспортируйте.",
    "Could not write file:\n"
    "%s":
        "Не удалось записать файл:\n"
        "%s",
    "The reference playlist itself was overwritten with the cleaned list.":
        "Сам эталонный плейлист перезаписан очищенным списком.",
    "The reference playlist was left unchanged.":
        "Эталонный плейлист оставлен без изменений.",
    "📤  Exported %d track(s) (sorted by dance) → %s":
        "📤  Экспортировано треков: %d (по танцам) → %s",
    "📤  Exported %d track(s) → %s": "📤  Экспортировано треков: %d → %s",
    "Exported %d unused track(s) to:\n"
    "%s\n"
    "\n"
    "%d hard duplicate(s) removed. %s":
        "Экспортировано неиспользуемых треков: %d, в:\n"
        "%s\n"
        "\n"
        "Удалено точных дубликатов: %d. %s",
    "🔁  Replace in %s": "🔁  Заменить в %s",
    "This song is in %d open playlists. Replacing it on one\n"
    "row leaves the other copies — pick a copy on each of its rows to\n"
    "replace them all (the choices are merged when you press Apply).":
        "Этот трек есть в открытых плейлистах: %d. Замена в одной\n"
        "строке оставляет другие копии — выберите копию в каждой его строке,\n"
        "чтобы заменить их все (выбор объединяется при нажатии «Применить»).",
    "%d occurrence(s) are set to Replace but have no replacement track yet.\n"
    "Pick a track for each, or switch them back to Keep.":
        "Вхождений с «Заменить», но ещё без трека замены: %d.\n"
        "Выберите трек для каждого или верните их на «Оставить».",
    "%d copy/copies are set to two different changes on different rows.\n"
    "Choose the same on each, or set one back to Keep all.":
        "Копий с двумя разными изменениями в разных строках: %d.\n"
        "Выберите везде одно и то же или верните одну на «Оставить все».",
    "🗑  Remove from %s": "🗑  Удалить из %s",
    "🗑  Removed %d duplicate": "🗑  Удалено дубликатов: %d",
    "🗑  Removed %d duplicates": "🗑  Удалено дубликатов: %d",
    "A track named “%s” is already in this playlist,\n"
    "but it’s a different file.":
        "Трек с названием «%s» уже есть в этом плейлисте,\n"
        "но это другой файл.",
    "“%s” is already in this playlist —\n"
    "“%s” looks like the same title in another file.":
        "«%s» уже есть в этом плейлисте —\n"
        "«%s» похоже на тот же трек в другом файле.",
    "“%s” is already in this playlist.\n"
    "\n"
    "Remove it from the wishlist anyway?":
        "«%s» уже есть в этом плейлисте.\n"
        "\n"
        "Всё равно удалить из списка пожеланий?",
    "“%s” is already in this playlist.\n"
    "\n"
    "Remove it from the playlist anyway?":
        "«%s» уже есть в этом плейлисте.\n"
        "\n"
        "Всё равно удалить из плейлиста?",
    "%d dragged track(s) are already in this playlist.\n"
    "\n"
    "Remove them from the wishlist anyway?":
        "Перетащенных треков, уже стоящих в этом плейлисте: %d.\n"
        "\n"
        "Всё равно удалить их из списка пожеланий?",
    "%d dragged track(s) are already in this playlist.\n"
    "\n"
    "Remove them from the playlist anyway?":
        "Перетащенных треков, уже стоящих в этом плейлисте: %d.\n"
        "\n"
        "Всё равно удалить их из плейлиста?",
    "“%s” looks like a %s track, but this slot is %s.\n"
    "\n"
    "Replace anyway?":
        "«%s» похож на трек %s, но это место — %s.\n"
        "\n"
        "Всё равно заменить?",
    "Remove this whole heat (all dances) from %s?":
        "Удалить весь этот заход (все танцы) из %s?",
    "⬆  %d song(s) moved up into empty slots":
        "⬆  Треков, сдвинутых на свободные места: %d",
    "Remove the entire round “%s” and all %d of its heats?":
        "Удалить весь тур «%s» со всеми заходами (%d)?",
    "Remove %s from %s?\n"
    "%d song(s) in this round will be cleared.":
        "Удалить %s из %s?\n"
        "Будут очищены треки этого тура: %d.",
    "Hide the empty %s from %s?": "Скрыть пустой %s в %s?",
    "Remove %s from all rounds and heats?\n"
    "%d song(s) across the playlist will be cleared.":
        "Удалить %s из всех туров и заходов?\n"
        "Будут очищены треки во всём плейлисте: %d.",
    "Hide the empty %s from all rounds?": "Скрыть пустой %s во всех турах?",
    "%d dropped track(s) look like %s dances, but this is a %s list.\n"
    "\n"
    "Add them anyway?":
        "Отпущенных треков: %d — похожи на танцы %s, но это список %s.\n"
        "\n"
        "Всё равно добавить?",
    "All open playlists (%d deck)": "Все открытые плейлисты (деков: %d)",
    "All open playlists (%d decks)": "Все открытые плейлисты (деков: %d)",
    "%d file added.": "Добавлено файлов: %d.",
    "%d files added.": "Добавлено файлов: %d.",
    "📅 Tournament day only (%d playlist)":
        "📅 Только турнирный день (плейлистов: %d)",
    "📅 Tournament day only (%d playlists)":
        "📅 Только турнирный день (плейлистов: %d)",
    "Dance: %s": "Танец: %s",
    "%s (%d beats/bar)": "%s (долей в такте: %d)",
    "'%s' is not a valid round pattern for %s %s — use heat counts like 6-3-2-1.":
        "«%s» — недопустимая схема туров для %s %s — используйте числа заходов, например 6-3-2-1.",
    "Red: the pool can't carry a competition (pool < %d or proven < %d — a 6-3-2-1 needs 12 per dance).  Orange: < 80 %% of the takt-labelled tracks are tournament tempo, or over half the pool is stale (no dateable playlist in ≥ 3 years; 'never played' always counts as stale).  Double-click a row to browse its never-played tracks in 📚 the library.":
        "Красный: репертуара не хватит на турнир (репертуар < %d или проверенных < %d — схеме 6-3-2-1 нужно 12 на танец).  Оранжевый: < 80 %% треков с меткой такта имеют турнирный темп, или больше половины репертуара устарело (нет датируемого плейлиста за ≥ 3 года; «ни разу не играл» всегда считается устаревшим).  Двойной щелчок по строке показывает её ни разу не игравшие треки в 📚 библиотеке.",
    "⚠️ %d gap(s) found": "⚠️ Найдено пробелов: %d",
    "(%d playlist)": "(плейлистов: %d)",
    "(%d playlists)": "(плейлистов: %d)",
    "%d song": "Треков: %d",
    "%d songs": "Треков: %d",
    "The playlist file is gone:\n"
    "\n"
    "%s":
        "Файла плейлиста больше нет:\n"
        "\n"
        "%s",
    "No .m3u playlists found under “%s”.":
        "В «%s» не найдено плейлистов .m3u.",
    "Remove “%s” from the tree?\n"
    "\n"
    "%d playlist file(s) are listed under it — they stay on disk, only this entry goes.":
        "Удалить «%s» из дерева?\n"
        "\n"
        "Под ним файлов плейлистов: %d — они остаются на диске, исчезает только эта запись.",
    "Remove %d entries from the tree?\n"
    "\n"
    "%d playlist file(s) are listed under them — they stay on disk, only these entries go.":
        "Удалить записи (%d) из дерева?\n"
        "\n"
        "Под ними файлов плейлистов: %d — они остаются на диске, исчезают только эти записи.",
    "%s and %s are different dances.\n"
    "\n"
    "Only titles of the same dance can swap places, so every round keeps its dances.":
        "%s и %s — разные танцы.\n"
        "\n"
        "Местами могут меняться только треки одного танца, чтобы каждый тур сохранял свои танцы.",
    "No past competition plans found for %s in %s.":
        "Прошлых турнирных планов для %s в %s не найдено.",
    "Remove all %d track(s) from wishlist%s?":
        "Удалить все треки (%d) из списка пожеланий%s?",
    "Remove the entire playlist%s? The table will be blank again.":
        "Удалить весь плейлист%s? Таблица снова станет пустой.",
    "Couldn't read as an audio track:": "Не удалось прочитать как аудиотрек:",
    "This list": "Этот список",
    "%s holds %d title twice — the same audio, e.g. a copy of the file on another drive:\n"
    "\n"
    "%s\n"
    "\n"
    "Remove the earlier copy? The last one stays.":
        "В %s дважды встречаются треки: %d — тот же звук, напр. копия файла на другом диске:\n"
        "\n"
        "%s\n"
        "\n"
        "Удалить более раннюю копию? Последняя остаётся.",
    "%s holds %d titles twice — the same audio, e.g. a copy of the file on another drive:\n"
    "\n"
    "%s\n"
    "\n"
    "Remove the earlier copies? The last one stays.":
        "В %s дважды встречаются треки: %d — тот же звук, напр. копия файла на другом диске:\n"
        "\n"
        "%s\n"
        "\n"
        "Удалить более ранние копии? Последняя остаётся.",
    "Any OpenAI-compatible /chat/completions host.":
        "Любой OpenAI-совместимый хост /chat/completions.",
    "%d models loaded.": "Загружено моделей: %d.",
    "%d suggestions — %d in your library.":
        "Предложений: %d — в вашей библиотеке: %d.",
    "▾  %d more lines": "▾  ещё строк: %d",
    "thinking…": "думает…",
    "Couldn't read “%s” as an audio track.":
        "Не удалось прочитать «%s» как аудиотрек.",
    "“%s” holds %d tracks (subfolders included).\n"
    "\n"
    "Reading them all takes a moment — every file's tags are read on the way in.\n"
    "\n"
    "Add them?":
        "В «%s» треков: %d (включая подпапки).\n"
        "\n"
        "Чтение всех займёт немного времени — по пути читаются теги каждого файла.\n"
        "\n"
        "Добавить их?",
    "↩ Left at %s — starts there again":
        "↩ Остановлено на %s — начнётся снова оттуда",
    "Plays %s — the stillness at the edges of the file is skipped":
        "Играет %s — тишина по краям файла пропускается",
    "Shorter than the configured play length (%s)":
        "Короче заданной длительности воспроизведения (%s)",
    "%s already holds %d track(s).\n"
    "\n"
    "Importing %s REPLACES them — the list is loaded fresh from the file, the tracks in it now are dropped.\n"
    "\n"
    "Import anyway?":
        "В %s уже треков: %d.\n"
        "\n"
        "Импорт %s ЗАМЕНЯЕТ их — список загружается заново из файла, треки, которые в нём сейчас, пропадают.\n"
        "\n"
        "Всё равно импортировать?",
    "“%s” is already used in this playlist.":
        "«%s» уже используется в этом плейлисте.",
    "A %s track can only move into another %s slot — not a %s slot.":
        "Трек %s можно переместить только на другое место %s — не на место %s.",
    "Dances (%d): %s": "Танцы (%d): %s",
    "Order: %s, %s, …": "Порядок: %s, %s, …",
    "🟰  Identical files (%d)": "🟰  Одинаковые файлы (%d)",
    "🧹  Remove the earlier copies, the last stays":
        "🧹  Удалить более ранние копии, последняя остаётся",
    "✏  %d pads selected — what you change here (colour, volume, fade, 🔁, 🔈, 🎶, S) applies to all of them.\n"
    "Label and shortcut stay with this pad.":
        "✏  Выбрано пэдов: %d — то, что вы меняете здесь (цвет, громкость, затухание, 🔁, 🔈, 🎶, S), применяется ко всем.\n"
        "Подпись и сочетание клавиш остаются у этого пэда.",
    "Empty = this slot's default (%s)":
        "Пусто = значение по умолчанию для этого слота (%s)",
    "Empty = no key (this slot has no default)":
        "Пусто = без клавиши (у этого слота нет значения по умолчанию)",
    "%s (wall)": "%s (Cartwall)",
    "⚠ already used by %s": "⚠ уже занято: %s",
    "%d key claimed twice — the marked ones will not fire. Pad keys win over slot keys.":
        "Клавиш, назначенных дважды: %d — отмеченные не сработают. Клавиши пэдов важнее клавиш слотов.",
    "%d keys claimed twice — the marked ones will not fire. Pad keys win over slot keys.":
        "Клавиш, назначенных дважды: %d — отмеченные не сработают. Клавиши пэдов важнее клавиш слотов.",
    "Page %d": "Страница %d",
    "page %d": "страница %d",
    "%d pads need %d pages at %d × %d; the wall keeps at most %d.\n"
    "Clear some pads or pick a bigger layout.":
        "Пэдам (%d) нужно страниц: %d при %d × %d; Cartwall вмещает не более %d.\n"
        "Очистите часть пэдов или выберите сетку побольше.",
    "Remove %s and the %d pads on it?\n"
    "The sample files are left alone — only the pads go.":
        "Удалить %s и пэды на ней (%d)?\n"
        "Файлы сэмплов не трогаются — удаляются только пэды.",
    "%d pads do not fit one %d × %d page.\n"
    "Pick a bigger layout first.":
        "Пэды (%d) не помещаются на одну страницу %d × %d.\n"
        "Сначала выберите сетку побольше.",
    "Could not write the wall:\n"
    "%s":
        "Не удалось записать Cartwall:\n"
        "%s",
    "%d pads written to\n"
    "%s\n"
    "\n"
    "The sample files themselves are not copied — the wall stores their paths.":
        "Записано пэдов: %d, в\n"
        "%s\n"
        "\n"
        "Сами файлы сэмплов не копируются — Cartwall хранит их пути.",
    "Replace the current wall with %d pads from\n"
    "%s?":
        "Заменить текущую Cartwall пэдами (%d) из\n"
        "%s?",
    "The wall is full: %d of %d tracks were placed.\n"
    "Clear some pads or pick a bigger layout for the rest.":
        "Cartwall заполнена: размещено %d из %d треков.\n"
        "Очистите часть пэдов или выберите сетку побольше для остальных.",
    "🔇 Only stillness left from %s — song ended.":
        "🔇 С %s только тишина — трек закончен.",
    "🔇 Skipped %ss of leading silence.": "🔇 Пропущено %s с тишины в начале.",
    "⚠️ Sample not found: %s": "⚠️ Сэмпл не найден: %s",
    "\n▶ Queue: place %d — Ctrl+click takes it out":
        "\n▶ Очередь: место %d — Ctrl+клик убирает его",
    "\nCtrl+click: into the ▶ queue":
        "\nCtrl+клик: в очередь ▶",
    "⚠️ Sample not found, skipped: %s":
        "⚠️ Сэмпл не найден, пропущен: %s",
    "⚠️ Queue stopped: none of its samples were found":
        "⚠️ Очередь остановлена: ни один сэмпл не найден",
    "⏱ Auto-advance pause extended by %ss.":
        "⏱ Пауза автоперехода продлена на %s с.",
    "🎯 Highlight at %s — %d mark(s). ✔ Done editing arms the stop.":
        "🎯 Кульминация на %s — меток: %d. ✔ Завершить правку взводит остановку.",
    "🎯 PD highlight %d marked at %s (stop set to #%s)":
        "🎯 Кульминация PD %d отмечена на %s (остановка на №%s)",
    "🏁  %s finished": "🏁  %s закончен",
    "🏁 %s finished — auto-advance stopped.":
        "🏁 %s закончен — автопереход остановлен.",
    "Can't cue — file not found: %s":
        "Нельзя подготовить — файл не найден: %s",
    "⏸ Cued %s — press ⏯ to play. — ⏭ walks the playlist":
        "⏸ %s подготовлен — нажмите ⏯ для воспроизведения. — ⏭ идёт по плейлисту",
    "⏸ Cued %s — press ⏯ to play.":
        "⏸ %s подготовлен — нажмите ⏯ для воспроизведения.",
    "the %s %s of this round": "%s %s этого тура",
    "this %s": "этот %s",
    "🎚 TSO tempo: %s %s → T%s (target T%s from %s)":
        "🎚 Темп TSO: %s %s → T%s (цель T%s из %s)",
    "⏸  cued: %s": "⏸  готов: %s",
    "↩ Picked up at %s.": "↩ Продолжено с %s.",
    "⏸  editing: %s": "⏸  правка: %s",
    "⏸  editing": "⏸  правка",
    "Play length per song: each song is stopped after this time,\n"
    "ramping down over the fade time first. Steps of %s s\n"
    "up to %s; one step further is\n"
    "'full' — no cut, every title plays to its own end.\n"
    "\n"
    "Double-click to type an exact length (e.g. 1:37).":
        "Длительность на трек: каждый трек останавливается после этого времени,\n"
        "сначала затухая в течение времени затухания. Шаги по %s с\n"
        "до %s; ещё один шаг —\n"
        "«полностью» — без обрезки, каждый трек играет до своего конца.\n"
        "\n"
        "Двойной щелчок — ввести точную длину (напр. 1:37).",
    "Move this highlight 0.1 s earlier": "Сдвинуть кульминацию на 0,1 с раньше",
    "Move this highlight 0.1 s later": "Сдвинуть кульминацию на 0,1 с позже",
    "⏱  Titles over an hour read:": "⏱  Треки длиннее часа:",
    "1:04:00 (hours)": "1:04:00 (часы)",
    "64:00 (minutes)": "64:00 (минуты)",
    "How the player and the mini player show the times of a title\nlonger than 59 minutes, such as a long mix.": "Как плеер и мини-плеер показывают время трека\nдлиннее 59 минут, например длинного микса.",
    "🐞 Bugs & ideas": "🐞 Ошибки и идеи",
    "Report a bug or suggest a feature as a GitHub issue: %s": "Сообщите об ошибке или предложите функцию через issue на GitHub: %s",
    "open a new issue": "создать новый issue",
    "No GitHub account? Write to %s": "Нет аккаунта GitHub? Пишите на %s",
    "🔌 Drive %s is gone: USB stick unplugged? %d titles can't play until it is back.": "🔌 Диск %s пропал: вынута USB-флешка? Треков, которые не сыграют до его возвращения: %d.",
    "⚠️ %d titles are gone from disk: moved, renamed or deleted?": "⚠️ Треков больше нет на диске: %d. Перемещены, переименованы или удалены?",
    "🔌 %d titles are back and can play again.": "🔌 Треки вернулись и снова могут играть: %d.",
    "🐂  Keep the pad down while a Paso Doble waits to start":
        "🐂  Держать пэд тихо, пока Пасодобль ждёт старта",
    "With 'Start after' set for the Paso Doble, the deck stands still\nbetween the call and the first bar while the couples walk on.\nOn, a 🎶 Background pad stays down through that wait as if the\nmusic already played. Off, it comes back in the wait like after\nany other title.":
        "Если для Пасодобля задан «Старт через», дека стоит между\nобъявлением и первым тактом, пока пары выходят на паркет.\nВкл.: пэд 🎶 Фон остаётся приглушённым всё это ожидание,\nкак будто музыка уже играет. Выкл.: он возвращается в ожидании,\nкак после любого другого трека.",
    "Off, a title waits until a 🎛 cartwall pad set to 🎶 Background\nhas faded out completely, then starts into silence. The wait is\nthe fade-out time above, or less if the bed is already going down.\nOn, the title starts at once and plays over the fade-out.":
        "Выкл.: трек ждёт, пока пэд 🎛 картволла с 🎶 Фон полностью\nзатихнет, и начинается в тишине. Ожидание равно времени затухания\nвыше или короче, если фон уже затихает.\nВкл.: трек стартует сразу и звучит поверх затухания.",
    "🔉↓  Fade by hand over:":
        "🔉↓  Затухание вручную за:",
    "as the list's fade-out":
        "как затухание списка",
    "How long 🔉↓ Fade out now, 🛑 Fade out and hold, a ⏹ stop at a time\nand the fade before quitting take. The fade at the end of the play\nlength keeps the playlist's own fade-out time.\n0 = the playlist's fade-out time for these as well.":
        "Сколько длятся 🔉↓ Затухание сейчас, 🛑 Затухание и стоп, остановка\n⏹ по времени и затухание перед выходом. Затухание в конце длины\nвоспроизведения сохраняет время затухания плейлиста.\n0 = и для них время затухания плейлиста.",
    "🔈  Duck under a voice or pad over:":
        "🔈  Приглушать под голос или пэд за:",
    "back up over:":
        "обратно за:",
    "How fast the music gets out of the way when the announcer speaks\nor a 🎛 cartwall pad plays, and how fast it comes back after.\nShort down keeps a pad's first beat clear; a slow way up keeps\nthe return from being an event of its own. The 🔉 Duck button\nis not ramped: it is immediate.":
        "Как быстро музыка уходит, когда говорит диктор или играет пэд 🎛\nкартволла, и как быстро возвращается после. Быстрый спуск\nоставляет первый удар пэда чистым; медленный подъём не делает\nвозврат отдельным событием. Кнопка 🔉 Приглушить работает\nсразу, без плавного перехода.",
    "🥇  Final: the music plays on":
        "🥇  Финал: музыка продолжает играть",
    "After the play length has faded a title of the final out, it comes back up as background while the couples celebrate — until 🔉↓ fades it, the next title starts or the file ends. Only under ✋ Manual: with ⏭ Auto the ⏸ pause and its music follow each title, and a title of the final ends as always.":
        "Когда длительность воспроизведения увела трек финала в тишину, он снова звучит фоном, пока пары празднуют — пока 🔉↓ не выведет его, не начнётся следующий трек или не закончится файл. Только в режиме ✋ Вручную: при ⏭ Авто за каждым треком следуют ⏸ пауза и её музыка, и трек финала заканчивается как обычно.",
    "Off":
        "Выкл.",
    "After the last dance of the final":
        "После последнего танца финала",
    "After every dance of the final":
        "После каждого танца финала",
    "Which titles of the final come back up after the play\nlength has faded them out. A round is the final when it\nis named Finale, Final or Endrunde.":
        "Какие треки финала снова звучат после того, как длительность\nувела их в тишину. Раунд считается финалом, если он\nназывается Finale, Final или Endrunde.",
    "Level:":
        "Уровень:",
    "How loud it comes back, in % of the music's level.":
        "Насколько громко он возвращается, в % от уровня музыки.",
    "Up over:":
        "Нарастание за:",
    "How long it takes to come back up. 0 = at once.":
        "Сколько времени он нарастает обратно. 0 = сразу.",
    "Down over:":
        "Затухание за:",
    "How long it takes to go down when 🔉↓ fades it.":
        "Сколько он затихает, когда 🔉↓ выводит его.",
    "quieter":
        "тише",
    "louder":
        "громче",
    "Volume %s %s — hold to glide":
        "Громкость %s %s — удерживайте для плавного изменения",
    "Duck to %d %%, again to mute, again back to full":
        "Приглушить до %d %%, ещё раз — без звука, ещё раз — на полную",
    "🎶 Pause music: the cartwall's ▶ queue plays its 🎶 Background pads.":
        "🎶 Музыка в паузе: очередь ▶ картволла играет свои 🎶 фоновые пады.",
    "mute":
        "без звука",
    "🌙  Then:":
        "🌙  Затем:",
    "A closing song that plays once the stop has ended the music —\n\"Who moved the clock today\". It plays at the music's volume to\nits end (🔉↓ fades it); then the next title waits for ⏯.\nOnly after the planned stop, never after ⏹ by hand.":
        "Финальная песня, которая звучит, когда остановка завершила музыку, —\n«Who moved the clock today». Она играет с громкостью музыки\nдо конца (🔉↓ плавно её гасит); затем следующий трек ждёт ⏯.\nТолько после запланированной остановки, не после ⏹ вручную.",
    "No closing song":
        "Без финальной песни",
    "⏹ Stopped as planned — 🌙 the closing song plays, then ⏯ the next title.":
        "⏹ Остановлено по плану — 🌙 звучит финальная песня, затем ⏯ следующий трек.",
    "🌙 Closing song not found: %s":
        "🌙 Финальная песня не найдена: %s",
    "📄  Move to page":
        "📄  Перенести на страницу",
    "“%s” is full: %d of %d pads were moved.":
        "«%s» заполнена: перенесено %d из %d пэдов.",
    "🔠  Text size:":
        "🔠  Размер текста:",
    "🏅 Background: entrance & awards":
        "🏅 Фон: выход и награждение",
    "<b>🏅 Background: entrance & awards</b> — a title with one of these words in its file or folder name, title or comment, comma-separated:":
        "<b>🏅 Фон: выход и награждение</b> — трек, у которого одно из этих слов есть в имени файла или папки, названии или комментарии, через запятую:",
    "Upper or lower case does not matter, and a part of a word is\nenough: 'Award' also finds '(Background Award)'. Shown under\n🏅 in the library's category filter and kept out of generated\nplaylists. Leave it empty to go by the folders below only.":
        "Регистр не важен, достаточно части слова: 'Award' находит и\n'(Background Award)'. Видно под 🏅 в фильтре категорий\nбиблиотеки и никогда не попадает в созданные плейлисты.\nОставьте пустым, чтобы искать только по папкам ниже.",
    "…and every title in these folders and below, one folder per line:":
        "…и каждый трек в этих папках и глубже, по одной папке в строке:",
    "Entrance and award music folder":
        "Папка с музыкой выхода и награждения",
    "Delete the highlight at %s s": "Удалить кульминацию на %s с",
    "Compensate loudness differences between tracks on playback:\n"
    "each song's measured EBU R128 loudness is pulled towards a\n"
    "common target, so quiet old recordings and loud modern\n"
    "masters play at a similar level.":
        "Выравнивать при воспроизведении разницу громкости между треками:\n"
        "измеренная громкость EBU R128 каждого трека подтягивается к\n"
        "общей цели, чтобы тихие старые записи и громкие современные\n"
        "мастеры звучали примерно одинаково.",
    "ℹ No loudness measured yet — tracks play at their\n"
    "original volume. Run 📊 Analyze loudness (⚙ Settings)\n"
    "to equalize them.":
        "ℹ Громкость ещё не измерена — треки играют с\n"
        "исходной громкостью. Запустите 📊 Анализ громкости (⚙ Настройки),\n"
        "чтобы выровнять их.",
    "ℹ %d open-playlist track not measured yet — it plays at original volume.\n"
    "Run 📊 Analyze loudness (⚙ Settings) to equalize it too.":
        "ℹ Треков открытых плейлистов ещё не измерено: %d — они играют с исходной громкостью.\n"
        "Запустите 📊 Анализ громкости (⚙ Настройки), чтобы выровнять и их.",
    "ℹ %d open-playlist tracks not measured yet — they play at original volume.\n"
    "Run 📊 Analyze loudness (⚙ Settings) to equalize them too.":
        "ℹ Треков открытых плейлистов ещё не измерено: %d — они играют с исходной громкостью.\n"
        "Запустите 📊 Анализ громкости (⚙ Настройки), чтобы выровнять и их.",
    "⚡ Tempo: measured ~%s vs label %s bpm (off %s%%)":
        "⚡ Темп: измерено ~%s против метки %s bpm (отклонение %s%%)",
    "label": "метка",
    "measured": "измерено",
    "🐢 Too slow: T%s (%s), TSO %s-%s":
        "🐢 Слишком медленно: T%s (%s), TSO %s-%s",
    "🐇 Too fast: T%s (%s), TSO %s-%s": "🐇 Слишком быстро: T%s (%s), TSO %s-%s",
    "⏱ Short: real play %s — %s file minus %ss silence (≤ %s)":
        "⏱ Короткий: реальное звучание %s — файл %s минус %s с тишины (≤ %s)",
    "⏱ Short: %s (≤ %s play length)": "⏱ Короткий: %s (≤ %s длительности)",
    "⏳ Long: %s (> %s)": "⏳ Длинный: %s (> %s)",
    "🔇 Hiss: never quieter than %s dB (> %s dB)":
        "🔇 Шум: никогда не тише %s дБ (> %s дБ)",
    "“%s”: uneven dance counts — ": "«%s»: неравное число танцев — ",
    "%s %d/%d (missing in heat ": "%s %d/%d (нет в заходе ",
    "Final ": "Финал ",
    "Semifinal ": "Полуфинал ",
    "“%s”": "«%s»",
    " has %d heats, expected 1.": ": заходов %d, ожидался 1.",
    " has %d heats, expected 2.": ": заходов %d, ожидалось 2.",
    "“%s”: %s heats differ by %d takte (allowed: 1) — ":
        "«%s»: заходы %s различаются (тактов: %d, допустимо: 1) — ",
    "heat %d: T%s “%s”": "заход %d: T%s «%s»",
    "“%s” — %s": "«%s» — %s",
    "🧩 “%s” %s heats differ by %d takte (allowed: 1)":
        "🧩 «%s»: заходы %s различаются (тактов: %d, допустимо: 1)",
    "title": "название",
    "dance": "танец",
    "takt": "такт",
    "year": "год",
    "genre": "жанр",
    "classes": "классы",
    "instrumental": "инструментал",
    "christmas": "Рождество",
    "ID3 title": "название ID3",
    "artist": "исполнитель",
    "length": "длительность",
    "album": "альбом",
    "markers": "метки",
    "⚠ %s: only %d proven song(s) — finals need %d; expect fresh fill-ins.":
        "⚠ %s: проверенных треков только %d — финалам нужно %d; ждите новых заполнителей.",
    "♪ %s: no track near the ideal %s bpm.":
        "♪ %s: нет трека около идеального темпа %s bpm.",
    "✦ %d/%d songs are fresh (%d%% new).":
        "✦ Новых треков: %d/%d (%d%% новых).",
    "⚠ %s could not fill %d of %d slots (%s) — park more tracks there or switch the source back to the Favorites library.":
        "⚠ %s: не удалось заполнить %d из %d мест (%s) — положите туда больше треков или верните источник на избранную библиотеку.",
    "⭐ the open wishlists": "⭐ открытые списки пожеланий",
    "📅 Day plan: %d competition(s) generated — %d songs locked for the day (Paso Doble may repeat)":
        "📅 План дня: создано турниров: %d — треков, закреплённых за днём: %d (Paso Doble может повторяться)",
    "🕑 Seeded from %d past “%s” list(s) — round pool sizes: %s":
        "🕑 Заполнено из прошлых списков: %d «%s» — размер репертуара по турам: %s",
    "⚠️ No past “%s” lists found — used the whole favorites library instead":
        "⚠️ Прошлых списков «%s» не найдено — вместо этого использована вся избранная библиотека",
    "🎯 %s: %d tracks  (%s)": "🎯 %s: треков %d  (%s)",
    "↺ swaps with a title from the end, drag-drop replaces":
        "↺ меняет местами с треком из конца, перетаскивание заменяет",
    "↺ / drag-drop to replace by timbre":
        "↺ / перетаскивание заменяет по тембру",
    "🤸 %s: %d tracks  (%s)  — %s": "🤸 %s: треков %d  (%s)  — %s",
    "📂 Importing %s…": "📂 Импорт %s…",
    "%d tracks are on the table, %d of them already in an open deck.":
        "Треков на выбор: %d, из них уже в открытом деке: %d.",
    "%d tracks are on the table.": "Треков на выбор: %d.",
    "💾 Saving %s…": "💾 Сохранение %s…",
    "➕  Adding %s tracks…": "➕  Добавление треков: %s…",
    "🐂  PD in": "🐂  PD через",
    "🐂  PD %s in": "🐂  PD %s через",
    "🐂  Paso Doble in %d s": "🐂  Paso Doble через %d с",
    "⚠ Could not play: %s": "⚠ Не удалось воспроизвести: %s",
    "⚠ Playback failed: %s": "⚠ Ошибка воспроизведения: %s",
    "unknown error": "неизвестная ошибка",
    "did not start": "не запустился",
    "⚠ “%s” would not play — skipped to the next title.":
        "⚠ «%s» не воспроизводится — переход к следующему треку.",
    "⚠ Playback stalled — “%s” reloaded at %s.":
        "⚠ Воспроизведение зависло — «%s» перезагружен с %s.",
    "stalled": "завис",
    "Pick up after a crash?":
        "Продолжить после сбоя?",
    "The last session ended while “%s” was playing.\n\nCue it again?":
        "Прошлый сеанс оборвался, когда играло «%s».\n\nПоставить снова?",
    "🔇 would not play: %s": "🔇 не воспроизводится: %s",
    "▴  fold back": "▴  свернуть обратно",
    "⏹  Stop": "⏹  Стоп",
    "Stop the run. A model that is still thinking is cut off and nothing is changed.":
        "Остановить запуск. Модель, которая ещё думает, прерывается, и ничего не меняется.",
    "Waiting for the model…": "Ожидание модели…",
    "Working…": "Работа…",
    "Stopping…": "Остановка…",
    "Check cancelled — drop or ➕ add files to run it again.":
        "Проверка отменена — перетащите файлы или добавьте их через ➕, чтобы запустить её снова.",
    "🧳  Export": "🧳  Экспорт",
    "✅ No gaps — every dance × class pool is healthy":
        "✅ Пробелов нет — каждый репертуар «танец × класс» в порядке",
    "Unfold the library pane": "Развернуть панель библиотеки",
    "📚 Library browser shown": "📚 Обозреватель библиотеки показан",
    "📚 Library browser hidden": "📚 Обозреватель библиотеки скрыт",
    "💾 Saving all playlists…": "💾 Сохранение всех плейлистов…",
    "🧳 Exporting venue bundle…": "🧳 Экспорт пакета для площадки…",
    "💾 Saving tournament-day playlists…":
        "💾 Сохранение плейлистов турнирного дня…",
    "This list is empty.": "Этот список пуст.",
    "This wishlist is empty.": "Этот список пожеланий пуст.",
    "💾 Saving playlist…": "💾 Сохранение плейлиста…",
    "💾 Saving wishlist…": "💾 Сохранение списка пожеланий…",
    "▴ All playlists folded to tabs — click a tab to open one":
        "▴ Все плейлисты свёрнуты во вкладки — щёлкните вкладку, чтобы открыть",
    "▾ All playlists unfolded": "▾ Все плейлисты развёрнуты",
    "Open the library pane back up": "Снова открыть панель библиотеки",
    "Collapse the whole pane —\n"
    "📚 Library and 🏆 Tournaments together":
        "Свернуть всю панель —\n"
        "📚 Библиотеку и 🏆 Турниры вместе",
    "📚 Library pane collapsed — the arrow in the tab bar opens it":
        "📚 Панель библиотеки свёрнута — стрелка в панели вкладок открывает её",
    "📚 Library pane open": "📚 Панель библиотеки открыта",
    "It failed": "Не удалось",
    "Stopped — nothing was changed.": "Остановлено — ничего не изменено.",
    "AI playlist stopped.": "ИИ-плейлист остановлен.",
    "Why these tracks": "Почему эти треки",
    "📅 Planning tournament day…": "📅 Планирование турнирного дня…",
    "Playlist not read": "Плейлист не прочитан",
    "🎵 Checking music…": "🎵 Проверка музыки…",
    "✅  No tempo / length issues in the current tracks.":
        "✅  В текущих треках нет проблем с темпом или длительностью.",
    "No tracks in any open playlist — drag playlists into the 📂 tab to check loose files.":
        "Ни в одном открытом плейлисте нет треков — перетащите плейлисты на вкладку 📂, чтобы проверить отдельные файлы.",
    "Method <span style='color:#b00'>(not used in playlist mode)</span>:":
        "Метод <span style='color:#b00'>(не используется в режиме плейлиста)</span>:",
    "📁 Reading the dropped folder…": "📁 Чтение перетащенной папки…",
    "Drop one or more audio files here, or click to browse":
        "Перетащите сюда один или несколько аудиофайлов или щёлкните для выбора",
    "Empty — switch ✏ Edit on to fill it":
        "Пусто — включите ✏ Правка, чтобы заполнить",
    "Editing ON — drop, drag, recolour and reshape the wall.\n"
    "Switch off before the tournament so nothing moves by accident.":
        "Правка ВКЛ — перетаскивайте, перемещайте, перекрашивайте и перестраивайте стену.\n"
        "Выключите перед турниром, чтобы ничего случайно не сдвинулось.",
    "Locked: pads only fire. Click to edit the wall.":
        "Заблокировано: пэды только играют. Щёлкните, чтобы править стену.",
    "🎛 Cartwall shown": "🎛 Cartwall показана",
    "🎛 Cartwall hidden": "🎛 Cartwall скрыта",
    "✏️ Editing highlights — playback paused; scrub to a crash, ⏯ to listen, 🎯 sets a mark at the playhead.":
        "✏️ Правка кульминаций — воспроизведение на паузе; перемотайте к удару, ⏯ — прослушать, 🎯 ставит метку в позиции воспроизведения.",
    "✔ Highlights armed — playback pauses at the stop once so you can check it.":
        "✔ Кульминации взведены — воспроизведение один раз остановится на метке, чтобы вы её проверили.",
    "🖥 The presenter's screen was disconnected — it opens again when the screen is back.":
        "🖥 Экран ведущего отключён — он откроется снова, когда экран вернётся.",
    "⏹ The next title was removed during the pause — nothing was started.":
        "⏹ Следующий трек удалён во время паузы — ничего не запущено.",
    "✔  Done editing": "✔  Завершить правку",
    "duck": "тише",
    "instrumental (🎙️ Demucs-measured)": "инструментал (🎙️ измерено Demucs)",
    "instrumental (🎙️ audio-detected)":
        "инструментал (🎙️ распознано по звуку)",
    "🎄 Christmas": "🎄 Рождество",
    "Similarity": "Сходство",
    "Match": "Совпадение",
    "Played together": "Играли вместе",
    "Classes: %s": "Классы: %s",
    "In these matching past lists:": "В этих подходящих прошлых списках:",
    "… +%d more": "… ещё +%d",
    "In %d of your playlists": "В ваших плейлистах: %d",
    "Played in: %s": "Играл в: %s",
    "▶ This list is playing: this switch decides what follows the title.":
        "▶ Этот список сейчас играет: этот переключатель решает, что идёт после трека.",
    "in the archive since %s": "в архиве с %s",
    "%s, sounds like %s (%d%%)": "%s, звучит как %s (%d%%)",
    "%s, sounds like %s (%s)": "%s, звучит как %s (%s)",
    "sounds like '%s' of the first heat (%s)":
        "звучит как «%s» из первого захода (%s)",
    "sounds like '%s' of the first heat": "звучит как «%s» из первого захода",
    "timbre top %d %%": "тембр, топ %d %%",
    "groove top %d %%": "грув, топ %d %%",
    "melody top %d %%": "мелодия, топ %d %%",
    "MERT top %d %%": "MERT, топ %d %%",
    "played %d× at the class": "в классе сыгран %d×",
    "never played at the class": "в классе ни разу не играл",
    "a version of %s, played %d× at the class":
        "версия %s — оригинал звучал в классе %d×",
    "a version of %s, never played at the class":
        "версия %s — оригинал ни разу не звучал в классе",
    "Titles to choose from": "Треки на выбор",
    "%d from this event's past years, %d from other events' lists of the class, %d new in the archive, %d rarely played at the class (new ones included)":
        "%d из прошлых лет этого мероприятия, %d из списков класса на других мероприятиях, %d новых в архиве, %d редко игравшихся в классе (включая новые)",
    "🏆  Event — a whole day of competitions, planned from its history":
        "🏆  Мероприятие — целый день турниров, спланированный по его истории",
    "Paste the event's schedule. Every competition gets up to three\n"
    "variants, drawn from the event's earlier editions, the class's\n"
    "lists at other events and titles that sound like those.":
        "Вставьте расписание мероприятия. Каждый турнир получает до трёх\n"
        "вариантов — из прошлых выпусков мероприятия, из списков класса\n"
        "на других мероприятиях и из похожих по звучанию треков.",
    "Paste the event's schedule, one competition per line:\n"
    "\n"
    "Sa: 10:00 HGR S STD 3-2-1\n"
    "So: 14:00 SEN I S STD (24) 2-1\n"
    "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6":
        "Вставьте расписание мероприятия, по одному турниру на строку:\n"
        "\n"
        "Sa: 10:00 HGR S STD 3-2-1\n"
        "So: 14:00 SEN I S STD (24) 2-1\n"
        "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6",
    "Competition": "Турнир",
    "Dances": "Танцы",
    "Heats per round": "Заходов в туре",
    "What was read from the schedule. Double-click a cell to correct\n"
    "it — the class (S, A … D), the dance codes, the heats per round.":
        "Что прочитано из расписания. Двойной щелчок по ячейке, чтобы\n"
        "исправить её — класс (S, A … D), коды танцев, заходы в туре.",
    "Event:": "Мероприятие:",
    "%d editions": "Выпусков: %d",
    "The event whose earlier editions are its history — the folders\n"
    "of that name in the playlist folder, whatever the year.":
        "Мероприятие, прошлые выпуски которого составляют его историю — папки\n"
        "с этим названием в папке плейлистов, за любой год.",
    "Year planned:": "Планируемый год:",
    "Editions of this year and later are not used as history.":
        "Выпуски этого и следующих лет не считаются историей.",
    "Earlier editions of the event": "Прошлые выпуски мероприятия",
    "Lists of the same class from other events":
        "Списки того же класса с других мероприятий",
    "New titles:": "Новые треки:",
    "How much of a variant may be titles that came into the archive in\n"
    "the last 18 months and were never played at the class. \"Like last\n"
    "year\" takes none — it offers them as replacements instead.":
        "Какую долю варианта могут составлять треки, попавшие в архив за\n"
        "последние 18 месяцев и ни разу не игравшиеся в классе. «Как в прошлом\n"
        "году» не берёт ни одного — вместо этого предлагает их как замену.",
    "Rarely played:": "Редко игравшиеся:",
    "How much of a variant may be titles played at most twice at the\n"
    "class so far, new ones included, the ones that sound like the\n"
    "played ones first. \"Like last year\" takes none.":
        "Какую долю варианта могут составлять треки, сыгранные в классе пока\n"
        "не более двух раз, включая новые — сначала те, что звучат как\n"
        "сыгранные. «Как в прошлом году» не берёт ни одного.",
    "Variants:": "Варианты:",
    "Like last year": "Как в прошлом году",
    "Last year, renewed": "Прошлый год, обновлённый",
    "Proven + fresh": "Проверенные + свежие",
    "Variety": "Разнообразие",
    "🤖  Let the AI check the drafts": "🤖  Пусть ИИ проверит черновики",
    "The model reads every draft and proposes swaps; each one is\n"
    "checked against the day before it goes in. Without it the\n"
    "computed plan is shown as it is.":
        "Модель читает каждый черновик и предлагает замены; каждая\n"
        "проверяется по дню, прежде чем войти. Без ИИ рассчитанный\n"
        "план показывается как есть.",
    "Event plan": "План мероприятия",
    "No competition could be read from the schedule. Each line\n"
    "needs a class, a style (STD/LAT) or its dances in brackets,\n"
    "and the heats per round, e.g.  'HGR S STD 3-2-1'.":
        "Из расписания не удалось прочитать ни одного турнира. Каждой строке\n"
        "нужен класс, программа (STD/LAT) или её танцы в скобках,\n"
        "и заходы в туре, напр.  «HGR S STD 3-2-1».",
    "Tick at least one variant to plan.":
        "Отметьте хотя бы один вариант для планирования.",
    "no earlier edition found — the class lists carry the plan":
        "прошлых выпусков не найдено — план держится на списках класса",
    "not used": "не используется",
    "%d competitions. Earlier editions: %s":
        "Турниров: %d. Прошлые выпуски: %s",
    "Asking again about: %s": "Повторный запрос по: %s",
    "Event": "Мероприятие",
    "The plan": "План",
    "🏆 Planning the event…": "🏆 Планирование мероприятия…",
    "🏆 %d competitions planned in %d variants":
        "🏆 Турниров запланировано: %d, вариантов: %d",
    "The AI's limit held back: %s\n"
    "\n"
    "%s\n"
    "\n"
    "Wait and ask again by itself in %d minutes?":
        "Лимит ИИ задержал: %s\n"
        "\n"
        "%s\n"
        "\n"
        "Подождать и спросить снова самостоятельно через %d мин.?",
    "🏆 Asking the AI again at %s": "🏆 ИИ будет спрошен снова в %s",
    "1 swap not applied, kept for your choice":
        "1 замена не применена, оставлена на ваш выбор",
    "%d swaps not applied, kept for your choice":
        "Замен не применено: %d, оставлены на ваш выбор",
    "the AI could not check it — the plan stands":
        "ИИ не смог проверить — план остаётся",
    "held back by the AI's limit — ask again later":
        "задержано лимитом ИИ — спросите позже",
    "🏆 Event plan": "🏆 План мероприятия",
    "🟦 This event's lists": "🟦 Списки этого мероприятия",
    "🟩 The class lists": "🟩 Списки класса",
    "🟨 New titles": "🟨 Новые треки",
    "🟧 Rarely played": "🟧 Редко игравшиеся",
    "⬜ Library": "⬜ Библиотека",
    "AI: %s": "ИИ: %s",
    "↺ Replaces '%s' of last year — %s": "↺ Заменяет «%s» прошлого года — %s",
    "↻ Suggested instead: %s — %s": "↻ Предложено вместо: %s — %s",
    "✋ The AI wanted '%s': %s": "✋ ИИ хотел «%s»: %s",
    "⏳ Ask about the held back now": "⏳ Спросить о задержанном сейчас",
    "🔁 Second round": "🔁 Второй круг",
    "Ask the AI again where a swap was lost, to fill or improve those slots.":
        "Снова спросить ИИ там, где замена потерялась, чтобы заполнить или улучшить эти места.",
    "Variant:": "Вариант:",
    "The earlier editions had no list of this competition — 'like similar competitions' fills it from the class lists 🟩":
        "В прошлых выпусках не было списка этого турнира — «Как похожие турниры» заполняет его из списков класса 🟩",
    "Like similar competitions": "Как похожие турниры",
    "The variant of the competition in front — each tab keeps its own, ✔ in its header; a click on a column header chooses it too":
        "Вариант турнира на переднем плане — каждая вкладка хранит свой, ✔ в её заголовке; щелчок по заголовку столбца тоже выбирает его",
    "Drag a title onto the same dance in another variant to take it over there, within its variant to swap the two":
        "Перетащите трек на тот же танец в другом варианте, чтобы перенести его туда, или внутри его варианта, чтобы поменять два местами",
    "'%s' ⇄ '%s': %s.\n"
    "\n"
    "Swap anyway?":
        "«%s» ⇄ «%s»: %s.\n"
        "\n"
        "Всё равно поменять?",
    "▶ A title's ▶ or Space plays it, again stops it; Ctrl+click in the menu one to choose from":
        "▶ Кнопка ▶ трека или Пробел запускает его, повторно — останавливает; Ctrl+щелчок в меню — выбрать один",
    "📅 Into the tournament-day decks": "📅 В деки турнирного дня",
    "🏆  Open the last plan": "🏆  Открыть последний план",
    "Show the last event plan side by side again, as you left it —\n"
    "nothing is planned or asked anew.":
        "Снова показывает последний план мероприятия рядом, как вы его оставили —\n"
        "ничего не планируется и не спрашивается заново.",
    "⏳ Held back by the AI's limit: %s": "⏳ Задержано лимитом ИИ: %s",
    "⚠ The AI could not check: %s — the plan stands":
        "⚠ ИИ не смог проверить: %s — план остаётся",
    "🔁 A swap was lost at: %s — a second round can fill or improve those slots":
        "🔁 Замена потерялась в: %s — второй круг может заполнить или улучшить эти места",
    "Double-click or right-click a title for what else fits there.  🟦 event  🟩 class lists  🟨 new  🟧 rarely played  ⬜ library  ↺ replaces last year's title  ↻ a replacement is offered  ✋ the AI wanted another":
        "Двойной или правый щелчок по треку показывает, что ещё подходит туда.  🟦 мероприятие  🟩 списки класса  🟨 новый  🟧 редко игравшийся  ⬜ библиотека  ↺ заменяет трек прошлого года  ↻ предлагается замена  ✋ ИИ хотел другой",
    "'Last year, renewed' found no sound-alike to swap here — the same as 'Like last year'":
        "«Прошлый год, обновлённый» не нашёл здесь похожего по звучанию для замены — то же, что «Как в прошлом году»",
    "↺ Back to last year: %s": "↺ Вернуть прошлый год: %s",
    "↻ Take the suggestion: %s": "↻ Принять предложение: %s",
    "✋ The AI wanted: %s (%s)": "✋ ИИ хотел: %s (%s)",
    "'%s' %s.\n"
    "\n"
    "Put it in anyway?":
        "«%s» %s.\n"
        "\n"
        "Всё равно поставить?",
    "🏆  %s: %d competitions into %d deck(s)": "🏆  %s: турниров: %d, деков: %d",
    "already plays that day": "уже играет в этот день",
    "already plays in that round": "уже играет в этом туре",
    "is offered for another slot": "предложен для другого места",
    "too many swaps": "слишком много замен",
    "that slot is swapped already": "это место уже заменено",
    "📦 Venue pack": "📦 Пакет площадки",
    "Take this desk to another PC in one file: the settings, every deck "
    "and wishlist, the 🎛 cartwall with its pads and keys — and, if you "
    "want, the music they use. Folder settings stay with each PC.":
        "Перенести этот пульт на другой ПК в одном файле: настройки, все деки "
        "и списки пожеланий, 🎛 Cartwall с пэдами и клавишами — и, по желанию, "
        "музыку, которую они используют. Настройки папок остаются на каждом ПК.",
    "📦  Export venue pack…": "📦  Экспорт пакета площадки…",
    "📥  Import venue pack…": "📥  Импорт пакета площадки…",
    "Save this desk to one file to take to another PC: the settings,\n"
    "every deck and wishlist, the 🎛 cartwall with its pads and keys —\n"
    "and, if you want, the music they use. Folder settings stay with\n"
    "each PC.":
        "Сохранить этот пульт в один файл, чтобы перенести на другой ПК:\n"
        "настройки, все деки и списки пожеланий, 🎛 Cartwall с пэдами и клавишами —\n"
        "и, по желанию, музыку, которую они используют. Настройки папок\n"
        "остаются на каждом ПК.",
    "Load a venue pack made on another PC. It replaces this PC's\n"
    "settings, decks and cartwall at the next start; what it replaces\n"
    "is kept in a before-venue-import folder next to them.":
        "Загрузить пакет площадки, созданный на другом ПК. При следующем запуске\n"
        "он заменит настройки, деки и Cartwall этого ПК; заменённое\n"
        "сохраняется рядом в папке before-venue-import.",
    "Export venue pack": "Экспорт пакета площадки",
    "Import venue pack": "Импорт пакета площадки",
    "Include the music files?\n"
    "\n"
    "Yes: the %d track(s) the decks and the cartwall use go into the pack too (%s MB) — the other PC needs nothing else.\n"
    "No: settings, decks and cartwall only — the other PC has the music already.":
        "Включить музыкальные файлы?\n"
        "\n"
        "Да: треки, которые используют деки и Cartwall (%d), тоже идут в пакет (%s МБ) — другому ПК больше ничего не нужно.\n"
        "Нет: только настройки, деки и Cartwall — на другом ПК музыка уже есть.",
    "Venue packs": "Пакеты площадки",
    "📦 Writing the venue pack…": "📦 Запись пакета площадки…",
    "📥 Unpacking the venue pack…": "📥 Распаковка пакета площадки…",
    "All files": "Все файлы",
    "📦 Venue pack cancelled — nothing was written.":
        "📦 Пакет площадки отменён — ничего не записано.",
    "📦 Venue pack saved to:\n"
    "%s":
        "📦 Пакет площадки сохранён в:\n"
        "%s",
    "%d track(s) included.": "Включено треков: %d.",
    "⚠ %d track(s) were missing on disk and are not in the pack.":
        "⚠ Треков нет на диске, и они не вошли в пакет: %d.",
    "This is no venue pack:": "Это не пакет площадки:",
    "The pack carries %d music file(s).\n"
    "\n"
    "Yes: unpack them into a folder of this PC — the decks and the cartwall then play them from there.\n"
    "No: leave them in the pack — this PC has the music already (🧭 Fix paths finds it if it lives elsewhere).":
        "В пакете музыкальных файлов: %d.\n"
        "\n"
        "Да: распаковать их в папку этого ПК — деки и Cartwall будут играть их оттуда.\n"
        "Нет: оставить в пакете — на этом ПК музыка уже есть (🧭 Исправить пути найдёт её, если она лежит в другом месте).",
    "Folder for the venue pack's music": "Папка для музыки пакета площадки",
    "📥 Venue pack import cancelled.": "📥 Импорт пакета площадки отменён.",
    "The import did not run:": "Импорт не выполнен:",
    "The venue pack takes over at the next start: settings, decks and cartwall are replaced then, and what they replace is kept in a before-venue-import folder.\n"
    "\n"
    "Anything you change before that is lost.\n"
    "\n"
    "Restart now?":
        "Пакет площадки вступит в силу при следующем запуске: тогда настройки, деки и Cartwall будут заменены, а заменённое сохранится в папке before-venue-import.\n"
        "\n"
        "Всё, что вы измените до этого, будет потеряно.\n"
        "\n"
        "Перезапустить сейчас?",
    "Play, skip, fade and fire pads from a phone's browser on this network — no app to install. The server's window shows the address, a QR code that logs the phone in, and the PIN.":
        "Воспроизведение, пропуск, затухание и пэды из браузера телефона в этой сети — без установки приложения. Окно сервера показывает адрес, QR-код, который входит с телефона, и PIN.",
    "📱  Start Server": "📱  Запустить сервер",
    "📱  Stop Server": "📱  Остановить сервер",
    "Stops the phone remote's server — connected phones lose the remote.":
        "Останавливает сервер пульта с телефона — подключённые телефоны теряют пульт.",
    "The phone remote's server is running — click for its window.":
        "Сервер пульта с телефона работает — щёлкните, чтобы открыть его окно.",
    "The hardware controller is connected — click for its window.":
        "Аппаратный контроллер подключён — щёлкните, чтобы открыть его окно.",
    "Starts the server and opens its window — stop it there again.\n"
    "\n"
    "Only phones on the same network get in, and only with the PIN;\n"
    "wrong PINs lock the phone out for a while.\n"
    "Windows may ask once whether the app may use the network —\n"
    "allow it for private networks.":
        "Запускает сервер и открывает его окно — там же его и останавливают.\n"
        "\n"
        "Войти могут только телефоны в той же сети и только с PIN;\n"
        "неверные PIN на время блокируют телефон.\n"
        "Windows может один раз спросить, можно ли приложению использовать сеть —\n"
        "разрешите для частных сетей.",
    "New PIN": "Новый PIN",
    "Make up a new PIN — phones that know the old one have to enter it again.":
        "Придумать новый PIN — телефонам, знающим старый, придётся ввести его заново.",
    "📱 Remote":
        "📱 Пульт",
    "📱 The phone remote could not start: %s":
        "📱 Пульт с телефона не удалось запустить: %s",
    "📱 Phone remote on — open %s on the phone, PIN %s":
        "📱 Пульт с телефона включён — откройте %s на телефоне, PIN %s",
    "📱  Phone remote": "📱  Пульт с телефона",
    "📱  Phone remote…": "📱  Пульт с телефона…",
    "Play, skip, fade and fire pads from a phone's browser on this\n"
    "network — no app to install. Opens the window to start the\n"
    "server, with a QR code that logs the phone in and a log of what\n"
    "reached it.":
        "Воспроизведение, пропуск, затухание и пэды из браузера телефона в этой\n"
        "сети — без установки приложения. Открывает окно, которое запускает сервер,\n"
        "с QR-кодом, который входит с телефона, и журналом того, что пришло.",
    "Scan the code with the phone's camera — it opens the remote, logged in. Or type the address:":
        "Отсканируйте код камерой телефона — он откроет пульт, уже с входом. Или введите адрес:",
    "This PC is on more than one network. The first one is the way to\n"
    "the internet, usually the Wi-Fi the phone is on as well.":
        "Этот ПК подключён к нескольким сетям. Первая — путь в\n"
        "интернет, обычно тот же Wi-Fi, в котором и телефон.",
    "Opens the remote in this PC's browser — a quick test that the server answers.":
        "Открывает пульт в браузере этого ПК — быстрая проверка, что сервер отвечает.",
    "Nothing turns up in the log when the phone tries? Then a firewall on this PC drops it: allow the program below for private networks (Windows Defender Firewall, or your security suite's own, e.g. Norton → Firewall → Program Control). The phone must be on the same Wi-Fi.%s":
        "В журнале ничего не появляется, когда телефон пытается подключиться? Значит, брандмауэр на этом ПК отбрасывает запрос: разрешите программу ниже для частных сетей (брандмауэр Защитника Windows или брандмауэр вашего пакета безопасности, напр. Norton → Брандмауэр → Управление программами). Телефон должен быть в том же Wi-Fi.%s",
    "Log": "Журнал",
    "● Running — port %d": "● Работает — порт %d",
    "○ Stopped": "○ Остановлен",
    "■  Stop": "■  Остановить",
    "▶  Start": "▶  Запустить",
    "No network found — is this PC on the Wi-Fi?":
        "Сеть не найдена — подключён ли этот ПК к Wi-Fi?",
    "Press Start — the code to scan shows up here.":
        "Нажмите «Запустить» — здесь появится код для сканирования.",
    "Connecting… the code to scan shows up as soon as guests can reach the page.":
        "Подключение… код для сканирования появится, как только гости смогут открыть страницу.",
    "No QR code: the segno package is missing. Type the address instead.":
        "Нет QR-кода: отсутствует пакет segno. Введите адрес вручную.",
    "▶ Server started on port %(detail)s":
        "▶ Сервер запущен на порту %(detail)s",
    "■ Server stopped": "■ Сервер остановлен",
    "%(ip)s opened the page": "%(ip)s открыл страницу",
    "✔ %(ip)s logged in with the PIN": "✔ %(ip)s вошёл с PIN",
    "✖ %(ip)s sent a wrong PIN": "✖ %(ip)s отправил неверный PIN",
    "⛔ %(ip)s locked out for %(detail)s s — too many wrong PINs":
        "⛔ %(ip)s заблокирован на %(detail)s с — слишком много неверных PIN",
    "⛔ New phones paused for %(detail)s s — too many wrong PINs from the network":
        "⛔ Новые телефоны приостановлены на %(detail)s с — слишком много неверных PIN из сети",
    "⛔ %(ip)s refused — not on the local network":
        "⛔ %(ip)s отклонён — не в локальной сети",
    "⚠ Could not start: %(detail)s": "⚠ Не удалось запустить: %(detail)s",
    "DanceSport Player remote": "Пульт DanceSport Player",
    "Connect": "Подключиться",
    "Wrong PIN": "Неверный PIN",
    "Too many wrong PINs — wait a minute":
        "Слишком много неверных PIN — подождите минуту",
    "No connection to the desk": "Нет связи с пультом",
    "Nothing is playing": "Ничего не играет",
    "Play \"%s\" now? The playing title fades out.":
        "Включить «%s» сейчас? Текущий трек затихнет.",
    "Stop all pads": "Остановить все пэды",
    "Next": "Далее",
    "Fade & hold": "Затухание и удержание",
    "Announce next dance": "Объявлять следующий танец",
    "Crossfade": "Кроссфейд",
    "Manual": "Вручную",
    "Menus, buttons and dialogs are in Spanish. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Меню, кнопки и диалоги на испанском. Танцы и туры сохраняют международные английские названия; названия треков и всё, что читается из ваших файлов, остаются как есть.",
    "Menus, buttons and dialogs are in Dutch. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Меню, кнопки и диалоги на нидерландском. Танцы и туры сохраняют международные английские названия; названия треков и всё, что читается из ваших файлов, остаются как есть.",
    "Menus, buttons and dialogs are in Russian. Dances and rounds keep their international English names; track names and anything read from your files stay as they are.":
        "Меню, кнопки и диалоги на русском. Танцы и туры сохраняют международные английские названия; названия треков и всё, что читается из ваших файлов, остаются как есть.",
    '🎛  Controller':
        '🎛  Контроллер',
    'Play, skip, fade, set the volume and fire cartwall pads from a USB MIDI controller (e.g. Korg nanoKONTROL2) or a HID one (e.g. a Traktor controller in its native mode). Pick the device, load a profile or click Learn and press the button that should do it.':
        'Воспроизведение, пропуск, затухание, громкость и пэды cartwall с USB-MIDI-контроллера (например, Korg nanoKONTROL2) или HID-контроллера (например, Traktor в родном режиме). Выберите устройство, загрузите профиль или нажмите «Обучить» и затем кнопку, которая должна это делать.',
    '— none —':
        '— нет —',
    'Device:':
        'Устройство:',
    'Look for devices again':
        'Искать устройства снова',
    'Show all HID devices, not only DJ controllers':
        'Показывать все HID-устройства, а не только DJ-контроллеры',
    'Presets ▾':
        'Пресеты ▾',
    '📂  Load profile…':
        '📂  Загрузить профиль…',
    '💾  Save profile…':
        '💾  Сохранить профиль…',
    'Control':
        'Элемент',
    'Learn':
        'Обучить',
    'Unbind this action':
        'Снять назначение',
    '%s — not plugged in':
        '%s — не подключено',
    '● Connected — %s':
        '● Подключено — %s',
    '○ Not connected — %s':
        '○ Не подключено — %s',
    'No controller chosen.':
        'Контроллер не выбран.',
    'Profile: %s':
        'Профиль: %s',
    'own':
        'своё',
    'Press or move a control…':
        'Нажмите или сдвиньте элемент…',
    'on the fader — %s':
        'фейдером — %s',
    'Load controller profile':
        'Загрузить профиль контроллера',
    'Controller profiles (*.json)':
        'Профили контроллера (*.json)',
    'This file is not a controller profile:\n%s':
        'Этот файл не является профилем контроллера:\n%s',
    'Save controller profile':
        'Сохранить профиль контроллера',
    'Could not save the profile:\n%s':
        'Не удалось сохранить профиль:\n%s',
    'not bound':
        'не назначено',
    'Last: %(control)s = %(value)d%% → %(action)s':
        'Последнее: %(control)s = %(value)d%% → %(action)s',
    '🎛  Cartwall pad %d':
        '🎛  Пэд cartwall %d',
    '⏯  Play / pause':
        '⏯  Воспроизведение / пауза',
    '⏭  Next title':
        '⏭  Следующий трек',
    '⏮  Previous title':
        '⏮  Предыдущий трек',
    '🔉↓  Fade out now':
        '🔉↓  Затухание сейчас',
    '🛑  Fade out and hold':
        '🛑  Затухание и стоп',
    '🔉  Duck the music on / off':
        '🔉  Приглушить музыку вкл / выкл',
    '🔈  Announce the next dance on / off':
        '🔈  Объявлять следующий танец вкл / выкл',
    '🔊  Music volume (fader or knob)':
        '🔊  Громкость музыки (фейдер или регулятор)',
    '⏹  Stop all pads':
        '⏹  Остановить все пэды',
    'Play, skip, fade, set the volume and fire cartwall pads from a USB MIDI or HID controller — a profile for the Korg nanoKONTROL2 is built in, any other is learned by pressing its buttons.':
        'Воспроизведение, пропуск, затухание, громкость и пэды cartwall с USB-MIDI- или HID-контроллера — профиль для Korg nanoKONTROL2 встроен, любой другой обучается нажатием его кнопок.',
    '🎛  Set up…':
        '🎛  Настроить…',
    # 🤸 the practice panel's own name
    "Practice": "Практика",
    "Practice / Party": "Практика / Пати",
    "🤸  Practice / Party": "🤸  Практика / Пати",
    "🤸  Practice / Party ▾": "🤸  Практика / Пати ▾",
    "Tempo from the file name": "Темп из имени файла",
    "Tempo from the BPM tag (%s bpm)": "Темп из тега BPM (%s bpm)",
    "Tempo from the title tag": "Темп из тега названия",
    "🔈  Sound outputs":
        "🔈  Аудиовыходы",
    "%s %s is not connected — it plays on the system default.":
        "%s %s не подключён — звук идёт на системное устройство по умолчанию.",
    "🎧 Pre-listen is on the music's own output — every preview is refused.":
        "🎧 Предпрослушивание на выходе музыки — каждое предпрослушивание отклоняется.",
    "🎧 Pre-listen is on the same output as the music — the hall hears every preview.":
        "🎧 Предпрослушивание на том же выходе, что и музыка — зал слышит каждое предпрослушивание.",
    "Every chosen output is plugged in.":
        "Каждый выбранный выход подключён.",
    "%s is connected.":
        "%s подключён.",
    "%s is not connected — plug it in if tonight needs it.":
        "%s не подключён — подключите, если он нужен сегодня.",
    "☀  Screen and sleep":
        "☀  Экран и сон",
    "While music plays or the presenter screen is up, the screen, the beamer and the computer stay awake.":
        "Пока играет музыка или открыт экран ведущего, экран, проектор и компьютер не засыпают.",
    "☀ Keep the screen awake is off — an hour nobody touches the desk blanks the screen and the beamer, and may put the computer to sleep.":
        "☀ «Не гасить экран» выключено — час без касания пульта гасит экран и проектор и может усыпить компьютер.",
    "🔴  Not ready — a sound output is not connected.":
        "🔴  Не готово — аудиовыход не подключён.",
    "⚙  Choose outputs…":
        "⚙  Выбрать выходы…",
    "🎛  Open the controller…":
        "🎛  Открыть контроллер…",
    "☀  Keep it awake":
        "☀  Не давать уснуть",
    "🔀  Crossfade:":
        "🔀  Кроссфейд:",
    "crossfade → %s s":
        "кроссфейд → %s с",
    "crossfade → off":
        "кроссфейд → выкл.",
    "🔀 The last %s s of a title and the first %s s of the next play together:\nred the one going out, green the one coming in.":
        "🔀 Последние %s с трека и первые %s с следующего звучат вместе:\nкрасный — уходящий, зелёный — входящий.",
    "🔀 No crossfade: one title ends, then the next starts.":
        "🔀 Без кроссфейда: один трек кончается, затем начинается следующий.",
    "The next title comes in under the end of the\nlast one — only where the list walks on with\nno pause. Off: one ends, the next starts.":
        "Следующий трек входит под конец предыдущего —\nтолько там, где список идёт дальше без паузы.\nВыкл.: один кончается, следующий начинается.",
    "The last seconds of a title and the first of the next play\ntogether: the old one fades out while the new one fades in,\nso the floor never hears a gap. Only where the list walks on\nby itself with no pause — a heat keeps its gap. Not after a\n🏁 round, a 🔁 title or a 🐂 Paso Doble run to its highlight.\n\nOff: one title ends, then the next starts. Every playlist\nkeeps its own answer.":
        "Последние секунды трека и первые секунды следующего\nзвучат вместе: старый затухает, пока новый нарастает,\nи паркет не слышит паузы. Только там, где список сам идёт\nдальше без паузы — заход на турнире сохраняет свою паузу.\nНе после 🏁 раунда, 🔁 трека или 🐂 Пасодобля до кульминации.\n\nВыкл.: один трек кончается, затем начинается следующий.\nКаждый плейлист хранит свой ответ.",
    "How long the two titles play together — half-second steps":
        "Как долго два трека звучат вместе — шаг полсекунды",
    "crossfade curve → %s":
        "кривая кроссфейда → %s",
    "equal power":
        "равная мощность",
    "linear":
        "линейная",
    "S-curve":
        "S-кривая",
    "🔀 Equal power: the two titles add up to one steady level\nall the way across — right for two unrelated songs.":
        "🔀 Равная мощность: два трека вместе дают ровный уровень\nна всём переходе — то, что нужно для двух разных песен.",
    "🔀 Linear: two straight lines, the way a plain mixer fader\ndoes it — a little quieter in the middle.":
        "🔀 Линейная: две прямые линии, как у простого фейдера микшера —\nв середине немного тише.",
    "🔀 S-curve: steady like equal power, but slow off both ends —\nthe new title is barely there at first, the old one lingers.":
        "🔀 S-кривая: ровно, как равная мощность, но медленно на обоих концах —\nновый трек сначала едва слышен, старый ещё звучит.",
    # ── 📨 Guest requests ──
    "📨  Guest requests":
        "📨  Заявки гостей",
    "📨  Guest requests…":
        "📨  Заявки гостей…",
    "Guests search the library on their phones and ask for a title, or\nleave a few words — it lands in an inbox, and you put it on the\nwishlist or dismiss it. Nothing a guest sends is played on its own.":
        "Гости ищут в библиотеке на телефоне и заказывают трек или\nпишут пару слов — всё попадает во входящие, а вы ставите это в\nсписок пожеланий или отклоняете. Ничего от гостей не играет само.",
    "Guests scan the code with their phone's camera — it opens the request page. Or show them the address:":
        "Гости сканируют код камерой телефона — он открывает страницу заявок. Или покажите им адрес:",
    "This PC is on more than one network. The first one is the way to\nthe internet, usually the Wi-Fi the guests are on as well.":
        "Этот ПК подключён к нескольким сетям. Первая — выход в\nинтернет, обычно тот же Wi-Fi, в котором и гости.",
    "Opens the request page in this PC's browser — a quick test that the server answers.":
        "Открывает страницу заявок в браузере этого ПК — быстрая проверка, что сервер отвечает.",
    "New code":
        "Новый код",
    "Make up a new event code — older links and photos of the QR code stop working.":
        "Придумать новый код события — старые ссылки и фото QR-кода перестанут работать.",
    "⭐  To wishlist":
        "⭐  В список пожеланий",
    "Put the requested title on the first ⭐ wishlist.":
        "Поставить заказанный трек в первый ⭐ список пожеланий.",
    "✕  Dismiss":
        "✕  Отклонить",
    "Take the request out of the inbox.":
        "Убрать заявку из входящих.",
    "Inbox":
        "Входящие",
    "○ Closed":
        "○ Закрыто",
    "● Open — port %d":
        "● Открыто — порт %d",
    "Event code: %s":
        "Код события: %s",
    "▶ Guest requests open on port %(detail)s":
        "▶ Заявки гостей открыты на порту %(detail)s",
    "■ Guest requests closed":
        "■ Заявки гостей закрыты",
    "📨 %(ip)s asks for %(detail)s":
        "📨 %(ip)s заказывает %(detail)s",
    "📨 %(ip)s wishes: %(detail)s":
        "📨 %(ip)s пишет: %(detail)s",
    "✖ %(ip)s came with an old code":
        "✖ %(ip)s пришёл со старым кодом",
    "⛔ %(ip)s sent too many requests":
        "⛔ %(ip)s отправил слишком много заявок",
    "Guest requests — click for the inbox.":
        "Заявки гостей — щёлкните, чтобы открыть входящие.",
    "⭐ On the wishlist: %s":
        "⭐ В списке пожеланий: %s",
    "⭐ Already on the wishlist: %s":
        "⭐ Уже в списке пожеланий: %s",
    "📨 Guest request: %s": "📨 Заявка гостя: %s",
    "📨 Guest wish: %s": "📨 Пожелание гостя: %s",
    "📨 Guest requests could not start: %s":
        "📨 Не удалось запустить заявки гостей: %s",
    "Song requests":
        "Заказ песен",
    "Now playing":
        "Сейчас играет",
    "Request a song":
        "Заказать песню",
    "Up next":
        "Далее",
    "Nothing lined up yet":
        "Пока ничего не запланировано",
    "Search a title or artist":
        "Поиск по названию или исполнителю",
    "Loading the titles…":
        "Загрузка треков…",
    "No matching title — write it as a wish below":
        "Подходящего трека нет — напишите его ниже как пожелание",
    "Request":
        "Заказать",
    "Not in the list? Write your wish:":
        "Нет в списке? Напишите пожелание:",
    "Send":
        "Отправить",
    "Thank you — the DJ has your request":
        "Спасибо — диджей получил вашу заявку",
    "That was a lot of requests — please wait a few minutes":
        "Слишком много заявок — подождите несколько минут",
    "Requests are closed right now":
        "Сейчас заявки не принимаются",
    "This link is out of date — scan the current QR code":
        "Эта ссылка устарела — отсканируйте текущий QR-код",
    "No connection to the DJ — try again in a moment":
        "Нет связи с диджеем — попробуйте ещё раз чуть позже",
    "Guests must be on the same Wi-Fi as this PC — or on its hotspot.":
        "Гости должны быть в той же сети Wi-Fi, что и этот ПК, — или в его точке доступа.",
    "Nothing turns up in the log when a phone on the Wi-Fi tries? Then a firewall on this PC drops it: allow the program below for private networks.%s":
        "В журнале ничего не появляется, когда пробует телефон из Wi-Fi? Значит, брандмауэр этого ПК блокирует его: разрешите программу ниже для частных сетей.%s",
    "The https address works on mobile data too, and on any Wi-Fi. It is new on every start — show the fresh QR code.":
        "Адрес https работает и через мобильный интернет, и в любой сети Wi-Fi. При каждом запуске он новый — показывайте свежий QR-код.",
    "Guests reach the page:":
        "Гости открывают страницу:",
    "Wi-Fi only":
        "Только Wi-Fi",
    "Wi-Fi and mobile data (Cloudflare tunnel)":
        "Wi-Fi и мобильный интернет (туннель Cloudflare)",
    "Wi-Fi only: guests must be on the same Wi-Fi as this PC, or on its hotspot.\nCloudflare tunnel: a public https address leads to this PC as well —\nno account and no router setup; it changes with every start.\nNeeds the free cloudflared program (asked for on the first start).":
        "Только Wi-Fi: гости должны быть в той же сети Wi-Fi, что и этот ПК, или в его точке доступа.\nТуннель Cloudflare: публичный адрес https тоже ведёт к этому ПК —\nбез учётной записи и без настройки роутера; он меняется при каждом запуске.\nНужна бесплатная программа cloudflared (спросим при первом запуске).",
    "The tunnel needs Cloudflare's free cloudflared program (about 55 MB). Download it now from Cloudflare's releases on GitHub?\n\nIt goes to: %s":
        "Туннелю нужна бесплатная программа Cloudflare cloudflared (около 55 МБ). Скачать её сейчас со страницы релизов Cloudflare на GitHub?\n\nОна будет в: %s",
    "Then download cloudflared yourself from\n%s\nand put it next to the program, as %s in:\n%s\n\nUntil then choose Wi-Fi only.":
        "Тогда скачайте cloudflared сами отсюда:\n%s\nи положите рядом с программой, как %s в:\n%s\n\nА пока выберите «Только Wi-Fi».",
    "Downloading cloudflared…":
        "Загрузка cloudflared…",
    "Download it yourself instead from <a href=\"%s\">Cloudflare's releases on GitHub</a>:":
        "Скачайте его сами с <a href=\"%s\">релизов Cloudflare на GitHub</a>:",
    "Take <b>%s</b>, double-click it to unpack it, and put the <b>cloudflared</b> inside into:":
        "Возьмите <b>%s</b>, распакуйте двойным щелчком и положите <b>cloudflared</b> из архива в:",
    "Take <b>%s</b> and save it as <b>%s</b> in:":
        "Возьмите <b>%s</b> и сохраните как <b>%s</b> в:",
    "Then make it runnable: <code>chmod +x %s</code>":
        "Затем сделайте его исполняемым: <code>chmod +x %s</code>",
    "Or, with Homebrew: <code>brew install cloudflared</code>":
        "Или через Homebrew: <code>brew install cloudflared</code>",
    "Then start again. Until then choose Wi-Fi only.":
        "Затем запустите снова. А пока выберите «Только Wi-Fi».",
    "The download failed: %s":
        "Загрузка не удалась: %s",
    "● Open — port %d, waiting for Cloudflare…":
        "● Открыто — порт %d, ждём Cloudflare…",
    "🌐 Connecting to Cloudflare…":
        "🌐 Подключение к Cloudflare…",
    "🌐 Public address: %(detail)s":
        "🌐 Публичный адрес: %(detail)s",
    "⚠ The tunnel ended (exit code %(detail)s) — guests on mobile data are cut off":
        "⚠ Туннель завершился (код выхода %(detail)s) — гости с мобильным интернетом отрезаны",
    "⚠ cloudflared not found — guests reach the page on the Wi-Fi only":
        "⚠ cloudflared не найден — гости откроют страницу только через Wi-Fi",
    "⚠ The tunnel could not start: %(detail)s":
        "⚠ Не удалось запустить туннель: %(detail)s",
    "The phone reaches the desk:":
        "Телефон подключается к пульту:",
    "Wi-Fi only: the phone must be on the same Wi-Fi as this PC, or on its hotspot.\nCloudflare tunnel: a public https address leads to this PC as well —\nno account and no router setup; it changes with every start, and\nthe PIN grows to 8 digits. Needs the free cloudflared program.":
        "Только Wi-Fi: телефон должен быть в той же сети Wi-Fi, что и этот ПК, или в его точке доступа.\nТуннель Cloudflare: публичный адрес https тоже ведёт к этому ПК —\nбез учётной записи и без настройки роутера; он меняется при каждом запуске, а\nPIN становится 8-значным. Нужна бесплатная программа cloudflared.",
    "The https address works on mobile data too, and on any Wi-Fi. It is new on every start — scan the fresh QR code. Whoever has the address still needs the PIN.":
        "Адрес https работает и через мобильный интернет, и в любой сети Wi-Fi. При каждом запуске он новый — отсканируйте свежий QR-код. Тому, у кого есть адрес, всё равно нужен PIN.",
    "● Running — port %d, waiting for Cloudflare…":
        "● Работает — порт %d, ожидание Cloudflare…",
    "Connecting… the code to scan shows up as soon as the phone can reach the desk.":
        "Подключение… код для сканирования появится, как только телефон сможет связаться с пультом.",
    "⚠ The tunnel ended (exit code %(detail)s) — the phone reaches the desk on the Wi-Fi only":
        "⚠ Туннель завершён (код выхода %(detail)s) — телефон подключается к пульту только по Wi-Fi",
    "⚠ cloudflared not found — the phone reaches the desk on the Wi-Fi only":
        "⚠ cloudflared не найден — телефон подключается к пульту только по Wi-Fi",
    "Song request? Scan here":
        "Заказать песню? Сканируйте",
    "🖥  Show the QR code on the presenter screen":
        "🖥  Показывать QR-код на экране ведущего",
    "While guest requests are open, the presenter screen shows the code in\nits corner — guests scan it from the floor.":
        "Пока приём заявок открыт, экран ведущего показывает код\nв углу — гости сканируют его с танцпола.",
    "refused":
        "отклонено",
    "Music folder":
        "Папка с музыкой",
    "Where is your dance music?":
        "Где лежит ваша танцевальная музыка?",
    "Use this folder":
        "Использовать эту папку",
    "Choose another folder…":
        "Выбрать другую папку…",
    "Every start reads the MP3 files in this folder and in all\n"
    "folders below it. The first start reads each file once,\n"
    "which takes long on a whole drive or an external disk,\n"
    "so pick the folder that holds your dance music.\n\n"
    "Found: %s\n\n"
    "You can change it at any time under ⚙ Settings → 📁 Paths.":
        "При каждом запуске читаются MP3-файлы в этой папке и во всех\n"
        "вложенных папках. Первый запуск читает каждый файл один раз,\n"
        "что долго на целом диске или внешнем диске,\n"
        "поэтому выберите папку с вашей танцевальной музыкой.\n\n"
        "Найдено: %s\n\n"
        "Изменить это можно в любой момент в ⚙ Настройки → 📁 Пути.",
    "Name the folder for the bundle on “%s”:":
        "Имя папки для пакета на «%s»:",
    "Make a folder named after the tournament in “%s”?":
        "Создать в «%s» папку с названием турнира?",
    "📁  Create folder":
        "📁  Создать папку",
    "Straight into “%s”":
        "Прямо в «%s»",
    "📦 Venue pack: this desk for another PC…":
        "📦 Пакет площадки: этот пульт для другого ПК…",
    "⭐ Include wishlists (%d)":
        "⭐ Включить списки пожеланий (%d)",
    "Each ⭐ wishlist with titles in it gets its own numbered\n"
    "folder in the bundle, beside the playlists.":
        "Каждый ⭐ список пожеланий с треками получает в пакете свою\n"
        "пронумерованную папку рядом с плейлистами.",
    "One file with the settings, every deck and wishlist and the\n"
    "cartwall, the music they use if you want: the same as\n"
    "⚙ Settings → 📦 Venue pack → Export venue pack….":
        "Один файл с настройками, всеми деками и списками пожеланий и\n"
        "Cartwall, по желанию с музыкой, которую они используют: то же, что\n"
        "⚙ Настройки → 📦 Пакет площадки → Экспорт пакета площадки….",
    "📚 Listing the library folder…":
        "📚 Чтение папки с музыкой…",
    "📚 Library: %s / %s files":
        "📚 Библиотека: %s / %s файлов",
    "📚 The library is still loading — this works once it is done.":
        "📚 Библиотека ещё загружается — это заработает, когда она будет готова.",
    "🎯  Focus playlist 1":
        "🎯  Фокус на плейлист 1",
    "🎯  Focus playlist 2":
        "🎯  Фокус на плейлист 2",
    "🎯  Focus playlist 3":
        "🎯  Фокус на плейлист 3",
    "🎯  Focus playlist 4":
        "🎯  Фокус на плейлист 4",
    "🎯  Focus playlist 5":
        "🎯  Фокус на плейлист 5",
    "🎯  Focus playlist 6":
        "🎯  Фокус на плейлист 6",
    "🎯  Focus playlist 7":
        "🎯  Фокус на плейлист 7",
    "🎯  Focus playlist 8":
        "🎯  Фокус на плейлист 8",
    "🎯  Focus wishlist 1":
        "🎯  Фокус на список пожеланий 1",
    "🎯  Focus wishlist 2":
        "🎯  Фокус на список пожеланий 2",
    "🎯  Focus wishlist 3":
        "🎯  Фокус на список пожеланий 3",
    "🎯  Focus wishlist 4":
        "🎯  Фокус на список пожеланий 4",
    "📚  Focus the library":
        "📚  Фокус на библиотеку",
    "🔄  Browse the list (endless knob)":
        "🔄  Листать список (бесконечный энкодер)",
    "⬆  Browse up":
        "⬆  Листать вверх",
    "⬇  Browse down":
        "⬇  Листать вниз",
    "▶  Play the selected title":
        "▶  Воспроизвести выбранный трек",
    "➕  Selected title to the playlist":
        "➕  Выбранный трек в плейлист",
    "⭐  Selected title to the wishlist":
        "⭐  Выбранный трек в список пожеланий",
    "➕  This playlist takes a title only dragged onto a slot.":
        "➕  Этот плейлист принимает трек, только перетащенный на позицию.",
    "Warm-up list: swap the two selected titles of one dance":
        "Список разминки: поменять местами два выбранных трека одного танца",
    "Play / stop the selected song — in Playing mode also in the list playing, where Space pauses the player":
        "Воспроизвести / остановить выбранный трек — в режиме воспроизведения и в играющем списке, где Пробел ставит плеер на паузу",
    "⏸ Library scan paused: %s / %s files":
        "⏸ Сканирование библиотеки на паузе: %s / %s файлов",
    "⏹ Stopping the library scan…":
        "⏹ Сканирование библиотеки останавливается…",
    "Pause the library scan":
        "Приостановить сканирование библиотеки",
    "Go on with the library scan":
        "Продолжить сканирование библиотеки",
    "Stop the library scan and use the titles read so far; the next start scans the rest":
        "Остановить сканирование библиотеки и использовать уже прочитанные треки; следующий запуск просканирует остальное",
    "⭐ Favorites":
        "⭐ Избранное",
    "🌐 Whole library":
        "🌐 Вся библиотека",
    "⏳ Whole library…":
        "⏳ Вся библиотека…",
    "The whole library is still loading in the background.\nIt is listed here when it is there; keep working meanwhile.":
        "Вся библиотека ещё загружается в фоне.\nОна появится здесь, как только будет готова; пока можно продолжать работу.",
    "🌐 The whole library is still loading — it is listed when it is there.":
        "🌐 Вся библиотека ещё загружается — она появится, как только будет готова.",
    "🌐 Loading the whole library…":
        "🌐 Загружается вся библиотека…",
    "🌐 Listing the whole library: %s / %s titles":
        "🌐 Вся библиотека выводится в список: %s / %s треков",
    "📚 Listing the library: %s / %s titles":
        "📚 Библиотека выводится в список: %s / %s треков",
    "Listing the whole music repository.\nClick to go back to the favorites library.":
        "Показан весь музыкальный архив.\nНажмите, чтобы вернуться к библиотеке избранного.",
    "Listing the favorites library.\nClick to list the whole music repository instead.":
        "Показана библиотека избранного.\nНажмите, чтобы показать весь музыкальный архив.",
    '🔄  Scan repository for new titles':
        '🔄  Искать новые треки в фонотеке',
    'Walk the whole music repository folder and read the tags of new and\nchanged files, so 🌐 Whole library in the library pane and the global\nsearch know every title. No audio analysis; the scan runs in the\nbackground, its progress in the status bar.':
        'Обойти всю папку фонотеки и прочитать теги новых и изменённых\nфайлов, чтобы 🌐 Вся библиотека в панели библиотеки и глобальный\nпоиск знали каждый трек. Без анализа аудио; сканирование идёт в\nфоне, его ход виден в строке состояния.',
    'Scan the whole music repository again for new and changed titles.\nReads the tags only, no audio analysis; the progress shows in the\nstatus bar.':
        'Заново просканировать всю фонотеку на новые и изменённые треки.\nЧитает только теги, без анализа аудио; ход виден в\nстроке состояния.',
    '🌐 Repository: %s / %s files':
        '🌐 Фонотека: %s / %s файлов',
    'Go on with the repository scan':
        'Продолжить сканирование фонотеки',
    'Pause the repository scan':
        'Приостановить сканирование фонотеки',
    'Stop the repository scan and use the titles read so far; the next scan reads the rest':
        'Остановить сканирование фонотеки и использовать уже прочитанные треки; следующее сканирование прочитает остальное',
    '⏹ Stopping the repository scan…':
        '⏹ Сканирование фонотеки останавливается…',
    '⏸ Repository scan paused: %s / %s files':
        '⏸ Сканирование фонотеки приостановлено: %s / %s файлов',
    '🌐 Listing the repository folder…':
        '🌐 Составляется список папки фонотеки…',
    '🌐 The repository is being scanned already.':
        '🌐 Фонотека уже сканируется.',
    'Scan repository':
        'Сканировать фонотеку',
    'Another task (a library scan or an analysis) is writing to the database. Let it finish, then try again.':
        'Другая задача (сканирование библиотеки или анализ) сейчас пишет в базу данных. Дождитесь её завершения и попробуйте снова.',
    "The Paso Doble pick for %s in ⚙ Settings → 🎛 Play sets\n(played in full reads as the 3rd highlight). A change here\nholds for this list only.":
        "Выбор пасодобля для %s в ⚙ Настройки → 🎛 Наборы воспроизведения\n(целиком — то же, что 3-я кульминация). Изменение здесь\nдействует только для этого списка.",
    "🐂 Paso Doble → each round's own pick":
        "🐂 Пасодобль → снова выбор каждого раунда",
    "Advanced: duck and fade times":
        "Дополнительно: приглушение и время затухания",
    "How far the duck goes and how fast, and the fade times of every\nkind of fade. The defaults suit most evenings.":
        "Насколько и как быстро приглушается музыка, и время каждого\nвида затухания. Значения по умолчанию подходят для большинства вечеров.",
    "\n🔁 Loop is off in the queue: it plays once":
        "\n🔁 В очереди повтор выключен: звучит один раз",
    "➕  Volume − / + buttons beside the player's and the cartwall's slider":
        "➕  Кнопки − / + рядом с регулятором плеера и Cartwall",
    "Step the music or the cartwall volume by 2 % a click; held, they glide.\nDouble-click the % readout to type a level instead.":
        "Меняет громкость музыки или Cartwall на 2 % за щелчок; при удержании — плавно.\nДважды щёлкните по значению %, чтобы ввести уровень.",
    "Mute the cartwall, again to bring it back":
        "Выключить звук Cartwall, повторный щелчок вернёт его",
    "🔌 %d titles are no longer on %s: found on %s, they play from there.":
        "🔌 %d треков больше нет на %s: найдены на %s и играют оттуда.",
    "Every text in the app, menus and tables included.\nAbove 115 % the buttons grow with it.\nRead when the app starts, like the theme.":
        "Весь текст приложения, включая меню и таблицы.\nВыше 115 % кнопки растут вместе с ним.\nЧитается при запуске, как и тема.",
    "< filename >":
        "< имя файла >",
    "How many titles, the one playing now included —\nthe count beside it runs down as they end.":
        "Сколько треков, включая текущий —\nсчётчик рядом уменьшается с каждым концом.",
    "Titles still to end, the one playing now included.":
        "Сколько треков ещё закончится, включая текущий.",
    "%d left":
        "осталось %d",
    "🎚  Start the main player's title while the background is still fading out":
        "🎚  Запускать трек основного плеера, пока фон ещё затухает",
    "%s — its own length, then plays on":
        "%s — своя длительность, затем играет дальше",
    "Plays on after its length":
        "Играет дальше после длительности",
    "Hold:":
        "Удержание:",
    "How long it stays at its dip before it comes back up.\n0 = it comes up at once.":
        "Сколько он остаётся на сниженном уровне, прежде чем нарастать обратно.\n0 = нарастает сразу.",
    "Dip to:":
        "Снизить до:",
    "How low the play-length fade takes it before it comes\nback up, in % of the music's level. 0 = all the way down.\nAt most the level it comes back at.":
        "Насколько затухание по длительности опускает его, прежде чем\nон снова поднимется, в % от уровня музыки. 0 = до тишины.\nНе выше уровня, на котором он возвращается.",
}
