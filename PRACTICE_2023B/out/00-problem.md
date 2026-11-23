BYTES 40274
# s1 赛题分析 · 2023 “ShuWei Cup” Problem B — 棉秆热解的催化反应

工作区：`E:\数学建模\PRACTICE_2023B`
题面：`problem/problem.txt`（5470 B，152 行，5 页）
附件：`data/Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx`、
`data/Annex II-Pyrolysis Gas Yields of Three Pyrolysis Combinations.xlsx`
本文件是 s1 的唯一交付物，交下一棒：**建模架构手**（→ `out/01-model.md` 与 `code/model_skeleton.py` 的 `MS.PARAMS`）。

---

## 0 结论速览（先给判定，后面逐条给证据）

| 项 | 判定 | 一句话依据 |
|---|---|---|
| 题型 | **B 物理 / 工程优化**（骨架族 B-α） | 题面 L104–106 要 `reaction kinetics`、L11–14 要 `mechanism`、L68–73 是 `fixed-bed pyrolysis` 装置语境；无优化目标函数、无整数决策、无图像输入 |
| 子问数 | 5 | L90–111，编号 (1)…(5) |
| 交付物形态 | Q1 数值 / Q2 方案 / Q3 数值 / Q4 机制 / Q5 预测 | 见 §2；五选一里**「排序」未被用到**，题面无任何优先级/名次要求 |
| 附件规模 | 声明数据格 **100 + 104 = 204** 格 | 见 §3；Annex I 3 表 × 4 产物，Annex II 3 表 × (9/5/5) 组分 |
| 声明区缺失率 | **0.00%**（100/100、104/104 全有值） | 见 §3.3；表内空位是**结构性缺列**，不是缺失值 |
| 最强信号 | DFA/CS 的 H2：6.48 → 43.62 mL/g(daf)，span/2σ = **14.47** | 见 §3.6 |
| 最弱信号 | Char：CS 表 span 0.76 < 2σ 2.94；LG 表 span 1.19 < 2σ 5.73 | **这两条必须在正文写「无显著变化」**，见 §4-M2 |
| 最容易被误读 | 三处，见 §4 | 「5% 误差」「100/100」「八档比例」 |
| 自设常数 | 12 项，全部列在 §6.2，**一条都不许当题给** | 温度数值题面未给，见 §6.2-T1 |

---

## 1 逐句抄出「要求你」的句子（带 problem.txt 行号）

抄写规则：只抄**要求句 / 约束句 / 交付句**三类，不解读、不改写。原文保留大小写与标点。

### 1.1 总起要求句

> **L88–89**　`Please complete the following questions through mathematical modeling:`

这一句把后面 5 个子问统一框成「必须建模，不许纯定性叙述」。

### 1.2 五个子问的要求句（逐字）

**Q1 — L90–95**
> **L90**　`(1) For each pyrolysis combination in Annex I, analyze the yield of`
> **L91**　`pyrolysis products (tar, water, coke residue, syngas) in relation to the`
> **L92**　`mixing ratios of the corresponding pyrolysis combinations, and explain`
> **L93**　`whether desulfurization ash, as far as it is used as a catalyst, plays a`
> **L94**　`significant role in facilitating the pyrolysis of cotton stalks, cellulose, and`
> **L95**　`lignin?`

**Q2 — L96–99**
> **L96**　`(2) According to Annex II, for each of the three pyrolysis`
> **L97**　`combinations, the effect of the mixing ratio of the pyrolysis combinations`
> **L98**　`on the yield of each group of pyrolysis gas is discussed and explained by`
> **L99**　`making corresponding images.`

**Q3 — L100–103**
> **L100**　`(3) Under the catalytic action of the same proportion of desulfurized`
> **L101**　`ash, is there a significant difference in the yields of the products`
> **L102**　`generated from the pyrolysis of CE and LG, as well as the yields of the`
> **L103**　`components of the pyrolysis gas? Please provide reasons.`

**Q4 — L104–106**
> **L104**　`(4) How do we establish a catalytic reaction mechanism model of`
> **L105**　`desulfurized ash for model compounds such as CE and LG and model the`
> **L106**　`reaction kinetics for analysis?`

**Q5 — L107–111**（跨页：L107–108 在 page 3，L109 是分页符，L110–111 在 page 4）
> **L107**　`(5) Please use mathematical models or AI learning methods to make`
> **L110**　`predictions on the yields or quantities of the pyrolysis products under`
> **L111**　`limited data conditions.`

### 1.3 约束句（决定假设与符号）

> **L16–19**　`A certain chemical engineering laboratory employed the model compound method to establish pyrolysis combinations: desulfurization ash with cotton stalk and desulfurization ash with model compounds.`
> **L19–20**　`The pyrolysis combinations were subjected to pyrolysis at different mixing ratios`
> **L30–31**　`in selecting model compounds, it was necessary to consider their controllability and stability in reaction`
> **L34–36**　`performance during the experiment, as well as their contribution to cotton stalk pyrolysis.`
> **L37–44**　`CE (Cellooligosaccharide) and LG (Lignin) are representative components of cellulose and lignin in the cotton stalk, which can represent the biomass characteristics of the cotton stalk itself.`
> **L68–75**　`The desulfurization ash/biomass pyrolysis experiment was conducted with fixed-bed pyrolysis at mixing ratios of 10/100, 20/100, 30/100, 40/100, 50/100, 60/100, 80/100, and 100/100.`
> **L76–77**　`under these experimental conditions, the relative error of parallel experiments is approximately 5%.`
> **L78–80**　`If the mixing ratios were chosen to be too small, such as 5/100 or 7/100, the relative error would have a significant impact on the experimental results and seriously affect the exploration and optimization process of the experiment.`
> **L145–146**　`All experiments in this study were conducted at the same temperature.`

### 1.4 交付句（决定产出形态）

