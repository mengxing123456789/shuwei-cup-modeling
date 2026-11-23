# 03 数字表（唯一来源：data/*.json）

本文件的每一行都对应 `data/<script>.json` 里的一个键；正文里出现的任何数字都必须能在此检索到。
格式约定：量 | 值 | 单位 | JSON 键。键的写法是 `文件:路径.到.字段`，`{case}` 表示三个场景各一行。

### 口径声明（先说清，再报数）

1. **时间轴**：day 0 = 压裂当天；注入 tinj = Vinj/qinj 天（基准 3000/300 = 10 d）；浸泡 ts 天；生产 360 d。
2. **折现**：日末折现 (1+r)^(-d/365)，r = 8%/yr，365 d/yr，基准 day 0。
3. **成本**：压裂 120 万元 day0 一次付；注入期逐日 30 万元/d；浸泡期逐日 3 万元/d；
   CO2 与纳米材料按 B.2 计算并在 day0 一次付。题面 B.4 检验向量算出小计 848.25 万元，脚本内断言通过。
4. **产水**：附件C 无产水数据，基线 WOR = 0（待假设），另做 WOR = 0.5 敏感性。
5. **浸泡时长两套口径**：`ts_data_grid` = 在附件C 的 5,10,…,60 档位上取 NPV 最大；
   `ts_continuous` = 对 M5 拟合曲线解 dNPV/dts = 0 的驻点。工程决策用前者，后者用来说明曲线形状。
6. **注入量不可识别**：附件C 不含 Vinj，`S_V = 1-exp(-Vinj/V0)` 依赖 V0 的口径；两种 V0 下推荐的 Vinj 会翻边，
   故本文只报 ts 与 Cn 的最优，不报 Vinj 的最优值（见 `p4_econ:V0` 与 `pareto_meta`）。
7. **NPV 的绝对符号**由题面固定成本（压裂 120 万 + 材料 + 注入）与附件C 的井尺度产量共同决定；
   本文不做井段数缩放，Case1/Case2 的结构性亏损是结论，不是计算错误。
8. 键里的 `{i}` 表示"该行对应 9 个（场景×浓度）组合里的第 i 个"，顺序为 Case1/Case2/Case3 各 Cn=0.5→1.0→1.5。

## 0  数据概况

附件C 的规模与结构；组数 = 场景 × 浓度 × 浸泡档。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| 总行数 | 38880 | 行 | `p3_decline:data_facts.n_rows` |
| 场景数 | 3 | 个 | `p3_decline:data_facts.n_cases` |
| 浓度档 | 0.5 / 1.0 / 1.5 | wt% | `p3_decline:data_facts.cn_levels` |
| 浸泡档 | 5 / 10 / 15 / 20 / 25 / 30 / 35 / 40 / 45 / 50 / 55 / 60 | d | `p3_decline:data_facts.ts_levels` |
| 生产日范围 | 1 / 360 | d | `p3_decline:data_facts.days` |
| (场景,浓度,浸泡) 组数 | 108 | 组 | `p3_decline:n_groups` |

## 1  P1：控制方程的无量纲群（三个场景各一组）

10 个无量纲群的数值；表达式与物理意义见 `out/01-model.md` 表 1-2。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Pi1_Fourier_60d = α_p·t/L_ref², α_p=k/(μ φ c_t), L_ref=h/2, t=60 d | 3.76 / 16 / 87.5 | — | `p1_mechanistic:dimensionless.{case}.Pi1_Fourier_60d.v` |
| Pi2_poroelastic = α_b p0/K_b | 0.00168 / 0.00194 / 0.0027 | — | `p1_mechanistic:dimensionless.{case}.Pi2_poroelastic.v` |
| Pi3_stressperm = γ_k Δp_max | 0.8 / 0.48 / 0.24 | — | `p1_mechanistic:dimensionless.{case}.Pi3_stressperm.v` |
| Pi4_storage_split = c_φ/(c_o+c_φ) | 0.412 / 0.375 / 0.333 | — | `p1_mechanistic:dimensionless.{case}.Pi4_storage_split.v` |
| Pi5_co2_diff = D_CO2 t/L_ref² | 5.18e-05 / 5.18e-05 / 5.18e-05 | — | `p1_mechanistic:dimensionless.{case}.Pi5_co2_diff.v` |
| Pi6_retard = R_n=1+ρ_r K_d/φ0 | 314 / 251 / 193 | — | `p1_mechanistic:dimensionless.{case}.Pi6_retard.v` |
| Pi7_damage = β_d ε_d | 0.48 / 0.5 / 0.48 | — | `p1_mechanistic:dimensionless.{case}.Pi7_damage.v` |
| Pi8_stressconc = a_σ√(L_f/w_f)·α_bΔp/(K_b ε_d) | 4.59 / 5.39 / 5.65 | — | `p1_mechanistic:dimensionless.{case}.Pi8_stressconc.v` |
| Pi9_injectivity = k Δp/(μ q/A_face) | 0.227 / 1.64 / 12.7 | — | `p1_mechanistic:dimensionless.{case}.Pi9_injectivity.v` |
| Pi10_time = t_soak/T_prod | 0.0833 / 0.0833 / 0.0833 | — | `p1_mechanistic:dimensionless.{case}.Pi10_time.v` |

## 1b  P1/P2：改造半径与标度律

数值解 R_p 由压力扰动 5% 判据给出；ν 由 R_p = C·t^ν 的 log-log 斜率（全窗口 5–60 d，n=56）估计。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  R_p(5 d) | 11.67 | m | `p1_mechanistic:radii.Case1.Rp[4]` |
| Case1  R_p(20 d) | 23.44 | m | `p1_mechanistic:radii.Case1.Rp[19]` |
| Case1  R_p(60 d) | 40.64 | m | `p1_mechanistic:radii.Case1.Rp[59]` |
| Case2  R_p(5 d) | 24.52 | m | `p1_mechanistic:radii.Case2.Rp[4]` |
| Case2  R_p(20 d) | 49.16 | m | `p1_mechanistic:radii.Case2.Rp[19]` |
| Case2  R_p(60 d) | 85.19 | m | `p1_mechanistic:radii.Case2.Rp[59]` |
| Case3  R_p(5 d) | 52.27 | m | `p1_mechanistic:radii.Case3.Rp[4]` |
| Case3  R_p(20 d) | 104.7 | m | `p1_mechanistic:radii.Case3.Rp[19]` |
| Case3  R_p(60 d) | 181.5 | m | `p1_mechanistic:radii.Case3.Rp[59]` |
| Case1  ν（5–60 d，n=56） | 0.5017 | — | `p1_mechanistic:scaling.Case1.all.nu` |
| Case1  ν 的 R² | 0.999999 | — | `p1_mechanistic:scaling.Case1.all.r2` |
| Case1  C（R_p = C·t^ν 的系数） | 5.213 | m·d^-ν | `p1_mechanistic:scaling.Case1.all.C` |
| Case1  R_p(60 d) 解析/数值比 | 1.288 | — | `p1_mechanistic:scaling.Case1.ratio_num_ana` |
| Case2  ν（5–60 d，n=56） | 0.5009 | — | `p1_mechanistic:scaling.Case2.all.nu` |
| Case2  ν 的 R² | 0.999999 | — | `p1_mechanistic:scaling.Case2.all.r2` |
| Case2  C（R_p = C·t^ν 的系数） | 10.96 | m·d^-ν | `p1_mechanistic:scaling.Case2.all.C` |
| Case2  R_p(60 d) 解析/数值比 | 1.143 | — | `p1_mechanistic:scaling.Case2.ratio_num_ana` |
| Case3  ν（5–60 d，n=56） | 0.5007 | — | `p1_mechanistic:scaling.Case3.all.nu` |
| Case3  ν 的 R² | 1.000000 | — | `p1_mechanistic:scaling.Case3.all.r2` |
| Case3  C（R_p = C·t^ν 的系数） | 23.37 | m·d^-ν | `p1_mechanistic:scaling.Case3.all.C` |
| Case3  R_p(60 d) 解析/数值比 | 1.071 | — | `p1_mechanistic:scaling.Case3.ratio_num_ana` |
| Case1  质量相对不平衡 | 7.658e-05 | — | `p1_mechanistic:solver_check.Case1.rel_imbalance` |
| Case1  网格加密相对差（N=300 vs 600） | 7.735e-06 | — | `p1_mechanistic:grid_convergence.Case1.rel_300` |
| Case2  质量相对不平衡 | 4.133e-05 | — | `p1_mechanistic:solver_check.Case2.rel_imbalance` |
| Case2  网格加密相对差（N=300 vs 600） | 3.562e-05 | — | `p1_mechanistic:grid_convergence.Case2.rel_300` |
| Case3  质量相对不平衡 | 1.522e-05 | — | `p1_mechanistic:solver_check.Case3.rel_imbalance` |
| Case3  网格加密相对差（N=300 vs 600） | 3.996e-05 | — | `p1_mechanistic:grid_convergence.Case3.rel_300` |

## 1c  P2：饱和时间尺度 τ 的两个机制假设 vs 数据反演

τ_sat 由"扩散到达特征长度"的两种几何给出；数据 τ 由 M5 拟合。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  τ_sat（假设A：基质块半宽 h/2） | 6.026 | d | `p1_mechanistic:scaling.Case1.tau_sat_A_block` |
| Case1  τ_sat（假设B：缝半长 Lf/2） | 150.7 | d | `p1_mechanistic:scaling.Case1.tau_sat_B_frac` |
| Case1  τ（M5 拟合） | 6.615 | d | `p3_decline:M5_params.Case1.tau` |
| Case1  corr(log A, log R_p) | 0.8873 | — | `p1_mechanistic:cross_check.Case1.corr` |
| Case1  ν_data（5–20 d） | 0.4204 | — | `p1_mechanistic:cross_check.Case1.nu_data_5_20` |
| Case2  τ_sat（假设A：基质块半宽 h/2） | 1.08 | d | `p1_mechanistic:scaling.Case2.tau_sat_A_block` |
| Case2  τ_sat（假设B：缝半长 Lf/2） | 38.89 | d | `p1_mechanistic:scaling.Case2.tau_sat_B_frac` |
| Case2  τ（M5 拟合） | 8.336 | d | `p3_decline:M5_params.Case2.tau` |
| Case2  corr(log A, log R_p) | 0.9164 | — | `p1_mechanistic:cross_check.Case2.corr` |
| Case2  ν_data（5–20 d） | 0.5017 | — | `p1_mechanistic:cross_check.Case2.nu_data_5_20` |
| Case3  τ_sat（假设A：基质块半宽 h/2） | 0.2089 | d | `p1_mechanistic:scaling.Case3.tau_sat_A_block` |
| Case3  τ_sat（假设B：缝半长 Lf/2） | 10.23 | d | `p1_mechanistic:scaling.Case3.tau_sat_B_frac` |
| Case3  τ（M5 拟合） | 9.984 | d | `p3_decline:M5_params.Case3.tau` |
| Case3  corr(log A, log R_p) | 0.933 | — | `p1_mechanistic:cross_check.Case3.corr` |
| Case3  ν_data（5–20 d） | 0.5713 | — | `p1_mechanistic:cross_check.Case3.nu_data_5_20` |

## 2  P2：浸泡响应的形状判别（三种候选形状 × 9 个组合）

