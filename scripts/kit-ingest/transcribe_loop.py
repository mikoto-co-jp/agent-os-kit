#!/usr/bin/env python3
"""文字起こしの常駐ループ（工程 2）。取得済みの動画・音声のうち text/ に無い物を順に whisper へ。lock・失敗印つき。

使い方:
  python3 transcribe_loop.py --work <一時ファイルの箱> [--sources 出所 ...] [--once] [--worker 1|2]
                             [--engine auto|mlx|faster|cli] [--model large-v3-turbo] [--model-path <ggml の .bin>] [--language ja]
  止め方: <work>/STOP_TRANSCRIBE を作る（プロセスを kill しない）。再開は同じコマンド（済んだ分は skip）。
  --once   1 周だけ回して終わる（門の前・小さな実弾に）。失敗が 1 本でもあれば exit 1
  --worker 2 は逆順に走査する（2 機体・2 プロセスで分け合うとき。lock は同じ形）

出力: text/<source>/<id>.txt（本文）＋ .json／.srt（engine が出せる物）＋ .meta.json（engine・秒・字数・発話密度）
      音声トラックが無い物は "(音声トラックなし)" を .txt に書いて済みにする。失敗は <id>.failed を置いて次へ（再試行は .failed を消す）。

engine（auto は上から順に在る物）:
  mlx     Apple Silicon: コマンド mlx_whisper（pipx install mlx-whisper）。GPU で 25〜60 倍速
  faster  python モジュール faster_whisper（pip install faster-whisper）。NVIDIA なら CUDA・無ければ CPU（遅い）
  cli     whisper.cpp の whisper-cli（brew install whisper-cpp）。--model-path に ggml モデルが要る。音声は 16kHz wav に変換して渡す
  どれも無い機体では止まって報告する（人に入れさせない。クラウドの文字起こしを使うなら料金を先に測って GO を取る＝課金）

守ること（元の棚の実測から）:
  - condition_on_previous_text=False を外さない（既定 True は同じ 1 行を延々と吐くループに落ち、50 分を丸ごと失いかけた）
  - 出力名は id 固定（--output-name）。先頭ハイフンの id が引数に化けるのを防ぐ
  - 発話密度（行数÷分）を .meta.json に残す。正常は 16〜25 行/分。外れ値は門が一覧に出す（暴走・無音・言語違い）
  - 書き出しは NFC に固定（macOS のファイル名は NFD）
"""
import argparse, datetime as dt, json, os, shutil, subprocess, sys, time, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_complete import MEDIA_EXT, has_audio, probe_duration  # noqa: E402


def log(work, msg):
    os.makedirs(os.path.join(work, "log"), exist_ok=True)
    with open(os.path.join(work, "log", "transcribe.log"), "a", encoding="utf-8") as f:
        f.write(dt.datetime.now().strftime("%m-%d %H:%M:%S ") + msg + "\n")
    print(msg, flush=True)


def pick_engine(want):
    if want in ("auto", "mlx") and shutil.which("mlx_whisper"):
        return "mlx"
    if want in ("auto", "faster"):
        try:
            import faster_whisper  # noqa: F401
            return "faster"
        except Exception:
            pass
    if want in ("auto", "cli") and shutil.which("whisper-cli"):
        return "cli"
    return ""


