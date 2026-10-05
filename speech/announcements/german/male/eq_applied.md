# male: announcement clips with an EQ baked in

- Preset: **clear**
- Applied: 2026-09-20 19:55
- Clips treated: 27
- The untouched recordings are in `original/`, and every run reads from there — applying again cannot stack a second EQ.

## Filter chain (ffmpeg -af)

    highpass=f=110
    equalizer=f=300:t=q:w=1.2:g=-3
    equalizer=f=3200:t=q:w=1.0:g=5
    acompressor=threshold=-18dB:ratio=3:attack=5:release=120:makeup=3
    alimiter=limit=0.95

## Re-encoded as

    -c:a libmp3lame -b:a 192k -ar 44100 -ac 1

## To undo

    .venv\Scripts\python.exe -m tools.announce_eq --restore

Written by `tools/announce_eq.py`; the next --apply overwrites it.
