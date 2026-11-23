# 论文模板（PAPER SKELETON）

按题型分族。每族给"章序列 + 每章必须回答的问题"。
直接复制到 `main.tex` 里改小节标题即可；`【…】` 是填空项。

三章是**必需**（实测：独立评价章 16/16、检验 14/16、题面分析 14/16）：

- `Problem Analysis`（题面分析）
- 检验：问内 `X.4` 或单列 `Sensitivity and Error Analysis`
- `Strengths and Weaknesses`（评价）

---

## 通用前置（五族相同）

```
摘要页   Summary Sheet（第 1 页，官方模板单页）
目录     Contents（第 2 页起）
I.   Introduction
     I.1  Background              现象 + 为什么现在重要（≤3 句）
     I.2  Restatement of Problems 逐条转述 Q1a…（不是抄题，是改写成本文变量）
     I.3  Our Work                本文给出什么（每问一句，句句有名词）
II.  Problem Analysis             题面里的机制、关键矛盾、简化理由
III. Assumptions and Justifications   每条：假设 / 理由 / 被谁用
IV.  Notations                    符号表三列
（C 组在此插入 Data Description 章）
V..  每问一章
N-3  Model Test / Sensitivity and Error Analysis
N-2  Strengths and Weaknesses
N-1  References
N    Appendix（源码、参数表、归档输出）
```

---

## A 族：图像 / 几何 / 工程测量

序列 A-α（一等奖 3/4 命中）：

```
V.   Question 1: 【本节标题用"做什么"，不用"第几问"】
     X.1 Image Pre-processing        灰度/去噪/裁剪；报像素数与阈值（可复现）
     X.2 【判别量】Modeling           像素判别、几何约束、标定关系
     X.3 Solution and Results         给出数 + 误差条
     X.4 Test Analysis                与独立测量/另一算法对比，报差值
     X.5 Short Summary                本问结论一句话
VI.  Question 2: ...
```

要点：
- `X.1` 必须写"输入图像多大、做了哪几步、每步参数是多少"。评委会拿这三项判断能否复现。
- `X.2` 里凡是"看起来像"的判断都要变成可算的判据（阈值、比例、亮度差）。
- `X.4` 的对比对象最好是**另一种方法**（不是自己换个参数再跑一遍）。

## B 族：物理 / 装置 / 优化

序列 B-α，**必须有机理论证 + 问内检验**（两篇缺检验的一等奖 `2205838`/`2307379` 都在此族，属反面样本）：

```
V.   Question 1: ...
     X.1 Mechanism and Assumptions   控制方程 / 受力 / 守恒，标明简化
     X.2 Mathematical Model          变量、约束、目标
     X.3 Solution                    解析或数值，给方法名与收敛判据
     X.4 Validation and Sensitivity  与解析解/实验/极限情形对比 + 参数敏感
```

要点：
- 缺"实验数据"时，用**极限情形自检**（把参数推到 0 或 ∞，结果应收敛到哪个已知解）。
- `X.4` 要给数字："参数 ±10% 时目标值变化 ≤【x%】"。

## C 族：数据 / 统计 / 政策情景

序列 C-α（**4/4 命中**，且数据章前置是 C 族与 A/B/D 的硬分界；数据章 3/4 篇真正单列）：

```
V.   Data Description and Preprocessing
     V.1 Sources and Acquisition     每个来源：机构、指标、期间、取数 URL、取数日期
     V.2 Cleaning                    缺失、异常、单位换算、口径变更，逐项给处理后的行数
     V.3 Rationality and Consistency 与其他来源交叉核对，报差异百分比
VI.  Question 1: ...
     X.1 Data Insight                先描述数据（趋势、分布）
     X.2 Modeling and Solution       模型 + 标定 + 结果
     X.3 Robustness and Conclusion   稳健性 + 本问结论
VII. Question 2: ...
VIII.Sensitivity Analysis and Error Analysis   单列（2/4 命中）
IX.  Conclusions and Policy Recommendations
     （逐问小结："For Problem one, …"；政策建议每条挂到一个数字）
X.   Strengths / Weaknesses / Future Work
```

要点：
- `V.3` 是 C 族的加分项：用**一个独立来源**核对（本项目用 WHO 与 World Bank 的期望寿命差 0.23%）。
- 政策建议不许空转：每条建议后跟"若不这么做，成本是【数】"。

## D 族：组合 / 整数 / 前沿

序列 D-α（一模型一章，经典 → 扩展 → 降规模）：

```
V.   Basic Model: 【经典模型名】
     X.1 Objective Function and Modeling Principles
     X.2 Constraints
     X.3 Solution
     X.4 Validation                与经典解/上界对比
VI.  Extended Model              加入现实约束（网络、安全、时序）
VII. Scale-Reduction Model       降维/分解/量子化，报"规模 N → n、误差 x%"
VIII.Comparison of Models        三模型在同一算例上的对比表（这是 D 族的核心论据）
IX.  Advantages and Limitations
```

要点：
- `VIII` 是 D 族的"创新点落地点"：必须有一张表把三个模型放在一起比（时间、解质量、内存）。
- 报"降规模"必须给代价："520 bit、9.1 s、与经典 MILP 差 <2.5%"。

## E 族：聚类 / 时序（n=1，只作推荐，不做频率外推）

E 组唯一一篇 `apmcm2213503` 的完整序列是：Introduction → Analysis of Question（2.1–2.4）→
General Assumptions and Notations（**合为一章**，与 A/B/C 不同）→ Model and Solution（4.1 Data Collection →
4.2 Problem Solving → 4.2.1–4.2.5 逐问）→ 时序模型章（5.1.1 model / 5.1.2 Stationarity Test /
5.1.3 White Noise Test / 5.1.4 Model Estimation and Test）→ 机理章 → Model Evaluation and Further Discussion。
**注意它正是反模式 P7-a 的出处**（letter 型小问脱离模型数字），照抄骨架时不要照抄这个缺陷。