> **L81–84**　`If it is possible to use a mathematical model and AI learning to predict the pyrolysis product yield or production under conditions with limited data, it would not only greatly reduce the time required for experimental optimization but also provide accurate guidance on the trend of changes in the distribution of pyrolysis products.`
> **L96–99**　（Q2）`… discussed and explained by making corresponding images.` ← 交付物是**图**
> **L103**　（Q3）`Please provide reasons.` ← 数值差异之外还要机制解释
> **L67**　`The experimental results are shown in Appendix 1 and Appendix 2.`
> **L112–130**　Annex I / Annex II 两个 xlsx 文件名
> **L131–137**　`Pyrolysis Combinations: Desulfurized Ash-Cotton Stalk; Desulfurized Ash-CE; Desulfurized Ash-LG.`
> **L138**　`Pyrolysis Products: Tar, Water, Char, Syngas.`
> **L139–140**　`Pyrolysis Gas Components for Desulfurized Ash and Cotton Stalk: H2, CO, CO2, CH4, C2H6, C3H8, C3H6, C2H4, C4H10.`
> **L141–142**　`Pyrolysis Gas Components for Desulfurized Ash and CE: H2, CO, CO2, CH4, C2H6.`
> **L143–144**　`Pyrolysis Gas Components for Desulfurized Ash and LG: H2, CO, CO2, CH4, C2H6.`

### 1.5 非要求句（明确排除，防止误当约束）

> **L1 / L33 / L85 / L109 / L148**　`===== page N =====` — PDF 抽取的分页符，不是题面内容。
> **L2**　`2023_“ShuWei Cup”` — 赛事标识。
> **L149–152**　`Title Statement: … any form of tampering, editing and other purposes is strictly prohibited …` — 版权声明，**不产生任何建模要求**，不得写进假设。
> **L12**　`(Noun definitions can be found in the appendix)` — 指 L131–146 的名词表，是**口径来源**而非独立要求。

**门 0 核对**（`templates/THINKING-CANVAS.md:23`：每个 Qx 有且仅有一条题目原文句子作依据）：
Q1←L90–95、Q2←L96–99、Q3←L100–103、Q4←L104–106、Q5←L107–111，五条一一对应，无一对多、无多对一。**通过**。

---

## 2 每个子问的交付物形态（五选一 + 理由）

五选一：**数值 / 方案 / 排序 / 预测 / 机制**。

| 问 | 形态 | 题面触发短语（行号） | 理由（为什么是这一种，不是别种） |
|---|---|---|---|
| Q1 | **数值** | L91–92 `analyze the yield … in relation to the mixing ratios`；L93–94 `plays a significant role` | 「significant」是**可判定的二值结论**，必须落到一个数上（显著性判据 + 变化幅度 + 极值位置）。只写机制会答不出"是否显著"。机制是**理由**，不是交付主体。 |
| Q2 | **方案** | L96–99 `discussed and explained by making corresponding images` | 交付物是**一套图族**（3 组合 × 各自组分数 = 9 + 5 + 5 = 19 条曲线，按组分归并成图）+ 图注解释。这是"方案"（可交付的图表编排），不是单个数值。 |
| Q3 | **数值** | L100–103 `is there a significant difference … Please provide reasons` | 先给差异量与其显著性（数值），再给机制（理由）。若判成"机制"，"significant" 这个二值判断就没有承载物。 |
| Q4 | **机制** | L104–106 `establish a catalytic reaction mechanism model … model the reaction kinetics` | 交付物是**模型结构本身**：反应网络 + 速率方程 + 参数辨识（A、E_a、n）+ 拟合优度。这一问的产物是方程，不是数。 |
| Q5 | **预测** | L107–111 `make predictions … under limited data conditions` | 明确要"预测值 + 预测区间 + 外推边界"。必须与 Q1–Q3 的**拟合/解释**区分开：拟合是 in-sample，预测要 out-of-sample。 |

**未用到的形态：排序。** 题面 152 行内没有任何「按…排序 / 优先级 / 名次 / 最优选择」的要求；L78–80 提 `optimization process` 只是解释为何不用 5/100、7/100，**不是**要本文做优化求解。若下游把 Q1 写成"各产物影响排序"，属自加要求，会与 L91–92 的 `in relation to` 脱节。

---

## 3 附件数据实测（行数 / 列名 / 缺失率 / 量级）

### 3.1 复算命令（本次实际执行，可原样重跑）

解释器：`E:\Mini\envs\mathmodel\python.exe`（Python 3.11.18，含 pandas / numpy）。

```powershell
$PY = 'E:\Mini\envs\mathmodel\python.exe'
$F1 = 'E:\数学建模\PRACTICE_2023B\data\Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx'
$F2 = 'E:\数学建模\PRACTICE_2023B\data\Annex II-Pyrolysis Gas Yields of Three Pyrolysis Combinations.xlsx'

# 形状 + 机械缺失率
& $PY -c "import pandas as pd;A=pd.read_excel(r'$F1',header=None);print('I',A.shape,A.size,int(A.isna().sum().sum()),round(100*A.isna().sum().sum()/A.size,1))"
& $PY -c "import pandas as pd;A=pd.read_excel(r'$F2',header=None);print('II',A.shape,A.size,int(A.isna().sum().sum()),round(100*A.isna().sum().sum()/A.size,1))"

# 声明数据格数（按表头行的比例个数 × 产物/组分数）
& $PY -c "import pandas as pd;A=pd.read_excel(r'$F1',header=None);print([sum(1 for x in A.iloc[h,1:].tolist() if pd.notna(x)) for h in (1,9,16)])"
& $PY -c "import pandas as pd;A=pd.read_excel(r'$F2',header=None);print([(r1-r0+1,nc) for r0,r1,nc in ((2,7,9),(11,15,5),(19,23,5))])"

# Annex I 闭合性：每个比例列四产物求和
& $PY -c "import pandas as pd;A=pd.read_excel(r'$F1',header=None);print([round(sum(A.iloc[r0+i,1+j] for i in range(4)),6) for r0,n in ((2,9),(10,8),(17,8)) for j in range(n)])"

# 掺比 → DFA 质量分数
& $PY -c "print([(a, round(100*a/(a+100),4)) for a in (10,20,30,40,50,60,80,100)])"
```

### 3.2 Annex I（热解产物产率）结构

