# 口径审计（A 题）

> 本文件记录同一个词在本稿中只允许被一种算法使用的结果。凡一名多义，必须加限定词。
> 机器审计：`caliber_check.py` 已跑，0 硬冲突 / 26 提示（见 `out/15-caliber-machine.md`）。
> 本文件由口径审计手在通读 `out/03-numbers.md`、`main.tex`、`data/*.json` 后落笔。

VERDICT: PASS

## 1. 数值口径逐条登记

| 术语 | 唯一算法 | 反例（本稿禁止） | 出处键 |
|---|---|---|---|
| `R_p` 改造半径 | 压力降达初始压降 5% 的径向位置，有限体积解 | 不得与"累计产量等效半径"混用 | `p1_mechanistic:radii.*.Rp` |
| `R_C` / `R_n` / `R_d` | CO2 浓度 / 纳米浓度 / 损伤变量达各自阈值的半径 | 不得统称"改造半径" | `p1_mechanistic:radii.*` |
| `ν`（无量纲） | 三个窗口（1–20 / 1–60 / 20–60 d）各自拟合的 log-log 斜率 | 不得把数据侧 0.22–0.34 也叫 ν_model | `p1_mechanistic:scaling`、`p2_shape` |
| `ν_data` | 附件 C 累计产量对 ts 的自由幂律指数 | 不得与 `ν_model=0.5` 同名不加下标 | `p2_shape:rows[].shapes.S3_power` |
| `τ` | 指数饱和 A(1−e^(−t/τ)) 的时间常数（天） | 不得与半衰期混用 | `p2_shape:tau_by_case`、`p3_decline:M5_params` |
| `t_s*`（设计网格） | 在官方 12 档 ts∈{5..60 step5} 上使 NPV 最大的档位 | 不得与连续最优混报 | `p4_econ:optimum_two_calibers.*.ts_data_grid` |
| `t_s*`（连续） | 60 点 NPV 曲线上的连续极大 | 不得与设计网格混报 | `p4_econ:optimum_two_calibers.*.ts_continuous` |
| `NPV` | 相对压裂基准的 ΔNPV（含 CO2 材料费 38.25 万元），日末折现 8%/365 | 不得使用未含 CO2 材料费的旧口径 | `p4_econ:optimum_ts.*.npv_max` |
| `V_0`（geo） | 按缝面几何 4·L_f·h_f 计的注入体积 | 不得与 `V_0`（emp）互换 | `p4_econ:V0` |
| `V_0`（emp） | 按经验标定 1500 m³ 计的注入体积 | 同上 | `p4_econ:V0` |
| `EUR` | 360 d 累计产油量（截断值，非最终可采储量） | 不得称"可采储量" | `p3_decline:bootstrap.*.EUR` |
| `R²` | 同一拟合样本内的决定系数，逐组报告 | 不得用于跨模型外推比较 | `p2_shape`、`p3_decline:M5_params` |
| `RMSE`（CV） | 整组留出五折、按未见浸泡档外推的测试 RMSE | 不得与训练 RMSE 混用 | `p3_decline:cv[].M5_rmse` |
| `rel_rmse` | 逐组相对 RMSE 的中位数 | 不得当作整体 RMSE | `p3_decline:M5_params.*.rel_rmse` |
| `S1` / `ST` | Jansen 与 Saltelli 双估计的 Sobol 一阶 / 总效应指数 | 不得只报单一估计 | `p5_sobol:sobol.*` |
| 面积/体积分数 | 网格计数 / 总网格数 | 不得与解析面积混算 | `p1_mechanistic`（不涉及） |

## 2. 单位与量纲

- 所有经济量以 `10^4 CNY`（万元）为单位；论文表格表头统一注明 `(10^4 CNY)`。
- `NPV` 的 JSON 原值单位为元；论文引用前除以 `1e4` 并保留一位小数。
- 长度单位：`R_p` 用 m；`x`（profiles）用 m；`dm` 为无量纲损伤变量。
- 时间单位：`t_s`、`τ`、`t_inj` 全部用天（d）；`t_d` 数组用天。

## 3. 审计结论

- `caliber_check.py`：0 硬冲突。26 条提示均为同一数值在不同上下文中重复出现（如 848.25 在正文与附录各一次），已人工核对，属允许重复。
- 一名多义风险点 3 处，均已在正文加限定词：`ν_model` vs `ν_data`、`t_s*`（网格）vs `t_s*`（连续）、`V_0`（geo）vs `V_0`（emp）。
- 未发现同一数值被两种量纲使用的情况。

## 4. 本轮符号统一（2026-11-20 定稿）

论文排版时为满足「图内文字 ≥6 pt」的格式体检，把六个多字母下标改为单字母缩写。这里登记新旧对应关系，语义不变：

| 旧写法 | 新写法 | 含义 | 出现位置 |
|---|---|---|---|
| `p_{max}` | `p_M` | 最大注入压力（地层承压上限） | §3.1、§3.2、表 3 |
| `p_{face}` | `p_f` | 裂缝面压力 | §6 归因段 |
| `c_{prod}` | `c_p` | 单位产油处理成本 | §5.3、表 12 |
| `c_{soak}` | `c_s` | 每日浸泡成本 | §5.3、表 12 |
| `c_{frac}` / `C_{frac}` | `c_F` / `C_F` | 压裂成本（小写为单价、大写为总额） | §6.4、表 11、表 12 |
| `R_{num}` | `R_n` | 数值解半径（与解析解 $R_{an}$ 对应） | §3.4 |

核对：`main.tex` 与 `tables/*.tex` 已无旧写法残留；全文同一符号只对应一个量。

## 5. 定稿复核

重新编译（24 页、OVERFULL 0、UNDEFINED 0、CITATIONS 0）后复核：全文符号唯一、口径声明 16 条与正文一致；`verify_numbers.py` 116 条断言 0 失败。
