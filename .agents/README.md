# `.agents` — 技能根

存放本工作区的全部技能。技能是「可被模型按需加载的指令包」，不是库——加载后改变的是模型的行为，不是提供函数调用。

## 目录

```
.agents/
  skills/
    mathmodeling/          主力：八步二十门流水线（1.5 MB）
    paper-kit/             42 个离线质检脚本（2.0 MB）
    paper-figures-captions/ 图型选择与 caption 写法
    paper-language-pass/   最小干预润色
    paper-cn2en-draft/     中文草稿 → 英文学术段落
    paper-results-review/  结果段落 + 审稿视角
    README.md              六技能清单与 mmkit 模块说明
```

## 为什么放在 `.agents/` 而不是 `skills/`

这是跨 agent 的约定目录名（Codex / Claude Code / Cursor 都认）。放在这里，换 agent 工具时不用改路径。

`mmkit` 的 `workspace_root()` 就是靠「向上找带 `.agents/skills` 的那一级」来定位工作区根的——**这个目录的存在本身就是定位锚点**，删了它所有脚本都找不到工作区。

## 技能怎么写

每个技能一个目录，必须有 `SKILL.md`：

```markdown
---
name: <技能名，与目录名一致>
description: <一句话：什么时候该用我。这句话决定模型能不能选到我>
---

# 正文
```

`description` 是唯一的触发条件，必须写「当用户要 X 时使用」，不要写「这个技能提供了 Y 功能」——后者模型匹配不上。

## 三个纪律

1. **技能正文里的判据必须能被执行。** 不写「应该注意格式」，写「页数 ≤25、页眉含队伍号、字号 ≥6 pt」。
2. **踩过的坑写进技能，不写进脑子。** 每个 FAIL 过两次的判据，正文里要有一句「为什么加这条」。
3. **改判据要升 schema。** `pipeline.py` 的 `STATE_SCHEMA` 不升，已 done 的步骤会被整步跳过，新加的门等于不存在。
