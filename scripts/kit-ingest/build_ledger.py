#!/usr/bin/env python3
"""台帳（09アーカイブ/コンテクスト銀行/_台帳.csv）を作り直す（工程 6）。カード 1 枚＝1 行。全数を指す。

置き場の理由: 抜いた資産は 01〜05 のどこにも散るので、全数の台帳を内容軸の 1 つ（旧 01商品資産/）に置くと
  「内容軸の 1 つの中に全数が居座る」形になる。メモリシステムの規則「台帳の置き場は、そのデータを使う人が
  最初に開くフォルダの直下」に従い、Vault の横へ置く（2026-09-19 主君裁定・帳簿 id=636）。

入力（読むだけ・書き換えない）:
  <棚>/09アーカイブ/コンテクスト銀行/<key>.md          カード（frontmatter に key・source・id・kind・why・orig_title・duration_min・chars・drive）
  <棚>/01商品資産〜05バックオフィス資産/**/*.md  仕訳先（frontmatter に key）。同じカードが複数に在れば " | " で並べる
出力:
  <棚>/09アーカイブ/コンテクスト銀行/_台帳.csv（UTF-8・NFC・列: key,面,種類,id,題,尺分か字数,原本,カード,仕訳先,抜いた理由）
  --out で別の出力先に書ける（門の前に別の場所へ作り、通ってから置く）
  `仕訳先` が空の行＝まだ仕訳していない物。`面` で束ねれば「あの会社から抜いた物が全部在るか」が数えられる＝解約の判定

使い方: python3 build_ledger.py --shelf <棚のルート> [--out PATH]
冪等・標準ライブラリだけ。カードを足したら必ず撃ち直す。「使われていない行が見えれば、取りこぼしはそこにある」。
"""
import argparse, csv, os, sys, unicodedata

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


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shelf", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    cards_dir = os.path.join(a.shelf, "09アーカイブ", "カード")
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
    rows = []
    if os.path.isdir(cards_dir):
        for n in sorted(os.listdir(cards_dir)):
            if not n.endswith(".md") or n == "README.md":
                continue
            p = os.path.join(cards_dir, n); fm = frontmatter(p)
            if not fm.get("key"):
                continue
            rows.append([nfc(fm["key"]), nfc(fm.get("source", "")), nfc(fm.get("kind", "")), nfc(fm.get("id", "")),
                         nfc(fm.get("orig_title", "")), nfc(fm.get("duration_min", "") or fm.get("chars", "")),
                         nfc(fm.get("drive", "")), os.path.relpath(p, a.shelf),
                         " | ".join(tree.get(fm["key"], [])), nfc(fm.get("why", ""))])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "面", "種類", "id", "題", "尺分か字数", "原本", "カード", "仕訳先", "抜いた理由"])
        w.writerows(rows)
    placed = sum(1 for r in rows if r[8])
    print(f"台帳 {len(rows)} 行 → {out}（仕訳済み {placed}・未仕訳 {len(rows)-placed}）")
    by = {}
    for r in rows:
        b = by.setdefault(r[1] or "（面なし）", [0, 0]); b[0] += 1; b[1] += 1 if r[8] else 0
    for face in sorted(by):
        print(f"  面 {face}: {by[face][0]} 件（仕訳済み {by[face][1]}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
