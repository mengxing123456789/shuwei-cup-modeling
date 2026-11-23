import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

old = r"""Offered a threshold to choose, the weight refuses one. With the asymmetric cost
$\kappa(\tau)=\big(k(\tau)+r\,g(\tau)\big)/n$ on the validation split, where $k$ counts bad
frames kept and $g$ good frames dropped, no ratio from \slotPCostRatioLow{} to
\slotPCostRatioHigh{} selects an interior $\tau$: above the smallest ratio the minimiser keeps
every frame at \slotPCostKeepAll, and at that ratio it drops every frame at
\slotPCostDropAll. Ranking is invariant to calibration as well, the three scores agreeing to
the last digit, so the customary calibrated $0.5$ cut would drop most of the training set at
\slotPCostHalfMult{} times the cost of keeping it all. The filter therefore exists and cost
minimisation says it should not be used, which is why the weight enters Part II as a weight."""

new = r"""Offered a threshold to choose, the weight refuses one. With the asymmetric cost
$\kappa(\tau)=\big(k(\tau)+r\,g(\tau)\big)/n$ on the validation split, where $k$ counts bad
frames kept and $g$ good frames dropped, no ratio from \slotPCostRatioLow{} to
\slotPCostRatioHigh{} selects an interior $\tau$: above the smallest ratio the minimiser
keeps every frame, and at that ratio it drops every frame. Ranking is invariant to
calibration as well, so the customary calibrated $0.5$ cut would drop most of the training
set at \slotPCostHalfMult{} times the cost of keeping it all: the filter exists and cost
minimisation says it should not be used, which is why the weight enters Part II as one."""

if old not in t:
    raise SystemExit("anchor not found")
io.open(P, "w", encoding="utf-8", newline="").write(t.replace(old, new))
print("trimmed")
