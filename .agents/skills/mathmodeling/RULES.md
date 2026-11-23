# 硬规定（RULES）

每条规定三部分：**规定**、**为什么**（踩过的坑或官方条款）、**验证命令**。
验证命令必须能跑出 PASS/FAIL；跑不出来的条目不算规定，只算建议。

编号规则：`R-` 之后跟类别字母与两位序号。类别：`E` 环境、`M` 建模/数据、`T` 训练、`W` 撰写、`X` 合规、`V` 验收。
改规定必须同时改测试（`scripts/tests/`）；测试改了规定没改，就是测试在骗人。

---

## R-E 环境

### R-E01 只用 mathmodel 解释器，不假设存在 dl 环境
**规定**：所有需要 numpy/pandas/matplotlib/torch 的脚本，一律
`E:\Mini\envs\mathmodel\python.exe`（或 `conda run -n mathmodel`）。文档与脚本注释里禁止出现
`conda activate dl` / `-n dl`。
**为什么**：本机**没有 `dl` 环境**。`conda env list` 只有 deep_learning_3.8 / label-studio /
labelimg / labelme / mathmodel / ml310 / py310；`conda run -n dl …` 直接
`EnvironmentLocationNotFound: Not a conda environment: E:\Mini\envs\dl`。
`mathmodel` 自带 torch 2.14.1+cu126 且 `cuda.is_available() True`，GPU 训练根本不需要 dl。
**验证**：`grep -rn "\-n dl\b\|activate dl" .agents/skills/mathmodeling/ | grep -v RULES.md` 必须为空。

### R-E02 跑 Python 时必须设 PYTHONIOENCODING=utf-8
**规定**：调用之前 `$env:PYTHONIOENCODING='utf-8'`；打印中文的脚本不要在 `conda run` 里跑。
**为什么**：`conda run` 包装后 stdout 走 GBK，中文一律
`UnicodeEncodeError: 'gbk' codec can't encode character '\ufffd'`。直接调 python.exe 并设
PYTHONIOENCODING 才稳。
**验证**：脚本里没有 `print` 中文却报 UnicodeEncodeError 时，检查是否用了 conda run。

