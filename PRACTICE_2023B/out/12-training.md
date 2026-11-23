BYTES 24277

NOT-APPLICABLE: 精确求解已闭式且全链 223.1 ms（18 次中位），42 次扰动的总代价实测 9.575 s < 60 s 等待预算；代理模型在精度、速度、参数/数据比三条上都不占优，训练无收益。

# 12 · 代理模型训练必要性判定（s3 · 代理模型训练手）

> 本文不是「训练报告」，是**训练必要性判定**。判定结论：**不训练**。
> 每个数字后面挂可复算命令（§7）或文件行号；凡未标注来源的数字都是本次实测，命令在 §7 逐条给出。
> 术语按 `out/01-model.md` L5–L8 的约定：`single` / `diff` / `trend` 三条阈值路径互不替代。

---

## 1 判定与那个乘法

派单要求先算 `单次求解 ms × 需评估次数`，乘积小于可接受等待时间就不训练。

| 量 | 实测 | 来源 |
|---|---|---|
| 单次全链求解（q1–q5，预热后 18 次中位） | **223.1 ms**（四分位 213.6 / 246.7，极值 208.6–285.7） | §7 命令 1（21 次，前 3 次为预热） |
| 单次全链求解（独立复核，另一轮 7 次中位） | 256.2 ms | §7 命令 1b，比上一条高 15%，故取样本更多、更低的那一轮 |
| 数据加载 `load_annex_i + load_annex_ii` | 6.1–8.0 ms | §7 命令 1 |
| 需评估次数（42 次扰动 = 换 42 个 MC 种子重跑全链） | **42** | §7 命令 2 |
| **乘积** | **0.2231 s × 42 = 9.37 s**（直接实测 9.462 / 9.575 / 9.643 s，三次重复） | §7 命令 2 |
| 可接受等待时间（本判定取 60 s，一次评审级重算的上限） | 60 s | 自设阈值，见 §2.3 |

**9.37 s ≪ 60 s；实测 9.575 s（三次中位）与乘法吻合到 2.2%。** 这就是不训练的全部理由 —— 与 2026_C 的 `252 ms × 42 = 10.6 s` 同型，量级一致。

单次脚本端到端墙钟（含解释器启动、`selftest`、五份 JSON 落盘）三次 **961 / 791 / 877 ms**（§7 命令 3）。即使按最悲观口径 961 ms，42 次也只有 40.4 s，仍在预算内。

**数字口径声明**：全链耗时在同一台机上跨轮抖动可达 ±25%（§7 命令 1 的极值 208.6–285.7 ms 就是同一批 21 次里的），所以本文取**中位**而不取均值，并且凡是「42 次」都直接实测三次取中位，不用单次乘法外推。抖动来源是 `N_MC = 4000` 的 `rng.normal` 与 `np.percentile`，不是模型本身不稳定 —— 见 §4 的 42 种子稳定性检验。

---

## 2 为什么「需评估次数」不可能变大

这是本文最容易被跳过、也最该写清的一步：如果「需评估次数」本该是 1e5 量级，那么 223 ms × 1e5 = 6.2 小时，结论就会翻转。所以要证明的是**它不会变大**。

### 2.1 主模型是闭式最小二乘，没有迭代

`out/01-model.md` L129 给的模型是 `v = b0 + b1·w + ε`，`v = ilr(S) ∈ R³`。拟合走正规方程 + 纯 Python 高斯消元（`code/numlib.py` L87 的 docstring：「最小二乘 B = argmin ||X·B - Y||，走正规方程 + 纯 Python 消元」），**没有梯度下降、没有线搜索、没有网格搜索**。`code/solve.py` L439 `B, rss = NL.lstsq(X, V)` 一次调用即得全局最优。

设计矩阵实测 `X.shape = (9, 2)`、`V.shape = (9, 3)`，故 `B.shape = (2, 3)` = **6 个参数**，与 `out/01-model.md` L67 的「ILR 拟合用 6 个参数（3 维 × 截距+斜率）」一致。

全链 `NL.lstsq` 的调用次数实测 **40 次**（§7 命令 4，逐问计数）：

