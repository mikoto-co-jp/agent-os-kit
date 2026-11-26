#!/bin/sh
# 秘密の誤コミット防止（ステージ済みファイル全走査・.githooks 自身は除外）
# 型: 接続文字列の合言葉・秘密鍵（RSA・EC・OpenSSH ほか）・Anthropic／OpenAI・AWS・GitHub（古い札・新しい札）・Slack・Google（API の鍵・OAuth の秘密）・Notion・JWT・
#   調べ物の鍵（OpenRouter sk-or-v1-・xAI xai-・Tavily tvly-・Perplexity pplx-）。
#   出所: 2026-11-26 会員からの直しの提案（型が 6 つだけで sk-ant-・sk-proj-・github_pat_・gho_ ほか・調べ物の鍵を通し、名前に空白のある紙を 2 つに割って見張らなかった）
#   Anthropic の鍵は本物が 100 字前後なので 80 字から、JWT は署名まで（本物の署名は 43 字から＝40 字から）を当てる＝試験の短い見本（sk-ant-api03-AAAA… や署名の短い JWT）は止めない
#   調べ物の鍵の下限は 20 字（本物は OpenRouter 64 字の 16 進・xAI 80 字前後・Tavily 32 字前後・Perplexity 48 字前後）
#   型ごとの効き目は --selftest（偽の値の見本を型ごとに 1 つ）で数える。型を足したら見本も 1 つ足す
#   正本はこの紙（器の雛形 scripts/kit/scripts/git-hooks/）。器の提供元の棚では棚の門 scripts/git-hooks/pre-commit-secret.sh がこの紙への別名、切り出した器では両方がこの紙の写し。
#   make-kit.sh --selftest の 5-2 段が棚の門と器の写しの差を数え、両方の --selftest を撃つ
PATTERNS='postgres(ql)?://[^ ]*:[^ @*]*@|BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{20}|sk-ant-[A-Za-z0-9_-]{80}|sk-(proj|svcacct|admin)-[A-Za-z0-9_-]{20}|AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{20}|gh[opsur]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22}|xox[bp]-|AIza[0-9A-Za-z_-]{35}|GOCSPX-[A-Za-z0-9_-]{20}|ntn_[A-Za-z0-9]{40}|secret_[A-Za-z0-9]{43}|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{40}|sk-or-v1-[0-9a-f]{20}|xai-[A-Za-z0-9]{20}|tvly-[A-Za-z0-9_-]{20}|pplx-[A-Za-z0-9]{20}'
# 接続文字列の「合言葉の枠」が穴（[PASSWORD] ${VAR} $VAR <...> YOUR_xxx）の行は実値ではない。
# 出所: 2026-09-19 にプロンプト資産 234 枚を git に載せたとき 4 行が偽陽性で止めた（ひな形の穴）。
# ⚠️ 穴と見なすのは「: と @ の間」だけ。利用者名や host に穴が在っても合言葉が実値なら止める。
# {{名}} は差し込みのひな形の穴（Vault の connection_url など、その道具の書き方そのもの）＝実値ではない。
# 調べ物の鍵の頭の後が x だけの語は書き方の見本（export TAVILY_API_KEY="tvly-xxxx…"）で実値ではない。
#   ⚠️ 見本の語だけを消してから型に当てる（行ごと捨てない）。行ごと捨てると同じ行の本物の形の鍵まで通す
#   後ろの区切りの字（\2）は残す＝消した跡で前後の語がつながって型に当たる形を作らない
XFILL='(sk-or-v1-|xai-|tvly-|pplx-)[xX]{20,}([^A-Za-z0-9_-]|$)'
HOLES='postgres(ql)?://[^ ]*:(\[[^]]*\]|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*|<[^>]*>|\{\{[^}]*\}\}|YOUR[A-Za-z0-9_]*|PASSWORD|password)@'
# 使い方:
#   sh pre-commit-secret.sh                    保存の門（台に載った紙）
#   sh pre-commit-secret.sh --range <元>..<先>  写す前の門（棚の post-commit や pre-push から撃つ口）: その範囲で変わった紙を <先> の中身で当てる（--no-verify で保存の門を飛ばした物も外へ出さない）
#   sh pre-commit-secret.sh --selftest         型ごとの偽の値で門を撃つ。exit 0＝合格／1＝普通の文で止めた（誤検出）／3＝偽の値を通した（門が死んでいる）
# 名前は -z で受けて 1 本ずつ当てる（空白の入った名前を割らない）。当てるのは --scan で自分を呼び直した側