### R-E03 写脚本文件用 WriteAllText + UTF8Encoding($false)
**规定**：把 Python 脚本写到临时文件，一律
`[System.IO.File]::WriteAllText($p, $s, (New-Object System.Text.UTF8Encoding($false)))`；`Out-File -Encoding utf8`
会插 BOM，然后 `python` 报 `SyntaxError: invalid non-printable character U+FEFF`。
**为什么**：踩过。BOM 在文件头，报错行号是 1，看起来像别的问题。
**验证**：python -c "import pathlib;p=pathlib.Path(r'$env:TEMP\\bom.py');print(p.read_bytes()[:3])"  # 必须是 b'imp'
### R-E04 读 LaTeX 日志按 **BOM** 判编码，不要假设它是 UTF-16
**规定**：先读前 2 字节：`FF FE` / `FE FF` 才按 UTF-16 解码，否则按 UTF-8。
`gauntlet.latex_errors` 已按此实现；**禁止**无脑 `[Encoding]::Unicode`。
**为什么**：这条原来的写法（"xelatex 写的日志是 UTF-16"）是**错的**，2026-11-11 实测推翻：
MiKTeX 自己写的 `main.log` 首 4 字节是 `54 68 69 73`（ASCII "This"）、54,328 字节纯 ASCII/UTF-8、
`Get-Content` 得 1393 行；`APMCM2025_C\main.log` 同样首字节 `54 68 69 73`。
真正带 `FF FE` 的 UTF-16 文件是 **PowerShell 用 `*>` / `>` 重定向落盘**的产物
（实测 `xelatex … *> ps_redir.log` → 首字节 `FF FE`，2062 字节）。
按错的方向解码，`grep "^!"` 一个都找不到，于是"日志无错误"变成假结论——两种错法都会造成假结论，
所以判据只能是 BOM，不能是"它在 logs 目录里"。
**验证**：`(Get-Content $log -TotalCount 1)` 能读出正文即可；判定用首字节：`54 68 69 73`=ASCII、`FF FE`=UTF-16
### R-E04b 所有 `.ps1` 文件必须存成 UTF-8 **with BOM**
**规定**：写 PowerShell 脚本时显式加 BOM（`New-Object System.Text.UTF8Encoding($true)`）。
**为什么**：PS 5.1 读**不带 BOM** 的 UTF-8 `.ps1` 会按 GBK 解正文，写死的中文路径变成
`E:\鏁板﹀缓妯\...` → `Cannot find path ... because it does not exist.`。子代理自己写探针时踩过，
绕了好几轮才定位。`.py` 相反：Python 读 UTF-8 不需要 BOM，加了反而让某些工具在首行看到 `\ufeff`
（见 R-E03）。
**验证**：`(Get-Content $ps1 -Encoding Byte -TotalCount 3)` 必须是 `239 187 191`（即 EF BB BF）
### R-E04c `$ErrorActionPreference="Stop"` 的触发条件是"Stop + 重定向"
**规定**：调 xelatex/pdftotext 时要么裸调用，要么包一层 `Invoke-Native` 把 stdout/stderr 收进内存；
**成败只看 `$LASTEXITCODE`**。
**为什么**：MiKTeX 每次启动都往 stderr 写 `security risk: running with elevated privileges`。
裸调用与 `| Out-Null` 不会抛，但 `*> $null` / `2>$null` / `2>&1 | Out-Null` 在
`$ErrorActionPreference="Stop"` 下会抛 `NativeCommandError`，把一次成功编译判成失败。
**验证**：在同一 shell 里先 `$ErrorActionPreference='Stop'`，再 `& xelatex -version 2>&1 | Out-Null`；能继续执行下一句即通过
### R-E04d 编译日志不许重定向到同名 `<job>.log`
**规定**：日志另起名（`<job>.out` / `<job>.build.txt`），或用 `Invoke-Native` 收到内存里；**禁止** `xelatex many.tex > many.log`。
**为什么**：外层 shell 先创建并占住 `many.log`，xelatex 随后要写同一个 `<job>.log` 打不开 →
`! I can't write on file 'many.log'.` → `Emergency stop` → `No pages of output.`（EXIT=1）。
2026-11-11 复现：`cmd /c "xelatex … many.tex > many.log 2>&1"` 得 exit=1 且日志里有上面三句；
改成 `> many.out` 得 exit=0、`Output written on many.pdf`。
`APMCM2026\build.ps1` 用内存捕获，所以当前仓库不会踩，但历史 `logs\*.txt` 说明曾经踩过。
**验证**：编译后 `Test-Path <job>.out` 为 True 且 `<job>.log` 只由 LaTeX 自己写（`Get-ChildItem <job>.log` 的 mtime 等于最后一次 xelatex 结束时间）
### R-E05 PowerShell 里 .NET 的 ReadAllText 认进程 cwd，不认 PowerShell 位置
**规定**：给 .NET API 的路径一律绝对路径。
**为什么**：`[System.IO.File]::ReadAllText('main.tex')` 在 `cd E:\数学建模\APMCM2025_C` 之后仍然去
`E:\数学建模\main.tex` 找，报 `未能找到文件"E:\数学建模\main.tex"`。踩过两次。
**验证**：`[System.IO.File]::ReadAllText('main.tex').Length` 与 `(Get-Content main.tex -Raw).Length` 必须相等
### R-E06 改 .py 用 Python 改，不用 PowerShell 字符串操作
**规定**：多行源码改动一律写成 Python 脚本，`read` → `replace` → `write`。
**为什么**：PowerShell 的 `-join`/`-replace` 处理带 `\\`、`$`、`%` 的多行 LaTeX/Python 源码会吃掉反斜杠，
曾把 15 张表里 58 行行尾 `\\` 降成 `\`，编译报
`! Extra alignment tab has been changed to \cr` / `! Misplaced \noalign` / `! Missing } inserted`。
**验证**：`git diff --numstat` 里被改的 .py 行数应与目标行数一致（不是整文件重写）；改完 `python -m py_compile <file>`
### R-E07 判断外部命令成败看退出码，不看 stderr
**规定**：`xelatex`、`pdftotext`、`pdfinfo` 往 stderr 写 "security risk: running with elevated privileges"，
这不是失败。判 `$LASTEXITCODE`。
**为什么**：在 `$ErrorActionPreference="Stop"` 下这句话会把整个构建脚本打断，而编译其实是成功的。
**验证**：命令后立刻 `$LASTEXITCODE`；`xelatex` 成功=0，`pdftotext` 成功=0（stderr 的 security-risk 行不影响）
### R-E08 没有 perl，不用 latexmk
**规定**：编译走两次 `xelatex -interaction=nonstopmode -halt-on-error main.tex`（`gauntlet.build` 已实现）。
**为什么**：`latexmk` 报 `MiKTeX could not find the script engine 'perl'`。
**验证**：`python -c "import subprocess;print(subprocess.run(['latexmk','-v'],capture_output=True).returncode)"` 应为非 0；构建脚本里 `Select-String -Pattern '\\blatexmk\\b' build.ps1` 命中 0
### R-E09 PowerShell 里 `$dst:` 会被当驱动器盘符
**规定**：拼路径用 `${dst}\a.py` 或 `Join-Path`。
**为什么**：`Select-String -Path "$dst\a.py","$dst\b.py"` 解析成 `E:\award_standard.py`，报找不到路径。
**验证**：`$dst = 'X:\y'; "$dst\a.py"` 会输出 `X:\a.py` 吗 —— 实际 `$dst:` 被当盘符时整串变 `X\a.py`；改成 `${dst}\a.py` 后 `Test-Path` 能正常判。

### R-E10 先修 PATH 的 `Library\bin`，再谈"换解释器"

**规定**：跑任何 numpy / scipy / matplotlib 之前，PATH 里必须**前置**
`<env>;<env>\Library\bin;<env>\Scripts`。前置后 mathmodel 可直接画图、跑 `least_squares`；
只有在**不能改 PATH** 的场合（别人的机器、CI 里写死绝对路径）才按旧办法换 `D:\Python`。

**为什么**：退出码 −1066598273（0xC06D007F）不是 matplotlib 的 bug，是 **MKL 延迟加载找不到依赖链**。
`envs\mathmodel\Library\bin` 里的 `libblas/libcblas/liblapack.dll` 全是转发桩，真正被引用的是
`mkl_rt.3.dll → mkl_core.3.dll → mkl_intel_thread.3.dll → libiomp5md.dll`（conda `mkl 2026.1.0`）。
直接用绝对路径调 `envs\mathmodel\python.exe` 时 PATH 里没有这一层，于是
`a@a`、`np.linalg.solve`、`scipy.linalg.lstsq`、`least_squares`、`canvas.draw()` 一起崩；
`import numpy` / `minimize_scalar`（不碰 LAPACK）却正常 —— 这个"一半能用"的现象就是当年误判成
matplotlib 专属 bug 的原因。2026-11-12 用上面的 PATH 前置后，`code/make_figures_extra.py`
在 mathmodel 里连出 7 张图（含 300 dpi PDF）全部成功，旧结论被推翻。

**验证**：同一条 matmul 在两种 PATH 下必须一成一败 —— 下面三条命令逐条跑，第 1 条退出码非零、第 2 条打 `3.0`、第 3 条打 7 张图。
```powershell
& 'E:\Mini\envs\mathmodel\python.exe' -c "import numpy as np; print((np.eye(3)@np.eye(3)).sum())"   # 不前置 → 退出码 -1066598273
$env:PATH='E:\Mini\envs\mathmodel;E:\Mini\envs\mathmodel\Library\bin;' + $env:PATH
& 'E:\Mini\envs\mathmodel\python.exe' -c "import numpy as np; print((np.eye(3)@np.eye(3)).sum())"   # 前置 → 3.0，退出码 0
& 'E:\Mini\envs\mathmodel\python.exe' code\make_figures_extra.py                                    # 前置 → 7 张图，退出码 0
```

### R-E11 派单判交付要三层，不能只看"文件存在"

**规定**：`landed()` 判"成员交付了"必须同时满足：①契约文件名存在且 > 0 字节；
②mtime 晚于派单时刻（`run_squad.py` 每波先 `crew.stamp()` 再 `dispatch()`）；
③内容像真活（`ledger.json` 的 `records` 非空且每条有出处（`url` 或 `source`）+`sha256`+`fetched_at`；Markdown 产物含 `VERDICT:`）。

**为什么**：端到端第一次跑时 W0 报"1/2 落地"，实际是 `new_verify.py` 补的
81 B 空壳 `data/ledger.json`（`{"records": []}`）被当成交付，数据溯源手一行都没写。
只补 mtime 也挡不住"动了一下但没真抓数据"的空壳，所以第 ③ 层按文件类型给最小内容要求。

**验证**：`& $PY -c` 造四份假产物跑 `crew.landed()` —— 空台账、缺 sha256 都须 False（键名用 `source` 的真台账须 True，实测 17 条真记录一开始被误判），
合规记录 True，无 `VERDICT` 的 md False。实测输出 `A False / B False / C True / D False`。

### R-E12 判交付要三层，且不许把 `BLOCKED` 当没干活

**规定**：`landed()` = ①契约文件名存在且 > 0 字节 ②mtime 晚于派单时刻（`crew.stamp()` 再 `dispatch()`）③内容像真活（`ledger.json` 的 `records` 非空、每条有出处（`url` 或 `source`）+`sha256`+`fetched_at`；Markdown 产物含 `VERDICT:`，且首行自报 `BYTES n` 必须等于磁盘真实字节）。`crew.outcome()` 另分 `delivered/blocked/failed/missing`，遇 `blocked` 立即 STOP，不等超时。

**为什么**：端到端实跑一次撞出四个假信号 —— 81 B 空壳台账被判"已交付"；数据溯源手用 `source` 键被全判"缺 url"；`BLOCKED: out/00-problem.md` 的产物 74 B 写于 19:54:42 却被空等到 660 s 超时；`00-problem.md` 首行写着 `BYTES 00000` 而磁盘 31,857 B。**检查器本身也会骗人**：第一版用 `len(txt.encode())` 比 `read_text()` 归一化后的串，永远相等，得改成 `p.stat().st_size`。

**验证**：`python _e2e/bytes_probe.py <tmp>` 须输出 `BYTES 00000 (wrong) -> 首行自报 BYTES 0，实际 38`；`python _e2e/content_probe.py <tmp>` 须输出空台账 False、缺 sha256 False、好记录 True。

### R-E13 计时类数字必须报 3 次中位，并标明"不可再现"

**规定**：任何写进报告/论文的"单次耗时、总耗时、加速比"必须是 3 次独立运行的中位数，并同时写明测量口径（样本数、冷启动是否剔除、是否串行）。只跑一次的数字只能写成量级（"约 50 ms 级"），不许写成 53.657 这类小数。

**为什么**：端到端实跑里 `02-solve.md` 报 `median_ms 53.657 / total_ms 12515.443`，我照它给的命令连跑三次得 50.042 / 53.738 / 55.918 与 11665.1 / 12172.3 / 12817.2 —— **结构结论（同一 sha `d14cfb53fd9bd607`）可再现，计时数字不可再现**。这与本机台账里"同方法单次噪声 ±56%"是同一现象。

**验证**：连跑三次 `code\solve_model.py`，比较输出行的 `timing:` 字段；`median_ms` 三次之差应落在报告所报中位数的 ±10% 内，否则报告里的数字要改成区间。

### R-E14 新建脚本必须先自测派单路径

**规定**：任何新写的派单/调度脚本，**在派给成员之前**先用 `--dry` 或单成员短线跑一次；
改过 `crew.py` 的 JS 注入段（`_JS_BASE` / `push_briefs` 的 node 脚本）必须重跑一次真实派单。

**为什么**：`crew.py` 第一版写完没跑，六处缺陷一个都没暴露 —— `{{ }}` 没被 format 展开
（`SyntaxError: Unexpected token '{'`）、硬编码 `TEAM_NAME`（`ReferenceError`）、`node -u`
（`bad option: -u`）、动态 `import ... + process.argv`（`SyntaxError: Unexpected token '+'`）、
按名字找成员而不是按 id、`wait()` 的 `+`/`or` 优先级把日志打成 `landed=`。
这些全部是"能 import 就算写完"掩盖掉的。

**验证**：`run_squad.py --dry` 应打出 8 波 13 人及各自依赖与输出路径（不碰 API）；`crew.list_members()` 应返回 13。
```powershell
& $PY "$MM\scripts\run_squad.py" $P --dry      # 依赖链与输出路径表
& $PY -c "import sys; sys.path.insert(0,r'$MM\scripts'); from mmkit import crew; print(len(crew.list_members()))"   # 13
```

### R-E15 断言必须有负对照

**规定**：新增一个检查/断言，必须**先把它改坏**证明它会红，再还原证明它会绿。没做过负对照的
断言只能算"没报错"。

**为什么**：`test_runbook.py` 里"§9.2 的未关闭项"第一版写成"文档中出现'队号'二字"，
把那一格改成"队号已填"照样 PASS —— **空过了**。改成从 `new_paper.py` 正则读出
`\baominghao{…XXXXX}` 的实际内容再要求它逐字出现，负对照才 FAIL。

**验证**：改坏一格 → `unittest` 必须 `FAILED` → `Copy-Item` 还原 → 必须 `OK`。
```powershell
Copy-Item "$MM\RUNBOOK.md" "$env:TEMP\rb.bak" -Force
# 把 §9.2 那一格改成"队号已填"，跑 unittest，应见 FAIL
Copy-Item "$env:TEMP\rb.bak" "$MM\RUNBOOK.md" -Force   # 还原后必须 OK
```

---

### R-E16 附录列全量源码后，页数锚点必须重验（锚点会漂移）

**规定**：往附录里加源码清单后，**必须重跑 `body_pages()` 的三夹具自测**（真稿 / `_e2e\E1` /
`_smoke\P9`），三个都报出同一口径的页数才能往下走。锚点只能用"目录之后**第一个**行首标题
形态命中"，不许用"最后一个宽松命中"。

**为什么**：附录 E 补到 31 个脚本后，`body` 从 30 变成 **112**。原因是若干脚本的源码里
本来就有字面量 `"Appendix A"`（它们是查附录的探针），"最后一个命中页"于是被后文的代码
带走。这是同一个函数第 **五** 次因为"锚点字符串出现在被测文本里"出错（前四次：目录页也列
Appendix A；`Page N of` 撞上正文；`Appendix` 撞上目录；`\f` 之后行首不是 `^`）。
官方模板还会把附录标题编号成 `I. Appendix A: Code`，所以锚点要允许罗马数字前缀。

**验证**：`python -c "from mmkit import gauntlet as G, paths; P=paths.find_paper(r'E:\数学建模\APMCM2025_C'); c=G.check_compliance(P); print(c.total_pages, c.body_pages, c.distinct_of, c._numbers_are_contiguous)"`
→ 必须 `134 30 1 True`；`_e2e\E1` 与 `_smoke\P9` 必须都得 `body=3`。

---

## R-M 建模与数据
**验证**：`$dst='E:\x'; Write-Output "${dst}\a.txt"` 输出 `E:\x\a.txt`（而不是 `E:` 被吃掉）
### R-M01 每个数字必须有 ledger 记录，禁止记忆型数据
**规定**：正文任何外部数字都要能追到 `data/ledger.json` 里一条带 `sha256` 的记录（`MMKit.provenance.Ledger`）。
`n_sources`/`n_records` 由脚本统计，不许手写。
**为什么**：官方 2026 规则要求数据可溯源；本项目的 54 源 / 922,942 条全做过哈希核对。
**验证**：`python -c "from mmkit import provenance as P; L=P.Ledger.load(); print(L.n_sources, L.n_records)"`。

### R-M02 官方站点抓不到只能报"未验证"
**规定**：目标站点超时/403/412 时，结论写"未验证"，不许写成"不存在"或"数据为 0"。
**为什么**：Comtrade 对"没有该伙伴的出口"是**省略该行**而不是返回 0。把省略读成 0 会得出"出口归零"的
错误结论（本项目 2025 年 6–9 月中国目的地就是这么差点写错的）。
**验证**：在 ledger 里搜 `value` 是否为 `null`；`null` 与 `0` 在正文里必须用不同措辞。

### R-M03 熵权法用极差归一，TOPSIS 用向量归一，不许混
**规定**：熵权法 `z=(x-min)/(max-min)`（它把 `z/Σz` 当概率）；TOPSIS `r=x/√Σx²`（它对超出观测范围的
输入保持单调）。两者写进同一函数就一定会混。
**为什么**：混用会把两个指标的权重压到 0.0006 与 0.0003（1206 倍差），且不会报错，只会让结论变得"平滑"。
**验证**：两个归一化函数各跑一组含异常值的数据：极差归一会饱和到 [0,1]，向量归一不会；`python -c "from mmkit import verify_numbers as V; V.main()"`
### R-M04 复合评分是相对量，扩样后必须重新归一
**规定**：往 TOPSIS 里追加预测年份时，范数、权重、理想点全部在**扩样后的候选集**上重算，并在正文说明
"扩样后的数值与原样本不可数值比较，只有序关系可比"，序关系要代码验证
（`np.argsort(np.argsort(...))` 比对）。
**为什么**：直接用 GM(1,1) 外推 `C_i` 得到 1.38/1.67/2.03，而 `C_i∈[0,1]`；用冻结的 min-max 则会把
"超出观测最大值"当成恶化，使当年评分从 0.95 掉到 0.73。
**验证**：扩样前后各存一份评分 JSON，`np.argsort(np.argsort(a))` 与 `np.argsort(np.argsort(b))` 前 n 位一致
### R-M05 离散开关与连续参数必须分开报
**规定**：模型里若有制度性开关（禁运、配额触发、halt），必须单列一张"开关贡献了多少方差"的分解，不许
混进参数敏感性里一起报。
**为什么**：本项目测得 halt 解释美国进口量方差的 **94.6%**，而连续参数框内关税解释 **96.4%**、弹性只解释
**3.1%**。混在一起报会得出"关税是主因"的相反结论。
**验证**：分解 JSON 里 `halt_us` / `tau1` / `sigma` 三项占比之和≈100%，且单独报 `halt_us` 那一行
### R-M06 惰性参数必须做检验，并写明它在什么条件下才起作用
**规定**：对每个参数做 ±10% 扰动，记录结论是否变化；完全不变的参数要么删除，要么写成"阈值面/触发条件"
的正面结论。
**为什么**：本项目的 diversion 参数在 σ6.5/τ47% 下 0.2/0.5/0.9 三个取值给出一字不差的
15.788930 MMT —— 因为它只加到容量上限上，而上限根本不 binding。而 Sobol 的"零"里有一部分是**取样盒
放错位置**造成的（临界倍数 m\* 在 τ=0.47 时是 0.818，而取样下界是 0.85），所以报"零"之前必须先算
临界面。
**验证**：`python -c "from mmkit import inertness; inertness.main()"`。

### R-M07 总量口径要写清是"指数"还是"加总"
**规定**：CES 品种数量指数与"各来源吨数之和"是两个量；替代发生时指数不动、加总上升。正文不许把加总
上升解释成"需求增加"。
**为什么**：本项目 τ 从 25% 到 47% 时加总从 105.03 涨到 105.94，而 CES 指数恒为 105.0327。
**验证**：同一场景同时读 `ces_index` 与 `sum(qty)`：替代发生时应出现"指数不动、加总上升"（本项目 105.0327 恒定 vs 105.94→112.59）
### R-M08 成本用基准量加权（Laspeyres），不用变动后的量（Paasche）
**为什么**：同一政策用 Paasche 算得 +1.12 bn，用 Laspeyres 算得 **−0.32 bn**，符号翻转；47% 档是
+2.08 vs **−6.77 bn**，差 2.53 倍。Paasche 用税后量做权重，等于让被子效应自己把自己抵消掉。
**规定**：成本变化量按**基准期数量**加权（Laspeyres）；用政策后数量加权（Paasche）会把替代效应重复计入。

**验证**：正文里凡是"消费者成本"必须能追到 `qX_base` 那一行代码。

### R-M09 binding 判定必须逐来源，且要看用了多少帽值
**规定**：报"上限是否起作用"时，列出每个来源的 `qty/cap` 百分比，不要只给一个布尔。
**为什么**：solver 的 `binding` 用 1e-3 MMT 容差，巴西 100.98 / 101.06 = **99.92%** 时返回 False，
正文若直接写"未触及上限"就是错的。
**验证**：`python -c "from mmkit import inertness; inertness.main()"` 输出里每个来源都有 qty/cap 百分比
### R-M10 网格边界解必须标星，并给出放宽后的值
**为什么**：本项目 Q3 中低端最优关税落在 0.25 网格边界；放宽到 0.40 后福利从 1.14 涨到 1.2374、
2.41 涨到 2.6777。把边界解当内点报会被评审一眼看穿。

---

## R-T 训练
**规定**：最优解落在搜索网格端点时，表格该行加 `$^*$`，正文给出放宽网格后的值，并说明放宽到多大才不再触边。

**验证**：最优解落在 `np.arange()` 端点时表格里该行带 `$^*$`：`Select-String -Path tables\*.tex -Pattern '\^\*'` 命中数 > 0
### R-M11 网格扩一次再说"最优点"（P-M10）
**规定**：报出的最优点若落在搜索区间端点，先把上界放大一次重跑；仍贴边只能写"在 [lo,hi] 内单调、最优在边界"，不许写"最优值为 X"。
**为什么**：本项目 Q3 中低端在 0–40% 网格上真峰出现在 τ=40%（原报末值），扩网格后收益还涨 6.5%；不扩就报等于把搜索半径当结论。
**验证**：`Select-String -Path main.tex -Pattern 'boundary|grid edge|extended grid'` 命中 >0，且表格里边界行带 `$^*$`

### R-M12 成本项与补贴项必须同一价格层级（P-M43）
**规定**：补贴/税收的单位价值必须等于它所作用的那一层价格（本地价含 markup 因子 μ）；福利为正的推荐政策，必须在修正记账后仍为正才算结论。
**为什么**：本项目 Q3 补贴漏乘 μ，高端段福利高估 **1.5056 bn（= 该段 W 的 83.7%）**，"推荐 τ16%/s36%"是记账产物；按 k=1.25 正确记账后变成 τ9%/s26%/W 0.7904，k≥1.5 时 W 转负。
**验证**：`python code\q3_semiconductors.py` 的 JSON 里 `welfare` 与 `welfare_level` 用同一 μ；对 k∈{0.95,1.0,1.25,1.5} 各跑一次，符号必须一致

### R-M13 正态化口径不许在两步之间换（P-M01/P-M02）
**规定**：熵权与 TOPSIS 必须用同一个归一化口径，并在正文声明该口径的一条性质（min-max 对列单调重标定不变、向量归一会变）。
**为什么**：子代理实测混用后最大权重比 **16.337 倍**且首位在 Soybeans 与 Mid/low chips 之间翻转；冻结 min-max 会把秩压平。旧笔记写的"1206 倍差"被实测推翻。
**验证**：两个归一化函数各跑一次同一数据，`Δw` 与 `Δrank` 必须写进 JSON；`git grep -n "min-max" --\*.py` 只应出现在同一个函数里

### R-M14 账号必须有缓存字节，没有就算"未验证"（P-M16）
**规定**：ledger 里每条记录除 URL/时间/sha256 外必须留原始响应字节（或可复算的落盘文件）；缺字节的源在正文算"未验证"。
**为什么**：本项目 54 个源里 **25 个** 只有哈希没有缓存字节，等于"当时抓到了但无法再核"。
**验证**：`python -c "from mmkit import provenance as P;L=P.Ledger.load();print(sum(1 for r in L.records if not r.get('path')))"` 应为 0

### R-M15 两个抽样盒必须显式对照（P-M57）
**规定**：Sobol 盒与 MC 盒不许各自默认；必须写清两者的上下界表，并说明差在哪里、为什么不影响结论。
**为什么**：本项目两盒 **9/9 输入都不同**，所以"Sobol 给出的零"不能直接叠加到 MC 分布的形状上。
**验证**：`python code\q1_sobol.py` 输出的 JSON 里带 `input_bounds`，与 `data/q1_surrogate_meta.json` 的 `input_bounds` 逐项比对，差异行写进正文

### R-M16 预测类题必须给"同批基线"的回测，不能只报自己的模型

**规定**：凡是"预测未来"的问，必须把读者会先想到的方法（persistence、线性外推、
ARIMA）放到**同一批 origin 与同一步长**上回测，和自己的模型并列成表；自己的模型没赢
就写它没赢。不许只在正文里说"ARIMA 不适合本问题"而不给数。

**为什么**：2023 C 的四法同批回测里，一等奖采用的 ARIMA(1,1,1) 在 h=1/2/3 全部最差
（13.9 / 22.2 / 32.8 pp，合并 22.9），ICD 集成是 5.0 / 11.4 / 15.6（合并 10.7），
而且差距随步长变大。没有这张表，"为什么不用 ARIMA"只是偏好之争；有了它，就是结论。
另一个理由：这张表是**唯一**能让"我们的方法更好"这句话有分母的地方。

**验证**：`python code\verify_numbers.py` 的输出必须含 `baselines: ARIMA pooled` 与
`baselines: ensemble pooled` 两条且 `0 failed`；`tables\t_baselines.tex` 存在且含四行方法名。

### R-M17 敏感性必须有一档"联合抽样"，不能只有 OAT

**规定**：除 ±x% 单因素扰动外，必须对进入该问的全部参数**联合抽样**（≥1000 次、种子
写进 JSON），给出关键量的 5/50/95 分位，并把"结论的符号在多少比例抽样里成立"写成概率。

**为什么**：2023 C 评审第一条就是"只有 ±20% OAT，缺 bootstrap / 留一年"。补 4,000 次
联合抽样后：出口损失 9,964–31,473 辆、城市减排 22,891–80,840 t、g\* 706–1,100 g/kWh，
而"仍然更干净"的概率 **99.8%**。OAT 只能回答"哪个假设最要紧"，回答不了"这个答案有多
不确定"；点估计稳不稳，只有联合抽样能说。

**验证**：`python code\run_analysis.py` 产出的 `results.json` 里必须有 `mc.n_draws >= 1000`
且含 `prob_still_cleaner`；正文引用的分位数在 `verify_numbers.py` 里各有一条 claim。

### R-T01 三个划分 + 种子写进 JSON
**规定**：train/val/test 行数与随机种子必须写进训练 JSON；测试集只评一次，且在 best-val 存档之后。
**为什么**：本项目 `data/q1_surrogate_meta.json` 有 `n_train 64000 / n_val 8000 / n_test 8000`、种子
20251113/20251114；从 `.pt` 独立复算 11 个输出 max|ΔR²|=0，才算"无泄漏"。
**验证**：`python -c "import json;d=json.load(open('data/q1_surrogate_meta.json'));print(d['n_train'],d['n_val'],d['n_test'],d['seed'])"` 四个数齐全
### R-T02 标准化统计量只用训练集
**规定**：`mean`/`std` 只从 `X_train` 算，验证集与测试集沿用训练集的统计量。
**为什么**：用全量统计量等于把测试集的均值方差泄漏进训练，R² 会虚高且无法在真实预测中复现。
**验证**：训练脚本里 `mean`/`std` 必须来自 `X_train`；`Select-String -Pattern 'X_all.*(mean|std)' code\q1_surrogate_train.py` 命中 0

### R-T03 训练期必须有 nvidia-smi 采样证据
**规定**：`logs/gpu_during_train.py` 与训练**并发**运行，每秒采样一次利用率/显存/功耗，输出落到
`logs/gpu_during_train.txt`。
**为什么**：事后跑一个 512×512 的 matmul 微基准不能证明"这次训练用了 GPU"。本项目实测 131 个样本里
**124 个**非零利用率、峰值 44%、190 MiB、19.88 W（空闲基线 0 MiB / 15.7 W）。
**验证**：`logs/gpu_during_train.txt` 非空，且采样窗口与训练窗口重叠（mtime 落在训练开始与结束之间），非零利用率样本占比 > 50%
### R-T04 R² 极高时必须给"任务本身有多容易"的对照
**规定**：held-out R² > 0.999 时，同测试集上跑一个全二次多项式做对照，两个数一起报。
**为什么**：本项目 55 项全二次已到 0.997–0.9985，而网络是 533,771 参数。只说 0.99998 会读成
"网络学到了很多"，实际是"目标函数本身光滑"。
**验证**：审计 JSON 里同时存在 `poly2_quadratic_r2` 与 `n_params`（本项目 0.997–0.9985 vs 533,771）
### R-T05 至少要两件泛化检验：k 折、多种子、外推
**为什么**：单次划分的 0.99998 可能只是这一刀切得好。本项目 5 折 mean 0.999981 / sd 9.2e-6，3 种子
mean 0.999991 / sd 2.5e-6，外推（训练 σ≤6，测试 σ>6）0.999989 → 0.999319（掉 6.7e-4）。
**规定**：至少两件泛化检验：k 折、多种子、外推实测；外推必须报盒子外的退化幅度。

**验证**：审计 JSON 至少三件：`kfold`、`multiseed`、`extrapolation`，每件都有 R² 数字
### R-T06 使用范围必须写在边界上
**规定**：代理模型只在设计盒内使用；正文必须写"超出盒子的退化幅度"和"没有任何结论依赖它超出盒子"。
**为什么**：外推掉 6.7e-4 看似小，但那只是盒边，再远没有证据。

---

## R-W 撰写
**验证**：正文里 `Select-String -Pattern 'beyond the box|out-of-box|extrapolat'` 命中 > 0，且紧跟一个退化幅度数字
### R-W01 摘要四段式且按序，段首 \textbf{}
**规定**：`Task / Model / Results / Validation` 四段，顺序固定，每段 `\textbf{...}` 起头。
**为什么**：官方规则原文说摘要占相当大比重，简单重复题目或复制引言样板"一般将被认为是没有竞争力的"；
16 篇一等奖实测：模型命名 16/16、具体结果 15/16、验证 15/16、逐问 13/16、背景 9/16。
**验证**：`python code\check_abstract.py` 退出 0，且四段 `\\textbf{Task|Model|Results|Validation}` 按序出现
### R-W02 摘要数字 ≤8 个、密度 ≤2/100 词
**为什么**：16 篇一等奖中位数是 **2.5 个不同数值、0.73/100 词**。本项目曾写到 44 个、11.25/100 词
（p100，17 倍中位数）—— 那不是"更充分"，是偏离评审习惯。改到 5 个 / 0.99 后回到 p62/p56。
**规定**：摘要数字 ≤8 个、密度 ≤2/100 词；数字必须带单位或基准。

**验证**：`python -c "import json;d=json.load(open('refs/project_vs_awards.json'));r={x['metric']:x for x in d['percentiles']};print(r['abstract_numbers']['project'], r['abstract_density']['project'])"` 分别 ≤8、≤2
### R-W03 每个数字写清口径
**规定**：报数必须带分母、基准年、名义/实际、是否年化。两条口径不同的结论不许并排放在一句里充当同一
口径的结论。
**为什么**：本项目 Q4 确定性累计 411.9 与蒙特卡洛均值 183.0（区间 [27.9, 353.6]）曾并排出现，读起来
像"点估计在自己的区间之外"；实际是一个固定税率、一个每年重抽税率。
**验证**：抽查正文任意 5 个数字，每个都能在同一段找到分母/基准年/实际或名义/是否年化之一
### R-W04 参考文献每条带类型标记与访问日期，且 >=70% 被正文引用
**规定**：每条参考文献必须有 [M]/[J]/[R]/[DB/OL] 之一、URL 的访问日期；>=70% 的条目要在正文被引用（cite 或 [n]）。
**为什么**：本项目曾被评审判 7 项 FAIL，其中参考文献 18 条全无 [M]/[J]、URL 只写年份、正文只引 2 条。
**验证**：`python scripts\gauntlet_check.py` 里 `R-W04 references have type markers` 与 `>=70% references cited` 两行均 PASS

### R-W05 U.S./US、optimisation/optimization 全文统一
**为什么**：见本条的实测数字与被评审判定的历史。

**规定**：选一套，全文一致（本 skill 默认美式 `U.S.` + `optimization`）。
**验证**：`Select-String -Path main.tex -Pattern '\bUS\b'` 命中 0（本 skill 默认 `U.S.`）；`optimisation` 同样命中 0
### R-W06 不许出现"众所周知""显而易见""应该没问题"这类无证据句
**为什么**：见本条的实测数字与被评审判定的历史。

**规定**：不许出现"众所周知""显而易见""应该没问题"这类无证据句；不用「考虑全面」「结果合理」形容自己的模型，此类评价必须换成数字。

**验证**：`grep -n "众所周知\|显而易见\|应该没问题" main.tex` 必须为空。

### R-W12 反事实数必须由脚本产出，段落里只许抄不许算

**规定**：凡是"若指数从 A 升到 B，损失就变成 C"这类反事实/情景数字，必须在 `code/run_analysis.py`
里成为一个具名产物（例：`q4.stress_index_080 = {price_pct, quantity_pct, lost_units}`），并且正文那句
必须被 `code/verify_numbers.py` 的一条 claim 绑住。手算出来的数不进正文。

**为什么**：Q4 曾经印过"index 0.62 → 0.80 would raise the price effect to **10.7%** and the lost
volume to **55,700** units"。这两个数是旧的 `τ=P/0.45` 口径留下的死数；口径改成 `τ=0.10·P` 之后真值是
**4.80% / 25,068**，而 `verify_numbers.py` 当时只绑了摘要和主链，没绑这句 —— 于是 `review_check`、
`gauntlet`、`verify_numbers` 三道门全绿，错数照样留在稿子里。它和"表格里的数与正文互斥"（D1）是同一类洞：
**判据覆盖不到的段落，就是错数活下来的地方**。

**验证**：`python code/verify_numbers.py` 的输出必须含 `Q4 stress price` 与 `Q4 stress lost units` 两条且
`0 failed`；负对照：把正文里的 `4.80\%` 改成任意别的数，重跑必须 `[FAIL]`。

---

## R-V 验收（写论文前的门）

### R-W07 正文页数有三个数，必须一起报，且真值只有一个（P-W01/P-W07）
**规定**：报正文页数必须同时给出 `numbered_pages`（带页眉的页数）、`M`（页眉分母）、`body_pages`（真值）；真值只取"第一个**同时**含页眉与 `Appendix A` 的那一页上页眉的 N"。目录页也写 `Appendix A`、摘要页无页眉，这两点让所有"首个出现 Appendix A"和"总页减前置页"的算法都错。
**为什么**：同一份 108 页 PDF，正确值 30，`compare_to_awards.py` 的旧算法给 28，另一种试算给 29。本稿前置页是 3 页（摘要 1 + 目录 2），恒差 1。
**验证**：`python -c "from mmkit import gauntlet as G;c=G.check_compliance();print(c.total_pages, c.body_pages, c.header_markers, c.distinct_of)"`，三个数一起看；`c._numbers_are_contiguous` 为 False 时数字作废

### R-W08 参考文献条目必须留在正文编号范围内（P-W02）
**规定**：`thebibliography` 放在 `\appendix` 之前；搬进附录会让正文 `[n]` 引用归零、paper 的 references 指标从 8 掉到 0。
**为什么**：本项目曾为省一页把书目搬进附录，`compare_to_awards.py` 随即把 `references` 量成 0，而它正是奖项基准带的一项。
**验证**：`python -c "import json;d=json.load(open('refs/project_vs_awards.json'));print([r['project'] for r in d['percentiles'] if r['metric']=='references'])"` 必须 > 0

### R-W09 断页只在结构性位置，且必须量 Δ（P-W03/P-W12）
**规定**：`\newpage`/`\clearpage`/`\enlargethispage` 只许用在结构边界（正文→附录、附录→书目）；每加一处必须重编译并量正文页数 Δ，Δ=0 就删掉。
**为什么**：一个孤立 `\newpage` 稳定 **+1 页**；而 `\enlargethispage` 插错位置（插在溢出页页首而不是上一页页尾）测出 Δ=0，白改。
**验证**：改前后各跑 `python scripts\gauntlet_check.py`，比较 `R-V01 body <= 30 pages` 行里的 `body=`

### R-W10 列声明与单元格数必须配平（P-W06）
**规定**：每张 `tabular` 的列声明与每行单元格数逐列数过；不配平时多一列会**静默**编译成功并留空列，少一列才报 `! Extra alignment tab`。
**为什么**：本项目曾把 5 格数据配 3 列声明，编译通过、末列全空，表格一直到渲染检查才发现。
**验证**：`python -c "import re,io;s=io.open('main.tex',encoding='utf-8').read();print(len(re.findall(r'\\begin\{tabular\}',s)))"` 与逐表核对；渲染后 `pdftoppm` 打开看一眼末列

### R-W11 任何"官方要求 X"必须指到原件页码，工作区旧笔记不算依据

**规定**：写进论文或规定里的每一条"官方要求"，必须能给出**原件 + 页码/行号**。扫描件（无文本层）
必须转图逐页读后再引，并在引用处注明"扫描件转录，见 `rule_pg-N.png`"。**工作区里自己以前写过
的说法，一律不能作为依据。**

**为什么**：本项目从某一版笔记起，`RULES.md` 与论文附录 B 都写着"2026 年新增 AI 工具使用声明，
不写就取消资格"。2026 官方规则 PDF 是 6 页扫描件，`pdftoppm -r 110` 逐页读 p3–p6 后，**全文
没有任何 AI / 人工智能 / 大模型 条款**；能引的只有 p3 那句"所有引用的资料必须注明出处，如有
参赛队未注明引用的内容的出处，将被取消参赛资格"。一条凭印象写下的"官方要求"在项目里活了
好几轮，还进了论文附录 B（已改为"自愿披露"并注明真实依据）。判据表 `_official_criteria.json`
的 C12 因此从 `verified` 降为 `不在官方规则内（p3–p6 逐页读图后未发现 AI 条款）`。

**验证**：`python -c "import json;d=json.load(open(r'E:\数学建模\APMCM-PROBLEMS\_official_criteria.json',encoding='utf-8'));print([(c['id'],c['status'][:12]) for c in d['criteria']])"`
→ C12 必须显示"不在官方规则内"；且 `Select-String -Path main.tex -Pattern 'required by the regulation'` **0 命中**。

### R-V01 正文 ≤30 页，页数取页眉分子
**规定**：正文页数 = 第一个 `Appendix A` 页页眉里的 `Page N`。不是 PDF 总页数，也不是
`pdftotext` 分页后的页序。
**为什么**：目录页也写着 "Appendix A"，按文本首匹配会把正文算成 2 页。本项目 `gauntlet.body_pages`
就是为这一条写的。
**验证**：`python -m unittest tests.test_gauntlet.TestBodyPages -v`。

### R-V02 页眉判定：全篇只有一个分母，且分子从 1 连续
**规定**：`len({分母})==1` 且分子去重后 == `1..n`。
**为什么**：前端 3 页不编号、未编号附录页也没有页眉，所以 `分子数 == 总页数` 这个判据会把任何正常论文
判成不合格（105 ≠ 108）。反过来，取"分子去重个数"会恒得 1。
**验证**：`python -c "from mmkit import gauntlet as G;c=G.check_compliance();print(c.distinct_of, G.Compliance.contiguous(c), c._header_numbers)"` 应为 1 / True / 连续序列
### R-V03 全文 0 个中文字符
**规定**：编译产物里 CJK 字符数为 0（含参考文献与页眉页脚），一个汉字都不许留。
**为什么**：官方要求全英文。`gauntlet.check_compliance().cjk_chars` 统计 `[\u4e00-\u9fff]`。
**验证**：`python -c "from mmkit import gauntlet as G;print(G.check_compliance().cjk_chars)"` 必须为 0

### R-V04 全文 0 处 "university"
**规定**：机构名不许出现在任何位置，包括参考文献里的出版社。Oxford University Press → Oxford:
Clarendon Press。
**为什么**：这一条曾让 PDF 里出现一次 "university"（[15] Corden 1974），被评审判为机构名泄漏。
**验证**：`python -c "from mmkit import gauntlet as G;print(G.check_compliance().university_hits)"` 必须为 0
### R-V05 队号不是占位符
**规定**：`\baominghao{}` 必须是真实队号，不许留 `X{3,}` 形态的占位符。
**为什么**：官方要求页眉只含队号与页码；占位符会让整篇论文无法与参赛队对应，且合规检查会直接判 FAIL。
**验证**：`grep -n "baominghao" main.tex` 里不许有 `X{3,}`。当前 `APMCM25XXXXX` 是**已知未关闭项**，
提交前必须填。

### R-V06 正文数值与 JSON 对账 0 失败，断言数 ≥ 全部数值的 70%
**规定**：`mmkit.verify_numbers`；字符串匹配必须词边界 `(?<![\d.])needle(?!\d)`。
**为什么**：裸 `in` 会把 `"16"` 匹配进 `"2016"`，于是"对账"永远通过、什么也没查。
**验证**：`python code\verify_numbers.py` 末行 `0 failures`，且断言数与 JSON 数字总数的比值 ≥ 0.70
### R-V07 基准带两侧同口径
**规定**：项目和一等奖论文都走同一个 `award_standard.measure()`，都喂 `pdftotext` 文本。
**为什么**：拿 LaTeX 源码对 PDF 文本，图表数为 0，任何论文都会被判"图表不足"。
**验证**：`python scripts\gauntlet_check.py` 里 `R-V07 band both sides` PASS（项目与基准走同一个 `award_standard.measure`）
### R-V08 交付前必须真的打开图看一次
**规定**：每张图生成后 `read_image` 看三件事：标注是否压线、刻度是否截断、ytick 是否出现 `1e18` 这类
量级错。
**为什么**：本项目踩过三次：标注压曲线、`v/scale` 写成除法导致 `1e18` 轴、`\\%` 在 matplotlib 里原样
打印成反斜杠百分号（matplotlib 要 `%`，只有 LaTeX 要 `\%`）。
**验证**：每张 `figures\*.png` 生成后 `read_image` 打开过一次；日志里每个图名都有对应的读图记录

### R-V09 产物比脚本旧就必须逐条解释，`verify_numbers` 全绿不算证据
**规定**：`mmkit.freshness`；`gauntlet_check.py` 的 `R-V09` 以 KNOWN OPEN 形式打印全部配对，
每一条只有两种合法状态 —— **重跑**，或**说清"旧是应该的"**（写进 `RUNBOOK.md` §9.2.1）。
**为什么**：`code\q1_sobol.py` 比它产出的 `data\q1_sobol.json` 新 17 h，而 `verify_numbers.py`
当时仍报 `0 failures` —— 旧产物撑住了断言，所以"绿"恰恰是过期的证据。重跑后
`ST[σ][q_US]` 0.030786 → 0.030591，差 1.95e-04 = **5.4 倍标准误**（不是 GPU 抖动：连跑两次 431 叶 0 差）。
**验证**：`python -c "…freshness.report(find_paper(…))"` 的每一行都对应 §9.2.1 的一格。

### R-V10 自动定位"被检对象"时，禁用字典序/最新/最大这类巧合判据
**规定**：先认规范名（`main.pdf`、`<目录名>.pdf`、`\baominghao` 的 PDF），都没有才退到显式规则，
并且**把选中的文件名打印出来**。
**为什么**：同一个错误犯了三次，每次都不报错、只报别人的问题：
①`find_paper()` 取"最新含 main.tex 的目录" → 量到 `_smoke2` 草稿，基准带全 FAIL；
②`review_bench.check_paper` 取 `sorted(glob("*.pdf"))[0]` → `APMCM2025_C` 里 `ai_usage.pdf`
（3 页）排在 `main.pdf`（134 页）之前，于是拿 AI 声明去核论文合规，报出 **7 条假 FAIL**
（无摘要页/无目录/无附录/无参考文献/页眉 0 行/占位队号 2 次/正文 3 页）；
③`gauntlet.band()` 在草稿上量到 figures=0。
**验证**：`unittest tests.test_gauntlet.TestPickPdf`（3 条：目录必须选 main.pdf、显式 PDF 路径优先、
无 main.pdf 时退到最大的那个）；`review_check.py` 首行必须打印 `pdf: main.pdf   pages: …`。
### R-V11 评审报告是快照：按它动手之前，先在当前树上重量一次
**规定**：任何一条"缺 X / 少 Y / 不合规"的结论，落地前必须用当前树重跑对应判据
（`review_check.py`、`R-V09`、`verify_numbers.py`），并把"报告怎么说 / 现在是多少"两列都写出来。
**为什么**：`review/01-compliance.md` 判 C9"附录只收 18 个 `.py`，缺 13 个"——这话在它写下的时刻是真的；
但附录随后已补到 31/31。我照着报告去"补那 13 个"，正则又没把 `\texttt{code/fetch\_data.py}` 里的
`\_` 还原，结果 30 个文件全部重复追加，`\lstinputlisting` 从 31 涨到 **61**。
发现方式是脚本自带的判据"补后 listing 数 == `code/*.py` 数"（61 ≠ 31 → exit 1）——**判据比人先发现**。
**验证**：`python -c "…re.findall(r'^\\\\lstinputlisting', open('main.tex').read(), re.M)"`
数出 31，与 `ls code/*.py` 的 31 相等；`review_check.py` 首行 `pdf: main.pdf pages: 134`。
### R-V12 判据口径必须回到原文的**限定词**：C7 只管正文，不管附录代码的注释
**规定**：`C7` / `R-V03`（不得出现中文）只统计**正文页**（前两页之后、行首 `Appendix A` 之前），
附录里的汉字单独打印但不判定。任何"整本 PDF 一把抓"的判据落地前，先回官方原文找限定词。
**为什么**：官方 2017–2023 每年 *Essay format* 的原文是
"no Chinese word should be found in the **main body** of the solution paper, the chart, etc."
（`E:\数学建模\APMCM-PROBLEMS\_rules_text\2023_APMCM_Essay_format_and_submission_specifications.txt:67`）。
旧实现数整个 `pdftotext` 输出，于是 2018A 练习稿附录里 12 个脚本的**中文注释**被算成正文违规：
实测正文 0 个汉字、附录 3207 个汉字，却被判 `FAIL`。这是判据错，不是论文错——而判据错比论文错更贵，
因为它会把所有带中文注释的源码的论文一律判红，逼着人去做"把注释翻译成英文"这种与评分无关的事。
**验证**：`review_check.py 'E:\数学建模\PRACTICE_2018A'` → `[OK] C7 chinese chars in body=0 (appendix, not judged=3207)`；
`gauntlet_check.py` → `[PASS] R-V03 zero CJK in body  body cjk=0 (appendix, not judged=3207)`。
两处判据同源（`mmkit/review_bench.py` 与 `mmkit/gauntlet.py` 用同一条行首锚点），改一处必须改另一处。

### R-V13 前置页顺序是**模板级**缺陷：摘要页必须在第 1 页，承诺书不属于英文赛项
**规定**：新论文一律从 `new_paper.py` 出骨架（它已改为 `\begin{abstract}` 直接起头）；
手写 HEAD 时不许出现 `\makecontrolsheet` 或 `\maketitle`。
**为什么**：`apmcmthesis.cls` 里 `\makecontrolsheet` 调用 `\@maketitle` 渲染承诺书，并把
`\maketitle` `\let` 成 `relax`；所以"先承诺书再摘要"的写法既占错第 1 页，又让后面的 `\maketitle`
变成空操作——**删一行不够，必须两行都删**。2018A 练习稿第一版就是这么写的，`C4 p1 has summary=False`
直接判红。英文本的官方格式是"第 1 页摘要页、第 2 页目录"（2023 规范 p.67 起；2026 扫描件 p3/p4 同义），
承诺书是中文赛项那一套。
**验证**：`pdftotext -f 1 -l 1 main.pdf - | head` 必须出现 `summary sheet`；
`review_check.py` 的 C4 两条同时 `[OK]`；`gauntlet_check.py` 的 `R-W11 front matter order` 打 `['summary','contents']`。
### R-V14 图内文字必须量"印刷后的有效字号"（≥6 pt），不能靠看图
**规定**：交稿前必跑 `mmkit.figfont`（`python -m mmkit.figfont <main.pdf>`）；判据是
"任何 **3 个字符以上**的 span 不得低于 **6.0 pt**"。单个字符（面板字母 `b`、刻度 `25`、`∗`）
不判——那是常规下标尺寸，正文里同样存在。
**为什么**：`\includegraphics[width=0.55\linewidth]` 会把图里的 7.5 pt 标签乘成 **4.1 pt**，
而 4 pt 与 8 pt 在任何屏幕缩略图里都一样"清楚"——**看图永远看不出这个问题**，只能从 PDF 里读磅值。
本工作区实测：2025C 主稿 `min=2.71 pt / violations(≥3字符且<6pt)=4024`（Fig 的 `Consumer cost`
只有 3.06 pt）；2018A 练习稿修前 `min=4.20 pt / 94 个 span < 6 pt`，修后 `min=4.98 / violations=0`。
**验证**：`python -m mmkit.figfont 'APMCM2025_C\main.pdf'` → `FAIL`（4024）；
`python -m mmkit.figfont 'PRACTICE_2018A\main.pdf'` → `PASS`（0 违规、6 个单字符）。
修法是两条一起动：figure 自己的 `fontsize`/`figsize` 放大 **且** `\includegraphics` 的
`width` 放大——只改一处会被缩放抵消。
**解释器坑**：`pymupdf` 只装在 `E:\Mini\envs\mathmodel`，`D:\Python` 没有。用 `D:\Python` 跑
`gauntlet_check.py` 时直接 import figfont 会 `ModuleNotFoundError: No module named 'fitz'`，
于是"论文没问题"被报成 FAIL。判据缺工具 ≠ 判据不通过：`gauntlet_check.py` 现在会依次探三个
解释器，全都没有就打 `SKIP` 并把该用的命令打出来（实测输出里会写 `(measured by python.exe)`）。

### R-V15 一切"锚点"必须覆盖模板的真实编号形态（罗马 / 字母 / 阿拉伯），且**先量模板再写正则**
**规定**：任何靠"标题行"切页、切正文、数章节的判据，正则必须同时吃三种编号形态：
阿拉伯（`4 . 3 . 1 Foo`，点两侧可能有空格）、罗马（`XII. References`）、
**字母**（`A. Appendix A: Code`，`\appendix` 之后 `\thesection` 变成字母）。
写完必须拿**至少三个夹具**（真稿 + 两个 smoke）打一遍，并且**打印命中数**——0 命中不许当 PASS。
**为什么**：同一个"锚点被被测文本干扰"的故障在这个工作区已经复发 **8 次**，每次都不是同一个正则：
①`section_titles()` 漏掉 `4 . 3 . 1` 与 `XII.` → 16 篇一等奖里 7 篇量到 `sections=0`、基准中位数
变成 **1**，练习稿的 `sections=0` 因此被误判 "inside IQR"；②`_body_end_page()` 用页内任意位置匹配
`Appendix\s+A`，正文里一句交叉引用就把正文切成前 17 页；③`gauntlet.body_pages()` 的附录锚点前缀
只写了 `(?:[IVXLC]+\.|[0-9]+\.)`，而实际标题是 **`A. Appendix A: Code`**（字母 A 不在 IVXLC 里）
→ `body_pages=0`、`findings=['Appendix heading page not found']`，一篇 66 页的合规稿被判"找不到附录"。
**验证**：`gauntlet.check_compliance()` 必须打印 `body>0` 且 `findings=[]`；
三夹具同跑 `total 68 body 18 markers 66 contig True` / `E1`、`P9` 各 `body=3`；
`award_standard.main()` 重算后 `median sections` 必须 ≥ 10（≤2 就是尺子坏了，代码里已有硬检查）。
**判据自检的第一步永远是"这条尺子量得出已知答案吗"**，不是"论文对不对"。

### R-V16 会漂的量（耗时/显存/帧率）不许绑单点，只许印**覆盖实测的区间**
**规定**：`verify_numbers.py` 里为这类量单列 `RANGES`：正文印的 `[lo,hi]` 必须**包含**
`data/*.json` 记下的那次测量（三次运行的 min/max）；印窄了就 FAIL，印宽了没人管。
一次性的、确定性的产物（AUC、p、阈值、CoM）仍然逐点绑，容差按印刷小数位定。
**为什么**：2018A 的"640× 实时"从 5.0 ms 改到 4.2 ms，再回填三次测量得 3.9--5.4 ms——
同一台机器、同一份代码，脚本级重跑三次分别是 7.6 / 8.7 / 9.7 ms（差 28%）。
把这种量绑成 `8.7` 的结果是每次重跑都要手改正文，改到后来没人再跑校验——**校验一旦烦人就会被绕过**。
**验证**：`verify_numbers.py` 结尾必须打印 `ranges: 5 bands checked`；
故意把正文的 `7.4--10.5` 改成 `7.4--9.0` 后必须 FAIL 并指出
`printed band does not cover measured [7.55, 7.71]`。

### R-V17 占位/无效这类判据必须查**语义**，不能只查字形
**规定**：C11 一类判据分两层——字形层（`XXXXX`、`apmcm2\dXXXXX`）+ 语义层（正文自称
"not a valid team number"、"identifier is a placeholder"、"队号待填"）。语义层命中同样 FAIL，
且要打印页码与句子前 70 字符。
**为什么**：2018A 定稿时正文印着 `the identifier APMCM18PRAC1 is deliberately not a valid
team number.`，而 `review_check.py` 报 `placeholder team number hits=0` —— 因为正则只认
字形占位。评审员一眼读到该句就判了废稿级：**官方条款看字面，不看正则**。
**验证**：`review_check.py PRACTICE_2018A` 必须打印
`self-declared invalid identifier in body=0`；把该句塞回 main.tex 重编译后必须变 `=1` 并 FAIL。
`mmkit/review_bench.SEM_PLACEHOLDER` 对旧句 `True`、对定稿 PDF 全文 `False`（负对照实测）。

### R-V18 派评审之前必须先生成口径基线；报告与基线不符必须并列两口径
**规定**：`review/00-metrics.md` 由 `scripts/run_review.py metrics`（**脚本**，不是审读员）生成，
内容 = 被测件（main.pdf / main.tex / 数据层）的 mtime + sha256 + 四条机器判据的原始输出。
派单前必须存在；任何报告里的数与它不同时，必须并列两个数并写明"我在何时对哪个文件重跑"。
论文侧不要手写这个文件（它要能被复算）。
**为什么**：2018A 第一轮 8 个审读员各自重跑同一组命令，报告里同时出现 68 页与 72 页两种口径；
4 条"废稿级"里有 3 条评的是我改之前的 PDF（R-V11 的第二次复发）。基线文件的真正作用是
**让"谁在什么时候看的什么文件"变成可核事实**，而不是省几条命令。
**验证**：`run_review.py metrics <论文目录>` 必须写出 `00-metrics.md`，且五个小节
（被测件身份 / review_check / gauntlet_check / figfont / verify_numbers+freshness）都有 `exit=`;
数据层比 `main.pdf` 新 60 s 以上时必须出现 `WARNING：数据层比 main.pdf 新`。
`tests/test_review_crew.py::test_every_brief_points_at_the_metrics_baseline` 守住"每个 brief 都被告知基线"。

### R-V19 跨进程取输出必须显式 `encoding="utf-8"`，否则 `text=True` 会静默返回空
**规定**：`subprocess.run(..., capture_output=True, text=True)` 若子进程被设了
`PYTHONIOENCODING=utf-8`（本项目所有判据都这么设），**必须同时给 `encoding="utf-8", errors="replace"`**；
或者干脆 `text=False` 自己 `.decode("utf-8","replace")`。禁止依赖 locale。
**为什么**：Windows 的 `locale.getpreferredencoding(False)` 是 GBK，`text=True` 让
`subprocess` 在**读取线程**里用 GBK 解码 UTF-8 字节 → `UnicodeDecodeError: 'gbk' codec can't
decode byte 0xa8 in position 100`，该异常发生在读取线程里，`run()` 返回的 `stdout` 是 **None**。
现象极像"这个脚本什么都没打印"：新写的 R-V06 测试因此假失败（断言说"gauntlet 没打印 R-V06"，
而实际上那一行就在输出里）。更坏的方向是反过来——把"判据跑崩了"读成"没有命中"。
**验证**：`tests/test_review_crew.py::TestStubIsNotAGreen` 之前报
`[] is not true : gauntlet 没打印 R-V06` 且 `len_out=0`，补 `encoding="utf-8"` 后同一断言变绿。
`run_review.py::_run` 用的是 `text=False` + 手工 decode，属正确写法，可作为模板。

### R-V20 名册与 brief 必须**同一次**写入，且读回 `min(brief_len) > 0` 才算建成
**规定**：任何"建队 / 更新名册"的调用，必须把 `brief` 一起发给宿主；
`POST /member` 的 upsert 语义是**整条覆盖**，缺 `brief` 键就等于"把 brief 写成空串"。
建完必须读回并打印 `n` 与 `min(brief_len)`，`n` 不等于名册人数或 `min(brief_len)==0` 一律判失败。
队伍简介（`description`）同样是必填：UI 卡片上"没有简介"和"这支队伍没内容"在用户眼里是同一件事。
**为什么**：2026-11-12 用户指着截图问"数学建模评审小队啥也没有啊，这两个是不同的呀，怎么混合了呢"。
实况不是混编（13 人 vs 10 人，名字无交集），而是 `run_review.py team()` 只发了
`[{"name": n, "permission": p}]` → 10 个成员的 brief 全被清成 0 字节、简介也没写，
于是 10 人小队在界面上显示成"10 位成员 / 没有简介 / 点进去什么都没有"。
同一支建稿队的 13 个 brief 还钉在冒烟夹具 `_e2e\E1` 上（上一次 `full_brief` 用的就是那个目录），
所以"内容不对"也是真的 —— 一个指向测试目录的 brief，成员照着做只会写到测试目录里。
**验证**：`run_review.py team <论文目录>` 必须打印 `members_read_back=10  brief_len min=1844  zero=[]`；另有两条必须同时成立：
- `crew.refresh_team(WS, paper)` 必须返回 `{"n": 13, "brief_min": 575, "zero": []}`；
- `tests/test_review_crew.py::TestRosterNeverBlanks` 三条：名册可由 `WAVES` 推出且 13 人不重名、
  两支队简介都 > 80 字符、`crew.py` 的 JS 模板里必须有 `cur.brief` 守卫且 `run_review.team()`
  不许再出现 `members = [{"name": n, "permission": p}]`。
- **负对照**：把 `run_review.py team()` 改回只写名册那版，界面上立刻变回"没有简介"（已实测一次）。


### R-V21 小队工作区**默认不钉**；要钉必须显式，因为钉住会污染该工作区的会话列表
**规定**：`create_team` / `refresh_team` 的 `workspace_id` 默认空串，`run_review.py team` 默认
`pin=False`；只有显式传 `workspace_id=` 或加 `--pin` 才调 `crew.workspace_id_for(path)` 去钉。
钉之前必须先问用户，因为钉住的代价是**每次派单都在该工作区的会话列表里新建一条会话**。
文件读写一律用绝对路径，不依赖会话落在哪个目录 —— 这是"可以不钉"的前提。
**为什么**：2026-11-12 同一用户的两轮反馈，方向相反，必须同时写下来才算把坑填上：
① 第一轮问"这里面的小队为什么工作区全是一个地方呢"—— 根因 `lib/index.js:2645
resolveWorkspacePin(team)` 的 `if (workspaceId === void 0) return void 0;`，不钉就由 Host 在
自己的默认目录开会话，界面 `SquadDetail.tsx:72` 显示"未绑定（用宿主默认目录）"；
② 钉了之后第二轮说"这个小队的默认还是按照原来的吧，不然我这里的会话太乱了，都没法找对话了"
—— 侧栏里"数学建模评审小队 / 题目契…"这类条目就是每次 run 建出来的会话，一天就淹掉自己的对话。
结论：**能力保留、默认关闭**。另一处坑：`GET /dsh-agents/api/state` 的 team 对象不回传
`workspaceId`，判断绑没绑只能调 `squads_read`。
**验证**：`crew.workspace_id_for(r"E:\数学建模")` 与 `…\PRACTICE_2018A` 都返回
`23b1f997-ec80-4939-85dd-30687ff8555a`、`E:\不存在` 返回 `None`（能力在）；而
`inspect.signature(crew.create_team).parameters["workspace_id"].default == ""`、
`run_review.team(paper)` 的 `pin` 默认 `False`（默认不钉）；`squads_read("61cec604-…")` 与
`squads_read("b68d6335-…")` 的返回体**不带** `workspaceId`（未绑定）。
`tests/test_review_crew.py::TestWorkspacePinOptIn` 两条必须通过。
**负对照**：显式 `run_review.py team <论文目录> --pin` 之后 `squads_read` 才重新出现
`"workspaceId"`；去掉 `--pin` 再跑一次，字段消失（已实测）。
