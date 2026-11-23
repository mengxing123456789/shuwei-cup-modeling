BYTES 71272

# 04 · 题目契合度审读 — PRACTICE_2023B

审读对象：`E:\数学建模\PRACTICE_2023B`（main.tex 4546 B / sha256 `2cc0e46029bb` / mtime 2026-11-19 16:49:15，末轮复测未变）
首轮测量：2026-11-19 17:11–17:14；二轮：17:28–17:31；末轮复测：17:44（本报告是快照，R-V11）

---

## 0 口径声明：基线文件缺失，本报告用现场测量替代

派单说明要求「先读 `review/00-metrics.md`，那是别人已经跑过的」，并把它定为口径的**唯一基线**。实测：

```
review/ 目录内容 = ['README.md']        00-metrics.md exists: False
```

`00-metrics.md` 从未生成（派单脚本没跑或没落盘）。因此本报告没有可对照的上游基线，下表所有数字都是我在 17:11–17:14 首轮、17:28–17:31 二轮、17:44 末轮三次现场跑出来的，**标注为「本报告实测」**；三轮一致者只报一个数，不一致者两列并列（本报告无此情况）。若后续补上 00-metrics.md，须以两列并列复核。

### 0.1 三条机器口径的原始输出（照抄，未改写）

① `E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\review_check.py E:\数学建模\PRACTICE_2023B`

```
paper: E:\数学建模\PRACTICE_2023B
pdf: None   pages: 0
[FAIL] X-pdf 找不到 PDF
        判据: 
        下一步: 把论文目录或 main.pdf 路径传进来
VERDICT: FAIL  (fail=1 unknown=0)
EXIT=1
```

（把参数换成 `…\main.tex` 结果相同，EXIT=1。）

② `E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py E:\数学建模\PRACTICE_2023B`

```
[FAIL] paper resolved   E:\数学建模\PRACTICE_2023B  <- 草稿（main.pdf 不存在或 < 150 KB）：基准带/引用/队号会假失败，请用 `gauntlet_check.py <论文目录>` 指明真稿
[FAIL] main.pdf exists  run gauntlet.build() or xelatex first
0/2 PASS
EXIT=1
```

③ `E:\Mini\envs\mathmodel\python.exe -m mmkit.figfont E:\数学建模\PRACTICE_2023B\main.pdf`

```
ModuleNotFoundError: No module named 'mmkit'
```

`mmkit` 不是已安装模块，实体在 `E:\数学建模\.agents\skills\mathmodeling\scripts\mmkit`。但**光加 `sys.path` 还不够**——`figfont.main()` 的签名是 `() -> int`（无位置参数），PDF 路径要从 `sys.argv[1]` 读。可复跑写法：

```python
import sys
sys.path.insert(0, r"E:\数学建模\.agents\skills\mathmodeling\scripts")
sys.argv = ["figfont", r"E:\数学建模\PRACTICE_2023B\main.pdf"]
from mmkit import figfont
figfont.main()
```

实测：

```
pymupdf.FileNotFoundError: no such file: 'E:\数学建模\PRACTICE_2023B\main.pdf'
  调用链: figfont.py:71 main -> :51 spans -> :37 _open -> :32 fitz.open
```

**判定：第③条是 BLOCKED-BY-ABSENCE（没有 PDF 可量），不是字号超标。** 三条命令两条直接 FAIL、一条无法执行，全部原因同一个：树里 0 个 PDF。另记一条**派单命令本身的可复算缺陷**：派单给的 `python -m mmkit.figfont <pdf>` 在本机跑不起来（模块未安装 + `main()` 不吃位置参数），照抄它会得到 `ModuleNotFoundError` 而不是字号结论——这类「命令写错但看起来像判据失败」最容易在评审报告里被当成字号问题。

```
any pdf in tree: []
```

### 0.2 被测件与数据层的代差（R-V11）

本报告实测（首轮 `17:11:18`，末轮 `17:28:42` 复测，两轮数值一致）：

| 文件 | 字节 | mtime | sha256 前 16 |
|---|---:|---|---|
| `data/Annex I- …xlsx` | 11335 | 2026-11-19 10:37:32 | `9cf303a3a30ee5fd` |
| `data/Annex II-…xlsx` | 11584 | 2026-11-19 10:37:32 | `ed71ce182be2767e` |
| `main.tex` | 4546 | 2026-11-19 16:49:15 | `2cc0e46029bbdec6` |
| `data/ledger.json` | 286874 | 2026-11-19 16:55:46 | `f1e7f39729a82a85` |
| `out/00-problem.md` | 40274 | 2026-11-19 17:00:52 | `90352bb665a1c859` |
| `out/15-benchmark.md` | 36720 | 2026-11-19 17:06:47 | `924982d45409c711` |
| `code/verify_numbers.py` | 2402 | 2026-11-19 16:49:15 | `e8dd7d6824bb8af7` |
| `code/model_skeleton.py` | **19720** | 2026-11-19 **17:39:50** | `2c210812a3072ec9` |
| `data/results_q1.json` | 15970 | 2026-11-19 17:30:46 | `853fb6bdd14fa182` |
| `data/results_q3.json` | 7505 | 2026-11-19 17:30:46 | `34a9bc403e54799e` |

**被测件落后 6 分 31 秒（对 ledger.json），落后 17 分 32 秒（对 out/15-benchmark.md）。** 也就是说：数据层和上游分析都比论文新，论文不是「写完了没更新」，而是**还没开始写**——见 §4。

**另一条更严重的时间线**：`code/model_skeleton.py` 在评审期间**三次**落盘（`17:22:45` 18213 B → `17:23:37` 18495 B → `17:39:50` 19720 B），**最后一次比 `main.tex`（16:49:15）晚 50 分 35 秒**；`data/results_q1..q5.json` 五个产物键于 `17:30:46` 同时落盘，比 `main.tex` 晚 41 分 31 秒。也就是说评审期间工作区仍在被上游脚本持续改写。**本报告引用的骨架行号以 17:39:50 版（sha256 `2c210812a3072ec9`，354 行）为准**：`τ_single` / `τ_diff` 的声明在第 `11-12` 行，符号表两行在第 `317-318` 行。该文件在评审中已漂移两次（`312-313` → `315-316` → `317-318`），若再次变动，这三处引用需重核。

---

## 1 先决问题：本题不是 APMCM 2023B（整条评审链的前提错位）

