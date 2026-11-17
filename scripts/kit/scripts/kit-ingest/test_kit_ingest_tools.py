#!/usr/bin/env python3
"""kit-ingest の 4 本（verify_complete・drive_put・transcribe_loop・build_ledger）の働きを撃つ試験。

外の道具（rclone・mlx_whisper）は偽物を PATH の先頭に置いて撃つ＝ネットにも Drive にも触れない。
  python3 scripts/kit-ingest/test_kit_ingest_tools.py              この試験の隣の 4 本を撃つ
  KIT_INGEST_DIR=<別の版の kit-ingest> python3 …/test_kit_ingest_tools.py   別の版を撃つ（直す前の版で落ちる＝陰性対照）
"""
import csv, importlib, io, os, shutil, stat, subprocess, sys, tempfile, unittest, zipfile
from contextlib import redirect_stdout

sys.dont_write_bytecode = True   # 試験が __pycache__ を作ると make-kit の切り出しが .pyc（中に機体の道）を固有値として落とす
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"   # 子のプロセス（--selftest）にも
HERE = os.environ.get("KIT_INGEST_DIR") or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def mod(name):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(data, bytes) else "w") as f:
        f.write(data)
    return path


def fake_tool(bindir, name, body):
    p = write(os.path.join(bindir, name), "#!/usr/bin/env python3\n" + body)
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="kit-ingest-test-")
        self.bin = os.path.join(self.t, "bin"); os.makedirs(self.bin)
        self.old_path = os.environ["PATH"]
        os.environ["PATH"] = self.bin + os.pathsep + self.old_path

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.t, ignore_errors=True)


