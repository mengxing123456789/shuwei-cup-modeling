BYTES 24270

# 08-figures：PRACTICE_2023B 图表清单与自检

> 判据一句话：PDF 自己的 MediaBox 才是版面。16 张图统一 416.5 pt 宽（5.784722 in × 72）；`apmcmthesis.cls:52` 的 geometry 给出 `\textwidth` ≈ 415.0 pt，按 `width=\linewidth` 放置时缩放 0.9964（最小字号 6.30 → 6.28 pt，仍在 6.0 判据之上）。
> 本文件不重算任何数值：所有读数都来自 `data/results_*.json` 的存储值，脚本只做展示格式化；键路径前缀 `q1:` = `data/results_q1.json`，`q2:`/`q3:`/`q4:`/`q5:`/`bnd:`/`pert:`/`tim:` 同理。

- 图 16 张、文件 32 个；`figures/` 内只有这 32 个文件（无 manifest、无中间产物）
- 宽 416.5 pt（全 16 张）、高 176.4–396.0 pt
- 最小字号 6.30 pt（fig13、fig16）；全库没有 <6.0 pt 的 span（连对数轴的单字符上标也没有，fig02 的刻度已显式写成 `0.1/1/10`）
- 全部文字 span 距页边 ≥2.0 pt（最紧是 fig16 的 x1=410.9，距右边 5.6 pt）
- 连续两次全量重跑，16 个 PDF 与 16 个 PNG 的 sha256 全同
- 出图解释器 `E:\Mini\python.exe`（3.14.6 / matplotlib 3.11.2）；判据解释器 `E:\Mini\envs\mathmodel\python.exe`（pymupdf）

## 1 清单

| # | 文件（`figures/`） | 论文节 | 高 pt | pdf B | png B | sha256 pdf / png（前 16 位） |
|---|---|---|---|---|---|---|
| 01 | `fig01_q1_product_yields.pdf` | Q1 | 313.2 | 18199 | 126536 | `7EB060B878B1598B` / `5C1EE9DFDF92B894` |
| 02 | `fig02_q1_span_noise.pdf` | Q1 | 183.6 | 16852 | 43455 | `CB807DAA38EF73FC` / `02E9083AA0C04FDE` |
| 03 | `fig03_q1_ilr_fit.pdf` | Q1 | 176.4 | 16530 | 48285 | `9DFB56E60C6700AE` / `A822F7F6F5FF8CBD` |
| 04 | `fig04_q2_major_abs.pdf` | Q2 | 205.2 | 16538 | 110243 | `153B9FBAB91542E5` / `67088EC45EFB26B0` |
| 05 | `fig05_q2_major_phi.pdf` | Q2 | 205.2 | 14031 | 87519 | `64D94AE770F454CB` / `121A60B32042C2D3` |
| 06 | `fig06_q2_minor_phi.pdf` | Q2 | 212.4 | 15279 | 74752 | `054456859CCA2299` / `FBA87B098B98C1E2` |
| 07 | `fig07_q2_bridge.pdf` | Q2 | 216.0 | 15660 | 83655 | `8F5689FB52C3CD02` / `01D2B7D137CCA30C` |
| 08 | `fig08_q3_product_delta.pdf` | Q3 | 302.4 | 17047 | 134060 | `83615F5ABC0FB78E` / `A9870B1C5B43DA13` |
| 09 | `fig09_q3_gas_ratio.pdf` | Q3 | 219.6 | 14936 | 81397 | `4C7379D23FB901C6` / `9205633D6BA87AE4` |
| 10 | `fig10_q4_selectivity.pdf` | Q4 | 194.4 | 12698 | 37731 | `B0C5D1B958EDCBDA` / `016B946809874B70` |
| 11 | `fig11_q4_carbon.pdf` | Q4 | 187.2 | 13743 | 93390 | `BACB78E28C070A8A` / `BF26517FA5B9F6E6` |
| 12 | `fig12_q4_ridge.pdf` | Q4 | 219.6 | 17212 | 73013 | `6E469136F1C11619` / `9B143956FEA57959` |
| 13 | `fig13_q5_predictions.pdf` | Q5 | 396.0 | 25338 | 275069 | `603F947A9A571F2F` / `D87D88D33A289FDB` |
| 14 | `fig14_q5_loo.pdf` | Q5 | 194.4 | 13728 | 48592 | `3E4F9AAF77F758D6` / `4E47AC6CA0853BF8` |
| 15 | `fig15_q5_support.pdf` | Q5 | 183.6 | 16504 | 50908 | `51BBE37A18AB167F` / `6526A2668217DCDC` |
| 16 | `fig16_validation.pdf` | 验证 | 198.0 | 17228 | 91599 | `2BB8E304E18D8BAC` / `E4CC971B214C4936` |

