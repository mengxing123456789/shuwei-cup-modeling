# 数学建模工作台（APMCM / 国赛）

一道赛题从读题到交稿的完整工作台：规定、可跑的检查、模板、小队。
所有数字来自本工作区 `APMCM2025_C` 的真实赛程，不是通用建议。

## 三十秒上手

**新赛题请先读 `WORKFLOW.md`**（八步流水线，一条命令跑到交稿，可断点续跑），
`RUNBOOK.md` 是它的叙事版（为什么这么排、踩过哪些坑），本文件只当工具清单用。

```powershell
# 0) 最省事的一条命令：骨架 → 八步二十门 → 交件（不做决策，门不过就停）
E:\Mini\envs\mathmodel\python.exe scripts\run_all.py "我的论文目录" --type C --problem "题面.txt"
#    = new_paper.py（没骨架时）+ 写 problem/problem.txt + pipeline.py + 复制成 题号+队号.pdf + 三闸终检
#    任何门不过就停，把门名/行号/理由打出来；修完重跑同一条命令（已过的步骤不会重派）

# 0b) 分步用同一条流水线（s1 赛题分析 → s8 评审收口），每步带机器闸门（共 20 道）
E:\Mini\envs\mathmodel\python.exe scripts\pipeline.py "我的论文目录"           # 从头跑到尾
E:\Mini\envs\mathmodel\python.exe scripts\pipeline.py "我的论文目录" --status   # 看做到哪
E:\Mini\envs\mathmodel\python.exe scripts\pipeline.py "我的论文目录" --step s3  # 跑到 s3

# 0c) 视觉审查通道（G11）：本机 magpie 的免费 VL 模型实测 429，需要一把有额度的 key
E:\Mini\envs\mathmodel\python.exe scripts\set_vision.py --show
E:\Mini\envs\mathmodel\python.exe scripts\set_vision.py --api-key sk-xxxx --model gpt-4o-mini

# 1) 开一篇新论文（复制骨架，填空项都是 <<…>>）
E:\Mini\envs\mathmodel\python.exe scripts\new_paper.py "我的论文目录" --type C

# 2) 起对账器 + 四个代码骨架
E:\Mini\envs\mathmodel\python.exe scripts\new_verify.py "我的论文目录"

# 3) 随时自检（16 项，退出码 0 = 全过）
E:\Mini\envs\mathmodel\python.exe scripts\gauntlet_check.py "我的论文目录"

# 3b) 交稿前总闸：规则自检 + 投稿前体检（+ 可选写作规则）一次跑完
E:\Mini\envs\mathmodel\python.exe scripts\submission_gate.py "我的论文目录"

# 4) 一条命令跑完 18 人 10 波（每波落地才进下一波；--dry 只看依赖链）
E:\Mini\envs\mathmodel\python.exe scripts\run_squad.py "我的论文目录" --dry

# 5) 改过规定就重跑测试（当前基线：Ran 64 tests, OK）
E:\Mini\envs\mathmodel\python.exe -m unittest discover `
    -s .agents\skills\mathmodeling\scripts\tests `
    -t .agents\skills\mathmodeling\scripts
```

### 门的三种结果，别混着看

| 标记 | 含义 | 拦不拦 |
|---|---|---|
| `PASS` | 判过 | 不拦 |
| `FAIL` | 判不过（有具体理由与行号） | **拦** |
| ` ?? ` | 该判却没判出来（工具崩了、超时、缺参数） | 软闸门不拦，其余拦 |
| ` NA ` | 结构上不适用（本题没有 `TABLE_*`、没上传模板、人写的审计报告比稿子旧 >5 分钟） | 不拦，但 `--status` 单独列一行「不适用（NA，未真判）」 |

`NA` 与 `??` 分开是因为**「本题根本没有这个对象」和「有这个对象但我没判成」是两件事**：
混成一个，前者的项目会永远卡在红门后面，后者的项目会以为自己过了。

### 派单降级：GUI 不在也能干

