#!/bin/bash
# make-kit.sh — 生きている棚から「器だけ」を切り出す 1 本（初期セットアップ席が撃つ）。
#
# 🔑 何を配るか: 地図（CLAUDE.md）・規則の紙 3 枚（.claude/rules/・固有値は {名前} の穴）・空の箱（.gitkeep）・
#   道具（scripts/ の固定リストと git-hooks/）・.gitignore・便の手順の雛形 1 枚。**中身は 1 行も入れない**（規矩 X-7）。
#   docs/SCOPE_PROGRESS.md は入れない＝生成器が最初に書く（`python3 scripts/build_scope_progress.py`）。
# 🔑 雛形の置き場: scripts/kit/（生きている紙から固有値・件数・日付つきの社内事故を抜いた写し）。雛形も出力に入れる（建てた棚が自分で門を撃ち、次の棚を切り出せる）。
#   写しは腐るので **--drift** が門: 規矩の X・H（雛形は生きている紙の部分集合・番号は連番）・帳簿の列・領域 8 語・種別・層、箱の state 8 語 が
#   生きている紙（.claude/rules/・scripts/kiroku.py）と一致しなければ exit 1。--selftest はこれも撃つ。
#
# 使い方:
#   bash scripts/make-kit.sh <出力先>                       出力先は空か存在しない dir。門（固有値 0 件）を通れば exit 0
#   bash scripts/make-kit.sh --fill <棚> 名前=… 呼ばれ方=… 事業名=… 棚の名前=… 棚の置き場=… "git remote=…"
#                                                          雛形の {名前} を埋める（冪等。無い穴は何もしない。埋めない穴は残る）
#   bash scripts/make-kit.sh --drift                        雛形と生きている紙の骨が一致するか（exit 0/1）
#   bash scripts/make-kit.sh --selftest                     空の一時 git リポに切り出して門を全部撃つ。exit 0＝合格／1＝壊れている／3＝負制御が落ちなかった
#
# ⚠️ bash 3.2（macOS 既定）は "$f（" の全角を変数名に取り込む。日本語の前の変数は必ず ${f} で囲む
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KIT="$ROOT/scripts/kit"
GATE="$ROOT/scripts/check-distributable.sh"

# ============================== 配る物（固定リスト。`scripts/*` を舐めない）==============================
# 当社固有の生成器（course/・register/・経理/・mirror_*.py・build_distribution_ledgers.py ほか）は入れない。足すならここに 1 行
KIT_TOOLS="kiroku.py build_scope_progress.py check-distributable.sh make-kit.sh"
KIT_HOOKS="pre-commit-secret.sh pre-commit-pii.sh pre-commit-deadpath.sh pre-commit-box.sh"
KIT_BOXES="00廷議 01商品資産 02マーケティング資産 03セールス資産 04オペレーション資産 05バックオフィス資産 06学習資産 07プロジェクト
08アーカイブ/案件 08アーカイブ/裁定 08アーカイブ/カード 09私用 10一時ファイル docs/定期便-手順 docs/定期便-ログ"
# ==================================================================================================

die() { echo "🚨 $*" >&2; exit "${2:-1}"; }

