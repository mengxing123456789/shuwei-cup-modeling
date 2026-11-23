BYTES 2305
# Layout record — SWC2026_C_ALT_BACKUP

## Page budget

| Region | Physical pages | Note |
|---|---|---|
| Summary sheet | 1 | written by `\maketitle`, no header (matches the official demo) |
| Contents | 1 | `\tableofcontents`, no header (matches the official demo) |
| Body | 23 | pages 3–25, numbered `Page 1 of 25` through `Page 23 of 25` |
| Appendix A | 62 | pages 26–87, continues the same page counter |
| Total | 87 | |

The ceiling of 25 counts summary, contents and body: 1 + 1 + 23 = 25, leaving
0 pages of headroom. The appendix is unlimited under the same clause.

## Typographic checks

| Check | Result |
|---|---|
| `Overfull \hbox` above 10 pt in `main.log` | 0 |
| Undefined references / citations | 0 |
| Prose numerals written as digits where the style wants words | 0 |
| Fonts embedded | all, `Type3 = 0` |
| Smallest body type | 12 pt (class default); footnotes 10 pt; table bodies `\footnotesize` = 10 pt |
| Smallest in-figure type | 6.2 pt in the source, 6.2 pt in the PDF |
| Figure width | all 7 at `1.0\linewidth` = 416.5 pt, equal to the text width, so the scale factor is exactly 1.0 |
| Figure text touching the canvas edge | 0 spans across all 7 PDFs |

## Header and footer

Two lines at the top of every body and appendix page:

```
Team # SWBMCM2634892
Page n of 25
```

`n` is `\thepage` and 25 is `\pageref{LastPage}` minus the two unnumbered front pages. The
counter is reset to 1 at the start of the body (`\setcounter{page}{1}` after `\newpage`), which is why
the body's first page reads `Page 1 of 25` rather than `Page 3 of 87`. Without the reset the
body would start at `Page 3` and the `of N` value would be off by the two front pages.

## Known cosmetic items

- The contents page lists the appendix subsections at the same depth as body subsections; the
  official demo does the same.
- `\emergencystretch` is raised and the Sources paragraph is wrapped in `sloppypar`; both were
  needed to remove the last two overfull boxes, and neither changes the visible line breaking
  of the body prose.
- The body sits at 23 pages against a 25-page ceiling, so there is room for another figure or
  table without a re-layout; that headroom was used once already, to add the within-gap
  scheduling experiment (Table 9 and Figure 6).

VERDICT: PASS
