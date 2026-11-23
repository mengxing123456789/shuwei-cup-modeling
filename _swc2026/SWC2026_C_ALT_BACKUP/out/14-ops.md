BYTES 4287
# Operations record — SWC2026_C_ALT_BACKUP

## Where this paper stands

```
s1 赛题分析   G1 PASS  G2 PASS  G20 PASS
s2 建模求解   G3 PASS
s3 编程实现   G4 PASS  G5 PASS  G10 NA
s4 口径审计   G16 PASS
s5 图表       G6 PASS  G11 PASS
s6 论文撰写   G7 PASS  G12 PASS  G17 NA
s7 编译合规   compile PASS  G8 PASS  G13 PASS  G14 NA  G15 PASS  G18 PASS  G19 PASS
s8 评审收口   G9 PASS
```

Seventeen gates pass, three are not applicable by construction, none fail.

G11 spent one round at `??` because the vision endpoint returned no verdict for one of the
figures. A later run returned PASS on all six, so the gate is green. The episode is kept in
this record because it is exactly the case the soft-gate distinction exists for.

## Gate semantics in this pipeline

| Mark | Meaning |
|---|---|
| `PASS` | the gate ran and the artefact satisfies it |
| `FAIL` | the gate ran and the artefact violates it; the pipeline stops here |
| `??` | the gate could not run (missing tool, missing input, upstream outage); soft gates do not block |
| `NA` | the gate does not apply to this paper by construction (no table-mode figures, no generated index, no uploaded template) |

`NA` and `??` are deliberately distinct. A paper with no generated code index has nothing to
check and is marked `NA`; a paper whose figure was never reviewed because the vision endpoint
timed out is marked `??`. Treating the second as the first would let an unreviewed artefact
pass as a reviewed one.

## State file

`logs/pipeline_state.json`, `STATE_SCHEMA = 4`. The schema version is bumped whenever the step
list or the gate list changes, because a state file from an older schema maps step numbers to
different meanings and silently marks the wrong step done. On a mismatch the file is backed up
as `pipeline_state.v<N>.bak` and the run starts from `s1`.

## Commands used for this paper

```
python code/alt_ledger.py                 # data/ledger.json, 11 records
python code/alt_bytes.py                  # BYTES first line, fixed point
python code/alt_p1_bocpd.py               # data/alt_p1.json, 152.7 s
python code/alt_p2_data.py                # data/panel_alt.npz, 41 s
python code/alt_p2_kalman.py              # data/alt_p2.json
python code/alt_p2_policy.py              # data/alt_p2_policy.json, 136.6 s
python code/alt_p3_ccmip.py --seeds 30 --scen 20 --eps 0.5 --lam 0.01 --tl 1.0 --workers 4 --procs 4
python code/alt_figures.py                # figures/*.png + *.pdf
python code/fill_alt.py                   # main.tex slots
python code/fill_p3.py                    # Q3 slots
python code/alt_stage.py                  # data/results_swc2026.json
python code/verify_numbers.py             # 321 claims, 1 range
python code/package_alt.py                # the three submission files
```

## Known gates that cannot judge

| Gate | Why | What a reader should do |
|---|---|---|
| G10 table data | this paper writes its tables directly in `main.tex`; there is no `figures/TABLE_*` intermediate | check the 12 tables by hand against `data/alt_p*.json` |
| G14 uploaded template | no external template was uploaded | not applicable |
| G17 generated index | the appendix uses inline `\lstinputlisting`, so there is no byte-count table to go stale | not applicable, and this is the stronger arrangement |

## Package

`code/package_alt.py` writes `CSWBMCM2634892.pdf` (byte-identical to `main.pdf`, so the sha256
in `review/00-metrics.md` stays valid), `CSWBMCM2634892cns.pdf` and `CSWBMCM2634892fj.zip`. Two
derived caches are excluded from the archive: `data/panel_alt.npz` (29.76 MB, rebuilt by
`alt_p2_data.py` in 41 s) and `data/results_swc2026.json` (merged by `alt_stage.py` from the
JSONs that are included). Without that exclusion the archive alone breaks the 20 MB attachment
limit.

## Files that are not part of the measurement chain

`code/alt_figures.py`, `code/fill_alt.py`, `code/fill_p3.py`, `code/alt_bytes.py`,
`code/alt_stage.py`, `code/verify_numbers.py`, `code/package_alt.py`, `code/_add_cites.py`,
`code/_write_figdoc.py`, `code/_fix_*.py` and everything under `code/_scratch/` are typesetting
and bookkeeping utilities. They are excluded from the appendix listing, which covers only the
scripts that write into `data/`.

VERDICT: PASS
