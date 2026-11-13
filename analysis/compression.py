"""Communication compression: dispatch prompts and job summaries over time."""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from analysis import config, lexicon, text as T

SLOT_PATTERNS = {
    "job_id": r"(?:job_id\s*=\s*\d+|job\s*\d+)",
    "scope": r"scope|时段|范围",
    "samples": r"样例|samples|20\s*份",
    "evidence": r"证据|报告|路径|self_check|review",
    "forbid": r"禁止|不得|不要|零改|不许",
    "sequence": r"先\s*valuation|先调用|第一步|再\s*valuation|单发|一次",
    "verdict": r"PASSED|FAILED|通过|不通过|approved|rejected",
    "round": r"轮次|round|续跑|重跑",
}


def load_dispatches() -> pd.DataFrame:
    d = pd.read_parquet(config.DERIVED / "dispatches.parquet")
    d = d[d.job_id.notna() & d.role.notna()].copy()
    d["job_id"] = d["job_id"].astype(int)
    d["time_utc"] = pd.to_datetime(d["time_utc"], utc=True)
    d["day"] = d["time_utc"].dt.strftime("%Y-%m-%d")
    d["tokens"] = d["text"].map(lambda s: len(T.tokenize(s)))
    for slot, pattern in SLOT_PATTERNS.items():
        d[f"slot_{slot}"] = d["text"].map(lambda s: int(bool(re.search(pattern, s, re.I))))
    slot_cols = [f"slot_{s}" for s in SLOT_PATTERNS]
    d["slots"] = d[slot_cols].sum(axis=1)
    d["bullets"] = d["text"].map(lambda s: len(re.findall(r"^\s*(?:[-*]|\d+\.)\s", s, re.M)))
    d["headings"] = d["text"].map(lambda s: len(re.findall(r"^\s*#+\s", s, re.M)))
    d["log_len"] = np.log1p(d["text_len"])
    terms = [x[0] for x in lexicon.CURATED]
    d["jargon"] = d["text"].map(lambda s: sum(s.count(t) for t in terms))
    d["jargon_per_1k"] = (d["jargon"] / d["tokens"].clip(lower=1) * 1000).round(2)
    return d


def complexity() -> pd.DataFrame:
    con = config.connect_valuation()
    j = pd.read_sql_query(
        """
        select j.id job_id, j.rounds, j.recoveries, j.restarts,
               (select count(*) from job_samples s where s.job_id=j.id) n_samples,
               (select count(distinct s.signature) from job_samples s where s.job_id=j.id) n_signatures
        from jobs j
        """,
        con,
    )
    return j


def template_similarity(d: pd.DataFrame) -> pd.Series:
    # Character n-gram TF-IDF; compare each row to all earlier rows of same role.
    vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=2, max_features=30000)
    X = vec.fit_transform(d["text"].tolist())
    sims = np.zeros(len(d))
    for i, (_, row) in enumerate(d.iterrows()):
        prior = d.index[(d["role"] == row["role"]) & (d["time_utc"] < row["time_utc"])]
        if len(prior) == 0:
            sims[i] = np.nan
            continue
        sims[i] = float(cosine_similarity(X[i], X[prior]).max())
    return pd.Series(sims, index=d.index)


def regress(d: pd.DataFrame) -> dict:
    d = d.copy()
    d["job_order"] = d["job_id"].rank(method="dense").astype(float)
    d["job_order_z"] = (d["job_order"] - d["job_order"].mean()) / d["job_order"].std()
    sig_std = d["n_signatures"].std()
    d["n_signatures_z"] = (
        (d["n_signatures"] - d["n_signatures"].mean()) / sig_std if sig_std and sig_std > 0 else 0.0
    )
    d["role"] = d["role"].astype(str)
    d["day"] = d["day"].astype(str)
    model = smf.ols(
        "log_len ~ job_order_z + C(role) + n_signatures_z + C(day)",
        data=d,
    ).fit(cov_type="cluster", cov_kwds={"groups": d["job_id"]})
    coef = float(model.params.get("job_order_z", np.nan))
    ci = model.conf_int().loc["job_order_z"].tolist() if "job_order_z" in model.params else [None, None]
    return {
        "n": int(len(d)),
        "coef_job_order_z": round(coef, 4),
        "ci_low": round(float(ci[0]), 4),
        "ci_high": round(float(ci[1]), 4),
        "p": round(float(model.pvalues.get("job_order_z", np.nan)), 4),
        "r2": round(float(model.rsquared), 4),
        "coef_per_10_jobs_pct": round((np.exp(coef * 10) - 1) * 100, 2),
    }


