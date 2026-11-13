import sqlite3
import json

DB = 'C:/path/to/valuation/data/opencode/state/opencode/opencode.db'

con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
con.row_factory = sqlite3.Row

print('== totals ==')
row = con.execute('''
select count(*) n,
       sum(tokens_input) ti, sum(tokens_output) to_, sum(tokens_reasoning) tr,
       sum(tokens_cache_read) tcr, sum(tokens_cache_write) tcw,
       sum(cost) cost
from session_v2
''').fetchone()
print(dict(row))

print('== agents ==')
for r in con.execute('''select agent, count(*) n, sum(tokens_input) ti, sum(tokens_output) to_,
       sum(tokens_reasoning) tr, sum(tokens_cache_read) tcr, sum(tokens_cache_write) tcw,
       min(time_created) first, max(time_updated) last
from session_v2 group by agent order by n desc'''):
    print(dict(r))

print('== message types ==')
for r in con.execute('select type, count(*) n from session_message group by type order by n desc'):
    print(dict(r))

print('== sample message ==')
r = con.execute('select * from session_message order by time_created limit 1').fetchone()
print(dict(r))
print(r['data'][:2000])

print('== sample session ==')
r = con.execute('select * from session_v2 order by time_created limit 1').fetchone()
print(dict(r))

print('== date range ==')
for r in con.execute('''select date(time_created/1000,'unixepoch') d, count(*) n from session_v2 group by d order by d'''):
    print(dict(r))
