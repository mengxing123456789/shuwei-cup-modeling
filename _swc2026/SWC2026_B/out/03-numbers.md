# 03 关键数字与 JSON 键

所有数字由 `code/` 重跑得到，键可追溯。键的写法：`文件名.路径`，列表下标从 0 起（例如 `p2.p2_2.rows[0].gap_s` 是 `data/p2.json` 里 p2_2.rows 数组第 1 行的 gap_s 字段）。分数型键在表里按百分数写，键内存的是 0–1 小数；比值型键在表里按百分数写，键内存的是小数比值。

## P1 可观测域与最优观测站

| 量 | 值 | 单位 | JSON 键 |
|---|---|---|---|
| T1 可观测面积（1 m 栅格） | 57.90 | % | `p1.observability.T1.frac_of_field_3d` |
| T1 可观测面积（0.5 m 栅格） | 56.08 | % | `p1.observability.T1.grid05_frac` |
| T1 可观测面积（0.25 m 栅格） | 56.149 | % | `p1_area_grid.converged.vehicle_025` |
| T1 可观测面积（0.125 m 栅格） | 56.079 | % | `p1_area_grid.converged.vehicle_0125` |
| 0.25 m 与 0.125 m 面积差 | 0.07 | 百分点 | `p1_area_grid.converged.delta_pp_025_vs_0125` |
| 面积主报值（0.25 m 净距口径） | 56.15 | % | `p1_area_grid.converged.recommend_frac` ×100 |
| 1 m 栅格与 0.125 m 收敛值之差 | 1.82 | 百分点 | `p1_area_grid.anomaly_1m.gap_pp_vs_converged` |
| 1 m 严格判据（>1.5 m）面积 | 53.89 | % | `p1_area_grid.anomaly_1m.strict_1m_frac` |
| 1 m 切点线虚增 | 4.01 | 百分点 | `p1_area_grid.anomaly_1m.over_inclusion_pp` |
| 1 m 粗网格少算 | 2.19 | 百分点 | `p1_area_grid.anomaly_1m.coarse_deficit_pp` |
| 相机点口径面积（0.125 m） | 61.984 | % | `p1_area_grid.converged.camera_0125` |
| 1.5 m 净距的覆盖代价 | 5.90 | 百分点 | `p1_area_grid.converged.clearance_cost_pp` |
| Q=1/r 上确界 | 0.13189027 | m⁻¹ | `p1.p1_T1.q_sup` |
| 俯仰临界半径 r_min（T1） | 7.58206 | m | `p1.p1_T1.r_min_analytic` |
| 连续最优站 x | 83.5283 | m | `p1.p1_T1.continuous.x` |
| 连续最优站 y | 62.5 | m | `p1.p1_T1.continuous.y` |
| 最优站水平距离 r | 7.58209 | m | `p1.p1_T1.continuous.r` |
| 最优站仰角 | 79.999961 | ° | `p1.p1_T1.continuous.elev_deg` |
| r=r_min 弧上同值点数 | 5677 | 个 | `p1.p1_T1.tie.n_tied_continuous` |
| tie-break 站 x | 91.1571 | m | `p1.p1_T1.tie.chosen.x` |
| tie-break 站 y | 66.1233 | m | `p1.p1_T1.tie.chosen.y` |
| tie-break 站到达时间（V4） | 1.2242 | s | `p1.p1_T1.tie.chosen.travel_s` |
| 弧上到达时间极差 | 30.9152 | s | `p1.p1_T1.tie.tie_travel_spread_s` |
| T1 俯仰可行格数 | 8469 | 个 | `p1.observability.T1.feasible_cells` |
| T2 平面阴影可观测格数 | 0 | 个 | `p1.observability.T2.obs_planar_cells` |
| T2 三维可观测面积 | 66.04 | % | `p1.observability.T2.frac_of_field_3d` |
| T3 三维可观测面积 | 56.67 | % | `p1.observability.T3.frac_of_field_3d` |
| 三目标求和版上界 | 0.41075263 | m⁻¹ | `p1.ext_Q3_targets.bound_sum_1_over_rmin` |

## P2(1) 双站定位精度

