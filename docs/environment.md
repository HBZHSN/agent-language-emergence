# 研究现场与环境

本文件只记录能从源仓库直接核验的事实。带“来源”的事实可在对应文件中复查；没有来源的推断不写。

## 1. 系统定位

`C:\path\to\valuation` 是一套估值表解析、核验与查询平台。业务目标是把共享目录中的 Excel 估值表解析为结构化净值、持仓、资金、费用与科目数据，经过解析者自检和独立核验后发布为不可变 release，并按产品/格式签名/日期时段绑定到日常解析流程。

- 架构：Flask + SQLite（WAL）+ 原生 OpenCode 2.0.32+。
- 角色：1 个主 Agent（调度/督导/启用）+ 解析子 Agent + 核验子 Agent + Watchdog（只读督导）。
- 来源：`README.md`、`AGENTS.md`、`valuation/opencode/*.md`。

## 2. 模型与推理配置

| 项 | 值 | 来源 |
| --- | --- | --- |
| Provider | `valuation`（OpenAI-compatible，`aisdk:@ai-sdk/openai-compatible`） | `data/opencode/config.json` |
| Base URL | `http://<internal-host>/v1` | 同上；`valuation/config.py` 的 `MODEL_URL` 默认值 |
| 模型 | `swift-1.5` | 同上 |
| 上下文上限 | 262,144 tokens | `config.json` 的 `limit.context` |
| 单次最大输出 | 16,384 tokens | `config.json` 的 `limit.output` / `max_tokens` |
| Thinking | 关闭（`chat_template_kwargs.enable_thinking=false`） | `config.json` 的 model body |
| 温度/采样参数 | 未在配置中显式设置，由服务端默认值决定 | `config.json` 无 `temperature`/`top_p` 字段 |
| 价格 | 未配置，`cost` 恒为 0 | `session_v2.cost`、`config.json` |
| 模型参数规模/架构 | 记录未暴露，不作推断 | — |

**重要口径**：`session_v2.tokens_input` 是每一步累计输入量（上下文会重复计费），不是唯一文本 token。全库合计 9,643,030,091；按消息逐条相加为 9,058,762,083，差额主要来自主会话被清理/压缩前的历史（见 `docs/data_quality.md`）。

## 3. Agent 角色与权限

| Agent | 模式 | 步数上限 | 核心权限 | 核心禁止 |
| --- | --- | ---: | --- | --- |
| `valuation-main` | primary | 600 | 业务工具、`subagent` 派工、查询、启用 | 编辑 `parsers/`、`valuation_trial`、`valuation_validate`、shell |
| `valuation-parser` | subagent | 400 | 编辑 `parsers/`、`verification/`（除 `review/`）、`.opencode/checks/`、`.opencode/scratch/`；shell；`valuation_trial` | 启用、调度、改不可变 release、改核验者代码 |
| `valuation-reviewer` | subagent | 400 | 编辑 `verification/`（除 `selfcheck/`）、`.opencode/reviews/`、`.opencode/scratch/`；shell；`valuation_validate`；`review_reject` | 改 `parsers/`、改解析者自检、启用、调度 |
| `valuation-watchdog` | subagent | 40 | 只读 `read/glob/valuation_session_db` | 写文件、shell、派工、业务工具 |

来源：`valuation/opencode/main.md`、`parser.md`、`reviewer.md`、`watchdog.md`；`valuation/opencode/index.js` 的 `primary`/`immediate` 集合与权限断言；`data/opencode/config.json` 的 `agents.*.steps`。

权限边界由插件和 `native.py` 强制，不依赖提示词自觉。主 Agent 的 `subagent` 调用被宿主强制 `background=true`，避免前台子会话阻塞督导与新工作通知（`index.js` 注释与 hook）。

## 4. 工具语法

官方工具分为三类：

1. OpenCode 内置：`read`、`edit`、`write`、`glob`、`grep`、`subagent`、`shell`（被插件替换为沙箱版本）等。
2. 业务工具：`valuation_progress`、`valuation_control`、`valuation_sync`、`valuation_scan`、`valuation_products`、`valuation_queue`、`valuation_prepare`、`valuation_fast_parse`、`valuation_verifier`、`valuation_check_template`、`valuation_job`、`valuation_trial`、`valuation_supervise`、`valuation_session_db`、`valuation_stop`、`valuation_defer`、`valuation_recover`、`valuation_cleanup`、`valuation_validate`、`valuation_review_reject`、`valuation_activate`、`valuation_fail`、`valuation_history`、`valuation_query`、`valuation_confirm`。
3. 观测中出现的非官方形式：`valution`、`valuation_verify`、`grep` 的可用性问题、`valutation_session_db` 等。非官方形式全部报错，详见 E6。

