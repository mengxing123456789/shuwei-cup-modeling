BYTES 21188

# 13-appendix：附录里由产物决定的值

> 角色：附录与自指手。被测件 `E:\数学建模\PRACTICE_2023B`；依赖 `out/09-writing.md`。
> 结论：附录（`main.tex` 第 632–687 行，§B）已经没有「由产物决定却手写」的数字。表内每行字节数、脚本数、总字节、表尾规则、16 枚图注印章、`figures/src` 的 15 份 ASCII 源副本、本文件首行字节数，全部由脚本从磁盘现读；§6 三条关闭条件全绿，全量门禁（gauntlet 16/16、review_check、submission gate sources/venue）也全绿。
> 唯一还像定时炸弹的一处在**正文**（`main.tex:48` 的 `547`），不在本角色权限内，见 §5.1。
> 本文件里出现的「当前值」都是 2026-11-19 22:5x 的读取快照，每条都带复跑命令；脚本一改就重跑命令刷新，不要手改数字。

## 1 三个必做：谁生成、谁守门

### 1.1 代码索引表：字节数不再进正文

| 环节 | 位置 | 作用 |
|---|---|---|
| 角色表 | `code/gen_index.py:46-62` | 15 个脚本名 → 一句 role；表里只可能出现这里有词条的脚本 |
| 逐行读盘 | `code/gen_index.py:98-116`（`:108` `path.stat().st_size`） | 行格式 `\texttt{name.py} & 3,875 & role\\`，字节数现读 |
| 表体 | `code/gen_index.py:119-126`（`:126`） | `HEAD + rows + [r"\bottomrule"]`——表尾由生成文件自己收 |
| 宏 | `code/gen_index.py:129-139`（`:135` `\CodeIndexCount`、`:136` `\CodeIndexBytes`） | 写 `figures/code_totals.tex`，正文只引宏 |
| 守门 | `code/gen_index.py:145-232` | ①`:150-161` 与 `render()` 逐字节比；②`:167-183` 用 G17 正则把每行与磁盘再核一遍；③`:198-231` 接线、表尾重复、宏作用域 |

接线：`main.tex:635` 先 `\input{figures/code_totals.tex}`（在 `:636 \begingroup` 之前，所以三个宏是全局的），`:642-648` 拥有 `\toprule`、表头行与 `\end{tabular}`，`:646` 只有一句 `\input{figures/code_index.tex}`；生成文件拥有 15 行与 `\bottomrule`（`figures/code_index.tex:20`）。图注（`:639`）用的是宏：`the inventory holds \CodeIndexCount{} scripts totalling \CodeIndexBytes{} bytes`。

为什么表尾必须跟着生成文件走：`gen_index.py:21-22` 把原因写在文件头——`\\` 若是 `\input` 文件的最后一个 token，TeX 在表收尾处报 `! Misplaced \noalign`，随后只出 30 页。守门在 `:202-206`：main.tex 在 `\input` 之后再补一条 `\bottomrule` 会被判错。

当前值：`figures/code_index.tex` 1,493 B / 20 行 / G17 可见 15 行；`figures/code_totals.tex` 214 B，两个数值宏为 15 / 242,037（读取时刻见 §4.1）。15 行逐行字节数见 §4.1 的审计块与 PDF 的 Table 9。

负向实测（证明守门不是空转）：给 `code_index.tex` 尾部加一个空格 → `STALE code_index.tex: 21 lines on disk, 20 expected`，exit=1；给 `code/fix_bytes.py` 尾部加一行注释（改字节数）→ `STALE code_index.tex:4`，exit=1。两条都回滚并核对散列（§4.5 的 G1、G4）。

### 1.2 图注印章（seal）：暂存队列 + 统一转义

问题形状：`stamp()`/`header()` 在 `save()` **之前**被调用，而文件名（stem）要到 `save()` 才定；所以不能在 `stamp()` 里直接写盘。

