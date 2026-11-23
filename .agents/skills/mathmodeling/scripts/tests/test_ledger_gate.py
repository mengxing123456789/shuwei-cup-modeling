# -*- coding: utf-8 -*-
"""_too_small 对 data/ledger.json 的四条分支（2026-11-19 两个真实误判的回归）。

实测背景：
1. 题面 20 B、0 个数字 token，数据溯源手正确写出 status=NOT-APPLICABLE + 5584 B
   理由，landed() 仍判 False → s1 会白等满 2400 s。
2. SHUWEI2025_A 用 ingest_data.py 把官方 xlsx 正式收进 data/，台账写成 `files`
   键，而 _too_small 只认 `records` → 已交付被判没干活。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmkit import crew  # noqa: E402


class TestLedgerGate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        self.ledger = self.tmp / "data" / "ledger.json"

    def write(self, obj):
        self.ledger.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def test_ingest_files_key_passes(self):
        """ingest_data.py 写 files 键 —— 官方数据已收进 data/ 就是交付。"""
        self.write({"schema": 1, "files": [{
            "name": "a.xlsx", "sha256": "0" * 64, "source": "official",
            "ingested_at": "2026-11-19T07:24:24Z", "verdict": "OK"}]})
        self.assertIsNone(crew._too_small(self.tmp, "数据溯源手"))

    def test_not_applicable_with_reason_passes(self):
        """题面没有外部数字时，写清 NOT-APPLICABLE 理由也算交付。"""
        self.write({"schema": 1, "records": [], "status": "NOT-APPLICABLE",
                    "not_applicable_line": "NOT-APPLICABLE: 题面 20 B、0 个数字 token，无可抓取指标。"})
        self.assertIsNone(crew._too_small(self.tmp, "数据溯源手"))

    def test_empty_shell_still_blocked(self):
        self.write({"records": []})
        self.assertIn("空壳", crew._too_small(self.tmp, "数据溯源手") or "")

    def test_not_applicable_without_reason_blocked(self):
        self.write({"records": [], "status": "NOT-APPLICABLE", "not_applicable_line": "NA"})
        self.assertIsNotNone(crew._too_small(self.tmp, "数据溯源手"))

    def test_missing_sha_blocked(self):
        self.write({"records": [{"source": "x", "fetched_at": "t"}]})
        self.assertIn("sha256", crew._too_small(self.tmp, "数据溯源手") or "")

    def test_member_fetched_at_accepted(self):
        self.write({"records": [{"source": "x", "sha256": "0" * 64, "fetched_at": "t"}]})
        self.assertIsNone(crew._too_small(self.tmp, "数据溯源手"))


if __name__ == "__main__":
    unittest.main()
