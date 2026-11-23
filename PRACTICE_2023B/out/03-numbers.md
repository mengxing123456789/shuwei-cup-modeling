BYTES 33837

# 03-numbers：main.tex 数字 ↔ data/*.json 对账

> 每条结论的 JSON 键路径见 **附录 A**（正文只此一句指针，不重复抄键路径）。

- 生成：`verify_numbers.py`
- 退出码：0
- 声明条数 claims=547；实检查 declared=547 checked=547
- JSON 侧：通过 547，失败 0
- 正文侧：声明 needle 145 条，命中 145 条
- main.tex 状态：**written**（挖掉队号/页码/文献宽度与 `<<...>>` 后剩 1053 个结果数字 token）
- main.tex：687 行 / 64777 字节，非注释区数字 token 1214 个，`<<...>>` 占位符 0 个

## 1 结论

全部声明通过：JSON 侧逐条重算与存储值一致，正文侧每个 needle 都在 main.tex 里按词边界命中。

### 骨架判据（为什么这一轮正文侧可以缓期）

main.tex 已是 **written** 状态（1053 个结果数字 token），骨架豁免不适用。声明的 needle 必须全部命中。

常见未命中原因：正文把 2 位小数写成 1 位或反过来 —— `needle_forms` 已同时接受 2 位与 1 位写法，仍不命中说明**数值不同**，要改的是正文而不是 needle。

## 2 分组总表

| 组 | 声明 | JSON 通过 | 正文 needle | 正文命中 |
|---|---|---|---|---|
| A matcher self-test | 8 | 8 | 0 | 0 |
| B ledger | 11 | 11 | 0 | 0 |
| C q1 ledger | 12 | 12 | 0 | 0 |
| D q1 CE/Char | 12 | 12 | 5 | 5 |
| D q1 CE/Syngas | 12 | 12 | 5 | 5 |
| D q1 CE/Tar | 12 | 12 | 5 | 5 |
| D q1 CE/Water | 12 | 12 | 5 | 5 |
| D q1 CS/Char | 12 | 12 | 2 | 2 |
| D q1 CS/Syngas | 12 | 12 | 5 | 5 |
| D q1 CS/Tar | 12 | 12 | 5 | 5 |
| D q1 CS/Water | 12 | 12 | 5 | 5 |
| D q1 LG/Char | 12 | 12 | 3 | 3 |
| D q1 LG/Syngas | 12 | 12 | 5 | 5 |
| D q1 LG/Tar | 12 | 12 | 5 | 5 |
| D q1 LG/Water | 12 | 12 | 5 | 5 |
| E q1 ilr CE | 6 | 6 | 3 | 3 |
| E q1 ilr CS | 6 | 6 | 2 | 2 |
| E q1 ilr LG | 6 | 6 | 3 | 3 |
| F q2 ledger | 19 | 19 | 0 | 0 |
| G q2 CE/C2H6 | 9 | 9 | 2 | 2 |
| G q2 CE/CH4 | 9 | 9 | 2 | 2 |
| G q2 CE/CO | 9 | 9 | 2 | 2 |
| G q2 CE/CO2 | 9 | 9 | 2 | 2 |
| G q2 CE/H2 | 9 | 9 | 2 | 2 |
| G q2 CS/C2H4 | 9 | 9 | 1 | 1 |
| G q2 CS/C2H6 | 9 | 9 | 1 | 1 |
| G q2 CS/C3H6 | 9 | 9 | 1 | 1 |
| G q2 CS/C3H8 | 9 | 9 | 1 | 1 |
| G q2 CS/C4H10 | 9 | 9 | 1 | 1 |
| G q2 CS/CH4 | 9 | 9 | 2 | 2 |
| G q2 CS/CO | 9 | 9 | 2 | 2 |
| G q2 CS/CO2 | 9 | 9 | 2 | 2 |
| G q2 CS/H2 | 9 | 9 | 2 | 2 |
| G q2 LG/C2H6 | 9 | 9 | 1 | 1 |
| G q2 LG/CH4 | 9 | 9 | 2 | 2 |
| G q2 LG/CO | 9 | 9 | 2 | 2 |
| G q2 LG/CO2 | 9 | 9 | 2 | 2 |
| G q2 LG/H2 | 9 | 9 | 1 | 1 |
| H q2 rowsum CE | 3 | 3 | 0 | 0 |
| H q2 rowsum CS | 3 | 3 | 0 | 0 |
| H q2 rowsum LG | 3 | 3 | 0 | 0 |
| I q2 bridge CE | 3 | 3 | 2 | 2 |
| I q2 bridge CS | 3 | 3 | 2 | 2 |
| I q2 bridge LG | 3 | 3 | 2 | 2 |
| J q3 Char | 6 | 6 | 1 | 1 |
| J q3 Syngas | 6 | 6 | 1 | 1 |
| J q3 Tar | 6 | 6 | 1 | 1 |
| J q3 Water | 6 | 6 | 1 | 1 |
| K q3 C2H6 | 2 | 2 | 1 | 1 |
| K q3 CH4 | 2 | 2 | 1 | 1 |
| K q3 CO | 2 | 2 | 1 | 1 |
| K q3 CO2 | 2 | 2 | 1 | 1 |
| K q3 H2 | 2 | 2 | 1 | 1 |
| K q3 flips | 1 | 1 | 0 | 0 |
| L q4 carbon CE | 2 | 2 | 2 | 2 |
| L q4 carbon CS | 2 | 2 | 1 | 1 |
| L q4 carbon LG | 2 | 2 | 2 | 2 |
| L q4 gamma CE | 5 | 5 | 4 | 4 |
| L q4 gamma CS | 5 | 5 | 4 | 4 |
| L q4 gamma LG | 5 | 5 | 3 | 3 |
| M q4 kinetics | 10 | 10 | 2 | 2 |
| N q5 grid | 9 | 9 | 7 | 7 |
| O q5 CE | 3 | 3 | 0 | 0 |
| O q5 CE/Char | 3 | 3 | 1 | 1 |
| O q5 CE/Syngas | 3 | 3 | 1 | 1 |
| O q5 CE/Tar | 3 | 3 | 1 | 1 |
| O q5 CE/Water | 3 | 3 | 1 | 1 |
| O q5 CS | 3 | 3 | 0 | 0 |
| O q5 CS/Char | 3 | 3 | 0 | 0 |
| O q5 CS/Syngas | 3 | 3 | 1 | 1 |
| O q5 CS/Tar | 3 | 3 | 1 | 1 |
| O q5 CS/Water | 3 | 3 | 1 | 1 |
| O q5 LG | 3 | 3 | 0 | 0 |
| O q5 LG/Char | 3 | 3 | 1 | 1 |
| O q5 LG/Syngas | 3 | 3 | 1 | 1 |
| O q5 LG/Tar | 3 | 3 | 1 | 1 |
| O q5 LG/Water | 3 | 3 | 1 | 1 |
| P binding | 2 | 2 | 0 | 0 |
| P boundary CE | 3 | 3 | 0 | 0 |
| P boundary CS | 3 | 3 | 0 | 0 |
| P boundary LG | 3 | 3 | 0 | 0 |
| P perturb | 5 | 5 | 0 | 0 |
| P timing | 10 | 10 | 0 | 0 |

