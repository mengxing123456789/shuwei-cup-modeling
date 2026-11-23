BYTES 59225
# 07 图表审读：六范式与误用

被测件（历史审读记录）：`E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\main.pdf`（当时的 5 图 74 页稿，印刷页码 "Page n of 72"）。注：本报告是那一轮的图表审读证据，其中列出的缺陷已在本轮修订中逐条处理；当前交付稿为 111 页 / 6 图 / "Page n of 109"，以 `main.tex` 与 `review/00-metrics.md` 为准。
审读对象：全文 5 张图（`figures/fig0_framework.pdf` … `figures/fig4_p2_voi.pdf`），Q3 章 0 张图。
本报告只判"图"，不判模型对错；凡与 `review\00-metrics.md` 冲突处两列并列。

---

## 0. 机器口径（动手读图之前先跑，原文粘贴）

### 0.1 review_check.py — 12 条官方硬项

```
> cd E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP
> & "E:\Mini\envs\mathmodel\python.exe" "E:\数学建模\.agents\skills\mathmodeling\scripts\review_check.py" .

paper: .
pdf: main.pdf   pages: 74
[ OK ] C4    p1 has summary/abstract=True
[ OK ] C4    p2 has contents/directory=False
[ OK ] C5    header lines matched=72
[ OK ] C5    headers leaking identity=0
[ OK ] C7    chinese chars in body=0 (appendix, not judged=0)
[ OK ] C6    total pages=74
[ OK ] C9    appendix=True code=True
[ OK ] C11   placeholder team number hits=0
[ OK ] C11   self-declared invalid identifier in body=0
[ OK ] C11   has References section=True
[ OK ] C8    reference type markers=8

VERDICT: PASS  (fail=0 unknown=0)
```

与 `00-metrics.md:18-32` 逐字一致（唯一差别是第一行：我传的目录参数是 `.`，基线传的是绝对路径，故基线印 `paper: E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP` 而我印 `paper: .`；判据行完全相同）。注：`[ OK ] C4 p2 has contents/directory=False` 是 C4 的目录项判据，值为 False（次页无目录）；该项判 OK 是因为 C4 只要求首页有摘要，目录缺失在本判据下不扣分 —— 这条留给 `01-compliance` 判，本报告不重复。

### 0.2 gauntlet_check.py — R 系列 16 项

```
> cd E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP
> & "E:\Mini\envs\mathmodel\python.exe" "E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py" .

[band] benchmark: E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\refs\official_standard.json  n=48  median sections=8.5
[PASS] paper resolved                      E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP
[PASS] R-V01 body <= 30 pages              body=18 (header numerator of first Appendix A page)
[PASS] R-V02 single denominator            distinct totals=1
[PASS] R-V02 numbers contiguous            header numerators form 1..n with no gaps
[PASS] R-V03 zero CJK in body              body cjk=0 (appendix, not judged=0)
[PASS] R-V04 zero 'university'             hits=0
[PASS] R-V05 team number filled            KNOWN OPEN: \baominghao placeholders must be filled before submission
[PASS] R-W06 no unsupported phrases        no 众所周知/显而易见/obviously,
[PASS] R-W11 front matter order            ['summary', 'contents']
[PASS] R-W04 references have type markers  8 type markers on 8 entries
[PASS] R-W04 >=70% references cited        cite calls=8, [n] uses before bibliography=0, entries=8
[PASS] R-V06 verify_numbers present        claims=51 exit=0
[PASS] R-V09 no stale artefact             KNOWN OPEN (explain each): 1 pair(s): data\alt_p3.json<-code\make_alt_p3_md.py(0.03h)
[PASS] R-V07 band measured on both sides   figures/equations non-zero, so project was read from PDF text
[PASS] R-V07 out-of-band count             ABOVE=['words', 'abstract_numbers', 'abstract_density', 'distinct_numbers', 'pct_mentions', 'sections'] BELOW=['abstract_words']
[PASS] R-V14 figure text >= 6 pt           min=4.73 pt median=7.97 pt violations=0 single-char<6pt=6 (measured by python.exe)

16/16 PASS
pdftotext: security risk: running with elevated privileges
```

两处如实说明：

1. R-W06 行里的中文在**我的** PowerShell 控制台按 GBK 解码成了乱码，上表按 `00-metrics.md:46` 的原文转录；判据本身 PASS，与基线一致。
2. 本次运行 shell 报 `[exit code: 1]`：`pdftotext: security risk: running with elevated privileges` 这一行落到 stderr，被 PowerShell 当成 NativeCommandError 抬成非零退出。**同一行 stderr 在基线的 `00-metrics.md:57` 也出现，而基线记 `exit=0`** —— 差别在采集环境（基线由 `run_review.py` 捕获输出、不经 PowerShell 的 NativeCommandError 判定），不在判据。16 条 `[PASS]` 与 `16/16 PASS` 逐字相同，故本报告的机器口径与基线一致，此差异不影响任何结论。

### 0.3 mmkit.figfont — 图内有效字号

`mmkit` 不在 `E:\Mini\envs\mathmodel` 里，需先设 `PYTHONPATH`（模块实际位于
`E:\数学建模\.agents\skills\mathmodeling\scripts\mmkit`）。不设会直接 `ModuleNotFoundError`。

```
> $env:PYTHONPATH="E:\数学建模\.agents\skills\mathmodeling\scripts"
> & "E:\Mini\envs\mathmodel\python.exe" -m mmkit.figfont main.pdf

pdf: main.pdf
  spans=20883  min=4.73 pt  median=7.97 pt
  violations (>= 3 chars and < 6.0 pt): 0
  single-character spans below 6.0 pt (not judged): 6
  PASS
```

与 `00-metrics.md:63-67` 逐字一致（第一行路径写法不同：我传相对名 `main.pdf`，基线传绝对路径；`spans` / `min` / `median` / `violations` / `single-character` / `PASS` 六项完全相同）。

### 0.4 与 `00-metrics.md` 的对账

| 项 | 00-metrics.md（17:41:02 生成） | 我在 2026-11-21 18:03 重跑 | 一致？ |
|---|---|---|---|
| review_check VERDICT | PASS (fail=0 unknown=0) | PASS (fail=0 unknown=0) | 一致 |
| main.pdf 页数 | 74 | 74 | 一致 |
| main.pdf mtime / sha256 前 8 | 17:40:29 / 378EED5F | **17:53:40 / 928F68CB** | **不一致，见 §0.5** |
| main.pdf 字节 | 594009 | 594009 | 一致 |
| gauntlet | 16/16 PASS | 16/16 PASS | 一致 |
| R-V14 min / median | 4.73 / 7.97 pt | 4.73 / 7.97 pt | 一致 |
| R-V14 violations | 0 | 0 | 一致 |
| R-V14 single-char<6pt | 6 | 6 | 一致 |
| R-V06 claims | 51 exit=0 | 51 exit=0（判据值；shell 因 stderr 报 exit 1） | 值一致 |
| R-V09 KNOWN OPEN | 1 pair `data\alt_p3.json<-code\make_alt_p3_md.py(0.03h)` | 同 | 一致 |

十项里九项一致，唯一的差异是 main.pdf 的编译时间戳与整包摘要（字节数、页数、图页位置全同），两列并列于 §0.5。**R-V14 的 `min=4.73` 与图内实测的 4.34 pt 是两个口径，不是矛盾**，见 §3.0。

### 0.5 被测件与数据层同代核对（R-V11：报告是快照）

`00-metrics.md:9` 记录的被测件是 **17:40:29 / sha256 378EED5F** 的 main.pdf；我在 18:03 复核时磁盘上的 main.pdf 已是 **17:53:40 / sha256 928F68CB**（同样 594009 B、同样 74 页、同样 5 张图、同样 5 条 caption 文字，main.tex 未改，mtime 与 sha 均仍为 17:33:45 / E72C9500）。按 R-V11 两列并列：

| 产物 | 00-metrics.md | 我在 2026-11-21 18:03 重测 | 是否影响本报告结论 |
|---|---|---|---|
| main.pdf mtime | 17:40:29 | **17:53:40**（晚 13 min，重编译） | 否 |
| main.pdf sha256 前 8 | 378EED5F | **928F68CB** | 否 |
| main.pdf 字节 / 页数 | 594009 / 74 | 594009 / 74 | 否 |
| 五张图所在 PDF 页 | 4 / 10 / 10 / 14 / 15 | 4 / 10 / 10 / 14 / 15 | 否 |
| 五条 caption 文字 | — | 与 main.tex:41-46、153-158、164-168、272-276、282-286 一致 | 否 |
| main.tex | 17:33:45 / E72C9500 | 17:33:45 / E72C9500 | 否 |

**结论：页数、字节、图页位置、caption 文字、四条机器判据全部不变，只有编译时间戳与整包摘要变了。** 故本报告所有判断对两个版本同时成立；凡下文引用"PDF 页码"处，均指这两个版本共有的 4/10/10/14/15 页。