PNG 全部 1735 px 宽（416.5/72 × 300 dpi，取整），与 PDF 一一对应。

## 2 复跑

```powershell
& "E:\Mini\python.exe" -X utf8 code\make_figures.py                      # 全量 16 张
& "E:\Mini\python.exe" -X utf8 code\make_figures.py --list                # 列 id
& "E:\Mini\python.exe" -X utf8 code\make_figures.py --only fig05          # 单图
& "E:\Mini\python.exe" -X utf8 code\make_figures.py --only fig04,fig05    # 多图（逗号分隔）
& "E:\Mini\envs\mathmodel\python.exe" -X utf8 code\check_figures.py       # 判据自检
```

- 单图实测：`--only fig16` → `[done] 1 figure(s)`；`--only fig04,fig05` → `[done] 2 figure(s)`
- 可重跑：`save()`（`code/make_figures.py:195-208`）把 PDF 的 `Creator` 固定为 `code/make_figures.py`、`CreationDate`/`ModDate` 置空，所以同一份 JSON 重跑字节稳定
- 只读：脚本只 `json.loads` 读 `data/results_*.json`，不写 `data/`、不碰 `main.tex`
- 解释器分歧：`E:\Mini\envs\mathmodel\python.exe` 在本机一执行 `fig.savefig` / `fig.canvas.draw()` 即崩（退出码 `-1066598273` = `0xC06D007F`，stdout/stderr 全空、无 traceback，空 figure 同样崩；把 `Library\bin` 前置到 PATH 也不解决）。因此数值由 mathmodel 解释器算，图由 `E:\Mini\python.exe` 出、判据也由它读——`check_figures.py` 反过来用 mathmodel 解释器里的 pymupdf，两套环境各干各的

## 3 逐图

### fig01 · `fig01_q1_product_yields`
- **画面**：2×2 四面板，每个面板一种产物（Tar/Water/Char/Syngas），横轴 `w (-)` 0–0.5，纵轴 `Yield (wt.%)`；三种颜色 + 三种实心 marker 区分为 CS/CE/LG，**每个面板各自一根产量轴**（量程不同，未共享）；图例在坐标区外底部。
- **读数**：CS Tar 19.46→12.13（span 7.33，单调降）；CS Water 26.84→31.02（span 4.18）；CS Char span 仅 0.76 且非单调；CE Tar 34.42→45.28（span 10.86，非单调）；CE Water 27.42→16.14（span 11.28，第 6 个水平回升到 18.25，1 次变号）；LG Tar 18.06→8.19（span 9.87）；LG Char 58.17→57.43（span 1.19，全组最平）。出处 `q1:combos.{CS,CE,LG}.products.{Tar,Water,Char,Syngas}.{y,first,last,span,monotone}`。
- **Caption**：`Product yields (wt.\%) of the three mixtures against the ash-to-biomass ratio $w$: Tar, Water, Char and Syngas. Each panel keeps its own yield axis; colour and marker identify CS, CE and LG, and the lines pass through the stored Annex~I levels.`
- **源**：`code/make_figures.py:214`；数据 `q1:combos.*.products.*`

### fig02 · `fig02_q1_span_noise`
- **画面**：横向点图，4 个产物作分类轴、三种组合上下错开；横轴是对数轴（0.1/1/10 三档刻度），竖虚线在比值 1 处标注噪声底。
- **读数**：12 条产物序列中 10 条 >1.3×噪声底；最高 LG Tar 8.7、CE Water 5.9、CS Tar 5.0；只有 CS Char 0.3、LG Char 0.2 落在噪声底以下，CE Char 1.4 贴着底线。出处 `q1:combos.*.products.*.span_over_thr`。
- **Caption**：`Observed end-to-end span of each product series divided by the Monte-Carlo noise floor, on a log axis; the dashed line at 1 is the noise floor itself. Points left of the line move less across the whole level range than the surrogate noise does.`
- **源**：`code/make_figures.py:246`；数据 `q1:combos.*.products.*.span_over_thr`

