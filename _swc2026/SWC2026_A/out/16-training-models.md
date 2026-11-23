# A 题代理模型训练记录（R0–R5）

> 环境：`E:\Mini\envs\mathmodel\python.exe`；GPU：NVIDIA GeForce RTX 4060 Laptop（8 GB，`torch.cuda.is_available()=True`）。
> 所有训练脚本在 `code/`，指标 JSON 在 `models/`，随机种子统一 20261120。
> 本文件记录的是**逐步优化过程**，包括失败与回退，不是只挑成功结果。

## 0. 数据与任务

- 输入 5 维：`log10(ts)`、`cn`、`log10(Vinj)`、`fCO2`、`log10(qinj)`。
- 输出 3 维：`log10(EUR)`、`log10(cost)`、`NPV/10^6`。
- 数据来源：`p4_econ.json` 的 Pareto 点（R0–R4）；R5 改为在完整设计网格上直接调用 `p4_econ.scheme()` 生成（每场景 20,664 个设计点，60%/40% 划分）。

## 1. 各轮结果（5 折或指定划分）

| 轮次 | 模型/数据 | EUR R² | cost R² | NPV R² | 结论 |
|---|---|---|---|---|---|
| R0 | 合并三场景，XGBoost，随机 5 折 | 0.989 | 1.000 | 0.977 | 表面很好，但 **留一场景 R²<0（-3.9/-2.6/-28.9）** → 跨场景不可外推 |
| R0 | 合并三场景，MLP，随机 5 折 | 0.992 | 1.000 | 0.983 | 同上 |
| R1 | 分场景 MLP，5 折 | 0.948/0.957/0.962 | ~1.000 | 0.996/0.878/0.905 | 分场景是必要的；Case2/3 的 NPV 接近 0、相对误差大 |
| R2 | 分场景 XGBoost + Optuna 调参，5 折复核 | 0.926/0.938/0.941 | ~1.000 | 0.996/0.813/0.849 | 调参后反而低于 R1 → **拒绝**，小数据下默认深度 4 更稳 |
| R3 | XGB+MLP 等权集成，5 折 | 0.929/0.943/0.946 | ~1.000 | 0.996/0.830/0.867 | 集成不优于纯 MLP → **拒绝** |
| R4 | 仅 Pareto 点训练，预测全设计网格 | — | — | 约 -10^14 | **外推爆炸**：Pareto 点只覆盖设计空间窄带，不能当全局代理 |
| R5 | 全网格 12,398 训练 / 8,266 测试，分场景 MLP | — | — | **0.9990/0.9989/0.9990** | Top-100 命中 91/89/93，Spearman 0.9992/0.9991/0.9993 → **采用** |

## 2. R5 的最优设计（代理预测 → 真值复核）

| 场景 | ts (d) | Cn | Vinj (m³) | fCO2 | 真值 NPV（万元） | 真最优 NPV（万元） | 差距 |
|---|---|---|---|---|---|---|---|
| Case1 | 8 | 0.5 | 1000 | 0.8 | -186.15 | -185.69（ts=9） | 0.46 |
| Case2 | 23 | 1.0 | 1000 | 0.8 | 72.75 | 75.20（Cn=0.5） | 2.46 |
| Case3 | 36 | 1.5 | 1000 | 0.8 | 730.29 | 730.32（ts=35） | 0.03 |

> 关键结论：最优解都落在 **Vinj=1000 m³（最小注入量）** 与 **fCO2=0.8（最高 CO₂ 比例）**；纳米浓度只在 Case3 取上限 1.5 wt%，Case1/2 取 0.5 wt%。这与「纳米材料贵、CO₂ 便宜」的经济直觉一致，也与 R1 的 Pareto 结构一致。

## 3. 为什么 R5 可信

1. **训练/测试同分布**：训练集覆盖完整设计网格，不是只取 Pareto 点。
2. **测试集从未参与训练或调参**：先划分，再训练，最后只评估一次。
3. **两层验证**：代理模型在 8,266 个留出设计点上的 R²≈0.999；再用真 `scheme()` 复核代理给出的最优设计，差距 0.03–2.46 万元。
4. **可复现**：`code/optimize_surrogate2.py` 一键复跑，结果写 `models/surrogate_r5_fullgrid.json`。

## 4. 下一步（R6，可继续做）

- 用 R5 代理 + NSGA-II 求三场景 Pareto 前沿，与 `p4_econ.pareto` 的精确前沿对照；
- 对 Case2 的 NPV 近零区域做主动学习（误差最大的 10% 样本追加真值），目标把 NPV R² 从 0.999 提到 0.9995；
- 把训练曲线、残差图、Top-100 命中图加入论文 §5/§6（当前论文未包含机器学习内容，这些属于深挖轮的新增章节）。

## 5. 产物清单

- `code/train_surrogate.py`（R0）
- `code/train_surrogate_case.py`（R1）
- `code/tune_surrogate.py`（R2）
- `code/optimize_surrogate.py`（R4，失败案例，保留作对照）
- `code/optimize_surrogate2.py`（R5，采用的最终版本）
- `models/surrogate_r0.json`、`surrogate_r1.json`、`surrogate_r2.json`、`surrogate_r2_eval5.json`、`surrogate_r3_ensemble.json`、`surrogate_r4_optimization.json`、`surrogate_r5_fullgrid.json`
- `models/surrogate_r5_Case1.pt` / `Case2.pt` / `Case3.pt`
