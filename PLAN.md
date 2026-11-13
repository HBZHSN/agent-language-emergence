# 研究计划：工具约束下多智能体语言的涌现

> 本文件是本项目唯一的执行清单。每完成一项，将 `[ ]` 改为 `[x]`，在 `docs/log.md` 追加一条记录，并做一次 git commit。
> 数据源只读：`C:\path\to\valuation`。不得修改、移动、删除该目录中的任何文件；所有实验数据必须来自该目录中已经形成的记录。

## 0. 研究目标与交付物

### 0.1 一句话目标

以一套真实生产级多智能体系统（1 个主 Agent + 3 类子 Agent）在 8 天内产生的约 96.4 亿输入 token、110,413 条消息、116,131 次工具调用为自然语料，研究多个 Agent 如何在工具约束下自发形成一套可复用的工作语言，并给出可复核的量化证据、因果叙事与局限性分析。

### 0.2 论文叙事线

- **起因**：123 个基金产品、43,870 份估值表需要被解析、核验、发布；单个模型无法一次完成，系统被拆成主 Agent（调度）、解析 Agent、核验 Agent、Watchdog（督导）四个角色，通过工具调用、文件产物和子会话消息协作。角色之间没有自然语言聊天通道，只有一条窄带宽的“主 Agent 派工—子 Agent 回报”通道，以及共享的代码/JSON/文件系统。这一通信瓶颈构成语言产生的选择压力。
- **经过**：2026-11-04 至 2026-11-11，系统连续运行 154 个 job，产生 2,202 个会话、110,413 条消息、116,131 次工具调用。Agent 在提示词之外逐步发明并稳定使用一套“估值行话/作战方言”：`红位`、`收口`、`单发`、`对账`、`终壳`、`盘面`、`零位移`、`盲发`、`回帖`、`落位`、`直裁` 等；同时出现 `valution` 这类被负反馈包围却持续复现的“化石词”，以及 `valutation_session_db` 等工具名变异。语言既在收敛，也在分化；既有适应性的压缩，也有病理性的漂移。
- **结果**：系统完成 43,829/43,870 份估值表解析（99.9%），形成 720 条 active binding、19 个不可变 release、43,829 条结果、1,586 万条科目明细；但仍有 4 个 failed、1 个 deferred job。论文要同时解释“为什么这套语言有效”和“为什么它没有避免失败”。

### 0.3 研究问题

- **RQ1（词汇涌现）**：哪些词/短语/工具名形式不在种子提示词和项目文档中，却在运行中反复出现并被多个 Agent 采用？它们的首次出现、扩散路径、存活时间是什么？
- **RQ2（角色方言）**：四个 Agent 是否形成可区分的语域（register）？主 Agent 的“裁决体”、解析 Agent 的“实测量体”、核验 Agent 的“审计体”、Watchdog 的“JSON 判决体”各自有哪些特征？
- **RQ3（收敛与分化）**：8 天内 Agent 之间的词汇/风格距离是收敛还是分化？收敛发生在哪些层面，分化又保留在哪些层面？
- **RQ4（压缩与规约化）**：派工提示、回报、纠偏是否随时间变短、变得更模板化，同时保留关键信息？能否量化“通信压缩”？
- **RQ5（选择与病理）**：工具名变异和化石词为什么能持续？工具成功/失败是否构成选择压力？为什么选择没有淘汰 `valution`？
- **RQ6（功能后果）**：语言特征与 job 结果（成功、轮次、Watchdog 干预、失败）是否相关？语言是协调的催化剂还是仅仅是指标？

### 0.4 交付物

1. `paper/paper.md`：完整论文（中文，约 2.0–2.8 万字，含摘要、正文、参考文献、附录）。
2. `paper/paper.html`：自包含排版版本（中文宋体/黑体，A4 打印样式）。
3. `paper/paper.pdf`：由 Edge headless 打印生成，图表完整、页码正确。
4. `paper/figures/`：10 幅左右主图 + 附录图，PNG/SVG，300 dpi。
5. `paper/tables/`：12 张左右主表 + 附录表，CSV 与 Markdown 双份。
6. `analysis/`：可重跑的分析流水线；`python analysis/run_all.py --check` 能从只读数据源重建全部聚合结果。
7. `docs/`：环境说明、数据字典、方法附录、案例研究、复现实验、日志。
8. `data/manifest.json`：源数据库、关键文件、派生数据的 SHA256 与行数清单。
9. 完整 git 历史：每项任务一次 commit；最终 tag `v1.0-paper`。

