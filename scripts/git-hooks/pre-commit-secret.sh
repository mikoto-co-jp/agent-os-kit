#!/bin/sh
# 秘密の誤コミット防止（ステージ済みファイル全走査・.githooks 自身は除外）
PATTERNS='postgresql://[^ ]*:[^ @*]*@|BEGIN (RSA |EC )?PRIVATE KEY|sk-[A-Za-z0-9]{20}|AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{20}|xox[bp]-'
FAIL=0
for f in $(git -c core.quotepath=false diff --cached --name-only --diff-filter=ACM); do
  case "$f" in .githooks/*) continue;; esac
  H=$(git show ":$f" 2>/dev/null | grep -EIn "$PATTERNS" | grep -v 'user:pass@host' | grep -v '\*\*\*\*' | head -3)
  [ -n "$H" ] && { echo "❌ pre-commit: $f に秘密らしき文字列:" >&2; echo "$H" >&2; FAIL=1; }
done
exit $FAIL
