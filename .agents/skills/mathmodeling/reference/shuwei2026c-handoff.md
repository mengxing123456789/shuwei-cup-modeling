# （副本）源文件：E:\数学建模\SHUWEI2026_C\HANDOFF.md —— 若两者不一致，以源文件为准。

# 数维杯 2026 C 题 · 交接说明（供其他会话直接接手）

写于 2026-11-20 15:34（UTC+8）。本文件是**唯一权威记录**：数字全部由脚本现算，
命令全部可直接复跑；凡是"未核实"的地方都单独标注，不混在结论里。

- 论文工作区：`E:\数学建模\SHUWEI2026_C`
- 技能根：`E:\数学建模\.agents\skills\mathmodeling`
- 解释器：`E:\Mini\envs\mathmodel\python.exe`（Python 3.11.18；numpy 2.4.6 / scipy 1.17.1 /
  sklearn 1.9.1 / networkx 3.6.1 / pulp 3.3.2 / statsmodels 0.15.0 / skimage 0.26.0 /
  ortools 9.15.6755 / pywt 1.8.0 / pandas 3.1.1 / pymupdf / pyarrow）
- 模型网关：`http://127.0.0.1:3425/v1`（OpenAI + Anthropic 双协议；视觉实测用 `auto/glm-5.3-flash`）
- 队号：**SWBMCM2634892**（本科组）；交件名 `C + 队号` → `CSWBMCM2634892.pdf`

---

## 0. 一句话现状

数据侧已经过**全字节 + 全视频**审计，P3 的官方口径 baseline 已跑通（90 trials）；
论文侧 s1 三门（G1/G2/G20）已 PASS，s2–s8 尚未开始。**没有任何建模结论已经写进正文。**

---

## 1. 赛事规则（数维杯，来自官方 `demo.tex` 与 2025 格式规范/提交流程）

| 项 | 规定 | 依据 |
|---|---|---|
| 语言 | **必须英文** | 2026 LaTeX 模版 `demo.tex:24-25`；2025 格式规范第四条 |
| 字号 | 正文 **≥12 pt**（模版 `\LoadClass[a4paper,12pt]{article}`） | 同上 |
| 页数 | **≤25 页，含摘要页与目录页**；附录页数不限 | 2025 格式规范第四条 |
| 首页 | 题目 / 摘要 / 关键词都在第 1 页；**第 2 页专用于目录** | 第二条 |
| 页眉 | 每页都要队号 + 页码，形如 `Team SWBMCM2634892，Page 1 of 5` | 第三条 |
| 附录 | 至少含**全部源程序**（软件名、命令、可运行源码）；赛题数据不要放附录 | 第六条 |
| 中文 | 正文、附录、**图形图表**都不得出现中文字体 | 提交流程 |
| 交件 | 论文 `题号+队号.pdf`；承诺书 `题号+队号+cns`（手签或电子签）；支撑材料 `+fj`（可选） | 提交流程 |
| 体积 | 附件建议 **<20 MB** | 提交流程 |
| 2026 正式通知 | **本机没有**，以上按 2025/2021 规则执行 | 未核实项 |

