# 仓库目录地图

工作区根：`E:\数学建模`。这份文件解释**每个目录是什么、为什么在仓库里、哪些被 `.gitignore` 排除以及为什么**。

跟踪面：**3,262 文件 / 598.9 MB**（2026-11-23 已删 5.6 GB C 题原始视频数据；磁盘剩余约 3.8 GB，其余是被排除的虚拟环境、二进制缓存与临时脚手架）。

---

## 一、会被提交的目录

### `.agents/skills/` —— 技能树（175 文件 / 2.3 MB）

| 技能 | 体积 | 用途 |
|---|---|---|
| `mathmodeling/` | 0.78 MB / 86 文件 | 主流水线。`SKILL.md` 是入口；`WORKFLOW.md` 定义八步二十门的判据；`RULES.md` 75 条硬规则（E19 证据 / M17 建模 / T6 表格 / W12 写作 / V21 验证）；`RUNBOOK.md` 排障；`CORPUS.md` 真题语料检索；`scripts/` 是全部可执行物；`squads/main/`（18 人建稿队）与 `squads/review/`（13 人评审队）是 brief 正文；`reference/shuwei2026c-handoff.md` 是 C 题交接档 |
| `paper-kit/` | 1.46 MB / 71 文件 | 42 个离线检查脚本（`tools/run_tool.py` 是统一入口）、10 家期刊格式注册表、13 份 DOCX 版式档案、40 套竞赛流水线定义（`pipelines.json` 含 `comp_shuwei` 与 `comp_shuwei_en`） |
| `paper-language-pass/` | 6 文件 | 润色 / ±5–15 词微调 / 逻辑红线 / 去 AI 味，最小干预 |
| `paper-figures-captions/` | 4 文件 | 架构图 prompt、实验图型选择、图注表注 |
| `paper-results-review/` | 3 文件 | 数据→结果分析段落；PDF→审稿报告 |
| `paper-cn2en-draft/` | 4 文件 | 中文草稿→英文正文；英文 LaTeX→中文速读 |
| `README.md` | 1 文件 | 四个 `paper-*` 技能与 `mathmodeling` 的分工、改编来源与维护纪律 |

被排除的只有 12 个 `.pyc`（`paper-kit/tools/*.pyc`、`paper-kit/prompts/__init__.pyc`）——它们是编译缓存，源码 `.py` 全部在仓库里。

### `_swc2026/` —— 2026 秋季赛主战场（约 66 MB 跟踪面）

```
_swc2026/
├── 00-README.md … 56-朱雀AIGC检测报告.md   55 篇过程报告（见下表）
├── SWC2026_C/                             ★ C 题论文工程（跟踪面 66.4 MB / 867 文件）
│   ├── main.tex  slots.tex  slots.full.tex  swmcmthesis.cls/.cfg
│   ├── CSWBMCM2634892.pdf                 提交稿 67 页
│   ├── CSWBMCM2634892cns.pdf              承诺书
│   ├── CSWBMCM2634892fj.zip               支撑材料 480 条目
│   ├── CSWBMCM2634892.docx                供查重/AIGC 站的 DOCX
│   ├── code/        200+ 脚本（含 mmkit 之外的独立实现）
│   ├── data/        所有实测 JSON（唯一数字来源）
│   ├── tables/      18 个 .tex 片段（多数由脚本生成）
│   ├── figures/     27 张图（全部由脚本生成）
│   ├── problem/     官方题面与 7 个附件
│   ├── audit/       verify_claims.py（145 条结构断言）
│   ├── snippets/    reproduce.ps1（一键复现）
│   └── logs/        训练与编译日志
├── SWC2026_A/  SWC2026_B/  SWC2026_D/     另外三题的第一轮尝试
├── SWC2026_C_ALT_BACKUP/                  备用稿（更早的排版版本）
├── award_corpus_2025/                     2025 数维杯获奖论文 PDF（对标用）
├── award_corpus_2023intl/                 2023 国际赛获奖论文 PDF
├── modex_re/                              Modex 逆向工作目录（字符串表、zlib、schema）
└── _modex_re_work/                        Modex 逆向的中间产物与批处理脚本
```