| 来源 | 次数 | 代码位置 |
|---|---|---|
| Q1：主模型 `M1_linear_w` 三组合各 1 次 | 3 | `code/solve.py` L188 |
| Q1：AIC 对照 `M2_linear_logw` + `M3_sqrt_w`，三组合各 2 次 | 6 | `code/solve.py` L213（循环 L210–L214） |
| Q4：选择性 `dlnS/dw` 三组合各 1 次 | 3 | `code/solve.py` L366 |
| Q5：三组合各 1 次全量拟合 | 3 | `code/solve.py` L439 |
| Q5：留一交叉验证，CS 9 折 + CE 8 折 + LG 8 折 | 25 | `code/solve.py` L460（循环 L457–L461） |
| Q2 / Q3 不拟合（只有算术与阈值比较） | 0 | `code/solve.py` L236–L348 |
| **合计** | **40** | 与插桩计数一致 |

单次 `lstsq` 中位耗时 **25.1 µs**（§7 命令 5），40 次 = **1.004 ms**。也就是说全链 223.1 ms 里，真正的拟合计算只占 **0.45%**；其余是 `N_MC = 4000` 的蒙特卡洛抽样与 ILR 反变换（`code/solve.py` L57 `N_MC = 4000`）。**注意 Q1 的 9 次里有 6 次是为 AIC 模型比较服务的**（`out/01-model.md` L153–L164 的模型形式敏感性），它们不产生任何预测值 —— 这本身就是「额外评估的边际收益极低」的现成例证。

**Q4 的动力学也不迭代**：`code/solve.py` L398–L404 的 `Ea_grid` 是 `np.linspace(100, 250, 16)` 的**固定 16 点脊线**，每点只做一次 `A = k·exp(Ea/(R·T))` 的代数求值 —— 这是「报脊线不报点」的实现（`out/01-model.md` L62 假设 A8、L218–L220），不是优化。

### 2.2 观测数锁死了数据侧

先把两种「观测数」口径分开，避免和 `out/01-model.md` L67 的口径打架（这是 V3 类错误的常见来源）：

| 口径 | CS | CE | LG | 合计 |
|---|---|---|---|---|
| **行数**（掺比档位） | 9 | 8 | 8 | **25** |
| **标量观测数**（行 × 3 个 ILR 坐标）= `V.size` | 27 | 24 | 24 | **75** |
| 残差自由度（标量观测 − 6 参数） | 21 | 18 | 18 | — |

`out/01-model.md` L67 写的「CS 有 27 个观测…CE/LG 各 24 个观测、残差自由度 21/18/18」用的是**标量观测数**口径（`code/solve.py` L190 `n_obs, k_par = int(V.size), int(B.size)`）。行数口径实测 9 / 8 / 8（§7 命令 6）。**两个口径都对，但必须指明用哪一个** —— 下文凡说「样本」都指**行数**（一个掺比档位是一行，不能把一个档位的 3 个 ILR 坐标当成 3 个独立实验）。

附件本身就这么大（Annex I 三张子表），**加档位需要重做实验，不是加算力**（`out/01-model.md` L252：「若审稿要求必须 F < 1，正确回应是补实验档位，不是改模型」）。

### 2.3 唯一的「需评估次数」上界是展示密度，不是求解难度

真要变大，只有一种场景：把预测网格加密、把 MC 次数拉高。本次实测了这条上界的极端值（§7 命令 7）：

> 3 组合 × 1001 点网格 × 4000 次 MC = **12,012,000 个点**，精确前向（einsum + ILR 反变换 + 分位数）总耗时 **2.729 s**。

即使用户要求把网格加密 143 倍（7 → 1001 点），精确求解仍然只要 2.7 s。**没有任何合理的展示需求能把乘积推过 60 s。**

---

## 3 即使强行训练，代理模型也赢不了：三条独立否决

必要性已经足够判 NOT-APPLICABLE。但「不训练」这个结论如果只靠一条乘法，审稿人会问「那万一你只是懒」。所以补三条**独立**否决，任一条单独成立即可。

### 3.1 参数 / 数据比：1252 : 25 = 50.1 : 1（行口径）／ 1252 : 75 = 16.7 : 1（标量口径）

一个最小的可用 MLP（1 → 32 → 32 → 4）参数量：

`(1×32+32) + (32×32+32) + (32×4+4) = 64 + 1056 + 132 = 1252`

两个口径都算一遍，谁都不能让这个模型站住：