def report_features() -> tuple[pd.DataFrame, dict]:
    """Child-agent reports (RQ4 report side): structure and jargon over jobs."""
    u = pd.read_parquet(config.DERIVED / "utterances.parquet")
    u = u[(u.act == "report") & u.agent.isin(["parser", "reviewer"])].copy()
    total = int(len(u))
    u["time_utc"] = pd.to_datetime(u["time_utc"], utc=True)
    sessions = pd.read_parquet(config.DERIVED / "sessions.parquet")
    title = dict(zip(sessions["id"], sessions["title"]))
    u["job_id"] = pd.to_numeric(u["job_id"], errors="coerce")
    miss = u["job_id"].isna()
    u.loc[miss, "job_id"] = pd.to_numeric(
        u.loc[miss, "session_id"].map(title).str.extract(r"job\s+(\d+)", flags=re.I)[0],
        errors="coerce",
    )
    linked = int(u["job_id"].notna().sum())
    u = u.dropna(subset=["job_id"]).copy()
    u["job_id"] = u["job_id"].astype(int)
    u["role"] = u["agent"]
    u["tokens"] = u["text"].map(lambda s: len(T.tokenize(s)))
    u["bullets"] = u["text"].map(lambda s: len(re.findall(r"^\s*(?:[-*]|\d+\.)\s", s, re.M)))
    u["headings"] = u["text"].map(lambda s: len(re.findall(r"^\s*#+\s", s, re.M)))
    u["jargon"] = u["text"].map(lambda s: sum(s.count(t) for t, _, _ in lexicon.CURATED))
    u["jargon_per_1k"] = (u["jargon"] / u["tokens"].clip(lower=1) * 1000).round(2)
    jobs = pd.read_parquet(config.DERIVED / "jobs.parquet")
    order = dict(zip(jobs["id"].astype(int), jobs["id"].astype(int).rank(method="dense").astype(int)))
    u["job_order"] = u["job_id"].map(order)
    u = u.sort_values("time_utc")
    cols = ["job_id", "role", "job_order", "time_utc", "text_len", "tokens", "bullets", "headings", "jargon", "jargon_per_1k"]
    feat = u[cols].copy()
    initial = u.drop_duplicates(["job_id", "role"], keep="first")
    corr = {}
    for role, sub in initial.groupby("role"):
        corr[role] = {
            "spearman_len_order": round(float(sub["text_len"].corr(sub["job_order"], method="spearman")), 3),
            "spearman_tokens_order": round(float(sub["tokens"].corr(sub["job_order"], method="spearman")), 3),
            "spearman_jargon_order": round(float(sub["jargon_per_1k"].corr(sub["job_order"], method="spearman")), 3),
            "n": int(len(sub)),
        }
    info = {
        "reports_total": total,
        "reports_linked": linked,
        "jobs": int(u["job_id"].nunique()),
        "initial_reports": int(len(initial)),
        "by_role": initial.groupby("role").size().to_dict(),
        "mean_tokens": round(float(initial["tokens"].mean()), 1),
        "mean_jargon_per_1k": round(float(initial["jargon_per_1k"].mean()), 2),
        "correlations": corr,
    }
    return feat, info


def main():
    d = load_dispatches()
    c = complexity()
    d = d.merge(c, on="job_id", how="left")
    d = d.sort_values("time_utc").reset_index(drop=True)
    d["template_similarity"] = template_similarity(d)
    d["job_order"] = d["job_id"].rank(method="dense").astype(int)
    # Public features only: never write raw dispatch text or product identity.
    drop_cols = [c for c in ["text", "product_name", "product_code", "child_session", "review_session"] if c in d.columns]
    d.drop(columns=drop_cols).to_csv(config.AGGREGATES / "e5_dispatch_features.csv", index=False, encoding="utf-8-sig")

    # First dispatch per job/role.  Some sessions are reused across turns, so
    # ``turn == 1`` is not a reliable proxy for the initial dispatch.
    initial = d.sort_values("time_utc").drop_duplicates(["job_id", "role"], keep="first").copy()
    reg = regress(initial)
    # Spearman by role
    corr = {}
    for role, sub in initial.groupby("role"):
        corr[role] = {
            "spearman_len_order": round(float(sub["text_len"].corr(sub["job_order"], method="spearman")), 3),
            "spearman_slots_order": round(float(sub["slots"].corr(sub["job_order"], method="spearman")), 3),
            "spearman_sim_order": round(float(sub["template_similarity"].corr(sub["job_order"], method="spearman")), 3),
            "spearman_jargon_order": round(float(sub["jargon_per_1k"].corr(sub["job_order"], method="spearman")), 3),
            "n": int(len(sub)),
        }

    # Job summaries: length, structure, jargon density.
    j = pd.read_parquet(config.DERIVED / "jobs.parquet")
    j = j[j["summary"].notna()].copy()
    j["job_order"] = j["id"].rank(method="dense").astype(int)
    j["summary_tokens"] = j["summary"].map(lambda s: len(T.tokenize(s)))
    j["jargon"] = j["summary"].map(lambda s: sum(s.count(t) for t, _, _ in lexicon.CURATED))
    j["jargon_per_1k"] = (j["jargon"] / j["summary_tokens"].clip(lower=1) * 1000).round(2)
    j["bullets"] = j["summary"].map(lambda s: len(re.findall(r"^\s*(?:[-*]|\d+\.)\s", s, re.M)))
    j["headings"] = j["summary"].map(lambda s: len(re.findall(r"^\s*#+\s", s, re.M)))
    j[["id", "job_order", "status", "summary_len", "summary_tokens", "jargon", "jargon_per_1k", "bullets", "headings"]].to_csv(
        config.AGGREGATES / "e5_job_summary_features.csv", index=False, encoding="utf-8-sig"
    )
    summary_corr = {
        "spearman_len_order": round(float(j["summary_len"].corr(j["job_order"], method="spearman")), 3),
        "spearman_jargon_order": round(float(j["jargon_per_1k"].corr(j["job_order"], method="spearman")), 3),
        "n": int(len(j)),
    }

    rep, rep_info = report_features()
    rep.to_csv(config.AGGREGATES / "e5_report_features.csv", index=False, encoding="utf-8-sig")

    summary = {
        "dispatch_rows": int(len(d)),
        "initial_dispatches": int(len(initial)),
        "by_role": initial.groupby("role").size().to_dict(),
        "mean_text_len": round(float(initial["text_len"].mean()), 1),
        "mean_tokens": round(float(initial["tokens"].mean()), 1),
        "mean_slots": round(float(initial["slots"].mean()), 2),
        "mean_jargon_per_1k": round(float(initial["jargon_per_1k"].mean()), 2),
        "mean_template_similarity": round(float(initial["template_similarity"].mean()), 4),
        "regression": reg,
        "correlations": corr,
        "job_summary": summary_corr,
        "reports": rep_info,
    }
    (config.AGGREGATES / "e5_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