本地官方资产：`E:\数学建模\数维杯\00_官网与规则\` 下 `2026…LaTeX模版\`（`swmcmthesis.cls`
16,729 B / `swmcmthesis.cfg` 3,567 B / `demo.tex` 6,395 B）、`…论文格式规范.pdf`(113,369 B)、
`…论文提交流程.pdf`(246,834 B)、`…承诺书.docx`、`…Word模版.docx`。

---

## 2. 数据全景（全部现算，可复跑）

### 2.1 规模

| 数据集 | records | environments | timestamps | 腕部视频 | 时长 p50 / max |
|---|---|---|---|---|---|
| EgoDemo | 31 | 13 | 16,414 | 9/31 | 11.0 / 58.8 s |
| EgoPro | 14 | 6 | 17,642 | 14/14 | 46.7 / 81.8 s |
| EgoStandard | 24 | 11 | 32,014 | 0/24 | 12.8 / 173.8 s |
| 合计 | **69** | **24** | **66,070** | 23/69 | — |

41 operators、30 scenes；环境级 split = **16 train / 4 validation / 4 test**，无环境跨 split。

### 2.2 字节与文件（`code/audit_all_data.py`，117.7 s，errors=0 warnings=0）

| 项目 | 实测 |
|---|---|
| ZIP member / 总字节 | **989 / 6,096,375,863 B** |
| 非视频 / 字节 | **805 / 461,837,574 B**（与解压副本逐一 SHA-256 相同） |
| 视频 / 字节 | **184 / 5,634,538,289 B** |
| 视频总帧 / 时长 | **178,512 帧 / 5,963.7379 s** |
| 首/中/末帧解码 | **184/184 成功** |
| 帧数 vs 数值表/帧索引 | **184/184 一致** |
| 主数值 payload 查重 | 无重复 |

按包：Demo 297 member / 1,916,728,226 B / 80 视频；Pro 308 / 2,029,238,984 / 56；
Std 384 / 2,150,408,653 / 48。每包 `sha256_mismatch`、`parse_errors`、`video_*_errors` 全 0。

**边界**：这是全字节、全文件、全视频容器与抽样解码审计，**不是** 178,512 帧逐帧语义判读。
论文里不得写成"逐帧审查过"。

### 2.3 手部与质量

| 指标 | Demo | Pro | Std |
|---|---|---|---|
| 手部流数 | 62 | 28 | 48 |
| 有效帧比例中位 | **1.000** | **1.000** | **1.000** |
| 全零帧段 / >50 ms 缺口 | 0 / 0 | 0 / 0 | 0 / 0 |
| 腕速 p50 / p99（m/s） | 0.142 / 0.531 | 0.159 / 0.746 | **0.266 / 0.909** |
| 相对起点高度 p10/p90（m） | −0.030 / +0.047 | −0.225 / +0.008 | −0.060 / +0.171 |
| 坏帧 / 总帧 | 108 / 16,414 (**0.658%**) | 410 / 17,642 (**2.324%**) | 310 / 32,014 (**0.968%**) |
| 逐记录坏帧 中位 / max | 0 / 2.60% | 1.25% / 7.21% | 0 / 6.75% |
| 原因字段 | `occlusion`（159 手侧标记） | 仅 `problem_type.length` | 仅长度 |

自然遮挡段：Demo 17 段（中位 0.133 s、max 0.567 s）；MCAP 119 段（中位 0.067 s、
**max 1.867 s**、**仅 1 段 ≥1 s**）。

---

## 3. 十个必须知道的结构坑

1. **目录名 ≠ `episode_uuid`**。Pro/Std 目录名与 `record_split.csv` **0 匹配**；真 uuid 在
   `session_metadata.csv` 的 `task_info.episode_uuid`；Demo 在
   `meta/episodes/chunk-000/file-000.parquet` 的 `episode_uuid` 列。按目录猜会得 13 个环境（错），
   正解是 24 个。
2. **1.2 s 阈值必须带容差**。`end_s − start_s` 的浮点误差产生 `1.1999999999999993`，
   裸 `>=1.2` 只数出 341；官方说 343。用 `>=1.2 − 1e-9`。
3. **Demo 的 hand 列是嵌套 list**。`fixed_size_list<fixed_size_list<float>[3]>[21]`；
   落到 pandas 是 object 数组，`np.isnan` 会抛 `ufunc 'isnan' not supported`，
   `ChunkedArray.to_numpy(dtype=...)` 不接受 dtype。**唯一稳的读法**：
   `tb.column(c).combine_chunks().to_pylist()` → `np.array(..., dtype=float)`。
4. **P3 抽样池极小**：validation 每族只有 **P 15 / A 13 / L 7** 个 eligible 段；30 个 seed 都在
   这些段里有放回抽。配对比较稳，但方差主要来自池小，必须在论文里报告。
5. **自然缺失不足**：没有 NaN / 全零帧 / >50 ms 缺口，自然遮挡仅 1 段 ≥1 s。
   所以 P2 的缺失只能**受控掩蔽**（见 §5 措辞）。
6. **三套数据运动强度差 ~1.9 倍**（腕速 p50 0.142 vs 0.266 m/s）：跨数据集直接合并会学成
   "按数据集分辨"。要做速度归一或加数据集哑变量。
7. **重尾是真的**：P 族 >10 s 12.2%、>20 s 3.5%、>40 s 1.7%、max 125 s；
   α=1.5、β=1.0 时 p50 7.0 s、max **188.5 s > S3 的 H=125 s**。
8. **坏帧是零膨胀**：中位 0，均值无意义；用分层模型（是否坏 × 坏多少）。
   坏帧是**人手标注的观测质量**，不等于商品遮挡、也不等于操作失败。
9. **腕部缺失**：Demo 9/31、Pro 14/14、Std 0/24；腕部**无 world 外参**，不能反投影到统一坐标。
10. **5 fps 是深度相机**，不是腕部；腕部 RGB 是 30 fps、1920×1536。

---

## 4. 流水线与当前状态

八步、二十道门（`STATE_SCHEMA = 4`）；`SOFT_GATES = {G10, G11, G14}`。

| 步 | 成员 | 门 | 本工作区状态 |
|---|---|---|---|
| s1 赛题分析 | 题目侦察手 / 数据溯源手 / 真题对标手 | G1 题面, G2 台账, G20 真题对标 | **PASS / PASS / PASS** |
| s2 建模求解 | 建模架构手 | G3 模型 | 未跑 |
| s3 编程实现 | 求解与优化手 / 代理模型训练手 / 数值对账手 | G4 求解, G5 数字对账, G10 表格数据(软) | 未跑 |
| s4 口径审计 | 口径审计手 | G16 口径审计 | 未跑 |
| s5 图表 | 图表手 | G6 图表, G11 视觉审查(软) | 未跑 |
| s6 论文撰写 | 论文撰写手 / 附录与自指手 | G7 正文形态, G12 论文数字, G17 附录自指 | 未跑 |
| s7 编译合规 | 格式合规手 / 版式与出栏手 / 流水线运维手 | G8 编译合规, G13 投稿体检, G14 模板核对(软), G15 源文件闭包, G18 版式出栏, G19 流水线自检 | 未跑 |
| s8 评审收口 | （评审小队 13 人） | G9 评审收口 | 未跑 |

产物契约（判据会读这几样，格式错了直接判没过）：

- `out/00-problem.md`：**首行必须是 `BYTES <n>`，且 n 等于该文件真实字节数**；末行 `VERDICT: PASS|FAIL`；
  不适用的产物写一行 `NOT-APPLICABLE: <理由>`（不空转、不假装 PASS）。
- `data/ledger.json`：每条数据源带 `source` + `sha256` + `fetched_at`（现 12 条 / 5,392 B）。
- `logs/pipeline_state.json`：断点；schema 不匹配会自动备份成 `pipeline_state.vN.bak` 并重来。
- `out/15-benchmark.md`（G20，现 4,100 B）；`out/05-caliber.md`（G16 人的部分）；
  `out/15-caliber-machine.md`（G16 机器部分，`code/caliber_check.py` 生成）。

---

## 5. 三问的建模建议（含措辞纠正）

> **重要措辞**：P2 不是"造数据"。正确说法是**在真实记录上做受控缺失掩蔽**
> ——数据源不变，改的是"回放时的可见性"，评估用留出记录的真实值做参照；
> 掩蔽通道、窗口、观测预算、延迟**事先固定并冻结**，所有方法共用，逐条可重放。
> 论文里写 "controlled input masking on real recordings"，不要写 "synthetic data"。

### P1 状态变化 + 观测可靠性
- 用 138 路手部流做"关键点 → 代表点"（代表点定义必须自证，例如腕部 0 号关键点或若干点几何中心）。
- 特征：速度/加速度分位、停留时长、方向变化率、抓取相（开合代理）。
- 可靠性：坏帧率 + 速度离散度 + 段长 做分层模型；Demo 有原因标签、Pro/Std 无 → 用半监督或只用 Demo 训练原因。
- Baseline 必须先做：常数预测（角度/位置不变）、线性外推。**报误差必须带参照来源**。

### P2 缺失下的预测与再观测
- 掩蔽矩阵：窗口 {0.5, 1, 2, 3, 5} s × 通道 {头戴, 腕部, 双通道}（腕部只有 23 条记录有）。
- 策略 baseline：保持最后状态 / 匀速运动 / 固定间隔再观测。
- 指标：预测误差（有参照时才报）、区间覆盖/集合可靠性、观测次数与成本、等待时间、计算开销。
- **禁止**：无独立参照时计算"真实位置误差"；用未到延迟的信息；按 prefix 匹配去检索未披露状态。

### P3 不确定下的补货调度
- 已实现官方协议 baseline：train 同族 median + 0.5 作预留；validation 同族池；保持行序；
  `random.Random(seed).choice` 按 `job_id` 排序；不偷看实际 p；EDD 选序；不查看。
- 结果（30 seeds × 3 cases = 90 trials，invalid_actions = 0）：

| case | 加权完成率 | 加权准时率 | 加权拖期(s) | 成本/预算 | elapsed/H | 未完成 | 提前停止 |
|---|---|---|---|---|---|---|---|
| S1 | 1.000 | 0.990 | 0.7 | 21.53/32 | 74.5/100 | 0.00 | 0/30 |
| S2 | 0.876 | 0.635 | 50.3 | 28.06/34 | 97.6/100 | 1.63 | 19/30 |
| S3 | 0.845 | 0.586 | 124.1 | 35.99/40 | 123.2/125 | 2.77 | 17/30 |

- 硬约束是**成本**：S3 固定执行费 2×16=32 / 预算 40，只剩 8 单位；查看一次 = 1 单位 + 1 秒设备。
- 下一步策略空间：把"是否查看"变成期望收益决策（看到 0.6 s 前缀可降低 p 的方差），
  预留 b 取分位数（如 P75）而不是中位；预算感知的优先级（w/due）排序。
- 必报 11 个指标（名字照题面）：weighted_completion_rate、weighted_on_time_rate、
  weighted_tardiness_s、cost、observations、elapsed_s、observed_overrun_s、reserved_idle_s、
  censored_units、invalid_actions、valid_protocol。

---

## 6. 已经踩过并修掉的真 bug（别再犯）

1. **P3 baseline 协议错**：曾用全量 343 段 + NumPy RNG + 把预留 b 设成实际 p。官方要求
   validation 池、行序、`random.Random(seed).choice`、按 `job_id` 排序。旧数字已作废。
2. **BYTES 自指差 12 字节**：先算 body 再去掉首行，导致报 14130、实际 14142。正确不动点：
   `n = len(("BYTES n\n" + body).encode())` 迭代到稳定（现 15,182 = 实际）。
3. **`new_paper.py` 存盘带 BOM**：`ast.parse` 报 `invalid non-printable character U+FEFF`；
   读文件用 `encoding="utf-8-sig"`。
4. **matplotlib `fontsize=6.0` 落成 5.98**：`R-V14` 只判 `len(text)>=3`，凡是要过门的文字 **≥6.2**。
5. **`hatch` 生成 tiling pattern**：`get_bboxlog()` 的 `fill-path` 会把 pattern BBox 算进去，
   视觉被裁但出栏检查报超大矩形。用虚线描边（`linestyle=(0,(2.2,1.4))`）+ `alpha=0.4` 代替 hatch。
6. **`savefig.bbox="tight"` 改缩放比**：本流水线把 figsize 精确设为版心宽 5.7854 in +
   `width=1.0\linewidth` 使缩放比恒 1；改 tight 会连带触发字号判据。
7. **`sharey` + 子图 `set_yticks([])` 会清掉主图刻度**（参数名全消失、不报错）。
8. **`\DeclareMathSizes` 的键是 `\f@size` 的精确十进制值**（本文档 `10.53937` / `9.03374` /
   `7.52812` / `6.52437`），写 `{12}` / `{7.5}` 一律匹配不上；newtx 已把阶梯改过。
9. **附录源码里的中文会让 venue 判"英文稿含中文"**：`check_chinese()` 是"每页取第一个命中"，
   要归零必须 PDF 全文零 CJK。数据契约键（`FUNC_ORDER` 之类）也要一并改成英文并同步。
10. **占位正则误判 Python 列表推导式**：已给 `venue_submission_check.py` 加
    `_is_code_fragment()`（含代码标点 / `for … in …` / `ast.parse` 可解析）。
11. **`Path.write_text` 在 Windows 做 `\n`→`\r\n`**：凡是"文件自身字节数"的自指，必须
    `write_bytes(s.encode("utf-8"))`。

---

## 7. 建议改进（按优先级，含落地位置）

### P0 —— 直接关系到"这次被质疑"的两件事

1. **新增 G21「数据覆盖审计」门**（`scripts/pipeline.py`）
   - 判据：`data/full_audit.json` 存在且 `verdict == "PASS"`；`code/audit_all_data.py --verify`
     重算 4 个总量（member 数、总字节、非视频字节、视频数/帧数）与审计记录一致；
     任一项不等 → FAIL 并打印两组数字。
   - 理由：今天的质疑正是"凭什么说查完了"。把总量做成门，重跑即验，不靠叙述。
2. **新增 G22「P3 协议自检」门**（`scripts/pipeline.py` + `code/baseline_p3.py` 导出 `CONFIG`）
   - 判据：抽样函数必须是 `random.Random(seed).choice`、池来自 `split == "validation"`、
     行序未被重排、job 遍历按 `job_id` 排序；结果表须含 11 个规定指标名；
     `invalid_actions == 0` 且 `valid_protocol` 全 True。
   - 理由：协议错一次就会让整组数字作废，且很难靠肉眼发现。

### P1 —— 防止同类错误复发

3. **统一 BYTES 写入工具**：`mmkit/textfile.py` 提供 `write_with_bytes(path, body)`，
   内部做不动点；所有产物生成器（含 `new_paper.py` 模板、`caliber_check.py`、
   `gen_index.py`）都改用它。现在每个脚本都自己写一遍，早晚再差几字节。
4. **新增 G23「数据画像」门**：要求 `data/data_profile.json` + `data/analysis.json` 同时存在，
   且 `records / environments / timestamps / split` 与审计一致；不一致直接 FAIL。
   这条专抓"13 个环境"那类映射错误。
5. **`new_paper.py --cls swmcm` 的骨架补三样**：
   - 预置 `\DeclareMathSizes`（用本机实测的 `\f@size` 值）；
   - 注释写明"正文 ≥12 pt，表格最低 `\footnotesize`，禁止 `\scriptsize`"；
   - 注释写明"第 2 页必须是目录，`\setcounter{page}{1}` 让正文从 Page 1 起"。
6. **`WORKFLOW.md` §5 更新为 20 门**并补 NA 语义（NA = 结构性不适用，计通过但单独列出；
   `??` = 该判却判不出，必须修）。现在文档还停在 15 门。

### P2 —— 质量与效率

7. **视觉审查（G11）**：把"接口超时/500"与"没配模型"分开记（现在后者 NA、前者 None，方向对）；
   建议再加"两模型一致才算结论"，单模型结论标 `unverified`。
8. **`analyze_data.py` 泛化**：列名探测（`pose_*_hand.csv` / hand 列）抽成函数，换数据集可复用；
   现在写死了 Ego 系列的三套命名。
9. **把 `refs/contest-code/` 的 840 个 `.m` 做成"算法索引"**：`INDEX.md` 已有五类对照，
   建议再补"本机 Python 等价实现的最小可跑片段"，避免赛时现查。
10. **`out/00-problem.md` 与 `out/data-analysis.md` 合并口径**：前者是题面解读，后者是数据画像；
    两者若出现同一数字必须同源（都由 `analysis.json` 读），现在有重复表述的风险。

---

## 8. 未核实 / 需要人确认

1. `Data_Documentation/attachment_guide.md`、`missing_observation_experiments.md` **不在下载包**。
2. Pro/Std 的 `problem_type` 只有长度，**无类型码**，无法按遮挡/边缘分组。
3. 2026 秋季赛正式通知（页数/语言/AI 声明）本机没有；现按 2025/2021 规则。
4. `tasks.csv` 与 `source_segment_index.csv` **无 job→unit 显式映射**；只能用官方抽样协议。
5. 视觉模型对数字 OCR 不准（能把 0.8612 读成 0.8812）：只用于版面判断，不用于读数。

---

## 9. 复现与接手命令

```powershell
$PY = 'E:\Mini\envs\mathmodel\python.exe'
$SK = 'E:\数学建模\.agents\skills\mathmodeling\scripts'
$P  = 'E:\数学建模\SHUWEI2026_C'

