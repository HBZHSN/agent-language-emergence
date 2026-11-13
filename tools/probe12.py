import sqlite3, json
con=sqlite3.connect('file:C:/path/to/valuation/data/opencode/state/opencode/opencode.db?mode=ro',uri=True); con.row_factory=sqlite3.Row
r=con.execute("select * from session_v2 where id='ses_abc2242e4d904322ab3222a8750b5d57'").fetchone()
print(json.dumps(dict(r),ensure_ascii=False,indent=1))
print(tuple(con.execute("select min(seq),max(seq),min(time_created),max(time_created) from session_message where session_id='ses_abc2242e4d904322ab3222a8750b5d57'").fetchone()))
print('compactions:')
for r in con.execute("select seq,time_created,substr(data,1,500) from session_message where session_id='ses_abc2242e4d904322ab3222a8750b5d57' and type='compaction' order by seq limit 3"):
    print(tuple(r))
