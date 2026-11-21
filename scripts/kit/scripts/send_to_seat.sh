#!/bin/sh
# 写し: 正本は中の OS の scripts/send_to_seat.sh（運営の棚）・器のこれは配るための写し。正本を直した席が同じ日に正本をそのまま写し直す（この 1 行だけが違う）・会員へは次の公開で届く
# 席（tmux の中の Claude）へ 1 通送り、受け取りの印まで見る。孔明・龐統・巡回の送り方はこの 1 本だけ（⛔ send-keys -l を手で撃たない）。
# 使い方: sh scripts/send_to_seat.sh [-s <ssh の宛先>] [-d <TMUX_TMPDIR>] [-t <tmux のフルパス>] [-w <印を待つ秒=120>] [-g <間隔の秒>] [-f] <セッション> <本文の紙|->
#         sh scripts/send_to_seat.sh --check <ID>   （終了 3 の後で、相手が受けたかを本文の指紋で測り直す・送らない＝下の ④）
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
# 🔑 届いたの数え方（箱 n=5121）: 印を待つ間、次のどれかを見たら届いた（終了 0）。どれで見たかを出力と記録に書く
#    ① 受けた: 画面に『受けた #<ID>』。見える画面だけでなく履歴（-S -<HL> 行）まで遡る＝印の後に相手の出力で画面の外へ流れても拾う
#    ② 順番待ち: 相手が仕事中で、本文が順番待ちに積まれた（画面の自分の #<ID> の行の下に『Queued』が出る）。
#       印は相手の仕事が終わるまで出ないので、待たずに届いたと返す（撃ち直さない＝2 度届かせない）
#    ③ 記録あり: 相手の受け取りの記録（monster の hook が events.log の user_prompt に載せる本文の指紋 prompt_norm_sha256）に
#       送った本文の指紋が在る。印が窓の内に出なくても、相手の会話には入っている（orchestrator の verified_by=fingerprint と同じ型）
#    🩸 2026-11-17 会員の知らせ（2 日で 8 通）と同日の検体: 仕事中の席へ送ると本文の下に『Queued』が出て相手は受けていたのに、
#       見える画面だけを 120 秒読んで終了 3 を返していた。⛔ 本文が画面に見える＝届いた、ではない（①②③はどれも相手の側の証拠）
# 🔑 ④ 後で測る（n=5253 会員の頼み）: 終了 3 でも相手は後で受けていることがある（窓を過ぎてから仕事を終えて読む・印を出し忘れる）。
#    送った本文の指紋（③と同じ prompt_norm_sha256）を sent.tsv の 8 列目に残し、--check <ID> がその指紋を受け手の記録で測り直す
#    （0＝記録に在る／3＝無い／2＝測れない: ID が無い・指紋の無い古い行・python3 が無い）。測り方は③の recorded() をそのまま使う
# 🔑 本文の頭（記録・入力欄に残ったかの照合）は文字で 12 字に切る（n=5253）: cut -c は macOS の C の locale（launchd）・GNU で バイトで切り、
#    日本語の 1 字を割る＝sent.tsv が壊れ、UTF-8 で照合する sh（zsh 等）では入力欄に残った本文を見落として送れたと読んだ。
#    python3 で UTF-8 として読んで切る（LC_ALL に依らない）。python3 が無い機体だけ今の cut -c
# 終了: 0＝届いた（①②③のどれか）／ 3＝送れた（入力欄は空）が①②③のどれも出ない ／ 2＝送れない（tmux が落ちた・入力欄に残った）
#       4＝送らなかった（-g の間隔の門: 同じ宛先へ同じ 1 通が <秒> 以内に在る・別の送り手が送り中）
# 記録: ${XDG_STATE_HOME:-$HOME/.local/state}/send-to-seat/sent.tsv に 1 行（時刻・宛先・ID・結果・本文の頭・送り手・本文の指紋・受け手の記録の指紋）
#   結果＝受けた／順番待ち／記録あり／印なし／送れない／止めた
#   送り手＝撃った席の tmux セッション名（tmux の外から撃ったら『不明』）。指紋＝本文全体の cksum（<CRC>-<バイト数>）。前の行は 5 列
#   受け手の記録の指紋＝③④が測る prompt_norm_sha256 の頭 16 桁（python3 が無ければ空）。前の行は 7 列＝--check は測れない（2）
EM=1   # 撃ち直しの 1 回目に終わりの印を送る（--selftest の陰性対照はこの行を 0 にした写しを撃つ）
HL=3000   # 印を探すとき遡る履歴の行数（0＝見える画面だけ＝直す前の手。--selftest の陰性対照が 0 にする）
QW=1      # 順番待ち（②）と受け手の記録（③）でも届いたと数える（0＝直す前の手。--selftest の陰性対照が 0 にする）
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
ev = sys.argv[3] if len(sys.argv) > 3 else ''
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
                if ev:   # monster の hook の写し: 本文の指紋を events の user_prompt に載せる
                    import hashlib, json
                    n = re.sub(r'\s+', '', re.sub(r'</?pasted_content\b[^>]*>', '', buf))
                    with open(ev, 'a') as f: f.write(json.dumps({'event': 'user_prompt', 'meta': {'prompt_norm_sha256': hashlib.sha256(n.encode()).hexdigest()[:16]}}, separators=(',', ':')) + '\n')
                if mode == 'stuck':    # Enter が効かない席: 本文が入力欄に残る（n=5253）
                    pass
                elif mode == 'queue':    # 仕事中: 本文が順番待ちに積まれ、印は出ない
                    w('\r\n❯ ' + buf.replace('\r', ' ').replace('\n', '\r\n  ') + '\r\n  ⎿  Queued · ctrl+x ctrl+s to send now\r\n'); buf = ''
                elif mode == 'silent':  # 仕事を受けたが窓の内に何も出さない
                    w('\r\n'); buf = ''
                else:
                    w('\r\n' + ('受けた ' + m.group(0) if m else '') + '\r\n'); buf = ''
                    if mode == 'scroll':   # 印の後に長い出力＝印が見える画面の外へ流れる
                        for k in range(120): w('出力 %d\r\n' % k)
            else: buf += ch
        show()
