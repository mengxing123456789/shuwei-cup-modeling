# 一等奖论文模式：16 篇实测提取（结构模板 / 摘要槽位 / 决策树 / 创新点 / 图表范式 / 反模式）

> **语料**：`E:\数学建模\APMCM2025_C\refs\award_text\*.txt` 中 16 篇英文赛道一等奖论文（`official_standard.json` 记 `n_first_prize_verified=16, n_excluded=0`）。
> **排除**：同目录 6 篇 2024 中文 UNVERIFIED 论文（`2024A题02838`、`2024A题03112`、`2024B题00536`、`2024B题02462`、`2024C题00023`、`2024C题02422`），不在本文统计口径内。
> **计数口径（全篇统一）**：先滤掉目录行——`body = '\n'.join(l for l in text.split('\n') if l.count('.') < 8)`——再对正文正则计数；脚本 `E:\数学建模\APMCM-PITFALLS\_work\scan.py`，原始输出 `_work\scan_out.txt`、`_work\features.json`、`_work\eqfig.json`。文中所有 `n/16`、`n/4` 均由该脚本产出，可复跑。
> **证据纪律**：每条结论后标 `【队号｜文件名】`，所引英文片段均为 `.txt` 原文（PDF 提取可能带拼写错误/乱码，照抄不改）。
> 频次记号：`在组内 n/组内总数`；跨组时写 `n/16`。

---

## 0. 语料与题号分组

| 组 | 题号语义 | 队号（文件） |
|---|---|---|
| **A** 图像/几何/工程 | 视觉→几何量→工程结论 | `apmcm2208815`（2022年A题优秀论文.txt）、`apmcm2309364`（2023年A题优秀论文.txt）、`apmcm24200438`（2024年A题优秀论文.txt）、`apmcm25302425`（2025年A题优秀论文.txt） |
| **B** 物理/优化 | 连续场→代理→多目标 | `apmcm2205838`（2022年B题优秀论文.txt）、`apmcm2307379`（2023年B题优秀论文.txt）、`apmcm24200636`（2024年B题优秀论文.txt）、`apmcm25304268`（2025年B题优秀论文.txt） |
| **C** 数据/统计 | 外部数据→拟合/预测/因果→政策 | `apmcm2203180`（2022年C题优秀论文.txt）、`apmcm2303763`（2023年C题优秀论文.txt）、`apmcm24200658`（2024年C题优秀论文.txt）、`apmcm25301412`（2025年C题优秀论文.txt） |
| **D** 前沿/组合 | 机理+整数规划/量子/降规模 | `apmcm2201058`（2022年D题优秀论文.txt）、`apmcm24207218`（2024年D题优秀论文.txt）、`apmcm25310840`（2025年D题优秀论文.txt） |
| **E** 聚类/时序 | 权重+时序+聚类 | `apmcm2213503`（2022年E题优秀论文.txt） |

摘要量化基线（`official_standard.json` 的 `per_paper` 字段）：absW 区间 **228–578 词**（均值 ≈374）；`abstract_numbers = 0` 的 **7/16**（`2208815`、`2213503`、`2309364`、`2303763`、`24200438`、`24200658`，以及 `2203180` 仅 2 个数字）；数字最密的是 `2201058`（absNum=38，density=11.48）与 `25304268`（absNum=11，density=3.45）。

---

## 1. 章节骨架族（按题号分组，实测频次）

### 1.1 五构件是否真有独立章节（本节是第 1 题"必有 5 个构件"的分母来源）

构件判定正则（`_work/scan.py` 的 `core` 字典）：
`II_analysis`（题面分析/重述章）、`test_sec`（检验类章标题：Sensitivity|Robust|Model Test|Error Analysis|Stability|Rationality）、`eval_sec`（评价类章标题：Strength|Advantage|Merit|Pros|Limitation|Weakness|Shortcoming|Evaluation|Disadvantage）、`unit4`/`unit4_labeled`（`\d+\.\d+\.\d` 三级子块与其标签）、`data_in_q`（问内数据节）、`letter`（Open Letter/Recommendation Letter/non-technical article）。

| 队号 | 题号 | II_analysis | test_sec | eval_sec | unit4 | data_in_q | letter |
|---|---|---|---|---|---|---|---|
| 2208815 | A | 4 | 2 | 5 | 13 | 0 | 0 |
| 2309364 | A | 6 | 7 | 9 | 10 | 2 | 0 |
| 24200438 | A | **0** | 35 | 14 | 16 | 1 | 0 |
| 25302425 | A | 5 | 16 | 8 | 20 | 1 | 0 |
| 2205838 | B | **0** | **0** | 6 | 15 | 0 | 0 |
| 2307379 | B | 1 | **0** | 5 | 7 | 0 | 0 |
| 24200636 | B | 5 | 28 | 9 | 17 | 0 | 0 |
| 25304268 | B | 5 | 22 | 25 | 27 | 4 | 0 |
| 2203180 | C | **0** | 16 | 9 | 15 | 3 | 0 |
| 2303763 | C | 1 | 11 | 9 | 18 | 8 | **4** |
| 24200658 | C | 5 | 9 | 8 | 16 | 5 | 0 |
| 25301412 | C | **0** | 20 | 16 | 39 | 5 | 0 |
| 2201058 | D | 1 | 3 | 7 | 13 | 0 | **4** |
| 24207218 | D | 2 | 56 | 31 | **0** | 7 | 0 |
| 25310840 | D | 8 | 16 | 9 | 20 | 1 | 0 |
| 2213503 | E | 7 | 4 | 14 | 11 | 6 | 4 |

**实测（跨 16 篇）**：
- **有独立题面分析/重述章**：**11/16**（无的 5 篇：`24200438`、`2205838`、`2203180`、`25301412`、另 `2307379`=1 次仅为标题残留）。
- **有独立检验章或问内检验块**：**13/16**（完全无"检验"语义结构的 3 篇：`2205838`（test_sec=0）、`2307379`（test_sec=0）、`24207218` 之外的 `24200438` 例外在于其检验折回第 5 章——实测 `Sensitivity Validation` / `5.2 Robustness`）。
- **有独立评价章**：**16/16**（100%），但标题词分布极散：`Advantages/Disadvantages`、`Strengths and Weaknesses`、`Merit/Shortcoming`、`Pros and Cons`、`Evaluation`、`Model Limitations` 六种以上写法。
- **"假设 + 符号表"作为独立章的**：**12/16**（缺的 4 篇：`2208815`（`Assumption` 0 次）、`2201058`（0 次，章名 `2 Model hypothesis`）、`24200636`（0 次）、`24200658`（仅 1 次，并入问内）——前两篇把假设并入模型章，后两篇无独立假设节）。实测正文 `Assumption` 计数：`24207218`=13、`25302425`=13、`2203180`/`2303763`/`25301412`=6、`24200438`=5、`2309364`=4、`25304268`/`25310840`=3、`2213503`=2、`2205838`/`2307379`/`24200658`=1、`2208815`/`2201058`/`24200636`=0。
- **附录含代码清单（`Listing N:`）的**：**3/16**（`24200438` 18 条含 `import cv2`、`2205838` 6 条 MATLAB、`2309364` 2 条 MATLAB+LINGO）⇒ 一等奖**不**要求附代码，附录形态自由。
- **字母/罗马数字编章的**：**2/16**（`24207218` 全篇 Ⅰ–Ⅸ + A/B/C；`25302425` 用 I/II/III/IV/V/VII）。

### 1.2 A 组（图像/几何/工程，n=4）最常见序列