```
V.   【时序模型章】
     X.1 Model Form                阶次、差分阶、季节项
     X.2 Stationarity Test         ADF/KPSS，给 p 值与结论
     X.3 White Noise Test          Ljung-Box，给 p 值
     X.4 Estimation and Validation 系数显著性 + 残差诊断 + 样本外一步预测误差
```

要点：四步各自一个子节，**每步给 p 值**。缺任何一步，检验章就等于没写。

---

## 摘要模板（按槽位填，四段固定）

```latex
\begin{abstract}
\textbf{Background and Task} 【现象一句话，带一个数】。This paper addresses
【N】 problems: 【任务1】；【任务2】；【任务3】。Three models are developed:
【模型1】, 【模型2】 and 【模型3】.

\textbf{Modeling Framework} 【Q1 用】, based on which 【Q2 用】, and extending
to 【Q3 用】. 【每个模型名后跟一个限定词：constrained / dynamic / stochastic 之类】.

\textbf{Results per Question} 【Q1：一个数 + 一个结论】; 【Q2：一个数 + 一个结论】;
【Q3：一个数 + 一个结论】.

\textbf{Validation and Limitation} 【验证手段1，带数】; 【验证手段2，带数】. The main
limitation is that 【具体局限，带数】.

\keywords{【与第 2 段模型名同序的关键词】}
\end{abstract}
```

自查：不同数字 ≤8 个；四段齐全且顺序正确；关键词顺序 = 模型出现顺序。

---

## 参考文献格式

```latex
\begin{thebibliography}{99}
\bibitem{ref1} 【作者】. 【题名】[J]. 【刊名】, 【年】, 【卷】(【期】): 【页码】.
\bibitem{ref2} 【作者】. 【书名】[M]. 【出版地】: 【出版社】，【年】.
\bibitem{ref3} 【机构】. 【报告名】[R]. 【年】.
\bibitem{ref4} 【机构】. 【数据集名】[DB/OL]. 【URL】, accessed 【YYYY-MM-DD】.
\end{thebibliography}
```

规则：条目 ≥12 条；≥70% 在正文以 `\cite` 引用；[M]/[J]/[R]/[DB/OL] 一个不漏；访问日期用 ISO。

---

## 页数预算（正文 30 页上限）

| 章 | 目标页 | 说明 |
|---|---|---|
| 摘要 | 1（不占正文） | 官方模板单页 |
| Introduction + Analysis | 2–3 | 别写超过 3 页，评委不看 |
| Assumptions + Notations | 2–3 | 符号表最多 1.5 页 |
| 每问一章 | 4–6 / 问 | 图 ≤3、表 ≤3，剩下的进附录 |
| 检验 | 2–3 | 至少 2 张图 |
| 评价 | 1 | 优缺点各 3 条 |
| References | 1 | 18 条约 1 页 |

超页时**唯一有效手段**：把归档表（完整参数表、全量结果表）搬进附录。
无效手段：压字号、缩行距、删论证（后者还会扣分）。

---

## 反模式速查（17 条，按组；编号对应 `APMCM-PITFALLS/04-award-patterns.json` 的 `antipatterns`）

| 编号 | 症状 | 判据 / 修法 |
|---|---|---|
| P1-a | 摘要纯方法清单（`apmcm2203180`） | 每段以结论数字收口，方法名只放第 2 段 |
| P1-b | 摘要纯数据堆砌（`apmcm2201058`，38 个数字 / density 11.48） | 数字必须配基准或极值，并说明为什么重要 |
| P1-c | 摘要结尾零信息（`apmcm2307379`） | 结尾段改成验证数字 + 具体局限 |
| P2-a | 没有验证、用自我肯定代替检验（`apmcm2205838`） | 检验计数 ≥1，给 ±幅度或实测误差百分比 |
| P2-b | 检验章缺失且缺点不指名（`apmcm2307379`） | 缺点必须指到变量/情景并给量级 |
| P3-a | 假设无 justifying（`apmcm2303763`） | 把"数据可信"改成可检验的清洗流程与误差界 |
| P3-b | 假设纯编号无理由（`apmcm2205838`） | 补量级论证 |
| P4-a | 缺点空转（`apmcm2205838`） | 写误差来源与量级，与正文数字对齐 |
| P4-b | 结论强于证据 / 排版崩坏（`apmcm24207218`） | 排版修正，陈述与数据一一对齐 |
| P4-c | 薄弱项只定性（`apmcm2213503`） | 给信息缺失对预测的影响百分比 |
| P5-a | 图号/章号/拼写崩坏（`apmcm24200636`） | 提交前跑交叉引用检查 |
| P5-b | 编号回退（`apmcm2201058`） | 统一编号体系，禁用手工编号 |
| P5-c | 标题拼写错误（`apmcm2203180`） | 拼写检查进提交清单 |
| P5-d | 标题/正文断词（`apmcm25302425`） | 断词检查；符号表空格统一 |
| P6-a | 符号表单位重复/断裂（`apmcm24200636`） | 三列：符号-含义-单位，单位只写一次 |
| P6-b | 假设用项目符号导致无法交叉引用（`apmcm25304268`） | 假设改编号并加 label |
| P7-a | letter 型小问脱离模型数字（`apmcm2213503`） | 公开信必须引用前问的定量结论（对照 `apmcm2303763` 的 Open Letter 章） |
