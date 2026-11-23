# 修订日志：第一轮评审 → 修订

日期：2026-11-17。评审方式：四个独立 subagent 按 `04_评分与复盘/评分细则_v1.md` 打分（judge-modeling 41 分、judge-evidence 39 分、judge-writing 20 分、judge-redteam 只列风险）。下面记录每一条被采纳的问题、改动位置与改动后的值。凡"未修"的都写明原因，避免把评审意见当成已解决。

## 一、数值与公式一致性（judge-evidence / judge-modeling）

| # | 问题 | 处理 | 位置 |
|---|---|---|---|
| 1 | Q5 损伤函数印成 `D=D2021·((Oref+O)/Oref)^1.5`，与代码 `ref_loss*(over/over_ref)**gamma` 不同，O=Oref 时自相矛盾（2.83×） | 正文改为 `D=D2021·(O/Oref)^1.5`，`D(Oref)=D2021`；容量写 `C=RL3d(T)+S`，溢出写 `O=(Q(X)−C)^+`；补 Oref=296.4 mm 的来历（Q(449)=399.4 − RL3d(2)=102.9） | `s7_q5.tex` |
| 2 | `1.76×10⁸ m³ … 8.7 h 排完` 配对错（1.76e8/36 mm·h⁻¹ 只需 4.15 h；8.7 h 是 313.4/36） | 峰值小时改报 $1.4×10^8$ m³（SCS：201.9 mm/h → 156.6 mm 产流，减 36 mm 容量 = 120.6 mm × 1180 km²）；8.7 h 挂在三日事件（265.4 mm 产流 / 36 mm·h⁻¹）上；50 mm·h⁻¹ 对应 6.3 h | `s3_q1.tex`、`summary.tex`、`s8_eval.tex` |
| 3 | "EVT 4/5 versus ML 1/5" 拼接了 EVT 最好与 ML 最差；"best ML 0.643 and 1/5" 混用 Ridge 的 ρ 与 RF 的重合 | 改为 `4/5 versus 3/5`（Ridge 3/5 是 ML 最好），并分写"Seven EVT variants 0.69–0.75 / 3–4 of 5；best ML 0.643 and 3/5，weakest 0.598 and 1/5" | `s5_q3.tex`、`summary.tex`、`s8_eval.tex` |
| 4 | 表 5 `Days ≥50 mm` 中位写成 +2.71%，文件中位为 +2.26% | 表与正文改 +2.26% | `s4_q2.tex` |
| 5 | "five belts" 实为六带 | 改 six belts，补 Northeast +4.6 | `s4_q2.tex` |
| 6 | 风险名单漏掉自己表 8 排第 3 的 Hohhot | 摘要与结论改为"Haikou, Guangzhou, Hohhot, Nanjing, Wuhan"；正文说明郑州"综合第 6、按 p10 第 7" | `summary.tex`、`s5_q3.tex`、`s8_eval.tex` |
| 7 | 摘要 "60% of its total in one day" 错（188.7/362.2=52%） | 改 52%，并注明是"of its event total" | `summary.tex`、`s8_eval.tex` |
| 8 | "uniform upgrading pays back at most 1.63" 与"社会口径无一处过线"都错 | 海口均匀方案最高 BCR 2.10（S=5 mm）、1.63 是最小总成本方案（S=80 mm）、计入 3.95 条命后 1.65；海口 126 组合中 16 个过社会线（最高 2.12） | `s7_q5.tex`、`summary.tex`、`s8_eval.tex` |
| 9 | 表 3 的 T=5/10/20 置信区间留空 | 填 [95.06,118.62]、[109.11,140.47]、[120.30,165.29] | `s3_q1.tex`（表 3） |
| 10 | 表 12 三格 `--` 与 CSV 冲突 | 改为 2.63/2.14/0.88（对应 h2m10/h5m10/h2m20 的郑州行） | `s7_q5.tex` |
| 11 | ξ 三个值未标窗口（−0.03 / −0.007 / +0.030） | 统一标注：日值 1961–2020 MLE −0.03、L-矩 +0.030；训练窗 1961–2010 MLE −0.007；并说明估计量选择只把设计深度移动 0.5%（102.9 vs 102.4 mm） | `s3_q1.tex`、`s8_eval.tex` |
| 12 | "2 000 replicates" 与代码 1 000 不符 | 正文改 1 000（事件重现期 500 次） | `s3_q1.tex` |
| 13 | 代码附录列了不存在的 `fetch_ghcn.py`；种子 20211117 不存在 | 换成 `_maketable.py`、`_selfcheck.py`；种子写 20210720（GEV bootstrap）与 0（kmeans/RF/GBR） | `appendix.tex` |
| 14 | "annual normal 640.8 mm" 无来源 | 标注为题面给定值 | `s1_intro.tex` |
| 15 | 站点数 35 与 audit 29 行不一致 | 正文统一 35 个文件，并在数据节说明 6 个文件无可用记录 | `s2_data.tex` |

## 二、表述与论证（judge-modeling / judge-redteam）

