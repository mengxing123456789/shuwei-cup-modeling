"""Fix broken appendix cross-references and put the learned-predictor numbers in
Appendix D.

All three appendix headings are `\\section*`, which never step a counter, so
`\\ref{app:...}` resolves to whatever the last numbered section was (the PDF
literally printed "Appendix 8").  The appendices are frozen in order A/B/C/D, so
the references become literal letters, which also matches the hard-coded "Appendix~D"
elsewhere.  The learned-predictor paragraph was compressed in the body and promised
its numbers here, so they are restored here.
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "main.tex")

REFS = [
    ("\\ref{app:calib}", "D"),
    ("\\ref{app:repro}", "C"),
]

GRU = r'''
\subsection*{The learned predictor on the same windows}
\label{app:gru}

Trained on identical windows, a GRU over the wrist track reaches
\slotPGPUAWristRMSE{}~cm at the shortest mask with \slotPGPUAWristWithinTwo{}\% of
windows inside the two-centimetre band, \slotPGpuRatio{} times better than the
regularised predictor there, but the same architecture gives \slotPGPUBSTwoRMSE{},
\slotPGPUCBothRMSE{} and \slotPGPUDBothRMSE{}~cm at the three longer masks, which is the
ridge ordering again: the mask removes exactly the frames that carried the motion. It is
not reported as the main predictor because it needs a GPU and because its error is not
monotone in the horizon.
'''


def main():
    tex = io.open(TEX, encoding="utf-8").read()
    n = 0
    for old, new in REFS:
        c = tex.count(old)
        assert c >= 1, (old, c)
        tex = tex.replace(old, new)
        n += c
    print("references replaced:", n)

    anchor = "\\subsection*{Why temperature scaling fails on the reliability route}"
    assert tex.count(anchor) == 1, tex.count(anchor)
    tex = tex.replace(anchor, GRU.strip("\n") + "\n\n" + anchor)

    # no literal "Appendix <digit>" may survive
    import re
    bad = re.findall(r"Appendix[~ ]\d", tex)
    print("residual 'Appendix <digit>' in source:", bad)

    io.open(TEX, "w", encoding="utf-8", newline="\n").write(tex)
    print("written", os.path.getsize(TEX), "B")


if __name__ == "__main__":
    main()