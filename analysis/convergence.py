"""Convergence / divergence of agent registers over time.

For each 12-hour window we build a unigram distribution per voice, compute
pairwise Jensen-Shannon divergence, and compare it with a pooled-null baseline
(two samples drawn from the same distribution with the observed sample sizes).
"""

from __future__ import annotations

import json
import math
import os
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

from analysis import config, text as T

WINDOW = os.environ.get("AGENT_LANG_WINDOW", "12h")
MAIN_VOICE = os.environ.get("AGENT_LANG_MAIN_VOICE", "all")
SUFFIX = "" if WINDOW == "12h" else "_" + WINDOW
if MAIN_VOICE == "own":
    SUFFIX += "_ownvoice"
VOICES = ["main", "parser", "reviewer", "watchdog"]
PAIRS = list(combinations(VOICES, 2))


def load() -> pd.DataFrame:
    df = pd.read_parquet(config.DERIVED / "utterances.parquet")
    df = df[df.agent.isin(VOICES)].copy()
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)
    df["clean"] = df["text"].map(T.clean_prose)
    df = df[df.clean.str.len() >= 2].copy()

    def voice(row):
        if row["act"] in ("dispatch", "job_summary", "job_instruction"):
            # Quoted child/human content relayed by main; "own" excludes it.
            return None if MAIN_VOICE == "own" else "main"
        if row["act"] == "verdict":
            return "watchdog"
        if row["agent"] in VOICES:
            return row["agent"]
        return None

    df["voice"] = df.apply(voice, axis=1)
    df = df[df.voice.notna()].copy()
    df["tokens"] = df["clean"].map(T.tokenize)
    df["window"] = df["time_utc"].dt.floor(WINDOW)
    return df


def build_counts(df: pd.DataFrame) -> tuple[dict, list[str], dict]:
    # global vocabulary from all content tokens
    all_counts = {}
    for _, row in df.iterrows():
        for tok in row["tokens"]:
            all_counts[tok] = all_counts.get(tok, 0) + 1
    vocab = [w for w, c in sorted(all_counts.items(), key=lambda x: -x[1])[:4000]]
    index = {w: i for i, w in enumerate(vocab)}
    counts = {}
    totals = {}
    for (window, voice), sub in df.groupby(["window", "voice"]):
        vec = np.zeros(len(vocab), dtype=np.float64)
        n = 0
        for toks in sub["tokens"]:
            for tok in toks:
                j = index.get(tok)
                if j is not None:
                    vec[j] += 1
                    n += 1
        if n < 200:
            continue
        counts[(window, voice)] = vec
        totals[(window, voice)] = n
    return counts, vocab, totals


def js(vec_a, vec_b, alpha=1.0):
    pa = (vec_a + alpha) / (vec_a.sum() + alpha * len(vec_a))
    pb = (vec_b + alpha) / (vec_b.sum() + alpha * len(vec_b))
    return float(jensenshannon(pa, pb, base=2))


def null_js(n_a, n_b, pooled, rng, reps=100):
    p = pooled / pooled.sum()
    vals = []
    for _ in range(reps):
        a = rng.multinomial(n_a, p).astype(np.float64)
        b = rng.multinomial(n_b, p).astype(np.float64)
        vals.append(js(a, b))
    return float(np.mean(vals))


def jaccard_top(vec_a, vec_b, vocab, k=200):
    a = {vocab[i] for i in np.argsort(vec_a)[-k:]}
    b = {vocab[i] for i in np.argsort(vec_b)[-k:]}
    return len(a & b) / max(1, len(a | b))


