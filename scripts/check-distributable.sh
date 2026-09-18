#!/bin/bash
# check-distributable.sh — 配布物（席の本文・器の雛形・道具）に固有値が無いかを撃つ門。
# 使い方: bash scripts/check-distributable.sh <file> [<file>...]   ヒット 0 なら exit 0、1 件でもあれば exit 1 でヒット行を出す。
# 固有値 = 持ち主が変わると変わる値（社名・人名・メール・ホスト・IP・UUID・テナント id・クラウドの共有ドライブ名・ホームディレクトリ配下の絶対パス）。
#   雛形では `{名前}` の穴にして、初期セットアップ席が 3 問の答えで埋める（規矩 X-7: 配るのは器だけ）。
# IPv4 は私設域（10./100./172./192.）か末尾 2〜3 桁の物だけ（節番号 5.3.3.1 の誤検知を避ける）。
# 除外: 行に「例:」「例：」「例）」「例)」を含む行（実例として引く固有値は可）。この門の PAT 定義行そのもの（同じ文字列を丸ごと含む行）も除外＝門自体が配布可能。
# ⛔ 配布外の棚を黙って飛ばす仕組みは持たない。渡された物は全部検める（何を配るかは呼ぶ側＝make-kit.sh が決める）。
PAT='(/Users/|~/Desktop|~/\.ssh|~/bin/|\b(10|100|172|192)\.([0-9]{1,3}\.){2}[0-9]{1,3}\b|\b[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{2,3}\b|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|@gmail\.com|@[a-z0-9-]+\.co\.jp|bluelamp[0-9]{2,3}\b|macbook|tatsuya|shiraishi|白石|達也|命OS|株式会社 ?命|[（(]株[）)]命|大和ViSiON|yamatovision|mikoto-(co-jp|monorepo|company|backend|staff)|mikoto\.co\.jp|Yashiro|YASHIRO|asia-northeast1|\bami ?機|司令室)'
EXCL='例[:：）)]\|\[定数'
rc=0; total=0
for f in "$@"; do
  [ -f "$f" ] || { echo "?? $f: 無い"; rc=1; continue; }
  hits=$(grep -nE "$PAT" "$f" | grep -vE "$EXCL" | grep -vF -- "$PAT" || true)
  n=$( [ -n "$hits" ] && echo "$hits" | wc -l | tr -d ' ' || echo 0 )
  total=$((total+n))
  if [ "$n" != "0" ]; then rc=1; echo "❌ $f: $n 件"; echo "$hits" | cut -c1-160 | sed 's/^/   /'; else echo "✅ $f: 0 件"; fi
done
echo "-- 合計 $total 件"; exit $rc
