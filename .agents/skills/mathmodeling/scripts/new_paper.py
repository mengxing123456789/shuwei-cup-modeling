#!/usr/bin/env python
"""新建一篇论文骨架：把 templates/PAPER-TEMPLATE.md 的章序列落成可编译的 main.tex。

用法：
    E:\\Mini\\envs\\mathmodel\\python.exe scripts\\new_paper.py <目录> [--type A|B|C|D|E]

生成：
    <目录>/main.tex            章序列已排好，填空项是 <<…>>
    <目录>/refs/               official_standard.json + award_text/ 的拷贝（基准带要用）
    <目录>/figures/ tables/ data/ logs/ code/ review/ problem/
    <目录>/NO_PEEK.md          禁止看优秀论文的清单与判据（练习赛用；正式赛写"无"也要留文件）
    <目录>/BUILD.md            从空目录到可提交件的命令序列 + C1..C12 自检表
    <目录>/review/README.md    评审小队往这里写 00-metrics.md / 01..09 / 00-plan.md
    <目录>/code/check_no_peek.py   禁区扫描（带负对照用法）
    <目录>/code/verify_numbers.py  对账骨架（含区间断言 RANGES 的半成品）

设计取舍：不抄官方 .cls（它有 \\CJK 未定义的 bug），而是直接 \\input 工作区里已编译通过的
apmcmthesis.cls；没有就用 article + 自定义页眉，保证一定编译得过。
空目录当论文交上去是常见的输法——所以骨架不只是 main.tex，还包含"会被评审要的东西"。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
WS = SKILL.parents[2]          # E:\数学建模
DONOR = WS / "APMCM2025_C"     # 已编译通过的真实论文，复用它的 cls 与 refs

# 数维杯（swmcmthesis）官方模板：不复制到技能里，直接从赛前下载的目录取，
# 这样官方更新模板时不用改代码。找不到就只在生成时告警，不阻断。
SHUWEI_DIRS = (
    WS / "数维杯" / "00_官网与规则" / "latex_template" /
    "2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）LaTeX模版",
)


def swmcm_donor() -> Path | None:
    """返回含 swmcmthesis.cls 的目录；找不到返回 None（只在数维杯模式下用）。"""
    for d in SHUWEI_DIRS:
        if (d / "swmcmthesis.cls").exists():
            return d
    for p in (WS / "数维杯").rglob("swmcmthesis.cls"):
        return p.parent
    return None

NO_PEEK_TEMPLATE = """# 不看优秀论文（练习赛用）

本目录里的任何一个决定，都不许来自"获奖论文怎么写的"。允许的来源只有：

- 官方题面、官方附件数据、官方格式规范（`APMCM-PROBLEMS\\_rules_text\\`）
- 公开教材/文献里的方法与常数（引用要写进参考文献）
- 自己的工作区规定（`RULES.md`）与模板

## 判据

`code/check_no_peek.py` 扫本目录（跳过 `problem/`、`data/`、`refs/`）里的路径词与行为词。
负对照：故意在一行里写下禁区路径，必须 FAIL；删掉后必须 PASS —— 没做过负对照的判据不算判据。

## refs/ 里有什么