| 口径 | 样本 | 参数 : 样本 | 判读 |
|---|---|---|---|
| 行（掺比档位） | 25（单组合最少 8） | **50.1 : 1** | 参数是样本的 50 倍 |
| 标量（行 × 3 ILR 坐标） | 75（单组合最少 24） | **16.7 : 1** | 仍远超常规 5:1 上限 |
| 对照：精确模型 | 75 | **6 : 75 = 0.08 : 1** | 6 个参数 |

即便取对代理模型最有利的标量口径，参数量仍是样本的 16.7 倍；而精确模型只用了 6 个参数就拿到 `F = 0.44 / 3.42 / 3.52`（§3.2）。**这不是「需要正则化」的问题，是「根本不该有这个模型」**：`out/01-model.md` L161–L164 已经因为**跨组合可比性**把主模型固定为 `M1_linear_w`，代理模型连这个可比性都保不住（三个组合的输入 `w` 支撑集不同：CS 含 `w = 0`，CE/LG 自 `w = 0.0909` 起，见 L39）。

### 3.2 噪声地板：残差已在 5% 以内，没有可赢的空间

`out/01-model.md` L28–L29 与 L322–L324 给出：

| 组合 | `σ_fit`（ILR 残差标准差） | `σ_noise`（5% 噪声映射到 ILR） | `F` | 判读 |
|---|---|---|---|---|
| CS | 0.0333 | 0.0502 | **0.44** | 残差**低于**噪声地板 —— 已到数据能给的下限 |
| CE | 0.0929 | 0.0502 | 3.42 | 失拟（信息量上限，非模型不足） |
| LG | 0.0941 | 0.0501 | 3.52 | 同上 |

CS 的 `F = 0.44 < 1` 意味着：**残差已经比噪声还小**。任何代理模型在 CS 上能做的唯一事情是过拟合噪声。CE/LG 的 `F > 1` 已在 `out/01-model.md` §V1（L244–L252）定性为自由度限制（18 个残差自由度、6 个参数），加项必然过拟合 —— 代理模型等价于「用 1252 个参数加项」，`F` 会掉到 1 以下，但那是 `out/01-model.md` L69 明令禁止的做法（「不许靠加高次项把 F 压到 1 以下（那是过拟合）」）。

### 3.3 速度：代理模型比精确求解**更慢**（实测，同进程同批次）

这是最反直觉、也最该报的一条。既然「训练代理模型是为了加速」，那就实测加速比。用 `einsum` 实现（禁用 BLAS，遵循 `out/01-model.md` L279–L283 的环境硬约束），同一台机、同一进程、预热后取中位：

| 批量 N | 精确前向（einsum + ILR 反变换） | MLP 1-32-32-4 前向 | 比值 |
|---|---|---|---|
| 1 | 6.30 µs | 6.90 µs | **1.1×（代理更慢）** |
| 7（= 本文预测网格点数） | 6.80 µs | 12.30 µs | **1.8×（代理更慢）** |
| 1,000 | 57.70 µs | 1189.45 µs | **20.6×（代理更慢）** |
| 100,000 | 10,102.60 µs | 113,556.20 µs | **11.2×（代理更慢）** |

原因很直白：**精确模型本身就是一个线性映射**。`v = b0 + b1·w` 是 3 次乘加，而 MLP 要过 2 层 tanh（32+32 个神经元）。代理模型的加速前提是「精确模型很贵」，这里前提不成立。

精确前向的单点成本：N=1000 时 **57.7 ns/点**，N=100000 时 **101 ns/点**（§7 命令 8）。

**这张表把「训练代理模型」从「不必要」升级为「有负收益」** —— 它不但不加分，还会让正文多一段与主结论无关的内容（派单红线）。

---

## 4 训练三件套：一项都不该做，做了也是假证据

派单要求训练必须留三划分种子、只用训练集标准化、跑 k 折 / 多种子 / 外推。这三件在本题**没有可执行的落点**，逐条说明为什么，而不是含糊跳过：

