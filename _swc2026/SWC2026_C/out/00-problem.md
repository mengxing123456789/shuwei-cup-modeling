BYTES 15873
# 00 题目拆解：要求做什么、哪句话是硬口径

队号 SWBMCM2634892（本科组），2026 第十二届数维杯秋季赛 C 题。
原文位置用 `problem/problem.txt:行号` 标注；P3 协议另有独立附件 `C_Problem3_Requirements.txt`，按节标注。
数据说明目录 `Data_Documentation/` 在收到的附件包里**不存在**，只有 P3 的 `C_Problem3_Requirements.txt`。因此 P2 的实验口径由本文第 4 节自定并冻结；P3 以该 requirements 文件为准。

## 1 三问的原话（逐句摘，不转述）

### P1 操作状态与观测可靠性（`problem/problem.txt:27-53`）

> Read and organize all three raw datasets, checking time alignment, coordinate conventions, duplicate records and quality flags. A “record” means the operation data from one acquisition sequence; a “time interval” is a continuous portion of a record.

> Use field completeness, temporal continuity and observation quality to identify which records and intervals support model fitting, error evaluation, analysis of low-quality observations or exclusion, and explain the reasons and selection criteria.

> Develop mathematical models of changes in operational states and observation reliability, and investigate differences across tasks, environments or stages.

> Select and define your own state variables, such as hand positions, orientations or relative motion, and retain this representation in Problem 2.

> Each hand has 21 recorded 3D keypoints. A representative hand point may be a selected keypoint or the geometric center of several keypoints; specify and justify its definition. A hand state must not be directly interpreted as a product state.

> Use the training set for parameter fitting, the validation set for model selection and the test set for evaluation after freezing the model. Include at least one reproducible baseline with a simple structure and few parameters, such as a constant predictor or a simple linear model, with its form appropriate to the state definition.

> Report data retention, main parameters and their uncertainty, error or consistency checks, and failure cases. Qualified held-out records may serve as references, but are not error-free, independent physical ground truth.

### P2 缺失观测下的预测与再观测（`problem/problem.txt:55-83`）

> Study how prediction error or uncertainty grows without new observations, how long prediction can continue within justified tolerances, and when a new observation should be requested.

> Retain the state variables selected and defined in Problem 1. Develop a prediction and uncertainty-update model for missing-observation periods, analyze the effects of missing duration, operational stage and historical information, and determine request times and waiting arrangements. Update your assessment as information returns.

> You may minimize observation cost and waiting subject to error requirements, or improve predictive accuracy with given resources. Explain your objective, tolerances and tradeoffs.

> Use artificial masking and replay experiments on real records: select intervals with qualified reference states, temporarily hide selected times or channels, predict using only information available at that point, and evaluate against the held-out records.

> A missing-observation window specifies the start and end of hidden observations. Windows, observation budgets, per-request costs and return delays are experimental conditions fixed in advance and shared by all compared methods.

> Re-observation may return only times and channels that actually exist in the raw records, and returned information cannot be used before its delay has elapsed. Compare against baselines such as holding the last state, simple motion prediction or fixed-interval observation, reporting error, uncertainty and observation expenditure.

> Use natural occlusion to analyze its occurrence, duration and recovery. Do not calculate true position error for low-quality intervals without an independent reference. Explain differences between artificial masking and natural occlusion.

### P3 不确定条件下的补货调度（`problem/problem.txt:85-140`）

> For the restocking-related jobs supplied in the attachments, use raw operation records to estimate operation durations and their uncertainty.

> Within limited time and cost, determine which jobs to prioritize and in what order, their reserved service durations, paid information reviews and waiting arrangements. Evaluate completion, on-time service, cost and equipment occupancy.

> Before execution, reserve a period of equipment service time for each job. This reserved service duration is a decision, rather than a known realized duration. An overrun delays later jobs; if service finishes early, the remainder of the reservation stays occupied and becomes idle time.

> The cases contain 8, 12 and 16 jobs, with horizons H of 100, 100 and 125 seconds, cost budgets of 32, 34 and 40, and paid-review limits of 4, 6 and 8, respectively.

