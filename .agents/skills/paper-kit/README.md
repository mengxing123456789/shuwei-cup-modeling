# paper-kit — 本机论文质检工具链

一套纯本机、可离线跑的论文检查与导出工具。**不依赖任何外部软件安装**，只依赖本机
`E:\Mini\envs\mathmodel`（Python 3.11，含 numpy / pandas / pymupdf / python-docx）。

## 来源

`tools\` 下的 27 个脚本与 3 类数据资产（`journal_registry` / `docx_style_profiles` /
`templates` / `prompts` / `pipelines.json`）原本是某个商业论文软件里的明文部分。
它们在该软件里是**脱离主程序也能独立运行**的普通 Python 脚本，因此被复制出来、
补齐缺失的依赖、并把所有指向原安装目录与产品名的标识换成中性名。

**原始出处已不再需要**：本目录里的东西自包含，那个软件卸载与否都不影响运行。

## 改造点清单（与原版逐项对照）

### 自建的两个替代模块

原版里这些脚本 import 两个只存在于原软件运行时的模块。本目录提供纯本机实现：

| 模块 | 替代了什么 | 实现要点 |
|---|---|---|
| `tools\trusted_gateway_config.py` | 原版的签名网关配置解析器 | 地址优先级：`snapshot` dict → `VISION_BASE_URL` > `OPENAI_BASE_URL` > `EDITOR_AI_BASE_URL` > `GPT_IMAGE_BASE_URL` → `https://api.openai.com`。`_join()` 自动避免 `/v1/v1`。`backend_loopback_url()` 只放行 `http://127.0.0.1` / `localhost` / `[::1]`，拒绝带 userinfo/query/fragment 的地址 |
| `tools\docx_text.py` | 原版的 `read_markdown()` | UTF-8 → UTF-8-SIG → GB18030 依次解码，全失败抛 `DocumentEncodingError`（不静默乱码） |

### 删掉的 3 个脚本

它们的功能依赖原软件的后端进程，脱离后端无法运行，且逻辑里全是旧产品的队列/票据机制：

| 脚本 | 原本干什么 | 为什么删 |
|---|---|---|
| `run_compute_remote.py` | 把求解任务甩到用户自己的服务器上跑 | 靠一次性令牌与私有后端通信，无后端即死 |
| `run_with_keys.py` | 带平台凭据跑命令（用户凭据不落地） | 同上，凭据由后端注入 |
| `skill_instruction_guard.py` | PreToolUse 守卫：防用旧版技能、防覆盖上游产物 | 守卫对象是原软件的技能目录结构，本机不存在 |

### 删掉的 `asar\`

原软件的 Electron 主进程明文（46 个文件），纯取证留档，对使用无价值，且本身是原产品代码。

### 全量去品牌化

脚本与数据里的所有标识都换成了中性名：schema 前缀统一为 `paperkit.survey.*`；
问卷渠道名简化为 `hub` / `web`；环境变量统一 `PAPERKIT_*` 前缀；HTTP 头、UA 串、
multipart 边界、字节码标记也一并改名。**目标：本目录里不出现任何指向原安装目录或产品名的字样。**

**唯一被手工修回的位置**：`tools\venue_submission_check.py:74` 的 `_AI_NAME_RE`。
那是**要检测 AI 痕迹的关键词表**，原本列了各家模型名。批量替换把其中一项换成了 `paperkit`，
语义就反了（工具会把自己名字当成 AI 痕迹去报）。已改回中性模型名（`notebooklm` / `perplexity`）。

## 目录

| 目录 | 内容 |
|---|---|
| `tools\` | 27 个 Python 脚本 + `run_tool.py` 统一入口 + 2 个自建模块 |
| `tools\journal_registry\families.json` | 10 家期刊/会议投稿格式，规则带 `quote` + `source_url` + `accessed` |
| `tools\docx_style_profiles\` | 13 份 DOCX 版式档案 + `covers\` 封面素材 |
| `templates\` | 9 份科研流程模板 |
| `prompts\` | 8 份写作提示词 |
| `pipelines.json` | 40 套竞赛/论文流水线的步骤定义 |

## 实测基线（2026-11-18，本机 mathmodel python 3.11.18）

- **27 个脚本 + `run_tool.py` 全部 `--help` exit=0**（`count_chapter_words.py` 无参数时 exit=1 并打印用法，属正常）。
- `count_chapter_words.py templates\PAPER_PLAN_TEMPLATE.md` → `TOTAL APPROX_WORDS=128 CHAR_NO_SPACES=800 CHAR_WITH_SPACES=948 CJK_CHARS=0 NON_CJK_WORDS=128 EN_WORDS=108` + 6 个分章行。
- 三个 `*_vision_check.py` 接通本机 magpie 网关（`http://127.0.0.1:3425/v1`）→ `PASS` / `CACHED_PASS` exit=0。
- `venue_submission_check.py` 对数维杯 LaTeX 骨架（8 页）→ `1 项要你处理，3 项提醒，3 项通过，1 项不适用`。

## 已知边界

- `markdown_utils.pyc` 只有字节码，magic `a70d0d0a` 只匹配 Python 3.11。换 3.12 会 `bad magic number`。
- `survey_import.py` 的 `pyreadstat` 依赖是可选的（只读 SPSS `.sav` 才需要）。
- `screenshot_capture.py` 需要 Electron 运行环境，本机无独立 Electron 时走降级退出码 2。
- `gpt_image.py` 需要 `GPT_IMAGE_API_KEY`（可用本机 magpie 网关的 key 顶替）。
