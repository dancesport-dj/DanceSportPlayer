#!/usr/bin/env python3
"""Build docs/manual/manual.html — the whole user manual on one page.

The index (README.md) comes first, then the numbered chapters in file-name
order, and the page is named after the index's heading. Links between the
chapters become jumps inside the page
(`13-export-print-paths.md#-usb-export` → `#13-export-print-paths__-usb-export`),
so the page reads like the Markdown files do on GitHub. The screenshots stay
in `img/` next to it, so the HTML works wherever the `docs/manual` folder goes.

Only the Markdown the manual uses is understood: headings, paragraphs,
nested lists, tables, fenced code, images, links, **bold**, *italic* and
`code`. Standard library only — the app has no Markdown dependency.

Run:  .venv\\Scripts\\python.exe -m tools.build_manual_html [manual_dir]

Without a folder it builds the player's manual in docs/manual and its German
translation in docs/manual/de. The planner's manual, kept on this machine
only, is built with docs/manual-planner.
"""
import html
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL_DIR = ROOT / "docs" / "manual"
OUT_FILE = MANUAL_DIR / "manual.html"
MANUALS = (MANUAL_DIR, MANUAL_DIR / "de")
INDEX_ID = "index"

# The builder's own words. A manual in a folder named "de" is German, every
# other one English.
WORDS = {
    "en": {"manual": "User Manual", "overview": "Overview", "contents": "Contents",
           "top": "↑ Index", "version": "Version"},
    "de": {"manual": "Benutzerhandbuch", "overview": "Übersicht", "contents": "Inhalt",
           "top": "↑ Übersicht", "version": "Version"},
}

log = logging.getLogger("dancesport.tools.manual")

_LIST_RE = re.compile(r"^( *)([-*]|\d+\.) +(.*)$")
_FENCE_RE = re.compile(r"^( *)```")
_HEADING_RE = re.compile(r"^(#{1,6}) +(.*)$")
_TABLE_SEP_RE = re.compile(r"^\|? *:?-+:? *(\| *:?-+:? *)*\|? *$")
_IMAGE_LINE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")


def language(manualDir: Path) -> str:
    return "de" if manualDir.name == "de" else "en"


def chapterFiles(manualDir: Path = MANUAL_DIR) -> list[Path]:
    """README first, then the numbered chapters in order."""
    chapters = sorted(p for p in manualDir.glob("[0-9][0-9]-*.md"))
    return [manualDir / "README.md"] + chapters


def sectionId(mdName: str) -> str:
    """The page anchor of a whole chapter file."""
    return INDEX_ID if mdName == "README.md" else Path(mdName).stem


def slugify(text: str) -> str:
    """GitHub's heading anchor: lower case, punctuation and emoji dropped,
    spaces turned into hyphens (so '🧳 USB export' → '-usb-export')."""
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def rewriteHref(href: str, current: str) -> str:
    """Point a link at the right place on the one page."""
    if re.match(r"^[a-z]+:", href):
        return href
    target, _, frag = href.partition("#")
    if not target:
        return f"#{sectionId(current)}__{frag}"
    if target.endswith(".md") and "/" not in target:
        sid = sectionId(target)
        return f"#{sid}__{frag}" if frag else f"#{sid}"
    return href


