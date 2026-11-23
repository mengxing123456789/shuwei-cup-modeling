BYTES 65183
# Modex-MH-Agent 3.0.2 工作流引擎逆向：一道赛题如何变成一篇论文

> 对象：`C:\modex-mh-agent`（Electron 外壳 + Python 3.11.9 后端，`resources\app\backend\services` 217 个模块全部编译为 `.pyd`）
> 方法：静态取证（PE 字符串表、Cython 限定名、模块/函数 docstring）+ 可复跑实验（用随包解释器导入模块直接调私有函数）
> 复现目录：`E:\数学建模\_swc2026\modex_re\`（脚本 + JSON 结果）
> 被分析对象零修改；`E:\数学建模\_swc2026\SWC2026_C`、`SWC2026_C_ALT_BACKUP` 未触碰。
> 凡本报告写「未证实」的，都是我用现有手段拿不到、且没有旁证可以替代的项。

---

## 0. 复现前提（照抄即可跑）

`.pyd` 是 PE/Cython 扩展，不是裸 marshal，`marshal.loads(data[16:])` 这条路对本安装无效（只有 9 个真 `.pyc` 走这条路）。可行手法是**用随包解释器导入**，`inspect.signature` / `inspect.getdoc` / 模块常量全部可读：

```powershell
$PY = 'C:\modex-mh-agent\runtime\python\python.exe'   # 3.11.9，自带 cryptography
# 必须同时把 app 与 app\backend 放进 sys.path，并 chdir 到 app
```

```python
import sys, os
app = r"C:\modex-mh-agent\resources\app"
sys.path.insert(0, app); sys.path.insert(0, app + r"\backend"); os.chdir(app)
from backend.services import workflow_engine as we
```

三条实测约束：

1. `E:\Mini\envs\mathmodel\python.exe`（3.11.18）**导入会失败**：`ModuleNotFoundError: No module named 'cryptography'`，抛点在 `account_transport.py:28 in init account_transport`。必须用随包解释器。
2. 部分函数是 **coroutine**（Cython 编译的 `async def`）：`_free_recheck`、`_recovery_outputs_pass`、`submission_review.run_for_step`、`writing_review.run_for_step`。直接调只拿到 `<coroutine object>`，要 `asyncio.run()`。
3. Cython 的 `TypeError` 文案是 `takes exactly N positional arguments (M given)`，说明 **签名不可用关键字绕过**，要按位置传。

证据：`E:\数学建模\_swc2026\modex_re\exp_free_result.json`、`exp_free_result3.json`、`exp_recovery.json`。

### 0.1 版本锚点（哪份源码编出了这个 pyd）

`C:\modex-mh-agent\resources\app\backend\_modex-build-inputs.json`（106,827 B）记录构建输入，可用来钉住版本：

- `workflow_engine` → 源 `web/backend/services/workflow_engine.py`，sha256 `a8fa9847f560480e2f52c5575f20d7056b0a8dcb125445f243a4e5a6a2b1b8ab`
- `workflow_acceptance` → 源 `web/backend/services/workflow_acceptance.py`，sha256 `48eb164d10f538a273c11f0c95de8a8db3da13af95911b3888cd68c31a941ba1`

源码本体未随包发布，所以本报告所有「docstring 原文」都是**从编译产物里读出来的**（`inspect.getdoc`），不是从源码抄的。文件体量：`workflow_engine.cp311-win_amd64.pyd` = 5,448,704 B，`workflow_acceptance.cp311-win_amd64.pyd` = 103,424 B，`workflow_intake.cp311-win_amd64.pyd` = 811,008 B。

---

## 1. 步骤契约表

`comp_shuwei` 模板在引擎里是 `TEMPLATES['comp_shuwei']`（`pyd 模块.TEMPLATES`，dump 见 `exp_templates.json`）；用户实际跑过的持久化实例在 `aris.db` 的 `workflow_steps`。两者**有一处版本漂移**，见 1.3。

### 1.1 模板定义（引擎侧，`exp_templates.json`）

| # | skill id | 名称 | checkpoint | output_files | primary_output | 最小字节 |
|---|---|---|---|---|---|---|
| 1 | `comp-prob-analysis` | 赛题分析 | `approve` | `PROBLEM_ANALYSIS.md` | 同名 | 1500 |
| 2 | `comp-modeling` | 建模求解 | `feedback` | `MODELING_REPORT.md` | 同名 | 2000 |
| 3 | `comp-code` | 编程实现 | `approve` | `code/main.py`, `RESULTS.md` | `RESULTS.md` | 1000 |
| 4 | `paper-figure` | 图表生成 | 无 | `figures/latex_includes.tex` | `figures/` | 500 |
| 5 | `paper-figure-drawio` | 流程与架构图绘制 | 无 | `figures/latex_includes.tex` | `figures/` | 500 |
| 6 | `comp-paper-zh` | 竞赛论文撰写 | `approve` | `paper/main.tex` | 同名 | 10000 |
| 7 | `comp-compile-zh` | 编译与合规检查 | 无 | `paper/main.pdf` | 同名 | 30000 |

`TEMPLATES` 共 40 个模板键；`pipeline_skill='comp-prob-analysis'`；模板目录映射 `_TEMPLATE_TO_FOLDER={'comp_shuwei':'shuweibei','comp_shuwei_en':'default'}`。

最小字节来自 `_STEP_MIN_SIZE`，取值由 `we._min_size_for(skill, primary)` 暴露（实验 `exp_health_result.json` 与 `exp_split` 实测一致）：

```
comp-prob-analysis 1500 | comp-modeling 2000 | comp-code 1000
paper-figure 500 | paper-figure-html 500 | comp-paper-zh 10000 | comp-compile-zh 30000
```

`_min_size_for` 的 docstring 原文（`pyd workflow_engine._min_size_for`）：

> 获取该 skill 的 primary_output 最低字节阈值, 默认 100。
> primary_output: 该步骤实际的主产物路径。docx 模式下改进循环的产物是 `paper/main.md`(Markdown), 而非默认的 50KB PDF, 用 PDF 阈值会误判失败, 因此对 markdown 产物使用更合理的下限。

**关键负结论（可复跑）**：`_primary_output_health` **不执行** 最小字节判定。270 字节的 `PROBLEM_ANALYSIS.md`、864 字节的 `RESULTS.md` 都返回 `(True,'')`（`exp_health3.json`）。字节阈值是在 `run_workflow` 主循环里用 `_primary_output_size` + `_min_size_for` 单独比的。所以「产物健康」≠「产物够大」，报告里不能混为一谈。

### 1.2 每一步的前置 / 后置

前置 = `_UPSTREAM_DEPS`（上游产物必须已存在，`_upstream_deps_for('comp_shuwei', skill)` 实测）+ `_STEP_REQUIRED_COMPANIONS`（二级文件）。

`_UPSTREAM_DEPS` 的 docstring 原文（引擎字符串表 `exp_upstream_strings.json`）：

> 该步骤开始前应已存在的上游产物（按模板区分；统计建模不再误报缺建模报告）。

| skill | 前置：上游产物 | 前置：配套文件 | 后置：本步专属检查 |
|---|---|---|---|
| `comp-prob-analysis` | 无 | 无 | `workflow_acceptance.core_file_problem`（REPORT_SKILLS）；`_PROBLEM_READING_SKILLS` → 题面 PDF/图片的 Vision 转录；`_append_materials_check` 只提示不拦 |
| `comp-modeling` | `PROBLEM_ANALYSIS.md` | 无 | 同上 `core_file_problem`；`_step_data_problem`（只在显式 fatal 或缺检查能力时拦） |
| `comp-code` | `MODELING_REPORT.md` | `code/main.py`, `figures/all_results.json` | `_check_step_companions`（存在 + >50 B + 汇总 JSON 结构可读）；`results_consistency_gate`（结果数字对账）；`_failed_problem_results` |
| `paper-figure` | 无 | 无 | `_check_figures_step_health[_static]`：FIGURE_MANIFEST 对账 + 必须有数据图；`_check_data_figure_quality` / `_check_figure_pdf_quality`；`_figure_source_problems`；`_registered_figure_skips` |
| `paper-figure-drawio` / `-html` | 无 | 无 | 同上，但要求的是架构图类（drawio 前缀或 `tikz_`）；`_registered_diagram_skips`（技术路线图永不可跳） |
| `comp-paper-zh` | `PROBLEM_ANALYSIS.md`, `MODELING_REPORT.md`, `RESULTS.md` | 无 | `_POST_WRITE_CHECK_SKILLS` 命中 → 写后检查；`check_paper_submission_contract(..., final_source=False)` 只做源码级确定性检查；`_check_paper_body_pages`（咨询性）；`_check_paper_modeling_quality_raw` 的 `applicable` 判定 |
| `comp-compile-zh` | `paper/main.tex` | 无 | `_FINAL_MODELING_GATE_SKILLS` 命中 → 建模深度终检；`_PAPER_DATA_CHECK_SKILLS` 命中 → `paper_data_check`；`submission_review`（投稿前检查）；`writing_review.run_final`（稿件检查） |

`_check_step_companions` docstring 原文（`pyd workflow_engine._check_step_companions`）：

> 检查二级文件是否齐全. 返回 (ok: bool, missing: List[str]).
> 每个文件要求:
>     - 文件存在
>     - 文件大小 > 50 字节 (防空文件占位)

实测比 docstring 更严（`exp_gates_result.json`）：`figures/all_results.json` 只有 `{}`（2 字节）时报 `figures/all_results.json (没有可读取的汇总结构)`，即**还要求能读出汇总结构**。

### 1.3 版本漂移（必须记下来）

- 引擎模板第 5 步是 `paper-figure-drawio`；
- `aris.db` 里这条工作流的第 5 步是 **`paper-figure-html`**（`workflow_steps.step_order=4`）；
- `_FIGURE_STEP_SKILLS` 与 `_FIGURE_HEALTH_SKILLS` 两个 id 都收；
- 实测 `_generate_claude_md(ws, title, 'comp_shuwei', {"language":"zh"})` 生成的第 5 步写的是 `paper-figure-html`，且 CLAUDE.md 里有一整块 `## ⛔ 流程图/架构图引擎 = HTML（用户选定，全程遵守）`，正文写「一律用 HTML+CSS 绘制（paper-figure-html skill：flex/grid 自动布局 → Electron printToPDF 转矢量 PDF），不使用 DrawIO」。

