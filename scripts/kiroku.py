#!/usr/bin/env python3
"""kiroku.py — 07プロジェクト の箱（status.md）の frontmatter を、同じ語彙表から吐き・検める道具（主君裁定 2026-09-18・帳簿 id=440）。

語彙表はこのファイルの先頭 1 か所だけ。生成器（build_scope_progress.py）もここを import して読む。
土台は CTO リポ `scripts/kiroku.py`（origin/main）。STATES は CTO 版と同じ語彙表に揃える（`--vocab-diff` が門）。
BOX_KEYS はこの棚の箱の鍵（主君裁定の表）で、CTO の箱の鍵（n・scope・constraints・escalate）とは意図して違う。

使い方（棚のルートで）:
  box       frontmatter を吐く（既存は frontmatter だけ置換・本文不変。省いた鍵は既存の値を引き継ぐ）
            python3 scripts/kiroku.py box --slug <日付-slug> --title … --state <語彙> --owner … --absorb … \
                [--ask …] [--lever …] [--until …] [--resume …] [--next …] [--due YYYY-MM-DD] [--tmp_ttl 30d]
            updated は道具が今日の日付を入れる（人は書かない）
  --check   紙が語彙表に合うか（exit 0/1・理由）。パスが箱の親フォルダなら、配下の全箱を検め、status.md の無い箱も exit 1
            python3 scripts/kiroku.py --check 07プロジェクト
            python3 scripts/kiroku.py --check 07プロジェクト/*/status.md
  --vocab-diff <CTO の kiroku.py>   2 つの語彙表（STATES）を比べ、食い違えば exit 1（門）
            python3 scripts/kiroku.py --vocab-diff <CTO リポ>/scripts/kiroku.py
            BOX_KEYS は設計上別（dev は n・scope・constraints・escalate／この棚は due・tmp_ttl）なので情報表示だけ（孔明裁定 2026-09-18・帳簿 id=450）
"""
import argparse, ast, datetime as dt, os, re, sys

# ============================== 語彙表（ここ 1 か所） ==============================
# 箱の state（8 語）。CTO リポ scripts/kiroku.py の STATES と同じ語彙表にする（門: --vocab-diff）
#   起案     箱を作った・誰も動いていない
#   裁定待ち 主君の答え待ち（ask が非空）
#   実行中   席が動いている
#   外部待ち 外の人か出来事（主君の手＝lever を含む）を待つ。until の期待日は日付必須（未定は不可）。
#            期待日を書けない＝こちらの手番が無い（投げ終わり）→ 完了にして resume を書き 08アーカイブ/案件/ へ（主君裁定 2026-09-18・帳簿 id=475）
#   確認待ち 席が終えて検収待ち
#   統合可   dev だけ（この棚では使わない・行は残す）
#   完了     終わりの定義を実測して閉じた
#   吸収済   absorb 先へ写した・墓標
STATES = ("起案", "裁定待ち", "実行中", "外部待ち", "確認待ち", "統合可", "完了", "吸収済")
# 旧語の読み替え（--check が理由に出す）
STATE_LEGACY = {"未着手": "起案", "条件待ち": "外部待ち", "対応中": "実行中", "凍結": "（08アーカイブ/案件/ の箱で表す）"}
# 07プロジェクト/<箱>/status.md の frontmatter 11 項目（この順）。これ以外の鍵は --check が弾く
BOX_KEYS = ("title", "state", "owner", "ask", "lever", "until", "resume", "next", "absorb", "due", "tmp_ttl", "updated")
BOX_EMPTY_OK = ("ask", "lever", "until", "resume", "next", "due", "tmp_ttl")
# ============================== writer（1 項目 1 人）==============================
#   title・absorb   作った席（1 回）
#   state           箱の持ち主（起案の間は作った席・孔明が配車したらその席）
#   owner           孔明が配車したとき。⛔「主君」「<!-- 要確認 -->」は不可（主君の番は lever で表す）
#   ask             持ち主。主君の決裁が要る問い。書式 問い｜選択肢｜推奨｜決めないと
#   lever           持ち主。主君の手が要る物。書式 何を｜何秒か｜閉じると何が動くか
#   until           持ち主。外部待ちの中身。書式 何を｜誰から｜期待日（YYYY-MM-DD。state 外部待ち では 未定 不可）
#   resume          閉じた席。投げ終わった箱の再開の合図。書式 何を｜誰から｜どこで拾う（state 完了 の箱だけ。廷議が毎朝引く）
#   next            持ち主。次の 1 手（1 行）
#   due・tmp_ttl    作った席（任意）
#   updated         機械（この道具が commit 時に入れる）
# ==================================================================================
OWNER_NG = ("主君", "要確認", "<!--")
SEP = "｜"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TTL_RE = re.compile(r"^\d+d$")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOX_DIR = os.path.join(ROOT, "07プロジェクト")
FM_RE = re.compile(r"^---\n(.*?)\n---\n?", re.S)


