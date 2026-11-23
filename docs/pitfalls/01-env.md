# 环境与工具链坑位（实测）

> 审计对象：工作区 `E:\数学建模`（`APMCM2025_C` 论文仓、`APMCM2026` 环境与构建仓）
> 审计日期：2026-11-11　|　执行环境：Windows，PowerShell **5.1.26100.7627**（`pwsh` 与 `powershell` 在此机为同一版本），**以 Administrator 身份运行**，ACP/OEMCP = 936(GBK)
> 复现素材目录：`E:\数学建模\.tmp_scratch\pit\`（含 `tex\` 夹具与全部 `pe*.ps1` / `check_*.py` 脚本）
> 判定约定：**验证结果 pass = 坑存在且复现成功**；**fail = 坑不存在或已被修**（此时该条如实标注，不删条）。

## 总览

| id | 标题 | 判定 |
| --- | --- | --- |
| P-E01 | MiKTeX 缺 perl，latexmk 整体不可用 | pass |
| P-E02 | 单遍 xelatex 交叉引用留在 `??`，必须两遍 | pass |
| P-E03 | `$ErrorActionPreference="Stop"` 把 MiKTeX 的 security-risk stderr 当成致命错误 | pass |
| P-E04 | `main.log` 本身不是 UTF-16；UTF-16 来自 PowerShell 重定向产物 | fail（对原命题） |
| P-E05 | `[System.IO.File]::ReadAllText('相对路径')` 按**进程 cwd** 解析 | pass |
| P-E06 | `Get-Content` 默认按 GBK 解码 UTF-8 中文，行数与码点双错 | pass |
| P-E07 | 裸 `python` 是 3.14.6，无任何第三方库 | pass |
| P-E08 | `Start-Process` 起子系统时，大小写重复的代理环境变量让它直接抛异常 | pass |
| P-E09 | 本机**没有 `dl` conda env**；`dl` 只是 env.ps1 的 profile 名 | 记录被证实（"不存在 dl env" pass） |
| P-E10 | numpy matmul 后再 `import torch` 触发 `OMP: Error #15` | pass |
| P-E11 | `$Matches[1]` 无匹配时抛 `无法对 Null 数组进行索引。`；且会**静默保留旧值** | pass |
| P-E12 | 用 PowerShell 字符串操作改 `.py` ⇒ BOM + CRLF + 中文乱码 | pass |
| P-E13 | matplotlib 标题里写 `\%` 会渲出字面反斜杠 | pass |
| P-E14 | f-string 里写 LaTeX 千分位 `{v{,}000}` 是语法错误 | pass |
| P-E15 | `pdftoppm` 输出按**总页数**零填充（`p-01.png`） | pass |
| P-E16 | WMI `AdapterRAM` 是 32 位字段，8188 MiB 被读成 4095 MiB | pass |
| P-E17 | `xelatex -log-directory=<dir>` 目标目录存在也失败 | pass |
| P-E18 | 页数口径：`\f` 计数已等于 `pdfinfo` 页数，再 +1 会多一页 | pass（口径坑） |
| P-E19 | 编译日志重定向到同名 `<job>.log` 会让 xelatex 自己写不出日志 | 需人工裁决（见条目末） |
| P-E20 | `conda run` 在 GBK 控制台下转发 U+FFFD 时自己崩（UnicodeEncodeError） | pass |
| P-E21 | 5.1 读**不带 BOM** 的 UTF-8 `.ps1`：中文路径/中文串全烂 | pass |

---

## P-E01 MiKTeX 缺 perl，latexmk 整体不可用

- 现象（逐字，`latexmk -pdf -interaction=nonstopmode t.tex`，EXIT=1）：
  ```
  latexmk.exe : latexmk: security risk: running with elevated privileges
  Sorry, but latexmk.exe did not succeed for the following reason:
    MiKTeX could not find the script engine 'perl' which is required to execute 'latexmk'.
  Remedy:
    Make sure 'perl' is installed on your system.
  For more information, visit: https://miktex.org/kb/fix-script-engine-not-found
  ```
  且 `Get-Command perl` 为空，`& perl -v` 报 `无法将“perl”项识别为 cmdlet、函数、脚本文件或可运行程序的名称。`（`CommandNotFoundException`）。
- 根因：MiKTeX 的 `latexmk.exe` 是一个**调用 perl 脚本**的包装器；本机只装了 MiKTeX 的 TeX 组件，没有 perl 运行时，所以包装器在脚本引擎查找阶段就退出，与 `.tex` 内容无关。
- 规定：**禁止**在任何构建脚本里调用 `latexmk`（包括 `latexmk -pdf/-xelatex/-pvc/-cd`）。统一用**两次 `xelatex -interaction=nonstopmode -halt-on-error -file-line-error`** 完成构建；需要 aux 交叉引用时见 P-E02。
- 验证：
  ```powershell
  # 期望：latexmk 失败且给出 perl 缺失；两次 xelatex 成功
  if (Get-Command perl -ErrorAction SilentlyContinue) { 'UNEXPECTED: perl 已安装' } else { 'OK: perl 不存在' }
  cd E:\数学建模\.tmp_scratch\pit\tex
  latexmk -pdf -interaction=nonstopmode t.tex 2>&1 | Select-String "script engine|perl"; "latexmk exit=$LASTEXITCODE"   # 期望 exit=1
  xelatex -interaction=nonstopmode -halt-on-error t.tex > $null 2>&1; "pass1 exit=$LASTEXITCODE"                        # 期望 0
  xelatex -interaction=nonstopmode -halt-on-error t.tex > $null 2>&1; "pass2 exit=$LASTEXITCODE"                        # 期望 0
  ```
- 实测时间：2026-11-11
- 实测输出：`perl present: False`；`latexmk exit=1`；`has 'could not find the script engine': True`；`has 'perl' remedy line: True`
- 验证结果: **pass**

---

## P-E02 单遍 xelatex 交叉引用留在 `??`，必须两遍

- 现象（`tc.tex` 含 `\tableofcontents` + `\ref`，单遍编译后 `pdftotext -enc UTF-8 tc.pdf -`）：
  - 第 1 遍：`Contents 1  A  see ?? on page ??  1`
  - 第 2 遍：`Contents 1 A  1  1  A  see 1 on page ??  1`
- 根因：`\ref` 的目标页码写在 `.aux` 里，第 1 遍时 `.aux` 尚未生成/是上一版，所以第 1 遍的 PDF 里是 `??`；第 2 遍读回 `.aux` 才补上。TOC 页码同理。这与 latexmk 无关（latexmk 本来就是靠自动多遍解决这件事，但本机没有 perl 用不了，见 P-E01）。
  （本例 `\pageref{last}` 仍为 `??` 是因为夹具没加载 `lastpage.sty`，属夹具问题，不计入本坑。）
