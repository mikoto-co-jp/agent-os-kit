#!/usr/bin/env python3
"""honjin.py — 本陣（総本部）と中の OS の形を建てる・古い形の棚を本陣へ移す・器の更新の差分を出す（セカンドブレイン設置が撃つ）。

本陣の形（器の版 本陣-1）:
  <本陣>/                 CLAUDE.md・.claude/rules/（3 枚）・00朝廷/・08プロジェクト/・09アーカイブ/・docs/・scripts（中の OS の scripts への別名）
  <本陣>/<棚の名前>/       中の OS＝01〜07・コンテクスト銀行・06エージェント資産・scripts・10私用・11一時ファイル
  保存は 2 か所（本陣／中の OS）。本陣の .gitignore が中の OS を外す。門の配線はどちらも scripts/git-hooks。

usage:
  python3 honjin.py lift <棚>                     古い形（棚 1 つ）の <棚> を、その親を本陣とする形にする（受付・箱・墓標・一覧・規則・地図を親へ上げる）。
                                                  保存はしない（新しく建てた棚はセカンドブレイン設置の「終わったら」の節で保存する）。git の保管場所なら move を使う
  python3 honjin.py move <古い棚> [<本陣>]         古い形の棚を本陣へ移す（<本陣> の既定は <古い棚> の隣の「本陣」）。
                                                  確かめ → 本陣を作る → 棚を中へ → lift → 2 か所に保存（道を全部書く）
                                                  中の OS の門の配線が古い棚の中の絶対の道なら相対に替える（rollback で前の値へ）。
                                                  会員が直した器の道具（器から来たどの版とも違う物）と器の写しが無い道具は替えず、差分を控えへ
  python3 honjin.py check <古い棚> [<本陣>]        move の確かめだけ（何も変えない）
  python3 honjin.py rollback <本陣> <棚の名前>      move を戻す（消さない＝本陣は「本陣-戻した-<日時>」へ名前を変えて残す）
  python3 honjin.py ledger <本陣> [--old <古い道>]  BlueLamp のプロジェクト欄の帳面で、古い道の行を本陣に置き換えて今のプロジェクトにする
                                                  （帳面は既定 ~/.appgenius-ai/projects/projects.json・HONJIN_PROJECTS_JSON で替えられる）
  python3 honjin.py clocks <道>                    時計の控え（routine・scheduler）でその道を読む物を並べる（読むだけ）
  python3 honjin.py version <本陣>                 規則の紙の頭の「器の版」を読む（無ければ「最初の器」）
  python3 honjin.py update <本陣> <新しい器>        器の更新の差分を作る（何も変えない）。<新しい器> は make-kit.sh で切り出した直後の dir。
                                                  差分は <中の OS>/11一時ファイル/器の更新-<日時>/ に置く。最後の行が「== 判定: 更新あり／更新なし」
                                                  ＝更新の有無は中身の違い（道具の 変わる・足す と 紙の差分）だけで決める（器の版の名前は見ない）
  python3 honjin.py update <本陣> <新しい器> --apply-tools    道具（scripts/ のうち器に在る物）を入れ替える。move と同じ見分けで、会員が直した道具と
                                                  器の写しが無い道具は替えず、新しい器との差分を 器の更新-<日時>/器と違う道具/ に置く
  python3 honjin.py update <本陣> <差分の dir> --apply-rules  持ち主の OK の後に、混ぜた紙（規矩・メモリシステム・地図・箱の README）を当てる
  python3 honjin.py kaiden <本陣>                  皆伝の機体にだけ: 席ごとの作業場所の道具（器の写しの scripts/皆伝/honjin_wt.py）を中の OS の scripts/ に置く
  python3 honjin.py selftest                       一時 dir で lift・move・rollback・ledger・update を撃つ（負制御こみ）。exit 0＝合格

⛔ 一括で消さない（rm -r を撃たない）。動かすのは mv だけ・戻すのも mv。⛔ git add -A を撃たない＝保存は道を全部ファイルで渡す。
⛔ 門（pre-commit）を --no-verify で越えない。門で止まったら止まって報告し、rollback で戻せる形のまま置く。
⛔ 同期クライアント（Google Drive・iCloud・Dropbox）の中では撃たない（mv が同期先ごと動く）。
"""
import datetime as dt
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.realpath(__file__))
UP = ["08プロジェクト", "09アーカイブ", "docs"]          # 本陣の直下へ上げる箱（受付は名前を替えて上げる＝下）
DESK_NEW, DESK_OLD = "00朝廷", "00廷議"                  # 受付。古い形の棚は 00廷議 のことがある＝上げるときに 00朝廷 へ
RULES = ".claude/rules"
MAP = "CLAUDE.md"
HONJIN_NAME = "本陣"
SYNC_MARKS = ("Google Drive", "GoogleDrive", "CloudStorage", "Mobile Documents", "iCloud", "Dropbox", "OneDrive")
STATE_DIR = "11一時ファイル"
VERSION_RE = re.compile(r"器の版[:：]\s*\**\s*([^\s（(*。]+)")
FILL_KEYS = ("名前", "呼ばれ方", "事業名", "棚の名前", "棚の置き場", "git remote")
NOW = dt.datetime.now().strftime("%Y%m%d-%H%M%S")


class Stop(Exception):
    pass


def say(m):
    print(m, flush=True)


def git(d, *a, check=True, inp=None):
    p = subprocess.run(["git", "-C", d, "-c", "core.quotepath=false", *a], capture_output=True,
                       input=inp, text=inp is None or isinstance(inp, str))
    if check and p.returncode != 0:
        raise Stop(f"git {' '.join(a[:3])} が落ちた（rc={p.returncode}）: {(p.stderr or '').strip()[:400]}")
    return p


def is_repo(d):
    return os.path.isdir(os.path.join(d, ".git")) or os.path.isfile(os.path.join(d, ".git"))


def in_sync_folder(p):
    rp = os.path.realpath(p)
    return any(m in rp for m in SYNC_MARKS)


def busy_in(d):
    """その道の下を cwd にしている程（会話・便）。lsof が無い機体では測れない＝空で返し、1 行出す"""
    if not shutil.which("lsof"):
        say("⚠️ lsof が無い: その棚の下で起きている程を測れない（席が自分で閉じたことを確かめる）")
        return []
    p = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fn"], capture_output=True, text=True)
    rd = os.path.realpath(d)
    me = os.path.realpath(os.getcwd())
    out = []
    for l in p.stdout.splitlines():
        if l.startswith("n"):
            q = os.path.realpath(l[1:])
            if (q == rd or q.startswith(rd + os.sep)) and q != me:
                out.append(q)
    return sorted(set(out))


def old_form(d):
    """古い形（棚 1 つ）か: 規則と地図が棚の中に在る"""
    return os.path.isfile(os.path.join(d, MAP)) and os.path.isdir(os.path.join(d, RULES))


def write_inner_map(osdir):
    name = os.path.basename(os.path.realpath(osdir))
    txt = (f"# {name}（中の OS）\n\n"
           f"本陣（親のフォルダ）の中の OS。**地図と規則は親の `CLAUDE.md` と `.claude/rules/` の 3 枚**（ここで起動しても載る）。ここに写さない。\n"
           f"受付・箱・墓標・一覧（`00朝廷/`・`08プロジェクト/`・`09アーカイブ/`・`docs/`）は親に在る。保存は 2 か所（本陣／{name}）。\n")
    with open(os.path.join(osdir, MAP), "w", encoding="utf-8") as f:
        f.write(txt)


def honjin_gitignore(name):
    return (f"# 本陣の保存から外す物（器の版 本陣-1）\n"
            f"# 中の OS は自分の保管場所で保存する＝本陣の保存には入れない\n"
            f"{name}/\n"
            f"# 途中物（メモリシステム「一時ファイル の規則」）\n**/一時ファイル/\n"
            f"# 生成物。再生成できる\n.venv/\nnode_modules/\n__pycache__/\n.DS_Store\n.obsidian/\n"
            f"# BlueLamp の VS Code 拡張がプロジェクトごとに掘る空箱\n.appgenius_temp/\n")