**序列 A-α：逐问四件套（问内闭环）—— 3/4 命中**（`2208815`、`2309364`、`24200438`；`25302425` 为同构变体）

```
1 Introduction
  1.1 Background
  1.2 Restatement / Problem requirements
  1.3 Our Work                       ← 3/4（2208815 无）
2 Problem Analysis                   ← 3/4（24200438 无）
3 Assumptions (and Justifications)   ← 3/4
4 Notations / Symbol Description
5..N  Model Establishment and Solution (每问一章)
   X.1 数据/图像预处理  或 Model Preparation
   X.2 模型建立
   X.3 求解与结果（图表为主）
   X.4 Test / Sensitivity 或 Analysis of the Result   ← 问内检验 3/4
N+1 Model Test（单列 Sensitivity + Robustness）  ← 2/4（24200438、25302425 有单列；2208815/2309364 折回问内）
N+2 Strengths and Weaknesses / Merit-Shortcoming-Improvement
N+3 References
N+4 Appendix（代码清单）
```

逐条证据：
- `2208815` 问内五件套原文（`_work/scan.py` grep `^\s*5\.\d\.\d`）：`5 . 1 . 1 Image pre-processing` → `5 . 1 . 2 Pixel discriminant modeling` → `5 . 1 . 3 Pixel discriminant model solution and results` → `5 . 1 . 4 Test analysis` → `5 . 1 . 5 Short summary`【apmcm2208815｜2022年A题优秀论文.txt】；`"Test analysis"` 在正文出现 **3 次**（每问一份）。
- `2309364` 问内：`5 . 1 . 1 Image Data Preprocessing` / `6 . 1 . 1 Principle Overview of YOLOv4 network` / `9 . 1 . 1 Principle Overview of VGG19 network`，结果节统一命名 `X.2 Results and `+结果类型（原文为 `Results and Histogram` / `Results and 2D Scatter Plot`）（`5 . 2 Results and Histogram of apple distribution`、`6 . 2 Results and 2D Scatter Plot of Geometric Coordinates`、`7 . 2 Results and Histogram of apple ripeness distribution`、`8 . 5 Results and mass distribution histogram`）【apmcm2309364｜2023年A题优秀论文.txt】。
- `24200438` 问内四段：`4 . 1 Question 1: Classify the Degradation Types of the Attached Image` → `4 . 1 . 1 Comprehensive Analysis` → `4 . 1 . 2 Grayscale-histogram-based Brightness Analysis Model` → `4 . 1 . 3 Jensen-Shannon-divergence-based RGB Histogram Model`；检验单列 `5 . 1 Sensitivity Validation` / `5 . 2 Robustness`【apmcm24200438｜2024年A题优秀论文.txt】。
- `25302425` 问内：`5 . 1 Analysis andsolving of Question One` → `5 . 1 . 1 Model Preparation` → `5 . 1 . 2 Prediction Model for Endpoint Coordinates Based on the DH Model` → `5 . 1 . 3 Motorsafety Validation Model` → `5 . 1 . 4 Analysis of the Result`【apmcm25302425｜2025年A题优秀论文.txt】。

**五构件在 A 组的实际写法差异**：
| 构件 | 组内写法（4 篇实测） |
|---|---|
| 假设 | 只有 `24200438` 用"逐条 justify"（章名 `Assumptions and Justifications`，`each of which is properly justified`）+ 命名式假设；`25302425` 用"命名假设+具体数字"（`Linkstructure Assumption: The left arm issimplified to 2 rigid links … upper arm length of 170 mm and forearm length of 168 mm`）；`2309364` 用 `3 . 1 Assumption 1`…`3 . 4 Assumption 4`（纯编号、无理由）；`2208815` 全文未出现假设章标题（`assum` 计数 2 次，藏在模型节）【apmcm24200438 / apmcm25302425 / apmcm2309364 / apmcm2208815】 |
| 符号表 | 3/4 单列（`4 Notations`）；`24200438` 的 `3 Notations` 极短，实际符号随问给 |
| 模型建立 | 统一"预处理 → 判据/网络 → 结果"三段；A 组 4/4 都在问内先写**数据/图像预处理**（`data_in_q`：`2309364`=2、`24200438`=1、`25302425`=1；`2208815` 写作 `5.1.1 Image pre-processing`） |
| 求解/结果 | **以图为主**：图编号去重数 `2309364`=34、`24200438`=27、`25302425`=14、`2208815`=4；`2309364` 表编号 **0**，`24200438` 表编号 **0**（`official_standard.json` tab=0）⇒ A 组"无表格、全图"是常态 2/4 |
| 检验 | 分裂为两派：**单列章**（`24200438` 的 5.1/5.2；`25302425` 的 `Motorsafety Validation Model`）vs **问内嵌**（`2208815` 每问 `Test analysis`；`2309364` 的 `6 . 1 . 3 Comparison of Model Recognition and Sensitivity Analysis`）|

### 1.3 B 组（物理/优化，n=4）最常见序列

**序列 B-α：机理章 + 问内五件套 —— 4/4 命中**

```
1 Introduction (1.1/1.2 问题重述)
2 Problem Analysis / Restatements and Analyses     ← 3/4（2205838 无）
3 Model Assumptions → 4 Symbol Description         ← 4/4（2307379 并入 3.1 术语符号）
5..N Model Establishment and Solution (每问一章)
   X.1 数据/边界预处理
   X.2 机理方程建立（NS/扩散/辐射传输/CFD）
   X.3 求解（仿真/优化器）
   X.4 结果与检验（Rationality Verification / inspection and analysis）
N+1 Evaluation (Advantages/Disadvantages 或 Pros and Cons)
N+2 Generalization / Future work
N+3 References → N+4 Appendix
```

证据：
- `24200636`：`6 . 1 Model establishment and solution of problem 1` → `6 . 1 . 1 Establishment of air circulation equation` → `6 . 1 . 2 The establishment of high-performance air-conditioning optimization model` → `6.1.3 The solution of the optimization model of high-performance air conditioning.` → `6 . 1 . 4 Seasonal simulation` → `6 . 1 . 5 Summary`；检验在问内：`6 . 2 . 4 inspection and analysis`；评价章 `7 evaluation and generalization of the model` → `7 . 1 . 1 Advantages of the model`【apmcm24200636｜2024年B题优秀论文.txt】。
- `25304268` 四件套：`5 . 1 . 1 Data Preprocessing` → `5 . 1 . 2 Establishment of the TMM Model` → `5 . 1 . 3 Model Solution and Result Analysis` → `5 . 1 . 4 Model Rationality Verification`【apmcm25304268｜2025年B题优秀论文.txt】。
- `2205838` 先机理后对象：`4 . 1 Physical basis of the model`（`4 . 1 . 1 Principle of Continuity` / `4 . 1 . 2 Daniel Bernoulli’s Equation` / `4 . 1 . 3 J. L. M. Poiseuille’s Equation`）→ `4 . 2 Air Resistance model and Force Analysis of the high-speed train` → `4 . 3 Optimization model of high-speed train head` → `4 . 4 Noise model of high-speed train` → `5. Evaluation of the models`（`5 . 1 Advantages of the model` / `5 . 2 Disadvantages of the model`）→ `VI. Optimization of the model` → `7. Future work`【apmcm2205838｜2022年B题优秀论文.txt】。
- `2307379`：无独立假设/符号章，符号与假设并入 `3 . 1 术语符号` / `3 . 2 Assumptions`，结果章内单列 `4 . 4 . 2.1 Innovative points` / `4 . 4 . 2.2 Results`，评价章叫 `5. Pros and Cons`【apmcm2307379｜2023年B题优秀论文.txt】。