结论：**模板默认 drawio，用户可切 HTML，DB 记的是实际选中的那个**。证据：`exp_templates.json`、`aris.db workflow_steps.skill_name`、`workspaces\7f5f0bf1057a\CLAUDE.md:6`。

---

## 2. 状态机

### 2.1 取值（枚举 + DDL 注释双证）

`WorkflowStatus`（`exp_state.json`，`pyd 模块.枚举`）：`pending | running | paused | completed | failed`。
DDL 侧同样写在 `schema_ddl.txt:7` 的列注释里。

`StepStatus`：`pending | running | waiting_checkpoint | completed | failed | skipped`（`schema_ddl.txt:32`）。

`workflows.enable_checkpoints` 的列注释原文（`schema_ddl.txt:10`）：

> `0=关闭检查点(自动连续执行) 1=开启检查点(步骤完成后暂停确认)`

`checkpoint_type` 取值 `idea_select | approve | feedback`（`schema_ddl.txt:34`）。

DB 里这条工作流 `enable_checkpoints=0`。按 DDL 注释「0=关闭检查点(自动连续执行)」，**它不会在三个 `approve/feedback` 步停下**，七步一路自动跑。这个推断有旁证但**未直接实测**（要真跑起来才能看到「停不停」）：

- `_forced_topic_checkpoint` docstring：`统计建模没填自拟题目时，选题步结束必须停下让用户定题，不看全局检查点开关。` —— 特意强调「不看开关」，反证普通检查点**看**开关。
- `_forced_plan_checkpoint` docstring：`只停这一步，不打开全局检查点开关` —— 同上。
- `_confirm_checkpoint_without_model` docstring：`免费重新检查通过、本步又开了检查点：照常停下等用户确认` —— 「又开了检查点」是停下的前提。

也就是说：**全局开关管普通检查点，两个 `_forced_*` 例外不管开关**。这条工作流是 0，所以它对用户是「按下去就一路跑到底」。

### 2.2 pause / resume

- `request_pause(workflow_id)` / `is_pause_requested` / `clear_pause_request` 三个函数；docstring（引擎字符串表）：
  > 标记用户要求暂停。pause 接口调用，步骤循环每步开头检查。
- `clear_pause_request` 的 docstring 是这套设计里最狠的一条：
  > 清除暂停标记。⛔ 所有启动路径（start/resume/restart/rerun/心跳复活/重启恢复/检查点续跑）都必须调用，否则工作流会在下一步立刻自杀、再也起不来。
- 中断恢复：`init_db` 先把 `running` 归一成 `paused`（`_mark_workflow_preparing` docstring：`init_db` first normalizes interrupted workflows to `paused`…persisting this state prevents the dashboard from presenting live work as idle）。DB 里这条工作流 `status='paused'`、`current_step=NULL`，正是这个归一化的结果。
- `auto_resume_count`：自动恢复护栏，跨重启持久化；**人工 start/resume/restart/rerun 清零，心跳/启动恢复只递增**（`schema_ddl.txt:13` 注释原文）。`_finish_continue_state` 在「本步真正完成」时把它一起清零（引擎字符串：`本步真正完成：交接原因、回执、付费继续次数清零；有进展了，自动续跑次数也清零。`）。
- 区间运行：`run_scope` 列注释（`schema_ddl.txt:17`）说存「起止步骤 id、本次要求」的 JSON，跨重启/心跳复活持续生效，跑到终点即清。**但 `we.load_run_scope(raw)` 对我构造的 11 种键名全部返回 `None`**（`exp_scope_result.json` / `exp_scope_result2.json`），包括 `start_step/end_step`、`start/end`、`from/to`、`start_skill/end_skill`、`steps`、`start_index/end_index`、`first/last`。**接受的键名：未证实**。只确定两件事：格式不对一律当没有范围（docstring 原文），以及 scoped 运行不触发强制检查点（`_forced_topic_checkpoint` / `_forced_plan_checkpoint` 的 `scoped=True` 分支）。

### 2.3 checkpoint（人工确认点）

运行时在 `backend.services.checkpoint_runtime`，HTTP 面在 `backend.routers.checkpoints`（前缀 `/api/workflows/{wf_id}/checkpoints`，`PUT /plan`、`GET /current`、`POST /resolve`）。

模块 docstring 原文：

> One server-owned clock and one decision per human checkpoint round. No model calls. Runtime identities deliberately expire on process restart: an old browser must never approve a recovered/new round with its previous token.

常量：`CHECKPOINT_TIMEOUT_SECONDS=1800`、`TIMEOUT_ACTIONS=('approve','pause')`。

实测（`exp_ckpt_result.json`、`exp_ckpt_result2.json`）：

- `start(wf, payload, timeout=2, on_timeout='approve')` → `public()` 返回
  `{active:true, checkpoint_id:'<32 hex>', step_name:'comp-modeling', display_name:null, checkpoint_type:'approve', primary_output_file:null, allow_feedback:true, started_at:ISO, deadline_at:ISO, timeout_seconds:2, remaining_seconds:2.0, on_timeout:'approve'}`。
- 用错 id 提交 → `CheckpointConflict: 检查点已变化或等待尚未恢复，请刷新后确认当前检查点`（这句是**原样**的，可用来判定客户端是否在旧 token 上重放）。
- 正确 id 提交 `{"action":"approve","data":{...}}` → `{status:'resolved', checkpoint_id:…, duplicate:false}`；再 `current()` 得 `active:false`。
- 超时：`on_timeout='approve'` → `{'action':'approve','auto':true}`；`on_timeout='pause'` → `{'action':'pause','auto':true}`，且此后 `current()` 为 `None`（这一条配合异常 `CheckpointTimeoutPaused` 的 docstring：`超时若设定为暂停，必须保持"等待确认"，用户回来可继续而不重算整步`）。
- `wait` 是**模块级函数** `wait(session, *, release=True)`，不是方法。
- 哪些类型超时后「转暂停」而不是「自动通过」：`_PAUSE_ON_CHECKPOINT_TIMEOUT = frozenset({'copyright_material','patent_disclosure'})`（实测）。竞赛流水线三类（`approve/feedback/idea_select`）都不在其中。

`aris.db` 的 `checkpoints` 表（DDL `schema_ddl.txt:53`，列 `data/response/status( pending|resolved )`）在这条工作流上**0 行**——它停在授权闸门之前，从没走到第一个确认点。

### 2.4 失败与重试语义

重试预算（常量实测）：`_MAX_STEP_RETRIES=5`、`_TRANSIENT_PROVIDER_RETRIES=5`、`_UNKNOWN_PROCESS_RETRIES=5`、`_INACTIVITY_RETRIES=5`、`_EMPTY_TOOL_RETRIES=5`、`_UNFINISHED_TURN_RETRIES=3`、`_BUN_PANIC_RETRIES=5`、`_PAID_CONTINUE_LIMIT=2`。

退避：`_RETRY_BACKOFF_SECONDS = {'transient_provider': (10,20,40,80,120), 'unknown_process': (5,10,20,40,60)}`；`_retry_backoff_seconds` docstring：`第 attempt 次（从 0 起）重试前的等待秒数；没登记的类别不等。`

分类器 `_process_retry_policy(result, *, allow_unfinished_turn=True) -> (kind, budget)` 实测（`exp_retry.json`）：

- `None`、`{}`、任意未知 dict → `('unknown_process', 5)`
- `{"incomplete_tool_calls":True}` / `{"failed_background_tasks":True}` / `{"incomplete_followup":True}` / `{"incomplete_background_tasks":True}` → `(同名 kind, 3)`
- **`transient_provider` 的触发条件：未证实**（只知预算与退避表，构造不出触发它的 result）。

超时语义：`_STEP_WALL_TIMEOUT_SECONDS = None`（无总时限），只有**静默超时**：`_step_inactivity_timeout` 实测 `comp-paper-zh=2700`、`comp-compile-zh=2700`、`comp-prob-analysis/comp-code/paper-figure=5400`（即稿件与编译 45 分钟，其余 90 分钟）。docstring 原文：

> Bound silent model calls without shortening any visible work.
>
> Competition manuscript and compile steps should continuously emit tool or compiler events.  Forty-five silent minutes indicates a stalled provider request, not productive writing; other legacy steps keep the conservative ninety-minute allowance.

