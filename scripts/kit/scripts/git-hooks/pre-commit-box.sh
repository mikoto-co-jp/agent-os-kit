#!/bin/sh
# 5 本目: 08プロジェクト/ の全箱が語彙表に合うか（status.md の無い箱・語彙外の state・表に無い鍵・owner の主君/要確認・手番 の書式・主君なら 🔬 と本文の 決裁待ちの材料・社外なら期待日）
# 落ちたら commit しない。強行は --no-verify
# 出所: 主君裁定 2026-09-18（帳簿 id=440）「箱の status.md に状態管理を持たせ、SCOPE_PROGRESS で自動的に表になる形にする」
D=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$D/../.." && pwd)
# 本陣の形（器の版 本陣-1）: 箱は中の OS の親＝本陣に在る。古い形（棚 1 つ）なら ROOT のまま
[ -d "$ROOT/../08プロジェクト" ] && ROOT=$(cd "$ROOT/.." && pwd)
OUT=$(python3 "$D/../kiroku.py" --check "$ROOT/08プロジェクト" 2>&1)
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "⛔ pre-commit-box: 08プロジェクト/ の箱が語彙表に合わない。直すのは status.md の frontmatter（道具: python3 scripts/kiroku.py box --slug <箱> …）" >&2
  echo "$OUT" | grep '^❌' >&2
  exit 1
fi
exit 0
