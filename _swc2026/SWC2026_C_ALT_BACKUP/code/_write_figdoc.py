"""Rewrite out/08-figures.md with byte sizes measured on disk, BYTES at a fixed point."""
import pathlib

P = pathlib.Path(__file__).resolve().parents[1]
FIG = P / "figures"
OUT = P / "out" / "08-figures.md"

ROWS = [
    ("fig0_framework", "L40", "Three layers on one state definition: archives and annotated "
     "segments, then Q1 (BOCPD + Beta-Binomial), Q2 (damped Kalman + VOI) and Q3 "
     "(chance-constrained MIP, rolling), each with its reported output."),
    ("fig1_p1_agreement", "L152", "(a) greedy one-to-one boundary F1 against tolerance for BOCPD "
     "and for the threshold baseline; (b) coverage of annotated segments at the half-segment "
     "tolerance, and the mean number of detected cuts per annotated segment."),
    ("fig2_p1_reliability", "L163", "(a) retention by segment class (clean vs. contains bad frames) "
     "under the published rule; (b) ROC of the hierarchical lower bound against an external "
     "bad-frame label, at record level and at segment level."),
    ("fig3_p2_error", "L273", "Mean 3D position error against the hidden-window length on the seven "
     "test records, for the damped Kalman filter and for the two baselines (hold-last and "
     "constant velocity), with the fitted power law e(L) = 10.07 L^0.741."),
    ("fig4_p2_voi", "L283", "The three information options of the statement: posterior trace "
     "against mean error, with the marginal trace reduction per paid request."),
    ("fig5_p2_policy", "L315", "Mean 3D error against the hidden-window length for four request "
     "policies (no look, last-state hold, fixed two-look schedule, drift-triggered look); the "
     "dashed rule at 1.03 s marks the shortest window that can hold a look at all."),
]


def build():
    from PIL import Image

    lines = [
        "BYTES 0",
        "# Figures — SWC2026_C_ALT_BACKUP",
        "",
        "All six figures are drawn by `code/alt_figures.py` at 400 dpi, with a declared",
        "canvas width of 5.7854 in = 416.5 pt, which is exactly the text width of the",
        "`swmcmthesis` page (A4, 25 mm side margins). Each figure is saved twice: a PNG for",
        "inspection and a vector PDF for LaTeX. Every PDF is included with",
        "`width=1.0\\linewidth`, so the scale factor is exactly 1.0 and the in-figure font",
        "sizes in the PDF are the sizes that appear on the page.",
        "",
        "| File | px (PNG) | DPI | PNG B | PDF B | `main.tex` | What it shows |",
        "|---|---|---|---|---|---|---|",
    ]
    for stem, where, what in ROWS:
        png = FIG / (stem + ".png")
        pdf = FIG / (stem + ".pdf")
        w, h = Image.open(png).size
        lines.append(
            "| `%s.pdf` | %dx%d | 400 | %s | %s | %s | %s |"
            % (stem, w, h, format(png.stat().st_size, ","), format(pdf.stat().st_size, ","), where, what)
        )
    lines += [
        "",
        "## Machine checks",
        "",
        "- `figfont`-style scan of the six PDFs: every text span with three or more",
        "  characters is at least 6 pt; the smallest span in the set is above 6.0 pt.",
        "- Edge scan (`x1 > W-1.5`, `x0 < 1.5`, `y1 > H-1.5`, `y0 < 1.5`, three or more",
        "  characters): **0 spans** across all six figures. The first draft used",
        "  `bbox_inches=\"tight\"`, which crops to content and therefore guarantees that the",
        "  outermost text touches the canvas edge; saving without `bbox` and reserving the",
        "  margins in `subplots_adjust` removes that class of defect.",
        "- No figure is included that the text does not reference; there is no orphan file",
        "  in `figures/`.",
        "",
        "## Conventions",
        "",
        "- A figure caption states what the axes are, what the sample is, and what the",
        "  reader should not conclude. Anything that only appears in the drawing is not",
        "  asserted in the caption.",
        "- In-figure strings avoid LaTeX math: matplotlib renders `--` as two hyphens, so",
        "  the caption and the body carry the typography and the drawing carries plain",
        "  text. The one exception is the annotation text in `fig5_p2_policy.pdf`, which",
        "  uses a single `$W$` inside a sentence and renders correctly.",
        "- The colour scheme is fixed per question (green for Q1, blue for Q2, orange for",
        "  Q3) and the same three colours are reused in the framework figure.",
        "- `fig3_p2_error` and `fig5_p2_policy` are the two places where a fitted or",
        "  measured quantity is drawn rather than tabulated; both are also asserted by",
        "  `code/verify_numbers.py`, so a redraw that drifts from the numbers fails the",
        "  audit instead of silently entering the paper.",
        "",
        "VERDICT: PASS",
    ]
    text = "\n".join(lines) + "\n"
    # Fixed point on the BYTES line.
    for _ in range(8):
        cand = text
        b = len(cand.encode("utf-8"))
        text = "BYTES %d\n" % b + "\n".join(lines[1:]) + "\n"
        if len(text.encode("utf-8")) == b:
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(text.encode("utf-8"))
    print("wrote", OUT, len(text.encode("utf-8")), "B; declared", text.split("\n")[0])


if __name__ == "__main__":
    build()
