# AGENTS.md

本文件面向在本仓库中继续工作的编码 Agent。**先读 `PLAN.md`，再读本文件。**

## 1. 项目是什么

本项目不是软件产品，而是一项**实证研究 + 论文写作**工程：

- 研究对象：`C:\path\to\valuation` 中一套真实生产级多智能体系统在 2026-11-04 至 2026-11-11 期间形成的运行记录。
- 研究问题：四个 Agent（主 Agent、解析 Agent、核验 Agent、Watchdog）如何在工具约束下自发形成一套共享工作语言（操作性混合语 / 角色社会方言），以及这套语言如何扩散、收敛、分化、病化并对结果产生影响。
- 交付物：一篇完整中文论文（Markdown + HTML + PDF）、可重跑的分析流水线、图表、数据字典、复现说明、完整 git 历史。

**数据源只读。** 不要修改、移动、删除、重命名 `C:\path\to\valuation` 中的任何文件。该目录可能有用户未提交的修改，一律视为用户工作，不碰。

## 2. 当前进度与续跑协议

1. 打开 `PLAN.md`，从上到下找第一个未勾选的 `- [ ]`。
2. 只做这一项（或这一项明确允许的并行子项）；开始前在 `docs/log.md` 追加 `START` 记录。
3. 完成后：
   - 把 `PLAN.md` 中对应项改为 `- [x]`；
   - 在 `docs/log.md` 追加 `DONE` 记录（时间、命令、关键数字、产物路径）；
   - `git add` 相关文件并 commit，message 用 `plan: <编号> <简述>`；
   - 如果任务产出论文数字，把数字写入 `data/aggregates/` 的 CSV，不要只写在正文里。
4. 如果任务被阻塞：不要勾选；在 `docs/log.md` 写 `BLOCKED` + 原因 + 需要用户决定的问题；保持工作区可复现。
5. 不要跳项。后续任务依赖前面的产物；跳项会导致口径漂移。

当前阶段以 `PLAN.md` 为准。不要凭记忆假设进度。

## 3. 环境与命令

- 操作系统：Windows（win32），PowerShell 7。
- Python：`C:\path\to\AppData\Local\Python\pythoncore-3.14-64\python.exe`（3.14）。
- 已安装：pandas、numpy、matplotlib、scipy、scikit-learn、networkx、statsmodels、jieba、pyarrow、python-docx。
- 本仓库根目录：`C:\path\to\agent-language`。
- 源数据：
  - `C:\path\to\valuation\data\opencode\state\opencode\opencode.db`（会话/消息/工具调用，约 722 MB）
  - `C:\path\to\valuation\data\valuation.db`（业务库，约 5.5 GB，含 1,586 万条科目明细）
  - `C:\path\to\valuation\data\snapshots\`（原始估值表快照，约 8.9 万个文件）
  - `C:\path\to\valuation\data\jobs\`、`results\`、`diagnostics\`、`harness-watch\`
- 常用命令：

```powershell
# 只读探查（示例）
python analysis\extract.py --check

# 全量重建聚合、图、表（计划中的 G1）
python analysis\run_all.py

# 只校验 manifest 与关键数字
python analysis\run_all.py --check

