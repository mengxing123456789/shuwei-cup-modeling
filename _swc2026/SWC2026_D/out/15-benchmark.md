# 2026 数维杯 D 题真题对标报告

语料范围：`C:\Users\29900\Downloads\AsterLink` 内数维杯优秀论文 124 篇（2019–2025），未引用任何亚太杯（APMCM）资料。
跳过：无（124 篇 PDF 全部成功抽取文本层，0 个文件解析失败）。
先给结论：**D 题在语料里无同型论文**。celestial、parallax、precession、three-body、epicycle、secular 六个词全库 0 命中；唯一一次 "Kepler" 出现在 2021C C202110076198 里，是 kepler.gl 可视化工具名，不是轨道力学。下列四篇是方法上的最近邻，不是同型。

## 1. 同型论文清单（四篇均为"方法最近邻"）

| 年份 | 题号 | 队号 | 标题 | 一句话方法 | 与本题的结构相似点 |
| --- | --- | --- | --- | --- | --- |
| 2025 | A | ASHUWEICUP2518979 | 首页标题即队号，无独立题名（哈密顿正则框架下的振动主动抑制） | 正则 Hamilton 框架+复相量合成力+四阶辛 RK（能量误差有界振荡）+Sobol+±10% MC | 全库唯一能支撑 Task2/Task3"长时间积分下轨道闭不闭合"的方法模板：它证的是"辛格式下能量误差有界"，D 要证的是"长周期极限下轨道遍历成各向同性环" |
| 2024 | C | C2024092929266 | 《Research on Deep Space Navigation Accuracy Improvement Based on Pulsar Timing Noise and Atmospheric Delay》 | RMS+功率谱拟合（81%→AR 模型 99%）+ARIMA（ACF/PACF 定阶）+误差分析 | 领域最近（天文观测+长期残差）；可借它的"残差分解+拟合优度对比"写 Task1 的观测误差，但它的对象是随机噪声，D 的 Task1 是确定性投影 |
| 2024 | A | A2024111130784 | 《Segmented Maximum Likelihood Estimation and NLMS》 | 陷波去噪+FFT+Welch 分段加窗+MLE+NLMS，两条独立路线互证主频（41 MHz／34.98 MHz／56.12 MHz） | 同一物理量的两条独立推导互证，正是 Task1"解析投影 vs 数值作图"该用的写法 |
| 2023 | A | A2023101519958 | 《Modeling and Optimization Control of Compound Helicopters》 | 把缺数据的气动系数拟合成"系数-前进比"多项式 → 力矩分解 → 角加速度 ODE → 姿态角；PSO 优化 | 参数化+ODE+数值积分的格式：Task2 的 ω_r/ω_φ 双共振模型可照它的"参数曲线→方程→积分"三段写 |

表中论文数字（81%→99%、41／34.98／56.12 MHz、I_h 97.20→58.69、Q 15.3→6.8 等）均引自已获奖论文相应队号（见队号列），不是本题结果。

## 2. 可照搬三条

**（1）辛积分 + 守恒量漂移判据。** 照 ASHUWEICUP2518979：Task3 用四阶辛 RK（至少 leapfrog），画"能量相对误差 vs 步数"曲线，证明误差有界振荡而非线性漂移；它的 I_h 97.20→58.69、Q 15.3→6.8（引自已获奖论文 ASHUWEICUP2518979，不是本题结果）是"把物理判据指标化"的写法官样板——D 题应把"轨道闭合"写成可计算量（相邻两周期近拱点角距、能量与角动量的相对漂移）。

**（2）两条独立路线互证。** 照 A2024111130784：Task1 给"解析投影公式"和"数值坐标变换/光线求交"两条路径，两条曲线叠一张图并报最大偏差（角秒或百分比）。它用主频定位与 MLE 互证得 41 MHz（引自已获奖论文 A2024111130784，不是本题结果），这种"两法给同一量、差多少"的写法可以直接搬，也正好回应题面"充分条件不等于充要"的口气。

**（3）参数扫描出相图。** 照 A2023101519958 的"系数-前进比"曲线加分段方程：Task2 以频率比 ω_r/ω_φ 为控制参数扫出"共振带"，带内做长时间积分，用参数-相图加 3–5 条典型轨道叠加呈现；再按题面提示把轨道进动写成"径向振荡+方位角振荡之和"（L74–82），这样每条轨道都能被两个频率定位。

## 3. 照搬会死两条

**（1）ASHUWEICUP2518979 的"保能量即正确"会死。** 它的系统保守且受控，辛结构保能量就等于数值正确；D 题 Task2 的结论是"long-period limits accumulative orbits will form an isotropic uniform symmetric orbital ring"（L64–66），这是相空间遍历性、时间平均的结论，能量守恒推不出来——一条闭合椭圆严格保能量，但显然不是各向同性环。照搬会把"能量有界"误当"轨道均匀"，Task2 的核心结论直接落空。改法：补时间平均的角分布统计量（方位角直方图 + Rayleigh 检验或与均匀分布的 KL 散度），用它判定各向同性，并给"多少个周期后统计量稳定"的收敛曲线。

