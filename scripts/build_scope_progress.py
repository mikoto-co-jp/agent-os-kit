#!/usr/bin/env python3
"""docs/SCOPE_PROGRESS.md の生成器（8 節固定）。読むのは元だけ、書くのは 1 枚。手で編集しない。

型の正本はこの docstring（旧 影分身/分身.md §3-1 は 2026-09-15 に退役）。節の順は固定。空の節は「（なし）」1 行。
語彙表（箱の state・鍵）は scripts/kiroku.py から import する（主君裁定 2026-09-18・帳簿 id=440）。
  1. プロジェクト     08プロジェクト/*/status.md を state 別（起案／裁定待ち／実行中／外部待ち／確認待ち／完了）の表＝箱｜owner｜next｜updated。
                      status.md の無い箱・語彙外の state は赤。09アーカイブ/案件/ の凍結箱は末尾に一覧
  2. 裁定表           00廷議/*.md（7 項目）の全数 ＋ 各箱の ask（問い｜選択肢｜推奨｜決めないと）。束ねない。推奨なしは差し戻し
  3. 主君の手         lever が非空の箱＝箱｜何を｜何秒｜閉じると何が動くか
  4. 待ち受け         until が非空の箱＝箱｜何を｜誰から｜期待日（今日を過ぎていれば 🔴）
                      ＋ 再開の合図＝09アーカイブ/案件/ の箱で resume が非空（投げ終わった箱。廷議が毎朝 1 件ずつ引く・帳簿 id=475）
  5. Routine          scheduler の正本 ~/.claude/scheduler/schedules.json（--schedules <json> で差し替え可）。agent 列＝その便を走らせる席。
                      「実行」列＝その便が帳簿（記録 MCP kiroku の run_start／run_end）に走った記録を残したか。
                      ⚠️ Python から口は撃てる（scripts/mcplib.py・2026-09-20 実測）が、**帳簿に便ごとの実行を読む口が無い**。
                      全便が同じ席名 `scheduler` で書く決まりなので `run_last` は席単位でしか引けない（⇒ 便ごとに分けられない）。
                      ⇒ 便が run_end と同時に置く 11一時ファイル/便の実行-YYYY-MM.tsv を読む（--runs で差し替え可）。
                      口の不足は 00廷議/2026-09-20-棚-道具が時計と帳簿に自分で聞けない.md で起票済み。
                      正本は帳簿・この tsv は 7 日で消える窓。tsv が無ければ全便「取得不能（tsv なし）」と出す（0 件とは書かない）
  6. エージェント（席） 06エージェント資産/_索引-写し.md の箱ごとの体数 ＋ --monsters <json>（list_monsters の結果）
  7. 完了（30 日）    09アーカイブ/案件/*.md の墓標
  8. 棚の差分         数だけ（08プロジェクト・00廷議・一段目のみ。深い走査はしない）

--check: 自己一致。①生成器の語彙が kiroku.STATES と同じ ②08プロジェクト/ の全箱が kiroku --check を通る
        ③箱から作る節（1〜4）を今の docs/SCOPE_PROGRESS.md と比べて一致（生成し直しが要るなら exit 1）

退役した生成器をここへ畳んだ（2026-09-14）:
  build_council.py  → §2（書式判定 問い｜選択肢｜推奨｜決めないと・差し戻し）。docs/裁定会.md は廃止
  build_schedules.py → §5（scheduler を直読み）。docs/定期便.md は廃止
「条件待ち」の節は 2026-09-18 に §4 待ち受け（until）へ替えた。「廃止候補」の節は 2026-09-14 に型から外した。

ROOT は環境変数 MIKOTO_OS_ROOT か、このファイルの 2 つ上（scripts/ の親）。
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kiroku  # 語彙表の正本（STATES・BOX_KEYS・parse_frontmatter・check_one）

ROOT = os.environ.get("MIKOTO_OS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
OUT_DEFAULT = os.path.join(ROOT, "docs", "SCOPE_PROGRESS.md")
SCHED_DIR = os.environ.get("SCHEDULER_DIR") or os.path.expanduser("~/.claude/scheduler")
PROJ = os.path.join(ROOT, "08プロジェクト")
APPROVE = os.path.join(ROOT, "00廷議")
GRAVES = os.path.join(ROOT, "09アーカイブ", "案件")
PROCS = os.path.join(ROOT, "docs", "定期便-手順")
RUNS = os.path.join(ROOT, "11一時ファイル")   # 便が run_end と同時に置く tsv（7 日で消える窓。正本は帳簿）
PROMPTS = os.path.join(ROOT, "06エージェント資産")
PROMPT_INDEX = os.path.join(PROMPTS, "_索引-写し.md")   # ⛔ 人が書く _索引.md ではない
SKILL_INDEX = os.path.join(PROMPTS, "06二軍エージェント", "_索引-スキル.md")
DONE_DAYS = 30
BIG_BYTES = 5 * 1024 * 1024
MEDIA = (".mp4", ".mov", ".pdf", ".png", ".jpg", ".jpeg", ".zip")
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

# 箱の state は kiroku.STATES（8 語）。生成器はこの並びで §1 の表を出す。語彙外・status.md 無しは赤
STATES = kiroku.STATES
STATE_SECTIONS = ("起案", "裁定待ち", "実行中", "外部待ち", "確認待ち", "完了")   # §1 に必ず出す 6 つ
STATE_ORDER = {s: i for i, s in enumerate(STATES)}
STATE_ORDER.update({"語彙外": 90, "状態なし": 91, "凍結": 92})


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
    """rows: state / name / owner / next / due / updated / ask / lever / until / bad（赤）"""
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
                         "ask": "", "lever": "", "until": "", "bad": True})
            continue
        fm = kiroku.parse_frontmatter(open(sp, encoding="utf-8").read()) or {}
        st = fm.get("state", "").strip()
        bad = st not in STATES
        rows.append({"state": st if not bad else "語彙外", "raw_state": st, "name": name,
                     "owner": fm.get("owner", ""), "next": fm.get("next", ""),
                     "due": fm.get("due", ""), "updated": fm.get("updated", ""),
                     "ask": fm.get("ask", ""), "lever": fm.get("lever", ""), "until": fm.get("until", ""),
                     "path": sp, "bad": bad})
    frozen = []
    for d in sorted(glob.glob(os.path.join(GRAVES, "*"))):
        if os.path.isdir(d):
            frozen.append(os.path.basename(d))
    rows.sort(key=lambda r: (STATE_ORDER.get(r["state"], 89), r["due"] or "9999", r["name"]))
    return rows, no_status, frozen


def split3(v):
    parts = [p.strip() for p in cell(v).split("｜")]
    while len(parts) < 3:
        parts.append("")
    return parts[:3]


# ---------- 2. 裁定表 ----------

def read_council(projects):
    """00廷議/*.md（正） ＋ 各箱の ask。推奨なしは表に入れず差し戻し。"""
    items, sent_back, waiting = [], [], []

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
        if fm.get("until") or "until:" in fm.get("期限", ""):
            waiting.append(row)
        else:
            items.append(row)

    # 各箱の ask（主君裁定 2026-09-18: 00廷議 ＋ 箱の ask の両方を載せる）
    for r in projects:
        if not has_ask(r.get("ask")):
            continue
        q, opts, rec, cost = split_ask(r["ask"])
        seat = cell(r.get("owner")) or "?"
        age = days_since(r.get("updated")) or 0
        row = {"seat": seat, "q": q, "opts": opts, "rec": rec, "due": r.get("due", ""),
               "cost": cost, "age": age, "note": "（箱）", "key": r["name"]}
        if rec and opts:
            items.append(row)
        else:
            sent_back.append((seat, r["name"] + "（箱の ask）", "推奨なし" if not rec else "選択肢なし"))

    # 全数を出す（束ねない・2026-09-14 主君 GO）。並びは期限が近い順 → 古い順
    items.sort(key=lambda r: (r["due"] or "9999", -r["age"]))
    return items, waiting, sent_back


# ---------- 3. 主君の手（lever）／ 4. 待ち受け（until） ----------

def read_levers(projects):
    out = []
    for r in projects:
        if not cell(r.get("lever")):
            continue
        what, sec, opens = split3(r["lever"])
        out.append({"name": r["name"], "what": what, "sec": sec, "opens": opens})
    return out


def read_untils(projects):
    out = []
    today = dt.date.today()
    for r in projects:
        if not cell(r.get("until")):
            continue
        what, who, when = split3(r["until"])
        late = False
        try:
            late = dt.date.fromisoformat(when) < today
        except ValueError:
            pass
        out.append({"name": r["name"], "what": what, "who": who, "when": when, "late": late})
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


def load_schedules(path):
    """scheduler の正本だけを読む（2026-09-14: docs/定期便.md は退役・写しから読まない）。"""
    src = path or os.path.join(SCHED_DIR, "schedules.json")
    if not os.path.exists(src):
        return None, src
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("schedules", data.get("result", data))
    if not isinstance(data, list):
        return None, src
    return data, src


def read_runs(runs_path):
    """便が run_end と同時に置く tsv を読む。戻り: (最後の実行 {便名: "MM-DD HH:MM 結果"}, tsv が 1 枚でも在ったか)。

    列: 開始ISO<TAB>便名<TAB>結果<TAB>実行id<TAB>中身（書式は docs/定期便-手順/_実行を帳簿へ書く.md）。
    ⚠️ 正本は帳簿（記録 MCP kiroku）。帳簿に便ごとの実行を読む口が無いので、ここはその窓を読むだけ。
    """
    paths = ([runs_path] if runs_path else sorted(glob.glob(os.path.join(RUNS, "便の実行-20??-??.tsv"))))
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
                ts, name, kekka = c[0].strip(), c[1].strip(), c[2].strip()
                try:
                    ts = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%m-%d %H:%M")
                except ValueError:
                    pass
                prev = last.get(name)
                if prev is None or ts >= prev[0]:
                    last[name] = (ts, kekka)
    return {k: (v[0] + (" " + v[1] if v[1] else "")).strip() for k, v in last.items()}, found


def read_routine(sched_path, runs_path=None):
    """戻り: (rows, src)。rows = {時刻,便,機体,状態,最終発火,手順書,実行,paused,fail}"""
    procs = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(os.path.join(PROCS, "*.md"))
             if not os.path.basename(p).startswith("_")}
    runs, runs_found = read_runs(runs_path)

    def proc_for(label):
        hits = [n for n in procs if n and n in label]
        return max(hits, key=len) if hits else None

    def run_of(name, label):
        if not runs_found:
            return "取得不能（tsv なし）"
        for k in (name, label):
            if k and k in runs:
                return runs[k]
        return "なし"

    schedules, src = load_schedules(sched_path)
    rows = []
    if schedules is not None:
        last = {}
        fires = os.path.join(SCHED_DIR, "fires.log")
        if os.path.exists(fires):
            with open(fires, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    last[r.get("schedule_id")] = r
        for s in schedules:
            label = s.get("label") or s.get("id") or ""
            fire = last.get(s.get("id"), {})
            ts = fire.get("ts", "")
            try:
                ts = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%m-%d %H:%M")
            except ValueError:
                pass
            result = fire.get("result", "")
            name = proc_for(label)
            rows.append({"時刻": cron_time(s.get("cron")), "便": cell(label),
                         "agent": cell(s.get("agent")) or "—", "機体": "B",
                         "状態": "**止**" if s.get("paused") else "稼働",
                         "最終発火": (ts + (" " + result if result else "")).strip() or "—",
                         "手順書": "あり" if name else "なし",
                         "実行": run_of(name, label),
                         "paused": bool(s.get("paused")),
                         "fail": result not in ("", "spawned", "ok")})
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
    """戻り: (rows, skills, foot)。行は箱ごと。席＝その箱から発火する scheduler の agent。"""
    boxes = read_prompt_boxes()
    skills = read_skill_count()
    monsters = load_monsters(monsters_path)

    # 箱 → その箱に居る体の名前
    names = {b["箱"]: box_names(b["箱"]) for b in boxes}

    # scheduler の席（agent）を箱へ結ぶ
    last = {}
    fires = os.path.join(SCHED_DIR, "fires.log")
    if os.path.exists(fires):
        with open(fires, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                last[r.get("schedule_id")] = r
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
        ts = (last.get(sc.get("id")) or {}).get("ts", "")
        try:
            ts = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%m-%d %H:%M")
        except ValueError:
            pass
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
        foot.append("- 箱に結べない scheduler の席: " + " / ".join(sorted(set(loose_seats))))
    return rows, skills, foot


# ---------- 7. 完了（30 日） ----------

def read_done():
    out = []
    for p in sorted(glob.glob(os.path.join(GRAVES, "*.md"))):
        with open(p, encoding="utf-8") as f:
            text = f.read()
        m = re.search(r"^#\s*(.+?)（(\d{4}-\d{2}-\d{2})\s*→\s*(\d{4}-\d{2}-\d{2})）", text, re.M)
        if m:
            title, closed = m.group(1), m.group(3)
        else:
            m2 = re.search(r"^#\s*(.+)$", text, re.M)
            title = m2.group(1) if m2 else os.path.basename(p)
            m3 = re.search(r"主君裁定\s*(\d{4}-\d{2}-\d{2})", text)
            closed = m3.group(1) if m3 else ""
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
        out.append({"closed": closed, "title": title, "absorb": absorb,
                    "grave": os.path.relpath(p, ROOT)})
    out.sort(key=lambda r: r["closed"], reverse=True)
    return out


# ---------- 8. 棚の差分 ----------

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
            "hook": os.path.exists(os.path.join(ROOT, ".git", "hooks", "pre-commit")),
            "approve": os.path.isdir(APPROVE),
            "tmp": os.path.isdir(os.path.join(ROOT, "11一時ファイル"))}


# ---------- 組み立て ----------

def table(header, rows):
    """行が無ければヘッダも出さず「（なし）」1 行（分身.md §3-1）。"""
    if not rows:
        return ["（なし）"]
    sep = "|" + "---|" * (header.count("|") - 1)
    return [header, sep] + rows


def build(args):
    """→ (lines, stderr 用の数字)"""
    projects, no_status, frozen = read_projects()
    items, waiting, sent_back = read_council(projects)
    levers = read_levers(projects)
    untils = read_untils(projects)
    resumes = read_resumes()
    routine, sched_src, runs_found = read_routine(args.schedules, getattr(args, "runs", None))
    seats, skills, seats_foot = read_seats(load_schedules(args.schedules)[0], args.monsters)
    done = read_done()
    shelf = read_shelf(no_status)

    n = {s: sum(1 for r in projects if r["state"] == s) for s in list(STATES) + ["語彙外", "状態なし"]}
    longest = max([r["age"] for r in items] or [0])
    fail = sum(1 for r in routine if r["fail"])
    norun = (sum(1 for r in routine if not r["paused"] and r["実行"] == "なし")
             if runs_found else "取得不能（窓の tsv なし）")
    seat_total = sum(r["体数"] for r in seats if r["箱"] != "スキル（未登録）")
    seat_run = ("未取得" if any(r["稼働中"] == "（未取得）" for r in seats)
                else sum(int(r["稼働中"]) for r in seats if str(r["稼働中"]).isdigit()))
    late = sum(1 for r in untils if r["late"])

    L = [f"<!-- 生成: scripts/build_scope_progress.py／{dt.datetime.now():%Y-%m-%d %H:%M}"
         "／手で編集しない。直すなら元（status.md・00廷議/・scheduler・墓標）を直す -->",
         f"# 全体像 — {dt.date.today():%Y-%m-%d}",
         "",
         f"数字: 箱 {len(projects)}（" + "・".join(f"{s} {n[s]}" for s in STATES if n[s]) 
         + f"・語彙外 {n['語彙外']}・状態なし {n['状態なし']}）／凍結 {len(frozen)}"
         f"／裁定待ち {len(items)} 件（最長 {longest} 日・差し戻し {len(sent_back)}）"
         f"／主君の手 {len(levers)}／待ち受け {len(untils)}（🔴 {late}）／再開の合図 {len(resumes)}"
         f"／便 {len(routine)} 本（fail {fail}・実行未記録 {norun}）"
         f"／席 {seat_total} 体（稼働 {seat_run}）／完了 {len(done)}（{DONE_DAYS} 日）",
         "",
         "## 1. プロジェクト（08プロジェクト/ の箱・state 別）", ""]

    def box_rows(rs):
        return [f"| {cell(r['name'])} | {cell(r['owner']) or '?'} | {cell(r['next'], 90) or '—'} | "
                f"{md(r['updated'])} |" for r in rs]

    for st in STATE_SECTIONS:
        rs = [r for r in projects if r["state"] == st]
        L += [f"### {st}（{len(rs)}）", ""]
        L += table("| 箱 | owner | next | updated |", box_rows(rs))
        L.append("")
    for st in ("統合可", "吸収済"):
        rs = [r for r in projects if r["state"] == st]
        if rs:
            L += [f"### {st}（{len(rs)}）", ""] + table("| 箱 | owner | next | updated |", box_rows(rs)) + [""]
    bad = [r for r in projects if r["state"] in ("語彙外", "状態なし")]
    L += [f"### 赤（{len(bad)}・直すのは owner）", ""]
    L += table("| 何 | 箱 | 直し方 |",
               [f"| **{'状態なし' if r['state'] == '状態なし' else '語彙外: ' + cell(r.get('raw_state'))}** | "
                f"{cell(r['name'])} | "
                f"{'status.md を kiroku.py box で作る' if r['state'] == '状態なし' else 'state を語彙（' + '｜'.join(STATES) + '）に直す'} |"
                for r in bad])
    L += ["", f"凍結（09アーカイブ/案件/ の箱・再点火は主君）: " + ("・".join(frozen) if frozen else "（なし）")]

    L += ["", "## 2. 裁定表（00廷議/ ＋ 箱の ask・番号で返す）", ""]
    L += table("| # | 席 | 問い | 推奨 | 期限 | 決めないと |",
               [f"| {CIRCLED[i] if i < len(CIRCLED) else '(' + str(i + 1) + ')'} | "
                f"{cell(r['seat'], 20)}{r['note']} | {cell(r['q'], 70)} | "
                f"{cell(r['rec'], 40) or '—'} | {md(r['due'])} | {cell(r['cost'], 40) or '—'} |"
                for i, r in enumerate(items)])
    L += ["", f"（差し戻し: {len(sent_back)} 件）", ""]
    L += [f"- **差し戻し**: {cell(s, 20)}｜{cell(w, 50)}｜理由＝{why}" for s, w, why in sent_back] or ["- 差し戻し: （なし）"]

    L += ["", "## 3. 主君の手（lever が非空の箱）", ""]
    L += table("| 箱 | 何を | 何秒 | 閉じると何が動くか |",
               [f"| {cell(r['name'])} | {cell(r['what'], 80)} | {cell(r['sec'], 20)} | {cell(r['opens'], 80)} |"
                for r in levers])

    L += ["", "## 4. 待ち受け（until が非空の箱・🔴＝期待日を過ぎた）", ""]
    L += table("| 箱 | 何を | 誰から | 期待日 |",
               [f"| {cell(r['name'])} | {cell(r['what'], 80)} | {cell(r['who'], 40)} | "
                f"{'🔴 ' if r['late'] else ''}{cell(r['when'])} |" for r in untils])
    L += ["", "### 再開の合図（09アーカイブ/案件/ の閉じた箱・resume が非空。来ていたら箱を 08プロジェクト/ へ戻す）", ""]
    L += table("| 箱 | 何を | 誰から | どこで拾う |",
               [f"| {cell(r['name'])} | {cell(r['what'], 80)} | {cell(r['who'], 40)} | {cell(r['where'], 60)} |"
                for r in resumes])

    L += ["", "## 5. Routine（scheduler の全機体）", ""]
    L += table("| 時刻 | 便 | agent | 機体 | 状態 | 最終発火 | 手順書 | 実行 |",
               [f"| {r['時刻']} | {cell(r['便'], 60)} | {cell(r.get('agent'), 20) or '—'} | "
                f"{r['機体']} | {r['状態']} | "
                f"{r['最終発火']} | {r['手順書']} | {r['実行']} |" for r in routine])
    if not any(r["機体"] != "B" for r in routine):
        L += ["", "（ami: 3 本・生成器が読めない）"]
    L += ["", "- **最終発火**＝scheduler が起こしたか（`~/.claude/scheduler/fires.log`）。**実行**＝その便が走り終わったと"
          "帳簿（記録 MCP `kiroku` の `run_start`／`run_end`）に残したか。**起こした ≠ 走り切った**ので 2 列ある",
          "- 実行の出所は `11一時ファイル/便の実行-YYYY-MM.tsv`（便が `run_end` と同時に置く窓・7 日で消える）。"
          "**正本は帳簿**＝手が要った率は `stocktake` で数える。書き方は `docs/定期便-手順/_実行を帳簿へ書く.md`"]
    if not runs_found:
        L += ["- ⚠️ **取得不能**: 窓の tsv が 1 枚も無い（まだどの便も置いていないか、7 日で消えた）。"
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
          f"／00廷議 {'あり' if shelf['approve'] else '**なし**'}"
          f"／11一時ファイル {'あり' if shelf['tmp'] else '**なし**'}"]
    if shelf["big_list"]:
        L += ["", "- 実体: " + " / ".join(shelf["big_list"])]
    L.append("")
    summary = (f"箱 {len(projects)}（状態なし {n['状態なし']}・語彙外 {n['語彙外']}・凍結 {len(frozen)}）"
               f" / 裁定 {len(items)} / 差し戻し {len(sent_back)} / 主君の手 {len(levers)} / 待ち受け {len(untils)}（🔴 {late}）"
               f" / 便 {len(routine)}（fail {fail}・実行未記録 {norun}・src {sched_src}）"
               f" / 席 {seat_total}（稼働 {seat_run}・スキル {skills}）"
               f" / 完了 {len(done)}")
    return L, summary


def box_sections(lines):
    """箱から作る節（§1〜§4）だけを取り出す（--check の比較用。生成時刻の行は除く）。"""
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
    """自己一致: ①語彙 ②全箱 ③§1〜§4 が今の SCOPE_PROGRESS.md と一致"""
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
        print(f"❌ {os.path.relpath(args.out, ROOT)} が無い（生成が要る）"); return 1
    now = open(args.out, encoding="utf-8").read().splitlines()
    if box_sections(lines) != box_sections(now):
        print(f"❌ 一致しない: 箱から作る節（§1〜§4）が {os.path.relpath(args.out, ROOT)} と違う（生成し直しが要る）"); rc = 1
    else:
        print(f"✅ 一致: 箱から作る節（§1〜§4）が {os.path.relpath(args.out, ROOT)} と同じ")
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedules", help="scheduler の一覧 JSON（schedule_list の結果）")
    ap.add_argument("--monsters", help="monster の一覧 JSON（list_monsters の結果）。無ければ「（未取得）」")
    ap.add_argument("--runs", help="便の実行の窓 tsv（既定: 11一時ファイル/便の実行-YYYY-MM.tsv を全部）")
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--check", action="store_true", help="自己一致（語彙・全箱・§1〜§4 の一致）。exit 0/1・書かない")
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
