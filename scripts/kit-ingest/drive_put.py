#!/usr/bin/env python3
"""原本をクラウド（Google Drive）へ置く（工程 3）。API（rclone）で置き、別経路（API の一覧の md5）で確かめる。消さない。

使い方:
  python3 drive_put.py --work <一時ファイルの箱> --remote <rclone のリモート名> --folder "<実体の置き場>" [--source 出所] [--id id] [--dry-run]
  --dry-run  撃つ呼び出し文を印字するだけ（クラウドに触らない）。それでも placed/<source>/<id>.dryrun を置いて、門が「dry-run で数えた」と分かる形にする
  置けて、別経路の md5 が一致した物だけ placed/<source>/<id>.ok（中身＝リモートの md5）。門はこのファイルを数える。

⛔ この道具はクラウド上で rm・rmdir・mv・delete・purge・sync を撃たない（元の棚の決まり「クラウドの置き場で消さない・動かさない」: 2026-09-08 に 16 万件がゴミ箱行き）。
   使うのは copy（宛先に同名が在れば上書き＝版が増えるだけで消えない）と lsf（読むだけ）。
⛔ ローカルの原本もこの道具は消さない。消してよい一覧を最後に印字するので、席が 4 手順（全数サイズ照合→置き先の可読性→全部通ってから→残存ゼロ確認）を通してから 1 本ずつ消す。
⛔ 同期クライアント（Google Drive for desktop 等）の cp で置かない。同期が止まっていても ls は答え、cp はローカルキャッシュに落ちるだけで上がらない（実測: 「本数が増えた」と確認した直後に原本を消した）。

rclone が無ければ exit 4（席が入れる: brew install rclone／winget install Rclone.Rclone）。接続（rclone config）の OAuth の同意ボタンだけ人が押す。
rclone の罠（元の棚の実測）: copyto は宛先に同名があると古い方をゴミ箱へ（使わない・copy を使う）／同サイズ同時刻は黙って飛ばす（--ignore-times）／
  --config を渡すと既定の設定が置き換わる（渡さない）／親フォルダは名前でなく id で指せる（--drive-root-folder-id）。
"""
import argparse, hashlib, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_complete import ASSET_EXT  # noqa: E402

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


def batch(a):
    """面ごとに 1 回の copy。数百〜数千本の面で 1 本ずつ撃つと一覧 API が本数ぶん走って二乗で遅くなるので、こちらを使う。"""
    if not a.dry_run and not shutil.which("rclone"):
        print("⛔ rclone が無い（席が入れる。人に入れさせない）"); return 4
    media_root = os.path.join(a.work, "media")
    sources = [a.source] if a.source else (sorted(os.listdir(media_root)) if os.path.isdir(media_root) else [])
    total_ok = total = total_dups = 0
    for src in sources:
        d = os.path.join(media_root, src)
        if not os.path.isdir(d):
            continue
        names = [n for n in sorted(os.listdir(d)) if os.path.splitext(n)[1].lower() in ASSET_EXT and ".part" not in n]
        if not names:
            continue
        dest = f"{a.remote}:{a.folder.rstrip('/')}/{src}/"
        pdir = os.path.join(a.work, "placed", src); os.makedirs(pdir, exist_ok=True)
        # 錠: 同じ面を 2 本の処理で同時に copy すると Drive は同名を許すので写しが 2 本できる（実測 2026-11-01: 面 1 つで 5 本）。mkdir は原子的
        lock = os.path.join(a.work, "placed", src + ".lock")
        try:
            os.mkdir(lock)
        except FileExistsError:
            print(f"⛔ 面 {src} は別の処理が置いている最中（{lock} が在る）。終わってから撃つ。止まった処理の残骸なら rmdir で外す")
            total += len(names); continue
        try:
            print(f"put 面 {src}: {len(names)} 本 → {dest}")
            # 置くのは数えた names だけ（フォルダ丸ごとだと取得途中の .part や拡張子の外の物まで置く）
            lst = os.path.join(a.work, "placed", src + ".files")
            with open(lst, "w", encoding="utf-8") as f:
                f.write("".join(n + "\n" for n in names))
            rc, out = rclone(["copy", "--copy-links", "--transfers", str(a.transfers), "--checkers", "8", "--stats-one-line", "--stats", "60s",
                              "--files-from-raw", lst, os.path.abspath(d), dest], a.dry_run)
            os.remove(lst)
            if rc != 0:
                print(f"  ⛔ copy 失敗 {out[-300:]}")
            # 別経路: 一覧 API の md5 を 1 回で取り、全数と突き合わせる
            rc, out = rclone(["lsf", "--format", "psh", "--hash", "MD5", "--files-only", dest], a.dry_run)
        finally:
            os.rmdir(lock)
        remote, seen = {}, {}
        for line in out.splitlines():
            parts = line.rsplit(";", 2)
            if len(parts) == 3:
                remote[parts[0]] = parts[2]; seen[parts[0]] = seen.get(parts[0], 0) + 1
        dups = sorted(n for n, c in seen.items() if c > 1)
        if dups:
            # 消すのは人（Web の画面）。この道具は消さない（X-3）
            print(f"  ⛔ 同名の写しが {len(dups)} 件（例: {dups[:3]}）。並走の写しの重なり。消すのは人が画面で 1 本ずつ")
        ok = 0
        for n in names:
            stem = os.path.splitext(n)[0]
            if os.path.isfile(os.path.join(pdir, stem + ".ok")):
                ok += 1; continue
            lm = md5_local(os.path.join(d, n))
            if remote.get(n) == lm:
                open(os.path.join(pdir, stem + ".ok"), "w").write(lm + "\n"); ok += 1
        miss = [n for n in names if not os.path.isfile(os.path.join(pdir, os.path.splitext(n)[0] + ".ok"))]
        print(f"  面 {src}: 置いた一覧 {len(remote)}・md5 一致 {ok}/{len(names)}" + (f"・不一致/未着 {len(miss)}（例: {miss[:3]}）" if miss else ""))
        total_ok += ok; total += len(names); total_dups += len(dups)
    print(f"--- 全体: md5 一致 {total_ok}/{total}・同名の写し {total_dups}")
    return 0 if total_ok == total and total_dups == 0 else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True)
    ap.add_argument("--remote", required=True, help="rclone listremotes に出る名前（末尾のコロン無し）")
    ap.add_argument("--folder", required=True, help="共有ドライブ内の置き場（例: 原本/動画原本-2026-09）")
    ap.add_argument("--source", default="")
    ap.add_argument("--id", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch", action="store_true",
                    help="面ごとに 1 回で置く（rclone copy をフォルダ単位・並列）。確かめ方は同じ＝一覧の md5 とローカルの md5 を全数で突き合わせ、一致した物だけ .ok")
    ap.add_argument("--transfers", type=int, default=8)
    a = ap.parse_args(argv)
    if a.batch:
        return batch(a)
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
            if ext.lower() not in ASSET_EXT or ".part" in name or (a.id and stem != a.id):
                continue
            if os.path.isfile(os.path.join(pdir, stem + ".ok")):
                print(f"skip {src}/{stem}（別経路で確認済み）"); verified += 1; eligible.append(os.path.join(d, name)); continue
            local = os.path.abspath(os.path.join(d, name))
            print(f"put {src}/{name} → {dest}")
            rc, out = rclone(["copy", "--ignore-times", "--no-traverse", "--copy-links", local, dest], a.dry_run)
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
                parts = line.rsplit(";", 2)
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
