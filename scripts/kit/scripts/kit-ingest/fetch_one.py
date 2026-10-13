#!/usr/bin/env python3
"""取得 1 本（工程 1）。1 本 1 呼び出し・冪等・完全性 3 段つき。並列は呼ぶ側（xargs -P）で決める。

使い方:
  python3 fetch_one.py --work <一時ファイルの箱> --source <出所> --id <id> --url <URL> [--size 申告バイト] [--duration 申告秒]
                       [--kind auto|file|hls|youtube] [--cookie-env 変数名] [--tol 2.0]
  manifest.tsv から回す例（5 列だけ切り出す。title に空白があるので行をそのまま渡さない）:
    tail -n +2 manifest/youtube.tsv | cut -f1,2,3,4,5 | while IFS=$'\t' read -r s i u sz du; do
      python3 fetch_one.py --work W --source "$s" --id="$i" --url="$u" --size="$sz" --duration="$du"; done
  ⚠️ 値は必ず --id="$i" の形（= で繋ぐ）で渡す。先頭がハイフンの id（YouTube に多い）を --id "$i" と離して渡すと
     オプションと読まれて落ちる（元の棚の帳簿 id=369 と同じ型。この道具の実弾でも 1 本目で踏んだ）

種類（--kind auto は URL から判定）:
  file     直リンク（http/https）を curl で落とす。Cookie が要る面は --cookie-env で環境変数の名前を渡す（値は書かない）
  hls      .m3u8 を ffmpeg -c copy で mp4（動画）か m4a（音声だけの m3u8）に
  youtube  youtube.com／youtu.be を yt-dlp で（1080p 上限・cookie は --cookie-env に Netscape 形式ファイルの「パス」を入れた変数名）

終わり方（exit）:
  0  取れた／既に完全な物が在って skip
  1  取れなかった（5 回試した）
  2  鍵切れ（401／403）。殴らず止まる。鍵を取り直してから同じコマンドで再開
  4  道具が無い（ffprobe／yt-dlp／curl）。席が入れる。人に入れさせない

守ること: 出力は media/<source>/<id>.<ext>。途中は .part に書き、3 段（バイト・読める・尺）を通ってから改名する。
        先頭がハイフンの id（YouTube に多い）は引数に化けるので、パスは絶対パスで渡し、URL の前に -- を置く。
        ログは <work>/log/fetch.log に 1 行ずつ（skip／ok／AUTH／FAIL）。心拍はこのログの最終行の時刻。
"""
import argparse, datetime as dt, os, shutil, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_complete import good, media_path, probe_duration  # noqa: E402


def log(work, msg):
    os.makedirs(os.path.join(work, "log"), exist_ok=True)
    with open(os.path.join(work, "log", "fetch.log"), "a", encoding="utf-8") as f:
        f.write(dt.datetime.now().strftime("%m-%d %H:%M:%S ") + msg + "\n")
    print(msg)


def guess_kind(url):
    u = url.lower()
    if "youtube.com/" in u or "youtu.be/" in u:
        return "youtube"
    if ".m3u8" in u:
        return "hls"
    return "file"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def fetch_file(url, part, cookie):
    if not shutil.which("curl"):
        return 4, "curl が無い"
    cmd = ["curl", "-sSL", "--retry", "2", "--retry-delay", "10", "-w", "%{http_code}", "-o", part]
    if cookie:
        cmd += ["-H", "Cookie: " + cookie]
    cmd += ["--", url]
    r = run(cmd)
    code = (r.stdout or "").strip()[-3:]
    if code in ("401", "403"):
        return 2, "code=" + code
    if code and not code.startswith("2"):
        return 1, "code=" + code
    return 0, "code=" + code


def fetch_hls(url, part):
    if not shutil.which("ffmpeg"):
        return 4, "ffmpeg が無い"
    base = ["ffmpeg", "-y", "-v", "error", "-protocol_whitelist", "file,http,https,tcp,tls,crypto", "-i", url]
    if part.endswith(".m4a"):
        r = run(base + ["-vn", "-c:a", "copy", "-bsf:a", "aac_adtstoasc", "-movflags", "+faststart", part])
        if r.returncode != 0:   # copy を拒まれたら 1 回だけ再エンコード
            r = run(base + ["-vn", "-c:a", "aac", "-b:a", "128k", part])
    else:
        r = run(base + ["-c", "copy", "-bsf:a", "aac_adtstoasc", "-movflags", "+faststart", part])
    if r.returncode != 0:
        tail = (r.stderr or "")[-200:]
        if "403" in tail or "401" in tail:
            return 2, tail
        return 1, tail
    return 0, "ffmpeg ok"


