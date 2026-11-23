import pathlib, sys
P = pathlib.Path("audit/verify_claims.py"); s = P.read_text(encoding="utf-8")
anchor = """    out = AUD / "verify_claims.json\""""
if s.count(anchor) != 1:
    print("MISS anchor", s.count(anchor)); sys.exit(1)
block = '''    # ---- 新增：§2.5 统一记号与三个命题、闭式解的 conditional-on-s 限定 ----
    has_notation = r"\\label{sec:notation}" in tex
    check("给出一节统一记号", has_notation, "sec:notation", True, has_notation)
    props = [
        ("相位命题指向正文检验", r"tested and refuted in Section~\\ref{sec:p1res}"),
        ("reservation 命题指向推导", r"derived in Section~\\ref{sec:p3closed}"),
        ("前缀信息命题指向上界测量", r"measured in Section~\\ref{sec:p2res}"),
    ]
    for nm, lit in props:
        check(nm, lit in tex, lit, True, lit in tex)
    cond = r"but only conditional on $s$" in tex
    check("闭式解标注 conditional on s", cond, "main.tex", True, cond)
    not_ceil = r"we do not" in tex and r"call the reference an upper bound" in tex
    check("不把 reference 叫上界", not_ceil, "main.tex", True, not_ceil)

'''
s = s.replace(anchor, block + anchor)
P.write_text(s, encoding="utf-8", newline="\n")
print("appended notation checks")
