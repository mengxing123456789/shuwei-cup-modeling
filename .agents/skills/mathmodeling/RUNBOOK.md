# RUNBOOK —— 拿到新赛题后，照这个顺序干活

**这份文档是给 agent 读的唯一入口。** 你（agent）被交来一个赛题目录（里面有一个官方题目 PDF、附件数据、可能还有 `main.tex` 半成品），从这里开始，按 §1 的顺序读文件、按 §2 跑命令、按 §3 派小队，直到 §5 的验收全绿。

**你不需要先读工作区里所有文件。** §1 里的每个文件都标了"何时读、读多少"，按需读，不要通读；`APMCM-PITFALLS` 的四份报告加起来 200 KB，只在遇到对应症状时定点查。

---

## 0 三十秒版本

```powershell
$P  = "E:\数学建模\<本题目录>"               # 本体怎么叫都行
$MM = "E:\数学建模\.agents\skills\mathmodeling"
$PY = "E:\Mini\envs\mathmodel\python.exe"     # 数值/画图/torch 都用它
$MP = "D:\Python\python.exe"                  # 只用来画图（见 §2.4 的已知故障）
$env:PATH = "E:\MIKTEX\miktex\miktex\bin\x64;$env:PATH"

& $PY "$MM\scripts\new_paper.py" $P --type C   # ① 起骨架（题型见 §1.2）
& $PY "$MM\scripts\new_verify.py" $P           # ② 起对账器 + 四个代码骨架
& $PY "$MM\scripts\gauntlet_check.py" $P       # ③ 随时体检（现在一定是 FAIL）
```

然后按 §3 派小队，每波结束后回到 §5 跑验收。

**不许跳过的三件事**（顺序有讲究）：
`new_verify.py` 必须在写正文之前跑 —— 它扫的是 `data/*.json`，正文里的数字是照着 JSON 写的；
反过来先写正文，你就没有可对账的基准，最后只能人工肉眼比。
`--type` 选错族也别回头改，章序列错了只是排布难看，结论不受影响；改的成本远高于收益。

---

## 1 读取顺序（严格按序，前一步没结论不要读下一步）

### 1.1 第一步：只有题面和附件，别的先别看

| 顺序 | 读什么 | 读多少 | 读它回答什么 |
|---|---|---|---|
| 1 | 本题目录下的官方题目 PDF（`problem.pdf` 或类似名字） | 全文，逐句 | 每个小问"要求你"做什么 |
| 2 | 附件数据的表头 + 前 20 行 + 总行数 | 只读这些 | 有没有缺失、单位、时间跨度 |
| 3 | 本文件 §1.2 题型表 | 只看一行 | 该用哪套章骨架 |

**读完必须能回答三件事，否则重读：**
1. 一共几问，每问的交付物形态（数值 / 方案 / 排序 / 预测 / 机制）。
2. 数据是本地的还是要去外部抓（`C/D` 型常要外部官方数据，`A/B` 型基本只用附件）。
3. 哪一句话最容易被读错（写成"读者会以为 X，实际是 Y"）。

### 1.2 题型 → 骨架（第一次选型就定，后面别换来换去）

| 题号 | 题型 | 骨架族 | 标志性方法 |
|---|---|---|---|
| A | 图像 / 几何 / 工程测量 | A-α 逐问四件套 | 预处理、分割、Hough、CNN |
| B | 物理 / 工程优化 | B-α 机理章 + 问内五件套 | 多目标、微分方程、元启发 |
| C | 数据 / 统计 / 政策 | C-α 数据章前置 + 问内三段 | 回归、ARIMA、计量、博弈 |
| D | 组合 / 整数 / 前沿 | D-α 一模型一章 | 整数规划、QUBO、退火、SVM |
| E | 聚类 / 时序（2022 独有） | E-α | 聚类、时序四步检验 |

依据：16 篇英文一等奖实测，A 3/4、B 4/4、C 4/4、D 2/3、E 1/1 各自用同一族骨架。详见 `templates/PAPER-TEMPLATE.md` §"五族章序列"。

### 1.3 第二步：写结论之前，只读这两份

- **`templates/THINKING-CANVAS.md`** —— 填空式路线图，11 节，每节末尾一个"门"。**填到第 4 节（"什么结果会让你改主意"）再动代码**，这一节救过本项目的结论（零关税从 −1.06 bn 纠正到 −0.32 bn，根因是基数错配）。
- **`templates/PAPER-TEMPLATE.md`** —— 按 §1.2 选的族，只读那一族。`new_paper.py` 已把它写成 `main.tex` 的章节骨架，多数时候你只需要在看不懂某节该写什么时回来对照。

### 1.4 第三步：只在撞上症状时定点查（不要通读）

`APMCM-PITFALLS/SUMMARY.md` 是总索引（2 KB，先读它），再按症状跳到：

| 症状 | 查这个文件的哪一段 |
|---|---|
| 编译报错 / 编码乱码 / 环境不对 | `01-env.md`（P-E01…P-E21） |
| 结果和预期反了 / 口径对不上 / 结论不稳 | `02-modeling.md`（P-M01…P-M64） |
| 页数超了 / 摘要没数字 / 图表太多 | `03-writing.md`（P-W01…P-W15） |
| 想不出创新点 / 不知道一等奖长什么样 | `04-award-patterns.md`（五族骨架、17 条反模式 P1-a…P7-a） |

每份 `.md` 旁边都有同名 `.json`，字段固定为 `id/title/symptom/rule/check/verified`，写代码做自动检查时读 JSON 更方便。

### 1.5 第四步：规则总表（写正文时随手查）

`RULES.md` —— 75 条硬规定，五族：`R-E`(19 环境) / `R-M`(17 建模) / `R-T`(6 训练) / `R-W`(12 撰写) / `R-V`(21 验收)。每条三段：**【规定】【为什么】【验证】**。**改规定必须同时改 `scripts/tests/test_rules.py`**。

### 1.6 第五步：方法论（需要时读，不必按序）