`pipeline.py` 默认「派单优先」：把这一波交给小队会话。派单失败（GUI 没起、宿主 run 状态卡住）
不中断流程，而是把这一波每人**完整 brief** 落到 `<paper>\logs\briefs\<sN>-<成员>.md`，
状态置 `awaiting-session`。你可以：

1. 在会话里按 brief 直接干完这一波（我就是这么干的）；
2. 再 `pipeline.py <paper> --skip-dispatch --only sN --force sN` 重跑，让闸门判一遍。

`--skip-dispatch` 是同一个通道的显式版：只跑门、不派人。

### 增量评审：每步门全过之后自动叫对应审读员

`s1 题目契合` / `s2 模型与检验` / `s3 数据与代码 + 数字对账` / `s4 口径冲突` / `s5 图表` /
`s6 结构 + 摘要` / `s7 合规 + 版式出栏`。**门没过就不叫**——评一份已知有病的稿是浪费。
`--no-review-each` 关掉它（省时间、省额度）。

## 文件

| 文件 | 什么时候读 |
|---|---|
| **`WORKFLOW.md`** | **执行手册：八步流水线、二十道门的判据、交稿前清单、反模式速查** |
| **`RUNBOOK.md`** | **拿到新题目的第一件事：读它，按它的顺序走（叙事版 + 踩坑记录）** |
| `RULES.md` | 写正文时随手查；75 条（E 19 / M 17 / T 6 / W 12 / V 21），每条有验证命令 |
| `templates\THINKING-CANVAS.md` | 拿到题目的第一小时 |
| `templates\PAPER-TEMPLATE.md` | 决定题型之后（附录按族分） |
| `modeling.md` | 写模型与假设的时候 |
| `training.md` | 要训代理模型/神经网络的时候 |
| `writing.md` | 写正文与摘要的时候 |
| `THINKING.md` | 90 分钟解题流程与四天时间预算 |

## 论文目录长什么样（`new_paper.py` 生成，别自己拼）

```
<paper>/
  main.tex  apmcmthesis.cls  apmcmthesis.cfg
  BUILD.md              ← 从空目录到可提交件的命令序列 + C1..C12 自检表
  NO_PEEK.md            ← 练习赛的禁区清单与判据（负对照做法写在里面）
  code/      数据层、模型、表、图、对账（verify_numbers.py 是骨架，必须填）
  data/      产物只进这里（*_*.json / csv），正文数字一律从这儿取
  figures/   每张 .png+.pdf，图内 >=3 字符的字号 >= 6 pt
  tables/    booktabs .tex，由 JSON 生成，不手抄
  review/    00-metrics.md（脚本写）+ 01..09（审读员）+ 00-plan.md（总编）
  refs/      official_standard.json + award_text/（基准带与此，不给人看）
  problem/   官方题面与附件原件（不许改）
  logs/      每次编译与重跑的原始日志
```

三条硬约定：①**产物只进 `data/`**，正文不许出现"我算出来的"中间值；②**报告只进 `review/`**，
派单脚本已经把输出路径定死在这里（第一轮曾全落到工作区根，`outcome()` 报 8/8 missing）；
③`problem/` 里的原件**只读**，要清洗就另存到 `data/`。
## 坑：报 [FAIL] 前先看被检对象

`find_paper()` 会取工作区里**最新**含 `main.tex` 的目录，于是新建的空模板（如 `_smoke2`）会被选中，
基准带量到 `figures=0`、引用数 0，看起来全是 FAIL。`gauntlet_check.py` 第 1 项会写明
`草稿（main.pdf 不存在或 < 150 KB）`——看到这句就把论文目录当参数传进去。

同一个坑在测验里踩了四次（`_smoke`、`_smoke2`、`T1`）。判据：**被检对象必须是你要交付的那一篇**。

## 坑：三个脚本没有 argparse，别用 `--help` 探参数

`new_paper.py`、`new_verify.py`、`gauntlet_check.py` 都把第一个位置参数当**论文目录**：

