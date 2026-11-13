"""Text cleaning, tokenization and seed-vocabulary helpers.

The goal is to separate *prose* (agent-authored natural language) from
structured artifacts (JSON, shell commands, SQL, file paths, tool output).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import jieba

from analysis import config

CUSTOM_TERMS = [
    line.strip()
    for line in (Path(__file__).parent / "lexicon_terms.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
for _term in CUSTOM_TERMS:
    jieba.add_word(_term, freq=100000)

STOPWORDS = set(
    """
    的 了 是 在 和 与 及 或 就 都 而 被 把 对 为 以 于 从 到 中 上 下 不 没有 也 这 那 一个 我们 你们 他们
    它们 自己 这个 那个 这些 那些 什么 怎么 如何 为什么 因为 所以 但是 然而 而且 并且 然后 就是 还是
    已经 正在 将要 可能 必须 只能 只会 以及 其中 之一 这样 那样 一下 一些 一种 没有 不是 可以 需要
    应该 如果 现在 目前 继续 进行 出现 发现 问题 情况 时候 地方 方面 部分 全部 所有 每个 任何 其他
    另外 同时 之后 之前 以上 以下 通过 对于 关于 由于 根据 按照 来自 处于 用于 作为 成为 认为 觉得
    知道 看到 得到 给出 使用 完成 开始 结束 一直 仍然 似乎 好像 大约 左右 很多 很少 更多 更少
    我 你 他 她 它 其 之 此 该 等 一 二 三 四 五 六 七 八 九 十 个 些 么 吧 呢 啊 呀 哦 嗯
    the a an and or of to in on for with by from as is are was were be been being this that these those
    it its we you they he she i not no yes if then else when while can could should would may might must
    will shall do does did done have has had get gets got make makes made use used using into over under
    """.split()
)

SINGLE_CHAR_TERMS = set("壳红绿刀卷坑链面位点线局轮刀发停查核验判证据账盘")

BOILERPLATE = [
    "You are a subagent spawned by another session.",
    "The user has requested that you continue",
    "请判断下面任务是否正常推进、空转或发生故障。",
    "先核对近期操作，按需读取实际代码、输出和失败报告。",
    "只读，不执行解析、不改代码、不调度主 agent。上次结论仅供比较，不当作事实。",
    "最近8条会话消息（最多36000字符，较长时截断；完整证据以任务文件为准）：",
]

_RE_FENCED = re.compile(r"```.*?```", re.S)
_RE_INLINE = re.compile(r"`[^`]*`")
_RE_JSON_OBJ = re.compile(r"\{[^{}]*\}", re.S)
_RE_JSON_ARR = re.compile(r"\[[^\[\]]*\]", re.S)
_RE_HTML = re.compile(r"<[^>]{1,200}>")
_RE_URL = re.compile(r"https?://\S+|ftp://\S+", re.I)
_RE_WINPATH = re.compile(r"[A-Za-z]:\\[^\s\"'<>]+")
_RE_POSIXPATH = re.compile(r"(?<![A-Za-z0-9_])/(?:workspace|opt|tmp|home|mnt|data)/[^\s\"'<>]+")
_RE_HASH = re.compile(r"\b[0-9a-fA-F]{16,}\b")
_RE_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_RE_NUM = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?%?")
_RE_ASCII_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-/]*")
_RE_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
_RE_PUNCT = re.compile(r"[\s\u3000-\u303f\uff00-\uffef!-/:-@\[-`{-~]+")


@lru_cache(maxsize=1)
def product_terms() -> tuple[tuple[str, ...], tuple[str, ...]]:
    con = config.connect_valuation()
    rows = con.execute("select name, code from products").fetchall()
    names = sorted({str(r[0]).strip() for r in rows if r[0] and len(str(r[0]).strip()) >= 4}, key=len, reverse=True)
    codes = sorted({str(r[1]).strip() for r in rows if r[1] and len(str(r[1]).strip()) >= 4})
    return tuple(names), tuple(codes)


@lru_cache(maxsize=1)
def seed_text() -> str:
    files = [config.SRC / "valuation" / "opencode" / n for n in config.SEED_PROMPTS]
    files += [config.SRC / n for n in config.SEED_DOCS]
    files += [config.SRC / "valuation" / "opencode" / "index.js", config.CONFIG_JSON]
    chunks = []
    for p in files:
        if p.exists():
            chunks.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks).casefold()


def is_seeded(term: str) -> bool:
    return term.casefold() in seed_text()


def mask_products(text: str) -> str:
    names, codes = product_terms()
    for name in names:
        if name in text:
            text = text.replace(name, " PRODUCT ")
    for code in codes:
        text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(code) + r"(?![A-Za-z0-9])", " CODE ", text)
    return text


def strip_structured(text: str) -> str:
    text = _RE_FENCED.sub(" ", text)
    text = _RE_INLINE.sub(" ", text)
    for _ in range(8):
        new = _RE_JSON_OBJ.sub(" ", text)
        new = _RE_JSON_ARR.sub(" ", new)
        if new == text:
            break
        text = new
    text = _RE_HTML.sub(" ", text)
    text = _RE_URL.sub(" ", text)
    text = _RE_WINPATH.sub(" ", text)
    text = _RE_POSIXPATH.sub(" ", text)
    text = _RE_UUID.sub(" ", text)
    text = _RE_HASH.sub(" ", text)
    text = _RE_NUM.sub(" ", text)
    for phrase in BOILERPLATE:
        text = text.replace(phrase, " ")
    # Drop lines that still look like serialized data.
    lines = []
    for line in text.splitlines():
        if line.count('"') >= 4 or line.count(":") >= 3 and line.count("{") >= 1:
            continue
        lines.append(line)
    return " ".join(lines)


def clean_prose(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = mask_products(text)
    text = strip_structured(text)
    text = _RE_PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_verdict(text: str) -> dict | None:
    """Return the parsed watchdog JSON object if the text is a verdict."""
    if not isinstance(text, str):
        return None
    t = text.strip()
    if not t.startswith("{"):
        return None
    try:
        obj = json.loads(t)
    except Exception:
        return None
    if isinstance(obj, dict) and "decision" in obj:
        return obj
    return None


def verdict_prose(text: str) -> str:
    obj = extract_verdict(text)
    if not obj:
        return clean_prose(text)
    parts = [str(obj.get("summary") or "")]
    ev = obj.get("evidence")
    if isinstance(ev, list):
        parts.extend(str(x) for x in ev)
    return clean_prose("\n".join(parts))


def tokenize(text: str) -> list[str]:
    text = mask_products(text)
    text = strip_structured(text)
    tokens: list[str] = []
    pos = 0
    for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_.\-/]*|[\u4e00-\u9fff]+", text):
        if m.start() > pos:
            pos = m.start()
        chunk = m.group(0)
        pos = m.end()
        if chunk[0].isascii():
            tok = chunk.casefold().strip("._-/")
            if len(tok) < 2 or len(tok) > 60:
                continue
            if tok in STOPWORDS:
                continue
            # Generated IDs and hashes are not lexical items.
            if re.fullmatch(r"(?:job|ses|msg|p|j|r|c|l|e|v|s)[_-]?\d+", tok):
                continue
            if re.fullmatch(r"[0-9a-f]{8,}", tok):
                continue
            tokens.append(tok)
        else:
            for w in jieba.cut(chunk, HMM=True):
                w = w.strip()
                if not w:
                    continue
                if w in STOPWORDS:
                    continue
                if len(w) == 1 and w not in SINGLE_CHAR_TERMS:
                    continue
                tokens.append(w)
    return tokens


def content_tokens(tokens: list[str]) -> list[str]:
    out = []
    for t in tokens:
        if t in STOPWORDS:
            continue
        if len(t) == 1 and not ("\u4e00" <= t <= "\u9fff" and t in SINGLE_CHAR_TERMS):
            continue
        out.append(t)
    return out


def cjk_runs(text: str) -> list[str]:
    text = mask_products(text)
    text = strip_structured(text)
    return _RE_CJK_RUN.findall(text)


def char_ngrams(text: str, n_min: int = 2, n_max: int = 6) -> list[str]:
    out = []
    for run in cjk_runs(text):
        for n in range(n_min, n_max + 1):
            for i in range(len(run) - n + 1):
                out.append(run[i : i + n])
    return out


def word_ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
