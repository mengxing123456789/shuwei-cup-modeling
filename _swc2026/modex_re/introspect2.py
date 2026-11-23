# -*- coding: utf-8 -*-
"""Import compiled backend modules (backend root on sys.path) and dump API surface."""
import sys, os, json, inspect, traceback

APP = r"C:\modex-mh-agent\resources\app"
BACKEND = os.path.join(APP, "backend")
sys.path.insert(0, APP)
sys.path.insert(0, BACKEND)
os.chdir(APP)

mods = sys.argv[1:]

def describe(name):
    out = {"module": name}
    try:
        m = __import__(name, fromlist=['*'])
        out["ok"] = True
        out["file"] = getattr(m, "__file__", None)
        out["doc"] = getattr(m, "__doc__", None)
        items = []
        for attr in sorted(dir(m)):
            if attr.startswith('__'): continue
            try: v = getattr(m, attr)
            except Exception: continue
            d = {"name": attr, "type": type(v).__name__}
            if callable(v):
                try: d["doc"] = inspect.getdoc(v)
                except Exception: pass
                try: d["sig"] = str(inspect.signature(v))
                except Exception: pass
                try: d["defaults"] = repr(getattr(v, '__defaults__', None))
                except Exception: pass
                try: d["module_of"] = getattr(v, '__module__', None)
                except Exception: pass
            elif isinstance(v, (str, int, float, bool, list, tuple, dict, frozenset)):
                d["value"] = repr(v)[:3000]
            items.append(d)
        out["attrs"] = items
    except Exception:
        out["ok"] = False
        out["error"] = traceback.format_exc()
    return out

res = [describe(m) for m in mods]
outp = os.environ.get("INTROSPECT_OUT", r"E:\数学建模\_swc2026\modex_re\introspect2.json")
with open(outp, "w", encoding="utf-8", newline="\n") as f:
    json.dump(res, f, ensure_ascii=False, indent=1, default=str)
for r in res:
    print(r["module"], "OK" if r.get("ok") else "FAIL", len(r.get("attrs", [])))
    if not r.get("ok"): print(r["error"].strip().splitlines()[-1])
