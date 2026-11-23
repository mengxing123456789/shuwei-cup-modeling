import sqlite3, io
p=r"C:\Users\29900\AppData\Roaming\ModexData\library-sTDDnH\db\aris.db"
con=sqlite3.connect(p)
out=[]
for t in ["workflows","workflow_steps","checkpoints","workflow_logs"]:
    row=con.execute("select sql from sqlite_master where type='table' and name=?",(t,)).fetchone()
    out.append("="*20+" "+t+"\n"+(row[0] if row else "MISSING"))
open(r"E:\数学建模\_swc2026\modex_re\schema_ddl.txt","w",encoding="utf-8").write("\n\n".join(out))
print("ok")
