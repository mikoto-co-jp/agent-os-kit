# SCOPE_PROGRESSの生成 — 手順の正本

> **最初に `.claude/rules/` の 3 枚（規矩・メモリシステム・主君）を読む。**この便は棚のルート以外で起動されることがあり、その時は規矩が載っていない（暫定。cwd で起こせるようになったら消す）

状態: **未登録**（孔明が便を建てるとき scheduler に登録する。task は「この紙を読んで動け」の 1 行だけ）。
目的: 機械が書く 1 枚（`docs/SCOPE_PROGRESS.md`）を朝の儀式の前に作り直す。手で書かない。正本は `07プロジェクト/<プロジェクト>/status.md`・`00廷議/*.md`・scheduler・`08アーカイブ/案件/` の墓標。

`docs/SCOPE_PROGRESS.md` の型（8 節固定・順固定・空の節は「（なし）」1 行）の正本は `scripts/build_scope_progress.py` の docstring。**この紙も生成器もその型に従う。**

## やること（この順）
1. `git -C {棚の置き場} pull --rebase --autostash`
2. **稼働中の席を取る**: MCP `list_monsters` の結果を JSON で `10一時ファイル/monsters-YYYY-MM-DD.json` に落とす。取れなければ次へ進む（§6 の稼働中が「（未取得）」になるだけ）
3. `python3 scripts/build_scope_progress.py --monsters <その json>`（8 節: プロジェクト（state 別・語彙は `scripts/kiroku.py`）／裁定表（00廷議 ＋ 箱の ask）／主君の手（lever）／待ち受け（until・期待日超過は 🔴）／Routine／エージェント（席）／完了 30 日／棚の差分）
   - scheduler の一覧を MCP（`schedule_list`）から渡すときは `--schedules <json のパス>`。渡さなければこの機体の scheduler の正本を直接読む
   - 出す先を変えるときだけ `--out <path>`（dry-run 用）
4. **ログ 1 行**を `docs/定期便-ログ/YYYY-MM.md` の末尾に書く: `YYYY-MM-DD HH:MM SCOPE_PROGRESSの生成｜<スクリプトの stderr の 1 行をそのまま>`。書かずに終わったら失敗
5. `docs/SCOPE_PROGRESS.md` とログを **1 本ずつ `git add -- <path>`** → commit「生成: SCOPE_PROGRESS YYYY-MM-DD」→ push（`git add -A` は禁止・規矩 X-1）

## 節ごとに、何が出たら誰が直すか
| 節 | 出る物 | 直す元 | 直す人 |
|---|---|---|---|
| 1 プロジェクト | **状態なし**（status.md が無い）・**語彙外**（state が 8 語に無い） | `python3 scripts/kiroku.py box --slug <箱> …` で frontmatter を作る／直す。pre-commit（pre-commit-box.sh）が commit を止める | そのプロジェクトの owner |
| 2 裁定表 | **差し戻し**（推奨なし・選択肢なし） | 出した席が `00廷議/` の紙に推奨を書く | 出した席 |
| 3 主君の手 | lever の行 | 主君が手を動かしたら持ち主が lever を空にする | 箱の持ち主 |
| 4 待ち受け | 🔴（期待日超過） | 持ち主が until の期待日を直すか、来た物を本文に写して until を空にする | 箱の持ち主 |
| 5 Routine | **止**・手順書なし・ログなし | scheduler と `docs/定期便-手順/<便>.md` | 便の owner |
| 7 完了 | — | `08アーカイブ/案件/` の墓標 | 閉じた席 |
| 8 棚の差分 | pre-commit **なし** ほか | 棚そのもの（`git config core.hooksPath scripts/git-hooks`） | 孔明 |

## やらないこと
- 節を手で足す・消す・並べ替える（答え・進捗は元へ書く。次の生成で消える）
- status.md や `00廷議/` を書き換える（**状態なし** は赤く出るだけ。直すのは owner）
- 数えていない数字を書く。0 件と「取得不能」を混ぜる

## 詰まったら
- スクリプトが落ちた → ログに `落ちた: <script>（1 行目のエラー）` を書き、記録 MCP `kiroku` の `ledger_append` を 1 回（種別＝躓き。規矩 §4）
- `git index.lock` が在る → 他席が commit 中。5 秒待って再試行
