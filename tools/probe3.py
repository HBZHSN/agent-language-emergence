import sqlite3
import json
import collections
import io

DB = 'C:/path/to/valuation/data/opencode/state/opencode/opencode.db'
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
con.row_factory = sqlite3.Row

out = io.open('tools/structure_sample.txt', 'w', encoding='utf-8')

def dump(label, obj, limit=4000):
    out.write('\n===== ' + label + ' =====\n')
    out.write(json.dumps(obj, ensure_ascii=False, indent=2)[:limit])
    out.write('\n')

# assistant message shapes
rows = con.execute("select * from session_message where type='assistant' order by time_created limit 3").fetchall()
for r in rows:
    d = json.loads(r['data'])
    dump('assistant ' + r['id'], d, 6000)

# user
r = con.execute("select * from session_message where type='user' order by time_created limit 1").fetchone()
dump('user', json.loads(r['data']), 3000)

# synthetic
r = con.execute("select * from session_message where type='synthetic' order by time_created limit 1").fetchone()
dump('synthetic', json.loads(r['data']), 3000)

# system
r = con.execute("select * from session_message where type='system' order by time_created limit 1").fetchone()
dump('system', json.loads(r['data']), 3000)

# compaction
r = con.execute("select * from session_message where type='compaction' order by time_created limit 1").fetchone()
dump('compaction', json.loads(r['data']), 3000)

# part/type census over assistant messages
ctr = collections.Counter()
keys = collections.Counter()
for r in con.execute("select data from session_message where type='assistant'"):
    d = json.loads(r['data'])
    if isinstance(d, dict):
        keys[tuple(sorted(d.keys()))] += 1
    parts = d.get('parts') if isinstance(d, dict) else None
    if isinstance(parts, list):
        for p in parts:
            if isinstance(p, dict):
                ctr[p.get('type')] += 1
            else:
                ctr['NON_DICT'] += 1
print('part types', ctr)
print('top-level key shapes', keys.most_common(10))

# tool names
tools = collections.Counter()
for r in con.execute("select data from session_message where type='assistant'"):
    d = json.loads(r['data'])
    for p in (d.get('parts') or []) if isinstance(d, dict) else []:
        if isinstance(p, dict) and p.get('type') in ('tool', 'tool-call', 'tool_use'):
            tools[p.get('tool') or p.get('name') or p.get('toolName')] += 1
print('tools', tools.most_common(30))
out.close()
print(open('tools/structure_sample.txt', encoding='utf-8').read()[:8000])
