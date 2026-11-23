# 数维杯复用手册

一份可以直接照做的作战手册。分五块：**流水线**（怎么跑）、**技能**（用什么）、**C 题完整链路**（一个真实案例的全套方法与数字）、**Modex 逆向要点**（商业工作台的流程契约）、**踩坑清单**（20 条，每条都付过代价）。

---

## 一、流水线：八步二十门

入口技能 `mathmodeling`，一条命令起全套：

```powershell
$PY = 'E:\Mini\envs\mathmodel\python.exe'
$SK = 'E:\数学建模\.agents\skills\mathmodeling'

& $PY "$SK\scripts\run_all.py" 'E:\数学建模\<新题目录>' --type C --problem-file '<新题目录>\problem\problem.txt'
& $PY "$SK\scripts\pipeline.py" '<新题目录>' --status     # 断点续跑看状态
& $PY "$SK\scripts\submission_gate.py" '<新题目录>' --stage final
```

### 1.1 八步与它们的门（`scripts/pipeline.py` 的 `STEPS`）

| 步 | 名称 | 成员 | 门 | 这一步的法定产物 |
|---|---|---|---|---|
| s1 | 赛题分析 | 题目侦察手、数据溯源手、真题对标手 | G1 G2 G20 | `out/00-problem.md`（逐句抄出"要求你"）、`data/ledger.json`、`out/15-benchmark.md` |
| s2 | 建模求解 | 建模架构手 | G3 | `out/01-model.md`（每问的模型 + 为什么不是别的） |
| s3 | 编程实现 | 求解与优化手、代理模型训练手、数值对账手 | G4 G5 G10 | `code/`、`data/*.json`、`out/03-numbers.md` |
| s4 | 口径审计 | 口径审计手 | G16 | `out/05-caliber.md`（同一个词不许被两种算法用过） |
| s5 | 图表 | 图表手 | G6 G11 | `figures/*.pdf`、`out/08-figures.md` |
| s6 | 论文撰写 | 论文撰写手、附录与自指手 | G7 G12 G17 | `main.tex`、`out/09-writing.md`、`out/13-appendix.md` |
| s7 | 编译合规 | 格式合规手、版式与出栏手、流水线运维手 | G8 G13 G14 G15 G18 G19 | `main.pdf`、`out/03-compliance.md`、`out/10-layout.md`、`out/14-ops.md` |
| s8 | 评审收口 | 13 人审阅队 | G9 | `review/*.md` |

### 1.2 二十道门各判什么（`pipeline.py` 的 `GATES`）

| 门 | 名称 | 判据 |
|---|---|---|
| G1 | 题面 | 逐句抄题 + 常量表；题面必须是文本层（扫描件判 FAIL） |
| G2 | 数据台账 | 每个数据文件有 sha256 + 来源 + 判据，`NOT-APPLICABLE` 要显式写 |
| G3 | 模型 | 符号冲突消解；每问有目标函数/方程 |
| G4 | 求解 | `out/02-solve.md` 有算法名 + 关键参数 + 复杂度 |
| G5 | 数字对账 | `code/verify_numbers.py` 末行 `failures=0` |
| G6 | 图表 | 图 pdf+png 双份、图内字号 ≥6 pt |
| G7 | 正文形态 | `review_bench` 12 项 `fail=0 unknown=0` |
| G8 | 编译合规 | `gauntlet_check.py` 16/16 |
| G9 | 评审收口 | 审阅队报告全部落盘 |
| G10 | 表格数据 | 表内数字能回到 `data/*.json`（**软门**） |
| G11 | 视觉审查 | 图不糊、不出栏（**软门**） |
| G12 | 论文数字 | 正文每个数字都能追到 JSON 的键 |
| G13 | 投稿体检 | `paper-kit` 的 `venue_submission_check.py` 无 error |
| G14 | 模板核对 | 与官方 cls/cfg 一致（**软门**） |
| G15 | 源文件闭包 | 全部源程序在附录或支撑材料里，且能跑 |
| G16 | 口径审计 | 同一个词（误差/精度/R²）不许两种算法混用 |
| G17 | 附录自指 | 页数/字数/图数由产物决定，不许手写 |
| G18 | 版式出栏 | 无 overfull、无 undefined、无裸数字 |
| G19 | 流水线自检 | 状态文件 schema 与步骤表一致，`??` 不许当 PASS |
| G20 | 真题对标 | 查语料、给出「可照搬/会死/新增约束」三条结论 |

