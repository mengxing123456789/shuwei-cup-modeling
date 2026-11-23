import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

# shrink the two-panel figure so it fits the space freed earlier
t = t.replace(r"\begin{subfigure}{0.42\linewidth}", r"\begin{subfigure}{0.34\linewidth}")

# tighten its caption
old = r"""\caption{Two views of the same test records. Left: the share of flagged frames in each
record, split by hand, showing that the flags concentrate in a few recordings rather than
spreading over the corpus. Right: the per-record gain of the learned boundary decoder over
chain-constrained agglomeration, positive on six of the seven records; the short record
loses because it holds a single true stage.}"""
new = r"""\caption{Two views of the same test records: the share of flagged frames per record and hand
(left), and the per-record gain of the learned boundary decoder over chain-constrained
agglomeration (right), positive on six of seven records.}"""
if old in t:
    t = t.replace(old, new)
    print("caption tightened")
else:
    print("caption MISS")

# and free two more lines in Section 3.4
old2 = r"""A temporal-convolutional reliability variant was trained on \slotPTCNWindow{} frames for
\slotPTCNBestEpoch{} epochs and reached test AUC \slotPTCNAUC{} against \slotPTCNValAUC{} on
validation, with \slotPTCNParams{} parameters and \slotPTCNSeconds{} s of training; its lift
of \slotPTCNAPLift{} in average precision does not pay for the loss of interpretability, so
the linear route is the deliverable and the convolutional one a bound."""
new2 = r"""A temporal-convolutional reliability variant was trained on \slotPTCNWindow{} frames for
\slotPTCNBestEpoch{} epochs and reached test AUC \slotPTCNAUC{} against \slotPTCNValAUC{} on
validation with \slotPTCNParams{} parameters and \slotPTCNSeconds{} s of training; its lift of
\slotPTCNAPLift{} in average precision does not pay for the loss of interpretability, so the
linear route is the deliverable."""
if old2 in t:
    t = t.replace(old2, new2)
    print("tcn sentence trimmed")
else:
    print("tcn MISS")

io.open(P, "w", encoding="utf-8", newline="").write(t)
