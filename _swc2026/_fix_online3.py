import py_compile

dst = r"E:\数学建模\_swc2026\SWC2026_C\code\p3_online_alpha2.py"
t = open(dst, encoding="utf-8").read()

old = """        OBS.append((j.d,p))
        if len(OBS)>=2:
            import numpy as _np
            dd=_np.array([o[0] for o in OBS]); pp=_np.array([o[1] for o in OBS])
            if dd.std()>1e-9:
                A_=float(_np.cov(dd,pp,bias=True)[0,1]/dd.var()); B_=float(pp.mean()-A_*dd.mean())
                EA[0]=min(max(A_,.3),2.0); EB[0]=min(max(B_,-1.),3.)"""
new = """        OBS.append((j.d,p))
        if ("online" in policy) and len(OBS)>=2:
            import numpy as _np
            dd=_np.array([o[0] for o in OBS]); pp=_np.array([o[1] for o in OBS])
            if dd.std()>1e-9:
                A_=float(_np.cov(dd,pp,bias=True)[0,1]/dd.var()); B_=float(pp.mean()-A_*dd.mean())
                EA[0]=min(max(A_,.3),2.0); EB[0]=min(max(B_,-1.),3.)"""
assert old in t
t = t.replace(old, new, 1)
open(dst, "w", encoding="utf-8", newline="\n").write(t)
py_compile.compile(dst, doraise=True)
print("gated on policy; compile ok")