"""Download the Bootstrap Icons (MIT) the app uses and generate shared/iconset.py.

    py tools/make_iconset.py shared/iconset.py

Needs the network — the icons are fetched from jsDelivr. Run it after adding a
name to WANT below; the generated module is what ships, so a build never has to
reach the internet.
"""
import re
import sys
import urllib.request

BASE = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/icons/{}.svg"

# app icon name → Bootstrap Icons name
WANT = {
    # transport
    "play": "play-fill",
    "pause": "pause-fill",
    "stop": "stop-fill",
    "play_circle": "play-circle-fill",
    "pause_circle": "pause-circle-fill",
    "prev": "skip-backward-fill",
    "next": "skip-forward-fill",
    "rewind": "rewind-fill",
    "forward": "fast-forward-fill",
    "cue_start": "skip-start-fill",
    "panic": "x-octagon-fill",
    "break_music": "cup-hot-fill",
    "fade_out": "volume-off-fill",
    "extend": "stopwatch-fill",
    "volume": "volume-up-fill",
    "volume_low": "volume-down-fill",
    "mute": "volume-mute-fill",
    "speak": "megaphone-fill",
    "sliders": "sliders",
    "display": "display-fill",
    "party": "balloon-fill",
    "target": "bullseye",
    "headphones": "headphones",
    "mic": "mic-fill",
    "soundwave": "soundwave",
    # files & lists
    "folder_open": "folder2-open",
    "folder": "folder-fill",
    "save": "floppy",
    "print": "printer-fill",
    "usb": "usb-drive-fill",
    "clipboard": "clipboard",
    "duplicate": "copy",
    "pane": "window-dock",
    "card_text": "card-text",
    "trash": "trash3",
    "eraser": "eraser-fill",
    "export": "box-arrow-up",
    "music": "music-note-beamed",
    "music_list": "music-note-list",
    "library": "journals",
    "calendar": "calendar-event",
    "pin": "pin-angle-fill",
    "history": "clock-history",
    "hourglass": "hourglass-split",
    "image": "image",
    "trophy": "trophy-fill",
    "puzzle": "puzzle-fill",
    # editing
    "plus": "plus-lg",
    "minus": "dash-lg",
    "check": "check-lg",
    "check_circle": "check-circle-fill",
    "close": "x-lg",
    "pencil": "pencil",
    "edit": "pencil-square",
    "search": "search",
    "star": "star-fill",
    "lock": "lock-fill",
    "unlock": "unlock-fill",
    "swap": "arrow-left-right",
    "undo": "arrow-counterclockwise",
    "redo": "arrow-clockwise",
    "regen": "arrow-repeat",
    "expand": "plus-square",
    "collapse": "dash-square",
    "compact": "arrows-collapse",
    "decks": "columns-gap",
    "compass": "compass",
    "gear": "gear-fill",
    "globe": "globe2",
    "chart": "bar-chart-fill",
    "bricks": "bricks",
    "analysis": "graph-up",
    "robot": "robot",
    "prompt": "chat-quote-fill",
    "brain": "cpu-fill",
    "bolt": "lightning-charge-fill",
    "stars": "stars",
    "warmup": "person-arms-up",
    "highlight": "activity",
    "warning": "exclamation-triangle-fill",
    "issue": "exclamation-circle-fill",
    "help": "question-circle",
    "blocked": "slash-circle",
    "state_save": "database-fill-check",
    # play length: the column header, and the two threshold verdicts
    # The track-length column. Outline, not -fill: at 10 px the filled one is a
    # dark blob next to the play triangle, the outline still reads as a watch.
    "stopwatch": "stopwatch",
    "flag": "flag-fill",             # marked for potential replace
    # Below / above the length threshold. Two hourglasses differing only in
    # where the sand sits are indistinguishable at 12 px — arrows are not.
    "short_track": "arrow-down-circle-fill",
    "long_track": "arrow-up-circle-fill",
    "mouse": "mouse2-fill",
    "keyboard": "keyboard-fill",
    # carets
    "caret_up": "caret-up-fill",
    "caret_down": "caret-down-fill",
    "caret_left": "caret-left-fill",
    "caret_right": "caret-right-fill",
    # the 🎨 looks: what the rest of the chrome's emoji become (shared/look_icons.py)
    "tag": "tag-fill",
    "clean": "magic",
    "suitcase": "suitcase-lg-fill",
    "shuffle": "shuffle",
    "repeat": "repeat",
    "hand": "hand-index-thumb-fill",
    "clock": "clock",
    "journal": "journal-text",
    "palette": "palette-fill",
    "import": "box-arrow-in-down",
    "info": "info-circle-fill",
    "bell": "bell-fill",
    "bell_off": "bell-slash-fill",
    "film": "film",
    "link": "link-45deg",
    "key": "key-fill",
    "wrench": "wrench",
    "chat": "chat-dots-fill",
    "bug": "bug-fill",
    "file": "file-earmark-text",
    "numbers": "123",
    "recycle": "recycle",
    "sun": "sun-fill",
    "moon": "moon-fill",
    "pulse": "heart-pulse-fill",
    "layout": "layout-split",
    "return": "arrow-return-left",
    "sort": "arrow-down-up",
    "sprout": "tree-fill",
    "arrow_up": "arrow-up",
    "crash": "exclamation-octagon-fill",
    "window": "window",
    "play_pause": "play-btn-fill",
    "scroll": "file-earmark-richtext",
}