### fig03 · `fig03_q1_ilr_fit`
- **画面**：3 组两根柱（拟合残差 σ 与 MC 噪声底 σ），柱顶标 σ 的 3 位小数，组上方标 F；图例两项在底部。
- **读数**：CS σ_fit 0.0333 < σ_noise 0.0502（F 0.44，`q1:combos.CS.ilr.lack_of_fit_verdict` 判「残差在 5% 噪声可解释范围内」）；CE 0.0929（F 3.42）、LG 0.0941（F 3.52）均判「存在系统性失拟」。CS 的 ILR 三轴 R² 为 0.977/0.909/0.564、选定 `M3_sqrt_w`；CE/LG 选 `M2_linear_logw`（`q1:combos.*.aic_best`）。
- **Caption**：`ILR fit residual $\sigma$ against the Monte-Carlo noise floor for the three mixtures; the number above each pair is the lack-of-fit $F$ and the number on each bar is the stored $\sigma$. Bars are grouped, not stacked.`
- **源**：`code/make_figures.py:286`；数据 `q1:combos.*.ilr.{sigma_fit,sigma_noise_mc,lack_of_fit_F}`

### fig04 · `fig04_q2_major_abs`
- **画面**：1×3 面板（CS/CE/LG），纵轴 `Yield (mL/g daf)`、横轴 `w (-)`；每个面板只画该组合「绝对量级」标号的物种（CS：H2/CO/CO2/CH4；CE：H2/CO/CO2/C2H6；LG：CO/CO2/CH4），五条图例是并集，未出现的物种在该面板没有线。
- **读数**：CS H2 6.48→43.62（span 37.14，CS 内最大）；CE H2 26.60→57.90（span 39.20）；LG 的绝对增长在 CO2（24.35→43.56，span 19.21），CO/CH4 只到 5.7/6.2。出处 `q2:combos.*.gases.*.{z,span,tier}`。
- **Caption**：`Absolute gas yields of the major species (mL/g daf) against $w$; each panel draws only the species assigned to the absolute tier for that mixture, so the shared five-entry legend is a union rather than a per-panel inventory.`
- **源**：`code/make_figures.py:322`；数据 `q2:combos.*.gases.*`

### fig05 · `fig05_q2_major_phi`
- **画面**：与 fig04 同三面板、同物种，纵轴换成摩尔分数 `φ (-)`，固定 0–1 量程（未按数据自适应）。
- **读数**：CS CO2 峰值 φ 0.5023 出现在 0/100；CE H2 峰值 0.8379 在 80/100，是全图最高占比；LG CO2 峰值 0.4575 在 100/100、CH4 0.4069 在 50/100。出处 `q2:combos.*.gases.*.{phi,argmax_label}`。
- **Caption**：`Mole fractions $\varphi = z / \sum z$ of the same major species, on a fixed 0--1 axis, so panel heights are comparable across mixtures.`
- **源**：`code/make_figures.py:349`；数据 `q2:combos.*.gases.*.phi`

### fig06 · `fig06_q2_minor_phi`
- **画面**：1×3 面板，纵轴对数（只标 0.001 与 0.01 两档），画「相对量级」标号的物种；CS 面板 5 条、CE 面板 1 条（CH4）、LG 面板 2 条（H2、C2H6），图例 7 项并集。
- **读数**：CE CH4 0.0421（20/100）是最大 minor，仍比 CE H2 的 0.8379 低一个半数量级；CS C3H8 升到 0.0060（80/100）、C4H10 0.0042 且在 40/100 有驼峰；LG C2H6 仅 0.0012（50/100）、LG H2 0.0099（80/100）。出处 `q2:combos.*.gases.*.{phi,tier,argmax_label}`。
- **Caption**：`Mole fractions of the minor species on a log axis; the minor tier is mixture-specific, so a panel can hold a single line (CE: CH$_4$ only) and the seven-entry legend is a union.`
- **源**：`code/make_figures.py:377`；数据 `q2:combos.*.gases.*`