### 0.5 非目标

- 不训练新模型，不做干预实验，不修改生产系统。
- 不把“语言”泛化为意识、心智理论或完整自然语言；论文只主张“工具约束下的操作性混合语（operational pidgin）/角色社会方言（sociolect）”。
- 不用合成数据替代真实记录；零模型/置换检验只用于统计推断，并明确标注。

---

## 1. 阶段 A：项目治理与可复现基线

- [x] **A1. 初始化仓库与目录**
  - 建立 `analysis/`、`paper/`、`docs/`、`data/aggregates/`、`data/manifest/`、`tools/`。
  - 写 `.gitignore`：排除 `.venv/`、`__pycache__/`、原始导出大文件、临时探针输出；保留脚本、聚合表、图表、论文。
  - 验收：`git status` 干净；目录结构在 README 中说明。

- [x] **A2. 写 AGENTS.md**
  - 说明数据源只读、不得泄露 `.env`/密钥、不得查询 `credential/account/kv` 等敏感表。
  - 说明续跑协议：先读 `PLAN.md`，取第一个未勾选项；完成后勾选、写日志、commit。
  - 说明环境、命令、编码注意事项、证据标准、论文规范。
  - 验收：一个新 Agent 只读 AGENTS.md + PLAN.md 就能知道下一步做什么。

- [x] **A3. 写 README.md 与数据字典骨架**
  - README 概述研究问题、数据源、目录、复现命令。
  - `docs/data_dictionary.md` 列出 opencode.db / valuation.db 的关键表、字段、行数口径。
  - 验收：文档中的表名、字段名与真实 schema 一致。

- [x] **A4. 建立只读访问层**
  - `analysis/config.py` 统一管理源路径、派生路径、时间窗口、Agent 名单、官方工具名单。
  - 所有 SQLite 连接使用 `file:...?mode=ro&immutable=1`（或 `mode=ro`），禁止写源库。
  - 验收：连接测试通过；对源库执行写操作会失败。

- [x] **A5. 建立日志与提交规范**
  - `docs/log.md` 记录每项任务的时间、命令、关键数字、commit hash。
  - 约定 commit message：`plan: A1 ...`、`exp: E2 ...`、`paper: ...`。
  - 验收：首次提交包含 PLAN/AGENTS/README/.gitignore。

- [x] **A6. 敏感信息治理与脱敏流水线**
  - 在 AGENTS.md 写死规则：API key、`.env`、密码、产品名、基金代码、产品路径、产品-specific 财务值不得进入 git。
  - 产品统一映射为 `Product NNN` / `PNNN`；完整映射只写 `data/private/`（gitignore）。
  - 实现 `analysis/privacy_check.py`：扫描 `git ls-files`，对源库产品名/代码、密钥模式、`.env` 模式做命中检查；有命中即失败。
  - 实现 `.githooks/pre-commit` 并 `git config core.hooksPath .githooks`。
  - 审计历史提交；如含敏感信息，用 `git filter-repo` 重写历史并记录。
  - 验收：`python analysis/privacy_check.py` 对当前树通过；`git log -p` 不含产品名/代码/密钥。

---

## 2. 阶段 B：现场审计与环境重建

- [x] **B1. 审计 opencode.db 的表结构与规模**
  - 统计 `session_v2`、`session_message`、`event`、`instruction_*` 等表的行数、时间范围、agent 分布、model 分布。
  - 口径：会话数、消息数、assistant/user/synthetic/idle/compaction 数、工具调用数、文本片段数。
  - 验收：生成 `data/aggregates/b1_opencode_inventory.csv` 与一段可引用摘要。

