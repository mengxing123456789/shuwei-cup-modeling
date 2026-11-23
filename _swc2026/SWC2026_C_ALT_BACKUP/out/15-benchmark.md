BYTES 1178
# Benchmark against the ShuWei Cup corpus (backup paper)

## Corpus query record

- Corpus: `E:\数学建模\.mh\corpus.json`, 318,958 bytes, `built_at 2026-11-19T03:35:35Z`.
- 195 records, all `contest = 数维杯`; types: paper 124, problem 58, data 9, appendix 4; years 2019–2025.
- Queries via `corpus_index.py`: `restock` 0, `shelf` 0, `unmanned supermarket` 0 — no precedent paper for this exact task.
- Neighbouring queries: `inventory` 8, `missing observation` 10, `pose estimation` 18.

## Benchmark set

`refs/official_standard.json` is the 48-paper ShuWei Cup set (49,027 bytes, `n_papers=48`, `n_first_prize_verified=0` because the prize labels are folder-level, not verified per team). Medians: 7,943.5 words, 446.5 abstract words, 14 figures, 5 tables, 14 equations, 8 references, 8.5 sections.

## Target profile for this paper

As a backup paper we aim at the same band as the main paper: English, at most 25 submitted pages including abstract and contents, at least 12-point body type, source code in the appendix. The paper is written against the same 48-paper yardstick so that a reader can compare the two submissions directly.

VERDICT: PASS
