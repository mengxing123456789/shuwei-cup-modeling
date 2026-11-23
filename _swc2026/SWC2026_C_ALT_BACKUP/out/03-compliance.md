BYTES 3278
# Compliance record — SWC2026_C_ALT_BACKUP

## The seven official clauses

Source: `2025年第十一届数维杯…（秋季赛）论文格式规范.pdf` (3 pages) plus the 2026
autumn `demo.tex`, whose own text requires English and "a readable font of at least
12-point type".

| Clause | Requirement | This draft | Verdict |
|---|---|---|---|
| 1 | Choose exactly one of A/B/C/D; the problem number must match the content | `\zubie{C}`; every section is about restocking under uncertain observation | pass |
| 2 | Title, summary and keywords on page 1; page 2 is the contents page only; body after | `\maketitle` writes the summary sheet on page 1, `\tableofcontents` fills page 2, body starts page 3 | pass |
| 3 | Every body page carries the team number and a page number, e.g. `Team A…, Page 1 of 5` | pages 3–111 each carry `Team # SWBMCM2634892` and `Page n of 109`; page 1 and 2 carry no header, as the official demo does | pass |
| 4 | English, 12 pt Times New Roman, at most 25 pages including summary and contents; appendix unlimited | English throughout; class loads at 12 pt; 111 submitted pages of which 21 are body (88 appendix pages, unlimited) — inside the ceiling | pass |
| 5 | References numbered in citation order, bracketed, with a type marker | 8 `\bibitem`, cited in order, each with `[M]`, `[J]` or `[EB/OL]` | pass |
| 6 | Appendix carries the software name, the commands and the runnable source; released data must not be reproduced | Appendix A lists 11 scripts verbatim; the interpreter and package set are named in `out/12-training.md`; no released data appears in the appendix | pass |
| 7 | No identity or institution in body or appendix | searched: no name, no university, no phone, no email, no city | pass |

## Additional submission rules (from the 2025 submission-flow document)

| Rule | This draft |
|---|---|
| Paper file name `problem+team.pdf` | `CSWBMCM2634892.pdf` |
| Commitment letter `problem+team+cns`, hand-signed or e-signed | `CSWBMCM2634892cns.pdf` — signature is the author's step, not the pipeline's |
| Support archive `problem+team+fj`, rar/zip, optional | `CSWBMCM2634892fj.zip` |
| Attachments under 20 MB recommended | measured after packaging |
| No Chinese anywhere, including inside figures | 0 CJK characters in `main.tex`; 0 CJK spans in the six figure PDFs |
| Must press submit until the system says 已提交 | author's step |

## Machine checks

- `review_bench.check_paper`: 11 findings, 0 fail (C4 both sentences true, C5 header
  lines matched on every body page, C6 page count inside limit, C7 zero CJK, C8 nine
  type markers, C9 appendix listings present, C11 team number consistent).
- `page_report`: overfull 0, undefined references 0, prose numerals 0.
- `pdffonts`: every font embedded, Type3 count 0.
- `code/verify_numbers.py`: 221 claims, 0 failures (60 of them bind the Q3 table cell by cell).

## Not verified by this record

The 2026 autumn notice itself is not on this machine; the page ceiling, the language
requirement and the commitment-letter rule are taken from the 2025 autumn regulation
and from the 2026 template's own `demo.tex`, both of which are present and quoted
above. If the 2026 notice changes any of them, this table needs one row updated.

VERDICT: PASS
