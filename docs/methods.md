# 方法附录

本文件是论文第 4 节的操作版，目的是让读者不看代码也能复现口径。

## 1. 数据抽取

源数据只读：

- `opencode.db`：`session_v2`、`session_message`；工具调用嵌在 assistant `content[]` 的 `type=="tool"` 元素中。
- `valuation.db`：`products`、`sources`、`jobs`、`job_samples`、`releases`、`bindings`、`results`、`watchdog_events`。
- 文件系统：`data/snapshots/`、`data/jobs/`、`data/results/`。

`analysis/extract.py` 生成：

- `data/derived/messages.parquet`：110,413 行；
- `data/derived/tool_calls.parquet`：116,131 行；
- `data/derived/utterances.parquet`：23,486 行（含 job 摘要、Watchdog 事件）；
- `data/derived/dispatches.parquet`：3,437 行；
- `data/derived/jobs.parquet`：154 行；
- `data/aggregates/c6_outcomes.csv`：154 行。

## 2. 话语分类

`analysis/extract.py::classify_act`：

- `user` + main → `human_status`（全库 1 条）；
- `user` + watchdog → `watchdog_task`（2,004 条）；
- `user` + parser/reviewer → `dispatch`（1,432 条）；
- `synthetic` → `notification`；
- `compaction` → `compaction`；
- Watchdog assistant 且文本以 `{` 开头并含 `"decision"` → `verdict`（1,119 条）；
- 其他 Watchdog assistant → `watchdog_other`；
- 其他 assistant 按关键词分为 `report`、`audit`、`directive`、`status`、`other`。

分类只用于分层描述；论文的主要词频统计不依赖 `report/audit` 的细分。

## 3. 清洗

`analysis/text.py::clean_prose`：

1. 产品名/代码替换为 `PRODUCT`/`CODE`（源库读取，不写盘）。
2. 删除 fenced code、inline code、JSON 对象/数组（迭代 8 次）、HTML、URL、Windows/POSIX 路径、UUID、长哈希、数字。
3. 删除固定模板（“You are a subagent spawned by another session.”、Watchdog 任务模板）。
4. 删除含大量引号/冒号的序列化行。
5. 标点归一为空格，压缩空白。

分词：中文 jieba + 261 个自定义词；英文/代码标识符整体保留；过滤停用词、单字（保留 `壳/红/绿/刀/卷` 等 20 个单字行话）、生成 ID（`job123`、`ses_...`、长哈希）。

## 4. 种子词表

- **T0**：`valuation/opencode/main.md`、`parser.md`、`reviewer.md`、`watchdog.md`、`contracts.md`、`index.js` 工具描述、`data/opencode/config.json` 的 system prompt。
- **T1**：`README.md`、`AGENTS.md`、`方案.md`。

`is_seeded(term)` = `term.casefold()` 是 T0/T1 合并文本的子串。这个标准偏保守。

## 5. 词项审定

1. 候选：词 unigram/bigram/trigram + 中文 2–6 字 n-gram；频次 ≥ 20；≥ 2 个 Agent；≥ 5 个 session。
2. 过滤：T0/T1 子串命中；纯数字/ID/路径；长度 < 2（除单字行话）。
3. 人工审定：两位标注者独立看 Top 300，按“是否承担协调功能”二分类；分歧讨论。最终 69 词，分六类：closure、ruling、evidence、status、repair、ritual。

## 6. 指标

**频次/广度**：子串计数、出现话语数、Agent 数、session 数、job 数、首末时间、存活天数、每万 token 速率。

**扩散方向**：
- main voice = `dispatch` + `job_summary` + `job_instruction` + main assistant；
- child voice = parser/reviewer assistant；
- watchdog voice = verdict；
- `main-first` if first_main < first_child；`child-first` if first_child < first_main；`same-timestamp` if equal；`main-only`/`child-only` if one side missing。
- lag = first_child − first_main（分钟）；负值表示 child 先。

**角色方言**：
- 对数几率比（Monroe et al. 2008）：对每个 Agent，计算词 w 在该 Agent 与其余 Agent 的计数，使用 informative Dirichlet prior α=0.5，z = delta / sqrt(var)。
- 分类器：TF-IDF（词 1–2 gram，min_df=3，max_features=60,000，sublinear_tf），逻辑回归（C=2，class_weight=balanced），按 session 分组 5 折交叉验证。main 的 job summary 单独成组 `job:<id>`。

**收敛**：
- 12 小时或 24 小时窗；每个 voice 的 unigram 分布（全局 Top 4,000 词，add-1 平滑）。
- JS 距离（base 2）。
- Null：从两个 voice 的合并分布中，按各自 token 数抽 multinomial 样本，重复 60 次，取 JS 均值；excess = observed − null。
- 趋势：OLS slope/day；2,000 次窗口 bootstrap 95% CI；BH-FDR 对 6 个 pair。

**压缩**：
- 每个 job/role 的首次派工；字符数、token 数、信息槽位（job_id/scope/samples/evidence/forbid/sequence/verdict/round 的正则命中数）、模板相似度（char 3–5 gram TF-IDF，与同角色前序派工的最大余弦）、行话密度（69 词/千 token）。
- Spearman；带日固定效应 OLS 作为敏感性（job 顺序与日期共线，回归不作为主结论）。

**工具变异**：
- 官方工具集合 + Levenshtein 距离；按 tool_name 聚合 calls/errors/success rate/first/last/input_keys。
- `valution` 的 schema 分类：`sql`、`agent`、`job_id`、`product_id`、`empty`。
- 连续 run：按主 Agent 工具序列，统计连续 `valution` 的长度；条件概率 P(next=valution | prev=valution) vs P(next=valution | prev≠valution)。
- token 成本：message_id 关联 `messages.parquet` 的 `tokens_input`。

**协议**：
- Watchdog JSON：`json.loads` 成功 + 含 decision/summary/evidence；key 顺序；decision 枚举；evidence 数量。
- 工具 schema：每个工具最频繁 key 集合为 canonical；exact match = 完全相同；Jaccard = 集合交并比；按日统计 distinct keysets。

**事件对齐**：
- 6 小时窗；新词首现数；trial/validate 错误；Watchdog main 判决；valution 调用；token；job 数。
- Spearman + Poisson GLM（log token offset）；BH-FDR 对 4 个相关；报告为探索性。

**结果关联**：
- job 级：派工行话密度、派工 token、trial/validate 调用/错误、Watchdog main、rounds/duration/failed。
- Spearman；Poisson GLM（active jobs，n=90）控制派工 token；只有 5 个 failed/deferred，不做稳定 logistic。

## 7. 统计

- Seed=42（bootstrap/零模型）。
- 分类器 GroupKFold(5) by session。
- Bootstrap 2,000 次（趋势/稳健性）；零模型 60 次/窗。
- BH-FDR：收敛 6 个 pair；事件 4 个相关；结果 2 个相关。
- 所有 p 值双侧；报告原始 p 与 q（或说明探索性）。

## 8. 复现边界

- 主会话 48.7% token 无消息级记录；早主 Agent 语言通过派工保留。
- 源库产品名/代码不进入公开聚合。
- `cost=0` 是未配置价格，不是真实免费。
- 结果数量不等于财务正确性。
