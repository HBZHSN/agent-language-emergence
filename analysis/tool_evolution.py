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

    def schema_of(keys) -> str:
        k = {x for x in str(keys).split(",") if x} if isinstance(keys, str) else set()
        if "sql" in k:
            return "sql"
        if k and k <= {"agent", "sessionID"}:
            return "subagent"
        if "job_id" in k:
            return "job"
        if "product_id" in k:
            return "product"
        return "empty"

    v["schema"] = v.input_keys.map(schema_of)
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

    # Timing structure of the main-agent valution burst: rapid within-burst
    # calls separated by long pauses (a single continuous loop would have no
    # such pauses).  Pauses > 600 s are treated as burst boundaries.
    vm_main = v[v.agent == "main"].sort_values("time_utc")
    gaps = vm_main.time_utc.diff().dt.total_seconds().dropna()
    pauses = gaps[gaps > 600]
    within = gaps[gaps <= 600]
    lifespan_days = (v.time_utc.max() - v.time_utc.min()).total_seconds() / 86400

    # External pacing: does a synthetic idle-monitor notification precede each
    # burst re-onset?  Record the trigger message for citable evidence.
    msgs = pd.read_parquet(config.DERIVED / "messages.parquet")
    msgs["time_utc"] = pd.to_datetime(msgs["time_utc"], utc=True)
    syn = msgs[msgs.type == "synthetic"]
    onset_rows = []
    trig_deltas = []
    trig_texts = set()
    for pos in pauses.index:
        row = vm_main.loc[pos]
        t0, sid = row.time_utc, row.session_id
        cand = syn[(syn.session_id == sid) & (syn.time_utc <= t0) & (syn.time_utc >= t0 - pd.Timedelta(seconds=300))]
        rec = {"onset_utc": t0.isoformat(), "gap_before_s": round(float(gaps.loc[pos]), 1), "session_id": sid,
               "synthetic_message_id": None, "trigger_delta_s": None}
        if len(cand):
            last = cand.sort_values("time_utc").iloc[-1]
            delta = float((t0 - last.time_utc).total_seconds())
            trig_deltas.append(delta)
            trig_texts.add(last["text"] if isinstance(last["text"], str) else "")
            rec["synthetic_message_id"] = last.message_id
            rec["trigger_delta_s"] = round(delta, 2)
        onset_rows.append(rec)
    pd.DataFrame(onset_rows).to_csv(config.AGGREGATES / "e6_burst_onsets.csv", index=False, encoding="utf-8-sig")
    trig = pd.Series(trig_deltas)

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
        "valution_lifespan_days": round(float(lifespan_days), 2),
        "main_valution_span_hours": round(float((vm_main.time_utc.max() - vm_main.time_utc.min()).total_seconds() / 3600), 2),
        "main_valution_gap_mean_s": round(float(gaps.mean()), 2),
        "main_valution_gap_median_s": round(float(gaps.median()), 2),
        "main_valution_within_burst_gap_mean_s": round(float(within.mean()), 2) if len(within) else None,
        "main_valution_bursts": int(len(pauses) + 1),
        "main_valution_pauses_gt_600s": int(len(pauses)),
        "main_valution_pause_total_hours": round(float(pauses.sum() / 3600), 2),
        "main_valution_pause_mean_s": round(float(pauses.mean()), 1) if len(pauses) else None,
        "main_valution_pause_min_s": round(float(pauses.min()), 1) if len(pauses) else None,
        "main_valution_pause_max_s": round(float(pauses.max()), 1) if len(pauses) else None,
        "main_valution_error_share": round(float((vm_main.status == "error").mean()), 4),
        "main_valution_reonsets": int(len(pauses)),
        "main_valution_reonsets_with_synthetic_trigger": int(len(trig_deltas)),
        "synthetic_trigger_delta_median_s": round(float(trig.median()), 2) if len(trig) else None,
        "synthetic_trigger_delta_mean_s": round(float(trig.mean()), 2) if len(trig) else None,
        "synthetic_trigger_delta_max_s": round(float(trig.max()), 2) if len(trig) else None,
        "synthetic_trigger_prompt_variants": int(len(trig_texts)),
    }
    (config.AGGREGATES / "e6_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(breakdown.to_string(index=False))
    print(summ.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