if [ "${1:-}" = --scan ]; then
  SRC=$2; shift 2; FAIL=0
  for f; do
    case "$f" in .githooks/*) continue;; esac
    H=$(git show "$SRC$f" 2>/dev/null | LC_ALL=C sed -E "s/$XFILL/\\2/g" | grep -EIn "$PATTERNS" | grep -v 'user:pass@host' | grep -v '\*\*\*\*' | grep -vE "$HOLES" | head -3)
    [ -n "$H" ] && { echo "❌ pre-commit: $f に秘密らしき文字列:" >&2; echo "$H" >&2; FAIL=1; }
  done
  exit $FAIL
fi

if [ "${1:-}" = --selftest ]; then
  self=$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")
  t=$(mktemp -d) || exit 1
  trap 'rm -rf "$t"' EXIT
  q() { printf "%0${1}d" 0 | tr 0 Q; }   # Q の並び＝形だけの偽の値。⚠️ この紙自身が門に当たらないよう、値は撃つ時に組み立てる
  hx() { printf "%0${1}d" 0 | tr 0 f; }   # f の並び＝16 進だけの型（OpenRouter）に当てる偽の値（Q は 16 進でないので当たらない）
  n=0; ok=0; miss=0; fp=0
  # one <期待の終了> <見本の名> <紙の名> <中身> [range]
  one() {
    n=$((n+1)); d="$t/$n"
    { mkdir "$d" && git -C "$d" init -q && printf '%s\n' "$4" > "$d/$3" && git -C "$d" add -- "$3"; } || { echo "🚨 selftest: 見本 $2 が作れない"; exit 1; }
    if [ "${5:-}" = range ]; then
      git -C "$d" -c core.hooksPath=/dev/null -c user.name=selftest -c user.email=selftest@example.invalid commit -q -m selftest || { echo "🚨 selftest: 見本 $2 を保存できない"; exit 1; }
      ( cd "$d" && sh "$self" --range "$(git hash-object -t tree /dev/null)..HEAD" >/dev/null 2>&1 ); rc=$?
    else
      ( cd "$d" && sh "$self" >/dev/null 2>&1 ); rc=$?
    fi
    if [ "$rc" = "$1" ]; then ok=$((ok+1)); else echo "❌ selftest: $2 が終了 ${rc}（期待 ${1}）"; if [ "$1" = 1 ]; then miss=1; else fp=1; fi; fi
  }
  one 1 'Anthropic の鍵'        k.md "key: sk-ant-api03-$(q 95)"
  one 1 'OpenAI の鍵（新）'     k.md "key: sk-proj-$(q 40)"
  one 1 'OpenAI の鍵（古い）'   k.md "key: sk-$(q 40)"
  one 1 'AWS の鍵'              k.md "id: AKIA$(q 16)"
  one 1 'Google の API の鍵'    k.md "key: AIza$(q 35)"
  one 1 'Google の OAuth の秘密' k.md "secret: GOCSPX-$(q 28)"
  one 1 'GitHub の札（ghp_）'   k.md "token: ghp_$(q 36)"
  one 1 'GitHub の札（gho_）'   k.md "token: gho_$(q 36)"
  one 1 'GitHub の細かい札'     k.md "token: github_pat_$(q 60)"
  one 1 'Slack の札'            k.md "token: xox""b-$(q 30)"
  one 1 'Notion の札（ntn_）'   k.md "token: ntn_$(q 46)"
  one 1 'Notion の札（secret_）' k.md "token: secret_$(q 43)"
  one 1 'JWT'                   k.md "jwt: eyJ$(q 20).eyJ$(q 20).$(q 43)"
  one 1 'postgres:// の合言葉'  k.md "url: postgres://app:$(q 16)@db.example.invalid/x"
  one 1 'postgresql:// の合言葉' k.md "url: postgresql://app:$(q 16)@db.example.invalid/x"
  one 1 'OpenSSH の秘密鍵'      k.md "-----BEGIN OPENSSH PRIVATE"" KEY-----"
  one 1 'RSA の秘密鍵'          k.md "-----BEGIN RSA PRIVATE"" KEY-----"
  one 1 'OpenRouter の鍵'       k.md "key: sk-or-v1-$(hx 64)"
  one 1 'xAI の鍵'              k.md "key: xai-$(q 80)"
  one 1 'Tavily の鍵'           k.md "key: tvly-$(q 32)"
  one 1 'Perplexity の鍵'       k.md "key: pplx-$(q 48)"
  one 1 '名前に空白の在る紙'    'a b.md' "key: sk-ant-api03-$(q 95)"
  one 1 '写す前の門（空白の名前）' 'c d.md' "key: sk-ant-api03-$(q 95)" range
  one 0 '試験の短い見本（sk-ant-）' k.md "key: sk-ant-api03-$(q 20)"
  one 0 '署名の短い JWT の見本' k.md "jwt: eyJ$(q 20).eyJ$(q 20).$(q 20)"
  one 0 'UUID'                  k.md "id: $(printf '%s-%s-%s-%s-%s' 1e2d3c4b 5a69 4788 9a0b 1c2d3e4f5a6b)"
  one 0 '連番'                  k.md "note-2026-11-21-0001 / 第0001号 / 20261121000000"
  one 0 '普通の文（risk-…）'    k.md "risk-management-framework-for-the-whole-team"
  one 0 '接続文字列の穴'        k.md 'url: postgres://app:${DB_PASSWORD}@db.example.invalid/x'
  one 0 '接続文字列の穴（<>）'  k.md "url: postgresql://app:<password>@db.example.invalid/x"
  one 0 '調べ物の鍵の書き方の見本（x の並び）' k.md "export TAVILY_API_KEY=\"tvly-$(printf '%032d' 0 | tr 0 x)\""
  one 1 'x の見本と同じ行の鍵' k.md "e.g. tvly-$(printf '%032d' 0 | tr 0 x) / key sk-ant-api03-$(q 95)"
  one 1 'x の見本と同じ行の鍵（写す前の門）' k.md "export TAVILY_API_KEY=tvly-$(printf '%032d' 0 | tr 0 x) XAI_API_KEY=xai-$(q 80)" range
  one 0 'x の見本だけの行（4 型）' k.md "sk-or-v1-$(printf '%064d' 0 | tr 0 x) xai-$(printf '%080d' 0 | tr 0 X) tvly-$(printf '%032d' 0 | tr 0 x) pplx-$(printf '%048d' 0 | tr 0 x)"
  [ "$miss" = 1 ] && { echo "🚨 selftest: 偽の値を通した（門が死んでいる）"; exit 3; }
  [ "$fp" = 1 ] && { echo "🚨 selftest: 普通の文で止めた（誤検出）"; exit 1; }
  echo "✅ selftest: 見本 $n 種のうち $ok 種が期待どおり（偽の値は全部止め、普通の文は通した）"
  exit 0
fi

if [ "${1:-}" = --range ]; then
  SRC="${2##*..}:"; set -- diff -z --name-only --diff-filter=ACM "$2"
else
  SRC=":"; set -- diff -z --cached --name-only --diff-filter=ACM
fi
git -c core.quotepath=false "$@" | xargs -0 sh "$0" --scan "$SRC" || exit 1
exit 0
