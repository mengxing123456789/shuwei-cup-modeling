# -*- coding: utf-8 -*-
import sys, os, json, shutil
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
from pathlib import Path
import backend.services.workflow_engine as we
skills=["comp-prob-analysis","comp-modeling","comp-code","paper-figure","paper-figure-html","comp-paper-zh","comp-compile-zh"]
res={"min_size":{},"companions":{},"upstream":{}}
for s in skills:
    try: res["min_size"][s]=we._min_size_for(s,None)
    except Exception as e: res["min_size"][s]="EXC "+repr(e)
    try: res["companions"][s]=we._required_companions_for(s,None)
    except Exception as e: res["companions"][s]="EXC "+repr(e)
    try: res["upstream"][s]=we._upstream_deps_for("comp_shuwei",s)
    except Exception as e: res["upstream"][s]="EXC "+repr(e)
ws=Path(r"E:\数学建模\_swc2026\modex_re\exp_health")
if ws.exists(): shutil.rmtree(ws)
ws.mkdir(parents=True)
# health cases per skill with sizes
cases=[]
for s,size in [("comp-prob-analysis",800),("comp-prob-analysis",1600),("comp-modeling",2100),("comp-code",1200),("comp-paper-zh",9000),("comp-paper-zh",11000),("comp-compile-zh",31000)]:
    fn=ws/(s+"_"+str(size)+".md")
    fn.write_text("真实内容。"*(size//15+1),encoding="utf-8")
    # force exact bytes
    data=("真实内容。"*(size//15+1)).encode("utf-8")[:size]
    fn.write_bytes(data)
    try: r=we._primary_output_health(ws,s,fn.name)
    except Exception as e: r="EXC "+repr(e)
    cases.append({"skill":s,"bytes":size,"file":fn.name,"result":[str(x) for x in (r if isinstance(r,tuple) else [r])]})
res["health"]=cases
# figure manifest experiment
mf=ws/"PROBLEM_ANALYSIS.md"
mf.write_text("""# 分析
<!-- BEGIN FIGURE_MANIFEST -->
## 数据图
- fig_cost
- fig_sensitivity
## 流程图
- fig_arch
- fig_flow
## TikZ 图
- fig_model_decision
<!-- END FIGURE_MANIFEST -->
""",encoding="utf-8")
try:
    a,b=we._read_figure_manifest(ws); res["figure_manifest"]={"data":a,"drawio":b}
except Exception as e: res["figure_manifest"]="EXC "+repr(e)
open(r"E:\数学建模\_swc2026\modex_re\exp_health_result.json","w",encoding="utf-8").write(json.dumps(res,ensure_ascii=False,indent=1))
print("done")
