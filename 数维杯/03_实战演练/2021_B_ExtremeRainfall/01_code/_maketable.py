import sys
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
import common as C, pandas as pd
q2 = pd.read_csv(C.RESULTS/"q2_city_trends.csv").sort_values(["belt","city"])
rows=[]
for _,r in q2.iterrows():
    city = r["city"].replace(", Ch","")
    rows.append(f'{city} & {r["lat"]:.2f} & {r["lon"]:.2f} & {int(r["n_years"])} & {r["mean_total"]:.0f} & {r["mean_rx1day"]:.1f} \\\\')
body = "\n".join(rows)
tex = r"""\begin{longtable}{lrrrrr}
\caption{Stations of the national panel: latitude, longitude, valid years in 1961--2020, mean annual total and mean annual maximum one-day rainfall.}\label{tab:stations}\\
\toprule
City & Lat & Lon & Years & Total (mm) & Rx1day (mm)\\
\midrule
\endfirsthead
\toprule
City & Lat & Lon & Years & Total (mm) & Rx1day (mm)\\
\midrule
\endhead
\bottomrule
\endfoot
""" + body + "\n\\end{longtable}\n"
(C.ROOT/"04_paper"/"station_table.tex").write_text(tex, encoding="utf-8")
print("cities", len(rows))
print(tex[:400])