两个 ν 不是一回事：ν=1/2 属于改造半径（前沿位置，见 1b 的数值解），而产量对 ts 的响应是饱和的。本表用附件C 直接判别，不靠论证。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  R²(A+B·√ts) 区间（Cn=0.5/1.0/1.5） | 0.6776 / 0.6934 / 0.6701 | — | `p2_shape:rows.{i}.shapes.S1_sqrt.r2` |
| Case1  R²(A(1−e^(−ts/τ))) 区间（Cn=0.5/1.0/1.5） | 0.9986 / 0.9986 / 0.9973 | — | `p2_shape:rows.{i}.shapes.S2_exp.r2` |
| Case1  R²(A·ts^ν) 区间（Cn=0.5/1.0/1.5） | 0.7455 / 0.7619 / 0.7401 | — | `p2_shape:rows.{i}.shapes.S3_power.r2` |
| Case1  τ（S2，Cn=0.5/1.0/1.5） | 6.609 / 6.696 / 6.549 | d | `p2_shape:rows.{i}.shapes.S2_exp.params.tau` |
| Case1  ν_data（S3） | 0.2193 / 0.2196 / 0.2156 | — | `p2_shape:rows.{i}.shapes.S3_power.params.nu` |
| Case1  τ 在三个浓度间的相对散布 | 0.0221 | — | `p2_shape:tau_cn_independence.Case1` |
| Case1  ΔR²（指数饱和 − √ts）最小者 | 0.3051 | — | `p2_shape:rows.{i}.dR2_exp_minus_sqrt` |
| Case1  √ts 形状的残差符号游程（期望 6.5） | 3 / 3 / 3 | 次 | `p2_shape:rows.{i}.shapes.S1_sqrt.resid_runs` |
| Case1  指数饱和的残差符号游程（期望 6.5） | 7 / 7 / 9 | 次 | `p2_shape:rows.{i}.shapes.S2_exp.resid_runs` |
| Case2  R²(A+B·√ts) 区间（Cn=0.5/1.0/1.5） | 0.7621 / 0.7684 / 0.7509 | — | `p2_shape:rows.{i}.shapes.S1_sqrt.r2` |
| Case2  R²(A(1−e^(−ts/τ))) 区间（Cn=0.5/1.0/1.5） | 0.9993 / 0.9991 / 0.9994 | — | `p2_shape:rows.{i}.shapes.S2_exp.r2` |
| Case2  R²(A·ts^ν) 区间（Cn=0.5/1.0/1.5） | 0.8019 / 0.8055 / 0.7928 | — | `p2_shape:rows.{i}.shapes.S3_power.r2` |
| Case2  τ（S2，Cn=0.5/1.0/1.5） | 8.291 / 8.502 / 8.227 | d | `p2_shape:rows.{i}.shapes.S2_exp.params.tau` |
| Case2  ν_data（S3） | 0.2833 / 0.2904 / 0.2799 | — | `p2_shape:rows.{i}.shapes.S3_power.params.nu` |
| Case2  τ 在三个浓度间的相对散布 | 0.0329 | — | `p2_shape:tau_cn_independence.Case2` |
| Case2  ΔR²（指数饱和 − √ts）最小者 | 0.2308 | — | `p2_shape:rows.{i}.dR2_exp_minus_sqrt` |
| Case2  √ts 形状的残差符号游程（期望 6.5） | 3 / 3 / 3 | 次 | `p2_shape:rows.{i}.shapes.S1_sqrt.resid_runs` |
| Case2  指数饱和的残差符号游程（期望 6.5） | 3 / 7 / 6 | 次 | `p2_shape:rows.{i}.shapes.S2_exp.resid_runs` |
| Case3  R²(A+B·√ts) 区间（Cn=0.5/1.0/1.5） | 0.8133 / 0.8175 / 0.8041 | — | `p2_shape:rows.{i}.shapes.S1_sqrt.r2` |
| Case3  R²(A(1−e^(−ts/τ))) 区间（Cn=0.5/1.0/1.5） | 0.9996 / 0.9998 / 0.9991 | — | `p2_shape:rows.{i}.shapes.S2_exp.r2` |
| Case3  R²(A·ts^ν) 区间（Cn=0.5/1.0/1.5） | 0.8308 / 0.8352 / 0.8219 | — | `p2_shape:rows.{i}.shapes.S3_power.r2` |
| Case3  τ（S2，Cn=0.5/1.0/1.5） | 10.036 / 9.991 / 9.947 | d | `p2_shape:rows.{i}.shapes.S2_exp.params.tau` |
| Case3  ν_data（S3） | 0.3433 / 0.3421 / 0.3416 | — | `p2_shape:rows.{i}.shapes.S3_power.params.nu` |
| Case3  τ 在三个浓度间的相对散布 | 0.00894 | — | `p2_shape:tau_cn_independence.Case3` |
| Case3  ΔR²（指数饱和 − √ts）最小者 | 0.1823 | — | `p2_shape:rows.{i}.dR2_exp_minus_sqrt` |
| Case3  √ts 形状的残差符号游程（期望 6.5） | 3 / 3 / 3 | 次 | `p2_shape:rows.{i}.shapes.S1_sqrt.resid_runs` |
| Case3  指数饱和的残差符号游程（期望 6.5） | 9 / 4 / 7 | 次 | `p2_shape:rows.{i}.shapes.S2_exp.resid_runs` |
| 9 个组合的最佳形状都是指数饱和 | 1 | — | `p2_shape:decision.best_shape_all_9` |
| ΔR² 的最小值（指数饱和 − √ts） | 0.1823 | — | `p2_shape:decision.min_dR2_exp_minus_sqrt` |
| 自由幂律被否掉（ν_data 偏离 0.5 或跨场景不等） | 1 | — | `p2_shape:decision.nu_single_powerlaw_rejected` |
| τ 与 R_p(60 d) 的 log-log 指数 | 0.2752 | — | `p2_shape:tau_scaling_vs_Rp.loglog_exponent` |
| 该指数的 R²（3 个点） | 0.9941 | — | `p2_shape:tau_scaling_vs_Rp.loglog_r2` |
| 若扩散控制应得的指数 | 2.0 | — | `p2_shape:tau_scaling_vs_Rp.diffusion_expected_exponent` |
| 实测/扩散预期 | 0.138 | — | `p2_shape:tau_scaling_vs_Rp.ratio_observed_to_diffusion` |

## 3  P3：五个产能模型的比选

BIC 越小越好；逐组自由参数的模型参数最多（M1/M2/M3 各 324/216/324 个），M5 只有 15 个。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| BIC (M1) | -54610.8 | — | `p3_decline:model_selection.M1.bic` |
| 参数个数 (M1) | 324 | 个 | `p3_decline:model_selection.M1.kpar` |
| 残差 RMSE (M1) | 0.4741 | m³/d | `p3_decline:model_selection.M1.rmse` |
| BIC (M2) | -55642.7 | — | `p3_decline:model_selection.M2.bic` |
| 参数个数 (M2) | 216 | 个 | `p3_decline:model_selection.M2.kpar` |
| 残差 RMSE (M2) | 0.4748 | m³/d | `p3_decline:model_selection.M2.rmse` |
| BIC (M3) | -55043.0 | — | `p3_decline:model_selection.M3.bic` |
| 参数个数 (M3) | 324 | 个 | `p3_decline:model_selection.M3.kpar` |
| 残差 RMSE (M3) | 0.4715 | m³/d | `p3_decline:model_selection.M3.rmse` |
| BIC (M4) | -56367.6 | — | `p3_decline:model_selection.M4.bic` |
| 参数个数 (M4) | 111 | 个 | `p3_decline:model_selection.M4.kpar` |
| 残差 RMSE (M4) | 0.4771 | m³/d | `p3_decline:model_selection.M4.rmse` |
| BIC (M5) | -55504.2 | — | `p3_decline:model_selection.M5.bic` |
| 参数个数 (M5) | 15 | 个 | `p3_decline:model_selection.M5.kpar` |
| 残差 RMSE (M5) | 0.4888 | m³/d | `p3_decline:model_selection.M5.rmse` |
| Case1  D（共享，40–330 d 对数斜率中位数） | 0.029938 | d⁻¹ | `p3_decline:shared_D.Case1.D` |
| Case1  D 在 36 组之间的变异系数 | 0.00426 | — | `p3_decline:shared_D.Case1.D_cv` |
| Case1  A∞（M5） | 8.767 | m³/d | `p3_decline:M5_params.Case1.Ainf` |
| Case1  τ（M5） | 6.615 | d | `p3_decline:M5_params.Case1.tau` |
| Case1  p（M5 饱和指数） | 0.996 | — | `p3_decline:M5_params.Case1.p` |
| Case1  a（M5 浓度敏感度） | 0.09302 | — | `p3_decline:M5_params.Case1.a` |
| Case1  R²（M5） | 0.9981 | — | `p3_decline:M5_params.Case1.r2` |
| Case1  相对 RMSE（M5） | 0.00655 | — | `p3_decline:M5_params.Case1.rel_rmse` |
| Case2  D（共享，40–330 d 对数斜率中位数） | 0.019979 | d⁻¹ | `p3_decline:shared_D.Case2.D` |
| Case2  D 在 36 组之间的变异系数 | 0.00226 | — | `p3_decline:shared_D.Case2.D_cv` |
| Case2  A∞（M5） | 27.51 | m³/d | `p3_decline:M5_params.Case2.Ainf` |
| Case2  τ（M5） | 8.336 | d | `p3_decline:M5_params.Case2.tau` |
| Case2  p（M5 饱和指数） | 0.9908 | — | `p3_decline:M5_params.Case2.p` |
| Case2  a（M5 浓度敏感度） | 0.09187 | — | `p3_decline:M5_params.Case2.a` |
| Case2  R²（M5） | 0.9991 | — | `p3_decline:M5_params.Case2.r2` |
| Case2  相对 RMSE（M5） | 0.005331 | — | `p3_decline:M5_params.Case2.rel_rmse` |
| Case3  D（共享，40–330 d 对数斜率中位数） | 0.014999 | d⁻¹ | `p3_decline:shared_D.Case3.D` |
| Case3  D 在 36 组之间的变异系数 | 0.00199 | — | `p3_decline:shared_D.Case3.D_cv` |
| Case3  A∞（M5） | 54.98 | m³/d | `p3_decline:M5_params.Case3.Ainf` |
| Case3  τ（M5） | 9.984 | d | `p3_decline:M5_params.Case3.tau` |
| Case3  p（M5 饱和指数） | 1.007 | — | `p3_decline:M5_params.Case3.p` |
| Case3  a（M5 浓度敏感度） | 0.08917 | — | `p3_decline:M5_params.Case3.a` |
| Case3  R²（M5） | 0.9995 | — | `p3_decline:M5_params.Case3.r2` |
| Case3  相对 RMSE（M5） | 0.004611 | — | `p3_decline:M5_params.Case3.rel_rmse` |
| Case1  EUR 的 bootstrap 90% 区间下界 | 287.7 | m³ | `p3_decline:bootstrap.Case1.EUR[0]` |
| Case1  EUR 的 bootstrap 90% 区间上界 | 292.3 | m³ | `p3_decline:bootstrap.Case1.EUR[1]` |
| Case1  D 的 bootstrap 90% 区间 | [0.0298, 0.0305] | d⁻¹ | `p3_decline:bootstrap.Case1.D` |
| Case2  EUR 的 bootstrap 90% 区间下界 | 1324 | m³ | `p3_decline:bootstrap.Case2.EUR[0]` |
| Case2  EUR 的 bootstrap 90% 区间上界 | 1339 | m³ | `p3_decline:bootstrap.Case2.EUR[1]` |
| Case2  D 的 bootstrap 90% 区间 | [0.0199, 0.0202] | d⁻¹ | `p3_decline:bootstrap.Case2.D` |
| Case3  EUR 的 bootstrap 90% 区间下界 | 3439 | m³ | `p3_decline:bootstrap.Case3.EUR[0]` |
| Case3  EUR 的 bootstrap 90% 区间上界 | 3488 | m³ | `p3_decline:bootstrap.Case3.EUR[1]` |
| Case3  D 的 bootstrap 90% 区间 | [0.0146, 0.0149] | d⁻¹ | `p3_decline:bootstrap.Case3.D` |
| bootstrap 重抽样次数 | 400 | 次 | `p3_decline:bootstrap.Case1.n_boot` |
| bootstrap 随机种子 | 20261120 | — | `p3_decline:bootstrap.Case1.seed` |

## 3b  P3：按浸泡档整组留出的交叉验证（5 折，含上下两个外推方向）

M2 是逐组自由指数：被留出的浸泡档没有参数可估，故只在训练组上打分（`M2_train_rmse`），测试档记 NA。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| fold 0 留出档 [5, 20, 35, 50]：M2 训练组 RMSE | 0.4874 | m³/d | `p3_decline:cv[0].M2_train_rmse` |
| fold 0：M4 留出档 RMSE | 1.262 | m³/d | `p3_decline:cv[0].M4_rmse` |
| fold 0：M5 留出档 RMSE | 0.4556 | m³/d | `p3_decline:cv[0].M5_rmse` |
| fold 1 留出档 [10, 25, 40, 55]：M2 训练组 RMSE | 0.476 | m³/d | `p3_decline:cv[1].M2_train_rmse` |
| fold 1：M4 留出档 RMSE | 0.6282 | m³/d | `p3_decline:cv[1].M4_rmse` |
| fold 1：M5 留出档 RMSE | 0.4798 | m³/d | `p3_decline:cv[1].M5_rmse` |
| fold 2 留出档 [15, 30, 45, 60]：M2 训练组 RMSE | 0.4605 | m³/d | `p3_decline:cv[2].M2_train_rmse` |
| fold 2：M4 留出档 RMSE | 0.7328 | m³/d | `p3_decline:cv[2].M4_rmse` |
| fold 2：M5 留出档 RMSE | 0.5087 | m³/d | `p3_decline:cv[2].M5_rmse` |
| fold 3 留出档 [5, 10, 15, 20, 25, 30]：M2 训练组 RMSE | 0.5193 | m³/d | `p3_decline:cv[3].M2_train_rmse` |
| fold 3：M4 留出档 RMSE | 2.666 | m³/d | `p3_decline:cv[3].M4_rmse` |
| fold 3：M5 留出档 RMSE | 1.075 | m³/d | `p3_decline:cv[3].M5_rmse` |
| fold 4 留出档 [35, 40, 45, 50, 55, 60]：M2 训练组 RMSE | 0.4256 | m³/d | `p3_decline:cv[4].M2_train_rmse` |
| fold 4：M4 留出档 RMSE | 0.6831 | m³/d | `p3_decline:cv[4].M4_rmse` |
| fold 4：M5 留出档 RMSE | 0.5329 | m³/d | `p3_decline:cv[4].M5_rmse` |
| 划分合规性审计：全部 PASS | 1 | — | `p3_decline:split_audit.all_pass` |
| fold 0 测试集独有的浸泡档 | [5, 20, 35, 50] | d | `p3_decline:split_audit.folds[0].test_ts_not_in_train` |
| fold 0 整组只落在一个 split | 1 | — | `p3_decline:split_audit.folds[0].PASS_group_whole` |
| fold 1 测试集独有的浸泡档 | [10, 25, 40, 55] | d | `p3_decline:split_audit.folds[1].test_ts_not_in_train` |
| fold 1 整组只落在一个 split | 1 | — | `p3_decline:split_audit.folds[1].PASS_group_whole` |
| fold 2 测试集独有的浸泡档 | [15, 30, 45, 60] | d | `p3_decline:split_audit.folds[2].test_ts_not_in_train` |
| fold 2 整组只落在一个 split | 1 | — | `p3_decline:split_audit.folds[2].PASS_group_whole` |
| fold 3 测试集独有的浸泡档 | [5, 10, 15, 20, 25, 30] | d | `p3_decline:split_audit.folds[3].test_ts_not_in_train` |
| fold 3 整组只落在一个 split | 1 | — | `p3_decline:split_audit.folds[3].PASS_group_whole` |
| fold 4 测试集独有的浸泡档 | [35, 40, 45, 50, 55, 60] | d | `p3_decline:split_audit.folds[4].test_ts_not_in_train` |
| fold 4 整组只落在一个 split | 1 | — | `p3_decline:split_audit.folds[4].PASS_group_whole` |