| 文件 | 何时读 |
|---|---|
| `modeling.md` | 建模阶段（符号表、假设、惰性检验、口径坑） |
| `training.md` | 要训练代理模型时（先算"精确求解 × 次数"是否可行） |
| `writing.md` | 动手写正文前（摘要四段式、压页唯一有效手段） |
| `THINKING.md`（90 分钟解题流程） | 时间紧时照它走 |
| `SKILL.md` | 想知道有哪些现成工具/命令，一张表 |

---

## 2 起步三命令 + 定期体检

### 2.1 起骨架

```powershell
& $PY "$MM\scripts\new_paper.py" $P --type C
# created <dir>\main.tex  type=C  sections=7  blanks=70
```

会建 `code data figures tables logs refs` 六个目录，拷 `apmcmthesis.cls/.cfg`（官方 cls 有 `\CJK` 未定义 bug，拷的是修过的 donor 版）、`refs/official_standard.json`、`refs/award_text/`（基准带靠它算，别删）。

### 2.2 起对账器（**在写正文之前**）

```powershell
& $PY "$MM\scripts\new_verify.py" $P
# wrote <dir>\code\verify_numbers.py  (N numeric leaves sampled from M file(s))
```

它扫 `data/*.json` 里的每个数值，生成"正文里必须能找到这个数"的断言表，并补四个骨架 `code/fetch_data.py`、`code/model.py`、`code/make_figures.py`、`data/ledger.json`（**已存在的绝不覆盖**）。没有 `data/*.json` 时它会警告并写出一个会 exit 2 的空壳——那是"拒绝给出假通过"，不是坏了。

### 2.3 体检

```powershell
& $PY "$MM\scripts\gauntlet_check.py" $P
```

14 项，退出码 0 = 全过。前 8 项是废稿级硬项（正文页数 / 单一分母 / 页码连续 / 零汉字 / 零机构名 / 队号 / 套话 / 文献类型标记 / 引用率 / 前置页顺序），后 6 项是对账与基准带。

**踩过的坑：** 报 FAIL 之前先看第 1 项 `paper resolved` —— 它会拒判草稿（`main.pdf` < 150 KB），并提示"把论文目录当参数传进去"。同一个"选错被检对象"的坑在端到端测验里踩了四次。

### 2.4 已知环境故障：mathmodel 的 matplotlib 画不了图

`E:\Mini\envs\mathmodel` 的 matplotlib **3.11.2 一 `canvas.draw()` 就硬崩**（退出码 −1066598273 = 0xC06D007F，Windows 事件日志 `KERNELBASE.dll … 0xc06d007f`）。import 正常、`Figure()` 正常、`FigureCanvasAgg` 正常、`plot()` 正常，只有真正绘制必崩；`font_manager` 也正常。换配置目录（`MPLCONFIGDIR` 指向空目录）无效；`D:\Python` 的 matplotlib **3.11.1 完全正常**。

**所以：画图一律用 `D:\Python\python.exe`**（它有 numpy 2.5.1 / scipy 1.18.1 / pandas 3.0.5 / matplotlib 3.11.1 / sklearn / statsmodels，**没有 torch**）。数值与 torch 训练仍用 `E:\Mini\envs\mathmodel\python.exe`。出不了图时先试这条，不要重装 matplotlib。

> 待办：matplotlib 3.11.2 与 Windows 的兼容性还没定论，重装未尝试（磁盘紧张）。若哪天修好，把本节改成"两条都可"，并在 `RULES.md` 的 R-E 系列加一条验证命令。

### 2.5 编译

```powershell
cd $P
& xelatex -interaction=nonstopmode main.tex
& xelatex -interaction=nonstopmode main.tex      # 必须两遍：第一遍 LastPage 未解析，页眉会印 "Page 1 of ??"
```

`latexmk` 不可用（`MiKTeX could not find the script engine 'perl'`）。日志是普通 UTF-8/ASCII，**不要**按 UTF-16 读（只有 PowerShell `*>` 重定向的产物才带 `FF FE`）。

---

## 3 派小队（13 人，8 波）

### 3.1 名册与依赖链

| 波 | 成员 | 上游产物 |
|---|---|---|
| W0 | 题目侦察手 / 数据溯源手 | 无 |
| W1 | 建模架构手 | `out/00-problem.md` |
| W2 | 求解与优化手 / 代理模型训练手 / 数值对账手 | `out/01-model.md` · `data/ledger.json` |
| W3 | 图表手 | `out/03-numbers.md` |
| W4 | 论文撰写手 | `out/01-model.md` `out/03-numbers.md` `out/08-figures.md` |
| W5 | 格式合规手 | `out/09-writing.md` |
| W6 | 对抗评审手 / 创新挖掘手 | `out/09-writing.md` `out/03-compliance.md` · `out/01-model.md` `out/03-numbers.md` |
| W7 | 时间与质检手 / 调度手 | 无（收口） |

设计师注意：**创新挖掘手不能等对抗评审手**。两人同波，若让它依赖 `out/04-review.md`，
`test_runbook.py` 会判"依赖了同波产物"而失败（这条测试就是这么加的——第一版确实写错了）。

### 3.2 派单命令

**一条命令跑完八波**（推荐；每波落地才进下一波，没落地就停下）：

```powershell
& $PY "$MM\scripts\run_squad.py" $P                 # 全部八波
& $PY "$MM\scripts\run_squad.py" $P --waves 0-2     # 只跑到 W2（白天赶工时用）
& $PY "$MM\scripts\run_squad.py" $P --dry           # 只看每波派谁、依赖什么，不碰 API
```

`--dry` 的输出就是**依赖链的真相**（从 `crew.DEPENDS` 读），派单前先看一遍，确认没人依赖错产物。

