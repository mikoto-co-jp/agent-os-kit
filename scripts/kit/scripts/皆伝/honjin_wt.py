#!/usr/bin/env python3
"""席ごとに 本陣 と 中の OS の作業木を切り、他席に触れずに commit/push する（皆伝の機体だけに置く・器の版 本陣-1）。

皆伝の機体は席（常駐の席・便）が何体も同時に本陣で起きる。git の index は 1 本しかなく全席で共有される（規矩 X-1'）ので、
1 席がフォルダを動かしている間、他席の git は index.lock で落ちるか、他席の動かし途中を自分の commit に拾う。
⇒ 席は自分の作業木で手を動かし、保存はこの道具で道を全部書いて 1 回で撃つ（開発の陣の席ごとの作業木と同じ形）。

本陣の中に中の OS が別の保管場所として入れ子になっている（本陣の .gitignore に `<中の OS>/`）。
⇒ 席の作業木も**入れ子で 2 本**切る: `<作業場>/<本陣>-wt-<席ID>/` と、その中の `<中の OS>/`。
   こうすると `scripts -> <中の OS>/scripts` の別名も、本陣の hook（core.hooksPath=scripts/git-hooks）も、席の作業木の中で今と同じに解ける。
   ⛔ 片方だけ切らない——中の OS が無いと本陣の hook の置き場が空になり、**門が黙って撃たれない**（git は hook が無ければ何も言わない）。
中の OS の名前は本陣の `scripts` の別名の先から読む（固有値を書かない）。⛔ 外への写し（origin）が無い棚では撃たない（作業木は origin/main から切る）。

usage:
  python3 honjin_wt.py open <short_id>               席の作業木 2 本を切る（在ればそのパスを返すだけ）。stdout 最終行＝本陣側のパス
  python3 honjin_wt.py sync                          自席の作業木 2 本を origin/main へ追随させる（cwd が自席の作業木の中）
  python3 honjin_wt.py push -m <msg> -- <path>...    <path> だけを commit して origin/main へ push する。
                                                     `<中の OS>/` で始まる道は中の OS の作業木で、それ以外は本陣の作業木で commit する
  python3 honjin_wt.py close                         自席の作業木 2 本を畳む。未 commit か未 push が在れば何も消さず rc=1

置き場: 既定は `<本陣>/<中の OS>/11一時ファイル/作業場/`（両方の保管場所で git の外＝**規則を 1 行も足さずに置ける**）。
        `HONJIN_WT_DIR` で替えられる。対象の本陣は `HONJIN_ROOT`（既定はこの道具の置き場から引く）。
        ⛔ 作業場が git の外でなければ切らない（check-ignore で確かめる）。
"""
import os
import re
import subprocess
import sys

REMOTE = "origin"
BRANCH = "main"
INNER = None   # 中の OS の名前。本陣の scripts の別名の先から読む（_inner）
ARCHIVED_BOXES = "09アーカイブ/案件"
PUSH_TRIES = 5


class Stop(Exception):
    def __init__(self, rc, msg):
        super().__init__(msg)
        self.rc = rc


def git(*args, cwd=None, check=True, env=None):
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    if check and p.returncode != 0:
        raise Stop(2, f"❌ git {' '.join(args)} が失敗（rc={p.returncode}）: {p.stderr.strip()}")
    return p


def honjin_root():
    """対象の本陣。`HONJIN_ROOT` が無ければ**本器の置き場から引く**（cwd は見ない）:
    中の OS/scripts に在れば 中の OS の本体の親、本陣の中（箱の下）に在れば本陣の本体。席の作業木の中の本器から撃っても本体を返す。"""
    if os.environ.get("HONJIN_ROOT"):
        return os.path.realpath(os.environ["HONJIN_ROOT"])
    here = os.path.dirname(os.path.realpath(__file__))
    p = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=here, check=False)
    if p.returncode == 0:
        main = os.path.dirname(os.path.realpath(p.stdout.strip()))
        # 中の OS に在れば その親（本陣の別名 scripts が中の OS を指す）、本陣の中（箱の下）に在れば本陣の本体
        parent = os.path.dirname(main)
        sc = os.path.join(parent, "scripts")
        if os.path.islink(sc) and os.path.realpath(sc) == os.path.join(main, "scripts"):
            return parent
        return main
    raise Stop(2, "⛔ 本陣が分からない。HONJIN_ROOT を渡すか、本陣の中の道具から撃つ")


