# APMCM2025_C 建模与数据审计：P-M 坑清单（实测版）

> 范围：`E:\数学建模\APMCM2025_C`（论文 `main.tex` + `code/q1..q5` + `data/results_*.json`）。
> 纪律：**所有"定量后果"栏里的数字都是我在本机跑出来的**（脚本名逐条给出，均在 `E:\数学建模\.tmp_scratch\`），
> 引自 review/论文原文的数字一律标 `（引自 …）`。每条末尾给 `实测：pass/fail` 的含义见文末「判定口径」。
> 环境：`D:\Python\python.exe`（numpy 2.5.1 / pandas 3.0.5 / scipy 1.18.1 / statsmodels 0.15.0，无 torch）。
> 生成时间：2026-11-11。

---

## 判定口径

- `pass` = 该坑**在本项目里真实发生**，且我复现出了具体数字/错值；
- `fail` = 该坑**在本项目里不发生**（命题为假、已被作者修掉、或在本数据上无触发条件），我给出了为什么；
- `pass(局部)` = 机制真实存在但触发条件未在本数据满足，风险仍在（量纲/参数区间层面）。

---

## P-M01 熵权法与 TOPSIS 的归一化口径必须一致（不是"必须 min-max"）

**现象/触发**：`code/q5_macro.py::entropy_topsis` L145–163 两步都用 min-max（`z=(col-col.min())/rng`，反向 `1-z`），
TOPSIS 的理想解 `best=V.max(axis=0)` 也取自 min-max 后的 `V`。文献里的标准写法是熵权与 TOPSIS 都用**向量归一**
`x/sqrt(sum x^2)`。用户清单的断言是「熵权必须 min-max、TOPSIS 必须向量归一，混用会毁指标（权重差 1206 倍）」。

**定量后果**（`p01_entropy_topsis.py`）：
- as_shipped 权重复现 `[0.227087, 0.193402, 0.130817, 0.127794, 0.166919, 0.153982]`，与 `data/results_q5.json`
  的 `reshoring_index.weights` **完全一致** → 代码 = 论文，没有两套数。
- textbook（向量归一 + 向量归一）权重 `[0.263125, 0.103121, 0.144753, 0.281015, 0.198561, 0.009425]`；
  两套口径的权重比 `[0.863, 1.8755, 0.9037, 0.4548, 0.8406, 16.337]` → **最大 16.337 倍**，不是 1206 倍。
- 排名翻转：shipped `Soybeans, Autos, Mid/low chips, …`；textbook `Mid/low chips, Autos, Soybeans, …` → **首位互换**。
- 列单调重标定（第 5 列 `×100+500`）：**min-max 权重变化 0.0**；**向量归一权重变化 max|Δw| = 0.1555**。
  → 论文正文（`main.tex` offset ~41066）"Entropy weights re-absorb any monotone rescaling of a column" 是**对的**，
  且只对 min-max 成立（或只对任何"按列仿射不变"的口径成立）。
- 加一行异常行业：比值 max 14.42，首位仍翻。

**规定**：**禁止**在同一指数里混用两种归一化口径；归一化口径必须与 TOPSIS 正/负理想解的构造口径一致，
并在方法节写明"某口径 → 对单调重标定不变 / 不变"这一性质。论文若宣称"权重不随计量单位变"，必须同时声明
"排名会对口径敏感"并给出敏感性表。

**检查代码**：
```python
import numpy as np
from itertools import product
def w_minmax(X, benefit):
    Z = X.copy()
    for j in range(X.shape[1]):
        c = X[:, j]; z = (c - c.min()) / np.where(c.ptp() == 0, 1, c.ptp())
        Z[:, j] = z if benefit[j] else 1 - z
    P = (Z + 1e-9) / (Z + 1e-9).sum(0)
    e = -(P * np.log(P)).sum(0) / np.log(len(X)); d = 1 - e
    return d / d.sum()
def w_vec(X, benefit):
    Z = X.copy()
    for j in range(X.shape[1]):
        n = np.linalg.norm(X[:, j]) or 1.0
        z = X[:, j] / n
        Z[:, j] = z if benefit[j] else -z
    P = (np.abs(Z) + 1e-9) / (np.abs(Z) + 1e-9).sum(0)
    e = -(P * np.log(P)).sum(0) / np.log(len(X)); d = 1 - e
    return d / d.sum()
# 红线断言：口径切换后首位若翻转，必须报出；单权重比 > 5 必须报出
```
**实测：pass**（代码 = 论文；口径一换首位翻转、单权重差 16.3 倍）。用户清单里"1206 倍 / 必须 min-max"的说法 **fail**。

---

## P-M01b 价格指数口径（算术 vs CES）会改变最优政策点

**现象/触发**：`code/q3_semiconductors.py::welfare` L85–103 用 `P = x*pD + (1-x)*pI`（算术加权），
而模型的需求侧份额是 CES（`x` 由 `(pD/pD0)^(1-σ)` 决定）。算术价与 CES 价不一致 → CES 份额 + 非 CES 价格 = 内部不一致。

**定量后果**（`p02_ces_price.py`、`p20_q3_mixed_index.py`）：
- 在 shipped 最优点（τ=.16, s=.36, x=.398168）：`P_arith 1.318604` vs `P_ces 1.276457`，gap **−0.042148（−3.20%）**，
  CS 由 **+0.481013** 翻到 **−0.608706**（差 **1.089720 bn**，= 3.24% of V=33.611）。
- 可行箱内最大 gap **0.140192**（τ=.25, s=.50, x=.6345）→ 该点 CS 差 **3.6246 bn**。
- 优化器：算术价最优 (τ.16, s.36, W **1.798766**)（= `results_q3.json`）；换 CES 价最优 (τ**.25**, s**.44**, W **3.744984**)。
- 三个段在 CES 价下 **全部把 τ 推到网格上界 0.25**（high .25/.44/3.745；mid .25/.30/1.405；low .25/.27/3.817）。

**规定**：**禁止**用算术价替代与 CES 份额配套的价格指数；若两侧口径不同，必须在结果表同时给"算术 CS"与"CES CS"
并报告 gap，且禁止用算术口径的最优点当作推荐值。

**检查代码**：
```python
def p_arith(x, pD, pI):  return x*pD + (1-x)*pI
def p_ces(x, pD, pI, s):
    return (x*pD**(1-s) + (1-x)*pI**(1-s))**(1/(1-s))
# 断言：在任一可行 (τ,s) 上 |p_arith - p_ces|/p_ces < 1e-3，否则价格指数与需求口径不配套
```
**实测：pass**。

---

## P-M02 预测年超出观测窗时，冻结 min-max 会把有序信息压成饱和值

**现象/触发**：熵权/TOPSIS 的 `col.min()/col.ptp()` 若只按**观测窗 2015–2024** 计算，再拿去给 2025–2028 打分，
越界值会被截断到 0 或 1。用户清单的断言是"更好的会被打成更差"。

**定量后果**（`p03_frozen_minmax.py`）：
- 成本类指标（越低越好）某年与窗内历史最低持平：frozen 与 extended 都给 1.0（**此例不翻**）。
- 真正的失效模式是越**上界**：raw `[0.5, 8.0, 9.0, 3.0, 7.0, 5.0]` → frozen z `[1.0, **0.0**, **0.0**, 0.6667, 0.0, 0.3333]`
  （**最差与次差同值 0，秩被抹平**）；extended z `[1.0, 0.1176, 0.0, 0.7059, 0.2353, 0.4706]`。
- 越**下界**方向：raw 0.40 的 frozen z=1.0 vs extended 0.6061 → "更好"被压成"最好"，且与其它年份不可比。

**规定**：预测年超出观测区间时，**禁止**沿用观测窗 min/max；必须扩面板（观测+预测）后重算范数/理想解，
并在正文声明"该年份的分数与样本内分数不可直接比较"。

**检查代码**：
```python
lo, hi = X_obs.min(0), X_obs.max(0)
X_all = np.vstack([X_obs, X_fc])
assert (X_all.min(0) == lo).all() and (X_all.max(0) == hi).all(), \
    "预测年越界：必须扩面板重算，或显式声明不可比"
