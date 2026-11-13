# 复现说明

## 1. 环境

- Windows（win32），PowerShell 7。
- Python 3.14（`C:\path\to\AppData\Local\Python\pythoncore-3.14-64\python.exe`）。
- 依赖：pandas、numpy、matplotlib、scipy、scikit-learn、networkx、statsmodels、jieba、pyarrow、markdown-it-py、pypdf、pymupdf。
- 源数据：`C:\path\to\valuation`（只读）。
- 本仓库：`C:\path\to\agent-language`。

## 2. 一键流程

```powershell
python -m analysis.extract
python -m analysis.audit
python -m analysis.lexicon_stats
python -m analysis.diffusion
python -m analysis.dialects
python -m analysis.convergence
$env:AGENT_LANG_WINDOW='24h'; python -m analysis.convergence; Remove-Item Env:AGENT_LANG_WINDOW
python -m analysis.compression
python -m analysis.tool_evolution
python -m analysis.protocol
python -m analysis.events
python -m analysis.outcomes
python -m analysis.human_input
python -m analysis.robustness
python -m analysis.tables
python -m analysis.figures
python -m analysis.build_paper
```

## 3. 校验

```powershell
python -m analysis.run_all --check
python -m analysis.privacy_check --all
```

`--check` 会核对：

- 源库行数：2,202 sessions、110,413 messages、116,131 tool calls、154 jobs、43,829 results；
- 关键聚合：69 个词项、1,119 次判决、2,283 次 `valution`、249,092,664 token；
- `data/manifest/manifest.json` 中的 SHA256（允许白名单时间戳差异）。

## 4. 预期产物

| 路径 | 内容 |
| --- | --- |
| `data/derived/*.parquet` | 本地派生语料（不提交） |
| `data/aggregates/b1_*` | 会话/消息/工具审计 |
| `data/aggregates/b2_*` | 业务规模/绑定 |
| `data/aggregates/e2_*` | 词表/扩散 |
| `data/aggregates/e3_*` | 角色方言/分类器 |
| `data/aggregates/e4_*` | 收敛 |
| `data/aggregates/e5_*` | 压缩/语域强化 |
| `data/aggregates/e6_*` | 工具变异/valution |
| `data/aggregates/e7_*` | 协议 |
| `data/aggregates/e8_*` | 事件对齐 |
| `data/aggregates/e9_*` | 结果关联 |
| `data/aggregates/e10_*` | 稳健性 |
| `data/aggregates/e11_*` | 人类输入 |
| `paper/figures/*.png` | 12 幅主图 |
| `paper/tables/*.md` | 14 张表 |
| `paper/paper.md` | 论文源文件 |
| `paper/paper.html` | 排版 HTML |
| `paper/paper.pdf` | 46 页 PDF |

## 5. 常见问题

- **中文乱码**：PowerShell 控制台默认 GBK；所有输出写入 UTF-8 文件，用 `read` 工具查看。源库文本是 UTF-8。
- **pandas 时间解析**：对 `2026-11-04T14:25:48.799000+00:00` 这类字符串，pandas 3 的 `to_datetime(..., utc=True)` 在部分 Series 上会返回 NaT；使用 `format='ISO8601'`。
- **分类器警告**：sklearn 1.9 的 `n_jobs` 警告不影响结果。
- **PDF**：Edge headless 打印；如果 Edge 路径不同，改 `analysis/build_paper.py` 的 `EDGE`。
- **源库只读**：所有连接使用 `mode=ro`；不要 `ATTACH` 可写库、不要 `VACUUM`/`UPDATE`。

## 6. 目录与提交

- `data/private/`、`data/derived/`、`tools/*.txt`、`.venv/` 不提交。
- `data/aggregates/`、`data/manifest/`、`paper/`、`docs/`、`analysis/` 提交。
- 提交前必须通过 `python -m analysis.privacy_check --all`。
