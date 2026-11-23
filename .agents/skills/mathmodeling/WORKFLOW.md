# 从题目到一等奖论文：可复刻工作链

> 本文件是**执行手册**，不是介绍。拿到新题后照着从上往下走，每步都有命令与机器闸门。
> 配套：`SKILL.md`（工具总表）、`RUNBOOK.md`（叙事版流程 + 踩坑）、`RULES.md`（75 条硬规则）、
> `templates/PAPER-TEMPLATE.md`（章节骨架）、`E:\数学建模\APMCM2025_C\refs\award_structure_spec.md`（22 篇一等奖实测结构）。

---

## 0 一句话

```
run_all.py（或 new_paper.py → new_verify.py → pipeline.py）→ 交稿
```

`run_all.py` 是最省事的入口（骨架 → 八步二十门 → 交件一条命令），`pipeline.py` 是**真正的引擎**。
它把「赛题分析 → 建模 → 编程 → 口径审计 → 图表 → 论文 → 编译合规 → 评审收口」
八步，落到本机 18 人建稿队 + 13 人审阅队 + 二十道机器门上，**可断点续跑**：某步失败，修完重跑同一条命令，
已过的步骤不会重派（不烧额度、不覆盖已对好的产物）。

### 0.1 门的三种不确定结果

| 标记 | 含义 | 拦不拦 | 谁会产生 |
|---|---|---|---|
| ` ?? ` | 该判却判不出（工具崩了、超时、缺参数） | 软闸门不拦，其余**拦** | 任何闸门函数抛异常或返回 `None` |
| ` NA ` | 结构上不适用 | 不拦，但 `--status` 单独列一行 | `gate_g10`（无 `TABLE_*`）、`gate_g14`（无上传模板）、`gate_g11`（没配视觉模型）、`_md_gate(judgment=True)`（人写的审计报告比稿子旧 >5 分钟） |

**为什么要分开**：「本题根本没有这个对象」和「有这个对象但我没判成」是两件事。混成一个，
前者的题目会永远卡在红门后面（逼人为了过门造假产物），后者会以为自己过了（假绿）。
`--status` 的输出末尾会打两行：`不适用（NA，未真判）：…` 与 `未过：…`，谁也藏不住。

### 0.2 派单失败会自动降级

`pipeline.py` 默认「派单优先」：这一波交给小队会话。派单不可用（GUI 没起、宿主 run 状态卡住）时
不中断流程，而是把这一波每人**完整 brief** 落到 `<paper>\logs\briefs\<sN>-<成员>.md`，状态置
`awaiting-session`，打印怎么续：

```
pipeline.py <paper> --skip-dispatch --only sN --force sN
```

`--skip-dispatch` 是同一通道的显式版：**只跑门、不派单**。

### 0.3 增量评审

每步门**全过之后**自动叫对应的审读员（`s1 题目契合` / `s2 模型与检验` / `s3 数据与代码 + 数字对账` /
`s4 口径冲突` / `s5 图表` / `s6 结构 + 摘要` / `s7 合规 + 版式出栏`），产物落 `review/`。
门没过就不叫——评一份已知有病的稿是浪费额度。`--no-review-each` 关掉。

### 0.4 状态文件会随步骤表改版

`logs\pipeline_state.json` 有 `schema` 字段。步骤表改版（这次把 7 步扩到 8 步、`s4` 从「图表」
改成「口径审计」）会让旧记录的键与新步骤对不上，所以 `STATE_SCHEMA` 同时升到 3：
旧状态整份作废并备份成 `pipeline_state.v<n>.bak`，不把 `s4=done` 误读成新 s4 已做完。

---

## 1 环境（一次配好）

```powershell
$PY = 'E:\Mini\envs\mathmodel\python.exe'        # 数值/画图/torch/docx/pymupdf 全在这
$MM = 'E:\数学建模\.agents\skills\mathmodeling'
$S  = "$MM\scripts"
$env:PATH = "E:\MIKTEX\miktex\miktex\bin\x64;$env:PATH"   # xelatex
$env:DSH_WEB_URL = 'http://127.0.0.1:63649'      # 小队派单必需；端口以当前 GUI 为准
$env:PYTHONIOENCODING = 'utf-8'                  # 中文输出不乱码
```