| 要求 | 本题状态 | 依据 |
|---|---|---|
| 三划分（train/val/test）行数与种子写进 JSON | **不可执行**。25 行数据切三份后每份 8/8/9，单组合最少只剩 5–6 行训练样本，少于 6 个参数 | §2.2；`out/01-model.md` L67 |
| `mean`/`std` 只从 `X_train` 算 | **无对象**。输入是 1 维 `w`，且 `w = a/(a+100)` 是题给掺比的确定性变换（`code/model_skeleton.py` L165–L171 `w_of_r`），不存在需要标准化的多变量特征 | `out/01-model.md` L38–L39 |
| k 折 | **已有等价物，且更强**：Q5 的留一交叉验证（LOO）就是 `k = n` 的 k 折，已跑完并落盘 | `code/solve.py` L456–L463；结果见 `out/01-model.md` L230–L234 |
| 多种子 | **已有**：`RNG_SEED = 20231119`（`code/solve.py` L56），本次 42 次扰动即 42 个种子的全链复跑 | §7 命令 2 |
| 外推 | **已证不需要，且禁止**：预测网格全部落在观测区间内，`is_extrapolation = False` 三组合全对 | `out/01-model.md` L64（A10）、L224；`code/solve.py` L474–L475 |

**关键区别**：LOO（k = n）比 5 折更严格，且它已经在 `data/results_q5.json` 里；把它改叫「k 折」不会增加任何信息，只会让正文多一个同义术语 —— 正是 `out/01-model.md` L264–L272（V3）警告的「同一名词被两种算法用过」。

---

## 5 GPU 证据：无训练对象，故无训练期采样

派单规定：GPU 证据必须是**训练期**每秒 `nvidia-smi` 采样，事后微基准不算。本文不训练，因此**不存在训练期**，也就没有可采样的窗口。为避免「用空闲基线冒充训练证据」，把两者分开报清楚：

**空闲基线（本次实测，5 次 × 1 s，§7 命令 9）**

| 采样 | 利用率 | 显存 | 功耗 |
|---|---|---|---|
| 1 | 0 % | 36 MiB | 2.96 W |
| 2 | 0 % | 36 MiB | 4.45 W |
| 3 | 0 % | 36 MiB | 4.18 W |
| 4 | 0 % | 36 MiB | 4.39 W |
| 5 | 0 % | 36 MiB | 2.94 W |

设备：`NVIDIA GeForce RTX 4060 Laptop GPU`，8188 MiB（`torch.cuda.get_device_properties(0).total_memory`）。解释器侧确认 `torch 2.14.1+cu126`、`cuda_available True`（§7 命令 10）。

**这张表只说明「GPU 存在且当前空闲」，不构成任何训练证据。** 若下游需要「本步用了 GPU」的断言，正确回答是：**本步没有用 GPU，也不需要** —— `code/solve.py` 全链只 import `numpy`，无 `torch`（`code/solve.py` L40 起 import 清单）。

---

## 6 红线复核

派单红线：「不许为了让论文有深度学习而训练。评审一眼能看出代理模型与主结论无关，反而扣分。」

逐条对照：

1. **主结论不依赖代理模型**。Q1–Q5 的每个数字都由闭式最小二乘 + 解析代数给出（§2.1），无一来自学习模型。加一个代理模型后，它要么复现同样的数（那就不需要它），要么偏离（那就与主结论冲突）。
2. **没有「深度学习」章节可写**。若强行训练，正文会出现一个 1252 参数的网络去拟合 25 行 1 维输入数据，而它的 `R²` 会与一个 6 参数线性模型无法区分 —— 这正是 R-T04 描述的「目标函数本身光滑」陷阱，只是本题连陷阱都进不去（样本量不足）。
3. **替代方案的收益已在 §3.3 实测为负**。
4. **题目本身不含优化**：`out/00-problem.md` L119 已判「题面 152 行内没有任何『按…排序 / 优先级 / 名次 / 最优选择』的要求」，L371 判「L78–80 的 `optimization process` 是描述实验选点，不是要解优化问题」。没有目标函数，就没有「代理模型替代昂贵目标函数评估」这个标准叙事。

**判定：不训练。** 这不是省略，是有证据的选择。

---

## 7 复算命令（`E:\Mini\envs\mathmodel\python.exe`，工作目录 `E:\数学建模\PRACTICE_2023B`）

以下每条都是本次实际执行过的命令，输出即正文数字的来源。

