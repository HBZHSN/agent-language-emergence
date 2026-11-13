# 数据字典

本文件只描述本研究实际使用的表与字段。所有字段名以只读源库的真实 schema 为准（`sqlite_master`）。

## 1. `opencode.db`

路径：`C:\path\to\valuation\data\opencode\state\opencode\opencode.db`

### 1.1 `session_v2`（2,202 行）

| 字段 | 含义 | 本研究用法 |
| --- | --- | --- |
| `id` | 会话 ID（`ses_…`） | 主键；关联 `session_message.session_id` |
| `parent_id` | 父会话 ID | 识别 main→parser/reviewer/watchdog 的父子关系 |
| `slug` | 会话短名 | 辅助识别 |
| `title` | 会话标题 | Watchdog 标题形如 `job 108 的 Watchdog` |
| `directory` | 工作目录 | 固定为估值项目根目录 |
| `version` | OpenCode 版本 | 2.0.32 |
| `agent` | Agent 名 | `valuation-main/parser/reviewer/watchdog` |
| `model` | 模型 JSON | `swift-1.5` / provider `valuation` |
| `tokens_input` | 累计输入 token | 10B 口径来源；上下文重复计费 |
| `tokens_output` | 输出 token | 用于输出规模 |
| `tokens_reasoning` | 推理 token | 本部署为 0（thinking 关闭） |
| `tokens_cache_read/write` | 缓存 token | 本部署为 0 |
| `cost` | 费用 | 本部署 provider 未配置价格，恒为 0 |
| `time_created` | 创建时间（ms） | UTC；换算 `datetime(ms/1000,'unixepoch')` |
| `time_updated` | 更新时间（ms） | 会话结束/最后活动 |
| `idle_outcome` | 空闲结果 | 辅助判断会话是否成功结束 |

### 1.2 `session_message`（110,413 行）

| 字段 | 含义 | 本研究用法 |
| --- | --- | --- |
| `id` | 消息 ID（`msg_…`） | 案例引用 |
| `session_id` | 会话 ID | 关联 `session_v2` |
| `type` | `assistant/user/synthetic/idle/compaction/system/model-switched/agent-switched` | 语料分层 |
| `seq` | 会话内序号 | 重建对话顺序 |
| `time_created` | 创建时间（ms） | 时间线 |
| `data` | JSON 字符串 | 见下 |

`data` 的常见结构：

- assistant：`{time, agent, model, content:[{type:"text",text}|{type:"tool",name,state,input,content,error}], finish, tokens, cost}`
- user：`{time, text}`
- synthetic：`{time, text}`
- idle：`{time, ...}`
- compaction：压缩摘要相关字段
- system：系统注入消息

### 1.3 工具调用（嵌在 assistant `content` 中）

| 字段 | 含义 |
| --- | --- |
| `name` | 工具名；可能包含变异名（如 `valution`） |
| `state.status` | `completed/error/streaming` |
| `state.input` | 工具参数（JSON） |
| `state.content` | 工具结果（JSON 字符串，通常含 `content[].text`） |
| `state.error` | 错误对象（`type/message`） |
| `time.created/ran/completed` | 调用时间线 |

## 2. `valuation.db`

路径：`C:\path\to\valuation\data\valuation.db`

### 2.1 `products`（123 行）

| 字段 | 含义 |
| --- | --- |
| `id` | 产品 ID |
| `identity` | 稳定标识（目录/来源 + 基金代码） |
| `name` | 产品全称（论文中脱敏） |
| `code` | 基金代码（如 P001） |
| `path` | 共享目录相对路径 |
| `rule_error/rule_start/rule_end/rule_binding_id` | 当前规则状态 |

### 2.2 `sources`（43,870 行）

| 字段 | 含义 |
| --- | --- |
| `id` | 源文件 ID |
| `product_id` | 产品 |
| `directory/relative_path` | 文件位置 |
| `size/mtime_ns` | 文件元数据 |
| `content_hash` | 内容摘要 |
| `snapshot_path` | 不可变快照路径 |
| `signature` | 格式签名 |
| `status` | `baseline/parsed/failed/...` |
| `layout_hash/layout_json` | 粗粒度版式 |

### 2.3 `jobs`（154 行）与 `job_samples`（3,080 行）

`jobs` 记录产品级任务：`id/product_id/status/instruction/child_session/review_session/module/library_hash/rounds/scope_start/scope_end/error/watchdog_*`。`status` 观测值为 `active/failed/deferred`。

`job_samples` 记录每个 job 抽样的 20 份（不足 20 全部）原始文件及其签名。

### 2.4 `releases`（19 行）与 `bindings`（720 行）

- `releases.hash`：整库不可变代码快照摘要。
- `bindings`：`product_id + signature → module + release_hash + start_date/end_date + status + origin`。720 条全部为 `active`。

### 2.5 `results`（43,829 行）

| 字段 | 含义 |
| --- | --- |
| `id` | 结果 ID |
| `product_id/source_id` | 产品/源文件 |
| `release_hash/module` | 使用的 release 与模块 |
| `valuation_date` | 估值日期 |
| `share_class/currency` | 份额类别/币种 |
| `status` | 结果状态（有效/冲突等） |
| `unit_nav/cumulative_nav/shares/net_assets/total_assets/total_liabilities` | 十进制字符串 |
| `record_hash` | 结果摘要 |

### 2.6 明细表

| 表 | 行数 | 含义 |
| --- | ---: | --- |
| `account_lines` | 15,860,739 | 全部原始科目及层级 |
| `holdings` | 9,412,714 | 持仓叶子明细 |
| `cash_balances` | 278,415 | 资金余额 |
| `fee_balances` | 327,160 | 费用余额 |
| `nav_sources` | — | 净值来源单元格 |

金额、净值、比例均为十进制文本；不要用 SQLite `SUM()` 做金额汇总。

### 2.7 `watchdog_events`（7,017 行）

| 字段 | 含义 |
| --- | --- |
| `job_id` | 任务 |
| `action` | 督导动作（inspect/interrupt/notify/…） |
| `state/reason` | 状态与原因 |
| `session_id` | Watchdog 会话 |
| `created_at` | UTC 时间 |

## 3. 文件系统证据

| 路径 | 内容 |
| --- | --- |
| `data/snapshots/<2位>/<sha>.xls[x]` | 原始估值表不可变快照 |
| `data/jobs/<job_id>/workspace/` | 抽样文件副本 |
| `data/jobs/<job_id>/outputs/` | 候选解析输出 |
| `data/jobs/<job_id>/self_check.json` | 解析者正式自检报告 |
| `data/jobs/<job_id>/review-*.json` | 核验者正式报告 |
| `data/jobs/<job_id>/last_failure.json` | 最近失败证据 |
| `data/results/` | 完整结果 JSON（43,829 个） |
| `data/diagnostics/` | 诊断日志 |
| `data/harness-watch/` | 巡检报告、计划、执行记录 |

## 4. 口径提醒

1. `tokens_input` 是每一步的累计输入量，不是唯一文本 token；9.64B 不能解释为 9.64B 条消息。
2. `cost` 恒为 0 是 provider 未配置价格，不是真实免费。
3. `results` 的 `status` 需要先查分布再引用；不要把“有结果”等同于“已人工确认”。
4. `products.name`、`sources.relative_path` 含产品名称，论文中脱敏。
5. 时间统一按 UTC 解释；`datetime('now')` 与 OpenCode 毫秒时间戳都是 UTC。