**五构件在 B 组的实际写法差异**：
- 假设 **4/4 都走"物理量"**：B 组假设几乎全是物性/边界条件（`2205838` 是例外，见 §6 反模式 P4）；`25304268` 把假设写成**数据范围声明**（`• Wavelength Range: The spectral calculations cover the range from 0.3 𝜇m to 55.56 𝜇m`）。
- 符号表 4/4 有，但 `2205838` 的符号表只列 6 个量、`24200636` 的符号表跨页（`S Surface area of humidifier Square meters (square meters) Q Air volume Cubic meters per second (m³/s)`）⇒ B 组符号表常按"量-单位-含义"而 A/C 组按"符号-含义"。
- 模型建立 4/4 都是"先写控制方程再离散/仿真"，公式编号密度高：`24200636` eq=46、`25304268` eq=43 > A 组（`24200438` eq=**1**）。
- 结果以 **CFD 场图/云图**为主：`2307379` 图 24 个（`Figure 20 Locations of the five fans`、`Figure 24 The three-fans scheme`）；`24200636` 图 14 个（`Figure 13Sensitivity`、`Figure 14 Best Design`）。
- 检验 **2/4 完全没有**（`2205838`、`2307379` 的 `test_sec` = 0）⇒ B 组"物理仿真即验证"的默认心态，是组内最大风险点。

### 1.4 C 组（数据/统计，n=4）最常见序列

**序列 C-α：数据章前置 + 问内"数据→模型→结果"—— 4/4 命中**

```
1 Introduction (1.1 Background / 1.2 Question Restatement / 1.3 Our Approach)
2 Assumptions (and Justifications) → 3 Notations / Notations
4 Data Description / Data Preprocessing (4.1 Collection / 4.2 Cleaning 或 3.1 Sources/3.2 Framework/3.3 Rationality)   ← 3/4（2203180 并入第 5 章前段）
5..8 每问一章：Data analysis → Model → Results（问句作章标题 1/4：2303763）
N+1 Sensitivity Analysis and Error Analysis（单列）  ← 2/4（2203180、2303763）；另 2 篇问内 3.x Robustness
N+2 Conclusions（分问罗列）/ Policy Recommendations
N+3 Strengths / Weaknesses / Future
N+4 References → Appendix
```

证据：
- `2203180`：`5 . 1 Models and Solutions for Problem1`、`5 . 2 Models and Solutions for Problem2: Explore the causes of temperature changes`；单列 `6. Sensitivity Analysis`；`7. Model Evalustion and Further Discussion`（原文拼写）；`8. Conclusions` 下按 `8 . 1 For Problem one` 逐问小结（首句 `In part a of problem 1, in the judgment of global temperature rise in March 2022, the methods`【apmcm2203180｜2022年C题优秀论文.txt】。
- `2303763`：问内四段 `4 . 1 Data Description` → `4 . 1 . 1 Data Collection and Pre-processing` → `4 . 2 New Energy Electric Vehicle Development Model`（`4 . 2 . 1 Influencing Factors and Index Setting` / `4 . 2 . 2 Multiple Linear Regression Model` / `4 . 2 . 3 Results`）；单列 `10. Sensitivity Analysis and Error Analysis`；评价 `11 . 1 . 2 Shortcomings of the Model`【apmcm2303763｜2023年C题优秀论文.txt】。
- `24200658`：问内 `5 . 1 Data analysis` → `5 . 2 Analysis of the development factors`（`5 . 2 . 1 Data Collection` / `5 . 2 . 2 Analysis of controlling factors`）→ `5 . 3 Forecast`（`5 . 3 . 1 Time series forecasting` / `5 . 3 . 2 Random forest regression prediction` / `5 . 3 . 3 Hybrid predictive models`）【apmcm24200658｜2024年C题优秀论文.txt】。
- `25301412`：问内三段 `4 . 1 Data Insight and Status Analysis` → `4 . 2 Modeling and Solution: The Constrained Armington Framework`（`4 . 2 . 1 Core Assumptions` / `4 . 2 . 2 Parameter Calibration and Justification` / `4 . 2 . 3 Mathematical Formulation` / `4 . 2 . 4 Simulation Results and Analysis`）→ `4 . 3 Robustness Analysis and Conclusion`（`4 . 3 . 1 Sensitivity Analysis Design`）【apmcm25301412｜2025年C题优秀论文.txt】。

**五构件在 C 组的实际写法差异（组内最不统一的一组）**：
- 假设 **3/4 用"Assumptions and Justifications"**，但 justify 质量差最大：`2303763` 的 `Assumption 1 Assuming that the data obtained from the search has a certain degree of credibility and rationality.`（无任何量化）vs `25301412` 的 `Rational Behavior Assumption … Ceteris Paribus`（经济学通用式）。
- **数据节前置**是 C 组与 A/B/D 的硬分界：`data_in_q` 计数 `2303763`=8、`24200658`=5、`25301412`=5、`2203180`=3；A 组同期 1–2、B 组 0–4。
- 结果**以表+预测曲线为主**：表编号 `2203180`=9（组内最多），图 `24200658`=26（`Figure 25 China's revenue matrix`、`Figure 27 Dynamic game results`）。
- 检验 **2/4 单列、2/4 问内**（`24200658` 的 `test_inside`=0，全靠问内 `5.3.x` 直接给结果 ⇒ 组内最弱的一篇）。
- 结尾构件特殊：**政策建议式结论 2/4**（`25301412` 的 `9 . 2 Policy Recommendations`；`2203180` 的 `8. Conclusions` 逐问），**Open Letter 小问 1/4**（`2303763` 的 `9. An Open Letter:New Energy Electric Vehicles Moisten Your Life and Mine`）。

### 1.5 D 组（前沿/组合，n=3）最常见序列

**序列 D-α：一模型一章 —— 2/3 命中**（`2201058` 以问分章、`25310840` 以模型分章；`24207218` 为 Ⅰ–Ⅸ 罗马数字变体）

```
1 Problem Restatement / Background（1.3 Our Work）      3/3
2 Problem Analysis（2.1–2.4）                            2/3
3 Symbol Legend → 4 Basic Assumptions                   2/3（24207218 为 Ⅳ Symbol + Ⅲ Assumptions per-model）
5..N 一模型一章（经典模型 → 扩展模型 → 降规模模型）
   X.1 Objective Function / Modeling Principles
   X.2 约束或机理
   X.3 Solution
   X.4 Validation（对比/误差/量子位数）
N+1 Advantages and Limitations / Model Limitations     3/3
N+2 Appendix（含代码/参数表）
```

证据：
- `25310840`：`5 . 1 . 1 Objective Function Construction` / `5 . 1 . 2 Power Balance Constraint`）→ `Incorporating Network and Security Constraints` → `7 . 1 Solving Unit Combination Problems with Network and Security Constraints` → `8 . 1 Scale Reduction Model Based on Spatio-Temporal Decomposition` / `8 . 2 Steps for Solving the Scale Reduction Model`；评价 `9 . 2 Model Limitations`【apmcm25310840｜2025年D题优秀论文.txt】。
- `24207218`：`A. First Model Analysis` / `A. First Problem Model Establishment and Solution` → `a. Modeling Principles and Approach` → `b. Data Analysis and Processing`（字母子块，`unit4`=**0**）【apmcm24207218｜2024年D题优秀论文.txt】。
- `2201058`：`4 . 1 Phase change model`（`4 . 1 . 1 Governing equations` / `4 . 1 . 2 Initial and boundary conditions` / `4 . 1 . 3 Numerical procedure`）→ `4 . 2 Heat transfer process`（`4 . 2 . 1 Temperature distribution` / `4 . 2 . 2 Phase change time` / `4 . 2 . 3 Liquid fraction`）→ `4 . 3 Optimization of the interval angle`；第 6 章分形：`Murray’s law and branch generation` / `6 . 3 . 2 Optimization result` / `6 . 3 . 3 Heat transfer process`【apmcm2201058｜2022年D题优秀论文.txt】。

