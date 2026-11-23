BYTES 18260
# 03 数字表：SWC2026 C 前期建模稿

队号 SWBMCM2634892。每一行的值都从 `data/*.json` 读出；JSON 键按 `文件名.路径` 写，`[case=S2,policy=slack,alpha=1.0,beta=0.5]` 表示在 `summary` 数组里按这些字段筛选。

跑数命令见文末。全部数字由 `code/make_numbers.py` 生成，不手抄。

## 1 规模与划分

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 记录数 | 69 | 条 | p1_state_summary.n_records |
| 帧数 | 66070 | 帧 | p1_state_summary.n_frames |
| 语义段 | 349 | 段 | segments.csv 行数 |
| environment | 24 | 个 | record_split.csv 去重 |
| train/val/test environment | 16/4/4 | 个 | record_split.csv split |
| 主导手 L / R | 26 / 43 | 条 | p1_state_summary.dominant_left/right |
| 状态维数（每手） | 32 | 维 | p1_state_summary.state_dim_per_hand |
| 几何特征（每手） | 8 | 维 | p1_state_summary.geom_dim_per_hand |
| EgoDemo 掌宽均值 | 0.0588 | m | p1_state_summary.dataset_means.palm_width.EgoDemo |
| EgoPro 掌宽均值 | 0.0597 | m | p1_state_summary.dataset_means.palm_width.EgoPro |
| EgoStandard 掌宽均值 | 0.0584 | m | p1_state_summary.dataset_means.palm_width.EgoStandard |
| EgoDemo 腕速均值 | 0.1448 | m/s | p1_state_summary.dataset_means.speed_mean.EgoDemo |
| EgoPro 腕速均值 | 0.1695 | m/s | p1_state_summary.dataset_means.speed_mean.EgoPro |
| EgoStandard 腕速均值 | 0.1673 | m/s | p1_state_summary.dataset_means.speed_mean.EgoStandard |
| EgoDemo 坏帧占比 | 0.22% | % | p1_state_summary.dataset_means.bad.EgoDemo |
| EgoPro 坏帧占比 | 2.05% | % | p1_state_summary.dataset_means.bad.EgoPro |
| EgoStandard 坏帧占比 | 0.87% | % | p1_state_summary.dataset_means.bad.EgoStandard |

## 2 P1 可靠性

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 逻辑回归 AUC_bad (train/val/test) | 0.744 / 0.752 / 0.596 | — | p1_reliability.auc_bad_calibrated |
| 几何马氏 AUC_bad (train/val/test) | 0.725 / 0.703 / 0.613 | — | p1_reliability.auc_bad_geometry |
| 融合 R AUC_bad (train/val/test) | — / 0.746 / 0.627 | — | p1_reliability.auc_bad_fused |
| ap_bad_calibrated (val/test) | 0.0739 / 0.0381 | — | p1_reliability.ap_bad_calibrated |
| ap_bad_geometry (val/test) | 0.0760 / 0.0369 | — | p1_reliability.ap_bad_geometry |
| ap_bad_fused (val/test) | 0.0764 / 0.0407 | — | p1_reliability.ap_bad_fused |
| AP 基线（正例率） | 0.0189 | — | p1_reliability.ap_baseline_test |
| test environment logistics_x_courier_station_0011 AUC / n / 正例 | 0.528 / 12634 / 426 | — | p1_reliability.per_env_test |
| test environment logistics_x_courier_station_0041 AUC / n / 正例 | 0.938 / 7274 / 36 | — | p1_reliability.per_env_test |
| 阈值 0.3：保留/召回/精确率/F1 | 0.930 / 0.816 / 0.0166 / 0.0324 | — | p1_reliability.threshold_sensitivity |
| 阈值 0.5：保留/召回/精确率/F1 | 0.711 / 0.587 / 0.0156 / 0.0303 | — | p1_reliability.threshold_sensitivity |
| 阈值 0.6：保留/召回/精确率/F1 | 0.490 / 0.329 / 0.0127 / 0.0244 | — | p1_reliability.threshold_sensitivity |
| 阈值 0.7：保留/召回/精确率/F1 | 0.185 / 0.074 / 0.0075 / 0.0136 | — | p1_reliability.threshold_sensitivity |
| 阈值 0.8：保留/召回/精确率/F1 | 0.002 / 0.000 / 0.0000 / 0.0000 | — | p1_reliability.threshold_sensitivity |
| 阈值 0.9：保留/召回/精确率/F1 | 0.000 / 0.000 / 0.0000 / 0.0000 | — | p1_reliability.threshold_sensitivity |