def _inner(root):
    """中の OS の名前＝本陣の scripts（別名）の先の親のフォルダ名。別名でなければ本陣の形ではない"""
    global INNER
    if INNER:
        return INNER
    sc = os.path.join(root, "scripts")
    if not os.path.islink(sc):
        raise Stop(2, f"⛔ {sc} が別名でない＝本陣の形ではない（古い形の棚は先に honjin.py move）")
    tgt = os.path.realpath(sc)
    if os.path.dirname(os.path.dirname(tgt)) != os.path.realpath(root):
        raise Stop(2, f"⛔ {sc} の先（{tgt}）が本陣の中の OS ではない")
    INNER = os.path.basename(os.path.dirname(tgt))
    return INNER


def _need_origin(repo):
    if git("remote", "get-url", REMOTE, cwd=repo, check=False).returncode != 0:
        raise Stop(2, f"⛔ {repo} に外への写し（{REMOTE}）が無い。この道具は外への写しを作った後の皆伝の機体で使う")


def workspace(root):
    return os.environ.get("HONJIN_WT_DIR") or os.path.join(root, _inner(root), "11一時ファイル", "作業場")


def _common(cwd):
    return os.path.realpath(git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd).stdout.strip())


def _worktrees(repo):
    out = git("worktree", "list", "--porcelain", cwd=repo).stdout
    return {os.path.realpath(l.split(" ", 1)[1]) for l in out.splitlines() if l.startswith("worktree ")}


def _ensure_ignored(root, ws):
    """作業場が本陣でも中の OS でも git の外か。外でなければ切らない（作業木が git status に出て、誰かの add に混じる）。"""
    os.makedirs(ws, exist_ok=True)
    for repo in (root, os.path.join(root, INNER)):
        rel = os.path.relpath(os.path.realpath(ws), os.path.realpath(repo))
        if rel.startswith(".."):
            continue                               # その保管場所の外＝関係ない
        if git("check-ignore", "-q", rel + "/", cwd=repo, check=False).returncode != 0:
            raise Stop(2, f"⛔ 作業場 {ws} が {repo} の git の外ではない。.gitignore に載せてから（または HONJIN_WT_DIR を替えて）撃つ")


def cmd_open(short_id):
    if not re.fullmatch(r"[0-9a-f]{8}", short_id or ""):
        raise Stop(2, f"❌ short_id は 16 進 8 桁（例: 1dcde143）: {short_id!r}")
    root = honjin_root()
    inner_root = os.path.join(root, _inner(root))
    _need_origin(root); _need_origin(inner_root)
    ws = workspace(root)
    _ensure_ignored(root, ws)
    dest = os.path.join(ws, f"{os.path.basename(root)}-wt-{short_id}")
    inner_dest = os.path.join(dest, INNER)

    if os.path.exists(dest):
        if os.path.realpath(dest) not in _worktrees(root):
            raise Stop(2, f"⛔ {dest} は在るが本陣の作業木ではない。⛔ 消さない——持ち主を確かめてから")
        print(f"✅ 本陣の作業木は既に在る（作り直さない）: {dest}")
    else:
        git("fetch", "-q", REMOTE, BRANCH, cwd=root)
        git("worktree", "add", "-q", "--no-checkout", "--detach", dest, f"{REMOTE}/{BRANCH}", cwd=root)
        if not os.environ.get("HONJIN_WT_FULL"):
            # 🔑 凍結した箱（09アーカイブ/案件/<slug>/）の中身は写さない（本陣の重さの大半がここに溜まる＝席ごとに丸ごと写すと重い）。
            #    墓標の 1 枚（案件/<slug>.md）は残る。
            #    ⚠️ 箱を凍結で 案件/<slug>/ へ動かすときは `git mv --sparse`（外した道へ動かすため）。丸ごと要る席は HONJIN_WT_FULL=1
            git("sparse-checkout", "set", "--no-cone", "/*", f"!/{ARCHIVED_BOXES}/*/", cwd=dest)
        git("checkout", "-q", "--detach", f"{REMOTE}/{BRANCH}", cwd=dest)
        print(f"✅ 本陣の作業木を切った: {dest}（detached @ {REMOTE}/{BRANCH}）")

    if os.path.exists(inner_dest):
        if os.path.realpath(inner_dest) not in _worktrees(inner_root):
            raise Stop(2, f"⛔ {inner_dest} は在るが中の OS の作業木ではない。⛔ 消さない——持ち主を確かめてから")
        print(f"✅ 中の OS の作業木は既に在る（作り直さない）: {inner_dest}")
    else:
        git("fetch", "-q", REMOTE, BRANCH, cwd=inner_root)
        git("worktree", "add", "-q", "--detach", inner_dest, f"{REMOTE}/{BRANCH}", cwd=inner_root)
        print(f"✅ 中の OS の作業木を切った: {inner_dest}（detached @ {REMOTE}/{BRANCH}）")

    # 🚪 本陣の hook が席の作業木の中で解けるか（scripts -> 中の OS/scripts の別名を通る）
    hp = git("config", "--get", "core.hooksPath", cwd=dest, check=False).stdout.strip()
    if hp and not os.path.exists(os.path.join(dest, hp, "pre-commit")):
        raise Stop(2, f"🚨 本陣の hook（{hp}/pre-commit）が席の作業木で解けない＝門が黙って撃たれない。commit しない")
    print(dest)
    return 0


