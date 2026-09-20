#!/usr/bin/env python3
"""席のエイリアス箱を建てる（06エージェント資産/_便/ と _孔明起動/）

何をするか: 台帳 2 本を読んで、**symlink だけ**の箱を 2 つ作り直す。
  _便/      … 便（scheduler が回す物）。名前の頭に時刻（HHMM）を付ける＝開いた瞬間に
               何時に何が回るか見える。台帳 06エージェント資産/_台帳-便.csv
  _孔明起動/ … 孔明が起動したら一緒に起きる席。時刻が無いので名前だけ。
               台帳 06エージェント資産/_台帳-孔明起動.csv

⛔ この 2 つの箱に実体を置かない。中身は symlink（相対）だけ。⛔ 絶対パスを焼かない。

🔑 便の正本は scheduler で、その控えは **scheduler 自身が持つ JSON**（既定 `~/.claude/scheduler/
   schedules.json`。環境変数 `SCHEDULER_STATE` で差し替え可）。**この紙はそれを自分で読む**＝
   席が `schedule_list` を撃って JSON に落とす手番は要らない（2026-09-20・実測で
   `schedule_list` の戻りと同じ 16 件・同じ id/cron/paused であることを確かめた）。
   このスクリプトは cron・label・状態 を台帳へ書き戻し、`正本`（どの紙がその便の手順か）は
   台帳に既に在る値をそのまま残す＝**人が決める列**。
   ⚠️ 新しい便は `正本` が空で足される。空のままなら link は張らず、検査が数える。
   ⛔ **控えが無いときは 0 件として扱わない**（「取れなかった」が「便が 1 本も無い」に化けると、
     台帳の全行が `消えた` に書き換わる）。取得不能として終了コード 2 で落ちる。

使い方:
    python3 scripts/build_agent_aliases.py                 # scheduler の控え → 台帳 → 箱
    python3 scripts/build_agent_aliases.py --schedules s.json  # 控えの代わりにこの JSON を読む
    python3 scripts/build_agent_aliases.py --no-refresh    # 台帳だけで箱を作り直す（控えを読まない）
    python3 scripts/build_agent_aliases.py --check         # 検査だけ（終了コード 0/1）
    python3 scripts/build_agent_aliases.py --selftest      # 負制御（検査が落ちるか）

終了コード: 0 = 正常 ／ 1 = 検査に落ちた ／ 2 = 台帳か scheduler の控えが読めない
"""
import argparse, csv, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(os.environ.get("MIKOTO_OS_ROOT") or Path(__file__).resolve().parents[1])
SHELF = "06エージェント資産"
BIN_BOX, KOMEI_BOX = "_便", "_孔明起動"
BIN_LEDGER, KOMEI_LEDGER = "_台帳-便.csv", "_台帳-孔明起動.csv"

KOMEI_README = """# _孔明起動 — 孔明が起動したら一緒に起きる席

ここに在るのは **エイリアスだけ**（実体は箱 `00マイエージェント/`〜`07退役エージェント/` か
`docs/定期便-手順/` に在る）。⛔ 実体をここに置かない。

| 何 | 中身 |
|---|---|
| 何がここに入るか | 孔明が起動したときに、時刻に依らず一緒に起きる席 |
| 誰が入れるか | 孔明（台帳 `_台帳-孔明起動.csv` に 1 行足して `scripts/build_agent_aliases.py` を撃つ） |
| `_便/` との違い | `_便/` は scheduler が時刻で起こす物。⛔ **同じ席を両方に置かない**（二重起動）。検査が数える |

⚠️ この紙は生成器が**無いときだけ**書く。ここに棚ごとの事情（1 号は誰か・いつ建てたか）を足してよい。
"""


def read_ledger(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]


def hhmm(cron: str) -> str:
    """cron の 分 時 から HHMM。読めなければ空。"""
    p = (cron or "").split()
    if len(p) < 2 or not p[0].isdigit() or not p[1].isdigit():
        return ""
    return f"{int(p[1]):02d}{int(p[0]):02d}"


def safe(name: str) -> str:
    return re.sub(r"[/\x00]", "-", (name or "").strip())


def scheduler_state() -> Path:
    """scheduler 自身が持つ控えの道。⛔ 機体固有の値を焼かない（$HOME から組む）。"""
    env = os.environ.get("SCHEDULER_STATE")
    return Path(env) if env else Path.home() / ".claude" / "scheduler" / "schedules.json"