# ---------- --drift: 雛形の骨が生きている紙と一致するか ----------
drift() {
  python3 - "$ROOT" "$KIT" <<'PY'
import re, sys, os
root, kit = sys.argv[1], sys.argv[2]
def read(p): return open(p, encoding="utf-8").read().splitlines()
def cells(l): return [c.strip() for c in l.strip().strip("|").split("|")]
def bones(lines):
    b = {}
    for l in lines:
        if re.match(r"^\| X-\d", l): c = cells(l); b["X " + c[0]] = (c[1], c[3])   # やらない事・代わりに（理由は日付を抜いてよい）
        if re.match(r"^\| H-\d", l): c = cells(l); b["H " + c[0]] = c[1]
        if re.match(r"^date,領域,", l): b["列"] = l
        if re.match(r"^\| \*\*`種別`\*\*", l): b["種別"] = l
        if re.match(r"^\| `層`", l): b["層"] = l
    sec = False
    for l in lines:
        if l.startswith("### 領域"): sec = True; continue
        if sec and l.startswith("#"): break
        if sec and re.match(r"^\| \*?\*?`", l): b.setdefault("領域", []).append(re.sub(r"[*`]", "", cells(l)[0]))
    return b
live = bones(read(os.path.join(root, ".claude/rules/規矩.md")))
tmpl = bones(read(os.path.join(kit, ".claude/rules/規矩.md")))
rc = 0
# X・H は「雛形 ⊆ 生きている紙」を中身で照合（主君が器から落とした行が在る＝2026-09-18・番号は雛形側で 1..n の連番に振り直す）
for pre in ("X ", "H "):
    live_vals = {v for k, v in live.items() if k.startswith(pre)}
    tk = sorted((k for k in tmpl if k.startswith(pre)), key=lambda k: int(k.split("-")[1]))
    for i, k in enumerate(tk, 1):
        if k != f"{pre}{pre.strip()}-{i}":
            rc = 1; print(f"❌ 規矩 {k}: 雛形の番号が連番でない（期待 {pre.strip()}-{i}）")
        if tmpl[k] not in live_vals:
            rc = 1; print(f"❌ 規矩 {k}: 雛形の行が生きている紙に無い {tmpl[k]!r}")
for k in sorted(set(live) | set(tmpl)):
    if k[:2] in ("X ", "H "): continue
    if live.get(k) != tmpl.get(k):
        rc = 1; print(f"❌ 規矩 {k}: 生 {live.get(k)!r} ／ 雛形 {tmpl.get(k)!r}")
sys.path.insert(0, os.path.join(root, "scripts")); import kiroku
states = "｜".join(kiroku.STATES)
for name in ("メモリシステム.md",):
    for label, p in (("生", os.path.join(root, ".claude/rules", name)), ("雛形", os.path.join(kit, ".claude/rules", name))):
        if states not in open(p, encoding="utf-8").read():
            rc = 1; print(f"❌ {label} {name}: kiroku.STATES（{states}）の並びが載っていない")
print("✅ drift: 雛形の骨（X・H は部分集合・列・領域・種別・層・state 8 語）は生きている紙と一致" if rc == 0 else "🚨 drift: 雛形が腐っている。scripts/kit/ を直す")
sys.exit(rc)
PY
}

# ---------- --fill: {名前} を埋める（冪等） ----------
fill() {
  local out="$1"; shift
  [ -d "$out" ] || die "棚が無い: $out" 2
  python3 - "$out" "$@" <<'PY'
import os, sys
out, pairs = sys.argv[1], sys.argv[2:]
rep = {}
for p in pairs:
    k, _, v = p.partition("=")
    if not k or not v: sys.exit(f"🚨 --fill の書式は キー=値: {p!r}")
    rep["{" + k + "}"] = v
n = 0
for d, _, fs in os.walk(out):
    if "/.git" in d or d.endswith("/.git"): continue
    for f in fs:
        p = os.path.join(d, f)
        if not f.endswith((".md", ".sh", ".py", ".gitignore")) and f != ".gitignore": continue
        s = open(p, encoding="utf-8").read(); t = s
        for k, v in rep.items(): t = t.replace(k, v)
        if t != s: open(p, "w", encoding="utf-8").write(t); n += 1; print(f"  ~ {os.path.relpath(p, out)}")
print(f"== fill: {n} 本を埋めた（{', '.join(rep)}）")
PY
}