def own_pair(cwd):
    """cwd から自席の (本陣の作業木, 中の OS の作業木) を返す。共有の本陣のルートや別リポなら撃たせない。"""
    root = honjin_root()
    inner_root = os.path.join(root, _inner(root))
    top = os.path.realpath(git("rev-parse", "--show-toplevel", cwd=cwd).stdout.strip())
    common = _common(cwd)
    if common == _common(inner_root):                      # 中の OS の作業木の中から撃った
        inner_top, top = top, os.path.dirname(top)
    elif common == _common(root):
        inner_top = os.path.join(top, INNER)
    else:
        raise Stop(2, f"⛔ ここ（{cwd}）は本陣の作業木ではない（別リポ）")
    if top == root or inner_top == os.path.realpath(inner_root):
        raise Stop(2, f"⛔ ここは本陣のルート（全席の作業場所）。撃たない。先に `honjin_wt.py open <自分の short_id>` で自席の作業木を切り、そこで撃つ")
    if not re.fullmatch(r".+-wt-[0-9a-f]{8}", os.path.basename(top)):
        raise Stop(2, f"⛔ {top} は席の作業木の名前（<本陣>-wt-<席ID>）ではない")
    if not os.path.isdir(inner_top) or os.path.realpath(inner_top) not in _worktrees(inner_root):
        raise Stop(2, f"🚨 {inner_top} に中の OS の作業木が無い。`open` を撃ち直す（無いままでは本陣の hook が解けない）")
    return top, inner_top


def replay(top, onto):
    """自席の未 push commit を onto の上へ作業木に触れずに積み直し、新しい先頭を返す。競合なら Stop(1)。"""
    commits = git("rev-list", "--reverse", "HEAD", "--not", onto, cwd=top).stdout.split()
    head = git("rev-parse", onto, cwd=top).stdout.strip()
    for c in commits:
        parent = git("rev-parse", f"{c}^", cwd=top).stdout.strip()
        mt = git("merge-tree", "--write-tree", "--name-only", f"--merge-base={parent}", head, c, cwd=top, check=False)
        if mt.returncode == 1:
            files = mt.stdout.split("\n\n", 1)[0].splitlines()[1:]
            raise Stop(1, f"⚠️ 競合: 自席の commit {c[:8]} が上流と同じ所を変えている（{', '.join(files) or '不明'}）。"
                          f"何も動かしていない。上流を読んでから直して撃ち直す")
        if mt.returncode != 0:
            raise Stop(2, f"❌ merge-tree が失敗: {mt.stderr.strip()}")
        tree = mt.stdout.splitlines()[0]
        meta = git("log", "-1", "--format=%an%x00%ae%x00%aI%x00%B", c, cwd=top).stdout
        an, ae, ad, msg = meta.split("\0", 3)
        p = subprocess.run(["git", "commit-tree", tree, "-p", head], cwd=top, input=msg, capture_output=True, text=True,
                           env={**os.environ, "GIT_AUTHOR_NAME": an, "GIT_AUTHOR_EMAIL": ae, "GIT_AUTHOR_DATE": ad})
        if p.returncode != 0:
            raise Stop(2, f"❌ commit-tree が失敗: {p.stderr.strip()}")
        head = p.stdout.strip()
    return head


def move_to(top, new):
    p = git("checkout", "-q", "--detach", new, cwd=top, check=False)
    if p.returncode != 0:
        raise Stop(1, f"⚠️ 競合: 自席の未 commit が上流の変更と同じファイルに在る。何も動かしていない。\n{p.stderr.strip()}")


def _sync_one(top):
    git("fetch", "-q", REMOTE, BRANCH, cwd=top)
    new = replay(top, f"{REMOTE}/{BRANCH}")
    move_to(top, new)
    return new