### fig07 · `fig07_q2_bridge`
- **画面**：散点图，横轴 `Annex I syngas (wt.%)`、纵轴 `Annex II gas mass (wt.%)`；灰虚线是 1:1 闭合线，三种颜色区分组合，框内文字给出 β 区间。
- **读数**：β = y/x 的区间 CS 0.570–0.713、CE 0.147–0.500、LG 0.849–1.246；CE 整段落在 1:1 线下方，CS 也整体偏低，LG 跨线而不过原点。结论：两本附录取的不是同一套量纲，β≠1 是口径差，不应被当作闭合修正系数使用。出处 `q2:bridge.*.beta_bridge`。
- **Caption**：`Annex~II gas mass against Annex~I syngas mass at each level; the dashed line is 1:1. $\beta$ is the per-mixture range of $y/x$; points below the line mean the two annexes do not report the same quantity, so the gap is a caliber difference rather than a closure error to be rescaled away.`
- **源**：`code/make_figures.py:408`；数据 `q2:bridge.*`

### fig08 · `fig08_q3_product_delta`
- **画面**：2×2 面板，纵轴 `Δ yield (wt.%)`，灰带是逐水平 `±thr` 的噪声带（虚边填充、无 hatch），零线细实线；面板标题带「n/n beyond band」计数。
- **读数**：Tar 均值 +30.78、8/8 超带；Char −33.27、8/8 超带（CE 的炭产量系统性低于 LG）；Water −1.17、6/8 超带且 1 次变号（带基本罩住）；Syngas +3.66、7/8。出处 `q3:products.*.{mean_Delta,n_exceed,n,sign_changes,thr_diff}`。
- **Caption**：`CE minus LG product yield at equal ash level, with the per-level $\pm$ noise band as a grey ribbon; the title of each panel gives how many levels fall outside that band.`
- **源**：`code/make_figures.py:450`；数据 `q3:products.*`

### fig09 · `fig09_q3_gas_ratio`
- **画面**：单面板折线，横轴为 5 个等灰位 `20/100…100/100`，纵轴 `CE / LG ratio (-, log)`，点线在比值 1 处标 parity。
- **读数**：H2 39.7–81.2、C2H6 48.6–172.5（CE 高出一到两个数量级）；CO 0.253–0.900、CO2 0.046–0.768、CH4 0.023–0.116（CE 反而低一到两个数量级）。5 个物种里只有 CO 是 4/5 超带，其余 5/5。出处 `q3:gases.*.{ratio_CE_over_LG,n_exceed,n}`。
- **Caption**：`CE/LG yield ratio of each gas at equal ash level, log axis; the dotted line is parity. Values above 1 mean CE yields more of that species at the same ash level, and the split is species-dependent rather than a single scale factor.`
- **源**：`code/make_figures.py:483`；数据 `q3:gases.*`

### fig10 · `fig10_q4_selectivity`
- **画面**：4 个产物 × 3 组合的分组柱，纵轴 `γ (-)`，零线可见（正负都画），Σγ=0 由中心化保证。
- **读数**：CS Tar −0.826 / Water +0.397 / Char +0.148 / Syngas +0.281；CE Tar +0.750 / Water −0.727 / Char +0.340 / Syngas −0.363；LG Tar −1.581 / Water +0.956 / Char +0.055 / Syngas +0.569。三组的符号组合各不相同，说明选择性方向随原料而反转。出处 `q4:selectivity.*.gamma_centered`。
- **Caption**：`Centred log-selectivity $\gamma = \mathrm{d}\ln S_p/\mathrm{d}w$ of each product, with $\sum_p \gamma_p = 0$ by construction; a positive bar means that product's share grows with $w$.`
- **源**：`code/make_figures.py:520`；数据 `q4:selectivity.*.gamma_centered`

### fig11 · `fig11_q4_carbon`
- **画面**：1×3 面板，纵轴 `nC (mmol/g daf)`（各面板量程不同），首水平以虚横线作基线，标题写存储的端到端变化。
- **读数**：CS −2.3%（−0.1227 mmol/g，非单调）；CE −77.2%（−2.1772，单调）；LG +40.1%（+1.2071，单调）。CE 的碳收率随灰位塌掉近八成，LG 则反向上升。出处 `q4:carbon_balance.*.{delta_end,delta_end_pct,monotone}`。
- **Caption**：`Gas-phase carbon $n_C$ (mmol/g daf) against $w$, with the first level drawn as a dashed baseline; the title of each panel carries the stored end-to-end change. Panel ranges differ, so compare slopes rather than heights.`
- **源**：`code/make_figures.py:554`；数据 `q4:carbon_balance.*`

