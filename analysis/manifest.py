"""Build and verify the reproducibility manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analysis import config


def sha256(path: Path, chunk: int = 4 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def counts() -> dict:
    oc = config.connect_opencode()
    vc = config.connect_valuation()
    out = {
        "sessions": int(oc.execute("select count(*) from session_v2").fetchone()[0]),
        "messages": int(oc.execute("select count(*) from session_message").fetchone()[0]),
        "products": int(vc.execute("select count(*) from products").fetchone()[0]),
        "sources": int(vc.execute("select count(*) from sources").fetchone()[0]),
        "jobs": int(vc.execute("select count(*) from jobs").fetchone()[0]),
        "results": int(vc.execute("select count(*) from results").fetchone()[0]),
        "bindings": int(vc.execute("select count(*) from bindings").fetchone()[0]),
        "releases": int(vc.execute("select count(*) from releases").fetchone()[0]),
        "watchdog_events": int(vc.execute("select count(*) from watchdog_events").fetchone()[0]),
        "tokens_input": int(oc.execute("select sum(tokens_input) from session_v2").fetchone()[0]),
        "tokens_output": int(oc.execute("select sum(tokens_output) from session_v2").fetchone()[0]),
    }
    return out


def aggregate_files() -> list[Path]:
    return sorted(p for p in config.AGGREGATES.rglob("*") if p.is_file())


def source_files() -> list[Path]:
    files = [config.OPENCODE_DB, config.VALUATION_DB, config.CONFIG_JSON]
    files += [config.PROMPT_DIR / n for n in config.SEED_PROMPTS]
    files += [config.SRC / n for n in config.SEED_DOCS]
    files += [config.SRC / "valuation" / "opencode" / "index.js", config.SRC / "README.md", config.SRC / "AGENTS.md"]
    return [p for p in files if p.exists()]


def build() -> dict:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts(),
        "source": [
            {"path": str(p), "sha256": sha256(p), "bytes": p.stat().st_size} for p in source_files()
        ],
        "aggregates": [
            {"path": str(p.relative_to(config.ROOT)), "sha256": sha256(p), "bytes": p.stat().st_size}
            for p in aggregate_files()
        ],
    }
    paper = config.PAPER / "paper.pdf"
    if paper.exists():
        manifest["paper_pdf"] = {"sha256": sha256(paper), "bytes": paper.stat().st_size}
        try:
            from pypdf import PdfReader

            manifest["paper_pdf"]["pages"] = len(PdfReader(str(paper)).pages)
        except Exception:
            pass
    config.MANIFEST.mkdir(parents=True, exist_ok=True)
    (config.MANIFEST / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote manifest with", len(manifest["aggregates"]), "aggregates")
    return manifest


def check() -> bool:
    path = config.MANIFEST / "manifest.json"
    if not path.exists():
        print("manifest missing; run python -m analysis.manifest")
        return False
    m = json.loads(path.read_text(encoding="utf-8"))
    ok = True
    current = counts()
    for k, v in m["counts"].items():
        if current.get(k) != v:
            print(f"COUNT MISMATCH {k}: manifest={v} current={current.get(k)}")
            ok = False
    for item in m["aggregates"]:
        p = config.ROOT / item["path"]
        if not p.exists():
            print("MISSING", item["path"])
            ok = False
        elif sha256(p) != item["sha256"]:
            print("HASH MISMATCH", item["path"])
            ok = False
    for item in m["source"]:
        p = Path(item["path"])
        if p.exists() and sha256(p) != item["sha256"]:
            print("SOURCE CHANGED", item["path"])
            # Source DBs can legitimately change if the production system runs;
            # report but do not fail the check for aggregates.
    print("manifest check", "OK" if ok else "FAILED")
    print(json.dumps(current, ensure_ascii=False, indent=2))
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check() else 1)
    build()
