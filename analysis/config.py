"""Read-only access and shared constants for the agent-language study.

Every source database is opened with ``mode=ro``.  Nothing in this module
writes to the valuation project.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The production data root is supplied locally through VALUATION_SRC.  The
# fallback is a documented placeholder, never a real machine path, so public
# artifacts and git history cannot leak the source location.
SRC_PLACEHOLDER = r"C:\path\to\valuation"
ROOT_PLACEHOLDER = r"C:\path\to\agent-language"
SRC = Path(os.environ.get("VALUATION_SRC", SRC_PLACEHOLDER))
OPENCODE_DB = SRC / "data" / "opencode" / "state" / "opencode" / "opencode.db"
VALUATION_DB = SRC / "data" / "valuation.db"
CONFIG_JSON = SRC / "data" / "opencode" / "config.json"
PROMPT_DIR = SRC / "valuation" / "opencode"

DERIVED = ROOT / "data" / "derived"
AGGREGATES = ROOT / "data" / "aggregates"
PRIVATE = ROOT / "data" / "private"
MANIFEST = ROOT / "data" / "manifest"
PAPER = ROOT / "paper"
FIGURES = PAPER / "figures"
TABLES = PAPER / "tables"
DOCS = ROOT / "docs"

for _d in (DERIVED, AGGREGATES, PRIVATE, MANIFEST, FIGURES, TABLES, DOCS):
    _d.mkdir(parents=True, exist_ok=True)

# The observation window is UTC, matching SQLite ``datetime('now')`` and the
# millisecond timestamps stored by OpenCode.
WINDOW_START = "2026-11-04T00:00:00+00:00"
WINDOW_END = "2026-11-12T00:00:00+00:00"

AGENTS = [
    "valuation-main",
    "valuation-parser",
    "valuation-reviewer",
    "valuation-watchdog",
]
AGENT_SHORT = {
    "valuation-main": "main",
    "valuation-parser": "parser",
    "valuation-reviewer": "reviewer",
    "valuation-watchdog": "watchdog",
}
ROLE_ORDER = ["main", "parser", "reviewer", "watchdog"]

# Built-in OpenCode tools plus the tools registered by valuation/opencode/index.js.
OFFICIAL_TOOLS = {
    "shell",
    "read",
    "edit",
    "write",
    "glob",
    "grep",
    "subagent",
    "task",
    "webfetch",
    "todowrite",
    "todoread",
}
_VALUATION_ACTIONS = [
    "progress",
    "control",
    "sync",
    "scan",
    "products",
    "queue",
    "prepare",
    "fast_parse",
    "verifier",
    "check_template",
    "job",
    "trial",
    "supervise",
    "session_db",
    "stop",
    "defer",
    "recover",
    "cleanup",
    "validate",
    "review_reject",
    "activate",
    "fail",
    "history",
    "query",
    "confirm",
]
# Deployed list per valuation/opencode/index.js (25 business tools; the
# deployed name is valuation_verifier, not valuation_verify).
OFFICIAL_TOOLS |= {"valuation_" + a for a in _VALUATION_ACTIONS}

MODEL_PROVIDER = "valuation"
MODEL_ID = "swift-1.5"
MODEL_CONTEXT = 262_144
MODEL_MAX_OUTPUT = 16_384
OPENCODE_VERSION = "2.0.32"

# Seed text: what every agent could see without reading project files.
SEED_PROMPTS = ["main.md", "parser.md", "reviewer.md", "watchdog.md", "contracts.md"]
# Secondary seed text: available in the repository, not automatically injected.
SEED_DOCS = ["README.md", "AGENTS.md", "方案.md"]


def connect_opencode() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{OPENCODE_DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def connect_valuation() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{VALUATION_DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _relative_to(path: Path, base: Path) -> Path | None:
    try:
        return path.resolve().relative_to(base.resolve())
    except (ValueError, OSError):
        return None


def display_path(path: Path) -> str:
    """Return a public, stable path with real roots replaced by placeholders."""
    path = Path(path)
    rel = _relative_to(path, SRC)
    if rel is not None:
        return str(Path(SRC_PLACEHOLDER) / rel)
    rel = _relative_to(path, ROOT)
    if rel is not None:
        return str(Path(ROOT_PLACEHOLDER) / rel)
    return str(path)


def resolve_path(value: str) -> Path:
    """Map placeholder paths back to the locally configured roots."""
    text = str(value)
    for placeholder, base in (
        (SRC_PLACEHOLDER, SRC),
        (ROOT_PLACEHOLDER, ROOT),
    ):
        if text.lower().startswith(placeholder.lower()):
            tail = text[len(placeholder):].lstrip("\\/")
            return base / tail
    return Path(text)


def rel(path: Path) -> str:
    rel_path = _relative_to(path, ROOT)
    if rel_path is not None:
        return str(rel_path)
    return display_path(path)


def write_markdown_table(rows: list[dict], path: Path) -> None:
    """Small helper for human-readable audit tables."""
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = list(rows[0])
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join("" if row.get(c) is None else str(row.get(c)) for c in cols) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