- [x] **B2. 审计 valuation.db 的业务规模**
  - 统计 products、sources、jobs、job_samples、releases、bindings、results、account_lines、holdings、cash_balances、fee_balances、watchdog_events 的行数与状态分布。
  - 统计每个产品的结果数、文件数、绑定数、失败数；按日统计 job/result 增量。
  - 验收：生成 `data/aggregates/b2_valuation_inventory.csv`；与 README 中的业务描述交叉核对。

- [x] **B3. 审计文件系统证据**
  - 统计 `data/snapshots/`、`data/jobs/`、`data/results/`、`data/diagnostics/`、`data/harness-watch/` 的文件数、总大小、时间范围。
  - 抽样检查 job 目录结构（workspace、outputs、self_check.json、review-*.json、last_failure.json）。
  - 验收：生成 `data/aggregates/b3_filesystem_inventory.csv`；列出可用的证据类型。

- [x] **B4. 重建系统架构与运行环境**
  - 从 `data/opencode/config.json` 提取 provider/model/上下文/输出上限/thinking 设置。
  - 从 `valuation/opencode/*.md` 提取四个 Agent 的系统提示词与角色边界。
  - 从 `valuation/opencode/index.js` 提取官方工具名单、权限矩阵、shell 沙箱约束。
  - 从 `start.ps1`、`app.py`、`valuation/config.py` 提取端口、路径、并发、扫描时间等。
  - 验收：`docs/environment.md` 完整、无猜测；每个事实标注来源文件与行号。

- [x] **B5. 重建事件时间线**
  - 以 UTC 为准，按小时统计：会话启动、消息量、工具调用、job 状态变化、results 写入、watchdog 事件、token 消耗。
  - 标注关键事件：首次 job、首次 trial/validate/activate、首次失败、首次 `valution`、首次出现候选行话、Watchdog 首次 `main/human` 判决、最后一个 job。
  - 验收：`data/aggregates/b5_timeline_hourly.csv` + `docs/timeline.md`；时间线与 job 表、session 表可对上。

- [x] **B6. 数据质量审计**
  - 检查重复消息、空消息、编码异常、会话与 job 的映射缺口、token 口径（累计输入 vs 唯一输入）、时区。
  - 明确“10B 调用记录”的准确含义：9,643,030,091 input tokens（约 96.4 亿，口语称 10B），32,736,566 output tokens。
  - 验收：`docs/data_quality.md` 列出已知问题与处理方式；论文中不把累计 token 当作唯一文本量。

---

## 3. 阶段 C：语料抽取与冻结

- [x] **C1. 会话级导出**
  - 字段：session_id、parent_id、agent、title、model、time_created/updated、tokens_*、cost、message_count、tool_call_count、job_id（若能映射）。
  - 输出 `data/derived/sessions.parquet`。
  - 验收：行数 = 2,202；agent 分布与 B1 一致。

- [x] **C2. 消息级导出**
  - 字段：message_id、session_id、agent、type、seq、time_created、finish、error、text、text_len、tool_call_count、tokens_input/output、model。
  - 文本只保留 assistant 的 text parts 与 user/synthetic 的 `text`；工具结果另表。
  - 输出 `data/derived/messages.parquet`。
  - 验收：行数 = 110,413；text 总字符数、空文本率有记录。

- [x] **C3. 工具调用级导出**
  - 字段：message_id、session_id、agent、tool_name、status、input_json、input_len、error_type、error_message、result_excerpt（前 2,000 字符）、duration_ms。
  - 保留官方工具名与变异名；不丢错误调用。
  - 输出 `data/derived/tool_calls.parquet`。
  - 验收：行数 = 116,131；`valution` 2,283 次、`valuation_session_db` 21,486 completed + 3,808 error 等关键计数可复现。

- [x] **C4. 文本话语级导出**
  - 将每条消息的文本切成“话语单元”：assistant text part、user 派工、synthetic 通知、watchdog 最终 JSON。
  - 字段：utterance_id、session_id、agent、role（main/parser/reviewer/watchdog/human/system）、act（dispatch/report/reject/verdict/status/other）、text、time、job_id。
  - 输出 `data/derived/utterances.parquet`。
  - 验收：至少覆盖 11,597 个 assistant text parts + 3,437 个 user 消息 + 874 个 synthetic；人工抽查 20 条分类正确。

