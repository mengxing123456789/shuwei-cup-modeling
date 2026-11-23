# 00 题目要求拆解（problem.txt 逐句）

> 这份拆解只做一件事：把 problem.txt 里「要求你做什么」逐句抄出并标行号，再把已知、未知、待假设分成三张表。题面背景故事不复述。
> 引用格式：`L127–136` 表示 problem.txt 第 127–136 行。

## 1. 题面各问的原文要求

### P1 可观测域与最优观测站（L127–136）

1. "For target T1 shown in Figure 1, determine the vehicle-observable region and illustrate your result with a plot."（L128–129）
2. "A station is observable only if all three constraints are satisfied concurrently: vehicle geometric constraints (the vehicle must remain within the field boundary and may not intrude into buildings), line-of-sight occlusion constraints, and feasible gimbal elevation bounds."（L129–131）
3. "Adopt Q=1/r as the metric for observation quality, where r is the horizontal distance from the camera to the target."（L132–133）
4. "Locate the optimal observation station under this metric and report its associated horizontal distance and line-of-sight elevation angle."（L133–134）
5. "Explicitly state the mathematical optimization criterion for 'optimal'."（L134–135）
6. "If multiple stations yield the identical optimal value, specify reasonable tie-breaking selection rules."（L135–136）

### P2(1) 双站定位精度模型与 T2 最优站对（L138–154）

1. "Two observation vehicles synchronously observe the same target from different azimuths, and the target's horizontal position is estimated by intersecting the two bearing lines."（L140–142）
2. "Assume that the azimuth measurement errors of the two vehicles are independent and normally distributed as N(0, (1°)²)."（L142–144）
3. "Construct a mathematical model that relates two-station localization accuracy to geometric station parameters, including baseline length, intersection angle, and target range."（L144–145）
4. "Define an accuracy metric and justify its rationality."（L146）
5. "Subject to the constraint that the travel time from each vehicle's initial position to its assigned observation station does not exceed 30 s, select two vehicles from the five available and determine the pair of observation stations that yields the best localization accuracy for alert T2."（L147–149）
6. "Report the station coordinates, baseline length, intersection angle, vehicle travel times, and the resulting accuracy metric."（L149–151）
7. "Discuss whether the accuracy model degenerates as the intersection angle approaches 0° or 180°, or when the stations lie on the boundary of the observable region, and propose corresponding handling strategies."（L151–154）

### P2(2) 多警报下的车辆复用与路径（L155–167）

1. "Three alerts, T1, T2, and T3, are released simultaneously at time t=0. Each alert requires two vehicles for intersection-based localization, resulting in a total of six vehicle-task slots. Since only five vehicles are available, certain vehicles must be reused to serve multiple observation tasks sequentially."（L156–159）
2. "The observation station for each alert must lie within the target's observable region, and all vehicle timelines must strictly adhere to the sequential observation rules defined previously."（L159–161）
3. "The objective is to minimize the maximum observation start time among the three alerts."（L162）
4. "Design a vehicle assignment and routing scheme to achieve this objective."（L163）
5. "Output the complete timeline for each vehicle, marking key events: departure, arrival at station, gimbal slew, observation start and end, gimbal reset, and subsequent departure."（L163–165）
6. "Additionally, independently define a 'nearest-assignment heuristic,' solve for a baseline scheme under identical constraints, and compare it with the optimized scheme to analyze the sources of the differences."（L165–167）

### P3 定位与指向误差对水平方位精度的影响（L168–189）

1. "Let the estimated vehicle position be P̂ and the true position be P, with localization error (δx,δy)=P̂−P. The gimbal computes the bearing angle based on the estimated position for pointing. Define Δψ as the deviation between the commanded bearing angle and the true bearing angle, wrapped into the interval [−180°,180°)."（L170–174）
2. "After the vehicle has traveled a cumulative distance of s meters, its horizontal coordinate errors are independent zero-mean normal random variables, with standard deviation 0.3+0.02s m."（L175–176）
3. "The gimbal zero-offset error and gimbal control error are also independent zero-mean normal variables, with standard deviations 0.8° and 0.6°, respectively, and are independent of the vehicle localization error."（L177–179）
4. "The target position is assumed to be perfectly known, and the horizontal distance from the vehicle to the target is fixed at 40 m."（L179–180）
5. "Construct an error propagation model for Δψ."（L181）
6. "Determine the maximum allowable travel distance such that P(|Δψ|≤5°)≥0.95."（L182–183）
7. "If the same accuracy requirement must still hold when the vehicle travels 80 m, derive constraints on the nonnegative parameters a and b in the localization standard-deviation model σ(s)=a+bs."（L183–185）
8. "Justify the applicability of any approximations or numerical methods used in the modeling, and validate the results."（L187–188）
9. "Compare the relative contributions of the three error sources to the horizontal bearing deviation, and provide practical deployment insights."（L188–189）

