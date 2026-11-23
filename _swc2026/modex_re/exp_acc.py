# -*- coding: utf-8 -*-
import sys, os, json, shutil
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
from pathlib import Path
from backend.services import workflow_acceptance as wa
ws = Path(r"E:\数学建模\_swc2026\modex_re\exp_acc")
if ws.exists(): shutil.rmtree(ws)
ws.mkdir(parents=True)
samples = {
 "empty.md": "",
 "heading.md": "# 标题\n\n## 一、问题重述\n",
 "todo.md": "# 标题\n\nTODO\n待补充\n",
 "prose.md": "本文针对问题一建立了线性规划模型。目标函数为总成本最小，约束包括产能约束、库存约束与非负约束。采用单纯形法求解，得到最优解为 123.45，并进行了灵敏度分析。\n"*8,
 "json.json": '{"a":1}',
}
for n,c in samples.items():
    (ws/n).write_text(c, encoding="utf-8")
cases=[]
for skill in ["comp-prob-analysis","comp-modeling","comp-code","comp-paper-zh","comp-compile-zh","paper-figure"]:
    for n in ["empty.md","heading.md","todo.md","prose.md","missing.md"]:
        try:
            r = wa.core_file_problem(ws, skill, ws/n)
            cases.append({"skill":skill,"file":n,"result":r})
        except Exception as e:
            cases.append({"skill":skill,"file":n,"exc":repr(e)})
lcases=[]
for n in ["empty.md","heading.md","todo.md","prose.md"]:
    lcases.append({"file":n,"has_report_content":wa.has_report_content((ws/n).read_text(encoding="utf-8"))})
# unfinished sections experiment
paper = ws/"paper"; (paper/"sections").mkdir(parents=True)
(paper/"main.tex").write_text("\\documentclass{article}\n\\begin{document}\n\\input{sections/s1}\n\\end{document}\n",encoding="utf-8")
(paper/"sections"/"s1.tex").write_text("\\section{问题一}\n\n\\subsection{模型建立}\n\n",encoding="utf-8")
try: unc = wa.unfinished_sections(ws)
except Exception as e: unc = "EXC "+repr(e)
out={"core_file_problem":cases,"has_report_content":lcases,"unfinished_sections":unc,
     "stats_workspace":wa.is_stats_workspace(ws)}
open(r"E:\数学建模\_swc2026\modex_re\exp_acc_result.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=1))
print("done")
