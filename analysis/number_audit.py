"""G2: verify the paper's key numbers against aggregate files."""

from __future__ import annotations

import json

import pandas as pd
from pypdf import PdfReader

from analysis import config


def main():
    checks = []
    b1 = json.loads((config.AGGREGATES / "b1_opencode_summary.json").read_text(encoding="utf-8"))
    b2 = json.loads((config.AGGREGATES / "b2_valuation_summary.json").read_text(encoding="utf-8"))
    e2 = json.loads((config.AGGREGATES / "e2_summary.json").read_text(encoding="utf-8"))
    e3 = json.loads((config.AGGREGATES / "e3_classifier_all.json").read_text(encoding="utf-8"))
    e4 = json.loads((config.AGGREGATES / "e4_summary.json").read_text(encoding="utf-8"))
    e6 = json.loads((config.AGGREGATES / "e6_summary.json").read_text(encoding="utf-8"))
    e7 = json.loads((config.AGGREGATES / "e7_summary.json").read_text(encoding="utf-8"))
    e9 = json.loads((config.AGGREGATES / "e9_summary.json").read_text(encoding="utf-8"))
    e11 = json.loads((config.AGGREGATES / "e11_summary.json").read_text(encoding="utf-8"))

    def add(name, actual, expected, source):
        ok = actual == expected
        checks.append({"name": name, "actual": actual, "expected": expected, "ok": ok, "source": source})

    add("sessions", b1["sessions"], 2202, "b1")
    add("messages", b1["messages"], 110413, "b1")
    add("tool_calls", e6["tool_calls"], 116131, "e6")
    add("tokens_input", b1["session_tokens_input"], 9643030091, "b1")
    add("tokens_output", b1["session_tokens_output"], 32736566, "b1")
    add("products", b2["products"], 123, "b2")
    add("sources", b2["table_counts"]["sources"], 43870, "b2")
    add("results", b2["results"], 43829, "b2")
    add("bindings", b2["bindings_active"], 720, "b2")
    add("releases", b2["releases"], 19, "b2")
    add("jobs", b2["table_counts"]["jobs"], 154, "b2")
    add("curated_terms", e2["curated_terms"], 69, "e2")
    add("terms_all_four", e2["terms_all_four_agents"], 64, "e2")
    add("macro_f1", e3["macro_f1"], 0.653, "e3")
    add("watchdog_f1", round(e3["report"]["watchdog"]["f1-score"], 3), 0.932, "e3")
    add("main_f1", round(e3["report"]["main"]["f1-score"], 3), 0.332, "e3")
    add("mean_js", e4["mean_js"], 0.4228, "e4")
    add("mean_excess_js", e4["mean_excess_js"], 0.1929, "e4")
    add("valution_calls", e6["valution_calls"], 2283, "e6")
    add("valution_tokens", e6["valution_tokens_input"], 249092664, "e6")
    add("valution_share", e6["valution_token_share_of_day"], 0.2382, "e6")
    add("valution_max_run", e6["main_valution_max_run"], 2271, "e6")
    add("valution_bursts", e6["main_valution_bursts"], 50, "e6")
    add("valution_reonsets_triggered", e6["main_valution_reonsets_with_synthetic_trigger"], 49, "e6")
    add("valution_lifespan_days", e6["valution_lifespan_days"], 4.61, "e6")
    add("verdicts", e7["verdict_attempts"], 1119, "e7")
    add("valid_verdicts", e7["valid_verdicts"], 923, "e7")
    add("valid_rate", e7["valid_rate"], 0.8248, "e7")
    add("human_messages", e11["human_messages"], 1, "e11")
    add("human_chars", e11["human_chars"], 12, "e11")
    add("jargon_rounds", e9["jargon_rounds_with_dispatch"], 0.253, "e9")
    add("jargon_p", round(e9["jargon_rounds_with_dispatch_p"], 4), 0.0135, "e9")
    add("pdf_pages", len(PdfReader(str(config.PAPER / "paper.pdf")).pages), 56, "paper.pdf")

    df = pd.DataFrame(checks)
    df.to_csv(config.AGGREGATES / "g2_number_audit.csv", index=False, encoding="utf-8-sig")
    print(df.to_string(index=False))
    print("\nFAILED", int((~df["ok"]).sum()), "of", len(df))


if __name__ == "__main__":
    main()
