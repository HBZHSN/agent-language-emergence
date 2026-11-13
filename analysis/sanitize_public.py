"""Redact institution/module names from public artifacts.

The production ``jobs.module`` field contains parser-module names that embed
client/institution abbreviations.  Public aggregates must not expose them.
This step replaces every raw module value with a stable ``module_NN`` label.
The raw-to-label mapping is written only to ``data/private/module_map.csv``
(gitignored); public files contain labels only.

The step is idempotent: already-sanitized ``module_NN`` values are left alone.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from analysis import config

LABEL_RE = re.compile(r"^module_\d{2}[a-z]?$")
CSV_MODULE_FILES = [
    "b2_binding_summary.csv",
    "c6_outcomes.csv",
    "e9_job_features.csv",
]
DIALECT_FILE = "e3_dialect_terms.csv"
CLASSIFIER_FILES = [
    "e3_classifier_all.json",
    "e3_classifier_nowd.json",
    "e3_classifier_own.json",
]


def _raw_modules_from_db() -> list[str]:
    try:
        con = config.connect_valuation()
        rows = con.execute(
            "select distinct module from jobs "
            "where module is not null and trim(module) != ''"
        ).fetchall()
        return sorted({str(r[0]).strip() for r in rows if r[0]})
    except Exception:
        return []


def _raw_modules_from_csv() -> list[str]:
    values: set[str] = set()
    for name in CSV_MODULE_FILES:
        path = config.AGGREGATES / name
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, usecols=lambda c: c == "module")
        except ValueError:
            continue
        if "module" in df.columns:
            for value in df["module"].dropna().unique():
                text = str(value).strip()
                if text and not LABEL_RE.match(text):
                    values.add(text)
    return sorted(values)


def _group_key(module: str) -> str:
    base = module.split("_valuation_sheet")[0]
    return base.split("_")[0].lower()


def _aliases(modules: list[str]) -> dict[str, str]:
    alias: dict[str, str] = {}
    for module in modules:
        group = _group_key(module)
        base = module.split("_valuation_sheet")[0]
        for token in base.split("_"):
            token = token.lower()
            if len(token) >= 3:
                alias[token] = group
    return alias


def _build_maps(modules: list[str]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    groups = sorted({_group_key(m) for m in modules if m})
    base = {g: f"module_{i + 1:02d}" for i, g in enumerate(groups)}
    module_map: dict[str, str] = {}
    for group in groups:
        variants = sorted(m for m in modules if _group_key(m) == group)
        for i, module in enumerate(variants):
            suffix = "" if i == 0 else "x"
            module_map[module] = base[group] + suffix
    alias_map = _aliases(modules)
    return module_map, alias_map, base


def _term_label(term: str, alias_map: dict[str, str], base: dict[str, str]) -> str | None:
    low = term.lower()
    for token, group in sorted(alias_map.items(), key=lambda kv: len(kv[0]), reverse=True):
        if low == token:
            # Only the primary group token gets the base label; secondary
            # tokens (client-name components) are variants.
            return base[group] if token == group else base[group] + "x"
        if low.startswith(token) and all(ch.isalnum() or ch == "_" for ch in low):
            return base[group] + "x"
    return None


def _sanitize_module_csv(name: str, module_map: dict[str, str]) -> int:
    path = config.AGGREGATES / name
    if not path.exists():
        return 0
    df = pd.read_csv(path)
    if "module" not in df.columns:
        return 0
    changed = 0

    def repl(value):
        nonlocal changed
        if pd.isna(value):
            return value
        text = str(value).strip()
        if LABEL_RE.match(text):
            return text
        if text in ("", "0", "None", "nan"):
            changed += 1
            return "module_00"
        label = module_map.get(text)
        if label is None:
            label = "module_99"
        changed += 1
        return label

    df["module"] = df["module"].map(repl)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return changed


def _sanitize_dialect_terms(alias_map: dict[str, str], base: dict[str, str]) -> int:
    path = config.AGGREGATES / DIALECT_FILE
    if not path.exists():
        return 0
    df = pd.read_csv(path)
    if "term" not in df.columns:
        return 0
    changed = 0

    def repl(term):
        nonlocal changed
        text = str(term)
        if LABEL_RE.match(text):
            return text
        label = _term_label(text, alias_map, base)
        if label is not None:
            changed += 1
            return label
        return text

    df["term"] = df["term"].map(repl)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return changed


def _redact_value(value, module_map: dict[str, str], alias_map: dict[str, str], base: dict[str, str], counter: list[int]):
    if isinstance(value, dict):
        return {k: _redact_value(v, module_map, alias_map, base, counter) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v, module_map, alias_map, base, counter) for v in value]
    if not isinstance(value, str):
        return value
    if value in module_map:
        counter[0] += 1
        return module_map[value]
    label = _term_label(value, alias_map, base)
    if label is not None:
        counter[0] += 1
        return label
    return value


def _sanitize_classifier(name: str, module_map: dict[str, str], alias_map: dict[str, str], base: dict[str, str]) -> int:
    path = config.AGGREGATES / name
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    counter = [0]
    redacted = _redact_value(data, module_map, alias_map, base, counter)
    path.write_text(json.dumps(redacted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return counter[0]


def _write_private_map(module_map: dict[str, str]) -> None:
    config.PRIVATE.mkdir(parents=True, exist_ok=True)
    rows = [{"kind": "module", "raw": raw, "label": label} for raw, label in sorted(module_map.items())]
    pd.DataFrame(rows).to_csv(config.PRIVATE / "module_map.csv", index=False, encoding="utf-8")


def main() -> None:
    modules = _raw_modules_from_db() or _raw_modules_from_csv()
    if not modules:
        print("sanitize: no raw modules found; nothing to do")
        return
    module_map, alias_map, base = _build_maps(modules)
    _write_private_map(module_map)
    counts = {
        "modules": len(module_map),
        "module_cells": sum(_sanitize_module_csv(name, module_map) for name in CSV_MODULE_FILES),
        "dialect_terms": _sanitize_dialect_terms(alias_map, base),
        "classifier_terms": sum(_sanitize_classifier(name, module_map, alias_map, base) for name in CLASSIFIER_FILES),
    }
    report = {
        "status": "ok",
        "labels": sorted(set(module_map.values())),
        **counts,
    }
    (config.AGGREGATES / "sanitization_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("sanitize:", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
