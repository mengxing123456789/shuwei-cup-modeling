BYTES 17823

# 10-caliber · 口径审计：同一个词被两种算法用过

- 被测目录：`E:\数学建模\PRACTICE_2023B`
- 审计时刻：2026-11-19 20:39–20:52
- 唯一产出：本文件 `E:\数学建模\PRACTICE_2023B\review\10-caliber.md`
- 审计对象：见 §0（main.tex 是空壳，真正的量化载体是 `out/*.md`）
- 结论：检出 12 组"同词两义"，其中 5 组夹带的是**事实错误**（不是"两数都对"），当前正文口径**不通过**

---

## 0 被测对象状态（必须先讲清，否则表里的 file:line 对不上）

- `main.pdf` **不存在**；`main.tex` 是未填的骨架：106 行 / 4546 B，含 69 处 `<<>>` 占位符、**0 个结果数字**（mtime 16:49:15）。所以"论文正文里的数字"目前只存在于下列三个交付草稿中，它们是将被灌进 main.tex 的数字来源：
  - `out/01-model.md`（347 行 / 24589 B，模型与符号）
  - `out/02-solve.md`（473 行 / 38249 B，求解结果叙述）
  - `out/03-numbers.md`（713 行 / 47942 B，BYTES 47942，claims=547，数字台账）
- `review/00-metrics.md` **缺失**（派单脚本未生成）。本报告因此不能引用它作基线，改为现场直接抽 `data/*.json`；若日后 00-metrics.md 出现，以其为准并复核本表 §2。
- **代际（R-V11 快照核对）**：`main.tex` 16:49:15 ⊂ `data/*.json` 18:26:41–18:26:55 ⊂ `out/*.md` 20:04–20:05 ⊂ `code/verify_numbers.py` 20:03:52。即被审的"被测件"main.tex 落后数据层约 1h37m；但真正的内容载体（drafts 20:04）**晚于**数据层（18:26），现场抽读 `189.718 / 254.609` 与 18:26 数据逐位一致 → 对本报告所审载体**无陈旧覆盖风险**。唯一"旧代数"是 `out/02-solve.md:17,72` 的 `156.304 / 74.2%`（18:06 那次重跑），正文已自带盘上现值对照。
- **timing 在三次重跑间漂移**：18:06 → q1=156.304 / pipeline=210.629；18:16/18:18 → 157.518 / 287.903；18:26 → 189.718 / 254.609。这本身是 K1"耗时占比"口径不稳的直接证据（同一个词，不同代）。

---

## 1 机器口径三条（原文粘贴；三条均 FAIL，原因是缺 PDF / 缺 mmkit，非内容错）

```
$ E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\review_check.py E:\数学建模\PRACTICE_2023B
[FAIL] X-pdf  找不到 PDF
pdf: None  pages: 0
VERDICT: FAIL (fail=1)
[exit code: 1]

$ E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py E:\数学建模\PRACTICE_2023B
[FAIL] paper resolved (main.pdf 不存在或<150KB)
[FAIL] main.pdf exists
0/2 PASS
[exit code: 1]

$ E:\Mini\envs\mathmodel\python.exe -m mmkit.figfont main.pdf
ModuleNotFoundError: No module named 'mmkit'
[exit code: 1]
```

> 三条全过不了的根因是**没有 main.pdf**（论文尚未由 tex 编译成稿），不是数字错误。因此本卷只能从"数据层 + 交付草稿"这一层审口径，不能审排版/图内字号。

---

## 2 口径冲突总表（核心交付物）

> 记法：`取值A`/`取值B` 各给 `出处 file:line` + `JSON 键` + `生成函数（code/*.py 函数:行）`。
> "生成函数"行的行号均已在 `code/solve.py`、`code/s3_deliver.py` 现场核对（复算命令见 §5）。
> 判定"冲突"的硬标准：**两取值来自不同函数，或同一函数不同参数/不同分母**。

