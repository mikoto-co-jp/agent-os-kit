#!/usr/bin/env python3
"""カードの検品（工程 4 の後）。1 枚ごとに ①frontmatter の key が名前と同じ ②文字起こしの先頭・末尾 150 字が元の .txt と一致 ③YAML が閉じている。

使い方: python3 verify_cards.py --work <一時ファイルの箱> --shelf <棚のルート>
        python3 verify_cards.py --selftest   正の対照（カード 1 枚＋_索引.md で 1 枚・不一致 0）と 負制御（壊れたカードを足すと不一致 1）を撃つ
  カード＝<棚>/コンテクスト銀行/<source>-<id>.md、元の文字＝<work>/text/<source>/<id>.txt
  ⚠️ 面（source）と id は **frontmatter から引く**。⛔ 鍵を最初のハイフンで割らない——面の名前にハイフンが入った瞬間に誤る
     （実測 2026-09-19: youtube は通るが line-step／mail-myasp／funnel-utage は面が line／mail／funnel に化けた）。
     あわせて key == source-id を検め、鍵と事実の層のずれも落とす。
  不一致は一覧に出して exit 1（席が事実の層から書き直す。手で直さない）。全部通れば exit 0。
  「_」で始まる紙（_台帳・_索引 など）と README.md はカードとして数えない。
なぜ要るか: 席（LLM）が 25 本ずつ書くと、貼り違い・途中省略・YAML の壊れが必ず数枚混じる（元の棚で 4,000 枚中 10 枚超）。
            文字起こしを「整形」した瞬間に原文が失われるので、先頭と末尾で原文どおりかを機械で見る。
"""
import argparse, os, re, shutil, sys, tempfile


def norm(t):
    return re.sub(r"\s+", "", t)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work"); ap.add_argument("--shelf"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.work and a.shelf):
        ap.error("--work と --shelf が要る（または --selftest）")
    cards = os.path.join(a.shelf, "コンテクスト銀行")   # 2026-09-20 の改名の後の置き場
    n = 0; bad = []
    for name in sorted(os.listdir(cards)) if os.path.isdir(cards) else []:
        if not name.endswith(".md") or name == "README.md" or name.startswith("_"):
            continue   # _台帳・_索引 など「_」で始まる紙はカードではない（メモリシステム「台帳と、その横に置く紙」）
        n += 1; key = name[:-3]; c = open(os.path.join(cards, name), encoding="utf-8", errors="ignore").read()
        if not c.startswith("---\n") or c.count("\n---\n") < 1:
            bad.append((key, "frontmatter が閉じていない")); continue
        if not re.search(r"^key:\s*[\"']?" + re.escape(key) + r"[\"']?\s*$", c.split("\n---\n", 1)[0], re.M):
            bad.append((key, "key が名前と違う")); continue
        fm = c.split("\n---\n", 1)[0]
        m_src = re.search(r'^source:\s*["\']?(.+?)["\']?\s*$', fm, re.M)
        m_id = re.search(r'^id:\s*["\']?(.+?)["\']?\s*$', fm, re.M)
        if not (m_src and m_id):
            bad.append((key, "事実の層に source か id が無い")); continue
        src, id_ = m_src.group(1), m_id.group(1)
        if f"{src}-{id_}" != key:
            bad.append((key, f"key と source-id が合わない（{src}-{id_}）")); continue
        txt = os.path.join(a.work, "text", src, id_ + ".txt")
        if not os.path.isfile(txt):
            continue
        t = norm(open(txt, encoding="utf-8", errors="ignore").read())
        if len(t) < 50:
            continue
        body = norm(c.split("## 文字起こし", 1)[-1])
        if t[:150] not in body or t[-150:] not in body:
            bad.append((key, "文字起こしが原文と違う（先頭か末尾の 150 字が無い）"))
    print(f"カード {n} 枚・不一致 {len(bad)}")
    for k, why in bad:
        print(f"  NG {k}: {why}")
    return 1 if bad else 0



def selftest():
    t = tempfile.mkdtemp(prefix="verify-cards-selftest-")
    try:
        work = os.path.join(t, "work"); cards = os.path.join(t, "shelf", "コンテクスト銀行")
        os.makedirs(os.path.join(work, "text", "x")); os.makedirs(cards)
        open(os.path.join(cards, "x-a1.md"), "w", encoding="utf-8").write(
            "---\nkey: x-a1\nsource: x\nid: \"a1\"\n---\n## 文字起こし\n検体の文字\n")
        open(os.path.join(cards, "_索引.md"), "w", encoding="utf-8").write("# 索引（frontmatter の無い紙）\n")
        print("== 正の対照（カード 1 枚＋_索引.md）")
        rc = main(["--work", work, "--shelf", os.path.join(t, "shelf")])
        if rc != 0:
            print("🚨 selftest: _索引.md を置いただけで検品が落ちた（_ で始まる紙をカードとして数えている）"); return 1
        open(os.path.join(cards, "x-b2.md"), "w", encoding="utf-8").write("key: x-b2\n（frontmatter が壊れたカード）\n")
        print("== 負制御（frontmatter の壊れたカードを 1 枚足す）")
        if main(["--work", work, "--shelf", os.path.join(t, "shelf")]) == 0:
            print("🚨 selftest: 壊れたカードを足したのに検品が通った（検品が死んでいる）"); return 3
        print("✅ selftest: _索引.md を置いても通り、壊れたカードは落ちた")
        return 0
    finally:
        shutil.rmtree(t)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
