# -*- coding: utf-8 -*-
import sys, os, shutil, json
sys.path.insert(0, r"C:\modex-mh-agent\resources\app"); sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
from pathlib import Path
import backend.services.workflow_engine as we
ws=Path(r"E:\数学建模\_swc2026\modex_re\exp_claude")
if ws.exists(): shutil.rmtree(ws)
(ws/"user_data").mkdir(parents=True)
(ws/"figures").mkdir()
(ws/"paper").mkdir()
(ws/"PROBLEM_ANALYSIS.md").write_text("# 赛题分析\n\n本题要求建立优化模型。\n"*20,encoding="utf-8")
(ws/"MODELING_REPORT.md").write_text("# 建模报告\n\n目标函数与约束条件如下。\n"*20,encoding="utf-8")
(ws/"RESULTS.md").write_text("# 结果\n\n最优值为 42。\n"*20,encoding="utf-8")
(ws/"paper"/"main.tex").write_text("\\documentclass{article}\\begin{document}论文\\end{document}\n",encoding="utf-8")
(ws/"figures"/"fig_cost.pdf").write_bytes(b"%PDF-1.4 fake")
(ws/"user_data"/"data.csv").write_text("x,y\n1,2\n",encoding="utf-8")
try:
    r=we._generate_claude_md(ws,"RE-探针","comp_shuwei",{"language":"zh"})
    print("ret",r)
except Exception as e:
    print("ERR",type(e).__name__,e)
p=ws/"CLAUDE.md"
print("exists",p.exists(),"bytes",p.stat().st_size if p.exists() else 0)
if p.exists(): open(r"E:\数学建模\_swc2026\modex_re\exp_claude_md.txt","w",encoding="utf-8").write(p.read_text(encoding="utf-8"))
