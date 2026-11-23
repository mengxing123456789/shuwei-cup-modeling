# -*- coding: utf-8 -*-
"""Probe which numerical routines are usable in this environment (argv[1] picks the test)."""
import sys
import numpy as np

test = sys.argv[1]
rng = np.random.default_rng(0)
if test == "dot":
    a = rng.normal(size=17085); b = rng.normal(size=17085)
    print(float(a @ b))
elif test == "matmul":
    A = rng.normal(size=(200, 300)); B = rng.normal(size=(300, 40))
    print(float((A @ B).sum()))
elif test == "svd":
    A = rng.normal(size=(200, 300))
    print(np.linalg.svd(A, full_matrices=False)[1][:3])
elif test == "lstsq":
    A = rng.normal(size=(500, 5)); y = rng.normal(size=500)
    print(np.linalg.lstsq(A, y, rcond=None)[0][:2])
elif test == "polyfit":
    x = np.linspace(0, 10, 500); y = 2 * x + rng.normal(size=500)
    print(np.polyfit(x, y, 1))
elif test == "linregress":
    from scipy import stats
    x = np.linspace(0, 10, 500); y = 2 * x + rng.normal(size=500)
    r = stats.linregress(x, y)
    print(r.slope, r.rvalue, r.pvalue)
elif test == "pearsonr":
    from scipy import stats
    x = rng.normal(size=17085); y = rng.normal(size=17085)
    print(stats.pearsonr(x, y)[0])
elif test == "spearman":
    from scipy import stats
    x = rng.normal(size=17085); y = rng.normal(size=17085)
    print(stats.spearmanr(x, y)[0])
elif test == "sk_tree":
    from sklearn.tree import DecisionTreeRegressor
    X = rng.normal(size=(2000, 4)); y = X[:, 0] * 2 + X[:, 1]
    m = DecisionTreeRegressor(max_depth=4, random_state=0).fit(X, y)
    print(m.predict(X[:3]))
elif test == "sk_forest":
    from sklearn.ensemble import RandomForestRegressor
    X = rng.normal(size=(2000, 4)); y = X[:, 0] * 2 + X[:, 1]
    m = RandomForestRegressor(n_estimators=20, max_depth=4, random_state=0, n_jobs=1).fit(X, y)
    print(m.predict(X[:3]))
elif test == "sk_gbr":
    from sklearn.ensemble import GradientBoostingRegressor
    X = rng.normal(size=(2000, 4)); y = X[:, 0] * 2 + X[:, 1]
    m = GradientBoostingRegressor(n_estimators=50, max_depth=2, random_state=0).fit(X, y)
    print(m.predict(X[:3]))
elif test == "sk_linear":
    from sklearn.linear_model import LinearRegression
    X = rng.normal(size=(500, 5)); y = rng.normal(size=500)
    print(LinearRegression().fit(X, y).coef_[:2])
elif test == "sm_ols":
    import statsmodels.api as sm
    X = rng.normal(size=(500, 5)); y = rng.normal(size=500)
    r = sm.OLS(y, sm.add_constant(X)).fit()
    print(r.params[:2])
elif test == "scipy_fit":
    from scipy import stats
    x = stats.genextreme.rvs(0.1, loc=100, scale=20, size=60, random_state=rng)
    print(stats.genextreme.fit(x))
else:
    raise SystemExit(f"unknown test {test}")