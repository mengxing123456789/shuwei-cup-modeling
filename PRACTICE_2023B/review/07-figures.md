BYTES 19810

# 07 · 图表审读：六范式逐图判（fig01–fig16）

## 0. 快照与机器口径（动手读图之前先跑的三条）

被测件目录 **没有 main.pdf**（`Test-Path E:\数学建模\PRACTICE_2023B\main.pdf` = False），所以前两条机器口径按"缺件"失败，第三条改按"逐图 PDF"跑：

```
$env:PYTHONPATH='E:\数学建模\.agents\skills\mathmodeling\scripts'
& 'E:\Mini\envs\mathmodel\python.exe' review_check.py   'E:\数学建模\PRACTICE_2023B'
  pdf: None   pages: 0
  [FAIL] X-pdf 找不到 PDF
  VERDICT: FAIL  (fail=1 unknown=0)          exit=1

& 'E:\Mini\envs\mathmodel\python.exe' gauntlet_check.py 'E:\数学建模\PRACTICE_2023B'
  [FAIL] paper resolved E:\数学建模\PRACTICE_2023B <- 草稿（main.pdf 不存在或 < 150 KB）
  [FAIL] main.pdf exists   run gauntlet.build() or xelatex first
  0/2 PASS                                    exit=1

& 'E:\Mini\envs\mathmodel\python.exe' -m mmkit.figfont figures\fig01..fig16.pdf
  16/16 PASS；violations (>= 3 chars and < 6.0 pt) = 0
  最紧一张 fig13：spans=83 min=6.3 pt median=6.3 pt   PASS
  （fig13 / fig15 在 21:30:45 重跑后的 PDF 上复测：fig13 83 spans / 6.3 pt，fig15 16 spans / 6.8 pt，结论不变）
```

缩放口径：apmcmthesis.cls:52 `\geometry{top=25.4mm,bottom=25.4mm,left=31.8mm,right=31.8mm}`，A4 版心宽 210−63.6 = 146.4 mm = **415.03 pt**；16 张图的 MediaBox 一律正好 **416.50 pt**（5.7847 in），`width=\linewidth` 实际缩放 415.03/416.5 = **0.9964**，最小有效字号 6.3 × 0.9964 = **6.277 pt**，过 6.0 的门槛只余 0.28 pt。

## 1. 基线：00-metrics.md 不存在，本表由我现场重建

派单脚本没有生成 `review\00-metrics.md`（`Test-Path` = False）。"唯一基线"因此由本报告重建；别人按同样命令可得同表（size/mtime 用 `Get-Item`，hash 用 `Get-FileHash -Algorithm SHA256`，取前 16 位）：

| 文件（相对 PRACTICE_2023B） | 字节 | mtime | sha256前16 |
|---|---|---|---|
| main.tex | 4546 | 11-19 16:49:15 | 2cc0e46029bbdec6 |
| code/make_figures.py | 30468 | 11-19 21:29:49 | 7a4f4e6ec3a5a023 |
| code/solve.py | 23518 | 11-19 17:30:42 | bdd5474850893f47 |
| out/08-figures.md | 24270 | 11-19 21:30:24 | 4c5580f9aad39aa1 |
| data/results_q1.json | 15970 | 11-19 18:26:41 | 853fb6bdd14fa182 |
| data/results_q4.json | 5245 | 11-19 18:26:41 | 3714fe375a219c12 |
| data/results_q5.json | 10363 | 11-19 18:26:41 | 93f88d016a03ea11 |
| data/results_timing.json | 2296 | 11-19 18:26:45 | 6a6875466ce0f376 |
| data/results_perturb.json | 37088 | 11-19 18:26:55 | 878111bfa5c0fe57 |
| figures/fig10_q4_selectivity.pdf | 12698 | 11-19 21:30:45 | b0c5d1b958edcbda |
| figures/fig13_q5_predictions.pdf | 25338 | 11-19 21:30:46 | 603f947a9a571f2f |
| figures/fig15_q5_support.pdf | 16504 | 11-19 21:30:47 | 51bbe37a18ab167f |