四条硬约束（踩过才知道）：

| 约束 | 原因 |
|---|---|
| 一律用 `$PY`，不用裸 `python` | 裸 python 没有 numpy/pandas/pymupdf，`gauntlet_check` 会退化成 `0/2 PASS` |
| 写 JSON 一律用 python `pathlib.write_text(encoding="utf-8")` | PowerShell 5.1 的 `Set-Content -Encoding UTF8` 带 BOM，`json.loads` 直接 ValueError |
| `$env:DSH_WEB_URL` 必须是**当前** GUI 端口 | 端口每次重启都变（见过 57781 / 63649）；`crew.list_members()` 拿不到名册就派不了单 |
| `$env:PATH` 前置 MiKTeX | `gauntlet.build()` 调 `xelatex`，不在 PATH 就静默返回非零 |

自检一条命令：

```powershell
& $PY -c "import numpy,pandas,matplotlib,pymupdf,docx;print('deps OK')"
```

---

## 2 起骨架（3 分钟）

```powershell
$P = 'E:\数学建模\APMCM2026_C'                  # 本题目录，名字随便
& $PY "$S\new_paper.py" $P --type C             # 题型见下表
& $PY "$S\new_verify.py" $P                     # 对账器 + 四个代码骨架
Copy-Item '<题面路径>' "$P\problem\problem.txt"  # 题面进 problem/
```

`--type` 选族（依据 16 篇一等奖实测：A 3/4、B 4/4、C 4/4、D 2/3、E 1/1 各用同一族骨架）：

| 题号 | 题型 | 骨架族 | 标志性方法 |
|---|---|---|---|
| A | 图像 / 几何 / 工程测量 | A-α 逐问四件套 | 预处理、分割、Hough、CNN |
| B | 物理 / 工程优化 | B-α 机理章 + 问内五件套 | 多目标、微分方程、元启发 |
| C | 数据 / 统计 / 政策 | C-α 数据章前置 + 问内三段 | 回归、ARIMA、计量、博弈 |
| D | 组合 / 整数 / 前沿 | D-α 一模型一章 | 整数规划、QUBO、退火、SVM |
| E | 聚类 / 时序 | E-α | 聚类、时序四步检验 |

**选错族别回头改**：章序列错了只是排布难看，结论不受影响；改的成本远高于收益。

`new_verify.py` 必须在写正文**之前**跑 —— 它扫 `data/*.json` 生成对账基准，
正文里的数字是照着 JSON 写的。反过来先写正文，就没有可对账的基准，最后只能肉眼比。

---

## 3 八步流水线（核心）

```powershell
& $PY "$S\pipeline.py" $P --status          # 随时看做到哪、每道门什么结果
& $PY "$S\pipeline.py" $P --dry             # 只打印计划
& $PY "$S\pipeline.py" $P                   # 从第一个未过的步骤接着跑
& $PY "$S\pipeline.py" $P --step s3         # 跑到 s3（含）
& $PY "$S\pipeline.py" $P --only s4 --force s4   # 只重跑 s4
& $PY "$S\pipeline.py" $P --skip-dispatch   # 只跑闸门不派单（改完稿自查）
```

### 八步 → 成员 → 闸门

| 步 | 名称 | 派谁 | 闸门 | 判据 |
|---|---|---|---|---|
| s1 | 赛题分析 | 题目侦察手、数据溯源手、**真题对标手** | G1 G2 **G20** | 逐句抄出"要求你"的句子 / 台账每条带出处+sha256+fetched_at / 同型题对标报告 `out/15-benchmark.md`（见 `CORPUS.md`） |
| s2 | 建模求解 | 建模架构手 | G3 | 符号表 + 假设 + 反证条件齐 |
| s3 | 编程实现 | 求解与优化手、代理模型训练手、数值对账手 | G4 G5 G10 | 交付耗时/binding/边界解 / `verify_numbers` 0 failures |
| s4 | 口径审计 | 口径审计手 | G16 | `out/05-caliber.md` 有 VERDICT（同一名词不许被两种算法用过） |
| s5 | 图表 | 图表手 | G6 G11 | 每图 pdf+png 双格式 + 图内有效字号 ≥6 pt |
| s6 | 论文撰写 | 论文撰写手、附录与自指手 | G7 G12 G17 | 12 条官方硬项无 FAIL / `code_index.tex` 的字节数与磁盘一致 |
| s7 | 编译合规 | 格式合规手、版式与出栏手、流水线运维手 | G8 G13 G14 G15 G18 G19 | xelatex 两遍成功 + gauntlet 16/16 + venue 0 项要你处理 + 图无贴边 + 无非软闸门留 `??` |
| s8 | 评审收口 | 13 人审阅队（11+1+1 三波） | G9 | `review/00-plan.md` 有 VERDICT |

