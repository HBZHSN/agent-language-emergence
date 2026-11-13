"""Run or verify the full analysis pipeline."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

from analysis import config, manifest


MODULES = [
    "analysis.extract",
    "analysis.audit",
    "analysis.diversity",
    "analysis.seed_terms",
    "analysis.lexicon_stats",
    "analysis.diffusion",
    "analysis.dialects",
    "analysis.convergence",
    "analysis.compression",
    "analysis.tool_evolution",
    "analysis.protocol",
    "analysis.events",
    "analysis.outcomes",
    "analysis.human_input",
    "analysis.robustness",
    "analysis.manifest",
    "analysis.tables",
    "analysis.figures",
    "analysis.build_paper",
    "analysis.privacy_check",
]


def run(module: str, env: dict | None = None) -> None:
    print(f"\n=== {module} ===", flush=True)
    t0 = time.time()
    e = os.environ.copy()
    if env:
        e.update(env)
    subprocess.run([sys.executable, "-m", module], check=True, env=e)
    print(f"=== {module} done in {time.time()-t0:.1f}s ===", flush=True)


def check() -> bool:
    ok = manifest.check()
    # paper checks
    pdf = config.PAPER / "paper.pdf"
    html = config.PAPER / "paper.html"
    if not pdf.exists() or not html.exists():
        print("paper missing")
        ok = False
    else:
        try:
            from pypdf import PdfReader

            pages = len(PdfReader(str(pdf)).pages)
            print("paper pages", pages)
            if pages < 30:
                print("paper too short")
                ok = False
        except Exception as exc:
            print("pdf check failed", exc)
            ok = False
    print("privacy check:")
    out = subprocess.run([sys.executable, "-m", "analysis.privacy_check", "--all"])
    if out.returncode != 0:
        ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check() else 1)
    for module in MODULES:
        if module == "analysis.convergence":
            run(module, {"AGENT_LANG_WINDOW": "12h"})
            run(module, {"AGENT_LANG_WINDOW": "24h"})
        else:
            run(module)


if __name__ == "__main__":
    main()
