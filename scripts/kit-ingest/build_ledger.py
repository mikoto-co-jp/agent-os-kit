#!/usr/bin/env python3
"""台帳（コンテクスト銀行/_台帳.csv）を作り直す（工程 6）。カード 1 枚＝1 行。全数を指す。

置き場の理由: 抜いた資産は 01〜05 のどこにも散るので、全数の台帳を内容軸の 1 つ（旧 01商品資産/）に置くと
  「内容軸の 1 つの中に全数が居座る」形になる。メモリシステムの規則「台帳の置き場は、そのデータを使う人が
  最初に開くフォルダの直下」に従い、Vault の横へ置く（2026-09-19 主君裁定・帳簿 id=636）。

入力（読むだけ・書き換えない）:
  <棚>/コンテクスト銀行/<key>.md          カード（frontmatter に key・source・id・kind・why・orig_title・duration_min・chars・drive）
  <棚>/01商品資産〜05バックオフィス資産/**/*.md  仕訳先（frontmatter に key）。同じカードが複数に在れば " | " で並べる
  <棚>/コンテクスト銀行/_台帳-面.csv       在れば列 `仕訳しない種類` だけ読む（その面の 種類 を `／` 区切り）。
                                          その面・その種類で仕訳先が空の行は `仕訳先` に「（仕訳しない）」と書き、未仕訳から外す。
                                          列が無い・空なら 仕訳しない は 0（今までどおり）
出力:
  <棚>/コンテクスト銀行/_台帳.csv（UTF-8・NFC・列: key,面,種類,id,題,尺分か字数,原本,カード,仕訳先,抜いた理由,正本の在り処,読む口。後ろ 2 列は外に正本が在る物の在り処と今の値を読む道具の名前＝この生成器は空で出す）
  --out で別の出力先に書ける（門の前に別の場所へ作り、通ってから置く）
  `仕訳先` が空の行＝まだ仕訳していない物。「（仕訳しない）」＝面の台帳で仕分けしないと決めた物。`面` で束ねれば「あの会社から抜いた物が全部在るか」が数えられる＝解約の判定

使い方: python3 build_ledger.py --shelf <棚のルート> [--out PATH] [--face-ledger PATH]
        python3 build_ledger.py --selftest   （検体で 仕訳しない が数えられる・列が空なら 0 を確かめる）
冪等・標準ライブラリだけ。カードを足したら必ず撃ち直す。「使われていない行が見えれば、取りこぼしはそこにある」。
"""
import argparse, csv, os, re, sys, tempfile, unicodedata

# 仕訳先として走査する内容軸（メモリシステムの内容軸。面 → ここへの対応表は メモリシステム.md が正本）
DOMAINS = ["01商品資産", "02マーケティング資産", "03セールス資産", "04オペレーション資産", "05バックオフィス資産"]


def frontmatter(path):
    fm = {}
    try:
        with open(path, encoding="utf-8") as f:
            if f.readline().strip() != "---":
                return fm
            for line in f:
                if line.strip() == "---":
                    break
                if ":" in line and not line[:1].isspace():
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"').strip("'")
    except (OSError, UnicodeDecodeError):
        pass
    return fm


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


NO_SORT = "（仕訳しない）"
NO_SORT_COL = "仕訳しない種類"