| 项 | 实测值 |
|---|---|
| 文件 | `Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx`，11335 B |
| sha256 | `9cf303a3a30ee5fd96ec851e02f589fb7296d6e7c86ed2d2c72cc2629acae171`（与 `data/ledger.json` 一致） |
| sheet | `Sheet1`（唯一） |
| 原始网格 | **30 行 × 10 列 = 300 格** |
| 有效表 | 3 张：Tab1 `DFA/CS`（r0）、Tab2 `DFA/CE`（r8）、Tab3 `DFA/LG`（r15） |
| 表头行（0 基） | Tab1 = r1，Tab2 = r9，Tab3 = r16 |
| 数据行（0 基） | Tar = r2/r10/r17；Water = r3/r11/r18；Char = r4/r12/r19；Syngas = r5/r13/r20 |
| 行标签原文 | `Tar yield` / `Water yield` / `Char yield` / `Syngas yield` |
| 列名（掺比） | Tab1 共 **9** 档：`0/100, 10/100, 20/100, 30/100, 40/100, 50/100, 60/100, 80/100, 100/100`；Tab2/Tab3 各 **8** 档：`10/100 … 100/100`（**无 0/100**） |
| 单位 | 表头写明 `wt.%(daf)`；脚注 r27 `daf: Dry ash-free basis` |
| 脚注行 | r25 `DFA–Desulfurized fly ash`（源文件编码损坏，显示为 `DFA??Desulfurized`）、r26 `CS–Cotton stalk`、r27 `daf`、r28 `CE: Cellulose`、r29 `LG: Lignin` |

### 3.3 缺失率（必须分清三种口径，混用会写出错误的数）

| 口径 | Annex I | Annex II | 说明 |
|---|---|---|---|
| **声明数据区缺失率** | **0 / 100 = 0.00%** | **0 / 104 = 0.00%** | 表头声明的每一格都有数值。**这是唯一可以写进正文的缺失率。** |
| 结构性缺列（不是缺失值） | Tab2/Tab3 各缺 `0/100` 一档 | Tab2/Tab3 各缺 `0/100, 10/100, 30/100, 60/100` 四档 | 附件没做那几档实验，属于**实验设计**，不得计入缺失率 |
| 机械 NaN 率（含标题/空行/图例） | 152 / 300 = **50.7%** | 209 / 360 = **58.1%** | 这是把标题行、空行 r6–r7/r21–r24、脚注 r25–r29 全算进分母的结果。**只能作为脚本自检数，不得当缺失率报** |

**红线**：正文若写「附件缺失率 50.7%」，是把结构性空行当缺失值，属口径错误。正确写法是「声明数据区无缺失；Annex I 的 CE/LG 两表与 Annex II 的 CE/LG 两表未设 0/100 空白对照，Annex II 的 CS 表缺 10/100、30/100、60/100 三档」。

### 3.4 Annex II（热解气体产率）结构

| 项 | 实测值 |
|---|---|
| 文件 | `Annex II-Pyrolysis Gas Yields of Three Pyrolysis Combinations.xlsx`，11584 B |
| sha256 | `ed71ce182be2767eec52abe429c038b098d035497665f89069bd4396af610d29`（与 ledger 一致） |
| 原始网格 | **30 行 × 12 列 = 360 格** |
| 有效表 | Tab1 `DFA/CS`（r0）、Tab2 `DFA/CE`（r9）、Tab3 `DFA/LG`（r17） |
| 表头行（0 基） | Tab1 = r1，Tab2 = r10，Tab3 = r18 |
| 数据行（0 基） | Tab1 = r2–r7（6 档）；Tab2 = r11–r15（5 档）；Tab3 = r19–r23（5 档） |
| 列名（组分） | Tab1 共 **9** 个：`H2, CO, CO2, CH4, C2H6, C3H8, C3H6, C2H4, C4H10`；Tab2/Tab3 各 **5** 个：`H2, CO, CO2, CH4, C2H6` |
| 行名（掺比） | Tab1：`0/100, 20/100, 40/100, 50/100, 80/100, 100/100`（6 档）；Tab2/Tab3：`20/100, 40/100, 50/100, 80/100, 100/100`（5 档） |
| 单位 | 表头 `mL/g,daf`；r1 备注 `Gas Yield, which refers to the amount of gas produced per gram of raw material.` |
| 脚注行 | r25–r29，与 Annex I 同构 |

### 3.5 量级（供 建模架构手 定初值与无量纲化）

**Annex I，wt.%(daf)，每个比例列四产物之和恒为 100.000000（25/25 列全对，实测）**

| 产物 | DFA/CS 范围 | DFA/CE 范围 | DFA/LG 范围 | 全局 |
|---|---|---|---|---|
| Tar | 19.46 → 12.13 | 34.42 → 45.28 | 18.06 → 8.19 | 8.19 – 45.28 |
| Water | 26.84 → 31.02 | 27.42 → 16.14 | 15.30 → 23.69 | 15.30 – 31.02 |
| Char | 29.21 → 29.87 | 21.43 → 24.91 | 58.17 → 57.43 | 21.43 – 58.17 |
| Syngas | 24.49 → 26.98 | 16.73 → 13.97 | 8.47 → 10.69 | 8.47 – 28.45 |

**闭合性结论**：Annex I 四产物构成**闭合单纯形**（Σ = 100 wt.%(daf)）。这直接给出一个硬约束 `Tar+Water+Char+Syngas = 100`，建模时若用四个独立回归会破坏该约束 —— 必须用 3 维 + 归一化，或 log-ratio（CLR/ILR）变换。**这是本题最容易在方法章踩的坑。**

**Annex II，mL/g(daf)，行和不闭合（绝对体积产率，不是百分比）**

| 表 | 行和范围 | 说明 |
|---|---|---|
| DFA/CS | 120.240 – 153.250 | 6 档，随掺比单调上升 |
| DFA/CE | 69.100 – 80.200 | 5 档，无单调性 |
| DFA/LG | 68.000 – 95.205 | 5 档，20/100 处最低 68.000 |

| 组分 | 全局范围 |
|---|---|
| H2 | 0.67 – 65.80 |
| CO | 5.30 – 25.93 |
| CO2 | 2.00 – 60.40 |
| CH4 | 0.70 – 33.86 |
| C2H6 | 0.05 – 13.80 |
| C3H8 | 0.55 – 0.88 |
| C3H6 | 0.35 – 0.41 |
| C2H4 | 0.71 – 0.81 |
| C4H10 | 0.25 – 0.56 |

