#!/usr/bin/env python3
"""ページの面の門（売り込みのページ・申込のページを引き上げたとき「取った」と言えるか）。gate.py の「取得」の列が使う。

なぜ在るか: 引き上げの門（gate.py）が数える「取得」は、動画・音声の拡張子（verify_complete.py の MEDIA_EXT）だけだった。
  ページの面（HTML・画像・CSS・対応表）は門に入らず、中身がエラーの頁（HTML）が CSS や画像の名前で置かれても「全数そろった」と出た。
  ⇒ 解約の判断の材料が嘘になる。本文（コンテクスト銀行員）の「`<body` が在る を門に足す」と門 14（取った の定義）・15（拡張子と中身）を道具で撃てる形にした。

置き場（<work> の下・面ごと）:
  html/<面>/<id>.html        描画後の DOM 全文（1 行＝manifest の 1 行。この道が在る行を「ページの行」と呼ぶ）
  css/<面>/…                 CSS の実体（下の階も見る）
  media/<面>-img/…           画像の実体（下の階も見る）
  html/<面>/_css-map.tsv     CSS の対応表（1 行目が見出し・`file` の列＝css/<面>/ からの道）
  html/<面>/_img-map.tsv     画像の対応表（1 行目が見出し・`file` の列＝media/<面>-img/ からの道）

ページの行が「取れた」と言える条件（1 つでも欠ければ欠け）:
  ① `<body` が在る（`</html>` で終わっていても head だけの頁は落とす）
  ② 見える文字が 200 字以上（script・style・noscript・タグ・空白を除いて数える）
  ③ 題（<title>）がエラーの頁の言い方でない（404・Not Found・Forbidden・ページが見つかりません ほか）
面ごとに（ページの行が 1 本でも在る面）:
  ④ css/<面>/ と media/<面>-img/ の全ファイルで、拡張子と中身が一致する（gzip は解いて見る。HTML のエラー頁が .css・.png の名前で置かれたら落ちる）
  ⑤ 対応表が 2 本とも在り、`file` の列が指す物が全部在り、置き場のファイルの数と対応表の一意の数がそろう
     （画像の無い面でも見出しだけの対応表は置く＝「無かった」と「数えていない」を分ける）

使い方:
  python3 verify_pages.py --work <一時ファイルの箱>     ページの行と面を全部見て一覧を出す。全部通れば exit 0、1 本でも欠ければ exit 1
  python3 verify_pages.py --selftest                   正の対照 1 つと負制御 8 本（1 本ずつ外して落ちるか）
  他の道具からは page_html(work, s, i)・page_ok(path)・face_problems(work, face) を import して使う。
"""
import argparse, csv, glob, gzip, html, os, re, shutil, sys, tempfile

MIN_VISIBLE = 200
ERROR_TITLE = re.compile(
    r"(?<![0-9])(?:400|401|403|404|410|429|500|502|503|504)(?![0-9])|not\s*found|forbidden|access\s*denied|"
    r"bad\s*gateway|service\s*unavailable|internal\s*server\s*error|too\s*many\s*requests|page\s*(?:does\s*not|doesn'?t)\s*exist|"
    r"ページが見つかりません|お探しのページ|ページは存在しません|アクセスが拒否|アクセスできません|エラーが発生",
    re.I)
MAPS = (("css", "_css-map.tsv"), ("img", "_img-map.tsv"))


def page_html(work, source, id_):
    p = os.path.join(work, "html", source, id_ + ".html")
    return p if os.path.isfile(p) else None


def _read_bytes(path):
    b = open(path, "rb").read()
    if b[:2] == b"\x1f\x8b":
        try:
            b = gzip.decompress(b)
        except OSError:
            pass
    return b


