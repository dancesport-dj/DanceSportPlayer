#!/usr/bin/env python3
"""Build docs/manual/manual.pdf and docs/manual/de/manual.pdf — the manual
in English and German, for the downloads and the ❔ menu.

Builds manual.html first (tools/build_manual_html), then prints the
manual's print page (build_manual_html.buildPrintHtml: a cover with the
version, a contents page, every chapter on a new page) with a headless
Chrome, Chromium or Edge. Twice: the first print tells on which page each
chapter and section landed (Chrome lists every anchor in the PDF's /Dests),
the second carries those numbers in its contents. No header or footer from
the browser: it would print the file's path, and with it the build
machine's user folder.

A PDF newer than every chapter, image and this tool is kept as it is: CI
prints it once and hands it to the build jobs, whose build scripts then only
copy it.

The browser is $DANCEPLAYLIST_CHROME when set, else the first one found on
PATH or in its usual install folder. GitHub's runners all have Chrome.

Run:  .venv\\Scripts\\python.exe -m tools.build_manual_pdf [manual_dir [out.pdf]]

Without a folder it builds both languages.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

from planner.version import build_version
from tools import build_manual_html

PDF_NAME = "manual.pdf"
PRINT_PAGE = "manual.print.html"
BROWSER_ENV = "DANCEPLAYLIST_CHROME"
BROWSER_NAMES = ("chrome", "google-chrome", "google-chrome-stable", "chromium",
                 "chromium-browser", "msedge", "microsoft-edge")
BROWSER_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)

log = logging.getLogger("dancesport.tools.manual")


def findBrowser() -> str | None:
    """The browser to print with, or None."""
    chosen = os.environ.get(BROWSER_ENV, "").strip()
    if chosen:
        return chosen
    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return next((p for p in BROWSER_PATHS if Path(p).is_file()), None)


def printCommand(browser: str, page: Path, pdf: Path, profile: Path) -> list[str]:
    # A profile of its own: the user's Chrome may be open, and its profile
    # would sign in and sync while the page prints. The outline is the PDF's
    # bookmarks, made from the headings.
    return [browser, "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", f"--user-data-dir={profile}",
            "--no-pdf-header-footer", "--generate-pdf-document-outline",
            f"--print-to-pdf={pdf}", page.as_uri()]


def pdfObject(data: bytes, num: int) -> bytes:
    m = re.search(rb"(?<!\d)%d 0 obj(.*?)endobj" % num, data, re.S)
    return m.group(1) if m else b""


def pdfName(raw: bytes) -> str:
    """A PDF name without its slash; #xx stands for one byte. Chrome names
    each destination after the link's fragment, percent-encoded."""
    return unquote(re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]),
                          raw).decode("utf-8", "replace"))


def destPages(data: bytes) -> dict[str, int]:
    """Anchor id -> page number (from 1), from the named destinations Chrome
    writes into the catalog. Empty when the PDF has none."""
    catalog = re.search(rb"/Type /Catalog(.*?)>>", data, re.S)
    dests = catalog and re.search(rb"/Dests (\d+) 0 R", catalog.group(1))
    root = catalog and re.search(rb"/Pages (\d+) 0 R", catalog.group(1))
    if not (dests and root):
        return {}
    order = []

    def walk(num):
        kids = re.search(rb"/Kids \[([^\]]*)\]", pdfObject(data, num))
        if kids:
            for kid in re.findall(rb"(\d+) 0 R", kids.group(1)):
                walk(int(kid))
        else:
            order.append(num)

    walk(int(root.group(1)))
    index = {num: i + 1 for i, num in enumerate(order)}
    entries = re.findall(rb"/([^\s/\[]+) \[(\d+) 0 R", pdfObject(data, int(dests.group(1))))
    return {pdfName(name): index[int(ref)] for name, ref in entries if int(ref) in index}


def isCurrent(manualDir: Path, outFile: Path) -> bool:
    """True when the PDF is newer than everything it is printed from."""
    if not outFile.is_file():
        return False
    sources = [*manualDir.glob("*.md"), *(build_manual_html.MANUAL_DIR / "img").glob("*"),
               Path(build_manual_html.__file__), Path(__file__)]
    return outFile.stat().st_mtime >= max(p.stat().st_mtime for p in sources)


def printOnce(browser: str, page: Path, pdf: Path) -> bool:
    """Print the page to the PDF; False (and why, in the log) when none came."""
    pdf.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        cmd = printCommand(browser, page, pdf.resolve(), Path(profile))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if pdf.is_file() and pdf.stat().st_size:
        return True
    pdf.unlink(missing_ok=True)
    log.error("📕 The browser wrote no PDF\n"
              "browser: %s\n"
              "exit code: %s\n"
              "%s", browser, result.returncode, result.stderr.strip()[-2000:])
    return False


def buildPdf(manualDir: Path, outFile: Path) -> int:
    if isCurrent(manualDir, outFile):
        log.info("📕 Manual PDF up to date\n"
                 "file: %s", outFile)
        return 0
    code = build_manual_html.main([str(manualDir)])
    if code:
        return code
    browser = findBrowser()
    if not browser:
        log.error("🧭 No Chrome, Chromium or Edge found\n"
                  "set: %s", BROWSER_ENV)
        return 1
    # Printed beside it and swapped in only when complete: a failed print
    # leaves the last good PDF, for a CI job that brought one along. The
    # print page sits in the manual's folder, so its img/ paths hold.
    page = manualDir / PRINT_PAGE
    fresh = outFile.with_name(outFile.stem + ".new.pdf")
    version = build_version()
    try:
        page.write_text(build_manual_html.buildPrintHtml(manualDir, version), encoding="utf-8")
        if not printOnce(browser, page, fresh):
            return 1
        pages = destPages(fresh.read_bytes())
        if pages:
            page.write_text(build_manual_html.buildPrintHtml(manualDir, version, pages),
                            encoding="utf-8")
            if not printOnce(browser, page, fresh):
                return 1
        else:
            log.warning("📕 No page numbers for the contents: the PDF names no anchors")
    finally:
        page.unlink(missing_ok=True)
    os.replace(fresh, outFile)
    log.info("📕 Manual PDF written\n"
             "file: %s\n"
             "version: %s\n"
             "size: %d KB", outFile, version, outFile.stat().st_size // 1024)
    return 0


def main(argv=None) -> int:
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = sys.argv[1:] if argv is None else argv
    if not args:
        return max([buildPdf(d, d / PDF_NAME) for d in build_manual_html.MANUALS])
    manualDir = Path(args[0]).resolve()
    outFile = Path(args[1]) if len(args) > 1 else manualDir / PDF_NAME
    return buildPdf(manualDir, outFile)


if __name__ == "__main__":
    sys.exit(main())
