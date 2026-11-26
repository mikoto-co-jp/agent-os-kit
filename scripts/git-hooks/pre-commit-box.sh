#!/bin/sh
# 5 本目: この commit が触る 08プロジェクト/<箱>/ が語彙表に合うか（status.md の無い箱・語彙外の state・表に無い鍵・owner の主君/要確認・手番 の書式・主君なら 🔬 と本文の 決裁待ちの材料・先方なら期待日）
# 落ちたら commit しない。強行は --no-verify
# 出所: 主君裁定 2026-09-18（帳簿 id=440）「箱の status.md に状態管理を持たせ、SCOPE_PROGRESS で自動的に表になる形にする」
D=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$D/../.." && pwd)
# 本陣の形（器の版 本陣-1）: 箱は中の OS の親＝本陣に在る。古い形（棚 1 つ）なら ROOT のまま
[ -d "$ROOT/../08プロジェクト" ] && ROOT=$(cd "$ROOT/.." && pwd)
# 🔑 検めるのは、この commit が触る箱だけ（git diff --cached の道が当たる 08プロジェクト/<箱>/）。
#    全箱を検めると、他の席が書きかけて同期された箱や自分の別の箱の書きかけで、箱に触れない保存まで止まった。
#    箱に触れない commit では撃たない。消えた箱（09アーカイブ へ動かした等）は検めない（在る箱だけ）
BOXES=$(python3 - "$ROOT/08プロジェクト" <<'PY'
import os, subprocess, sys
proj = os.path.realpath(sys.argv[1])
top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
out = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only", "--no-renames", "-z"],
                     capture_output=True, text=True).stdout
seen = []
for p in filter(None, out.split("\0")):
    rel = os.path.relpath(os.path.realpath(os.path.join(top, p)), proj)
    parts = rel.split(os.sep)
    if rel.startswith("..") or len(parts) < 2 or parts[0].startswith("."):
        continue   # 箱の外・08プロジェクト 直下のファイル（箱でない）
    box = os.path.join(proj, parts[0])
    if os.path.isdir(box) and box not in seen:
        seen.append(box)
print("\n".join(os.path.join(b, "status.md") for b in seen))
PY
) || { echo "⛔ pre-commit-box: commit が触る箱を測れない（python3 か git が落ちた）" >&2; exit 1; }
[ -z "$BOXES" ] && exit 0
OLDIFS=$IFS; IFS='
'
set -- $BOXES
IFS=$OLDIFS
OUT=$(python3 "$D/../kiroku.py" --check "$@" 2>&1)
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "⛔ pre-commit-box: この commit が触る箱が語彙表に合わない。直すのは status.md の frontmatter（道具: python3 scripts/kiroku.py box --slug <箱> …）" >&2
  echo "$OUT" | grep '^❌' >&2
  exit 1
fi
exit 0
