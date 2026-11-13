from pathlib import Path

p = Path('paper/paper.md')
s = p.read_text(encoding='utf-8')
repls = [
    (
        '第三类是**评测与失败分析**：Cemri 等（2025）系统分析了多 Agent LLM 系统为何失败，指出规范冲突、验证缺失、协调断裂等模式。',
        '第三类是**评测与失败分析**：Cemri 等（2025）系统分析了多 Agent LLM 系统为何失败，指出规范冲突、验证缺失、协调断裂等模式；Wang 等（2024）的综述覆盖了更多系统。'
    ),
    (
        '社会方言（sociolect）和行话（argot）研究则关注群体内部的词汇如何标记身份、边界和共同实践（Labov, 1972；Eckert, 2000；Halliday, 1978；Wenger, 1998）。',
        '社会方言（sociolect）和行话（argot）研究则关注群体内部的词汇如何标记身份、边界和共同实践（Labov, 1972；Eckert, 2000；Halliday, 1978；Wenger, 1998）；言语行为理论（Austin, 1962；Searle, 1969）和异质语言（Bakhtin, 1981）则为“说话即行动”“同一语言内部的多声部”提供了概念工具。'
    ),
    (
        '用对数几率比（log-odds ratio with informative Dirichlet prior）计算每个 Agent 相对于其他 Agent 的特征词；',
        '用对数几率比（log-odds ratio with informative Dirichlet prior；Monroe et al., 2008）计算每个 Agent 相对于其他 Agent 的特征词；'
    ),
    (
        '计算两两 Jensen–Shannon 散度。',
        '计算两两 Jensen–Shannon 散度（Lin, 1991）。'
    ),
    (
        '多重比较用 Benjamini–Hochberg FDR；',
        '多重比较用 Benjamini–Hochberg FDR（Benjamini & Hochberg, 1995）；'
    ),
]
for a, b in repls:
    if a not in s:
        print('NOT FOUND:', a[:40])
    s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print('done')