实现：
- `code/seal.py:45-46` 两个暂存字典 `_PENDING_SEAL` / `_PENDING_HEAD`；`:96-105` `stamp()`/`header()` 只入队；`:117-126` `commit()` 出队（`:123-124` pop），`STEM_SEAL[stem]` 在 `:125-126` 逐行过 `tex_escape` 后写 `<stem>.seal.tex`。
- `code/seal.py:48-63` `_TEX_MAP` 覆盖 `& % $ # _ { } ~ ^ +`；`tex_escape` 在 `:64-79` 先按 `" m2"` 切分，再逐字符转义（所以 `mm2` 变 `mm\textsuperscript{2}`，而 `m2` 单独出现不会被误切）；`:80-94` `_unescaped` 是反向扫描器，`:181-203` `check()` 用它验「每行都是转义态」，并要求印章数与 `--expect` 相等。
- 调用顺序：`code/make_figures.py:197-211` 的 `save()` 先写 PDF/PNG，再 `plt.close()`，`:208` 才 `commit(stem, FIGDIR, origin="code/make_figures.py")`，最后打印三个文件的字节数。16 组 `header`/`stamp` 全在各自的 `save()` 之前（如 `:248-249` fig01、`:857-858` fig16），顺序由暂存队列保证，不靠调用者自觉。

当前值：16 枚印章，148–194 B，合计 2,648 B；PDF 里可直接 grep 到 `source: data/results_q1.json; generator: code/make_figures.py`（每个 `.seal.tex` 的第 2 行是 header、第 4 行是图内来源行）。当前印章里真正出现的危险字符只有 `_`（每个数据文件名与脚本名都有）；`%` 与 `m2` 路径目前由 `seal.py --selftest` 的 10 条用例覆盖（`ok 10 escape cases`），没有被真实文案踩到。

负向实测：给一枚印章尾部加一行裸 `_` → `fig01_q1_product_yields.seal.tex:6: unescaped ['_']`，exit=1；把一枚印章移走 → `seals on disk: 15` 且 `--expect 16` 报缺，exit=1（§4.5 的 G2、G5）。

### 1.3 附录源码的语言：ASCII 副本，不是正文 CJK

venue 的 `check_chinese` 逐页扫 PDF 的 CJK；附录里只要印出中文注释就会命中。本题的附录并没有 `\lstinputlisting`（`main.tex` 只有 `:651-683` 一段手写摘录），但提交闭包要求源码随件走，所以源码副本仍需 ASCII：

- `code/mk_appendix_src.py` 把 `code/*.py` 复制到 `figures/src/`，把**字符串与注释里**的非 ASCII 逐字符换成 `\uXXXX`（`:190-206` `convert_file`），并用 `ast.dump` 证明改写前后语法树的值不变。
- 拒转 4 类，宁可报错也不猜：非 ASCII 标识符、bytes literal、f-string 替换域里含反斜杠、token 前置反斜杠（文件头 `:22-37` 的说明）。
- 样例：`code/solve.py:59` `DERIVED_MARK = " [\u6d3e\u751f\u5217]"`；`code/verify_numbers.py:51` `DASH = "\u2014"`。这两个脚本分别有 1,152 / 3,237 个非 ASCII 字符可转（`gen_index.py --audit` 末两行）。
- 当前值：`figures/src` 15 份、274,696 B 全 ASCII、10,964 个非 ASCII 字符被改写；`--quiet --check` exit=0。

负向实测：给 `figures/src/gen_index.py` 尾部加一个空格 → `STALE figures\src\gen_index.py: rerun code/mk_appendix_src.py`，exit=1（§4.5 的 G3）。

## 2 自指数字台账

A 类＝已经是生成物（改脚本后重跑即刷新，不靠人记）；B 类＝正文/报告里手写、当前恰好为真；C 类＝看着像自指、其实不是。

