"""Render paper.md to a styled HTML file and print it to PDF with Edge."""

from __future__ import annotations

import subprocess
from pathlib import Path

from markdown_it import MarkdownIt

from analysis import config

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

CSS = r"""
@page {
  size: A4;
  margin: 20mm 18mm 20mm 18mm;
}
html { font-size: 11pt; }
body {
  font-family: "Source Han Serif SC", "SimSun", "Microsoft YaHei", serif;
  line-height: 1.85;
  color: #1a1a1a;
  max-width: 100%;
  margin: 0;
}
h1, h2, h3, h4 {
  font-family: "Microsoft YaHei", "SimHei", sans-serif;
  color: #111111;
  line-height: 1.35;
}
h1 { font-size: 22pt; text-align: center; margin: 40mm 0 6mm 0; }
h1 + h2 { text-align: center; font-size: 14pt; font-weight: normal; margin-top: 0; color: #333; }
h2 {
  font-size: 16pt;
  margin-top: 10mm;
  padding-bottom: 2mm;
  border-bottom: 1.2pt solid #333;
  page-break-after: avoid;
  page-break-before: always;
}
h1 + h2 { page-break-before: avoid; }
h3 { font-size: 13pt; margin-top: 7mm; page-break-after: avoid; }
h4 { font-size: 11.5pt; }
p { text-align: justify; text-indent: 2em; margin: 0.55em 0; }
p.no-indent, li p { text-indent: 0; }
blockquote {
  margin: 2mm 0 2mm 6mm;
  padding: 2mm 4mm;
  border-left: 2.5pt solid #999;
  background: #f7f7f7;
  color: #333;
  font-size: 10pt;
}
blockquote p { text-indent: 0; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0 4mm 0;
  font-size: 8.6pt;
  page-break-inside: avoid;
}
th, td { border: 0.5pt solid #bbb; padding: 1.2mm 1.5mm; vertical-align: top; }
th { background: #eeeeee; font-weight: bold; }
tr:nth-child(even) td { background: #fafafa; }
img { max-width: 100%; display: block; margin: 3mm auto 2mm auto; page-break-inside: avoid; }
figure { margin: 4mm 0; page-break-inside: avoid; text-align: center; }
figcaption { font-size: 9pt; color: #555; margin-top: 1.5mm; text-align: center; }
p.caption { text-indent: 0; font-size: 9pt; color: #333; margin: 2.5mm 0 1mm 0; }
code, pre {
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-size: 9pt;
  background: #f5f5f5;
}
pre { padding: 3mm; overflow-x: auto; white-space: pre-wrap; page-break-inside: avoid; }
ul, ol { margin: 0.4em 0 0.6em 2em; }
li { margin: 0.2em 0; }
hr { border: none; border-top: 0.5pt solid #ccc; margin: 6mm 0; }
a { color: #1a4f8b; text-decoration: none; }
.cover { page-break-after: always; }
.toc { page-break-after: always; }
.toc h2 { border: none; text-align: center; }
.toc ul { list-style: none; margin-left: 0; }
.toc li { margin: 1.2mm 0; }
.small { font-size: 9pt; color: #555; }
"""


def add_heading_ids(html: str) -> str:
    # markdown-it does not add ids by default; add stable ids for h2/h3.
    import re

    counter = {"n": 0}

    def repl(m):
        level, text = m.group(1), m.group(2)
        counter["n"] += 1
        return f'<h{level} id="h{counter["n"]}">{text}</h{level}>'

    return re.sub(r"<h([23])>(.*?)</h\1>", repl, html, flags=re.S)


def add_captions(html: str) -> str:
    import re

    html = re.sub(
        r'<img src="([^"]+)" alt="([^"]+)"\s*/?>',
        r'<figure><img src="\1" alt="\2"><figcaption>\2</figcaption></figure>',
        html,
    )
    html = re.sub(r"<p>(表\s?[0-9A-Z]+　[^<]*)</p>", r'<p class="caption">\1</p>', html)
    return html


def build_html() -> Path:
    md_text = (config.PAPER / "paper.md").read_text(encoding="utf-8")
    md = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True}).enable("table")
    body = md.render(md_text)
    body = add_heading_ids(body)
    body = add_captions(body)
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>工具约束下的多智能体语言涌现</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>"""
    path = config.PAPER / "paper.html"
    path.write_text(html, encoding="utf-8")
    print("wrote", path, len(html))
    return path


def build_pdf(html_path: Path) -> Path:
    pdf = config.PAPER / "paper.pdf"
    if pdf.exists():
        pdf.unlink()
    cmd = [
        str(EDGE),
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--virtual-time-budget=15000",
        f"--print-to-pdf={pdf}",
        html_path.resolve().as_uri(),
    ]
    print("running", " ".join(cmd))
    subprocess.run(cmd, check=True, timeout=180)
    print("wrote", pdf, pdf.stat().st_size if pdf.exists() else 0)
    return pdf


if __name__ == "__main__":
    build_pdf(build_html())