**同代判定**：`data/*.json` 写于 18:26:41–18:26:55，`figures/*.pdf` 画于 21:30:45–21:30:5x，`code/make_figures.py` 改于 21:29:49，`main.tex` 停在 16:49:15。数据层比图**旧 3 h 04 min**，即图是最后一次求解之后重画的，不存在"拿旧数据画图"。真正落后的是正文：main.tex 仍是 106 行骨架（≈40 个 `<<...>>` 占位符，`grep -c includegraphics` = 0、`grep -c '\\caption'` = 0），**16 张图目前没有被正文引用**。

> R-V11：本报告是 2026-11-19 21:38 的快照。图与 data 在 21:29–21:31 之间被重跑过一次（我读代码时是 21:18 版，重跑后的 21:29:49 版对我引用的 11 处行号逐一复核，全部一致：43 / 237 / 345 / 401 / 501 / 578-579 / 656-658 / 721 / 739 / 748）。此后任何重跑，第 4、5 节的数字都要重算。

## 2. 六范式覆盖：命中 1 / 6

| 范式 | 张数 | 图号 | 判定 |
|---|---|---|---|
| 情景对比分组柱 | 3 | fig03、fig10、fig14 | 有；分组而非堆叠，形态正确 |
| 敏感性龙卷风 / 秩漂移 | 0 | — | NOT-APPLICABLE：无一张画 ±swing 条形或秩序变化 |
| Laffer / Pareto | 0 | — | NOT-APPLICABLE：无最优化峰值曲线，无累积份额前沿 |
| 雷达 | 0 | — | NOT-APPLICABLE：无多轴闭合图 |
| 热力图 | 0 | — | NOT-APPLICABLE：无 imshow/pcolor/hexbin（§2.1 说明代价） |
| 流程图 | 0 | — | NOT-APPLICABLE：无节点-箭头图（§2.2 说明代价） |

计数口径（可复算）：`Select-String code\make_figures.py -Pattern 'scatter|pie|imshow|pcolor|hexbin|hist2d|contourf|radar|patches\.'` → 只命中 `matplotlib.patches.Patch`（图例用），绘图调用只有 `plot / bar / barh / fill_between`，**没有一个是面积或极坐标编码**。

**2.1 热力图缺失的具体代价**：fig14 的 12 格 LOO 与 fig13 的 12 格带子宽度都是 3×4 矩阵（行=混合，列=产物）。分组柱只能读出"同一产物里谁高"，读不出"CE 整行比 CS 整行差一档"——而这正是 paper 要说的话。`fig14` 一眼能看出 CE 四格全在 5% 线之上，但那靠的是四根同色柱按列对齐，读者要自己拼。

**2.2 流程图缺失的具体代价**：fig16(b) 用 9 行点图标 5 段耗时，读者得自己算 Q1 189.7 ms 与 Q5 68.1 ms 各占五段中位之和 259.5 ms 的 73.1% 与 26.2%，而 Q2/Q3/Q4 合计 1.71 ms 只占 0.66%（分母用 259.5 而不是 pipeline 254.6，否则三项相加 101.9%，见 §3 的 fig16 行）。换成一张带耗时的流程图，顺序与预算一次读完，还省掉 9 行标签。

## 3. 逐图表（16 行）