class VerifyComplete(Base):
    def setUp(self):
        super().setUp()
        self.vc = mod("verify_complete")
        fake_tool(self.bin, "pdfinfo", "import sys\nprint('Pages: 1')\n")   # 機体の pdfinfo に依らない

    def test_names_exist(self):
        for n in ("DOC_EXT", "IMG_EXT", "ASSET_EXT", "doc_readable"):
            self.assertTrue(hasattr(self.vc, n), n)
        self.assertTrue(set(self.vc.MEDIA_EXT) <= set(self.vc.ASSET_EXT))

    def test_documents(self):
        ok = lambda n, d: self.vc.doc_readable(write(os.path.join(self.t, n), d))[0]
        self.assertTrue(ok("a.pdf", b"%PDF-1.4\n...\n"))
        self.assertFalse(ok("b.pdf", b"<html>not a pdf"))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w/>")
        self.assertTrue(ok("c.docx", buf.getvalue()))
        self.assertFalse(ok("d.docx", buf.getvalue()[:20]))          # 途中で切れた zip
        self.assertTrue(ok("e.txt", "日本語の文です。\n" * 50))
        self.assertTrue(ok("f.txt", ("日本語の文です。\n" * 50).encode("cp932")))
        self.assertFalse(ok("g.txt", bytes(range(128, 256)) * 64))   # 文字でない物

    def test_images(self):
        ok = lambda n, d: self.vc.doc_readable(write(os.path.join(self.t, n), d))[0]
        self.assertTrue(ok("a.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 32))
        self.assertTrue(ok("b.jpg", b"\xff\xd8\xff\xe0" + b"\0" * 32))
        self.assertTrue(ok("c.bmp", b"BM\x36\x10\x0e\x00" + b"\0" * 32))   # 大きさの欄が 0 でない普通の BMP
        self.assertFalse(ok("d.png", b"GIF-like but not" + b"\0" * 16))

    def test_good_and_media_path(self):
        work = os.path.join(self.t, "w")
        write(os.path.join(work, "media", "face1", "doc1.pdf"), b"%PDF-1.4\n" + b"x" * 100)
        p = self.vc.media_path(work, "face1", "doc1")
        self.assertTrue(p and p.endswith("doc1.pdf"), p)
        ok, why = self.vc.good(p)                  # 尺を見ない（ffprobe が無くても通る）
        self.assertTrue(ok, why)


class DrivePut(Base):
    def setUp(self):
        super().setUp()
        self.log = os.path.join(self.t, "rclone.log")
        # 偽の rclone: copy は --files-from(-raw) の名前だけを「置いた」と覚え、lsf はそれを path;size;md5 で返す
        fake_tool(self.bin, "rclone", f"""
import hashlib, json, os, sys
LOG = {self.log!r}; STORE = LOG + ".store"
a = sys.argv[1:]
open(LOG, "a").write(json.dumps(a) + "\\n")
store = json.load(open(STORE)) if os.path.exists(STORE) else {{}}
if a[0] == "copy":
    src, dest = a[-2], a[-1]
    names = sorted(os.listdir(src)) if os.path.isdir(src) else [os.path.basename(src)]
    for flag in ("--files-from-raw", "--files-from"):
        if flag in a:
            names = [l.strip() for l in open(a[a.index(flag) + 1]) if l.strip()]
    base = src if os.path.isdir(src) else os.path.dirname(src)
    for n in names:
        store.setdefault(dest, {{}})[n] = hashlib.md5(open(os.path.join(base, n), "rb").read()).hexdigest()
    json.dump(store, open(STORE, "w"))
elif a[0] == "lsf":
    dest = a[-1]
    for n, h in sorted(store.get(dest, {{}}).items()):
        print(f"{{n}};1;{{h}}")
    for n, h in store.get(dest + "#dup", {{}}).items():
        print(f"{{n}};1;{{h}}")
""")
        self.work = os.path.join(self.t, "w")
        self.face = os.path.join(self.work, "media", "face1")
        write(os.path.join(self.face, "v1.mp4"), b"video-1")
        write(os.path.join(self.face, "d1.pdf"), b"%PDF-1.4 doc")
        write(os.path.join(self.face, "v2.mp4.part"), b"half")            # 取得途中
        write(os.path.join(self.face, "note.xyz"), b"not an asset")
        self.dp = mod("drive_put")

    def run_put(self, *extra):
        with redirect_stdout(io.StringIO()) as out:
            rc = self.dp.main(["--work", self.work, "--remote", "r", "--folder", "原本", *extra])
        return rc, out.getvalue()

    def calls(self):
        import json
        return [json.loads(l) for l in open(self.log)] if os.path.exists(self.log) else []

    def test_batch_one_copy_per_face(self):
        rc, out = self.run_put("--batch")
        self.assertEqual(rc, 0, out)
        copies = [c for c in self.calls() if c[0] == "copy"]
        self.assertEqual(len(copies), 1, copies)                           # 面ごとに 1 回
        self.assertIn("--copy-links", copies[0])
        placed = os.path.join(self.work, "placed", "face1")
        self.assertEqual(sorted(os.listdir(placed)), ["d1.ok", "v1.ok"])   # .part と拡張子の外は置かない・数えない
        self.assertFalse(os.path.exists(os.path.join(self.work, "placed", "face1.lock")))  # 錠は外れている
        import json
        sent = json.load(open(self.log + ".store"))["r:原本/face1/"]
        self.assertEqual(sorted(sent), ["d1.pdf", "v1.mp4"])               # Drive へ送るのも数えた物だけ（取得途中の .part を置かない）

    def test_batch_counts_duplicates(self):
        import json
        store = self.log + ".store"
        json.dump({"r:原本/face1/#dup": {"v1.mp4": "x"}}, open(store, "w"))
        rc, out = self.run_put("--batch")
        self.assertEqual(rc, 1, out)                                       # 同名の写しは落ちる（消しはしない）
        self.assertIn("同名の写し", out)

    def test_batch_lock_refuses(self):
        os.makedirs(os.path.join(self.work, "placed", "face1.lock"))
        rc, out = self.run_put("--batch")
        self.assertEqual(rc, 1, out)
        self.assertEqual([c for c in self.calls() if c[0] == "copy"], [])  # 別の処理が置いている面は撃たない

    def test_single_places_documents(self):
        rc, out = self.run_put()
        self.assertTrue(os.path.isfile(os.path.join(self.work, "placed", "face1", "d1.ok")), out)


class TranscribeLoop(Base):
    def test_dotted_id_gets_its_own_txt(self):
        # 偽の mlx_whisper: 本物と同じく --output-name の最後のドットより後を拡張子と読んで切る
        fake_tool(self.bin, "mlx_whisper", """
import os, sys
a = dict(x.split("=", 1) for x in sys.argv[1:] if x.startswith("--output-") and "=" in x)
d, n = a["--output-dir"], a["--output-name"]
n = os.path.splitext(n)[0]
for ext in (".txt", ".srt", ".json"):
    open(os.path.join(d, n + ext), "w").write("書き起こし\\n")
""")
        tl = mod("transcribe_loop")
        out = os.path.join(self.t, "out"); os.makedirs(out)
        ok, why = tl.run_mlx("in.m4a", out, "Vo.Bass", "large-v3", "ja")
        self.assertTrue(ok, why)
        self.assertTrue(os.path.isfile(os.path.join(out, "Vo.Bass.txt")))
        self.assertFalse(os.path.exists(os.path.join(out, "Vo.txt")))      # 別の id の名で書いていない
        self.assertEqual(sorted(os.listdir(out)), ["Vo.Bass.json", "Vo.Bass.srt", "Vo.Bass.txt"])  # 仮の置き場は残らない


class BuildLedger(Base):
    def card(self, root, key, kind, title, why="理由", source="face1"):
        write(os.path.join(root, "コンテクスト銀行", key + ".md"),
              f"---\nkey: {key}\nsource: {source}\nid: {key}\nkind: {kind}\norig_title: {title}\nwhy: {why}\ndrive: https://drive.example/{key}\n---\n本文\n")

    def test_private_and_learning_and_order(self):
        bl = mod("build_ledger")
        shelf = os.path.join(self.t, "shelf")
        self.card(shelf, "k3", "動画", "公開の題")
        self.card(shelf, "k1", "教材", "他人の教材")
        write(os.path.join(shelf, "07学習資産", "教材ライブラリ", "作者", "k1.md"), "---\nkey: k1\n---\n")
        priv = os.path.join(shelf, "10私用", "箱A")
        self.card(priv, "k2", "私用", "口座のある題", why="見せない理由")
        self.card(priv, "k4", "契約", "見せない題2")
        write(os.path.join(priv, "05バックオフィス資産", "見せない名.md"), "---\nkey: k4\n---\n")
        out = os.path.join(self.t, "ledger.csv")
        with redirect_stdout(io.StringIO()):
            rc = bl.main(["--shelf", shelf, "--out", out])
        self.assertIn(rc, (0, None))
        rows = list(csv.reader(open(out, encoding="utf-8")))
        body = rows[1:]
        self.assertEqual([r[0] for r in body], ["k1", "k2", "k3", "k4"])  # key で並ぶ
        by = {r[0]: r for r in body}
        self.assertIn("07学習資産", by["k1"][8])                           # 内容軸 07 を仕訳先として読む
        self.assertEqual(by["k2"][8], "（私用・棚に入れない）")
        text = open(out, encoding="utf-8").read()
        for secret in ("口座のある題", "見せない理由", "見せない題2", "見せない名", "drive.example/k2", "drive.example/k4"):
            self.assertNotIn(secret, text)                                 # 見せない箱の文は git に載る台帳へ写さない
        self.assertIn("10私用/箱A", by["k4"][8])                           # 在ったこと（どの箱か）は残る
        self.assertEqual(by["k3"][4], "公開の題")

    def test_selftest_still_passes(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "build_ledger.py"), "--selftest"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
