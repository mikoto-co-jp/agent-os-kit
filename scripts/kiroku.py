#!/usr/bin/env python3
"""kiroku.py — 08プロジェクト の箱（status.md）の frontmatter を、同じ語彙表から吐き・検める道具（主君裁定 2026-09-18・帳簿 id=440）。

語彙表はこのファイルの先頭 1 か所だけ。生成器（build_scope_progress.py）もここを import して読む。
土台は CTO リポ `scripts/kiroku.py`（origin/main）。**STATES と `手番` の書式は CTO 版と同じ**（主君裁定 2026-10-02・帳簿 id=3117
「A: 開発の箱と同じ『手番』1 行と 4 語に揃える」）。艦隊オフィスの判定式（CTO `scripts/keiki.py` の quest_lane／ticket_lane）が
式を 2 つ持たずにこの棚の箱も読めるようにするため。`--vocab-diff` が門（STATES だけ。BOX_KEYS は設計上別）。
BOX_KEYS はこの棚の箱の鍵で、CTO の箱の鍵（n・配車・repo・scope・constraints・escalate）とは意図して違う（resume・due・tmp_ttl はこの棚だけ）。

使い方（棚のルートで）:
  box       frontmatter を吐く（既存は frontmatter だけ置換・本文不変。省いた鍵は既存の値を引き継ぐ）
            python3 scripts/kiroku.py box --slug <日付-slug> --title … --state <語彙> --owner … --absorb … \
                [--手番 '誰が｜何を｜🔬 実測'] [--resume …] [--next …] [--due YYYY-MM-DD] [--tmp_ttl 30d]
            updated は道具が今日の日付を入れる（人は書かない）
  --check   紙が語彙表に合うか（exit 0/1・理由）。パスが箱の親フォルダなら、配下の全箱を検め、status.md の無い箱も exit 1
            python3 scripts/kiroku.py --check 08プロジェクト
            python3 scripts/kiroku.py --check 08プロジェクト/*/status.md
  --vocab-diff <CTO の kiroku.py>   2 つの語彙表（STATES）を比べ、食い違えば exit 1（門）
            python3 scripts/kiroku.py --vocab-diff <CTO リポ>/scripts/kiroku.py
            BOX_KEYS は設計上別なので情報表示だけ（孔明裁定 2026-09-18・帳簿 id=450）
"""
import argparse, ast, datetime as dt, os, re, sys

# ============================== 語彙表（ここ 1 か所） ==============================
# 箱の state（4 語）。CTO リポ scripts/kiroku.py の STATES と同じ語彙表（門: --vocab-diff）
#   起案     箱を作った・誰も動いていない
#   実行中   箱が生きている。**誰のボールかは state ではなく `手番:` の『誰が』で言う**
#   完了     終わりの定義を実測して閉じた（投げ終わった箱は resume を書いて 09アーカイブ/案件/ へ）
#   吸収済   absorb 先へ写した・墓標
# 🚨 2026-10-02 主君裁定（帳簿 id=3117）で 裁定待ち・外部待ち・確認待ち・統合可 を外した（CTO は 2026-09-20／09-24 に先に外した）。
#    どれも「誰の手番か」の別表現で、state と ask／lever／until が同じ 1 つの事実を 2 か所で持っていた。
#    ⛔ 札が在ると「自分は動かなくてよい」の言い訳に使われる（CTO 実測: 外部待ち 30 本中 27 本が中の手番だった）。
STATES = ("起案", "実行中", "完了", "吸収済")
# 旧語の読み替え（--check が理由に出す）
STATE_LEGACY = {"未着手": "起案", "条件待ち": "実行中（手番 に誰を書く）", "対応中": "実行中",
                "凍結": "（09アーカイブ/案件/ の箱で表す）",
                "裁定待ち": "実行中＋手番: 主君｜…｜🔬 …＋本文の `## 決裁待ちの材料`",
                "外部待ち": "実行中＋手番: 先方｜…（期待日 YYYY-MM-DD）｜🔬 …",
                "確認待ち": "実行中＋手番: <検収する人>｜…", "統合可": "（この棚では使わない）"}

