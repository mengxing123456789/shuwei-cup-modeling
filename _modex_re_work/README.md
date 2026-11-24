# _modex_re_work — Modex 商业平台逆向

> modex（一个商业建模工作台）的 JS bundle 解包、接口清单、提示词模板、流程状态机转储。**本仓库的八步二十门流水线，设计上直接受益于这里的分析。**

## 三份笔记（在 `../_swc2026/`）

| 文件 | 大小 | 内容 |
| --- | --- | --- |
| `44-Modex数维杯流程逆向与对标.md` | 13.9 KB | modex 打数维杯的完整流程，与我们的做法逐条对照 |
| `45-Modex逆向-工作流引擎.md` | 63.7 KB | 状态机、节点类型、变量传递、重试策略 |
| `46-Modex逆向-技能与质检层.md` | 102.4 KB | 它的「技能」怎么定义、质检怎么判、提示词怎么拼 |

## 这个目录里是什么

```
_modex_re_work/
  strings/                 JS bundle 里的字符串表转储
  zlib/  zlib2/  zlib3/    解压后的 chunk
  ctx_*.js.txt             几个关键 bundle 的上下文片段（main / NewWorkflow / WorkflowDetail / AccountStepModels）
  aris_db_schema.txt       15,614 B —— 它的数据库表结构（最有用的一份）
  cjk_simulated_all.txt    24,536 B —— 中文提示词模板全量
  cjk_simulated_short.txt  6,074 B —— 精简版
  cjk_paper_modeling_quality.txt  344 B —— 论文建模质量判据
  batch2.py  batch_strings.py  cjk_all.py  crit.py  ctx.py  dis_pyd.py  dump_cards.py
```

## 三个可复用的观察

1. **它把「写论文」拆成有类型的状态机节点**，不是一次性长提示词。这直接对应我们的 `s1`–`s8` 八步。
2. **它的质检层是独立节点**，输出结构化判据（`cjk_paper_modeling_quality.txt` 就是它的判据原文）。这对应我们的 20 道门——**门必须是可机器判的**，不能是「感觉写得不错」。
3. **它的中文提示词模板做了分层**（系统层 / 任务层 / 格式层 / 反例层），`cjk_simulated_all.txt` 里能看出每层的作用。我们的 `squads/main/*.md` 与 `squads/review/*.md` 是同一个思路。

## 注意

`strings/` 与 `zlib*/` 体积较大且已被 `.gitignore` 的 `_modex_re_work/strings/` 规则排除；仓库里只留分析脚本与提取出的文本。

<!-- path-note -->
