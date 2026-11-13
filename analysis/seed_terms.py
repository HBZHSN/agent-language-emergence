"""C7: build the T0/T1 seed vocabulary table."""

from __future__ import annotations

import collections

import pandas as pd

from analysis import config, text as T

T0 = [config.PROMPT_DIR / n for n in config.SEED_PROMPTS] + [
    config.PROMPT_DIR / "index.js",
    config.CONFIG_JSON,
]
T1 = [config.SRC / n for n in config.SEED_DOCS]


def main():
    counter = collections.Counter()
    sources = collections.defaultdict(set)
    tiers = {}
    for tier, files in (("T0", T0), ("T1", T1)):
        for p in files:
            if not p.exists():
                continue
            for tok in T.tokenize(p.read_text(encoding="utf-8", errors="ignore")):
                counter[tok] += 1
                sources[tok].add(p.name)
                tiers.setdefault(tok, tier)
    rows = [
        {"term": t, "tier": tiers[t], "count": c, "sources": ",".join(sorted(sources[t])), "seeded": True}
        for t, c in counter.most_common()
    ]
    df = pd.DataFrame(rows)
    df.to_csv(config.AGGREGATES / "c7_seed_terms.csv", index=False, encoding="utf-8-sig")
    summary = {
        "terms": int(len(df)),
        "t0_terms": int((df.tier == "T0").sum()),
        "t1_terms": int((df.tier == "T1").sum()),
        "top": df.head(20)[["term", "tier", "count"]].to_dict(orient="records"),
    }
    import json

    (config.AGGREGATES / "c7_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
