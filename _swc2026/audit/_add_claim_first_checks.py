"""Five checks for the claim-first round: the answer table, the rejected-moves table and the
cost-threshold paragraph, all tied back to the JSON that owns the numbers."""

import io
import os
import re

F = r"E:\数学建模\_swc2026\audit\verify_claims.py"
t = io.open(F, encoding="utf-8", newline="").read()

anchor = '    # ---------- text-level checks ----------'
assert t.count(anchor) == 1, "anchor: %d" % t.count(anchor)

BLOCK = r'''    # ---------- claim-first round: answers, rejected moves, threshold cost ----------
    _sv = slots()

    def _num(x):
        try:
            return float(str(x).replace("$", "").replace("\\,", "").strip())
        except Exception:
            return None

    check("tab:answers present with three rows",
          main_text.count("\\label{tab:answers}") == 1
          and all(k in main_text for k in ("P1: is the hand state recoverable",
                                           "P2: does a request buy information",
                                           "P3: what is the truth worth")),
          "the three questions are answered in a table before the derivation")

    _cost = load("p1b_cost_threshold.json")
    _der = _cost["_derived"]
    check("cost-threshold slots match the JSON",
          abs((_num(_sv["slotPCostKeepAll"]) or -1) - _der["cost_keep_all_at_r1"]) < 1e-4
          and abs((_num(_sv["slotPCostHalfMult"]) or -1) - _der["half_rule_multiple"]) < 0.06
          and abs((_num(_sv["slotPCostRatioHigh"]) or -1) - _der["ratio_max"]) < 1e-6,
          "keep-all, the half-rule multiple and the ratio range come from the JSON")

    check("no interior threshold is ever optimal",
          _der["n_interior_optima"] == 0 and "selects an interior" in main_text,
          "the claim in the text is the claim in the JSON")

    check("tab:negatives lists the rejected moves",
          main_text.count("\\label{tab:negatives}") == 1
          and "What was tried, measured and rejected" in main_text,
          "one table of rejected moves, kept in the appendix so the body budget holds")

    check("the recommended threshold is withdrawn",
          "the operating point we recommend" not in main_text,
          "the sentence that recommended a tau is gone, replaced by the cost minimisation")

'''

t = t.replace(anchor, BLOCK + anchor)
io.open(F, "w", encoding="utf-8", newline="\n").write(t)
print("patched", os.path.getsize(F))