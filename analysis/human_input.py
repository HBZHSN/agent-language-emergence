"""Human input baseline: how much of the language was seeded by the human?"""

from __future__ import annotations

import json

import pandas as pd

from analysis import config, text as T


def main():
    m = pd.read_parquet(config.DERIVED / "messages.parquet")
    u = m[m.type == "user"].copy()
    by_agent = u.groupby("agent").size().to_dict()
    main_user = u[u.agent == "main"]
    human_text = main_user["text"].tolist()
    human_chars = int(main_user["text_len"].sum())
    # Child user messages are authored by main/harness, not by a human.
    child = u[u.agent.isin(["parser", "reviewer", "watchdog"])]
    rows = [
        {"category": "human_user_message", "count": int(len(main_user)), "chars": human_chars},
        {"category": "main_authored_dispatch", "count": int((u.agent.isin(["parser", "reviewer"])).sum()), "chars": int(child[child.agent.isin(["parser", "reviewer"])]["text_len"].sum())},
        {"category": "harness_watchdog_task", "count": int((u.agent == "watchdog").sum()), "chars": int(child[child.agent == "watchdog"]["text_len"].sum())},
    ]
    out = pd.DataFrame(rows)
    out.to_csv(config.AGGREGATES / "e11_human_input.csv", index=False, encoding="utf-8-sig")
    summary = {
        "user_messages": int(len(u)),
        "by_agent": by_agent,
        "human_messages": int(len(main_user)),
        "human_chars": human_chars,
        "human_text_is_status_query": all("任务" in t or "完成" in t for t in human_text),
        "human_share_of_user_messages": round(float(len(main_user) / max(1, len(u))), 6),
        "seed_terms_in_prompts": len(T.CUSTOM_TERMS),
        "note": "Only one human turn exists; all task instructions and corrections are agent/harness generated.",
    }
    (config.AGGREGATES / "e11_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