**手写派单**（只派一波、或要改任务正文时）：

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$py = @"
import sys; sys.path.insert(0, r'$MM\scripts')
from mmkit import crew
from pathlib import Path
ws, paper = Path(r'$P'), Path(r'$P')
crew.push_briefs(ws, paper)                                  # 按本题路径重生成 13 份 brief
print(crew.dispatch(ws, paper, ['题目侦察手', '数据溯源手']))   # 派一波，返回 sessionId
print(crew.wait(ws, ['题目侦察手', '数据溯源手'], timeout_s=2400))
"@
[System.IO.File]::WriteAllText("$env:TEMP\crew_w0.py", $py, (New-Object System.Text.UTF8Encoding($false)))
& $PY "$env:TEMP\crew_w0.py"
```

### 3.4 端到端实跑记录（2026-11-11，`E:\数学建模\_e2e\E1`，题面用 6 页规则 PDF 占位）

这条记录的作用是**标定入口的真实能力边界**，不是宣传。它证明的是"命令能跑通、判据能拦住假交付"，**不是**"成员一次就能把题做对"。

| 波 | 成员 | 结果 | 复验结论 |
|---|---|---|---|
| W0 | 数据溯源手 | delivered | 17 条真记录 + 7 个实抓缓存（`data/cache/*.html` 5 个页面 + `rules_2026.pdf` 2.6 MB）+ `ledger.json.bak`；每条有 `source`/`sha256`/`fetched_at`/`status=verified`，另有 `unverified` 2 条（奖项队数、2026 赛题）明写"未公布，不能当官方数字" |
| W0 | 题目侦察手 | 首轮 missing，重派 delivered | 首轮 36 步正常结束却没写文件；重派交付 26,076 B、15 张表、42 个数值、`VERDICT: PASS`。我独立复算：PDF 6 页 / 每页 1 图 / 文本层 0 字符 / 2,656,950 B / sha `f50d011b…` 全部一致 |
| W1 | 建模架构手 | 首轮 blocked，重派 failed | 首轮产物 74 B 写 `BLOCKED: out/00-problem.md`；重派 24,958 B、27 个符号、11 张表、`VERDICT: FAIL`（因题面缺失）。我复算 `ledger.json` 23,406 B / sha `6061e012…` 与其自述一致 |

**这轮挖出来的 4 个真缺陷（都已修，且都有负对照）：**
1. **空壳当交付**：`new_verify.py` 补的 81 B `data/ledger.json` 被 `landed()` 判 True → 加 `crew.stamp()` + `landed(since=)` 要求 mtime 更新。负对照：空壳 False / 派单后重写 True。
2. **字段名咬死**：数据溯源手用 `source` 键，第一版判据只认 `url`，17 条真记录全被判"缺 url" → 判据改为"有出处（`url` 或 `source`）+ `sha256` + `fetched_at`"。
3. **BLOCKED 当没干活**：`BLOCKED`/`FAIL` 是契约内回报，旧逻辑让它空等到超时 660 s（产物 19:54:42 就写好了）→ 新增 `crew.outcome()` 返回 `delivered/blocked/failed/missing`，遇 `blocked` 立即 STOP。
4. **`BYTES` 自报不实**：成员在建文件前先写了 `BYTES 00000` 再没回来改 → 新增首行 `BYTES n` 与磁盘真实字节比对。**第一版检查器自己是假的**：用 `len(txt.encode())` 比 `read_text()` 归一化后的串，永远相等；改用 `p.stat().st_size` 才真能红（负对照：`BYTES 00000` → `首行自报 BYTES 0，实际 38`）。

**复验记录（补）：** W2 三份交付我都自跑过。`数值对账手` 报的两份 sha256（`verify_numbers.py` 27,093 B `4f4aa928cb615d9c`、`main.tex` 3,647 B `a000912cb1a8274a`）与磁盘完全一致；我自己重跑 `code/verify_numbers.py` 得到 `CHECKS 12 FAILED 1 (hard 0, vacuous 1)`、`VERDICT: FAIL`，与它自述一致（正文 0 个数字 → V02 空转，故意 fail-closed）。`求解与优化手` 报的 `results_solve.json` sha `d14cfb53fd9bd607` 我连跑三次都是同一个值，**结构结论（翻转行、网格零可行集、证书一致）可再现**；但它报的单次耗时**不可再现**：同一脚本三次 `median_ms` = 50.04 / 53.74 / 55.92（报告写 53.657）、`total_ms` = 11665 / 12172 / 12817（报告写 12515.443）。**这是本入口最该记住的口径局限**：结构数字要复跑比对，计时数字只能当量级，除非专门做 3 次取中位并写进报告。

**这轮没证明的事**（别把它读成"入口已验证"）：W2–W7 未跑完；题面是占位 PDF 而不是真题，所以成员只能交"题面缺失"级的结论；`run_squad.py` 的 STOP 语义保证"上游缺就停"，但没有自动补派。

**派单纪律（每条都是实测换来的）：**
- **先 `push_briefs`，再 `dispatch`**：成员 brief 里写死了本题的绝对路径与上游产物路径，不重打就会去读别的题。
- **判交付 = 存在 + 派单后被写过 + 内容像真活**。三层判据缺一层就会被骗：
  - 存在：`crew.landed()` 只认 `OUTPUT_OF` 里那一个文件名。实测有成员把内容写进 `out/final-check.md`（17939 B、首行还写了 `BYTES 17939`），契约文件一个没有。
  - 派单后被写过：`run_squad.py` 每波先 `crew.stamp()` 记时刻再派单，`landed(since=…)` 要求 mtime 变新。**这条是端到端第一次跑撞出来的** —— `new_verify.py` 补的 81 B 空壳 `data/ledger.json`（`{"records": []}`）让 W0 报"1/2 落地"，而数据溯源手一行都没写。
  - 内容像真活：`ledger.json` 的 `records` 不能为空、每条要有**出处**（`url` 或 `source`，两种键名都收）+ `sha256` + `fetched_at`；Markdown 产物必须含 `VERDICT:` 行。用例实测：空台账 False、缺 sha256 False、好记录 True、无 VERDICT False。
  - **现场教训**：数据溯源手交了 17 条真记录，键名用的是 `source` 而不是 `url` —— 第一版判据把它全判"缺 url"，会冤枉一个干了真活的成员。判据要盯"有没有可核对的出处"，不盯某一个键名。
- **区分三种"没通过"**：`crew.outcome()` 返回 `delivered / blocked / failed / missing`。`BLOCKED:` 与 `VERDICT: FAIL` 是**契约内的正常回报**，不是没干活：成员已经给出结论，该停下的是人，不是时钟。端到端跑里 W1 的产物 19:54:42 就写好了（`BLOCKED: out/00-problem.md`），旧判据让它空等到超时 660 s。
- **不看会话状态**：有成员 36 步正常结束却没写文件，会话状态骗过人。
- **给短任务**：一个成员一次只派一件能用 100 步内做完的事，长任务拆开派。
- **中文走管道会乱码**：`crew._node()` 收的是原始 bytes 再按 UTF-8 解；成员一律按 **id** 定位而非名字。

### 3.3 复验成员产物（五项，逐条过）

| 项 | 怎么验 |
|---|---|
| 文件 | `Test-Path` + 字节数 > 0，首行 `BYTES n` 与实长一致 |
| mtime | 产物早于源码 = 旧版结论，作废 |
| 数字 | 自己跑一遍它给的命令对账 |
| 可运行性 | 它说"已生成图/已编译"，就真跑一次 |
| 口径 | 问清统计方式（行数含不含空行、分母是谁） |

成员自评 `VERDICT: PASS` **不算证据**，只算主张。

**一个真实的失败样本（来自本项目 R1 日记，可直接照抄它的骨架）：**
`out/06-gate.md` 17938 B，首行 `BYTES 17938`，正文第一行就是被检对象与检查时刻，
倒计时那一段把**命令和它的输出都贴上了**（`hours_left=445.9`、`12h_window_now=False`），
截止来源指到 `APMCM2026/README.md:3` 逐字引用；后面九条格式硬项逐条 PASS/FAIL，
每条都带命令；结尾主动声明"5 个 PASS 里 3 个是空模板自然满足"，最后一行 `VERDICT: FAIL`。
这就是"可复算"的具体样子：**命令 + 输出 + 落点行号**，三者缺一就退化成口头结论。

### 3.5 审阅小队（10 人，2 波）：写完之后怎么被挑错

13 人那支是**生产队**（从题面到成稿）；这一支是**审阅队**，只对**已经存在的稿子**说话。
两支共用同一套 `crew.py`，只是换一张名册：

```powershell
D:\Python\python.exe "$MM\scripts\run_review.py" wave0 "我的论文目录"   # 先写 00-metrics.md，再派 9 人
D:\Python\python.exe "$MM\scripts\run_review.py" wave1 "我的论文目录"   # 总编收口
```

| 波 | 成员 | 产出 | 判据来源 |
|---|---|---|---|
| -1 | **脚本**（不是人）：`run_review.py metrics` | `review/00-metrics.md`（被测件 mtime/sha256 + 四条判据原始输出） | `review_check` / `gauntlet_check` / `figfont` / `verify_numbers` / `freshness` |
| 1 | 合规审查员 / 论文结构审读 / 摘要与表达审读 / 题目契合度审读 / 模型与检验审读 / 数据与代码审读 / **数字对账员** / 图表审读 / 创新性评估 | `review/01…09-*.md` | C1–C12 + 22 篇一等奖 PDF 实测 + 35 份真题 |
| 2 | 改进方案总编 | `review/00-plan.md` | 只读上面九份 + `00-metrics.md`，不新增取证 |

派单**不要**再手写 `crew.dispatch(WS, WS, …)`：第二个参数才是输出根，第一轮两处都传 `WS`，
8 份报告全落到工作区根、`outcome()` 报 8/8 missing。输出根现在由 `review_crew.full_briefs()` 定死在论文目录。

**派审阅队的两条硬经验（都是实测撞出来的）**：

1. **先在 brief 里写"先落盘骨架"**。第一轮 8 人跑 1500 s，只有 5 人落盘；3 个没落盘的
   工具数 180–244、耗时 3485–3599 s，`turnBoundary.openTurnStartSeq` 一直没闭合
   —— 它们不是超时，是**陷在探索里**。交付者只有 75–142 个工具。**任务颗粒度比并发数更要命。**
2. **总编必须收到"不要重新取证"**。第一次派总编，它跑了 12 步 15 工具 209 s 后停在
   openTurn、零字节；把 8 份报告的**字节数清单**塞进 brief、并要求"第 1 个动作就写骨架、
   每写完一节立刻回写"，210 s 就交出 31,639 B / 195 行的 `00-plan.md`。

**审阅队的三条口径纪律**（写进 `review_crew.HOUSE`，违反的结论不算）：

- 引用官方条款必须写 `C编号` + 文件名 + 行号；引用真题写 `文件名:行号`；
- **不许说"一等奖都这样"** —— 要说"22 篇里 N 篇"并给出可复算的提取命令；
- 自己**先证伪取证前提**：`04-fit.md` 开场就声明"`PROBLEMS\` 里没有 2025 题面，
  以下题面判定受二手复原限制"，这比硬判成"论文答偏题"正确得多。

审阅队产出的**定级词表**只有四个，混用就等于没分级：

| 层级 | 含义 | 处置 |
|---|---|---|
| 废稿级 | 触发 C9/C11 这类"unconditionally disqualified" | 不修不得提交 |
| 结论级 | 结论被自己的数据推翻 | 必须改数字或改话 |
| 口径级 | 评委一看就追问，但不改结论 | 批量批注式改 |
| 增强级 | 只提分 | 时间够再做 |

---

## 4 每问的推进模板

对每个小问，严格按这七步，不许跳：

1. **符号与假设**：一符号一义（含单位与量级），假设分"结构性"与"可检验"两类，每类都写"违反了会怎样"。
2. **口径**：先写下"谁和谁比、分母是什么、单位是什么"，再写公式。
3. **先写反证条件**："出现什么结果我就改主意"，写进 `logs/decisions.md`。
4. **由简到繁**：基线模型先跑通并留数，再上复杂模型；**复杂模型必须证明它更好**（留出样本外，同一折、同一指标）。
5. **解的性质**：调用耗时、约束是否 binding（逐来源列，不许只给一个 True）、是否落在搜索网格边界（边界解必须标星 + 放宽网格后的值）。
6. **稳定性三强度**：参数 ±10% 扰动 / 重抽样本 / Sobol 或秩相关；**必须报不利的那一半**（例：排序位移 0 但 top-1 只活 65%）。
7. **写进正文**：结果 + 口径句 + 一条具体局限。

**第 4 步的失败样子**：只跑复杂模型、不跑基线，就没法证明"复杂是必要的"。本项目实测过
反例——某次 LSTM 比 ARIMA 好 3%，但那 3% 全落在同一折的超参噪声里；补跑基线后结论撤回。
**判据**：同一折、同一指标、留出样本外，复杂模型赢超过一个标准差才算赢。

---

## 5 每波的验收门

| 门 | 判据 | 命令 |
|---|---|---|
| G1 题面 | `out/00-problem.md` 存在且能列出每问交付物形态 | 人工读 |
| G2 数据 | `data/ledger.json` 每条都有 `url/fetched_at/sha256`，抓不到的写"未验证"不是 0 | `& $PY code\fetch_data.py` → `N records, 0 without provenance` |
| G3 模型 | 符号表 + 假设 + 反证条件齐 | 人工读 `out/01-model.md` |
| G4 求解 | 交付耗时、binding、边界解三个性质 | 人工读 `out/02-solve.md` |
| G5 对账 | `0 failures` | `& $PY code\verify_numbers.py` |
| G6 图表 | 每图有单位/样本量/口径 | 人工看图 + caption |
| G7 正文 | 正文 ≤ 30 页、摘要 4 段、≥3 个数字 | `gauntlet_check.py` 第 2–4 项 + `writing.md` |
| G8 合规 | 14 项 PASS（队号那一项在填真号前必然 FAIL，属已知豁免） | `& $PY "$MM\scripts\gauntlet_check.py" $P` |
| G9 全员 | 13 份契约产物齐 | `crew.landed()` 全 True |

---

## 6 时间预算（4 天赛程）

| 时段 | 干什么 | 不许干什么 |
|---|---|---|
| D1 上午 | 读题、判题型、建骨架、抓数据 | 写正文 |
| D1 下午 | 符号表、假设、反证条件、基线模型跑通 | 上复杂模型 |
| D2 | 主模型 + 求解 + 每问初稿结果 | 调格式 |
| D3 上午 | 稳定性三强度、图表 | 加新模型 |
| D3 下午 | 摘要 + 正文成稿、压页 | 改结论 |
| D4 凌晨 | 合规 14 项、对账、编译两遍 | **只改会废稿的项**（页数/汉字/机构名/队号/文献格式） |

**最后 12 小时：** 只允许改 §5 G7/G8 列出的会废稿的项。改模型、改数字、加章节都在此之前做完。

---

## 7 交付清单

```
<本题目录>/
  main.tex  main.pdf                 # 论文（两遍 xelatex，正文 ≤30 页）
  ControlSheet（如赛制要求独立控制页）
  code/        fetch_*.py model.py make_figures.py make_tables.py verify_numbers.py
  data/        ledger.json results_*.json
  figures/     *.pdf + *.png（同图两格式）
  tables/      tab_*.tex
  out/         00-problem … 11-dispatch（小队产物，不交付但留证）
  logs/        decisions.md + 编译日志
refs/          参考文献（[M]/[J] 类型标记，≥70% 被正文 cite）
```

2026 赛制还要求一份 **AI 工具使用详情说明**（工具名/版本、用途与阶段、关键交互记录、采纳与人工修改），模板见 `templates/PAPER-TEMPLATE.md` 末尾。

**交付前的最后一分钟清单**（按顺序，每项都要有命令输出）：

1. `main.pdf` 的 `Pages:` 与正文末页页眉数字差 ≤ 附件页数 —— 用 `pdfinfo` + `pdftotext` 两处对。
2. `gauntlet_check.py` 除队号外全 PASS。
3. `verify_numbers.py` 打 `0 failures`，且它的条数是你**真检查过的**条数（不是 0 条的空壳通过）。
4. 每个图文件都有 `.pdf` 与 `.png` 两份，且 `code/make_figures.py` 能原样重跑。
5. `data/ledger.json` 里没有一条 `sha256` 为空。
6. 队号已填（脚手架写的是 `\baominghao{apmcm2699001}`，**提交前必须换成本队真号**；C11 只查"是不是 XXXXX 形状"，查不出"号码是别人的"），文件名按赛制命名（`A<队号>.pdf`）。
7. AI 使用说明 PDF 与论文一起交，内容与实际用过的大模型一致。

---

## 8 反模式速查（见到就停手）

| 编号 | 症状 | 修法 |
|---|---|---|
| P1 | 摘要纯方法清单或纯数据堆砌或零信息结尾 | 四段式 + 每问至少一个数字 + 一条具体局限 |
| P2 | 没有检验结构却写"模型很全面、结果合理" | 必须有检验章或问内检验块，且报数字 |
| P3 | 假设不可检验（"假设数据可信合理"） | 每条假设配 justifying 与"违反了会怎样" |
| P4 | 缺点空转、结论强于证据 | 缺点指名到文件行号与数字 |
| P5 | 图号章号拼写崩坏、编号回退 | 编译两遍后逐页看目录与 `\ref` |
| P6 | 符号/单位重复或离散、用 `•` 导致无法交叉引用 | 符号表唯一、用 `\label`/`\ref` |
| P7 | 小问被"文章化"后失去技术含量 | 政策类小问也必须引用前问的数字 |

完整 17 条（带队号出处）在 `APMCM-PITFALLS/04-award-patterns.md`。

---

## 9 维护这份文档

- 改 §2 的命令 → 必须同步改 `SKILL.md` 的"工具矩阵"。
- 改 §3 的波次或成员 → 改 `scripts/mmkit/crew.py` 的 `WAVES`/`DEPENDS`/`OUTPUT_OF` 与 `squads/main/`、`squads/review/` 下的同名 md（主队 17 份、评审队 13 份），两边都要改。
- 改 §8 → 同步 `templates/PAPER-TEMPLATE.md` 的反模式表。
- 自测：`& $PY -m unittest discover -s "$MM\scripts\tests" -t "$MM\scripts"`（当前基线 `Ran 42 tests … OK (skipped=1)`；skip 的那 1 条是队号占位符，属已知未关闭项）。

### 9.1 文档里的每一句话都必须能被一句话验证

这份 RUNBOOK 有 `scripts/tests/test_runbook.py` 守着，它查四件事：

| 查什么 | 为什么要查 |
|---|---|
| 十个小节骨架都在、正文 > 6000 字符 | 防写到一半被截断 |
| 文中出现的绝对路径与 `templates/`、`scripts/`、`squads/main/`、`squads/review/` 相对路径**全部存在** | 路径错一个字符，agent 就静默走偏；这错我犯过（`refs/official_standard.json` 被写成 `APMCM2026\refs\...`） |
| `new_paper.py` / `new_verify.py` / `gauntlet_check.py` 有 `main()` 与入口守卫 | 防"文档说能跑、其实没入口" |
| `crew` 的 `WAVES` 恰好 8 波、每个成员都有 `OUTPUT_OF`、**依赖只能引用更早的波** | 同波依赖会让下游永远等不到上游 |

**改文档时先跑这条测试**，它比读一遍文档可靠。

**测试本身也要做负对照。** 一条断言"文档写了队号占位符"第一版写成"文档里出现'队号'二字"，
把 §9.2 那一格改成"队号已填"照样 PASS —— **空过了**。正确写法是从 `new_paper.py` 里
正则读出 `\baominghao{…XXXXX}` 的实际内容，再要求它逐字出现在文档里。改完立刻做一次负对照：
改坏一格 → 跑测试 → 必须 FAIL → 还原 → 必须 OK。没做过负对照的断言，只能算"没报错"。

### 9.2 已知未关闭项（照实记，不许写成已完成）

| 项 | 现状 | 后果 |
|---|---|---|
| mathmodel 的 matplotlib 3.11.2 一 draw 就崩 | 换 `D:\Python`（3.11.1）出图，未修 | 画图必须换解释器，见 §2.4 |
| 队号 `\baominghao{apmcm2699001}` | 用户自己填，脚手架给的是"格式合法的假号" | 字形层查不出错号：C11 只判 `XXXXX` 形状与正文自称占位。**这条从"恒 FAIL"变成了"静默通过"**，所以写进了 §7 交付清单第 6 条 |
| `APMCM2025_C` 第 1 页直接是摘要页 | 那篇本身没有 Control Sheet | 它是格式反面教材，别照抄它的前置页 |
| 成员偶尔不写契约文件名 | 靠 `run_squad.py` 停在这一波 + §3.3 复验兜住 | 会浪费一轮派单 |
| `R-V09` 仍报 6 条"产物比脚本旧" | 逐条解释见表 9.2.1；都不需要重跑 | 无（但别把它当"查过了"） |
| **评审报告是快照，会过期** | `review/01-compliance.md` 判"附录缺 13 个脚本"，但附录现在 31/31 齐全（`\lstinputlisting` 实测 31 行、`code/*.py` 实测 31 个） | 照旧报告去"补脚本"会重复补成 61 条；**改之前先在当前树上重量一次**（`review_check.py` / `R-V09`），报告只提供线索不提供现状 |

#### 9.2.1 `R-V09` 那 6 条，一句一条

判据是"**名字 token 一方是另一方子集 + 产物 mtime 更旧**"，它是启发式，不是依赖图。
所以每一行只有两种合法状态：**重跑**，或**说清"旧是应该的"**。下面全部取到了硬证据：

| 配对 | 为什么不用重跑 |
|---|---|
| `data\q1_surrogate_data.csv` ← `code\q1_surrogate_data.py`（16.4 h） | 在 `_repro06` 里整条重跑过，产物 `sha256 = 7BB5537C…AF15C2E` 与 live **完全相同** → 内容没变，只有 mtime 旧 |
| `data\q1_surrogate_data.csv` ← `code\q1_surrogate_train.py` / `q1_surrogate_audit.py` | 这两支是**读**这个 csv 的，方向是"输入早于脚本"，本来就该旧 |
| `data\q1_surrogate_meta.json` ← `code\q1_surrogate_data.py` / `q1_surrogate_train.py` | meta 是 LHS 数据设计的**输入档案**，由 data 脚本写、被 train 读；重跑 meta 会改采样种子，反而破坏 `_repro06` 的可复现链 |
| `data\q1_surrogate_audit.json` ← `code\q1_surrogate_data.py` | audit 是 train 之后的审计产物，脚本改动只动了日志行；重跑输出同值（`06-code` 已核） |
| `data\q1_robust_sigma.json` ← `code\robust_sigma.py`（0.8 h） | 二者是同一支脚本的"跑两次取稳健值"关系，第二次的 mtime 落在 json 之后是正常的写序 |

**判断顺序（别反过来）**：
1. 先看方向 —— 产物是被脚本**读**还是被**写**？被读的旧是对的。
2. 再看内容 —— `sha256` 或关键字段有没有变？没变就不算过期。
3. 只有"被写 + 内容变了"才是真过期（本次 `q1_sobol.json` 就是这一种：431 叶里 407 差，`ST[σ][q_US]` 0.030786 → 0.030591，差 **5.4 倍标准误**）。
---

## 10 练习赛实录：2018A（不看任何优秀论文）

**目的**：在真赛题上把"读题 → 建模 → 出图出表 → 写正文 → 编译 → 对账 → 评审"整条链走一遍，
并且**只用工作区自己的经验、模板、小队**。选 2018 A 的理由是硬的：一等奖语料 22 篇只覆盖
2022–2025，**2018 没有任何获奖论文**，所以"不看"在结构上不可能作弊，而不是靠自觉。

**防线**：`PRACTICE_2018A\NO_PEEK.md` + `code\check_no_peek.py`。判据是"本目录 .py/.md/.tex/.json/.log/.txt
里不许出现 `_award_text`、`历年优秀论文` 等禁区词，也不许出现'一等奖论文/优秀论文'这类行为词"。
负对照实测：正常 `scanned 0 files; forbidden hits 0 / VERDICT: PASS`；故意写一行
`src = r"...\_award_text\2025C.txt"` → `FAIL code\_trap.py:1 [path:_award_text]`。

**规模**（全部可复算，数字在 `PRACTICE_2018A\data\*.json`）：76 段轨迹 × 42 点、74 人可连
（13 人一年内跌倒，17.6%）、25 个平衡特征、0 缺失；三问分别落在 3 个脚本上；
特征抽取 **4.3 ms/段（753× 实时）**；论文 60 页（正文 16 页）。

**这次练习强制暴露并修掉的三处口径错（都已写进 `RULES.md`）**：

| 症状 | 根因 | 修法 | 规定 |
| --- | --- | --- | --- |
| `C7 chinese chars=3207` 判红，但正文一个字中文都没有 | 判据数整个 PDF，官方原文只说 **main body** | `review_bench` 与 `gauntlet` 同时改成"正文页 only，附录汉字单独打印" | **R-V12** |
| `C4 p1 has summary=False`：第 1 页是承诺书 | 模板 HEAD 先 `\makecontrolsheet` 再 `\maketitle`，且后者被 `\let` 成 `relax`（删一行不管用） | `new_paper.py` 的 HEAD 从 `\begin{abstract}` 直接起头 | **R-V13** |
| `R-W04 cite calls=0`，11 条文献一条没引 | 正文写完才补 `thebibliography`，从没回头加 `\cite` | 在方法与出处处补 9 处 `\cite` | **R-W04**（原有） |

**判据自带的两次"抓到我"**（这就是为什么要先写校验、再写正文）：
- `verify_numbers.py` 抓到正文写 `5.4% of the motion files`，实际 2/76 = **2.6%**；
- 同一脚本抓到自己的三处口径错：负数印正数要 `abs()`、`0.9936` 印成 `99.4` 要 ×100、
  `tau_mean` 只在表里不在正文（表由 JSON 直接生成，不该进 claim 表）。

**数据层的四个 API 坑**（都会在别人的代码里重演）：`people` 是 dict 列表且键是
`Name`/`Height`（大写带空格）不是属性；`com_height_ratio(w, height_cm)` 第二位置参数必填；
`np.loadtxt` 撞上每行末尾的制表符要 `rstrip`；`.trc` 没有点名，只能按中位高度切 6 带。

**结论**：练习稿最终 `gauntlet_check.py` **16/16 PASS**、`review_check.py` **11/11 PASS**、
`verify_numbers.py` **108 claims + 5 个区间带 / 0 failures**、`figfont` **0 violations**。这不代表论文能拿一等奖
（体量仍比一等奖带偏小：`figures 9 vs median 14.5`、`equations 5 vs 17` 都在带下方），
只代表**"能不能提交"这一层已经干净**。

## 10.1 第二段：把评审发现真的改进去（2026-11-12）

九份报告（8 名审读员 + 1 名总编）落在 `E:\数学建模\review\`，不是练习稿目录里 —— 审读员的 cwd
是工作区根，而 `OUTPUT_OF` 写的是相对的 `review/0X.md`。`crew.outcome()` 因此把 8 份全报 `missing`，
实际全部已交货。修法是 `mmkit/crew.py` 加 `_resolve(ws, name)`（先 `ws/rel`，再 `ws.glob("*/rel")`）。

