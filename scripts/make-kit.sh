#!/bin/bash
# make-kit.sh — 生きている棚から「器だけ」を切り出す 1 本（AOS設置が撃つ）。
#
# 🔑 何を配るか: 地図（CLAUDE.md）・規則の紙 3 枚（.claude/rules/・固有値は {名前} の穴）・空の箱（.gitkeep。README を置いた 3 箱だけ .gitkeep なし）・
#   道具（scripts/ の固定リスト・git-hooks/・kit-ingest/・sms/）・.gitignore・docs/SCOPE_PROGRESS.md の芯 1 枚。**中身は 1 行も入れない**（規矩 X-7）。
#   docs/SCOPE_PROGRESS.md は「8 節の見出しと『まだ作られていません』の 1 行」だけの芯を入れる（⛔ 空の紙にしない＝「全体像」と名乗って何も言わない紙は嘘になる）。
#   中身は生成器が最初に撃たれたとき（`python3 scripts/build_scope_progress.py`）にまるごと書き直す。
#   ⛔ docs/定期便-手順/ は配らない（2026-09-20 主君裁定「便という種類をやめて席に一本化する」で箱ごと畳んだ。
#      中身＝全体像の作り方は AOS設置 §5 と 孔明の起動の手へ、走った記録の書き方は メモリシステム「記録は、どこに書くか」へ継いだ）。
# 🔑 雛形の置き場: scripts/kit/（生きている紙から固有値・件数・日付つきの社内事故を抜いた写し）。雛形も出力に入れる（建てた棚が自分で門を撃ち、次の棚を切り出せる）。
#   写しは腐るので **--drift** が門: 規矩の X・H（雛形は生きている紙の部分集合・番号は連番）・帳簿の列・領域 8 語・種別・層、箱の state 8 語 が
#   生きている紙（.claude/rules/・scripts/kiroku.py）と一致しなければ exit 1。--selftest はこれも撃つ。
#
# 使い方:
#   bash scripts/make-kit.sh <出力先>                       出力先は空か存在しない dir。門（固有値 0 件）を通れば exit 0
#   bash scripts/make-kit.sh --fill <棚> 名前=… 呼ばれ方=… 事業名=… 棚の名前=… 棚の置き場=… "git remote=…"
#                                                          雛形の {名前} を埋める（冪等。無い穴は何もしない。埋めない穴は残る）
#                                                          ⛔ 埋めるのは「その人の棚の紙」だけ。scripts/ 配下（道具自身と scripts/kit/ の雛形の写し）には触れない
#                                                             （触れると次の切り出しと --selftest の門が固有値で落ちる＝2026-09-20 通しテスト §2-6）
#   bash scripts/make-kit.sh --drift                        雛形と生きている紙の骨が一致するか（exit 0/1）
#   bash scripts/make-kit.sh --numbers <道…>                 配る物が指す X-n・H-n・§n が雛形の規矩に実在するか（exit 0/1）
#   bash scripts/make-kit.sh --selftest                     空の一時 git リポに切り出して門を全部撃つ。exit 0＝合格／1＝壊れている／3＝負制御が落ちなかった
#                                                          ffprobe が無い機体では 4-2（引き上げの門の selftest）だけ ⏭ で飛ばす（初日に動画は無い。飛ばした事実は 1 行出す）
#
# ⚠️ bash 3.2（macOS 既定）は "$f（" の全角を変数名に取り込む。日本語の前の変数は必ず ${f} で囲む
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KIT="$ROOT/scripts/kit"
GATE="$ROOT/scripts/check-distributable.sh"

