#!/bin/sh
# 写し: 正本は中の OS の scripts/houtou_patrol_check.sh（運営の棚）・器のこれは配るための写し。正本を直した席が同じ日に正本をそのまま写し直す（この 1 行だけが違う）・会員へは次の公開で届く
# 龐統の見回り（@龐統 の本文「巡回」・予約の check）: 席を起こす周だけ exit 0。1＝起こさない・2＝測れない。
# 使い方: sh houtou_patrol_check.sh <箱の在る棚（本陣）のルートか mirror clone>   ⛔ 棚は読むだけ（書かない・pull しない・作業木に触らない）
#   予約の check は起動子 houtou_patrol_launch.sh を撃つのが既定（起動子が毎周 台本の main からこのファイルを取り出して撃つ）。
#   試験: python3 scripts/test_houtou_patrol_check.py（器の側・偽の台帳・偽の tmux・写しの棚で陽性と陰性の対照を撃つ）
# 🔑 運営では中の OS の scripts/ のこれが正本・器（CTO の scripts/）は配るための写しで 1 バイトも違えない。器だけの置き場では器のこれが正本（起動子が CTO の main から取り出して撃つ）。
#   2026-11-09 に会員の差分 n137 と突き合わせて 1 本にした（龐統が居れば 1 行送る・居なければ 1 周だけ立て直しの席を起こす、は 10-18 の孔明の裁きのまま）。
# 数える物（08プロジェクト/*/status.md の frontmatter）:
#   開いた箱 N＝state が 起案 か 実行中
#   配る物 M＝開いた箱のうち、起案・owner が空・手番の『誰が』が 席（着手待ち）のどれか＝席の付いていない在庫（本文「配車」）
# 起こす周: ①開いた箱の並び（道・state・owner・手番の行）が前回と違う ②開いた箱が在る限り、前に起こしてから 15 分（HOUTOU_EVERY 秒）
#   開いた箱が 0 なら起こさない（指紋だけ控える＝次に 1 箱現れた周で起こす）
# 起こす周は、常駐の龐統が生きているかを 2 つで測る（本文「巡回」の 2 つ）:
#   ① 席の台帳（monster-orchestrator の state.json）に、常駐の印 $D/resident の short_id の行が running で在る
#   ② その行の tmux_socket（台帳が持つ絶対の道）の tmux に、その行の席（=名前の完全一致）が在り、窓の中で claude（node）が動いている
#      🩸 pgid の先頭の番号では測らない: 先頭のプロセスが先に死ぬと、同じ番号が席の中の短命なプロセスに使い回される（2026-11-09 実測・
#         生きた常駐の pgid の先頭が 9 日後に別の起動時刻のプロセスだった）。🩸 TMUX_TMPDIR を推さない: launchd の下ではずれる＝台帳の道を -S で渡す
#   居る → 「【巡回便・開いた箱 N・配る物 M】」の 1 行を send_to_seat.sh で常駐へ送り exit 1（予約の席は立てない）。送れない＝exit 2（指紋も時刻も控えない＝次の周に送り直す）
#          受け取りの印は待たない（HOUTOU_RECEIPT_WAIT 秒・既定 0＝印なしの 3 も送れたに数える＝scheduler の上限 60 秒を超えない）
#   居ない → exit 0。1 行目「【巡回便・立て直し・常駐の龐統 <旧ID> が死んでいる（理由）…】」が予約の席（@龐統）へ渡る＝その席が常駐を 1 体立て直す（本文「起動したら」）
#          立て直しの席が走っている 30 分（HOUTOU_REVIVE 秒）は 2 体目を起こさない（2026-10-18 龐統が 2 体の裁き）
#   測れない（台帳が読めない・tmux に届かない）→ exit 2（⛔ 測れないまま 2 体目の龐統を立てない）
# 保護フォルダ（デスクトップ・書類・ダウンロード・iCloud）の下の棚は理由を 1 行出して exit 2（launchd から読むと git が戻らない＝mirror を state の下に置け）
# 棚に remote が無ければ作業木そのものを読む・在ればその本線を読む。取り込みは 20 秒で打ち切る（打ち切っても止めない＝手元の本線を読む）
# 送る道具: HOUTOU_SEND ＞ 台本の git（HOUTOU_SCRIPTS_GIT・起動子が渡す）の本線（clone は origin/main・mirror は main）から取り出した物 ＞ このファイルの隣
# 状態は ${HOUTOU_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/houtou-patrol}（resident＝常駐の short_id（常駐が起動時に書く）・last_fp・last_wake・reviving・sent.tsv）
# 試しの口: HOUTOU_NOW（今の epoch）・HOUTOU_NOFETCH=1・HOUTOU_MONSTERS_STATE（台帳）・HOUTOU_TMUX（tmux）・HOUTOU_SEND（送る道具）
R="$1"
[ -n "$R" ] && [ -d "$R" ] || { echo "棚のルートが無い（${R:-引数なし}）" >&2; exit 2; }
RP=$(cd "$R" && pwd -P) || exit 2
HP=$(cd "$HOME" 2>/dev/null && pwd -P); HP=${HP:-$HOME}
for P in "$HP/Desktop" "$HP/Documents" "$HP/Downloads" "$HP/Library/Mobile Documents"; do
  case "$RP/" in "$P/"*) echo "棚が保護フォルダ（${P#"$HP"/}）の下に在る＝launchd から読むと git が戻らない。保護フォルダの外に置いた mirror を渡せ（${RP}）" >&2; exit 2;; esac
