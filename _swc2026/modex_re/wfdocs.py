import sys, os, json
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
import importlib, inspect
m = importlib.import_module("backend.routers.workflows")
want = ["start","pause","resume","submit_checkpoint","restart","rerun_step","create","get_one"]
for n in want:
    f=getattr(m,n,None)
    print("="*8,n, inspect.signature(f) if f else None)
    print((inspect.getdoc(f) or "")[:1200])