**报告里最硬的一条不是文笔，是 build 不一致**：8 份报告都在评审 **10:52 的 PDF**，而 `data/*.json`
是 11:09 的 CoM 修正后才生成的。于是正文的 AUC 0.412 / p 0.0995 / 阈值 0.2313 全是上一代的数。
教训是 `R-V11` 的加强版：**评审之前先确认被测件与数据层同代**（比较 mtime，不比大小）。

**改进去的（每条都跑过它自己的验证命令）**：

| 编号 | 发现 | 改法 | 验证输出 |
| --- | --- | --- | --- |
| J1 | 摘要 `749` 无任何来源（25×74 应为 1850） | 全文改 1850 | `verify_numbers` 绑 `25*n_joined` |
| J2 | `τ_cv` 被当"力矩变异性"，实际恒等于 `CV(d)` | 改名 + 声明恒等式 | `max\|τ_cv−sd/mean\|=0.0` |
| J3 | `bw_p95 = 1+a_z/g` 里 m 被约掉，验不了质量模型 | 写明两个恒等式与"不据此下结论" | 正文 §3.2 |
| J4 | `SEG_MASS` 是单侧值却每带只加一次 → CoM 偏高 | `BILATERAL` 加倍 | CoM 0.618 → 0.548（0.555 为当前值） |
| J6 | 权重 0.266 ≠ 影响 26.6%（TOPSIS 有效贡献仅 12.7%） | 权重与有效贡献并列 | `share_top5` / `share_ratio 6.64` |
| J7 | `AUC=0.412` 被写成 "wrong side" | 写成"安全分/风险分同一信息，看 CI 是否含 0.5" | `1-auc` 与镜像 CI |
| S1 | CRITIC 换权后分级**反转**（论文只报 ρ） | 报 39/74 换级、top-10 重合 4/10 | `extras2.critic` |
| S2 | 99.4% 只在"同批人动权重"成立 | 与受试者重抽 57.1% 并列 | `extras2.resample` |
| C10 | 12 个 Welch 检验未做多重比较 | 加 BH：`q_min=0.244` | `force.bh.q_min` |
| K4 | 摩擦需求三个口径混用 | 0.391 单帧 / 0.244 最大个体 p95 / 0.134 队列中位 | `force.mu.*` |
| K2 | "640× 实时"只算抽取 | 加 `code/timing.py`，端到端 8.7 ms = **368×** | `timing.json` |
| C9 | 雷达图注把家族强弱说反 | 用 `extras2.family_profile` 的实测值重写 | stability 0.261 > spatial 0.098 > smooth 0.058 > posture 0.021 |