### P4 扰动下的重调度与方案比较（L190–218）

1. "Take the scheduling solution obtained in Problem 2(2) as the baseline. Consider the following disturbances and their combinations occurring at time t=5 s:"（L191–192）
2. "a new alert requiring two observation vehicles, with parameters θ∈[0°,360°), R∈[30,50] m, and H=50 m;"（L192–194）
3. "the random failure of exactly one out of the five vehicles, where each vehicle has an equal probability of failure. A failed vehicle withdraws from service and does not obstruct travel paths;"（L194–195）
4. "a communication outage occurs over the interval [5,t_rec], with t_rec∈(5,30], meaning the outage duration falls within [5,30] s. During the outage, vehicles continue executing their ongoing tasks; new scheduling commands are received only after communication is recovered."（L195–198）
5. "Develop a rescheduling model for these disturbances and compare its performance against the policy of retaining the original schedule. Present results for scenarios with single disturbances and with combined disturbances."（L199–201）
6. "Important rules: any alert whose observation has already started before the disturbance is treated as completed and cannot be rescheduled; vehicles that have been dispatched but have not yet begun observation may be reassigned."（L201–203）
7. "Neither scheme has advance knowledge of disturbances when the schedule is made at t=0; rescheduling uses real-time information and is triggered only after a disturbance actually occurs."（L203–205）
8. "For the uncertainty in the parameters (θ, R, H) of the new alert within the given ranges, design representative scenarios or a scenario set, and justify the scenario design and evaluation criteria."（L205–207）
9. "Adopt an evaluation window t∈[0,60] s. Let N denote the total number of alerts to be observed within this window, including newly added alerts, and let k denote the count of alerts that successfully initiate observation. An alert is counted as successful only when both assigned vehicles arrive at their stations and finish gimbal pointing."（L208–211）
10. "Define the completion ratio η=k/N and the latest observation start time t_last. If any pending alert cannot start observation before the end of the evaluation window, set t_last=60 s. Schemes are prioritized first by a higher value of η; for schemes with identical η, the one with smaller t_last is preferred."（L211–216）
11. "Report (η,t_last), rescheduling policies, and vehicle timelines for each scenario. Analyze scenarios where rescheduling yields benefits and scenarios where rescheduling performs poorly, and explain the underlying causes."（L216–218）

## 2. 已知条件

| 类别 | 条件 | 来源 |
|---|---|---|
| 场地 | 100 m×100 m 正方形，原点在西南角，x 轴向东、y 轴向北 | L33–38 |
| 建筑 | B1 [22,34]×[16,26] h=20；B2 [63,79]×[59,71] h=28；B3 [10,24]×[65,76] h=12；B4 [72,86]×[22,34] h=24；B5 [41,51]×[38,46] h=32（单位 m） | L39–63（表 1） |
| 车辆 | V1(15,14)、V2(88,10)、V3(14,86)、V4(88,68)、V5(50,93)；等效半径 1.5 m；速度 3 m/s | L88–90 |
| 相机 | 离地 2 m；俯仰角可行域 [−10°,80°]；转速 30°/s（双轴同时转，取较长时间） | L93–99 |
| 观测 | 两车到站并完成指向后同步观测 5 s；观测结束按转速规则回正到正东水平 | L104–108、L111–122 |
| 目标 | T1(30°,40,45)、T2(150°,45,35)、T3(285°,38,55)，即 (x,y)=(50+R cosθ, 50+R sinθ)、z=H | L64–73 |
| 遮挡 | 视线与建筑棱、面、顶点相切或接触都算遮挡 | L102–103 |
| 误差 | 定位 σ(s)=0.3+0.02s m（两坐标独立、零均值）；云台零偏 0.8°；控制误差 0.6°；目标位置精确；水平距离固定 40 m | L175–180 |
| 通信 | t_rec∈(5,30]，中断期间车辆继续执行既定动作 | L195–198 |
| 评价 | 窗口 [0,60] s；η=k/N；t_last 规则；η 优先、t_last 次之 | L208–216 |

## 3. 未知 / 待求