| 图号 | 范式 | 误用类型 | 改法（改 caption / 重画） |
|---|---|---|---|
| fig01 | 六范式之外（2×2 多面板折线） | **口径命名错**：caption 把 w 叫 "ash-to-biomass ratio"，代码里是质量分数 a/(a+b)（"40/100"→0.2857=40/140，不是 0.4）；无 n（CS 9 档 / CE·LG 8 档）、无误差带 | 改 caption |
| fig02 | 六范式之外（比值点图；最接近"敏感性"但无 ±swing、无秩） | 12 个比值同时与 1 比，无 family-wise 说明；无 n_mc | 改 caption |
| fig03 | **情景对比分组柱** | F 无 df、无 α（df=21/21、18/18、18/18 可由 JSON 的 n_obs/k_par 推出，却没印）；solve.py:225 的"5%"是 eps_rel 测量噪声而非显著性水平；`ax.text(x, 0.111, f"F = …")` 固定 y（make_figures.py:305）而 CS 两根柱只到 0.0502 → 悬空浮字 | 改 caption（+ 把 F 挪到柱顶） |
| fig04 | 六范式之外（1×3 折线） | 三块共用零点但量程 0–60 / 0–60 / 0–40（make_figures.py:345 `set_ylim(0.0, None)` 逐面板自动），caption 只说图例是并集，没说高度不可跨面板比 | 改 caption（或重画 sharey） |
| fig05 | 六范式之外（1×3 折线） | caption 称 "the same major species"，实际每块都缺项（CS 无 C2H6、CE 无 CH4、LG 无 H2 与 C2H6）；φ=z/Σz 是体积份额，写成 mole fraction 需理想气体假设，caption 未写 | 改 caption |
| fig06 | 六范式之外（log 折线） | 3.9 个十进位只标 2 个刻度（0.001、0.01，make_figures.py:401-403），最大数据 0.042 落在无标签区；7 条图例对块内 1–5 条线 | 重画刻度 + 改 caption |
| fig07 | 六范式之外（散点 + 1:1） | 每混合只有 4 点，n 未标；点未标档位；2/3 画布空（数据全在 x 10–28、y 1–17，因 1:1 线必须过原点） | 改 caption |
| fig08 | 六范式之外（2×2 Δ 折线 + 带） | 无。全篇最自解释的一张：n/n 进标题、±带是逐档阈值、零点线明确；四块量程不同，但画的本来就是四个不同产物的 Δ，不是同一标尺上的横比 | 不改 |
| fig09 | 六范式之外（log 折线） | **坐标与标签两套口径**：x 坐标是 w=a/(a+b)=[0.1667, 0.2857, 0.3333, 0.4444, 0.5]，刻度标签却是比值 "20/100…100/100"（make_figures.py:501-502），档距 0.119 / 0.048 / 0.111 / 0.056 不等距，轴标题 "ash / biomass level" 又用比值口径 | 重画刻度（x=a/b 或等距分类轴）+ 改 caption |
| fig10 | **情景对比分组柱** | **caption 假命题**："a positive bar means that product's share grows with w"——LG Char 原始斜率 −0.0251，中心化后 +0.0555（solve.py:368 `gamma = b - b.mean()`），符号被翻转；中心化零点被当作"无效应"（0 = 四产物平均响应，不是不变）；12 条无误差带，2/12 的 |γ| 小于 95% 半宽 | 重画（加 se/95%）+ 改 caption |
| fig11 | 六范式之外（1×3 折线） | 三段量程 0.150 / 2.5 / 1.2（同一单位 mmol/g daf，make_figures.py:576-579 逐面板 pad），CS 的 2.8% 变化被画成满屏下跌；caption 的补救"compare slopes rather than heights"**无效**——视觉斜率同样被各段量程缩放 | 重画（按首档归一化 %，或共用量程）+ 改 caption |
| fig12 | 六范式之外（等转化率脊线） | 无拐点需求，直线即结论；caption 已写 iso-conversion locus | 不改 |
| fig13 | 六范式之外（3×4 分面带） | 每格独立 ylim（make_figures.py:656-658），带子的**视觉宽度排序与相对宽度排序相反**：CS·Char 占本格 76.6% 高度但相对宽度 13.1%（12 格最窄），CS·Tar 占 21.5% 而相对 15.8%；caption 没警告跨格不可比，正文却要拿"CS 带最窄"当结论 | 重画（按产物列共用量程）+ 改 caption |
| fig14 | **情景对比分组柱** | 分母未写（`loo_rmse_rel = rmse / obs[:,i].mean()`，solve.py:472，是"该格观测均值"）；n 未标（CS 9 折 / CE·LG 8 折）；12 格对同一条 5% 线做二值判定却无 family-wise 说明，且 5% 易被读成 α；caption 后半句错（见 §6.2） | 改 caption |
| fig15 | 六范式之外（区间条 / 条带） | `ax.set_xlim(0.03, 0.79)`（make_figures.py:739）把 CS 支撑左端 w=0.0 **裁掉**，画出来是 0.03–0.5，而 boundary JSON 是 0.0–0.5；灰点图例写 "inside support"（:748）而 caption 写 "query levels inside it"，CS 行 0.0909 那点是**观测档不是查询档** | 重画 xlim + 改 caption |
| fig16 | (a) 条形 / (b) log 棒棒糖 | (b) 只落中位点，JSON 里的 min/max/stdev 全没画；pipeline 254.6 与五段中位之和 259.5 不等（中位不可加），caption 未声明 pipeline 是独立计时 | 改 caption |

