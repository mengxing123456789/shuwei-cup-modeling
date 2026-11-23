BYTES 32536
# 04-fit｜题面「要求你」句式 × 论文交付物对照

被测件：`E:\数学建模\_swc2026\SWC2026_A\main.pdf`
题面原文：`E:\数学建模\_swc2026\SWC2026_A\problem\problem.txt`（1056 行，2026 数维杯 A 题；注意 `E:\数学建模\APMCM-PROBLEMS\PROBLEMS\2026_A.txt` 是另一道 APMCM 2026 A 题，不是本题）
官方依据：`E:\数学建模\APMCM-PROBLEMS\_official_evidence.json`（35 份真题，8 个关注点）、`_official_criteria.json`（C1..C12）
本报告只回答一件事：把题面里每一句「要你做 X」抠出来，在论文里找到 X 的落点，判定它是**数值**、**定性**、**部分**还是**没做**。

## 0. 复算口径与快照

### 0.1 `review/00-metrics.md` 缺失

`review/00-metrics.md` 不存在：2026-11-20 10:54、11:07、11:09 多次查看 `E:\数学建模\_swc2026\SWC2026_A\review\`，只有 `README.md`（1337 B，09:34:19）。`README.md:7` 明说 `00-metrics.md` 由 `scripts/run_review.py` 自动生成，是本报告的唯一基线；实际文件没有生成。因此本报告没有第二列可并列；下面的机器输出是我在最终快照上自己重跑的第一基线。若之后补生成 `00-metrics.md`，请按本节的 mtime/sha256 对齐，不要用别的构建。

### 0.2 被测件与数据层同代性

| 文件 | mtime（2026-11-20） | 字节 | sha256 |
|---|---:|---:|---|
| `main.pdf` | 11:13:35 | 451432 | `CF59A02A633FC0C03D21921041886FC22895474A52E7D2C923DE232C8F87910E` |
| `main.tex` | 11:09:33 | 48630 | `78ED6F265289B0F2159005FD0FDBCC7ABCFCBF46EC3A10AB8DCCBE66D9D32AFD`（410 行） |
| `problem/problem.txt` | 09:34:27 | 25430 | `E435158BA36993939C9C6F5DFE8AA9CA6137047BB3619368837066DCF2A45E9E` |
| `data/p4_econ.json` | 10:43:27 | 729040 | `5EE2A3610185BECE62B217B525E336C1CFBC4B89815EE92FB36C2187DF84E315` |
| `data/p5_sobol.json` | 10:43:31 | 13016 | `33F01DB0736E7A755B1FA8A4DAAF0949B6B0296719793E7BDFCA1E16F027F066` |
| `data/p3_decline.json` | 10:42:17 | 62894 | `3CCA7C0BD1A3C3123BFB152CA87F197351BCB407B3D4241E1350668C19A6480C` |
| `tables/*.tex` | 10:49:32 | — | — |
| `figures/*.pdf` | 最新 11:06:25 | — | — |

数据层（p4/p5/p3 10:42–10:43，tables 10:49，figures 11:06）没有晚于 `main.pdf`（11:13:35）→ **不存在「被测件落后 N 小时」的 R-V11 告警**。审读期间论文被连续重建（10:49→11:00→11:03→11:07→11:08→11:10→11:13），本报告是 **11:13:35 快照**；如果读者在另一个构建上复跑，必须重算命令，不能把本报告页码/行号直接套到旧 PDF。

### 0.3 复算命令

```bat
cd /d E:\数学建模\_swc2026\SWC2026_A
E:\Mini\envs\mathmodel\python.exe ..\.agents\skills\mathmodeling\scripts\review_check.py .
E:\Mini\envs\mathmodel\python.exe ..\.agents\skills\mathmodeling\scripts\gauntlet_check.py .
E:\Mini\envs\mathmodel\python.exe -m mmkit.figfont main.pdf
E:\Mini\envs\mathmodel\python.exe code\verify_numbers.py
```

`mmkit` 需要 `PYTHONPATH=E:\数学建模\.agents\skills\mathmodeling\scripts`。PDF 抽取使用 `pdftotext -layout -enc UTF-8 main.pdf review\work\pdf_pages.txt` 后按 `\f` 分页；本报告引用的 PDF 页号均为该快照的印刷页。

## 1. 机器口径原始输出

```
== review_check.py ==
paper: E:\数学建模\_swc2026\SWC2026_A
pdf: main.pdf   pages: 24
[ OK ] C4    p1 has summary/abstract=True
[ OK ] C4    p2 has contents/directory=False
[ OK ] C5    header lines matched=23
[ OK ] C5    headers leaking identity=0
[ OK ] C7    chinese chars in body=0 (appendix, not judged=0)
[ OK ] C6    total pages=24
[ OK ] C9    appendix=True code=True
[ OK ] C11   placeholder team number hits=0
[ OK ] C11   self-declared invalid identifier in body=0
[ OK ] C11   has References section=True
[ OK ] C8    reference type markers=12
VERDICT: PASS  (fail=0 unknown=0)

== gauntlet_check.py ==
[band] benchmark: E:\数学建模\_swc2026\SWC2026_A\refs\official_standard.json  n=16  median sections=13.5
[PASS] paper resolved                      E:\数学建模\_swc2026\SWC2026_A
[PASS] R-V01 body <= 30 pages              body=23 (header numerator of first Appendix A page)
[PASS] R-V02 single denominator            distinct totals=1
[PASS] R-V02 numbers contiguous            header numerators form 1..n with no gaps
[PASS] R-V03 zero CJK in body              body cjk=0 (appendix, not judged=0)
[PASS] R-V04 zero 'university'             hits=0
[PASS] R-V05 team number filled            KNOWN OPEN: \baominghao placeholders must be filled before submission
[PASS] R-W06 no unsupported phrases        no 众所周知/显而易见/obviously,
[PASS] R-W11 front matter order            ['summary', 'contents']
[PASS] R-W04 references have type markers  12 type markers on 12 entries
[PASS] R-W04 >=70% references cited        cite calls=25, [n] uses before bibliography=0, entries=12
[PASS] R-V06 verify_numbers present        claims=116 exit=0
[PASS] R-V09 no stale artefact             KNOWN OPEN (explain each): none
[PASS] R-V07 band measured on both sides   figures/equations non-zero, so project was read from PDF text
[PASS] R-V07 out-of-band count             ABOVE=['abstract_numbers', 'abstract_density', 'distinct_numbers', 'pct_mentions', 'density_per_100w', 'tables', 'references'] BELOW=['figures']
[PASS] R-V14 figure text >= 6 pt           min=5.98 pt median=11.96 pt violations=0 single-char<6pt=53 (measured by python.exe)
16/16 PASS

== mmkit.figfont main.pdf ==
pdf: E:\数学建模\_swc2026\SWC2026_A\main.pdf
spans=5333  min=5.98 pt  median=11.96 pt
violations (>= 3 chars and < 6.0 pt): 0
single-character spans below 6.0 pt (not judged): 53
PASS

== code/verify_numbers.py ==
116 claims passed, 0 failed
failures=0
```

三条机器口径全过；这只是格式、页数和「文本里的数能否对到产物」的门槛。下面第 2–6 节是机器没有覆盖的题面契合度问题。

## 2. 题面逐句「要求你」表

说明：`problem.txt` 是英文题面；下表保留原句，引号内为逐字原文。`main.tex` 行号按 11:09:33 的 410 行版本。

### 2.1 Problem 1（P1）

| # | 题面要求（原句 + 行号） | 论文兑现位置（章 / 表 / 图） | 兑现程度 |
|---|---|---|---|
| P1-1 | `problem.txt:47-50` “Establish the coupled equations for the interacting seepage, stress, and damage fields, comprising the fluid-seepage continuity equation, the rock mechanical constitutive relation, the Biot effective-stress coupling relation, and the damage evolution equation.” | `main.tex §3.1 L87-125, Eq(1)-(6)`；`Figure 1` p7 | **定性**：油气/水相质量守恒、应力敏感渗透率、Hooke、Biot 有效应力、损伤 d、CO2 对流扩散、纳米吸附均有公式；但「each equation 的 physical meaning」未逐式成段。 |
| P1-2 | `problem.txt:50-52` “Specify the physical assumptions, initial conditions, and boundary conditions of the model, briefly explain the physical meaning of each equation,” | `main.tex §2.2 L72-83 A1-A8`；`§3.2 L127-134`；`Figure 1` p7 | **定性（部分）**：A1-A8、初始条件 p0=45 MPa/Sw=0.25、三阶段边界均在；逐式物理解释只有变量定义和零散一句，不是每式一段。 |
| P1-3 | `problem.txt:52-53` “and distinguish the boundary conditions of the injection, soaking, and production stages.” | `main.tex §3.2 L127-133`；`Figure 1` p7 | **数值**：注入 p=pM、q=qinj、c=cin、n=nin；闷井 q=0 且两端无流；生产 p=pwf=35 MPa，三阶段边界明确。 |

### 2.2 Problem 2（P2）

| # | 题面要求（原句 + 行号） | 论文兑现位置（章 / 表 / 图） | 兑现程度 |
|---|---|---|---|
| P2-1 | `problem.txt:55-58` “nondimensionalize the coupled equations established in Problem 1, obtain the dimensionless governing parameter groups, and explain the physical meaning of each parameter; with reference to Appendix A, give the order of magnitude of a reasonable value for each parameter.” | `main.tex §4.1 L171-176`；`Table 2` p9 | **部分（定性）**：Table 2 有十组 Π 和 “Physical meaning” 列；但没有 order-of-magnitude 列，也没有逐参数引 Appendix A 的取值依据。`data/p1_mechanistic.json` 的 `dimensionless.Case{1,2,3}.Pi*_*.order` 已有十组数量级（如 Π1=0, Π2=-3, Π5=-5, Π6=2），论文没有印出来。 |
| P2-2 | `problem.txt:59-61` “Use dimensional analysis to derive an approximate analytical relation between the soaking time and the radius of stimulation influence,” | `main.tex §4.3 Eq(8)-(9) L183-201`；`Table 1` p8；`Figure 2` p8 | **数值**：Rδ=sqrt(4αpt)·erfc^-1(δ)，δ=0.05 时 R0.05=2.77·sqrt(αpt)；数值 40.64 m vs 解析 31.55 m，比 1.29；Table 1 的 ν=0.5008–0.5030。 |
| P2-3 | `problem.txt:61-62` “and analyze which dimensionless parameters significantly modify the effect of soaking time on the stimulation extent.” | `main.tex §4.5 L219-220` | **定性（部分）**：正文说明 Π1/Π3/Π8/Π6/Π10 进入或影响关系，但只有 γk 从 0→2 的一组敏感性（指数 0.5003→0.5060，前因子 12%）；没有十组参数的逐项敏感度表或排序。 |

### 2.3 Problem 3（P3）

| # | 题面要求（原句 + 行号） | 论文兑现位置（章 / 表 / 图） | 兑现程度 |
|---|---|---|---|
| P3-1 | `problem.txt:64-68` “Formulate a multi-objective optimization model with the objectives of enhancing reservoir production and reducing the total operational cost, define the design variables, and impose engineering constraints on the basis of equipment capacity, the limits on nanomaterial use, and the upper limit of formation pressure-bearing capacity.” | `main.tex §5.1 L224-227`；`Table 5` p14 | **数值/部分**：目标（EUR 最大、名义成本最小）和约束 q≤800、V≤5000、m_nano≤30 t、pmax=min(0.95pf,60) MPa 都写了；但 `data/p4_econ.json:design_space` 把 `qinj` 固定为 800，且没有 `τinj` 的搜索维，设计向量里的 `qinj` 与 `τinj` 实际未优化。 |
| P3-2 | `problem.txt:68-72` “Taking Case0 (the base case) as the starting point, select three representative scenarios—a low-permeability, high-stress reservoir; a medium-permeability, low-stress reservoir; and a high-permeability reservoir with complex natural fractures—” | `main.tex §5.3 L232-248`；`Table 5` p14 | **部分/没做**：论文只用 Case1/2/3，全文 `Case0`/`Case 0` 0 hit；Case3 的“complex natural fractures”未建模（见 §4.1，题面 Table A.3 的 ρnf Case3=0.08 m/m2，论文 A2/A3 改成 homogeneous isotropic、1D）。 |
| P3-3 | `problem.txt:72-74` “choose an appropriate intelligent optimization algorithm, and solve for the Pareto-optimal solution set by means of simulation or a surrogate model. Justify the choice of algorithm,” | `main.tex §5.1 L227`；`§5.3 L250` | **部分/没做**：实际是加权和网格 + “NSGA-II check”；没有算法选择理由、没有与其他智能算法的比较，也没有说明为什么加权和标量化适合本 Pareto 问题。 |
| P3-4 | `problem.txt:74-75` “and provide 2–3 compromise operational schemes for reference for each of the three scenarios.” | `main.tex §5.3 L244-248`；`Table 5` p14 | **部分**：Table 5 每个案例只有 geo/emp 两个标定行（各一个 knee），不是 2–3 个独立运营方案；表列只有 ts、Vinj、EUR、Cost、NPV，缺 cn、fCO2、qinj、τinj，不能直接执行。`p4_econ.pareto_meta` 的 knee 实际含 `cn=0.5, fCO2=0.8, qinj=800`，但论文未印。 |
| P3-5 | `problem.txt:75-78` “In view of measurement errors in geological parameters, assume ±15% random perturbations in key parameters such as permeability and in-situ stress, screen the Pareto-optimal set for robust operational schemes with strong disturbance resistance, and give engineering recommendations.” | `main.tex §5.4 L252-253`；`Table 6` p15 | **没做/部分**：Table 6 的 14 个组合因子是 `Ainf/tau/D/Poil/cprod/csoak/Cfrac`，没有 permeability、没有 in-situ stress；不是对 Pareto 集做随机扰动筛选；没有工程建议段（见 §4.2）。 |

### 2.4 Problem 4（P4）

| # | 题面要求（原句 + 行号） | 论文兑现位置（章 / 表 / 图） | 兑现程度 |
|---|---|---|---|
| P4-1 | `problem.txt:80-82` “Use the productivity simulation data in Attachment C to build a productivity prediction model, divide the training and test sets appropriately, and adopt corresponding measures to prevent overfitting.” | `main.tex §6.1-6.3 L259-274`；`Table 9` p17 | **数值/部分**：38,880 条、按 case×concentration×soak 整组划分、每折至少一个未见 soak level、M5 15 参数；但 `Table 9` 的 caption 说 “two complete soak levels”，表内实际是 4 或 6 个（见 D6）。 |
| P4-2 | `problem.txt:82-84` “Using the economic parameters in Appendix B, calculate the net present value (NPV), plot the variation of NPV with soaking time, and determine the optimal soaking time for each of the three scenarios.” | `main.tex §6.4 L279-300`；`Figure 5` p18；`Table 10` p18 | **数值**：NPV 曲线、Table 10 的数据网格 10/25/35 d 和连续最优 9.78/23.49/35.44 d、2% 带 4–19/18–31/31–40 均有。 |
| P4-3 | `problem.txt:85-87` “Compare the results of the data-driven model with those of the mechanistic model; where discrepancies arise, analyze their causes in terms of model assumptions, numerical error, and data noise.” | `main.tex §6.5 L309-312` | **部分**：有两层机制解释（指数 0.50 vs 0.22–0.34、半径 40.6 vs 34–36、共享 D CV<0.5%）和噪声段（11.95%/29%）；正文没有把“numerical error”作为一个原因定量写出来。`data/p4_econ.json:attribution.numerical_error` 有“网格加密 1e-5、R_p 不进 NPV”的说明，但论文正文没有引用。 |
| P4-4 | `problem.txt:87-88` “Construct a comprehensive evaluation index system for reservoir stimulation performance,” | `main.tex §6.7 L323-324` | **定性/部分**：四个维度（物理可行性、经济回报、稳健性、设计可辨识性）都有代理量，但没有权重、评分公式、归一化或阈值；论文明确“不合成单一数”，所以它是一组指标而不是可计算的综合评价体系。 |
| P4-5 | `problem.txt:88-90` “carry out a global sensitivity analysis of the key geological and operational parameters, and identify the parameters that most strongly influence the optimal soak time.” | `main.tex §6.6 L314-321`；`Table 12` p20 | **没做/部分**：8 个因子是 `Ainf, tau, D, Poil, cprod, csoak, Cfrac, a`，全部是产量模型/经济参数；没有渗透率、地应力、注入速率、注入体积、CO2 比例、纳米浓度等地质/运营参数。因此 Table 12 能回答“模型参数谁重要”，不能回答题面“key geological and operational parameters”。 |

### 2.5 全局一致性、补充定义与模型假设

| # | 题面要求（原句 + 行号） | 论文兑现位置（章 / 表 / 图） | 兑现程度 |
|---|---|---|---|
| G-1 | `problem.txt:99` “Problems 2, 3, and 4 must remain consistent with Problem 1.” | `main.tex §3–§6` 共用同一组控制方程；`§6.2` M5 是数据侧模型 | **部分**：P1 方程与 P2/P3 的 Π/V0 口径相同；P4 的 M5 是独立数据拟合模型，正文用 `§6.5` 做对照，但没有把 P4 的 `Ainf/tau` 代回 P1 做同一组机理参数的一致性检验。 |
| G-2 | `problem.txt:92-99` “Stimulation radius: defined as ... recommended thresholds ... Δp/p0 = 5%, ... 0.01 wt%, ... d = 0.10. Unless otherwise stated, ... pressure disturbance reaches 5% of p0.” | `main.tex §4.3 L194`；`Table 1` p8 | **部分**：默认压力扰动 5% 已实现（R0.05=2.77√(αpt)，Table 1 的 Rp）；Table 1 另有 R_C=0.004、R_d=0.020；没有给 nanoparticle 0.01 wt% 对应的半径。 |
| G-3 | `problem.txt:125-129`（基本假设 3）“Whether the free CO2 phase is modeled separately is left to the contestants; if it is neglected, the applicable conditions must be stated and a comparison with the case in which the free phase is considered must be provided.” | `main.tex A5 L79`；`Eq(5) L117-119` | **没做**：正文只有 Henry 溶解和 dissolved CO2 对流扩散；`free CO`/`free phase` 0 hit，`supercritical` 0 hit；没有“忽略自由 CO2 相”的适用条件说明，也没有与考虑自由相的对比。 |
| G-4 | `problem.txt:153-162` Case0 是 base case；“complete set of values is given in the Case0 columns ... the complete values for the three typical scenarios are also listed” | `main.tex` 全文无 `Case0`；`§5` 直接使用 Case1–3 | **没做**：`Case0` 0 hit；没有说明从 Case0 到 Case1/2/3 的扰动路径，也没有用 Case0 校验参数/初始状态。 |

## 3. 官方高频项核账（`_official_evidence.json`）

`_official_evidence.json` 的口径：`n_statements=35`，8 个 aspect；全库频次为 `n_present/n_total`。本题不是 APMCM 真题，但这些 aspect 是官方语料的高频检查面，仍可作为「题面通常要什么」的对照。

| aspect（`_official_evidence.json`） | 全库频次 | 本题对应题面 | 本文判定 |
|---|---:|---|---|
| 给数据 / 附件（R-M14，`data_attachment`） | 19/35 = 54.3% | `problem.txt:959-1056` Attachment C（38,880 条，3×3×12×360） | **兑现**：`main.tex:70` 明确 38,880 条；§6.1–6.3 使用附件 C；Appendix A `main.tex:367` 声明四个脚本写 `data/*.json`。原始 xlsx 未在论文附录重印，但题面已给附件，数据契约成立。 |
| 政策建议 / 决策输出（R-W08，`policy`） | 19/35 = 54.3% | P3 `problem.txt:74-78` “provide 2–3 compromise operational schemes ... and give engineering recommendations” | **漏（本题唯一整类没做）**：`main.tex:244-248` 只有 knee 点和一条 Case1 的 `ts=23–25 d, Vinj=3200–5000` 带；`Table 5` 每案例 2 行标定、列缺 cn/fCO2/qinj/τinj；没有 2–3 个独立可执行方案，也没有工程建议段。 |
| 预测 / 时序（R-T04，`predict`） | 13/35 = 37.1% | P4 `problem.txt:80-84` 建产量预测模型、NPV–闷井曲线、三案例最优闷井时间 | **兑现（模型层面）**：M5 15 参数、组间 CV（Table 9）、NPV 曲线（Figure 5）与 Table 10 均给出；但没有独立未来时间窗（全部数据在 360 d 内），所以是“拟合+样本外 soak level 验证”，不是外推到时序未来。 |
| 要求具体数值（R-W05，`quantify`） | 13/35 = 37.1% | P4 `problem.txt:82-84` “calculate the NPV ... determine the optimal soaking time” | **兑现（数值很多）**：Table 10/11 和 §6.4 均有数值；但 D1–D4 表明若干印出的数值与 `data/*.json` 对不上，属“有数但不可复算”，不能算质量达标。 |

补充两个与本题直接相关的 aspect：

- `optimize`（R-M10）全库只有 5/35，但本题 P3 是核心；本文有目标/约束模型，**算法选择理由、2–3 方案、Pareto 集扰动筛选**未完成。
- `sensitivity`（R-V07）8/35，本题 P3/P4 两处都要求；P3 的 ±15% 因子集错、P4 的全局敏感性维度错，见 §2.3/§2.4 与 D2/D5。

**回答“本文漏了哪一类”**：四类高频项里，**「政策建议/工程建议」是唯一整类没有交付的（19/35）**。它不是“文字不够漂亮”，而是 P3 的 `2–3 compromise operational schemes` 与 `engineering recommendations` 没有可执行对象（案例、ts、Vinj、cn、fCO2、qinj、判定阈值）。其次是 **P4 的“地质/运营参数全局敏感性”**：虽然 `sensitivity` 不是 19/35 那一类，但题面白纸黑字要求，本文用 8 个模型/经济参数替代了地质/运营参数，属于方向错位。

## 4. 两条最容易整条漏掉的

### 4.1 描述性约束：Case3 的 complex natural fractures 被改成了均质一维

题面 `problem.txt:69-71` 明确要求第三个场景是 “a high-permeability reservoir with complex natural fractures”。附录 A 的 Table A.3（`problem.txt:697-704`）给出 `Natural-fracture density ρnf`：Lower 0、Upper 0.10、**Case0 0、Case1 0、Case2 0.01、Case3 0.08 m/m2**；`problem.txt:168-169` 又说明该密度是“单位面积总缝长”。

论文 `main.tex:76-77` 的 A2/A3 写：

- A2：“The matrix block is homogeneous and isotropic...”
- A3：“Flow is one-dimensional in the direction normal to the fracture face... single-fracture, single-well element.”

全文 `grep -ni natural main.tex` **0 hit**，`ρnf`/`ρ_nf` **0 hit**。因此：

1. **谁对**：题面 Table A.3 明确给 Case3 的 `ρnf=0.08 m/m2`；论文的 A2/A3 把它设成 0（均质）。按题面数据，Case3 不是均质一维；论文的 `Case3` 结果（Rp=181.46 m，V0_geo=264,199 m3，NPV +184.3×10^4）是**另一个均质模型**的结果。
2. **影响**：`p1_mechanistic.json:Case3` 的 `Rn=193.3`、`dm_max=0.6621` 等都没有 natural-fracture 几何；`p4_econ:V0.Case3.geo=264199.4` 也没有任何 `ρnf` 输入。题面要求的高渗复杂裂缝场景没有被建模，不是“参数近似”。
3. **复算**：`Select-String -Path problem\problem.txt -Pattern 'Natural-fracture density' -Context 0,8` 可得 Table A.3 的 0/0/0.01/0.08；`Select-String -Path main.tex -Pattern 'natural|ρnf'` 0 hit。任何读者拿同一份 PDF 都可复算。

同类问题：`Case0` 是题面明确的 base case（`problem.txt:153-162`），论文 `Case0` 0 hit；P3 直接从 Case1–3 开始，没有从 Case0 的基准值计算扰动或标定。这与“Taking Case0 as the starting point”是结构性不符，不是措辞问题。

### 4.2 “给建议/给方案”的小问：只有一条 band，不是可执行方案

题面 P3 `problem.txt:74-78` 的要求是并列两项：**每个场景 2–3 个折中运营方案** + **工程建议**。可执行交付至少要有：案例、ts、Vinj、cn、fCO2、qinj（若允许）、判定阈值（NPV/成本/产能）。

论文实际：

- `main.tex:244-248` 只给 Case1 的 `ts=23–25 d, Vinj=3200–5000 m3` 的“band”，Case2/3 只给 knee 的 ts/Vinj/EUR/NPV；没有每案例 2–3 个独立方案。
- `Table 5` p14 的列是 `V0 model / Front points / ts / Vinj / EUR / Cost / NPV`；缺 `cn / fCO2 / qinj / τinj`，无法从表直接执行。
- `p4_econ.pareto_meta` 实际有六个 knee 的完整参数（`cn=0.5, fCO2=0.8, qinj=800`；Case1 geo/emp ts=23/25、Vinj=5000/3200；Case2 27/29、5000/3100；Case3 31/33、5000/3100），但论文只印了 ts/Vinj，剩下的关键操作参数没有交付。
- `main.tex:339-345` 的 Conclusion 只有经济结论（Cases1/2 亏、Case3 盈利），没有“选哪个方案、按什么阈值停机/转产”的工程建议。

所以这一小问只能判 **部分/没做**。如果只写“Case3 is profitable”这种队列级结论，按题面标准等于没做；本稿比一句结论多了一点 band，但仍不足以称为 2–3 个可执行方案。

## 5. 四类高频可复算缺陷逐类检查

| 类 | 判定 | 本稿证据 |
|---|---|---|
| ① 口径混用（权重 vs 有效贡献、逐帧 pool vs 每人 p95、抽取耗时 vs 端到端） | **FAIL** | `main.tex:204` 把 M5 的 τ=8.34/10.02 d 当作 Table 4 的指数饱和 τ（Table 4 是 8.502/9.991）；`main.tex:270` 的 Ainf Case3=51.3 与 Table 8 的 54.985 不同；`main.tex:70` 的 9.7% 没有 `data/*.json` 键；`Table 9` caption 的“two complete soak levels”与实际 4/6 个不符。见 D3/D4/D6/D7。 |
| ② 倍数与百分数（同一现象两个分母） | **FAIL** | `main.tex:250` “below 1% in every case” vs `p4_econ.pareto_meta` Case2 `rel_diff=-0.140628`（14.06%）、Case3 `-0.0139404`（1.39%）；`main.tex:253` “no perturbation moves ... more than one day” vs `p4_econ.robustness` Case2 `max|d_ts|=2.0`；`main.tex:310` “34–36 / 40.6 = 0.92–0.95”实际 0.837–0.887，`p4_econ.mechanism_channel` 的 0.92195/1.07238 是 sqrt(0.85)/sqrt(1.15) 不是数据半径比。见 D1/D2/D5。 |
| ③ 多重比较（k 个检验必须给 BH/Bonferroni q） | **NOT-APPLICABLE** | 全文没有 p 值、显著性检验或 k 次假设检验；Table 12 是确定性 Sobol 方差分解（48 个指数），不是多重检验。没有 q 可报。严格说，Sobol 表没有给出指数置信区间/重复抽样误差，这是不确定性报告的另一个问题，但不是 BH/Bonferroni 问题。 |
| ④ 图表刻度（有效字号 < 6 pt 用 figfont 量） | **PASS（最终快照）** | `mmkit.figfont`：spans=5333，min=5.98 pt，median=11.96 pt，`violations(>=3 chars and <6.0pt)=0`，single-char<6pt=53；`gauntlet` R-V14 PASS。仍有 53 个单字符 span 在 5.98 pt（多为图内符号/数字），按机器口径不判违规；若评审把单字符也按 6 pt 卡，这是临界值而非硬失败。 |

## 6. 可复算缺陷清单（按严重度）

### D1（最硬）NSGA-II “below 1% in every case” 与产物相反

- 论文：`main.tex:250` “the relative difference between its best NPV and the grid best is below 1% in every case (the exact values are in the data file).”
- 产物：`data/p4_econ.json` → `pareto_meta["Case1|nsga2_check"].rel_diff = -0.0003147129`；`Case2|... = -0.1406281085`；`Case3|... = -0.0139404015`。
- 复算：

```bat
E:\Mini\envs\mathmodel\python.exe -c "import json;d=json.load(open(r'E:\数学建模\_swc2026\SWC2026_A\data\p4_econ.json',encoding='utf-8'));print({k:round(v['rel_diff'],6) for k,v in d['pareto_meta'].items() if k.endswith('nsga2_check')})"
```

- 实测：`{'Case1|nsga2_check': -0.000315, 'Case2|nsga2_check': -0.140628, 'Case3|nsga2_check': -0.01394}`。Case2 是 **14.06%**，Case3 是 **1.39%**，不是“every case <1%”。这条把“optimizer check”从验证变成了反面证据。

### D2（题面直接冲突）鲁棒性因子集与“最多一天”声明都不成立

- 论文：`main.tex:253` “a 14-run screen in which permeability and in-situ stress are perturbed by ±15% one at a time and in combination. In Cases 1 and 2 no perturbation moves the optimal soak time by more than one day.”
- 产物：`data/p4_econ.json:robustness.Case1/2/3.cases` 只有 `Ainf+/-、tau+/-、D+/-、Poil+/-、cprod+/-、csoak+/-、Cfrac+/-`；没有 `permeability`、没有 `in-situ stress`。
- `max(|d_ts|)`：Case1=1.0，Case2=2.0，Case3=4.0；Case2 的 `tau+` 是 +2.0、`tau-` 是 -2.0、`csoak-` 是 +2.0；`n_changed` 只有 Case3=2，但位移阈值仍是 2 天。
- 复算：

```bat
E:\Mini\envs\mathmodel\python.exe -c "import json;d=json.load(open(r'E:\数学建模\_swc2026\SWC2026_A\data\p4_econ.json',encoding='utf-8'));[print(c, max(abs(x['d_ts']) for x in d['robustness'][c]['cases'].values()), list(d['robustness'][c]['cases'])) for c in ['Case1','Case2','Case3']]"
```

- 结论：题面要求的 `permeability`/`in-situ stress` 没有做；`no perturbation ... more than one day` 至少在 Case2 不成立；“Pareto set 的随机扰动筛选”也没有任何实现（只有 14 个单参数/组合的确定性情景）。

### D3（Table 4 与正文互斥）τ 和 runs 不是同一组拟合

- 论文：`main.tex:204` “τ=6.70, 8.34 and 10.02 d ... the exponential model produces 7, 7 and 9 [runs].”
- 表：`tables/tab_shape.tex:10-12` 的 `τ` 是 6.696 / **8.502** / **9.991**，`runs_exp` 是 7 / 7 / **4**。
- 产物：`data/p2_shape.json` 的 `S2_exp`（cn=1.0）`tau=6.695827 / 8.501644 / 9.991346`，`resid_runs=7/7/4`。
- 结论：正文的 8.34/10.02 与 7/7/9 来自 M5/其他拟合，不是 Table 4 的累计产量指数拟合；同一段把三套口径混写。复算：`Select-String -Path tables\tab_shape.tex -Pattern '6.696|8.502|9.991|runs'`。

### D4（Table 8 与正文互斥）Case3 的 Ainf/tau 是旧值

- 论文：`main.tex:270` “Ainf=8.77, 27.51 and 51.3 m3/d, τ=6.62, 8.34 and 10.02 d.”
- 表：`tables/tab_m5.tex:10-12` 的 Case3 是 **Ainf=54.985、τ=9.98**；`data/p3_decline.json:M5_params.Case3` 是 **54.98488 / 9.98355**。
- 结论：Case3 的 Ainf 和 τ 都印错；Ainf 差 3.7 m3/d（约 7%），τ 差 0.04 d。`main.tex:270` 这一行同时与 Table 8、`p3_decline` 两个产物不一致。

### D5（半径倍数算错）0.92–0.95 不是 34–36/40.6

- 论文：`main.tex:310` “radius 40.6 m vs data-implied 34–36 m (ratio 0.92–0.95).”
- 算术：34/40.6 = 0.8374，36/40.6 = 0.8867；若按论文的 40.6/34–36 则是 1.128–1.194。0.92–0.95 无法由这两个数得到。
- 产物：`data/p4_econ.json:mechanism_channel` 的 `Rp_ratio_low=0.9219544`、`Rp_ratio_high=1.0723805` 实际是 `sqrt(0.85)` 与 `sqrt(1.15)`（±15% 渗透率），不是“data-implied 34–36”的比值；`p4_econ` 没有 `R_data` 键。复算：`print(34/40.6, 36/40.6, 40.6/34, 40.6/36)`。

### D6（Table 9 caption 与表体互斥）

- `tables/tab_cv.tex:3`：“Each fold holds out two complete soak levels.”
- 表体 `tables/tab_cv.tex:10-14`：每折 held-out soak levels 是 4 个、4 个、4 个、6 个、6 个（Fold 1: 5,20,35,50；Fold 2: 10,25,40,55；Fold 3: 15,30,45,60；Fold 4/5 各 6 个）；`data/p3_decline.json:split_audit.folds[*].held_out_ts` 同样是 4/6 个。
- 结论：caption 的“two complete soak levels”与表和 `split_audit` 都不符；实际是 4 或 6 个。虽然组间切分本身正确（`PASS_group_whole`、`PASS_test_has_unseen_ts` 均 true），但读者无法从 caption 知道表在说什么。

### D7（印出来的 9.7% 没有产物键）

- 论文：`main.tex:70` “the residual of a smooth fit to the daily rate has a median relative standard deviation of 9.7%.”
- 产物：`data/p3_decline.json:noise_check` 只有 `med_rel_resid=0.1194627`（11.95%）和 `resid_sd_rel=0.2909382`（29.09%）；`data/*.json` 搜索 `9.7`/`0.097` 没有对应的 9.7% 键（有 `rmse_free=0.0976957`，但它是另一个拟合的 RMSE，不是 median relative standard deviation）。
- 结论：这是“印出来的数找不到产物键”的典型；要么把 9.7% 的来源补成 `noise_check` 的新键，要么改成 11.95%/29.09% 的明确口径。复算：`Select-String -Path data\*.json -Pattern '9\.7|0\.097'`。

### D8（“90th percentile”标签与产物不符）

- 论文：`main.tex:312` “the 90th percentile of the relative standard deviation is 29%.”
- 产物：`data/p3_decline.json:noise_check.resid_sd_rel=0.2909382` 是“相对残差标准差”，不是 90th percentile；`data/p4_econ.json:attribution.data_noise.measured_resid_sd_rel` 同值同义。
- 结论：29% 这个数值本身有键，但“90th percentile”是错误标签；若它确实是 sd，就应写“relative standard deviation 29%”；若确实是 p90，则没有 `p90` 键。

## 7. 判定

- 逐句核对：题面 P1–P4 加上补充定义/假设共 18 条可判要求；**P1 的方程/边界、P2 的解析半径、P4 的 NPV 曲线是完整数值交付；P3 的 2–3 方案/工程建议、P4 的地质-运营全局敏感性、Case3 天然裂缝、自由 CO2 相是结构性缺项**。其余多处是 partial（有框架、缺可执行细节）。
- 机器侧：`review_check` PASS、`gauntlet` 16/16 PASS、`figfont` PASS、`verify_numbers` 116/116 PASS；这说明格式、页数、参考文献类型、图内字号和单个数字的产物覆盖都合格，**但不能替代题面契合度**。
- **判 FAIL 的决定性理由（一条即可）**：`problem.txt:74-78` 明确要每个场景 2–3 个折中运营方案 + 工程建议；论文只有 knee/band 和一张两行标定表（`main.tex:244-248`、`Table 5`），没有可执行方案与工程建议，属于结构性缺项，不是措辞问题。第二理由：`problem.txt:69-71` 的 Case3 complex natural fractures 被论文改成 homogeneous isotropic（`main.tex:76-77`，`natural` 0 hit，ρnf Case3=0.08 未使用），模型对象都不是题面那一个。
- 次级（不单独构成 FAIL，但都是可复算硬伤）：D1 NSGA-II 14.06%/1.39% 与 “<1%” 相反；D2 鲁棒性因子无 permeability/in-situ stress 且 Case2 位移 2 天；D3/D4 正文与 Table 4/8 互斥；D5 半径比 0.92–0.95 算术不成立；D6 Table 9 caption 两水平 vs 4/6；D7/D8 9.7% 无键、29% 标签错。
- 与 `00-metrics.md` 的关系：该文件缺失，无法做两数并列；本报告的三条重跑输出即基线，`review_check`/`gauntlet`/`figfont` 与最终快照一致。若之后补生成 `00-metrics.md`，请先核对 `main.pdf` 的 sha256 `CF59A02A...` 和 mtime `11:13:35`，否则会把旧构建的页码/行号带进来。

VERDICT: FAIL