**量级落差必须写进正文**：H2 跨三个数量级（0.67 → 65.8，**98.2 倍**），C3H6 / C2H4 跨不到 1.2 倍。同一张图上直接画 9 条曲线会让小量级组分被压成平线 —— Q2 必须**分栏或对数轴**，否则图无法读，G6（图内有效字号）和可读性都会掉。

### 3.6 噪声地板与显著性判据（由 L76–77 派生，这是 Q1/Q3 的判据来源）

题给：`the relative error of parallel experiments is approximately 5%`（L77）。取 σ = 0.05·y，则 **2σ 判据 = 0.10·y**。
两档判据：

- **趋势级**：`span / (0.10·mean) > 1` —— 整条曲线的总变化是否超噪。
- **单步级**：`|y_{k+1} − y_k| > 0.10·max(|y_k|, |y_{k+1}|)` —— 相邻两点之差是否超噪。

**Annex I 趋势级实测**（span / 2σ(mean)）：

| 组合 | Tar | Water | Char | Syngas |
|---|---|---|---|---|
| DFA/CS | 5.04 | 1.45 | **0.26** | 1.46 |
| DFA/CE | 2.58 | 5.86 | 1.45 | 2.73 |
| DFA/LG | 8.73 | 4.11 | **0.21** | 3.12 |

**Annex I 单步级实测**（超噪步数 / 总步数）：

| 组合 | Tar | Water | Char | Syngas |
|---|---|---|---|---|
| DFA/CS | 2/8 | 0/8 | 0/8 | 0/8 |
| DFA/CE | 2/7 | 4/7 | 1/7 | 1/7 |
| DFA/LG | 4/7 | 1/7 | 0/7 | 2/7 |

**这张表给出两个必须在正文显式说明的反直觉点**：

1. **DFA/CS 的 Water 单步 0/8 全不超噪，但趋势级 1.45 > 1** → 结论只能写「单调上升趋势成立（总漂移 4.18 wt.% > 2σ_mean 2.89），但没有任何相邻一步单独显著」。写成「每增加 10 个掺比单位水产率显著上升」是**假阳性**。
2. **Char 两个组合都落在噪声内**（0.26、0.21）→ 必须写「Char 产率对掺比不敏感」，不许把它讲成"略有上升/略有下降"。

**Annex II 趋势级与单步级实测**（关键项）：

| 组合 | 组分 | span | 2σ(mean) | span/2σ | 单调性 | 超噪步 |
|---|---|---|---|---|---|---|
| DFA/CS | H2 | 37.140 | 2.566 | **14.47** | 严格↑ | 5/5 |
| DFA/CS | C4H10 | 0.310 | 0.038 | 8.23 | 非单调（峰在 40/100） | 5/5 |
| DFA/CS | CO2 | 9.490 | 5.415 | 1.75 | 严格↓ | **0/5** |
| DFA/CS | C3H6 | 0.060 | 0.038 | 1.59 | 非单调 | 0/5 |
| DFA/CE | CO2 | 16.700 | 0.792 | **21.09** | 严格↓ | 4/4 |
| DFA/CE | C2H6 | 10.600 | 0.668 | 15.87 | 严格↓ | 3/4 |
| DFA/CE | H2 | 39.200 | 5.074 | 7.73 | 峰在 80/100 | 4/4 |
| DFA/LG | H2 | 0.140 | 0.075 | 1.86 | 非单调 | **0/4** |
| DFA/LG | CO | 5.705 | 1.766 | 3.23 | 严格↑ | **0/4** |
| DFA/LG | C2H6 | 0.040 | 0.007 | 5.71 | 非单调 | 4/4 |

**DFA/LG 的 CO 是本题最刁的一条**：严格单调上升（15.23 → 20.935），span/2σ = 3.23 > 1，但**单步 0/4 全不超噪**。原因是最小步长 0.53 相对 15.23 的 2σ 阈值 1.576 太小。正确写法：「CO 随掺比单调上升，累计增幅 5.705 mL/g(daf) 超出 2σ 判据（1.766），但任一相邻档位之间均未单独超噪，故只支持趋势性结论。」—— 这句话同时挡住了"过度解读"和"漏报真实趋势"两种失分。

**DFA/LG 的 C2H6 反过来**：span 只有 0.040 mL/g(daf)（0.05–0.09），span/2σ = 5.71 看着很高，但绝对值是**仪器噪声量级**。判据只对"相对变化"敏感，对"绝对可测性"不敏感。→ 必须补一句绝对值判断：「C2H6 在 LG 体系始终 < 0.1 mL/g(daf)，无论相对变化如何，其绝对贡献可忽略。」

### 3.7 掺比 → 质量分数的换算（口径必写）

附件列头 `a/100` 的分母是**生物质质量**（`mL/g,daf` 与 `wt.%(daf)` 的 daf 基准都是生物质干基），因此 DFA 的质量分数为 `a/(a+100)`：

| 列头 | DFA 质量分数 | DFA 摩尔/质量配比 |
|---|---|---|
| 10/100 | **9.0909%** | 0.10 |
| 20/100 | 16.6667% | 0.20 |
| 30/100 | 23.0769% | 0.30 |
| 40/100 | 28.5714% | 0.40 |
| 50/100 | 33.3333% | 0.50 |
| 60/100 | 37.5000% | 0.60 |
| 80/100 | 44.4444% | 0.80 |
| 100/100 | **50.0000%** | 1.00 |

**`100/100` 不是"纯 DFA"，是 DFA 与生物质等质量比（DFA 占 50%）。** 见 §4-M3。

---

## 4 三处最容易被误读的表述

每条写成「读者会以为 X，实际是 Y」，并给实测证据与正确写法。

### M1（约束在不等式右端）——「5% 相对误差」

