"""Curated operational lexicon.

Terms were selected from the data-driven candidate list (word unigrams and
character n-grams) and manually checked for a coordination function.  The
selection rule is documented in docs/methods.md; this file is the frozen list
used by the paper.
"""

CURATED = [
    # closure / finalization
    ("收口", "closure", "把任务、证据链或修复收束到可提交状态"),
    ("终壳", "closure", "最终送审的核验/解析壳"),
    ("终局", "closure", "不可再改的最终裁定"),
    ("终序列", "closure", "收尾阶段的固定动作序列"),
    ("停手", "closure", "接到裁定后停止一切修改"),
    ("回执", "closure", "执行完毕后的简短确认"),
    ("交单", "closure", "把候选/报告交给下一角色"),
    ("呈报", "closure", "向上级角色提交结论"),
    # ruling / adjudication
    ("直裁", "ruling", "主 Agent 直接裁定，不再走子会话往返"),
    ("裁决", "ruling", "对争议证据作出终局判断"),
    ("裁定", "ruling", "对范围、口径或动作的正式决定"),
    ("先例", "ruling", "此前 job 形成的可复用裁定"),
    ("纪律", "ruling", "对 Agent 行为边界的约束"),
    ("治理", "ruling", "对流程/权限/证据链的制度性维护"),
    # evidence / reconciliation
    ("对账", "evidence", "把面板、原表、候选三方逐项核对"),
    ("逐字", "evidence", "逐字符引用原文，不做转述"),
    ("逐格", "evidence", "逐单元格核对"),
    ("逐份", "evidence", "逐份样例核对"),
    ("逐字符", "evidence", "逐字符比对代码/文本"),
    ("逐字节", "evidence", "逐字节比对文件"),
    ("在卷", "evidence", "证据已经进入任务卷宗"),
    ("留证", "evidence", "把证据留在可复核的位置"),
    ("判据面", "evidence", "检查判据所覆盖的证据面"),
    ("注册面", "evidence", "注册/登记信息的可见面"),
    ("盘面", "evidence", "磁盘上的实际状态"),
    ("现势", "evidence", "当前最新状态，而非历史快照"),
    ("代际", "evidence", "不同 release/壳版本的代际关系"),
    ("实值", "evidence", "实际测量得到的值"),
    ("零位移", "evidence", "同一失败在多次重跑中位置/文案不变"),
    ("零改", "evidence", "零代码改动"),
    ("零动", "evidence", "数值/判据零改动"),
    ("全等", "evidence", "逐字段完全相等"),
    ("闭合", "evidence", "守恒式/证据链闭合"),
    ("守恒", "evidence", "金额或净值恒等式成立"),
    ("复算", "evidence", "独立重算而非复用解析结果"),
    ("直读", "evidence", "直接从原表读取，不经过解析函数"),
    ("直证", "evidence", "直接证据，不靠推断"),
    ("普查", "evidence", "对全量样本做覆盖性检查"),
    # color / status
    ("红位", "status", "检查中的失败位/红项"),
    ("红面", "status", "失败证据所在的检查面"),
    ("绿面", "status", "通过证据所在的检查面"),
    ("全绿", "status", "全部检查通过"),
    ("零触", "status", "零触碰/零改动"),
    # repair / risk
    ("单发", "repair", "只发一次 trial/validate，不反复试探"),
    ("一刀", "repair", "一次最小编辑"),
    ("单刀", "repair", "只做一处最小改动"),
    ("盲发", "repair", "未对账就提交，含贬义"),
    ("落盘", "repair", "把结果写入磁盘/证据目录"),
    ("落位", "repair", "把改动放到正确位置"),
    ("兜底", "repair", "保底方案/最后防线"),
    ("空转", "repair", "反复调试但没有正式提交"),
    ("返工", "repair", "因判据/口径错误重做"),
    ("走偏", "repair", "执行方向偏离任务目标"),
    ("跑偏", "repair", "同“走偏”的口语变体"),
    ("白跑", "repair", "没有产生有效证据的运行"),
    ("卡点", "repair", "阻塞任务的具体难点"),
    ("漂移", "repair", "判据/口径在往返中逐渐偏移"),
    ("缝合", "repair", "把不同证据面拼成完整链条"),
    ("拆弹", "repair", "拆除高风险缺陷"),
    ("收窄", "repair", "缩小判据/范围"),
    ("放宽", "repair", "放松判据（通常被禁止）"),
    ("降级", "repair", "把硬判据降为观察项"),
    ("误报", "repair", "检查器把正确结果判错"),
    ("漏判", "repair", "检查器没有发现真实缺陷"),
    ("补盲", "repair", "补上未覆盖的检查盲区"),
    ("留档", "repair", "把过程/结论存档"),
    ("在案", "repair", "记录已经进入案卷"),
    ("薄壳", "repair", "只保留产品差异的薄检查脚本"),
    ("硬判据", "repair", "不可放宽的硬性检查"),
    ("软判据", "repair", "可降级为观察项的检查"),
    # evidence/ritual
    ("自证", "ritual", "用盘上证据自我证明"),
    ("停手", "ritual", "收到裁定后立即停止"),
    ("回帖", "ritual", "在会话中给出结构化回复"),
    ("单刀", "ritual", "一次只改一处"),
    ("一发", "ritual", "一次只发一个正式提交"),
]

# Seed terms used as a baseline for diffusion/adoption comparisons.
SEED_BASELINE = ["解析", "核验", "绑定", "签名", "判据", "证据", "报告", "启用", "样例", "净值"]


def as_dict() -> list[dict]:
    seen = {}
    out = []
    for term, category, gloss in CURATED:
        if term in seen:
            continue
        seen[term] = True
        out.append({"term": term, "category": category, "gloss": gloss})
    return out