**五构件在 D 组的实际写法差异**：
- 假设 **3/3 都按"模型/物理"分组**：`2201058` 物理量型（`1) The physical properties of the PCM are homogenous, isotropic, and temperature independent … 3) Natural convection of liquid PCM conforms to the Boussinesq assumption`）；`24207218` 按模型 A/B/C 分块（`1.Data Correlation Assumptions … 2.AR Model Related Assumptions … 3.Prediction Model Assumptions`）；`25310840` 把假设绑到算法（`Assumption 1: Power system load data exhibits clusterability, enabling the division of 24- hour load curves into K typical time periods via the K-means algorithm`）。
- 模型建立 **公式密度最高**：eq 计数 `25310840`=56（全 16 篇最高）、`2201058`=31、`24207218`=0（该篇无编号公式，全靠表，表编号 8）。
- 结果**以表为主**：`25310840` 表编号 10、`24207218` 表 8、`2201058` 图 25（CFD 云图）。
- 检验 3/3 都有，但形态不同：`24207218` 是 `1. Sensitivity Analysis` + `2. Error Analysis` 双列（`test_sec`=56）；`25310840` 用 **结果对比**（原文 `with outputs deviating by less than 2.5% from classical MILP solutions`）；`2201058` 用**双模型互证**（拓扑优化 vs 分形优化）。

### 1.6 E 组（聚类/时序，n=1，不做频率外推）

`2213503` 的单篇序列（仅记录，不作为"最常见"）：
```
1 Introduction → 2 Analysis of Question（2.1–2.4）→ 3 General Assumptions and Notations
4 Model and Solution（4.1 Data Collection → 4.2 Problem Solving → 4.2.1…4.2.5 The Solution of Problem a…e）
5 时序模型章（5.1.1 模型 5.1.2 Stationarity Test 5.1.3 White Noise Test 5.1.4 Model Estimation and Test）
6 机理章（6.1 Measurement of Nuclear Weapon Energy / 6.2 Definition of Earth Destruction）
8 Model Evaluation and Further Discussion（8.1 Strengths / 8.2 Weaknesses / 8.3 Further Discussion）
References
```
原文：`5 . 1 . 2 Stationarity Test` / `5 . 1 . 3 White Noise Test` / `5 . 1 . 4 Model Estimation and Test`【apmcm2213503｜2022年E题优秀论文.txt】。**E 组独有的"时序四步检验"**（平稳性→白噪声→估计→验证）在 16 篇里只有这一篇写成独立子块，可视为 E 类题的推荐模板而非统计结论（n=1）。

---

## 2. 摘要模板（4 个 `\textbf{}` 段的句式槽位）

16 篇实测的共同骨架是 **背景段 → 逐问段 → 结果评估段 → Keywords**（16/16 都能对齐，逐问段起手词实测为 `In response to question one`（`2203180`）、`For problem 1`、`For Problem 1`、`Regarding question 4`、`Problem 1:`（`25302425`）等多种）。因此槽位模板按"4 个 `\textbf{}` 语义段"给：

### 槽位表

| # | `\textbf{}` 段名 | 句式槽位（抽象） | 必填要素 | 官方统计的对齐指标 |
|---|---|---|---|---|
| 1 | `\textbf{Background and Task}` | 「<<领域>> 在 <<时间/规模>> 上出现 <<矛盾现象>>。题目要求回答 <<Q1 动词短语>>、<<Q2 动词短语>>、…，本文据此建立 <<总数>> 个模型。」 | 现象+任务清单+模型总数 | absW 前 20%（228–578 词的 15–25% 区间） |
| 2 | `\textbf{Modeling Framework}` | 「针对 Q1 采用 <<模型名 A>>（<<为何选它的一句机理>>）；针对 Q2 在 A 的基础上引入 <<模型名 B>>，把 <<原表征>> 换成 <<新表征>>；…最终形成 <<框架名/缩写>>。」 | 每问一个具名模型 + 模型间的**依赖关系**（"based on / building on / extending"） | 关键词行须与之同名（见 §2.3） |
| 3 | `\textbf{Results per Question}` | 「Q1 得到 <<量>> = <<数字>> <<单位>>（<<置信区间/误差>>）；Q2 得到 <<阈值/极值>>；Q3 在 <<情景>> 下 <<数字>>，相较基准 <<%>>。」逐问一句，**每句至少一个数字** | 数字+单位+基准对比 | `abstract_numbers` 目标 ≥3；density ≥1.0 |
| 4 | `\textbf{Validation and Limitation}` | 「通过 <<敏感性变量>> ±<<幅度>> 时结果变化 <<%>>、与 <<对照模型>> 的偏差 <<%>>、<<样本外/实测>> 检验 R²=<<…>>，说明模型 <<成立范围>>；局限在于 <<具体条件>>，未来可 <<一句话>>。」 | 至少 2 种验证手段 + 1 条**具体**局限 | 对应正文 test_sec/eval_sec ≥1 |

### 2.1 三星级填充范例（数字最密的一等奖，`2201058`/`24207218`/`25310840` 形态）

```
\textbf{Background and Task} 结晶器保护渣的 <<膜厚/结晶温度>> 决定铸坯质量，工业现场只能观测
<<图像/温度场>>。题目要求 (i) 从图像反演 <<几何/物性>>、(ii) 预测 <<相变时间>>、(iii) 在
<<角度/结构>> 上做优化。本文建立 <<3>> 个模型，共用同一套 <<像素/焓-孔隙率>> 表征。

\textbf{Modeling Framework} 针对 Q1 以 <<像素判别 + Tamura 纹理>> 建立特征-物性方程；Q2 采用
<<焓-孔隙率 CFD>> 求 <<温度分布/液相分数>>；Q3 把 <<翅片形状>> 换成 <<Murray 定律生成的分形树>>，
并与 <<SIMP 变密度拓扑优化>> 并行对比。

\textbf{Results per Question} Q1 的像素判别误差 <<±X%>>；Q2 得到初始相变时间
<<47.6 / 39.2 / 31.4 / 25.2 / 20.7 / 17.2 min>>，最优 <<间隔角 24°>> 时最短 <<17.2 min>>、
最大液相分数 <<12.3%>>；Q3 拓扑优化较矩形/三角翅片提升 <<18.84%/28.17%>>，分形优化提升
<<14.01%/24.25%>>。

\textbf{Validation and Limitation} 以 <<双模型互证 + 网格无关性>> 验证，<<角度/网格>> 扰动
<<±10%>> 时目标量变化 <<<5%>>；局限是 <<未考虑接触热阻/三维效应>>。
```

### 2.2 二星级填充范例（预测型 C/D 题，`24207218`/`2203180` 形态）