EOF
  fail=0
  sed -e 's/^HL=3000 .*/HL=0/' -e 's/^QW=1 .*/QW=0/' "$SUT" > "$TD/legacy5121.sh"   # 直す前の手＝見える画面だけ・印だけ（箱 n=5121）
  sed -e 's/^HEAD=.*/HEAD=$(printf %s "$BODY" | head -n 1 | LC_ALL=C cut -c1-12)/' -e '/^  || HEAD=/d' "$SUT" > "$TD/legacy5253.sh"   # 直す前の手＝頭をバイトで切る（n=5253・launchd の C の locale の cut -c）
  one() {  # $1=名 $2=席の mode $3=試す版 [$4=受け手の events の道（席が書く）] [$5=送り手が読む events の道（既定＝$4）] [$6=本文の 1 行目] [$7=sh]
    S="sts-$1"; LG="$TD/$1.log"; : > "$LG"
    tx new-session -d -s "$S" -x 200 -y 30 "python3 '$TD/seat.py' $2 '$LG' '${4:-}'"; sleep 1
    out=$(printf '%s\n2 行目\n' "${6:-selftest $1}" | SEND_TO_SEAT_EVENTS="${5:-${4:-$TD/no-events}}" ${7:-sh} "$3" -d "$TD" -t "$TT" -w 15 "$S" - 2>&1); rc=$?
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
  # 箱 n=5121: 仕事中の席（順番待ち）・印が画面の外へ流れる席・印を出さず記録だけ在る席。それぞれ直す前の手（陰性対照）で終了 3
  r=$(one queue queue "$SUT"); echo "$r"
  case "$r" in "queue rc=0 "*"送信=1 "*"届いた・順番待ち"*) echo "  OK 仕事中の席の順番待ちを届いたと数える";; *) echo "  NG 仕事中の席"; fail=1;; esac
  r=$(one queue5121 queue "$TD/legacy5121.sh"); echo "$r"
  case "$r" in "queue5121 rc=3 "*"送信=1 "*) echo "  OK 陰性対照: 直す前の手は順番待ちを終了 3 と返す";; *) echo "  NG 陰性対照（順番待ち）"; fail=1;; esac
  r=$(one scroll scroll "$SUT"); echo "$r"
  case "$r" in "scroll rc=0 "*"受けた #"*) echo "  OK 画面の外へ流れた印を履歴から拾う";; *) echo "  NG 流れた印"; fail=1;; esac
  r=$(one scroll5121 scroll "$TD/legacy5121.sh"); echo "$r"
  case "$r" in "scroll5121 rc=3 "*) echo "  OK 陰性対照: 直す前の手は流れた印を拾えず終了 3";; *) echo "  NG 陰性対照（流れた印）"; fail=1;; esac
  r=$(one silent silent "$SUT" "$TD/events.log"); echo "$r"
  case "$r" in "silent rc=0 "*"受け手の記録"*) echo "  OK 印が出なくても受け手の記録（本文の指紋）で届いたと数える";; *) echo "  NG 受け手の記録"; fail=1;; esac
  r=$(one silentnoev silent "$SUT"); echo "$r"
  case "$r" in "silentnoev rc=3 "*) echo "  OK 陰性対照: 記録も印も無ければ終了 3（届いたと言わない）";; *) echo "  NG 陰性対照（記録なし）"; fail=1;; esac
  # n=5253 ④: 終了 3 の後で --check <ID> が本文の指紋を受け手の記録で測り直す（席は窓の内に記録しない形＝送り手は no-events を読む）
  r=$(one late silent "$SUT" "$TD/late-events.log" "$TD/no-events"); echo "$r"
  LID=$(printf '%s' "$r" | sed -n 's/.*（#\([0-9][0-9-]*\)・.*/\1/p' | head -n 1)
  case "$r" in "late rc=3 "*"--check $LID"*) echo "  OK 印なしの終了 3 は --check の撃ち方を出す";; *) echo "  NG 印なしの終了 3 に --check の撃ち方が無い"; fail=1;; esac
  c=$(SEND_TO_SEAT_EVENTS="$TD/late-events.log" sh "$SUT" --check "$LID" 2>&1); crc=$?; echo "  check rc=$crc :: $c"
  [ "$crc" = 0 ] && echo "  OK 後で記録に在る指紋を --check が届いたと数える" || { echo "  NG --check が記録の指紋を数えない"; fail=1; }
  c=$(SEND_TO_SEAT_EVENTS="$TD/no-events" sh "$SUT" --check "$LID" 2>&1); crc=$?; echo "  check(陰性) rc=$crc :: $c"
  [ "$crc" = 3 ] && echo "  OK 陰性対照: 記録に指紋が無ければ --check は終了 3（届いたと言わない）" || { echo "  NG 陰性対照（--check 記録なし）"; fail=1; }
  c=$(sh "$SUT" --check 0000000000-1 2>&1); crc=$?
  [ "$crc" = 2 ] && echo "  OK 陰性対照: 無い ID は --check が測れない（2）" || { echo "  NG 無い ID が rc=$crc"; fail=1; }
  # n=5253 頭の文字の割れ: 日本語の頭（バイトの 12 で 1 字が割れる形）が入力欄に残る席。UTF-8 で照合する sh（zsh を sh として）で撃つ
  JP='n=1 送達の道具の文字の割れほか'
  ZS=""; ZT=$(command -v zsh 2>/dev/null) && { ln -s "$ZT" "$TD/sh"; ZS="$TD/sh"; }
  r=$(LC_ALL=en_US.UTF-8 one jp stuck "$SUT" "" "" "$JP" "${ZS:-sh}"); echo "$r"
  case "$r" in "jp rc=2 "*"入力欄に本文が残った"*) echo "  OK 日本語の頭でも入力欄に残った本文を見落とさない";; *) echo "  NG 日本語の頭で入力欄に残った本文を見落とした"; fail=1;; esac
  TSVH=$(awk -F'\t' '$2=="sts-jp" { h=$5 } END { print h }' "$XDG_STATE_HOME/send-to-seat/sent.tsv")
  if printf '%s' "$TSVH" | python3 -c 'import sys; b=sys.stdin.buffer.read(); s=b.decode("utf-8"); sys.exit(0 if s=="n=1 送達の道具の文字" else 1)' 2>/dev/null; then
    echo "  OK sent.tsv の本文の頭は文字で 12 字（割れていない）"; else echo "  NG sent.tsv の本文の頭が割れた: $(printf %s "$TSVH" | od -An -tx1 | tr -d '\n')"; fail=1; fi
  # launchd の形（C の locale）: 直す前の版の cut -c はここでバイトで切る＝試す版そのものが直す前なら sent.tsv の頭が割れる
  r=$(LC_ALL=C one jpc stuck "$SUT" "" "" "$JP"); echo "$r"
  case "$r" in "jpc rc=2 "*) echo "  OK C の locale でも入力欄に残った本文を見落とさない";; *) echo "  NG C の locale で入力欄の照合"; fail=1;; esac
  TSVH=$(awk -F'\t' '$2=="sts-jpc" { h=$5 } END { print h }' "$XDG_STATE_HOME/send-to-seat/sent.tsv")
  if printf '%s' "$TSVH" | python3 -c 'import sys; sys.exit(0 if sys.stdin.buffer.read().decode("utf-8")=="n=1 送達の道具の文字" else 1)' 2>/dev/null; then
    echo "  OK C の locale でも sent.tsv の本文の頭は文字で 12 字"; else echo "  NG C の locale で sent.tsv の頭が割れた: $(printf %s "$TSVH" | od -An -tx1 | tr -d '\n')"; fail=1; fi
  if [ -n "$ZS" ]; then
    r=$(LC_ALL=en_US.UTF-8 one jp5253 stuck "$TD/legacy5253.sh" "" "" "$JP" "$ZS"); echo "$r"
    case "$r" in "jp5253 rc=3 "*) echo "  OK 陰性対照: 直す前の手（バイトの頭）は入力欄に残った本文を見落とし送れたと読む";; *) echo "  NG 陰性対照（バイトの頭）"; fail=1;; esac
  else echo "  SKIP 陰性対照（バイトの頭）: zsh が無い"; fi
  TSVH=$(awk -F'\t' '$2=="sts-jp5253" { h=$5 } END { print h }' "$XDG_STATE_HOME/send-to-seat/sent.tsv")
  if printf '%s' "$TSVH" | python3 -c 'import sys; sys.stdin.buffer.read().decode("utf-8")' 2>/dev/null; then
    [ -z "$ZS" ] || { echo "  NG 陰性対照: 直す前の手の頭が割れていない"; fail=1; }; else echo "  OK 陰性対照: 直す前の手は sent.tsv の頭を割る"; fi
  [ "$fail" = 0 ] && echo "selftest 全部 OK" || echo "selftest 落ちた"
  exit "$fail"
