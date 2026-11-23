# 数字表

口径：除 `_meta` 与常量外，所有值由 `code/run_all.py` 一次跑出（四段合计 43.74 s，
预算 300 s，`run_all.json:within_budget`），
写进 `data/*.json`。第四列 `file.path` 的 file 是 `data/<file>.json`，path 是该 JSON 里的键路径
（数字段表示数组下标）。校验脚本 `code/check_numbers.py` 逐行解析本表并对账，失败数计入 `failures`。

基准：a=1 AU、e=0.3、i=30°、Ω=90°、ω=60°、θ_E=0（T1）；μ=1、c=3/2、γ=−0.277778（T2/T3）。

## T1 观测几何

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 三维真椭圆半轴比（沿轨道法向） | 0.953939 | 1 | t1_geometry.views.truth_ellipse.ratio |
| 黄道面俯视半轴比（题面的"真轨道"） | 0.880687 | 1 | t1_geometry.views.ecliptic_topdown.ratio |
| 地球方向正交投影半轴比 | 0.511193 | 1 | t1_geometry.views.from_earth_orthographic.ratio |
| 视椭圆长半轴 A | 0.965946 | AU | t1_geometry.views.from_earth_orthographic.A |
| 视椭圆短半轴 B | 0.493785 | AU | t1_geometry.views.from_earth_orthographic.B |
| 视椭圆主轴方位 ψ | -1.62071 | 度 | t1_geometry.views.from_earth_orthographic.psi_deg |
| 星像到视椭圆中心距离 | 0.198431 | AU | t1_geometry.views.from_earth_orthographic.center_offset |
| 视椭圆焦距 √(A²−B²) | 0.830197 | AU | t1_geometry.views.from_earth_orthographic.apparent_focus_distance |
| 星像距离 / 焦距 | 0.239017 | 1 | t1_geometry.views.from_earth_orthographic.star_vs_focus_ratio |
| 拱线方向与视椭圆主轴夹角 | 39.2727 | 度 | t1_geometry.views.from_earth_orthographic.apsidal_vs_major_deg |
| 圆轨道极限校验（σ比减解析值） | 0.0 | 1 | t1_geometry.views.circular_check.abs_diff |
| 视差主效应幂（精确−正交 ∝ ε^k） | 1.005 | 1 | t1_geometry.parallax.power_fits.exact_minus_orth.power |
| 该幂的 se | 0.00232 | 1 | t1_geometry.parallax.power_fits.exact_minus_orth.se_power |
| 一阶公式误差幂（精确−一阶 ∝ ε^k） | 2.006 | 1 | t1_geometry.parallax.power_fits.exact_minus_1st.power |
| 一阶公式误差系数 | 0.780264 | 1 | t1_geometry.parallax.power_fits.exact_minus_1st.intercept |
| 一阶曲线对圆锥的残差幂 | 1.997 | 1 | t1_geometry.parallax.power_fits.conic_resid_1st.power |
| 一阶曲线对圆锥的残差系数 | 0.0255908 | 1 | t1_geometry.parallax.power_fits.conic_resid_1st.intercept |
| 图卡选择差系数（gnomonic−方向余弦） | 0.751071 | 1 | t1_geometry.parallax.power_fits.gnomonic_minus_sin.intercept |
| 精确视曲线对二次曲线残差（d_E=100 a） | 1.37017e-16 | AU | t1_geometry.parallax.table.4.conic_exact |
| 一阶视曲线 2 次拟合残差（d_E=100 a） | 2.57258e-6 | AU | t1_geometry.parallax.table.4.ladder_1st.deg2 |
| 一阶视曲线 3 次拟合残差（d_E=100 a） | 4.68336e-11 | AU | t1_geometry.parallax.table.4.ladder_1st.deg3 |
| 一阶视曲线 4 次拟合残差（d_E=100 a） | 2.30483e-16 | AU | t1_geometry.parallax.table.4.ladder_1st.deg4 |
| 倾角扫描：半轴比最大改变 | 0.013881 | 1 | t1_geometry.inclination_scan.max_aspect_shift |
| 倾角扫描：中心偏移最大改变 | 0.312132 | AU | t1_geometry.inclination_scan.max_center_shift |
| 倾角扫描：近远心距比最大改变 | 0.087934 | 1 | t1_geometry.inclination_scan.max_peri_aph_shift |
| 倾角扫描：方位角最大偏离（引理 R-1） | 9.16e-11 | 角秒 | t1_geometry.inclination_scan.max_azimuth_gap_arcsec |
| 倾角扫描：一阶对二次残差最大 | 0.000196553 | AU | t1_geometry.inclination_scan.max_conic_resid_1st |
| 退化倾角个数（视曲线压成线段） | 1 | 个 | t1_geometry.inclination_scan.n_degenerate |
| 反演亏维数 | 2 | 个 | t1_geometry.identifiability.deficiency |
| 精确解族成员数（e∈[0.02,0.86]） | 378 | 个 | t1_geometry.identifiability.n_family_members |
| 精确解族覆盖的 e 下界 | 0.02 | 1 | t1_geometry.identifiability.e_range.0 |
| 火星会合周期 | 2.13533 | 年 | t1_geometry.solar_system_mars.synodic_period_yr |
| 火星视轨道逆行时间占比 | 0.59325 | 1 | t1_geometry.solar_system_mars.retrograde_time_fraction |
| 火星视轨道逆行弧段数 | 2 | 段 | t1_geometry.solar_system_mars.n_retrograde_episodes |
| 火星视轨道首尾不闭合度 | 0.0215071 | 1 | t1_geometry.solar_system_mars.apparent_path_not_closed |
| 火星视轨道 8 次拟合残差 | 4.2308e-8 | AU | t1_geometry.solar_system_mars.conic_ladder_apparent.deg8 |