## 4. 四条必答（逐条给可数口径）

**4.1 自解释**（16 条 caption，逐项数）
- 单位：**16/16** 有单位或显式无量纲标记（fig10 γ(-)、fig05 φ(-)、fig02 ratio(-)）→ PASS
- 口径定义：**14/16** 交代了所画量怎么算；错的 2 条是 fig01（w 叫错）与 fig14（分母缺）
- 样本量：**3/16**（fig08 的 n/n 进标题、fig16(a) 的 42 runs、fig16(b) 的 five serial repetitions）；fig01 的 9/8 档、fig07 的 4 点、fig14 的 9 vs 8 折、fig03 的 n_mc 都没露面（`results_q1.json` 有 `n_mc` 键）
- 误差带：**2/16**（fig08 的 ±thr、fig13 的 5–95%）；其中一半是"数据层没有误差量可画"（results_q4 无 se/ci/p 键），一半是"算了没画"（results_timing 有 min/max/stdev）

**4.2 是否用面积代替量值：0 命中。** 全库没有 bubble / pie / treemap / 热力图，`grep -n 's=\s*[0-9a-z]' code\make_figures.py` 0 命中。唯一疑似是 fig15 的 `lw=6.0, alpha=0.20`（:721）粗线段——粗细是装饰、沿 x 的长度才是量（区间），caption 写的是 segment，legend 写的是 calibration support，语义没被读成量级 → 不计误用。

**4.3 Laffer / Pareto 拐点：NOT-APPLICABLE**（本套图没有 Laffer 曲线也没有 Pareto 前沿）。可数的替代检查是"该标阈值的地方标了没有"：fig02 比值 1、fig09 parity 1、fig14 5% 线、fig08 的 y=0、fig10 的 y=0 —— **5/5 都标了**。fig12 是等转化率脊线，16 点共线，既无拐点也不该有，不扣分。

**4.4 敏感性是否只画了有利的一半：6 张相关图里 5 张显示了不利面。**
- fig02：CS·Char 0.259、LG·Char 0.208 落在噪声地板左侧，照画；
- fig03：CE 3.42、LG 3.52 两个 F>1（失拟）照印；
- fig08：Water 6/8 且含一次方向翻转，照画；
- fig11：CE 端到端 −77.2%，照画；
- fig16(a)：12/42 从未被 solve.py 读到（42 次扰动的 28.6%），照画。
**唯一丢散度的是 fig16(b)**：JSON 里有 Q1 167.1–223.1 ms、pipeline 229.8–302.2 ms，`results_timing.json` 的 meta 自己写着"单次测量噪声本机实测可到 ±56%"，图上只留中位点——这是把最有利的统计量单独摆出来。

## 5. 四类高频缺陷复算

**①口径混用：命中 4 处。**
1. w 的命名：**10 张图**以 w 为横坐标（fig01/04/05/06/07/08/09/11/13/15）。其中只有 1 条 caption 给了定义而把它叫成 "the ash-to-biomass ratio $w$"（fig01，out/08-figures.md:58）；2 条只写 "against $w$" 不给定义（fig04 :76、fig11 :118）；1 条写 "the $w$ range"（fig15 :142）；余下 6 条连 w 都没提、改用 "at each level / equal ash level" 代指（fig05/06/07/08/09/13）。而代码里 w 是质量分数：`level_w()`（make_figures.py:117-121）把 "40/100" 解成 40/140=0.2857，不是比值 0.4；q1 的 w 数组 CS=[0.0,0.0909,0.1667,0.2308,0.2857,0.3333,0.375,0.4444,0.5] 与 a/(a+b) 逐位吻合；
2. fig09 的 x 轴：坐标 w、标签 a:b；
3. fig10 的中心化零点：0=平均响应，caption 当"不变"；
4. fig03 的 "F" 与 "5%"：5% 是 eps_rel 测量噪声，不是 α。

