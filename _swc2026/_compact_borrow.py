# -*- coding: utf-8 -*-
"""Compact pass: shrink figures + compress S/W & Conclusion to bring body back to 23 pages."""
import pathlib, sys

TEX = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\main.tex")

A = [
    # figures
    ("\\includegraphics[width=1.0\\linewidth]{figures/fig0_framework.pdf}",
     "\\includegraphics[width=0.72\\linewidth]{figures/fig0_framework.pdf}"),
    ("\\includegraphics[width=1.0\\linewidth]{figures/fig1_p1_agreement.pdf}",
     "\\includegraphics[width=0.85\\linewidth]{figures/fig1_p1_agreement.pdf}"),
    ("\\includegraphics[width=1.0\\linewidth]{figures/fig2_p1_reliability.pdf}",
     "\\includegraphics[width=0.85\\linewidth]{figures/fig2_p1_reliability.pdf}"),
    ("\\includegraphics[width=1.0\\linewidth]{figures/fig3_p2_error.pdf}",
     "\\includegraphics[width=0.85\\linewidth]{figures/fig3_p2_error.pdf}"),
    ("\\includegraphics[width=1.0\\linewidth]{figures/fig4_p2_voi.pdf}",
     "\\includegraphics[width=0.85\\linewidth]{figures/fig4_p2_voi.pdf}"),
    ("\\includegraphics[width=1.0\\linewidth]{figures/fig5_p2_policy.pdf}",
     "\\includegraphics[width=0.85\\linewidth]{figures/fig5_p2_policy.pdf}"),
    # reproduction paragraph: shorten + breakable
    ("\\paragraph{Reproduction commands.} With the released archives unpacked at \\texttt{Restocking\\_Problem\\_and\\_Data\\_EN}, every number is reproduced by \\texttt{python code/alt\\_p1\\_bocpd.py}, \\texttt{code/alt\\_p2\\_data.py}, \\texttt{code/alt\\_p2\\_kalman.py}, \\texttt{code/alt\\_p2\\_policy.py}, \\texttt{code/alt\\_p2\\_train.py}, \\texttt{code/alt\\_p3\\_ccmip.py}, \\texttt{code/alt\\_p3\\_sweep.py}, \\texttt{code/alt\\_p3\\_ab.py}, then \\texttt{code/verify\\_numbers.py} (321 checks) and \\texttt{xelatex main.tex} twice; the vendored copies in \\texttt{code/vendor/} freeze the derived inputs so the verifier passes without re-running the 428.7~s solver job.",
     "\\paragraph{Reproduction commands.} With the archives unpacked, run the scripts of Appendix~A in their listed order, then \\texttt{code/verify\\_numbers.py} (321 checks) and \\texttt{xelatex} twice; the \\texttt{code/vendor/} copies freeze the derived inputs so the verifier passes without re-running the 428.7~s solver job."),
    # Conclusion: compress four paragraphs into three, keep every number
    ("""We answered the three questions with one state definition and three estimators that share it. A record is reduced to $21$ keypoints per hand in the head frame at $30$~Hz (resampled to $5$~Hz only for the Q1 change-point detector); from that reduction, Question~1 segments the record and scores each segment's reliability, Question~2 predicts through a hidden window and prices the next look, and Question~3 schedules under the resulting duration uncertainty.

The results are mixed in a way that is worth stating plainly. The reliability layer separates clean from contaminated segments at record level (AUC $0.914$) but not at segment level (leave-one-out $0.675$, and $0.076$ once the comparison is made within records), so it is published as an aggregator with a reproducible retention rule rather than as a detector. The Kalman layer beats both baselines at every mask length and its advantage grows with the length of the hidden window, but its measurement noise sits at the numerical floor, which collapses the value-of-information decision to a step function. The scheduling program beats EDF but not the SLACK rule, and the largest effect in its table comes from re-planning rather than from the chance constraint.

Two things would change the picture most: an information source for reliability independent of the bad-frame label, and a heteroscedastic observation model that makes the value of a look record-specific; both remain open rather than filled with assumptions. The chance-level sweep, the five-mapping $\\alpha/\\beta$ grid and the trained ridge baseline with conformal intervals, open in earlier drafts, are now reported in Sections~\\ref{sec:sens} and~\\ref{sec:q2}.""",
     """We answered the three questions with one state definition and three estimators that share it: a record is reduced to $21$ keypoints per hand at $30$~Hz (resampled to $5$~Hz only for Q1), and the same reduction feeds segmentation with reliability, prediction with pricing, and scheduling with reservations. The results are mixed and stated plainly. The reliability layer separates clean from contaminated segments at record level (AUC $0.914$) but not at segment level ($0.675$ leave-one-out, $0.076$ within records), so it is published as an aggregator, not a detector. The Kalman layer beats both baselines at every mask length, but its noise sits at the numerical floor, collapsing the value-of-information decision to a step function. The scheduling program beats EDF but not the SLACK rule, and its largest effect comes from re-planning, not from the chance constraint. Two things would change the picture most: a reliability signal independent of the bad-frame label, and a heteroscedastic observation model making the value of a look record-specific; both remain open. The chance sweep, the five-mapping grid and the trained ridge baseline with conformal intervals, open in earlier drafts, are now reported in Sections~\\ref{sec:sens} and~\\ref{sec:q2}."""),
    # S/W weaknesses bullet 2: compress
    ("  \\item The Kalman layer fits its measurement noise at the numerical floor ($R$ median $1.6\\times10^{-9}$), so the posterior collapses onto the last visible frame and the reported covariance understates uncertainty under occlusion; a trained ridge predictor beats it at every mask length (Table~\\ref{tab:p2train}), so the filter is retained for its information-value derivation, not for peak accuracy; the observation-independent covariance makes the value-of-information rule record-independent (Section~\\ref{sec:sens}).",
     "  \\item The Kalman layer fits its noise at the numerical floor ($R$ median $1.6\\times10^{-9}$), so the posterior collapses onto the last visible frame and understates occluded uncertainty; a trained ridge predictor beats it at every mask length (Table~\\ref{tab:p2train}), so the filter is kept for its information-value derivation, and the value-of-information rule is record-independent (Section~\\ref{sec:sens})."),
]

def main():
    text = TEX.read_bytes().decode("utf-8")
    for old, new in A:
        c = text.count(old)
        assert c == 1, f"anchor count {c} != 1 for: {old[:70]!r}"
        text = text.replace(old, new)
    TEX.write_bytes(text.encode("utf-8"))
    print(f"COMPACT OK: {len(A)} edits, {len(text.encode('utf-8'))} bytes")

if __name__ == "__main__":
    sys.exit(main())
