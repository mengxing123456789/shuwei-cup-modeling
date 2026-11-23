BYTES 18881

# 05-caliber · 口径审计（同一个词被两种算法用过）

> 审计对象：`out/01-model.md`（347 行 / 24589 B）、`out/02-solve.md`（473 行 / 38249 B）、`out/03-numbers.md`（713 行 / 47942 B）。三份末行均为 `VERDICT: PASS`。
> 判据来源：`E:\数学建模\.agents\skills\mathmodeling\WORKFLOW.md` §11 第 1–4 条、§5.1（G16）。
> 纪律：**只改措辞与限定语，不动任何数字**；改数字必须回「求解与优化手」重跑。本文件不改任何上游文件。
> 复算解释器：`E:\Mini\envs\mathmodel\python.exe`（Python 3.11.18 / numpy 2.4.6，BLAS 被禁，见 `code/numlib.py`）。

---

## 0 三条前置判断

1. **派单必查点①「LP 上界 / 整数格最优 / 实际可达」在本项目不适用。** `out/02-solve.md:34` 明写「本棒不做优化：不存在 LP 松弛、不存在整数格、不存在目标值上界」。其同型替代物有两处，本表按同型处理：#K7（派生列 R² 虚高，把「坐标级 R²」当「拟合优度」）、#K1–#K2（同一个「不变/判定」被 trend 与 single/step/diff 多条路径共用）。
2. **派单必查点⑤的先验数字与实测不符，需按实测走。** 派单写「42 次扰动里 12 次不可行」；`data/results_perturb.json → meta.counts` 实测 `attempted 42 / model_perturb 16 / query_move 14 / never_read 12 / model_infeasible 1 / model_feasible 15 / flip_denominator 15 / model_runs_with_flip 1`。12 次是 **`never-read`（参数不在 `SOLVE_SRC` 里，扰动后 `max_rel_change` 全 0.0）**，真正的不可行只有 **1 次**（`alpha+`，α=0.95×1.1=1.045≥1，`code/s3_deliver.py:522–523` 显式拦下）。`out/02-solve.md:180–185` 已自行纠正，本表把它列入「保留区」，不得反向改回去。
3. **本表共 22 条缺陷**：K 级 8 条（会直接导致读者得出错误结论）、M 级 11 条（会误读数量关系）、L 级 3 条（措辞/排版）。另有 9 条**已自带双口径说明**，列入 §2「保留区」，**不要重改**。

---

## 1 缺陷表

