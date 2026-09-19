#!/bin/sh
# 秘密の誤コミット防止（ステージ済みファイル全走査・.githooks 自身は除外）
PATTERNS='postgresql://[^ ]*:[^ @*]*@|BEGIN (RSA |EC )?PRIVATE KEY|sk-[A-Za-z0-9]{20}|AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{20}|xox[bp]-'
# 接続文字列の「合言葉の枠」が穴（[PASSWORD] ${VAR} $VAR <...> YOUR_xxx）の行は実値ではない。
# 出所: 2026-09-19 にプロンプト資産 234 枚を git に載せたとき 4 行が偽陽性で止めた（ひな形の穴）。
# ⚠️ 穴と見なすのは「: と @ の間」だけ。利用者名や host に穴が在っても合言葉が実値なら止める。
HOLES='postgresql://[^ ]*:(\[[^]]*\]|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*|<[^>]*>|YOUR[A-Za-z0-9_]*|PASSWORD|password)@'
FAIL=0
for f in $(git -c core.quotepath=false diff --cached --name-only --diff-filter=ACM); do
  case "$f" in .githooks/*) continue;; esac
  H=$(git show ":$f" 2>/dev/null | grep -EIn "$PATTERNS" | grep -v 'user:pass@host' | grep -v '\*\*\*\*' | grep -vE "$HOLES" | head -3)
  [ -n "$H" ] && { echo "❌ pre-commit: $f に秘密らしき文字列:" >&2; echo "$H" >&2; FAIL=1; }
done
exit $FAIL
