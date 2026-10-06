"""Render the picture ⚙ Settings shows for each theme: a crop of the real main
window, with a small example playlist, under that theme.

    py -m tools.theme_previews [key ...]      (from the repo root)

Writes assets/themes/<key>.png for the classic light / dark and every 🎨 look
(shared/looks.py), or only for the keys given. Each theme renders in its own
process: the theme is applied once at start-up, as in the app, and the shared
table colours are shaded in place — a second theme in the same process would
shade them twice.

The artist and title cells are blurred afterwards, as in the manual (needs
Pillow). Run it on Windows with the real platform plugin; offscreen Qt measures
text far too wide and the crops come out cramped.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
# The part of the 1500×900 main window the preview shows: the toolbar, the
# planning column's top and deck A with its title strip and table.
CROP = (0, 0, 760, 430)


def _render(key: str) -> None:
    os.environ["DANCEPLAYLIST_STATE_DIR"] = tempfile.mkdtemp(prefix="dp_preview_")
    sys.path.insert(0, str(ROOT))
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtWidgets import QApplication

    settings = {"theme": key, "app_mode": "both", "language": "de"}
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    from shared import theme
    theme.apply_settings(settings)
    theme.install_stylesheet_hook()
    theme.sync_shared_colors()
    theme.apply_app(app)
    from shared import look_icons
    look_icons.install()
    from planner import i18n
    i18n.apply_settings(settings)
    i18n.install_text_hook()

    import dancesport_gui
    from planner.models import MusicEntry, RoundConfig
    from tests.qt_test_support import StubLoader

    with mock.patch.object(dancesport_gui, "LibraryLoader", StubLoader), \
            mock.patch.object(dancesport_gui, "load_settings",
                              lambda *a, **k: dict(settings)):
        win = dancesport_gui.MainWindow()
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)

    songs = (("Andrea Bocelli", "Vivo Per Lei", "LW", 29, 180, 12),
             ("Michael Bublé", "Feeling Good", "LW", 28, 172, 3),
             ("Jessie J", "Bang Bang", "TG", 32, 165, 0),
             ("Astor Piazzolla", "Libertango", "TG", 33, 150, 8),
             ("Ed Sheeran", "Perfect", "WW", 59, 175, 21),
             ("Sia", "Never Give Up", "SF", 29, 158, 1),
             ("Bruno Mars", "Treasure", "QS", 51, 162, 5))
    by_dance = {}
    for artist, title, dance, bpm, length, pop in songs:
        by_dance.setdefault(dance, []).append(MusicEntry(
            path=Path(rf"C:\music\{artist} - {title}.mp3"), title=title,
            dance=dance, bpm=bpm, duration=length, popularity=pop,
            tag_artist=artist))
    dances = ["LW", "TG", "WW", "SF", "QS"]
    heat1 = [by_dance[d][0] for d in dances]
    heat2 = [by_dance[d][-1] for d in dances]
    rounds = [RoundConfig(name="Vorrunde", heats=2, tier="early"),
              RoundConfig(name="Endrunde", heats=1, tier="final")]
    win._tableA.load({"Vorrunde": [heat1, heat2], "Endrunde": [heat2]},
                     dances, rounds, "S", play_cb=lambda *a: None,
                     suggester=None, use_timbre=False, style="Standard")
    win._set_active_table(win._tableA)
    win.resize(1500, 900)
    win.show()
    for _ in range(30):
        app.processEvents()
    out = ROOT / "assets" / "themes" / f"{key}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    win.grab(QRect(*CROP)).save(str(out), "PNG")
    _blur_names(out, _name_cells(win, win._tableA), win.devicePixelRatioF())
    print(f"wrote {out.relative_to(ROOT)}", flush=True)
    # The app's threads and hooks make a clean Qt shutdown slow and noisy;
    # the picture is written, nothing else is left to do.
    os._exit(0)


def _name_cells(win, table) -> list:
    """The artist and title cells of every song row, in window coordinates.
    Round and dance header rows span the table and are left readable."""
    from shared.columns import _COL_ARTIST, _COL_TITLE

    cells = []
    for row in range(table.rowCount()):
        if table.columnSpan(row, 0) > 1:
            continue
        for col in (_COL_ARTIST, _COL_TITLE):
            rect = table.visualRect(table.model().index(row, col))
            if rect.isValid():
                top_left = table.viewport().mapTo(win, rect.topLeft())
                cells.append(rect.translated(top_left - rect.topLeft()))
    return cells


def _blur_names(path: Path, cells: list, scale: float) -> None:
    """Blur the song names, as in the manual's screenshots: the example songs
    are real ones, and a preview should not advertise them."""
    from PIL import Image, ImageFilter

    img = Image.open(path)
    img.load()
    x0, y0, x1, y1 = CROP[0], CROP[1], CROP[0] + CROP[2], CROP[1] + CROP[3]
    for cell in cells:
        left, top = max(cell.left(), x0), max(cell.top(), y0)
        right, bottom = min(cell.right() + 1, x1), min(cell.bottom() + 1, y1)
        if right <= left or bottom <= top:
            continue
        box = tuple(round(v * scale) for v in
                    (left - x0, top - y0, right - x0, bottom - y0))
        region = img.crop(box)
        for _ in range(2):
            region = region.filter(ImageFilter.GaussianBlur(7))
        img.paste(region, box)
    img.save(path, "PNG")


def main(argv: list[str]) -> int:
    if argv[:1] == ["--one"]:
        _render(argv[1])
        return 0
    from shared import theme
    keys = argv or list(theme._THEMES)
    env = dict(os.environ, QT_QPA_PLATFORM="windows") if sys.platform == "win32" \
        else dict(os.environ)
    failed = []
    for key in keys:
        done = subprocess.run([sys.executable, "-m", "tools.theme_previews",
                               "--one", key], cwd=ROOT, env=env)
        if done.returncode != 0:
            failed.append(key)
    if failed:
        print("Not rendered: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
