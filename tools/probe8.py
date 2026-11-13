import sqlite3
import json
import io

DB = 'C:/path/to/valuation/data/opencode/state/opencode/opencode.db'
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
con.row_factory = sqlite3.Row
out = io.open('tools/message_samples.txt', 'w', encoding='utf-8')

def text_of(d):
    parts = []
    for p in d.get('content') or []:
        if isinstance(p, dict) and p.get('type') == 'text':
            parts.append(p.get('text') or '')
    return '\n'.join(parts)

# first user message (dispatch) for parser/reviewer/watchdog, early and late by session time
for agent in ['valuation-parser', 'valuation-reviewer', 'valuation-watchdog']:
    rows = con.execute('''select m.session_id, m.data, s.time_created from session_message m
        join session_v2 s on s.id=m.session_id
        where m.type='user' and s.agent=? order by s.time_created''', (agent,)).fetchall()
    out.write('\n\n########## %s user messages (%d) ##########\n' % (agent, len(rows)))
    for r in rows[:2] + rows[-2:]:
        d = json.loads(r['data'])
        out.write('\n--- session %s ---\n' % r['session_id'])
        out.write((d.get('text') or '')[:2500] + '\n')

# main assistant text messages, first and last
rows = con.execute('''select m.data, m.time_created from session_message m join session_v2 s on s.id=m.session_id
    where m.type='assistant' and s.agent='valuation-main' order by m.time_created''').fetchall()
out.write('\n\n########## main assistant text (%d) ##########\n' % len(rows))
for r in rows[:5] + rows[-5:]:
    d = json.loads(r['data'])
    t = text_of(d)
    if t.strip():
        out.write('\n--- %s ---\n' % r['time_created'])
        out.write(t[:2000] + '\n')

# watchdog final reports: assistant text
rows = con.execute('''select m.data, m.time_created from session_message m join session_v2 s on s.id=m.session_id
    where m.type='assistant' and s.agent='valuation-watchdog' order by m.time_created''').fetchall()
out.write('\n\n########## watchdog assistant text (%d) ##########\n' % len(rows))
for r in rows[:5] + rows[-5:]:
    d = json.loads(r['data'])
    t = text_of(d)
    if t.strip():
        out.write('\n--- %s ---\n' % r['time_created'])
        out.write(t[:2000] + '\n')

# synthetic messages
rows = con.execute('''select m.data, m.time_created, s.agent from session_message m join session_v2 s on s.id=m.session_id
    where m.type='synthetic' order by m.time_created limit 4''').fetchall()
out.write('\n\n########## synthetic ##########\n')
for r in rows:
    d = json.loads(r['data'])
    out.write('\n--- %s %s ---\n' % (r['agent'], r['time_created']))
    out.write((d.get('text') or '')[:2000] + '\n')

out.close()
print(open('tools/message_samples.txt', encoding='utf-8').read()[:16000])
