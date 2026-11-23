# -*- coding: utf-8 -*-
"""Dump all workflow-related rows from aris.db as JSON."""
import sqlite3, json

DB = r"C:\Users\29900\AppData\Roaming\ModexData\library-sTDDnH\db\aris.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

out = {}
for t in ["workflows", "workflow_steps", "workflow_logs", "checkpoints", "settings", "conversation_drafts", "model_presets"]:
    rows = [dict(r) for r in cur.execute(f'SELECT * FROM "{t}"')]
    out[t] = rows

with open(r"E:\数学建模\_swc2026\modex_re\db_dump.json", "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=2, default=str))