| # | 词 | 取值 A（出处 file:line + JSON键 + 生成函数） | 取值 B（同） | 是否冲突 | 处置建议 |
|---|----|------|------|:---:|------|
| 1 | 耗时占比（q1 占端到端/流水线） | `out/02-solve.md:17,72` 「q1 156.304 ms 占 pipeline **74.2%**」；键 `results_timing.json→calls[name==q1].median_ms / calls[name==pipeline_q1_to_q5].median_ms`（156.304/210.629，18:06 旧代）；生成 `s3_deliver.py:148 part_timing`（每调用取 median，L148-193） | `out/02-solve.md:98,104`「盘上现值 189.718/254.609=**74.51%**」（18:26 当代，同键同函数）；若分母改用五问纯算力和 `sum5=259.527` 得 **73.10%**（第三个分母） | 是 | 两个都留但改名区分：`占串行流水线(q1..q5)耗时比`（分母 254.609）与 `占五问纯算力和比`（分母 259.527）；删/改 156.304 旧代印数并统一到当代；表注写明"流水线含各问模型加载，纯算力和只是五问中位相加" |
| 2 | Tar 变化幅度（相对首档 %） | CS Tar **−37.667%** → 相对**纯棉秆 0/100 基线**；键 `results_q1.json→combos.CS.products.Tar.delta_end_pct=-37.667`；生成 `solve.py:174 delta_end_pct=100·(y[-1]-y[0])/y[0]`；出处 `out/02-solve.md:95`(C6)、`out/01-model.md:267` | CS Tar **−29.681%** → 相对**10/100 基线**；键 `results_binding.json→sources.*.C6.CS_Tar_pct_vs_10/100`；生成 `s3_deliver.py:296 =100·(y[-1]-y[1])/y[1]`；CE +31.551% / LG −54.651% 只有 10/100 口径（无 vs0 值） | 是 | 两个都留但改名区分：`相对首档(0/100)` vs `相对二档(10/100)`；表里补 vs0/vs10 两列（现 CS 有 vs0、CE/LG 缺，横向不可比——`out/01-model.md:87` 已警示） |
| 3 | 超噪 N/N 的分母 | Q3「8/8、5/5」的 N＝**档对数**（产物 8 对、气体 5 对）；键 `results_q3.json→products.<p>.n_exceed / n`（n=8）、`gases.<g>.n_exceed / n`（n=5）；生成 `solve.py:321 n=len(lev)`、`solve.py:337 n=len(levg)`；出处 `out/02-solve.md:290-300`、`out/01-model.md:189` | Q1/Q2「5/5、2/8」的 N＝**步数=档数−1**（CS 8、CE/LG 7；CS 5、CE/LG 4）；键 `results_q1.json→combos.<x>.products.<p>.steps`（长度）、`results_q2.json→combos.<x>.gases.<g>.n_step`；生成 `solve.py:180 n_step=len(dy)`、`solve.py:268 n_step=len(dz)`；出处 `out/01-model.md:228,259` | 是 | 只保留一个口径并改掉另一处：统一为"步数"（与显著性判定同一分母）；Q3 若必须用档对数则改名 `超噪档对数`，禁止与"步数"同列混排 |
| 4 | mean（Q2 气体均值） | 正文「mean 分别 **0.0377 / 0.168 / 0.007**」——实为 **阈值 thr_trend**；键 `results_q2.json→combos.<x>.gases.<g>.thr_trend`；生成 `solve.py:265 thr_trend=2·eps·|y|.mean()`；出处 `out/02-solve.md:104,109,110` | 真 `mean` ＝ **0.377 / 1.68 / 0.070**；键 `results_q2.json→combos.<x>.gases.<g>.mean`；生成 `solve.py:264 mean=|y|.mean()` | 是 | 只保留一个口径并改掉另一处：正文"mean=0.0377…"改为"阈值 thr_trend=0.0377…"；真均值另列或删（两值差约 10×，读者必误读） |
| 5 | eps「保全部判定不变」区间 | 正文「保全部判定不变 **[0.012934, 0.065646]**，全宽 105.42%」，暗示对"全部判定"成立；键 `results_binding.json→sources.*.eps_band_keeping_all_significance`；生成 `s3_deliver.py:379`；出处 `out/02-solve.md:98,467` | 该区间实际只扫 `s3_deliver.py:361-368` 收集的 **trend 路径 31 格（Q1 12 + Q2 19）**；换 `thr_single/thr_diff` 检验时区间内仍翻判（三检验各自 eps* 不同） | 是 | 在表注写明各自定义：「保全部判定」限定为"trend 检验下 31 格"；若要覆盖 single/step/diff 须重算并给更窄区间 |
| 6 | A7「保全部不翻栏区间 [2.50,5.40]（含两端点；仍判 minor）」 | 正文称含两端点、span=2.50 的 CE-CH4 仍判 minor；键 `results_boundary.json→combos.*.band_keeping_all_tiers`；生成 `s3_deliver.py:321`；出处 `out/02-solve.md:96,468` | 实测 thr=2.5 时 CE-CH4(span2.5) 判 **major**（`span>=thr`），thr=5.4 时 CS-CO(span5.4) 跌 minor → 真区间是**开区间 (2.5, 5.4)**，端点不保 | 是（且为**事实错误**，非"两数都对"） | 只保留一个口径并改掉另一处：把"含两端点/仍判 minor"改为"开区间 (2.5, 5.4)，端点处 CE-CH4 / CS-CO 翻栏"；区间写 `(2.5,5.4)` 不用 `[ ]` |
| 7 | R²（拟合优度） | 正文「被推出那列 R² **必然接近 1**，不能当拟合优度」——指 product 级 ILR 逐坐标 R2_each；键 `results_q1.json→combos.<x>.ilr.*`（每组合 3 个坐标 R²）；生成 `solve.py:192-195 R2_each`；出处 `out/02-solve.md:44`、`out/01-model.md:27` | 同句外又用 R² 指"产物级整体拟合优度"（一个数）；逐坐标反例：CE 坐标2 R²=**0.250**（远非接近 1），见 `combos.CE.ilr` | 是（"必然接近1"被 CE 0.25 证伪，是全称错误） | 两个都留但改名区分：`逐坐标 R²`（列 3 值）与 `产物级 R²`；删掉"必然接近 1"的全称断言 |
| 8 | 敏感度"宽度%"的分母 | 边界半宽示例 `[15.20,17.72]`「半宽/中点=**15.73%**」，分母＝**区间中点**；键 `results_boundary.json→combos.*`；出处 `out/02-solve.md:339,350` | eps「全宽 **105.42%**」，分母＝**声明值 eps0**；键 `results_binding.json→sources.*.band_width_pct_of_eps`；生成 `s3_deliver.py:380 =100·(hi-lo)/eps0` | 是 | 两个都留但改名区分：`相对中点半宽%` vs `相对声明值全宽%`；表注写清（正文 L350 已并列两算法，但未命名） |
| 9 | "不可行/没跑到"的计数 | 「42=16 model+**14 query+12 never-read**」中的 12 ＝ **never_read**（从未读取）；键 `results_perturb.json→`（runs/infeasible 统计）；生成 `s3_deliver.py:535 part_perturb`；出处 `out/02-solve.md:20,465` | **model_infeasible=1**（真正无可行解）；键 `results_perturb.json→infeasible`；同函数 `part_perturb.model_infeasible` | 是 | 两个都留但改名区分：`从未读取(never_read)=12` 与 `求解不可行(model_infeasible)=1` 分列；表注点明"12 个不是不可行" |
| 10 | "相对 RMSE"（Q5 留一） | `out/01-model.md:228-234` 表与 `out/02-solve.md:361` 写**比值**：CS.Char **0.009**、CE.Water **0.187**；键 `results_q5.json→combos.<x>.point.<p>.loo_rmse_rel`；生成 `solve.py:472 loo_rmse_rel=rmse/mean` | `out/03-numbers.md:480-495,668-678` 写**百分数**：CS.Char **0.892069**、CE **18.7**（`100*loo_rmse/mean`，键 `loo_rmse_rel%`）；`out/01-model.md:364` 又写"±18.7%" | 是 | 只保留一个口径：跨文件统一用比值（0.009）/或统一百分数（0.9%）；若两处都留必须表注 `比值×100=百分数`（0.0089↔0.89%） |
| 11 | "变化幅度/跨度"（ratio 的分子） | ratio 分子用 **span=max−min**；键 `results_q1.json→combos.<x>.products.<p>.span`（CS Tar span=7.33）；生成 `solve.py:169 span=y.max()-y.min()`；`out/01-model.md:228` 表头明写 span=max-min | 同表唯一"幅度"列印 **末−首=delta_end**；键 `...delta_end`（CS Tar=−7.33）；生成 `solve.py:173`；6 格单调反常时 span≠|末-首|，读者以为是同一"变化量" | 是 | 只保留一个口径并改掉另一处：表里补 `span` 列（现缺，`out/01-model.md:134` 表头无 span），明确 `ratio=span/(2·eps·mean)`；"末−首"另列 |
| 12 | gap%（贴线偏离） | A7「CS-CO span 5.400（**gap 8.0%**）」——分母＝**阈值 5.0**；键 `results_binding.json→sources.*.C6/…A7.*.gap_pct`；生成 `s3_deliver.py:325 gap_pct=100·|span−5.0|/5.0`；出处 `out/02-solve.md:96` | 读者易按"相对 span"读：0.4/5.4=**7.4%**（另一分母） | 是 | 在表注写 `gap%=|span−5|/5`（相对阈值），或改名 `偏离阈值%`；避免被读成相对跨度 |

