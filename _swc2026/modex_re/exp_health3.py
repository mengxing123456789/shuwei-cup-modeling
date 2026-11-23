# -*- coding: utf-8 -*-
import sys, os, json, shutil
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
from pathlib import Path
import backend.services.workflow_engine as we
ws=Path(r"E:\数学建模\_swc2026\modex_re\exp_health3")
if ws.exists(): shutil.rmtree(ws)
ws.mkdir(parents=True)
rows=[]
for s, sizes in {"comp-prob-analysis":[100,400,1000,1600],"comp-modeling":[600,1500,2100],"comp-code":[300,1100],"comp-paper-zh":[3000,10500],"comp-compile-zh":[5000,31000]}.items():
    for target in sizes:
        txt="本文建立模型并求解，给出结果与检验。"*max(1,target//18)
        fn=ws/f"{s}_{target}.md"; fn.write_text(txt,encoding="utf-8")
        n=len(txt.encode("utf-8"))
        try: r=we._primary_output_health(ws,s,fn.name)
        except Exception as e: r=("EXC",repr(e))
        rows.append({"skill":s,"target":target,"actual":n,"result":[str(x) for x in r]})
open(r"E:\数学建模\_swc2026\modex_re\exp_health3.json","w",encoding="utf-8").write(json.dumps(rows,ensure_ascii=False,indent=1))
print("done")
