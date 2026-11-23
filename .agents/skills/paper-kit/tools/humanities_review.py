"""文本评估规则引擎（人文社科论文质检）

⛔ 本文件改编自开源项目 humanities-thesis-skill（作者 @ganzhi-black, MIT License,
   https://github.com/ganzhi-black/humanities-thesis-skill）的 scripts/lib/review_rules.py，
   规则逻辑原样复用，仅调整术语表加载路径并补充 CLI 入口。MIT 署名见
   skills/shared-scripts/NOTICE-humanities.md。

用确定性规则（正则匹配、术语表比对、格式模板检查）对生成的论文文本
进行校验。不依赖模型判断——模型自己检查自己等于没检查。

每条规则返回一个 Issue 对象，包含位置、严重程度和修改建议。

用法（CLI）：
    python humanities_review.py paper.md                  # 文本报告
    python humanities_review.py paper.md --format json    # JSON（供 Agent 解析）
    python humanities_review.py paper.md --severity error # 只看错误级
    python humanities_review.py paper.md --discipline history  # 按学科关掉不适用的规则（默认读 .mh/writing_spec.json）

退出码：0 没有错误级问题；1 有错误级问题（警告和提示不影响退出码）。

2026-10-11 论证逻辑与文理分型第 5 期修过的地方：引用年份上限按当年算并查参考文献行；"有学者指出"同一句紧跟出处
就不报、没出处降为警告（与写作规则 R4"改写成有研究者认为并紧跟出处"一致）；全角"［待补充］"也认，占位符升为警告；
"必然性""其实际"等复合词不误报，强度词不和 R3-01 重复报；同义译名组去掉常用词、挪进术语表；脚注、文献类型、
标题（Markdown # 与 LaTeX 的 section 命令）识别补全；引文里的第一人称不算自称；"值得注意的是""首先/其次"不再当论证
连接或论据；新增"研究表明"后缺引用（R1-04）。原文引语能不能在上传材料里找到，交给 tools/academic_writing_check.py 的 H 组。
"""
from __future__ import annotations
import re
import os
import logging
from datetime import date
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    ERROR = "error"       # 必须修改：编造文献、格式严重错误
    WARNING = "warning"   # 建议修改：术语不一致、语体问题
    INFO = "info"         # 提示注意：可选优化


@dataclass
class Issue:
    rule: str              # 规则编号，如 "R1-01"
    severity: Severity
    message: str           # 问题描述
    line: int = 0          # 所在行号
    context: str = ""      # 问题上下文（截取的文本片段）
    suggestion: str = ""   # 修改建议

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "context": self.context[:100] if self.context else "",
            "suggestion": self.suggestion,
        }


# ═══════════════════════════════════════════════════════
# 第一类：可信度检查（对应 Rules R1/R3）
# ═══════════════════════════════════════════════════════

# 同一句里紧跟的出处：[N]、[N-M]、^[N]^、\cite{…}、①、[^n]、\footnote、（作者，年份）、作者（年份）
_CITE_MARK = re.compile(
    r"\[\s*\d+(?:\s*[-–—,，、]\s*\d+)*\s*\]|\\(?:cite[a-zA-Z]*|footcite|parencite|textcite)\*?\s*(?:\[[^\]]*\]\s*)*\{"
    r"|\\footnote\s*\{|\[\^[^\]\s]+\]|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|<sup>"
    r"|[（(][^（）()\n]{0,40}?(?:19|20)\d{2}[a-z]?(?:\s*[:：，,][^（）()\n]{0,12})?[）)]")
_SENTENCE_END = re.compile(r"[。！？!?；;]")


def _sentence_at(line: str, start: int, end: int) -> str:
    """line 里包住 [start, end) 的那一句。"""
    left = max((m.end() for m in _SENTENCE_END.finditer(line, 0, start)), default=0)
    right = _SENTENCE_END.search(line, end)
    return line[left:right.end() if right else len(line)]