**统计：12 组 = 8 组"两数都对、同词两义"（#1,2,3,4,8,9,10,11,12 中除事实错误者）+ 3 组夹带事实错误（#5 全称过宽、#6 端点断言错、#7"必然接近1"被证伪）。**

---

## 3 与既有 out/05-caliber.md 的对照

- 本波已有 `out/05-caliber.md`（18881 B，审同一组 `out/01-model.md`、`out/02-solve.md`、`out/03-numbers.md`；结论 VERDICT: PASS；登记 22 处 = 8 K + 11 M + 3 L，并含 §2 保留区 9 条）。
- 交叉核对结果：本表 §2 的 #1、#2、#3、#4、#6、#8、#10 落在其 K/M 清单内（K1 耗时占比、K2 Tar 双基准、K3 超噪分母、K4 mean 错标、K7 R² 全称），**独立复现一致**。
- 本表相对它的增量（它缺的）：
  1. 每行补 **JSON 键 + 生成函数:行号**（out/05-caliber.md 只到 file:line 叙述，未回溯到 `solve.py`/`s3_deliver.py` 的算出点）——这是本卷能"复算"的前提；
  2. 新增 **#11 变化幅度 span vs 末-首**（ratio 分子口径）与 **#12 gap% 分母=阈值**，这两条 out/05-caliber.md 未列；
  3. 明确把 **#5/#6/#7** 从"措辞缺陷"升级为"事实错误"（out/05-caliber.md 记作 M 级措辞，本卷实测端点翻栏/CE R²=0.25，判为错误）。