`_swc2026` 根的报告按主题分五段，**按编号顺序读就是完整的决策链**：

| 编号 | 主题 | 代表文件 |
|---|---|---|
| 00–04 | 选题 | `00-选题评分框架.md`、`01-四题第一轮总报告.md`、`02-选题建议与评分矩阵.md`（七维评分 A 8.08 / B 7.40 / C 6.51 / D 5.33）、`04-选题终局与三天备赛总规划.md` |
| 05–18 | C 题主线 | `08-C题全面审计与修改纲领.md`、`09-C现状与数字对账.md`、`11-统一主线设计.md`、`12-三问各自最强方案.md`、`13-P2预训练判决实验.md`、`14-P3自适应与信息上界.md` |
| 21–32 | 第一轮优化 | `21-P3优化结果.md`、`22-P1a改进结果.md`、`31-AsterLink对标与差距清单.md`、`32-命题A与命题B.md` |
| 35–42 | 第二轮多角度优化 | `35-P1a-v2结果.md`、`36-P1b-v2结果.md`、`37-P2-v2结果.md`、`38-P3策略-v2结果.md`、`39-P3复核-v2结果.md`、`40-官方基准与模型阶梯.md`、`41-P1状态-v2结果.md`、`42-第二轮多角度优化对比.md` |
| 43–56 | 格式、对标、评审、合规 | `43-官方格式核对与图表重做.md`、`44-Modex数维杯流程逆向与对标.md`、`45-Modex逆向-工作流引擎.md`、`46-Modex逆向-技能与质检层.md`、`48-官网通知逐条核对与AIGC风险.md`、`50-两份查重报告差异分析.md`、`51-逐问复查与参数核对.md`、`52-整体测评与一等奖判定.md`、`54-备用稿与获奖论文对比评估.md`、`56-朱雀AIGC检测报告.md` |

> 编号 00/01/02/07/08 各有两份，是同一批次的分册（如 `07-C题进展与交接.md` 与 `07-数据包审计.md`），不是重复。45/46/47/49 原本也有重复，已分别改名到 51/52/53/54/55/56。

### `数维杯/` —— 官方规则与常备资料

| 子目录 | 内容 |
|---|---|
| `00_官网与规则/` | 2021 / 2025 / 2026 三套官方件：论文格式规范、提交流程、Word 模板、承诺书、LaTeX 模板（`demo.tex` + `swmcmthesis.cls/.cfg`）、`AnyMath专项奖与备赛笔记.md` |
| `01_往年赛题/` | 2021 国际赛 B/C/D 题题面 + 附件数据（xlsx） |
| `02_一等奖论文_参考/` | `一等奖论文写法提炼.md`（8.5 KB，结构级总结） |
| `03_实战演练/` | 2021 B 题（极端降水）完整演练 |
| `04_评分与复盘/` | `复盘_2021B.md`、`自主评分报告_2021B.md`、`评分细则_v1.md` |
| `05_模板与工具/` | `extract_pdf.py`、`fetch_ghcn.py`、`inspect_data.py`、`paper_profile.py`、`latex/`（中英双模板 + `build.ps1`） |
| `2026年第十二届…赛题/` | 本届 C 题原始题面与附件（与 `_swc2026/SWC2026_C/problem/` 同源） |
| `99_归档/` | 2021 B 题旧版工程 |
| `refs/official_standard.json` | 47.9 KB 的官方规范结构化版本 |

### `PRACTICE_2023B/` / `SHUWEI2025_A/` / `SHUWEI2026_C/` / `shuwei/`