| # | 问题 | 处理 |
|---|---|---|
| 16 | "expected maximum 小于 n 年分位数"方向反 | 改为"在 Gumbel 尾下比 n 年分位数高 0.577σ，所以分位数目标系统性偏大、bias 为负大" |
| 17 | "integrating over the fitted GEV" 与代码（历史样本均值 + CVaR95）不符 | 改为历史样本均值 + 上 5% CVaR |
| 18 | 损失分解被当成因果证据 | 明确写"这是恒等式，不是因果检验"，因果结论只在有外部证据的暴露机制上 |
| 19 | "每毫米贵 6.4 倍" 分母口径不同 | 从表中删除该行，正文改为"仅作指示，两者降雨分母不同"；图注同步说明 |
| 20 | A1 声称"官方与站点口径从不混用"，但 Oref 混用 | A1 改为"站点数据驱动全部统计与设计深度；官方 449 mm 只作为损伤函数尺度锚，并在 §9 报告改用站点口径的后果（×2.465）" |
| 21 | A7 "observed convexity" 无出处；A8 敏感性承诺只兑现一半 | A7 改为"a priori 取 1.5，§9 在 1.2–1.8 扫描"；A8 指向 §9 的成本范围 |
| 22 | 缺参数三分法表 | 新增附录 `tab:params`（18 个参数：状态/取值/来源/是否扫描） |
| 23 | §9.1 用 capacity ratio 与排水时间当 CN 敏感性证据（按构造与 CN 无关） | 明确说 capacity ratio 按构造与 CN 无关，不能当稳健性证据；改用产流体积 2.72–3.52×10⁸ m³、排水 6.4–8.3 h，以及 Task 5 的 BCR 1.80→3.18 |
| 24 | Q3 前三名 RMSE 差 1.8 mm 小于离散度 | 补配对 bootstrap：T14−Emax = 9.14 [3.31,13.64]（P=0.997）；Emax−Emax_trend = 1.72 [−1.92,7.04] |
| 25 | "each EVT Spearman >0.73" 与 0.688 矛盾 | 改 0.69–0.75，并承认趋势版破坏排序 |
| 26 | 形态参数未辨识却只用 L-矩尾 | 说明三个窗口、两种估计量对设计深度只差 0.5%，不改变结论 |

## 三、写作与规范（judge-writing）

| # | 问题 | 处理 |
|---|---|---|
| 27 | 表 6 表注承诺 Overlap 列但表里没有 | 加 Overlap 列（4,4,4,3,3,4,4,3,1,2） |
| 28 | fig07 图注颜色语义反了 | 改"red denotes increasing extremes and blue decreasing"；fig08 附录图注同步 |
| 29 | fig20 图注写 Zhengzhou/Guangzhou + 管径标准，图面是 Zhengzhou/Haikou + annualised cost | 改图注 |
| 30 | 表 8 列名 "ML ten-year max" 与表注"regression estimate"不符 | 改 "Regression ten-year max" |
| 31 | 表 9/10 首列列头空白 | 已补 `City`（本轮复核） |
| 32 | 参考文献未按首引次序、URL 无访问日期、3 条未被引用 | 按首引重排（sc, che2021, mem2021, pettitt1979, menne2012, sen1968, mann1945, coles2001, neh1986, bh1995, hosking1985, gb50014, gb55027, ipcc2021），补 accessed 日期，14 条全部被引用 |
| 33 | 摘要页无页眉；页眉缺 "of N" | 摘要页用默认 fancy；页眉改 `Page X of \pageref{LastPage}`（需 `lastpage` 宏包） |
| 34 | 摘要 "destroyed 120.06 billion CNY of assets" | 改 "caused ... of direct loss" |
| 35 | 公式无编号 | 未修：公式均为行内/单行推导，正文以文字指代；改动会牵动交叉引用，收益小于风险 |
| 36 | 符号表全在附录 | 保留（正文用符号即定义；附录 A 集中列出，符合 2021 格式"符号说明可放正文或附录"） |

## 四、页数

| 轮次 | 总页 | 正文 | 摘要+目录+正文 | 处理 |
|---|---|---|---|---|
| 评审时 | 29 | 20 | 22 | — |
| 加入参数表与 §9 扩写后 | 34 | 22 | 25 | 超限 |
| 移 fig17/fig20/fig22 入附录、图宽 0.62–0.76、目录 `\small` | 32 | 20 | 23 | 达标 |
| 摘要压回单页（删 60 词、`\enlargethispage{6\baselineskip}`） | 31 | 20 | 22 | 达标 |

## 五、未修项（诚实记录）

- 公式编号：13 处展示公式无 `\eqref` 编号，评委可按规范扣分。
- 年最大值独立性未检验（A4 只是假设）。
- 损失函数只有一次事件标定，指数取 1.5 是假设；已给 1.2–1.8 扫描。
- 单价（1e9 元/mm、800 元/m³、1.5e8 元/km²）是 planning-grade 假设，来源写在参数表里，但没有招标价逐条出处。
- "typical city 深入分析"只有郑州有暴露/脆弱度数据；海口、广州只有损失函数反演值。