- `new_paper.py --help` 会在当前目录真的建出一个名为 `--help` 的论文骨架（实测 type=C sections=7 blanks=70）；
- `new_verify.py --help` 会往那个目录里写 `code/verify_numbers.py` 与四个 stub；
- `gauntlet_check.py --help` 会把 `"--help"` 当目录，报 `[FAIL] paper resolved … 草稿` 0/2 PASS。

要看参数就读源码或本文的用法列，**不要**用 `--help`。

## 工具

| 脚本 | 作用 | 用法 |
|---|---|---|
| **`scripts\pipeline.py`** | **八步流水线主入口**：s1 赛题分析 → s8 评审收口，每步带机器闸门（20 道），可断点续跑 | `pipeline.py <dir> [--status\|--dry\|--step sN\|--only sN\|--force sN\|--skip-dispatch]` |
| `scripts\gauntlet_check.py` | 16 项合规一键 PASS/FAIL | 见上 |
| `scripts\submission_gate.py` | **交稿前总闸**：gauntlet + 投稿前体检 [+ 写作规则]，一张结论表 | `submission_gate.py <dir> [--only venue] [--main main_en] [--with-writing]` |
| `scripts\run_squad.py` | 八波派单一条命令，任一成员未交付即停 | `run_squad.py <dir> [--waves 0-2] [--dry]` |
| `scripts\mmkit\crew.py` | 18 份（评审 13 份）brief 重生成 + 派单 + 等落地 | `push_briefs()` `dispatch()` `wait()` |
| `scripts\new_verify.py` | 由 `data/*.json` 生成对账器 + 补四个代码骨架 | `new_verify.py <dir>` |
| `scripts\run_review.py` | 生成 `review/00-metrics.md` + 派 10 人评审（两波） | `run_review.py metrics\|wave0\|wave1\|status\|team <dir>` |
| `scripts\mmkit\gauntlet.py` | 页数/合规/基准带的实现 | `check_compliance()`、`band()`、`build()` |
| `scripts\mmkit\verify_numbers.py` | 正文数字 vs JSON 对账 | `python code\verify_numbers.py` |
| `scripts\mmkit\inertness.py` | 惰性参数检验 | `inertness.main()` |
| `scripts\mmkit\provenance.py` | 带 sha256 的取数台账 | `Ledger.save/load` |
| `scripts\mmkit\paths.py` | 定位论文目录 | `find_paper()`，认 `MM_PAPER` |
| `scripts\new_paper.py` | 新建论文骨架 | 见上 |
| `scripts\corpus_index.py` | **历年真题/获奖论文/附件语料检索**（195 条，G20 的查证工具） | `corpus_index.py --build`；`--query-file problem/problem.txt`；`--year 2023 --problem B --kind paper --list` |
| `scripts\authenticity_check.py` | **下载件真实性台账**（扫描件/只有表头/打不开一律标出来） | `authenticity_check.py --build`；`--summary`；`--show 2023` |
| `scripts\ingest_data.py` | 数据收件：**核过才进 `data/`**，并写 `data/ledger.json`（sha256+判据） | `ingest_data.py <dir> <file>... [--source "赛方网盘"] [--force]` |

## 交稿前总闸（`submission_gate.py`）

`gauntlet_check.py` 只查「规则有没有被违反」，**不看写作逻辑，也不看投稿格式**。
这两块由 `paper-kit` 技能补上（本机论文质检工具链），`submission_gate.py` 把它们串成一张结论表：

```powershell
# 默认：① 规则自检 + ② 投稿前体检
E:\Mini\envs\mathmodel\python.exe scripts\submission_gate.py "我的论文目录"

# 只跑投稿格式那套（快，查页数/字体/中文/占位/图表出栏）
E:\Mini\envs\mathmodel\python.exe scripts\submission_gate.py "我的论文目录" --only venue

# 扁平布局（main_en.tex / main_zh.tex）要指定主文件
E:\Mini\envs\mathmodel\python.exe scripts\submission_gate.py "...\latex" --only venue --main main_en
```

