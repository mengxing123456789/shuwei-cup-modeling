"""Add five checks covering the reservation-level identifiability paragraph."""
import io
import os

AUD = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(AUD, "verify_claims.py")

BLOCK = r'''
    # --- reservation-level identifiability (p3_quantile_curve.json) ----------
    _S = slots()
    _q = load_json("p3_quantile_curve.json")
    _grid = _q["_meta"]["q_grid"]
    check("q 网格左端与 slot 一致", near(num(_S["PQSweepLow"]), _grid[0], 1e-9),
          f"slot={_S['PQSweepLow']} grid[0]={_grid[0]}", _grid[0], num(_S["PQSweepLow"]))
    check("q 网格右端与 slot 一致", near(num(_S["PQSweepHigh"]), _grid[-1], 1e-9),
          f"slot={_S['PQSweepHigh']} grid[-1]={_grid[-1]}", _grid[-1], num(_S["PQSweepHigh"]))
    _tc = [float(x) for x in _q["cases"]["S2"]["tune_curve"]]
    _mono = all(b <= a + 1e-12 for a, b in zip(_tc, _tc[1:]))
    check("S2 调优曲线随 q 单调不增（过度预留是失效模式）", _mono,
          "tune_curve S2 monotone non-increasing", True, _mono)
    _hc = [float(x) for x in _q["cases"]["S2"]["holdout_curve"]]
    _flatter = (max(_hc) - min(_hc)) < (max(_tc) - min(_tc))
    check("S2 留出曲线比调优曲线更平（水平弱可辨识）", _flatter,
          f"hold span={max(_hc)-min(_hc):.4f} tune span={max(_tc)-min(_tc):.4f}", True, _flatter)
    _phrase = "the plateau, not a point" in main_text
    check("正文写明平台而非点估计", _phrase, "main.tex", True, _phrase)

'''

ANCHOR = '    out = AUD / "verify_claims.json"'


def main():
    t = io.open(P, encoding="utf-8").read()
    assert t.count(ANCHOR) == 1, t.count(ANCHOR)
    t = t.replace(ANCHOR, BLOCK.lstrip("\n") + ANCHOR)
    io.open(P, "w", encoding="utf-8", newline="\n").write(t)
    print("inserted; bytes", os.path.getsize(P))


if __name__ == "__main__":
    main()