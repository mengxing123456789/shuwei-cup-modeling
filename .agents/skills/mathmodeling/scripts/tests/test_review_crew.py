"""评审小队与论文骨架的契约测试。

这些断言来自 2026-11-12 那两轮真实评审，每一条都对应一次实际故障：
  10 人名册      ← 第 10 人（数字对账员）是因为"749 个特征值"这种数没人抽样复算才加的
  输出根=paper   ← 第一轮 8 份报告全落到工作区根，outcome() 报 8/8 missing
  brief≤4000     ← 宿主 API 的硬限制，超了整条派单 400
  00-metrics     ← 8 个人各自重跑同一组命令，报告里出现 68/72 页两种口径
  负对照         ← 脚手架自带的禁扫脚本一开始扫自己，永远 FAIL
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
MM = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from mmkit import review_crew as RC  # noqa: E402
import run_review  # noqa: E402

WS = SCRIPTS.parents[3]            # E:\数学建模（scripts -> mathmodeling -> skills -> .agents -> WS）
PAPER = WS / "PRACTICE_2018A"
BRIEF_MAX = 4000                   # 宿主 BRIEF_MAX_LENGTH


class TestReviewCrew(unittest.TestCase):
    def test_thirteen_members_three_waves(self):
        self.assertEqual(len(RC.MEMBERS), 13)
        self.assertEqual([len(w) for w in RC.WAVES], [11, 1, 1])
        self.assertIn("数字对账员", RC.WAVES[0])
        self.assertIn("口径冲突审读", RC.WAVES[0])
        self.assertEqual(RC.WAVES[1], ["改进方案总编"])
        self.assertEqual(RC.WAVES[2], ["修复排序手"])

    def test_every_member_has_output_and_permission(self):
        names = [n for n, _ in RC.MEMBERS]
        for n in names:
            self.assertIn(n, RC.OUTPUT_OF, f"{n} 没有输出文件")
            self.assertIn(n, RC.DEPENDS, f"{n} 没有依赖声明（空也要写 []）")
            self.assertIn(RC.OUTPUT_OF[n], RC.OUTPUT_OF.values())
        self.assertEqual(len(set(RC.OUTPUT_OF.values())), len(names), "两个成员写同一个文件")

    def test_outputs_are_numbered_and_land_under_the_paper(self):
        """报告的编号是下游配对用的；路径必须挂在论文目录，不是工作区根。"""
        for n, rel in RC.OUTPUT_OF.items():
            self.assertTrue(rel.startswith("review/"), f"{n}: {rel}")
        briefs = RC.full_briefs(WS, PAPER)
        for n, s in briefs.items():
            want = str(PAPER / RC.OUTPUT_OF[n])
            self.assertIn(f"【你的输出】{want}", s, f"{n} 的输出路径没定死在论文目录")

    def test_editor_in_chief_waits_for_all_eleven(self):
        deps = RC.DEPENDS["改进方案总编"]
        self.assertEqual(len(deps), 11)
        self.assertIn("review/09-numbers.md", deps)
        self.assertIn("review/11-layout.md", deps)

    def test_briefs_fit_the_api_limit(self):
        for n, s in RC.full_briefs(WS, PAPER).items():
            self.assertLessEqual(len(s), BRIEF_MAX, f"{n} brief {len(s)} 字符，超过宿主上限")

    def test_every_brief_points_at_the_metrics_baseline(self):
        for n, s in RC.full_briefs(WS, PAPER).items():
            self.assertIn("00-metrics.md", s, f"{n} 没被告知口径基线在哪")
            self.assertIn("报告是快照", s, f"{n} 没被告知报告会过期")

    def test_number_reconciler_requires_sampling(self):
        s = RC.full_briefs(WS, PAPER)["数字对账员"]
        self.assertIn("抽 10 个", s)
        self.assertIn("结构性空转", s)


class TestScaffoldLoop(unittest.TestCase):
    """new_paper.py 生成的不只是 main.tex：评审要用的东西必须在骨架里就位。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dest = Path(cls.tmp.name) / "P_loop"
        r = subprocess.run([sys.executable, str(SCRIPTS / "new_paper.py"), str(cls.dest),
                            "--type", "A"], capture_output=True, text=True, timeout=300)
        cls.out = r.stdout + r.stderr

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_scaffold_ran(self):
        self.assertIn("created", self.out)
        self.assertIn("blanks=", self.out)

    def test_directories_and_docs_exist(self):
        for d in ("code", "data", "figures", "tables", "logs", "refs", "review", "problem"):
            self.assertTrue((self.dest / d).is_dir(), f"缺目录 {d}")
        for f in ("NO_PEEK.md", "BUILD.md", "review/README.md",
                  "code/check_no_peek.py", "code/verify_numbers.py", "main.tex"):
            self.assertTrue((self.dest / f).is_file(), f"缺文件 {f}")

    def test_verify_stub_runs_and_admits_it_binds_nothing(self):
        r = subprocess.run([sys.executable, str(self.dest / "code" / "verify_numbers.py")],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 claims", r.stdout, "空骨架不该假装有 claim")
        self.assertIn("PASS", r.stdout)

    def test_no_peek_has_a_working_negative_control(self):
        """PASS → 放陷阱 FAIL（要报出文件:行号）→ 删掉恢复 PASS。"""
        chk = self.dest / "code" / "check_no_peek.py"
        ok = subprocess.run([sys.executable, str(chk)], capture_output=True, text=True, timeout=120)
        self.assertEqual(ok.returncode, 0, "新目录不该有禁区命中：\n" + ok.stdout)
        self.assertIn("forbidden hits 0", ok.stdout)

        trap = self.dest / "code" / "_trap.py"
        trap.write_text('src = r"E:\\x\\_award_text\\y.txt"\n', encoding="utf-8")
        try:
            bad = subprocess.run([sys.executable, str(chk)], capture_output=True, text=True, timeout=120)
            self.assertEqual(bad.returncode, 1, "陷阱没被抓住：\n" + bad.stdout)
            self.assertIn("code", bad.stdout)
            self.assertIn("_trap.py:1", bad.stdout.replace("\\", "/"))
        finally:
            trap.unlink()
        again = subprocess.run([sys.executable, str(chk)], capture_output=True, text=True, timeout=120)
        self.assertEqual(again.returncode, 0, again.stdout)


class TestStubIsNotAGreen(unittest.TestCase):
    """脚手架发的 verify_numbers.py 是 0-claim 桩。R-V06 若只判"文件存在"，
    一份从没绑过数字的论文会拿绿 —— 2026-11-12 实测过这个假绿，这里把它钉住。
    """

    def test_zero_claim_stub_fails_r_v06(self):
        import os
        import shutil
        import subprocess
        import tempfile

        g = SCRIPTS / "gauntlet_check.py"
        stub = ('print("0 claims, 0 ranges")\nprint("PASS")\nraise SystemExit(0)\n')
        with tempfile.TemporaryDirectory() as td:
            # 自己搭最小骨架，不依赖工作区里任何脚手架目录（_smoke 之类会被清掉）
            d = Path(td) / "P0"
            (d / "code").mkdir(parents=True)
            (d / "paper").mkdir()
            (d / "main.tex").write_text(
                "\\documentclass{article}\n\\begin{document}stub\\end{document}\n", encoding="utf-8")
            (d / "code" / "verify_numbers.py").write_text(
                "import sys\n" + stub, encoding="utf-8")
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            # 必须用带可用 numpy 的解释器：mathmodel 环境里 numpy 的 LAPACK 会 fail-fast
            # （exit=-1066598273 且 stdout 为空），那样这个测试会"什么都没打印"地假通过。
            exe = sys.executable
            r = subprocess.run([exe, str(g), str(d), "--allow-draft"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=900, env=env)
            out = (r.stdout or "") + (r.stderr or "")
            line = [x for x in out.splitlines() if "R-V06" in x]
            self.assertTrue(line, f"gauntlet 没打印 R-V06：rc={r.returncode} len_out={len(out)} "
                                  f"exe={exe}\n" + out[-800:])
            self.assertIn("FAIL", line[0], "0-claim 桩拿了绿：\n" + line[0])
            self.assertIn("claims=0", line[0])


class TestNoAnswersInTheScaffold(unittest.TestCase):
    """练习赛目录里不能有一等奖正文 —— 那等于把答案放在旁边，
    而 check_no_peek.py 跳过 refs/，文件级扫描抓不到它。"""

    @classmethod
    def setUpClass(cls):
        import subprocess
        import tempfile

        cls.tmp = tempfile.TemporaryDirectory()
        cls.dest = Path(cls.tmp.name) / "P_peek"
        subprocess.run([sys.executable, str(SCRIPTS / "new_paper.py"), str(cls.dest),
                        "--type", "A"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_no_award_texts_copied(self):
        self.assertFalse((self.dest / "refs" / "award_text").exists(),
                         "骨架拷了一等奖正文：练习赛的 no-peek 立刻失效")
        self.assertTrue((self.dest / "refs" / "official_standard.json").is_file(),
                        "基准带需要 official_standard.json")

    def test_scan_flags_a_planted_award_dir(self):
        import subprocess

        chk = self.dest / "code" / "check_no_peek.py"
        ok = subprocess.run([sys.executable, str(chk)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120)
        self.assertEqual(ok.returncode, 0, ok.stdout)

        d = self.dest / "refs" / "award_text"
        d.mkdir()
        (d / "fake.txt").write_text("placeholder", encoding="utf-8")
        try:
            bad = subprocess.run([sys.executable, str(chk)], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=120)
            self.assertEqual(bad.returncode, 1, "放了一等奖目录却没被抓：\n" + bad.stdout)
            self.assertIn("award_text", bad.stdout)
        finally:
            (d / "fake.txt").unlink()
            d.rmdir()



class TestRosterNeverBlanks(unittest.TestCase):
    """名册与 brief 必须同一次写，且读回 min(brief_len) > 0（2026-11-12 UI 事故的契约）。

    事故现象：GUI 上「数学建模评审小队 10 位成员 / 没有简介 / 点进去什么都没有」。
    根因：run_review.team() 发的是 [{name, permission}]，create_team 的 upsert 把 brief 写成空串。
    这三条断言分别钉住：①建稿队名册可由 WAVES 推出且 13 人；②两支队的简介都不许为空；
    ③create_team 的 JS 里必须有"没有新 brief 就不发 brief 键"的守卫。
    """

    def test_production_roster_from_waves(self):
        from mmkit import crew
        roster = [n for wave in crew.WAVES for n in wave]
        self.assertEqual(len(roster), 18, roster)
        self.assertEqual(len(set(roster)), 18, "有重名成员：" + str(roster))
        self.assertEqual(sorted(crew.PERMISSION), [], "所有人都是 workspace-write：read-only 写不出产物，G1/G9 永远拿不到 VERDICT")
        for n in crew.PERMISSION:
            self.assertIn(n, roster)

    def test_team_descriptions_non_empty(self):
        from mmkit import crew
        self.assertGreater(len(crew.TEAM_DESCRIPTION.strip()), 80, "建稿队简介太短，UI 会当成没有")
        self.assertGreater(len(RC.TEAM_DESCRIPTION.strip()), 80, "评审队简介太短，UI 会当成没有")
        self.assertIn("十三角色", RC.TEAM_DESCRIPTION)

    def test_create_team_guard_keeps_brief(self):
        """upsert 时缺 brief 不许把已有 brief 清空 —— 直接查 JS 模板里的守卫。"""
        src = (SCRIPTS / "mmkit" / "crew.py").read_text(encoding="utf-8")
        self.assertIn("cur.brief", src, "create_team 缺少「沿用旧 brief」的守卫")
        self.assertIn("description", src, "create_team 不支持队伍简介")
        # run_review.team() 必须把 brief 一起写进去
        rr = (SCRIPTS / "run_review.py").read_text(encoding="utf-8")
        self.assertIn("full_briefs", rr)
        self.assertNotIn('members = [{"name": n, "permission": p}]', rr,
                         "team() 又退回只写名册不写 brief 的写法")



class TestWorkspacePinOptIn(unittest.TestCase):
    """工作区**默认不钉**，只能显式钉（2026-11-12 用户两次反馈的最终结论）。

    宿主语义（`lib/index.js:2645 resolveWorkspacePin`）：`team.workspaceId === undefined`
    → run 不带 workspace id → 由 Host 在**它自己的默认目录**里开会话，`SquadDetail.tsx:72`
    显示"未绑定（用宿主默认目录）"。钉住则每次 run 都在该工作区的会话列表里新建一条会话。
    用户先问"为什么都是同一个地方"，钉了之后又说"会话太乱了，都没法找对话了" ——
    所以：能力保留（`workspace_id_for`），默认关闭，要钉必须显式给。
    """

    def test_lookup_matches_exact_and_ancestor(self):
        from mmkit import crew
        fake = [{"id": "w-root", "path": r"E:\数学建模", "title": "数学建模"},
                {"id": "w-other", "path": r"E:\3d", "title": "3d"}]
        orig = crew._node
        crew._node = lambda *a, **k: __import__("json").dumps(fake)
        try:
            self.assertEqual(crew.workspace_id_for(r"E:\数学建模"), "w-root")
            self.assertEqual(crew.workspace_id_for(r"E:\数学建模\PRACTICE_2018A"), "w-root")
            self.assertIsNone(crew.workspace_id_for(r"E:\没有这个目录"))
        finally:
            crew._node = orig

    def test_default_is_unpinned_and_pin_is_explicit(self):
        import inspect
        from mmkit import crew
        sig_c = inspect.signature(crew.create_team)
        self.assertEqual(sig_c.parameters["workspace_id"].default, "",
                         "create_team 的 workspace_id 默认必须是空串（不钉），否则每次派单都污染工作区会话列表")
        sig_r = inspect.signature(crew.refresh_team)
        self.assertEqual(sig_r.parameters["workspace_id"].default, "")
        sig_t = inspect.signature(run_review.team)
        self.assertFalse(sig_t.parameters["pin"].default, "run_review.team 默认必须是 pin=False")
        src = (SCRIPTS / "mmkit" / "crew.py").read_text(encoding="utf-8")
        self.assertIn("workspaceId", src, "create_team 仍要能把 workspaceId 发出去（显式钉时）")
        rr = (SCRIPTS / "run_review.py").read_text(encoding="utf-8")
        body = rr.split("def team(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("if pin:", body)
        self.assertLess(body.index("wid = \"\""), body.index("if pin:"),
                        "workspace_id_for 只能在 --pin 分支里调用")


if __name__ == "__main__":
    unittest.main()