# D 题：要求清单与参考材料的数学审查

题面：`problem/problem.txt`，106 行，4 页。本文只做一件事：把「要求你做什么」逐句钉到行号上，
把已知 / 未知 / 待假设分开，再把题面给出的参考材料逐条判定。模型本身见 `out/01-model.md`，
数字见 `out/03-numbers.md`。

---

## 1 题面要求（逐句摘录，标行号）

### 1.1 背景里给出的四条「开普勒不足」（题面 i 节）

这四条不是提问，是题面已经下的判断。T3 要我们「show」它们，所以它们同时是待证命题。

| # | 原文（行号） | 它要求证明什么 |
| --- | --- | --- |
| B1 | L15–24 "the orbital observational data used by Kepler is incomplete in the spatial dimension… determining true orbit requires observations from at least three mutually orthogonal directions—corresponding, in engineering terms, to a three-view orthographic representation. … observations were obtained from only a single terrestrial viewpoint" | 单一视点 ⇒ 状态不可完全重构。可数化的说法：观测量个数 < 未知量个数 |
| B2 | L27–34 "the observational data were also temporally incomplete. … concentrated in the interval from 1580 to 1600. … The actual radial resonant period may be extremely long (possibly several centuries)." | 有限时间基线识别不了长周期模 |
| B3 | L35–41 "The strictly elliptical (or circular) orbits derived from the inverse-square law … constitute an exact solution to a mathematically integrable two-body conservative system. A real planetary system, however, is a non-integrable multi-body dissipative system … exhibits chaos and resonance." | 椭圆轨道是降阶参考模型，不是真实动力学 |
| B4 | L42–48 "a sufficient condition does not constitute a necessary-and-sufficient conclusion. … alternative orbital models may equally well describe the actual trajectories." | 从椭圆反推万有引力只是充分条件 |

### 1.2 Task 1（L53–60）

| 要求 | 原文 |
| --- | --- |
| T1-a 数学推导 | L53–54 "Derive mathematically and plot programmatically" |
| T1-b 设定观测视角 | L54–57 "From the observational perspective on Earth, remote measuring and mapping the orbital curve of a planet in the solar system, such as Venus or Mars, involves a certain angle of view—either looking down or looking up perspective." |
| T1-c 差异的对象 | L57–58 "geometric discrepancies between the observed orbital shape and the true orbit that is depicted from a viewpoint perpendicular to the planet's orbital ecliptic plane" |
| T1-d 必须用视差 | L58–60 "derive these geometric differences mathematically by using geometric principles combined with optical parallax" |
| T1-e 必须出图 | L60 "plot these orbital curves programmatically" |

注意 T1-c 的「真轨道」被定义为**垂直于黄道面俯视**看到的那条，不是三维轨道本身。所以本题至少要区分三个对象：
三维真轨道、黄道面俯视图、地球方向视图。三者两两不同（本文 §2 表 1 给数字）。

### 1.3 Task 2（L61–66）

| 要求 | 原文 |
| --- | --- |
| T2-a 建模对象 | L61–63 "Create and develop a new 'Model for the Sole Centrism of a Stellar System and Closures of Planetary Orbits' by some methodologies of mathematics and physics" |
| T2-b 方法限定 | L64 "dual-resonance (radial and azimuthal oscillatory motions) model should be used" |
| T2-c 核心结论 | L65–66 "with a core conclusion long-period limits accumulative orbits will form an isotropic uniform symmetric orbital ring with a single dynamical center" |

T2-c 是一个复合断言，拆成四个可分别检验的子命题，本文逐个判：

- C1 长周期累积轨道形成**环**（ring）；
- C2 该环**各向同性**（isotropic，即方位角分布不挑方向）；
- C3 该环**均匀**（uniform，即方位角密度是常数）；
- C4 存在**唯一动力学中心**（single dynamical center）。

### 1.4 Task 3（L67–71）

| 要求 | 原文 |
| --- | --- |
| T3-a 编程出轨迹 | L67–68 "Basing on the above equations present the geometric trajectories of planetary motions by a computer programing" |
| T3-b 由轨迹显示开普勒不足 | L69–71 "From above demonstrating the computed geometric trajectories of planetary motions, could be shown that Kepler's laws have been found to have significant deficiencies in both accuracy and rigor" |

