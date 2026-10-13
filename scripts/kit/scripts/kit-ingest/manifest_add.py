#!/usr/bin/env python3
"""棚卸し（工程 0）— YouTube 以外。手元のファイル（パソコンの中・同期フォルダ・会議録画の書き出し）か、直リンク／HLS の URL を manifest に足す。

使い方:
  手元のファイル:  python3 manifest_add.py --work W --source <出所> --file <path> [--file ...]      id はファイル名（拡張子なし）・尺は ffprobe 実測
  URL:            python3 manifest_add.py --work W --source <出所> --url <URL> --id <id> [--size N] [--duration S] [--title T] [--container C]
                  会員サイト・講座サイトは、管理画面の一覧 API や埋め込み JSON から id と URL を取って 1 行ずつここへ（席が playwright で取る）
書く先: <work>/manifest/<出所>.tsv（列は verify_complete.COLS）。同じ id は上書きしない（冪等）。
分母の定義: 「1 行＝ファイル 1 本」。1 講義に動画が 2 本なら 2 行（講義で数えると添付の側が落ちる）。
"""
import argparse, csv, datetime as dt, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_complete import COLS, probe_duration  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True); ap.add_argument("--source", required=True)
    ap.add_argument("--file", action="append", default=[]); ap.add_argument("--url", default=""); ap.add_argument("--id", default="")
    ap.add_argument("--size", default=""); ap.add_argument("--duration", default=""); ap.add_argument("--title", default="")
    ap.add_argument("--container", default="")
    a = ap.parse_args(argv)
    out = os.path.join(a.work, "manifest", a.source + ".tsv"); os.makedirs(os.path.dirname(out), exist_ok=True)
    have = {}
    if os.path.isfile(out):
        with open(out, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                have[r["id"]] = r
    today = dt.date.today().isoformat(); new = 0
    rows = []
    for p in a.file:
        p = os.path.abspath(p); id_ = os.path.splitext(os.path.basename(p))[0]
        d = probe_duration(p)
        rows.append({"source": a.source, "id": id_, "url": "file://" + p, "size_bytes": str(os.path.getsize(p)),
                     "duration_sec": f"{d:.2f}" if d is not None else "", "title": id_, "container": os.path.basename(os.path.dirname(p)),
                     "fetched_at": today})
    if a.url:
        if not a.id:
            ap.error("--url には --id が要る")
        rows.append({"source": a.source, "id": a.id, "url": a.url, "size_bytes": a.size, "duration_sec": a.duration,
                     "title": a.title.replace("\t", " "), "container": a.container.replace("\t", " "), "fetched_at": today})
    for r in rows:
        if r["id"] not in have:
            have[r["id"]] = r; new += 1
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter="\t"); w.writeheader()
        for r in have.values():
            w.writerow({c: r.get(c, "") for c in COLS})
    print(f"{a.source}: 本数 {len(have)}（新規 {new}）→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