> Of 349 intervals, the 343 lasting at least 1.2 seconds enter common sampling; the remaining intervals stay in the source index.

> Upon release, a job provides the first 0.2 seconds of numerical data from the start of its source segment, free of charge. Each job allows at most two paid reviews: the first extends the cumulative visible prefix to 0.6 seconds and the second to 1.0 second. Each review consumes 1 scenario second and 1 cost unit; waiting does not extend the prefix.

> Unrevealed source identifiers, end times and subsequent states cannot be used in current decisions.

> If the original annotation duration is d, the scenario service duration is αd + β. The nominal mapping uses α = 1 and β = 0.5 seconds. Test sensitivity with α = 0.75 or 1.5 while β remains 0.5 seconds, and with β = 0 or 1 second while α remains 1.

> The reserved service duration b must be at least 0.2 seconds. For inter-zone distance D, movement and changeover take D + 0.5 seconds, and execution costs 2 + 0.1b + 0.2D.

> If realized scenario service takes p and starts at s, completion occurs at s + p, and the equipment becomes available again at s + max(p, b). If service crosses horizon H, terminate the trial and count that job as unfinished.

> Training, validation and test sets contain 16, 4 and 4 environments, for parameter fitting, model selection and evaluation of frozen solutions.

> For each case and mapping condition, use the same set of 30 supplied seeds to form 30 trials; all methods receive identical sampled jobs for paired comparison.

> If cost or capacity risk is the primary objective, the mean weighted on-time completion rate for each case under nominal conditions must be at least 0.50; report any failure to meet this requirement.

## 2 P3 的完整口径（原样抄，按 `C_Problem3_Requirements.txt` 节）

**任务数据（§1）。** 36 个 job，S1=8、S2=12、S3=16；各 case 独立，均从 t=0 在 Z0 出发，累计成本 0、review 0。H/B/K 见下表。一个 work unit 是原文标注区间，不是产品数；349 个区间中 343 个时长 ≥1.2 s 可采样。`start_s/end_s` 是零基，d = end_s − start_s。

| case | jobs | H (s) | B (cost) | K (reviews) |
| --- | --- | --- | --- | --- |
| S1 | 8 | 100 | 32 | 4 |
| S2 | 12 | 100 | 34 | 6 |
| S3 | 16 | 125 | 40 | 8 |

**采样（§1）。** 按 `job_id` 排序，对每个 job 在指定 split 与 family 内**有放回均匀**抽 1 个 eligible 区间；保持 `source_segment_index.csv` 行序；每个 case 重置生成器；参考序列为 `random.Random(int(seed)).choice`，按 job 顺序连续调用。种子不是策略输入。

**信息（§2）。** 释放时免费给前 0.2 源秒；两次付费 review 把累计前缀延到 0.6、1.0 源秒，各 1 cost、占设备 1 scenario 秒，受 K 与 B 限制；只有已释放且未执行的 job 可 review，已完成前驱不是 review 前提；信息在延迟结束后才可用；等待不产生新数据。前缀含时间戳、双手 21 点位置/朝向、头与左右头相机位姿、原始手部质量旗标；**不含** source id、segment 端点、总时长、语义描述、后续样本。不做插值/补洞。

**不可用信息（§2，红线）。** 不得用全量源集合、source index、**prefix matching**、种子知识、隐藏 source id 去反推未揭示的 state、endpoint 或 duration。此条在本项目里被单独记录为合规约束：`code/p3_schedule.py` 只接受 `data/prefix_features.csv` 的前缀特征，不读 `sample`/`unit_id` 做匹配。