# ---------------------------------------------------------------- lift
def lift(osdir, quiet=False):
    """<osdir>（古い形・まだ保存しない）を、その親を本陣とする形にする。動かした道の一覧を返す"""
    osdir = os.path.realpath(osdir)
    hj = os.path.dirname(osdir)
    name = os.path.basename(osdir)
    if not old_form(osdir):
        raise Stop(f"{osdir} は古い形ではない（{MAP} と {RULES}/ が無い）。もう本陣の形なら何もしない")
    clash = [x for x in (MAP, RULES, DESK_NEW, DESK_OLD, *UP) if os.path.lexists(os.path.join(hj, x))]
    if clash:
        raise Stop(f"本陣 {hj} に既に在る: {', '.join(clash)}（上書きしない。別の本陣か、先に持ち主に聞く）")
    moved = []
    desk = DESK_NEW if os.path.isdir(os.path.join(osdir, DESK_NEW)) else DESK_OLD
    if os.path.isdir(os.path.join(osdir, desk)):
        os.rename(os.path.join(osdir, desk), os.path.join(hj, DESK_NEW)); moved.append((desk, DESK_NEW))
    else:
        os.mkdir(os.path.join(hj, DESK_NEW)); open(os.path.join(hj, DESK_NEW, ".gitkeep"), "w").close()
    for d in UP:
        if os.path.lexists(os.path.join(osdir, d)):
            os.rename(os.path.join(osdir, d), os.path.join(hj, d)); moved.append((d, d))
    os.makedirs(os.path.join(hj, ".claude"), exist_ok=True)
    os.rename(os.path.join(osdir, RULES), os.path.join(hj, RULES)); moved.append((RULES, RULES))
    try:
        os.rmdir(os.path.join(osdir, ".claude"))      # 空のときだけ（中に他の物が在れば残る）
    except OSError:
        pass
    os.rename(os.path.join(osdir, MAP), os.path.join(hj, MAP)); moved.append((MAP, MAP))
    write_inner_map(osdir)
    sc = os.path.join(hj, "scripts")
    if not os.path.lexists(sc):
        os.symlink(os.path.join(name, "scripts"), sc)   # 相対の別名＝本陣でも中の OS でも同じ道具
    gi = os.path.join(hj, ".gitignore")
    if not os.path.exists(gi):
        open(gi, "w", encoding="utf-8").write(honjin_gitignore(name))
    if not is_repo(hj):
        git(hj, "init", "-q")
    git(hj, "config", "core.hooksPath", "scripts/git-hooks")
    if not quiet:
        say(f"✅ lift: 本陣 {hj} ／ 中の OS {name}（上げた物: {', '.join(a if a == b else f'{a}→{b}' for a, b in moved)}・別名 scripts→{name}/scripts）")
    return moved


# ---------------------------------------------------------------- move
def default_honjin(old):
    return os.path.join(os.path.dirname(os.path.realpath(old)), HONJIN_NAME)


def check(old, hj):
    old = os.path.realpath(old)
    if in_sync_folder(old) or in_sync_folder(os.path.dirname(hj)):
        raise Stop(f"{old} が同期フォルダの中に在る（mv が同期先ごと動く）。止まって報告")
    if not old_form(old):
        raise Stop(f"{old} は古い形ではない（{MAP} と {RULES}/ が無い）")
    if os.path.lexists(hj):
        raise Stop(f"{hj} が既に在る（2 回目は撃たない／別の本陣が在る＝持ち主に聞く）")
    if is_repo(old):
        dirty = git(old, "status", "--porcelain", "--untracked-files=no").stdout.strip()
        if dirty:
            raise Stop(f"{old} に保存していない直しが在る:\n{dirty[:800]}\n先に保存してから（中身を見るのは持ち主）")
        if git(old, "remote", check=False).stdout.strip():
            git(old, "fetch", "-q", check=False)
            up = git(old, "rev-parse", "--abbrev-ref", "@{u}", check=False).stdout.strip()
            if up:
                behind = git(old, "rev-list", "--count", f"HEAD..{up}").stdout.strip()
                if behind != "0":
                    raise Stop(f"{old} が外の写し（{up}）より {behind} 遅れている。先に取り込んでから")
    b = busy_in(old)
    if b:
        raise Stop("その棚の下で起きている程が在る（会話・便）。閉じてから:\n  " + "\n  ".join(b[:10]))
    say(f"✅ check: 撃てる（{old} → {hj}/{os.path.basename(old)}）")


def nul(b):
    return [p for p in b.split("\0") if p]


def inner_hooks(old, new):
    """move の中で: 中の OS の core.hooksPath が**古い棚の中を指す絶対の道**なら、同じ所を指す相対の道に替える（箱 n=5346）。
    🩸 会員の実測 2026-11-21: 絶対の道で配線した棚は、mv の後は無い場所を指し、git は門を**黙って**飛ばす（move の保存も門なしで入る）。
    替えるのはこの 1 つだけ: 相対の道（mv で一緒に動く）・未設定は触らない。古い棚の外を指す絶対の道（共有の門など）は
    mv の後も在るので替えず、1 行で知らせる。返り: (前の値, 後の値)。替えなかったら (前の値, 前の値)＝rollback は前の値へ戻す"""
    hp = git(new, "config", "--local", "--get", "core.hooksPath", check=False).stdout.strip()
    if not hp or not os.path.isabs(hp):
        return hp, hp
    rp = os.path.realpath(hp)       # 古い棚はもう無いが親は在る＝/var→/private/var などの別名は解ける（old も realpath）
    if rp == old or rp.startswith(old + os.sep):
        rel = os.path.relpath(rp, old)
        git(new, "config", "--local", "core.hooksPath", rel)
        say(f"✅ 中の OS の門の配線: 絶対の道 {hp} → 相対の道 {rel}（移した後も保存の前の門が動く）")
        return hp, rel
    say(f"⚠️ 中の OS の門の配線は棚の外の絶対の道 {hp}（移しても在る＝替えない）")
    return hp, hp