## 3c  P3：每组 (场景,浓度,浸泡) 的 qi、D、EUR

qi 为 M5 的第一天产能 A(ts,Cn)·e^-D，EUR 为 360 d 累计；D 按场景共享，故同一场景内 qi 的差异全部来自 A(ts,Cn)。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1 Cn=0.5 ts=10：q1 | 6.522 | m³/d | `p3_decline:groups[0].qi_shared` |
| Case1 Cn=0.5 ts=10：EUR（实测） | 214.9 | m³ | `p3_decline:groups[0].EUR_data` |
| Case1 Cn=0.5 ts=10：EUR（M5 拟合） | 217.8 | m³ | `p3_decline:groups[0].EUR_shared` |
| Case1 Cn=0.5 ts=15：q1 | 7.594 | m³/d | `p3_decline:groups[1].qi_shared` |
| Case1 Cn=0.5 ts=15：EUR（实测） | 248.4 | m³ | `p3_decline:groups[1].EUR_data` |
| Case1 Cn=0.5 ts=15：EUR（M5 拟合） | 253.7 | m³ | `p3_decline:groups[1].EUR_shared` |
| Case1 Cn=0.5 ts=20：q1 | 7.937 | m³/d | `p3_decline:groups[2].qi_shared` |
| Case1 Cn=0.5 ts=20：EUR（实测） | 261 | m³ | `p3_decline:groups[2].EUR_data` |
| Case1 Cn=0.5 ts=20：EUR（M5 拟合） | 265.1 | m³ | `p3_decline:groups[2].EUR_shared` |
| Case1 Cn=0.5 ts=25：q1 | 8.001 | m³/d | `p3_decline:groups[3].qi_shared` |
| Case1 Cn=0.5 ts=25：EUR（实测） | 265.2 | m³ | `p3_decline:groups[3].EUR_data` |
| Case1 Cn=0.5 ts=25：EUR（M5 拟合） | 267.2 | m³ | `p3_decline:groups[3].EUR_shared` |
| Case1 Cn=0.5 ts=30：q1 | 8.282 | m³/d | `p3_decline:groups[4].qi_shared` |
| Case1 Cn=0.5 ts=30：EUR（实测） | 272.5 | m³ | `p3_decline:groups[4].EUR_data` |
| Case1 Cn=0.5 ts=30：EUR（M5 拟合） | 276.6 | m³ | `p3_decline:groups[4].EUR_shared` |
| Case1 Cn=0.5 ts=35：q1 | 8.334 | m³/d | `p3_decline:groups[5].qi_shared` |
| Case1 Cn=0.5 ts=35：EUR（实测） | 273.1 | m³ | `p3_decline:groups[5].EUR_data` |
| Case1 Cn=0.5 ts=35：EUR（M5 拟合） | 278.3 | m³ | `p3_decline:groups[5].EUR_shared` |
| Case1 Cn=0.5 ts=40：q1 | 8.365 | m³/d | `p3_decline:groups[6].qi_shared` |
| Case1 Cn=0.5 ts=40：EUR（实测） | 274.7 | m³ | `p3_decline:groups[6].EUR_data` |
| Case1 Cn=0.5 ts=40：EUR（M5 拟合） | 279.4 | m³ | `p3_decline:groups[6].EUR_shared` |
| Case1 Cn=0.5 ts=45：q1 | 8.389 | m³/d | `p3_decline:groups[7].qi_shared` |
| Case1 Cn=0.5 ts=45：EUR（实测） | 274.7 | m³ | `p3_decline:groups[7].EUR_data` |
| Case1 Cn=0.5 ts=45：EUR（M5 拟合） | 280.2 | m³ | `p3_decline:groups[7].EUR_shared` |
| Case1 Cn=0.5 ts=5：q1 | 4.405 | m³/d | `p3_decline:groups[8].qi_shared` |
| Case1 Cn=0.5 ts=5：EUR（实测） | 144.6 | m³ | `p3_decline:groups[8].EUR_data` |
| Case1 Cn=0.5 ts=5：EUR（M5 拟合） | 147.1 | m³ | `p3_decline:groups[8].EUR_shared` |
| Case1 Cn=0.5 ts=50：q1 | 8.452 | m³/d | `p3_decline:groups[9].qi_shared` |
| Case1 Cn=0.5 ts=50：EUR（实测） | 276.6 | m³ | `p3_decline:groups[9].EUR_data` |
| Case1 Cn=0.5 ts=50：EUR（M5 拟合） | 282.3 | m³ | `p3_decline:groups[9].EUR_shared` |
| Case1 Cn=0.5 ts=55：q1 | 8.353 | m³/d | `p3_decline:groups[10].qi_shared` |
| Case1 Cn=0.5 ts=55：EUR（实测） | 275 | m³ | `p3_decline:groups[10].EUR_data` |
| Case1 Cn=0.5 ts=55：EUR（M5 拟合） | 279 | m³ | `p3_decline:groups[10].EUR_shared` |
| Case1 Cn=0.5 ts=60：q1 | 8.332 | m³/d | `p3_decline:groups[11].qi_shared` |
| Case1 Cn=0.5 ts=60：EUR（实测） | 273.5 | m³ | `p3_decline:groups[11].EUR_data` |
| Case1 Cn=0.5 ts=60：EUR（M5 拟合） | 278.3 | m³ | `p3_decline:groups[11].EUR_shared` |
| Case1 Cn=1.0 ts=10：q1 | 6.791 | m³/d | `p3_decline:groups[12].qi_shared` |
| Case1 Cn=1.0 ts=10：EUR（实测） | 223.2 | m³ | `p3_decline:groups[12].EUR_data` |
| Case1 Cn=1.0 ts=10：EUR（M5 拟合） | 226.8 | m³ | `p3_decline:groups[12].EUR_shared` |
| Case1 Cn=1.0 ts=15：q1 | 7.849 | m³/d | `p3_decline:groups[13].qi_shared` |
| Case1 Cn=1.0 ts=15：EUR（实测） | 257.6 | m³ | `p3_decline:groups[13].EUR_data` |
| Case1 Cn=1.0 ts=15：EUR（M5 拟合） | 262.2 | m³ | `p3_decline:groups[13].EUR_shared` |
| Case1 Cn=1.0 ts=20：q1 | 8.256 | m³/d | `p3_decline:groups[14].qi_shared` |
| Case1 Cn=1.0 ts=20：EUR（实测） | 271.6 | m³ | `p3_decline:groups[14].EUR_data` |
| Case1 Cn=1.0 ts=20：EUR（M5 拟合） | 275.8 | m³ | `p3_decline:groups[14].EUR_shared` |
| Case1 Cn=1.0 ts=25：q1 | 8.659 | m³/d | `p3_decline:groups[15].qi_shared` |
| Case1 Cn=1.0 ts=25：EUR（实测） | 284.4 | m³ | `p3_decline:groups[15].EUR_data` |
| Case1 Cn=1.0 ts=25：EUR（M5 拟合） | 289.2 | m³ | `p3_decline:groups[15].EUR_shared` |
| Case1 Cn=1.0 ts=30：q1 | 8.714 | m³/d | `p3_decline:groups[16].qi_shared` |
| Case1 Cn=1.0 ts=30：EUR（实测） | 285.8 | m³ | `p3_decline:groups[16].EUR_data` |
| Case1 Cn=1.0 ts=30：EUR（M5 拟合） | 291.1 | m³ | `p3_decline:groups[16].EUR_shared` |
| Case1 Cn=1.0 ts=35：q1 | 8.757 | m³/d | `p3_decline:groups[17].qi_shared` |
| Case1 Cn=1.0 ts=35：EUR（实测） | 288.3 | m³ | `p3_decline:groups[17].EUR_data` |
| Case1 Cn=1.0 ts=35：EUR（M5 拟合） | 292.5 | m³ | `p3_decline:groups[17].EUR_shared` |
| Case1 Cn=1.0 ts=40：q1 | 8.771 | m³/d | `p3_decline:groups[18].qi_shared` |
| Case1 Cn=1.0 ts=40：EUR（实测） | 289.2 | m³ | `p3_decline:groups[18].EUR_data` |
| Case1 Cn=1.0 ts=40：EUR（M5 拟合） | 293 | m³ | `p3_decline:groups[18].EUR_shared` |
| Case1 Cn=1.0 ts=45：q1 | 8.739 | m³/d | `p3_decline:groups[19].qi_shared` |
| Case1 Cn=1.0 ts=45：EUR（实测） | 287.7 | m³ | `p3_decline:groups[19].EUR_data` |
| Case1 Cn=1.0 ts=45：EUR（M5 拟合） | 291.9 | m³ | `p3_decline:groups[19].EUR_shared` |
| Case1 Cn=1.0 ts=5：q1 | 4.692 | m³/d | `p3_decline:groups[20].qi_shared` |
| Case1 Cn=1.0 ts=5：EUR（实测） | 153.9 | m³ | `p3_decline:groups[20].EUR_data` |
| Case1 Cn=1.0 ts=5：EUR（M5 拟合） | 156.7 | m³ | `p3_decline:groups[20].EUR_shared` |
| Case1 Cn=1.0 ts=50：q1 | 8.695 | m³/d | `p3_decline:groups[21].qi_shared` |
| Case1 Cn=1.0 ts=50：EUR（实测） | 286.8 | m³ | `p3_decline:groups[21].EUR_data` |
| Case1 Cn=1.0 ts=50：EUR（M5 拟合） | 290.4 | m³ | `p3_decline:groups[21].EUR_shared` |
| Case1 Cn=1.0 ts=55：q1 | 8.845 | m³/d | `p3_decline:groups[22].qi_shared` |
| Case1 Cn=1.0 ts=55：EUR（实测） | 289.8 | m³ | `p3_decline:groups[22].EUR_data` |
| Case1 Cn=1.0 ts=55：EUR（M5 拟合） | 295.4 | m³ | `p3_decline:groups[22].EUR_shared` |
| Case1 Cn=1.0 ts=60：q1 | 8.795 | m³/d | `p3_decline:groups[23].qi_shared` |
| Case1 Cn=1.0 ts=60：EUR（实测） | 290.2 | m³ | `p3_decline:groups[23].EUR_data` |
| Case1 Cn=1.0 ts=60：EUR（M5 拟合） | 293.8 | m³ | `p3_decline:groups[23].EUR_shared` |
| Case1 Cn=1.5 ts=10：q1 | 7.197 | m³/d | `p3_decline:groups[24].qi_shared` |
| Case1 Cn=1.5 ts=10：EUR（实测） | 236.3 | m³ | `p3_decline:groups[24].EUR_data` |
| Case1 Cn=1.5 ts=10：EUR（M5 拟合） | 240.4 | m³ | `p3_decline:groups[24].EUR_shared` |
| Case1 Cn=1.5 ts=15：q1 | 8.257 | m³/d | `p3_decline:groups[25].qi_shared` |
| Case1 Cn=1.5 ts=15：EUR（实测） | 270.8 | m³ | `p3_decline:groups[25].EUR_data` |
| Case1 Cn=1.5 ts=15：EUR（M5 拟合） | 275.8 | m³ | `p3_decline:groups[25].EUR_shared` |
| Case1 Cn=1.5 ts=20：q1 | 8.776 | m³/d | `p3_decline:groups[26].qi_shared` |
| Case1 Cn=1.5 ts=20：EUR（实测） | 286.9 | m³ | `p3_decline:groups[26].EUR_data` |
| Case1 Cn=1.5 ts=20：EUR（M5 拟合） | 293.1 | m³ | `p3_decline:groups[26].EUR_shared` |
| Case1 Cn=1.5 ts=25：q1 | 8.977 | m³/d | `p3_decline:groups[27].qi_shared` |
| Case1 Cn=1.5 ts=25：EUR（实测） | 294.4 | m³ | `p3_decline:groups[27].EUR_data` |
| Case1 Cn=1.5 ts=25：EUR（M5 拟合） | 299.9 | m³ | `p3_decline:groups[27].EUR_shared` |
| Case1 Cn=1.5 ts=30：q1 | 9.098 | m³/d | `p3_decline:groups[28].qi_shared` |
| Case1 Cn=1.5 ts=30：EUR（实测） | 299.1 | m³ | `p3_decline:groups[28].EUR_data` |
| Case1 Cn=1.5 ts=30：EUR（M5 拟合） | 303.9 | m³ | `p3_decline:groups[28].EUR_shared` |
| Case1 Cn=1.5 ts=35：q1 | 9.25 | m³/d | `p3_decline:groups[29].qi_shared` |
| Case1 Cn=1.5 ts=35：EUR（实测） | 303.8 | m³ | `p3_decline:groups[29].EUR_data` |
| Case1 Cn=1.5 ts=35：EUR（M5 拟合） | 309 | m³ | `p3_decline:groups[29].EUR_shared` |
| Case1 Cn=1.5 ts=40：q1 | 9.03 | m³/d | `p3_decline:groups[30].qi_shared` |
| Case1 Cn=1.5 ts=40：EUR（实测） | 297.9 | m³ | `p3_decline:groups[30].EUR_data` |
| Case1 Cn=1.5 ts=40：EUR（M5 拟合） | 301.6 | m³ | `p3_decline:groups[30].EUR_shared` |
| Case1 Cn=1.5 ts=45：q1 | 9.192 | m³/d | `p3_decline:groups[31].qi_shared` |
| Case1 Cn=1.5 ts=45：EUR（实测） | 301.7 | m³ | `p3_decline:groups[31].EUR_data` |
| Case1 Cn=1.5 ts=45：EUR（M5 拟合） | 307 | m³ | `p3_decline:groups[31].EUR_shared` |
| Case1 Cn=1.5 ts=5：q1 | 4.901 | m³/d | `p3_decline:groups[32].qi_shared` |
| Case1 Cn=1.5 ts=5：EUR（实测） | 160.4 | m³ | `p3_decline:groups[32].EUR_data` |
| Case1 Cn=1.5 ts=5：EUR（M5 拟合） | 163.7 | m³ | `p3_decline:groups[32].EUR_shared` |
| Case1 Cn=1.5 ts=50：q1 | 8.958 | m³/d | `p3_decline:groups[33].qi_shared` |
| Case1 Cn=1.5 ts=50：EUR（实测） | 296.6 | m³ | `p3_decline:groups[33].EUR_data` |
| Case1 Cn=1.5 ts=50：EUR（M5 拟合） | 299.2 | m³ | `p3_decline:groups[33].EUR_shared` |
| Case1 Cn=1.5 ts=55：q1 | 9.268 | m³/d | `p3_decline:groups[34].qi_shared` |
| Case1 Cn=1.5 ts=55：EUR（实测） | 304 | m³ | `p3_decline:groups[34].EUR_data` |
| Case1 Cn=1.5 ts=55：EUR（M5 拟合） | 309.6 | m³ | `p3_decline:groups[34].EUR_shared` |
| Case1 Cn=1.5 ts=60：q1 | 9.181 | m³/d | `p3_decline:groups[35].qi_shared` |
| Case1 Cn=1.5 ts=60：EUR（实测） | 301.3 | m³ | `p3_decline:groups[35].EUR_data` |
| Case1 Cn=1.5 ts=60：EUR（M5 拟合） | 306.6 | m³ | `p3_decline:groups[35].EUR_shared` |
| Case2 Cn=0.5 ts=10：q1 | 18.39 | m³/d | `p3_decline:groups[36].qi_shared` |
| Case2 Cn=0.5 ts=10：EUR（实测） | 909.7 | m³ | `p3_decline:groups[36].EUR_data` |
| Case2 Cn=0.5 ts=10：EUR（M5 拟合） | 919.7 | m³ | `p3_decline:groups[36].EUR_shared` |
| Case2 Cn=0.5 ts=15：q1 | 22.01 | m³/d | `p3_decline:groups[37].qi_shared` |
| Case2 Cn=0.5 ts=15：EUR（实测） | 1088 | m³ | `p3_decline:groups[37].EUR_data` |
| Case2 Cn=0.5 ts=15：EUR（M5 拟合） | 1101 | m³ | `p3_decline:groups[37].EUR_shared` |
| Case2 Cn=0.5 ts=20：q1 | 23.92 | m³/d | `p3_decline:groups[38].qi_shared` |
| Case2 Cn=0.5 ts=20：EUR（实测） | 1182 | m³ | `p3_decline:groups[38].EUR_data` |
| Case2 Cn=0.5 ts=20：EUR（M5 拟合） | 1197 | m³ | `p3_decline:groups[38].EUR_shared` |
| Case2 Cn=0.5 ts=25：q1 | 24.72 | m³/d | `p3_decline:groups[39].qi_shared` |
| Case2 Cn=0.5 ts=25：EUR（实测） | 1225 | m³ | `p3_decline:groups[39].EUR_data` |
| Case2 Cn=0.5 ts=25：EUR（M5 拟合） | 1236 | m³ | `p3_decline:groups[39].EUR_shared` |
| Case2 Cn=0.5 ts=30：q1 | 25.29 | m³/d | `p3_decline:groups[40].qi_shared` |
| Case2 Cn=0.5 ts=30：EUR（实测） | 1260 | m³ | `p3_decline:groups[40].EUR_data` |
| Case2 Cn=0.5 ts=30：EUR（M5 拟合） | 1265 | m³ | `p3_decline:groups[40].EUR_shared` |
| Case2 Cn=0.5 ts=35：q1 | 25.5 | m³/d | `p3_decline:groups[41].qi_shared` |
| Case2 Cn=0.5 ts=35：EUR（实测） | 1269 | m³ | `p3_decline:groups[41].EUR_data` |
| Case2 Cn=0.5 ts=35：EUR（M5 拟合） | 1275 | m³ | `p3_decline:groups[41].EUR_shared` |
| Case2 Cn=0.5 ts=40：q1 | 25.9 | m³/d | `p3_decline:groups[42].qi_shared` |
| Case2 Cn=0.5 ts=40：EUR（实测） | 1285 | m³ | `p3_decline:groups[42].EUR_data` |
| Case2 Cn=0.5 ts=40：EUR（M5 拟合） | 1295 | m³ | `p3_decline:groups[42].EUR_shared` |
| Case2 Cn=0.5 ts=45：q1 | 26.1 | m³/d | `p3_decline:groups[43].qi_shared` |
| Case2 Cn=0.5 ts=45：EUR（实测） | 1292 | m³ | `p3_decline:groups[43].EUR_data` |
| Case2 Cn=0.5 ts=45：EUR（M5 拟合） | 1305 | m³ | `p3_decline:groups[43].EUR_shared` |
| Case2 Cn=0.5 ts=5：q1 | 11.89 | m³/d | `p3_decline:groups[44].qi_shared` |
| Case2 Cn=0.5 ts=5：EUR（实测） | 587.8 | m³ | `p3_decline:groups[44].EUR_data` |
| Case2 Cn=0.5 ts=5：EUR（M5 拟合） | 594.6 | m³ | `p3_decline:groups[44].EUR_shared` |
| Case2 Cn=0.5 ts=50：q1 | 26.47 | m³/d | `p3_decline:groups[45].qi_shared` |
| Case2 Cn=0.5 ts=50：EUR（实测） | 1307 | m³ | `p3_decline:groups[45].EUR_data` |
| Case2 Cn=0.5 ts=50：EUR（M5 拟合） | 1324 | m³ | `p3_decline:groups[45].EUR_shared` |
| Case2 Cn=0.5 ts=55：q1 | 26.1 | m³/d | `p3_decline:groups[46].qi_shared` |
| Case2 Cn=0.5 ts=55：EUR（实测） | 1295 | m³ | `p3_decline:groups[46].EUR_data` |
| Case2 Cn=0.5 ts=55：EUR（M5 拟合） | 1305 | m³ | `p3_decline:groups[46].EUR_shared` |
| Case2 Cn=0.5 ts=60：q1 | 26.18 | m³/d | `p3_decline:groups[47].qi_shared` |
| Case2 Cn=0.5 ts=60：EUR（实测） | 1296 | m³ | `p3_decline:groups[47].EUR_data` |
| Case2 Cn=0.5 ts=60：EUR（M5 拟合） | 1310 | m³ | `p3_decline:groups[47].EUR_shared` |
| Case2 Cn=1.0 ts=10：q1 | 18.99 | m³/d | `p3_decline:groups[48].qi_shared` |
| Case2 Cn=1.0 ts=10：EUR（实测） | 944.5 | m³ | `p3_decline:groups[48].EUR_data` |
| Case2 Cn=1.0 ts=10：EUR（M5 拟合） | 949.9 | m³ | `p3_decline:groups[48].EUR_shared` |
| Case2 Cn=1.0 ts=15：q1 | 23.05 | m³/d | `p3_decline:groups[49].qi_shared` |
| Case2 Cn=1.0 ts=15：EUR（实测） | 1138 | m³ | `p3_decline:groups[49].EUR_data` |
| Case2 Cn=1.0 ts=15：EUR（M5 拟合） | 1153 | m³ | `p3_decline:groups[49].EUR_shared` |
| Case2 Cn=1.0 ts=20：q1 | 24.99 | m³/d | `p3_decline:groups[50].qi_shared` |
| Case2 Cn=1.0 ts=20：EUR（实测） | 1236 | m³ | `p3_decline:groups[50].EUR_data` |
| Case2 Cn=1.0 ts=20：EUR（M5 拟合） | 1250 | m³ | `p3_decline:groups[50].EUR_shared` |
| Case2 Cn=1.0 ts=25：q1 | 25.89 | m³/d | `p3_decline:groups[51].qi_shared` |
| Case2 Cn=1.0 ts=25：EUR（实测） | 1283 | m³ | `p3_decline:groups[51].EUR_data` |
| Case2 Cn=1.0 ts=25：EUR（M5 拟合） | 1295 | m³ | `p3_decline:groups[51].EUR_shared` |
| Case2 Cn=1.0 ts=30：q1 | 26.63 | m³/d | `p3_decline:groups[52].qi_shared` |
| Case2 Cn=1.0 ts=30：EUR（实测） | 1318 | m³ | `p3_decline:groups[52].EUR_data` |
| Case2 Cn=1.0 ts=30：EUR（M5 拟合） | 1332 | m³ | `p3_decline:groups[52].EUR_shared` |
| Case2 Cn=1.0 ts=35：q1 | 27.54 | m³/d | `p3_decline:groups[53].qi_shared` |
| Case2 Cn=1.0 ts=35：EUR（实测） | 1352 | m³ | `p3_decline:groups[53].EUR_data` |
| Case2 Cn=1.0 ts=35：EUR（M5 拟合） | 1377 | m³ | `p3_decline:groups[53].EUR_shared` |
| Case2 Cn=1.0 ts=40：q1 | 27.49 | m³/d | `p3_decline:groups[54].qi_shared` |
| Case2 Cn=1.0 ts=40：EUR（实测） | 1363 | m³ | `p3_decline:groups[54].EUR_data` |
| Case2 Cn=1.0 ts=40：EUR（M5 拟合） | 1375 | m³ | `p3_decline:groups[54].EUR_shared` |
| Case2 Cn=1.0 ts=45：q1 | 27.24 | m³/d | `p3_decline:groups[55].qi_shared` |
| Case2 Cn=1.0 ts=45：EUR（实测） | 1356 | m³ | `p3_decline:groups[55].EUR_data` |
| Case2 Cn=1.0 ts=45：EUR（M5 拟合） | 1363 | m³ | `p3_decline:groups[55].EUR_shared` |
| Case2 Cn=1.0 ts=5：q1 | 12.3 | m³/d | `p3_decline:groups[56].qi_shared` |
| Case2 Cn=1.0 ts=5：EUR（实测） | 609.3 | m³ | `p3_decline:groups[56].EUR_data` |
| Case2 Cn=1.0 ts=5：EUR（M5 拟合） | 615 | m³ | `p3_decline:groups[56].EUR_shared` |
| Case2 Cn=1.0 ts=50：q1 | 27.4 | m³/d | `p3_decline:groups[57].qi_shared` |
| Case2 Cn=1.0 ts=50：EUR（实测） | 1356 | m³ | `p3_decline:groups[57].EUR_data` |
| Case2 Cn=1.0 ts=50：EUR（M5 拟合） | 1370 | m³ | `p3_decline:groups[57].EUR_shared` |
| Case2 Cn=1.0 ts=55：q1 | 27.93 | m³/d | `p3_decline:groups[58].qi_shared` |
| Case2 Cn=1.0 ts=55：EUR（实测） | 1371 | m³ | `p3_decline:groups[58].EUR_data` |
| Case2 Cn=1.0 ts=55：EUR（M5 拟合） | 1397 | m³ | `p3_decline:groups[58].EUR_shared` |
| Case2 Cn=1.0 ts=60：q1 | 27.68 | m³/d | `p3_decline:groups[59].qi_shared` |
| Case2 Cn=1.0 ts=60：EUR（实测） | 1367 | m³ | `p3_decline:groups[59].EUR_data` |
| Case2 Cn=1.0 ts=60：EUR（M5 拟合） | 1384 | m³ | `p3_decline:groups[59].EUR_shared` |
| Case2 Cn=1.5 ts=10：q1 | 20.26 | m³/d | `p3_decline:groups[60].qi_shared` |
| Case2 Cn=1.5 ts=10：EUR（实测） | 1002 | m³ | `p3_decline:groups[60].EUR_data` |
| Case2 Cn=1.5 ts=10：EUR（M5 拟合） | 1013 | m³ | `p3_decline:groups[60].EUR_shared` |
| Case2 Cn=1.5 ts=15：q1 | 23.97 | m³/d | `p3_decline:groups[61].qi_shared` |
| Case2 Cn=1.5 ts=15：EUR（实测） | 1187 | m³ | `p3_decline:groups[61].EUR_data` |
| Case2 Cn=1.5 ts=15：EUR（M5 拟合） | 1199 | m³ | `p3_decline:groups[61].EUR_shared` |
| Case2 Cn=1.5 ts=20：q1 | 26.01 | m³/d | `p3_decline:groups[62].qi_shared` |
| Case2 Cn=1.5 ts=20：EUR（实测） | 1290 | m³ | `p3_decline:groups[62].EUR_data` |
| Case2 Cn=1.5 ts=20：EUR（M5 拟合） | 1301 | m³ | `p3_decline:groups[62].EUR_shared` |
| Case2 Cn=1.5 ts=25：q1 | 27.4 | m³/d | `p3_decline:groups[63].qi_shared` |
| Case2 Cn=1.5 ts=25：EUR（实测） | 1353 | m³ | `p3_decline:groups[63].EUR_data` |
| Case2 Cn=1.5 ts=25：EUR（M5 拟合） | 1370 | m³ | `p3_decline:groups[63].EUR_shared` |
| Case2 Cn=1.5 ts=30：q1 | 28.05 | m³/d | `p3_decline:groups[64].qi_shared` |
| Case2 Cn=1.5 ts=30：EUR（实测） | 1386 | m³ | `p3_decline:groups[64].EUR_data` |
| Case2 Cn=1.5 ts=30：EUR（M5 拟合） | 1403 | m³ | `p3_decline:groups[64].EUR_shared` |
| Case2 Cn=1.5 ts=35：q1 | 28.51 | m³/d | `p3_decline:groups[65].qi_shared` |
| Case2 Cn=1.5 ts=35：EUR（实测） | 1410 | m³ | `p3_decline:groups[65].EUR_data` |
| Case2 Cn=1.5 ts=35：EUR（M5 拟合） | 1426 | m³ | `p3_decline:groups[65].EUR_shared` |
| Case2 Cn=1.5 ts=40：q1 | 28.39 | m³/d | `p3_decline:groups[66].qi_shared` |
| Case2 Cn=1.5 ts=40：EUR（实测） | 1405 | m³ | `p3_decline:groups[66].EUR_data` |
| Case2 Cn=1.5 ts=40：EUR（M5 拟合） | 1420 | m³ | `p3_decline:groups[66].EUR_shared` |
| Case2 Cn=1.5 ts=45：q1 | 28.84 | m³/d | `p3_decline:groups[67].qi_shared` |
| Case2 Cn=1.5 ts=45：EUR（实测） | 1425 | m³ | `p3_decline:groups[67].EUR_data` |
| Case2 Cn=1.5 ts=45：EUR（M5 拟合） | 1442 | m³ | `p3_decline:groups[67].EUR_shared` |
| Case2 Cn=1.5 ts=5：q1 | 13.19 | m³/d | `p3_decline:groups[68].qi_shared` |
| Case2 Cn=1.5 ts=5：EUR（实测） | 648.9 | m³ | `p3_decline:groups[68].EUR_data` |
| Case2 Cn=1.5 ts=5：EUR（M5 拟合） | 659.7 | m³ | `p3_decline:groups[68].EUR_shared` |
| Case2 Cn=1.5 ts=50：q1 | 28.47 | m³/d | `p3_decline:groups[69].qi_shared` |
| Case2 Cn=1.5 ts=50：EUR（实测） | 1415 | m³ | `p3_decline:groups[69].EUR_data` |
| Case2 Cn=1.5 ts=50：EUR（M5 拟合） | 1424 | m³ | `p3_decline:groups[69].EUR_shared` |
| Case2 Cn=1.5 ts=55：q1 | 28.38 | m³/d | `p3_decline:groups[70].qi_shared` |
| Case2 Cn=1.5 ts=55：EUR（实测） | 1410 | m³ | `p3_decline:groups[70].EUR_data` |
| Case2 Cn=1.5 ts=55：EUR（M5 拟合） | 1420 | m³ | `p3_decline:groups[70].EUR_shared` |
| Case2 Cn=1.5 ts=60：q1 | 28.61 | m³/d | `p3_decline:groups[71].qi_shared` |
| Case2 Cn=1.5 ts=60：EUR（实测） | 1418 | m³ | `p3_decline:groups[71].EUR_data` |
| Case2 Cn=1.5 ts=60：EUR（M5 拟合） | 1431 | m³ | `p3_decline:groups[71].EUR_shared` |
| Case3 Cn=0.5 ts=10：q1 | 32.99 | m³/d | `p3_decline:groups[72].qi_shared` |
| Case3 Cn=0.5 ts=10：EUR（实测） | 2176 | m³ | `p3_decline:groups[72].EUR_data` |
| Case3 Cn=0.5 ts=10：EUR（M5 拟合） | 2189 | m³ | `p3_decline:groups[72].EUR_shared` |
| Case3 Cn=0.5 ts=15：q1 | 40.92 | m³/d | `p3_decline:groups[73].qi_shared` |
| Case3 Cn=0.5 ts=15：EUR（实测） | 2692 | m³ | `p3_decline:groups[73].EUR_data` |
| Case3 Cn=0.5 ts=15：EUR（M5 拟合） | 2716 | m³ | `p3_decline:groups[73].EUR_shared` |
| Case3 Cn=0.5 ts=20：q1 | 45.45 | m³/d | `p3_decline:groups[74].qi_shared` |
| Case3 Cn=0.5 ts=20：EUR（实测） | 2986 | m³ | `p3_decline:groups[74].EUR_data` |
| Case3 Cn=0.5 ts=20：EUR（M5 拟合） | 3017 | m³ | `p3_decline:groups[74].EUR_shared` |
| Case3 Cn=0.5 ts=25：q1 | 48.95 | m³/d | `p3_decline:groups[75].qi_shared` |
| Case3 Cn=0.5 ts=25：EUR（实测） | 3208 | m³ | `p3_decline:groups[75].EUR_data` |
| Case3 Cn=0.5 ts=25：EUR（M5 拟合） | 3249 | m³ | `p3_decline:groups[75].EUR_shared` |
| Case3 Cn=0.5 ts=30：q1 | 50.12 | m³/d | `p3_decline:groups[76].qi_shared` |
| Case3 Cn=0.5 ts=30：EUR（实测） | 3295 | m³ | `p3_decline:groups[76].EUR_data` |
| Case3 Cn=0.5 ts=30：EUR（M5 拟合） | 3326 | m³ | `p3_decline:groups[76].EUR_shared` |
| Case3 Cn=0.5 ts=35：q1 | 50.46 | m³/d | `p3_decline:groups[77].qi_shared` |
| Case3 Cn=0.5 ts=35：EUR（实测） | 3341 | m³ | `p3_decline:groups[77].EUR_data` |
| Case3 Cn=0.5 ts=35：EUR（M5 拟合） | 3349 | m³ | `p3_decline:groups[77].EUR_shared` |
| Case3 Cn=0.5 ts=40：q1 | 51.88 | m³/d | `p3_decline:groups[78].qi_shared` |
| Case3 Cn=0.5 ts=40：EUR（实测） | 3413 | m³ | `p3_decline:groups[78].EUR_data` |
| Case3 Cn=0.5 ts=40：EUR（M5 拟合） | 3443 | m³ | `p3_decline:groups[78].EUR_shared` |
| Case3 Cn=0.5 ts=45：q1 | 52.08 | m³/d | `p3_decline:groups[79].qi_shared` |
| Case3 Cn=0.5 ts=45：EUR（实测） | 3427 | m³ | `p3_decline:groups[79].EUR_data` |
| Case3 Cn=0.5 ts=45：EUR（M5 拟合） | 3457 | m³ | `p3_decline:groups[79].EUR_shared` |
| Case3 Cn=0.5 ts=5：q1 | 20.73 | m³/d | `p3_decline:groups[80].qi_shared` |
| Case3 Cn=0.5 ts=5：EUR（实测） | 1363 | m³ | `p3_decline:groups[80].EUR_data` |
| Case3 Cn=0.5 ts=5：EUR（M5 拟合） | 1376 | m³ | `p3_decline:groups[80].EUR_shared` |
| Case3 Cn=0.5 ts=50：q1 | 52.23 | m³/d | `p3_decline:groups[81].qi_shared` |
| Case3 Cn=0.5 ts=50：EUR（实测） | 3442 | m³ | `p3_decline:groups[81].EUR_data` |
| Case3 Cn=0.5 ts=50：EUR（M5 拟合） | 3466 | m³ | `p3_decline:groups[81].EUR_shared` |
| Case3 Cn=0.5 ts=55：q1 | 52.08 | m³/d | `p3_decline:groups[82].qi_shared` |
| Case3 Cn=0.5 ts=55：EUR（实测） | 3434 | m³ | `p3_decline:groups[82].EUR_data` |
| Case3 Cn=0.5 ts=55：EUR（M5 拟合） | 3457 | m³ | `p3_decline:groups[82].EUR_shared` |
| Case3 Cn=0.5 ts=60：q1 | 52.49 | m³/d | `p3_decline:groups[83].qi_shared` |
| Case3 Cn=0.5 ts=60：EUR（实测） | 3469 | m³ | `p3_decline:groups[83].EUR_data` |
| Case3 Cn=0.5 ts=60：EUR（M5 拟合） | 3484 | m³ | `p3_decline:groups[83].EUR_shared` |
| Case3 Cn=1.0 ts=10：q1 | 34.91 | m³/d | `p3_decline:groups[84].qi_shared` |
| Case3 Cn=1.0 ts=10：EUR（实测） | 2293 | m³ | `p3_decline:groups[84].EUR_data` |
| Case3 Cn=1.0 ts=10：EUR（M5 拟合） | 2317 | m³ | `p3_decline:groups[84].EUR_shared` |
| Case3 Cn=1.0 ts=15：q1 | 43.17 | m³/d | `p3_decline:groups[85].qi_shared` |
| Case3 Cn=1.0 ts=15：EUR（实测） | 2827 | m³ | `p3_decline:groups[85].EUR_data` |
| Case3 Cn=1.0 ts=15：EUR（M5 拟合） | 2865 | m³ | `p3_decline:groups[85].EUR_shared` |
| Case3 Cn=1.0 ts=20：q1 | 47.55 | m³/d | `p3_decline:groups[86].qi_shared` |
| Case3 Cn=1.0 ts=20：EUR（实测） | 3137 | m³ | `p3_decline:groups[86].EUR_data` |
| Case3 Cn=1.0 ts=20：EUR（M5 拟合） | 3156 | m³ | `p3_decline:groups[86].EUR_shared` |
| Case3 Cn=1.0 ts=25：q1 | 50.11 | m³/d | `p3_decline:groups[87].qi_shared` |
| Case3 Cn=1.0 ts=25：EUR（实测） | 3314 | m³ | `p3_decline:groups[87].EUR_data` |
| Case3 Cn=1.0 ts=25：EUR（M5 拟合） | 3326 | m³ | `p3_decline:groups[87].EUR_shared` |
| Case3 Cn=1.0 ts=30：q1 | 51.85 | m³/d | `p3_decline:groups[88].qi_shared` |
| Case3 Cn=1.0 ts=30：EUR（实测） | 3434 | m³ | `p3_decline:groups[88].EUR_data` |
| Case3 Cn=1.0 ts=30：EUR（M5 拟合） | 3441 | m³ | `p3_decline:groups[88].EUR_shared` |
| Case3 Cn=1.0 ts=35：q1 | 53.27 | m³/d | `p3_decline:groups[89].qi_shared` |
| Case3 Cn=1.0 ts=35：EUR（实测） | 3512 | m³ | `p3_decline:groups[89].EUR_data` |
| Case3 Cn=1.0 ts=35：EUR（M5 拟合） | 3536 | m³ | `p3_decline:groups[89].EUR_shared` |
| Case3 Cn=1.0 ts=40：q1 | 53.82 | m³/d | `p3_decline:groups[90].qi_shared` |
| Case3 Cn=1.0 ts=40：EUR（实测） | 3545 | m³ | `p3_decline:groups[90].EUR_data` |
| Case3 Cn=1.0 ts=40：EUR（M5 拟合） | 3572 | m³ | `p3_decline:groups[90].EUR_shared` |
| Case3 Cn=1.0 ts=45：q1 | 54.34 | m³/d | `p3_decline:groups[91].qi_shared` |
| Case3 Cn=1.0 ts=45：EUR（实测） | 3585 | m³ | `p3_decline:groups[91].EUR_data` |
| Case3 Cn=1.0 ts=45：EUR（M5 拟合） | 3607 | m³ | `p3_decline:groups[91].EUR_shared` |
| Case3 Cn=1.0 ts=5：q1 | 21.64 | m³/d | `p3_decline:groups[92].qi_shared` |
| Case3 Cn=1.0 ts=5：EUR（实测） | 1425 | m³ | `p3_decline:groups[92].EUR_data` |
| Case3 Cn=1.0 ts=5：EUR（M5 拟合） | 1436 | m³ | `p3_decline:groups[92].EUR_shared` |
| Case3 Cn=1.0 ts=50：q1 | 54.71 | m³/d | `p3_decline:groups[93].qi_shared` |
| Case3 Cn=1.0 ts=50：EUR（实测） | 3602 | m³ | `p3_decline:groups[93].EUR_data` |
| Case3 Cn=1.0 ts=50：EUR（M5 拟合） | 3631 | m³ | `p3_decline:groups[93].EUR_shared` |
| Case3 Cn=1.0 ts=55：q1 | 55.35 | m³/d | `p3_decline:groups[94].qi_shared` |
| Case3 Cn=1.0 ts=55：EUR（实测） | 3628 | m³ | `p3_decline:groups[94].EUR_data` |
| Case3 Cn=1.0 ts=55：EUR（M5 拟合） | 3673 | m³ | `p3_decline:groups[94].EUR_shared` |
| Case3 Cn=1.0 ts=60：q1 | 54.9 | m³/d | `p3_decline:groups[95].qi_shared` |
| Case3 Cn=1.0 ts=60：EUR（实测） | 3615 | m³ | `p3_decline:groups[95].EUR_data` |
| Case3 Cn=1.0 ts=60：EUR（M5 拟合） | 3644 | m³ | `p3_decline:groups[95].EUR_shared` |
| Case3 Cn=1.5 ts=10：q1 | 36.48 | m³/d | `p3_decline:groups[96].qi_shared` |
| Case3 Cn=1.5 ts=10：EUR（实测） | 2394 | m³ | `p3_decline:groups[96].EUR_data` |
| Case3 Cn=1.5 ts=10：EUR（M5 拟合） | 2421 | m³ | `p3_decline:groups[96].EUR_shared` |
| Case3 Cn=1.5 ts=15：q1 | 44.39 | m³/d | `p3_decline:groups[97].qi_shared` |
| Case3 Cn=1.5 ts=15：EUR（实测） | 2926 | m³ | `p3_decline:groups[97].EUR_data` |
| Case3 Cn=1.5 ts=15：EUR（M5 拟合） | 2947 | m³ | `p3_decline:groups[97].EUR_shared` |
| Case3 Cn=1.5 ts=20：q1 | 50.12 | m³/d | `p3_decline:groups[98].qi_shared` |
| Case3 Cn=1.5 ts=20：EUR（实测） | 3288 | m³ | `p3_decline:groups[98].EUR_data` |
| Case3 Cn=1.5 ts=20：EUR（M5 拟合） | 3327 | m³ | `p3_decline:groups[98].EUR_shared` |
| Case3 Cn=1.5 ts=25：q1 | 53.28 | m³/d | `p3_decline:groups[99].qi_shared` |
| Case3 Cn=1.5 ts=25：EUR（实测） | 3504 | m³ | `p3_decline:groups[99].EUR_data` |
| Case3 Cn=1.5 ts=25：EUR（M5 拟合） | 3536 | m³ | `p3_decline:groups[99].EUR_shared` |
| Case3 Cn=1.5 ts=30：q1 | 55.33 | m³/d | `p3_decline:groups[100].qi_shared` |
| Case3 Cn=1.5 ts=30：EUR（实测） | 3643 | m³ | `p3_decline:groups[100].EUR_data` |
| Case3 Cn=1.5 ts=30：EUR（M5 拟合） | 3672 | m³ | `p3_decline:groups[100].EUR_shared` |
| Case3 Cn=1.5 ts=35：q1 | 55.38 | m³/d | `p3_decline:groups[101].qi_shared` |
| Case3 Cn=1.5 ts=35：EUR（实测） | 3660 | m³ | `p3_decline:groups[101].EUR_data` |
| Case3 Cn=1.5 ts=35：EUR（M5 拟合） | 3676 | m³ | `p3_decline:groups[101].EUR_shared` |
| Case3 Cn=1.5 ts=40：q1 | 56.48 | m³/d | `p3_decline:groups[102].qi_shared` |
| Case3 Cn=1.5 ts=40：EUR（实测） | 3722 | m³ | `p3_decline:groups[102].EUR_data` |
| Case3 Cn=1.5 ts=40：EUR（M5 拟合） | 3748 | m³ | `p3_decline:groups[102].EUR_shared` |
| Case3 Cn=1.5 ts=45：q1 | 56.2 | m³/d | `p3_decline:groups[103].qi_shared` |
| Case3 Cn=1.5 ts=45：EUR（实测） | 3707 | m³ | `p3_decline:groups[103].EUR_data` |
| Case3 Cn=1.5 ts=45：EUR（M5 拟合） | 3730 | m³ | `p3_decline:groups[103].EUR_shared` |
| Case3 Cn=1.5 ts=5：q1 | 22.55 | m³/d | `p3_decline:groups[104].qi_shared` |
| Case3 Cn=1.5 ts=5：EUR（实测） | 1488 | m³ | `p3_decline:groups[104].EUR_data` |
| Case3 Cn=1.5 ts=5：EUR（M5 拟合） | 1497 | m³ | `p3_decline:groups[104].EUR_shared` |
| Case3 Cn=1.5 ts=50：q1 | 56.95 | m³/d | `p3_decline:groups[105].qi_shared` |
| Case3 Cn=1.5 ts=50：EUR（实测） | 3760 | m³ | `p3_decline:groups[105].EUR_data` |
| Case3 Cn=1.5 ts=50：EUR（M5 拟合） | 3780 | m³ | `p3_decline:groups[105].EUR_shared` |
| Case3 Cn=1.5 ts=55：q1 | 57.28 | m³/d | `p3_decline:groups[106].qi_shared` |
| Case3 Cn=1.5 ts=55：EUR（实测） | 3770 | m³ | `p3_decline:groups[106].EUR_data` |
| Case3 Cn=1.5 ts=55：EUR（M5 拟合） | 3802 | m³ | `p3_decline:groups[106].EUR_shared` |
| Case3 Cn=1.5 ts=60：q1 | 57.09 | m³/d | `p3_decline:groups[107].qi_shared` |
| Case3 Cn=1.5 ts=60：EUR（实测） | 3768 | m³ | `p3_decline:groups[107].EUR_data` |
| Case3 Cn=1.5 ts=60：EUR（M5 拟合） | 3789 | m³ | `p3_decline:groups[107].EUR_shared` |