**动作与可行性（§3）。** 单设备；执行/review/等待互斥；等待必须为正、不得跨 H、免费；可随时 stop；每 trial 至多 200 个 action；等待与 review 不改变位置。Z0=(0,0), Z1=(1,0), Z2=(0,1), Z3=(1,1), Z4=(2,0)；D 为当前 zone 到服务 zone 的欧氏距离，速度 1，单位距离 1 s；每次执行额外 0.5 s changeover，同 zone 也有。执行选 b ≥ 0.2，s = t + D + 0.5，成本 2 + 0.1b + 0.2D；接受前必须检查累计成本 ≤ B 且 s + b ≤ H，**不得用未揭示的 p 做这个检查**；接受即扣费、不退。C = s + p；若 C ≤ H，完成，设备下次可用 s + max(p,b)；b > p 产生 reserved idle，p > b 延长占用；非抢占。H 先到则终止，该 job 记为 unfinished + censored；设备在 H 时可用也终止。**不可行命令**（未释放/重复/前驱未完成/预留不足/超预算/计划跨 H/非有限值/超 200 action）不执行，保留已消耗资源、记违规并终止 trial；违规 trial 仍进统计。

**指标（§4，逐字）。** w 为权重，W 为该 case 全部 job 权重和；**所有 job 都留在分母，包括未完成**；未完成 job 的 tardiness 用 C = H。

| 指标 | 定义 |
| --- | --- |
| weighted_completion_rate | 在 H 前完成的权重 / W |
| weighted_on_time_rate | 在各自 due 前完成的权重 / W |
| weighted_tardiness_s | Σ w·max(C − due, 0)，不除 W |
| cost / observations | 累计成本 / 付费 review 次数 |
| elapsed_s | trial 结束时刻，可小于 H |
| observed_overrun_s | Σ_executed max(min(p, H−s) − b, 0) |
| reserved_idle_s | Σ_completed max(b − p, 0) |
| censored_units | 因服务跨 H 而未完成的已执行 job 数 |
| invalid_actions / valid_protocol | 不可行命令数 / 是否符合动作协议 |

**种子与 trial 数（§4）。** 30 个公开种子 2026111700–2026111729；每 case 30 trials，3 case 共 90；五个 mapping 共 **450 trials**。对比策略共享同一批 source 分配以做配对。正式测试用 test 记录与赛方另冻的 30 个种子；策略必须在看测试结果前冻结。每个 trial 结果行要有 case、split、trial number、seed、α、β 与全部指标。

**约束检查（§4）。** 若以成本/容量风险为主目标，名义 mapping 下每 case 30 trials 的 mean weighted on-time completion 必须 ≥ 0.50；不满足就如实报，不得声称数学不可行。

## 3 已知 / 未知 / 待假设

### 已知（有文件、有字段、能复算）

| 事项 | 值 / 位置 |
| --- | --- |
| 记录数 | 69（EgoDemo 31、EgoPro 14、EgoStandard 24） |
| 帧数 | 66,070（30 Hz，双手 21 点） |
| 语义区间 | 349，eligible（≥1.2 s）343 |
| 环境划分 | 24 个 environment，16 train / 4 validation / 4 test（`record_split.csv`） |
| P1 状态维度 | 每手 32 维（15 坐标 + 4 标量 + 3 法向 + 3 前向 + 3 速度 + 3 加速度 + 速度模 + 加速度模） |
| 可靠性标签 | Demo `bad_frame_ratio.json`；Pro/Standard `annotation_bad_frame_pose_hand.csv` 的 `is_bad` |
| P3 任务 | `tasks.csv` 36 行；5 条前驱：S2_J09←J02、S2_J11←J05、S3_J12←J03、S3_J15←J06、S3_J16←J07 |
| P3 条件 | `common_conditions.json`：前缀 0.2/0.6/1.0 s、review 延迟 1 s、review 成本 1、每 job 至多 2 次、α=1 β=0.5、reserve_min 0.2、速度 1、changeover 0.5、费用 2/0.1/0.2 |

### 未知（题面没给、附件缺、必须自己定或标风险）

