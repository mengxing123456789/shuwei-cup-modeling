BYTES 32623

# 06 代码与数据可复现性审计

被测件：`E:\数学建模\PRACTICE_2023B`
审计窗口：2026-11-19 18:13 – 18:30（本机时区）
唯一产出：本文件
审计期间存在并发写者：PID 33368 `E:\Mini\envs\mathmodel\python.exe -X utf8 pipeline.py E:\数学建模\PRACTICE_2023B --only s3 --force s3 --skip-dispatch`（18:13:42 起，全程存活），期间把 `code/verify_numbers.py` 从 46271 B 一路改到 53573 B，并反复重写 `data/results_*.json`。**本报告是 18:29:21 的快照**（R-V11）。凡我给出的数字，均附该时刻的文件 sha256 前缀；重跑者若得不同值，先比 sha256 再比数。

---

## 0 三条机器口径：全部无法在 PDF 层面执行（原文输出）

| # | 命令 | exit | 耗时 | 原文关键行 |
|---|---|---|---|---|
| ① | `python review_check.py E:\数学建模\PRACTICE_2023B` | 1 | 225 ms | `pdf: None  pages: 0` / `[FAIL] X-pdf 找不到 PDF` / `VERDICT: FAIL (fail=1 unknown=0)` |
| ② | `python gauntlet_check.py E:\数学建模\PRACTICE_2023B` | 1 | 248 ms | `[FAIL] paper resolved ... <- 草稿（main.pdf 不存在或 < 150 KB）` / `[FAIL] main.pdf exists  run gauntlet.build() or xelatex first` / `0/2 PASS` |
| ③ | `python -m mmkit.figfont E:\数学建模\PRACTICE_2023B\main.pdf` | 1 | — | `pymupdf.FileNotFoundError: no such file: 'E:\数学建模\PRACTICE_2023B\main.pdf'` |

复算命令（mmkit 不在 site-packages，必须设 PYTHONPATH）：

```powershell
$env:PYTHONPATH='E:\数学建模\.agents\skills\mathmodeling\scripts'
$env:PYTHONIOENCODING='utf-8'
E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\review_check.py E:\数学建模\PRACTICE_2023B
E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py E:\数学建模\PRACTICE_2023B
E:\Mini\envs\mathmodel\python.exe -m mmkit.figfont E:\数学建模\PRACTICE_2023B\main.pdf
```

**根因不是环境**：`xelatex` 在 PATH（`E:\MIKTEX\miktex\miktex\bin\x64\xelatex.exe`），骨架 `main.tex` 能编出 5 页 PDF（见 `review\09-numbers.md` §0.1 的冻结副本实测，`exit=0 / Output written on main.pdf (5 pages)`）。缺 PDF 是**流水线没走到编译**。

被测件现场状态（18:29:21）：