T3-b 是「show」，不是「assert」。所以必须给可观测量在开普勒模型下的值与在本文模型下的值，
且两者之差要超出可分辨的尺度，不能停在文字层面。

### 1.5 Solving Tips（L74–82）——这段是题面给的路线，不是结论

| 原文 | 它建议什么 |
| --- | --- |
| L74–77 "please refer to Newton's study of spiral motion in a resistive medium [8], and to DTQ Law by James Deng's SDP atomic model [9-12] (which shows radial resonances), we propose that orbital precession can be considered the sum of independent radial and azimuthal oscillatory motions." | 进动 = 径向振荡 + 方位角振荡之和 |
| L77–78 "A parametric dual-resonance model is constructed, angular momentum is conserved" | 参数化双共振 + 角动量守恒 |
| L78–82 "it can be shown that the long-term cumulative orbit converges to an isotropic uniform ring; thus, the idea of a single dynamical center is supported." | 长周期 ⇒ 均匀环 ⇒ 单中心 |

最后一句是**逻辑跳跃**（环均匀不能推出单中心），本文在 §3 第 4、7 条处理。

---

## 2 已知 / 未知 / 待假设

### 2.1 已知（题面给的，或标准力学里的常量）

| 项 | 值 / 内容 | 出处 |
| --- | --- | --- |
| 参考行星 | Venus、Mars（T1 点名） | L55 |
| 观测者位置 | 地球，位于黄道面内，单一视点 | L22–24 |
| 时间基线 | 1580–1600，20 年 | L29–30 |
| 力律 | 平方反比（牛顿）为标准基线；题面要求允许偏离 | L35–37 |
| 水星近日点进动观测值 | 43.1 角秒/世纪（异常部分） | 外部常量，本文作为对照量，标为 `NOT-APPLICABLE` 型常量而非数据 |
| 光速 | 299 792.458 km/s | 同上 |

水星 43.1″/世纪不是赛题给的附件数据 —— 本题无数据附件。它在 `data/t3_kepler.json` 里记作
`mercury.observed_anomalous_arcsec_per_century`，属于「教科书常量类基线」，不是 measured data。
G2 的判定按 `NOT-APPLICABLE`（本题无官方数据附件）走。

### 2.2 未知（必须由建模解答的）

| # | 未知 | 由哪一问回答 |
| --- | --- | --- |
| U1 | 地球方向的视轨道与黄道面俯视图差多少 | T1 |
| U2 | 能否仅凭视轨道反推倾角 i | T1（判据） |
| U3 | 视差在解析上是什么阶的修正 | T1 |
| U4 | 什么参数下「累积轨道」是环、什么参数下不是 | T2 |
| U5 | 角动量在什么意义下守恒、摄动下如何演化 | T2 |
| U6 | 「单一动力学中心」的数学定义是什么，本模型里成立否 | T2 |
| U7 | 开普勒三定律各在哪一步失效、失效多大 | T3 |

### 2.3 待假设（本文引入的，须在正文声明并给失效条件）

| # | 假设 | 为什么必须加 | 失效条件 |
| --- | --- | --- | --- |
| A1 | 行星质量 ≪ 恒星质量，恒星固定于原点 | 否则是二体相对运动，力心会跑 | 质量比 > 1e-3 |
| A2 | 观测在星心 gnomonic 图卡（切平面标准坐标 ξ=tan）上记录 | 视曲线的代数次数依赖图卡选择；方向余弦图下「精确视曲线是圆锥曲线」不成立 | 用全天球方向余弦记录 |
| A3 | 摄动只保留 m=2 的静态谐波项 ε r² cos 2φ | 双共振需要离散的角向谐波；连续谱没有锁相 | 摄动含 m≥3 或多个频率 |
| A4 | 进动按 Δφ = π·ω_φ/ω_r 累积（即每半个径向周期进动一次） | 这是「径向 + 方位角独立振荡」的量化形式，题面 L76–77 的路线 | 径向与方位角不独立（强耦合） |
| A5 | 环的「均匀」用方位角边缘分布的 KS 距离度量 | 二维均匀性不能用一维检验代替，故另配 fill factor | 只关心径向结构时 |

