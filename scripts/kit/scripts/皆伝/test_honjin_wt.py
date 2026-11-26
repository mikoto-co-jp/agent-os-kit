#!/usr/bin/env python3
"""皆伝の道具 honjin_wt.py push と箱の門 pre-commit-box.sh の試験。依存なし: `python3 scripts/kit/scripts/皆伝/test_honjin_wt.py -v`

🚨 仕様（会員の提案 2 点・CTO 箱 n=5656）:
   ① 差分が無くても、自席の HEAD に origin/main に無い commit が在れば送る（前の push が途中で止まった後の撃ち直し）
      陽性対照: 差分ありは今どおり送る／陰性対照: 差分なし・送っていない commit 0 本なら何もしない
   ② 箱の門は commit が触る箱だけを検める。他の席の箱 B が語彙外でも、箱に触れない保存は通る
      陰性対照: 箱 B を含む保存は今どおり止まる。止まったら <道> の下で積んだ index を戻す
🚨 本物の本陣・中の OS には触らない: 毎回、使い捨ての本陣の形（入れ子 2 本＋bare 2 本）を一時ディレクトリに作る。
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))       # scripts/kit/scripts/皆伝
TOOLS = os.path.dirname(HERE)                            # scripts/kit/scripts
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
ENV.pop("HONJIN_WT_DIR", None)
ENV.pop("HONJIN_WT_FULL", None)
SID = "0123abcd"
BAD = "---\ntitle: 悪い箱\nstate: 未着手\nowner: x\nabsorb: x\nupdated: 2000-01-02\n---\n# 悪い箱\n"


def run(cwd, *a, env=None, check=True):
    p = subprocess.run(list(a), cwd=cwd, capture_output=True, text=True, env={**ENV, **(env or {})})
    if check and p.returncode != 0:
        raise AssertionError(f"{a} rc={p.returncode}\n{p.stdout}\n{p.stderr}")
    return p


def git(cwd, *a, check=True):
    return run(cwd, "git", *a, check=check)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


class Shelf(unittest.TestCase):
    """本陣（検体の本陣）の中に 中の OS（検体OS）が別の保管場所として入れ子。scripts は 検体OS/scripts への別名"""

    def setUp(self):
        self.d = os.path.realpath(tempfile.mkdtemp(prefix="honjin_wt_"))
        self.addCleanup(shutil.rmtree, self.d, True)
        hj = self.hj = os.path.join(self.d, "本陣")
        os1 = self.os1 = os.path.join(hj, "検体OS")
        sc = os.path.join(os1, "scripts")
        os.makedirs(os.path.join(sc, "git-hooks"))
        shutil.copy(os.path.join(HERE, "honjin_wt.py"), os.path.join(sc, "honjin_wt.py"))
        shutil.copy(os.path.join(TOOLS, "kiroku.py"), os.path.join(sc, "kiroku.py"))
        shutil.copy(os.path.join(TOOLS, "git-hooks", "pre-commit-box.sh"), os.path.join(sc, "git-hooks", "pre-commit-box.sh"))
        write(os.path.join(sc, "git-hooks", "pre-commit"), '#!/bin/sh\nsh "$(dirname "$0")/pre-commit-box.sh"\n')
        os.chmod(os.path.join(sc, "git-hooks", "pre-commit"), 0o755)
        write(os.path.join(os1, ".gitignore"), "11一時ファイル/\n__pycache__/\n")
        write(os.path.join(os1, "01商品資産", "a.md"), "base\n")
        os.symlink("検体OS/scripts", os.path.join(hj, "scripts"))
        write(os.path.join(hj, ".gitignore"), "検体OS/\n")
        write(os.path.join(hj, "c.txt"), "base\n")
        os.makedirs(os.path.join(hj, "08プロジェクト"))
        for slug in ("2000-01-01-箱A", "2000-01-02-箱B"):
            run(hj, sys.executable, "scripts/kiroku.py", "box", "--slug", slug, "--title", "検体", "--state", "起案",
                "--owner", "検体", "--absorb", "なし")
        for r in (hj, os1):
            git(r, "init", "-q", "-b", "main")
            git(r, "config", "core.hooksPath", "scripts/git-hooks")
            git(r, "add", "-A")
            git(r, "commit", "-qm", "base")
            git(self.d, "init", "-q", "--bare", "-b", "main", r + ".git")
            git(r, "remote", "add", "origin", r + ".git")
            git(r, "push", "-q", "origin", "HEAD:main")
        out = self.wt_cmd(hj, "open", SID).stdout.strip().splitlines()[-1]
        self.w = out
        self.wi = os.path.join(out, "検体OS")

    def wt_cmd(self, cwd, *a, check=True):
        return run(cwd, sys.executable, os.path.join(self.hj, "scripts", "honjin_wt.py"), *a,
                   env={"HONJIN_ROOT": self.hj}, check=check)

    def origin(self, repo, path):
        return git(self.d, "--git-dir", repo + ".git", "show", f"main:{path}", check=False)

    def head(self, repo):
        return git(self.d, "--git-dir", repo + ".git", "rev-parse", "main").stdout.strip()

    # ---------- ① ----------
    def test_push_with_diff_lands(self):
        """陽性対照: 差分ありの push は今どおり載る"""
        write(os.path.join(self.w, "c.txt"), "直した\n")
        self.wt_cmd(self.w, "push", "-m", "検体", "--", "c.txt")
        self.assertEqual(self.origin(self.hj, "c.txt").stdout, "直した\n")

    def test_no_diff_but_unsent_commit_is_pushed(self):
        """差分なし・送っていない commit 1 本 → origin/main に載る（本陣と中の OS の両方）"""
        for top, path in ((self.w, "c.txt"), (self.wi, "01商品資産/a.md")):
            write(os.path.join(top, path), "未送り\n")
            git(top, "commit", "-qm", "前の push が途中で止まった", "--", path)
        self.wt_cmd(self.w, "push", "-m", "撃ち直し", "--", "c.txt", "検体OS/01商品資産/a.md")
        self.assertEqual(self.origin(self.hj, "c.txt").stdout, "未送り\n")
        self.assertEqual(self.origin(self.os1, "01商品資産/a.md").stdout, "未送り\n")

    def test_no_diff_nothing_unsent_does_nothing(self):
        """陰性対照: 差分なし・送っていない commit 0 本なら送らない（origin は動かない・rc=0）"""
        before = self.head(self.hj), self.head(self.os1)
        p = self.wt_cmd(self.w, "push", "-m", "検体", "--", "c.txt", "検体OS/01商品資産/a.md")
        self.assertEqual((self.head(self.hj), self.head(self.os1)), before)
        self.assertNotIn("push した", p.stdout)

    # ---------- ② ----------
    def _break_box_b_on_origin(self):
        """他の席が箱 B を語彙外のまま保存して同期された（門を抜けて origin に在る）"""
        write(os.path.join(self.hj, "08プロジェクト", "2000-01-02-箱B", "status.md"), BAD)
        git(self.hj, "commit", "-qm", "他の席の書きかけ", "--no-verify", "--", "08プロジェクト/2000-01-02-箱B/status.md")
        git(self.hj, "push", "-q", "origin", "HEAD:main")
        self.wt_cmd(self.w, "sync")

    def test_unrelated_commit_passes_with_bad_other_box(self):
        """箱 B が語彙外のまま、箱に触れない c.txt だけの push が通る"""
        self._break_box_b_on_origin()
        write(os.path.join(self.w, "c.txt"), "箱に触れない\n")
        self.wt_cmd(self.w, "push", "-m", "検体", "--", "c.txt")
        self.assertEqual(self.origin(self.hj, "c.txt").stdout, "箱に触れない\n")

    def test_other_good_box_passes_with_bad_other_box(self):
        """箱 A（語彙どおり）を直す push は、箱 B が語彙外でも通る"""
        self._break_box_b_on_origin()
        p = os.path.join(self.w, "08プロジェクト", "2000-01-01-箱A", "status.md")
        write(p, read(p) + "\n- 現在地: 検体\n")
        self.wt_cmd(self.w, "push", "-m", "検体", "--", "08プロジェクト/2000-01-01-箱A/status.md")
        self.assertIn("現在地: 検体", self.origin(self.hj, "08プロジェクト/2000-01-01-箱A/status.md").stdout)

    def test_commit_touching_bad_box_is_stopped_and_index_restored(self):
        """陰性対照: 箱 B を含む push は今どおり止まる。止まった後、index に積んだ物は戻っている"""
        write(os.path.join(self.w, "08プロジェクト", "2000-01-02-箱B", "status.md"), BAD)
        write(os.path.join(self.w, "c.txt"), "一緒に\n")
        before = self.head(self.hj)
        p = self.wt_cmd(self.w, "push", "-m", "検体", "--", "c.txt", "08プロジェクト/2000-01-02-箱B/status.md", check=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("pre-commit-box", p.stderr)
        self.assertIn("index は撃つ前の形に戻した", p.stderr)
        self.assertEqual(self.head(self.hj), before)
        self.assertEqual(git(self.w, "diff", "--cached", "--name-only").stdout.strip(), "")
        self.assertEqual(read(os.path.join(self.w, "c.txt")), "一緒に\n")   # 手元は変えない


if __name__ == "__main__":
    unittest.main()
