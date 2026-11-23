"""Insert the reservation-level identifiability paragraph and its slots.

Adds ten slots read from p3_quantile_curve.json, one new paragraph in Part III
Validation, and fixes the hard-coded "Appendix~D" at main.tex:1156.

Every edit asserts count==1 on the original string; nothing is written if any
edit misses.
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "main.tex")
FN = os.path.join(ROOT, "code", "fill_numbers.py")

SLOTS = '''
# --- reservation-level identifiability (p3_quantile_curve.json) ------------
for _nm, _c, _key, _i in (
        ("PQSweepLow", "S2", "q_grid", 0),
        ("PQSweepHigh", "S2", "q_grid", -1),
        ("PQTuneLowSTwo", "S2", "tune_curve", 0),
        ("PQTuneHighSTwo", "S2", "tune_curve", -1),
        ("PQTuneLowSThree", "S3", "tune_curve", 0),
        ("PQTuneHighSThree", "S3", "tune_curve", -1),
        ("PQHoldLowSTwo", "S2", "holdout_curve", 0),
        ("PQHoldHighSTwo", "S2", "holdout_curve", -1),
        ("PQHoldLowSThree", "S3", "holdout_curve", 0),
        ("PQHoldHighSThree", "S3", "holdout_curve", -1),
):
    add(_nm, "p3_quantile_curve", ["cases", _c, _key, _i], "f4")
'''

PARA = r'''
The search fixes the rule but not the level, and the level turns out to be weakly
identified. With the two selected configurations held fixed in everything except the
quantile, and with that quantile swept from \slotPQSweepLow{} to \slotPQSweepHigh{} on
the same tuning seeds, the on-time rate falls monotonically: from
\slotPQTuneLowSTwo{} to \slotPQTuneHighSTwo{} in S\slotCaseTwo{} and from
\slotPQTuneLowSThree{} to \slotPQTuneHighSThree{} in S\slotCaseThree. Over-reservation
is the failure mode, and \eqref{eq:cfprob} says why --- a reservation buys capacity, so a
metric that prices lateness alone charges it as pure cost. On the held--out seeds the
same interval is flatter (\slotPQHoldLowSTwo{} to \slotPQHoldHighSTwo{} and
\slotPQHoldLowSThree{} to \slotPQHoldHighSThree{}), so what the data support is the
plateau rather than a point; the sweep never sampled below \slotPQSweepLow{}, which
bounds the claim to the region it actually visited.
'''

ANCHOR = ("S\\slotCaseThree{} alone crosses zero; and because the candidate family came from earlier\n"
          "experiments, the fifteen-fifteen split confirms rather than blinds.\n")


def main():
    tex = io.open(TEX, encoding="utf-8").read()
    fn = io.open(FN, encoding="utf-8").read()
    edits = []

    # 1) hard-coded appendix letter -> reference
    old = "Table~\\ref{tab:cf} in Appendix~D checks this"
    new = "Table~\\ref{tab:cf} in Appendix~\\ref{app:calib} checks this"
    assert tex.count(old) == 1, ("appendix letter", tex.count(old))
    tex = tex.replace(old, new)
    edits.append("appendix-letter")

    # 2) paragraph after the candidate-search paragraph
    assert tex.count(ANCHOR) == 1, ("anchor", tex.count(ANCHOR))
    tex = tex.replace(ANCHOR, ANCHOR + PARA)
    edits.append("q-paragraph")

    # 3) slots
    marker = 'add("POracleGapSThreeCI", "p3_oracle_same_rule", ["cases", "S3", "gap_ci95"], "f4")\n'
    assert fn.count(marker) == 1, ("slot anchor", fn.count(marker))
    fn = fn.replace(marker, marker + SLOTS)
    edits.append("slots")

    io.open(TEX, "w", encoding="utf-8", newline="\n").write(tex)
    io.open(FN, "w", encoding="utf-8", newline="\n").write(fn)
    print("edits applied:", edits)
    print("tex bytes", os.path.getsize(TEX), "fn bytes", os.path.getsize(FN))


if __name__ == "__main__":
    main()