- [x] **C5. 派工—回报配对**
  - 从 `subagent` 工具调用、子会话 `parent_id`、job 表的 `child_session/review_session` 重建 main→parser/reviewer 的派工关系。
  - 字段：job_id、round、dispatch_utterance_id、child_session、dispatch_text、report_text、outcome、duration。
  - 输出 `data/derived/dispatches.parquet`。
  - 验收：124 个 parser 会话、111 个 reviewer 会话均有配对或明确缺失原因。

- [x] **C6. 业务结果聚合**
  - 按产品/日/job 聚合：sources、results、bindings、releases、失败数、冲突数、净值覆盖。
  - 输出 `data/aggregates/c6_outcomes.csv`。
  - 验收：43,829 results、720 active bindings、19 releases、154 jobs 可对上。

- [x] **C7. 种子文本与种子词表**
  - 汇总四个系统提示词、工具描述、`contracts.md`、README/AGENTS/方案中的术语，形成 T0（提示词）/T1（项目文档）词表。
  - 输出 `data/aggregates/c7_seed_terms.csv`，字段：term、source、tier、first_seen_in_seed。
  - 验收：至少覆盖 500 个词/短语；人工核对 30 个高频词。

- [x] **C8. 冻结语料与清单**
  - 对源 DB、关键源文件、派生 parquet 计算 SHA256、行数、生成时间。
  - 输出 `data/manifest/manifest.json`。
  - 验收：重跑 C1–C7 得到相同行数与哈希（允许时间戳字段差异，需在文档中说明）。

---

## 4. 阶段 D：测量框架与预实验

- [x] **D1. 分词与规范化**
  - 中文：jieba + 自定义词典（工具名、业务术语、Agent 行话）；英文/代码标识符：正则保留 `valuation_*`、`self_check`、`job_id` 等为一个 token。
  - 处理全角/半角、大小写、路径、哈希、数字掩码；保留 `红位`、`收口` 等行话原形。
  - 验收：对 100 条人工标注文本的分词 F1 ≥ 0.9（或错误率 < 10%）。

- [x] **D2. 词汇多样性指标**
  - 计算每 Agent/每天/每 job 的 token 数、type 数、TTR、MATTR（窗口 500）、hapax 比例、Zipf 斜率。
  - 验收：`data/aggregates/d2_diversity.csv`；抽样复核 3 个时间窗。

- [x] **D3. 角色方言指标**
  - 多项分布的对数几率比（Monroe et al. 2008，informative Dirichlet prior）；输出每 Agent 的 top 50 特征词/短语。
  - 训练 TF-IDF + 逻辑回归分类器，按 session 分组交叉验证，报告 macro-F1、混淆矩阵。
  - 验收：分类器与 top 词表可复现；基线（多数类）对比明确。

- [x] **D4. 收敛/分化指标**
  - 每时间窗（建议 6 小时或 1 天）计算 Agent 两两的 unigram Jensen–Shannon 距离、词汇 Jaccard、风格向量距离（句长、代码混合、标点、模板覆盖率）。
  - 零模型：保持每 Agent 消息量、随机重分配消息；bootstrap 95% CI。
  - 验收：`data/aggregates/d4_divergence.csv`；零模型分布与观测值对比图。

- [x] **D5. 压缩/规约化指标**
  - 派工文本：字符数、token 数、句数、信息槽位（job_id、scope、路径、禁止项、证据）覆盖率、与前序派工的最大 n-gram 覆盖率、最近邻余弦相似度。
  - 回报文本：长度、结构化比例（标题/列表/JSON）、证据路径数、结论词位置。
  - 验收：按 job 序号的时间序列可复现；控制产品/复杂度后的回归结果。

- [x] **D6. 工具语法指标**
  - 官方工具名集合、变异名集合、编辑距离、错误率、首次出现、持续时长、每次出现前后的上下文。
  - 工具调用序列的 bigram/trigram 转移矩阵；每 Agent 的“工具语法”熵。
  - 验收：`data/aggregates/d6_tool_grammar.csv`；`valution` 与 `valuation_session_db` 变异族的完整清单。