# ---------- 手番: 誰が｜何を｜🔬 実測（CTO 版と同じ書式・1 番目が『誰が』） ----------
# 🚨 旧 until は 何を｜誰から｜期待日 の順だった。**手番 は 1 番目が『誰が』**。⛔ 順を取り違えると別の節に出る（CTO 2026-09-20 実害）。
# 『誰が』の語彙（閉じた語彙・1 語）。CTO の DARE_VOCAB（主君・CTO・日直参謀・席・他の箱・社外）と同じ考え方で、
#   この棚の司令塔は 日直参謀 ではなく 孔明。開発へ渡した起票の着地を待つなら CTO。席の名前は owner と 何を に書く（⛔ 誰が に席名を入れない＝語彙が開く）
DARE_VOCAB = ("主君", "孔明", "CTO", "席", "他の箱", "先方")
INSIDE = ("主君", "孔明", "CTO", "席", "他の箱")   # ＝中の手番（撃てば進む）。主君も中（CTO の INSIDE と同じ）
OUTSIDE = ("先方",)                               # ＝外の応答待ち（旧 外部待ち の本物だけ）。開発の陣の起票の着地を待つのもここ
#   艦隊オフィスの面（CTO keiki.py）: 主君＝しゅくんの て／先方＝まっている（2026-10-02 主君裁定・帳簿 id=3148）
# 旧語 → 新語（読めるが --check が赤にして寄せ先を名指す）。社外 は 2026-10-02 に 先方 へ改名（帳簿 id=3148）
LEGACY_DARE = {"社外": "先方"}
RETIRED_DARE = "時間"   # CTO 2026-09-24 主君直命（帳簿 id=1728）で退役。時刻に縛られる手は scheduler／routine に予約して席を当てる
# 先方 の手番は 何を に `期待日 YYYY-MM-DD` を必ず書く（主君裁定 2026-09-18・帳簿 id=475「外部待ちは相手の答えの後にこちらの続きが在る箱だけ・期待日は日付必須」を手番へ移した）。
#   期待日を書けない＝こちらの続きが無い（投げ終わり）→ 完了 にして resume を書き 09アーカイブ/案件/ へ
EXPECT_RE = re.compile(r"期待日\s*(\d{4}-\d{2}-\d{2})")
MATERIAL_HEAD = "決裁待ちの材料"   # 手番 の『誰が』が 主君 の箱は、本文に `## 決裁待ちの材料`（問い／選択肢／推奨／決めないと）

# 08プロジェクト/<箱>/status.md の frontmatter 10 項目（この順）。これ以外の鍵は --check が弾く
BOX_KEYS = ("title", "state", "手番", "owner", "resume", "next", "absorb", "due", "tmp_ttl", "updated")
BOX_EMPTY_OK = ("手番", "resume", "next", "due", "tmp_ttl")
# 旧書式の鍵 → 寄せ先（--check が理由に出す）。2026-10-02 主君裁定（帳簿 id=3117）で 3 欄とも退役
BOX_LEGACY = {"until": "手番（誰が｜何を（期待日 YYYY-MM-DD）｜🔬 先に撃った実測）",
              "ask": "手番: 主君｜…｜🔬 … ＋ 本文の `## 決裁待ちの材料`（問い／選択肢／推奨／決めないと）",
              "lever": "手番: 主君｜…｜🔬 …（体を動かす頼みも同じ欄・材料の 選択肢 は空でよい）"}
# ============================== writer（1 項目 1 人）==============================
#   title・absorb   作った席（1 回）
#   state           箱の持ち主（起案の間は作った席・孔明が配車したらその席）
#   手番            詰まりを見つけた席。書式 誰が｜何を｜🔬 実測。⛔ 詰まっていない箱には書かない（空でよい）
#                   誰が＝主君 なら 🔬（自分で撃って席では閉じられないと確かめた実測）と本文の `## 決裁待ちの材料` が要る
#                   誰が＝先方 なら 何を に `期待日 YYYY-MM-DD`
#   owner           孔明が配車したとき。⛔「主君」「<!-- 要確認 -->」は不可（主君の番は 手番 で表す）
#   resume          閉じた席。投げ終わった箱の再開の合図。書式 何を｜誰から｜どこで拾う（state 完了 の箱だけ。朝廷が毎朝引く）
#   next            持ち主。次の 1 手（1 行）
#   due・tmp_ttl    作った席（任意）
#   updated         機械（この道具が commit 時に入れる）
# ==================================================================================
OWNER_NG = ("主君", "要確認", "<!--")
SEP = "｜"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TTL_RE = re.compile(r"^\d+d$")

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
# 本陣の形（器の版 本陣-1）: 受付・箱・墓標・一覧は中の OS の親＝本陣に在る。古い形（棚 1 つ）なら ROOT のまま。
#   本陣の scripts は中の OS の scripts への別名なので、どちらから撃っても realpath で中の OS を ROOT に取り、親を見る
HONJIN = os.environ.get("HONJIN_ROOT") or next((d for d in (os.path.dirname(ROOT), ROOT)
                                              if os.path.isdir(os.path.join(d, "08プロジェクト"))), ROOT)
