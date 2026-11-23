BYTES 10715
# 2026 数维杯 C 题真题对标报告

语料范围：`C:\Users\29900\Downloads\AsterLink` 内数维杯优秀论文 124 篇（2019–2025），未引用任何亚太杯（APMCM）资料。
跳过：无（124 篇 PDF 全部成功抽取文本层，0 个文件解析失败）。

## 1. 同型论文清单

| 年份 | 题号 | 队号 | 标题 | 一句话方法 | 与本题的结构相似点 |
| --- | --- | --- | --- | --- | --- |
| 2025 | A | ASHUWEICUP2537139 | 《Active Vibration Suppression of Vehicle Lateral Motion》 | 4-DOF 状态空间（M/C/K）+LQR（差分进化调权 α=50.0、β=0.05）+离散卡尔曼（仅测横向加速度 σ_a=0.01 m/s²） | 只有部分状态可测时的重构+与全状态反馈的差距当上界+能耗代价；C 题 Prob2 是"只有部分观测时预测+花钱买新观测"，同一套"信息换性能"结构 |
| 2022 | C | C2022111514190 | 首页标题即队号（AD 诊断） | 正则清洗 → 空值与实验周期的关系（非随机缺失）→ 递归预测式填充（数据缩减量提升至多 24%）+MissForest → 经验误差 vs 泛化误差比多模型 → SHAP | 缺失机制诊断+留存率口径+失效案例，正是 Prob1 要报的 data retention |
| 2020 | B | B202011151508 | 《Research on Stock Forecasting Method Based on Hidden Markov Model》 | Lyapunov（Wolf）+自相关定延迟+G-P 定嵌入维 → HMM（前向后向/Baum-Welch/Viterbi），隐状态数灵敏度 | 隐状态+观测序列+解码；C 题"作业状态"就是隐状态，它也把"隐状态数怎么定"当成可检验问题 |
| 2024 | C | C2024092929266 | 《Research on Deep Space Navigation Accuracy Improvement Based on Pulsar Timing Noise and Atmospheric Delay》 | RMS+功率谱拟合（81% → AR 模型 99%）+ARIMA（ACF/PACF 定阶）+误差分析 | 残差时序建模与"预测随步长发散"的刻画；Prob2 的"不确定度随缺失时长增长"是同一件事 |
| 2025 | A | ASHUWEICUP2518979 | 首页标题即队号，无独立题名（哈密顿框架下的振动主动抑制） | 正则 Hamilton+复相量+四阶辛 RK+MPC+UKF，把不可测扰动增广进状态再估；R²=0.9718、MAE=1453 N（13.9%） | 不可测量量增广+协方差传播，手位姿缺失段可直接照这个结构做预测与不确定度更新 |

表中论文数字（α=50.0、β=0.05、σ_a=0.01 m/s²、24%、81%→99%、R²=0.9718、MAE=1453 N 等）均引自已获奖论文相应队号（见队号列），不是本题结果；349 个区间、343 个 ≥1.2 s、16/4/4 个 environment 等来自本题题面。

## 2. 可照搬三条

**（1）"天花板基准+三档信息条件"。** 照 ASHUWEICUP2537139 的场景 1/2 对照：Prob2 设三档——全观测（作弊上界）、仅历史（holding last）、按需再观测（本文策略），报同一组指标（预测误差、不确定度、请求次数、累计成本），并写"相对作弊上界差 x%"。它给的是 216.32→162.83→156.19（−24.7%→−27.8%）、相对全状态只退化 4.1%（引自已获奖论文 ASHUWEICUP2537139，不是本题结果）；这种"退化百分比"比单报一个误差更有说服力。

**（2）缺失机制先诊断再填。** 照 C2022111514190：先看缺失与阶段/时段的关系（是否非随机），再选填充方法，最后报可计数结论（它写"数据缩减量提升至多 24%"，引自已获奖论文 C2022111514190，不是本题结果）。C 题 Prob1 应给三套记录各自的"可用区间/总区间"与丢弃原因分布（遮挡、出画、质量旗标），而不是只写"做了清洗"。