```
\textbf{Background and Task} <<行业>> 在 <<年份>> 出现 <<需求缺口>>。题目要求预测
<<指标>>、判定 <<分类>>、并给出 <<推荐/政策>>。本文以 <<数据集名（规模 n=…）>> 为基础建立
<<4>> 个模型。

\textbf{Modeling Framework} Q1 用 <<AR(2)>> 捕捉短期自相关，Q2 在 <<两阶段 SVM>> 中加入
<<罚项>> 抑制类别不平衡，Q3 用 <<神经协同过滤 NCF>> 处理稀疏交互，Q4 把三者统一改写为
<<QUBO>> 以便量子求解。

\textbf{Results per Question} Q1 预测 <<10 月需求 10598.776>>，95% 置信区间
<<[10004.46, 11193.10]>>；Q2 分类准确率 <<93.80%>>，较基线提升 <<5%>>；Q3 的 MSE 下降
<<74.24%>>、RMSE 改善 <<49.25%>>；Q4 在 <<600 qubit>> 约束下取得可行解。

\textbf{Validation and Limitation} 用 <<留出样本外检验 + 混淆矩阵 + 参数敏感性>> 验证：全部 12 个
<<-1 类>> 样本正确，<<1 类>> 8 个仅 1 个误分；局限是 <<QUBO 受 600 qubit 限制、需谨慎离散化>>。
```

### 2.3 三星级填充范例（政策/优化型 C-D 题，`25301412`/`25310840` 形态）

```
\textbf{Background and Task} <<关税/机组>> 政策在 <<情景>> 下引发 <<成本上升/供能不足>>。
题目要求评估 <<Q1 现状>>、模拟 <<Q2 冲击>>、求解 <<Q3 最优税率/机组组合>>、并讨论
<<Q4 长期风险>>。本文提出 <<SMDEF 框架>> 统一 <<微观/宏观>> 两层。

\textbf{Modeling Framework} Q1 用 <<约束 Armington 模型>> 校准替代弹性；Q2 用
<<动态 Stackelberg 博弈>> 描述先动-后动；Q3 把税率作为上层变量、市场均衡作为下层约束构成
<<双层规划>>，并用 <<Laffer 曲线>> 求极值；Q4 用 <<QUBO 罚函数 + K-means 时段降规模>> 把规模压到
<<520 bit>>。

\textbf{Results per Question} Q1 得到出口 <<64.1%>> 萎缩、某国 <<245%>> 出口激增；Q2 的
<<关税临界点 11.1%>>；Q3 的 Laffer 最优点 <<≈30%>>，60% 已落入"过税区"；Q4 降维 <<48%>>、
<<9.1 s>> 求解、成本偏差 <<less than 2.5%>>（相对经典 MILP）。

\textbf{Validation and Limitation} 通过 <<弹性/成本参数敏感性 + 与经典 MILP 对账 + 稳健性情景>>
验证；局限是 <<量子位规模约束、部分参数依赖外部估算>>。
```

### 2.4 摘要槽位与"官方统计"的对齐检查表（可直接做自检脚本）

1. `\textbf{}` 段数 = 4（少于此则无法覆盖 §2 表四要素）——`official_standard.json` 无此项，需自测。
2. `absW` 落在 228–578（16 篇实测区间），超出上限说明背景段灌水。
3. `abstract_numbers ≥ 3`：7/16 的一等奖是 0 个数字，**不是** 允许项，而是"其他维度极强时的例外"；对标时应以 `2201058`(38)、`25304268`(11)、`25302425`(9) 为目标。
4. Keywords 与第 2 段模型名一一对应：16/16 成立，例如 `2201058` 的 `heat transfer fins, CFD, topology optimization, fractal geometry` 与其四问模型完全同序。

---

## 3. 解题思路模板（题面 → 模型的决策树）

### 3.1 A 类：图像/几何/工程

```
题面出现 "识别/计数/测量/增强/轨迹" 
├── 有标注数据？
│   ├── 有 → 先建"几何/物理判据"基线（Hough/颜色空间/阈值），再上深度网络做对照
│   │        【2309364：Lab a* + Hough 与 YOLOv4/VGG19 并列对比】
│   └── 无 → 走物理模型（JS 散度/Laplacian/FbRF），把"无参考质量代理"当检验
│            【24200438：SIFT 关键点数作无参考代理】
├── 输出量与图像量的量纲不一致？（2D 面积 → 3D 质量）
│   └── 必须补一个"图像→物理量"的映射假设，并给出修正项
│        【2309364：invented a brightness-estimation method ourselves】
└── 是否含机构/关节（机器人、机械臂）？
    └── 走运动学链：DH 参数 → 逆解 → 轨迹多项式 → 能耗目标 + 关节约束
        【25302425：DH + 五次多项式 + SQP】
```

判定实测依据：A 组 4/4 都在问内先做"预处理"再建模（§1.2）；4/4 的结果节以图交付、表编号为 0 的 2/4（`2309364`、`24200438`）。

### 3.2 B 类：物理/优化

```
题面出现 "场/流动/传热/辐射/结构优化"
├── 是否需要高保真场？
│   ├── 是 → 先定控制方程（NS / 对流扩散 / Fick / 辐射传输 TMM）
│   │        再定离散（CFD 网格 / 分层传输矩阵），网格无关性必须做
│   │        【2205838：Continuity + Bernoulli + Poiseuille；24200636：NS + 对流扩散 + Fick】
│   └── 否 → 用解析/半解析代理，但必须给出代理误差
├── 决策变量是"形状"还是"参数"？
│   ├── 形状 → 拓扑优化（SIMP/变密度）或分形生成（Murray）+ 两者对比
│   │         【2201058：topology optimization vs fractal】
│   └── 参数 → GA / 梯度下降 / BFGS，先粗后细
│            【2307379：GA + Markov 链收敛；24200636：梯度下降 + BFGS】
└── 多目标？
    └── 画 Pareto 前沿，说明权重/罚系数如何扫出前沿，并指出拐点
        【2022B：24 次 Pareto 提及；25304268：Figure 7 Pareto frontier】
```

**B 类硬约束（从组内缺口反推）**：B 组 `test_sec=0` 的 2/4（`2205838`、`2307379`）说明"仿真即验证"是常见做法，但同组 `24200636`（`test_sec`=28）与 `25304268`（22）证明一等奖也可以做到"问内检验 + 合理性验证"，应以后两者为骨架。

### 3.3 C 类：数据/统计

```
题面问 "预测/评估/因果/政策"
├── ① 数据可得性判定
│   ├── 官方数据源优先（统计局/世行/行业年鉴）；无官方 → 明确写"估算并给区间"
│   │        【25301412：4.2.2 Parameter Calibration and Justification】
│   └── 数据年份跨度 < 20 → 不做长周期 ARIMA，改 Holt-Winters/结构模型
│            【24200658：Holt-Winters + multiple regression】
├── ② 数据清洗与合理性（C 组必做：data_in_q 3–8 次/篇）
│   └── 加一节 "Data Collection and Pre-processing"，交代缺失值/异常值/口径
│        【2303763：4 . 1 . 1 Data Collection and Pre-processing】
├── ③ 时序检查（四步）
│   └── 平稳性检验 → 白噪声检验 → 定阶估计 → 残差检验
│        【2213503：5.1.2 Stationarity Test / 5.1.3 White Noise Test / 5.1.4 Model Estimation and Test】
├── ④ 结构断点/情景
│   └── 若政策有明确生效年（关税、补贴），先做 DID/断点再谈预测
│        【2303763：DID；25301412：2025 Shock 情景】
├── ⑤ 模型选型顺序（由简到繁，且必须证明"复杂的更好"）
│   └── 基准（多元回归）→ ARIMA/时序 → 树模型（RF）→ 混合（GA-BP）→ 结构模型（博弈/CGE）
│        【2203180：t-test + multiple regression + ARIMA + Random Forest + GA-BP 并列】
└── ⑥ 必须留出样本外检验 + 误差分析
    └── 拆出台阶：Sensitivity Analysis / Error Analysis 单列一章
        【2303763：10. Sensitivity Analysis and Error Analysis；2203180：6. Sensitivity Analysis】
```

