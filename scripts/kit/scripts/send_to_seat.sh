#!/bin/sh
# 写し: 正本は中の OS の scripts/send_to_seat.sh（運営の棚）・器のこれは配るための写し。正本を直した席が同じ日に正本をそのまま写し直す（この 1 行だけが違う）・会員へは次の公開で届く
# 席（tmux の中の Claude）へ 1 通送り、受け取りの印まで見る。孔明・龐統・巡回の送り方はこの 1 本だけ（⛔ send-keys -l を手で撃たない）。
# 使い方: sh scripts/send_to_seat.sh [-s <ssh の宛先>] [-d <TMUX_TMPDIR>] [-t <tmux のフルパス>] [-w <印を待つ秒=120>] [-g <間隔の秒>] [-f] <セッション> <本文の紙|->
#         sh scripts/send_to_seat.sh --selftest [<試す send_to_seat.sh>]   （使い捨ての tmux に偽の席を立てて撃ち直しの手を試す・本物の席へは送らない）
#   -s を付けると、その機体の tmux へ撃つ（実行席の席へ指揮席から送るとき）。付けなければ自機の tmux
# 🔑 送り先の画面が view-mode／copy-mode（定刻の便の出力・人のスクロール）に入っていると、貼り付けも Enter も入力欄に届かない（箱 n=2253・n=4265）
#    ⇒ 貼る前と Enter を撃ち直す前に #{pane_in_mode} を見て、1 なら send-keys -X cancel で抜ける（3 回まで）
# 🔑 貼り付けの終わりの印（ESC [201~）が席に届かないことがある＝席は括りの貼り付けの途中のままで、後の Enter も本文の改行として飲まれ送られない
#    ⇒ Enter を撃ち直す 1 回目だけ、終わりの印を送ってから Enter（2 回目以降は Enter だけ）。撃ち直しが要らない普通の席には印を余計に送らない
# 撃ち方: load-buffer → paste-buffer -p（席が括りの貼り付けを受けるなら複数行を 1 通で渡す）→ 一呼吸 → Enter。3 秒後に入力欄（最後の ❯ の行）に本文の頭が残っていれば Enter を撃ち直す（3 回まで）
# 🔑 受け取りの印: 本文の末尾に「受け取りの印」の行（ID つき）を足す。受けた席は最初の出力の 1 行目に『受けた #<ID>』を出す
#    （両方の本文に書いてある）。画面の ❯ の行の外にその文字列が出たら受け取った。⛔ 本文が画面に見える＝届いた、ではない
#    （足す行には『受けた #<ID>』の並びそのものを書かない＝送った本文の写しを印と取り違えない）
# 🚪 間隔の門（-g <秒> を渡したときだけ・会員の差分 n=4761 束2）: 同じ宛先へ同じ 1 通（本文全体の指紋が同じ）が <秒> 以内に
#    sent.tsv に『受けた』か『印なし』で在るか、別の送り手が今まさに送っている（inflight-<鍵> の印）なら送らない＝止めるのは 2 度撃ちだけ。
#    違う本文・違う宛先は通す。『送れない』『止めた』と指紋の無い古い行（5 列）は数えない（撃ち直しは通す）。わざと同じ文を撃ち直すなら -f
#    ⛔ 頭（本文の頭 12 字）では比べない（launchd の C の locale では cut -c が バイトで切る＝頭が同じ別の文を黙って落とす）
#    -g を渡さなければ今のまま（門は眠る・rc 4 は出ない）＝呼び手が自分の撃ち直しの決まり（rc 0/3 だけを送れたと読む等）を持つ所を壊さない
# 終了: 0＝受け取りの印を見た ／ 3＝送れた（入力欄は空）が印が出ない ／ 2＝送れない（tmux が落ちた・入力欄に残った）
#       4＝送らなかった（-g の間隔の門: 同じ宛先へ同じ 1 通が <秒> 以内に在る・別の送り手が送り中）
# 記録: ${XDG_STATE_HOME:-$HOME/.local/state}/send-to-seat/sent.tsv に 1 行（時刻・宛先・ID・結果・本文の頭・送り手・本文の指紋）
#   送り手＝撃った席の tmux セッション名（tmux の外から撃ったら『不明』）。指紋＝本文全体の cksum（<CRC>-<バイト数>）。前の行は 5 列
EM=1   # 撃ち直しの 1 回目に終わりの印を送る（--selftest の陰性対照はこの行を 0 にした写しを撃つ）
if [ "${1:-}" = --selftest ]; then
  SUT=${2:-$0}
  TT=$(command -v tmux) || { echo "SKIP: tmux が無い"; exit 0; }
  command -v python3 >/dev/null || { echo "SKIP: python3 が無い（偽の席に使う）"; exit 0; }
  TD=$(mktemp -d /tmp/sts.XXXXXX)          # ソケットの道を短く保つ（長いと tmux が起きない）
  export XDG_STATE_HOME="$TD/state"
  tx() { env -u TMUX TMUX_TMPDIR="$TD" "$TT" "$@"; }
  trap 'tx kill-server 2>/dev/null; rm -rf "$TD"' EXIT
  sed 's/^EM=1 .*/EM=0/' "$SUT" > "$TD/legacy.sh"   # 直す前の手＝撃ち直しは Enter だけ
  cat > "$TD/seat.py" <<'EOF'
