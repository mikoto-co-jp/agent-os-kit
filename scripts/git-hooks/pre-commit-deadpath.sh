#!/bin/sh
# 死んだ参照の門（2026-09-15）
# 検査するのは「改訂される紙」だけ: .claude/rules/・CLAUDE.md・docs/定期便-手順/・01〜06 の棚。
# 記録（docs/_Operations-Log.md・docs/定期便-ログ/・07プロジェクト/・08アーカイブ/・.claude/記録/）は
# 過去のパスを含むのが正しいので検査しない（ISO 9001: 記録は retained、文書は maintained）。
# docs/SCOPE_PROGRESS.md も検査しない: 上の記録たち（墓標・status.md）から過去のパスを集めて出す
# 生成物で、手で直せない型だから（2026-09-16 に 16 件で毎朝の生成便を止め、--no-verify が常態化していた）。
ROOT=$(git rev-parse --show-toplevel); T=$(mktemp)
git -c core.quotepath=false diff --cached --name-only --diff-filter=ACM -- '*.md' \
 | grep -vE '^(docs/_Operations-Log\.md|docs/SCOPE_PROGRESS\.md|docs/定期便-ログ/|07プロジェクト/|08アーカイブ/|\.claude/記録/)' \
 | while read -r f; do
  git show ":$f" | grep -oE '`(\.claude|docs|0[1-6][^`/ ]*|scripts|09私用|10一時ファイル)/[^`]+`' | tr -d '`' | sort -u | while read -r p; do
    case "$p" in *'*'*|*'<'*|*'…'*|*'['*|*'{'*|*'YYYY'*|*'NNN'*) continue;; esac   # glob・placeholder は飛ばす
    q=$(printf '%s' "$p" | sed 's/[（(].*//; s/ の .*//; s/#.*//; s/[、。].*//')
    [ -e "$ROOT/$q" ] || echo "❌ $f → 実在しない: $q" >&2; [ -e "$ROOT/$q" ] || echo 1 >> "$T"
  done
done
if [ -s "$T" ]; then rm -f "$T"; echo "↑ 指す前に測る。直すか、パスでない物なら \` \` を外す。強行は --no-verify" >&2; exit 1; fi
rm -f "$T"; exit 0
