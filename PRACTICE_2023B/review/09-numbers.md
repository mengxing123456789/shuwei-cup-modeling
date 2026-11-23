BYTES 26961

# 09 数字对账（numbers audit）

被测件：`E:\数学建模\PRACTICE_2023B`
审计时刻：2026-11-19 18:16 – 18:26（本机时区）
唯一产出：本文件

---

## 0 被测对象状态：正文侧没有可审计的数字

| 项 | 派单/惯例期望 | 实测 | 证据 |
|---|---|---|---|
| `main.pdf` | 存在 | **不存在** | `Test-Path` = False；全目录 `*.pdf` 计数 = 0 |
| `main.tex` | 含结果数字 | 4546 B **未填写骨架**，69 处 `<<...>>` 占位符，结果数字 token = **0** | sha256 前缀 `2CC0E46029BBDEC6`，mtime 16:49:15 |
| `review\00-metrics.md` | 派单称「由派单脚本自动生成，口径唯一基线」 | **不存在** | `review\` 下仅 `04-fit.md`(17:42:09) / `05-model.md`(17:47:57) / `README.md`(16:49:15) |
| `tables\`、`figures\` | 有产物 | **均为空目录** | 目录存在、条目数 0 |
| `code\make_figures.py`、`code\make_tables.py` | — | 均不存在 | — |
| `code\verify_numbers.py` | 稳定 | 审计期间被并发改写 5 次（47267→47952→48143→48203→48303 B） | 见 §0.3 |

### 0.1 缺 PDF 不是编译问题（已证）

`xelatex` 在 PATH：`E:\MIKTEX\miktex\miktex\bin\x64\xelatex.exe`（XeTeX 3.141592653-2.6-0.999997 / MiKTeX 25.12）。

```
cd <冻结副本>
xelatex -interaction=nonstopmode main.tex
→ exit=0，Output written on main.pdf (5 pages)
   仅 LaTeX Warning: Reference 'LastPage' on page 3 undefined
