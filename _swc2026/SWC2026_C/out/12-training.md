BYTES 2417
# 12 训练：GPU 模型与训练日志

队号 SWBMCM2634892。本文件只记录“训练了什么、用什么参数、结果多少”，不重复正文的模型推导。

## 0 环境

- GPU：**NVIDIA GeForce RTX 4060 Laptop 8.59 GB**
- torch **2.14.1+cu126**，CUDA 12.6，capability 8.9
- Python：`E:\Mini\envs\mathmodel\python.exe`（3.11.18）

## 1 P1a：分段（peak-distance）

- 选型规则：peak distance = 训练段时长 10 分位 = **54 帧（1.8 s）**；height 在 validation ARI 上选，取 **0.3**；test 只评一次。
- 结果：**test mean ARI 0.549、std 0.261、F1 0.607、boundary F1 0.195、boundary MAE 1.23 s（7 条记录）**。
- 对照：CPU 版 Ward 分段 ARI 0.414 / F1 0.561 → GPU 版把 ARI 抬到 0.549。

## 2 P1b：可靠性时序模型（TCN）

- 结构：TCN 4 blocks，dilations 1/2/4/8，96 通道，GroupNorm + GELU
- 输入：15 帧窗口（0.5 s），特征含 32 维状态 + 8 维几何
- 训练：18 epochs，batch 1024，lr 2e-3，seed 20261120，device cuda
- 用途：与 P1 的逻辑回归/马氏距离对照，验证“时序模型是否比手工特征更强”

## 3 P2：多步预测（GRU）

- 结构：GRU(128, 2 层) encoder + MLP multi-horizon head
- 输入：10 帧上下文（0.33 s）
- 训练：40 epochs，batch 512，lr 2e-3，seed 20261120，device cuda
- 结果：L=0.2 s 的 test RMSE = **1.38 cm**（ridge 基线 2.00 cm）；总训练耗时 **182.9 s**
- 说明：GRU 只在 L≤0.5 s 有明显优势，L≥1.0 s 与 ridge 打平——正文按这个结论写，没有夸大

## 4 P3：不需要训练的部分

P3 的调度策略（EDF/NOW/SLACK/VOI/ORACLE）是**规则 + 搜索**，不是神经网络：
- SLACK 的预留量由分位数回归给出，分位数在 train 上拟合
- VOI 用前缀回归的局部斜率估计“再看一次值不值”
- ORACLE 是“已知真实 p”的上界，仅作对照，不可部署

## 5 训练与复现

```powershell
$env:PATH = 'E:\Mini\envs\mathmodel;E:\Mini\envs\mathmodel\Library\bin;' + $env:PATH
E:\Mini\envs\mathmodel\python.exe code\train_gpu_p1b.py
E:\Mini\envs\mathmodel\python.exe code\train_gpu_p2.py
E:\Mini\envs\mathmodel\python.exe code\p1a_gpu_segmentation.py
```

每次训练都固定 seed 并把 `best_val_epoch` 写进 JSON；test 只在选型完成后评一次（`data/p1a_gpu_segmentation_final.json` 的 `_meta` 里写着这条规则）。

VERDICT: PASS
