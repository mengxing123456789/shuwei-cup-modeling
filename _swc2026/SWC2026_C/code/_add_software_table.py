# -*- coding: utf-8 -*-
"""Insert the software-version table required by item 1(6) of the format spec.

The spec asks the appendix to state the software actually used.  The paper named Python
and xelatex in prose but never listed versions, which a reviewer can check in a minute.
This table is generated from the versions measured on the team machine, not from memory.
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.tex"

ANCHOR = r"\texttt{code/fill\_numbers.py} from the JSON files listed beside each table."

TABLE = r"""

% numerals-ok: begin
\begin{longtable}{p{0.28\textwidth}p{0.26\textwidth}p{0.38\textwidth}}
\caption{Software used, with the version actually executed on the team machine.}
\label{tab:software}\\
\toprule
Package & Version & Used for \\
\midrule
\endfirsthead
\toprule
Package & Version & Used for \\
\midrule
\endhead
\bottomrule
\endfoot
Python & 3.11.18 & every script in \texttt{code/} \\
NumPy & 2.4.6 & arrays and the vectorised scheduler \\
SciPy & 1.17.1 & peak finding, quadrature, sparse algebra \\
pandas & 3.1.1 & the record and segment tables \\
scikit-learn & 1.9.1 & ridge, logistic, standardisation, the splits \\
PyTorch & 2.14.1 with CUDA 12.6 & the two learned networks, on one RTX 4060 Laptop \\
LightGBM & 4.7.0 & the gradient-boosted reliability detector \\
Matplotlib & 3.11.2 & every figure, at 400 dpi \\
PyMuPDF & 2.1 & the page and font measurements behind the audits \\
MiKTeX XeTeX & 4.16 (MiKTeX 25.12) & this document \\
\bottomrule
\end{longtable}
% numerals-ok: end"""


def main():
    apply = "--apply" in sys.argv
    text = io.open(MAIN, encoding="utf-8").read()
    n = text.count(ANCHOR)
    print("anchor hits:", n)
    if n != 1:
        print("ABORT: anchor must appear exactly once")
        return 1
    if "tab:software" in text:
        print("already present")
        return 0
    new = text.replace(ANCHOR, ANCHOR + TABLE)
    print("bytes %d -> %d" % (len(text), len(new)))
    if not apply:
        print("dry run; pass --apply")
        return 0
    io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new)
    print("written", MAIN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
