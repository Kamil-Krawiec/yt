#!/usr/bin/env bash
# install_tcap.sh — installer for the `tcap` thumbnail helper CLI.
# Run this script to set up the CLI plus dependencies automatically.

set -euo pipefail

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  export PATH="/usr/sbin:/usr/bin:/sbin:/bin"
  unset PYTHONPATH PYTHONHOME PYTHONUSERBASE \
        LD_PRELOAD LD_LIBRARY_PATH DYLD_LIBRARY_PATH
fi
IFS=$'\n\t'
umask 022

APP="tcap"
VERSION="1.0.0"
SCRIPT_NAME="$(basename "$0")"

SYSTEM_PREFIX="/opt/$APP"
SYSTEM_BIN_DIR="/usr/local/bin"
USER_PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/$APP"
USER_BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"

INSTALL_MODE="auto"
PREFIX=""
BIN_DIR=""
FORCE=0
SKIP_PACKAGE_INSTALL=0
APT_UPDATED=0

log_info()  { printf '[%s] %s\n' "$APP" "$*"; }
log_warn()  { printf '[%s] WARN: %s\n' "$APP" "$*" >&2; }
log_error() { printf '[%s] ERROR: %s\n' "$APP" "$*" >&2; }
need_cmd()  { command -v "$1" >/dev/null 2>&1; }

usage() {
  cat <<USAGE
$SCRIPT_NAME $VERSION — install the '$APP' CLI

Usage: $SCRIPT_NAME [options]

Options:
  --system         Install for every user (into /opt/$APP with launcher at /usr/local/bin)
  --user           Install just for you (into ~/.local/share/$APP with launcher at ~/.local/bin)
  --prefix DIR     Install into DIR (combine with --bin-dir for a custom launcher path)
  --bin-dir DIR    Place the launcher script in DIR
  --force          Reinstall even if files already exist (recreates the virtualenv)
  --skip-packages  Do not install system packages automatically
  -h, --help       Show this help and exit

Examples:
  ./$SCRIPT_NAME             # user install in ~/.local
  sudo ./$SCRIPT_NAME        # system install using sudo
  sudo ./$SCRIPT_NAME --force  # rebuild an existing system install
USAGE
}

detect_pkg_manager() {
  for candidate in apt-get dnf yum pacman zypper apk brew; do
    if need_cmd "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  printf 'none\n'
}

install_packages() {
  local pm="$1"; shift
  local runner=()

  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    if need_cmd sudo; then
      runner=(sudo -E)
    else
      log_error "Need sudo/root privileges to install packages. Install dependencies manually."
      exit 1
    fi
  fi

  case "$pm" in
    apt-get)
      if [ $APT_UPDATED -eq 0 ]; then
        "${runner[@]}" env DEBIAN_FRONTEND=noninteractive apt-get update -y
        APT_UPDATED=1
      fi
      "${runner[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
      ;;
    dnf)
      "${runner[@]}" dnf install -y "$@"
      ;;
    yum)
      "${runner[@]}" yum install -y "$@"
      ;;
    pacman)
      "${runner[@]}" pacman -Sy --noconfirm "$@"
      ;;
    zypper)
      "${runner[@]}" zypper --non-interactive install "$@"
      ;;
    apk)
      "${runner[@]}" apk add --no-cache "$@"
      ;;
    brew)
      brew install "$@"
      ;;
    *)
      log_error "Package manager '$pm' is not supported."
      exit 1
      ;;
  esac
}

ensure_dependency() {
  local binary="$1" package_hint="$2"
  if need_cmd "$binary"; then
    return
  fi
  if [ $SKIP_PACKAGE_INSTALL -eq 1 ]; then
    log_error "Missing dependency '$binary'. Install package '$package_hint' manually and rerun."
    exit 1
  fi
  log_info "Installing dependency: $package_hint"
  install_packages "$PKG_MANAGER" "$package_hint"
  if ! need_cmd "$binary"; then
    log_error "Dependency '$binary' is still missing after attempted install."
    exit 1
  fi
}