**②倍数与百分数：命中 2 处。**
1. fig14 的 "%" 分母未写（每格观测均值；同图 12 格分母各不相同，18.708% 与 0.892% 不在同一标尺上直接比）；
2. fig11 三段同单位不同量程，把 2.8% 的变化画成 89% 变化的视觉量级（CS 0.150/5.32、CE 2.5/2.82、LG 1.2/3.0）。

**③多重比较：命中 3 处，且都没有 q 可给。**
- fig02：12 个 ratio 与 1 比；
- fig03：3 个 F；
- fig14：12 格与同一条 5% 线。
三处都没有 p 值（results_q1 的 ilr 键里无 p、results_q4 无 se）——**"给不出 BH/Bonferroni 后的 q"本身就是缺陷**，不是"q 算错"。若只按 fig03 的 3 个 F 做族，BH 在 k=3 下也改不了"CE/LG 显著、CS 不显著"的结论；真正有风险的是 fig14：12 格二值判定里 8 格"超线"，其中 CS·Tar 只超 0.497 个百分点（5.497 vs 5.0），这一格的归属对阈值极敏感，caption 却把它归给了 CE/LG。

**④图表刻度（有效字号）：0 违规。** 16/16 PASS，最小 6.277 pt（fig13 的 83 个 span 全在 6.3）。这一条是**干净的**，不是缺陷；但距 6.0 的门槛只有 0.28 pt，fig13 若要再塞内容（例如标注 12 格的相对带子宽度），建议整张提到 7.0 pt 起，别贴着门槛改。

## 6. 三条硬错（每条都有反例、都能当场复算）

**6.1 fig10 的 caption 是假命题。** caption（out/08-figures.md:112）写 "a positive bar means that product's share grows with $w$"。反例：LG·Char 的原始斜率 `dlnS_dw_raw` = **−0.0251**（份额随 w 略降），中心化后 `gamma_centered` = **+0.0555**（正条）。12 格里恰好 1 格符号被翻转。
复算方法（纯 Python，不经 numpy，因为 `E:\Mini\envs\mathmodel\python.exe` 在 `np.linalg.lstsq` 上会以 0xC06D007F 崩溃）：用 `results_q1.json` 的 9/8 档 y 对 `[1, w]` 做 OLS，取斜率减去四产物斜率均值——12 个 γ 与 `results_q4.json` 逐位相同（差 0.0000），可见链路无误，错的是 caption 的解释，不是数据。
顺带量出：12 个 γ 里有 **2 个**的 |γ| 小于自身 95% 半宽——CE·Water |−0.7269| vs ±0.9127、LG·Syngas |0.5692| vs ±0.6575（半宽 = t₀.₉₇₅(n−2)·se，se 由同一 OLS 的残差给出）。图上这两根柱与别处一样实心，没有误差带。

**6.2 fig14 的 caption 后半句错。** caption（:136）写 "eight of the twelve cells sit above it, and the CE/LG cells are the ones that do"。前一句对：CS 1（Tar 5.497）+ CE 4 + LG 3 = 8。后一句错：这 8 格里 1 格是 **CS·Tar**。

**6.3 fig05 的 caption 与图不符。** caption（:82）写 "Mole fractions of the same major species"。实际 CS 无 C2H6 线、CE 无 CH4 线、LG 无 H2 与 C2H6 线——"the same"对三块都假。同一张图还叠了第二个口径问题：φ=z/Σz 是体积份额，写成 mole fraction 只在理想气体下等价（§solve.py 用 `V_m_ASSUMED` 折摩尔，说明模型确实假定理想气体，但 caption 没写这一句）。

## 7. 页面预算（C6）与语言（C7）

C6（2019_APMCM 官方格式说明 :83 "within 30 pages, the appendix is no limit"）：16 图高度合计 3607.2 pt，按 0.9964 缩放后 3594.2 pt = **49.9 in**；版心高 297−2×25.4 = 246.2 mm = 9.69 in → **5.15 个版心 ≈ 5.2 页纯图幅**（不含 caption，caption 另计约 16×2 行）。30 页上限下不构成风险，但正文目前 0 处引用，图注预算要随骨架一起补。