失败文案（`_recovery_failure_message(reason, attempts, quality, stalled)` 实测）：

- `核心产物检查未通过（初次检查 + 3 次实际返修）：主产物未通过检查。`
- `质量检查未通过（初次检查 + 3 次实际返修）：主产物未通过检查。`
- `核心产物检查未通过（初次检查 + 3 次实际返修；因检查范围内的源码、结果与失败原因均未变化，已提前停止返修）：模型进程无响应。`

「继续」到上限的文案（`_continue_limit_message(2,'主产物仍未通过检查')` 原样）：

> 这一步已经连续继续执行 2 次仍没有完成，为避免继续花钱，先停在这里（产物和记录都保留着）。这次重新检查没通过的地方：主产物仍未通过检查。可以这样处理：① 换个模型或调高这一步的思考强度，再点「继续执行」（会重新计数）；② 打开产物自己改好后点「继续执行」：只重新检查、不调用模型，检查通过就算完成；③ 点这一步右侧的「重新执行此步骤」，从头重做这一步。

三条反作弊设计（都有实验支撑）：

1. `_artifact_progress_signature(ws, ["RESULTS.md"])` → `[["RESULTS.md", 200, "70d3bf8b0b9d83a61012"]]`；**原样重写同样内容签名不变**，所以「重写一遍」拿不到新的付费返修机会（`exp_sig`）。
2. `_health_requires_repair` 只认硬失败：`(health_ok=False, 任意 reason)` → `True`；`(True, '[CORE_ARTIFACT] …')` → `False`（`[OPTIONAL_OPTIMIZATION]`、`[NEEDS_FIX]` 也不触发硬返修，走各自的预算）。docstring 原文：

   > Never let auxiliary changes override deterministic missing artifacts.
   >
   > Retain the prior advisory treatment of size/page heuristics; they are not authority to rewrite a correct manuscript. Explicit figure, computation, companion, checker and submission failures cannot be converted to success.
3. 异常类型把「停」分成三档：`RepairStopped`（有明确证据说明活全停了）、`StepRepairInterrupted`（不安全/未完成，保留回执不许盲目重放）、`StepCheckPending`（安全停下，但执行与质量都没过）。

---

## 3. 产物校验：五类后检各查什么、怎么拦

先说**总原则**（这条最容易踩）：这五类里只有一部分进健康门。`step_review_report` 的模块 docstring 明写：

> ⛔ 只做展示：不进健康门、不触发返修、不写 error_message —— "带说明完成"那套机制已撤回（docs/INTERNAL_REPAIR_NO_DRAFT_BYPASS_2026-09-09.md）。读不到、格式不对就当没有，绝不影响步骤完成。结果在步骤完成时算一次存进 workflow_steps，前端轮询详情时不重算图片指纹。

`submission_review` 同样：

> ⛔ 只报告：不进健康门、不触发返修、不写 error_message。检查器自己出错只记"检查未完成"，绝不影响步骤完成。

所以五类后检的真实分工是：

| 后检 | 落盘位置 | 是否阻断 | 谁写 |
|---|---|---|---|
| `main_output_receipt` | `workflow_steps.main_output_receipt` | **阻断**（回执无效就必须真跑） | 引擎 `_main_output_receipt` |
| `precompile_report` | `workflow_steps.precompile_report` | 不阻断（只展示） | `skills/shared-scripts/precompile_guard.py` |
| `submission_check` | `workflow_steps.submission_check` + `SUBMISSION_CHECK.md` | 不阻断（只报告） | `venue_submission_check.py` |
| `writing_check` | `workflow_steps.writing_check` / `WRITING_CHECK.md` | 部分阻断（`error` 修，`fix` 只补一轮，`warning` 只显示） | `writing_review` |
| `vision_review` | `workflow_steps.vision_review` | **阻断**（最终门：issue 或 missing → exit 1） | `tools/vision_ledger.py` |

补一条读法：`vision_review` 的阻断发生在**图表工具自己的最终门**（`tools/vision_ledger.py` 退出码），而引擎侧的 `step_review_report.vision_review()` 只是把它汇总成步骤卡展示（docstring：⛔ 只做展示）。两者别混成一层。

### 3.1 `main_output_receipt`（唯一真正「省钱闸门」）

`_main_output_receipt(skill_name, primary, created, modified, started)` 产出 JSON（实测）：

```json
{"skill":"comp-code","primary":"RESULTS.md","at":<float>,"started":<float>,
 "created":["RESULTS.md"],"modified":["code/main.py"]}
```

`_usable_main_output_receipt(raw, workspace, skill_name, primary, upstream_completed)` docstring 原文：

> 回执有效 = 同一技能、同一主产物、之后没有上游步骤重新完成过、主产物现在仍然健康。

实测边界（`exp_receipt2`）：

- 换技能（`comp-modeling`）→ `None`；换主产物（`MODELING_REPORT.md`）→ `None`；坏 JSON → `None`。
- **把 `RESULTS.md` 覆盖成完全不同的短内容，回执仍然 usable** —— 回执**不是内容哈希绑定**，只绑 skill + primary + 上游未重跑 + 当前 health。也就是说「产物被换掉了」这条它能放过，真正拦得住它的是 health 与 `_artifact_progress_signature` 那一层。

### 3.2 `precompile_report`

来源 `.mh/precompile/changes.json`（由 `precompile_guard.py` 写）。我按三种猜测形状造了这个文件，`step_review_report.precompile_report(ws, 0)` **三次都返回 `None`**（`exp_precompile_result.json`）：说明它认的是工具自己那份 schema，手写对不上就当没有。字段内容（由 docstring 与 `collect` 的语义）：本步改了哪些文件、+/− 行数、最近改动清单、原文快照位置、关键说明。

### 3.3 `submission_check`

只在两种情况下跑：论文带 `.mh/writing_spec.json` 的投稿格式段，或上传了 LaTeX 模板。`COMPILE_SKILLS={'paper-compile-zh','paper-compile'}`，所以 `comp_shuwei` 的编译步（`comp-compile-zh`）**不在**这个集合里，只有跑 `paper-compile-zh` 的模板才会触发。写 `SUBMISSION_CHECK.md` + `.mh/quality/submission_check.json`，检查器是 `venue_submission_check.py`。

### 3.4 `writing_check`

`DRAFT_CHECK_SKILLS` 实测 12 个（`course-paper`、`course-report`、`humanities-write`、`humanities-write-latex`、`literature-review`、`paper-write`、`paper-write-docx`、`paper-write-nature`、`paper-write-nature-docx`、`paper-write-zh`、`paper-write-zh-docx`、`thesis-proposal`），**`comp-paper-zh` 不在里面**（`exp_writing_result.json`、`exp_writing_stage.json`）；`stage_for('comp-paper-zh')` → `None`，`stage_for('comp-compile-zh')` → `None`。所以这条流水线的论文步与编译步**都拿不到** `writing_check`（`FINAL_CHECK_SKILLS={'paper-compile-zh','paper-compile','docx-export'}`，`comp-compile-zh` 同样不在）。规划步跑 P 组写 `.mh/quality/writing_check.json`，写作步跑 S/I/R/D/C/N/K/T/H 组写 `WRITING_CHECK.md`，`STEP_CHECK_TIMEOUT_SECONDS=300`，结论带稿件指纹，读出来时判断「稿件之后有没有再改过」→ 填 `stale`。

模块 docstring 原样（`pyd writing_review`，全文见 `exp_writing_api.json`）关键两句：

> 需修项变成 `severity="fix"` 的 CheckIssue：step_recovery 只让写作步照清单定点改一轮，改完再查；还有就照实显示，不阻断、不判失败。提示合成一条不可修的 warning：只显示，不返修。检查器自己出错只记"检查未完成"，不拦、不返修。
>
> 结论和稿件版本绑定（检查器的 fingerprint）：稿件之后再改过，`is_stale()` 返回 True，步骤卡显示"已过期"。

### 3.5 `vision_review`

`tools/vision_ledger.py`（明文 Python，可读）。规则常量：`RULES_VERSION=2`、`MAX_ATTEMPTS=2`、`MAX_VERSIONS_PER_HOUR=4`、`MAX_ENTRIES=400`、`REPLY_KEEP=2000`；状态 `pass/issue/unreviewed`；退出码 `pass:0, issue:1, unreviewed:2`。

判定（`classify(reply)`，实测）：首行 `PASS`/`通过` 或「未发现…问题」→ `pass`；`ISSUE n:` / `问题n：` 行 → `issue`（排除「无/none/已撤回」）；EDGE 行含 `悬空` → `issue`；其余 → `unreviewed`。原文提示：

- `视觉模型的回复里既没有 PASS 也没有列出 ISSUE，无法判定`
- `没有这一版的审查记录` / `图文件不存在或读不到` / `视觉模型返回了空回复`
- 超过次数：`这一版已付费看过 2 次仍无法判定，不再重复调用`
- 版本节流：`这张图一小时内已看过 4 个版本；先按已列出的问题一次改好再审，不要改一点审一次`

账本键是 `"2:<sha256 of file>"`，`expected` 里按 kind 登记应审清单。最终门：`1 if result["issue"] or result["missing"] else 0`（`vision_ledger.py:546`）—— **issue 与 missing 阻断，unreviewed 只显示（exit 2）**。

