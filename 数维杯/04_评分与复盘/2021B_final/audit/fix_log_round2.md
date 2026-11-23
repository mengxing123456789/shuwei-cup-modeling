# 修订日志（第二轮：final-arbiter 复核后）

日期：2026-11-17　执行：lead　基准：`05_audit/main_draft.pdf`（31 页）

| # | final-arbiter 指出的问题 | 严重度 | 处理 | 落点 / 证据 |
|---|---|---|---|---|
| 1 | 排水时间三套口径：p9 用 313.4/36=8.7 h，却写 265.4 mm 径流；p20 用 8.3–6.4 h | −3.5 | 统一到径流口径 | `s3_q1.tex:98` 改 7.4 h（一年一遇）/5.3 h（三年一遇）；`s8_eval.tex:40` 8.7→7.4；摘要同步改 7.4 |
| 2 | Task 4 恒等式差 1.066：23.9 ≠ 2.68×2.95×2.84 = 22.4 | −3 | 显式写出面积比残差 | `s6_q4.tex:48` 加"167000/156700 = 1.07"；`s8_eval.tex:46` 与摘要改写为"面积归一后 22.4，余 ×1.07 为面积比" |
| 3 | 摘要溢出：`\enlargethispage` 把关键词推出可印区 | −2.5 | 删除该命令，正文压掉约 90 词 | `summary.tex` 重写；`pdftotext` 复核 p1 末尾即 `CVaR`，p2 为 Contents |
| 4 | "composite" 排序无定义，"郑州第六"不可复现 | −2 | 定义 composite = p10 秩与回归秩的均值，并改用 p10 单口径 | `s5_q3.tex:80` 重写；表 8 换成 `q3_risk_table.csv` 的 LM p10 前十；郑州 p10 第 16、composite 第 10 |
| 5 | 表 3 的 T=5/10/20 置信区间印成 "–" | −1 | 补齐 | `s3_q1.tex:61` 填 [95.1,118.6]、[109.1,140.5]、[120.3,165.3] |
| 6 | p18 "3.7 expected deaths avoided"（应为 3.95） | −0.5 | 改 3.95（7.67−3.72） | `s7_q5.tex:41` |
| 7 | "reverses the verdict for every city" 与表 12 冲突（郑州两格 <1） | −0.5 | 改为"有密集核心的城市"，并标出 1.06/0.71 | `s7_q5.tex:66` |
| 8 | p20 "449 mm 未换算重现期" 与 p8 已给 1.6e8 yr 矛盾 | −0.5 | 改为"只作量级引用，区间 678 yr–∞" | `s8_eval.tex:9` |
| 9 | 表 16 漏 `s06c_q5_sensitivity.py` | −1 | 代码表补齐 s02b / s04b / s04c / s06c 四个脚本 | `appendix.tex:88-96` |
| 10 | p20 误引 Appendix A（应为 B，参数表在 `app:params`） | −1 | 改 `\ref{app:params}` | `s8_eval.tex:5` |
| 11 | 符号表 `O = (X−C)+` 与正文 `Q(X)−C` 冲突 | 口径 | 改为 $(Q(X)-C)^+$ 并注明 Q 为 SCS 产流 | `appendix.tex:26` |
| 12 | $O_{\rm ref}$ 行把 162.4 标成 $Q(313.4)$ | 口径 | 写成 $Q(313.4)-RL_{3d}(2)=265.4-102.9=162.4$ | `appendix.tex:54` |
| 13 | fig20 图注称横轴为 design standard、"optimum at left edge" | 规范 | 改为 annualised investment；星标为各城社会最优（海口 2 年+80 mm，郑州仅 2 年） | `appendix.tex:175` |
| 14 | fig15 图注仍写"ten-year expected maximum" | 规范 | 改为 $p_{10}$ 前十 + RL10 | `appendix.tex:163` |
| 15 | p12 "the weakest 0.598 and 1/5" 跨方法拼接 | 规范 | 改 0.598 with 2/5，并说明有模型仅 1/5 | `s5_q3.tex:50` |
| 16 | 集中度差 0.60−0.47=0.13，文中写 0.134 | 规范 | 改 $|0.602-0.468|=0.134$（印刷精度 0.13） | `s6_q4.tex:33` |
| 17 | 表 15 "Wu Lu Mu Qi" 与正文 Urumqi 不一致 | 规范 | 统一 Urumqi | `station_table.tex:22` |
| 18 | 表 12 列序 m20 在 m10 之前 | 规范 | 重排为 m10、m20 两两相邻，数值随列同步 | `s7_q5.tex:57-61` |
| 19 | 1.4e8 m³ 无结果档支撑（旧 JSON 为 1.76e8） | 可复现 | 新增 `s02b_q1_peak.py` → `q1_peak_hour.json`：156.6−36=120.6 mm×1180 km² = 1.4226e8 m³ | `03_results/q1_peak_hour.json` |
| 20 | p10 与 RL 用两套拟合，风险表不可复现 | 可复现 | 新增 `s04b_q3_risk_table.py`：同一次 LM 拟合算 p10 与 RL；`s04c_q3_risk_figs.py` 重画 fig14/fig15 | `03_results/q3_risk_table.csv`、`q3_risk_table.json` |

## 修订后自检

- `main.pdf`：**31 页**；摘要 p1（关键词完整）、目录 p2、正文 p3–p22（**20 页**）、References p23、附录 p24–p31。
- 两条页数限制：正文 20 ≤ 20；摘要+目录+正文 22 ≤ 24。
- 编译无 `Reference undefined`、无 `Citation undefined`；Overfull 均 ≤ 6.6 pt。
- 图表：21 图、16 表、17 个展示公式；占位符 0。
- 数字层：正文引用的 Q5 标定值、Q1 峰值余量、Q3 风险表均可在 `03_results/` 找到唯一来源。

## 仍未处理的已知弱点（写在论文 §8.3 里，不再掩盖）

- 年最大值 i.i.d. 未做正式检验；5–7 个留出年使 Q3 的误差区间很宽。
- 损失幂律 γ=1.5 由单次事件标定，只能靠 §8.1 的范围给不确定性。
- 无水力模型：内涝是水量平衡估算，不是管网演算。
- Q4 分解是恒等式，不是因果识别。