done
D="${HOUTOU_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/houtou-patrol}"; mkdir -p "$D" || exit 2
REMOTE=$(/usr/bin/git -C "$R" config --get branch.main.remote 2>/dev/null); [ -n "$REMOTE" ] || REMOTE=origin
B=$(/usr/bin/git -C "$R" symbolic-ref -q --short "refs/remotes/$REMOTE/HEAD" 2>/dev/null); B=${B#"$REMOTE"/}; B=${B:-main}
if /usr/bin/git -C "$R" remote get-url "$REMOTE" >/dev/null 2>&1; then
  [ -n "${HOUTOU_NOFETCH:-}" ] || GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10" GIT_TERMINAL_PROMPT=0 \
    /usr/bin/perl -e 'alarm 20; exec @ARGV' /usr/bin/git -C "$R" fetch -q "$REMOTE" "$B" >/dev/null 2>&1 || true
  REF=$REMOTE/$B; /usr/bin/git -C "$R" rev-parse -q --verify "$REF" >/dev/null || REF=$B
  /usr/bin/git -C "$R" rev-parse -q --verify "$REF" >/dev/null || { echo "棚の本線（${REF}）が読めない" >&2; exit 2; }
elif [ "$(/usr/bin/git -C "$R" rev-parse --is-bare-repository 2>/dev/null)" = false ]; then
  REF=:wt
else
  echo "棚が git の作業木でない（${R}）" >&2; exit 2
fi
OUT=$(python3 - "$R" "$REF" <<'PY'
import glob, hashlib, os, re, subprocess, sys
r, ref = sys.argv[1], sys.argv[2]
def g(*a, inp=None):
    p = subprocess.run(["git", "-c", "core.quotepath=off", "-C", r, *a], input=inp, capture_output=True)
    if p.returncode: sys.exit(2)
    return p.stdout
texts = []
if ref == ":wt":
    for x in sorted(glob.glob(os.path.join(r, "08プロジェクト", "*", "status.md"))):
        try: texts.append((os.path.relpath(x, r), open(x, encoding="utf-8").read()))
        except OSError: sys.exit(2)
else:
    paths = sorted(p for p in g("ls-tree", "-r", "--name-only", ref, "--", "08プロジェクト/").decode().split("\n")
                   if re.fullmatch(r"08プロジェクト/[^/]+/status\.md", p))
    # 中身は cat-file --batch 1 本でまとめて読む（launchd の下は子の起動が絞られる）
    out = g("cat-file", "--batch", inp="".join(f"{ref}:{p}\n" for p in paths).encode()) if paths else b""
    i = 0
    for p in paths:
        j = out.index(b"\n", i); head = out[i:j].split(); i = j + 1
        if len(head) < 3 or head[1] != b"blob": continue
        size = int(head[2]); texts.append((p, out[i:i + size].decode("utf-8", "replace"))); i += size + 1
items, n, m = [], 0, 0
for p, text in texts:
    fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not fm: continue
    f = lambda k: (re.search(rf"^{k}:[ \t]*(.*)$", fm.group(1), re.M) or [None, ""])[1].strip()
    state, owner, teban = f("state"), f("owner"), f("手番")
    if state not in ("起案", "実行中"): continue
    n += 1
    if state == "起案" or not owner or re.split(r"[｜|]", teban)[0].strip() == "席": m += 1
    items.append("\t".join([p, state, owner, hashlib.sha1(teban.encode()).hexdigest()[:8]]))
print(hashlib.sha1("\n".join(items).encode()).hexdigest(), n, m)
PY
) || { echo "棚の箱が読めない（${REF}）" >&2; exit 2; }
set -- $OUT; H=$1; N=$2; M=$3
[ -n "$M" ] || exit 2
NOW=${HOUTOU_NOW:-$(date +%s)}; LAST_H=$(cat "$D/last_fp" 2>/dev/null); LAST_T=$(cat "$D/last_wake" 2>/dev/null); case "$LAST_T" in ''|*[!0-9]*) LAST_T=0;; esac
if [ "$N" -eq 0 ]; then echo "$H" > "$D/last_fp"; exit 1; fi
if [ "$H" != "$LAST_H" ]; then WHY="変化あり"
elif [ $((NOW-LAST_T)) -ge "${HOUTOU_EVERY:-900}" ]; then WHY="$(( ${HOUTOU_EVERY:-900} / 60 )) 分ぶり"
else exit 1; fi
T=${HOUTOU_TMUX:-$(command -v tmux 2>/dev/null)}
for c in /opt/homebrew/bin/tmux /usr/local/bin/tmux /usr/bin/tmux; do [ -n "$T" ] || { [ -x "$c" ] && T=$c; }; done
# 常駐の生死。1 行目＝居る／居ない／測れない・2 行目＝理由か tmux の席の名・3 行目＝tmux_socket・4 行目＝常駐の short_id
LIVE=$(python3 - "$D/resident" "$T" <<'PY'
import json, os, re, subprocess, sys
def live():
    try: sid = open(sys.argv[1], encoding="utf-8").read().split()[0]
    except (OSError, IndexError): return "居ない", "常駐の印（resident）が無い"
    if not re.fullmatch(r"[0-9a-f]{8}", sid): return "居ない", "常駐の印が short_id の形でない"
    st = os.environ.get("HOUTOU_MONSTERS_STATE") or os.path.expanduser("~/.claude/monsters/state.json")
    if not os.path.exists(st): return "居ない", "席の台帳が無い"
    try:
        ms = json.load(open(st, encoding="utf-8"))["monsters"]
        rows = [x for x in (ms.values() if isinstance(ms, dict) else ms) if isinstance(x, dict)]
    except Exception as e:
        return "測れない", "席の台帳が読めない（%s）" % type(e).__name__
    row = next((x for x in rows if str(x.get("short_id") or "") == sid or str(x.get("id") or "").startswith(sid)), None)
    if row is None: return "居ない", "台帳に %s の行が無い" % sid
    if row.get("status") != "running": return "居ない", "台帳の %s が %s" % (sid, row.get("status"))
    sess = str(row.get("tmux_session") or "monster-" + sid); sock = str(row.get("tmux_socket") or "")
    if not sock: return "測れない", "台帳の %s に tmux_socket が無い" % sid
    if not os.path.exists(sock): return "居ない", "%s の tmux（%s）が無い" % (sid, sock)
    if not sys.argv[2]: return "測れない", "tmux が見つからない"
    env = {k: v for k, v in os.environ.items() if k != "TMUX"}
    def tm(*a):
        return subprocess.run([sys.argv[2], "-S", sock, *a], capture_output=True, text=True, timeout=10, env=env)
    try:
        p = tm("has-session", "-t", "=" + sess)
        if p.returncode:
            if "can't find session" in p.stderr: return "居ない", "%s の席（%s）が tmux に無い" % (sid, sess)
            return "測れない", "tmux に届かない（%s）" % (p.stderr.strip()[:80] or "rc=%d" % p.returncode)
        cmd = tm("display", "-p", "-t", "=" + sess + ":", "#{pane_current_command}").stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return "測れない", "tmux が撃てない（%s）" % type(e).__name__
    if not (cmd in ("node", "claude") or cmd.startswith("bluelamp")):
        return "居ない", "%s の窓で claude が動いていない（%s）" % (sid, cmd or "空")
    return "居る", sess, sock, sid
print("\n".join(live()))
PY
)
{ read -r A; read -r WHAT; read -r SOCK; read -r SID; } <<EOF
$LIVE
EOF
MSG="開いた箱 ${N}・配る物 ${M}"
case "$A" in
  居る)
    rm -f "$D/reviving"
    SEND=${HOUTOU_SEND:-}
    if [ -z "$SEND" ] && [ -n "${HOUTOU_SCRIPTS_GIT:-}" ] && \
       { SREF=origin/main; /usr/bin/git --git-dir="$HOUTOU_SCRIPTS_GIT" rev-parse -q --verify "refs/remotes/$SREF" >/dev/null 2>&1 || SREF=main; } && \
       /usr/bin/git --git-dir="$HOUTOU_SCRIPTS_GIT" show "$SREF:scripts/send_to_seat.sh" > "$D/send_to_seat.sh.tmp" 2>/dev/null && [ -s "$D/send_to_seat.sh.tmp" ]; then
      mv "$D/send_to_seat.sh.tmp" "$D/send_to_seat.sh"; SEND="$D/send_to_seat.sh"   # launchd は保護フォルダの道具を読めない＝台本の mirror から取り出す
    fi
    rm -f "$D/send_to_seat.sh.tmp"
    [ -n "$SEND" ] || SEND="$(dirname "$0")/send_to_seat.sh"
    [ -f "$SEND" ] || { echo "送る道具が無い（${SEND}）" >&2; exit 2; }
    TD=""; case "$SOCK" in */tmux-*/*) TD=${SOCK%/tmux-*};; esac
    printf '【巡回便・%s】（%s）巡回を 1 周回せ（本文「巡回」の 0〜5）。\n' "$MSG" "$WHY" | sh "$SEND" ${TD:+-d "$TD"} -t "$T" -w "${HOUTOU_RECEIPT_WAIT:-0}" "$WHAT" - >/dev/null 2>&1
    rc=$?
    printf '%s\t%s\t送った rc=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$SID" "$rc" >> "$D/sent.tsv"
    [ "$rc" -eq 0 ] || [ "$rc" -eq 3 ] || { echo "常駐の龐統（${WHAT}）へ送れない（send_to_seat rc=${rc}）＝次の周に送り直す" >&2; exit 2; }
    echo "$H" > "$D/last_fp"; echo "$NOW" > "$D/last_wake"
    exit 1;;
  居ない)
    echo "$H" > "$D/last_fp"; echo "$NOW" > "$D/last_wake"
    RV=$(cat "$D/reviving" 2>/dev/null); case "$RV" in ''|*[!0-9]*) RV=0;; esac
    [ $((NOW-RV)) -lt "${HOUTOU_REVIVE:-1800}" ] && exit 1   # 立て直しの席が走っている間は 2 体目を起こさない
    echo "$NOW" > "$D/reviving"
    RES=$(cat "$D/resident" 2>/dev/null | head -1)
    # 🔑 席へ渡るのは 1 行目だけ（scheduler が check の出力の 1 行目を task に付ける）
    echo "【巡回便・立て直し・常駐の龐統 ${RES:-（記録なし）} が死んでいる（${WHAT}）・${MSG}】この席が常駐の龐統を 1 体立てて監督を付け替えよ（本文「起動したら」）"
    exit 0;;
  *) echo "龐統の生死を測れない（${WHAT:-生死の段が落ちた}）＝起こさない" >&2; exit 2;;
esac
