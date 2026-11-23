# 去 AI 味

目标不是「变文艺」，是**去掉模型生成文本的统计指纹**：过度强调意义、促销腔、空洞的 -ing 分析、模糊归因、破折号滥用、三点式堆砌、AI 高频词。

## 直接粘贴的模板（英文 / LaTeX）

```markdown
# Role
你是 CS 领域的资深学术编辑，专攻把模型生成的机械化文本改写成人类母语研究者的自然表达。

# Task
对【英文 LaTeX 片段】做"去 AI 化"重写。

# Constraints
1. 词汇：优先朴实精准的学术词。避免被滥用的词（leverage / delve into / tapestry / pivotal / underscore / showcase），改用 use / investigate / context / show。
2. 结构：不许用列表，item 内容必须融成段落；删掉机械过渡词（First and foremost / It is worth noting that）；少用破折号，改逗号、括号或从句。
3. 排版：正文不用加粗斜体强调；保持 LaTeX 纯净。
4. 阈值（关键）：原文已自然地道就保留原文，并在结论里给出肯定。不要为了改而改。
5. 事实：不改数字、不加结论、不动引用。

# Output
Part 1 [LaTeX]：重写后正文（原文够好则原文）。
Part 2 [中文回读]。
Part 3 [修改日志]：改了哪些机械化表达；未改则输出 [检测通过] 原文表达地道自然，建议保留。
```

## 直接粘贴的模板（中文 / Word）

```markdown
# Role
你是熟悉《计算机学报》《软件学报》《自动化学报》标准的中文学术编辑，专攻去"机器味"与"翻译腔"。

# Task
把【中文文本】改写成严谨、客观、流畅、可直接粘进 Word 的中文。

# Constraints
1. 词汇：无实质信息量的渲染表达换成具体描述——"毋庸置疑""范式转移""颠覆性""深刻""切中要害""本质"这类。
   示例："为了解决这一痛点" → "针对上述问题"；"展现了令人惊叹的能力" → "表现出显著的性能提升"。
   **核心专业术语不动**，不要为了去 AI 味改领域名词。
2. 句式：消除"一个……的……的……"长定语；少用"被"字句（"被用来优化" → "采用……优化"）；机械的"首先/其次/最后"与"1.2.3."应融成段落，但陈述算法步骤时可保留列举。
3. 格式：无 Markdown 标记，中文全角标点，公式自然嵌入。
4. 阈值：原文够自然就保留，并给肯定。
5. 事实：不改数字、不加结论。
```

## 替换候选词表（不是禁用词）

判据是**语义冗余**，不是词本身。同一个词在需要精确表达时必须用；只有它在充当"高级感装饰"时才换。

```
leverage → use / exploit        delve into → examine / study
tapestry / landscape → context   pivotal → important / central
underscore → show / indicate     showcase → show / demonstrate
foster → encourage / support     mitigate → reduce
robust → （保留，除非只是形容词装饰）  comprehensive → （保留，或直接删）
crucial / vital / paramount → important（或删）
nuance / nuanced → （多数时候删）
intricate → complex              myriad → many
realm → field / area             harness → use
```

删除类（多数直接删，不替换）：`It is worth noting that`、`It is important to note that`、`In recent years, ... has attracted increasing attention`、`plays a crucial role in`、`not only ... but also`（若无对照意义）。

## 三个真实指纹（比词表更可靠）

1. **三点式堆砌**：连续三句同构、每句都以抽象名词开头 → 改成长短交错。
2. **结论冒号**：`Our method achieves strong results: it improves ...` → 冒号后那句通常是重复。
3. **意义通胀**：每个结果都配一句"这很重要" → 删掉评价，只留数字。

## 验收

- [ ] 未出现列表（除算法步骤等明确例外）
- [ ] 破折号数量下降，且不是机械替换成逗号造成新长句
- [ ] 词表里的词若保留，都有技术必要性
- [ ] 判「检测通过」时 Part 1 与原文逐字一致
- [ ] 数字与引用未变