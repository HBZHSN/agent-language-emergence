from pathlib import Path

files = ["analysis/number_audit.py", "docs/reproduction.md", "docs/number_audit.md", "docs/review_checklist.md"]
for f in files:
    p = Path(f)
    s = p.read_text(encoding="utf-8")
    s = s.replace("44 页", "46 页").replace("44 pages", "46 pages").replace("paper pages 44", "paper pages 46")
    s = s.replace('pages), 44', 'pages), 46')
    s = s.replace('"pdf_pages", len(PdfReader(str(config.PAPER / "paper.pdf")).pages), 44', '"pdf_pages", len(PdfReader(str(config.PAPER / "paper.pdf")).pages), 46')
    p.write_text(s, encoding="utf-8")
    print("updated", f)