# ============================== 配る物（固定リスト。`scripts/*` を舐めない）==============================
# 当社固有の生成器（course/・register/・経理/・mirror_*.py・build_distribution_ledgers.py ほか）は入れない。足すならここに 1 行
KIT_TOOLS="kiroku.py build_scope_progress.py build_agent_aliases.py check-distributable.sh make-kit.sh"
KIT_HOOKS="pre-commit-secret.sh pre-commit-pii.sh pre-commit-deadpath.sh pre-commit-box.sh"
# 資産の引き上げ席が呼ぶ道具（下の 2 行で合わせて 10 本＝kit-ingest 9 ＋ sms 1。無いとその席は配っても最初の門で止まる）
KIT_INGEST="verify_complete.py fetch_one.py transcribe_loop.py drive_put.py build_ledger.py manifest_add.py inventory_youtube.py verify_cards.py gate.py"
KIT_SMS="read_code.sh"
KIT_BOXES="00廷議 01商品資産 02マーケティング資産 03セールス資産 04オペレーション資産 05バックオフィス資産 06エージェント資産 06エージェント資産/_便 06エージェント資産/_孔明起動 07学習資産 08プロジェクト
09アーカイブ/案件 09アーカイブ/裁定 09アーカイブ/コンテクスト銀行 10私用 11一時ファイル"
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
# ⛔ scripts/ 配下は埋めない: 道具のコメントに書かれた {名前} と scripts/kit/ の雛形の写しは「穴のまま」が正しい
#   （埋めると check-distributable が固有値と数え、建てた棚の --selftest と次の切り出しが落ちる）。飛ばした事実は 1 行出す
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
SKIP_DIRS = (".git", "scripts")
for d, ds, fs in os.walk(out):
    if d == out:
        for sd in SKIP_DIRS:
            if sd in ds: ds.remove(sd); print(f"  \u23ed {sd}/ は埋めない（{'道具と雛形の写し' if sd == 'scripts' else 'git の中身'}）")
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
  # 1) 雛形（地図・規則 3 枚・全体像の芯 1 枚・箱の README 3 枚）
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
  for b in $KIT_INGEST; do
    [ -f "scripts/kit-ingest/$b" ] || { echo "  🚨 scripts/kit-ingest/${b} が無い（リストと現物がずれている）"; rc=1; continue; }
    maybe_copy "scripts/kit-ingest/$b" "scripts/kit-ingest/$b" || rc=1
  done
  for b in $KIT_SMS; do
    [ -f "scripts/sms/$b" ] || { echo "  🚨 scripts/sms/${b} が無い（リストと現物がずれている）"; rc=1; continue; }
    maybe_copy "scripts/sms/$b" "scripts/sms/$b" || rc=1
  done
  # pre-commit の親は書き下ろす（生きている方は当社固有の門を 1 本余分に撃つため）
  cat > "$OUT/scripts/git-hooks/pre-commit" <<'SH'
#!/bin/sh
# pre-commit（配線: git config core.hooksPath scripts/git-hooks）
# 4 本を順に撃つ。1 本でも落ちたら commit しない。強行は --no-verify
#   秘密（鍵・接続文字列）／PII（口座・カード・個人番号）／死んだ参照（改訂される紙が指す実在しないパス）／箱（08プロジェクト/ の status.md が語彙表に合うか）
D=$(dirname "$0"); FAIL=0
for h in pre-commit-secret.sh pre-commit-pii.sh pre-commit-deadpath.sh pre-commit-box.sh; do sh "$D/$h" || FAIL=1; done
exit $FAIL
SH
  chmod +x "$OUT"/scripts/git-hooks/* "$OUT"/scripts/*.sh "$OUT"/scripts/sms/*.sh; echo "  + scripts/git-hooks/pre-commit（書き下ろし）"
  # 3) .gitignore
  cat > "$OUT/.gitignore" <<'GI'
# 見せない物。ここに置いた物は git に載らない
10私用/
# 途中物。プロジェクトと一緒に消える
**/一時ファイル/
# プロジェクトに属さない途中物
11一時ファイル/
# 生成物。再生成できる
.venv/
node_modules/
__pycache__/
.DS_Store
.obsidian/
GI
  echo "  + .gitignore"
  # 4) 空の箱
  # 雛形が README を置いた箱（06エージェント資産 とその下の 2 箱）は README が git に載せる ⇒ .gitkeep を足さない
  for b in $KIT_BOXES; do
    mkdir -p "$OUT/$b"
    if [ -n "$(ls -A "$OUT/$b" 2>/dev/null)" ]; then echo "  = ${b}/（README 在り・.gitkeep なし）"
    else : > "$OUT/$b/.gitkeep"; echo "  + ${b}/.gitkeep"; fi
  done
  # 5) ⛔ 運用ログ（docs/_Operations-Log.md）は配らない（2026-09-20 主君裁定）。
  #   同じ物を帳簿が持てる（領域＝棚・種別＝判定）。紙は書く人が居なくなると止まり、止まったことに誰も気づかない。
  # 門: 出力の全ファイルに固有値の検査を当てる
  echo "== 門: check-distributable（出力の全ファイル）"
  local files; files=$(find "$OUT" -type f -not -name '.gitkeep' | sort)
  # shellcheck disable=SC2086
  bash "$GATE" $files || rc=1
  [ $rc = 0 ] && echo "✅ 器は配れる（固有値 0 件・落とした物 0）" || echo "🚨 配れない（上の 🚨／❌ を直す）"
  return $rc
}

