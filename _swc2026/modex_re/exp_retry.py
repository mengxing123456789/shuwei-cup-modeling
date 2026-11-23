# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
import backend.services.workflow_engine as we
cands = [
 ("none", None),
 ("empty", {}),
 ("kind_transient", {"kind":"transient_provider"}),
 ("error_kind_transient", {"error_kind":"transient_provider"}),
 ("type_transient", {"type":"transient_provider"}),
 ("status_failed", {"status":"failed"}),
 ("ok_false", {"ok":False}),
 ("error_str", {"error":"connection reset"}),
 ("incomplete_tool_calls", {"incomplete_tool_calls":True}),
 ("failed_background_tasks", {"failed_background_tasks":True}),
 ("incomplete_followup", {"incomplete_followup":True}),
 ("incomplete_background_tasks", {"incomplete_background_tasks":True}),
 ("bun_panic", {"bun_panic":True}),
 ("empty_tool", {"empty_tool":True}),
 ("inactivity", {"inactivity":True}),
 ("timed_out", {"timed_out":True}),
 ("error_code_transient", {"error_code":"TRANSIENT_PROVIDER"}),
 ("reason_transient", {"reason":"transient_provider"}),
]
out=[]
for n,d in cands:
    try: r=we._process_retry_policy(d)
    except Exception as e: r=("EXC",repr(e))
    out.append({"case":n,"input":d,"output":[str(x) for x in (r if isinstance(r,tuple) else [r])]})
open(r"E:\数学建模\_swc2026\modex_re\exp_retry.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=1))
print(json.dumps(out,ensure_ascii=False,indent=1))
