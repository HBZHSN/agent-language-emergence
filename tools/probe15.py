import sqlite3, json, io, datetime
con=sqlite3.connect('file:C:/path/to/valuation/data/opencode/state/opencode/opencode.db?mode=ro',uri=True); con.row_factory=sqlite3.Row
out=io.open('tools/valution_first.txt','w',encoding='utf-8')
rows=[]
for r in con.execute("select m.id,m.session_id,m.time_created,m.data,s.agent,s.title from session_message m join session_v2 s on s.id=m.session_id where m.type='assistant'"):
    d=json.loads(r['data'])
    for p in d.get('content') or []:
        if isinstance(p,dict) and p.get('type')=='tool' and p.get('name')=='valution':
            ts=(p.get('time') or {}).get('created') or r['time_created']
            rows.append((ts,r['id'],r['session_id'],r['agent'],r['title'],(p.get('state') or {}).get('input')))
rows.sort()
for x in rows[:10]:
    out.write(json.dumps({'ts':datetime.datetime.fromtimestamp(x[0]/1000,datetime.UTC).isoformat(),'msg':x[1],'session':x[2],'agent':x[3],'title':x[4],'input':x[5]},ensure_ascii=False)+'\n')
out.write('total %d\n'%len(rows))
out.close()
print(open('tools/valution_first.txt',encoding='utf-8').read())
