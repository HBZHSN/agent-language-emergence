"""Job-level association between language features and outcomes.

This is observational: jargon may be a response to task difficulty rather than
a cause of success.  We report associations and explicitly avoid causal claims.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

from analysis import config, lexicon, text as T


def job_features() -> pd.DataFrame:
    jobs = pd.read_parquet(config.DERIVED / "jobs.parquet").copy()
    jobs["job_id"] = jobs["id"].astype(int)
    d = pd.read_parquet(config.DERIVED / "dispatches.parquet")
    d = d[d.job_id.notna() & d.role.notna()].copy()
    d["job_id"] = d["job_id"].astype(int)
    d["jargon"] = d["text"].map(lambda s: sum(s.count(t) for t, _, _ in lexicon.CURATED))
    d["tokens"] = d["text"].map(lambda s: len(T.tokenize(s)))
    d["jargon_per_1k"] = d["jargon"] / d["tokens"].clip(lower=1) * 1000
    # first dispatch per job/role
    d = d.sort_values("time_utc").drop_duplicates(["job_id", "role"], keep="first")
    agg = d.groupby("job_id").agg(
        dispatch_len=("text_len", "mean"),
        dispatch_tokens=("tokens", "mean"),
        dispatch_jargon_per_1k=("jargon_per_1k", "mean"),
        dispatch_slots=("text_len", "size"),
    ).reset_index()

    t = pd.read_parquet(config.DERIVED / "tool_calls.parquet")
    t["job_id"] = t["input_json"].str.extract(r'"job_id"\s*:\s*"?(\d+)"?')[0]
    t["job_id"] = pd.to_numeric(t["job_id"], errors="coerce")
    tt = t.dropna(subset=["job_id"]).copy()
    tt["job_id"] = tt["job_id"].astype(int)
    tool = tt.groupby(["job_id", "tool_name"]).agg(calls=("status", "size"), errors=("status", lambda s: (s == "error").sum())).reset_index()
    tool_pivot = tool.pivot(index="job_id", columns="tool_name", values=["calls", "errors"]).fillna(0)
    tool_pivot.columns = [f"{a}_{b}" for a, b in tool_pivot.columns]
    tool_pivot = tool_pivot.reset_index()

    # watchdog main verdicts by job title "job N ..."
    u = pd.read_parquet(config.DERIVED / "utterances.parquet")
    u = u[(u.agent == "watchdog") & (u.act == "verdict")].copy()
    u["decision"] = u["text"].map(lambda s: (T.extract_verdict(s) or {}).get("decision"))
    u["job_id"] = u["session_id"].map(lambda s: None)
    # session title is the reliable link; recover it from sessions.parquet
    sessions = pd.read_parquet(config.DERIVED / "sessions.parquet")
    title = dict(zip(sessions["id"], sessions["title"]))
    u["job_id"] = u["session_id"].map(title).str.extract(r"job\s+(\d+)")[0]
    u["job_id"] = pd.to_numeric(u["job_id"], errors="coerce")
    wd = u.dropna(subset=["job_id"]).groupby("job_id").agg(
        watchdog_main=("decision", lambda s: (s == "main").sum()),
        watchdog_verdicts=("decision", "size"),
    ).reset_index()
    wd["job_id"] = wd["job_id"].astype(int)

    out = jobs.merge(agg, on="job_id", how="left").merge(tool_pivot, on="job_id", how="left").merge(wd, on="job_id", how="left")
    out = out.fillna(0)
    out["failed"] = out["status"].isin(["failed", "deferred"]).astype(int)
    return out


def main():
    df = job_features()
    # Public job-level features: drop raw summaries, product identity and
    # session identifiers.  The full table stays local (data/derived).
    drop_cols = [
        "product_name", "product_code", "child_session", "review_session",
        "instruction", "summary", "error", "library_hash",
    ]
    public = df.drop(columns=[c for c in drop_cols if c in df.columns])
    public.to_csv(config.AGGREGATES / "e9_job_features.csv", index=False, encoding="utf-8-sig")

    features = [
        "dispatch_len",
        "dispatch_tokens",
        "dispatch_jargon_per_1k",
        "rounds",
        "recoveries",
        "restarts",
        "n_signatures" if "n_signatures" in df else "rounds",
        "calls_valuation_trial",
        "errors_valuation_trial",
        "calls_valuation_validate",
        "errors_valuation_validate",
        "watchdog_main",
        "watchdog_verdicts",
    ]
    features = [f for f in dict.fromkeys(features) if f in df.columns]
    rows = []
    for f in features:
        for target in ["rounds", "duration_min", "failed"]:
            if f == target or df[f].nunique() < 2:
                continue
            rho, p = spearmanr(df[f], df[target])
            rows.append({"feature": f, "target": target, "spearman": round(float(rho), 3), "p": round(float(p), 4), "n": int(len(df))})
    pd.DataFrame(rows).to_csv(config.AGGREGATES / "e9_correlations.csv", index=False, encoding="utf-8-sig")

    # Poisson regression for rounds; only jobs with dispatch features.
    reg_df = df[(df.dispatch_tokens > 0) & (df.status == "active")].copy()
    for c in ["dispatch_jargon_per_1k", "dispatch_tokens", "rounds"]:
        reg_df[c] = pd.to_numeric(reg_df[c], errors="coerce")
    reg_df = reg_df.dropna(subset=["dispatch_jargon_per_1k", "dispatch_tokens", "rounds"])
    reg = {}
    if len(reg_df) >= 20:
        X = reg_df[["dispatch_jargon_per_1k", "dispatch_tokens"]].copy()
        X["dispatch_jargon_per_1k"] = (X["dispatch_jargon_per_1k"] - X["dispatch_jargon_per_1k"].mean()) / X["dispatch_jargon_per_1k"].std()
        X["dispatch_tokens"] = (X["dispatch_tokens"] - X["dispatch_tokens"].mean()) / X["dispatch_tokens"].std()
        X = sm.add_constant(X)
        y = reg_df["rounds"].astype(float)
        try:
            model = sm.GLM(y, X, family=sm.families.Poisson()).fit(cov_type="HC1")
            reg = {
                "n": int(len(reg_df)),
                "coef": {k: round(float(v), 4) for k, v in model.params.items()},
                "p": {k: round(float(v), 4) for k, v in model.pvalues.items()},
                "pseudo_r2": round(float(1 - model.deviance / model.null_deviance), 4),
            }
        except Exception as exc:
            reg = {"error": str(exc), "n": int(len(reg_df))}

    disp = df[df["dispatch_tokens"] > 0]
    filtered_rho, filtered_p = spearmanr(disp["dispatch_jargon_per_1k"], disp["rounds"])
    summary = {
        "jobs": int(len(df)),
        "failed_or_deferred": int(df["failed"].sum()),
        "with_dispatch": int((df["dispatch_tokens"] > 0).sum()),
        "jargon_rounds_all": round(float(spearmanr(df["dispatch_jargon_per_1k"], df["rounds"]).statistic), 3),
        "jargon_rounds_with_dispatch": round(float(filtered_rho), 3),
        "jargon_rounds_with_dispatch_p": round(float(filtered_p), 4),
        "regression_rounds": reg,
        "descriptives": {
            "rounds_median": float(df["rounds"].median()),
            "rounds_max": float(df["rounds"].max()),
            "duration_median_min": float(df["duration_min"].median()),
        },
    }
    (config.AGGREGATES / "e9_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(pd.DataFrame(rows).sort_values(["target", "p"]).head(30).to_string(index=False))


if __name__ == "__main__":
    main()