- 判定口径差异：out/05-caliber.md 末行 PASS 是按"数字本身可复算、只需改措辞"给的；本卷末行给 **FAIL**，是按"当前正文仍同词两义且含事实错误、尚未回改"给的。两者不矛盾——同一份材料，一个评"底层数字可信"，一个评"呈现口径当前是否过关"。

---

## 4 保留区（看着像同词两用，但正文已标"两个基数/两套算法"，本卷不判为新缺陷，仅登记别再双重标记）

- `out/02-solve.md:74` −1.56%=3.335/213.964（五问和基）vs +1.93%=4.918/254.609（pipeline 基）——已明标两基数。
- `out/02-solve.md:96` CS-CO gap 8.0% / LG-CO gap 14.1%——分母 5.0 已可推，列 #12 只为命名。
- `out/02-solve.md:350` 半宽/中点 15.73% 与全宽 105.42%——正文已并列"两套算法"，列 #8 只为命名。
- `out/02-solve.md:95` C6 CS −37.667 / CE +31.551 / LG −54.651——三列各自纵向读，`out/01-model.md:87` 已写"两个百分数不可横向比较"，列 #2 为核心冲突本体。
- `5.400` 与 `5.399999999999999` 浮点同一值，非口径冲突。

---

## 5 复算命令（别人拿同一份数据/代码可逐条验证本表）

```bat
:: 1) 定位"生成函数:行号"（每个词算出点）
findstr /n "delta_end_pct span span_over_thr n_step thr_trend loo_rmse_rel R2_each" code\solve.py
findstr /n "CS_Tar_pct_vs_10 gap_pct band_keeping_all_tiers eps_band_keeping_all_significance never_read model_infeasible part_timing" code\s3_deliver.py

:: 2) 打印本表引用的 JSON 数值（键名以本机实际为准，见下）
E:\Mini\envs\mathmodel\python.exe -c "import json;t=json.load(open(r'data/results_timing.json',encoding='utf-8'));print({c['name']:c['median_ms'] for c in t['calls']})"
E:\Mini\envs\mathmodel\python.exe -c "import json;q=json.load(open(r'data/results_q1.json',encoding='utf-8'));p=q['combos']['CS']['products']['Tar'];print(p['delta_end_pct'],p['span'],p['mean'],p['thr_trend'])"
E:\Mini\envs\mathmodel\python.exe -c "import json;q=json.load(open(r'data/results_q2.json',encoding='utf-8'));print(q['tiers']['CS']);print(q['combos']['CS']['gases']['C4H10']['mean'],q['combos']['CS']['gases']['C4H10']['thr_trend'])"
```