```
**实测：pass（机制）/ fail（"更好变更差"这一措辞）**：翻转方向是"更好被压成最好"（饱和），不是符号反向。

---

## P-M03 加权和 ≠ CES 数量指数：本例 CES 聚合恒等 105.0327

**现象/触发**：`solve_equilibrium` 同时返回 `total_mmt = sum(qty)`（算术和）与内部 CES 聚合；
`eps_d = 0.0` 意味着需求固定在 Q0，求解器把 CES 聚合**钉在 Q0**，于是"总量指数不变"而"算术和随情景变"。

**定量后果**（`p04_ces_index.py`、`p04b_ces_numeraire.py`）：
- 六情景 CES 聚合 = **105.032704**（`U/Q0 = 1.000000000`，到机器精度）；算术和
  105.032704 / 104.427562 / 105.425028 / 105.937877 / 106.509269 / **112.594103**（halt）。
  极差 **7.5614 MMT（+7.20%）**。
- `avg_price` 随情景 502 → 600 USD/t。
- 论文 `tables/tab_q1.tex` 的 `Total` 列正是算术和；正文（`main.tex` ~23000）已显式写
  "The column headed total is the arithmetic sum … it must not be read as … more soybeans being eaten"（引自论文）。
  → **作者已区分，但表头只写 Volume(MMT)，读者仍会误读**。

**规定**：**禁止**用加权和替代 CES 指数报告总量变化；若必须并列，两列分标（`CES index (fixed)` / `arithmetic
sum (substitution)`），单位与口径各自写清，且正文用"substitution, not consumption"限定。

**检查代码**：
```python
rho = (sigma-1)/sigma
U = (sum(alpha[o]*q[o]**rho for o in q))**(1/rho)
assert abs(U/Q0 - 1) < 1e-9, "eps_d=0 时 CES 聚合必须等于 Q0"
assert abs(total_mmt - sum(q.values())) < 1e-9
```
**实测：pass**（两者在本例相差 **7.20%** 且 CES 恒等）。

---

## P-M04 约束的 `binding` 标志：容差是绝对的、量纲耦合，且只检查了"扩容后"的上限

**现象/触发**：`code/q1_soybean.py` L315 `"binding": {o: bool(qty[o] > cap2[o] - 1e-3)}`。`cap2` = 物理出口上限
`cap` **加上 60% diversion 再分配**；`1e-3` 是绝对容差。用户清单断言「99.92% 占用率会被报成 False」。

**定量后果**（`p05c_cap_violation.py`、`p05f_true_cap.py`、`p05g_binding_tol_real.py`）：
- halt 情景 Brazil：`cap2 = 101.0619`（= 91.7656 + 0.70×0.60×14.41774），`q = 100.9825`，
  slack **0.07941**，util **99.9214%** → shipped `binding=False`，**这一条是真的**（99.92% → False）。
- 但把 Brazil 对照**未扩容**的物理上限：`q 100.9825 / cap 91.7656 = **110.0440%**` → 巴西在"自己的出口上限之上 10%"运行，
  系统却报 `False`。**这才是真缺陷：只查 `cap2`，不查 `cap`。**
- 容差扫描（6 情景 × 4 origin）：除 halt/US（`cap=1e-6`、`q=1e-9`，1e-3 绝对容差说 True、1e-6 相对说 False）外，
  **slack 最小 1.538**（τ=.03 halt Argentina，q 5.5491 vs cap 7.0874，util **78.30%**）；tol 从 1e-9 扫到 1.0
  **只翻转 1 对**。→ "1e-3 容差把 99.92% 报成 False"在本数据上**只有 halt/US 一处假阳性**，且是 cap≈1e-6 造成的。
- `cap2` **未随返回值输出**（`p60_math_consistency.py`），复核者无法从返回值重算 flag。

**规定**：①`binding` 必须用**相对容差** `q > cap*(1-1e-6)`，禁止绝对 1e-3；②必须同时对 `cap`（物理上限）和
`cap2`（再分配上限）报告，任一超限都算 bind；③`cap2` 必须随结果返回，使 flag 可复算。

**检查代码**：
```python
binding = {o: bool(q[o] > cap2[o]*(1-1e-6)) for o in q}
over_physical = {o: bool(q[o] > cap[o]*(1-1e-6)) for o in q}
assert not any(over_physical.values()) or any(binding.values()), \
    "在物理上限之上运行却报不 bind"