| # | 值 | 出现位置 | 由谁生成 | 复跑命令 | 当前值（2026-11-19 22:5x） | 何时过期 |
|---|---|---|---|---|---|---|
| A1 | 15 个脚本的字节数（脚本名升序） | `figures/code_index.tex:5-19`；PDF Table 9 | `gen_index.py:108` | `python code/gen_index.py` | 3,875 / 2,564 / 3,083 / 30,061 / 1,665 / 1,735 / 15,546 / 33,570 / 9,367 / 19,793 / 3,860 / 31,406 / 7,594 / 23,696 / 54,222 | 任一 `.py` 改动后没重跑 |
| A2 | 脚本数 15 | `code_totals.tex:2` `\CodeIndexCount`；正文经 `main.tex:639,685` | `gen_index.py:135` | 同上 | 15 | 增删 `code/*.py`（新增脚本必须有 ROLE 行，否则 `:111-115` 直接 SystemExit） |
| A3 | 总字节 242,037 | `code_totals.tex:3` `\CodeIndexBytes`；`main.tex:639` | `gen_index.py:136` | 同上 | 242,037 | 任一 `.py` 改动 |
| A4 | 表尾 `\bottomrule` | `code_index.tex:20` | `gen_index.py:126` | 同上 | 存在；main.tex `:646` 之后直接 `\end{tabular}`，没有第二条规则 | 手改生成文件，或把规则搬回 main.tex |
| A5 | 16 枚印章（图注来源行） | `figures/*.seal.tex` | `make_figures.py:208` → `seal.py:117-126` | `E:\Mini\python.exe -X utf8 code\make_figures.py` | 16 枚，148–194 B，合计 2,648 B | 改图、改数据来源、改 `header`/`stamp` 文案而不重跑（见 §5.3） |
| A6 | `figures/src` 15 份 ASCII 副本 | `figures/src/*.py` | `mk_appendix_src.py:190-206` | `python code/mk_appendix_src.py`（生成）/ `--quiet --check`（守门） | 15 份 / 274,696 B / 10,964 处改写 | 任一 `.py` 改动后没重跑 |
| A7 | 本文件首行 `BYTES n` | `out/13-appendix.md:1` | `code/fix_bytes.py:29-39` | `python code/fix_bytes.py out/13-appendix.md` | 不回填进正文——见下方注 | 任何编辑之后 |
| A8 | 页数 | 只在 PDF 页脚（`Page k of 27`），正文只写规则「thirty-page limit」（`main.tex:685`） | `lastpage` + xelatex | `xelatex main.tex`（两遍） | 物理 29 页 = 摘要页+目录 2 页 + 27 编号页；R-V01 body=25 | 重编译；没有手写页数可过期 |
| B1 | `the 547 stored claims` | `main.tex:48` | **无生成器（手写）** | 见 §4.7 | 547（ledger 547、对账 547、tex 145/145、JSON 0 失败） | 任一 claim 增删；**没有任何闸门会红**，见 §5.1 |
| B2 | `claims=547 …` | `out/03-numbers.md:9-10` | `verify_numbers.py` 自己打印 | `python code/verify_numbers.py` | 547 / 547 / 0 | 随脚本自动改，不是炸弹 |
| B3 | `claims=547`、`body=24/总 28 页` | `out/09-writing.md:4,50,51` | 验收记录（人写） | 重跑 verify_numbers + gauntlet | claims 仍 547；**页数口径已过期**：现在 R-V01 body=25、物理 29 | 记录性质，重跑后刷新 |
| C1 | `thirty-page limit` | `main.tex:685` | 规则常量 | — | 30 | 不随产物变 |
| C2 | 附录 A 的区间（8.19–58.17、5.3e-4–0.838 等） | `main.tex:584-628` | `data/results_*.json` → 145 条 needle | `python code/verify_numbers.py` | tex 侧 145/145 命中 | 数据变；由 needle 闸门兜住 |
| C3 | `twelve … combinations`、`fifteen feasible runs`、`sixteen` | 正文各处（如 `:529`） | 实验常数 | 同上 | 参与 145 条中的带小数结果；个位数计数按设计不挂 needle（`verify_numbers.py:158`） | 数据变 |

A7 的注：**不能**在正文里复述这个数。`n = base + len(str(n))` 是自指方程，写进去会让首行和正文互相追着改；`fix_bytes.py:29-39` 的 12 次迭代就是防这个。所以只给命令，数值以命令输出为准。

## 3 本会话动过什么