| 量 | 值 | 单位 | JSON 键 |
|---|---|---|---|
| DRMS 理论下界 | 0.143623 | m | `p2.p2_1.drms_lower_bound` |
| 可达 DRMS（最优站对） | 0.143623 | m | `p2.p2_1.attained.drms` |
| 两站水平距离 r1 | 5.8188 | m | `p2.p2_1.attained.r1` |
| 两站水平距离 r2 | 5.8188 | m | `p2.p2_1.attained.r2` |
| 交会角 γ | 90.000 | ° | `p2.p2_1.attained.gamma_deg` |
| 基线长度 | 8.229 | m | `p2.p2_1.attained.baseline` |
| V3 行程 | 4.4148 | s | `p2.p2_1.attained.travel1_s` |
| V5 行程 | 13.0719 | s | `p2.p2_1.attained.travel2_s` |
| V3 云台转向 | 2.6667 | s | `p2.p2_1.attained.slew1_s` |
| V5 云台转向 | 4.0113 | s | `p2.p2_1.attained.slew2_s` |
| 下界可达站对总数 | 45540 | 对 | `p2.p2_1.n_attaining_pairs` |
| 蒙特卡洛 RMS | 0.143533 | m | `p2.p2_1.mc_validation.mc_rms` |
| 蒙特卡洛 p95 | 0.248254 | m | `p2.p2_1.mc_validation.mc_p95` |
| 蒙特卡洛 p99 | 0.308513 | m | `p2.p2_1.mc_validation.mc_p99` |
| 闭式与 MC 相对误差 | 0.063 | % | `p2.p2_1.mc_validation.rel_err` |
| 留 0.5° 仰角余量的 DRMS | 0.150964 | m | `p2.p2_1.attained.robust.drms` |
| 余量后的等效半径 r_eff | 6.1162 | m | `p2.p2_1.attained.robust.r_eff` |
| 余量带来的精度代价 | 5.111 | % | `p2.p2_1.attained.robust.cost_pct` |
| 视线余隙 ≥1 m 档的 DRMS | 0.143727 | m | `p2.p2_1.clearance_tier.drms` |
| 该档比下界的代价 | 0.0725 | % | `p2.p2_1.clearance_tier.penalty_vs_lb_pct` |
| 该档 s2 的楼顶竖直余隙 | 2.7368 | m | `p2.p2_1.clearance_tier.clearance2_m` |

## P2(2) 三警报调度

| 量 | 值 | 单位 | JSON 键 |
|---|---|---|---|
| 最优 makespan（0.25 m 细化） | 10.8583 | s | `p2.p2_2.unconstrained.makespan` |
| 3 m 栅格 makespan | 11.2141 | s | `p2.p2_2.grid_refine.inf.makespan_3m` |
| 细化下降量 | 0.3558 | s | `p2.p2_2.grid_refine.inf.delta_s` |
| T1 观测开始 | 1.5320 | s | `p2.p2_2.unconstrained.starts.T1` |
| T2 观测开始 | 10.8583 | s | `p2.p2_2.unconstrained.starts.T2` |
| T3 观测开始 | 5.7776 | s | `p2.p2_2.unconstrained.starts.T3` |
| 最近分配启发式 makespan | 11.2541 | s | `p2.p2_2.rows[0].greedy_makespan` |
| 最优与启发式之差 | 0.3958 | s | `p2.p2_2.rows[0].gap_s` |
| cap=40 m 档 makespan | 17.1306 | s | `p2.p2_2.rows[1].exact_makespan` |
| cap=30 m 档 makespan | 24.3009 | s | `p2.p2_2.rows[2].exact_makespan` |
| cap=20 m 档 makespan | 31.3183 | s | `p2.p2_2.rows[3].exact_makespan` |
| cap=15 m 档 makespan | 33.3529 | s | `p2.p2_2.rows[4].exact_makespan` |
| cap=10 m 档 makespan | 38.9285 | s | `p2.p2_2.rows[5].exact_makespan` |
| cap=10 m 档 T3 的 DRMS（γ=0 退化） | ∞ | m | `p2.p2_2.rows[5].drms_exact.T3.drms` |

## P3 误差传播

