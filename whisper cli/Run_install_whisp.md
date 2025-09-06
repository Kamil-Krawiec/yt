# whisp 🎙️  
Simple CLI wrapper around [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for CPU-friendly transcription and optional English translation.  
Everything runs inside its own **virtualenv in `/opt/whisp`**, so no global `pip install` required.  

---

## 🔧 Installation

Run the installer script (needs `sudo`):

```bash
sudo bash install_whisp.sh
```

The script will:  
- create `/opt/whisp/` with a dedicated Python venv  
- install `faster-whisper` and dependencies  
- place a global command **`whisp`** in `/usr/local/bin/`  

After installation you can use `whisp` anywhere on your system.

---

## 🚀 Usage

Show all flags and defaults:
```bash
whisp --info
```

### Basic transcription (auto-detect language → native subtitles)
```bash
whisp ~/audio/input.m4a
```
Outputs:  
- `out/input.srt` (subtitles)  
- `out/input.txt` (plain text transcript)  

---

### Native transcription + English translation
```bash
whisp --translate ~/audio/interview.mp3
```
Outputs:  
- `out/interview.srt`  
- `out/interview.txt`  
- `out/interview_en.srt`  
- `out/interview_en.txt`  

---

### Choose model
(default is `medium`)  
```bash
whisp -m small ~/audio/talk.wav
```

- `small` → faster, lower quality  
- `medium` → balanced, recommended for Polish/EN  
- `large-v2/v3` → best quality, slowest  

---

### Force source language
(skip auto-detection)
```bash
whisp --lang pl ~/audio/podcast.mp3
```

---

### Custom output directory
```bash
whisp -o ~/transcripts ~/audio/lecture.mp4
```

---

### Performance tip (CPU threading)
Limit BLAS threads to keep machine responsive:
```bash
OPENBLAS_NUM_THREADS=6 OMP_NUM_THREADS=6 whisp -m medium ~/audio/meeting.m4a
```

---

## 📂 Output files
By default everything goes into `./out/` relative to your working dir:  
- `file.srt` → native subtitles  
- `file.txt` → native transcript  
- `file_en.srt` + `file_en.txt` → English translation (if `--translate` is set)  

---

## 📝 Example Workflow (Mac → Server)

Send a file from Mac to server:
```bash
scp "./plik_.mov" user@server_ip:~/path/to/file/test.mov
```

Run transcription + translation on server:
```bash
whisp --translate -m medium -o ~/path/to/output/folder ~path/to/input/file/test_odcinek7.mov'
```

Results will be in `~/path/to/output/file`.

---
```bash
kamil@server:~/homelab$ whisp --info
whisp – faster-whisper CLI

Customizable flags (with defaults):
  -h, --help                default===SUPPRESS==  help=show this help message and exit
  -m, --model               default=medium        help=Model: tiny/base/small/medium/large-v2/large-v3 (default: medium)
  --compute-type            default=int8          help=int8 | int8_float16 | float16 | float32 (default: int8 for CPU)
  --beam                    default=1             help=Beam size (default: 1)
  --lang                    default=None          help=Force source language (e.g., 'pl', 'en'). Omit for auto-detect.
  --threads                 default=0             help=Limit BLAS threads; 0=auto (default: 0)
  -o, --outdir              default=./out         help=Output directory (default: ./out)
  --words-per-line          default=6             help=Max words per subtitle line (default: 6)
  --translate               default=False         help=Also produce English translation (SRT+TXT) in addition to native transcript.
  --info                    default=False         help=Print all customizable flags with defaults and exit.

Examples:
  whisp --info
  whisp input.m4a
  whisp --translate input.m4a
  whisp -m small --threads 6 input.wav
  whisp --lang pl --words-per-line 5 -o ~/transcripts call.mp3
```

## ⚠️ Notes
- First run will download the Whisper model (cached under `~/.cache`).
- Works CPU-only, default `compute-type=int8` for efficiency.
- On **i5-8500T (16 GB RAM)** → recommended models:  
  - `small` for speed (~0.5–1× realtime)  
  - `medium` for better accuracy (slower, ~3–5× realtime)  