实测一份合格账本喂给引擎侧汇总（`exp_vision2_result.json`）：

```json
{"kinds":[{"kind":"datafig","total":1,"pass":1,"issue":0,"unreviewed":0,"missing":0,"figures":[]}]}
```
`summary_lines` → `看图质检（数据图）：1 张全部通过`。

### 3.6 离线安装的现实：所有「付费检查器」都降级

本安装 `resources\app` 下**没有 `skills/` 与 `skills/shared-scripts/`**（技能正文只在授权通过后下发），于是所有依赖 shared-scripts 的检查器统一退化成同一句：

- 图表：`[CHECK_UNAVAILABLE] 当前版本图表检查工具暂不可用；已有图表已保留，请恢复连接后重新检查，不需要重绘。`
- 统计自洽：`[CHECK_UNAVAILABLE] 当前版本统计自洽检查工具暂不可用；已有数据与结果已保留，请恢复连接后重新检查，不需要重算。`
- 投稿规范：`[CHECK_UNAVAILABLE] 无法加载当前版本 shared-scripts：[WinError 2] 系统找不到指定的文件。: 'C:\\modex-mh-agent\\resources\\app\\backend\\license-v2-client.json'`

调用栈原样（stderr，`exp_gates` / `exp_html`）：

```
workflow_engine.py line 1565 in _check_figure_pdf_quality
paper_submission_contract.py line 362 in _materialized_checkers
skill_source.py line 93 in skill_source.resolve_skill_package
license_v2_client.py line 1435 in license_v2_client.default_client
license_v2_client.py line 658 in LicenseV2Client.load_profile
FileNotFoundError: [WinError 2] … license-v2-client.json
```

语义上这是 **fail-closed 但不判失败**：`[CHECK_UNAVAILABLE]` 既不算完成，也不据此让模型改数据（`_check_stats_coherence` docstring：`不算完成，也不据此让模型改写数据和结果`）。**顺序很重要**：清单对账在检查器之前跑，所以「规划 2 张、实际 1 张」这类硬缺陷照样能报出来。

### 3.7 页面数：参考值，不是闸门

`_check_paper_body_pages(ws, 'comp-paper-zh', max_pages, page_policy)` 实测：正文 7,600 / 38,000 / 152,000 汉字，`max_pages` 取 30 / 25 / 10 / `None`，`page_policy` 取 `advisory_max` / `hard`，**全部返回 `(True, "")`**（`exp_paper2_result.json`）。`_resolve_competition_page_rule('comp_shuwei', {'language':'zh'})` → `[30,'advisory_max']`，`('comp_mcm',{})` → `[25,'advisory_max']`。两条 docstring 原文（`pyd workflow_engine._resolve_competition_page_rule`、`._check_paper_body_pages`）：

> Return the final-submission page reference for one competition.
>
> Every competition uses ``advisory_max`` locally: the value is visible to the user but never becomes a generation, expansion, or compression gate.

> 按竞赛页数语义做保守的正文字符预检。
>
> 正文定义：
> - LaTeX 模式：`paper/sections/*.tex` 总字符数
> - Word 模式：`paper/main.md` 中"## 附录"之前的部分
> - 中文 chars_per_page ≈ 800（含图表），英文 ≈ 2200

这条对「我的 25 页超页」问题有直接含义：Modex 的页数是**告知**，不是**卡点**；超页在它那里不会 FAIL。

---

## 4. 上下文传递：一步的产物怎么进下一步

五条通道，按重要性排（4.1–4.4 是「给模型看什么」，4.5–4.8 是「引擎自己拿什么判」）：

### 4.1 `CLAUDE.md`：每步重写的「任务书」

`_generate_claude_md(workspace, title, template, params)` 每步重写工作区根的 `CLAUDE.md`（实测 8,014 B，`exp_claude_md.txt`；真实工作区那份 7,600 B / 79 行）。段落与行号（真实文件 `workspaces\7f5f0bf1057a\CLAUDE.md`）：

| 行 | 段落 |
|---|---|
| 3 | `## 项目说明`（`这是一个自动化研究管理的工作流引擎，当前正在执行「数维杯数学建模」流水线。`） |
| 6 | `## 流水线步骤`（1–7 步全列，第 5 步写实际选中的图引擎） |
| 15 | `## 重要规则`（全部产物落 cwd；Write/Edit 分块；禁用 Bash heredoc；长脚本 `timeout 900`；每步至少 1 个文件；先读已有文件） |
| 24 | `## 参数`（research topic / template / language） |
| 28 | `## Bash 环境变量（页数/字数等检查脚本会用到）` |
| 38 | `## ⛔ 流程图/架构图引擎 = HTML（用户选定，全程遵守）`（仅当第 5 步选了 HTML 引擎才出现） |
| 43 | `## 竞赛规则（数维杯数学建模（国内赛））`（30 页参考、ctexart、XeLaTeX） |
| 54 | `## 计算质量与有界验证`（14 条，含「不得篡改数据」「本步授权边界」） |
| 69 | `## 等计算时的单次等待上限`（单次等待 4 分钟、分析试算 `timeout 180`） |
| 74 | `## 数据图配色与版式（仅限数据图，与流程图独立）` |

`## 工作区文件` 段末尾固定附一句（`_CLAUDE_MD_FILES_NOTE` 原样）：

> `user_data/` 下是用户上传的原始材料，请完整阅读并作为研究基础；其余是前面步骤的产物，按需读取，未经本步核对不要当成题目事实。目录摘要只压缩重复路径，不允许把全量数据分析降级为抽样分析。

另写 `.env_skill`（141 B，实测内容）：

```bash
#!/bin/bash
# Auto-generated by workflow_engine.
# Source this in any bash script: source .env_skill
export SUBMISSION_PAGE_REFERENCE=30
```

### 4.2 `_build_context_summary`：真正的内容注入

`_build_context_summary(workspace, files, max_chars=12000)` docstring：`读取工作区已有文件的内容摘要，供给 Claude 参考。优先读取关键类型文件（md/tex/bib），并做字符预算。` 实测输出是 `### <file>` + 围栏代码块（`exp_context_summary.txt`，3000 上限时 1,295 字符）。

**哪些文件进「完整读取」名单**由 `_prev_output_is_report(path)` 决定，docstring 原样：

> 前序产出里要"完整读取"的：报告（.md/.bib）、根目录的小型事实与台账（.json，如 PROBLEM_FACTS / CROSS_PROBLEM_LEDGER）、figures/ 下的图表引用与表格源（.tex）。代码（.py）、子目录里的数据 JSON（真实工作区单个几百 KB 到 20 MB）、论文正文源码和 _tmp/ 临时文件不在此列：以前一并要求完整读取，写作步多达 104 个文件、1.3–21 MB。

其余前序产出只给数量与类型，走 `_prev_on_demand_note`（按需读，靠工作区文件索引）。**这就是 12,000 字符预算的来源**：不是把上一步全文塞给下一步，而是「报告全文 + 台账全文 + 图/表源 + 其余按需」。

### 4.3 `.mh/step-checkpoints/<digest>.json`：跨步产物证据

`_write_step_handoff_evidence(workspace, workflow_id, skill_name, outputs)` 实测产出（`exp_handoff`）：

路径 `…\.mh\step-checkpoints\340203beef774671.json`（16 位十六进制，与 `_CHECKPOINT_DIGEST_CHARS=16` 对齐），内容：

```json
{"completed_at": 1795246187,
 "files": [{"bytes": 19, "path": "PROBLEM_ANALYSIS.md",
            "sha256": "d8fff4a129637343b47be511a55eb2f586d8b2cd0f8cf4991154150f81226abd"}],
 "schema": 1, "skill": "comp-prob-analysis", "workflow_id": "wf-test"}
```

`_write_step_handoff(...)` 只是它的薄包装（返回同一路径）。这是「上一步到底交付了什么」的可核对凭据，也是崩溃恢复时判断「哪些已完成」的依据。

### 4.4 `upstream_guard`：不许下游改上游

模块 docstring 原样（`backend.services.upstream_guard`）：

> 下游步骤不得改写上游产物（机制审查 P5）。
> 实测：数据图步骤按工作区说明里"真实违例须定位并修受影响实现"去改 code/、重跑求解，只换掉部分结果文件，RESULTS.md、汇总 JSON、后几问仍是旧数——同一问出现两三套数。
> 两层保护（只用于竞赛流水线步骤，协同/编辑器调用不受影响）：
>   1. 工具守卫：通过环境变量 MH_PROTECTED_UPSTREAM 告诉 PreToolUse 守卫，本步不许 Write/Edit 已存在的上游文件、不许用命令覆盖它们或重跑求解代码；
>   2. 快照兜底：步骤开始时给上游产物做快照，每次 CLI 运行结束和步骤完成前逐个比对，被改动/删除的还原成开始时的版本，改动版另存到 .mh/upstream_guard/ 以便核对。
> 新建文件不受限制（数据图步骤可以写自己的补充数据）；只保护本步开始时已存在的上游产物。

实测（`exp_upstream_result.json`、`exp_upstream_result2.json`）：