**为什么把口径审计单独立一步**：2026_C 的 42 项审阅清单里有 10 项是「同一个词被两种算法用过」——
`4.608%` 与 `4.506%`（W=800 与 W=793）、`0.86%` 与 `0.8608`（相对量 vs 效益值）、`0.1317` 是 tiers 3+4+5
而 `0.0148` 是 tiers 4+5。这类缺陷两个数各自都算对了，放在数值对账里永远抓不到。

### 闸门的三种返回值（重要）

`PASS` / `FAIL` / `??`（判不出）。**`??` 不许当通过** —— 缺文件、缺依赖、解析不出计数，
一律报 `??` 而不是默认 PASS。这是 `mmkit/review_bench.py` 定下的规矩：机器没报错 ≠ 这步没问题。

`--status` 的输出长这样（真实运行）：

```
步骤    名称        状态        闸门
s1    赛题分析      done      G1=PASS  G2=PASS
s2    建模求解      done      G3=PASS
s3    编程实现      gate-failedG4= ??  G5=PASS
...
```

### 断点续跑怎么工作

状态写在 `<论文目录>/logs/pipeline_state.json`，每步记 `status` / `gates` / `gate_detail` / `outcomes`。
重跑时 `status == "done"` 的步骤直接跳过。想重跑某步用 `--force s4`。

---

## 4 每问内部怎么写（拿一等奖的关键）

依据 `award_structure_spec.md`（精读 13 篇 + 量化扫 22 篇）：**每题六件套，缺一件就扣"不完整"**。

| 件 | 内容 | 硬要求 |
|---|---|---|
| A | 问题重述（本文变量） | 不许抄题面原句 |
| B | 建模思路 | 一句话说清"为什么用这个方法" |
| C | 模型建立 | 公式带编号；符号与 Notations 表一致 |
| D | 求解 | 给算法名 + 关键参数值 + 复杂度或耗时 |
| E | 结果 | **表格化**，每个数字带单位；至少一个反直觉发现 |
| F | 小结 | 三句：得到了什么 / 为什么可信 / 对下一问有什么用 |

### 摘要骨架（评委只认真读这一页）

英文 14 句（12–16 句，350–430 词），中文 11 句（850–1000 字），**结果数字 4–8 个**。

```
B 背景+痛点（1 句）
M 总方法（1 句：宣布"建了一系列模型"）
Q1m → Q1r → Q1c    （每问 2–3 句：方法 → 数字 → 判词）
Q2m → Q2p → Q2r
Q3m → Q3r
Q4m → Q4r
v+S 综合验证 + 意义（1 句）
```

三条实测规律：

1. **数字少不是问题，数字虚才是问题**。中文一等奖那篇整篇摘要只有 4 个数字，但每个都带单位、都能对上正文的表。
2. 每问以「针对问题一 / For the first problem」开头，评委一眼扫得到。
3. 「首先/接着/最后」各用一次就收手，靠**分段**而不是连接词推进。

### 正文章节（8 章通用骨架）

```
Summary Sheet（第 1 页，不占正文页数）
Contents（第 2 页起）
I.   Introduction          （Background ≤3 句 / Restatement 改写成本文变量 / Our Work 每问一句）
II.  Problem Analysis      （机制、关键矛盾、简化了什么及为什么）★16/16 一等奖都有
III. Assumptions and Justifications （假设 / 理由 / 被谁用）★16/16
IV.  Notations             （三列：Symbol / Meaning / Unit）
V..  每问一章
N-3 Sensitivity and Error Analysis  ★14/16
N-2 Strengths and Weaknesses        ★16/16
N-1 References             （≥12 条，≥70% 在正文 cite，[M]/[J]/[R]/[DB/OL] 不漏）
N   Appendix               （软件名 + 全部源码）
```