```bat
:: 3) 万能反查：给一个数值，打印它在 data/*.json 里的完整路径（任何一行的取值都能这样回溯）
E:\Mini\envs\mathmodel\python.exe -c "import json,glob
def walk(o,p=''):
 for k,v in (o.items() if isinstance(o,dict) else enumerate(o) if isinstance(o,list) else []):
  if isinstance(v,(dict,list)): yield from walk(v,p+'/'+str(k))
  else: yield p,v
TARGET=float(input('target='))
for f in glob.glob(r'data/*.json'):
 try: d=json.load(open(f,encoding='utf-8'))
 except: continue
 for p,v in walk(d):
  if isinstance(v,(int,float)) and abs(v-TARGET)<=1e-6*max(1,abs(TARGET)): print(f,p,v)"
```

> 说明：§2 各行的"JSON 键"是根据本机 `data/*.json` 现行结构写的最短路径；若键名有出入，用第 3 段"万能反查"按**数值**定位，任何一条结论都可被第三方用同一条命令复算——这正是 out/05-caliber.md 未提供、本卷补上的可复算性。

---

## 6 判据锚（[判断] 声明）

对照 `E:\数学建模\APMCM-PROBLEMS\_official_criteria.json`（12 条判据 C1..C12，覆盖 19 份官方规范），其中 **没有任何一条 C 编号规定"同名词必须单一含义"**——C 系列管的是格式、附录、摘要、引用等硬项（此点与本波 `out/09-numbers.md` §6.4 一致：C1–C12 不要求"每个数字可复算"）。因此本卷"同词两义＝缺陷"属**内部自洽性[判断]**，不是官方 C 编号硬项。理由链：读者在同一篇里遇到两处标同一名词、实为两种分母/两种函数产物时，会误以为在看同一个量；这是**可读性与诚实呈现**的自设标准，非官方成文要求。凡上表结论，均已给"出处 file:line + JSON 键 + 生成函数:行"三重锚，可被独立复算，不依赖 C 编号。

**2026_C 四例在本论文的映射与缺席声明**：题面给的 `4.608%/4.506%`(W=800/793)、`0.86%/0.8608`、`0.1317=tiers3+4+5 / 0.0148=tiers4+5`、`532/300 运行费` 经全库 grep **均不存在**于本论文任何文件（无 `4.608|4.506|0.8608|0.1317|0.0148|W=800|W=793|闲置面积|NPV` 命中）。本卷按"同一缺陷类型"映射到本论文的对偶实例：`4.608/4.506`↔#2 Tar 双基准；`0.86%/0.8608`↔#10 相对 RMSE 比值/百分数；`0.1317/0.0148`(tiers 分层)↔#3 超噪 N 分母(档对/步数)差分1；`532/300`(含不含折旧)↔#1 耗时占比含不含流水线开销。

---

## 7 结论

- **检出 12 组同词两义**；其中 #5/#6/#7 为事实错误（须改正文，不是改名可了）。
- 处置分布：**只保留一个并改另一处** → #3,#4,#6,#7,#10,#11；**两个都留但改名区分** → #1,#2,#8,#9；**表注写明定义** → #5,#12。
- 十二条里 8 条已被 `out/05-caliber.md` 以措辞级登记；本卷补上"JSON 键+生成函数:行号"溯源与 #11/#12 两条新冲突，并把 #5/#6/#7 升级为事实错误级。
- 当前 `out/*.md` 正文口径**未通过**：至少 #6(端点翻栏仍写"含两端点/仍判minor")、#4(mean 实为阈值)、#7("必然接近1"被 CE R²=0.25 证伪) 仍是会误导读者的成句断言。回改后（只动措辞与限定语、不动数字）方可转 PASS。

VERDICT: FAIL
