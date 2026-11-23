# 论文写作 skill 套件（项目级 · 数学建模工作区）

放在 `E:\数学建模\.agents\skills\` 下，与既有的 `mathmodeling` skill 同级；本项目 agent 自动发现。也可整目录复制到别的项目（`.dsh/skills/`、`.claude/skills/`、`.cursor/skills/`）直接复用。
源目录：`E:\论文复现\.dsh\skills\`。四个 skill 目录逐字一致（18 个文件 sha256 全等）；本 README 在拷贝后做了本地化（改了路径与分工说明）。

## 与 `mathmodeling` 的分工

| 谁 | 管什么 |
|---|---|
| `mathmodeling` | 竞赛流程与硬项：读题、建模、求解、数字对账、页数与格式合规、评审小队派单 |
| 本套件四个 skill | 手上活：中英互译、润色与去 AI 味、图型与图注、结果段与审稿式挑错 |

两者不重叠：`mathmodeling/writing.md` 定的是**结构**（摘要四段式、数字配额、压页），本套件管的是**句子与图表本身**。写摘要先按 `writing.md` 定骨架，再用 `paper-language-pass` 过语言。

## 来源与改编说明

场景划分与「输出契约 + 反乱改阈值」的思路来自 [Leey21/awesome-ai-research-writing](https://github.com/Leey21/awesome-ai-research-writing)（★3.6 万）。

**该仓库没有 LICENSE**（GitHub `/license` 返回 404），因此本目录是**重写改编**，不逐字复制其 prompt 文本：保留的是结构（按论文阶段切分、强制输出契约、原文达标就放行），文案、约束与验收清单是重写的，并修掉了上游的两处缺陷（`中转中-word` 里重复的「3.」编号；76 词黑名单混入的分词残留如 Ador / Bear / Engage / Innovate / Integrate / Originates / Inscription）。

若要对外分发本套件，先确认上游许可；本套件自身许可见项目根目录的 LICENSE（没有就补一个）。

## 四个 skill

| skill | 什么时候触发 | 载体 |
|---|---|---|
| `paper-cn2en-draft` | 中文草稿→英文正文；英文 LaTeX→中文速读 | LaTeX / Word |
| `paper-language-pass` | 润色、±5–15 词微调、逻辑红线检查、去 AI 味 | LaTeX / Word |
| `paper-figures-captions` | 方法架构图（文生图 prompt）、实验图型选择、图/表标题 | 通用 |
| `paper-results-review` | Excel/CSV→结果分析段落；PDF→审稿报告与改稿策略 | LaTeX / 通用 |

四个入口互不依赖，可单独拿走一个目录使用。

## 维护纪律

1. 每个 `SKILL.md` 各带一段「输出契约」，措辞必须一致。这是**有意的重复**，为的是每个 skill 可单独迁移；改契约就四处同改。
2. 每条约束必须对应一条验收项。写不出验收项的约束是口号，删掉它。
3. skill 里不放具体论文数据、机构名、投稿目标——那是每次调用的输入。
4. 上游「模型选择」一节不进 skill：那是时间快照（Claude Fable 5 / Gemini-3.7-flash / qwen3.8-max 这类命名随榜单漂移），选型按当期榜单自己定。