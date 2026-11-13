"""Phase B audits: inventory the OpenCode and valuation databases.

Run with ``python analysis/audit.py``.  Everything is read-only.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analysis import config


def ms_to_dt(ms: int | None):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def parse_json(text: str | None):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def text_parts(data: dict) -> list[str]:
    out = []
    for part in data.get("content") or []:
        if isinstance(part, dict) and part.get("type") == "text":
            out.append(part.get("text") or "")
    return out


def iter_assistant(con: sqlite3.Connection):
    for row in con.execute("select id, session_id, time_created, data from session_message where type='assistant'"):
        data = parse_json(row["data"]) or {}
        yield row["id"], row["session_id"], row["time_created"], data


def audit_opencode() -> dict:
    con = config.connect_opencode()
    sessions = pd.read_sql_query("select * from session_v2", con)
    sessions["agent_short"] = sessions["agent"].map(config.AGENT_SHORT).fillna(sessions["agent"])
    sessions["start"] = pd.to_datetime(sessions["time_created"], unit="ms", utc=True)
    sessions["end"] = pd.to_datetime(sessions["time_updated"], unit="ms", utc=True)
    sessions["duration_min"] = (sessions["end"] - sessions["start"]).dt.total_seconds() / 60

    # message-level pass
    counters = collections.defaultdict(collections.Counter)
    daily = collections.defaultdict(collections.Counter)
    tool_stats = collections.defaultdict(lambda: {"calls": 0, "errors": 0, "agents": set(), "first": None, "last": None})
    type_counts = collections.Counter()
    model_counts = collections.Counter()
    text_chars = collections.Counter()
    text_parts_count = collections.Counter()
    empty_assistant = 0
    replacement_chars = 0
    step_tokens = collections.Counter()
    step_out = collections.Counter()
    msg_rows = con.execute("select session_id, type, time_created, data from session_message").fetchall()
    for row in msg_rows:
        typ = row["type"]
        type_counts[typ] += 1
        agent = sessions.loc[sessions["id"] == row["session_id"], "agent_short"]
        agent = agent.iloc[0] if len(agent) else "unknown"
        dt = ms_to_dt(row["time_created"])
        day = dt.strftime("%Y-%m-%d") if dt else "unknown"
        counters[agent]["messages"] += 1
        counters[agent][typ] += 1
        daily[day]["messages"] += 1
        daily[day][typ] += 1
        data = parse_json(row["data"]) or {}
        if typ == "assistant":
            if not data.get("content"):
                empty_assistant += 1
            parts = text_parts(data)
            nchars = sum(len(x) for x in parts)
            text_chars[agent] += nchars
            text_parts_count[agent] += len(parts)
            daily[day]["text_chars"] += nchars
            replacement_chars += sum(x.count("\ufffd") for x in parts)
            tok = data.get("tokens") or {}
            ti, to = int(tok.get("input") or 0), int(tok.get("output") or 0)
            step_tokens[agent] += ti
            step_out[agent] += to
            daily[day]["tokens_input"] += ti
            daily[day]["tokens_output"] += to
            model = data.get("model") or {}
            model_counts[f"{model.get('providerID')}/{model.get('id')}"] += 1
            for part in data.get("content") or []:
                if not isinstance(part, dict) or part.get("type") != "tool":
                    continue
                name = part.get("name") or "<missing>"
                state = part.get("state") or {}
                status = state.get("status") or "unknown"
                counters[agent]["tool_calls"] += 1
                daily[day]["tool_calls"] += 1
                tool_stats[name]["calls"] += 1
                tool_stats[name]["agents"].add(agent)
                if status == "error":
                    counters[agent]["tool_errors"] += 1
                    daily[day]["tool_errors"] += 1
                    tool_stats[name]["errors"] += 1
                ts = (part.get("time") or {}).get("created") or row["time_created"]
                if tool_stats[name]["first"] is None or ts < tool_stats[name]["first"]:
                    tool_stats[name]["first"] = ts
                if tool_stats[name]["last"] is None or ts > tool_stats[name]["last"]:
                    tool_stats[name]["last"] = ts

    # agent summary
    agent_rows = []
    for agent in config.AGENTS:
        short = config.AGENT_SHORT[agent]
        s = sessions[sessions["agent"] == agent]
        agent_rows.append(
            {
                "agent": short,
                "sessions": len(s),
                "messages": counters[short]["messages"],
                "assistant": counters[short]["assistant"],
                "user": counters[short]["user"],
                "synthetic": counters[short]["synthetic"],
                "idle": counters[short]["idle"],
                "compaction": counters[short]["compaction"],
                "tool_calls": counters[short]["tool_calls"],
                "tool_errors": counters[short]["tool_errors"],
                "tool_error_rate": round(counters[short]["tool_errors"] / max(1, counters[short]["tool_calls"]), 4),
                "text_parts": text_parts_count[short],
                "text_chars": text_chars[short],
                "step_tokens_input": step_tokens[short],
                "step_tokens_output": step_out[short],
                "session_tokens_input": int(s["tokens_input"].sum()),
                "session_tokens_output": int(s["tokens_output"].sum()),
                "first": s["start"].min().isoformat() if len(s) else None,
                "last": s["end"].max().isoformat() if len(s) else None,
                "median_duration_min": round(float(s["duration_min"].median()), 2) if len(s) else None,
                "max_duration_min": round(float(s["duration_min"].max()), 2) if len(s) else None,
            }
        )
    agent_df = pd.DataFrame(agent_rows)
    agent_df.to_csv(config.AGGREGATES / "b1_agent_summary.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [{"type": k, "count": v} for k, v in type_counts.most_common()]
    ).to_csv(config.AGGREGATES / "b1_message_types.csv", index=False, encoding="utf-8-sig")

    daily_rows = []
    for day in sorted(daily):
        d = daily[day]
        daily_rows.append(
            {
                "date": day,
                "messages": d["messages"],
                "assistant": d["assistant"],
                "user": d["user"],
                "synthetic": d["synthetic"],
                "tool_calls": d["tool_calls"],
                "tool_errors": d["tool_errors"],
                "text_chars": d["text_chars"],
                "step_tokens_input": d["tokens_input"],
                "step_tokens_output": d["tokens_output"],
            }
        )
    pd.DataFrame(daily_rows).to_csv(config.AGGREGATES / "b1_daily.csv", index=False, encoding="utf-8-sig")

    tool_rows = []
    for name, st in tool_stats.items():
        tool_rows.append(
            {
                "tool": name,
                "calls": st["calls"],
                "errors": st["errors"],
                "error_rate": round(st["errors"] / max(1, st["calls"]), 4),
                "agents": ",".join(sorted(st["agents"])),
                "official": int(name in config.OFFICIAL_TOOLS),
                "first": ms_to_dt(st["first"]).isoformat() if st["first"] else None,
                "last": ms_to_dt(st["last"]).isoformat() if st["last"] else None,
            }
        )
    tool_df = pd.DataFrame(tool_rows).sort_values("calls", ascending=False)
    tool_df.to_csv(config.AGGREGATES / "b1_tool_summary.csv", index=False, encoding="utf-8-sig")

    # session-level table (small, useful for later phases)
    sessions_out = sessions[
        [
            "id",
            "parent_id",
            "agent",
            "agent_short",
            "title",
            "version",
            "start",
            "end",
            "duration_min",
            "tokens_input",
            "tokens_output",
            "cost",
            "idle_outcome",
        ]
    ].copy()
    sessions_out.to_parquet(config.DERIVED / "sessions.parquet", index=False)

    summary = {
        "sessions": int(len(sessions)),
        "messages": int(len(msg_rows)),
        "message_types": dict(type_counts),
        "models": dict(model_counts),
        "agents": agent_rows,
        "empty_assistant": empty_assistant,
        "replacement_chars": replacement_chars,
        "tool_names": int(len(tool_stats)),
        "non_official_tool_names": int(sum(1 for n in tool_stats if n not in config.OFFICIAL_TOOLS)),
        "session_tokens_input": int(sessions["tokens_input"].sum()),
        "session_tokens_output": int(sessions["tokens_output"].sum()),
        "step_tokens_input": int(sum(step_tokens.values())),
        "step_tokens_output": int(sum(step_out.values())),
        "first": sessions["start"].min().isoformat(),
        "last": sessions["end"].max().isoformat(),
    }
    (config.AGGREGATES / "b1_opencode_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def audit_valuation() -> dict:
    con = config.connect_valuation()
    tables = [
        "products",
        "sources",
        "jobs",
        "job_samples",
        "releases",
        "bindings",
        "results",
        "account_lines",
        "holdings",
        "cash_balances",
        "fee_balances",
        "watchdog_events",
    ]
    counts = []
    for t in tables:
        n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
        counts.append({"table": t, "rows": n})
    pd.DataFrame(counts).to_csv(config.AGGREGATES / "b2_table_counts.csv", index=False, encoding="utf-8-sig")

    jobs_status = pd.read_sql_query("select status, count(*) n from jobs group by status order by n desc", con)
    jobs_status.to_csv(config.AGGREGATES / "b2_jobs_by_status.csv", index=False, encoding="utf-8-sig")

    jobs_daily = pd.read_sql_query(
        "select substr(created_at,1,10) date, count(*) n from jobs group by date order by date", con
    )
    results_daily = pd.read_sql_query(
        "select substr(created_at,1,10) date, count(*) n from results group by date order by date", con
    )
    results_status = pd.read_sql_query(
        "select status, count(*) n from results group by status order by n desc", con
    )
    results_status.to_csv(config.AGGREGATES / "b2_results_by_status.csv", index=False, encoding="utf-8-sig")
    daily = jobs_daily.merge(results_daily, on="date", how="outer", suffixes=("_jobs", "_results")).fillna(0)
    daily.to_csv(config.AGGREGATES / "b2_daily.csv", index=False, encoding="utf-8-sig")

    product_summary = pd.read_sql_query(
        """
        select p.id product_id, p.code, p.name, p.path,
               (select count(*) from sources s where s.product_id=p.id) sources,
               (select count(*) from results r where r.product_id=p.id) results,
               (select count(*) from bindings b where b.product_id=p.id) bindings,
               (select count(*) from jobs j where j.product_id=p.id) jobs,
               (select min(r.valuation_date) from results r where r.product_id=p.id) first_date,
               (select max(r.valuation_date) from results r where r.product_id=p.id) last_date,
               (select count(distinct r.valuation_date) from results r where r.product_id=p.id) distinct_dates
        from products p order by p.id
        """,
        con,
    )
    # Full product identity stays private (gitignored).  Public aggregates only
    # carry a pseudonymous label and counts.
    product_summary.to_csv(config.PRIVATE / "b2_product_summary_private.csv", index=False, encoding="utf-8-sig")
    public_products = product_summary.copy()
    public_products["product_label"] = public_products["product_id"].map(lambda x: f"Product {int(x):03d}")
    public_products = public_products[
        ["product_id", "product_label", "sources", "results", "bindings", "jobs", "distinct_dates"]
    ]
    public_products.to_csv(config.AGGREGATES / "b2_product_summary.csv", index=False, encoding="utf-8-sig")

    bindings = pd.read_sql_query(
        """
        select b.id, b.product_id, p.code, p.name, b.signature, b.module, b.release_hash,
               b.start_date, b.end_date, b.status, b.origin
        from bindings b join products p on p.id=b.product_id order by b.product_id, b.start_date
        """,
        con,
    )
    bindings.to_csv(config.PRIVATE / "b2_bindings_private.csv", index=False, encoding="utf-8-sig")
    binding_summary = (
        bindings.groupby(["module", "status", "origin"])
        .agg(bindings=("id", "size"), products=("product_id", "nunique"))
        .reset_index()
        .sort_values("bindings", ascending=False)
    )
    binding_summary.to_csv(config.AGGREGATES / "b2_binding_summary.csv", index=False, encoding="utf-8-sig")

    summary = {
        "table_counts": {r["table"]: int(r["rows"]) for r in counts},
        "jobs_status": dict(zip(jobs_status["status"], jobs_status["n"].astype(int))),
        "results_status": dict(zip(results_status["status"], results_status["n"].astype(int))),
        "products": int(len(product_summary)),
        "bindings_active": int((bindings["status"] == "active").sum()),
        "releases": int(con.execute("select count(*) from releases").fetchone()[0]),
        "results": int(con.execute("select count(*) from results").fetchone()[0]),
    }
    (config.AGGREGATES / "b2_valuation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def audit_filesystem() -> dict:
    rows = []
    for name in ["snapshots", "jobs", "results", "diagnostics", "harness-watch", "opencode", "derived"]:
        base = config.SRC / "data" / name if name != "derived" else config.DERIVED
        if not base.exists():
            continue
        files = 0
        total = 0
        exts = collections.Counter()
        for root, _dirs, names in os.walk(base):
            for fn in names:
                files += 1
                try:
                    total += (Path(root) / fn).stat().st_size
                except OSError:
                    pass
                exts[Path(fn).suffix.lower() or "<none>"] += 1
        rows.append(
            {
                "directory": name,
                "path": config.display_path(base),
                "files": files,
                "bytes": total,
                "gb": round(total / 1e9, 2),
                "top_extensions": ", ".join(f"{k}:{v}" for k, v in exts.most_common(5)),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(config.AGGREGATES / "b3_filesystem_inventory.csv", index=False, encoding="utf-8-sig")
    return {"directories": rows}


def audit_timeline() -> dict:
    con = config.connect_opencode()
    sessions = pd.read_sql_query("select id, agent, time_created from session_v2", con)
    sessions["hour"] = pd.to_datetime(sessions["time_created"], unit="ms", utc=True).dt.floor("h")
    agent_map = dict(zip(sessions["id"], sessions["agent"].map(config.AGENT_SHORT).fillna(sessions["agent"])))
    msg_rows = con.execute("select session_id, type, time_created, data from session_message").fetchall()
    recs = []
    for row in msg_rows:
        data = parse_json(row["data"]) or {}
        dt = ms_to_dt(row["time_created"])
        rec = {
            "hour": dt.replace(minute=0, second=0, microsecond=0),
            "agent": agent_map.get(row["session_id"], "unknown"),
            "type": row["type"],
            "tool_calls": 0,
            "tool_errors": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "text_chars": 0,
        }
        if row["type"] == "assistant":
            parts = text_parts(data)
            rec["text_chars"] = sum(len(x) for x in parts)
            tok = data.get("tokens") or {}
            rec["tokens_input"] = int(tok.get("input") or 0)
            rec["tokens_output"] = int(tok.get("output") or 0)
            for part in data.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "tool":
                    rec["tool_calls"] += 1
                    if (part.get("state") or {}).get("status") == "error":
                        rec["tool_errors"] += 1
        recs.append(rec)
    msg = pd.DataFrame(recs)
    hourly = msg.groupby("hour").agg(
        messages=("type", "size"),
        assistant=("type", lambda s: (s == "assistant").sum()),
        user=("type", lambda s: (s == "user").sum()),
        synthetic=("type", lambda s: (s == "synthetic").sum()),
        tool_calls=("tool_calls", "sum"),
        tool_errors=("tool_errors", "sum"),
        tokens_input=("tokens_input", "sum"),
        tokens_output=("tokens_output", "sum"),
        text_chars=("text_chars", "sum"),
    )
    sess_hourly = sessions.groupby("hour").size().rename("sessions_started")
    hourly = hourly.join(sess_hourly, how="outer").fillna(0)

    vcon = config.connect_valuation()
    jobs = pd.read_sql_query("select id, created_at, updated_at, status from jobs", vcon)
    jobs["hour"] = pd.to_datetime(jobs["created_at"], utc=True).dt.floor("h")
    jobs_hourly = jobs.groupby("hour").size().rename("jobs_created")
    results = pd.read_sql_query("select id, created_at from results", vcon)
    results["hour"] = pd.to_datetime(results["created_at"], utc=True).dt.floor("h")
    results_hourly = results.groupby("hour").size().rename("results_created")
    events = pd.read_sql_query("select id, created_at from watchdog_events", vcon)
    events["hour"] = pd.to_datetime(events["created_at"], utc=True).dt.floor("h")
    events_hourly = events.groupby("hour").size().rename("watchdog_events")
    hourly = hourly.join([jobs_hourly, results_hourly, events_hourly], how="outer").fillna(0).sort_index()
    hourly.index.name = "hour_utc"
    hourly.to_csv(config.AGGREGATES / "b5_timeline_hourly.csv", encoding="utf-8-sig")

    # Key first occurrences
    tc = con.execute(
        "select data from session_message where type='assistant'"
    ).fetchall()
    first_tool = {}
    for row in tc:
        data = parse_json(row["data"]) or {}
        for part in data.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "tool":
                name = part.get("name")
                ts = (part.get("time") or {}).get("created")
                if name and ts and (name not in first_tool or ts < first_tool[name]):
                    first_tool[name] = ts
    events_out = [
        {"event": "first_session", "timestamp": sessions["hour"].min().isoformat(), "source": "session_v2"},
        {"event": "first_job", "timestamp": pd.to_datetime(jobs["created_at"], utc=True).min().isoformat(), "source": "jobs"},
        {"event": "first_result", "timestamp": pd.to_datetime(results["created_at"], utc=True).min().isoformat(), "source": "results"},
        {"event": "first_watchdog_event", "timestamp": pd.to_datetime(events["created_at"], utc=True).min().isoformat(), "source": "watchdog_events"},
    ]
    for name in ["valuation_trial", "valuation_validate", "valuation_activate", "valuation_recover", "valution"]:
        if name in first_tool:
            events_out.append(
                {"event": f"first_tool:{name}", "timestamp": ms_to_dt(first_tool[name]).isoformat(), "source": "opencode"}
            )
    pd.DataFrame(events_out).to_csv(config.AGGREGATES / "b5_key_events.csv", index=False, encoding="utf-8-sig")
    return {"hourly_rows": int(len(hourly)), "key_events": events_out}


def audit_quality() -> dict:
    con = config.connect_opencode()
    sessions = pd.read_sql_query("select id, agent, title, parent_id from session_v2", con)
    messages = con.execute("select id, session_id, type, data from session_message").fetchall()
    hashes = collections.Counter()
    duplicate_sessions = collections.Counter()
    empty = collections.Counter()
    replacement = 0
    for row in messages:
        data = parse_json(row["data"]) or {}
        h = hashlib.sha256((row["data"] or "").encode("utf-8")).hexdigest()
        hashes[h] += 1
        duplicate_sessions[h] = row["session_id"]
        if row["type"] == "assistant":
            parts = text_parts(data)
            if not parts:
                empty["assistant_no_text"] += 1
            replacement += sum(x.count("\ufffd") for x in parts)
    dup_groups = sum(1 for v in hashes.values() if v > 1)
    dup_msgs = sum(v for v in hashes.values() if v > 1)

    vcon = config.connect_valuation()
    jobs = pd.read_sql_query("select id, child_session, review_session, status from jobs", vcon)
    session_ids = set(sessions["id"])
    mapped_child = jobs["child_session"].isin(session_ids).sum()
    mapped_review = jobs["review_session"].isin(session_ids).sum()
    main_id = "ses_abc2242e4d904322ab3222a8750b5d57"
    main_user = con.execute(
        "select count(*) from session_message where session_id=? and type='user'", (main_id,)
    ).fetchone()[0]
    main_seq = con.execute(
        "select min(seq), max(seq), min(time_created), max(time_created), count(*) from session_message where session_id=?",
        (main_id,),
    ).fetchone()
    child_prompts = con.execute(
        """
        select s.agent, count(*) from session_message m
        join session_v2 s on s.id=m.session_id
        where m.type='user' and s.parent_id=? group by s.agent
        """,
        (main_id,),
    ).fetchall()
    first = con.execute("select min(time_created), max(time_created) from session_message").fetchone()
    token_sessions = con.execute("select sum(tokens_input), sum(tokens_output) from session_v2").fetchone()
    main_tokens = con.execute("select tokens_input, tokens_output from session_v2 where id=?", (main_id,)).fetchone()
    # Sum of per-step tokens requires parsing; use the audit summary if present.
    b1 = json.loads((config.AGGREGATES / "b1_opencode_summary.json").read_text(encoding="utf-8"))
    main_step = next(a for a in b1["agents"] if a["agent"] == "main")
    quality = {
        "sessions": int(len(sessions)),
        "messages": int(len(messages)),
        "duplicate_message_groups": dup_groups,
        "duplicate_messages": dup_msgs,
        "duplicate_share": round(dup_msgs / max(1, len(messages)), 4),
        "assistant_without_text": int(empty["assistant_no_text"]),
        "replacement_chars": replacement,
        "jobs": int(len(jobs)),
        "jobs_child_session_mapped": int(mapped_child),
        "jobs_review_session_mapped": int(mapped_review),
        "main_human_user_messages": int(main_user),
        "main_seq_min": int(main_seq[0]),
        "main_seq_max": int(main_seq[1]),
        "main_first_message_utc": ms_to_dt(main_seq[2]).isoformat(),
        "main_last_message_utc": ms_to_dt(main_seq[3]).isoformat(),
        "main_message_count": int(main_seq[4]),
        "main_session_tokens_input": int(main_tokens[0]),
        "main_step_tokens_input": int(main_step["step_tokens_input"]),
        "main_missing_tokens_input": int(main_tokens[0]) - int(main_step["step_tokens_input"]),
        "main_missing_token_share": round(
            (int(main_tokens[0]) - int(main_step["step_tokens_input"])) / max(1, int(main_tokens[0])), 4
        ),
        "child_user_prompts": {r[0]: int(r[1]) for r in child_prompts},
        "first_message_utc": ms_to_dt(first[0]).isoformat(),
        "last_message_utc": ms_to_dt(first[1]).isoformat(),
        "session_tokens_input": int(token_sessions[0]),
        "session_tokens_output": int(token_sessions[1]),
        "step_tokens_input": b1["step_tokens_input"],
        "step_tokens_output": b1["step_tokens_output"],
        "token_ratio_step_over_session": round(b1["step_tokens_input"] / max(1, token_sessions[0]), 4),
    }
    (config.AGGREGATES / "b6_quality.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return quality


def main():
    print("B1 opencode ...")
    b1 = audit_opencode()
    print(json.dumps(b1, ensure_ascii=False, indent=2)[:2000])
    print("B2 valuation ...")
    b2 = audit_valuation()
    print(json.dumps(b2, ensure_ascii=False, indent=2)[:1500])
    print("B3 filesystem ...")
    b3 = audit_filesystem()
    print(json.dumps(b3, ensure_ascii=False, indent=2)[:1000])
    print("B5 timeline ...")
    b5 = audit_timeline()
    print(json.dumps(b5, ensure_ascii=False, indent=2)[:1000])
    print("B6 quality ...")
    b6 = audit_quality()
    print(json.dumps(b6, ensure_ascii=False, indent=2)[:1500])


if __name__ == "__main__":
    main()
