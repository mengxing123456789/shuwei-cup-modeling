# 31 — AsterLink 获奖论文对标与我们（SWC2026_C）的差距清单

> 语料：`C:\Users\29900\Downloads\AsterLink`（只读）。解压临时目录 `C:\Users\29900\AppData\Local\Temp\aster\_tmp` 已清理。
> 我们：`E:\数学建模\_swc2026\SWC2026_C\main.tex`（1,796 行）+ `main.pdf`（38 页，正文 25 + 附录 13）。
> 机读数据：`_aster_corpus_stats.json`（124 篇逐篇统计）。
>
> **统计口径**：页数=PyMuPDF `page_count`；字符数=`get_text("text")` 全量；标题优先取 PDF 大纲（`get_toc()`，≥6 条且一级≥3 时用），否则按「字号≥正文×1.02 + 编号样式 `N.`/`一、`/`第N章`/`N.M`」扫描行级 span（正文号=全篇字符最多的字号）；图/表=题注行 `图|Fig|表|Table N` 去重计数；公式=行尾 `(N)` 编号去重；参考文献=`参考文献`/`References` 之后 `\[\d+\]` 行数；附录起点=大纲或正文首行出现 `附录/Appendix` 且页码在后半部；关键词标志=全文正则（95%CI= `95%`/`置信区间`/`confidence interval`）。

---

## §1 清点表

- **可解析 PDF 共 134 份**：赛题/模板/流程类 10 份 + **参赛论文 124 篇**。
- **无一篇扫描件**：124 篇的最低「每页字符数」也有 1,061（判定线 <500/页）；全部可作结构样本。
- 年份分布：2019=22, 2020=15, 2021=16, 2022=17, 2023=18, 2024=15, 2025=21（2025 文件名 `XSHUWEICUP25…`，按 `25→2025` 归年）。
- 题号分布：A=36, B=33, C=31（+2 个小写 `c2019…` 归 C，共 33）, D=22。
- 页数分布（全部 124 篇）：20–29 页=40, 30–39=46, 40–49=14, 50+=24；**中位数 35 页，正文（除附录）中位数 25 页**。
- 附录检出 95 篇（大纲含 `Appendix/附录` 49 篇 + 后半部首行命中 46 篇）；中位附录长度 **11 页**（2024-25 为 18.5 页）；29 篇完全无附录标记。

## §2 抽样深读（16 篇；C 题 12 + 近年 8，交集不重复计）

| 论文 | 骨架（一级标题序列，简写） | 关键观察 |
|---|---|---|
| C2024110930663 (2024C, 25p) | Intro → Assumptions+Notations → ModelⅠ TVF-EMD → ModelⅡ SA → ModelⅢ BDSK-SA → Sensitivity → Strengths/Weakness → Conclusion | **8 节整、每问一个 Model 节**；fig 18/tab 6/eq 30/ref 9；摘要 15 个数字；无附录。最干净的对标样板，篇幅与我们正文完全相同（25p） |
| C2024101629647 (2024C, 32p) | Intro → Problem analysis → Assumptions+Symbols → Methods and Modeling（每问三级展开）→ Conclusion → Appendix | eq 40、fig 12；**模型统一收进一节 "Methods"，每问是三级子目**；ref 16 |
| C2024092929266 (2024C, 46p) | Intro → Problem analysis → Symbol+Assumptions → Model → Test the Models → Sensitivity → S&W → Refs → Appendix(20p) | fig 12/tab 5/eq 20；**有 CI、p 值、误差棒**；附录 20 页放代码与诊断 |
| C2022111514190 (2022C, 46p) | Intro → Problem analysis → Symbol+Assumptions → Model → Model eval & optimisation → Refs → App | fig **27**/tab 10；图密度全场最高之一；含 baseline + complexity |
| C2022110513494 (2022C, 39p) | Intro → Problem analysis → Assumptions → Data preprocessing → **一问一节**（5 问各一节）→ Refs → App | 五问骨架；ref 18；单位、复杂度齐全 |
| C202111046833 (2021C, 28p) | Raising+restate → Problem analysis → Assumptions → Symbol → Model → 优缺点分析 → Refs → App | eq 20/ref 11；有 95%CI + 误差棒；早期年份的完整模板 |
| C201986768 (2019C, 31p) | Intro → Problem analysis → Symbol+Assumptions → Model → Test the Models → Sensitivity → Refs → App | tab 8/ref 15；有 p 值；**2019 年就配齐 假设/检验/灵敏度 三节** |
| CSHUWEICUP2556711 (2025C, 52p) | Intro → Problem analysis → Symbol+Assumptions → Model(4.1–4.5 每问子目) → Sensitivity → Refs | **图 15 + 表 24 + eq 87 + 伪代码 + CV + p 值 + CI**，唯一全齐的样本；ref 只 5 |
| CSHUWEICUP2559001 (2025C, 39p) | Intro → Problem analysis → Symbol+Assumptions → Data preprocessing → Model → … | 图只 2 张但表 8；eq=0（全用编号行文公式） |
| CSHUWEICUP2551760 (2025C, 92p) | Restatement → Problem Analysis(每问一段) → Assumptions → Symbol Legend → **每问一节** → Model Analysis and Testing → Evaluation → Refs → 4 个代码附录 | 17 个一级节；92 页是把 4 段 Python 全量贴进正文附录 |
| CSHUWEICUP2561635 (2025C, 68p) | Intro → Assumptions+Notation → 每问一节 → Refs → Appendix(38p) | 附录占 55%；eq 36 |
| CSHUWEICUP2556821 (2025C, 199p) | Intro → Problem analysis → Symbol+Assumptions → Model → … → Appendix | fig 34；**199 页是全场最长——超长不等于好评，见 §5** |
| B2024100129342 (2024B, 51p) | Problem analysis → Symbol+Assumptions → Model establishment and solution → Refs | 标题层浅但 fig 17；无附录检出 |
| D2024091329034 (2024D, 43p) | Introduce → Research ideas → Assumptions → Notations → Data preprocessing → 每 Task 一节 → Test → Eval → Refs → App | tab 17；**有 Research ideas（技术路线）专节 + CV** |
| ASHUWEICUP2534291 (2025A, 83p) | Intro → Problem analysis → Symbol+Assumptions → Model → Test → Sensitivity → S&W → Conclusion → App | 83 页但 body=25：附录 58 页全代码/图表 |
| BSHUWEICUP2549835 (2025B, 104p) | 标准 8 节 + 中文六段附录 | 104 页；附录是"统计信息/诊断/病害分布"报告书 |