# 偽の席: 括りの貼り付けを受ける（ESC[?2004h）。mode=drop は最初の終わりの印を 1 度だけ落とす。届いた印と送信を log に 1 行ずつ
import codecs, os, re, sys, tty
mode, log = sys.argv[1], sys.argv[2]
tty.setraw(0)
def w(s): os.write(1, s.encode())
def note(s):
    with open(log, 'a') as f: f.write(s + '\n')
B, E = b'\x1b[200~', b'\x1b[201~'
buf, paste, dropped, data = '', False, False, b''
dec = codecs.getincrementaldecoder('utf-8')('ignore')
def show(): w('\r\x1b[K❯ ' + buf.replace('\r', ' ').replace('\n', ' '))
w('\x1b[?2004h'); show()
while True:
    c = os.read(0, 4096)
    if not c: break
    data += c
    while data:
        if data.startswith(B): paste, data = True, data[6:]; continue
        if data.startswith(E):
            data = data[6:]; note('END')
            if mode == 'drop' and not dropped: dropped = True; continue
            paste = False; continue
        if data[:1] == b'\x1b' and (B.startswith(data) or E.startswith(data)): break   # 印の途中＝続きを待つ
        i = data.find(b'\x1b', 1); chunk, data = (data, b'') if i < 0 else (data[:i], data[i:])
        for ch in dec.decode(chunk):
            if ch == '\x1b': continue
            if ch == '\r' and not paste:
                m = re.search(r'#[0-9][0-9-]*', buf); note('SUBMIT')
                w('\r\n' + ('受けた ' + m.group(0) if m else '') + '\r\n'); buf = ''
            else: buf += ch
        show()
EOF
  fail=0
  one() {  # $1=名 $2=席の mode $3=試す版 $4=期待する rc の区別（ok|ng）
    S="sts-$1"; LG="$TD/$1.log"; : > "$LG"
    tx new-session -d -s "$S" -x 200 -y 30 "python3 '$TD/seat.py' $2 '$LG'"; sleep 1
    out=$(printf 'selftest %s\n2 行目\n' "$1" | sh "$3" -d "$TD" -t "$TT" -w 15 "$S" - 2>&1); rc=$?
    ends=$(grep -c '^END$' "$LG"); subs=$(grep -c '^SUBMIT$' "$LG")
    tx kill-session -t "$S" 2>/dev/null
    echo "$1 rc=$rc 終わりの印=$ends 送信=$subs :: $out"
  }
  r=$(one drop drop "$SUT"); echo "$r"
  case "$r" in "drop rc=0 "*"送信=1 "*) echo "  OK 印を落とす席で届く";; *) echo "  NG 印を落とす席で届かない"; fail=1;; esac
  r=$(one normal normal "$SUT"); echo "$r"
  case "$r" in "normal rc=0 終わりの印=1 送信=1 "*) echo "  OK 普通の席で届く・印を余計に送らない";; *) echo "  NG 普通の席"; fail=1;; esac
  r=$(one legacy drop "$TD/legacy.sh"); echo "$r"
  case "$r" in "legacy rc=2 "*"送信=0 "*) echo "  OK 陰性対照: 直す前の手（Enter だけ）では印を落とす席に届かない";; *) echo "  NG 陰性対照が届いた＝偽の席が印を落としていない"; fail=1;; esac
  [ "$fail" = 0 ] && echo "selftest 全部 OK" || echo "selftest 落ちた"
  exit "$fail"