软门只有 **G10 / G11 / G14**——它们不阻断，但会出现在 `--status` 的未过清单里。判不出（`None`）不拦，判不过（`False`）照样拦。

### 1.3 三条不可让步的纪律

1. **数字只有一个来源。** 正文不许出现手写结果数字。C 题的做法：`main.tex` 里全是 `\slotXxx` 宏，`code/fill_numbers.py` 从 `data/*.json` 生成 `slots.tex`，`audit/check_slots.py` 检查"有没有未定义槽 / 有没有裸数字"。这条纪律让"改一个数要改全文"变成"改一个 JSON 再重跑"。
2. **断言分层，任一层红就不算完成。** C 题的三层：结构 145 条（`audit/verify_claims.py`）、数值 136 条（`code/verify_numbers.py`）、格式 16 项（`gauntlet_check.py`）。
3. **负结果照写。** 见 §三.5。

---

## 二、技能清单

### 2.1 主流水线：`mathmodeling`

```
SKILL.md      入口与路由
WORKFLOW.md   八步二十门的判据（与 pipeline.py 的 GATES 必须一致）
RULES.md      75 条硬规则：E19 证据 / M17 建模 / T6 表格 / W12 写作 / V21 验证
RUNBOOK.md    排障手册、已知故障绕法、时间预算
CORPUS.md     真题语料怎么查、赛制与题型谱系
writing.md    摘要四段式、数字配额、压页
modeling.md   建模套路
THINKING.md   思考纪律
training.md   训练类题的规范
reference/    algorithms-10.md（十类算法）、shuwei2026c-handoff.md（C 题交接）
scripts/      pipeline.py / run_all.py / gauntlet_check.py / submission_gate.py /
              corpus_index.py / ingest_data.py / authenticity_check.py /
              caliber_check.py / new_paper.py / new_verify.py / run_squad.py /
              run_review.py / review_check.py / set_vision.py / mmkit/
squads/main/  18 人建稿队 brief（十波）
squads/review/ 13 人评审队 brief
```

### 2.2 检查工具：`paper-kit`

统一入口 `tools/run_tool.py`。常用：

| 工具 | 用途 |
|---|---|
| `venue_submission_check.py` | 投稿体检（页数、图表出栏、占位符、中文）。**参数是工作区目录，不是 pdf 路径** |
| `academic_writing_check.py` | 40 条学术写作规则（需要写作档案，没有就 SKIP） |
| `analyze_latex_template.py` | LaTeX 模板体检 |
| `docx_precheck.py` / `analyze_docx.py` | DOCX 版式检查 |
| `scholar_fetch.py` | 文献检索取 BibTeX |
| `pipelines.json` | 40 套竞赛流水线定义，含 `comp_shuwei` 与 `comp_shuwei_en`（各 7 步） |

### 2.3 手活四件

| 技能 | 触发 |
|---|---|
| `paper-language-pass` | 润色、±5–15 词微调、逻辑红线、去 AI 味。默认只在必须改时改 |
| `paper-figures-captions` | 架构图 prompt、实验图型选择、图注表注 |
| `paper-results-review` | 数据→结果分析段落；PDF→审稿报告 |
| `paper-cn2en-draft` | 中文草稿→英文正文；英文 LaTeX→中文速读 |

分工：`mathmodeling/writing.md` 定**结构**（摘要四段式、数字配额、压页），这四个管**句子与图表本身**。

---