**跨样本骨架规律（124 篇的众数结构）**：
`Introduction → Problem analysis → Symbol and Assumptions → Model（或每问一节）→ Test the Models / Sensitivity → Strengths and Weakness → Conclusion → References → Appendix`。
出现率：显式假设节 **98%**、灵敏度/敏感性 **52%（2024-25 达 78%）**、Strengths&Weakness（=局限节）**50%（2024-25 达 81%）**、独立检验节 39%、符号说明节 28%（更多篇把它并入 Assumptions 节）。**算法编号框全场仅 5/124** —— 不用 Algorithm 环境是常态，"模型/求解"写进正文即可。

## §3 多维度对比表（我们 vs 获奖中位数/众数）

| 维度 | 我们（实测） | 全部 124 篇中位数 | C 题 33 篇中位数 | 2024-25 中位数 | 差值/判定 |
|---|---|---|---|---|---|
| 正文页数 | **24**（p3–25，正文页眉标 "Page N of 25"） | 25 | 25 | 30 | 达线（C 题一致），比 2024-25 少 6p |
| 附录页数 | **13**（p26–38） | 11（95 篇检出附录者中位） | 11 | 18.5 | 相当偏短 |
| 一级节数 | **8** | 9 | 8 | 9 | 持平 |
| 二级节数 | **32** | 20 | 20 | 19.5 | **+12（偏多，碎）** |
| 图数（题注） | **7**（另 p38 有 1 张总览图=8） | 11 | 8 | 14.5 | **−4 至 −7** |
| 表数（题注） | **20** | 4 | 5 | 5 | **+15（远超众数）** |
| 算法编号框 | 0 | 0 | 0 | 0 | 持平（全场都不用） |
| 编号公式 | **4**（另若干 displaymath 无编号） | 6 | 5 | 24.5 | **近年中位远超我们（24.5 vs 4）** |
| 参考文献 | **9** | 7 | 9 | 6.5 | 达标 |
| 显式假设节 | **无独立节**（散见 3 处行内 "Assumptions"） | 有（98%） | 有（100%） | 有（100%） | **缺** |
| 符号表节 | 无专节（附录 A 有 Notation 表） | 28% 有 | 18% 有 | 42% 有 | 弱项但非必需 |
| 灵敏度/稳健性节 | **无专节**（仅 6 次行内词） | 52% 有 | 58% 有 | **78%/86%** | **缺——近两年已成标配** |
| 局限/S&W 节 | **有**（§7.1 Limitations） | 50% 有 | 42% 有 | 81% 有 | 已有 |
| 检验节 | **有**（每问 Validation 小节） | 39% 有 | 39% 有 | 61% 有 | 已有（优于中位） |
| 95% 置信区间 | **有**（Table 12 + 39 处 interval） | 23% 有 | 27% 有 | 22% 有 | **已有（优于 3/4 获奖稿）** |
| 摘要含具体数字 | **45 个数字**（AUC/AP/ARI/Brier/±） | 中位 14 | 11 | 16 | **远超（约 3×）** |
| 引言给三问三答 | **有**（§1.2 + Table 1 三问结论先行） | ≈0% 显式 | 0% | 0% | **独特点（别人用 Problem analysis 而非三问三答）** |
| p 值/假设检验 | 无 | 31% | 27% | 33% | 缺（非必需） |
| RMSE 类误差指标 | **有** | 98% | 97% | 92% | 达标 |
| 交叉验证 | 无显式 CV（用 held-out seeds/records） | 12% | 15% | 19% | 弱 |
| baseline 对比 | **有**（deliberately simple baseline + GRU） | 18% | 30% | 47% | **已有** |
| 误差棒/± | **有** | 58% | 64% | 81% | 已有 |
| 复杂度声明 | **无** | 37% | 45% | 47% | **缺** |
| 技术路线图/框架图 | p38 有 1 张 | 多数有 | 多数有 | 多数有 | 有但位置偏后（放正文更好） |