**（3）残差过程 → 预测区间随步长变宽。** 照 C2024092929266：对每条通道拟合残差 AR 过程，用 h 步预测方差 σ²(h) 画不确定度包络（它功率谱拟合 81%、AR 后 99%，引自已获奖论文 C2024092929266，不是本题结果），包络超阈值即触发再观测请求——这把"何时请求"从拍参数变成可计算规则。

## 3. 照搬会死两条

**（1）B202011151508 的 HMM 直套会死。** 它的观测是日收益率这种低维标量、状态数 2–3，Baum-Welch 在几千个点上收敛；C 题每手 21 个 3D 关键点×双手×多通道×30 Hz，通道强相关，且题面 L45–46 明确 A hand state must not be directly interpreted as a product state. 硬套会退化成"一帧一个隐状态"（状态数≈帧数），等于没做状态抽象；它唯一的灵敏度结论还是 no significant difference，等于没给选择依据。改法：自定义低维状态（手中心相对货架的法向距离、法向速度、遮挡标志），用线性高斯状态空间+协方差传播，并给维度选择的定量依据（AIC/BIC 或验证集误差）。

**（2）C2022111514190 的"递归预测式填充"会死。** 它填的是同一受试者纵向随访之间的缺口，相邻两次测试间隔已知、可借后测信息；C 题的缺失是"手伸进货架被挡"，缺口内没有同源观测，而且题面 L78–79 规定 returned information cannot be used before its delay has elapsed、L81–82 禁止在没有独立参考时计算真实位置误差。照搬"用未来帧回填"同时违反因果性与评价口径，还会让"预测误差随时间增长"这条曲线变成平的。改法：只用 t 时刻之前的信息做前向预测；在人工遮挡实验里彻底屏蔽未来帧；把"延迟"建成显式状态（信息可用时刻）。

## 4. 本题相对最近邻新增的三条约束

**（1）冻结划分+配对实验。** 题面 L130–133：Training, validation and test sets contain 16, 4 and 4 environments … use the same set of 30 supplied seeds to form 30 trials; all methods receive identical sampled jobs for paired comparison. 往届是随机划分、单次运行，没有配对比较；这意味着不能挑 seed 报最好结果，必须报 30 次的配对差与置信区间。

**（2）信息按价格分级揭示。** L106–109：免费给前 0.2 s，两次付费审查把可见前缀累计到 0.6 s 与 1.0 s，Each review consumes 1 scenario second and 1 cost unit。观测按"三档前缀+延迟+单位成本"分级；全库没有一篇建模"信息分级定价"。

**（3）预留时长的下侧浪费。** L90–93：This reserved service duration is a decision, rather than a known realized duration … if service finishes early, the remainder of the reservation stays occupied and becomes idle time.；L126 设备在 s+max(p,b) 释放。往届加工时间都是已知常数（C20201009824 的 2.9 h、A202111107503 的靠泊时长），这里决策变量带"早完工也浪费"，报多了报少了都亏。

## 5. 评委视角的三条失分点

**（1）只报精度不报留存。** C2024092929266 通篇 R²/拟合优度，没有一条"哪些区间被丢弃、为什么"。C 题 L52–53 要 report data retention 与 failure cases。避免办法：留存漏斗图（349 个区间 → 343 个 ≥1.2 s → 质量合格 → 进训练/验证/测试）+3–5 条失效案例表，写机制而不是写"数据质量问题"。

**（2）不确定度只给标准差当误差棒。** ASHUWEICUP2537139 给了 RMSE 但没给预测区间覆盖率。避免办法：报 PICP（95% 区间的实际覆盖率）与平均区间宽度，画 reliability diagram；覆盖率偏离标称值时说明协方差被低估或高估，并给校准因子。

