# 00 题面要求清单（逐句抄 + 已知/未知/待假设）

题面：`problem/problem.txt`（只读，1056 行）。本文所有引用都带行号，便于评委回溯。附录表位置：Table A.1 在 L172、Table A.2 在 L360、Table A.3 在 L634、Table B.1 在 L792、Attachment C 说明在 L959。
数据：`附件C Synthetic_Production_Data（英文版）.xlsx`，38 880 行（3 场景 × 3 浓度 × 12 浸泡档 × 360 d）。
参数：Appendix A（几何/流体/裂缝，L1–L600 附近）与 Appendix B（经济，L780–L900）。
队号 SWBMCM2634892，本科组。

---

## 1 逐句要求（问题要你做什么）

### Problem 1（L44–L53）

| 编号 | 题面原句 | 行号 | 本文落在哪 |
|---|---|---|---|
| P1-a | "Establish the coupled equations for the interacting seepage, stress, and damage fields, comprising the fluid-seepage continuity equation, the rock mechanical constitutive relation, the Biot effective-stress coupling relation, and the damage evolution equation." | L47–50 | `out/01-model.md` §1.1，式 (1.1)–(1.7) |
| P1-b | "Specify the physical assumptions, initial conditions, and boundary conditions of the model" | L50–51 | §1.1 末段 + 表 1-1（三个阶段的边界条件） |
| P1-c | "briefly explain the physical meaning of each equation" | L51–52 | §1.1 每个方程后一行"它管什么" |
| P1-d | "distinguish the boundary conditions of the injection, soaking, and production stages" | L52–53 | 表 1-1 的三列 |

### Problem 2（L54–L62）

| 编号 | 题面原句 | 行号 | 本文落在哪 |
|---|---|---|---|
| P2-a | "nondimensionalize the coupled equations established in Problem 1, obtain the dimensionless governing parameter groups, and explain the physical meaning of each parameter" | L56–58 | §2.1 + 表 2-1（10 个 Π，含物理意义） |
| P2-b | "with reference to Appendix A, give the order of magnitude of a reasonable value for each parameter" | L58–59 | 表 2-1 末列（三场景数值与 10 的幂次），`03-numbers.md` §1 |
| P2-c | "Use dimensional analysis to derive an approximate analytical relation between the soaking time and the radius of stimulation influence" | L59–61 | §2.2，式 (2.5)–(2.8)：R_p = C·t^(1/2)，C 由阈值定 |
| P2-d | "analyze which dimensionless parameters significantly modify the effect of soaking time on the stimulation extent" | L61–62 | §1.2（Π3 的表达式与量级）+ §1.6 检验 4：γ_k（Π3）改变系数 C 最多（γ_k 0→2 时 C 由 4.07 升到 6.67，+64%），但不改 ν；β_d、A_d 对 R_p(60 d) 的影响 <1%（`p1_mechanistic:nu_sensitivity`） |
| P2-e | 补充说明："Stimulation radius: defined as the farthest normal distance … recommended thresholds are Δp/p0 = 5%, a CO2 mass fraction of 0.01, a nanoparticle concentration of 0.01 wt%, and d = 0.10. Unless otherwise stated, the term refers by default to the normal distance at which the pressure disturbance reaches 5% of p0." | L92–L98 | §1.3 判据：四个阈值各算一遍，默认压力 5%（`p1_mechanistic:radii.{case}.Rp/RC/Rn/Rd`） |

### Problem 3（L63–L78）