- 只做核验与一次幂等重建：`E:\Mini\python.exe -X utf8 code\make_figures.py --only fig16`。三个输出（PDF/PNG/seal）重建前后字节数与 SHA256 全同（§4.4），只有 mtime 变；`main.pdf` 仍是当前件（其内容引用的图没有变），gauntlet R-V09「no stale artefact」仍 PASS。
- 建过 `.negtest.ps1` 与 `.negtest/` 做五条负向测试，跑完删除；被临时改动的四个文件与一枚被移走的印章都做了回滚，并逐一核对散列（§4.5 的 `restored=True`）。
- 没有改任何 `.py`、`main.tex`、图注或其它角色的产物；`main.tex` 的接线与 `make_figures.py` 的 `commit()` 顺序是当前状态，本会话未再动。

## 4 证据

### 4.1 索引自审（`gen_index.py --audit` 原样）

```
file                     lines    bytes
code/solve.py             544   23,696
code/check_no_peek.py      67    3,083
NO_PEEK.md                 25    1,290
main.tex                  687   64,777
out/01-model.md           347   24,589
out/02-solve.md           473   38,249
out/03-numbers.md         557   33,837
out/08-figures.md         215   24,270
problem/problem.txt       152    5,470
main.tex: sections 14, subsections 31, placeholders 0, digit tokens outside comments 1624
main.tex: tab:code yes, inputs figures/code_index.tex yes
main.tex: code_totals input at line 635, outside every \begingroup: the macros stay global
main.tex: no CJK after \begin{document}
figures/: 16 pdf, 16 png, 18 tex [...], 51 entries
seals: 16 of 16 figure PDFs have a .seal.tex
figures/src: 15 ASCII copies, 274,696 bytes
code_index.tex: 1,493 bytes, 20 lines, 15 of 15 rows visible to G17
solve.py: 1152 non-ASCII -> convertible
verify_numbers.py: 3237 non-ASCII -> convertible
```

### 4.2 三条关闭条件（§6 的原命令）

```
seals on disk: 16
seal exit=0
row check: 15/15 rows match disk, G17 scan clean
wiring: main.tex inputs figures/code_index.tex and adds no rule of its own
index exit=0
copies in figures\src: 0 written, 274,696 bytes ASCII, 10964 non-ASCII characters rewritten
```

第三条的附带短语扫描：`lines 67` 与 `starting with the ledger build` 全文 0 命中；`fourteen` 只在 `main.tex:529` 命中一次，读原文是「42 次扰动里 14 次只动查询点」的实验计数，不是附录脚本数。附录区间（`main.tex` 632–687 行）内没有任何 `fourteen`/`fifteen`/`sixteen` 字面量，只有 `\CodeIndexCount{}`。

### 4.3 全量门禁

```
gauntlet_check.py  -> 16/16 PASS   (R-V01 body=25; R-V06 claims=547 exit=0; R-V09 no stale artefact)
review_check.py    -> VERDICT: PASS (fail=0 unknown=0)  C9 appendix=True code=True
submission_gate.py . --only sources -> [PASS] 闭包 19 个源文件，figures/ 无死文件
submission_gate.py . --only venue   -> [PASS] 0 项要你处理
```

### 4.4 fig16 幂等重建（seal 管道端到端）

```
BEFORE / AFTER 完全相同
fig16_validation.pdf       2BB8E304…D09B9A   17,228 B
fig16_validation.png       E4CC971B…149853E   91,599 B
fig16_validation.seal.tex  4008F864…DE9AADD07    187 B
[ok] fig16_validation.pdf 17228 B  fig16_validation.png 91599 B  fig16_validation.seal.tex 187 B
```

顺带钉死一个环境事实：同一个 `--only fig16` 用 `E:\Mini\envs\mathmodel\python.exe` 会原生崩溃（Windows fatal exception `0xc06d007f`，栈：`matplotlib\bezier.py:310 __call__` ← `matplotlib\axes\_base.py:2593 _update_patch_limits` ← `make_figures.py:810` 的 `barh`）；用 `E:\Mini\python.exe`（3.14.6，mpl 3.11.2）成功。所以 §7 的图命令写死 `E:\Mini\python.exe`。

### 4.5 负向测试（守门不是空转）

每行都在跑完后把文件字节回滚并用 `Get-FileHash` 核对；`restored=True` 是散列相等。

