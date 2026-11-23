p=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_tables.py"
s=open(p,encoding="utf-8").read()
start=s.index("shape_rows = []")
end=s.index('w("tab_shape.tex"')
new = '''shape_rows = []
for c in CASES:
    rec = [q for q in p2["rows"] if q["case"] == c and abs(q["cn"] - 1.0) < 1e-9][0]
    sh = rec["shapes"]
    shape_rows.append(
        f"{c} & {sh['S1_sqrt']['r2']:.4f} & {sh['S2_exp']['r2']:.4f} & {sh['S3_power']['r2']:.4f} & "
        f"{sh['S3_power']['params']['nu']:.4f} & {sh['S2_exp']['params']['tau']:.3f} & "
        f"{sh['S1_sqrt']['resid_runs']} & {sh['S2_exp']['resid_runs']} \\\\\\\\"
    )

'''
s=s[:start]+new+s[end:]
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
