# 内部审稿清单

## 研究问题与论证

- [x] 六个 RQ 都在正文中有对应小节，且开头说明“这一节回答哪个 RQ”。
- [x] 每个 RQ 都有至少一个表/图/数字支撑。
- [x] 结论区分描述、相关、因果；没有把观察性关联写成因果。
- [x] 对“语言”的定义是操作化的五层框架，没有泛化为意识/理解。
- [x] 承认单系统、单模型、8 天、主会话缺口等限制。

## 数据与数字

- [x] 所有数字来自 `data/aggregates/` 或 `data/manifest/`。
- [x] 9.64B 明确说明是累计输入 token，不是独立消息数。
- [x] 2,202/110,413/116,131/154/43,829 等核心数字与源库一致。
- [x] 69 词、64 个四 Agent 共用、39 main-first/28 child-first 与 CSV 一致。
- [x] `valution` 2,283 次、249,092,664 token、23.8% 与 CSV 一致。
- [x] 分类器 macro-F1=0.653、watchdog F1=0.932、main F1=0.332 与 JSON 一致。
- [x] 收敛 12h/24h 斜率与 p/q 与 CSV 一致。
- [x] 压缩 ρ 与 CSV 一致；解释了回归符号相反的共线性。
- [x] 事件/结果关联标注了探索性、样本量与 FDR。

## 方法

- [x] 数据源只读；没有修改 `C:\path\to\valuation`。
- [x] 产品名/代码脱敏；公开聚合不含敏感信息。
- [x] 分词/清洗/种子词表/词项审定有文档。
- [x] 分类器按 session 分组交叉验证。
- [x] 收敛有零模型；趋势有 bootstrap CI。
- [x] 多重比较有 BH-FDR 或明确说明。
- [x] 复现命令可跑通；manifest 可校验。

## 写作

- [x] 摘要包含问题、数据、方法、四个发现、局限。
- [x] 引言讲清“起因—经过—结果”。
- [x] 相关工作覆盖涌现通信、LLM 多 Agent、语言收敛/社会方言、工具协议。
- [x] 每个图表在正文中被引用。
- [x] 参考文献 40 条，正文引用与文献表对应。
- [x] 案例引用有 message_id/时间/Agent；产品信息脱敏。
- [x] 附录包含数据字典、工具清单、复现、伦理。

## 交付

- [x] `paper/paper.md`（约 4.9 万字符）。
- [x] `paper/paper.html`。
- [x] `paper/paper.pdf`（46 页）。
- [x] `paper/figures/` 12 幅图。
- [x] `paper/tables/` 14 张表。
- [x] `python -m analysis.privacy_check --all` 通过。
- [x] git 历史完整；最终 tag 待打。

## 待办

- [x] `python -m analysis.run_all --check` 最终跑通（G1）。
- [x] 30 个数字人工对账（G2）。
- [x] 最终 tag `v1.0-paper`（G4）。
