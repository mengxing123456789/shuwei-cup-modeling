import sys, json, inspect, os
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
import importlib
m = importlib.import_module("backend.services.workflow_engine")
out = {}
for name in ["WorkflowStatus","StepStatus","TemplateType","StepDef","TemplateDef","CheckIssue","PaperSubmissionContractReport","ModelingQualityReport"]:
    obj = getattr(m, name, None)
    if obj is None: out[name] = "MISSING"; continue
    try:
        if hasattr(obj, "__members__"):
            out[name] = {"kind":"enum","members":{k:str(v.value) for k,v in obj.__members__.items()}}
        elif hasattr(obj, "__dataclass_fields__"):
            out[name] = {"kind":"dataclass","fields":{k:str(v.type) for k,v in obj.__dataclass_fields__.items()}}
        else:
            out[name] = {"kind":type(obj).__name__, "repr":repr(obj)[:500]}
    except Exception as e:
        out[name] = "ERR "+repr(e)
# all caps constants not already captured
consts = {}
for k,v in vars(m).items():
    if k.isupper() and not k.startswith("_") and isinstance(v,(str,int,float,bool,tuple,frozenset)):
        consts[k]=repr(v)[:400]
out["PUBLIC_CONSTS"]=consts
print(json.dumps(out, ensure_ascii=False, indent=1))
