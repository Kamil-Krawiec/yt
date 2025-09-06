#!/usr/bin/env bash
set -euo pipefail

# --- Paths ---
PREFIX="/opt/whisp"
VENV="$PREFIX/.venv"
BIN="/usr/local/bin/whisp"
SCRIPT="$PREFIX/whisper_cli.py"

# --- Pre-reqs ---
apt-get update
apt-get install -y python3-venv ffmpeg

# --- Create app dir ---
mkdir -p "$PREFIX"

# --- Write the Python CLI ---
cat > "$SCRIPT" <<'PY'
#!/usr/bin/env python3
import argparse, os, sys, time, pathlib
from faster_whisper import WhisperModel

def to_srt_timestamp(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def chunk_srt_write(segments, path: pathlib.Path, max_words: int = 6):
    """
    Write SRT splitting each whisper segment into smaller chunks
    of up to `max_words` words, distributing time proportionally.
    """
    with path.open("w", encoding="utf-8") as f:
        idx = 1
        for seg in segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            words = text.split()
            duration = max(seg.end - seg.start, 0.001)
            avg_time = duration / max(len(words), 1)

            for i in range(0, len(words), max_words):
                chunk = words[i:i + max_words]
                if not chunk:
                    continue
                chunk_start = seg.start + i * avg_time
                chunk_end = seg.start + (i + len(chunk)) * avg_time
                f.write(f"{idx}\n")
                f.write(f"{to_srt_timestamp(chunk_start)} --> {to_srt_timestamp(chunk_end)}\n")
                f.write(" ".join(chunk) + "\n\n")
                idx += 1

def write_txt(segments, path: pathlib.Path):
    with path.open("w", encoding="utf-8") as f:
        for seg in segments:
            text = (seg.text or "").strip()
            if text:
                f.write(text + "\n")

def transcribe_file(
    audio_path: pathlib.Path,
    model_name: str,
    compute_type: str,
    beam_size: int,
    language: str | None,
    task: str,  # "transcribe" or "translate"
    num_threads: int | None,
):
    # optional threading caps (keep server responsive)
    if num_threads and num_threads > 0:
        os.environ["OPENBLAS_NUM_THREADS"] = str(num_threads)
        os.environ["OMP_NUM_THREADS"] = str(num_threads)

    print(f"[info] loading model: {model_name} (compute_type={compute_type})")
    model = WhisperModel(model_name, compute_type=compute_type)

    print(f"[info] running {task} | language={language or 'auto'} | beam_size={beam_size}")
    t0 = time.time()
    segments, info = model.transcribe(
        str(audio_path),
        language=language,        # None → auto-detect
        task=task,                # "transcribe" or "translate"
        beam_size=beam_size,
    )
    segs = list(segments)
    print(f"[info] detected_language={info.language} (p={info.language_probability:.2f}) "
          f"| duration={getattr(info, 'duration', 'n/a')}")
    print(f"[info] elapsed={time.time() - t0:.1f}s")
    return segs, info

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="whisp",
        description="CPU-friendly faster-whisper CLI: native transcription and optional English translation."
    )
    p.add_argument("audio", nargs="?", help="Path to audio/video (wav/mp3/m4a/mp4…)")
    p.add_argument("-m", "--model", default="medium",
                   help="Model: tiny/base/small/medium/large-v2/large-v3 (default: medium)")
    p.add_argument("--compute-type", default="int8",
                   help="int8 | int8_float16 | float16 | float32 (default: int8 for CPU)")
    p.add_argument("--beam", type=int, default=1, help="Beam size (default: 1)")
    p.add_argument("--lang", default=None,
                   help="Force source language (e.g., 'pl', 'en'). Omit for auto-detect.")
    p.add_argument("--threads", type=int, default=0,
                   help="Limit BLAS threads; 0=auto (default: 0)")
    p.add_argument("-o", "--outdir", default="./out",
                   help="Output directory (default: ./out)")
    p.add_argument("--words-per-line", type=int, default=6,
                   help="Max words per subtitle line (default: 6)")

    # flags
    p.add_argument("--translate", action="store_true",
                   help="Also produce English translation (SRT+TXT) in addition to native transcript.")
    p.add_argument("--info", action="store_true",
                   help="Print all customizable flags with defaults and exit.")
    return p

def print_info(p: argparse.ArgumentParser):
    print("whisp – faster-whisper CLI")
    print("\nCustomizable flags (with defaults):")
    for a in p._actions:
        if not a.option_strings:
            continue
        opts = ", ".join(a.option_strings)
        default = a.default if a.default is not None else "None"
        print(f"  {opts:25s} default={default}  help={a.help or ''}")
    print("\nExamples:")
    print("  whisp --info")
    print("  whisp input.m4a")
    print("  whisp --translate input.m4a")
    print("  whisp -m small --threads 6 input.wav")
    print("  whisp --lang pl --words-per-line 5 -o ~/transcripts call.mp3")
    print("")

def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)

    if args.info or not args.audio:
        print_info(p)
        if not args.audio:
            return 0
        # if audio provided + --info, continue processing after info print

    audio_path = pathlib.Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        print(f"[error] file not found: {audio_path}", file=sys.stderr)
        return 1

    outdir = pathlib.Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    stem = audio_path.stem

    # 1) Native transcription
    native_segments, info = transcribe_file(
        audio_path=audio_path,
        model_name=args.model,
        compute_type=args.compute_type,
        beam_size=args.beam,
        language=args.lang,     # None → auto
        task="transcribe",
        num_threads=(args.threads if args.threads > 0 else None),
    )
    native_srt = outdir / f"{stem}.srt"
    native_txt = outdir / f"{stem}.txt"
    chunk_srt_write(native_segments, native_srt, max_words=args.words_per_line)
    write_txt(native_segments, native_txt)
    print(f"[ok] native transcripts: {native_srt} | {native_txt}")

    # 2) Optional English translation
    if args.translate:
        en_segments, _ = transcribe_file(
            audio_path=audio_path,
            model_name=args.model,
            compute_type=args.compute_type,
            beam_size=args.beam,
            language="en",
            task="translate",
            num_threads=(args.threads if args.threads > 0 else None),
        )
        en_srt = outdir / f"{stem}_en.srt"
        en_txt = outdir / f"{stem}_en.txt"
        chunk_srt_write(en_segments, en_srt, max_words=args.words_per_line)
        write_txt(en_segments, en_txt)
        print(f"[ok] English translation: {en_srt} | {en_txt}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
PY

chmod +x "$SCRIPT"

# --- Create and fill venv (no global pip installs) ---
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install "faster-whisper>=1.0.0"

# --- Install global launcher ---
cat > "$BIN" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT="/opt/whisp/whisper_cli.py"
VENV="/opt/whisp/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "[error] venv missing at $VENV" >&2
  exit 1
fi
exec "$VENV/bin/python" "$SCRIPT" "$@"
SH
chmod +x "$BIN"

echo "------------------------------------------------------------"
echo "[OK] whisp installed."
echo "Location: /opt/whisp (venv: /opt/whisp/.venv)"
echo "Command:  whisp"
echo "Try:      whisp --info"
echo "------------------------------------------------------------"