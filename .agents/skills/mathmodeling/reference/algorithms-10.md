# 十类算法清单（照《数模》2004 年第 1 期，董乘宇）+ 本机 Python 对应实现

原文 PDF：`E:\数学建模\refs\数学建模竞赛中应当掌握的十类算法.pdf`（5 页，2004 年，中国数学建模网）。
原文是「竞赛该掌握什么」的清单，不是教程；这里把它翻成**本机能跑的东西**，避免明天临时找库。

| # | 原文说法 | 原文字面工具 | 本机怎么落地（已装） |
|---|---|---|---|
| 1 | 蒙特卡罗 / 随机模拟 | MATLAB | `numpy.random.default_rng(seed)` + 自写抽样循环；敏感性用拉丁超立方向量 `rng.random` |
| 2 | 数据拟合、参数估计、插值 | MATLAB | `scipy.optimize.curve_fit`、`numpy.polyfit`、`scipy.interpolate.{CubicSpline,PchipInterpolator,lagrange,griddata}`、`statsmodels` 做参数区间 |
| 3 | 线性/整数/多目标/二次规划 | Lindo、Lingo | `scipy.optimize.{linprog,milp,minimize}`（HiGHS）、`ortools.linear_solver`/`sat`、`pulp`、`cvxpy` 不在本机 |
| 4 | 图论：最短路、网络流、二分图 | 手写 | `networkx`（Dijkstra/Floyd/Prim/max_flow/matching 全有）、`ortools.graph` 做大图 |
| 5 | 动态规划、回溯、分治、分支定界 | 手写 | 手写 DP 表（`functools.lru_cache` 或显式表）；分支定界交给 `milp` 的 B&B，不要自己写 |
| 6 | 模拟退火、神经网络、遗传算法 | MATLAB | `scipy.optimize.{anneal,dual_annealing,differential_evolution}`、`sklearn.neural_network.MLP*`；GA/PSO 用 `differential_evolution` 顶替，或按 `refs/contest-code` 里的 `.m` 翻写 |
| 7 | 网格法、穷举法 | 高级语言 | `itertools.product` + 向量化；先算规模 `(M+1)^N`，超过 1e7 就换 6 里的启发式 |
| 8 | 连续量离散化 | 手写 | `numpy.diff`（差分代微分）、`scipy.integrate.{simpson,trapezoid}`（求和代积分）、时间步长收敛性必须做（见下） |
| 9 | 数值分析：方程组、矩阵、积分 | MATLAB | `numpy.linalg.{solve,lstsq,eig}`、`scipy.linalg`、`scipy.integrate`、`scipy.sparse` |
| 10 | 图像处理 | MATLAB | `Pillow`、`scikit-image`（本机有）、`opencv-python`（视环境）；图上标注走我们自己的 `make_figures.py` |

## 原文里值得抄下来的两句判断

- 第 6 类（SA / 神经网络 / GA）：「算法的实现比较困难，需慎重使用」。对应到我们流水线就是
  **`G5` 的数值对账**：启发式方法必须给出「同一算例 3 次不同种子的结果离散度」，否则不许写进正文的结论句。
- 第 7 类（网格 / 穷举）：「计算量很大，最好在运算速度较快的计算机中进行」。对应到
  **`G10`（算力/规模软闸门）**：先把搜索空间规模算出来写进产物，再决定要不要降维。

## 与我们 20 道门的对应（明天用得上）

| 原文算法类 | 落在哪道门 |
|---|---|
| 1 蒙特卡罗、8 离散化 | 步长/样本量的收敛性写进 `out/02-solve.md`，`G5` 读它 |
| 3 规划、5 分支定界 | `milp` 必须报 `mip_gap` 与求解器名，`G4` 认这两个字段 |
| 6 启发式 | 多种子离散度 → `G5`；不可复现的随机种子 → `G15` 闭包查不到就判死 |
| 2 拟合/插值 | 拟合优度与参数区间进 `results_*.json`，`G12` 抽查 |
| 10 图像 | 图内文字 ≥6.2pt、不出 MediaBox → `G6` / `G18`；视觉审查 → `G11` |

## 一句话

这份 2004 年的清单在**算法分类**上没过时，在**工具**上整篇过时（它默认 MATLAB/Lingo）。
明天按右列用本机的 scipy / networkx / ortools / sklearn / statsmodels，不要为了「照着清单做」
去装 MATLAB 或 Lingo。