A2 是本轮最重要的假设：它不是技术细节，它决定 T1 的结论长什么样。本文 §3 第 1 条会说明
为什么不能悄悄换掉。

---

## 3 参考材料逐条判定

题面 L74–82 与参考文献 [8]–[12] 的主张，逐条判「可形式化 / 需修正 / 不成立」。
只评数学内容，不评来源。

**第 1 条｜"orbital precession can be considered the sum of independent radial and azimuthal oscillatory motions"（L76–77）**
判定：**可形式化**。
根据：写成相位变量即得闭式。径向周期 T_r、方位周期 T_φ，每半个径向周期拱线进动一次，
Δϖ = π·ω_φ/ω_r，等价于每圈进动 Δφ − 2π = 2π(ω_φ/ω_r − 1)。本文取 c ≡ ω_φ/ω_r，
则 ϖ̇ = ω_φ − ω_r，闭合条件 c ∈ Q。数值见 `t3_kepler.json:law1.dphi_minus_2pi_deg` = 179.993°，
与解析 2π(c−1) = 180° 差 0.007°（辛积分截断误差）。这条是题面路线里唯一一条完全站得住的。

**第 2 条｜"angular momentum is conserved"（L78）**
判定：**需修正**（缺条件）。
根据：L = r×v 守恒的充要条件是力始终沿 r，即中心力。SDP 若含径向谐振子项，势是 V(r) 而非 V(|r−O|)，
则 L 不守恒。本文给可判定的形式：把力心平移 δ，dL′/dt = −δ×F，故 |L′| 的漂移随 |δ| 线性增长。
数值 `t2_resonance.json:sole_centrism.drift_power` = 1.052 ± 0.019，δ=0 时漂移 2.17e-13。
所以「角动量守恒」在同一条主张里既对（中心力）又错（一旦把力心挪开），必须带条件说。

**第 3 条｜"the long-term cumulative orbit converges to an isotropic uniform ring"（L78–81）**
判定：**需修正**（只在 c 无理时成立，且「收敛」这个词用错）。
根据：累积轨道是环面上的像。c = q/p 有理 ⇒ φ = (q/p)θ_r 锁相，像是闭合的 p 瓣玫瑰线，
一维、Lebesgue 测度零，二维占据率 fill = 0.465；c 无理 ⇒ 稠密（Weyl 等分布），fill = 0.971。
不是「收敛到」，是「稠密填充」—— 有限时间永远只是有限条弧。数值见
`t2_resonance.json:dichotomy.rational_max_fill` / `irrational_min_fill`。

**第 4 条｜"thus, the idea of a single dynamical center is supported"（L81–82）**
判定：**不成立**（推理无效）。
根据：单中心是势的函数形式决定的，与共振、与环是否均匀都无关。V = −μ/r + γ/r² 是中心力，
无论 c 取什么值、轨道闭合与否，关于原点的 L 严格守恒（数值漂移 2.17e-13）。
反过来，环均匀（c 无理）与轨道闭合（c 有理）在同一条轨道上**互斥**：闭合是测度零的曲线，
均匀填充要求二维。所以「均匀环 ⇒ 单中心」这条链两头都对不上，中间那步是空的。

**第 5 条｜"dual-resonance … radial resonances"（L64, L76）**
判定：**可形式化**，但要指明共振比。
根据：c = 3/2 恰是 2ω_φ = 3ω_r，与静态 m=2 扰动的 Lindblad 条件 mω_φ = lω_r（m=2, l=3）重合。
锁相后径向宽度被分界线 dJ_sep = 2√(ε/β) 界住，数值比 0.999688（`resonance_bound.pendulum`）。
非共振参数下没有这个 √ε 标度，只有线性响应。所以「双共振」这个词必须带比，否则是空话。