```
G1 index-stale: exit=1 restored=True :: STALE code_index.tex: 21 lines on disk, 20 expected
G2 seal-escape: exit=1 restored=True :: fig01_q1_product_yields.seal.tex:6: unescaped ['_'] in '_'
G3 src-stale:   exit=1 restored=True :: STALE figures\src\gen_index.py: rerun code/mk_appendix_src.py
G4 script-bytes:exit=1 restored=True :: STALE code_index.tex:4  (on disk: % 15 scripts, 242,037 bytes ...)
G5 seal-missing:exit=1 restored=True :: seals on disk: 15
```

### 4.6 本文件首行的回填

```
E:\Mini\envs\mathmodel\python.exe code\fix_bytes.py out\13-appendix.md
```

`fix_bytes.py:22-39` 读盘 → 改首行 → 写回（LF）→ 再读盘复核，迭代到不动点；数值不在本文件复述（理由见 §2 A7 的注）。读者跑这一条就能验首行与磁盘一致。

### 4.7 547 的只读复算（不写任何文件）

```
E:\Mini\envs\mathmodel\python.exe -X utf8 -c "import sys;sys.path.insert(0,'code');import verify_numbers as v;d=v.load_docs();C=v.build_claims(d);t=v.strip_comments(v.TEX.read_text(encoding='utf-8'));it=v.evaluate(C,t,{str(p.stat().st_size) for p in v.CODE.glob('*.py')});print('claims',len(it),'evaluated',sum(1 for x in it if x['evaluated']),'tex_declared',sum(1 for x in it if x['needle']),'tex_bound',sum(1 for x in it if x['needle'] and x['ok_tex']),'json_bad',sum(1 for x in it if x['ok_json'] is False))"
claims 547 evaluated 547 tex_declared 145 tex_bound 145 json_bad 0
```

`main.tex:48` 的 `547` 此刻恰好为真；`out/03-numbers.md:9-10` 同值。

## 5 未闭环 / 风险

### 5.1 正文的 `547`：红线级别，但不在我权限内

- 位置：`main.tex:48`「the 547 stored claims and their provenance are itemised in that script」。这是「本文 Y 个数字」的自指，符合派单里定时炸弹的定义。
- 它**不是**生成的：`547` 不来自 `\CodeIndexCount` 一类宏，也不在 `verify_numbers.py` 的 needle 表里（该表 145 条都是结果值）。
- 过期条件：任何一次 claim 增删，`main.tex:48` 就错，而且**没有闸门会红**——R-V06 只解析脚本自己打印的 `claims=547`，不读正文这句话。我做了只读复算（§4.7）证明它现在是对的，仅此而已。
- 修法（交给撰写手/数值对账手，二选一）：
  1. 删数字：「the stored claims and their provenance are itemised in that script」——零风险，不动逻辑；
  2. 让 `verify_numbers.py` 在写 `out/03-numbers.md` 时同时输出 `\ClaimsCount{547}` 到一个 `.tex`，正文改成 `\ClaimsCount{}`，并把「正文是否引了这个宏」加进闸门。
- 我为什么不动：派单的改版权限只列了 `main.tex` 的三类接线与 `solve.py`/`verify_numbers.py` 的 `\uXXXX`，改这句话属于「改数字/改正文论证」，明确禁止。它在正文，不在附录；我不越权，也不假装它不存在。

### 5.2 `mk_appendix_src.py` 的退出码与文件头承诺不符

文件头 `:37` 写「0 current, 1 stale, 3 refused」，实现 `:249` 只有 `return 1 if stale else 0`：有 refused 项、但所有现有副本都 current 时仍然 exit=0。后果有限——被拒的文件不会写出副本，下一次 `--check` 会以 `STALE`（或缺失）红掉——但**当次**是假绿。一行修法：`return 3 if refused else (1 if stale else 0)`。这个脚本不在派单允许我动的清单里，所以只记录、不改。

### 5.3 印章文案没有独立闸门

`seal.py --check` 验的是「有、转义过、数量对」，不验「与 `make_figures.py` 里当前的 `header()`/`stamp()` 文案一致」。改了文案却不重跑图，印章会静默停在旧文案。现在没有数字在里面（全是 provenance 文本），风险是文字漂移，不是数字过期。检测法就是我这次做的幂等重建：重跑 `make_figures.py`，比对三件产物的 SHA256（§4.4）。要变成闸门，需要让 `seal.py` 能复算期望文案——那要改 `make_figures.py` 的结构，超出接线权限。