## 3 P1 分段（test，7 条记录）

| 方法 | ARI | 帧 F1 | 边界 MAE (s) | 边界召回 | 边界精确率 | 段数误差 | JSON 键 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 头部状态 + Ward | 0.414 (0.253) | 0.561 (0.220) | 1.390 | 0.686 | 0.657 | 4.0 | p1_segmentation.by_method.ward |
| 原始坐标 + KMeans | 0.342 (0.161) | 0.392 (0.180) | 0.355 | 1.000 | 0.194 | 41.0 | p1_segmentation.by_method.raw |
| 头部 + Ward + oracle K | 0.599 (0.151) | 0.689 (0.175) | 1.994 | 0.771 | 0.771 | 0.0 | p1_segmentation.by_method.ward_oracleK |
| 原始坐标 + Ward | 0.344 (0.181) | 0.491 (0.125) | 1.878 | 0.710 | 0.678 | 4.0 | p1_segmentation.by_method.ward_rawfeat |
| 头部状态 + KMeans | 0.332 (0.182) | 0.372 (0.170) | 0.183 | 1.000 | 0.139 | 63.6 | p1_segmentation.by_method.kmeans_headfeat |
| 主−基线 绝对差 ARI / F1 | +0.0715 / +0.1696 | — | — | — | — | — | p1_segmentation.improvement.ward |
| EgoDemo F1（主/基线） | 0.870 / 0.530 | — | — | — | — | — | p1_segmentation.by_dataset.EgoDemo |
| EgoPro F1（主/基线） | 0.423 / 0.247 | — | — | — | — | — | p1_segmentation.by_dataset.EgoPro |
| EgoStandard F1（主/基线） | 0.448 / 0.396 | — | — | — | — | — | p1_segmentation.by_dataset.EgoStandard |

## 4 P2 预测误差（位置，cm）

| L (s) | 方法 | RMSE | MAE | 恢复跳变均值 | 跳变 p95 | ≤2 cm | ≤5 cm | JSON 键 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.2 | hold | 2.60 | 1.89 | 3.45 | 8.14 | 0.667 | 0.938 | p2_prediction.by_length[L_s=0.2,method=hold] |
| 0.2 | cv | 2.47 | 1.46 | 3.22 | 8.51 | 0.777 | 0.955 | p2_prediction.by_length[L_s=0.2,method=cv] |
| 0.2 | ca | 4.61 | 2.18 | 5.14 | 16.41 | 0.705 | 0.898 | p2_prediction.by_length[L_s=0.2,method=ca] |
| 0.2 | ridge | 2.00 | 1.36 | 2.78 | 6.74 | 0.803 | 0.972 | p2_prediction.by_length[L_s=0.2,method=ridge] |
| 0.5 | hold | 4.56 | 3.40 | 5.80 | 13.43 | 0.413 | 0.780 | p2_prediction.by_length[L_s=0.5,method=hold] |
| 0.5 | cv | 6.04 | 3.83 | 8.13 | 19.40 | 0.435 | 0.748 | p2_prediction.by_length[L_s=0.5,method=cv] |
| 0.5 | ca | 18.44 | 9.33 | 25.20 | 74.48 | 0.329 | 0.536 | p2_prediction.by_length[L_s=0.5,method=ca] |
| 0.5 | ridge | 3.97 | 2.89 | 5.30 | 12.23 | 0.500 | 0.837 | p2_prediction.by_length[L_s=0.5,method=ridge] |
| 1.0 | hold | 6.72 | 5.11 | 8.03 | 18.02 | 0.262 | 0.609 | p2_prediction.by_length[L_s=1.0,method=hold] |
| 1.0 | cv | 11.46 | 7.95 | 16.44 | 36.45 | 0.234 | 0.472 | p2_prediction.by_length[L_s=1.0,method=cv] |
| 1.0 | ca | 71.17 | 33.78 | 95.68 | 280.11 | 0.170 | 0.279 | p2_prediction.by_length[L_s=1.0,method=ca] |
| 1.0 | ridge | 6.30 | 4.80 | 7.76 | 17.43 | 0.283 | 0.638 | p2_prediction.by_length[L_s=1.0,method=ridge] |
| 2.0 | hold | 8.95 | 7.05 | 10.02 | 22.22 | 0.155 | 0.451 | p2_prediction.by_length[L_s=2.0,method=hold] |
| 2.0 | cv | 23.54 | 16.29 | 32.39 | 75.08 | 0.119 | 0.261 | p2_prediction.by_length[L_s=2.0,method=cv] |
| 2.0 | ca | 250.54 | 125.59 | 366.27 | 1038.83 | 0.085 | 0.140 | p2_prediction.by_length[L_s=2.0,method=ca] |
| 2.0 | ridge | 8.58 | 6.82 | 9.74 | 20.87 | 0.143 | 0.466 | p2_prediction.by_length[L_s=2.0,method=ridge] |