def check_fabricated_references(text: str) -> list[Issue]:
    """检测可能编造的文献引用"""
    issues: list[Issue] = []
    lines = text.split("\n")
    this_year = date.today().year

    for i, line in enumerate(lines, 1):
        # "有学者指出"一类：同一句紧跟出处就不报（写作规则 R4 让这样写）；没有出处才报，警告级
        for m in re.finditer(r"(有学者|有研究者|有人|据研究)(指出|认为|发现|表明|提出)", line):
            if _CITE_MARK.search(_sentence_at(line, m.start(), m.end())):
                continue
            issues.append(Issue(
                rule="R1-01",
                severity=Severity.WARNING,
                message="模糊引用：使用了「有学者指出」类表述，同一句里没有出处",
                line=i,
                context=line.strip()[:80],
                suggestion="在同一句紧跟具体出处（[N]、注码或作者与年份），或改成直接写出作者与观点；找不到出处就删去",
            ))

        # 占位符：半角 [待补充 和全角 ［待补充（写作技能写的是全角）都认；提交前必须补齐，所以是警告
        if re.search(r"[\[［【]\s*待(?:补充|查证|核实|作者填写|作者补充|确认)", line):
            issues.append(Issue(
                rule="R1-02",
                severity=Severity.WARNING,
                message="发现待补充占位符，提交前需要补充具体信息",
                line=i,
                context=line.strip()[:80],
                suggestion="按 OPEN_QUESTIONS.md 里的待确认事项补齐，补不了的改写成不需要这条信息的说法",
            ))

        # 晚于今年的年份可能是编造的：正文里的（2027）和参考文献条目里的年份都查
        years = [int(y) for y in re.findall(r"[（(]\s*((?:19|20)\d{2})[a-z]?\s*[)）]", line)]
        if re.match(r"^\s*(?:\[\s*\d+\s*\]|\\bibitem|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|\[\^[^\]\s]+\]:)", line):
            # 页码（": 2030""-2031""第 2045 页""p. 2030"）、DOI 和网址里的数不算年份
            years += [int(y) for y in re.findall(
                r"(?<![\d.\-–—~～:：/])(?<![:：]\s)(?<!pp\.\s)(?<!p\.\s)(?<!第)((?:19|20)\d{2})(?!\d)(?!\s*页)", line)]
        for year in sorted(set(years)):
            if year > this_year:
                issues.append(Issue(
                    rule="R1-03",
                    severity=Severity.ERROR,
                    message=f"引用年份 {year} 超过当前年份（{this_year}），可能是编造的",
                    line=i,
                    context=line.strip()[:80],
                ))

        # "研究表明"一类：同一句没有出处（R1-04，2026-10-11 新增）
        for m in re.finditer(r"(?<![本该此这])(?:已有|大量|许多|不少|诸多|相关|以往)?(?:研究|文献)(?:表明|显示|发现|指出|证实)", line):
            if re.search(r"(?:上述|前述|以上|这些|这一|该)$", line[max(0, m.start() - 3):m.start()]):
                continue
            if _CITE_MARK.search(_sentence_at(line, m.start(), m.end())):
                continue
            issues.append(Issue(
                rule="R1-04",
                severity=Severity.WARNING,
                message="「研究表明」一类说法同一句里没有引用",
                line=i,
                context=line.strip()[:80],
                suggestion="在同一句紧跟具体文献，或删去这类模糊归因",
            ))
            break

    return issues


def check_unsupported_claims(text: str) -> list[Issue]:
    """检测过度断言：缺少限定词的绝对化表述"""
    issues: list[Issue] = []
    lines = text.split("\n")

    absolute_patterns = [
        (r"毫无疑问", "建议改为「可以认为」或「有理由认为」"),
        (r"众所周知", "建议改为「学界普遍认为」并附引用"),
        (r"不言而喻", "学术论文中应当明确论证，而非诉诸不言而喻"),
        (r"显而易见", "建议改为「从以上分析可以看出」"),
        (r"(?<!偶然与)(?<!偶然和)必然(?!性|王国|律|与偶然|和偶然)", "建议改为「很可能」或「在很大程度上」，除非有充分论证"),
        (r"完全(?:是|证明了|说明了)", "建议加入限定词，避免绝对化"),
        (r"无可辩驳", "学术论文中应避免此类修辞"),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, suggestion in absolute_patterns:
            if re.search(pattern, line):
                issues.append(Issue(
                    rule="R3-01",
                    severity=Severity.WARNING,
                    message=f"过度断言：使用了「{re.search(pattern, line).group()}」",
                    line=i,
                    context=line.strip()[:80],
                    suggestion=suggestion,
                ))

    return issues


# ═══════════════════════════════════════════════════════
# 第二类：术语一致性检查
# ═══════════════════════════════════════════════════════

def _load_terminology_map() -> dict[str, list[str]]:
    """从术语对照表加载中文→英文映射"""
    term_map: dict[str, list[str]] = {}
    _here = os.path.dirname(os.path.abspath(__file__))
    # 多候选路径：运行时工作区 _utils/ 、开发期 skills/shared-scripts/ 、同目录
    _candidates = [
        os.path.join(os.getcwd(), "_utils", "humanities-terminology-bilingual.md"),
        os.path.join(_here, "..", "skills", "shared-scripts", "humanities-terminology-bilingual.md"),
        os.path.join(_here, "humanities-terminology-bilingual.md"),
        os.path.join(_here, "..", "..", "references", "terminology-bilingual.md"),
    ]
    term_file = next((p for p in _candidates if os.path.isfile(p)), None)
    if not term_file:
        return term_map

    try:
        with open(term_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("|") or line.startswith("|---"):
                    continue
                cols = [c.strip() for c in line.split("|")]
                cols = [c for c in cols if c]
                if len(cols) >= 2:
                    zh = cols[0]
                    # 处理"中文A/中文B"的情况
                    for term in re.split(r"[/／]", zh):
                        term = term.strip()
                        if term and len(term) >= 2 and term not in ("中文", "说明"):
                            term_map[term] = cols[1:]
    except OSError:
        pass
    return term_map


_DEFAULT_SYNONYM_GROUPS = [
    ["赤裸生命", "裸命", "裸生命"],
    ["灵晕", "灵韵"],
    ["延异", "延差", "分延"],
    ["操演性", "述行性", "展演性"],
    ["异托邦", "异质空间", "异质地方"],
    ["解域化", "去疆域化", "去辖域化"],
]


def _term_file() -> Optional[str]:
    _here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.getcwd(), "_utils", "humanities-terminology-bilingual.md"),
        os.path.join(_here, "..", "skills", "shared-scripts", "humanities-terminology-bilingual.md"),
        os.path.join(_here, "humanities-terminology-bilingual.md"),
    ]
    return next((p for p in candidates if os.path.isfile(p)), None)


