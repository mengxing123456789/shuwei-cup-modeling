# -*- coding: utf-8 -*-
import sys, os, json, time, shutil
sys.path.insert(0, r"C:\modex-mh-agent\resources\app"); sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
from pathlib import Path
import backend.services.workflow_engine as we
ws=Path(r"E:\数学建模\_swc2026\modex_re\exp_receipt")
if ws.exists(): shutil.rmtree(ws)
(ws/"code").mkdir(parents=True)
(ws/"RESULTS.md").write_text("结果"*1000,encoding="utf-8")
(ws/"code"/"main.py").write_text("print(1)\n"*100,encoding="utf-8")
started=time.time()-60
r=we._main_output_receipt("comp-code","RESULTS.md",["RESULTS.md"],["code/main.py"],started)
print("RECEIPT",r)
try:
    u=we._usable_main_output_receipt(r,ws,"comp-code","RESULTS.md",[])
    print("USABLE",json.dumps(u,ensure_ascii=False))
except Exception as e: print("USABLE_ERR",repr(e))
# tamper: modify primary
(ws/"RESULTS.md").write_text("改过"*10,encoding="utf-8")
try:
    u2=we._usable_main_output_receipt(r,ws,"comp-code","RESULTS.md",[])
    print("USABLE_AFTER_EDIT",json.dumps(u2,ensure_ascii=False))
except Exception as e: print("USABLE2_ERR",repr(e))
open(r"E:\数学建模\_swc2026\modex_re\exp_receipt_result.json","w",encoding="utf-8").write(json.dumps({"receipt":r,"usable":u if 'u' in dir() else None},ensure_ascii=False,indent=1))
