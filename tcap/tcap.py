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