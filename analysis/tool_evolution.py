"""Tool-name evolution: official vocabulary, variants, selection and contagion."""

from __future__ import annotations

import json
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from analysis import config


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def load() -> pd.DataFrame:
    t = pd.read_parquet(config.DERIVED / "tool_calls.parquet")
    t["time_utc"] = pd.to_datetime(t["time_utc"], utc=True)
    t["official"] = t["tool_name"].isin(config.OFFICIAL_TOOLS)
    return t


def nearest_official(name: str) -> tuple[str, int]:
    best = min(config.OFFICIAL_TOOLS, key=lambda x: levenshtein(name, x))
    return best, levenshtein(name, best)


def main():
    t = load()
    summary_rows = []
    for name, sub in t.groupby("tool_name"):
        near, dist = nearest_official(name)
        summary_rows.append(
            {
                "tool": name,
                "calls": int(len(sub)),
                "errors": int((sub.status == "error").sum()),
                "success_rate": round(float((sub.status == "completed").mean()), 4),
                "agents": ",".join(sorted(sub.agent.unique())),
                "official": bool(name in config.OFFICIAL_TOOLS),
                "nearest_official": near,
                "edit_distance": dist,
                "first": sub.time_utc.min().isoformat(),
                "last": sub.time_utc.max().isoformat(),
                "input_keys": ";".join(sub.input_keys.dropna().value_counts().head(3).index.tolist()),
            }
        )
    summ = pd.DataFrame(summary_rows).sort_values("calls", ascending=False)
    summ.to_csv(config.AGGREGATES / "e6_variants.csv", index=False, encoding="utf-8-sig")

    # valution breakdown.  The form is used as a universal placeholder for
    # several different tool schemas (subagent, job, product, empty).
    v = t[t.tool_name == "valution"].copy()
    v["schema"] = np.where(
        v.input_keys.str.contains("sql", na=False),
        "sql",
        np.where(v.input_keys.str.contains("agent", na=False), "subagent",
                 np.where(v.input_keys.str.contains("job_id", na=False), "job",
                          np.where(v.input_keys.str.contains("product_id", na=False), "product", "empty"))),
    )
    breakdown = v.groupby(["agent", "schema", "status"]).size().reset_index(name="calls")
    breakdown.to_csv(config.AGGREGATES / "e6_valution_breakdown.csv", index=False, encoding="utf-8-sig")

    msgs = pd.read_parquet(config.DERIVED / "messages.parquet")
    msgs["time_utc"] = pd.to_datetime(msgs["time_utc"], utc=True)
    vm = msgs[msgs.message_id.isin(v.message_id)]
    vm_tokens = int(vm["tokens_input"].sum())
    day = msgs[(msgs.time_utc >= "2026-11-10") & (msgs.time_utc < "2026-11-11")]
    v["hour"] = v.time_utc.dt.floor("h")
    schema_timeline = (
        v.groupby(["agent", "schema"]).agg(first=("time_utc", "min"), last=("time_utc", "max"), calls=("message_id", "size")).reset_index()
    )
    schema_timeline.to_csv(config.AGGREGATES / "e6_valution_schema_timeline.csv", index=False, encoding="utf-8-sig")

    # hourly series for valution and subagent
    hourly = []
    for name in ["valution", "subagent", "valuation_session_db"]:
        sub = t[t.tool_name == name].copy()
        sub["hour"] = sub.time_utc.dt.floor("h")
        for hour, g in sub.groupby("hour"):
            hourly.append({"hour": hour, "tool": name, "calls": len(g), "errors": int((g.status == "error").sum())})
    pd.DataFrame(hourly).sort_values(["hour", "tool"]).to_csv(config.AGGREGATES / "e6_tool_hourly.csv", index=False, encoding="utf-8-sig")

    # Hourly token cost of the valution loop.
    vm_hour = vm.copy()
    vm_hour["hour"] = vm_hour["time_utc"].dt.floor("h")
    vm_hour.groupby("hour").agg(calls=("message_id", "size"), tokens_input=("tokens_input", "sum")).reset_index().to_csv(
        config.AGGREGATES / "e6_valution_hourly_tokens.csv", index=False, encoding="utf-8-sig"
    )

    # Transition matrix for main tool calls (ordered by time).
    main = t[t.agent == "main"].sort_values("time_utc").copy()
    trans = Counter()
    prev = None
    for _, row in main.iterrows():
        cur = row.tool_name
        if prev is not None:
            trans[(prev, cur)] += 1
        prev = cur
    trans_rows = [{"from": a, "to": b, "count": c} for (a, b), c in trans.most_common()]
    pd.DataFrame(trans_rows).to_csv(config.AGGREGATES / "e6_transitions.csv", index=False, encoding="utf-8-sig")

    # Runs of consecutive valution calls in the main session.
    runs = []
    cur = 0
    for _, row in main.iterrows():
        if row.tool_name == "valution":
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    run_dist = Counter(runs)

    # Conditional probability of valution after valution vs after other.
    seq = main.tool_name.tolist()
    after_v = [seq[i] for i in range(1, len(seq)) if seq[i - 1] == "valution"]
    after_o = [seq[i] for i in range(1, len(seq)) if seq[i - 1] != "valution"]
    p_v = sum(1 for x in after_v if x == "valution") / max(1, len(after_v))
    p_o = sum(1 for x in after_o if x == "valution") / max(1, len(after_o))

    summary = {
        "tool_calls": int(len(t)),
        "official_calls": int(t.official.sum()),
        "nonofficial_calls": int((~t.official).sum()),
        "nonofficial_share": round(float((~t.official).mean()), 4),
        "distinct_tools": int(t.tool_name.nunique()),
        "distinct_nonofficial": int(t.loc[~t.official, "tool_name"].nunique()),
        "valution_calls": int(len(v)),
        "valution_by_agent": v.groupby("agent").size().to_dict(),
        "valution_by_schema": v.groupby("schema").size().to_dict(),
        "valution_success": int((v.status == "completed").sum()),
        "valution_tokens_input": vm_tokens,
        "valution_token_share_of_day": round(vm_tokens / max(1, int(day["tokens_input"].sum())), 4),
        "valution_mean_input_tokens": round(float(vm["tokens_input"].mean()), 1),
        "valution_median_input_tokens": float(vm["tokens_input"].median()),
        "main_valution_runs": len(runs),
        "main_valution_max_run": int(max(runs) if runs else 0),
        "main_valution_run_distribution": dict(run_dist),
        "p_valution_after_valution": round(float(p_v), 4),
        "p_valution_after_other": round(float(p_o), 4),
        "contagion_odds_ratio": round(float((p_v / max(1e-9, 1 - p_v)) / (p_o / max(1e-9, 1 - p_o))), 4),
    }
    (config.AGGREGATES / "e6_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(breakdown.to_string(index=False))
    print(summ.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
