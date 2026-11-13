import sqlite3
import json
import collections
import io

DB = 'C:/path/to/valuation/data/opencode/state/opencode/opencode.db'
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
con.row_factory = sqlite3.Row

ctr = collections.Counter()
tools = collections.Counter()
by_agent_tools = collections.defaultdict(collections.Counter)
finish = collections.Counter()
models = collections.Counter()
sizes = []
errors = 0
for r in con.execute("select data from session_message where type='assistant'"):
    try:
        d = json.loads(r['data'])
    except Exception:
        errors += 1
        continue
    models[str(d.get('model'))] += 1
    finish[d.get('finish')] += 1
    content = d.get('content')
    if not isinstance(content, list):
        continue
    for p in content:
        if not isinstance(p, dict):
            continue
        ctr[p.get('type')] += 1
        if p.get('type') == 'tool':
            tools[p.get('name')] += 1
            by_agent_tools[d.get('agent')][p.get('name')] += 1
    sizes.append(len(r['data']))

out = io.open('tools/part_census.txt', 'w', encoding='utf-8')
out.write('part types: ' + repr(ctr) + '\n')
out.write('tools: ' + repr(tools.most_common(40)) + '\n')
out.write('finish: ' + repr(finish.most_common(20)) + '\n')
out.write('models: ' + repr(models.most_common(10)) + '\n')
out.write('errors: %d\n' % errors)
out.write('size total MB: %.1f max MB: %.1f\n' % (sum(sizes)/1e6, max(sizes)/1e6))
for agent, c in by_agent_tools.items():
    out.write('agent %s: %s\n' % (agent, c.most_common(30)))
out.write('\n== session titles ==\n')
for r in con.execute('select agent, count(*) n from session_v2 group by agent'):
    out.write(repr(dict(r)) + '\n')
out.write('\n== top titles ==\n')
for r in con.execute('select agent, title, count(*) n from session_v2 group by agent, title order by n desc limit 40'):
    out.write(repr(dict(r)) + '\n')
out.close()
print(open('tools/part_census.txt', encoding='utf-8').read()[:12000])
