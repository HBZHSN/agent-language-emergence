"""Event alignment: do failures and watchdog interventions precede lexical innovation?"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import mannwhitneyu, spearmanr

from analysis import config, lexicon, text as T

BIN = "6h"
PREDICTORS = ["trial_errors", "validate_errors", "watchdog_main", "valution_calls"]


def bh_q(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvals[i] * m / rank)
        q[i] = prev
    return q


def load() -> pd.DataFrame:
    u = pd.read_parquet(config.DERIVED / "utterances.parquet")
    u["time_utc"] = pd.to_datetime(u["time_utc"], utc=True)
    u["bin"] = u["time_utc"].dt.floor(BIN)
    u["tokens"] = u["text"].map(lambda s: len(T.tokenize(s)) if isinstance(s, str) else 0)
    t = pd.read_parquet(config.DERIVED / "tool_calls.parquet")
    t["time_utc"] = pd.to_datetime(t["time_utc"], utc=True)
    t["bin"] = t["time_utc"].dt.floor(BIN)
    v = pd.read_parquet(config.DERIVED / "utterances.parquet")
    v["time_utc"] = pd.to_datetime(v["time_utc"], utc=True)
    v["bin"] = v["time_utc"].dt.floor(BIN)
    return u, t, v


def main():
    u, t, v = load()
    bins = pd.date_range(u["bin"].min(), u["bin"].max(), freq=BIN, tz="UTC")
    base = pd.DataFrame({"bin": bins})

    tok = u.groupby("bin").agg(tokens=("tokens", "sum"), utterances=("utterance_id", "size")).reset_index()
    base = base.merge(tok, on="bin", how="left").fillna(0)

    trial = t[t.tool_name == "valuation_trial"].groupby("bin").agg(trial_calls=("status", "size"), trial_errors=("status", lambda s: (s == "error").sum())).reset_index()
    validate = t[t.tool_name == "valuation_validate"].groupby("bin").agg(validate_calls=("status", "size"), validate_errors=("status", lambda s: (s == "error").sum())).reset_index()
    valution = t[t.tool_name == "valution"].groupby("bin").size().rename("valution_calls").reset_index()
    base = base.merge(trial, on="bin", how="left").merge(validate, on="bin", how="left").merge(valution, on="bin", how="left").fillna(0)

    def is_verdict(text):
        return T.extract_verdict(text) is not None

    verdicts = v[(v.agent == "watchdog") & (v.act == "verdict")].copy()
    verdicts["decision"] = verdicts["text"].map(lambda s: (T.extract_verdict(s) or {}).get("decision"))
    wd = verdicts.groupby("bin").agg(watchdog_main=("decision", lambda s: (s == "main").sum())).reset_index()
    base = base.merge(wd, on="bin", how="left").fillna(0)

    j = pd.read_parquet(config.DERIVED / "jobs.parquet")
    j["created_at"] = pd.to_datetime(j["created_at"], utc=True)
    j["bin"] = j["created_at"].dt.floor(BIN)
    jobs = j.groupby("bin").size().rename("jobs_created").reset_index()
    base = base.merge(jobs, on="bin", how="left").fillna(0)

    # New curated terms per bin (first occurrence of each term).
    terms = pd.read_csv(config.AGGREGATES / "e2_term_stats.csv")
    terms["first_time"] = pd.to_datetime(terms["first_time"], format="ISO8601", utc=True)
    terms["bin"] = terms["first_time"].dt.floor(BIN)
    firsts = terms.groupby("bin").size().rename("new_terms").reset_index()
    base = base.merge(firsts, on="bin", how="left").fillna(0)

    base.to_csv(config.AGGREGATES / "e8_bins.csv", index=False, encoding="utf-8-sig")

    cols = ["new_terms", "trial_errors", "validate_errors", "watchdog_main", "valution_calls", "tokens", "jobs_created"]
    corr = []
    for a in cols:
        for b in cols:
            if a >= b:
                continue
            rho, p = spearmanr(base[a], base[b])
            corr.append({"a": a, "b": b, "spearman": round(float(rho), 3), "p": round(float(p), 4), "n": int(len(base))})
    pd.DataFrame(corr).to_csv(config.AGGREGATES / "e8_correlations.csv", index=False, encoding="utf-8-sig")

    # Poisson regression with log tokens offset.  n is small; report as
    # descriptive association, not causal effect.  NegativeBinomial is the
    # overdispersion-robust counterpart.
    X = base[["trial_errors", "validate_errors", "watchdog_main", "valution_calls"]].astype(float)
    X = sm.add_constant(X)
    y = base["new_terms"].astype(float)
    offset = np.log(base["tokens"].clip(lower=1))
    try:
        model = sm.GLM(y, X, family=sm.families.Poisson(), offset=offset).fit()
        pvals = {k: float(v) for k, v in model.pvalues.items()}
        q = bh_q([pvals[k] for k in PREDICTORS])
        reg = {
            "coef": {k: round(float(v), 4) for k, v in model.params.items()},
            "p": {k: round(v, 4) for k, v in pvals.items()},
            "q_bh": {k: round(qi, 4) for k, qi in zip(PREDICTORS, q)},
            "n": int(len(base)),
            "pseudo_r2": round(float(1 - model.deviance / model.null_deviance), 4),
        }
    except Exception as exc:
        reg = {"error": str(exc)}
    try:
        from statsmodels.discrete.discrete_model import NegativeBinomial

        nb = NegativeBinomial(y, X, offset=offset).fit(disp=0, maxiter=200)
        nb_p = {k: float(v) for k, v in nb.pvalues.items()}
        nb_q = bh_q([nb_p[k] for k in PREDICTORS])
        nb_reg = {
            "coef": {k: round(float(v), 4) for k, v in nb.params.items()},
            "p": {k: round(v, 4) for k, v in nb_p.items()},
            "q_bh": {k: round(qi, 4) for k, qi in zip(PREDICTORS, nb_q)},
            "alpha": round(float(nb.params.get("alpha", np.nan)), 4),
            "n": int(len(base)),
        }
    except Exception as exc:
        nb_reg = {"error": str(exc)}

    # Event contrast: bins with above-median trial errors vs below.
    med = base["trial_errors"].median()
    high = base[base["trial_errors"] > med]["new_terms"]
    low = base[base["trial_errors"] <= med]["new_terms"]
    if len(high) and len(low):
        stat, p = mannwhitneyu(high, low, alternative="two-sided")
        contrast = {"median_trial_errors": float(med), "high_n": int(len(high)), "low_n": int(len(low)), "high_mean": round(float(high.mean()), 2), "low_mean": round(float(low.mean()), 2), "mannwhitney_p": round(float(p), 4)}
    else:
        contrast = {}

    summary = {
        "bins": int(len(base)),
        "bin_size": BIN,
        "new_terms_total": int(base["new_terms"].sum()),
        "trial_errors_total": int(base["trial_errors"].sum()),
        "validate_errors_total": int(base["validate_errors"].sum()),
        "watchdog_main_total": int(base["watchdog_main"].sum()),
        "valution_total": int(base["valution_calls"].sum()),
        "regression": reg,
        "regression_nb": nb_reg,
        "contrast": contrast,
        "correlations": corr,
    }
    (config.AGGREGATES / "e8_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