| 编号 | 题面原句 | 行号 | 本文落在哪 |
|---|---|---|---|
| P3-a | "Formulate a multi-objective optimization model with the objectives of enhancing reservoir production and reducing the total operational cost, define the design variables" | L64–66 | §3.1：目标 (max EUR, min 总成本)，设计变量 (ts, Cn, Vinj, qinj, fCO2) |
| P3-b | "impose engineering constraints on the basis of equipment capacity, the limits on nanomaterial use, and the upper limit of formation pressure-bearing capacity" | L66–68 | §3.1 约束 (3.2)：qinj ≤ 800 m³/d、日产液 ≤ 100 m³/d、m_nano ≤ 30 t/井、pmax ≤ 承压上限、tinj+ts ≤ 90 d |
| P3-c | "Taking Case0 (the base case) as the starting point, select three representative scenarios—a low-permeability, high-stress reservoir; a medium-permeability, low-stress reservoir; and a high-permeability reservoir with complex natural fractures" | L68–L71 | §3.1 末：Case0 只作对照，正文报 Case1/2/3 |
| P3-d | "choose an appropriate intelligent optimization algorithm, and solve for the Pareto-optimal solution set by means of simulation or a surrogate model. Justify the choice of algorithm" | L72–L74 | §3.2：自实现 NSGA-II 作对账 + "成本升序扫描"的精确前沿作主算（理由：可行域仅 540 点，穷举精确） |
| P3-e | "provide 2–3 compromise operational schemes for reference for each of the three scenarios" | L74–L75 | §3.4 表 3-2：每场景 3 套（膝点、max-NPV、最低成本） |
| P3-f | "assume ±15% random perturbations in key parameters such as permeability and in-situ stress, screen the Pareto-optimal set for robust operational schemes with strong disturbance resistance, and give engineering recommendations" | L75–L78 | §3.4 + 表 3-3：7 因子 × 2 符号 = 14 次确定性扰动，判据是**决策不变性**（ts* 是否改变）而非 NPV 均值 |

### Problem 4（L79–L90）

| 编号 | 题面原句 | 行号 | 本文落在哪 |
|---|---|---|---|
| P4-a | "Use the productivity simulation data in Attachment C to build a productivity prediction model, divide the training and test sets appropriately, and adopt corresponding measures to prevent overfitting." | L80–L82 | §4.1（5 个模型比选）+ §4.2（按浸泡档整组留出的 5 折 CV）+ `p3_decline:split_audit`（三条 PASS 断言） |
| P4-b | "Using the economic parameters in Appendix B, calculate the net present value (NPV), plot the variation of NPV with soaking time, and determine the optimal soaking time for each of the three scenarios." | L82–L84 | §5.1 NPV 公式 + `fig3_npv_vs_soak` + 表 5-1（两套口径） |
| P4-c | "Compare the results of the data-driven model with those of the mechanistic model; where discrepancies arise, analyze their causes in terms of model assumptions, numerical error, and data noise." | L85–L87 | §6 表 6-1（每条写成"若假设不成立 → 预测偏高/偏低 X%"） |
| P4-d | "Construct a comprehensive evaluation index system for reservoir stimulation performance, carry out a global sensitivity analysis of the key geological and operational parameters, and identify the parameters that most strongly influence the optimal soaking time." | L87–L90 | §7 指标体系 + §8 Sobol（S1/ST）+ 表 8-2（排序：谁主导 ts*） |

### 全局约束

| 编号 | 题面原句 | 行号 | 本文落在哪 |
|---|---|---|---|
| G-1 | "Problems 2, 3, and 4 must remain consistent with Problem 1." | L99 | §9 一致性检查表（每个跨问题的数字都指回 P1 的方程或参数） |
| G-2 | Model Assumptions (3)："允许忽略自由 CO2 相"但须给适用条件并与考虑自由相的情形比较 | L100–L150 | §1.1 假设 A3 + 表 6-1 第 1 行（忽略游离相 → 气相推进更快 → R_p 被低估的方向与量级） |
| G-3 | Model Assumptions (8)：经济评价严格按 Appendix B、基准态 25 MPa/300 K、不计税费与残值 | L100–L150 | §5.1 口径声明 |

---

## 2 题面明写必须给出的图表

