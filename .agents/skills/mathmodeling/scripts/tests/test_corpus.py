"""语料索引与真实性台账的口径测试。

这两个模块的价值全在「文件名不规矩时还能判对年份/题号」——一旦判错，G20 的对标报告就会
拿错年份的稿子当最近邻。所以把踩过的四种命名写法钉成断言，而不是靠肉眼看输出。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmkit import corpus  # noqa: E402


class TestCorpusNaming(unittest.TestCase):
    def setUp(self):
        from mmkit import corpus

        self.C = corpus

    def test_problem_letters_in_four_spellings(self):
        """`A_Problem` / `IMCM_Problem_A` / `problemC-…` / 拼错的 `problrmD` 都要认出来。"""
        cases = {
            "2023_“ShuWei Cup”B_Problem.pdf": "B",
            "2019_“ShuWei Cup”IMCM_Problem_A.pdf": "A",
            "problemC-Optimal snow removal plan.pdf": "C",
            "problrmD-Ways for enterprises to resume work.pdf": "D",
        }
        for name, want in cases.items():
            m = self.C.PROBLEM_IN_NAME.search(name)
            self.assertEqual(self.C._problem_of(m), want, name)

    def test_year_and_problem_from_name(self):
        self.assertEqual(self.C._meta_from_name("2024“ShuWei Cup”_Problem.zip")[0], "2024")
        self.assertEqual(self.C._meta_from_name("A202111107503.pdf"), ("2021", "A"))

    def test_title_from_official_filename(self):
        """官方给的文件名 `Problem A：<标题>` 比从正文猜稳，2025 四题只能靠它。"""
        self.assertEqual(
            self.C._title_from_name("Problem A：Active Vibration Suppression Design Based on Centrifugal Actuators"),
            "Active Vibration Suppression Design Based on Centrifugal Actuators",
        )
        self.assertEqual(self.C._title_from_name("A_Problem（题面整理）"), "")

    def test_ledger_and_readme_are_skipped(self):
        """台账与说明不是语料：进索引会让「未知年份题面」凭空多几条。"""
        for name in ("_PROVENANCE.md", "README_题面补全说明.md", "readme.md"):
            self.assertTrue(self.C._skip_name(Path(name)), name)
        self.assertFalse(self.C._skip_name(Path("2023_“ShuWei Cup”A_Problem.pdf")))


class TestAuthenticityVerdicts(unittest.TestCase):
    def setUp(self):
        from mmkit import authenticity

        self.A = authenticity

    def test_pdf_without_text_layer_is_suspect(self):
        """扫描件：有页数但抽不出字。判 BROKEN 会让人以为文件坏了，判 OK 会让模板提取半夜崩。"""
        v, why = self.A.verdict_check(".pdf", {"pages": 3, "chars_p1": 40, "chars": 120, "images_p1": 3, "encrypted": False})
        self.assertEqual(v, "SUSPECT", why)

    def test_pdf_broken_when_unopenable(self):
        v, _ = self.A.verdict_check(".pdf", {"pages": 0, "chars_p1": 0, "chars": 0, "images_p1": 0, "encrypted": False})
        self.assertEqual(v, "BROKEN")

    def test_xlsx_with_header_only_is_suspect(self):
        """只有表头 = 数据没下全。这是网盘断点续传最常见的残留。"""
        v, why = self.A.verdict_check(".xlsx", {"sheets": [{"name": "Sheet1", "rows": 1, "cols": 6}]})
        self.assertEqual(v, "SUSPECT", why)

    def test_xlsx_with_rows_is_ok(self):
        v, _ = self.A.verdict_check(".xlsx", {"sheets": [{"name": "Sheet1", "rows": 1002, "cols": 6}]})
        self.assertEqual(v, "OK")


class TestTitleGuards(unittest.TestCase):
    """标题的两道闸：否决器（_plausible_title）+ 往前接行（_join_back）。

    这两条是 2026-11-19 第三次修的产物：124 篇论文里曾有约 30 篇标题只拿到
    「换行后的后半截」（"Machines Based on Multiple Optimization Models"），
    还有几篇拿到摘要句。这里把两类错误各钉一条测试。
    """

    @classmethod
    def setUpClass(cls):
        from mmkit import corpus

        cls.corpus = corpus

    def test_abstract_sentence_rejected(self):
        self.assertFalse(corpus._plausible_title(
            "this paper, the effective utilization and sustainable development of cotton straw will be"))
        self.assertFalse(corpus._plausible_title("For question 1: Firstly, the data were pre-processed"))
        self.assertFalse(corpus._plausible_title("November 15, 2021"))

    def test_real_title_accepted(self):
        self.assertTrue(corpus._plausible_title("Modeling and Optimization Control of Compound Helicopters"))
        self.assertTrue(corpus._plausible_title("The Mathematics of Laundry Cleaning"))

    def test_join_back_stitches_wrapped_title(self):
        lines = ["", "Optimization of Washing", "Machines Based on Multiple Optimization Models"]
        self.assertEqual(corpus._join_back(lines, 2, lines[2]),
                         "Optimization of Washing Machines Based on Multiple Optimization Models")

    def test_join_back_refuses_page_header(self):
        lines = ["Team # 12345", "Backtracking Algorithms"]
        self.assertEqual(corpus._join_back(lines, 1, lines[1]), "Backtracking Algorithms")

    def test_guess_title_reads_problem_line(self):
        text = "Problem C: Intelligent Recognition and Detection of AI-Generated Text\nAbstract\n..."
        self.assertEqual(corpus._guess_title(text, "fallback"),
                         "Intelligent Recognition and Detection of AI-Generated Text")


if __name__ == "__main__":
    unittest.main()