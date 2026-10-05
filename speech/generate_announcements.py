#!/usr/bin/env python3
"""Generate tournament-dance announcements with ElevenLabs.

The script creates one MP3 per announcement, per language and per configured
voice:
  announcements/german/male/{CODE}.mp3
  announcements/english/female/{CODE}.mp3
That is the set the app plays (player.announce._CLIP_DIR): the dances, the
"Nächster Tanz" / "Next dance" lead-in, "Heat" and the heat numbers 1-8. The
file names are the same in every language (the lead-in is next_dance.mp3
in German too), so the app finds a clip by its code and takes the German one
wherever another language has none yet. Another language is one more entry in
DANCE_NAMES and HEAT_CALLS.

Pronunciation variants go somewhere else on purpose:
  varianten/german/male/{CODE}__{spelling}.mp3
A multilingual voice reads "Forró", "Cha-Cha-Cha" or "Heat" the way it reads
them, and the only way to find out which spelling makes it say the word a
dancer expects is to listen. PRONUNCIATION_VARIANTS below holds the spellings
worth auditioning; the winner goes into DANCE_NAMES and the clip is re-made.
Nothing under varianten/ is ever played, shipped or committed — the build spec
globs announcements/{language}/{voice}/*.mp3 only.

Anything already on disk is left alone, so a second run only fills the gaps
(and costs nothing). Delete a file to have it made again.

Install dependencies with:
    pip install -U elevenlabs python-dotenv

Put ELEVENLABS_API_KEY in the environment or in a .env file next to this
script, then run:
    python generate_announcements.py
"""

import os
import re
import sys
from pathlib import Path
from collections.abc import Iterable

# Editable voice IDs. Replace these with IDs from your ElevenLabs Voice
# Library if you prefer different voices. Both are multilingual voices and
# speak every language below.
VOICE_IDS = {
    "male": "P2nQmhGdlvdom54cOLbN",
    "female": "5ThBwj643QOv31S1kAFo",
}

MODEL_ID = "eleven_multilingual_v2"
OUTPUT_ROOT = Path(__file__).resolve().parent / "announcements"
VARIANTS_ROOT = Path(__file__).resolve().parent / "varianten"

# Keep the spoken forms explicit. In particular, the punctuation/spacing
# choices below can improve pronunciation in multilingual_v2:
# - Forró: keep the accent and test it with the selected voice; if needed,
#   use "Forro" only as a voice-specific fallback.
# - West Coast Swing: keep the spaces so it is spoken as three words.
# - Cha-Cha-Cha: keep the hyphens so the three syllables are separated.
DANCE_NAMES = {
    "german": {
        "LW": "Langsamer Walzer",
        "TG": "Tango",
        "WW": "Wiener Walzer",
        "SF": "Slowfox",
        "QS": "Quickstep",
        "SB": "Samba",
        "CC": "Cha-Cha-Cha",
        # The full stop is the audition winner (PRONUNCIATION_VARIANTS below):
        # bare "Rumba" comes out of the PA sounding like a question.
        "RB": "Rumba.",
        "PD": "Paso Doble",
        "JV": "Jive",
        "BA": "Bachata",
        "SL": "Salsa",
        "WCS": "West Coast Swing",
        "KZ": "Kizomba",
        "FO": "Forró",
        "DF": "Discofox",
        "next_dance": "Nächster Tanz",
    },
    "english": {
        "LW": "Slow Waltz",
        "TG": "Tango",
        "WW": "Viennese Waltz",
        "SF": "Slowfox",  # Marcel's choice over "Slow Foxtrot"
        "QS": "Quickstep",
        "SB": "Samba",
        "CC": "ChaCha",  # Marcel's choice over "Cha-Cha-Cha"
        "RB": "Rumba.",
        "PD": "Paso Doble",
        "JV": "Jive",
        "BA": "Bachata",
        "SL": "Salsa",
        "WCS": "West Coast Swing",
        "KZ": "Kizomba",
        "FO": "Forró",
        "DF": "Discofox",
        "next_dance": "Next dance",
    },
}

# The running order: "Heat" and the number that follows it. The numbers are
# spelled out — a bare "3" is read as a digit by some voices and as "drei" by
# others, and the hall needs the word.
HEAT_CALLS = {
    "german": {
        "heat": "Heat",
        "1": "eins",
        "2": "zwei",
        "3": "drei",
        "4": "vier",
        "5": "fünf",
        "6": "sechs",
        "7": "sieben",
        "8": "acht",
    },
    "english": {
        "heat": "Heat",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
    },
}

ANNOUNCEMENTS = {language: {**DANCE_NAMES[language], **HEAT_CALLS[language]}
                 for language in DANCE_NAMES}

# Clips a voice reads too fast for the hall, as (voice, "language/code") →
# ElevenLabs speed (1.0 is the voice's own pace, 0.7 the slowest it takes).
# Marcel: the English female Slow Waltz and ChaCha were too fast.
SPEEDS = {
    ("female", "english/LW"): 0.85,
    ("female", "english/CC"): 0.85,
}