def visible_text(doc):
    doc = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1\s*>", " ", doc)
    doc = re.sub(r"(?s)<!--.*?-->", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    return re.sub(r"\s+", "", html.unescape(doc))


def page_ok(path):
    """(ok, 理由)。① body ② 見える文字 ③ 題。"""
    if not path or not os.path.isfile(path):
        return False, "HTML が無い"
    doc = _read_bytes(path).decode("utf-8", "replace")
    if not re.search(r"(?i)<body[\s>]", doc):
        return False, "<body が無い（head だけの頁）"
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", doc)
    title = html.unescape(m.group(1)).strip() if m else ""
    if title and ERROR_TITLE.search(title):
        return False, f"題がエラーの頁の言い方（{title[:40]}）"
    n = len(visible_text(doc))
    if n < MIN_VISIBLE:
        return False, f"見える文字が {n} 字（{MIN_VISIBLE} 字未満）"
    return True, f"ok 見える文字 {n} 字"


def _is_html(b):
    h = b[:512].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    return h.startswith((b"<!doctype html", b"<html", b"<head", b"<body")) or b"<html" in h[:200]


def content_matches(path):
    """(ok, 理由)。拡張子と中身の一致。⛔ image/* かではなく、拡張子どおりの中身か。"""
    ext = os.path.splitext(path)[1].lower()
    b = _read_bytes(path)
    if not b:
        return False, "0 バイト"
    if _is_html(b) and ext not in (".html", ".htm"):
        return False, f"中身が HTML（{ext} の名前で置かれたエラーの頁）"
    sig = {
        ".png": lambda: b.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": lambda: b.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda: b.startswith(b"\xff\xd8\xff"),
        ".gif": lambda: b.startswith((b"GIF87a", b"GIF89a")),
        ".webp": lambda: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
        ".avif": lambda: b[4:12] in (b"ftypavif", b"ftypavis"),
        ".bmp": lambda: b.startswith(b"BM"),
        ".ico": lambda: b.startswith(b"\x00\x00\x01\x00"),
        ".svg": lambda: b"<svg" in b[:4096].lower(),
        ".woff": lambda: b.startswith(b"wOFF"),
        ".woff2": lambda: b.startswith(b"wOF2"),
        ".ttf": lambda: b.startswith((b"\x00\x01\x00\x00", b"true")),
        ".otf": lambda: b.startswith(b"OTTO"),
    }
    if ext in sig:
        return (True, "ok") if sig[ext]() else (False, f"中身が {ext} ではない（先頭 {b[:8]!r}）")
    if ext in (".css", ".js"):
        try:
            b.decode("utf-8")
        except UnicodeDecodeError:
            return False, f"中身が文字ではない（{ext}）"
        return True, "ok"
    return True, "ok（拡張子の表に無い・HTML でないことだけ見た）"


def _files(d):
    out = []
    for r, _, fs in os.walk(d):
        for f in fs:
            if f == ".DS_Store" or f.startswith("._"):
                continue
            out.append(os.path.relpath(os.path.join(r, f), d))
    return sorted(out)


def face_problems(work, face):
    """面ごとの ④⑤。欠けの一覧（空なら通った）。"""
    bad = []
    dirs = {"css": os.path.join(work, "css", face), "img": os.path.join(work, "media", face + "-img")}
    for kind, d in dirs.items():
        for rel in _files(d) if os.path.isdir(d) else []:
            ok, why = content_matches(os.path.join(d, rel))
            if not ok:
                bad.append(f"{face}/{kind}/{rel}: {why}")
    for kind, name in MAPS:
        mp = os.path.join(work, "html", face, name)
        if not os.path.isfile(mp):
            bad.append(f"{face}: 対応表 html/{face}/{name} が無い（{kind} が無い面でも見出しだけ置く）"); continue
        with open(mp, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        if rows and "file" not in rows[0]:
            bad.append(f"{face}: 対応表 {name} に file の列が無い"); continue
        mapped = sorted({r["file"].strip() for r in rows if (r.get("file") or "").strip()})
        d = dirs[kind]
        on_disk = _files(d) if os.path.isdir(d) else []
        for m in mapped:
            if not os.path.isfile(os.path.join(d, m)):
                bad.append(f"{face}: 対応表 {name} の {m} が置き場に無い")
        if len(mapped) != len(on_disk):
            bad.append(f"{face}: {kind} の数が対応表とそろわない（対応表 {len(mapped)}・置き場 {len(on_disk)}）")
    return bad


def page_faces(work):
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(work, "html", "*"))
                  if glob.glob(os.path.join(p, "*.html")))


def check(work, rows=None):
    """(分母, 欠けの一覧, 面ごとの欠け)。rows を渡さなければ manifest の全行のうちページの行だけ。"""
    if rows is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from verify_complete import manifest_paths, read_manifest
        rows = [r for m in manifest_paths(work) for r in read_manifest(m)]
    n, bad = 0, []
    for r in rows:
        p = page_html(work, r["source"], r["id"])
        if not p:
            continue
        n += 1
        ok, why = page_ok(p)
        if not ok:
            bad.append(f"{r['source']}/{r['id']}: {why}")
    faces = {f: face_problems(work, f) for f in page_faces(work)}
    return n, bad, faces


# ------------------------------ selftest ------------------------------
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
GOOD_BODY = "<p>" + "検体の本文です。" * 40 + "</p>"
ERROR_PAGE = "<!DOCTYPE html><html><head><title>404 Not Found</title></head><body><h1>Not Found</h1></body></html>"


