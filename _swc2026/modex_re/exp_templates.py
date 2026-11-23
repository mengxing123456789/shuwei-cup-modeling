# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
import backend.services.workflow_engine as we
out={}
t=we.TEMPLATES
out["template_keys"]=list(t.keys())
c=t.get("comp_shuwei")
def dump_step(s):
    d={}
    for f in ["skill_name","display_name","output_files","primary_output","has_checkpoint","checkpoint_type"]:
        try: d[f]=getattr(s,f)
        except Exception as e: d[f]="ERR "+repr(e)
    return d
out["comp_shuwei"]={}
for f in ["pipeline_skill","display_name"]:
    try: out["comp_shuwei"][f]=getattr(c,f)
    except Exception as e: out["comp_shuwei"][f]="ERR"
out["comp_shuwei"]["sub_steps"]=[dump_step(s) for s in c.sub_steps]
out["comp_shuwei"]["legacy_steps"]=[dump_step(s) for s in getattr(c,"legacy_steps",[])]
open(r"E:\数学建模\_swc2026\modex_re\exp_templates.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=1,default=str))
print(json.dumps(out,ensure_ascii=False,indent=1,default=str)[:4000])
