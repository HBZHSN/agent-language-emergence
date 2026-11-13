"""Generate the paper figures from sanitized aggregates."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analysis import config, lexicon

plt.rcParams.update(
    {
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
    }
)

COLORS = {
    "main": "#1f77b4",
    "parser": "#2ca02c",
    "reviewer": "#d62728",
    "watchdog": "#9467bd",
}
CAT_COLORS = {
    "closure": "#4c72b0",
    "ruling": "#dd8452",
    "evidence": "#55a868",
    "status": "#c44e52",
    "repair": "#8172b3",
    "ritual": "#937860",
}


def save(fig, name: str):
    path = config.FIGURES / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", path)


def fig_architecture():
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def box(x, y, w, h, text, color, fs=9):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.12", linewidth=1.2, edgecolor=color, facecolor=color + "22")
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color="#222222", wrap=True)

    box(3.7, 4.5, 2.6, 1.0, "主 Agent\n调度 / 裁决 / 启用", COLORS["main"], 10)
    box(0.7, 2.5, 2.4, 0.95, "解析 Agent\n实现 / trial", COLORS["parser"], 10)
    box(6.9, 2.5, 2.4, 0.95, "核验 Agent\n独立 validate", COLORS["reviewer"], 10)
    box(3.7, 0.6, 2.6, 0.95, "Watchdog\n只读判决", COLORS["watchdog"], 10)
    box(0.5, 4.5, 2.4, 0.8, "人类\n仅 1 条状态查询", "#7f7f7f", 9)
    box(3.7, 2.5, 2.6, 1.35, "共享工件\nparsers/ · verification/\ndata/jobs/ · JSON/文件", "#8c8c8c", 8.5)

    arrow = dict(arrowstyle="->", linewidth=1.4, color="#555555")
    ax.annotate("", xy=(3.6, 3.15), xytext=(3.0, 4.4), arrowprops=arrow)
    ax.annotate("", xy=(2.0, 3.55), xytext=(3.9, 4.4), arrowprops=arrow)
    ax.annotate("", xy=(7.9, 3.55), xytext=(6.1, 4.4), arrowprops=arrow)
    ax.annotate("", xy=(6.2, 4.4), xytext=(7.9, 3.55), arrowprops=arrow)
    ax.annotate("", xy=(5.0, 1.65), xytext=(5.0, 2.4), arrowprops=dict(arrowstyle="->", linewidth=1.2, color="#999999", linestyle="--"))
    ax.annotate("", xy=(2.6, 4.9), xytext=(4.7, 4.9), arrowprops=dict(arrowstyle="->", linewidth=1.1, color="#999999", linestyle="--"))

    ax.text(2.3, 4.05, "派工 / 纠偏", fontsize=8, color="#444444")
    ax.text(2.9, 3.75, "回报", fontsize=8, color="#444444")
    ax.text(8.15, 4.2, "派工", fontsize=8, color="#444444")
    ax.text(8.15, 3.65, "报告", fontsize=8, color="#444444")
    ax.text(5.2, 2.05, "读写证据", fontsize=8, color="#666666")
    ax.text(5.0, 5.62, "状态查询", fontsize=8, color="#666666")
    ax.set_title("图 1  四 Agent 的通信拓扑：星形派工 + 共享工件", fontsize=12)
    save(fig, "fig01_architecture.png")


def fig_daily():
    d = pd.read_csv(config.AGGREGATES / "b1_daily.csv")
    b = pd.read_csv(config.AGGREGATES / "b2_daily.csv")
    d = d.merge(b, on="date", how="left").fillna(0)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(d))
    ax.bar(x, d["messages"], color="#4c72b0", alpha=0.75, label="消息数")
    ax.set_ylabel("消息数")
    ax.set_xticks(x)
    ax.set_xticklabels([s[5:] for s in d["date"]], rotation=0)
    ax2 = ax.twinx()
    ax2.plot(x, d["tool_errors"], color="#c44e52", marker="o", label="工具错误")
    ax2.plot(x, d["n_results"], color="#55a868", marker="s", label="结果写入")
    ax2.set_ylabel("错误数 / 结果数")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right")
    ax.set_title("图 2  逐日消息量、工具错误与结果写入（UTC）")
    ax.grid(axis="y", alpha=0.25)
    save(fig, "fig02_daily.png")


def fig_tokens():
    a = pd.read_csv(config.AGGREGATES / "b1_agent_summary.csv")
    order = ["main", "parser", "reviewer", "watchdog"]
    a = a.set_index("agent").loc[order].reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    axes[0].barh(a["agent"], a["session_tokens_input"] / 1e9, color=[COLORS[x] for x in a["agent"]])
    axes[0].set_xlabel("累计输入 token（十亿）")
    axes[0].set_title("输入 token（上下文重复计费）")
    for i, v in enumerate(a["session_tokens_input"] / 1e9):
        axes[0].text(v + 0.03, i, f"{v:.2f}B", va="center", fontsize=9)
    axes[1].barh(a["agent"], a["session_tokens_output"] / 1e6, color=[COLORS[x] for x in a["agent"]])
    axes[1].set_xlabel("输出 token（百万）")
    axes[1].set_title("输出 token")
    for i, v in enumerate(a["session_tokens_output"] / 1e6):
        axes[1].text(v + 0.1, i, f"{v:.1f}M", va="center", fontsize=9)
    for ax in axes:
        ax.grid(axis="x", alpha=0.25)
    fig.suptitle("图 3  Agent 级 token 分布", fontsize=12)
    fig.tight_layout()
    save(fig, "fig03_tokens.png")


def fig_lexicon():
    d = pd.read_csv(config.AGGREGATES / "e2_term_stats.csv").sort_values("count", ascending=True).tail(22)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.barh(d["term"], d["count"], color=[CAT_COLORS.get(c, "#888888") for c in d["category"]])
    ax.set_xlabel("出现次数（清洗后语料，子串计数）")
    ax.set_title("图 4  高频操作性词汇（按类别着色）")
    ax.grid(axis="x", alpha=0.25)
    handles = [mpatches.Patch(color=v, label=k) for k, v in CAT_COLORS.items()]
    ax.legend(handles=handles, loc="lower right", title="类别", fontsize=8)
    save(fig, "fig04_lexicon.png")


def fig_adoption(terms=("逐字", "收口", "单发", "对账", "红位", "终壳")):
    u = pd.read_parquet(config.DERIVED / "utterances.parquet")
    u = u[u.agent.isin(["main", "parser", "reviewer", "watchdog"])].copy()
    u["time_utc"] = pd.to_datetime(u["time_utc"], utc=True)
    u["date"] = u["time_utc"].dt.floor("D")
    u["clean"] = u["text"].map(lambda s: s if isinstance(s, str) else "")
    dates = pd.date_range(u["date"].min(), u["date"].max(), freq="D", tz="UTC")
    fig, ax = plt.subplots(figsize=(9, 4.3))
    for term in terms:
        sub = u[u["clean"].str.contains(term, regex=False)]
        first = sub.groupby("agent")["date"].min()
        cum = []
        for day in dates:
            cum.append(int((first <= day).sum()))
        ax.step(dates, cum, where="post", marker="o", label=term, linewidth=1.8)
    ax.set_ylim(0.5, 4.5)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_ylabel("已采用该词的 Agent 数")
    ax.set_title("图 5  代表性词汇的跨 Agent 采用曲线")
    ax.legend(ncol=3, fontsize=8)
    ax.grid(alpha=0.25)
    save(fig, "fig05_adoption.png")


def fig_dialect():
    d = pd.read_csv(config.AGGREGATES / "e3_dialect_terms.csv")
    agents = ["main", "parser", "reviewer", "watchdog"]
    top = []
    for a in agents:
        sub = d[(d.agent == a) & (d.z > 0)].nlargest(6, "z")
        top.extend(sub["term"].tolist())
    top = list(dict.fromkeys(top))
    mat = np.zeros((len(top), len(agents)))
    for i, t in enumerate(top):
        for j, a in enumerate(agents):
            row = d[(d.agent == a) & (d.term == t)]
            mat[i, j] = float(row["z"].iloc[0]) if len(row) else 0.0
    fig, ax = plt.subplots(figsize=(7.5, 8))
    im = ax.imshow(mat, cmap="RdBu_r", vmin=-60, vmax=60, aspect="auto")
    ax.set_xticks(range(len(agents)))
    ax.set_xticklabels(agents)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top, fontsize=8)
    ax.set_title("图 6  角色方言的关键词（对数几率 z）")
    for i in range(len(top)):
        for j in range(len(agents)):
            if abs(mat[i, j]) >= 10:
                ax.text(j, i, f"{mat[i,j]:.0f}", ha="center", va="center", fontsize=7, color="white" if abs(mat[i, j]) > 35 else "#222222")
    fig.colorbar(im, ax=ax, shrink=0.6, label="z")
    save(fig, "fig06_dialect.png")


def fig_convergence():
    d = pd.read_csv(config.AGGREGATES / "e4_divergence.csv")
    d["window"] = pd.to_datetime(d["window"], utc=True)
    pairs = sorted(d["pair"].unique())
    fig, ax = plt.subplots(figsize=(9, 4.3))
    for p in pairs:
        sub = d[d.pair == p].sort_values("window")
        ax.plot(sub["window"], sub["excess_js"], marker="o", linewidth=1.5, label=p)
    ax.axhline(0, color="#999999", linewidth=0.8, linestyle="--")
    ax.set_ylabel("超额 JS 散度（观测 − 零模型）")
    ax.set_title("图 7  角色语域的超额散度随时间（12 小时窗）")
    ax.legend(ncol=2, fontsize=8)
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    save(fig, "fig07_convergence.png")


def fig_compression():
    d = pd.read_csv(config.AGGREGATES / "e5_dispatch_features.csv")
    d = d.drop_duplicates(["job_id", "role"]).sort_values("job_order")
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.9))
    for ax, col, label in [
        (axes[0], "jargon_per_1k", "行话密度（每千 token）"),
        (axes[1], "text_len", "派工文本长度（字符）"),
    ]:
        for role, color in (("parser", COLORS["parser"]), ("reviewer", COLORS["reviewer"])):
            sub = d[d.role == role]
            ax.scatter(sub["job_order"], sub[col], s=14, alpha=0.35, color=color, label=role)
            roll = sub.sort_values("job_order")[col].rolling(12, min_periods=3).mean()
            ax.plot(sub.sort_values("job_order")["job_order"], roll, color=color, linewidth=2.2)
        ax.set_xlabel("Job 顺序")
        ax.set_ylabel(label)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    axes[0].set_title("(a) 行话密度随 job 顺序上升")
    axes[1].set_title("(b) 派工长度未显著压缩")
    fig.suptitle("图 8  通信的“语域强化”而非简单压缩", fontsize=12)
    fig.tight_layout()
    save(fig, "fig08_compression.png")


def fig_valution():
    h = pd.read_csv(config.AGGREGATES / "e6_tool_hourly.csv")
    v = h[h.tool == "valution"].copy()
    v["hour"] = pd.to_datetime(v["hour"], utc=True)
    tok = pd.read_csv(config.AGGREGATES / "e6_valution_hourly_tokens.csv")
    tok["hour"] = pd.to_datetime(tok["hour"], utc=True)
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    ax.bar(v["hour"], v["calls"], width=0.035, color="#c44e52", alpha=0.8, label="valution 调用")
    ax.set_ylabel("每小时调用次数")
    ax2 = ax.twinx()
    ax2.plot(tok["hour"], tok["tokens_input"].cumsum() / 1e6, color="#4c72b0", marker="o", label="累计输入 token")
    ax2.set_ylabel("累计输入 token（百万）")
    ax.set_title("图 9  `valution` 化石词：9 小时、2,283 次、2.49 亿输入 token")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    ax.grid(axis="y", alpha=0.25)
    fig.autofmt_xdate()
    save(fig, "fig09_valution.png")


def fig_outcomes():
    d = pd.read_csv(config.AGGREGATES / "e9_job_features.csv")
    d = d[d.dispatch_jargon_per_1k > 0].copy()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#c44e52" if x else "#4c72b0" for x in d["failed"]]
    ax.scatter(d["dispatch_jargon_per_1k"], d["rounds"] + 1, c=colors, s=28, alpha=0.75)
    ax.set_yscale("log")
    ax.set_xlabel("首次派工的行话密度（每千 token）")
    ax.set_ylabel("job 轮次 + 1（对数）")
    rho, p = spearmanr(d["dispatch_jargon_per_1k"], d["rounds"])
    ax.set_title(f"图 10  行话密度与 job 轮次（Spearman ρ={rho:.2f}, p={p:.1e}）")
    ax.grid(alpha=0.25)
    save(fig, "fig10_outcomes.png")


def fig_protocol():
    v = pd.read_csv(config.AGGREGATES / "e7_verdicts.csv")
    v["date"] = pd.to_datetime(v["date"], utc=True)
    daily = v.groupby("date").agg(attempts=("valid", "size"), valid=("valid", "mean")).reset_index()
    s = pd.read_csv(config.AGGREGATES / "e7_schema.csv").head(10)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
    axes[0].plot(daily["date"], daily["valid"] * 100, marker="o", color=COLORS["watchdog"])
    axes[0].set_ylim(0, 105)
    axes[0].set_ylabel("严格 JSON 合规率（%）")
    axes[0].set_title("(a) Watchdog 判决格式")
    axes[0].grid(alpha=0.25)
    fig.autofmt_xdate()
    axes[1].barh(s["tool"][::-1], s["exact_match"][::-1] * 100, color="#55a868")
    axes[1].set_xlim(0, 105)
    axes[1].set_xlabel("规范 key 集合完全匹配率（%）")
    axes[1].set_title("(b) 工具输入图式")
    axes[1].grid(axis="x", alpha=0.25)
    fig.suptitle("图 11  协议与图式的标准化", fontsize=12)
    fig.tight_layout()
    save(fig, "fig11_protocol.png")


def fig_events():
    d = pd.read_csv(config.AGGREGATES / "e8_bins.csv")
    d["bin"] = pd.to_datetime(d["bin"], utc=True)
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    ax.bar(d["bin"], d["new_terms"], width=0.2, color="#4c72b0", alpha=0.8, label="新词首现数")
    ax.set_ylabel("新词首现数 / 6h")
    ax2 = ax.twinx()
    ax2.plot(d["bin"], d["watchdog_main"], color="#c44e52", marker="o", label="Watchdog main 判决")
    ax2.plot(d["bin"], d["trial_errors"] / 10, color="#55a868", marker="s", label="trial 错误/10")
    ax2.set_ylabel("判决数 / 错误数")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
    ax.set_title("图 12  新词首现、Watchdog 升级与 trial 失败的时间对齐")
    ax.grid(axis="y", alpha=0.25)
    fig.autofmt_xdate()
    save(fig, "fig12_events.png")


def main():
    fig_architecture()
    fig_daily()
    fig_tokens()
    fig_lexicon()
    fig_adoption()
    fig_dialect()
    fig_convergence()
    fig_compression()
    fig_valution()
    fig_outcomes()
    fig_protocol()
    fig_events()


if __name__ == "__main__":
    main()