| 未知 | 影响 | 处理 |
| --- | --- | --- |
| `Data_Documentation/` 全部文档（record_index、missing_observation_experiments.md、tasks_and_evaluation.md、attachment_guide、file_manifest） | P2 没有官方实验口径；P3 只能以 requirements 文件代替 | P2 口径在第 4 节冻结；P3 逐条按 requirements |
| P2 的 per-request 成本与延迟 | 题面只说“fixed in advance”，未给数值 | 自建 c(T)=0.5+0.2T，λ=1 cm/cost，并做 λ 敏感性 |
| P2 的容忍误差 | 题面未给 | 以 5 cm 作为 reactive 基线阈值，另报 RMSE 全曲线 |
| 环境语义标签（retail/logistics 以外的场景） | 只能从 `environment_id` 前缀读 | 用 `environment_id` 前两级做场景标签，不聚类硬造 |
| 操作员是否跨环境 | 题面明说可能跨，split 不是 unseen-operator | 在讨论里写明指标偏乐观的来源 |
| `tasks.csv` 的 zone/权重是否与记录一致 | 题面说 scenario assumption | 不做物理一致性校验，按题面当合成条件 |

### 待假设（写进模型、后面要检验）

| 假设 | 依据 | 失效条件 / 检验 |
| --- | --- | --- |
| 头部位姿可作为归一化参考，头部坐标系下手部状态跨环境可比 | 头戴相机随头动，手部任务在头坐标系下更稳定 | 头部位姿本身缺失/抖动时退化；用 per-record 头部速度与 bad 率检验 |
| 21 点中 wrist + 食指尖 + 拇指尖足以表征末端；掌宽可做尺度归一 | 抓取/放置主要由拇指-食指对捏决定 | 侧捏/掌托任务会低估；用 aperture 分布与 subtask 描述对照 |
| `is_bad` 是“观测质量”的可靠代理，而非“动作异常” | 字段名与 problem_type（occlusion/edge） | 若 bad 与运动突变强相关，几何特征会学成运动检测器；用速度分层 AUC 检验 |
| 测试环境与训练环境同分布（仅场景不同） | 题面要求 environment split | 跨环境 AUC 0.528 说明分布差异大；在 P1 失败案例里明写 |
| P3 的 d 只由前缀可估，不能用 source id 反查 | requirements §2 红线 | 回归残差 MAE 2.94 s，已量化 |
| 五个 mapping 共用同一批抽样（同 seed 配对） | §4 要求 paired | 代码按 case+seed 生成，策略不改抽样 |

## 4 P2 的实验口径（自定，先冻结）

`Data_Documentation/missing_observation_experiments.md` 缺失，故在跑任何模型前固定如下，所有对比方法共用：

- 保留状态：P1 的**优势手腕点世界坐标 3D**（不是 21×3 全量）；这是 P1 状态里第 0–2 维。
- 帧率 30；上下文 10 帧（1/3 s）；掩码长度 L ∈ {0.2, 0.5, 1.0, 2.0} s = {6,15,30,60} 帧。
- 每条 test 记录每个 L 最多 400 个窗口，步长 L/2；上下文与掩码内不得有 `is_bad` 帧；只在前向可用信息上预测。
- 误差：位置 RMSE / MAE（m），终点误差，恢复后跳变 |pred_last − true_first_after|。
- 再观测成本：每次请求 c(T)=0.5+0.2T（cost），误差权重 λ=1 cm/cost；目标 J(T)=RMSE(T)[cm]+λ·c(T)/T（按每秒摊）。
- 自然遮挡：连续 `is_bad` 段按 run 统计时长、恢复时间；低质量段不算真值误差。

## 5 交付物与题面要求的对应

| 题面要求 | 本稿产物 |
| --- | --- |
| 数据整理、保留/排除理由 | `out/03-numbers.md` 表 1；`data/panel_records.csv` |
| P1 状态定义、可靠性模型、baseline、失败案例 | `out/01-model.md` §1；`data/p1_*.json`；`code/p1_state.py`、`p1_model.py` |
| P2 masking/replay、误差随 L、成本、自然遮挡 | §2；`data/p2_*.json`；`code/p2_predict.py`、`p2_crossover.py` |
| P3 36 job、三 case、五 mapping、450 trials、七指标、约束 | §3；`data/p3_*.json/csv`；`code/p3_schedule.py` |
| 可复现程序 | `code/run_all.py`，入口一次跑完 |

VERDICT: PASS