### fig12 · `fig12_q4_ridge`
- **画面**：单面板折线 + 点，横轴 `Ea (kJ/mol)` 100–260，纵轴 `log10 A (1/s)`；框内文字给出固定 kt 的条件。
- **读数**：16 个 (Ea, log10 A) 点，log10 A 从 3.751（Ea 100）到 13.545（Ea 250）；它们共同满足 n=1 时 kt = 2.996（1800 s、800 K）：Ea 从 100 涨到 250 kJ/mol，A 必须同步涨到 10^13.5 才补得回来，所以单温数据分不开 Ea 与 A（n 的混淆度 6.34）。出处 `q4:kinetics.{ridge_n1,kt_required,k_required_per_s,n_order_confounding}`。
- **Caption**：`Compensation ridge for fixed reaction order $n = 1$: each point is an $(E_a, A)$ pair that reproduces $kt = 2.996$ at 1800 s and 800 K, so the line is an iso-conversion locus rather than a fit to rate data.`
- **源**：`code/make_figures.py:581`；数据 `q4:kinetics.*`

### fig13 · `fig13_q5_predictions`
- **画面**：3×4 面板（行=组合、列=产物）；空心圆是 Annex I 观测，实线是预测均值，灰带是 5–95% 区间（虚边）；行/列身份都写在面板标题里（`CS · Tar` 形式），左侧不出行标；图例三项在底部。
- **读数**：预测网格是 7 个 `w`（0.1304–0.4737，来自 `q5:meta.grid_w`，不是观测的 9/8 个水平），所以观测点与均值线不逐点重合；带子的相对宽度与 fig14 一致，CS 最窄（LOO 0.9–5.5%）、CE/LG 明显更宽（最高 18.7%）。出处 `q5:combos.*.{point,lo,hi}`。
- **Caption**：`Prediction grid: open circles are Annex~I observations, the solid line is the predictive mean and the grey ribbon the 5--95\% interval; rows are mixtures and columns products, and the grid holds seven query levels rather than the observed ones.`
- **源**：`code/make_figures.py:616`；数据 `q5:combos.*`、`q5:meta.grid_w`

### fig14 · `fig14_q5_loo`
- **画面**：4 产物 × 3 组合的分组柱，纵轴 `LOO RMSE (%)`，横向虚线标 5%。
- **读数**：12 格里 8 格在 5% 线之上：CE Water 18.71 最高，LG Tar 17.08、LG Syngas 12.40、LG Water 6.92、CE Tar 6.34、CE Char 6.03、CE Syngas 6.00、CS Tar 5.50；线下是 CS Water 1.37、CS Char 0.89、CS Syngas 4.91、LG Char 1.53。与 fig03 的失拟结论一致：CE/LG 的区间更宽。出处 `q5:combos.*.loo_rmse_rel`。
- **Caption**：`Leave-one-out relative RMSE per mixture and product, with the 5\% reference line; eight of the twelve cells sit above it, and the CE/LG cells are the ones that do.`
- **源**：`code/make_figures.py:668`；数据 `q5:combos.*.loo_rmse_rel`

### fig15 · `fig15_q5_support`
- **画面**：三行（LG/CE/CS），每行一条粗半透明支撑段（标定区间 `w_min–w_max`）、灰点（支撑内查询水平）、橙三角（观测水平正好落在支撑边缘）、红叉（越界外推），竖点线标预测网格的 7 个水平。
- **读数**：CS 支撑 0–0.5、1 个边缘点、4 个外推点；CE/LG 支撑 0.0909–0.5、各 2 个边缘点、各 4 个外推点；拓宽网格与观测网格重叠处的预测最大差 0.0（同点同值，说明网格换算是干净的）。外推延伸到 w=0.75。出处 `bnd:combos.*.{w_min,w_max,n_boundary_star,n_extrapolation_star2,max_abs_diff_on_overlap,rows}`。
- **Caption**：`Calibration support against the widened query grid: the thick translucent segment spans the $w$ range covered by Annex~I, grey dots are query levels inside it, triangles mark an observed level that coincides with the support edge, and crosses are the extrapolated levels. Dotted verticals mark the seven levels of the prediction grid.`
- **源**：`code/make_figures.py:703`；数据 `bnd:combos.*`、`q5:meta.grid_w`