**这一轮又抓到尺子自己的四处错**（都写进了规定）：C7 数了附录汉字（`R-V12`）、
章节正则漏 `4 . 3 . 1` 与 `XII.`（`R-V15`）、附录锚点没有字母形态（`R-V15`）、
`_pick_pdf` 按字典序选中 `ai_usage.pdf`（`R-V10`）。
**顺序永远是：先证明尺子量得出已知答案，再用它量论文。**

### §10.2 第二轮：合规复审判 4 条废稿级，全部是"纸面工序"
报告 `E:\数学建模\PRACTICE_2018A\review\01-compliance.md`（23,285 B，223 行，11:44:52）对 11:32 那份 68 页 PDF
给出 4 条 FAIL。**先注意它读的是旧 PDF**：定稿是 72 页（补两个 listing 后），这正是"报告是快照"
（R-V11）的又一次现身。逐条修法与实测：

| # | 判据 | 报告怎么说 | 改法 | 修后实测 |
|---|---|---|---|---|
| 1 | C11 | 正文 p18 印 `the identifier APMCM18PRAC1 is deliberately not a valid team number`，字形正则 0 命中 | 删该句，全篇只留 `apmcm1899001` | `self-declared invalid identifier in body=0`；PDF 里搜 `APMCM18PRAC1` 为 False |
| 2 | C9 | 附录 11 个 listing，`export_annex1.py`（Appendix B 第 1 步）与 `timing.py`（摘要 4.2/4.5/368/757 的生成者）都没印 | 补两个 `\lstinputlisting`（11→13）+ Appendix B 加 `timing.py` 步 | `listings=13`，`whitelist` 齐 |
| 3 | C3 | 交付件名 `main.pdf`，官方要"题号+队号" | 编译后复制成 `A1899001.pdf` | 630,135 B |
| 4 | C5 | p2 目录页页眉是 `CONTENTS`×2（无队号无页码） | `\pagestyle{mainmatterstyle}` 提到 `\tableofcontents` 之前 + `\thispagestyle{mainmatterstyle}` | p2 头部 `Team # apmcm1899001 … Page 2 of 70` |