数据层时间线（2026-11-21，均为实测 mtime）：

| 产物 | mtime | 字节 | sha256 前 8 |
|---|---|---|---|
| data/alt_p2.json | 15:43:51 | 18432 | — |
| data/alt_p1.json | 16:33:16 | 744740 | — |
| figures/fig0_framework.pdf | 17:18:49 | 20174 | 8BE71EF1 |
| figures/fig1_p1_agreement.pdf | 17:18:50 | 18268 | A374766A |
| figures/fig2_p1_reliability.pdf | 17:18:50 | 22052 | F4B07835 |
| figures/fig3_p2_error.pdf | 17:18:50 | 17525 | 378C5E5D |
| figures/fig4_p2_voi.pdf | 17:18:51 | 15102 | 4BA378FA |
| data/alt_p3.json | 17:26:02 | 257695 | — |
| data/results_swc2026.json | 17:30:56 | 1164274 | — |
| main.pdf | 17:53:40 | 594009 | 928F68CB |

结论：**main.pdf 比所有 data/*.json 都新**，不存在"被测件落后 N 小时"。但两件事必须写明：

1. `figures/*.pdf`（17:18:49–17:18:51）比 `data/alt_p3.json`（17:26:02）早 7 分钟、比 `data/results_swc2026.json`（17:30:56）早 12 分钟。核对 `code/alt_figures.py` 的读取清单：五张图只读 `alt_p1.json`（16:33:16）与 `alt_p2.json`（15:43:51），两者分别早于图 45 min 与 95 min，**不绘 alt_p3 / results_swc2026 的任何数**，因此图不是旧数据的产物，无需"落后 N 小时"警告。
2. `figures/` 目录 mtime 16:28:28 是目录元数据，不代表文件内容时间（文件 mtime 17:18 才是真值），不据此判陈旧。

---

## 1. 六范式覆盖：用了 2 个，缺 4 个

判据：任务给定的六范式。命中要求"图的形式"符合该范式，而非题面出现关键词。

| # | 范式 | 本论文用了吗 | 落点 | 缺口说明 |
|---|---|---|---|---|
| P1 | 情景对比分组柱 | ✅ 用了 | 图2(a)(b)（`fig1_p1_agreement.pdf`） | 两个 panel 都是分组柱；但 (a) 的横轴是有序数值被当类别轴，(b) 混绝对/相对两种口径 |
| P2 | 敏感性龙卷风与秩漂移 | ❌ 缺 | 只有 `tab:p1sens`（main.tex:175-191，8 行表） | 无龙卷风图、无秩漂移图。7 个配置的 F1@0.5s 极差 0.136→0.183；做成龙卷风一眼可见 sigma 的条形比 hazard 长（见 §3.7） |
| P3 | Laffer 与 Pareto | ❌ 缺 | 无；图5 是最接近的（代价-误差前沿）但无拐点标记 | 图5 画的是 A/B/C 三个离散选项，不是前沿曲线；break-even 只以文字出现，未画竖线/切点 |
| P4 | 雷达 | ❌ 缺 | 无 | Q3 有 3 case × 5 policy × 4 metric（main.tex:329-352）天然适合雷达（每个 policy 一条闭合多边形，4 根轴），却只有表 |
| P5 | 热力图 | ❌ 缺 | 无 | 同上 3×5 网格 + 4 指标，正是热力图的标准形态；`tab:p3` 是纯表 |
| P6 | 流程图 | ✅ 用了 | 图1（`fig0_framework.pdf`） | 唯一一张流程图，但 caption 宣称的结构图中没画（见 §3.1） |

**另有 2 张图不属于六范式**：图4（误差-参数折线）、图5（散点+虚线）。它们本身不是缺陷，但意味着六范式里 4 个空缺不是"用别的形式替代了"，而是**根本没做**。

### 1.1 缺范式是不是缺陷？——用真题基线说话，不凭印象

在 22 篇一等奖抽取文本（`E:\数学建模\APMCM-PROBLEMS\_award_text\*.txt`）上做正则计数（脚本 `out\_figcheck\award_figref.py`，结果落 `E:\数学建模\APMCM-PROBLEMS\_award_figref.json`）：

| 范式关键词 | 命中篇数 / 22 | 命中次数 | 命中的论文（括号内为次数） |
|---|---|---|---|
| heatmap / 热力 | 6 | 16 | 2022C(3)、2024B(1)、2024C(3)、2025A(1)、2025C(1)、B题00536(7) |
| （heatmap 复算口径） | — | — | 正则须用 `heat\s*map\|heatmap\|热力\|热图`（`heat map` 中间有空格，窄式 `heatmap` 会漏掉 2022C 的 3 处）；该式在 22 篇上命中 **7 篇 17 处**，其中 `C题02422.txt` 的 1 处是"量子退火…利用热力学中的**热波动**"，属误命中，剔除后即上行的 **6 篇 16 处**。脚本 `out\_figcheck\award_figref.py` 只出图引用数，热力图/范式计数由本行正则单独复算 |
| pareto / 帕累托 | 5 | 44 | 2022B(24)、2024B(5)、2025B(8)、2025C(2)、A题02838(5) |
| contour / 等高线 | 3 | 16 | — |
| radar / 雷达 | 1 | 1 | 2025年C题优秀论文.txt |
| laffer | 1 | 8 | 2025年C题优秀论文.txt |
| tornado / 龙卷风 | 0 | 0 | — |
| waterfall / 瀑布 | 0 | 0 | — |
| sankey / 桑基 | 0 | 0 | — |

据此：

- **热力图**：6/22 一等奖用过，是可核的常见做法 → 缺它是**实际失分点**，[判断] 理由链：Q3 的 3×5 网格有 4 个指标，表格读"哪格最好"要逐行扫，热力图一眼可读；6/22 的基线说明评审见过这种形式。
- **Pareto**：5/22 用过，且 `2022年B题优秀论文.txt:1628` "Figure 12 Pareto optimality schematic."、`:1660` "3. Pareto optimality search, as shown in Figure 12…" —— 一等奖把前沿画成图并在正文指认。本论文图5 有前沿的实质（代价 vs 误差）却没画成前沿、没标拐点。
- **Laffer**：1/22（`2025年C题优秀论文.txt`），且该篇 line 57 "pinpointing the Optimal Tariff Rate at ≈30%"、line 1700 "Figure 7.5 confirms the Laffer Curve effect:" —— **峰值/拐点在正文里点名**。本论文没有 Laffer 型对象，P3 的"Laffer 半边"NOT-APPLICABLE（理由：全文无"税率-收入"型倒 U 目标函数，`data/*.json` 中无任何先升后降的单峰收益曲线），但 Pareto 半边适用。
- **雷达**：1/22，弱基线 → 缺雷达记为**建议项而非缺陷**。
- **龙卷风/秩漂移**：0/22 → 不能说"一等奖都画龙卷风"。但敏感性本身有官方落点：`_official_evidence.json` 的 `sensitivity` aspect（35 篇中 8 篇具备，含 2026_A/B/C），其 why 字段为"官方评审七条里明写'模型的稳定性验证'；题面明示时缺失即硬扣分"，对应 R-V07。**本论文敏感性只以表出现、只扫 2 个参数、且表只印有利的三列**（见 §3.7）—— 缺图是形式问题，**只印有利的一半是内容问题**，后者更重。

### 1.2 关于官方判据的可引用范围（先说清，免得后面每条都要重复）

对 `E:\数学建模\APMCM-PROBLEMS\_rules_text\*.txt` 全部 16 份（2017–2026）做 grep，与图/chart/图 相关的条款**只有一族**，即 C6/C7 的同一句 "…the chart, etc. (The main body of the solution paper should be controlled within 30 pages…)"，出现在 2017:77、2018:81、2019:81、2020:81、2021:69、2022:69、2023:69、2023.5:59。

- 其中 **C7 明确把"图（the chart）"纳入"不得出现中文"的范围**（`2018_APMCM_Essay_format_and_submission_specifications.txt:79,81`；`2017_...:75`）。这是本报告唯一一条**可官方引用**的图内文字判据，且实测通过：五张图 cjk=0（§3.8）。
- **C6** 只约束正文字号 "the size of font is usually 11 or 12"（`2018_...:77`）与 30 页上限（`:83`），**不约束图内字号**。
- 官方 16 份文本里**没有任何**关于 caption 自解释、误差带、轴刻度、拐点标记、图数量的条款。因此本报告除 C7 与 C6 字号上下文外，每一条范式/误用判断都标 **[判断]** 并给理由链，不冒充官方要求。
- C12（AI 声明）在 2026 扫描件 p3–p6 **不存在**，故全文不引用 C12。

---

## 2. 逐图判读表（主表）

列义：**图号** = 论文中的 Figure 编号（含 PDF 页 / 印刷页）；**范式** = 六范式之一或"非六范式"；**误用类型** = 可复算的具体错法；**改法** = 改 caption 够不够，还是必须重画。

| 图号 | 范式 | 误用类型 | 改法（改 caption 还是重画） |
|---|---|---|---|
| **图1** `fig0_framework.pdf`<br>PDF p4 / 印刷 p2<br>main.tex:39-48 | 流程图（P6） | ① **caption 宣称两条跨问链接，图中 0 条箭头**：Q 列 x 200–290、h>20 pt 的曲线数 = 0；链接只以 6.20 pt 脚注文字存在（y 149.2–156.5）。② 4 种填色（蓝/橙/绿/灰）**无图例，caption 不提颜色**，而填色覆盖 10 个框中的 9 个。③ 框内计数 `3 archives / 69 records / 66,070 frames`、`349 annotated segments` 是**硬编码字符串**（alt_figures.py:106-107），与 alt_p1.json 数值相同但未读 JSON，违反同文件 :4 自述。④ 全文 **0 处 `\ref{fig:framework}`**，正文无一句指向本图。 | **重画**（补 Q1→Q2、Q1→Q3 两条箭头 + 填色图例）+ **改 caption**（删 "the two cross-question links are…" 或改为 "the footnote names…"）+ 正文补引用 |
| **图2(a)** `fig1_p1_agreement.pdf`<br>PDF p10 / 印刷 p8<br>main.tex:151-160 | 情景对比分组柱（P1） | ① **有序数值当等距类别轴**：±0.2/±0.5/±2.0/±5.0 s 的刻度中心 x = 58.74/101.89/145.05/188.20 pt，页间距 43.153/43.153/43.153 pt（极差 **0.000**），而标签数值间距 0.3/1.5/3.0 s（max/min = **10.0×**）。斜率/面积读数无意义。② **无误差带**：全图 0 条 whisker（§4.1）。③ 只画 F1 不画 P/R，而两种检测器的 n_pred 不同（399 vs 276），同一个 F1 含义不同（§3.2）。④ ±0.2 s 与 ±5.0 s 两处柱高差 1.02 / 1.23 pt，小于一条 1.5 pt 线宽。 | **重画**（真数值轴或对数轴 + CI + 补 P/R 子图）+ **改 caption**（补 n=280 边界 / n=349 段、补 399 vs 276 两个预测数） |
| **图2(b)** 同上 | 情景对比分组柱（P1） | ① **基线三元组硬编码**：`b2 = [0.542, 0.593, 0.762]`（alt_figures.py:171），而 alt_p1.json 里 `coverage.baseline.tol_zero/0.2s/half_segment` = 0.5415473/0.5931232/0.7621777 存在 —— **这组数没有产物键读入路径**，是缺陷本身。② **三种容差混两类口径**：0 s（绝对）、±0.2 s（绝对）、half-segment（**每段相对**）放在同一类别轴上，x = 297.0/342.1/387.8，间距 45.07/45.73 pt。③ caption 未给 panel (b) 的 n=349。④ 红色脚注 x 135.9–281.0 **落在 (a) 的 x 区间下方**（两 frame 均止于 y 106.0），被读成 (a) 的注，而 1.14/0.79 是整检测器量。 | **重画**（读 JSON、把 half-segment 单独标注或换轴）+ **改 caption**（写明三种容差口径不同、n=349、1.14/0.79 属整图） |
| **图3** `fig2_p1_reliability.pdf`<br>PDF p10 / 印刷 p8<br>main.tex:162-170 | 情景对比分组柱（P1，嵌套柱） | ① **长度诚实、面积撒谎**：width/value = 169.824（AUC）与 169.824（F1），同一线性标尺；但外柱面积 1921.9 pt²、内柱 493.8 pt²，**面积比 0.2569**，而值比 F1/AUC = **0.6681** —— 按墨水量积分会把 F1 读成 AUC 的 0.257，**低估 61.5 %**。② **x 轴跑到度量上界之外**：0→1.0 占 169.82 pt，frame 到 x1=351.98 = 值 **1.300**，30 % 的面板宽度是算术上不可能的数据。③ **无 CI 让 0.00112 变成"结果"**：Hanley–McNeil（n1=51, n0=298）给 0.91367→CI[0.860,0.968]、0.91479→CI[0.861,0.969]，差 0.00112 = 一个 CI 宽的 1.0 %。④ **只画有利的一半**：main.tex:150 自陈段级组内 LOO AUC = **0.076**（低于随机、方向相反），图里 0.914/0.915 两根在、0.076 不在。⑤ 标题 "(a)" 无 (b)。 | **重画**（分组柱 + 每柱 CI；补 0.076 与组内 0.5648 两根"组内"参照柱；x 轴收到 1.0）+ **改 caption**（写明 n=51/349、CI 方法、两根 0.91 不可区分） |
| **图4** `fig3_p2_error.pdf`<br>PDF p14 / 印刷 p12<br>main.tex:270-278 | 非六范式（误差-参数折线） | ① **无误差带**，而同表 `rmse_cm`（3.526/6.862/8.742/11.334）与 `p90_cm`（5.646/11.237/14.097/18.743）就在 alt_p2.json 里，画一条带零成本。② **caption 的 "never worse than holding the last state" 图承载不了**：L=1.0 s 时 9.464 vs 9.554 差 0.090 cm；y 轴 0–20 占 82.78 pt → 4.139 pt/cm，故差 **0.37 pt**，小于默认线宽 1.5 pt。③ 标注 "×1.0" 实为 1.018（1.8 %），与其余 ×1.4/×1.6/×2.3 并列时被读作同类。④ **只画 4 个基线中的 3 个**：`linear`（3.31/6.342/10.329/18.003）从未入图。⑤ 标题 "(a)" 无 (b)。 | **重画**（加 rmse/p90 误差带 + 补 linear 基线 + 对 L=1.0 做内嵌放大）+ **改 caption**（把 "never worse" 改成 "within 0.9 % of holding, indistinguishable at this scale"；写明 ×2.3 的分母是 Kalman 的 mean_cm） |
| **图5** `fig4_p2_voi.pdf`<br>PDF p15 / 印刷 p13<br>main.tex:280-288 | Laffer/Pareto（P3，最接近但未成范式） | ① **y 轴截断到数据自身范围的 59 %**：轴 9–14 占 91.10 pt，数据 9.874–12.809 = 53.47 pt，**零点在可见底边下方 1.8 个轴高**。② **虚线连 A→C 跳过被支配的 B**：唯一长斜段 (98.0,54.8)→(336.4,100.4) 正是 A 的标记到 C 的标记，而 caption 自己说 "the value of information is a step function: buy none or buy both"（main.tex:284-285）——**图与 caption 互相否认**。③ caption 称虚线连 "the two interior points of the frontier"，但 **A 与 C 是两个端点**，B 才是内点。④ **无拐点标记**：break-even（1158.006 cm²/单位 ≈ 1.608 cm RMSE）只在文字里。⑤ **三个点 n 不等**：Table 7 caption（main.tex:259）说 "evaluated on the same windows"，但 A `n_windows=221`、B/C `n_windows=300`。 | **重画**（去 A→C 虚线或改阶梯线；加 break-even 竖线；y 轴从 0 起或加断轴符号）+ **改 caption**（删 "interior points"；写明 A 用 221 窗、B/C 用 300 窗，不可直接横比） |
| **（缺）** Q3 章 | 雷达（P4）/ 热力图（P5） | Q3 有 3 case × 5 policy × 4 metric（`tab:p3`, main.tex:329-352），**一张图都没有**；热力图基线 6/22 一等奖用过。 | **补图**（5×3 热力图，4 指标 4 个 panel；或 5 条雷达） |
| **（缺）** 敏感性 | 龙卷风与秩漂移（P2） | 敏感性只有 `tab:p1sens`（main.tex:175-191），**只印有利的三列**：8 行其实只有 7 个配置；选中格在已印的 Count MAE / F1@0.5s / F1@2s 上是第 2/1/1 名，**未印的 F1@5s 上是第 2 名**（最好的是 hazard=2 的 0.65896）；正文 main.tex:365 把 sigma 的摆幅 0.046 记在 hazard 名下；merge threshold 与 drop fraction **根本没扫**（`min_seg_s`/`map_drop` 在 8 个 JSON 里各只出现 2 次且是同一个值 —— `alt_p1.json:/config` 与 `results_swc2026.json:/alt_p1/config` 是镜像，去重后 1 个值、0 条 sweep；对照 `hazard_lambda_s` 12 次、`sigma_s` 8 次）。 | **补图 + 补算**（龙卷风：每参数 ±1 档对 3 指标的摆幅；秩漂移：7 配置排序是否翻转）+ **改正文**（0.046 的归属、删未测的 merge/drop 断言） |

---

## 3. 逐图证据

### 3.0 先说字号：两个口径，不是矛盾

`mmkit.figfont` 报 `min=4.73 pt`（在 main.pdf 页面上量），我直接量 `figures/*.pdf` 得最小 4.34 pt。两者都对，差一个**缩放因子**：

| 图 | 图内字号 (pt) | 页面字号 (pt) | 比值 |
|---|---|---|---|
| fig0 | 6.00 / 6.20 | 6.53 / 6.75 | 1.0883 / 1.0887 |
| fig1 | 4.90 / 6.20 / 6.60 / 7.00 / 7.40 | 5.34 / 6.75 / 7.19 / 7.62 / 8.06 | 1.0898 |
| fig2 | 4.34 / 6.20 / 6.60 / 7.00 / 7.40 | 4.73 / 6.75 / 7.19 / 7.62 / 8.06 | 1.0899 |
| fig3 | 6.20 / 6.60 / 7.00 / 7.40 | 6.75 / 7.19 / 7.62 / 8.06 | 1.0887 |
| fig4 | 4.34 / 6.20 / 6.60 / 7.00 / 7.40 | 4.73 / 6.75 / 7.19 / 7.62 / 8.06 | 1.0899 |

即 `\includegraphics[width=1.0\linewidth]` 实际把图放大了 **1.0889×**。实测（`out\_figcheck\scale_ratio.py`，对**同一张图的图内 PDF 与它在页面上的落位**取同一规则 —— 全部 drawing rect 的并集宽度 —— 再相除，故不受画布留白影响）：五张图的图内 ink 宽一律 **416.55 pt**（等于其 canvas 宽），页面落位 ink 宽一律 **453.56 pt**，比值 **1.0889**，与上表字号比值 1.0883–1.0899 逐位吻合。成因：`main.log` 记 `\textwidth=455.24411pt`，而实测落位 453.56 pt（差 1.68 pt），二者都大于图的 416.55 pt，于是 `width=1.0\linewidth` 把图**拉大**而非缩小。`code/alt_figures.py:5-7` 的注释写 "at the exact text width (5.7854 in = 416.55 pt) so the scale factor in the paper is exactly 1.0"，**该假设与实际排版不符**：脚本按 1.0 设计字号，排版又乘了 1.089。这解释了为什么设计时 6.0 pt 的框内文字印出来是 6.53 pt、设计时 4.34 pt 的 `$F_1$` 下标印出来是 4.73 pt。**报告一律以页面字号为准**，那是评审真看到的。

页面最小 4.73 pt 是 `$F_1$` 的下标 "1"（fig2 四处、fig1 一处 → 5.34 pt）与 `cm$^2$` 的上标 "2"（fig4 一处）。机制：matplotlib mathtext 下标 = 父字号 × 0.7，6.20×0.7 = 4.34、7.00×0.7 = 4.90，乘 1.089 得 4.73 与 5.34。

**这 6 个 span 恰好都是单字符**，所以 figfont 的 ">= 3 chars and < 6.0 pt" 过滤器全部放过（`violations=0`）。结论：**R-V14 的 PASS 是真的，但"图内有效字号全部 ≥ 6 pt"是假的** —— 每一个 F₁ 的下标、每一个 cm² 的上标，印出来只有 4.7–5.3 pt，比 6 pt 门槛低 12–21 %，而任何自动检查都抓不到。这是本报告唯一一条"机器说 PASS 而人必须推翻"的项。

C6 的官方文字只规定正文 "the size of font is usually 11 or 12"（`2018_APMCM_Essay_format_and_submission_specifications.txt:77`）与 30 页上限（`:83`），**没有**关于图内字号的门槛；6 pt 是本次评审的既定阈值（`gauntlet_check.py` R-V14 用它），属行业惯例值。故此处标 **[判断]**，理由链：(a) 官方只约束正文字号，不约束图内；(b) 4.73 pt 在 100 % 缩放的 PDF 上肉眼可读性差；(c) 这几个字符是**下标/上标里的数字**，恰是"F1 还是 F2""cm 还是 cm²"的判别位 —— 读者辨错就误解了度量。

### 3.1 图1：caption 画了一张图里没有的图

`fig0_framework.pdf` 几何（`out\_figcheck\fig0_anatomy.py`、`fig0_curves.py`）：

- 11 个填充形状 = 1 个白页 rect + **10 个框**；5 种填色：蓝 (0.933,0.953,0.98)×2、橙 (0.992,0.949,0.914)×2、绿 (0.918,0.98,0.945)×3、灰 (0.957,0.965,0.969)×3、白 ×1。
- 48 条曲线 = **40 个箭头**（每条 ≤ 6 pt）+ 8 条大曲线：6 条 9.2–15.0 pt 水平短接、2 条 13.5×4.9 与 13.5×5.4 的肘形弧（x 193.4→207.0，即第二列到第三列的入口）。
- **跨问链接的检验**：Q1→Q3 或 Q1→Q2 的箭头应落在 x 200–290、h>20 pt。**计数 = 0**。Q 列三个框 y0 = 33/65/97、h = 25，间隙只有 7 pt，物理上放不下箭头。
- 那两条链接**只以文字存在**：`ax.text(0.5, 0.02, "cross-question links: Q1 variance -> Q2 process noise;  Q1 reliability -> Q3 reservation", ...)`（alt_figures.py:127-130），印在 y 149.2–156.5、6.20 pt。

而 caption（main.tex:44-46）写 "**The two cross-question links are** the Q1 posterior variance, which enters Q2 as process noise, and the Q1 reliability, which enters Q3 as the reservation floor." —— 读者按 caption 去找箭头，图里没有。这不是措辞问题，是**图与说明指称不同对象**。★ 这条同时违反本报告判"自解释"的第一项：caption 描述的结构在图中不存在，读者无法核对。

另：四种填色无图例、caption 不提颜色 → 颜色在语义上无用（读者无法知道绿=问题、灰=输出）。这不是"少个图例"的小事：填色覆盖 10 个框中的 9 个，是全图最大的视觉变量，却零信息。

计数硬编码：`box(0.08, 2.80, 1.90, 1.05, "3 archives\n69 records\n66,070 frames", ...)` 与 `"349 annotated\nsegments + bad\nframe labels"`（alt_figures.py:106-107），数值与 `data\alt_p1.json` 的 `data.n_records=69`、`data.n_frames=66070`、`data.n_segments=349` **完全一致**，但它们是字面量，不是读来的。文件头 docstring（alt_figures.py:4）写 "Every plotted number is read from the JSON of record; nothing is typed." —— **自述与代码不符**。数值今天没错，但这是"下次重跑数据变了图不会变"的结构性隐患。

正文引用：`out\_figcheck\refcount.py` 对 main.tex 计数 —— `\ref{fig:` **0 次**、`\bFig\.` **0 次**、`Figure~` **0 次**、裸词 `\bFigure` **0 次**（连 caption 正文里都不出现；PDF 上的 "Figure 1" 是 LaTeX 自动加的前缀，不是作者写的字）；而 `\label{fig:` 有 **5 个**（fig:framework / p1agree / p1rel / p2err / p2voi），`\ref{tab:` **7 次**（tab:p1scale:97、p1f1:132、p1sens:173、p2alpha:223、p2mask:223、p2voi:256、p1sens:365）。即：**5 个图标签全部写了却一个都没被引用**，而 7 个表引用全都有对应标签 —— 作者知道怎么引用，只是没引用图。PDF 文本层扫描同样只在五条 caption 前缀里见到 "Figure N"。**5 张图全部无正文锚点。**

这条要不要判缺陷，用基线说话（`out\_figcheck\award_figref.py`）：22 篇一等奖里 **16 篇在正文指认过自己的图**（合计 94 处 in-text pointer），**6 篇为 0**（2022C、2022E、2023B、2023C、2024D、2025D）。所以 16/22 是多数做法，本论文落在 6/22 的少数侧 —— **[判断]** 定性为"强调不足的缺陷，不是致命项"，理由链：多数一等奖这么做；且本文 5 张图承担的是核心结论（图3 是 Q1 的主结果、图4 是 Q2 的主结果），不指认等于让评审自己找。

### 3.2 图2(a)：有序变量被摊成等距类别

刻度标签中心实测（`out\_figcheck\fig_axes.py` + `fig_numbers.py` C1）：

| 标签 | 中心 x (pt) | 页间距 (pt) | 标签数值 (s) | 数值间距 (s) |
|---|---|---|---|---|
| ±0.2 s | 58.74 | — | 0.2 | — |
| ±0.5 s | 101.89 | 43.153 | 0.5 | 0.3 |
| ±2.0 s | 145.05 | 43.153 | 2.0 | 1.5 |
| ±5.0 s | 188.20 | 43.153 | 5.0 | 3.0 |

页间距极差 **0.000 pt**，数值间距 max/min = 3.0/0.3 = **10.0×**。容差（秒）是有序、有比率的量，却被画成四个等距类别。后果：

1. 曲线的"斜率"没有意义 —— 0.5 s 到 2.0 s 的 1.5 s 与 2.0 s 到 5.0 s 的 3.0 s 画成等长，视觉上"变好变快"被抹平。
2. 读者会以为四个容差等距抽样，而实际是 0.2/0.5/2/5（近似几何级数 2.5×/4×/2.5×）。

同一面板的 ylim 0–0.80（frame y 33.9–106.0，高 72.1 pt → **90.1 pt/单位**）。实测柱高（`get_drawings()` 取 `re` 项，蓝=BOCPD、橙=threshold）：

| 容差 | BOCPD 柱高 (pt) | 基线柱高 (pt) | 高差 (pt) | 高差占 1.5 pt 线宽 |
|---|---|---|---|---|
| ±0.2 s | 9.02 | 10.04 | **1.02** | 0.68× |
| ±0.5 s | 16.44 | 19.76 | 3.32 | 2.21× |
| ±2.0 s | 52.25 | 49.56 | 2.69 | 1.79× |
| ±5.0 s | 58.88 | 57.65 | **1.23** | 0.82× |

折算校验：斜率 (58.88−9.02)/(0.65−0.10) = **90.65 pt/单位**，与轴高推算的 90.1 一致（差 0.6 %），说明柱高确为线性、零起点。

读法：±0.2 s 与 ±5.0 s 两处高差 **1.02 / 1.23 pt**，都小于一条 1.5 pt 线宽 —— 肉眼不可辨；而柱上印了两位小数，读者读的是数字不是柱。**印数字弥补了刻度缺陷**，但柱高本身在撒谎（看起来一样高），且这四个"看起来的差"没有一个能判显著（无 CI）。

**F1 单值掩盖了方向相反的两件事**（`out\_figcheck\fig1_pr.py`）。micro-F1 = 2·TP/(n_pred + n_true)，两种检测器的 n_pred 不同（BOCPD 399、基线 276），n_true 固定 280，故同一个 F1 含义不同。反解得：

| 容差 | 方法 | n_pred | F1 | TP | precision | recall |
|---|---|---|---|---|---|---|
| ±0.2 s | BOCPD | 399 | 0.10015 | 34 | 0.0852 | **0.1214** |
| ±0.2 s | 基线 | 276 | 0.11151 | 31 | 0.1123 | 0.1107 |
| ±0.5 s | BOCPD | 399 | 0.18262 | 62 | 0.1554 | **0.2214** |
| ±0.5 s | 基线 | 276 | 0.21942 | 61 | 0.2210 | 0.2179 |
| ±2.0 s | BOCPD | 399 | 0.58027 | 197 | 0.4937 | **0.7036** |
| ±2.0 s | 基线 | 276 | 0.55036 | 153 | 0.5543 | 0.5464 |
| ±5.0 s | BOCPD | 399 | 0.65390 | 222 | 0.5564 | **0.7929** |
| ±5.0 s | 基线 | 276 | 0.64029 | 178 | 0.6449 | 0.6357 |

**BOCPD 的 recall 在四个容差上全部高于基线**（+0.0107/+0.0036/+0.1571/+0.1571），precision 在四个容差上全部低于基线（−0.0271/−0.0656/−0.0606/−0.0885）。也就是说 caption 里那句 "the fixed-threshold baseline is better at strict tolerance" 严格说是**F1 意义上的更好，而召回上 BOCPD 反而略高**：±0.2 s 的 F1 劣势（−0.0114）几乎全部由 precision 造成，而 precision 低是因为它报了 399 个边界（基线 276）。图只画 F1 一根柱，读者无法知道"更好"是哪种更好 —— 这正是"是否自解释"判据下的实质缺陷：[判断] 理由链 = 该图的结论（loose 赢、strict 输）完全由 F1 这一标量承载，而同一份 JSON 里 precision/recall 都在，画出 P/R 双柱即可让"用过度分割换召回"一眼可见；不画等于把方法差异藏进一个合成标量。

### 3.3 图2(b)：硬编码 + 混口径 + 脚注错位

- **硬编码**：`b2 = [0.542, 0.593, 0.762]`（`code\alt_figures.py:171`）。JSON 里 `coverage.baseline.tol_zero=0.5415473`、`tol_0.2s=0.5931232`、`tol_half_segment=0.7621777`。按任务契约"印出来的数必须能被别人复算…找不到产物键的数字是缺陷本身"：这三个数**有产物键但代码没读**，等价于手抄 —— 且手抄成 3 位小数，图与表/正文的口径一致性由人保证而非由代码保证。
- **混口径**：x = 297.0 / 342.1 / 387.8，间距 45.07 / 45.73 pt（几乎等距），但三个标签是 "cover@0"（绝对 0 s）、"cover@±0.2s"（绝对 0.2 s）、"cover@half"（**每段长度的一半**，相对量）。把绝对量与相对量排在同一类别轴上，等于把 s 与 % 并列。caption（main.tex:157-158）只说 "coverage at three tolerances"，未点明第三种是相对口径。
- **脚注错位**：panel (a) 标题 x 78.2–169.4、panel (b) 标题 x 318.3–366.5，两者 frame 均止于 y 106.0；红色脚注 "cuts per segment: BOCPD 1.14, threshold 0.79" 在 x 135.9–281.0、y 149.2–156.5 —— **横向落在 (a) 的区间内、纵向在两个 frame 之下**。视觉归属指向 (a)，但 1.14/0.79 是 `over_segmentation.*.mean_change_points_per_annotated_segment`，属整检测器、不属 (a)。caption 里虽有一句 "Coverage is bought with over-segmentation"，但读者先看图。

### 3.4 图3：长度诚实、面积撒谎，且只画有利的一半

**面积**（`fig_numbers.py` C2）：width/value 在四行上都是 169.824（AUC）与 169.824（F1），单一线性标尺，**柱长是对的**。但构造是"外柱 AUC、内柱 F1 嵌在里面"，读者若按墨水面积读：

- 外柱面积 1921.9 pt²，内柱 493.8 pt²，面积比 **0.2569**；
- 值比 F1/AUC = 0.6681；
- 低估 **61.5 %**。

这是典型的"用面积代替量值"：同一编码里混了两个面积语义（长度编码值、面积编码值×另一宽度）。改成"每行两根并排柱（AUC 灰、F1 深）"即可消掉。

**x 轴越界**（`fig_last.py` D2）：刻度 0.0→1.0 占 169.82 pt，1 单位 = 169.82 pt；frame 右边界 x1=351.98，对应值 **1.300**。AUC 与 F1 的上界都是 1.0，**30 % 的面板宽度是算术上不存在的数据**。为放标签而延长轴是常见做法，但这里没有断轴符号、没有轴端截断标记，读者会以为存在 >1 的取值。

**无 CI 让噪声变成发现**（`fig_evidence.py` E3，Hanley–McNeil，n1=51、n0=298）：

| 方法 | AUC | SE | 95 % CI | CI 宽度 |
|---|---|---|---|---|
| record_posterior_bound | 0.91367 | 0.0276 | [0.860, 0.968] | 0.108 |
| raw_record_bad_rate | 0.91479 | 0.0274 | [0.861, 0.969] | 0.108 |
| hierarchical_looo | 0.67548 | 0.0438 | [0.590, 0.761] | 0.172 |
| official_eligible_flag | 0.48993 | 0.0436 | [0.404, 0.575] | 0.171 |

前两行差 0.00112 = **一个 CI 宽的 1.0 %** —— 同一个数。图把它们画成两根等长的独立柱，等于把一个方法报了两遍。后两行 CI 不重叠（0.590 > 0.575），所以图的**真结论**（段级 LOO 优于 released flag）成立；被无 CI 抬举的只有前两行。

**只画有利的一半**（最重的一条）：正文 main.tex:150 明写段级组内 LOO AUC = **0.076**（低于随机、方向相反）。图3 画了 0.914 与 0.915 两根，**0.076 一根都没有**。正文用一整句自我否认的数，图把它当成主结果展示。这正对应任务里"敏感性是否只画了有利的一半"这一判据 —— 此处不是敏感性图，但**同一个病**：选择性展示。

同一句还有一个可复算的偏差。main.tex:150 说 "the record-level scores have a within-record AUC of exactly 0.500 by construction"，而 `downstream_auc.within_record.mean_auc`（n_records=21, n_segments=162）实测是（`out\_figcheck\sens_claims.py` 第 3 节）：

| 方法 | 组内 mean AUC | 是否"恰好 0.500" |
|---|---|---|
| record_posterior_bound | **0.5647683** | 否 |
| raw_record_bad_rate | 0.5000000 | 是 |
| official_eligible_flag | 0.5000000 | 是 |
| hierarchical_looo | 0.0759127 | 否（正文引用的就是这个 0.076） |
| oracle_segment_bad_rate | 1.0000000 | 否（上界参照） |

"exactly 0.500 by construction" 只对 `raw_record_bad_rate` 与 `official_eligible_flag` 成立；**`record_posterior_bound` 在组内其实是 0.565，高于随机 0.065**。所以正文那句话把三个方法一起按 "0.500" 处理，而图3 缺的那根参照柱应该是 **0.5648** 而不是 0.500 —— 若照 0.500 补柱，会把 posterior bound 的真实组内表现**再压低 6.5 个点**，是补图时必须用对的那个数。这条同时是"印出来的数必须能被别人复算"的正面例子：正文的 0.500 有产物键（`within_record.mean_auc`），一查就发现它对 0.5648 不成立。

### 3.5 图4：caption 的排序断言小于线宽，且只画了 4 个基线中的 3 个

`fig_numbers.py` C3：y 轴 0–20 占 82.78 pt → **4.139 pt/cm**。

| L (s) | Kalman (cm) | Hold (cm) | 差 (cm) | 差 (pt) | 与 1.5 pt 线宽比 |
|---|---|---|---|---|---|
| 0.2 | 2.862 | 3.387 | 0.525 | 2.17 | 1.45× |
| 0.4 | 5.656 | 5.998 | 0.342 | 1.42 | 0.94× |
| 0.6 | 7.095 | 7.353 | 0.258 | 1.07 | 0.71× |
| 1.0 | 9.464 | 9.554 | **0.090** | **0.37** | **0.25×** |

L=0.4/0.6/1.0 三处，两线间距都**小于或等于一条线宽**，笔迹重叠。而 caption（main.tex:274-276）断言 "The damped filter is **never worse than** holding the last state" —— 图在四处里有一处（0.37 pt）根本分不开，另两处勉强。**这句话只能由表（main.tex:248-251）承载，图承载不了。**

**只画 4 个基线中的 3 个**（`fig_text.py` 末节）：`mask_protocol.baselines` 有 12 行，含 hold / cv / **linear** 三种方法 × 四个 L：

| L (s) | hold | cv | **linear** | 图里画了吗 |
|---|---|---|---|---|
| 0.2 | 3.387 | 2.914 | **3.31** | hold ✅ cv ✅ linear ❌ |
| 0.4 | 5.998 | 7.731 | **6.342** | hold ✅ cv ✅ linear ❌ |
| 0.6 | 7.353 | 11.502 | **10.329** | hold ✅ cv ✅ linear ❌ |
| 1.0 | 9.554 | 21.497 | **18.003** | hold ✅ cv ✅ linear ❌ |

图例只有 "damped Kalman / last-state hold / constant velocity" 三行（6.20 pt，x 79.2）。linear 基线在 L=0.2 s 时（3.31 cm）比 hold（3.387）**更好**，也就是说"我们的滤波器在最短窗上优于所有基线"这个更强的主张其实**不成立**（Kalman 2.862 < linear 3.31，仍最好，但 linear 优于 hold 这一点被图隐去，使 hold 显得是唯一对手）。[判断] 这是"只画有利的一半"的第二种形态：不是把不利数据删掉，而是**少画一个会削弱叙事对照的基线**；理由链 = 该基线在同一 JSON、同一方法族、同四个 L 上齐备，删它无技术理由，而它的存在会改变"对手是谁"的读法。

同表 `rmse_cm` 与 `p90_cm` 也在同一行里，画一条误差带零成本，但图上一条 whisker 都没有。

"×1.0/×1.4/×1.6/×2.3" 标注：cv/kalman = 2.914/2.862 = 1.018、7.731/5.656 = 1.367、11.502/7.095 = 1.621、21.497/9.464 = 2.271 —— 数值全对（四舍五入到一位），但第一处把 1.8 % 写成 "×1.0"，在四个标注里读作"同量级"，而 1.8 % 与其余 37 %/62 %/127 % 不是一类事实。

标题 "(a) Error grows with the hidden window" 无 (b) —— 三个图（图3/4/5）都有这个孤悬的 "(a)"。

### 3.6 图5：截断的轴 + 与 caption 互相否认的虚线

**轴截断**（`fig_numbers.py` C4）：y 轴 9–14 占 91.10 pt；数据 9.874–12.809 = 53.47 pt = 面板高的 **59 %**；零点在可见底边下方 **1.8 个轴高**。2.94 cm 的差被拉满整个面板。截断本身可为"看差异"服务，但图上无断轴符号（无 zigzag、无 "axis starts at 9" 标注），caption 也不提 —— 读者会以为误差从 0 量起、2.9 cm 是"巨大差异"。

**虚线连错对象**（`fig_numbers.py` C6）：全图唯一长斜段 (98.0,54.8)→(336.4,100.4)，两端正是 A 的标记与 C 的标记。而 caption（main.tex:284-285）说 "the value of information is a **step function**: buy none or buy both" —— 若是阶跃，A 与 C 之间**不应有线**（或应是分段水平线）。图把阶跃画成平滑斜坡，与本文自己的结论相反。B（12.809 cm，代价 1）被这条线跳过，而 B 恰是被支配的中间选项 —— 斜坡暗示"买一次也能按比例获益"，正是本文要否定的。

**措辞与几何相反**：caption 说 "The dashed line joins the two **interior points** of the frontier"（main.tex:285-286），但 A（代价 0）与 C（代价 2）是**两个端点**，B（代价 1）才是内点。一句话同时错了对象与几何。

**拐点未标**：break-even = 1158.006 cm²/单位 ≈ 1.608 cm RMSE（`voi.threshold_cm2` / `threshold_rmse_cm`），只以文字出现。P3 要求"Pareto/Laffer 标拐点"，这里既无竖线、无切点、无阴影区。★ 这正是六范式里 P3 的判据落点：**代价-误差平面上，A→B 是支配关系（B 更贵且更差），B→C 是真实交易；拐点在 B 处，不在 A→C 的中点**。图上把 A→C 连成直线，等于把拐点位置抹掉。

**n 不等却横比**（`voi_opts.py`）：`data\alt_p2.json` → `official_options` 中 A `n_windows=221`、B/C `n_windows=300`；`mask_protocol.hold_A_90 = {n_windows: 221, mean_cm: 12.412, rmse_cm: 14.592}` 佐证 A 的 90 % 分位只在 221 窗上算。Table 7 caption（main.tex:259）写 "evaluated on the **same windows**"，图5 把三点画成可直接横比。A 的 12.377 与 300 窗 hold 基线 12.412 之差（0.035 cm）**只来自窗集不同**，不来自方法。

### 3.7 敏感性：表格形态下的"只画有利的一半"

论文没有敏感性图（P2 缺失），敏感性全部落在 `tab:p1sens`（main.tex:175-191）。表格同样能犯"只画有利的一半"，这里犯了四重（`out\_figcheck\sens_rank.py`、`sens_claims.py`）：

**一、8 行不是 8 个配置。** 按四个指标的完整元组去重，8 行只有 **7 个不同配置** —— `hazard_lambda_s=4` 与 `sigma_s=0.4` 是同一格（两行数值逐位相同：mae 2.94203、F1@0.5s 0.18262、F1@2s 0.58027、F1@5s 0.65390）。正文 main.tex:173 写 "Eight configurations were re-run"，实际是 7 个配置 + 1 行重复的基准。重复印基准行是常规做法，但"8 个配置"这句话是错的，且它让"扫了 8 次"的印象强于事实。

**二、选中的格在未印的那一列上不是最好。**

| 指标 | 选中格 | 名次（7 格） | 最好 | 最差 | 表里印了吗 |
|---|---|---|---|---|---|
| Count MAE | 2.94203 | **2/7** | 2.88406（sigma=0.6） | 3.13043 | 印了 |
| F1@0.5s | 0.18262 | **1/7** | 0.18262 | 0.13650 | 印了 |
| F1@2s | 0.58027 | **1/7** | 0.58027 | 0.52915 | 印了 |
| F1@5s | 0.65390 | **2/7** | 0.65896（hazard=2） | 0.63677 | **没印** |

表印的三列里，选中格有两列是第 1；唯一不是第 1 的那一列（Count MAE，第 2）还在表里，而**它也不是第 1 的那一列（F1@5s）被整列省掉了**。JSON 里 `micro_f1_5` 是逐行都有的字段，省掉它是选择而非数据限制。这不是"图只画有利的一半"，是"表只印有利的三列"，同一个病。

**三、正文把 sigma 的摆幅记在 hazard 名下。** main.tex:365 写 "The hazard rate is the only parameter that matters: moving it by a factor of two changes $F_1$ by 0.046"：

| 参数 | F1@0.5s 全距 | 扫描跨度 | 相邻 2× 步长的实际变化 |
|---|---|---|---|
| hazard_lambda_s | **0.03912** | 2→8（4.00×） | 2→4: **+0.03522**；4→8: **−0.03912** |
| sigma_s | **0.04612** | 0.25→0.6（2.40×） | 无 2× 步长（0.25→0.4 是 1.6×） |

**0.046 精确对上 sigma 的全距 0.04612，对不上 hazard 的 0.03912**；而且 sigma 的摆幅（0.04612）比 hazard 的（0.03912）**大 18 %**，所以"hazard 是唯一要紧的参数"被这张表本身否证。另外"factor of two"在表里没有对应的相邻行：hazard 的 2× 邻居是 2→4 与 4→8，给出 +0.035 与 −0.039，都不是 0.046。这条是**可复算的正文与产物冲突**，比缺图严重。

**四、两个参数根本没扫。** `min_seg_s=3.0` 与 `map_drop=0.3` 在 `data/*.json` 全部 8 个文件里各只出现 **2 次，且是同一个值**：`alt_p1.json` 的 `/config` 一次，`results_swc2026.json` 的 `/alt_p1/config` 一次（该文件是 `alt_p1/alt_p2/alt_p3/...` 的**镜像汇总包**，不是独立产物）—— 也就是**去重后只有 1 个值、0 条 sweep**。对照 `hazard_lambda_s` 12 次、`sigma_s` 8 次（同样两文件镜像，去重后 6 次与 4 次，即真被扫过）。复算命令见 §5 第 13 条。所以 main.tex:365 "the merge threshold and the drop fraction move it by less than 0.01" 这句话**在产物里找不到任何依据** —— 按任务契约"找不到产物键的数字是缺陷本身"，这不是"需要更精确"，是**没有测过**。

**范式判读**：敏感性在六范式里应做成龙卷风（每参数 ±1 档对三指标的摆幅，一眼看出 sigma 的条形比 hazard 长）或秩漂移（7 个配置在三个指标下的排序是否翻转 —— 本例中 Count MAE 的第 1 是 sigma=0.6、F1@0.5s 的第 1 是 hazard=4、F1@5s 的第 1 是 hazard=2，**排序确实翻转**，正是秩漂移图要展示的现象）。目前是一张 5 列 8 行的表，读者要自己算全距才能发现正文说反了。

### 3.8 自解释清单（单位 / 样本量 / 误差带 / 口径，逐图实测）

`fig_last.py` D3 + `fig_text.py` 逐字清点：

| 图 | 单位在图上 | 样本量在图上 | 误差带 | 口径在 caption | CJK |
|---|---|---|---|---|---|
| 图1 | ❌（"frames""records" 是名词不是单位） | ✅（69 records / 66,070 frames / 349 segments） | ❌ | ⚠ 颜色无语义、链接只在脚注 | 0 ✅ |
| 图2(a) | ✅（ylabel "Boundary $F_1$"，横轴 "±0.2 s"） | ❌（caption 有 280，图上无） | ❌ | ⚠ 未给 399 vs 276 | 0 ✅ |
| 图2(b) | ⚠（"%" 在 ylabel "Annotated segments covered (%)"） | ❌（图上无 349） | ❌ | ⚠ 未说明 half 是相对口径 | 0 ✅ |
| 图3 | ✅（"AUC"/"$F_1$" 是量名，无单位需求） | ✅（"prevalence 14.6% (51/349 segments)"） | ❌ | ⚠ 未给 CI 方法 | 0 ✅ |
| 图4 | ✅（"Mean 3D error (cm)"、"Mask length $L$ (s)"） | ✅（"test records 7, 300 windows per length"） | ❌ | ⚠ 未写 ×2.3 的分母 | 0 ✅ |
| 图5 | ✅（"Mean 3D error (cm)"、"Cost units…"） | ❌（图上无 221/300） | ❌ | ❌（"interior points" 与几何相反） | 0 ✅ |

- **C7 通过**：五张图 cjk=0，`2018_APMCM_Essay_format_and_submission_specifications.txt:81` 把 chart 纳入"不得出现中文"的范围，此项满足 —— 这是唯一一条可官方引用且通过的图内文字判据。
- **误差带 0/5**：见 §4.1 的实测。
- **样本量 3/5 在图上**，但**恰是唯一有 n 不等问题的那张（图5）没有**；这是自解释性最该补的一处。

---

## 4. 四类高频可复算缺陷在图表层的落点

任务点名的四类（口径混用 / 倍数与百分数 / 多重比较 / 图表刻度），逐类在图上的实际命中：

### 4.1 图表刻度（含误差带）

- **无误差带是实测结论，不是印象**（`fig_numbers.py` C5）：fig1/fig3/fig4 里所有细竖段都是 3.50 pt 的轴刻度，且**坐在同一基线上**（fig1 全在 y 105.98–109.48；fig3 全在 129.44–132.94；fig4 全在 122.31–125.81），颜色全为 (0.1059,0.1059,0.1059)。**没有任何与数值相关的竖向长度** → 零 whisker。五张图里一张带误差带都没有。
- **轴越界**：图3 到 1.300（超上界 30 %）。
- **轴截断**：图5 从 9 起（数据占 59 % 面板高，零点在下方 1.8 个轴高）。
- **类别轴代替数值轴**：图2(a) 等距 43.153 pt vs 数值间距 10.0× 差。
- **口径混轴**：图2(b) 绝对/相对混排。
- **有效字号**：页面最小 4.73 pt（6 个单字符 span），机器判 PASS、人判不合格（§3.0）。

### 4.2 口径混用

- 图2(b)：`cover@0`（s）与 `cover@half`（段长比例）同轴。
- 图5：A 用 221 窗、B/C 用 300 窗，caption 称 "same windows"；这是**同一个"倍数"两个分母**的典型（0.035 cm 差来自窗集）。
- 图3：`record_posterior_bound` 与 `raw_record_bad_rate` 是**同一信息的两条代理**，被画成两个方法。
- 图4：`mean_cm` 作图，而同表 `rmse_cm`/`p90_cm` 不画 —— 误差度量在"均值 vs 尾部"间只取了对本文最有利的那个（均值最小）。
- 图2(a)：只画 F1，不画 precision/recall；两种检测器 n_pred 不同（399 vs 276），同一 F1 不等价（§3.2 表）。

### 4.3 倍数与百分数（同一现象两个分母）

- 图4 的 "×2.3"：分母是 Kalman 的 9.464 cm，得 2.271；若分母换成 hold 的 9.554，得 2.250；若换成 RMSE 的 11.334，得 1.897。caption 只说 "a factor of 2.3 better than ballistic extrapolation"，未写分母是哪一个量（应为 mean_cm 的 Kalman）。同页 Table 6 印的是 RMSE 列，读者若拿 RMSE 复算得 1.90，对不上 2.3。
- 图2(b) 的 "1.14 vs 0.79 cuts per segment"：两个数都除以"annotated segment"数，但 BOCPD 实际产出 399 个边界、基线 276 个（caption 未给这两个原始数），1.14 = 399/349、0.79 = 276/349 —— **百分比的分母（349）未在 caption 出现**，读者无法复算。
- 图3 的 "F₁/AUC"：面积比 0.2569 vs 值比 0.6681（§3.4），同一个比值两个数，差 61.5 %，取决于按长度读还是按面积读。

### 4.4 多重比较

图3 一张图 4 个 AUC 的比较、图2(a) 一张图 8 根柱的比较、图4 一张图 12 个点的比较，**全部无任何校正**（无 BH/Bonferroni 后的 q，无 family-wise 说明）。最尖锐的是图3：4 个 AUC 两两比 = 6 对，其中 0.914/0.915 这一对差 1.0 % 个 CI 宽被当结果。按任务契约"同一张表 k 个检验，必须给 BH/Bonferroni 后的 q"，此处 **k=6 而 q 一个都没有**。

敏感性侧同一个病、另一种形态（§3.7）：8 行里选中的格在三个已印指标上是第 2/1/1 名，**没印的 F1@5s 上它是第 2 名**。多指标择优不校正、且择优用的指标恰好是已印的三个 —— 这是"用同一份数据既选参数又报性能"的选择性偏倚，比缺 q 值更实。

---

## 5. 复算命令（拿同一份 PDF 可重跑）

```powershell
$R  = "E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP"
$PY = "E:\Mini\envs\mathmodel\python.exe"

# 0) 三条机器口径（§0.1–0.3）
cd $R
& $PY "E:\数学建模\.agents\skills\mathmodeling\scripts\review_check.py"   $R
& $PY "E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py" $R
$env:PYTHONPATH = "E:\数学建模\.agents\skills\mathmodeling\scripts"
& $PY -m mmkit.figfont "$R\main.pdf"

# 1) 正文 0 处图引用（§3.1）：应输出 0
& $PY -c "import re;t=open(r'$R\main.tex',encoding='utf-8').read();print('ref fig:',len(re.findall(r'\\\\ref\{fig:',t)),' ref tab:',len(re.findall(r'\\\\ref\{tab:',t)))"

# 2) 五张图的几何与字号（§3.0 表）
cd $R; & $PY out\_figcheck\fig_geometry.py

# 2b) 图引用计数（§3.1 首段）：应输出 ref fig: 0 / ref tab: 7 / label fig: 5 / label tab: 8
cd $R; & $PY out\_figcheck\refcount.py

# 2c) 排版缩放因子 1.0889 的实测（§3.0）：五张图 ink 宽 416.55 → 落位 453.56
cd $R; & $PY out\_figcheck\scale_ratio.py

# 3) 图2(a) 刻度是否等距（§3.2 表）
cd $R; & $PY out\_figcheck\fig_axes.py

# 4) C1..C7：轴间距 / 长度vs面积 / Kalman-hold 间距 / 轴截断 / whisker / 虚线端点 / n_windows
cd $R; & $PY out\_figcheck\fig_numbers.py

# 5) D1..D3：fig0 填色与连接线 / 轴越界 / CJK 与自解释清单（§3.1、§3.8）
cd $R; & $PY out\_figcheck\fig_last.py

# 6) E1..E4：脚注错位 / 图2(b) 混口径 / Hanley-McNeil CI / 孤悬 "(a)"
cd $R; & $PY out\_figcheck\fig_evidence.py

# 7) fig0 的跨问链接箭头计数（§3.1）：应输出 0
cd $R; & $PY out\_figcheck\fig0_curves.py

# 8) 22 篇一等奖的图引用与范式基线（§1.1）
cd $R; & $PY out\_figcheck\award_figref.py

# 9) 图3/图4 图内每一个字的字号与坐标，以及 4 个基线是否都画了（§3.5、§3.6、§3.8）
cd $R; & $PY out\_figcheck\fig_text.py

# 10) 图2(a) 的 F1 拆成 precision/recall（§3.2 第二张表）
cd $R; & $PY out\_figcheck\fig1_pr.py

# 11) 敏感性：8 行几个不同配置、选中格在四个指标上的名次（§3.7 一、二）
cd $R; & $PY out\_figcheck\sens_rank.py

# 12) 0.046 属于哪个参数、merge/drop 有无扫描、组内 AUC 是否恰好 0.500（§3.7 三、四；§3.4）
cd $R; & $PY out\_figcheck\sens_claims.py

# 13) min_seg_s / map_drop 是否被扫过（§3.7 四）：应输出各 2 次，hazard 12 次、sigma 8 次
& $PY -c "import glob,os;R=r'$R\data';[print(k,sum(open(f,encoding='utf-8').read().count(chr(34)+k+chr(34)) for f in glob.glob(os.path.join(R,'*.json')))) for k in ('min_seg_s','map_drop','hazard_lambda_s','sigma_s')]"

# 14) 六范式的真题基线（§1.1 表）：每行输出 "篇数/22 命中次数"
#     应输出 heatmap 7/22 17、pareto 5/22 44、contour 3/22 16、radar 1/22 1、laffer 1/22 8、tornado 0/22 0
#     heatmap 的第 7 篇是 C题02422.txt 的"热力学…热波动"误命中，剔除后即 §1.1 表的 6/22 16
& $PY -c "import re,glob,os;T=r'E:\数学建模\APMCM-PROBLEMS\_award_text';fs=sorted(glob.glob(os.path.join(T,'*.txt')));ps={'heatmap':r'heat\s*map|heatmap|热力|热图','pareto':r'pareto|帕累托','contour':r'contour|等高线','radar':r'radar|雷达','laffer':r'laffer','tornado':r'tornado|龙卷风'};[print(k,sum(1 for f in fs if re.search(p,open(f,encoding='utf-8',errors='replace').read(),re.I)),'/',len(fs),sum(len(re.findall(p,open(f,encoding='utf-8',errors='replace').read(),re.I)) for f in fs)) for k,p in ps.items()]"
```

上述 `out\_figcheck\` 下 13 个脚本（fig_geometry / refcount / scale_ratio / fig_axes / fig_numbers / fig_last / fig_evidence / fig0_curves / award_figref / fig_text / fig1_pr / sens_rank / sens_claims）+ 3 条官方脚本（review_check / gauntlet_check / mmkit.figfont）+ 第 13 条内联命令，已在本次审读中全部跑过，输出即本报告引用的数字；脚本留在 `out\_figcheck\` 下，任何人可重跑。第 2b 条（图引用计数）应输出 `ref fig: 0 / ref tab: 7 / label fig: 5 / label tab: 8`，第 2c 条（缩放因子）应输出五行 `1.0889`，第 13 条应输出 `min_seg_s 2 / map_drop 2 / hazard_lambda_s 12 / sigma_s 8`，第 14 条应输出 `heatmap 7 / 22 17` 等六行（heatmap 第 7 篇为误命中，见 §1.1 表下的复算口径行）—— 这四条的输出我今日均已核对，与报告正文一致。

---

## 6. 结论

**判 FAIL。** 三条机器口径全过（review_check PASS、gauntlet 16/16、figfont PASS），所以剩下的是**必须读出来的问题**，共 8 类：

1. **图3 只画有利的一半** —— 正文 main.tex:150 自陈段级组内 LOO AUC = **0.076**（低于随机、方向相反），图里 0.914/0.915 两根在、它不在。另：同句说 "the record-level scores have a within-record AUC of exactly 0.500 by construction"，实测 `downstream_auc.within_record.mean_auc` = {hierarchical_looo 0.0759, record_posterior_bound **0.5648**, raw_record_bad_rate 0.5000, official_eligible_flag 0.5000, oracle 1.0000} —— **只有两个恰好 0.500，posterior bound 是 0.565**，正文的 "by construction" 对它不成立。这是本报告最重的一条。
2. **敏感性只印有利的三列，且正文的 0.046 属于另一个参数** —— tab:p1sens 的 8 行其实只有 **7 个不同配置**（hazard=4 与 sigma=0.4 是同一格），正文 main.tex:173 却说 "Eight configurations"；表只印 Count MAE / F1@0.5s / F1@2s，**不印 F1@5s**（`micro_f1_5`），而选中格在 F1@0.5s 与 F1@2s 上是 7 格中的第 1、在 **F1@5s 上是第 2**、在 Count MAE 上是第 2。更硬的是 main.tex:365 "moving it [hazard] by a factor of two changes F1 by 0.046"：hazard 的 F1@0.5s 全距只有 **0.03912**（2→4 得 +0.03522、4→8 得 −0.03912），而 **0.04612 正是 sigma 的全距** —— 正文把 sigma 的摆幅记在 hazard 名下，并据此说"hazard 是唯一要紧的参数"，与表相反。
3. **图2(b) 基线三元组硬编码**（`alt_figures.py:171`），有产物键却没读；图1 的 69/66,070/349 同病。任务契约"印出来的数必须能被别人复算"在此断裂。
4. **图5 与 caption 互相否认** —— 虚线连 A→C 画成平滑斜坡，caption 说 "step function: buy none or buy both"；caption 又称 A/C 为 "interior points"，而它们是端点。拐点（B 处）因此被抹掉。
5. **图5 三选项 n 不等（A 221 / B·C 300）却被 caption 说成 "same windows"** —— 可复算的样本量矛盾。
6. **零误差带**（实测 0 条 whisker，五张图）；图4 的 "never worse than holding" 在 L=1.0 处只有 0.37 pt，小于线宽；而 `rmse_cm` / `p90_cm` 就在同一行 JSON 里，画带零成本。图4 另**少画一个基线**（linear 3.31/6.342/10.329/18.003），而 linear 在 L=0.2 s 优于 hold，会改变"对手是谁"的读法。
7. **三种刻度误用各一处**：图2(a) 把有序数值摊成等距类别轴（页间距极差 0.000 pt vs 数值间距 10.0×）、图3 x 轴跑到 1.300（超度量上界 30 %）、图5 y 轴截断到数据范围的 59 %（零点在可见底边下 1.8 个轴高）—— 全部无断轴符号。
8. **六范式缺 4 个**：热力图（6/22 一等奖用过，Q3 的 3×5×4 网格正是标准形态）、Pareto 拐点（5/22 用过，图5 有前沿实质却不标拐点）、雷达（1/22，建议项）、龙卷风/秩漂移（0/22，但敏感性表只扫 2 参数、merge threshold 与 drop fraction **根本没扫** —— `min_seg_s` 与 `map_drop` 在全部 8 个 JSON 里各只出现 2 次（各文件的 `config` 选定值），对照 `hazard_lambda_s` 12 次、`sigma_s` 8 次）。

**改法优先级**：图3 重画（补 0.076 与组内 0.5648 参照柱 + CI + x 轴收到 1.0）> 敏感性补龙卷风图并补印 F1@5s、改正 0.046 的归属、删未测的 merge/drop 断言 > 图5 重画（阶梯线 + 从 0 起 + break-even 竖线）+ 改 caption（n 不等）> 图2 重画（数值轴 + 读 JSON + 补 P/R）> 图4 重画（加 rmse/p90 带 + 补 linear + 内嵌放大）> 图1 重画（补两条箭头 + 图例）> 正文补 5 处 `\ref{fig:}` > 补 Q3 热力图与雷达。

VERDICT: FAIL