- `prepare_step(ws, 'comp_shuwei', 'paper-figure')` 的快照清单就是 `RESULT_PATTERNS` 那 18 条：`code/**`、`output/**`、`submission/**`、`figures/all_results.json`、`figures/results.json`、`figures/problem_*_results.json`、`results.json`、`RESULTS.md`、`MODELING_REPORT.md`、`PROBLEM_ANALYSIS.md`、`PROBLEM_FACTS.json`、`CAPABILITY_CHECKLIST.json`、`CAPABILITY_VERDICT.json`、`DATA_FACTS.json`、`DELIVERABLES.json`、`SUBMISSION_SPEC.json`、`TOPIC_PLAN.md`、`DATA_SOURCES.json`。
- 篡改 `RESULTS.md` 并删掉 `code/main.py` 后 `restore_active()` → 返回 `(StepGuard, ['RESULTS.md','code/main.py'])`，文件内容回到 `原始结果 v1`，`main.py` 复活；改动版存到 `.mh\upstream_guard\paper-figure\rejected\20261121-154505\RESULTS.md`，原件在 `orig\`，另有 `manifest.json`（含每条 sha256）。
- 新建文件（`figures/fig_cost.pdf`）**不还原**。
- 每步的守卫清单不同：`patterns_for('comp_shuwei','comp-prob-analysis')` → `[]`；`'comp-code'` → 6 条（`PROBLEM_ANALYSIS.md`、`PROBLEM_FACTS.json`、`CAPABILITY_CHECKLIST.json`、`DATA_FACTS.json`、`SUBMISSION_SPEC.json`、`MODELING_REPORT.md`）；`'comp-paper-zh'` / `'comp-compile-zh'` → 全 18 条。
- 另有 `EVIDENCE_PATTERNS`（4 条：`_tmp/figure_use_plan.tsv`、`_tmp/refs_raw*.jsonl`、`_tmp/refs_raw.json`、`_tmp/scholar_raw.jsonl`）：跨步骤留档，**只防删不防改**。模块 docstring 末句原样：`另有一类跨步骤留档（EVIDENCE_PATTERNS，所有工作流都适用）：后面步骤的核对要读，只防删、不防改。`
- `DOWNSTREAM_SKILLS`（15 个，守卫只对这些 skill 生效）：`paper-illustration`、`comp-paper-huawei-zh-docx`、`comp-paper-huawei-zh`、`comp-paper-en`、`docx-export`、`comp-paper-en-docx`、`paper-figure-html`、`comp-compile-zh`、`comp-paper-zh`、`paper-figure`、`comp-paper-zh-docx`、`paper-figure-drawio`、`docx-format-check`、`nature-figure`、`comp-compile-en`。
- `STATS_ANALYSIS_PATTERNS` = `['TOPIC_PLAN.md']`（统计建模另加一层）。

### 4.5 `FIGURE_MANIFEST`：图表契约

`_read_figure_manifest(workspace)` docstring：从 `PROBLEM_ANALYSIS.md` / `PAPER_PLAN.md` / `MODELING_REPORT.md` / `TOPIC_PLAN.md` 读 `<!-- BEGIN FIGURE_MANIFEST -->` 区块，按**三章节标题**归类（权威，优先于文件名前缀），返回 `(data_figs, drawio_figs)`；找不到返回 `([], [])`。

实测分类（重要，别猜）：

| 章节写法 | 归到 |
|---|---|
| `**数据图**` `**数据可视化**` `**数据图（含表格）**` | 数据图 |
| `**流程图**` `**架构图**` `**流程图与架构图**` `**方法流程图**` `**架构**` `**流程图/架构图**` `**示意图**` `**技术路线图**` | **数据图**（不是架构图！） |
| `**TikZ 图**` `**TikZ**` `**流程图（HTML）**` `**DrawIO 图**` | 架构图 |
| `## 流程图` `## 架构图` `## DrawIO 图`（`##` 标题） | **数据图**（章节识别不生效，退化为前缀兜底） |

也就是说：**只有 `**粗体**` 标题才会走权威分类，且「架构图」必须写成 `DrawIO` / `TikZ` / `流程图（HTML）` 才会进架构桶**。写 `**架构图**` 会被要求产数据图。证据：`exp_manifest2/3/4`、`exp_scope_result2.json`。

配套登记文件：

- `figures/FIGURE_SOURCES.json` = `{"fig_cost": ["problem_1_results.json::cost_curve", ...]}`（可选；给了就必须指到存在的文件与可解析的字段，否则算图步自己的虚假声明）。
- `figures/FIGURE_SKIPPED.json`：docstring 原文 `A skip counts only when figures/FIGURE_SKIPPED.json names it with a reason *and* the missing data, and UPSTREAM_ISSUES.md mentions it…At most half of the planned figures (at least one) may be skipped`。实测：schema 是 `{"skipped":[{"figure":…,"reason":…,"missing":…}]}`；只写 `figure`+`reason` 会报 `…登记为画不出的图不符合要求：fig_cost（缺 reason 或 missing：要写清缺哪个文件/字段/哪一问的结果）`；不写 `skipped` 键报 `figures/FIGURE_SKIPPED.json 缺少 skipped 列表`。
- 架构图另有 `_registered_diagram_skips`：`The technical roadmap is always required, so it can never be skipped.`

### 4.6 没被引擎解析的「事实文件」

`PROBLEM_FACTS.json` / `CROSS_PROBLEM_LEDGER.json` 在引擎字符串表里**只出现在 `_prev_output_is_report` 的 docstring 那一句**里（`PROBLEM_FACTS / CROSS_PROBLEM_LEDGER）、figures/ 下的图表引用与表格源（.tex）。`），即引擎把它们当「要完整读取的前序产物」，自己**不解析**。真正读它们的是工具侧：`tools/paper_data_check.py:554-555` 把 `PROBLEM_FACTS.json` / `DATA_FACTS.json` / `DATA_PROFILE.json` 放进溯源池（同一池里还有 `results.json`、`results_*.json`、`figures/*.json`、`figures/TABLE_*.{tex,md,csv}`、`user_data/**/*_extracted.*`）。

`_step_outputs(paths)` 决定「哪些文件算这一步的产出」：docstring 原样

> 一步的"产出"清单（output_files、完成卡、对话结果、交接记录、市调 AI 附录都用它）：按出现顺序去重，去掉 `_tmp/` 自检脚本、`.mh/` 这类内部文件。它们接口本来就不让读，还会被当成成果写进 AI 任务记忆和参赛附录（真实验收 10-13：课程论文的产出里混着 _tmp/course-paper-1..5.py）。门禁、给模型的文件清单、"这一步动没动文件"的判断照旧用完整扫描，不走这里。

实测：`["RESULTS.md","_tmp/x.py",".mh/y.json","code/main.py","RESULTS.md"]` → `["RESULTS.md","code/main.py"]`。

### 4.7 第 0 步：题面 PDF 的 Vision 转录（`_VISION_PSEUDO_STEP='预处理'`）

赛题是 PDF/图片时，引擎在**第一步之前**跑一段不计入七步的预处理，把题面变成文字再进 CLAUDE.md。这块是「一道赛题」真正进流水线的入口，值得单独记。

| 函数 | docstring 原文 | 实测常量 |
|---|---|---|
| `_pdf_vision_targets(workspace) -> list[Path]` | `Return the deterministic PDF set shared by automatic and chat modes. The explicitly selected problem statement is always included. A small number of ordinary PDF attachments are also included, matching the legacy automatic-workflow policy without letting a large reference library trigger unbounded vision calls.` | — |
| `_extract_pdf_with_vision(workspace, workflow_id, progress_callback=None)` | `Bounded, source-versioned OCR; partial results are never called complete.` | — |
| `_needs_pdf_vision(pdf_file, *, now=None) -> bool` | `Return false for a good cache or a recent transient all-page failure. Successful OCR is reused indefinitely while its transcript exists. A full fallback is retried after a short cooldown, and replacing the source PDF invalidates the cooldown immediately through the source signature.` | `_PDF_VISION_RULE=2`、`_PDF_VISION_RETRY_COOLDOWN_SECONDS=1800` |
| `_record_pdf_vision_attempt(pdf_file, status, *, attempted_at=None)` | `Atomically retain only bounded retry metadata, never OCR text or secrets.` | — |
| `_describe_workspace_images(workspace, content, workflow_id=None, *, cached_only=False) -> str` | `扫描工作区中的图片文件，用 vision LLM 描述内容，追加到 CLAUDE.md 正文中。workflow_id 可选：传了就把识别进度推到前端日志区（这一步也跑在步骤循环之前，不推就是一段静默）。不传则退化成原行为，不影响其它调用方。cached_only：只用识别过的缓存（改设置、回退以后重写 CLAUDE.md 用），没识别过的不在这里花钱。` | — |
| `_notify_vision(workflow_id, text)` | `推一条预处理进度到前端日志区。⛔ 只吞 Exception，不能写成 except BaseException / 裸 except：CancelledError 继承自 BaseException，一旦在这里被吞掉，用户点暂停就对整个 vision 阶段失效了。推送失败本身无所谓 —— 前端还有 5~8 秒轮询兜底。` | — |

这条通道和 `aris.db` 对得上：`workflow_logs` 前 4 条正是 `正在准备上传材料、识别图片与赛题 PDF…` / `正在准备上传材料并检查识别结果` / `正在检查工作流授权；通过后识别上传材料` / `正在准备当前步骤所需工作流授权；尚未调用模型，不消耗模型额度`。也就是说本机这次运行**卡在预处理阶段的授权闸门**，七步一步都没进。