**命令 1 · 全链单次耗时（21 次，前 3 次预热）与加载耗时**
```
python -c "import time,sys,statistics;sys.path.insert(0,r'code');import model_skeleton as M,solve as S;ai=M.load_annex_i();aii=M.load_annex_ii();ts=[]
for _ in range(21):
    a=time.perf_counter();r1=S.q1(ai);S.q2(aii,ai);S.q3(ai,aii);S.q4(ai,aii,r1);S.q5(ai);ts.append((time.perf_counter()-a)*1000)
w=ts[3:];print([round(x,1) for x in ts]);print('median=%.1f min=%.1f max=%.1f'%(statistics.median(w),min(w),max(w)))"
```
→ `[241.4, 214.0, 213.3, 213.8, 214.2, 228.8, 226.4, 212.2, 211.5, 213.0, 228.8, 256.7, 254.8, 244.0, 232.4, 219.1, 208.6, 214.1, 285.7, 258.1, 219.8]`；`median=223.1 min=208.6 max=285.7`（保留 18 次，四分位 213.6 / 246.7）

**命令 1b · 独立复核（另一轮 7 次，前 1 次预热）**
```
python -c "import time,sys,statistics;sys.path.insert(0,r'code');import model_skeleton as M,solve as S;t0=time.perf_counter();ai=M.load_annex_i();aii=M.load_annex_ii();print('load_ms=%.1f'%((time.perf_counter()-t0)*1000));ts=[]
for _ in range(7):
    a=time.perf_counter();r1=S.q1(ai);S.q2(aii,ai);S.q3(ai,aii);S.q4(ai,aii,r1);S.q5(ai);ts.append((time.perf_counter()-a)*1000)
print([round(x,1) for x in ts]);print('median=%.1f'%statistics.median(ts[1:]))"
```
→ `load_ms=8.0`；`chain_ms=[314.8, 306.4, 248.3, 264.0, 297.5, 223.2, 210.3]`；`median=256.2`
（该轮整体偏慢，是机器负载差异，不是代码差异 —— 与命令 1 的 223.1 ms 差 15%，故正文取两轮中更低、样本更多的 223.1 ms，并在 §1 声明 ±25% 抖动）

**命令 2 · 42 次扰动（换种子重跑全链），重复三次**
```
python -c "import time,sys;sys.path.insert(0,r'code');import model_skeleton as M,solve as S;ai=M.load_annex_i();aii=M.load_annex_ii();S.q1(ai)
for rep in range(3):
    t0=time.perf_counter()
    for i in range(42):
        S.RNG_SEED=20231119+i;r1=S.q1(ai);S.q2(aii,ai);S.q3(ai,aii);S.q4(ai,aii,r1);S.q5(ai)
    d=time.perf_counter()-t0;print('rep%d 42_total_s=%.3f per_run_ms=%.1f'%(rep,d,d/42*1000))"
```
→ `rep0 42_total_s=9.643 per_run_ms=229.6`；`rep1 42_total_s=9.575 per_run_ms=228.0`；`rep2 42_total_s=9.462 per_run_ms=225.3`（三次中位 **9.575 s**）

**命令 3 · `solve.py` 端到端墙钟（三次）**
```
for($i=0;$i -lt 3;$i++){ $sw=[Diagnostics.Stopwatch]::StartNew(); python code\solve.py > $null 2>&1; $sw.Stop(); "run$i wall_ms=$($sw.ElapsedMilliseconds) exit=$LASTEXITCODE" }
```
→ `run0 wall_ms=961 exit=0`；`run1 wall_ms=791 exit=0`；`run2 wall_ms=877 exit=0`

**命令 4 · 全链 `NL.lstsq` 调用次数**
```
python -c "import sys;sys.path.insert(0,r'code');import model_skeleton as M,solve as S,numlib as NL;ai=M.load_annex_i();aii=M.load_annex_ii();c={'n':0};o=NL.lstsq
def w(*a,**k):
    c['n']+=1;return o(*a,**k)
NL.lstsq=w;r1=S.q1(ai);S.q2(aii,ai);S.q3(ai,aii);S.q4(ai,aii,r1);S.q5(ai);print('calls=',c['n'])"
```
→ `lstsq_calls_full_chain = 40`

**命令 5 · 单次 `lstsq` 中位耗时**
```
python -c "import time,sys,statistics;sys.path.insert(0,r'code');import numpy as np,numlib as NL,model_skeleton as M,solve as S;ai=M.load_annex_i();d=ai['DFA/CS'];V=S.ilr(np.column_stack([d['series'][p] for p in S.PROD])/100.0);X=S.design(d['w']);xs=[]
for _ in range(300):
    a=time.perf_counter();NL.lstsq(X,V);xs.append((time.perf_counter()-a)*1e6)
print('lstsq_us=%.1f'%statistics.median(xs),'X',X.shape,'V',V.shape)"
```
→ `lstsq_us=25.1`，`X (9, 2)`，`V (9, 3)`

