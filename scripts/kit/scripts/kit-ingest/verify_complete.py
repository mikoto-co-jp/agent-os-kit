#!/usr/bin/env python3
"""完全性判定（取得した動画・音声が「全部」入っているか）。道具の共通部＋門。

3 段で判定する（1 段でも落ちたら不完全）:
  1. バイト数    manifest の申告 size_bytes の 97% 以上（申告が無ければ 1 バイト以上）
  2. 読める      ffprobe が尺を読める（途中で切れた mp4 は moov が無く読めない）
  3. 尺          manifest の申告 duration_sec と ±tol 秒（既定 2.0。申告が無ければ飛ばす）
理由: ffmpeg／curl は途中で切れても黙って exit 0 で終わることがある。尺は末尾の欠落しか捕まえず、バイトは
      申告と数百 KB ずれる。だから両方かける（元の棚の実測 2 件: 19:58 対 22:50・786 秒 対 2,587 秒）。

使い方:
  python3 verify_complete.py --work <一時ファイルの箱> [--manifest <manifest.tsv> ...] [--tol 2.0]
    manifest の全行について media/<source>/<id>.* を判定し、一覧と件数を出す。全部通れば exit 0、1 本でも欠ければ exit 1。
  他の道具からは good(path, size, duration, tol) を import して使う。

manifest.tsv の列（タブ区切り・1 行目が見出し）:
  source  id  url  size_bytes  duration_sec  title  container  fetched_at
  size_bytes・duration_sec は取れなければ空。1 行＝ファイル 1 本（講義ではない。1 講義に動画が 2 本なら 2 行）。
"""
import argparse, csv, glob, os, shutil, subprocess, sys

MEDIA_EXT = (".mp4", ".m4a", ".mp3", ".mov", ".mkv", ".webm", ".wav", ".m4v", ".aac", ".ogg", ".flac")
COLS = ["source", "id", "url", "size_bytes", "duration_sec", "title", "container", "fetched_at"]


def ffprobe_bin():
    return shutil.which("ffprobe") or ""


def probe_duration(path):
    """ffprobe の実測秒（float）。読めなければ None。先頭ハイフンの名前でも壊れないよう絶対パスで渡す。"""
    p = ffprobe_bin()
    if not p:
        return None
    r = subprocess.run([p, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.abspath(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def has_audio(path):
    p = ffprobe_bin()
    if not p:
        return True
    r = subprocess.run([p, "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                        os.path.abspath(path)], capture_output=True, text=True)
    return "audio" in r.stdout


def good(path, size=None, duration=None, tol=2.0):
    """(ok, 理由)。size・duration は manifest の申告（無ければ None）。"""
    if not path or not os.path.isfile(path):
        return False, "ファイルが無い"
    got = os.path.getsize(path)
    if got <= 0:
        return False, "0 バイト"
    if size:
        if got < int(size) * 97 // 100:
            return False, f"バイト不足 {got}/{size}"
    d = probe_duration(path)
    if d is None:
        return False, "ffprobe が尺を読めない（途中で切れている）"
    if duration:
        if abs(d - float(duration)) > tol:
            return False, f"尺のずれ 実測 {d:.1f}s 申告 {float(duration):.1f}s（許容 ±{tol}s）"
    return True, f"ok {got}B {d:.1f}s"


def read_manifest(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        for c in COLS:
            r.setdefault(c, "")
    return rows


def manifest_paths(work):
    return sorted(glob.glob(os.path.join(work, "manifest", "*.tsv")))


def media_path(work, source, id_):
    """media/<source>/<id>.<ext> を探す（拡張子は問わない・途中断片は除く）。無ければ None。"""
    d = os.path.join(work, "media", source)
    if not os.path.isdir(d):
        return None
    for name in sorted(os.listdir(d)):
        stem, ext = os.path.splitext(name)
        if stem == id_ and ext.lower() in MEDIA_EXT and ".part" not in name and ".temp" not in name:
            return os.path.join(d, name)
    return None


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True)
    ap.add_argument("--manifest", nargs="*", help="省けば <work>/manifest/*.tsv 全部")
    ap.add_argument("--tol", type=float, default=2.0)
    a = ap.parse_args(argv)
    if not ffprobe_bin():
        print("⛔ ffprobe が無い（席が入れる。人に入れさせない）"); return 4
    mans = a.manifest or manifest_paths(a.work)
    if not mans:
        print("⛔ manifest が無い（工程 0 が先）"); return 1
    n = ok = 0
    bad = []
    for m in mans:
        for r in read_manifest(m):
            n += 1
            p = media_path(a.work, r["source"], r["id"])
            g, why = good(p, r["size_bytes"] or None, r["duration_sec"] or None, a.tol)
            print(("OK " if g else "NG ") + f"{r['source']}/{r['id']}  {why}")
            if g:
                ok += 1
            else:
                bad.append(f"{r['source']}/{r['id']}: {why}")
    print(f"--- 分母 {n}・完全 {ok}・欠け {len(bad)}")
    for b in bad:
        print("  NG " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