```

用 pymupdf 抽这 5 页文本：`pages=5  chars=2330  distinct decimal tokens = 0`，可见占位符只剩 1 个 `<< sym >>`。
→ **骨架能编出 5 页 PDF；缺 `main.pdf` 是流程没走到，不是环境问题。** 这也意味着「正文里的数字」目前在任何载体上都不存在。

### 0.2 代际：数据层比被测件新 1 小时 29 分（R-V11）

| 层 | mtime | 大小 / sha256 前缀 |
|---|---|---|
| `main.tex`（被测件） | 2026-11-19 **16:49:15** | 4546 B / `2CC0E46029BBDEC6` |
| `code\solve.py` | 17:30:42 | — |
| `code\model_skeleton.py` | 17:42:58 | — |
| `code\s3_deliver.py`（产出 `data\*.json`） | 17:56:18 | — |
| `data\*.json` | 18:17:44 – 18:18:28 | 见 §0.4 |
| `code\verify_numbers.py` | 18:17:08 | 48303 B / `921093BC2A92B207` |

**被测件落后 1 小时 29 分，以下数字可能已被重跑覆盖。** 本报告一律以 18:18:51 的原子快照现场重跑的数为准，不引用 16:49 的正文（它没有数字可引）。

### 0.3 并发改写：同一脚本两次跑出不同的 needle 总数

| 时刻 | 字节数 | sha256 前缀 | 运行结果 |
|---|---|---|---|
| 18:14:42.079 | 47267 | `DA3B2865…` | — |
| 18:15:35.203 | 47952 | `0C18FBB0…` | — |
| 18:15:44.754 | 48143 | `BDE0CF0D…` | `deferred=139` |
| 18:16:00.390 | 48203 | `8D1E4FE2E7BD` | `deferred=142` |
| 18:17:08 | 48303 | `921093BC2A92B207` | （主树最新） |

`deferred` 从 139 变 142，纯粹因为脚本自己在改。→ **本报告全部结论基于冻结副本**（`C:\Users\29900\AppData\Local\Temp\num_audit\`，verify_numbers.py = 48203 B / `8D1E4FE2E7BD` / 18:16:00.390），主树后续变化不改变结论。

### 0.4 快照（唯一取数源）

`C:\Users\29900\AppData\Local\Temp\num_snap_181851\`（18:18:51 原子拷贝 `data\*.json` + `out\*.md` + `main.tex` + `code\*.py`）

| 文件 | sha256 前缀 |
|---|---|
| `results_q1.json` | `853FB6BDD14F` |
| `results_q2.json` | `D9B646AE51D7` |
| `results_q3.json` | `34A9BC403E54` |
| `results_q4.json` | `3714FE375A21` |
| `results_q5.json` | `93F88D016A03` |
| `results_timing.json` | `787B7FFBBDD4` |
| `results_binding.json` | `87E88799EDF0` |
| `results_boundary.json` | `E5515DC5E495` |
| `results_perturb.json` | `878111BFA5C0` |
| `ledger.json` | `F1E7F39729A8` |

与 18:16 冻结副本逐字节比对：**只有 `results_timing.json` 变了**（`1366E01311F0` → `787B7FFBBDD4`），其余 9 个 JSON 相同。这一条差异直接决定了抽样 S1/S2 的结论（§2）。

---

## 1 机器口径三条（原文）

派单要求「动手看正文之前先跑三条」。三条全部不通过或不可用，且其中两条失败于同一原因：没有 `main.pdf`。

### 1.1 `review_check.py`（12 条官方硬项）

```
$ python E:\数学建模\.agents\skills\mathmodeling\scripts\review_check.py E:\数学建模\PRACTICE_2023B
[FAIL] X-pdf 找不到 PDF
pdf: None   pages: 0
VERDICT: FAIL (fail=1 unknown=0)
[exit code: 1]
```

### 1.2 `gauntlet_check.py`（R 系列 16 项）

```
$ python E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py E:\数学建模\PRACTICE_2023B
[FAIL] paper resolved
[FAIL] main.pdf exists  run gauntlet.build() or xelatex first
0/2 PASS
[exit code: 1]
```

### 1.3 `mmkit.figfont`（图内有效字号）

```
$ E:\Mini\envs\mathmodel\python.exe -m mmkit.figfont main.pdf
ModuleNotFoundError: No module named 'mmkit'
[exit code: 1]
```

**图内有效字号无法用指定工具测量**（`mmkit` 未安装）。且 `figures\` 为空、无 `code\make_figures.py`、无 `main.pdf`，三重原因导致第 ④ 类缺陷（图表刻度）本次不可判。

---

## 2 `verify_numbers.py` 末三行（原样）

冻结副本（48203 B / `8D1E4FE2E7BD`）+ 同代数据 + 补齐两个 xlsx 后：

```
$ cd C:\Users\29900\AppData\Local\Temp\num_run
$ E:\Mini\envs\mathmodel\python.exe code\verify_numbers.py
```

```
claims=544 declared=544 checked=544 failures=0 verdict=PASS exit=0 json_ok=544 json_fail=0 tex_bound=0/142 tex_state=skeleton deferred=142
  DEFER 142 tex needles (main.tex is the skeleton: no result number to bind yet)