**第 6 条｜"Newton's study of spiral motion in a resistive medium [8]"（L74–75）**
判定：**可形式化，但与本题结论相反**。
根据：阻力介质里轨道是收缩螺线，机械能单调减，环半径随时间单调缩小，没有稳态环。
它能提供的是「非闭合轨道」的例子，不能提供「均匀环」。题面把它列在 T2 路线里，是把「不闭合」
和「收敛到环」混成一件事。本文因此不用阻力，改用中心力 + 角向谐波（保守），这样 L 才守恒。

**第 7 条｜"Kepler's laws have been found to have significant deficiencies in both accuracy and rigor"（L12–13, L69–71）**
判定：**需修正**（第三条定律的「不足」不是普适的）。
根据：本文把三条分别量化。第一定律失效：γ≠0 时吻切根数不收敛、拱线每周期进动 179.997°；
第二定律在中心力下**严格成立**（dA/dt 相对偏差 1.05e-13，只剩积分器截断），只有非中心扰动才撬开
（四极 ε=1e-2 时 3.3%）；第三定律在 γ 模型下**结构上不可见** —— a_obs 与开普勒 a_K 代数恒等，
2×斜率仍精确 3.000，要撬开它必须引入非中心扰动（2.906，95% CI [2.817, 2.994]）。
所以「三条都失效」这个笼统说法不对：第二、三条在中心力变形下是看不见的，题面得指明失效机制。

**第 8 条｜"determining true orbit requires observations from at least three mutually orthogonal directions"（L17–19）**
判定：**需修正**（数目对，理由不对）。
根据：不是「必须三个正交方向」，而是「观测量个数必须 ≥ 未知量个数」。正交投影下的外观椭圆只给
2 个无量纲量（短长轴比、主轴方位 ψ），未知量是 (e, ω, i, Ω) 共 4 个，亏 2 维 —— 实测存在 378 个
精确解（`identifiability.n_family_members`）。而视差把 i 与 Ω 的退化 (i,Ω)→(π−i, Ω+π) 按
(a/d_E)² 撬开，所以「时间基线 + 有限距离」可以替代部分视角，判据 d_E/a ≳ 1/√σ。
三个正交方向是充分而非必要的，题面这句把工程直觉当成了几何定理。

---

## 4 本轮交付边界

做：三问的模型、全部数值实验、10 张图、数字表、参考材料审查。
不做：整篇论文、LaTeX 排版、PDF 编译、参考文献格式。`problem/` 全程只读。

---

## 5 写作阶段的 8 条硬约束（从 `RULES.md` 摘，本轮已遵守）

1. **R-E01** 只用 `E:\Mini\envs\mathmodel\python.exe` 跑代码，不换解释器。本轮全部脚本用它。
2. **R-E02** 每次执行前设 `PYTHONIOENCODING=utf-8`，否则中文路径下的 print 会崩。
3. **R-E10** 执行前把 `E:\Mini\envs\mathmodel\Library\bin` 前置到 PATH —— 缺这条会触发 MKL 0xC06D007F
   （无 Python 栈的原生崩溃）。本轮踩过一次，记在这里。
4. **R-M01** 正文每个外部数字要能追到 `data/ledger.json` 的条目（带 sha256），或标 `NOT-APPLICABLE` 的
   常量基线。本题无数据附件，水星 43.1″/世纪 走后者。
5. **R-W03** 每个数字写清口径：单位、参考系、拟合点数、误差定义。`out/03-numbers.md` 逐行带单位与键。
6. **R-W06** 禁止「众所周知 / 显而易见 / 易得 / 显然」。本轮所有公式都给了出发方程与近似阶，
   没有一处用这四个词。
7. **R-V06** 正文数值与 `data/*.json` 对账，失败数必须为 0。`code/check_numbers.py` 现在 89 行对账 0 失败。
8. **R-V14** 图内印刷字号 ≥6 pt。图由 `setup_matplotlib()` 统一设 rcParams（轴标签 9、刻度 8、图例 7.5）。

附两条按交付阶段启用：**R-V08** 交付前真打开每张图看一次（渲染级检查，不能只信代码）；
**R-V03** 若最终按英文稿提交，正文 0 中文字符（附录代码与 `data/` 注释除外）。