派单要求「从 `APMCM-PROBLEMS\PROBLEMS\` 取当年该题原题全文」。照做会拿到**另一道题**：

| 文件 | 赛事 | 标题 | 行数 | sha256 前 16 |
|---|---|---|---:|---|
| `problem\problem.txt` | 2023 **“ShuWei Cup”**（L2） | `Problem B：The catalytic reaction of cotton stalk pyrolysis`（L3） | 152 | `1a02b88cc8f58045` |
| `APMCM-PROBLEMS\PROBLEMS\2023_B.txt` | 2023 **APMCM**（L1） | `Microclimate Regulation in Glass Greenhouses`（L6） | 87 | `2efb901931a6b9b3` |

交叉验证：

- `2023_B.txt` 全文不含 `pyrolysis`；`problem.txt` 全文不含 `greenhouse`。
- 对整个 `E:\数学建模\APMCM-PROBLEMS\` 树（`*.txt,*.md,*.json`）检索 `pyrolysis` → **0 命中**。
- `_official_evidence.json` 的 `per_problem` 共 35 条，2023 年只有 `2023_A`（Fruit-Picking Robots）/ `2023_B`（Glass Greenhouses，sha256 `d64352e06f3ec5bc…`，chars 4606）/ `2023_C`（New Energy EVs）。**数维杯热解题不在这 35 份语料里。**
- `APMCM-PROBLEMS\2023.5\1701857067649008.zip`（13817849 B，16 项）是 2023 五月杯（量子计算/边缘设施），亦无关。

**结论：本论文的权威题面是 `problem\problem.txt`，不是 `APMCM-PROBLEMS\PROBLEMS\2023_B.txt`。** 下文所有行号均指 `problem\problem.txt`。

推论（必须写进报告，否则整条链会把错题当对题）：

1. `_official_criteria.json` 的 C1–C12 出自 **APMCM** 的 Essay format 规范（如 C4 引 `2018_APMCM_Essay_format_and_submission_specifications.txt:57`、C6 引 `2019_…:83`）。数维杯的格式规范不在该目录内。C 系列只能当**体裁惯例**用，不能当本赛的判分条款。
2. `_official_evidence.json` 的 8 个关注点频次（分母 35）描述的是 **APMCM 题库**，不是本题。用它做「本题漏了哪一类」的检查，必须先把模式跑在**本题**上——见 §3。
3. 顺带记录官方文件自身的一处不一致（不改判、只标注）：`_official_evidence.md:3` 写「共 **35 份**官方赛题本体」，同文件 `:6` 的小节标题写「分母 = **32 份**赛题本体」。JSON 侧无顶层 `n_total` 字段，但 `n_statements = 35`、`len(per_problem) = 35`、且 `aspects` 每条的 `n_total` 都是 35。**我按 35 使用**，32 视为该 md 的笔误。

---

## 2 逐句要求表（主表）

抄写规则：只收**要求句 / 约束句 / 交付句**，不解读。行号为 `problem.txt` 实际行号。兑现位置只查 `main.tex`（全文 106 行，69 个 `<<…>>` 占位符，`\b\d+\.\d+\b` 匹配数 = **0**，即全文没有任何小数）。

| # | 题面要求（原句 + 行号） | 论文兑现位置 | 兑现程度 |
|---|---|---|---|
| R1 | **L88–89** `Please complete the following questions through mathematical modeling:` | 结构上有槽位：`\section{Problem Analysis}` main.tex:43、`Assumptions` :45、`Notations` :50 | **没做**（三节正文全为 `<<…>>`） |
| R2 | **L90–92** `(1) For each pyrolysis combination in Annex I, analyze the yield of pyrolysis products (tar, water, coke residue, syngas) in relation to the mixing ratios …` | `\section{Question 1}` main.tex:54，四子节 :55/:57/:59/:61 | **没做**（4 处 `<<fill>>`；全文 `Tar/Water/Char/Syngas` 各 0 命中） |
| R3 | **L93–95** `…and explain whether desulfurization ash, as far as it is used as a catalyst, plays a significant role in facilitating the pyrolysis of cotton stalks, cellulose, and lignin?` | 同上 Q1 节；`significant` 全文 0 命中 | **没做**（「是否显著」是二值判定，无判据、无结论） |
| R4 | **L96–99** `(2) …the effect of the mixing ratio … on the yield of each group of pyrolysis gas is discussed and explained by making corresponding images.` | `\section{Question 2}` main.tex:63（:64/:66/:68/:70 四子节） | **没做**，且**无图槽位**：`\begin{figure}` = 0，`\includegraphics` = 0 |
| R5 | **L100–102** `(3) …is there a significant difference in the yields of the products generated from the pyrolysis of CE and LG, as well as the yields of the components of the pyrolysis gas?` | **无章节**。Q3 仅存在于摘要占位：main.tex:17 `<<Q3 model>>`、:20 `<<Q3 number + conclusion>>` | **没做**（无正文落点） |
| R6 | **L103** `Please provide reasons.` | 同 R5，无落点 | **没做** |
| R7 | **L104–106** `(4) How do we establish a catalytic reaction mechanism model of desulfurized ash for model compounds such as CE and LG and model the reaction kinetics for analysis?` | **无章节**；`kinetic` / `activation` 全文各 0 命中 | **没做**（连占位符都没有） |
| R8 | **L107–111** `(5) Please use mathematical models or AI learning methods to make predictions on the yields or quantities of the pyrolysis products under limited data conditions.` | **无章节**；`predict` / `extrapol` / `confidence` 全文各 0 命中 | **没做**（连占位符都没有） |
| R9 | **L16–19** `…employed the model compound method to establish pyrolysis combinations: desulfurization ash with cotton stalk and desulfurization ash with model compounds.` | 无；`desulfur` / `cotton` 各 0 命中 | **没做** |
| R10 | **L30–36**（句跨 30–36）`in selecting model compounds, it was necessary to consider their controllability and stability in reaction performance during the experiment, as well as their contribution to cotton stalk pyrolysis.` | `\section{Assumptions and Justifications}` main.tex:45 只有 **2** 个 `\item` 槽位（:47/:48） | **没做**（槽位数量本身不足以承载） |
| R11 | **L37–44**（句跨 37–44）`CE (Cellooligosaccharide) and LG (Lignin) are representative components of cellulose and lignin in the cotton stalk, which can represent the biomass characteristics of the cotton stalk itself.` | 无 | **没做**（且此句与附件脚注冲突，见 §5.3） |
| R12 | **L68–75**（句跨 68–75，配比枚举在 L74–75）`The desulfurization ash/biomass pyrolysis experiment was conducted with fixed-bed pyrolysis at mixing ratios of 10/100, 20/100, 30/100, 40/100, 50/100, 60/100, 80/100, and 100/100.` | 无；`mixing` 0 命中 | **没做**（且此 8 档与附件实际档位不符，见 §5.2） |
| R13 | **L76–77** `…under these experimental conditions, the relative error of parallel experiments is approximately 5%.` | 无 | **没做**（这是 R3/R5 唯一可用的判据来源） |
| R14 | **L78–80** `If the mixing ratios were chosen to be too small, such as 5/100 or 7/100, the relative error would have a significant impact…` | 无 | **没做**（题面自问自答式说明，论文若要「重述题面」必须转述） |
| R15 | **L145–146** `All experiments in this study were conducted at the same temperature.` | 无；`temperature` 0 命中 | **没做**（这条决定 Q4 能不能辨识 Ea，见 §5.1） |
| R16 | **L67** `The experimental results are shown in Appendix 1 and Appendix 2.` | 无；`Annex` 0 命中 | **没做**（正文未交代数据出处） |
| R17 | **L112–130** Annex I / Annex II 两个 xlsx 文件名 | 无 | **没做** |
| R18 | **L131–137** `Pyrolysis Combinations: Desulfurized Ash-Cotton Stalk; Desulfurized Ash-CE; Desulfurized Ash-LG.` | 无 | **没做** |
| R19 | **L138** `Pyrolysis Products: Tar, Water, Char, Syngas.` | 无 | **没做** |
| R20 | **L139–140** CS 气体 9 组分 `H2, CO, CO2, CH4, C2H6, C3H8, C3H6, C2H4, C4H10` | 无 | **没做** |
| R21 | **L141–144** CE / LG 气体各 5 组分 `H2, CO, CO2, CH4, C2H6` | 无 | **没做** |
| R22 | **L81–87** `If it is possible to use a mathematical model and AI learning to predict the pyrolysis product yield or production under conditions with limited data, it would not only greatly reduce the time required for experimental optimization but also provide accurate guidance on the trend of changes in the distribution of pyrolysis products.` | 无 | **没做**（这是 Q5 的动机句，摘要 L13 的 `<<one sentence with a number>>` 本该承接） |
| R23 | **L99 + L103**（两个交付动词）`…is discussed and explained by making corresponding images.` / `Please provide reasons.` | 表格：全文仅 `\begin{table}` 1 处（main.tex:51），且只有 **1 行**数据槽 `:53`；图：`\begin{figure}` 0 处 | **没做**（Q2 要成组图，Q1 需 12 格判定、Q3 需 32+25=57 格判定，1 行表装不下） |

**非要求句（明确排除，防止被当成约束写进假设）**：L1/L33/L85/L109/L148 是 PDF 分页符 `===== page N =====`；L2 赛事标识；L149–152 `Title Statement … strictly prohibited …` 版权声明；L12 `(Noun definitions can be found in the appendix)` 只是指向 L131–146 的名词表。

**主表汇总（本报告实测）**：23 条要求，**兑现 0 条，部分兑现 0 条，没做 23 条**。这不是「质量不足」，是「正文不存在」——见 §4 的槽位审计。

---

## 3 四类高频类别：官方口径 vs 本题实测

派单点名四类：给数据 19/35、政策建议 19/35、预测时序 13/35、要求具体数值 13/35。这些数来自 `_official_evidence.json` 的 `aspects`（分母 35，APMCM 题库）。**必须先把同一批正则跑在本题上**，否则会把「APMCM 常见」误当成「本题要求」。

复算命令见 §8.1。本题实测（本报告实测）：

| 关注点 | 官方规则 | 官方语料频次 | 跑在 `problem.txt` 上的命中 | 命中行 | 本题是否真有此要求 |
|---|---|---|---:|---|---|
| restatement 题面重述/任务拆解 | R-W01 | 12/35 = 34.3% | **0** | — | **有**，但模式匹配不到：题面用 `(1)…(5)` 编号，不是 `Question/Task/Problem 1` |
| data_attachment 给数据/需自取 | R-M14 | **19/35 = 54.3%** | **2** | L121、L130（只匹配到 `.xlsx` 文件名） | **有**，且是硬要求：两个附件是全篇唯一数据源 |
| predict 预测/时序 | R-T04 | **13/35 = 37.1%** | **2** | L82 `predict the pyrolysis product yield`、L87 `trend of changes` | **有**（Q5, L107–111），但**不是时序**：全文无时间轴、无 t 变量 |
| optimize 优化/决策 | R-M10 | 5/35 = 14.3% | **0** | — | **无**（L80/L86 的 `optimization` 是在解释为何不用 5/100，不是求解任务） |
| quantify 要求具体数值 | R-W05 | **13/35 = 37.1%** | **0** | — | **有，但模式漏检**：本题用 `analyze` / `significant` / `provide` 承载数值要求，没有一个 `calculate/how many` |
| letter 书信型 | R-W09 | 3/35 = 8.6% | **0** | — | **无** |
| policy 政策建议/决策输出 | R-W08 | **19/35 = 54.3%** | **0** | — | **无**（全文 `policy/recommend/suggestion/strategy` 各 0 次） |
| sensitivity 题面明示要做检验 | R-V07 | 8/35 = 22.9% | 1（假阳性） | L31 `controllability and stability in reaction` | **无**（L31 讲的是模型化合物的挑选理由，不是要求做灵敏度检验） |

### 3.1 本文漏了哪一类（直接回答派单问题）

1. **政策建议 19/35 —— 本题不存在，不构成漏项。** 本题 0 命中，`problem.txt` 全文没有 policy/advice 类小问。若论文硬塞一节「政策建议」，属自加要求。
2. **给数据 19/35 —— 漏了，而且是硬漏。** 附件是唯一数据源，但 `main.tex` 里 `Annex` 0 命中、`\begin{table}` 只有 Notations 一处 1 行、无任何数据表。数据层本身已经做好了（`data/ledger.json` 204 条逐格记录、sha256、`coverage_scan.annex.total_cells = 204`、`verdict: PASS`；评审后期又落盘 `data/results_q1..q5.json` 五份产物键，合计 67.9 KB），**但论文一个字都没引**。这是「有产物、无引用」的典型断裂——派单说的「找不到产物键的数字是缺陷本身」在这里是反向的：**产物键齐全，正文零引用**。
3. **预测 13/35 —— 漏了，且落点不存在。** Q5（L107–111）在 `main.tex` 里连占位符都没有（`predict` 0 命中）。注意：本题的预测**不是时序预测**，若论文画一条「时间—产率」曲线就是编数据（全文无时间变量）。
4. **要求具体数值 13/35 —— 漏了，且是本题最贵的一条。** 模式匹配 0 命中会误导人以为本题不要数字；实际上 `significant`（L94、L101）出现 2 次、`significant impact`（L79）1 次，共 3 处，每一处都是**必须落到数值上的二值判定**。本报告已把判据算好（§6.1），可直接用。

---

## 4 槽位审计：为什么「没做」是可预期的

`main.tex` 的骨架**在结构上装不下本题**。本报告实测：

| 项 | 实测值 | 本题需要 | 缺口 |
|---|---:|---|---|
| `\section{Question N}` 数 | **2**（main.tex:54 Q1、:63 Q2） | 5（L90/96/100/104/107） | **缺 Q3、Q4、Q5 三个正文节** |
| `\begin{figure}` / `\includegraphics` | **0 / 0** | Q2 明令 `by making corresponding images`（L99），且 Q1/Q3 也需图 | **无任何图槽位** |
| `\begin{table}` | **1**（Notations，main.tex:51） | 至少再加 Q1 判定表（12 格）、Q2 曲线表、Q3 判定表（产物 32 格 + 气体 25 格）、Q5 预测表 | **缺 4 张表** |
| 表内数据行槽 | **1 行**（main.tex:53 `$<<sym>>$ & <<meaning>> & <<unit>> \\`） | 符号至少 10 个（Tar/Water/Char/Syngas/H2/…/配比/σ） | 缺口 ≥ 9 行 |
| 假设条数 | **2**（main.tex:47–48） | 至少含：同一温度、5% 误差作 σ、CE/LG 命名裁决、四产物闭合、外推边界 | 缺口 ≥ 3 条 |
| 摘要里枚举的任务数 | **3**（main.tex:14 `<<task 1>>; <<task 2>>; <<task 3>>`） | **5** | **摘要模板硬编码少数了 2 个** |
| 摘要里枚举的模型数 | **3**（main.tex:16–17 仅 Q1/Q2/Q3） | 5 | 缺 Q4（动力学）、Q5（预测） |
| 摘要里枚举的结果数 | **3**（main.tex:19–20 仅 Q1/Q2/Q3） | 5 | 同上 |
| 附录代码 | `\lstinputlisting` 被注释（main.tex:104） | `code/` 下 **12 个 `*.py`**（`check_no_peek.py` 3083 / `fetch_annex.py` 30061 / `model_skeleton.py` 19720 / `solve.py` 23518 / `numlib.py` 3860 / `fix_bytes.py` 1665 / `gen_appendix.py` 1735 / `check_md.py` 2564 / `verify_numbers.py` 2402 + 6 个 `_probe_*.py` 探针；其中 6 个是探针，不是产物脚本） | 一个都没列 |

**关键判断：摘要模板把「3 个问题 / 3 个模型 / 3 个结果」写成了固定槽位，而题面有 5 个子问。** 这不是「内容没填」，是**骨架与题面不同构**。即使把 69 个 `<<…>>` 全填满，Q3/Q4/Q5 仍然没有交付位置，摘要仍然自报 3 问——这会构成一条可复算的错误（题面 `(1)…(5)` 五条 vs 论文自报 3 条）。

同时记录一条「工具链空转」的证据：`code/verify_numbers.py` 是空脚手架（0 claims、0 ranges），跑起来打印 `0 claims, 0 ranges (both empty = nothing is bound yet)` 后返回 PASS；`gauntlet_check.py` 的 R-V06 明确把 `claims==0` 判为未通过。也就是说：**当前没有任何数字被绑定到产物键上**，等正文写出来后，每个数字都得补 claim。

---

## 5 类① 描述性约束：不是祈使句，但写反了就是可复算的错误

题面有 6 条描述性陈述，不带 `please`/`should`，但都是硬事实。论文目前**没有断言**（正文为空），所以「暂无相反断言」；但下游一旦按常识补写，极可能踩这 6 条。我把数据判决先算好，写成「谁对」的形式。

### 5.1 L145–146 `All experiments … at the same temperature.` → Q4 的动力学参数不可辨识

描述性约束的含义：**单温度**数据。要辨识 Arrhenius 参数（A、Ea），至少需要 ≥3 个温度点的速率常数。本题只有 1 个温度且**温度数值未给**（`data/ledger.json` 的 `unverified[0]` 已记：`problem.txt:145-146 只说 All experiments ... at the same temperature，未给数值`）。

因此：
- 若论文 Q4 写出「拟合得到 Ea = xxx kJ/mol」，**与 L145–146 矛盾**，且无产物键可查 → 双重缺陷。
- 合法写法只有两种：① 把 Ea 当**假设值**并引文献（标 `[文献值]`），② 用单温度数据做**表观速率常数 k_app** 的辨识，明确声明「Ea 不可辨识」。
- 反向也成立：若论文写「在 800 K 下…」并当成实测，同样违反 L145–146（该数值是自设，不是题给）。

### 5.2 L68–75 八档配比 → 附件实际档位不是八档，气体更少

描述性约束 L68–75（句意完整跨 68–75，比例枚举在 L74–75）列出 8 档（10/100…100/100）。**附件实测档位与之不符**（本报告实测，`data/*.xlsx` 逐表读）：

| 表 | 实际档位数 | 档位 | 与题面 8 档的关系 |
|---|---:|---|---|
| Annex I Tab1 DFA/CS | 9 | `0/100` + 8 档 | 多一个 `0/100` 空白对照 |
| Annex I Tab2 DFA/CE | 8 | 8 档全 | 一致 |
| Annex I Tab3 DFA/LG | 8 | 8 档全 | 一致 |
| Annex II Tab1 DFA/CS | **6** | `0/100, 20, 40, 50, 80, 100` | **缺 10/100、30/100、60/100** |
| Annex II Tab2 DFA/CE | **5** | `20, 40, 50, 80, 100` | **缺 10/100、30/100、60/100** |
| Annex II Tab3 DFA/LG | **5** | `20, 40, 50, 80, 100` | **缺 10/100、30/100、60/100** |

**可复算的错误形态**：Q2（L96–99）要求「for each of the three pyrolysis combinations … the effect of the mixing ratio on the yield of each group of pyrolysis gas」。但 Annex II 里 **10/100、30/100、60/100 三档对任何组合都不存在**。若论文画了 8 个点的气体曲线，那 3 个点是插值或编造，属可复算错误。合法写法：气体只能在 `{20,40,50,80,100}`（CE/LG）与 `{0,20,40,50,80,100}`（CS）上作图，并在图注写明档位缺失。

同理，跨附件联合比较（Q1 产物 vs Q2 气体）只能在 **5 个公共档位** `{20/100, 40/100, 50/100, 80/100, 100/100}` 上做。

### 5.3 L37–44 `CE (Cellooligosaccharide)` vs 附件脚注 `CE: Cellulose` → 命名冲突必须裁决

`problem.txt:38` 写 `CE (Cellooligosaccharide)`；两个 xlsx 的脚注（Annex I `r29`、Annex II `r29`）都写 `CE: Cellulose`。**同一符号两个所指。** 论文必须择一并声明（建议：以题面 L38 为准，脚注视为附件笔误，在 Assumptions 里写一句）。若论文既写「纤维素」又在符号表写 `Cellooligosaccharide`，属自相矛盾。

### 5.4 L76–77 `relative error … approximately 5%` → 是判据右端，不是模型精度目标

描述性约束给了噪声地板 σ ≈ 5%。它的**唯一合法用途**是构造显著性阈值（2σ = 0.10 × 参考量），**不是**「模型误差要小于 5%」，也**不是**「R² > 0.95 就达标」。若论文写「模型相对误差 4.8%，优于实验误差 5%」，是把噪声地板当精度指标——这正是 `out/00-problem.md` §4 的 M1 陷阱。

**这一条是 §7.2 口径分歧的根源**：题面只说「5% 的平行实验误差」，没说 5% 是相对于**哪个量**。相对基准端点、相对末端点、相对全序列均值，三种读法都能自圆其说，而 `DFA/CS Syngas` 一格会因此翻转。论文若不在符号表里把分母写死，读者无法复算。

### 5.5 L138 `Pyrolysis Products: Tar, Water, Char, Syngas` → 四产物闭合是硬约束

本报告实测：Annex I 全部 25 列（3 组合 × 各自档位），`Tar + Water + Char + Syngas` 的求和**唯一值 = 100.0**（DFA/CS、DFA/CE、DFA/LG 三组合分别验证，全部 `unique=[100.0]`）。

**更强的一条证据：附件里有一整行本来就是公式。** 用 `openpyxl.load_workbook(path, data_only=False)` 扫全表（命令见 §8.6），三个组合各有一行不是硬值而是 `=100 − 其余三项`：

| 组合 | 公式行 | 公式格数（共 9 个配比列） | 形态 |
|---|---|---|---|
| DFA/CS | `Syngas yield`（r6） | **8 / 9** —— 非公式的那格是硬值 `24.49`（`0/100` 空白对照） | `=100-C3-C4-C5` |
| DFA/CE | `Char yield`（r13） | **8 / 9** —— 非公式那格为空（无 `0/100`） | `=100-B11-B12-B14` |
| DFA/LG | `Tar yield`（r18） | **8 / 9** —— 非公式那格为空（无 `0/100`） | `=100-B19-B20-B21` |

Annex II 全表无公式（0 个公式格）。三个组合合计 **24 个公式格**。**含义**：CS 的 Syngas、CE 的 Char、LG 的 Tar 在附件层面就是「100 减另外三项」的派生量。对这三个产物单独回归得到的 R² 必然虚高（它在数学上不是独立观测），**不能作为模型拟合优度的证据**。`data/results_q1.json` 用 `is_derived: true` 独立标出了同样三格（`DFA/CS Syngas`、`DFA/CE Char`、`DFA/LG Tar`），与本表逐格对应。

**可复算的错误形态**：把 4 个产物当 4 条独立回归分别拟合，会得到 4 组互相不闭合的预测（和 ≠ 100），并把派生行的虚高 R² 当作证据。合法写法：CLR/ILR 变换，或 3 维 + 归一化。若论文摘要写「建立了 4 个产物的产率模型」而不提闭合，评审可直接用这 25 列求和反证。

### 5.6 L78–80 为何不用 5/100、7/100 → 若论文自称「加密档位」就与题面相反

题面明确说小配比会被 5% 误差吞掉。若论文建议「补做 5/100、7/100 以提高分辨率」，与 L78–80 相反；正确方向是提高配比或增加平行样。

---

## 6 类② 可执行交付物：本题哪几问必须给「人群/剂量/阈值」式的落地件

派单的第二条陷阱是「题面要方案，论文只给一句队列级结论＝没做」。本题没有政策建议类小问（§3.1），但**有两问在实质上要求可执行判定规则**，不是叙述：

### 6.1 Q1（L93–95）与 Q3（L100–103）：`significant` 是可执行二值判定

题面用 `significant` 两次（L94、L101）。这不是形容词，是**要求给出判定阈值 + 逐格结论**。判据只能从 L76–77 的 5% 派生：**2σ = 0.10 × 全序列均值**，判定「极差 span > 2σ ⇒ 显著」。

> **本表采用「口径 B」，这是本报告的一个显式选择，不是唯一选择。** 另一种同样自洽的口径（「口径 A」：阈值 `0.10 × 两端点最大值`、效应量 `|末端点 − 首端点|`）会让下表中 **`DFA/CS Syngas` 一格翻转为「不显著」**（A：2.49 < 2.70；B：3.96 > 2.72）。12 格里只有这一格受口径影响，其余 11 格两种口径同判。翻转机制、两口径全表对照与择一理由见 **§7.2**——那一节是本报告关于「口径混用」的主证据，本表只是它的落地版。

本报告按口径 B 把 Q1 的 12 格全部算完（可直接进正文；命令见 §8.2）：

| 组合 | 产物 | 极差 span | 2σ（=0.10×均值） | span/2σ | 判定 |
|---|---|---:|---:|---:|---|
| DFA/CS | Tar | 7.33 | 1.45 | 5.04 | **显著** |
| DFA/CS | Water | 4.18 | 2.89 | 1.45 | **显著** |
| DFA/CS | Char | 0.76 | 2.94 | 0.26 | **不显著** |
| DFA/CS | Syngas | 3.96 | 2.72 | 1.46 | **显著（口径敏感，见 §7.2）** |
| DFA/CE | Tar | 10.86 | 4.21 | 2.58 | **显著** |
| DFA/CE | Water | 11.28 | 1.93 | 5.86 | **显著** |
| DFA/CE | Char | 3.48 | 2.41 | 1.45 | **显著** |
| DFA/CE | Syngas | 3.98 | 1.46 | 2.73 | **显著** |
| DFA/LG | Tar | 9.87 | 1.13 | 8.73 | **显著** |
| DFA/LG | Water | 8.39 | 2.04 | 4.11 | **显著** |
| DFA/LG | Char | 1.19 | 5.73 | 0.21 | **不显著** |
| DFA/LG | Syngas | 3.41 | 1.09 | 3.12 | **显著** |

方向（DFA/CS，`0/100 → 100/100`，本报告实测）：Tar 19.46 → 12.13（**−7.33，−37.7%**，单调降）；Water 26.84 → 31.02（**+4.18，+15.6%**，单调升）；Char 29.21 → 29.87（+0.66，+2.3%，**非单调**）；Syngas 24.49 → 26.98（+2.49，+10.2%，**非单调**，峰值在 50/100 的 28.45）。

**因此 Q1 的答案不是「都有显著促进」，而是「Char 无显著变化」**（CS 与 LG 两组合都是）。若论文写「脱硫灰对四类产物产率均有显著促进」，**与数据相反，可用上表直接反证**。

> **交叉验证（本报告独立性检查）**：上表 12 行是我从两份 xlsx 独立重算的。评审后期 `data/results_q1.json`（17:30:46 落盘，15970 B）出现，其 `combos[*].products[*]` 的 `span` / `thr_trend` / `span_over_thr` / `trend_significant` 四个字段与上表 **12 格逐格完全一致**（含 `CS Char` 与 `LG Char` 两格 `false`）。这说明本表不是「我一个人的算法」，而是与论文侧产物键同源同值——**报告里每一个判定都能被 `data/results_q1.json` 的键名指认**，满足派单「印出来的数必须能被别人复算」的要求。该 JSON 的 `meta.caliber` 也写明 `eps_rel: 0.05`、`path_trend` 与 `dof`（四产物 Σ=100 → 仅 3 自由度，拟合在 3 维 ILR 空间），与 §5.5 的闭合约束同源。

> **本小节已按 `data/results_q3.json` 的 `meta.caliber` 更正（原稿写错了一处）**：原稿写「Q3 的 20 格 = 5 个公共档位 × 4 产物」。**错。** Annex I 的 CE 与 LG **各有 8 档**（`10/100…100/100`，无 `0/100`），所以**产物**可配 **8 对 = 32 格**；只有**气体**受 Annex II 限制（CE/LG 各 5 档 `20/40/50/80/100`）才是 **5 对 = 25 格**。`results_q3.json` 的 meta 原话：「Annex I 的 CE/LG 各有 8 档（10…100），逐档可配 8 对」「Annex II 的 CE/LG 各有 5 档（20/40/50/80/100），只能配 5 对」「两处档数不同，不得混用一个『公共档位』说法」。原稿把气体的 5 档限制套到了产物上，等于白扔 3 个档位、12 个格子。下表按 8 档重算。

Q3 产物：CE vs LG，**8 个档位 × 4 产物 = 32 格**（本报告实测，命令见 §8.2）：

| 档位 | ΔTar | ΔWater | ΔChar | ΔSyngas |
|---|---:|---:|---:|---:|
| 10/100 | +16.36 | **+12.12** | −36.74 | +8.26 |
| 20/100 | +24.54 | +2.83 | −32.55 | +5.18 |
| 30/100 | +31.40 | **−2.33** | −32.96 | +3.89 |
| 40/100 | +33.50 | −4.07 | −32.28 | +2.85 |
| 50/100 | +35.04 | −5.28 | −32.60 | +2.84 |
| 60/100 | +35.39 | −3.62 | −32.64 | **+0.87** |
| 80/100 | +32.94 | −1.48 | −33.58 | +2.12 |
| 100/100 | +37.09 | −7.55 | −32.82 | +3.28 |

**ΔWater 在 30/100 变号**（10/100 是 +12.12，20/100 是 +2.83，30/100 起全负）。若论文写「CE 的水产率恒低于 LG」，在 10/100 与 20/100 两格上就是错的。这是「同一现象两种符号」的典型陷阱：**只看 30–100 六档会得出「CE 恒低」，把 10/100 与 20/100 补回来就翻。** 任何「CE 比 LG 高/低」的结论都必须带档位条件。`results_q3.json` 的 `flips` 字段独立给出同一结论：`{"products": ["Water"], "gases": []}`——**只有 Water 变号，气体一组都不变号。**

上表只给了差值，**没给判定**——因为 Q3 是「两个独立测量之差」，`code/model_skeleton.py:318` 为这类比较声明了专用路径 `τ_diff = 0.10·√(y_a² + y_b²)`，而不是 Q1 用的序列口径。按 `τ_diff` 逐格判定（命令见 §8.2）：

| 档位 | ΔTar vs τ | ΔWater vs τ | ΔChar vs τ | ΔSyngas vs τ |
|---|---|---|---|---|
| 10/100 | +16.36 / 3.89 **显著** | +12.12 / 3.14 **显著** | −36.74 / 6.20 **显著** | +8.26 / 1.88 **显著** |
| 20/100 | +24.54 / 4.07 **显著** | +2.83 / 2.83 **临界（比值 1.0003，余量 0.00085）** | −32.55 / 6.26 **显著** | +5.18 / 1.85 **显著** |
| 30/100 | +31.40 / 4.42 **显著** | −2.33 / 2.69 **不显著（0.87）** | −32.96 / 6.20 **显著** | +3.89 / 1.91 **显著** |
| 40/100 | +33.50 / 4.50 **显著** | −4.07 / 2.69 **显著** | −32.28 / 6.21 **显著** | +2.85 / 1.88 **显著** |
| 50/100 | +35.04 / 4.55 **显著** | −5.28 / 2.70 **显著** | −32.60 / 6.22 **显著** | +2.84 / 1.89 **显著** |
| 60/100 | +35.39 / 4.53 **显著** | −3.62 / 2.85 **显著** | −32.64 / 6.23 **显著** | **+0.87 / 1.74 不显著（0.50）** |
| 80/100 | +32.94 / 4.44 **显著** | −1.48 / 2.93 **不显著（0.51）** | −33.58 / 6.18 **显著** | +2.12 / 1.73 **显著** |
| 100/100 | +37.09 / 4.60 **显著** | −7.55 / 2.87 **显著** | −32.82 / 6.25 **显著** | +3.28 / 1.76 **显著** |

**32 格里 29 格显著、3 格不显著**（Water@30/100 0.87、Water@80/100 0.51、Syngas@60/100 0.50），另有 1 格临界（Water@20/100，比值 1.0003、余量 0.00085）。**Q3 的正确措辞是：Tar 与 Char 在全部 8 档上 CE 与 LG 均显著不同（方向恒为 CE 高 Tar、CE 低 Char）；Water 与 Syngas 只在部分档位显著。** 若论文只写「CE 与 LG 有显著差异」，就把 3 个不显著格与 1 个临界格一起抹掉了——这正是 `significant` 作为可执行判定的落点。

Q3 气体：CE vs LG，**5 个公共档位 × 5 组分 = 25 格**（本报告实测）：**24 格显著，1 格不显著**（`CO @ 20/100`，`|d| = 1.53` vs `τ = 2.05`，比值 0.75）。方向：H₂ 恒 CE 高（+25.93…+64.99），CO/CO₂/CH₄ 恒 CE 低（CO −1.53…−15.64、CO₂ −5.65…−41.56、CH₄ −24.47…−31.35），C₂H₆ 恒 CE 高（+3.15…+13.72）。

**口径敏感性（Q3 全 57 格）：** A（`0.10·max`）与 C（`τ_diff`）在**产物 32 格上有 1 处分歧**（`Water @ 30/100`：`|d| = 2.330`，`τ_diff = 2.693` 判 n.s.，`τ_max = 2.017` 判 SIG），在**气体 25 格上有 1 处分歧**。合计 57 格里 2 格翻转——比原稿「20 格 0 分歧」的说法更准确：**不是 0 分歧，是格子数被我少算了。**

### 6.2 Q5（L107–111）：预测必须给「点 + 区间 + 外推边界」三件套

`under limited data conditions` 明说要处理小样本。可执行交付物至少包含：
1. **点预测**（逐组合逐产物，带单位 `wt.%(daf)` / `mL/g,daf`）；
2. **预测区间**（不是置信区间；n=5–9，必须说明用 t 分布还是 bootstrap）；
3. **外推边界**（题面只到 100/100 = DFA 质量分数 50.0000%，本报告实测 `100×a/(a+100)`：10/100→9.0909%、20/100→16.6667%、…、100/100→50.0000%）。**超出 50% 的部分是外推，必须声明不可用。**
4. **留一/留档位验证**（5–9 个点做不了 k 折，只能 LOO 或 leave-one-ratio-out）。

若 Q5 只写「建立了 BP 神经网络，R²=0.98」，三件套一件都没给 → **没做**。注意本题**没有时间轴**，任何「时序预测」「LSTM 预测未来 5 年」都是把 APMCM 的 `predict` 模式错套到本题上。

---

## 7 四类高频可复算缺陷：本槽位能查的几类

派单点名四类（口径混用 / 倍数与百分数 / 多重比较 / 图表刻度），本槽位逐类查：**多重比较命中（§7.1）、口径混用命中（§7.2）、倍数与百分数部分命中（§7.3）、图表刻度 BLOCKED-BY-ABSENCE（§7.4）**。

### 7.1 多重比较（命中：检验数 ≥12，骨架里 0 处校正）

Q1 是 **12 个检验**（3 组合 × 4 产物），Q2 是 **19 条序列**（9 + 5 + 5），Q3 是 **57 格**（产物 8 档 × 4 = 32，气体 5 档 × 5 = 25）。在 α = 0.05 下不校正的族错误率（本报告实算）：

```
k=12 → 1 − 0.95^12 = 0.4596
k=19 → 1 − 0.95^19 = 0.6226
k=32 → 1 − 0.95^32 = 0.8063
k=25 → 1 − 0.95^25 = 0.7226
k=57 → 1 − 0.95^57 = 0.9463
```

即「整张表至少出现一个假显著」的概率 46%–95%。`main.tex` 全文 `Bonferroni` / `BH` / `p-value` 各 **0 命中**——校正机制在骨架里根本不存在。Q1/Q3 的表必须给 BH 或 Bonferroni 后的 q 值，否则「32 格里 29 格显著」这句话不可信。

（本报告 §6.1 的 `span > 2σ` 是**必要筛**，不是检验替代品；论文若用它下结论，须明写「这是基于题面 5% 噪声地板的保守筛，未做多重比较校正，故同时报告 BH-q」。）

### 7.2 口径混用（命中：**三种**各自自洽的判据，在同一格给出相反判定）

> **更正记录（本报告自查）**：本节初稿写的是「`out/00-problem.md` §7.1 同一张表混用两个分母」。**该指控不成立，已撤回。** 撤回依据：把上游四个 2σ 逐个对三种候选分母做拟合，四个全部落在 `0.10 × max(两端点)` 上，误差 ≤ 0.004（命令见 §8.5）。上游是一套自洽口径；初稿之所以看着像混用，是因为 Tar 的最大端点恰好是 `0/100` 基线，而其余三项最大端点在 `100/100`。**保留这条更正记录，是因为「我一开始也读错了」本身就是这道题的口径陷阱的证据。**

真正的问题不是「谁算错」，而是**几种都说得通的判据会给出相反结论**。目前工作区里已经出现了**三种**口径，其中第三种是 `code/model_skeleton.py` 自己声明的——该文件在本报告撰写期间三次落盘（`17:22:45` 18213 B、`17:23:37` 18495 B、`17:39:50` 19720 B），**每一次都晚于本报告初稿，也都晚于 `main.tex`**：

| 口径 | 阈值 2σ | 效应量 | 定义域 | 出处 |
|---|---|---|---|---|
| **A（上游口径）** | `0.10 × max(首端点, 末端点)` | `\|末端点 − 首端点\|` | 需有 `0/100` 基线，即只有 DFA/CS 严格成立 | `out/00-problem.md` §7.1 |
| **B（本报告口径）** | `0.10 × mean(全序列)` | `span = max − min` | 任意序列 | 本报告 §6.1 |
| **C（骨架口径）** | `τ_single = 0.10·y`（单测量 vs 真值）<br>`τ_diff = 0.10·√(y_a²+y_b²)`（两独立测量之差） | 逐次比较的 `\|y_a − y_b\|` | 逐格，不需要序列统计量 | `code/model_skeleton.py:11-12`、`:317-318` |

把 A、B 两种口径同时跑遍 Q1 的 12 格（命令见 §8.5，逐格输出照抄在该节）：

| 组合·产物 | A 阈值 | A 效应 | A 判定 | B 阈值 | B 效应 | B 判定 | 一致？ |
|---|---:|---:|---|---:|---:|---|---|
| DFA/CS Tar | 1.95 | 7.33 | 显著 | 1.45 | 7.33 | 显著 | 一致 |
| DFA/CS Water | 3.10 | 4.18 | 显著 | 2.89 | 4.18 | 显著 | 一致 |
| DFA/CS Char | 2.99 | 0.66 | 不显著 | 2.94 | 0.76 | 不显著 | 一致 |
| **DFA/CS Syngas** | **2.70** | **2.49** | **不显著** | **2.72** | **3.96** | **显著** | **相反** |
| DFA/CE Tar | 4.53 | 10.86 | 显著 | 4.21 | 10.86 | 显著 | 一致 |
| DFA/CE Water | 2.74 | 11.28 | 显著 | 1.93 | 11.28 | 显著 | 一致 |
| DFA/CE Char | 2.46 | 3.18 | 显著 | 2.41 | 3.48 | 显著 | 一致 |
| DFA/CE Syngas | 1.67 | 2.76 | 显著 | 1.46 | 3.98 | 显著 | 一致 |
| DFA/LG Tar | 1.81 | 9.87 | 显著 | 1.13 | 9.87 | 显著 | 一致 |
| DFA/LG Water | 2.37 | 8.39 | 显著 | 2.04 | 8.39 | 显著 | 一致 |
| DFA/LG Char | 5.82 | 0.74 | 不显著 | 5.73 | 1.19 | 不显著 | 一致 |
| DFA/LG Syngas | 1.07 | 2.22 | 显著 | 1.09 | 3.41 | 显著 | 一致 |

**12 格里 11 格两种口径同判，只有 `DFA/CS Syngas` 一格翻转。** 翻转的机制可复算：Syngas 在 DFA/CS 上**非单调**，峰值出现在 `50/100` 的 **28.45**，而两端点是 24.49 与 26.98。端点差 2.49 远小于全序列极差 3.96，于是「只比两端」判不显著、「比全序列」判显著。

**这一格决定了 Q1 结论的措辞**：

- 若采用口径 A，Q1 答案是「**四类产物里 Char 与 Syngas 无显著变化**，催化只显著作用于 Tar 与 Water」；
- 若采用口径 B，Q1 答案是「**只有 Char 无显著变化**，其余三类均显著」。

两句话都能从同一份 Annex I 复算出来，**这就是本题最该在论文里显式声明口径的地方**。本报告 §6.1 表采用口径 B（并在该表该行标注了「口径敏感」），理由是：题面 L93–94 问的是「**the yield … in relation to the mixing ratios**」，即整条曲线随配比的响应，`span` 才是这句话的直接对应量；只比两端会把非单调序列的中间响应丢掉。

**口径 C 是工作区自己后来的选择。** `code/model_skeleton.py:11-12` 明文写了两条路径：`τ_single = 0.10·y`（单测量 vs 已知真值）、`τ_diff = 0.10·√(y_a²+y_b²)`（两个独立测量的差），并加了一句「凡写「显著」必须标路径」。这两个式子的分母不是序列统计量，而是**被比较的那个测量本身**——所以它既不会像 A 那样依赖「有没有 0/100 基线」，也不会像 B 那样把非单调序列的中间峰算进极差。Q3 恰好是「两个独立测量之差」，`τ_diff` 在形式上正是它的对应判据。

**但实测结果要纠正一句我本想写的话。** 我一度打算写「上游 Q3 用的就是 `τ_diff` 等价形式」——**该推断不成立，已弃用**。把上游 §7.2 报的四组阈值区间（Tar 3.83–4.53、Water 2.10–2.37、Char 5.70–5.75、Syngas 1.33–1.54）拿五个候选公式逐个拟合（命令见 §8.2 末段），结果：

| 候选公式 | Tar | Water | Char | Syngas | 是否吻合上游区间 |
|---|---|---|---|---|---|
| `0.10·max(y_a,y_b)` | 3.83–4.53 | 2.10–2.37 | 5.70–5.75 | 1.33–1.54 | **四组全部吻合** |
| `0.10·√(y_a²+y_b²)` | 4.07–4.60 | 2.69–2.93 | 6.18–6.26 | 1.73–1.89 | 全部偏高，不吻合 |
| `0.10·(y_a+y_b)/2` | 2.60–2.70 | 1.89–2.07 | 4.04–4.12 | 1.22–1.33 | 不吻合 |
| `0.05·√2·max` | 2.71–3.20 | 1.48–1.68 | 4.03–4.06 | 0.94–1.09 | 不吻合 |
| `0.10·min(y_a,y_b)` | 0.82–1.38 | 1.61–1.99 | 2.36–2.49 | 1.02–1.18 | 不吻合 |

**上游 Q3 用的也是 `0.10·max(y_a,y_b)`，与它 Q1 的端点口径同源——上游其实是一套口径贯穿到底，不是混用。** 我原先看到「结论都是 4/5 超噪」就以为是同一公式，这是「结论一致 ≠ 公式相同」的误推。两式之比 `τ_diff / τ_max = √(1 + (min/max)²)`，取值区间 `[1, √2]`：两值相等时 `τ_diff` 最高、比 `0.10·max` 高 41%；两值悬殊时趋于相等。本题实测比值（命令见 §8.2）：

| 产物 | `τ_diff/τ_max` 区间 | 相当于比 `0.10·max` 高 |
|---|---|---|
| Tar | 1.0162–1.0626 | +1.6% – +6.3% |
| Water | 1.2100–1.3662 | **+21.0% – +36.6%** |
| Char | 1.0817–1.0899 | +8.2% – +9.0% |
| Syngas | 1.2003–1.3061 | **+20.0% – +30.6%** |

即两式在 Tar/Char 上几乎同值（CE 与 LG 相差 10–40 倍），在 Water/Syngas 上差两到三成（CE 与 LG 只差 1.2–2 倍）。**但「20 格 0 分歧」是原稿少算格子后的假象**——按真实格数（产物 32 + 气体 25 = 57），两式有 **2 处分歧**：`Water @ 30/100`（`|d| = 2.330`，`τ_diff = 2.693` 判 n.s.，`τ_max = 2.017` 判 SIG）与气体 1 格。其余 55 格同判，因为最接近阈值的几格仍留有余量：`Water @ 80/100` 的 `|d|/τ_diff = 0.506`（`0.10·max` 下 0.69，两种口径都判不显著）；`Water @ 20/100` 的 `|d| = 2.8300` 对 `τ_diff = 2.8291`，**比值 1.0003、余量 0.00085**（`0.10·max` 下 τ=2.14、比值 1.32）。**这一格的正负号不由物理决定，而由第三位小数的舍入决定**——所以真正需要论文声明的不是「换公式会改答案」，而是「这一格压在阈值上，路径与舍入规则必须写出来，否则读者无法判断 1.0003 是算出来的还是凑出来的」。

所以「口径混用」在本题的准确形态是：**A 与 C 都是自洽的，在 Q3 的 57 格里 55 格同判、2 格翻转；真正会翻转得更彻底的是 Q1 的 `DFA/CS Syngas` 一格（A↔B）**。`τ_diff` 的价值不在于「换答案」，而在于它是**两个独立测量之差**的正确误差传播形式，写进论文比 `0.10·max` 更站得住；但若论文只写「显著」而不写路径，读者仍然无法判断翻转格是怎么来的。

**返修要求（P1）**：`main.tex` 必须在符号表或 Q1 首段写明三件事——① 2σ 走哪条路径（`τ_single` / `τ_diff` / 端点口径 A / 全序列口径 B）；② 效应量是 `span` 还是 `|Δ端点|` 还是 `|y_a − y_b|`；③ 若 Q1 与 Q3 用了不同路径，必须分别标注，因为 `DFA/CS Syngas` 会在 A/B 之间翻转，而 `Water @ 20/100` 在 `τ_diff` 下只有 0.00085 的余量、舍入方式即可改判。**只写一个判定而不写口径，读者无法判断你是算了还是抄了。**

### 7.3 量纲与基线不可比（命中：三类不可比被混在一句话里的风险）

§7.2 说的是「同一判定、两种口径」。这里说的是**更基础的不可比**——三处一旦写进同一句结论就会错：

1. **基线段数不同**：Q1 的 DFA/CS 有 **9 档**（含 `0/100` 空白对照），CE/LG 只有 **8 档**（无 `0/100`）。因此「催化增量」这个量**只有 CS 能算**（有基线可减），CE/LG 算不出绝对增量，只能算「随配比的相对变化」。若论文对 CE/LG 写「脱硫灰使焦产率提高 xx%」，是把无基线组当有基线组。
2. **量纲不可加**：`wt.%(daf)`（Annex I，四产物产率）与 `mL/g,daf`（Annex II，气体组分产率）不能相加、不能在同一张图左右轴直接比较大小。
3. **说明列不是数据**：Annex II 每个分表末列的表头是一整句说明文字 `Gas Yield, which refers to the amount of gas produced per gram of raw material.`，本报告实测该列全为 `nan`。按列解析会多出 1 条空序列（我在第一遍脚本里就踩到了，见 §8.2 的 `species` 过滤）——若论文报「20 条气体序列」，其中一条是这句话。

### 7.4 图表刻度（BLOCKED-BY-ABSENCE）

`figures/` = **0 个文件**，`\includegraphics` = **0 处**，`main.pdf` 不存在。无图可量，`mmkit.figfont` 无法执行（§0.1 第③条）。**本项无法判定，不是通过。** 待有 PDF 后必须重跑 `mmkit.figfont`，判据是「图内 ≥3 字符的字号 ≥ 6 pt」。

---

## 8 复算命令（拿同一份数据可原样重跑）

解释器：`E:\Mini\envs\mathmodel\python.exe`（Python 3.11.18，含 pandas）。

**本节六段代码（§8.1–§8.6）均已从本文件原样抽出、独立执行验证过**：抽取方式 `re.search(r"### 8\.N.*?```python\n(.*?)```", ...)` 后直接交给解释器，六段全部 `exit 0`，且文中每一段「实测输出」都能在真实 stdout 里找到**连续、逐字、顺序一致**的对应片段（校验脚本逐行比对 `contiguous_subrun`，六段全 True）。§8.2 修过一处 `NameError`（原稿漏绑定 `CE`/`LG`），已在代码内补上并注明；§8.2 贴出的是 81 行输出中的第 75–81 行（其余 74 行已整理成 §5.5/§6.1 的三张表）。

### 8.1 把官方 8 个关注点模式跑在本题上（§3 的来源）

```python
import json, re, pathlib
d = json.loads(pathlib.Path(r"E:\数学建模\APMCM-PROBLEMS\_official_evidence.json").read_text(encoding="utf-8"))
lines = pathlib.Path(r"E:\数学建模\PRACTICE_2023B\problem\problem.txt").read_text(encoding="utf-8").splitlines()
for a in d["aspects"]:
    pat = re.compile(a["pattern"])
    hits = [(i+1, l.strip()) for i, l in enumerate(lines) if pat.search(l)]
    print(a["id"], a["rule"], f"corpus={a['n_present']}/{a['n_total']}", f"hits={len(hits)}", hits[:4])
```

实测输出（照抄，8 行）：

```
restatement R-W01 corpus=12/35 hits=0 []
data_attachment R-M14 corpus=19/35 hits=2 [(121, 'Combinations.xlsx'), (130, 'Combinations.xlsx')]
predict R-T04 corpus=13/35 hits=2 [(82, 'learning to predict the pyrolysis product yield or production under'), (87, 'on the trend of changes in the distribution of pyrolysis products.')]
optimize R-M10 corpus=5/35 hits=0 []
quantify R-W05 corpus=13/35 hits=0 []
letter R-W09 corpus=3/35 hits=0 []
policy R-W08 corpus=19/35 hits=0 []
sensitivity R-V07 corpus=8/35 hits=1 [(31, 'necessary to consider their controllability and stability in reaction')]
```

读法：`policy 0`、`quantify 0`、`optimize 0`、`letter 0`、`restatement 0`；`data_attachment 2`（L121/L130，只是 `.xlsx` 文件名）；`predict 2`（L82/L87）；`sensitivity 1`（L31，假阳性——讲的是模型化合物选择的「可控性与稳定性」，不是要求做敏感性检验）。

### 8.2 Q1 12 格 + Q2 19 序列 + Q3 57 格（§5.2、§6.1 的来源）

```python
import pandas as pd
D = r"E:\数学建模\PRACTICE_2023B\data"
a1 = pd.read_excel(D + r"\Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx", header=None)
a2 = pd.read_excel(D + r"\Annex II-Pyrolysis Gas Yields of Three Pyrolysis Combinations.xlsx", header=None)
P8 = ["10/100","20/100","30/100","40/100","50/100","60/100","80/100","100/100"]

def parse_I(df):
    out = {}
    for name, hdr in [("DFA/CS",1), ("DFA/CE",9), ("DFA/LG",16)]:
        ratios = [str(v) for v in df.iloc[hdr].tolist()[1:] if str(v) != "nan"]
        prods  = [str(v) for v in df.iloc[hdr+1:hdr+5, 0].tolist()]
        out[name] = {"ratios": ratios,
                     "data": {p.replace(" yield",""): {r: float(df.iloc[hdr+1+i][1+j]) for j, r in enumerate(ratios)}
                              for i, p in enumerate(prods)}}
    return out

def parse_II(df):
    out = {}
    for name, hdr in [("DFA/CS",1), ("DFA/CE",10), ("DFA/LG",18)]:
        species = [str(v) for v in df.iloc[hdr].tolist()[1:] if str(v) != "nan"]
        species = [s for s in species if not s.startswith("Gas Yield")]   # 剔掉说明列
        ratios, data, k = [], {s: {} for s in species}, hdr+1
        while k < len(df) and str(df.iloc[k][0]) in P8 + ["0/100"]:
            r = str(df.iloc[k][0]); ratios.append(r)
            for j, s in enumerate(species): data[s][r] = float(df.iloc[k][1+j])
            k += 1
        out[name] = {"ratios": ratios, "data": data}
    return out

I, II = parse_I(a1), parse_II(a2)
for k, v in I.items():                       # 闭合性
    print(k, sorted({round(sum(v["data"][p][r] for p in v["data"]), 6) for r in v["ratios"]}))
for k, v in I.items():                       # Q1 12 格
    for p in v["data"]:
        vals = [v["data"][p][r] for r in v["ratios"]]
        m = sum(vals)/len(vals); thr = 0.10*m; span = max(vals)-min(vals)
        print(k, p, f"span={span:.2f} 2sig={thr:.2f} ratio={span/thr:.2f}", "SIG" if span > thr else "n.s.")
for k, v in II.items():                      # Q2 19 序列
    for s in v["data"]:
        vals = [v["data"][s][r] for r in v["ratios"]]
        m = sum(vals)/len(vals); thr = 0.10*m; span = max(vals)-min(vals)
        print(k, s, f"span={span:.3f} 2sig={thr:.3f} ratio={span/thr:.2f}", "SIG" if span > thr else "n.s.")
for r in ["10/100","20/100","30/100","40/100","50/100","60/100","80/100","100/100"]:   # Q3 产物 8 档（差值）
    print(r, [f"{p}:{I['DFA/CE']['data'][p][r]-I['DFA/LG']['data'][p][r]:+.2f}" for p in I["DFA/CE"]["data"]])
n_sig = 0
for r in ["10/100","20/100","30/100","40/100","50/100","60/100","80/100","100/100"]:   # Q3 产物 32 格（tau_diff）
    for p in ["Tar","Water","Char","Syngas"]:
        a, b = I["DFA/CE"]["data"][p][r], I["DFA/LG"]["data"][p][r]
        d, tau = a-b, 0.10*(a*a+b*b)**0.5
        n_sig += abs(d) > tau
        print(f"{r:8s} {p:6s} CE={a:7.2f} LG={b:7.2f} d={d:+7.2f} tau={tau:6.2f} "
              f"|d|/tau={abs(d)/tau:5.2f} {'SIG' if abs(d) > tau else 'n.s.'}")
print("Q3 products SIG:", n_sig, "/32")

# Q3 阈值公式归属：把上游 §7.2 报的四组区间拿五个候选公式逐个拟合（§7.2 拟合表的来源）
CE, LG = I["DFA/CE"]["data"], I["DFA/LG"]["data"]      # 必须先绑定，否则下面 NameError
up = {"Tar": (3.83, 4.53), "Water": (2.10, 2.37), "Char": (5.70, 5.75), "Syngas": (1.33, 1.54)}
cands = {
    "0.10*max(ya,yb)":      lambda a, b: 0.10 * max(a, b),
    "0.10*sqrt(ya^2+yb^2)": lambda a, b: 0.10 * (a*a + b*b) ** 0.5,
    "0.10*(ya+yb)/2":       lambda a, b: 0.10 * (a + b) / 2,
    "0.05*sqrt(2)*max":     lambda a, b: 0.05 * 2 ** 0.5 * max(a, b),
    "0.10*min(ya,yb)":      lambda a, b: 0.10 * min(a, b),
}
R5 = ["20/100", "40/100", "50/100", "80/100", "100/100"]
for p in ["Tar", "Water", "Char", "Syngas"]:
    lo, hi = up[p]
    print(f"{p:8s} upstream {lo:.2f}-{hi:.2f} |", end=" ")
    for k, f in cands.items():
        v = [f(CE[p][r], LG[p][r]) for r in R5]
        ok = abs(min(v) - lo) < 0.02 and abs(max(v) - hi) < 0.02
        print(f"{k}={min(v):.2f}-{max(v):.2f}{' OK' if ok else ''}", end="  ")
    print()

# A 与 C 在 Q3 全 57 格上是否分歧（§7.2「2 处分歧」的来源）
R8 = ["10/100","20/100","30/100","40/100","50/100","60/100","80/100","100/100"]
dis = []
for p in ["Tar","Water","Char","Syngas"]:
    for r in R8:
        a, b = CE[p][r], LG[p][r]
        if (abs(a-b) > 0.10*max(a, b)) != (abs(a-b) > 0.10*(a*a+b*b)**0.5):
            dis.append((p, r))
print("A-vs-C disagreements on Q3 products (8 tiers):", len(dis), "/32", dis)
# 气体 25 格同理（Annex II 的 CE/LG 各 5 档）
G = II["DFA/CE"]["data"]; H = II["DFA/LG"]["data"]
R5 = ["20/100","40/100","50/100","80/100","100/100"]
dg = [(s, r) for s in G for r in R5
      if (abs(G[s][r]-H[s][r]) > 0.10*max(G[s][r], H[s][r]))
      != (abs(G[s][r]-H[s][r]) > 0.10*(G[s][r]**2+H[s][r]**2)**0.5)]
print("A-vs-C disagreements on Q3 gases (5 tiers):", len(dg), "/25", dg)
```

实测输出（照抄）。全量输出共 **81 行**：前 3 行是四产物闭合验证（`DFA/CS [100.0]` 等），接着 12 行 Q1、19 行 Q2、8 行 Q3 产物差值、32 行 Q3 产物判定、25 行 Q3 气体判定——这些已分别整理进 §5.5 与 §6.1 的三张表，此处只贴最后两段（阈值公式归属 + 口径分歧），因为它们是 §7.2 的**唯一**依据：

```
Q3 products SIG: 29 /32
Tar      upstream 3.83-4.53 | 0.10*max(ya,yb)=3.83-4.53 OK  0.10*sqrt(ya^2+yb^2)=4.07-4.60  0.10*(ya+yb)/2=2.60-2.70  0.05*sqrt(2)*max=2.71-3.20  0.10*min(ya,yb)=0.82-1.38
Water    upstream 2.10-2.37 | 0.10*max(ya,yb)=2.10-2.37 OK  0.10*sqrt(ya^2+yb^2)=2.69-2.93  0.10*(ya+yb)/2=1.89-2.07  0.05*sqrt(2)*max=1.48-1.68  0.10*min(ya,yb)=1.61-1.99
Char     upstream 5.70-5.75 | 0.10*max(ya,yb)=5.70-5.75 OK  0.10*sqrt(ya^2+yb^2)=6.18-6.26  0.10*(ya+yb)/2=4.04-4.12  0.05*sqrt(2)*max=4.03-4.06  0.10*min(ya,yb)=2.36-2.49
Syngas   upstream 1.33-1.54 | 0.10*max(ya,yb)=1.33-1.54 OK  0.10*sqrt(ya^2+yb^2)=1.73-1.89  0.10*(ya+yb)/2=1.22-1.33  0.05*sqrt(2)*max=0.94-1.09  0.10*min(ya,yb)=1.02-1.18
A-vs-C disagreements on Q3 products (8 tiers): 1 /32 [('Water', '30/100')]
A-vs-C disagreements on Q3 gases (5 tiers): 1 /25 [('CO', '20/100')]
```

读法：**只有 `0.10*max(ya,yb)` 一列在四个产物上都带 `OK`**——其余四个候选公式（`τ_diff`、算术平均、`0.05√2·max`、`min`）全部对不上上游报的区间。这就是「上游 Q3 用的也是 `0.10·max`」的判据，也是本报告第二稿「上游用 `τ_diff`」被弃用的原因。

**最后那两行是本报告自己的更正痕迹**：初稿此处印的是 `A-vs-C disagreements on Q3: 0 /20`，那是把产物格数少算成 20（误用了气体的 5 档）得到的。按真实格数重跑后是 `1 /32` 与 `1 /25`，合计 57 格里 2 格翻转。上面六行是重跑后的原样输出（含行序），可整段复制执行。

### 8.3 配比 → DFA 质量分数（§6.2 外推边界的来源）

```python
for a in [10,20,30,40,50,60,80,100]: print(f"{a}/100 -> {100*a/(a+100):.4f}%")
```

实测输出（照抄，8 行）：

```
10/100 -> 9.0909%
20/100 -> 16.6667%
30/100 -> 23.0769%
40/100 -> 28.5714%
50/100 -> 33.3333%
60/100 -> 37.5000%
80/100 -> 44.4444%
100/100 -> 50.0000%
```

读法：`100/100` 对应 **50.0000%**（**不是纯 DFA**——因为配比是 DFA 与原料的质量比，DFA 占 `a/(a+100)`），`10/100` 对应 `9.0909%`。这就是 Q5 外推边界该写「≤ 50% DFA 质量分数」而不是「≤ 100%」的依据。

### 8.4 骨架槽位计数（§4 的来源）

```python
import re, pathlib
t = pathlib.Path(r"E:\数学建模\PRACTICE_2023B\main.tex").read_text(encoding="utf-8")
print("placeholders", len(re.findall(r"<<[^>]*>>", t)))
print("decimals", re.findall(r"\b\d+\.\d+\b", t))
print("Q-sections", re.findall(r"\\section\{Question[^}]*\}", t))
for pat in [r"\\begin\{figure\}", r"\\includegraphics", r"\\begin\{table\}", r"\\cite\{", r"\\lstinputlisting"]:
    print(pat, len(re.findall(pat, t)))
```

实测输出（照抄，8 行）：

```
placeholders 69
decimals []
Q-sections ['\\section{Question 1: <<What it does>>}', '\\section{Question 2: <<What it does>>}']
\\begin\{figure\} 0
\\includegraphics 0
\\begin\{table\} 1
\\cite\{ 0
\\lstinputlisting 1
```

读法：69 个占位符、0 个小数、只有 Question 1 与 Question 2 两个节、0 个 figure、0 个 includegraphics、1 个 table、0 个 cite、1 个 lstinputlisting（在 main.tex:104 被注释掉）。

### 8.5 两种口径的对照 + 撤回「两个分母」指控的依据（§7.2 的来源）

这一条同时干两件事：① 证明上游 `out/00-problem.md` §7.1 的四个 2σ 用的是**单一**口径（撤回本报告初稿的指控）；② 给出 12 格在两种口径下的完整判定，定位唯一翻转格。

```python
import pandas as pd
D = r"E:\数学建模\PRACTICE_2023B\data"
a1 = pd.read_excel(D + r"\Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx", header=None)

def parse_I(df):
    out = {}
    for name, hdr in [("DFA/CS",1), ("DFA/CE",9), ("DFA/LG",16)]:
        ratios = [str(v) for v in df.iloc[hdr].tolist()[1:] if str(v) != "nan"]
        prods  = [str(v) for v in df.iloc[hdr+1:hdr+5, 0].tolist()]
        out[name] = {"ratios": ratios,
                     "data": {p.replace(" yield",""): {r: float(df.iloc[hdr+1+i][1+j]) for j, r in enumerate(ratios)}
                              for i, p in enumerate(prods)}}
    return out

I = parse_I(a1)

# ① 撤回依据：上游四个 2σ 逐个对 0.10*max(两端点) 验证（不靠 argmin 猜，直接列三种分母）
up = {"Tar": 1.95, "Water": 3.10, "Char": 2.99, "Syngas": 2.70}
for p in ["Tar","Water","Char","Syngas"]:
    v = I["DFA/CS"]["data"][p]; rs = I["DFA/CS"]["ratios"]
    first, last = v[rs[0]], v[rs[-1]]
    mean = sum(v[r] for r in rs)/len(rs)
    mx = 0.10*max(first, last)
    print(f"{p:7s} up={up[p]:.2f} | 0.1*first={0.1*first:.3f} 0.1*last={0.1*last:.3f} "
          f"0.1*mean={0.1*mean:.3f} 0.1*max_endpoint={mx:.3f} "
          f"err_max_endpoint={abs(mx-up[p]):.4f}")
# 期望：err_max_endpoint 全 <= 0.004 -> 上游口径单一，指控撤回
# 注意：Tar 的 max 端点是 0/100（19.46 > 12.13），其余三项 max 端点是 100/100

# ② 12 格 × 两口径
for k in ["DFA/CS","DFA/CE","DFA/LG"]:
    v = I[k]["data"]; rs = I[k]["ratios"]
    for p in ["Tar","Water","Char","Syngas"]:
        s = v[p]; vals = [s[r] for r in rs]
        A_eff = abs(s[rs[-1]] - s[rs[0]]); A_thr = 0.10*max(s[rs[0]], s[rs[-1]])
        A = "SIG" if A_eff > A_thr else "n.s."
        B_eff = max(vals) - min(vals); B_thr = 0.10*(sum(vals)/len(vals))
        B = "SIG" if B_eff > B_thr else "n.s."
        print(f"{k:7s}{p:8s} A[{A_thr:6.2f} vs {A_eff:6.2f} -> {A:4s}] "
              f"B[{B_thr:6.2f} vs {B_eff:6.2f} -> {B:4s}] {'same' if A==B else '*** DIFFER ***'}")
# 期望：唯一 DIFFER = DFA/CS Syngas
```

**本报告实测输出（逐字，2026-11-19 17:19 现场重跑）**：

```
Tar     up=1.95 | 0.1*first=1.946 0.1*last=1.213 0.1*mean=1.455 0.1*max_endpoint=1.946 err_max_endpoint=0.0040
Water   up=3.10 | 0.1*first=2.684 0.1*last=3.102 0.1*mean=2.891 0.1*max_endpoint=3.102 err_max_endpoint=0.0020
Char    up=2.99 | 0.1*first=2.921 0.1*last=2.987 0.1*mean=2.938 0.1*max_endpoint=2.987 err_max_endpoint=0.0030
Syngas  up=2.70 | 0.1*first=2.449 0.1*last=2.698 0.1*mean=2.716 0.1*max_endpoint=2.698 err_max_endpoint=0.0020
DFA/CS Tar      A[  1.95 vs   7.33 -> SIG ] B[  1.45 vs   7.33 -> SIG ] same
DFA/CS Water    A[  3.10 vs   4.18 -> SIG ] B[  2.89 vs   4.18 -> SIG ] same
DFA/CS Char     A[  2.99 vs   0.66 -> n.s.] B[  2.94 vs   0.76 -> n.s.] same
DFA/CS Syngas   A[  2.70 vs   2.49 -> n.s.] B[  2.72 vs   3.96 -> SIG ] *** DIFFER ***
DFA/CE Tar      A[  4.53 vs  10.86 -> SIG ] B[  4.21 vs  10.86 -> SIG ] same
DFA/CE Water    A[  2.74 vs  11.28 -> SIG ] B[  1.93 vs  11.28 -> SIG ] same
DFA/CE Char     A[  2.46 vs   3.18 -> SIG ] B[  2.41 vs   3.48 -> SIG ] same
DFA/CE Syngas   A[  1.67 vs   2.76 -> SIG ] B[  1.46 vs   3.98 -> SIG ] same
DFA/LG Tar      A[  1.81 vs   9.87 -> SIG ] B[  1.13 vs   9.87 -> SIG ] same
DFA/LG Water    A[  2.37 vs   8.39 -> SIG ] B[  2.04 vs   8.39 -> SIG ] same
DFA/LG Char     A[  5.82 vs   0.74 -> n.s.] B[  5.73 vs   1.19 -> n.s.] same
DFA/LG Syngas   A[  1.07 vs   2.22 -> SIG ] B[  1.09 vs   3.41 -> SIG ] same
```

即：**四项的 `err_max_endpoint` 全 ≤ 0.004，上游没有混用分母；12 格里唯一翻转的是 `DFA/CS Syngas`。**

> 口径 A 的一个附带限制，必须一并写出：它只在**有 `0/100` 基线**的组合上严格成立（本题只有 DFA/CS）。对 DFA/CE、DFA/LG 而言首端点是 `10/100`，「端点差」退化成 `|100/100 − 10/100|`，与「相对于空白对照的增量」不是同一个量。上表仍列出它们的 A 列，只是为了让 12 格可对照，**不能据此声称 CE/LG 有催化增量**（见 §7.3 第 1 条）。

### 8.6 Annex I 里的公式行（§5.5 派生量表的来源）

读公式而不是读值：`data_only=False` 才能看到 `=100-C3-C4-C5` 这样的单元格。

```python
import openpyxl
D = r"E:\数学建模\PRACTICE_2023B\data"
f1 = D + r"\Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx"
f2 = D + r"\Annex II-Pyrolysis Gas Yields of Three Pyrolysis Combinations.xlsx"
for tag, path, hdrs in [("Annex I", f1, [1,9,16]), ("Annex II", f2, [0,9,17])]:
    ws = openpyxl.load_workbook(path, data_only=False).worksheets[0]
    n = sum(1 for hdr in hdrs for row in ws.iter_rows(min_row=hdr+2, max_row=hdr+5)
              for c in row if isinstance(c.value, str) and c.value.startswith("="))
    print(tag, "formula cells:", n)
ws = openpyxl.load_workbook(f1, data_only=False).worksheets[0]
for r in range(1, 26):
    fs = [ws.cell(row=r, column=c).value for c in range(2, 11)]
    fsn = [x for x in fs if isinstance(x, str) and x.startswith("=")]
    if fsn:
        print(f"  row {r} label={ws.cell(row=r,column=1).value!r} "
              f"formulas={len(fsn)}/{len(fs)} sample={fsn[0]}")
```

实测输出（照抄）：

```
Annex I formula cells: 24
Annex II formula cells: 0
  row 6 label='Syngas yield' formulas=8/9 sample==100-C3-C4-C5
  row 13 label='Char yield' formulas=8/9 sample==100-B11-B12-B14
  row 18 label='Tar yield' formulas=8/9 sample==100-B19-B20-B21
```

`8/9` 的分母是 9 个配比列（`0/100` 到 `100/100`），分子是其中 8 个公式格。`row 6`（DFA/CS 的 Syngas）那一格非公式的硬值是 `24.49`，正是 `0/100` 空白对照——Syngas 在无脱硫灰时是实测值，其余 8 格由 `=100 − Tar − Water − Char` 派生。`row 13` 与 `row 18`（CE 的 Char、LG 的 Tar）的 `0/100` 格为空（CE/LG 没有空白对照），所以同样是 8 个公式格、8 个有效值。**三个组合合计 24 个公式格，Annex II 一个都没有。**

---

## 9 返修清单（按「不修就必然扣分」排序）

| 优先级 | 事项 | 依据 | 落点 |
|---|---|---|---|
| P0 | **补 Q3/Q4/Q5 三个 `\section`**，或把 5 问合并成 3 章并在章内明确标 `(3)(4)(5)` | `problem.txt` L100/L104/L107 vs main.tex 仅 :54/:63 | main.tex 骨架 |
| P0 | **摘要模板的 3 个槽改成 5 个**（`<<task 1..5>>`、`<<Q1..Q5 model>>`、`<<Q1..Q5 number>>`） | main.tex:14/:16-17/:19-20 硬编码 3 | main.tex:13–20 |
| P0 | **加图环境**：Q2 明令 `by making corresponding images`（L99），当前 0 个 figure | L96–99 | 新增 ≥3 组图（3 组合分面） |
| P0 | **Q1/Q3 判定表**：12 格 / 57 格（产物 32 + 气体 25），带 2σ 阈值与 q 值 | L93–94 / L101 | 新增 2 张表（当前仅 1 张 1 行表） |
| P0 | **在正文首次出现配比的地方声明档位实况**：Annex II 只有 `{0,20,40,50,80,100}`(CS) 与 `{20,40,50,80,100}`(CE/LG)，题面 L68–75 的 10/30/60 三档在气体数据里不存在 | §5.2 附件实测 | Q2 首段 + 图注 |
| P1 | **符号表从 1 行扩到 ≥10 行**：Tar/Water/Char/Syngas/σ/配比/DFA 质量分数/H2…C4H10 | main.tex:53 | `Notations` |
| P1 | **假设补到 ≥5 条**：同一温度（L145–146）、5% 作 σ（L76–77）、CE 命名裁决（L38 vs 脚注 r29）、四产物闭合（实测和=100.0）、外推边界 50% DFA | main.tex:47–48 仅 2 槽 | `Assumptions` |
| P1 | **Q2 只画实际存在的档位**：气体 CE/LG 仅 5 档、CS 仅 6 档；10/30/60 不得出现 | 附件实测（§5.2） | Q2 图注 |
| P1 | **Q1 必须写「Char 不显著」**：CS span 0.76 < 2σ 2.94；LG span 1.19 < 2σ 5.73 | 本报告 §6.1 | Q1 结论 |
| P2 | **多重比较**：12 / 19 / 32 / 25 个检验给 BH-q 或明写「未校正，故只作保守筛」 | §7.1（FWER 0.4596 / 0.6226 / 0.8063 / 0.7226，合计 57 格 0.9463） | Q1/Q2/Q3 表注 |
| P2 | **声明 σ 的口径并全篇统一**：路径取 `τ_single` / `τ_diff`（骨架 C）/ 端点 A / 全序列 B；若 Q1 与 Q3 用不同路径须分别标注。**实测：A 与 C 在 Q3 的 57 格里 55 格同判、2 格翻转**（产物 `Water @ 30/100`、气体 `CO @ 20/100`；`τ_diff/τ_max = √(1+(min/max)²)` ∈ [1, 1.41]，本题 Water/Syngas 差 20%–37% 仍多数不改判定）；Q1 里会翻转的是 `DFA/CS Syngas`（A：2.49<2.70 不显著；B：3.96>2.72 显著）。另须声明舍入规则：`Water @ 20/100` 在 `τ_diff` 下余量仅 0.00085 | §7.2（Q1 12 格中 1 格翻转；Q3 57 格中 2 格翻转、另有 2 格压在线上） | 符号表 + 全部判定表 |
| P2 | **Q5 三件套**：点 + 区间 + 外推边界（≤50.0000% DFA） | L107–111 | 新增 Q5 节 |
| P2 | **Q4 不得给 Ea 数值**，只能给 k_app 或引文献标 `[文献值]` | L145–146 | 新增 Q4 节 |
| P3 | **附录列全 `code/` 的全部脚本**（评审期间从 4 个增长到 **12 个 `*.py`**：`check_no_peek.py` 3083 B / `fetch_annex.py` 30061 B / `model_skeleton.py` 19720 B / `solve.py` 23518 B / `numlib.py` 3860 B / `fix_bytes.py` 1665 B / `gen_appendix.py` 1735 B / `check_md.py` 2564 B / `verify_numbers.py` 2402 B，另有 6 个 `_probe_*.py` 探针） | main.tex:104 被注释；BUILD.md「listing 数 ≥ 脚本数」 | `Appendix A` |
| P3 | **`code/verify_numbers.py` 补 claim**：当前仍是 0 claims / 0 ranges，R-V06 判未通过（`data/results_q1..q5.json` 已落盘，claim 有素材可绑） | §4 | code/ |

---

## 10 结论

1. **题面身份必须先纠正**：本论文的题面是 `problem\problem.txt`（2023 数维杯 B 题·棉秆热解催化），不是 `APMCM-PROBLEMS\PROBLEMS\2023_B.txt`（2023 APMCM B 题·玻璃温室小气候）。整条 APMCM 语料（35 份）与 C1–C12 判据只能当体裁惯例，不能当本题判分条款。**§1**
2. **兑现程度：23 条要求，0 条兑现。** `main.tex` 106 行、69 个占位符、0 个小数、0 个图、1 张 1 行表、2 条假设、1 行符号。不是「写得不好」，是**正文不存在**（`main.pdf` 在整棵树里 0 个）。**§2 §4**
3. **骨架与题面不同构**：5 个子问只给了 2 个 `\section`，摘要模板硬编码「3 个问题 / 3 个模型 / 3 个结果」。即使填满占位符，Q3/Q4/Q5 仍无交付位置，摘要仍会自报 3 问。**§4**
4. **四类高频类别里，本题真正漏的是「给数据」与「预测」，不是「政策建议」**：政策建议在本题 0 命中（不构成漏项）；给数据 19/35 是硬要求但论文 `Annex` 0 命中；预测 13/35 对应 Q5 且无落点，且**不是时序**。要求具体数值 13/35 被正则漏检（`significant` 承载），本报告已把 12 格 + 57 格判定算好。**§3 §6**
5. **两条最容易整条漏掉的，都查了**：① 描述性约束 6 条已逐条给出「谁对」（最硬的是 L68–75 八档 vs 附件气体仅 5–6 档、L145–146 单温度 ⇒ Ea 不可辨识、四产物闭合实测和恒为 100.0，且 Annex I 有 24 个 `=100−其余三项` 的公式格，即 CS 的 Syngas / CE 的 Char / LG 的 Tar 在附件层面就是派生量）；② 可执行交付物落在 Q1/Q3 的 `significant` 二值判定与 Q5 的三件套上，本报告给出了阈值与全部数值。**§5 §6**
6. **两类可复算缺陷已定位**：① 多重比较未校正——k=12/19/32/25/57，FWER = 0.4596 / 0.6226 / 0.8063 / 0.7226 / 0.9463，而 `main.tex` 里 `Bonferroni`/`BH`/`p-value` 各 0 命中；② **口径混用**——本题的 `significant` 判定存在**三种**各自自洽的口径（A 端点 `0.10·max` / B 全序列 `0.10·mean`+span / C 骨架的 `τ_single`+`τ_diff`）。实测：**A 与 C 在 Q3 的 57 格里 55 格同判、2 格翻转**（产物 `Water @ 30/100`、气体 `CO @ 20/100`；`τ_diff/τ_max = √(1+(min/max)²)`，两值相等时高 41%、悬殊时趋同），**Q1 里会翻转的是 `DFA/CS Syngas` 一格**（A：端点差 2.49 < 2σ 2.70 判不显著；B：全序列极差 3.96 > 2σ 2.72 判显著，因 Syngas 在 50/100 处有峰值 28.45 而非单调）。另有一格压在线上：`Water @ 20/100`（CE=21.37、LG=18.54），`|d| = 2.8300`、`τ_diff = 2.8291`，**比值 1.0003，余量只有 0.00085**——在 `τ_diff` 下是「勉强显著」，在 `0.10·max` 下（τ=2.14）是 `1.32` 的舒适显著。这一格的正负号不由物理决定，而由**你在第三位小数上怎么舍入**决定。论文不声明路径，这类格结论不可复算。**§7.1 §7.2**
   > 两条自查更正：① 本报告初稿曾指控上游 `out/00-problem.md` §7.1「同一张表混用两个分母」，**经复算不成立、已撤回**（上游四个 2σ 全部吻合 `0.10 × 两端点最大值`，误差 ≤ 0.004）；② 本报告第二稿曾推断「上游 Q3 用的是 `τ_diff` 等价形式」，**同样不成立、已弃用**（上游 Q3 四组阈值区间只吻合 `0.10·max`，`τ_diff` 全部偏高）。两次都是「结论碰巧一致 ≠ 公式相同」。依据见 §7.2 与 §8.5。
7. **图表刻度无法判定**：`figures/` 0 文件、`\includegraphics` 0 处、无 PDF，`mmkit.figfont` BLOCKED-BY-ABSENCE。**不得记为通过。** **§7.4**

VERDICT: FAIL
