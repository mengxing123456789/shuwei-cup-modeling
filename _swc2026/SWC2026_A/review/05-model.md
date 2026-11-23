BYTES 35994
# 05-model.md — 模型与检验审读：只找能推翻结论的地方

**对象**：`E:\数学建模\_swc2026\SWC2026_A`；`main.tex` 433 行；`main.pdf` 24 页；队号 ASWBMCM2634892。
**范围**：口径（谁和谁比、分母、基期）、稳定性不利半区、边界解、敏感性强度、结论强度。排版、语言、创新性不在此文。
**约定**：行号均指 `main.tex` 源文件行；表号指 `tables/*.tex`；JSON 键指 `data/*.json`。含推断的条目加 `[判断]` 并给理由链。

## 0. 机器口径与快照

### 0.1 版本快照（三个读取时刻，R-V11：报告是快照）

| 来源 | main.pdf | main.tex | 说明 |
|---|---|---|---|
| `review/00-metrics.md`（11:12:23 生成） | 11:10:01，451432 B，sha256 `A07B0CBEFCD1897F6F03CC21E9649E0D` | 11:09:33，48630 B，sha256 `78ED6F265289B0F2159005FD0FDBCC7A`（410 行） | 派单脚本的基线 |
| 中间读取（11:15） | 11:13:35，451432 B，sha256 `CF59A02A633FC0C03D21921041886FC22895474A52E7D2C923DE232C8F87910E` | 未变，sha256 同上 | **00-metrics 评的是 11:10:01 旧 PDF；11:13:35 是第一次重建版** |
| 最终读取（11:30） | 11:29:34，456424 B，sha256 `27D4AB8A51BF2DF3840AA2C8D2269AD68206C096A64C2B95C899FF03663C5A8B` | 11:29:22，50145 B，sha256 `CF89A98E8631D9D99A7DCCBDD390BDA817EC8E622B22D1F646E3B3123FAECBDB`（433 行） | **本报告最终以这一版为对象**；新增的是附录 D，正文引用行号未移动（核到 `main.tex:343`） |

我在 11:30 对最终 `27D4...` 的 PDF 重跑了四条机器判据；与 00-metrics 的数值一致（除 PDF 身份与图内 span 总数）：

```text
$ cd /d E:\数学建模\_swc2026\SWC2026_A
$ E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\review_check.py E:\数学建模\_swc2026\SWC2026_A
exit=0
VERDICT: PASS (fail=0 unknown=0); pages=24; C4/C5/C6/C7/C8/C9/C11 OK

$ E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py E:\数学建模\_swc2026\SWC2026_A
exit=0
16/16 PASS; body=23; R-V02 denominators=1 and consecutive; R-V04 12 type markers / 12 refs;
R-V06 claims=116 exit=0; R-V14 min=5.98 pt median=11.96 pt violations=0

$env:PYTHONPATH="E:\数学建模\.agents\skills\mathmodeling\scripts"; E:\Mini\envs\mathmodel\python.exe -m mmkit.figfont main.pdf
spans=5454; min=5.98 pt; median=11.96 pt; violations=0; single-char<6pt=53; PASS

$ E:\Mini\envs\mathmodel\python.exe code\verify_numbers.py
116 claims passed, 0 failed
```

完整 stdout 已存 `review/work/05_review_check_1129.txt`、`05_gauntlet_1129.txt`、`05_figfont_1129.txt`、`05_verify_1129.txt`（UTF-16，Windows 下 `Get-Content -Encoding Unicode` 可读；旧版同名 `*_now.txt` 仍有 11:15 快照）。

### 0.2 数据层同代性

p1–p5 的 `data/*.json` 为 10:42:17–10:53:32，`tables/*.tex` 最新 11:09:58，`figures/*.pdf` 最新 11:06:25，均早于当前 `main.pdf` 的 11:29:34；不触发“被测件落后”告警。`data/results_A.json` 是 11:14:23 的 aggregate（早于最终 PDF，但晚于 11:10 数据层），`source="aggregate of data/*.json"`，全库无任何代码引用它，不属于论文输入；下文不把它当证据。

**为什么机器全 PASS 仍要写这份报告**：`verify_numbers.py` 的 docstring 说 “Every number quoted in main.tex is re-derived from the JSON”（`code/verify_numbers.py:4-6`），但 144 行代码实际只做 116 个结构谓词，不读 `main.tex`。例如 `:111` 用 `close("ts_grid_vs_data", w2["ts_data_grid"], v["ts_grid"], 2.0)`，2.0 天容差天然接受 `25 vs 23`；`:123` 只检查硬编码的 `n_changed` 2/0/0，不检查 `d_ts`；`:126-133` 只检查 Sobol `S1∈[0,1]` 与 `sum∈[0.9,1.02]`，`sum>1` 也能过。它没有覆盖 `main.tex:250` 的 `<1%`、`:253` 的 `<=1 d`、`:270` 的 `51.3`、`:310` 的 `0.92–0.95`、`:70` 的 `9.7%`。因此 116/116 PASS 是覆盖盲区，不是正文全部对账。

## 1. 结论摘要（按可推翻性排序）

