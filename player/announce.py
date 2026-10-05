"""Spoken announcement of the next dance ("Nächster Tanz: Langsamer Walzer").

Split out of the player so the text building stays pure and testable — the Qt
speech engine is created lazily and only when the operator switches the feature
on in the play panel.

The announcement is made from RECORDED clips
(speech/announcements/{german,english}/{female,male}/),
generated once with speech/generate_announcements.py: a hall hears a real voice
instead of the Windows synthesiser. Clips are fragments — "Nächster Tanz" and
the dance name are separate files, played back to back with a breath between —
so the same pieces serve the pause cue and the over-the-music one. A dance with
no clip is not announced: the Windows synthesiser is no stand-in for the
recordings (Marcel: "it is really bad"), and an announcement that can't be
made must never break playback. The synthesiser only still reads the takt,
which has no clips.

Everything is spoken in the hall's language (planner.terms.hall_language),
dance names included: a hall announcement made half in another language reads
as a different speaker taking over mid-sentence, and Marcel wants one voice on
the microphone, as far as the recordings go: a clip that was never recorded in
English is played from the German set. The sentence is still built as
fragments, because the takt has to be said separately from the name.
"""
import logging
import random
import re
import subprocess
import sys
import threading

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl

from planner import terms
from planner.models import DANCE_NAMES

log = logging.getLogger("dancesport.gui")

# What the announcement says for each dance — Marcel's wording, chosen by how
# it comes out of the synthesiser, not by how it is printed. Kept complete
# rather than as a diff against DANCE_NAMES so a display rename can never
# change what the hall hears. Codes not listed fall back to DANCE_NAMES.
_SPOKEN = {
    'SA': 'Samba',
    # Written the way the German voice PRONOUNCES them, not the way the dance is
    # written: it read "Chachacha" out letter by letter and turned "Rumba" into
    # "Ramba" (English vowel). German spelling rules get both right — "tsch" is
    # [tʃ], "uh" is a long, unambiguous u. tools/announce_audition.py speaks
    # candidates out loud; change these only after listening.
    'CC': 'Tscha Tscha',   # two, not three: the third is swallowed anyway
    'RB': 'Ruhmba',
    'PD': 'Paso doble',
    # Plain, and staying plain: the voice swallows the end of it, but Jivee,
    # Dschaiw, Jschaiw and the rest of the phonetic respellings all sounded
    # worse. Not a spelling problem — see --voices in
    # tools/announce_audition.py before touching this again.
    'JI': 'Jive',
    'LW': 'Langsamer Walzer',
    'TG': 'Tango',
    'WW': 'Wiener Walzer',
    'QS': 'Quickstep',
    'SF': 'Slowfox',
    'DISCOFOX': 'Discofox',
    'SALSA': 'Salsa',
    'BACHATA': 'Bachata',
    'WCS': 'West Coast Swing',
    'KIZOMBA': 'Kizomba',
    'FORRO': 'Forro',      # the accent throws the synthesiser off
}
# No fragment takes this long. If the engine never reports back the music must
# still come out from under the duck.
_WATCHDOG_MS = 8000

# ── Recorded announcements ────────────────────────────────────────────────────
# Beside the code, like the app icon: a frozen build unpacks them next to the
# modules, so this resolves in both.
_CLIP_DIR = Path(__file__).resolve().parents[1] / "speech" / "announcements"
# One folder per language, a voice folder in each. German was recorded first:
# every clip another language does not have yet is taken from there.
_CLIP_FALLBACK = "german"
# The voices that were recorded. Order matters: it decides the draw when the
# operator asks for a voice that isn't installed.
_CLIP_GENDERS = ("female", "male")
_CLIP_LEAD = "next_dance"
# "Heat" and the spoken number that follows it, filed under the number itself
# ("3.mp3" says "drei"). Only 1-8 were recorded — see `heat_clips`.
_CLIP_HEAT = "heat"
# The clips are named by the code the desk shows (terms.DANCE_SHORT: Samba SB,
# Jive JV); the social dances the app spells out are filed short (the
# generator's DANCE_NAMES).
_CLIP_CODE = {
    'SA': 'SB', 'JI': 'JV',
    'SALSA': 'SL', 'DISCOFOX': 'DF', 'BACHATA': 'BA',
    'KIZOMBA': 'KZ', 'FORRO': 'FO',
}
# A breath between "Nächster Tanz" and the dance. Back to back they run into
# one word; much longer and it sounds like the announcer lost their place. Short
# because it is now the WHOLE gap — the studio silence around each word is
# trimmed off (see below), where it used to be added on top of this.
_CLIP_GAP_MS = 180