## 4  P4：题面 B.4 的官方检验向量

用来锁定成本口径。Vinj=3000、fCO2=0.5、Cn=1.0、注入 10 d、浸泡 30 d。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| 水相体积 Vaq | 1500 | m³ | `p4_econ:test_b4.Vaq` |
| 纳米材料用量 | 15 | t | `p4_econ:test_b4.m_nano_t` |
| 纳米材料费 | 300 | 万元 | `p4_econ:test_b4.cost_nano_wan` |
| CO2 用量 | 1275 | t | `p4_econ:test_b4.m_co2_t` |
| CO2 费 | 38.25 | 万元 | `p4_econ:test_b4.cost_CO2_wan` |
| 注入天数 | 10 | d | `p4_econ:test_b4.tinj_d` |
| 小计（不含生产费） | 848.2 | 万元 | `p4_econ:test_b4.subtotal_wan` |
| 断言通过 | 1 | — | `p4_econ:test_b4.PASS` |

## 4b  P4：最优浸泡时间的两套口径（Cn=1.0）

档位最优是工程可执行的决策值；连续驻点是 dNPV/dts=0 的解。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  ts_data_grid（档位最优） | 10 | d | `p4_econ:optimum_two_calibers.Case1|cn1.0.ts_data_grid` |
| Case1  ts_continuous（连续驻点） | 9.78 | d | `p4_econ:optimum_two_calibers.Case1|cn1.0.ts_continuous` |
| Case1  档位最优处的 NPV | -720.21 | 万元 | `p4_econ:optimum_two_calibers.Case1|cn1.0.npv_at_data_grid` |
| Case1  两口径之差 Δts | -0.22 | d | `p4_econ:optimum_two_calibers.Case1|cn1.0.d_ts` |
| Case1  两口径之差 ΔNPV | 0.00 | 万元 | `p4_econ:optimum_two_calibers.Case1|cn1.0.d_npv_wan` |
| Case1  ±2% 平台带 | [4, 19] | d | `p4_econ:optimum_ts.Case1|cn1.0.band_2pct` |
| Case1  ts=5 d 的 NPV | -726.77 | 万元 | `p4_econ:optimum_ts.Case1|cn1.0.npv_at_5` |
| Case1  ts=30 d 的 NPV | -761.95 | 万元 | `p4_econ:optimum_ts.Case1|cn1.0.npv_at_30` |
| Case2  ts_data_grid（档位最优） | 25 | d | `p4_econ:optimum_two_calibers.Case2|cn1.0.ts_data_grid` |
| Case2  ts_continuous（连续驻点） | 23.49 | d | `p4_econ:optimum_two_calibers.Case2|cn1.0.ts_continuous` |
| Case2  档位最优处的 NPV | -445.97 | 万元 | `p4_econ:optimum_two_calibers.Case2|cn1.0.npv_at_data_grid` |
| Case2  两口径之差 Δts | -1.51 | d | `p4_econ:optimum_two_calibers.Case2|cn1.0.d_ts` |
| Case2  两口径之差 ΔNPV | 0.56 | 万元 | `p4_econ:optimum_two_calibers.Case2|cn1.0.d_npv_wan` |
| Case2  ±2% 平台带 | [18, 31] | d | `p4_econ:optimum_ts.Case2|cn1.0.band_2pct` |
| Case2  ts=5 d 的 NPV | -587.66 | 万元 | `p4_econ:optimum_ts.Case2|cn1.0.npv_at_5` |
| Case2  ts=30 d 的 NPV | -451.96 | 万元 | `p4_econ:optimum_ts.Case2|cn1.0.npv_at_30` |
| Case3  ts_data_grid（档位最优） | 35 | d | `p4_econ:optimum_two_calibers.Case3|cn1.0.ts_data_grid` |
| Case3  ts_continuous（连续驻点） | 35.44 | d | `p4_econ:optimum_two_calibers.Case3|cn1.0.ts_continuous` |
| Case3  档位最优处的 NPV | 184.26 | 万元 | `p4_econ:optimum_two_calibers.Case3|cn1.0.npv_at_data_grid` |
| Case3  两口径之差 Δts | 0.44 | d | `p4_econ:optimum_two_calibers.Case3|cn1.0.d_ts` |
| Case3  两口径之差 ΔNPV | 0.00 | 万元 | `p4_econ:optimum_two_calibers.Case3|cn1.0.d_npv_wan` |
| Case3  ±2% 平台带 | [31, 40] | d | `p4_econ:optimum_ts.Case3|cn1.0.band_2pct` |
| Case3  ts=5 d 的 NPV | -347.20 | 万元 | `p4_econ:optimum_ts.Case3|cn1.0.npv_at_5` |
| Case3  ts=30 d 的 NPV | 179.42 | 万元 | `p4_econ:optimum_ts.Case3|cn1.0.npv_at_30` |

