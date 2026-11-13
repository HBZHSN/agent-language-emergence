import sqlite3, json, collections, io, datetime
DB='C:/path/to/valuation/data/opencode/state/opencode/opencode.db'
con=sqlite3.connect('file:'+DB+'?mode=ro',uri=True); con.row_factory=sqlite3.Row
out=io.open('tools/main_msgs_by_day.txt','w',encoding='utf-8')
main='ses_abc2242e4d904322ab3222a8750b5d57'
c=collections.defaultdict(collections.Counter)
for r in con.execute("select type,time_created from session_message where session_id=? order by time_created",(main,)):
    day=datetime.datetime.fromtimestamp(r['time_created']/1000,datetime.UTC).strftime('%Y-%m-%d')
    c[day][r['type']]+=1
for d in sorted(c): out.write(d+' '+repr(dict(c[d]))+'\n')
out.write('\nparents:\n')
for r in con.execute("select agent,count(*) n,min(time_created),max(time_created) from session_v2 group by agent"):
    out.write(repr(dict(r))+'\n')
out.write('\nparent ids:\n')
for r in con.execute("select parent_id,count(*) n from session_v2 group by parent_id"):
    out.write(repr(dict(r))+'\n')
out.close()
print(open('tools/main_msgs_by_day.txt',encoding='utf-8').read())
