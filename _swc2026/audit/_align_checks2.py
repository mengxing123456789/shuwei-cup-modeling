# AI 辅助：DeepSeek Harness 助手生成的第二轮对齐补丁（限定在 reference 块内替换）。
# -*- coding: utf-8 -*-
"""Second alignment pass.

`sys` is rebound by a later `import sys` inside main(), so any bare `sys` earlier
in the same function is an unbound local.  Reach the module through importlib
instead, and scope the edit to this block so the older simulator check (which
already works) is untouched.  Also loosen two identity tolerances from 1e-6 to
1e-4: the slot carries four decimals by construction.
"""
from pathlib import Path

V = Path(r"E:\数学建模\_swc2026\audit\verify_claims.py")
F = Path(r"E:\数学建模\_swc2026\SWC2026_C\code\fill_numbers.py")

v = V.read_text(encoding="utf-8")

anchor = "# The paper's reference is \"the same rule run with p known\""
i = v.index(anchor)
j = v.index("except Exception as exc:  # noqa: BLE001", i)
head, body, tail = v[:i], v[i:j], v[j:]

old_sys = '        sys.path.insert(0, str(C / "code"))'
assert body.count(old_sys) == 1, f"sys line in block: {body.count(old_sys)}"
body = body.replace(
    old_sys,
    '        importlib.import_module("sys").path.insert(0, str(C / "code"))',
    1,
)
old_imp = "        import p3_stochastic_schedule as p3sim_ref  # type: ignore"
assert body.count(old_imp) == 1, "module import in block"
body = body.replace(
    old_imp,
    '        p3sim_ref = importlib.import_module("p3_stochastic_schedule")',
    1,
)
v = head + body + tail

for old, new, tag in (
    ("near(cov, _emp, 1e-6)", "near(cov, _emp, 1e-4)", "coverage tol"),
    ("near(headline2, sel2, 1e-6)", "near(headline2, sel2, 1e-4)", "headline tol"),
):
    n = v.count(old)
    assert n == 1, f"{tag}: matched {n}"
    v = v.replace(old, new, 1)

V.write_text(v, encoding="utf-8", newline="\n")

f = F.read_text(encoding="utf-8")
kept, dropped = [], []
for ln in f.split("\n"):
    s = ln.strip()
    if (
        s.startswith('add("PAdaptImplGapMean"')
        or s.startswith('add("PAdaptAlphaCostMean"')
        or s.startswith('add("PAdaptRegretMax"')
    ):
        dropped.append(s)
        continue
    kept.append(ln)
assert len(dropped) == 3, f"expected 3 PAdapt definitions, got {len(dropped)}"
F.write_text("\n".join(kept), encoding="utf-8", newline="\n")
print("verify_claims.py: 4 edits; fill_numbers.py dropped:")
for d in dropped:
    print("  -", d)