```
**实测：pass(局部)**：Brazil 99.92%→False 与 110.04%→False 两处都复现；"1e-3 容差扫描会大面积翻转" **fail**。

---

## P-M06 消费者成本用 Laspeyres 还是 Paasche：本例每个正关税都符号翻转

**现象/触发**：`code/q2_autos.py` L156 `pI_new = (pX*qX_base + other_value)/par["M"]` —— `qX_base` 是**基准数量**，
即 Laspeyres。用户清单断言「47% 关税下符号翻转（+2.08 → −6.77 bn）」。

**定量后果**（`p06b_paasche_proper.py`）：
- Laspeyres `(pI_new−pI0)*M0/1000`：τ=10/15/25/47% → **2.6027 / 4.3379 / 7.8082 / 15.4430**（与 `tab_q2.tex` 逐字一致）。
- Paasche `(pI_new*M_new − pI0*M0)/1000`：**−1.5522 / −2.6095 / −4.7735 / −9.7309** → **每个 τ>0 都翻号**（篮子收缩快于涨价）。
- |L/P| = **1.677 / 1.662 / 1.636 / 1.587**；DWL-only（P−L）= −4.155 / −6.948 / −12.582 / −25.174。
- `pI_new/pI0` = 1.01285/1.02142/1.03856/1.07625；`M/M0` = 0.9797/0.9664/0.9402/0.8845。
- 论文正文（~56000）报的是福利口径 L −6.77、P +2.08、倍数 1.54×@15% / 2.53×@47%（引自论文）——**同一事实的另一种切法**。

**规定**：**禁止**在同一福利结论里混用 Laspeyres/Paasche；必须写明"以基准数量加权"，并在正文给出两种口径的
**倍数**与**符号是否一致**；若符号不一致，结论只能表述为"区间跨越零"。

**检查代码**：
```python
L = (pI1 - pI0) * M0 / 1000
P = (pI1*M1 - pI0*M0) / 1000
print(f"{L/V:+.4f} vs {P/V:+.4f}  ratio {L/P:+.3f}  sign_flip={np.sign(L)!=np.sign(P)}")
assert not np.sign(L) != np.sign(P) or "sign flips; report both and the factor" in open(REPORT).read()
```
**实测：pass**。

---

## P-M07 两套进口基数混用会在零政策处造出虚假福利

**现象/触发**：Q2 有 `par["M"] = 7.081579`（六来源合计）与 `import_share*sales_m = 7.686277`（世界口径）两个"进口量"。
在一处恒等式里同时用二者，τ=0 时福利不为零。

**定量后果**（`p07b_bases.py`、`p07c_bases.py`）：
- 两基数差 **−0.604698 百万辆**（`M_world/M6 = 1.085390`）。
- 现行代码已统一到世界口径：τ=0 时 `welfare = **+0.722538**`（不是 0，因为 0.025 基准本身含税）。
- **重造旧 bug**（production leg 用六来源 domestic baseline）：τ=0 welfare = **+2.395497**，虚假增量 **+1.672959 bn**
  = gap × pD × 10%/1000 = −0.604698×27666.02×0.1/1000。margin 取 0.07 → −1.171；取 0.05 → −0.836
  → 论文/代码注释里的 **−1.06 bn** 落在 margin≈0.06（引自 `code/q2_autos.py` L188 注释与 `main.tex` Appendix B）。
- 另一种混法（价格用世界 `pI`、数量用 `M6`）：τ=0 consumer cost = **−14.679456 bn** 的假收益。

**规定**：**同一福利恒等式内所有"进口量"必须同一口径**；并在 τ=0 处**断言 ΔWelfare ≡ 0**（基准态自洽性测试）。

**检查代码**：
```python
w0 = solve_auto(par, tau0_e0, ...)["welfare_bn"]
w_base = solve_auto(par, tau0_e0, ...)          # 同一 τ 两次调用
assert abs(delta_welfare_at_zero_policy) < 1e-9, "零政策处福利增量非零 = 两口径混用"
assert abs(par["M"] - par["import_share"]*par["sales_m"]) < 1e-9 or "两基数必须显式归一"
```
**实测：pass**（重造出的虚假福利 +1.672959 bn，符号与量级与论文 −1.06 bn 同机制）。

---

## P-M08 零敏感性可能只是采样盒没跨过临界面

**现象/触发**：Q1 的 capacity 乘子 Sobol 总阶指数报 0，采样盒 `[0.85, 1.15]`；而容量约束的临界乘子 `m*` 是 τ 的函数。
用户清单断言 `m* ≈ 0.82`、盒下限 0.85 高于它。

**定量后果**（`p08_sobol_box.py`、`p08b_sobol_box_audit.py`、`p21_q1_critical_bisect.py`、`p49b_q1_cap_inert.py`）：
- 二分求 **m\* = 0.817671**（τ1=.47, σ=6.5），与 `data/q1_binding_surface.json` 的 `mstar 0.817682` 差 1.1e-5。
- 盒下限 0.85 比 m\* 高 **3.95%** → **盒内永不 bind**。
- q_Brazil 样本标准差：盒 `[0.85,1.15]` → **0.0000**（range 死平 81.090）；`[0.70,1.15]` → sd 2.8385；
  `[0.60,1.15]` → sd 6.1170；`[0.50,1.15]` → sd 9.4465。→ **盒形决定方差，不决定模型**。
- 4 输入 Saltelli（σ/pass/div/capmul，n=150）：capmul 固定或 `[0.92,1.10]` → ST = σ .4085 / pass .6364 / div .0000 /
  **cap .0000**（和 1.0449）；capmul 扩到 `[0.60,1.10]` → σ .0553 / pass .0154 / div .2161 / **cap 1.1566**（和 1.4435）。
  → **cap 的零指数是盒的假象，跨过 m\* 后立刻变成第一大驱动**。
- 论文 `tables/tab_binding.tex` 脚注自认 "the box [0.85,1.15] therefore straddles the critical line only above τ≈0.7"（引自论文），
  但 `tables/tab_sobol.tex` 的 caption 仍写 "over the parameter box used by the Monte Carlo" —— 且 **9/9 个输入的两套盒都不同**
  （`p57b.py`：σ 2–8 vs 2.4–8；pass 0.5–1.0 vs 0.6–1.0；div 0.2–1.0 vs 0.3–0.9；τ0/τ1 自由 vs 固定；cap 0.85–1.15 vs 0.92–1.10）。

**规定**：报告任何"0 敏感性"前，**必须先算临界值 m\*** 并断言采样盒跨过它；若未跨过，指数必须标 `inert (box never
crosses m*=…)` 且不得用于论证"该参数不重要"。Sobol 盒与 MC 盒若不同，必须两表分列。

**检查代码**：
```python
mstar = bisect(lambda m: q_Brazil(m) - cap_brazil(m), lo, hi)   # 首次 bind 的乘子
assert box_lo <= mstar <= box_hi, f"box [{box_lo},{box_hi}] never crosses m*={mstar:.4f}; ST=0 is an artefact"
assert np.std(q_brazil_samples) > 0, "样本方差为 0：该轴在盒内是常数"
```
**实测：pass**。

---

## P-M09 参数在函数签名里但函数体从不读它：敏感性恒为 0

**现象/触发**：`q2.solve_auto(par, tau, phi, subsidy, sigma_top, sigma_mode, sigma_in)` 的 `sigma_in` 在函数体出现 **0 次**。
`data/results_q2.json` 里 `elasticity.sigma_import = −0.20778860758275833`（se 0.2290092303621269, n=60），
代码却用 `sigma_import_used = 4.0`。

**定量后果**（`p09_sigma_in.py`）：
- σ_in = 0.5 / 1 / 2 / 4 / 8 / 16 → `imports_m` 恒 **7.428131564**、`welfare_bn` 恒 **+0.826046260**，
  最大差 **0.0**（bit-identical）。
- 论文 `tab:inert` 已把它标 `unread` 且给输出 7.428（引自论文）→ **半修**：表承认了，代码没删。

**规定**：**函数签名里的参数若不被函数体引用，必须删除或抛 `NotImplementedError`**；敏感性表里它必须标 `unread`
而不是给 0，且**不得**把它算进"稳健性"论证。同理，校准值与使用值不一致（−0.208 vs 4.0）必须两处标注来源。

**检查代码**：
```python
import inspect, ast
src = inspect.getsource(solve_auto); tree = ast.parse(src)
params = [a.arg for a in tree.body[0].args.args[1:]]
body = ast.dump(tree.body[0])
unused = [p for p in params if f"'{p}'" not in body and f" {p}" not in body]
assert not unused, f"unread parameters: {unused}"
```
**实测：pass**。

---

## P-M10 网格搜索最优点落在边界上，必须报边界并向外扩一次

**现象/触发**：`q3.optimize_segment` 用 `arange(0,0.26,0.01) × arange(0,0.51,0.01)`；`q1_policy_frontier` 的 `tau` 网格
上限 1.0。用户清单断言"最优点落在网格边界"。

**定量后果**（`p10_grid_edge.py`、`p10b_laffer_edge.py`、`p10c_q1_laffer_extend.py`、`p46_sec_lower_bound.py`）：
- Q3 mid 段最优 **(τ=.25, s=.27, W=2.198013)**，τ **恰在上界**；扩到 0.60 后最优 **(τ=.60, s=.25, W=2.566726)**
  （**+0.369，+16.8%**），且**仍贴上界**。welfare 在 τ=.24/.25/.26/.28/.30 单调升 2.1667/2.1826/2.1979/2.2271/2.2545。
- Q3 `security_floor_optimum` τ=.25（贴上界）；frontier 中 **lam_scale ≥ 1.2 起 τ 全部 0.25**。
  对 high 段把 τ 扩到 0.60，最优点仍是 (.16,.36)、W 1.7988 → **上限对该段不约束（+0.0000）**，需分项报。
- Q1 frontier `laffer.by_sigma`：**8/42 个 σ 的 τ\* = 1.0**（σ=2.4/2.54/2.68/2.82/2.96/3.1/3.24/3.38）；
  **真跑 solver 扩到 τ=2**：σ=2.40 → τ\* = **1.65**, rev **5.2971**（vs 1.0 处 4.9719，**+6.5%**）；
  2.68 → 1.38 / 4.8423；3.10 → 1.13 / 4.3732；3.38 → 1.015 / 4.1477 → **4 个角点的真峰在 τ>1**。
- Q4 Laffer 网格 ≤1.0 → argmax τ=0.35423 / R=441.146；扩到 2.0 仍 0.35424（**此处不截断**）。

**规定**：任何最优点落在网格边界时，**必须报"边界解"**并在正文写明搜索上界，**并向外扩网格一次**再报；
若扩后仍贴边，结论只能写"在 [lo, hi] 内单调，最优在边界"。

**检查代码**：
```python
best = max(grid, key=f)
inner = all(lo[i] < best[i] < hi[i] for i in range(len(best)))
assert inner, f"boundary solution at {best}: re-run on an extended grid before reporting"
```
**实测：pass**。

---

## P-M11 蒙特卡洛抽样区间必须以校准值为中心

**现象/触发**：多个乘子被抽自 `U(0,1)` 或 `U(0.5,2)`，其中位数偏离校准值 1.0。用户清单断言 "0–1 vs 0.5–2 的差别"。

**定量后果**（`p11_mc_box.py`、`p11b_lamcenter.py`、`p26_q3_boxcenter.py`）：
- Q3 λ 乘子：`U(0,1)` 均值 **0.5003**（偏 **−49.97%**）；现行 `U(0.5,2)` 均值 **1.2504**（偏 **+25.04%**，方向反了但仍有偏）；
  `U(0.9,1.1)` 均值 1.0。
- 真模型 MC（400 次，δ~U(.30,.50)）：`U(0,1)` → W mean **0.6146** [0.0061,1.6947]、τ 贴边 0.000；
  `U(0.5,2)` → mean **2.9401** [0.6502,6.2176]、**贴边 0.547**；`U(0.9,1.1)` → mean **1.8188** [1.2315,2.4560]、贴边 0.095。
  → **中心化差 3 个百分点，福利口径改 4.8 倍**（0.61 → 2.94）。
- 其余乘子偏置：`cL_s U(1.06,1.16)` 均值 1.11（+0.91%）；`phi U(.6,1)` 0.80（0）；`sm U(2,5)` **3.50（+16.67%）**；
  `eps U(2,4.5)` **3.25（+8.33%）**；`g U(.01,.06)` 均值 .035（**−44.69%**，且校准值 .06328 在箱外）；
  `persist U(.6,1)` 均值 .80（−20%，校准值 1.0 在箱**边界**）。
- Q5 是**正例**：θ~N(.12,.04) 均值 .1186、γ~N(−.06,.02) 均值 −.0594（`p61_q5_multiplier_bias.py`）。

**规定**：乘子型参数**必须绕校准值 1.0 居中**（中位数 = 校准值），区间端点对称或对数对称；抽样后**断言**
`|mean(multiplier) − 1| < 0.05`。物理量参数（σ、g、persist）的区间必须**含校准值且不把校准值放在端点**。

**检查代码**：
```python
draws = rng.uniform(0.9, 1.1, 4000)          # 以 1.0 为中心
assert abs(draws.mean() - 1.0) < 0.05
assert lo <= calibrated <= hi and not np.isclose(calibrated, lo) and not np.isclose(calibrated, hi), \
    "校准值在抽样盒外或贴着盒边"
