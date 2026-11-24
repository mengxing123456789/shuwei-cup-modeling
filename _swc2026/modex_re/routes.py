import sys, os, json
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
import importlib
mods = ["backend.routers.checkpoints","backend.routers.artifact_context","backend.routers.workflows"]
for mn in mods:
    m = importlib.import_module(mn)
    print("="*10, mn, "prefix=", getattr(m.router,'prefix',''))
    for r in m.router.routes:
        print(f"{','.join(sorted(getattr(r,'methods',[]) or [])):22s} {getattr(r,'path','')}  -> {getattr(r,'name','')}")