## §4 可执行差距清单（≥12 条，按「评奖影响 ÷ 成本」排序）

| # | 他们有的 X，我们没有 | 补它要什么（落点） | 预计成本/页 |
|---|---|---|---|
| 1 | **独立 "Sensitivity Analysis" 专节**（2024-25 获奖率 78%；C 题 58%；我们 0 节，仅 6 处行内词） | 在 §6 与 §7 之间插一节 `Sensitivity and robustness`：把已算好的「三个 case × 三个 service multiplier」Brier 表、ARI 对聚类超参的重扫、GRU 1.38cm 的换窗重训各抽一张小图/小表。数据全在 `data/*.json`，无新实验 | **+0.5–1 页正文**（从 §3–§5 各压 0.2p 换得）；成本=写 1 节 + 移 2 张图 |
| 2 | **独立 "Assumptions" 专节**（100% C 题有；我们只有行内碎片） | 新节放在 §2 之前或并入 §2 开头：把我们散在 §3.1/§4.1/§5.1 的 7 处假设（qualified≠ground truth、official split 16/4/4、三格式坐标差异、缺失机制 MAR 近似、Brier 阈值预设等）集中编号列出 | **+0.4 页**；零实验 |
| 3 | **模型复杂度声明**（C 题 45%、2024-25 47%；我们 0 处） | 每问 "Solution" 小节尾加一行：`cost = O(N·C)` / `O(T·w)` / `O(K·J)` 与实测秒数（code 目录的计时日志已有） | **+3 行**；零实验 |
| 4 | **图数补到 14 左右**（2024-25 中位 14.5；我们 7） | 从附录把 3–4 张已存在的图（p38 总览框架图、P3 policy 对比图、ARI 曲线、时长分布图）移到正文对应节；再加 1 张「技术路线图」放 §1.4 | **净正文图 +4–5 张**；图已存在，只是挪位置 |
| 5 | **"Strengths and Weakness" 标题对齐**（81% 2024-25 用此名；我们叫 "Limitations and failure conditions"，评委扫目录时认不出这是 S&W） | §7.1 改题 `Strengths and weaknesses` 或 `Model evaluation: strengths and limits` | **改 1 个标题** |
| 6 | **编号公式补到 ~10**（2024-25 中位 24.5；我们 4） | 把 P3 闭式（due−s−β)/α、Brier 定义、ARI 定义、conformal 分位数、logistic 校准式、GRU 窗口记号改挂编号；现在已是 displaymath 只是没编 | **+6 个编号**；零实验 |
| 7 | **二级节瘦身**（我们 32 vs 中位 20；每问 8 个子节太碎） | §3–§5 每问把 "Results" 与 "Summary" 合并、"Model" 与 "Solution" 留其一；预计砍 6–8 个二级节 | **−0.5 页**（节标题空行本身占版面） |
| 8 | **"Problem analysis / 三问怎么串" 更醒目**（获奖稿 100% 有 "Problem analysis" 节；我们藏在 §1.2） | §1.2 改名为 `Problem analysis: the three questions and how they connect`，Table 1 保留——评委熟悉的词 + 我们的独家三问三答 | **改 1 个标题** |
| 9 | **"Test the Models / Model evaluation" 有图有表**（获奖稿该节都配诊断图；我们 §7 只有文字+Table 16） | 把 Appendix D 的「三闸未达标项」画成一张小表+一张雷达/条形图放 §7 | **+0.3 页** |
| 10 | **伪代码/算法框 0**（全场仅 4% 用，**这一条不学**，但见 §5） | 不用补 | 0 |
| 11 | **p 值缺失**（33% 2024-25 有；我们 0） | P1 的 AUC 0.596/0.627 与 baseline 0.0189 的差、P3 0.8667 vs 0.8153 的差，都能补一个 bootstrap p；code 里已有 bootstrap 框架 | **+2 行数字**；成本=跑 1 个脚本（已有数据） |
| 12 | **参考文献补到 12+ 且含同题近三年文献**（我们 9，C 题中位 9，但强稿 C2024101629647=16、CSHUWEICUP2551760=12） | 补 3 条：conformal 综述（已有 Vovk 可再引 Angelopoulos）、missing-data 综述（Little&Rubin 已有，可加 Emmanuel）、scheduling 综述 | **+3 条 bibitem** |
| 13 | **"Model Evaluation" 放在结论前**（我们 §7 已在，对齐 ✔） | 无改动 | 0 |
| 14 | **附录标签"AI 使用报告"显性化**（官方合规；获奖稿无此节但我们必须有） | 附录 E 已存在；把目录里 "Appendix E" 改名 `Appendix E: AI tool usage report` 让评委一眼看到 | **改 1 个标题** |
| 15 | **正文页数别超 25 也别短于 22**（C 题中位正文 25；我们 24，留 1 页余量给 #1/#2 后仍 ≤25） | 执行 #1 时同步把 §3.5/§4.3 的长表压缩 | 净 0 页 |