- **目录约定**：`venue_submission_check.py` 硬编码 `<ws>/paper/main.tex|main.pdf`。本工作区是扁平布局，
  脚本会自动搭一个临时 `paper/` 视图（复制 main.* + figures/tables/.mh + *.cls/*.cfg），跑完即删，不动原目录。
- **写作规则默认不跑**：`academic_writing_check.py` 按学术论文文体判（要有 Limitations 节、Discussion 要与已有研究比较），
  数学建模竞赛论文没这些硬要求，强跑会出假 FIX。要查就先写 `.mh/writing_spec.json`（**必须用 python 写，别用
  PowerShell `Set-Content -Encoding UTF8`——5.1 带 BOM，`json.loads` 会 ValueError → 静默 SKIP**），再带 `--with-writing`。
- **实测基线**（2026-11-18，`APMCM2026_C` 终稿 96 页）：`submission_gate.py . --only venue` →
  **0 项要你处理**，3 提醒 / 4 通过 / 1 不适用；`gauntlet_check.py` → 16/16 PASS；
  `verify_numbers.py` → `claims=36 failures=0`。这三项已全部进 `pipeline.py` 的 s7（G8/G13/G15）。
- 老基线（2026-11-17，留作对照）：`APMCM2025_C` → gauntlet 14/16、venue 3 项要处理（英文稿混入中文、
  代码占位符、12 页元素出栏 ≤2.3pt）；`数维杯\05_模板与工具\latex`（`--main main_en`）→ venue 1 项要处理
  （占位符未填，骨架态预期）、图表出栏 PASS。

### 六道 paper-kit 闸（已接进 `pipeline.py`）

| 门 | 步骤 | 跑什么 | 软闸门 |
|---|---|---|---|
| G10 表格数据 | s3 | `paper_data_check --mode table`（无 `TABLE_*` 则 `??`） | ✅ |
| **G16 口径审计** | s4 | `out/05-caliber.md` 有 VERDICT（同一名词不许被两种算法用过） | |
| G11 视觉审查 | s5 | `data_fig_vision_check`（无视觉模型则 `??`） | ✅ |
| G12 论文数字 | s6 | `paper_data_check --mode pdf`（查数字能否在原始数据里找到） | |
| **G17 附录自指** | s6 | `code_index.tex` 的字节数与磁盘逐个相等 | |
| G13 投稿体检 | s7 | `venue_submission_check`（页数/字体/中文/占位/出栏） | |
| G14 模板核对 | s7 | `template_ingest verify`（无上传模板则 `??`） | ✅ |
| G15 源文件闭包 | s7 | `paper_source_scope`（`figures/` 有无死文件） | |
| **G18 版式出栏** | s7 | 逐张图对 MediaBox（`x1 > W-2.0`）+ `Overfull >10pt` 必 0 | |
| **G19 流水线自检** | s7 | 非软闸门不许留 `??` | |
| **G20 真题对标** | s1 | `out/15-benchmark.md` 有 VERDICT，且正文出现 `corpus_index.py`/`corpus.json`（没查过就不许过） | `corpus_index.py --query-file problem/problem.txt` |

**`??` 在软闸门里不拦，在其余门里算失败。** G5 与 G12 互补：G5 管「数字有没有登记」，G12 管
「数字在原始数据里找不找得到」——本项目 G5 的 36 条全过，G12 仍挑出 127 条未溯源线索（多为中间量）。

## 基准带（16 篇一等奖实测，IQR 判据；数据来自 `refs/official_standard.json`）

下表「本文实测」是 `APMCM2026_C` 终稿（2026-11-18，96 页）由 `gauntlet_check.G.G.band()` 现算的值：

| 指标 | 一等奖中位 | IQR (p25–p75) | 本文实测 | 判定 |
|---|---|---|---|---|
| words | 8,228 | 6,386 – 10,910 | 10,459 | 带内（pct 68.8） |
| abstract_words | 374.5 | 324 – 431 | 435 | 超带（81.2） |
| abstract_numbers | 2.5 | 0 – 8 | 10 | 超带（87.5） |
| abstract_density | 0.73 | 0 – 2.21 | 2.30 | 超带（75.0） |
| distinct_numbers | 75 | 55 – 117 | 383 | 超带（93.8） |
| pct_mentions | 16 | 7.5 – 28.8 | 81 | 超带（93.8） |
| density_per_100w | 1.16 | 0.56 – 1.69 | 3.66 | 超带（87.5） |
| sections | 13.5 | 8.5 – 18.3 | 14 | 带内（50.0） |
| subsections | 28.5 | 24.8 – 34.8 | 43 | 超带（87.5） |
| figures | 14.5 | 9.75 – 24.3 | 15 | 带内（50.0） |
| tables | 4 | 1 – 6.25 | 9 | 超带（87.5） |
| equations | 17 | 9 – 33.3 | 19 | 带内（50.0） |
| references | 7.5 | 5.75 – 11.3 | 8 | 带内（50.0） |

8 项超带，全部落在「更多」一侧（摘要长度、摘要数字数、摘要密度、不同数字数、数字提及数、
数字密度、小节数、表数），5 项在带内，`BELOW=[]` 无一项偏少。
**超带不等于扣分**：`R-V07` 只要求两侧都测到、不要求全部落在 IQR 内。代价是评委读得慢。

## 坑位总账

`E:\数学建模\APMCM-PITFALLS\SUMMARY.md` 是索引：01 环境 / 02 建模 / 03 撰写 / 04 一等奖反推。
遇到报错先在那里按关键词搜，再去 `RULES.md` 看对应规定；规定与测试一一对应。

## 评审（写完之后的第二支小队）

论文写完不等于能交。这支 9 人小队专门挑错，**依据不是"经验"，是真实官方原件**：
2015–2026 共 35 份真题、16 份官方格式规范、22 份一等奖 PDF，全部落在
`E:\数学建模\APMCM-PROBLEMS\`（带 URL + UTC 时间 + sha256），机器判据是 `C1–C12`。

```powershell
> # 合规硬项先自己跑，别等人来告
E:\Mini\envs\mathmodel\python.exe scripts\review_check.py "我的论文目录"
E:\Mini\envs\mathmodel\python.exe scripts\review_check.py --criteria   # 12 条判据 + 原文出处
> # 产物过期（脚本改过没重跑）——verify_numbers 全绿也证明不了
E:\Mini\envs\mathmodel\python.exe -c "import sys;sys.path.insert(0,r'E:\数学建模\.agents\skills\mathmodeling\scripts');from mmkit import freshness,paths;print(freshness.report(paths.find_paper(r'我的论文目录')))"
```

10 人两波：合规审查员 / 论文结构 / 摘要表达 / 题目契合 / 模型检验 / 数据代码 / **数字对账员** / 图表 / 创新评估
→（汇总）改进方案总编。第 7 人是因为 2018A 里"749 个特征值"这种数只有被人**抽样复算**才会现形。

派单只有一条命令（会**先**生成 `review/00-metrics.md` 口径基线，再派 9 人）：

```powershell
> D:\Python\python.exe scripts\run_review.py metrics "我的论文目录"   # 只生成基线
> D:\Python\python.exe scripts\run_review.py wave0   "我的论文目录"   # 基线 + 9 人并发
> D:\Python\python.exe scripts\run_review.py wave1   "我的论文目录"   # 总编收口
> D:\Python\python.exe scripts\run_review.py status  "我的论文目录"
> D:\Python\python.exe scripts\run_review.py team                     # 建/核对 10 人名册
```

`00-metrics.md` 里有被测件的 mtime/sha256 与四条机器判据的**原始输出**；数据层比 `main.pdf` 新时
它会自己打 WARNING。审读员被要求以它为唯一口径基线（报告是快照，R-V11）。
输出路径一律挂在**论文目录**的 `review/` 下——根由 `review_crew.full_briefs()` 定死，不靠派单方自觉。

定级词只有四个：**废稿级 / 结论级 / 口径级 / 增强级**（见 `RUNBOOK.md` §3.5）。

## 小队

`数学建模小队`（team `61cec604-e7fa-4468-9a84-40757e4292c6`），**18 人十波**：
题目侦察手、数据溯源手、**真题对标手** → 建模架构手 → 求解与优化手、代理模型训练手、数值对账手 → **口径审计手** →
图表手 → 论文撰写手 → **版式与出栏手、附录与自指手** → 格式合规手 → 对抗评审手、创新挖掘手 →
时间与质检手、调度手、**流水线运维手**。

`数学建模评审小队`（team `b68d6335-b534-4f4b-aec7-0b2d56b501b8`），**13 人三波**：
11 个审读员并发（合规 / 结构 / 摘要 / 契合 / 模型与检验 / 数据与代码 / 数字对账 / 图表 / 创新 /
**口径冲突** / **版式与出栏**）→ 改进方案总编 → **修复排序手**。

两人的 brief 正文是仓库里的 **31 份 md**：`squads/main/NN-<成员>.md` 与 `squads/review/NN-<成员>.md`。
`crew.full_brief()` 优先读它们，再把当次的 `【本次派单】/【依赖产物】/【你的输出】` 三行拼在最前面——
手写正文里写的是上一次的论文目录，换题靠这三行覆盖。改 brief 就改那 31 个文件，然后

```powershell
$PY = 'E:\Mini\envs\mathmodel\python.exe'
& $PY -c "import sys;sys.path.insert(0,r'E:\数学建模\.agents\skills\mathmodeling\scripts');
from mmkit import crew; print(crew.push_briefs(__import__('pathlib').Path(r'E:\数学建模\APMCM2026_C'),
                                               __import__('pathlib').Path(r'E:\数学建模\APMCM2026_C')))"
```

**写 brief 的通道只有 `/dsh-agents/api/member`**：直接改 `C:\Users\29900\.dsh\dsh-agents\ledger.json`
会被宿主的内存副本覆盖，`GET /state` 看不到改动，且不报错。

```powershell
# brief 全量重推（18 + 13 人）。_push.py 自动探测当前 GUI 端口，不写死。
& $PY 'E:\数学建模\.agents\skills\mathmodeling\squads\_push.py'          # 预览
& $PY 'E:\数学建模\.agents\skills\mathmodeling\squads\_push.py' --write  # 真写
```

用 `squad-runner` 的 `inline.mjs` 取单人 brief 直接当 subagent prompt；
整队跑用 `run.mjs squad 数学建模 "…"`（GUI 的"整队运行"不触发 turn，别用）。


## 数维杯（swmcmthesis）走法 — 与亚太杯的四处不同

数维杯官方模板是 `swmcmthesis.cls`，接口与 `apmcmthesis` 不同：`\zubie{ABCD}` 选
题号、摘要是 `\abstract{...}` **宏参数**（不是 environment）、目录标题是单数
`Content`、页眉是**两行**（`Team # xxx` 与 `Page n of N`）。因此：

```powershell
# 起数维杯骨架（自动带 \zubie、宏式摘要、swmcmthesis.cls/.cfg）
& $PY scripts\new_paper.py <dir> --type A --cls swmcm --team SWBMCM2634892
& $PY scripts\run_all.py  <dir> --type A --cls swmcm --problem-file <题面.txt>
```

机器门已按模板分流（2026-11-19 实测）：

| 项 | 亚太杯 | 数维杯 |
|---|---|---|
| 页数上限 | 正文 <= 30 | **含摘要页与目录页 <= 25**（附录不限） |
| 页眉正则 | 一行式 | 两行式也认（`HEADER_RE` 双分支） |
| 目录标题 | `Contents` | `Content`（单数，已认） |
| 附录锚点 | `A.` / `1.` | `A` + 多空格（`pdftotext -layout` 形态，已认） |

写稿要点（官方 2021 格式规范原文）：**必须英文**；摘要页第 1 页、目录独占第 2 页；
正文每页都要队号与 `Page n of N`；附录必须含**全部源程序**（含软件名与可运行命令），
赛题数据不要放附录；正文与附录都不得出现学校与姓名。