BOX_DIR = os.path.join(HONJIN, "08プロジェクト")
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


def body_of(text):
    m = FM_RE.match(text)
    return text[m.end():] if m else text


def dump_frontmatter(values):
    return "---\n" + "".join(f"{k}: {one_line(values.get(k))}\n" for k in BOX_KEYS) + "---\n"


def missing(values):
    return [k for k in BOX_KEYS if k not in values or (k not in BOX_EMPTY_OK and not one_line(values.get(k)))]


# ---------- 手番 ----------
def teban_parts(raw):
    """`手番` を 誰が｜何を｜🔬実測 の 3 欄に割る（足りない欄は空文字）。3 欄目は最初に 🔬 で始まる欄（CTO の until_parts と同じ）。"""
    parts = [x.strip() for x in re.split(r"[｜|]", one_line(raw))]
    who, what = (parts + ["", ""])[:2]
    kenshou = next((p for p in parts[2:] if p.startswith("🔬")), "")
    return [who, what, kenshou]


def dare_of(raw):
    """`手番` の『誰が』を 1 語で返す。語彙外・空なら ""（⛔ 推測で埋めない）。"""
    who = teban_parts(raw)[0]
    who = LEGACY_DARE.get(who, who)   # 旧語は読める（門は why_teban が赤にする）
    return who if who in DARE_VOCAB else ""


def expect_of(raw):
    """`手番` の 何を に書いた `期待日 YYYY-MM-DD`（無ければ ""）。"""
    m = EXPECT_RE.search(one_line(raw))
    return m.group(1) if m else ""


def why_teban(raw, body=""):
    """`手番:` の 1 行（と 主君 なら本文）が書式に反していれば理由を並べて返す（空なら合格）。"""
    raw = one_line(raw)
    if not raw:
        return []
    why = []
    who, what, k = teban_parts(raw)
    if who == RETIRED_DARE:
        why.append("⛔ 時間 は待ち先ではない＝scheduler／routine に予約して、手番 は 席 か 孔明 にする")
    elif who in LEGACY_DARE:
        why.append(f"手番 の『誰が』の {who} は旧語＝{LEGACY_DARE[who]} に書き替える（2026-10-02 主君裁定・帳簿 id=3148）")
        who = LEGACY_DARE[who]
    elif who not in DARE_VOCAB:
        why.append(f"手番 の 1 番目が『誰が』の語彙に無い（今: {who[:40]}）。書式は 誰が{SEP}何を{SEP}🔬実測 で、"
                   f"1 番目は {'／'.join(DARE_VOCAB)} のどれか 1 語（旧 until の 何を｜誰から｜期待日 の順で書かない）")
    if not what:
        why.append("手番 の 何を が空")
    if who == "主君":
        if "🔬" not in raw:
            why.append("手番 の『誰が』が 主君 なのに 🔬 が無い（主君に出す前に自分で撃った実測を同じ行に書く）")
        if MATERIAL_HEAD not in (body or ""):
            why.append(f"手番 の『誰が』が 主君 なのに、本文に `## {MATERIAL_HEAD}` が無い"
                       "（問い／選択肢／推奨／決めないと を書く。体を動かす頼みなら 選択肢 は空でよい）")
    if who == "先方" and not expect_of(raw):
        why.append("手番 の『誰が』が 先方 なのに 何を に `期待日 YYYY-MM-DD` が無い"
                   "（書けない＝こちらの続きが無い→ 完了 にして resume を書き 09アーカイブ/案件/ へ・帳簿 id=475）")
    return why