页数预算（正文 30 页上限）：摘要 1（不占正文）/ 引言+分析 2–3 / 假设+符号 2–3 / 每问 4–6（图 ≤3、表 ≤3）/
检验 2–3（≥2 张图）/ 评价 1（优缺点各 3 条）/ 参考文献 1。**超页唯一有效手段：归档表搬附录。**

---

## 5 交稿前：二十道门逐条过

`pipeline.py --status` 全 `PASS` 之后，再手工确认七件事（每项都要有命令输出）：

1. `pdfinfo main.pdf` 的 `Pages:` 与正文末页页眉数字差 ≤ 附录页数 —— 两处对。
2. `gauntlet_check.py` 除队号外全 PASS。
3. `verify_numbers.py` 打 `0 failures`，且条数是**真检查过的**条数（不是 0 条的空壳通过）。
4. 每个图文件都有 `.pdf` 与 `.png` 两份，`code/make_figures.py` 能原样重跑。
5. `data/ledger.json` 里没有一条 `sha256` 为空（或已声明 `NOT-APPLICABLE` 且给了常量基线）。
6. 队号已填（脚手架写的是占位，**提交前必须换成本队真号**）。
7. AI 使用说明与实际用过的大模型一致（若赛制要求）。

### 5.1 九道机器闸 + 十道 paper-kit / 自检闸

`pipeline.py` 现在跑 **20 道门**。前九道是 `mathmodeling` 自己的，后面十道接的是 `paper-kit` 的离线工具与自己写的三项自检：

| 门 | 步骤 | 跑什么 | 判据 | 软闸门 |
|---|---|---|---|---|
| G1 题面 | s1 | 逐句抄题 + 常量表 | `VERDICT: PASS` | |
| G2 数据溯源 | s1 | 34 条常量标行号 | `NOT-APPLICABLE` 或 PASS | |
| **G20 真题对标** | s1 | 查过语料（正文出现 `corpus_index.py`/`corpus.json`） | `out/15-benchmark.md` 有 `VERDICT: PASS` | |
| G3 模型 | s2 | 符号冲突消解 | PASS | |
| G4 求解 | s3 | `out/02-solve.md` | PASS | |
| G5 数字对账 | s3 | `verify_numbers.py` | `failures=0` | |
| **G10 表格数据** | s3 | `paper_data_check --mode table` | 有 `TABLE_*` 才判 | ✅ |
| **G16 口径审计** | s4 | `out/05-caliber.md` | 有 VERDICT | |
| G6 图表 | s5 | 14 图 pdf+png、图内字号 | 全 `ok=True` | |
| **G11 视觉审查** | s5 | `data_fig_vision_check` | 视觉模型可用才判 | ✅ |
| G7 正文形态 | s6 | `review_bench` 12 项 | `fail=0 unknown=0` | |
| **G12 论文数字** | s6 | `paper_data_check --mode pdf` | `致命=0` | |
| **G17 附录自指** | s6 | `figures/code_index.tex` vs 磁盘 | 每个脚本字节数逐一相等 | |
| G8 编译合规 | s7 | `gauntlet_check.py` | 16/16 | |
| **G13 投稿体检** | s7 | `venue_submission_check` | `0 项要你处理` | |
| **G14 模板核对** | s7 | `template_ingest verify` | 有上传模板才判 | ✅ |
| **G15 源文件闭包** | s7 | `paper_source_scope` | `figures/` 无死文件 | |
| **G18 版式出栏** | s7 | 逐张 `figures/*.pdf` 的 span 对 MediaBox | 无贴边（含 `x1 > W-2.0`）+ `Overfull >10 pt` 为 0 | |
| **G19 流水线自检** | s7 | 读 `pipeline_state.json` | 非软闸门不许留 `??`；`out/14-ops.md` 有 VERDICT | |
| G9 评审收口 | s8 | 审阅队报告 | 计划落盘 | |

