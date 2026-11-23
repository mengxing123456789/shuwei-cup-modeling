---
name: paper-kit
description: "本机论文质检工具链：42 个可离线跑的检查与导出脚本（31 个 .py + 11 个 .pyc）（学术写作 40 条规则、数据真实性核对、投稿前体检、文献检索取 BibTeX、DOCX 导出与模板填充、LaTeX 模板体检、问卷 Kano/PSM/联合分析/SEM 全套、图表视觉审查），10 家期刊投稿格式注册表（每条规则带官网原文与访问日期），13 份 DOCX 版式档案（含对标 cumcmthesis 的竞赛中文样式），9 份科研流程模板，40 套竞赛/论文流水线定义（含数维杯、亚太赛、美赛、国赛）。用于数学建模竞赛与学术论文的成稿检查、格式对齐、文献与图表核对。用户提到投稿前检查、写作规则检查、文献取 BibTeX、DOCX 模板填充、期刊格式、竞赛流水线、图表审查时使用。"
argument-hint: "[要跑的工具或任务]"
user-invocable: true
---

# paper-kit（本机论文质检工具链）

一套纯本机、可离线跑的论文检查与导出工具。**不依赖任何外部软件安装**——所有脚本只依赖本机
`E:\Mini\envs\mathmodel`（Python 3.11，含 numpy / pandas / pymupdf / python-docx）。

## 路径

| 目录 | 内容 |
|---|---|
| `tools\` | 42 个脚本（31 个 `.py` + 11 个 `.pyc`），全部本机实测可跑 |
| `tools\journal_registry\families.json` | 10 家期刊/会议投稿格式，规则带 `quote` + `source_url` + `accessed` |
| `tools\docx_style_profiles\` | 13 份 DOCX 版式档案 + `covers\` 封面素材 |
| `templates\` | 9 份科研流程模板（研究契约、实验计划/日志、发现、Idea 候选、论文计划…） |
| `prompts\` | 8 份写作提示词（DOCX 渲染陷阱、学术 Markdown 写法、课程/论文图语言） |
| `pipelines.json` | 40 套流水线的步骤定义（含 `comp_shuwei` / `comp_shuwei_en` / `comp_apmcm` / `comp_mcm`） |

## 11 个 `.pyc` 脚本（无源码，只能当黑盒调）

这 11 个是原厂以字节码发布的模块，没有对应 `.py`。magic 是 `a70d0d0a`，**只匹配 Python 3.11**，
`run_tool.py` 用 `SourcelessFileLoader` 加载，实测在本机 `mathmodel`（3.11.18）全部可跑：

| 脚本 | 作用 | 调用 |
|---|---|---|
| `analyze_docx.pyc` | 逐段提取字体/字号/对齐/缩进/行距，写 JSON 版式档案 | `analyze_docx.pyc <docx> [--json-out p]` |
| `analyze_latex_template.pyc` | 拆 LaTeX 模板的结构与版式参数 | `--input <tex> --output <json>` |
| `derive_profile.pyc` | 从一份 DOCX 反推 style profile | `--input <docx> --output <json>` |
| `derive_profile_unified.pyc` | 自动判别并反推（`derive_profile_auto`） | 无参即可 |
| `docx_precheck.pyc` | 导出前体检：裸公式、字数、段落计数 | `--source <docx> [--workspace w]` |
| `fix_bare_latex_in_md.pyc` | 扫描并修复 Markdown 里缺 `$$` 的裸公式块 | `<md 路径>` |
| `generate_format_reference.pyc` | 按工作流生成格式参考 Markdown | `--workflow w --out p` |
| `proposal_docx_layout.pyc` | 开题报告 Word 版式：补封面信息表与评议栏、正文页码从 1 起 | `<docx>` |
| `stats_docx_package.pyc` | 统计建模大赛 Word 交付件版式 | `<docx>` |
| `thesis_docx_layout.pyc` | 学位论文（本/硕/博）Word 确定性排版 | `<docx>` |
| `markdown_utils.pyc` | 被 `count_chapter_words` import 的字数/清洗工具 | 不单独调用 |

实测样例：`analyze_docx.pyc "2021 APMCM Summary Sheet.docx" --json-out _t.json` → exit 0，
输出 `body_en font=Times New Roman size_pt=12.0 bold=False alignment=center first_line_indent_pt=0.0 line_spacing=1.25`，
JSON 507 B。

**限制**：这 11 个只能按命令行调，改不了内部逻辑；要改就得重写。`figure_style_regression_gallery.pyc`
**没有搬**——它 import `skills/shared-scripts/plot_utils.py`，而那个目录在原厂安装包里就不存在（是构建时漏打的），
搬过来也跑不了。

## 怎么跑（统一入口 `run_tool.py`）

**一律用 `run_tool.py` 当壳**，不要直接 `python tools\xxx.py`：

```powershell
$PY = 'E:\Mini\envs\mathmodel\python.exe'
$T  = 'E:\数学建模\.agents\skills\paper-kit\tools'

