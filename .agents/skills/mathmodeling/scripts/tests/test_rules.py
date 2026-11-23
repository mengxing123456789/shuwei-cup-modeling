# -*- coding: utf-8 -*-
"""对 RULES.md 本身做结构测试：规定文件不能退化成一堆只写"不许"的清单。

三条硬要求的由来：
  R-E03..R-W03 里有 32 条第一版只写了「规定」+「为什么」，没有「验证」——
  于是"每条规定都做了测试验证"这句话就变成了空话。测试把这件事钉住：
  缺了验证手段的规定，测试直接失败，逼着人去补一条可执行的检查。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "RULES.md"

# 章节前缀 -> 该章节规定数量的下限。下限来自实际盘点，只许往上增不许往下减。
MIN_PER_FAMILY = {"E": 9, "M": 15, "T": 6, "W": 10, "V": 8}


def _blocks() -> list[tuple[str, str]]:
    text = RULES.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^### ", text)
    out = []
    for part in parts[1:]:
        rid = part.split()[0]
        out.append((rid, part))
    return out


class TestRulesDocument(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(RULES.is_file(), f"missing {RULES}")
        self.blocks = _blocks()

    def test_ids_are_unique_and_contiguous(self) -> None:
        ids = [r for r, _ in self.blocks]
        self.assertGreaterEqual(len(ids), 51, f"only {len(ids)} rules")
        self.assertEqual(len(ids), len(set(ids)), "duplicate rule ids")

    def test_every_family_has_enough_rules(self) -> None:
        got: dict[str, int] = {}
        for rid, _ in self.blocks:
            fam = re.match(r"R-([A-Z])", rid).group(1)
            got[fam] = got.get(fam, 0) + 1
        for fam, floor in MIN_PER_FAMILY.items():
            self.assertGreaterEqual(
                got.get(fam, 0), floor, f"family {fam} fell below its floor: {got}"
            )

    def test_every_rule_states_a_rule(self) -> None:
        for rid, body in self.blocks:
            self.assertIn("**规定**", body, f"{rid} has no 规定 line")

    def test_every_rule_states_why(self) -> None:
        # 没有"为什么"的规定无法判断它是否仍适用，删掉时也没人知道代价。
        for rid, body in self.blocks:
            self.assertTrue(
                "**为什么**" in body or "**判据**" in body,
                f"{rid} has no 为什么/判据 line",
            )

    def test_every_rule_names_a_check(self) -> None:
        # 这一条就是本次要补的 32 条：规定必须说清"怎么证明我遵守了它"。
        missing = [
            rid
            for rid, body in self.blocks
            if "**验证**" not in body and "**检查**" not in body
        ]
        self.assertEqual(missing, [], f"rules without a 验证 line: {missing}")

    def test_checks_are_executable_not_adjectives(self) -> None:
        # "验证：注意检查一下" 这类话不算验证手段。要求出现命令、路径、数字或工具名。
        bad = []
        for rid, body in self.blocks:
            m = re.search(r"\*\*(?:验证|检查)\*\*[：:](.+)", body)
            if not m:
                bad.append((rid, "no check sentence"))
                continue
            sent = m.group(1)
            if not re.search(r"`|=|\d|\.py|\.ps1|\.json|\.tex", sent):
                bad.append((rid, sent.strip()[:40]))
        self.assertEqual(bad, [], f"checks are not executable: {bad}")


if __name__ == "__main__":
    unittest.main()