#!/usr/bin/env python3
"""門（工程の終わり）。分母 N（manifest の行数）に対して 取得 N・文字 N・配置 N・台帳 N。1 本でも欠ければ通らない。

使い方:
  python3 gate.py --work <一時ファイルの箱> --shelf <棚のルート> [--ledger <_台帳.csv>] [--allow-dryrun] [--tol 2.0]
  python3 gate.py --selftest        小さな検体（2 本）で 正の対照（通る）と 負制御（1 本消して落ちる）を撃つ

数え方（何をもって在るとするか）:
  分母 N   <work>/manifest/*.tsv の行の合計（source/id が鍵）
  取得     media/<source>/<id>.* が完全性 3 段（バイト・読める・尺 ±tol）を通る
  文字     text/<source>/<id>.txt が在り 1 バイト以上（"(音声トラックなし)" も済み）・<id>.failed が無い
  配置     placed/<source>/<id>.ok（別経路の md5 が一致した印）。--allow-dryrun のときだけ .dryrun も数え、その旨を必ず印字する
  台帳     _台帳.csv に key=<source>-<id> の行が在る
  ついでに 発話密度の外れ値（text/<source>/<id>.meta.json の lines_per_min が 4 未満・音声なし以外）を一覧に出す＝落とさないが引き渡しの紙に載せる

終わり方: 0＝4 列とも N と一致／1＝欠けあり（どの列の何が欠けたか一覧）／3＝--selftest で負制御が落ちなかった（門が死んでいる）
「全数 ✅」は門が落ちることを確かめてからしか信じない。--selftest は本文を直すたびに撃つ。
"""
import argparse, csv, json, os, shutil, struct, sys, tempfile, wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_complete import good, manifest_paths, media_path, read_manifest  # noqa: E402


def count(work, shelf, ledger, allow_dryrun, tol):
    rows = []
    for m in manifest_paths(work):
        rows += read_manifest(m)
    n = len(rows)
    keys = set()
    if ledger and os.path.isfile(ledger):
        with open(ledger, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                keys.add(r.get("key", ""))
    lack = {"取得": [], "文字": [], "配置": [], "台帳": []}
    dry = 0; outliers = []
    faces = {}          # 面 -> [分母, 欠け]（面＝解約の単位。1 面が全数そろえばその会社はやめられる）
    for r in rows:
        s, i = r["source"], r["id"]; tag = f"{s}/{i}"
        f = faces.setdefault(s, [0, 0]); f[0] += 1; hurt = False
        ok, why = good(media_path(work, s, i), r["size_bytes"] or None, r["duration_sec"] or None, tol)
        if not ok:
            lack["取得"].append(f"{tag}: {why}"); hurt = True
        t = os.path.join(work, "text", s, i)
        if not (os.path.isfile(t + ".txt") and os.path.getsize(t + ".txt") > 0) or os.path.isfile(t + ".failed"):
            lack["文字"].append(tag); hurt = True
        elif os.path.isfile(t + ".meta.json"):
            meta = json.load(open(t + ".meta.json", encoding="utf-8"))
            if not meta.get("no_audio") and meta.get("lines_per_min", 99) < 4:
                outliers.append(f"{tag}: {meta.get('lines_per_min')} 行/分（暴走・無音・言語違いを疑う）")
        p = os.path.join(work, "placed", s, i)
        if os.path.isfile(p + ".ok"):
            pass
        elif allow_dryrun and os.path.isfile(p + ".dryrun"):
            dry += 1
        else:
            lack["配置"].append(tag); hurt = True
        if f"{s}-{i}" not in keys:
            lack["台帳"].append(tag); hurt = True
        if hurt:
            f[1] += 1
    return n, lack, dry, outliers, faces


def report(n, lack, dry, outliers, faces=None):
    print(f"分母 N={n} ｜ 取得 {n-len(lack['取得'])} ｜ 文字 {n-len(lack['文字'])} ｜ 配置 {n-len(lack['配置'])}"
          + (f"（うち dry-run {dry}・本番では不可）" if dry else "") + f" ｜ 台帳 {n-len(lack['台帳'])}")
    if faces:
        print("--- 面ごと（面＝解約の単位。全数そろった面だけ、やめてよい）")
        for face in sorted(faces):
            tot, hurt = faces[face]
            print(f"  面 {face}: 分母 {tot} ｜ そろった {tot-hurt}"
                  + ("  ✅ この面は解約してよい" if hurt == 0 else f"  ⛔ {hurt} 件欠け——解約しない"))
    bad = False
    for k, v in lack.items():
        for x in v:
            print(f"  欠け[{k}] {x}"); bad = True
    for o in outliers:
        print(f"  ⚠️ 発話密度 {o}")
    if n == 0:
        print("⛔ 分母が 0（manifest が無い＝工程 0 が先）"); return 1
    print("✅ 門を通った（N=取得=文字=配置=台帳）" if not bad else "⛔ 門で止めた（1 本でも欠ければ終わらない）")
    return 0 if not bad else 1


def make_wav(path, seconds=1.0):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"".join(struct.pack("<h", 0) for _ in range(int(8000 * seconds))))