| ID | 严重度 | 会推翻什么 | 一句话证据 |
|---|---|---|---|
| M1 | 致命 | Part I/II 的 “radius vs soak time”、P2 的 τ 解释、P4 的 V0_geo | `p1_mechanistic.py` 实际上 60 天全程恒压注入；没有闷井段、没有生产段；`ts` 是注入时长 |
| M2 | 致命 | 摘要/结论中的 “peak NPV” 和 “optimal soak” | 所有 NPV 曲线固定 `Vinj=3000, qinj=300, fCO2=0.5, cn=1.0`；Pareto knee 是另一套设计；Case3 的 +184.3 不是全设计峰值 |
| M3 | 致命 | “Case3 robustly profitable”“Case1/2 structurally loss-making” | Case3 的 Sobol 5% 分位为 `-151.3×10^4`；Case2 的 geo knee 为 `+2.0×10^4` |
| M4 | 严重 | “permeability and in-situ stress ±15%”“no perturbation >1 d” | 14 个扰动是 7 个模型/经济参数×±15%，无渗透率、无地应力；Case2 有 3/14 个 `|d_ts|>1`，exact top-1 只活 4/14 |
| M5 | 严重 | “optimal design” 的物理含义 | 六个 knee 的 `qinj=800`、`fCO2=0.8`、`cn=0.5` 全部落在搜索边界；`qinj/fCO2` 不进产量（qinj 只改注入期/折现，fCO2 只改材料成本）；`qinj=800` 与 P1 的 4.7–45.5 m³/d 相差 17–170 倍 |
| M6 | 严重 | “NSGA-II check below 1%” | 代码 `gens=120` 不是 200；`rel_diff` Case2 `-14.06%`、Case3 `-1.39%`，不是 `<1%` |
| M7 | 严重 | M5 参数与模型选择 | `main.tex:270` 的 `D=2.99e-4` 比 JSON 的 `0.02994` 小 100 倍；Case3 的 `51.3/10.02/0.99` 与表 `54.985/9.98/1.0073` 不符；M5 的 AIC/BIC 明显差于 M3 |
| M8 | 严重 | “grid converges to 7.7e-6”“both below 1e-4” | 7.7e-6 只是 Case1；Case2 3.56e-5、Case3 2.89e-4，Case3 超过 1e-4 |
| M9 | 中高 | “two calibres differ by at most 1.5 d” | Case2 的 `d_ts=-1.507353` 已超过 1.5；同一 Case2 的 ts* 至少有 23、23.49、25、27、29 五个口径 |
| M10 | 中高 | Pareto knee 的可复现性 | `knee(trim=0.05)` 未在正文披露；trim 5→20% 时 Case3 emp 的 ts 从 33 变 28（-5 d），Case1 emp 25→27；trim 0→20% 时 Case3 emp 为 31→28 |
| M11 | 中 | “nine case–concentration combinations” | `p2_shape.py:130-155` 实际 `n_points:3`，只用三个 case 的 τ 均值回归，不是九个点 |
| M12 | 中 | 多处印刷数字可复算性 | `main.tex:141`、`:201`、`:204`、`:217`、`:270`、`:310`、`:312` 与 JSON/表不一致；见 §6 逐句表 |

## 2. 口径：谁和谁比、分母是谁、基期是哪年

### 2.1 P1 的 “soak” 实际是 60 天恒压注入（M1）

`main.tex:127-132` 定义三阶段：注入 `0<t<=t_inj` 用 `p(0,t)=p_M, q(0,t)=q_inj`；闷井 `t_inj<t<=t_inj+t_s` 用 `q(0,t)=0` 且两端无流；生产 `p(0,t)=p_wf=35 MPa`。`main.tex:137` 写 “1200 steps cover the 60-day soak”，`:152` 写 “simulated radius against soak time”。

实际 `code/p1_mechanistic.py:175-176` 的 `solve(case, ts=60.0, ..., tmax=95.0)` 中，`ts` 直接进入 `:209-216` 的 `nsteps=int(round(ts/dt))`；`:228-242` 每一步都对节点 0 施加 `p_new[0]=g['pmax']*MPA`，节点 N-1 施加 `p_new[-1]=p0`；`:264` 固定 `rr[0]=1.0`。代码没有 stage switch，没有 `q=0` 的闷井段，也没有 `p=35 MPa` 的生产段。`p1_mechanistic.py:339-342` 调 `solve(case, ts=60.0)` 生成 radii/scaling。

复算：

```bash
E:\Mini\envs\mathmodel\python.exe -c "import sys;sys.path.insert(0,'code');import p1_mechanistic as p; st=p.solve('Case1',ts=60.0,N=150)['store']; print({k:st[k] for k in ('mass_in_m3','store_m3','rel_imbalance','achieved_rate_m3_d','pump_rate_m3_d','p_face_MPa','Rp_end_m')})"
```

产物 `data/p1_mechanistic.json:solver_check`：`mass_in_m3=309.718/972.108/2988.061`，`achieved_rate_m3_d=4.7259/14.8117/45.4909`，`pump_rate_m3_d=300`，`p_face=60/57/60 MPa`。60 天按 300 m³/d 应注入 18,000 m³，实际只有 1.7%/5.4%/16.6%；`qface` 比 300 低 64/20/6.6 倍。`main.tex:139` 说 309.718 m³ 是 “at the end of injection”，其实它是 60 天恒压注入的累计量。

**后果**（`[判断]`，依据：代码无 stage switch、60 天恒压边界、实际注入量只为设计量的 1.7%/5.4%/16.6%）：`Rp(60)=40.64/85.19/181.46 m` 是 60 天注入压力前缘，不是 60 天闷井后的扩散前缘；`ν=0.500–0.503` 是恒压注入的自相似指数；`main.tex:341` 用它解释 “数据侧 0.22–0.34 的 retention layer” 的对照基准不成立。`main.tex:130` 同时写 `p(0,t)=p_M` 与 `q(0,t)=q_inj` 是过定边界；代码只施加 `p=p_M`，`q` 是解出来的 4.7–45.5 m³/d，不是 300。题面 `problem/problem.txt:99` 要求 Problems 2/3/4 与 Problem 1 一致；P4 却用 `qinj=300` 或 `800`，P1 的 60 MPa 井做不到。

**最小改法**（二选一）：
1. **保留物理故事**：在 `p1_mechanistic.py` 增加 `t_inj`、`ts` 两个时间参数，注入段用 `q=q_inj`（Neumann）或 `p=p_M` 之一；到 `t_inj` 后切 `q=0`、两端 no-flow 的闷井段；再切 `p=35 MPa` 的生产段。重跑 `Rp(ts)`、`Table 1`、`Figure 2`、`ν`、`P2` 的 τ 对照、`P4` 的 `V0_geo`。这是唯一让现有标题和结论成立的改法。
2. **保留结果、改叙事**：把 P1 的 `ts` 改名为 `t_inj`，全文把 “radius against soak time” 改为 “radius after t_inj days of constant-pressure injection”；删掉 “1200 steps cover the 60-day soak”，把 `main.tex:341` 的 retention 对照降为 “尚待验证的假设”。此改法成本低，但 Part II 的 “soak front” 结论要整体降级。

