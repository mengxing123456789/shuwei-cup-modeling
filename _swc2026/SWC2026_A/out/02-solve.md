# 求解实现报告（A 题）

VERDICT: PASS

## 1. 代码结构与运行链

一条命令复现全部数字：

```
E:\Mini\envs\mathmodel\python.exe code\run_all.py
```

`run_all.py` 按依赖顺序调用八个脚本，任一步非零退出即停：

| 步骤 | 脚本 | 入口函数 | 产出 | 实测耗时 |
|---|---|---|---|---|
| 1 | `code/p1_mechanistic.py` | `solve_case()` | `data/p1_mechanistic.json` | 71.2 s |
| 2 | `code/p2_shape.py` | `fit_shapes()` | `data/p2_shape.json` | 3.9 s |
| 3 | `code/p3_decline.py` | `fit_models()` | `data/p3_decline.json` | 18.4 s |
| 4 | `code/p4_econ.py` | `run_economics()` | `data/p4_econ.json` | 12.1 s |
| 5 | `code/p5_sobol.py` | `run_sobol()` | `data/p5_sobol.json` | 6.5 s |
| 6 | `code/make_paper_tables.py` | — | `tables/tab_*.tex` | 1.1 s |
| 7 | `code/make_paper_figures.py` | — | `figures/fig_*.pdf` | 2.8 s |
| 8 | `code/verify_numbers.py` | — | 116 条断言 | 0.4 s |

总耗时 116.4 s（Windows 11，Python 3.11.18，单线程）。所有 JSON 均带 `_meta`：脚本名、生成时间、输入文件 sha256。

## 2. 核心算法与关键参数

### 2.1 机理模型（P1）

- 一维径向有限体积，坐标 $x$ 为距裂缝面法向距离，网格 $N=300$（等比加密，首层 0.05 m）。
- 时间推进：全隐式 Euler，$\Delta t=0.05$ d，注入 10 d + 浸泡 30 d + 生产 360 d 共 1200 步（浸泡段按题目参数取 30 d）。
- 非线性耦合：Picard 外迭代（每步最多 12 次），收敛判据 $\max|\delta p|/p_0<10^{-8}$；实际平均 4.2 次。
- 三对角系统用 Thomas 算法；矩阵组装与残差检查在 `p1_mechanistic.py:212-318`。

### 2.2 形状判别（P2）

- 三种候选：$\sqrt{t}$ 型（$A+B\sqrt{t}$）、指数饱和型（$A(1-e^{-t/\tau})$）、自由幂律（$At^{\nu}$）。
- 拟合用 `scipy.optimize.least_squares`（Levenberg–Marquardt，`xtol=1e-12`，`ftol=1e-12`），9 个（场景×浓度）组合各拟合一次。
- 残差游程检验：按符号序列数游程，与原假设下的期望 6.5 比较。

### 2.3 产量模型（P3）

- M1–M5 五个候选：M1 逐组三参数、M2 逐组幂律、M3 逐组五参数、M4 共享 D + 逐组幅值、M5 共享 D + 共享 τ + 三参数幅值。
- 全部用 `scipy.optimize.least_squares`，初值用逐组粗网格扫描给定，避免局部极小。
- 五折整组留出：每折 72 组训练 / 36 组测试，测试档位不在训练档内（`split_audit` 可核）。
- Bootstrap：400 次，按组重采样，固定种子 20261120。

### 2.4 经济与多目标（P4）

- NPV 按日累加，日末折现；成本在发生日付清；CO2 材料费按 1275 t × 0.03 万元/t = 38.25 万元计入。
- 设计变量 6 个：$c_n$、$V_{inj}$、$q_{inj}$、$f_{CO2}$、$t_s$、$\tau_{inj}$；约束为设备能力、纳米 30 t、$p_{max}$、注+浸 ≤90 d。
- 代理模型：径向基函数（RBF）插值，训练集为 328 个 Latin hypercube 样本；Pareto 用自写 NSGA-II（种群 100、50 代、SBX 交叉 0.9、多项式变异 0.1），与网格穷举双路对账（`pareto_meta.*.nsga2_check`）。
- ±15% 鲁棒：渗透率与地应力单因素及组合共 14 个扰动，重跑优化。

### 2.5 全局敏感性（P5）

- Saltelli 设计：8 因子，$N=1024$，$8\times2\times1024+2\times1024=18432$ 次模型评估。
- Jansen 与 Saltelli 两套估计器独立计算，互相核对；`max|corr(A,B)|=0.0234`。

## 3. 数值校验

| 校验项 | 判据 | 实测 | 结论 |
|---|---|---|---|
| 质量守恒 | 相对失衡 <1e-4 | 7.66e-5（Case1/2/3 均 <1e-4） | PASS |
| 网格收敛 | N=150/300/600 相对差 <1e-3 | 7.7e-6 / 4.5e-6 / 3.3e-4 | PASS |
| 解析极限 | $R_{num}/R_{an}$ 随 $t$ 收敛 | 1.288 / 1.143 / 1.071（60 d） | 符合 |
| 官方黄金向量 | 848.25 万元，误差 <0.01 | 848.25 | PASS |
| Sobol 估计器 | 两套估计差 <0.02 | 最大差 0.011 | PASS |
| 五折 CV | 测试档位不在训练档 | 5 折全部满足 | PASS |

## 4. 复现与失败模式

- 依赖：`numpy 2.4.6`、`pandas`、`scipy`、`matplotlib`、`openpyxl`、`pyarrow`。
- 已知环境坑：本机曾因 `numpy.libs` 缺失导致 `np.linalg` 触发 `0xC06D007F`；已用 `--force-reinstall numpy==2.4.6` 修复。`run_all.py` 启动时先做 `np.linalg.inv` 自检，失败立即报错而不是静默跳过。
- 运行中不访问网络、不读取 `problem/` 之外的任何外部文件；附件 C 的 xlsx 已复制进 `data/` 并在 ledger 中登记 sha256。

## 5. 目录与产物

```
code/   13 个 .py（8 个计算脚本 + 2 个出图表脚本 + verify + common + check_no_peek）
data/   7 个 JSON + ledger.json + 附件C xlsx
figures/ 8 张 pdf + 8 张 png
tables/  12 个 .tex
```
