# 案例研究（可追溯版）

本文件给出论文第 6 节的五个案例，附 message_id、session_id 可追溯信息。所有产品名/代码/样例已替换为 `[产品]`、`[代码]`、`[样例]`；引用只保留与语言现象有关的片段。

## 案例一：`单发`（主 Agent → parser，3 秒采纳）

- 时间：2026-11-06T13:30:32.152Z
- Agent：parser（主 Agent 派工）
- message_id：`msg_1b10dc53a002fOwZUWaPXpOge5`
- 原文（节选）：

> “本回合=**单发终局重放，零检测零循环**…… valuation_trial(J) 单发：通过 → 回执…… 即停，交主 agent 转 Reviewer validate。”

- 采纳：2026-11-06T13:30:35.310Z，parser，`msg_1b10dd1a8001yTF3l4lcrVCj4F`：

> “## job J 终局单发回执（前置拒，按指令即停）”

- 观察：lag=+0.05 分钟；`单发` 后续覆盖 57 个 job、305 个 session、四个 Agent。
- 解释：主 Agent 在“正门通道用尽”的瓶颈处造词，把“只发一次、不循环、通过即停”压缩成一个动作类别。

## 案例二：`收口` / `对账`（reviewer → 主 Agent，bottom-up）

### `收口`

- 首现：2026-11-04T09:58:54.298Z，reviewer，`msg_1a5ff4c55001I6xhFbCMf7rQSN`：

> “shell 沙箱在收尾阶段返回『没有属于本会话的可执行任务』（会话任务已**收口**），额外的回归项独立细查无法再执行，已作为限制如实记录，不影响本轮批准结论。”

- 主 Agent 采纳：2026-11-04T14:25:48.799Z，parser（主 Agent 派工），`msg_1a6f38070002tIwNNzEcVkhnaC`：

> “主 agent 收口指令……停止 rp1t.py 一行的调试……”

- 观察：lag=−266.9 分钟（4.4 小时）；`收口` 后续 3,231 次、411 个 session、89 个 job。
- 解释：reviewer 在证据收尾的语境中先把“结束”命名为“收口”，主 Agent 后采纳并广播。

### `对账`

- 首现：2026-11-04T09:58:54.298Z，reviewer，同一报告；23 秒后主 Agent 在派工中使用。
- 观察：`对账` 后续 2,421 次、258 个 session、97 个 job；在高风险修复中成为“三方逐字核对”的标准动作。
- 解释：并列于 `收口` 的 bottom-up 案例；说明子 Agent 不只是执行者，也是词汇创新源。

## 案例三：`一刀 + 一发 + 停手`（高风险修复的仪式化压缩）

- 时间：2026-11-11T02:43:17.395Z
- Agent：parser（主 Agent 派工）
- message_id：`msg_1c87ce5c7002T0FlEpbf4kCL0S`
- 原文（节选）：

> “本轮只允许**一刀 + 一发**…… PASSED 即停正式提交。若 trial 后 conservation 第四次零位移：立即停手，把上述实测量 vs 壳逻辑 vs 宿主红面三方对账回帖交主 agent 直裁，不再改壳。”

- 观察：`一刀` 指一次最小编辑，`一发` 指一次正式 trial，`停手` 指收到结果后停止迭代；三词构成一个可审计的动作序列。
- 解释：句法层压缩的典型；与词汇层扩张（`红位/终壳/零位移/盲发`）同时发生。

## 案例四：`valution`（化石词与语义漂白）

- 首现（Watchdog）：2026-11-06T07:11:36.145Z，`msg_1afb263fb001LZCJ2UrGmoIxcB`，输入 `{"sql": "x"}`。
- 首现（主 Agent）：2026-11-10T12:38:46.664Z，`msg_1c577d04d001p9qjZAVBVVve0v`，输入 `{"agent": "valuation-parser"}`。
- 末次：2026-11-10T21:43:58.902Z，`msg_1c76af3a6001vImbMlHw3GHqsl`，输入 `{}`。
- 错误原文：

> “No tool named \"valution\" is currently available. Please use a tool from the available tool list.”

- 图式阶段：
  1. `agent/sessionID`（46 次，想调 subagent）；
  2. `job_id`（600 次，想调 valuation_job）；
  3. `product_id`（455 次，想调 prepare/queue/fast_parse）；
  4. 空参数（1,176 次，泛化重试）。
- 成本：2,283 次调用、249,092,664 输入 token、占 11-10 当日 23.8%；主 Agent 2,277 次、248,814,095 token。
- 重复环：主 Agent 工具序列中 5 个连续 run（3×1、1×3、1×2,271）；2,271 次的 run 是 2,271 条独立 assistant 消息，平均间隔 0.98 秒。
- 条件概率：P(valution | prev=valution)=0.9978；P(valution | prev≠valution)=0.0024；OR≈186,667。
- 解释：语义漂白（一个词形吸收四种 schema）+ 局部上下文自激 + 开放工具词表 + 成本不可见。

## 案例五：Watchdog 判决语法

- 首条判决：2026-11-04T07:39:07.704Z，`msg_1a57f54310012HI0m74ZDrE3pP`：

> `{"decision": "healthy", "summary": "valuation-parser 子会话正在对 data/jobs/J/workspace 下 20 个 .xls 估值表做系统性结构探查……属于真实调试进展而非空转……", "evidence": ["job stage=parser, child ... active", "..."]}`

- 语域：`decision` 三值枚举（healthy/main/human），`summary` 判断，`evidence` 1–6 条可核对证据。
- 全库：1,119 次判决尝试，923 次合法（82.5%）；healthy 601、main 321、human 1；平均 evidence 6.09 条。
- 解释：Watchdog 的语言是协议语言，不是工作语言；它是其他三个 Agent 的只读审计视角，也是分类器最容易识别的角色（F1=0.932）。

## 追溯方式

- `messages.parquet`：按 message_id 查原文、时间、Agent、session。
- `tool_calls.parquet`：按 message_id 查工具名、输入、错误、结果摘要。
- `utterances.parquet`：按 utterance_id 查清洗后话语。
- 所有引用在 `paper/paper.md` 第 6 节；本文件是带 ID 的版本。
