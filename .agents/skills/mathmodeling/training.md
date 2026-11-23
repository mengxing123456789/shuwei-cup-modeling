# 训练环节（training.md）

适用范围：模型解起来太慢、需要上万次求值（方差分解、全局敏感性、贝叶斯后验、随机规划），于是
用一份学到的替代品顶替求解器。**替代品的用途是让"用不起的分析"变得用得起，不是让结论变得好看。**

## 第 0 步：先算清楚需不需要训练

训练的成本必须与"不训练要多久"对得上，否则就是给自己找麻烦。

```
单次求解耗时 t_ms × 需要的求值次数 N = 总时间
```

本项目实测：CES 均衡求解 **8.14 ms/次**（16 进程分摊后）；Saltelli 设计 5,766,144 次/重复，
4 重复 → 精确求解约 **52 小时**。不可行，所以训练成立。

**反例**：如果只需 5,000 次求值（约 41 秒），训练 126 秒 + 写代码 + 加一层误差，纯属自伤。
先算，再决定。

## 第 1 步：数据设计

```python
from scipy.stats.qmc import LatinHypercube
rng = LatinHypercube(d=n_inputs, seed=SEED)
X = rng.random(n_points)                       # [0,1)^d
X = lo + X * (hi - lo)                         # 映到物理区间
```

**必须写进 meta JSON 的东西**：`n_requested`、`n_rows`、`n_train`、`n_val`、`n_test`、
`n_solver_failures`、`design`（含库名与种子）、`wall_seconds`、`ms_per_solve`、`workers`、
`input_bounds`（每个变量的 lo/hi）、`in_cols`、`out_cols`。

失败要记成 NaN 然后计数**并丢弃**，不许静默变成 0。本项目 80,000 点、0 失败。

**设计盒的选择是结论的一部分**：盒放错了，敏感性分析会报出假的零（见 `modeling.md` 的"伪零"）。

## 第 2 步：划分

```
固定置换种子 → 打乱 → 64,000 / 8,000 / 8,000
```

- 三划分必须**不相交**，且种子写进 JSON。
- 标准化统计量**只用训练集**：`Ytr.mean(0)` / `Ytr.std(0)`。用全量统计量 = 把测试集信息泄漏进训练，
  R² 会虚高，而且从任何结果里都看不出来。
- 保留验证集上最好的存档（`best_val_mse` 那一刻），**然后**才评测试集，测试集只评一次。

## 第 3 步：结构

小而稳的残差 MLP 够用：

```python
class ResBlock(nn.Module):
    def __init__(self, w, p):
        super().__init__()
        self.f = nn.Sequential(nn.Linear(w, w), nn.SiLU(), nn.Dropout(p), nn.Linear(w, w))
        self.n = nn.LayerNorm(w)
    def forward(self, x):
        return self.n(x + self.f(x))
```

- 输入先标准化，`Linear → ResBlock×depth → Linear`。
- AdamW `weight_decay=1e-5`，`CosineAnnealingLR(T_max=epochs)`，`clip_grad_norm_(5.0)`。
- **`T_max=epochs`**，别设成 60 而训 200 轮（那样后 140 轮学习率恒为 0）。
- 本项目选定 `width 256 / depth 4 / dropout 0.05 / lr 2e-3 / bs 512`，200 轮，RTX 4060 Laptop 上
  **126.3 s**。

## 第 4 步：两段式——搜索，然后重训

```
第一段：10 个配置 × 60 轮，按 best_val_mse 排序（记录每个配置的耗时）
第二段：冠军配置 × 200 轮，保留 best-val 存档
```

本项目第一段 **434.9 s**（10 个配置），第二段 126.3 s。两段耗时都要写进正文，不要只写第二段。

**报告全精度**：验证误差 2.057e-5 与 1.568e-5 在日志里都会打印成 `0.00002`，无法区分。正文给它
全精度，或在表脚注里说明"日志只保留五位小数，无法分辨"。

## 第 5 步：泛化检验（至少两件）

| 检验 | 做法 | 本项目结果 |
|---|---|---|
| k 折 | k=5，池化 train+val，测试集不参与任何一折 | mean 0.999981，sd 9.2e-6 |
| 多种子 | 冠军配置 ×3 种子（200 轮） | mean 0.999991，sd 2.5e-6 |
| 外推 | 训练集截到 σ≤6，测 σ>6 | 0.999989 → 0.999319（掉 6.7e-4） |

外推那一档要写清**用在哪、不用在哪**：本项目的所有结论都来自精确求解器，替代品只用于方差分解，
而方差分解的抽样范围在设计盒内。

## 第 6 步：R² 高到离谱时必须解释为什么

held-out R² 0.99998 读起来像"网络很强"，实际往往是**目标函数本身光滑**。必须给对照：

> 同一个测试集上，一个 55 项的全二次多项式已经到 0.997–0.9985，而网络有 533,771 个参数。

两个数一起报，读者才知道那 533,771 个参数买到的是什么（此处是 1,000 倍加速，不是 0.002 的精度）。

## 第 7 步：GPU 证据

**合格证据 = 训练进行中的采样**，不是事后的微基准。

```powershell
# logs/gpu_during_train.py：每秒一次，150 样本
nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader
```

与训练**并发**跑，输出落 `logs/gpu_during_train.txt`。本项目：131 个样本，**124 个**非零利用率，
峰值 **44%**、**190 MiB**、**19.88 W**；空闲基线 0 MiB / 15.7 W。

反例（被评审点名删掉）：训练结束四分钟后再跑一个 512×512 的 matmul，打印"CUDA 可用"——
那证明的是显卡能用，不是这次训练用了它。

## 第 8 步：独立复算，不信自己的 JSON

从 `.pt` 重新载入 `state_dict`，在测试集上前向，比对 JSON 里的每个输出。本项目 11 个输出
`max|ΔR²| = 0`。这一步同时能抓出"上次的 JSON 不是这份代码生成的"这类事故。

## 常见错误

| 现象 | 原因 | 修 |
|---|---|---|
| `mat1 and mat2 must have the same dtype` | numpy 的 `rng.random` 是 float64，模块是 float32 | 显式 `.astype(np.float32)` |
| Sobol 的 ST 加总 > 1.3 | 估计器样本不足或输入高度非线性 | 提高 N 或多重复取均值，报 SE |
| 训练中利用率只有个位数 | batch 太小，GPU 一直等数据 | 提高 bs 或加 `num_workers` |
| 200 轮里 128 轮损失 > 1e-4 | 学习率衰减太慢或 lr 太大 | 看损失曲线前 20 轮是否震荡 |
| 换个种子 R² 变到 0.99 | 单一划分 + 早停太早 | 加多种子检验，报 sd 而不是单值 |