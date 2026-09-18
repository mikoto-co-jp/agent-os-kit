# {棚の名前}

{事業名}（{呼び名}）。AI エージェントが読んで働く棚。

**この棚の規則は `.claude/rules/` の 3 枚が正本。ここには写さない。**

| 紙 | 何 | 誰が変えるか |
|---|---|---|
| `.claude/rules/規矩.md` | 越えない線（⛔🔒）・帳簿の書き方・判断の読み方 | **主君（{呼び名}）だけ** |
| `.claude/rules/メモリシステム.md` | どこに置くか（置き場のルール）・入れてはいけない物 | 席。孔明が追記できる。整理は承認 |
| `.claude/rules/主君.md` | 誰か・やってもらいたいこと・丞相の呼び名 | 主君。孔明が追記できる。整理は承認 |

箱は 2 つ。**守る `rules/`（毎回読む・3 枚）／数える 記録 MCP `kiroku`（帳簿・実験・実行・追記のみ）。**過去の事例と主君の答え（`焼き先=答え／任せる` の印）は全部帳簿の行。判断に迷ったら `ledger_query` で引く（引き方は `規矩.md` 3 節）。

道具は `scripts/`（箱の frontmatter＝`kiroku.py`・全体像の生成＝`build_scope_progress.py`・門＝`git-hooks/`・配布の門＝`check-distributable.sh`）。全体像は `docs/SCOPE_PROGRESS.md`（生成物。手で書かない。手順は `docs/定期便-手順/SCOPE_PROGRESSの生成.md`）。
