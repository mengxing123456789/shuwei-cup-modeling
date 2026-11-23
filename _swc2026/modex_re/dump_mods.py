# -*- coding: utf-8 -*-
import sys, os, json, inspect, types
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
import importlib
mods=["step_review_report","submission_review","writing_review","quality_receipts","paper_submission_contract","checkpoint_runtime","artifact_graph","artifact_catalogue","artifact_bundle","artifact_display","artifact_patch","public_artifact_access"]
for m in mods:
    try:
        mod=importlib.import_module("backend.services."+m)
    except Exception as e:
        print(m,"IMPORT_ERR",e); continue
    lines=[f"MODULE backend.services.{m}", "DOC: "+(inspect.getdoc(mod) or "")]
    consts=[]
    funcs=[]
    for n in dir(mod):
        if n.startswith("__"): continue
        v=getattr(mod,n)
        if inspect.isfunction(v) or inspect.isclass(v):
            try: sig=str(inspect.signature(v))
            except Exception: sig="(?)"
            funcs.append(f"{n}{sig} :: "+(inspect.getdoc(v) or "").replace("\n"," | "))
        elif isinstance(v,(str,int,float,bool,tuple,list,dict,frozenset,set)) and n.isupper():
            consts.append(f"{n} [{type(v).__name__}] = {v!r}")
    lines.append("CONSTANTS:\n"+"\n".join(consts))
    lines.append("CALLABLES:\n"+"\n".join(funcs))
    open(rf"E:\数学建模\_swc2026\modex_re\api_{m}.txt","w",encoding="utf-8").write("\n".join(lines))
    print(m,"ok",len(consts),len(funcs))