### 4.1 窗口数与共形区间

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| L=0.2s 窗口数 | 2207 | 个 | p2_prediction._meta.windows.6 |
| L=0.5s 窗口数 | 1499 | 个 | p2_prediction._meta.windows.15 |
| L=1.0s 窗口数 | 738 | 个 | p2_prediction._meta.windows.30 |
| L=2.0s 窗口数 | 348 | 个 | p2_prediction._meta.windows.60 |
| L=0.2s 共形半径 q90 / 覆盖率 / 中位误差 | 0.0289 / 0.895 / 0.0092 | m / — / m | p2_interval.by_length |
| L=0.5s 共形半径 q90 / 覆盖率 / 中位误差 | 0.0643 / 0.902 / 0.0201 | m / — / m | p2_interval.by_length |
| L=0.6s 共形半径 q90 / 覆盖率 / 中位误差 | 0.0746 / 0.905 / 0.0228 | m / — / m | p2_interval.by_length |
| L=1.0s 共形半径 q90 / 覆盖率 / 中位误差 | 0.1013 / 0.893 / 0.0358 | m / — / m | p2_interval.by_length |
| L=2.0s 共形半径 q90 / 覆盖率 / 中位误差 | 0.1367 / 0.887 / 0.0535 | m / — / m | p2_interval.by_length |

### 4.2 再观测经济性

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 最优间隔 T* | 0.30 | s | p2_prediction.economics.optimum.T_s |
| 最优 RMSE / 成本 / J | 2.65 / 1.867 / 4.521 | cm / cost/s / — | p2_prediction.economics.optimum |
| 基线 fixed_0.5s：T / RMSE / J | 0.50 / 3.97 / 5.173 | s / cm / — | p2_prediction.economics.baselines.fixed_0.5s |
| 基线 fixed_1.0s：T / RMSE / J | 1.00 / 6.30 / 6.998 | s / cm / — | p2_prediction.economics.baselines.fixed_1.0s |
| 基线 reactive_5cm：T / RMSE / J | 0.72 / 5.00 / 5.894 | s / cm / — | p2_prediction.economics.baselines.reactive_5cm |
| 基线 never_observe：T / RMSE / J | ∞ / 8.58 / 8.577 | s / cm / — | p2_prediction.economics.baselines.never_observe |
| 自然遮挡段数 | 264 | 段 | p2_prediction.occlusion.n_runs |
| 自然遮挡 mean_s | 0.2019 | s | p2_prediction.occlusion.mean_s |
| 自然遮挡 median_s | 0.1333 | s | p2_prediction.occlusion.median_s |
| 自然遮挡 p90_s | 0.4900 | s | p2_prediction.occlusion.p90_s |
| 自然遮挡 max_s | 1.9000 | s | p2_prediction.occlusion.max_s |
| 自然遮挡 share_over_1s | 0.76% | % | p2_prediction.occlusion.share_over_1s |

### 4.3 hold/CV 交叉点

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 均值交叉点 | 0.267 | s | p2_crossover.crossover_s.mean |
| 中位交叉点 | 0.600 | s | p2_crossover.crossover_s.median |
| 3 帧 CV 增益（均值/中位） | +26.2% / +53.5% | % | p2_crossover.rows[L_frames=3] |
| 6 帧 CV 增益（均值/中位） | +8.8% / +36.3% | % | p2_crossover.rows[L_frames=6] |
| 8 帧 CV 增益（均值/中位） | -4.6% / +27.9% | % | p2_crossover.rows[L_frames=8] |
| 10 帧 CV 增益（均值/中位） | -10.8% / +16.2% | % | p2_crossover.rows[L_frames=10] |
| 12 帧 CV 增益（均值/中位） | -21.9% / +8.4% | % | p2_crossover.rows[L_frames=12] |
| 15 帧 CV 增益（均值/中位） | -35.9% / +1.2% | % | p2_crossover.rows[L_frames=15] |
| 18 帧 CV 增益（均值/中位） | -39.4% / -8.8% | % | p2_crossover.rows[L_frames=18] |
| 30 帧 CV 增益（均值/中位） | -70.5% / -41.2% | % | p2_crossover.rows[L_frames=30] |

