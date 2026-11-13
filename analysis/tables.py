"""Build paper-ready Markdown/CSV tables from sanitized aggregates."""

from __future__ import annotations

import json

import pandas as pd

from analysis import config


def md(df: pd.DataFrame, path: str, floatfmt: str = "{:.3f}") -> None:
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].map(lambda x: "" if pd.isna(x) else floatfmt.format(x))
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "|".join(["---"] * len(df.columns)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    (config.TABLES / path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    df.to_csv(config.TABLES / path.replace(".md", ".csv"), index=False, encoding="utf-8-sig")


def bh(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvals[i] * m / rank)
        q[i] = min(1.0, prev)
    return q


def main():
    # Table 1: agents
    a = pd.read_csv(config.AGGREGATES / "b1_agent_summary.csv")
    t1 = a[["agent", "sessions", "messages", "tool_calls", "tool_errors", "text_parts", "session_tokens_input", "session_tokens_output"]].copy()
    t1["input_B"] = (t1.pop("session_tokens_input") / 1e9).round(3)
    t1["output_M"] = (t1.pop("session_tokens_output") / 1e6).round(2)
    md(t1, "table01_agents.md")

    # Table 2: message types
    t2 = pd.read_csv(config.AGGREGATES / "b1_message_types.csv")
    md(t2, "table02_message_types.md")

    # Table 3: daily
    d1 = pd.read_csv(config.AGGREGATES / "b1_daily.csv")
    d2 = pd.read_csv(config.AGGREGATES / "b2_daily.csv")
    t3 = d1.merge(d2, on="date", how="left").fillna(0)
    t3["tokens_input_B"] = (t3.pop("step_tokens_input") / 1e9).round(3)
    t3 = t3[["date", "messages", "tool_calls", "tool_errors", "tokens_input_B", "n_jobs", "n_results"]]
    md(t3, "table03_daily.md")

    # Table 4: top terms
    e2 = pd.read_csv(config.AGGREGATES / "e2_term_stats.csv").sort_values("count", ascending=False).head(20)
    e2["first_time"] = pd.to_datetime(e2["first_time"], format="ISO8601", utc=True).dt.strftime("%m-%d %H:%M")
    t4 = e2[["term", "category", "count", "agents", "sessions", "jobs", "first_voice", "first_time", "rate_per_10k"]]
    md(t4, "table04_terms.md")

    # Table 5: diffusion direction
    ds = json.loads((config.AGGREGATES / "e2_diffusion_summary.json").read_text(encoding="utf-8"))
    t5 = pd.DataFrame([{"direction": k, "terms": v} for k, v in ds["directions"].items()])
    md(t5, "table05_diffusion.md")

    # Table 6: dialect key terms
    d = pd.read_csv(config.AGGREGATES / "e3_dialect_terms.csv")
    rows = []
    for agent in ["main", "parser", "reviewer", "watchdog"]:
        sub = d[(d.agent == agent) & (d.z > 0)].nlargest(8, "z")
        rows.append({"agent": agent, "top_terms": "、".join(sub["term"].tolist()), "max_z": round(float(sub["z"].max()), 1)})
    md(pd.DataFrame(rows), "table06_dialect.md")

    # Table 7: classifier
    clf = json.loads((config.AGGREGATES / "e3_classifier_all.json").read_text(encoding="utf-8"))
    cm = pd.DataFrame(clf["confusion_matrix"], index=["main", "parser", "reviewer", "watchdog"], columns=["main", "parser", "reviewer", "watchdog"])
    cm.index.name = "true\\pred"
    cm.to_csv(config.TABLES / "table07_confusion.csv", encoding="utf-8-sig")
    lines = ["| true\\pred | main | parser | reviewer | watchdog |", "|---|---:|---:|---:|---:|"]
    for idx, row in cm.iterrows():
        lines.append("| " + idx + " | " + " | ".join(str(int(x)) for x in row.values) + " |")
    (config.TABLES / "table07_confusion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    pd.DataFrame([{"metric": k, "value": clf[k]} for k in ["n", "macro_f1", "weighted_f1", "vectorizer_features"]]).to_csv(
        config.TABLES / "table07_metrics.csv", index=False, encoding="utf-8-sig"
    )

    # Table 8: convergence
    t12 = pd.read_csv(config.AGGREGATES / "e4_trends.csv")
    t24 = pd.read_csv(config.AGGREGATES / "e4_trends_24h.csv")
    e12 = t12[t12.metric == "excess_js"].copy()
    e24 = t24[t24.metric == "excess_js"].copy()
    e12["q_12h"] = bh(e12["p_two_sided"].tolist())
    e24["q_24h"] = bh(e24["p_two_sided"].tolist())
    t8 = e12[["pair", "slope_per_day", "ci_low", "ci_high", "p_two_sided", "q_12h"]].merge(
        e24[["pair", "slope_per_day", "p_two_sided", "q_24h"]], on="pair", suffixes=("_12h", "_24h")
    )
    md(t8, "table08_convergence.md")

    # Table 9: compression
    comp = json.loads((config.AGGREGATES / "e5_summary.json").read_text(encoding="utf-8"))
    rows = []
    for role, v in comp["correlations"].items():
        rows.append({"role": role, **v})
    md(pd.DataFrame(rows), "table09_compression.md")

    # Table 10: tool variants
    v = pd.read_csv(config.AGGREGATES / "e6_variants.csv")
    v = v[~v.official].sort_values("calls", ascending=False).head(15).copy()
    v["tool"] = v["tool"].str.replace("\n", "\\n", regex=False).str.slice(0, 40)
    for col in ["first", "last"]:
        v[col] = pd.to_datetime(v[col], format="ISO8601", utc=True).dt.strftime("%m-%d %H:%M")
    t10 = v[["tool", "calls", "success_rate", "agents", "nearest_official", "edit_distance", "first", "last"]]
    md(t10, "table10_tool_variants.md")

    # Table 11: protocol
    p = json.loads((config.AGGREGATES / "e7_summary.json").read_text(encoding="utf-8"))
    t11 = pd.DataFrame(
        [
            {"metric": "verdict_attempts", "value": p["verdict_attempts"]},
            {"metric": "valid_verdicts", "value": p["valid_verdicts"]},
            {"metric": "valid_rate", "value": p["valid_rate"]},
            {"metric": "order_ok_rate", "value": p["order_ok_rate"]},
            {"metric": "decision_healthy", "value": p["decision_counts"].get("healthy", 0)},
            {"metric": "decision_main", "value": p["decision_counts"].get("main", 0)},
            {"metric": "decision_human", "value": p["decision_counts"].get("human", 0)},
            {"metric": "mean_evidence_n", "value": p["mean_evidence_n"]},
            {"metric": "evidence_gt_6", "value": p["evidence_gt_6"]},
            {"metric": "mean_exact_match", "value": p["mean_exact_match"]},
        ]
    )
    md(t11, "table11_protocol.md")

    # Table 12: events
    ev = json.loads((config.AGGREGATES / "e8_summary.json").read_text(encoding="utf-8"))
    corr = pd.DataFrame(ev["correlations"])
    corr = corr[corr.a == "new_terms"].copy()
    corr["q_bh"] = bh(corr["p"].tolist())
    md(corr, "table12_events.md")

    # Table 13: outcomes
    oc = json.loads((config.AGGREGATES / "e9_summary.json").read_text(encoding="utf-8"))
    t13 = pd.DataFrame(
        [
            {"metric": "jobs", "value": oc["jobs"]},
            {"metric": "failed_or_deferred", "value": oc["failed_or_deferred"]},
            {"metric": "with_dispatch", "value": oc["with_dispatch"]},
            {"metric": "jargon_rounds_all", "value": oc["jargon_rounds_all"]},
            {"metric": "jargon_rounds_with_dispatch", "value": oc["jargon_rounds_with_dispatch"]},
            {"metric": "jargon_rounds_with_dispatch_p", "value": oc["jargon_rounds_with_dispatch_p"]},
            {"metric": "poisson_jargon_coef", "value": oc["regression_rounds"]["coef"].get("dispatch_jargon_per_1k")},
            {"metric": "poisson_jargon_p", "value": oc["regression_rounds"]["p"].get("dispatch_jargon_per_1k")},
            {"metric": "poisson_r2", "value": oc["regression_rounds"].get("pseudo_r2")},
            {"metric": "nb_jargon_coef", "value": oc["regression_rounds_nb"]["coef"].get("dispatch_jargon_per_1k")},
            {"metric": "nb_jargon_p", "value": oc["regression_rounds_nb"]["p"].get("dispatch_jargon_per_1k")},
            {"metric": "nb_alpha", "value": oc["regression_rounds_nb"].get("alpha")},
            {"metric": "nb_alpha_p", "value": oc["regression_rounds_nb"]["p"].get("alpha")},
        ]
    )
    md(t13, "table13_outcomes.md")

    # Table 14: robustness
    t14 = pd.read_csv(config.AGGREGATES / "e10_robustness.csv")
    md(t14, "table14_robustness.md")


if __name__ == "__main__":
    main()
