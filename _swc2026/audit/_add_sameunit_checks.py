from pathlib import Path

p = Path(r"E:\数学建模\_swc2026\audit\verify_claims.py")
t = p.read_text(encoding="utf-8")

anchor = '    out = AUD / "verify_claims.json"'
assert t.count(anchor) == 1

block = r'''    # --- same-unit comparison of the two P2 predictors ---------------------
    _S2 = slots()
    _s3 = 3.0 ** 0.5
    _gru_a = num(_S2["PGPUAWristRMSE"])
    _gru_a3 = num(_S2["PGpuAThreeD"])
    check("GRU 逐坐标误差换算三维=×√3（附录同单位段）",
          near(_gru_a3, _gru_a * _s3, 0.011),
          f"3D={_gru_a3} per-coord={_gru_a} ×√3={_gru_a*_s3:.3f}", round(_gru_a * _s3, 2), _gru_a3)
    _rdg_a = num(_S2["PTwoARidgeRMSE"])
    _rdg_pc = num(_S2["PRidgeAPerCoord"])
    check("ridge 三维误差换算逐坐标=÷√3（附录同单位段）",
          near(_rdg_pc, _rdg_a / _s3, 0.011),
          f"per-coord={_rdg_pc} 3D={_rdg_a} ÷√3={_rdg_a/_s3:.3f}", round(_rdg_a / _s3, 2), _rdg_pc)
    _pairs = [("C", "PGpuCThreeD", "PTwoCRidgeRMSE", "PGpuWinCPerCoordPct"),
              ("D", "PGpuDThreeD", "PTwoDRidgeRMSE", "PGpuWinDPerCoordPct")]
    _ok = True
    _det = []
    for _tag, _g3, _r3, _pct in _pairs:
        _gv, _rv, _pv = num(_S2[_g3]), num(_S2[_r3]), num(_S2[_pct])
        _want = 100.0 * (_rv - _gv) / _rv
        _ok = _ok and near(_pv, _want, 0.06)
        _det.append(f"{_tag}: {_pv} vs {_want:.2f}")
    check("C/D 掩码的百分比增益在两种单位下一致（同一比值）", _ok, "; ".join(_det), "match", _ok)
    check("附录同单位段写明 both units 并已删除旧的 times-better 说法",
          ("in both units" in main_text) and ("times better than the" not in main_text),
          "main.tex", True, "in both units" in main_text)

'''

t = t.replace(anchor, block + anchor)
p.write_text(t, encoding="utf-8", newline="\n")
print("patched verify_claims.py")