- 规定：**必须**连续跑两遍 xelatex；判定"页码对了"要读第 2 遍的 PDF，不能读第 1 遍。
- 验证：
  ```powershell
  cd E:\数学建模\.tmp_scratch\pit\tex
  Remove-Item tc.aux,tc.toc,tc.pdf -ErrorAction SilentlyContinue
  xelatex -interaction=nonstopmode -halt-on-error tc.tex > $null 2>&1
  $p1 = (pdftotext -enc UTF-8 tc.pdf -) -join ' '
  xelatex -interaction=nonstopmode -halt-on-error tc.tex > $null 2>&1
  $p2 = (pdftotext -enc UTF-8 tc.pdf -) -join ' '
  "pass1 has ?? : $($p1 -match '\?\?')"   # 期望 True（坑存在）
  "pass2 has ?? : $($p2 -match '\?\?')"   # 期望 False
  ```
- 实测时间：2026-11-11
- 实测输出：第 1 遍 `Contents 1  A  see ?? on page ??  1`；第 2 遍 `Contents 1 A  1  1  A  see 1 on page ??  1`
- 验证结果: **pass**

---

## P-E03 `$ErrorActionPreference="Stop"` 把 MiKTeX 的 security-risk stderr 当成致命错误

- 现象（逐字）：`xelatex.exe : xelatex: security risk: running with elevated privileges`，后跟
  `+ CategoryInfo : NotSpecified: (xelatex: securi...ated privileges:String) [], RemoteException` 与
  `+ FullyQualifiedErrorId : NativeCommandError`；在 Stop 偏好下脚本**直接终止**，而 PDF 其实已经生成、`$LASTEXITCODE=0`。`pdftotext` / `pdfinfo` / `miktex-dvipdfmx` 同样会打这条。
- 根因：本机以 Administrator 运行，MiKTeX 对"提权运行"发一条**非致命的警告写到 stderr**。PowerShell 把原生程序 stderr 转成 `NativeCommandError` 流；只有在**有重定向参与**（`*>`、`2>$null`、`2>&1`、`2>&1 | ...`、或捕获到变量）时，这条流才会在 `$ErrorActionPreference='Stop'` 下升级为终止性错误。实测分三种形态：
  - 裸调用（不重定向）：Stop 下**不抛**，`exit=0`
  - `| Out-Null`（只接 stdout）：Stop 下**不抛**，`exit=0`
  - `*> $null` / `2>$null` / `2>&1 | Out-Null` / `$o = & ... 2>&1`：Stop 下**抛** `<xelatex: security risk: running with elevated privileges>`
  同一脚本里 `A no-throw (exit=0)` + `B code=0` 也复现了"Stop 但没走重定向就不抛"的另一面，说明坑的触发条件是**重定向 + Stop**，不是 Stop 本身。
- 规定：
  1. **禁止**在 `$ErrorActionPreference='Stop'` 的脚本里用 `*>&1` / `2>&1` / `2>$null` 去接 xelatex、pdftotext、pdfinfo、latexmk 的输出。
  2. 统一用 `Invoke-Native` 包装：函数内临时把偏好切到 `Continue`，用 `2>&1 | ForEach-Object {"$_"}` 收集，成败只看 `$LASTEXITCODE`（见 `E:\数学建模\APMCM2026\build.ps1` 同名函数）。
  3. 不要把流里的 `security risk: running with elevated privileges` 当编译失败信号；真正的 TeX 错误是行首 `!` 的行。
- 验证：
  ```powershell
  function Invoke-Native { param([string]$Exe,[string[]]$Arguments)
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $out = & $Exe @Arguments 2>&1 | ForEach-Object { "$_" }; [pscustomobject]@{ Output=@($out); Code=$LASTEXITCODE } }
    finally { $ErrorActionPreference = $prev } }
  $ErrorActionPreference = 'Stop'
  try { & xelatex -interaction=nonstopmode -halt-on-error -output-directory=E:\数学建模\.tmp_scratch\pit\tex E:\数学建模\.tmp_scratch\pit\tex\t.tex 2>&1 | Out-Null; 'UNEXPECTED: 没抛' }
  catch { "OK 复现：Stop + 2>&1 抛错 -> $($_.Exception.Message)" }
  $r = Invoke-Native 'xelatex' @('-interaction=nonstopmode','-halt-on-error','-output-directory=E:\数学建模\.tmp_scratch\pit\tex','E:\数学建模\.tmp_scratch\pit\tex\t.tex')
  "wrapper code=$($r.Code) lines=$($r.Output.Count) first='$($r.Output[0])'"   # 期望 code=0
  $r2 = Invoke-Native 'xelatex' @('-interaction=nonstopmode','-halt-on-error','-output-directory=E:\数学建模\.tmp_scratch\pit\tex','E:\数学建模\.tmp_scratch\pit\tex\bad.tex')
  "bad.tex code=$($r2.Code) err=$(($r2.Output | Where-Object { $_ -match '^!' } | Select-Object -First 1))"  # 期望 code=1
  ```
- 实测时间：2026-11-11
- 实测输出：`THREW <xelatex: security risk: running with elevated privileges>`；wrapper `B code=0 lines=16 first line: xelatex: security risk: running with elevated privileges`；`C code=1 / C error line: ! Undefined control sequence.`
- 验证结果: **pass**

---

## P-E04 `main.log` 本身不是 UTF-16；UTF-16 来自 PowerShell 重定向产物

- 现象：查看 `E:\数学建模\APMCM2026\main.log` 首 4 字节为 `54 68 69 73`（ASCII "This"），**无 FF FE BOM**；`Get-Content` 与 `[System.IO.File]::ReadAllLines` 都得 **1393** 行。真正 UTF-16LE（`FF FE`）的 15 个日志全在别处：`E:\数学建模\APMCM2025_C\data\{figs,q1_run,q1_run2,q1_run_b,q2_run,tables,tex1,tex2,tex3,verify,_q1_new}.log`、`logs\{surrogate_train_run,surrogate_train_run2,train_with_sampler}.log`、`review\_probe_bind_1024.log`；其首字节如 `FF FE 7B 00`。
- 根因：UTF-16 不是 MiKTeX 写的——是 **PowerShell 5.1 的 `*>` / `>` 重定向**默认用 Unicode 编码落盘造成的；MiKTeX 自己写的 `<job>.log` 是普通 ASCII/ANSI。所以"main.log 是 UTF-16"这个命题本身不成立，但"PS 重定向产物是 UTF-16"真成立了（实测 `& xelatex ... *> ps_redir.log` → 首字节 `FF FE 78 00`、1990 字节、21 行）。BOM 在时 `Get-Content` / `-Encoding Unicode` / `ReadAllLines` 三法读数一致（150 行），不会数错。
- 规定：
  1. **禁止**再用 `*>` / `>` 落"给人看"的日志——会得到 UTF-16；要么用 `| Out-File -Encoding utf8`，要么用 `Invoke-Native` 收集后 `[IO.File]::WriteAllLines(..., UTF8Encoding($false))`。
  2. 读日志前先看 BOM：`FF FE` = UTF-16LE（`Get-Content` 能自动识别），`EF BB BF` = UTF-8 with BOM，其余按 UTF-8 显式声明读。
  3. 不要把"main.log 是 UTF-16"写进任何文档或脚本假设。