设计要点（可直接抄）：OCR 结果按源文件签名缓存、成功永久复用、全页失败冷却 30 分钟、换源文件立即失效；重试元数据与 OCR 正文分文件存（`_pdf_vision_state_path` docstring：`Internal retry ledger; deliberately excluded from public artifacts.`）。证据：`exp_vision_api.json`、`aris.db workflow_logs`。

### 4.8 `_STEP_SCOPED_SECTIONS`：哪些参数只给某几个 skill 看

`params` 里的开关不是全局生效，而是按 skill 白名单注入 CLAUDE.md（实测 `we._STEP_SCOPED_SECTIONS`，9 个键）：

| params 键 | 只对这些 skill 生效 |
|---|---|
| `PLAN_STAGE_GUIDANCE` | `comp-prob-analysis`、`comp-stats-topic`、`course-plan`、`course-report-plan`、`humanities-plan`、`paper-plan`、`paper-plan-zh` |
| `PLAN_USER_OUTLINE` | `paper-plan`、`paper-plan-zh` |
| `FIGURE_SUPPLEMENT_MODE` | `paper-figure` |
| `COURSE_DOCX_DRAWIO_PNG` | `paper-figure-drawio` |
| `PAPER_FIGURE_LANG_ZH` | `nature-figure`、`paper-figure`、`paper-figure-drawio`、`paper-figure-html` |
| `NATURE_FIGURE_LANG` | 同上四个 |
| `DOCX_FORMAT_CHECK_CONTEXT` | `docx-format-check` |
| `AUTO_REVIEW_DOCX_MODE` / `AUTO_REVIEW_PDF_MODE` | `auto-review-loop` |

这条对「给模型的话要不要说」有直接含义：同一个 `params` 字典里塞满开关，模型只会看到属于本步的那几个。证据：`pyd workflow_engine._STEP_SCOPED_SECTIONS`（本机实测逐项列出）。

### 4.9 检查点确认后 CLAUDE.md 要「重写并补回」

`_regenerate_claude_md_keeping_extras` docstring 原样（`pyd workflow_engine`，`exp_rewrite_note.json`）：

> 重新生成 CLAUDE.md，并补回开跑时追加的两段：上传图片的识别描述、材料核对提示。
>
> ⛔ 只重写不补，后续步骤就看不到图片里的题面信息（检查点确认后曾经这样丢过）。
> 图片描述走 `.mh/image-descriptions.json` 持久化缓存，开跑时已识别过的命中不付费；
> 材料核对只重写 CLAUDE.md 里那一段，不再给用户重复推送提示。

这是一条**真实事故留下的补丁**：CLAUDE.md 是「每步重写」的，重写会冲掉开跑时追加的图片描述段——用户一旦在检查点点确认，题面图片信息就在后续步骤里消失了。修法是「重写 + 补回」，并把图片描述落成 `.mh/image-descriptions.json` 缓存（命中不付费）。

对我的含义：凡是「每步重写任务书」的设计，都要同时给出「哪些内容是从别处补回来的」清单，否则第一次人工干预就会静默丢上下文。

---

## 5. 与我的 8 步 20 门对照

我的流水线：`E:\数学建模\.agents\skills\mathmodeling\scripts\pipeline.py`（`STATE_SCHEMA=4`，`STEPS` line 104，`GATES` line 679，`SOFT_GATES` line 707，`run_step` line 1009）。

| Modex 机制 | 我的等价物 | 我缺什么 |
|---|---|---|
| 七步 DAG（模板固定顺序，`_UPSTREAM_DEPS` 声明前置产物） | `STEPS` s1–s8 + `mmkit/crew.py:57 DEPENDS` / `:77 OUTPUT_OF` / `:102 WAVES` | Modex 的「前置产物不存在就不许开跑」是**引擎硬判**；我的依赖只写在 crew 里用于排序，`pipeline.py` 全文检索 `depends`/`upstream`/`上游` **零命中**，即本地流水线本身不验上游文件是否存在 |
| 每步 `primary_output` + 最小字节（`_STEP_MIN_SIZE`/`_primary_output_size`，含拆分 LaTeX 的合计口径） | `_md_gate` 只判「存在 + 非空 + 首 8 行有 VERDICT」 | 没有最小体量判据；也没有「`paper/main.tex` 是装配文件、真内容在 `paper/sections/`」这种口径（实测：`paper/main.tex` 42 B + `paper/sections/*.tex` 四份合计 96,030 B → `_primary_output_size` 返回 **96,072 B** = main.tex + 全部 sections 之和；同一目录换成 `comp-code` 调则返回 **42 B**，说明合计口径只对稿件类 skill 生效） |
| `_STEP_REQUIRED_COMPANIONS`（`comp-code` 必须有 `code/main.py` + `figures/all_results.json`，且汇总结构可读） | G4「求解」+ G5「数字对账」间接覆盖 | 没有「主产物之外还必须有这几件」的显式清单；`{}` 这种空壳汇总在我这儿能过 |
| `main_output_receipt` + `_usable_main_output_receipt`（同技能同产物、上游未重跑、当前健康） | `pipeline_state.json` 的 `status=="done"` | 我的 `done` 是**历史事实**，不校验产物此后有没有被换掉；也没有「回执失效就必须重跑」的机制 |
| `_free_recheck`（不调模型只重判）+ `_complete_step_without_model` | `--skip-dispatch --only sN --force` | 我是「人工记得重跑」，它是**自动降级**：连续「继续」到上限后转成只读重检，通过就算完成 |
| `_process_retry_policy` + `_RETRY_BACKOFF_SECONDS` + `paid_continues` 上限 2 | 无（一步 FAIL 就整条停，靠人改） | 没有失败分类、没有退避、没有「同类失败第 N 次就停手给出路」 |
| `_artifact_progress_signature`（内容签名，原样重写不算进展） | 无 | 我的「重跑」不看产物有没有实质变化，容易在同一个坑上反复付费 |
| `upstream_guard`（快照 + 还原 + `MH_PROTECTED_UPSTREAM` + rejected 留档） | 无（只有 AGENTS.md 口头禁令「`problem/` 只读」） | **最该补的一条**：没有机制阻止 s5 图表手去改 `code/` 重跑求解 |
| `_read_figure_manifest` + `FIGURE_SKIPPED` + `FIGURE_SOURCES` 对账 | G6「图表」（每张 PDF 跑 `mmkit.figfont.report` + 要求同名 `.png`） | 我没有「先声明图清单、再核对产出数」这一层，也没有「画不出要登记理由与缺哪个字段、最多跳一半」的出口 |
| `vision_review`（账本 + 次数上限 + 版本节流 + issue/missing 阻断、unreviewed 只显示） | G11「视觉审查」（软门） | 我的 G11 是软门（`SOFT_GATES`），`??` 也能过；Modex 把 issue/missing 做成**硬阻断**，只把「没审成」降级 |
| `writing_check` 三级 severity（`error` 必修 / `fix` 补一轮 / `warning` 只显示）+ 稿件指纹 stale | G7/G12/G17 + 写作手人工 | 我没有 severity 分级，也没有「检查结论对的是哪一版稿子」的指纹 |
| `submission_check` 只报告、不阻断 | G13「投稿体检」硬门 | 我是反的：Modex 明确「只报告」，我这门会 FAIL 整条流水线 |
| 页数 `advisory_max`（实测永不阻断） | G18「版式出栏」**不判页数**（`pipeline.py:581-640` 只判「图内文字越界 4pt」「Overfull hbox >10pt」；无图返回 `NA`）；页数在 `gauntlet_check.py:86` 的 `R-V01 body <= 30 pages` 里判 | 我把页数当硬门（C 题正文超 25 页）；Modex 只提示。**但这一条不能照搬**：数维杯/国赛的正文页上限是评审硬规则，`R-V01` 该留；该学的是 Modex 把「参考页数」与「版式硬伤」分成两个判据，不要用页数代替版式检查 |
| `checkpoint_runtime`（服务端时钟、32 hex token、1800 s、超时 approve/pause、旧 token 报冲突） | 无（我停下来靠人看 `--status`） | 没有「一轮确认只能有一个决定」「旧页面不许替新轮次点确认」这类语义 |
| `pause` 请求 + `clear_pause_request` 必须被所有启动路径调用 | 无 | 我的续跑没有暂停请求位，靠人 Ctrl-C |
| `.mh/step-checkpoints/<digest>.json`（每步产物 bytes + sha256） | `logs/pipeline_state.json` 记 `gates` 与时间 | 我记「判过什么」，不记「交付物的指纹」 |
| `_step_outputs` 过滤 `_tmp/`、`.mh/` | 无 | 我的 `out/` 与 `figures/` 里会混自检脚本，最终清单要靠人删 |

一句话总结差异：**Modex 把「这一步算不算完成」做成可重放的证据题（回执 + 指纹 + 快照 + 账本），我把「这一步算不算完成」做成一次性判断题（跑一次门，结果写进 state）**。

---

## 6. 可复用的三条设计（按能直接搬进 `pipeline.py` 写）

### 设计一：主产物回执 + 免费重检（省的是重复付费，不是判据强度）

要加的东西：