## 3 失败清单

无。

## 4 DERIVED 登记表（正文里算出来的数，算式可手算复核）

| 组 | 值 | 算式 |
|---|---|---|
| D q1 CS/Tar | `-7.33` | delta_end = y[-1] - y[0] |
| D q1 CS/Tar | `-37.667` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 CS/Tar | `7.33` | span = max(y) - min(y) |
| D q1 CS/Tar | `1.45467` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 CS/Tar | `5.03896` | span_over_thr = span / (0.10*mean(y)) |
| D q1 CS/Tar | `1` | trend_significant = span > thr_trend |
| D q1 CS/Tar | `2` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 CS/Tar | `1` | all(Δy>0) or all(Δy<0) |
| D q1 CS/Water | `4.18` | delta_end = y[-1] - y[0] |
| D q1 CS/Water | `15.5738` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 CS/Water | `4.18` | span = max(y) - min(y) |
| D q1 CS/Water | `2.89133` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 CS/Water | `1.4457` | span_over_thr = span / (0.10*mean(y)) |
| D q1 CS/Water | `1` | trend_significant = span > thr_trend |
| D q1 CS/Water | `0` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 CS/Water | `1` | all(Δy>0) or all(Δy<0) |
| D q1 CS/Char | `0.66` | delta_end = y[-1] - y[0] |
| D q1 CS/Char | `2.2595` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 CS/Char | `0.76` | span = max(y) - min(y) |
| D q1 CS/Char | `2.93789` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 CS/Char | `0.258689` | span_over_thr = span / (0.10*mean(y)) |
| D q1 CS/Char | `0` | trend_significant = span > thr_trend |
| D q1 CS/Char | `0` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 CS/Char | `0` | all(Δy>0) or all(Δy<0) |
| D q1 CS/Syngas | `2.49` | delta_end = y[-1] - y[0] |
| D q1 CS/Syngas | `10.1674` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 CS/Syngas | `3.96` | span = max(y) - min(y) |
| D q1 CS/Syngas | `2.71611` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 CS/Syngas | `1.45797` | span_over_thr = span / (0.10*mean(y)) |
| D q1 CS/Syngas | `1` | trend_significant = span > thr_trend |
| D q1 CS/Syngas | `0` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 CS/Syngas | `0` | all(Δy>0) or all(Δy<0) |
| D q1 CE/Tar | `10.86` | delta_end = y[-1] - y[0] |
| D q1 CE/Tar | `31.5514` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 CE/Tar | `10.86` | span = max(y) - min(y) |
| D q1 CE/Tar | `4.20825` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 CE/Tar | `2.58065` | span_over_thr = span / (0.10*mean(y)) |
| D q1 CE/Tar | `1` | trend_significant = span > thr_trend |
| D q1 CE/Tar | `2` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 CE/Tar | `0` | all(Δy>0) or all(Δy<0) |
| D q1 CE/Water | `-11.28` | delta_end = y[-1] - y[0] |
| D q1 CE/Water | `-41.1379` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 CE/Water | `11.28` | span = max(y) - min(y) |
| D q1 CE/Water | `1.92625` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 CE/Water | `5.85594` | span_over_thr = span / (0.10*mean(y)) |
| D q1 CE/Water | `1` | trend_significant = span > thr_trend |
| D q1 CE/Water | `4` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 CE/Water | `0` | all(Δy>0) or all(Δy<0) |
| D q1 CE/Char | `3.18` | delta_end = y[-1] - y[0] |
| D q1 CE/Char | `14.839` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 CE/Char | `3.48` | span = max(y) - min(y) |
| D q1 CE/Char | `2.4065` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 CE/Char | `1.44608` | span_over_thr = span / (0.10*mean(y)) |
| D q1 CE/Char | `1` | trend_significant = span > thr_trend |
| D q1 CE/Char | `1` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 CE/Char | `0` | all(Δy>0) or all(Δy<0) |
| D q1 CE/Syngas | `-2.76` | delta_end = y[-1] - y[0] |
| D q1 CE/Syngas | `-16.4973` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 CE/Syngas | `3.98` | span = max(y) - min(y) |
| D q1 CE/Syngas | `1.459` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 CE/Syngas | `2.7279` | span_over_thr = span / (0.10*mean(y)) |
| D q1 CE/Syngas | `1` | trend_significant = span > thr_trend |
| D q1 CE/Syngas | `1` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 CE/Syngas | `0` | all(Δy>0) or all(Δy<0) |
| D q1 LG/Tar | `-9.87` | delta_end = y[-1] - y[0] |
| D q1 LG/Tar | `-54.6512` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 LG/Tar | `9.87` | span = max(y) - min(y) |
| D q1 LG/Tar | `1.13` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 LG/Tar | `8.73451` | span_over_thr = span / (0.10*mean(y)) |
| D q1 LG/Tar | `1` | trend_significant = span > thr_trend |
| D q1 LG/Tar | `4` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 LG/Tar | `0` | all(Δy>0) or all(Δy<0) |
| D q1 LG/Water | `8.39` | delta_end = y[-1] - y[0] |
| D q1 LG/Water | `54.8366` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 LG/Water | `8.39` | span = max(y) - min(y) |
| D q1 LG/Water | `2.0435` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 LG/Water | `4.1057` | span_over_thr = span / (0.10*mean(y)) |
| D q1 LG/Water | `1` | trend_significant = span > thr_trend |
| D q1 LG/Water | `1` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 LG/Water | `0` | all(Δy>0) or all(Δy<0) |
| D q1 LG/Char | `-0.74` | delta_end = y[-1] - y[0] |
| D q1 LG/Char | `-1.27213` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 LG/Char | `1.19` | span = max(y) - min(y) |
| D q1 LG/Char | `5.73362` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 LG/Char | `0.207548` | span_over_thr = span / (0.10*mean(y)) |
| D q1 LG/Char | `0` | trend_significant = span > thr_trend |
| D q1 LG/Char | `0` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 LG/Char | `0` | all(Δy>0) or all(Δy<0) |
| D q1 LG/Syngas | `2.22` | delta_end = y[-1] - y[0] |
| D q1 LG/Syngas | `26.2102` | delta_end_pct = 100*(y[-1]-y[0])/y[0] |
| D q1 LG/Syngas | `3.41` | span = max(y) - min(y) |
| D q1 LG/Syngas | `1.09288` | thr_trend = 2*eps_rel*mean(|y|) = 0.10*mean(y) |
| D q1 LG/Syngas | `3.12021` | span_over_thr = span / (0.10*mean(y)) |
| D q1 LG/Syngas | `1` | trend_significant = span > thr_trend |
| D q1 LG/Syngas | `2` | count(|Δy_i| > 0.10*max(|y_i|,|y_i+1|)) |
| D q1 LG/Syngas | `0` | all(Δy>0) or all(Δy<0) |
| E q1 ilr CS | `0.0332594` | sigma_fit = sqrt(rss/(n_obs-k_par)) |
| E q1 ilr CS | `0.439639` | F = (sigma_fit / sigma_noise_mc)^2 |
| E q1 ilr CS | `27` | n_obs = n_levels * 3（ILR 3 维） |
| E q1 ilr CS | `M3_sqrt_w` | aic_best = min(cand, key=cand.get) |
| E q1 ilr CS | `0` | F<=1 ⇔ 残差在噪声内 |
| E q1 ilr CE | `0.0928927` | sigma_fit = sqrt(rss/(n_obs-k_par)) |
| E q1 ilr CE | `3.42323` | F = (sigma_fit / sigma_noise_mc)^2 |
| E q1 ilr CE | `24` | n_obs = n_levels * 3（ILR 3 维） |
| E q1 ilr CE | `M2_linear_logw` | aic_best = min(cand, key=cand.get) |
| E q1 ilr CE | `0` | F<=1 ⇔ 残差在噪声内 |
| E q1 ilr LG | `0.0940614` | sigma_fit = sqrt(rss/(n_obs-k_par)) |
| E q1 ilr LG | `3.52194` | F = (sigma_fit / sigma_noise_mc)^2 |
| E q1 ilr LG | `24` | n_obs = n_levels * 3（ILR 3 维） |
| E q1 ilr LG | `M2_linear_logw` | aic_best = min(cand, key=cand.get) |
| E q1 ilr LG | `0` | F<=1 ⇔ 残差在噪声内 |
| G q2 CS/H2 | `37.14` | span = max(z)-min(z) |
| G q2 CS/H2 | `2.56617` | thr_trend = 0.10*mean(z) |
| G q2 CS/H2 | `14.4729` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/H2 | `major` | tier = major if span>=5 else minor |
| G q2 CS/H2 | `3.92335` | m = z * M / V_m |
| G q2 CS/H2 | `1` | all(Δz>0) or all(Δz<0) |
| G q2 CS/H2 | `5` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/H2 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CS/CO | `5.4` | span = max(z)-min(z) |
| G q2 CS/CO | `2.239` | thr_trend = 0.10*mean(z) |
| G q2 CS/CO | `2.41179` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/CO | `major` | tier = major if span>=5 else minor |
| G q2 CS/CO | `29.1422` | m = z * M / V_m |
| G q2 CS/CO | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CS/CO | `1` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/CO | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CS/CO2 | `9.49` | span = max(z)-min(z) |
| G q2 CS/CO2 | `5.41517` | thr_trend = 0.10*mean(z) |
| G q2 CS/CO2 | `1.75249` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/CO2 | `major` | tier = major if span>=5 else minor |
| G q2 CS/CO2 | `99.9598` | m = z * M / V_m |
| G q2 CS/CO2 | `1` | all(Δz>0) or all(Δz<0) |
| G q2 CS/CO2 | `0` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/CO2 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CS/CH4 | `9.7` | span = max(z)-min(z) |
| G q2 CS/CH4 | `2.98` | thr_trend = 0.10*mean(z) |
| G q2 CS/CH4 | `3.25503` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/CH4 | `major` | tier = major if span>=5 else minor |
| G q2 CS/CH4 | `21.623` | m = z * M / V_m |
| G q2 CS/CH4 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CS/CH4 | `2` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/CH4 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CS/C2H6 | `0.99` | span = max(z)-min(z) |
| G q2 CS/C2H6 | `0.279833` | thr_trend = 0.10*mean(z) |
| G q2 CS/C2H6 | `3.53782` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/C2H6 | `minor` | tier = major if span>=5 else minor |
| G q2 CS/C2H6 | `3.94422` | m = z * M / V_m |
| G q2 CS/C2H6 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CS/C2H6 | `2` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/C2H6 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CS/C3H8 | `0.33` | span = max(z)-min(z) |
| G q2 CS/C3H8 | `0.0706667` | thr_trend = 0.10*mean(z) |
| G q2 CS/C3H8 | `4.66981` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/C3H8 | `minor` | tier = major if span>=5 else minor |
| G q2 CS/C3H8 | `1.71163` | m = z * M / V_m |
| G q2 CS/C3H8 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CS/C3H8 | `2` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/C3H8 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CS/C3H6 | `0.06` | span = max(z)-min(z) |
| G q2 CS/C3H6 | `0.0378333` | thr_trend = 0.10*mean(z) |
| G q2 CS/C3H6 | `1.5859` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/C3H6 | `minor` | tier = major if span>=5 else minor |
| G q2 CS/C3H6 | `0.713428` | m = z * M / V_m |
| G q2 CS/C3H6 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CS/C3H6 | `0` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/C3H6 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CS/C2H4 | `0.1` | span = max(z)-min(z) |
| G q2 CS/C2H4 | `0.0761667` | thr_trend = 0.10*mean(z) |
| G q2 CS/C2H4 | `1.31291` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/C2H4 | `minor` | tier = major if span>=5 else minor |
| G q2 CS/C2H4 | `0.938721` | m = z * M / V_m |
| G q2 CS/C2H4 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CS/C2H4 | `0` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/C2H4 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CS/C4H10 | `0.31` | span = max(z)-min(z) |
| G q2 CS/C4H10 | `0.0376667` | thr_trend = 0.10*mean(z) |
| G q2 CS/C4H10 | `8.23009` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CS/C4H10 | `minor` | tier = major if span>=5 else minor |
| G q2 CS/C4H10 | `0.6483` | m = z * M / V_m |
| G q2 CS/C4H10 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CS/C4H10 | `5` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CS/C4H10 | `1` | trend_significant = span > 0.10*mean(z) |
| H q2 rowsum CS | `120.24` | row_sum_i = Σ_g z_{g,i} |
| H q2 rowsum CS | `1` | Σ_g φ_{g,i} = 1（φ = z / row_sum） |
| H q2 rowsum CS | `['CH4', 'CO', 'CO2', 'H2']` | tiers.major = [g for g if tier=='major'] |
| G q2 CE/H2 | `39.2` | span = max(z)-min(z) |
| G q2 CE/H2 | `5.074` | thr_trend = 0.10*mean(z) |
| G q2 CE/H2 | `7.72566` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CE/H2 | `major` | tier = major if span>=5 else minor |
| G q2 CE/H2 | `5.20775` | m = z * M / V_m |
| G q2 CE/H2 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CE/H2 | `4` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CE/H2 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CE/CO | `8.4` | span = max(z)-min(z) |
| G q2 CE/CO | `0.884` | thr_trend = 0.10*mean(z) |
| G q2 CE/CO | `9.50226` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CE/CO | `major` | tier = major if span>=5 else minor |
| G q2 CE/CO | `6.62323` | m = z * M / V_m |
| G q2 CE/CO | `1` | all(Δz>0) or all(Δz<0) |
| G q2 CE/CO | `4` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CE/CO | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CE/CO2 | `16.7` | span = max(z)-min(z) |
| G q2 CE/CO2 | `0.792` | thr_trend = 0.10*mean(z) |
| G q2 CE/CO2 | `21.0859` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CE/CO2 | `major` | tier = major if span>=5 else minor |
| G q2 CE/CO2 | `3.92692` | m = z * M / V_m |
| G q2 CE/CO2 | `1` | all(Δz>0) or all(Δz<0) |
| G q2 CE/CO2 | `4` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CE/CO2 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CE/CH4 | `2.5` | span = max(z)-min(z) |
| G q2 CE/CH4 | `0.168` | thr_trend = 0.10*mean(z) |
| G q2 CE/CH4 | `14.881` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CE/CH4 | `minor` | tier = major if span>=5 else minor |
| G q2 CE/CH4 | `0.501031` | m = z * M / V_m |
| G q2 CE/CH4 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 CE/CH4 | `3` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CE/CH4 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 CE/C2H6 | `10.6` | span = max(z)-min(z) |
| G q2 CE/C2H6 | `0.668` | thr_trend = 0.10*mean(z) |
| G q2 CE/C2H6 | `15.8683` | span_over_thr = span/(0.10*mean(z)) |
| G q2 CE/C2H6 | `major` | tier = major if span>=5 else minor |
| G q2 CE/C2H6 | `4.29303` | m = z * M / V_m |
| G q2 CE/C2H6 | `1` | all(Δz>0) or all(Δz<0) |
| G q2 CE/C2H6 | `3` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 CE/C2H6 | `1` | trend_significant = span > 0.10*mean(z) |
| H q2 rowsum CE | `76` | row_sum_i = Σ_g z_{g,i} |
| H q2 rowsum CE | `1` | Σ_g φ_{g,i} = 1（φ = z / row_sum） |
| H q2 rowsum CE | `['C2H6', 'CO', 'CO2', 'H2']` | tiers.major = [g for g if tier=='major'] |
| G q2 LG/H2 | `0.14` | span = max(z)-min(z) |
| G q2 LG/H2 | `0.0754` | thr_trend = 0.10*mean(z) |
| G q2 LG/H2 | `1.85676` | span_over_thr = span/(0.10*mean(z)) |
| G q2 LG/H2 | `minor` | tier = major if span>=5 else minor |
| G q2 LG/H2 | `0.0710556` | m = z * M / V_m |
| G q2 LG/H2 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 LG/H2 | `0` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 LG/H2 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 LG/CO | `5.705` | span = max(z)-min(z) |
| G q2 LG/CO | `1.7661` | thr_trend = 0.10*mean(z) |
| G q2 LG/CO | `3.23028` | span_over_thr = span/(0.10*mean(z)) |
| G q2 LG/CO | `major` | tier = major if span>=5 else minor |
| G q2 LG/CO | `26.1617` | m = z * M / V_m |
| G q2 LG/CO | `1` | all(Δz>0) or all(Δz<0) |
| G q2 LG/CO | `0` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 LG/CO | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 LG/CO2 | `19.21` | span = max(z)-min(z) |
| G q2 LG/CO2 | `3.7262` | thr_trend = 0.10*mean(z) |
| G q2 LG/CO2 | `5.15539` | span_over_thr = span/(0.10*mean(z)) |
| G q2 LG/CO2 | `major` | tier = major if span>=5 else minor |
| G q2 LG/CO2 | `85.5283` | m = z * M / V_m |
| G q2 LG/CO2 | `1` | all(Δz>0) or all(Δz<0) |
| G q2 LG/CO2 | `1` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 LG/CO2 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 LG/CH4 | `6.19` | span = max(z)-min(z) |
| G q2 LG/CH4 | `3.0982` | thr_trend = 0.10*mean(z) |
| G q2 LG/CH4 | `1.99793` | span_over_thr = span/(0.10*mean(z)) |
| G q2 LG/CH4 | `major` | tier = major if span>=5 else minor |
| G q2 LG/CH4 | `21.3797` | m = z * M / V_m |
| G q2 LG/CH4 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 LG/CH4 | `2` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 LG/CH4 | `1` | trend_significant = span > 0.10*mean(z) |
| G q2 LG/C2H6 | `0.04` | span = max(z)-min(z) |
| G q2 LG/C2H6 | `0.007` | thr_trend = 0.10*mean(z) |
| G q2 LG/C2H6 | `5.71429` | span_over_thr = span/(0.10*mean(z)) |
| G q2 LG/C2H6 | `minor` | tier = major if span>=5 else minor |
| G q2 LG/C2H6 | `0.0670786` | m = z * M / V_m |
| G q2 LG/C2H6 | `0` | all(Δz>0) or all(Δz<0) |
| G q2 LG/C2H6 | `4` | count(|Δz_i| > 0.10*max(|z_i|,|z_i+1|)) |
| G q2 LG/C2H6 | `1` | trend_significant = span > 0.10*mean(z) |
| H q2 rowsum LG | `68` | row_sum_i = Σ_g z_{g,i} |
| H q2 rowsum LG | `1` | Σ_g φ_{g,i} = 1（φ = z / row_sum） |
| H q2 rowsum LG | `['CH4', 'CO', 'CO2']` | tiers.major = [g for g if tier=='major'] |
| I q2 bridge CS | `17.4597` | wtpct = m_mg_per_g / 10 |
| I q2 bridge CS | `0.570011` | lo = min(beta_bridge[*]) |
| I q2 bridge CS | `0.712932` | hi = max(beta_bridge[*]) |
| I q2 bridge CE | `7.70338` | wtpct = m_mg_per_g / 10 |
| I q2 bridge CE | `0.147115` | lo = min(beta_bridge[*]) |
| I q2 bridge CE | `0.499895` | hi = max(beta_bridge[*]) |
| I q2 bridge LG | `8.68153` | wtpct = m_mg_per_g / 10 |
| I q2 bridge LG | `0.848634` | lo = min(beta_bridge[*]) |
| I q2 bridge LG | `1.2461` | hi = max(beta_bridge[*]) |
| J q3 Tar | `[16.36, 24.539999999999996, 31.400000000000002, 33.5, 35.040000000000006, 35.39, 32.94, 37.089999999999996]` | Delta_i = CE_i - LG_i |
| J q3 Tar | `30.7825` | mean_Delta = mean(CE - LG) |
| J q3 Tar | `[3.887029714319149, 4.070956889970711, 4.4157674304700425, 4.497073270472697, 4.5530001098177015, 4.531675738620317, 4.444983239563452, 4.601472047073632]` | thr_diff = 2*eps_rel*sqrt(ya²+yb²) = 0.10*sqrt(ya²+yb²) |
| J q3 Tar | `8` | n_exceed = count(|Delta| > thr_diff) |
| J q3 Tar | `0` | sign_changes = count(diff(sign(Delta)) != 0) |
| J q3 Tar | `37.09` | max|Delta| |
| J q3 Water | `[12.120000000000001, 2.830000000000002, -2.330000000000002, -4.07, -5.280000000000001, -3.620000000000001, -1.4800000000000004, -7.550000000000001]` | Delta_i = CE_i - LG_i |
| J q3 Water | `-1.1725` | mean_Delta = mean(CE - LG) |
| J q3 Water | `[3.1399783438743656, 2.82914916538524, 2.6927578799439065, 2.693233929683792, 2.697412463825286, 2.848437115331845, 2.9250521362874884, 2.8665583894279916]` | thr_diff = 2*eps_rel*sqrt(ya²+yb²) = 0.10*sqrt(ya²+yb²) |
| J q3 Water | `6` | n_exceed = count(|Delta| > thr_diff) |
| J q3 Water | `1` | sign_changes = count(diff(sign(Delta)) != 0) |
| J q3 Water | `12.12` | max|Delta| |
| J q3 Char | `[-36.74000000000001, -32.55000000000001, -32.96000000000001, -32.279999999999994, -32.6, -32.63999999999999, -33.58, -32.82]` | Delta_i = CE_i - LG_i |
| J q3 Char | `-33.2713` | mean_Delta = mean(CE - LG) |
| J q3 Char | `[6.1991884952790395, 6.262714826654651, 6.20324576330811, 6.21032237488522, 6.218674456827597, 6.228917241383128, 6.181963603904507, 6.2480853067159705]` | thr_diff = 2*eps_rel*sqrt(ya²+yb²) = 0.10*sqrt(ya²+yb²) |
| J q3 Char | `8` | n_exceed = count(|Delta| > thr_diff) |
| J q3 Char | `0` | sign_changes = count(diff(sign(Delta)) != 0) |
| J q3 Char | `36.74` | max|Delta| |
| J q3 Syngas | `[8.26, 5.18, 3.8900000000000006, 2.8499999999999996, 2.84, 0.8699999999999992, 2.119999999999999, 3.280000000000001]` | Delta_i = CE_i - LG_i |
| J q3 Syngas | `3.66125` | mean_Delta = mean(CE - LG) |
| J q3 Syngas | `[1.8751901236941284, 1.8496513184922179, 1.9086070837131464, 1.876905165425254, 1.885969246833044, 1.742690161790099, 1.7318406393199117, 1.7590821470300926]` | thr_diff = 2*eps_rel*sqrt(ya²+yb²) = 0.10*sqrt(ya²+yb²) |
| J q3 Syngas | `7` | n_exceed = count(|Delta| > thr_diff) |
| J q3 Syngas | `0` | sign_changes = count(diff(sign(Delta)) != 0) |
| J q3 Syngas | `8.26` | max|Delta| |
| K q3 H2 | `65.8` | abs_max = max(max|CE|, max|LG|) |
| K q3 H2 | `5` | n_exceed = count(|Delta| > thr_diff) |
| K q3 CO | `20.935` | abs_max = max(max|CE|, max|LG|) |
| K q3 CO | `4` | n_exceed = count(|Delta| > thr_diff) |
| K q3 CO2 | `43.56` | abs_max = max(max|CE|, max|LG|) |
| K q3 CO2 | `5` | n_exceed = count(|Delta| > thr_diff) |
| K q3 CH4 | `33.86` | abs_max = max(max|CE|, max|LG|) |
| K q3 CH4 | `5` | n_exceed = count(|Delta| > thr_diff) |
| K q3 C2H6 | `13.8` | abs_max = max(max|CE|, max|LG|) |
| K q3 C2H6 | `5` | n_exceed = count(|Delta| > thr_diff) |
| K q3 flips | `['Water']` | flips = [k for k if sign_changes>0 or n_exceed==0] |
| L q4 gamma CS | `0` | Σ_p gamma_p = 0（中心化后） |
| L q4 gamma CS | `-0.826313` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma CS | `0.397043` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma CS | `0.148141` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma CS | `0.281128` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 carbon CS | `-0.122691` | delta_end = c_mmol[-1] - c_mmol[0] |
| L q4 carbon CS | `-2.30473` | delta_end_pct = 100*(c[-1]-c[0])/c[0] |
| L q4 gamma CE | `0` | Σ_p gamma_p = 0（中心化后） |
| L q4 gamma CE | `0.74961` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma CE | `-0.726859` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma CE | `0.340415` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma CE | `-0.363165` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 carbon CE | `-2.17721` | delta_end = c_mmol[-1] - c_mmol[0] |
| L q4 carbon CE | `-77.2152` | delta_end_pct = 100*(c[-1]-c[0])/c[0] |
| L q4 gamma LG | `0` | Σ_p gamma_p = 0（中心化后） |
| L q4 gamma LG | `-1.58096` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma LG | `0.956255` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma LG | `0.0554864` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 gamma LG | `0.569218` | gamma_p = d ln S_p/d w，中心化后 Σgamma = 0 |
| L q4 carbon LG | `1.20706` | delta_end = c_mmol[-1] - c_mmol[0] |
| L q4 carbon LG | `40.135` | delta_end_pct = 100*(c[-1]-c[0])/c[0] |
| M q4 kinetics | `0.95` | kt(n=0) = alpha |
| M q4 kinetics | `2.99573` | kt(n=1) = -ln(1-alpha) |
| M q4 kinetics | `19` | kt(n=2) = 1/(1-alpha) - 1 |
| M q4 kinetics | `0.0016643` | k = kt / t_hold_s |
| M q4 kinetics | `1800` | t_hold_s = t_hold_ASSUMED*60 = 30*60 = 1800 |
| M q4 kinetics | `6.34236` | confounding = kt(n=2)/kt(n=1)（比值，不是 log 比） |
| M q4 kinetics | `5633.73` | A = k_need(n=1)*exp(Ea*1000/(R*T)) |
| M q4 kinetics | `3.7508` | log10_A = log10(A) |
| N q5 grid | `[0.13043478260869565, 0.2, 0.25925925925925924, 0.3103448275862069, 0.3548387096774194, 0.4117647058823529, 0.4736842105263158]` | w = r/(1+r)（model_skeleton.py:165-168） |
| N q5 grid | `0.130435` | w = r/(1+r) |
| N q5 grid | `0.2` | w = r/(1+r) |
| N q5 grid | `0.259259` | w = r/(1+r) |
| N q5 grid | `0.310345` | w = r/(1+r) |
| N q5 grid | `0.354839` | w = r/(1+r) |
| N q5 grid | `0.411765` | w = r/(1+r) |
| N q5 grid | `0.473684` | w = r/(1+r) |
| O q5 CS | `100` | 行和恒等于 100（ILR 反变换的构造性闭合） |
| O q5 CS | `0.0332594` | Q5 的 ILR 噪声尺度沿用 Q1 拟合残差 sigma_fit |
| O q5 CS/Tar | `5.49717` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 CS/Water | `1.36578` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 CS/Char | `0.892069` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 CS/Syngas | `4.91023` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 CE | `100` | 行和恒等于 100（ILR 反变换的构造性闭合） |
| O q5 CE | `0.0928927` | Q5 的 ILR 噪声尺度沿用 Q1 拟合残差 sigma_fit |
| O q5 CE/Tar | `6.3408` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 CE/Water | `18.7075` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 CE/Char | `6.0321` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 CE/Syngas | `6.00481` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 LG | `100` | 行和恒等于 100（ILR 反变换的构造性闭合） |
| O q5 LG | `0.0940614` | Q5 的 ILR 噪声尺度沿用 Q1 拟合残差 sigma_fit |
| O q5 LG/Tar | `17.0779` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 LG/Water | `6.92245` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 LG/Char | `1.53024` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| O q5 LG/Syngas | `12.3951` | loo_rmse_rel% = 100*loo_rmse/mean(观测 y)（solve.py:472） |
| P timing | `15.061` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P timing | `1.72` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P timing | `1.894` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P timing | `189.718` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P timing | `1.228` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P timing | `0.226` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P timing | `0.255` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P timing | `68.1` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P timing | `254.609` | median = sorted(runs)[len//2]（results_timing.json meta） |
| P boundary CS | `1` | count(mark == '★') |
| P boundary CS | `4` | count(mark == '★★') |
| P boundary CS | `[0.090909, 0.130435, 0.2, 0.259259, 0.310345, 0.354839, 0.411765, 0.473684, 0.5, 0.545455, 0.6, 0.666667, 0.75]` | w = r/(1+r) |
| P boundary CE | `2` | count(mark == '★') |
| P boundary CE | `4` | count(mark == '★★') |
| P boundary CE | `[0.090909, 0.130435, 0.2, 0.259259, 0.310345, 0.354839, 0.411765, 0.473684, 0.5, 0.545455, 0.6, 0.666667, 0.75]` | w = r/(1+r) |
| P boundary LG | `2` | count(mark == '★') |
| P boundary LG | `4` | count(mark == '★★') |
| P boundary LG | `[0.090909, 0.130435, 0.2, 0.259259, 0.310345, 0.354839, 0.411765, 0.473684, 0.5, 0.545455, 0.6, 0.666667, 0.75]` | w = r/(1+r) |
| P perturb | `16` | feasible + infeasible = model_perturb |
| P perturb | `15` | 分母只算 model 类可行扰动 |
| P perturb | `42` | 三类之和 = attempted |
| P perturb | `1` | count(model 且 n_flips>0) |

## 5 复算命令

```powershell
cd E:\数学建模\PRACTICE_2023B
& 'E:\Mini\envs\mathmodel\python.exe' code\verify_numbers.py
```

本脚本只读 data/*.json 与 main.tex，不改任何上游文件；唯一写入的是本报告自身（首行 `BYTES <n>` 用 write_bytes 迭代到不动点）。

## 附录 A · 数值索引（结论 → data/*.json 键路径）

> 正文与结论只指向本附录一次，不重复抄表；键路径就是给对账绑 claim 的原料。

| 组 | 覆盖的结论 | JSON 键路径 |
|---|---|---|
| B ledger | 数据溯源：204 条记录 / 31 条序列 / 两个附件 sha256 | `data/ledger.json → records / series / source_files` |
| C q1 ledger | Q1 逐格值（4 产物 × 3 组合）与台账一致 | `data/ledger.json → records[].value ↔ data/results_q1.json → combos.*.products.*.y` |
| D q1 | Q1 首末值、变幅、阈值、超阈步数、单调性 | `data/results_q1.json → combos.*.products.*.{first,last,delta_end,delta_end_pct,span,mean,thr_trend,span_over_thr,n_step_exceed,monotone}` |
| E q1 ilr | Q1 成分回归：σ_fit、失拟 F、R²、AIC 选型 | `data/results_q1.json → combos.*.ilr.{sigma_fit,lack_of_fit_F,R2_each,aic,aic_best}` |
| F q2 ledger | Q2 逐格气体体积与台账一致 | `data/ledger.json → records[].value ↔ data/results_q2.json → combos.*.gases.*.z` |
| G q2 | Q2 气体 span、φ、质量产率、量级分层、峰值档位 | `data/results_q2.json → combos.*.gases.*.{span,phi,m_mg_per_g,tier,argmax_label,trend_significant}` |
| H q2 rowsum | Q2 行和与 φ 分母 | `data/results_q2.json → combos.*.row_sum / gases.*.phi / tiers` |
| I q2 bridge | 两附件量纲桥接系数 β | `data/results_q2.json → bridge.*.{gas_mass_wtpct,annex1_syngas_wtpct,beta_bridge}` |
| J q3 | Q3 CE 与 LG 逐档差、平均差、超阈计数、符号翻转 | `data/results_q3.json → products.* / gases.*` |
| K q3 | Q3 单气最大绝对体积 | `data/results_q3.json → gases.*.abs_max` |
| L q4 | Q4 选择性弹性 γ、碳平衡收支 | `data/results_q4.json → selectivity.*.gamma_centered / carbon_balance.*` |
| M q4 kinetics | Q4 动力学：kt、k、n 级混淆比、Ea–A 脊线 | `data/results_q4.json → kinetics.*` |
| N q5 grid | Q5 预测网格 r → w | `data/results_q5.json → meta.grid_r / meta.grid_w` |
| O q5 | Q5 点预测、区间、留一误差 | `data/results_q5.json → combos.*.{point,lo,hi,loo_rmse,loo_rmse_rel,row_sum_point}` |
| P boundary | Q5 查询点是否越出观测支撑 | `data/results_boundary.json → combos.*.{rows,n_boundary_star,n_extrapolation_star2}` |
| P binding | 约束在解处是否起作用 | `data/results_binding.json → sources[].binding` |
| P perturb | 参数 ±10% 后结论是否翻转 | `data/results_perturb.json → counts / runs[].flips` |
| P timing | 各步调用耗时中位数 | `data/results_timing.json → calls[].median_ms` |

## 7 交给下一棒

**论文撰写手**：第 6 节的表就是 `main.tex` 要填的数。逐行抄 `待命中的写法` 那一列，数值不要自己重算 —— 表里的每个数都已由第 4 节算式从 `data/*.json` 现算过一遍。写完重跑本脚本，`正文侧 声明/命中` 会从 `145 / 0` 涨到 `145 / 145`，`## 6 缓期清单` 消失、`VERDICT` 仍为 `PASS`，G5 才算真过。

**图表手**：本报告不印任何脚本字节数（自指数字会变孤儿 token），所以 `tab:code` 里的脚本大小只能由 `code/gen_index.py` 现读生成；但 `code/verify_numbers.py` 本轮的字节数已经变了，`tab:code` 必须重跑一次生成器，否则那张表是旧的。

**共同注意**：正文只要出现第一个结果数字，`tex_state` 就从 `skeleton` 变 `written`，骨架缓期立即作废 —— 半填的正文比空正文更容易被 G5 判 FAIL，所以第 6 节的数要么不填，要么一次填完。

VERDICT: PASS