## §5 反面教材（获奖稿里的坏做法，我们不该学）

| 坏做法 | 实例 | 为什么不该学 |
|---|---|---|
| **无附录标记 → 附录混进正文/全篇冗长** | 29/124 完全无 Appendix 标；CSHUWEICUP2556821 199 页、ASHUWEICUP2535346 359 页 | 超长是排版灾难不是加分项；评审读不完。我们 25+13（附录页眉改 "Appendix, p.N"）比它们更像 "完整论文" |
| **只报最好结果、无对比** | 82% 无 baseline 词；18% 有 baseline 也多为口头 | 我们 P3 0.8667 vs 0.8153 是**带对照**的，这是我们的真实优势，别退化 |
| **无置信区间/误差棒** | 77% 无 95%CI；19% 无 ±/std | 我们有 39 处 interval + ±0.0316，是全场前 23% |
| **"Symbol and Assumptions" 合并但假设只有 2 行** | 多数 2024-25 稿 | 假设只写"忽略 X、假设 Y"是形式化凑数；我们的假设要编号且每条挂到正文使用位置 |
| **参考文献 <5 或 >15 个但无近三年** | CSHUWEICUP2556711 只 5 条（52 页）；多篇 0 条 | 文献太少显得没调研；我们 9 条够了，补到 12 即可 |
| **把完整代码贴正文附录** | CSHUWEICUP2551760 把 4 段 Python 原样贴进 92 页 | 评委不看代码；放节选+路径即可（我们已经这么做了，附录 13 页适度） |
| **表格无单位** | 抽样中 8/16 缺 units_table | 我们单位在正文叙述里，表格列头可再补 |
| **"Strengths and Weakness" 空泛化** | 几乎每篇该节都写 "模型可进一步改进" | 我们的 §7.1 写的是**失效条件**（什么时候不准），这是对的，别改回套话 |
| **问题分析只有一句 "我们分三步"** | 多数稿 Problem analysis 只 0.3 页 | 我们的 §1.2 + Table 1 三问三答比这个强，保留 |

## §6 一句话总结

**我们现在的结构最像 2024 年 C 题 `C2024110930663`**（同样 25 页正文、8–9 节、按问题分 Model 节、图多表少、结论前收 Sensitivity+S&W）；差在它的 **Sensitivity 专节、假设专节、复杂度声明、近年的图密度（14.5 vs 我们 7）** 上——而它没有的 95%CI、三问三答、P3 对照实验我们反而已经具备。**若把 §4 的 #1/#2/#3/#4 补齐（≈1.5 页净增），我们就不是"对标"而是"该届中上"的骨架。**