## 三、C 题完整链路（2026 秋季赛 Restocking 人形机器人）

这一节是整个仓库最有价值的部分：**一个从原始数据到 67 页成稿的完整技术链路，含所有实测数字与它们的失败分支。**

### 3.1 题目骨架

三问一条链：

- **Part I 状态**：184 个视频 / 69 条记录 / 24 个环境 / 66,070 帧 / 每只手 21 个 3D 关键点。要把关键点变成"手状态"（阶段 + 可靠性），并且**手状态不得直接解释为产品状态**。
- **Part II 预测**：人工掩码回放。窗口/预算/请求成本/返回延迟预先固定。决策是"何时请求、如何等待"。官方主指标是**平均 3D 距离 R = (1/M)Σ‖p̂ − p_ref‖₂**（不是 RMSE）。
- **Part III 调度**：36 个 job，S1/S2/S3 = 8/12/16 job，H = 100/100/125，预算 32/34/40，review 上限 4/6/8。`p = αd + β`，名义 α=1、β=0.5，敏感性 α=0.75/1.5、β=0/1。报告 11 项指标，其中 **mean weighted on-time completion 每案例须 ≥0.50**。

### 3.2 Part I：掌心坐标系 + bi-TCN 边界检测 + 约束 DP

**代表点必须论证。** 比较三个候选：

| 代表点 | 刚性（cm，越小越稳） | 抖动比 |
|---|---|---|
| wrist（kp0） | 0.00005 | 0.1389 |
| **palm 质心（kp 0,5,9,13,17）** | **0.00001** | 0.1382 |
| tips 质心（kp 4,8,12,16,20） | 1.53823 | 0.1428 |

掌心比指尖稳两个数量级。逐关键点 leave-one-out：去掉任一 MCP 关节，掌心刚性变化 < 0.001 cm（最大 3.7e-06）；去掉任一指尖，变化 1.44–1.81 cm。**结论：掌心刚性不依赖任何单个关节，这是"掌心 vs 指尖"1.5 cm 的实质差别。**

**分割网络**：6 个残差块（dilation 1,2,4,8,16,1）、96 通道、双向平均、570,849 参数。验证集选解码常数（`height ∈ {0.15,0.25,0.35,0.45,0.55}` × `dist ∈ {15,22,30,40,55}`），测试集只评一次。

**关键教训：训练循环不可逐位复现。** 分块采样 `np.random.randint` + cuDNN autotuning，同一输入两次跑出 `0.4913` 与 `0.5326`。所以头条必须报分布：

> **ARI 0.5366 ± 0.0124**（三次重训，range 0.5293–0.5509），vs Ward 0.4138，**gap 12.28 点**（远大于 sd 1.24 点）；boundary F1 0.1707。

初稿曾报单跑 0.5487——那是旧权重的幸运抽样，现已在附录 L 明写「the first-draft value sits near the top of that range … the point estimate was a favourable draw rather than a stable property of the method」。

**零参数基线**（证明增益不是常数预测能拿到的）：全序列 1 段 ARI 0.1429、中点切两段 0.1265。

**阶段**：五段（reach / pick / place / transport / arrange），阈值 `THR = {v_hi 0.10, v_lo 0.05, a_grasp 0.15, t_arrange 0.8, a_closed 0.55, min_seg 3, static_run 5}`。默认份额 reach 65.63% / pick 7.15 / place 4.70 / transport 17.30 / arrange 5.22，平均段长 60.15 帧。阈值敏感性：最敏感是 `v_lo`（±20% 使份额变化 6.35 点），抓取/放置判定很稳（<1.3 点）。

### 3.3 可靠性检测器

八配置阶梯（V1–V8），V8 = V1 结构 + 保标签左右对称增广 + 交换 TTA：

> **test AUC 0.8271 / AP 0.1494 / worst per-env AUC 0.7777 / 318,790 参数 / 41.7 s per seed**