```
**实测：pass**。

---

## P-M12 确定性点估计落在自己的 MC 区间之外：两种口径，不是矛盾，但必须分开写

**现象/触发**：Q4 Persist 点估计 411.8948 落在 MC 的 [27.8894, 353.6175] 之外；Q1 q_US 点 15.7889 落在 [15.9050, 18.9197] 之外。

**定量后果**（`p12c_point_mc.py`、`p22_q4_family.py`、`p31_q1_mc_center.py`、`p34_q1_pt_vs_mc.py`、`p63_allpoint_in_mc.py`）：
- Q4：点 411.8948 vs MC mean 183.0464 [27.8894, 353.6175]，**超 p95 58.2773 bn**。根因：点的 g=0.06328 **高于 MC 自己的
  g 上界 0.06（+5.47%）**；压到 0.06 仍是 408.0445（仍在外）。另两项 Partial 318.7192、Full 201.8809 在区间内。
- Q1：1200 次重跑 shipped 生成器（seed 20251112）→ q_US mean **17.4141** [15.8832, 18.8924]，点 15.7889 在外，
  **3.5% 的抽样低于点估计**；`pass>=0.99` 占 3.3% → 点估计≈自身分布的 3.5 分位。原因：`p48_q1_pt_outside_why.py`
  证明 div 与 capmul 对 q_US **完全无影响**，唯二有效轴是 σ 与 pass，而点估计把 `pass` 放在 **U(0.6,1.0) 的上端点**。
- 汇总（`p63_allpoint_in_mc.py`）：**Q1 q_US、Q4 Persist 两项在外；Q2/Q3/Q5 共 8 项在内**。

**规定**：点估计与 MC 区间是**两种口径**（确定性中心参数 vs 参数不确定性分位带），必须分两行/两列标注口径，
**禁止**把两者当同一个数的"估计与误差"。同时**断言**"点估计使用的每个参数都落在自己 MC 盒内且不在盒边"；
若在外，必须给出根因（哪一维被放在端点）。

**检查代码**：
```python
pt = solve(**point_params)
lo, hi = np.percentile(mc_draws, [5, 95])
inband = lo <= pt <= hi
assert all(box_lo[k] < point_params[k] < box_hi[k] for k in box), \
    "点估计参数在抽样盒外/边上；区间无法包含它是设计问题"