---

### 附件 A：抽样 16 篇标题明细（机读，节选自 `_aster_corpus_stats.json`）

- **C2024110930663**（2024C, 25p, body25）：1.Introduction / 2.Assumptions and Notations / 3.ModelⅠ TVF-EMD / 4.ModelⅡ SA / 5.ModelⅢ BDSK-SA / 6.Sensitivity Analysis / 7.Strengths and Weakness / 8.Conclusion / Refs｜fig18 tab6 eq30 ref9 abs#15
- **C2024101629647**（2024C, 32p）：Introduction / Problem analysis / Assumptions+Symbols / Methods and Modeling / Conclusion / Refs / Appendix｜fig12 eq40 ref16
- **C2024092929266**（2024C, 46p）：Introduction / Problem analysis / Symbol+Assumptions / Model / Test the Models / Sensitivity / S&W / Refs / Appendix(20p)｜fig12 eq20
- **C2022111514190**（2022C, 46p）：Introduction / Problem analysis / Symbol+Assumptions / Model / Model eval+optimisation / Refs / App｜fig27 tab10 eq18 ref10
- **C2022110513494**（2022C, 39p）：Introduction / Problem analysis / Assumptions / Data preprocessing / 一问一节×5 / Refs / App｜ref18
- **C202111046833**（2021C, 28p）：Raising+restate / Problem analysis / Assumptions / Symbol / Model / 优缺点 / Refs / App｜eq20 ref11 含CI
- **C201986768**（2019C, 31p）：Introduction / Problem analysis / Symbol+Assumptions / Model / Test / Sensitivity / Refs / App｜tab8 ref15 含p值
- **CSHUWEICUP2556711**（2025C, 52p）：Introduction / Problem analysis / Symbol+Assumptions / Model(4.1–4.5) / Sensitivity / Refs｜fig15 tab24 eq87 含CI+p+CV+伪代码
- **CSHUWEICUP2559001**（2025C, 39p）：Introduction / Problem analysis / Symbol+Assumptions / Data preprocessing / Model｜tab8 eq0(行文公式)
- **CSHUWEICUP2551760**（2025C, 92p）：Restatement / Problem Analysis / Assumptions / Symbol Legend / 每问一节×5 / Model Analysis+Testing / Eval / Refs / 4×Code｜fig8 tab11 eq24 ref12 含CI
- **CSHUWEICUP2561635**（2025C, 68p）：Introduction / Assumptions+Notation / 每问一节×5 / Refs / Appendix(38p)｜eq36
- **CSHUWEICUP2556821**（2025C, 199p）：Introduction / Problem analysis / Symbol+Assumptions / Model / … / Appendix｜fig34——超长反例
- **B2024100129342**（2024B, 51p）：Problem analysis / Symbol+Assumptions / Model establishment / Refs｜fig17
- **D2024091329034**（2024D, 43p）：Introduce / Research ideas / Assumptions / Notations / Data preprocessing / Task×4 / Test / Eval / Refs / App｜tab17 含CV
- **ASHUWEICUP2534291**（2025A, 83p）：标准 8 节 + 附录(58p)｜fig21 eq44 含p值
- **BSHUWEICUP2549835**（2025B, 104p）：标准 8 节 + 中文附录六段｜fig24 eq54

### 附件 B：我们的实测明细

- `main.tex`：1,796 行 / 99.8KB；`\section` 8、`\subsection` 32、`table` 20（`tabular` 20）、`figure` 7（`includegraphics` 8）、`equation/align` 4、`algorithm` 0、`bibitem` 9、`thebibliography` 1、`\appendix` 0（用独立页眉宏实现，正文末页 p25）。
- `main.pdf`：38 页；p26 起页眉改 `Appendix, p.N`；附录 A=Notation 表（p26）、B=代码节选（p27–31）、C=运行步骤（p30–32）、D=预声明判分表（p34）、E=AI 使用报告（≈p32–33）、"试过但被拒"清单（p37）、总览图（p38）。
- 摘要页数字计数：45（AUC 0.596/0.627、AP 0.0407 vs 0.0189、ARI 0.414→0.5487、Brier 0.0365/skill 0.644/0.0397、0.8667/0.8063 vs 0.8153/0.7406、0.0517±0.0316、8000 jobs、16/4/4、69 记录/24 环境/66070 帧/5.834GB 等）。
- CI 证据：`Table 12`（"Paired same-seed differences … with 95% intervals"）+ 摘要 "±0.0316"。