**G18 为什么要看图自己的 MediaBox**：`main.tex` 里 14 张图全是 `width=1.0\linewidth`，缩放比恒 1.0，
图内超出画布 416.5 pt 的文字被 PDF **直接裁掉**——读者看到的是断头句（2026_C 第 12 页
`ity utilisation η (dimensionless, = demand/installed cap` 就是这么来的）。主文档版心查不出这件事。
同一道门还查 `get_bboxlog()` 的图元：matplotlib 的 `hatch` 生成 tiling pattern，BBox 远超画布。

**G19 的意义**：`??` 是「判不出」，前面所有门都可能因为缺文件而返回它。若允许 `??` 混过去，
整条链会在「什么都没查」的状态下报完成。这道门把「非软闸门留了 `??`」变成硬失败。

**G20 的意义**：题面之外还有一层信息——同型题往年是怎么解的、哪条路线得过奖、哪条路线在评审笔下死过。这一层不查，建模架构就会凭直觉选一条路线，而那条路线可能正好是往年「看着漂亮但拿不到分」的那条。门只判两件事：有没有查（正文点名了检索器）、查完有没有下结论（VERDICT）。

**软闸门（✅）的含义**：`??` 不拦。进这个集合的只有两类 —— 依赖第三方服务的门（视觉模型额度随时可能用完，算 FAIL 会让整条链永久堵死）、结构上可能不适用的门（题目没有 `TABLE_*`、没用上传模板）。**其余门 `??` 一律算失败**，不许拿「判不出」蒙过去。

G5 与 G12 是互补的，不是重复：G5 管「每个数字有没有登记」，G12 管「每个数字在原始数据里找不找得到」。本项目实测 G5 的 36 条声明全过，G12 仍挑出 127 条未溯源线索（多为中间量）。

---

## 6 时间预算（4 天赛程）

| 时段 | 干什么 | 不许干什么 |
|---|---|---|
| D1 上午 | 读题、判题型、建骨架、抓数据 | 写正文 |
| D1 下午 | 符号表、假设、反证条件、基线模型跑通 | 上复杂模型 |
| D2 | 主模型 + 求解 + 每问初稿结果 | 调格式 |
| D3 上午 | 稳定性三强度、图表 | 加新模型 |
| D3 下午 | 摘要 + 正文成稿、压页 | 改结论 |
| D4 凌晨 | 合规 14 项、对账、编译两遍 | **只改会废稿的项** |

**最后 12 小时只允许改会废稿的项**：页数 / 汉字 / 机构名 / 队号 / 文献格式。
改模型、改数字、加章节都在此之前做完。

---

## 7 17 条反模式（见到就停手）

从 22 篇一等奖里反推出来的"掉档特征"，每条都对应真实论文编号：

| 码 | 反模式 | 实例 |
|---|---|---|
| P1-a | 摘要纯方法清单，零结果 | `apmcm2203180` |
| P1-b | 摘要纯数据堆砌（38 个数字，density 11.48） | `apmcm2201058` |
| P1-c | 摘要结尾零信息（"本文具有重要参考价值"） | `apmcm2307379` |
| P2-a | 无任何验证 | `apmcm2205838` |
| P2-b | 检验章缺失且缺点不指名 | — |
| P3-a | 假设无 justifying（只有"假设 A 成立"） | `apmcm2303763` |
| P3-b | 假设纯编号列表，不写被谁用 | — |
| P4-a | 缺点空转（"模型仍有改进空间"） | — |
| P4-b | 结论强度超过证据 / 排版崩坏 | `apmcm24207218` |
| P4-c | 薄弱项只定性不量化 | `apmcm2213503` |
| P5-a | 图号章号崩坏 | `apmcm24200636` |
| P5-b | 编号回退（先 3.1 后 3.0） | — |
| P5-c | 标题拼写错误 | — |
| P5-d | 断词（"university" 被断成 "univer-sity"） | `apmcm25302425` |
| P6-a | 符号表单位重复或断裂 | — |

---

## 8 这套链的独立性（为什么不产生路径依赖）

