"""一条命令跑完「给题目 → 一等奖论文」的七步链，每步带机器闸门，可断点续跑。

## 为什么要有这个文件

`RUNBOOK.md` 把 13 人建稿队、10 人审阅队、九道验收门全写清楚了，但它是**给人读的**：
每一步要不要往下走，靠人读产物判断。`run_squad.py` 只解决了「八波派单」，
`run_review.py` 只解决了「评审派单」，两者之间**没有状态机**：

- 跑到第 3 波失败，重来时前两波会重派一遍（烧钱、还会覆盖已经对好的产物）；
- 「这一步到底算不算过」没有机器答案，只有人肉读 md；
- 换一台机器 / 换一个会话，不知道上次做到哪。

这个脚本补的就是这一层：**七步状态机 + 每步的机器闸门 + 断点续跑**。

## 七步是怎么来的

对应 `comp_shuwei` / `comp_shuwei_en` 那套七步流水线（赛题分析 → 建模求解 →
编程实现 → 图表生成 → 流程与架构图 → 竞赛论文撰写 → 编译与合规检查）。
那边每步的产物契约藏在加密技能正文里拿不到；这里**用本机已有的 13 人建稿队 +
10 人审阅队 + 九道门重新定义一遍**，契约写在 `crew.OUTPUT_OF` 与下面的 GATES 里。

步骤 → 成员 → 闸门：

    s1 赛题分析    题目侦察手、数据溯源手              G1 G2
    s2 建模求解    建模架构手                          G3
    s3 编程实现    求解与优化手、代理模型训练手、数值对账手  G4 G5
    s4 图表        图表手                              G6
    s5 论文撰写    论文撰写手                          G7
    s6 编译合规    编译 + 格式合规手                    G8
    s7 评审收口    10 人审阅队（9+1 两波）              G9

## 闸门的三种返回值

`True` 过、`False` 不过、`None` 判不出（缺文件 / 缺依赖）。**`None` 不许当通过** ——
这是 `mmkit/review_bench.py` 定下的规矩，这里照抄：判不出就得说判不出，
否则「机器没报错」会被误读成「这一步没问题」。

## 用法

    $PY = 'python'
    $S  = '<skill>\scripts\pipeline.py'

    & $PY $S <论文目录> --status              # 看做到哪一步、每道门什么结果
    & $PY $S <论文目录> --dry                 # 只打印计划，不派单
    & $PY $S <论文目录>                       # 从第一个未过的步骤接着跑
    & $PY $S <论文目录> --step s3             # 只跑到 s3（含）
    & $PY $S <论文目录> --only s4             # 只跑 s4
    & $PY $S <论文目录> --force s4            # 已过的步骤也重跑
    & $PY $S <论文目录> --skip-dispatch       # 只跑机器闸门，不派单（改完稿自查用）

退出码：0 = 走到指定步骤且全过；1 = 有门没过；2 = 环境不全（缺解释器/缺目录/缺名册）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from mmkit import crew, paths  # noqa: E402
from mmkit import pyexe  # noqa: E402
from mmkit import review_crew as RC  # noqa: E402
import submission_gate as SG  # noqa: E402  （G10–G15 的实现在那里，这里只做编排）

PY = Path(pyexe.py())
STATE_NAME = "logs/pipeline_state.json"

# 状态文件带上"这些键属于哪一版步骤表"。2026-11-18 把 7 步扩成 8 步时，s4 从"图表"变成
# "口径审计"，旧状态里的 s4=done 会被新表读成"口径审计已做完"——这是会骗人的假绿。
# 版本对不上就整份作废（旧文件先备份成 .v1.bak），从零开始重派。
#
# v4（2026-11-19）：s1 加第 18 名成员「真题对标手」与第 20 道门 G20。
# 为什么这一改必须升版本：run_step 对 status=="done" 的步骤整步跳过，跳过的步骤
# **不会去判它新加的闸门**，于是老状态里的 s1 会让 G20 永远不出现，而 G19 又会把
# 「非软闸门留了判不出的」判成 FAIL——一份跑完的稿子突然变红。宁可作废重派。
STATE_SCHEMA = 4

# 状态词表三值 + 一个显式的「不适用」。
# 为什么要有 NA：2026-11-18 那一轮里 G10（没 TABLE_*）、G11（视觉模型额度用完）、
# G14（没上传模板）常年打 `??`，汇报时混在 PASS 中间，看不出「今天有三门其实没判」。
# NA 与 `??` 的区别是语义：NA = 这道门对本题结构上不适用（有据可查），
# `??` = 该判但判不出（工具崩了、缺依赖）。前者不拦且单独列出，后者仍然只对软闸门放行。
NA = "NA"
MARK = {True: "PASS", False: "FAIL", None: " ?? ", NA: " NA "}


# ---------------------------------------------------------------- 步骤定义

@dataclass
class Step:
    key: str
    title: str
    members: list[str] = field(default_factory=list)
    gates: list[str] = field(default_factory=list)
    review: bool = False          # True = 走审阅小队而不是建稿小队
    compile_first: bool = False   # True = 派单前先编译一遍（合规手要读新 PDF）


STEPS: list[Step] = [
    Step("s1", "赛题分析", ["题目侦察手", "数据溯源手", "真题对标手"], ["G1", "G2", "G20"]),
    Step("s2", "建模求解", ["建模架构手"], ["G3"]),
    Step("s3", "编程实现", ["求解与优化手", "代理模型训练手", "数值对账手"], ["G4", "G5", "G10"]),
    Step("s4", "口径审计", ["口径审计手"], ["G16"]),
    Step("s5", "图表", ["图表手"], ["G6", "G11"]),
    Step("s6", "论文撰写", ["论文撰写手", "附录与自指手"], ["G7", "G12", "G17"]),
    Step("s7", "编译合规", ["格式合规手", "版式与出栏手", "流水线运维手"],
         ["G8", "G13", "G14", "G15", "G18", "G19"], compile_first=True),
    Step("s8", "评审收口", [], ["G9"], review=True),
]


# ---------------------------------------------------------------- 状态读写

def load_state(paper: Path) -> dict:
    p = paper / STATE_NAME
    if p.exists():
        try:
            st = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            st = {}
        if st.get("schema") != STATE_SCHEMA:
            bak = p.with_suffix(f".v{st.get('schema', 1)}.bak")
            try:
                if not bak.exists():
                    bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError:
                pass
            print(f"  （步骤表改版：旧状态 schema={st.get('schema')} 已作废并备份为 {bak.name}）")
            return {"schema": STATE_SCHEMA}
        return st
    return {"schema": STATE_SCHEMA}


def save_state(paper: Path, st: dict) -> None:
    p = paper / STATE_NAME
    p.parent.mkdir(parents=True, exist_ok=True)
    st["schema"] = STATE_SCHEMA
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- 小工具

def _run(argv: list[str], cwd: Path, timeout: int = 1800) -> tuple[int, str]:
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    env["PYTHONPATH"] = str(SCRIPTS) + (";" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        r = subprocess.run([str(a) for a in argv], cwd=str(cwd), capture_output=True,
                           timeout=timeout, env=env)
    except Exception as exc:                                  # noqa: BLE001
        return 1, f"<{type(exc).__name__}: {exc}>"
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    return r.returncode, out.strip()


def _md_gate(paper: Path, rel: str, judgment: bool = False) -> tuple[bool | None, str]:
    """Markdown 产物闸门：存在 + 有 VERDICT/NOT-APPLICABLE + 过最小内容判据。

    `judgment=True` 表示这份产物是**判断型**的（审计、评审、创新挖掘）——它记录的是
    「当时那份稿子有什么问题」。稿子一改，结论就过期了，拿它判新稿是假证据。
    所以判断型产物加一道时效判据：比稿子旧就判 `NA`（不适用），而不是 PASS/FAIL。
    数据型产物（解题输出、图表清单）不加：它们本身就是最新执行结果。
    """
    p = paper / rel
    if not p.exists() or p.stat().st_size == 0:
        return None, f"缺 {rel}"
    txt = p.read_text(encoding="utf-8", errors="replace")
    head = "\n".join(txt.splitlines()[:8])
    # HOUSE 契约允许「不适用」：首部写 NOT-APPLICABLE: <理由> 即算交付
    if "NOT-APPLICABLE:" in head:
        why = next((l for l in txt.splitlines() if "NOT-APPLICABLE:" in l), "")
        return True, f"{rel} NOT-APPLICABLE  {why.strip()[:70]}"
    if judgment:
        stale = _stale_minutes(paper, p)
        if stale is not None and stale > JUDGMENT_STALE_MIN:
            return NA, (f"{rel} 比稿子旧 {stale:.0f} 分钟（>{JUDGMENT_STALE_MIN:.0f}），"
                        f"结论按过时处理；重跑这一步再判")
    if "VERDICT: PASS" in txt:
        bad = crew._bad_bytes_line(p, txt) if hasattr(crew, "_bad_bytes_line") else None
        if bad:
            return False, bad
        return True, f"{rel} {p.stat().st_size} B, VERDICT: PASS"
    if "VERDICT: FAIL" in txt:
        return False, f"{rel} 自报 VERDICT: FAIL"
    if "VERDICT:" not in txt:
        return False, f"{rel} 没有 VERDICT 行"
    return None, f"{rel} VERDICT 行无法判定"


# 判断型产物的过期阈值（分钟）。给 5 分钟余量：改稿与重判之间常常只隔一条命令。
JUDGMENT_STALE_MIN = 5.0


def _stale_minutes(paper: Path, artifact: Path) -> float | None:
    """产物比「它该判的东西」旧多少分钟。None = 没有可比的锚点。"""
    anchors: list[float] = []
    for pat in ("main.tex", "main.pdf", "figures/*.pdf", "code/*.py", "data/*.json"):
        for f in paper.glob(pat):
            try:
                anchors.append(f.stat().st_mtime)
            except OSError:
                pass
    if not anchors:
        return None
    try:
        return (max(anchors) - artifact.stat().st_mtime) / 60.0
    except OSError:
        return None


def _count(pattern: str, root: Path) -> int:
    return len(list(root.glob(pattern))) if root.exists() else 0


# ---------------------------------------------------------------- 九道门

def gate_g1(paper: Path) -> tuple[bool | None, str]:
    return _md_gate(paper, crew.OUTPUT_OF["题目侦察手"])


def gate_g2(paper: Path) -> tuple[bool | None, str]:
    """数据台账：两种合法形态，任取其一。

    1. `records` 非空，每条带出处(url/source) + sha256 + fetched_at —— 真抓了外部数据。
    2. `status: NOT-APPLICABLE` + `not_applicable_line` + `status_reason` +
       `attachment_baseline` 非空 —— 题面附件已给全外生常量，确实无需外部数据。

    为什么要放行第 2 种：`crew._too_small()` 只认第 1 种（它的注释写着"台账 records 为空
    （只留了 new_verify 的空壳）"），但 HOUSE 契约本身允许 `NOT-APPLICABLE: <理由>`。
    2026_C 实测撞上：数据溯源手核了题面 34 条常量、逐条标了行号、写了 300 字理由，
    `_too_small` 仍判"空壳"，于是 W0 白等 1500 秒超时。那是闸门判据的缺陷，不是成员的活没干。
    """
    p = paper / "data" / "ledger.json"
    if not p.exists():
        return None, "缺 data/ledger.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"ledger.json 不是合法 JSON：{exc}"
    # 两代台账都用过：`records`（crew 契约）与 `entries`（EXAM_2023C 这批的 fetch 脚本）。
    # 只认一个键会把「真抓了 14 条、每条带 url+sha256+fetched_at」的台账判成空壳。
    recs = d.get("records") or d.get("entries") or []
    if recs:
        bad = [r for r in recs
               if not (r.get("url") or r.get("source") or r.get("api"))
               or not r.get("sha256") or not r.get("fetched_at")]
        if bad:
            return False, f"{len(bad)}/{len(recs)} 条记录缺 出处/sha256/fetched_at"
        return True, f"{len(recs)} 条记录，全带出处+sha256+fetched_at"

    # 第 2 种形态：显式声明不适用，且给出可核对的理由与基线
    status = str(d.get("status") or "").upper()
    reason = str(d.get("status_reason") or "").strip()
    na_line = str(d.get("not_applicable_line") or "").strip()
    base = d.get("attachment_baseline")
    n_base = len(base) if isinstance(base, (list, dict)) else 0
    # 2026_C 事故：成员把 not_applicable_line 写在专用字段里，status 仍写 PASS（那是台账自身的
    # 构建状态，不是适用性）。闸门只认 status=="NOT-APPLICABLE"，于是把一份逐条核过 34 条常量、
    # 写了 314 字理由的台账判成"空壳"。判据改成：只要 NA 声明三件套齐备，status 写什么不重要。
    if na_line.startswith("NOT-APPLICABLE") and status in ("NOT-APPLICABLE", "PASS"):
        if not na_line.startswith("NOT-APPLICABLE"):
            return False, "status=NOT-APPLICABLE 但缺 not_applicable_line"
        if len(reason) < 80:
            return False, f"NOT-APPLICABLE 的理由只有 {len(reason)} 字，不足以核对"
        if n_base == 0:
            return False, "NOT-APPLICABLE 但 attachment_baseline 为空（没有可核对的常量表）"
        return True, f"NOT-APPLICABLE（题面附件已给 {n_base} 条常量，理由 {len(reason)} 字）"
    return False, f"records 为空且未声明 NOT-APPLICABLE（status={status or '缺失'}）"


def gate_g3(paper: Path) -> tuple[bool | None, str]:
    return _md_gate(paper, crew.OUTPUT_OF["建模架构手"])


def gate_g4(paper: Path) -> tuple[bool | None, str]:
    return _md_gate(paper, crew.OUTPUT_OF["求解与优化手"])


def _tex_is_skeleton(paper: Path) -> bool:
    """`main.tex` 还是骨架吗（`new_paper.py` 留下的 `<<…>>` 占位 ≥5 个）。

    为什么需要这个判据：2023B 压测实测，s3 的 `verify_numbers.py` 同时管两件事——
    (a) 数据层自洽（`declared == checked`、`json_fail == 0`）；
    (b) 正文绑定（每个声明数字在 `main.tex` 里找得到，`tex_bound == declared`）。
    (b) 在 s3 结构上**不可能**成立：`main.tex` 要到 s6 才由论文撰写手填，
    s3 时它是 69 个 `<<…>>` 的空壳。旧 G5 把 (b) 的 76 条 miss 当失败，
    于是每一步都红、整条流水线卡在 s3（实测 `tex_bound=0/76`，
    报告自己也写了 "root cause: main.tex is still the skeleton"）。
    分工改成：G5 只判 (a)，(b) 归 G12（s6，那时正文已写完）。
    """
    p = paper / "main.tex"
    if not p.exists():
        return True
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True
    return t.count("<<") >= 5


def gate_g5(paper: Path) -> tuple[bool | None, str]:
    """对账器（**数据层**）：声明数与核对数一致、JSON 侧零失败。0 failures 才算过。

    坑：`verify_numbers.py` 的输出是**一行 key=value**：
    `declared=126 checked=126 failures=0 verdict=PASS exit=0`。
    第一版按"裸数字分词"找计数，`failures=0` 因为带等号不被 `str.isdigit()` 认，
    于是判成"解析不出 failures 数"→ `??`。必须用正则取 `failures=<n>`。

    分工（2026-11-19 压测后改）：本门只管数据层。正文绑定（`tex_bound`）在 s6 由
    G12 判——`main.tex` 到 s6 才有内容，s3 判它必然是 0。
    """
    import re  # noqa: PLC0415
    script = paper / "code" / "verify_numbers.py"
    if not script.exists():
        return None, "缺 code/verify_numbers.py（先跑 new_verify.py）"
    rc, out = _run([PY, script], cwd=paper)
    last = [l for l in out.splitlines() if l.strip()][-1:] or [""]
    m = re.search(r"failures\s*[=:]\s*(\d+)", out)
    if not m:
        # 第三种写法（EXAM_2023C 这批）：`119 passed, 0 failed, 0 unbound abstract numbers`
        m2 = re.search(r"(\d+)\s+passed,\s*(\d+)\s+failed", out)
        if m2:
            checked, n_fail = int(m2.group(1)), int(m2.group(2))
            if checked == 0:
                return False, "0 passed：一个数字都没扫到，属空壳通过"
            return rc == 0 and n_fail == 0, f"passed={checked} failed={n_fail}  {last[0][:80]}"
        # 老版对账器（APMCM2025_C 用的那种）不打计数，只打一句结论：
        # `PASS: JSON values and paper strings are consistent`
        # 不能因此判 ??，否则一份真对过的稿子永远过不了 G5。
        if rc == 0 and re.search(r"^PASS:", out, re.M):
            return True, f"老版对账器：{last[0][:90]}"
        return None, f"输出里没有 failures=<n>（末行：{last[0][:80]}）"
    n_fail = int(m.group(1))
    m_d = re.search(r"declared\s*[=:]\s*(\d+)", out)
    m_c = re.search(r"checked\s*[=:]\s*(\d+)", out)
    m_jf = re.search(r"json_fail\s*[=:]\s*(\d+)", out)
    n_json_fail = int(m_jf.group(1)) if m_jf else 0
    detail = (f"failures={n_fail} declared={m_d.group(1) if m_d else '?'}"
              f" checked={m_c.group(1) if m_c else '?'}"
              f" json_fail={n_json_fail}  {last[0][:80]}")
    # 空壳通过：declared=0 说明没扫到任何数字，不是"全对"
    if m_d and int(m_d.group(1)) == 0:
        return False, "declared=0：一个数字都没扫到，属空壳通过  " + detail
    if rc == 0 and n_fail == 0:
        return True, detail
    # 唯一的容错：正文还是骨架，且失败全部落在正文绑定上（JSON 侧零失败、声明全核对过）
    if _tex_is_skeleton(paper) and n_json_fail == 0 and m_d and m_c \
            and m_d.group(1) == m_c.group(1):
        return True, ("数据层自洽，正文仍是骨架（s6 才填），tex 绑定归 G12  "
                      + detail)
    return False, f"exit={rc}  " + detail


def gate_g6(paper: Path) -> tuple[bool | None, str]:
    """图表：每图两格式（pdf+png）+ **每张图内**有效字号 ≥6 pt。

    坑：第一版拿 `paper/main.pdf` 去跑 figfont，但 s4 阶段正文还没编译，
    `main.pdf` 根本不存在 → `FileNotFoundError` 被吞成 `??`，
    于是"图都画好了、字号全合格"的一步也过不了。必须逐张图跑。
    """
    fig = paper / "figures"
    pdfs = sorted(fig.glob("*.pdf")) if fig.is_dir() else []
    pngs = _count("*.png", fig)
    if not pdfs:
        return None, "figures/ 里没有 pdf"
    try:
        from mmkit import figfont  # noqa: PLC0415
    except Exception as exc:                                  # noqa: BLE001
        return None, f"figfont 导不进来：{type(exc).__name__}: {exc}"
    worst = None
    lo = 99.0
    bad_font = []
    for p in pdfs:
        try:
            rep = figfont.report(p)
        except Exception as exc:                              # noqa: BLE001
            return None, f"figfont 读不了 {p.name}：{type(exc).__name__}: {exc}"
        m = rep.get("min_pt") or 0
        if m < lo:
            lo, worst = m, p.name
        # 判据跟 figfont 自身一致：只看 `ok`（即 ≥3 字符的 span 是否低于 6 pt）。
        # 单字符 span（面板字母、刻度、数学符号）本来就有 5.x pt 的常规下标尺寸，
        # 拿裸 min_pt 当门槛会把合格的图判死（2026_C 的 fig06/fig07 就是这样被误杀）。
        if not rep.get("ok", True):
            bad_font.append(f"{p.name}(viol={rep.get('violations')},min={m:.2f}pt)")
    only_pdf = [p.stem for p in pdfs if not (fig / (p.stem + ".png")).exists()]
    ok = not bad_font and not only_pdf
    detail = f"figures pdf={len(pdfs)} png={pngs} min_pt={lo:.2f}@{worst}"
    if bad_font:
        detail += f"  字号不足: {bad_font[:4]}"
    if only_pdf:
        detail += f"  缺 png: {only_pdf[:5]}"
    return ok, detail


def gate_g7(paper: Path) -> tuple[bool | None, str]:
    """正文形态：12 条官方硬项 + 页数/前置顺序/参考文献。"""
    from mmkit import review_bench as RB  # noqa: PLC0415
    rep = RB.check_paper(str(paper))
    bad = [f for f in rep.findings if f.ok is False]
    unknown = [f for f in rep.findings if f.ok is None]
    # C11 的占位队号在填真号前必然 FAIL，属已知豁免（RUNBOOK §5 G8）
    hard = [f for f in bad if not (f.cid == "C11" and "placeholder" in f.observed)]
    detail = f"12 项 fail={len(bad)} unknown={len(unknown)}"
    if hard:
        detail += "  硬项: " + "; ".join(f"{f.cid} {f.observed}" for f in hard[:4])
    return (not hard), detail


def gate_g8(paper: Path) -> tuple[bool | None, str]:
    """编译合规：先真编译，再跑 gauntlet 的 16 项。"""
    rc, out = _run([PY, SCRIPTS / "gauntlet_check.py", paper], cwd=paper)
    lines = [l for l in out.splitlines() if l.startswith("[FAIL]")]
    summary = [l for l in out.splitlines() if "/" in l and "PASS" in l][-1:] or ["?"]
    hard = [l for l in lines if "R-V05" not in l and "R-V14" not in l]
    detail = f"gauntlet {summary[0].strip()}  fail={len(lines)}"
    if hard:
        detail += "  " + " | ".join(h.split("]", 1)[1].strip()[:60] for h in hard[:3])
    return (rc == 0 or not hard), detail


def gate_g9(paper: Path) -> tuple[bool | None, str]:
    return _md_gate(paper, RC.OUTPUT_OF["改进方案总编"])


# ---- G10–G15：把 `paper-kit` 的检查脚本变成流水线的强制步骤 ----------------
# 实现在 `submission_gate.py`（它同时是独立 CLI），这里只负责在正确的步骤
# 调正确的那个。每个门自己搭临时视图、跑完即删，不动论文目录。

def gate_g10(paper: Path) -> tuple[bool | None, str]:
    """s3 之后：表格数据真实性（`figures/TABLE_*` 里的数字能不能回到 JSON）。

    本项目没有 `TABLE_*` 文件（表格直接写在 `main.tex` 里），工具会报
    「无 TABLE 文件，跳过」——那是**结构上不适用**，返回 NA 而不是 None：
    两者都不拦，但 NA 会在 `--status` 里单列一行，让人看见这门没真判。
    """
    ws, tmp = SG.stage_data(paper, SG._pick_main(paper)[0] or "main")
    try:
        ok, d = SG.run_data(ws, "table")
    finally:
        if tmp is not None:
            tmp.cleanup()
    return (NA if ok is None else ok), d


def gate_g11(paper: Path) -> tuple[bool | None, str]:
    """s4 之后：图表视觉审查。

    「没配视觉模型」是结构问题（NA）；工具崩了、调用失败是**判不出**（None，
    由 SOFT_GATES 放行）——两者不能混，否则额度用尽会被记成「本题不适用」。
    """
    ok, d = SG.run_vision(paper)
    if ok is None and ("没配视觉模型" in d or "没有模型能看图" in d):
        return NA, d
    return ok, d


def gate_g12(paper: Path) -> tuple[bool | None, str]:
    """s6 之后：论文数字真实性（正文每个结果类数字能不能回到 `results_*.json`）。

    与 G5 分工：G5 跑项目自带的 `verify_numbers.py`，管「每个数字有没有登记」；
    G12 跑 `paper_data_check.py`，管「每个数字在原始数据里找不找得到」。
    两者互不替代——本项目实测 G5 的 36 条声明全过，G12 仍挑出 134 个未溯源线索。

    2026-11-19 压测补：**正文绑定**（`tex_bound == declared`，即每个声明数字都在
    `main.tex` 里印出来了）也从这里判。它不能留在 G5：s3 时 `main.tex` 还是骨架，
    那一半必然 0，会让整条流水线卡在 s3。s6 正文写完，这里才是它该判的地方。
    """
    ws, tmp = SG.stage_data(paper, SG._pick_main(paper)[0] or "main")
    try:
        ok, detail = SG.run_data(ws, "pdf")
    finally:
        if tmp is not None:
            tmp.cleanup()
    if not ok:
        return ok, detail
    # 第二半：正文绑定
    script = paper / "code" / "verify_numbers.py"
    if not script.exists():
        return ok, detail
    rc, out = _run([PY, script], cwd=paper)
    import re  # noqa: PLC0415
    m = re.search(r"tex_bound\s*[=:]\s*(\d+)\s*/\s*(\d+)", out)
    if not m:
        return ok, detail
    bound, total = int(m.group(1)), int(m.group(2))
    if total > 0 and bound < total:
        return False, f"正文只绑上 {bound}/{total} 个声明数字（其余在 main.tex 里印不出）  {detail}"
    return ok, f"{detail}  正文绑定 {bound}/{total}"


def gate_g13(paper: Path) -> tuple[bool | None, str]:
    """s6 之后：投稿前体检（页数/字体/书签/属性/英文稿混中文/占位符/图表出栏）。"""
    ws, tmp = SG.stage_venue(paper, SG._pick_main(paper)[0] or "main")
    try:
        return SG.run_venue(ws)
    finally:
        if tmp is not None:
            tmp.cleanup()


def gate_g14(paper: Path) -> tuple[bool | None, str]:
    """s6 之后：上传模板有没有被改坏。没用上传模板时是结构上的不适用（NA）。"""
    ws, tmp = SG.stage_venue(paper, SG._pick_main(paper)[0] or "main")
    try:
        ok, d = SG.run_template(ws)
    finally:
        if tmp is not None:
            tmp.cleanup()
    return (NA if ok is None else ok), d


def gate_g15(paper: Path) -> tuple[bool | None, str]:
    """s6 之后：`figures/*.tex` 有没有没被 `main.tex` 引到的死文件。"""
    return SG.run_sources(paper)


def gate_g16(paper: Path) -> tuple[bool | None, str]:
    """s4：口径审计 —— 同一个词有没有被两种算法用过。

    两层判据，缺一不可：
    (a) **机器硬项**：`caliber_check.py` 每次读当前 `main.tex` 现算（同一数值串被两种
        量纲使用）。这是为了解决「人写的报告是快照、改完稿永远红」的死结——机器那部分
        不再依赖谁记得重写报告。
    (b) **人的判断**：`out/05-caliber.md` 必须**比稿子新**（`judgment=True` 的时效判据）。
        过期就当没判，`NA` 而不是 FAIL；这时门按「机器过了，人未复判」放行，并在
        `--status` 的 NA 行里留痕——不能让一份 18:03 的旧报告永久堵住 22:00 的稿子，
        但也不能假装人审过了。
    """
    rc, out = _run([PY, SCRIPTS / "caliber_check.py", paper], cwd=paper, timeout=600)
    rep = [l for l in out.splitlines() if l.startswith("报告:")]
    detail = rep[-1].split("报告:", 1)[-1].strip() if rep else (out.splitlines()[-1][:90] if out else "无输出")
    if rc != 0:
        return False, f"机器硬项未过：{detail}"
    h_ok, h_detail = _md_gate(paper, crew.OUTPUT_OF["口径审计手"], judgment=True)
    if h_ok is NA:
        # 人没复判时返回 NA（不拦），而不是 True：效果一样是放行，但 `--status` 会把
        # G16 列进「不适用（NA，未真判）」那一行——这是唯一能让人看见「机器只判了硬项」的地方。
        return NA, f"机器 PASS（{detail}）；人未复判"
    if h_ok is True:
        return True, f"机器 PASS（{detail}）；人 PASS"
    return False, f"机器 PASS，但人的审计未过：{h_detail}"


def gate_g17(paper: Path) -> tuple[bool | None, str]:
    """s6：附录与自指 —— 由产物决定的值不许手写。

    除了成员的 md 产物，再单独查一条：`figures/code_index.tex` 里印的字节数
    是否与磁盘上的 `code/*.py` 一致。这条是可以机器判的，不靠成员自觉。
    """
    ok, detail = _md_gate(paper, crew.OUTPUT_OF["附录与自指手"])
    if ok is not True:
        return ok, detail
    idx = paper / "figures" / "code_index.tex"
    if not idx.exists():
        # 结构上不适用：有的稿子用 \lstinputlisting 内联源码，没有「脚本→字节数」索引表
        return NA, "没有 figures/code_index.tex（本稿内联 listing，无自指字节数表）"
        return ok, detail
    idx = paper / "figures" / "code_index.tex"
    if not idx.exists():
        return None, "缺 figures/code_index.tex（先跑 code/gen_index.py）"
    import re as _re  # noqa: PLC0415
    bad: list[str] = []
    for name, printed in _re.findall(r"\\texttt\{([\w\-.]+)\}\s*&\s*([\d,]+)", idx.read_text(encoding="utf-8")):
        f = paper / "code" / name
        if not f.exists():
            bad.append(f"{name}: 表里有、磁盘上没有")
            continue
        got = f"{f.stat().st_size:,}"
        if got != printed.strip():
            bad.append(f"{name}: 印 {printed.strip()} B / 实 {got} B")
    if bad:
        return False, "；".join(bad[:3]) + ("…" if len(bad) > 3 else "")
    return True, detail


def gate_g18(paper: Path) -> tuple[bool | None, str]:
    """s7：版式与出栏 —— 读者看不到的断头句。

    两条判据都机器可判：
    (a) 每张 `figures/*.pdf` 的文字 span 不许超出它**自己的** MediaBox
        超出 4pt 以上（`x1 > W+4.0` 等）——超出去的字读者看不到，是硬伤；
        2–4pt 是 matplotlib 自己估 bbox 的抖动（300dpi 下不到 0.02 英寸），不判死；
        「贴边」（`W-2.0` 以内 2pt）只计数、不判死：`bbox_inches="tight"` 存出来的图
        本来就把内容裁到画布边，把贴边当硬伤会让整类老稿永远过不去（EXAM_2023C 实测
        17 张里 10 张贴边，而它们一个断头字都没有）；
    (b) `main.log` 里的 `Overfull \\hbox` 超过 10.0pt 必须改（1.0–10.0 只记账）。
    """
    import re as _re  # noqa: PLC0415
    try:
        import pymupdf as fitz  # noqa: PLC0415
    except ImportError:
        try:
            import fitz  # type: ignore  # noqa: PLC0415
        except ImportError:
            return None, "没有 pymupdf，量不了出栏"
    figs = sorted((paper / "figures").glob("*.pdf"))
    if not figs:
        # 无图的稿子不是「判不出」而是「本题不涉及」：返回 NA 才不阻塞 s7。
        # 之前返回 None，让任何纯文字稿在 G19 里被判「非软闸门留了判不出的」。
        return NA, "没有 figures/*.pdf（本题无图，出栏无从判）"
    worst: list[str] = []
    touched: list[str] = []
    for f in figs:
        try:
            doc = fitz.open(str(f))
        except Exception:                                     # noqa: BLE001
            worst.append(f"{f.name}: 打不开")
            continue
        for page in doc:
            W, H = page.rect.width, page.rect.height
            for blk in page.get_text("dict")["blocks"]:
                for line in blk.get("lines", []):
                    for sp in line.get("spans", []):
                        t = sp["text"].strip()
                        if len(t) < 3:
                            continue
                        x0, y0, x1, y1 = sp["bbox"]
                        out = max(x1 - (W + 4.0), -4.0 - x0, y1 - (H + 4.0), -4.0 - y0)
                        if out > 0:
                            worst.append(f"{f.name}: {t[:24]!r} 越界 {out:.1f}pt")
                        elif max(x1 - (W - 2.0), 2.0 - x0, y1 - (H - 2.0), 2.0 - y0) > 0:
                            touched.append(f.name)
        doc.close()
    log = paper / "main.log"
    hbox: list[str] = []
    if log.exists():
        for m in _re.finditer(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log.read_text(encoding="utf-8", errors="replace")):
            if float(m.group(1)) > 10.0:
                hbox.append(f"{m.group(1)}pt")
    if worst:
        return False, f"{len(worst)} 处图内文字被裁：{'；'.join(worst[:3])}"
    if hbox:
        return False, f"{len(hbox)} 处 Overfull >10pt: {', '.join(hbox[:4])}"
    edge = f"，其中 {len(set(touched))} 张有文字贴边（不判死）" if touched else ""
    return True, f"{len(figs)} 张图无文字被裁{edge}，Overfull>10pt 为 0"


def gate_g19(paper: Path) -> tuple[bool | None, str]:
    """s7：流水线运维 —— 门本身有没有坏。

    机器可判的两条：`verify_numbers.py` 单次运行即 `failures=0`（自指判据若不
    收敛，跑两遍结果不同），以及 `pipeline_state.json` 里非软闸门不许留 `??`。
    """
    st = load_state(paper)
    # 自指：G19 在上一次运行里必然是 None（它正是那个还没跑的闸门），把自己算进去就永远过不去。
    unknown = [f"{k}.{g}" for k, rec in st.items() if isinstance(rec, dict)
               for g, v in (rec.get("gates") or {}).items()
               if v is None and g not in SOFT_GATES and not (k == "s7" and g == "G19")]
    if unknown:
        return False, f"非软闸门留了判不出的：{', '.join(unknown[:6])}"
    return _md_gate(paper, crew.OUTPUT_OF["流水线运维手"])


def gate_g20(paper: Path) -> tuple[bool | None, str]:
    """s1：真题对标 —— 有没有真的查过历年语料，而不是凭印象说"这题没人做过"。

    判据只认两样，都可机器复核：产物存在且末行 VERDICT，以及产物里出现过语料索引
    的真实路径（`.mh/corpus.json` 或 `corpus_index.py`）。后者防的是"写一篇漂亮的对标
    报告但一次没查"——那种稿子的"无先例"结论是不可信的。
    """
    ok, detail = _md_gate(paper, crew.OUTPUT_OF["真题对标手"])
    if ok is not True:
        return ok, detail
    src = paper / crew.OUTPUT_OF["真题对标手"]
    try:
        text = src.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return False, f"读不出 {src}: {exc}"
    if "corpus_index.py" not in text and "corpus.json" not in text:
        return False, "报告里没有一条语料查询记录（应出现 corpus_index.py 或 corpus.json）"
    return True, detail


GATES = {
    "G20": ("真题对标", gate_g20),
    "G1": ("题面", gate_g1),
    "G2": ("数据台账", gate_g2),
    "G3": ("模型", gate_g3),
    "G4": ("求解", gate_g4),
    "G5": ("数字对账", gate_g5),
    "G6": ("图表", gate_g6),
    "G7": ("正文形态", gate_g7),
    "G8": ("编译合规", gate_g8),
    "G9": ("评审收口", gate_g9),
    "G10": ("表格数据", gate_g10),
    "G11": ("视觉审查", gate_g11),
    "G12": ("论文数字", gate_g12),
    "G13": ("投稿体检", gate_g13),
    "G14": ("模板核对", gate_g14),
    "G15": ("源文件闭包", gate_g15),
    "G16": ("口径审计", gate_g16),
    "G17": ("附录自指", gate_g17),
    "G18": ("版式出栏", gate_g18),
    "G19": ("流水线自检", gate_g19),
}

# 软闸门：判不出（None）不拦，但判不过（False）照样拦。
# 进这个集合的只有两类：(a) 依赖外部服务的门（模型/网络不可用是常态，
# 算成 FAIL 会让整条链因为第三方额度永久堵死）；(b) 结构上可能不适用的门
# （项目没有 TABLE_* 文件、没上传过 LaTeX 模板）——那时工具只能返回「无从核对」，
# 把它当失败等于逼人为了过门去造假产物。
SOFT_GATES = {"G10", "G11", "G14"}


# ---------------------------------------------------------------- 编译

def compile_paper(paper: Path) -> tuple[bool, str]:
    """xelatex 两遍。TeX 不在 PATH 就报清楚，不静默跳过。

    坑：`gauntlet.build()` 返回的是**返回码列表**（`[0, 0]` = 两遍都成功），
    不是页数。第一版按页数判 `if not pages[-1]`，0 被当成"没出页"，
    于是一份能编 134 页的稿子被报成"编译没出页：[0, 0]"。
    判据必须是 `all(code == 0)`；页数从 PDF 另取。
    """
    from mmkit import gauntlet as G  # noqa: PLC0415
    if not Path(G.XELATEX).exists():
        return False, f"找不到 xelatex：{G.XELATEX}（装 MiKTeX 或改 mmkit/gauntlet.py 的 XELATEX）"
    try:
        codes = G.build(G.Paper(root=paper), passes=2)
    except Exception as exc:                                  # noqa: BLE001
        return False, f"编译失败 {type(exc).__name__}: {exc}"
    pdf = paper / "main.pdf"
    n_pages = 0
    try:
        import pymupdf  # noqa: PLC0415  （别用 fitz：它会往 stderr 打 FutureWarning）
        with pymupdf.open(pdf) as doc:
            n_pages = doc.page_count
    except Exception:                                         # noqa: BLE001
        pass
    ok = bool(codes) and all(c == 0 for c in codes) and n_pages > 0
    detail = f"返回码={codes}  main.pdf={n_pages} 页"
    if not ok:
        errs = []
        log = paper / "main.log"
        if log.exists():
            errs = [l for l in log.read_text(encoding="utf-8", errors="replace").splitlines()
                    if l.startswith("!")][:3]
        return False, detail + ("  " + " | ".join(errs) if errs else "")
    return True, detail


# ---------------------------------------------------------------- 派单

def dispatch_step(paper: Path, step: Step, timeout: int) -> dict[str, str]:
    """派一步的成员并等落地。返回 {成员: outcome}。"""
    if step.review:
        return dispatch_review(paper, timeout)
    ws = paper
    for name, status in crew.push_briefs(ws, paper, only=step.members):
        print(f"  brief {name:<8} {status}")
        if status.startswith(("MISMATCH", "NO-BODY")):
            raise SystemExit(f"FATAL: {name} 的 brief 更新失败，派单会读旧路径")
    before = crew.stamp(ws, step.members)
    sent = crew.dispatch(ws, paper, step.members)
    for name, sid in sent.items():
        print(f"  {name:<8} {sid}")
    st = crew.wait(ws, step.members, timeout_s=timeout, since=before)
    return {n: crew.outcome(ws, n) for n in step.members}


def dispatch_review(paper: Path, timeout: int) -> dict[str, str]:
    """审阅队两波：9 人并发 → 总编收口。"""
    out: dict[str, str] = {}
    wave0 = RC.WAVES[0]
    print(f"  审阅 W0 派 {len(wave0)} 人")
    # 审阅队用同一个 squad 机制：借用 crew 的 push/dispatch/wait，只换 brief 与产物表
    for name, status in _push_review_briefs(paper, wave0):
        print(f"  brief {name:<10} {status}")
    before = _review_stamp(paper, wave0)
    sent = _dispatch_review_members(paper, wave0)
    for name, sid in sent.items():
        print(f"  {name:<10} {sid}")
    _review_wait(paper, wave0, timeout, before)
    for n in wave0:
        out[n] = _review_outcome(paper, n)
    # 总编
    wave1 = RC.WAVES[1]
    print(f"  审阅 W1 派 {len(wave1)} 人: {wave1}")
    for name, status in _push_review_briefs(paper, wave1):
        print(f"  brief {name:<10} {status}")
    before = _review_stamp(paper, wave1)
    sent = _dispatch_review_members(paper, wave1)
    for name, sid in sent.items():
        print(f"  {name:<10} {sid}")
    _review_wait(paper, wave1, timeout, before)
    for n in wave1:
        out[n] = _review_outcome(paper, n)
    return out


# 审阅队复用 crew 的 node 通道，但成员来自 review_crew（另一个 teamId）。
def _push_review_briefs(paper: Path, members: list[str]) -> list[tuple[str, str]]:
    return _review_call("push", paper, members)


def _dispatch_review_members(paper: Path, members: list[str]) -> dict[str, str]:
    return dict(_review_call("dispatch", paper, members))


def _review_stamp(paper: Path, members: list[str]) -> dict[str, float | None]:
    return {n: (paper / RC.OUTPUT_OF[n]).stat().st_mtime
            if (paper / RC.OUTPUT_OF[n]).exists() else None for n in members}


def _review_outcome(paper: Path, name: str) -> str:
    p = paper / RC.OUTPUT_OF[name]
    if not p.exists() or p.stat().st_size == 0:
        return "missing"
    txt = p.read_text(encoding="utf-8", errors="replace")
    head = "\n".join(txt.splitlines()[:6])
    if "BLOCKED:" in head:
        return "blocked"
    if "VERDICT: FAIL" in txt:
        return "failed"
    return "delivered"


def _review_wait(paper: Path, members: list[str], timeout: int,
                 since: dict[str, float | None]) -> None:
    t0 = time.time()
    while True:
        done = []
        for n in members:
            p = paper / RC.OUTPUT_OF[n]
            if p.exists() and p.stat().st_size > 0:
                b = since.get(n)
                if b is None or p.stat().st_mtime > b:
                    done.append(n)
        if len(done) == len(members):
            return
        spent = int(time.time() - t0)
        if spent >= timeout:
            print(f"TIMEOUT after {spent}s; 未交付: {[n for n in members if n not in done]}")
            return
        print(f"  ...{spent:>4}s  landed={done if done else '(none)'}", flush=True)
        time.sleep(30)


def _review_call(kind: str, paper: Path, members: list[str]):
    """审阅队的 push/dispatch：直接改 crew 的 TEAM_ID 临时切到评审队。

    crew 里的 node 通道把 TEAM_ID 硬编码在 JS 里；这里用一个薄封装把 teamId 换掉，
    不去动 crew.py（那份文件有实测记录，不该为一个调用点改结构）。
    """
    saved = crew.TEAM_ID
    try:
        crew.TEAM_ID = crew.REVIEW_TEAM_ID
        if kind == "push":
            return _push_briefs_override(paper, members)
        return _dispatch_override(paper, members)
    finally:
        crew.TEAM_ID = saved


def _push_briefs_override(paper: Path, members: list[str]) -> list[tuple[str, str]]:
    bodies = {n: RC.full_briefs(paper, paper)[n] for n in members}
    js = crew._js_base() + """
