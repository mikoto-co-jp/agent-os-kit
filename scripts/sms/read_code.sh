#!/bin/sh
# 二段階認証のコードを、この Mac に届いた SMS／iMessage から読む。
# 使い方: sh scripts/sms/read_code.sh [何分前まで見るか（既定 10）]
# 狙い: 携帯に届く確認コードを人に読ませない（規矩 §5-2 スマホ同期）。1 回の設定で以後すべての面の SMS の壁が消える。
# 🚨 前提: iPhone の 設定 → メッセージ → テキストメッセージ転送 で この Mac を ON にすること。
#         ⚠️ 転送が OFF だと最終受信が何か月も前のまま返る。⛔ 0 件を「コードが来ていない」と読む前に、
#            直近の受信日時を見て転送そのものが生きているかを確かめる（否定結果には陽性対照を）。
# ⛔ 値を会話に書かない。撃った席が読んで、その場で使う。
MIN=${1:-10}
DB="$HOME/Library/Messages/chat.db"
[ -r "$DB" ] || { echo "🚨 chat.db が読めない（フルディスクアクセスが要る）" >&2; exit 1; }
sqlite3 "$DB" "
select datetime(m.date/1000000000+978307200,'unixepoch','localtime') || '  [' || m.service || ']  ' ||
       replace(coalesce(m.text, m.attributedBody), char(10), ' ')
from message m
where m.is_from_me = 0
  and m.date/1000000000 + 978307200 > strftime('%s','now') - ${MIN}*60
order by m.date desc limit 10;"
