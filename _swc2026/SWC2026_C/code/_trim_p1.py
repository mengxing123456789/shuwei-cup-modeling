import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

pairs = [
# A. fuse the "headline reproduced" sentences
(r"""The headline number of the
learned route is the one the production script produces, and it is reproduced rather
than assumed: a rerun of the same script at the same seed returns test AUC
\slotPRelTCNTestAUC{} and average precision \slotPRelTCNAPLift{}-fold the prevalence
baseline, digit for digit, in \slotPRelSeconds{} s on one device. That rerun is the
evidence we offer. Everything below it is a sensitivity study around the script, not
a search for a better score.""",
r"""The headline of the learned
route is the one the production script produces, and it is reproduced rather than assumed:
a rerun at the same seed returns test AUC \slotPRelTCNTestAUC{} and average precision
\slotPRelTCNAPLift{}-fold the prevalence baseline, digit for digit, in \slotPRelSeconds{} s
on one device. Everything below is a sensitivity study around that script."""),

# B. drop the Brier-omission paragraph's last two clauses
(r"""We report no Brier score for this route, and the omission is a finding: a Brier score
punishes a mis-calibrated probability \cite{gneiting2007}, whereas the weight was built to
rank, and Appendix~D works through the arithmetic that keeps it from being a probability.""",
r"""We report no Brier score here, and the omission is a finding: a Brier score punishes a
mis-calibrated probability \cite{gneeting2007}, whereas the weight was built to rank, and
Appendix~D works through the arithmetic that keeps it from being one."""),

# C. compress the bi-TCN lead-in
(r"""The learned route escapes that problem by never choosing a count. A dilated temporal
convolutional network with \slotPSegGPUParams{} parameters (a windowed alternative to a
state-space filter) scores each frame for being a boundary, and only two decoding constants ---""",
r"""The learned route escapes that problem by never choosing a count: a dilated temporal
convolutional network with \slotPSegGPUParams{} parameters (a windowed alternative to a
state-space filter) scores each frame for being a boundary, and two decoding constants ---"""),
]

for old, new in pairs:
    if old not in t:
        raise SystemExit("anchor missing:\n" + old[:80])
    t = t.replace(old, new)

t = t.replace(r"\cite{gneeting2007}", r"\cite{gneiting2007}")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("trimmed 3 blocks in P1")
