BYTES 2934
# Writing record — SWC2026_C_ALT_BACKUP

## Delivery shape

| Item | Measured |
|---|---|
| Language | English throughout, including figure strings and table headers |
| Class | `swmcmthesis` (2026 autumn official), body type 12 pt Times New Roman |
| Submitted pages | 87 (summary sheet 1 + contents 1 + body 23 + appendix 62) |
| Body pages | 23, well inside the 25-page ceiling; the ceiling counts front matter and body |
| `main.tex` | 73,447 B |
| `main.pdf` | 748,688 B |
| Figures | 7 `figure` environments, 7 `\includegraphics`, all `width=1.0\linewidth` |
| Tables | 12, all inside `\footnotesize` (10 pt at this class's scale), none in `\scriptsize` |
| Display equations | 0 `\[ ... \]` blocks, one of which contains an `aligned` sub-environment |
| References | 13 items, 12 `\cite` calls, each item carrying a GB/T type marker |
| Sections / subsections | 12 / 17 |
| Source listings | 10 `\lstinputlisting` blocks in Appendix A |

## Structure

Summary sheet on page 1 (`\maketitle` writes it), contents on page 2, body from page 3 to
page 25, appendix from page 26 to page 87. The body runs
Introduction → A Unified View → Assumptions → Notations → Data Description → Q1 → Q2 → Q3 →
Sensitivity and Error Analysis → Strengths and Weaknesses → References, then Appendix A
reproduces the 10 scripts verbatim.

## Machine checks performed on this draft

- `xelatex` twice, both exit 0, zero `!` errors, zero `Overfull \hbox` above 10 pt.
- Every page from 3 onward carries `Team # SWBMCM2634892` and `Page n of 25`;
  the summary sheet and contents page carry no header, which is what the official demo does.
- No text span below 6 pt and no span touching the canvas edge in any of the six figure PDFs.
- `code/verify_numbers.py` binds 321 printed
  numbers and one printed band to JSON keys; 0 failures. Machine line: `claims=321 declared=321 checked=321 failures=0 verdict=PASS exit=0`.

## Writing conventions applied

1. Every number in the body is either quoted from `data/*.json` or derived from a quoted
   number in the same sentence; no number is introduced in prose alone.
2. Where a result is negative, the sentence says so in the same paragraph as the result. The
   change-point layer losing to a threshold baseline, the reliability layer failing at segment
   level, and the scheduling program trailing SLACK are each stated where they are measured,
   not deferred to a limitations section.
3. A figure caption describes only what the drawing contains; anything the drawing does not
   show is left to the body.
4. No sentence claims that a quantity is "the best" without naming the comparator and the sample.
5. Symbol names are introduced once, in the Notations table, and reused verbatim.
6. The third-party claims that motivated the within-gap experiment are credited as motivation
   and then re-measured here; the paper reports our numbers, not theirs.

VERDICT: PASS