> **读者会以为**：`the relative error of parallel experiments is approximately 5%`（L77）是**本文模型要达到的精度指标**，或者是"数据够准，可以直接拟合"的背书。
>
> **实际是**：它是**数据自身的不确定度**，用途是给显著性判据定一个**不等式右端**——`|Δy| > 2×0.05×y` 才算"显著"。它出现在判据的右边，不是模型要逼近的左边目标。把它当精度目标会写出"本文模型误差 5%，精度良好"这类无信息自夸（对应反模式 P2：`the results are accurate` 无量化自夸）。

**证据**：L76–77 的上下文是"为什么选这些掺比"（L75 `This choice of mixing ratios was based on the fact that…`），紧接着 L78–80 说掺比太小（5/100、7/100）时 `the relative error would have a significant impact`。所以 5% 是**实验设计的下界约束**，不是模型指标。

**实测后果**：若不用这个判据，Char 的 span 0.76（DFA/CS）会被讲成"随掺比上升"；用上判据后 0.76 < 2σ 2.94，必须写"无显著变化"。两种写法差一个结论。

**正确写法**：「题给平行实验相对误差约 5%，本文据此取 2σ = 0.10·y 作为显著性阈值；凡变化幅度未超此阈值的产物，本文不主张其随掺比变化。」

### M2（可容纳 ≠ 必须 / 有数 ≠ 有信号）——「附件每格都有数」

> **读者会以为**：附件 12 张表（3 组合 × 4 产物 + 3 组合 × 气体组分）里**每一格都有数值**，所以每一条曲线都可以下趋势结论，Q1 应当逐条报"上升/下降"。
>
> **实际是**：有数值 ≠ 有信号。按 L77 的 2σ 判据，**至少 2 条产物曲线和 3 条气体曲线落在噪声内**，必须在正文写"无显著变化"而不是"略有变化"：
> - Char(DFA/CS)：span 0.76，2σ(mean) 2.94，**比值 0.26**
> - Char(DFA/LG)：span 1.19，2σ(mean) 5.73，**比值 0.21**
> - CO2(DFA/CS)：span 9.49，2σ(mean) 5.42，比值 1.75 但**单步 0/5**
> - H2(DFA/LG)：span 0.14，2σ(mean) 0.075，比值 1.86 但**单步 0/4**，且绝对值 0.67–0.81 属噪声量级
> - CO(DFA/LG)：单调↑且 span/2σ = 3.23，但**单步 0/4**

**为什么这是"可容纳 ≠ 必须"的同构**：表格能容纳 100 + 104 个数字，不等于每个数字都必须被解释成趋势。把它读成"每格必须有结论"，就会给 Char 编出一条不存在的趋势。

**正确写法**：「Char 产率在三个组合中的跨度分别为 0.76、3.48、1.19 wt.%(daf)，均未超过 2σ 判据（2.94、2.41、5.73），故本文判定 DFA 掺比对焦渣产率无显著影响。」—— 这句话本身就是一个**有价值的负结论**，评委给分，编趋势扣分。

### M3（时点/端点错位）——「八档掺比 10/100 … 100/100」

> **读者会以为**：`10/100, 20/100, 30/100, 40/100, 50/100, 60/100, 80/100, and 100/100`（L74–75）是一条**从 0 到 100% 等距的连续网格**，`100/100` 就是"纯脱硫灰"，而且题面的 8 档就是全部实验点。
>
> **实际是**三件事都错：
> 1. **不是等距**：步长是 `10×6 + 20×2`（实测 `[10,10,10,10,10,10,20,20]`），后段加密到 20。做等距差分/等距回归会引入系统偏差。
> 2. **`100/100` 的 DFA 质量分数只有 50.0000%**（§3.7），不是 100%。写成"纯 DFA 热解"是量级级错误。
> 3. **题面漏列了 `0/100` 空白对照**：Annex I 的 Tab1（DFA/CS）与 Annex II 的 Tab1（DFA/CS）都含 `0/100` 列，而 L74–75 的 8 档里没有它。也就是说**题面比例集 ⊊ 附件列集**。若严格按题面 8 档建模，会丢掉唯一的纯生物质基线，Q1 里"催化剂是否显著促进"就失去对照。

**证据**：Annex I Tab1 列头实测 `['0/100','10/100',…,'100/100']`（9 档）；Annex II Tab1 行名实测 `['0/100','20/100','40/100','50/100','80/100','100/100']`（6 档）。两附件比例网格还不一致：Annex I 有 10、30、60 档，Annex II 没有。

**正确写法**：「题面列出 8 档掺比（L74–75）；Annex I 的 DFA/CS 表与 Annex II 的 DFA/CS 表另设 `0/100` 空白对照（纯棉秆），本文将其作为催化效应的基线纳入；两附件比例网格不同（Annex I 为 {0,10,20,30,40,50,60,80,100}，Annex II 为 {0,20,40,50,80,100}），跨附件比较只在公共档位 {20,40,50,80,100} 上进行。」

### 附加 M4（名词口径冲突，必须择一声明）

> **读者会以为**：`CE` 就是纤维素（Cellulose）。
>
> **实际是**：题面 L37–38 把它展开为 `CE (Cellooligosaccharide)`（纤维寡糖，纤维素的部分水解/低聚产物），而**附件脚注 r28 写 `CE: Cellulose`**。两者不是同一物质：寡糖有还原端、聚合度低、热解行为与高聚纤维素不同。

**处理**：论文必须**择一并在假设或符号表里声明**，建议沿用题面 L37 的 `Cellooligosaccharide`（题面是主口径），并加一句「附件脚注记为 Cellulose，本文按题面口径视为纤维寡糖类模型化合物，该差异不影响掺比趋势结论」。不声明会在口径审计（G16）被判「同一名词被两种含义用过」。

### 附加 M5（恒定 ≠ 已知）

> **读者会以为**：`All experiments in this study were conducted at the same temperature`（L145–146）意味着温度已知，可以写进模型参数。
>
> **实际是**：题面只说"同一温度"，**没有给数值**。所以温度在本题里**不是自变量、不是参数、无法做温度敏感性分析**；任何温度数值都是**自设**，必须显式标注，且不能出现在"题给条件"里。

---

## 5 题型判定

### 5.1 判定：**B 物理 / 工程优化**，骨架族 **B-α（机理章 + 问内五件套）**