| 项 | 实测 | 命令 |
|---|---|---|
| `*.pdf`（全树递归） | **0 个** | `glob('**/*.pdf', recursive=True)` |
| `figures\`、`tables\` | 存在但**条目数 0** | `glob('figures/*')`、`glob('tables/*')` |
| `review\00-metrics.md`（派单称"唯一基线"） | **不存在**；`review\` 现有 `04-fit.md`(71272 B, 17:42:09)、`05-model.md`(33278 B, 17:47:57)、`09-numbers.md`(26961 B, 18:27:02)、`README.md`(1337 B) | `Get-ChildItem review` |
| `main.tex` | 4546 B / 107 行 / mtime 16:49:15 / sha256 前缀 `2cc0e46029bbdec6` / `<<`=69 对 / **结果数字 token = 0** | 见 §3.1 |
| 项目是否 git 仓库 | `Test-Path .git` = **False** | 无 diff 级溯源能力 |

> **口径说明（必须并写）**：`review\09-numbers.md` 记 `<<...>>` 占位符 **69 处**，我用 `re.findall(r"<<.*?>>", tex)` 得 **68 处**。差异来自一处嵌套 `<<<...>>>`：非贪婪 `.*?` 会把它切成两段少算一处。`tex.count('<<')`=69、`re.findall(r"<<[^<>]*>>")`=69、`re.findall(r"<<.*?>>", re.S)`=69 —— **69 是对的，我最初那个 68 是我方正则口径错**，在此并列两个数并更正。

---

## 1 台账 `data/ledger.json`：字段齐全，但没有 `url`（设计使然，非缺陷）

文件：286874 B / mtime 16:55:46 / sha256 前缀 `f1e7f39729a82a85`。

| 字段 | 要求 | 实测 | 判定 |
|---|---|---|---|
| `source` | 必有 | **204 / 204** | PASS |
| `sha256` | 必有 | **204 / 204**，全为 64 位 hex（non-hex = 0） | PASS |
| `fetched_at` | 必有 | **204 / 204**，但**只有 1 个不同值** `2026-11-19T08:49:16Z` | PASS（见下） |
| `url` | 派单要求 url/source 二选一 | **0 / 204 有 `url` 字段** | 需说明，见下 |
| `cell_sha256` | — | 204 / 204，**204 个互不相同**（每格独立哈希） | PASS |
| `api` / `indicator` / `value` / `unit` / `external` | — | 204 / 204 | PASS |
| 其它字段缺失 | — | 逐条扫 9 个必填字段，`missing = {}`（空字典） | PASS |

- **`url` 为 0 是合理设计，不是漏字段**。数据源是两份官方 xlsx，无联网抓取；台账用 `source`（相对路径）+ `api`（`xlsx://<file>/<sheet>!<cell>`）表达来源。`source` 分布：Annex I **100** 条、Annex II **104** 条，合计 204，与 `coverage_scan.annex.total_cells = 204` 一致。若按派单字面要求"必须有 url"，则应记为 **NOT-APPLICABLE：本题数据源为随题附件 xlsx，不存在可抓取 URL**，而不是缺字段。
- **`distinct sha256 = 2`** 也是合理的：它是**整文件**哈希（Annex I `9cf303a3a30ee5fd…`、Annex II `ed71ce182be2767e…`），两文件我实测哈希与台账一致；每格的可追溯性由 `cell_sha256`（204 个互异值）承担。
- **`fetched_at` 全为常量是明示策略**。`clock_policy` 原文：`整份 ledger 不含任何 wall clock。fetched_at 一律是常量 FETCH_ANCHOR_UTC = 2026-11-19T08:49:16Z … 这样重跑 code/fetch_annex.py 得到的文件与上一次逐字节相同`。同时它记录了不用 xlsx 内部 zip 时间戳的理由（`两张附件的成员时间戳全被写入器清零成 1980-01-01`），该值另存 `source_files[*].zip_internal_stamp` 仅作诊断。→ 这是**为了确定性刻意冻结时间**，代价是 `fetched_at` 失去"实际抓取时刻"的语义，只能读作"本版数据锚点"。属可接受权衡，但引用时不得当"抓取时间"用。
- **自证段可用**：`replay` 给出 build / check / payload 三条命令 + `payload_sha256=d89a5091474aa837…` + `deterministic=true` + `deps="仅 python 标准库（zipfile / xml.etree / hashlib / json）"`；`verification` 5 条全 PASS；`unverified` 5 项（热解温度、升温速率、停留时间、脱硫灰组成、棉秆元素分析，均 `value=null`）—— **未知项显式留空而不是补值**，这一条做对了。
- **我独立复算了 31 条 `series` 向量哈希：31 / 31 全部命中，mismatch = 0**。复算口径（重跑者照此可复现）：

```python
# cwd = E:\数学建模\PRACTICE_2023B
import json, hashlib, re
L = json.load(open('data/ledger.json', encoding='utf-8'))
R = L['records']
for s in L['series']:
    pre = "%s.%s.%s." % (s['annex'], s['combo'].replace('/', '_'), s['indicator'].replace(' ', ''))
    rows = [r for r in R if r['id'].startswith(pre)]
    vec = '|'.join('%s:%.6f' % (re.search(r'配比\s*(\S+?)（', r['period']).group(1), r['value']) for r in rows)
    assert hashlib.sha256(vec.encode()).hexdigest() == s['sha256'], s['id']
```
（第一次复算我把 `combo` 的 `/` 与 `indicator` 的空格忘了替换，12 条 prefix 匹配到 0 条记录、哈希为 `e3b0c442…`（空串哈希）—— 是我方口径错，已修正；此处记录以便他人避开同一坑。）

- **一处措辞与实现不符（小瑕疵）**：`records_note` 称"原始 repr 另存 `raw_float`"，实测只有满足 `abs(value - raw) > 1e-9` 的 record 才写 `raw_float` / `raw_note`，不是每条都有。语义正确（只对被舍入过的格留原始值），但措辞应改为"被舍入过的格另存"。

**§1 判定：PASS**（三条字段实质齐备；`url` 属 NOT-APPLICABLE）。

---

## 2 脚本重跑：全部 exit=0，模型层逐字节确定，耗时层天然不可复现

cwd 一律 `E:\数学建模\PRACTICE_2023B`，解释器 `E:\Mini\envs\mathmodel\python.exe -X utf8`。以下为 18:26 统一时刻的一次真跑。

