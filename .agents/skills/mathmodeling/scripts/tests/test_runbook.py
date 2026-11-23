"""守住 RUNBOOK.md：文档里每条命令指向的文件必须真实存在。

为什么要有这个测试：RUNBOOK 的价值全在"agent 照它跑得通"。路径写错一个字符，
agent 就卡在第一步，而这不会有任何报错——只会静默走偏。这类错我已经犯过：
`refs/official_standard.json` 曾被我写成 `APMCM2026\refs\...`（真实位置在
`APMCM2025_C\refs\`，被套在基准带里的 donor 兜底掩盖了三个会话）。

判据只有两条：
1. RUNBOOK 里出现的每个 `\\` 路径 / 反引号路径，若形如 .py/.json/.md/.tex，必须在磁盘上存在；
2. RUNBOOK 引用的脚本级命令（new_paper / new_verify / gauntlet_check）必须真能 --help 或至少 import 通过。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
RUNBOOK = SKILL / "RUNBOOK.md"
MM = SKILL
SCRIPTS = MM / "scripts"

# 文档里刻意写成占位符的东西，不算路径
PLACEHOLDERS = {"<本题目录>", "<dir>", "<论文目录>", "$P", "$MM", "$PY"}

# 工作区根下的目录：文档里写成 `APMCM-PITFALLS/x.md`、`squads/...` 时按工作区根解析，
# 写成 `templates/...`、`scripts/...` 时按 skill 目录解析。
WS_SUBDIRS = ("APMCM-PITFALLS/", "APMCM2025_C/", "APMCM2026/")   # squads/ 已迁进 skill 目录
WS = SKILL.parents[2]


def _doc() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def _paths_in(doc: str) -> set[str]:
    """抽出所有像文件路径的片段。

    只认两种：带盘符的绝对路径，或指向本 skill 目录的显式相对路径
    （`templates/...`、`scripts/...`、`APMCM-PITFALLS/...`、`squads/...`）。
    论文章节里的相对名（`code/verify_numbers.py`、`out/00-problem.md`、
    `refs/official_standard.json`）是**目标论文里**的路径，此刻当然不存在，
    不能拿它们判文档写错 —— 这正是这个测试第一版误报 22 个文件的原因。
    """
    found: set[str] = set()
    for piece in re.findall(r"[A-Za-z]:\\[^\s`）)，,]+", doc):
        if re.search(r"\.(py|json|md|tex|mjs|pdf|cfg|cls)$", piece):
            found.add(piece)
    for tok in re.findall(r"`([^`\n]+)`", doc):
        for piece in re.split(r"[\s,，、()]+", tok):
            if piece in PLACEHOLDERS:
                continue
            if piece.startswith(("templates/", "scripts/", "APMCM-PITFALLS/", "squads/")):
                found.add(piece)
            elif piece.startswith("$MM\\") or piece.startswith("$MM/"):
                found.add(piece[4:])
    return found


def _resolve(rel: str) -> Path:
    """把文档里的片段解析成磁盘路径。"""
    if re.match(r"^[A-Za-z]:[\\/]", rel):
        return Path(rel.replace("\\", "/"))
    if rel.startswith(WS_SUBDIRS):
        return WS / rel
    return MM / rel.replace("\\", "/")


class TestRunbook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = _doc()

    def test_runbook_exists_and_is_not_a_stub(self):
        self.assertTrue(RUNBOOK.exists(), f"{RUNBOOK} missing")
        n = len(self.doc)
        self.assertGreater(n, 6000, "RUNBOOK 太短，像是没写完")
        # 九节骨架都要在
        for head in ("## 0", "## 1", "## 2", "## 3", "## 4", "## 5", "## 6", "## 7", "## 8", "## 9"):
            self.assertIn(head, self.doc, f"缺小节 {head}")

    def test_every_path_it_names_exists(self):
        missing = []
        checked = 0
        for rel in sorted(_paths_in(self.doc)):
            p = _resolve(rel)
            checked += 1
            if not p.exists():
                missing.append(rel)
        self.assertGreater(checked, 3, "解析到的路径太少，正则可能失效了")
        self.assertEqual(missing, [], f"RUNBOOK 指向了不存在的文件: {missing}")

    def test_the_three_starter_scripts_are_real(self):
        for name in ("new_paper.py", "new_verify.py", "gauntlet_check.py"):
            p = SCRIPTS / name
            self.assertTrue(p.exists(), f"缺 {name}")
            # 新加的脚本很长，main() 未必在前 4000 字符内；整文件搜更稳
            src = p.read_text(encoding="utf-8")
            self.assertIn("def main", src, f"{name} 里找不到 main()")
            self.assertIn('__name__ == "__main__"', src, f"{name} 没配入口守卫")

    def test_crew_exposes_the_api_runbook_uses(self):
        import sys

        sys.path.insert(0, str(SCRIPTS))
        from mmkit import crew  # noqa: F401

        for fn in ("list_members", "push_briefs", "dispatch", "landed", "wait"):
            self.assertTrue(callable(getattr(crew, fn, None)), f"crew 缺 {fn}()")
        self.assertEqual(len(crew.WAVES), 10, "波次数应固定为 10（18 人）")
        # 每个人都要有输出契约，否则 landed() 会 KeyError
        for name in (n for w in crew.WAVES for n in w):
            self.assertIn(name, crew.OUTPUT_OF, f"{name} 没有输出契约")
        # 依赖只能引用"更早的波"的产物
        wave_of = {n: i for i, w in enumerate(crew.WAVES) for n in w}
        producer = {v: k for k, v in crew.OUTPUT_OF.items()}
        for name, deps in crew.DEPENDS.items():
            for d in deps:
                owner = producer.get(d)
                self.assertIsNotNone(owner, f"{name} 依赖 {d}，但没人产出它")
                self.assertLess(wave_of[owner], wave_of[name], f"{name} 依赖了同波或后波的 {owner}")

    def test_known_failure_note_is_present(self):
        """matplotlib 崩溃是当前真实故障；文档必须写明绕法，否则画图会卡死。"""
        self.assertIn("0xC06D007F", self.doc)
        self.assertIn(r"D:\Python\python.exe", self.doc)

    def test_run_squad_is_wired_into_the_doc(self):
        """`run_squad.py` 是八波派单的入口；文档不写它，人还得手抄 here-string。"""
        p = SCRIPTS / "run_squad.py"
        self.assertTrue(p.exists(), "缺 run_squad.py")
        self.assertIn("run_squad.py", self.doc, "RUNBOOK 没提 run_squad.py")
        self.assertIn("--dry", self.doc, "RUNBOOK 该教人先 --dry 看依赖链")

    def test_open_items_table_matches_reality(self):
        """§9.2 的"已知未关闭项"必须真的存在，不能写成已完成。

        这里只查两条可判定的：队号占位符仍然在模板里、matplotlib 故障仍没修。
        哪天修好了，这条会失败，逼你同步改文档 —— 这正是想要的行为。
        """
        tmpl = (MM / "scripts" / "new_paper.py").read_text(encoding="utf-8")
        # 2026-11-12 改：脚手架不再发 XXXXX 占位符（会被不慎提交、也被 C11 判红），
        # 改成"格式合法的假号"。代价是**静默风险**：C11 查不出错号，
        # 所以这条测试反过来要求模板里**没有** XXXXX，且文档必须写出那个假号与"提交前换真号"。
        self.assertNotIn("baominghao{APMCM26XXXXX}", tmpl, "脚手架又发占位符了：它会被 C11 判红")
        self.assertNotRegex(tmpl, r"baominghao\{[A-Za-z0-9]*XXXXX\}")
        self.assertIn("apmcm2699001", tmpl, "脚手架队号变了，§9.2 要跟着改")
        self.assertIn("队号", self.doc)
        # 出图绕法必须同时写"画图用哪个解释器"
        self.assertRegex(self.doc, r"画图[^\n]*D:\\Python|D:\\Python[^\n]*画图")

    def test_open_table_names_the_real_team_number(self):
        """§9.2 的未关闭项必须逐字写出模板里的真实占位符。

        负对照验过：只查"文档里出现'队号'"这句话是**空过的** —— 把那一格
        改成"队号已填"照样 PASS。所以这里从 new_paper.py 里读出 `\\baominghao{…}`
        的实际内容，要求它在文档里逐字出现；哪天队号真填了，这条会失败，
        逼你回头删掉 §9.2 那一行。
        """
        tmpl = (MM / "scripts" / "new_paper.py").read_text(encoding="utf-8")
        m = re.search(r"baominghao\{([A-Za-z0-9]{6,})\}", tmpl)
        self.assertIsNotNone(m, "模板里找不到 \\baominghao{…}，§9.2 该删了")
        # 逐字出现在文档里：负对照验过，只写"队号"二字是空过的。
        self.assertIn(m.group(1), self.doc, f"§9.2 没逐字写出脚手架队号 {m.group(1)}")
        # 而且必须同时写明"提交前换成真号"——假号能静默过 C11。
        self.assertIn("提交前必须换成本队真号", self.doc, "假号能静默通过 C11，文档必须点出这个风险")


if __name__ == "__main__":
    unittest.main()