### fig16 · `fig16_validation`
- **画面**：两面板。(a) 横向条形计数（4 类），条形末端标数值；(b) 对数横轴点图，9 个调用各一个点并在右侧标中位毫秒数。
- **读数**：(a) 42 次扰动：never read 12、query move 14、model feasible 15、model infeasible 1——后两类合计 16 次模型实跑，其中 15 次落在可判分母里、1 次发生翻转。 (b) selftest 15.06、load Annex I 1.72、load Annex II 1.894、Q1 189.7、Q2 1.228、Q3 0.226、Q4 0.255、Q5 68.1、Q1–Q5 pipeline 254.6 ms。出处 `pert:meta.counts`、`tim:calls`。
- **Caption**：`(a) Outcomes of the 42-run perturbation audit, counted by class; (b) median wall time of five serial repetitions per call, log axis, with the median printed beside each point.`
- **源**：`code/make_figures.py:759`；数据 `pert:meta.counts`、`tim:calls`

## 4 硬要求逐条对账

| 规则 | 本项目的做法 | 证据 |
|---|---|---|
| ① MediaBox 是判据 | 全 16 页 W=416.5±0.05；逐 span 比 `page.rect`，左右上下各留 2.0 pt | `code/check_figures.py:87`；判据表见下 |
| ② 6 pt 硬线 | 全局字号 6.8/7.2/7.4/7.8，紧凑图 6.3/6.5；最小 6.30 | `code/make_figures.py:80-95`；`gate_g6` 的 `min_pt=6.30@fig13` |
| ③ 长 ylabel 竖排会上下裁 | ylabel 一律短式：`Yield (wt.%)`、`φ (-)`、`Δ yield (wt.%)`、`γ (-)`、`nC (mmol/g daf)`、`log10 A (1/s)`、`LOO RMSE (%)` | 判据表 `y0/y1` 列，全部 ≥16.6 且 ≤H−8.6 |
| ④ 同轴同量纲 | 产量 wt.%、气体 mL/g daf、φ 无量纲、碳 mmol/g 分面板；比值与百分比各自成图 | fig04/05/06/11 各自一根轴；fig14 只画 % |
| ⑤ 图例不进坐标区 | 全部图用 `fig.legend(loc="lower center", bbox_to_anchor=(0.5, 0.020), frameon=False)`，底部留 0.155–0.275 | `code/make_figures.py:163-170` |
| ⑥ sharey 陷阱 | 无 `sharey=` 参数、无 `set_yticks([])`；多面板各自刻度（`sharey` 只出现在 `:16` 的约定注释里） | `grep -c "sharey="` = 0 |
| ⑦ hatch 污染 bboxlog | 全脚本无 `hatch=`；带边用 `fill_between` + 虚线描边 + `alpha=0.16`，虚线用 `linestyle=(0,(2.2,1.4))` | `grep -c "hatch="` = 0 |
| ⑧ 出图换解释器 | 出图 `E:\Mini\python.exe`；判据 `E:\Mini\envs\mathmodel\python.exe`；两次全量重跑 0 崩溃 | §2 命令；重复运行 sha256 全同 |

判据表（`code/check_figures.py` 输出，末行 `[PASS]`）：

```
figure                                      W      H min_pt    x0     x1    y0     y1 spans
fig01_q1_product_yields                 416.5  313.2   6.80  14.1  406.9  20.1  304.2    37
fig02_q1_span_noise                     416.5  183.6   6.80  31.5  390.0  17.0  177.2    14
fig03_q1_ilr_fit                        416.5  176.4   6.50  15.9  375.1  17.7  170.1    22
fig04_q2_major_abs                      416.5  205.2   6.80  18.2  387.2  20.1  198.3    44
fig05_q2_major_phi                      416.5  205.2   6.80  11.7  387.2  20.1  198.3    36
fig06_q2_minor_phi                      416.5  212.4   6.80   8.7  387.2  23.3  205.4    29
fig07_q2_bridge                         416.5  216.0   6.60  18.2  401.5  18.4  208.9    22
fig08_q3_product_delta                  416.5  302.4   6.80   8.4  404.9  20.6  293.6    38
fig09_q3_gas_ratio                      416.5  219.6   6.80   7.6  404.9  20.0  212.5    19
fig10_q4_selectivity                    416.5  194.4   6.80   8.3  369.9  16.6  187.8    15
fig11_q4_carbon                         416.5  187.2   6.80  11.6  397.6  17.5  167.4    36
fig12_q4_ridge                          416.5  219.6   6.50  22.4  405.5  18.9  205.7    19
fig13_q5_predictions                    416.5  396.0   6.30  10.4  395.4  18.1  385.3    83
fig14_q5_loo                            416.5  194.4   6.80   9.7  369.9  16.6  187.8    19
fig15_q5_support                        416.5  183.6   6.80  28.4  372.0  17.0  177.2    16
fig16_validation                        416.5  198.0   6.30  11.3  410.9  19.1  181.8    38
```