- [x] **D7. 协议/图式指标**
  - 从工具输入 JSON 提取 key 集合、key 顺序、嵌套深度；从 Watchdog 输出提取 `decision/summary/evidence` 合规率。
  - 统计状态词（healthy/main/human、passed/failed、approved/rejected）的用法与共现。
  - 验收：`data/aggregates/d7_schema.csv`；至少 3 个图式的标准化曲线。

- [x] **D8. 预实验与阈值冻结**
  - 在 10% 分层样本上跑 D2–D7，检查稀疏性、长尾、Agent 样本量不均衡。
  - 冻结主分析阈值：候选词最小频次、最少 session 数、最少 Agent 数、存活天数。
  - 验收：`docs/methods.md` 写明所有阈值及其敏感性分析计划。

---

## 5. 阶段 E：主实验

- [x] **E1. 语料规模与活动结构（描述性）**
  - 表：按 Agent 的会话/消息/工具调用/token/文本量；按日的活动曲线；会话时长分布；job 生命周期。
  - 图：24 小时活动热图、累计 token 曲线、Agent 会话量对比。
  - 验收：论文第 4 节所有数字可由 `data/aggregates/e1_*.csv` 复现。

- [x] **E2. 涌现词表与扩散（RQ1）**
  - 用 T2 候选（不在 T0/T1）按频次、session 广度、Agent 广度、存活天数筛选；人工复核 top 100。
  - 对每个词计算：首现时间/Agent、采用 Agent 数、采用 session 数、扩散半衰期、存活天数、使用峰值。
  - 图：Top 20 涌现词的首现—扩散热图；3 条典型词的扩散曲线。
  - 验收：`data/aggregates/e2_emergent_terms.csv`；论文报告候选数、通过数、Top 20 表。

- [x] **E3. 角色方言（RQ2）**
  - 对数几率比 top 词表；分类器 macro-F1；混淆矩阵；每条消息的“方言得分”。
  - 图：四象限 dialect map（用多维缩放或 PCA）；top 特征词条形图。
  - 验收：`data/aggregates/e3_dialect_terms.csv`、`e3_classifier.json`；分类器按 session 交叉验证。

- [x] **E4. 收敛与分化（RQ3）**
  - 按 6 小时/天计算两两 JS 距离、Jaccard、风格距离；拟合时间趋势（含 bootstrap CI）。
  - 区分“共享词汇收敛”与“角色语域分化”：前者应下降，后者应保持。
  - 图：4×4 距离热图（早期 vs 晚期）、时间趋势线。
  - 验收：`data/aggregates/e4_divergence.csv`；趋势斜率、CI、p 值。

- [x] **E5. 通信压缩与模板化（RQ4）**
  - 派工文本长度/信息槽位随 job 序号的变化；回报文本长度/结构化比例；模板覆盖率。
  - 回归：log(length) ~ job_order + complexity + agent + day，bootstrap 聚类到 job。
  - 图：派工长度与信息槽位双轴图；模板覆盖率曲线。
  - 验收：`data/aggregates/e5_compression.csv`；至少 3 个控制变量。

- [x] **E6. 工具名变异与选择（RQ5）**
  - 变异族谱：`valuation_session_db` → `valution_session_db` → `valutation_session_db` → ...；编辑距离图。
  - 计算变异率、错误率、复现率、存活时间；比较 `valution` 与随机错拼基线。
  - 事件研究：第一次 `valution` 前后 30 分钟的消息/错误/纠偏。
  - 图：变异网络图；`valution` 每小时频次与错误率。
  - 验收：`data/aggregates/e6_tool_mutations.csv`；论文报告 2,283 次 `valution` 的完整统计。

- [x] **E7. 协议与图式标准化（RQ5/RQ6）**
  - Watchdog JSON 合规率、字段缺失率、evidence 数量分布；工具输入 key 集合的标准化。
  - 图：JSON 合规率时间线；key 共现网络。
  - 验收：`data/aggregates/e7_protocol.csv`；至少 3 个图式的首次出现与稳定时间。