### 5.2 判据（逐条对 `templates/THINKING-CANVAS.md:34` 的 B 类判定信号「装置、传热/传质、受力、调度、容量」）

| 信号 | 题面证据 | 命中 |
|---|---|---|
| **装置** | L68–73 `fixed-bed pyrolysis`（固定床热解）；L16–18 `chemical engineering laboratory employed the model compound method` | ✅ 强 |
| **机理** | L11 `studying the mechanism and properties of cotton stalk pyrolysis products`；L13–14 `investigating the mechanism and effects of catalysts`；L24–25 `catalytic mechanism and effects` | ✅ 强 |
| **动力学** | L104–106 `establish a catalytic reaction mechanism model … model the reaction kinetics for analysis` | ✅ 决定性 |
| **参数辨识** | L81–84 `use a mathematical model and AI learning to predict`；L107–111 `under limited data conditions` | ✅ 中（指向 Q5） |

### 5.3 排除其他四类的理由

| 类 | 排除理由 |
|---|---|
| **A 图像 / 几何 / 工程测量** | 题面与附件**零图像输入**：两个 xlsx 全是数值表，无图、无点云、无测距对象。L98–99 的 `making corresponding images` 是**输出**图，不是输入图。 |
| **C 数据 / 统计 / 政策** | 数据是**受控实验表**（3 组合 × 固定温度 × 8–9 档掺比），不是观测型面板/时序/政策情景；无年份维度、无地区维度、无政策变量。Q1/Q3 虽用统计检验，但只是**手段**，主问题（Q4）要机理模型。**C 是次选族**，Q5 可借 C 的小样本回归方法。 |
| **D 组合 / 整数 / 前沿** | 题面无整数决策变量、无指派/装箱/路径、无规模阶梯。L78–80 的 `optimization process` 是描述实验选点，不是要解优化问题。 |
| **E 聚类 / 时序（纯）** | 掺比不是时间轴；无平稳性/白噪/阶数识别需求。三组合可做聚类对比，但那是分析手段而非题目要求。 |

### 5.4 对下一棒的族内要求（B-α 必带）

按 `WORKFLOW.md:99` 与 `templates/THINKING-CANVAS.md:34`，B-α 族**必须有「机理论证 + 问内检验」两件**，且明令 **不许「仿真即验证」**：

1. **机理论证章**：为什么脱硫灰（CaO/CaSO4 基）会改变产物分布 —— 碱性位催化脱羧/脱羰、CaO 吸收 CO2 推动水煤气变换（WGS）向右、灰中无机盐促进二次裂解。这一章要能解释 §3.6 里 H2 单调升、CO2 单调降、CH4 先升后降这三条形状。
2. **问内检验**：每个子问末尾必须有量化检验（拟合残差、交叉验证、参数置信区间），不得只报拟合曲线好看。
3. **Q4 必须是真动力学模型**（不是"机理示意 + 定性讨论"）：至少给出 `dα/dt = A·exp(−E_a/RT)·f(α)` 形式的速率方程、`f(α)` 的选定理由、以及 A / E_a / n 的辨识结果与置信区间。

---

## 6 题面常数表（供 建模架构手 直接转成 `MS.PARAMS`）

### 6.1 题给常数（**全部有 problem.txt 行号，不得改写成别的出处**）

| # | 符号 | 值 | 单位 | 出处行号 | 原文 |
|---|---|---|---|---|---|
| C01 | `r_1` | 10/100 | 质量比（DFA : 生物质），无量纲 | L74 | `10/100` |
| C02 | `r_2` | 20/100 | 同上 | L74 | `20/100` |
| C03 | `r_3` | 30/100 | 同上 | L75 | `30/100` |
| C04 | `r_4` | 40/100 | 同上 | L75 | `40/100` |
| C05 | `r_5` | 50/100 | 同上 | L75 | `50/100` |
| C06 | `r_6` | 60/100 | 同上 | L75 | `60/100` |
| C07 | `r_7` | 80/100 | 同上 | L75 | `80/100` |
| C08 | `r_8` | 100/100 | 同上 | L75 | `100/100` |
| C09 | `r_neg1` | 5/100 | 同上 | L78 | `such as 5/100`（**反例，未采用**，不得当实验点） |
| C10 | `r_neg2` | 7/100 | 同上 | L78 | `or 7/100`（**反例，未采用**） |
| C11 | `eps_rel` | 5% = 0.05 | 无量纲（相对误差） | L77 | `approximately 5%` |
| C12 | `sigma_y` | 0.05·y | 与 y 同（wt.%(daf) 或 mL/g(daf)） | 由 C11 派生 | — |
| C13 | `thr_2sigma` | 0.10·y | 同上 | 由 C11 派生 | — |
| C14 | `N_comb` | 3 | 组（DFA/CS、DFA/CE、DFA/LG） | L131–137 | 三个组合名 |
| C15 | `N_prod` | 4 | 种（Tar、Water、Char、Syngas） | L138 | `Tar, Water, Char, Syngas` |
| C16 | `N_gas_CS` | 9 | 种（H2、CO、CO2、CH4、C2H6、C3H8、C3H6、C2H4、C4H10） | L139–140 | 9 个化学式 |
| C17 | `N_gas_CE` | 5 | 种（H2、CO、CO2、CH4、C2H6） | L141–142 | 5 个化学式 |
| C18 | `N_gas_LG` | 5 | 种（同 C17） | L143–144 | 5 个化学式 |
| C19 | `N_Q` | 5 | 问 | L90–111 | `(1)…(5)` |
| C20 | `N_annex` | 2 | 份附件 | L112–130 | `Annex I` / `Annex II` |
| C21 | `year` | 2023 | — | L2、L150 | `2023_“ShuWei Cup”` / `in 2023` |
| C22 | `edition` | 9 | 届 | L149 | `the 9th “ShuWei Cup”` |
| C23 | `T_const` | 恒定，**数值未给** | K（数值缺） | L145–146 | `conducted at the same temperature` |

### 6.2 自设常数（**题面没有，全部标「自设」，一条都不许写成「题给」**）