## 4c  P4：盈亏平衡反推（Cn=1.0，ts 取档位最优）

NPV = 0 所需的累计产油与实测之比，即"结构性亏损"的定量表述。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  实测累计油 | 224.7 | m³ | `p4_econ:break_even.Case1.EUR_obs` |
| Case1  NPV=0 所需累计油 | 2587 | m³ | `p4_econ:break_even.Case1.EUR_required_for_zero` |
| Case1  所需/实测 | 11.51 | 倍 | `p4_econ:break_even.Case1.ratio_required_over_observed` |
| Case1  NPV=0 所需油价 | 35417 | CNY/m³ | `p4_econ:break_even.Case1.price_required_for_zero` |
| Case1  NPV=0 所需的 Cfrac 变化量 | -600.2 | 万元 | `p4_econ:break_even.Case1.frac_cost_required_for_zero` |
| Case2  实测累计油 | 1274 | m³ | `p4_econ:break_even.Case2.EUR_obs` |
| Case2  NPV=0 所需累计油 | 2714 | m³ | `p4_econ:break_even.Case2.EUR_required_for_zero` |
| Case2  所需/实测 | 2.13 | 倍 | `p4_econ:break_even.Case2.ratio_required_over_observed` |
| Case2  NPV=0 所需油价 | 6840 | CNY/m³ | `p4_econ:break_even.Case2.price_required_for_zero` |
| Case2  NPV=0 所需的 Cfrac 变化量 | -325.4 | 万元 | `p4_econ:break_even.Case2.frac_cost_required_for_zero` |
| Case3  实测累计油 | 3517 | m³ | `p4_econ:break_even.Case3.EUR_obs` |
| Case3  NPV=0 所需累计油 | 2831 | m³ | `p4_econ:break_even.Case3.EUR_required_for_zero` |
| Case3  所需/实测 | 0.81 | 倍 | `p4_econ:break_even.Case3.ratio_required_over_observed` |
| Case3  NPV=0 所需油价 | 2802 | CNY/m³ | `p4_econ:break_even.Case3.price_required_for_zero` |
| Case3  NPV=0 所需的 Cfrac 变化量 | 304.3 | 万元 | `p4_econ:break_even.Case3.frac_cost_required_for_zero` |