## T2 双共振与单中心

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 解析解 vs 辛积分：径向相对误差 | 1.791e-6 | 1 | t2_resonance.validation.rel_r_error |
| 能量相对漂移 | 1.01052e-5 | 1 | t2_resonance.validation.energy_rel_drift |
| Δφ 每周期（数值） | 9.42477 | 弧度 | t2_resonance.validation.dphi_per_period_numeric |
| Δφ 每周期（理论 2πc） | 9.42478 | 弧度 | t2_resonance.validation.dphi_per_period_theory |
| 有理 c 的最大二维占据率 | 0.465278 | 1 | t2_resonance.dichotomy.rational_max_fill |
| 无理 c 的最小二维占据率 | 0.971065 | 1 | t2_resonance.dichotomy.irrational_min_fill |
| 有理 c 的最大径向离散度 | 0.241839 | 1 | t2_resonance.dichotomy.rational_max_spread |
| 无理 c 的最小径向离散度 | 0.220393 | 1 | t2_resonance.dichotomy.irrational_min_spread |
| c=3/2 的方位角 KS 距离（边缘分布不可判） | 0.0162671 | 1 | t2_resonance.dichotomy.rows.1.D_max |
| c=7/5 的二维占据率 | 0.465278 | 1 | t2_resonance.dichotomy.rows.5.fill |
| c=π 的二维占据率 | 0.971065 | 1 | t2_resonance.dichotomy.rows.9.fill |
| 单条闭合轨道集合的 KS 距离 | 0.134892 | 1 | t2_resonance.ensemble.ks_trend.0.D |
| 16 条等权集合的 KS 距离 | 0.0174108 | 1 | t2_resonance.ensemble.ks_ensemble.D |
| c=3/2 长积分闭合间隙（3000 周期） | 0.790951 | 1 | t2_resonance.long_integration.3/2.closure_gap |
| c=golden 长积分闭合间隙 | 0.0546565 | 1 | t2_resonance.long_integration.golden.closure_gap |
| c=3/2 长积分 KS D（n=1e5） | 0.000723269 | 1 | t2_resonance.long_integration.3/2.ks.2.D |
| c=3/2 长积分径向宽度 | 0.703801 | 1 | t2_resonance.long_integration.3/2.radial_width |
| 环径向宽度（ε=0） | 0.711482 | 1 | t2_resonance.quasiperiodic_boundedness.width_unperturbed |
| 环径向宽度（ε=3e-2） | 0.993807 | 1 | t2_resonance.quasiperiodic_boundedness.rows.6.width |
| 宽度随 ε 的拟合幂 | 0.5684 | 1 | t2_resonance.quasiperiodic_boundedness.fit_power |
| 该幂的 se | 0.1343 | 1 | t2_resonance.quasiperiodic_boundedness.fit_power_se |
| ε≤1e-3 小振幅段拟合幂 | 1.06 | 1 | t2_resonance.quasiperiodic_boundedness.fit_power_small_eps |
| L 相对振荡幅度（ε=3e-2） | 0.123256 | 1 | t2_resonance.quasiperiodic_boundedness.rows.6.L_max_rel |
| 摆动幅实测 / 分界线理论 2√(ε/β) | 0.999688 | 1 | t2_resonance.resonance_bound.pendulum.0.ratio |
| 力心平移 δ=0 时的 L 漂移 | 2.17382e-13 | 1 | t2_resonance.sole_centrism.drift_at_zero |
| L 漂移随 δ 的幂 | 1.052 | 1 | t2_resonance.sole_centrism.drift_power |
| 该幂的 se | 0.01908 | 1 | t2_resonance.sole_centrism.drift_power_se |
| 力心平移 δ=0.3 时的 L 漂移 | 1.66073 | 1 | t2_resonance.sole_centrism.torque_test.6.L_drift_rel |

