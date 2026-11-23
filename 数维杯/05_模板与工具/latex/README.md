# 数维杯 LaTeX 成文骨架（官方模板，已验证可编译）

用**官方 2026 秋季赛 LaTeX 模板**（`swmcmthesis.cls` v1.8）搭的英文赛道骨架。
实测：`pdflatex ×3` → **8 页 / 263 KB / 8.8 s**，无未定义引用、无缺字符。

| 文件 | 说明 |
|---|---|
| `main_en.tex` | **英文赛道正文骨架**（官方 `swmcmthesis`），8 页 |
| `main_zh.tex` | 中文备用骨架（`ctexart` + biber/gb7714-2015），7 页；官方未发中文 cls 时用 |
| `swmcmthesis.cls` / `.cfg` | 官方类文件，**必须与 .tex 同目录** |
| `official\` | 官方原件副本（cls / cfg / demo.tex），出问题可回溯 |
| `gen_figures.py` | matplotlib 出图 → `figures\*.pdf` |
| `build.ps1` | 一键编译 + 页数/超页/警告/占位符体检 |
| `figures\` | `fig_convergence.pdf` / `fig_sensitivity.pdf`（示例数据） |
| `out\` | `main_en.pdf` / `main_zh.pdf`（成品） |

## 一键编译

```powershell
cd 'E:\数学建模\数维杯\05_模板与工具\latex'
.\build.ps1                 # 编英文（默认）
.\build.ps1 -MaxPages 25    # 换页数上限（默认 25）
.\build.ps1 -Clean          # 清中间文件，out\*.pdf 保留
.\build.ps1 -Target zh      # 备用：编中文骨架
```

编译序列：**en = `pdflatex ×3`**（目录 + `LastPage` 交叉引用，三遍才稳）；
**zh = `xelatex ×3 + biber`**（biblatex 要三轮：出 `.bcf` → biber → 读 `.bbl` → 定稿）。
英文不用 bibtex —— 参考文献是手写 `thebibliography`。

> **不要用 `latexmk`**：本机 `latexmk.exe` 是 Perl 脚本壳，而本机没有 Perl
> （`MiKTeX could not find the script engine 'perl'`）。

## 字体嵌入（交稿必查）

`gen_figures.py` 里设了 `pdf.fonttype=42` / `ps.fonttype=42`。**不设会出事**：
matplotlib 默认 `fonttype=3`，PDF 里的文字变成 Type 3 轮廓（`pdffonts` 显示 `Type 3`），
虽然 `emb` 仍是 `yes`，但文字不可复制、不可搜索，部分竞赛/期刊的自动检查会判"字体不合规"。

改完实测（`pdffonts out\main_en.pdf`）：

| 位置 | 改前 | 改后 |
|---|---|---|
| 正文/公式（newtx + TeXGyre） | Type 1 | Type 1（不变） |
| 图内文字（TimesNewRomanPSMT） | **Type 3** ×3 | **CID TrueType** |
| 图内公式（STIXGeneral） | **Type 3** ×3 | **CID TrueType** |

全表 `emb` 列全 `yes`、`sub` 全 `yes`、`uni` 全 `yes`。

## 官方模板的两个前置依赖（本机已修，换机器要重做）

官方 demo 在干净 MiKTeX 上编不过，卡在两处：

1. `! LaTeX Error: File 'fontaxes.sty' not found.`（由 `newtxtext.sty:344` 触发）
   → `mpm --install=fontaxes`
2. `!pdfTeX error: (file txtt): Font txtt at 657 not found`
   —— `txfonts` 装了、`txtt.tfm`/`txtt.pfb` 都在，缺的只是 **font map 没刷新**
   → `initexmf --mkmaps` + `initexmf --update-fndb`

修完 `pdflatex demo.tex` 输出 16 页，官方 demo 完整可编。
已设 `initexmf --set-config-value='[MPM]AutoInstall=1'`，后续缺包自动装。

## 本机踩过的坑（已绕开，写进脚本/模板）

1. **matplotlib 直接调 `python.exe` 会在 `savefig` 崩**：`0xC06D007F`（delay-load
   failure），进程被 kill、无 Traceback。原因：conda 未激活时 `Library\bin` 不在 PATH。
   `build.ps1` 已把 `env; Library\mingw-w64\bin; Library\usr\bin; Library\bin; Scripts; bin` 前置。
2. **表格单元格以 `[` 开头会炸**：`\\` 后的 `[` 被当可选参数 →
   `Missing number, treated as zero` / `Illegal unit of measure`。
   修法：`{[Ours (v1)]}` 加大括号。
3. **cls/cfg 不在同目录** → `File 'swmcmthesis.cls' not found`。
   `build.ps1` 现在从 `official\` 自动补，不用手抄。
4. **`build.ps1` 必须存 UTF-8 with BOM**：本机默认 shell 是 Windows PowerShell 5.1，
   无 BOM 按 ANSI 解码，中文注释打乱语法（`MissingEqualsInHashLiteral`）。
5. **中文文档不能用 bibtex**：中文 `.aux` 让 MiKTeX 25.12 的 `bibtex.exe`
   直接 `0xC0000374`（heap corruption，零输出）。中文一律 `biber`。
6. **python 打中文到控制台**会 `UnicodeEncodeError`（GBK）：
   需 `[Console]::OutputEncoding=UTF8` + `$env:PYTHONIOENCODING='utf-8'`。
7. **matplotlib 默认出 Type 3 字体**（见上节"字体嵌入"），必须设 `pdf.fonttype=42`。
8. **biblatex 只跑两遍会报 undefined references**：第一遍只生成 `.bcf`，
   biber 之后第二遍才读到 `.bbl`，交叉引用要第三遍才收敛。所以 zh 是 `xelatex ×3`。

## 本机实测基线（2026-11-17）

| 目标 | 引擎 | 页数 | 体积 | 耗时 | 未定义引用 | 占位符 |
|---|---|---|---|---|---|---|
| `-Target en` | pdflatex ×3 | 8 | 284.3 KB | 9.7 s | 0 | 61 |
| `-Target zh` | xelatex ×3 + biber | 7 | 177.4 KB | 18.3 s | 0 | 27 |

页数含封面 + 目录 + 正文 6 页 + 附录；英文口径 25 页上限，余量充足。
占位符是骨架态的预期值，不是错误 —— 但**交稿前必须归零**。

## 赛时替换清单（按顺序做）

1. **元信息**（`main_en.tex` 第 20~25 行附近）：
   `\title{}`、`\baominghao{SWBMCM2600001}`、`\zubie{C}`、`\date{2026}`。
   报名号与选题从官网/报名系统抄，别猜。
2. **摘要**（`\abstract{}`）：评委可能只读这一页。四段式 —— 问题与目标 / 建了什么模型、
   变量与约束 / 怎么解 / 三条带具体数字的发现 + 一句适用边界。400~600 词，不放公式不放引用。
3. **占位符清零**：全文红色 `[..]` 是 `\ph{}` 占位，`build.ps1` 每次都会报剩余数量。
   ```powershell
   Select-String -Path main_en.tex -Pattern '\[[A-Za-z][^\]]{2,80}\]'   # 还有哪些
   ```
4. **图**：改 `gen_figures.py` 换真实数据，或直接覆盖 `figures\*.pdf`。
   结构图/流程图优先 **TikZ 内联**（模板里 `fig:pipeline` 就是），改字不用重画。
5. **参考文献**：`thebibliography` 里手写 `\bibitem{}`，正文用 `\cite{bib:xxx}`。
   模板已给 4 条真实可查条目（NSGA-II / HiGHS 并行单纯形 / Saltelli 敏感性 / Boyd 凸优化），
   换成自己真引的，**别留没引用的条目**。
6. **页数**：`build.ps1` 打印页数并在超 `-MaxPages` 时标黄。英文口径 25 页。
7. **提交前**：`pdffonts out\main_en.pdf` 确认第二列全 `yes`（字体全嵌入）；
   官方要求**提交 PDF**。

## 官方类的已知行为（别当成 bug）

- `\zubie{C}` 会把封面右上角 "Problem Chosen" 下的字母排成**红色大字**，`ABCD` 全写也行。
- 页眉左 `Team # <报名号>`，右 `Page N of M`（`M` 来自 `lastpage`，所以要编三遍）。
- 目录标题是 `Content`（不是 Contents），`Key word:` 单数 —— 都是 cfg 里的官方措辞。
- `\section` 编号带尾点（`1.`），`\subsection` 不带（`3.2`）。
- 类已加载：amsmath/amssymb/bm、graphicx、booktabs、longtable、multirow、array、
  lastpage、caption、enumitem、listings、subfigure、pdfpages、cleveref、hyperref、
  newtxtext/newtxmath、lipsum、mwe、tikz **未**加载。重复 `\usepackage` 不报错，但没必要。
- 图片搜索路径已含 `figures/ figure/ pictures/ pic/ images/` 等，
  `\includegraphics{fig_x.pdf}` 不写目录也能找到。
- `tabular` 被类重定义为 `\arraystretch{1.3}`，行高比默认松，排三线表正好。