无论哪条，`main.tex:130` 必须二选一：`p=p_M` 或 `q=q_inj`，并把 P4 的 `qinj` 改为 P1 可实现的 5–45 m³/d 后重跑经济；否则 “qinj” 在两处含义不同。

### 2.2 NPV 的 “peak” 是基线切片，不是全设计最优（M2）

`code/p4_econ.py:68-85` 的 `scheme` 默认 `Vinj=3000.0, qinj=300.0, fCO2=0.5`；`:297-303` 的 `npv_curves` 全部用 `scheme(c, ts, cn)`，即 `cn` 变、`Vinj/qinj/fCO2` 不变、`V0=None`。`:80-85` 中 `A=A_scale(ts,cn)`，`qinj` 只通过 `tinj=Vinj/qinj` 进成本，`fCO2` 只通过 `materials` 进成本；`V0=None` 时 `A` 与 `Vinj` 也无关。因此 `main.tex:289` 的 `-720.2/-445.4/+184.3` 和 `main.tex:343` 的 “continuous optimal 9.8/23.5/35.4 d” 都是 **`Vinj=3000、qinj=300、fCO2=0.5、cn=1.0` 的单条基线切片**。`Figure 5` caption 只写 `cn=1.0`（`main.tex:294`），没有写 `Vinj/qinj/fCO2`。

全 `cn` 与 Pareto knee 的对比（单位 `10^4 CNY`）：

| Case | headline `cn=1.0`（`main.tex:289`） | `optimum_ts` 的 `cn=0.5` 最优 | 全 `cn` 最优的 `ts` | Pareto knee geo | Pareto knee emp |
|---|---:|---:|---:|---:|---:|
| Case1 | -720.2 | -573.3 | 9 | -472.1 | -361.7 |
| Case2 | -445.4 | -312.9 | 23 | +2.0 | -71.5 |
| Case3 | +184.3 | +287.6 | 35 | +1013.6 | +541.2 |

复算：

```bash
E:\Mini\envs\mathmodel\python.exe -c "import json,pprint; d=json.load(open('data/p4_econ.json')); pprint.pp(d['optimum_ts']); pprint.pp({k:v['knee'] for k,v in d['pareto_meta'].items() if '|' in k})"
```

`p4_econ.json:optimum_ts` 九个 `(case,cn)` 组合的 argmax 全部在 `cn=0.5` 下界（Case1 -573.3、Case2 -312.9、Case3 +287.6），摘要与结论却只报 `cn=1.0` 的 -720.2/-445.4/+184.3；`pareto_meta` 的 `knee` 是 `cn=0.5, qinj=800, fCO2=0.8` 的另一套设计。`main.tex:13` 的 “Case 3 is profitable (peak NPV +184.3 at ts=35)” 在 `cn=0.5` 下已是 +287.6，在 geo knee 下 +1013.6，在 `npv_best` 下 +1028.6；`main.tex:343` 的 “peak” 同样不成立。

**最小改法**：
- 每个 “peak/NPV/optimal” 前加限定词 “baseline-design (`Vinj=3000, qinj=300, fCO2=0.5, cn=1.0`)”；`Figure 5` caption 加齐四个量；
- 新增一张 “case × cn × calibration → best NPV” 表（九行），至少报 `cn=0.5` 的 -573.3/-312.9/+287.6；
- 若要用 “global best”，改报 `pareto_meta` 的 knee/NPV best（Case1 knee -472.1、NPV best -220.1；Case2 +2.0/+16.2；Case3 +1013.6/+1028.6），并说明 `qinj=800` 是边界、P1 物理上不可达。

### 2.3 同一个 Case2 至少有五个 `ts*`（M9）

| 口径 | Case1 | Case2 | Case3 | 产物键 |
|---|---:|---:|---:|---|
| `optimum_ts` 整数网格 argmax | 10 | 23 | 35 | `p4_econ.json:optimum_ts` |
| `ts_continuous`（cn=1.0） | 9.7827 | 23.4926 | 35.4448 | `optimum_two_calibers` |
| `ts_data_grid`（5 天档） | 10 | 25 | 35 | `optimum_two_calibers` |
| Pareto knee geo | 23 | 27 | 31 | `pareto_meta` |
| Pareto knee emp | 25 | 29 | 33 | `pareto_meta` |

`main.tex:289/300` 只比较 `23.49 vs 25` 就说 “two calibres differ by at most 1.5 d”；`optimum_two_calibers` 的 `d_ts=-1.507353` 已超过 1.5，且 `same_level` 阈值是 `2.5 d`（`p4_econ.py:349`），不是 1.5。摘要 `main.tex:11` 的 “10, 23.5 and 35.4 d (25 d on the five-day design grid in Case 2)” 本身是混用：Case1 取设计档 10、Case2/3 取连续值 23.5/35.4；若全用设计档应为 10/25/35，若全用连续应为 9.78/23.49/35.44。`break_even` 和 `robustness` 又用整数网格的 23，不是 25。

**最小改法**：只保留一张 `case × calibration → ts*` 表（上表），把 “at most 1.5 d” 改为 “连续驻点与 5 天档的最大差为 1.51 d（Case2）”；摘要不要混用，选一套决策口径（建议 5 天档 10/25/35）并在全文统一。

### 2.4 “2% band” 的分母（M9 附带）

`p4_econ.py:328`：`band = npv >= npv.max() - 0.02 * abs(npv.max())`。这是 **`|NPV_max|` 的 2%**，不是相对收益的 2%，也不是相对峰值的 2%。对负 NPV 案例，`band` 表示“亏损绝对值多 2%”；对正 NPV 案例，表示“收益少 2%”。`main.tex:324` 把 15/13/9 d 当 “design identifiability” 与其他维度并列，跨正负案例不可比。

