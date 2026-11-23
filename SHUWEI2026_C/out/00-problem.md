BYTES 15182

# C 题数据全景分析（Restocking Operations in Unmanned Supermarkets）

> 本文件是数据侧的事实底稿，不是论文正文。所有数字由 `code/profile_data.py`、
> `code/deep_stats.py` 现算得到，产物 `data/data_profile.json`（195,994 B）、
> `data/deep_stats.json`、`data/ledger.json`（12 条记录，全带 source+sha256+fetched_at）。
> 复现：`E:\Mini\envs\mathmodel\python.exe code\profile_data.py`。

## 1. 规模与清单（实测，与题面一致）

| 数据集 | records | timestamps | 环境数 | 腕部视频 | 容器 |
|---|---|---|---|---|---|
| EgoDemo | 31 | 16,414 | 13 | 9/31 | JSON + Parquet + MP4 |
| EgoPro | 14 | 17,642 | 6 | 14/14（4 路） | MCAP 展平为 CSV |
| EgoStandard | 24 | 32,014 | 11 | 0/24（仅头戴 2 路） | MCAP 展平为 CSV |
| 合计 | **69** | **66,070** | **24** | — | 原始 5.834 GB，非视频 461.8 MB |

- 24 个 environment 的划分是**按环境**、不是按记录：train 16 / validation 4 / test 4，实测**无环境跨 split**（0 泄漏）。
- 三个数据集**共用环境**（6 个）：`logistics_x_courier_station_0021`（Demo+Pro，train）、
  `retail_x_supermarket_0037 / 0054 / 0058`（Demo+Std，train）、`retail_x_supermarket_0074`（Demo+Std，validation）、
  `logistics_x_courier_station_0011`（Pro+Std，test）。→ 跨数据集比较可以做到**同环境配对**，这在 Problem 1 的“比较任务/环境/阶段差异”里是免费的对照组。
- 5 类场所：retail（超市/便利店）、logistics（快递站）、office（写字楼）、home（公寓）、hospitality（餐厅）；
  12 类场景（`package_room`、`detergent_shelf`、`refrigerated_section`、`dining_area`、`kitchen`…）。
- 41 个 operator、30 个 scene：**operator 不跨 split 重复**不是要求，但实测同一 operator 在 train 里出现多次，做留出评估时按**环境**分，不要按人分。

## 2. 两个必须先踩平的坑（判据写错的直接原因）

1. **目录名不是 `episode_uuid`**。`record_split.csv` 的 `episode_uuid` 与 EgoPro/EgoStandard 的目录名 **0 匹配**；
   真 uuid 在 `session_metadata.csv` 的 `task_info.episode_uuid`。EgoDemo 的目录名是 `E001..E031`，
   真 uuid 在 `meta/episodes/chunk-000/file-000.parquet` 的 `episode_uuid` 列。
   按目录名硬猜（旧版 profiler 的做法）会把 environments 算成 13、operators 18、scenes 17 —— **全错**；
   按 uuid 关联后是 **24 / 41 / 30**，与题面“24 environments”对齐。
2. **1.2 s 阈值不能裸比**。`source_segment_index.csv` 的 `duration_s` 是 `end_s - start_s` 浮点差，
   实测有 6 行得到 `1.1999999999999993`；裸写 `>= 1.2` 会数出 341，题面写的是 **343**。
   加 `1e-9` 容差后 = 343（`eligible==1` 也是 343）。凡用这条索引做筛选，阈值都带容差。

## 3. 时间与采样：连续性没问题，缺的是“看得见”而不是“采得到”

- 三套数据的时间戳都是 **30 Hz 均匀**（`dt` median 0.033333 s、`p99` 0.033334 s、`neg/zero` 全 0），
  抽样的 6 个 record 里 **>1.5×dt 的间隔 0 个**。→ 缺测不是采样掉帧造成的，只能来自遮挡/坏帧/人为掩蔽。
- 设备配置（EgoPro `session_metadata.csv`）：head_left / head_right RGB **1920×1456 @30**、
  head_depth **320×240 @5**、left / right wrist RGB **1920×1536 @30**。
  **注意**：5 fps 的是深度相机，不是腕部相机（这点很容易读错）。
- 腕部通道覆盖不均：Demo 9/31、Pro 14/14、**Std 0/24**。
  → Problem 2 的“多通道掩蔽”只能在 Demo 的 9 个 + Pro 的 14 个上做；Std 只能做单/双头戴通道实验。

## 4. 坐标：每段录像一个自己的 world 帧，腕部相机没有外参