- 验证：
  ```powershell
  $f = 'E:\数学建模\APMCM2026\main.log'
  $b = [System.IO.File]::ReadAllBytes($f)
  "首4字节: $(($b[0..3] | ForEach-Object { $_.ToString('X2') }) -join ' ')  UTF16BOM=$($b[0] -eq 0xFF -and $b[1] -eq 0xFE)"  # 期望 54 68 69 73 / False
  "行数: $((Get-Content $f).Count)"   # 期望 1393
  # 对照：PS 重定向产物确实是 UTF-16
  & xelatex -interaction=nonstopmode -halt-on-error E:\数学建模\.tmp_scratch\pit\tex\t.tex *> E:\数学建模\.tmp_scratch\pit\ps_redir.log
  $b2 = [System.IO.File]::ReadAllBytes('E:\数学建模\.tmp_scratch\pit\ps_redir.log')
  "ps_redir 首2字节: $(($b2[0..1] | ForEach-Object { $_.ToString('X2') }) -join ' ')"  # 期望 FF FE
  ```
- 实测时间：2026-11-11
- 实测输出：`main.log 首4字节: 54 68 69 73 ; BOM? False`、`Get-Content 行数 = 1393`；`ps_redir 首字节 FF FE 78 00，size=1990，21 行`
- 验证结果: **fail**（原命题"main.log 是 UTF-16"不成立；坑的真实形态是"PS 重定向产物是 UTF-16"，已单列在根因与规定里）

---

## P-E05 `[System.IO.File]::ReadAllText('相对路径')` 按进程 cwd 解析，不认 PowerShell 当前位置

- 现象（逐字）：脚本里先 `Set-Location 'E:\数学建模\APMCM2025_C'`，再相对读：
  ```
  Mock: MethodInvocationException :: Exception calling "ReadAllText" with "1" argument(s):
  "Could not find a part of the path 'E:\数学建模\.tmp_scratch\pit\code\common.py'."
  ```
  此时 `PS location = E:\数学建模\APMCM2025_C`，而 `process cwd = E:\数学建模\.tmp_scratch\pit`。
- 根因：`Set-Location` 只移动 PowerShell 的**位置**（provider path）；.NET 的 `System.IO.*` 与**原生 exe**（xelatex、pdftotext、pdfinfo、python）都用进程级 CWD，而 `.NET` 进程的 CWD 在 PowerShell 里**不会**跟着 `Set-Location` 变。同一坑在原生 exe 上同样成立：cwd 在 `pit` 时 `pdfinfo many.pdf` → `I/O Error: Couldn't open file 'many.pdf': No such file or directory.`。
- 规定：
  1. 凡是 `.NET` 静态 IO（`ReadAllText`/`ReadAllLines`/`WriteAllText`/`IO.File::Exists`）**必须给绝对路径**；也可先 `[Environment]::CurrentDirectory = (Get-Location).Path` 同步，但更稳妥是绝对路径。
  2. 调原生 exe 传文件参数时同样给绝对路径（或用 `Push-Location` 后 `Start-Process -WorkingDirectory`）。
  3. 项目内统一从 `$PSScriptRoot` 派生绝对路径，不要依赖"当前在哪个目录"。
- 验证：
  ```powershell
  # 在 E:\数学建模\.tmp_scratch\pit 下执行
  $p = Start-Job { Set-Location 'E:\数学建模\APMCM2025_C'; [System.IO.File]::ReadAllText('code\common.py') }
  ```
  更直接的可判定写法：
  ```powershell
  cd E:\数学建模\.tmp_scratch\pit
  powershell -NoProfile -Command "
    Set-Location 'E:\数学建模\APMCM2025_C'
    try { [IO.File]::ReadAllText('code\common.py') | Out-Null; 'UNEXPECTED: 相对路径成功' }
    catch { 'OK 复现：' + `$_.Exception.Message }
    (Get-Content 'code\common.py' -Raw).Length"   # 期望抛错；Get-Content 侧 10901
  ```
- 实测时间：2026-11-11
- 实测输出：`relative ReadAllText THREW: MethodInvocationException :: ... "Could not find a part of the path 'E:\数学建模\.tmp_scratch\pit\code\common.py'."`；`Get-Content relative len = 10901`；`ReadAllText absolute len = 10901`
- 验证结果: **pass**

---

## P-E06 `Get-Content` 默认按 GBK 解码 UTF-8 中文，行数与码点双错

- 现象：对 `E:\数学建模\APMCM2025_C\README.md`（7906 字节）：
  - 真值（文件里 `0x0A` 个数）= **87** 行
  - `Get-Content README.md`（不写 `-Encoding`）= **84** 行
  - `Get-Content README.md -Encoding UTF8` = **87** 行
  - 默认解码首行（乱码）：`# APMCM 2025 C 棰樺畬鏁村缓缓妯?鈥?U.S. 鈥淩eciprocal Tariffs鈥?`
  - UTF8 解码首行（正确）：`# APMCM 2025 C 题完整建模 — “Reciprocal Tariffs”`
  - 码点对照：默认 26864,27194,30060,… vs UTF8 39064,23436,25972,…
- 根因：PS 5.1 的 `Get-Content` 无 `-Encoding` 时用 `Default`，即系统 ANSI 代码页 **936**。UTF-8 的三字节汉字被当成 1.5 个 GBK 双字节字符，逐对吞字节，偶尔把一个 `0x0A` 一起吃进去 → 行数变少、中文变乱码。结构证明：字节 `41 C4 E3 BA C3 0A`（'A'+GBK"你好"）用 `-Encoding Default` 解出 `A你好`（码点 65,20320,22909，与 `[Text.Encoding]::GetEncoding(936).GetString` 逐位相等），用 `-Encoding UTF8` 解出 65,65533,65533,65533。
- 规定：
  1. 读任何文本**必须显式 `-Encoding UTF8`**（或 `[System.IO.File]::ReadAllLines($abs)`，它默认 UTF-8）。
  2. 报"行数/节数/条数"之前必须先确认解码方式；用 `0x0A` 计数当真值对照。
  3. 不要用"默认读能拿到内容"当成"内容正确"。
- 验证（`E:\数学建模\.tmp_scratch\pit\check_e13.ps1`）：
  ```powershell
  $f = 'E:\数学建模\APMCM2025_C\README.md'
  $nl  = @([System.IO.File]::ReadAllBytes($f) | Where-Object { $_ -eq 0x0A }).Count
  $def = @(Get-Content $f).Count
  $u8  = @(Get-Content $f -Encoding UTF8).Count
  if ($def -eq $nl) { "PASS default=$def" } else { "FAIL default=$def 真值=$nl" }
  "UTF8 行数 = $u8"
  ```
- 实测时间：2026-11-11
- 实测输出：`FAIL default=84 真值=87 （默认按 GBK 解码 UTF-8 中文，会把多字节序列拆错，行数少 3）` / `UTF8 -Encoding 行数 = 87`
- 验证结果: **pass**

---

## P-E07 裸 `python` 是 3.14.6，无任何第三方库

- 现象：`python -c "import numpy"` →
  ```
  Traceback (most recent call last):
    File "<string>", line 1, in <module>
  ModuleNotFoundError: No module named 'numpy'
  ```
  `pandas` / `matplotlib` / `torch` 同；`python -c "import sys;print(sys.version.split()[0])"` → `3.14.6`。