fi
SSH=""; TD=""; T=""; W=120; G=0; FORCE=""
CHECK=""; [ "${1:-}" = --check ] && { CHECK=${2:-}; [ -n "$CHECK" ] || { echo "使い方: send_to_seat.sh --check <ID>"; exit 2; }; }
[ -n "$CHECK" ] || while getopts s:d:t:w:g:f o; do case $o in s) SSH=$OPTARG;; d) TD=$OPTARG;; t) T=$OPTARG;; w) W=$OPTARG;; g) G=$OPTARG;; f) FORCE=1;; *) exit 2;; esac; done
if [ -n "$CHECK" ]; then   # ④ 後で測る: 送らない。sent.tsv のその ID の行から宛先と受け手の記録の指紋を引き、③の recorded() で測り直す
  ROW=$(I="$CHECK" awk -F'\t' '$3==ENVIRON["I"] && $8!="" { r=$2"\t"$8 } END { print r }' "${XDG_STATE_HOME:-$HOME/.local/state}/send-to-seat/sent.tsv" 2>/dev/null)
  [ -n "$ROW" ] || { echo "測れない（sent.tsv に #${CHECK} の行が無いか、受け手の記録の指紋の無い古い行）"; exit 2; }
  DEST=${ROW%%	*}; NFP=${ROW#*	}
  case "$DEST" in *:*) SSH=${DEST%%:*}; SES=${DEST#*:};; *) SES=$DEST;; esac   # tmux のセッション名に : は入らない＝前が ssh の宛先
else
shift $((OPTIND-1)); SES="$1"; SRC="$2"
[ -n "$SES" ] && [ -n "$SRC" ] || { echo "使い方: send_to_seat.sh [-s ssh] [-d TMUX_TMPDIR] [-t tmux] [-w 秒] [-g 間隔の秒] [-f] <セッション> <本文の紙|->"; exit 2; }
case "$G" in ''|*[!0-9]*) echo "-g は秒の数（${G}）"; exit 2;; esac
ID="$(date +%m%d%H%M%S)-$$"
BODY=$(if [ "$SRC" = - ]; then cat; else cat "$SRC"; fi) || exit 2
MSG=$(printf '%s\n（受け取りの印: 最初の出力の 1 行目に「受けた」と「#%s」を空白 1 つで並べて出せ）' "$BODY" "$ID")
HEAD=$(printf '%s' "$BODY" | python3 -c 'import sys; sys.stdout.write(sys.stdin.buffer.read().decode("utf-8", "replace").split("\n", 1)[0][:12])' 2>/dev/null) \
  || HEAD=$(printf '%s' "$BODY" | head -n 1 | cut -c1-12)   # 文字で 12 字（LC_ALL に依らない）。python3 の無い機体だけ今の cut -c