# Spellings to audition, per language and announcement (see the module
# docstring). Only the words a German multilingual voice can get wrong are
# listed — the English ones, the Latin-American ones and the accent. The
# spelling that wins goes into DANCE_NAMES / HEAT_CALLS.
#
# Punctuation is a pronunciation variant too: a bare word is read as if the
# sentence went on, which is why "Rumba" comes out of the PA sounding like a
# question. A full stop makes the voice put it down, an exclamation mark calls
# it out. player.announce.spoken_fragment does the same for the live synthesiser.
PRONUNCIATION_VARIANTS = {
    "german": {
        "RB": ["Rumba.", "Rumba!"],
        "heat": ["Hiet", "Hiit"],
        "CC": ["Cha Cha Cha", "Tscha-Tscha-Tscha"],
        "SF": ["Slow Fox", "Slouwfox"],
        "QS": ["Quick Step", "Kwickstepp"],
        "JV": ["Jive.", "Dschaiw", "Dschaif"],
        "PD": ["Passo Doble", "Paso Dobleh"],
        "WCS": ["West-Coast-Swing", "Wesst Kohst Swing"],
        "FO": ["Forro", "Forroh"],
        "KZ": ["Kisomba"],
        "BA": ["Batschata"],
        "SL": ["Salssa"],
        "DF": ["Disco Fox", "Diskofox", "Discofox."],
        "TG": ["Tango."],
    },
    "english": {
        "RB": ["Rumba.", "Rumba!"],
    },
}

# Punctuation in a variant's file name, spelled out in the variant's language.
_PUNCTUATION = {
    "german": {".": " punkt", "!": " ruf", "?": " frage", ",": " komma"},
    "english": {".": " stop", "!": " exclaim", "?": " question", ",": " comma"},
}


def get_api_key() -> str | None:
    """Read the key from the environment, optionally loading a local .env."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv(Path(__file__).resolve().parent / ".env")
    return os.getenv("ELEVENLABS_API_KEY")


def write_audio(chunks: Iterable[bytes], destination: Path) -> None:
    """Write the streamed ElevenLabs response to an MP3 file.

    The stream lands in a .part file first. A download cut halfway would
    otherwise leave a clipped MP3 under the final name, and a second run keeps
    whatever is already on disk.
    """
    partial = destination.with_name(destination.name + ".part")
    try:
        with partial.open("wb") as output:
            for chunk in chunks:
                if chunk:
                    output.write(chunk)
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)


def spelling(text: str, language: str = "german") -> str:
    """The spoken text as a file name part: 'Rumba!' → 'rumba_ruf' in German,
    'rumba_exclaim' in English.

    Punctuation is spelled out rather than dropped — between "Rumba." and
    "Rumba!" it is the whole difference, and two variants may not share a name.
    """
    for mark, word in _PUNCTUATION[language].items():
        text = text.replace(mark, word)
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def announcement_jobs(genders: Iterable[str]) -> list:
    """(voice, label, text, destination) for every clip this script makes."""
    jobs = []
    for gender in genders:
        for language, texts in ANNOUNCEMENTS.items():
            for code, text in texts.items():
                jobs.append((gender, f"{language}/{code}", text,
                             OUTPUT_ROOT / language / gender / f"{code}.mp3"))
        for language, variants in PRONUNCIATION_VARIANTS.items():
            for code, texts in variants.items():
                for text in texts:
                    jobs.append((gender, f"{language}/{code} ({text})", text,
                                 VARIANTS_ROOT / language / gender
                                 / f"{code}__{spelling(text, language)}.mp3"))
    return jobs


def main() -> int:
    api_key = get_api_key()
    if not api_key:
        print(
            "Error: no ELEVENLABS_API_KEY found in the environment or a .env file.",
            file=sys.stderr,
        )
        print("No audio files were created.", file=sys.stderr)
        return 2

    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        print("Error: the 'elevenlabs' package is missing. Install it with: pip install -U elevenlabs", file=sys.stderr)
        return 3

    try:
        client = ElevenLabs(api_key=api_key)
    except Exception as exc:
        print(f"Error initialising the ElevenLabs client: {exc}", file=sys.stderr)
        return 4

    genders = []
    for gender, voice_id in VOICE_IDS.items():
        if not voice_id or voice_id.startswith("PASTE_"):
            print(f"Skipped: no voice ID set for {gender}.", file=sys.stderr)
            continue
        genders.append(gender)

    jobs = announcement_jobs(genders)
    pending = [job for job in jobs if not job[3].exists()]
    print(f"{len(jobs)} announcement(s), {len(jobs) - len(pending)} already there, "
          f"{len(pending)} to make.")

    generated: list[Path] = []
    for number, (gender, label, spoken_text, destination) in enumerate(pending, 1):
        destination.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{number}/{len(pending)}] {gender}/{label}: {spoken_text}")
        try:
            options = {}
            speed = SPEEDS.get((gender, label))
            if speed is not None:
                # Only the pace is sent. Reading the voice's stored settings to
                # change just that needs a voices_read key, which ours isn't.
                from elevenlabs import VoiceSettings
                options["voice_settings"] = VoiceSettings(speed=speed)
            audio = client.text_to_speech.convert(
                text=spoken_text,
                voice_id=VOICE_IDS[gender],
                model_id=MODEL_ID,
                output_format="mp3_44100_128",
                **options,
            )
            write_audio(audio, destination)
            generated.append(destination)
            print(f"  saved: {destination}")
        except Exception as exc:
            print(f"  ERROR for {gender}/{label}: {exc}", file=sys.stderr)
            if destination.exists() and destination.stat().st_size == 0:
                destination.unlink()

    print("\nFiles created:")
    for path in generated:
        print(path)
    print(f"Total: {len(generated)} file(s)")
    return 0 if generated or not pending else 5


if __name__ == "__main__":
    raise SystemExit(main())