# ---------- 他の箱 の先（CTO keiki.py の当て方と同じ・2026-10-05 主君 OK「きみやっちゃってください」・帳簿 4535） ----------
# 『誰が』＝他の箱 は「棚の中の開いた箱」か「CTO の 02案件 の箱（n=<番号>）」を指すときだけ。先が紙や出来事だと
# 艦隊オフィスは「放置・紙を指している」＝画面で「席がいない」と出す（2026-10-05 実害: 孔明が開発待ちの 4 箱に 他の箱 と書いた）。
# 開発の陣の着地を待つ箱は 先方（メモリシステム「開発の陣の起票の着地を待つのも 先方」）。
# CTO の 02案件 の置き場は環境変数 KIROKU_CTO_ROOT（固有値を書かない）。無ければ n= の先は「測定不能」で通さない。
N_RX = re.compile(r"\bn\s*=\s*(\d+)")


def open_box_slugs(self_slug=""):
    base = BOX_DIR
    out = []
    if not os.path.isdir(base):
        return out
    for d in os.listdir(base):
        sp = os.path.join(base, d, "status.md")
        if d == self_slug or not os.path.exists(sp):
            continue
        fm = parse_frontmatter(open(sp, encoding="utf-8").read()) or {}
        if one_line(fm.get("state")) not in ("完了", "吸収済"):
            out.append(d)
    return out


def cto_open_ns():
    """CTO の 02案件 の開いた箱の n の集合。置き場が分からなければ None（測定不能）。"""
    root = os.environ.get("KIROKU_CTO_ROOT", "")
    base = os.path.join(root, "02案件") if root else ""
    if not base or not os.path.isdir(base):
        return None
    ns = set()
    for d in os.listdir(base):
        sp = os.path.join(base, d, "status.md")
        if os.path.exists(sp):
            m = re.search(r"^n:\s*(\d+)\s*$", open(sp, encoding="utf-8").read(), re.M)
            if m:
                ns.add(m.group(1))
    return ns


def why_hoka(raw, self_slug=""):
    """手番 の『誰が』が 他の箱 なら、何を が開いた箱を指しているか。理由を返す（空なら合格）。"""
    raw = one_line(raw)
    if not raw or teban_parts(raw)[0] != "他の箱":
        return []
    what = teban_parts(raw)[1]
    if any(s in what for s in open_box_slugs(self_slug)):
        return []
    ns = N_RX.findall(what)
    if ns:
        have = cto_open_ns()
        if have is None:
            return ["手番 の『誰が』が 他の箱 で n= を指すが、CTO の 02案件 が見えない（KIROKU_CTO_ROOT）＝測定不能で通さない"]
        if any(n in have for n in ns):
            return []
    return ["手番 の『誰が』が 他の箱 なのに、何を が開いた箱（08プロジェクト/<slug> か CTO 02案件 の n=<番号>）を指していない"
            "＝計器は「席がいない（紙を指している）」と出す。開発の陣の着地を待つなら 先方｜…（期待日 YYYY-MM-DD）"]


# ---------- 書式の検査（1 項目 1 関数・理由を返す・None なら合格） ----------
def why_resume(v):
    v = one_line(v)
    if not v:
        return None
    p = [x.strip() for x in v.split(SEP)]
    if len(p) != 3 or not all(p):
        return f"resume の書式: 何を{SEP}誰から{SEP}どこで拾う の 3 部。今 {len(p)} 部"
    return None


def why_owner(v):
    v = one_line(v)
    for ng in OWNER_NG:
        if ng in v:
            return f"owner に「{ng}」は不可（主君の番は 手番 で表す・席名を入れる）: {v}"
    return None


def why_state(fm):
    st = one_line(fm.get("state"))
    if st not in STATES:
        hint = f"→ {STATE_LEGACY[st]}" if st in STATE_LEGACY else ""
        return f"state 語彙外: {st}（{'｜'.join(STATES)}）{hint}"
    if one_line(fm.get("resume")) and st != "完了":
        return f"resume が在るのに state が {st}（resume は 完了 の箱だけ＝閉じたが合図で戻る）"
    return None