| 量 | 值 | 单位 | JSON 键 |
|---|---|---|---|
| 双侧 95% 分位数 z₀.₉₇₅ | 1.95996398 | — | `p3.p3.z975` |
| 允许总标准差 | 2.551067 | ° | `p3.p3.budget_deg` |
| 定位项允许标准差 | 2.346901 | ° | `p3.p3.sigma_loc_allow_deg` |
| 允许的定位距离标准差 | 1.638446 | m | `p3.p3.sigma_s_allow_m` |
| 最大允许行驶距离 s_max（闭式） | 66.922299 | m | `p3.p3.s_max` |
| s_max（二分法） | 66.922299 | m | `p3.p3.s_max_bisect` |
| s_max 处 MC 概率 | 0.94954 | — | `p3.p3.mc_at_s_max` |
| 0.98·s_max 处 MC 概率 | 0.9532 | — | `p3.p3.mc_at_098_s_max` |
| s=80 m 处 MC 概率 | 0.91437 | — | `p3.p3.mc_at_80` |
| 定位项与云台项相等点 | 19.906585 | m | `p3.p3.s_cross_loc_vs_gimbal` |
| 80 m 约束的 b 上限 | 0.020481 | m/m（无量纲） | `p3.p3.ab_constraint.b_max` |
| a=0.3 时 b 的允许上限 | 0.016731 | m/m（无量纲） | `p3.p3.ab_constraint.b_at_a_eq_03` |
| 名义 b=0.02 的缺口 | 0.003269 | m/m（无量纲） | `p3.p3.ab_constraint.shortfall_b` |
| s=0 时定位方差份额 | 15.5874 | % | `p3.p3.contributions[0].share_loc` |
| s=0 时零偏方差份额 | 54.024 | % | `p3.p3.contributions[0].share_zero` |
| s=0 时控制方差份额 | 30.3885 | % | `p3.p3.contributions[0].share_ctrl` |
| s=66.92 时定位方差份额 | 84.6342 | % | `p3.p3.contributions[4].share_loc` |
| s=80 时总标准差 | 2.899454 | ° | `p3.p3.contributions[5].sigma_total_deg` |

## P4 扰动重调度

扰动：t=5 注入新警报 T4（θ~U[0,360)、R~U[30,50]、H=50，r_min=8.4637 m）、一台车故障（均匀）、通信中断 [5,t_rec]（t_rec~U(5,30]）。基线 = P2(2) 的 10.8583 s 方案，T1 在 t=5 已锁定。N=4，η=k/4，k<4 时 t_last 记 60 s 哨兵。

| 量 | 值 | 单位 | JSON 键 |
|---|---|---|---|
| 请求抽样数 | 500 | 次 | `p4.p4.n_mc` 与 `p4.p4.rows` 长度→实际 |
| 有效场景数 | 492 | 次 | `p4.p4.n_mc` |
| 因无可行站对跳过 | 8 | 次 | `p4.p4.n_skip_new_alert` |
| T4 的俯仰下界行程 | 8.4637 | m | `p4.p4.r_min_new` |
| T4 双站 DRMS | 0.208907 | m | `p4.p4.rows[0].drms_new` |
| keep_strict mean η | 0.5483 | — | `p4.p4.keep_strict.mean_eta` |
| keep_strict mean t_last | 60.000 | s | `p4.p4.keep_strict.mean_tlast` |
| keep_strict 已服务最晚开始 | 8.814 | s | `p4.p4.summary.served_last_start.keep_strict` |
| keep mean η | 0.7983 | — | `p4.p4.keep.mean_eta` |
| keep mean t_last | 55.098 | s | `p4.p4.keep.mean_tlast` |
| keep 已服务最晚开始 | 34.502 | s | `p4.p4.summary.served_last_start.keep` |
| resched 已服务最晚开始 | 41.107 | s | `p4.p4.summary.served_last_start.resched` |
| resched mean η | 1.0000 | — | `p4.p4.resched.mean_eta` |
| resched mean t_last | 41.107 | s | `p4.p4.resched.mean_tlast` |
| resched t_last 中位数 | 41.334 | s | `p4.p4.resched.tlast_p50` |
| resched t_last p90 | 52.137 | s | `p4.p4.resched.tlast_p90` |
| resched t_last 最大 | 57.072 | s | `p4.p4.summary.resched_tlast_max` |
| 重调度胜率（η,t_last 词典序） | 0.8069 | — | `p4.p4.win_resched` |
| 保持胜率 | 0.0264 | — | `p4.p4.win_keep` |
| 并列率 | 0.1667 | — | `p4.p4.tie` |
| η 平均提升 | 0.2017 | — | `p4.p4.eta_gain_mean` |
| t_last 平均缩短 | 13.991 | s | `p4.p4.tlast_gain_mean` |
| keep_strict η=0.50 的场景数 | 397 | 个 | `p4.p4.keep_strict.eta_hist` |
| keep_strict η=0.75 的场景数 | 95 | 个 | `p4.p4.keep_strict.eta_hist` |
| V1 故障时 keep mean η | 0.75 | — | `p4.p4.by_fail[0].keep_eta` |
| V5 故障时 keep mean η | 1.00 | — | `p4.p4.by_fail[4].keep_eta` |
| 窗口 30 s 时 keep η | 0.6311 | — | `p4.p4.by_horizon[0].keep_eta` |
| 窗口 30 s 时 resched η | 0.6225 | — | `p4.p4.by_horizon[0].resched_eta` |
| 窗口 45 s 时 resched η | 0.8847 | — | `p4.p4.by_horizon[1].resched_eta` |
| 窗口 60 s 时 resched η | 1.0000 | — | `p4.p4.by_horizon[2].resched_eta` |
| t_rec∈[5,8) 的 resched 胜率 | 0.8226 | — | `p4.p4.by_t_rec_lex[0].win_resched` |
| t_rec∈[5,8) 的 keep 胜率 | 0.1452 | — | `p4.p4.by_t_rec_lex[0].win_keep` |
| t_rec∈[15,30) 的 keep 胜率 | 0.0000 | — | `p4.p4.by_t_rec_lex[3].win_keep` |
| 阈值判据原文 | 见 `threshold_rule` | — | `p4.p4.threshold_rule` |