- 同一只手 21 个关键点在世界系下的**刚性尺寸稳定**：相邻关键点最大距离 median **0.157 m**（p05 0.149 / p95 0.160），说明关键点定义一致、无尺度漂移。
- 但**世界原点逐段不同**（实测 bbox）：Demo E001 x[0.48,1.63] z[1.14,1.45]；E010 z[-0.99,-0.39]；
  Pro 样本 x[-2.93,-1.77] y[-3.77,-3.19]。→ 不能跨 record 直接算绝对距离或拼地图；
  Problem 1 的“坐标约定”检查必须写成**每段独立归一**（减质心 / 用工作台局部系），否则统计量全是位置偏置。
- 手质心在单段内的行程 span（x/y/z）：Demo 0.38/0.39/0.26 m、Pro 0.60/0.59/0.58 m、Std 0.74/0.83/0.54 m（p95 最大到 2.3 m，含走动的段）。
- 腕部相机**无 world 外参**（题面明说，配置文件里也只有 intrinsic）→ 腕部像素不能反投影到世界系；
  Problem 2 里用腕部通道只能做“同模态自洽”的预测/校验，不能当世界坐标的真值。

## 5. 质量标记：比率低、但结构不对称

| 数据集 | 坏帧/总帧 | 坏帧率 | 单记录中位 | 单记录最大 |
|---|---|---|---|---|
| EgoDemo | 108 / 16,414 | **0.658%** | 0.0 | 2.61% |
| EgoPro | 410 / 17,642 | **2.324%** | 1.25% | 7.21% |
| EgoStandard | 310 / 32,014 | **0.968%** | 0.0 | 6.75% |

- Demo 的 `bad_frame_ratio.json` 给的是**每只手的坏帧原因计数**（`occlusion` 共 159 次，左右手分别 96/63），
  一个坏帧可同时记左右手 → 原因计数（159）**大于**坏帧数（108），不能直接当帧数用。
- Pro/Std 的 `annotation_bad_frame_pose_hand.csv` 只导出 `is_bad` 与 `problem_type.length`；
  **具体类型码没有导出**（该文件只有 10 列）。→ 想按“遮挡 vs 边缘”分组，只能用 Demo；
  Pro/Std 只能做“坏/不坏”二分类，或者自己从几何上判定（例如关键点接近画面边界、速度突变）。
- 坏帧分布是**重尾**：中位 0 或 1%，但单段可到 7%。→ Problem 1 的“观测可靠性模型”用**分段率**而不是全局均值，
  否则 69 段里有 40 多段是 0，回归会退化。

## 6. 自然遮挡：亚秒级，做不出“长缺失”

| 组 | 段数 | median | p95 | max | ≥0.2 s | ≥1 s | 涉及记录 |
|---|---|---|---|---|---|---|---|
| Demo | 17 | 0.133 s | 0.460 s | 0.567 s | 6 | 0 | 5/31 |
| MCAP（Pro+Std） | 119 | 0.067 s | 0.507 s | 1.867 s | 36 | **1** | 17/38 |

→ 结论很硬：**自然遮挡无法支撑“缺失 3 s / 5 s 的预测”这类实验**，Problem 2 必须用**人工掩蔽 + 回放**（题面也是这么要求的）。
自然遮挡只能拿来当“真实发生频率/恢复时长”的先验（发生密度约 0.45 段/分钟，恢复 median 0.07–0.13 s）。

## 7. 语义段与 work unit：349 → 343

- `source_segment_index.csv`：349 行，`eligible==1` 343 行，排除理由只有 `shorter_than_1p2_seconds`（6 行）。
- 时长（343 条）：min 1.2 / p25 3.0 / **median 4.0** / p75 7.3 / p95 14.08 / **max 125.0** / mean 6.39 s。
- 按 family：**P 172（median 4.0）/ A 145（3.6）/ L 26（7.0）**（eligible 口径）。
  服务时长 `αd+β`（α=1、β=0.5）对应：P p50 4.5 / A 4.1 / **L 7.5**，p90 分别 11.5 / 10.5 / 14.1。
- 按 split：train 252 / validation 35 / test 62；按数据集：Demo 118 / Pro 71 / Std 160。
- 每段 2–23 个 work unit（median 4，mean 5.06）。
- **一段 = 一个文本标注区间，不是一件商品**。`annotation_semantic_segments.csv` 里
  `segment.start_time / end_time` 是标注窗口（实测某 Pro 段切成 8 个 10 s 窗口、subtask 全同），
  而 `source_segment_index` 是把窗口**按任务合并**后的作业单位 —— 两者粒度不同，混用会把 “1 段” 当成 “1 件货”。

## 8. 三个 case 的结构（tasks.csv 12 行 × 3）

