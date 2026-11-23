from pathlib import Path

p = Path(r"E:\数学建模\_swc2026\SWC2026_C\code\fill_numbers.py")
lines = p.read_text(encoding="utf-8").splitlines()

idx = None
for i, ln in enumerate(lines):
    if ln.strip() == "for key, section, what, producer in TODO_SLOTS:" and "OUT_SLOTS.write_text" in "\n".join(lines[i:i + 8]):
        idx = i
        break
assert idx is not None, "anchor not found"

block = r'''    # --- same-unit comparison of the two P2 predictors ---------------------
    # The appendix used to compare a per-coordinate GRU error with a
    # three-dimensional ridge error and call the ratio "times better".
    # sqrt(3) relates the two units; both are derived here so the
    # paragraph cannot drift away from the data.
    _s3 = 3.0 ** 0.5
    _gru = {k: float(RAW["PGPU" + k + suf]) for k, suf in
            (("A", "WristRMSE"), ("B", "STwoRMSE"), ("C", "BothRMSE"), ("D", "BothRMSE"))}
    _rdg = {k: float(RAW["PTwo" + k + "RidgeRMSE"]) for k in "ABCD"}
    _same_unit = []
    for _k in "ABCD":
        _same_unit.append(("PGpu" + _k + "ThreeD", "f2", _gru[_k] * _s3))
        _same_unit.append(("PRidge" + _k + "PerCoord", "f2", _rdg[_k] / _s3))
    for _k in "CD":
        _same_unit.append(("PGpuWin" + _k + "PerCoordPct", "f1",
                           100.0 * (_rdg[_k] / _s3 - _gru[_k]) / (_rdg[_k] / _s3)))
    _same_unit.append(("PGpuAPerCoordGapPct", "f1",
                       100.0 * (_gru["A"] - _rdg["A"] / _s3) / (_rdg["A"] / _s3)))
    for _name, _tag, _val in _same_unit:
        lines.append("% [calc] same-unit comparison, p2_prediction / p2_gpu")
        lines.append(r"\newcommand{\slot" + _name + "}{" + fmt_value(_val, _tag) + "}")
        count += 1
'''

out = lines[:idx] + block.splitlines() + lines[idx:]
p.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("inserted before line", idx + 1)