print(f"point {pt:.4f} band [{lo:.4f},{hi:.4f}] in={inband} frac_below={np.mean(mc_draws<pt):.3f}")
```
**实测：pass**。

---

## P-M13 Sobol 指数轴的约定：`S1[input][output]` 转置读会得到 >1 的份额

**现象/触发**：用户清单断言"按行单独算 MSE 的 Sobol 轴序搞反会得到无意义结论"。

**定量后果**（`p13_sobol_axis.py`）：
- `code/q1_sobol.py` L112–121：`s1 = np.zeros((d,n_out)); s1[i] = (fB*(fAB-fA)).mean(axis=0)/var`
  → 形状 `(9, 11)` = **[input][output]**，原样 `tolist()` 存盘（L156–157 不转置）。
- 正确读法 `ST[input][output]`，q_US 列和 **1.0612**（O(1)，admissible）；全部 11 列和：
  q_US 1.0612 / q_Brazil 1.0601 / q_Argentina 1.0603 / q_ROW 1.0668 / v_US 1.1491 / v_Brazil 1.0603 /
  v_Argentina 1.0605 / v_ROW 1.0671 / **total_mmt 0.6110** / total_bn 1.0387 / avg_price 1.0375。
- 转置误读 `ST[output][input]`：行和 sigma .3810 / pass .3811 / diversion .0003 / tau0 .3395 /
  **tau1 10.1705** / cap_* ≈0 → **物理不可能（>1 达 10 倍）**。
- 论文 `tab_sobol` 的 "Sum of S_T = 1.0612 / 1.0375" 与我复算**一致** → **轴序本身是对的**。

**规定**：存盘前**必须断言"ST 按输入求和 ≈ 1"**；若按输出求和 >1，即轴序反了（或数据被转置）。`total_*` 类输出的
低和（本例 0.611）必须单独解释为**交互项**，不得当作"遗漏参数"。

**检查代码**：
```python
ST = np.array(j["ST"]); d, m = ST.shape
colsum = ST.sum(axis=0)          # 按输入求和，正确轴序下应 ≈1
rowsum = ST.sum(axis=1)          # 按输出求和
assert np.all(colsum > 0.9) and np.all(colsum < 1.2), f"axis reversed? colsum={colsum}"
assert not np.any(rowsum > 1.5), f"row sums >1.5 means transposed: {rowsum}"
```
**实测：fail（命题为假）/ pass（反例可复现）**：本项目轴序正确；转置读法可稳定产出 tau1 = 10.17 的荒谬份额。

---

## P-M14 代理模型的高 R² 是插值必然，不构成验证

**现象/触发**：Q1 用 NN 代理 `solve_equilibrium`，报 TEST r2 ≈ 0.99999。用户清单关注"验证卫生"。

**定量后果**（`p14_surrogate_audit.py`、`p14b_surrogate.py`、`p52_surrogate_spike.py`、`p58_audit_cv_ceiling.py`）：
- 选型只用 **val**（10 组 `mean_val_r2` 0.9999562–0.9999844）；final **VAL r2 0.999988653 vs TEST 0.999991179**
  （test 反而高 +2.525e-06）→ **无 test 泄漏**（review 里"test 被 evaluate 11 次"是计算次数，不是选择泄漏）。
- **CV 5 折 best_epoch = 55–59 / 预算 60，全部贴顶** → CV r2 是误差的**下界**，不是收敛值（极差 2.452e-05）。
- train loss ep0 0.02736 → ep47 **0.07015** → ep48 0.00266，**最大偏离 316.6×**，只有 ep47/ep48 两处。
  论文正文（~620 段）称 "the learning rate non-monotone after epoch 120"（引自论文），
  但 `CosineAnnealingLR(T_max=epochs)` 的 lr **单调下降**（max diff −1.234e-07；ep120 6.91e-4 → ep187 2.1e-5 → ep199 0）
  → **描述的是 T_max=60 的旧三段余弦，代码已修，正文未同步**。
- 唯一非平凡误差：**inside r2 0.9999889 / outside 0.9993192**，worst **v_US 0.998814**；n_inside 4797 / n_outside 2640。
- final `best_epoch 187/200`，最后 13 epoch 被丢弃。

**规定**：代理模型报告**必须给"箱外外推最差输出误差"**（本例 0.999319 / worst 0.998814），**禁止**只报均值 R²；
CV 若 best_epoch 贴预算上限，必须标"误差下界（未收敛）"。

**检查代码**：
```python
assert cv_best_epochs.max() < epochs_budget - 2, "CV 贴预算上限：误差是下界，不能称'已收敛'"
print("extrapolation:", {"inside": r2_in, "outside": r2_out, "worst": worst_out})
assert r2_out < r2_in and worst_out < r2_out, "外推误差必须单独报，且必须比箱内差"
```
**实测：pass**。

---

## P-M15 情景冲击的基准期从数据取，禁止字面量

**现象/触发**：`code/q5_macro.py` L126 `d_shock = 100*(e - 0.025)` 写死 0.025，而模型自己的 e24 = 0.02396861。

**定量后果**（`p15_q5_base.py`、`p15b_q5_base_quant.py`）：
- 偏移 **0.1031 pp** 的关税率；d_shock 用 0.025 → **+4.4156 pp**，用 e24 → **+4.5188 pp**。
- 经 θ=0.12：首季通胀**低估 0.0124 pp**；14 季峰值通胀 4.4172 vs 4.4499（**−0.0327 pp**）；
  均值通胀 4.2152 vs 4.2459；均值 GDP 1.2535 vs 1.2410（+0.0126 pp）。
- 0.025 不出现在任何数据文件；e24 = 2.3969% 出现在 `data/q4_monthly.csv` 聚合里。

**规定**：情景冲击的**基准期必须从数据取**（`e24`），**禁止**字面量；若确需保留字面量，必须在代码注释与论文两处
同时标注"与实测 e24 差 0.1031 pp"。

**检查代码**：
```python
e0 = d[d.index.year == base_year].e_rate.mean()
assert abs(e0 - E0_LITERAL) < 5e-4, f"基准期字面量 {E0_LITERAL} 与实测 {e0:.6f} 不符"
```
**实测：pass**（量级小，但常数确实错，0.025 vs 0.02396861）。

---

## P-M27 Q1 的 `tau0` 被论文一处说成 inert，实处会动 2.57 MMT

**现象/触发**：`solve_equilibrium` 里 `delta_tau = (tau1-tau0)/(1+tau0)`，τ0 不抵消。论文 `tab:inert` 第 3 行
"Q1 tariff τ0 0.032 moves"（引自论文）与正文 ~41066 "the pre-policy tariff cancels out of the Question 1 ratio"（引自论文）**互相矛盾**。

**定量后果**（`p47_q1_tau0_inert.py`、`p56_inert_sweep.py`）：
- τ0 = 0.00/0.10/0.25/0.50 → total 107.511229 / 106.815574 / 105.937877 / 104.942751，极差 **2.568 MMT**；
  US 9.139383 / 11.674580 / 15.788930 / 23.004864；Δtau = +0.470000 / +0.176000 / **−0.020000**。
- 对照：diversion 0→1 与 capBR 0.85→1.15 的 US swing/ref **0.000e+00**（完全不动）→ tab:inert 把这两项标 inert 是**对的**。

**规定**：**禁止**在没有一次性扫描证据时把参数称作"cancels / inert"；正文与 tab:inert 的参数处置必须同源同值。

**检查代码**：
```python
vals = [solve(...tau0=t)["total_mmt"] for t in (0.0, 0.1, 0.25, 0.5)]
assert max(vals)-min(vals) < 1e-6*np.mean(vals), "tau0 显然会动；不得称 inert"
```
**实测：pass（矛盾成立）**。

---

## P-M43 Q3 补贴项漏乘加成率 μ：福利高估 83.7% of W，推荐政策是记账产物

**现象/触发**：`code/q3_semiconductors.py::welfare` L98 `sub = s*(1+delta)*qD`，而 `ps = (mu-1)*(1+delta)*(1-s)*qD`
是**含 μ 的价格**口径。补贴按单位产出支付，单位价值应等于本地价 `pD = (1+δ)(1−s)μ`。

**定量后果**（`p43_q3_sub_mu.py`、`p44_q3_sub_mu_flip.py`、`p45_q3_sub_sensitivity.py`）：
- high 段：补贴 6.0223 → **7.5279（+25.0%）**；W 高估 **1.5056 bn = 83.7% of 1.7988**。
- 单位补贴乘子 k 扫描：k=1.00 → (τ .16, s .36, W 1.7988)【现稿】；k=1.10 → (.12,.32,1.2888)；
  **k=1.25（正确）→ (.09,.26,0.7904)**；k=1.50 → (.07,.18,0.3534)；k=2.00 → (.05,.05,0.0818)。
- mid/low：修正后**最优 s 全部顶到 0.50**（mid .25/.50/2.4865；low .25/.50/4.9670）。
- → 推荐值 **τ16% / s36%** 是"补贴按 80% 成本记账"的产物。

**规定**：**成本项与收益项必须用同一价格层级**；补贴/税收单位价值必须等于它作用的那个价格（此处本地价含 μ）。
任何"福利为正的推荐政策"在修正记账后若仍为正才算结论。

**检查代码**：
```python
assert abs(sub_total - s*pD*qD) < 1e-9, "补贴必须按本地价（含 mark-up）计成本"
assert abs(ps_total - (mu-1)*pD*qD) < 1e-9, "生产者增益与补贴必须同一价格层级"
```
**实测：pass**。

---

## P-M53 Q3 的段规模是定义不是校准，模型无法表达本地部门独立收缩

**现象/触发**：`V = imports/(1-x0)` 与 `total_value_bn` 恒等；`qD = x*V/pD` 于是被 x0 钉住。

**定量后果**（`p53_q3_base_vs_import.py`）：三段 `V/(imports/(1−x0))` 比值 **1.000000**
（high 30.25/0.9=33.611；mid 9.753/0.75=13.004；low 23.3202/0.82=28.4393）。

**规定**：把"总量 ∝ 1/(1−x0)"这类定义式当校准值引用是重复计数；**禁止**在论文里把 V 与 imports 当两个独立数据点。
若模型需要本地部门与进口独立变动，必须给两个独立基量。

**检查代码**：
```python
for seg in segs: assert abs(seg["V"] - seg["imports"]/(1-seg["x0"])) < 1e-9, "V 由 x0 定义"
```
**实测：pass**。

---

## P-M54 芯片三段与整个 HS 8542 是两个分母（H1）

**现象/触发**：high 30.25 + mid 9.75 + low 23.32 = 63.32 vs `total_chip_import_bn` 40.3865。

**定量后果**（`p54_h1_segments.py`）：比值 **1.5679（+56.79%）**；`total_chip_import_bn` = 40.386451682
（与论文 40.39 一致）；段和 63.3233（与论文 63.32 一致）→ **两数都对，分母不同**；论文正文（~16965 / ~61241）
已写明"sum to $63.32 bn across the two headings and not to the $40.39 bn of 8542 alone"（引自论文）。

**规定**：同一节里出现两个"芯片进口"总量必须**显式给分母标签**（HS 8542 单独 / 8542+8541 合并），
且禁止把两数的比值当增长率。

**检查代码**：
```python
assert abs(sum(seg["imports_bn"].values()) - SEG_SUM) < 1e-6
assert abs(total_chip_import - TOTAL_8542) < 1e-6
assert math.isclose(sum(segs)/total, 63.3233/40.3865, rel_tol=1e-4)   # 分母必须写明
```
**实测：pass（数字对、分母标签缺失）**。

---

## P-M55 网格边界为主导时，"平均最优"是截尾变量的均值

**现象/触发**：Q3 MC 里 57.1% 的抽样把 τ 顶到 0.25 网格上界，报出的 tau mean 0.1945。

**定量后果**（`p55_q3_mc_boundary.py`、`p46_sec_lower_bound.py`）：
- `boundary_share = 0.571`，p95 τ = 0.25 → 至少 57.1% 的抽样落在上限；0.1945 是 `min(τ*, 0.25)` 的均值，
  **不是 τ\* 的均值**（真值 ≥ 0.1945）。
- welfare mean 3.1096 [0.6424, 6.1082]，而点估计 1.7988 **在区间内**；MC 均值高于点估计是因为 λ_scale 的 U(0.5,2) 均值 1.25（见 P-M11）。

**规定**：抽样落边界时，**必须报 `boundary_share`**，且"均值"必须标为**截尾均值**；不得把截尾均值当作无约束最优。

**检查代码**：
```python
bs = np.mean(tau_draws >= tau_ceiling - 1e-9)
assert bs < 0.05, f"boundary_share={bs:.3f}: 报截尾均值或扩网格"
```
**实测：pass**。

---

## P-M16 数据台账：25/54 个源无字节可复核

**现象/触发**：论文 Appendix B 称 "URL, UTC timestamp and SHA-256 for all 54 sources"（引自论文）。

**定量后果**（`p16_data_audit.py`、`p16c_cache_sha.py`、`p16d_ledger_fresh.py`）：
- `data/ledger.json` 54 sources，`sha256` 字段 54/54 非空且互异；`data/cache` 152 文件；按 `sha256(url)[:20]+".bin"`
  匹配 → **29/54 命中，25/54 缺失（46.3%）**；命中的 29 个文件 sha256 与 ledger **全部 MATCH（0 mismatch）**。
- ledger 的 `cached` 字段 **54 个全为 False**（而 29 个确实在盘上）→ 字段本身失信。
- `data/cache` 中 **123 个文件不被任何 ledger url 引用**（孤儿缓存）。
- `fetched_at` 30 个不同值，全部落在 `2026-11-10T10` 这一小时内。

**规定**：**"可复现"必须落地为"源→缓存→sha256→结果"的闭环断言**；无字节的源必须在 ledger 标 `cached:false` +
在论文写"该源不可独立复核"，`cached` 字段必须由文件存在性生成而不是手写。

**检查代码**：
```python
import hashlib, json, pathlib
led = json.load(open(DATA/"ledger.json"))
ok = [s for s in led if (pathlib.Path("data/cache")/(hashlib.sha256(s["url"].encode()).hexdigest()[:20]+".bin")).exists()]
assert len(ok) == len(led), f"{len(led)-len(ok)}/{len(led)} sources have no cached bytes"
```
**实测：pass**（46.3% 缺失；引用不实）。

---

## P-M20 Q3 的 CS 符号由价格指数口径决定（P-M01b 的量化）

见 P-M01b：算术价下 CS = **+0.481013**，CES 价下 **−0.608706**，符号翻转，差 1.089720 bn。
**规定**：CS 的符号必须在正文中与"价格指数是算术还是 CES"同句给出，禁止单独引用 CS 符号做福利判断。
**实测：pass**。

---

## P-M29 tab_q2 的算术闭合（把"矛盾"判成假）

**现象/触发**：review 称 tab_q2 自由贸易行相加 = −0.9200 ≠ 报告 −0.1750。

**定量后果**（`p29_tab_q2_arithmetic.py`）：按**增量**列 `−consumer_cost + tariff_rev_increment + producer_gain`
与 `welfare_bn` 的残差，**六行全 0.0000**（含 Free trade 行）。→ −0.9200 是把 **LEVEL 列**相加的结果，
而福利是**增量**口径；论文 caption 已注明 "the one place the two accounting bases cannot be read off each other"（引自论文）。

**规定**：表里同时存在 LEVEL 与 Δ 两套列时，**表头必须分标**，且 caption 必须给一行"如何相加才等于 ΔWelfare"的公式。

**检查代码**：
```python
for r in rows:
    lhs = -r["consumer_cost"] + r["tariff_rev_increment"] + r["producer_gain"]
    assert abs(lhs - r["welfare_bn"]) < 1e-6, f"{r['scenario']}: {lhs:.4f} vs {r['welfare_bn']:.4f}"