来源：`valuation/opencode/index.js` 的 `definitions`；`analysis/config.py` 的 `OFFICIAL_TOOLS`。

## 5. 运行环境

| 项 | 值 | 来源 |
| --- | --- | --- |
| 宿主 | Windows（win32），PowerShell 7 | 运行环境 |
| 源项目 Python | 3.14.3（venv） | `.venv/pyvenv.cfg` |
| Web 框架 | Flask 3.1.2 + waitress 3.0.2 | `requirements.lock` |
| Excel 读取 | xlrd 2.0.2、openpyxl 3.1.5 | `requirements.lock` |
| OpenCode | 2.0.32 | `session_v2.version` |
| Web 端口 | 5082 | `valuation/config.py` 默认值 |
| OpenCode 端口 | 4097 | 同上 |
| 每日扫描 | 18:00 | `SCAN_TIME` 默认值 |
| 解析并发 | 4 workers | `PARSE_WORKERS` 默认值 |
| 单 job 总时限 | 120 分钟 | `WATCHDOG_MAX_MINUTES` |
| Watchdog 检查间隔 | 3 分钟 | `WATCHDOG_CHECK_MINUTES` |
| 数据库 | SQLite WAL；`data/valuation.db` 约 5.5 GB | 文件系统 |
| 会话库 | `data/opencode/state/opencode/opencode.db` 约 722 MB | 文件系统 |

## 6. 沙箱

解析、核验、shell 探索都在 Docker 容器中执行：

- 镜像：`valuation-shared-parser:1`（195 MB，基于 `python:3.12-slim`）。
- 非 root：`--user 65534:65534`。
- 禁网：`--network none`。
- 只读根：`--read-only`，`/tmp` 为 16 MB tmpfs。
- 资源：`--cpus 1`、`--memory 256m`、`--memory-swap 256m`、`--pids-limit 32`、`--cap-drop ALL`、`--security-opt no-new-privileges`。
- 挂载：`data/jobs` 只读挂载到 `/workspace/data/jobs`；按角色开放 `parsers`/`verification`/`.opencode` 的受限写目录。

来源：`sandbox/Dockerfile`、`valuation/sandbox.py`。

## 7. 业务规模

| 指标 | 值 |
| --- | ---: |
| 产品 | 123 |
| 源文件 | 43,870 |
| 结果 | 43,829（active 43,632；conflict 197） |
| 科目明细 | 15,860,739 |
| 持仓明细 | 9,412,714 |
| 资金余额 | 278,415 |
| 费用余额 | 327,160 |
| 不可变 release | 19 |
| 格式绑定 | 720（全部 active） |
| job | 154（active 149；failed 4；deferred 1） |
| Watchdog 事件 | 7,017 |
| 原始快照 | 43,849 个文件，4.9 GB |
| 完整结果 JSON | 43,829 个文件，14.39 GB |

来源：`data/aggregates/b2_*`、`b3_filesystem_inventory.csv`。

## 8. 时间与观测窗口

- 所有数据库时间按 UTC 解释；SQLite `datetime('now')` 与 OpenCode 毫秒时间戳均为 UTC。
- 会话创建：2026-11-04 07:32:22 UTC（主会话）。
- 第一条消息：2026-11-04 07:36:06 UTC（parser 子会话）。
- 最后一条消息：2026-11-11 05:20:53 UTC（主会话）。
- 观测窗口：2026-11-04 至 2026-11-11，共 8 个自然日（约 190 小时）。

## 9. 需要特别说明的数据缺口

主会话 `ses_abc2242e4d904322ab3222a8750b5d57` 的消息序列从 `seq=28766` 开始，最早保留消息为 2026-11-09 01:29:25 UTC；其 `tokens_input` 为 1,123,380,494，而保留消息逐条相加只有 576,043,588，约 48.7% 的输入 token 对应的事件已不在消息表中。推断为 11-09 前的会话历史被清理/压缩（会话有 33 条 compaction 记录），但清理原因无法从现有数据确定。

这不影响对 11-09 之后主 Agent 直接话语的分析；11-04 至 11-08 的主 Agent 语言主要通过它写给子 Agent 的 756 条 parser 派工、676 条 reviewer 派工和 2,004 条 Watchdog 任务描述保留下来。论文必须把这一点写成方法限制，不能把“主会话缺失”误写成“主 Agent 未活动”。

来源：`data/aggregates/b6_quality.json`、`session_message.seq`。
