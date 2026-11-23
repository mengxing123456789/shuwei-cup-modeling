#!/usr/bin/env python3
"""通用界面截图工具 — 用 Electron 内嵌 Chromium 给运行中的网页截图。

供 dev-report(报告界面截图)、软著/专利材料等场景复用。契约稳定：
输入 URL/HTML + 输出 PNG 路径，输出真实界面截图（离线，不下载浏览器）。

用法:
  # 探测能力（Electron 是否可用）。可用退出 0，不可用退出 2（调用方据此降级为占位符）
  python screenshot_capture.py --check

  # 单张截图(PNG)
  python screenshot_capture.py --url http://127.0.0.1:19001/ --out figures/shot_home.png

  # 单张出「矢量 PDF」(HTML 流程图 → 论文 \includegraphics 直接引)：out 用 .pdf 即自动走 pdf，
  # 也可显式 --format pdf。等效 drawio --crop：单页、无白边、真矢量文字。
  python screenshot_capture.py --file figures/fig_roadmap.html --out figures/fig_roadmap.pdf --format pdf

  # 元素级几何自检（只测量不出图，供 HTML 流程图自修复循环用）：
  #   量 .fig 内文字块，报「文字溢出被裁 / 越出画布边界 / 文字块重叠」。退出码 0=干净 1=有问题 2=无法检查。
  python screenshot_capture.py --geom-check figures/fig_flow_q1.html            # 无公式的图
  python screenshot_capture.py --geom-check figures/fig_flow_q1.html --render-math  # 含公式的图

  # 批量（推荐）：--config 指向一个 JSON
  python screenshot_capture.py --config shots.json

shots.json 结构:
  {
    "viewport": {"width": 1280, "height": 800},
    "targets": [
      {"url": "http://127.0.0.1:19001/",          "out": "figures/shot_home.png", "waitMs": 1200},
      {"url": "http://127.0.0.1:19001/login",      "out": "figures/shot_login.png", "waitForSelector": ".login-form"},
      {"file": "D:/proj/code/frontend/index.html", "out": "figures/shot_index.png", "fullPage": true},
      {"file": "D:/proj/figures/fig_flow.html",    "out": "figures/fig_flow.pdf",   "format": "pdf"},
      {"file": "D:/proj/figures/fig_algo.html",    "out": "figures/fig_algo.pdf",   "format": "pdf", "renderMath": true}
    ]
  }

renderMath:true → 截图前注入 KaTeX，把 HTML 里的 \(...\)/\[...\]/$$ 渲染成真公式（含公式的
流程/算法/架构图用）。素材缺失时自动降级（图仍出，公式不渲染），不阻断。

⛔ format:"pdf"（或 out 以 .pdf 结尾）→ Electron 原生 printToPDF 出矢量 PDF：量内容真实像素，
   页面尺寸设成刚好等于内容，单页无白边、文字可选可搜、无限放大不糊。fullPage 仅对 png 有意义。

退出码: 0=全部成功  1=部分/全部截图失败  2=Electron 不可用(应降级)  3=参数/致命错误

⛔ 全标准库实现，与项目其它 tools 一致，不引第三方。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# 单次 Electron 调用总超时（秒）：兜底防子进程卡死
_TOTAL_TIMEOUT = 180

# ===== 科研规范阈值（--norm-check 用）=====
# ⛔ 这三条是 geom-check 的盲区：它只量图内部相对关系，量不到"缩进论文后还看不看得清"。
#    实测依据：真实工作区 6 张图 5 张栽在这里（最糟一张字缩到 4.5pt，眼睛只看到灰块）。
MIN_FONT_PT = 8.0        # 最终印刷可读下限；低于此字形分辨困难
MAX_PAGE_SHARE = 0.60    # 单图占正文区高度上限；超过就挤走正文、浮动错位
# 模块数上限（= 最外层文字块，节点带副标题算 1 个）。
# ⛔ 标定依据：正常设计 = 最多 6 阶段标签 + 8 模块 ≈ 14；实测达标图 7~16。
#    用户报"一坨"的那张是 5 标签 + 20 框 = 25，故闸设 22 才兜得住那一类。
# ⛔ 这条是兜底，判别力弱于字号/占页两项（好坏图的块数区间有重叠）——真正抓问题靠前两项。
MAX_TEXT_BLOCKS = 22
MAX_FIG_H_IN = 8.2       # = md_to_docx 的 _DEFAULT_IMAGE_MAX_H_IN，高度受限时的封顶

# 技术路线总览是“认知导航”，不能只用字号和物理占页判断。真实失败样本在字号合格时仍有
# 32/37 个模块、多个粗黑焦点和长段文字，用户无法快速识别主路径。
ROADMAP_MAX_NODES = 18
ROADMAP_MAX_TEXT_BLOCKS = 26
ROADMAP_MAX_TOTAL_CHARS = 560
ROADMAP_MAX_NODE_CHARS = 64
ROADMAP_MAX_FOCUS = 1
ROADMAP_MAX_DARK_FILL = 0.08
ROADMAP_MAX_THICK_SHARE = 0.20

# ===== 零灰阈值（《设计规范 0.2 节》同口径）=====
# ⛔ 实测依据：12 张结构/形态/排版全不同的图，因共用同一套灰被用户一眼指认"同一套系统"。
#    中间灰 = 低彩度 + 中等明度。近黑/近白不算（那是正常黑白字与底）。
_GRAY_MAX_CHROMA = 18    # max(R,G,B)-min(R,G,B) ≤ 此值 = 近中性
_GRAY_LUM_LO = 45        # 明度下界：≤45 视作纯黑（#000/#111/#1a1a1a/#2b2b2b 放行）
_GRAY_LUM_HI = 243       # 明度上界：≥243 视作纯白


def _scan_repeating_gradients(html_path):
    """扫 repeating-linear/radial/conic-gradient：Chromium 打印成 PDF 时，这种底纹铺在高一点的窄条上
    会被切成一块块，只剩每段一小截（10-12 实测：路线图左侧斜纹泳道条只画出最底下一截，而且是糊的）。
    同样的斜纹改用带 background-size 的平铺 linear-gradient、SVG 底纹，或直接用 double 边框，都能完整出图。
    """
    try:
        txt = Path(html_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return sorted({m.group(0).lower() for m in
                   re.finditer(r"repeating-(?:linear|radial|conic)-gradient", txt, re.I)})


def _scan_italics(html_path):
    """扫斜体：中文无真斜体，浏览器只能伪斜（正体强行倾斜），学术排版不用，
    且是一眼可辨的系统特征。见《设计规范 0 节第 8.1 条》。

    ⛔ 三种来源都要抓：font-style:italic/oblique、<i> 标签、<em> 标签。
       但若同文件已有 `font-style:normal !important` 兜底，则 <i>/<em> 不会真斜 → 放行标签，
       只报显式声明的 italic。
    """
    try:
        txt = Path(html_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    hits = []
    for m in re.finditer(r"font-style\s*:\s*(italic|oblique)", txt, re.I):
        hits.append("font-style:" + m.group(1).lower())
    # ⛔ font 简写也能设斜体：`font:italic 14px serif`（对抗测试抓出的漏洞）。
    #    只匹配 font 属性本身，不能误伤 font-family/font-size/font-weight。
    for m in re.finditer(r"(?<![\w-])font\s*:\s*[^;{}]*?\b(italic|oblique)\b", txt, re.I):
        hits.append("font 简写:" + m.group(1).lower())
    guarded = re.search(r"font-style\s*:\s*normal\s*!important", txt, re.I)
    if not guarded:
        for tag in ("i", "em"):
            n = len(re.findall(r"<%s[\s>]" % tag, txt, re.I))
            if n:
                hits.append("<%s> ×%d（无 font-style:normal 兜底）" % (tag, n))
    return hits


def _is_mid_gray(r, g, b):
    chroma = max(r, g, b) - min(r, g, b)
    lum = (r * 299 + g * 587 + b * 114) // 1000
    return chroma <= _GRAY_MAX_CHROMA and _GRAY_LUM_LO < lum < _GRAY_LUM_HI


def _hsl_to_rgb(h, s, ll):
    """h:0-360 s,l:0-1 → (r,g,b) 0-255。用于把 hsl() 换算后套同一判据。"""
    import colorsys
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, ll, s)
    return round(r * 255), round(g * 255), round(b * 255)


# ⛔ CSS 命名灰：纯 hex/hsl/rgb 扫描完全漏掉它们（对抗测试实测被绕过）。
#    只列真正落在"中间灰"区间的（black/white 不在此列）。
_NAMED_GRAYS = {
    "gray": (128, 128, 128), "grey": (128, 128, 128),
    "darkgray": (169, 169, 169), "darkgrey": (169, 169, 169),
    "dimgray": (105, 105, 105), "dimgrey": (105, 105, 105),
    "lightgray": (211, 211, 211), "lightgrey": (211, 211, 211),
    "silver": (192, 192, 192), "gainsboro": (220, 220, 220),
    "whitesmoke": (245, 245, 245), "lightslategray": (119, 136, 153),
    "slategray": (112, 128, 144), "darkslategray": (47, 79, 79),
}


def _scan_mid_grays(html_path):
    """扫 HTML 源码里的颜色字面量，返回 {颜色: 出现次数} 的中间灰表。

    ⛔ 五类写法都要扫，缺一即成绕过口子（前四类都真漏过 / 被对抗测试抓出）：
       ① 十六进制：3 位与 6 位都要（只认 6 位会漏 #777/#fff）
       ② hsl()：低饱和 hsl 就是灰（4 个模板全用 hsl，曾被误报为"零灰"）
          ⛔ 逗号语法与【空格语法 hsl(0 0% 60%)】都要认
       ③ rgb()：整数形式与【百分比形式 rgb(60%,60%,60%)】都要认
       ④ CSS 命名颜色：gray/silver/gainsboro/dimgray… 纯正则扫 hex 完全看不见
    ⛔ 只看源码不看渲染：CSS 变量制下颜色只在 :root 出现一次，够用且零依赖。
    """
    import collections
    try:
        txt = Path(html_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    found = collections.Counter()

    # ① 十六进制
    for m in re.finditer(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", txt):
        h = m.group(1).lower()
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        if _is_mid_gray(r, g, b):
            found[f"#{h}"] += 1

    # ② hsl()：逗号或空格分隔，S/L 带 %（h 允许负数与小数、deg 后缀）
    _num = r"[-+]?[\d.]+"
    hsl_re = (r"hsla?\(\s*(%s)(?:deg)?\s*[,\s]\s*(%s)%%\s*[,\s]\s*(%s)%%"
              % (_num, _num, _num))
    for m in re.finditer(hsl_re, txt, re.I):
        try:
            hh, ss, lll = (float(m.group(i)) for i in (1, 2, 3))
        except ValueError:
            continue
        r, g, b = _hsl_to_rgb(hh, ss / 100, lll / 100)
        if _is_mid_gray(r, g, b):
            found["hsl(%g,%g%%,%g%%)" % (hh, ss, lll)] += 1

    # ③ rgb()：整数或百分比，逗号或空格分隔
    rgb_re = (r"rgba?\(\s*(%s)(%%?)\s*[,\s]\s*(%s)(%%?)\s*[,\s]\s*(%s)(%%?)"
              % (_num, _num, _num))
    for m in re.finditer(rgb_re, txt, re.I):
        try:
            vals = []
            for vi, pi in ((1, 2), (3, 4), (5, 6)):
                v = float(m.group(vi))
                vals.append(v * 255 / 100 if m.group(pi) == "%" else v)
            r, g, b = (max(0, min(255, round(v))) for v in vals)
        except ValueError:
            continue
        if _is_mid_gray(r, g, b):
            found["rgb(%d,%d,%d)" % (r, g, b)] += 1

    # ④ CSS 命名灰（词边界，避免匹配到 --gray-bg 这类变量名的一部分）
    for name, (r, g, b) in _NAMED_GRAYS.items():
        n = len(re.findall(r"(?<![\w-])%s(?![\w-])" % name, txt, re.I))
        if n and _is_mid_gray(r, g, b):
            found[name] += n

    return dict(found)


# ===== 内容体检（--norm-check 第五项）=====
# ⛔ 前四项管「看不看得清」，这项管「读不读得通」。实测 12 张真实图：截断 39 处、
#    元内容 18 处、公式剥离留空 4 处 —— 全是从工作区 .md 裸抽文字带进来的。
#
#
# 公式占位符：探针把每棵 .katex 子树换成这个私用区字符再回传。
# ⛔ 必须与 desktop/capture.js 的 maskedText() 保持一致（那边写作字面 \uE000）。
#    用私用区字符而非 "[MATH]" 之类：正文绝不可能出现它，零误伤。
_MASK = "\uE000"
#
# ① 元内容：讲【报告自身】的修订记录/编号台账，不是模型方法。正式论文里读者看不懂
#    「修正项 F1」「HC-01..HC-08」指什么，因为它们只在中间产物里有定义。
_META_WORDS = (
    "METHOD_CLAIMS", "MODELING_REPORT", "PARAMS_RAW", "RESULTS.md",
    "修正项", "硬约束清单", "结果约束清单", "约束清单", "符号表",
    "参数口径表", "输入口径", "台账", "对账", "自检", "兜底", "回填",
    "书写口径", "版本记录", "修订记录", "变更记录",
)
# ② 工程语汇：与 skills/shared-scripts/ai_tell_check.py 的 BANNED 同源。
#    ⛔ 两处各留一份而不 import：本文件在 tools/、那个在 skills/shared-scripts/
#    （运行时还会被复制进 _utils/），生命周期不同，跨目录 import 必碎。
#    改词时【两处都要改】。
_JARGON_WORDS = (
    "口径", "闭环", "链路", "落地", "打通", "拉齐", "颗粒度", "抓手",
    "赋能", "上游", "下游", "复用", "维度上",
)
# ②′ 学科里的正当搭配不算元内容 / 工程语汇（上游供应商、下游客户、闭环控制、通信链路、频率复用、统计口径、
#    设备台账、设备自检、土壤颗粒度……）：与 skills/shared-scripts/ai_tell_check.py 的 DOMAIN_TERMS 同源，
#    ⛔ 改词时【两处都要改】。那边只在有写作档案的学术工作区生效；图里的字短、搭配写得很死，这里一律放行
#    （10-21 复查：按用户数据画的供应链、控制、通信流程图被整张拦下）。
#    ⛔ 不收「修正项」：图里的“修正项 F1：……”是建模报告的自述，照旧拦。
_DOMAIN_TERMS = (
    r"闭环(?:控制|系统|反馈|传递|增益|极点|稳定|辨识|调节|响应|带宽)|开环[^，。；\n]{0,8}闭环|(?:反馈|控制)闭环",
    r"(?:通信|无线|有线|传输|光纤?|卫星|数据|上行|下行|物理|逻辑|网络|信号)链路|链路(?:预算|层|质量|容量|状态|损耗|增益|聚合|余量)",
    r"(?:频率|时分|频分|码分|波分|空分|正交频分|代码|软件|模块|资源|空间)复用|复用(?:器|率|技术|因子|距离|模式)",
    r"(?:统计|核算|计算|测算|调查|指标|统一|不同|一致)口径|口径(?:一致|不一|调整|差异|统一)",
    r"上游(?:河段|河道|水库|来水|流域|地区|区域|企业|产业|行业|供应商|厂商|原料|基因|序列|启动子|调控|区段|站)"
    r"|(?:产业链|供应链|河流|基因)上游|上下游",
    r"下游(?:河段|河道|水位|流域|地区|区域|企业|产业|行业|客户|需求|市场|基因|序列|靶标|任务|应用|站)"
    r"|(?:产业链|供应链|河流|基因)下游|上下游",
    r"(?:管理|设备|资产|安全|环境|排污|物资)台账|台账(?:管理|制度|记录)",
    r"(?:设备|上电|开机|系统|硬件|内置|周期)自检|自检(?:电路|程序|功能|模块|测试)",
    r"颗粒度(?:分布|分析|测定|组成)|(?:土壤|粉体|颗粒)颗粒度",
)
_DOMAIN_RE = re.compile("|".join("(?:%s)" % p for p in _DOMAIN_TERMS))
# ③ 内部标记符号 + Markdown 残留：抄文字时把源码符号一起搬进了图。
_MARK_RE = re.compile(r"[⛔✅❌⚠]|\bHC-\d|\bA\d+\s*[:：]?\s*$")
_MD_RESIDUE_RE = re.compile(r"`|\*\*|^\s*[-*+]\s|^#{1,6}\s")
# 路径/代码标识符：实测抓到工作区目录名 `comp-paper-zh` 被当成「本文重点」画进图，
# 与早先 `Overlap` 泄漏同源 —— 从工作区抽文字时把路径/变量名当成了内容。
# ⛔ 判据要求【两段各≥2 个小写字母】以 -/_ 相连，才能避开正当写法：
#    NSGA-II（大写）、A-B 混填（单字符）、x_1（在 _MASK 内已遮蔽）全部放行。
_IDENT_RE = re.compile(r"[a-z]{2,}[-_][a-z]{2,}|\.(?:md|py|json|csv|ya?ml|txt)\b")
# ④ 截断：占位符 _MASK = 已遮蔽的公式（数学 \dots 的 … 在里面，不算截断）。
#    ⛔ 只认三点及以上的西文省略号：`x..y` 是区间写法（如 HC-01..HC-08）不算截断，
#       它由 _MARK_RE 的 HC-\d 另行拦下。
_TRUNC_RE = re.compile(r"…|\.\.\.")
# ⑤ 公式剥离留空：原文 `与 $v_p$ 的` 剥掉 LaTeX 后成了「与 的」——符号删了没补。
# ⛔ 判据不能写成「汉字+空格+汉字」：那会把「第 3.2 节 灵敏度分析」这类正当的
#    "编号 + 空格 + 标题" 判成留空（实测误报）。真实留空的特征是【空格后紧跟依附性
#    虚词】——的/时/最/非 这些字不能起头，前面必然少了个被删掉的符号。
# ⛔ 全角空格是正当排版（如「状态上行　　指令下发」），探针已不压它，这里只认半角。
# ⛔ 字表只留「的/时」两个：其余候选都能正当起头 ——「以最小化为目标」「非线性增长」
#    「最优解」「为线性」「是显著的」，收进来必误报。宁可漏检也不误报：误报会让作图者
#    去改本来正确的文字（曾因判据污染把两张达标的图改坏）。
_BLANK_MATH_RE = re.compile(r"[一-龥] (?=[的时])")
# 更强的一条：行内连续 2+ 半角空格。原文 `分数 $\phi$ 时` 剥掉公式后左右空格并存，
# 探针已刻意不压它（见 capture.js 的 squash）。判别力高于上面的单空格判据。
_BLANK_GAP_RE = re.compile(r"[一-龥]  +|  +[一-龥]")

# ⑥ 结果泄漏：流程图/路线图应描述方法与流向，不承担结果展示。算法参数
# （容差、步长、迭代上限等）允许保留；由求解得到的数值和宣告式结论必须进正文。
_RESULT_NUMBER = r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:\s*[eE]\s*[-+]?\d+)?\s*%?"
_RESULT_WITH_NUMBER_RE = re.compile(
    rf"(?:输出|结果|求得|得到|计算得|确定为|最终|最优(?:值|解|方案)?|"
    rf"终止时刻|临界时刻|最小(?:值|螺距|成本|距离)?|最大(?:值|速度|收益)?|"
    rf"提升|降低|减少|增加|准确率|精确率|召回率|误差|RMSE|MAE|R\s*[²2]|AUC|"
    rf"result|output|obtained|final|optimal|minimum|maximum|improv(?:e|ed)|reduc(?:e|ed))"
    rf"[^。；;!?]{{0,36}}{_RESULT_NUMBER}", re.IGNORECASE,
)
_RESULT_ASSIGNMENT_RE = re.compile(
    rf"(?:t\s*\*|p\s*(?:_\s*)?min|v\s*(?:_\s*)?max|RMSE|MAE|MSE|MAPE|"
    rf"R\s*[²2]|AUC|F1|cost|objective)\s*(?:=|≈|:)\s*{_RESULT_NUMBER}",
    re.IGNORECASE,
)
_RESULT_CLAIM_RE = re.compile(
    r"结论成立|验证通过|结果表明|显著优于|效果最佳|性能(?:明显|显著)?提升|"
    r"validation\s+passed|results?\s+show|outperform(?:s|ed)?",
    re.IGNORECASE,
)
_METHOD_SETTING_RE = re.compile(
    r"终止条件|停止条件|收敛阈值|容差|步长|精度|迭代上限|最大迭代|种群规模|"
    r"搜索范围|参数范围|置信水平|样本量|时间步|tolerance|threshold|step\s*size|"
    r"iterations?|population\s*size|search\s*range",
    re.IGNORECASE,
)
_STRONG_RESULT_CUE_RE = re.compile(
    r"输出|结果|求得|得到|计算得|确定为|最终|最优值|终止时刻|临界时刻|"
    r"result|output|obtained|final|optimal\s+value",
    re.IGNORECASE,
)


def _result_leak_reason(text):
    text = " ".join((text or "").split())
    if not text:
        return None
    if _RESULT_CLAIM_RE.search(text):
        return "包含结论性判断，改为待输出的量名"
    if _METHOD_SETTING_RE.search(text) and not _STRONG_RESULT_CUE_RE.search(text):
        return None
    if _RESULT_WITH_NUMBER_RE.search(text) or _RESULT_ASSIGNMENT_RE.search(text):
        return "包含具体求解结果数值，移入正文或结果图表"
    return None


def _check_node_texts(node_texts):
    """对探针回传的可见文字做内容体检，返回 [(类别, 说明, 样例)]。

    ⛔ 必须用【渲染后】的文字，不能扫 HTML 源码：
       - 源码里 `$v_p$` 有内容，只有渲染后才知道是真留空还是 KaTeX 出了符号；
       - 源码含 CSS 字符串、KaTeX 的 LaTeX 注解，扫了全是误报。
    """
    # ⛔ 按【文字条目】聚合，不按命中次数：一条「修正项 F1：…必须含 …」既是元内容
    #    又是截断，但对作图者只是「重写这一条」一个动作。按次数计会把 9 条虚报成 14 处，
    #    读的人以为工作量翻倍。
    agg = {}
    order = []
    for raw in node_texts or []:
        t = (raw or "").strip()
        if not t:
            continue
        if t not in agg:
            agg[t] = []
            order.append(t)
        cats = agg[t]

        def add(cat, why, _c=cats):
            if not any(c == cat for c, _ in _c):
                _c.append((cat, why))
        plain = _DOMAIN_RE.sub("·", t)     # 学科搭配先遮掉，再查元内容、工程语汇（见 _DOMAIN_TERMS）
        for w in _META_WORDS:
            if w in plain:
                add("元内容", "「%s」是中间产物的自述，不是模型方法" % w)
                break
        for w in _JARGON_WORDS:
            if w in plain:
                add("工程语汇", "「%s」是工程口语，学术图不用" % w)
                break
        m = _MARK_RE.search(t)
        if m:
            add("内部标记", "残留「%s」" % m.group(0).strip())
        m = _MD_RESIDUE_RE.search(t)
        if m:
            add("Markdown 残留", "抄来的「%s」没清" % m.group(0).strip())
        m = _IDENT_RE.search(t)
        if m:
            add("路径/标识符", "「%s」是目录名或变量名，不是论文内容" % m.group(0))
        # 截断只看遮蔽公式后的文字
        if _TRUNC_RE.search(t.replace(_MASK, "")):
            add("截断", "标签被硬切，正式论文读不通")
        tx = t.replace(_MASK, "X")
        if _BLANK_MATH_RE.search(tx) or _BLANK_GAP_RE.search(tx):
            add("公式留空", "剥 LaTeX 时符号被删没补")
        result_reason = _result_leak_reason(tx)
        if result_reason:
            add("结果泄漏", result_reason)
    return [(cats, t.replace(_MASK, "⟨式⟩")[:46]) for t in order
            for cats in (agg[t],) if cats]


def _check_text_deco(text_deco):
    """底纹压字 / 白描边光晕（"图丑"的第一位真因），返回 [(类别, 样例, 细节)]。

    ⛔ 实测来源：禁灰之后"表示重点"只剩黑底纹一条路，于是把 45° 斜线或点阵垫在
       11px 中文后面 —— 笔画被网格切碎，糊成一团；作图者再加 -webkit-text-stroke 白描边
       去救可读性，结果每个字一圈白光晕，一眼就是机器生成。
    ⛔ 正解：底纹只铺在【无文字】的窄条/色块上；文字层次改用线宽 / 双线 / 虚线 / 留白。
       空心字（color:transparent + text-stroke）是例外——它没有填充，不产生光晕，放行。
    """
    hits = []
    for it in text_deco or []:
        txt = (it.get("txt") or "").strip()
        bg = it.get("bg") or ""
        try:
            stroke = float(it.get("stroke") or 0)
        except (TypeError, ValueError):
            stroke = 0.0
        if bg:
            hits.append(("底纹压字", txt, bg))
        if stroke > 0.3 and bg:
            # 有底纹又有描边 = 典型的"先垫底纹再用白描边救"组合
            hits.append(("描边救底纹", txt, "text-stroke %.1fpx" % stroke))
    # 同一条文字只报一次最重的
    seen, out = set(), []
    for cat, txt, detail in hits:
        if txt in seen:
            continue
        seen.add(txt)
        out.append((cat, txt[:34], detail))
    return out


def _check_text_ink(text_ink):
    """合成墨色查中间灰（禁灰第二层），返回 [(rgb串, 次数, 原色, 累计opacity, 样例)]。

    ⛔ 源码扫描的盲区：黑字 opacity:.78 在白底上合成明度 56 —— 落在禁灰区间、
       肉眼就是深灰，但字面量是 #000 → _scan_mid_grays 判「零灰」。
    ⛔ 只拦【文字】：opacity 用在线/边框/底纹上是 INK 六档的正当手段（弱化不靠调灰），
       拦了会砍掉整个弱化体系。文字发灰才是用户点出的"喜欢加粗跟浅色"那个破绽。
    """
    bad = []
    for it in text_ink or []:
        try:
            r, g, b = int(it["r"]), int(it["g"]), int(it["b"])
        except (KeyError, TypeError, ValueError):
            continue
        if _is_mid_gray(r, g, b):
            bad.append(("rgb(%d,%d,%d)" % (r, g, b), it.get("n") or 1,
                        it.get("raw") or "?", it.get("op"), it.get("txt") or ""))
    bad.sort(key=lambda x: -x[1])
    return bad


def _is_roadmap(path):
    name = Path(path).stem.lower()
    return bool(re.search(r"roadmap|technical[-_]?route|tech[-_]?route|技术路线", name))


def _style_audit_issues(path, geom):
    """Return deterministic readability issues collected by desktop/capture.js.

    Route diagrams receive stricter cognitive-load checks; other diagram types only share
    the WCAG-inspired text contrast check. Kept pure so unit tests do not need Electron.
    """
    audit = (geom or {}).get("styleAudit") or {}
    issues = []
    low = audit.get("lowContrast") or []
    if low:
        samples = "、".join(
            "「%s」%.2f:1" % ((it.get("txt") or "?")[:18], float(it.get("ratio") or 0))
            for it in low[:4]
        )
        issues.append("文字对比度：%d 处低于 4.5:1（%s）。调整文字或背景色；不要用降低 opacity 表示次要。"
                      % (len(low), samples))

    palette = str(audit.get("palette") or "").lower()
    palette_bad = audit.get("paletteViolations") or []
    if palette == "mono" and palette_bad:
        samples = "、".join(
            "「%s」%s=%s" % ((it.get("txt") or "?")[:14], it.get("prop") or "color",
                              it.get("color") or "?")
            for it in palette_bad[:4]
        )
        issues.append("配色越界：用户选择纯黑白，但渲染后发现 %d 处非黑白颜色（%s）。"
                      "结构可以变化，文字、填充、边框、连线和图案必须全部改为纯黑或纯白。"
                      % (len(palette_bad), samples))

    if not _is_roadmap(path):
        return issues

    nodes = int(audit.get("semanticNodes") or 0)
    explicit = bool(audit.get("explicitNodes"))
    if explicit and nodes > ROADMAP_MAX_NODES:
        issues.append("路线图节点：%d 个，硬上限 %d。保留高层主路径，细节拆到子问题流程图。"
                      % (nodes, ROADMAP_MAX_NODES))
    blocks = int((geom or {}).get("textBlocks") or 0)
    if explicit and blocks > ROADMAP_MAX_TEXT_BLOCKS:
        issues.append("路线图文字模块：%d 个，硬上限 %d。标题、阶段标签与节点叠加过多，须合并或拆图。"
                      % (blocks, ROADMAP_MAX_TEXT_BLOCKS))
    total_chars = int(audit.get("totalNodeChars") or 0)
    if explicit and total_chars > ROADMAP_MAX_TOTAL_CHARS:
        issues.append("路线图文字：%d 字符，硬上限 %d。删除段落、公式推导、参数和结果数值。"
                      % (total_chars, ROADMAP_MAX_TOTAL_CHARS))
    max_chars = int(audit.get("maxNodeChars") or 0)
    if explicit and max_chars > ROADMAP_MAX_NODE_CHARS:
        issues.append("单节点文字：最长 %d 字符（上限 %d），样例「%s」。改为一个动作或对象。"
                      % (max_chars, ROADMAP_MAX_NODE_CHARS,
                         (audit.get("maxNodeText") or "?")[:36]))
    focus = int(audit.get("focusNodes") or 0)
    # 旧图没有显式标记时，class 名可能把阶段基座误认成 focus；仅对极端多焦点硬拦。
    if (explicit and focus > ROADMAP_MAX_FOCUS) or (not explicit and focus >= 5):
        issues.append("视觉焦点：%d 个（上限 %d）。只能保留一个 data-mh-focus，其他节点取消粗边/反色。"
                      % (focus, ROADMAP_MAX_FOCUS))
    dark_nodes = int(audit.get("darkNodes") or 0)
    if dark_nodes:
        issues.append("深色节点：%d 个。技术路线图禁止黑底白字节点或黑色底座，黑白风格也应使用白底细黑线。"
                      % dark_nodes)
    dark_ratio = float(audit.get("darkFillRatio") or 0)
    if dark_ratio > ROADMAP_MAX_DARK_FILL:
        issues.append("深色填充：占画布 %.1f%%（上限 %.0f%%）。路线图禁止黑色横幅和黑底白字节点。"
                      % (dark_ratio * 100, ROADMAP_MAX_DARK_FILL * 100))
    thick = int(audit.get("thickNodes") or 0)
    # 旧图的类名回退会把部分阶段条误算成节点；须同时满足“至少 5 个 + 占比超限”才硬拦。
    # 新图有 data-mh-node 精确标记，直接按比例判定。
    if (explicit and nodes and thick / nodes > ROADMAP_MAX_THICK_SHARE) or (
            not explicit and nodes and thick >= 5 and thick / nodes > ROADMAP_MAX_THICK_SHARE):
        issues.append("粗边节点：%d/%d（上限 %.0f%%）。普通节点改为细线，用留白/线型/编号分层。"
                      % (thick, nodes, ROADMAP_MAX_THICK_SHARE * 100))
    return issues


# ===== 判据自测用例（--self-test）=====
# ⛔ 改动上面任何词表/正则后必跑：`python screenshot_capture.py --self-test`
#    这些用例全部来自真实翻车或真实误报，删一条就少一层防线。
#    输入按【探针已处理过】的形态写：半角换行已压、每棵 .katex 已换成 _MASK。
_TEST_CONTENT = [
    # ---- 应命中 ----
    ("修正项 F1：功率平衡式必须含 …", {"元内容", "截断"}),
    ("硬约束清单 HC-01..HC-08", {"元内容", "内部标记"}),
    ("参数口径表", {"元内容", "工程语汇"}),
    ("METHOD_CLAIMS：本报告的方法主张", {"元内容"}),
    ("— 本文重点：comp-paper-zh", {"路径/标识符"}),      # 真实：工作区目录名进了图
    ("见 md_to_docx.py 的实现", {"路径/标识符"}),
    ("结果约束清单`）", {"元内容", "Markdown 残留"}),
    ("姿态 → 阻力面积的映射与其…", {"截断"}),
    ("⛔ 一致性校验", {"内部标记"}),
    ("两种受限机制与 的非单调性", {"公式留空"}),         # 真实：剥了 $v_p$ 没补
    ("体积分数  时的导通概率", {"公式留空"}),            # 真实：双空格
    ("**关键步骤**", {"Markdown 残留"}),
    ("闭环校正机制", {"工程语汇"}),
    ("输出：t*=412.473838 s", {"结果泄漏"}),
    ("结论成立，方案显著优于基线", {"结果泄漏"}),
    # ---- 应放行（每条都对应一次真实误报或已识别的误报风险）----
    ("NSGA-II 多目标求解", set()),          # 大写缩写带连字符
    ("A-B 混填策略", set()),                # 单字符两侧
    ("阶段 I：参数标定", set()),
    ("状态上行　　指令下发", set()),         # 全角空格是正当排版
    ("第 3.2 节 灵敏度分析", set()),         # 真实误报：曾被判"公式留空"
    ("目标 以最小化能耗为准", set()),        # "以"能正当起头
    ("阻力 非线性增长", set()),              # "非"能正当起头
    ("求解 最优构型", set()),                # "最"能正当起头
    ("模型 和 数据两条线", set()),           # "和"能正当起头
    ("修正量 ΔF 的量纲分析", set()),         # "修正量"是正当数学词,别误伤成"修正项"
    ("序列 %s 的收敛判别" % _MASK, set()),   # 公式内的数学省略号,不算截断
    ("速度 %s 的非单调性分析" % _MASK, set()),
    ("Pareto 前沿筛选", set()),
    ("时间二分求根（精度 1e-6 s）", set()),
    ("输出最优螺距 p_min", set()),
    # 学科搭配（10-21 复查：供应链 / 控制 / 通信流程图被整张拦下）；同一条里的工程口语照旧拦
    ("上游供应商 → 下游客户", set()),
    ("闭环控制系统", set()),
    ("通信链路预算", set()),
    ("统计口径一致性检验", set()),
    ("设备自检流程", set()),
    ("打通数据链路", {"工程语汇"}),
]
_TEST_INK = [   # (r, g, b, 应否拦)
    (56, 56, 56, True),      # 黑字 opacity:.78 合成——字面量骗过源码扫描的那一类
    (31, 31, 31, False),     # opacity:.88 合成,近黑放行
    (0, 0, 0, False),        # 纯黑
    (255, 255, 255, False),  # 纯白
    (128, 128, 128, True),   # 正灰
    (139, 139, 133, True),   # 真实盲点:只认 r==g==b 会漏
    (30, 90, 200, False),    # 彩色放行
]


_TEST_DECO = [   # (bg, stroke, 应否拦)
    ("repeating-linear-gradient(45deg, rgb(0,0,0) 0px, ...)", 0, True),   # 斜线压字
    ("radial-gradient(rgb(0,0,0) 0.5px, ...)", 0, True),                  # 点阵压字
    ("repeating-linear-gradient(45deg, ...)", 2.6, True),                 # 底纹+白描边救
    ("", 0.8, False),   # 空心字（无填充、无底纹）→ 放行
    ("", 0, False),     # 干净文字
]


def _self_test():
    """跑内置对抗用例，返回失败条数（并打印明细）。"""
    fails = 0
    deco_fails = 0
    for bg, stroke, want in _TEST_DECO:
        got = bool(_check_text_deco([{"txt": "示例", "bg": bg, "stroke": stroke}]))
        if got != want:
            deco_fails += 1
            print("❌ 可读性 bg=%r stroke=%s 期望%s 实得%s"
                  % (bg[:20], stroke, "拦" if want else "放行", "拦" if got else "放行"))
    print("可读性闸: %d/%d" % (len(_TEST_DECO) - deco_fails, len(_TEST_DECO)))
    fails += deco_fails
    for text, want in _TEST_CONTENT:
        got = {c for cats, _ in _check_node_texts([text]) for c, _ in cats}
        if got != want:
            fails += 1
            print("❌ 内容 %r\n   期望 %s / 实得 %s"
                  % (text.replace(_MASK, "⟨式⟩"),
                     sorted(want) or "放行", sorted(got) or "放行"))
    print("内容闸: %d/%d" % (len(_TEST_CONTENT) - fails, len(_TEST_CONTENT)))
    ink_fails = 0
    for r, g, b, want in _TEST_INK:
        got = bool(_check_text_ink([{"r": r, "g": g, "b": b, "n": 1}]))
        if got != want:
            ink_fails += 1
            print("❌ 墨色 rgb(%d,%d,%d) 期望%s 实得%s"
                  % (r, g, b, "拦" if want else "放行", "拦" if got else "放行"))
    print("墨色闸: %d/%d" % (len(_TEST_INK) - ink_fails, len(_TEST_INK)))
    return fails + ink_fails


def _resolve_electron():
    """返回 (exe, main_script_or_None)。找不到返回 (None, None)。

    优先用后端 config 的 RUNTIME_ELECTRON_*；失败再看环境变量 MH_ELECTRON_EXE/MAIN。
    """
    exe = None
    main = None
    # 1) 从后端 config 读（把 web/backend 加入 path）
    try:
        _backend = Path(__file__).resolve().parent.parent / "web" / "backend"
        if str(_backend) not in sys.path:
            sys.path.insert(0, str(_backend))
        import config as _cfg  # type: ignore
        exe = getattr(_cfg, "RUNTIME_ELECTRON_EXE", None)
        main = getattr(_cfg, "RUNTIME_ELECTRON_MAIN", None)
    except Exception:
        pass
    # 2) 环境变量兜底（skill 运行时若注入了路径）
    if not exe:
        exe = os.environ.get("MH_ELECTRON_EXE") or None
        main = os.environ.get("MH_ELECTRON_MAIN") or None
    if exe and Path(exe).exists():
        # main 可选：打包后主 exe 自带 main.js，main 为空是正常的
        if main and not Path(main).exists():
            main = None
        return exe, main
    return None, None


def _capture_dir():
    """capture.js 所在目录（与 electron main.js 同级 desktop/，或打包后 app 内）。

    独立跑 capture.js 时需要它的路径；打包后主 exe 自带，不需要。
    """
    # 开发：desktop/capture.js
    dev = Path(__file__).resolve().parent.parent / "desktop" / "capture.js"
    return str(dev) if dev.exists() else None


def run_capture(targets, viewport=None, timeout=_TOTAL_TIMEOUT):
    """执行截图/出图。targets: [{url|file, out, format?, waitMs?, waitForSelector?, fullPage?}]。

    format="pdf"(或 out 以 .pdf 结尾) → 矢量 PDF；否则 PNG。字段整体透传给 capture.js。
    返回 dict: {"ok": bool, "results": [...], "reason": str}
    """
    exe, main = _resolve_electron()
    if not exe:
        return {"ok": False, "results": [], "reason": "electron_unavailable"}

    # 输出路径统一转绝对（capture.js 在自己进程里解析，相对路径基准不确定）
    norm_targets = []
    for t in targets:
        t2 = dict(t)
        if t2.get("out"):
            t2["out"] = str(Path(t2["out"]).resolve())
        if t2.get("file"):
            t2["file"] = str(Path(t2["file"]).resolve())
        norm_targets.append(t2)

    tmp = Path(tempfile.mkdtemp(prefix="mh_capture_"))
    cfg_path = tmp / "cfg.json"
    result_path = tmp / "result.json"
    cfg = {
        "viewport": viewport or {"width": 1280, "height": 800},
        "resultPath": str(result_path),
        "targets": norm_targets,
    }
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    # 命令：打包后 [exe, --mh-capture, cfg]；开发 [exe, capture.js, --mh-capture, cfg]
    # 开发用 capture.js 直接跑(argv[1]=capture.js 触发自动执行)；
    # main 存在(dev)时也可用 main.js 走分流，但直接 capture.js 更省启动开销。
    cap_js = _capture_dir()
    cmd = [exe]
    if main is not None:
        # 开发场景：优先直接跑 capture.js（更快、不启动整个应用）
        if cap_js:
            cmd.append(cap_js)
        else:
            cmd.append(main)
    cmd += ["--mh-capture", str(cfg_path)]

    env = dict(os.environ)
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "1"
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "results": [], "reason": "timeout"}
    except Exception as e:
        return {"ok": False, "results": [], "reason": "spawn_failed: %s" % e}

    # 读逐张结果
    results = []
    if result_path.exists():
        try:
            results = json.loads(result_path.read_text(encoding="utf-8")).get("results", [])
        except Exception:
            pass
    # 兜底：没拿到 result.json 就按输出文件是否存在判断
    if not results:
        for t in norm_targets:
            out = t.get("out")
            ok = bool(out) and Path(out).exists() and Path(out).stat().st_size > 1000
            results.append({"ok": ok, "out": out, "url": t.get("url") or t.get("file")})

    ok_all = bool(results) and all(r.get("ok") for r in results)
    return {"ok": ok_all, "results": results,
            "reason": "" if ok_all else "some_or_all_failed",
            "stderr_tail": (proc.stderr or "")[-500:]}


def main():
    # ⛔ 报告含 ✅/❌ 等非 GBK 字符：Windows 默认 GBK 控制台会 UnicodeEncodeError 崩溃。
    #    强制 stdout/stderr 走 UTF-8（Python 3.7+），生产 subprocess 与本机终端都稳。
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="通用界面截图工具(Electron capturePage)")
    ap.add_argument("--check", action="store_true", help="仅探测 Electron 是否可用")
    ap.add_argument("--config", help="批量截图配置 JSON 路径")
    ap.add_argument("--url", help="单张：页面 URL")
    ap.add_argument("--file", help="单张：本地 HTML 文件路径")
    ap.add_argument("--out", help="单张：输出路径(.png 截图 / .pdf 矢量)")
    ap.add_argument("--format", choices=["png", "pdf"], help="单张：输出格式(缺省按 out 后缀推断)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--wait-ms", type=int, default=1000)
    ap.add_argument("--full-page", action="store_true")
    ap.add_argument("--render-math", action="store_true",
                    help="截图前注入 KaTeX 渲染 HTML 里的 \\(...\\)/$$ 公式（含公式的流程/架构图用）")
    ap.add_argument("--geom-check", metavar="HTML",
                    help="元素级几何自检：量 HTML 里 .fig 内文字块，报文字溢出/越界裁切/块重叠。"
                         "只测量不出图。退出码 0=干净 1=有问题 2=无法检查。含公式的图配 --render-math。")
    ap.add_argument("--norm-check", metavar="HTML",
                    help="科研规范自检：字号/占页/对比度/视觉重量/认知密度、"
                         "无斜体、内容(截断/元内容/工程语汇/残留/公式留空)；路线图额外硬查节点/焦点/黑色面积。"
                         "geom-check 管不了这些（它只量图内部相对关系）。"
                         "退出码 0=达标 1=不达标 2=无法检查。含公式的图配 --render-math。")
    ap.add_argument("--self-test", action="store_true",
                    help="判据自测：跑内置对抗用例，验「该拦的拦住、该放的放行」。"
                         "⛔ 改动词表/正则后必跑，防判据退化。退出码 0=全过 1=有失败。")
    ap.add_argument("--page-width-in", type=float, default=5.5,
                    help="论文插图最大显示宽度(英寸)，默认 5.5 = md_to_docx 的 _DEFAULT_IMAGE_MAX_W_IN")
    ap.add_argument("--page-height-in", type=float, default=9.7,
                    help="论文正文区可用高度(英寸)，默认 9.7 ≈ A4 去页边距")
    args = ap.parse_args()

    # ===== 判据自测（不起 Electron，几十毫秒）=====
    if args.self_test:
        n = _self_test()
        print("✅ 判据全部达标" if not n else "⛔ %d 条判据失败 — 改回去或补用例" % n)
        sys.exit(1 if n else 0)

    # ===== 科研规范自检（可读性 / 占页 / 密度）=====
    if args.norm_check:
        one = {"file": args.norm_check, "geomCheck": True, "waitMs": args.wait_ms}
        if args.render_math:
            one["renderMath"] = True
        res = run_capture([one], viewport={"width": args.width, "height": args.height})
        if res.get("reason") == "electron_unavailable":
            print("electron unavailable — 无法规范自检，跳过（不阻塞）"); sys.exit(2)
        results = res.get("results") or []
        geom = (results[0].get("geom") if results else None) or {}
        fig = geom.get("fig") or {}
        w, h = fig.get("w") or 0, fig.get("h") or 0
        mf = geom.get("minFont")
        if not w or not h or not mf:
            print("⚠ 规范自检无法进行: %s" % (geom.get("error") or "无 .fig / 未测到字号"))
            sys.exit(2)
        blocks = geom.get("textBlocks") or 0
        # ⛔ 零灰检查：直接读 HTML 源码里的颜色字面量。
        #    判据与《设计规范 0.2 节》一致：chroma ≤18 且 45 < lum < 243 → 中间灰。
        #    近黑(lum≤45)/近白(lum≥243)放行——那是正常黑白，不是"灰"。
        grays = _scan_mid_grays(args.norm_check)
        italics = _scan_italics(args.norm_check)
        content = _check_node_texts(geom.get("nodeTexts"))
        deco = _check_text_deco(geom.get("textDeco"))
        style_issues = _style_audit_issues(args.norm_check, geom)
        style_audit = geom.get("styleAudit") or {}
        # 按论文实际插入规则推显示尺寸（宽受限为主，过高则改为高受限）
        disp_w = args.page_width_in
        disp_h = disp_w * h / w
        if disp_h > MAX_FIG_H_IN:
            disp_h = MAX_FIG_H_IN
            disp_w = disp_h * w / h
        font_pt = 72.0 * disp_w * mf / w
        share = disp_h / args.page_height_in
        print("=== 科研规范自检: %s ===" % args.norm_check)
        print("画布 %dx%d px（高/宽 %.2f）· 最小字号 %.1fpx · 模块 %d 个"
              % (w, h, h / w, mf, blocks))
        print("插入论文后 %.1f×%.1fin，占正文区高 %.0f%%，最小字 %.1fpt" % (disp_w, disp_h, share * 100, font_pt))
        bad = []
        if font_pt < MIN_FONT_PT:
            bad.append("字号：缩后仅 %.1fpt（下限 %dpt）。图设计得太宽 → 图宽/字号 = %.1f，须 ≤ %d。"
                       "改法：缩图宽或提字号，最小字来自「%s」"
                       % (font_pt, MIN_FONT_PT, w / mf, int(72.0 * args.page_width_in / MIN_FONT_PT),
                          geom.get("minFontTxt") or "?"))
        if share > MAX_PAGE_SHARE:
            bad.append("占页：占正文区高 %.0f%%（上限 %.0f%%）。高/宽 %.2f 偏高 → 压行数"
                       "（如把编号标签并进名称行），别只改朝向——换成竖排只会更高。"
                       % (share * 100, MAX_PAGE_SHARE * 100, h / w))
        # 普通图的块数仍是弱信号；路线图的认知密度由 style_issues 组合节点/文字/焦点硬拦。
        if blocks > MAX_TEXT_BLOCKS:
            print("⚠ 密度偏高：%d 个模块（建议 ≤%d）。若同时字号吃紧，优先删模块——"
                  "长公式降级到副标题、说明性文字移交 caption。" % (blocks, MAX_TEXT_BLOCKS))
        if _is_roadmap(args.norm_check) and not style_audit.get("explicitNodes"):
            print("⚠ 旧版路线图未提供 data-mh-node 标记：已启用保守兼容检查；新生成路线图必须补标记后使用严格认知密度门。")
        # 中间灰本身不是错误；合规的浅底/中性边框可减少纯黑视觉重量。真正硬门是
        # 渲染后的文字对比度（style_issues）和路线图深色面积。
        if grays:
            top = sorted(grays.items(), key=lambda kv: -kv[1])[:6]
            detail = "、".join("%s×%d" % (c, n) for c, n in top)
            print("ℹ 中性灰使用：%d 种（%s）。允许作为浅底/次级边界；文字仍须通过 4.5:1 对比度。"
                  % (len(grays), detail))
        # ⛔ 禁斜体（0 节第 8.1 条）：中文伪斜 + 一眼可辨的系统特征
        if italics:
            bad.append("斜体：查出 %s。⛔ 中文无真斜体，浏览器只能伪斜（正体强行倾斜），"
                       "学术排版不用。改用字距收放 letter-spacing / 字号差 / opacity 表达"
                       "「次要」；并加兜底 `.fig,.fig *{font-style:normal!important}`"
                       % "、".join(italics[:4]))
        repeating = _scan_repeating_gradients(args.norm_check)
        if repeating:
            bad.append("底纹：用了 %s，转成 PDF 后会断成一段段（只剩每段一小截）。斜纹改用平铺写法 "
                       "`background-image:linear-gradient(45deg,transparent 45%%,#000 45%%,#000 55%%,transparent 55%%);"
                       "background-size:5px 5px`，或直接用 `border-left:3px double #000`" % "、".join(repeating))
        for issue in style_issues:
            bad.append(issue)
        # ⛔⛔ 底纹压字 / 描边光晕：这是"图丑"的第一位真因，必须硬拦
        if deco:
            lines = ["可读性：%d 条文字被底纹或描边破坏。⛔ 底纹只许铺在【无文字】的"
                     "窄条/色块上；文字层次改用线宽 / 双线 / 虚线 / 留白。" % len(deco)]
            for cat, txt, detail in deco[:5]:
                lines.append("    · [%s] 「%s」 ← %s" % (cat, txt, detail))
            lines.append("    ⛔ 实测：黑斜线垫在 11px 中文后笔画被切碎，再加白描边救 → "
                         "每字一圈白光晕，一眼是机器生成。空心字（color:transparent，无填充）不在此列。")
            bad.append("\n".join(lines))
        # ⛔ 内容体检：正式论文里读不通的文字（截断/元内容/工程语汇/残留符号）
        if content:
            import collections as _c
            by = _c.Counter(cat for cats, _ in content for cat, _ in cats)
            head = "、".join("%s×%d" % (k, v) for k, v in by.most_common())
            lines = ["内容：%d 条文字要重写（%s）。⛔ 图里的文字要能独立读懂——"
                     "正式论文的读者看不到中间产物。" % (len(content), head)]
            for cats, sample in content[:8]:
                tags = "".join("[%s]" % c for c, _ in cats)
                lines.append("    · %s 「%s」" % (tags, sample))
                lines.append("        %s" % "；".join(w for _, w in cats))
            lines.append("    改法：截断 → 换短标题或语义改写，⛔ 别硬切加省略号；"
                         "元内容 → 整条换成模型方法本身；工程语汇 → 见"
                         "《写作规范·工程/质检语汇泄漏》替代表；公式 → 保留符号别只删 $。")
            bad.append("\n".join(lines))
        if not bad:
            print("✅ PASS — 字号 / 占页 / 对比度 / 视觉重量 / 认知密度 / 无斜体 / 内容 达标")
            sys.exit(0)
        for b in bad:
            print("❌ %s" % b)
        print("⛔ 共 %d 项不达标 — 见《设计规范 0.1 节 物理可读性》。" % len(bad))
        sys.exit(1)

    # ===== 几何自检模式（只测量不出图）=====
    if args.geom_check:
        one = {"file": args.geom_check, "geomCheck": True, "waitMs": args.wait_ms}
        if args.render_math:
            one["renderMath"] = True
        res = run_capture([one], viewport={"width": args.width, "height": args.height})
        if res.get("reason") == "electron_unavailable":
            print("electron unavailable — 无法几何自检，跳过（不阻塞）"); sys.exit(2)
        results = res.get("results") or []
        geom = (results[0].get("geom") if results else None) or {}
        if not geom or geom.get("error"):
            print("⚠ 几何自检无法进行: %s" % (geom.get("error") if geom else "无 .fig 或探针无返回"))
            sys.exit(2)
        overflow = geom.get("overflow") or []
        clip = geom.get("clip") or []
        overlap = geom.get("overlap") or []
        misalign = geom.get("misalign") or []
        escape = geom.get("escape") or []
        fig = geom.get("fig") or {}
        n = len(overflow) + len(clip) + len(overlap) + len(misalign) + len(escape)
        print("=== 几何自检: %s ===" % args.geom_check)
        print("画布 %sx%s px, 文字块 %s 个" % (fig.get("w", "?"), fig.get("h", "?"), geom.get("blocks", "?")))
        if n == 0:
            print("✅ PASS — 无文字溢出 / 越界 / 重叠 / 标签越位 / 对齐偏差")
            sys.exit(0)
        # ⛔ 标签越位：补住"文字压伪元素"盲区 —— 伪元素画的连线拿不到 rect，
        #    无法参与重叠检测；改判"绝对定位文字是否跑出自己的定位父"。
        if escape:
            print("❌ 标签越位 %d 处（跑出自己的定位父，会压住相邻列/轨道的连线）：" % len(escape))
            for e in escape[:8]:
                print("   · 「%s」 向%s越出 %spx（父 .%s）"
                      % (e.get("txt"), e.get("side"), e.get("over"), e.get("parent")))
            print("   改法：分支标签只写「是/否」，说明并入上游节点副标题（见《设计规范 0.6 节》⑨）。")
        if overflow:
            print("❌ 文字溢出被裁 %d 处（盒子太窄/太矮，文字被切）：" % len(overflow))
            for o in overflow[:12]:
                print("   · 「%s」 实宽%s>盒宽%s 实高%s>盒高%s"
                      % (o.get("txt"), o.get("sw"), o.get("cw"), o.get("sh"), o.get("ch")))
        if clip:
            print("❌ 越出 .fig 边界 %d 处（会被论文页面裁掉）：" % len(clip))
            for c in clip[:12]:
                sides = []
                for k, name in (("left", "左"), ("top", "上"), ("right", "右"), ("bottom", "下")):
                    if c.get(k, 0) > 0:
                        sides.append("%s越%spx" % (name, c[k]))
                print("   · 「%s」 %s" % (c.get("txt"), " ".join(sides)))
        if overlap:
            print("❌ 文字块重叠 %d 对（内容互相压盖）：" % len(overlap))
            for v in overlap[:12]:
                print("   · 「%s」 ×「%s」 交叠面积%spx²" % (v.get("a"), v.get("b"), v.get("area")))
        if misalign:
            print("❌ 对齐偏差 %d 处（声明了同列/同行却没对齐——用 grid+1fr/stretch 从结构锁死，别手写 width/margin）：" % len(misalign))
            for a in misalign[:12]:
                axis = a.get("axis")
                way = "同列竖直对齐(中轴横坐标)" if axis == "x" else "同行水平对齐(中轴纵坐标)"
                mem = "、".join(a.get("members") or [])
                print("   · %s=%s：%s 组内 %d 个元素中轴错开 %spx（>%s容差）｜成员：%s"
                      % (a.get("attr"), a.get("group"), way, a.get("count"), a.get("spread"), 4, mem))
        print("⛔ 共 %d 处几何问题 — 读 HTML 针对性改 CSS 后重检。" % n)
        sys.exit(1)

    if args.check:
        exe, main_js = _resolve_electron()
        if exe:
            print("OK electron available: %s%s" % (exe, "" if not main_js else " (+main.js)"))
            sys.exit(0)
        print("electron unavailable — 截图能力不可用，调用方应降级为占位符")
        sys.exit(2)

    # 组装 targets
    if args.config:
        try:
            cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        except Exception as e:
            print("配置读取失败: %s" % e); sys.exit(3)
        targets = cfg.get("targets") or []
        viewport = cfg.get("viewport")
    elif (args.url or args.file) and args.out:
        one = {"out": args.out, "waitMs": args.wait_ms}
        if args.url:
            one["url"] = args.url
        else:
            one["file"] = args.file
        if args.format:
            one["format"] = args.format
        if args.full_page:
            one["fullPage"] = True
        if args.render_math:
            one["renderMath"] = True
        targets = [one]
        viewport = {"width": args.width, "height": args.height}
    else:
        print("需要 --config，或 (--url|--file) + --out"); sys.exit(3)

    if not targets:
        print("没有截图目标"); sys.exit(3)

    res = run_capture(targets, viewport=viewport)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if res["reason"] == "electron_unavailable":
        sys.exit(2)
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