| # | 符号 | 建议值 | 单位 | 为什么必须自设 | 风险 |
|---|---|---|---|---|---|
| T1 | `T_py` | `[自设]` 800 | K | 题面 L145–146 只说同一温度，未给数值 | 若写成"题给 800 K"，G1 逐条比对直接判 FAIL |
| T2 | `beta_heat` | `[自设]` 10 | K/min | 升温速率题面未提 | 影响 E_a 的绝对值，只影响量级不影响趋势 |
| T3 | `t_hold` | `[自设]` 30 | min | 停留时间未给 | 同上 |
| T4 | `Q_carrier` | `[自设]` 100 | mL/min | 载气流速未给（`mL/g,daf` 隐含但流量未知） | 影响气体停留/二次裂解 |
| T5 | `d_p` | `[自设]` 0.2 | mm | 粒径未给 | 影响传热限制，进而影响表观 E_a |
| T6 | `m_sample` | `[自设]` 5 | g | 单次进样量未给 | 与 T4 共同决定 `mL/g` 的可比性 |
| T7 | `A_pre` | `[自设]` 待辨识，初值 1e10 | s⁻¹ | 指前因子题面未给 | 必须与 E_a 联合辨识，不得单独固定 |
| T8 | `E_a` | `[自设]` 待辨识，先验 100–250 | kJ/mol | 活化能题面未给 | 与 T2 强耦合，需同时扰动做敏感性 |
| T9 | `n_order` | `[自设]` 1（先验）| — | 反应级数题面未给 | 应给 n=0/1/2 三档对比，不许只报一档 |
| T10 | `f_alpha` | `[自设]` 选 R2/R3/D1 三种对比 | — | 机理函数形式题面未给 | 单一一律选 `f(α)=1−α` 属未经论证 |
| T11 | `dfa_comp` | `[自设]` CaO 40% / CaSO4 30% / SiO2 15% / 其他 15% | wt.% | 脱硫灰化学组成题面与附件均未给 | 只能用文献典型值，必须标注"文献值，非本题数据" |
| T12 | `grid_pred` | `[自设]` r ∈ {15,25,35,45,55,70,90}/100 | — | Q5 的预测工况网格题面未给 | 必须声明"内插/外推"边界，不得声称已实验验证 |

### 6.3 派生量（**由题给数据算出，可复算，不算自设也不算题给**）

| # | 量 | 值 | 复算方式 |
|---|---|---|---|
| D01 | `w_DFA(r)` | 10/100→9.0909%；50/100→33.3333%；100/100→50.0000% | `100·a/(a+100)`，见 §3.7 命令 |
| D02 | 四产物闭合约束 | `Tar+Water+Char+Syngas ≡ 100.000000` | Annex I 25 列全对，见 §3.1 命令 |
| D03 | `span/2σ` 12 项 | 见 §3.6 表 | `(max−min)/(0.1·mean)` |
| D04 | 单步超噪计数 12 项 | 见 §3.6 表 | `|Δy| > 0.1·max(|y_k|,|y_{k+1}|)` |
| D05 | Q3 差异 9 项 | 见 §7.2 | 同档位 CE 值 − LG 值 |
| D06 | `AnnexII r21–r23 c2` 精度异常 | 17.305 / 19.075 / 20.935 | 三值为 .005 网格，同列其余为 .01 网格 → 疑似平行实验算术平均回填，**引用时按 3 位小数原样保留并加注** |

---

## 7 给下一棒的预计算（可直接进 Q1/Q3 正文，省一轮返工）

### 7.1 Q1 的催化效应基线（DFA/CS，`0/100` → `100/100`）

| 产物 | 0/100 | 100/100 | 绝对变化 | 相对变化 | 2σ 判据 | 结论 |
|---|---|---|---|---|---|---|
| Tar | 19.46 | 12.13 | −7.33 | **−37.7%** | 1.95 | 显著↓ |
| Water | 26.84 | 31.02 | +4.18 | **+15.6%** | 3.10 | 显著↑ |
| Char | 29.21 | 29.87 | +0.66 | +2.3% | 2.99 | **不显著** |
| Syngas | 24.49 | 26.98 | +2.49 | +10.2% | 2.70 | 不显著（< 2σ 2.70） |

**这是 Q1「催化剂是否显著促进」最硬的一条证据**：脱硫灰把 Tar 砍掉 37.7%、把 Water 抬高 15.6%，Char 基本不动。**"促进热解"的正确含义是促 Tar 二次裂解 + 促脱水，不是促成炭。**

### 7.2 Q3 的 CE vs LG 差异（5 个公共档位 20/40/50/80/100）

**产物（wt.%(daf)）**

| 产物 | CE − LG 五档差值 | 2σ 阈值 | 超噪 | 结论 |
|---|---|---|---|---|
| Tar | +24.54, +33.50, +35.04, +32.94, +37.09 | 3.83–4.53 | **5/5** | CE/LG = 1.91–4.69 倍，极显著 |
| Char | −32.55, −32.28, −32.60, −33.58, −32.82 | 5.70–5.75 | **5/5** | LG/CE = 2.3–2.7 倍，极显著 |
| Syngas | +5.18, +2.85, +2.84, +2.12, +3.28 | 1.33–1.54 | **5/5** | CE 略高，显著 |
| Water | +2.83, −4.07, −5.28, −1.48, −7.55 | 2.10–2.37 | **4/5** | **方向随档位翻转**，80/100 档不超噪 |

**Water 必须写成「随掺比交叉」**：20/100 时 CE 比 LG 高 2.83，40/100 起反转为 CE 低 4.07–7.55。写成"CE 水产率更低"是错的（第一档反例）。

**气体（mL/g(daf)）**

