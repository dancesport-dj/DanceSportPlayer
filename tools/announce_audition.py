"""Hear how the announcement voice reads each candidate spelling, in a row.

The synthesiser is the only judge of a spelling: 'ChaCha' looks fine written
down and comes out letter by letter, and 'Jive' loses its end. So: listen, note
what sounded right, and put it into _SPOKEN in player/announce.py.

Each candidate is spoken exactly the way the real announcement speaks it — its
own utterance, the last one of the sentence, through spoken_fragment(). Saying
"3. Jive" in one breath would hide the very clipping this is meant to expose,
so the number comes first, as a separate utterance.

When no spelling works, the voice itself is the problem. This machine has four
German voices across two engines (winrt: Stefan, Katja, Hedda — sapi: Hedda
Desktop), and they do not clip alike; --voices plays the same word through all
of them, one after the other.

    .venv\\Scripts\\python.exe -m tools.announce_audition            # jive set
    .venv\\Scripts\\python.exe -m tools.announce_audition rumba
    .venv\\Scripts\\python.exe -m tools.announce_audition Jive Jivee Dschaif
    .venv\\Scripts\\python.exe -m tools.announce_audition --voices
    .venv\\Scripts\\python.exe -m tools.announce_audition --voices Jive Jivee
    .venv\\Scripts\\python.exe -m tools.announce_audition --rate -0.3
    .venv\\Scripts\\python.exe -m tools.announce_audition --engine sapi
"""
import argparse
import sys

from PySide6.QtCore import QLocale, QTimer
from PySide6.QtWidgets import QApplication

from player.announce import DanceAnnouncer, spoken_fragment

# Candidate spellings per problem word, best guess first. Punctuation variants
# belong here too — the mark at the end changes the phrasing without touching
# the word.
SETS = {
    "jive": ["Jive", "Jivee", "Jive!", "Jive?", "Dschaif", "Dschaiff",
             "Dschaiw", "Jschaiw", "Djaif", "Jaif"],
    "rumba": ["Ruhmba", "Rumba", "Rummba", "Rum Ba"],
    "cc": ["Tscha Tscha", "Tscha Tscha Tscha", "Tschatscha", "Chachacha",
           "Cha Cha Cha"],
    "pd": ["Paso doble", "Passo Dobble", "Paßo Doble"],
    "all": ["Langsamer Walzer", "Tango", "Wiener Walzer", "Slowfox",
            "Quickstep", "Samba", "Tscha Tscha", "Ruhmba", "Paso doble",
            "Jivee", "Discofox"],
}


def german_voices(engine_name):
    """[(engine, tts, locale, voice), …] — every German voice of one engine.

    availableVoices() only ever lists the CURRENT locale, so the locales have to
    be walked; the engine is left on the last one visited and the caller sets
    whichever it wants before speaking.
    """
    from PySide6.QtTextToSpeech import QTextToSpeech
    found = []
    tts = QTextToSpeech(engine_name)
    for loc in tts.availableLocales():
        if loc.language() != QLocale.Language.German:
            continue
        tts.setLocale(loc)
        for v in tts.availableVoices():
            found.append((engine_name, tts, loc, v))
    return found


def all_german_voices():
    """Every German voice this machine has, across every engine."""
    from PySide6.QtTextToSpeech import QTextToSpeech
    out = []
    for name in QTextToSpeech.availableEngines():
        if name == "mock":
            continue
        out += german_voices(name)
    return out


def build_tts(ann: DanceAnnouncer, engine_name):
    """The announcer's own engine, or a named one set to its German voice —
    engines clip short words differently, so which one speaks is a lever."""
    if not engine_name:
        return ann._engine()
    from PySide6.QtTextToSpeech import QTextToSpeech, QVoice
    tts = QTextToSpeech(engine_name)
    de = ann._find_voice(tts, QLocale, QVoice, QLocale.Language.German)
    if de is not None:
        tts.setLocale(de[0])
        tts.setVoice(de[1])
        ann._voices = {"de": de}
    return tts


def build_queue(words, voices):
    """The run as [(line to print, tts, locale, voice, text to speak), …].

    Numbers and voice names are utterances of their own, so the candidate stays
    the short, FINAL one — the position the announcement actually puts it in.
    """
    queue = []
    for eng, tts, loc, voice in voices:
        if len(voices) > 1:
            short = voice.name().replace("Microsoft ", "")
            queue.append((f"\n── {eng}  ·  {voice.name()} ──",
                          tts, loc, voice, f"Stimme {short}, {eng}"))
        for i, w in enumerate(words, 1):
            queue.append(("", tts, loc, voice, f"Nummer {i}"))
            queue.append((f"{i:2d}. {w}", tts, loc, voice, w))
    return queue


def main():
    # The Windows console is cp1252 and the voice names print inside a rule of
    # box characters — without this the tool dies on its own heading.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("words", nargs="*",
                    help=f"spellings to try, or a set: {', '.join(SETS)}")
    ap.add_argument("--rate", type=float, default=None,
                    help="speaking rate, -1.0 (slow) … 1.0 (fast)")
    ap.add_argument("--engine", default=None,
                    help="speech engine to use (e.g. winrt, sapi)")
    ap.add_argument("--voices", action="store_true",
                    help="play through EVERY German voice of every engine; "
                         "with no words given, just the word Jive")
    args = ap.parse_args()

    words = args.words or (["Jive"] if args.voices else ["jive"])
    if len(words) == 1 and words[0] in SETS:
        words = SETS[words[0]]

    app = QApplication([])
    ann = DanceAnnouncer()
    if args.voices:
        voices = (german_voices(args.engine) if args.engine
                  else all_german_voices())
        if not voices:
            print("no German voice on this machine")
            return 1
    else:
        tts = build_tts(ann, args.engine)
        if tts is None:
            print("no speech engine")
            return 1
        pair = ann._voices.get("de")
        voices = [(tts.engine(), tts, tts.locale(),
                   pair[1] if pair else tts.voice())]

    for _eng, tts, _loc, _v in voices:
        if args.rate is not None:
            tts.setRate(max(-1.0, min(1.0, args.rate)))
    print("rate:", f"{voices[0][1].rate():+.2f}",
          " voices:", len(voices))
    print("Listen for the END of each word — that is what gets swallowed.")

    queue = build_queue(words, voices)
    speaking = {"tts": None}

    def say_next():
        if not queue:
            QTimer.singleShot(1200, app.quit)
            return
        label, tts, loc, voice, text = queue.pop(0)
        if label:
            print(label, flush=True)
        tts.setLocale(loc)
        tts.setVoice(voice)
        speaking["tts"] = tts
        tts.say(spoken_fragment(text))

    def on_state(tts, state):
        # Every engine is connected, but only the one that was asked to speak
        # may drive the queue — an idle engine reports Ready too.
        if tts is not speaking["tts"]:
            return
        if state in (tts.State.Ready, tts.State.Error):
            QTimer.singleShot(400, say_next)

    for _eng, tts, _loc, _v in {id(v[1]): v for v in voices}.values():
        tts.stateChanged.connect(lambda s, t=tts: on_state(t, s))
    say_next()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
