import os
# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Third borrowed analysis: marginal value is not monotone.

The ALT draft proves that in a linear-Gaussian filter the posterior trace does not
depend on the observations, so the second look is worth exactly as much as the
first and the optimal policy has no interior solution. Our engine reaches the
same verdict empirically (270 cells, none passes), but the *mechanism* we can
state is different and stronger: the value of an information increment is not
monotone in the size of the increment.

`data/up2_p3review.json` already holds the ceiling of a free, instantaneous,
unlimited perfect prefix at two disclosure lengths (6 and 10 extra frames) and of
the full-duration oracle, each maximised over the reservation quantile. If the
ceiling were monotone in the disclosure, the longer free prefix would dominate.
It does not: the longer prefix is worth *less* in every case.

This script only re-expresses those numbers as marginal values, so the paper can
state the non-monotonicity without a new simulation.
"""
import io, json, os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def main():
    d = json.loads(io.open(os.path.join(DATA, "up2_p3review.json"),
                           encoding="utf-8").read())
    ceil = d["information_ceiling"]
    best = ceil["best_by_case"]

    rows = {}
    for case in ("S1", "S2", "S3"):
        b = best[case]
        f6 = b["free6"]["max_delta_pt"]
        f10 = b["free10"]["max_delta_pt"]
        tr = b["true"]["max_delta_pt"]
        rows[case] = dict(
            free6_pt=f6, free10_pt=f10, true_pt=tr,
            marginal_second_pt=f10 - f6,
            ratio_second_over_first=(f10 / f6) if abs(f6) > 1e-12 else None,
            non_monotone=bool(f10 < f6),
            q_at_free6=b["free6"]["at_q"], q_at_free10=b["free10"]["at_q"],
        )

    # the two-case statement the paper will make (S2 and S3 are the ones the
    # paper schedules; S1 saturates and is reported but not argued on)
    s2, s3 = rows["S2"], rows["S3"]
    out = dict(
        _meta=dict(
            source="data/up2_p3review.json information_ceiling",
            definition=("ceiling of a free, instantaneous, unlimited perfect prefix at "
                        "6 and 10 extra frames, and of the full-duration oracle, each "
                        "maximised over the reservation quantile q"),
            claim=("the value of an information increment is not monotone in the "
                   "increment: the longer free prefix is worth less in every case"),
        ),
        cases=rows,
        n_non_monotone=sum(1 for r in rows.values() if r["non_monotone"]),
        s2_second_pt=s2["marginal_second_pt"],
        s3_second_pt=s3["marginal_second_pt"],
        s2_first_pt=s2["free6_pt"],
        s3_first_pt=s3["free6_pt"],
        gate_pt=ceil["gate_pt"],
        true_max_pt=ceil["true_max_pt"],
    )
    with io.open(os.path.join(DATA, "up20_marginal_info.json"), "w",
                 encoding="utf-8", newline="") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()