判据之外另做了两项程序化复核，都是为了让 caption 不写图上没有的东西：

- 文本重叠探针（逐对 span 的 bbox 交并比，阈值 12% 取小框面积）：16 张 PDF 全部 0 对重叠，说明刻度标签、注释、图例没有互相压字
- 文案抽取：fig03 的 `0.033/0.093/0.094/0.050` 与 `F = 0.44/3.42/3.52`、fig08 的 `8/8、6/8、8/8、7/8`、fig16 的 `12/14/15/1` 与 `15.06…254.6` 都能从 PDF 里原样抽回；非 ASCII 字符只有 `± · Δ Σ β γ σ φ −`，没有缺字方框

## 5 与 03-numbers 对账

- `out/03-numbers.md:9-10` 记 claims=547、checked=547、JSON 侧 547 通过 0 失败；本文件的每个读数都落在它的键路径集合内，没有新增派生量
- 图内文字是 JSON 存储值的展示格式化：σ 取 3 位小数（0.0332594 → `0.033`）、F 取 2 位（3.42323 → `3.42`）、时间取 4 位有效数字（254.609 → `254.6`）。论文正文引用时按 `03-numbers.md` 的 DERIVED 表取位数，不要照抄图上的短式
- `out/03-numbers.md:12` 记 `main.tex` 仍是 skeleton：图目前没有被正文引用。G6 已按库里的 `pipeline.gate_g6(Path("E:\数学建模\PRACTICE_2023B"))` 实跑，返回 `ok=True`、`figures pdf=16 png=16 min_pt=6.30@fig13_q5_predictions.pdf`（`code/make_figures.py:80` 的 rcParams 决定这个下限）；撰写手插图后 G6/G11 需要重跑
- 本文件不引入任何新结论：fig07 的 β≠1、fig03 的失拟、fig14 的超 5% 都是 JSON 里已有的判据值（`lack_of_fit_verdict`、`beta_bridge`、`loo_rmse_rel`）

## 6 已知限制

- 复核方式是程序判据 + 文案抽取，没有做像素级的审美判断；图看起来「好不好看」不在本轮判据里
- fig13 的 CE·Water 面板刻度是 20.0–30.0（一位小数），fig11 的三个面板量程不同；若要统一位数或统一量程，改 `code/make_figures.py` 对应 `set_yticks` 后重跑，判据会自动复检
- 对数轴共 4 处（fig02、fig06、fig09、fig16b），刻度只标主档，读者按主档读
- fig15 的粗线段是 `lw=6.0` 的半透明线而不是填充带，caption 里写的是 segment
- fig07 的 β 是逐水平 y/x 的区间，不是拟合斜率；区间端点来自 `q2:bridge.*.beta_bridge`，图上文字做了两位小数截断
- 全文图内无中文（论文是英文稿），若改中文稿需换字体并重跑判据

## 7 交接给撰写手

- 16 个 `\includegraphics[width=\linewidth]{figures/figNN_xxx.pdf}`；文件名见 §1，编号 fig01–fig16 与本章小节一一对应
- caption 直接用 §3 的字符串（已按 LaTeX 转义 `\%`、`$w$`、`$\varphi$`）；`\label{fig:qN_xxx}` 自取
- 正文引用图内数字时走 `out/03-numbers.md` 的 DERIVED 表位数，不要用图上的截断值
- 若插图后 `main.tex` 出现第一个结果数字，`03-numbers.md` 的 145 条 needle 缓期立即作废，需重跑 `verify_numbers.py`
- 需要单图返工时：`--only figNN` 只重画那一张，其余 PDF 的 sha256 不变

VERDICT: PASS