只有 `official_standard.json`（16 篇一等奖的**分布数字**：词数、图数、章节数……）。
**没有** `award_text/` —— 那是一等奖正文，把答案放进论文目录会让"不看"变成空话。
要重算基准，回 `E:\数学建模\APMCM2025_C\refs\` 跑，不要在这个目录里建它。

## 为什么

练习赛的价值在于"我能不能独立做出来"。看了获奖论文，练的就变成"抄得像不像"。
选年份时优先选**语料里没有获奖论文**的年份（2026 赛前：2015–2020 全都没有），
这样"不看"是结构上不可能作弊，不靠自觉。
"""

BUILD_TEMPLATE = """# BUILD：从空目录到可提交件

## 0. 把原件放进来（只读）

```
problem/     题面 PDF + 附件（xlsx/csv/trc/图片）。官方原件只读，要清洗就另存到 data/。
refs/        已经带了 official_standard.json 与 award_text/：baseline 要用，正文不许引用。
```

## 1. 数据层（只做一次）

```
<interp> code/fetch_*.py          # 抓数就写台账：url + fetched_at + sha256
<interp> code/features.py         # 产物进 data/*.json，不打印到屏幕
```

## 2. 建模与对账（每次改代码都要重跑）

```
<interp> code/model_a.py ... code/model_z.py
<interp> code/make_tables.py      # 表由 JSON 生成，不手抄
<interp> code/make_figures.py     # 图内 >=3 字符的字号必须 >= 6 pt
<interp> code/verify_numbers.py   # 印出来的数必须绑到 JSON 键
```

## 3. 编排

```
<interp> scripts/run_review.py metrics <本目录>    # 生成 review/00-metrics.md（口径基线）
xelatex main.tex   （两次）
<interp> scripts/gauntlet_check.py <本目录>        # R 系列
<interp> scripts/review_check.py  <本目录>         # C1..C12
```

## 4. 提交前自检（C1–C12 里可机器判的部分）

| 项 | 命令 | 期望 |
|---|---|---|
| 页码只有队号+页码 | `review_check.py` C5 | 每页都有，且不含身份信息 |
| 正文无中文（附录不算） | C7 | `body cjk=0` |
| 正文 <= 30 页 | `gauntlet_check.py` R-V01 | `body<=30` |
| 附录列全源码 | C9 + `code/*.py` 实数 | listing 数 >= 脚本数 |
| 队号两层 | C11 | 字形 0 命中 **且** 语义 0 命中 |
| 文件名 | 手工 | `A<队号>.pdf` |
| 摘要页第 1、目录第 2 | C4 | 两页都对 |
| 参考文献类型标记 | C8 | `[M]/[J]/...` 数 >= 条目数 |
"""

REVIEW_README = """# review/：评审产物放这里

由 `scripts/run_review.py` 驱动，文件名的编号是固定的（下游靠文件名配对）：

| 文件 | 谁写 | 内容 |
|---|---|---|
| `00-metrics.md` | **脚本**（不是人） | 四条机器判据的原始输出 + 被测件 mtime/sha256。审读员的唯一口径基线 |
| `01-compliance.md` | 合规审查员 | C1..C12 逐条，任何 FAIL 都是废稿级 |
| `02-structure.md` | 论文结构审读 | 族属、必备章、每问闭环、页数预算 |
| `03-abstract.md` | 摘要与表达审读 | 四段式 + 数字配额 + 可替换英文改写 |
| `04-fit.md` | 题目契合度审读 | 题面每条要求 -> 论文兑现位置 -> 兑现程度 |
| `05-model.md` | 模型与检验审读 | 口径/稳定性/边界/敏感性/结论强度 |
| `06-code.md` | 数据与代码审读 | 台账、可重跑性、verify 覆盖率、产物新鲜度 |
| `07-figures.md` | 图表审读 | 六范式与误用 |
| `08-innovation.md` | 创新性评估 | 四类创新 + 可检验命题 |
| `09-numbers.md` | 数字对账员 | 抽 10 个数复算 + 结构性空转清单 |
| `00-plan.md` | 改进方案总编 | 四级排序的可执行清单 + 档位判断 |

**规矩**：报告是快照（R-V11）。任何"缺 X/少 Y"的结论落地前，用当前树重量一次，两列都写。
"""

CHECK_NO_PEEK = '''#!/usr/bin/env python
"""扫本目录，禁止出现指向获奖论文/优秀论文的路径或行为（练习赛用）。

用法：
    python code/check_no_peek.py [目录]        # 默认本文件的上一级
负对照（必须先做一次）：
    在本目录随便写一个 .py，里面放一行 src = r"...\\\\_award_text\\\\x.txt"
    -> 必须 FAIL 并指出行号；删掉后必须 PASS。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# 路径词：出现即说明引用了禁区语料
PATH_WORDS = ["_award_text", "award_pdfs", "_award_outline", "APMCM2025_C",
              "allpapers", "excellent", "prize_lists", "优秀论文", "一等奖论文"]
# 行为词：出现即说明在描述"抄哪篇"
# 行为词只收"指向某个获奖答案"的短语。裸的"照抄"会命中"别照抄键名"这类正常句子（P11 实测）。
ACT_WORDS = ["获奖论文怎么", "参考一等奖", "照抄一等奖", "照抄获奖", "仿写一等奖", "copy the award"]
EXT = {".py", ".md", ".tex", ".json", ".txt", ".log", ".csv", ".m"}
SKIP = {"problem", "data", "refs", "annex_A", "review", ".git", "__pycache__"}
# 目录级禁区：refs/award_text 是一等奖正文，练习赛里出现就等于把答案放在了旁边。
# 只在文件级扫会漏掉它（refs 本身要跳过，因为 official_standard.json 就在那儿）。
DIR_BAN = ["refs/award_text", "award_text"]
# 这些文件**本来就要写出禁区路径**（否则没法告诉人哪些不能碰）。判据若扫自己必然 FAIL，
# 规则文档与判据本身必须豁免，否则负对照永远做不出来（P11 实测：豁免前 8 命中）。
EXEMPT = {"NO_PEEK.md", "code/check_no_peek.py"}

PAT = re.compile("|".join(map(re.escape, PATH_WORDS)), re.I)
ACT = re.compile("|".join(map(re.escape, ACT_WORDS)), re.I)


def scan(root: Path) -> list[str]:
    hits: list[str] = []
    for bad in DIR_BAN:
        d = root / bad
        if d.exists() and d.is_dir():
            hits.append(f"{bad}/ (directory: 一等奖正文在这里，练习赛必须删除)")
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXT:
            continue
        rel = p.relative_to(root).as_posix()
        if set(p.relative_to(root).parts) & SKIP or rel in EXEMPT:
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if PAT.search(line) or ACT.search(line):
                    hits.append(f"{p.relative_to(root)}:{i}")
        except OSError:
            continue
    return hits


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    hits = scan(root)
    for h in hits:
        print("FAIL", h)
    print(f"scanned {root}  forbidden hits {len(hits)}")
    print("VERDICT:", "PASS" if not hits else "FAIL")
    return 0 if not hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

VERIFY_TEMPLATE = '''#!/usr/bin/env python
"""对账骨架：正文里印出来的每个数，都要能回到 data/*.json 里的一个键。

这里只放**结构**，没有 claim —— 空着也必须能跑通并打印 0 claims / PASS，
这样"没填"不会被误读成"没问题"（真论文里，claims 为 0 等于没对上账，评审会判 FAIL）。

三种断言写法：
    add("键名", json里的值, "正文里印的字符串")           # 逐点绑，容差按印刷小数位
    RANGES = [(名字, (实测min, 实测max), ("印的下界", "印的上界"))]   # 会漂的量绑区间
    # 派生量在源码里算：1 - auc、1 - ci[1]、sum(sorted(w)[:5])*100
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "main.tex"


def _tol(expected: float, needle: str) -> float:
    """容差按**印刷的小数位**定：印 3.1 就容 0.05，印 96.4 就容 0.964。"""
    dp = len(needle.split(".")[1]) if "." in needle else 0
    return max(0.011, abs(expected) * 0.01, 0.5000001 * 10 ** (-dp))


def main() -> int:
    claims: list[tuple[str, float, str]] = []
    fails: list[tuple] = []
    tex = TEX.read_text(encoding="utf-8")

    def add(path: str, value: float, needle: str) -> None:
        claims.append((path, value, needle))

    # ---- 在这里填 claim（示例被注释掉，别照抄键名） ----
    # j = json.loads((ROOT / "data" / "model.json").read_text(encoding="utf-8"))
    # add("model.auc", j["auc"], "0.705")

    RANGES: list[tuple[str, tuple[float, float], tuple[str, str]]] = [
        # ("timing.end_band", (7.55, 7.71), ("7.4", "10.5")),
    ]

    print(f"{len(claims)} claims, {len(RANGES)} ranges (both empty = nothing is bound yet)")
    for path, value, needle in claims:
        if not re.search(r"(?<![\\d.])" + re.escape(needle) + r"(?![\\d])", tex):
            fails.append((path, value, needle, "not printed"))
    for path, (lo_m, hi_m), (lo_p, hi_p) in RANGES:
        if float(lo_p) > lo_m + 1e-9 or float(hi_p) < hi_m - 1e-9:
            fails.append((path, (lo_m, hi_m), (lo_p, hi_p), "printed band too narrow"))
    for f in fails:
        print("  FAIL", f)
    print("PASS" if not fails else "FAIL")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

# 每族的章序列。与 templates/PAPER-TEMPLATE.md 一一对应，改一处要改两处。
SECTIONS = {
    "A": [
        ("Question 1: <<What it does>>", [
            "Image Pre-processing", "<<Discriminant>> Modeling", "Solution and Results", "Test Analysis", "Short Summary"]),
        ("Question 2: <<What it does>>", [
            "Pre-processing", "Model", "Solution and Results", "Test Analysis", "Short Summary"]),
    ],
    "B": [
        ("Question 1: <<What it does>>", [
            "Mechanism and Assumptions", "Mathematical Model", "Solution", "Validation and Sensitivity"]),
        ("Question 2: <<What it does>>", [
            "Mechanism and Assumptions", "Mathematical Model", "Solution", "Validation and Sensitivity"]),
    ],
    "C": [
        ("Question 1: <<What it does>>", [
            "Data Insight", "Modeling and Solution", "Robustness and Conclusion"]),
        ("Question 2: <<What it does>>", [
            "Data Insight", "Modeling and Solution", "Robustness and Conclusion"]),
    ],
    "D": [
        ("Basic Model: <<classic model>>", [
            "Objective Function and Modeling Principles", "Constraints", "Solution", "Validation"]),
        ("Extended Model: <<realistic constraints>>", [
            "Objective Function", "Constraints", "Solution", "Validation"]),
        ("Scale-Reduction Model", ["Reduction Strategy", "Solution", "Validation", "Comparison of Models"]),
    ],
    "E": [
        ("<<Time Series Model>>", [
            "Model Form", "Stationarity Test", "White Noise Test", "Estimation and Validation"]),
    ],
}

HEAD = r"""\documentclass[<<options>>]{apmcmthesis}
\tihao{<<A>>}
\baominghao{apmcm2699001}   % <-- 队号，提交前必须填；必须 apmcm+数字，否则页眉正则配不上
\begin{document}
% 官方格式（2017-2023 每年 Essay format p.67 起；2026 扫描件 p3/p4 同义）：
%   第 1 页 = Summary Sheet（摘要页），第 2 页 = Contents，第 3 页起正文。
% 英文赛项**没有** Control Sheet（承诺书是中文赛项那一套）。
% 实测坑（2018A 练习稿）：HEAD 原来先 \makecontrolsheet 再 \maketitle，承诺书占第 1 页，
% review_check 的 C4「第一页必须是摘要页」直接判红。而且 \makecontrolsheet 会把 \maketitle
% \let 成 relax，所以删一行不够 —— 两行都要去掉，直接从 \begin{abstract} 起。
\thispagestyle{empty}
\begin{abstract}
\textbf{Background and Task} <<one sentence with a number>>. This paper addresses
<<N>> problems: <<task 1>>; <<task 2>>; <<task 3>>. <<N>> models are developed.

\textbf{Modeling Framework} <<Q1 model>>, based on which <<Q2 model>>, and extending
to <<Q3 model>>.

\textbf{Results per Question} <<Q1 number + conclusion>>; <<Q2 number + conclusion>>;
<<Q3 number + conclusion>>.

\textbf{Validation and Limitation} <<validation 1 with number>>; <<validation 2 with
number>>. The main limitation is that <<one concrete limitation with a number>>.

\keywords{<<model names in the order they appear above>>}
\end{abstract}

\newpage
\tableofcontents
\newpage
% 必须是 mainmatterstyle：它才是 \fancyhead 里带 "Team # ... Page n of N" 的那个。
% 用 plain 会丢掉页眉，gauntlet 的 R-V02 直接判 body=0。
\pagestyle{mainmatterstyle}
\setcounter{page}{1}
"""

HEAD_SWMCM = r"""\documentclass{swmcmthesis}
% 数维杯官方模板（2026 秋季赛）。与 apmcmthesis 的三处接口差异：
%   1) 摘要用 \abstract{...} 宏，不是 \begin{abstract}...\end{abstract}；
%   2) 选题用 \zubie{ABCD}，不是 \tihao{A}；
%   3) 页眉两行（队号一行、页码一行），review_bench.HEADER_RE 已同时认两种排版。
% 宏参数里不要出现空行（空行会被当 \par，参数没加 \long 时直接报错），换行用 \\。
\title{<<title>>}
\baominghao{<<TEAM>>}
\zubie{<<A>>}
\abstract{
\textbf{Background and Task} <<one sentence with a number>>. This paper addresses <<N>> problems: <<task 1>>; <<task 2>>; <<task 3>>. <<N>> models are developed. \\
\textbf{Modeling Framework} <<Q1 model>>, based on which <<Q2 model>>, and extending to <<Q3 model>>. \\
\textbf{Results per Question} <<Q1 number + conclusion>>; <<Q2 number + conclusion>>; <<Q3 number + conclusion>>. \\
\textbf{Validation and Limitation} <<validation 1 with number>>; <<validation 2 with number>>. The main limitation is that <<one concrete limitation with a number>>.
}
\keywords{<<model names in the order they appear above>>}
\date{2026}
\begin{document}
% 第 1 页 = 标题 + 摘要 + 关键词（\maketitle 生成），第 2 页 = 目录，第 3 页起正文。
\maketitle
\tableofcontents
\newpage
% 必须重置：本类默认不重置，正文会从物理第 3 页起编号（实测 "Page 3 of 5"），
% 于是 body_pages 判成 0、R-V02 报跳号。重置后与 apmcmthesis 同语义（Page 1 of N 指正文页）。
\setcounter{page}{1}
"""

TAIL = r"""\section{Strengths and Weaknesses}
\subsection{Strengths}
\begin{itemize}
  \item <<strength 1, points to a result>>
  \item <<strength 2>>
  \item <<strength 3>>
\end{itemize}
\subsection{Weaknesses}
\begin{itemize}
  \item <<weakness 1, with a number>>
  \item <<weakness 2, with a number>>
  \item <<weakness 3, with a number>>
\end{itemize}

\begin{thebibliography}{99}
\bibitem{ref1} <<author>>. <<title>>[J]. <<journal>>, <<year>>, <<vol>>(<<no>>): <<pages>>.
\bibitem{ref2} <<author>>. <<book>>[M]. <<place>>: <<publisher>>, <<year>>.
\bibitem{ref3} <<institution>>. <<report>>[R]. <<year>>.
\bibitem{ref4} <<institution>>. <<dataset>>[DB/OL]. <<url>>, accessed <<YYYY-MM-DD>>.
\end{thebibliography}

\appendix
% 必须用 \section{Appendix A: Code}：apmcmthesis.cls 里 \section 被改成罗马数字（I. ），
% \appendix 不会把它变成 "Appendix A"。而 gauntlet 认正文首页的锚点正是字面 "Appendix A"。
\section{Appendix A: Code}
% 先把 code/main.py 写出来，再把下一行取消注释。模板默认不启用：
% 缺文件时 listings 抛 "! Package Listings Error: File `code/main(.py)' not found"
% + "! Emergency stop."，exit=1，且 lastpage 跳号让页眉变成 "Page N of ??"。
%\lstinputlisting{code/main.py}
<<paste the full source of every script that produced a number, one appendix per script>>
\end{document}
"""


def build(dest: Path, ptype: str, cls: str = "apmcm", team: str = "") -> str:
    """生成 main.tex。cls=swmcm 时换用数维杯官方模板的骨架（摘要用宏参数）。"""
    secs = SECTIONS[ptype]
    head = HEAD
    if cls == "swmcm":
        head = (HEAD_SWMCM
                .replace("<<TEAM>>", team or "SWBMCM2600001")
                .replace("<<A>>", ptype))
    body = [r"\section{Introduction}",
            r"\subsection{Background}", "<<why this matters now, one paragraph>>",
            r"\subsection{Restatement of the Problems}", "<<restate each question in your own variables>>",
            r"\subsection{Our Work}", "<<what this paper delivers, one line per question>>",
            r"\section{Problem Analysis}", "<<the mechanism, the key tension, what you simplify and why>>",
            r"\section{Assumptions and Justifications}",
            r"\begin{enumerate}",
            r"  \item <<assumption>> --- <<why>>; used by Section~<<x>>.",
            r"  \item <<assumption>> --- <<why>>; used by Section~<<x>>.",
            r"\end{enumerate}",
            r"\section{Notations}",
            r"\begin{table}[htbp]\centering\caption{Notations}\label{tab:notation}",
            r"\begin{tabular}{@{}lll@{}}\toprule Symbol & Meaning & Unit \\ \midrule",
            r"$<<sym>>$ & <<meaning>> & <<unit>> \\ \bottomrule\end{tabular}\end{table}"]

    if ptype == "C":
        body += [r"\section{Data Description and Preprocessing}",
                 r"\subsection{Sources and Acquisition}",
                 r"<<institution, indicator, period, URL, access date --- one line per source>>",
                 r"\subsection{Cleaning}",
                 r"<<missing rate, outliers, unit conversion, post-processing row count>>",
                 r"\subsection{Rationality and Consistency}",
                 r"<<cross-check two independent sources, report the gap in per cent>>"]

    for title, subs in secs:
        body.append(r"\section{" + title + "}")
        for s in subs:
            body.append(r"\subsection{" + s + "}")
            body.append("<<fill>>")
    body.append(r"\section{Sensitivity Analysis and Error Analysis}")
    body.append("<<perturbation / resampling / variance decomposition; report the unfavourable half>>")
    body.append(r"\section{Conclusion}")
    body.append("<<per-question summary, each pointing at a number>>")
    return "\n".join([head] + body + [TAIL])


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    dest = Path(sys.argv[1]).resolve()
    ptype = "C"
    if "--type" in sys.argv:
        ptype = sys.argv[sys.argv.index("--type") + 1].upper()
    cls = "apmcm"
    if "--cls" in sys.argv:
        cls = sys.argv[sys.argv.index("--cls") + 1].lower()
    if cls not in ("apmcm", "swmcm"):
        print("--cls must be apmcm or swmcm")
        return 2
    team = ""
    if "--team" in sys.argv:
        team = sys.argv[sys.argv.index("--team") + 1]
    if ptype not in SECTIONS:
        print(f"--type must be one of {sorted(SECTIONS)}")
        return 2

    for d in ("code", "data", "figures", "tables", "logs", "refs", "review", "problem"):
        (dest / d).mkdir(parents=True, exist_ok=True)

    # 骨架不只有 main.tex：评审真正会要的东西先占位，空目录也能跑通。
    for rel, body in (
        ("NO_PEEK.md", NO_PEEK_TEMPLATE),
        ("BUILD.md", BUILD_TEMPLATE),
        ("review/README.md", REVIEW_README),
        ("code/check_no_peek.py", CHECK_NO_PEEK),
        ("code/verify_numbers.py", VERIFY_TEMPLATE),
    ):
        p = dest / rel
        if not p.exists():
            p.write_text(body, encoding="utf-8")

    # 复用 donor 的 cls：它已经在真实论文上编译通过两次。
    if cls == "swmcm":
        donor_dir = swmcm_donor()
        names = ("swmcmthesis.cls", "swmcmthesis.cfg")
        if donor_dir is None:
            print("WARNING: 找不到 swmcmthesis.cls（数维杯官方模板目录）；"
                  "把 2026 秋季赛的 cls/cfg 放进论文目录后再编译")
        else:
            for name in names:
                src = donor_dir / name
                if src.exists():
                    shutil.copy2(src, dest / name)
    else:
        for name in ("apmcmthesis.cls", "apmcmthesis.cfg"):
            src = DONOR / name
            if src.exists():
                shutil.copy2(src, dest / name)
            else:
                print(f"WARNING: {src} missing; main.tex will not compile until the cls is supplied")

    tex = dest / "main.tex"
    tex.write_text(build(dest, ptype, cls=cls, team=team), encoding="utf-8")

    # 基准带只需要**分布数字**（official_standard.json）。**不拷 award_text/**：
    # 那是 22 篇一等奖的正文，把答案放进论文目录会让"练习赛不看优秀论文"变成不可执行
    # （而且 check_no_peek.py 跳过 refs/，扫描也抓不到）。重算基准请回 donor 目录跑。
    # 数维杯用数维杯自己的基准（`数维杯/build_standard.py` 由 48 篇优秀论文重建），
    # 只有它还不在时才回落亚太杯那份——两种赛事的词数/图数分布差别很大。
    if cls == "swmcm":
        src = WS / "数维杯" / "refs" / "official_standard.json"
        if not src.exists():
            src = DONOR / "refs" / "official_standard.json"
    else:
        src = DONOR / "refs" / "official_standard.json"
    if src.exists() and not (dest / "refs" / src.name).exists():
        shutil.copy2(src, dest / "refs" / src.name)
    if (dest / "refs" / "award_text").exists():
        print("WARNING: refs/award_text/ 存在 —— 练习赛请删掉，它是一等奖正文（答案）")

    blanks = tex.read_text(encoding="utf-8").count("<<")
    print(f"created {tex}  type={ptype}  cls={cls}  sections={len(SECTIONS[ptype]) + 5}  blanks={blanks}")
    print("next: fill the <<...>> slots, then run scripts\\gauntlet_check.py")
    if cls == "swmcm":
        print("     数维杯：\\baominghao 填真实队号（SWBMCM+数字），\\zubie 填选题字母")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