## 4d  P4：V0 的两种口径与注入量不可识别

V0_geo 由机理 R_p(60 d) 与缝面面积给出；V0_emp 为经验值 1500 m³。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  R_p(60 d) | 40.64 | m | `p4_econ:V0.Case1.Rp60` |
| Case1  缝面面积 A_face | 8000 | m² | `p4_econ:V0.Case1.A_face` |
| Case1  V0_geo | 2.601e+04 | m³ | `p4_econ:V0.Case1.geo` |
| Case1  V0_emp | 1500 | m³ | `p4_econ:V0.Case1.emp` |
| Case1  V0=geo：max-NPV 解的 Vinj | 1000 | m³ | `p4_econ:pareto_meta.Case1|geo.npv_best.Vinj` |
| Case1  V0=geo：max-NPV | -220.12 | 万元 | `p4_econ:pareto_meta.Case1|geo.npv_best.npv` |
| Case1  V0=geo：前沿点数 | 328 | 个 | `p4_econ:pareto_meta.Case1|geo.n_front` |
| Case1  V0=geo：膝点的 ts / Vinj | 23 / 5000 | d / m³ | `p4_econ:pareto_meta.Case1|geo.knee` |
| Case1  V0=geo：膝点的 EUR / 成本 / NPV | 428 / 578 / -472.07 | m³ / 万元 / 万元 | `p4_econ:pareto_meta.Case1|geo.knee` |
| Case1  V0=emp：max-NPV 解的 Vinj | 1000 | m³ | `p4_econ:pareto_meta.Case1|emp.npv_best.Vinj` |
| Case1  V0=emp：max-NPV | -210.50 | 万元 | `p4_econ:pareto_meta.Case1|emp.npv_best.npv` |
| Case1  V0=emp：前沿点数 | 347 | 个 | `p4_econ:pareto_meta.Case1|emp.n_front` |
| Case1  V0=emp：膝点的 ts / Vinj | 25 / 3200 | d / m³ | `p4_econ:pareto_meta.Case1|emp.knee` |
| Case1  V0=emp：膝点的 EUR / 成本 / NPV | 274 / 444 / -361.66 | m³ / 万元 / 万元 | `p4_econ:pareto_meta.Case1|emp.knee` |
| Case1  NSGA-II 与网格 max-NPV 的相对差 | -0.0003147 | — | `p4_econ:pareto_meta.Case1|nsga2_check.rel_diff` |
| Case2  R_p(60 d) | 85.19 | m | `p4_econ:V0.Case2.Rp60` |
| Case2  缝面面积 A_face | 9600 | m² | `p4_econ:V0.Case2.A_face` |
| Case2  V0_geo | 8.179e+04 | m³ | `p4_econ:V0.Case2.geo` |
| Case2  V0_emp | 1500 | m³ | `p4_econ:V0.Case2.emp` |
| Case2  V0=geo：max-NPV 解的 Vinj | 4800 | m³ | `p4_econ:pareto_meta.Case2|geo.npv_best.Vinj` |
| Case2  V0=geo：max-NPV | 16.18 | 万元 | `p4_econ:pareto_meta.Case2|geo.npv_best.npv` |
| Case2  V0=geo：前沿点数 | 341 | 个 | `p4_econ:pareto_meta.Case2|geo.n_front` |
| Case2  V0=geo：膝点的 ts / Vinj | 27 / 5000 | d / m³ | `p4_econ:pareto_meta.Case2|geo.knee` |
| Case2  V0=geo：膝点的 EUR / 成本 / NPV | 2053 / 590 / 1.99 | m³ / 万元 / 万元 | `p4_econ:pareto_meta.Case2|geo.knee` |
| Case2  V0=emp：max-NPV 解的 Vinj | 1600 | m³ | `p4_econ:pareto_meta.Case2|emp.npv_best.Vinj` |
| Case2  V0=emp：max-NPV | -36.10 | 万元 | `p4_econ:pareto_meta.Case2|emp.npv_best.npv` |
| Case2  V0=emp：前沿点数 | 385 | 个 | `p4_econ:pareto_meta.Case2|emp.n_front` |
| Case2  V0=emp：膝点的 ts / Vinj | 29 / 3100 | d / m³ | `p4_econ:pareto_meta.Case2|emp.knee` |
| Case2  V0=emp：膝点的 EUR / 成本 / NPV | 1271 / 448 / -71.52 | m³ / 万元 / 万元 | `p4_econ:pareto_meta.Case2|emp.knee` |
| Case2  NSGA-II 与网格 max-NPV 的相对差 | -0.1406 | — | `p4_econ:pareto_meta.Case2|nsga2_check.rel_diff` |
| Case3  R_p(60 d) | 181.5 | m | `p4_econ:V0.Case3.Rp60` |
| Case3  缝面面积 A_face | 1.12e+04 | m² | `p4_econ:V0.Case3.A_face` |
| Case3  V0_geo | 2.642e+05 | m³ | `p4_econ:V0.Case3.geo` |
| Case3  V0_emp | 1500 | m³ | `p4_econ:V0.Case3.emp` |
| Case3  V0=geo：max-NPV 解的 Vinj | 5000 | m³ | `p4_econ:pareto_meta.Case3|geo.npv_best.Vinj` |
| Case3  V0=geo：max-NPV | 1028.63 | 万元 | `p4_econ:pareto_meta.Case3|geo.npv_best.npv` |
| Case3  V0=geo：前沿点数 | 341 | 个 | `p4_econ:pareto_meta.Case3|geo.n_front` |
| Case3  V0=geo：膝点的 ts / Vinj | 31 / 5000 | d / m³ | `p4_econ:pareto_meta.Case3|geo.knee` |
| Case3  V0=geo：膝点的 EUR / 成本 / NPV | 5495 / 602 / 1013.57 | m³ / 万元 / 万元 | `p4_econ:pareto_meta.Case3|geo.knee` |
| Case3  V0=emp：max-NPV 解的 Vinj | 3200 | m³ | `p4_econ:pareto_meta.Case3|emp.npv_best.Vinj` |
| Case3  V0=emp：max-NPV | 547.01 | 万元 | `p4_econ:pareto_meta.Case3|emp.npv_best.npv` |
| Case3  V0=emp：前沿点数 | 399 | 个 | `p4_econ:pareto_meta.Case3|emp.n_front` |
| Case3  V0=emp：膝点的 ts / Vinj | 33 / 3100 | d / m³ | `p4_econ:pareto_meta.Case3|emp.knee` |
| Case3  V0=emp：膝点的 EUR / 成本 / NPV | 3371 / 460 / 541.16 | m³ / 万元 / 万元 | `p4_econ:pareto_meta.Case3|emp.knee` |
| Case3  NSGA-II 与网格 max-NPV 的相对差 | -0.01394 | — | `p4_econ:pareto_meta.Case3|nsga2_check.rel_diff` |