### 3.4 D 类：前沿/组合

```
题面出现 "大规模/组合优化/量子/多设备协同"
├── ① 先把"经典可解版"做出来（否则后面全是空中楼阁）
│   └── MILP/MIP + 商用求解器，报求解时间与最优性 gap
│        【25310840：5.1 Solving the Classic Unit Combination Problem Using a Mixed-Integer Programming】
├── ② 加现实约束（网络/安全/N-1/热备）
│   └── 每加一层约束就报"成本上升多少、时间上升多少"
│        【25310840：6.1 Generator Scheduling Model Incorporating Network and Security】
├── ③ 前沿形式（QUBO/量子）只作为"再表达"，必须与经典解对账
│   └── 偏差 <X%、比特数、求解秒数三件套
│        【25310840：less than 2.5% from classical MILP solutions、520 bits、9.1 seconds；24207218：三模型统一改写 QUBO】
├── ④ 规模降不下来时做"降规模"，但要写清"降规模定理/假设"
│   └── 聚类聚合/分布因子筛选，并给出 loss 上界
│        【25310840：Assumption 1 … clusterability … K-means；dimensionality reduction of 48%】
└── ⑤ 机理与优化的分工：机理模型负责"可行域"，优化负责"最优解"，须分别验证
    【2201058：CFD 求场 + 拓扑/分形求形状】
```

### 3.5 E 类：聚类/时序（n=1，模板取自 `2213503`，不作频率断言）

```
题面问 "评估/排序/预测/分组"
├── ① 多指标赋权 → CRITIC（客观权重）或 AHP；给出权重条形图
│        【2213503：F5 CRITIC score bar chart】
├── ② 时序：ADF 平稳性 → 白噪声 → ARIMA 定阶 → 残差 + 置信区间
├── ③ 分组：DBSCAN（无需预设簇数），报 eps/minPts 敏感性
│        【2213503：F15 DBSCAN clustering algorithm flowchart】
└── ④ 若某小问要求"非技术文章/公开信"，单独成章并保留结论引用
    【2213503：submitted a non-technical article to the United Nations；
      2303763：9. An Open Letter:...】
```

---

## 4. 创新点清单（真新意 vs 仅组合）

判定口径：文中出现"自创/改写/新框架/新因子/新映射"的**机制性**陈述才算真新意；只把现成方法并列使用（各问各一个模型）判为"组合"。全部引文可在对应 `.txt` grep。

### 4.1 真新意（7 篇，按类型分四类）

| 类型 | 队号 | 问题 | 一句话概括 | 原文证据 |
|---|---|---|---|---|
| **换表征** | `apmcm2309364` | 2023A Q4（质量估计） | 用**图像亮度**反推物距，替代"只按 2D 面积算质量"的失真空假设 | `we invented a brightness-estimation method ourselves to make the calculated apple quality more consistent with the actual situation`【2023年A题优秀论文.txt】 |
| 换表征 | `apmcm2309364` | 2023A Q1（重叠圆） | 以重叠比 γ 与阈值 λ 替代"逐个圆独立判定"，解决重叠圆重复计数 | `Flowchart of the Optimization Model for Eliminating Duplicate Circles`（F6 标题，正文用 γ/λ 判据） |
| 换表征 | `apmcm24200438` | 2024A Q1（数据预处理） | 以"上四分位/中位/下四分位"分组做噪声对抗预处理 NAP，替代简单去噪 | `we preprocessed the attachment 1 dataset with an innovate statistical method Noise Adversarial Preprocessing (NAP)` |
| 换表征 | `apmcm24207218` | 2024D Q1–Q3→Q4 | 把 AR(2)、两阶段 SVM、NCF 三个经典模型**统一改写为 QUBO 二次型** | `Quadratic Unconstrained Binary Optimization`（关键词行）+ Ⅴ章逐模型 `a. AR Model Construction` |
| **换约束表达** | `apmcm2307379` | 2023B Q4（风机优化） | 引入 `length magnification` 因子把"风机方向+风量"折进单一放大系数，改造 GA 的作用方向 | `(1) Length magnification. Considering the direction and magnitude of the fans, we devise a factor, length magnification, to strength its power in the specific direction of the fans' head`【2023年B题优秀论文.txt】 |
| 换约束表达 | `apmcm25310840` | 2025D Q4（降规模） | 以"K-means 时段聚类 + 机组聚合 + 分布因子筛选"把 UC 压到 520 bit，并把假设写成可检验命题 | `The method achieves a maximum dimensionality reduction of 48%, yielding a compact model of only 520 bits, solved in 9.1 seconds`；`Assumption 1: Power system load data exhibits clusterability, enabling the division of 24- hour load curves into K typical time periods via the K-means algorithm` |
| **换规模** | `apmcm25310840` | 2025D Q1–Q4 | 同一问题四层规模（经典 MILP → 网络安全 MILP → QUBO → 降规模），形成"规模阶梯"叙事 | `8.1 Scale Reduction Model Based on Spatio-Temporal Decomposition`；`less than 2.5% from classical MILP solutions`（摘要） |
| **跨学科映射** | `apmcm2201058` | 2022D Q3（翅片形状） | 把生理学的 **Murray 定律** 搬到翅片分形树生成，与 SIMP 拓扑优化并列对比 | `For fractal optimization, optimal parent-children fractal trees are generated by Murray's law and growth ratio` |
| 跨学科映射 | `apmcm25301412` | 2025C Q3–Q4 | 以财政学 **Laffer 曲线** 给"对等关税"找最优点，并用 Stackelberg 双层结构表述 | `Our Crisis-Aware Forecasting confirms a Laffer Curve effect, pinpointing the Optimal Tariff Rate at ≈30%`；`Tariff Tipping Point of 11.1%` |
| 跨学科映射（框架级） | `apmcm25301412` | 2025C 全篇 | 自造 **SMDEF** 总框架统合微观/宏观层，把 Q1–Q5 的结果挂到同一因果链上 | `Our SMDEF framework (integrating cross-layer quantitative models) confirms the "Reciprocal Tariff" strategy's structural flaws` |

### 4.2 只有"组合"、无机制主张的（8 篇，可作"稳妥但上限有限"的对照）

| 队号 | 问题 | 实际构成 | 判定理由 |
|---|---|---|---|
| `apmcm2205838` | 2022B | k-ε CFD + RWIND 风洞 + Pareto + MOPSO | 四件全是商用/成熟工具；正文无"inovative"语义（`innov`=0），创新章缺失，只有 `5.1/5.2` 优缺点 |
| `apmcm2203180` | 2022C | t 检验 + 多元回归 + ARIMA + 随机森林 + GA-BP | 摘要把五个模型并列成清单（`based on various methods such as pivot analysis, correlation analysis, t-test…`），无"为何叠加"的机制论证 |
| `apmcm2303763` | 2023C | 多元回归 + ARIMA + Lotka-Volterra + DID | `innov`=0；Lotka-Volterra 只作隐喻式类比 |
| `apmcm24200658` | 2024C | 时序 + 面板/VAR + Holt-Winters + 静态/动态博弈 | `innov`=0；各问一模型，博弈部分与预测部分未互证 |
| `apmcm25304268` | 2025B | TMM + GRA + DE + MG-EMT + LCA | 关键词行即方法清单 `PDMS TMM GRA DE MG-EMT LCA`；无自创因子（对比 2023B 的 `length magnification`） |
| `apmcm2213503` | 2022E | CRITIC + ADF + ARIMA + DBSCAN | `innov`=0；标准"权重—时序—聚类"三件套 |
| `apmcm2208815` | 2022A | 像素判别 + Tamura 纹理 + 多项式回归 | `innov`=0；纯管线拼接，图像处理的"保护渣"机理未转化为新判据 |
| `apmcm24200636` | 2024B | NS/对流扩散/Fick + 梯度下降 + BFGS + Pareto | `innov`=0；公式极多（eq=46）但优化器全为通用算法 |