# 看交接单（八步二十门 + 每门判定）
& $PY "$SK\pipeline.py" $P --status

# 重跑 s1（三门）
& $PY "$SK\pipeline.py" $P --only s1 --force s1 --skip-dispatch --no-review-each

# 数据审计（约 2 min，全量字节 + 184 路视频）
& $PY "$P\code\audit_all_data.py"

# 数据画像与分布层
& $PY "$P\code\profile_data.py"
& $PY "$P\code\analyze_data.py"

# 官方口径 baseline（30 seeds × 3 cases）
& $PY "$P\code\baseline_p3.py"
```

产物与大小（现状）：`out/00-problem.md` 15,182 B、`out/data-analysis.md` 10,625 B、
`out/15-benchmark.md` 4,100 B、`data/data_profile.json` 195,994 B、`data/analysis.json` 19,545 B、
`data/full_audit.json` 1,963 B、`data/video_audit.json` 102,682 B、
`data/results_baseline_p3.json` 1,985 B、`data/baseline_p3_trials.csv` 13,749 B。

---

## 10. 新会话开工前必守的五条

1. **先读本文件，再读 `WORKFLOW.md` §5（门表）与 `SKILL.md`（数维杯走法）**，不要凭印象写门。
2. **任何数字都要有产物**：写到 `data/*.json`，正文从 JSON 读；不许手抄。
3. **不许把"抽样解码"说成"逐帧审查"**，也不许把"受控掩蔽"说成"造数据"。
4. **协议类东西先冻结再跑**（抽样规则、掩蔽窗口、预留策略），跑完不许回头调参再报。
5. **改完必须重跑**：`analysis` → `baseline` → `pipeline --status`；门不过就停下修，
   不要连过几门再回头（红门会互相掩盖）。