**最小改法**：在 `Table 10` 或正文写清 `2% of |NPV_max|`；若要做可比区间，用 `0.02 * max(|NPV|, 1)` 或对负案例改用相对亏损；不要把 band 宽度作为与 NPV 同量纲的“识别性”。

## 3. 稳定性：必须报告不利的一半（M4）

### 3.1 14 个 OAT 的真实分布

`p4_econ.py:432-473`：`factors=('Ainf','tau','D','Poil','cprod','csoak','Cfrac')`，每个 ±15%，共 14 个 run；**没有 permeability，没有 in-situ stress**；`base` 是 `curves[c]['cn1.0']` 的整数网格 argmax（Case1 10、Case2 23、Case3 35）；`changed=abs(d_ts)>2.5`，因此 ±2 天被隐藏为 “unchanged”。

| Case | base `ts*` | exact `ts*` 存活 | `|d_ts|>1` 的 run | `d_ts` 明细 | NPV 最低–最高（`10^4`） | 相对 span |
|---|---:|---:|---:|---|---:|---:|
| Case1 | 10 | **5/14（35.7%）** | 0/14 | 其余 9 个 ±1 | -738.2 – -702.2 | 5.0% |
| Case2 | 23 | **4/14（28.6%）** | **3/14** | `tau+2, tau-2, csoak- +2` | -508.9 – -378.5 | 29.3% |
| Case3 | 35 | **4/14（28.6%）** | **3/14** | `tau+4, tau-4, Poil- -2` | +9.6 – +361.2 | 190.8% |

复算：

```bash
E:\Mini\envs\mathmodel\python.exe -c "import json,pprint; d=json.load(open('data/p4_econ.json')); pprint.pp(d['robustness'])"
```

`tables/tab_robust.tex:10-12` 印的是 `Runs changing ts*=0/0/2`；这只是 `>2.5 d` 阈值下的结果，不是 “最优解稳定”。**排序确实没动**（Case3 > Case2 > Case1 在 14 个 run 中一直成立），但 **top-1 只活 5/14、4/14、4/14**；这正是需要报告的“不利的一半”。`main.tex:253` 说 “Cases 1 and 2 no perturbation moves the optimal soak time by more than one day” 对 Case2 假（3/14 超过 1 天）；`main.tex:307` “Cases 1 and 2 remain negative in every perturbation” 也只覆盖这 7 个模型/经济参数，未覆盖题面要求的 permeability/stress。

### 3.2 Sobol 的 5% 分位（同一现象的另一个分母）

`p5_sobol.json` 的 NPV 分位数（单位 `10^4 CNY`）：

| Case | 5% | 50% | 95% |
|---|---:|---:|---:|
| Case1 | -761.5 | -719.8 | -675.1 |
| Case2 | -573.5 | -448.7 | -286.4 |
| Case3 | **-151.3** | +170.8 | +600.3 |

`main.tex:248` “Case 3 is robustly profitable” 是在 14 个 OAT run（且全是模型/经济参数）下的结论；`p5` 在 8 因子联合抽样下 Case3 的 5% 分位为负。**最小改法**：把 “robustly profitable” 改为 “median positive; 5% quantile -151.3×10^4; not robust in the lower tail”，并在摘要 `main.tex:13` 同步；若坚持 “robust”，把 `p5` 的 Ainf/tau/csoak/Cfrac 范围收窄到 ±15% 后重跑并给出 q05。

### 3.3 为什么 `tab_robust` 的 0/0/2 仍会误导

`p4_econ.py:463` 的 `changed` 阈值 2.5 d 比 `main.tex:253` 宣称的 “more than one day” 宽 2.5 倍。Case2 的 `tau±` 和 `csoak-` 各 2 d，Case3 的 `tau±` 4 d，全部被 “0/0/2” 隐藏。**最小改法**：阈值改为 `abs(d_ts) > 0` 或至少 `> 1`；表头写 “Runs with any change in argmax ts / exact ts survival”，不要只报 “Runs changing ts*”。

## 4. 边界解：最优点落在搜索网格边上（M5）

`p4_econ.py:219-240` 的 `front_grid` 固定 `qinj=800`（上界），`ts 5–60 step1`、`Vinj 1000–5000 step100`、`cn 0.5/1/1.5`、`fCO2 0.2/0.5/0.8`；`:481-488` 明确写 “qinj 取上限 800 m³/d 使注入期最短”。六个 knee 的 `qinj=800`、`fCO2=0.8`、`cn=0.5` 全是边界；geo 的 `Vinj=5000` 也是上界。

**边界解表**（knee 条件；`*` = 搜索边界；`NPV` 与 `10^4 CNY`；括号为放宽该变量并重新优化 `ts 5–60` 后的 `ts / NPV`）：

| Case / 标定 | knee `(ts, Vinj, qinj, fCO2, cn)` | knee NPV | qinj→1200 | fCO2→1.0 | Vinj→8000 | cn→0.25 |
|---|---|---:|---:|---:|---:|---:|
| Case1 geo | `(23, 5000*, 800*, 0.8*, 0.5*)` | -472.1 | `(13, -396.5)` | `(13, -382.0)` | `(15, -607.6)` | `(12, -409.2)` |
| Case1 emp | `(25, 3200, 800*, 0.8*, 0.5*)` | -361.7 | `(10, -303.3)` | `(10, -285.6)` | `(10, -698.6)` | `(9, -302.9)` |
| Case2 geo | `(27, 5000*, 800*, 0.8*, 0.5*)` | +2.0 | `(27, +62.2)` | `(27, +76.5)` | `(30, +143.9)` | `(27, +37.2)` |
| Case2 emp | `(29, 3100, 800*, 0.8*, 0.5*)` | -71.5 | `(23, -36.0)` | `(23, -19.9)` | `(24, -392.8)` | `(23, -44.0)` |
| Case3 geo | `(31, 5000*, 800*, 0.8*, 0.5*)` | +1013.6 | `(39, +1089.2)` | `(39, +1103.1)` | `(43, +1810.0)` | `(39, +1039.5)` |
| Case3 emp | `(33, 3100, 800*, 0.8*, 0.5*)` | +541.2 | `(35, +571.9)` | `(35, +587.8)` | `(36, +303.7)` | `(34, +549.0)` |

