# 归档清单：2021 数维杯国际赛 B 题实战演练

归档时间：2026-11-17（round 4 后重新归档）　执行：lead

## 交付物

| 文件 | 说明 |
|---|---|
| `2021B_practice_paper.pdf` | 终稿 34 页；摘要 p1、目录 p2、正文 p3–p22（20 页）、References p23–24、附录 p25–34 |
| `src/*.tex`, `src/*.py` | 14 个 LaTeX 源文件 + 17 个 Python 脚本（含 `s10_q5_compare.py`、`s07_q3_regional.py`、`s08_q5_sp.py`、`s09_q4_shapley.py`） |
| `results/*.csv, *.json` | 全部正文数字的唯一来源（59 个文件 + `ghcn/` 原始数据） |
| `figures/*.png` | 30 张图（论文引用 23 张，其余为过程图） |
| `audit/纪律声明.md` | 隔离规则：未查任何 2021 B 题答案论文 |
| `audit/fix_log.md`、`fix_log_round2.md`、`fix_log_round3.md`、`fix_log_round4.md` | 四轮修订的逐条问题 → 处理 → 落点 |
| `audit/自主评分报告_2021B.md` | 四评审 + 终审 + 两轮独立复评的八维评分与分数估计 |
| `audit/page_map.json`、`selfcheck_report.json`、`paper_text.txt` | 页数核算、自检、逐页文本 |

## 指纹

- PDF：SHA256 `E860EA6345349AE560C1A56499940854A92C199253FF2845CF617292EDE497FE`，3,023,735 字节，34 页
- 编译：`pdflatex -interaction=nonstopmode main.tex`（MiKTeX，E:\MIKTEX），exit 0，无 undefined reference/citation
- 运行环境：`E:\数学建模\数维杯\.venv`（Python 3.11，numpy 2.2.6 / pandas 2.2.3 / scipy 1.15.3 / scikit-learn 1.6.1 / matplotlib 3.10.1）

## 硬性检查

| 项 | 结果 |
|---|---|
| 正文 ≤ 20 页 | PASS（p3–p22，20 页） |
| 摘要+目录+正文 ≤ 24 页 | PASS（22 页） |
| 摘要单页、关键词完整 | PASS（p1 末行为 9 个关键词） |
| 匿名 | PASS（页眉仅 `Team # 2021B-PRACTICE`） |
| 参考文献编号且被引用 | PASS（16 条，首引次序即编号） |
| 占位符 / TODO | PASS（0 命中） |
| 交叉引用 | PASS（label 与 ref 双向核对） |

## 五问与主要结论

| 任务 | 方法 | 结论摘要 |
|---|---|---|
| Q1 郑州降水与内涝 | MK+Sen、Pettitt、GEV（MLE+bootstrap）、SCS-CN | 总量不显著（+1.19 mm/dec, p=0.92），湿日 −2.0/dec（p=0.021），强度 +0.23（p=0.062），ξ=−0.026；2021-07-20 日值 188.7 mm＝54 年经验/151 年拟合，三日 313.4 mm＝6.4×10³ 年；峰值小时产流 156.6 mm 超一年一遇容量 120.6 mm，即 1.42×10⁸ m³，三日径流需 7.4 h 排完 |
| Q2 全国趋势 | 25 城、单一 BH 族 146 个有限检验、k-means | 仅 2 个总量、1 个日极值趋势通过 FDR，而强度 7 个、湿日 9 个（按指标分族则为 1/1/1/11/13）；六带总量：北方 −6.4、东北 +4.6、西北 +12.5、长江 +20.2、华南 +21.5、西南 −27.1 mm/dec |
| Q3 未来极端城市 | 10 种策略 + 区域频率分析（index-flood、Hosking–Wallis） | 目标定义比分布选择更重要（RMSE 64.8→55.7，bias −41.5→−20.5）；EVT 排序优于 ML（top-5 重合 4/5 vs 3/5）；全国池化被 H1=2.56 否掉，k=2 两组齐性（H1=0.22/0.03），池化只买 ≤1.2 mm；p10 前十由福州、海口、广州、呼和浩特领跑，郑州第 16 |
| Q4 两类暴雨 | 6 指标 + 类型判据 + 损失恒等式与 Shapley 分解 | 郑州＝强度型（日值 134 年一遇，单日占 52%），太原＝持续型（9.5 年一遇，集中度处第 6 百分位）；损失比 23.9 = 面积 1.07 × 密度 2.68 × 受灾比例 2.95 × 人均损失 2.84；Shapley 份额 31.3/33.6/32.7/2.5% |
| Q5 长期建设 | 30 年组合优化 + 场景随机规划（CVaR95 约束） | **均匀升级三城全不划算**（网格最高 0.28 广州 / 0.18 海口 / 0.10 郑州）；护住 2% 高暴露区后 4.05/2.62/1.50（城市序反转，因绝对损失密度决定）；加 CVaR95 上限后无约束解全为 status quo，风险受限方案比值均 <0.28，故风险上限是"约束"不是"投资" |

## 复现步骤

```powershell
$py = "E:\数学建模\数维杯\.venv\Scripts\python.exe"
cd "E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code"
& $py s01_prepare.py
& $py s02_q1.py; & $py s02b_q1_peak.py
& $py s03_q2.py
& $py s04_q3.py; & $py s04b_q3_risk_table.py; & $py s04c_q3_risk_figs.py
& $py s07_q3_regional.py
& $py s05_q4.py; & $py s09_q4_shapley.py
& $py s06_q5.py; & $py s06b_q5_selective.py; & $py s06c_q5_sensitivity.py; & $py s08_q5_sp.py
& $py s10_q5_compare.py
cd ..\04_paper
& "E:\MIKTEX\miktex\miktex\bin\x64\pdflatex.exe" -interaction=nonstopmode main.tex
```

种子：20210720（全部参数 bootstrap 与 Monte Carlo 齐性检验）、0（k-means / RF / GBR）；`s05_q4.py` 与 `s09_q4_shapley.py` 不用随机数。

## 已知局限（论文 §8.3 已写明）

- 年最大值 i.i.d. 未做正式检验；留出窗口只有 5–7 个有效年。
- 损失幂律 γ=1.5 由单次事件标定，只用 §8.1 的范围表达不确定性。
- 内涝为水量平衡估算，无管网水力演算。
- Q4 的分解是恒等式 + Shapley 归因，不是因果识别。
- 区域频率分析的分组依赖 k-means，k 的选择影响群组数；H1 的蒙特卡洛只有 400 次。
- Q5 的三项单价（输水 1e9 元/mm·1180km²、蓄水 800 元/m³、海绵 1.5e8 元/km²）是量级估计，不是招标价。

## 修订史

| 轮次 | 页数 | 评审分 | 关键修正 |
|---|---|---|---|
| 初稿 | 29 | 78.5（B） | 13 处数字口径、摘要溢出、composite 无定义、表 3 缺 CI |
| round 2 | 31 | 74（C） | **Q5 损伤函数漏面积项（真 bug）**、Shapley 表述、文献覆盖 |
| round 3 | 34 | 83.5（B） | 结论翻转为"均匀升级不划算 + 热点定向"、新增三项升级（区域频率 / 随机规划 / Shapley） |
| round 4 | 34 | 估算 85–89（A 边缘，未经独立复评） | FDR 族 146、ξ 逐窗口、海口三档、站点账、表 5 中位数、脚本表与种子 |

详见 `audit/fix_log*.md` 与 `audit/自主评分报告_2021B.md`。
