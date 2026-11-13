"""Term-level statistics for the curated lexicon and seed baseline."""

from __future__ import annotations

import collections
import json

import pandas as pd

from analysis import config, lexicon, text as T

ACTS = {
    "dispatch",
    "report",
    "audit",
    "directive",
    "status",
    "other",
    "job_summary",
    "job_error",
    "job_instruction",
    "verdict",
    "watchdog_other",
}


def load_corpus() -> pd.DataFrame:
    utt = pd.read_parquet(config.DERIVED / "utterances.parquet")
    utt = utt[utt.act.isin(ACTS) & utt.agent.isin(["main", "parser", "reviewer", "watchdog"])].copy()
    utt["time_utc"] = pd.to_datetime(utt["time_utc"], utc=True)
    utt = utt.sort_values("time_utc").reset_index(drop=True)
    utt["clean"] = utt["text"].map(T.clean_prose)
    utt = utt[utt["clean"].str.len() >= 2].copy()

    def voice(row):
        if row["act"] in ("dispatch", "job_summary", "job_instruction"):
            return "main"
        if row["act"] == "verdict":
            return "watchdog"
        if row["agent"] in ("main", "parser", "reviewer", "watchdog"):
            return row["agent"]
        return "system"

    utt["voice"] = utt.apply(voice, axis=1)
    return utt


def count_term(df: pd.DataFrame, term: str) -> pd.Series:
    return df["clean"].map(lambda s: s.count(term))


def main():
    df = load_corpus()
    df["n_tokens"] = df["clean"].map(lambda s: len(T.content_tokens(T.tokenize(s))))
    total_tokens = int(df["n_tokens"].sum())

    stats = []
    agent_counts = []
    items = lexicon.as_dict()
    for item in items:
        term = item["term"]
        hits = count_term(df, term)
        mask = hits > 0
        sub = df[mask]
        if len(sub) == 0:
            continue
        first = sub.iloc[0]
        last = sub.iloc[-1]
        by_agent = sub.groupby("agent").size().to_dict()
        for agent in ["main", "parser", "reviewer", "watchdog"]:
            if by_agent.get(agent):
                agent_counts.append({"term": term, "agent": agent, "count": int(by_agent[agent])})
        dispatch_sub = sub[sub["act"] == "dispatch"]
        child_sub = sub[sub["voice"].isin(["parser", "reviewer"])]
        main_sub = sub[sub["voice"] == "main"]
        first_dispatch = dispatch_sub.iloc[0]["time_utc"].isoformat() if len(dispatch_sub) else None
        first_child = child_sub.iloc[0]["time_utc"].isoformat() if len(child_sub) else None
        first_main = main_sub.iloc[0]["time_utc"].isoformat() if len(main_sub) else None
        stats.append(
            {
                "term": term,
                "category": item["category"],
                "gloss": item["gloss"],
                "count": int(hits.sum()),
                "utterances": int(mask.sum()),
                "agents": int(sub["agent"].nunique()),
                "agent_list": ",".join(sorted(sub["agent"].unique())),
                "sessions": int(sub["session_id"].nunique(dropna=True)),
                "jobs": int(sub["job_id"].nunique(dropna=True)),
                "first_time": first["time_utc"].isoformat(),
                "first_agent": first["agent"],
                "first_voice": first["voice"],
                "first_utterance": first["utterance_id"],
                "first_message": first["message_id"],
                "first_main_time": first_main,
                "first_dispatch_time": first_dispatch,
                "first_child_time": first_child,
                "last_time": last["time_utc"].isoformat(),
                "days": int((sub["time_utc"].dt.floor("D")).nunique()),
                "seeded": bool(T.is_seeded(term)),
                "rate_per_10k": round(float(hits.sum()) / max(1, total_tokens) * 10000, 3),
            }
        )
    stats_df = pd.DataFrame(stats).sort_values(["count"], ascending=False)
    stats_df.to_csv(config.AGGREGATES / "e2_term_stats.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(agent_counts).to_csv(config.AGGREGATES / "e2_agent_term_counts.csv", index=False, encoding="utf-8-sig")

    # Seed baseline
    base = []
    for term in lexicon.SEED_BASELINE:
        hits = count_term(df, term)
        mask = hits > 0
        sub = df[mask]
        if len(sub) == 0:
            continue
        base.append(
            {
                "term": term,
                "count": int(hits.sum()),
                "utterances": int(mask.sum()),
                "agents": int(sub["agent"].nunique()),
                "sessions": int(sub["session_id"].nunique(dropna=True)),
                "first_time": sub.iloc[0]["time_utc"].isoformat(),
                "seeded": True,
            }
        )
    pd.DataFrame(base).to_csv(config.AGGREGATES / "e2_seed_baseline.csv", index=False, encoding="utf-8-sig")

    # Daily jargon density by agent
    core_terms = [x["term"] for x in items]
    df["date"] = df["time_utc"].dt.strftime("%Y-%m-%d")
    df["core_hits"] = 0
    for term in core_terms:
        df["core_hits"] += count_term(df, term)
    daily = (
        df.groupby(["date", "agent"])
        .agg(tokens=("n_tokens", "sum"), core_hits=("core_hits", "sum"), utterances=("utterance_id", "size"))
        .reset_index()
    )
    daily["jargon_per_10k"] = (daily["core_hits"] / daily["tokens"].clip(lower=1) * 10000).round(3)
    daily.to_csv(config.AGGREGATES / "e2_daily_jargon.csv", index=False, encoding="utf-8-sig")

    summary = {
        "utterances": int(len(df)),
        "tokens": total_tokens,
        "curated_candidates": len(items),
        "curated_terms": int(len(stats_df)),
        "terms_with_hits": int(len(stats_df)),
        "terms_all_four_agents": int((stats_df["agents"] == 4).sum()),
        "terms_with_seed_overlap": int(stats_df["seeded"].sum()),
        "top_terms": stats_df.head(20)["term"].tolist(),
    }
    (config.AGGREGATES / "e2_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(stats_df.head(30).to_string(index=False))


if __name__ == "__main__":
    main()