复算（脚本已写在工作区，直接运行）：

```bash
E:\Mini\envs\mathmodel\python.exe review\work\boundary.py
```

`qinj` 与 `fCO2` 的边界最优是模型结构产物：`p4_econ.py:78-85` 中 `qinj` 只进 `tinj=Vinj/qinj`（注入成本与收入折现时点），`fCO2` 只进 `materials`（材料成本），二者都不进 `A`、不进 `EUR`（产量积分本身）；因此“更高 qinj”主要靠缩短注入期和降成本获益、“更高 fCO2”只降材料成本，二者都不会降低产量，最优点会贴在上界。`qinj=800` 还与 P1 的 `achieved_rate 4.7–45.5 m³/d` 相差 17–170 倍（见 §2.1），`[判断]` 物理上不可达。`fCO2=0.8` 是网格上界，`cn=0.5` 是下界；`Vinj=5000` geo 是上界。`main.tex:244-248` 把 knee 当作推荐值，未标 `*`，也未报放宽后的值。

**最小改法**：
- `Table 5` 每个 knee 后加 `*`，脚注：`qinj=800 upper bound; fCO2=0.8 upper bound; cn=0.5 lower bound; geo Vinj=5000 upper bound`；
- 在表后加一列/一小表，报放宽值（本表括号）并说明 `qinj/fCO2` 只进成本；如果不想让“最优设计”落在边界，给 `qinj/fCO2` 增加物理产量项或把它们从 Pareto 决策变量中移除；
- 把“qinj=800 使注入期最短”写成“这是成本最小化的边界解，不是物理最优”；`Case2` 的 +2.0 万是边界解、不是“盈利稳健”的证据。

### 4.1 knee 的 5% trim 敏感性（M10）

`p4_econ.py:243-267` 的 `knee(pts, trim=0.05)` 在归一化 `(EUR,-cost)` 平面两端各裁 5% 分位；正文 `main.tex:233` 只说 “最大距离、按两个目标的范围归一化”，未提 5%。用 `p4.knee` 重跑 `trim=0/1%/5%/10%/20%`：

| Case | 0% | 1% | 5% | 10% | 20% |
|---|---:|---:|---:|---:|---:|
| Case1 geo ts | 24 | 24 | 23 | 23 | 22 |
| Case1 emp ts | 24 | 25 | 25 | 26 | 27 |
| Case2 geo ts | 28 | 28 | 27 | 27 | 26 |
| Case2 emp ts | 28 | 29 | 29 | 30 | 31 |
| Case3 geo ts | 31 | 31 | 31 | 30 | 28 |
| Case3 emp ts | 31 | 32 | 33 | 34 | 35 |

Case3 emp 的 ts 从 33 变 28（-5 d），Case1 emp 从 25 变 27（+2 d）；正文只报 `trim=5%` 单点。**最小改法**：把 `trim` 写进方法，给 0/5/10% 三档的 knee 表；或改用不依赖 trim 的定义（最大曲率、UTOPIA 距离），并报告其敏感性。

## 5. 敏感性强度：三档实际是什么（M3/M4/M5 的证据层）

| 档 | 实际做法（代码/产物） | 主要结果 | 证据强度 |
|---|---|---|---|
| OAT ±15% | `p4_econ.py:432-473`：7 个因子（Ainf,tau,D,Poil,cprod,csoak,Cfrac）×±15%，14 run，固定 `cn=1.0, Vinj=3000, qinj=300, fCO2=0.5` | exact ts 存活 5/14、4/14、4/14；NPV span 5%/29%/191%；Case2 3/14 `|d_ts|>1` | 只支持“基线切片的局部稳定性”；不支持“permeability/stress”；不是 combination |
| 重抽样 | `p3_decline.py:244-268`：每组 `(Cn=1.0, ts=30)` 一个组，400 次 residual bootstrap，固定 ARPS 指数形式 | EUR 95% CI 287.7–292.3 / 1323.7–1338.7 / 3439.0–3488.1 m³；`main.tex:277` 说“窄因为噪声小” | 条件残差区间；不含模型形式/组间异质性/模型选择；`main.tex:277` 自认“不含 model-form uncertainty” |
| Sobol | `p5_sobol.py:22-27`：8 因子，N=1024，18,432 evals；范围为 Ainf/tau/csoak/Cfrac 0.70–1.30（±30%）、D/Poil/cprod 0.85–1.15（±15%）、a 0.50–1.50（±50%） | NPV `sum S1=0.9806/0.9810/0.9931`；ts* `sum S1=1.0372/1.0229/1.0163`（>1）；Case3 q05=-151.3 万 | 因子固定 `Vinj=3000/qinj=300/fCO2=.5`，无设计变量；`a` 在 cn=1.0 时结构性为 0；`ts_closed` 的 F 固定按 20 d 算 |

### 5.1 `a` 的零效应是结构性的，不是“a 不重要”

`p5_sobol.py:41/58` 与 `p4_econ.py:57-60` 的 `A_scale` 都有因子 `(1 + a*(cn-1))`；`p5` 固定 `cn=1.0`，所以 `1+a*(cn-1)=1` 对任意 `a` 恒成立。`tab_sobol.tex` 的 `a` 列全为 0.000，是 **设计导致的零**，不应解释为“damage coefficient 不影响 NPV/ts*”。**最小改法**：在 `cn=0.5/1.5` 或把 `a` 重新参数化后重跑；表注写 “a 在 cn=1.0 下不可识别”。