| 题面位置 | 要的东西 | 本文产物 |
|---|---|---|
| L56–L58 | 无量纲群（每个带物理意义） | 表 2-1（10 个），`03-numbers.md` §1 |
| L58–L59 | 每个参数的量级 | 表 2-1 末两列（三场景数值 + 10 的幂） |
| L59–L61 | 浸泡时间—改造半径的近似解析关系 | 式 (2.5)，`fig6_scaling`（R_p–t 的 log-log 与 t^1/2 参考线重合） |
| L73–L74 | Pareto 前沿 | `fig4_pareto`（三场景，V0_emp 口径） |
| L83–L84 | NPV 随浸泡时长的变化 | `fig3_npv_vs_soak`（三浓度 × 三场景 + 最优标记 + ±2% 平台带） |
| L87 | 综合评价指标体系 | 表 7-1（6 个维度、11 个指标，逐条给权重与数据来源） |
| L88–L89 | 全局敏感性 | `fig5_sobol_ts`（S1/ST 横条）+ 表 8-1 |
| 隐含 | 递减族 / 拟合优度 | `fig1_decline_family`、`fig2_soak_saturation`、`fig7_shape_discrimination` |

---

## 3 已知（题面给的、数据给的）

| 项 | 值 / 内容 | 出处 |
|---|---|---|
| 场景与代号 | Case0 基准、Case1 低渗高应力、Case2 中渗低应力、Case3 高渗复杂裂缝 | 题面 L68–L71、Table A.1（L172 起） |
| 储层参数（Table A.1，L172 起） | Case1/2/3：p0 = 45/50/45 MPa、T = 110/120/110 °C、k_m = 0.10/0.03/0.10 mD、φ0 = 0.10/0.08/0.10、E = 30/38/30 GPa、ν = 0.23/0.25/0.23、α_b = 0.80/0.85/0.80、γ_k = 0.05/0.08/0.04 MPa⁻¹、ε_d = 0.005/0.004/0.005、β_d = 100/120/100、pmax = 57/60/57 MPa | 题面 Table A.1；全部转写进 `code/mm_common.py:GEO` |
| 流体参数（Table A.2，L360 起） | ρ_o 800/810/800、μ_o 2.0/3.0/2.0 mPa·s、μ_w 0.35、A_c 0.5/0.6/0.5 MPa、K_d 0.01 m³/kg、a_σ 0.3、a_θ 15、D_CO2 = 1e-9 m²/s、D_n = 5e-10 m²/s、d_n = 25 nm | Table A.2；`mm_common.py:FLUID` |
| 裂缝与施工（Table A.3，L634 起） | L_f 100/120/140 m、h_f 20 m、w_f 3/4/5 mm、k_f 3000/5000/8000 mD、q_inj = 300 m³/d、V_inj = 3000 m³、f_CO2 = 0.5、τ_inj = 0、p_wf = 35 MPa、T_prod = 360 d、注入+浸泡 ≤ 90 d、单井日产液 ≤ 100 m³/d | Table A.3；`mm_common.py:FRAC` |
| 经济参数（Table B.1，L792 起） | P_oil* = 3396 CNY/m³（75 USD/bbl × 7.20 ÷ 0.159）、c_nano = 20×10⁴ CNY/t、c_CO2 = 0.03×10⁴ CNY/t、c_inj = 30×10⁴ CNY/d、c_soak = 3×10⁴ CNY/d、C_frac = 120×10⁴ CNY/井、c_prod = 350 CNY/m³、c_water = 25 CNY/m³、r = 8%/yr | Table B.1，L788–L872；`mm_common.py:ECON` |
| 材料用量 | m_CO2 = ρ_ref f_CO2 V_inj/1000（ρ_ref = 850 kg/m³）、m_nano = (Cn/100)·1000·(1−f_CO2)·V_inj/1000，上限 30 t/井 | B.2，L877–L897 |
| 成本公式 | C_total = C_frac + c_inj t_inj + c_soak t_s + C_nano + C_CO2 + c_prod Q_o + c_water Q_w | B.3，L898 起 |
| 官方检验向量 | V_inj=3000、f_CO2=0.5、Cn=1.0、注入 10 d、浸泡 30 d → 材料 300+38.25 万元、注入 300 万元、浸泡 90 万元、压裂 120 万元，小计 **848.25 万元** | B.4；脚本断言 `p4_econ:test_b4.PASS` |
| 附件C 结构 | 38 880 行；Cn ∈ {0.5, 1.0, 1.5} wt%；ts ∈ {5,10,…,60} d；day 1–360；3 场景 × 36 组 = 108 组 | `p3_decline:data_facts` |
| 附件C 噪声声明 | 由参考机理模型生成、含 ±5% 高斯噪声、截断非负；不是现场数据、不是标准答案，只考趋势/量级/排序 | 题面 Attachment C 说明段 |
| 附件C 使用规则 | (1) 按场景×浓度×浸泡**整组**划分 train/test，禁止同组内随机切相邻生产日；(2) 测试集至少含一个未训练浸泡档；(3) 禁止用 Cum_Oil 反推日产再补噪；(4) 附件C 只覆盖 Cn 与 ts，其余变量的影响须由机理模型或显式假设给出；(5) 允许平滑但须说明并与原始对比 | 题面 Attachment C 说明段 |
| 数据内部一致性（自测） | `Cum_Oil` 与 `cumsum(Oil_Rate)` 最大偏差 0.20 m³（两位小数舍入），累计列不含独立噪声 | `p3_decline:noise_check` |

