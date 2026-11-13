"""Fail if tracked content contains credentials or product identity.

Usage:
    python analysis/privacy_check.py            # scan tracked files
    python analysis/privacy_check.py --staged   # scan staged files (pre-commit)
    python analysis/privacy_check.py --all      # scan tracked + untracked non-ignored

The checker reads product names/codes from the read-only valuation database so
the deny-list is never written to disk.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from analysis import config

TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".js", ".json", ".csv", ".tsv", ".html", ".css",
    ".yml", ".yaml", ".toml", ".ini", ".cfg", ".ps1", ".sh", ".tex", ".bib",
}
SKIP_PREFIXES = (
    "data/derived/",
    "data/private/",
    "paper/_build/",
    "tools/_scratch/",
)
MAX_BYTES = 5_000_000

SECRET_PATTERNS = [
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")),
    ("api_key_assignment", re.compile(
        r"(?i)\b(?:api[_-]?key|model_api_key|secret|password|passwd|access[_-]?token|refresh[_-]?token)"
        r"\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{12,})"
    )),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}")),
]


def git_files(staged: bool, all_files: bool) -> list[str]:
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    elif all_files:
        cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    else:
        cmd = ["git", "ls-files"]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        raise SystemExit("git command failed: " + out.stderr)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def load_products() -> tuple[list[str], list[str]]:
    con = config.connect_valuation()
    rows = con.execute("select name, code from products").fetchall()
    names = sorted({str(r[0]).strip() for r in rows if r[0] and len(str(r[0]).strip()) >= 4}, key=len, reverse=True)
    codes = sorted({str(r[1]).strip() for r in rows if r[1] and len(str(r[1]).strip()) >= 4})
    return names, codes


def load_module_tokens() -> list[str]:
    """Institution/module tokens derived from jobs.module (never hard-coded)."""
    try:
        con = config.connect_valuation()
        rows = con.execute(
            "select distinct module from jobs where module is not null and trim(module) != ''"
        ).fetchall()
    except Exception:
        return []
    tokens: set[str] = set()
    for row in rows:
        module = str(row[0]).strip()
        base = module.split("_valuation_sheet")[0]
        for token in base.split("_"):
            token = token.strip().lower()
            if len(token) >= 3:
                tokens.add(token)
    return sorted(tokens, key=len, reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    names, codes = load_products()
    code_res = [(c, re.compile(r"(?<![A-Za-z0-9])" + re.escape(c) + r"(?![A-Za-z0-9])")) for c in codes]
    module_res = [
        (t, re.compile(r"(?i)(?<![A-Za-z0-9])" + re.escape(t) + r"[0-9a-z_]*(?![A-Za-z0-9])"))
        for t in load_module_tokens()
    ]

    violations: list[str] = []
    for rel in git_files(args.staged, args.all):
        if any(rel.startswith(p) for p in SKIP_PREFIXES):
            continue
        path = config.ROOT / rel
        if not path.exists() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.stat().st_size > MAX_BYTES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")

        for label, pattern in SECRET_PATTERNS:
            for m in pattern.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                violations.append(f"{rel}:{line}: {label}")

        for name in names:
            if name in text:
                line = text.count("\n", 0, text.find(name)) + 1
                violations.append(f"{rel}:{line}: product_name")

        for code, pattern in code_res:
            for m in pattern.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                masked = code[:2] + "***"
                violations.append(f"{rel}:{line}: product_code({masked})")

        for token, pattern in module_res:
            for m in pattern.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                masked = token[:2] + "***"
                violations.append(f"{rel}:{line}: module_name({masked})")

    if violations:
        print("PRIVACY CHECK FAILED:")
        for v in violations[:200]:
            print("  " + v)
        if len(violations) > 200:
            print(f"  ... {len(violations) - 200} more")
        print("\nRemove or pseudonymize the content before committing.  See AGENTS.md 4.5.")
        return 1
    print("privacy check passed: no product identity or credentials in scanned files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