def check_values(fm, body=""):
    why = [f"{k} なし" for k in missing(fm)]
    why += [f"旧書式 {k}: → {to}" for k, to in BOX_LEGACY.items() if k in fm]
    why += [f"表に無いキー: {k}（writer が決まっていない項目を増やさない）" for k in fm
            if k not in BOX_KEYS and k not in BOX_LEGACY]
    r = why_state(fm)
    if r:
        why.append(r)
    for k, f in (("owner", why_owner), ("resume", why_resume)):
        r = f(fm.get(k))
        if r:
            why.append(r)
    why += why_teban(fm.get("手番"), body)
    for k in ("updated", "due"):
        v = one_line(fm.get(k))
        if v and not DATE_RE.match(v):
            why.append(f"{k} は YYYY-MM-DD: {v}")
    v = one_line(fm.get("tmp_ttl"))
    if v and not TTL_RE.match(v):
        why.append(f"tmp_ttl は <日数>d（例 30d）: {v}")
    return why


def dup_keys(text):
    """同じキーが 2 度書かれていたら理由（パーサは後勝ちに潰すので書いた側から見えない・CTO 2026-09-20 実害）。"""
    m = FM_RE.match(text)
    seen = {}
    for l in (m.group(1).splitlines() if m else []):
        k = re.match(r"^([^:\s]+):", l)
        if k:
            seen[k.group(1)] = seen.get(k.group(1), 0) + 1
    return [f"同じキーが {v} 回: {k}（1 項目 1 行）" for k, v in seen.items() if v > 1]


# ---------- box ----------
def cmd_box(a):
    path = os.path.join(a.root or BOX_DIR, a.slug, "status.md")
    given = {k: getattr(a, k) for k in BOX_KEYS if k != "updated" and getattr(a, k) is not None}
    existing, body = {}, None
    if os.path.exists(path):
        text = open(path, encoding="utf-8").read()
        existing = parse_frontmatter(text) or {}
        body = body_of(text)
    values = {k: existing.get(k, "") for k in BOX_KEYS}
    values.update(given)
    values["updated"] = dt.date.today().isoformat()
    if body is None:
        body = f"# {one_line(values['title'])}\n"
    why = check_values(values, body)
    if why:
        print("❌ " + "／".join(why), file=sys.stderr); return 1
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(dump_frontmatter(values) + body)
    print(os.path.relpath(path, ROOT)); return 0


# ---------- --check ----------
def check_one(path):
    """→ (ok, reasons)"""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        return False, [str(e)]
    fm = parse_frontmatter(text)
    if fm is None:
        return False, ["frontmatter が無い"]
    slug = os.path.basename(os.path.dirname(os.path.abspath(path)))
    why = check_values(fm, body_of(text)) + dup_keys(text) + why_hoka(fm.get("手番"), slug)
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
            if name in ("STATES", "BOX_KEYS", "DARE_VOCAB"):
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
    if "BOX_KEYS" in theirs:
        if "手番" not in theirs["BOX_KEYS"]:
            rc = 1; print("❌ 向こうの BOX_KEYS に 手番 が無い（手番の 1 欄が両方の箱の共通の鍵）")
        if theirs["BOX_KEYS"] != BOX_KEYS:
            mine_only = [k for k in BOX_KEYS if k not in theirs["BOX_KEYS"]]
            theirs_only = [k for k in theirs["BOX_KEYS"] if k not in BOX_KEYS]
            print(f"ℹ️ BOX_KEYS は設計上別（門にしない）: こちらだけ {mine_only}／向こうだけ {theirs_only}")
    if "DARE_VOCAB" in theirs:
        missing = [w for w in DARE_VOCAB if w not in theirs["DARE_VOCAB"]]
        if missing:
            rc = 1; print(f"❌ こちらの『誰が』{missing} が向こう（keiki が読む語彙）に無い＝艦隊オフィスの面で 手番が空 に落ちる")
        print(f"ℹ️ 手番 の『誰が』: こちら {'／'.join(DARE_VOCAB)} ／ 向こう {'／'.join(theirs['DARE_VOCAB'])}（こちらの語は全部向こうに在ること）")
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", nargs="+", metavar="PATH", help="紙が語彙表に合うか（exit 0/1・理由）。箱の親フォルダも可")
    ap.add_argument("--vocab-diff", metavar="KIROKU_PY", help="別の kiroku.py と語彙表を比べる（exit 0/1）")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("box", help="08プロジェクト/<slug>/status.md の frontmatter")
    p.add_argument("--slug", required=True)
    for k in BOX_KEYS:
        if k != "updated":
            p.add_argument(f"--{k}", dest=k, default=None)
    p.add_argument("--root", help="箱の親（既定 <棚>/08プロジェクト/）")
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
