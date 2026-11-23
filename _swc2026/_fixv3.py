p=r"E:\数学建模\_swc2026\SWC2026_A\code\verify_numbers.py"
s=open(p,encoding="utf-8").read()
s=s.replace('close("golden_vector_subtotal", t["subtotal"], 848.25, 1e-2)','close("golden_vector_subtotal", t["subtotal_wan"], 848.25, 1e-2)')
s=s.replace('close("golden_m_nano", t["m_nano"], t["Cn"] * 1e-2 * t["Vinj"], 1e-9)','close("golden_m_nano", t["m_nano_t"], t["cn_levels"][2] * 1e-2 * t["Vinj"], 1e-9)')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
