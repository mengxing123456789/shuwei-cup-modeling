# Round 3 修订记录（Q5 面积口径 bug 修复及其连锁修正）

日期：2026-11-17 晚
触发：arbiter2 独立复评（74/100，C）发现 Q5 损伤函数不含面积。

## 1. 根因与修复

**Bug**：`s06_q5.py` 与 `s08_q5_sp.py` 的损伤式为
`dmg = ref_loss * (over / over_ref) ** gamma`，其中 `ref_loss = OFFICIAL_LOSS`（郑州 409 亿），
完全没有面积项。后果：230 km² 的海口与 1180 km² 的郑州在同一溢出深度下损失相同，
海口的 EAD 被高估约 4.1 倍，"只有海口值得投资"这一结论是伪结论。

**修复**（四个脚本同构，全部用 edit/write，不用 PowerShell 改 .py）：
- `s06_q5.py` 新增 `city_loss_scale(area_km2, gamma) = OFFICIAL_LOSS * (area/area_z) ** gamma`；
  输水成本改为按面积计价的 `pipe_cost_per_mm_km2 = 1.0e9/1180.0`。
- `s06b_q5_selective.py` 新增 `city_ref_loss(area_km2, area_z, gamma)`，同样 `** gamma`。
- `s08_q5_sp.py` 内联同一换算，capex 用 `pipe_cost_per_mm_km2 * area * cadd`。
- `s06c_q5_sensitivity.py` 的 `plan_bcr` 改用 `Q5.city_loss_scale(...)`。
- 新增 `s10_q5_compare.py`：出 `fig21_bcr.png`（均匀 vs 热点，同城同钱）与 `q5_menu_comparison.csv`。

幂次用 `** gamma` 而不是线性面积，是为了与"损失按溢出体积的 1.5 次幂增长"这一主假设保持一致；
线性面积会与主假设矛盾。

## 2. 结论翻转（论文已全部改写）

| 口径 | 旧（错） | 新（对） |
|---|---|---|
| 均匀升级最优 | 海口 1.63（80 mm）、2.10（5 mm）"只有海口划算" | 三城全不投资；网格最高 0.28 广州 / 0.18 海口 / 0.10 郑州 |
| 热点定向最优 | 30.4 海口 / 3.14 广州 / 1.50 郑州 | 4.05 广州 / 2.62 海口 / 1.50 郑州（城市序反转） |
| 随机规划无约束 | 海口蓄水 112.5 mm、比值 1.47 | 三城全部 status quo |
| 随机规划风险上限 | 海口 2.00/1.49/1.20 | 海口 0.17/0.13/0.11；广州 0.27/0.21/0.17；郑州 0.10/0.085/0.068 |

城市排序反转的原因：热点投资看的是**绝对损失密度**，广州 1400 km² × 11.31 亿的暴露
压过海口更高的设计深度。这一条比原来的"海口最优"更有解释力，也更符合 2021 郑州的实际
（郑州不是雨最大的城市，是损失最重的城市）。

## 3. 其他修订（arbiter2 清单）

1. **Shapley 表述错误**：原文"for a product the Shapley value collapses to the log-share"是错的。
   `v(S)=∏_{i∈S} f_i` 时 Shapley 值 = `(∏f_i − 1)/n`（等分），不是 log 份额。
   已改：正文说明两种口径（水平分解 31.3/33.6/32.7/2.5% 与对数分解 31.1/34.1/32.9/2.0%）
   分别回答"水平问题"和"比率问题"；`s09_q4_shapley.py` 的 `note` 同步改正，
   `fig24` 改画 `shapley_share` 并把轴标签改为 "Share of the 23.9-fold loss gap"。
2. **1.4e8 无结果档支撑**：`s02_q1.py` 峰值小时段原来用 `(201.9−cap)*area*1e6*0.9`，0.9 系数无出处。
   已改为把 201.9 mm 过 SCS-CN（CN 85）得产流 156.562 mm，再减设计容量：
   36 mm/h → 120.562 mm × 1180 km² = **1.4226e8 m³**；同时新增
   `hours_to_drain_3day_runoff`（7.37 h）与 `hours_to_drain_3day_rainfall`（8.71 h）两个口径，
   论文正文统一用径流口径 7.4 h。
3. **Task 3 排名表述**：原文"Haikou, Guangzhou, Hohhot, Nanjing and Wuhan … Zhengzhou ranks sixth"
   与表 8（按 p10）不符。已改为"Fuzhou, Haikou, Guangzhou, Hohhot 领先；郑州概率第 16、综合第 10"。
4. **s8 残留旧比值**：CN 敏感性 1.80→3.18 改为 0.155→0.274；估计量 2.10→2.08 改为 0.181→0.179；
   "51.5%"、"2.12"、"0.96"、"1.63/1.65" 等旧口径数字全部删除或替换。
5. **符号冲突**：`S` 同时表示 SCS 滞留参数与蓄水深度。已拆为 `S_ret` 与 `S_sto`，
   随机规划决策变量改 `C_add`/`S_sto`，符号表同步。
6. **文献**：`[11]` 原只有 Hosking 1985（PWM 估计），新增 Hosking & Wallis 1993（H 统计量）
   与 Hosking & Wallis 1997（index-flood 专著），按首引顺序排在 [11][12]，全文 16 条。
7. **图注**：`fig21` 图注原描述"economic vs with deaths valued"与改后的图不符，
   已改为"两个菜单在同城同钱下的最高比值"；`fig24` 图注改为水平份额。
8. **页数**：加三项升级后一度 34 页（正文 21）。通过缩小 fig23（0.62→0.44）、
   优缺点列表改 `\small`、结论段压缩，回到 **正文 20 页 / 含摘要目录 22 页**，总 34 页。

## 4. 终态

- `04_paper/main.pdf`：34 页。p1 摘要（单页，含 9 关键词）、p2 目录、p3–p22 正文（20 页）、
  p23–24 References（16 条）、p25–34 附录（A 符号 / B 参数来源 / C 数据 / D 代码 / E 补充图）。
- 自检：图 23、表 16、展示公式 19、词 10162、占位符 0、无 undefined reference/citation。
- 编译：`pdflatex -interaction=nonstopmode main.tex` 两遍，exit 0。

## 5. 教训

- **量纲检查要写在代码里，不只在脑子里**：`ref_loss * (over/over_ref)**gamma` 看起来像
  "归一化到参考事件"，实际上把城市的规模信息丢了。凡是"以某城市为锚"的公式，
  必须显式写出锚城市与目标城市之间的换算因子。
- **一个 bug 会污染整条结论链**：这个 bug 让 Q5 从"海口划算"翻转成"谁都不划算、
  只有热点划算"，摘要、§7、§9、图 21 全部要重写。所以每轮评审后先跑一遍
  "结论是否仍然成立"的复核，比逐字改数字更省事。
- **独立复评的价值**：四个评审里只有 arbiter2 去读了代码，才抓到这个问题。
  只读 PDF 的评审不可能发现它。