# ── Trimming the recorded silence off the clips ───────────────────────────────
# Every clip carries studio silence around the word: a beat before the voice
# starts and a longer one after it stops. Four fragments back to back add up to
# most of a second of nothing, and the announcement drags. So each clip is
# probed ONCE per session (ffmpeg silencedetect) for where its audio really
# begins and ends; playback seeks past the head and cuts to the next fragment at
# the tail instead of sitting through it. The files themselves are never
# touched, and a clip that could not be probed simply plays whole — the trim is
# an improvement, never a precondition.
_TRIM_NOISE_DB = -45      # quieter than anything the voice does
_TRIM_MIN_SECS = 0.05     # shorter than any pause inside a spoken word
_TRIM_PAD_MS = 30         # keep a hair of attack and decay — a hard cut clicks
_TRIM_MIN_KEEP_MS = 150   # below this the probe found nonsense; play it whole
# What an UNMEASURED clip is worth when the announcement is being timed (see
# `clip_secs`). No recorded clip of either voice is longer — the longest is
# "West Coast Swing" at 1.567 s — so this over-states rather than cuts short,
# which is the right way round: too long a lead costs a beat more silence, too
# short a one puts the music back over the voice.
_CLIP_ASSUMED_MS = 1700
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)")
# str(path) → (start_ms, end_ms). Session-lived: the clips ship with the app and
# a run that never announces never pays for the probe.
_BOUNDS = {}
_BOUNDS_PROBED = set()    # folders whose probe has been started


def spoken_fragment(text: str) -> str:
    """One fragment as it is handed to the engine.

    Trailing full stop: the engine cuts the tail off a short utterance — "Jive"
    came out of the hall PA without its end. A sentence mark gives it a beat of
    silence to cut into instead of the word. Text that already ends in
    punctuation is left alone.
    """
    return text + "." if text[-1:].isalnum() else text


# The synthesiser's sentence in each language the hall can be in
# (terms.hall_language): the lead-in, the takt, the word for a missing dance.
_SENTENCE = {
    "de": {"next": "Nächster Tanz", "takt": "Takte", "dance": "Tanz"},
    "en": {"next": "Next dance", "takt": "bars", "dance": "Dance"},
}


def spoken_name(dance_code: str) -> tuple:
    """(what to say for this dance, the language it is said in — the hall's).

    English takes the screen's English names: the respellings in `_SPOKEN`
    are written for a German voice. The social dances keep their own names.
    """
    code = (dance_code or "").upper()
    lang = terms.hall_language()
    if lang == "en":
        name = (terms.DANCE_NAMES_EN.get(code) or _SPOKEN.get(code)
                or DANCE_NAMES.get(code) or code or _SENTENCE[lang]["dance"])
        return name, lang
    name = _SPOKEN.get(code) or DANCE_NAMES.get(code) or code or "Tanz"
    return name, "de"


def announce_text(dance_code: str, takt: int = None, now: bool = False,
                  heat: int = None) -> str:
    """The whole sentence as one string — what gets logged, and what a
    single-voice engine would say.

    `heat` (the heat number) and `takt` (bars per minute) are appended only when
    the operator asked for them — the heat tells the couples which round they
    are in, the takt is useful in training and noise on a tournament floor. The
    heat comes first: it is the part the floor is waiting for.
    `now=True` drops the "Nächster Tanz" framing: spoken over the first bars of
    the music, the dance isn't next any more, it is running.
    """
    name, lang = spoken_name(dance_code)
    words = _SENTENCE[lang]
    text = name if now else f"{words['next']}: {name}"
    if heat:
        text += f", Heat {int(heat)}"
    if takt:
        text += f", {int(takt)} {words['takt']}"
    return text