# ---------- --numbers: 配る物が指す番号が雛形の規矩に実在するか ----------
# 🔑 --drift は「雛形 ⊆ 生きている紙」しか見ない ⇒ 主君が器から行を落として番号を振り直した後、
#   生きている側の番号で書いた配る紙は、会員の棚では別の行を指す（2026-09-20 に 8 箇所で実際に起きた）。
numbers() {
  [ $# -gt 0 ] || die "--numbers <道…>（ファイルか dir）" 2
  python3 - "$KIT/.claude/rules/規矩.md" "$@" <<'PY'
import os, re, sys
tmpl, targets = sys.argv[1], sys.argv[2:]
ID_RE   = re.compile(r"^\|\s*[*`]*\s*([XH]-\d+'?)\s*[*`]*\s*\|")
HEAD_RE = re.compile(r"^#{1,6}\s+(.*)$")
NUM_RE  = re.compile(r"§?\s?(\d+(?:-[0-9A-Za-z]+)?)")
REF_ID  = re.compile(r"(?<![0-9A-Za-z])([XH]-\d+'?)")
REF_SEC = re.compile(r"§\s?(\d+(?:-[0-9A-Za-z]+)?)")
def parents(n): return {n, n.split("-")[0]} if "-" in n else {n}
def anchors(lines, heads_only):
    ids, secs = set(), set()
    for l in lines:
        m = HEAD_RE.match(l)
        if m:
            for n in NUM_RE.findall(m.group(1)): secs |= parents(n)
        if not heads_only:
            m = ID_RE.match(l)
            if m: ids.add(m.group(1))
    return ids, secs
def read(p): return open(p, encoding="utf-8").read().splitlines()
t_ids, t_secs = anchors(read(tmpl), False)
if not t_ids or not t_secs:
    print(f"🚨 雛形の規矩から番号を拾えなかった: {tmpl}"); sys.exit(1)
# 🔑 README は「器に無い番号」を名前で挙げる説明文なので、検査すると必ず誤検出になる。
#   ⛔ 撃ち方を紙に書くだけでは守られない（次に撃つ席が README を読まずに *.md と撃つ）⇒ 機械で飛ばす。
#   飛ばした事実は必ず 1 行出す（黙って飛ばさない）。飛ばした結果 0 本になったら落ちる（何も検査しないのを成功と呼ばせない）。
SKIP = ("README.md",)
files, skipped = [], []
for t in targets:
    if os.path.isdir(t):
        for d, _, fs in os.walk(t):
            if "/.git" in d or d.endswith("/.git"): continue
            for f in fs:
                if not f.endswith(".md"): continue
                (skipped if f in SKIP else files).append(os.path.join(d, f))
    elif t.endswith(".md"):
        (skipped if os.path.basename(t) in SKIP else files).append(t)
files.sort()
for q in sorted(skipped):
    print(f"\u23ed {q}: README は説明文（器に無い番号を名前で挙げる紙）なので検査しない")
if not files:
    print("\U0001f6a8 番号: 検査する紙が 0 本だった（README だけを渡していないか）"); sys.exit(1)
bad = 0
for p in files:
    lines = read(p)
    _, own = anchors(lines, True)   # § は自分の節への参照にも使われる ⇒ 自分の見出しでも解決してよい
    for i, l in enumerate(lines, 1):
        for r in REF_ID.findall(l):
            if r not in t_ids:
                bad += 1; print(f"❌ {p}:{i}: 規矩 {r} は器の雛形に無い（雛形に在るのは {' '.join(sorted(t_ids))}）")
        for r in REF_SEC.findall(l):
            if r not in t_secs and r not in own:
                bad += 1; print(f"❌ {p}:{i}: §{r} はこの紙にも器の雛形の規矩にも無い")
print(f"✅ 番号: 配る物 {len(files)} 本が指す X-n・H-n・§n は全部、器の雛形の側に在る" if bad == 0
      else f"🚨 番号: {bad} 箇所が雛形に無い行を指している（配ると会員の棚で別の行を指す）")
sys.exit(1 if bad else 0)
PY
}

# ---------- --selftest ----------
selftest() {
  local t; t=$(mktemp -d) || exit 2
  local kit="$t/kit"
  step() { echo "🔬 $*"; }
  step "1 素の切り出し"; bash "$0" "$kit" > "$t/cut.log" 2>&1 || { cat "$t/cut.log"; die "selftest: 切り出しが exit 0 にならない"; }
  step "2 drift（雛形の骨）"; bash "$0" --drift || die "selftest: 雛形が生きている紙とずれている"
  step "3 fill（{名前} を埋める・冪等・scripts/ には触れない）"
  ( cd "$kit" && find scripts -type f -exec shasum {} + | sort ) > "$t/scripts.before"
  bash "$0" --fill "$kit" 名前=検体 呼ばれ方=主君 事業名=検体商店 棚の名前=検体の棚 棚の置き場="$kit" "git remote=検体remote" > /dev/null || die "selftest: fill が落ちた"
  grep -rlE '\{(名前|呼ばれ方|事業名|棚の名前|棚の置き場|git remote)\}' "$kit" --include='*.md' --exclude-dir=scripts && die "selftest: fill の後に穴が残った"
  grep -qrl '{名前}' "$kit/scripts/kit/.claude/rules" || die "selftest: fill が scripts/kit/ の雛形の写しまで埋めた（次の切り出しが固有値で落ちる）"
  ( cd "$kit" && find scripts -type f -exec shasum {} + | sort ) > "$t/scripts.after"
  cmp -s "$t/scripts.before" "$t/scripts.after" || { diff "$t/scripts.before" "$t/scripts.after"; die "selftest: fill が scripts/ 配下（道具）を書き換えた"; }
  bash "$0" --fill "$kit" 名前=検体 > /dev/null || die "selftest: fill を 2 回撃つと落ちる（冪等でない）"
  step "4 空の git リポで道具が走る"
  ( cd "$kit" && git init -q && git config core.hooksPath scripts/git-hooks ) || die "selftest: git init"
  mkdir -p "$t/sched"
  ( cd "$kit" && SCHEDULER_DIR="$t/sched" python3 scripts/build_scope_progress.py 2> "$t/gen.err" ) || { cat "$t/gen.err"; die "selftest: build_scope_progress.py が落ちた"; }
  [ -s "$kit/docs/SCOPE_PROGRESS.md" ] || die "selftest: docs/SCOPE_PROGRESS.md が書かれていない"
  ( cd "$kit" && python3 scripts/kiroku.py box --slug 2000-01-01-検体 --title 検体 --state 起案 --owner AOS設置 --absorb なし > /dev/null ) || die "selftest: kiroku.py box が落ちた"
  ( cd "$kit" && python3 scripts/kiroku.py --check 08プロジェクト > /dev/null ) || die "selftest: kiroku.py --check が正しい箱で落ちる"
  step "4-2 引き上げの門が器の中で走る（負制御こみ）"
  # 🔑 gate.py --selftest は検体の音声の尺を ffprobe で測る。素の Mac には無い＝初日に動画は無いので、この段だけ ⏭（黙って飛ばさない・道具が器に在ることは下で見る）
  if command -v ffprobe > /dev/null 2>&1; then
    ( cd "$kit" && python3 scripts/kit-ingest/gate.py --selftest > /dev/null 2>&1 ) || die "selftest: kit-ingest/gate.py --selftest が exit 0 にならない" 3
  else
    echo "⏭ ffprobe 無し: 引き上げの門の selftest（gate.py --selftest）は飛ばした。動画を引き上げる日までに ffmpeg を入れれば撃てる"
  fi
  for b in $KIT_INGEST; do
    [ -f "$kit/scripts/kit-ingest/$b" ] || die "selftest: 器に scripts/kit-ingest/${b} が入っていない"
  done
  for b in $KIT_SMS; do
    [ -x "$kit/scripts/sms/$b" ] || die "selftest: 器に scripts/sms/${b} が入っていない（か実行できない）"
  done
  step "5 門の正の対照（正しい物を stage して pre-commit が通る）"
  ( cd "$kit" && git add -- CLAUDE.md .gitignore .claude/rules/規矩.md .claude/rules/メモリシステム.md .claude/rules/主君.md docs/SCOPE_PROGRESS.md 08プロジェクト/2000-01-01-検体/status.md \
      && sh scripts/git-hooks/pre-commit ) || die "selftest: 正しい物で pre-commit が落ちる（門が壊れている）"
  step "6 門の負制御 A（語彙外の state で pre-commit が落ちる）"
  mkdir -p "$kit/08プロジェクト/2000-01-02-悪い箱"
  printf -- '---\ntitle: 悪い箱\nstate: 未着手\nowner: x\nask: \nlever: \nuntil: \nresume: \nnext: \nabsorb: x\ndue: \ntmp_ttl: \nupdated: 2000-01-02\n---\n# 悪い箱\n' > "$kit/08プロジェクト/2000-01-02-悪い箱/status.md"
  if ( cd "$kit" && git add -- 08プロジェクト/2000-01-02-悪い箱/status.md && sh scripts/git-hooks/pre-commit > /dev/null 2>&1 ); then
    echo "🚨 selftest: 語彙外の state なのに pre-commit が通った（門が死んでいる）"; rm -rf "$t"; exit 3
  fi
  step "7 門の負制御 B（固有値を入れて check-distributable が落ちる）"
  local bad; bad="/Use""rs/someone/Desk""top/thing"   # 検体はこの道具自身が門に当たらないよう割って作る
  printf '\n- 検体（固有値）: %s\n' "$bad" >> "$kit/CLAUDE.md"
  if bash "$GATE" "$kit/CLAUDE.md" > /dev/null 2>&1; then
    echo "🚨 selftest: 固有値を入れたのに門が通った（門が死んでいる）"; rm -rf "$t"; exit 3
  fi
  step "8 配る物の番号が雛形の規矩に実在する（負制御こみ）"
  numbers "$kit" || die "selftest: 器の中の紙が、雛形の規矩に無い番号を指している"
  mkdir -p "$t/nc"
  printf -- '# 負制御\n\n⛔ X-99 と §98-7 を見よ（雛形に無い番号）\n' > "$t/nc/負制御.md"
  if numbers "$t/nc" > /dev/null 2>&1; then
    echo "🚨 selftest: 雛形に無い番号（X-99・§98-7）を入れたのに番号の門が通った（門が死んでいる）"; rm -rf "$t"; exit 3
  fi
  # 負制御 D: README を飛ばすようにしたせいで、同じ箱の本物の紙のずれを見逃していないか
  mkdir -p "$t/nc2"
  printf -- '# 説明\n\nこの紙は X-99 が器に無いことを説明している\n' > "$t/nc2/README.md"
  printf -- '# 配る紙\n\n⛔ X-99 を見よ\n' > "$t/nc2/配る紙.md"
  # ⛔ 「落ちたか」だけを見てはいけない——README ごと全部飛ばして 0 本になっても落ちるので、区別がつかない。
  #   ⇒ 本物の紙の名前と番号が出力に出ていることを確かめる（🪤 2026-09-20 に実際にこれで素通りした）
  local d_out; d_out=$(numbers "$t/nc2" 2>&1)
  if ! printf '%s' "${d_out}" | grep -q '配る紙\.md:.*X-99'; then
    echo "🚨 selftest: README を飛ばしたせいで、同じ箱の本物の紙の X-99 を見逃した"; echo "${d_out}"; rm -rf "$t"; exit 3
  fi
  # 負制御 E: README しか渡されなければ「0 本を検査して合格」にしない
  mkdir -p "$t/nc3"
  printf -- '# 説明\n\nX-99 の話\n' > "$t/nc3/README.md"
  if numbers "$t/nc3" > /dev/null 2>&1; then
    echo "🚨 selftest: README だけを渡したのに合格した（0 本を検査して通っている）"; rm -rf "$t"; exit 3
  fi
  rm -rf "$t"
  echo "✅ selftest: 切り出し・drift・fill・生成器・kiroku・正の対照・負制御 A/B/C/D/E（番号・README）が全部通った"
  exit 0
}

case "${1:-}" in
  --selftest) selftest ;;
  --drift) drift ;;
  --numbers) shift; numbers "$@" ;;
  --fill) shift; fill "$@" ;;
  "") sed -n '2,19p' "$0"; exit 2 ;;
  *) cut "$1" ;;
esac