门槛 AP≥0.13 且 worst≥0.7646 → 通过。AP 是第一轮 0.0676 的 2.2 倍。

**诚实点**：按 val AUC argmax 会选 V1（0.8654 vs V8 0.8608，差 0.0046 在噪声内），但 V1 不过 AP 门槛——这条写进附录 L，不藏。

**可靠性融合**：fused test AUC 0.6267 / AP 0.0407 → 多任务 DualTCN 0.8325 / 0.1056（512,387 参数）。四臂：A 时序平滑 0.6496/0.0655（FAIL）、B 下一帧残差 0.7889/0.0517（FAIL AP）、C 多任务 0.8325/0.1056（**最强**）、D 全组合 0.8222/0.0924（预注册主臂 PASS）。**组合未叠加**——D 比 C 低 0.010 AUC / 0.013 AP。

### 3.4 Part II：预测器阶梯 + 成本曲线

掩码长度 L = 0.2 / 0.6 / 1.0 / 2.0 s（6/18/30/60 帧）。四个预测器：hold-last、常数加速度、ridge（α=10 + conformal 90%）、分位 GRU。

**官方 mean 距离 R（cm，record bootstrap 4000 次）**：

| L | hold | ridge | quantile |
|---|---|---|---|
| 6 帧（0.2 s） | 1.381 | 1.368（CI 跨零） | **0.643**（CI [−0.771, −0.704]） |
| 18 帧（0.6 s） | 3.419 | 3.288（CI [−0.175, −0.087]） | **2.979**（CI [−0.510, −0.371]） |
| 30 帧（1.0 s） | 4.840 | 4.817（CI 跨零） | **4.636**（CI [−0.265, −0.144]） |
| 60 帧（2.0 s） | 6.865 | 6.819（CI 跨零） | 7.028（CI [+0.125, +0.202] 显著变差） |

**两个重要结论**：①按官方 mean 指标，ridge 只在 L18 显著优于 hold——此前 RMSE 口径把 ridge 的尾部优势讲大了；②分位 GRU 在 L6–L30 全显著优于 hold，L60 反而变差。

**不可约误差**（oracle 探针）：L6 1.0712 / L18 3.9617 / L30 6.0507 / L60 8.8825 cm。现有模型已贴近不可约误差，架构升级空间极小——这是"不继续堆模型"的定量依据。

**成本曲线**：请求成本 1.0、延迟 1.0 s，交叉点 **mean 0.27 s / median 0.60 s**——预测在约 0.3 s 内比直接观测便宜。

**负结果**：context length 5/10/20/40 帧的 RMSE 是 6.252/6.298/6.323/6.307 cm（几乎平的）；特征子集四种（38/35/32/36 维）全是 6.298 cm。**这两项"该有增益却没有"的实验写进附录 N，是"我们已经试过"的证据。**

### 3.5 Part III：预约 + EDF，以及三个负结果

**策略族**：`p = αd + β` 预测完成时刻，预留 `b`，起点 `s' = s + max(p, b)`，然后 EDF。闭式：`P(on time) = F_d((due − s − β)/α)`，**与 b 无关**（条件于 s）——这是命题 B 的内容。

**冻结策略**（在 validation 上选，30 seeds × 5 mappings 评估）：

| case | 策略串 | test | all30 | vs slack |
|---|---|---|---|---|
| S2 | `A_s0_rabs_q0.45_g0.75_l12_m0.60_G0.00_k0.60_0.60` | 0.8283 | 0.8486 | **+6.00 点** |
| S3 | `A_s0_rfix_q0.30_g0.35_l20_m0.15_G0.25_k0.60_0.60_rev_t0.02` | 0.7900 | 0.8056 | **+4.75 点** |

**主检验**：blocked 配对差 **+5.38 点，95% CI [+2.57, +8.18]**（10 个 case×mapping 块，每块 5 个 test seed 重复）。10 块无一退化（最差 S2|α=0.75 是 +0.00，基线已饱和 0.9917）。

