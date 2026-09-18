#!/bin/sh
# PII pre-commit 関門（2026-08-09 設置・経理レーン実害2件が起点）
# ステージされた差分に 口座番号/カード番号/マイナンバー らしきパターンが入ったら commit を止める
d=$(git diff --cached --unified=0 -- '*.md' '*.csv' '*.json' 2>/dev/null | grep '^+' | grep -v '^+++')
echo "$d" | grep -nE '(普通|当座)[  ]*[0-9]{7}|[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}|マイナンバー.*[0-9]{12}' >/dev/null 2>&1 && {
  echo "🚨 PII らしき文字列（口座番号/カード番号/個人番号）が commit に含まれています。経理/docs/作業/（ignore済）へ移すか、--no-verify で明示的に上書きしてください" >&2
  exit 1
}
exit 0
