# 方法架构图：绘图提示词

## 为什么必须钉死约束

直接说「画一个基于注意力的多模态融合框架图」，产出通常是：渐变背景、3D 立体块、假英文标签、箭头随意连、模块数量不对。信息图的价值在于**可读的拓扑**，不在于视觉炫技。所以提示词要把造型、连线、分区、风格四个维度都写死。

## 中文版模板（给绘图模型，如 Nano Banana）

```text
# 任务
画一张学术论文用的方法架构图，扁平矢量风格，白底，无渐变、无 3D 阴影、无照片元素。

# 画布
横向 16:9，留白充足，模块之间间距一致。

# 分区（从左到右四个竖直区块，区块之间用浅灰虚线分隔并标注标题）
1. 输入 Input：[INPUT_DESC]
2. 编码 Encoder：[ENCODER_DESC]
3. 融合 Fusion：[FUSION_DESC]
4. 输出 Output：[OUTPUT_DESC]

# 模块造型
- 数据张量：细长矩形，标注形状如 [B, N, D]
- 网络层/模块：圆角矩形，标注模块名
- 操作：圆形或菱形小图标（⊕ 表示逐元素相加，⊗ 表示逐元素相乘）
- 可学习参数：矩形右下角加小三角标记

# 箭头语义（三种线型必须视觉可分）
- 实线箭头：前向数据流
- 虚线箭头：监督信号 / 标签输入
- 点划线箭头：损失回传

# 配色
最多三色 + 灰阶。同一类模块同色。文字一律深灰 #333，不用彩色字。

# 文字
所有标签用英文，字号统一，不出现乱码或生造词。不要在图内写句子，只写名词短语。

# 禁止
不要装饰性背景、不要发光效果、不要拟物图标、不要超过三层的立体感。
```

## 英文版模板（给 drawio / diagram 工具 / 国际模型）

```text
# Task
Draw a flat-vector architecture diagram for an academic paper. White background,
no gradients, no 3D shading, no photographic elements.

# Canvas
16:9 landscape, generous margins, uniform spacing between blocks.

# Regions (four vertical columns, left to right; separate with light grey dashed
# dividers and a short region title above each)
1. Input: [INPUT_DESC]
2. Encoder: [ENCODER_DESC]
3. Fusion: [FUSION_DESC]
4. Output: [OUTPUT_DESC]

# Node shapes
- Tensors: thin rectangles labelled with shape, e.g. [B, N, D]
- Layers/modules: rounded rectangles labelled with the module name
- Operations: small circles/diamonds (⊕ element-wise add, ⊗ element-wise multiply)
- Learnable parameters: small triangle marker at the bottom-right corner

# Edge semantics (three visually distinct styles)
- Solid arrow: forward data flow
- Dashed arrow: supervision signal / label input
- Dash-dot arrow: loss backpropagation

# Colour
At most three colours plus greys. Same module class = same colour.
All text dark grey #333, never coloured.

# Typography
English labels only, uniform font size, no invented words, noun phrases only (no sentences).

# Forbidden
Decorative backgrounds, glow effects, skeuomorphic icons, more than two levels of depth.
```

## 提示词里最容易漏、漏了就废的四项

1. **张量形状标注**：没有 `[B, N, D]` 这类标注，审稿人无法确认维度是否对齐。
2. **箭头语义**：三种线型不区分，读者会把监督信号当成数据流。
3. **同类同色**：不写这句，模型会给每个模块随机配色，图看起来像散装。
4. **禁止句内文字**：模型一旦在图里写句子，必然出现语法错误或生造词。

## 出图之后必查（人工，别跳过）

- [ ] 模块数量与正文的方法描述完全一致（多一个少一个都是硬伤）
- [ ] 每个标签拼写正确、术语与正文一致
- [ ] 箭头方向对得上数据流方向（反向箭头是最常见的致命错）
- [ ] 张量形状与正文公式里的维度一致
- [ ] 缩小到单栏宽度仍可读（很多图在 100% 下好看，缩到 8cm 就糊了）

## 替代路线：直接进 drawio

若模型出图反复不对，改成让 `diagram_apply` 按上面的模块清单与箭头语义建图，再手调位置。矢量、可改、字体统一，通常比再抽十次卡更快。