def one_line(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def parse_frontmatter(text):
    """frontmatter → dict。字下げ行は直前の鍵の続き。無ければ None。"""
    m = FM_RE.match(text)
    if not m:
        return None
    fm, last = {}, None
    for line in m.group(1).splitlines():
        if line[:1].isspace() and last:
            fm[last] += " " + line.strip()
        elif ":" in line:
            k, v = line.split(":", 1)
            last = k.strip()
            fm[last] = v.strip().strip('"')
    return fm


def dump_frontmatter(values):
    return "---\n" + "".join(f"{k}: {one_line(values.get(k))}\n" for k in BOX_KEYS) + "---\n"


def missing(values):
    return [k for k in BOX_KEYS if k not in values or (k not in BOX_EMPTY_OK and not one_line(values.get(k)))]


def is_ask(v):
    """ask が実際の問いか。空・「なし」始まりは問いでない。"""
    v = one_line(v)
    return bool(v) and not v.startswith("なし")


def split_ask(v):
    return [p.strip() for p in one_line(v).split(SEP)]


# ---------- 書式の検査（1 項目 1 関数・理由を返す・None なら合格） ----------
def why_ask(v):
    if not is_ask(v):
        return None
    p = split_ask(v)
    if len(p) != 4 or not all(p):
        return f"ask の書式: 問い{SEP}選択肢{SEP}推奨{SEP}決めないと の 4 部（{SEP} 区切り・空欄なし）。今 {len(p)} 部"
    return None


def why_until(v):
    v = one_line(v)
    if not v:
        return None
    p = [x.strip() for x in v.split(SEP)]
    if len(p) != 3 or not all(p):
        return f"until の書式: 何を{SEP}誰から{SEP}期待日 の 3 部。今 {len(p)} 部"
    if p[2] != "未定" and not DATE_RE.match(p[2]):
        return f"until の期待日は YYYY-MM-DD か 未定: {p[2]}"
    return None


def why_resume(v):
    v = one_line(v)
    if not v:
        return None
    p = [x.strip() for x in v.split(SEP)]
    if len(p) != 3 or not all(p):
        return f"resume の書式: 何を{SEP}誰から{SEP}どこで拾う の 3 部。今 {len(p)} 部"
    return None


def why_lever(v):
    v = one_line(v)
    if not v:
        return None
    p = [x.strip() for x in v.split(SEP)]
    if len(p) != 3 or not all(p):
        return f"lever の書式: 何を{SEP}何秒か{SEP}閉じると何が動くか の 3 部。今 {len(p)} 部"
    return None


def why_owner(v):
    v = one_line(v)
    for ng in OWNER_NG:
        if ng in v:
            return f"owner に「{ng}」は不可（主君の番は lever で表す・席名を入れる）: {v}"
    return None


def why_state(fm):
    st = one_line(fm.get("state"))
    if st not in STATES:
        hint = f"→ {STATE_LEGACY[st]}" if st in STATE_LEGACY else ""
        return f"state 語彙外: {st}（{'｜'.join(STATES)}）{hint}"
    if st == "裁定待ち" and not is_ask(fm.get("ask")):
        return "state 裁定待ち なのに ask が空（主君の答え待ち＝ask が非空）"
    if st == "外部待ち" and not (one_line(fm.get("until")) or one_line(fm.get("lever"))):
        return "state 外部待ち なのに until も lever も空（外の人か出来事＝until・主君の手＝lever）"
    if st == "外部待ち" and one_line(fm.get("until")).endswith(SEP + "未定"):
        return "state 外部待ち の until に期待日が無い（未定）。こちらの続きが在るなら日付を書く。無い（投げ終わり）なら 完了 にして resume を書き 08アーカイブ/案件/ へ"
    if one_line(fm.get("resume")) and st != "完了":
        return f"resume が在るのに state が {st}（resume は 完了 の箱だけ＝閉じたが合図で戻る）"
    return None


def check_values(fm):
    why = [f"{k} なし" for k in missing(fm)]
    why += [f"表に無いキー: {k}（writer が決まっていない項目を増やさない）" for k in fm if k not in BOX_KEYS]
    for f in (why_state, ):
        r = f(fm)
        if r:
            why.append(r)
    for k, f in (("owner", why_owner), ("ask", why_ask), ("until", why_until), ("lever", why_lever), ("resume", why_resume)):
        r = f(fm.get(k))
        if r:
            why.append(r)
    for k in ("updated", "due"):
        v = one_line(fm.get(k))
        if v and not DATE_RE.match(v):
            why.append(f"{k} は YYYY-MM-DD: {v}")
    v = one_line(fm.get("tmp_ttl"))
    if v and not TTL_RE.match(v):
        why.append(f"tmp_ttl は <日数>d（例 30d）: {v}")
    return why


# ---------- box ----------
def cmd_box(a):
    path = os.path.join(a.root or BOX_DIR, a.slug, "status.md")
    given = {k: getattr(a, k) for k in BOX_KEYS if k != "updated" and getattr(a, k) is not None}
    existing, body = {}, None
    if os.path.exists(path):
        text = open(path, encoding="utf-8").read()
        m = FM_RE.match(text)
        existing = parse_frontmatter(text) or {}
        body = text[m.end():] if m else text
    values = {k: existing.get(k, "") for k in BOX_KEYS}
    values.update(given)
    values["updated"] = dt.date.today().isoformat()
    why = check_values(values)
    if why:
        print("❌ " + "／".join(why), file=sys.stderr); return 1
    if body is None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        body = f"# {one_line(values['title'])}\n"
    open(path, "w", encoding="utf-8").write(dump_frontmatter(values) + body)
    print(os.path.relpath(path, ROOT)); return 0


# ---------- --check ----------
def check_one(path):
    """→ (ok, reasons)"""
    try:
        fm = parse_frontmatter(open(path, encoding="utf-8").read())
    except OSError as e:
        return False, [str(e)]
    if fm is None:
        return False, ["frontmatter が無い"]
    why = check_values(fm)
    return not why, why


def expand(paths):
    """箱の親フォルダなら配下の全箱の status.md（無い箱は None で返す）。"""
    out = []
    for p in paths:
        if os.path.isdir(p) and os.path.basename(os.path.normpath(p)) != "" and not os.path.exists(os.path.join(p, "status.md")):
            for d in sorted(os.listdir(p)):
                fp = os.path.join(p, d)
                if os.path.isdir(fp) and not d.startswith("."):
                    sp = os.path.join(fp, "status.md")
                    out.append((fp, sp if os.path.exists(sp) else None))
        elif os.path.isdir(p):
            out.append((p, os.path.join(p, "status.md")))
        else:
            out.append((os.path.dirname(p), p))
    return out


def rel(p):
    ap = os.path.abspath(p)
    return os.path.relpath(ap, ROOT) if ap.startswith(ROOT + os.sep) else p


def cmd_check(paths):
    rc = 0
    for box, sp in expand(paths):
        if sp is None:
            print(f"❌ {rel(box)}/: status.md が無い（箱を作った席が kiroku.py box で作る）"); rc = 1; continue
        ok, why = check_one(sp)
        print(("✅ " if ok else "❌ ") + rel(sp) + ("" if ok else ": " + "／".join(why)))
        rc |= 0 if ok else 1
    return rc


# ---------- --vocab-diff ----------
def load_vocab(path):
    """別の kiroku.py の STATES・BOX_KEYS を実行せずに読む（ast）。"""
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("STATES", "BOX_KEYS"):
                out[name] = tuple(ast.literal_eval(node.value))
    return out


def cmd_vocab_diff(other):
    theirs = load_vocab(other)
    if "STATES" not in theirs:
        print(f"❌ {other}: STATES が読めない"); return 1
    rc = 0
    if STATES != theirs["STATES"]:
        rc = 1
        mine_only = [s for s in STATES if s not in theirs["STATES"]]
        theirs_only = [s for s in theirs["STATES"] if s not in STATES]
        print(f"❌ STATES が食い違う: こちら {'｜'.join(STATES)} ／ 向こう {'｜'.join(theirs['STATES'])}"
              + (f"／こちらだけ {mine_only}" if mine_only else "")
              + (f"／向こうだけ {theirs_only}" if theirs_only else "")
              + ("／並びが違う" if not mine_only and not theirs_only else ""))
    else:
        print("✅ STATES 一致")
    if "BOX_KEYS" in theirs and theirs["BOX_KEYS"] != BOX_KEYS:
        mine_only = [k for k in BOX_KEYS if k not in theirs["BOX_KEYS"]]
        theirs_only = [k for k in theirs["BOX_KEYS"] if k not in BOX_KEYS]
        print(f"ℹ️ BOX_KEYS は設計上別（門にしない）: こちらだけ {mine_only}／向こうだけ {theirs_only}")
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", nargs="+", metavar="PATH", help="紙が語彙表に合うか（exit 0/1・理由）。箱の親フォルダも可")
    ap.add_argument("--vocab-diff", metavar="KIROKU_PY", help="別の kiroku.py と語彙表を比べる（exit 0/1）")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("box", help="07プロジェクト/<slug>/status.md の frontmatter")
    p.add_argument("--slug", required=True)
    for k in BOX_KEYS:
        if k != "updated":
            p.add_argument(f"--{k}", default=None)
    p.add_argument("--root", help="箱の親（既定 <棚>/07プロジェクト/）")
    a = ap.parse_args(argv)
    if a.check:
        return cmd_check(a.check)
    if a.vocab_diff:
        return cmd_vocab_diff(a.vocab_diff)
    if a.cmd == "box":
        return cmd_box(a)
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
