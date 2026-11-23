#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ingest_data.py 的闸门测试：只测「收了什么、拒了什么、台账写了什么」。

不测 PDF/rar 分支（那要真样本，另由 authenticity 的测试覆盖），只测 xlsx 两条硬判据：
  表头 + 数据 → 进 data/ 且 ledger 记 verdict=OK
  只有表头     → 拒收，退出码 1，data/ 里不出现该文件
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import ingest_data  # noqa: E402

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None


def _xlsx(path: Path, rows: list[list]) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


@unittest.skipIf(openpyxl is None, "需要 openpyxl 造样本")
class TestIngest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.paper = self.root / "paper"

    def tearDown(self):
        self.tmp.cleanup()

    def test_ok_file_is_copied_and_ledgered(self):
        src = _xlsx(self.root / "data.xlsx", [["t", "v"], [1, 2], [3, 4]])
        code = ingest_data.main([str(self.paper), str(src), "--source", "测试源"])
        self.assertEqual(code, 0)
        self.assertTrue((self.paper / "data" / "data.xlsx").is_file())
        ledger = json.loads((self.paper / "data" / "ledger.json").read_text(encoding="utf-8"))
        row = ledger["files"][0]
        self.assertEqual(row["verdict"], "OK")
        self.assertFalse(row["forced"])
        self.assertEqual(row["source"], "测试源")
        self.assertEqual(len(row["sha256"]), 64)

    def test_header_only_is_refused(self):
        src = _xlsx(self.root / "head.xlsx", [["a", "b", "c"]])
        code = ingest_data.main([str(self.paper), str(src)])
        self.assertEqual(code, 1)
        self.assertFalse((self.paper / "data" / "head.xlsx").exists())

    def test_force_takes_it_but_marks_forced(self):
        src = _xlsx(self.root / "head.xlsx", [["a", "b", "c"]])
        code = ingest_data.main([str(self.paper), str(src), "--force"])
        self.assertEqual(code, 0)
        ledger = json.loads((self.paper / "data" / "ledger.json").read_text(encoding="utf-8"))
        self.assertTrue(ledger["files"][0]["forced"])

    def test_dry_does_not_copy(self):
        src = _xlsx(self.root / "data.xlsx", [["t", "v"], [1, 2]])
        code = ingest_data.main([str(self.paper), str(src), "--dry"])
        self.assertEqual(code, 0)
        self.assertFalse((self.paper / "data" / "data.xlsx").exists())


if __name__ == "__main__":
    unittest.main()