### 5.2 Sobol 的 `sum S1(ts*)>1` 和估计量

`p5_sobol.json` 的 `sum_S1` 对 ts* 为 1.0372/1.0229/1.0163；一阶指数之和大于 1，说明 `S1` 截负（`:101` `np.clip(S1,0,None)`）或估计量方差偏大，不足以把这些数当作可加的方差分解。`main.tex:319` 只报 NPV 的 0.98–0.99，没有报 ts* 的 >1。**最小改法**：对 ts* 报 `ST` 或 `S1` 的 bootstrap CI，并在正文说明 `sum S1>1` 是截负/估计误差，不作为“可加性”证据；或改用更稳定的Saltelli 2010 估计量。

### 5.3 `ts_closed` 与 p4 的 `F(ts)` 不是同一口径

`p5_sobol.py:65-81` 的 `ts_closed` 中 `F` 固定按 `ts=20 d` 算（`:76-77`），而 `p4_econ.py:317-327` 对每个 `ts` 迭代 `F(ts)`。`p5_sobol.py:174-179` 的 `consistency_check` 已显示：Case2 `npv_max=-4,459,652.51` vs p4 `-4,454,037.70`，`ts_at_max=25` vs p4 `23`。**最小改法**：p5 用 p4 的 `scheme`/迭代 F，或明确把 `ts_closed` 改名为 “fixed-F approximation”，不要在同一段把两者当同一 `ts*`。

### 5.4 弹性核对不是“独立方法”

`main.tex:321` 说 “predicted ratio of the elasticities ... 0.227; measured 0.266 ... independent elasticity criterion”。但 `p5_sobol.py:182-198` 的 `pred_S1_tau_over_Ainf=(e_tau/e_Ainf)^2`，`e_Ainf=tau/ts*`、`e_tau=(ts*-tau)/ts*`；实际 `e_tau/e_Ainf` 为 0.477/1.818/2.554，平方才是 0.227/3.31/6.52。`obs_S1_tau_over_Ainf` 是同一模型 Sobol 的 `S1(tau)/S1(Ainf)`，不是独立实验的弹性。**最小改法**：把 0.227/0.266 改称 “squared elasticity ratio vs Sobol S1 ratio”；若要称独立，必须用另一套模型/数据估计弹性，而不是同模型解析式。

## 6. 结论是否强于证据：逐句表

下面行号均指 `main.tex`。最后一列“产物键/复算”可直接用 §8 的命令取；表中 `w` = `10^4 CNY`。