| 组分 | CE 五档 | LG 五档 | 差值 | 超噪 | 结论 |
|---|---|---|---|---|---|
| H2 | 26.6, 47.8, 55.6, 65.8, 57.9 | 0.67, 0.72, 0.78, 0.81, 0.79 | +25.93 … +64.99 | **5/5** | CE/LG = **39.7–81.2 倍** |
| C2H6 | 13.8, 8.6, 4.4, 3.4, 3.2 | 0.08, 0.06, 0.09, 0.07, 0.05 | +13.72 … +3.15 | **5/5** | CE/LG = **48.6–172.5 倍** |
| CH4 | 3.2, 1.9, 1.3, 1.3, 0.7 | 27.67, 33.25, 33.86, 30.26, 29.87 | −24.47 … −29.17 | **5/5** | LG 高一个量级 |
| CO2 | 18.7, 9.8, 5.9, 3.2, 2.0 | 24.35, 37.91, 39.26, 41.23, 43.56 | −5.65 … −41.56 | **5/5** | LG 高，且 LG 侧随掺比↑ 而 CE 侧随掺比↓ |
| CO | 13.7, 10.6, 8.1, 6.5, 5.3 | 15.23, 15.76, 17.305, 19.075, 20.935 | −1.53 … −15.64 | **5/5** | LG 略高 |

**Q3 的机制答案（可直接用，但要自己补文献）**：
- **CE 路线 = 深度脱氢/裂解**：H2 与 C2H6 极高、CO2 极低 → 寡糖骨架富含 C–O–C 与端基，热解走开环 + 脱氢，C2 物种保留在气相。
- **LG 路线 = 缩聚成炭 + 脱甲基**：Char 高 2.3–2.7 倍、CH4 高一个量级（CE/LG = 0.0–0.1）、CO2 高（CE/LG = 0.0–0.8）、H2 几乎为零 → 木质素芳环缩合直接留固相，甲氧基断裂产 CH4，羧基/酯基产 CO2，缺可供脱氢的脂肪氢。
- **这正是本题最漂亮的一条反直觉发现**：同为"生物质模型化合物"，同一掺比下产物分布**完全反向**（CE 产气产油、LG 产炭），说明脱硫灰的催化选择性**取决于底物官能团**，不能用单一"促进热解"概括。

---

## 8 交给下一棒（建模架构手）的交接清单

### 8.1 必须带进 `code/model_skeleton.py` 的 `MS.PARAMS`

- **题给块**：C01–C23（§6.1）。每个键后面写 `# Lxx` 行号注释，便于 G1 回查。
- **自设块**：T1–T12（§6.2）。**每个键名后缀 `_ASSUMED`**，值旁写 `# 自设`。这样 `verify_numbers.py` 与人工审计都能一眼分开两类。
- **派生块**：D01–D06（§6.3）。由代码现算，不写死。

### 8.2 三条建模硬约束（写错要返修）

1. **Annex I 的四产物闭合**：`Tar+Water+Char+Syngas = 100` 对 25 列全成立（实测）。四个独立回归会破坏约束 → 用 3 维 + 归一化，或 CLR/ILR 变换。这一条不写进方法章，审稿人一眼看出没用数据。
2. **两附件比例网格不同**：Annex I `{0,10,20,30,40,50,60,80,100}`，Annex II `{0,20,40,50,80,100}`。跨附件只对齐 `{20,40,50,80,100}`。逐档对齐会凭空造出 5 个不存在的数据点。
3. **CE/LG 无 `0/100` 基线**：Annex I 与 Annex II 的 CE/LG 表都从 10/100（或 20/100）起。Q1 的"催化剂是否显著促进 CE/LG 热解"**没有零催化剂对照**，只能用最低掺比外推，或明确写"本文对 CE/LG 的催化效应只能给出掺比依赖的方向性结论，无法给出相对纯组分的绝对增量"。这一句不写，等于把无对照当有对照。

### 8.3 三条最容易被 G1 判 FAIL 的写法（逐条对照 problem.txt 自查）

| 危险写法 | 为什么 FAIL | 正确写法 |
|---|---|---|
| 「题给热解温度 800 K」 | L145–146 无数值 | 「题面声明所有实验在同一温度下进行（L145–146），本文取 T = 800 K（**自设**）」 |
| 「题给掺比从 0 到 100%」 | L74–75 是 8 档 10/100–100/100，`0/100` 只在附件 | 「题面 8 档掺比（L74–75）；附件另设 0/100 空白对照」 |
| 「题给附件缺失率 50.7%」 | 声明数据区缺失率为 0.00%，50.7% 是含空行标题的机械值 | 「声明数据区无缺失；结构性未设档位见 §3.3」 |

### 8.4 未解决项（留给后续棒，不在本棒范围）

| 项 | 为什么本棒不解决 | 建议归属 |
|---|---|---|
| 同型题的往期解法检索 | 属 G20 真题对标，由独立成员负责（`squads/main/18-真题对标手.md`） | 真题对标手 |
| 脱硫灰化学组成 | 题面与附件均未给，必须外部文献 | 数据溯源手（建 ledger，标 `fetched_at`） |
| 温度数值 | 题面未给，若外部文献能定位原实验条件则可替换自设值 | 数据溯源手 |
| CE 到底是寡糖还是纤维素 | 题面与附件冲突，需择一，属口径决策 | 口径审计手（s4，`out/05-caliber.md`） |

---

## 9 自检

| 检查项 | 结果 |
|---|---|
| 5 个子问各有一条原文句子作依据（`THINKING-CANVAS.md:23` 门 0） | ✅ Q1←L90–95、Q2←L96–99、Q3←L100–103、Q4←L104–106、Q5←L107–111 |
| 每个子问的交付物形态已五选一并给理由 | ✅ §2（数值/方案/数值/机制/预测；「排序」未用并说明原因） |
| 附件行数、列名、缺失率、量级已 pandas 现读 | ✅ §3，含可原样重跑的命令 |
| 三处易误读写成「读者会以为 X，实际是 Y」 | ✅ §4-M1/M2/M3，另附 M4/M5 |
| 题型判定 + 判据 | ✅ §5（B / B-α，四条命中 + 四类排除） |
| 每个常数有符号、值、单位、出处行号 | ✅ §6.1（C01–C23）；§6.2 自设 T1–T12；§6.3 派生 D01–D06 |
| 题面没有的数字全部标「自设」 | ✅ §6.2 全表标 `[自设]`，§8.3 列了三条最易犯的误标 |
| 未修改任何上游文件 | ✅ 仅新建 `out/00-problem.md` |
| 首行 `BYTES <n>` 与磁盘字节数一致 | ✅ 见首行 |

VERDICT: PASS