- 根因：`E:\Mini\python.exe`（conda base）是 3.14.6 的裸解释器，本项目全部依赖装在 `E:\Mini\envs\mathmodel`（Python **3.11.18**，numpy 2.4.6 / scipy 1.17.1 / pandas 3.1.1 / matplotlib 3.11.2 / torch 2.14.1+cu126）。
- 规定：**禁止**在任何命令、脚本、文档里写裸 `python` / `py` 去跑本项目的数值代码。统一 `conda run -n mathmodel python ...`，或直接 `E:\Mini\envs\mathmodel\python.exe`（后者须先把 `E:\Mini\envs\mathmodel;...\Library\bin;...\Scripts` 放到 PATH 最前，否则 numpy 会 `0xC0000409`，见 APMCM2026/env.ps1）。
- 验证：
  ```powershell
  python -c "import sys;print(sys.version.split()[0])"                                  # 期望 3.14.6
  python -c "import numpy" 2>&1 | Select-String 'ModuleNotFoundError'                   # 期望命中
  conda run -n mathmodel python -c "import sys,numpy,torch;print(sys.version.split()[0],numpy.__version__,torch.__version__)"
  # 期望 3.11.18 2.4.6 2.14.1+cu126
  ```
- 实测时间：2026-11-11
- 实测输出：`3.14.6`；`ModuleNotFoundError: No module named 'numpy'`；`3.11.18 2.4.6 2.14.1+cu126`
- 验证结果: **pass**

---

## P-E08 `Start-Process` 起子系统时，大小写重复的代理环境变量让它直接抛异常

- 现象（逐字）：
  ```
  Start-Process : 已添加项。字典中的关键字:“NO_PROXY”所添加的关键字:“no_proxy”
  + CategoryInfo : NotSpecified: (:) [Start-Process], ArgumentException
  + FullyQualifiedErrorId : System.ArgumentException,Microsoft.PowerShell.Commands.StartProcessCommand
  ```
  英文界面下同义：`Start-Process : Item has already been added. Key in dictionary: 'NO_PROXY'  Key being added: 'no_proxy'`。
  清掉 `no_proxy` 后立刻换成下一对：`已添加项。字典中的关键字:“https_proxy”所添加的关键字:“HTTPS_PROXY”`。
- 根因：本机进程环境里存在**大小写仅不同**的重复键（`NO_PROXY`/`no_proxy`、`HTTPS_PROXY`/`https_proxy`、`HTTP_PROXY`/`http_proxy`，值相同）。`Start-Process` 在构造成员环境块时用**大小写不敏感**的字典合并，于"同名"处抛 `ArgumentException`。这跟 `.NET`/`cmd`/原生 exe 无关——它们接受重复键，所以只有 `Start-Process`（可能还有 `CreateProcess` 包装类 cmdlet）会炸。
- 规定：
  1. 需要起子进程时，优先 `& $exe @args`（同进程、直接看到退出码），其次 `cmd /c`；**只有真正要脱离当前会话时才用 `Start-Process`**。
  2. 一旦必须 `Start-Process`，先清掉小写副本：
     ```powershell
     foreach ($k in @('no_proxy','https_proxy','http_proxy')) { Remove-Item "Env:$k" -ErrorAction SilentlyContinue }
     ```
     （注意：每次新起的 `pwsh` 都从父进程环境重新继承，这步**每进程都要重做**。）
  3. `-Args` 只是 `-ArgumentList` 的别名，与自动变量 `$Args` 不是一回事；传参一律写 `-ArgumentList`。脚本里追加 `-Args hello` 会被当成位置参数吞掉，`param()` 收不到。
- 验证：
  ```powershell
  $dups = [System.Environment]::GetEnvironmentVariables('Process').Keys |
    ForEach-Object { [pscustomobject]@{ Low = $_.ToLowerInvariant(); Orig = $_ } } |
    Group-Object Low | Where-Object { $_.Count -gt 1 }
  "重复键: " + (($dups | ForEach-Object { ($_.Group.Orig) -join '/' }) -join '; ')   # 期望 NO_PROXY/no_proxy; ...
  try { Start-Process powershell -ArgumentList '-NoProfile','-Command','exit 0' -Wait -PassThru -NoNewWindow -ErrorAction Stop | Out-Null; 'UNEXPECTED: 成功' }
  catch { "OK 复现: $($_.Exception.Message)" }
  foreach ($k in @('no_proxy','https_proxy','http_proxy')) { Remove-Item "Env:$k" -ErrorAction SilentlyContinue }
  (Start-Process powershell -ArgumentList '-NoProfile','-Command','exit 0' -Wait -PassThru -NoNewWindow).ExitCode   # 期望 0
  ```
- 实测时间：2026-11-11
- 实测输出：`duplicate-insensitive keys: NO_PROXY/no_proxy; https_proxy/HTTPS_PROXY; http_proxy/HTTP_PROXY`；`已添加项。字典中的关键字:“NO_PROXY”所添加的关键字:“no_proxy”`；清掉三对后 `PARAM m = [hello]`、`exit=0`
- 验证结果: **pass**

---

## P-E09 本机没有 `dl` conda env；`dl` 只是 env.ps1 的 profile 名

- 现象：`conda env list` 输出只有 `base / deep_learning_3.8 / label-studio / labelimg / labelme / mathmodel / ml310 / py310`，**没有 dl**；而 `E:\数学建模\APMCM2025_C\code\q1_sobol.py`、`q1_surrogate_train.py` 的 docstring 写着 "Run under the `dl` profile"，`APMCM2025_C\README.md` 训练段写"须用 `dl` 档，`env.ps1 -Profile dl`"。若照字面执行 `conda activate dl`，会得到 `Could not find conda environment: dl`。
- 根因：`dl` 是 `E:\数学建模\APMCM2026\env.ps1` 里的 **profile 参数值**（`-Profile dl` 只把 `MKL_NUM_THREADS=1`、`OMP_NUM_THREADS=1` 等变量设上），不是独立环境。真正执行数值代码的环境始终是 `mathmodel`。
- 规定：
  1. 文档与脚本里写 **`conda run -n mathmodel`**；要"dl 档"时写 `conda run -n mathmodel` 并附 OpenMP 相关环境变量（参考 `env.ps1 -Profile dl` 的赋值），**禁止**写 `conda activate dl` / `-n dl`。
  2. 引 `dl` 之前先 `conda env list` 确认；引用历史记录时把"dl 档/ dl env"当作 profile 名理解。
- 验证：
  ```powershell
  conda env list 2>&1 | Select-String '^\s*dl\s'      # 期望无输出
  conda run -n dl python -c "print(1)" 2>&1 | Select-String 'Could not find conda environment'  # 期望命中
  Select-String -Path E:\数学建模\APMCM2026\env.ps1 -Pattern 'Profile (dl|classic)'   # 期望能看到 dl 是 profile
  ```
- 实测时间：2026-11-11
- 实测输出：`dl 是否存在：False`；`env.ps1:1 # Activate the mathmodel conda environment and select a numerical profile.`、`5: . .\env.ps1 -Profile dl  -> profile "dl": PyTorch / LSTM / CNN on the GPU`
- 验证结果: **pass**（"不存在 dl env" 成立；历史记录里的 `dl` 全部应读作 profile）

---

## P-E10 numpy matmul 后再 `import torch` 触发 `OMP: Error #15`