```
**实测：fail（命题为假）**——算术完全闭合，所谓矛盾是口径误读。

---

## P-M31 Q1 的 MC 盒不以点估计为中心（σ 6.5 vs 盒心 5.20）

**现象/触发**：`sigma_used = 6.5`，而 MC 抽 `sigma ~ U(2.4, 8.0)`（中心 5.20）。

**定量后果**（`p31_q1_mc_center.py`）：盒心 5.20；距点估计 **+1.30（+25.0%）**；距 IV 估计 2.7992 **−2.4008**。
两者都在盒内，但 back-test 最优 2.4 只距左界 0.2。MC q_US mean 17.4431 [15.9050, 18.9197]，
点 15.7889 **在区间外**（点比 MC 均值低 **9.48%**）。

**规定**：见 P-M11——乘子与中心参数必须绕校准值居中；若刻意用"偏离中心"的区间表达模型不确定性，
必须在正文写"本区间不以点估计为中心，点估计位于第 X 分位"。

**检查代码**：
```python
centre = (lo+hi)/2
assert abs(point - centre) < 0.1*point, f"MC box centre {centre} vs point {point}: document the offset"
```
**实测：pass**。

---

## P-M37 Q2 的"份额"一词对应两个分母

**现象/触发**：正文"at the 15% deal the export share drops from 27.0% to 22.1%"（引自论文）与 `tab_q2.tex`
的 Share 列（28.1 → 13.6）看起来矛盾。

**定量后果**（`p37_q2_local_share_tau.py`、`p17c.py`）：重跑模型 → X 份额 0.2813/0.2700/0.2391/**0.2207**/
0.1887/**0.1359**，L 份额 0.6188/0.6300/0.6613/**0.6803**/0.7142/0.7731（τ = 0/0.025/0.10/0.15/0.25/0.47）
与 `results_q2.json` 的 `mode_share` 逐位一致。正文的 27.0%→22.1% 是"日本品牌在美销量中出口占比"，
表里 28.1→13.6 是"日本占美国**进口**份额" → **两个分母同一个词**。

**规定**：任何"share"列必须写清分母（`of Japanese-brand US sales` / `of total US imports`）；正文与表若用不同分母，
必须在 caption 交叉引用。

**检查代码**：
```python
assert abs(mode_share["X"] + mode_share["L"] + mode_share["M"] - 1) < 1e-9
assert "denominator" in open(TEX).read().lower(), "share 列必须写明分母"
```
**实测：pass（口径混淆真实存在，算术无误）**。

---

## P-M39 Q4 Laffer 峰对"泄漏参数"与网格上限都很敏感

**现象/触发**：`revenue = e*M*(1−κe)` 的 κ 与网格上限各自移动 e\*。

**定量后果**（`p39_q4_laffer_leak.py`）：
- κ=0 → κ=0.5：eps 2.0 → 1.0000/0.4999（**−50.0%**）；2.5 → .6668/.4174（−37.4%）；3.0 → **.4999/.3542（−29.1%）**；
  3.5 → .4000/.3058；4.0 → .3333/.2680；4.5 → .2858/.2381。
- **eps=0.6795（模型自己的 OLS 估计）→ e\* = 1.0000 = 网格上界**（曲线在 e=1 仍上升）。
- 报告值 `laffer(eps=3.0)` = e\* **0.499875** / R_max **523.701618** / R_at_2024 78.91702。

**规定**：**Laffer 峰必须同时报 (ε, κ, 网格上界) 三元组**；若 e\* 触上界必须写"边界解"并扩网格（见 P-M10）；
不得用 4 位小数报一个由未标定参数决定的峰位。

**检查代码**：
```python
r = laffer(...) ; assert r["e_star"] < 0.9999, f"e*={r['e_star']:.4f} is the grid edge"
print("report (eps, kappa, grid_hi, e*, R_max) together")
```
**实测：pass**。

---

## P-M40 Q4 的 ε 是估计值 0.68 但用了 3.0：预测对 ε 的依赖未报

**定量后果**（`p40_q4_eps_source.py`）：`elasticity = {epsilon_ols 0.6795, se 0.8469, r2 0.9821, n 118, epsilon_used 3.0}`，
note "OLS is imprecise; calibrated central value 3.0 used"。2025 收入 R25 = ε·M25：ε .68 → 2314.5；1.5 → 4942.7；
2.0 → 6458.5；2.5 → 7911.8；**3.0 → 9304.3**；3.5 → 10638.1；4.5 → 13136.3 → **ε 从 .68 到 4.5 使同一公式的收入变 5.7 倍**。

**规定**：使用"校准值"而非"估计值"时，**必须同时报估计值、标准误、与切换造成的结论敏感度**；不得用估计值的
标准误去给校准值做区间。

**检查代码**：
```python
assert "epsilon_used" in est and "epsilon_ols" in est
assert "sensitivity_to_eps" in report, "换了 ε 就必须给敏感度表"
```
**实测：pass**。

---

## P-M41 Q4 的 MAPE 在"进口"上，不在"收入"上

**定量后果**（`p41_q4_rev_units.py`、`p41b.py`）：
- 2024：imports **3292.515 bn** / duties **78.917 bn** → e = **0.023969**；2025 Jan–Sep：imports 2630.511 / duties 174.042
  → e = **0.066163**（9 个月，年化进口 3507.35）。月度 e_rate：0.0225/0.0224/0.0239/0.0565/0.0808/0.1006/0.0981/0.1107/0.1082。
- `revenue(e25, e24, M24, 3.0) = **192.9885 bn**`；报告 `model_predicted_jansep = 152.2227`、`mape_imports = 0.117302`。
- → **验证指标是进口 MAPE (11.7%)，收入从未被验证**；论文摘要 "tracks the observed collections" 的措辞强于证据。

**规定**：**验证指标必须与被主张的量一致**；若验证的是进口、主张的是收入，正文必须分句写两个对象的证据强度。

**检查代码**：
```python
assert validation_key == "mape_imports" and claim_about == "revenue" is False, \
    "MAPE 在进口上，不得表述为'收入拟合良好'"