# Icons Bootstrap does not have, drawn here in the same 16-grid, same solid
# weight. Kept in this file so a regeneration doesn't wipe them.
EXTRA = {
    # The Paso Doble's bull: the one dance whose glyph the app has always been
    # recognised by, and there is no horned animal in Bootstrap Icons. This is
    # the 🐂 emoji itself — Twemoji's ox (CC-BY 4.0, see ICONS-LICENSE.txt),
    # flattened to one colour: body and horn as solid shapes, the eye punched
    # out with evenodd so it takes the panel colour instead of a hard-coded
    # white. Drawing one by hand never read as the animal; this does, and it is
    # the silhouette the user already knows. The viewBox is shifted down 4.5
    # units to centre the artwork, which sits in the bottom 3/4 of Twemoji's
    # 36-grid.
    "bull": ("0 4.5 36 36",
             # body, four legs and tail in one path; the last subpath is the eye
             '<path fill-rule="evenodd" d="M33.912 14.37C33.588 12.602 31.976 11 '
             '30 11H9c-1 0-5.325.035-6 2L.691 19.305C.016 21.27 1 24.087 3.027 '
             '24.087c1.15 0 2.596-.028 3.998-.052C10.016 28.046 12.898 36 14 36c'
             '.849 0 1.572-3.414 1.862-6h11.25c.234 2.528.843 6 1.888 6 .954 0 '
             '2.977-4.301 4.136-10.917.431-1.901.726-4.418.824-7.647.024.172.04'
             '.356.04.564v9c0 .553.447 1 1 1s1-.447 1-1v-9c0-1.807-.749-3.053-2'
             '.088-3.63zM7.5 16a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0z"/>'
             # the near horn, sweeping up off the muzzle
             '<path d="M10 12c-2 2-4.791-1-7-1-2.209 0-3-.434-3-.969 0-.535 1.791'
             '-.969 4-.969S12 10 10 12z"/>'),
}


def body_of(svg: str) -> str:
    """The drawable content of a Bootstrap icon, normalised for recolouring."""
    inner = svg.split(">", 1)[1].rsplit("</svg>", 1)[0]
    inner = re.sub(r"<!--.*?-->", "", inner, flags=re.S)
    inner = re.sub(r'\s+fill="currentColor"', "", inner)
    return " ".join(inner.split())


def main():
    out, missing = {}, []
    for name, bi in sorted(WANT.items()):
        try:
            with urllib.request.urlopen(BASE.format(bi), timeout=20) as r:
                svg = r.read().decode("utf-8")
        except Exception as exc:
            missing.append(f"{name} ({bi}): {exc}")
            continue
        vb = re.search(r'viewBox="([^"]+)"', svg)
        out[name] = (bi, vb.group(1) if vb else "0 0 16 16", body_of(svg))
    for name, (vb, body) in EXTRA.items():
        out[name] = ("drawn for this app — not a Bootstrap icon", vb, body)
    out = dict(sorted(out.items()))
    if missing:
        print("MISSING:")
        for m in missing:
            print("  ", m)
    print(f"got {len(out)}/{len(WANT)}")
    if missing:
        sys.exit(1)
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        fh.write(HEADER)
        for name, (bi, vb, body) in out.items():
            # The bodies quote their attributes with ", so they go into
            # single-quoted Python strings — no escaping, still readable.
            assert "'" not in body, name
            fh.write(f'    # {bi}\n    "{name}": ("{vb}",\n')
            for chunk in wrap(body):
                fh.write(f"     '{chunk}'\n")
            fh.write("     ),\n")
        fh.write("}\n")
    print("wrote", sys.argv[1])


def wrap(s: str, width: int = 88):
    out, line = [], ""
    for tok in s.split(" "):
        if line and len(line) + len(tok) + 1 > width:
            out.append(line + " ")
            line = tok
        else:
            line = f"{line} {tok}".strip()
    if line:
        out.append(line)
    return out


HEADER = '''# -*- coding: utf-8 -*-
"""The app's icon artwork: Bootstrap Icons, embedded as SVG bodies.

Generated — do not edit by hand. Regenerate with the script this file was
built by (tools/make_iconset.py) if an icon has to be added.

Bootstrap Icons © 2019 The Bootstrap Authors, MIT licensed. The full licence
text is in ICONS-LICENSE.txt next to this file. The bodies are stored rather
than shipped as .svg files so a frozen build needs no data folder, and their
`fill="currentColor"` is stripped so `shared.icons` can paint them in any colour.

Each entry is (viewBox, body). The Bootstrap name is in the comment above it —
keep it, that is what makes this file regenerable.
"""

SVG = {
'''

if __name__ == "__main__":
    main()
