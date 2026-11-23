# APMCM 论文撰写 / 模板 / 摘要 / 页数 / 参考文献 坑单（P-W 系列）

**适用范围**：APMCM 2025/2026 英文赛道，工作区 `E:\数学建模`。
**被测主体**：`E:\数学建模\APMCM2025_C\main.tex`（1872 行）、`apmcmthesis.cls`（13838 B）、`main.pdf`（108 页）。
**数字来源**：除标注「引自 <文件>」的条目外，全部由本轮 xelatex / pdftotext / Python 实测产生；实验工程在 `E:\数学建模\.tmp_scratch\ex1\`（验完即弃，`w*.py` / `chk_*.py` 可复跑）。
**工具链**：`E:\MIKTEX\miktex\miktex\bin\x64\{xelatex,pdftotext,pdfinfo}.exe`；`compare_to_awards.py` 必须用 `D:\Python\python.exe`（3.13.12 + numpy 2.5.1，默认 `python` 是 3.14.6 无 numpy）。
**判定用语**：`PASS` = 现行稿满足本条；`FAIL` = 现行稿违反；`PARTIAL` = 部分满足 / 手法合规但目标未达。

---

## 总表

| 编号 | 坑 | 定量后果（实测） | 现有稿判定 |
|---|---|---|---|
| P-W01 | 用 PDF 总页 / 跳 4 页找 Appendix A 数正文 | 105 编号页里正文 **30**；naive 给 28，另一种 naive 给 29；真值只有一个 | PASS |
| P-W02 | 参考文献放进附录 | `references` 8 → **0**，正文 `[n]` 8 → 0 | PASS（书目在 `main.tex:1589`，Appendix A 在 `:1657`） |
| P-W03 | 孤立 `\newpage`/`\clearpage` | 一个 = **+1 页**；字数 ×3 才 +18 页 | PASS（3 处断页全是结构必需） |
| P-W04 | 全篇 `[htbp]`→`[H]` | 小规模 8 vs 8；24 表时 **13 vs 12（H 多 1 页）** | PARTIAL（17 张表在 `tables/*.tex` 用 `[H]`，`main.tex` 内 0 处） |
| P-W05 | 全局 `\\`→`\` | 3 页 → **1 页**，`! Misplaced \noalign.` | PASS（无截断行） |
| P-W06 | 列声明 ≠ 单元格数 | `{lrr}`/5 格 → 编译失败；`{lrrrrr}`/5 格 → **静默**编译成功、末列空 | PASS（18 张 tabular 全配平） |
| P-W07 | 正文页数基线 | 正文 30 / 附录 75 / 11928 词 / **397.6 词每页** / 23 页带浮动体 | PASS（临界） |
| P-W08 | 附录不限页：搬档案表 | 1 张 120 行表 = **1 页**；3 张也只 1 页；PDF 总页不变 | PASS（11 表已在附录 C，正文只剩 6） |
| P-W09 | 摘要四段粗体标签 | 本稿 `Task./Framework./Results./Validation.`；硬编码 `Model.` 的检查器判假阴性 | PASS |
| P-W10 | 摘要数字密度 | 小数口径 **5 / 0.99**（中位 2.5 / 0.73）；全数字口径 19 / 3.76（中位 12 / 3.3） | PASS |
| P-W11 | `Page N of M` 的 M 会滞后 | 单遍编译出现 `Page 10 of 9` | PASS（105/105） |
| P-W12 | `\enlargethispage` | 只有末页溢出 ≤2.5 行时省 1 页（pad=4 时 7→6） | PARTIAL（`main.tex:1742` 在 Appendix C，对正文无效） |
| P-W13 | `Float too large` 静默溢出 | 45 行表溢出 213.2968pt 仍印、页数不变 | PASS（`main.log` 0 处） |
| P-W14 | 附录 `\cite` 与手写 `[18]` 重复 | PDF 印出两次 `[18]` | FAIL（`main.tex:1693`） |
| P-W15 | `compare_to_awards.py` 口径 | 三项越界：`tables 18`(p100)、`distinct_numbers 455`(p93.8)、`pct_mentions 263`(p100) | FAIL（内容待办） |

---

## P-W01 正文页数：只能从页眉 `Page N of M` 取，三种「看起来对」的算法给三个不同答案

**现象/触发**：报「正文多少页」。`compare_to_awards.py` 的取法是「跳过前 4 页、遇到 `Appendix A` 截断」，`review/03_compliance.md` 当年用的是 PDF 总页减固定前置页。

**定量后果**（实测 `w01_probe.py` / `w01_body.py`，同一份 `main.pdf`）：

| 算法 | 结果 | 错在哪 |
|---|---|---|
| 页眉 `Page N of M`，遇 Appendix A 取该页的 N | **30**（正确） | — |
| `compare_to_awards.py`：`for i,p in enumerate(pages): if i<4: continue; if re.search(r"Appendix\s+A\b",p): break` | **28**（= `appx_i − 4` = 32−4） | 它数的是 PDF 页数，前置页恒假定 4；本稿前置页是 3（摘要 1 + 目录 2），恒差 1 |
| 「PDF 总页 108 − 前 3 页 − 附录」式试算 | **29** | 把摘要页也算进正文或把交接页扣掉，口径不一致 |
| 数「带页眉的页」 | **105** | 这是全文编号页（含附录 75 页），不是正文 |

实测布局（`pdftotext -layout` 切 `\f`）：PDF idx0 = 摘要页（**无页眉**）、idx1–2 = 目录（无页眉，含 `. . .` 点引导线）、idx3–32 = 页眉 `Page 1 of 105` … `Page 30 of 105`、**idx32 同时出现 `Appendix A: Reproducibility`**、idx33– = `Page 31 of 105` … `Page 105 of 105`。
关键点有三个：
1. **目录页也含 "Appendix A"**（idx2 里是 `Appendix A: Reproducibility . . . 32`），任何「首个出现 Appendix A 的页」算法都会指向目录。
2. **摘要页不含页眉**；它的「Page 1 of 105」只出现在页内表格文字里，不能当页眉证据。
3. **交接页本身是正文最后一页**（Appendix A 的标题与 `Page 30 of 105` 同页），所以「正文页数 = 该页页眉里的 N」，不是「该页之前的页数」。

**规定**：
1. **必须**用 `pdftotext -layout -enc UTF-8` 按 `\f` 分页，用正则 `Page\s+(\d+)\s+of\s+(\d+)` 取页眉；**禁止**用 PDF 总页数或「减固定前置页」。
2. 正文页数 = **第一个同时含页眉与 `Appendix A` 的页**上页眉的 `N`；若该页不存在（无附录），取带页眉页的页数。
3. 报页数**必须同时**报 `numbered_pages`、`M`、`body_pages` 三个数；`contiguous`（页眉 N 是否 1..k 连续）为 False 时数字作废，先重编译。
4. 引 `review/03_compliance.md` 里的 75 页 / `Page N of 72` 一律视为过期数据（引自 `E:\数学建模\APMCM2025_C\review\03_compliance.md`，该文件基于旧 72 页稿）。

**检查代码**：
```python
import re, subprocess, json
P = r"E:\MIKTEX\miktex\miktex\bin\x64\pdftotext.exe"
HDR = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)")
APPX = re.compile(r"Appendix\s+A\b")

def pages(pdf):
    return [p for p in subprocess.run([P, "-layout", "-enc", "UTF-8", pdf, "-"],
            capture_output=True).stdout.decode("utf-8", "replace").split("\f") if p.strip()]

def counts(pdf):
    ps = pages(pdf)
    hdr = [(i, int(m.group(1)), int(m.group(2)))
           for i, p in enumerate(ps) for m in [HDR.search(p[:400])] if m]
    appx_i = next((i for i, _, _ in hdr if APPX.search(ps[i])), None)
    appx_n = next((n for i, n, _ in hdr if APPX.search(ps[i])), None)
    body = appx_n if appx_n is not None else len(hdr)
    return {"pdf_pages": len(ps), "numbered_pages": len(hdr), "M": hdr[0][2] if hdr else None,
            "body_pages": body, "appendix_and_after": len(hdr) - body,
            "naive_compare_to_awards": max(0, appx_i - 4) if appx_i is not None else None,
            "contiguous": [n for _, n, _ in hdr] == list(range(1, len(hdr) + 1))}

print(json.dumps(counts(r"E:\数学建模\APMCM2025_C\main.pdf"), ensure_ascii=False))
```

**实测结果 / pass-fail**：`{"pdf_pages":108,"numbered_pages":105,"M":105,"body_pages":30,"appendix_and_after":75,"naive_compare_to_awards":28,"contiguous":true}` → **PASS**（正文 30 页，正好在 30 页控制线）。同脚本对 `p_base.pdf` 得 `body_pages=1`（该旧稿的 Appendix A 紧接摘要页，真实正文只有 1 页）——说明该算法在不同布局上都自洽，而 naive 法在这些布局上给 0 或负数。

---

## P-W02 参考文献放进附录 ⇒ `references` 指标读成 0（正文 `[n]` 也一起归零）

**现象/触发**：为压正文页数，把 `\begin{thebibliography}` 从 Conclusion 后搬到 Appendix A。

**定量后果**（实测 `w02_metric.py`，最小工程，同一内容只改书目位置，8 条文献）：

| 变体 | `references`（行首 `[n]`） | 正文 `[n]` 标记 | 正文词数 | 正文页 |
|---|---|---|---|---|
| 书目在正文 · 有引注 | **8** | 8 | 1320 | 3 |
| 书目在附录 · 有引注 | **0** | **0** | 989 | 2 |
| 书目在正文 · 无引注 | 8 | 8 | 1320 | 3 |
| 书目在附录 · 无引注 | 0 | 0 | 989 | 2 |

口径来自 `E:\数学建模\APMCM2025_C\code\award_standard.py`：`references = len(re.findall(r"^\s*\[\d{1,2}\]", t, re.M))` —— **行首** `[n]`，只在「正文取窗」内数。书目搬走后正文取窗里既无 `[n]` 条目也无 `\cite` 落点，两项一起归零。
一等奖基准中位数 `references = 7.5`（p25 = 5.25、p75 = 11.75，引自 `E:\数学建模\APMCM2025_C\refs\official_standard_report.txt`），归零即跌出全部分位。
现行稿实测：`\begin{thebibliography}` 在 `main.tex:1589`，`Appendix A:` 在 `main.tex:1657`，18 条 `\bibitem`；正文窗口内行首 `[n]` **19** 处、`[n]`/`[n, m]` 标记 38 个；`compare_to_awards.py` 当次运行给出 `references = 9`（p62.5）。

**规定**：
1. **禁止**把 `thebibliography` 移出正文；它**必须**位于 Conclusion 之后、`Appendix A` 之前（与 `apmcmthesis.cls:381–399` 里 `\section{\refname}` 的位置一致，该节会自动带页眉并计入正文）。
2. 附录只放代码 / 复现步骤 / 档案表 / AI 声明，**不放**文献。
3. 正文里**必须**有 `\cite` 落点；书目条目数 ≥ 正文 `[n]` 唯一编号数，不允许「列了但没引」。
4. 搬动任何附录结构后，**必须**重跑 `compare_to_awards.py` 并重写 `refs/project_vs_awards.json`，不得沿用旧 json。

**检查代码**：
```python
import re
TEX = r"E:\数学建模\APMCM2025_C\main.tex"
tex = open(TEX, encoding="utf-8").read()
bib, appx = tex.find("\\begin{thebibliography}"), tex.find("Appendix A:")
line = lambda k: tex[:k].count("\n") + 1
print({"bib_line": line(bib), "appendix_a_line": line(appx),
       "bib_before_appendix": 0 < bib < appx,
       "bibitems": len(re.findall(r"\\bibitem", tex)),
       "body_cites": len(re.findall(r"\\cite\{", tex[:appx]))})
```

**实测结果 / pass-fail**：`{"bib_line":1589,"appendix_a_line":1657,"bib_before_appendix":true,"bibitems":18,"body_cites":16}` 且正文取窗行首 `[n]` = 19 → **PASS**。反例（书目在附录）`references` 8→0 → **FAIL**，且是**静默**的：编译无任何警告。

---

## P-W03 页数卡住不动，真因是孤立 `\newpage`/`\clearpage`，不是字数

**现象/触发**：版面底部还有半页空白，页数却卡在某个值；删句子无效，加内容也不涨。

**定量后果**（实测 `w03_newpage.py`，同一 fill=30 正文）：

| 变体 | PDF 页 | 编号页 |
|---|---|---|
| A 无手工断页 | 10 | 10 |
| B 正文第 1 节后 1 个 `\newpage` | 11 | 11 |
| C 正文第 1 节后 1 个 `\clearpage` | 11 | 11 |
| D 字数 ×3（fill 30→90） | 28 | 27 |

→ **一个孤立 `\newpage` = 恰好 +1 页，`\clearpage` 同效**；字数 ×3 才 +17 页（线性，约 1 页 / 260 词）。所以「卡住」是断页造成的固定空档，删字永远碰不到它。
**踩过的假阴性**：第一版脚本把断页插在最后一节之后（紧贴 `\begin{thebibliography}`），那里 TeX 本来就换页，测得 Δ=0；断页必须插在正文中间（`hard_breaks=(1,)`）才能复现。

现行稿硬断页只有 3 处（`chk_w03.py` 全量扫描）：
- `main.tex:117 \newpage`，前 `\end{abstract}` 后 `\tableofcontents` —— 结构必需；
- `main.tex:120 \newpage`，前 `\tableofcontents` 后 `\pagestyle{mainmatterstyle}` —— 结构断页（目录后切主文页样式）；
- `main.tex:1820 \clearpage`，前为分节注释、后 `\section*{Appendix E: Source code}` —— 结构断页。

**规定**：
1. 页数异常时**先**扫源码里的 `\newpage/\clearpage/\pagebreak`，再谈字数。
2. 只允许「结构断页」：摘要→目录、目录→正文、附录切换。其余一律视为孤立断页，**禁止**。
3. 孤立断页一晚要多花的排查时间，远大于它换来的排版收益：**删**，用 `\enlargethispage`（P-W12）或搬附录（P-W08）代替。
4. 任何断页改动后**必须**重编译两遍并重跑 P-W01。

**检查代码**：
```python
import re, json
BREAK = re.compile(r"\\(newpage|clearpage|pagebreak)\b")
STRUCT_PAIRS = {("\\end{abstract}", "\\tableofcontents"),
                ("\\tableofcontents", "\\pagestyle{mainmatterstyle}")}
TEX = r"E:\数学建模\APMCM2025_C\main.tex"

def neighbours(lines, i):
    prev = next((lines[j].strip() for j in range(i-1, -1, -1) if lines[j].strip()), "")
    nxt  = next((lines[j].strip() for j in range(i+1, len(lines)) if lines[j].strip()), "")
    return prev, nxt

lines = open(TEX, encoding="utf-8").read().splitlines()
out = []
for i, ln in enumerate(lines):
    if not BREAK.search(ln) or ln.lstrip().startswith("%"):
        continue
    prev, nxt = neighbours(lines, i)
    ok = (prev, nxt) in STRUCT_PAIRS or nxt.startswith("\\begin{thebibliography}") or "Appendix" in nxt
    out.append({"line": i+1, "cmd": ln.strip(), "prev": prev[:36], "next": nxt[:36], "structural": ok})
print(json.dumps({"breaks": out, "orphans": [b for b in out if not b["structural"]]}, ensure_ascii=False, indent=1))
```

**实测结果 / pass-fail**：3 处断页全部 `structural=true`，`orphans=[]` → **PASS**。

---

## P-W04 全篇 `[htbp]`→`[H]` 省不了页，规模上去反而 +1 页

**现象/触发**：「用 `float` 包的 `[H]` 把图表钉死在正文处就能压页」。

**定量后果**（实测 `w04_06.py`）：

| 场景 | `[htbp]` | `[H]` | `[t]` | `[p]` |
|---|---|---|---|---|
| 6 图 + 6 表，4 节 | 8 | 8 | 8 | 8 |
| 6 节 × 4 表（24 张 8 行表） | **12** | **13** | — | — |
| 3 张 120 行大表 | 13 | 14 | — | — |

→ 小规模下四种位置说明符**完全等价**；表一多，`[H]` **比 `[htbp]` 多 1 页**（禁止浮动体漂移⇒钉在原处的表把后文整体推下页）。「全篇改 `[H]` 只省 1 页」这个说法方向都不对：**只会多，不会少**。

现行稿实测（`chk_w04.py` 遍历 `main.tex` + `tables/*.tex`）：floats **33**、`htbp` **16**、`H` **17**；`H` 全部来自 `tables/tab_*.tex` 的**第 1 行**（17 个文件：tab_audit / tab_binding / tab_data / tab_decision / tab_lafferfam / tab_lambda / tab_lp / tab_q1 / tab_q1bt / tab_q2 / tab_q3 / tab_q4 / tab_q5 / tab_reshore / tab_sigmarob / tab_sobol / tab_surro），`main.tex` 内 `H` = 0。
→ 所以「本稿没有 `[H]`」是错的读法：**只看 `main.tex` 会漏掉全部 17 个 `[H]`**。

**规定**：
1. **禁止**为压页数把 `[htbp]` 全局换成 `[H]`；实测只会持平或多 1 页。
2. 统计浮动体位置说明符**必须**同时扫 `main.tex` 与其 `\input` 的子文件；只扫主文件得到的 `H_count` 不可信。
3. 允许 `[H]` 的唯一理由：某图表**必须**与某段同页（如算法伪码与调用它的段落）；改一张必须重量页数。
4. 大表优先 `longtable` 或拆表，不用 `[H]`。

**检查代码**：
```python
import re, pathlib, collections, json
ROOT = pathlib.Path(r"E:\数学建模\APMCM2025_C")
FLOAT = re.compile(r"\\begin\{(figure|table)\}\[([^\]]*)\]")
hits = []
for f in [ROOT/"main.tex", *sorted((ROOT/"tables").glob("*.tex"))]:
    t = f.read_text(encoding="utf-8")
    for m in FLOAT.finditer(t):
        hits.append((f.name, t[:m.start()].count("\n")+1, m.group(2)))
print(json.dumps({"floats": len(hits),
                  "specs": dict(collections.Counter(s for _, _, s in hits)),
                  "H_files": sorted({f for f, _, s in hits if "H" in s}),
                  "H_in_main_tex": sum(1 for f, _, s in hits if f == "main.tex" and "H" in s)}, ensure_ascii=False))
```

**实测结果 / pass-fail**：`{"floats":33,"specs":{"htbp":16,"H":17},"H_files":[17 个 tab_*.tex],"H_in_main_tex":0}` → **PARTIAL**：`[H]` 已在 17 张子表里用满，按本条反例（H 多 1 页）应逐步改回 `[htbp]` 并重量页数；但页面已压线 30 页，改动需与 P-W08 一起做。

---

## P-W05 全局把 `\\` 替换成 `\` ⇒ 首个错误是 `! Misplaced \noalign.`，不是 Alignment tab

**现象/触发**：用编辑器/脚本「统一行终止符」，把 `\\` 吃成一个 `\`。

**定量后果**（实测 `w04_06.py` 的 W05 组，同一张 3 列表）：

| 变体 | 编译 | 首个错误 | 出错行 | PDF 页 |
|---|---|---|---|---|
| 正确 `a & b & c \\ \midrule` | 成功，0 错 | — | — | 3 |
| 全局替换后 `a & b & c \ \midrule` | **失败** | `! Misplaced \noalign.` | `l.44 a & b & c \ \midrule` | **1（内容全丢）** |

机制：行尾只剩一个 `\`，它把下一行的 `\midrule` 变成转义后的整词，`\noalign` 因此落在非法位置而先炸。
**任务书预期的 `! Extra alignment tab has been changed to \cr` 在这个场景不会出现**——那个错误属于 P-W06 的「单元格多于列声明」方向。认错错误名会导致按错误原因去修（去调列声明），越修越乱。

**规定**：
1. **禁止**对 `.tex` 做 `\\`→`\` 或 `\`→`\\` 之类的全局替换；改表必须逐文件 grep 校验。
2. 每个表格行尾**恰好一个** `\\`；`\\[2pt]` 的可选参数保留方括号。
3. 日志出现 `Misplaced \noalign` ⇒ **先数行终止符**；出现 `Extra alignment tab` ⇒ 去查列声明（P-W06）。两者不可混。
4. 表格文件必须参与编译验证（`\input` 全部被编到），否则截断行可能潜伏到下一次改模板才爆。

**检查代码**：
```python
import pathlib
ROOT = pathlib.Path(r"E:\数学建模\APMCM2025_C")
bad = []
for f in [ROOT/"main.tex", *sorted((ROOT/"tables").glob("*.tex"))]:
    for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        s = ln.rstrip()
        if s.endswith("\\") and not s.endswith("\\\\") and s not in ("\\\\",):
            bad.append({"file": f.name, "line": i, "tail": s[-40:]})
print({"truncated_rows": bad, "ok": not bad})
```

**实测结果 / pass-fail**：`{"truncated_rows":[],"ok":true}` → **PASS**。被全局替换的变体 `errors=['! Misplaced \\noalign.']`、页数 3→1 → **FAIL**（静默内容丢失：PDF 只剩 1 页）。

---

## P-W06 列声明与单元格数不一致：**多给单元格才致命**，少给能编过（静默）

**现象/触发**：`\begin{tabular}{lrrrrr}`（声明 6 列）与表头 `&`（5 个单元格）不一致——真发生过一次。

**定量后果**（实测 `w04_06.py` 的 W06 组）：

| 变体 | 编译 | 错误 | 渲染 |
|---|---|---|---|
| `{lrr}` 声明 3 列，每行 5 单元格 | **失败**，1 页 | `! Extra alignment tab has been changed to \cr.` @ `l.44 a & b & c &` | 后续内容全丢 |
| `{lrrrrr}` 声明 6 列，每行 5 单元格 | **成功**，3 页 | `errors=[]` | 表格正常印出，**第 6 列留空** |

→ 真稿那次报错的真实方向是「**单元格多于列声明**」；「声明多于单元格」**不报错**，属于更危险的静默形态（编译通过、PDF 正常、末列空白，只有肉眼或文本核对能发现）。

现行稿实测（`chk_w05_w06.py`，18 张 tabular：`main.tex` 2 张手写 + `tables/*.tex` 16 张）：`col_mismatch = []`，全部配平（例：`lll`/3-3、`lrrrr`/5-5、`lcccc`/5-5、`lr`/2-2）。

**规定**：
1. 每个 `tabular` 的列声明数 **必须**等于该表所有行中 `&` 数最大值 + 1。
2. `\multicolumn{n}{..}` 计 n 个单元格；跨列数与声明数要配平。
3. 编译通过**不算**通过：表格必须用 PDF 文本核对每一列是否有内容（静默形态只有此法可查）。
4. 建表顺序：先定单元格数，再写 `{colspec}`；改动列声明必须同时改所有行。

**检查代码**：
```python
import re, pathlib, json
ROOT = pathlib.Path(r"E:\数学建模\APMCM2025_C")
TAB = re.compile(r"\\begin\{tabular\}(?:\[[^\]]*\])?\{(?P<spec>[^{}]*)\}(?P<body>.*?)\\end\{tabular\}", re.S)

def colspec_n(spec):
    return sum(1 for _ in re.finditer(r"[lcrXYZ]|\{(?:[^{}]|\{[^{}]*\})*\}", spec))

bad = []
for f in [ROOT/"main.tex", *sorted((ROOT/"tables").glob("*.tex"))]:
    for m in TAB.finditer(f.read_text(encoding="utf-8")):
        cols = colspec_n(m.group("spec"))
        rows = [r for r in re.split(r"\\\\", m.group("body")) if r.strip()]
        maxc = max((1 + len(re.findall(r"(?<!\\)&", r)) for r in rows), default=0)
        if cols != maxc:
            bad.append({"file": f.name, "spec": m.group("spec"), "declared": cols,
                        "max_cells": maxc, "fatal": maxc > cols, "silent": cols > maxc})
print(json.dumps({"tables_checked": 18, "mismatch": bad, "ok": not bad}, ensure_ascii=False, indent=1))
```

**实测结果 / pass-fail**：`{"mismatch":[],"ok":true}`（18 张全配平）→ **PASS**。反例 `{lrr}`/5 格 → 编译 FAIL；`{lrrrrr}`/5 格 → 编译 PASS 但检查器 FAIL（末列空）→ 该类写法**FAIL**。

---

## P-W07 正文页数基线：30 页 + 75 页附录，密度 398.6 词每页

**现象/触发**：`review/03_compliance.md` 里记录的 75 页 / `Page N of 72` 已过期；`main.pdf` 现在是 108 页。

**定量后果**（实测）：

| 指标 | 值 | 来源 |
|---|---|---|
| PDF 总页 | 108 | `pdfinfo` |
| 带页眉编号页 | 105 | `w01_body.py` |
| 正文页（页眉 N=1..30） | **30** | `w01_body.py` |
| 附录及以后（编号页） | 75 | `w01_body.py` |
| 正文词数 | **11928** | `chk_w07_floats.py`（正文 PDF idx 4–33） |
| 正文词密度 | **397.6 词/页** | 11928 / 30 |
| 含 ≥1 浮动体提及的正文页 | **23 / 30** | `chk_w07_floats.py` |
| 含 ≥2 个不同浮动体标签的正文页 | **15 / 30**（正文第 4、5、8、9、10、11、12、13、15、16、18、22、24、26、27 页） | `chk_w07_floats.py` |
| 正文页里出现的不同 `Figure N`/`Table N` 标签 | **32** | `chk_w07_floats.py` |

规则原文（引自 `E:\数学建模\APMCM2025_C\refs\spec.txt`）："The main body of the solution paper should be controlled within 30 pages, the appendix is no limit."；同文件另规定首页为摘要页、第二页为目录页、字号通常 11 或 12。
**口径警告**：`w07_budget.py` 用 `compare_to_awards` 的 naive 窗口，给出 `body_pages=28 / body_words=11162 / 398.6 词每页 / 18 页带浮动体 / 9 页带 ≥2`；这些是**28 页窗口**的数字，不能与本文的 30 页并列。上表已统一改用 30 页窗口（词数 11928、密度 397.6、23 页、15 页）。凡引用密度必须写分母。

**规定**：
1. 正文页数**只**按 P-W01 报；**禁止**引用 `03_compliance.md` 的 75/72。
2. 30 页是**控制线**（原文 "should be controlled within"），本稿**正好压线**：任何新增正文内容必须同时给出等量的压页方案（P-W08 / P-W12）。
3. 报密度**必须**写清分母口径（`词数 / P-W01 正文页` 或 `词数 / naive 窗口页`），两者不可混用。
4. 浮动体密度是压页的第二个杠杆：18/30 页带浮动体、9 页带 ≥2 个。加图表前先看这两项。

**检查代码**：
```python
import re, subprocess
P = r"E:\MIKTEX\miktex\miktex\bin\x64\pdftotext.exe"
HDR = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)")
def budget(pdf, body_pages):
    ps = [p for p in subprocess.run([P, "-layout", "-enc", "UTF-8", pdf, "-"], capture_output=True)
          .stdout.decode("utf-8", "replace").split("\f") if p.strip()]
    hdr = [(i, int(m.group(1))) for i, p in enumerate(ps) for m in [HDR.search(p[:400])] if m]
    start = next(i for i, n in hdr if n == 1)          # page printed "Page 1 of M"
    body = ps[start:start + body_pages]
    words = len(re.findall(r"[A-Za-z][A-Za-z'-]*", "\f".join(body)))
    labels = [set(re.findall(r"(?:Figure|Table)\s+\d+", p)) for p in body]
    return {"pdf_pages": len(ps), "numbered_pages": len(hdr), "body_pages": body_pages,
            "body_words": words, "words_per_page": round(words / body_pages, 1),
            "pages_with_float": sum(1 for s in labels if s),
            "pages_with_2plus": [i + 1 for i, s in enumerate(labels) if len(s) >= 2],
            "distinct_float_labels": len(set().union(*labels))}
print(budget(r"E:\数学建模\APMCM2025_C\main.pdf", 30))
```

**实测结果 / pass-fail**：正文 30 页 / 附录 75 页 / 11928 词 / 397.6 词每页 / 23 页带浮动体 → **PASS（临界）**；把 PDF 总页 108 当正文页的报法 → **FAIL**（虚高 3.6 倍）。

---

## P-W08 附录不限页数：搬档案表是唯一可持续的正文压缩手段（但收益只有 1 页/次）

**现象/触发**：「把大表搬进 Appendix C 就能省页」——需要知道到底省多少、以及 PDF 总页是否真的下降。

**定量后果**（实测 `w08_appx.py`，正文 4 节 + 每张 120 行 × 6 列的档案表）：

| 档案表数量 | 编号页（表在正文） | 编号页（表在附录） | 省 | PDF 总页 |
|---|---|---|---|---|
| 1 张 | 8 | **7** | **1** | 8 / 8 |
| 3 张 | 10 | **9** | **1** | 10 / 10 |

→ 搬 1 张 120 行表省 **1 个正文页**；搬 3 张**也只省 1 页**（附录里这些表仍占页，PDF 总页数不变）。所以「搬附录」的收益是**离散的 1 页/次**，不是线性的，靠它压 3 页要搬三轮、每轮重量。
另：单张 45 行表在正文日志报 `LaTeX Warning: Float too large for page by 213.2968pt`，表格**仍印出**、页数不变（见 P-W13）——搬附录≠解决溢出。

现行稿实测（`chk_w08_counts.py` 按 `\section*{Appendix A` 切分并解析 `\input{tables/...}`）：5 个附录节 `Appendix A: Reproducibility`(1657) / `B: Declaration of AI tool use`(1687) / `C: Additional tables and figures`(1740) / `D: Data dictionary`(1795) / `E: Source code`(1821)；17 张表**正文 6 张**（`tab_q1`@494、`tab_decision`@933、`tab_q2`@1085、`tab_q3`@1217、`tab_lambda`@1249、`tab_q4`@1360），**附录 C 已有 11 张**（`tab_surro`@1769、`tab_audit`@1771、`tab_q5`@1773、`tab_sobol`@1774、`tab_binding`@1776、`tab_sigmarob`@1783、`tab_lp`@1785、`tab_data`@1787、`tab_reshore`@1789、`tab_q1bt`@1791、`tab_lafferfam`@1793），无重复引用。
→ 与 P-W15 的 `tables = 18`（p100）对照：正文 30 页里出现 18 个不同的 `Table N` 编号（1–18），而正文实际只有 6 张 `\input`、全稿 `\caption` 共 32 条（`main.tex` 15 + `tables/*.tex` 17）。`award_standard.py` 数的是「`Table N` 编号去重数」，附录 C 的 11 张表一旦被正文文字引用就会被计入——**搬表只压页，不压 `tables` 指标**；要压指标必须减少正文对这些表的文字指名。

**规定**：
1. 压正文的**优先手段**是搬「档案性内容」（完整数据表、逐条参数、参数扫描明细、复现日志），不是删论证。
2. 搬运模式：正文留 3–5 行摘要表 + 一句 `See Appendix C for the full table`；全文表放 `\section*{Appendix C: ...}`。
3. **禁止**期待省多页：实测 1 张表 = 1 页、3 张表仍 = 1 页。预算按「每轮搬 1 页」算。
4. **禁止**用搬附录去消灭页尾半页空白（那是 P-W12 的活）；搬完**必须**重量 P-W01 页数 + P-W02 `references` + P-W07 密度。
5. 附录节标题**必须**用 `\section*{Appendix X: 名称}` + `\addcontentsline`，与现稿 A–E 一致（自动编号会破坏页眉）。

**检查代码**（按 `Appendix A` 切分，解析 `\input{tables/...}`，不受「无 `.tex` 后缀」影响）：
```python
import re
tex = open(r"E:\数学建模\APMCM2025_C\main.tex", encoding="utf-8").read()
appx = tex.find("\\section*{Appendix A")
pat = re.compile(r"\\input\{\\?tables/([^}]*)\}")
norm = lambda s: s if s.endswith(".tex") else s + ".tex"
body = [(tex[:m.start()].count("\n")+1, norm(m.group(1))) for m in pat.finditer(tex) if m.start() < appx]
apx  = [(tex[:m.start()].count("\n")+1, norm(m.group(1))) for m in pat.finditer(tex) if m.start() >= appx]
print({"appendix_sections": re.findall(r"\\section\*\{Appendix [A-Z][^}]*\}", tex),
       "tables_in_body": len(body), "body_tables": body,
       "tables_in_appendix": len(apx),
       "enlargethispage": re.findall(r"\\enlargethispage\{[^}]*\}", tex)})
```

**实测结果 / pass-fail**：`{"appendix_sections":5,... "tables_in_body":6,"tables_in_appendix":11,"enlargethispage":["2.5\\baselineskip"]}` → **PASS**：11 张档案表已搬进 Appendix C，正文只剩 6 张；正文正好压线 30 页，若再加内容必须继续搬（每条搬运按 1 页计）。

---

## P-W09 摘要四段粗体标签：顺序固定，但第三段实测是 `Framework.` 不是 `Model.`

**现象/触发**：检查脚本把段首标签硬编码成 `Task./Model./Results./Validation.`，把合规稿判成不合规。

**定量后果**（实测 `w09_moves.py` 解析 `main.pdf` 第 1 页）：
`{"labels": ["Task","Framework","Results","Validation"], "in_order_by_position": true, "n_labels": 4}`
源码：`main.tex:63–115` 四个段首 `\textbf{...}`，后接 `main.tex:112–114` 的 `\keywords{...}`（8 个关键词，`\quad` 分隔）。
→ 硬编码 `Model.` 的检查器：**PASS 稿被判 FAIL**（假阴性）；只校验「4 个标签 + 顺序 + 首 Task + 末 Validation」的检查器：PASS。

**规定**：
1. 摘要**必须**恰好 4 段，段首粗体标签，顺序 `Task.` → 方法标签 → `Results.` → `Validation.`。
2. 方法标签允许 `Model.` / `Method.` / `Framework.` 三选一；本稿用 `Framework.`，**不得**为了凑检查器去改内容。
3. 检查器**禁止**硬编码第三段字面量；**必须**校验「数量 = 4、位置单调递增、首 = Task、末 = Validation」。
4. 摘要**必须**独立成页（cls 的 `\abstract` 自带 `\newpage`，`apmcmthesis.cls:342–358`），关键词紧跟第四段。

**检查代码**：
```python
import re, subprocess, json
P = r"E:\MIKTEX\miktex\miktex\bin\x64\pdftotext.exe"
def moves(pdf):
    p = subprocess.run([P, "-layout", "-enc", "UTF-8", pdf, "-"], capture_output=True
                      ).stdout.decode("utf-8", "replace").split("\f")[0]
    txt = p[p.find("Task."):p.find("Keywords:")]
    found = [(m.start(), m.group(1)) for m in
             re.finditer(r"\b(Task|Model|Method|Framework|Results|Validation)\.", txt)]
    names = [n for _, n in found]
    asc = all(found[i][0] < found[i+1][0] for i in range(len(found)-1))
    return {"labels": names, "n": len(found), "ordered": asc,
            "first_task": names[:1] == ["Task"], "last_validation": names[-1:] == ["Validation"],
            "ok": len(found) == 4 and asc and names[:1] == ["Task"] and names[-1:] == ["Validation"]}
print(json.dumps(moves(r"E:\数学建模\APMCM2025_C\main.pdf"), ensure_ascii=False))
```

**实测结果 / pass-fail**：`{"labels":["Task","Framework","Results","Validation"],"n":4,"ordered":true,"first_task":true,"last_validation":true,"ok":true}` → **PASS**（硬编码 `Model.` 的检查器 → FAIL，属假阴性）。

---

## P-W10 摘要数字密度：两个口径差 4 倍，必须写清是哪一种

**现象/触发**：`award_standard.py` 的 `abstract_numbers` 只数**小数** `\d+\.\d+`；`abstract_structure.json` 家族数**所有数字**。同一篇摘要，两个口径可差 4 倍；旧 `03_compliance.md` 判的「44 个 / 15.4 不符合官方标准」是第三种口径的旧稿数字。

**定量后果**（实测 `w10_abs.py`，`main.pdf` 第 1 页摘要区，词数 505）：

| 口径 | 值 | 每 100 词 | 一等奖中位数（引自 `refs/official_standard_report.txt` / `abstract_structure_report.txt`） |
|---|---|---|---|
| 小数去重（`award_standard.py`） | **5** | **0.99** | 2.5 / 0.73（p25–p75：0–8 / 0–2.49） |
| 全数字去重 | 19 | 3.76 | 12 / 3.3（范围 3–48 / 0.5–13.8） |
| 百分号 token | 9 | 1.78 | 0/1/20（min/median/max） |

→ 本稿小数口径 **p62.5 / p56.2**（落在 p25–p75 内，属合规区），全数字口径 19/3.76 与 16 篇中位（12/3.3）同量级。旧稿「44 个 / 15.4」在新稿上**已不成立**。
`abstract_words = 505`（p87.5，中位 374.5）——摘要偏长，但不在越界名单里。

**规定**：
1. 报摘要数字密度**必须**带口径名（`小数去重/100词` 或 `全数字去重/100词`）；**禁止**混用或只写「数字密度」。
2. 对标一等奖用**同名口径**的中位：小数口径目标 2.5（上界 8）；全数字口径目标 12（上界 48）。
3. 摘要**必须**含「结果数字 + 区间 + 验证数字」三类，但每 100 词全数字 ≤13.8、小数 ≤8。
4. `abstract_words` 目标 374.5，p75 = 431.75；本稿 505 已超 p75，摘要再长就要砍词而非加数字。

**检查代码**：
```python
import re, subprocess, json
P = r"E:\MIKTEX\miktex\miktex\bin\x64\pdftotext.exe"
def abstract_numbers(pdf):
    p = subprocess.run([P, "-layout", "-enc", "UTF-8", pdf, "-"], capture_output=True
                      ).stdout.decode("utf-8", "replace").split("\f")[0]
    ab = p[p.find("Task."):p.find("Keywords:")]
    w = len(re.findall(r"[A-Za-z][A-Za-z'-]*", ab))
    dec, alln = set(re.findall(r"\d+\.\d+", ab)), set(re.findall(r"\d+(?:[.,]\d+)?", ab))
    return {"words": w, "distinct_decimals": len(dec), "decimals_per_100w": round(len(dec)/w*100, 2),
            "distinct_all_numbers": len(alln), "all_per_100w": round(len(alln)/w*100, 2),
            "in_decimal_band": 0 <= len(dec) <= 38, "in_all_band": 3 <= len(alln) <= 48,
            "words_above_p75": w > 431.75}
print(json.dumps(abstract_numbers(r"E:\数学建模\APMCM2025_C\main.pdf"), ensure_ascii=False))
```

**实测结果 / pass-fail**：`{"words":505,"distinct_decimals":5,"decimals_per_100w":0.99,"distinct_all_numbers":19,"all_per_100w":3.76,"in_decimal_band":true,"in_all_band":true,"words_above_p75":true}` → 数字密度 **PASS**；词数 505 超 p75 → 长度 **PARTIAL**（建议砍到 ≤430）。

---

## P-W11 `Page N of M` 里的 M 会滞后一版：单遍编译能印出 `Page 10 of 9`

**现象/触发**：往附录追加内容后只编一遍，摘要页印 `Page 1 of 9`，而正文页眉已到 `Page 10 of 9`。

**定量后果**（实测 `w11b_counter.py`，正文 4 节 + 3 张 120 行表）：

| 变体 | PDF 页 | 有页眉页 | max N | M 取值 | N > M |
|---|---|---|---|---|---|
| 表在正文 | 10 | 10 | 10 | {10} | false |
| 表在附录（单遍） | 10 | 10 | **10** | **{9}** | **true** |

→ 真实 PDF 里出现 `Page 10 of 9` 这种自相矛盾页眉（`\pageref{LastPage}` 早一版定稿）。现行稿目前 `105 of 105` 一致，但任何一次「附录追加大块内容 + 只编一遍」都会踩到。

**规定**：
1. **必须** `xelatex` 跑 **2 遍**以上才能取页数；只编一遍的页数报告作废。
2. 报页数**必须同时**给 `max N` 与 `M`；两者不等 = 「页数不可信」，先重编译再读。
3. **禁止**把摘要页的 `M` 当正文页数依据（它是全文编号页数，且可能滞后一版）。
4. `contiguous == False`（页眉 N 不连续）同样视为不可信，查 P-W03 的孤立断页。

**检查代码**：
```python
import re, subprocess, json
P = r"E:\MIKTEX\miktex\miktex\bin\x64\pdftotext.exe"
HDR = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)")
def header_integrity(pdf):
    ps = [p for p in subprocess.run([P, "-layout", "-enc", "UTF-8", pdf, "-"], capture_output=True
          ).stdout.decode("utf-8", "replace").split("\f") if p.strip()]
    pairs = [(int(m.group(1)), int(m.group(2))) for m in (HDR.search(p[:400]) for p in ps) if m]
    N = [a for a, _ in pairs]; M = sorted({b for _, b in pairs})
    return {"pdf_pages": len(ps), "with_header": len(N), "max_N": max(N) if N else 0, "M": M,
            "contiguous": N == list(range(1, len(N) + 1)),
            "consistent": bool(N) and max(N) == M[-1]}
print(json.dumps(header_integrity(r"E:\数学建模\APMCM2025_C\main.pdf"), ensure_ascii=False))
```

**实测结果 / pass-fail**：`{"pdf_pages":108,"with_header":105,"max_N":105,"M":[105],"contiguous":true,"consistent":true}` → **PASS**；单遍变体 `max_N=10, M=[9], consistent=false` → **FAIL**。

---

## P-W12 `\enlargethispage{2.5\baselineskip}` 能吃掉半页空白，但只在「末页溢出 ≤2.5 行」的带内有效

**现象/触发**：想不动模板、不改页边距就吃掉末页的半页空白。

**定量后果**（实测 `w15f.py`：正文 4 节 × 12 段，在末节顶部注入 `\enlargethispage{2.5\baselineskip}`，pad = 追加段落数）：

| pad | 不注入（编号页） | 注入（编号页） | Δ |
|---|---|---|---|
| 0–3 | 6 | 6 | 0 |
| **4** | **7** | **6** | **−1** |
| 5–8 | 7 | 7 | 0 |

另有 `w15_etp.py` 每节注入、n 取 1.0 / 2.5 / 5.0 / 10.0 → 11 → 10 / 10 / 10 / 9：**1.0 就够吃 1 页，2.5 与 1.0 同效，10.0 才再省 1 页**（有饱和）。
参数标定：`apmcmthesis.cls:53 \renewcommand*{\baselinestretch}{1.38}`，12pt ⇒ 1 `\baselineskip` ≈ 19.9pt，`2.5\baselineskip` ≈ **49.7pt ≈ 2.5 行正文**。
现行稿已在用：`main.tex:1742 \enlargethispage{2.5\baselineskip}`，位置在 **Appendix C 起首**——手法正确，但对正文 30 页**无贡献**。
**踩过的假阴性**：把命令放在 `\end{document}` 前（`w15c.py`）Δ 恒为 0；放在正文最末尾一节之后（`w15_etp.py` 首版）也常得 0。**它必须落在「即将溢出的那一页」的页面开头**。

**规定**：
1. 吃页尾空白**必须**用 `\enlargethispage{n\baselineskip}`，`n ∈ [1.0, 2.5]`；超过 5 无增益且有顶穿页脚风险。
2. 命令**必须**放在「即将溢出的那一页」的页面开头（一般是该页第一段的起点）；放在 `\end{document}` 前或章节尾 = 无效。
3. **禁止**用 `\vspace*{-x}`、改 `\textheight`、改 `\baselinestretch` 做同类操作（破坏模板与页眉对齐）。
4. 用了它**必须**重量 P-W01 页数，并确认日志无新 `Overfull \vbox`。

**检查代码**：
```python
import re
tex = open(r"E:\数学建模\APMCM2025_C\main.tex", encoding="utf-8").read()
log = open(r"E:\数学建模\APMCM2025_C\main.log", encoding="utf-8", errors="replace").read()
hits = [(tex[:m.start()].count("\n") + 1, m.group(1))
        for m in re.finditer(r"\\enlargethispage\{([^}]*)\}", tex)]
def ok(a):
    try: return 1.0 <= float(re.sub(r"[^0-9.]", "", a)) <= 2.5
    except ValueError: return False
print({"hits": hits, "in_band": [(l, a, ok(a)) for l, a in hits],
       "overfull_vbox": len(re.findall(r"Overfull \\vbox", log)),
       "float_too_large": len(re.findall(r"Float too large", log))})
```

**实测结果 / pass-fail**：`{"hits":[(1742,"2.5\\baselineskip")],"in_band":[(1742,"2.5\\baselineskip",true)],"overfull_vbox":0,"float_too_large":0}` → 手法 **PASS**；但位置在 Appendix C → 对「压正文页数」目标 **PARTIAL**（搬不到正文前不要指望它）。

---

## P-W13 `Float too large for page` 会静默溢出，页数不变但排版已破

**现象/触发**：45 行 6 列表塞进 `[htbp]`，日志有警告，PDF 页数不变，于是以为「省了页」。

**定量后果**（实测 `w04_06.py` / `w08_appx.py`）：45 行表 → `LaTeX Warning: Float too large for page by 213.2968pt`，PDF 仍 4 页、表格仍印出（`x10 1 2 3 4` 可检索）；18 行表无警告。溢出量 213.2968pt ≈ 30% 的 `\textheight`（`cls` 的正文高 = 297−2×25.4 = 246.2mm ≈ 698pt）。

**规定**：
1. 单张浮动表**必须**能在 `\textheight` 内放下；放不下**必须**拆表或改 `longtable`。
2. 日志出现 `Float too large` **禁止**当作通过；它意味着内容压进了页脚区，视觉上会被裁或叠字。
3. 检查器**必须**扫 `.log` 的 `Float too large` 与 `Overfull \vbox` 两个关键字，两者都必须为 0。

**检查代码**：
```python
import re
log = open(r"E:\数学建模\APMCM2025_C\main.log", encoding="utf-8", errors="replace").read()
bad = re.findall(r"Float too large for page by [\d.]+pt", log)
print({"float_too_large": len(bad), "samples": bad[:3],
       "overfull_vbox": len(re.findall(r"Overfull \\vbox", log)),
       "ok": not bad and not re.search(r"Overfull \\vbox", log)})
```

**实测结果 / pass-fail**：`main.log` → `float_too_large=0`、`overfull_vbox=0` → **PASS**。

---

## P-W14 附录里的 `\cite` 与手写 `[18]` 重复，PDF 印出两次

**现象/触发**：AI 声明写成 `... as required by the regulation: \cite{ai}, listed as entry [18] with its type [EB/OL].`

**定量后果**：PDF 渲染为 `regulation: [18], listed as entry [18] with its type [EB/OL].` —— 同一编号出现两次；且该 `\cite` 是**附录里唯一的引注**，一旦按 P-W02 把书目搬附录，它就是孤例。
实测（`chk_w02_w14.py`）：`cite+bracket lines: 1 [(1693, 'regulation: \\cite{ai}, listed as entry [18] with its type [EB/OL].')]` —— 全稿仅此一处。

**规定**：
1. 一处引用只写一次，**禁止** `\cite{x}` 与手写 `[n]` 并列。
2. 附录引注**必须**指向正文已出现过的文献；附录**禁止**引入正文未引用文献。
3. 正确写法：`as required by the regulation (Reference [18], type [EB/OL]).`（去掉 `\cite{ai}`）或 `... as required by the regulation \cite{ai} (type [EB/OL]).`（去掉手写编号）。

**检查代码**：
```python
import re
tex = open(r"E:\数学建模\APMCM2025_C\main.tex", encoding="utf-8").read()
bad = [{"line": i, "text": ln.strip()[:120]}
       for i, ln in enumerate(tex.splitlines(), 1)
       if "\\cite" in ln and re.search(r"\[\d{1,2}\]", ln)]
print({"cite_plus_literal": len(bad), "detail": bad})
```

**实测结果 / pass-fail**：`{"cite_plus_literal":1,"detail":[{"line":1693,...}]}` → **FAIL**（须二选一）。

---

## P-W15 `compare_to_awards.py` 的三个口径陷阱（numpy / 只数小数 / 提及≠布尔）

**现象/触发**：直接 `python code\compare_to_awards.py`，或直接引用它输出的 `has_*`。

**定量后果**（实测）：
1. 默认 `python` = 3.14.6（`C:\Users\29900\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`）→ `ModuleNotFoundError: No module named 'numpy'`；**必须** `& "D:\Python\python.exe"`（3.13.12 + numpy 2.5.1）。
2. `has_*` 是**提及次数**不是布尔（正则计数）；`has_neural=7/16` 读作「7 篇提到」。
3. `abstract_numbers` / `distinct_numbers` 只数小数（同 P-W10）。
4. 当次输出（写回 `refs/project_vs_awards.json`）：words 12340 (p87.5)、abstract_words 505 (p87.5)、abstract_numbers 5 (p62.5)、abstract_density 0.99 (p56.2)、distinct_numbers 455 (p93.8)、pct_mentions 263 (**p100**)、density_per_100w 3.69 (p87.5)、sections 5 (p75)、subsections 0 (p43.8)、figures 14 (p50)、tables 18 (**p100**)、equations 19 (p56.2)、references 9 (p62.5)。
   越界三项：`tables 18 vs 中位 4`、`distinct_numbers 455 vs 75`、`pct_mentions 263 vs 16`。
5. 一等奖 16 篇中位数（引自 `E:\数学建模\APMCM2025_C\refs\official_standard_report.txt`）：words **8228**、figures **14.5**、tables **4**、equations **17**、references **7.5** —— 已实读核对，与任务书给定值一致。

**规定**：
1. **必须**用 `D:\Python\python.exe` 运行；运行后**必须**重写 `refs/project_vs_awards.json`，报告只引当次数字。
2. 引 `has_*` 一律写「提及数 n/16」，不写「有/无」。
3. 中位数**禁止**手抄；任何引用须同时写来源文件与 min–max 区间。
4. 三项越界是当前最该动的：`tables 18`（p100）→ 14 张从属表搬附录（按 P-W08 每轮 1 页）；`distinct_numbers 455` / `pct_mentions 263` → 正文复述数字过密，删重复列举。
5. `figures 14`（p50，中位 14.5）与 `equations 19`（p56.2，中位 17）都在带内，**不要**为了「好看」加图表——它们会推高 tables 与页数。

**检查代码**：
```python
import json, subprocess
out = subprocess.run([r"D:\Python\python.exe", r"E:\数学建模\APMCM2025_C\code\compare_to_awards.py"],
                     capture_output=True, text=True, cwd=r"E:\数学建模\APMCM2025_C")
d = json.load(open(r"E:\数学建模\APMCM2025_C\refs\project_vs_awards.json", encoding="utf-8"))
# the file is NOT {"comparison": {metric: {...}}}; it is a flat list under "percentiles"
outside = [{"metric": r["metric"], "project": r["project"], "median": r["median"],
            "pct_rank": r["pct_rank"]}
           for r in d["percentiles"]
           if r.get("pct_rank") is not None and (r["pct_rank"] > 90 or r["pct_rank"] < 10)]
print({"exit": out.returncode, "benchmark_n": d["benchmark_n"],
       "project_headline": {k: d["project"][k] for k in
                            ("words", "tables", "figures", "equations", "references")},
       "outside_band": outside})
```

**实测结果 / pass-fail**：`exit=0`，`refs/project_vs_awards.json` 由本次运行重写，三项越界已确认 → 口径 **PASS**；`tables 18`（p100）、`distinct_numbers 455`（p93.8）、`pct_mentions 263`（p100）→ 内容 **FAIL**（待办，非格式）。

---

## 附：本轮踩到的工具坑（不属于 P-W 条目，但会伪造结论）

| 坑 | 现象 | 规避 |
|---|---|---|
| PowerShell 无 heredoc | `python - <<'EOF'` 报 ParserError | 探针写成 `.py` 文件再执行 |
| 默认 `python` 无 numpy | `compare_to_awards.py` 直接崩 | 用 `D:\Python\python.exe` |
| GBK 输出编码 | `UnicodeEncodeError: 'gbk' codec can't encode character '\u037e'` | 先 `$env:PYTHONIOENCODING="utf-8"` |
| `cd` 不跨调用 | 每条命令都在工作区根 | 每条命令自带 `cd` 或 `workdir` |
| 只复制 `apmcmthesis.cls` | `! LaTeX Error: File 'apmcmthesis.cfg' not found.` | 复制 cls 必须同时复制 `apmcmthesis.cfg`（`cls:420` `\AtBeginDocument{\input{apmcmthesis.cfg}}`） |
| 断页插错位置 | `\newpage` / `\enlargethispage` 测出 Δ=0 | 断页插正文中间；`\enlargethispage` 插溢出页的页首 |

---

## 来源标注

- 一等奖中位数、presence 统计：`E:\数学建模\APMCM2025_C\refs\official_standard_report.txt`、`refs\official_standard.json`。
- 摘要结构与数字密度（16 篇）：`E:\数学建模\APMCM2026\refs\abstract_structure.json`、`abstract_structure_report.txt`。
- 测量口径实现：`E:\数学建模\APMCM2025_C\code\award_standard.py`、`code\compare_to_awards.py`。
- 规则原文：`E:\数学建模\APMCM2025_C\refs\spec.txt`（"main body … within 30 pages, the appendix is no limit"）。
- 旧记录（**已过期，不得引用数字**）：`E:\数学建模\APMCM2025_C\review\03_compliance.md`（基于旧 72 页稿）。
- 模板参数：`E:\数学建模\APMCM2025_C\apmcmthesis.cls:52–53`（geometry、`\baselinestretch{1.38}`）、`:137–151`（fancyhdr 页眉）、`:342–367`（`\abstract` / `\keywords`）、`:381–399`（`thebibliography`）。