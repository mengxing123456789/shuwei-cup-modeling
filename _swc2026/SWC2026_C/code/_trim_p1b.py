import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

old = r"""A temporal-convolutional reliability variant was trained on \slotPTCNWindow{}
frames for \slotPTCNBestEpoch{} epochs and reached test AUC \slotPTCNAUC{} against
\slotPTCNValAUC{} on validation, with \slotPTCNParams{} parameters and
\slotPTCNSeconds{} s of training. Its lift over the fused geometric route,
\slotPTCNAPLift{} in average precision, does not pay for the loss of
interpretability, so the paper reports the linear route as the deliverable and
the convolutional route as a bound.

\subsection{Validation}
\label{sec:p1val}

The reliability model is validated in three ways. First, the split is by
environment, so the test numbers are cross-environment numbers. Second, the
threshold sweep reports retention, recall and precision on the same curve, which
makes the precision collapse at high thresholds a stated property rather than a
surprise. Third, we stress the model on the two test environments separately
(Appendix~\ref{app:ablation}). The first is a courier-station environment,
\texttt{\slotPEnvOneName}, with \slotPEnvOneN{} frames and \slotPEnvOnePos{}
positives. The second, \texttt{\slotPEnvTwoName}, has \slotPEnvTwoN{} frames and
\slotPEnvTwoPos{} positives. The AUC is \slotPEnvOneAUC{} on the first and
\slotPEnvTwoAUC{} on the second. The pre-declared pass mark for reliability was
AUC above \slotPassAUC{} with average precision above prevalence. The pooled test
split passes, the courier-station environment does not."""

new = r"""A temporal-convolutional reliability variant was trained on \slotPTCNWindow{} frames for
\slotPTCNBestEpoch{} epochs and reached test AUC \slotPTCNAUC{} against \slotPTCNValAUC{} on
validation, with \slotPTCNParams{} parameters and \slotPTCNSeconds{} s of training; its lift
of \slotPTCNAPLift{} in average precision does not pay for the loss of interpretability, so
the linear route is the deliverable and the convolutional one a bound.

\subsection{Validation}
\label{sec:p1val}

The split is by environment, so every test number here is a cross-environment number, and
the threshold sweep reports retention, recall and precision on one curve, which makes the
precision collapse at high thresholds a stated property rather than a surprise. Stressing the
two test environments separately (Appendix~\ref{app:ablation}): \texttt{\slotPEnvOneName}
holds \slotPEnvOneN{} frames with \slotPEnvOnePos{} positives and \texttt{\slotPEnvTwoName}
\slotPEnvTwoN{} frames with \slotPEnvTwoPos{}, scoring \slotPEnvOneAUC{} and
\slotPEnvTwoAUC{}. The pre-declared mark was AUC above \slotPassAUC{} with average precision
above prevalence: the pooled split passes, the courier-station environment does not."""

if old not in t:
    raise SystemExit("P1 validation anchor missing")
t = t.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("compressed P1 validation")