def _load_synonym_groups() -> list[list[str]]:
    """术语表"同一概念的不同译名"一节：| 推荐译名 | 其他译名（顿号分隔） | 原文 |；读不到就用内置的几组。"""
    path = _term_file()
    groups: list[list[str]] = []
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                inside = False
                for line in f:
                    line = line.strip()
                    if line.startswith("## "):
                        inside = "同一概念的不同译名" in line
                        continue
                    if not inside or not line.startswith("|") or line.startswith("|-") or "推荐译名" in line:
                        continue
                    cols = [c.strip() for c in line.strip("|").split("|")]
                    if len(cols) >= 2 and cols[0]:
                        group = [cols[0]] + [t.strip() for t in re.split(r"[、,，/／]", cols[1]) if t.strip()]
                        if len(group) >= 2:
                            groups.append(group)
        except OSError:
            groups = []
    return groups or [list(g) for g in _DEFAULT_SYNONYM_GROUPS]


def check_terminology_consistency(text: str) -> list[Issue]:
    """检查同一概念的中文译名是否一致（译名组见术语表）"""
    issues: list[Issue] = []

    # 检查同一概念是否在文中使用了不同的中文译名（例如"赤裸生命"和"裸命"混用）。译名组写在术语表的
    # "同一概念的不同译名"一节；"纪律""论述""召唤""质询""灵光"这类常用词不进组，免得误报
    synonym_groups = _load_synonym_groups()

    for group in synonym_groups:
        found_terms = []
        found_lines: dict[str, list[int]] = {}
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            # 长的先认，认过的位置不再给短的匹配："赤裸生命"里的"裸生命"不算混用
            work = line
            for term in sorted(group, key=len, reverse=True):
                if term in work:
                    if term not in found_terms:
                        found_terms.append(term)
                    found_lines.setdefault(term, []).append(i)
                    work = work.replace(term, "\0" * len(term))

        if len(found_terms) > 1:
            locations = "; ".join(
                f"「{t}」(第{','.join(str(l) for l in found_lines[t][:3])}行)"
                for t in found_terms
            )
            issues.append(Issue(
                rule="T-01",
                severity=Severity.WARNING,
                message=f"术语不一致：同一概念使用了多个译名",
                context=locations,
                suggestion=f"建议统一使用「{group[0]}」（术语表的推荐译名），或在首次出现时注明不同译法",
            ))

    return issues


# ═══════════════════════════════════════════════════════
# 第三类：格式规范检查
# ═══════════════════════════════════════════════════════

def check_citation_format(text: str) -> list[Issue]:
    """检查引注格式常见问题"""
    issues: list[Issue] = []
    lines = text.split("\n")

    for i, line in enumerate(lines, 1):
        # 检查脚注编号后是否缺少内容（空脚注）：①…⑳、Markdown 的 [^n]:、LaTeX 的 \footnote{}
        if (re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*$", line.strip())
                or re.match(r"^\[\^[^\]\s]+\]:\s*$", line.strip())
                or re.search(r"\\footnote\s*\{\s*\}", line)):
            issues.append(Issue(
                rule="F-01",
                severity=Severity.ERROR,
                message="空脚注：脚注编号后没有内容",
                line=i,
                context=line.strip(),
            ))

        # 检查GB/T 7714格式中是否缺少文献类型标识（Markdown 的 [N] 条目、LaTeX 的 \bibitem 条目）
        if re.search(r"^\s*\[\d+\]\s+\S", line) or re.match(r"^\s*\\bibitem\s*(?:\[[^\]]*\])?\{[^}]*\}\s*\S", line):
            if not re.search(r"\[(?:[MJDCNPSRGAZ]|EB|DB|CP|DS|CM|CL|A/OL|M/OL|J/OL|D/OL|C/OL|N/OL|EB/OL|DB/OL|CP/OL|Z/OL)(?:/OL)?\]", line):
                issues.append(Issue(
                    rule="F-02",
                    severity=Severity.WARNING,
                    message="参考文献条目可能缺少文献类型标识（如 [M] [J] [D]）",
                    line=i,
                    context=line.strip()[:80],
                    suggestion="GB/T 7714 要求标注 [M]专著 [J]期刊 [D]学位论文 等",
                ))

        # 检查中英文标点混用（排除：括号内内容、参考文献行、脚注行）
        is_ref_line = bool(re.match(r"^\s*\[\d+\]", line) or re.match(r"^\s*[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]", line)
                           or re.match(r"^\s*(?:\\bibitem|\[\^[^\]\s]+\]:)", line))
        if not is_ref_line:
            # 去掉所有括号内容后再检测
            line_no_parens = re.sub(r"[（(][^）)]*[）)]", "", line)
            if re.search(r"[\u4e00-\u9fff][,.;:?!]", line_no_parens):
                issues.append(Issue(
                    rule="F-03",
                    severity=Severity.WARNING,
                    message="中文语境中使用了英文标点",
                    line=i,
                    context=line.strip()[:80],
                    suggestion="中文语境应使用全角标点（，。；：？！）",
                ))

    # 悬空脚注：正文里写了 [^n]，却没有 [^n]: 的脚注内容（每个编号只报一次）
    defined = set(re.findall(r"(?m)^\s*\[\^([^\]\s]+)\]:", text))
    reported: set[str] = set()
    for i, line in enumerate(lines, 1):
        for m in re.finditer(r"\[\^([^\]\s]+)\](?!:)", line):
            key = m.group(1)
            if key in defined or key in reported:
                continue
            reported.add(key)
            issues.append(Issue(
                rule="F-01",
                severity=Severity.ERROR,
                message=f"悬空脚注：正文里的 [^{key}] 没有对应的脚注内容",
                line=i,
                context=line.strip()[:80],
                suggestion="补上脚注内容，或改成 [N] 引用；Word 版没有页下脚注，不要写 [^n]",
            ))

    return issues