# ---------- 切り出し ----------
cut() {
  local OUT="$1"
  [ -e "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ] && die "出力先が空でない: $OUT" 2
  mkdir -p "$OUT" || exit 2
  cd "$ROOT" || exit 2
  copy() { mkdir -p "$OUT/$(dirname "$2")"; cp "$1" "$OUT/$2"; echo "  + ${2}"; }
  # maybe_copy <元> <先> … 固有値 0 件の物だけ配る。1 件でもあれば配らず落とす（⛔ 黙って落とさない）
  maybe_copy() {
    local h; h=$(bash "$GATE" "$1" 2>/dev/null | sed -n 's/^-- 合計 \([0-9]*\) 件$/\1/p')
    if [ "${h:-0}" != "0" ]; then echo "  🚨 ${1}（固有値 ${h} 件・配らない）"; return 1; else copy "$1" "$2"; fi
  }
  echo "== make-kit: $ROOT → $OUT"
  local rc=0 f b
  # 1) 雛形（地図・規則 3 枚・便の手順 1 枚）
  for f in $(cd "$KIT" && find . -type f -not -name '.DS_Store' | sed 's#^\./##' | sort); do
    maybe_copy "scripts/kit/$f" "$f" || rc=1
    copy "scripts/kit/$f" "scripts/kit/$f"        # 雛形も配る＝建てた棚が自分で --selftest を撃て、次の棚を切り出せる
  done
  # 2) 道具（固定リスト）
  for b in $KIT_TOOLS; do
    [ -f "scripts/$b" ] || { echo "  🚨 scripts/${b} が無い（リストと現物がずれている）"; rc=1; continue; }
    maybe_copy "scripts/$b" "scripts/$b" || rc=1
  done
  for b in $KIT_HOOKS; do
    [ -f "scripts/git-hooks/$b" ] || { echo "  🚨 scripts/git-hooks/${b} が無い"; rc=1; continue; }
    maybe_copy "scripts/git-hooks/$b" "scripts/git-hooks/$b" || rc=1
  done
  # pre-commit の親は書き下ろす（生きている方は当社固有の門を 1 本余分に撃つため）
  cat > "$OUT/scripts/git-hooks/pre-commit" <<'SH'
#!/bin/sh
# pre-commit（配線: git config core.hooksPath scripts/git-hooks）
# 4 本を順に撃つ。1 本でも落ちたら commit しない。強行は --no-verify
#   秘密（鍵・接続文字列）／PII（口座・カード・個人番号）／死んだ参照（改訂される紙が指す実在しないパス）／箱（07プロジェクト/ の status.md が語彙表に合うか）
D=$(dirname "$0"); FAIL=0
for h in pre-commit-secret.sh pre-commit-pii.sh pre-commit-deadpath.sh pre-commit-box.sh; do sh "$D/$h" || FAIL=1; done
exit $FAIL
SH
  chmod +x "$OUT"/scripts/git-hooks/* "$OUT"/scripts/*.sh; echo "  + scripts/git-hooks/pre-commit（書き下ろし）"
  # 3) .gitignore
  cat > "$OUT/.gitignore" <<'GI'
# 見せない物。ここに置いた物は git に載らない
09私用/
# 途中物。プロジェクトと一緒に消える
**/一時ファイル/
# プロジェクトに属さない途中物
10一時ファイル/
# 生成物。再生成できる
.venv/
node_modules/
__pycache__/
.DS_Store
.obsidian/
GI
  echo "  + .gitignore"
  # 4) 空の箱
  for b in $KIT_BOXES; do mkdir -p "$OUT/$b"; : > "$OUT/$b/.gitkeep"; echo "  + ${b}/.gitkeep"; done
  # 5) 運用ログの見出しだけ（1 行目は初期セットアップ席が「棚を建てた日と 3 問の答え」を書く）
  printf '# 運用ログ（運用の変更を 1 行ずつ・新しい行は末尾）\n\n' > "$OUT/docs/_Operations-Log.md"; echo "  + docs/_Operations-Log.md（見出しだけ）"
  # 門: 出力の全ファイルに固有値の検査を当てる
  echo "== 門: check-distributable（出力の全ファイル）"
  local files; files=$(find "$OUT" -type f -not -name '.gitkeep' | sort)
  # shellcheck disable=SC2086
  bash "$GATE" $files || rc=1
  [ $rc = 0 ] && echo "✅ 器は配れる（固有値 0 件・落とした物 0）" || echo "🚨 配れない（上の 🚨／❌ を直す）"
  return $rc
}

# ---------- --selftest ----------
selftest() {
  local t; t=$(mktemp -d) || exit 2
  local kit="$t/kit"
  step() { echo "🔬 $*"; }
  step "1 素の切り出し"; bash "$0" "$kit" > "$t/cut.log" 2>&1 || { cat "$t/cut.log"; die "selftest: 切り出しが exit 0 にならない"; }
  step "2 drift（雛形の骨）"; bash "$0" --drift || die "selftest: 雛形が生きている紙とずれている"
  step "3 fill（{名前} を埋める・冪等）"
  bash "$0" --fill "$kit" 名前=検体 呼ばれ方=主君 事業名=検体商店 棚の名前=検体の棚 棚の置き場="$kit" "git remote=検体remote" > /dev/null || die "selftest: fill が落ちた"
  grep -rlE '\{(名前|呼ばれ方|事業名|棚の名前|棚の置き場|git remote)\}' "$kit" --include='*.md' && die "selftest: fill の後に穴が残った"
  bash "$0" --fill "$kit" 名前=検体 > /dev/null || die "selftest: fill を 2 回撃つと落ちる（冪等でない）"
  step "4 空の git リポで道具が走る"
  ( cd "$kit" && git init -q && git config core.hooksPath scripts/git-hooks ) || die "selftest: git init"
  mkdir -p "$t/sched"
  ( cd "$kit" && SCHEDULER_DIR="$t/sched" python3 scripts/build_scope_progress.py 2> "$t/gen.err" ) || { cat "$t/gen.err"; die "selftest: build_scope_progress.py が落ちた"; }
  [ -s "$kit/docs/SCOPE_PROGRESS.md" ] || die "selftest: docs/SCOPE_PROGRESS.md が書かれていない"
  ( cd "$kit" && python3 scripts/kiroku.py box --slug 2000-01-01-検体 --title 検体 --state 起案 --owner 初期セットアップ席 --absorb なし > /dev/null ) || die "selftest: kiroku.py box が落ちた"
  ( cd "$kit" && python3 scripts/kiroku.py --check 07プロジェクト > /dev/null ) || die "selftest: kiroku.py --check が正しい箱で落ちる"
  step "5 門の正の対照（正しい物を stage して pre-commit が通る）"
  ( cd "$kit" && git add -- CLAUDE.md .gitignore .claude/rules/規矩.md .claude/rules/メモリシステム.md .claude/rules/主君.md docs/定期便-手順/SCOPE_PROGRESSの生成.md docs/SCOPE_PROGRESS.md 07プロジェクト/2000-01-01-検体/status.md \
      && sh scripts/git-hooks/pre-commit ) || die "selftest: 正しい物で pre-commit が落ちる（門が壊れている）"
  step "6 門の負制御 A（語彙外の state で pre-commit が落ちる）"
  mkdir -p "$kit/07プロジェクト/2000-01-02-悪い箱"
  printf -- '---\ntitle: 悪い箱\nstate: 未着手\nowner: x\nask: \nlever: \nuntil: \nresume: \nnext: \nabsorb: x\ndue: \ntmp_ttl: \nupdated: 2000-01-02\n---\n# 悪い箱\n' > "$kit/07プロジェクト/2000-01-02-悪い箱/status.md"
  if ( cd "$kit" && git add -- 07プロジェクト/2000-01-02-悪い箱/status.md && sh scripts/git-hooks/pre-commit > /dev/null 2>&1 ); then
    echo "🚨 selftest: 語彙外の state なのに pre-commit が通った（門が死んでいる）"; rm -rf "$t"; exit 3
  fi
  step "7 門の負制御 B（固有値を入れて check-distributable が落ちる）"
  local bad; bad="/Use""rs/someone/Desk""top/thing"   # 検体はこの道具自身が門に当たらないよう割って作る
  printf '\n- 検体（固有値）: %s\n' "$bad" >> "$kit/CLAUDE.md"
  if bash "$GATE" "$kit/CLAUDE.md" > /dev/null 2>&1; then
    echo "🚨 selftest: 固有値を入れたのに門が通った（門が死んでいる）"; rm -rf "$t"; exit 3
  fi
  rm -rf "$t"
  echo "✅ selftest: 切り出し・drift・fill・生成器・kiroku・正の対照・負制御 A/B が全部通った"
  exit 0
}

case "${1:-}" in
  --selftest) selftest ;;
  --drift) drift ;;
  --fill) shift; fill "$@" ;;
  "") sed -n '2,20p' "$0"; exit 2 ;;
  *) cut "$1" ;;
esac