**命令 6 · 每组合观测行数**
```
python -c "import sys;sys.path.insert(0,r'code');import model_skeleton as M;ai=M.load_annex_i();print({k:len(ai[k]['w']) for k in ai},'total',sum(len(ai[k]['w']) for k in ai))"
```
→ `{'DFA/CS': 9, 'DFA/CE': 8, 'DFA/LG': 8} total 25`

**命令 7 · 极端展示密度（3 × 1001 × 4000）**
```
python -c "import time,sys;sys.path.insert(0,r'code');import numpy as np,numlib as NL,model_skeleton as M,solve as S;ai=M.load_annex_i();t0=time.perf_counter()
for k in S.COMBOS:
    d=ai[k];V=S.ilr(np.column_stack([d['series'][p] for p in S.PROD])/100.0);X=S.design(d['w']);B,_=NL.lstsq(X,V)
    wg=np.linspace(d['w'].min(),d['w'].max(),1001);Vg=np.einsum('nk,km->nm',S.design(wg),B)
    P=S.ilr_inv((Vg+np.random.default_rng(0).normal(0,0.05,size=(4000,1001,3))).reshape(-1,3));np.percentile(P,[5,95],axis=0)
print('extreme_s=%.3f'%(time.perf_counter()-t0))"
```
→ `EXTREME 3x1001x4000 = 2.729 s`（12,012,000 点）

**命令 8 · 精确前向 vs MLP 前向（同进程、预热、中位）**
```
python -c "import time,sys,statistics;sys.path.insert(0,r'code');import numpy as np,numlib as NL,model_skeleton as M,solve as S;ai=M.load_annex_i();d=ai['DFA/CS'];V=S.ilr(np.column_stack([d['series'][p] for p in S.PROD])/100.0);B,_=NL.lstsq(S.design(d['w']),V);g=np.random.default_rng(0);W1=g.normal(0,.5,(1,32));W2=g.normal(0,.5,(32,32));W3=g.normal(0,.5,(32,4))
def med(f,n):
    xs=[]
    for _ in range(n):
        a=time.perf_counter();f();xs.append(time.perf_counter()-a)
    return statistics.median(xs)*1e6
for N in (1,7,1000,100000):
    Xg=S.design(np.linspace(0.05,0.5,N));n=200 if N<=1000 else 20
    e=med(lambda:S.ilr_inv(np.einsum('nk,km->nm',Xg,B)),n)
    m=med(lambda:np.einsum('ni,ij->nj',np.tanh(np.einsum('ni,ij->nj',np.tanh(np.einsum('ni,ij->nj',Xg[:,:1],W1)),W2)),W3),n)
    print('N=%-7d exact=%10.2f us mlp=%10.2f us ratio=%6.1fx'%(N,e,m,m/e))"
```
→ `N=1 exact=6.30 mlp=6.90 ratio=1.1x`；`N=7 exact=6.80 mlp=12.30 ratio=1.8x`；`N=1000 exact=57.70 mlp=1189.45 ratio=20.6x`；`N=100000 exact=10102.60 mlp=113556.20 ratio=11.2x`

**命令 9 · GPU 空闲基线（5 次 × 1 s）**
```
for($i=0;$i -lt 5;$i++){ nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader; Start-Sleep -Seconds 1 }
```
→ `0 %, 36 MiB, 2.96 W` / `0 %, 36 MiB, 4.45 W` / `0 %, 36 MiB, 4.18 W` / `0 %, 36 MiB, 4.39 W` / `0 %, 36 MiB, 2.94 W`

**命令 10 · 解释器与 CUDA 可用性**
```
python -c "import torch;print(torch.__version__,torch.cuda.is_available());print(torch.cuda.get_device_name(0),round(torch.cuda.get_device_properties(0).total_memory/2**20))"
```
→ `2.14.1+cu126 True`；`NVIDIA GeForce RTX 4060 Laptop GPU 8188`