## T3 轨迹与开普勒三定律

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 轨道偏心率 c=3/2 情形 | 0.555556 | 1 | t3_kepler.trajectory.e |
| 积分步长 dt | 0.000647711 | 时间单位 | t3_kepler.trajectory.dt |
| 近心距 | 0.285719 | AU | t3_kepler.trajectory.r_min |
| Δφ 每径向周期 | 9.42465 | 弧度 | t3_kepler.trajectory.dphi_per_period |
| 拱线每周期进动 | 179.997 | 度 | t3_kepler.law1.apsidal_drift_deg_per_period |
| Δφ−2π 每周期 | 179.993 | 度 | t3_kepler.law1.dphi_minus_2pi_deg |
| 8 周期后的闭合间隙 | 0.00102355 | 1 | t3_kepler.law1.closure_gap |
| 吻切 a 的 5% 分位 | -2.61163 | AU | t3_kepler.law1.a_osc_p05_p50_p95.0 |
| 吻切 a 的中位数 | 1.04157 | AU | t3_kepler.law1.a_osc_p05_p50_p95.1 |
| 吻切 a 的 95% 分位 | 3.81885 | AU | t3_kepler.law1.a_osc_p05_p50_p95.2 |
| dA/dt 最大相对偏差（中心力） | 1.05249e-13 | 1 | t3_kepler.law2.dAdt_max_rel |
| dA/dt 最大相对偏差（四极 ε=1e-2） | 0.0332248 | 1 | t3_kepler.law2.quadrupole_eps_1e-2.dAdt_max_rel |
| dA/dt 平均相对偏差（四极 ε=1e-2） | 0.0119489 | 1 | t3_kepler.law2.quadrupole_eps_1e-2.dAdt_mean_rel |
| T²∝a^k 的 k（纯开普勒） | 3.0 | 1 | t3_kepler.law3.kepler.exponent_T2_a3 |
| T²∝a^k 的 k（γ 模型，c=3/2） | 3.0 | 1 | t3_kepler.law3.gamma_model.exponent_T2_a3 |
| T²∝a^k 的 k（四极 ε=3e-2） | 2.90561 | 1 | t3_kepler.law3.quadrupole.exponent_T2_a3 |
| 四极拟合斜率 log T–log a | 1.4528 | 1 | t3_kepler.law3.quadrupole.slope |
| 四极拟合斜率 se | 0.02213 | 1 | t3_kepler.law3.quadrupole.se |
| T²∝a^k 的 k 的 95% CI 下界（四极） | 2.8171 | 1 | t3_kepler.law3.quadrupole.ci95_T2_a3.0 |
| T²∝a^k 的 k 的 95% CI 上界（四极） | 2.9941 | 1 | t3_kepler.law3.quadrupole.ci95_T2_a3.1 |
| 水星进动（1PN） | 42.98 | 角秒/世纪 | t3_kepler.mercury.dphi_arcsec_per_century |
| 水星进动每圈 | 0.10352 | 角秒/圈 | t3_kepler.mercury.dphi_arcsec_per_orbit |
| 水星世纪圈数 | 415.2 | 圈/世纪 | t3_kepler.mercury.orbits_per_century |
| 水星进动（观测异常） | 43.1 | 角秒/世纪 | t3_kepler.mercury.observed_anomalous_arcsec_per_century |
| 开普勒模型给的水星进动 | 0.0 | 角秒/世纪 | t3_kepler.mercury.kepler_prediction |

## 反例与三成因（counterexamples.json）