## 5 P3 时长模型与容量

| 量 | 值 | 单位 | JSON 键 |
| --- | --- | --- | --- |
| 前缀 0.2s：MAE / RMSE / Spearman / 均值基线 | 2.939 / 3.864 / 0.288 / 3.336 | s / s / — / s | p3_scheduling.duration_model.0.2 |
| 前缀 0.6s：MAE / RMSE / Spearman / 均值基线 | 2.972 / 3.900 / 0.257 / 3.336 | s / s / — / s | p3_scheduling.duration_model.0.6 |
| 前缀 1.0s：MAE / RMSE / Spearman / 均值基线 | 3.290 / 4.228 / 0.107 / 3.336 | s / s / — / s | p3_scheduling.duration_model.1.0 |
| S1 容量比（seed-1 NN） | 0.490 | — | p3_scheduling.capacity[case=S1] |
| S2 容量比（seed-1 NN） | 0.780 | — | p3_scheduling.capacity[case=S2] |
| S3 容量比（seed-1 NN） | 0.800 | — | p3_scheduling.capacity[case=S3] |
| S1 容量比（解析 MST） | 0.658 | — | p3_scheduling.capacity_analytic[case=S1] |
| S2 容量比（解析 MST） | 1.023 | — | p3_scheduling.capacity_analytic[case=S2] |
| S3 容量比（解析 MST） | 1.081 | — | p3_scheduling.capacity_analytic[case=S3] |

## 6 P3 名义结果（α=1, β=0.5, 30 seeds）

| case | 策略 | 加权准时 | 95% CI 半宽 | 加权完成 | 加权拖期 (s) | 成本 | review | elapsed (s) | overrun (s) | idle (s) | censored | JSON 键 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | edf | 0.992 | ±0.008 | 1.000 | 0.5 | 22.76 | 0.0 | 75.3 | 15.0 | 7.4 | 0.00 | p3_scheduling.summary[case=S1,policy=edf,alpha=1.0,beta=0.5] |
| S1 | edf_rev | 0.992 | ±0.008 | 1.000 | 0.5 | 22.76 | 0.0 | 75.3 | 15.0 | 7.4 | 0.00 | p3_scheduling.summary[case=S1,policy=edf_rev,alpha=1.0,beta=0.5] |
| S1 | now | 0.973 | ±0.016 | 1.000 | 1.5 | 22.84 | 0.0 | 75.7 | 15.0 | 7.4 | 0.00 | p3_scheduling.summary[case=S1,policy=now,alpha=1.0,beta=0.5] |
| S1 | oracle | 0.992 | ±0.008 | 1.000 | 2.6 | 23.93 | 0.0 | 72.0 | 0.0 | 4.0 | 0.00 | p3_scheduling.summary[case=S1,policy=oracle,alpha=1.0,beta=0.5] |
| S1 | slack | 0.992 | ±0.008 | 1.000 | 1.8 | 22.78 | 0.0 | 75.4 | 15.0 | 7.4 | 0.00 | p3_scheduling.summary[case=S1,policy=slack,alpha=1.0,beta=0.5] |
| S1 | voi | 0.992 | ±0.008 | 1.000 | 1.8 | 22.78 | 0.0 | 75.4 | 15.0 | 7.4 | 0.00 | p3_scheduling.summary[case=S1,policy=voi,alpha=1.0,beta=0.5] |
| S2 | edf | 0.610 | ±0.075 | 0.864 | 46.4 | 29.53 | 0.0 | 97.5 | 20.6 | 9.5 | 0.30 | p3_scheduling.summary[case=S2,policy=edf,alpha=1.0,beta=0.5] |
| S2 | edf_rev | 0.603 | ±0.072 | 0.851 | 49.0 | 30.16 | 1.2 | 96.8 | 20.5 | 9.1 | 0.23 | p3_scheduling.summary[case=S2,policy=edf_rev,alpha=1.0,beta=0.5] |
| S2 | now | 0.590 | ±0.065 | 0.857 | 60.2 | 29.27 | 0.0 | 96.8 | 20.5 | 9.6 | 0.27 | p3_scheduling.summary[case=S2,policy=now,alpha=1.0,beta=0.5] |
| S2 | oracle | 0.910 | ±0.017 | 0.910 | 64.8 | 31.35 | 0.0 | 91.9 | 0.0 | 5.3 | 0.00 | p3_scheduling.summary[case=S2,policy=oracle,alpha=1.0,beta=0.5] |
| S2 | slack | 0.829 | ±0.031 | 0.879 | 67.6 | 29.49 | 0.0 | 96.9 | 20.4 | 9.4 | 0.30 | p3_scheduling.summary[case=S2,policy=slack,alpha=1.0,beta=0.5] |
| S2 | voi | 0.825 | ±0.034 | 0.869 | 72.8 | 30.18 | 0.7 | 97.1 | 20.2 | 9.4 | 0.37 | p3_scheduling.summary[case=S2,policy=voi,alpha=1.0,beta=0.5] |
| S3 | edf | 0.543 | ±0.048 | 0.835 | 126.8 | 37.12 | 0.0 | 121.6 | 25.8 | 12.1 | 0.27 | p3_scheduling.summary[case=S3,policy=edf,alpha=1.0,beta=0.5] |
| S3 | edf_rev | 0.535 | ±0.048 | 0.815 | 143.0 | 38.43 | 2.5 | 119.8 | 25.4 | 11.1 | 0.30 | p3_scheduling.summary[case=S3,policy=edf_rev,alpha=1.0,beta=0.5] |
| S3 | now | 0.503 | ±0.045 | 0.834 | 144.1 | 36.67 | 0.0 | 121.1 | 25.7 | 12.0 | 0.17 | p3_scheduling.summary[case=S3,policy=now,alpha=1.0,beta=0.5] |
| S3 | oracle | 0.841 | ±0.016 | 0.844 | 123.3 | 38.13 | 0.0 | 111.7 | 0.0 | 6.5 | 0.00 | p3_scheduling.summary[case=S3,policy=oracle,alpha=1.0,beta=0.5] |
| S3 | slack | 0.785 | ±0.028 | 0.848 | 149.2 | 35.96 | 0.0 | 119.7 | 26.8 | 12.2 | 0.07 | p3_scheduling.summary[case=S3,policy=slack,alpha=1.0,beta=0.5] |
| S3 | voi | 0.744 | ±0.034 | 0.822 | 166.5 | 36.63 | 1.7 | 118.7 | 27.0 | 11.5 | 0.10 | p3_scheduling.summary[case=S3,policy=voi,alpha=1.0,beta=0.5] |

