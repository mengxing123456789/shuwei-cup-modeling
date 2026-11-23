p=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_tables.py"
s=open(p,encoding="utf-8").read()
old='''    v = opt[k]
    nrows.append(
        f"{c} & {v['npv_at_5']/1e4:.1f} & {v['npv_max']/1e4:.1f} & {v['npv_at_30']/1e4:.1f} & "
        f"{v['ts_grid']} & {v['ts_closed']:.2f} & {v['band_2pct'][0]}--{v['band_2pct'][1]} \\\\\\\\"
    )'''
new='''    v = opt[k]
    w2 = p4["optimum_two_calibers"][k]
    nrows.append(
        f"{c} & {v['npv_at_5']/1e4:.1f} & {v['npv_max']/1e4:.1f} & {v['npv_at_30']/1e4:.1f} & "
        f"{w2['ts_data_grid']:.0f} & {w2['ts_continuous']:.2f} & {v['band_2pct'][0]}--{v['band_2pct'][1]} \\\\\\\\"
    )'''
assert old in s
s=s.replace(old,new)
s=s.replace('$t_s^\\\\ast$ grid (d)','$t_s^\\\\ast$ design grid (d)')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