---

## 4 未知（题面没给、数据里没有）

| 编号 | 缺什么 | 为什么关键 | 现在怎么处理 |
|---|---|---|---|
| U1 | 产水数据（WOR / Q_w） | NPV 里的 c_water Q_w 项算不出 | 基线 WOR = 0，另报 WOR = 0.5 的敏感性一行（表 5-2） |
| U2 | 注入体积 V_inj 在产量中的响应 | 附件C 不含 V_inj，S_V = 1−exp(−V_inj/V0) 依赖 V0 口径 | 两种 V0 口径（几何 2.6×10⁴ m³ / 经验 1500 m³）都算，报"注入量不可识别"；只给 ts 与 Cn 的最优 |
| U3 | 井段数 / 簇数 N_f | 决定单井产量与固定成本的相对尺度 | 不做缩放，只报敏感性一行（表 5-3）：N_f = 1/2/3 时 NPV 的变化 |
| U4 | 裂缝的几何分布（单缝 vs 多簇、天然缝网络） | 决定改造体积与 Case3 的"复杂裂缝"如何离散 | 单缝等效（L_f、h_f、w_f、k_f 取自 A.3），缝面面积 = 4 L_f h_f；在 §1.1 假设 A4 声明 |
| U5 | 滞留/吸附位点容量（K_d 之外的动力学常数） | 决定 τ 的物理来源 | 只把 τ 当标定量，并用两条独立路径交叉验证；τ 的机理列为 open（§2.4） |
| U6 | 游离 CO2 相的相平衡数据（相对渗透率、溶解常数） | 假设 (3) 允许忽略游离相，但要求给适用条件 | 用 Pe 数与溶解度上限给出适用条件（§1.1 假设 A3） |
| U7 | 现场温度对 μ_o 的影响曲线 | 影响 α_p 与 R_p | 用 A.2 的给定 μ_o（等温），温度效应列为 open |
| U8 | 纳米颗粒在孔隙壁的吸附层厚度 | 影响 k 的改造幅度（A_d） | A_d 取 0/20/200 三档做敏感性（`p1_mechanistic:nu_sensitivity`） |

---

## 5 待假设（每条都写"若不成立，结论往哪偏、偏多少"）

