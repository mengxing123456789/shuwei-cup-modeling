# -*- coding: utf-8 -*-
import sys, os, json, shutil
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
from pathlib import Path
import backend.services.workflow_engine as we
ws=Path(r"E:\数学建模\_swc2026\modex_re\exp_health2")
if ws.exists(): shutil.rmtree(ws)
ws.mkdir(parents=True)
rows=[]
for s in ["comp-prob-analysis","comp-modeling","comp-code","comp-paper-zh","comp-compile-zh"]:
    for target in [500,1200,1800,2500,3500]:
        txt=("本文针对问题建立模型并给出求解结果与检验。"*300)
        fn=ws/f"{s}_{target}.md"; fn.write_text(txt,encoding="utf-8")
        n=len(txt.encode("utf-8"))
        try: r=we._primary_output_health(ws,s,fn.name)
        except Exception as e: r=("EXC",repr(e))
        rows.append({"skill":s,"target":target,"actual":n,"result":[str(x) for x in r]})
open(r"E:\数学建模\_swc2026\modex_re\exp_health2.json","w",encoding="utf-8").write(json.dumps(rows,ensure_ascii=False,indent=1))
print("done")
