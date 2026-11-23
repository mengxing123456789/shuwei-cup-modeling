import py_compile

dst = r"E:\数学建模\_swc2026\SWC2026_C\code\p1b_calib.py"
t = open(dst, encoding="utf-8").read()

old_tail = '''    print("CALIB",json.dumps(calib,ensure_ascii=False))'''
new_tail = '''    # Platt scaling (a,b) on validation: fixes both slope and intercept
    from scipy.optimize import minimize as _min
    def _platt_nll(w):
        a,b=w
        q=1/(1+np.exp(-(a*_logit(pv)+b)))
        return -np.mean(yva*np.log(q+1e-12)+(1-yva)*np.log(1-q+1e-12))
    r2=_min(_platt_nll,x0=np.array([1.0,0.0]),method="Nelder-Mead")
    a_pl,b_pl=float(r2.x[0]),float(r2.x[1])
    ppl=1/(1+np.exp(-(a_pl*_logit(pt)+b_pl)))
    const=float(yte.mean())
    calib.update(platt_a=a_pl,platt_b=b_pl,
                 platt_val_nll=float(r2.fun),
                 brier_platt=float(np.mean((ppl-yte)**2)),
                 ece15_platt=_ece(ppl,yte),
                 mean_prob_platt=float(ppl.mean()),
                 brier_constant=float(np.mean((const-yte)**2)),
                 brier_constant_baserate=const)
    print("CALIB",json.dumps(calib,ensure_ascii=False))'''

assert old_tail in t
t = t.replace(old_tail, new_tail, 1)
t = t.replace('np.savez(os.path.join(DATA,"p1b_probs.npz"),pt=pt,pcal=pcal,yte=yte,env=Ete)',
              'np.savez(os.path.join(DATA,"p1b_probs.npz"),pt=pt,pcal=pcal,ppl=ppl,yte=yte,env=Ete)', 1)
open(dst, "w", encoding="utf-8", newline="\n").write(t)
py_compile.compile(dst, doraise=True)
print("platt added, compile ok")