| case | jobs | H (s) | 成本预算 | 查看上限 | release | due 范围 | 权重分布 | 前驱 |
|---|---|---|---|---|---|---|---|---|
| S1 | 8 | 100 | 32 | 4 | 0/20/40 | 35–100 | 3×2, 1×2, 2×4 | 0 |
| S2 | 12 | 100 | 34 | 6 | 0/20/40 | 35–100 | 3×3, 1×3, 2×6 | 2 |
| S3 | 16 | 125 | 40 | 8 | 0/25/50 | 43.75–125 | 3×4, 1×4, 2×8 | 3 |

- 区域只用 Z1–Z4（各 case 均分：S1 各 2 / S2 各 3 / S3 各 4），起点 Z0(0,0)；
  Z1(1,0) Z2(0,1) Z3(1,1) Z4(2,0) → 相邻移动耗时 D+0.5 ∈ [1.5, 2.5] s，最远 Z0→Z4 2.0+0.5。
- **成本代数的硬约束（本段最重要的发现）**：`service_fixed = 2.0`/job，
  S3 是 16 jobs → **固定成本 32，预算 40，只剩 8 个成本单位**给 `0.1b + 0.2D`。
  按 b≈p50、D≈1.2 估，16 个 job 光这两项就要 ≈ 3.8 + 3.0 = 6.8，只剩 1.2 的余量给“观察（每次 1 单位）”。
  → **S3 上“多看几次”几乎不可行**：最多 1 次查看就可能超预算；这与 S1（8×2=16/32，余 16）完全相反。
  这决定了三个 case 的策略不能共用一套参数，必须在 S3 上把“查看”当稀缺资源。

## 9. 覆盖性审计（回应“是不是认真查了所有数据”）

本轮不是只抽几个 record：逐 ZIP member 流式读了全部字节，逐一路打开了全部视频；805 个非视频文件与解压副本逐一 SHA-256 比对并做 CSV/JSON/Parquet 解析。产物：`data/full_audit.json`、`data/video_audit.json`，脚本 `code/audit_all_data.py`。

| 项目 | 实测 |
|---|---|
| ZIP member / 总字节 | **989 / 6,096,375,863 B** |
| 非视频 / 字节 | **805 / 461,837,574 B**，与解压副本哈希全部一致，解析错误 0 |
| 视频 / 字节 | **184 / 5,634,538,289 B** |
| 视频总帧数 / 时长 | **178,512 帧 / 5,963.7379 s** |
| 分辨率 | 1920×1456 共 138 路；1920×1536 共 46 路 |
| 视频可解码性 | 每路首/中/末帧均可解码；**全部 184 路通过** |
| 帧数与数值表/帧索引 | **184/184 一致** |
| 主数值 payload 查重 | **无重复** |
| 审计错误 / 警告 | **0 / 0** |

边界：这证明的是**全字节、全文件、全视频容器与抽样解码**都核过；不是把 178,512 帧逐帧做了语义判读。语义层目前只做了数值表与标注，没有逐帧人工看图。

按压缩包拆开（每包的 `sha256_mismatch`、`parse_errors`、`video_open_errors`、`video_sample_decode_errors` 全部为 0）：

| 包 | member | 字节 | 视频 | 视频字节 | 非视频 | 非视频字节 |
|---|---|---|---|---|---|---|
| EgoDemo | 297 | 1,916,728,226 | 80 | 1,881,710,137 | 217 | 35,018,089 |
| EgoPro | 308 | 2,029,238,984 | 56 | 1,865,703,907 | 252 | 163,535,077 |
| EgoStandard | 384 | 2,150,408,653 | 48 | 1,887,124,245 | 336 | 263,284,408 |
| 合计 | **989** | **6,096,375,863** | **184** | **5,634,538,289** | **805** | **461,837,574** |

`data/video_audit.json` 是 184 条逐路记录，每条形如
`{"dataset":"EgoDemo","member":"…/videos/observation.images.head_left/chunk-000/file-000.mp4","bytes":50126915,"sha256":"3d99bd5f…","expected_frames":1619,"open":true,"frames":1619,"fps":30.0,"width":1920,"height":1456,"duration_s":53.9667,"decoded_samples":[{"position":0,"ok":true},…]}` ——
它同时给出**与数值表比对的期望帧数**和**实解帧数**，两者 184/184 相等。

## 9b. 官方口径 baseline（已替换首版错误结果）

首版曾误用全量 343 段 + NumPy RNG，并把预留 b 设为实现 p；那组数字已作废。现按 `Problem_3_Requirements.pdf` 重算：

