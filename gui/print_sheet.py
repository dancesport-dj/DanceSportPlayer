"""🖨 The printed running order's HTML — one deck, its rounds as tables.

Split off the print mixin: the sheet is built from a deck's name and its song
rows alone, so it is a plain function, tested without a window; the mixin
keeps choosing what to print and writing the PDF.
"""
import html
import time

from gui.common import _fmt_track_secs
from planner.terms import dance_name


def deck_print_html(name: str, metas: list) -> list:
    """Build the HTML parts for one deck (title + per-round tables)."""
    esc = html.escape
    total_secs = sum(int(getattr(m.entry, "duration", 0) or 0) for m in metas)
    parts = [
        f"<h1 style='margin-bottom:0;'>{esc(name)}</h1>",
        f"<p style='color:#555;'>{time.strftime('%d.%m.%Y %H:%M')} · "
        f"{len(metas)} songs"
        + (f" · ~{_fmt_track_secs(total_secs)} play time" if total_secs else "")
        + "</p>"]
    cur_round: object = object()   # sentinel ≠ any round name (incl. "")
    open_table = False
    for m in metas:
        rn = m.round_name or ""
        if rn != cur_round:
            if open_table:
                parts.append("</table>")
            cur_round = rn
            if rn:
                parts.append("<h2 style='background:#dbe6f4; padding:3px;'>"
                             f"{esc(rn.upper())}</h2>")
            parts.append(
                "<table border=1 cellspacing=0 cellpadding=4 width='100%'>"
                "<tr style='background:#eef2f8;'>"
                "<th align=left width='13%'>Dance</th>"
                "<th align=left width='9%'>Heat</th>"
                "<th align=left width='18%'>Artist</th>"
                "<th align=left>Title</th>"
                "<th align=left width='18%'>Album</th>"
                "<th width='7%'>BPM</th><th width='9%'>Length</th></tr>")
            open_table = True
        e = m.entry
        dn = dance_name(m.dance, m.dance or "")
        heat = (f"↳ backup {m.backup_n or ''}".rstrip() if m.backup
                else (f"Heat {m.h_idx + 1}" if m.multi else ""))
        secs = int(getattr(e, "duration", 0) or 0)
        artist = getattr(e, "tag_artist", "") or ""
        album = getattr(e, "tag_album", "") or ""
        parts.append(
            f"<tr><td>{esc(dn)}</td><td>{esc(heat)}</td>"
            f"<td>{esc(artist)}</td>"
            f"<td>{esc(e.title or '')}</td>"
            f"<td>{esc(album)}</td>"
            f"<td align=center>{'T' + str(e.bpm) if e.bpm else ''}</td>"
            f"<td align=center>{_fmt_track_secs(secs) if secs else ''}</td></tr>")
    if open_table:
        parts.append("</table>")
    return parts
