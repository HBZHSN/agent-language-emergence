"""Role-dialect analysis: classifier, log-odds key terms, style features."""

from __future__ import annotations

import json
import math
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from analysis import config, text as T

ACTS = {
    "dispatch",
    "report",
    "audit",
    "directive",
    "status",
    "other",
    "job_summary",
    "job_error",
    "job_instruction",
    "verdict",
    "watchdog_other",
}
AGENTS = ["main", "parser", "reviewer", "watchdog"]


def load() -> pd.DataFrame:
    df = pd.read_parquet(config.DERIVED / "utterances.parquet")
    df = df[df.act.isin(ACTS) & df.agent.isin(AGENTS)].copy()
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)
    df["clean"] = df["text"].map(T.clean_prose)
    df = df[df.clean.str.len() >= 2].copy()
    df["group"] = df["session_id"].fillna("job:" + df["job_id"].astype("Int64").astype(str))
    df["doc_word"] = df["clean"].map(lambda s: " ".join(T.tokenize(s)))
    df["doc"] = df["doc_word"]
    df = df[df.doc.str.len() > 0].copy()
    return df


def classifier(df: pd.DataFrame, suffix: str = "") -> dict:
    X = np.asarray(df["doc"].tolist(), dtype=object)
    y = np.asarray(df["agent"].tolist(), dtype=object)
    groups = np.asarray(df["group"].tolist(), dtype=object)
    pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=60000, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", C=2.0, n_jobs=-1)),
        ]
    )
    cv = GroupKFold(n_splits=5)
    pred = cross_val_predict(pipe, X, y, groups=groups, cv=cv, n_jobs=1)
    report = classification_report(y, pred, labels=AGENTS, output_dict=True, zero_division=0)
    cm = confusion_matrix(y, pred, labels=AGENTS).tolist()
    macro = f1_score(y, pred, average="macro")
    weighted = f1_score(y, pred, average="weighted")
    # Full fit for interpretable coefficients.
    pipe.fit(X, y)
    vec: TfidfVectorizer = pipe.named_steps["tfidf"]
    clf: LogisticRegression = pipe.named_steps["clf"]
    terms = np.array(vec.get_feature_names_out())
    coefs = {}
    for i, agent in enumerate(clf.classes_):
        top = np.argsort(clf.coef_[i])[-30:][::-1]
        coefs[agent] = [{"term": str(terms[j]), "coef": round(float(clf.coef_[i][j]), 4)} for j in top]
    out = {
        "n": int(len(df)),
        "classes": list(clf.classes_),
        "macro_f1": round(float(macro), 4),
        "weighted_f1": round(float(weighted), 4),
        "report": report,
        "confusion_matrix": cm,
        "top_coefficients": coefs,
        "vectorizer_features": int(len(terms)),
    }
    (config.AGGREGATES / f"e3_classifier{suffix}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(cm, index=AGENTS, columns=AGENTS).to_csv(
        config.AGGREGATES / f"e3_confusion{suffix}.csv", encoding="utf-8-sig"
    )
    return out


def log_odds(df: pd.DataFrame) -> pd.DataFrame:
    # Term counts per agent over tokenized docs.
    counts = {a: Counter() for a in AGENTS}
    totals = Counter()
    for _, row in df.iterrows():
        toks = row["doc_word"].split()
        counts[row["agent"]].update(toks)
        totals[row["agent"]] += len(toks)
    vocab = set().union(*[set(c) for c in counts.values()])
    rows = []
    alpha = 0.5
    for agent in AGENTS:
        y_i = counts[agent]
        n_i = totals[agent]
        y_j = Counter()
        for other in AGENTS:
            if other != agent:
                y_j.update(counts[other])
        n_j = sum(totals[o] for o in AGENTS if o != agent)
        for term in vocab:
            a = y_i.get(term, 0)
            b = n_i - a
            c = y_j.get(term, 0)
            d = n_j - c
            if a + c < 8:
                continue
            delta = math.log((a + alpha) / (b + alpha)) - math.log((c + alpha) / (d + alpha))
            var = 1.0 / (a + alpha) + 1.0 / (c + alpha)
            z = delta / math.sqrt(var)
            rows.append({"agent": agent, "term": term, "count_agent": a, "count_rest": c, "log_odds": round(delta, 4), "z": round(z, 3)})
    out = pd.DataFrame(rows)
    out["abs_z"] = out["z"].abs()
    out = out.sort_values(["agent", "abs_z"], ascending=[True, False])
    out.to_csv(config.AGGREGATES / "e3_dialect_terms.csv", index=False, encoding="utf-8-sig")
    return out


def style(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for agent in AGENTS:
        sub = df[df.agent == agent]
        if len(sub) == 0:
            continue
        toks = sub["doc_word"].str.split()
        n_tokens = toks.map(len)
        ascii_tokens = toks.map(lambda xs: sum(1 for x in xs if x.isascii()))
        rows.append(
            {
                "agent": agent,
                "utterances": int(len(sub)),
                "tokens": int(n_tokens.sum()),
                "mean_tokens": round(float(n_tokens.mean()), 2),
                "median_tokens": float(n_tokens.median()),
                "p90_tokens": float(n_tokens.quantile(0.9)),
                "ascii_ratio": round(float(ascii_tokens.sum() / max(1, n_tokens.sum())), 4),
                "json_verdict_share": round(float((sub.act == "verdict").mean()), 4),
                "dispatch_share": round(float((sub.act == "dispatch").mean()), 4),
                "job_summary_share": round(float((sub.act == "job_summary").mean()), 4),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(config.AGGREGATES / "e3_style.csv", index=False, encoding="utf-8-sig")
    return out


def main():
    df = load()
    print("corpus", len(df), df.groupby("agent").size().to_dict())
    own = df[~df.act.isin(["dispatch", "job_summary", "job_instruction"])].copy()
    print("own-voice", len(own), own.groupby("agent").size().to_dict())
    clf_own = classifier(own, suffix="_own")
    clf_all = classifier(df, suffix="_all")
    for name, clf in (("own", clf_own), ("all", clf_all)):
        print(name, json.dumps({k: clf[k] for k in ["n", "macro_f1", "weighted_f1", "vectorizer_features"]}, ensure_ascii=False, indent=2))
        print(pd.DataFrame(clf["confusion_matrix"], index=AGENTS, columns=AGENTS))
    lo = log_odds(df)
    print(lo.groupby("agent").head(8)[["agent", "term", "count_agent", "count_rest", "z"]].to_string(index=False))
    st = style(df)
    print(st.to_string(index=False))


if __name__ == "__main__":
    main()