**（3）再观测策略只调阈值不报代价曲线。** 题面 L75–76 把预测误差、累计成本、等待时间并列为评价量。往年只报单点（C20201009824 的 2.9 h、A202111107503 的 82%）。避免办法：给"成本-误差"前沿，标出 holding last、固定间隔观测、本文策略三个点，并给预算约束下的最优阈值与"阈值±20% 时结果变化"的灵敏度。

## 6. 一句话判词

没有同型题；最接近的是 2025A 的"部分观测重构+与全状态基准比"（ASHUWEICUP2537139）与 2022C 的"缺失机制+留存率"（C2022111514190）；"何时花钱买下一次观测"在 124 篇里 0 命中（optimal stopping、POMDP、particle filter 全 0），难度高于往届 C 题，属"数据+决策"混合型，是四题里评价口径最细的一道。

## 附录：数字口径（可复核）

计数全部在 `E:\数学建模\_swc2026\_bench_txt\*.txt`（124 份唯一文本，PyMuPDF 抽文本层）上用 `E:\Mini\envs\mathmodel\python.exe` 的 `re.findall` 做。

| 报告里的数字 | 出处文件 | 复核串／正则 |
| --- | --- | --- |
| α=50.0、β=0.05、σ_a=0.01 m/s²、216.32→162.83（−24.7%）、4.1% 退化、9570.42 J vs 12296.34 J | 2025_NA_Active_Vibration_Suppression_of_Vehicle_Lateral_Motion.txt | 检索 `50.0`、`0.01 m/s`、`216.32`、`4.1%`、`9570.42`（4.1% 原文即写 degradation of only 4.1%） |
| −27.8%、156.19 | 同上 | 检索 `156.19`、`27.8` |
| 数据缩减量至少提升至多 24%、MissForest | 2022_C_C2022111514190.txt | 检索 `24%`（原文 improve the data reduction by up to 24%）、`MissForest` |
| no significant difference | 2020_B_B_Research_on_Stock_Forecasting_Method_Based_on_Hidden_Markov_Model.txt | 检索该串（1 次） |
| 功率谱拟合优度 81%、AR 模型 99% | 2024_C_2024092929266_Research_on_Deep_Space_Navigation_Accuracy_Improvement_Base.txt | 检索 `81%`、`99%`（原文 81% goodness-of-fit；final model achieved a 99% goodness-of-fit） |
| R²=0.9718、MAE=1453 N（13.9%） | 2025_NA_SHUWEICUP2518979.txt | 检索 `0.9718`、`1453`、`13.9%` |
| 全库 0 命中：optimal stopping／POMDP／particle filter／masking | 124 份 txt | 正则 `(?i)optimal\s+stopping`、`(?i)pomdp`、`(?i)particle\s+filter`、`(?i)masking` 各 0 次；统计含图表与参考文献文字 |
| 0.2/0.6/1.0 s、16/4/4 个 environment、30 个 seed、349/343、8/12/16 jobs | SWC2026_C\problem\problem.txt | L96–99、L106–109、L130–133 |
| PICP 标称 95%、阈值±20% | — | 统计惯例与灵敏度建议，不是论文数据也不是本题结果 |

VERDICT: PASS

## 语料查询记录（可复核）

- 索引文件：`E:\数学建模\.mh\corpus.json`（318,958 B，`count 195`，全部 `contest="数维杯"`；paper 124 / problem 58 / data 9 / appendix 4，年份 2019–2025）
- 查询方式：读取上述 JSON 的 `records[*].title` 与 `records[*].kind`，按关键词逐条匹配后计数（脚本 `E:\数学建模\.agents\skills\mathmodeling\scripts\corpus_index.py`）
- 同题检索：`补货` 0 命中、`货架` 0 命中、`无人超市` 0 命中、`restock` 0 命中
- 相邻主题：`库存` 8 条、`缺失` 10 条、`姿态` 18 条（均为方法相近、题目不同）
- 结论：本题在 195 条数维杯语料中无同题先例；上述相邻主题只用于方法对标，不用于结果对标。

VERDICT: PASS