def refresh_from_schedules(shelf: Path, sched_json: Path):
    """scheduler の控えで 台帳-便 の cron・時刻・便・agent・状態 を書き戻す。正本 は触らない。"""
    data = json.loads(sched_json.read_text(encoding="utf-8"))
    scheds = data.get("schedules", data.get("result", data)) if isinstance(data, dict) else data
    if not isinstance(scheds, list):
        raise ValueError(f"scheduler の控えの形が読めない（list でない）: {sched_json}")
    led = shelf / BIN_LEDGER
    rows = read_ledger(led)
    by_id = {r["id"]: r for r in rows}
    fields = ["id", "cron", "時刻", "便", "正本", "agent", "状態", "備考"]
    added, gone = [], []
    for s in scheds:
        sid = str(s.get("id", ""))[:8]
        r = by_id.get(sid)
        if r is None:
            r = {k: "" for k in fields}
            r["id"] = sid
            r["便"] = safe(str(s.get("label", ""))).split("（")[0].split("(")[0].strip()
            rows.append(r); by_id[sid] = r; added.append(sid)
        r["cron"] = str(s.get("cron", ""))
        r["時刻"] = hhmm(r["cron"])
        r["agent"] = str(s.get("agent", ""))
        r["状態"] = "止まっている" if s.get("paused") else "稼働"
    live = {str(s.get("id", ""))[:8] for s in scheds}
    for r in rows:
        if r["id"] not in live and r["状態"] != "消えた":
            r["状態"] = "消えた"; gone.append(r["id"])
    rows.sort(key=lambda r: (r["時刻"] or "9999", r["便"]))
    with led.open("w", encoding="utf-8", newline="") as f:
        # 行末は LF。⛔ 既定の CRLF にしない（棚の他の台帳は全部 LF・差分が毎回出る）
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return added, gone


def rebuild(shelf: Path, quiet=False):
    """台帳 2 本 → 箱 2 つの symlink を作り直す。戻りは (張った数, 張れなかった行)。"""
    plans, skipped = {BIN_BOX: [], KOMEI_BOX: []}, []

    for r in read_ledger(shelf / BIN_LEDGER):
        if r.get("状態", "") != "稼働":
            continue
        tgt, t = (r.get("正本") or "").strip(), (r.get("時刻") or "").strip()
        if not tgt:
            skipped.append(f"{BIN_BOX}: {r.get('便','?')}（正本が空: {r.get('備考','') or '未定'}）"); continue
        if not (ROOT / tgt).exists():
            skipped.append(f"{BIN_BOX}: {r.get('便','?')}（正本が実在しない: {tgt}）"); continue
        plans[BIN_BOX].append((f"{t or '____'}-{safe(r['便'])}.md", tgt))

    for r in read_ledger(shelf / KOMEI_LEDGER):
        tgt = (r.get("正本") or "").strip()
        if not tgt:
            skipped.append(f"{KOMEI_BOX}: {r.get('席','?')}（正本が空）"); continue
        if not (ROOT / tgt).exists():
            skipped.append(f"{KOMEI_BOX}: {r.get('席','?')}（正本が実在しない: {tgt}）"); continue
        plans[KOMEI_BOX].append((f"{safe(r['席'])}.md", tgt))

    made = 0
    for box, items in plans.items():
        d = shelf / box
        d.mkdir(parents=True, exist_ok=True)
        for f in d.iterdir():                       # 古い link だけ消す（実体は消さない）
            if f.is_symlink():
                f.unlink()
            elif f.name not in ("README.md",):
                skipped.append(f"{box}: 実体が居座っている（消していない）: {f.name}")
        for name, tgt in sorted(items):
            rel = os.path.relpath(ROOT / tgt, d)    # 相対だけ。⛔ 絶対パスを焼かない
            (d / name).symlink_to(rel)
            made += 1
            if not quiet:
                print(f"  {box}/{name} → {rel}")
    rm = shelf / KOMEI_BOX / "README.md"
    if not rm.exists():                              # 人が足した棚ごとの事情を消さない
        rm.write_text(KOMEI_README, encoding="utf-8")
    return made, skipped