| 编号 | 假设 | 依据 | 若不成立的影响（方向 + 量级） |
|---|---|---|---|
| A1 | 一维法向对称：以缝面为原点的半无限一维问题（法向 x） | 缝长远大于改造半径时成立；实测 R_p(60 d)/L_f = 0.41/0.71/1.30（Case1/2/3），前两个场景成立，Case3 已不满足 | Case3 的 R_p 应视为**上界**（一维高估了侧向绕流），二维会对 Case3 折减；Case1/2 的误差 ≲ 10% |
| A2 | 等温（题面给定 T 恒定），忽略焦耳-汤姆逊与热膨胀 | Table A.1 每个场景只给一个温度 | 若注入液与地层温差 30 K，热膨胀项 α_T ΔT ≈ 3×10⁻³，比累积项（Case1 的 2.7×10⁻²）小约一个数量级 → 列入可忽略（表 1-2 的 thermal 行） |
| A3 | 忽略游离 CO2 相，CO2 以溶解态随水相输运 | 题面假设 (3) | 若游离相饱和度 > 0.1，气相黏度低 → 压力前缘推进更快 → 本文 R_p 偏低约 20–40%（按 μ_g/μ_w ≈ 0.02 的两相流度比估算） |
| A4 | 单条等效裂缝（L_f、h_f、w_f、k_f），缝面面积 A_face = 4 L_f h_f | A.3 只给单缝参数 | 若实际多簇，A_face 按簇数线性放大 → V0_geo 同比例变化，R_p 不变；NPV 结论（ts*）不受影响 |
| A5 | 渗透率的应力敏感可逆（k = k0 e^{γ_k Δp}） | A.1 只给 γ_k | 若存在滞回（卸载后 k 不恢复），生产期 k 会低于本文值 → EUR 偏低，ts* 略向长侧移动 |
| A6 | 损伤变量是指数饱和型 d = 1−exp(−β_d⟨ε−ε_d⟩₊) | 需满足 d∈[0,1)、在 ε_d 处连续 | 若改用线性 d，d 会超过 1（非物理）。实测把 β_d 由 1 改到 2，C 由 5.1963 变 5.1981（+0.03%）、R_p(60 d) 变 0.3% → 该形式对 R_p 的影响可忽略（`p1_mechanistic:nu_sensitivity.{case}.bd_x*`） |
| A7 | 递减率 D 在场景内与 Cn、ts 无关 | 实测：40–300 d 对数斜率跨 36 组变异 <0.5%（`p3_decline:shared_D.*.D_cv`） | 若 D 真随 ts 变，按 ∂lnEUR/∂D = −1/D，ΔD/D = 0.4% → EUR 偏 0.4%，对 ts* 的影响 <0.2 d |
| A8 | 生产期井底流压恒定 p_wf = 35 MPa（定压生产） | 题面 A.3 给定 | 若定产生产，递减形状会变（改为 arps 双曲），EUR 变化由 b 指数控制 |
| A9 | 产量与 A(ts, Cn) 成正比（"scale-only"结构） | 同场景内 D 的组间变异系数 0.43%/0.23%/0.20%（`p3_decline:shared_D.*.D_cv`），归一化递减形状见 `fig1_decline_family` | 若不成立（形状随 ts 变），M5 的 RMSE 会显著高于 M4；实测 M5 外推 RMSE 0.46–1.07 vs M4 0.63–2.67，支持本条 |
| A10 | 折现按日末、365 d/yr、基准 day 0 | 惯例 + 题面 r = 8%/yr | 若按日初折现，NPV 变化 <0.3%（一天折现因子 1.0002） |

---

## 6 交付清单与复跑方式

- 复跑：`E:\Mini\envs\mathmodel\python.exe code\run_all.py`（一次跑完 p3 → p1 → p2_shape → p4 → p5 → verify_env → figs → make_tables，约 110 s）
- 数字唯一来源：`data/*.json`（每个文件带 `_meta`：脚本名 + 脚本 sha256 + 运行时间 + 输入 xlsx 的 sha256）
- 数字表：`out/03-numbers.md`（每行"量 | 值 | 单位 | JSON 键"）
- 图：`figures/fig1…fig7`（PNG + PDF）
VERDICT: PASS
