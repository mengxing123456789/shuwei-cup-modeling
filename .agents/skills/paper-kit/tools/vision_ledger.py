#!/usr/bin/env python3
r"""看图质检的统一判定与账本（第一档 A4，2026-10-08）。

三个看图脚本（drawio / tikz / 数据图）以前"没看也算通过"：空回复、客套话、看图次数用完都按
PASS 放行；"没审成"只记在模型自己写的 _tmp/*.txt 里，步骤卡照样显示全部通过。现在：

- 判定只有三种：pass（明确回答 PASS 且没列问题）/ issue（列出了 ISSUE）/ unreviewed（空回复、
  看不懂的回复、服务不可用、没配视觉模型、读图失败……）。unreviewed 退出码 2，绝不当通过。
- 账本按图片内容记在 .mh/vision_ledger.json（工作区文件列表不显示的隐藏目录，原子写）：图没改就沿用
  上次结论、不再付费；改一个像素就重新看。同一版本拿到看不懂的回复时最多再看一次
  （MAX_ATTEMPTS），同一张图一小时内最多看 MAX_VERSIONS_PER_HOUR 个版本（防"改一点审一次"）。
- 同一轮审查（SKILL 循环开头 export MH_VISION_RUN=…）里视觉服务一报不可用就熔断：
  这一轮其余图直接记"没审成"、不再调用；下一轮重新尝试。
- `status` 汇总应审的图：通过 / 有问题 / 没审成 / 没有记录。最终门（SKILL）和步骤卡（后端）
  读的是同一份账本、同一份应审清单。

命令行：
  python vision_ledger.py status --kind drawio figures/fig_a.pdf figures/fig_b.pdf
      逐图打印 PASS / ISSUE / UNREVIEWED / MISSING，并把这份应审清单记进账本；
      有"有问题"或"没有记录"的图退出码 1（最终门据此挡住），只有"没审成"仍是 0。
  python vision_ledger.py disable --kind drawio --reason "快速模式"
      记下"本轮按设置关闭了视觉审查"，步骤卡显示为关闭而不是未完成。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RULES_VERSION = 2              # 判定规则或提示词变了就加一：旧版本的结论不再沿用
                               # 2（10-12）：流程图先逐条描述连线（EDGE 行），写了“悬空”的按有问题算
LEDGER = Path(".mh") / "vision_ledger.json"
MAX_ATTEMPTS = 2               # 同一版本最多付费看几次（只有回复看不懂才会看第二次）
MAX_VERSIONS_PER_HOUR = 4      # 同一张图一小时内最多看几个版本
MAX_ENTRIES = 400
REPLY_KEEP = 2000              # 流程图回复先列每条连线，800 字会把后面的 ISSUE 截掉

STATUS_PASS, STATUS_ISSUE, STATUS_UNREVIEWED = "pass", "issue", "unreviewed"
_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
EXIT_CODES = {STATUS_PASS: 0, STATUS_ISSUE: 1, STATUS_UNREVIEWED: 2}

# 列出问题的行：ISSUE / ISSUE 1: / **ISSUE 2：** / - ISSUE 3. / 1. ISSUE: / 问题1：
_ISSUE_RE = re.compile(
    r"(?mi)^[ \t>]*(?:[-*•]\s*|\d+[.)、]\s*)?(?:\*\*|__)?\s*"
    r"(?:ISSUE\s*\d*\s*(?:\*\*|__)?\s*[:：.)、\-–—]|ISSUE\s*\d+\b|问题\s*\d+\s*(?:\*\*|__)?\s*[:：])"
)
_PASS_RE = re.compile(
    r"^(?:(?:RESULT|VERDICT|结论|结果|判定)\s*[:：]\s*)?(?:PASS(?:ED)?(?![A-Za-z])|通过[。.!！]?$)")
# 只有代码围栏/强调符号的行不算正文（模型偶尔把 PASS 包在 ``` 里）
_MARKUP_ONLY = "*_#>`\"' \t~-="
# "ISSUE: 无" / "ISSUE 1: none" 这种只是说没有问题
_NO_ISSUE_RE = re.compile(r"^\W*(?:无|没有|无问题|没有问题|none|n/?a|nothing|no issues?)\W*$", re.I)
# 没按格式答 PASS、但第一行明确说"没有问题"的也算看过且通过
_CLEAR_RE = re.compile(
    r"^(?:未发现|没有发现|没发现|无|没有)(?:任何|明显的?)?(?:硬伤|问题|缺陷)"
    r"|^NO (?:ISSUES?|PROBLEMS?|DEFECTS?)(?: (?:FOUND|DETECTED))?(?![A-Z])"
)
# 流程图提示词要求先逐条描述连线：EDGE 1: A → B；接好/悬空；标注：…（不是结论，判定时跳过）
_EDGE_RE = re.compile(
    r"(?i)^[ \t>]*(?:[-*•]\s*|\d+[.)、]\s*)?(?:\*\*|__)?\s*(?:EDGE|连线)\s*\d*\s*(?:\*\*|__)?\s*[:：]")
# 描述里写了“悬空”（不算“没有悬空”“未悬空”这类否定）
_DANGLING_RE = re.compile(r"(?<!没有)(?<!并未)(?<![不无没未])悬空")
# 逐条描述和结论之间的小标题：“连线清单：”“结论：”
_HEADING_RE = re.compile(r"^.{0,16}[:：]$")
# 列了 ISSUE 又自己撤回的：“……不列为问题（忽略）”“略有偏差（可忽略）”（“不可忽略”照算问题）
_RETRACTED_RE = re.compile(
    r"不列为问题|不算(?:作|是)?问题|不作为问题|不构成问题|不视为问题|[（(]忽略[）)]"
    r"|(?<!不)可以忽略|(?<!不)可忽略|无需修改|不需要修改|不必修改")


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def classify(reply: object) -> tuple[str, str]:
    """(status, reason) for one vision reply; never treats a non-answer as a pass."""
    if not isinstance(reply, str) or not reply.strip():
        return STATUS_UNREVIEWED, "视觉模型返回了空回复"
    lines = reply.splitlines()
    retracted = set()
    for at, line in enumerate(lines):
        marker = _ISSUE_RE.match(line)
        if not marker:
            continue
        text = line[marker.end():].strip(" *_")
        if _NO_ISSUE_RE.match(text) or _RETRACTED_RE.search(text):
            retracted.add(at)
            continue
        return STATUS_ISSUE, ""
    edges = [line for line in lines if _EDGE_RE.match(line)]
    dangling = [line.strip(_MARKUP_ONLY).strip() for line in edges if _DANGLING_RE.search(line)]
    if dangling:
        # 逐条描述已经说了有线没接上，结论再写 PASS 也不算通过
        return STATUS_ISSUE, "逐条描述里有连线写了“悬空”（有一端没接到节点上）：" + "；".join(
            item[:100] for item in dangling[:3])
    body = (line.strip(_MARKUP_ONLY).strip() for at, line in enumerate(lines)
            if not _EDGE_RE.match(line) and at not in retracted)
    first = next((line for line in body if line and not (edges and _HEADING_RE.match(line))), "")
    if _PASS_RE.match(first.upper()) or _CLEAR_RE.match(first.upper()):
        return STATUS_PASS, ""
    return STATUS_UNREVIEWED, "视觉模型的回复里既没有 PASS 也没有列出 ISSUE，无法判定"


def normalize_name(path: Path) -> str:
    stem = path.stem
    if stem.startswith("wrap_"):
        stem = stem[len("wrap_"):]
    for suffix in ("_vision", "_dfv", "_dv", "_v"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem


def workspace_root(path: Path) -> Path:
    resolved = Path(path).resolve()
    for ancestor in resolved.parents:
        if ancestor.name in ("figures", "_tmp"):
            return ancestor.parent
        if (ancestor / ".mh").is_dir() or (ancestor / "CLAUDE.md").is_file():
            return ancestor
    return Path.cwd()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(root: Path) -> dict:
    try:
        data = json.loads((root / LEDGER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("entries"), dict):
        data = {"version": 1, "entries": {}}
    return data


def save(root: Path, data: dict) -> None:
    entries = data["entries"]
    if len(entries) > MAX_ENTRIES:
        newest = sorted(entries.items(), key=lambda item: item[1].get("at_ts", 0))[-MAX_ENTRIES:]
        data["entries"] = dict(newest)
    path = root / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


class Review:
    """One figure version under review: decide whether to call, then record the outcome."""

    def __init__(self, image: Path, kind: str, source: Path | None = None,
                 digest: str | None = None) -> None:
        self.image = Path(image)
        self.source = Path(source) if source else self.image
        self.kind = kind
        self.root = workspace_root(self.source)
        self.figure = normalize_name(self.source)
        if digest and _SHA256_RE.fullmatch(digest):
            # review 送审前对原图做了快照：结论只属于那一刻的内容，审查途中图被改了也不会记到新图上
            self.key = f"{RULES_VERSION}:{digest.lower()}"
        else:
            try:
                self.key = f"{RULES_VERSION}:{file_hash(self.source)}"
            except OSError:
                self.key = ""
        self.run = os.environ.get("MH_VISION_RUN", "").strip()

    def _entry(self, data: dict) -> dict:
        return data["entries"].get(self.key) or {}

    def precheck(self) -> tuple[str, str, str]:
        """('cached', status, reply) / ('skip', reason, '') / ('call', '', '')."""
        if not self.key:
            return "skip", "读不到图片文件", ""
        data = load(self.root)
        entry = self._entry(data)
        if entry.get("status") in (STATUS_PASS, STATUS_ISSUE):
            reply = entry.get("reply", "")
            if entry["status"] == STATUS_ISSUE and entry.get("reason"):
                reply = f"{reply}\nISSUE（按逐条描述判定）: {entry['reason']}"
            return "cached", entry["status"], reply
        breaker = data.get("breaker") or {}
        if self.run and breaker.get("run") == self.run:
            return "skip", f"本轮审查中视觉服务已不可用（{breaker.get('reason', '')}），这张图没有再调用", ""
        if int(entry.get("attempts", 0)) >= MAX_ATTEMPTS:
            return "skip", f"这一版已付费看过 {MAX_ATTEMPTS} 次仍无法判定，不再重复调用", ""
        if not entry.get("calls"):
            # 还没付费看过的新版本才受"一小时几个版本"的限制；被限过的版本一小时后自然放行
            hour_ago = _now() - 3600
            recent = {key for key, item in data["entries"].items()
                      if item.get("figure") == self.figure and item.get("kind") == self.kind
                      and max(item.get("calls") or [0]) >= hour_ago}
            if len(recent) >= MAX_VERSIONS_PER_HOUR:
                return "skip", (f"这张图一小时内已看过 {MAX_VERSIONS_PER_HOUR} 个版本；"
                                "先按已列出的问题一次改好再审，不要改一点审一次"), ""
        return "call", "", ""

    def _write(self, status: str, reason: str, reply: str = "", paid: bool = False) -> None:
        if not self.key:
            return
        data = load(self.root)
        entry = dict(self._entry(data))
        now = _now()
        calls = list(entry.get("calls") or [])
        if paid:
            calls = (calls + [now])[-6:]
        try:
            source = os.path.relpath(self.source.resolve(), self.root.resolve())
        except ValueError:  # 不同盘符
            source = str(self.source.resolve())
        entry.update({
            "figure": self.figure, "kind": self.kind,
            "source": source.replace(os.sep, "/"),
            "status": status, "reason": reason, "reply": (reply or "")[:REPLY_KEEP],
            "attempts": int(entry.get("attempts", 0)) + (1 if paid else 0),
            "calls": calls, "at": _iso(now), "at_ts": now,
        })
        data["entries"][self.key] = entry
        save(self.root, data)

    def record_reply(self, reply: object) -> str:
        status, reason = classify(reply)
        self._write(status, reason, reply if isinstance(reply, str) else "", paid=True)
        return status

    def record_unreviewed(self, reason: str, *, outage: bool = False) -> None:
        self._write(STATUS_UNREVIEWED, reason)
        if outage and self.run and self.key:
            data = load(self.root)
            data["breaker"] = {"run": self.run, "reason": reason[:200], "at": _iso(_now())}
            save(self.root, data)


def _settle_without_call(review: Review) -> int | None:
    """Cached verdict or a recorded skip (exit code); None when a paid look is needed."""
    action, detail, reply = review.precheck()
    if action == "cached":
        print(f"CACHED_{detail.upper()}: 这一版图已审过（图没改，沿用上次结论，不再付费）")
        if reply:
            print(reply)
        return EXIT_CODES[detail]
    if action == "skip":
        review.record_unreviewed(detail)
        print(f"UNREVIEWED: {detail}。这张图记为'视觉审查未完成'，不要为此改图或反复手动重试。")
        return 2
    return None


def run_check(image: Path, kind: str, source: Path | None, call, digest: str | None = None) -> int:
    """Shared flow for the three vision scripts.

    ``call()`` returns the reply text or raises ``Unreviewable(reason, outage)``.
    Prints what the skill needs and returns the exit code (0 / 1 / 2).
    """
    review = Review(image, kind, source, digest)
    settled = _settle_without_call(review)
    if settled is not None:
        return settled
    try:
        reply = call()
    except Unreviewable as exc:
        review.record_unreviewed(exc.reason, outage=exc.outage)
        print(exc.message)
        return 2
    status = review.record_reply(reply)
    print(reply if isinstance(reply, str) else "")
    if status == STATUS_UNREVIEWED:
        print(f"UNREVIEWED: {classify(reply)[1]}。这张图记为'视觉审查未完成'（不是通过）。")
    elif status == STATUS_ISSUE and classify(reply)[1]:
        print(f"ISSUE（按逐条描述判定）: {classify(reply)[1]}。把这条线的两端接到对应节点上再审。")
    return EXIT_CODES[status]


class Unreviewable(Exception):
    """The figure could not be reviewed; ``message`` is printed for the skill."""

    def __init__(self, reason: str, message: str, *, outage: bool = False) -> None:
        super().__init__(reason)
        self.reason, self.message, self.outage = reason, message, outage


def summarize(root: Path, expected: list[str], kind: str = "", *, for_card: bool = False) -> dict:
    """Status of each expected figure (paths relative to ``root``) under the current rules.

    ``for_card``（只给步骤卡用）：卡片显示的是那一步当时的审查结果——
    - 判定规则升级后，这一版图没按新规则重审过，就沿用旧规则下的结论；
    - Word 稿流程审完把图的 PDF 转成 PNG、删掉了 PDF（技能就是这么规定的），就沿用这个文件最后一次的结论。
    两种情况以前都显示成"视觉审查未完成"（10-12 小白实测：两张都 PASS 的图，卡片写"未完成 2/2 张"）。
    最终门（status 命令）不用它：规则变了、图没了，都得按现在的文件和规则重审。
    """
    data = load(root)
    by_key = data["entries"]
    rows = []
    for rel in expected:
        path = (root / rel)
        name = normalize_name(Path(rel))
        try:
            digest = file_hash(path) if path.is_file() else ""
        except OSError:
            digest = ""
        if not digest:
            same_file = [item for item in by_key.values() if for_card and isinstance(item, dict)
                         and str(item.get("source", "")).replace("\\", "/") == rel.replace("\\", "/")
                         and (not kind or item.get("kind") == kind)]
            if not same_file:
                rows.append({"figure": name, "file": rel, "status": "missing", "reason": "图文件不存在或读不到"})
                continue
            entry = max(same_file, key=_ts)
        else:
            entry = by_key.get(f"{RULES_VERSION}:{digest}") or {}
        if not entry and for_card:
            older = [item for key, item in by_key.items()
                     if isinstance(item, dict) and key.partition(":")[2] == digest]
            entry = max(older, key=_ts) if older else {}
        status = entry.get("status") or "missing"
        reason = entry.get("reason", "") if status == STATUS_UNREVIEWED else (
            "没有这一版的审查记录" if status == "missing" else "")
        rows.append({"figure": name, "file": rel, "status": status, "reason": reason})
    counts = {key: sum(1 for row in rows if row["status"] == key)
              for key in (STATUS_PASS, STATUS_ISSUE, STATUS_UNREVIEWED, "missing")}
    return {"kind": kind, "total": len(rows), **counts, "figures": rows}


def record_expected(root: Path, kind: str, expected: list[str]) -> None:
    data = load(root)
    data.setdefault("expected", {})[kind or "any"] = {"files": expected, "at": _iso(_now()), "at_ts": _now()}
    save(root, data)


def record_disabled(root: Path, kind: str, reason: str) -> None:
    data = load(root)
    data.setdefault("disabled", {})[kind or "any"] = {"reason": reason, "at": _iso(_now()), "at_ts": _now()}
    save(root, data)


def _ts(item: object) -> float:
    try:
        return float(item.get("at_ts", 0)) if isinstance(item, dict) else 0.0
    except (TypeError, ValueError):
        return 0.0


def step_summary(root: Path, since_ts: float) -> dict | None:
    """What the step card shows for one figure step: uses the gate's own expected lists.

    A kind whose final gate never ran (step stopped early) falls back to the figures that
    were reviewed during this step, so "没审成" is still visible on the card.
    """
    data = load(root)
    kinds = {}
    for kind, item in (data.get("disabled") or {}).items():
        if _ts(item) >= since_ts:
            kinds[kind] = {"kind": kind, "disabled": str(item.get("reason", ""))[:120]}
    for kind, item in (data.get("expected") or {}).items():
        if _ts(item) < since_ts or kind in kinds:
            continue
        files = [str(f) for f in item.get("files") or [] if isinstance(f, str)]
        kinds[kind] = summarize(root, files, kind, for_card=True)
    reviewed: dict[str, list[str]] = {}
    for entry in data["entries"].values():
        kind, source = entry.get("kind"), entry.get("source")
        if (_ts(entry) >= since_ts and isinstance(kind, str) and kind and kind not in kinds
                and isinstance(source, str) and source):
            reviewed.setdefault(kind, [])
            if source not in reviewed[kind]:
                reviewed[kind].append(source)
    for kind, files in reviewed.items():
        kinds[kind] = summarize(root, files, kind, for_card=True)
    if not kinds:
        return None
    return {"kinds": list(kinds.values())}


TOOLS_BY_KIND = {"drawio": "drawio_vision_check.py", "tikz": "tikz_vision_check.py",
                 "datafig": "data_fig_vision_check.py"}


def _pdf_to_png(pdf: Path, out: Path) -> bool:
    try:
        import fitz  # PyMuPDF：纯 wheel、自带渲染，打包运行环境里都有
        with fitz.open(str(pdf)) as doc:
            doc[0].get_pixmap(matrix=fitz.Matrix(200 / 72, 200 / 72)).save(str(out))
        return out.is_file()
    except Exception:
        return False


def _tool_path(kind: str, tool: str | None) -> Path:
    """The vision script next to this file, else the published tools dir ($MH_TOOLS_DIR)."""
    if tool:
        return Path(tool)
    name = TOOLS_BY_KIND[kind]
    candidates = [Path(__file__).resolve().parent / name]
    if os.environ.get("MH_TOOLS_DIR", "").strip():
        candidates.append(Path(os.environ["MH_TOOLS_DIR"].strip()) / name)
    return next((path for path in candidates if path.is_file()), candidates[0])


def review(kind: str, files: list[str], tool: str | None = None) -> int:
    """Look at each figure once in one review round; exit 1 only when a figure has issues."""
    import subprocess
    tool_path = _tool_path(kind, tool)
    run_id = f"{kind}-{int(_now())}-{os.getpid()}"
    env = {**os.environ, "MH_VISION_RUN": run_id, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    counts = {STATUS_PASS: 0, STATUS_ISSUE: 0, STATUS_UNREVIEWED: 0}
    for name in files:
        path = Path(name)
        print(f"=== 视觉自检 [{kind}]: {path.name} ===", flush=True)
        try:
            data = path.read_bytes()
        except OSError:
            print("  图文件不存在或读不到，跳过（最终门会把它列为 MISSING）")
            continue
        # 送审的是这一刻的快照：结论绑定这份内容，审查途中图被改了，新图仍算"没有记录"
        digest = hashlib.sha256(data).hexdigest()
        current = Review(path, kind, digest=digest)
        current.run = run_id
        settled = _settle_without_call(current)
        if settled is not None:
            counts[{0: STATUS_PASS, 1: STATUS_ISSUE}.get(settled, STATUS_UNREVIEWED)] += 1
            continue
        if not tool_path.is_file():
            current.record_unreviewed(f"找不到看图脚本 {tool_path.name}")
            print(f"  ⚠ 找不到 {tool_path.name}：这张图视觉审查未完成")
            counts[STATUS_UNREVIEWED] += 1
            continue
        scratch = current.root / "_tmp"
        snapshot = scratch / f"{path.stem}_vsnap{path.suffix}"
        made = [snapshot]
        try:
            scratch.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(data)
        except OSError:
            current.record_unreviewed("写不了临时快照（_tmp/）")
            print("  ⚠ 写不了临时快照：这张图视觉审查未完成")
            counts[STATUS_UNREVIEWED] += 1
            continue
        target = snapshot
        if kind != "drawio" and path.suffix.lower() == ".pdf":
            target = scratch / f"{path.stem}_vcheck.png"
            made.append(target)
            if not _pdf_to_png(snapshot, target):
                for item in made:
                    item.unlink(missing_ok=True)
                current.record_unreviewed("PDF 转图片失败（缺 PyMuPDF）")
                print("  ⚠ PDF 转图片失败：这张图视觉审查未完成")
                counts[STATUS_UNREVIEWED] += 1
                continue
        command = [sys.executable, str(tool_path), str(target),
                   "--source", str(path), "--source-sha256", digest]
        try:
            proc = subprocess.run(command, env=env, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=330)
            code, output = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, output = None, f"看图脚本没有正常结束：{type(exc).__name__}"
        finally:
            for item in made:
                try:
                    item.unlink(missing_ok=True)
                except OSError:
                    pass
        print(output.rstrip())
        # 结论以账本为准，不看退出码：脚本崩溃（退出码 1 + Traceback）不等于图有问题，
        # 异常退出又没留下记录的也要记"没审成"，免得最终门把它当成"没有记录"一直挡着。
        status = current._entry(load(current.root)).get("status")
        traceback = "Traceback (most recent call last)" in output
        abnormal = code not in (0, 1, 2) or traceback
        if status not in (STATUS_PASS, STATUS_ISSUE, STATUS_UNREVIEWED) or (
                abnormal and status == STATUS_UNREVIEWED):
            if traceback:
                reason = "看图脚本运行出错"
            elif code is None:
                reason = output
            else:
                reason = f"看图脚本没有给出结论（退出码 {code}）"
            current.record_unreviewed(reason)
            status = STATUS_UNREVIEWED
        counts[status] += 1
    print(f"=== 视觉自检结果：通过 {counts[STATUS_PASS]} 张，有问题 {counts[STATUS_ISSUE]} 张，"
          f"没审成 {counts[STATUS_UNREVIEWED]} 张 ===")
    if counts[STATUS_ISSUE]:
        print("有问题的图：按上面的 ISSUE 一次改好、重新导出/编译后再跑本命令；没改过的图沿用结论，不会重复付费。")
    if counts[STATUS_UNREVIEWED]:
        print("没审成的图记为“视觉审查未完成”（不阻塞、会在步骤卡上提示）；不要为此改图或反复重试。")
    return 1 if counts[STATUS_ISSUE] else 0


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description="看图质检账本")
    sub = parser.add_subparsers(dest="command", required=True)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--kind", default="")
    status_parser.add_argument("files", nargs="*")
    review_parser = sub.add_parser("review")
    review_parser.add_argument("--kind", required=True, choices=sorted(TOOLS_BY_KIND))
    review_parser.add_argument("--tool", default=None)
    review_parser.add_argument("files", nargs="*")
    disable_parser = sub.add_parser("disable")
    disable_parser.add_argument("--kind", default="")
    disable_parser.add_argument("--reason", default="按设置关闭")
    args = parser.parse_args(argv)
    # 模型可能先 cd 进了 figures/：没有图路径时也从当前目录往上找工作区根
    root = workspace_root(Path(args.files[0]) if getattr(args, "files", None) else Path.cwd() / "_")
    if args.command == "disable":
        record_disabled(root, args.kind, args.reason)
        print(f"VISION_DISABLED: {args.reason}")
        return 0
    if args.command == "review":
        return review(args.kind, args.files, args.tool)
    rels = []
    for name in args.files:
        try:
            rels.append(os.path.relpath(Path(name).resolve(), root.resolve()).replace(os.sep, "/"))
        except ValueError:  # 不同盘符
            rels.append(str(Path(name).resolve()).replace(os.sep, "/"))
    record_expected(root, args.kind, rels)
    result = summarize(root, rels, args.kind)
    labels = {STATUS_PASS: "PASS", STATUS_ISSUE: "ISSUE", STATUS_UNREVIEWED: "UNREVIEWED", "missing": "MISSING"}
    for row in result["figures"]:
        extra = f"（{row['reason']}）" if row["reason"] else ""
        print(f"{labels[row['status']]} {row['file']}{extra}")
    print(f"SUMMARY total={result['total']} pass={result['pass']} issue={result['issue']} "
          f"unreviewed={result['unreviewed']} missing={result['missing']}")
    return 1 if result["issue"] or result["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