题面 T2-c 的结论只在条件下成立。这一节是三条反例的数值，以及 T1/T3 的补强数字。

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 阻力：L 衰减率（拟合） | -0.01 | 1/时间 | counterexamples.drag.L_decay_rate_fit |
| 阻力：L 衰减率（解析 -k） | -0.01 | 1/时间 | counterexamples.drag.L_decay_rate_theory |
| 阻力：a 衰减率（拟合） | -0.0200036 | 1/时间 | counterexamples.drag.a_decay_rate_fit |
| 阻力：a 衰减率（解析 -2k） | -0.02 | 1/时间 | counterexamples.drag.a_decay_rate_theory |
| 阻力：t=149.787 时 a/a0 | 0.0500195 | 1 | counterexamples.drag.a_over_a0_at_t_end |
| 螺旋：前后半段径向 KS | 0.991247 | 1 | counterexamples.drag.ks_r_spiral_first_vs_second_half |
| 无耗散对照：前后半段径向 KS | 0.00015 | 1 | counterexamples.drag.ks_r_rosette_control |
| 螺旋：前后半段方位 KS（只看方位会误判成环） | 0.00993018 | 1 | counterexamples.drag.ks_phi_first_vs_second_half |
| a 缩小 10 倍所需时间 | 115.129 | 时间单位 | counterexamples.drag.a_shrink_10x_time |
| a 缩小 10 倍所需圈数 | 18.3234 | 圈 | counterexamples.drag.a_shrink_10x_orbits |
| a 半衰期 | 34.6574 | 时间单位 | counterexamples.drag.a_half_life_time |
| c=3/2 方位谱主导阶 l | 2 | 1 | counterexamples.harmonics.spectrum.0.A_dominant_l |
| c=3/2 方位谱 l=2 幅值 | 0.195518 | 1 | counterexamples.harmonics.spectrum.0.A_l.1 |
| c=5/3 方位谱 l=3 幅值 | 0.0606123 | 1 | counterexamples.harmonics.spectrum.1.A_l.2 |
| c=7/5 方位谱 l=5 幅值 | 0.00169285 | 1 | counterexamples.harmonics.spectrum.2.A_l.4 |
| c=golden 最大谐波幅值 | 0.00313832 | 1 | counterexamples.harmonics.spectrum.4.A_l.4 |
| 观测窗 τ/T=0.01 的 l=1 幅值 | 0.0325541 | 1 | counterexamples.harmonics.time_window.0.A1 |
| 观测窗 τ/T=0.01 的 l=2 幅值 | 0.0456254 | 1 | counterexamples.harmonics.time_window.0.A2 |
| 观测窗 τ/T=0.01 折算的虚假环心偏移 | 0.0201835 | AU | counterexamples.harmonics.time_window.0.equiv_center_offset_AU |
| 观测窗 τ/T=0.3 的 l=1 幅值 | 0.00117805 | 1 | counterexamples.harmonics.time_window.3.A1 |
| 观测窗 τ/T=0.3 折算的虚假环心偏移 | 0.000730391 | AU | counterexamples.harmonics.time_window.3.equiv_center_offset_AU |
| 观测窗 τ/T=1 的 l=1 幅值 | 0.000333391 | 1 | counterexamples.harmonics.time_window.4.A1 |
| 旋转平均后 l=1 幅值（W=6.283 rad） | 4.16739e-05 | 1 | counterexamples.harmonics.partial_mixing.4.A1 |
| i=0° 透视曲线重心偏移 | 0.250469 | AU | counterexamples.t1_views.rows.0.persp_centroid_offset |
| i=0° 正交曲线重心偏移 | 0.224601 | AU | counterexamples.t1_views.rows.0.ortho_centroid_offset |
| i=30° 透视曲线重心偏移 | 0.356879 | AU | counterexamples.t1_views.rows.1.persp_centroid_offset |
| i=30° 正交曲线重心偏移 | 0.297119 | AU | counterexamples.t1_views.rows.1.ortho_centroid_offset |
| i=60° 透视曲线重心偏移 | 0.460919 | AU | counterexamples.t1_views.rows.2.persp_centroid_offset |
| i=90° 透视与正交曲线重心偏移（二者重合） | 0.449202 | AU | counterexamples.t1_views.rows.3.persp_centroid_offset |
| 耗散：每圈半长轴相对漂移（k=0.01） | -0.125664 | 1/圈 | counterexamples.t3_dissipation.a_drift_rel_per_orbit |
| 耗散：半长轴半衰期 | 5.51589 | 圈 | counterexamples.t3_dissipation.half_life_orbits |

三条反例各自破坏的命题：E1（阻力）破坏环的平稳性，径向 KS 0.991247 vs 对照 0.00015；
E2（只锁径向）破坏各向同性，方位谱锁在分母阶 q 上；E3（混合同量级）破坏单中心可辨识，
τ/T=0.01 时虚假环心偏移 0.0201835 AU = R̄ 的 3.3%。

## 运行开销（不进对账表：每次运行浮动 ±5%）

`code/run_all.py` 一次跑完三段：T1 约 24 s（1440 点 × 10 个 d_E × 倾角扫描 37 组 + 两次最小二乘族搜索）、
T2 约 9 s（两个 3000 周期 / 300000 步辛积分 + 7 组 600 周期摄动扫描）、T3 约 2.4 s（40000 步轨迹 + 三组拟合）。
合计约 36 s，预算 300 s，`data/run_all.json:within_budget` = true。

图（`figures/`，每张 pdf + png，`setup_matplotlib()` 统一 rcParams）：
fig1_three_views 三视图对比、fig2_parallax_scaling 视差形变与阶数标定、fig3_observables_vs_i 倾角扫描、
fig4_mars_geocentric 火星地心视轨道、fig5_identifiability 可辨识性解族、fig6_rosette 玫瑰线与环、
fig7_uniformity 长积分角分布与 KS、fig8_resonance_width 共振摆与径向宽度标度、fig9_kepler_laws
开普勒三定律三项检验、fig10_mercury_precession 水星进动。