> 交叉核对：全 16 篇中 `Laffer` 仅 `25301412` 命中 8 次，`Open Letter` 仅 `2303763` 命中 2 次，`Listing N:` 代码清单仅 `24200438`(18) / `2205838`(6) / `2309364`(2) 三篇命中——本表的"唯一性"判定均可用这两条 grep 复核。

### 4.3 一处"看起来是创新、实测是单标量"的警示案例

`apmcm25302425` 正文表：`Problem 1          4.00 J   2.67 J   33.3%    1.50   [1.000, 1.000]`、`Problem 2 14.00 J 9.33 J 33.3% 1.50 [1.000, 1.000]`、`Problem 3 86.80 J 57.86 J 33.3% 1.50 [0.500, 1.500]`【apmcm25302425｜2025年A题优秀论文.txt】。三问降幅完全一致 + 时标因子恒为 1.500 ⇒ 所谓"多关节协同优化"在数值上等价于"整体把速度降 1/1.5"（因能耗≈功率×时间而线性缩放）。这是**数据自证**的弱创新，登记在案以便我们自研时避免复刻。

---

## 5. 可复用图表范式（6 种）与误用

频次来自 `_work/scan.py` 的图类关键词统计（同一篇只计有无）与图标题 grep。

| # | 范式 | 适用条件 | 误用 | 出处（队号+图题） |
|---|---|---|---|---|
| 1 | **情景对比分组柱** | 同一指标在 2–4 个情景（政策/方案/季节）下并排；需有共同基准线 | 组数 >5 时改用分面；无基准时读者无法判断"好坏" | `apmcm25302425`：`Figure 12 … subplot (a)shows original plan 14.00 J, optimized plan 9.33 J`（原方案 vs 优化方案 并排）；亦见 `2205838`（FigAxes 21）、`25310840`（6） |
| 2 | **敏感性龙卷风/秩漂移** | 参数 ≥4 个、需排序影响力；龙卷风给 ±幅度，秩漂移给排序变化 | 只画"折线扫参"而不标注可行区间（把发散段也画进同一轴）| `apmcm25304268`：`Figure 12 Sensitivity analysis of GRA score versus PDMS thickness`；`apmcm24200438`：`Figure 26 Sensitivity Validation of Problem 2`（正文 `each sensitivity of parameter is below 5%`）|
| 3 | **Laffer/前沿曲线（含 Pareto 前沿）** | 存在单一控制变量与"先升后降"的最优，或两目标权衡 | 把前沿画成"光滑曲线"却只跑了 3 个离散点（伪连续）；不标拐点/最优值坐标 | `apmcm25301412`：`Laffer Curve Optimization`（关键词）+ `Optimal Tariff Rate at ≈30%`；`apmcm25304268`：`Figure 7 Pareto frontier showing the trade-off between performance score and total cost` |
| 4 | **雷达图** | 3–6 个维度、≤4 个对象、量纲已归一（如 0–10 分）| 维度 >8 或对象 >5 ⇒ 逐轴不可读；在雷达图上比"面积"当总分（不同轴的量纲不可加）| `apmcm25301412`：`Figure 7.7 Radar Chart: Tariff Policy "Impossible Trinity"`，并直接以面积判优劣 `Pragmatic: Largest total area—Pareto optimal`（此为典型"面积即总分"误用）|
| 5 | **热力图（相关矩阵/二维参数图）** | 展示矩阵型关系（特征×特征、波长×厚度、时段×机组）| 颜色映射用彩虹色且不给色标单位；样本量少时把 0.1 的差异画成强色块 | `apmcm24200658`：`Figure 20 Heat map of the correlation between features and target variables`；`apmcm25304268`：`Figure 2 Two-dimensional colormap of emissivity as a function of wavelength and PDMS`；`apmcm25301412`：`Heatmap of Argentina's Export Growth Rate`（Figure 4.4）|
| 6 | **流程图（技术路线/算法流程）** | 交代"多问如何串联"或"算法内部步骤"；放第 1–2 页作 roadmap，或每个算法前一张 | 只画箭头不写判据（菱形无出口条件）；流程图与正文步骤不一致（改代码未改图）| `apmcm2208815`：`Figure1 Model building flow chart`（且图**未编号表格体系**，全文只 4 张图）；`apmcm2213503`：`F1 ARIMA model building flowchart` / `F15 DBSCAN clustering algorithm flowchart`；`apmcm2309364`：`F5 Flowchart of the Apple Recognition Algorithm`；`apmcm25310840`：`Figure 1 Technical Roadmap`；`apmcm24200636`：`Figure 1Our Wrok`（**拼写错误+图 1 与 "5 Our Work" 节错位**，误用范例）|

**组内分布补证**：流程图 6/16 篇命中（`2208815`、`2213503`、`2309364`、`2303763`、`24200636`，另 `24302425` 借用 roadmap）；热力图 5/16（`2203180`、`24200636`、`24200658`、`25302425`、`25301412`）；Pareto/前沿 4/16（`2205838`、`24200636`、`25304268`、`25301412`）；雷达与 Laffer **各 1/16**（均 `25301412`）⇒ 后两者属"高风险高辨识度"，用错即突出。

---

## 6. 反模式（评委明显示弱/扣分的写法，均带原文）

### P1 摘要纯方法清单 / 纯数据堆砌

- **纯方法清单**：`apmcm2203180`（2 数字摘要）—— `This paper combines the knowledge of relevant statistics, based on various methods such as pivot analysis, correlation analysis, t-test, multiple regression model, ARIMA time series model, random forest algorithm, GA-BP neural network algorithm and other software such as MATLAB, SPSS and EXCEL`【2022年C题优秀论文.txt】。后果：读者看完不知结论，正文 `8.1 For Problem one` 才补 `the phenomenon of global warming exists`。
- **纯数据堆砌**：`apmcm2201058`（absNum=38、density=11.48）—— `47.6min, 39.2min, 31.4min, 25.2min,\n20.7min, 17.2min`（原文为横向列举，六个数字并列，无基准无对照）【2022年D题优秀论文.txt】。后果：数字虽多，但摘要读不出"为什么这些数字重要"。
- **无数字的泛结尾**：`apmcm2307379` —— `In summary, our research not only established an effective model to simulate the environmental conditions in the glass greenhouse, but also optimized the fan design through a genetic algorithm`【2023年B题优秀论文.txt】（`abstract_numbers=4` 但全在问内，结尾段零信息）。

### P2 没有验证 / 检验章缺失