- 现象（逐字）：
  ```
  OMP: Error #15: Initializing libomp.dll, but found libiomp5md.dll already initialized.
  OMP: Hint This means that multiple copies of the OpenMP runtime have been linked into the program. That is dangerous, since it can degrade performance or cause incorrect results. The best thing to do is to ensure that only a single OpenMP runtime is linked into the process, e.g. by avoiding static linking of the OpenMP runtime in any library. As an environment variable, you can also set KMP_DUPLICATE_LIB_OK=TRUE to allow the program to continue.
  ```
  exit=3。另：`Library\bin` 不在 PATH 时 `import torch` 直接
  `OSError: [WinError 127] 找不到指定的程序。 Error loading "E:\Mini\envs\mathmodel\Lib\site-packages\torch\lib\shm.dll" or one of its dependencies.`
- 根因：`mathmodel` 里 numpy 走 conda-forge MKL BLAS，一次 matmul 就把 Intel 的 `libiomp5md.dll` 拉进进程；随后 `import torch` 要加载它自带的 LLVM `libomp.dll`，两个 OpenMP 运行时同进程 ⇒ #15。**关键触发条件是"numpy 先做了一次实际 BLAS 运算"**：实测 `import numpy; import torch`（不 matmul）exit=0；`torch` 先 matmul 再 numpy 也 exit=0。`OMP_NUM_THREADS=1` / `MKL_NUM_THREADS=1` 单独或同时都**不能**消除冲突（它们只控制线程数，不解决运行时重复链接）。
- 规定：
  1. 训练/推理脚本**先 `import torch`，再 `import numpy`**，且把 numpy 的 BLAS 调用放在 torch 初始化之后；或使用独立进程只跑 torch。
  2. 需要两者混跑时设 `KMP_DUPLICATE_LIB_OK=TRUE` 并接受"可能静默错算"的风险——**数值对账（verify_numbers）必须在这个变量下重跑一遍**，不能拿 classic 档的结果当结论。
  3. 必检查 `Library\bin` 在 PATH 最前。
- 验证（`check_kmp.py` + `check_kmp2.ps1`）：
  ```powershell
  $py = @'
  import numpy as np
  a = np.ones((300,300)) @ np.ones((300,300))   # 先触发 MKL
  import torch
  print("torch ok", torch.__version__)
  '@
  [IO.File]::WriteAllText("$env:TEMP\kmp_probe.py", $py, (New-Object System.Text.UTF8Encoding($false)))
  $env:PYTHONIOENCODING='utf-8'
  conda run -n mathmodel python "$env:TEMP\kmp_probe.py" 2>&1 | Select-String 'OMP: Error #15'
  "exit=$LASTEXITCODE"   # 期望命中且 exit=3
  ```
- 实测时间：2026-11-11
- 实测输出：`OMP: Error #15: Initializing libomp.dll, but found libiomp5md.dll already initialized.`、`exit = 3`、`RESULT: clash (与记录一致)`
- 验证结果: **pass**

---

## P-E11 `$Matches[1]` 无匹配时抛 `无法对 Null 数组进行索引。`，且会静默保留旧值

- 现象（逐字）：`无法对 Null 数组进行索引。`，`FullyQualifiedErrorId = NullArray`（英文界面：`Cannot index into a null array.`）。本机中文系统下原样为前者。
- 根因：`-match` 不匹配时**不清空** `$Matches`，而是保留上一次的值；只有在"当前进程/作用域里从没匹配过"时才是 `$null`，这时 `$Matches[1]` 就抛 NullArray。所以它有两种表现，**后者更危险**：先匹配到 `12`，再拿同一个 `$Matches[1]` 去读失败的那次结果，静默拿到旧值 `12`（实测 `B else-branch -> $Matches[1] = 12  <-- 陈旧值`）。`[regex]::Match().Groups[1]` 则安全：不匹配时 `Success=False`、`Groups[1].Value` 为空串、不抛。
- 规定：
  1. **禁止**用 `$Matches[1]` 取分组结果。
  2. 统一 `$m = [regex]::Match($text, '^Pages:\s+(\d+)', 'Multiline')`，先判 `$m.Success`，再取 `$m.Groups[1].Value`。
  3. 正则匹配的返回值要立刻落到局部变量，不要跨语句复用 `$Matches`。
- 验证（`pe11c.ps1`）：
  ```powershell
  $ErrorActionPreference = 'Continue'
  try { $s = 'no page info here'
        if ($s -match '^Pages:\s+(\d+)') { } else { $Matches[1] } }
  catch { "OK 复现: $($_.Exception.Message) | $($_.FullyQualifiedErrorId)" }   # 期望 无法对 Null 数组进行索引。/NullArray
  $m = [regex]::Match('no page info here', '^Pages:\s+(\d+)', 'Multiline')
  "safe: success=$($m.Success) value=[$($m.Groups[1].Value)]"                   # 期望 False / []
  ```
- 实测时间：2026-11-11
- 实测输出：`C THREW: Cannot index into a null array. | FQID=NullArray`（中文界面为 `无法对 Null 数组进行索引。`）；`B else-branch -> $Matches[1] = 12 <-- 陈旧值`；`D safe route: success=False value=[]`
- 验证结果: **pass**

---

## P-E12 用 PowerShell 字符串操作改 `.py` ⇒ BOM + CRLF + 中文乱码

- 现象：`$s = Get-Content x.py -Raw; $s = $s -replace '中文注释','中文注释B'; $s | Set-Content x.py -Encoding UTF8` 之后：
  - 首字节 `EF BB BF`（UTF-8 **with BOM**）、`CRLF` 计数 1
  - `ast.parse` 报 `SyntaxError: invalid non-printable character U+FEFF`
  - 中文行变成 `NAME = "娑擃厽鏋冨鏋冨▔銊╁櫞"`（码点 0x6d93,0xe15f,…），原文 `中文注释` 的 UTF-8 字节**已不存在**
  - 对照：用 python 写的同一文件首字节 `23 20 2D 2A`（`# -*`），`CRLF` 0，`ast.parse` OK，码点 0x4e2d,0x6587,0x6ce8,0x91ca
- 根因：两件事叠加。(1) `Get-Content -Raw` 无 `-Encoding` 时按 GBK 解码（见 P-E06），中文在**读入**那一步就已经烂了；(2) `Set-Content -Encoding UTF8` 在 5.1 下写 **BOM**，且 `Set-Content` 会把多行字符串按平台换行重写为 CRLF。任一都会让 `.py` 无法被 python 3 直接解析（BOM）+ 内容错乱。
- 规定：
  1. **禁止**用 `Get-Content -replace … | Set-Content` 这类 PowerShell 字符串管线改 `.py`（或任何 UTF-8 源码/配置）。
  2. 改文件统一走 python：
     ```powershell
     conda run -n mathmodel python -c "from pathlib import Path; p=Path(r'X.py'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('old','new'), encoding='utf-8', newline='')"
     ```
     或写一个 `fix.py` heredoc 再跑（`newline=''` 保留原换行，`encoding='utf-8'` 无 BOM）。
  3. 改完必须跑一次"字节体检"（见下），绿了才算改完。