& $PY "$T\run_tool.py" --list                       # 列全部脚本
& $PY "$T\run_tool.py" academic_writing_check.py --stage final --skill paper-write <工作区>
& $PY "$T\run_tool.py" venue_submission_check.py   <工作区>
& $PY "$T\run_tool.py" scholar_fetch.py bibtex-doi 10.1109/4235.996017
& $PY "$T\run_tool.py" count_chapter_words.py <某个.md>
```

**为什么要有这层壳**：脚本之间有互相 import（`count_chapter_words` → `markdown_utils`、
`docx_export` → `docx_text`、三个 vision 检查 → `trusted_gateway_config`）。直接跑时脚本目录
不一定在 `sys.path` 首位。`run_tool.py` 把 `tools\` 插到 `sys.path[0]`，再用 `runpy.run_path`
执行，退出码透传。

`markdown_utils.pyc` 只有字节码（无 .py 源码），magic `a70d0d0a` 只匹配 **Python 3.11**——
本机 mathmodel 是 3.11.18，可用；换 3.12 会报 `bad magic number`。

## 三个真能改变交付质量的工具

### 1. `academic_writing_check.py` — 40 条写作规则（只读，不改稿）

```powershell
& $PY "$T\run_tool.py" academic_writing_check.py --stage final --skill paper-write <工作区>
& $PY "$T\run_tool.py" academic_writing_check.py --stage plan  --skill paper-plan   <工作区>
```

`--stage plan` 查大纲论证主线（P1–P4）；`--stage draft|final` 查成稿（S 结构 / I 引言 / R 综述 /
D 讨论 / C 结论 / N 话说过头 / K 口吻 / T 按研究类型 / H 人文 / Q 开题）。
退出码：**0 无问题 / 1 有需修 / 2 不适用 / 3 没跑成**。

规则实例：C1 结论在重复摘要、N1 话说过头（首次/填补空白/领先所有）、R1 文献罗列（甲认为、乙认为）、
K3 流程用语进了正文、I1 引言提前报告结果。

**与 `mathmodeling` 的 `gauntlet_check.py` 互补**：gauntlet 查页数/编号/字体/引用，这个查**写作逻辑与口吻**。

> ⚠️ 竞赛论文默认**不跑**这一项：它按学术论文文体判（要求 Limitations 一节、Discussion 要与已有研究比较），
> 竞赛稿没有这些硬要求，强跑会出假 FIX。要跑需先在工作区写 `.mh\writing_spec.json`（**必须用 python 写**，
> PowerShell 5.1 的 `Set-Content -Encoding UTF8` 带 BOM 会让 json 解析失败 → 整步静默 SKIP）。

### 2. `venue_submission_check.py` — 投稿前体检

```powershell
& $PY "$T\run_tool.py" venue_submission_check.py <工作区> [--json]
```

读 `paper/main.pdf`、`paper/main.log`、`main.tex` 及其 `\input`，逐项核对：页数、字体嵌入、
书签链接、PDF 属性、中文、匿名、模板未被改、样张残留、中文前置部分。
产出 `SUBMISSION_CHECK.md`（给人看）+ `.mh\quality\submission_check.json`（给程序看）。
**只报告不拦**（设计如此）。

实测（数维杯 LaTeX 骨架，8 页）：`1 项要你处理，3 项提醒，3 项通过，1 项不适用`——
那 1 项就是稿子里的 `[占位符]` 还没换。它还抓出过两处真版式缺陷（`\item [xxx]` 被排到版心外、
`lstlisting` 的 `frame=single` + `numbers=left` 双重外溢）。

### 3. `scholar_fetch.py` — 四级 fallback 取文献与 BibTeX

```powershell
& $PY "$T\run_tool.py" scholar_fetch.py search "NSGA-II multiobjective" --max 10
& $PY "$T\run_tool.py" scholar_fetch.py bibtex-doi 10.1109/4235.996017
& $PY "$T\run_tool.py" scholar_fetch.py bibtex-id 2301.07041
```

AMiner → Semantic Scholar → CrossRef → DBLP 依次降级。**直接吐 BibTeX**，省掉手抄作者年份卷期页码。
配合 `mathmodeling` 的 `R-W04 references have type markers` 与 `>=70% references cited` 两条验收门用。

## 其余工具速查

| 脚本 | 干什么 | 实测 |
|---|---|---|
| `paper_data_check.py` | 数据真实性自检（数字能不能溯源到产物） | OK |
| `template_ingest.py` | LaTeX 模板体检：认主文件/收依赖/判编译方式/试编译 | OK |
| `docx_export.py` | Markdown → DOCX（中文学术格式、三线表、OMML 公式） | OK |
| `docx_template_fill.py` | 把 Markdown 填进自己的 .docx 模板（保留封面/页眉/页边距） | OK |
| `docx_template_analyze.py` | 分析 .docx 模板的段落与样式结构 | OK |
| `derive_reference_from_docx.py` | 从 .docx 反推 Markdown 参考格式 | OK |
| `survey_methods.py` | Kano / PSM / 联合分析 / SEM / CFA，**数字全由脚本算** | OK |
| `survey_schema.py` | 问卷 schema 校验 + codebook | OK |
| `survey_render.py` | 出 markdown / 问卷星可粘贴文本 / codebook 三态 | OK |
| `survey_sample_size.py` | 样本量计算 | OK |
| `survey_simulate.py` | 问卷数据模拟 | OK |
| `survey_import.py` / `survey_clean.py` | 导入与清洗 | OK |
| `survey_docx_deliver.py` | 问卷报告出 DOCX | OK |
| `survey_formulas.py` | 问卷统计公式与结果文件 | OK |
| `humanities_review.py` | 人文社科稿确定性规则校验 | OK |
| `arxiv_fetch.py` | arXiv 搜索与下载 | OK |
| `count_chapter_words.py` | 分章字数统计（中英分开计） | OK |
| `paper_source_scope.py` | 稿件来源范围核对 | OK |
| `vision_ledger.py` | 视觉核对台账 | OK |
| `data_fig_vision_check.py` | 数据图视觉审查（轴标签截断/图例压数据/刻度重叠） | OK，需视觉模型 |
| `tikz_vision_check.py` | TikZ 图视觉审查 | OK，需视觉模型 |
| `drawio_vision_check.py` | draw.io 图视觉审查 | OK，需视觉模型 |
| `screenshot_capture.py` | Chromium 截图（可出矢量 PDF） | 需 Electron 环境 |
| `gpt_image.py` | GPT Image 生图 | 需 `GPT_IMAGE_API_KEY` |

### 图表视觉审查怎么接（本机 magpie 网关）

三个 `*_vision_check.py` 用 OpenAI 兼容协议调视觉模型，认环境变量：

```powershell
$env:OPENAI_BASE_URL   = 'http://127.0.0.1:3425/v1'
$env:OPENAI_API_KEY    = 'sk-local'
$env:REVIEWER_MODEL_ID = 'opencode-zen-free/nemotron-3.5-super-vl-free'
& $PY "$T\run_tool.py" tikz_vision_check.py <图片路径> [--source <源文件>]
```

实测输出 `PASS` / `CACHED_PASS`（同一张图第二次审直接沿用结论，不再付费）。
它们**不吃 `--help`**：无参数时打印用法并 exit=2。

## 数据资产：怎么用

### `journal_registry\families.json`（10 家）

`ieee_conf`(8 条规则) / `ieee_journal`(7) / `springer_lncs`(5) / `elsevier`(4) / `journal_en`(0) /
`cn_journal`(4) / `springer_nature`(2) / `wiley`(1) / `mdpi`(0) / `tandf`(2)。

每个 family 带 `review_modes`、`page_reference`（官方 note + `source_url` + `locator_zh` + `accessed`）、
`ai_statement`（AI 披露位置 + 官方原文）、`writing_notes_zh`、`rules[]`。
**`_doc` 里的硬规矩**：规则必须附官网原文（`quote`）、出处（`source_url`）和访问日期（`accessed`），
找不到原文的值不写进来。

→ 需要「某刊 AI 声明怎么写、页数上限多少、模板 class 用哪个」时查这里，比现搜官网快且带出处。

### `docx_style_profiles\`（13 份）

`competition_zh`（对标 cumcmthesis：A4 四边 2.5 cm、标题 SimHei 15 pt 居中、正文 SimSun 12 pt
行距 1.5 首行缩进 2 字、三线表 1.5/0.75/1.5 pt、参考文献悬挂 0.74 cm 10.5 pt 方括号）、
`competition_mcm`（`header_text = "Team # {CONTROL}, Page {PAGE} of {PAGES}"`、`summary_sheet` 三栏）、
`competition_en`、`competition_mathorcup`、`cn_degree_thesis`、`default_cn_thesis`、`course_paper`、
`course_report`、`literature_review`、`market_survey_zh`、`reference_paper_general`、`stats_zh`、
`thesis_proposal`。

→ **Word 交稿时**用 `docx_export.py --profile competition_zh` 直接套；**LaTeX 交稿时**当排版对照表查
（数维杯官方 `swmcmthesis.cls` 已在本机 MiKTeX 编通，见 `数维杯\05_模板与工具\latex\README.md`）。

### `pipelines.json`（40 套）

`comp_shuwei`（中文，7 步）/ `comp_shuwei_en`（英文，7 步）/ `comp_apmcm` / `comp_mcm` / `comp_cumcm` 等。

7 步骨架：`赛题分析(approve) → 建模求解(feedback) → 编程实现(approve) → 图表生成 →
流程架构图 → 论文撰写(approve) → 编译与合规检查`。

**把检查点位置、反馈点位置抄进 `mathmodeling` 的 `RUNBOOK.md` 8 波里**即可。

## 与 `mathmodeling` 技能的分工

| 谁 | 管什么 |
|---|---|
| `mathmodeling` | 主线：读题 → 建模 → 求解 → 出图 → 成稿 → 验收。75 条 RULES、13 人 8 波小队、`gauntlet_check.py` 16 项硬检查 |
| **本技能** | 补 `mathmodeling` 没有的：**写作逻辑检查**（40 条）、**投稿格式库**（10 家带出处）、**文献取 BibTeX**、**图表视觉审查** |
| `数维杯\05_模板与工具\latex\build.ps1` | 编译：`pdflatex ×3`（英文 swmcmthesis）/ `xelatex ×3 + biber`（中文） |
| `mathmodeling\scripts\submission_gate.py` | 总闸：一次跑 gauntlet + venue [+ writing]，出统一结论表 |

## 坑（已实测）

1. **别直接 `python xxx.py`**：脚本互相 import，脚本目录不在 `sys.path` 首位就
   `ModuleNotFoundError: No module named 'markdown_utils'`。**一律走 `run_tool.py`**。
2. `markdown_utils.pyc` 无 .py 源码，magic `a70d0d0a` 只匹配 Python 3.11；换版本报 `bad magic number`。
3. `*_vision_check.py` 三个（`data_fig` / `tikz` / `drawio`）不吃 `--help`，无参数时打印用法并 exit=2。
   它们是给视觉模型用的，需要图像路径与模型凭据（见上）。
4. `venue_submission_check.py` 找的是 `paper/main.pdf`（`paper\` 子目录）。扁平布局
   （`main_en.tex` 在根上）要先把 PDF 摆进 `paper\`，或用 `submission_gate.py` 自动搭临时视图。
5. `academic_writing_check.py` 对纯 LaTeX 工作区会 `SKIP: 不适用`（退出码 2）——它按写作档案和
   Markdown 成稿找，LaTeX 稿需先有 `.mh/writing_spec.json` 或走 `--source` 指定。
6. `survey_import.py` 的 `pyreadstat` 依赖是可选的（只读 SPSS `.sav` 时才需要），没装不影响 Excel/CSV。
7. `screenshot_capture.py` 需要 Electron 运行环境，本机无独立 Electron 时会走降级退出码 2。

## 自建的两个替代模块（原脚本依赖它们，此处为纯本机实现）

| 模块 | 干什么 |
|---|---|
| `tools\trusted_gateway_config.py` | 解析视觉/生图模型的 base_url 与 TLS 上下文。地址优先级：`snapshot` → `VISION_BASE_URL` > `OPENAI_BASE_URL` > `EDITOR_AI_BASE_URL` > `GPT_IMAGE_BASE_URL` → `https://api.openai.com`。`backend_loopback_url()` 只放行 `http://127.0.0.1` / `localhost` / `[::1]` |
| `tools\docx_text.py` | `read_markdown()`：UTF-8 → UTF-8-SIG → GB18030 依次解码，全失败抛 `DocumentEncodingError`（不静默乱码） |
