"""The JSON files the desk and the evening both write: the settings and the
cartwall pads. Plus where the master player is docked, the one setting the
evening reads that needs interpreting.

Reading the settings with their per-machine defaults (gui.dialogs.load_settings)
stays with the desk, which owns the defaults; this module is only the file.
"""
from planner.store import JsonStore

SETTINGS = JsonStore("gui_settings.json")

# 🎛 Cartwall pads. Its own file, not the autosave envelope: that one is rotated
# and snapshotted for undo, and a pad assignment must not be undone by Ctrl+Z on
# an unrelated deck edit. Pads are equipment, not playlist content.
CARTWALL = JsonStore("cartwall.json", note="starting with empty pads")

# 🆘 The title on air: deck, row and position, rewritten while it plays and
# removed by every stop and a clean quit. Found at a start, the last run
# crashed (player.window.main_load offers to pick up there).
ON_AIR = JsonStore("on_air.json", note="no crash resume offered")


_on_failure = None   # 💾 told when a settings save does not land


def report_settings_failures(callback) -> None:
    """Who hears of a settings save that did not land: the window installs
    gui.settings_save_report, which tells the user. None: nobody."""
    global _on_failure
    _on_failure = callback


def save_settings(s: dict, *, report: bool = True) -> bool:
    """False when the file did not land (see JsonStore.write). Then the hook
    above is told, unless the caller shows a box of its own (report=False):
    some fifty callers never look at the result."""
    ok = SETTINGS.write(s)
    if not ok and report and _on_failure is not None:
        _on_failure()
    return ok


PLAYER_LAYOUTS = ("panel", "wide")
DEFAULT_PLAYER_LAYOUT = "panel"


def player_layout_of(settings: dict) -> str:
    """Where the master player is docked, or the panel for anything
    unrecognised (a settings file written before the option existed)."""
    choice = str(settings.get("player_layout") or "").strip().lower()
    return choice if choice in PLAYER_LAYOUTS else DEFAULT_PLAYER_LAYOUT


def load_cartwall_file():
    """The parsed cartwall.json, or None when there is nothing readable there.
    Interpreting it — including refusing to overwrite a newer version — is
    planner.playing.cartwall.load_doc's job."""
    return CARTWALL.read()


def save_cartwall_file(doc: dict) -> None:
    CARTWALL.write(doc)