import fs from 'node:fs';
const cfg = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const BODIES = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const state = await api(base.base, 'state');
const t = (state?.teams ?? []).find(x => x.id === TEAM_ID);
if (!t) { console.error('team not found'); process.exit(1); }
const res = [];
for (const m of t.members) {
  if (cfg.only && !cfg.only.includes(m.name)) continue;
  const fb = BODIES[m.name];
  if (!fb) { res.push([m.name, 'NO-BODY']); continue; }
  const r = await api(base.base, 'member', { method: 'POST', body: { teamId: t.id,
    member: { id: m.id, name: m.name, preset: m.preset ?? 'standard',
              permission: m.permission, brief: fb } } });
  const got = (r?.team?.members ?? []).find(x => x.id === m.id);
  res.push([m.name, got && got.brief.length === fb.length ? `OK ${fb.length}` : 'MISMATCH']);
}
console.log(JSON.stringify(res));
"""
    cfg = paper / "logs" / "_review_cfg.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"only": members}, ensure_ascii=False), encoding="utf-8")
    body_mod = cfg.with_name("_review_bodies.json")
    body_mod.write_text(json.dumps(bodies, ensure_ascii=False), encoding="utf-8")
    raw = crew._node(js, str(cfg), str(body_mod).replace("\\", "/"))
    return [tuple(x) for x in json.loads(raw)]


def _fallback_briefs(paper: Path, step: Step) -> tuple[int, str]:
    """派单不可用时的降级：把这一波每个人的完整 brief 落到磁盘，交给会话内执行。

    为什么降级要落盘而不是只打印：brief 里有十几条踩过的坑（MediaBox 判据、
    `\\DeclareMathSizes` 的 `\\f@size` 键、`gen_index` 必重跑），打印一遍就没了；
    落盘之后会话里照文件干，和真派单拿到的指令是同一份。
    """
    d = paper / "logs" / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    try:
        if step.review:
            briefs = RC.full_briefs(paper, paper)
        else:
            briefs = {m: crew.full_brief(m, paper, paper) for m in step.members}
    except Exception as exc:                                  # noqa: BLE001
        return 0, f"生成 brief 也失败了：{type(exc).__name__}: {exc}"
    for name, text in briefs.items():
        (d / f"{step.key}-{name}.md").write_text(text, encoding="utf-8", newline="\n")
        n += 1
    return n, str(d)


def _dispatch_override(paper: Path, members: list[str]) -> dict[str, str]:
    briefs = RC.full_briefs(paper, paper)
    js = crew._js_base() + """