- train 同族 median + 0.5 s 作为预留 b；validation 同族 eligible 池有放回抽样；保持 `source_segment_index` 行序。
- 每 case 每 seed 重新 `random.Random(seed)`，按 `job_id` 排序依次 `choice`；30 个 public seeds `2026111700..2026111729`。
- EDD 选序、不付费查看、不看实际 p；实现 release/predecessor/移动/切换/成本/H/非抢占/预留不提前释放。
- 产物：`data/results_baseline_p3.json`、逐 trial `data/baseline_p3_trials.csv`，脚本 `code/baseline_p3.py`。

| case | 加权完成率 mean | 加权准时率 mean | 加权拖期 mean(s) | 成本 mean/预算 | elapsed mean/H | 未完成 units mean | 提前停止 |
|---|---|---|---|---|---|---|---|
| S1 | **1.000** | **0.990** | 0.7 | 21.53 / 32 | 74.5 / 100 | 0.00 | 0/30 |
| S2 | 0.876 | 0.635 | 50.3 | 28.06 / 34 | 97.6 / 100 | 1.63 | 19/30 |
| S3 | 0.845 | 0.586 | 124.1 | 35.99 / 40 | 123.2 / 125 | 2.77 | 17/30 |

三 case 的名义加权准时率都 > 0.50，满足题面下限；但 S2/S3 的完成率与 elapsed 说明**容量和预留**才是主要矛盾，不是“多看几次”。S3 固定执行费已占 32/40，查看预算极紧。

## 10. 三问的可行性判据（能不能做、缺什么）

| 问题 | 数据够不够 | 具体做法 | 缺的东西 |
|---|---|---|---|
| P1 状态变化 + 可靠性建模 | **够**。69 段 / 66,070 帧 / 24 环境 / 343 作业单位 / 坏帧重尾 | 每段独立归一后做“关键点→代表点”的轨迹特征（速度、加速度、停留、抓取相），可靠性用坏帧率 + 关键点速度离散度 + 段长做分层模型 | 只有 Demo 有坏帧原因；Pro/Std 无类型码 |
| P2 缺失下的预测与再观测 | **够但必须人工掩蔽**（自然遮挡 max 1.87 s、仅 1 段 ≥1 s） | 人工掩蔽窗口 {0.5,1,2,3,5} s × 通道 {头戴,腕部,双通道}，预测器 3 个 baseline + 1 个学习型；再观测成本模型直接照题面 | 腕部无外参 → 腕部实验只能做同模态；Std 无腕部 |
| P3 不确定下的补货调度 | **够**（343 eligible 区间，按 family+split 抽样） | 官方事件驱动仿真 + EDD/权重优先/预算感知；预留 b 与查看次数作为动作；30 seed 配对 | 无显式 job→unit 映射，但官方抽样协议已给：split/family/行序/random.Random(seed)/job_id 排序 |

## 11. 还没拿到 / 需要用户确认的

1. 题面提到的 `Data_Documentation/`（`attachment_guide.md`、`missing_observation_experiments.md`）
   **不在下载包里**。P2 的实验约定只能按题面正文推，建议去官网或群里补下这两个文件。
2. `problem_type` 的类型码未导出（CSV 只有长度）。若要按遮挡/边缘分组，只能靠 Demo 或自建几何判据。
3. 2026 秋季赛的**页数/语言/AI 声明**规则，本机只有 2025 与 2021 版（英文、12 pt、≤25 页含摘要与目录）。
   按旧规写作是安全的，但交件前要对一眼 2026 通知。
4. `source_segment_index` 与 `tasks.csv` 之间没有 job→unit 的显式映射；官方已规定按 split/family 的 eligible 池、
   保持行序、`random.Random(seed).choice`、按 `job_id` 排序逐个有放回抽样。论文只能照此实现，不能再自定义全池抽样。

## 12. 复现与产物

```
E:\Mini\envs\mathmodel\python.exe code\profile_data.py   # data/data_profile.json（69 段全字段）
E:\Mini\envs\mathmodel\python.exe code\deep_stats.py     # data/deep_stats.json（本文件的汇总表）
E:\Mini\envs\mathmodel\python.exe code\audit_all_data.py # 全量 ZIP/视频审计（约 2 min）
E:\Mini\envs\mathmodel\python.exe code\baseline_p3.py    # 官方 30-seed baseline
```

VERDICT: PASS — 989 个 ZIP member 全量读取、805 非视频全量校验、184 视频全路打开且首中末帧可解码；规模/环境/时间/坐标/质量/区间/任务数字全部现算，官方 baseline 已按 PDF 重算；Data_Documentation 缺失与 problem_type 类型码未导出等缺口已列出。
