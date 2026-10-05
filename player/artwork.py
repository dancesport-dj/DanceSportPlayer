"""🖼 Cover art for the player card.

Same fallback chain as the iPad app, one step longer at the front because a
tournament playlist can carry its own picture: the playlist's image if the .m3u
names one (or one lies beside it), the track's embedded cover otherwise, and a
coloured tile with a ♪ when there is neither — so the card never collapses just
because a file has no artwork.

Results are memoized, including "this one has none": the card asks again on
every track change, and re-reading an ID3 tag mid-tournament is wasted work.
"""
import logging
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)

from planner.playlist_text import PlaylistEncodingError, read_playlist_text

log = logging.getLogger("dancesport.gui.artwork")

# Cover files sitting next to a playlist or a track, in the order players look.
_ART_STEMS = ("cover", "folder", "front", "albumart", "artwork")
_ART_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
# Playlist tags that name a picture. #EXTIMG is the common one; the other two
# turn up in lists exported by media servers.
_ART_TAGS = ("#EXTIMG:", "#EXTALBUMARTURL:", "#EXTART:")

_cache: dict = {}       # (kind, path, size) → QPixmap
_no_art: set = set()    # files already known to carry no cover


def _beside(path: Path) -> Path | None:
    """A cover image next to `path`: same name first, then the usual names."""
    folder = path.parent
    for ext in _ART_EXTS:
        cand = folder / (path.stem + ext)
        if cand.exists():
            return cand
    for stem in _ART_STEMS:
        for ext in _ART_EXTS:
            cand = folder / (stem + ext)
            if cand.exists():
                return cand
    return None


def playlist_art(m3u: Path | None) -> Path | None:
    """The image a whole playlist stands for — a picture tag inside the .m3u,
    or an image file next to it."""
    if not m3u:
        return None
    m3u = Path(m3u)
    try:
        for line in read_playlist_text(m3u)[0].splitlines():
            line = line.strip()
            for tag in _ART_TAGS:
                if line.upper().startswith(tag):
                    ref = line[len(tag):].strip()
                    if not ref:
                        continue
                    cand = Path(ref)
                    if not cand.is_absolute():
                        cand = m3u.parent / ref
                    if cand.exists():
                        return cand
    except (OSError, PlaylistEncodingError) as exc:
        log.debug("🖼 Playlist artwork unreadable\nfile: %s\nerror: %s", m3u, exc)
        return None
    return _beside(m3u)


def embedded_art(track: Path | None) -> bytes | None:
    """The cover stored inside the audio file itself (ID3 APIC, MP4 covr,
    FLAC picture block)."""
    if not track:
        return None
    try:
        from mutagen import File as MutagenFile
        f = MutagenFile(str(track))
    except Exception as exc:
        log.debug("🖼 Cover unreadable\nfile: %s\nerror: %s", track, exc)
        return None
    if f is None:
        return None
    for pic in getattr(f, "pictures", None) or []:
        return pic.data
    tags = getattr(f, "tags", None)
    if tags is None:
        return None
    for key in list(tags.keys()):
        if str(key).startswith("APIC"):
            return tags[key].data
        if str(key) == "covr" and tags[key]:
            return bytes(tags[key][0])
    return None


def placeholder(size: int, key: str) -> QPixmap:
    """The art-less tile: a colour derived from the name, so the same title
    always gets the same one, with a ♪ on it (the iPad app's stand-in)."""
    hue = (abs(hash(key)) % 360) / 360.0
    top = QColor.fromHsvF(hue, 0.55, 0.80)
    bottom = QColor.fromHsvF(hue, 0.55, 0.50)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, top)
    grad.setColorAt(1.0, bottom)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.10, size * 0.10)
    p.fillPath(path, grad)
    f = QFont()
    f.setPixelSize(int(size * 0.5))
    p.setFont(f)
    p.setPen(QColor("#ffffff"))
    p.drawText(QRectF(0, 0, size, size), int(Qt.AlignmentFlag.AlignCenter), "♪")
    p.end()
    return pm


def _rounded(pm: QPixmap, size: int) -> QPixmap:
    """Scale to a square and round the corners, like the player's cover."""
    scaled = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                       Qt.TransformationMode.SmoothTransformation)
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.10, size * 0.10)
    p.setClipPath(path)
    p.drawPixmap(int((size - scaled.width()) / 2),
                 int((size - scaled.height()) / 2), scaled)
    p.end()
    return out


def cover(track: Path | None, playlist: Path | None,
          size: int) -> QPixmap:
    """The picture to show for `track` played out of `playlist`.

    Playlist image first — a tournament list with its own artwork means that
    picture, not the cover of whichever CD the track came off. Never returns a
    null pixmap: the coloured tile is the last step."""
    for kind, src in (("list", playlist_art(playlist)), ("track", track)):
        if src is None:
            continue
        key = (kind, str(src), size)
        hit = _cache.get(key)
        if hit is not None:
            return hit
        if str(src) in _no_art:
            continue
        pm = QPixmap()
        if kind == "list":
            pm.load(str(src))
        else:
            data = embedded_art(src)
            if data:
                pm.loadFromData(data)
        if pm.isNull():
            _no_art.add(str(src))
            continue
        out = _rounded(pm, size)
        _cache[key] = out
        return out
    return placeholder(size, Path(track).stem if track else "—")
