"""D2: lexical diversity by agent and day."""

from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd

from analysis import config, text as T

ACTS = {
    "dispatch", "report", "audit", "directive", "status", "other",
    "job_summary", "job_error", "job_instruction", "verdict", "watchdog_other",
}
AGENTS = ["main", "parser", "reviewer", "watchdog"]


def mattr(tokens: list[str], window: int = 500) -> float:
    if len(tokens) <= window:
        return len(set(tokens)) / max(1, len(tokens))
    vals = []
    for i in range(0, len(tokens) - window + 1, max(1, window // 2)):
        chunk = tokens[i : i + window]
        vals.append(len(set(chunk)) / window)
    return float(np.mean(vals)) if vals else 0.0


def zipf_slope(counter: Counter) -> float:
    if len(counter) < 10:
        return 0.0
    freqs = np.array(sorted(counter.values(), reverse=True), dtype=float)
    ranks = np.arange(1, len(freqs) + 1, dtype=float)
    mask = freqs > 0
    return float(np.polyfit(np.log(ranks[mask]), np.log(freqs[mask]), 1)[0])


def main():
    u = pd.read_parquet(config.DERIVED / "utterances.parquet")
    u = u[u.act.isin(ACTS) & u.agent.isin(AGENTS)].copy()
    u["time_utc"] = pd.to_datetime(u["time_utc"], utc=True)
    u["date"] = u["time_utc"].dt.strftime("%Y-%m-%d")
    u["tokens"] = u["text"].map(lambda s: T.tokenize(s) if isinstance(s, str) else [])
    rows = []
    for (agent, date), sub in u.groupby(["agent", "date"]):
        toks = [t for xs in sub["tokens"] for t in xs]
        if len(toks) < 20:
            continue
        c = Counter(toks)
        rows.append(
            {
                "agent": agent,
                "date": date,
                "tokens": len(toks),
                "types": len(c),
                "ttr": round(len(c) / len(toks), 4),
                "mattr500": round(mattr(toks), 4),
                "hapax": sum(1 for v in c.values() if v == 1),
                "hapax_ratio": round(sum(1 for v in c.values() if v == 1) / len(c), 4),
                "zipf_slope": round(zipf_slope(c), 3),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(config.AGGREGATES / "d2_diversity.csv", index=False, encoding="utf-8-sig")
    summary = out.groupby("agent").agg(
        days=("date", "nunique"),
        mean_ttr=("ttr", "mean"),
        mean_mattr=("mattr500", "mean"),
        mean_hapax=("hapax_ratio", "mean"),
        mean_zipf=("zipf_slope", "mean"),
    ).reset_index()
    summary.to_csv(config.AGGREGATES / "d2_summary.csv", index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))
    print("rows", len(out))


if __name__ == "__main__":
    main()
