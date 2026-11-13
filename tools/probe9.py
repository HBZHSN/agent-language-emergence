import sqlite3
import json
import io

DB = 'C:/path/to/valuation/data/opencode/state/opencode/opencode.db'
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
con.row_factory = sqlite3.Row
out = io.open('tools/main_users.txt', 'w', encoding='utf-8')
rows = con.execute("select * from session_message where session_id='ses_abc2242e4d904322ab3222a8750b5d57' and type='user' order by seq").fetchall()
out.write('count %d\n' % len(rows))
for r in rows:
    d = json.loads(r['data'])
    out.write('\n--- %s seq=%s ---\n' % (r['time_created'], r['seq']))
    out.write((d.get('text') or '')[:3000] + '\n')
out.close()
print('done', len(rows))