```
**实测：pass**。

---

## P-M42 Q4 的"累计净增益"大小由名义增长假设主导

**定量后果**（`p42_q4_netchange.py`）：Persist 逐年 net **+128.965 / +137.126 / +145.803** → 累计 **411.8948**；
g=0 → **342.2146**；g=0.06 → **408.0445**；"全部按 2024 税率"（无政策）→ **500.8771**
→ 无政策的累计税收**比有政策还高 88.98 bn**，即头条数字的方向来自"税率与进口基数的相对增长"，不是关税本身。

**规定**：报"累计净增益"必须**给无政策反事实的绝对值对照**，并说明该量在 g 与基数上的依赖；数字不得单独出现。

**检查代码**：
```python
assert "counterfactual_no_policy" in out and "g=0" in out["sensitivity"], "累计增益必须给反事实与 g 敏感度"
```
**实测：pass**。

---

## P-M44 补贴记账修正后 Q3 最优政策的敏感性

见 P-M43 的 k 扫描表（`p44_q3_sub_mu_flip.py`）：high k=1.25 → (τ .09, s .26, W 0.7904)；mid → (τ .25, s .50, W 2.4865)；
low → (τ .25, s .50, W 4.9670)。**规定**：推荐值必须附"记账口径乘子 k"的扫描表。**实测：pass**。

---

## P-M45 P-M43 的连续扫描（单位补贴成本 k）

`p45_q3_sub_sensitivity.py`：k=1.00 → (.16,.36,1.7988)；1.10 → (.12,.32,1.2888)；1.25 → (.09,.26,0.7904)；
1.50 → (.07,.18,0.3534)；2.00 → (.05,.05,0.0818)；**在 shipped 最优点重估 W 依次 1.7988 / 1.1965 / 0.2932 / −1.2124 / −4.2235**
（k≥1.5 时推荐政策的福利**转负**）。**规定**：补贴成本口径不明确时，结论只能写"符号不稳定"。**实测：pass**。

---

## P-M46 Q3 的安全权重 λ 决定"推荐关税"，而 λ 不可观测

**定量后果**（`p46_sec_lower_bound.py`）：frontier lam_scale 0.9 → (τ .13, W 1.466)；1.0 → (.16, 1.7988)；
1.1 → (.21, 2.178)；**≥1.2 起 τ 全部 = 0.25（网格上界）**；`security_floor_optimum` τ .25 / s .40 / x .5012 / W 1.6393（贴上界）。
对 high 段把 τ 扩到 0.60，最优点仍是 (.16,.36) / 1.7988 → 上限**不约束该段**（+0.0000）。

**规定**：把"国家安全溢价"作为可调权重 λ 时，**必须报"λ 在何值处改变推荐政策"**（本例 λ_scale ≈ 1.2），
并声明推荐值是 λ 的函数而非政策结论。

**检查代码**：
```python
taus = [opt(lam)["tau"] for lam in np.linspace(0.5, 2.0, 31)]
assert taus[0] != taus[-1] and "lambda_threshold" in out, "λ 改变结论的阈值必须报出"
```
**实测：pass**。

---

## P-M48 Q1 的点估计在自身分布的 3.5 分位（不是"中位数附近的估计"）

`p48_q1_pt_outside_why.py`：div 0.0/0.3/0.6/0.9 与 capmul 0.92/1.00/1.10 → q_US **恒 15.7889**、total 恒 **105.9379**
（**完全无影响**）；pass 1.0→0.6 使 q_US 15.7889→18.0635；σ 2.4→18.2378、8.0→15.3100。
`p34_q1_pt_vs_mc.py`：1200 次重跑 → 点估计位于 **3.5 分位**。**规定**：点估计若落在自分布的下/上 5%，
必须在正文标注"该点对应参数取值的端点位置"，并说明为何仍选它。**实测：pass**。

---

## P-M49 47% 关税下 capacity 与 diversion 真的不动（正例，防误报）

`p49b_q1_cap_inert.py`：capmul 固定 1.00 或 `[0.92,1.10]` → ST = σ .4085 / pass .6364 / div .0000 / **cap .0000**（和 1.0449）。
**规定**：报"某参数不影响结果"必须先证明**该约束在该情景下确实不 bind**（本例 q_Brazil 81.09 vs cap 91.77，util 88.4%），
否则按 P-M08 判为盒的假象。**实测：pass（同时是 P-M08 的反面对照）**。

---

## P-M50 Q2 的 tipping 13.6% 是 φ=0.8 的数

`p50_q2_pb_basis.py`：tipping 随 φ：0.6→**0.181159**；0.7→0.155280；0.8→**0.135870**；0.9→0.120773；1.0→**0.108696**；
换 σ_top / σ_mode = 4.0/4.0 **不变**（`p24_fig_vs_table.py`，tipping 只依赖 g_X=g_L 的闭式）。
**规定**：报告"临界关税"必须**绑定 pass-through 值**（本例 φ=0.8）并给 φ 扫描；单值出现即为不可复核。**实测：pass**。

---

## P-M51 Q2 的"1% 单位成本支持"是出口成本 cX 的 1%，不是本地成本的 1%

`p51_q2_subsidy_tip.py`：cX = 25032.479 USD/unit，s=0.01 → 250.325 USD/unit = 本地成本（cL·μ = 31666.086）的 **0.79%**；
NTR 行 tipping 0.1359/0.1250/0.1141/0.1033、welfare −0.3207/−0.3965/−0.4722/−0.5479 与论文一致；s=0 行 = Deal 行逐位一致
（`p35_q2_ntr_vs_table.py`）。**规定**：补贴口径必须写"占哪个成本基准"，百分比不得裸写。**实测：pass（措辞口径）**。

---

## P-M52 论文训练曲线的描述与已修代码不符

见 P-M14：train 尖峰仅 ep47/ep48、最大 316.6×；`CosineAnnealingLR(T_max=epochs)` lr **单调下降**（max diff −1.234e-07）。
论文仍写 "learning rate non-monotone after epoch 120"（引自论文）。**规定**：正文对超参行为的描述必须与**当前**代码一致；
改了 `T_max` 必须同步删改该段。**实测：pass（文-码不一致）**。

---

## P-M56 一次扫描复现 tab:inert 的 Q1 行

`p56_inert_sweep.py`：σ 2.4→8.0 swing/ref **1.854e-01**；pass .6→1.0 **1.441e-01**；div 0→1 **0.000**；capBR .85→1.15 **0.000**。
**规定**：tab:inert 这类表必须由一条可复跑脚本生成并落盘，而不是手写数字。**实测：pass**。

---

## P-M57 Sobol 设计盒 ≠ MC 抽样盒（9/9 都不同）

`p57b.py`：σ [2,8] vs [2.4,8]；pass [0.5,1.0] vs [0.6,1.0]；div [0.2,1.0] vs [0.3,0.9]；τ0 [0.2,0.3] vs 0.25 固定；
τ1 [0.03,0.6] vs 0.47 固定；四个 cap [0.85,1.15] vs [0.92,1.10]。**9/9 不同**。
**规定**：**禁止**用"MC 的盒"描述 Sobol/设计的盒（如 `tab_sobol` caption 现文 "the parameter box used by the Monte Carlo"）；
两套盒必须两处列出。**实测：pass**。

---

## P-M58 CV 的 best_epoch 全部贴预算上限

`p58_audit_cv_ceiling.py`：5 折 best_epoch **55/59/56/58/59**（预算 60），r2 极差 2.452e-05。
**规定**：CV 训练预算必须**从 best_epoch 反推**（≥ 2× 最长 fold 的 best_epoch），贴顶的 CV 只能标"误差下界"。**实测：pass**。

---

## P-M59 固定成本比例：代码与论文一致（H17 判假）

`p59_h17_fixed_costs.py`：代码 fX=0.01cX / fL=0.020cX / fM=0.015cX → 相对 cX 为 1.00/2.00/1.50%；
相对各自模式成本 1.00/1.82/1.44%。论文 "1.0%, 2.0%, 1.5% of the export cost"（引自论文）→ **一致**；顺序也是 fL > fM > fX。
**规定**：百分比基数必须写"of the export cost"。**实测：fail（命题为假）**。

---

## P-M60 结果字典缺 `cap2`，无法从返回值复算 binding

`p60_math_consistency.py`：5 条恒等式 **total=sum(qty) 0.00e+00；value=qty·price/1000 0.00e+00；avg_price 0.00e+00；
CES 聚合=Q0 4.44e-16**；但第 4 条（q ≤ cap2 且 flag 一致）**无法写**，因为 `solve_equilibrium` 不返回 `cap2`。
**规定**：凡进入 flag 判定的中间量（cap、cap2、slack）**必须随结果返回**，使 flag 可被外部复算。**实测：pass**。

---

## P-M61 Q5 的 MC 乘子中心化是正确的（正例）

`p61_q5_multiplier_bias.py`：θ~N(0.12,0.04) → 均值 **0.1186**、P(<0)=0.0020；γ~N(−0.06,0.02) → **−0.0594**。
**规定**：用正态绕校准值抽样是**正确**做法；若改成 `U(0,1)` 会把 θ 的均值砍到 0.5（偏 −38%，同 P-M11）。
**实测：fail（该坑在 Q5 不发生）**——作为 P-M11 的正面样板写进清单。

---

## P-M62 Q5 的点估计与 MC 区间口径分离（正例）

`p62_q5_mc_vs_point.py`：Partial|severe 平均 inflation **3.8106** vs MC [3.3057,4.3270]（内）；
gdp 1.4237 vs [1.2216,1.6111]（内）；u 4.3881 vs [4.2944,4.4892]（内）。
**规定**：见 P-M12——本项目只有 Q5 做对了，其余四处（Q1、Q4）需要按 P-M12 补口径说明。**实测：fail（该坑在 Q5 不发生）**。

---

## P-M63 全项目"点估计 in MC"对照表

`p63_allpoint_in_mc.py` 输出（自己跑的）：

| 项 | 点估计 | MC [p05, p95] | 在内 |
|---|---|---|---|
| Q1 q_US @47% | 15.7889 | [15.9050, 18.9197] | **否** |
| Q2 Japan welfare | −0.3207 | [−1.6969, 0.8671] | 是 |
| Q3 high welfare | 1.7988 | [0.6424, 6.1082] | 是 |
| Q3 high tau | 0.1600 | [0.0500, 0.2500] | 是 |
| Q4 Persist cum | 411.8947 | [27.8894, 353.6175] | **否** |
| Q4 Partial cum | 318.7192 | 同上 | 是 |
| Q4 Full cum | 201.8809 | 同上 | 是 |
| Q5 inflation | 3.8103 | [3.3057, 4.3270] | 是 |
| Q5 gdp | 1.4237 | [1.2216, 1.6111] | 是 |
| Q5 unemployment | 4.3881 | [4.2944, 4.4892] | 是 |

**规定**：这张表应作为交付物的一部分，每轮模型改动后重跑；出现"否"必须给根因（本例 Q1 = pass 在盒端点上；Q4 = g 在盒外）。
**实测：pass（2/10 在外）**。

---

## P-M64 场景表是生成物（可复现性正例）

`p64_q1_scen_baseline_match.py`：τ0=τ1=0.25 重跑 → qty `US 22.134149 / Brazil 74.647380 / Arg 4.101921 / ROW 4.149254`、
value `12.040339 / 36.455785 / 2.082480 / 2.147491`、`total 105.0327043769999` —— **与 `data/results_q1.json` 的 Baseline 行逐位一致**。
**规定**：任何复现工作的第一步都应是"重跑基准态并逐位比对"，通过后才讨论别的。**实测：pass**。

---

## 附录 A：脚本索引（`E:\数学建模\.tmp_scratch\`，跑完即弃，如需重跑见各条"检查代码"）

| 坑 | 脚本 |
|---|---|
| P-M01 | `p01_entropy_topsis.py`、`p30_q5_drop.py`、`p30b_q5_drop.py` |
| P-M01b / P-M20 | `p02_ces_price.py`、`p20_q3_mixed_index.py`、`p19_q3_priceindex_flag.py` |
| P-M02 | `p03_frozen_minmax.py`、`p65_minmax_forecast_flip.py`（面板无 year 列，改用合成面板） |
| P-M03 | `p04_ces_index.py`、`p04b_ces_numeraire.py`、`p27_q1_totals_identity.py`、`p28_tab_q1_header.py` |
| P-M04 | `p05_binding.py`、`p05c_cap_violation.py`、`p05e_forced_binding.py`、`p05f_true_cap.py`、`p05g_binding_tol_real.py` |
| P-M06 | `p06_paasche.py`、`p06b_paasche_proper.py` |
| P-M07 | `p07_bases.py`、`p07b_bases.py`、`p07c_bases.py`、`p17c.py` |
| P-M08 / P-M49 | `p08_sobol_box.py`、`p08b_sobol_box_audit.py`、`p21_q1_critical_bisect.py`、`p49_q1_cap_inert.py`、`p49b_q1_cap_inert.py` |
| P-M09 | `p09_sigma_in.py` |
| P-M10 | `p10_grid_edge.py`、`p10b_laffer_edge.py`、`p10c_q1_laffer_extend.py` |
| P-M11 / P-M31 | `p11_mc_box.py`、`p11b_lamcenter.py`、`p26_q3_boxcenter.py`、`p26b_q1_mc_box.py`、`p31_q1_mc_center.py` |
| P-M12 / P-M48 / P-M63 | `p12_point_vs_mc.py`、`p12c_point_mc.py`、`p22_q4_family.py`、`p34_q1_pt_vs_mc.py`、`p48_q1_pt_outside_why.py`、`p63_allpoint_in_mc.py` |
| P-M13 | `p13_sobol_axis.py` |
| P-M14 / P-M52 / P-M58 | `p14_surrogate_audit.py`、`p14b_surrogate.py`、`p52_surrogate_spike.py`、`p58_audit_cv_ceiling.py`、`p23_surrogate_vs_real.py` |
| P-M15 | `p15_q5_base.py`、`p15b_q5_base_quant.py` |
| P-M16 | `p16_data_audit.py`、`p16b_ledger_fields.py`、`p16c_cache_sha.py`、`p16d_ledger_fresh.py` |
| P-M27 | `p47_q1_tau0_inert.py`、`p56_inert_sweep.py` |
| P-M29 | `p29_tab_q2_arithmetic.py` |
| P-M37 / P-M35 | `p37_q2_local_share_tau.py`、`p35_q2_ntr_vs_table.py` |
| P-M39 / P-M40 / P-M41 / P-M42 | `p39_q4_laffer_leak.py`、`p40_q4_eps_source.py`、`p41_q4_rev_units.py`、`p41b.py`、`p42_q4_netchange.py` |
| P-M43 / P-M44 / P-M45 | `p43_q3_sub_mu.py`、`p44_q3_sub_mu_flip.py`、`p45_q3_sub_sensitivity.py` |
| P-M46 / P-M55 | `p46_sec_lower_bound.py`、`p55_q3_mc_boundary.py` |
| P-M50 / P-M51 | `p50_q2_pb_basis.py`、`p51_q2_subsidy_tip.py`、`p24_fig_vs_table.py` |
| P-M53 / P-M54 | `p53_q3_base_vs_import.py`、`p54_h1_segments.py` |
| P-M57 | `p57_sobol_box_vs_mc.py`、`p57b.py` |
| P-M59 | `p59_h17_fixed_costs.py` |
| P-M60 | `p60_math_consistency.py` |
| P-M61 / P-M62 | `p61_q5_multiplier_bias.py`、`p62_q5_mc_vs_point.py` |
| P-M64 | `p64_q1_scen_baseline_match.py` |

## 附录 B：一句话红线汇总（可直接贴进方法与验证章节）

1. 同一指数内**禁止混用归一化口径**；口径变更必须报首位是否翻转、最大权重比。
2. 预测年越界时**禁止沿用观测窗 min/max**；扩面板重算并声明不可比。
3. **禁止**用加权和替代 CES 指数；并列时必须两列分标、口径分开写。
4. `binding` 必须用**相对容差**，且必须同时检查物理上限与再分配上限。
5. 福利结论**禁止混用** Laspeyres / Paasche；必须报倍数与符号一致性。
6. 同一福利恒等式内**禁止混用两套进口基数**；零政策处 ΔWelfare 必须恒为 0。
7. 报"0 敏感性"前**必须先算临界值并断言采样盒跨过它**。
8. 签名里不被函数体读的参数**必须删除或抛异常**，敏感性表标 unread。
9. 最优点落在网格边界**必须报边界解并向外扩一次**。
10. MC 乘子**必须绕校准值 1.0 居中**，并断言均值偏离 < 5%。
11. 点估计与 MC 区间**必须分口径写**；点估计的每个参数必须落在自己的盒内且不在盒边。
12. 存盘前**必须断言 ST 按输入求和 ≈ 1**；按输出求和 > 1 即轴序反了。
13. 代理模型**必须报箱外最差误差**；CV 贴预算上限只能标"误差下界"。
14. 情景冲击的基准期**必须从数据取**，禁止字面量。