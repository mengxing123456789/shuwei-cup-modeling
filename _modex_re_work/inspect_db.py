# -*- coding: utf-8 -*-
import sqlite3, os, io
p = os.path.expandvars(r'%APPDATA%\ModexData\library-sTDDnH\db\aris.db')
con = sqlite3.connect('file:' + p + '?mode=ro', uri=True)
cur = con.cursor()
out = io.open(r'E:\数学建模\_modex_re_work\aris_db_schema.txt', 'w', encoding='utf-8')
for (name, sql) in cur.execute("select name, sql from sqlite_master where type='table' order by name"):
    out.write('TABLE ' + name + '\n  ' + (sql or '').replace('\n',' ') + '\n')
out.write('--- counts ---\n')
for (name,) in cur.execute("select name from sqlite_master where type='table' order by name"):
    try:
        n = cur.execute(f'select count(*) from "{name}"').fetchone()[0]
        out.write(f'{name} {n}\n')
    except Exception as e:
        out.write(f'{name} ERR {e}\n')
out.close()
print('ok')