def renderInline(text: str, current: str) -> str:
    """Code spans, images, links, bold and italic — everything else escaped."""
    codes = []

    def keepCode(m):
        codes.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keepCode, text)
    text = html.escape(text, quote=False)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f'<img src="{m.group(2)}" alt="{html.escape(m.group(1))}">',
        text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{rewriteHref(m.group(2), current)}">{m.group(1)}</a>',
        text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def splitRow(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def isBlockStart(lines: list[str], i: int) -> bool:
    line = lines[i]
    if _HEADING_RE.match(line) or _FENCE_RE.match(line) or _LIST_RE.match(line):
        return True
    return (line.startswith("|") and i + 1 < len(lines)
            and bool(_TABLE_SEP_RE.match(lines[i + 1])))


def dedent(lines: list[str], width: int) -> list[str]:
    return [ln[width:] if ln[:width].strip() == "" else ln.lstrip() for ln in lines]


def renderBlocks(lines: list[str], current: str, headings: list[tuple]) -> str:
    """Render a run of Markdown lines; list items recurse with their body."""
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        fence = _FENCE_RE.match(line)
        if fence:
            indent = len(fence.group(1))
            body = []
            i += 1
            while i < len(lines) and not _FENCE_RE.match(lines[i]):
                body.append(lines[i][indent:] if lines[i][:indent].strip() == ""
                            else lines[i])
                i += 1
            i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(body))}</code></pre>")
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            label = renderInline(text, current)
            if level == 1:   # the chapter's <section> carries its id
                headings.append((1, sectionId(current), label))
                out.append(f"<h1>{label}</h1>")
            else:
                hid = f"{sectionId(current)}__{slugify(text)}"
                headings.append((level, hid, label))
                out.append(f'<h{level} id="{hid}">{label}</h{level}>')
            i += 1
            continue

        if line.startswith("|") and i + 1 < len(lines) and _TABLE_SEP_RE.match(lines[i + 1]):
            head = splitRow(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(splitRow(lines[i]))
                i += 1
            th = "".join(f"<th>{renderInline(c, current)}</th>" for c in head)
            body = "".join(
                "<tr>" + "".join(f"<td>{renderInline(c, current)}</td>" for c in row)
                + "</tr>" for row in rows)
            out.append(f'<div class="table"><table><thead><tr>{th}</tr></thead>'
                       f"<tbody>{body}</tbody></table></div>")
            continue

        item = _LIST_RE.match(line)
        if item:
            html_list, i = renderList(lines, i, current, headings)
            out.append(html_list)
            continue

        para = [line.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not isBlockStart(lines, i):
            para.append(lines[i].strip())
            i += 1
        image = _IMAGE_LINE_RE.match(" ".join(para))
        if image:
            alt, src = image.groups()
            out.append(f'<figure><img src="{src}" alt="{html.escape(alt)}">'
                       f"<figcaption>{html.escape(alt)}</figcaption></figure>")
        else:
            out.append(f"<p>{renderInline(' '.join(para), current)}</p>")
    return "\n".join(out)


def renderList(lines: list[str], i: int, current: str,
               headings: list[tuple]) -> tuple[str, int]:
    """One list starting at line `i`; returns its HTML and the next line."""
    first = _LIST_RE.match(lines[i])
    indent = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    start = int(first.group(2)[:-1]) if ordered else 1
    items = []
    while i < len(lines):
        m = _LIST_RE.match(lines[i])
        if not m or len(m.group(1)) != indent or m.group(2)[0].isdigit() != ordered:
            break
        width = indent + len(m.group(2)) + 1
        body = [m.group(3)]
        i += 1
        while i < len(lines):
            ln = lines[i]
            if not ln.strip():
                nxt = next((x for x in lines[i + 1:] if x.strip()), "")
                if len(nxt) - len(nxt.lstrip()) > indent:
                    body.append("")
                    i += 1
                    continue
                break
            lead = len(ln) - len(ln.lstrip())
            if lead <= indent and (_LIST_RE.match(ln) or lead < indent or isBlockStart(lines, i)):
                break
            if lead <= indent and not _LIST_RE.match(ln):
                body.append(ln.strip())   # a lazy continuation line
            else:
                body.append(ln)
            i += 1
        items.append(dedent(body[:1], 0) + dedent(body[1:], width))
    parts = []
    for body in items:
        inner = renderBlocks(body, current, headings)
        if "" not in body and inner.startswith("<p>"):   # a tight item
            inner = inner[3:].replace("</p>", "", 1)
        parts.append(f"<li>{inner}</li>")
    tag = "ol" if ordered else "ul"
    attr = f' start="{start}"' if ordered and start != 1 else ""
    return f"<{tag}{attr}>{''.join(parts)}</{tag}>", i


_CSS = """
:root { --fg:#1d232b; --muted:#5b6673; --bg:#fbfaf7; --line:#dcdfe3;
        --accent:#2f62c9; --code:#eef0f3; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e4e7eb; --muted:#9aa4b1; --bg:#16191d; --line:#343a42;
          --accent:#7aa5f5; --code:#23282e; } }
body { margin:0; background:var(--bg); color:var(--fg);
       font:16px/1.6 "Segoe UI", system-ui, -apple-system, sans-serif; }
main { max-width:960px; margin:0 auto; padding:24px 20px 80px; }
section { border-top:1px solid var(--line); padding-top:12px; margin-top:48px; }
section:first-child { border-top:none; margin-top:0; }
h1 { font-size:1.9em; line-height:1.25; }
h2 { font-size:1.4em; margin-top:1.8em; }
h3 { font-size:1.15em; margin-top:1.5em; }
a { color:var(--accent); }
code { background:var(--code); padding:1px 5px; border-radius:4px; font-size:.92em; }
pre { background:var(--code); padding:12px 14px; border-radius:6px; overflow-x:auto; }
pre code { padding:0; background:none; }
.table { overflow-x:auto; margin:1em 0; }
table { border-collapse:collapse; }
th, td { border:1px solid var(--line); padding:6px 10px; text-align:left;
         vertical-align:top; }
th { background:var(--code); }
figure { margin:1.2em 0; }
figure img, p img { max-width:100%; height:auto; border:1px solid var(--line);
                    border-radius:4px; }
figcaption { color:var(--muted); font-size:.9em; margin-top:4px; }
.top { position:fixed; right:16px; bottom:16px; background:var(--accent);
       color:#fff; text-decoration:none; padding:6px 12px; border-radius:18px;
       font-size:.9em; }
.toc { position:fixed; top:0; left:0; bottom:0; width:290px; overflow-y:auto;
       box-sizing:border-box; padding:18px 10px 40px 14px; font-size:14px;
       line-height:1.4; border-right:1px solid var(--line); background:var(--code); }
.toc .title { font-weight:600; margin:0 0 10px 6px; }
.toc ul { list-style:none; margin:0; padding:0; }
.toc ul ul { padding-left:14px; }
.toc a { display:block; padding:3px 6px; border-radius:4px; color:var(--fg);
         text-decoration:none; }
.toc a:hover { background:var(--line); }
.toc a.active { background:var(--accent); color:#fff; }
.toc summary { cursor:pointer; list-style:none; }
.toc summary::-webkit-details-marker { display:none; }
.toc summary a { font-weight:600; }
.toc details { margin-bottom:2px; }
.toc details:not([open]) > summary a::after { content:" ▸"; color:var(--muted); }
body.has-toc main { margin-left:max(290px, calc(50vw - 480px + 145px)); }
@media (max-width: 900px) {
  .toc { position:static; width:auto; max-height:45vh; border-right:none;
         border-bottom:1px solid var(--line); }
  body.has-toc main { margin-left:auto; } }
@media print {
  :root { --fg:#1d232b; --muted:#5b6673; --bg:#fff; --line:#dcdfe3;
          --accent:#2f62c9; --code:#eef0f3; }
  @page { margin:16mm 14mm; @bottom-center { content:counter(page); font:9pt "Segoe UI", system-ui, sans-serif; } }
  body { font-size:11pt; }
  .top { display:none; }
  .toc { position:static; width:auto; border:none; background:none; font-size:12pt;
         break-after:page; }
  .toc details > ul, .toc details:not([open]) > summary a::after { display:none; }
  .toc a.active { background:none; color:var(--fg); }
  body.has-toc main { margin:0; max-width:none; padding:0; }
  section { break-before:page; border-top:none; margin-top:0; }
  h1, h2, h3, p:has(+ figure), p:has(+ .table), p:has(+ ul) { break-after:avoid; }
  figure, pre, tr { break-inside:avoid; }
  /* A screenshot taller than this would leave the page before it half
     empty, or not fit a page at all and be cut off. */
  figure img { max-height:150mm; width:auto; } }
"""

# The printed manual only (buildPrintHtml): its cover and contents page.
_PRINT_CSS = """
main { max-width:none; margin:0; padding:0; }
@page { size:A4; }
@page :first { @bottom-center { content:none; } }
.cover { height:240mm; display:flex; flex-direction:column; justify-content:center;
         align-items:center; text-align:center; break-after:page; }
.cover .logo { width:40mm; height:auto; margin-bottom:12mm; }
.cover .product { font-size:34pt; font-weight:700; line-height:1.15; margin:0; }
.cover .kind { font-size:18pt; color:var(--muted); margin:4mm 0 0; }
.cover .version { font-size:12pt; color:var(--muted); margin:18mm 0 0; }
.contents { break-after:page; line-height:1.4; }
.contents ul { list-style:none; margin:0; padding:0; }
.contents a { display:flex; align-items:baseline; color:var(--fg); text-decoration:none; }
.contents .dots { flex:1; min-width:6mm; margin:0 2mm; border-bottom:1px dotted var(--muted); }
.contents .pg { min-width:7mm; text-align:right; }
.contents .l1 { font-weight:600; margin-top:3mm; break-after:avoid; }
.contents .l2 { padding-left:7mm; font-size:10pt; margin-top:.5mm; }
"""

_SCRIPT = """
const links = [...document.querySelectorAll('.toc a')];
const targets = links.map(a => document.getElementById(a.hash.slice(1)));
function spy() {
  let best = 0;
  targets.forEach((t, i) => { if (t && t.getBoundingClientRect().top < 90) best = i; });
  links.forEach((a, i) => a.classList.toggle('active', i === best));
  const box = links[best].closest('details');
  document.querySelectorAll('.toc details').forEach(d => { d.open = d === box; });
  const nav = document.querySelector('.toc');
  const a = links[best].getBoundingClientRect(), n = nav.getBoundingClientRect();
  if (a.top < n.top || a.bottom > n.bottom) nav.scrollTop += a.top - n.top - n.height / 3;
}
addEventListener('scroll', spy, {passive: true});
spy();
"""


def tocHtml(headings: list[tuple], words: dict = WORDS["en"]) -> str:
    """The sidebar: one fold per chapter with its ## and ### headings inside.
    The script unfolds the chapter being read and lights the heading on screen."""
    chapters = []
    for level, hid, label in headings:
        if level == 1:
            chapters.append((hid, words["overview"] if hid == INDEX_ID else label, []))
        elif level <= 3 and chapters:
            chapters[-1][2].append((level, hid, label))
    parts = [f'<nav class="toc"><p class="title">{words["manual"]}</p><ul>']
    for sid, label, subs in chapters:
        parts.append(f'<li><details><summary><a href="#{sid}">{label}</a></summary><ul>')
        inSub = False
        for level, hid, sub in subs:
            if level == 3 and not inSub and parts[-1].endswith("</li>"):
                parts[-1] = parts[-1][:-5] + "<ul>"   # nest under the ## before
                inSub = True
            elif level == 2 and inSub:
                parts.append("</ul></li>")
                inSub = False
            parts.append(f'<li><a href="#{hid}">{sub}</a></li>')
        if inSub:
            parts.append("</ul></li>")
        parts.append("</ul></details></li>")
    parts.append("</ul></nav>")
    return "".join(parts)


def renderManual(manualDir: Path) -> tuple[list[tuple], list[tuple[str, str]], str]:
    """Every heading, every chapter as (section id, body HTML), and the index's
    heading as plain text."""
    headings = []
    sections = []
    for md in chapterFiles(manualDir):
        lines = md.read_text(encoding="utf-8").splitlines()
        sections.append((sectionId(md.name), renderBlocks(lines, md.name, headings)))
    first = (manualDir / "README.md").read_text(encoding="utf-8").splitlines()[0]
    return headings, sections, first.lstrip("#").strip()


def buildHtml(manualDir: Path = MANUAL_DIR) -> tuple[str, list[str]]:
    """The page, and every internal link whose anchor does not exist."""
    headings, sections, heading = renderManual(manualDir)
    ids = {hid for _, hid, _ in headings}
    content = "\n".join(f'<section id="{sid}">\n{body}\n</section>' for sid, body in sections)
    broken = sorted({h for h in re.findall(r'href="#([^"]+)"', content) if h not in ids})
    title = html.escape(heading)
    lang = language(manualDir)
    page = (f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{title}</title>\n<style>{_CSS}</style>\n</head>\n<body class=\"has-toc\">\n"
            f"{tocHtml(headings, WORDS[lang])}\n<main>\n{content}\n</main>\n"
            f'<a class="top" href="#index">{WORDS[lang]["top"]}</a>\n'
            f"<script>{_SCRIPT}</script>\n</body>\n</html>\n")
    return page, broken


def isNavLine(para: str) -> bool:
    """A paragraph that only steps between chapters ("Manual index · previous:
    …", "Next: …"): every link goes to a chapter's top and at most three words
    stand outside them. A sentence that merely points at a chapter has more."""
    links = re.findall(r'<a href="#([^"]*)">', para)
    if not links or any("__" in h or not (h == INDEX_ID or h[:1].isdigit()) for h in links):
        return False
    outside = re.sub(r"<[^>]+>", "", re.sub(r"<a [^>]*>.*?</a>", "", para, flags=re.S))
    return len(re.findall(r"\w+", outside)) <= 3


def printBody(sid: str, body: str, words: dict = WORDS["en"]) -> str:
    """A chapter as it is printed: without the lines that step between the
    web page's chapters, and without the note that points at that web page."""
    body = re.sub(r'<p>(?:(?!</p>).)*href="manual\.html"(?:(?!</p>).)*</p>\n?', "",
                  body, flags=re.S)
    body = re.sub(r"(</h1>\n)(<p>.*?</p>)\n",
                  lambda m: m.group(1) if isNavLine(m.group(2)) else m.group(0),
                  body, count=1, flags=re.S)
    last = re.search(r"\n(<p>(?:(?!<p>).)*</p>)$", body, flags=re.S)
    if last and isNavLine(last.group(1)):
        body = body[:last.start()]
    if sid == INDEX_ID:
        body = re.sub(r"<h1>.*?</h1>", f"<h1>{words['overview']}</h1>", body, count=1)
    return body


def contentsHtml(headings: list[tuple], pages: dict[str, int],
                 words: dict = WORDS["en"]) -> str:
    """The contents page: the chapters and their ## sections, each with a
    dotted leader to its page."""
    rows = []
    for level, hid, label in headings:
        if level > 2:
            continue
        if hid == INDEX_ID:
            label = words["overview"]
        rows.append(f'<li class="l{level}"><a href="#{hid}"><span class="label">{label}</span>'
                    f'<span class="dots"></span><span class="pg">{pages.get(hid, "")}</span></a></li>')
    return (f'<nav class="contents"><h1>{words["contents"]}</h1>'
            f'<ul>{"".join(rows)}</ul></nav>')


def buildPrintHtml(manualDir: Path, version: str, pages: dict[str, int] | None = None) -> str:
    """The page the PDF is printed from: a cover with the app's name, the
    manual's and the version, a contents page, then the chapters, each on a
    new page. `pages` maps an anchor to its page in an earlier print of this
    same page; without it the contents leaves the numbers blank, which takes
    the same room, so the pages stay where they are."""
    headings, sections, heading = renderManual(manualDir)
    lang = language(manualDir)
    words = WORDS[lang]
    product, _, kind = heading.partition(" — ")
    logo = ROOT / "icon.png"
    cover = ['<div class="cover">']
    if logo.is_file():
        cover.append(f'<img class="logo" src="{logo.as_uri()}" alt="">')
    cover.append(f'<p class="product">{html.escape(product)}</p>')
    if kind:
        cover.append(f'<p class="kind">{html.escape(kind)}</p>')
    cover.append(f'<p class="version">{words["version"]} {html.escape(version)}</p></div>')
    content = "\n".join(f'<section id="{sid}">\n{printBody(sid, body, words)}\n</section>'
                        for sid, body in sections)
    return (f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
            f"<title>{html.escape(heading)}</title>\n<style>{_CSS}{_PRINT_CSS}</style>\n"
            f"</head>\n<body>\n{''.join(cover)}\n{contentsHtml(headings, pages or {}, words)}\n"
            f"<main>\n{content}\n</main>\n</body>\n</html>\n")


def main(argv=None) -> int:
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = sys.argv[1:] if argv is None else argv
    if not args:
        return max([main([str(d)]) for d in MANUALS])
    manualDir = Path(args[0]).resolve()
    outFile = manualDir / OUT_FILE.name
    page, broken = buildHtml(manualDir)
    missing = [src for src in re.findall(r'<img src="([^"]+)"', page)
               if not (manualDir / src).is_file()]
    outFile.write_text(page, encoding="utf-8")
    log.info("📘 Manual written\n"
             "file: %s\n"
             "size: %d KB", outFile, len(page.encode("utf-8")) // 1024)
    for anchor in broken:
        log.error("🔗 Broken link: #%s", anchor)
    for src in missing:
        log.error("🖼️ Missing image: %s", src)
    return 1 if broken or missing else 0


if __name__ == "__main__":
    sys.exit(main())