```python
# pipeline.py 顶部
RECEIPT_KEY = "receipt"          # 写进 st[step.key]
RECEIPT_RULE = 1                 # 口径变了就升，旧回执自动失效

def _artifact_fingerprint(paper: Path, rels: list[str]) -> dict:
    """本步声明的产物 → {rel: [bytes, sha256[:16]]}；缺文件记 None。"""
    import hashlib
    out = {}
    for rel in rels:
        p = paper / rel
        if p.is_file():
            b = p.read_bytes()
            out[rel] = [len(b), hashlib.sha256(b).hexdigest()[:16]]
        else:
            out[rel] = None
    return out

def usable_receipt(paper: Path, step: Step, st: dict) -> bool:
    """同一步、同一批产物、上游未重跑、指纹未变 → 不必重跑，直接复用结论。"""
    rec = st.get(step.key) or {}
    rc = rec.get(RECEIPT_KEY)
    if not rc or rc.get("rule") != RECEIPT_RULE or rc.get("status") != "done":
        return False
    if rc.get("outputs") != list(step.outputs):          # 声明变了就不认
        return False
    for up in step.depends:                              # 上游重跑过就不认
        if (st.get(up) or {}).get("finished_at", "") > rc.get("at", ""):
            return False
    return _artifact_fingerprint(paper, step.outputs) == rc.get("fingerprint")
```

参数建议：

- **`Step` 现在只有 `key/title/members/gates/review/compile_first` 五个字段**（`pipeline.py:95-101`），没有 `outputs`，也没有 `depends`。设计一要先加两个字段：`outputs: list[str]`（本步声明的产物）与 `depends: list[str]`（上游步骤 key）。取值建议：s1 `out/00-problem.md`；s3 `code/main.py` + `data/*.json` 摘要；s6 `main.tex`；s7 `main.pdf`。**目录型产物不要逐个文件哈希**，用 `(文件数, 总字节, 最大 mtime)` 三元组，否则 5,000 个中间文件会把指纹算成性能问题。
- 记录时机：`run_step` 里门全过之后（`pipeline.py:1062` 那句 `rec["status"] = "done"` 旁边）写回执，含 `{"rule":1,"at":finished_at,"outputs":[...],"fingerprint":{...},"gates":{...}}`。
- 复用时机：`main()` 的 `st[key]["status"] == "done"` 判断后面加一句 `and usable_receipt(...)`；不满足就当作未完成重跑（这正好补上「产物被换掉但 state 还是 done」的漏洞）。
- 免费重检：加 `--recheck` 开关，语义等价 `_free_recheck`：**不派单，只跑门**，跑完用 `_artifact_fingerprint` 比一次，指纹没变就不写新的 `finished_at`（防「重跑一次就算有进展」）。

### 设计二：上游守卫（快照 + 还原 + 拒收留档）

```python
GUARD_PATTERNS = {
    "s5": ["code/**", "data/**", "out/03-numbers.md", "out/05-caliber.md"],
    "s6": ["code/**", "data/**", "figures/**", "out/03-numbers.md"],
    "s7": ["code/**", "data/**", "figures/**", "main.tex", "out/09-writing.md"],
}
GUARD_DIR = ".mh/upstream_guard"      # 不放进 out/，免得被当成产物

def guard_snapshot(paper: Path, key: str, patterns: list[str]) -> dict:
    """派单前：把本步开始时已存在的上游产物记成 {rel: sha256}。"""
def guard_restore(paper: Path, key: str, snap: dict) -> list[str]:
    """派单后：比对 → 被改/被删的还原成快照版，改动版另存 rejected/<ts>/。返回被还原的相对路径。"""
```

要点（全部来自实测行为，照抄即可）：

1. **只保护「本步开始时已存在」的文件**；本步新建的文件不还原（`exp_upstream_result2`：新建 `figures/fig_cost.pdf` 保留）。
2. 被改动的版本**不要丢**，另存 `rejected/<YYYYmmdd-HHMMSS>/<rel>`，原件存 `orig/<rel>`，再写一份 `manifest.json`（`{"skill":…, "patterns":[…], "hashes":{rel:sha256}}`）。这样「谁改了上游」是可复核的。
3. 还原结果要能被门看到：`guard_restore` 返回非空列表时，在 `rec` 里记 `rec["upstream_restored"] = [...]`，并且**该步不许判 done**（等于强制重跑一次），否则会出现「上游被改 → 已还原 → 但本步基于被改版本算出的数字还在」。
4. 真要做工具层拦截，就照它的做法给子进程注入一个环境变量（`MH_PROTECTED_UPSTREAM` = 清单 JSON），让派单侧在 PreToolUse 里读；`env_value()` 的实测输出就是那份 18 条 patterns 的 JSON 数组，可直接当协议。

### 设计三：图表清单对账 + 合法跳过登记

```python
MANIFEST_BEGIN = "<!-- BEGIN FIGURE_MANIFEST -->"
MANIFEST_END   = "<!-- END FIGURE_MANIFEST -->"
DATA_SECTIONS  = ("数据图", "数据可视化", "数据图（含表格）")
ARCH_SECTIONS  = ("TikZ", "DrawIO", "流程图（HTML）")
SKIP_FILE      = "figures/FIGURE_SKIPPED.json"
ISSUES_FILE    = "UPSTREAM_ISSUES.md"

def read_figure_manifest(paper: Path) -> tuple[list[str], list[str]]:
    """从 out/00-problem.md / out/01-model.md / out/08-figures.md 读清单；
    只认 **粗体** 章节标题；`##` 标题一律不算章节（会退化成前缀兜底）。"""
def reconcile_figures(paper: Path) -> tuple[bool, str]:
    """规划 N 张 vs figures/<name>.{pdf,png} 实际 M 张；缺的允许登记跳过，
    但必须 (a) 写 reason 且写 missing（缺哪个文件/字段/哪一问），
    (b) UPSTREAM_ISSUES.md 里提到这个名字，(c) 跳过数 ≤ 规划数的一半。"""