def announce_parts(dance_code: str, takt: int = None,
                   now: bool = False, heat: int = None) -> list:
    """The same sentence as [(text, language), …] — one fragment per phrase.

    The heat and the takt stay their own fragments so the voice puts a beat
    before them instead of running them into the dance name.
    """
    name, lang = spoken_name(dance_code)
    words = _SENTENCE[lang]
    parts = [] if now else [(f"{words['next']}:", lang)]
    parts.append((name, lang))
    if heat:
        parts.append((f"Heat {int(heat)}", lang))
    if takt:
        parts.append((f"{int(takt)} {words['takt']}", lang))
    return parts


def clip_language() -> str:
    """The clip folder the announcement is made from: the hall's language
    (planner.terms.hall_language — English on an English screen unless the
    German dance terms are kept), German for every other."""
    return "english" if terms.hall_language() == "en" else _CLIP_FALLBACK


def clip_folders(gender: str, root: Path = None,
                 language: str = None) -> list[Path]:
    """Where this voice's clips are looked for, in order: the language's own
    folder, then the German one — a recorded German clip beats the synthesiser.
    """
    root = root if root is not None else _CLIP_DIR
    language = language or clip_language()
    return [root / lang / (gender or "")
            for lang in dict.fromkeys((language, _CLIP_FALLBACK))]


def find_clip(folders, stem: str) -> Path | None:
    """The first recording of `stem` in these folders, or None.

    Clip by clip, not folder by folder: an English set that has the dances
    but not yet the numbers still says the dance in English.
    """
    for folder in folders:
        path = folder / f"{stem}.mp3"
        if path.is_file():
            return path
    return None


def clip_genders(root: Path = None, language: str = None) -> tuple:
    """The recorded voices actually installed, in `_CLIP_GENDERS` order."""
    return tuple(g for g in _CLIP_GENDERS
                 if any(f.is_dir() for f in clip_folders(g, root, language)))


def pick_clip_gender(mode: str, available, last: str = None) -> str | None:
    """Which recorded voice makes this announcement.

    `mode` is the operator's choice — 'female', 'male' or 'random' for a mixed
    evening. Mixed ALTERNATES: `last` is the voice of the previous announcement
    and the other one takes this turn, so the evening reads she, he, she, he
    instead of drawing the same voice four times in a row; only the very first
    announcement (no `last`) is a draw. A voice that was asked for but never
    recorded falls back to what IS there rather than dropping to the
    synthesiser: the wrong gender still beats the robot. None when nothing is
    installed.
    """
    pool = [g for g in _CLIP_GENDERS if g in (available or ())]
    if not pool:
        return None
    if mode in pool:
        return mode
    others = [g for g in pool if g != last]
    return random.choice(others or pool)


def heat_clips(folders, heat: int = None) -> list[Path]:
    """["heat.mp3", "3.mp3"] — the two fragments that say "Heat drei".

    Empty unless BOTH were recorded. The numbers stop at 8, so a field big
    enough to need a ninth heat keeps the dance and drops the number rather
    than calling "Heat" into nothing; the announcement log names the clips that
    did play.
    """
    if not heat:
        return []
    pair = [find_clip(folders, _CLIP_HEAT), find_clip(folders, str(int(heat)))]
    return pair if all(pair) else []


def announce_clips(dance_code: str, gender: str, now: bool = False,
                   root: Path = None, heat: int = None,
                   language: str = None) -> list[Path]:
    """The recorded fragments of this announcement, in the order they play.

    Empty when the dance was never recorded — it is then not announced.
    `now=True` (spoken over the first bars) drops the "Nächster Tanz" lead in,
    exactly as the spoken sentence does. Each fragment comes from `language`
    when it was recorded there, from German otherwise.
    """
    folders = clip_folders(gender, root, language)
    code = (dance_code or "").upper()
    name = find_clip(folders, _CLIP_CODE.get(code, code))
    if name is None:
        return []
    lead = find_clip(folders, _CLIP_LEAD)
    return (([] if now or lead is None else [lead]) + [name]
            + heat_clips(folders, heat))