fi
SSH=""; TD=""; T=""; W=120; G=0; FORCE=""
while getopts s:d:t:w:g:f o; do case $o in s) SSH=$OPTARG;; d) TD=$OPTARG;; t) T=$OPTARG;; w) W=$OPTARG;; g) G=$OPTARG;; f) FORCE=1;; *) exit 2;; esac; done
shift $((OPTIND-1)); SES="$1"; SRC="$2"
[ -n "$SES" ] && [ -n "$SRC" ] || { echo "使い方: send_to_seat.sh [-s ssh] [-d TMUX_TMPDIR] [-t tmux] [-w 秒] [-g 間隔の秒] [-f] <セッション> <本文の紙|->"; exit 2; }
case "$G" in ''|*[!0-9]*) echo "-g は秒の数（${G}）"; exit 2;; esac
ID="$(date +%m%d%H%M%S)-$$"
BODY=$(if [ "$SRC" = - ]; then cat; else cat "$SRC"; fi) || exit 2
MSG=$(printf '%s\n（受け取りの印: 最初の出力の 1 行目に「受けた」と「#%s」を空白 1 つで並べて出せ）' "$BODY" "$ID")
HEAD=$(printf '%s' "$BODY" | head -n 1 | cut -c1-12)
FP=$(printf '%s' "$BODY" | cksum | awk '{ print $1 "-" $2 }')   # 受け取りの印の行（ID）を足す前の本文＝同じ 1 通なら送り手が違っても同じ
DEST="${SSH:+$SSH:}$SES"
ME=""; [ -n "${TMUX:-}" ] && ME=$(tmux display-message -p ${TMUX_PANE:+-t "$TMUX_PANE"} '#S' 2>/dev/null | head -n 1 | tr -d '\t\r')   # 送り手＝自分の tmux（-d・-s は宛先の tmux）
[ -n "$ME" ] || ME=不明
L="${XDG_STATE_HOME:-$HOME/.local/state}/send-to-seat"; mkdir -p "$L"
log() { printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$DEST" "$ID" "$1" "$HEAD" "$ME" "$FP" >> "$L/sent.tsv"; }
if [ "$G" -gt 0 ] && [ -z "$FORCE" ]; then
  # 送り中の印（mkdir は 1 人しか通らない）。殺された送り手の残りは、印を待つ秒＋5 分を過ぎたら死んだとみなす
  LK="$L/inflight-$(printf '%s\t%s' "$DEST" "$FP" | cksum | cut -d' ' -f1)"
  [ -n "$(find "$LK" -maxdepth 0 -mmin +$((W/60+5)) 2>/dev/null)" ] && rmdir "$LK" 2>/dev/null
  mkdir "$LK" 2>/dev/null || { log 止めた; echo "送らない（同じ宛先へ同じ 1 通を別の送り手が送り中: ${DEST}「${HEAD}」指紋 ${FP}・わざと撃ち直すなら -f）"; exit 4; }
  trap 'rmdir "$LK" 2>/dev/null' EXIT
  X=$(( $(date +%s) - G )); CUT=$(date -r "$X" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -d "@$X" '+%Y-%m-%dT%H:%M:%S')
  PREV=$(D="$DEST" F="$FP" C="$CUT" LC_ALL=C awk -F'\t' '$1>=ENVIRON["C"] && $2==ENVIRON["D"] && $7==ENVIRON["F"] && ($4=="受けた" || $4=="印なし") { p=$1" #"$3 } END { print p }' "$L/sent.tsv" 2>/dev/null)
  [ -n "$PREV" ] && { log 止めた; echo "送らない（同じ宛先へ同じ 1 通が ${G} 秒以内に在る: ${DEST}「${HEAD}」指紋 ${FP} ${PREV}・わざと撃ち直すなら -f）"; exit 4; }
fi
# tmux の中から撃つと ${TMUX}（今いる tmux の口）が TMUX_TMPDIR より勝ち、別の tmux の席へ届かない（試しで実測）＝-d のときは外す
PRE="T=${T:-tmux}; ${TD:+unset TMUX; export TMUX_TMPDIR='$TD';} S='$SES';"
run() { if [ -n "$SSH" ]; then ssh -o BatchMode=yes -o ConnectTimeout=8 $SSH "$PRE $1"; else /bin/sh -c "$PRE $1"; fi; }
cap() { run '"$T" capture-pane -p -J -t "$S"'; }
unmode() { run 'i=0; while [ "$("$T" display-message -p -t "$S" "#{pane_in_mode}")" = 1 ] && [ $i -lt 3 ]; do "$T" send-keys -t "$S" -X cancel; i=$((i+1)); done; :'; }
lastp() { grep '^❯' | tail -n 1; }
unmode
printf '%s' "$MSG" | run '"$T" load-buffer -b send-to-seat - && "$T" paste-buffer -p -b send-to-seat -d -t "$S" && sleep 1 && "$T" send-keys -t "$S" Enter' \
  || { log 送れない; echo "送れない（tmux が落ちた: ${SES}）"; exit 2; }
n=0
while :; do
  sleep 3
  PL=$(cap | lastp)
  case "$PL" in *"$HEAD"*) ;; *) break;; esac   # 入力欄が空か、残っているのが自分の本文でない（淡い予測の文字）なら送れた
  n=$((n+1)); [ "$n" -gt 3 ] && { log 送れない; echo "送れない（入力欄に本文が残った・Enter 3 回: ${SES}）"; exit 2; }
  unmode
  if [ "$EM" = 1 ] && [ "$n" = 1 ]; then run '"$T" send-keys -t "$S" -H 1b 5b 32 30 31 7e && sleep 1'; fi   # 終わりの印 ESC [201~
  run '"$T" send-keys -t "$S" Enter'
done
t=0
while [ "$t" -lt "$W" ]; do
  if cap | grep -v '^❯' | grep -q "受けた #$ID"; then log 受けた; echo "受けた #${ID}（${SES}）"; exit 0; fi
  sleep 5; t=$((t+5))
done
log 印なし; echo "送れたが受け取りの印が ${W} 秒出ない（#${ID}・${SES}）＝届いたと言わない"; exit 3
