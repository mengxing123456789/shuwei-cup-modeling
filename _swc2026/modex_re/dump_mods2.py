# -*- coding: utf-8 -*-
import sys, os, inspect, importlib
sys.path.insert(0, r"C:\modex-mh-agent\resources\app"); sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
mods=["step_review_report","submission_review","writing_review","quality_receipts","paper_submission_contract","checkpoint_runtime","artifact_graph","artifact_catalogue","artifact_bundle","artifact_display","artifact_patch","public_artifact_access","precompile_guard"]
for m in mods:
    try: mod=importlib.import_module("backend.services."+m)
    except Exception as e:
        print(m,"ERR",e); continue
    lines=[f"MODULE backend.services.{m}","DOC: "+(inspect.getdoc(mod) or ""),"CALLABLES:"]
    for n in dir(mod):
        if n.startswith("__"): continue
        v=getattr(mod,n)
        if callable(v) and not inspect.isclass(v) and getattr(v,"__module__",None)==mod.__name__:
            try: sig=str(inspect.signature(v))
            except Exception: sig="(?)"
            lines.append(f"{n}{sig} :: "+(inspect.getdoc(v) or "").replace("\n"," | "))
    open(rf"E:\数学建模\_swc2026\modex_re\api2_{m}.txt","w",encoding="utf-8").write("\n".join(lines))
    print(m, len(lines)-3)