C7（2017_APMCM_Essay_format_and_submission_specifications.txt:75 "no Chinese word should be found in the main body"）：16 条 caption 逐条正则 `[\u4e00-\u9fff]` 命中 **0**，图这一层 PASS。注意这只覆盖 caption 字符串本身（out/08-figures.md:58–148），图片内的文字全是英文标签，`figfont` 也未发现中文 span。

## 8. 复算清单（别人拿同一份 PDF/JSON 可照做）

```
# 1 机器口径
$env:PYTHONPATH='E:\数学建模\.agents\skills\mathmodeling\scripts'
& 'E:\Mini\envs\mathmodel\python.exe' review_check.py   'E:\数学建模\PRACTICE_2023B'
& 'E:\Mini\envs\mathmodel\python.exe' gauntlet_check.py 'E:\数学建模\PRACTICE_2023B'
& 'E:\Mini\envs\mathmodel\python.exe' -m mmkit.figfont figures\fig13_q5_predictions.pdf

# 2 版心与缩放的算术
#   415.03 pt = (210-63.6) mm / 25.4 * 72 ;  0.9964 = 415.03/416.5 ;  6.3*0.9964 = 6.277

# 3 fig10 的符号翻转与 95% 半宽
#   读 data/results_q4.json 的 dlnS_dw_raw（列表，按 Tar/Water/Char/Syngas）与 gamma_centered（字典）
#   LG、Char：raw = -0.0251，centered = +0.0555  → 符号翻转
#   se 由 data/results_q1.json 的 y 与 w 做 [1,w] 的 OLS 残差得到

# 4 fig14 的 8/12 与 CS·Tar
python -c "import json;q=json.load(open(r'E:\数学建模\PRACTICE_2023B\data\results_q5.json'));print(q['combos']['CS']['loo_rmse_rel'])"
#   CS Tar 0.05497 > 0.05  → 8 格里含 CS·Tar

# 5 fig13 的带子宽度 vs 格子高度（每格独立 ylim 的证据）
#   pad = max(0.10*(max(allv)-min(allv)), 0.08) ; allv = obs + lo + hi   (make_figures.py:656-658)
#   CS·Char 带宽/本格 y 范围 = 0.766，相对宽度 13.1%（12 格最窄）

# 6 fig15 的支撑左端被裁
#   boundary.combos.CS.w_min = 0.0 ; make_figures.py:739 set_xlim(0.03, 0.79)

# 7 caption 中文字符计数
[System.IO.File]::ReadAllLines('E:\数学建模\PRACTICE_2023B\out\08-figures.md',[Text.Encoding]::UTF8) |
  Select-String -Pattern '^\s*-\s*\*\*Caption\*\*' | Select-String -Pattern '[\u4e00-\u9fff]'
#   命中 0 / 16 条

# 8 页面预算
#   sum(H_pt)=3607.2 ; x0.9964 = 3594.2 pt = 49.92 in ; /9.69 in = 5.15 版心
```

## 9. 结论

图本身能画、字号合规、页面预算不超、无面积编码误用；问题集中在**"图说的"与"数据说的"不一致**：三条 caption 与 `data/*.json` 直接冲突（fig10 正号解释、fig14 后一句、fig05 "the same"），三处坐标口径会让看图得到的结论与数据相反（fig09 轴、fig11 量程、fig13 独立 ylim），两处漏报样本量与分母（fig14、fig03）。按"结论表格必须能被别人拿同一份 PDF 复算"的口径，这三条硬错足以判不及格。改法分布：只改 caption 8 张（fig01/02/04/05/07/14/16，加 fig03 的一处微调——F 文本从固定 y=0.111 挪到柱顶）、必须动代码重画 6 张（fig06 刻度、fig09 x 轴、fig10 误差带、fig11 归一化、fig13 按列共用量程、fig15 xlim）、不动 2 张（fig08、fig12）。

VERDICT: FAIL