| 维度 | 上一代商业工作台 | 本链 |
|---|---|---|
| 技能正文 | 加密胶囊，需账号额度+联网才下发 | 明文，`E:\数学建模\.agents\skills\` 下可读可改 |
| 产物契约 | 藏在加密技能里，拿不到 | 写在 `mmkit/crew.py` 的 `OUTPUT_OF`（13 条）与 `pipeline.py` 的 `GATES`（9 条） |
| 步骤定义 | `templates.json` 只给步骤名 | `pipeline.py` 的 `STEPS`（7 步，带闸门） |
| 检查层 | 加密，只能从 pyd 符号表反推 | 明文：`review_bench.py`（12 条官方判据，每条带 file:line）+ `gauntlet.py`（16 项） |
| 依赖 | 7.5 GB 自带运行时，卸载即失效 | 只依赖 `E:\Mini\envs\mathmodel`（mathmodel 环境）与 MiKTeX |
| 计费 | 账号额度 / 自备 Key | 免费（本机模型 + 免费网关） |

**外部工作台卸载后本链仍完整可跑** —— 已实测：把 PATH 里含该产品名的项全部剔除，
`paper-kit` 的 42 个工具照常运行，`pipeline.py` 的二十道门照常判定。

---

## 9 已知边界（照实记，不许写成已完成）

1. **`pipeline.py` 的 s7（审阅队）依赖 DSH Web GUI 在跑**。GUI 不在时 `crew.list_members()` 报
   `✗ 找不到运行中的 DSH Web GUI`，派单失败。此时可先用 `--skip-dispatch` 跑机器闸门（G1–G8 全部不需要 GUI）。
2. **图内字号 ≥6 pt（G6）对某些 matplotlib 默认设置会 FAIL**。`APMCM2025_C` 实测 `min_pt=2.71`，
   4024 处违规、2990 处单字小于 6pt。根因不是"字号写小了"，而是三处结构性错误：
   `savefig.bbox="tight"` 让每张图导出宽度都不同、`\includegraphics[width=0.86\linewidth]` 再缩一次、
   `\setmonofont[Scale=MatchLowercase]` 把等宽字再缩 0.814 倍。修法：`bbox="standard"` +
   `figsize` 宽度取 `\textwidth/72` 英寸 + `width=1.0\linewidth` + `Scale=1.0`。
3. **`APMCM2025_C\main.tex:52` 的 `\baominghao{APMCM25XXXXX}` 仍是占位**，是 C11 FAIL 的唯一原因。
   该目录是历史作品，保留原状作对账基准，不代填。
4. **`gauntlet` 的 `R-V09 no stale artefact` 会把"数据比代码新 16 小时"判成已知开放项**。
   这不是错，是提示：数据是用旧版代码生成的，需要重跑或说明。
5. **R-V14 的 6.0 pt 边界要留余量**：PDF 里 6.0 pt 常被写成 **5.98 pt**，正好落在 `<6.0` 判据外。
   给到 6.2 以上才稳。LaTeX 表格 `\small`（9pt）里的数学下标会落到 5.98 pt —— 表格不加字号
   （正文 10.5 pt）下标约 7 pt，是过 R-V14 最省事的办法。
6. **`verify_numbers.py` 必须自己重写 `data/ledger.json`**，不能要求人工同步；且它的 D 段判据
   依赖 ledger 里的 `verdict`，而 `verdict` 又由本轮结果决定 —— 必须写成不动点循环
   （`main()` 里 6 轮，实测 2 轮收敛），否则要跑第二遍命令行才 PASS。
7. **写文件字节数时不能用 `Path.write_text(encoding="utf-8")`**：Windows 会做 `\n` → `\r\n`
   转换，任何"文件自身字节数"的自引用永不收敛。必须 `write_bytes(text.encode("utf-8"))`。
8. **`gauntlet_check.py` 与 `verify_numbers.py` 对同一件事曾用两套口径**（`N claims` vs `claims=N`）。
   最省事的修法是两种写法都打，而不是改其中一方。

---

## 10 从零复现（验收本链用）

```powershell
# 1) 起骨架
$P = 'E:\数学建模\APMCM2026_C'
& $PY "$S\new_paper.py" $P --type C
& $PY "$S\new_verify.py" $P

# 2) 题面进 problem/
Copy-Item 'E:\数学建模\APMCM-PROBLEMS\PROBLEMS\2026_C.txt' "$P\problem\problem.txt"