**P3 官方十一项指标**（我们 vs slack）：idle 3.53/3.34 vs 6.81/9.10，其余（完成率、准时率、tardiness、成本、review 次数、elapsed、overrun、censored）全部不劣。`invalid_actions=0`、`valid_protocol=true`、`budget_ok_rate=1.0`、`horizon_ok_rate=1.0`（450 trials 审计）。

**三个负结果，都写进正文/附录：**

1. **付费二次观测在 270 个格子里 0 格值得买。** 机制：预约误差 `b − p = α(Q_res − ε)`，点预测被代数消去，复核只能压残差宽度（sd 仅 0.4–0.7 s）；每次复核吃掉 100–125 s 时域里的 1 s，边际代价 ≈ φ/σ ≈ 0.8 点/秒。免费完美 1.0 s 前缀信息的上界也只有 **+0.42 点**，低于 1 点门槛。贪心复核平均 **−5.70 点**（S1 −2.05 / S2 −6.83 / S3 −8.23）。
2. **价值阶梯：规则买来的，不是数据买来的。** S2 规则 25.28 / 真实时长 3.33 / 付费观测 0 / 额外预留 −9.83 点；S3 21.88 / 3.85 / 0 / −7.99。**换成真实时长只值 3–4 点，而规则值 22–25 点。**
3. **视频有用，但只用在"帧可靠性"上。** 2 Hz 视频统计 + 姿态特征：AP 0.0516→0.0681（**+31.92%**）、AUC 0.7422→0.7694。但把 120 个视频统计接进强检测器 V8：AP 0.1494→**0.0581**（−61.1%）、worst 0.7777→0.5247——**过拟合**。late fusion 增益 **0.0008%**；10 Hz 采样（AP +8.27%、AUC −0.0025）反而比 2 Hz 差。

### 3.6 三个可迁移的方法论

1. **代表点先论证再使用。** 任何"用一个点代表一个刚体"的建模，都要给刚性/抖动指标 + leave-one-out。这是最容易漏、也最容易被评委问的一步。
2. **预注册 + 负结果。** 每个优化方向先写门槛（`data/up2_*_prereg.json` 带 sha256），跑完照判。C 题第二轮 7 个方向里 5 个 FAIL，全部如实写进附录 L 的七行台账。
3. **消融要分两类写。** "有增益的"进正文；"该有增益却没有的"（context length、feature subset、付费观测、视频 late fusion）进附录，标注 `passes=false` 与门槛值。

---

## 四、Modex 3.0.2 逆向要点

取证对象 `C:\modex-mh-agent`，方法：安装树静态取证 + 编译模块字符串 + 运行时 SQLite `workflow_steps` 真实行 + 明文工具源码。完整版见 `_swc2026/44/45/46` 三份报告。

### 4.1 它的"数维杯能力"= 7 步 × 每步一个必交产物 × 3 个人工检查点

| # | skill | 检查点 | 必交产物 |
|---|---|---|---|
| 1 | `comp-prob-analysis` | **approve** | `PROBLEM_ANALYSIS.md` |
| 2 | `comp-modeling` | **feedback** | `MODELING_REPORT.md` |
| 3 | `comp-code` | **approve** | `code/main.py`、`RESULTS.md` |
| 4 | `paper-figure` | 无 | `figures/latex_includes.tex` |
| 5 | `paper-figure-html` | 无 | `figures/latex_includes.tex` |
| 6 | `comp-paper-zh` | **approve** | `paper/main.tex` |
| 7 | `comp-compile-zh` | 无 | `paper/main.pdf` |

三个设计要点值得直接搬：

1. **每个非末步有唯一主产物**，下一步只认这个文件——避免"写到哪算哪"。
2. **检查点只在需要人判断的地方**（选题理解、模型方向、代码路线、成稿）；图表与编译不设，因为确定性。
3. **图表步骤的产物是 `latex_includes.tex` 而不是图片**——要求"图必须能被论文直接 `\input`"，这与"图编号/宽度/字体统一"是同一件事。

