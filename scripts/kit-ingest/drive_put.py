#!/usr/bin/env python3
"""原本をクラウド（Google Drive）へ置く（工程 3）。API（rclone）で置き、別経路（API の一覧の md5）で確かめる。消さない。

使い方:
  python3 drive_put.py --work <一時ファイルの箱> --remote <rclone のリモート名> --folder "<実体の置き場>" [--source 出所] [--id id] [--dry-run]
  --dry-run  撃つ呼び出し文を印字するだけ（クラウドに触らない）。それでも placed/<source>/<id>.dryrun を置いて、門が「dry-run で数えた」と分かる形にする
  置けて、別経路の md5 が一致した物だけ placed/<source>/<id>.ok（中身＝リモートの md5）。門はこのファイルを数える。

⛔ この道具はクラウド上で rm・rmdir・mv・delete・purge・sync を撃たない（元の棚の規矩 X-5: 2026-09-08 に 16 万件がゴミ箱行き）。
   使うのは copy（宛先に同名が在れば上書き＝版が増えるだけで消えない）と lsf（読むだけ）。
⛔ ローカルの原本もこの道具は消さない。消してよい一覧を最後に印字するので、席が 4 手順（全数サイズ照合→置き先の可読性→全部通ってから→残存ゼロ確認）を通してから 1 本ずつ消す。
⛔ 同期クライアント（Google Drive for desktop 等）の cp で置かない。同期が止まっていても ls は答え、cp はローカルキャッシュに落ちるだけで上がらない（実測: 「本数が増えた」と確認した直後に原本を消した）。

rclone が無ければ exit 4（席が入れる: brew install rclone／winget install Rclone.Rclone）。接続（rclone config）の OAuth の同意ボタンだけ人が押す。
rclone の罠（元の棚の実測）: copyto は宛先に同名があると古い方をゴミ箱へ（使わない・copy を使う）／同サイズ同時刻は黙って飛ばす（--ignore-times）／
  --config を渡すと既定の設定が置き換わる（渡さない）／親フォルダは名前でなく id で指せる（--drive-root-folder-id）。
"""
import argparse, hashlib, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_complete import MEDIA_EXT  # noqa: E402

FORBIDDEN = ("delete", "purge", "sync", "move", "moveto", "rmdir", "rmdirs", "cleanup", "deletefile")


def md5_local(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rclone(args, dry):
    cmd = ["rclone"] + args
    assert cmd[1] not in FORBIDDEN, "⛔ 消す系の副命令は撃たない"
    if dry:
        print("  $ " + " ".join(cmd)); return 0, ""
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True)
    ap.add_argument("--remote", required=True, help="rclone listremotes に出る名前（末尾のコロン無し）")
    ap.add_argument("--folder", required=True, help="共有ドライブ内の置き場（例: 原本/動画原本-2026-09）")
    ap.add_argument("--source", default="")
    ap.add_argument("--id", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not a.dry_run and not shutil.which("rclone"):
        print("⛔ rclone が無い（席が入れる。人に入れさせない）"); return 4
    media_root = os.path.join(a.work, "media")
    sources = [a.source] if a.source else (sorted(os.listdir(media_root)) if os.path.isdir(media_root) else [])
    put = verified = 0
    eligible = []
    for src in sources:
        d = os.path.join(media_root, src)
        if not os.path.isdir(d):
            continue
        dest = f"{a.remote}:{a.folder.rstrip('/')}/{src}/"
        pdir = os.path.join(a.work, "placed", src); os.makedirs(pdir, exist_ok=True)
        for name in sorted(os.listdir(d)):
            stem, ext = os.path.splitext(name)
            if ext.lower() not in MEDIA_EXT or ".part" in name or (a.id and stem != a.id):
                continue
            if os.path.isfile(os.path.join(pdir, stem + ".ok")):
                print(f"skip {src}/{stem}（別経路で確認済み）"); verified += 1; eligible.append(os.path.join(d, name)); continue
            local = os.path.abspath(os.path.join(d, name))
            print(f"put {src}/{name} → {dest}")
            rc, out = rclone(["copy", "--ignore-times", "--no-traverse", local, dest], a.dry_run)
            if a.dry_run:
                rclone(["lsf", "--format", "psh", "--hash", "MD5", "--files-only", dest], True)
                print(f"  → 比べる: ローカル md5 と一覧の md5 が同じなら placed/{src}/{stem}.ok を置く")
                open(os.path.join(pdir, stem + ".dryrun"), "w").write("dry-run\n"); put += 1; continue
            if rc != 0:
                print(f"  ⛔ copy 失敗 {out[-200:]}"); continue
            put += 1
            # 別経路: 置いたのと別の口（一覧 API の md5）で確かめる
            rc, out = rclone(["lsf", "--format", "psh", "--hash", "MD5", "--files-only", dest], False)
            remote_md5 = ""
            for line in out.splitlines():
                parts = line.split(";")
                if len(parts) == 3 and parts[0] == name:
                    remote_md5 = parts[2]
            lm = md5_local(local)
            if remote_md5 and remote_md5 == lm:
                open(os.path.join(pdir, stem + ".ok"), "w").write(remote_md5 + "\n")
                verified += 1; eligible.append(local); print(f"  ✅ md5 一致 {lm}")
            else:
                print(f"  ⛔ md5 不一致 ローカル {lm} リモート {remote_md5 or '（一覧に無い）'}——.ok は置かない")
    print(f"--- 置いた {put}・別経路で一致 {verified}" + ("（dry-run）" if a.dry_run else ""))
    if eligible and not a.dry_run:
        print("ローカルを消してよい候補（席が 4 手順を通してから 1 本ずつ。この道具は消さない）:")
        for p in eligible:
            print("  " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