ensure_path_visibility() {
  local target_dir="$1"
  local mode="$2"

  if [ -z "$target_dir" ]; then
    return 1
  fi

  if printf ':%s:' "$PATH" | grep -q ":$target_dir:"; then
    hash -r 2>/dev/null || true
    return 0
  fi

  if [ "$mode" = "system" ]; then
    return 1
  fi

  case "$target_dir" in
    "$HOME"/*) ;;
    *)
      return 1
      ;;
  esac

  local profiles=("$HOME/.profile" "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.zprofile" "$HOME/.zshrc")
  local profile=""
  for candidate in "${profiles[@]}"; do
    if [ -f "$candidate" ]; then
      profile="$candidate"
      break
    fi
  done
  if [ -z "$profile" ]; then
    profile="$HOME/.profile"
    touch "$profile"
  fi

  local now
  now="$(date -u '+%Y-%m-%d %H:%M:%SZ')"

  if ! grep -F "$target_dir" "$profile" >/dev/null 2>&1; then
    if ! {
      printf '\n# Added by install_tcap.sh (%s)\n' "$now"
      printf 'export PATH="%s:$PATH"\n' "$target_dir"
    } >> "$profile"; then
      log_warn "Could not update $profile automatically. Add $target_dir to PATH manually."
      return 1
    fi
    log_info "Appended $target_dir to PATH in $profile (new shells will use it)."
  else
    log_info "$profile already references $target_dir."
  fi

  if ! printf ':%s:' "$PATH" | grep -q ":$target_dir:"; then
    PATH="$target_dir:$PATH"
    export PATH
  fi

  log_info "To use $APP immediately, run: export PATH=\"$target_dir:\$PATH\""
  hash -r 2>/dev/null || true
  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --system) INSTALL_MODE="system" ;;
    --user) INSTALL_MODE="user" ;;
    --prefix)
      [[ $# -lt 2 ]] && { log_error "--prefix requires a directory"; exit 1; }
      PREFIX="$2"; shift ;;
    --bin-dir)
      [[ $# -lt 2 ]] && { log_error "--bin-dir requires a directory"; exit 1; }
      BIN_DIR="$2"; shift ;;
    --force) FORCE=1 ;;
    --skip-packages) SKIP_PACKAGE_INSTALL=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log_error "Unknown option '$1'"
      usage
      exit 1
      ;;
  esac
  shift
done

if [ "$INSTALL_MODE" = "auto" ]; then
  if [ "${EUID:-$(id -u)}" -eq 0 ]; then
    INSTALL_MODE="system"
  else
    INSTALL_MODE="user"
  fi
fi

PKG_MANAGER="$(detect_pkg_manager)"

if [ -z "$PREFIX" ]; then
  if [ "$INSTALL_MODE" = "system" ]; then
    PREFIX="$SYSTEM_PREFIX"
  else
    PREFIX="$USER_PREFIX"
  fi
fi

if [ -z "$BIN_DIR" ]; then
  if [ "$INSTALL_MODE" = "system" ]; then
    BIN_DIR="$SYSTEM_BIN_DIR"
  else
    BIN_DIR="$USER_BIN_DIR"
  fi
fi

if [ "$INSTALL_MODE" = "system" ] && [ "${EUID:-$(id -u)}" -ne 0 ]; then
  if ! need_cmd sudo; then
    log_error "System-wide install requires sudo/root privileges. Re-run with sudo or use --user."
    exit 1
  fi
  log_info "Re-running under sudo for system installation..."
  args=("--system")
  if [ $FORCE -eq 1 ]; then args+=("--force"); fi
  if [ $SKIP_PACKAGE_INSTALL -eq 1 ]; then args+=("--skip-packages"); fi
  if [ -n "$PREFIX" ]; then args+=("--prefix" "$PREFIX"); fi
  if [ -n "$BIN_DIR" ]; then args+=("--bin-dir" "$BIN_DIR"); fi
  exec sudo -- "$0" "${args[@]}"
fi

INSTALL_DIR="$PREFIX"
VENV_DIR="$INSTALL_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python3"
ENTRYPOINT="$INSTALL_DIR/$APP.py"
LAUNCHER="$BIN_DIR/$APP"

log_info "Installing $APP $VERSION"
log_info "Install mode: $INSTALL_MODE"
log_info "Install dir: $INSTALL_DIR"
log_info "Launcher dir: $BIN_DIR"

if ! need_cmd install; then
  log_error "Required command 'install' (coreutils) not found."
  exit 1
fi

if [ $SKIP_PACKAGE_INSTALL -eq 0 ] && [ "$PKG_MANAGER" = "none" ]; then
  log_warn "No supported package manager detected; dependencies must already be present."
fi

ensure_dependency python3 python3
if [ "$PKG_MANAGER" = "apt-get" ] && [ $SKIP_PACKAGE_INSTALL -eq 0 ]; then
  if ! python3 -m venv --help >/dev/null 2>&1; then
    log_info "Installing python3-venv"
    install_packages "$PKG_MANAGER" python3-venv
  fi
fi

ensure_dependency ffmpeg ffmpeg
if ! need_cmd ffprobe; then
  if [ $SKIP_PACKAGE_INSTALL -eq 0 ] && [ "$PKG_MANAGER" != "none" ]; then
    log_info "Installing ffprobe (provided by most ffmpeg packages)"
    install_packages "$PKG_MANAGER" ffmpeg || true
  fi
  if ! need_cmd ffprobe; then
    log_error "ffprobe still missing. Install ffmpeg/ffprobe manually and rerun."
    exit 1
  fi
fi

if [ $FORCE -eq 1 ]; then
  log_info "--force requested: removing previous virtualenv and launcher"
  rm -rf "$VENV_DIR"
  rm -f "$ENTRYPOINT" "$LAUNCHER"
fi

log_info "Creating directories"
install -d -m 0755 "$INSTALL_DIR"
install -d -m 0755 "$BIN_DIR"

if [ ! -d "$VENV_DIR" ]; then
  log_info "Creating virtual environment"
  python3 -m venv "$VENV_DIR"
else
  log_info "Using existing virtual environment"
fi

log_info "Upgrading pip inside the virtual environment"
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null

log_info "Writing CLI entry point to $ENTRYPOINT"
cat > "$ENTRYPOINT" <<'PY'
#!/usr/bin/env python3
"""tcap CLI: append a still PNG to the end of an MP4 for thumbnail selection."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

VERSION = os.environ.get("TCAP_CLI_VERSION", "unknown")


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float
    has_audio: bool


class CommandError(RuntimeError):
    """Raised when a subprocess exits with a non-zero status."""


def run_capture(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        quoted = " ".join(shlex.quote(arg) for arg in cmd)
        raise CommandError(f"Command failed ({process.returncode}): {quoted}\nSTDERR:\n{process.stderr}")
    return process


def run_json(cmd: list[str]) -> dict:
    return json.loads(run_capture(cmd).stdout or "{}")


def run_text(cmd: list[str]) -> str:
    return run_capture(cmd).stdout.strip()


def ffprobe_props(video_path: Path) -> VideoInfo:
    if not video_path.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")

    meta = run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate",
            "-of",
            "json",
            str(video_path),
        ]
    )
    try:
        stream = meta["streams"][0]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unable to read video stream metadata from {video_path}") from exc

    width = int(stream["width"])
    height = int(stream["height"])
    frame_rate = stream.get("avg_frame_rate", "30/1")
    try:
        num, den = frame_rate.split("/")
        fps = float(num) / float(den) if float(den) != 0 else float(num)
    except Exception:
        fps = 30.0

    try:
        duration = float(
            run_text(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(video_path),
                ]
            )
        )
    except Exception:
        duration = 0.0

    has_audio = False
    try:
        audio_meta = run_json(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "json",
                str(video_path),
            ]
        )
        has_audio = bool(audio_meta.get("streams"))
    except Exception:
        has_audio = False

    return VideoInfo(width, height, fps, duration, has_audio)


def append_thumbnail(
    mp4_path: Path,
    png_path: Path,
    out_path: Path,
    *,
    duration: float = 0.3,
    crf: int = 18,
    audio_bitrate: str = "192k",
) -> None:
    if not mp4_path.exists():
        raise FileNotFoundError(f"Input video not found: {mp4_path}")
    if not png_path.exists():
        raise FileNotFoundError(f"Thumbnail PNG not found: {png_path}")

    info = ffprobe_props(mp4_path)

    still_chain = (
        f"[1:v]scale={info.width}:{info.height},fps={info.fps:.6f},"
        f"format=yuv420p,setsar=1,trim=duration={duration},setpts=PTS-STARTPTS[v1]"
    )

    if info.has_audio:
        a0_chain = "[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a0]"
    else:
        a0_chain = (
            f"anullsrc=r=48000:cl=stereo,atrim=duration={info.duration:.6f},"
            "asetpts=PTS-STARTPTS[a0]"
        )

    a1_chain = f"anullsrc=r=48000:cl=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS[a1]"
    v0_chain = "[0:v]setpts=PTS-STARTPTS[v0]"
    filter_graph = ";".join(
        [
            v0_chain,
            a0_chain,
            still_chain,
            a1_chain,
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
        ]
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp4_path),
        "-loop",
        "1",
        "-t",
        f"{duration}",
        "-i",
        str(png_path),
        "-filter_complex",
        filter_graph,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.1",
        "-crf",
        str(crf),
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    run_capture(cmd)


def show_info() -> None:
    entry = Path(__file__).resolve()
    install_dir = entry.parent
    venv_dir = install_dir / ".venv"
    python_bin = venv_dir / "bin" / "python3"
    ffmpeg_path = shutil.which("ffmpeg") or "not on PATH"
    ffprobe_path = shutil.which("ffprobe") or "not on PATH"

    print(f"[tcap] Version: {VERSION}")
    print(f"[tcap] Entry point: {entry}")
    print(f"[tcap] Install dir: {install_dir}")
    print(f"[tcap] Virtualenv: {venv_dir}")
    print(f"[tcap] Python: {python_bin}")
    print(f"[tcap] ffmpeg: {ffmpeg_path}")
    print(f"[tcap] ffprobe: {ffprobe_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tcap",
        description="Append a PNG still to the end of an MP4 (default 0.3s) to aid thumbnail selection.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--pair",
        type=Path,
        help="Pair mode: provide an MP4; the PNG is inferred as <stem>.png",
    )
    group.add_argument(
        "-v",
        "--video",
        type=Path,
        help="Explicit MP4 path (use with -t/--thumb)",
    )
    group.add_argument(
        "--info",
        action="store_true",
        help="Show install details and version information, then exit",
    )
    parser.add_argument(
        "-t",
        "--thumb",
        type=Path,
        help="Explicit PNG path (required with -v/--video)",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        help="Output MP4 path (default: <stem>_thumb.mp4)",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=0.3,
        help="Still duration in seconds (default: 0.3)",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="x264 CRF quality (lower = higher quality/larger files) (default: 18)",
    )
    parser.add_argument(
        "--audio-bitrate",
        default="192k",
        help="AAC audio bitrate to use for the appended still (default: 192k)",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="the processed video overwrites the original (atomic replace in the same folder). Without it, a new <name>_thumb.mp4 is created in the current directory. (default: false)",
    )
    args = parser.parse_args()
    if args.info:
        return args
    if not (args.pair or args.video):
        parser.print_help()
        parser.exit(0)
    return args


def main() -> None:
    args = parse_args()

    if args.info:
        show_info()
        return

    if args.pair:
        mp4 = args.pair
        png = args.pair.with_suffix(".png")
    else:
        if not args.video or not args.thumb:
            sys.exit("When using -v/--video you must also pass -t/--thumb.")
        mp4 = args.video
        png = args.thumb

    output = args.out or mp4.with_name(mp4.stem + "_thumb.mp4")

    if args.inplace:
      # Write a temporary file in the SAME directory as the input MP4
      # so the final replace is atomic and not cross-filesystem.
      with tempfile.NamedTemporaryFile(
          prefix=f"{mp4.stem}_tmp_",
          suffix=mp4.suffix,
          dir=str(mp4.parent),
          delete=False,
      ) as tf:
          tmp_path = Path(tf.name)

      try:
          append_thumbnail(
              mp4,
              png,
              tmp_path,
              duration=args.duration,
              crf=args.crf,
              audio_bitrate=args.audio_bitrate,
          )
          # Atomically replace the original file
          tmp_path.replace(mp4)
          print(f"[tcap] Updated in place: {mp4}")
      except Exception:
          # Best-effort cleanup if something goes wrong
          try:
              tmp_path.unlink()
          except FileNotFoundError:
              pass
          raise
    else:
        append_thumbnail(
            mp4,
            png,
            output,
            duration=args.duration,
            crf=args.crf,
            audio_bitrate=args.audio_bitrate,
        )
        print(f"[tcap] Done: {output}")


if __name__ == "__main__":
    try:
        main()
    except CommandError as exc:
        print(f"[tcap] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # pragma: no cover - safeguard
        print(f"[tcap] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
PY
chmod +x "$ENTRYPOINT"

log_info "Creating launcher at $LAUNCHER"
cat > "$LAUNCHER" <<LAUNCHER
#!/usr/bin/env bash
export TCAP_CLI_VERSION="$VERSION"
exec "$PYTHON_BIN" "$ENTRYPOINT" "\$@"
LAUNCHER
chmod +x "$LAUNCHER"

preexisting_path="$(command -v "$APP" 2>/dev/null || true)"
if ensure_path_visibility "$BIN_DIR" "$INSTALL_MODE"; then
  log_info "Configured PATH to include $BIN_DIR."
else
  log_warn "Launcher directory $BIN_DIR is not on PATH. Invoke '$LAUNCHER' directly or add it manually."
fi

post_path="$(command -v "$APP" 2>/dev/null || true)"
if [ -n "$preexisting_path" ] && [ "$preexisting_path" != "$LAUNCHER" ]; then
  log_warn "A previous '$APP' was detected at $preexisting_path. Remove it if you prefer the new launcher to take precedence."
fi
if [ -n "$post_path" ] && [ "$post_path" != "$LAUNCHER" ]; then
  log_warn "Another '$APP' is still first on PATH at $post_path. Adjust PATH or remove it so $LAUNCHER is picked up."
fi

log_info "Installation complete. Try: $APP --info"
log_info "To start using it in the same terminal session, you can either run export command listed above or refresh your shell with 'exec bash -l' (or exec zsh -l)."