```

参数与判据（照 Modex 原样）：

- 数据图命名建议 `fig_<what>.pdf` + 同名 `.png`（我 G6 已经要求 `.png` 兄弟文件，正好对齐）。
- 架构图前缀白名单可直接抄它那 24 条：`fig_arch fig_flow fig_roadmap fig_pipeline fig_framework fig_er fig_overview fig_system fig_module fig_index fig_hierarchy fig_multiagent fig_topology fig_dataflow fig_pkg fig_class fig_seq fig_gantt fig_network fig_model_decision fig_decision fig_state fig_uml tikz_`。**技术路线图（`fig_roadmap`）永不可跳**。
- 接进 `pipeline.py` 的位置：`gate_g6`（line 358）之前先跑 `reconcile_figures`，不通过直接 FAIL 并把原因写进 `gate_detail["G6"]`；通过后再跑现有的字号/`.png` 检查。
- 失败文案照它写（这样人一眼知道要补什么）：`规划 3 张, 实际 1 张, 缺 2 张`；`登记为画不出的图不符合要求：fig_cost（缺 reason 或 missing：要写清缺哪个文件/字段/哪一问的结果）`。

---

## 7. 证据附录

复现脚本与结果都在 `E:\数学建模\_swc2026\modex_re\`。下表 `pyd 模块.函数` 指用随包解释器导入后 `inspect` 得到的对象；`aris.db 表.列` 指只读打开的 `C:\Users\29900\AppData\Roaming\ModexData\library-sTDDnH\db\aris.db`。

| 结论 | 证据 |
|---|---|
| 步骤清单/顺序/checkpoint/output_files | `pyd workflow_engine.TEMPLATES['comp_shuwei']`；`exp_templates.json`；`aris.db workflow_steps.skill_name/display_name/step_order/has_checkpoint/checkpoint_type/output_files` |
| 模板总数与 `shuwei` 家族 | `pyd workflow_engine.TEMPLATES`（40 键，含 `comp_shuwei` / `comp_shuwei_en`）；`LEGACY_TEMPLATES` 只有 `comp_stats` 一个键 |
| 版本锚点（源码 sha256） | `backend\_modex-build-inputs.json`（`workflow_engine.py` → `a8fa9847…`，`workflow_acceptance.py` → `48eb164d…`）；`Get-Item` 实测 pyd 体量 5,448,704 B |
| 第 5 步 DB 里是 `paper-figure-html`、模板里是 `paper-figure-drawio` | `aris.db workflow_steps(step_order=4).skill_name`；`exp_templates.json`；`workspaces\7f5f0bf1057a\CLAUDE.md:6` |
| 最小字节阈值 | `pyd workflow_engine._STEP_MIN_SIZE` / `_min_size_for`；`exp_health_result.json` |
| health 不判字节 | `exp_health3.json`（270 B / 864 B 都 `(True,'')`） |
| 拆分 LaTeX 合计口径 | `pyd workflow_engine._primary_output_size` docstring；`exp_split`（`paper/main.tex` 42 B + `paper/sections/*.tex` 96,030 B → 返回 96,072 B；同目录用 `comp-code` 调 → 42 B） |
| 上游依赖 | `pyd workflow_engine._UPSTREAM_DEPS` / `_upstream_deps_for`；`exp_health_result.json` |
| 配套文件与空壳汇总 | `pyd workflow_engine._STEP_REQUIRED_COMPANIONS` / `_check_step_companions`；`exp_gates_result.json` |
| 状态取值 | `pyd workflow_engine.WorkflowStatus` / `StepStatus`；`exp_state.json`；`schema_ddl.txt:7,32` |
| `enable_checkpoints` 语义 | `schema_ddl.txt:10` |
| `auto_resume_count` 语义 | `schema_ddl.txt:13` |
| `run_scope` 语义 / 键名未证实 | `schema_ddl.txt:17`；`exp_scope_result.json`、`exp_scope_result2.json`（11 种键名全 `None`） |
| checkpoint 运行时 | `pyd checkpoint_runtime`（docstring、`CHECKPOINT_TIMEOUT_SECONDS=1800`、`TIMEOUT_ACTIONS`）；`exp_ckpt_result.json`、`exp_ckpt_result2.json` |
| `CheckpointConflict` 原文 | `exp_ckpt_result.json` |
| `_PAUSE_ON_CHECKPOINT_TIMEOUT` | `pyd workflow_engine._PAUSE_ON_CHECKPOINT_TIMEOUT`；`exp_misc_result.json` |
| 重试预算/退避 | `pyd workflow_engine._MAX_STEP_RETRIES` 等；`_RETRY_BACKOFF_SECONDS`；`exp_state.json` |
| 失败分类 | `pyd workflow_engine._process_retry_policy`；`exp_retry.json`（`transient_provider` 触发条件未证实） |
| 静默超时 | `pyd workflow_engine._step_inactivity_timeout`；`exp_misc_result.json`；`_STEP_WALL_TIMEOUT_SECONDS=None` |
| 失败文案 | `pyd workflow_engine._recovery_failure_message`（4 组实测输出） |
| 继续上限文案 | `pyd workflow_engine._continue_limit_message(2,…)`（原样） |
| 内容签名防刷 | `pyd workflow_engine._artifact_progress_signature`；`exp_sig`（原样重写签名不变） |
| `_health_requires_repair` 只认硬失败 | `pyd workflow_engine._health_requires_repair`；`exp_hr`、`exp_hr2`、`exp_precompile_result.json` |
| 回执形状与有效性边界 | `pyd workflow_engine._main_output_receipt` / `_usable_main_output_receipt`；`exp_receipt.py`、`exp_receipt2` |
| 交接证据文件 | `pyd workflow_engine._write_step_handoff_evidence`；`exp_handoff\.mh\step-checkpoints\340203beef774671.json` |
| 交接提示词原文 | `pyd workflow_engine._handoff_block` / `_fresh_retry_handoff` / `_with_handoff`（`exp_handoff` 实测三份全文） |
| `core_file_problem` 原文 | `pyd workflow_acceptance.core_file_problem`；`exp_acc_result.json`（`[CORE_ARTIFACT] 核心报告 …只有标题、空白或占位内容；请补充实际结果，不要凑字数`、`[CHECK_UNAVAILABLE] 无法读取核心报告 …：FileNotFoundError`） |
| `core_file_problem` 不判体量 | `exp_accept2`（300 B 纯 x 也返回 `""`） |
| `has_report_content` / `unfinished_sections` / `is_stats_workspace` | `exp_acc_result.json` |
| 图表清单分类 | `pyd workflow_engine._read_figure_manifest`；`exp_manifest2/3/4`、`exp_scope_result2.json` |
| 跳过登记 schema 与上限 | `pyd workflow_engine._registered_figure_skips` / `_registered_diagram_skips` docstring；`exp_skip_result.json`、`exp_skip_result2.json` |
| 图 PDF 质检不可用 | `exp_gates_result.json`、`exp_html`（stderr 调用栈） |
| 统计自洽不可用 | `exp_gates_result.json`（`workflow_engine.py line 835` → `paper_submission_contract.py line 362`） |
| 投稿规范不可用 | `exp_paper2_result.json` |
| 页数永不阻断 | `pyd workflow_engine._check_paper_body_pages` / `_resolve_competition_page_rule`；`exp_paper2_result.json`、`exp_misc_result.json` |
| 建模深度门自禁用 | `pyd workflow_engine._check_paper_modeling_quality_raw`；`exp_paper2_result.json`（`applicable:false, info:["上游展示公式少于 6 个，不启用数量门槛"]`） |
| 五类后检只展示 | `pyd step_review_report` 模块 docstring；`pyd submission_review` 模块 docstring；`exp_post_result.json` |
| `vision_review` 规则与退出码 | `tools/vision_ledger.py:36-68,85,299,360,546`；`exp_vision_result.json`；`exp_vision2_result.json` |
| `writing_check` 不含 `comp-paper-zh` | `pyd writing_review.DRAFT_CHECK_SKILLS` / `stage_for`；`exp_writing_result.json` |
| `CLAUDE.md` 结构与原文 | `workspaces\7f5f0bf1057a\CLAUDE.md`（7,600 B / 79 行）；`exp_claude_md.txt`（8,014 B） |
| `.env_skill` | `workspaces\7f5f0bf1057a\.env_skill`（141 B） |
| 上下文摘要与「完整读取」白名单 | `pyd workflow_engine._build_context_summary` / `_prev_output_is_report` / `_prev_on_demand_note`；`exp_context_summary.txt` |
| 题面 Vision 预处理（缓存/冷却/目标集） | `pyd workflow_engine._pdf_vision_targets` / `_extract_pdf_with_vision` / `_needs_pdf_vision` / `_record_pdf_vision_attempt` / `_describe_workspace_images` / `_notify_vision`；`exp_vision_api.json`（`_PDF_VISION_RULE=2`、`_PDF_VISION_RETRY_COOLDOWN_SECONDS=1800`、`_VISION_PSEUDO_STEP='预处理'`） |
| `_STEP_SCOPED_SECTIONS` 9 键白名单 | `pyd workflow_engine._STEP_SCOPED_SECTIONS`（本机逐项打印，见 4.8 表） |
| CLAUDE.md 重写要补回图片描述与材料核对 | `pyd workflow_engine._regenerate_claude_md_keeping_extras` docstring；`exp_rewrite_note.json`；`exp_ckpt_strings.json`（字符串表命中同一句） |
| `writing_review` 模块 docstring 与函数签名 | `pyd writing_review`；`exp_writing_api.json`（`run` / `run_for_step` / `run_final` / `step_issues` / `stage_for` / `is_stale` / `finalize_plan` 的完整 docstring） |
| `stage_for` 全映射与三个 skill 集合 | `pyd writing_review.stage_for` / `FINAL_CHECK_SKILLS` / `DRAFT_CHECK_SKILLS` / `PLAN_CHECK_SKILLS`；`exp_writing_stage.json` |
| `PROBLEM_FACTS`/`CROSS_PROBLEM_LEDGER` 引擎不解析 | `workflow_engine.strings.json`（仅出现在 `_prev_output_is_report` docstring）；`tools/paper_data_check.py:554-555` |
| `upstream_guard` 全流程 | `pyd upstream_guard`（模块 docstring、`RESULT_PATTERNS`、`patterns_for`、`StepGuard`）；`exp_upstream_result.json`、`exp_upstream_result2.json` |
| `_step_outputs` 过滤 | `pyd workflow_engine._step_outputs`；`exp_scope_result.json` |
| 授权闸门与 `MODEL_KEY_MISSING` | `aris.db workflow_steps(step_order=0).error_message`、`workflow_logs` id 5/6（两行原文）；`pyd workflow_engine.AccessModeError`（构造该 code 抛 `KeyError`，正文不在字节里）；后端全量扫描 `MODEL_KEY_MISSING` 命中 0 文件 |
| 检查点表结构 | `schema_ddl.txt:53-60`；`aris.db checkpoints`（0 行） |
| 本机 8 步 20 门 | `pipeline.py:81,104,679,707,1009`（`STATE_SCHEMA`/`STEPS`/`GATES`/`SOFT_GATES`/`run_step`） |
| 我的门函数行号 | `pipeline.py:221 G1, 225 G2, 275 G3, 279 G4, 305 G5, 358 G6, 400 G7, 414 G8, 426 G9, 434 G10, 450 G11, 462 G12, 496 G13, 506 G14, 517 G15, 522 G16, 549 G17, 581 G18, 643 G19, 659 G20` |

**未证实清单**（不许当结论用）：

1. `run_scope` 的 JSON 键名（11 种试法全 `None`，只知语义不知字段名）。
2. `transient_provider` 的触发条件（只知预算 5 与退避 10/20/40/80/120）。
3. `workflow_steps.resume_error_code` 的取值词表（DDL 有列、注释说是「类型化原因」，但后端字节里搜不到该标识符）。
4. `precompile_report` 的 `changes.json` 真实 schema（三种猜测形状都被判「没有」）。
5. `MODEL_KEY_MISSING` 的文案来源模块（`AccessModeError` 内部 code→message 映射表，构造即 `KeyError`；后端 0 命中，只能以 `aris.db` 行文为准）。
6. `_process_retry_policy` 对「空 tool 调用 / bun panic」两类预算（常量存在，构造不出 result 去命中）。
7. 「`enable_checkpoints=0` 时三个 `approve/feedback` 步确实不停」—— 只有 DDL 注释与两个 `_forced_*` 的反证，没有真跑起来的观测（本机这次运行卡在授权闸门，七步一步没进）。

VERDICT: PASS
