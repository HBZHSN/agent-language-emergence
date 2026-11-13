# 工具约束下的多智能体语言涌现

本仓库是一项实证研究与论文写作工程。研究对象是 `C:\path\to\valuation` 中一套真实生产级多智能体估值表解析系统在 2026-11-04 至 2026-11-11 期间形成的运行记录。

## 研究问题

1. 四个 Agent（主 Agent、解析 Agent、核验 Agent、Watchdog）是否在提示词之外自发形成共享词汇与工作语言？
2. 这套语言如何按角色分化，又如何随时间收敛？
3. 派工/回报是否变得更短、更模板化，同时保留关键信息？
4. 工具名变异（如 `valution`）为什么在负反馈下仍能存活？
5. 语言特征与 job 结果之间有什么关系？

## 数据规模

- 9,643,030,091 累计输入 token（约 96.4 亿，口语称 10B）；32,736,566 输出 token。
- 2,202 个会话：main 1、parser 124、reviewer 111、watchdog 1,966。
- 110,413 条消息：assistant 102,270、user 3,437、synthetic 874、idle 3,436、compaction 244、system 103。
- 116,131 次工具调用；11,597 个 assistant 文本片段。
- 业务侧：123 个产品、43,870 份源文件、43,829 条结果、720 条 active binding、19 个 release、154 个 job。
- 主会话中只有 1 条人类消息（“现在还有哪些任务没有完成”）；其余 user 消息均为 Agent/宿主生成。

## 目录

```text
AGENTS.md             面向后续 Agent 的工作协议
PLAN.md               唯一执行清单（逐项勾选）
analysis/             抽取、指标、实验、绘图、论文构建
data/derived/         源库导出的 parquet（大文件，不提交）
data/aggregates/      论文用聚合 CSV/JSON（提交）
data/manifest/        SHA256、行数、生成时间
paper/                paper.md / paper.html / paper.pdf / figures / tables
docs/                 环境、数据字典、方法、时间线、案例、日志、伦理
```

## 复现

```powershell
# 1. 只读抽取（首次运行会生成 data/derived/）
python analysis\extract.py

# 2. 全量指标、实验、图表
python analysis\run_all.py

# 3. 校验 manifest 与关键数字
python analysis\run_all.py --check

# 4. 构建论文 HTML/PDF
python analysis\build_paper.py
```

> 源数据只读；不要修改 `C:\path\to\valuation`。详见 `AGENTS.md`。

## 状态

进度以 `PLAN.md` 的勾选为准，过程记录见 `docs/log.md`。