- [x] **E8. 事件对齐：失败、修复与创新爆发（RQ5）**
  - 以 job 失败/trial 失败/validate 失败/watchdog `main` 判决为事件，统计事件前后 1 小时的新词率、行话率、派工压缩率。
  - 负二项回归或泊松回归：新词数 ~ 失败数 + 新 job 数 + 时段固定效应。
  - 图：事件研究系数图；创新爆发时间线。
  - 验收：`data/aggregates/e8_event_study.csv`；报告效应量与 CI，避免把相关当因果。

- [x] **E9. 语言特征与 job 结果（RQ6）**
  - 单元：job（n=154）；结果：activated vs failed/deferred；轮次；watchdog 干预次数。
  - 特征：派工压缩率、行话密度、证据路径数、结构化比例、`valution` 次数、review 轮次。
  - 模型：分层/稳健 logistic 或负二项；控制产品复杂度（文件数、签名数、scope 天数）。
  - 图：特征与结果的相关矩阵；预测边际效应。
  - 验收：`data/aggregates/e9_outcomes.csv`；明确样本量与共线性诊断。

- [x] **E10. 稳健性**
  - 排除 Watchdog（占会话 89%）重跑 E2–E5；按 Agent 等量抽样；改用 1 天/12 小时窗口；改用词形/短语两种单位；排除 synthetic/boilerplate。
  - 用 session 聚类 bootstrap 重估 CI；用置换检验重估方言显著性。
  - 验收：`data/aggregates/e10_robustness.csv`；主结论在至少 80% 规格下保持方向与显著性。

- [x] **E11. 人类输入基线**
  - 证明主会话仅有 1 条人类消息（“现在还有哪些任务没有完成”），其余 user 消息均为 Agent/宿主生成。
  - 对比“种子词”与“涌现词”在人类消息中的出现；量化人类 seeding 的上界。
  - 验收：`data/aggregates/e11_human_input.csv`；论文明确区分“自发”与“提示词脚手架”。

- [x] **E12. 案例研究**
  - 选取 5 条可追溯的“词源链”：
    1. `红位/绿位` 与失败检查的军事化隐喻；
    2. `收口/单发/一刀` 与高风险修复的仪式化指令；
    3. `对账/零位移/盘面` 与三方证据核对；
    4. `valution` 化石词与工具名变异；
    5. Watchdog 的 `healthy/main/human` 判决语域。
  - 每条给出：首现消息 ID/时间/Agent、前 3 条上下文、扩散到哪些 Agent、典型引用、与结果的关系。
  - 验收：`docs/case_studies.md`；每条引用可回到 `data/derived/messages.parquet`。

---

## 6. 阶段 F：图表与论文

- [x] **F1. 图表规范**
  - 统一字体（中文用 Microsoft YaHei/SimHei，英文用 DejaVu Sans）、配色、字号、分辨率；图注中英双语或中文。
  - 所有图从 `data/aggregates/` 生成，不手改数字。
  - 验收：`paper/figures/` 10 幅主图 + 附录图；每幅有生成脚本。

- [x] **F2. 表格规范**
  - 12 张主表：语料规模、Agent 角色、token 分布、涌现词 Top 20、方言特征词、分类器结果、收敛指标、压缩回归、工具变异、协议合规、事件研究、结果关联。
  - 每张表附 CSV 与 Markdown；显著性与 CI 标注。
  - 验收：表格数字与聚合 CSV 一致。

- [x] **F3. 论文提纲与写作**
  - 结构：摘要；1 引言；2 相关工作；3 研究现场与环境；4 数据与测量；5 结果（RQ1–RQ6）；6 案例研究；7 讨论；8 有效性与局限；9 结论；参考文献；附录 A–D。
  - 写作要求：中文学术体；每个定量 claim 有表/图/附录指向；避免“证明意识/理解”等过度主张；区分描述、相关、因果。
  - 验收：`paper/paper.md` 完成，字数 2.0–2.8 万，参考文献 30–50 条。