**（2）C2024092929266 的 AR/ARIMA 长期外推会死。** 它把计时残差当可差分序列外推，81%→99% 是样本内拟合（引自已获奖论文 C2024092929266，不是本题结果），没有样本外验证。D 题 Task1 的差异是确定性几何投影（视差+透视），用 ARIMA 去"预测"观测轨道与真实轨道的差，会把系统偏差写成随机项，方向就错了：视差偏差随真近点角有固定相位关系，AR 模型会把它抹成零均值噪声。改法：解析推导给出偏差的相位结构，数值只用于验证与量级估计，残差项仅用于估计数值误差。

## 4. 本题相对最近邻新增的三条约束

**（1）双视角显式对照。** 题面 L56–60：derive these geometric differences mathematically by using geometric principles combined with optical parallax, and plot these orbital curves programmatically，即"黄道面内单视点看到的轨道"与"真实轨道"两套坐标都要画、都要给公式。语料 parallax 0 命中，没有一篇做过投影差异。

**（2）结论是极限下的统计对称性，不是单条轨道。** L64–66：long-period limits accumulative orbits will form an isotropic uniform symmetric orbital ring with a single dynamical center，且要求用双共振（径向+方位角振荡）模型并保持角动量守恒（L74–82）。往年论文的结论都是"某条曲线/某个数值"，没有"分布的不动点"这种口径——单条闭合轨道与"各向同性环"是两个不同层次的命题。

**（3）要求论证必要性的边界。** L42–48：a sufficient condition does not constitute a necessary-and-sufficient conclusion … alternative orbital models may equally well describe the actual trajectories. 往年没有一篇写"我的结论在什么条件下会被别的模型同样解释"，而 D 题把这条写进了任务描述，等于要求"可反驳性"。

## 5. 评委视角的三条失分点

**（1）把"画轨道"当结果。** A2024111130784 给了 41／34.98／56.12 MHz 三个数却没有不确定度；D 题 Task1 若只画两条曲线、不给偏差量级（最大角偏差、径向相对偏差），会被判"只给图不给数"。避免办法：给偏差随真近点角或时间的曲线，加最大/均方偏差数值，并说明采样密度对偏差估计的影响。

**（2）长时间积分不报步长与守恒量漂移。** ASHUWEICUP2518979 报了能量有界，但没给步长收敛阶。避免办法：三档步长的收敛表（误差比≈2⁴ 才算四阶），同时报能量与角动量的相对漂移；再给"统计量稳定所需周期数"与步长的关系。

**（3）"单中心"结论没有可反驳的对照。** 全库没有一篇设零假设或对照模型。避免办法：设对照组（纯开普勒二体+同一观测窗），用同一个各向同性统计量比较并给定量差别；再讨论"多中心但观测上不可分辨"的情形，说明为什么题设的单中心模型更简约（参数个数、残差）。

## 6. 一句话判词

数维杯 8 届 124 篇里没有天体轨道、视差、共振题（celestial/parallax/precession/three-body/epicycle/secular 全 0 命中，正则见文末附录），D 是语料中完全不存在的新类型，难度最高——它要"解析推导+保结构数值积分+统计对称性证明"三件套，语料里最多只有其中一件。

## 附录：数字口径（可复核）

计数全部在 `E:\数学建模\_swc2026\_bench_txt\*.txt`（124 份唯一文本，PyMuPDF 抽文本层）上用 `E:\Mini\envs\mathmodel\python.exe` 的 `re.findall` 做。

| 报告里的数字 | 出处文件 | 复核串／正则 |
| --- | --- | --- |
| I_h 97.20→58.69（−39.6%）、Q 15.3→6.8（−70%）、20-step prediction / 10-step control | 2025_NA_SHUWEICUP2518979.txt | 检索 `97.20`、`15.3→6.8`、`20-step prediction, 10-step control` |
| R²=0.9718、MAE=1453 N（13.9%） | 同上 | 检索 `0.9718`、`1453`、`13.9%` |
| 41 MHz（主频与 MLE 互证） | 2024_A_Segmented_Maximum_Likelihood_Estimation_and_NLMS.txt | 检索 `41 MHz` |
| 34.98 MHz（NLMS）／56.12 MHz（分段 MLE） | 同上 | 检索 `34.98`、`56.12` |
| 功率谱拟合优度 81%、AR 模型 99% | 2024_C_2024092929266_Research_on_Deep_Space_Navigation_Accuracy_Improvement_Base.txt | 检索 `81%`、`99%` |
| 全库 0 命中：celestial／parallax／precession／three-body／epicycle／secular | 124 份 txt | 正则 `(?i)celestial`、`(?i)parallax`、`(?i)precession`、`(?i)three[\s\-]?body`、`(?i)epicycle`、`(?i)secular` 各 0 次；统计含图表与参考文献文字 |
| Kepler 仅 1 次 | 2021_C_C202110076198.txt | 正则 `(?i)kepler` 全库 1 次、落在该文件，上下文为 kepler.gl 可视化工具名 |
| 1580–1600、充分条件非充要、isotropic uniform symmetric orbital ring | SWC2026_D\problem\problem.txt | L15–32、L42–48、L64–66 |
| 2⁴ 收敛阶、步长三档、Rayleigh／KL 统计量 | — | 数学性质与方法建议，不是论文数据也不是本题结果 |