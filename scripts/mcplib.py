#!/usr/bin/env python3
"""Python から BlueLamp の口（MCP）を直に撃つ — 生成器が席を挟まずに自分で引くための 1 枚。

🔑 何のためか: 生成器（Python）が口を撃てないと、席が手で `<tool>` を撃って JSON に落として
   渡す 2 手になる。配った先では会員の孔明が同じ手番を踏む。⇒ この紙が 1 手にする。
   🔬 2026-09-20 実測: stdio で JSON-RPC を話すと tools/list が 710 件返り、
   `kiroku__ledger_query` が実データを返した（鍵は機体の `~/.musuhi/portal-token.enc` を
   子プロセスが継ぐので、**本文にも環境変数にも秘密を書かない**）。

⛔ 機体固有の道を焼かない。サーバの道はこの順で自分で見つける:
   1. 環境変数 `BLUELAMP_MCP_CMD`（空白区切り。どんな入れ方でもここで上書きできる）
   2. `npm root -g` が指す `bluelamp/dist/lib/mcp-server/index.cjs` ＋ PATH 上の node
   3. 見つからなければ **はっきり落ちる**（⛔ 黙って 0 件を返さない）

使い方:
    from mcplib import MCP, call
    print(call("kiroku__ledger_query", {"tenantId": ..., "limit": 5}))   # 1 発だけ
    m = MCP(); m.init()                                                   # 何発も撃つとき
    r = m.send("tools/call", {"name": ..., "arguments": {...}})
    m.close()
"""
import json
import os
import shlex
import shutil
import subprocess
import threading
import time

SERVER_REL = os.path.join("bluelamp", "dist", "lib", "mcp-server", "index.cjs")


def server_cmd():
    """口を開く撃ち方を返す。⛔ 見つからなければ RuntimeError（0 件に化けさせない）。"""
    env = os.environ.get("BLUELAMP_MCP_CMD")
    if env:
        return shlex.split(env)

    node = shutil.which("node")
    tried = []
    roots = []
    try:
        out = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            roots.append(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    # npm が無い機体のための控え（見つからなければ黙って飛ばす）
    for p in ("/opt/homebrew/lib/node_modules", "/usr/local/lib/node_modules",
              os.path.expanduser("~/.npm-global/lib/node_modules")):
        if p not in roots:
            roots.append(p)

    for r in roots:
        cand = os.path.join(r, SERVER_REL)
        tried.append(cand)
        if os.path.exists(cand):
            if not node:
                raise RuntimeError(
                    "BlueLamp の口は見つかったが node が PATH に無い。\n"
                    f"  口: {cand}\n"
                    "  非対話の SSH では PATH に乗らないことがある。"
                    "`BLUELAMP_MCP_CMD='<nodeのフルパス> <上の道>'` で渡す。")
            return [node, cand]

    raise RuntimeError(
        "BlueLamp の口（MCP サーバ）が見つからない。⛔ これは「0 件」ではなく「取得不能」。\n"
        "  探した所:\n    " + "\n    ".join(tried) + "\n"
        "  直し方: `npm i -g bluelamp` で入れるか、"
        "`BLUELAMP_MCP_CMD='<node> <index.cjs の道>'` で道を渡す。")


class MCP:
    """stdio の JSON-RPC を 1 本張る。大きい戻りが席の文脈に載らないのが利点。"""

    def __init__(self, timeout=600, cmd=None):
        self.p = subprocess.Popen(cmd or server_cmd(),
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1,
                                  env=dict(os.environ))
        self.id = 0
        self.timeout = timeout
        self.err = []
        threading.Thread(target=self._drain, daemon=True).start()

    def _drain(self):
        for line in self.p.stderr:
            self.err.append(line.rstrip())

    def send(self, method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self.id += 1
            msg["id"] = self.id
        self.p.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        if notify:
            return None
        want = self.id
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("server closed stdout. stderr tail:\n" + "\n".join(self.err[-20:]))
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if obj.get("id") == want:
                return obj
        raise TimeoutError(f"timeout waiting for {method}")

    def init(self):
        r = self.send("initialize", {"protocolVersion": "2024-11-05",
                                     "capabilities": {},
                                     "clientInfo": {"name": "mikoto-os", "version": "1"}})
        self.send("notifications/initialized", {}, notify=True)
        return r

    def close(self):
        try:
            self.p.stdin.close()
            self.p.terminate()
        except OSError:
            pass

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def unwrap(r, tool="tool"):
    """戻りから本文を取り出す。⛔ 失敗を空文字に化けさせず、必ず投げる。"""
    if r is None:
        raise RuntimeError(f"{tool}: 戻りが無い")
    if "error" in r:
        raise RuntimeError(f"{tool}: {json.dumps(r['error'], ensure_ascii=False)[:400]}")
    res = r.get("result", {})
    if res.get("isError"):
        raise RuntimeError(f"{tool} isError: {json.dumps(res, ensure_ascii=False)[:400]}")
    content = res.get("content") or []
    if not content:
        raise RuntimeError(f"{tool}: 中身が空（取得不能。0 件と読み替えない）")
    return content[0].get("text", "")


def call(tool, arguments=None, timeout=600):
    """1 発だけ撃って本文を返す。落ちるときは例外（⛔ 空や 0 件を返さない）。"""
    m = MCP(timeout=timeout)
    try:
        m.init()
        return unwrap(m.send("tools/call", {"name": tool, "arguments": arguments or {}}), tool)
    finally:
        m.close()


if __name__ == "__main__":
    # 自己検査: 口が開くか・tools/list が返るか。開かなければ exit 2（取得不能）。
    import sys
    try:
        print("口:", " ".join(server_cmd()))
        with MCP(timeout=120) as m:
            n = len(m.send("tools/list", {})["result"]["tools"])
        print(f"✅ 口が開いた（道具 {n} 件）")
    except Exception as e:                                    # noqa: BLE001 — 取得不能を人に見せる
        print(f"❌ 取得不能: {e}")
        sys.exit(2)
