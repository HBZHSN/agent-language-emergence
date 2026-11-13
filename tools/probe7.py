import sqlite3
import json
import io
import collections

DB = 'C:/path/to/valuation/data/opencode/state/opencode/opencode.db'
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
con.row_factory = sqlite3.Row
out = io.open('tools/tool_errors.txt', 'w', encoding='utf-8')

status = collections.Counter()
samples = collections.defaultdict(list)
for r in con.execute("select session_id, data from session_message where type='assistant'"):
    d = json.loads(r['data'])
    for p in d.get('content') or []:
        if not isinstance(p, dict) or p.get('type') != 'tool':
            continue
        name = p.get('name')
        st = p.get('state') or {}
        status[(name, st.get('status'))] += 1
        if name not in ('shell','read','glob','edit','write','grep','subagent','valuation_session_db','valuation_job','valuation_trial','valuation_validate','valuation_check_template','valuation_supervise','valuation_recover','valuation_stop','valuation_verifier','valuation_review_reject','valuation_prepare','valuation_fast_parse','valuation_verify','valuation_products','valuation_activate','valuation_progress','valuation_defer','valuation_control','valuation_queue'):
            if len(samples[name]) < 8:
                samples[name].append({'session': r['session_id'], 'status': st.get('status'), 'input': st.get('input'), 'error': st.get('error'), 'content': str(st.get('content'))[:600]})

for (name, st), n in sorted(status.items(), key=lambda x: -x[1])[:80]:
    out.write('%s | %s | %d\n' % (name, st, n))
out.write('\n== samples ==\n')
for name, arr in samples.items():
    out.write('\n### %s\n' % name)
    for s in arr:
        out.write(json.dumps(s, ensure_ascii=False)[:1500] + '\n')
out.close()
print(open('tools/tool_errors.txt', encoding='utf-8').read()[:12000])