### 5.4 附录 listing 是 reconstruction，不是 `\lstinputlisting`

`main.tex:651-683` 是手写摘录；`:685` 已声明它是 reconstruction、`code/solve.py` 才是权威。它与 `solve.py` 的差异不止「去掉注解」：`_ilr_basis` 被改名成 `ilr_basis`（`solve.py:71` vs `main.tex:654`），阈值里的 `MS.v("eps_rel")` 被替换成参数 `eps`（`solve.py:105-119` vs `main.tex:676-682`）。数学等价，但不是逐字。当前没有任何闸门比对二者；若 venue 要求 listing 与源码逐字一致，这里会被抓。可选修法：改成 `\lstinputlisting[language=Python, firstline=…, lastline=…]{figures/src/solve.py}`（ASCII 副本已在 `figures/src/solve.py`），版面由撰写手决定。

### 5.5 图重建的解释器

见 §4.4：`E:\Mini\envs\mathmodel\python.exe` 在 fig16 上原生崩溃，`E:\Mini\python.exe` 正常。这不是数字问题，但会让「复跑」这一步失败，属于同一类「文档写了、实际跑不通」的风险，所以在 §7 里写死。

### 5.6 依赖件 `out/09-writing.md` 的页数/行数记录已过期

它在 `:4` 写「`main.tex`（671 行）与 `main.pdf`（28 页）」，在 `:50` 写「body=24 ≤ 30（总 28 页，附录 A 起于印刷页 24）」。当前实测：`main.tex` 687 行 / 64,777 B，`main.pdf` 物理 29 页（2 页摘要+目录 + 27 编号页），R-V01 body=25。它不是 PDF 内容，`gauntlet_check.py` 与 `submission_gate.py --only venue` 都不读这份记录，所以门禁全绿也不代表它是对的；但任何人拿它当复现依据都会对不上。刷新权在撰写手：重跑 §6 之后把 `:4`、`:50` 改成实测值，或者干脆改成「以 gauntlet 输出为准」而不写具体数——后者才不会再过期。

## 6 关闭条件（本角色）

| 命令 | 期望 | 当前 |
|---|---|---|
| `python code/seal.py --check figures --expect 16` | exit 0，16 枚 | exit 0，「seals on disk: 16」 |
| `python code/mk_appendix_src.py --quiet --check` | exit 0，0 written | exit 0，0 written / 274,696 B ASCII |
| `python code/gen_index.py --check` + 短语扫描 | exit 0，15/15，无陈旧短语 | exit 0，15/15，附录区间无 `fourteen`/`lines 67`/`ledger build` |

三条都跑过三遍：核验开始时、fig16 重建与负向测试回滚之后、本文件最后改稿之后（均为 exit 0，输出见 §4.2）。

## 7 复跑顺序（从脚本到 PDF）

1. `python code/solve.py` —— 重写 `data/results_q*.json`（幂等，`RNG_SEED` 固定）。
2. `python code/verify_numbers.py` —— 印出 `claims=… failures=… verdict=…`；正文数字对账的最后一道。
3. `E:\Mini\python.exe -X utf8 code\make_figures.py` —— 重写 16 组 PDF/PNG，并 `commit()` 16 枚印章。**不要**用 `E:\Mini\envs\mathmodel\python.exe`（§4.4）。
4. `python code/seal.py --check figures --expect 16`。
5. `python code/gen_index.py` —— 重写 `code_index.tex` 与 `code_totals.tex`；再 `--check`。
6. `python code/mk_appendix_src.py` —— 刷新 `figures/src`；再 `--quiet --check`。
7. `xelatex main.tex` 两遍（或 `latexmk -xelatex main.tex`）。
8. `python code/check_figures.py`、`gauntlet_check.py`、`review_check.py`、`submission_gate.py --only sources/venue`。
9. `python code/fix_bytes.py out/13-appendix.md` —— 本文件首行回填。

前六步任何一步改了 `.py`，第 5 步之后的表与第 9 步的字节数都要重跑；这就是这套管道的全部纪律。

VERDICT: PASS