"""Build the Assignment 2 PDF from ``A2_report.md``.

Steps: pandoc (Markdown -> HTML), move the generated table of contents after the executive
summary, print cover and body separately with headless Chrome, fill TOC page numbers from
the first body render (second pass), then merge into the final PDF.

Usage:
    python report/build/build_pdf.py [--out ../DDM501_Assignment2_<id>_<name>.pdf]
"""

from __future__ import annotations

import argparse
import html as html_lib
import re
import subprocess
import unicodedata
from pathlib import Path

from pypdf import PdfReader, PdfWriter

BUILD_DIR = Path(__file__).resolve().parent
REPORT_DIR = BUILD_DIR.parent
DEFAULT_OUT = REPORT_DIR.parent / "DDM501_Assignment2_hoa25ms13299_PhamNgocHoa.pdf"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=REPORT_DIR)


def render_html(html_path: Path) -> None:
    run([
        "pandoc", "A2_report.md", "--standalone", "--toc", "--toc-depth=2", "--number-sections",
        "--number-offset=-1",
        "--template", str(BUILD_DIR / "template.html"), "--css", "build/style.css",
        "--resource-path", str(REPORT_DIR), "-o", str(html_path),
    ])
    html = html_path.read_text(encoding="utf-8")
    toc = re.search(r'<nav id="TOC" role="doc-toc">.*?</nav>', html, flags=re.S).group(0)
    html = html.replace(toc, "")
    toc = re.sub(r'<a href="(#[^"]+)"([^>]*)>(.*?)</a>',
                 r'<a href="\1"\2><span class="toc-text">\3</span><span class="toc-dots"></span><span class="toc-page" data-target="\1"></span></a>',
                 toc, flags=re.S)
    html = html.replace('<div id="toc-placeholder"></div>', toc)
    html = re.sub(r"<colgroup>.*?</colgroup>", "", html, flags=re.S)
    html = html.replace('href="build/style.css"', 'href="style.css"')
    html = html.replace('src="figures/', f'src="{REPORT_DIR}/figures/')
    html_path.write_text(html, encoding="utf-8")


def print_pdf(html_path: Path, pdf_path: Path, mode: str) -> None:
    subprocess.run(["node", str(BUILD_DIR / "print_pdf.mjs"), str(html_path), str(pdf_path), mode], check=True)


def normalise(text: str) -> str:
    """Lower-case, collapse whitespace and expand typographic ligatures (ﬁ, ﬀ) from PDF text."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().lower()


def toc_entries(html: str) -> list[tuple[str, str]]:
    """Return (anchor, searchable heading text) for each TOC entry."""
    toc = re.search(r'<nav id="TOC".*?</nav>', html, flags=re.S).group(0)
    out = []
    pattern = r'<a href="(#[^"]+)"[^>]*><span class="toc-text">(.*?)</span><span class="toc-dots">'
    for anchor, inner in re.findall(pattern, toc, flags=re.S):
        text = re.sub(r"<[^>]+>", " ", inner).replace("&amp;", "&")
        out.append((anchor, normalise(text)))
    return out


def outline_entries(html: str) -> list[tuple[str, str, int]]:
    """Return (anchor, display title, nesting level) for each TOC entry, for PDF bookmarks."""
    toc = re.search(r'<nav id="TOC".*?</nav>', html, flags=re.S).group(0)
    out, level = [], -1
    for tag, anchor, inner in re.findall(r'(<ul[^>]*>|</ul>|<a href="(#[^"]+)"[^>]*><span class="toc-text">(.*?)</span><span class="toc-dots">)', toc, flags=re.S):
        if tag.startswith("<ul"):
            level += 1
        elif tag == "</ul>":
            level -= 1
        else:
            title = re.sub(r"<[^>]+>", " ", inner)
            title = html_lib.unescape(re.sub(r"\s+", " ", title)).strip()
            out.append((anchor, title, level))
    return out


def find_pages(pdf_path: Path, entries: list[tuple[str, str]]) -> dict[str, int]:
    pages = [normalise(p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages]
    toc_last = max(i for i, p in enumerate(pages) if "table of contents" in p)
    found: dict[str, int] = {}
    start = toc_last + 1
    for anchor, text in entries:
        for i in range(start, len(pages)):
            if text in pages[i]:
                found[anchor] = i + 1
                start = i
                break
    return found


def fill_pages(html_path: Path, pages: dict[str, int]) -> None:
    html = html_path.read_text(encoding="utf-8")
    for anchor, page in pages.items():
        html = html.replace(f'<span class="toc-page" data-target="{anchor}"></span>',
                            f'<span class="toc-page" data-target="{anchor}">{page}</span>')
    html_path.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    html_path = BUILD_DIR / "A2_report.html"
    cover_pdf, body_pdf = BUILD_DIR / "cover.pdf", BUILD_DIR / "body.pdf"
    render_html(html_path)
    print_pdf(html_path, body_pdf, "body")
    entries = toc_entries(html_path.read_text(encoding="utf-8"))
    pages = find_pages(body_pdf, entries)
    missing = [a for a, _ in entries if a not in pages]
    if missing:
        print(f"warning: TOC entries without page: {missing}")
    fill_pages(html_path, pages)
    print_pdf(html_path, body_pdf, "body")
    if find_pages(body_pdf, entries) != pages:
        raise SystemExit("TOC page numbers shifted after second pass")
    print_pdf(html_path, cover_pdf, "cover")

    writer = PdfWriter()
    for part in (cover_pdf, body_pdf):
        for page in PdfReader(str(part)).pages:
            writer.add_page(page)
    # Body page n is merged page index n (index 0 is the cover).
    parents: dict[int, object] = {}
    for anchor, title, level in outline_entries(html_path.read_text(encoding="utf-8")):
        if anchor in pages:
            parents[level] = writer.add_outline_item(title, pages[anchor], parent=parents.get(level - 1))
    writer.page_mode = "/UseOutlines"
    writer.add_metadata({
        "/Title": "ML Pipeline Design & MLOps Analysis — Telco Customer Churn (DDM501 Assignment 2)",
        "/Author": "Phạm Ngọc Hòa (hoa25ms13299)",
        "/Subject": "DDM501 Individual Assignment 2",
    })
    with open(args.out, "wb") as fh:
        writer.write(fh)
    print(f"wrote {args.out} ({len(writer.pages)} pages: 1 cover + {len(writer.pages) - 1} body)")


if __name__ == "__main__":
    main()
