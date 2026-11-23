import sys, os, inspect, importlib
sys.path.insert(0, r"C:\modex-mh-agent\resources\app"); sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
mod=importlib.import_module("backend.services.step_review_report")
for n in dir(mod):
    if n.startswith("__"): continue
    v=getattr(mod,n)
    if callable(v):
        print(n, type(v), getattr(v,"__module__",None), getattr(v,"__doc__",None))
