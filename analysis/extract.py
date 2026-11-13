"""Phase C: extract normalized tables from the read-only OpenCode database.

Outputs (gitignored, local only):
  data/derived/messages.parquet
  data/derived/tool_calls.parquet
  data/derived/utterances.parquet
  data/derived/dispatches.parquet
  data/derived/sessions_enriched.parquet
  data/derived/jobs.parquet
  data/aggregates/c6_outcomes.csv
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path[0] = str(Path(__file__).resolve().parents[1])

from analysis import config


def dt(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def parse_json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def result_text(state: dict, limit: int = 2000) -> str:
    out = []
    for item in state.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            out.append(item.get("text") or "")
    text = "\n".join(out)
    return text[:limit]


def classify_act(agent: str, typ: str, text: str) -> str:
    short = config.AGENT_SHORT.get(agent, agent)
    if typ == "user":
        if short == "main":
            return "human_status"
        if short == "watchdog":
            return "watchdog_task"
        return "dispatch"
    if typ == "synthetic":
        return "notification"
    if typ == "system":
        return "system"
    if typ == "compaction":
        return "compaction"
    if short == "watchdog":
        t = text.strip()
        if t.startswith("{") and '"decision"' in t:
            return "verdict"
        return "watchdog_other"
    if not text.strip():
        return "empty"
    # Heuristic speech-act classes; used only for descriptive strata.
    if re.search(r"(PASSED|FAILED|approved|rejected|review_|changed_bindings|报告|结论)", text):
        return "report"
    if re.search(r"(请|必须|禁止|先 |下一步|裁定|收口|单发|停手|停止)", text):
        return "directive"
    if re.search(r"(核验|判据|证据|红位|绿|对账|逐字|面板|宿主|壳)", text):
        return "audit"
    if re.search(r"(job|product|进度|完成|排队|启用|结果)", text, re.I):
        return "status"
    return "other"


def extract_messages(con: sqlite3.Connection, sessions: pd.DataFrame) -> pd.DataFrame:
    agent = dict(zip(sessions["id"], sessions["agent_short"]))
    parent = dict(zip(sessions["id"], sessions["parent_id"]))
    title = dict(zip(sessions["id"], sessions["title"]))
    rows = []
    for r in con.execute(
        "select id, session_id, type, seq, time_created, time_updated, data from session_message"
    ):
        data = parse_json(r["data"]) or {}
        typ = r["type"]
        text = ""
        tool_calls = 0
        tokens_in = tokens_out = 0
        finish = None
        error = None
        model = None
        if typ == "assistant":
            parts = []
            for part in data.get("content") or []:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "text":
                    parts.append(part.get("text") or "")
                elif part.get("type") == "tool":
                    tool_calls += 1
            text = "\n".join(parts).strip()
            tok = data.get("tokens") or {}
            tokens_in = int(tok.get("input") or 0)
            tokens_out = int(tok.get("output") or 0)
            finish = data.get("finish")
            err = data.get("error")
            error = (err or {}).get("message") if isinstance(err, dict) else (str(err) if err else None)
            model = (data.get("model") or {}).get("id")
        else:
            text = (data.get("text") or "").strip()
        ts = r["time_created"]
        rows.append(
            {
                "message_id": r["id"],
                "session_id": r["session_id"],
                "parent_id": parent.get(r["session_id"]),
                "agent": agent.get(r["session_id"], "unknown"),
                "session_title": title.get(r["session_id"]),
                "type": typ,
                "seq": r["seq"],
                "time_utc": dt(ts),
                "time_ms": ts,
                "text": text,
                "text_len": len(text),
                "tool_calls": tool_calls,
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "finish": finish,
                "error": error,
                "model": model,
                "act": classify_act(agent.get(r["session_id"], "unknown"), typ, text),
            }
        )
    return pd.DataFrame(rows)


def extract_tool_calls(con: sqlite3.Connection, sessions: pd.DataFrame) -> pd.DataFrame:
    agent = dict(zip(sessions["id"], sessions["agent_short"]))
    rows = []
    for r in con.execute("select id, session_id, time_created, data from session_message where type='assistant'"):
        data = parse_json(r["data"]) or {}
        for idx, part in enumerate(data.get("content") or []):
            if not isinstance(part, dict) or part.get("type") != "tool":
                continue
            state = part.get("state") or {}
            inp = state.get("input")
            inp_text = json.dumps(inp, ensure_ascii=False, sort_keys=True) if inp is not None else ""
            err = state.get("error")
            rows.append(
                {
                    "message_id": r["id"],
                    "session_id": r["session_id"],
                    "agent": agent.get(r["session_id"], "unknown"),
                    "part_index": idx,
                    "tool_name": part.get("name") or "<missing>",
                    "status": state.get("status") or "unknown",
                    "input_json": inp_text,
                    "input_len": len(inp_text),
                    "input_keys": ",".join(sorted(inp.keys())) if isinstance(inp, dict) else "",
                    "error_type": (err or {}).get("type") if isinstance(err, dict) else None,
                    "error_message": (err or {}).get("message") if isinstance(err, dict) else None,
                    "result_excerpt": result_text(state),
                    "time_utc": dt((part.get("time") or {}).get("created") or r["time_created"]),
                    "duration_ms": (
                        ((part.get("time") or {}).get("completed") or 0)
                        - ((part.get("time") or {}).get("created") or 0)
                        if (part.get("time") or {}).get("completed")
                        else None
                    ),
                }
            )
    return pd.DataFrame(rows)


def extract_utterances(messages: pd.DataFrame, jobs: pd.DataFrame) -> pd.DataFrame:
    session_job = {}
    for _, j in jobs.iterrows():
        if j["child_session"]:
            session_job[j["child_session"]] = int(j["id"])
        if j["review_session"]:
            session_job[j["review_session"]] = int(j["id"])
    rows = []
    for _, m in messages.iterrows():
        if m["type"] not in ("assistant", "user", "synthetic", "system", "compaction"):
            continue
        act = m["act"]
        if act == "empty":
            continue
        rows.append(
            {
                "utterance_id": f"{m['message_id']}:text",
                "message_id": m["message_id"],
                "session_id": m["session_id"],
                "job_id": session_job.get(m["session_id"]),
                "agent": m["agent"],
                "type": m["type"],
                "act": act,
                "time_utc": m["time_utc"],
                "text": m["text"],
                "text_len": m["text_len"],
            }
        )
    # Job-level reports are among the densest prose artifacts in the system.
    for _, j in jobs.iterrows():
        for field, act in (("summary", "job_summary"), ("error", "job_error"), ("instruction", "job_instruction")):
            text = j.get(field)
            if not isinstance(text, str) or not text.strip():
                continue
            rows.append(
                {
                    "utterance_id": f"job:{j['id']}:{field}",
                    "message_id": None,
                    "session_id": None,
                    "job_id": int(j["id"]),
                    "agent": "main" if field == "summary" else "system",
                    "type": "job_artifact",
                    "act": act,
                    "time_utc": j["updated_at"] if field == "summary" else j["created_at"],
                    "text": text,
                    "text_len": len(text),
                }
            )
    # Watchdog event reasons (short, highly formulaic).
    vcon = config.connect_valuation()
    for r in vcon.execute("select id, job_id, action, state, reason, session_id, created_at from watchdog_events"):
        reason = r["reason"]
        if not reason:
            continue
        rows.append(
            {
                "utterance_id": f"watchdog_event:{r['id']}",
                "message_id": None,
                "session_id": r["session_id"],
                "job_id": r["job_id"],
                "agent": "watchdog",
                "type": "watchdog_event",
                "act": "watchdog_event",
                "time_utc": pd.to_datetime(r["created_at"], utc=True),
                "text": f"{r['action']} | {r['state'] or ''} | {reason}",
                "text_len": len(reason) + len(r["action"]) + len(r["state"] or "") + 6,
            }
        )
    return pd.DataFrame(rows)


def extract_dispatches(messages: pd.DataFrame, jobs: pd.DataFrame) -> pd.DataFrame:
    # One row per user message in a child session, with job mapping.
    child_to_job = {}
    for _, j in jobs.iterrows():
        if j["child_session"]:
            child_to_job[j["child_session"]] = (j["id"], "parser")
        if j["review_session"]:
            child_to_job[j["review_session"]] = (j["id"], "reviewer")
    rows = []
    for _, m in messages[messages["type"] == "user"].iterrows():
        job = child_to_job.get(m["session_id"])
        rows.append(
            {
                "message_id": m["message_id"],
                "session_id": m["session_id"],
                "agent": m["agent"],
                "job_id": job[0] if job else None,
                "role": job[1] if job else None,
                "time_utc": m["time_utc"],
                "text": m["text"],
                "text_len": m["text_len"],
                "act": m["act"],
            }
        )
    df = pd.DataFrame(rows)
    # turn index within session
    df = df.sort_values(["session_id", "time_utc"]).copy()
    df["turn"] = df.groupby("session_id").cumcount() + 1
    return df


def extract_jobs() -> pd.DataFrame:
    con = config.connect_valuation()
    jobs = pd.read_sql_query(
        """
        select j.id, j.product_id, j.status, j.rounds, j.restarts, j.recoveries,
               j.created_at, j.updated_at, j.child_session, j.review_session,
               j.module, j.library_hash, j.scope_start, j.scope_end,
               j.summary, j.error, j.instruction,
               length(coalesce(j.summary,'')) summary_len,
               length(coalesce(j.error,'')) error_len,
               p.code product_code, p.name product_name
        from jobs j join products p on p.id=j.product_id order by j.id
        """,
        con,
    )
    jobs["created_at"] = pd.to_datetime(jobs["created_at"], utc=True)
    jobs["updated_at"] = pd.to_datetime(jobs["updated_at"], utc=True)
    jobs["duration_min"] = (jobs["updated_at"] - jobs["created_at"]).dt.total_seconds() / 60
    return jobs


def outcomes(jobs: pd.DataFrame) -> pd.DataFrame:
    labels = {pid: f"Product {int(pid):03d}" for pid in jobs["product_id"].unique()}
    out = jobs.copy()
    out["product_label"] = out["product_id"].map(labels)
    out = out[
        [
            "id",
            "product_id",
            "product_label",
            "status",
            "rounds",
            "restarts",
            "recoveries",
            "duration_min",
            "summary_len",
            "error_len",
            "module",
        ]
    ]
    out.to_csv(config.AGGREGATES / "c6_outcomes.csv", index=False, encoding="utf-8-sig")
    return out


def main():
    sessions = pd.read_parquet(config.DERIVED / "sessions.parquet")
    if "agent_short" not in sessions:
        sessions["agent_short"] = sessions["agent"].map(config.AGENT_SHORT).fillna(sessions["agent"])
    con = config.connect_opencode()
    print("messages ...")
    messages = extract_messages(con, sessions)
    messages.to_parquet(config.DERIVED / "messages.parquet", index=False)
    print("tool calls ...")
    tools = extract_tool_calls(con, sessions)
    tools.to_parquet(config.DERIVED / "tool_calls.parquet", index=False)
    print("jobs ...")
    jobs = extract_jobs()
    jobs.to_parquet(config.DERIVED / "jobs.parquet", index=False)
    print("utterances ...")
    utt = extract_utterances(messages, jobs)
    utt.to_parquet(config.DERIVED / "utterances.parquet", index=False)
    print("dispatches ...")
    disp = extract_dispatches(messages, jobs)
    disp.to_parquet(config.DERIVED / "dispatches.parquet", index=False)
    print("outcomes ...")
    outcomes(jobs)
    print("counts", len(messages), len(tools), len(utt), len(jobs), len(disp))
    print("messages by agent:\n", messages.groupby("agent").size())
    print("tools by status:\n", tools.groupby("status").size())


if __name__ == "__main__":
    main()