- `PRACTICE_2023B/`：2023 数维杯 B 题（催化反应）完整练习，含 `problem/`、`code/`、`data/`、`figures/`、`tables/`。
- `SHUWEI2025_A/`：2025 秋季赛 A 题旧工程，`COMPARISON_2025A.md` 是与 12 篇一等奖论文的对标审计。
- `SHUWEI2026_C/`：2026 C 题的**早期副本**（`data/raw/` 已排除，剩 36 文件 / 2.3 MB），保留只为看演化；正式版本在 `_swc2026/SWC2026_C/`。
- `shuwei/`：2022–2023 年的抓取脚本与早期尝试（`_src/`、`_tmp2022/` 已排除）。

### 根文件

- `AGENTS.md`（15 KB）：工作区总纲，每次会话自动注入。**新会话先读这个。**
- `ISOLATION.md`（6.8 KB）：独立性与隔离性自证——证明这套流水线不依赖任何外部商业工作台，也不会泄漏到别的工作区。
- `README.md`：本仓库首页。
- `docs/`：本说明书三件。

---

## 二、被 `.gitignore` 排除的东西（以及为什么）

规则按块组织，每条都对应一个真实原因：

| 规则块 | 排除什么 | 为什么 |
|---|---|---|
| 亚太杯 | `APMCM*/`、`EXAM_2023C/`、`PRACTICE_2018A/` | 用户要求只收数维杯。这 7 个目录已物理移到 `E:\数学建模_apmcm\`（约 1.4 GB），规则保留是为了防止误拷回来 |
| 环境 | `.venv/`、`__pycache__/`、`*.py[cod]`、`*.pyd`、`*.so`、`*.dll`、`*.exe` | `数维杯/.venv` 单项就 493.5 MB / 16,796 文件；`.pyd` 147 MB 是 Modex 编译模块与 site-packages |
| LaTeX 中间件 | `*.aux`、`*.log`、`*.out`、`*.toc`、`*.fls`、`*.synctex.gz`、`*.blg`、`*.bbl`、`*.xdv`、`*.run.xml`、`verify.*` | 可由 `xelatex` 重建。注意 `main.toc` 也在此列，但 `code/add_pdf_outline.py` 需要它——复现脚本会先编译再生成大纲 |
| 二进制数据 | `*.npz`、`*.npy`、`*.pt`、`*.pth`、`*.ckpt`、`*.onnx`、`*.parquet`、`*.pkl`、`*.sqlite`、`*.pack`、`*.idx`、`*.bin` | `SWC2026_C/data` 611.8 MB 里 289 MB 是 `.npz` 特征缓存、3.1 MB 是模型权重。全部可由 `code/` 重跑生成（见 `docs/EXCLUDED_LARGE_FILES.md`） |
| 原始数据 | `cdata/`、`*/data/raw/`、`*/raw/`、`_downloads/`、`*.mp4`、`*.m4s`、`*.yuv`、`*.trc`、`*.mat`、`*.caj`、`*.bmp`、`*.rar`、`*.7z`、`*.tar*` | `cdata` 440.4 MB（EgoPro/EgoStandard 原始视频与 CSV）、`_downloads` 283.4 MB（6 个 GitHub 仓库快照）、`refs/contest-code` 73.2 MB（MATLAB/YUV 真题代码）。这些都是**从官方渠道重新下载**的，不该进仓库 |
| 训练临时 | `models/`、`shadow_anchor_*/`、`finalrep_r*/`、`code.bak_*/`、`_frozen_v1/`、`_superseded/`、`_figures_unused/`、`_unused/` | 代表点重训的 shadow 目录、三次重训的 `finalrep_r1..r3`、被 `quarantine_superseded.py` 隔离的旧产物 |
| 脚手架 | `_scratch/`、`_scratch_pandoc*`、`_pkgtest*/`、`_pkgfinal/`、`_verify_pkg/`、`_check_ws/`、`_venuecheck/`、`_pkit/`、`_tmp/`、`_pages/`、`_audit_pages/`、`_qa/`、`_bench/`、`_bench_txt/`、`_qprobe/`、`_algtest/`、`_preview/`、`_template2025/`、`_nmmcm/`、`_posts/`、`_ref2025/` | 一次性工作目录。`_pkit/paper/data/` 曾是 `SWC2026_C/data/` 的整份拷贝（`state.npz` 重复 12 份），是最大的重复来源 |
| 备份 | `*.bak*`、`*.broken_*`、`*.prev`、`*.rerun*` | `SWC2026_C` 根有 24 个 `main.tex.bak_*`（每个约 100 KB），都是压缩正文过程中的快照 |
| 体积文本 | `_modex_re_work/strings/`、`_swc2026/modex_re/*.strings.json`、`_swc2026/_bench_txt/` | Modex 逆向导出的全量字符串表（单文件几十 MB），结论已写进 `44/45/46` 三份报告 |
| 一次性探针 | `/_*.py`、`/_repo_tools/`、`/refs/contest-code/` | 根目录 7 个 `_*.py` 是当时的临时补丁；`_repo_tools/` 是本次建仓用的统计脚本 |
| `shuwei` 内部 | `shuwei/_src/`、`shuwei/_tmp*/` | `_src/` 里有三个嵌套 `.git`（第三方仓库快照），不能进主仓库 |
| 演练产物 | `数维杯/03_实战演练/**/03_results/`、`99_归档/**/results/`、`99_归档/**/audit/` | 2021 B 题演练的中间结果，可重跑 |
| 视频站抓取 | `_swc2026/bili-C/`、`_swc2026/bili-BV1Zzsv6fELo/`、`*/logs/**/*.png` | 74.2 + 66.8 MB 的 B 站视频与帧图，结论已写进报告 |
| 重复语料 | `SHUWEI2025_A/logs/_awards/` | 与 `award_corpus_2025/` 逐字节重复（约 90 MB） |
| 压缩包 | `*.zip`，但 `!**/CSWBMCM2634892fj.zip` 放行 | 支撑材料 zip 是交付件，必须进仓库。**否定规则必须写 `!**/xxx`，写 `!*/xxx` 不生效**（`git check-ignore -v` 验证过） |
| 备用稿 zip | `_swc2026/SWC2026_C_ALT_BACKUP/**/*.zip` | 备用稿目录里也有一份同名 zip，是重复的，只保留提交版 |
| 临时预览图 | `/_swc2026/_*.png`、`**/logs/*.png` | 根目录 61 张 `_diff*/_preview*` 截图与 `SWC2026_C/logs` 92 张逐页核对图，合计 24.3 MB，全是渲染核对产物，随时可重出 |
| 空错误文件 | `*.err` | 12 个 0 字节 stderr 占位，无信息量 |
| CSV 放行 | `!*.csv` | 上面的原始数据规则会连带排除小体积统计 CSV（如 `data/v2_video_features.csv` 8.2 MB 的体积统计、`record_split.csv`），这些是论文引用的，要留 |

---

## 三、验证规则是否生效

```powershell
cd 'E:\数学建模'
git check-ignore -v '_swc2026\SWC2026_C\CSWBMCM2634892fj.zip'   # 应输出 !**/ 那条（被放行）
git check-ignore -v '_swc2026\SWC2026_C\data\panel.npz'         # 应命中 *.npz
git check-ignore -v '数维杯\.venv'                               # 应命中 .venv/
git ls-files | Measure-Object -Line          # 跟踪面文件数（3,262）
```

---

## 四、磁盘占用对照

| 项 | 磁盘 | 进仓库 | 差额去向 |
|---|---|---|---|
| 总计 | ~3.8 GB / ~33k 文件 | **598.9 MB / 3,262 文件** | 虚拟环境、二进制缓存、脚手架（原始数据已删） |
| `_swc2026` | 1,825 MB | 213 MB | `cdata` 440 MB、`SWC2026_C/data` 588 MB（二进制）、`_scratch` 123 MB、B 站视频 141 MB |
| `数维杯` | 1,040 MB | 38 MB | `.venv` 493 MB、`_downloads` 283 MB、演练结果 |
| `refs` | 73 MB | 0.2 MB | `contest-code/`（MATLAB/YUV） |
| `SHUWEI2026_C` | 443 MB | 2.3 MB | `data/raw/` 441 MB（与 `cdata` 重复） |