def check(shelf: Path):
    """🔑 検査。二値で返す（0 = 合格）。"""
    bad, seen = [], {}
    for box in (BIN_BOX, KOMEI_BOX):
        d = shelf / box
        if not d.is_dir():
            bad.append(f"箱が無い: {box}"); continue
        for f in sorted(d.iterdir()):
            if f.name == "README.md":
                continue
            if not f.is_symlink():
                bad.append(f"❌ 実体が居る（symlink だけの箱）: {box}/{f.name}"); continue
            if not f.resolve().exists():             # 1. 切れた symlink ＝ 迷子
                bad.append(f"❌ 迷子（先が実在しない）: {box}/{f.name} → {os.readlink(f)}")
                continue
            seen.setdefault(str(f.resolve()), []).append(f"{box}/{f.name}")
    for tgt, where in seen.items():                  # 2. 両方の箱に同じ席＝二重起動
        boxes = {w.split("/")[0] for w in where}
        if len(boxes) > 1:
            bad.append(f"❌ 二重起動（{' と '.join(sorted(boxes))} に同じ席）: {tgt}")
    return bad


def selftest():
    """🔬 負制御: わざと切れた symlink を 1 本作り、検査 1 がそれを検出することを確かめる。"""
    tmp = Path(tempfile.mkdtemp())
    try:
        shelf = tmp / SHELF; (shelf / BIN_BOX).mkdir(parents=True); (shelf / KOMEI_BOX).mkdir()
        real = shelf / "00マイエージェント"; real.mkdir(); (real / "x.md").write_text("x")
        (shelf / BIN_BOX / "0545-生きている.md").symlink_to("../00マイエージェント/x.md")
        if check(shelf):
            print("❌ selftest A: 健全な箱で落ちた"); return 1
        (shelf / BIN_BOX / "0600-迷子.md").symlink_to("../00マイエージェント/無い.md")
        b = check(shelf)
        if not any("迷子" in x for x in b):
            print("❌ selftest B: 切れた symlink を検出しなかった＝落ちない検査"); return 1
        (shelf / BIN_BOX / "0600-迷子.md").unlink()
        (shelf / KOMEI_BOX / "二重.md").symlink_to("../00マイエージェント/x.md")
        (shelf / BIN_BOX / "0700-二重.md").symlink_to("../00マイエージェント/x.md")
        b = check(shelf)
        if not any("二重起動" in x for x in b):
            print("❌ selftest C: 両方の箱に同じ席が居るのを検出しなかった"); return 1
        (shelf / KOMEI_BOX / "二重.md").unlink(); (shelf / BIN_BOX / "0700-二重.md").unlink()
        (shelf / BIN_BOX / "実体.md").write_text("これは symlink ではない")
        if not any("実体が居る" in x for x in check(shelf)):
            print("❌ selftest D: 実体の居座りを検出しなかった"); return 1
        print("✅ selftest 4 段（A 健全で通る・B 迷子で落ちる・C 二重起動で落ちる・D 実体で落ちる）")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedules", help="scheduler の控えの代わりに読む JSON（既定は自分で見つける）")
    ap.add_argument("--no-refresh", action="store_true", help="控えを読まず、台帳だけで箱を作り直す")
    ap.add_argument("--check", action="store_true", help="検査だけ")
    ap.add_argument("--selftest", action="store_true", help="負制御")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    shelf = ROOT / SHELF
    if not shelf.is_dir():
        print(f"❌ 棚が無い: {shelf}"); return 2
    if a.check:
        bad = check(shelf)
        print("\n".join(bad) if bad else "✅ 検査 0 件（迷子なし・二重起動なし・実体の居座りなし）")
        return 1 if bad else 0
    if not a.no_refresh:
        src = Path(a.schedules) if a.schedules else scheduler_state()
        if not src.exists():
            # ⛔ ここで 0 件として続けない。台帳の全行が「消えた」に書き換わる。
            print(f"❌ 取得不能（scheduler の控えが無い: {src}）")
            print("   便が本当に 0 本なのか、控えが読めないだけなのか、ここでは区別できない。")
            print("   控えの道が違うなら SCHEDULER_STATE か --schedules で渡す。")
            print("   控えを読まずに箱だけ作り直すなら --no-refresh。")
            return 2
        try:
            added, gone = refresh_from_schedules(shelf, src)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"❌ 取得不能（scheduler の控えが読めない: {src}）: {e}")
            return 2
        print(f"台帳-便 を更新（出所 {src}）: 足した {len(added)} 件 {added} / 消えた {len(gone)} 件 {gone}")
    made, skipped = rebuild(shelf)
    print(f"張った link {made} 本")
    for s in skipped:
        print(f"  ⚠️ 張らなかった: {s}")
    bad = check(shelf)
    print("\n".join(bad) if bad else "✅ 検査 0 件")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