## 4e  P4：±15% 扰动的鲁棒性（7 个因子 × 2 个符号 = 14 次）

判据是决策不变性：扰动后档位最优 ts 是否改变。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  基准 ts* | 10 | d | `p4_econ:robustness.Case1.base_ts` |
| Case1  基准 NPV | -720.21 | 万元 | `p4_econ:robustness.Case1.base_npv` |
| Case1  改变了 ts* 的扰动个数 | 0 | 个（共 14） | `p4_econ:robustness.Case1.n_changed` |
| Case1  NPV 相对摆幅 | 0.05 | — | `p4_econ:robustness.Case1.npv_span_rel` |
| Case2  基准 ts* | 23 | d | `p4_econ:robustness.Case2.base_ts` |
| Case2  基准 NPV | -445.40 | 万元 | `p4_econ:robustness.Case2.base_npv` |
| Case2  改变了 ts* 的扰动个数 | 0 | 个（共 14） | `p4_econ:robustness.Case2.n_changed` |
| Case2  NPV 相对摆幅 | 0.293 | — | `p4_econ:robustness.Case2.npv_span_rel` |
| Case3  基准 ts* | 35 | d | `p4_econ:robustness.Case3.base_ts` |
| Case3  基准 NPV | 184.26 | 万元 | `p4_econ:robustness.Case3.base_npv` |
| Case3  改变了 ts* 的扰动个数 | 2 | 个（共 14） | `p4_econ:robustness.Case3.n_changed` |
| Case3  NPV 相对摆幅 | 1.91 | — | `p4_econ:robustness.Case3.npv_span_rel` |

## 4f  P4：机理-数据差异的归因（方向 + 量级）

每条都可检验：给出"若假设不成立，预测偏高/偏低多少"。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  共享 D 的相对散布 ΔD/D | 0.00426 | — | `p4_econ:attribution.shared_D_impact.Case1.rel_dD` |
| Case1  共享 D 假设失效对 EUR 的相对影响 | 0.00426 | — | `p4_econ:attribution.shared_D_impact.Case1.d_EUR_rel` |
| Case2  共享 D 的相对散布 ΔD/D | 0.00226 | — | `p4_econ:attribution.shared_D_impact.Case2.rel_dD` |
| Case2  共享 D 假设失效对 EUR 的相对影响 | 0.00226 | — | `p4_econ:attribution.shared_D_impact.Case2.d_EUR_rel` |
| Case3  共享 D 的相对散布 ΔD/D | 0.00199 | — | `p4_econ:attribution.shared_D_impact.Case3.rel_dD` |
| Case3  共享 D 假设失效对 EUR 的相对影响 | 0.00199 | — | `p4_econ:attribution.shared_D_impact.Case3.d_EUR_rel` |
| 实测残差中位相对值（题面声明噪声 ±5%） | 0.1195 | — | `p4_econ:attribution.data_noise.measured_med_rel_resid` |
| 实测残差相对标准差 | 0.2909 | — | `p4_econ:attribution.data_noise.measured_resid_sd_rel` |
| Case1  EUR 的 bootstrap 半宽（噪声传播） | 2.29 | m³ | `p4_econ:attribution.data_noise.eur_ci_wan.Case1` |
| Case2  EUR 的 bootstrap 半宽（噪声传播） | 7.472 | m³ | `p4_econ:attribution.data_noise.eur_ci_wan.Case2` |
| Case3  EUR 的 bootstrap 半宽（噪声传播） | 24.51 | m³ | `p4_econ:attribution.data_noise.eur_ci_wan.Case3` |
| 缝面面积口径 | A_face = 4·Lf·hf = 2(条缝翼) × 2(个面) × Lf × hf | — | `p4_econ:attribution.A_face_convention.expression` |

## 5  P5：Sobol 全局敏感性（对 ts*）