def cmd_sync(cwd):
    top, inner_top = own_pair(cwd)
    a, b = _sync_one(top), _sync_one(inner_top)
    print(f"✅ 追随した: 本陣={a[:8]} 中の OS={b[:8]}（stash 不使用・自席の未 commit はそのまま）")
    return 0


def push_head(top, label):
    for i in range(1, PUSH_TRIES + 1):
        git("fetch", "-q", REMOTE, BRANCH, cwd=top)
        new = replay(top, f"{REMOTE}/{BRANCH}")
        p = git("push", "-q", REMOTE, f"{new}:refs/heads/{BRANCH}", cwd=top, check=False)
        if p.returncode == 0:
            print(f"✅ {label} を push した: {REMOTE}/{BRANCH}={new[:8]}（{i} 回目）")
            try:
                move_to(top, new)
            except Stop as e:
                raise Stop(1, f"⚠️ push は済んだが作業木は追随していない（自席の未 commit が上流と重なる）。{e}")
            return 0
        print(f"… {label} の push 拒否（他席が先に push した）→ 取り直して積み直す（{i}/{PUSH_TRIES}）", file=sys.stderr)
    raise Stop(2, f"❌ {label}: {PUSH_TRIES} 回続けて push が拒否された。commit は自席の HEAD に在る（消えていない）")


def _in_archived(p):
    p = os.path.normpath(p)
    return p == ARCHIVED_BOXES or p.startswith(ARCHIVED_BOXES + os.sep)


def _sparse_staged(top, paths):
    """道の下で、sparse の外（skip-worktree）の印が付いたまま HEAD と違う物を index に積んでいる道。
    `git commit -- <道>` は手元の実物から commit を作り直すので、印の付いた物を見ずに飛ばす（漏れる）。"""
    skip = {l[2:] for l in git("ls-files", "-t", "-z", "--", *paths, cwd=top).stdout.split("\0") if l.startswith("S ")}
    staged = git("diff", "--cached", "--name-only", "--no-renames", "-z", "--", *paths, cwd=top).stdout.split("\0")
    return skip.intersection(staged)