| # | 行 | 原文/原句（缩写） | 产物键或复算值 | 判定 | 最小改法 |
|---:|---:|---|---|---|---|
| 1 | 9 | “three grid levels agree to 7.7e-6” | `p1_mechanistic.json:grid_convergence` Case1 7.7345e-6/4.4589e-6；Case2 3.56e-5/3.06e-5；Case3 3.9995e-5/2.8877e-4 | 只是 Case1；Case3 最大 2.89e-4 | 改为 “Case1 7.7e-6; worst case 2.9e-4”，或给三行表 |
| 2 | 11 | “optimal soak 10, 23.5, 35.4 d (25 d ... Case2)” | `p4_econ.json:optimum_two_calibers` 10/25/35 vs 9.78/23.49/35.44 | 三种口径混用 | 统一为 10/25/35（设计档）或 9.78/23.49/35.44（连续），不要混 |
| 3 | 13 | “Case 3 ... peak NPV +184.3 at ts=35” | `optimum_ts` cn0.5 +287.6；`pareto_meta` knee +1013.6，npv_best +1028.6 | “peak”不是全设计峰值 | 改 “baseline-design peak +184.3”；或改报全局 +1013.6 |
| 4 | 141 | “Case3 ratio 1.18–1.2” | `tab_scaling.tex:13` 与 `p1_mechanistic.json:scaling.Case3.ratio_num_ana` 均 1.071 | 数值不符 | 改 1.071；三案例 1.288/1.143/1.071 |
| 5 | 201 | “prefactor changes by 12%” | `p1_mechanistic.json:nu_sensitivity` C 4.07→6.67（+63.9%）、9.62→12.48（+29.7%）、21.85→24.94（+14.1%） | 12% 无产物键，且与三案不符 | 报三个 case 的实际 prefactor 变化，或删 12% |
| 6 | 204 | “τ=6.70, 8.34, 10.02; R²=0.9992; runs 7,7,9” | `tab_shape.tex:10-12` τ=6.696/8.502/9.991，R² Case2 0.9991，runs exp=7/7/4 | 三处不一致 | 全部改为表值；Case2 τ 8.50、runs 4 |
| 7 | 215 | “nine case–concentration combinations” | `p2_shape.json:tau_scaling_vs_Rp.n_points=3`；`p2_shape.py:130-155` 用 3 个 case 的 τ 均值 | 实际 3 点，不是 9 点 | 改 “three case means”；若要 9 点，按 cn 分三层并给 cluster CI |
| 8 | 217 | “ts*/τ 3.50; elasticity 0.23→6.5” | `p5_sobol.json:elasticity_check` `ts_over_tau` 1.477/2.819/3.554；`e_tau` 0.323/0.645/0.719；0.227/6.52 是 `pred_S1_tau_over_Ainf`，不是 elasticity | “elasticity”标签错；3.50 应为 3.55 | 改 `ts*/τ=1.48/2.82/3.55`；把 0.23→6.5 改成 `S1(tau)/S1(Ainf)` 的 0.227→6.52 |
| 9 | 248 | “Case 3 robustly profitable” | `p5_sobol.json:quantiles.Case3` 5% = -151.3 万 | 只在 14 个 OAT 下正；联合 Sobol 5% 负 | 改 “median positive, 5% quantile negative”；或收窄 Sobol 范围重跑 |
| 10 | 250 | “64 individuals and 200 generations; below 1% in every case” | `p4_econ.py:150` `gens=120`；`pareto_meta` rel_diff -0.000315/-0.140628/-0.013940 | 200 vs 120；Case2 14.06%、Case3 1.39% | 改 120 代；把 <1% 改为 0.03%/14.1%/1.4%，或重跑 200 代 |
| 11 | 253 | “permeability and in-situ stress ±15% ... no perturbation >1 day” | `p4_econ.py:432-473` factors 无 km/stress；Case2 3/14 `|d_ts|>1`；14 run 是 7 因子 OAT，不是 combination | 与代码不符 | 改 “seven model/economic factors, one-at-a-time”；补 km/stress 映射后重跑；报 exact survival |
| 12 | 265 | “M3 wins AIC ... M5 only slightly worse RMSE” | `tab_modelsel.tex:12-14` M3 AIC -57819.1/BIC -55043.0；M5 AIC -55632.7/BIC -55504.2；ΔAIC 2186.4，ΔBIC 461.2；M3 无 CV | 只报 M3 AIC，不报 M5 AIC/BIC；选择依据不足以称“模型更好” | 表里加 M5 AIC/BIC；把选择理由写死为 “extrapolation, not information criterion”；补 M3 的 held-out CV |
| 13 | 270 | “D=2.99e-4, 2.00e-4, 1.50e-4; Ainf=8.77,27.51,51.3; τ=6.62,8.34,10.02; p=0.996,0.991,0.99” | `p3_decline.json:shared_D` D=0.02994/0.01998/0.01500（表 `tab_m5.tex:10-12` 的 `299.384/199.794/149.987 ×10^-4`）；M5 Case3 54.985/9.9835/1.0073 | **D 小 100 倍**；Case3 三个参数均不符 | 改 D 为 `2.99×10^-2` 等；Case3 改 54.985/9.98/1.0073；或直接从 `tab_m5` 抄 |
| 14 | 289/300 | “two calibres ... at most 1.5 d” | `optimum_two_calibers` Case2 `d_ts=-1.507353`；`same_level` 阈值 2.5 | 差 1.507 >1.5；实际用 2.5 阈值 | 改 “max 1.51 d”；同表列出 23/25 两种口径 |
| 15 | 307 | “Cases 1 and 2 remain negative in every perturbation” | `p4_econ.json:robustness` 只有 7 因子；`pareto_meta` Case2 geo knee +2.0；`qinj=1200` +62.2 | “every perturbation”仅基线 7 因子；Case2 在 knee/放宽边界为正 | 改 “in the seven-factor baseline screen”；把 Case2 的 +2.0 写进正文，不再称 structurally loss-making |
| 16 | 310 | “data-implied radius 34–36 m; ratio 0.92–0.95” | 34/40.6=0.837，36/40.6=0.887；34–36 m 无产物键 | 算术不成立；无键 | 改 0.84–0.89，或先给 34–36 m 的 JSON 键 |
| 17 | 312 | “90th percentile of relative standard deviation 29%” | `p3_decline.json:noise_check.resid_sd_rel=0.29094`（`np.std`，不是 p90）；`med_rel_resid=0.11946` | 把 std 当 p90；9.7% 也不在 JSON | 改 “std of group-relative residuals 29.1%”，删 90th；`main.tex:70` 改 11.95% 或给 9.7% 的键 |
| 18 | 324 | “physical feasibility ... both below 1e-4” | mass 7.7e-5 OK；grid Case3 2.8877e-4 >1e-4 | “both” 只在 Case1 成立 | 改 “mass <1e-4 all cases; grid worst 2.9e-4”；或细分 |
| 19 | 335 | “grid converges to 7.7e-6; NSGA-II within 1%” | 同 #1；`pareto_meta` rel_diff 14.06%/1.39% | 两句都只覆盖 Case1/不成立 | 同 #1/#10 的改法 |
| 20 | 343 | “continuous optimal 9.8/23.5/35.4; Case3 peak +184.3 at 35” | `optimum_two_calibers` 9.783/23.493/35.445；`optimum_ts` cn0.5 +287.6；knee +1013.6 | 混口径 + 非全局 peak | 同 #2/#3；结论只写 “baseline design” |

**另外两处方法描述问题**（不单独占一行，但影响可复现性）：
- `main.tex:227` 说 “weighted-sum scalarisation on a grid”，实际 `p4_econ.py:219-240` 是穷举网格 + 非支配筛选（`nds`），没有加权和；`main.tex:250` 又说 “not an artefact of weighted-sum scalarisation”，前后方法名不一致。最小改法：改成 “exhaustive grid + non-dominated filter”。
- `main.tex:315` 说 “two estimators agree to 0.01 in every index”，`p5_sobol.json` 的 `max_abs_S1_minus_ST` Case2 NPV 为 0.01509 >0.01。最小改法：改 “<=0.016”，或报每案最大差。

## 7. 最小改法汇总（按优先级）