### 6.1 配对差（相对 EDF，同一批采样 job）

| case | 策略 | 均值差 | 95% CI | JSON 键 |
| --- | --- | --- | --- | --- |
| S1 | edf_rev | +0.000 | ±0.000 | p3_scheduling.paired_vs_edf |
| S1 | now | -0.019 | ±0.010 | p3_scheduling.paired_vs_edf |
| S1 | oracle | +0.000 | ±0.000 | p3_scheduling.paired_vs_edf |
| S1 | slack | +0.000 | ±0.000 | p3_scheduling.paired_vs_edf |
| S1 | voi | +0.000 | ±0.000 | p3_scheduling.paired_vs_edf |
| S2 | edf_rev | -0.007 | ±0.010 | p3_scheduling.paired_vs_edf |
| S2 | now | -0.019 | ±0.025 | p3_scheduling.paired_vs_edf |
| S2 | oracle | +0.300 | ±0.068 | p3_scheduling.paired_vs_edf |
| S2 | slack | +0.219 | ±0.066 | p3_scheduling.paired_vs_edf |
| S2 | voi | +0.215 | ±0.067 | p3_scheduling.paired_vs_edf |
| S3 | edf_rev | -0.007 | ±0.007 | p3_scheduling.paired_vs_edf |
| S3 | now | -0.040 | ±0.014 | p3_scheduling.paired_vs_edf |
| S3 | oracle | +0.298 | ±0.040 | p3_scheduling.paired_vs_edf |
| S3 | slack | +0.243 | ±0.047 | p3_scheduling.paired_vs_edf |
| S3 | voi | +0.201 | ±0.049 | p3_scheduling.paired_vs_edf |

### 6.2 约束检查（名义 ≥0.50）

