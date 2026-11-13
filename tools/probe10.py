import sqlite3, json, collections, io
DB='C:/path/to/valuation/data/opencode/state/opencode/opencode.db'
con=sqlite3.connect('file:'+DB+'?mode=ro',uri=True); con.row_factory=sqlite3.Row
out=io.open('tools/main_tools_by_day.txt','w',encoding='utf-8')
main='ses_abc2242e4d904322ab3222a8750b5d57'
byday=collections.defaultdict(collections.Counter)
firsts={}
for r in con.execute("select time_created,data from session_message where session_id=? and type='assistant' order by time_created",(main,)):
    d=json.loads(r['data']); day=__import__('datetime').datetime.utcfromtimestamp(r['time_created']/1000).strftime('%Y-%m-%d')
    for p in d.get('content') or []:
        if isinstance(p,dict) and p.get('type')=='tool':
            n=p.get('name'); byday[day][n]+=1
            ts=(p.get('time') or {}).get('created') or r['time_created']
            firsts.setdefault(n,ts)
for day in sorted(byday):
    out.write(day+' '+repr(byday[day].most_common())+'\n')
out.write('\nfirsts:\n')
for n,ts in sorted(firsts.items(), key=lambda x:x[1]):
    out.write('%s %s\n'%(n,__import__('datetime').datetime.utcfromtimestamp(ts/1000).isoformat()))
out.close()
print(open('tools/main_tools_by_day.txt',encoding='utf-8').read()[:8000])
