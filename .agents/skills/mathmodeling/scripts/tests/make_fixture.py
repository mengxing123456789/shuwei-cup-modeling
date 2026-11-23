"""测试夹具：一个 70 行、故意留三条缺陷的 main.tex + 空白 PDF。

只用于验证 crew 的"落地判据"和 verify_numbers / gauntlet 的报错路径，
不是交付物。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

WS = Path(r"E:\数学建模\_fixture")
TEX = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{longtable}\usepackage{booktabs}
\usepackage{hyperref}\usepackage{fancyhdr}
\pagestyle{fancy}\fancyhf{}
\lhead{\small Team \#\ APMCM26XXXXX}\rhead{\small Page \thepage\ of \pageref{LastPage}}
\usepackage{lastpage}
\begin{document}
\section{Summary}
We model the thing. The score rises from 0.0132 to 0.9979 over ten years, a gain of 0.9847.
The weight of energy is 0.2184 and the top year survives in 63.6 per cent of resamples.
\section{Introduction}
The problem asks for a forecast.
\section{Question 1}
The elasticity is $\sigma=6.5$ and the tariff is 15\%.
\begin{table}[htbp]\centering\caption{Cost decomposition}\label{tab:cost}
\begin{tabular}{@{}lr@{}}\toprule Item & A \\ \midrule
Revenue & 0.00 & -0.87 & -0.05 \\ \bottomrule\end{tabular}\end{table}
The welfare change is $-0.1750$ billion and the total volume is 105.9379 million tonnes.
\section{Conclusion}
We conclude with a dangling reference \cite{nope} and a hand-written marker [7].
\section*{Appendix A: Code}
\noindent listing omitted.
\end{document}
"""


def main() -> int:
    WS.mkdir(parents=True, exist_ok=True)
    (WS / "main.tex").write_text(TEX, encoding="utf-8")
    for d in ("code", "data", "figures", "tables", "logs", "refs", "out"):
        (WS / d).mkdir(exist_ok=True)
    # 真编一遍：表格列数不符会 exit 1，这正是我们要的"已知缺陷"
    log = WS / "logs" / "fixture.log"
    cmd = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
    for _ in range(2):
        proc = subprocess.run(cmd, cwd=WS, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        log.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    pdf = WS / "main.pdf"
    print(f"fixture built: tex={len(TEX)}B pdf_exists={pdf.exists()} "
          f"pdf_bytes={pdf.stat().st_size if pdf.exists() else 0} exit={proc.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())