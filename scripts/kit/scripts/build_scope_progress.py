#!/usr/bin/env python3
"""docs/SCOPE_PROGRESS.md の生成器（9 節固定）。読むのは元だけ、書くのは 1 枚。手で編集しない。

型の正本はこの docstring（旧 影分身/分身.md の型の節は 2026-09-15 に退役）。節の順は固定。空の節は「（なし）」1 行。
語彙表（箱の state・鍵）は scripts/kiroku.py から import する（主君裁定 2026-09-18・帳簿 id=440）。
  （2026-10-02 主君裁定・帳簿 id=3117: 箱の書き方を開発の箱と同じ 4 語の state と `手番: 誰が｜何を｜🔬実測` の 1 欄に揃えた。
   ask／lever／until は退役。裁定表・主君の手・待ち受けの 3 節はどれも 手番 の『誰が』1 本から仕分ける＝誰のボールかを 2 か所で持たない）
  1. プロジェクト     08プロジェクト/*/status.md を state 別（起案／実行中／完了）の表＝箱｜owner｜手番（誰が）｜next｜updated。
                      status.md の無い箱・語彙外の state は赤。09アーカイブ/案件/ のフォルダは state で 閉じた箱（数）／凍結（末尾に一覧）／墓標が読めない（赤）に分ける
  2. 裁定表           00朝廷/*.md の全数（手番 の『誰が』＝主君 の紙。孔明 の紙は「孔明が裁く（うけつけ）」に別に出す・手番なしは差し戻し）
                      ＋ 手番 の『誰が』＝主君 の箱のうち、本文 `## 決裁待ちの材料` に 選択肢 が在る物（問い｜選択肢｜推奨｜決めないと）。
                      束ねない。推奨なしは差し戻し
                      ＋ 定点の窓口（DESKS の status.md）の ask も同じ書式で載せる（08プロジェクト/ の外に居る終わりの無い箱・まだ旧書式）
  3. 主君の手         手番 の『誰が』＝主君 の箱のうち、材料に 選択肢 が無い物（体を動かす頼み）＝箱｜何を｜🔬 実測
  4. 待ち受け         手番 の『誰が』が 主君 以外の箱＝箱｜誰が｜何を｜期待日（何を の `期待日 YYYY-MM-DD`。今日を過ぎていれば 🔴）
                      ＋ 再開の合図＝09アーカイブ/案件/ の箱で resume が非空（投げ終わった箱。朝廷が毎朝 1 件ずつ引く）
  5. Routine          時計の控え＝routine の ~/.claude/routine/routines.json（初伝から使える既定の時計）と、
                      皆伝の機体なら scheduler の ~/.claude/scheduler/schedules.json も。在る方を全部読んで 1 表に合わせる
                      （片方だけの機体で足りる・--schedules <json> で 1 本に差し替え可）。最終発火は控えの隣の runs.log／fires.log
                      （月替わりで畳まれた fires-YYYY-MM.log も読む）。
                      頭の数字: fail＝最後の発火か、席が起きた最後の回（skipped_* と check 自体の落ちを除く）が error／timeout。
                      見張りが「用無し」と答えた周（skipped_policy）・前の回が走っている周（skipped_running）・席が自分で閉じた回
                      （done_self）は落ちではない。
                      実行未記録＝scheduler の止めていない便で、席が 1 回でも起きたのに窓に 1 行も無い物（routine と 1 度も起きていない便は数えない）。
                      席が立たない便は別の欄: check だけ＝起こしたが check が毎回「用無し」で席が 1 度も立っていない／
                      未発火＝時計がまだ 1 度も起こしていない。実行の列は窓の便名を label の括弧の頭の英語名と routine の name でも引く。
                      時計 列＝その便をどちらの時計が起こすか。agent 列＝その便を走らせる席（routine には agent が無いので「—」）。
                      「手順書」列＝その便を回す席の本文（06エージェント資産/_便/ のエイリアス。畳む途中の棚は docs/定期便-手順/ も見る）。
                      「実行」列＝その便が帳簿（記録 MCP kiroku の run_start／run_end）に走った記録を残したか。
                      ⚠️ Python から口は撃てる（scripts/mcplib.py・2026-09-20 実測）が、**帳簿に便ごとの実行を読む口が無い**。
                      全便が同じ席名 `scheduler` で書く決まりなので `run_last` は席単位でしか引けない（⇒ 便ごとに分けられない）。
                      ⇒ 便が run_end と同時に置く 11一時ファイル/便の実行-YYYY-MM.tsv を読む（--runs で差し替え可）。
                      正本は帳簿・この tsv は窓（中の OS と本陣の 2 か所を読む）。tsv が無ければ全便「取得不能（tsv なし）」と出す（0 件とは書かない）
  6. エージェント（席） 06エージェント資産/_索引-写し.md の箱ごとの体数 ＋ --monsters <json>（list_monsters の結果）
  7. 完了（30 日）    09アーカイブ/案件/*.md の墓標 ＋ フォルダのまま閉じた箱（status.md の state が 完了・吸収済・閉じた日は updated）
  8. 棚の差分         数だけ（08プロジェクト・00朝廷・一段目のみ。深い走査はしない）
  9. 期限（金庫の鍵） 金庫（password-manager）の各項目の説明に書いた「期限 YYYY-MM-DD」を近い順に並べ、残り 14 日以内か切れた物に 🔴。
                      生成器は MCP を撃てない＝席が `list_secrets` の出力をファイルに保存して `--vault <ファイル>` で渡す。出すのは項目名と期限だけ
                      （説明の他の文・値は出さない）。期限の正本は金庫の説明のまま（⛔ 写しの台帳を作らない）。
                      ⛔ 渡されないときは「取得不能」と出す（「（なし）」や 0 件と書かない）。期限の書かれていない項目は出さない。
                      1〜8 の節の番号を動かさないために末尾に足した（他の紙が裁定表と Routine の節を番号で指している）

--check: 自己一致。①生成器の語彙が kiroku.STATES と同じ ②08プロジェクト/ の全箱が kiroku --check を通る
        ③箱から作る節（1〜4）を今の docs/SCOPE_PROGRESS.md と比べて一致（生成し直しが要るなら exit 1）

退役した生成器をここへ畳んだ（2026-09-14）:
  build_council.py  → 裁定表の節（書式判定 問い｜選択肢｜推奨｜決めないと・差し戻し）。docs/裁定会.md は廃止
  build_schedules.py → Routine の節（scheduler を直読み）。docs/定期便.md は廃止
「条件待ち」の節は 2026-09-18 に待ち受けの節（until）へ替えた。「廃止候補」の節は 2026-09-14 に型から外した。

ROOT は環境変数 MIKOTO_OS_ROOT か、このファイルの 2 つ上（scripts/ の親）。
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import kiroku  # 語彙表の正本（STATES・BOX_KEYS・parse_frontmatter・check_one）

ROOT = os.environ.get("MIKOTO_OS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.realpath(__file__)))
# 本陣の形（器の版 本陣-1）: 受付・箱・墓標・一覧は中の OS の親＝本陣に在る。古い形（棚 1 つ）なら ROOT のまま
HONJIN = kiroku.HONJIN if not os.environ.get("MIKOTO_OS_ROOT") else (
    os.environ.get("HONJIN_ROOT") or next((d for d in (os.path.dirname(ROOT), ROOT)
                                          if os.path.isdir(os.path.join(d, "08プロジェクト"))), ROOT))
OUT_DEFAULT = os.path.join(HONJIN, "docs", "SCOPE_PROGRESS.md")
# 時計の控え。routine（初伝から使える既定の時計）は全機体、scheduler は皆伝の機体だけに在る。在る方を全部読む
ROUTINE_DIR = os.environ.get("ROUTINE_DIR") or os.path.expanduser("~/.claude/routine")
SCHED_DIR = os.environ.get("SCHEDULER_DIR") or os.path.expanduser("~/.claude/scheduler")
PROJ = os.path.join(HONJIN, "08プロジェクト")
# 受付。古い形の棚（更新の前）は 00廷議 のまま在ることがある＝在る方を読む（両方無ければ 00朝廷）
APPROVE = next((p for p in (os.path.join(HONJIN, "00朝廷"), os.path.join(HONJIN, "00廷議")) if os.path.isdir(p)),
               os.path.join(HONJIN, "00朝廷"))
# 定点の窓口＝終わりの無い箱。08プロジェクト/ には置かないが、status.md の ask は裁定表の節に載せる（書式は箱と同じ）
DESKS = [os.path.join(ROOT, "04オペレーション資産", "customer", "サポート", "status.md")]
GRAVES = os.path.join(HONJIN, "09アーカイブ", "案件")
# その便を回す席の本文が在るか（Routine の節の「手順書」列）。2026-09-20 に「便という種類をやめて席に一本化する」で
# 正本は 06エージェント資産/_便/（{HHMM}-{便}.md のエイリアス）へ移った。docs/定期便-手順/ は畳む途中の棚のためだけに残す
PROC_DIRS = [os.path.join(ROOT, "06エージェント資産", "_便"),
             os.path.join(HONJIN, "docs", "定期便-手順")]
RUNS = os.path.join(ROOT, "11一時ファイル")   # 便が run_end と同時に置く tsv（窓。正本は帳簿）
# 本陣で起きた席は本陣の 11一時ファイル/ に書くことがある。両方を読む（同じ所なら 1 つ）
RUNS_DIRS = list(dict.fromkeys([RUNS, os.path.join(HONJIN, "11一時ファイル")]))
# 時計の結果の語のうち「落ちた」だけ。done_self／done／done_idle／ok＝走り終えた、spawned＝起こした、
# skipped_policy＝見張りが用無しと答えた周、skipped_running＝前の回がまだ走っている周＝どれも正常
FAIL_RESULTS = ("error", "timeout")
PROMPTS = os.path.join(ROOT, "06エージェント資産")
PROMPT_INDEX = os.path.join(PROMPTS, "_索引-写し.md")   # ⛔ 人が書く _索引.md ではない
SKILL_INDEX = os.path.join(PROMPTS, "06二軍エージェント", "_索引-スキル.md")
DONE_DAYS = 30
BIG_BYTES = 5 * 1024 * 1024
MEDIA = (".mp4", ".mov", ".pdf", ".png", ".jpg", ".jpeg", ".zip")
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

# 箱の state は kiroku.STATES（4 語）。生成器はこの並びでプロジェクトの節の表を出す。語彙外・status.md 無しは赤
STATES = kiroku.STATES
STATE_SECTIONS = ("起案", "実行中", "完了")   # プロジェクトの節に必ず出す 3 つ（吸収済 は在るときだけ）
STATE_ORDER = {s: i for i, s in enumerate(STATES)}
STATE_ORDER.update({"語彙外": 90, "状態なし": 91, "凍結": 92})
# 09アーカイブ/案件/ の下のフォルダの箱を status.md の state で分ける（箱 n=4971・2026-11-15 会員の報告）。
#   完了・吸収済＝閉じた箱（数だけプロジェクトの節・30 日以内は完了の節）／起案・実行中・旧語（kiroku.STATE_LEGACY）・frontmatter の無い
#   旧書式の status.md・status.md の無い資料だけのフォルダ＝凍結（再点火は主君）／frontmatter は在るが state が空・語彙外＝赤「墓標が読めない」
CLOSED_STATES = ("完了", "吸収済")
FROZEN_STATES = tuple(s for s in STATES if s not in CLOSED_STATES) + tuple(kiroku.STATE_LEGACY)


# ---------- 読む道具 ----------

def frontmatter(path):
    """--- ... --- を dict に。無ければ None。"""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm


def cell(s, limit=None):
    s = re.sub(r"<!--.*?-->", "", str(s or ""), flags=re.S).strip()
    s = s.replace("|", "｜").replace("\n", " ").strip()
    s = re.sub(r"\s+", " ", s)
    if limit and len(s) > limit:
        s = s[:limit - 1] + "…"
    return s


def has_ask(ask):
    """ask が実際の問いか。空・「なし」始まりは問いでない。"""
    a = (ask or "").strip().strip('"')
    return bool(a) and not a.startswith("なし")


def split_ask(text):
    """build_council.py と同じ書式判定: 問い｜選択肢｜推奨｜決めないと"""
    parts = [p.strip() for p in str(text).split("｜")]
    while len(parts) < 4:
        parts.append("")
    return parts[:4]


def days_since(iso):
    try:
        return (dt.date.today() - dt.date.fromisoformat(iso)).days
    except (ValueError, TypeError):
        return None


def md(iso):
    """2026-09-14 → 09-14"""
    return iso[5:] if re.match(r"^\d{4}-\d{2}-\d{2}", str(iso or "")) else cell(iso)


# ---------- 1. プロジェクト ----------

def read_projects():
    """rows: state / name / owner / next / due / updated / 手番 / material（本文の 決裁待ちの材料）/ bad（赤）"""
    rows, no_status = [], []
    for d in sorted(glob.glob(os.path.join(PROJ, "*"))):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d)
        sp = os.path.join(d, "status.md")
        if not os.path.exists(sp):
            no_status.append(name)
            rows.append({"state": "状態なし", "name": name, "owner": "?",
                         "next": "**status.md が無い。付けるまで赤**", "due": "", "updated": "",
                         "手番": "", "material": {}, "bad": True})
            continue
        text = open(sp, encoding="utf-8").read()
        fm = kiroku.parse_frontmatter(text) or {}
        st = fm.get("state", "").strip()
        bad = st not in STATES
        rows.append({"state": st if not bad else "語彙外", "raw_state": st, "name": name,
                     "owner": fm.get("owner", ""), "next": fm.get("next", ""),
                     "due": fm.get("due", ""), "updated": fm.get("updated", ""),
                     "手番": fm.get("手番", ""), "material": read_material(kiroku.body_of(text)),
                     "path": sp, "bad": bad})
    rows.sort(key=lambda r: (STATE_ORDER.get(r["state"], 89), r["due"] or "9999", r["name"]))
    return rows, no_status


def name_date(name):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else ""


def grave_box(d):
    """09アーカイブ/案件/<フォルダ>/ を 1 つ読む → (kind, row)。kind は 閉じた／凍結／読めない。
    閉じた日は status.md の updated（無ければフォルダ名の日付）"""
    name = os.path.basename(d)
    sp = os.path.join(d, "status.md")
    if not os.path.exists(sp):
        return "凍結", {"name": name}                       # 資料だけのフォルダ
    text = open(sp, encoding="utf-8").read()
    fm = kiroku.parse_frontmatter(text)
    if fm is None:
        return "凍結", {"name": name}                       # frontmatter の無い旧書式（語彙より前の箱）
    st = (fm.get("state") or "").strip()
    if st in CLOSED_STATES:
        upd = (fm.get("updated") or "").strip()
        closed = upd if re.match(r"^\d{4}-\d{2}-\d{2}$", upd) else name_date(name)
        return "閉じた", {"name": name, "state": st, "closed": closed,
                          "title": fm.get("title") or name, "absorb": fm.get("absorb") or "—",
                          "grave": os.path.relpath(sp, HONJIN)}
    if st in FROZEN_STATES:
        return "凍結", {"name": name}
    return "読めない", {"name": name, "raw_state": st}


def read_graves():
    """→ closed（行）, frozen（名前）, unreadable（行）。1 枚の墓標（*.md）はここで数えない（完了の節の read_done が読む）"""
    closed, frozen, unreadable = [], [], []
    for d in sorted(glob.glob(os.path.join(GRAVES, "*"))):
        if not os.path.isdir(d):
            continue
        kind, row = grave_box(d)
        {"閉じた": closed, "凍結": frozen, "読めない": unreadable}[kind].append(row if kind != "凍結" else row["name"])
    return closed, frozen, unreadable


def read_material(body):
    """本文の `## 決裁待ちの材料` 節から 問い／選択肢／推奨／決めないと を取る（- 鍵: 値 の行。決めないと は「決めないと…:」で始まる鍵も可）。"""
    m = re.search(r"^## " + kiroku.MATERIAL_HEAD + r".*?$(.*?)(?=^## |\Z)", body or "", re.S | re.M)
    out = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        mm = re.match(r"^\s*[-*]\s*(問い|選択肢|推奨|決めないと)[^:：]*[:：]\s*(.*)$", line)
        if mm and mm.group(1) not in out:
            out[mm.group(1)] = mm.group(2).strip()
    return out


def is_body_ask(opts):
    """選択肢が無い（空・「（体を動かす頼み）」）＝裁定ではなく体を動かす頼み＝主君の手の節"""
    o = cell(opts)
    return not o or o.startswith("（体を動かす")


def read_desks():
    """定点の窓口（DESKS）の status.md を箱と同じ形で読む。裁定表の節の ask にだけ使う。紙が無ければ読み飛ばす"""
    rows = []
    for sp in DESKS:
        if not os.path.exists(sp):
            continue
        fm = kiroku.parse_frontmatter(open(sp, encoding="utf-8").read()) or {}
        rows.append({"name": os.path.relpath(os.path.dirname(sp), ROOT), "owner": fm.get("owner", ""),
                     "updated": fm.get("updated", ""), "ask": fm.get("ask", ""), "due": fm.get("due", ""),
                     "note": "（窓口）"})
    return rows


def split3(v):
    parts = [p.strip() for p in cell(v).split("｜")]
    while len(parts) < 3:
        parts.append("")
    return parts[:3]


# ---------- 2. 裁定表 ----------

def read_council(projects):
    """00朝廷/*.md（正） ＋ 手番=主君 の箱の材料 ＋ 窓口の ask。推奨なしは表に入れず差し戻し。
    00朝廷 の紙は 手番 の『誰が』で分ける: 主君＝裁定表／孔明＝うけつけ（孔明が受けるか断るかを裁く）／手番なし＝差し戻し"""
    items, sent_back, koumei = [], [], []

    for p in sorted(glob.glob(os.path.join(APPROVE, "*.md"))):
        fm = frontmatter(p)
        base = os.path.basename(p)
        seat = (fm or {}).get("席", "") or base
        if not fm:
            sent_back.append((seat, base, "frontmatter が無い"))
            continue
        rec, opts = fm.get("推奨", ""), fm.get("選択肢", "")
        if not rec:
            sent_back.append((seat, base, "推奨なし"))
            continue
        if not opts:
            sent_back.append((seat, base, "選択肢なし"))
            continue
        age = days_since((re.match(r"(\d{4}-\d{2}-\d{2})", base) or [None, ""])[1]) or 0
        row = {"seat": seat, "q": fm.get("問い", ""), "opts": opts, "rec": rec,
               "due": fm.get("期限", ""), "cost": fm.get("決めないと", ""),
               "age": age, "note": "",
               "key": (fm.get("案件", "") or fm.get("プロジェクト", "") or seat)}
        dare = kiroku.dare_of(fm.get("手番", ""))
        if dare == "主君":
            items.append(row)
        elif dare == "孔明":
            koumei.append(row)
        else:
            sent_back.append((seat, base, "手番なし（主君か孔明か）" if not dare else f"手番 の誰が が {dare}（00朝廷 は 主君 か 孔明）"))

    # 手番=主君 の箱の材料（選択肢が在る物＝裁定。無い物は主君の手の節）
    for r in projects:
        if kiroku.dare_of(r.get("手番")) != "主君" or is_body_ask(r["material"].get("選択肢")):
            continue
        mt = r["material"]
        seat = cell(r.get("owner")) or "?"
        age = days_since(r.get("updated")) or 0
        row = {"seat": seat, "q": mt.get("問い", ""), "opts": mt.get("選択肢", ""), "rec": mt.get("推奨", ""),
               "due": r.get("due", ""), "cost": mt.get("決めないと", ""), "age": age, "note": "（箱）", "key": r["name"]}
        if row["rec"]:
            items.append(row)
        else:
            sent_back.append((seat, r["name"] + "（箱の材料）", "推奨なし"))

    # 定点の窓口の ask（DESKS・まだ旧書式の紙。窓口の writer が 手番 へ移すまでここで拾う）
    for r in read_desks():
        if not has_ask(r.get("ask")):
            continue
        q, opts, rec, cost = split_ask(r["ask"])
        seat = cell(r.get("owner")) or "?"
        age = days_since(r.get("updated")) or 0
        row = {"seat": seat, "q": q, "opts": opts, "rec": rec, "due": r.get("due", ""),
               "cost": cost, "age": age, "note": r.get("note", "（箱）"), "key": r["name"]}
        if rec and opts:
            items.append(row)
        else:
            sent_back.append((seat, r["name"] + "（箱の ask）", "推奨なし" if not rec else "選択肢なし"))

    # 全数を出す（束ねない・2026-09-14 主君 GO）。並びは期限が近い順 → 古い順
    items.sort(key=lambda r: (r["due"] or "9999", -r["age"]))
    return items, koumei, sent_back


# ---------- 3. 主君の手／ 4. 待ち受け（どちらも 手番 の『誰が』から） ----------

def read_levers(projects):
    out = []
    for r in projects:
        if kiroku.dare_of(r.get("手番")) != "主君" or not is_body_ask(r["material"].get("選択肢")):
            continue
        _who, what, k = kiroku.teban_parts(r["手番"])
        out.append({"name": r["name"], "what": what, "k": k})
    return out


def read_untils(projects):
    out = []
    today = dt.date.today()
    for r in projects:
        who = kiroku.dare_of(r.get("手番"))
        if not cell(r.get("手番")) or who == "主君":
            continue
        _w, what, _k = kiroku.teban_parts(r["手番"])
        when = kiroku.expect_of(r["手番"])
        late = bool(when) and dt.date.fromisoformat(when) < today
        out.append({"name": r["name"], "what": what, "who": who or "⚠️語彙外", "when": when or "—", "late": late})
    out.sort(key=lambda r: (r["when"] if re.match(r"^\d{4}-", r["when"]) else "9999", r["name"]))
    return out


def read_resumes():
    """09アーカイブ/案件/<箱>/status.md の resume（何を｜誰から｜どこで拾う）"""
    out = []
    for d in sorted(glob.glob(os.path.join(GRAVES, "*"))):
        sp = os.path.join(d, "status.md")
        if not os.path.isdir(d) or not os.path.exists(sp):
            continue
        fm = kiroku.parse_frontmatter(open(sp, encoding="utf-8").read()) or {}
        if not cell(fm.get("resume")):
            continue
        what, who, where = split3(fm["resume"])
        out.append({"name": os.path.basename(d), "what": what, "who": who, "where": where})
    return out


# ---------- 5. Routine ----------

def cron_time(cron):
    f = str(cron or "").split()
    if len(f) < 5:
        return cell(cron)
    mi, hh, dom, mon, dow = f[:5]
    t = f"{int(hh):02d}:{int(mi):02d}" if hh.isdigit() and mi.isdigit() else f"{hh}:{mi}"
    extra = [x for x in (("日 " + dom) if dom != "*" else "",
                         ("月 " + mon) if mon != "*" else "",
                         ("曜 " + dow) if dow != "*" else "") if x]
    return t + ("（" + "・".join(extra) + "）" if extra else "")


# (時計の名前, 控えの dir, 控えのファイル名, 一覧の鍵, 最終発火の log, log の id 鍵)
CLOCKS = (("routine", lambda: ROUTINE_DIR, "routines.json", "routines", "runs.log", "routine_id"),
          ("scheduler", lambda: SCHED_DIR, "schedules.json", "schedules", "fires.log", "schedule_id"))


def short_ts(ts):
    """ISO → "MM-DD HH:MM"（この機体の時刻）。読めない物も頭の YYYY-MM-DDTHH:MM だけは拾う。
    ⛔ 読めない文字列をそのまま返さない（"2026-…" は "11-…" より大きいと並び、古い行が最新に見える）"""
    ts = (ts or "").strip()
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%m-%d %H:%M")
    except ValueError:
        m = re.match(r"\d{4}-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})", ts)
        if m:
            return f"{m[1]}-{m[2]} {m[3]}:{m[4]}"
        m = re.match(r"\d{4}-(\d{2})-(\d{2})", ts)
        return f"{m[1]}-{m[2]} 00:00" if m else ts


def read_fires(fires, key):
    """最終発火の log → {id: 最後の行}。無ければ空。
    月替わりで畳まれた控え（fires-YYYY-MM.log など・UTC の月で切れる）も読む＝月 1 の便の発火を取りこぼさない。
    各行に `_act`（skipped_* でない最後の行＝席が実際に起きた／落ちた最後の回）を付ける。"""
    last, act = {}, {}
    if not fires:
        return last
    stem, ext = os.path.splitext(fires)
    paths = sorted(glob.glob(f"{stem}-20??-??{ext}")) + [fires]
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    last[r.get(key)] = r
                    # 見張り（check）自体が落ちた行は席の回ではない＝後で check が通れば治っている
                    if not (str(r.get("result") or "").startswith("skipped")
                            or str(r.get("detail") or "").startswith("check")):
                        act[r.get(key)] = r
    return {k: dict(v, _act=act.get(k, {})) for k, v in last.items()}


def load_schedules(path):
    """時計の正本だけを読む（2026-09-14: docs/定期便.md は退役・写しから読まない）。
    既定は routine（routines.json）と scheduler（schedules.json）の在る方を全部読んで合わせる
    （routine だけの機体でも・両方在る皆伝の機体でも、便を取りこぼさない）。path を渡せばその 1 本だけ。
    戻り: (一覧 or None, src)。一覧の各便には `_clock`（routine／scheduler）と `_fire`（最終発火の行・無ければ {}）を付ける。
    控えが 1 本も無ければ None（⛔ 0 本と区別する）。"""
    if path:
        cands = [(None, path)]
    else:
        cands = [(c, os.path.join(d(), fn)) for c, d, fn, *_ in CLOCKS]
    found = [(c, p) for c, p in cands if os.path.exists(p)]
    if not found:
        return None, "・".join(p for _, p in cands)
    out = []
    for clock, src in found:
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
        if clock is None:   # 渡された 1 本は中身の鍵で見分ける
            clock = "routine" if isinstance(data, dict) and "routines" in data else "scheduler"
        _, _, _, key, log, id_key = next(c for c in CLOCKS if c[0] == clock)
        if isinstance(data, dict):
            data = data.get(key, data.get("result", data))
        if not isinstance(data, list):
            return None, src
        last = read_fires(os.path.join(os.path.dirname(src), log), id_key)
        for s in data:
            if isinstance(s, dict):
                out.append(dict(s, _clock=clock, _fire=last.get(s.get("id"), {})))
    return out, "・".join(p for _, p in found)


def read_runs(runs_path):
    """便が run_end と同時に置く tsv を読む。戻り: (最後の実行 {便名: "MM-DD HH:MM 結果"}, tsv が 1 枚でも在ったか)。

    列: 開始ISO<TAB>便名<TAB>結果<TAB>実行id<TAB>中身（書式は .claude/rules/メモリシステム.md「記録は、どこに書くか」）。
    ⚠️ 正本は帳簿（記録 MCP kiroku）。帳簿に便ごとの実行を読む口が無いので、ここはその窓を読むだけ。
    """
    paths = ([runs_path] if runs_path else
             [p for d in RUNS_DIRS for p in sorted(glob.glob(os.path.join(d, "便の実行-20??-??.tsv")))])
    last, found = {}, False
    for p in paths:
        if not os.path.exists(p):
            continue
        found = True
        with open(p, encoding="utf-8") as f:
            for line in f:
                c = line.rstrip("\n").split("\t")
                if len(c) < 3 or not c[0].strip():
                    continue
                ts, name, kekka = short_ts(c[0]), c[1].strip(), c[2].strip()
                prev = last.get(name)
                if prev is None or ts >= prev[0]:
                    last[name] = (ts, kekka)
    return {k: (v[0] + (" " + v[1] if v[1] else "")).strip() for k, v in last.items()}, found


# 便の別名に使う英語の語（小文字で始まる 4 字以上・sweep-watch・site-seo-daily など）
ALIAS_RE = re.compile(r"(?<![A-Za-z0-9_.-])[a-z][A-Za-z0-9_.-]{3,}")
PAREN_RE = re.compile(r"[（(]([^）)]*)[）)]")


def bin_aliases(schedules):
    """→ {便の id: (別名, …)}。別名＝label の括弧の中の英語の語と routine の name（会員の窓はこちらで書くことがある）。
    2 本以上の便に出る語（機体の名前 mac-studio など）は便を見分けられないので落とす"""
    raw = {}
    for s in schedules:
        # 括弧の頭に置いた英語の名前だけ（「（sweep-watch→候補置き場へ…）」「（bluelamp-chrome）」）。
        # 括弧の途中の英語（「合図 support で起きる」「Playwright 読み」）は便の名前ではないので拾わない
        words = {m.group(0).strip(".-_") for part in PAREN_RE.findall(str(s.get("label") or ""))
                 for m in [ALIAS_RE.match(part.strip())] if m}
        if s.get("name"):
            words.add(str(s["name"]).strip())
        raw[s.get("id")] = {w for w in words if len(w) >= 4}
    seen = {}
    for ws in raw.values():
        for w in ws:
            seen[w] = seen.get(w, 0) + 1
    return {k: tuple(sorted(w for w in ws if seen[w] == 1)) for k, ws in raw.items()}


def read_routine(sched_path, runs_path=None):
    """戻り: (rows, src)。rows = {時刻,便,時計,状態,最終発火,手順書,実行,paused,fail}"""
    procs = {}
    for d in PROC_DIRS:
        for p in glob.glob(os.path.join(d, "*.md")):
            b = os.path.basename(p)
            if b.startswith("_"):
                continue
            # 席の本文は {HHMM}-{便}.md で並ぶので、頭の時刻を落として便の名前で引けるようにする
            procs.setdefault(re.sub(r"^\d{4}-", "", os.path.splitext(b)[0]), p)
    runs, runs_found = read_runs(runs_path)

    def proc_for(label):
        hits = [n for n in procs if n and n in label]
        return max(hits, key=len) if hits else None

    def run_of(name, label, agent, sid, aliases=()):
        """窓の便名で引く。席は手順書の名前・予約の名前・予約 id 入りの名前（「経理の日次の便（予約 f5741ddd）」）など
        まちまちに書くので、①手順書の名前か予約の名前と同じ ②便名に予約 id が入っている ③便名（4 字以上）が予約の名前に
        入っている ④便名の英語の語が便の別名（label の括弧の中の英語名・routine の name）と同じ、の順に引き、
        当たった中で一番新しい行を返す。agent（席の名前）では引かない＝同じ席が複数の便を持つため"""
        if not runs_found:
            return "取得不能（tsv なし）"
        al = set(aliases)
        hits = [v for k, v in runs.items()
                if (k and k in (name, label)) or (sid and len(sid) >= 8 and sid in k)
                or (len(k) >= 4 and k in label) or (al and (k in al or al & set(ALIAS_RE.findall(k))))]
        return max(hits) if hits else "なし"

    schedules, src = load_schedules(sched_path)
    rows = []
    if schedules is not None:
        aliases = bin_aliases(schedules)
        for s in schedules:
            label = s.get("label") or s.get("name") or s.get("id") or ""
            fire = s["_fire"]
            ts = short_ts(fire.get("ts", "")) if fire.get("ts") else ""
            result = fire.get("result", "")
            act = fire.get("_act") or {}
            name = proc_for(label)
            ran = run_of(name, label, str(s.get("agent") or "").lstrip("@"), s.get("id") or "",
                         aliases.get(s.get("id"), ()))
            # 席が立たない便は「実行未記録」と別に数える（窓に書く物が無いのが正常）:
            # 未発火＝時計が 1 度も起こしていない／check だけ＝起こしたが check が毎回「用無し」で席が 1 度も立っていない
            idle = "" if s.get("paused") or act else ("未発火" if not fire else ("check だけ" if s.get("check") else ""))
            if idle and ran == "なし":
                ran = f"なし（{idle}）"
            rows.append({"時刻": cron_time(s.get("cron")), "便": cell(label),
                         "agent": cell(s.get("agent")) or "—", "時計": s["_clock"],
                         "状態": "**止**" if s.get("paused") else "稼働",
                         "最終発火": (ts + (" " + result if result else "")).strip() or "—",
                         "手順書": "あり" if name else "なし",
                         "実行": ran,
                         "paused": bool(s.get("paused")),
                         # 落ちた＝席が起きた最後の回が error／timeout（用無しの周で上書きされた落ちも拾う）
                         "fail": result in FAIL_RESULTS or act.get("result") in FAIL_RESULTS,
                         # 実行未記録の分母: scheduler の便で、席が 1 回でも起きた物だけ。routine は窓に書く仕組みが無いので
                         # 数えない（routine の正本は runs.log の ok／error）。1 度も起きていない便は書く物が無い
                         "未記録": (s["_clock"] == "scheduler" and not s.get("paused") and bool(act)
                                    and ran == "なし"),
                         "idle": idle})
    rows.sort(key=lambda r: (r["paused"], r["時刻"]))
    return rows, src, runs_found


# ---------- 6. エージェント（席） ----------

def read_prompt_boxes():
    """06エージェント資産/_索引-写し.md の「## 箱ごとの体数」を読む。無ければ棚を直に数える。"""
    boxes = []
    if os.path.exists(PROMPT_INDEX):
        with open(PROMPT_INDEX, encoding="utf-8") as f:
            inside = False
            for line in f:
                if line.startswith("## "):
                    inside = "箱ごとの体数" in line
                    continue
                if not inside or not line.startswith("|"):
                    continue
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                if len(c) < 2 or not c[1].isdigit():
                    continue
                boxes.append({"箱": c[0], "体数": int(c[1])})
    if not boxes and os.path.isdir(PROMPTS):
        for d in sorted(os.listdir(PROMPTS)):
            fp = os.path.join(PROMPTS, d)
            if os.path.isdir(fp) and re.match(r"^0[0-7]", d):   # 箱だけ。_便/ _孔明起動/ は数えない
                boxes.append({"箱": d,
                              "体数": len([x for x in os.listdir(fp) if x.endswith(".md")
                                          and not x.startswith("_")])})
    return boxes


def read_skill_count():
    """二軍にあるスキル（.claude/skills から降ろした物）の本数。表の行を数える。"""
    if not os.path.exists(SKILL_INDEX):
        return 0
    n = 0
    with open(SKILL_INDEX, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## "):   # 「## 追記」から先はスキルではない
                break
            if not line.startswith("|"):
                continue
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) < 3 or c[0] in ("群", "") or set(c[0]) <= {"-"}:
                continue
            n += 1
    return n


def box_names(box):
    """箱の中の体の名前（ファイル名の「（」より前）。箱が無ければ空。"""
    d = os.path.join(PROMPTS, box)
    if not os.path.isdir(d):
        return []
    out = []
    for fn in os.listdir(d):
        if not fn.endswith(".md") or fn.startswith("_"):
            continue
        stem = os.path.splitext(fn)[0]
        out.append(re.split(r"[（(]", stem)[0].strip())
        out += re.findall(r"[「『]([^」』]+)[」』]", stem)   # 「CTO」のような通称も名前に
    return [x for x in out if len(x) >= 2]


def load_monsters(path):
    """--monsters <json>（list_monsters の結果）。無ければ None＝（未取得）。"""
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("monsters", data.get("result", []))
    return data if isinstance(data, list) else None


def read_seats(schedules, monsters_path):
    """戻り: (rows, skills, foot)。行は箱ごと。席＝その箱から発火する時計の agent（routine には agent が無い）。"""
    boxes = read_prompt_boxes()
    skills = read_skill_count()
    monsters = load_monsters(monsters_path)

    # 箱 → その箱に居る体の名前
    names = {b["箱"]: box_names(b["箱"]) for b in boxes}

    # 時計の席（agent）を箱へ結ぶ
    seat_box, loose_seats = {}, []
    for sc in (schedules or []):
        agent = str(sc.get("agent") or "").lstrip("@").strip()
        if not agent:
            continue
        hit = None
        for box, ns in names.items():
            for n in ns:
                if n and (n in agent or agent in n):
                    hit = box
                    break
            if hit:
                break
        ts = (sc.get("_fire") or {}).get("ts", "")
        ts = short_ts(ts) if ts else ""
        if hit:
            seat_box.setdefault(hit, {"seats": set(), "fire": ""})
            seat_box[hit]["seats"].add("@" + agent)
            if ts > seat_box[hit]["fire"]:
                seat_box[hit]["fire"] = ts
        else:
            loose_seats.append("@" + agent + ("（" + ts + "）" if ts else ""))

    # 稼働中の monster を箱へ結ぶ（task_head と workdir の文字合わせ。名前を返す口が無いため）
    mon_box, loose_mon = {}, []
    for m in (monsters or []):
        blob = (m.get("task_head", "") or "") + " " + (m.get("workdir", "") or "")
        hit = None
        for box, ns in names.items():
            for n in ns:
                if n and len(n) >= 3 and n in blob:
                    hit = box
                    break
            if hit:
                break
        rec = {"cwd": m.get("workdir", "") or "—", "id": m.get("short_id", "")}
        if hit:
            mon_box.setdefault(hit, []).append(rec)
        else:
            loose_mon.append(rec)

    rows = []
    for b in boxes:
        box = b["箱"]
        sb = seat_box.get(box, {})
        mb = mon_box.get(box, [])
        rows.append({"席": "・".join(sorted(sb.get("seats", []))) or "—",
                     "箱": box, "体数": b["体数"],
                     "稼働中": ("（未取得）" if monsters is None else str(len(mb))),
                     "cwd": " / ".join(sorted({x["cwd"] for x in mb})) or "—",
                     "最終発火": sb.get("fire") or "—"})
    if skills:
        rows.append({"席": "—", "箱": "スキル（未登録）", "体数": skills,
                     "稼働中": "—", "cwd": "—",
                     "最終発火": "— （`.claude/skills/` の形をやめた物・呼べない）"})

    foot = []
    if monsters is None:
        foot.append("- 稼働中: （未取得）。`--monsters <json>`（list_monsters の結果）を渡すと埋まる")
    else:
        foot.append(f"- 稼働中の monster: {len(monsters)} 体"
                    + ("／箱に結べない: " + " / ".join(f"{x['id']} {x['cwd']}" for x in loose_mon)
                       if loose_mon else ""))
    if loose_seats:
        foot.append("- 箱に結べない時計の席: " + " / ".join(sorted(set(loose_seats))))
    return rows, skills, foot


# ---------- 7. 完了（30 日） ----------

def read_done(closed_boxes=()):
    """1 枚の墓標（09アーカイブ/案件/*.md）＋フォルダのまま閉じた箱（read_graves の closed）の 30 日。
    1 枚の墓標の閉じた日: 見出しの（開始 → 終了）→ frontmatter の updated → 本文の「主君裁定 YYYY-MM-DD」→ 名前の日付（印を付ける）"""
    out = []
    for r in closed_boxes:
        age = days_since(r["closed"])
        if age is not None and age <= DONE_DAYS:
            out.append({"closed": r["closed"], "title": r["title"], "absorb": r["absorb"], "grave": r["grave"]})
    for p in sorted(glob.glob(os.path.join(GRAVES, "*.md"))):
        with open(p, encoding="utf-8") as f:
            text = f.read()
        fm = kiroku.parse_frontmatter(text) or {}
        m = re.search(r"^#\s*(.+?)（(\d{4}-\d{2}-\d{2})\s*→\s*(\d{4}-\d{2}-\d{2})）", text, re.M)
        upd = (fm.get("updated") or "").strip()
        if m:
            title, closed = m.group(1), m.group(3)
        else:
            m2 = re.search(r"^#\s*(.+)$", text, re.M)
            title = fm.get("title") or (m2.group(1) if m2 else os.path.basename(p))
            m3 = re.search(r"主君裁定\s*(\d{4}-\d{2}-\d{2})", text)
            if re.match(r"^\d{4}-\d{2}-\d{2}$", upd):
                closed = upd
            elif m3:
                closed = m3.group(1)
            else:
                closed = name_date(os.path.basename(p))
                if closed:
                    title += "（閉じた日が読めない・名前の日付）"
        age = days_since(closed)
        if age is None or age > DONE_DAYS:
            continue
        absorb = "—"
        sec = re.search(r"##\s*成果はどこへ行ったか(.*?)(?=\n##\s|\Z)", text, re.S)
        if sec:
            for line in sec.group(1).splitlines():
                if not line.startswith("|"):
                    continue
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                if len(c) >= 2 and c[0] not in ("物", "") and not set(c[0]) <= {"-"}:
                    absorb = c[1]
                    break
        if absorb == "—" and fm.get("absorb"):
            absorb = fm["absorb"]
        out.append({"closed": closed, "title": title, "absorb": absorb,
                    "grave": os.path.relpath(p, HONJIN)})
    out.sort(key=lambda r: r["closed"], reverse=True)
    return out


# ---------- 8. 棚の差分 ----------

def has_pre_commit(shelf):
    """その棚で pre-commit の門が効くか。core.hooksPath が指していれば <棚>/<hooksPath>/pre-commit、
    指していなければ git の hooks（作業木でも正しい道＝rev-parse --git-path）。在って実行可なら True"""
    import subprocess

    def git(*a):
        try:
            r = subprocess.run(["git", "-C", shelf, *a], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    hp = git("config", "core.hooksPath")
    if hp:
        hp = os.path.expanduser(hp)
        fp = os.path.join(hp if os.path.isabs(hp) else os.path.join(shelf, hp), "pre-commit")
    else:
        gp = git("rev-parse", "--git-path", "hooks/pre-commit")
        fp = (gp if os.path.isabs(gp) else os.path.join(shelf, gp)) if gp else \
            os.path.join(shelf, ".git", "hooks", "pre-commit")
    return os.path.isfile(fp) and os.access(fp, os.X_OK)


def read_shelf(no_status):
    big = []
    for base in (PROJ, APPROVE):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ("一時ファイル", ".git")]
            for fn in filenames:
                if fn.lower().endswith(MEDIA):
                    fp = os.path.join(dirpath, fn)
                    try:
                        if os.path.getsize(fp) > BIG_BYTES:
                            big.append(os.path.relpath(fp, ROOT))
                    except OSError:
                        pass
    for fn in os.listdir(ROOT):
        fp = os.path.join(ROOT, fn)
        if os.path.isfile(fp) and fn.lower().endswith(MEDIA):
            try:
                if os.path.getsize(fp) > BIG_BYTES:
                    big.append(fn)
            except OSError:
                pass
    return {"no_status": len(no_status), "big": len(big), "big_list": big[:5],
            "hook": all(has_pre_commit(d) for d in dict.fromkeys(
                os.path.realpath(p) for p in (ROOT, HONJIN))),
            "approve": os.path.isdir(APPROVE),
            "tmp": os.path.isdir(os.path.join(ROOT, "11一時ファイル"))}


# ---------- 組み立て ----------

def table(header, rows):
    """行が無ければヘッダも出さず「（なし）」1 行（型の正本＝この道具の頭の docstring）。"""
    if not rows:
        return ["（なし）"]
    sep = "|" + "---|" * (header.count("|") - 1)
    return [header, sep] + rows


# ⏳ 金庫の鍵の期限（全体像の期限の節）。入力は password-manager の list_secrets の出力（文字のまま）＝1 項目 1 行
#    `• <名前> (<username>) 🔗<url> — <説明> [by <作った人>, <日付>]`。名前は最初の区切りまで、期限は行のどこかの「期限 YYYY-MM-DD」。
VAULT_HEAD = "保存済みシークレット"
VAULT_EMPTY = "保存済みのシークレットはありません"
KIGEN_RE = re.compile(r"期限\s*[:：]?\s*(\d{4}-\d{1,2}-\d{1,2})")
KIGEN_WARN_DAYS = 14


def _vault_name(line):
    s = line[1:].strip()
    cut = [i for i in (s.find(" ("), s.find(" 🔗"), s.find(" — "), s.find(" [by ")) if i > 0]
    return s[:min(cut)] if cut else s


def read_vault(path, today=None):
    """→ (rows|None, 理由・件数の文)。rows=[{名前, 期限, 残り, 印}] 期限の近い順。None は取得不能（理由つき）。"""
    if not path:
        return None, "金庫の一覧が渡されていない（`list_secrets` の出力をファイルに保存して `--vault <ファイル>` で渡す）"
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return None, f"金庫の一覧を読めない（{type(e).__name__}: {e.strerror or e}）"
    items = [ln for ln in text.splitlines() if ln.lstrip().startswith("•")]
    if VAULT_HEAD not in text and VAULT_EMPTY not in text:
        return None, "渡されたファイルが `list_secrets` の出力の形でない（見出し「📦 保存済みシークレット」が無い）"
    today = today or dt.date.today()
    rows = []
    for ln in items:
        m = KIGEN_RE.search(ln)
        if not m:
            continue
        name = _vault_name(ln.strip())
        try:
            d = dt.date.fromisoformat("-".join(f"{int(x):02d}" for x in m.group(1).split("-")))
        except ValueError:
            rows.append({"名前": name, "期限": m.group(1), "残り": "日付が読めない", "印": "🔴", "_k": dt.date.min}); continue
        left = (d - today).days
        rest = f"あと {left} 日" if left > 0 else ("今日まで" if left == 0 else f"{-left} 日前に切れた")
        rows.append({"名前": name, "期限": d.isoformat(), "残り": rest, "印": "🔴" if left <= KIGEN_WARN_DAYS else "", "_k": d})
    rows.sort(key=lambda r: r["_k"])
    return rows, f"金庫 {len(items)} 件のうち期限の書かれた項目 {len(rows)} 件"


def vault_section(vault_path=None, today=None):
    """期限の節の行（見出しから）。一覧なしは「取得不能」1 行（⛔ 0 件や「（なし）」と書かない）。"""
    rows, why = read_vault(vault_path, today)
    L = ["", "## 9. 期限（金庫の鍵）", "",
         f"> 金庫の各項目の説明に `期限 YYYY-MM-DD` と書いた物だけを近い順に出す。🔴 は残り {KIGEN_WARN_DAYS} 日以内か切れた物。"
         "期限の正本は金庫の説明（⛔ 写しを作らない）。出すのは項目名と期限だけ。", ""]
    if rows is None:
        return L + [f"取得不能（{why}）"]
    if not rows:
        return L + [f"期限の書かれた項目は無い（{why}）"]
    return L + [f"（{why}）", "", "| 印 | 項目 | 期限 | 残り |", "|---|---|---|---|"] + \
        [f"| {r['印']} | {cell(r['名前'], 60)} | {r['期限']} | {r['残り']} |" for r in rows]


def build(args):
    """→ (lines, stderr 用の数字)"""
    projects, no_status = read_projects()
    closed_boxes, frozen, unreadable = read_graves()
    items, koumei, sent_back = read_council(projects)
    levers = read_levers(projects)
    untils = read_untils(projects)
    resumes = read_resumes()
    routine, sched_src, runs_found = read_routine(args.schedules, getattr(args, "runs", None))
    scheds, _ = load_schedules(args.schedules)
    seats, skills, seats_foot = read_seats(scheds, args.monsters)
    done = read_done(closed_boxes)
    shelf = read_shelf(no_status)

    n = {s: sum(1 for r in projects if r["state"] == s) for s in list(STATES) + ["語彙外", "状態なし"]}
    longest = max([r["age"] for r in items] or [0])
    fail = sum(1 for r in routine if r["fail"])
    # 窓の最後の行が 失敗＝席は走り切ったが自分で 失敗 と閉じた（時計の fail とは別の数）
    runfail = sum(1 for r in routine if not r["paused"] and str(r["実行"]).endswith("失敗"))
    norun = (sum(1 for r in routine if r["未記録"])
             if runs_found else "取得不能（窓の tsv なし）")
    # 席が立たない便（実行未記録には数えない・別の欄）
    chk_only = sum(1 for r in routine if r["idle"] == "check だけ")
    nofire = sum(1 for r in routine if r["idle"] == "未発火")
    seat_total = sum(r["体数"] for r in seats if r["箱"] != "スキル（未登録）")
    seat_run = ("未取得" if any(r["稼働中"] == "（未取得）" for r in seats)
                else sum(int(r["稼働中"]) for r in seats if str(r["稼働中"]).isdigit()))
    late = sum(1 for r in untils if r["late"])

    L = [f"<!-- 生成: scripts/build_scope_progress.py／{dt.datetime.now():%Y-%m-%d %H:%M}"
         "／手で編集しない。直すなら元（status.md・00朝廷/・時計の控え・墓標）を直す -->",
         f"# 全体像 — {dt.date.today():%Y-%m-%d}",
         "",
         f"数字: 箱 {len(projects)}（" + "・".join(f"{s} {n[s]}" for s in STATES if n[s]) 
         + f"・語彙外 {n['語彙外']}・状態なし {n['状態なし']}）／凍結 {len(frozen)}"
         f"／閉じた箱 {len(closed_boxes)}（" + "・".join(f"{s} {sum(1 for r in closed_boxes if r['state'] == s)}" for s in CLOSED_STATES)
         + f"）／墓標が読めない {len(unreadable)}"
         f"／裁定待ち {len(items)} 件（最長 {longest} 日・差し戻し {len(sent_back)}）"
         f"／主君の手 {len(levers)}／待ち受け {len(untils)}（🔴 {late}）／再開の合図 {len(resumes)}"
         f"／便 {len(routine)} 本（fail {fail}・窓の最後が失敗 {runfail}・実行未記録 {norun}＝席が起きた scheduler の便で窓に無い物"
         f"・席が立たない便 check だけ {chk_only}・未発火 {nofire}）"
         f"／席 {seat_total} 体（稼働 {seat_run}）／完了 {len(done)}（{DONE_DAYS} 日）",
         "",
         "## 1. プロジェクト（08プロジェクト/ の箱・state 別）", ""]

    def box_rows(rs):
        return [f"| {cell(r['name'])} | {cell(r['owner']) or '?'} | {kiroku.dare_of(r.get('手番')) or '—'} | "
                f"{cell(r['next'], 90) or '—'} | {md(r['updated'])} |" for r in rs]

    for st in STATE_SECTIONS:
        rs = [r for r in projects if r["state"] == st]
        L += [f"### {st}（{len(rs)}）", ""]
        L += table("| 箱 | owner | 手番 | next | updated |", box_rows(rs))
        L.append("")
    for st in ("吸収済",):
        rs = [r for r in projects if r["state"] == st]
        if rs:
            L += [f"### {st}（{len(rs)}）", ""] + table("| 箱 | owner | 手番 | next | updated |", box_rows(rs)) + [""]
    bad = [r for r in projects if r["state"] in ("語彙外", "状態なし")]
    L += [f"### 赤（{len(bad) + len(unreadable)}・直すのは owner）", ""]
    L += table("| 何 | 箱 | 直し方 |",
               [f"| **{'状態なし' if r['state'] == '状態なし' else '語彙外: ' + cell(r.get('raw_state'))}** | "
                f"{cell(r['name'])} | "
                f"{'status.md を kiroku.py box で作る' if r['state'] == '状態なし' else 'state を語彙（' + '｜'.join(STATES) + '）に直す'} |"
                for r in bad]
               + [f"| **墓標が読めない: {cell(r['raw_state']) or '（state が空）'}** | 09アーカイブ/案件/{cell(r['name'])} | "
                  f"status.md の state を {'｜'.join(CLOSED_STATES)}（閉じた）か {'｜'.join(FROZEN_STATES[:2])}（凍結）に直す |"
                  for r in unreadable])
    L += ["", f"閉じた箱（09アーカイブ/案件/ のフォルダ・state {'｜'.join(CLOSED_STATES)}）: {len(closed_boxes)}"
              "（30 日以内は §7）"]
    L += ["", f"凍結（09アーカイブ/案件/ の箱・再点火は主君）: " + ("・".join(frozen) if frozen else "（なし）")]

    L += ["", "## 2. 裁定表（00朝廷/ と箱の 手番＝主君・番号で返す）", ""]
    L += table("| # | 席 | 問い | 推奨 | 期限 | 決めないと |",
               [f"| {CIRCLED[i] if i < len(CIRCLED) else '(' + str(i + 1) + ')'} | "
                f"{cell(r['seat'], 20)}{r['note']} | {cell(r['q'], 70)} | "
                f"{cell(r['rec'], 40) or '—'} | {md(r['due'])} | {cell(r['cost'], 40) or '—'} |"
                for i, r in enumerate(items)])
    L += ["", f"（差し戻し: {len(sent_back)} 件）", ""]
    L += [f"- **差し戻し**: {cell(s, 20)}｜{cell(w, 50)}｜理由＝{why}" for s, w, why in sent_back] or ["- 差し戻し: （なし）"]
    L += ["", f"### 孔明が裁く（00朝廷/ のうけつけ・手番＝孔明）（{len(koumei)}）", ""]
    L += table("| 席 | 問い | 推奨 |",
               [f"| {cell(r['seat'], 20)} | {cell(r['q'], 70)} | {cell(r['rec'], 40) or '—'} |" for r in koumei])

    L += ["", "## 3. 主君の手（手番＝主君 の箱のうち、体を動かす頼み）", ""]
    L += table("| 箱 | 何を | 🔬 実測 |",
               [f"| {cell(r['name'])} | {cell(r['what'], 100)} | {cell(r['k'], 80)} |" for r in levers])

    L += ["", "## 4. 待ち受け（手番 が 主君 以外の箱・🔴＝期待日を過ぎた）", ""]
    L += table("| 箱 | 誰が | 何を | 期待日 |",
               [f"| {cell(r['name'])} | {cell(r['who'])} | {cell(r['what'], 80)} | "
                f"{'🔴 ' if r['late'] else ''}{cell(r['when'])} |" for r in untils])
    L += ["", "### 再開の合図（09アーカイブ/案件/ の閉じた箱・resume が非空。来ていたら箱を 08プロジェクト/ へ戻す）", ""]
    L += table("| 箱 | 何を | 誰から | どこで拾う |",
               [f"| {cell(r['name'])} | {cell(r['what'], 80)} | {cell(r['who'], 40)} | {cell(r['where'], 60)} |"
                for r in resumes])

    L += ["", "## 5. Routine（この機体の時計）", ""]
    L += table("| 時刻 | 便 | agent | 時計 | 状態 | 最終発火 | 手順書 | 実行 |",
               [f"| {r['時刻']} | {cell(r['便'], 60)} | {cell(r.get('agent'), 20) or '—'} | "
                f"{r['時計']} | {r['状態']} | "
                f"{r['最終発火']} | {r['手順書']} | {r['実行']} |" for r in routine])
    L += ["", "- **この機体の時計の控えだけを読む**（routine の `~/.claude/routine/routines.json`・皆伝の機体なら scheduler の `~/.claude/scheduler/schedules.json` も）。"
          "別の機体で回している便はここに出ない"]
    L += ["- **最終発火**＝時計が起こしたか（routine は `~/.claude/routine/runs.log`・scheduler は `~/.claude/scheduler/fires.log`）。**実行**＝その便が走り終わったと"
          "帳簿（記録 MCP `kiroku` の `run_start`／`run_end`）に残したか。**起こした ≠ 走り切った**ので 2 列ある",
          "- 実行の出所は `11一時ファイル/便の実行-YYYY-MM.tsv`（便が `run_end` と同時に置く窓・中の OS と本陣の 2 か所を読む）。"
          "**正本は帳簿**＝手が要った率は `stocktake` で数える。書き方は `.claude/rules/メモリシステム.md`「記録は、どこに書くか」",
          "- 実行の列は窓の便名を、手順書の名前・予約の名前・予約 id・label の括弧の中の英語名・routine の name で引く。"
          "**なし（check だけ）**＝check が毎回「用無し」で席が 1 度も立っていない便、**なし（未発火）**＝時計がまだ 1 度も起こしていない便"
          "＝どちらも窓に書く物が無いのが正常なので、実行未記録には数えない"]
    if not runs_found:
        L += ["- ⚠️ **取得不能**: 窓の tsv が 1 枚も無い（まだどの便も置いていないか、消された）。"
              "⛔ これは「走っていない」ではない。帳簿を `stocktake` で引く"]

    L += ["", "## 6. エージェント（席）", ""]
    L += table("| 席 | 箱 | 体数 | 稼働中 | cwd | 最終発火 |",
               [f"| {cell(r['席'], 60)} | {r['箱']} | {r['体数']} | {r['稼働中']} | "
                f"{cell(r['cwd'], 60)} | {r['最終発火']} |" for r in seats])
    L += [""] + seats_foot
    L += ["", "（正本: BlueLamp の DB。写しは 06エージェント資産/<箱>/ ＝ git に載る）"]

    L += ["", f"## 7. 完了（{DONE_DAYS} 日・墓標から）", ""]
    L += table("| 閉じた日 | プロジェクト | absorb 先 | 墓標 |",
               [f"| {md(r['closed'])} | {cell(r['title'], 50)} | {cell(r['absorb'], 60)} | "
                f"{cell(r['grave'])} |" for r in done])

    L += ["", "## 8. 棚の差分（§1 の手 1）", "",
          f"status.md 無し {shelf['no_status']}／語彙外 {n['語彙外']}／`一時ファイル` の外の実体（5 MB 超）{shelf['big']}"
          f"／pre-commit {'あり' if shelf['hook'] else '**なし**'}"
          f"／00朝廷 {'あり' if shelf['approve'] else '**なし**'}"
          f"／11一時ファイル {'あり' if shelf['tmp'] else '**なし**'}"]
    if shelf["big_list"]:
        L += ["", "- 実体: " + " / ".join(shelf["big_list"])]
    L += vault_section(getattr(args, "vault", None))
    L.append("")
    summary = (f"箱 {len(projects)}（状態なし {n['状態なし']}・語彙外 {n['語彙外']}・凍結 {len(frozen)}"
               f"・閉じた箱 {len(closed_boxes)}・墓標が読めない {len(unreadable)}）"
               f" / 裁定 {len(items)} / 差し戻し {len(sent_back)} / 主君の手 {len(levers)} / 待ち受け {len(untils)}（🔴 {late}）"
               f" / 便 {len(routine)}（fail {fail}・窓の失敗 {runfail}・実行未記録 {norun}・check だけ {chk_only}・未発火 {nofire}・src {sched_src}）"
               f" / 席 {seat_total}（稼働 {seat_run}・スキル {skills}）"
               f" / 完了 {len(done)}")
    return L, summary


def box_sections(lines):
    """箱から作る節（プロジェクト〜待ち受けの 4 節）だけを取り出す（--check の比較用。生成時刻の行は除く）。"""
    out, inside = [], False
    for l in lines:
        if l.startswith("## 1. "):
            inside = True
        if l.startswith("## 5. "):
            break
        if inside:
            out.append(l)
    return out


def cmd_check(args):
    """自己一致: ①語彙 ②全箱 ③プロジェクト〜待ち受けの 4 節が今の SCOPE_PROGRESS.md と一致"""
    rc = 0
    if tuple(STATE_ORDER[s] for s in STATES) != tuple(range(len(STATES))):
        print("❌ 語彙: 生成器の STATE_ORDER が kiroku.STATES と食い違う"); rc = 1
    else:
        print(f"✅ 語彙: kiroku.STATES {len(STATES)} 語と一致")
    boxes = [d for d in sorted(glob.glob(os.path.join(PROJ, "*"))) if os.path.isdir(d)]
    ng = [b for b in boxes if not os.path.exists(os.path.join(b, "status.md")) or not kiroku.check_one(os.path.join(b, "status.md"))[0]]
    if ng:
        print(f"❌ 箱: {len(ng)}/{len(boxes)} が kiroku --check を通らない（" + "・".join(os.path.basename(b) for b in ng[:5]) + ("…" if len(ng) > 5 else "") + "）"); rc = 1
    else:
        print(f"✅ 箱: {len(boxes)}/{len(boxes)} が kiroku --check を通る")
    lines, _ = build(args)
    if not os.path.exists(args.out):
        print(f"❌ {os.path.relpath(args.out, HONJIN)} が無い（生成が要る）"); return 1
    now = open(args.out, encoding="utf-8").read().splitlines()
    if box_sections(lines) != box_sections(now):
        print(f"❌ 一致しない: 箱から作る節（プロジェクト〜待ち受けの 4 節）が {os.path.relpath(args.out, HONJIN)} と違う（生成し直しが要る）"); rc = 1
    else:
        print(f"✅ 一致: 箱から作る節（プロジェクト〜待ち受けの 4 節）が {os.path.relpath(args.out, HONJIN)} と同じ")
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedules", help="時計の控えの代わりに読む 1 本（routine の routines.json か scheduler の schedules.json）")
    ap.add_argument("--monsters", help="monster の一覧 JSON（list_monsters の結果）。無ければ「（未取得）」")
    ap.add_argument("--runs", help="便の実行の窓 tsv（既定: 11一時ファイル/便の実行-YYYY-MM.tsv を全部）")
    ap.add_argument("--vault", help="password-manager の list_secrets の出力を保存したファイル（任意・無ければ期限の節は「取得不能」）")
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--check", action="store_true", help="自己一致（語彙・全箱・プロジェクト〜待ち受けの 4 節の一致）。exit 0/1・書かない")
    args = ap.parse_args()
    if args.check:
        sys.exit(cmd_check(args))
    L, summary = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote {args.out}: {summary}", file=sys.stderr)


if __name__ == "__main__":
    main()