import fs from 'node:fs';
const cfg = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const state = await api(base.base, 'state');
const t = (state?.teams ?? []).find(x => x.id === TEAM_ID);
if (!t) { console.error('team not found'); process.exit(1); }
const res = {};
for (const p of cfg.payloads) {
  const r = await api(base.base, 'run', { method: 'POST',
    body: { teamId: t.id, memberId: p.memberId, firstMessage: p.msg } });
  res[p.memberId] = r?.run?.sessionId ?? 'NO-SESSION';
}
console.log(JSON.stringify(res));
"""
    # 注意：crew.list_members_by_id() 只回 name/permission/brief_len，没有 id。
    # _review_call 已经把 crew.TEAM_ID 临时切到评审队，所以这里直接用 list_members()。
    roster = {m["id"]: m["name"] for m in crew.list_members()}
    by_name = {v: k for k, v in roster.items()}
    payloads = []
    for name in members:
        mid = by_name.get(name)
        if mid is None:
            raise KeyError(f"评审队没有成员 {name!r}；roster={sorted(roster.values())}")
        payloads.append({"memberId": mid, "msg": briefs[name]})
    cfg = paper / "logs" / f"_review_run_{int(time.time())}.json"
    cfg.write_text(json.dumps({"payloads": payloads}, ensure_ascii=False), encoding="utf-8")
    raw = crew._node(js, str(cfg).replace("\\", "/"))
    got = json.loads(raw)
    return {roster[k]: v for k, v in got.items() if k in by_name.values()}


# ---------------------------------------------------------------- 增量评审

# 每步之后叫谁来看一眼。依据是「这一步做出来的东西最容易被谁挑出问题」：
# s1 题面读漏 → 题目契合度审读；s2 假设站不住 → 模型与检验审读；
# s3 数对不上 → 数据与代码 + 数字对账；s4 口径 → 口径冲突；
# s5 图误导读 → 图表；s6 结构与摘要 → 结构 + 摘要表达；s7 交付合规 → 合规 + 版式出栏。
# 总编与排序手不进增量（它们要等全部落地，见 RC.WAVES）。
STEP_REVIEWERS: dict[str, list[str]] = {
    "s1": ["题目契合度审读"],
    "s2": ["模型与检验审读"],
    "s3": ["数据与代码审读", "数字对账员"],
    "s4": ["口径冲突审读"],
    "s5": ["图表审读"],
    "s6": ["论文结构审读", "摘要与表达审读"],
    "s7": ["合规审查员", "版式与出栏审读"],
}


def review_after(paper: Path, step: Step, timeout: int) -> dict[str, str]:
    """这一步过门之后，叫对应的审读员看一遍，产物落 review/。"""
    names = STEP_REVIEWERS.get(step.key) or []
    if not names:
        return {}
    print(f"  [增量评审] {step.key} 之后 {len(names)} 人: {names}")
    for n, s in _push_review_briefs(paper, names):
        print(f"    brief {n:<10} {s}")
    before = _review_stamp(paper, names)
    sent = _dispatch_review_members(paper, names)
    for n, sid in sent.items():
        print(f"    {n:<10} {sid}")
    _review_wait(paper, names, timeout, before)
    return {n: _review_outcome(paper, n) for n in names}


# ---------------------------------------------------------------- 主流程

def print_status(paper: Path) -> int:
    st = load_state(paper)
    print(f"论文目录 {paper}")
    print(f"{'步骤':<6}{'名称':<10}{'状态':<12}闸门")
    na_list: list[str] = []
    fail_list: list[str] = []
    for s in STEPS:
        rec = st.get(s.key, {})
        status = rec.get("status", "(未跑)")
        cells = []
        for g in s.gates:
            v = rec.get("gates", {}).get(g)
            cells.append(f"{g}={MARK.get(v, ' - ')}")
            if v == NA:
                na_list.append(g)
            elif v is False:
                fail_list.append(g)
        print(f"{s.key:<6}{s.title:<10}{status:<12}{' '.join(cells)}")
    # NA 单独一行：这不是失败，但必须让读的人看到「今天有几门其实没判」。
    if na_list:
        print(f"\n不适用（NA，未真判）：{', '.join(sorted(set(na_list)))}")
    if fail_list:
        print(f"未过：{', '.join(sorted(set(fail_list)))}")
    return 0


def run_step(paper: Path, step: Step, st: dict, timeout: int, skip_dispatch: bool,
             review_each: bool = True) -> bool:
    print(f"\n=== {step.key} {step.title}  成员={step.members or ['审阅队']}  门={step.gates}")
    rec = st.setdefault(step.key, {"gates": {}})
    rec["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    if step.compile_first:
        ok, detail = compile_paper(paper)
        print(f"  [compile] {MARK[ok]}  {detail}")
        rec["compile"] = detail
        if not ok:
            rec["status"] = "compile-failed"
            save_state(paper, st)
            return False

    if not skip_dispatch and (step.members or step.review):
        try:
            outs = dispatch_step(paper, step, timeout)
        except Exception as exc:                              # noqa: BLE001
            # 派单优先、失败降级：不中断流程，把这一波的 brief 落盘交给会话内执行。
            n, where = _fallback_briefs(paper, step)
            print(f"  派单不可用（{type(exc).__name__}: {exc}）")
            print(f"  → 已把 {n} 份 brief 落到 {where}")
            print(f"  → 会话内按 brief 干完这一波，再用 --skip-dispatch --only {step.key} --force {step.key} 重跑")
            rec["status"] = "awaiting-session"
            rec["error"] = f"{type(exc).__name__}: {exc}"
            rec["briefs"] = where
            save_state(paper, st)
            return False
        for n, o in outs.items():
            print(f"  {n:<10} {o}")
        rec["outcomes"] = outs

    all_ok = True
    for g in step.gates:
        label, fn = GATES[g]
        try:
            ok, detail = fn(paper)
        except Exception as exc:                              # noqa: BLE001
            ok, detail = None, f"{type(exc).__name__}: {exc}"
        na = ok == NA
        soft = ok is None and g in SOFT_GATES
        note = "  (不适用)" if na else ("  (软闸门，判不出不拦)" if soft else "")
        print(f"  [{g} {label}] {MARK[ok]}  {detail}{note}")
        rec["gates"][g] = ok
        rec.setdefault("gate_detail", {})[g] = detail
        # 每判完一门就落盘：G19 用 load_state 读盘判「有没有留 ??」，
        # 只在整步末尾存一次的话它读到的是上一轮的值（实测 s7.G18 已判 NA，
        # G19 仍报「留了判不出的」）。
        save_state(paper, st)
        if not (ok is True or na or soft):
            all_ok = False

    rec["status"] = "done" if all_ok else "gate-failed"
    rec["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_state(paper, st)

    # 增量评审：只在门全过之后叫，门没过时叫人来评是浪费——评的是一份已知有病的稿。
    if all_ok and review_each and not step.review and step.key in STEP_REVIEWERS:
        try:
            rec["review_after"] = review_after(paper, step, timeout)
        except Exception as exc:                              # noqa: BLE001
            names = STEP_REVIEWERS[step.key]
            d = paper / "logs" / "briefs"
            d.mkdir(parents=True, exist_ok=True)
            try:
                briefs = RC.full_briefs(paper, paper)
                for nm in names:
                    if nm in briefs:
                        (d / f"{step.key}-rev-{nm}.md").write_text(
                            briefs[nm], encoding="utf-8", newline="\n")
            except Exception:                                 # noqa: BLE001
                pass
            print(f"  [增量评审] 派单不可用（{type(exc).__name__}: {exc}）；"
                  f"brief 已落到 {d}，会话内补完后重跑本步")
            rec["review_after"] = {"error": f"{type(exc).__name__}: {exc}"}
        save_state(paper, st)
    return all_ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="八步流水线 + 二十道机器闸门（可断点续跑）")
    ap.add_argument("paper", help="论文目录")
    ap.add_argument("--status", action="store_true", help="只看状态")
    ap.add_argument("--dry", action="store_true", help="只打印计划")
    ap.add_argument("--step", help="跑到这一步（含）")
    ap.add_argument("--only", help="只跑这一步")
    ap.add_argument("--force", help="这些步骤已过也重跑，逗号分隔")
    ap.add_argument("--skip-dispatch", action="store_true", help="只跑闸门不派单")
    ap.add_argument("--no-review-each", action="store_true",
                    help="关掉『每步过门后叫对应审读员看一遍』（默认开着）")
    ap.add_argument("--timeout", type=int, default=2400, help="每步等待秒数")
    a = ap.parse_args(argv)

    paper = Path(a.paper).resolve()
    if not paper.exists():
        print(f"目录不存在: {paper}")
        return 2
    if not (paper / "main.tex").exists():
        print(f"WARN: {paper} 里没有 main.tex；先跑 new_paper.py <目录> --type C")

    if a.status:
        return print_status(paper)

    keys = [s.key for s in STEPS]
    if a.only:
        todo = [s for s in STEPS if s.key == a.only]
        if not todo:
            print(f"--only {a.only} 不在 {keys}")
            return 2
    elif a.step:
        if a.step not in keys:
            print(f"--step {a.step} 不在 {keys}")
            return 2
        todo = STEPS[: keys.index(a.step) + 1]
    else:
        todo = STEPS

    force = {x.strip() for x in (a.force or "").split(",") if x.strip()}

    if a.dry:
        st = load_state(paper)
        for s in todo:
            done = st.get(s.key, {}).get("status") == "done" and s.key not in force
            flag = "skip(已过)" if done else "run"
            print(f"{s.key} {s.title:<10} {flag:<10} members={s.members or ['审阅队9+1']} gates={s.gates}")
        return 0

    st = load_state(paper)
    for s in todo:
        if st.get(s.key, {}).get("status") == "done" and s.key not in force:
            print(f"\n--- {s.key} {s.title}  已过，跳过（--force {s.key} 可重跑）")
            continue
        if not run_step(paper, s, st, a.timeout, a.skip_dispatch,
                        review_each=not a.no_review_each):
            print(f"\nSTOP 在 {s.key}：门没过。修完再跑同一条命令即可，已过的步骤不会重派。")
            return 1
    print("\n全部指定步骤通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