report=C:\Users\29900\AppData\Local\Temp\num_run\out\03-numbers.md bytes=43943
```

两点必须记下：

1. **`failures=0` 与 `verdict=PASS` 在 skeleton 态下不证明任何正文数字。** `tex_bound=0/142`，142 条 needle 全部 `deferred`（缓期，不计失败）——正文侧一条都没绑上，因为正文里没有数字。
2. 若 `data\` 里缺两个 xlsx，同一条命令退化成 `checked=542 failures=4 verdict=FAIL exit=3`，4 条均为 `UNEVAL/FAIL [B ledger] annex_i|ii sha256 与磁盘一致: EXC FileNotFoundError: ... 'Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx'`。补齐后 PASS。→ **PASS/FAIL 对工作目录内容敏感，报告必须带完整复算命令。**

---

## 3 抽样 10 个数字（逐个现场复算）

**抽样来源说明（必须先讲清）**：`main.pdf` 不存在、`main.tex` 结果数字为 0，所以「从 PDF 正文抽 10 个」在物理上不可能。唯一承载「将来会印进正文的数字」的文件是 `out\02-solve.md`（34305 B，mtime 18:06:48）。本节从它抽 10 个，覆盖摘要段 3 个、Q1–Q5 各 1 个、表 2 个，避开年份与题号。**下列「印的值」严格说是「待印的值」，正文尚未生成——这一点本身就是 §6 结论的一部分。**

复算口径：`E:\Mini\envs\mathmodel\python.exe`，直接读快照 `data\*.json` 的键，不经过任何中间脚本。

### 3.1 对账表

| # | 位置 | 印的值 | 产物文件与键名 | 现场复算的值 | 差 | 结论 |
|---|---|---|---|---|---|---|
| S1 | 摘要① 耗时 | `q1` median **156.304** ms | `results_timing.json` → `calls[name=q1].median_ms` | **157.518** | +1.214 ms（+0.78%） | **不可复算**（代际失效，§3.3-S1） |
| S2 | 摘要① 占比 | `q1` 占端到端 **74.2%** | 派生：`calls[q1].median_ms / calls[pipeline_q1_to_q5].median_ms` | **54.71%**（157.518/287.903） | −19.49 pp | **不可复算**（分母不稳定 + 代际失效，§3.3-S2） |
| S3 | 摘要③ 边界 | ★ **5** 个、★★ **12** 个 | `results_boundary.json` → `combos[*].n_boundary_star` / `n_extrapolation_star2` | CS 1 + CE 2 + LG 2 = **5**；4+4+4 = **12** | 0 | 可复算 |
| Q1 | Q1 表 | `CS Tar delta_end_pct` **−37.67** | `results_q1.json` → `combos.CS.products.Tar.delta_end_pct` | **−37.66700924974306** | 0.003 | 可复算 |
| Q2 | Q2 表 | `CS CO` span **5.400**、ratio **2.412** | `results_q2.json` → `combos.CS.gases.CO.span` / `.span_over_thr` | **5.399999999999999** / **2.4118** | <0.001 | 可复算 |
| Q3 | Q3 表 | `Tar` Δ 均值 **+30.783** | `results_q3.json` → `products.Tar.mean_Delta` | **30.7825** | 0.0005 | 可复算 |
| Q4 | Q4 表 | `CS Tar gamma` **−0.826** | `results_q4.json` → `selectivity.CS.gamma_centered.Tar` | **−0.8263126758069008** | <0.001 | 可复算 |
| Q5 | Q5 表 | `CS Char loo_rmse_rel` **0.00892** | `results_q5.json` → `combos.CS.loo_rmse_rel.Char` | **0.008920691530344188** | <1e-15 | 可复算（但该条 needle 为空，§5.2） |
| T1 | 边界放宽表 `CS, r=1.0` | `11.56 / 30.76 / 29.55 / 28.14` | `results_boundary.json` → `combos.CS.rows[r=1.0].point.{Tar,Water,Char,Syngas}` | **11.5552 / 30.7617 / 29.5457 / 28.1373** | ≤0.005 | 可复算 |
| T2 | 约束状态表 | `active` **5** 条，全表 **11** 条 | `results_binding.json` → `sources[*].binding` 的 Counter | `active:5, active-at-endpoints:1, vacuous:1, active-on-interpretation:1, active-near-edge:1, active-on-A-only:1, active-as-prohibition:1` = **11** | 0 | 可复算 |

**小计：10 个抽样中 8 个可复算，2 个不可复算（S1、S2）。**

### 3.2 复算命令（别人可拿同一份快照重跑）

```python
import json
L = lambda f: json.load(open(f, encoding='utf-8'))     # cwd = 快照目录
tm = L('results_timing.json'); bd = L('results_boundary.json')
q1 = L('results_q1.json'); q2 = L('results_q2.json'); q3 = L('results_q3.json')
q4 = L('results_q4.json'); q5 = L('results_q5.json'); bn = L('results_binding.json')

c = {x['name']: x for x in tm['calls']}
print(c['q1']['median_ms'], c['pipeline_q1_to_q5']['median_ms'])
print(100 * c['q1']['median_ms'] / c['pipeline_q1_to_q5']['median_ms'])
print(sum(v['n_boundary_star'] for v in bd['combos'].values()),
      sum(v['n_extrapolation_star2'] for v in bd['combos'].values()))
