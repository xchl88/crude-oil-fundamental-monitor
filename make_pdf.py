"""Render each report's English brief and Chinese summary to PDF.

    python make_pdf.py                 # every folder in reports/
    python make_pdf.py 2026-10-21      # one report

Markdown -> HTML with pandoc (GitHub-flavoured Markdown, line breaks kept), HTML -> PDF with
headless Chrome, so tables, charts and Traditional Chinese render as on GitHub.
The Markdown files stay the source: rerun after any edit (`brief_llm.py
finalize` does this itself). Set CHROME to use a different Chrome binary.
"""
import html
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
DOCS = (("brief_EN.md", "brief_EN.pdf", "en"), ("summary_CN.md", "summary_CN.pdf", "zh-Hant"))

CSS = """
@page { size: A4; margin: 15mm 14mm 16mm; }
body { font-family: -apple-system, "Helvetica Neue", Arial, "PingFang TC", "Heiti TC", sans-serif;
       font-size: 9.6pt; line-height: 1.45; color: #1f2328; }
h1 { font-size: 16pt; margin: 0 0 6pt; color: #12355b; }
h2 { font-size: 12pt; margin: 14pt 0 5pt; color: #12355b; border-bottom: 1px solid #d0d7de; padding-bottom: 2pt; }
h3 { font-size: 10.5pt; margin: 12pt 0 4pt; color: #12355b; }
h2, h3 { break-after: avoid; }
p { margin: 4pt 0; }
ul, ol { margin: 3pt 0 5pt; padding-left: 16pt; }
li { margin: 1.5pt 0; }
em { color: #57606a; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 8pt; font-size: 8.4pt; }
th, td { border: 1px solid #d0d7de; padding: 3pt 5pt; vertical-align: top; }
th { background: #f0f3f6; text-align: left; }
td[style*="right"], th[style*="right"] { white-space: nowrap; }   /* keep "–$12.18" on one line */
tr { break-inside: avoid; }
img { max-width: 100%; display: block; margin: 6pt auto; break-inside: avoid; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 10pt 0; }
a { color: #0b5cad; text-decoration: none; word-break: break-all; }
blockquote { margin: 6pt 0; padding: 4pt 8pt; border-left: 3px solid #d0d7de; color: #57606a; }
"""


def render(folder, md_name, pdf_name, lang):
    src = folder / md_name
    if not src.exists():
        return None
    body = subprocess.run(["pandoc", "-f", "gfm+hard_line_breaks", "-t", "html5", str(src)],
                          capture_output=True, text=True, check=True).stdout
    title = next((l.lstrip("# ").strip() for l in src.read_text().splitlines() if l.startswith("# ")), md_name)
    page = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<base href="{folder.as_uri()}/"><title>{html.escape(title)}</title>'
            f"<style>{CSS}</style></head><body>{body}</body></html>")
    out = folder / pdf_name
    with tempfile.TemporaryDirectory() as tmp:
        page_path = Path(tmp) / "page.html"
        page_path.write_text(page)
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
                        "--allow-file-access-from-files", f"--user-data-dir={tmp}/profile",
                        f"--print-to-pdf={out}", page_path.as_uri()],
                       capture_output=True, check=True, timeout=120)
    return out


def main():
    dates = sys.argv[1:] or sorted(p.name for p in REPORTS.iterdir() if (p / "brief_EN.md").exists())
    for d in dates:
        for md_name, pdf_name, lang in DOCS:
            out = render(REPORTS / d, md_name, pdf_name, lang)
            if out:
                print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