| # | 级 | 必查点 | 正文行号 | 原文短语（节录） | 它实际属于哪个口径 | 建议改法 |
|---|---|---|---|---|---|---|
| K1 | K | ②阈值沿哪条路径 | `out/02-solve.md:98`、`:467` | 「保**全部判定**不变的区间 `[0.012934, 0.065646]`」 | 「判定」= **仅 `trend` 路径**（`span > 2·eps·mean`）。`single`/`step`/`diff` 三条路径在区间内大面积翻转：Q1 CS-Tar 的 `n_step_exceed` 2→**6**→0、Q2 CS-C3H6 0→**5**→0；Q3 Water 超噪 8/8→**6/8**→4/8、Syngas 8/8→7/8→**6/8**。区间的 31 个格子（Q1 12 + Q2 19）里，**25 格的 `n_step_exceed` 在三个 eps 点上取值不同** | 改「保 **`trend` 路径**显著性判定不变的开区间 `(0.012934, 0.065646)`——**两端点各翻 1 格**（下端点 Q1-CS-Char 由不显著变显著、上端点 Q2-CS-C2H4 由显著变不显著）；`single`/`step`/`diff` 路径不在此区间保护范围内」。附录 A `:467` 同步改 |
| K2 | K | ②阈值沿哪条路径 | `out/02-solve.md:96`、`:200`、`:468` | 「保全部不翻栏的区间 `[2.50, 5.40]`（**含两端点**；span=2.50 的 CE-CH4 恰在下界上且**仍判 minor**）」 | 实测 `thr=2.5` → **CE-CH4 翻成 major**（不是「仍判 minor」）；`thr=5.4` 字面量 → **CS-CO 翻成 minor**（因 `CS CO span` 的浮点值是 `5.399999999999999 < 5.4`）。真实可行域是**开区间** `(2.50, 5.399999999999999)`，两端点各翻 1 格 | 改「保分栏不变的开区间 `(2.50, 5.40)`——**两端点各翻 1 格**（下端点 CE-CH4 升主量级、上端点 CS-CO 掉次量级）」。**删掉「含两端点」与「仍判 minor」**。附录 A `:468` 同步改 |
| K3 | K | ③分母是什么 | `out/02-solve.md:110` | 「它们的**分母小**（**mean** 分别 0.0377/0.168/0.007）」 | 0.0377/0.168/0.007 是 **`thr_trend` = 2·eps_rel·mean**，不是 `mean`。真 `mean` = **0.376667 / 1.680000 / 0.070000**（`results_q2.json → combos.{CS.C4H10, CE.CH4, LG.C2H6}.mean`）。差一个 `2×0.05 = 0.1` 的因子 | 改「它们的**判据阈值小**（`thr_trend` 分别 0.0377/0.168/0.007，= 2·eps_rel·mean；对应 `mean` 是 0.377/1.680/0.070）」 |
| K4 | K | ③分母是什么 | `out/02-solve.md:290`、`:292–300`；`out/01-model.md:189`、`:192–199` | Q3 表头「超噪（分母 = **档对数**：产物 8、气体 5）」与 Q1/Q2 的「分母 = **步数 = 档数−1**」并列 | **同形「N/N 超噪」在两处分母不同**：Q2 CS-H2 的「5/5」中 5 = 步数 = 6 档−1；Q3 气体 H2 的「5/5」中 5 = 档对数 = 5 档。Q1 CS-Tar 的「2/8」中 8 = 步数 = 9 档−1；Q3 产物 Tar 的「8/8」中 8 = 档对数 = 8 档。**两处都出现 5/5 与 8/8，数值巧合但分母不同** | Q3 表头改「超噪（分母 = **档对数 = 档数**，**不是** Q1/Q2 的「步数 = 档数−1」：产物 8、气体 5）」；`out/02-solve.md:283` 的「5 = 步数」保留，但补一句「Q3 同形的 5/5 分母是档对数，与 Q2 的步数只是数值巧合」 |
| K5 | K | ④合计口径 | `out/02-solve.md:18` | 「（与 §5 的「扰动参数来源 21 条」是**两个不相交集合**）」 | **事实错误**。`results_binding.json` 的 11 个 id 与 `results_perturb.json` 的 21 个 source 的**交集 = `['T_py','eps_rel']`**（2 个） | 改「11 条绑定来源里有 **2 条同时出现在扰动清单**（`eps_rel`、`T_py`），其余 9 条不在扰动清单中」 |
| K6 | K | ④合计口径 | `out/01-model.md:61` | 「阈值挪到 8，LG 的 CH4（span 6.19）与 **CS 的 CO**（span 5.40）会掉进次量级」 | 实测 `thr=8.0` 翻转 **3 格**：`[CS-CO, LG-CO, LG-CH4]`。正文只列 2 格，**漏了 LG 的 CO（span 5.705）**。「挪到 2，CE 的 CH4 会升进主量级」实测正确（`thr=2.0` 翻 `[CE-CH4]`） | 改「阈值挪到 8，CS 的 CO（5.40）、LG 的 CO（5.71）、LG 的 CH4（6.19）**三格**会掉进次量级」 |
| K7 | K | ①松弛 vs 可达（同型） | `out/02-solve.md:44` | 「被推出的那列 **R² 必然接近 1**，不能当拟合优度」 | `data/results_q1.json` **没有逐产物的 R² 键**。唯一的 R² 是 `combos.*.ilr.R2_each`，是**三元素 list（对应 3 个 ILR 坐标）**：CS `[0.977, 0.909, 0.564]`、CE `[0.575, 0.250, 0.563]`、LG `[0.822, 0.774, 0.482]`。CE 第三坐标只有 0.250，「接近 1」不成立 | 改「被推出的那列在 ILR 空间的 `R2_each` **不能当拟合优度**（CS 0.977/0.909/0.564，CE 0.575/0.250/0.563，LG 0.822/0.774/0.482）——它是**坐标级**而非**产物级**」。删「必然接近 1」 |
| K8 | K | ②阈值沿哪条路径 | `out/02-solve.md:292`、`:294`、`:296`、`:298`、`:299`、`:300`；`out/01-model.md:192`、`:195`、`:199`（共 9 处） | 行尾「8/8（**对数**）」「5/5（**对数**）」 | `code/solve.py:300–346` 的 `q3()` **没有任何 log 变换**（全文件唯一的 `np.log` 在 L363 的 `q4` 段）。「对数」在本项目另有三义：ILR 正交对数比空间（`01-model.md:31`）、对数导数（`01-model.md:82`）、对数组成 `ln S_p`（`01-model.md:311`）。Q3 表里的「（对数）」实指「CE/LG 比值跨量级」（CO2 16.73×、C2H6 3.55×、CH4 4.93×） | 9 处统一改「（比值跨量级）」或「（CE/LG 跨 1 个数量级以上）」；并在 `01-model.md` 附录 A 加一句「本文『对数』只指 ILR / `ln S_p` / `d ln S_p`；Q3 表旧标签『（对数）』不指任何 log 变换」 |
| M1 | M | ②阈值沿哪条路径 | `out/02-solve.md:199` | 「`tier_thr` +（5.0→5.5）| model | 是 | **1** | 0.0 | **翻转 1**」 | 该扰动走 `code/s3_deliver.py:85` 的 `headlines(..., tier_thr=)` 与 `:92` 的 `span >= tier_thr`，**不走** `code/solve.py:271` 的硬编码 `span >= 5.0`（后者只生成 `results_q2.json` 的 `tier` 字段）。正文没写这条分叉，读者会以为与 L271 自相矛盾 | 补一句「本行翻转由 `s3_deliver.py` 的 `headlines(tier_thr=)` 重算；`solve.py:271` 的 `5.0` 是 `results_q2.json` 的 `tier` 字段专用，两处不是同一段代码」 |
| M2 | M | ④合计口径 | `out/02-solve.md:45` | 「单跑一次端到端 **210.629 ms**（§2）」 | 18:06 那次运行的读数；盘上 `results_timing.json` 现值为 **254.609**（`out/03-numbers.md:504`）。§2 表头（`:58`）已声明批次，本句未声明 | 改「单跑一次端到端 210.629 ms（**2026-11-19 18:06 那次运行**；盘上现值 254.609）」 |
| M3 | M | ③分母是什么 | `out/02-solve.md:75` | 「差 **−3.335 ms（−1.56%）**。这不是算术矛盾，是两次独立测量之间的噪声……」 | 与 `:74` **同句重复**：`:74` 已给「−1.56% = 3.335/213.964（五问之和为基）、+1.93% = 4.918/254.609（pipeline 为基）」。重复句会让读者以为有两个不同的 −1.56% | 删 `:75` 首句「差 −3.335 ms（−1.56%）」，保留其后半句「这不是算术矛盾……故报中位不报单次」 |
| M4 | M | ⑥单位 | `out/02-solve.md:339` vs `:350` | `:339`「区间半宽示例（Tar @ r=0.15）：`[15.20, 17.72]`」**不给百分比**；`:350`「区间半宽示例（Tar @ r=0.15）：`[32.16, 44.17]`（**半宽/中点 = 15.73%**）」 | 两处同一口径（半宽/中点），一处标一处不标；`[15.20,17.72]` 是 **CS** 的 Tar，`[32.16,44.17]` 是 **CE** 的 Tar，同形不同组合 | 给 `:339` 补「半宽/中点 = (17.72−15.20)/(2×16.41) ≈ 7.7%」，或在两处统一写「半宽/中点」并各标组合名 |
| M5 | M | ④合计口径 | `out/02-solve.md:465` | 「扰动计数 | **42 / 16 / 14 / 12 / 1 / 15 / 1**」 | 七个数字挤在一格且无标签。对应 `meta.counts` 的键序是 `attempted / model_perturb / query_move / never_read / model_infeasible / flip_denominator / model_runs_with_flip` | 改「42 `attempted` / 16 `model_perturb` / 14 `query_move` / 12 `never_read` / 1 `model_infeasible` / 15 `flip_denominator` / 1 `model_runs_with_flip`」 |
| M6 | M | ③分母是什么 | `out/03-numbers.md:13` vs `:23` | `:13`「非注释区**数字 token 26 个**」与 `:23`「挖掉元数据与占位符后**一个结果数字都没有**（0 个 token）」并列 | **两个不同分母**：26 = 非注释区全部数字 token（含队号/页码/文献宽度）；0 = **结果**数字 token。`:12` 的 `skeleton` 判据用的是后者 | `:23` 补「（与 `:13` 的 26 不是同一计数：26 含队号/页码/文献宽度等元数据）」；或把 `:13` 改写成「结果数字 token 0 个；其余元数据数字 token 26 个」 |
| M7 | M | ③分母是什么 | `out/01-model.md:319` vs `:321` | `τ_single` 量级「**0.007**–5.817（产物 0.819–5.817）」与 `τ_trend` 量级「**0.007**–5.734」 | 两者下界同为 0.007，都来自 **LG 的 C2H6**（`y ≈ 0.07`）；但只有 `τ_trend` 的注释写了「分母小会放大比值」，`τ_single` 没有 | 给 `τ_single` 补同款注释「下界 0.007 来自 LG C2H6（y≈0.07）；产物段 0.819–5.817」 |
| M8 | M | ⑥单位 | `out/02-solve.md:96` | 「贴线格 `CS-CO span=5.400`（gap **8.0%**）、`LG-CO span=5.705`（gap 14.1%）」 | `span` 单位是 mL/g(daf)；`gap%` 的分母是**声明值 5.0**（`code/s3_deliver.py:325`：`100·|span−5.0|/5.0`），**不是 span 本身**。另 `CS-CO span` 的浮点值是 `5.399999999999999`（见 #K2） | 补「gap% 的分母是声明值 5.0，不是 span」；`5.400` 后加「（浮点值 5.399999999999999，见 #K2）」 |
| M9 | M | ③分母是什么 | `out/02-solve.md:228` vs `out/01-model.md:134` | 两处 ratio 列名都写 `span/(2·eps·mean)`，但 `01-model.md:134` 表头**只有「末-首｜相对首档｜ratio」三列，没有 span 列** | ratio 的分子是 **span = max−min**，不是「末−首」。Δ≠span 的有 6 格：CS Char 末−首 +0.66 / span 0.760（ratio 0.2587 vs 用末−首算 0.2247，差 15%）、CS Syngas +2.49/3.96、CE Char +3.18/3.48、CE Syngas −2.76/3.98、LG Char −0.74/1.19、LG Syngas +2.22/3.41 | `01-model.md:134` 加一列「span（= max−min）」；或把 ratio 列改成「ratio（分子是 span，**不是**末−首；逐格 span 见 `02-solve.md:228`）」 |
| M10 | M | ⑤可行 vs 不可行 | `out/02-solve.md:22` | 「±10% 下**头条定性结论零翻转**」 | 分母是 **15 次可行模型扰动**（不含 14 `query`、12 `never-read`、1 不可行）。同段 `:206–208` 写清了，摘要句没写 | 改「**15 次可行模型扰动**下头条定性结论零翻转」 |
| M11 | M | ④合计口径 | `out/02-solve.md:206` | 「Q1 的 `trend` 判定（**12 个产物格**）……在 15 次可行模型扰动里一次都没动」 | 12 是 Q1 产物格总数；而 #K1 的 eps 保判区间统计的是 **31 格**（Q1 12 + Q2 19）。两个格数出现在相邻两节，读者易把 12 当成 eps 区间的格子数 | 补「（Q1 12 格；`eps` 保判区间另统计 Q1 12 + Q2 19 = **31 格**，见 #K1）」 |
| L1 | L | ⑥单位 | `out/01-model.md:326–327` vs `:219–220` | 符号表单位写 `s^-1`；同文件正文写 `s⁻¹` | 同一单位的两种写法（ASCII 上标 vs Unicode 上标），属排版不一致，不是数值口径错 | 统一为 `s⁻¹` |
| L2 | L | ⑥单位 | `out/01-model.md:334` | `t_hold` 单位列写 `min（30）` | 单位格混进了数值 30，而「量级（实测）」列已写 30 | 单位列只写 `min` |
| L3 | L | ③分母是什么 | `out/02-solve.md:98` | 「上侧余量 0.015646（eps 的 **31.29%**）、下侧 0.037066（**74.13%**）」与同句「**全宽**为声明值 `eps=0.05` 的 **105.42%**」 | 三个百分数的分母**都是声明值 0.05**，但只有「全宽」那处写了分母；另两处的 31.29% / 74.13% 是「余量 / 0.05」，不是「余量 / 全宽」 | 补「三个百分数的分母都是声明值 `eps=0.05`」；或把「全宽」改写成「全宽 0.052712（= 声明值的 105.42%）」 |

