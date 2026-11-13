"""Diffusion direction of curated terms: main-first vs child-first."""

from __future__ import annotations

import json

import pandas as pd

from analysis import config


def main():
    d = pd.read_csv(config.AGGREGATES / "e2_term_stats.csv")
    for col in ["first_time", "first_main_time", "first_child_time", "last_time"]:
        d[col] = pd.to_datetime(d[col], format="ISO8601", utc=True, errors="coerce")
    rows = []
    for _, r in d.iterrows():
        fm, fc = r["first_main_time"], r["first_child_time"]
        if pd.isna(fm) and pd.isna(fc):
            direction = "no-main-no-child"
        elif pd.isna(fm):
            direction = "child-only"
        elif pd.isna(fc):
            direction = "main-only"
        elif fm < fc:
            direction = "main-first"
        elif fc < fm:
            direction = "child-first"
        else:
            direction = "same-timestamp"
        lag = None
        if pd.notna(fm) and pd.notna(fc):
            lag = (fc - fm).total_seconds() / 60
        rows.append(
            {
                "term": r["term"],
                "category": r["category"],
                "count": int(r["count"]),
                "first_voice": r["first_voice"],
                "first_main_time": fm,
                "first_child_time": fc,
                "direction": direction,
                "lag_minutes": None if lag is None else round(float(lag), 2),
                "seeded": bool(r["seeded"]),
            }
        )
    out = pd.DataFrame(rows).sort_values(["direction", "count"], ascending=[True, False])
    out.to_csv(config.AGGREGATES / "e2_diffusion_direction.csv", index=False, encoding="utf-8-sig")

    summary = {
        "terms": int(len(out)),
        "directions": out.direction.value_counts().to_dict(),
        "first_voice": out.first_voice.value_counts().to_dict(),
        "seeded_terms": out[out.seeded].term.tolist(),
        "main_first_top": out[out.direction == "main-first"].head(10)[["term", "count"]].to_dict(orient="records"),
        "child_first_top": out[out.direction == "child-first"].head(10)[["term", "count"]].to_dict(orient="records"),
        "median_lag_minutes": round(float(out.lag_minutes.abs().median()), 1),
    }
    (config.AGGREGATES / "e2_diffusion_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
