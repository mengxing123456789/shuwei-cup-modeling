"""Pass 5: restore the literal appendix letter and shave the three lines that spill."""
import io
import os

TEX = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"

PAIRS = [
    # the reintroduced \ref{app:calib} renders as a section number, not a letter
    (r"""Appendix~\ref{app:calib} scores us against marks declared before the experiments
and names the three that were not met.""",
     r"""Appendix~D scores us against marks declared before the experiments and names the
three that were not met.""", "appendix-letter"),
    (r"""\emph{IEEE
Transactions on Systems Science and Cybernetics}, 2, 22--26.""",
     r"""\emph{IEEE Trans.\ Syst.\ Sci.\ Cybern.}, 2, 22--26.""", "howard-abbrev"),
    (r"""\bibitem{deepseek} DeepSeek Harness, command-line coding agent, DeepSeek, used
18--20 November 2026.""",
     r"""\bibitem{deepseek} DeepSeek Harness, CLI coding agent, DeepSeek, 18--20 Nov 2026.""",
     "deepseek-short"),
    (r"""on-time rate over EDF in both capacity-constrained cases, while the truth is worth only
three to four points once the rule is fixed. Each negative result arrives with the
condition that would reverse it.""",
     r"""on-time rate over EDF in both capacity-constrained cases, while the truth is worth only
three to four points once the rule is fixed, and each negative result arrives with the
condition that would reverse it.""", "conclusion3"),
]


def main():
    t = io.open(TEX, encoding="utf-8").read()
    for old, new, tag in PAIRS:
        assert t.count(old) == 1, (tag, t.count(old))
        t = t.replace(old, new)
    io.open(TEX, "w", encoding="utf-8", newline="\n").write(t)
    print("pass 5 done; bytes", os.path.getsize(TEX))


if __name__ == "__main__":
    main()