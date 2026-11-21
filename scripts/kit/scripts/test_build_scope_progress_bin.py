#!/usr/bin/env python3
"""全体像の Routine の節（便）の数え方の試し。依存なし: `python3 scripts/test_build_scope_progress_bin.py -v`

仕様から書く（終わりの定義）:
  fail は時計の結果が error／timeout のときだけ（skipped_policy・skipped_running・done_self・spawned・ok は落ちではない）。
    最後が「用無し」の周でも、席が起きた最後の回が error なら fail（隠れた落ちを拾う）
  実行の列は窓の便名を label の括弧の頭の英語名・routine の name でも引く
    陰性対照: 2 本以上の便の括弧に出る語（機体の名前など）と、括弧の途中の英語では引かない
  check だけで席が 1 度も立っていない便と、1 度も起こされていない便は「実行未記録」に数えず、別の欄（idle）に出る
    陰性対照: 席が起きたのに窓に無い scheduler の便は、今までどおり実行未記録に数える
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_scope_progress as B  # noqa: E402

TS = "2026-01-10T00:00:00Z"
SCHEDULES = [
    {"id": "aaaa0001", "label": "週の掃除（sweep-watch→候補へ 1 行）", "cron": "0 4 * * 1", "agent": "@掃除"},
    {"id": "aaaa0002", "label": "見張りだけの便（box-one・check で完結）", "cron": "*/5 * * * *", "check": "exit 1"},
    {"id": "aaaa0003", "label": "まだ起きていない便（月 1）", "cron": "0 9 1 * *"},
    {"id": "aaaa0004", "label": "自分で閉じる便（box-one・毎朝）", "cron": "0 6 * * *"},
    {"id": "aaaa0005", "label": "落ちた便", "cron": "0 7 * * *"},
    {"id": "aaaa0006", "label": "隠れた落ちの便（用無しの周で上書き）", "cron": "0 8 * * *", "check": "exit 1"},
    {"id": "aaaa0007", "label": "返事の周（09 時・返A が交互に返す・reply-bot で読む）", "cron": "0 9 * * *"},
]
FIRES = [
    {"schedule_id": "aaaa0001", "result": "spawned"},
    {"schedule_id": "aaaa0002", "result": "skipped_policy", "detail": "check=用無し（exit 1）"},
    {"schedule_id": "aaaa0004", "result": "done_self"},
    {"schedule_id": "aaaa0005", "result": "error"},
    {"schedule_id": "aaaa0006", "result": "timeout"},
    {"schedule_id": "aaaa0006", "result": "skipped_policy", "detail": "check=用無し（exit 1）"},
    {"schedule_id": "aaaa0007", "result": "skipped_running"},
]
ROUTINES = [{"id": "bbbb0001", "name": "site-daily", "cron": "0 5 * * *"}]
ROUTINE_RUNS = [{"routine_id": "bbbb0001", "result": "ok"}]
TSV = ["sweep-watch\t成功", "site-daily\t成功", "box-one の周\t成功", "reply-bot の周\t成功"]


def jl(rows):
    return "".join(json.dumps(dict(r, ts=TS), ensure_ascii=False) + "\n" for r in rows)


class BinCount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.tmp.name
        sd, rd = os.path.join(t, "sched"), os.path.join(t, "routine")
        os.makedirs(sd), os.makedirs(rd)
        runs = os.path.join(t, "便の実行-2026-01.tsv")
        for path, text in ((os.path.join(sd, "schedules.json"), json.dumps({"schedules": SCHEDULES}, ensure_ascii=False)),
                           (os.path.join(sd, "fires.log"), jl(FIRES)),
                           (os.path.join(rd, "routines.json"), json.dumps({"routines": ROUTINES}, ensure_ascii=False)),
                           (os.path.join(rd, "runs.log"), jl(ROUTINE_RUNS)),
                           (runs, "".join(f"{TS}\t{line}\tr1\t\n" for line in TSV))):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        B.SCHED_DIR, B.ROUTINE_DIR = sd, rd
        rows, _src, found = B.read_routine(None, runs)
        assert found
        cls.rows = {r["便"]: r for r in rows}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def row(self, head):
        hits = [r for k, r in self.rows.items() if k.startswith(head)]
        self.assertEqual(len(hits), 1, head)
        return hits[0]

    def test_fail_only_error_timeout(self):
        self.assertTrue(self.row("落ちた便")["fail"])
        self.assertTrue(self.row("隠れた落ち")["fail"], "用無しの周で上書きされた timeout を拾う")
        for ok in ("週の掃除", "見張りだけ", "自分で閉じる", "返事の周", "まだ起きていない"):
            self.assertFalse(self.row(ok)["fail"], ok)

    def test_alias_label_paren_and_routine_name(self):
        self.assertTrue(self.row("週の掃除")["実行"].endswith("成功"), "label の括弧の頭の英語名で引く")
        self.assertTrue(self.row("site-daily")["実行"].endswith("成功"), "routine の name で引く")

    def test_alias_negative_controls(self):
        # box-one は 2 本の便の括弧の頭に出る＝見分けられない語。括弧の途中の reply-bot は名前ではない
        self.assertEqual(self.row("見張りだけ")["実行"], "なし（check だけ）")
        self.assertEqual(self.row("返事の周")["実行"], "なし")

    def test_idle_column_not_counted_as_unrecorded(self):
        self.assertEqual(self.row("見張りだけ")["idle"], "check だけ")
        self.assertFalse(self.row("見張りだけ")["未記録"])
        self.assertEqual(self.row("まだ起きていない")["idle"], "未発火")
        self.assertEqual(self.row("まだ起きていない")["実行"], "なし（未発火）")
        self.assertFalse(self.row("まだ起きていない")["未記録"])

    def test_unrecorded_still_counted(self):
        self.assertTrue(self.row("自分で閉じる")["未記録"], "席が起きたのに窓に無い scheduler の便は数える")
        self.assertEqual(self.row("自分で閉じる")["idle"], "")


if __name__ == "__main__":
    unittest.main()