FP=$(printf '%s' "$BODY" | cksum | awk '{ print $1 "-" $2 }')   # 受け取りの印の行（ID）を足す前の本文＝同じ 1 通なら送り手が違っても同じ
DEST="${SSH:+$SSH:}$SES"
ME=""; [ -n "${TMUX:-}" ] && ME=$(tmux display-message -p ${TMUX_PANE:+-t "$TMUX_PANE"} '#S' 2>/dev/null | head -n 1 | tr -d '\t\r')   # 送り手＝自分の tmux（-d・-s は宛先の tmux）
[ -n "$ME" ] || ME=不明
L="${XDG_STATE_HOME:-$HOME/.local/state}/send-to-seat"; mkdir -p "$L"
# 受け手の記録の指紋（③④）: 送った本文の指紋（hook と同じ正規化＝pasted_content の包みと空白を落として sha256 の頭 16 桁）
# python3 が無ければ空＝③④は数えない（①②だけ）
NFP=""; [ "$QW" = 1 ] && NFP=$(printf '%s' "$MSG" | python3 -c 'import sys,re,hashlib; p=sys.stdin.read(); print(hashlib.sha256(re.sub(r"\s+","",re.sub(r"</?pasted_content\b[^>]*>","",p)).encode()).hexdigest()[:16])' 2>/dev/null)
log() { printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$DEST" "$ID" "$1" "$HEAD" "$ME" "$FP" "$NFP" >> "$L/sent.tsv"; }
if [ "$G" -gt 0 ] && [ -z "$FORCE" ]; then
  # 送り中の印（mkdir は 1 人しか通らない）。殺された送り手の残りは、印を待つ秒＋5 分を過ぎたら死んだとみなす
  LK="$L/inflight-$(printf '%s\t%s' "$DEST" "$FP" | cksum | cut -d' ' -f1)"
  [ -n "$(find "$LK" -maxdepth 0 -mmin +$((W/60+5)) 2>/dev/null)" ] && rmdir "$LK" 2>/dev/null
  mkdir "$LK" 2>/dev/null || { log 止めた; echo "送らない（同じ宛先へ同じ 1 通を別の送り手が送り中: ${DEST}「${HEAD}」指紋 ${FP}・わざと撃ち直すなら -f）"; exit 4; }
  trap 'rmdir "$LK" 2>/dev/null' EXIT
  X=$(( $(date +%s) - G )); CUT=$(date -r "$X" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -d "@$X" '+%Y-%m-%dT%H:%M:%S')
  PREV=$(D="$DEST" F="$FP" C="$CUT" LC_ALL=C awk -F'\t' '$1>=ENVIRON["C"] && $2==ENVIRON["D"] && $7==ENVIRON["F"] && ($4=="受けた" || $4=="順番待ち" || $4=="記録あり" || $4=="印なし") { p=$1" #"$3 } END { print p }' "$L/sent.tsv" 2>/dev/null)
  [ -n "$PREV" ] && { log 止めた; echo "送らない（同じ宛先へ同じ 1 通が ${G} 秒以内に在る: ${DEST}「${HEAD}」指紋 ${FP} ${PREV}・わざと撃ち直すなら -f）"; exit 4; }
fi
fi
# tmux の中から撃つと ${TMUX}（今いる tmux の口）が TMUX_TMPDIR より勝ち、別の tmux の席へ届かない（試しで実測）＝-d のときは外す
PRE="T=${T:-tmux}; ${TD:+unset TMUX; export TMUX_TMPDIR='$TD';} S='$SES';"
run() { if [ -n "$SSH" ]; then ssh -o BatchMode=yes -o ConnectTimeout=8 $SSH "$PRE $1"; else /bin/sh -c "$PRE $1"; fi; }
cap() { if [ "$HL" -gt 0 ]; then run '"$T" capture-pane -p -J -S -'"$HL"' -t "$S"'; else run '"$T" capture-pane -p -J -t "$S"'; fi; }
# 受け手の記録（③④）: events の道は受け手の機体の物（-s なら ssh の先で読む）
EVP=${SEND_TO_SEAT_EVENTS:-}
recorded() { [ -n "$NFP" ] && run "grep -qF '\"prompt_norm_sha256\":\"$NFP\"' \"${EVP:-\$HOME/.claude/monsters/events.log}\" 2>/dev/null"; }
# 順番待ち（②）: 自分の #ID を含む行（受けた の行でない）の後 6 行の内に『Queued』
queued() { printf '%s\n' "$1" | I="#$ID" awk 'index($0, ENVIRON["I"]) && index($0, "受けた " ENVIRON["I"]) == 0 { k = NR } k && NR > k && NR <= k + 6 && /Queued/ { f = 1 } END { exit !f }'; }
if [ -n "$CHECK" ]; then
  if recorded; then echo "届いた #${CHECK}（${DEST}・受け手の記録に本文の指紋 ${NFP} が在る）"; exit 0; fi
  echo "受け手の記録に #${CHECK} の本文の指紋 ${NFP} が無い（${DEST}）＝届いたと言わない"; exit 3
fi
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
t=0; REC=""
while [ "$t" -lt "$W" ]; do
  P=$(cap)
  if printf '%s\n' "$P" | grep -v '^❯' | grep -q "受けた #$ID"; then log 受けた; echo "受けた #${ID}（${SES}）"; exit 0; fi
  if [ "$QW" = 1 ]; then
    [ -z "$REC" ] && recorded && REC=1
    if queued "$P"; then log 順番待ち; echo "届いた・順番待ち #${ID}（${SES}・相手は仕事中＝印は仕事の後に出る・証拠: 画面の Queued${REC:+ と受け手の記録}）＝撃ち直さない"; exit 0; fi
  fi
  sleep 5; t=$((t+5))
done
if [ "$QW" = 1 ] && { [ -n "$REC" ] || recorded; }; then
  log 記録あり; echo "届いた #${ID}（${SES}・受け手の記録に本文の指紋 ${NFP} が在る・印は ${W} 秒の内に出ない）＝撃ち直さない"; exit 0
fi
log 印なし; echo "送れたが受け取りの印が ${W} 秒出ない（#${ID}・${SES}）＝届いたと言わない${NFP:+・後で測る: sh $0 --check $ID}"; exit 3