# 3) 八步流水线（可随时中断、随时重跑）
& $PY "$S\pipeline.py" $P

# 4) 看结果
& $PY "$S\pipeline.py" $P --status
```

已实测的基线（2026-11-18 终稿，`E:\数学建模\APMCM2026_C`，2026 C 题「创业社区规划与资源配置优化」）：

| 步骤 | 结果 |
|---|---|
| s1 赛题分析 | G1 PASS（`out/00-problem.md` 31,301 B，逐句抄出 15 条"要求你"）；G2 PASS（`NOT-APPLICABLE` + 34 条常量基线） |
| s2 建模求解 | G3 PASS（`out/01-model.md` 29,384 B，34 条外生常量逐条标行号，消解 4 处符号冲突） |
| s3 编程实现 | G4 PASS（`out/02-solve.md` 34,676 B）；G5 PASS（`verify_numbers` 0 failures）；G10 `??`（无 `TABLE_*`，软闸门） |
| s4 图表 | G6 PASS（`figures` pdf=14 png=14，图内 CJK = 0，`mmkit.figfont` 全部 `ok=True`）；G11 `??`（无视觉模型，软闸门） |
| s5 论文撰写 | G7 PASS（`review_bench` 12 项 fail=0 unknown=0）；G12 PASS（`致命=0 条目=2425 已比对=1087 未溯源=127`） |
| s6 编译合规 | `xelatex` 两遍 `[0,0]`，`main.pdf` **96 页**；G8 PASS（**gauntlet 16/16**，fail=0）；G13 PASS（venue **0 项要你处理**）；G14 `??`（无上传模板，软闸门）；G15 PASS（闭包 16 个源文件） |
| s7 评审收口 | G9 PASS，10 人 2 波约 2,940 s，`review/00-plan.md` 37,974 B / 42 项 |

终稿三闸：

| 闸 | 命令 | 结果 |
|---|---|---|
| 对账 | `verify_numbers.py` | `claims=36 declared=36 checked=36 failures=0 verdict=PASS` |
| 合规 | `gauntlet_check.py` | **16/16 PASS**，`R-V01 body=29`、`R-V03 body cjk=0`、`R-V14 violations=0` |
| 投稿 | `submission_gate.py . --only venue` | **0 项要你处理**，3 提醒 / 4 通过 / 1 不适用 |
| 摘要 | `review_bench.abstract_stats` | `words 447 / numbers 39 / density 8.72 / verdict_words inside`（区间 327–449） |

对账基准（16 篇一等奖，`refs/official_standard.json`；`pct` = 在 16 篇里的百分位，`G.G.band()` 现算）：

| metric | 本项目 | p25 | 中位 | p75 | pct | 判定 |
|---|---|---|---|---|---|---|
| words | 10,459 | 6,386 | 8,228 | 10,910 | 68.8 | inside IQR |
| abstract_words | 435 | 324 | 374.5 | 431 | 81.2 | ABOVE |
| abstract_numbers | 10 | 0 | 2.5 | 8 | 87.5 | ABOVE |
| abstract_density | 2.30 | 0 | 0.73 | 2.21 | 75.0 | ABOVE |
| distinct_numbers | 383 | 55 | 75 | 117 | 93.8 | ABOVE |
| pct_mentions | 81 | 7.5 | 16 | 28.8 | 93.8 | ABOVE |
| density_per_100w | 3.66 | 0.56 | 1.16 | 1.69 | 87.5 | ABOVE |
| sections | 14 | 8.5 | 13.5 | 18.3 | 50.0 | inside IQR |
| subsections | 43 | 24.8 | 28.5 | 34.8 | 87.5 | ABOVE |
| figures | 15 | 9.75 | 14.5 | 24.3 | 50.0 | inside IQR |
| tables | 9 | 1 | 4 | 6.25 | 87.5 | ABOVE |
| equations | 19 | 9 | 17 | 33.3 | 50.0 | inside IQR |
| references | 8 | 5.75 | 7.5 | 11.3 | 50.0 | inside IQR |

**"ABOVE band" 不是问题**：一等奖论文里数字密度高的那几篇本来就在上界外，`R-V07` 只要求两侧都测到、
不要求全部落在 IQR 内（本项目 `BELOW=[]`，无一项偏少）。

特征覆盖：`has_assumption` 6（16 篇 100%）、`has_limitation` 3（87.5%）、`has_software` 3（75%）、
`has_sensitivity` 4（68.8%）、`has_robust` 5（56.2%）、`has_provenance` 1（6.2%）全部达标；
`has_neural` / `has_error_metric` / `has_ci` / `has_sklearn` 为 0 —— 这四项在 16 篇里的出现率是
43.8% / 37.5% / 31.2% / 18.8%，属"可选加强"而非必备（本题是确定性优化，没有可训练模型，
硬加神经网络反而失真）。

---

## 11 这一轮改稿改了什么（可复用的经验，不是过程记录）

`s7` 审阅队出了 42 项（F 级 8 / J 级 16 / K 级 10 / Z 级 8）。全部修完后，真正有价值的是这九条：

1. **自指数字必删**。摘要写「36 checks / 1,704 tokens / pass」，而 `verify_numbers` 一跑就把它推翻 ——
   任何"检查自己"的数字都会被下一次运行改写。改成不带数字的表述，或让生成器输出（见 `gen_index.py`）。
2. **两种口径不能共用一个词**。`42-run sweep` 与 `30 feasible runs` 混用，读者会以为有一半被藏起来。
   凡分母，第一次出现就写清「42 runs, of which 30 stay integer-feasible」。
3. **松弛值不能当可达值写**。LP 上限 6.0476 与整数格最好 6.0396 差 0.008，说成"可达到 0.86% 增益"
   就是假命题。必须分开写「天花板 0.86%、其中 0.73% 在整数格上可达」。
4. **阈值要标明是哪条路径上的**。`4.506%/yr` 是 W=793 的需求增长率阈值，`4.608%/yr` 是 W=800 的；
   只写一个数而不说在哪条路径上，读者无法复现。
5. **图注只能写图上真有的东西**。五处图注写「hatched cells」「the marker is」「the vertical rule marks」，
   而图上既没有 hatch 也没有 marker —— 这类错误比排版错更伤，因为它在骗读者的眼。
6. **同轴多柱必须同量纲**。比值 / 万元 / 百分比混在一条轴上，必然有一类被压成 0.1 pt 的细线。
   要么 `twinx()`，要么拆面板。
7. **图例不进坐标区**。`fig.legend(loc="lower center", bbox_to_anchor=...)` 占画布底部一层，
   再用 `bottom=` 给 xlabel 与图例之间留两层间距。
8. **`sharey` + `set_yticks([])` 会连主图刻度一起清掉**。参数名会全部消失且不报错 —— 排查时先怀疑这个。
9. **字号 6 pt 是硬判据**，而 PDF 里 6.0 pt 常写成 5.98 pt。给到 6.2 以上才稳。表格里的数学下标
   还会再降两档（`\footnotesize` 之后 4.98 pt），必须在导言区用 `\DeclareMathSizes` 按 `\f@size`
   的**精确十进制值**重声明（本文档实测 `10.53937` / `9.03374` / `7.52812` / `6.52437`，写 `{12}`
   或 `{7.5}` 都匹配不上）。
10. **附录里的源码也是正文**。`venue_submission_check` 会把 `\lstinputlisting` 印出的中文逐页算进
    「英文稿里的中文」，也会把代码里的 `[...]` 当占位符。两条修法：源码里的字符串改成英文（或
    `\uXXXX` 转义保住语义），占位正则加「含代码标点 / 英文词少于 2 个」的排除。
11. **`hatch` 会污染出栏检查**。matplotlib 的 tiling pattern 在 PDF 里 BBox 远超画布，视觉被裁
    但 `get_bboxlog()` 数得到。改用 `linestyle=(0,(2.2,1.4))` + `alpha=0.40` 虚线描边。
12. **enumitem 的列表标签会伸出左版心**。`apmcmthesis.cls` 把 `labelwidth` 定成 2em，而 `(Q1)`
    比它宽；手写 `\settowidth{\labelwidth}` 会被覆盖，必须 `\begin{enumerate}[leftmargin=*, align=left]`。
