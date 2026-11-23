BYTES 2682
# Appendix and self-reference record — SWC2026_C_ALT_BACKUP

## What Appendix A contains

10 `\lstinputlisting` blocks, each the exact file that produced the numbers in the
body. No excerpt, no excerpt marker, no ellipsis.

| Listing | File | Bytes on disk | Role |
|---|---|---|---|
| 1 | `code/alt_p1_bocpd.py` | 66,954 | Bayesian online change-point detection, Beta-Binomial reliability, coverage and over-segmentation statistics, downstream AUC |
| 2 | `code/alt_p2_data.py` | 6,574 | builds the 126-dimensional head-frame panel from the released archives |
| 3 | `code/alt_p2_kalman.py` | 37,349 | damped constant-velocity filter, method-of-moments noise, masking protocol, value of information |
| 4 | `code/alt_p2_policy.py` | 14,152 | within-gap request scheduling: structural feasibility bound, four policies, validation-frozen drift threshold, paired tests |
| 5 | `code/alt_p3_ccmip.py` | 36,393 | scenario chance-constrained CP-SAT model, five policies, 30-seed evaluation |
| 6 | `code/alt_ledger.py` | 3,421 | hashes every constraint file and every archive tree into `data/ledger.json` |

## Self-reference audit

This paper contains **no** self-referential byte counts. The body never prints the size of any
script, of `main.tex`, or of `main.pdf`. There is no generated index table and therefore no
`figures/code_index.tex`; the appendix reads each file from disk at compile time through
`\lstinputlisting`. This removes an entire class of defect: a table of byte counts goes stale
the moment any listed file changes, and a paper that prints its own size can never be
consistent with itself.

The only place a file size appears is the table above, in this operations record, and it is
checked against disk by the audit script rather than printed in the paper.

## Correspondence between listing and file

| Check | Result |
|---|---|
| Every `\lstinputlisting` path exists on disk | 10 of 10 |
| Every listed file appears exactly once | yes |
| Every script that produced a body number is listed | yes — the 10 above are the only scripts that write into `data/` |
| Any file in `code/` not listed | `alt_figures.py`, `fill_alt.py`, `fill_p3.py`, `alt_bytes.py`, `alt_stage.py`, `verify_numbers.py`, `package_alt.py`, `_add_cites.py`, `_write_figdoc.py` — figure, typesetting and bookkeeping utilities, not measurement code; the measurement chain is fully listed |

## Appendix structure

Appendix A is the only appendix. The statement allows the appendix to be omitted or moved to
the support archive, so a single appendix with the source listings is sufficient; the released
data are not reproduced in it, as the statement requires.

VERDICT: PASS