def _silencedetect(ffmpeg: str, path: Path) -> str | None:
    """ffmpeg's stderr for one clip, or None when the probe didn't run."""
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-map", "a:0",
             "-af", f"silencedetect=noise={_TRIM_NOISE_DB}dB:d={_TRIM_MIN_SECS}",
             "-f", "null", "-"],
            capture_output=True, text=True, errors="replace",
            timeout=20, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stderr


def parse_bounds(stderr: str) -> tuple | None:
    """(start_ms, end_ms) of the spoken audio from silencedetect stderr.

    Only silence at the very head and the very tail counts — a pause inside
    "West Coast Swing" is part of the announcement, not padding. None when the
    output carried no duration to measure against, and the untrimmed span when
    the probe left less than a word behind (something was misread; better a
    slow announcement than a clipped one).
    """
    from shared.audio_probes import parse_silences  # local: keeps import order free
    m = _DURATION_RE.search(stderr or "")
    if not m:
        return None
    h, mi, s = m.groups()
    total = int(round((int(h) * 3600 + int(mi) * 60 + float(s)) * 1000))
    start, end = 0, total
    for span_start, span_end in parse_silences(stderr):
        head, tail = int(span_start * 1000), int(span_end * 1000)
        if head <= _TRIM_PAD_MS:
            start = max(start, tail)
        if tail >= total - _TRIM_PAD_MS:
            end = min(end, head)
    start = max(0, start - _TRIM_PAD_MS)
    end = min(total, end + _TRIM_PAD_MS)
    return (start, end) if end - start >= _TRIM_MIN_KEEP_MS else (0, total)


def clip_bounds(path: Path) -> tuple:
    """(start_ms, end_ms|None) to play of a clip — (0, None) means play it whole.

    Reads the session cache only; `prime_clip_bounds` is what fills it.
    """
    return _BOUNDS.get(str(path)) or (0, None)


def clip_secs(clips) -> float:
    """How long these fragments take to speak, breaths included.

    The trimmed span is what actually plays — playback seeks past the head
    silence and cuts at the tail — so a measured clip is timed exactly. One
    nobody has measured yet plays whole, and is counted at `_CLIP_ASSUMED_MS`.
    """
    clips = list(clips)
    if not clips:
        return 0.0
    total = 0
    for path in clips:
        start, end = clip_bounds(path)
        total += (end - start) if end else _CLIP_ASSUMED_MS
    return (total + _CLIP_GAP_MS * (len(clips) - 1)) / 1000.0


def announce_secs(dance_code: str, takt: int = None, now: bool = False,
                  heat: int = None, root: Path = None,
                  language: str = None) -> float:
    """How long this announcement will run, or 0.0 when that cannot be known.

    The pause needs this to start the voice early enough to be finished before
    the music comes in. It is the LONGER of the installed voices: a mixed
    evening only draws the voice at the moment it speaks, and a lead that fits
    one of them is no lead at all.

    0.0 for everything the recordings don't cover — the takt (read by the
    synthesiser, whose speed is the system's) and a dance that was never
    recorded. The caller falls back to its fixed lead there; guessing a length
    for a voice nobody can time would be worse than admitting it.
    """
    if takt:
        return 0.0
    language = language or clip_language()
    return max((clip_secs(announce_clips(dance_code, gender, now, root, heat,
                                         language))
                for gender in clip_genders(root, language)), default=0.0)

def prime_clip_bounds(folder: Path):
    """Probe every clip of one voice in the background, once per session.

    Off the GUI thread and off the announcement's critical path: the first
    announcement of a run plays its clips whole and every later one is trimmed,
    which is worth far more than making the operator wait for ffmpeg.
    """
    key = str(folder)
    if key in _BOUNDS_PROBED or not folder.is_dir():
        return
    _BOUNDS_PROBED.add(key)
    threading.Thread(target=_prime_clip_bounds, args=(folder,),
                     name="announce-trim", daemon=True).start()


