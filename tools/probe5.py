import sqlite3
import sys
import io

DB = 'C:/path/to/valuation/data/valuation.db'
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
out = io.open('tools/valuation_schema.txt', 'w', encoding='utf-8')
for name, sql in con.execute("select name, sql from sqlite_master where type='table' order by name"):
    out.write('\nTABLE %s\n%s\n' % (name, sql))
out.close()
print('done')
