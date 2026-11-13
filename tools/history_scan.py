import sqlite3, subprocess, re
con=sqlite3.connect('file:C:/path/to/valuation/data/valuation.db?mode=ro',uri=True)
names=[r[0] for r in con.execute('select name from products') if r[0] and len(r[0])>=4]
codes=[r[0] for r in con.execute('select code from products') if r[0]]
revs=subprocess.run(['git','rev-list','--all'],capture_output=True,text=True).stdout.split()
print('commits',len(revs))
for rev in revs:
    files=subprocess.run(['git','ls-tree','-r','--name-only',rev],capture_output=True,text=True).stdout.splitlines()
    for f in files:
        if not f.lower().endswith(('.md','.txt','.py','.json','.csv','.html','.js','.ps1','.sh','.yml','.yaml')): continue
        blob=subprocess.run(['git','show',f'{rev}:{f}'],capture_output=True,text=True,encoding='utf-8',errors='replace').stdout
        for n in names:
            if n in blob:
                print('NAME',rev[:8],f,n[:8]+'...')
                break
        for c in codes:
            if re.search(r'(?<![A-Za-z0-9])'+re.escape(c)+r'(?![A-Za-z0-9])',blob):
                print('CODE',rev[:8],f,c[:2]+'***')
                break