| 脚本 | exit | 耗时 | 落盘 | 复跑确定性 |
|---|---|---|---|---|
| `code/fetch_annex.py --check` | 0 | **169 ms** | 不写盘（只比对） | 字节级一致：`[check] PASS 字节级一致 286874 B  payload_sha256=d89a5091474aa83761a4a0f02d36fed79fe2ae7a4ed18becadf8eed9c496397a` |
| `code/fetch_annex.py --payload` | 0 | 151 ms | 不写盘 | 同一 sha |
| `code/model_skeleton.py` | 0 | **597 ms** | 不写盘（自测） | 打印 `[selftest] Annex I 闭合 max\|Σ-100\| = 1.42e-14 （25 列）`、`公式派生单元格 24 个`、`网格嵌套 {'DFA/CS': True,'DFA/CE': True,'DFA/LG': True}；Annex II 16 列`、`[MS] PARAMS 32 条；SYMBOLS 41 条`（题给 9 / 中间量 24 / 自设 8） |
| `code/solve.py` | 0 | **878 ms** | `results_q1..q5.json`（15970 / 18832 / 7505 / 5245 / 10363 B） | **连跑两次，10 个 `data/*.json` 的 sha256 全部 `stable=True`** |
| `code/s3_deliver.py` | 0 | **13805 ms** | `results_timing.json` 2296 B、`results_binding.json` 9868 B、`results_boundary.json` 17107 B、`results_perturb.json` 37088 B | 重跑后**只有 `results_timing.json` 变**（`673cb196…` → `6a687546…`），其余 9 个不变 |
| `code/verify_numbers.py` | 0 | **155 ms** | `out/03-numbers.md` 47619 B | 见 §3 |

- **`s3_deliver.py` 的耗时抖动极大**：同一脚本、同一输入，我先后测到 **32654 ms** 与 **13805 ms**（2.37×）。这不是脚本问题，是机器负载（并发写者 PID 33368 正在跑 s3）。→ 任何引用"本流水线跑多久"的说法都必须同时给机器状态，否则不可复算。
- **`results_timing.json` 不可复现是设计使然（它测的就是时间），但它在对账体系里被当普通结果引用**，这是 §6 全部矛盾的源头。
- `fetch_annex.py --check` 是**真重放**：重新 `build()`→`render()` 得 blob 与磁盘字节逐字节比对，不一致时打第一处差异行号并 `return 1`（`--build` 才写盘）。这是本项目可复现性做得最扎实的一处。

**§2 判定：PASS**（数据层与模型层全可复算）。

---

## 3 `code/verify_numbers.py` 对账有效性：**结构上对不上正文**

文件：**53573 B / 1062 行 / sha256 前缀 `7f6e5951a3d43c10`** / mtime 18:21:55。

### 3.1 stdout 原文（exit=0，155 ms）

```
544 claims
claims=544 declared=544 checked=544 failures=0 verdict=PASS exit=0 json_ok=544 json_fail=0 tex_bound=0/142 tex_state=skeleton deferred=142
DEFER 142 tex needles (main.tex is the skeleton: no result number to bind yet)
report=…\out\03-numbers.md bytes=47619
```

### 3.2 派单点名要看的 coverage 行：**源码里根本没有**

| 派单要求的字样 | 在 `code/verify_numbers.py` 中出现次数 |
|---|---|
| `printed numbers bound` | **0** |
| `tokens not bound` | **0** |
| `not bound` | **0** |

唯一等价输出是 `tex_bound=0/142 tex_state=skeleton deferred=142`（打印在 `code/verify_numbers.py:1039-1040`）与 `DEFER 142 tex needles`（`code/verify_numbers.py:1054`）。**没有任何一处列出"未绑定的 token 是什么"** —— `tex_stats` 只报一个 token 总数，从不打印清单。→ 派单设计的那个"看 M 里有没有结果的数字"的检查手段，在本实现里**不存在**，我只能改为独立枚举（§3.3）。

### 3.3 独立枚举 main.tex 的数字 token：26 个，全部合法归零

| 项 | 实测 |
|---|---|
| 非注释区数字 token | **26** 个，去重后只有 `{1, 2, 2699001, 3, 4, 99}` |
| `META_TOKEN_PATS` 条数 | **10** 条（不是 11） |
| 实际命中 | PAT0 `\baominghao{apmcm2699001}` 1 处；PAT1 `\setcounter{page}{1}` 1 处；PAT2 `\begin{thebibliography}{99}` 1 处；PAT3 `\bibitem{…}` 4 处；PAT4 `\label{tab:notation}` 1 处；PAT7 `\begin`/`\end{env}` 16 处；PAT8 `Question \d+` 2 处（Question 1 / Question 2） |
| 剥完 META + `<<.*?>>` 后剩余 | **0** 个 token |

→ `state = "skeleton"` 的判定**合法**，不是漏挖真数字（`code/verify_numbers.py:748`）。**这一处脚本没错**，但它带来一个致命后果：`code/verify_numbers.py:803-811` 的骨架豁免

```python
skeleton = (tstate["state"] == "skeleton")
tex_bad  = [] if skeleton else tex_miss      # L808
deferred = tex_miss if skeleton else []      # L809
n_fail   = len(json_bad) + len(tex_bad) + len(unevaluated)   # L811
```

使 **142 条正文侧 needle 在骨架状态下永不进入 `n_fail`**。也就是说：只要 `main.tex` 保持骨架，`verdict=PASS` 就与正文写对写错完全无关。

### 3.4 544 条 claim 的构成：402 条结构性不可能在正文侧失败