| 问 | 待求量 | 输出形式 |
|---|---|---|
| P1 | T1 的车载可观测区域；Q=1/r 下的最优站、r、仰角；并列时的 tie-break 规则 | 区域图 + 最优站坐标 + 上确界 |
| P2(1) | 双站定位精度与基线、交会角、距离的解析关系；精度指标；T2 的最优站对与两台车；退化分析 | 公式 + 站对坐标 + DRMS + 基线 + γ + 行程 |
| P2(2) | 三警报六槽位的车辆分配与路径；逐车完整时间线；最近分配启发式对照 | 分配表 + 时间线 + makespan 对比 |
| P3 | Δψ 的误差传播模型；P(|Δψ|≤5°)≥0.95 的最大行驶距离；80 m 时 (a,b) 的约束；三误差源贡献 | 解析式 + s_max + 可行域 + 贡献份额 |
| P4 | 扰动下的重调度模型；三策略（保持原计划 / 保持+补派 / 重调度）对比；500 次蒙特卡洛；逐场景 (η,t_last)；重调度有益/更差的阈值判据 | 492 次有效抽样的分布 + 窗口与 t_rec 分段表 + 判据 |

## 4. 需自行假设（及正当理由）

| # | 假设 | 正当理由 |
|---|---|---|
| A1 | 车体按半径 1.5 m 的圆处理，车心到建筑外墙与场地边界均 ≥1.5 m 视为几何可行 | 题面给出"等效半径 1.5 m"（L88–90），用圆盘近似车体是二维路径规划的标准做法；外扩 1.5 m 后可用可见图求绕障最短路 |
| A2 | 视线与建筑相切/接触算遮挡（用闭 AABB 的 slab 判定，eps=1e-9 外扩） | 题面 L102–103 明确"Any tangency or contact … counts as occlusion"；该约定使面积估计偏小（见 01-model.md 方法学注记） |
| A3 | 云台"回正"指回到正东水平（pan=0°, tilt=0°），回正耗时 = max(|Δpan|,|Δtilt|)/30 | 题面 L107–108、L118–120 规定回正到 due-east horizontal，且"already … equals zero"；双轴同时转取较长时间与题面转速规则一致 |
| A4 | 车辆在站与站之间走绕障最短路（车心内缩 1.5 m、楼体外扩 1.5 m，可见图 Dijkstra），行驶中云台保持正东水平 | 题面 L112–113 规定行驶中云台正东；绕障最短路是"最短时间"的自然解释 |
| A5 | 同一台车可以串行服务两个警报（P2(2) 六槽五车） | 题面 L156–159 明说"certain vehicles must be reused … sequentially"；每次观测 5 s 后回正再走，时间线严格串行 |
| A6 | 已开始观测的警报在扰动后视为完成，不因通信中断而中断 | 题面 L201–203 明确规则；观测一旦开始就锁定 |
| A7 | P4 中新警报与 T1/T2/T3 同公式（(x,y)=(50+Rcosθ,50+Rsinθ)，z=H），也需两车观测 | 题面 L192–194 给出参数范围，且"requiring two observation vehicles" |
| A8 | 故障车"不挡路"：故障后从路网中移除，其他车路径按原绕障最短路计算 | 题面 L194–195 明确"withdraws from service and does not obstruct travel paths" |
| A9 | P4 的 N 计入窗口内所有需观测警报（含 T1/T2/T3 与新增 T4），即使某警报因故障无法完成也计入 | 题面 L208–210"total number of alerts to be observed within this window, including newly added alerts"；这样 η 才能惩罚失败 |
| A10 | P4 重调度指令在 t_rec 时刻生效（t_rec>5）；生效前车辆按原计划继续动作 | 题面 L195–198：中断期间继续执行既定动作，恢复后才收到新指令 |
| A11 | P4 四参数独立均匀抽样：θ~U[0,360)、R~U[30,50]、故障车~U{V1..V5}、t_rec~U(5,30]；若新警报在 4 台幸存车可达站里凑不出夹角足够的一对，该次抽样跳过并计入跳过率 | 题面给的是区间而非离散档位；跳过率（8/500=1.6%）本身是「新警报可能有几何无解」的量化结论 |
| A12 | 数值计算用双精度，时间精度 1e-6 s；事件驱动仿真不设固定 dt | 题面要求严格串行时间线；事件队列可避免 dt 离散误差，P4 的 (η,t_last) 对时间敏感 |

VERDICT: PASS
