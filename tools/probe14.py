import sqlite3, json, io
con=sqlite3.connect('file:C:/path/to/valuation/data/valuation.db?mode=ro',uri=True); con.row_factory=sqlite3.Row
out=io.open('tools/jobs_detail.txt','w',encoding='utf-8')
for r in con.execute("select id,product_id,status,created_at,updated_at,rounds,restarts,recoveries,error,summary,child_session,review_session from jobs order by id"):
    d=dict(r)
    out.write(json.dumps(d,ensure_ascii=False)[:1500]+'\n')
out.close()
print(open('tools/jobs_detail.txt',encoding='utf-8').read()[:12000])
