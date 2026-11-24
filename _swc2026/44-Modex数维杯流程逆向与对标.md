# Modex 数维杯流程逆向与对标（附 2026 C 题落地核验）

日期：2026-11-21　　取证对象：`C:\modex-mh-agent`（Modex-MH-Agent 3.0.2）
取证方式：安装树静态取证 + 编译模块字符串 + 运行时 SQLite 的 `workflow_steps` 真实行 + 明文工具源码
结论一句话：**Modex 的「数维杯能力」= 7 步流水线 × 每步一个必交产物 × 3 个人工检查点 × 4 类引擎后检；它强在流程约束，不强在算法本身。这套约束我已经在本工作区用 8 步 20 门复刻，并且比它多 13 道机器门。**

---

## 1. 取证证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| 流水线定义（40 条） | `E:\数学建模\.agents\skills\paper-kit\pipelines.json` | 从原厂 `templates.json` 导出，含 `comp_shuwei` 与 `comp_shuwei_en` 各 7 步 |
| **每步必交产物（真值）** | `C:\Users\29900\AppData\Roaming\ModexData\library-sTDDnH\db\aris.db` → `workflow_steps` 表（7 行，`workflow_id=7f5f0bf1057a`） | 这是运行时真正落库的 `output_files`，比 `pipelines.json` 更新 |
| 引擎实现 | `C:\modex-mh-agent\resources\app\backend\services\workflow_engine.cp311-win_amd64.pyd`（5,448,704 B） | 字符串含 `planned：这一步计划的产物（模板里的 output_files）`、`检查 PAPER_PLAN.md / PROBLEM_ANALYSIS.md / TOPIC_PLAN.md 是否声明本论文无图表` |
| 验收实现 | `...\services\workflow_acceptance.cp311-win_amd64.pyd`（103,424 B） | 字符串：`数模第一步必产 PROBLEM_ANALYSIS`、`统计建模第一步只产 TOPIC_PLAN` |
| 明文工具 | `C:\modex-mh-agent\resources\app\tools\`（35 个 .py / 1.43 MB） | 已本机化为 `paper-kit\tools\`（31 .py + 11 .pyc） |
| 技能正文 | 加密胶囊 | 见 §2.2：**拿不到，且是设计上的商业闸门** |

---

## 2. Modex 的系统设计（它到底怎么"做建模"）

### 2.1 三层结构

1. **Electron 前端**（`dist\assets\*.js`，含新建页的 23 个竞赛模板卡片）。数维杯卡片原文：`赛题分析 → 建模 → 编程 → 图表 → 论文 → 编译`，`pages:30`，`lang:zh`。
2. **Python 后端**（`backend\` 全编译成 `.pyd`，245 个 / 65.2 MB；明文 `.py` 为 0）。216 个 service 模块，关键在于 `workflow_engine` / `workflow_acceptance` / `workflow_intake` / `skill_capsule` / `skill_source` / `skill_delivery_gate` / `simulated_review`。
3. **技能胶囊**（加密 zip，运行时向授权服务器换取）。每步真正干活的 prompt 与脚本都在胶囊里，**不在安装包内**。

### 2.2 商业闸门（为什么技能正文拿不到）

- `skill_delivery_gate.ENFORCED=True`，唯一放行条件是「当前这台电脑的模型真能调通一次最小请求」。
- `MESSAGES` 七个错误码：`MODEL_KEY_MISSING` / `MODEL_KEY_REJECTED` / `MODEL_KEY_CREDIT_REQUIRED` / `MODEL_CREDIT_REQUIRED` / `MODEL_REALNAME_REQUIRED` / `MODEL_ACCOUNT_UNAVAILABLE` / `MODEL_PRESET_UNAVAILABLE`。
- 实跑 `comp_shuwei` 工作流，`workflow_steps` 第 1 行的 `error_message` 原文：
  `[MODEL_KEY_MISSING] 还没填执行模型的 API Key：到设置页填好（可用「测试连接」验一下）再继续；技能内容只在能正常调用模型时下发（MODEL_KEY_MISSING）；当前产物已保留`
- 另有两层：`license-v2-client.json` 未随包发布 → `capsules_enabled()` 必 `FileNotFoundError`；`api.mhcode.ai` 整站 Cloudflare 1010；账户 `quota: 0`。
- **结论**：技能正文属于「付费且联网才下发」的资产，静态安装包里没有。这一点不因破解手段而改变；能拿到的只有明文工具层（1.43 MB）与数据结构。

### 2.3 模型接入

- `model_presets` 表字段只有 `{id,name,model_id,api_key,provider_id,created_at}`，`base_url` 不存（`schema.sql` 原文：「请求地址始终由 License 签名配置确定」）。
- 想接本机 magpie（`127.0.0.1:3425`）会被 `trusted_gateway_config.normalize_url()` 硬拒：只准 https 公网域名、端口 443、禁 IP 与 localhost。唯一放行 loopback 的 `backend_loopback_url()` 只存在于 `tools\trusted_gateway_config.pyc`，而 `site-packages` 里的明文版没有它。
- 所以：**Modex 的模型通道不可替换**。它不是一个"通用 agent"，而是"绑定自家网关的建模工作台"。

---

## 3. 数维杯流水线的真实契约（7 步）

以下 `output_files` 直接来自 `aris.db` 的 `workflow_steps` 行，不是推测：

| # | skill | 中文名 | 检查点 | 必交产物 |
|---|---|---|---|---|
| 1 | `comp-prob-analysis` | 赛题分析 | `approve` | `PROBLEM_ANALYSIS.md` |
| 2 | `comp-modeling` | 建模求解 | `feedback` | `MODELING_REPORT.md` |
| 3 | `comp-code` | 编程实现 | `approve` | `code/main.py`、`RESULTS.md` |
| 4 | `paper-figure` | 图表生成 | 无 | `figures/latex_includes.tex` |
| 5 | `paper-figure-html` | 流程与架构图绘制 | 无 | `figures/latex_includes.tex` |
| 6 | `comp-paper-zh` | 竞赛论文撰写 | `approve` | `paper/main.tex` |
| 7 | `comp-compile-zh` | 编译与合规检查 | 无 | `paper/main.pdf` |

三个设计要点：

1. **每个非末步都有唯一主产物**，下一步只认这个文件。这避免了「写到哪算哪」。
2. **三个检查点是人工的**：赛题分析要 `approve`（选题/理解对不对）、建模要 `feedback`（模型方向）、编程要 `approve`（代码路线）、论文要 `approve`（成稿）。图表与编译不设检查点，因为它们是确定性的。
3. **图表步骤的产物是 `latex_includes.tex` 而不是图片本身**——它要求"图必须能被论文直接 `\input`"，这与"论文里图编号/宽度/字体统一"是同一件事。

### 3.1 引擎级的附加检查（`workflow_steps` 的列）

`workflow_steps` 还有这些列，说明每一步结束后引擎会落"收据"：

`vision_review`（图的视觉审查）、`precompile_report`（编译前报告）、`submission_check`（投稿体检）、`writing_check`（写作规则检查）、`main_output_receipt`（主产物收据）、`paid_continues`（付费续跑次数）。

以及引擎字符串里出现的产物名：
`PROBLEM_ANALYSIS.md`、`TOPIC_PLAN.md`、`MODELING_REPORT.md`、`PAPER_PLAN.md`、`FIGURE_MANIFEST`、`FIGURE_SOURCES`、`FIGURE_SKIPPED`、`TABLE_DATA_CHECK_PASSED.txt`、`CROSS_PROBLEM_LEDGER`、`PROBLEM_FACTS`。

→ 翻译成一句话：**Modex 的"质量"主要来自"每步一个可验收产物 + 图/表/编译/写作四类后检"，不是来自某个更强的模型或算法。**

---

## 4. Modex 与我这套流水线的对照

| 维度 | Modex `comp_shuwei` | 本工作区 `mathmodeling` |
|---|---|---|
| 步骤 | 7 步 | **8 步**（多一步 s4 口径审计） |
| 机器门 | 4 类后检（vision / precompile / submission / writing） | **20 道门**（G1–G20，含 G16 口径、G17 自指、G18 出栏、G19 自检、G20 真题对标） |
| 人工检查点 | 4 个（approve/feedback） | 由 `pipeline.py` 在 FAIL 处停 + 每步增量评审 |
| 每步产物契约 | 1 个主产物（`output_files`） | `crew.OUTPUT_OF` 18 项 + `BYTES`/`VERDICT` 协议 |
| 小队 | 单 agent 顺序执行 | 18 人十波 + 13 人评审队（可并发） |
| 数据溯源 | 无强制 ledger | `data/ledger.json` 每条带 source+sha256+fetched_at，G2 拦截 |
| 图表 | `latex_includes.tex` | `figures/*.pdf` + G6 字号 + G11 视觉 + G18 出栏 |
| 论文自指 | 无 | G17：脚本字节数与附录索引必须一致 |
| 页数/格式 | 模板元数据写 30 页（**与官方 25 页冲突**） | 按官方 2025/2026 规范：≤25 页含摘要与目录，`submitted_pages` 判据 |
| 可离线 | 否（技能胶囊+许可网关） | **是**（技能全在工作区 `.agents\skills`，无外部依赖） |

**Modex 有而我没有的**：无（其 7 步的每一步在本工作区都有对应产物与门）。
**我有而 Modex 没有的**：G16 口径审计、G17 附录自指、G18 出栏、G19 流水线自检、G20 真题对标、数据 ledger、评审队、离线可跑。

---

## 5. 已复刻的等价物（`E:\数学建模\.agents\skills\paper-kit`）

- `tools\`：31 个 `.py` + 11 个 `.pyc`（共 42 个），含 `academic_writing_check.py`（40 条规则）、`venue_submission_check.py`（投稿体检）、`scholar_fetch.py`（文献四级 fallback）、`docx_export.py` / `docx_template_fill.py`、`survey_methods.py`（Kano/PSM/联合/SEM）、`analyze_latex_template.pyc`、`docx_precheck.pyc`、`stats_docx_package.pyc` 等。
- `prompts\`：9 份，含 `academic_docx_traps.md`（DOCX 渲染陷阱）、`docx_write_markdown_academic.md`、`paper_figure_lang_zh.md`。
- `templates\`：9 份科研流程模板。
- `tools\docx_style_profiles\`：13 份版式档案（含对标 `cumcmthesis.cls` 的 `competition_zh`）。
- `tools\journal_registry\families.json`：10 家期刊族、含 `quote`/`source_url`/`accessed`。
- `pipelines.json`：40 条流水线定义（含数维杯中英文两条）。

**没复刻的**：加密技能正文（56 个 `comp-*` / `paper-*` / `survey-*` 技能的实际 prompt）。它拿不到；我用「本工作区自建的 8 步 20 门 + 18 人 brief」替代其功能，不依赖它。

---

## 6. 2026 C 题按 Modex 七步的逐项核验

> 核验对象：`E:\数学建模\_swc2026\SWC2026_C`（Team CSWBMCM2634892）
> 判定口径：每一步是否有「Modex 要求的那个产物」+「我的机器门是否 PASS」。

| Modex 步 | 它要的产物 | 本稿的对应产物 | 机器判定 |
|---|---|---|---|
| 1 赛题分析 | `PROBLEM_ANALYSIS.md` | `out/00-problem.md`（逐句抄"要求你"）+ `out/15-benchmark.md`（195 条数维杯语料对标，同题 0 命中、同型 8/10/18 条） | G1/G2/G20 PASS |
| 2 建模求解 | `MODELING_REPORT.md` | `out/01-model.md` + `out/02-solve.md`（三问模型、变量、假设、误差口径） | G3/G4 PASS |
| 3 编程实现 | `code/main.py` + `RESULTS.md` | `code/`（`p1_*` / `p2_*` / `p3_*` 全部脚本）+ `data/*.json`（`p2_official.json`、`p3_strategy_v2.json` 等）+ `out/03-numbers.md` | G4/G5 PASS（`verify_numbers.py` 109 claims / 0 failed） |
| 4 图表生成 | `figures/latex_includes.tex` | `figures/` 全部图 + `slots.tex` 的 `\slotFig*` 宽度宏；正文 3 图、附录 8 图 | G6/G11 PASS（视觉审查；5 张曾因上游 500 记 unverified，已复跑） |
| 5 流程/架构图 | 同上 | `figures/fig0_framework.png`（数据 → Part I/II → 观察/Part III → 决策上限）+ `fig_chain.png`（双面板链路图） | G18 PASS（出栏 0） |
| 6 论文撰写 | `paper/main.tex` | `main.tex`（101,717 B，1,500+ 行，24 节）+ `slots.tex`（1,425 宏） | G7/G12/G17 PASS |
| 7 编译与合规 | `paper/main.pdf` | `main.pdf`（58 页：正文 25 + 附录 33）+ `CSWBMCM2634892.pdf` + `cns.pdf` + `fj.zip`（389 条目 / 7.35 MB） | G8 16/16、G13 0 项、G15 PASS |

**结论**：Modex 七步在本稿上逐项有产物、逐项有判定，且无一项靠"看起来对"。

---

## 7. 真实性证据（数据与视频到底查到什么程度）

这是对用户「所有的数据和视频都要分析，我要求真实」的直接回答，区分「全量」与「抽样」：

| 对象 | 覆盖 | 方法 | 结果 |
|---|---|---|---|
| 三个 ZIP 的全部成员 | **989 / 989** | 逐 member 流式 SHA-256 | 全部可读，无损坏 |
| 全部非视频文件 | **805 / 805** | 全量 CSV/JSON 解析、Parquet schema 与行数校验 | 0 解析失败 |
| 全部视频 | **184 / 184** | OpenCV 打开、读 fps/帧数/分辨率、首/中/末三帧解码 | 全部可解码；帧数与数值表/帧索引完全一致 |
| 视频总帧数 | **178,512 帧** | 元数据统计 | 总时长 5,963.74 s |
| 主数值 payload | 全部 | 重复检测 | 无重复 |
| 审计结论 | — | `data/full_audit.json` | `errors=0 warnings=0 verdict=PASS`，耗时 117.7 s |

**边界（必须说清）**：这不是「逐帧语义看片」。我做到的是「全字节 + 全文件解析 + 全视频容器/采样解码」，没有对 178,512 帧逐帧做人工语义标注。任何声称"逐帧看过每一帧"的说法都是不真实的，本报告不这么写。

数据侧另有的结构性核对（`data/data_profile.json` 195,994 B）：
69 records / 24 environments / 41 operators / 30 scenes / 66,070 timestamps；train-validation-test 环境级 16/4/4；`source_segment_index` 349 行、eligible 343（1.2 s 阈值需 1e-9 容差）；自然遮挡 Demo 17 段 / MCAP 119 段（仅 1 段 ≥1 s → P2 长缺失必须人工掩蔽）。

---

## 8. 当前成稿状态（2026-11-21 13:34 实测）

```text
main.pdf                 58 页（正文 25 / 附录 33）
verify_claims.py         PASS=118  FAIL=0  NA=0  total=118
verify_numbers.py        109 claims passed, 0 failed
gauntlet_check.py        16/16 PASS
page_report.py           overfull 0 / undefined 0 / prose numerals 0
中文/校名/姓名/电话检索  0
提交件                   CSWBMCM2634892.pdf 1,732,944 B
                         CSWBMCM2634892cns.pdf 17,080 B
                         CSWBMCM2634892fj.zip 7,347,586 B（389 条目，合计 8.68 MB < 20 MB）
```

## 9. 仍需人工完成（不能由代码代替）

1. `CSWBMCM2634892cns.pdf` 目前只有 `1. Shuping Zhang`，2/3 号队员姓名与三人手签需本人补齐（若确为单人参赛，则按单人承诺书处理——这点需按赛方要求确认）。
2. `submission_gate.py --stage final` 在本机会挂起（已知问题 >17 min 无输出）；以 `gauntlet_check.py` + `verify_numbers.py` + `page_report.py` 三道为准。
3. 赛方如要求 Word 版，需用官方模板另导；当前交付为 PDF。
4. Modex 模板元数据写「30 页」，官方 2025/2026 规范是「≤25 页含摘要与目录」——**以官方为准，本稿正文 25 页**。

---

## 10. 一句话总结

Modex 值得学的是它的**流程约束**（7 步 × 1 主产物 × 4 检查点 × 4 类后检），不是它的模型或算法；这些东西已经在本工作区被复刻并加强为 8 步 20 门 + 18 人小队 + 13 人评审队 + 数据 ledger，且完全离线可跑。C 题按这七步逐项核验全部有产物、有判定；数据侧 989 个文件全字节审计、184 路视频全量解码核对、178,512 帧统计一致。
