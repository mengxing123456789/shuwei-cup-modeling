"""Second trim pass: remove restatements so the body returns to 25 pages."""
import pathlib
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


# 1. the video-volume sentence repeats the manifest table
sub("video-volume",
    r"""Video accounts for
\slotNVideos{} files and \slotVideoMB{} MB, \slotVideoShare{}\% of the package
volume, and the statement says explicitly that full videos are not additional policy
inputs, so no method in this paper reads them.""",
    r"""The videos are \slotVideoShare{}\% of the package volume by design, and the
statement says they are not additional policy inputs, so no method here reads them.""")

# 2. Part II: the equation paragraph restated what the frontier already says
sub("p2-restate",
    r"""the case fixes. Every term on the right is measurable in the replay, so the frontier of
Section~\ref{sec:p2res} evaluates Equation~\eqref{eq:p2dec} instead of ranking
predictors. We choose ridge on a frozen context length over a sequence model because
the question is how much information a prefix carries, not which architecture wins; the
sequence arm is reported separately and does not beat it. The fit initialises at zero,
solves the normal equations once per context length and stops, and no constant is tuned
on the test records.""",
    r"""the case fixes. We choose ridge on a frozen context length over a sequence model
because the question is how much information a prefix carries, not which architecture
wins; the fit initialises at zero, solves the normal equations once per context length
and stops, and no constant is tuned on the test records.""")

# 3. conclusion: the three-point recap repeated the section bodies
sub("concl-recap",
    r"""Second, and
against the usual expectation, knowing the duration is worth little once the rule is
fixed: handing the rule the true duration and changing nothing else lifts S\slotCaseTwo{}
from \slotPImpSTwoAllCand{} to \slotPOracleSameSTwo{} and S\slotCaseThree{} from
\slotPImpSThreeAllCand{} to \slotPOracleSameSThree{}, paired gains of \slotPOracleGapSTwo{}
$\pm$ \slotPOracleGapSTwoCI{} and \slotPOracleGapSThree{} $\pm$ \slotPOracleGapSThreeCI{},
both excluding zero and both only three to four points wide. The distance from EDF to that
reference, \slotPStochPairSTwoEDFOldDiff{} and \slotPStochPairSThreeEDFOldDiff, is an order
of magnitude larger, so what remains is room in the rule rather than room in the knowledge,
and the information channel is worth exactly what the rule leaves for it. Third, we do not
call the reference an upper bound: it bounds this rule, not the information.""",
    r"""Second, and
against the usual expectation, knowing the duration is worth little once the rule is
fixed: handing it the true duration lifts S\slotCaseTwo{} from \slotPImpSTwoAllCand{} to
\slotPOracleSameSTwo{} and S\slotCaseThree{} from \slotPImpSThreeAllCand{} to
\slotPOracleSameSThree{}, paired gains of \slotPOracleGapSTwo{} $\pm$ \slotPOracleGapSTwoCI{}
and \slotPOracleGapSThree{} $\pm$ \slotPOracleGapSThreeCI{}, both only three to four points
wide, while the distance from EDF to that reference is an order of magnitude larger. The
room is in the rule, not in the knowledge. Third, we do not call the reference an upper
bound: it bounds this rule, not the information.""")

# 4. Part II frontier paragraph: the decision form is now stated above it
sub("p2-frontier",
    r"""Because the released protocol fixes the action space rather than our cost curve (prefixes of 0.2, 0.6 and 1.0~""",
    r"""Because the protocol fixes the action space rather than our cost curve (prefixes of 0.2, 0.6 and 1.0~""")

P.write_text(out, encoding="utf-8")
print("WROTE", P.name, len(src), "->", len(out), " chars (saved", len(src) - len(out), ")")
print("edits:", ", ".join(done))