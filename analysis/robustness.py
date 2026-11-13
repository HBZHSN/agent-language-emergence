"""Consolidated sensitivity checks for the main claims."""

from __future__ import annotations

import json

import pandas as pd
from scipy.stats import spearmanr

from analysis import config, lexicon, text as T


def main():
    rows = []

    # E2: curated term counts, full vs no-watchdog, and exact-token vs substring.
    u = pd.read_parquet(config.DERIVED / "utterances.parquet")
    u = u[u.agent.isin(["main", "parser", "reviewer", "watchdog"])].copy()
    u["clean"] = u["text"].map(T.clean_prose)
    u = u[u.clean.str.len() >= 2]
    terms = [t for t, _, _ in lexicon.CURATED]
    full = {t: int(u["clean"].map(lambda s: s.count(t)).sum()) for t in terms}
    nowd = u[u.agent != "watchdog"]
    no_wd = {t: int(nowd["clean"].map(lambda s: s.count(t)).sum()) for t in terms}
    df = pd.DataFrame({"term": terms, "full": [full[t] for t in terms], "no_watchdog": [no_wd[t] for t in terms]})
    rho, p = spearmanr(df.full, df.no_watchdog)
    rows.append({"check": "E2 term counts: full vs no-watchdog", "statistic": round(float(rho), 3), "p": round(float(p), 4), "n": len(df), "note": "rank correlation"})

    # E4: window sensitivity, main-reviewer excess JS.
    for window in ["12h", "24h"]:
        suffix = "" if window == "12h" else "_" + window
        path = config.AGGREGATES / f"e4_trends{suffix}.csv"
        if path.exists():
            tr = pd.read_csv(path)
            sub = tr[(tr.pair == "main-reviewer") & (tr.metric == "excess_js")]
            if len(sub):
                rows.append({"check": f"E4 main-reviewer excess JS ({window})", "statistic": float(sub.iloc[0]["slope_per_day"]), "p": float(sub.iloc[0]["p_two_sided"]), "n": int(sub.iloc[0]["n"]), "note": "slope/day"})

    # E5/E9: jargon vs rounds sensitivity.
    e9 = pd.read_csv(config.AGGREGATES / "e9_job_features.csv")
    for label, sub in [
        ("all jobs", e9),
        ("active only", e9[e9.status == "active"]),
        ("rounds<=20", e9[e9.rounds <= 20]),
        ("active & rounds<=20", e9[(e9.status == "active") & (e9.rounds <= 20)]),
        ("with dispatch", e9[e9.dispatch_jargon_per_1k > 0]),
    ]:
        if len(sub) > 5 and sub.dispatch_jargon_per_1k.nunique() > 2:
            rho, p = spearmanr(sub.dispatch_jargon_per_1k, sub.rounds)
            rows.append({"check": f"E9 jargon vs rounds ({label})", "statistic": round(float(rho), 3), "p": round(float(p), 4), "n": int(len(sub)), "note": "Spearman"})

    # E6: valution cost with and without watchdog.
    t = pd.read_parquet(config.DERIVED / "tool_calls.parquet")
    m = pd.read_parquet(config.DERIVED / "messages.parquet")
    v = t[t.tool_name == "valution"]
    vm = m[m.message_id.isin(v.message_id)]
    rows.append({"check": "E6 valution tokens (all agents)", "statistic": int(vm.tokens_input.sum()), "p": None, "n": int(len(v)), "note": "tokens"})
    rows.append({"check": "E6 valution tokens (main only)", "statistic": int(vm[vm.agent == "main"].tokens_input.sum()), "p": None, "n": int((v.agent == "main").sum()), "note": "tokens"})

    out = pd.DataFrame(rows)
    out.to_csv(config.AGGREGATES / "e10_robustness.csv", index=False, encoding="utf-8-sig")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
