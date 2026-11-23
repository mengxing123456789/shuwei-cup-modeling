p=r"E:\数学建模\_swc2026\SWC2026_A\code\verify_numbers.py"
s=open(p,encoding="utf-8").read()
s=s.replace('close("golden_Vaq", t["Vaq"], t["Vinj"] * t["fCO2"], 1e-9)','close("golden_Vaq", t["Vaq"], 3000.0 * 0.5, 1e-9)')
s=s.replace('close("golden_m_nano", t["m_nano_t"], t["cn_levels"][2] * 1e-2 * t["Vinj"], 1e-9)','close("golden_m_nano", t["m_nano_t"], 1.0 * 1e-2 * 3000.0, 1e-9)')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