def fetch_youtube(url, outdir, id_, cookie_file):
    y = shutil.which("yt-dlp")
    if not y:
        return 4, "yt-dlp が無い"
    # 出力名は id 固定（題名を名前にしない）。1080p 上限・mp4 に寄せる
    cmd = [y, "--no-update", "-q", "--no-warnings", "--no-playlist", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b",
           "--merge-output-format", "mp4", "-o", os.path.join(outdir, id_ + ".%(ext)s"), "--no-part"]
    if cookie_file:
        cmd += ["--cookies", cookie_file]
    cmd += ["--", url]
    r = run(cmd)
    if r.returncode != 0:
        tail = (r.stderr or "")[-300:]
        if "Sign in" in tail or "cookies" in tail or "403" in tail or "Private video" in tail:
            return 2, tail
        return 1, tail
    return 0, "yt-dlp ok"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--size", default="")
    ap.add_argument("--duration", default="")
    ap.add_argument("--kind", default="auto", choices=["auto", "file", "hls", "youtube"])
    ap.add_argument("--cookie-env", default="", help="Cookie ヘッダ（file）か cookies.txt のパス（youtube）が入った環境変数の名前")
    ap.add_argument("--tol", type=float, default=2.0)
    a = ap.parse_args(argv)
    if not shutil.which("ffprobe"):
        log(a.work, f"NOTOOL {a.source}/{a.id} ffprobe が無い"); return 4
    size = int(a.size) if a.size.strip() else None
    dur = float(a.duration) if a.duration.strip() else None
    kind = guess_kind(a.url) if a.kind == "auto" else a.kind
    outdir = os.path.abspath(os.path.join(a.work, "media", a.source))
    os.makedirs(outdir, exist_ok=True)

    have = media_path(a.work, a.source, a.id)
    ok, why = good(have, size, dur, a.tol)
    if ok:
        log(a.work, f"skip {a.source}/{a.id} {why}"); return 0
    if have:
        os.remove(have)   # 不完全な物は消して取り直す（自分の箱の中の途中物だけ）
    cookie = os.environ.get(a.cookie_env, "") if a.cookie_env else ""

    for attempt in range(1, 6):
        if kind == "youtube":
            rc, msg = fetch_youtube(a.url, outdir, a.id, cookie)
            got = media_path(a.work, a.source, a.id)
        else:
            ext = ".m4a" if (kind == "hls" and "audio" in a.url.lower()) else ".mp4"
            part = os.path.join(outdir, a.id + ext + ".part")
            rc, msg = fetch_hls(a.url, part) if kind == "hls" else fetch_file(a.url, part, cookie)
            got = None
            if rc == 0 and os.path.isfile(part):
                if os.path.getsize(part) < 200 and "error code" in open(part, errors="ignore").read(50):
                    os.remove(part); rc, msg = 1, "ratelimit"
                    time.sleep(30 * attempt); continue
                final = part[:-5]
                os.replace(part, final); got = final
            elif os.path.isfile(part):
                os.remove(part)
        if rc == 2:
            log(a.work, f"AUTH {a.source}/{a.id} {msg}"); return 2
        if rc == 4:
            log(a.work, f"NOTOOL {a.source}/{a.id} {msg}"); return 4
        if rc == 0 and got:
            ok, why = good(got, size, dur, a.tol)
            if ok:
                log(a.work, f"ok {a.source}/{a.id} {why} try{attempt}"); return 0
            log(a.work, f"retry{attempt} {a.source}/{a.id} 不完全: {why}")
            os.remove(got)
        else:
            log(a.work, f"retry{attempt} {a.source}/{a.id} {msg.strip()[-120:]}")
        time.sleep(10)
    log(a.work, f"FAIL {a.source}/{a.id}"); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