print(q1['combos']['CS']['products']['Tar']['delta_end_pct'])
print(q2['combos']['CS']['gases']['CO']['span'], q2['combos']['CS']['gases']['CO']['span_over_thr'])
print(q3['products']['Tar']['mean_Delta'])
print(q4['selectivity']['CS']['gamma_centered']['Tar'])
print(q5['combos']['CS']['loo_rmse_rel']['Char'])
print([r['point'] for r in bd['combos']['CS']['rows'] if r['r'] == 1.0])
from collections import Counter
print(Counter(s['binding'] for s in bn['sources']))
```

### 3.3 每个抽样数字的三件事

三件事定义：**(a) 能否从 `data/*.json` 找到键**；**(b) 键算出来是否等于印的数**；**(c) 该键是否由当前版本脚本生成（比 mtime）**。

| # | (a) 有键 | (b) 等值 | (c) 当前脚本生成 | 三件事结论 |
|---|---|---|---|---|
| S1 | 有（`calls[q1].median_ms`） | **否**（157.518 ≠ 156.304） | **否**：`results_timing.json` mtime 18:18:28 晚于 `s3_deliver.py` 17:56:18，但印的 156.304 逐位等于 **18:16 冻结副本**的 timing 值 → 印的是上一代 timing，被 18:18 重跑覆盖 | (a)✓(b)✗(c)✗ |
| S2 | 有（派生，无直接键） | **否**（54.71% ≠ 74.2%） | **否**：同 S1；且分母 `pipeline_q1_to_q5` 的 `stdev_ms=184.778 / median=287.903`，**CV=64.2%**（min 245.453 / max 638.799），本身就是不稳定量 | (a)✓(b)✗(c)✗ |
| S3 | 有（`n_boundary_star`、`n_extrapolation_star2`） | 是 | 是：`results_boundary.json` 18:18:26 晚于 `s3_deliver.py` 17:56:18 | (a)✓(b)✓(c)✓ |
| Q1 | 有（`products.Tar.delta_end_pct`） | 是 | 是：`results_q1.json` 18:17:44 晚于 `s3_deliver.py` 17:56:18 | (a)✓(b)✓(c)✓ |
| Q2 | 有（`gases.CO.span`、`.span_over_thr`） | 是 | 是：18:18:0x | (a)✓(b)✓(c)✓ |
| Q3 | 有（`products.Tar.mean_Delta`；注意键名是 `mean_Delta`，不是「Delta 的 mean」） | 是 | 是：18:18:1x | (a)✓(b)✓(c)✓ |
| Q4 | 有（`selectivity.CS.gamma_centered.Tar`） | 是 | 是：18:18:2x | (a)✓(b)✓(c)✓ |
| Q5 | 有（`combos.CS.loo_rmse_rel.Char`） | 是 | 是：18:18:2x | (a)✓(b)✓(c)✓ |
| T1 | 有（`rows[r=1.0].point`） | 是 | 是：18:18:26 | (a)✓(b)✓(c)✓ |
| T2 | 有（`sources[*].binding`） | 是 | 是：18:18:26 | (a)✓(b)✓(c)✓ |

**S1/S2 的性质要写清楚**：这两个数不是「算错」，是**快照失效**。`02-solve.md`（18:06:48）从 18:16 的 timing 里取数并印出，18:18 主树又重跑了一次 timing，把 `q1` 从 156.304 改成 157.518、`pipeline` 从 210.629 改成 287.903。于是「摘要里印的 74.2%」在**当前代数据上算不出来**——当前代算出来是 54.71%。这正是派单 R-V11 要求的「报告是快照」那条纪律的反面教材：**摘要数字随一次重跑漂移 19.5 个百分点，且没有任何机制会报错**（`verify_numbers.py` 因为 skeleton 态全部 deferred，一条都不会红）。

补充：同一份 timing 里 `q1/(五问之和)` = 157.518 / 222.235 = **70.88%**。若「占比」的本意是「q1 占五问计算量」，正确分母是五问之和而不是含 I/O 的 pipeline；74.2% 用的分母是 `pipeline_q1_to_q5`（含两次 annex 加载与自检），而 `selftest`/`load_annex_i`/`load_annex_ii` 三项合计 18.4 ms 也被算进了分母之外又被排除在分子之外。**同一现象两个分母，这是第 ① 类口径混用。**

### 3.4 额外复算（不计入 10 个抽样，供交叉验证）

| 印的值 | 键 / 算式 | 复算 | 结论 |
|---|---|---|---|
| 扰动 42 次 = 16+14+12 | `results_perturb.json` → `meta.counts` | `attempted=42, model_perturb=16, query_move=14, never_read=12, model_infeasible=1, model_feasible=15, flip_denominator=15, model_runs_with_flip=1`；`len(runs)=42`、`len(infeasible)=1`、16+14+12=42 | 可复算 |
| `eps_rel` 保持区间「宽 105.42%」 | `(hi−lo)/declared` | `(0.065646−0.012934)/0.05 = 105.424%` | 可复算 |
| `alpha−` 使 `k_required` n=2「掉 68.97%」 | `k*0.95/1.05` | base=0.010555555555555545 → **0.0095503**，跌幅 **−9.5238%** | **不可复算**（§5.3-②） |
| Q3 `Water` 行 `−7.55…+12.12 / −1.173 / 6/8 / 1` | `products.Water.*` | `n_exceed=6, sign_changes=1, n=8, mean_Delta=−1.1725, Delta range [−7.55, 12.12]` | 可复算 |
| Q3 `Tar` ratio 区间 `1.906–5.529` | `ratio_CE_over_LG` | `[1.9058693, 5.5286935]` | 可复算 |
| 重叠 7 点差 `0.000e+00` | `combos[*].max_abs_diff_on_overlap` | CS/CE/LG 三个组合全 `= 0.0` | 可复算 |
| `alpha+` 那 1 次不可行 | `results_perturb.json` → `runs[source=alpha, sign=+]` | `feasible=false, infeasible_reason="alpha>=1：n=1 需 ln(1-α)、n=2 需 1/(1-α)-1，均无定义"` | 可复算 |

---

## 4 结构性空转

派单第 4 步要求两件事：脚本里有没有 needle 为空或断言恒真的条目；正文里有多少数字**没有任何 claim 覆盖**。

### 4.1 断言恒真 = 6 条（自己验自己）

判据：AST 取每个 `A(...)` 调用的第 2 个位置参数（`fn`）与第 3 个（`expected`）源码文本，逐字相同即自反。共扫 92 个 `add`/`A` 调用点（其中 4 个位置参数的 90 个），命中 6 条：

| 行号 | 调用 | 为什么恒真 |
|---|---|---|
| `code\verify_numbers.py:362` | `A(g,"R2[0]", lambda il=il: il["R2_each"][0], il["R2_each"][0], ...)` | 唯一带 needle 的样本被拔掉后纯自反 |
| `code\verify_numbers.py:480` | `lambda pd=pd: max(abs(a-b) for a,b in zip(pd["CE"],pd["LG"]))` | 两侧同一表达式 |
| `code\verify_numbers.py:512` | `A(f"L q4 gamma {c}", f"gamma[{p}]", lambda sel=sel,p=p: sel["gamma_centered"][p], sel["gamma_centered"][p], ...)` | 两侧同一取值 |
| `code\verify_numbers.py:578` | `A("N q5 grid", f"grid_w[{i}]", lambda w=w: w, w, ...)` | 恒等式 |
| `code\verify_numbers.py:609` | `A(f"O q5 {c}/{p}", "point 首点", lambda d=d,p=p: d["point"][p][0], d["point"][p][0], ...)` | 两侧同一取值 |
| `code\verify_numbers.py:624` | `A("P binding","binding 取值都在合法集合内", lambda: sorted({s["binding"] for s in bn["sources"]}), sorted({s["binding"] for s in bn["sources"]}))` | **连 `expected` 都取自同一个集合，永远 True** |

前 5 条是「自反但至少读过数据」；`:624` 这条连 expected 都来自被检对象本身，**在任何输入下都不可能失败**，是纯空转。

### 4.2 needle 为空列表 = 6 条（从正文侧静默消失）

`needle_forms(v, nds=(2,1))`（`code\verify_numbers.py:103-143`）有三道闸：①舍入成 0 的写法丢掉；②相对误差 >5% 丢掉；③**有效数字 <3 位丢掉**（`n_sig(s) < 3: continue`，:140）。第三道闸把下列 6 条判成 `[]`：

| claim | expected | needle |
|---|---|---|
| `D q1 CS/Char` \| `delta_end_pct = 100·Δ/y[0]` \| evidence `solve.py:174` | `2.2595001711742557` | `[]` |
| `D q1 LG/Char` \| `delta_end_pct` | `-1.2721334020973043` | `[]` |
| `E q1 ilr CS` \| `lack_of_fit_F = (sigma_fit/sigma_noise)²` \| evidence `solve.py:204` | `0.4396392746554419` | `[]` |
| `L q4 carbon CS` \| `delta_end_pct` \| evidence `solve.py:388` | `-2.304726785115645` | `[]` |
| `L q4 gamma LG` \| `gamma[Char]` | `0.05548640934178156` | `[]` |
| `O q5 CS/Char` \| `loo_rmse_rel% = 100·rmse/mean(y_q1)` | `0.8920691530344188` | `[]` |

关键在 `evaluate` 里的分支：`if it["needle"]:` 对 `[]` 为假 → `ok_tex = None`。**这 6 条既不进 `deferred` 也不进 `failures`，直接从正文侧消失**，而 `failures=0` 照样成立。也就是说 `failures=0` 的语义是「544 条里 396 条没有 needle、6 条 needle 为空、142 条缓期、0 条真绑上」，与「数字都对」不是一回事。

### 4.3 覆盖：正文数字 86.8% 没有任何 claim 覆盖

`out\03-numbers.md` 里**没有 coverage 行、没有 M 列表**（`grep 'coverage|^\| *M[0-9]|未覆盖'` 在 03-numbers.md 零命中）。脚本里的 `coverage` 只出现在 `coverage_scan.annex` 的单元格计数断言（`code\verify_numbers.py:258-261`），与「正文数字覆盖率」无关。→ **派单第 4 步要求的 coverage 行在本脚本里不存在**，只能自建。

自建统计（剔代码块、行内 code、`L143` 这类行号引用）：

| 口径 | distinct token | 被 needle 覆盖 | 覆盖率 | 未覆盖 |
|---|---|---|---|---|
| ≥3 位有效数字的小数 | **365** | 48 | **13.2%** | **317（86.8%）** |
| 含整数 token | **437** | 48 | 11.0% | 389 |

142 条 needle 展平后共 192 个写法。未覆盖的高频结果数（括号为出现次数）：
`156.304`(3)、`68.97`(3)、`210.629`(3)、`0.5000`(3)、`9.091`(3)、`1.111`(3)、`74.2`(2)、`0.188`(2)、`15.83`(2)、`19.34`(2)、`105.42`(2)、`37.67`(2)、`1.446`(2)、`31.55`(2)、`54.65`(2)、`0.208`(2)、`37.140`(2)、`5.400`(2)、`1.313`(2)、`2.500`(2)、`5.705`(2)。

注意 `37.67`、`5.400`、`0.188` 这些**在 §3 里被我手工复算通过的数字，恰恰不在 needle 集合里**——它们能对上是我的手工工作，不是脚本的保证。

### 4.4 needle 精度比印刷精度粗：written 态下 85/142 绑不上（决定性实验）

`needle_forms(v, nds=(2,1))` 只产出 **2 位 / 1 位小数**的写法。把论文实际会印的写法喂给 `has_token`（`code\verify_numbers.py:98-100`，正则 `(?<![\d.])needle(?!\d)`）：

| 印的写法 | needle | `has_token` |
|---|---|---|
| `156.304` | `['156.30']` | **False** |
| `74.2` | `['74.21']` | **False** |
| `-37.67` / `-37.667` | `['-37.7']` | **False** |
| `5.039` | `['5.04']` | **False** |
| `5.400` | `['5.40']` | **False** |
| `30.783` | `['30.78','30.8']` | **False** |
| `-1.173` | `['-1.17']` | **False** |
| `-0.826` | `['-0.826']` | **True**（唯一命中，该条 nds=(3,2)） |
| `0.00892` | `[]` | None（静默消失） |

决定性实验：把 `out\02-solve.md` 全文转义后拼进骨架 `main.tex` 生成 `main_synth.tex`（39837 B），`tex_state` 变 `written`（result_tokens=1525、placeholders=68），再跑 `evaluate`：

```
declared=142  bound=57  unbound=85
```

**即：把论文里所有数字都写进正文，142 条 needle 仍有 85 条（59.9%）绑不上。** 另一路独立实验（把 02-solve.md 的数字 token 拼成纯数字串）得 `bound=48 unbound=94`，方向一致。

→ 结论：**needle 精度粗于正文印刷精度**。skeleton 态把 142 条全判缓期，正好掩盖了这个缺陷；一旦正文写成 written，大量真实、正确、可复算的数字会被判「未命中」。这是结构性缺陷，不是个别漏项。

### 4.5 claim 分组（544 条）

`A 8 / B 11 / C 12 / D 144 / E 18 / F 19 / G 171 / H 9 / I 6 / J 24 / K 11 / L 21 / M 10 / N 9 / O 45 / P 26`
带 needle 分布：`D 55 / G 31 / L 16 / O 11 / E 8 / N 7 / K 5 / J 4 / I 3 / M 2 = 142`
needle 三分：`None 396` / `[] 6` / 非空 `142`。

---

## 5 四类高频可复算缺陷逐类查

### ① 口径混用 —— 命中

- **耗时占比**：把「逐调用 median」与「pipeline 端到端 median」并列做占比（156.304/210.629 = 74.2%），而 pipeline 单次 **CV=64.2%**（min 245.453 / max 638.799 / stdev 184.778）。分母不稳定，占比不可复算；换分母（五问之和 222.235）得 70.88%，换当代数据得 54.71%。同一句话三个数。
- **比例 vs 百分数并列**：`O q5 CS/Tar loo_rmse_rel` 的 expected 是 `0.0549717`（比例），needle 写成 `5.50`（×100，见 `code\verify_numbers.py:583` `needle_forms(d["loo_rmse_rel"][p] * 100.0, ...)`）。这是设计，但 `out\03-numbers.md` 第 6 节把两者并列显示，读者会读成矛盾。
- **逐帧 pool vs 每人 p95 型混用**：本题无此结构（无逐帧数据），**NOT-APPLICABLE**：`data\` 里没有任何帧级/个体级数组，`results_*` 全是标量与组合级汇总。

### ② 倍数与百分数（同一现象两个分母）—— 命中

`alpha−`（×0.95）使 `k_required` n=2「掉 **68.97%**」：

- `out\02-solve.md` L195 印 `0.0105556 → 0.0032759`。
- 现场复算：`k_required_per_s["n=2"] = 0.010555555555555545`；`×0.95/1.05 = 0.0095503`；跌幅 `(0.95/1.05 − 1)×100 = **−9.5238%**`。
- `68.97%` 对应的是 `1/(1−α)−1` 在 α→1 的发散口径（`0.0105556 → 0.0032759` 是 `1/0.95 − 1` vs `1/1.05 − 1` 的比值），**不是同一量纲的跌幅**。两个分母混在一句话里。
- 对照可复算的正例：`eps_rel` 保持区间「宽 105.42%」→ `(0.065646−0.012934)/0.05 = 105.424%` ✅。

### ③ 多重比较 —— 命中（无任何校正）

| 组 | 检验数 | 显著数 | 校正 |
|---|---|---|---|
| Q1 trend | 12 | 10 | 无 |
| Q2 trend | 19 | 19 | 无 |
| Q3 diff | 9 | — | 无 |
| **合计** | **40** | — | **无 BH / 无 Bonferroni / 无 q 值** |

- 全项目 `grep -i 'Bonferroni|BH|FDR|多重比较|q ?值'` 只在 `out\01-model.md:176` 命中一次，且说的是别的事（「不是用来做闭合校正」）。
- 扫 `results_q1..q4` 全部键名，**没有任何 `p` / `q` / `fdr` / `adj` 类键**（命中的 `k_par`、`phi`、`path_diff` 等均非检验统计量）。→ 40 个判定共用同一个 `eps_rel=0.05`，无族错误率控制，也**没有 p 值可用来事后校正**。这不是「应加校正」的建议，是「该结论在多重比较下不可复算」。

### ④ 图表刻度 —— 无法测量（三重阻塞）

`mmkit` 未安装（`ModuleNotFoundError`）、无 `main.pdf`、`figures\` 为空且无 `code\make_figures.py`。派单要求的「有效字号 < 6 pt 用 figfont 量」本次做不到。**NOT-APPLICABLE（工具与产物双缺）**，不构成对论文的指控，但也不构成放行。

---

## 6 结论

### 6.1 三选一

**`存在 2 个不可复算`**：S1（`q1` median_ms 印 156.304，当代 157.518）、S2（`q1` 占端到端印 74.2%，当代 54.71%）。其余 8 个抽样（S3、Q1–Q5、T1、T2）在快照数据上逐个复算通过。

### 6.2 必须同时记下的两层限制

1. **正文侧无被测对象**：`main.pdf` 不存在，`main.tex` 是 0 结果数字的骨架，`review\00-metrics.md` 基线缺失。本报告的 10 个抽样取自 `out\02-solve.md`（待印数字），**不是从 PDF 正文抽的**——「正文数字可复算」这件事目前无法被证明，也无法被否证。
2. **`verify_numbers.py` 的 PASS 不等于数字对**：`failures=0` 的构成为 `None 396 + [] 6 + deferred 142 + bound 0`；written 态实测 `bound=57 / unbound=85`；覆盖仅 13.2%；另有 6 条恒真断言（含 1 条永不失败）。**这个脚本能证明「JSON 里的键等于 JSON 里的键」，不能证明「论文里印的数等于数据」。**

### 6.3 三个真缺陷（按严重度）

| 级 | 缺陷 | 证据 | 修法方向 |
|---|---|---|---|
| 高 | needle 精度（2 位小数）粗于印刷精度（3–4 位有效数字），written 态 85/142 绑不上 | §4.4，`main_synth.tex` 实验 `bound=57 unbound=85` | needle 用与正文同精度的写法，或改「数值区间匹配」而非字面匹配 |
| 高 | 摘要耗时占比随一次重跑漂移 19.5 pp，且无任何机制报警 | §3.3-S1/S2，timing `1366E01311F0→787B7FFBBDD4` | 摘要数字必须由 `s3_deliver.py` 与正文同批生成；占比固定分母（五问之和）并给出 CV |
| 中 | 6 条空 needle 静默消失 + 6 条恒真断言（`:624` 永不失败） | §4.1、§4.2 | 空 needle 计 `UNCOVERED` 而非 `None`；`expected` 不得取自被检对象 |
| 中 | 40 个检验无多重比较校正、无 p 值产物 | §5-③ | 输出 p 值键，给 BH 后 q 值 |

### 6.4 官方判据的适用性（不许假借）

`E:\数学建模\APMCM-PROBLEMS\_official_criteria.json` 12 条：`C1-cycle / C2-choice / C3-naming / C4-frontmatter / C5-header / C6-pagelimit / C7-english / C8-refs / C9-appendix / C10-award-ratio / C11-disqualify / C12-ai`。

**C1–C12 没有一条要求「正文数字必须可复算」**（全是格式/流程/页数/语言/参考文献/附录项）。所以本报告的判据是**自设标准「可复算性」**，不挂 C 编号。唯一可引的是 **C9-appendix**（`n_hits=16`，`2017_APMCM_Essay_format_and_submission_specifications.txt:122` 要求附录列出软件名与全部源码）——因为「附录无源码 = 无法复核结果」正是它的原话理由，与本报告的关切同向。本工作区 `tables\`、`figures\` 为空、无附录产物，若定稿也如此，则 C9 会独立命中，与本报告的数字结论无关但需另行处理。

### 6.5 复算总命令（别人拿同一份快照可重跑）

```powershell
$SNAP = 'C:\Users\29900\AppData\Local\Temp\num_snap_181851'
cd $SNAP
Get-FileHash results_*.json,ledger.json -Algorithm SHA256 | ForEach-Object { "$($_.Hash.Substring(0,12))  $($_.Path)" }
E:\Mini\envs\mathmodel\python.exe -c "import json;d=json.load(open('results_timing.json',encoding='utf-8'));c={x['name']:x for x in d['calls']};print(c['q1']['median_ms'],c['pipeline_q1_to_q5']['median_ms'],100*c['q1']['median_ms']/c['pipeline_q1_to_q5']['median_ms'])"
```

冻结副本复跑 verify_numbers：

```powershell
cd C:\Users\29900\AppData\Local\Temp\num_run
E:\Mini\envs\mathmodel\python.exe code\verify_numbers.py
```

VERDICT: FAIL
