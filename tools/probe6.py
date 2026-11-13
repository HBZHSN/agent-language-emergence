import sqlite3
import io

DB = 'C:/path/to/valuation/data/valuation.db'
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
out = io.open('tools/valuation_counts.txt', 'w', encoding='utf-8')
for t in ['products','sources','jobs','job_samples','releases','bindings','results','account_lines','holdings','cash_balances','fee_balances','watchdog_events']:
    try:
        n = con.execute('select count(*) from "%s"' % t).fetchone()[0]
        out.write('%s %d\n' % (t, n))
    except Exception as e:
        out.write('%s ERR %s\n' % (t, e))
out.write('\n== jobs by status ==\n')
for r in con.execute('select status, count(*) n from jobs group by status order by n desc'):
    out.write(repr(r) + '\n')
out.write('\n== products sample ==\n')
for r in con.execute('select id, identity, name, code, path from products limit 20'):
    out.write(repr(r) + '\n')
out.write('\n== jobs timeline ==\n')
for r in con.execute("select substr(created_at,1,10) d, count(*) n from jobs group by d order by d"):
    out.write(repr(r) + '\n')
out.write('\n== results timeline ==\n')
for r in con.execute("select substr(created_at,1,10) d, count(*) n from results group by d order by d"):
    out.write(repr(r) + '\n')
out.write('\n== bindings ==\n')
for r in con.execute('select status, count(*) n from bindings group by status'):
    out.write(repr(r) + '\n')
out.close()
print(open('tools/valuation_counts.txt', encoding='utf-8').read())