- [x] **F4. 相关工作与引用核验**
  - 覆盖：emergent communication（Lewis games、TarC、Lazaridou et al.）、LLM multi-agent collaboration、linguistic convergence/communication accommodation、sociolect/argot、tool learning/tool-augmented LLM、LLM agent production studies。
  - 每条引用核对标题/作者/年份/DOI 或 URL；无法核验的不引用。
  - 验收：`paper/refs.bib` 或 `paper/references.md`；正文引用与文献表一一对应。

- [x] **F5. 生成 HTML/PDF**
  - 用 Edge headless 将 `paper/paper.html` 打印为 A4 PDF；检查中文字体、图表、表格、页码、目录。
  - 验收：`paper/paper.pdf` 可打开，页数 ≥ 30，图表不溢出。

- [x] **F6. 内部审稿**
  - 按 checklist 自审：研究问题是否回答、方法是否可复现、数字是否一致、因果是否过度、局限是否充分、伦理是否说明。
  - 至少做一轮“红队”：假设结论相反，找反例；把反例写入局限或稳健性。
  - 验收：`docs/review_checklist.md` 全部打勾；红队记录在 `docs/red_team.md`。

---

## 7. 阶段 G：复现、交付与收尾

- [x] **G1. 一键复现**
  - `python analysis/run_all.py --check`：从只读源库重建聚合、图、表，校验 manifest；不修改源数据。
  - 验收：在干净目录/新进程下跑通；输出哈希与 manifest 一致（允许白名单时间戳差异）。

- [x] **G2. 数字对账**
  - 论文中每个数字与 `data/aggregates/*.csv` 对账；随机抽取 30 个数字人工复核。
  - 验收：`docs/number_audit.md` 记录抽查结果，0 处不一致。

- [x] **G3. 隐私与安全**
  - 检查论文/图表/聚合数据不含 `.env` 密钥、OpenCode password、数据库凭据、个人邮箱、真实产品敏感信息（产品名可保留？按用户要求，使用公开的基金代码/名称可能敏感；默认脱敏为 P001… 或保留代码？需在论文中说明。数据源是内部生产数据，论文中产品名可改为“产品 A/B”或保留代码；为可复核性保留代码，名称脱敏）。
  - 验收：`docs/ethics.md`；grep 检查无密钥模式。

- [ ] **G4. 最终清单**
  - 逐项检查 PLAN.md 全部 `[x]`；`docs/log.md` 完整；git 历史清晰；tag `v1.0-paper`。
  - 验收：`git status` 干净；`git log --oneline` 可读；最终交付说明在 README。

---

## 8. 执行顺序与依赖

```text
A1 → A2 → A3 → A4 → A5
B1 → B2 → B3 → B4 → B5 → B6
C1 → C2 → C3 → C4 → C5 → C6 → C7 → C8
D1 → D2 → D3 → D4 → D5 → D6 → D7 → D8
E1 → E2 → E3 → E4 → E5 → E6 → E7 → E8 → E9 → E10 → E11 → E12
F1 → F2 → F3 → F4 → F5 → F6
G1 → G2 → G3 → G4
```

并行机会：B1/B2/B3 可并行；C1/C2/C3 可并行；E2–E7 在 D 完成后可并行；F1/F2 可在 E 后期开始。任何并行都必须在日志中记录分支/命令，避免数字口径漂移。

## 9. 完成定义（Definition of Done）

- [ ] 论文完整、可读、有摘要/引言/相关工作/环境/数据/方法/结果/案例/讨论/局限/结论/参考文献/附录。
- [ ] 所有实验数据来自 `C:\path\to\valuation`，无合成数据替代；零模型仅用于统计推断并标注。
- [ ] 至少 10 幅图、12 张表，全部可由脚本重建。
- [ ] 至少 3 个可追溯的案例，引用精确到 message_id / 时间戳。
- [ ] 核心结论有置信区间/显著性/稳健性支持；不把相关写成因果。
- [ ] 数据/隐私/伦理声明完整；不泄露密钥与敏感凭据。
- [ ] `python analysis/run_all.py --check` 通过；manifest 可校验。
- [ ] PLAN.md 全部勾选；git 历史完整；最终 tag 存在。