def _build(t):
    w = os.path.join(t, "work")
    for d in ("manifest", "html/p", "css/p", "media/p-img"):
        os.makedirs(os.path.join(w, d))
    with open(os.path.join(w, "manifest", "p.tsv"), "w", encoding="utf-8") as f:
        f.write("source\tid\turl\tsize_bytes\tduration_sec\ttitle\tcontainer\tfetched_at\n")
        for i in ("a1", "b2"):
            f.write(f"p\t{i}\thttp://example.invalid/{i}\t\t\t検体 {i}\tページ\t2000-01-01\n")
    for i in ("a1", "b2"):
        open(os.path.join(w, "html", "p", i + ".html"), "w", encoding="utf-8").write(
            f"<!DOCTYPE html><html><head><title>検体の頁 {i}</title><style>p{{color:red}}</style></head><body>{GOOD_BODY}</body></html>")
    open(os.path.join(w, "css", "p", "main.css"), "w").write("body{margin:0}\n")
    with gzip.open(os.path.join(w, "css", "p", "sub.css"), "wb") as g:
        g.write(b"p{color:blue}\n")
    open(os.path.join(w, "media", "p-img", "hero.png"), "wb").write(PNG)
    open(os.path.join(w, "html", "p", "_css-map.tsv"), "w").write("url\tfile\nhttp://example.invalid/main.css\tmain.css\nhttp://example.invalid/sub.css\tsub.css\n")
    open(os.path.join(w, "html", "p", "_img-map.tsv"), "w").write("page\turl\tfile\na1\thttp://example.invalid/hero.png\thero.png\n")
    return w


def _bad(w):
    n, bad, faces = check(w)
    return bool(bad) or any(faces.values())


def selftest():
    t = tempfile.mkdtemp(prefix="pages-selftest-")
    try:
        w = _build(t)
        n, bad, faces = check(w)
        if n != 2 or bad or any(faces.values()):
            print(f"🚨 selftest: 正しい検体で落ちた（分母 {n}）: {bad} {faces}"); return 1
        print("== 正の対照（ページ 2 本・CSS 2（1 本は gzip）・画像 1・対応表 2）: 通った")
        hurts = [
            ("① <body が無い", lambda w: open(os.path.join(w, "html/p/a1.html"), "w").write(
                "<!DOCTYPE html><html><head><title>検体</title></head></html>")),
            ("② 見える文字が 200 字未満", lambda w: open(os.path.join(w, "html/p/a1.html"), "w").write(
                "<html><head><title>検体</title><script>" + "x" * 900 + "</script></head><body><p>短い</p></body></html>")),
            ("③ 題がエラーの頁", lambda w: open(os.path.join(w, "html/p/b2.html"), "w").write(
                "<html><head><title>ページが見つかりません</title></head><body>" + GOOD_BODY + "</body></html>")),
            ("④ エラーの頁を CSS の名前で置く", lambda w: open(os.path.join(w, "css/p/main.css"), "w").write(ERROR_PAGE)),
            ("④ エラーの頁を画像の名前で置く", lambda w: open(os.path.join(w, "media/p-img/hero.png"), "w").write(ERROR_PAGE)),
            ("④ webp を .png の名前で置く", lambda w: open(os.path.join(w, "media/p-img/hero.png"), "wb").write(
                b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 16)),
            ("⑤ 対応表が無い", lambda w: os.remove(os.path.join(w, "html/p/_img-map.tsv"))),
            ("⑤ 置き場の数が対応表とそろわない", lambda w: open(os.path.join(w, "css/p/extra.css"), "w").write("a{}\n")),
        ]
        for name, hurt in hurts:
            shutil.rmtree(w); w = _build(t)
            hurt(w)
            if not _bad(w):
                print(f"🚨 selftest: {name} なのに門が通った（門が死んでいる）"); return 3
            print(f"== 負制御（{name}）: 落ちた")
        print(f"✅ selftest: 正の対照が通り、負制御 {len(hurts)} 本がそれぞれ落ちた")
        return 0
    finally:
        shutil.rmtree(t, ignore_errors=True)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.work:
        ap.error("--work が要る（または --selftest）")
    n, bad, faces = check(a.work)
    print(f"--- ページの行 {n}・通った {n - len(bad)}・欠け {len(bad)}")
    for b in bad:
        print("  NG " + b)
    for f, probs in faces.items():
        print(f"  面 {f}: " + ("✅ CSS・画像・対応表がそろった" if not probs else f"⛔ {len(probs)} 件"))
        for p in probs:
            print("    NG " + p)
    return 0 if not bad and not any(faces.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
