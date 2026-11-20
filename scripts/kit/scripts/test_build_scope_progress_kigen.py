#!/usr/bin/env python3
"""全体像の §9「期限（金庫の鍵）」の試し。依存なし: `python3 scripts/test_build_scope_progress_kigen.py -v`

仕様から書く（終わりの定義）:
  金庫の一覧（list_secrets の出力）を渡すと、説明の「期限 YYYY-MM-DD」を近い順に並べ、残り 14 日以内か切れた物に 🔴
  陰性対照: 期限の書かれていない項目は出ない／一覧を渡さないと「取得不能」（「（なし）」や 0 件とは書かない）／15 日以上先に印は付かない
  出すのは項目名と期限だけ（説明の他の文は出さない）
  §9 は §8 の後ろ（§1〜§8 の番号は動かさない）
"""
import datetime as dt
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_scope_progress as B  # noqa: E402

TODAY = dt.date(2026, 11, 17)


def vault_text(lines):
    body = "\n".join(lines)
    return f"📦 保存済みシークレット ({len(lines)}件)\n\n{body}\n"


def d(n):
    return (TODAY + dt.timedelta(days=n)).isoformat()


SPECIMEN = [
    f"• 外の合鍵 A (bot) 🔗example — 外のサービスの鍵・期限 {d(5)}・説明の他の文 zz-hidden-1 [by x, 2026-11-01]",
    f"• 外の合鍵 B — 期限 {d(-3)} 切れたら入れ直す zz-hidden-2 [by x, 2026-10-01]",
    "• 期限の無い鍵 — ただのメモ zz-hidden-3 [by x, 2026-10-01]",
]


def write(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    f.write(text); f.close()
    return f.name


class Kigen(unittest.TestCase):
    def test_specimen_two_rows_near_first_both_red(self):
        rows, why = B.read_vault(write(vault_text(SPECIMEN)), TODAY)
        self.assertEqual([r["名前"] for r in rows], ["外の合鍵 B", "外の合鍵 A"])
        self.assertEqual([r["印"] for r in rows], ["🔴", "🔴"])
        self.assertEqual(rows[0]["残り"], "3 日前に切れた")
        self.assertEqual(rows[1]["残り"], "あと 5 日")
        self.assertIn("3 件のうち期限の書かれた項目 2 件", why)

    def test_section_shows_only_name_and_date(self):
        out = "\n".join(B.vault_section(write(vault_text(SPECIMEN)), TODAY))
        self.assertIn("| 🔴 | 外の合鍵 B |", out)
        self.assertNotIn("期限の無い鍵", out)          # 陰性対照: 期限の書かれていない項目は出ない
        self.assertNotIn("zz-hidden", out)             # 説明の他の文は出さない

    def test_no_vault_is_unmeasurable_not_zero(self):
        out = "\n".join(B.vault_section(None, TODAY))
        self.assertIn("取得不能", out)
        self.assertNotIn("（なし）", out)
        self.assertNotIn("0 件", out)

    def test_unreadable_or_wrong_shape_is_unmeasurable(self):
        self.assertIsNone(B.read_vault("/nonexistent/zz-vault.txt", TODAY)[0])
        self.assertIsNone(B.read_vault(write("全然ちがう出力\n• 期限 2026-11-20\n"), TODAY)[0])

    def test_boundary_14_red_15_plain(self):
        rows, _ = B.read_vault(write(vault_text([f"• 十四 — 期限 {d(14)}", f"• 十五 — 期限 {d(15)}"])), TODAY)
        self.assertEqual({r["名前"]: r["印"] for r in rows}, {"十四": "🔴", "十五": ""})

    def test_empty_vault_is_measured_not_unmeasurable(self):
        out = "\n".join(B.vault_section(write("保存済みのシークレットはありません\n"), TODAY))
        self.assertIn("期限の書かれた項目は無い", out)
        self.assertNotIn("取得不能", out)

    def test_bad_date_is_flagged(self):
        rows, _ = B.read_vault(write(vault_text(["• 壊れた日付 — 期限 2026-13-40"])), TODAY)
        self.assertEqual((rows[0]["印"], rows[0]["残り"]), ("🔴", "日付が読めない"))

    def test_cli_carries_section_after_8(self):
        # 空の棚（一時 dir）に向けて生成器を撃ち、§9 が §8 の後ろに載る配線と --vault を測る。時計の控えも空の dir に向ける
        with tempfile.TemporaryDirectory() as root:
            out = os.path.join(root, "sp.md")
            env = {**os.environ, "MIKOTO_OS_ROOT": root, "HONJIN_ROOT": root,
                   "ROUTINE_DIR": os.path.join(root, "clock"), "SCHEDULER_DIR": os.path.join(root, "clock"), "HOME": root}
            run = lambda *extra: subprocess.run([sys.executable, os.path.join(HERE, "build_scope_progress.py"), "--out", out, *extra],
                                               capture_output=True, text=True, env=env)
            p = run("--vault", write(vault_text(SPECIMEN)))
            self.assertEqual(p.returncode, 0, p.stderr)
            text = open(out, encoding="utf-8").read()
            self.assertIn("## 9. 期限（金庫の鍵）", text)
            self.assertIn("外の合鍵 A", text)
            self.assertLess(text.index("## 8. "), text.index("## 9. 期限（金庫の鍵）"))
            self.assertNotIn("zz-hidden", text)
            p = run()                                   # 陰性対照: --vault なしは取得不能（0 件にしない）
            self.assertEqual(p.returncode, 0, p.stderr)
            nine = open(out, encoding="utf-8").read().split("## 9. 期限（金庫の鍵）", 1)[1]
            self.assertIn("取得不能", nine)
            self.assertNotIn("外の合鍵", nine)
        h = subprocess.run([sys.executable, os.path.join(HERE, "build_scope_progress.py"), "--help"],
                           capture_output=True, text=True)
        self.assertIn("--vault", h.stdout)


if __name__ == "__main__":
    unittest.main()
