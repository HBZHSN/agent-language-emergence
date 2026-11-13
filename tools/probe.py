import sqlite3
import sys

def main():
    db = sys.argv[1]
    con = sqlite3.connect('file:' + db + '?mode=ro', uri=True)
    for name, sql in con.execute("select name, sql from sqlite_master where type='table' order by name"):
        try:
            n = con.execute('select count(*) from "%s"' % name).fetchone()[0]
        except Exception as exc:
            n = 'ERR ' + str(exc)
        print('TABLE', name, n)
        print(sql)
        print()

if __name__ == '__main__':
    main()
