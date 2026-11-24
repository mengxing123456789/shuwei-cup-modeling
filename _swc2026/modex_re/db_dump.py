# -*- coding: utf-8 -*-
"""Dump aris.db schema and workflow-related rows for Modex RE."""
import sqlite3, json, sys, os

DB = r"C:\Users\29900\AppData\Roaming\ModexData\library-sTDDnH\db\aris.db"

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    print("TABLES:", len(tables))
    for t in tables:
        try:
            n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except Exception as e:
            n = f"ERR {e}"
        print(f"  {t}: {n}")

if __name__ == "__main__":
    main()
