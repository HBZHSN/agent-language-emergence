# 数据质量审计

对应 `analysis/audit.py`、`data/aggregates/b6_quality.json`。所有数字可由该脚本重跑。

## 1. 总量与口径

| 指标 | 值 | 说明 |
| --- | ---: | --- |
| 会话 | 2,202 | main 1、parser 124、reviewer 111、watchdog 1,966 |
| 消息 | 110,413 | assistant 102,270、user 3,437、idle 3,436、synthetic 874、compaction 244、system 103、model-switched 44、agent-switched 5 |
| 工具调用 | 116,131 | 含成功与失败 |
| assistant 文本片段 | 11,597 | 只统计 `content[].type=="text"` |
| 会话累计输入 token | 9,643,030,091 | `session_v2.tokens_input` 求和；上下文重复计费 |
| 逐条输入 token | 9,058,762,083 | assistant 消息 `tokens.input` 求和 |
| 差额 | 584,268,008 | 占会话口径 6.06% |
| 会话累计输出 token | 32,736,566 | |
| 逐条输出 token | 30,251,259 | |

**结论**：论文可以说“约 96.4 亿累计输入 token（口语称 10B）”，但不能说“96.4 亿条独立消息”或“96.4 亿唯一 token”。逐条口径与累计口径都要在方法中说明。

## 2. 主会话历史缺口（最重要）

- 主会话 `ses_abc2242e4d904322ab3222a8750b5d57` 创建于 2026-11-04 07:32:22 UTC。
- 其 `session_message.seq` 最小值是 **28,766**，最大值 65,277；最早保留消息 2026-11-09 01:29:25 UTC。
- `tokens_input=1,123,380,494`；保留消息逐条相加 `576,043,588`；缺失 **547,336,906**，占 48.72%。
- 会话有 33 条 compaction；其中一条明确 `compaction.failed`（“summary reached the output token limit”），但无法证明这就是历史缺失的唯一原因。
- 影响：
  - 11-04 至 11-08 的主会话直接话语不可用；不能据此说“主 Agent 未活动”。
  - 早主 Agent 的语言通过子会话首条 user 消息保留：parser 756 条、reviewer 676 条、watchdog 2,004 条。
  - 所有涉及“主 Agent 早期用词”的统计必须使用派工文本，而不是主会话消息。
- 论文写法：把“主会话历史截断”写成明确的数据限制，并在附录给出 seq 与 token 证据。

## 3. 重复与空文本

- 完全重复的消息（按 `data` JSON 的 SHA256）：6 组、15 条，占 0.01%；可忽略，但去重分析时要说明。
- assistant 消息中 90,673 条没有 text part（88.66%）。这不是缺失：它们主要是纯工具调用消息。语言分析必须把“文本话语”和“工具调用”分开，否则会把 88% 的工具语法误当自然语言。
- 替换字符 U+FFFD：0。源库文本是有效 UTF-8；PowerShell 控制台乱码只是显示问题。
- 空 assistant content：0（`content` 字段均存在，只是可能没有 text part）。

## 4. 会话—job 映射

- 154 个 job：109 个有 `child_session` 映射到现存会话，104 个有 `review_session` 映射。
- 45 个 job 没有子会话：多为 `fast_parse` 快速通道（rounds=0），属于设计内行为，不是数据丢失。
- 4 个 failed、1 个 deferred；失败/缓办原因保留在 `jobs.error/summary`，但包含产品信息，不能直接提交。
- 论文中的 job 级分析应使用 `job_id` + 脱敏标签，不引用产品名。

## 5. 时区与时间

- OpenCode `time_created` 是毫秒 Unix 时间戳；SQLite `datetime('now')` 是 UTC 字符串；两者可直接比较。
- 会话/消息/结果/Job 的时间均为 UTC。
- 观测窗口：2026-11-04 07:32 至 2026-11-11 05:20 UTC。
- 日界按 UTC 00:00 划分；论文中明确说明，避免与北京时间日界混淆。

## 6. 工具名与错误

- 官方工具 37 个（含 `valuation_*`）。
- 观测到大量非官方名：`valution`（2,283 次，全部 error）、`valuation_verify`（58 次，全部 error）、`valutation_session_db`（13 次）、`valiation_session_db`（12 次）、`valution_session_db`（10 次）、`grep`（151 次，全部 error）等。
- `grep` 是官方内置名但在此部署不可用；它和 `valution` 不同：前者是工具可用性问题，后者是模型生成的词形。
- 工具错误总数：主 2,426、parser 1,900、reviewer 2,498、watchdog 5,967。Watchdog 的错误率高，主要因为它用 `valuation_session_db` 试探 schema/表名（3,808 次 error）。
- 论文中不能把“工具 error”一律当作业务失败；`valuation_trial/validate` 的 error 很多是检查未通过（正常业务反馈）。

## 7. 业务状态

- 结果：43,829 条，其中 active 43,632、conflict 197（0.45%）。
- Job：active 149、failed 4、deferred 1。
- Binding：720 条全部 active；release 19 个。
- 这说明“结果写入”覆盖率高，但不等于全部产品都已完成人工确认；论文用“已写入结果”而非“全部验收通过”。

## 8. 成本与模型

- `cost` 全为 0：provider 未配置价格，不是真实免费。
- 模型只有一个：`valuation/swift-1.5`，102,270 条 assistant 消息全部使用它；没有跨模型比较。
- `tokens_reasoning=0`、cache=0：thinking 关闭，无缓存计费。
- 温度/采样参数未在配置中显式设置，不能推断。

## 9. 敏感信息

- 产品名称、基金代码、产品路径、产品-specific 财务值不进入公开聚合。
- `data/private/` 保存完整映射，已 gitignore；`analysis/privacy_check.py` 在提交前扫描。
- 论文案例引用只保留 message_id/session_id/UTC/Agent/脱敏标签。

## 10. 已知但暂不处理的问题

1. 主会话早期消息缺失，无法恢复；只能通过子会话派工文本间接重建。
2. 部分 `idle` 消息的语义未完全解析；本研究只把它计入活动量，不做语言分析。
3. `event` 表在观测窗口内为空；时间线主要由 `session_message` 与业务表重建。
4. `model-switched` / `agent-switched` 消息数量很少，未做单独分析；不影响主结论。
5. 产品名称在源库中可能有历史改名；公开聚合用 product_id 标签，不追踪名称变化。