def move(old, hj):
    old = os.path.realpath(old)
    hj = os.path.abspath(hj)
    check(old, hj)
    name = os.path.basename(old)
    repo = is_repo(old)
    pre = git(old, "rev-parse", "HEAD").stdout.strip() if repo else ""
    tracked = nul(git(old, "ls-files", "-z").stdout) if repo else []
    os.mkdir(hj)
    new = os.path.join(hj, name)
    os.rename(old, new)
    state = os.path.join(new, STATE_DIR, f"本陣への移し替え-{NOW}")
    os.makedirs(state, exist_ok=True)
    try:
        moved = lift(new, quiet=True)
    except Exception:
        os.rename(new, old); os.rmdir(hj)
        raise
    hooks = inner_hooks(old, new) if repo else ("", "")
    tools, kept = put_tools(new, state)
    json.dump({"old": old, "honjin": hj, "name": name, "pre": pre, "moved": moved, "tools": tools, "kept": kept,
               "hooks": list(hooks), "at": NOW},
              open(os.path.join(state, "控え.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    say(f"✅ 棚を本陣の中へ: {old} → {new}・上げた物 {len(moved)}・門と道具を新しい器の物に {len(tools)} 本（控え {os.path.relpath(state, hj)}/控え.json）")
    if kept:
        say(f"ℹ️ 会員が直した道具 {len(kept)} 本は替えなかった（器の新しい版との差分: {os.path.relpath(state, hj)}/器と違う道具/）:\n  " + "\n  ".join(kept))
    if not repo:
        say("ℹ️ 古い棚は git の保管場所ではなかった＝保存はセカンドブレイン設置の「終わったら」の節と同じ形で建てる側が撃つ")
        return 0
    # 保存（中の OS）: 上げた物の削除と地図の書き直し。道を全部ファイルで渡す（X-1'）
    srcs = {a for a, _ in moved}
    lo = sorted({p for p in tracked if p == MAP or any(p == a or p.startswith(a + "/") for a in srcs)} | {MAP} | set(tools))
    # 保存（本陣）: 前の HEAD で git に載っていた上げた物（受付は名前を読み替え）＋ .gitignore・scripts の別名
    def mp(p):
        for a, b in moved:
            if p == a or p.startswith(a + "/"):
                return b + p[len(a):]
        return None
    hs = sorted({q for q in (mp(p) for p in tracked) if q} | {".gitignore", "scripts"}
                | ({f"{DESK_NEW}/.gitkeep"} if not any(b == DESK_NEW for _, b in moved) else set()))
    for d, paths, msg in ((new, lo, f"本陣へ移した: 受付・箱・墓標・一覧・規則・地図を親の本陣へ上げ、門と道具を新しい器の物にした（{name} は中の OS になった）"),
                          (hj, hs, f"本陣を建てた: {name} {pre[:12]} から受付・箱・墓標・一覧・規則・地図を上げた")):
        f = os.path.join(state, f"保存する道-{'本陣' if d == hj else '中のOS'}.txt")
        open(f, "wb").write("".join(p + "\0" for p in paths).encode())
        git(d, "add", "--pathspec-from-file=" + f, "--pathspec-file-nul")
        p = git(d, "commit", "-q", "-m", msg, "--pathspec-from-file=" + f, "--pathspec-file-nul", check=False)
        if p.returncode != 0:
            say((p.stdout or "") + (p.stderr or ""))
            raise Stop(f"{'本陣' if d == hj else '中の OS'} の保存が門で止まった（⛔ --no-verify しない）。上の門の出力を直すか、"
                       f"`python3 scripts/honjin.py rollback {hj} {name}` で戻す")
    left = git(hj, "ls-files", "--others", "--exclude-standard").stdout.strip()
    say(f"✅ move: 中の OS {git(new, 'rev-parse', 'HEAD').stdout.strip()} ／ 本陣 {git(hj, 'rev-parse', 'HEAD').stdout.strip()}"
        f"（本陣に未追跡のまま置いた物: {len(left.splitlines()) if left else 0} 本＝前から保存していなかった物。消さない）")
    return 0


def rollback(hj, name):
    hj = os.path.abspath(hj)
    new = os.path.join(hj, name)
    st = sorted(d for d in os.listdir(os.path.join(new, STATE_DIR)) if d.startswith("本陣への移し替え-")) \
        if os.path.isdir(os.path.join(new, STATE_DIR)) else []
    if not st:
        raise Stop(f"控え（{name}/{STATE_DIR}/本陣への移し替え-*/控え.json）が無い＝move で移した棚ではない")
    c = json.load(open(os.path.join(new, STATE_DIR, st[-1], "控え.json"), encoding="utf-8"))
    old = c["old"]
    if os.path.lexists(old):
        raise Stop(f"{old} が既に在る（上書きしない）")
    b = busy_in(hj)
    if b:
        raise Stop("本陣の下で起きている程が在る。閉じてから:\n  " + "\n  ".join(b[:10]))
    os.replace(os.path.join(new, MAP), os.path.join(new, STATE_DIR, st[-1], "中のOSの地図.md"))   # 中の OS の 3 行の地図は控えへ
    for a, b2 in c["moved"]:
        src, dst = os.path.join(hj, b2), os.path.join(new, a)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.rename(src, dst)
    if c["pre"] and is_repo(new) and c.get("tools"):
        # 替えた門と道具を前の HEAD の物に戻す（前に無かった道具は控えの置き場へ退ける＝消さない）
        keep_t = os.path.join(new, STATE_DIR, st[-1], "替えた道具の後")
        for r in c["tools"]:
            if git(new, "cat-file", "-e", f"{c['pre']}:{r}", check=False).returncode == 0:
                git(new, "checkout", c["pre"], "--", r)
            elif os.path.exists(os.path.join(new, r)):
                os.makedirs(os.path.dirname(os.path.join(keep_t, r)), exist_ok=True)
                os.rename(os.path.join(new, r), os.path.join(keep_t, r))
    if c["pre"] and is_repo(new):
        # 移した保存の後の直しは履歴に残す（reset しない）。上げた物の道を全部書いて「戻した」を 1 つ保存
        f = os.path.join(new, STATE_DIR, st[-1], "保存する道-中のOS.txt")
        if os.path.exists(f):
            git(new, "add", "--pathspec-from-file=" + f, "--pathspec-file-nul")
            p = git(new, "commit", "-q", "-m", "本陣への移し替えを戻した", "--pathspec-from-file=" + f, "--pathspec-file-nul", check=False)
            if p.returncode not in (0, 1):
                raise Stop("戻しの保存が門で止まった: " + (p.stderr or p.stdout)[:400])
    hk = c.get("hooks") or []
    if len(hk) == 2 and hk[0] != hk[1] and is_repo(new):
        git(new, "config", "--local", "core.hooksPath", hk[0])      # 移す前の値に戻す（古い場所へ戻すので前の絶対の道がまた効く）
    os.rename(new, old)
    keep = f"{hj}-戻した-{NOW}"
    os.rename(hj, keep)
    same = ""
    if c["pre"] and is_repo(old):
        same = "（前の HEAD と同じ木: " + ("はい" if git(old, "diff", "--quiet", c["pre"], "HEAD", check=False).returncode == 0 else "いいえ") + "）"
    say(f"✅ rollback: {old} に戻した{same}。本陣は {keep} に残した（消していない）")
    return 0


# ---------------------------------------------------------------- ledger（BlueLamp のプロジェクト欄）
def ledger(hj, old=None):
    """拡張の読み方: 形は {"projects":[{id,name,description,createdAt,updatedAt,path,status,metadata}]}。
    起きたときに 1 回だけ読み、updatedAt が一番新しい行を今のプロジェクトにする。
    ⛔ 開いている古い窓は覚えた中身で帳面を書き戻す＝書いたらすぐ新しい窓を開き、古い窓では選ばない"""
    pj = os.environ.get("HONJIN_PROJECTS_JSON") or os.path.expanduser("~/.appgenius-ai/projects/projects.json")
    hj = os.path.abspath(hj)
    old = os.path.abspath(old) if old else None
    now = int(time.time() * 1000)
    data = {"projects": []}
    if os.path.exists(pj):
        data = json.load(open(pj, encoding="utf-8"))
        bak = pj + f".前-{NOW}"
        shutil.copy2(pj, bak)
    if not isinstance(data, dict) or not isinstance(data.get("projects"), list):
        raise Stop('帳面の形が {"projects": [...]} でない（拡張は 0 件と読む）。触らずに止まる')
    P = data["projects"]
    ab = lambda p: os.path.abspath(p.get("path", "") or "/")
    hit_new = [p for p in P if ab(p) == hj]
    hit_old = [p for p in P if old and ab(p) == old]
    if hit_new:
        hit_new[0]["updatedAt"] = now; what = "本陣の行が在った→updatedAt を今に"
    elif hit_old:
        hit_old[0].update(path=hj, name=os.path.basename(hj), updatedAt=now); what = f"古い道の行（id {hit_old[0].get('id')}）を本陣に置き換えた"
    else:
        P.append({"id": str(uuid.uuid4()), "name": os.path.basename(hj), "description": "", "createdAt": now,
                  "updatedAt": now, "path": hj, "status": "active", "metadata": {}}); what = "本陣の行を足した"
    os.makedirs(os.path.dirname(pj), exist_ok=True)
    tmp = pj + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, pj)
    cur = max(P, key=lambda p: p.get("updatedAt") or 0)
    ok = ab(cur) == hj
    say(f"{'✅' if ok else '❌'} ledger: {what}。今のプロジェクト（updatedAt 最大）= {cur.get('name')}（行 {len(P)}）")
    return 0 if ok else 1


# ---------------------------------------------------------------- clocks
def clocks(path):
    path = os.path.abspath(path)
    hits = 0
    for f, key in ((os.path.expanduser(os.environ.get("ROUTINE_DIR") or "~/.claude/routine") + "/routines.json", "routines"),
                   (os.path.expanduser(os.environ.get("SCHEDULER_DIR") or "~/.claude/scheduler") + "/schedules.json", "schedules")):
        if not os.path.exists(f):
            say(f"— {os.path.basename(os.path.dirname(f))}: 控えが無い（この機体に無い時計）")
            continue
        try:
            rows = json.load(open(f, encoding="utf-8")).get(key, [])
        except Exception as e:
            say(f"⚠️ {f} を読めない: {e}（測れない）"); continue
        for r in rows:
            s = json.dumps(r, ensure_ascii=False)
            if path in s:
                hits += 1
                say(f"  {os.path.basename(os.path.dirname(f))} {r.get('id')} {r.get('label') or r.get('name') or ''}: この道を読む")
    say(f"== clocks: {path} を読む時計 {hits} 本（直すのは時計の口で 1 本ずつ・中身は変えない）")
    return 0


# ---------------------------------------------------------------- version / update
def version_of(d):
    for f in ("規矩.md", "メモリシステム.md"):
        p = os.path.join(d, RULES, f)
        if os.path.exists(p):
            for l in open(p, encoding="utf-8").read().splitlines()[:12]:
                m = VERSION_RE.search(l)
                if m:
                    return m.group(1)
    return None


def inner_of(hj):
    sc = os.path.join(hj, "scripts")
    if os.path.islink(sc):
        return os.path.dirname(os.path.realpath(sc))
    raise Stop(f"{hj} に scripts の別名が無い＝本陣の形ではない（古い形なら先に move）")


def fill_values(hj, osdir):
    s = open(os.path.join(hj, RULES, "主君.md"), encoding="utf-8").read()
    v = {"棚の名前": os.path.basename(osdir), "棚の置き場": osdir}
    m = re.search(r"^# 主君 — (.+)$", s, re.M); v["名前"] = m.group(1).strip() if m else None
    m = re.search(r"呼ばれ方[:：]\s*([^（(\n]+)", s); v["呼ばれ方"] = m.group(1).strip() if m else None
    m = re.search(r"職業／事業[:：]\s*(.+)$", s, re.M); v["事業名"] = m.group(1).strip() if m else None
    r = git(osdir, "remote", "get-url", "origin", check=False).stdout.strip() if is_repo(osdir) else ""
    v["git remote"] = r or "なし（ローカルだけ）"
    return {k: x for k, x in v.items() if x}


def filled(text, v):
    for k, x in v.items():
        text = text.replace("{" + k + "}", x)
    return text


def merge_set(kit):
    """器の中で、持ち主の棚に混ぜて当てる紙（提供元が書く所を持つ紙）と、その置き場（本陣か中の OS か）"""
    out = []
    for d, ds, fs in os.walk(kit):
        rel = os.path.relpath(d, kit)
        if rel.split(os.sep)[0] in ("scripts", ".git"):
            ds[:] = []; continue
        for f in fs:
            r = os.path.normpath(os.path.join(rel, f))
            if not f.endswith(".md") or r in (os.path.join(RULES, "主君.md"), os.path.join("docs", "SCOPE_PROGRESS.md")):
                continue                                  # 主君.md は全部が会員の物・全体像は生成物
            side = "本陣" if r == MAP or r.startswith(RULES + os.sep) else "中の OS"
            out.append((r, side))
    return sorted(out)


def tool_set(kit):
    """器の道具（scripts/ の下）。scripts/皆伝/ は皆伝の機体にだけ置く物＝器の写し（scripts/kit/ の下）にだけ在ればよい"""
    out = []
    for d, _, fs in os.walk(os.path.join(kit, "scripts")):
        for f in fs:
            if f == ".DS_Store" or "__pycache__" in d:
                continue
            r = os.path.relpath(os.path.join(d, f), kit)
            if r.startswith(os.path.join("scripts", "皆伝") + os.sep):
                continue
            out.append(r)
    return sorted(out)


def kit_dir():
    """器の置き場。棚の scripts/ から撃てば隣の kit/、器の写しの scripts/（scripts/kit/scripts/）から撃てば器そのもの（1 つ上）。
    make-kit の selftest は器の写しの honjin.py を撃つ＝棚の scripts/ に同じ道具を 2 本置かない（芯 2）"""
    k = os.path.join(HERE, "kit")
    if os.path.isdir(os.path.join(k, "scripts")):
        return k
    up = os.path.dirname(HERE)
    if os.path.basename(up) == "kit" and os.path.isdir(os.path.join(up, "scripts")):
        return up
    return k


def kit_versions(osdir, r):
    """道具 r が**器から来たときの中身**の集合（3 方向の元・箱 n=5346）＝中の OS の器の写し `scripts/kit/<r>` の今と、
    その保管場所の履歴に在った全部の版。会員の道具がこのどれかと同じなら、会員は直していない（器の古い版のまま）。"""
    base = os.path.join("scripts", "kit", r)
    out = set()
    if os.path.exists(os.path.join(osdir, base)):
        out.add(open(os.path.join(osdir, base), "rb").read())
    if is_repo(osdir):
        for c in git(osdir, "log", "--all", "--format=%H", "--", base, check=False).stdout.split():
            p = subprocess.run(["git", "-C", osdir, "show", f"{c}:{base}"], capture_output=True)
            if p.returncode == 0:
                out.add(p.stdout)
    return out


TOOL_SAME, TOOL_ADD, TOOL_REPLACE, TOOL_MINE, TOOL_NOBASE, TOOL_COPY = "同じ", "足す", "替える", "直した", "元なし", "器の写し"


def tool_verdicts(osdir, kit):
    """器の道具 1 本ずつを、会員の棚に当てる前に見分ける（3 方向・箱 n=5346／n=5351）。**move・update・--apply-tools の判定はこの 1 つだけ**（決まり「同じ事実を 2 か所に持たせない」）。
    元＝器から来たときの中身（{@link kit_versions}）／会員の今／新しい器。返り: [(道, 判定, 会員の今の中身 or None, 新しい器の中身)]
      同じ   会員の今が新しい器と同じ＝何もしない
      足す   会員の棚に無い＝置く
      替える 会員の今が元のどれかと同じ（器から来たまま）＝新しい器に替える
      直した 会員の今が元のどれとも違う＝**替えない**。新しい器との差分だけ控える
      元なし 元が 1 つも無い（器の写しを持たない棚）＝直したか測れない＝**替えない**。差分だけ控える（日直参謀の受領 2026-11-21）
      器の写し scripts/kit/ の下＝次の更新の元。会員の道具ではない（move は替えない・--apply-tools は替える）
    ⚠️ 全部を見分けてから書く: --apply-tools は器の写し（元）も替えるので、書きながら見分けると元が先に新しい版になる"""
    out = []
    for r in tool_set(kit):
        new_b = open(os.path.join(kit, r), "rb").read()
        dst = os.path.join(osdir, r)
        mine = open(dst, "rb").read() if os.path.exists(dst) else None
        if r.startswith(os.path.join("scripts", "kit") + os.sep):
            v = TOOL_SAME if mine == new_b else TOOL_COPY
        elif mine is None:
            v = TOOL_ADD
        elif mine == new_b:
            v = TOOL_SAME
        else:
            base = kit_versions(osdir, r)
            v = TOOL_REPLACE if mine in base else (TOOL_MINE if base else TOOL_NOBASE)
        out.append((r, v, mine, new_b))
    return out


def tool_diff(state, r, mine, new_b):
    """替えなかった道具の、会員の今 → 新しい器 の差分を state/器と違う道具/<道>.diff に置く"""
    d = os.path.join(state, "器と違う道具", r + ".diff")
    os.makedirs(os.path.dirname(d), exist_ok=True)
    try:
        a, b = mine.decode("utf-8").splitlines(True), new_b.decode("utf-8").splitlines(True)
        txt = "".join(difflib.unified_diff(a, b, f"会員の今/{r}", f"新しい器/{r}"))
    except UnicodeDecodeError:
        txt = "（文字でない道具＝差分を出せない）\n"
    open(d, "w", encoding="utf-8").write(txt)
    return d


def place_tools(osdir, kit, state, with_copy):
    """{@link tool_verdicts} の判定どおりに道具を置く（move と --apply-tools の共通の口）。with_copy＝器の写し（scripts/kit/）も替えるか。
    返り: (替えた・足した道, 替えなかった会員の道（直した＋元なし）, 元なしの道)"""
    vs = tool_verdicts(osdir, kit)
    changed, kept, nobase = [], [], []
    for r, v, mine, new_b in vs:
        if v in (TOOL_MINE, TOOL_NOBASE):
            kept.append(r)
            if v == TOOL_NOBASE:
                nobase.append(r)
            if state:
                tool_diff(state, r, mine, new_b)
        elif v in (TOOL_ADD, TOOL_REPLACE) or (v == TOOL_COPY and with_copy):
            dst = os.path.join(osdir, r)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(kit, r), dst); changed.append(r)
    return changed, kept, nobase


def put_tools(osdir, state=None):
    """move の中で: 門と道具を、この honjin.py が入っている器の物に替える（古い門は本陣の形を知らず、保存で落ちる）。
    器の写し（scripts/kit/ の雛形）は替えない＝更新（update）の 3 方向の元として建てた日の物を残す。
    🩸 会員の実測 2026-11-21（箱 n=5346・n=5351）: 会員が直して使っている器の道具を中身が違うというだけで黙って上書きしていた。
       ⇒ 見分けは {@link tool_verdicts}（update・--apply-tools と同じ 1 つ）。会員が直した道具と、元が無い道具は替えず差分を控える。
    返り: (替えた道, 替えなかった会員の道)"""
    kit = kit_dir()
    if not os.path.isdir(os.path.join(kit, "scripts")):
        raise Stop(f"{kit} に器の道具が無い＝この honjin.py は手本（scripts/kit/ を持つ棚）から撃っていない")
    changed, kept, _ = place_tools(osdir, kit, state, with_copy=False)
    return changed, kept


def update(hj, kit):
    hj = os.path.realpath(hj); kit = os.path.realpath(kit)
    osdir = inner_of(hj)
    if not os.path.isfile(os.path.join(kit, "scripts", "make-kit.sh")):
        raise Stop(f"{kit} は器の切り出しではない（scripts/make-kit.sh が無い）")
    a, b = version_of(hj) or "（無い＝最初の器）", version_of(kit) or "（無い）"
    out = os.path.join(osdir, STATE_DIR, f"器の更新-{NOW}")
    os.makedirs(os.path.join(out, "混ぜた紙"), exist_ok=True)
    v = fill_values(hj, osdir)
    say(f"== update: 器の版 今 {a} → 新しい器 {b}（答え {len(v)} 個を主君.md と棚から読んだ: {', '.join(v)}）")
    rep = [f"# 器の更新の差分（{NOW}）", "", f"- 今の版: {a}", f"- 新しい器の版: {b}", f"- 本陣: {os.path.basename(hj)}・中の OS: {os.path.basename(osdir)}", ""]
    # 道具
    tl = tool_set(kit)
    vs = tool_verdicts(osdir, kit)                        # --apply-tools と同じ見分け（1 つだけ）
    by = lambda v: [r for r, x, _, _ in vs if x == v]
    chg, add, mine_k, nob = by(TOOL_REPLACE) + by(TOOL_COPY), by(TOOL_ADD), by(TOOL_MINE), by(TOOL_NOBASE)
    for r, x, m, n in vs:
        if x in (TOOL_MINE, TOOL_NOBASE):
            tool_diff(out, r, m, n)
    mine_only = sorted(set(tool_set(osdir)) - set(tl))
    rep += ["## 1. 道具（提供元が書く所＝入れ替える・--apply-tools）", "",
            f"- 変わる {len(chg)}・足す {len(add)}・替えない（会員が直した）{len(mine_k)}・替えない（器の写しが無く直したか測れない）{len(nob)}"
            f"・会員の道具（器に無い＝触らない）{len(mine_only)}", ""]
    rep += [f"  - ~ {r}" for r in chg] + [f"  - + {r}" for r in add]
    rep += [f"  - = {r}（替えない（会員が直した）・差分: 器と違う道具/{r}.diff）" for r in mine_k]
    rep += [f"  - = {r}（替えない（器の写しが無い）・差分: 器と違う道具/{r}.diff）" for r in nob] + [""]
    # 紙（3 方向で混ぜる: 元＝棚が建った時の器の写し（中の OS の scripts/kit/）／会員の今／新しい器。どれも答えで埋めてから）
    rep += ["## 2. 紙（提供元の所だけ入れ替え・会員が足した所は残す＝3 方向で混ぜた・--apply-rules は持ち主の OK の後）", ""]
    conflicts = 0
    papers = 0                                            # 中身が変わる紙の数（判定に使う）
    for r, side in merge_set(kit):
        mine = os.path.join(hj if side == "本陣" else osdir, r)
        base_p = os.path.join(osdir, "scripts", "kit", r)
        new_t = filled(open(os.path.join(kit, r), encoding="utf-8").read(), v)
        if not os.path.exists(mine):
            res, n, how = new_t, 0, "足す（会員の棚に無い）"
        else:
            mine_t = open(mine, encoding="utf-8").read()
            base_t = filled(open(base_p, encoding="utf-8").read(), v) if os.path.exists(base_p) else None
            if mine_t == new_t:
                continue
            if base_t is None:
                # 元が無い（器の写しを持たない棚）＝混ぜられない。新しい器の文に会員の文を印つきで並べ、持ち主と見る
                res = "<<<<<<< 会員の今\n" + mine_t + "=======\n" + new_t + ">>>>>>> 新しい器\n"; n = 1; how = "元が無い＝全文を並べた（衝突 1）"
            else:
                with tempfile.TemporaryDirectory() as t:
                    fm, fb, fn = (os.path.join(t, x) for x in ("m", "b", "n"))
                    open(fm, "w", encoding="utf-8").write(mine_t); open(fb, "w", encoding="utf-8").write(base_t); open(fn, "w", encoding="utf-8").write(new_t)
                    p = subprocess.run(["git", "merge-file", "-p", "-L", "会員の今", "-L", "棚が建った時の器", "-L", "新しい器", fm, fb, fn],
                                       capture_output=True, text=True)
                    res, n = p.stdout, max(p.returncode, 0)
                how = f"混ぜた（衝突 {n}）" if n else "混ぜた（衝突 0）"
            if res == mine_t:
                continue                                  # 器はこの紙の提供元の所を変えていない（会員の足した所だけが違う）
        conflicts += n; papers += 1
        dst = os.path.join(out, "混ぜた紙", side, r)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write(res)
        cur = open(mine, encoding="utf-8").read().splitlines(True) if os.path.exists(mine) else []
        d = "".join(difflib.unified_diff(cur, res.splitlines(True), f"今/{side}/{r}", f"後/{side}/{r}"))
        open(dst + ".diff", "w", encoding="utf-8").write(d)
        plus = sum(1 for l in d.splitlines() if l.startswith("+") and not l.startswith("+++"))
        minus = sum(1 for l in d.splitlines() if l.startswith("-") and not l.startswith("---"))
        rep.append(f"- {side}/{r}: {how}・足す {plus} 行・消す {minus} 行（混ぜた紙/{side}/{r}.diff）")
    rep += ["", f"衝突 {conflicts}（衝突の印 <<<<<<< ======= >>>>>>> が残る紙は --apply-rules が拒む＝持ち主と決めて直してから）", ""]
    # 判定（箱 n=5469）: 更新の有無は中身の違いだけで決める。器の版の名前は中身が直っても同じことがある（2026-11-21 に規則の紙が直ったのに
    #   版は本陣-1 のまま＝版で比べた席が『更新なし』で終えた）。⇒ 版は見出しの印にとどめ、判定に使わない（正本を中身 1 つに）
    has = bool(chg or add or papers)
    verdict = (f"== 判定: 更新あり（道具 変わる {len(chg)}・足す {len(add)}・紙 {papers}。器の版の名前は見ていない）" if has
               else "== 判定: 更新なし（道具も紙も中身の違い 0。器の版の名前は見ていない）")
    rep += [verdict]
    open(os.path.join(out, "差分.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
    json.dump({"kit": kit, "honjin": hj, "os": osdir, "tools_change": chg, "tools_add": add, "tools_kept": mine_k, "tools_kept_nobase": nob, "from": a, "to": b,
               "papers_changed": papers, "has_update": has},
              open(os.path.join(out, "控え.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    say("\n".join(rep))
    say(f"== 差分の置き場: {out}（何も変えていない）")
    return 0


def apply_tools(hj, kit):
    """道具を入れ替える。見分けは move と同じ {@link tool_verdicts}＝会員が直した道具と、器の写しが無い道具は替えず、
    新しい器との差分を 11一時ファイル/器の更新-<日時>/器と違う道具/ に置く（箱 n=5351）。器の写し（scripts/kit/）は替える＝次の更新の元"""
    hj = os.path.realpath(hj); kit = os.path.realpath(kit); osdir = inner_of(hj)
    out = os.path.join(osdir, STATE_DIR, f"器の更新-{NOW}")
    changed, kept, nobase = place_tools(osdir, kit, out, with_copy=True)
    for r in changed:
        say(f"  ~ {r}")
    for r in kept:
        say(f"  = {r}（替えない（{'器の写しが無い' if r in nobase else '会員が直した'}）・差分: {os.path.relpath(out, osdir)}/器と違う道具/{r}.diff）")
    if kept:
        os.makedirs(out, exist_ok=True)
        json.dump({"kit": kit, "changed": changed, "kept": kept, "kept_nobase": nobase, "at": NOW},
                  open(os.path.join(out, "入れ替えの控え.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    say(f"✅ apply-tools: {len(changed)} 本を入れ替えた・会員が直した道具 {len(kept) - len(nobase)} 本と器の写しが無い道具 {len(nobase)} 本は替えなかった"
        f"（会員の道具には触っていない）。保存は道を全部書いて中の OS へ")
    return 0


def apply_rules(hj, out):
    hj = os.path.realpath(hj); osdir = inner_of(hj)
    root = os.path.join(out, "混ぜた紙")
    if not os.path.isdir(root):
        raise Stop(f"{out} は update が作った差分の置き場ではない")
    files = []
    for side in ("本陣", "中の OS"):
        for d, _, fs in os.walk(os.path.join(root, side)):
            for f in fs:
                if f.endswith(".diff"):
                    continue
                p = os.path.join(d, f)
                t = open(p, encoding="utf-8").read()
                if re.search(r"^(<<<<<<<|=======|>>>>>>>)( |$)", t, re.M):
                    raise Stop(f"衝突の印が残る: {os.path.relpath(p, root)}（持ち主と決めて直してから撃ち直す。何も当てていない）")
                files.append((p, os.path.join(hj if side == "本陣" else osdir, os.path.relpath(p, os.path.join(root, side)))))
    for src, dst in files:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst); say(f"  ~ {dst}")
    say(f"✅ apply-rules: {len(files)} 枚を当てた。器の版: {version_of(hj) or '（無い）'}。保存は道を全部書いて本陣と中の OS へ")
    return 0


# ---------------------------------------------------------------- kaiden（席ごとの作業場所）
def kaiden(hj):
    hj = os.path.realpath(hj); osdir = inner_of(hj)
    src = os.path.join(osdir, "scripts", "kit", "scripts", "皆伝", "honjin_wt.py")
    dst = os.path.join(osdir, "scripts", "honjin_wt.py")
    if not os.path.exists(src):
        raise Stop(f"器の写しに {os.path.relpath(src, osdir)} が無い（器が古い＝先に update）")
    if os.path.exists(dst):
        say(f"— kaiden: {os.path.relpath(dst, hj)} は既に在る（上書きしない）"); return 0
    shutil.copy2(src, dst); os.chmod(dst, 0o755)
    say(f"✅ kaiden: 席ごとの作業場所の道具を置いた（{os.path.relpath(dst, osdir)}）。使えるのは外への写し（origin）を作った後")
    return 0


# ---------------------------------------------------------------- selftest
def selftest():
    global NOW                                            # 8 で器の更新の置き場の名前を分ける（同じ秒に 2 回撃つ）
    t = tempfile.mkdtemp(prefix="honjin-selftest-")
    env_pj = os.path.join(t, "projects.json")
    os.environ["HONJIN_PROJECTS_JSON"] = env_pj

    def shelf(d, desk=DESK_OLD):
        for x in (RULES, desk, "08プロジェクト/2000-01-01-検体", "09アーカイブ/案件", "docs", "01商品資産", "scripts/git-hooks", "11一時ファイル"):
            os.makedirs(os.path.join(d, x), exist_ok=True)
        for f, s in ((MAP, "# 検体の棚\n"), (f"{RULES}/規矩.md", "# 規矩\n"), (f"{RULES}/主君.md", "# 主君 — 検体\n- 呼ばれ方: 主君（）\n- 職業／事業: 検体商店\n"),
                     (f"{RULES}/メモリシステム.md", "# メモリ\n"), (f"{desk}/件.md", "件\n"),
                     ("docs/SCOPE_PROGRESS.md", "x\n"), ("01商品資産/a.md", "a\n"), ("scripts/git-hooks/pre-commit", "#!/bin/sh\nexit 0\n"),
                     (".gitignore", "11一時ファイル/\n")):
            open(os.path.join(d, f), "w", encoding="utf-8").write(s)
        os.chmod(os.path.join(d, "scripts/git-hooks/pre-commit"), 0o755)
        subprocess.run([sys.executable, os.path.join(HERE, "kiroku.py"), "box", "--root", os.path.join(d, "08プロジェクト"),
                        "--slug", "2000-01-01-検体", "--title", "検体", "--state", "起案", "--owner", "AOS設置", "--absorb", "なし"],
                       capture_output=True, check=True)

    try:
        # 1 lift（保存の無い新しい棚）
        hj = os.path.join(t, "a", HONJIN_NAME); s = os.path.join(hj, "検体OS"); shelf(s)
        lift(s)
        for x in (MAP, f"{RULES}/規矩.md", f"{DESK_NEW}/件.md", "08プロジェクト/2000-01-01-検体/status.md", "docs", ".gitignore"):
            assert os.path.exists(os.path.join(hj, x)), f"lift の後に本陣に {x} が無い"
        assert os.path.islink(os.path.join(hj, "scripts")) and os.path.isdir(os.path.join(hj, "scripts", "git-hooks")), "scripts の別名が解けない"
        assert not os.path.exists(os.path.join(s, RULES)) and os.path.exists(os.path.join(s, MAP)) and os.path.exists(os.path.join(s, "01商品資産/a.md"))
        say("🔬 1 lift: 本陣に 受付（00廷議→00朝廷）・箱・一覧・規則・地図・別名。中の OS に 01 と 3 行の地図 ✅")
        # 負制御 1: もう本陣の形の棚に lift を撃つと止まる
        try:
            lift(s); raise AssertionError("負制御: 本陣の形に lift が通った")
        except Stop:
            say("🔬 1' 負制御: 本陣の形の棚への lift は止まる ✅")
        # 2 move（git の保管場所の古い棚）
        old = os.path.join(t, "b", "検体OS"); shelf(old)
        git(old, "init", "-q"); git(old, "config", "user.email", "k@example.invalid"); git(old, "config", "user.name", "k")
        git(old, "config", "core.hooksPath", "scripts/git-hooks")
        tr = [p for p in subprocess.run(["find", ".", "-type", "f"], cwd=old, capture_output=True, text=True).stdout.split() if "/.git/" not in p]
        git(old, "add", "--", *tr); git(old, "commit", "-q", "-m", "検体")
        open(os.path.join(old, "01商品資産", "未保存.md"), "w").write("u\n")      # 前から保存していない物＝保存に混ぜない
        pre = git(old, "rev-parse", "HEAD").stdout.strip()
        # 負制御 2: 保存していない直しが在ると止まる
        open(os.path.join(old, "01商品資産/a.md"), "a").write("dirty\n")
        try:
            move(old, default_honjin(old)); raise AssertionError("負制御: 未保存の直しが在るのに move が通った")
        except Stop:
            say("🔬 2' 負制御: 保存していない直しが在ると move は止まる ✅")
        git(old, "checkout", "--", "01商品資産/a.md")
        hj2 = default_honjin(old)
        move(old, hj2)
        n2 = os.path.join(hj2, "検体OS")
        assert git(n2, "status", "--porcelain", "--untracked-files=no").stdout.strip() == "", "中の OS に保存漏れ"
        assert git(hj2, "status", "--porcelain", "--untracked-files=no").stdout.strip() == "", "本陣に保存漏れ"
        assert "00朝廷/件.md" in git(hj2, "ls-files").stdout and "検体OS" not in git(hj2, "ls-files").stdout, "本陣の保存の中身が違う"
        assert "01商品資産/未保存.md" not in git(n2, "ls-files").stdout, "前から保存していない物を保存した"
        say("🔬 2 move: 2 か所に保存・中の OS を本陣の保存に入れない・前の未保存は未保存のまま ✅")
        # 3 ledger
        json.dump({"projects": [{"id": "x", "name": "検体OS", "path": old, "updatedAt": 1}, {"id": "y", "name": "別", "path": "/elsewhere", "updatedAt": 2}]},
                  open(env_pj, "w"))
        assert ledger(hj2, old) == 0
        d = json.load(open(env_pj))["projects"]
        assert len(d) == 2 and d[0]["path"] == os.path.abspath(hj2) and d[0]["id"] == "x" and d[1]["path"] == "/elsewhere", "帳面の置き換えが違う"
        open(env_pj, "w").write("[]")
        try:
            ledger(hj2); raise AssertionError("負制御: 配列だけの帳面を書き換えた")
        except Stop:
            say("🔬 3 ledger: 古い行を本陣に置き換え（id は残す・他の行は触らない）・負制御（形の違う帳面は触らない）✅")
        # 4 rollback
        rollback(hj2, "検体OS")
        assert os.path.exists(os.path.join(old, f"{DESK_OLD}/件.md")) and os.path.exists(os.path.join(old, MAP)) and not os.path.exists(hj2)
        assert git(old, "diff", "--quiet", pre, "HEAD", check=False).returncode == 0, "rollback の後の木が前と違う"
        say("🔬 4 rollback: 前の場所・前の木に戻った（履歴は消さない・本陣は名前を変えて残した）✅")
        # 5 中の OS の門の配線が古い棚の中の絶対の道（会員の実測 2026-11-21・箱 n=5346）
        def repo_shelf(d, files=()):
            shelf(d)
            for f, txt in files:
                os.makedirs(os.path.dirname(os.path.join(d, f)), exist_ok=True)
                open(os.path.join(d, f), "w", encoding="utf-8").write(txt)
            git(d, "init", "-q"); git(d, "config", "user.email", "k@example.invalid"); git(d, "config", "user.name", "k")
            fs = [p for p in subprocess.run(["find", ".", "-type", "f"], cwd=d, capture_output=True, text=True).stdout.split() if "/.git/" not in p]
            git(d, "add", "--", *fs); git(d, "commit", "-q", "-m", "検体")
        old3 = os.path.join(t, "c", "検体OS"); repo_shelf(old3)
        abs_hp = os.path.join(os.path.realpath(old3), "scripts", "git-hooks")
        git(old3, "config", "core.hooksPath", abs_hp)
        hj3 = default_honjin(old3); move(old3, hj3); n3 = os.path.join(hj3, "検体OS")
        hp3 = git(n3, "config", "--get", "core.hooksPath").stdout.strip()
        assert hp3 == "scripts/git-hooks", f"移した後の中の OS の門の配線が相対でない: {hp3}"
        gate = os.path.join(n3, "scripts", "git-hooks", "pre-commit"); keep_gate = open(gate, "rb").read()
        open(gate, "w").write("#!/bin/sh\nexit 1\n"); os.chmod(gate, 0o755)          # 必ず落ちる門＝門が効いているかの物差し
        assert git(n3, "commit", "-q", "--allow-empty", "-m", "x", check=False).returncode != 0, "移した後に中の OS の門が効いていない"
        # 負制御: 同じ物差しで、古い絶対の道（もう無い場所）だと門は黙って飛ばされる＝直す前の形
        git(n3, "config", "core.hooksPath", abs_hp)
        assert git(n3, "commit", "-q", "--allow-empty", "-m", "x", check=False).returncode == 0, "負制御: 無い道の門で落ちた（物差しが壊れている）"
        git(n3, "reset", "-q", "--soft", "HEAD~1"); git(n3, "config", "core.hooksPath", "scripts/git-hooks")
        open(gate, "wb").write(keep_gate)
        say("🔬 5 move: 中の OS の門の配線が古い棚の中の絶対の道 → 相対の scripts/git-hooks に替わり、落ちる直しの保存は落ちる（負制御: 古い絶対の道のままだと黙って通る）✅")
        rollback(hj3, "検体OS")
        assert git(old3, "config", "--get", "core.hooksPath").stdout.strip() == abs_hp, "rollback で門の配線が前の値に戻っていない"
        say("🔬 5' rollback: 門の配線も前の値に戻る ✅")
        # 5'' 古い棚の外の絶対の道（共有の門）は替えない
        shared = os.path.join(t, "共有の門"); os.makedirs(shared)
        old5 = os.path.join(t, "e", "検体OS"); repo_shelf(old5); git(old5, "config", "core.hooksPath", shared)
        hj5 = default_honjin(old5); move(old5, hj5)
        assert git(os.path.join(hj5, "検体OS"), "config", "--get", "core.hooksPath").stdout.strip() == shared, "棚の外の門の配線を書き替えた"
        say("🔬 5'' 負制御: 古い棚の外を指す絶対の道は替えない ✅")
        # 6 会員が直した器の道具は替えない（update と同じ 3 方向: 元＝器から来たときの中身の全版）
        K = lambda r: os.path.join("scripts", "kit", r)
        old6 = os.path.join(t, "f", "検体OS")
        repo_shelf(old6, ((K("scripts/build_agent_aliases.py"), "# 器 v1\n"), ("scripts/build_agent_aliases.py", "# 器 v1\n# 会員が足した 1 行\n"),
                          (K("scripts/check-distributable.sh"), "# 器 v1\n"), ("scripts/check-distributable.sh", "# 器 v1\n"),
                          (K("scripts/mcplib.py"), "# 器 v0\n"), ("scripts/mcplib.py", "# 器 v0\n"),
                          ("scripts/sms/read_code.sh", "# 会員が Android に足した読み方（器の写しが無い）\n")))
        open(os.path.join(old6, K("scripts/mcplib.py")), "w").write("# 器 v1\n")        # 器の写しを v1 へ（会員の道具は v0 のまま＝直していない）
        git(old6, "commit", "-q", "-m", "器の写しを v1 へ", "--", K("scripts/mcplib.py"))
        hj6 = default_honjin(old6); move(old6, hj6); n6 = os.path.join(hj6, "検体OS")
        kit_b = lambda r: open(os.path.join(kit_dir(), r), "rb").read()
        assert open(os.path.join(n6, "scripts/build_agent_aliases.py")).read() == "# 器 v1\n# 会員が足した 1 行\n", "会員が直した道具を上書きした"
        st6 = sorted(d for d in os.listdir(os.path.join(n6, STATE_DIR)) if d.startswith("本陣への移し替え-"))[-1]
        c6 = json.load(open(os.path.join(n6, STATE_DIR, st6, "控え.json"), encoding="utf-8"))
        assert c6["kept"] == ["scripts/build_agent_aliases.py", "scripts/sms/read_code.sh"], f"替えなかった道具の控えが違う: {c6['kept']}"
        for r in c6["kept"]:
            assert os.path.getsize(os.path.join(n6, STATE_DIR, st6, "器と違う道具", r + ".diff")) > 0, f"差分が無い: {r}"
        assert open(os.path.join(n6, "scripts/sms/read_code.sh")).read().startswith("# 会員が Android"), "器の写しが無い道具を move が替えた"
        # 負制御: 器から来たまま（今の写しと同じ／履歴の古い版と同じ）の道具は今までどおり新しい器の物に替わる
        assert open(os.path.join(n6, "scripts/check-distributable.sh"), "rb").read() == kit_b("scripts/check-distributable.sh"), "器のままの道具が替わっていない"
        assert open(os.path.join(n6, "scripts/mcplib.py"), "rb").read() == kit_b("scripts/mcplib.py"), "器の古い版のままの道具が替わっていない"
        say("🔬 6 move: 会員が直した道具と器の写しが無い道具は替えずに差分を控えへ・器のまま（今の写し／履歴の古い版）の道具は替わる（負制御 2）✅")
        # 7 器の更新（update の差分.md と --apply-tools）も move と同じ見分け（箱 n=5351）
        T = lambda x: os.path.join("scripts", f"t7_{x}.py")
        for f, txt in ((K(T("a")), "# 器 v1\n"), (T("a"), "# 器 v1\n# 会員が直した 1 行\n"),
                       (K(T("b")), "# 器 v1\n"), (T("b"), "# 器 v1\n"),
                       (T("c"), "# 会員の道具（器の写しが無い）\n"),
                       (K(T("d")), "# 器 v0\n"), (T("d"), "# 器 v0\n")):
            open(os.path.join(n6, f), "w", encoding="utf-8").write(txt)
        git(n6, "add", "--", K(T("a")), T("a"), K(T("b")), T("b"), T("c"), K(T("d")), T("d"))
        git(n6, "commit", "-q", "-m", "検体 7", "--", K(T("a")), T("a"), K(T("b")), T("b"), T("c"), K(T("d")), T("d"))
        open(os.path.join(n6, K(T("d"))), "w").write("# 器 v1\n")       # 写しだけ v1 へ（会員の d は履歴の古い版 v0 のまま）
        git(n6, "commit", "-q", "-m", "検体 7 写し", "--", K(T("d")))
        nk7 = os.path.join(t, "新しい器7")
        for f, txt in [(T(x), "# 器 v2\n") for x in "abcd"] + [(K(T(x)), "# 器 v2\n") for x in "abcd"] + [(T("e"), "# 器 v2 新\n"), ("scripts/make-kit.sh", "#\n")]:
            os.makedirs(os.path.dirname(os.path.join(nk7, f)), exist_ok=True)
            open(os.path.join(nk7, f), "w", encoding="utf-8").write(txt)
        assert update(hj6, nk7) == 0
        u7 = sorted(d for d in os.listdir(os.path.join(n6, STATE_DIR)) if d.startswith("器の更新-"))[-1]; u7 = os.path.join(n6, STATE_DIR, u7)
        rp7 = open(os.path.join(u7, "差分.md"), encoding="utf-8").read()
        assert f"= {T('a')}（替えない（会員が直した）" in rp7 and f"= {T('c')}（替えない（器の写しが無い）" in rp7, "差分.md が会員の道具を見分けていない"
        assert f"~ {T('b')}" in rp7 and f"~ {T('d')}" in rp7 and f"+ {T('e')}" in rp7, "差分.md が器のままの道具を『変わる』に並べていない"
        assert apply_tools(hj6, nk7) == 0
        rd = lambda f: open(os.path.join(n6, f), encoding="utf-8").read()
        assert rd(T("a")) == "# 器 v1\n# 会員が直した 1 行\n", "--apply-tools が会員の直した道具を上書きした"
        assert rd(T("c")) == "# 会員の道具（器の写しが無い）\n", "--apply-tools が器の写しが無い道具を上書きした"
        for x in "ac":
            assert os.path.getsize(os.path.join(u7, "器と違う道具", T(x) + ".diff")) > 0, f"差分が無い: {T(x)}"
        # 負制御: 器から来たまま（今の写し／履歴の古い版）の道具・新しい道具・器の写しは新しい器に揃う＝見分けが「全部残す」になっていない
        assert rd(T("b")) == rd(T("d")) == "# 器 v2\n" and rd(T("e")) == "# 器 v2 新\n", "器のままの道具が替わっていない"
        assert all(rd(K(T(x))) == "# 器 v2\n" for x in "abcd"), "器の写し（次の更新の元）が新しい器に揃っていない"
        say("🔬 7 update・--apply-tools: 会員が直した道具と器の写しが無い道具は替えず差分を控え・差分.md に『替えない』と並べる・器のままの道具と写しは替わる（負制御）✅")
        # 8 更新の有無は中身で決める（箱 n=5469）: 器の版の名前が同じでも、規則の紙が 1 行直れば『更新あり』・何も直していなければ『更新なし』
        mem = os.path.join(RULES, "メモリシステム.md")
        cur = open(os.path.join(hj6, mem), encoding="utf-8").read()
        def kit8(name, paper):
            d = os.path.join(t, name); shutil.copytree(nk7, d)
            os.makedirs(os.path.join(d, RULES), exist_ok=True)
            open(os.path.join(d, mem), "w", encoding="utf-8").write(paper); return d
        def last(d):
            u = sorted(x for x in os.listdir(os.path.join(n6, STATE_DIR)) if x.startswith("器の更新-"))[-1]
            return json.load(open(os.path.join(n6, STATE_DIR, u, "控え.json"), encoding="utf-8")), open(os.path.join(n6, STATE_DIR, u, "差分.md"), encoding="utf-8").read()
        NOW = NOW + "-8a"; assert update(hj6, kit8("新しい器8a", cur)) == 0
        c8a, r8a = last(n6)
        assert c8a["has_update"] is False and "== 判定: 更新なし" in r8a, f"何も直していない器で『更新あり』: {c8a}"
        NOW = NOW + "b"; assert update(hj6, kit8("新しい器8b", cur + "- 提供元が足した 1 行\n")) == 0
        c8b, r8b = last(n6)
        assert c8b["has_update"] is True and c8b["papers_changed"] == 1 and "== 判定: 更新あり" in r8b, f"紙が 1 行直ったのに『更新なし』: {c8b}"
        assert c8b["from"] == c8a["from"], "検体の器の版の名前が動いた（版を同じにしたまま試す）"
        say("🔬 8 update の判定: 器の版の名前が同じでも、紙が 1 行直れば『更新あり』・直していなければ『更新なし』（負制御）✅")
        say("✅ selftest: lift・move・ledger・rollback・門の配線・会員の道具（move と器の更新）・更新の有無の判定と負制御 8 つが通った")
        return 0
    except (AssertionError, Stop) as e:
        say(f"🚨 selftest: {e}"); return 1
    finally:
        say(f"（検体の置き場 {t}＝OS の一時領域。消すのは OS に任せる）")


def main(a):
    try:
        if a[:1] == ["lift"] and len(a) == 2:
            lift(a[1]); return 0
        if a[:1] in (["move"], ["check"]) and len(a) in (2, 3):
            hj = os.path.abspath(a[2]) if len(a) == 3 else default_honjin(a[1])
            return move(a[1], hj) if a[0] == "move" else (check(a[1], hj) or 0)
        if a[:1] == ["rollback"] and len(a) == 3:
            return rollback(a[1], a[2])
        if a[:1] == ["ledger"] and len(a) in (2, 4):
            return ledger(a[1], a[3] if len(a) == 4 and a[2] == "--old" else None)
        if a[:1] == ["clocks"] and len(a) == 2:
            return clocks(a[1])
        if a[:1] == ["version"] and len(a) == 2:
            say(version_of(a[1]) or "（無い＝最初の器）"); return 0
        if a[:1] == ["update"] and len(a) in (3, 4):
            if len(a) == 4 and a[3] == "--apply-tools":
                return apply_tools(a[1], a[2])
            if len(a) == 4 and a[3] == "--apply-rules":
                return apply_rules(a[1], a[2])
            if len(a) == 3:
                return update(a[1], a[2])
        if a[:1] == ["kaiden"] and len(a) == 2:
            return kaiden(a[1])
        if a == ["selftest"]:
            return selftest()
        print(__doc__.split("\n\n")[2], file=sys.stderr); return 2
    except Stop as e:
        print(f"⛔ {e}", file=sys.stderr); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