| case | 策略 | 均值 | 是否满足 | JSON 键 |
| --- | --- | --- | --- | --- |
| S1 | edf | 0.992 | 是 | p3_scheduling.constraint_nominal |
| S1 | edf_rev | 0.992 | 是 | p3_scheduling.constraint_nominal |
| S1 | now | 0.973 | 是 | p3_scheduling.constraint_nominal |
| S1 | oracle | 0.992 | 是 | p3_scheduling.constraint_nominal |
| S1 | slack | 0.992 | 是 | p3_scheduling.constraint_nominal |
| S1 | voi | 0.992 | 是 | p3_scheduling.constraint_nominal |
| S2 | edf | 0.610 | 是 | p3_scheduling.constraint_nominal |
| S2 | edf_rev | 0.603 | 是 | p3_scheduling.constraint_nominal |
| S2 | now | 0.590 | 是 | p3_scheduling.constraint_nominal |
| S2 | oracle | 0.910 | 是 | p3_scheduling.constraint_nominal |
| S2 | slack | 0.829 | 是 | p3_scheduling.constraint_nominal |
| S2 | voi | 0.825 | 是 | p3_scheduling.constraint_nominal |
| S3 | edf | 0.543 | 是 | p3_scheduling.constraint_nominal |
| S3 | edf_rev | 0.535 | 是 | p3_scheduling.constraint_nominal |
| S3 | now | 0.503 | 是 | p3_scheduling.constraint_nominal |
| S3 | oracle | 0.841 | 是 | p3_scheduling.constraint_nominal |
| S3 | slack | 0.785 | 是 | p3_scheduling.constraint_nominal |
| S3 | voi | 0.744 | 是 | p3_scheduling.constraint_nominal |

## 7 P3 敏感性（α, β）

| case | α | β | EDF | NOW | SLACK | ORACLE | JSON 键 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | 0.75 | 0.5 | 0.992 | 0.975 | 0.990 | — | p3_scheduling.summary |
| S1 | 1.0 | 0.0 | 0.992 | 0.975 | 0.992 | — | p3_scheduling.summary |
| S1 | 1.0 | 0.5 | 0.992 | 0.973 | 0.992 | 0.992 | p3_scheduling.summary |
| S1 | 1.0 | 1.0 | 0.990 | 0.965 | 0.990 | — | p3_scheduling.summary |
| S1 | 1.5 | 0.5 | 0.958 | 0.921 | 0.958 | — | p3_scheduling.summary |
| S2 | 0.75 | 0.5 | 0.711 | 0.685 | 0.857 | — | p3_scheduling.summary |
| S2 | 1.0 | 0.0 | 0.656 | 0.629 | 0.856 | — | p3_scheduling.summary |
| S2 | 1.0 | 0.5 | 0.610 | 0.590 | 0.829 | 0.910 | p3_scheduling.summary |
| S2 | 1.0 | 1.0 | 0.585 | 0.565 | 0.832 | — | p3_scheduling.summary |
| S2 | 1.5 | 0.5 | 0.421 | 0.393 | 0.756 | — | p3_scheduling.summary |
| S3 | 0.75 | 0.5 | 0.629 | 0.585 | 0.769 | — | p3_scheduling.summary |
| S3 | 1.0 | 0.0 | 0.581 | 0.537 | 0.795 | — | p3_scheduling.summary |
| S3 | 1.0 | 0.5 | 0.543 | 0.503 | 0.785 | 0.841 | p3_scheduling.summary |
| S3 | 1.0 | 1.0 | 0.529 | 0.483 | 0.769 | — | p3_scheduling.summary |
| S3 | 1.5 | 0.5 | 0.433 | 0.393 | 0.696 | — | p3_scheduling.summary |

### 7.1 review 增益敏感性

| case | 假设 MAE 增益 (s) | η | review 次数 | 成本 | seeds | JSON 键 |
| --- | --- | --- | --- | --- | --- | --- |

## 8 图

- `figures/fig1_keypoint_tracks.png`
- `figures/fig2_bad_ratio.png`
- `figures/fig3_segmentation.png`
- `figures/fig4_p2_error_vs_mask.png`
- `figures/fig5_p2_cost_tradeoff.png`
- `figures/fig6_p3_policy.png`
- `figures/fig7_reliability_roc.png`
- `figures/fig8_p2_crossover.png`

## 9 复跑

```powershell
$env:PATH = 'E:\Mini\envs\mathmodel;E:\Mini\envs\mathmodel\Library\bin;' + $env:PATH
E:\Mini\envs\mathmodel\python.exe code\run_all.py
```

`run_all.py` 依次跑 build_panel → p1_state → p1_model → p2_predict → p2_crossover → p2_interval → p3_schedule → make_numbers → verify_numbers。

VERDICT: PASS