- `apmcm2205838`：全篇 `Sensitivity`/`Robust`/`test` 语义 **0 次**（`test_sec=0`），只有 `5.1 Advantages of the model` 的自我肯定 `The consideration of the model is very comprehensive, the simulation results are reasonable and the results are accurate`【2022年B题优秀论文.txt】——"结果准确"没有任何量化依据。
- `apmcm2307379`：`test_sec=0`，评价章 `5 . 2 Cons` / `Despite achievements, some deficiency should not be ignored.`【2023年B题优秀论文.txt】——承认有缺陷却不指名，等于没检验。
- `apmcm24200658`：`test_inside=0`，Q3 直接给预测结果（`5.3.1 Time series forecasting` / `5.3.2 Random forest regression prediction` / `5.3.3 Hybrid predictive models`），未留样本外检验块【2024年C题优秀论文.txt】。

### P3 假设没有 justify（或 justify 不可检验）

- `apmcm2303763`：`Assumption 1 Assuming that the data obtained from the search has a certain degree of credibility and rationality.`【2023年C题优秀论文.txt】——把"数据可信"当假设，等于免检所有数据。
- `apmcm2205838`：`1. The material is the same for different high-speed railroads. 2. High-speed rail is straight. 3. The wind speed is the same. 4. Body length is the same.`【2022年B题优秀论文.txt】——四条并列、无来源无范围。
- 反向正面样本（对标用）：`apmcm24200438` 的 `each of which is properly justified` 与 `apmcm25310840` 的 `Assumption 1: Power system load data exhibits clusterability, enabling the division of 24- hour load curves into K typical time periods via the K-means algorithm`（假设→算法→可检验对象三段闭合）。

### P4 结论/薄弱项空转，与正文脱节

- `apmcm2205838`：`5 . 2 Disadvantages of the model 1. There is a certain amount of error; 2. For the model can not do exactly the same; 3. There is still a lot of room for improvement.`【2022年B题优秀论文.txt】——三条缺点对任何论文都成立，零信息。
- `apmcm2213503`：`8.2 Weaknesses 1 As the degree of information disclosure has certain limitations on model building, the accuracy of prediction will be affected to some extent.`【2022年E题优秀论文.txt】——只有定性"到某种程度"，无数字。
- `apmcm24207218`：`Confusion Matrix:：` 与 `The confusion matrix analysis reveals the model's precise classification capabilities`（矩阵本体排版为 `12 0` / `[` 的错位残片）【2024年D题优秀论文.txt】——矩阵排版残缺（`[ ]` 空壳、数字错位），却下"precise"结论；旁边表却有 `Phase 2 (RBF) 20 19 1 95.00%` 与 `Average 93.80%`，结论强于证据。

### P5 排版/编号/图号自我崩坏（评委第一眼可见）

- `apmcm24200636`：`5 Our Work Figure 1Our Wrok The above figure shows the overall idea of solving the problem in the form of a flowchart`【2024年B题优秀论文.txt】——章号错（应 5.x）、`Wrok` 拼写错、图号与正文错位。
- `apmcm2201058`：目录中 `9. Strength and weakness` 之下又出现 `7.1 Strength` / `7.2 Weakness`（编号回退）【2022年D题优秀论文.txt】。
- `apmcm2203180`：`7. Model Evalustion and Further Discussion`（拼写）【2022年C题优秀论文.txt】。
- `apmcm25302425`：`5 . 1 Analysis andsolving of Question One`（缺空格）、`the left arm issimplified to 2 rigid links`（缺空格）【2025年A题优秀论文.txt】。

### P6 符号/单位离散化（B、D 组高频）

- `apmcm24200636`：符号表跨行断裂 `S Surface area of humidifier Square meters (square meters) Q Air volume Cubic meters per second (m³/s)`【2024年B题优秀论文.txt】——单位重复书写（"Square meters (square meters)"）。
- `apmcm25304268`：假设条用 `•` 项目符号而非编号，导致正文无法 `\ref`（`• Wavelength Range: The spectral calculations cover the range from 0.3 𝜇m to 55.56 𝜇m`）【2025年B题优秀论文.txt】。

### P7 小问类型被"文章化"后失去技术含量

- `apmcm2213503`（2022E Q4）：`we submitted a non-technical article to the United Nations, explained our team's views on nuclear weapons`【2022年E题优秀论文.txt】——该小问在正文只占 letter 章（`letter`=4，`concl`=3），没有把前问模型的数字引进来（对比 `apmcm2303763` 的 Open Letter 章至少引用了前面模型结论）。
- `apmcm2201058`（2022D Q4）：`7 Recommendation letter`（`letter`=4）替代了建模章，导致 D 组 `unit4` 仅 13。

---

## 7. 给自研 skill 的直接指令（从上面数据反推的硬规则）

1. **骨架生成器**：按题号先落地 §1.2–1.5 的对应序列；`II_analysis` 章必写（11/16 有，缺失时问内必须补"问句分析"子块）。
2. **假设校验器**：假设条目必须含"假设→量化/来源→被哪个求解步骤使用"三段；检测到 `a certain degree of`／`can not do exactly` 类措辞直接告警（对齐 §6 P3/P4）。
3. **摘要打分器**：四段式 + `abstract_numbers ≥3` + keywords 与第 2 段模型名同序；`absW` 控制在 230–580。
4. **检验完整性检查**：`test_sec + test_inside ≥ 1` 且检验必须报**至少一个数字**（对标 `24200438` 的 `each sensitivity of parameter is below 5%`）。
5. **图表选择器**：按 §5 表选型；雷达图限制 ≤6 轴且禁止"面积总分"；Pareto/前沿必须标拐点坐标；流程图菱形必须有出口判据。
6. **创新点声明器**：只允许四类（换表征/换约束表达/换规模/跨学科映射），且必须像 `25310840` 那样把创新写成"可检验命题 + 数字"，避免 `25302425` 的"单标量伪装成多目标优化"。

---

## 附：本文件所有引用的可 grep 索引

| 队号 | 文件 | 本文引用位置 |
|---|---|---|
| apmcm2208815 | 2022年A题优秀论文.txt | §1.2、§5 (Figure1 Model building flow chart)、§4.2 |
| apmcm2205838 | 2022年B题优秀论文.txt | §1.3、§4.2、§6 P2/P3/P4 |
| apmcm2203180 | 2022年C题优秀论文.txt | §1.4、§3.3、§4.2、§6 P1/P5 |
| apmcm2201058 | 2022年D题优秀论文.txt | §1.5、§4.1、§5、§6 P1/P5/P7 |
| apmcm2213503 | 2022年E题优秀论文.txt | §1.6、§3.5、§5、§6 P4/P7 |
| apmcm2309364 | 2023年A题优秀论文.txt | §1.2、§3.1、§4.1、§5 |
| apmcm2307379 | 2023年B题优秀论文.txt | §1.3、§4.1、§6 P1/P2 |
| apmcm2303763 | 2023年C题优秀论文.txt | §1.4、§3.3、§4.2、§6 P3 |
| apmcm24200438 | 2024年A题优秀论文.txt | §1.2、§3.1、§4.1、§5、§6 P3 |
| apmcm24200636 | 2024年B题优秀论文.txt | §1.3、§4.2、§5、§6 P5/P6 |
| apmcm24200658 | 2024年C题优秀论文.txt | §1.4、§4.2、§5、§6 P2 |
| apmcm24207218 | 2024年D题优秀论文.txt | §1.5、§4.1、§6 P4 |
| apmcm25302425 | 2025年A题优秀论文.txt | §1.2、§4.3、§5、§6 P5 |
| apmcm25304268 | 2025年B题优秀论文.txt | §1.3、§4.2、§5、§6 P6 |
| apmcm25301412 | 2025年C题优秀论文.txt | §1.4、§3.3、§4.1、§5 |
| apmcm25310840 | 2025年D题优秀论文.txt | §1.5、§3.4、§4.1、§5、§6 P3 |