1. **先修 P1 的阶段/边界**（M1）：要么实现注入—闷井—生产三阶段并重跑 P1/P2/P4，要么把 P1 全文改成 “injection-time pressure front”，删掉 “soak front” 结论；`p(0,t)=p_M` 与 `q(0,t)=q_inj` 只留一个。同步把 P4 的 `qinj` 改成 P1 可实现的 5–45 m³/d，或把 P4 的 `qinj` 改名为 “pump capacity”，避免同名不同义。
2. **重写 P4 的头条口径**（M2/M9）：所有 NPV 曲线标 `Vinj=3000, qinj=300, fCO2=0.5, cn=1.0`；新增九组 `(case,cn)` 表；把 `+184.3` 降为 “baseline-design peak”，把全局最优改为 Pareto knee 的 `+1013.6`（并注明边界）；摘要/结论统一 `10/25/35` 或 `9.78/23.49/35.44`，不要混。
3. **重跑稳定性**（M4）：把 `permeability`/`stress` 映射到 `Ainf`/`tau`（Ainf∝km，tau∝1/αp）后加入 14-run；阈值改 `>0` 或 `>1 d`；表头报 exact top-1 存活 5/14、4/14、4/14；正文 `253/307` 改 “7 个模型/经济参数”，不再说 “permeability and in-situ stress”。
4. **所有边界解标星**（M5）：`Table 5` 加脚注；报告 `qinj=1200/fCO2=1.0/cn=0.25/Vinj=8000` 的放宽值；说明 qinj/fCO2 只进成本；`qinj=800` 与 P1 的 4.7–45.5 m³/d 不一致，不足以作为物理设计。
5. **修正印刷数字**（M7/M12）：`main.tex:270` D 改为 `2.99/2.00/1.50 ×10^-2`；Case3 Ainf/τ/p 改 `54.985/9.98/1.0073`；`main.tex:141` 1.071；`204` 表值；`215` 3 点；`217` 3.55；`310` 0.84–0.89；`312` std 29.1%；`324/335` worst grid 2.9e-4。
6. **补模型选择与 bootstrap**（M7）：`tab_modelsel` 加 M5 AIC/BIC 与 M3 CV；`main.tex:265` 明说 “选择 M5 是为了外推，不是 AIC 最优”；bootstrap 要么按整组/模型形式重抽样，要么把 `main.tex:277` 改成 “conditional residual interval, not model-form”。
7. **Sobol 与 knee 的披露**（M10/M11）：`p5` 报三档范围表；`a` 在 cn=0.5/1.5 重跑；`ts_closed` 用 p4 的迭代 F；`knee` 报 trim=0/5/10% 三档；`p2` 报 3 点而不是 “nine”。

## 8. 复算命令（同一份 PDF）

行号指 `main.tex`；`PD` 指 `E:\Mini\envs\mathmodel\python.exe`；工作目录 `E:\数学建模\_swc2026\SWC2026_A`。

```bash
set PD=E:\Mini\envs\mathmodel\python.exe
cd /d E:\数学建模\_swc2026\SWC2026_A

REM 四条机器判据
%PD% E:\数学建模\.agents\skills\mathmodeling\scripts\review_check.py .
%PD% E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py .
set PYTHONPATH=E:\数学建模\.agents\skills\mathmodeling\scripts && %PD% -m mmkit.figfont main.pdf
%PD% code\verify_numbers.py

REM P1 阶段/边界：看 store / achieved / pump / p_face
%PD% -c "import sys;sys.path.insert(0,'code');import p1_mechanistic as p; st=p.solve('Case1',ts=60.0,N=150)['store']; print({k:st[k] for k in ('mass_in_m3','store_m3','rel_imbalance','achieved_rate_m3_d','pump_rate_m3_d','p_face_MPa','Rp_end_m')})"
REM 看 p1 的每步边界，确认无 stage switch
%PD% -c "import re; t=open('code/p1_mechanistic.py',encoding='utf-8').read().splitlines(); print('\n'.join(f'{i+1}: {l}' for i,l in enumerate(t) if 175<=i+1<=242))"

REM P4：全部 (case,cn) 最优、两套标定、Pareto knee
%PD% -c "import json,pprint; d=json.load(open('data/p4_econ.json')); pprint.pp(d['optimum_ts']); pprint.pp({k:v['knee'] for k,v in d['pareto_meta'].items() if '|' in k})"

REM P4：14-run 的 exact ts 存活
%PD% -c "import json; d=json.load(open('data/p4_econ.json')); [print(c, d['robustness'][c]['base_ts'], sum(1 for r in d['robustness'][c]['cases'].values() if r['d_ts']==0), '/', d['robustness'][c]['n_perturb'], 'span', d['robustness'][c]['npv_span_rel']) for c in ('Case1','Case2','Case3')]"

REM P4：边界解（knee 各变量放宽并重优化 ts）
%PD% review\work\boundary.py

REM P3：D、M5 参数、AIC/BIC
%PD% -c "import json,pprint; d=json.load(open('data/p3_decline.json')); pprint.pp(d['shared_D']); pprint.pp(d['M5_params']); pprint.pp(d['model_selection'])"

REM P2：τ-vs-Rp 的 n_points
%PD% -c "import json; print(json.load(open('data/p2_shape.json'))['tau_scaling_vs_Rp'])"

REM P5：Sobol 设计/分位/弹性/S1 和
%PD% -c "import json,pprint; d=json.load(open('data/p5_sobol.json')); pprint.pp(d['design']); [print(c, d['sobol'][c]['quantiles'], d['sobol'][c]['npv']['sum_S1'], d['sobol'][c]['ts']['sum_S1']) for c in ('Case1','Case2','Case3')]; pprint.pp(d['elasticity_check'])"
```

PDF 文本复核（PDF 的页数与行号与 `main.tex` 不同，用 `pdftotext` 关键字定位）：

```bash
pdftotext -layout main.pdf - | findstr /n "three grid levels agree optimal soak time peak NPV 184.3 two calibres NSGA-II permeability and in-situ stress robustly profitable"
```

## 9. 判定

- **VERDICT: FAIL**。机器硬项 PASS（C4/C5/C6/C7/C8/C9/C11、R-V02/V04/V06/V14 全过），但模型与检验层存在可推翻结论的缺陷：P1 的核心 “soak” 阶段未实现（M1）；NPV/Pareto 的头条数是基线切片且 boundary 解全在搜索边界（M2/M5）；稳定性只报了有利的一半（M4）；Case3 “robustly profitable” 与 Sobol 5% 分位冲突（M3）；多处印刷数无产物键或与表/JSON 不符（M7/M12）。
- **最小可交付修复路径**：先做 §7 第 1–4 项，再做第 5–7 项；第 1 项会改变 P1/P2/P4 的数值，必须重跑后重新生成 `data/*.json`、`tables/*.tex`，再运行 `review_check.py` / `gauntlet_check.py` / `verify_numbers.py`。第 2–7 项若不改模型，仅改文字与表注，也要同步更新 `main.tex` 与 `tables/*.tex`，否则 PDF 与产物仍是两套数。

VERDICT: FAIL