### 4.2 商业闸门（为什么它的技能正文拿不到）

`skill_delivery_gate.ENFORCED=True`，唯一放行条件是「本机能调通一次最小模型请求」。七个错误码：`MODEL_KEY_MISSING` / `MODEL_KEY_REJECTED` / `MODEL_KEY_CREDIT_REQUIRED` / `MODEL_CREDIT_REQUIRED` / `MODEL_REALNAME_REQUIRED` / `MODEL_ACCOUNT_UNAVAILABLE` / `MODEL_PRESET_UNAVAILABLE`。另有 `license-v2-client.json` 未随包发布、`api.mhcode.ai` Cloudflare 1010、账户 `quota: 0`。

**结论**：技能正文是"付费且联网才下发"的资产，静态安装包里没有。能拿到的只有明文工具层（`resources\app\tools\`，35 个 .py / 1.43 MB，已本机化为 `paper-kit\tools\`）与数据结构。

### 4.3 模型通道不可替换

`model_presets` 表只有 `{id,name,model_id,api_key,provider_id,created_at}`，**`base_url` 不存**（`schema.sql`：「请求地址始终由 License 签名配置确定」）。想接本机网关会被 `trusted_gateway_config.normalize_url()` 硬拒（只准 https 公网域名、端口 443、禁 IP 与 localhost）。它不是通用 agent，是绑定自家网关的建模工作台。

### 4.4 三条可直接搬进 `pipeline.py` 的设计

1. **主产物回执 + 免费重检。** `Step` 加 `outputs: list[str]` 与 `depends: list[str]`；门全过后写 `{"rule":1,"at":...,"outputs":[...],"fingerprint":{rel:[bytes,sha256[:16]]}}`；`--recheck` 开关不派单只跑门，指纹没变就不写新的 `finished_at`（防"重跑一次就算有进展"）。**目录型产物用 `(文件数, 总字节, 最大 mtime)` 三元组**，不要逐文件哈希。
2. **上游守卫。** 派单前把上游产物快照成 `{rel: sha256}`，派单后比对，被改/被删的还原，改动版另存 `rejected/<ts>/`。
3. **每步收据。** 引擎在 `workflow_steps` 落"收据"，说明这一步的计划产物、实际产物、检查结果——这是"可审计"的最小实现。

### 4.5 我们的 8 步 20 门 vs 它的 7 步

我们比它多 13 道机器门（它 4 类引擎后检，我们 20 道），少 3 个人工检查点（我们靠预注册门槛替代人工 approve）。它的优势是"产物即契约"的强制力，我们的优势是"数字可溯源"的机器判据。

---

## 五、踩坑清单（20 条，每条都付过代价）

### 环境与工具

1. **`Get-Content` 默认按 ANSI 解码中文**，会切错行。报"行数/节数"前先确认解码：`Get-Content x.md` 得 298 行，`-Encoding UTF8` 得 361 行。用 `[System.IO.File]::ReadAllLines($p).Length` 最稳。
2. **WMI 的 `AdapterRAM` 是 32 位字段**，超 4 GB 截断（NVIDIA 返回 4293918720 = 2³²−1048576，假值）。显存一律用 `nvidia-smi --query-gpu=memory.total`。
3. **PowerShell 不支持 heredoc `<<'PY'`**，多行 Python 必须落 `.py` 再执行。双引号内嵌 Python 正则的 `\"` 与 `$` 会被 PowerShell 解释。
4. **PowerShell 里按目录聚合数字必须用 Python。** `$agg[$k]=@($a[0]+$s, $a[1]+1)` 会报"方法调用失败，因为 [System.Object[]] 不包含名为"+"的方法"——取出来是 Object[] 不是 int[]。
5. **单次测量不能当结论。** 同方法单次噪声实测 ±56%（截图法三次 59.9 / 73.6 / 93.6 ms）。要下结论：先 warmup、至少 3 次取中位、串行跑。