def _prime_clip_bounds(folder: Path):
    from shared.audio_probes import find_ffmpeg
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        log.info("🔈 No ffmpeg — the announcement clips play with their "
                 "recorded silence around each word")
        return
    trimmed = 0
    for clip in sorted(folder.glob("*.mp3")):
        stderr = _silencedetect(ffmpeg, clip)
        bounds = parse_bounds(stderr) if stderr is not None else None
        if bounds is None:
            continue
        _BOUNDS[str(clip)] = bounds
        trimmed += 1
    log.info("🔈 Announcement clips measured\n"
             "language: %s\n"
             "voice: %s\n"
             "clips: %s", folder.parent.name, folder.name, trimmed)


def pick_voice(voices, QLocale, QVoice, language=None):
    """The voice to announce with: the wanted language, female if there is one.

    A hall announcement is a woman's voice in nearly every tournament, and the
    German voices Windows ships (Katja, Hedda) are female anyway — this just
    makes sure a male voice installed alongside them doesn't win by order.
    `language` is a QLocale.Language and defaults to German.
    Returns None when there is nothing to choose from.
    """
    language = language if language is not None else QLocale.Language.German
    matching = [v for v in voices if v.locale().language() == language]
    for pool in (matching, voices):
        for v in pool:
            if v.gender() == QVoice.Gender.Female:
                return v
        if pool:
            return pool[0]
    return None


