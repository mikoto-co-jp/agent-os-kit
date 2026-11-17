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
  ページの行（html/<source>/<id>.html が在る行）とページの面は verify_pages.py で見る（MEDIA_EXT は動画・音声だけ）。

manifest.tsv の列（タブ区切り・1 行目が見出し）:
  source  id  url  size_bytes  duration_sec  title  container  fetched_at
  size_bytes・duration_sec は取れなければ空。1 行＝ファイル 1 本（講義ではない。1 講義に動画が 2 本なら 2 行）。
"""
import argparse, csv, glob, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MEDIA_EXT = (".mp4", ".m4a", ".mp3", ".mov", ".mkv", ".webm", ".wav", ".m4v", ".aac", ".ogg", ".flac")
# 文書・画像（媒体でない資産）。取得の門は「読める」で判定する（尺は無い）。文字は extract_text.py が出す
DOC_EXT = (".pdf", ".docx", ".pptx", ".xlsx", ".pages", ".key", ".numbers", ".txt", ".md", ".html", ".htm", ".eml",
           ".rtf", ".srt", ".vtt", ".json", ".csv", ".tsv", ".doc", ".ppt", ".xls")
IMG_EXT = (".png", ".jpg", ".jpeg", ".heic", ".gif", ".webp", ".svg", ".tif", ".tiff", ".bmp")
ASSET_EXT = MEDIA_EXT + DOC_EXT + IMG_EXT


def doc_readable(path):
    """文書・画像が開けるか（途中で切れた zip 系・空の PDF を落とす）。(ok, 理由)。"""
    import zipfile
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            with open(path, "rb") as f:
                head = f.read(5)
            if head != b"%PDF-":
                return False, "PDF の頭が無い"
            pi = shutil.which("pdfinfo")
            if pi:
                r = subprocess.run([pi, os.path.abspath(path)], capture_output=True, text=True)
                if r.returncode != 0 or "Pages:" not in r.stdout:
                    if "password" in (r.stderr or "").lower():
                        return True, "ok pdf（合言葉つき）"
                    return False, "pdfinfo が読めない（途中で切れている）"
            return True, "ok pdf"
        if ext in (".docx", ".pptx", ".xlsx", ".pages", ".key", ".numbers"):
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path) as z:
                    if z.testzip() is not None:
                        return False, "zip が壊れている"
                return True, "ok " + ext[1:]
            if ext in (".pages", ".key", ".numbers") and os.path.isdir(path):
                return True, "ok " + ext[1:] + "（束）"
            return False, "zip として開けない"
        if ext in IMG_EXT:
            with open(path, "rb") as f:
                head = f.read(16)
            if ext == ".svg" or head[:4] in (b"\x89PNG", b"GIF8", b"RIFF", b"II*\x00", b"MM\x00*") or head[:2] == b"BM" or head[:3] == b"\xff\xd8\xff" or head[4:8] == b"ftyp":
                return True, "ok image"
            return False, "画像の頭が無い（拡張子と中身が違う）"
        with open(path, "rb") as f:
            raw = f.read(1 << 16)
        if ext in (".doc", ".ppt", ".xls"):
            return True, "ok " + ext[1:]
        bad = raw.decode("utf-8", "replace").count("\ufffd")
        if bad and bad > max(8, len(raw) // 100):   # 1% を超えて壊れている物だけ落とす（数バイトの混入は原文のまま通す）
            # utf-16 はほぼどのバイト列でも読めてしまう＝BOM が在るときだけ。cp932 は 64KB の切れ目で割れた末尾 1 バイトを許す
            cands = [raw, raw[:-1]] if raw[:2] not in (b"\xff\xfe", b"\xfe\xff") else []
            for chunk in cands:
                try:
                    chunk.decode("cp932"); break
                except UnicodeDecodeError:
                    continue
            else:
                if raw[:2] not in (b"\xff\xfe", b"\xfe\xff"):
                    return False, "文字として読めない"
        return True, "ok text"
    except OSError as e:
        return False, f"開けない {e}"

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
    if os.path.splitext(path)[1].lower() not in MEDIA_EXT:
        ok, why = doc_readable(path)
        return ok, (f"{why} {got}B" if ok else why)
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
        if stem == id_ and ext.lower() in ASSET_EXT and ".part" not in name and ".temp" not in name:
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
    from verify_pages import page_html, page_ok
    n = ok = 0
    bad = []
    for m in mans:
        for r in read_manifest(m):
            n += 1
            pg = page_html(a.work, r["source"], r["id"])   # ページの行は verify_pages の ①②③（媒体の 3 段ではない）
            p = media_path(a.work, r["source"], r["id"])
            g, why = page_ok(pg) if pg else good(p, r["size_bytes"] or None, r["duration_sec"] or None, a.tol)
            print(("OK " if g else "NG ") + f"{r['source']}/{r['id']}  {why}")
            if g:
                ok += 1
            else:
                bad.append(f"{r['source']}/{r['id']}: {why}")
    from verify_pages import face_problems, page_faces
    for face in page_faces(a.work):
        for x in face_problems(a.work, face):
            bad.append(f"{face}/(面) {x}")
    print(f"--- 分母 {n}・完全 {ok}・欠け {len(bad)}")
    for b in bad:
        print("  NG " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