| 项 | 数量 |
|---|---|
| claims 总数 | 544 |
| **`needle=None`（正文侧结构性不可能失败）** | **402** |
| 有 needle | 142（展开成 **189** 个不同字符串；92 条单写法、50 条双写法） |
| 带 `derived` 算式 | 390 |
| **不带 `derived`（expected 只能照抄 json）** | **154**（其中 27 条有 needle、127 条 needle=None） |
| **不带 derived 且 `expected == fn()`（纯自指复制）** | **83** |

复算命令：

```powershell
E:\Mini\envs\mathmodel\python.exe -c "import importlib.util,os; os.chdir(r'E:\数学建模\PRACTICE_2023B'); s=importlib.util.spec_from_file_location('V',r'code\verify_numbers.py'); V=importlib.util.module_from_spec(s); s.loader.exec_module(V); it=V.build_claims(V.load_docs()); it=it.items if hasattr(it,'items') else it; print(len(it), sum(1 for x in it if not x.get('needle')), sum(1 for x in it if x.get('derived')), sum(1 for x in it if not x.get('derived')))"
```

分组 needle 覆盖（claims / 有 needle）：A 8/0、B 11/0、C 12/0、D 144/62、E 18/8、F 19/0、G 180/26、H 9/0、I 6/3、J 24/4、K 11/5、L 26/16、M 10/2、N 9/7、O 45/11、P 26/0（P 下 binding 2/0、boundary 9/0、perturb 5/0、timing 10/0）。
→ **A/B/C/F/H/P 共 6 组（77 条）完全不给 needle**；`P timing` 10 条（就是 §6 那张耗时表）**一条 needle 都没有**。

### 3.5 `needle=None` 之外，还有两类"永远不可能失败"的写法

1. **5 条两侧读同一条 json 路径（真自证）**：
   - `code/verify_numbers.py:596` `ridge 首行 A` → 两侧都读 `k['ridge_n1'][0]`
   - `code/verify_numbers.py:601` `ridge 首行 log10_A` → 同上
   - `code/verify_numbers.py:403` `R2[0]` → 两侧都读 `il['R2_each'][0]`
   - `code/verify_numbers.py:553` `gamma[{p}]` → `A(... sel["gamma_centered"][p], rel=1e-9)`，实际值也是 `sel["gamma_centered"][p]`
   - `code/verify_numbers.py:650` `point 首点` → 两侧都读 `d['point'][p][0]`

   这 5 条无论 json 值是多少都必然 PASS。
2. **83 条无 derived 且 `expected == fn()`**：`expected` 是字面量、`fn()` 只是把同一条 json 键再读一遍，两者相等是恒等式（如 `D q1 CS/Tar/first = 19.46`）。这类 claim 的价值仅在于"json 里确实有这个值"，**不校验任何算式**。

### 3.6 匹配器本身是对的，但有三处会让真数字绑不上

- 词边界匹配 `re.search(r"(?<![\d.])" + re.escape(str(needle)) + r"(?!\d)", text)`（`code/verify_numbers.py:98-100`），配 8 条自测断言（A 组，含 `2016 不含 16`、`0.16 不含 16`、`119.46 不含 19.46`）—— **匹配器是被证明的，这一处做对了**。
- **符号被抹平**：`needle_forms` 里 `for x in (v, abs(v))`。实测 `needle_forms(37.667) = ['37.67','37.7']`（无负号）；`has_token('Δ=-37.7%','37.7')` 与 `has_token('Δ=+37.7%','37.7')` **都为 True**。→ 正文把 −37.7% 写成 +37.7% 也照样 PASS。
- **短数字绑不上**：`needle_forms(2.3) = ['2.30']`（有效数字 < 3 位的写法被丢），而正文写 `2.3%`；`has_token('...+2.3%','2.30')` 与 `has_token('...-2.3%','2.30')` **都为 False**。→ `CS/Char +2.3%` 这类两有效数字的量，即使正文写对也判不中。
- **`QUOTABLE_MIN = 1.0`**：span < 1.0 的量不给 needle（注释举 `C3H6 0.06 mL/g`）。

### 3.7 对账范围漏掉了唯一真正印了数字的地方

`code/verify_numbers.py` 的输入只有 `data/*.json`（10 个）+ `main.tex`。全文正则扫 `open(...)` 调用：**从不读** `out/01-model.md`、`out/02-solve.md`、`review/04-fit.md`、`review/05-model.md`。

而当前**唯一真正印了结果数字的载体就是 `out/*.md`**（main.tex 是骨架、无 PDF）。→ **耗时表、`±18.7%`、`105.42%`、`74.2%` 全部在对账范围之外**。§6 的失效行因此不会被任何脚本抓到。

**§3 判定：FAIL**（对账工具本身实现正确，但覆盖面结构性失效：正文侧 0/142 命中且永不失败、402/544 无正文侧断言、83 条纯自指、交付文档完全不在范围）。

---

## 4 `mmkit.freshness`：PASS，但对本项目主脚本是结构性空转