def trend(values: pd.DataFrame, value_col: str) -> dict:
    # OLS slope per day, bootstrap over windows.
    x = (values["window"] - values["window"].min()).dt.total_seconds().to_numpy() / 86400
    y = values[value_col].to_numpy()
    if len(y) < 3:
        return {"slope_per_day": None, "ci_low": None, "ci_high": None, "n": len(y)}
    slope = float(np.polyfit(x, y, 1)[0])
    rng = np.random.default_rng(42)
    boots = []
    for _ in range(5000):
        idx = rng.integers(0, len(y), len(y))
        if len(set(idx)) < 3:
            continue
        boots.append(float(np.polyfit(x[idx], y[idx], 1)[0]))
    return {
        "slope_per_day": slope,
        "ci_low": float(np.percentile(boots, 2.5)),
        "ci_high": float(np.percentile(boots, 97.5)),
        "n": len(y),
        "p_two_sided": float(min(1.0, 2 * min(np.mean(np.array(boots) <= 0), np.mean(np.array(boots) >= 0)))),
    }


def main():
    df = load()
    counts, vocab, totals = build_counts(df)
    windows = sorted({w for w, _ in counts})
    rng = np.random.default_rng(7)
    rows = []
    for window in windows:
        present = [v for v in VOICES if (window, v) in counts]
        if len(present) < 2:
            continue
        pooled = sum(counts[(window, v)] for v in present)
        for a, b in PAIRS:
            if (window, a) not in counts or (window, b) not in counts:
                continue
            va, vb = counts[(window, a)], counts[(window, b)]
            observed = js(va, vb)
            null = null_js(totals[(window, a)], totals[(window, b)], pooled, rng, reps=60)
            rows.append(
                {
                    "window": window,
                    "pair": f"{a}-{b}",
                    "js": observed,
                    "null_js": null,
                    "excess_js": observed - null,
                    "jaccard_top200": jaccard_top(va, vb, vocab),
                    "tokens_a": totals[(window, a)],
                    "tokens_b": totals[(window, b)],
                }
            )
    out = pd.DataFrame(rows)
    out["window"] = pd.to_datetime(out["window"], utc=True)
    out.to_csv(config.AGGREGATES / f"e4_divergence{SUFFIX}.csv", index=False, encoding="utf-8-sig")

    trends = []
    for pair, sub in out.groupby("pair"):
        for col in ["js", "excess_js", "jaccard_top200"]:
            t = trend(sub.sort_values("window"), col)
            trends.append({"pair": pair, "metric": col, **t})
    pd.DataFrame(trends).to_csv(config.AGGREGATES / f"e4_trends{SUFFIX}.csv", index=False, encoding="utf-8-sig")

    # early vs late (first/last 48h) heatmaps
    start = out["window"].min()
    end = out["window"].max()
    early = out[out["window"] <= start + pd.Timedelta(hours=47)]
    late = out[out["window"] >= end - pd.Timedelta(hours=47)]
    heat = []
    for label, sub in (("early", early), ("late", late)):
        for _, r in sub.iterrows():
            heat.append({"period": label, **{k: r[k] for k in ["pair", "js", "excess_js", "jaccard_top200"]}})
    pd.DataFrame(heat).to_csv(config.AGGREGATES / f"e4_early_late{SUFFIX}.csv", index=False, encoding="utf-8-sig")

    summary = {
        "window": WINDOW,
        "main_voice": MAIN_VOICE,
        "bootstrap_reps": 5000,
        "windows": int(out["window"].nunique()),
        "pairs": int(out["pair"].nunique()),
        "observations": int(len(out)),
        "mean_js": round(float(out["js"].mean()), 4),
        "mean_null_js": round(float(out["null_js"].mean()), 4),
        "mean_excess_js": round(float(out["excess_js"].mean()), 4),
        "mean_jaccard_top200": round(float(out["jaccard_top200"].mean()), 4),
        "trends": pd.DataFrame(trends).to_dict(orient="records"),
    }
    (config.AGGREGATES / f"e4_summary{SUFFIX}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in ["windows", "observations", "mean_js", "mean_null_js", "mean_excess_js", "mean_jaccard_top200"]}, ensure_ascii=False, indent=2))
    print(pd.DataFrame(trends).to_string(index=False))


if __name__ == "__main__":
    main()