---

## 2 保留区（**已自带双口径说明，不要重改**）

以下 9 条看着像「同词两用」，但正文已把两个口径并列写出。若按 §1 的风格再改一遍，会把已经说清的地方改乱。

| 行号 | 原文要点 | 为什么已合格 |
|---|---|---|
| `02-solve.md:17`、`:72` | `q1` 占 pipeline **74.2%**（18:06 那次）vs 盘上现值 **74.51%**（189.718/254.609） | 同句已括注两个数与来源（`03-numbers.md:499,504`） |
| `02-solve.md:74` | **−1.56%** = 3.335/213.964（五问之和为基）vs **+1.93%** = 4.918/254.609（pipeline 为基） | 明写「不是同一个基数的两个读数」「该差值随运行变号，不可当固定偏差引用」 |
| `02-solve.md:20`、`:180–185` | 42 = 16 model + 14 query + 12 never-read；12 次「**不等于不可行**」；真正不可行 1 次 | 这是对派单先验口径的**纠正**，与 §0 第 2 条一致，必须保留 |
| `02-solve.md:216–217` | 「42 次里 30 次不翻转」会把分母从 15 吹到 **27**（27 = 15+12，不是任何实测计数） | 已自带反事实标注「这是反事实，不是实测值（实测 1/15 = 6.67%）」 |
| `02-solve.md:43` | CS-Tar 单格翻转点 `eps* = 0.2519`，**不是** §3 那个区间上界 `0.065646` | 已括注「后者由另一格 CS-C2H4 的 ratio 决定」。**但「保全部判定」这个词要按 #K1 改成「保 trend 判定」** |
| `02-solve.md:350` | 「半宽/中点 = 15.73%」与 §3「全宽 105.42%」是两套算法 | 明写「那里是全宽/声明值，这里是半宽/中点」 |
| `02-solve.md:283` | 「5/5 超噪（5 = **步数** = 档数−1；Q2 的 CS 共 6 档，档数另计）」 | 已把「步数」与「档数」分开。只需按 #K4 补一句与 Q3 的区分 |
| `02-solve.md:19` | ★ 5 个、★★ 12 个，**三组合合计**（CS 1/4、CE 2/4、LG 2/4） | 合计与分解都写了，且与 `results_boundary.json` 实测一致（★5 / ★★12，`max_abs_diff_on_overlap = 0.0`） |
| `01-model.md:215` | CS 气相碳末−首 **−2.30%** vs max−min **2.91%**（1.2618 倍） | 明写「『守恒』按 span 读是 2.91% 不是 2.30%」。仅 CS 有此差异，CE/LG 单调故 span=delta（`results_q4.json → carbon_balance` 实测 `monotone=True`） |