class DanceAnnouncer:
    """Speaks `announce_parts` through QtTextToSpeech, one fragment per voice.

    Silently does nothing when the module or an engine is unavailable — an
    announcement that can't be made must never break playback.
    """

    def __init__(self, parent=None, on_speaking=None, voice: str = "female"):
        self._tts = None
        self._parent = parent
        self._failed = False
        self._on_speaking = on_speaking   # ducks the music under the voice
        self._voices = {}    # 'de' / 'en' → (QLocale, QVoice)
        self._queue = []     # fragments not spoken yet
        self._token = 0      # invalidates the watchdog of an older fragment
        self._state = None   # QTextToSpeech.State, once there is an engine
        self.speaking = False   # polled by the pause-music ducking
        # Recorded clips: which voice to use, the player they run through (built
        # on first use) and the fragments of the running announcement.
        self._voice_mode = voice or "female"
        self._last_gender = None   # so a mixed evening alternates the voices
        self._clip_player = None
        self._clip_out = None
        self._clip_end = None   # QMediaPlayer.MediaStatus.EndOfMedia, once built
        self._clip_ready = ()   # …the statuses at which a seek sticks
        self._clip_loaded = None   # …and LoadedMedia alone (see _on_clip_status)
        self._clip_queue: list[Path] = []
        self._clips_failed = False
        self._takt_warned = False
        # Where the running clip's audio really starts and ends (see _BOUNDS),
        # and whether that clip has already been placed / already ended.
        self._clip_start_ms = 0
        self._clip_stop_ms = None
        self._clip_seeked = False
        self._clip_over = False
        self._clip_playing = False

    def set_voice(self, mode: str):
        """Which recorded voice announces from here on — 'female', 'male' or
        'random' for a mixed evening (the voices then alternate). Takes effect
        on the next announcement; one already running is left to finish in the
        voice it started in."""
        self._voice_mode = mode or "female"

    def _find_voice(self, tts, QLocale, QVoice, language):
        """(locale, voice) the engine speaks `language` with, or None.

        availableVoices() only ever lists the *current* locale, so finding a
        second language means walking the locales; the engine is left on
        whichever one the search stopped at, and the caller sets the one it
        wants to keep.
        """
        for loc in tts.availableLocales():
            if loc.language() != language:
                continue
            tts.setLocale(loc)
            v = pick_voice(tts.availableVoices(), QLocale, QVoice, language)
            if v is not None:
                return loc, v
        return None

    def _engine(self):
        if self._tts is not None or self._failed:
            return self._tts
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech, QVoice
            from PySide6.QtCore import QLocale
        except ImportError as exc:
            self._failed = True
            log.warning("🔈 No text-to-speech module available: %s", exc)
            return None
        try:
            engines = [e for e in QTextToSpeech.availableEngines() if e != "mock"]
            # Engines do NOT all ship the same voices, and one without a German
            # one would read the announcement in whatever it has. So try them in
            # order and keep the first that speaks German, falling back to the
            # first that works at all.
            tts, german = None, None
            for name in (engines or [None]):
                cand = QTextToSpeech(name, self._parent) if name \
                    else QTextToSpeech(self._parent)
                de = self._find_voice(cand, QLocale, QVoice, QLocale.Language.German)
                if tts is None or (de is not None and german is None):
                    if tts is not None:
                        tts.deleteLater()
                    tts, german = cand, de
                else:
                    cand.deleteLater()
                if german is not None:
                    break
            # An English hall (terms.hall_language) is read by an English
            # voice; without one the German voice reads the English sentence.
            english = self._find_voice(tts, QLocale, QVoice,
                                       QLocale.Language.English)
            self._voices = {"de": german, "en": english}
            if german is not None:
                tts.setLocale(german[0])
                tts.setVoice(german[1])
            else:
                tts.setLocale(QLocale(QLocale.Language.German,
                                      QLocale.Country.Germany))
            self._state = QTextToSpeech.State
            tts.stateChanged.connect(self._on_state)
            self._tts = tts
            log.info("🔈 Announcer ready\n"
                     "engine: %s (of %s)\n"
                     "german voice: %s\n"
                     "english voice: %s", tts.engine(), ", ".join(engines) or "default",
                     german[1].name() if german else "—",
                     english[1].name() if english else "—")
            if german is None:
                log.warning("🔈 No German voice installed — the announcement is "
                            "read by whatever voice the engine defaults to.\n"
                            "Fix: Windows Settings → Time & language → Speech → "
                            "Manage voices → add a German voice")
        except Exception as exc:              # engine init is platform-dependent
            self._failed = True
            log.warning("🔈 Text-to-speech unavailable: %s", exc)
        return self._tts

    def _clip_engine(self):
        """The player the recorded clips run through, built on first use.

        Its own player, not the deck's: the announcement plays OVER the music
        that is being ducked for it.
        """
        if self._clip_player is not None or self._clips_failed:
            return self._clip_player
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            player = QMediaPlayer(self._parent)
            out = QAudioOutput(self._parent)
            player.setAudioOutput(out)
            player.mediaStatusChanged.connect(self._on_clip_status)
            player.errorOccurred.connect(self._on_clip_error)
            self._clip_end = QMediaPlayer.MediaStatus.EndOfMedia
            self._clip_loaded = QMediaPlayer.MediaStatus.LoadedMedia
            self._clip_ready = (QMediaPlayer.MediaStatus.LoadedMedia,
                                QMediaPlayer.MediaStatus.BufferedMedia)
            self._clip_player, self._clip_out = player, out
        except Exception as exc:          # multimedia is platform-dependent
            self._clips_failed = True
            log.warning("🔈 Recorded announcements unavailable: %s", exc)
        return self._clip_player

    def _clips_for(self, dance_code: str, now: bool,
                   heat: int = None) -> list[Path]:
        """The recorded fragments for this dance, or [] when there are none."""
        if self._clips_failed:
            return []
        language = clip_language()
        gender = pick_clip_gender(self._voice_mode, clip_genders(None, language),
                                  self._last_gender)
        if gender is None:
            return []
        self._last_gender = gender
        for folder in clip_folders(gender, None, language):
            prime_clip_bounds(folder)   # so the NEXT one is trimmed
        return announce_clips(dance_code, gender, now, heat=heat,
                              language=language)

    def _start_clip(self, path: Path):
        self._token += 1
        token = self._token
        QTimer.singleShot(_WATCHDOG_MS, lambda: self._give_up(token))
        self._clip_start_ms, self._clip_stop_ms = clip_bounds(path)
        self._clip_seeked = False   # this clip's media hasn't been placed yet
        self._clip_over = False     # …and its end has not been acted on
        self._clip_playing = False  # …and its audio has not started
        self._clip_player.setSource(QUrl.fromLocalFile(str(path)))
        self._clip_player.play()

    def _play_clips(self, clips: list[Path]) -> bool:
        if self._clip_engine() is None:
            return False
        self._clip_queue = list(clips[1:])
        # Duck before the first clip, exactly as the spoken path does: the
        # player reports back a moment later, and between clips it reports the
        # end of one — neither must let the music jump back up mid-announcement.
        self._set_speaking(True)
        self._start_clip(clips[0])
        return True

    def _next_clip(self, token: int):
        if token != self._token or not self._clip_queue:
            return
        self._start_clip(self._clip_queue.pop(0))

    def _on_clip_status(self, status):
        """The media of the running fragment reports in.

        Both halves run ONCE per fragment. The backend repeats a status (loaded
        then buffered, a stray end from the clip that was cut short), and acting
        on a repeat would seek a fragment that is already playing or pull the
        NEXT one out of the queue unheard — which is a word missing from the
        announcement, not a glitch anybody can hear as one.
        """
        if status in self._clip_ready:
            if not self._clip_seeked:
                self._clip_seeked = True
                self._clip_playing = status != self._clip_loaded
                # Skip the recorded silence in front of the word. Only here: a
                # seek before the media is loaded is dropped by the backend.
                if self._clip_start_ms:
                    self._clip_player.setPosition(self._clip_start_ms)
                if self._clip_stop_ms:
                    self._arm_tail_cut(self._token,
                                       self._clip_stop_ms - self._clip_start_ms)
                return
            if status != self._clip_loaded:
                self._clip_playing = True    # the word is running
            elif self._clip_playing:
                # …and now it is not. WMF never reports EndOfMedia for a clip
                # that runs to its own end — it falls back to LoadedMedia — so a
                # clip nobody measured yet (the first announcement of a voice,
                # before the ffmpeg trim probe lands, or every one of them where
                # there is no ffmpeg) would hang here until the 8 s watchdog:
                # eight seconds of music under the duck, with the fragments
                # after this one never spoken.
                self._clip_done(self._token)
            return
        if status == self._clip_end:
            self._clip_done(self._token)

    def _arm_tail_cut(self, token: int, after_ms: int, retried: bool = False):
        """Move on when the word is over instead of sitting through the silence
        the recording ends in.

        Timed rather than watched: the player reports its position on the
        backend's own schedule, and a position left over from the fragment
        BEFORE this one would cut this one before it was ever heard. The one
        re-check covers a slow start — the clock ran while the media was still
        opening, so ask the player where it really is before cutting.
        """
        QTimer.singleShot(max(0, int(after_ms)),
                          lambda: self._cut_tail(token, retried))

    def _cut_tail(self, token: int, retried: bool):
        if token != self._token or self._clip_over or not self._clip_stop_ms:
            return
        left = self._clip_stop_ms - self._clip_player.position()
        if left > 50 and not retried:
            self._arm_tail_cut(token, left, retried=True)
            return
        self._clip_player.stop()
        self._clip_done(token)

    def _clip_done(self, token: int):
        """One fragment is over — the next one, or the end of the whole run."""
        if token != self._token or self._clip_over:
            return
        self._clip_over = True
        if self._clip_queue:
            QTimer.singleShot(_CLIP_GAP_MS, lambda: self._next_clip(token))
        else:
            self._set_speaking(False)

    def _on_clip_error(self, err, msg):
        log.warning("🔈 Announcement clip failed\n"
                    "error: %s\n"
                    "detail: %s", err, msg)
        self._clip_queue = []
        self._set_speaking(False)

    def _set_speaking(self, on: bool):
        """The duck spans the whole run, so this only flips at its ends."""
        if on == self.speaking:
            return
        self.speaking = on
        if self._on_speaking is not None:
            try:
                self._on_speaking(on)
            except RuntimeError:
                # The listener's Qt objects are already deleted — a teardown
                # this didn't get told about. Nothing left to duck; stop asking.
                self._on_speaking = None

    def _say(self, text: str, lang: str):
        pair = self._voices.get(lang) or self._voices.get("de")
        if pair is not None:
            self._tts.setLocale(pair[0])
            self._tts.setVoice(pair[1])
        self._token += 1
        token = self._token
        QTimer.singleShot(_WATCHDOG_MS, lambda: self._give_up(token))
        self._tts.say(spoken_fragment(text))

    def _on_state(self, state):
        if state == self._state.Speaking:
            self._set_speaking(True)
            return
        if state in (self._state.Ready, self._state.Error):
            if self._queue:
                self._say(*self._queue.pop(0))
            else:
                self._set_speaking(False)

    def _give_up(self, token: int):
        """The engine never said the fragment was over — let the music back up
        rather than leaving it ducked behind a voice that isn't coming. And
        silence that voice: arriving late, it would talk over the music at
        full level."""
        if token != self._token or not self.speaking:
            return
        log.warning("🔈 Announcement never finished — restoring the music")
        self.stop()

    def speak(self, dance_code: str, takt: int = None, now: bool = False,
              heat: int = None) -> bool:
        """Say the dance from the recordings. Returns False when nothing was
        spoken — a dance without a clip is not read by the synthesiser.

        Asking for the takt hands the WHOLE announcement to the synthesiser:
        there are no clips for a tempo (the recorded numbers are the heats
        1-8), and half an announcement in the recorded voice with the tempo
        tacked on by Windows reads as two announcers talking over each other.
        One voice on the microphone — the operator ticking "…with takt" is
        choosing which one.

        The takt only steps aside for a synthesiser that is actually there: on
        a machine with no speech engine the recordings still say everything
        except the tempo, which beats an announcement nobody hears.
        """
        by_voice = bool(takt) and self._engine() is not None
        if takt and not self._takt_warned:
            self._takt_warned = True
            log.info("🔈 The takt was asked for\n"
                     "read by: %s\n"
                     "why: the recordings have clips for the dances and the "
                     "heats, none for a tempo",
                     "the synthesiser" if by_voice
                     else "the recordings, without the takt — no speech engine")
        clips = [] if by_voice else self._clips_for(dance_code, now, heat)
        if clips:
            log.info("🔈 Announcing dance from the recordings\n"
                     "text: %s\n"
                     "clips: %s\n"
                     "over the music: %s",
                     announce_text(dance_code, None, now, heat),
                     ", ".join(c.stem for c in clips), now)
            if self._play_clips(clips):
                return True
        if not by_voice:
            log.info("🔈 Dance not announced\n"
                     "dance: %s\n"
                     "why: no recording for it", dance_code)
            return False
        tts = self._engine()
        if tts is None:
            return False
        parts = announce_parts(dance_code, takt, now, heat)
        log.info("🔈 Announcing dance\n"
                 "text: %s\n"
                 "over the music: %s",
                 announce_text(dance_code, takt, now, heat), now)
        self._queue = parts[1:]
        # Duck before the first word: the engine reports Speaking a moment
        # later, and between fragments it reports Ready — neither must let the
        # music jump back up mid-announcement.
        self._set_speaking(True)
        self._say(*parts[0])
        return True

    def stop(self):
        self._queue = []
        self._clip_queue = []
        self._clip_stop_ms = None   # no tail cut owed on a clip that is gone
        self._token += 1        # whatever was pending is no longer wanted
        if self._tts is not None:
            self._tts.stop()
        if self._clip_player is not None:
            self._clip_player.stop()
        self._set_speaking(False)

    def shutdown(self):
        """The window is going away — stop talking and forget the duck callback.

        The engine is a child of that window and emits one last state change
        while it is being destroyed. By then the player's timers are gone, and
        calling back into them raises RuntimeError out of the deleted C++
        objects, which surfaces as an uncaught exception on quit."""
        self._on_speaking = None
        self._queue = []
        self._clip_queue = []
        self.speaking = False
        for engine in (self._tts, self._clip_player):
            if engine is not None:
                try:
                    engine.stop()
                except RuntimeError:
                    pass      # already deleted — nothing left to silence
