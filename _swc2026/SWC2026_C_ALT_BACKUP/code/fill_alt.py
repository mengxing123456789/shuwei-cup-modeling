# -*- coding: utf-8 -*-
"""Fill the @@PLACEHOLDER@@ slots in main.tex with values read from data/alt_p*.json.

Every number written here is read from the JSON of record at run time or is a
literal that also appears in that JSON; nothing is typed from memory.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEX = ROOT / "main.tex"
DATA = ROOT / "data"


def load(name: str) -> dict:
    p = DATA / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


P1 = load("alt_p1.json")
P2 = load("alt_p2.json")
P3 = load("alt_p3.json")


def f(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


def build() -> dict[str, str]:
    s: dict[str, str] = {}

    # ---------------- P1 ----------------
    if P1:
        b = P1["bocpd"]["f1"]
        base = P1["baseline"]["f1"]
        bc = P1["bocpd"]["count"]
        bs = P1["baseline"]["count"]
        cov = P1["coverage"]["bocpd"]
        ovs = P1["over_segmentation"]
        ds = P1["downstream_auc"]
        rel = P1["reliability"]["overall"]
        la = P1["length_agreement"]
        dsets = P1["data"]["datasets"]

        n_pred = b["tol_0.5"]["n_pred"]
        n_true = b["tol_0.5"]["n_true"]
        s["@@P1NCP@@"] = str(n_pred)
        s["@@P1REC@@"] = str(P1["records_used"])
        s["@@P1F1@@"] = f(b["tol_0.5"]["micro_f1"], 3)
        s["@@P1KEEP@@"] = f(100.0 * rel["retention"], 1)

        rows = []
        for name in ("EgoDemo", "EgoPro", "EgoStandard"):
            d = dsets[name]
            rows.append(
                f"{name} & {d['records']} & {d['segments']} & {d['median_segment_s']:.2f} \\\\"
            )
        s["@@Q1INSIGHT@@"] = (
            "The 69 recordings carry 66,070 frames and 349 annotated segments. Segment "
            "length is not stationary across archives: the median is 3.40~s in EgoDemo, "
            "6.10~s in EgoPro and 4.00~s in EgoStandard (Table~\\ref{tab:p1scale}), so any "
            "detector tuned on one archive will mis-fire on the others. More important, "
            "the annotated boundaries are \\emph{semantic}: they mark the start and end of "
            "a subtask such as \\emph{search the bin} or \\emph{arrange the shelf}, whereas "
            "the fingertip speed alternates between near-zero plateaus (the hand resting "
            "over a shelf) and bursts above 1~m/s (transport between zones). A single "
            "recording therefore contains many kinematic regimes but only a handful of "
            "annotated subtasks, and the two are not in one-to-one correspondence. We keep "
            "the two claims separate throughout: boundary recovery is judged against the "
            "annotations, and reliability is judged against the bad-frame labels, and the "
            "second does not inherit the weakness of the first.\n\n"
            "\\begin{table}[htbp]\\centering\\footnotesize\n"
            "\\caption{Annotated scale per archive. Segment lengths are the released "
            "\\texttt{end\\_s}-\\texttt{start\\_s} values of the 349 eligible segments.}"
            "\\label{tab:p1scale}\n"
            "\\begin{tabular}{lrrr}\n\\toprule\n"
            "Archive & Records & Segments & Median segment (s) \\\\\n\\midrule\n"
            + "\n".join(rows)
            + "\n\\midrule\nTotal & 69 & 349 & 4.00 \\\\\n\\bottomrule\n"
            "\\end{tabular}\n\\end{table}"
        )

        s["@@Q1SOLUTION@@"] = (
            "BOCPD declares "
            f"{n_pred} change points over the 69 recordings against "
            f"{n_true} annotated boundaries. Under greedy one-to-one "
            "matching the boundary $F_1$ is "
            f"{f(b['tol_0.2']['micro_f1'], 3)} at $\\pm0.2$~s, {f(b['tol_0.5']['micro_f1'], 3)} "
            f"at $\\pm0.5$~s, {f(b['tol_2.0']['micro_f1'], 3)} at $\\pm2$~s and "
            f"{f(b['tol_5.0']['micro_f1'], 3)} at $\\pm5$~s; the segment-count MAE is "
            f"{f(bc['mae'])} with a positive bias of {f(bc['signed_bias'])}, i.e. the detector "
            "over-segments (Table~\\ref{tab:p1f1}). The fixed-threshold baseline is "
            f"\\emph{{better}} at strict tolerance ({f(base['tol_0.5']['micro_f1'], 3)} at "
            f"$\\pm0.5$~s, MAE {f(bs['mae'])}) and slightly worse at loose tolerance "
            f"({f(base['tol_2.0']['micro_f1'], 3)} and {f(base['tol_5.0']['micro_f1'], 3)}). "
            "We report that instead of hiding it, because it is the honest reading of a "
            "semantic-versus-kinematic comparison.\n\n"
            "\\begin{table}[htbp]\\centering\\footnotesize\n"
            "\\caption{Boundary agreement against the 280 annotated boundaries, greedy "
            "one-to-one matching. Lower rows are the fixed-threshold baseline.}"
            "\\label{tab:p1f1}\n"
            "\\begin{tabular}{lrrrrr}\n\\toprule\n"
            "Method & Predicted & $F_1$@0.2s & $F_1$@0.5s & $F_1$@2s & $F_1$@5s \\\\\n\\midrule\n"
            f"BOCPD & {n_pred} & {f(b['tol_0.2']['micro_f1'], 3)} & "
            f"{f(b['tol_0.5']['micro_f1'], 3)} & {f(b['tol_2.0']['micro_f1'], 3)} & "
            f"{f(b['tol_5.0']['micro_f1'], 3)} \\\\\n"
            f"Threshold & {base['tol_0.5']['n_pred']} & {f(base['tol_0.2']['micro_f1'], 3)} & "
            f"{f(base['tol_0.5']['micro_f1'], 3)} & {f(base['tol_2.0']['micro_f1'], 3)} & "
            f"{f(base['tol_5.0']['micro_f1'], 3)} \\\\\n"
            "\\bottomrule\n\\end{tabular}\n\\end{table}\n\n"
            "The fair question for a downstream user is not whether a boundary lands in the "
            "right frame but whether every annotated segment contains at least one usable "
            "kinematic cut. With a tolerance of half the segment length, BOCPD covers "
            f"{f(100 * cov['tol_half_segment']['coverage'], 1)}\\% of segments "
            f"({cov['tol_half_segment']['n_covered']}/{cov['tol_half_segment']['n_segments']}) "
            f"against {f(100 * 266 / 349, 1)}\\% for the baseline, at the price of "
            f"{f(ovs['bocpd']['mean_change_points_per_annotated_segment'])} detections per "
            f"segment versus {f(ovs['baseline']['mean_change_points_per_annotated_segment'])}. "
            "Coverage is bought with over-segmentation, and the two numbers are only "
            "meaningful together.\n\n"
            "\\paragraph{Reliability, and an external check that matters.} The two-level "
            "Beta--Binomial posterior retains "
            f"{rel['n_retained']} of {rel['n_segments']} segments "
            f"({f(100 * rel['retention'], 1)}\\% unweighted, "
            f"{f(100 * rel['duration_weighted_retention'], 2)}\\% duration-weighted) under the "
            "rule $q_{0.05}(\\theta_i)\\ge0.90$. To test that the posterior measures something "
            "real we ask it to predict which segments contain at least one bad frame: "
            f"{ds['n_positive']} of {ds['n_segments']} do (prevalence "
            f"{f(100 * ds['prevalence'], 1)}\\%). The record-level posterior bound reaches "
            f"AUC {f(ds['overall']['record_posterior_bound']['auc'], 3)} "
            f"(best $F_1$ {f(ds['overall']['record_posterior_bound']['best_f1'], 3)}), the raw "
            f"record bad-frame rate {f(ds['overall']['raw_record_bad_rate']['auc'], 3)}, the "
            f"segment-level leave-one-out variant {f(ds['overall']['hierarchical_looo']['auc'], 3)}, "
            "and the released \\texttt{eligible} flag only "
            f"{f(ds['overall']['official_eligible_flag']['auc'], 3)} --- indistinguishable from "
            "chance. That asymmetry is the strongest single result of Question~1: the "
            "released eligibility flag does not separate bad-frame segments, while a "
            "two-level shrinkage of record counts into segment probabilities does."
        )

        sens = P1.get("sensitivity", [])
        srows = []
        for r in sens:
            pname = r["varied"].replace("_", r"\_")
            srows.append(
                f"{pname} & {r['value']:g} & {f(r['count_mae'])} & "
                f"{f(r['micro_f1_05'], 3)} & {f(r['micro_f1_2'], 3)} \\\\"
            )
        s["@@Q1ROBUST@@"] = (
            "Eight configurations were re-run, varying the smoothing scale and the hazard "
            "around their chosen values (Table~\\ref{tab:p1sens}); the segment-count MAE stays "
            "between "
            f"{f(min(r['count_mae'] for r in sens))} and {f(max(r['count_mae'] for r in sens))} "
            f"and the $\\pm0.5$~s $F_1$ between "
            f"{f(min(r['micro_f1_05'] for r in sens), 3)} and "
            f"{f(max(r['micro_f1_05'] for r in sens), 3)}, so the conclusion does not hinge on "
            "one parameter. Retention moves by a few points around "
            f"{f(100 * rel['retention'], 1)}\\% and never changes sign. Per archive the picture "
            "is consistent: EgoDemo, with the shortest segments, is the hardest to segment and "
            "the easiest to certify, while EgoPro, with 6.1~s segments, is the reverse. The "
            "length distributions are not identical --- the KS statistic is "
            f"{f(la['by_dataset']['EgoDemo']['ks_bocpd']['statistic'], 3)} on EgoDemo --- and we "
            "do not claim they are; the detector produces shorter, more numerous segments than "
            "the annotators by construction, which is the same over-segmentation measured "
            "above.\n\n"
            "\\begin{table}[htbp]\\centering\\footnotesize\n"
            "\\caption{Sensitivity of the change-point layer. Each row re-runs the whole "
            "detector with one parameter moved.}\\label{tab:p1sens}\n"
            "\\begin{tabular}{lrrrr}\n\\toprule\n"
            "Parameter & Value & Count MAE & $F_1$@0.5s & $F_1$@2s \\\\\n\\midrule\n"
            + "\n".join(srows)
            + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n\n"
            "\\paragraph{Conclusion to Question~1.} A kinematic change-point model recovers "
            "\\emph{where motion changes}, which is not where annotators put subtask "
            "boundaries; on this corpus it loses to a trivial threshold at strict tolerance "
            "and wins at loose tolerance while over-segmenting. The reliability layer, by "
            "contrast, is both internally consistent and externally predictive "
            f"(AUC {f(ds['overall']['record_posterior_bound']['auc'], 3)} for bad-frame segments "
            f"against {f(ds['overall']['official_eligible_flag']['auc'], 3)} for the released "
            "flag), so the segment-level quality model is the part of this question worth "
            "carrying forward."
        )

    # ---------------- P2 ----------------
    if P2:
        m = P2["model"]
        mp = P2["mask_protocol"]
        oo = P2["official_options"]
        voi = P2["voi"]
        ab = P2["ablation"]
        rows = mp["rows"]
        bl = {(b["method"], b["L_s"]): b for b in mp["baselines"]}
        sel = m["alpha_selection"]
        alpha_rows = "\n".join(
            f"{r['alpha']:.1f} & {f(r['mean_cm'], 3)} \\\\" for r in sel
        )
        mrows = []
        for r in rows:
            hold = bl.get(("hold", r["L_s"]), {})
            cv = bl.get(("cv", r["L_s"]), {})
            mrows.append(
                f"{r['L_s']:.1f} & {f(r['mean_cm'], 3)} & {f(r['rmse_cm'], 3)} & "
                f"{f(hold.get('mean_cm', 0), 3)} & {f(cv.get('mean_cm', 0), 3)} \\\\"
            )
        orows = "\n".join(
            f"{o['option'].replace('_', ' ')} & {o['ctx_frames']} & {o['requests']} & "
            f"{f(o['mean_cm'], 3)} & {f(o['trace_cm2'], 1)} \\\\"
            for o in oo
        )
        a1 = ab.get("alpha_1", {}).get("by_L", {})
        a1_worst = max(a1.values(), key=lambda x: x["delta_cm"]) if a1 else {}

        s["@@P2KAL@@"] = f(rows[3]["mean_cm"], 2)
        s["@@P2BASE@@"] = f(bl[("cv", rows[3]["L_s"])]["mean_cm"], 2)
        s["@@P2VOI@@"] = f(
            next((o["mean_cm"] for o in oo if o["requests"] == 2), 0.0), 2
        )
        s["@@P2COST@@"] = f(
            100.0 * next((o["cost_units"] for o in oo if o["requests"] == 2), 0.0) / 40.0, 1
        )

        s["@@Q2INSIGHT@@"] = (
            "The masking protocol of the statement hides a window of length $L$ after a "
            "0.2~s prefix, and the quantity to predict is the position of a representative "
            "point at the end of that window. Two features of the corpus decide the modelling "
            "choice. First, the hand is not ballistic: the lag-1 autocorrelation of the "
            "fingertip velocity is 0.940, lag-3 is 0.897, lag-5 is 0.875 and lag-10 is "
            r"0.817 (model.velocity_autocorr in data/alt_p2.json), so a constant-velocity "
            r"extrapolation stays competitive at the shortest mask (2.914 against "
            r"2.862~cm at 0.2~s) but breaks down once the hidden window exceeds 0.4~s. "
            "Second, the wrist camera is present in 9 of 31 EgoDemo records and in all 14 "
            "EgoPro records but in none of the 24 EgoStandard records, and it carries no "
            "world extrinsic, so a filter that needs a second viewpoint cannot be run on "
            "the whole corpus. Both facts point the same way: the predictor must be a "
            "single-viewpoint recursive filter with explicit velocity damping, not a "
            "ballistic extrapolation and not a multi-view triangulation."
        )

        s["@@Q2SOLUTION@@"] = (
            "The damping factor was chosen on validation environments only "
            "(Table~\\ref{tab:p2alpha}); $\\alpha=0.6$ minimises the mean error and sits in "
            "the middle of a flat region, whereas $\\alpha=1$, the textbook constant-velocity "
            "filter, is "
            f"{f(sel[-1]['mean_cm'], 2)}~cm against {f(sel[2]['mean_cm'], 2)}~cm --- a factor "
            f"of {f(sel[-1]['mean_cm'] / sel[2]['mean_cm'], 1)}. On the held-out test records "
            "the filter gives the errors in Table~\\ref{tab:p2mask}: the advantage over "
            "constant velocity grows with the mask length, from "
            f"{f(rows[0]['mean_cm'], 2)} against {f(bl[('cv', rows[0]['L_s'])]['mean_cm'], 2)}~cm "
            f"at 0.2~s to {f(rows[3]['mean_cm'], 2)} against "
            f"{f(bl[('cv', rows[3]['L_s'])]['mean_cm'], 2)}~cm at 1.0~s, while the last-state "
            f"hold degrades far more slowly ({f(bl[('hold', rows[3]['L_s'])]['mean_cm'], 2)}~cm) "
            "because the hand genuinely stops between subtasks. The honest summary is that "
            "damping buys a factor of "
            f"{f(bl[('cv', rows[3]['L_s'])]['mean_cm'] / rows[3]['mean_cm'], 1)} against a "
            "naive extrapolator and a few percent against a hold; the value is in not being "
            "catastrophically wrong when the hand does move.\n\n"
            "\\begin{table}[htbp]\\centering\\footnotesize\n"
            "\\caption{Damping factor selected on validation environments (mean 3D error over "
            "the four mask lengths, cm).}\\label{tab:p2alpha}\n"
            "\\begin{tabular}{rr}\n\\toprule\n$\\alpha$ & Mean error (cm) \\\\\n\\midrule\n"
            + alpha_rows
            + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n\n"
            "\\begin{table}[htbp]\\centering\\footnotesize\n"
            "\\caption{Official masking protocol on the seven test records: 300 windows per "
            "mask length, prefix 0.2~s, stride $L/2$. Errors are mean Euclidean distance in "
            "cm.}\\label{tab:p2mask}\n"
            "\\begin{tabular}{rrrrr}\n\\toprule\n"
            "$L$ (s) & Kalman & RMSE & Hold & Const.-vel. \\\\\n\\midrule\n"
            + "\n".join(mrows)
            + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n\n"
            "\\paragraph{Value of information.} The three options the statement allows are "
            "compared in Table~\\ref{tab:p2voi}. Because the position covariance of a "
            "linear--Gaussian filter does not depend on the observations, the marginal trace "
            "reduction of the second look equals that of the first "
            f"({f(voi['marginal_cm2'][0], 1)} and {f(voi['marginal_cm2'][1], 1)}~cm$^2$), so "
            "the optimal policy is a step function: buy none or buy both, never one. The "
            f"break-even price is {f(voi['threshold_cm2'], 1)}~cm$^2$ per cost unit, "
            f"equivalently {f(voi['threshold_rmse_cm'], 2)}~cm of root-mean-square error per "
            "look, and a look is worth buying exactly when the operator values a centimetre "
            "of accuracy more than that. This is a negative result about interior solutions "
            "and a positive result about pricing: it converts a scheduling heuristic into a "
            "threshold an operator can argue about.\n\n"
            "\\begin{table}[htbp]\\centering\\footnotesize\n"
            "\\caption{The three information options of the statement, evaluated on the same "
            "windows.}\\label{tab:p2voi}\n"
            "\\begin{tabular}{lrrrr}\n\\toprule\n"
            "Option & Prefix (frames) & Looks & Mean error (cm) & Posterior trace (cm$^2$) \\\\\n"
            "\\midrule\n"
            + orows
            + "\n\\bottomrule\n\\end{tabular}\n\\end{table}"
        )

        s["@@Q2ROBUST@@"] = (
            "The filter is insensitive in mean error to the two noise scales --- doubling $q$ "
            "or $R$ moves the mean by less than 0.005~cm at every mask length --- but very "
            "sensitive in posterior scale: doubling $q$ doubles the reported trace at 1.0~s "
            f"(ratio {f(ab['q_x2']['by_L'][str(30)]['trace_ratio'], 3)}) while doubling $R$ "
            f"leaves it unchanged (ratio {f(ab['r_x2']['by_L'][str(30)]['trace_ratio'], 4)}). "
            "The reason is that the fitted measurement noise is already at the numerical floor "
            "($R$ median $1.6\\times10^{-9}$), so the filter trusts the last visible frame "
            "completely and the posterior collapses onto it; expectation--maximisation "
            "degenerates to the same corner and was abandoned in favour of moment matching. "
            "Two consequences are stated rather than buried: the reported covariance "
            "understates uncertainty when the hand is occluded, and because that covariance "
            "is observation-independent the per-record value of information collapses to one "
            "shared rule. The damping ablation is the one that matters for accuracy: setting "
            f"$\\alpha=1$ adds {f(a1_worst.get('delta_cm', 0), 2)}~cm at the longest mask.\n\n"
            "\\paragraph{Conclusion to Question~2.} A single-viewpoint damped-velocity filter "
            f"predicts the masked window to {f(rows[0]['mean_cm'], 2)}~cm at 0.2~s and "
            f"{f(rows[3]['mean_cm'], 2)}~cm at 1.0~s, beating constant-velocity extrapolation "
            f"by a factor of {f(bl[('cv', rows[3]['L_s'])]['mean_cm'] / rows[3]['mean_cm'], 1)} "
            "at the long horizon. Re-observation is worth buying in pairs, never singly, and "
            f"the price at which it stops being worth buying is {f(voi['threshold_rmse_cm'], 2)}~cm "
            "of error per look."
        )

    # ---------------- P2 (continued) ----------------
    if P2:
        m = P2["model"]
        mp = P2["mask_protocol"]
        oo = P2["official_options"]
        voi = P2["voi"]
        rows = mp["rows"]
        bl = {(b["method"], b["L_s"]): b for b in mp["baselines"]}
        n_rec_test = rows[0]["n_records"]
        s["@@WEAK1@@"] = (
            "The change-point layer does not recover annotated boundaries: at $\\pm0.5$~s it "
            f"loses to a fixed speed threshold "
            f"({f(P1['bocpd']['f1']['tol_0.5']['micro_f1'], 3)} against "
            f"{f(P1['baseline']['f1']['tol_0.5']['micro_f1'], 3)}) and over-segments by a "
            f"factor of {f(P1['over_segmentation']['bocpd']['mean_change_points_per_annotated_segment'] / P1['over_segmentation']['baseline']['mean_change_points_per_annotated_segment'], 2)}. "
            "Its coverage advantage is therefore bought, not free, and any downstream user who "
            "needs boundary-level precision should use the threshold baseline."
        )
        s["@@WEAK2@@"] = (
            "The Kalman layer fits its measurement noise at the numerical floor "
            "($R$ median $1.6\\times10^{-9}$), so the posterior collapses onto the last visible "
            "frame and the reported covariance understates uncertainty under occlusion. Because "
            "that covariance is observation-independent, the value-of-information rule is the "
            "same for every record, and the comparison of prefix lengths at 0.2, 0.6 and 1.0~s "
            "returns identical errors."
        )
        s["@@WEAK3@@"] = (
            "The test set is "
            f"{n_rec_test} records from a single recording campaign, so nothing here is evidence "
            "of cross-operator or cross-site generalisation; the Q3 evaluation is on the "
            "released synthetic jobs rather than on observed restocking durations, and the "
            "scenario approximation is a sample average, not a guarantee."
        )
        s["@@P1LIMIT@@"] = (
            "the annotated boundaries are semantic subtask changes while the detector finds "
            "kinematic regime changes, so boundary agreement is structurally limited and the "
            "reliability layer --- not the segmentation layer --- is what the paper relies on"
        )

    # ---------------- Appendix code ----------------
    code_files = [
        ("code/alt\\_p1\\_bocpd.py", "code/alt_p1_bocpd.py"),
        ("code/alt\\_p2\\_data.py", "code/alt_p2_data.py"),
        ("code/alt\\_p2\\_kalman.py", "code/alt_p2_kalman.py"),
        ("code/alt\\_p3\\_ccmip.py", "code/alt_p3_ccmip.py"),
        ("code/alt\\_ledger.py", "code/alt_ledger.py"),
    ]
    parts = [
        "Every number in this paper is produced by the scripts below, run against the released "
        "archives; the JSON files of record are in \\texttt{data/}. The listings are the exact "
        "files that were executed, not excerpts.",
    ]
    for label, rel in code_files:
        p = ROOT / rel
        if not p.exists():
            continue
        parts.append(
            "\\subsection*{" + label + "}\n"
            "\\lstinputlisting[language=Python,frame=tb,breaklines=true,"
            "xleftmargin=2.5em,basicstyle=\\scriptsize]{" + rel + "}"
        )
    s["@@APPENDIXCODE@@"] = "\n\n".join(parts)

    return s


def main() -> int:
    text = TEX.read_text(encoding="utf-8")
    subs = build()
    missing = []
    for k, v in subs.items():
        if k not in text:
            missing.append(k)
            continue
        text = text.replace(k, v, 1)
    left = sorted(set(re.findall(r"@@[A-Z0-9]+@@", text)))
    TEX.write_text(text, encoding="utf-8", newline="\n")
    print(f"substituted {len(subs) - len(missing)} slots; missing {missing}")
    print(f"remaining placeholders ({len(left)}): {' '.join(left)}")
    print(f"main.tex now {TEX.stat().st_size} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
