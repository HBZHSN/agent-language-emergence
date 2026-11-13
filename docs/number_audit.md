# 数字对账表

本表列出论文中最关键的数字及其来源。`analysis/number_audit.py` 自动对账 33 项（v1.1 起含病理结构三项与 PDF 页数），结果写 `data/aggregates/g2_number_audit.csv`；本表给出人工基准。

| # | 数字 | 论文位置 | 来源文件 | 字段/口径 |
| ---: | --- | --- | --- | --- |
| 1 | 2,202 会话 | 摘要/3.4 | `b1_opencode_summary.json` | `sessions` |
| 2 | 110,413 消息 | 摘要/3.4 | `b1_opencode_summary.json` | `messages` |
| 3 | 102,270 assistant | 3.4 | `b1_message_types.csv` | `assistant` |
| 4 | 3,437 user | 3.4 | `b1_message_types.csv` | `user` |
| 5 | 116,131 工具调用 | 摘要/3.4 | `b1_opencode_summary.json` | `tool_calls` |
| 6 | 103,339 completed / 12,791 error | 3.4 | `data/derived/tool_calls.parquet` | `status` |
| 7 | 9,643,030,091 输入 token | 摘要/3.4 | `b1_opencode_summary.json` | `session_tokens_input` |
| 8 | 32,736,566 输出 token | 3.4 | `b1_opencode_summary.json` | `session_tokens_output` |
| 9 | 123 产品 | 摘要/3.4 | `b2_valuation_summary.json` | `products` |
| 10 | 43,870 源文件 | 摘要/3.4 | `b2_table_counts.csv` | `sources` |
| 11 | 43,829 结果 | 摘要/3.4 | `b2_table_counts.csv` | `results` |
| 12 | 720 active binding | 摘要/3.4 | `b2_valuation_summary.json` | `bindings_active` |
| 13 | 19 release | 摘要/3.4 | `b2_valuation_summary.json` | `releases` |
| 14 | 154 job | 摘要/3.4 | `b2_table_counts.csv` | `jobs` |
| 15 | 149 active / 4 failed / 1 deferred | 3.4 | `b2_jobs_by_status.csv` | `status` |
| 16 | 43,632 active / 197 conflict | 3.4 | `b2_results_by_status.csv` | `status` |
| 17 | 1 条人类消息（12 字符） | 3.5/5.9 | `e11_summary.json` | `human_messages` / `human_chars` |
| 18 | 69 个审定词项 | 5.1 | `e2_summary.json` | `curated_terms` |
| 19 | 64 个四 Agent 共用 | 5.1 | `e2_summary.json` | `terms_all_four_agents` |
| 20 | 39 main-first / 28 child-first | 5.1 | `e2_diffusion_summary.json` | `directions` |
| 21 | `逐字` 8,950 次 | 5.1/表3 | `e2_term_stats.csv` | `count` |
| 22 | `收口` 3,231 次 | 5.1/表3 | `e2_term_stats.csv` | `count` |
| 23 | `单发` 2,536 次 | 5.1/表3 | `e2_term_stats.csv` | `count` |
| 24 | macro-F1 0.653 | 5.2 | `e3_classifier_all.json` | `macro_f1` |
| 25 | Watchdog F1 0.932 | 5.2 | `e3_classifier_all.json` | `report.watchdog.f1-score` |
| 26 | main F1 0.332 | 5.2 | `e3_classifier_all.json` | `report.main.f1-score` |
| 27 | mean JS 0.4228 / null 0.2299 / excess 0.1929 | 5.3 | `e4_summary.json` | `mean_js` 等 |
| 28 | main–reviewer 12h slope −0.0152, p=0.012, q=0.072；24h −0.0173, p=0.007, q=0.020；main–watchdog 24h −0.0199, p=0.002, q=0.014 | 5.3 | `e4_trends.csv` / `e4_trends_24h.csv` | `excess_js` |
| 29 | 行话 vs rounds（有派工）ρ=0.253, p=0.0135 | 5.8 | `e9_summary.json` | `jargon_rounds_with_dispatch` |
| 30 | `valution` 2,283 次 / 249,092,664 token / 23.8% | 5.5 | `e6_summary.json` | `valution_calls` / `valution_tokens_input` / `valution_token_share_of_day` |
| 31 | `valution` 最大连续 run 2,271 | 5.5 | `e6_summary.json` | `main_valution_max_run` |
| 32 | 1,119 判决 / 923 合法 / 82.5% | 5.6 | `e7_summary.json` | `verdict_attempts` / `valid_verdicts` / `valid_rate` |
| 33 | healthy 601 / main 321 / human 1 | 5.6 | `e7_summary.json` | `decision_counts` |
| 34 | `grep` 151 次全部 error | 5.5 | `b1_tool_summary.csv` | `grep` 行 |
| 35 | 56 页 PDF | 交付 | `paper/paper.pdf` | `pypdf` 页数 |
| 36 | `valution` 50 爆发 / 49 次重新点火均有 synthetic 触发 / 存活 4.61 天 | 5.5/6.4 | `e6_summary.json` / `e6_burst_onsets.csv` | `main_valution_bursts` / `main_valution_reonsets_with_synthetic_trigger` / `valution_lifespan_days` |
| 37 | 停顿 612.5–643.0s、合计 8.46h（93%）；触发时差中位 1.46s | 5.5 | `e6_summary.json` | `main_valution_pause_*` / `synthetic_trigger_delta_median_s` |
| 38 | 去 Watchdog 三分类 macro-F1 0.568；本嗓 main F1 0.000 | 5.2/附录A2 | `e3_classifier_nowd.json` / `e3_classifier_own.json` | `macro_f1` / `report.main.f1-score` |
| 39 | E9 负二项行话系数 0.212, p=0.010；E8 负二项 watchdog_main p=0.287 | 5.7/5.8 | `e9_summary.json` / `e8_summary.json` | `regression_rounds_nb` / `regression_nb` |
| 40 | 回报侧首份 n=173（parser 85/reviewer 88），行话 ρ=+0.444/+0.221 | 5.4 | `e5_summary.json` / `e5_report_features.csv` | `reports` |

## 对账方法

```powershell
python -c "import json; d=json.load(open('data/aggregates/b1_opencode_summary.json',encoding='utf-8')); print(d['sessions'], d['messages'], d['session_tokens_input'])"
python -c "import pandas as pd; print(pd.read_csv('data/aggregates/e2_term_stats.csv').query('term==\"单发\"')[['count']].iloc[0,0])"
```

## 已知差异

- 论文中 `2,271` 是“主 Agent 工具序列中的最大连续 run”；`2,283` 是全部 `valution` 调用（含 Watchdog 6 次）。两者不要混用。
- 论文中 `249,092,664` 是全部 `valution` 消息的 `tokens_input`；`248,814,095` 是主 Agent 部分。
- 论文中 `0.238` 是 `249,092,664 / 1,045,540,166`（11-10 当日输入 token）。
- 论文中 `macro-F1=0.653` 是 `e3_classifier_all.json`（含 `watchdog_other`）；早期运行（不含 watchdog_other）是 0.687，已在版本中替换。最终以 0.653 为准。
- v1.1：bootstrap 主结果 5,000 次，12h main–reviewer p 由 0.015 变为 0.012；表 7 增加 q 列。事件级 Poisson 显著项在负二项下不显著，论文已降级为假说。`valution` 间隔统计以 `e6_summary.json` 实测为准（中位 0.93s，49 次 ~10.3min 停顿）。