```
$env:PYTHONPATH='E:\数学建模\.agents\skills\mathmodeling\scripts'
python -m mmkit.freshness E:\数学建模\PRACTICE_2023B
→ PASS  no script is newer than a name-matched artefact        exit=0
```

跑了两次（重跑 `solve.py` 前后各一次），**两次都 PASS** —— 这正是问题所在：我刚刚重写了全部 `results_*.json`，它仍然说"没有脚本比同名产物新"。

机制（`E:\数学建模\.agents\skills\mathmodeling\scripts\mmkit\freshness.py`）：

- `STOP = {"q1".."q5","data","make","tab","fig","code","py","json","tex","pdf","png","final","check","run"}`；
- 配对条件是一方 token 集合是另一方的子集（`at <= st or st <= at`）；
- `solve.py` → `{"solve"}`；`results_q1.json` → `{"results"}`（`q1`/`json` 都被 STOP 掉）。**两个集合互不为子集 ⇒ 永远配不上对**；
- `verify_numbers.py` → `{"verify","numbers"}` 与 `ledger.json` → `{"ledger"}` 同理。

`freshness.py:14-15` 自己写明"token 配对是启发式，不是依赖图"。→ **这个 PASS 对本项目不构成"产物不旧"的证据**，必须换成显式时间戳比较（§8 表已给）。

**§4 判定：NOT-APPLICABLE 于本项目 —— PASS 无信息量**（工具在能配对的命名约定下有效；本项目的命名 `solve.py → results_q1.json` 不在其覆盖内）。

---

## 5 附录与 `code/*.py`：三处不一致

### 5.1 附录里一个脚本都没有

| 位置 | 内容 |
|---|---|
| `main.tex:100` | `\section{Appendix A: Code}`（节标题存在） |
| `main.tex:104` | `%\lstinputlisting{code/main.py}` —— **被注释掉** |
| `main.tex:105` | `<<paste the full source of every script that produced a number, one appendix per script>>` —— **仍是占位符** |
| `code/main.py` | **不存在**（`os.path.exists` = False） |

对照官方判据 **C9-appendix（附录须列出软件名与全部源码）**：`n_hits = 16`，覆盖 **8 份**官方规范；原文如 `2017_APMCM_Essay_format_and_submission_specifications.txt:122` `In the appendices, you should provide the name of the software which you use`、`:124` `and all computer source code (if you have)`；`2018_…txt:126` / `:128` 同款。→ 本论文**附录源码 0 行、软件名 0 处**（`main.tex` 全文对 `Python` / `numpy` / `MiKTeX` / `xelatex` 的命中数均为 0）。这一条按 C9 是硬项。

### 5.2 唯一的"脚本清单"已经过期

| 来源 | 声称 | 实测（18:29:21） | 偏差 |
|---|---|---|---|
| `review/04-fit.md:199`、`:768` | `code/` 下 **12 个** `*.py` | **16 个**（10 个非探针 + 6 个 `_probe_*.py`） | 条数 12 vs 16 |
| 同上 | `verify_numbers.py` **2402 B** | **53573 B** | **22.3 倍** |

→ `review/04-fit.md` 的清单是**早期快照**，不能当现状引用。（`code/` 下 6 个 `_probe_*.py` 是探查遗留脚本，本身也是"提交物该不该带"的问题，见 C3-naming `n_hits=72` / 14 份文件对提交物清单的要求。）

### 5.3 三个不同的"附录 A"，且数值索引的行号有 4/11 错位

| "附录 A" | 出处 | 内容 |
|---|---|---|
| `Appendix A: Code` | `main.tex:100` | 空的（§5.1） |
| 「附录 A · 符号表」 | `out/01-model.md:292` | 由 `code/gen_appendix.py --write` 从 `MS.SYMBOLS` 生成，41 行 |
| 「附录 A · 数值索引」 | `out/02-solve.md:431` | 结论 → json 键路径 → 代码行号，11 行 |

`out/02-solve.md` 数值索引的 11 条 `L` 行号，逐条核"该行号附近 ±3 行是否真出现对应 token"：**7 / 11 命中，4 条错位**。

| 文档行 | 量 | 引用的 L | `solve.py` 中真实行 |
|---|---|---|---|
| `out/02-solve.md:444` | CE 失拟统计量 `lack_of_fit_F` | L204 | **224 / 503** |
| `out/02-solve.md:445` | CS 失拟统计量 `lack_of_fit_F` | L204 | **224 / 503** |
| `out/02-solve.md:456` | Q3 Tar 均值差 `mean_Delta` | L320 | **324** |
| `out/02-solve.md:459` | 级数混淆比 `n_order_confounding` | L396 | **409 / 516** |

（其余 76 条 `L\d+` 引用全在 `solve.py` 541 行范围内，无越界。）复算命令：