def srt_time(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_outputs(outbase, segments, text):
    """segments: [(start, end, text)]. .txt／.json／.srt を NFC で書く。"""
    nfc = lambda s: unicodedata.normalize("NFC", s)
    with open(outbase + ".txt", "w", encoding="utf-8") as f:
        f.write(nfc(text).strip() + "\n")
    with open(outbase + ".json", "w", encoding="utf-8") as f:
        json.dump({"text": nfc(text), "segments": [{"start": s, "end": e, "text": nfc(t)} for s, e, t in segments]},
                  f, ensure_ascii=False)
    with open(outbase + ".srt", "w", encoding="utf-8") as f:
        for i, (s, e, t) in enumerate(segments, 1):
            f.write(f"{i}\n{srt_time(s)} --> {srt_time(e)}\n{nfc(t).strip()}\n\n")


def run_mlx(f, outdir, id_, model, lang):
    # --output-name=<id> は必ず = で繋ぐ（先頭ハイフンの id を離して渡すとオプションと読まれて落ちる。実弾 1 本目で踏んだ）
    cmd = ["mlx_whisper", f, "--model", f"mlx-community/whisper-{model}", "--language", lang, "--task", "transcribe",
           f"--output-dir={outdir}", f"--output-name={id_}", "--output-format", "all",
           "--condition-on-previous-text", "False", "--hallucination-silence-threshold", "2", "--no-speech-threshold", "0.5",
           "--verbose", "False"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return False, (r.stderr or "")[-300:]
    # mlx は NFD で書くことがあるので .txt を NFC に揃える
    p = os.path.join(outdir, id_ + ".txt")
    if os.path.isfile(p):
        t = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(unicodedata.normalize("NFC", t))
    return os.path.isfile(p), "mlx ok"


def run_faster(f, outdir, id_, model, lang):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="auto", compute_type="auto")
    segs, _ = m.transcribe(f, language=lang, condition_on_previous_text=False, no_speech_threshold=0.5,
                           hallucination_silence_threshold=2, vad_filter=False)
    segments = [(s.start, s.end, s.text) for s in segs]
    write_outputs(os.path.join(outdir, id_), segments, "\n".join(t.strip() for _, _, t in segments))
    return True, "faster ok"


def run_cli(f, outdir, id_, model_path, lang):
    if not model_path or not os.path.isfile(model_path):
        return False, "--model-path（ggml の .bin）が無い"
    wav = os.path.join(outdir, id_ + ".16k.wav")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, (r.stderr or "")[-200:]
    r = subprocess.run(["whisper-cli", "-m", model_path, "-l", lang, "-otxt", "-osrt", "-oj", "-of", os.path.join(outdir, id_),
                        "-f", wav], capture_output=True, text=True)   # -of の値は絶対パスなので先頭ハイフンにならない
    os.remove(wav)
    if r.returncode != 0:
        return False, (r.stderr or "")[-300:]
    p = os.path.join(outdir, id_ + ".txt")
    if os.path.isfile(p):
        t = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(unicodedata.normalize("NFC", t))
    return os.path.isfile(p), "cli ok"


def one_pass(a, engine):
    did = fails = 0
    media_root = os.path.join(a.work, "media")
    sources = a.sources or (sorted(os.listdir(media_root)) if os.path.isdir(media_root) else [])
    for src in sources:
        d = os.path.join(media_root, src)
        if not os.path.isdir(d):
            continue
        files = sorted(x for x in os.listdir(d) if os.path.splitext(x)[1].lower() in MEDIA_EXT
                       and ".part" not in x and ".temp" not in x and ".f" not in os.path.splitext(x)[0][-5:])
        if a.worker == 2:
            files.reverse()
        for name in files:
            if os.path.isfile(os.path.join(a.work, "STOP_TRANSCRIBE")):
                return did, fails, True
            f = os.path.abspath(os.path.join(d, name)); id_ = os.path.splitext(name)[0]
            outdir = os.path.join(a.work, "text", src); os.makedirs(outdir, exist_ok=True)
            out = os.path.join(outdir, id_)
            if os.path.isfile(out + ".txt") or os.path.isfile(out + ".failed"):
                continue
            try:
                os.mkdir(out + ".lock")
            except FileExistsError:
                continue   # 他ワーカーが処理中
            try:
                dur = probe_duration(f)
                if dur is None:
                    log(a.work, f"unreadable {src}/{id_}"); continue
                t0 = time.time()
                if not has_audio(f):
                    open(out + ".txt", "w", encoding="utf-8").write("(音声トラックなし)\n")
                    ok, msg = True, "no-audio"
                elif engine == "mlx":
                    ok, msg = run_mlx(f, outdir, id_, a.model, a.language)
                elif engine == "faster":
                    ok, msg = run_faster(f, outdir, id_, a.model, a.language)
                else:
                    ok, msg = run_cli(f, outdir, id_, a.model_path, a.language)
                sec = int(time.time() - t0)
                if ok and os.path.isfile(out + ".txt"):
                    text = open(out + ".txt", encoding="utf-8").read()
                    lines = len([l for l in text.splitlines() if l.strip()])
                    meta = {"engine": engine, "model": a.model, "language": a.language, "seconds": sec,
                            "duration_sec": dur, "chars": len(text), "lines": lines,
                            "lines_per_min": round(lines / max(dur / 60, 0.01), 2), "no_audio": msg == "no-audio"}
                    json.dump(meta, open(out + ".meta.json", "w", encoding="utf-8"), ensure_ascii=False)
                    log(a.work, f"ok{a.worker} {src}/{id_} {sec}s {len(text)}B {meta['lines_per_min']}行/分 [{engine}]")
                else:
                    open(out + ".failed", "w").write(msg + "\n")
                    log(a.work, f"FAIL {src}/{id_} {msg.strip()[-160:]}"); fails += 1
                did += 1
            finally:
                try:
                    os.rmdir(out + ".lock")
                except OSError:
                    pass
    return did, fails, False


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True)
    ap.add_argument("--sources", nargs="*")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--worker", type=int, default=1)
    ap.add_argument("--engine", default="auto", choices=["auto", "mlx", "faster", "cli"])
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--model-path", default="")
    ap.add_argument("--language", default="ja")
    a = ap.parse_args(argv)
    if not shutil.which("ffprobe"):
        print("⛔ ffprobe が無い（席が入れる）"); return 4
    engine = pick_engine(a.engine)
    if not engine:
        print("⛔ 文字起こしの道具が無い（mlx_whisper／faster_whisper／whisper-cli のどれか。席が入れる。人に入れさせない）"); return 4
    log(a.work, f"start worker{a.worker} engine={engine} model={a.model}")
    while True:
        did, fails, stopped = one_pass(a, engine)
        if stopped:
            log(a.work, "stop"); return 0
        if a.once:
            log(a.work, f"once done did={did} fails={fails}"); return 1 if fails else 0
        if did == 0:
            time.sleep(120)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