# 生成论文 HTML/PDF（计划中的 F5）
python analysis\build_paper.py
```

> 具体脚本名以实际实现为准；实现后同步更新本节。

### 3.1 编码注意事项

- 所有文本文件用 **UTF-8** 读写。
- PowerShell 控制台默认代码页可能把中文显示成乱码（`��`），**不要**据此判断数据损坏。把输出写入 UTF-8 文件，再用 `read` 工具查看。
- SQLite 文本本身是 UTF-8；`sqlite3` 命令行在 Windows 下可能显示乱码，优先用 Python。
- 论文中的中文标点用全角；代码标识符用英文。

### 3.2 SQLite 只读

```python
import sqlite3
con = sqlite3.connect('file:C:/path/to/valuation/data/valuation.db?mode=ro', uri=True)
```

- 永远加 `mode=ro`；不要 `ATTACH` 可写库；不要 `VACUUM`、`UPDATE`、`DELETE`、`DROP`。
- 不要查询 `credential`、`account`、`control_account`、`kv` 等敏感表；`session_db` 只允许 `SELECT/WITH`。
- 大表（`account_lines`、`holdings`）只做聚合查询，不要 `SELECT *` 拉进内存。

## 4. 研究口径（重要）

### 4.1 “10B 调用记录”的准确含义

源库统计为：

- `session_v2.tokens_input` 合计 **9,643,030,091**（约 96.4 亿，口语称 10B）。
- `tokens_output` 合计 **32,736,566**。
- `session_message` 共 **110,413** 条；其中 assistant **102,270**、user **3,437**、synthetic **874**、idle **3,436**、compaction **244**、system **103**。
- 工具调用 **116,131** 次；assistant 文本片段 **11,597** 个。
- 会话 **2,202** 个：main 1、parser 124、reviewer 111、watchdog 1,966。

论文中第一次出现时必须写清楚“累计输入 token（上下文重复计费）”，不要把 9.64B 说成“9.64B 条独立消息”或“唯一文本 token”。

### 4.2 “语言”的操作化定义

不要把 Agent 的输出泛称为“自然语言”。论文采用五层操作化：

1. **词汇层**：词、短语、缩写、工具名形式。
2. **形态层**：截断、拼合、错拼、下划线/大小写、中文夹英文。
3. **句法层**：模板句、JSON 图式、工具调用序列、状态词语法。
4. **语用层**：派工、回报、拒绝、升级、缓办、裁决等言语行为。
5. **社区层**：首现、扩散、采用、收敛、分化、存活、淘汰。

“涌现”必须满足可核查标准（见 PLAN D8/E2）：不在种子提示词/项目文档中、重复出现、跨 session、跨 Agent（或跨角色）、有协调功能、存活 ≥ 2 天或 ≥ 3 个 job。达不到就降级为“候选/一次性变异”，不要硬说成语言。

### 4.3 证据标准

- 每个数字必须能指向 `data/aggregates/*.csv` 或 `data/manifest/manifest.json`。
- 每个案例引用必须给出 `message_id`、`session_id`、UTC 时间、Agent、原文片段。
- 区分：
  - **描述**（我们观察到什么）；
  - **相关**（两个变量同向/反向，附 CI 与 p 值）；
  - **因果**（只有在有事件顺序、控制变量、稳健性时才谨慎表述）。
- 不要用“证明”“必然”“导致”描述观察性结果；用“与……一致”“预测”“伴随”。
- 报告样本量、缺失值、排除标准；不要只报显著结果。

### 4.4 统计与可复现

- 所有随机过程固定 seed；bootstrap 至少 1,000 次（主结果 5,000 次）。
- 分类器按 **session** 分组交叉验证，不能按消息随机切分（会泄漏）。
- 时间序列/面板回归要控制日固定效应或时段固定效应；CI 聚类到 job/session。
- 多重比较使用 Benjamini–Hochberg FDR；论文中报告校正后的 q 值或明确说明。
- 零模型/置换检验只用于推断，不作为“实验数据”。

## 5. 论文写作规范

- 语言：中文；术语首次出现给英文原文（如“操作性混合语（operational pidgin）”）。
- 结构：摘要；1 引言；2 相关工作；3 研究现场与环境；4 数据与测量；5 结果；6 案例研究；7 讨论；8 有效性与局限；9 结论；参考文献；附录 A–D。
- 每节开头先回答“这一节要回答哪个 RQ”，不要让读者猜。
- 图表：图注在图下方，表注在表上方；每张图表在正文中至少被引用一次；数字与 CSV 一致。
- 参考文献：只引用能核验的文献；正文引用与文献表一一对应；优先 DOI/官方 URL。
- 不泄露：`.env`、`MODEL_API_KEY`、OpenCode password、数据库凭据、个人邮箱。产品名称在论文中脱敏为“产品 A/B…”或保留基金代码但去掉全称；原始快照路径不写进论文正文。

## 6. 目录约定

```text
AGENTS.md             本文件
PLAN.md               唯一执行清单（勾选）
README.md             项目说明
analysis/             抽取、指标、实验、绘图、构建脚本
data/derived/         从源库导出的 parquet（大文件，默认 gitignore）
data/aggregates/      论文用聚合 CSV/JSON（提交）
data/manifest/        SHA256、行数、生成时间（提交）
paper/                paper.md / paper.html / paper.pdf / figures / tables
docs/                 environment / data_dictionary / methods / timeline / case_studies / log / ethics
tools/                一次性探针（可清理，不进入论文证据链）
```

- `data/derived/` 的大文件不提交；提交 `data/aggregates/` 与 `data/manifest/`，保证别人不用 5.5GB 源库也能核对论文数字。
- 不要提交 `.venv/`、`__pycache__/`、临时日志、原始 Excel 快照。
- 论文 PDF 与图提交；HTML 若过大可只提交模板与生成脚本。

## 7. 安全与边界

- 不执行任何会修改 `C:\path\to\valuation` 的命令。
- 不把源数据上传到外部服务；本项目的网络请求只用于查文献（若需要）。
- 不运行 `start.ps1`、不重启源项目的 OpenCode/Flask、不碰 Docker 容器。
- 不读取或输出 `.env`；如误看到密钥，不要写入任何文件或回复。
- 不删除 `data/aggregates/` 中的历史结果；新结果用新文件名或版本号，保留可追溯性。

## 8. 完成前自检

- [ ] `PLAN.md` 中所有项已勾选，或明确标注 `BLOCKED` 并有用户决定。
- [ ] `python analysis/run_all.py --check` 通过。
- [ ] 论文中的 30 个随机数字与 CSV 对账一致。
- [ ] `git status` 干净；`git log --oneline` 可读；tag `v1.0-paper` 存在。
- [ ] 没有密钥、密码、个人邮箱、原始快照路径泄露。
- [ ] 论文明确写出：数据来自单一系统、单一模型、8 天观察窗口；不能外推到所有多智能体系统。
