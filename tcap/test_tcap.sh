#!/usr/bin/env bash
set -euo pipefail

# Simple tcap benchmark
# Usage:
#   ./test_tcap.sh [INPUT_MP4]
# Defaults:
#   INPUT_MP4 = test_tcap_real.mp4
#   PNG       = <stem>.png (np. test_tcap_real.png)

IN="${1:-test_tcap_real.mp4}"
BASE="${IN%.*}"
PNG="${PNG:-${BASE}.png}"

# CRF presets (you can tweak)
CRF_LOW="${CRF_LOW:-16}"
CRF_DEF="${CRF_DEF:-18}"   # matches tcap default
CRF_HIGH="${CRF_HIGH:-22}"

# Outputs
OUT_LOW="${BASE}_thumb_crf${CRF_LOW}.mp4"
OUT_DEF="${BASE}_thumb_crf${CRF_DEF}.mp4"
OUT_HIGH="${BASE}_thumb_crf${CRF_HIGH}.mp4"
OUT_COPY="${BASE}_thumb_copy.mp4"
OUT_RENC="${BASE}_thumb_reenc.mp4"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }
need tcap
need ffprobe
need date

[ -f "$IN" ]  || { echo "Input not found: $IN"; exit 1; }
[ -f "$PNG" ] || { echo "PNG not found: $PNG"; exit 1; }

# Portable size in bytes
fsize() { wc -c < "$1" | tr -d '[:space:]'; }
# Human-readable size
human() {
  awk -v b="$1" 'function human(x){ s="B KMGTPE";i=0;while (x>=1024 && i<6){x/=1024;i++} return sprintf("%.1f %s", x, substr(s, i*2+1, 1)) } BEGIN{print human(b)}'
}

# Bitrate via ffprobe (bps -> kb/s)
vbit() { ffprobe -v error -select_streams v:0 -show_entries stream=bit_rate -of default=nk=1:nw=1 "$1" 2>/dev/null || true; }
abit() { ffprobe -v error -select_streams a:0 -show_entries stream=bit_rate -of default=nk=1:nw=1 "$1" 2>/dev/null || true; }
# Duration (s)
dur() { ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 "$1"; }

measure() {
  local label="$1"; shift
  local start end secs
  start="$(date +%s)"
  "$@"
  end="$(date +%s)"
  secs=$(( end - start ))
  echo "$secs"
}

echo "== tcap bench =="
echo "Input: $IN"
echo "Thumb: $PNG"
echo

# 1) CRF sweep (low/def/high)
echo "→ Building (CRF=${CRF_LOW}/${CRF_DEF}/${CRF_HIGH})..."
t_low_s=$(measure "CRF${CRF_LOW}" tcap --video "$IN" --thumb "$PNG" --out "$OUT_LOW"  --crf "$CRF_LOW")
t_def_s=$(measure "CRF${CRF_DEF}" tcap --video "$IN" --thumb "$PNG" --out "$OUT_DEF"  --crf "$CRF_DEF")
t_hig_s=$(measure "CRF${CRF_HIGH}" tcap --video "$IN" --thumb "$PNG" --out "$OUT_HIGH" --crf "$CRF_HIGH")

# 2) Copy-concat vs re-encode (at default CRF)
echo "→ Building (copy-concat vs re-encode)..."
t_copy_s=$(measure "COPY" tcap --video "$IN" --thumb "$PNG" --out "$OUT_COPY" --crf "$CRF_DEF")
t_renc_s=$(measure "RENC" tcap --video "$IN" --thumb "$PNG" --out "$OUT_RENC" --crf "$CRF_DEF" --no-copy-concat)

# Collect stats
ref_dur=$(dur "$IN")

row() {
  local name="$1" file="$2" secs="$3"
  local sz bytes vb ab
  bytes=$(fsize "$file")
  sz=$(human "$bytes")
  vb=$(vbit "$file"); ab=$(abit "$file")
  # Convert bps to kb/s if present
  [[ -n "$vb" ]] && vb_kbps=$(( vb / 1000 )) || vb_kbps=-
  [[ -n "$ab" ]] && ab_kbps=$(( ab / 1000 )) || ab_kbps=-
  printf "%-22s %-10s %6ss   v=%-7s  a=%-7s  (%s)\n" "$name" "$sz" "$secs" "${vb_kbps}k" "${ab_kbps}k" "$(basename "$file")"
}

echo
echo "== Summary =="
echo "Reference duration: ${ref_dur}s"
echo
printf "%-22s %-10s %6s   %-8s %-8s  %s\n" "Variant" "Size" "Time" "v_bitrate" "a_bitrate" "File"
printf "%-22s %-10s %6s   %-8s %-8s  %s\n" "------" "----" "----" "--------" "--------" "----"
row "CRF ${CRF_LOW}"  "$OUT_LOW"  "$t_low_s"
row "CRF ${CRF_DEF}"  "$OUT_DEF"  "$t_def_s"
row "CRF ${CRF_HIGH}" "$OUT_HIGH" "$t_hig_s"
row "COPY (default)"  "$OUT_COPY" "$t_copy_s"
row "RE-ENCODE"       "$OUT_RENC" "$t_renc_s"