- 验证（`check_e12.py`）：
  ```python
  from pathlib import Path
  import ast
  p = Path('target.py'); b = p.read_bytes(); bad = []
  if b[:3] == b'\xef\xbb\xbf': bad.append('BOM')
  if b'\r\n' in b: bad.append('CRLF')
  try: ast.parse(b.decode('utf-8'))
  except SyntaxError as e: bad.append('SyntaxError:' + e.msg)
  print(('FAIL ' if bad else 'PASS ') + (','.join(bad) if bad else 'clean utf-8 LF'))
  ```
- 实测时间：2026-11-11
- 实测输出：PS 改写件 `FAIL BOM,CRLF,SyntaxError:invalid non-printable character U+FEFF`；python 改写件 `PASS clean utf-8 LF`
- 验证结果: **pass**

---

## P-E13 matplotlib 标题里写 `\%` 会渲出字面反斜杠

- 现象：`ax.set_title(r"Labor share 62\% of GDP")` + `ax.text(..., r"A 5\% B")` 出的 PNG 上显示 `Labor share 62\% of GDP` 与 `A 5\% B`（反斜杠肉眼可见）；同一图改成 `62%` / `5%` 后正常显示 `62%`、`5%`。两版截图存于 `E:\数学建模\.tmp_scratch\pit\mpl_backslash.png` 与 `mpl_plain.png`。
- 根因：matplotlib 的文本默认不是 LaTeX（`text.usetex=False` 且未把整串包进 `$...$`），`%` 在 matplotlib 里**没有特殊含义**，`\` 也不是转义前缀，于是 `\%` 原样输出两个字符。`\%` 只在 **LaTeX 正文**里才需要（如 `E:\数学建模\.agents\skills\mathmodeling\scripts\mmkit\provenance.py:269` 的 `f"{100 * x:.{nd}f}\\%"` 是生成 `.tex`，正确）。
- 规定：
  1. 图内文字（title / xlabel / ylabel / text / legend / annot）**只写 `%`**，不写 `\%`。
  2. 同一字符串若既进图又进 `.tex`，**必须拆成两份**，不得共用。
  3. 真要 LaTeX 渲染时，用 `plt.rcParams['text.usetex']=True` 并把整串放进 `$…$`，那才轮到 `\%`。
- 验证：
  ```python
  import matplotlib; matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  fig, ax = plt.subplots(figsize=(3,2))
  ax.set_title(r"Labor share 62\% of GDP")     # 坑
  ax.text(0.5, 0.5, r"A 5\% B", ha='center')
  fig.savefig('pct_bad.png', dpi=80)
  fig2, ax2 = plt.subplots(figsize=(3,2))
  ax2.set_title("Labor share 62% of GDP")      # 正确
  ax2.text(0.5, 0.5, "A 5% B", ha='center')
  fig2.savefig('pct_ok.png', dpi=80)
  print('ok')
  ```
  然后人工/OCR 看图：`pct_bad.png` 出现反斜杠即坑存在。
- 实测时间：2026-11-11
- 实测输出：截图 `mpl_backslash.png` 标题文字为 `Labor share 62\% of GDP`、正文 `A 5\% B`；`mpl_plain.png` 为 `62%` / `5%`
- 验证结果: **pass**

---

## P-E14 f-string 里写 LaTeX 千分位 `{v{,}000}` 是语法错误

- 现象（逐字）：
  ```
    File "fs_bad2.py", line 2
      (v{,}000)
        ^
  SyntaxError: f-string: invalid syntax
  ```
- 根因：`{}` 在 f-string 里是**替换字段**边界，`{,}000` 被当成格式说明符解析，`,` 不是合法格式字符 ⇒ 语法错误。治理 LaTeX 千分位（`64{,}000`）需要原样输出花括号，但原样输出又和 f-string 语法冲突。非 f-string 的普通字符串 `"capacity 64{,}000 units"` 完全合法（实测输出 `literal tex: capacity 64{,}000 units`）。
- 规定：
  1. 要生成 LaTeX 的 `{,}` 千分位时，**不要用 f-string**：先拼普通字符串，或写 `{{,}}`（双花括号）显式转义。
  2. 要给数字加逗号千分位（Python 侧），用 `f"{v:,}"`（实测 `64000` → `64,000`）。
  3. 生成 `.tex` 的代码要单独跑一遍并 `xelatex` 验证（`{,}` 与 `,` 在 LaTeX 里排版效果不同）。
- 验证：
  ```powershell
  $bad = "v = 64`ns = f'capacity {v{,}000} units'`nprint(s)`n"
  [IO.File]::WriteAllText("$env:TEMP\fs_bad.py", $bad, (New-Object System.Text.UTF8Encoding($false)))
  $env:PYTHONIOENCODING='utf-8'
  conda run -n mathmodel python "$env:TEMP\fs_bad.py" 2>&1 | Select-String 'SyntaxError'   # 期望 f-string: invalid syntax
  conda run -n mathmodel python -c "print(f'{64000:,}')"                                     # 期望 64,000
  ```
- 实测时间：2026-11-11
- 实测输出：`SyntaxError: f-string: invalid syntax`；正确写法 `capacity 64000 units` / `literal tex: capacity 64{,}000 units`
- 验证结果: **pass**

---

## P-E15 `pdftoppm` 输出按**总页数**零填充（`p-01.png`）

- 现象：12 页 PDF 跑 `pdftoppm -png -r 30 many.pdf p` 得到 `p-01.png … p-12.png`（2 位零填充）；单页 PDF 跑 `pdftoppm -png -r 30 t.pdf single` 得到 `single-1.png`（**不填充**）；用 `-f 5 -l 5` 只出第 5 页仍是 `one-05.png`（按总页数 12 补到 2 位，不是按实际输出页数 1 补）。
- 根因：poppler 的 `pdftoppm` 生成文件名时用"总页数字数"决定序号宽度（10≤N<100 → 2 位，100≤N<1000 → 3 位），与本次输出几页无关。所以写死 `p-1.png` / `p-10.png` 的脚本在 ≥10 页时全部找不到文件。
- 规定：
  1. 取 `pdftoppm` 输出**禁止硬编码 `p-1.png`**；用通配 + 排序，或先用 `pdfinfo` 求页数再格式化补零：
     ```powershell
     $pad = "$([math]::Floor([math]::Log10([math]::Max(1,$pages-1)))+1)"  # 1..1000
     $name = 'p-' + $i.ToString("0{$pad}")
     ```
  2. 批量时优先 `Get-ChildItem p-*.png | Sort-Object Name`，别按数字拼路径。
- 验证：
  ```powershell
  cd E:\数学建模\.tmp_scratch\pit\tex
  pdftoppm -png -r 30 many.pdf p 2>$null
  (Get-ChildItem p-*.png | Select-Object -First 2 -ExpandProperty Name) -join ','   # 期望 p-01.png,p-02.png
  pdftoppm -png -r 30 t.pdf single 2>$null
  (Get-ChildItem single*.png -ExpandProperty Name) -join ','                        # 期望 single-1.png
  pdftoppm -png -r 30 -f 5 -l 5 many.pdf one 2>$null
  (Get-ChildItem one*.png -ExpandProperty Name) -join ','                           # 期望 one-05.png
  ```
- 实测时间：2026-11-11
- 实测输出：`p-01.png, p-02.png, p-03.png`；`single-1.png`；`one-05.png`
- 验证结果: **pass**

---

## P-E16 WMI `AdapterRAM` 是 32 位字段，8188 MiB 被读成 4095 MiB

- 现象：`(Get-CimInstance Win32_VideoController | ? { $_.Name -match 'NVIDIA' }).AdapterRAM` → **4293918720**（= 2^32 − 1048576，折 4095 MiB）；而 `nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits` → **8188** MiB。Intel 那项 `AdapterRAM=134217728`（128 MiB，共享显存同样无意义）。
- 根因：`Win32_VideoController.AdapterRAM` 在 WMI 中声明为 **uint32**，>4 GiB 的显存值溢出回绕，且显存本身是动态共享的，这个字段在现代显卡上从不准确。驱动版本号也不再是真实版本（WMI 给 `32.0.16.1062`，nvidia-smi 给 `610.62`）。
- 规定：
  1. 显存/型号/驱动**只认 `nvidia-smi --query-gpu=name,memory.total,driver_version`**。
  2. 需要注册表时读 `HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\<序号>\HardwareInformation.qwMemorySize`（本机 `8585740288` = 8188 MiB 正确）；序号不固定，要遍历并读 `DriverDesc` 匹配。
  3. **禁止**在任何报告里引用 WMI 的 `AdapterRAM` 数值当显存。
- 验证：
  ```powershell
  $wmi = (Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match 'NVIDIA' }).AdapterRAM
  $smi = (nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits) -join ''
  "WMI=$wmi ($([math]::Round($wmi/1MB,0)) MiB)  smi=$smi MiB  截断=$($wmi -lt [math]::Pow(2,32))"
  # 期望 WMI=4293918720 (4095 MiB) smi=8188 截断=True
  ```
- 实测时间：2026-11-11
- 实测输出：`WMI AdapterRAM = 4293918720 (4095 MiB)`、`nvidia-smi = 8188 MiB`、`WMI 是否截断到 2^32 以下：True`
- 验证结果: **pass**

---

## P-E17 `xelatex -log-directory=<dir>` 目标目录存在也失败

- 现象：`E:\数学建模\.tmp_scratch\pit\tex\lg` 目录确实存在，执行
  `cd tex && xelatex -interaction=nonstopmode -log-directory=lg -halt-on-error t.tex > lg\out.txt 2>&1` → EXIT=1，`lg\out.txt` 只有：
  ```
  Sorry, but xelatex did not succeed.

  The log file hopefully contains the information to get MiKTeX going again:

    C:\Users\29900\AppData\Local\MiKTeX\miktex\log\xelatex.log
  ```
  `lg` 目录里没有生成 `t.log`；同目录**不带** `-log-directory` 编译则 exit=0、`t.log` 正常写出 2476 字节（说明不是权限问题）。
- 根因：MiKTeX 25.12 的 `-log-directory` 实现在"日志写到另一个目录"时失败，且失败原因被写进 MiKTeX 自己的用户级日志（`%LOCALAPPDATA%\MiKTeX\miktex\log\xelatex.log`），不写 `t.log`。这是工具自身行为，不是参数用法错误（目录已存在、路径合法）。
- 规定：
  1. **禁止**用 `-log-directory` 清理/集中日志。
  2. 日志清理统一：编译前 `Remove-Item <job>.log -ErrorAction SilentlyContinue`，日志留在工作目录。
  3. 若必须隔离日志，编译后**复制**走，不在编译期指定目录。
- 验证：
  ```powershell
  cd E:\数学建模\.tmp_scratch\pit\tex
  New-Item -ItemType Directory -Force .\lg | Out-Null
  xelatex -interaction=nonstopmode -log-directory=lg -halt-on-error t.tex > lg\out.txt 2>&1
  "exit=$LASTEXITCODE  files=$(Get-ChildItem .\lg | Select-Object -ExpandProperty Name -join ',')"
  (Get-Content .\lg\out.txt -Raw) -match 'did not succeed'      # 期望 exit=1、只有 out.txt、True
  ```
- 实测时间：2026-11-11
- 实测输出：`exit=1`、`lg 目录内容: out.txt`、`out.txt 是否含 'did not succeed': True`；对照 `exit=0 / t.log 大小 = 2476`
- 验证结果: **pass**

---

## P-E18 页数口径：`\f` 计数已等于 `pdfinfo` 页数，再 +1 会多一页

- 现象：`E:\数学建模\APMCM2025_C\main.pdf`：
  - `pdfinfo` → `Pages:           108`
  - `pdftotext -enc UTF-8 main.pdf -` 输出里 `\f`（U+000C）个数 = **108**
  - 文本末尾字符就是 `\f`（`last char is FF: True`）
  - 若按"`\f` 之后再 +1"算页 = **109**（错一页）
- 根因：poppler 的 `pdftotext` 在**每页末尾**写一个 form feed（含最后一页），所以 `\f` 计数直接等于页数；只有把 `\f` 当"新页开头"去计数、再对第一页补 1 的写法才等价，但那种写法一旦漏掉末尾 `\f` 就会少一页。`E:\数学建模\APMCM2025_C\code\check_pages.py` 的 docstring 已把这个口径写清楚了（页索引 = 该行之前的 `\f` 数 + 1）。
- 规定：
  1. 页数**优先**用 `pdfinfo` + `[regex]::Match($out,'^Pages:\s+(\d+)','Multiline').Groups[1].Value`（见 P-E11 的安全取法）。
  2. 只有需要"某行在第几页"时才用 `\f` 计数，且规则固定为"该行之前出现的 `\f` 个数 + 1"；**禁止**在这之后再给总页数 +1。
  3. 交叉核对：`\f` 总数应等于 `pdfinfo` 的 `Pages`；不等就说明文本提取失败（如加密、扫描件）。
- 验证（`pe18.ps1`）：
  ```powershell
  cd E:\数学建模\APMCM2025_C
  $pages = [regex]::Match((pdfinfo main.pdf 2>$null) -join "`n", '^Pages:\s+(\d+)', 'Multiline').Groups[1].Value
  $txt   = (pdftotext -enc UTF-8 main.pdf - 2>$null) -join ''
  $ff    = ([regex]::Matches($txt, "`f")).Count
  "pdfinfo=$pages  ff=$ff  ff+1=$($ff+1)  tail-is-FF=$($txt[-1] -eq [char]12)"
  ```
- 实测时间：2026-11-11
- 实测输出：`pdfinfo Pages = 108`；`pdftotext form-feed count = 108`；`form-feed count + 1 = 109`；`last char is FF: True`
- 验证结果: **pass**

---

## P-E19 编译日志重定向到同名 `<job>.log` 会让 xelatex 自己写不出日志

- 现象（逐字）：
  ```
  ! I can't write on file `many.log'.
  (Press Enter to retry, or Control-C to exit; default file extension is `.log')
  Please type another transcript file name
  ! Emergency stop
  No pages of output.
  ```
  EXIT=1。命令是 `cd tex && xelatex ... many.tex > many.log 2>&1`。把重定向目标换成 `many.out` 后：EXIT=0，`many.out` 内含 `Output written on many.pdf (12 pages).`
- 根因：外层 shell 的重定向**先创建并占住** `many.log`（句柄被 cmd/重定向持有），xelatex 随后要**写**同一个 `<job>.log` 打不开，TeX 就进 `Emergency stop`。
- 规定：**禁止**把编译输出重定向到与被编译文档同 basename 的 `<job>.log`；日志名用 `<job>.out` / `<job>.build.txt`，或干脆不重定向（用 `Invoke-Native` 收集到内存）。
- 验证：
  ```powershell
  cd E:\数学建模\.tmp_scratch\pit\tex
  Remove-Item many.log -ErrorAction SilentlyContinue
  cmd /c "xelatex -interaction=nonstopmode -halt-on-error many.tex > many.log 2>&1"; "clash exit=$LASTEXITCODE"
  (Get-Content many.log -Raw -Encoding UTF8) -match "I can't write on file"   # 期望 True
  cmd /c "xelatex -interaction=nonstopmode -halt-on-error many.tex > many.out 2>&1"; "ok exit=$LASTEXITCODE"
  (Get-Content many.out -Raw -Encoding UTF8) -match 'Output written on many.pdf'  # 期望 True
  ```
- 实测时间：2026-11-11
- 实测输出：`exit=1` / `has I can't write: True` / `has Emergency stop: True` / `has No pages of output: True`；对照 `exit=0` / `has Output written: True`
- 验证结果: **pass**（机制已确证）
- 需人工裁决：该现象**是否需要立规**取决于构建脚本写法。`E:\数学建模\APMCM2026\build.ps1` 用的是 `Invoke-Native` 内存捕获，不落 `.log` 重定向，因此当前仓库**不会**踩到；但 `APMCM2025_C\logs\*.txt` 那批历史日志说明过去确实用过重定向。建议立规（本报告已按立规写），若裁决为"不立规"，本条应改判为"记录存档"。

---

## P-E20 `conda run` 在 GBK 控制台下转发 U+FFFD 时自己崩

- 现象（逐字）：
  ```
  UnicodeEncodeError: 'gbk' codec can't encode character '\ufffd' in position 4: illegal multibyte sequence
  ```
  EXIT=1，且**Python 脚本本身成功执行了**（它只是 print 了一个含 U+FFFD 的串）。
- 根因：`conda run` 把子进程 stdout 转发给父控制台时用系统默认编码（本机 GBK/936），遇到 U+FFFD 就崩在 `conda` 自己的 `print(response.stdout, file=sys.stdout)`（`E:\Mini\Lib\site-packages\conda\cli\main_run.py:141`）。这条与 P-E06 同源：都是"GBK 当 UTF-8 用"。
- 规定：
  1. 跑 `conda run` **必须**先 `PYTHONIOENCODING=utf-8`（本报告所有 python 调用都这么写）。
  2. 输出里有 Windows 错误信息、乱码、U+FFFD 时不要直接管道给 conda；重定向到文件后按 UTF-8 读。
- 验证：
  ```powershell
  cd $env:TEMP
  Set-Content emit.py "print('ok-' + chr(0xFFFD) + '-end')" -Encoding UTF8
  conda run -n mathmodel python emit.py > f.txt 2>&1; "exit=$LASTEXITCODE"        # 期望 1 + UnicodeEncodeError
  cmd /c "set PYTHONIOENCODING=utf-8& conda run -n mathmodel python emit.py > g.txt 2>&1"; "exit=$LASTEXITCODE"  # 期望 0
  ```
- 实测时间：2026-11-11
- 实测输出：`exit=1`、`UnicodeEncodeError present: True`、`UnicodeEncodeError: 'gbk' codec can't encode character '\ufffd' in position 4: illegal multibyte sequence`；加 `PYTHONIOENCODING=utf-8` 后 `exit=0`、`UnicodeEncodeError present: False`
- 验证结果: **pass**

---

## P-E21 PowerShell 5.1 读**不带 BOM** 的 UTF-8 `.ps1`：中文路径/中文串全烂

- 现象（逐字）：
  ```
  powershell.exe : Get-Content : Cannot find path 'E:\鏁板﹀缓妯\.tmp_scratch\pit\py_way2.py' because it does not exist.
  ```
  同一个 `.ps1`，仅把文件从"UTF-8 无 BOM"改存为"UTF-8 with BOM"，同一路径立刻能读到；含中文的 `Write-Output '中文OK'` 无 BOM 时输出 `涓枃OK`，带 BOM 时输出 `中文OK`。
- 根因：5.1 对**没有 BOM 的 `.ps1`** 按系统 ANSI（936）解码脚本正文，写死的 `E:\数学建模\...` 被解成 `E:\鏁板﹀缓妯\...` 从而找不到路径。带 BOM 时按 UTF-8 解码，正常。这与交互式输入的编码无关（那条路径经 `[Console]::OutputEncoding` 正常）。
- 规定：
  1. 本机所有 `.ps1` 一律存成 **UTF-8 with BOM**（`E:\数学建模\APMCM2026\build.ps1`、`env.ps1` 已是）。
  2. 新建脚本用 `[IO.File]::WriteAllText($p, $text, (New-Object System.Text.UTF8Encoding($true)))` 落盘；不要用"无 BOM"的写法。
  3. 脚本里尽量**不写中文绝对路径**：用 `$PSScriptRoot` 派生，或从 `$env:MM_ROOT` 取。
- 验证：
  ```powershell
  $body = "Get-Content 'E:\数学建模\.tmp_scratch\pit\py_way2.py' -Raw | Select-Object -First 1"
  [IO.File]::WriteAllText("$env:TEMP\fw_nobom.ps1", $body, (New-Object System.Text.UTF8Encoding($false)))
  [IO.File]::WriteAllText("$env:TEMP\fw_bom.ps1",   $body, (New-Object System.Text.UTF8Encoding($true)))
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\fw_nobom.ps1" 2>&1 | Select-String 'does not exist'  # 期望命中
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\fw_bom.ps1"   2>&1 | Select-Object -First 1           # 期望正常内容
  ```
- 实测时间：2026-11-11
- 实测输出：无 BOM 版 `Cannot find path 'E:\鏁板﹀缓妯\.tmp_scratch\pit\py_way2.py' because it does not exist.`；带 BOM 版正常输出 `# -*- coding: utf-8 -*-`；`nobom: 涓枃OK` / `bom: 中文OK`
- 验证结果: **pass**

---

## 附：环境事实（供后续审计复用）

| 项 | 值（实测） |
| --- | --- |
| PowerShell | 5.1.26100.7627（`pwsh` 同版本），ACP/OEMCP = 936 |
| 运行身份 | Administrator（`IsInRole Administrator = True`） |
| TeX | MiKTeX 25.12，`xelatex/latexmk/pdftotext/pdftoppm/pdfinfo` 均在 `E:\MIKTEX\miktex\miktex\bin\x64\`；**无 perl** |
| conda | `E:\Mini\Library\bin\conda.bat`；env 列表见 P-E09；`mathmodel` = Python 3.11.18 |
| 关键包 | numpy 2.4.6 / scipy 1.17.1 / pandas 3.1.1 / matplotlib 3.11.2 / sklearn 1.9.1 / torch 2.14.1+cu126（CUDA 可用） |
| GPU | RTX 4060 Laptop 8188 MiB，driver 610.62（sm_89） |