_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_TEX_HEADING = re.compile(r"\\(?:part|chapter|section|subsection|subsubsection)\*?\s*(?:\[[^\]]*\])?\s*\{(.+?)\}\s*$")


def _heading_titles(lines: list[str]) -> list[str]:
    titles = []
    for line in lines:
        m = _MD_HEADING.match(line) or _TEX_HEADING.search(line.strip())
        if m:
            titles.append(m.group(1).strip())
    return titles


def _heading_level(line: str) -> Optional[int]:
    m = re.match(r"^\s{0,3}(#{1,6})\s+\S", line)
    if m:
        return len(m.group(1))
    m = re.match(r"^\s*\\(part|chapter|section|subsection|subsubsection)\*?\s*[\[{]", line)
    if m:
        return {"part": 0, "chapter": 1, "section": 2, "subsection": 3, "subsubsection": 4}[m.group(1)]
    return None


def check_heading_consistency(text: str) -> list[Issue]:
    """检查标题编号体系是否一致"""
    issues: list[Issue] = []
    lines = text.split("\n")

    has_chinese_heading = False  # 第一章、第二章
    has_number_heading = False   # 1、2、1.1

    # 只看真正的标题（Markdown 的 # 行、LaTeX 的 \chapter/\section 标题），正文里"1 年后"这类行不算
    for title in _heading_titles(lines):
        if re.match(r"^第[一二三四五六七八九十百\d]+[章节]", title):
            has_chinese_heading = True
        if re.match(r"^\d+(\.\d+)*\s+\S", title):
            has_number_heading = True

    if has_chinese_heading and has_number_heading:
        issues.append(Issue(
            rule="F-04",
            severity=Severity.WARNING,
            message="标题编号体系混用：同时使用了「第X章」和数字编号",
            suggestion="选择一种体系并全文统一",
        ))

    return issues


# ═══════════════════════════════════════════════════════
# 第四类：学术语体检查
# ═══════════════════════════════════════════════════════