def _commit_from_index(top, msg, paths, label):
    # 🔑 rebase・sync の checkout は sparse を当て直し、`git mv --sparse` で 案件/ へ動かした物を手元から消して
    #    skip-worktree の印を付ける。`git commit -- <道>` はその物を飛ばし、旧い道の削除だけが commit される
    #    （手本の棚で実際に数百本が漏れた）。
    #    ⇒ その時だけ、一時の index（HEAD ＋ 自席の index の <道> の下）を作って commit する。<道> の外は入らない（-- <道> と同じ）。
    tmp = os.path.join(git("rev-parse", "--absolute-git-dir", cwd=top).stdout.strip(), "honjin_wt-index")
    env = {"GIT_INDEX_FILE": tmp}
    try:
        git("read-tree", "HEAD", cwd=top, env=env)
        git("rm", "-r", "-q", "--cached", "--ignore-unmatch", "--sparse", "--", *paths, cwd=top, env=env)
        entries = git("ls-files", "-s", "-z", "--", *paths, cwd=top).stdout
        if entries:
            p = subprocess.run(["git", "update-index", "-z", "--index-info"], cwd=top, input=entries,
                               capture_output=True, text=True, env={**os.environ, **env})
            if p.returncode != 0:
                raise Stop(2, f"❌ {label}: 一時の index に積めない: {p.stderr.strip()}")
        p = subprocess.run(["git", "commit", "-q", "-m", msg], cwd=top, capture_output=True, text=True,
                           env={**os.environ, **env})
        sys.stdout.write(p.stdout); sys.stderr.write(p.stderr)
        if p.returncode != 0:
            raise Stop(2, f"❌ {label}: commit が失敗（hook が止めた可能性・上の出力を読む）rc={p.returncode}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    if git("diff", "--cached", "--quiet", "HEAD", "--", *paths, cwd=top, check=False).returncode != 0:
        raise Stop(2, f"🚨 {label}: commit の後も <道> の下に index と HEAD の差が残る（漏れ）。push しない")
    return True


def _commit(top, msg, paths, label):
    # 🔑 git mv（フォルダを動かす）を新旧の両方の道で渡せる:
    #    在る道は add、消えた道は index から外すだけ（git mv 済みなら何もしない）。⛔ -A は撃たない（規矩 X-1）
    # 🔑 凍結の箱（09アーカイブ/案件/<slug>/）は open で外した道＝ `git mv --sparse` で動かした先は add も rm も
    #    `--sparse` が無いと「sparse-checkout の外」で落ちる（手本の棚の陰性対照で確かめた）。
    #    ⇒ 案件/ の下の道にだけ `--sparse` を渡す（他の道は今までどおり＝外した道へ黙って書かない）
    here = [p for p in paths if os.path.lexists(os.path.join(top, p))]
    gone = [p for p in paths if p not in here]
    for sparse in (False, True):
        flag = ["--sparse"] if sparse else []
        add = [p for p in here if _in_archived(p) == sparse]
        rm = [p for p in gone if _in_archived(p) == sparse]
        if add:
            git("add", *flag, "--", *add, cwd=top)
        if rm:
            git("rm", "-r", "-q", "--cached", "--ignore-unmatch", *flag, "--", *rm, cwd=top)
    if git("diff", "--cached", "--quiet", "--", *paths, cwd=top, check=False).returncode == 0:
        print(f"— {label}: 差分なし（commit しない）")
        return False
    if _sparse_staged(top, paths):
        return _commit_from_index(top, msg, paths, label)
    p = subprocess.run(["git", "commit", "-q", "-m", msg, "--", *paths], cwd=top, capture_output=True, text=True)
    sys.stdout.write(p.stdout); sys.stderr.write(p.stderr)
    if p.returncode != 0:
        raise Stop(2, f"❌ {label}: commit が失敗（hook が止めた可能性・上の出力を読む）rc={p.returncode}")
    return True


def cmd_push(msg, paths, cwd):
    if not msg or not paths:
        raise Stop(2, "❌ push には -m <msg> と -- <path>... が要る（⛔ 全部は commit しない）")
    top, inner_top = own_pair(cwd)
    outer, inner = [], []
    for p in paths:
        ap = os.path.normpath(p if os.path.isabs(p) else os.path.join(cwd, p))
        rel = os.path.relpath(ap, top)
        if rel.startswith(".."):
            raise Stop(2, f"⛔ {p} は自席の作業木の外")
        if rel == INNER or rel.startswith(INNER + os.sep):
            inner.append(os.path.relpath(ap, inner_top))
        else:
            outer.append(rel)
    # 中の OS を先に: 本陣の commit が中の OS の道具（hook）を新しい形で撃てるように
    if inner and _commit(inner_top, msg, inner, "中の OS"):
        push_head(inner_top, "中の OS")
    if outer and _commit(top, msg, outer, "本陣"):
        push_head(top, "本陣")
    return 0


def _assert_clean_pushed(top, label):
    dirty = git("status", "--porcelain", cwd=top).stdout.strip()
    if dirty:
        raise Stop(1, f"⛔ 畳まない: {label} に未 commit が在る\n{dirty}")
    git("fetch", "-q", REMOTE, BRANCH, cwd=top)
    if git("merge-base", "--is-ancestor", "HEAD", f"{REMOTE}/{BRANCH}", cwd=top, check=False).returncode != 0:
        ahead = git("rev-list", "--count", f"{REMOTE}/{BRANCH}..HEAD", cwd=top).stdout.strip()
        raise Stop(1, f"⛔ 畳まない: {label} に {REMOTE}/{BRANCH} に無い commit が {ahead} 本在る → 先に `push` する")


def cmd_close(cwd):
    top, inner_top = own_pair(cwd)
    root = honjin_root()
    _assert_clean_pushed(inner_top, "中の OS")
    _assert_clean_pushed(top, "本陣")       # 本陣の status は .gitignore で 中の OS/ を見ない＝別に測る
    git("worktree", "remove", inner_top, cwd=os.path.join(root, INNER))
    git("worktree", "remove", top, cwd=root)
    print(f"✅ 畳んだ: {top}（と中の {INNER}）")
    return 0


def main(argv, cwd=None):
    cwd = cwd or os.getcwd()
    try:
        if len(argv) == 2 and argv[0] == "open":
            return cmd_open(argv[1])
        if argv == ["sync"]:
            return cmd_sync(cwd)
        if argv == ["close"]:
            return cmd_close(cwd)
        if argv[:1] == ["push"] and "--" in argv:
            k = argv.index("--")
            opts, paths = argv[1:k], argv[k + 1:]
            msg = opts[1] if len(opts) == 2 and opts[0] == "-m" else None
            return cmd_push(msg, paths, cwd)
        print(__doc__.split("\n\n")[2], file=sys.stderr)
        return 2
    except Stop as e:
        print(str(e), file=sys.stderr)
        return e.rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