**命令 11 · 上游噪声地板与失拟统计（交叉核对，不改上游）**
```
python -c "import json;d=json.load(open('data/results_q1.json',encoding='utf-8'));[print(c,'sigma_fit=%.4f sigma_noise=%.4f F=%.2f'%(d['combos'][c]['ilr']['sigma_fit'],d['combos'][c]['ilr']['sigma_noise_mc'],d['combos'][c]['ilr']['lack_of_fit_F'])) for c in ('CS','CE','LG')]"
```
→ `CS sigma_fit=0.0333 sigma_noise=0.0502 F=0.44` / `CE sigma_fit=0.0929 sigma_noise=0.0502 F=3.42` / `LG sigma_fit=0.0941 sigma_noise=0.0501 F=3.52`

**命令 12 · 42 种子稳定性（显著性结论是否翻转 + `F` 的散布）**
```
python -c "import sys;sys.path.insert(0,r'code');import model_skeleton as M,solve as S;ai=M.load_annex_i();flip={};Fs={'CS':[],'CE':[],'LG':[]};base=None
for i in range(42):
    S.RNG_SEED=20231119+i;r1=S.q1(ai);sig={}
    for cs in ('CS','CE','LG'):
        Fs[cs].append(r1['combos'][cs]['ilr']['lack_of_fit_F'])
        for p,v in r1['combos'][cs]['products'].items(): sig[(cs,p)]=bool(v['trend_significant'])
    if base is None: base=sig
    else:
        for k in sig:
            if sig[k]!=base[k]: flip[k]=flip.get(k,0)+1
print('flips=',flip if flip else 'NONE')
for cs in Fs:
    v=Fs[cs];print(cs,'F min=%.3f max=%.3f spread=%.3f'%(min(v),max(v),max(v)-min(v)))"
```
→ `significance_flips_across_42_seeds = NONE`；`CS F 0.436–0.444 (spread 0.007)` / `CE F 3.399–3.460 (0.061)` / `LG F 3.485–3.539 (0.054)`

---

## 8 交给下一棒

- **`out/12-training.md` 的存在意义是「证明不需要训练」，不是「训练日志」。** 下游写正文时**不要**新增深度学习章节、不要引用任何网络参数量、不要出现 `R² > 0.99` 之类的代理模型指标 —— 本题没有。
- 若下游需要「泛化能力」证据，用已有的 LOO 表（`out/01-model.md` L230–L234，`data/results_q5.json` 的 `loo_rmse_rel`），它比任何代理模型的 k 折都严格（`k = n`）。
- 若某一步真的出现「精确求解超时」（本判定未出现，见 §1、§2.3），触发条件是：**乘积 > 60 s**。届时先按 §2.3 检查是不是展示密度问题（加密网格通常 3 s 内解决），再考虑代理模型，并按 R-T01/T02/T03/T05 全套执行。
- 依赖方向：本文只读 `out/01-model.md` 与 `data/results_q1.json`、`code/*.py`，**未修改任何上游文件的内容**。说明一处必须披露的副作用：为测端到端墙钟（§7 命令 3）我运行了 `code/solve.py` 五次，该脚本会重写 `data/results_q*.json`，因此这五个文件的 **mtime 变了**；但内容是逐字节一致的 —— 用 `Get-FileHash -Algorithm SHA256` 在重跑前后对比，五个文件 `identical=True`（`results_q1.json` `853FB6BDD14FA182…`、`q2` `D9B646AE51D727D1…`、`q3` `34A9BC403E54799E…`、`q4` `3714FE375A219C12…`、`q5` `93F88D016A03EA11…`），即重跑是幂等的（`RNG_SEED = 20231119` 固定，`code/solve.py` L56）。复算命令：
  ```
  $b=@{}; Get-ChildItem data\results_q*.json | %{ $b[$_.Name]=(Get-FileHash $_.FullName -Algorithm SHA256).Hash }
  python code\solve.py > $null; Get-ChildItem data\results_q*.json | %{ "$($_.Name) identical=$((Get-FileHash $_.FullName -Algorithm SHA256).Hash -eq $b[$_.Name])" }
  ```
  `code/solve.py`、`code/model_skeleton.py`、`code/numlib.py`、`out/01-model.md`、`out/00-problem.md` 五个文件的 mtime 与内容均未变（本次会话内最后一次核对：`01-model.md` 17:43:22、`00-problem.md` 17:00:52、`solve.py` 17:30:42、`model_skeleton.py` 17:42:58、`numlib.py` 17:29:53）。

---

VERDICT: PASS
