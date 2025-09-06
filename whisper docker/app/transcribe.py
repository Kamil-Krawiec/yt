import os, time, pathlib
from faster_whisper import WhisperModel

MODEL = os.getenv("MODEL_SIZE", "base")  # dla 4GB: "tiny" albo "base"
LANG  = os.getenv("LANGUAGE", "pl")
OUT   = pathlib.Path("/output")
INP   = pathlib.Path("/input")
PROCESSED = set()

# Load Whisper model (int8 for CPU efficiency)
model = WhisperModel(MODEL, compute_type="int8")

def ts(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace('.', ',')

def transcribe_one(p):
    segs, _ = model.transcribe(str(p), language=LANG, beam_size=1)
    lines = []
    for i, s in enumerate(segs, 1):
        lines.append(f"{i}\n{ts(s.start)} --> {ts(s.end)}\n{s.text.strip()}\n")
    (OUT / (p.stem + ".srt")).write_text("".join(lines), encoding="utf-8")
    print("[OK]", p.name)

while True:
    for p in INP.glob("*"):
        if p.is_file() and p.suffix.lower() in [".mp3", ".wav", ".m4a", ".mp4", ".mov"] and p not in PROCESSED:
            try:
                transcribe_one(p)
                PROCESSED.add(p)
            except Exception as e:
                print("[ERR]", p, e)
    time.sleep(2)
