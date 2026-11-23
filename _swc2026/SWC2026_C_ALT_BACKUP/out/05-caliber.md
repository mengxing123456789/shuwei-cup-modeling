BYTES 4622
# Caliber audit — SWC2026_C_ALT_BACKUP

## Machine pass

`caliber_check.py` over `main.tex`: **hard items 0, warnings 0, VERDICT PASS**.
The machine check can only detect one class — the same numeric string carrying two
different unit suffixes in the same paper. Everything below is the part a machine
cannot see.

## The six classes a reader could confuse

**1. Page counts.** Three different denominators appear in this project and each
means something else. `submitted pages` = 111 (everything the reader receives);
`body pages` = 21 (summary and contents excluded, appendix excluded); `Page n of N`
inside the PDF = `n` over 109, which is the body-plus-appendix count with the two
unnumbered front pages removed. The paper prints only the first and the third. The
figure "21 body pages" appears in `out/10-layout.md` and nowhere in `main.tex`, so a
reader of the paper alone never sees it. No sentence mixes the three.

**2. Record, environment and segment.** A *record* is one episode directory; an
*environment* is a `environment_id` shared by several records; a *segment* is one
annotated interval inside a record. The counts are 69 records, 24 environments, 349
segments (343 eligible). The split is environment-level, 16/4/4, which is why the
test set is 7 records rather than a round number of records. Whenever the paper says
"test records" it means 7; whenever it says "validation environments" it means 4.

**3. `ρ` versus `θ`.** `θ` is the bad-frame rate and `ρ = 1 − θ` is the usable
probability. The retention rule is stated on `ρ` (`q_{0.025}(ρ) ≥ 0.90`) precisely
because stating it on `θ` would read as "keep the segments with the highest bad-frame
rate", which is the opposite of the intent. The first draft of this paper made that
mistake; it is corrected in the body and the correction is called out in place.

**4. Mask length `L` in seconds versus in frames.** The official protocol is stated
in seconds; the released helper `p2_predict.py` uses frames {6, 15, 30, 60}. At the
5 Hz analysis rate those are 1.2, 3.0, 6.0 and 12.0 s, which is not the set used
here. This paper uses seconds throughout, {0.2, 0.4, 0.6, 1.0} s, and never converts
to frames, so the two sets cannot be confused in the text — but a reader comparing
against the helper will find different numbers, and that is a difference of protocol,
not of result.

**5. Centimetres versus metres.** Every 3D error in this paper is in centimetres;
the state vectors are in metres (the head-frame panel is stored in metres and the
filter runs in metres). The conversion happens once, in `alt_p2_kalman.py`, and the
paper prints only centimetres.

**6. Percentage points versus percent.** The Q3 on-time differences are quoted as
absolute rates (`0.522` to `0.711`), not as relative improvements, because a relative
improvement of a rate that starts at 0.52 is easy to inflate. The one place a
relative figure appears — the `0.084` gain from re-planning — is labelled as a
difference of rates, not as a percentage.

## Conflicts found and resolved during this round

| Item | First draft | Measured | Resolution |
|---|---|---|---|
| Change-point trigger | "MAP run length drops to zero" | `P(r_t = 0)` never exceeds 0.119, so that rule fires almost never | rewritten as "falls below 30% of its running peak", which is what the code does |
| Free parameters | "the only free parameter is λ" | four: σ, λ, merge threshold, drop fraction | rewritten; three are read from training data, the fourth is set once |
| Reliability direction | `q_{0.05}(θ) ≥ 0.90` | sign reversed | rewritten on `ρ` |
| "strongest single result" | record-level AUC 0.914 presented as evidence the hierarchy helps | segment-level leave-one-out 0.675; within-record 0.076 | the claim is withdrawn and the mechanism explained |
| Q3 ranking | "raises on-time while cutting cost" | rolling beats EDF, trails SLACK, cost not uniformly lower | abstract rewritten around the measured ranking |

## Resolved this round: the chance level is now a measured curve

The earlier note that `ε` "was not swept" no longer holds. A six-level sweep
(`ε` in {0.20, 0.30, 0.40, 0.50, 0.60, 0.70}, 8 paired seeds, 135 cells,
728.9 s of solver time) and a train-only residual-bank ablation are recorded in
`data/alt_p3_sweep.json` and summarised in the body. Across all six levels and the
train-only bank the best policy stays `slack_old` (mean weighted on-time 0.821);
the rolling program peaks at 0.804 at `ε = 0.50`. No unmeasured "earlier run at
0.25" is cited anywhere; `code/verify_numbers.py` asserts the swept numbers.

VERDICT: PASS
