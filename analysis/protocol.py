"""Protocol and schema standardization: verdict JSON and tool input grammars."""

from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from analysis import config, text as T

VERDICT_KEYS = {"decision", "summary", "evidence"}
DECISIONS = {"healthy", "main", "human"}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    u = pd.read_parquet(config.DERIVED / "utterances.parquet")
    u["time_utc"] = pd.to_datetime(u["time_utc"], utc=True)
    t = pd.read_parquet(config.DERIVED / "tool_calls.parquet")
    t["time_utc"] = pd.to_datetime(t["time_utc"], utc=True)
    t["official"] = t["tool_name"].isin(config.OFFICIAL_TOOLS)
    return u, t


def verdicts(u: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in u[(u.agent == "watchdog") & (u.act == "verdict")].iterrows():
        obj = T.extract_verdict(r["text"])
        if not obj:
            rows.append({"time_utc": r["time_utc"], "valid": False, "decision": None, "summary_len": None, "evidence_n": None, "keys": "", "order_ok": False})
            continue
        keys = list(obj.keys())
        ev = obj.get("evidence")
        rows.append(
            {
                "time_utc": r["time_utc"],
                "valid": True,
                "decision": obj.get("decision"),
                "summary_len": len(str(obj.get("summary") or "")),
                "evidence_n": len(ev) if isinstance(ev, list) else None,
                "keys": ",".join(keys),
                "order_ok": keys[:3] == ["decision", "summary", "evidence"],
                "path_mentions": sum(1 for x in ev if isinstance(x, str) and ("\\" in x or "/" in x)) if isinstance(ev, list) else 0,
            }
        )
    out = pd.DataFrame(rows)
    out["date"] = out["time_utc"].dt.strftime("%Y-%m-%d")
    return out


def schema(t: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    daily = []
    for tool, sub in t[t.official].groupby("tool_name"):
        if len(sub) < 10:
            continue
        keysets = sub["input_keys"].fillna("").tolist()
        canonical = Counter(keysets).most_common(1)[0][0]
        canonical_set = set(canonical.split(",")) if canonical else set()
        exact = (sub["input_keys"].fillna("") == canonical).mean()
        jacc = []
        for ks in keysets:
            s = set(ks.split(",")) if ks else set()
            jacc.append(len(s & canonical_set) / max(1, len(s | canonical_set)))
        rows.append(
            {
                "tool": tool,
                "calls": int(len(sub)),
                "canonical_keys": canonical,
                "exact_match": round(float(exact), 4),
                "mean_jaccard": round(float(sum(jacc) / len(jacc)), 4),
                "distinct_keysets": int(len(set(keysets))),
            }
        )
        sub = sub.copy()
        sub["date"] = sub["time_utc"].dt.strftime("%Y-%m-%d")
        for date, g in sub.groupby("date"):
            daily.append(
                {
                    "tool": tool,
                    "date": date,
                    "calls": int(len(g)),
                    "exact_match": round(float((g["input_keys"].fillna("") == canonical).mean()), 4),
                    "distinct_keysets": int(g["input_keys"].fillna("").nunique()),
                }
            )
    return pd.DataFrame(rows).sort_values("calls", ascending=False), pd.DataFrame(daily)


def main():
    u, t = load()
    v = verdicts(u)
    v.to_csv(config.AGGREGATES / "e7_verdicts.csv", index=False, encoding="utf-8-sig")
    s, sd = schema(t)
    s.to_csv(config.AGGREGATES / "e7_schema.csv", index=False, encoding="utf-8-sig")
    sd.to_csv(config.AGGREGATES / "e7_schema_daily.csv", index=False, encoding="utf-8-sig")

    valid = v[v.valid]
    summary = {
        "verdict_attempts": int(len(v)),
        "valid_verdicts": int(v.valid.sum()),
        "valid_rate": round(float(v.valid.mean()), 4),
        "order_ok_rate": round(float(v.order_ok.mean()), 4),
        "decision_counts": valid.decision.value_counts().to_dict(),
        "decision_off_schema": int((~valid.decision.isin(DECISIONS)).sum()),
        "mean_summary_len": round(float(valid.summary_len.mean()), 1),
        "mean_evidence_n": round(float(valid.evidence_n.mean()), 2),
        "evidence_gt_6": int((valid.evidence_n > 6).sum()),
        "tools_with_schema": int(len(s)),
        "mean_exact_match": round(float(s.exact_match.mean()), 4),
        "mean_jaccard": round(float(s.mean_jaccard.mean()), 4),
        "top_schema": s.head(10).to_dict(orient="records"),
    }
    (config.AGGREGATES / "e7_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(s.head(15).to_string(index=False))
    print(v.groupby("date").agg(attempts=("valid", "size"), valid=("valid", "sum")).to_string())


if __name__ == "__main__":
    main()
