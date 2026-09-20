#!/usr/bin/env python3
"""棚卸し（工程 0）— YouTube。チャンネル／再生リスト／動画の URL から manifest/youtube.tsv を作る。落とさない。

使い方:
  python3 inventory_youtube.py --work <一時ファイルの箱> --url <チャンネル or 再生リスト or 動画 URL> [--url ...] [--cookie-env 変数名]
  チャンネルは https://www.youtube.com/@<handle>/videos の形で渡す（ライブ・ショートは /streams /shorts を別に渡す）。
  --cookie-env: cookies.txt（Netscape 形式）のパスが入った環境変数の名前。「Sign in to confirm you're not a bot」が出た機体はこれが要る。
    cookie は席が playwright（ログイン済みプロファイル）から取り、一時領域に置き、終わったら消す。人に取らせない。

何を書くか: source=youtube・id・url・size_bytes（空。形式ごとにサイズが違うので申告値は使わず、完全性は尺で判定）・duration_sec・title・container（チャンネル名）・fetched_at（今日）
  既に在る行（同じ id）は上書きしない（冪等・追記）。分母はこのファイルの行数になる。数え終わったら本数と合計時間を印字する。
"""
import argparse, csv, datetime as dt, json, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_complete import COLS  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True); ap.add_argument("--url", action="append", required=True)
    ap.add_argument("--cookie-env", default="")
    a = ap.parse_args(argv)
    y = shutil.which("yt-dlp")
    if not y:
        print("⛔ yt-dlp が無い（席が入れる: brew install yt-dlp／winget install yt-dlp）"); return 4
    out = os.path.join(a.work, "manifest", "youtube.tsv"); os.makedirs(os.path.dirname(out), exist_ok=True)
    have = {}
    if os.path.isfile(out):
        with open(out, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                have[r["id"]] = r
    cookie = os.environ.get(a.cookie_env, "") if a.cookie_env else ""
    new = 0; today = dt.date.today().isoformat()
    for u in a.url:
        cmd = [y, "--no-update", "--no-warnings", "--skip-download", "--flat-playlist", "-J", "--"]
        if cookie:
            cmd[1:1] = ["--cookies", cookie]
        r = subprocess.run(cmd + [u], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            print(f"⛔ 一覧が取れない {u}: {(r.stderr or '')[-200:].strip()}"); return 2 if "Sign in" in (r.stderr or "") else 1
        d = json.loads(r.stdout)
        entries = d.get("entries") if d.get("_type") == "playlist" else [d]
        for e in entries or []:
            if not e or not e.get("id"):
                continue
            vid = e["id"]
            if vid in have:
                continue
            # 一覧（flat）には尺・サイズが無いことがある → 1 本ずつ取る（落とさない）
            if e.get("duration") is None:
                r2 = subprocess.run(cmd + [f"https://www.youtube.com/watch?v={vid}"], capture_output=True, text=True)
                if r2.returncode == 0 and r2.stdout.strip():
                    e = json.loads(r2.stdout)
            have[vid] = {"source": "youtube", "id": vid, "url": f"https://www.youtube.com/watch?v={vid}",
                         "size_bytes": "",   # YouTube は形式ごとにサイズが違い申告値が使えない。完全性は尺で見る
                         "duration_sec": str(e.get("duration") or ""),
                         "title": (e.get("title") or "").replace("\t", " "), "container": (e.get("channel") or e.get("uploader") or "").replace("\t", " "),
                         "fetched_at": today}
            new += 1
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter="\t"); w.writeheader()
        for r in have.values():
            w.writerow({c: r.get(c, "") for c in COLS})
    secs = sum(float(r["duration_sec"] or 0) for r in have.values())
    print(f"youtube: 本数 {len(have)}（新規 {new}）・合計 {secs/3600:.1f} 時間 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
