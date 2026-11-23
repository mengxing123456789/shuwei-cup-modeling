# Lead 独立复核：C 题 P3 的可行性与真正的难点（不依赖 mm-c）

来源：`_lead_check_C.py`，输入 `Restocking_Tasks_and_Constraints/*`，
口径 `common_conditions.json` v `q3-20261117-v1`。结果在 `_lead_check_C.json`。

## 1. 缺失文档已被替代数据源补齐（C 的 D1 风险降低）
题面反复引用的 `Data_Documentation/` 在本下载包里**不存在**，但权威信息都在别处：
- `record_split.csv`：69 记录 + 表头，列 `episode_uuid,dataset,environment_id,scene_id,operator_id,split`（train 246 / validation 35 / test 62 个源片段级；记录级见文件）。
- `source_segment_index.csv`：**349 个源片段单元**，列含 `unit_id,dataset,sample,episode_uuid,environment_id,split,family_id,task,start_s,end_s,duration_s,description,eligible,exclusion_reason`。
  343 个 `eligible=1`；6 个被排除，`exclusion_reason` 全部是 `shorter_than_1p2_seconds`。
  → P3 的抽样池是**现成的、带资格标记的**，不需要自己推断。
- `tasks.csv`：36 个 job，列 `case_id,job_id,family_id,release_s,due_s,priority_weight,zone_id,predecessors`；
  有 3 个 job 带前驱（S2_J09←S2_J02、S2_J11←S2_J05、S3_J12←S3_J03、S3_J15←S3_J06、S3_J16←S3_J07）。
- `service_zones.csv`：Z0(0,0) Z1(1,0) Z2(0,1) Z3(1,1) Z4(2,0)，坐标是**抽象服务区坐标**不是物体位置。
- `job_families.csv`：P=Placement and replenishment、A=Arrangement and repositioning、L=Inspection and labeling。

## 2. 服务时长是重尾的 —— 这才是 P3 的真难点
源片段 `duration_s` 按 family（eligible=343）：

| family | n | mean | sd | p50 | p90 | max |
| --- | --- | --- | --- | --- | --- | --- |
| A | 145 | 4.97 | 5.66 | 3.6 | 10.0 | 51.8 |
| L | 26 | 8.96 | 8.65 | 7.0 | 13.6 | 38.0 |
| P | 172 | 7.20 | 11.30 | 4.0 | 11.0 | **125.0** |

P 家族的最长单元 **125 s**，比 S1 的整个 horizon（100 s）还长；sd 与 mean 同量级。
按 split 均值几乎无差异（train 6.34 / validation 6.43 / test 6.56）。
→ **单次抽样的方差足以决定成败**：一次倒霉抽样就能吞掉整个预算窗口。
这也是指标里为什么有 `censored`、以及为什么要求 30 个公开种子取均值。

## 3. 容量比：S1 松、S2/S3 刚好卡死
服务时长 p = α·d_f + β = 1.0·d_f + 0.5；行程 = D/speed + changeover = D/1.0 + 0.5。
用「最近邻下界」估行程，得到每 case 的总工作量下界：

| case | jobs | horizon | 服务合计 (s) | 行程下界 (s) | 总下界 (s) | 容量比 |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | 8 | 100 | 58.4 | 8.0 | 66.4 | **0.664** |
| S2 | 12 | 100 | 90.5 | 10.0 | 100.5 | **1.005** |
| S3 | 16 | 125 | 120.8 | 12.0 | 132.8 | **1.063** |

S1 有余量；S2 恰好等于 horizon；S3 超出 6%。这是出题人**故意**设计的：
在均值意义下 S2/S3 根本做不完，加上重尾就更做不完 → 必须「取舍」而不是「排程」。

## 4. 成本预算：S1 松，S2/S3 绑定 → 与完成率直接对撞
单位成本：服务固定 2.0 + reserve 0.1/s + 距离 0.2/坐标单位（wait 免费）；
观测 1.0/次（≤ max_per_job=2 次，即 prefix 0.2/0.6/1.0 s 分级释放），延迟 1.0 s。

| case | 预算 | 服务固定合计 | 估算 reserve 合计 | budget−service_fixed | 全观测成本上限 |
| --- | --- | --- | --- | --- | --- |
| S1 | 32 | 16.0 | 5.8 | 16.0 | 4.0（不绑） |
| S2 | 34 | 24.0 | 9.1 | 10.0 | 6.0（不绑） |
| S3 | 40 | 32.0 | 12.1 | 8.0 | 8.0（刚好） |

S3：全服务 16 job 的估算总成本约 46.5 > 40 → **必须主动放弃 2 个 job（或压缩 reserve）**。
而放弃 job 直接压低 `weighted_completion_rate`，与题面「成本/风险主目标时 η≥0.5」的门槛正面相撞。
→ 这个门槛是真的会绑的，不是摆设。

## 5. 三问的隐藏耦合（我认为是 C 的最高价值创新链）
`observation.semantics` 写明：观测是**分级释放已录示范的前缀**，不是新视角。而服务的时长
`p = α·d + β` 里的 `d` 正是该 job 抽样到的**源片段时长**，事前未知。
→ 于是「付 1.0 成本 + 1.0 s 延迟」换来的是 **d 的信息**：
  用 0.2/0.6/1.0 s 的前缀（30 fps 下 6/18/30 帧的 21×3 手关键点 + 头位姿）去
  **辨识这是 349 个源单元中的哪一个**（辨识成功 ⇒ d 精确已知），
  或退一步只做 d 的**分位数预测**（保守排程）。
这条链把 P1（状态表征与观测可靠性）、P2（缺失观测下的预测与再观测价值）、
P3（不确定性下的调度与成本）**串成同一条管线**，而不是三道互不相干的题。
创新点写法：`VoI（信息的价值）= Δ(η, t_last, cost) / (1 cost + 1 s delay)`，
并给出「何时不值得看前缀」的判据（当 d 的后验已经很窄、或 horizon 余量足够时）。

## 6. 顺带确认的可行入口
- 每 case 的前 3 个 job 的 release 都是 0，due−release 平均 49–62 s，最小 35 s；
  「窗口 < 8×平均服务时长」的 job 数：S1 6、S2 9、S3 8 → 截止期普遍紧。
- 最近邻访问序（下界用）显示 job 的 zone 分布是 Z1/Z2/Z3/Z4 各四分之一（S3），
  所以行程下界很小（12 s / 16 job），**距离成本不是主要矛盾，时间与信息才是**。