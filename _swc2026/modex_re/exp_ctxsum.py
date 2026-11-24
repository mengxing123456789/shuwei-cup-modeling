# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, r"C:\modex-mh-agent\resources\app"); sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
from pathlib import Path
import backend.services.workflow_engine as we
ws=Path(r"E:\数学建模\_swc2026\modex_re\exp_claude")
files=["PROBLEM_ANALYSIS.md","MODELING_REPORT.md","RESULTS.md","paper/main.tex"]
try:
    s=we._build_context_summary(ws, files, 3000)
    open(r"E:\数学建模\_swc2026\modex_re\exp_context_summary.txt","w",encoding="utf-8").write(s)
    print("len",len(s))
except Exception as e: print("ERR",repr(e))
# also test _plan_has_no_data_work
print("no_data",we._plan_has_no_data_work(ws))