### LaTeX 与版式

6. **`\enlargethispage{10\baselineskip}` 会把文本顶出纸面**（maxy 848.5 > 页高 841.9）。判据：maxy 必须 ≤ ~842。
7. **`\setlength{\baselineskip}{9.6pt}` 与 `\itemsep{-5.5pt}` 会让参考文献行互相覆盖**（PDF 里出现贯穿横线）。itemsep 不得小于 −2 pt。正确的做法是**删正文文字**换空间，不是压字距。
8. **正文顶满 25 页时，摘要多 2 行会把关键词挤到第 2 页、目录推到第 3 页**，`BodyLastPage` 从 25 变 26。任何正文新增一行都必须先等量删字。
9. **`\leftskip 0pt plus \hsize minus \hsize{...}` 会让居中的红字右缘超出 label 10 pt。** 用 `\centering` 并去掉 `\leftskip` 包裹。
10. **`swmcmthesis.cls` 是 LF 换行**，PowerShell 替换要同时试 `\r\n` 与 `\n` 两种写法。
11. **`\textsf{due}` / `\text{due}` 在多字母算子上会渲染成斜体 `due_j`**，一律用 `\mathrm{due}`。
12. **`\ref` 返回的节号自带句点**（`3.`），写 `Sections~\ref{a}--\ref{b}` 会印出 `3.--5.`。要么硬编码，要么删手写句点。
13. **附录用 `\section*{Appendix X: ...}` + 手工 `\addcontentsline` 会让 `\ref{app:x}` 返回节计数器**（正文出现 "Appendix 8"）。必须用 `\begin{appendices}` + `\section{...}`。
14. **`fill_numbers` 的槽名会把数字转英文**：`PDetV8AUC` → `\slotPDetVEightAUC`。main.tex 必须写转换后的名字，否则 `Undefined control sequence`。
15. **`page_report.py` 接受 pdf 路径参数时会把它当 `.tex` 读**，报 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe4`。无参调用才对。
16. **`venue_submission_check.py` 的参数是工作区目录，不是 pdf 路径**；传 pdf 会 `FileNotFoundError: …main.pdf\.mh`。

### PDF 与书签

17. **`titlesec` 在 `hyperref` 之前加载会让书签钩子失效**（`main.out` 只剩一条）。`bookmark.sty` 本机不存在，用 `code/add_pdf_outline.py` 从 `main.toc` 生成更可靠：`parse_toc` → `anchors` → hex 标题 + 命名目标 + `/Dest` + `set_counts`，最后断言页数/逐页文本/72dpi 光栅不变。
18. **`walk()` 取书签 xref 必须递归先序**，用栈会错序（报 `name subsection.1.1 points at page 3, outline says 57`）。**根 `/Count` 是"可见条数"不是总条数**（负数 = 折叠），改成 58 会破坏折叠语义。
19. **`.gitignore` 的否定规则 `!*/xxx.zip` 对多层路径不生效**，必须写 `!**/xxx.zip`。`git check-ignore -v` 是唯一可靠的验证手段。

### 建模与实验

20. **训练循环可能不可逐位复现。** 分块采样 + cuDNN autotuning 让同一输入两次跑出 0.4913 与 0.5326。**头条必须报 `mean ± sd` over repeated runs**，否则单跑的好数字迟早被自己的重跑打脸。同理：**验证集选出的解码常数每次重训会落到不同值**（height 0.10/0.15/0.30 都出现过），这是散布的另一半来源。

### 附加：数据与打包

21. **`quarantine_superseded.py` 的引用扫描必须跳过自身与 `_*.py` 探针**，否则探针里点名了所有候选，每个产物都被判"被引用"。模糊名要扫 `f"xxx{k}.json"` 形态（`range(len(stem), 9, -1)` 而不是 `len(stem)-1`）。
22. **支撑包必须含 `tables/`。** 漏了它，交上去的包解压后 `xelatex` 直接失败（`main.tex` 全靠 `\input{tables/*.tex}`）。验证方法：解压到空目录真编译一次，逐页比对文本与光栅。
23. **删 LaTeX 块必须按行配平 `\begin{table}` / `\end{table}`。** 用正则 `(?:.*?\n)*?` 会跨节吞噬正文（曾把 101,257 B 吃成 70,187 B）。

---

## 六、数维杯官方规则速查

### 6.1 格式规范（`论文格式规范.pdf`）

- 只能选 A–D 一题，题号与内容不符取消资格。
- **论文题目、摘要、关键词必须在第一页；第二页为目录专用页**；目录后开始正文。标题加粗、首字母大写。
- **正文每页必须有队伍编号与页眉页码**，例如 `Team ASWBMCM2600001` / `Page 1 of 25`。
- 12 号 Times New Roman、英文、公式排版规范。**正文 ≤25 页（含摘要页、目录页），附录页数不限。**
- 参考文献方括号编号，按正文引用次序；书籍须给页码，尽量不用网址。
- **全部源程序须在附录或支撑材料**。缺少必要源程序/不能运行/结果与正文不符可能取消评奖资格。
- 正文和附录不得出现身份与学校信息。
- **表标题在上、图标题在下；图形图表中不能出现中文。**

### 6.2 命名（关键，容易搞错）

规范原文：「论文命名格式为 **题号+队伍号.pdf**，其中 "A" 为题号，"SWBMCM2600001" 为队伍号，例如 `ASWBMCM2600001.pdf`。」

三条独立证据表明**队号本身不含题号字母**：报名系统截图 `队伍编号: SWBMCM2634892`、`Word模版.docx` 封面 `Team Control Number` = `SWBMCM2600001`、`demo.pdf` p3 页眉 `Team # SWBMCM2600001`。

所以：
- **文件名**：`C` + `SWBMCM2634892` → `CSWBMCM2634892.pdf` / `+cns.pdf` / `+fj.zip` ✓
- **文档内部队号**：`SWBMCM2634892`（不带 C）
- 规范第三条举例 `Team ASWBMCM2600001` 带字母，与两份官方模板矛盾——**取模板口径**。

### 6.3 三条红线

1. **AIGC > 30% 或总相似 > 50% → 取消评奖**（news225）。朱雀实测全 PDF 1.9470%、正文 p3–p25 **0.0000%**。
2. **AI 工具规定**（news220，2026-11-11 施行）：模型构建/算法设计/推导/结果解读必须队员独立完成；须自行改写、不得照搬；须声明 + 附《AI 工具使用情况报告》（不计页数）；脚本注释须标 AI 辅助。
3. **提交三件分别上传**：论文 PDF、承诺书（`题号+队伍号+cns`）、支撑材料（`题号+队伍号+fj`，zip/rar，建议 <20 MB）。**必须点"点击提交"，显示"已提交"才算成功。**

---

## 七、下次开赛的 15 分钟检查表

```powershell
# 1. 环境还在吗
& $PY -c "import numpy,pandas,scipy,sklearn,torch,matplotlib;print('ok')"
xelatex --version | Select-Object -First 1

# 2. 技能树完好
& $PY "$SK\scripts\pipeline.py" --help 2>&1 | Select-Object -First 3
& $PY -m unittest discover -s "$SK\scripts\tests" -t "$SK\scripts"   # 基线 70 tests OK

# 3. 官方件是最新的吗（每年模板可能变）
Get-ChildItem 'E:\数学建模\数维杯\00_官网与规则' | Sort-Object LastWriteTime -Descending

# 4. 语料索引还能查吗
& $PY "$SK\scripts\corpus_index.py" --stats

# 5. 建新题
& $PY "$SK\scripts\run_all.py" 'E:\数学建模\<新题>' --type C --problem-file '<新题>\problem\problem.txt'
```

然后按 §一 跑八步，按 §六.1 逐条核格式，按 §五 提前避开已知坑。