```powershell
E:\Mini\envs\mathmodel\python.exe -c "import re,os; os.chdir(r'E:\数学建模\PRACTICE_2023B'); s=open(r'code\solve.py',encoding='utf-8').read().split(chr(10)); d=open(r'out\02-solve.md',encoding='utf-8').read().split(chr(10)); rows=[(i,re.search(r'\|\s*([^|]+?)\s*\|\s*[-\d.]+\s*\|\s*`([^`]+)`\s*\|\s*L(\d+)',l)) for i,l in enumerate(d,1)]; rows=[(i,m.group(1),re.split(r'[.>]\s*',m.group(2))[-1].strip('`{}[]'),int(m.group(3))) for i,m in rows if m]; print([(i,lab[:14],t,c,[j+1 for j,x in enumerate(s) if t in x][:3]) for i,lab,t,c in rows])"
```

**§5 判定：FAIL**（C9 硬项未满足；清单过期 22.3 倍；行号 4/11 错位）。

---

## 6 同一份 data，两处不同口径 —— 硬证据

### 6.1 耗时表 9 行里 8 行已失效（唯一真正的口径冲突）

`out/02-solve.md:58-68` 印的耗时表，与盘上 `data/results_timing.json`（18:26:45，sha256 前缀 `6a6875466ce0f376`）对比：

| call | 正文印的 (ms) | 盘上 median_ms | 偏差 | 判定 |
|---|---|---|---|---|
| selftest | 14.891 | 15.061 | **−1.13%** | 失效 |
| load_annex_i | 1.664 | 1.720 | **−3.26%** | 失效 |
| load_annex_ii | 1.892 | 1.894 | −0.11% | 一致 |
| q1 | 156.304 | 189.718 | **−17.61%** | 失效 |
| q2 | 0.745 | 1.228 | **−39.33%** | 失效 |
| q3 | 0.188 | 0.226 | **−16.81%** | 失效 |
| q4 | 0.294 | 0.255 | **+15.29%** | 失效 |
| q5 | 56.433 | 68.100 | **−17.13%** | 失效 |
| pipeline_q1_to_q5 | 210.629 | 254.609 | **−17.27%** | 失效 |

**8 / 9 行偏差 > 1%**，方向一致（旧值普遍偏低，说明那次运行机器更空）。而这些数在**全树只有 `out/02-solve.md` 自己**（`grep 156.304` / `14.891` / `210.629` / `74.184` / `56.433` 命中文件列表均只有该文件）→ 是**一次已丢失的运行**，无产物键。

**它派生出的三个结论全部随之失效**：

| 位置 | 结论 | 问题 |
|---|---|---|
| `out/02-solve.md:17`、`:72` | `q1` 占端到端 **74.2%**（= 156.304 / 210.629） | 分子分母都是旧值；用盘上数重算为 189.718 / 254.609 = **74.5%**。差值小，但**两个操作数都无产物键**，读者无法复算 |
| `out/02-solve.md:77` | `q5` 前一次 74.184 → 本次 56.433，差 **24%** | 两个数都不在任何 json 里；24% 算术对（(74.184−56.433)/74.184 = 23.93%），但**两个操作数都无产物** |
| `out/02-solve.md:75-76` | 「单次测量噪声 **±56%**（见 results_timing.json 的 meta.note）」 | `meta.note` 原文确有"±56%"字样，但**盘上 json 复算不出这个统计量**：9 个 call 的 (max−min)/min 分别为 selftest 13.5%、load_annex_i 35.5%、load_annex_ii **56.7%**、q1 33.5%、q2 **71.8%**、q3 12.7%、q4 15.9%、q5 14.0%、pipeline 31.5%。→ ±56% 只是 `load_annex_ii` 一格的巧合，`q2` 的 71.8% 比它还大。**这是把一句机器级经验值当成本次运行的统计量借用** |

复算命令：

```powershell
E:\Mini\envs\mathmodel\python.exe -c "import json,os; os.chdir(r'E:\数学建模\PRACTICE_2023B'); t=json.load(open('data/results_timing.json',encoding='utf-8')); [print('%-22s median=%8.3f spread=%5.1f%%'%(c['name'],c['median_ms'],(max(c['runs_ms'])-min(c['runs_ms']))/min(c['runs_ms'])*100)) for c in t['calls']]"
```

### 6.2 `±18.7%`：数值对，但没写是哪一格

`out/02-solve.md:363` 写"引用 Q5 预测时必须带 LOO 值，否则等于把 **±18.7%** 的误差当 0 报"。盘上 `data/results_q5.json` 的 `loo_rmse_rel` 12 格降序：**CE/Water 18.708%**、LG/Tar 17.078%、LG/Syngas 12.395%、LG/Water 6.922%、CE/Tar 6.341%、CE/Char 6.032%、CE/Syngas 6.005%、CS/Tar 5.497%、CS/Syngas 4.910%、LG/Char 1.530%、CS/Water 1.366%、CS/Char 0.892%。→ 18.7% 是**最大格 CE/Water**，数值可复算；但正文只给一个不带格名的 `±18.7%`，读者无法定位（且 `18.7` 不在 verify_numbers 的 needle 里，源码 grep 命中 0）。

### 6.3 `105.42%`：有产物键，但对账工具不管

`out/02-solve.md:98` 与 `:104` 两次印 `105.42%`，产物键 `data/results_binding.json → sources[eps_rel].measure.band_width_pct_of_eps = 105.42`，**数值可复算**。但 `105.42` 同样不在 verify_numbers 的 needle 里（grep 0 命中）。→ 这类"有键但对账工具不管"的数字，靠人肉一致性维持，一旦 data 重跑就会静默失效。

### 6.4 Q1 百分比口径：**已自曝，处理正确**（不算缺陷，但要记）

`out/01-model.md:86-87` 与 `:267` 明写「CS 的 −37.7% 相对纯棉秆（有 0/100 档），CE 的 +31.6% 相对 10/100 档（无零基线）——两个百分数不可横向比较」；`data/results_q1.json` 的 labels 证实 CS 有 9 档（含 `0/100`）、CE/LG 各 8 档（从 `10/100` 起）。`out/02-solve.md:95` 进一步给出 CS Tar 的双基准 `−37.667%`（对 0/100）与 `−29.681%`（对 10/100）。
→ 这是**已披露的口径差异**，我核为正确。遗留问题只有一处：`review/05-model.md:72` 指出 Q1 表仍把三组合的百分比放进同一张表（自订规则 V3 ③ 未执行）。

**§6 判定：FAIL**（耗时表 8/9 行无产物键支撑；由它派生的 74.2% / 24% / ±56% 三个结论均不可复算）。

---

## 7 四类高频缺陷逐类过一遍

| 类 | 本题命中情况 | 证据 |
|---|---|---|
| ① 口径混用 | **命中**：耗时表用旧运行的值、`±56%` 借机器经验值当统计量；`results_timing.json` 这类天然不可复现的产物与确定性产物混在同一对账体系里 | §6.1 |
| ② 倍数与百分数（同一现象两个分母） | **命中但已披露**：Q1 的 CS 有 `0/100` 零基线、CE/LG 无；`−37.7%` vs `−29.68%` 是同一现象两个分母，`out/02-solve.md:95` 已并列给出 | §6.4 |
| ③ 多重比较（BH/Bonferroni 后 q） | **NOT-APPLICABLE**：本项目 544 条 claim 是对**产物值的算术复算**，不是对同一张表做 k 个统计检验，不存在族错误率问题。真正需要多重比较的是 Q2 的 25 个气体格 × 显著性判定，但 `data/results_q2.json` 给的是 `thr_trend` / `span_over_thr` 逐格判据而非 p 值，故无 q 可算 | `out/02-solve.md` §Q2 表；`results_q2.json` 键名 |
| ④ 图表刻度（有效字号 < 6 pt） | **NOT-APPLICABLE**：`figures\` 条目数 0、`*.pdf` 计数 0，`mmkit.figfont` 无对象可量 | §0 |

---

## 8 结论表（可用同一批文件复算）

**复算前置**：被测件无 PDF，故一切复算以 `main.tex` + `data/*.json` + `code/*.py` 为对象，不用 PDF。

| # | 核查项 | 结论 | 可复算命令 / 判据 |
|---|---|---|---|
| 1 | `main.pdf` 存在 | **否** | `glob('**/*.pdf')` → 0；`review_check.py` exit=1 |
| 2 | 台账 `source` / `sha256` / `fetched_at` 覆盖 | **204/204 全覆盖** | §1 脚本；`missing = {}` |
| 3 | 台账 `url` 字段 | **0/204**（NOT-APPLICABLE：数据源为随题 xlsx） | `sum('url' in r for r in records)` = 0 |
| 4 | 台账 31 条 series 向量哈希 | **31/31 命中，mismatch=0** | §1 复算脚本 |
| 5 | 抓取脚本可重跑 | **是**，exit=0 / 169 ms / 字节级一致 | `code/fetch_annex.py --check` |
| 6 | 建模脚本可重跑且确定 | **是**，`solve.py` exit=0 / 878 ms / 10 个 json sha 全同 | 连跑两次比 sha256 |
| 7 | 交付脚本可重跑 | **是**，`s3_deliver.py` exit=0 / 13805 ms（另一次 32654 ms） | 两次耗时差 2.37×，须带机器状态 |
| 8 | `verify_numbers.py` 对账 JSON 侧 | **544/544 PASS，failures=0** | `code/verify_numbers.py` exit=0 / 155 ms |
| 9 | `verify_numbers.py` 对账正文侧 | **0/142 命中，142 条全部 DEFER，且骨架状态下永不进入 n_fail** | `code/verify_numbers.py:803-811`；stdout `tex_bound=0/142` |
| 10 | 派单要求的 coverage 行 | **源码不存在**（`printed numbers bound` / `tokens not bound` 各 0 次） | `src.count('printed numbers bound')` = 0 |
| 11 | `needle=None` 结构性空转 | **402/544（73.9%）** | §3.4 复算命令 |
| 12 | 无 derived 且 `expected==fn()` 纯自指 | **83 条** | §3.4 复算命令 |
| 13 | 对账是否覆盖 `out/*.md`（唯一印数载体） | **否**，`open()` 零命中 | §3.7 |
| 14 | `mmkit.freshness` | **PASS，但结构性空转**（`solve.py`↔`results_q1.json` 配不上对） | §4；`freshness.py:14-15` |
| 15 | 附录源码（C9，16 hits / 8 份规范） | **0 行**；`main.tex:104` 注释、`:105` 占位；`code/main.py` 不存在 | §5.1 |
| 16 | 附录软件名（C9） | **0 处** | `main.tex` 对 Python/numpy/MiKTeX/xelatex 命中 0 |
| 17 | 附录脚本清单与 `code/*.py` 一致 | **否**：声称 12 个 / 2402 B，实测 16 个 / 53573 B（22.3×） | `review/04-fit.md:199`、`:768` |
| 18 | 数值索引行号准确 | **7/11**，4 条错位 | §5.3 复算命令 |
| 19 | 同一 data 两处不同口径 | **命中**：耗时表 8/9 行偏差 >1% | §6.1 |
| 20 | 耗时表派生结论（74.2% / 24% / ±56%） | **全部不可复算**（操作数无产物键） | §6.1 |
| 21 | Q1 双分母百分比 | **已披露，处理正确** | `out/01-model.md:86-87`、`:267`、`out/02-solve.md:95` |
| 22 | 多重比较 / 图表字号 | NOT-APPLICABLE（无统计检验族、无图无 PDF） | §7 |

---

## 9 可复现性等级：**部分可复算**

分层给结论，不合并成一个笼统评语：

| 层 | 等级 | 理由（全部有命令） |
|---|---|---|
| **数据层**（附件 → `data/ledger.json`） | **全可复算** | `fetch_annex.py --check` exit=0、169 ms、**字节级一致**、`payload_sha256` 固定；台账 204/204 字段齐备；31/31 series 哈希独立命中；未知项显式 `value=null` 不补值 |
| **模型层**（`code/*.py` → `data/results_*.json`） | **全可复算** | `solve.py` 两次运行 10 个 json sha256 全同；`s3_deliver.py` 除 `results_timing.json`（测时间，天然不可复现）外 9 个 json 全同；`model_skeleton.py` 自测闭合误差 1.42e-14 |
| **印数层**（→ 正文/交付文档） | **不可复算** | ①`main.tex` 是骨架，结果数字 token = 0，`main.pdf` 不存在；②`verify_numbers.py` 正文侧 0/142 命中且骨架下永不失败，402/544 无正文侧断言，83 条纯自指；③唯一印了数字的 `out/*.md` **不在对账范围内**；④耗时表 8/9 行无产物键、派生的 74.2% / 24% / ±56% 均不可复算；⑤附录源码 0 行（C9 硬项） |

**综合：部分可复算**（数据层与模型层是这台机器上少见的干净实现；失效全部集中在"从产物到正文"的最后一跳）。

**判定 FAIL 的三条硬理由**：
1. **C9-appendix（16 hits / 8 份官方规范）未满足**：`main.tex:100` 有 `Appendix A: Code` 标题，但源码 0 行（`:104` 注释、`:105` 占位）、软件名 0 处。
2. **对账工具的覆盖面结构性失效**：`tex_bound=0/142` + 骨架豁免（`code/verify_numbers.py:803-811`）使 `verdict=PASS` 与正文写对写错无关；派单点名的 coverage 行在源码中不存在。
3. **唯一印了数字的载体（`out/02-solve.md`）已被 data 重跑覆盖**：耗时表 8/9 行偏差 >1%（最大 −39.33%），其派生的 74.2% / 24% / ±56% 三个结论无产物键，且对账工具根本不读该文件。

**修复顺序（按代价从小到大）**：
1. `code/verify_numbers.py` 增加 `out/*.md` 为输入，并把 `P timing` 的 10 条 claim 接上 needle；
2. 把耗时表改成从 `results_timing.json` 现取现印（或明确标注"某时刻快照，不可复算"）；
3. 删除 `out/02-solve.md:75-76` 的 `±56%`（或改为"本机历史经验值，非本次运行统计量"）；
4. `main.tex:104` 解注释并按 C9 逐脚本 `\lstinputlisting`，同时在附录列软件名与版本；
5. 重写 `review/04-fit.md` 的脚本清单（12→16、2402 B→53573 B），修正数值索引 4 条行号；
6. `mmkit.freshness` 在本项目不适用，改用显式 mtime 比较（§8 表已可复算）。

---

本报告只写这一个文件。所有数字均标注了 18:29:21 时刻的文件 sha256 前缀；并发写者 PID 33368 若在此后继续改写 `code/verify_numbers.py`（`7f6e5951a3d43c10`）或 `data/results_*.json`，请先比 sha256 再比数，不要直接拿本报告的数字去对新的产物。

VERDICT: FAIL