def check_register(text: str) -> list[Issue]:
    """检查学术语体问题"""
    issues: list[Issue] = []
    lines = text.split("\n")

    informal_patterns = [
        (r"其实(?!际|质|现|验|施|力|例|测|证|体|物)", "学术论文中一般不用「其实」，建议改为「实际上」或直接陈述"),
        (r"说白了", "过于口语化，建议删除或改为学术表述"),
        (r"大家都知道", "建议改为「学界普遍认为」并附引用"),
        (r"很明显", "建议用具体论证替代「很明显」"),
        (r"当然了", "建议改为「诚然」或「固然」"),
        (r"这个问题很有意思", "建议直接说明问题的学术意义"),
        (r"笔者觉得", "建议改为「笔者认为」或「本文认为」"),
        (r"总之就是", "过于口语化，直接写出结论句即可（不必加「综上所述」一类收束词）"),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, suggestion in informal_patterns:
            if re.search(pattern, line):
                issues.append(Issue(
                    rule="S-01",
                    severity=Severity.WARNING,
                    message=f"语体问题：使用了口语化表述「{re.search(pattern, line).group()}」",
                    line=i,
                    context=line.strip()[:80],
                    suggestion=suggestion,
                ))

    return issues


def check_self_reference(text: str) -> list[Issue]:
    """检查自称用法是否统一"""
    issues: list[Issue] = []
    lines = text.split("\n")

    refs_found: dict[str, list[int]] = {}
    for i, raw_line in enumerate(lines, 1):
        # 引文里的"我们""我认为"是被引的人说的，不是作者自称：去掉中文引号内容和引文块
        if raw_line.lstrip().startswith(">"):
            continue
        line = re.sub(r"“[^”]*”|「[^」]*」|『[^』]*』", "", raw_line)
        for ref in ["笔者", "本文", "本研究", "我们"]:
            if ref in line:
                refs_found.setdefault(ref, []).append(i)
        # "我"用正向匹配——只匹配真正作为自称的用法
        if re.search(r"我(?:认为|以为|将|的|在本|试图|倾向于|主张|发现)", line):
            refs_found.setdefault("我", []).append(i)

    if len(refs_found) > 2:
        terms = ", ".join(f"「{k}」" for k in refs_found)
        issues.append(Issue(
            rule="S-02",
            severity=Severity.WARNING,
            message=f"自称用法不统一：同时使用了 {terms}",
            suggestion="建议全文统一使用「本文」或「笔者」",
        ))

    return issues


# ═══════════════════════════════════════════════════════
# 第五类：结构完整性检查
# ═══════════════════════════════════════════════════════

def check_structure(text: str) -> list[Issue]:
    """检查论文基本结构要素是否完整"""
    issues: list[Issue] = []

    # 不分大小写；LaTeX 的 thebibliography、\bibliography、\printbibliography 也算有参考文献。
    # 缺参考文献是警告（技能用 --severity warning 调用，info 会被滤掉）；摘要、关键词按学校或课程要求，只提示
    checks = [
        ("摘要", r"摘\s*要|(?i:abstract)", "论文缺少摘要", Severity.INFO),
        ("关键词", r"关键词|关键字|(?i:key\s*words?|index\s+terms)", "论文缺少关键词", Severity.INFO),
        ("参考文献", r"参考文献|引用文献|(?i:references|bibliography)", "论文缺少参考文献", Severity.WARNING),
    ]

    for name, pattern, msg, severity in checks:
        if not re.search(pattern, text):
            issues.append(Issue(
                rule="ST-01",
                severity=severity,
                message=msg,
                suggestion=f"检查是否遗漏了{name}部分",
            ))

    # 检查引言是否有明确的论点句：按真正的标题（# 行、\section）找引言，到下一个同级或更高级标题为止；
    # 没有标题的纯文本才退回旧写法
    intro_section = ""
    lines = text.split("\n")
    intro_level = None
    for line in lines:
        level = _heading_level(line)
        if intro_level is None:
            if level is not None and re.search(r"引言|绪论|导论|导言|问题的提出|Introduction", line):
                intro_level = level
            continue
        if level is not None and level <= intro_level:
            break
        intro_section += line + "\n"
    if intro_level is None and not _heading_titles(lines):
        in_intro = False
        for line in lines:
            if re.search(r"引言|绪论|导论|Introduction", line):
                in_intro = True
                continue
            if in_intro:
                if re.match(r"^(第[一二三]|[一二三]、|\d+[\s.])", line.strip()):
                    break
                intro_section += line + "\n"

    if intro_section:
        thesis_indicators = ["本文论证", "本文认为", "本文试图", "本文旨在",
                             "本研究认为", "笔者认为", "本文的核心论点"]
        has_thesis = any(ind in intro_section for ind in thesis_indicators)
        if not has_thesis:
            issues.append(Issue(
                rule="ST-02",
                severity=Severity.WARNING,
                message="引言中未发现明确的论点句",
                suggestion="引言末尾应有一句明确的论点陈述（如「本文论证……」）",
            ))

    return issues


# ═══════════════════════════════════════════════════════
# 第六类：论证逻辑检查
# ═══════════════════════════════════════════════════════

# 论证连接词库——出现这些词意味着句子间有逻辑关系
_CONNECTORS = {
    # 因果
    "因此", "所以", "故而", "由此可见", "正因为", "之所以", "因为", "由于",
    "这意味着", "这说明", "这表明", "可见",
    # 转折
    "然而", "但是", "不过", "尽管如此", "虽然", "但", "却",
    # 递进
    "不仅如此", "更重要的是", "进一步", "更为关键的是", "而且",
    "在此基础上", "由此出发",
    # 对比
    "相比之下", "与之不同", "相反", "反之", "另一方面",
    # 论证动作
    "换言之", "也就是说", "具体而言", "之所以这样说",
    "这一点可以从", "从中可以看出",
}
# "值得注意的是"不算论证连接：写作规则把它列为套话，这里再奖励它等于鼓励 AI 腔

# 并列堆砌信号——连续出现这些开头意味着只是在罗列而非论证
_LISTING_SIGNALS = [
    r"^同时[,，]",
    r"^此外[,，]",
    r"^另外[,，]",
    r"^还有[,，]",
    r"^也[,，]",
    r"^并且[,，]",
    r"^以及",
]


def check_argumentation_logic(text: str) -> list[Issue]:
    """检测论证逻辑断裂：句间/段间/章节间缺乏论证连接"""
    issues: list[Issue] = []
    lines = text.split("\n")

    # ── 检查一：段落内部的连续断言（只论不证） ──
    # 如果一个段落里连续3句以上都没有论证连接词，可能是在堆砌断言
    para_lines: list[tuple[int, str]] = []  # (行号, 内容)
    paragraphs: list[list[tuple[int, str]]] = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            if para_lines:
                paragraphs.append(para_lines[:])
                para_lines.clear()
        else:
            # 跳过标题行、引用块、参考文献
            if re.match(r"^(#|>|\[|第[一二三四五六七八九十]+|[\d]+\.)", stripped):
                if para_lines:
                    paragraphs.append(para_lines[:])
                    para_lines.clear()
                continue
            para_lines.append((i, stripped))
    if para_lines:
        paragraphs.append(para_lines[:])

    for para in paragraphs:
        if len(para) < 4:
            continue

        # 将段落按句号分句
        sentences: list[tuple[int, str]] = []
        for line_no, line_text in para:
            for sent in re.split(r"[。！？]", line_text):
                sent = sent.strip()
                if len(sent) > 5:
                    sentences.append((line_no, sent))

        if len(sentences) < 4:
            continue

        # 检查是否有连续4句以上没有任何论证连接词
        consecutive_no_connector = 0
        max_streak = 0
        streak_start_line = 0

        for line_no, sent in sentences:
            has_connector = any(c in sent for c in _CONNECTORS)
            if has_connector:
                consecutive_no_connector = 0
            else:
                if consecutive_no_connector == 0:
                    streak_start_line = line_no
                consecutive_no_connector += 1
                max_streak = max(max_streak, consecutive_no_connector)

        if max_streak >= 4:
            issues.append(Issue(
                rule="L-01",
                severity=Severity.WARNING,
                message=f"段落中连续 {max_streak} 句缺少论证连接（第{streak_start_line}行附近）",
                line=streak_start_line,
                context=para[0][1][:60] + "...",
                suggestion="检查这些句子之间是否缺少因果、转折、递进等逻辑关系。"
                           "如果是在罗列观察，考虑用「这意味着……」「之所以……是因为……」"
                           "等表述补充论证",
            ))

    # ── 检查二：并列堆砌（只证不论） ──
    # 连续3个以上段落以"同时""此外""另外"开头，说明在堆砌而非推进
    listing_streak = 0
    listing_start_line = 0

    for para in paragraphs:
        if not para:
            continue
        first_sent = para[0][1]
        is_listing = any(re.match(p, first_sent) for p in _LISTING_SIGNALS)
        if is_listing:
            if listing_streak == 0:
                listing_start_line = para[0][0]
            listing_streak += 1
        else:
            if listing_streak >= 3:
                issues.append(Issue(
                    rule="L-02",
                    severity=Severity.WARNING,
                    message=f"连续 {listing_streak} 个段落以并列词开头（第{listing_start_line}行起）",
                    line=listing_start_line,
                    suggestion="并列结构适合罗列现象，但学术论文需要递进论证。"
                               "考虑将这些段落重组为「提出观察→分析原因→得出推论」的递进结构",
                ))
            listing_streak = 0
    # 处理末尾
    if listing_streak >= 3:
        issues.append(Issue(
            rule="L-02",
            severity=Severity.WARNING,
            message=f"连续 {listing_streak} 个段落以并列词开头（第{listing_start_line}行起）",
            line=listing_start_line,
            suggestion="并列结构适合罗列现象，但学术论文需要递进论证。"
                       "考虑将这些段落重组为「提出观察→分析原因→得出推论」的递进结构",
        ))

    # ── 检查三：引文后缺少分析（只引不论） ──
    # 检测模式：引了一段材料（用引号或书名号标记），但紧接着就跳到了下一个观点
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        # 检测一句话以引文结尾，但没有跟上分析
        ends_with_quote = bool(re.search(r'["”」』][\s。]*$', stripped))
        if ends_with_quote:
            # 看下一个非空行
            next_content = ""
            for j in range(i, min(i + 3, len(lines))):
                nl = lines[j].strip() if j < len(lines) else ""
                if nl:
                    next_content = nl
                    break

            if next_content:
                # 如果下一句也是引文开头，或者是一个新的论述（没有分析当前引文）
                starts_new_topic = bool(re.match(
                    r"^(此外|同时|另外|与此同时|除此之外|值得一提的是|值得注意的是|[\"“「『])",
                    next_content,
                ))
                if starts_new_topic:
                    issues.append(Issue(
                        rule="L-03",
                        severity=Severity.WARNING,
                        message="引文后可能缺少分析：引用结束后直接跳到了新话题",
                        line=i,
                        context=stripped[:60],
                        suggestion="引文之后应紧跟对引文的分析——"
                                   "这段引文说明了什么？它如何支撑你的论点？",
                    ))

    # ── 检查四：章节之间缺少过渡 ──
    # 检查每个章节标题前面的最后一段是否有收束，标题后面是否有承接
    chapter_heading_lines: list[int] = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.match(r"^(第[一二三四五六七八九十]+[章节]|#{1,3}\s+\d|#{1,3}\s*第[一二三四五六七八九十百\d]+[章节]|\\(?:chapter|section)\*?\s*[\[{])", stripped):
            chapter_heading_lines.append(i)

    for idx, heading_line in enumerate(chapter_heading_lines):
        if idx == 0:
            continue  # 第一章不需要检查前面的过渡

        # 检查标题后面第一段是否直接从理论定义或背景介绍开始
        first_para_start = ""
        for j in range(heading_line, min(heading_line + 5, len(lines))):
            if j < len(lines):
                nl = lines[j - 1].strip()  # 0-indexed
                if nl and not re.match(r"^(第|#|\d+\.|\\(?:chapter|section|label))", nl):
                    first_para_start = nl
                    break

        if first_para_start:
            bad_starts = [
                r"^[A-Z\u4e00-\u9fff]+（.*?）是",  # "福柯（Michel Foucault）是..."
                r"^在\d{4}年",                       # "在1975年..."
                r"^关于.{2,6}的研究",                 # "关于X的研究..."
            ]
            for pattern in bad_starts:
                if re.match(pattern, first_para_start):
                    issues.append(Issue(
                        rule="L-04",
                        severity=Severity.INFO,
                        message="章节开头可能缺少与上一章的逻辑衔接",
                        line=heading_line,
                        context=first_para_start[:60],
                        suggestion="章节开头建议从上一章留下的问题或张力切入，"
                                   "而不是直接从背景介绍或理论定义开始",
                    ))
                    break

    return issues


def check_argumentation_depth(text: str) -> list[Issue]:
    """深层论证检查：预设前提未论证、因果链跳跃、叙述淹没论点、结尾堆砌"""
    issues: list[Issue] = []
    lines = text.split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            continue

        # ── L-05：预设前提未论证 ──
        # 检测"由于A，所以B"结构中A是一个强判断而非事实
        # 模式：由于/因为/鉴于 + 强判断词 + 无引用支撑
        causal_premise_patterns = [
            # "由于X并非/不是Y"——否定性前提常常是未论证的主观判断
            (r"(由于|因为|鉴于)(.{4,30})(并非|不是|并不|并未|未必是|绝非)", "前提中的否定性判断"),
            # "由于X所认为的Y"——把主观判断嵌入因果前提
            (r"(由于|因为|鉴于)(.{2,15})(所认为的|所谓的|所理解的)", "前提中嵌入了主观判断"),
        ]
        for pattern, desc in causal_premise_patterns:
            m = re.search(pattern, stripped)
            if m:
                # 检查这个前提附近是否有引用支撑
                context_window = stripped[max(0, m.start()-20):m.end()+40]
                has_citation = bool(re.search(
                    r"[①②③④⑤⑥⑦⑧⑨⑩]|\[\d+\]|（.*?\d{4}.*?）", context_window
                ))
                if not has_citation:
                    issues.append(Issue(
                        rule="L-05",
                        severity=Severity.WARNING,
                        message=f"因果前提可能未论证：{desc}，但未见引用或论证支撑",
                        line=i,
                        context=stripped[:80],
                        suggestion="「由于/因为」引导的前提如果包含价值判断，"
                                   "需要先论证这个前提成立，再用它推导结论",
                    ))
                break

        # ── L-06：叙述比例失衡 ──
        # 检测超长句子中叙事成分远多于分析成分
        # 信号：一句话超过100字，且包含大量动作动词但缺少分析动词
        sentences = re.split(r"[。！？]", stripped)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 100:
                continue

            narrative_verbs = len(re.findall(
                r"(?:发生|出现|建立|成立|颁布|发动|开始|结束|到达|返回|"
                r"出版|发表|签署|宣布|任命|组建|迁移|抵达|爆发|"
                r"写道|记载|描述|讲述|描绘|记录|引述|转述|复述|"
                r"设置|进入|离开|逃离|攻打|占领|投降|撤退)",
                sent,
            ))
            analytic_verbs = len(re.findall(
                r"(?:表明|说明|揭示|意味着|体现|反映|证明|论证|暗示|"
                r"可见|因此|由此|换言之|之所以|正因为|由此可见|"
                r"呈现出|构成了|指向了|折射出|回应了|挑战了|颠覆了)",
                sent,
            ))
            if narrative_verbs >= 4 and analytic_verbs == 0:
                issues.append(Issue(
                    rule="L-06",
                    severity=Severity.INFO,
                    message="长句中叙述成分可能过多，缺少分析性表述",
                    line=i,
                    context=sent[:80] + "...",
                    suggestion="考虑将叙事部分压缩，或在叙述后立即跟上分析"
                               "（这意味着什么？为什么这个细节重要？）",
                ))

        # ── L-07：结尾概念堆砌 ──
        # 检测以"由此可见""综上所述"等收束词开头的句子中
        # 用顿号连接了过多未在前文展开的概念
        summary_starters = ["由此可见", "综上所述", "综上", "总之", "概言之", "可见"]
        for starter in summary_starters:
            if starter in stripped:
                # 找到收束词之后的内容
                idx = stripped.index(starter)
                after_summary = stripped[idx:]

                # 数顿号连接的并列项
                enumeration_match = re.findall(r"[、]", after_summary)
                if len(enumeration_match) >= 4:
                    issues.append(Issue(
                        rule="L-07",
                        severity=Severity.WARNING,
                        message=f"总结句中堆砌了 {len(enumeration_match)+1} 个以上并列概念",
                        line=i,
                        context=after_summary[:80],
                        suggestion="总结不应引入前文未充分展开的新概念。"
                                   "检查这些并列项是否都在前文得到了论证——"
                                   "如果没有，要么删去，要么补充论证",
                    ))
                break

        # ── L-08：强度词缺乏支撑 ──
        # 检测"显然""极其""无疑"等词紧跟在只有一个论据的推理之后
        # R3-01 已经报过的（毫无疑问、必然地……）不重复报
        masked = re.sub(r"毫无疑问|毋庸置疑|必然地|确凿无疑", lambda mm: "　" * len(mm.group()), stripped)
        intensity_words = re.findall(
            r"(显然|极其|无疑|不言自明)",
            masked,
        )
        for word in intensity_words:
            word_idx = masked.index(word)
            # 检查强度词所在句子附近是否有多重论据（"首先、其次"只是列举，不算论据）
            surrounding = stripped[max(0, word_idx-60):word_idx+60]
            evidence_markers = len(re.findall(
                r"(不仅|而且|一方面|另一方面|例如|比如|根据|据)",
                surrounding,
            ))
            if evidence_markers < 2:
                issues.append(Issue(
                    rule="L-08",
                    severity=Severity.WARNING,
                    message=f"强断言「{word}」附近未见充分的论据支撑",
                    line=i,
                    context=surrounding.strip()[:80],
                    suggestion=f"「{word}」暗示结论不证自明，但学术论文中应当"
                               "展示推理过程。建议删去强度词，或补充多重论据",
                ))

    return issues


# ═══════════════════════════════════════════════════════
# 汇总执行
# ═══════════════════════════════════════════════════════

ALL_CHECKS = [
    check_fabricated_references,
    check_unsupported_claims,
    check_terminology_consistency,
    check_citation_format,
    check_heading_consistency,
    check_register,
    check_self_reference,
    check_structure,
    check_argumentation_logic,
    check_argumentation_depth,
]


# 按学科关掉不适用的规则：史学本来就以叙述史实为主（L-06 叙述比例）；法学章节常从概念界定起笔（L-04）
DISCIPLINE_OFF = {
    "history": {"L-06"},
    "law": {"L-04"},
}


def run_all_checks(text: str, discipline: Optional[str] = None) -> list[Issue]:
    """执行所有检查规则，返回按严重程度排序的问题列表"""
    issues: list[Issue] = []
    off = DISCIPLINE_OFF.get(discipline or "", set())
    for check_fn in ALL_CHECKS:
        try:
            issues.extend(issue for issue in check_fn(text) if issue.rule not in off)
        except Exception as e:
            logger.warning("Review rule %s failed: %s", check_fn.__name__, e)

    # 按严重程度排序：error > warning > info
    severity_order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
    issues.sort(key=lambda x: (severity_order.get(x.severity, 9), x.line))
    return issues


# ═══════════════════════════════════════════════════════
# CLI 入口（改编自原项目 scripts/review.py）
# ═══════════════════════════════════════════════════════
import argparse
import sys
import json


def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def review(text: str, min_severity: str = "info", discipline: Optional[str] = None) -> list:
    """评估文本，返回问题列表（供 Agent 以模块方式调用）。"""
    issues = run_all_checks(text, discipline)
    severity_order = {"error": 0, "warning": 1, "info": 2}
    threshold = severity_order.get(min_severity, 2)
    return [i for i in issues if severity_order.get(i.severity.value, 2) <= threshold]


def _render_text(issues, text: str) -> str:
    if not issues:
        return "✓ 未发现问题。\n"
    ec = sum(1 for i in issues if i.severity == Severity.ERROR)
    wc = sum(1 for i in issues if i.severity == Severity.WARNING)
    ic = sum(1 for i in issues if i.severity == Severity.INFO)
    lines = [f"评估完成：{ec} 个错误 / {wc} 个警告 / {ic} 个提示",
             f"文本总行数：{len(text.splitlines())}", ""]
    icon = {Severity.ERROR: "✗ [错误]", Severity.WARNING: "⚠ [警告]", Severity.INFO: "ℹ [提示]"}
    for it in issues:
        loc = f"第{it.line}行" if it.line else ""
        lines.append(f"{icon.get(it.severity, '?')} {it.rule} {loc}")
        lines.append(f"  {it.message}")
        if it.context:
            lines.append(f"  上下文：{it.context}")
        if it.suggestion:
            lines.append(f"  建议：{it.suggestion}")
        lines.append("")
    return "\n".join(lines)


def _render_json(issues) -> str:
    return json.dumps({
        "total": len(issues),
        "errors": sum(1 for i in issues if i.severity == Severity.ERROR),
        "warnings": sum(1 for i in issues if i.severity == Severity.WARNING),
        "info": sum(1 for i in issues if i.severity == Severity.INFO),
        "issues": [i.to_dict() for i in issues],
    }, ensure_ascii=False, indent=2)


def _profile_discipline() -> Optional[str]:
    """当前目录（工作区根目录）里写作档案的学科；没有就是 None。"""
    try:
        with open(os.path.join(".mh", "writing_spec.json"), "r", encoding="utf-8") as f:
            profile = (json.load(f) or {}).get("profile") or {}
        value = profile.get("discipline")
        return value if isinstance(value, str) else None
    except (OSError, ValueError, AttributeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="人文社科论文文本评估工具",
                                     epilog="退出码：0 没有错误级问题；1 有错误级问题。")
    parser.add_argument("input", help="待评估文件路径，或 - 表示 stdin")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--severity", choices=["error", "warning", "info"], default="info",
                        help="最低显示级别")
    parser.add_argument("--discipline", help="学科（history、law……），按学科关掉不适用的规则；默认读 .mh/writing_spec.json")
    args = parser.parse_args()
    text = _read_input(args.input)
    issues = review(text, min_severity=args.severity, discipline=args.discipline or _profile_discipline())
    print(_render_json(issues) if args.format == "json" else _render_text(issues, text))
    return 1 if any(issue.severity == Severity.ERROR for issue in issues) else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