def read_no_sort(path):
    """面の台帳から {面: {種類,…}} を返す。ファイルか列が無ければ空。"""
    out = {}
    if not path or not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or NO_SORT_COL not in [nfc(c).strip() for c in r.fieldnames]:
            return out
        for row in r:
            row = {nfc(k).strip(): nfc(v) for k, v in row.items() if k is not None}
            face = (row.get("面") or "").strip()
            kinds = {k.strip() for k in re.split(r"[／/|、,]", row.get(NO_SORT_COL) or "") if k.strip()}
            if face and kinds:
                out.setdefault(face, set()).update(kinds)
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shelf")
    ap.add_argument("--out", default="")
    ap.add_argument("--face-ledger", default="", help="面の台帳（既定 <棚>/コンテクスト銀行/_台帳-面.csv）")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.shelf:
        ap.error("--shelf が要る")
    cards_dir = os.path.join(a.shelf, "コンテクスト銀行")   # 2026-09-20 の改名の後の置き場
    out = a.out or os.path.join(cards_dir, "_台帳.csv")
    tree = {}
    for box in DOMAINS:
        d = os.path.join(a.shelf, box)
        if not os.path.isdir(d):
            continue
        for dp, dns, fns in os.walk(d):
            dns.sort()
            for n in sorted(fns):
                if n.endswith(".md") and n != "README.md":
                    k = frontmatter(os.path.join(dp, n)).get("key")
                    if k:
                        tree.setdefault(k, []).append(os.path.relpath(os.path.join(dp, n), a.shelf))
    no_sort = read_no_sort(a.face_ledger or os.path.join(cards_dir, "_台帳-面.csv"))
    rows = []
    if os.path.isdir(cards_dir):
        for n in sorted(os.listdir(cards_dir)):
            if not n.endswith(".md") or n == "README.md":
                continue
            p = os.path.join(cards_dir, n); fm = frontmatter(p)
            if not fm.get("key"):
                continue
            face, kind = nfc(fm.get("source", "")), nfc(fm.get("kind", ""))
            placed_at = " | ".join(tree.get(fm["key"], []))
            if not placed_at and kind and kind in no_sort.get(face, ()):
                placed_at = NO_SORT
            rows.append([nfc(fm["key"]), face, kind, nfc(fm.get("id", "")),
                         nfc(fm.get("orig_title", "")), nfc(fm.get("duration_min", "") or fm.get("chars", "")),
                         nfc(fm.get("drive", "")), os.path.relpath(p, a.shelf),
                         placed_at, nfc(fm.get("why", "")), "", ""])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "面", "種類", "id", "題", "尺分か字数", "原本", "カード", "仕訳先", "抜いた理由", "正本の在り処", "読む口"])
        w.writerows(rows)
    skip = sum(1 for r in rows if r[8] == NO_SORT)
    placed = sum(1 for r in rows if r[8] and r[8] != NO_SORT)
    print(f"台帳 {len(rows)} 行 → {out}（仕訳済み {placed}・未仕訳 {len(rows)-placed-skip}・仕訳しない {skip}）")
    by = {}
    for r in rows:
        b = by.setdefault(r[1] or "（面なし）", [0, 0, 0]); b[0] += 1
        if r[8] == NO_SORT:
            b[2] += 1
        elif r[8]:
            b[1] += 1
    for face in sorted(by):
        print(f"  面 {face}: {by[face][0]} 件（仕訳済み {by[face][1]}・未仕訳 {by[face][0]-by[face][1]-by[face][2]}・仕訳しない {by[face][2]}）")
    return 0


def selftest():
    """検体の棚で 3 つの数え方を確かめる。正: 列に書いた種類が 仕訳しない に入る／負制御: 列が空なら 仕訳しない 0。"""
    import contextlib, io
    def card(d, key, face, kind):
        with open(os.path.join(d, key + ".md"), "w", encoding="utf-8") as f:
            f.write(f"---\nkey: {key}\nsource: {face}\nkind: {kind}\n---\n本文\n")
    def run(shelf, out):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--shelf", shelf, "--out", out])
        with open(out, encoding="utf-8") as f:
            rows = list(csv.reader(f))
        return rc, buf.getvalue(), rows
    with tempfile.TemporaryDirectory() as t:
        cb = os.path.join(t, "コンテクスト銀行"); os.makedirs(cb)
        os.makedirs(os.path.join(t, "02マーケティング資産"))
        card(cb, "photo-1", "photo", "写真"); card(cb, "photo-2", "photo", "写真")
        card(cb, "photo-3", "photo", "動画"); card(cb, "mail-1", "mail", "配信")
        with open(os.path.join(t, "02マーケティング資産", "a.md"), "w", encoding="utf-8") as f:
            f.write("---\nkey: mail-1\n---\n")
        fl = os.path.join(cb, "_台帳-面.csv")
        # 正: photo の 写真 だけ 仕訳しない
        with open(fl, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows([["面", "サービス名", NO_SORT_COL], ["photo", "写真", "写真"], ["mail", "配信", ""]])
        rc, msg, rows = run(t, os.path.join(t, "o1.csv"))
        hdr = rows[0]
        if rc != 0 or len(hdr) != 12 or hdr[-2:] != ["正本の在り処", "読む口"]:
            print("🚨 selftest: 列が 12 本で出ない", hdr); return 3
        if "仕訳済み 1・未仕訳 1・仕訳しない 2" not in msg:
            print("🚨 selftest: 仕訳しない が数えられない\n" + msg); return 3
        if sum(1 for r in rows[1:] if r[8] == NO_SORT) != 2:
            print("🚨 selftest: 仕訳先 に（仕訳しない）が書かれない"); return 3
        # 負制御: 列が空
        with open(fl, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows([["面", "サービス名", NO_SORT_COL], ["photo", "写真", ""], ["mail", "配信", ""]])
        rc, msg, rows = run(t, os.path.join(t, "o2.csv"))
        if "仕訳済み 1・未仕訳 3・仕訳しない 0" not in msg:
            print("🚨 selftest 負制御: 列が空なのに 仕訳しない が 0 でない\n" + msg); return 3
        # 負制御: 列そのものが無い（旧い面の台帳）
        with open(fl, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows([["面", "サービス名"], ["photo", "写真"]])
        rc, msg, rows = run(t, os.path.join(t, "o3.csv"))
        if "仕訳済み 1・未仕訳 3・仕訳しない 0" not in msg:
            print("🚨 selftest 負制御: 列が無いのに 仕訳しない が 0 でない\n" + msg); return 3
    print("selftest ok: 仕訳しない 2（正）／列が空 0・列が無い 0（負制御）／列 12 本")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