N=1024，2k=16 维单一 Sobol 设计前后切分 A/B（实测 max|corr(A,B)| 见下），Jansen 估计量；S1 之和 ≈ 1、ST 之和 ≈ 1 说明交互项可忽略，模型近似可加。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| A/B 两矩阵列间最大 |corr| | 0.0234 | — | `p5_sobol:design.max_abs_corr_A_B` |
| 模型求值次数 | 18432 | 次 | `p5_sobol:design.n_eval` |
| 随机种子 | 20261120 | — | `p5_sobol:design.seed` |
| Case1  ΣS1（对 ts*） | 1.037 | — | `p5_sobol:sobol.Case1.ts.sum_S1` |
| Case1  ΣST（对 ts*） | 1.026 | — | `p5_sobol:sobol.Case1.ts.sum_ST` |
| Case1  max|S1−ST|（对 ts*） | 0.0113 | — | `p5_sobol:sobol.Case1.ts.max_abs_S1_minus_ST` |
| Case1  S1(Ainf) 对 ts* | 0.353 | — | `p5_sobol:sobol.Case1.ts.S1.Ainf` |
| Case1  ST(Ainf) 对 ts* | 0.3609 | — | `p5_sobol:sobol.Case1.ts.ST.Ainf` |
| Case1  S1(tau) 对 ts* | 0.09398 | — | `p5_sobol:sobol.Case1.ts.S1.tau` |
| Case1  ST(tau) 对 ts* | 0.1053 | — | `p5_sobol:sobol.Case1.ts.ST.tau` |
| Case1  S1(D) 对 ts* | 0.09353 | — | `p5_sobol:sobol.Case1.ts.S1.D` |
| Case1  ST(D) 对 ts* | 0.08869 | — | `p5_sobol:sobol.Case1.ts.ST.D` |
| Case1  S1(Poil) 对 ts* | 0.1133 | — | `p5_sobol:sobol.Case1.ts.S1.Poil` |
| Case1  ST(Poil) 对 ts* | 0.109 | — | `p5_sobol:sobol.Case1.ts.ST.Poil` |
| Case1  S1(cprod) 对 ts* | 0.009231 | — | `p5_sobol:sobol.Case1.ts.S1.cprod` |
| Case1  ST(cprod) 对 ts* | 0.001167 | — | `p5_sobol:sobol.Case1.ts.ST.cprod` |
| Case1  S1(csoak) 对 ts* | 0.3581 | — | `p5_sobol:sobol.Case1.ts.S1.csoak` |
| Case1  ST(csoak) 对 ts* | 0.3613 | — | `p5_sobol:sobol.Case1.ts.ST.csoak` |
| Case1  S1(Cfrac) 对 ts* | 0.007988 | — | `p5_sobol:sobol.Case1.ts.S1.Cfrac` |
| Case1  ST(Cfrac) 对 ts* | 0 | — | `p5_sobol:sobol.Case1.ts.ST.Cfrac` |
| Case1  S1(a) 对 ts* | 0.007988 | — | `p5_sobol:sobol.Case1.ts.S1.a` |
| Case1  ST(a) 对 ts* | 0 | — | `p5_sobol:sobol.Case1.ts.ST.a` |
| Case1  因子排序（按 ST） | csoak, Ainf, Poil, tau | — | `p5_sobol:sobol.Case1.ts.order` |
| Case2  ΣS1（对 ts*） | 1.023 | — | `p5_sobol:sobol.Case2.ts.sum_S1` |
| Case2  ΣST（对 ts*） | 1.014 | — | `p5_sobol:sobol.Case2.ts.sum_ST` |
| Case2  max|S1−ST|（对 ts*） | 0.006201 | — | `p5_sobol:sobol.Case2.ts.max_abs_S1_minus_ST` |
| Case2  S1(Ainf) 对 ts* | 0.179 | — | `p5_sobol:sobol.Case2.ts.S1.Ainf` |
| Case2  ST(Ainf) 对 ts* | 0.1825 | — | `p5_sobol:sobol.Case2.ts.ST.Ainf` |
| Case2  S1(tau) 对 ts* | 0.543 | — | `p5_sobol:sobol.Case2.ts.S1.tau` |
| Case2  ST(tau) 对 ts* | 0.5492 | — | `p5_sobol:sobol.Case2.ts.ST.tau` |
| Case2  S1(D) 对 ts* | 0.04667 | — | `p5_sobol:sobol.Case2.ts.S1.D` |
| Case2  ST(D) 对 ts* | 0.04363 | — | `p5_sobol:sobol.Case2.ts.ST.D` |
| Case2  S1(Poil) 对 ts* | 0.05832 | — | `p5_sobol:sobol.Case2.ts.S1.Poil` |
| Case2  ST(Poil) 对 ts* | 0.05515 | — | `p5_sobol:sobol.Case2.ts.ST.Poil` |
| Case2  S1(cprod) 对 ts* | 0.005181 | — | `p5_sobol:sobol.Case2.ts.S1.cprod` |
| Case2  ST(cprod) 对 ts* | 0.00059 | — | `p5_sobol:sobol.Case2.ts.ST.cprod` |
| Case2  S1(csoak) 对 ts* | 0.1816 | — | `p5_sobol:sobol.Case2.ts.S1.csoak` |
| Case2  ST(csoak) 对 ts* | 0.1827 | — | `p5_sobol:sobol.Case2.ts.ST.csoak` |
| Case2  S1(Cfrac) 对 ts* | 0.004552 | — | `p5_sobol:sobol.Case2.ts.S1.Cfrac` |
| Case2  ST(Cfrac) 对 ts* | 0 | — | `p5_sobol:sobol.Case2.ts.ST.Cfrac` |
| Case2  S1(a) 对 ts* | 0.004552 | — | `p5_sobol:sobol.Case2.ts.S1.a` |
| Case2  ST(a) 对 ts* | 0 | — | `p5_sobol:sobol.Case2.ts.ST.a` |
| Case2  因子排序（按 ST） | tau, csoak, Ainf, Poil | — | `p5_sobol:sobol.Case2.ts.order` |
| Case3  ΣS1（对 ts*） | 1.016 | — | `p5_sobol:sobol.Case3.ts.sum_S1` |
| Case3  ΣST（对 ts*） | 1.009 | — | `p5_sobol:sobol.Case3.ts.sum_ST` |
| Case3  max|S1−ST|（对 ts*） | 0.00397 | — | `p5_sobol:sobol.Case3.ts.max_abs_S1_minus_ST` |
| Case3  S1(Ainf) 对 ts* | 0.1103 | — | `p5_sobol:sobol.Case3.ts.S1.Ainf` |
| Case3  ST(Ainf) 对 ts* | 0.1121 | — | `p5_sobol:sobol.Case3.ts.ST.Ainf` |
| Case3  S1(tau) 对 ts* | 0.7206 | — | `p5_sobol:sobol.Case3.ts.S1.tau` |
| Case3  ST(tau) 对 ts* | 0.7246 | — | `p5_sobol:sobol.Case3.ts.ST.tau` |
| Case3  S1(D) 对 ts* | 0.0277 | — | `p5_sobol:sobol.Case3.ts.S1.D` |
| Case3  ST(D) 对 ts* | 0.02549 | — | `p5_sobol:sobol.Case3.ts.ST.D` |
| Case3  S1(Poil) 对 ts* | 0.03632 | — | `p5_sobol:sobol.Case3.ts.S1.Poil` |
| Case3  ST(Poil) 对 ts* | 0.03388 | — | `p5_sobol:sobol.Case3.ts.ST.Poil` |
| Case3  S1(cprod) 对 ts* | 0.003494 | — | `p5_sobol:sobol.Case3.ts.S1.cprod` |
| Case3  ST(cprod) 对 ts* | 0.0003626 | — | `p5_sobol:sobol.Case3.ts.ST.cprod` |
| Case3  S1(csoak) 对 ts* | 0.1117 | — | `p5_sobol:sobol.Case3.ts.S1.csoak` |
| Case3  ST(csoak) 对 ts* | 0.1122 | — | `p5_sobol:sobol.Case3.ts.ST.csoak` |
| Case3  S1(Cfrac) 对 ts* | 0.00311 | — | `p5_sobol:sobol.Case3.ts.S1.Cfrac` |
| Case3  ST(Cfrac) 对 ts* | 0 | — | `p5_sobol:sobol.Case3.ts.ST.Cfrac` |
| Case3  S1(a) 对 ts* | 0.00311 | — | `p5_sobol:sobol.Case3.ts.S1.a` |
| Case3  ST(a) 对 ts* | 0 | — | `p5_sobol:sobol.Case3.ts.ST.a` |
| Case3  因子排序（按 ST） | tau, csoak, Ainf, Poil | — | `p5_sobol:sobol.Case3.ts.order` |

## 5b  P5：弹性判据与 Sobol 的交叉验证

闭式 ts* = τ·ln(arg) 给出 e(A∞)=e(c_soak)=τ/ts*、e(τ)=(ts*−τ)/ts*；预测的 S1 比 = (e_i/e_A∞)²，与实测比对照。

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| Case1  ts*/τ | 1.48 | — | `p5_sobol:elasticity_check.Case1.ts_over_tau` |
| Case1  主导因子判据 | Ainf/csoak | — | `p5_sobol:elasticity_check.Case1.regime` |
| Case1  e(A∞) = e(c_soak) | 0.677 | — | `p5_sobol:elasticity_check.Case1.e_Ainf` |
| Case1  e(τ) | 0.323 | — | `p5_sobol:elasticity_check.Case1.e_tau` |
| Case1  预测 S1(τ)/S1(A∞) | 0.227 | — | `p5_sobol:elasticity_check.Case1.pred_S1_tau_over_Ainf` |
| Case1  实测 S1(τ)/S1(A∞) | 0.266 | — | `p5_sobol:elasticity_check.Case1.obs_S1_tau_over_Ainf` |
| Case1  实测 S1(c_soak)/S1(A∞) | 1.014 | — | `p5_sobol:elasticity_check.Case1.obs_S1_csoak_over_Ainf` |
| Case1  NPV 的 5/50/95 分位 | -762 / -720 / -675 | 万元 | `p5_sobol:sobol.Case1.quantiles.npv` |
| Case1  ts* 的 5/50/95 分位 | 6.5 / 9.5 / 13.2 | d | `p5_sobol:sobol.Case1.quantiles.ts` |
| Case2  ts*/τ | 2.82 | — | `p5_sobol:elasticity_check.Case2.ts_over_tau` |
| Case2  主导因子判据 | tau | — | `p5_sobol:elasticity_check.Case2.regime` |
| Case2  e(A∞) = e(c_soak) | 0.355 | — | `p5_sobol:elasticity_check.Case2.e_Ainf` |
| Case2  e(τ) | 0.645 | — | `p5_sobol:elasticity_check.Case2.e_tau` |
| Case2  预测 S1(τ)/S1(A∞) | 3.308 | — | `p5_sobol:elasticity_check.Case2.pred_S1_tau_over_Ainf` |
| Case2  实测 S1(τ)/S1(A∞) | 3.033 | — | `p5_sobol:elasticity_check.Case2.obs_S1_tau_over_Ainf` |
| Case2  实测 S1(c_soak)/S1(A∞) | 1.014 | — | `p5_sobol:elasticity_check.Case2.obs_S1_csoak_over_Ainf` |
| Case2  NPV 的 5/50/95 分位 | -574 / -449 / -286 | 万元 | `p5_sobol:sobol.Case2.quantiles.npv` |
| Case2  ts* 的 5/50/95 分位 | 18.0 / 23.1 / 29.5 | d | `p5_sobol:sobol.Case2.quantiles.ts` |
| Case3  ts*/τ | 3.55 | — | `p5_sobol:elasticity_check.Case3.ts_over_tau` |
| Case3  主导因子判据 | tau | — | `p5_sobol:elasticity_check.Case3.regime` |
| Case3  e(A∞) = e(c_soak) | 0.281 | — | `p5_sobol:elasticity_check.Case3.e_Ainf` |
| Case3  e(τ) | 0.719 | — | `p5_sobol:elasticity_check.Case3.e_tau` |
| Case3  预测 S1(τ)/S1(A∞) | 6.520 | — | `p5_sobol:elasticity_check.Case3.pred_S1_tau_over_Ainf` |
| Case3  实测 S1(τ)/S1(A∞) | 6.536 | — | `p5_sobol:elasticity_check.Case3.obs_S1_tau_over_Ainf` |
| Case3  实测 S1(c_soak)/S1(A∞) | 1.013 | — | `p5_sobol:elasticity_check.Case3.obs_S1_csoak_over_Ainf` |
| Case3  NPV 的 5/50/95 分位 | -151 / 171 / 600 | 万元 | `p5_sobol:sobol.Case3.quantiles.npv` |
| Case3  ts* 的 5/50/95 分位 | 27.3 / 35.1 / 44.1 | d | `p5_sobol:sobol.Case3.quantiles.ts` |

## 6  环境与数值对账

| 量 | 值 | 单位 | 来源 JSON 键 |
|---|---|---|---|
| numpy 版本 | 2.4.6 | — | `verify_env:numpy_version` |
| 手写 OLS 与 numpy 的一致性（三场景） | 5.9e-16 / 5.2e-16 / 4.6e-16 | — | `verify_env:slope_equivalence.{i}.rel_diff` |
| 对账通过 | 1 | — | `verify_env:PASS` |

VERDICT: PASS
