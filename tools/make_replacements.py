import sqlite3
from pathlib import Path

con = sqlite3.connect('file:C:/path/to/valuation/data/valuation.db?mode=ro', uri=True)
lines = []
for pid, name, code in con.execute('select id, name, code from products order by id'):
    label = f'Product {int(pid):03d}'
    pcode = f'P{int(pid):03d}'
    if name and name.strip():
        lines.append(f'literal:{name.strip()}==>{label}')
    if code and code.strip():
        lines.append(f'literal:{code.strip()}==>{pcode}')
Path('data/private/replacements.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('lines', len(lines))