---

## 3 复算命令（每条都能独立跑，输出即证据）

```powershell
# ① #K5：binding 与 perturb 的来源集合不是不相交，交集是 ['T_py','eps_rel']
E:\Mini\envs\mathmodel\python.exe -c "import json;d=r'E:\数学建模\PRACTICE_2023B\data';b=json.load(open(d+r'\results_binding.json',encoding='utf-8'));q=json.load(open(d+r'\results_perturb.json',encoding='utf-8'));print(sorted(set(s['id'] for s in b['sources'])&set(r['source'] for r in q['runs'])))"

# ② #K2 + #K6：A7 端点与 thr=8 的翻转格
E:\Mini\envs\mathmodel\python.exe -c "import json;d=r'E:\数学建模\PRACTICE_2023B\data';q=json.load(open(d+r'\results_q2.json',encoding='utf-8'));c=[(k,g,v['span'],v['tier']) for k,r in q['combos'].items() for g,v in r['gases'].items()];f=lambda t:[(k,g) for k,g,s,ti in c if ('major' if s>=t else 'minor')!=ti];print(len(c),f(2.5),f(5.4),f(5.5),f(8.0))"
# 输出：19 [('CE','CH4')] [('CS','CO')] [('CS','CO')] [('CS','CO'),('LG','CO'),('LG','CH4')]

# ③ #K3：CE-CH4 的 mean 与 thr_trend 是两个数（0.168 vs 1.68）
E:\Mini\envs\mathmodel\python.exe -c "import json;d=r'E:\数学建模\PRACTICE_2023B\data';q=json.load(open(d+r'\results_q2.json',encoding='utf-8'));print([(g,round(v['mean'],6),round(v['thr_trend'],6),round(v['span_over_thr'],4)) for g,v in q['combos']['CE']['gases'].items()])"

# ④ #K1：eps 区间只保 trend 路径（把 eps 换成端点重算 Q3 的 diff 超噪）
E:\Mini\envs\mathmodel\python.exe -c "import json,math;d=r'E:\数学建模\PRACTICE_2023B\data';q=json.load(open(d+r'\results_q3.json',encoding='utf-8'));ne=lambda e:{k:sum(1 for a,b in zip(v['CE'],v['LG']) if abs(a-b)>2*math.sqrt((e*a)**2+(e*b)**2)) for k,v in q['products'].items()};print([(e,ne(e)) for e in (0.012934,0.05,0.065646)])"
# 输出里 Water 8→6→4、Syngas 8→7→6，即 diff 路径在区间内翻
```

`code/s3_deliver.py:360–396` 的 `ratios` 只收集 `span_over_thr` 与 `trend_significant`（Q1 12 产物 + Q2 19 气体 = **31 格**），所以 `eps_band_keeping_all_significance` 这个名字里的 `all_significance` 严格讲只覆盖 `trend` 一条路径——这是 #K1 的代码侧根源。

---

## 4 一句话交接

K 级 8 条里有 6 条集中在 **A7 / eps_rel 两个「保…不变的区间」**上（#K1、#K2、#K4、#M1、#M8，加 #K6 的漏格）：它们的共同病根是「一个区间名同时承诺了多条判据」。改法一律是**在区间名后面挂路径限定语 + 写清端点开闭**，不动任何数字。改完这 6 条，`02-solve.md:96/98/199/200/467/468` 与 `01-model.md:61` 六处即可闭环。

VERDICT: PASS
