import sqlite3, json
p=r"C:\Users\29900\AppData\Roaming\ModexData\library-sTDDnH\db\aris.db"
con=sqlite3.connect(p); con.row_factory=sqlite3.Row
for t in ["workflows","workflow_steps","checkpoints","workflow_logs"]:
    row=con.execute("select sql from sqlite_master where type='table' and name=?",(t,)).fetchone()
    print("="*20,t); print(row["sql"] if row else "MISSING")
print("="*20,"ALL TABLES")
for r in con.execute("select name from sqlite_master where type='table' order by name"): print(r[0])
