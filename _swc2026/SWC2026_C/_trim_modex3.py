"""Move the calibration digression out of the body (into Appendix D) and shrink
the figure widths, so the body returns to 25 pages without losing content."""
import pathlib
import re
import sys

P = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\main.tex")
src = P.read_text(encoding="utf-8")
out = src
done = []


def sub(name, old, new):
    global out
    n = out.count(old)
    if n != 1:
        print(f"FAIL {name}: found {n}")
        sys.exit(1)
    out = out.replace(old, new, 1)
    done.append(name)


BODY_BLOCK = r"""The temporal route shows why in sharper form. Its mean
predicted badness is \slotPCalMeanRaw{} against a base rate of \slotPCalBase{}. Temperature scaling ($T=\slotPCalTemp{}$) raises the Brier score from
\slotPCalBrierRaw{} to \slotPCalBrierTemp{} and the calibration error from
\slotPCalECEraw{} to \slotPCalECEt{}, and even Platt scaling
(\slotPCalBrierPlatt{}) loses to a constant predictor at \slotPCalBrierConst{}. The
cause is arithmetic: a temperature only rescales the logit, while the mis-fit is an
intercept, so no positive temperature maps that mean onto a base rate two orders of
magnitude smaller. We therefore use the weight as a filter, never as a probability."""

sub("move-calib-body", BODY_BLOCK,
    r"""The same arithmetic that stops this route from being a probability is worked
through in Appendix~\ref{app:calib}; it is why we use the weight as a filter and never
as a probability.""")

sub("move-calib-appendix", r"\end{document}",
    r"""\subsection*{Why temperature scaling fails on the reliability route}
\label{app:calib}

The temporal route shows the failure in sharper form. Its mean predicted badness is
\slotPCalMeanRaw{} against a base rate of \slotPCalBase{}. Temperature scaling
($T=\slotPCalTemp{}$) raises the Brier score from \slotPCalBrierRaw{} to
\slotPCalBrierTemp{} and the calibration error from \slotPCalECEraw{} to
\slotPCalECEt{}, and even Platt scaling (\slotPCalBrierPlatt{}) loses to a constant
predictor at \slotPCalBrierConst{}. The cause is arithmetic: a temperature only
rescales the logit, while the mis-fit is an intercept, so no positive temperature maps
that mean onto a base rate two orders of magnitude smaller.

\end{document}""")

P.write_text(out, encoding="utf-8")
print("main.tex", len(src), "->", len(out))

# shrink figure widths in the generator
G = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\code\fill_numbers.py")
g = G.read_text(encoding="utf-8")
before = g
for old, new, name in (
    (r'("FigW": (r"0.45\linewidth", "layout"),)', r'("FigW": (r"0.38\linewidth", "layout"),)', "FigW"),
    (r'("FigWSmall": (r"0.25\linewidth", "layout"),)', r'("FigWSmall": (r"0.20\linewidth", "layout"),)', "FigWSmall"),
):
    if g.count(old) != 1:
        print("FAIL spec", name, g.count(old))
        sys.exit(1)
    g = g.replace(old, new, 1)
G.write_text(g, encoding="utf-8")
print("fill_numbers.py spec updated; changed:", g != before)
print("edits:", ", ".join(done))