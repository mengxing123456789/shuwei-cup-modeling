"""Push the 31 member briefs into the two squads through the plugin's own REST route.

The route POST /dsh-agents/api/member is the same service the GUI writes through, so
the write reaches the host's in-memory ledger (a direct ledger.json edit does not).
Each call echoes the whole squad back; this script ignores the echo and prints counts.
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).with_name("squads")
if not ROOT.exists():
    ROOT = pathlib.Path("E:/数学建模/.agents/skills/mathmodeling/squads")

SQUADS = [
    {
        "dir": "main",
        "id": "61cec604-e7fa-4468-9a84-40757e4292c6",
        "name": "数学建模小队",
        "leadPreset": "standard",
        "description": (
            "亚太杯/国赛/数维杯数学建模全流程小队（18 人，十波）。给一个题目，产出可提交的成稿："
            "题目侦察 → 真题对标（2019–2025 数维杯真题与获奖论文语料，查同型题与那批稿子的章法）→ "
            "建模架构 → 数据溯源（抓数必留 url+时间+sha256）→ 求解与优化 / 代理模型训练 → "
            "数值对账（正文每个数回到 JSON 键）→ 口径审计（同一个词不许被两种算法用过）→ "
            "图表（图内 ≥6 pt、六范式、不被 MediaBox 裁）→ 论文撰写 → 版式与出栏（出栏看的是图自己的画布）→ "
            "附录与自指（由产物决定的值不许手写）→ 格式合规（C1–C12）→ 对抗评审 / 创新挖掘 → "
            "时间与质检 → 流水线运维（守 pipeline.py 与二十道门本身）→ 调度。"
            "每份 brief 都带可复算命令、法定产物路径与一句红线；"
            "跑的是 E:\\数学建模\\.agents\\skills\\mathmodeling\\scripts\\pipeline.py 的 s1–s7 与 G1–G20，"
            "判据全部可机器复核，不靠「看起来对」。"
        ),
        "members": [
            # (name, permission, file)
            ("题目侦察手", "read-only", "01-题目侦察手.md"),
            ("建模架构手", "workspace-write", "02-建模架构手.md"),
            ("数据溯源手", "read-only", "03-数据溯源手.md"),
            ("求解与优化手", "workspace-write", "04-求解与优化手.md"),
            ("代理模型训练手", "workspace-write", "05-代理模型训练手.md"),
            ("数值对账手", "read-only", "06-数值对账手.md"),
            ("图表手", "workspace-write", "07-图表手.md"),
            ("论文撰写手", "workspace-write", "08-论文撰写手.md"),
            ("格式合规手", "read-only", "09-格式合规手.md"),
            ("对抗评审手", "read-only", "10-对抗评审手.md"),
            ("创新挖掘手", "read-only", "11-创新挖掘手.md"),
            ("时间与质检手", "read-only", "12-时间与质检手.md"),
            ("调度手", "read-only", "13-调度手.md"),
            ("口径审计手", "read-only", "14-口径审计手.md"),
            ("版式与出栏手", "read-only", "15-版式与出栏手.md"),
            ("附录与自指手", "read-only", "16-附录与自指手.md"),
            ("流水线运维手", "workspace-write", "17-流水线运维手.md"),
            ("真题对标手", "workspace-write", "18-真题对标手.md"),
        ],
    },
    {
        "dir": "review",
        "id": "b68d6335-b534-4f4b-aec7-0b2d56b501b8",
        "name": "数学建模评审小队",
        "leadPreset": "standard",
        "description": (
            "写完论文之后的挑剔小队（13 人），只对已经存在的稿子下判断并给可执行改法。"
            "合规（C1–C12 官方条款）→ 结构（族属/必备章/每问闭环/页数预算）→ 摘要表达（四段式+数字配额）→ "
            "题目契合（题面每条要求逐条兑现）→ 模型与检验（口径/稳定性/边界/敏感性/结论强度）→ "
            "数据代码（台账/可重跑/verify 覆盖率/产物新鲜度）→ 数字对账（抽数回 JSON 复算）→ "
            "口径冲突（同一个词被两种算法用过，与数字对账分工）→ 图表（六范式与误用）→ "
            "版式与出栏（读者看不到的断头句）→ 创新性（四类创新+可检验命题）→ "
            "修复排序（今晚必做/明天能做/可以不做，带工时）→ 总编（四级排序、耗时、今晚必做）。"
            "依据全部是可核原件：35 份真题、16 份官方格式规范、22 份一等奖 PDF。"
            "派单前先由脚本生成 review/00-metrics.md 当唯一口径基线；报告只准对着它说话。"
        ),
        "members": [
            ("合规审查员", "read-only", "01-合规审查员.md"),
            ("论文结构审读", "read-only", "02-论文结构审读.md"),
            ("摘要与表达审读", "read-only", "03-摘要与表达审读.md"),
            ("题目契合度审读", "read-only", "04-题目契合度审读.md"),
            ("模型与检验审读", "read-only", "05-模型与检验审读.md"),
            ("数据与代码审读", "read-only", "06-数据与代码审读.md"),
            ("图表审读", "read-only", "07-图表审读.md"),
            ("创新性评估", "read-only", "08-创新性评估.md"),
            ("改进方案总编", "workspace-write", "09-改进方案总编.md"),
            ("数字对账员", "read-only", "10-数字对账员.md"),
            ("口径冲突审读", "read-only", "11-口径冲突审读.md"),
            ("版式与出栏审读", "read-only", "12-版式与出栏审读.md"),
            ("修复排序手", "read-only", "13-修复排序手.md"),
        ],
    },
]


def _candidates() -> list[str]:
    """候选 GUI 地址。

    以前这里写死 http://127.0.0.1:63649，DSH Web 每次重启都换端口，写死就是一次超时
    加一句 URLError。顺序：环境变量 → 已知端口 → 监听端口里能答 /dsh-agents/api/state 的。
    """
    out: list[str] = []
    env = (os.environ.get("DSH_WEB_URL") or "").strip()
    if env:
        out.append(env.rstrip("/"))
    for port in (63649, 59792, 54532, 61694, 65082):
        out.append(f"http://127.0.0.1:{port}")
    # netstat 兜底：只取 LISTENING，端口按出现顺序，靠后的（新起的）先试
    try:
        txt = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        txt = ""
    ports: list[int] = []
    for line in txt.splitlines():
        m = re.search(r"127\.0\.0\.1:(\d+)\s+\S+\s+LISTENING", line, re.I)
        if m and int(m.group(1)) not in ports:
            ports.append(int(m.group(1)))
    for port in reversed(ports):
        cand = f"http://127.0.0.1:{port}"
        if cand not in out:
            out.append(cand)
    return out


def _detect_base() -> str:
    """第一个能答 /dsh-agents/api/state 的地址。全都答不上就报错，不静默回落到旧端口。"""
    tried: list[str] = []
    for base in _candidates():
        tried.append(base)
        try:
            req = urllib.request.Request(
                base + "/dsh-agents/api/state",
                headers={"Accept": "application/json", "Origin": base, "Sec-Fetch-Site": "same-origin"},
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if b"teams" in resp.read(200000):
                    return base
        except Exception:
            continue
    raise SystemExit("找不到 DSH Web GUI：试过 " + ", ".join(tried[:6]) + " …；设 $env:DSH_WEB_URL 再跑")


BASE = _detect_base()


def call(path: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Origin": BASE,
            "Sec-Fetch-Site": "same-origin",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def state() -> dict:
    req = urllib.request.Request(
        BASE + "/dsh-agents/api/state",
        headers={"Accept": "application/json", "Origin": BASE, "Sec-Fetch-Site": "same-origin"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    write = "--write" in sys.argv
    st = state()
    by_id = {t["id"]: t for t in st["teams"]}
    total = 0
    for sq in SQUADS:
        team = by_id.get(sq["id"])
        if team is None:
            print(f"!! squad missing: {sq['name']}")
            return 2
        existing = {m["name"]: m for m in team["members"]}
        print(f"\n== {sq['name']}  ({len(team['members'])} existing, {len(sq['members'])} target)")
        # 1) squad description
        if write:
            call(
                "/dsh-agents/api/team",
                {
                    "team": {
                        "id": sq["id"],
                        "name": sq["name"],
                        "description": sq["description"],
                        "leadPreset": sq["leadPreset"],
                    }
                },
            )
            print("   description updated")
        # 2) members
        for name, perm, fname in sq["members"]:
            path = ROOT / sq["dir"] / fname
            brief = path.read_text(encoding="utf-8")
            current = existing.get(name)
            # 每份 brief 都要求写一个产物文件，read-only 会直接挡住交付，
            # 所以统一给 workspace-write（原队伍里 read-only 的两位也一并提上来）。
            payload = {"teamId": sq["id"], "member": {"name": name, "permission": "workspace-write", "brief": brief}}
            if current:
                payload["member"]["id"] = current["id"]
            tag = "update" if current else "ADD   "
            print(f"   {tag} {name:12s} {len(brief):5d} chars  {fname}")
            if write:
                call("/dsh-agents/api/member", payload)
            total += 1
    print(f"\ntotal members pushed: {total}  (write={write})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