## 敏感性（OAT + 联合抽样）

| 量 | 值 | 单位 | JSON 键 |
|---|---|---|---|
| σ 的 DRMS log-log 斜率 | 0.9881 | — | `sens.sens.joint.log_slope_drms_T2_vs_sigma` |
| σ=0.5° 时 T2 DRMS 下界 | 0.071812 | m | `sens.sens.oat_sigma[0].drms_lb_T2` |
| σ=1.0° 时 T2 DRMS 下界 | 0.143623 | m | `sens.sens.oat_sigma[2].drms_lb_T2` |
| σ=2.0° 时 T2 DRMS 下界 | 0.287247 | m | `sens.sens.oat_sigma[4].drms_lb_T2` |
| σ 从 1° 到 2° 的变化率 | +100.0 | % | `sens.sens.oat_sigma[4].d_pct` |
| σ=1° 时 P4 新警报 DRMS | 0.208907 | m | `sens.sens.oat_sigma[2].p4_drms` |
| v=2 m/s 时 P2(2) makespan | 10.8582 | s | `sens.sens.oat_speed[0].makespan` |
| v=5 m/s 时 P2(2) makespan | 10.8582 | s | `sens.sens.oat_speed[5].makespan` |
| v 从 3 到 5 m/s 的 makespan 变化率 | 0.0 | % | `sens.sens.oat_speed[5].d_pct` |
| v=2 m/s 时 P2(1) 近站行程 | 6.6222 | s | `sens.sens.p2_1_speed_table[0].travel_s1` |
| v=2 m/s 时 P2(1) 远站行程 | 19.6078 | s | `sens.sens.p2_1_speed_table[0].travel_s2` |
| v=5 m/s 时 P2(1) 近站行程 | 2.6489 | s | `sens.sens.p2_1_speed_table[2].travel_s1` |
| v=5 m/s 时 P2(1) 远站行程 | 7.8431 | s | `sens.sens.p2_1_speed_table[2].travel_s2` |
| 俯仰上限 75° 时 T1 可观测占比 | 56.07 | % | `sens.sens.oat_elev[0].area_T1` |
| 俯仰上限 85° 时 T1 可观测占比 | 59.09 | % | `sens.sens.oat_elev[4].area_T1` |
| 俯仰上限 75° 时 T2 下界 | 8.842323 | m | `sens.sens.oat_elev[0].r_min_T2` |
| 俯仰上限 85° 时 T2 下界 | 2.887126 | m | `sens.sens.oat_elev[4].r_min_T2` |
| 俯仰上限 85° 时 T1 面积增量 | +1.19 | 百分点 | `sens.sens.oat_elev[4].delta_area_T1_pp` |
| 联合抽样 T2 DRMS 均值 | 0.18219 | m | `sens.sens.joint.out.drms_lb_T2.mean` |
| 联合抽样 T2 DRMS 标准差 | 0.08461 | m | `sens.sens.joint.out.drms_lb_T2.std` |
| 联合抽样 T2 DRMS p05 | 0.06777 | m | `sens.sens.joint.out.drms_lb_T2.p05` |
| 联合抽样 T2 DRMS p95 | 0.34391 | m | `sens.sens.joint.out.drms_lb_T2.p95` |
| σ 的秩相关 | 0.7695 | — | `sens.sens.joint.out.drms_lb_T2.rho_sigma` |
| 俯仰上限的秩相关 | −0.5896 | — | `sens.sens.joint.out.drms_lb_T2.rho_elev` |
| 车速的秩相关 | 0.0696 | — | `sens.sens.joint.out.drms_lb_T2.rho_v` |
| 联合抽样 makespan 标准差 | 0.0 | s | `sens.sens.joint.out.makespan.std` |

VERDICT: PASS