定稿：`main.pdf` 72 页、`body=19`（附录 A 首页页眉分子）、`review_check` 11 项全 OK / PASS、
`gauntlet_check` 16/16 PASS、`verify_numbers` 108 claims + 5 bands / 0 failures、`figfont` 0 violations。
**新规定 R-V17**（语义占位）由这次事故生成。

## 10.3 这一轮的教训变成了什么（2026-11-12，反馈闭环）

练习赛跑完后，改的不是"文笔"，是**四件会让下一轮少踩一次的事**。每条都附了验证方式。

| # | 改了什么 | 为什么（来源事故） | 怎么验证 |
|---|---|---|---|
| 1 | 新增 `scripts\run_review.py`，派单**前**先写 `review\00-metrics.md` | 8 个审读员各自重跑同一组命令，报告里同时出现 68 页与 72 页两种口径；3 条"废稿级"其实评的是我改之前的 PDF | `run_review.py metrics <dir>` → 文件里有 mtime/sha256 + 四条判据原始输出；数据层比 PDF 新时自己打 WARNING |
| 2 | 评审队 9 人 → **10 人**，加 `数字对账员`（输出 `review/09-numbers.md`） | 摘要印过 "749 feature values"（真值 1850 = 25×74），而 749 在任何 JSON 里都不存在；只有"抽 10 个数逐个复算"才会现形 | `run_review.py team` → `members_read_back=10`；brief 让 09 号先跑 verify_numbers 再抽样 |
| 3 | `review_crew.full_briefs()` 的输出根从 `ws` 改成 **`paper`** | 第一轮 8 份报告全落到工作区根 `E:\数学建模\review\`，`outcome()` 报 8/8 missing | `full_briefs(ws, paper)` 打印的 `【你的输出】` 必须在论文目录下 |
| 4 | `new_paper.py` 的骨架从"只有 main.tex"扩到**目录 + 五个会被评审要的文件** | 空目录交上去是常见输法：没有 `review/` 就没有报告落点，没有 `BUILD.md` 就没有提交自检表，没有 `verify_numbers.py` 就没有对账入口 | `new_paper.py _smoke\P11 --type A` → 生成 `NO_PEEK.md` `BUILD.md` `review/README.md` `code\check_no_peek.py` `code\verify_numbers.py`，两个桩都能跑通 |

**第 2 条的连带修正**：`review_check.py` 的 C11 必须是两层（字形 `XXXXX` + 语义"正文自称不是有效队号"），
因为练习稿把占位写成了 `the identifier … is deliberately not a valid team number`，字形正则 0 命中（见 R-V17）。

**第 4 条的连带修正**：脚手架自带的 `check_no_peek.py` 一开始扫自己 → 8 处命中、永远 FAIL。
规则文档与判据本身必须进 `EXEMPT`，行为词只收"指向某个获奖答案"的短语（裸的"照抄"会命中"别照抄键名"）。
负对照实测：新目录 `forbidden hits 0 / PASS` → 放入 `src = r"…\_award_text\x.txt"` 后 `FAIL code\_trap.py:1` → 删掉恢复 PASS。

### 10.4 2026-11-12 UI 事故：名册写空、brief 钉在夹具上

用户指着截图问："数学建模小队里面的内容有点不对，评审小队啥也没有，这两个是不同的，怎么混了"。
复查结论：**没有混编**（建稿队 13 人 / 评审队 10 人，名字无交集），但有三处真缺陷：

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | 评审队 10 人 brief 全 0 字节、简介空 | `run_review.py team()` 只发 `{name, permission}`，`POST /member` 是整条覆盖 | 名册带 `brief` 一起发；读回 `min(brief_len)>0` 才算成（R-V20） |
| 2 | 建稿队 13 个 brief 指向 `_e2e\E1` | `full_brief` 用的 paper 是冒烟夹具 | 新增 `crew.refresh_team(ws, paper)`，重推到真实论文目录 |
| 3 | 两支队都没有简介 | `create_team` 不支持 `description` | JS 模板加 `description`，已存在则 `POST /team` 原地更新 |

复核读数：建稿队 `n=13 desc_len=247 min_brief=575 zero=[]`；评审队 `n=10 desc_len=334 min_brief=1844 zero=[]`。
测试 `Ran 45 tests OK`（新增 `TestRosterNeverBlanks` 三条）。
教训一句话：**"界面上看起来什么都没有"往往是写入约定错了，不是内容错了** ——
upsert 语义下，少发一个字段等于把那个字段清空。