def selftest():
    if not shutil.which("ffprobe"):
        print("⛔ selftest には ffprobe が要る"); return 4
    t = tempfile.mkdtemp(prefix="gate-selftest-")
    work = os.path.join(t, "work"); shelf = os.path.join(t, "shelf")
    for d in ("manifest", "media/x", "text/x", "placed/x"):
        os.makedirs(os.path.join(work, d))
    os.makedirs(os.path.join(shelf, "09アーカイブ", "カード")); os.makedirs(os.path.join(shelf, "01商品資産", "検体講座"))
    with open(os.path.join(work, "manifest", "x.tsv"), "w", encoding="utf-8") as f:
        f.write("source\tid\turl\tsize_bytes\tduration_sec\ttitle\tcontainer\tfetched_at\n")
        for i in ("a1", "-b2"):
            f.write(f"x\t{i}\thttp://example.invalid/{i}\t\t1.0\t検体 {i}\t検体\t2000-01-01\n")
    for i in ("a1", "-b2"):
        make_wav(os.path.join(work, "media", "x", i + ".wav"))
        open(os.path.join(work, "text", "x", i + ".txt"), "w").write("検体の文字\n")
        json.dump({"lines_per_min": 20, "no_audio": False}, open(os.path.join(work, "text", "x", i + ".meta.json"), "w"))
        open(os.path.join(work, "placed", "x", i + ".ok"), "w").write("md5\n")
        open(os.path.join(shelf, "09アーカイブ", "カード", f"x-{i}.md"), "w", encoding="utf-8").write(
            f"---\nkey: x-{i}\nsource: x\nid: \"{i}\"\norig_title: 検体 {i}\nduration_min: 0\ndrive: 検体/x/{i}.wav\n---\n## 文字起こし\n検体の文字\n")
        open(os.path.join(shelf, "01商品資産", "検体講座", f"{i}.md"), "w", encoding="utf-8").write(f"---\nkey: x-{i}\n---\n検体の文字\n")
    import subprocess
    ledger = os.path.join(shelf, "09アーカイブ", "カード", "_台帳.csv")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_ledger.py"), "--shelf", shelf],
                   check=True, capture_output=True)
    print("== 正の対照（2 本そろっている）")
    if report(*count(work, shelf, ledger, False, 2.0)) != 0:
        print("🚨 selftest: 正しい検体で門が落ちた（門が壊れている）"); shutil.rmtree(t); return 1
    import shutil as _sh
    snap = os.path.join(t, "snap"); _sh.copytree(work, os.path.join(snap, "work")); _sh.copytree(shelf, os.path.join(snap, "shelf"))
    checks = [("文字", lambda: os.remove(os.path.join(work, "text", "x", "-b2.txt"))),
              ("配置", lambda: os.remove(os.path.join(work, "placed", "x", "a1.ok"))),
              ("取得", lambda: open(os.path.join(work, "media", "x", "a1.wav"), "wb").write(b"RIFF")),
              ("台帳", lambda: open(ledger, "w").write("key,source,id\n"))]
    for name, hurt in checks:
        # 毎回そろった状態へ戻してから 1 列だけ欠く（欠けの累積で落ちたのを「その列の門」と誤認しない）
        _sh.rmtree(work); _sh.rmtree(shelf)
        _sh.copytree(os.path.join(snap, "work"), work); _sh.copytree(os.path.join(snap, "shelf"), shelf)
        print(f"== 負制御（{name} だけを 1 本欠く）")
        hurt()
        if report(*count(work, shelf, ledger, False, 2.0)) == 0:
            print(f"🚨 selftest: {name} を欠いたのに門が通った（門が死んでいる）"); _sh.rmtree(t); return 3
    shutil.rmtree(t)
    print("✅ selftest: 正の対照が通り、4 列それぞれの負制御が落ちた")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work"); ap.add_argument("--shelf"); ap.add_argument("--ledger", default="")
    ap.add_argument("--allow-dryrun", action="store_true"); ap.add_argument("--tol", type=float, default=2.0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.work and a.shelf):
        ap.error("--work と --shelf が要る（または --selftest）")
    ledger = a.ledger or os.path.join(a.shelf, "09アーカイブ", "カード", "_台帳.csv")
    return report(*count(a.work, a.shelf, ledger, a.allow_dryrun, a.tol))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
