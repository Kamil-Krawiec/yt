#!/usr/bin/env python3
"""tcap CLI: append a still PNG to the end of an MP4/MOV without touching the base video."""

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
    codec_name: str
    pix_fmt: str
    sample_aspect_ratio: str
    time_base_num: int
    time_base_den: int


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
            "stream=width,height,avg_frame_rate,codec_name,pix_fmt,sample_aspect_ratio,time_base",
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

    codec_name = str(stream.get("codec_name", "") or "")
    pix_fmt = str(stream.get("pix_fmt", "") or "")

    sar = str(stream.get("sample_aspect_ratio", "") or "1:1")

    time_base = str(stream.get("time_base", "") or "1/1000")
    try:
        tb_num_str, tb_den_str = time_base.split("/")
        tb_num = int(tb_num_str)
        tb_den = int(tb_den_str)
    except Exception:
        tb_num = 1
        tb_den = 1000
    if tb_num <= 0:
        tb_num = 1
    if tb_den <= 0:
        tb_den = 1000

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

    return VideoInfo(width, height, fps, duration, has_audio, codec_name, pix_fmt, sar, tb_num, tb_den)


def append_thumbnail(
    mp4_path: Path,
    png_path: Path,
    out_path: Path,
    *,
    duration: float = 0.3,
    crf: int = 18,
) -> None:
    if not mp4_path.exists():
        raise FileNotFoundError(f"Input video not found: {mp4_path}")
    if not png_path.exists():
        raise FileNotFoundError(f"Thumbnail PNG not found: {png_path}")

    info = ffprobe_props(mp4_path)
    if duration <= 0:
        raise ValueError("Duration must be greater than zero.")

    suffix = mp4_path.suffix.lower()
    if suffix not in {".mp4", ".mov"}:
        raise ValueError("Only .mp4 and .mov containers are supported.")

    fps = info.fps if info.fps > 0 else 30.0
    pix_fmt = info.pix_fmt or "yuv420p"
    codec_name = info.codec_name.lower()
    sar = info.sample_aspect_ratio or "1:1"
    if sar in {"0:1", "1:0"}:
        sar = "1:1"

    # Minimal mapping: we only support codecs that can safely be concatenated without a
    # full transcode of the source segment.
    encoder_map: dict[str, list[str]] = {
        "h264": ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf)],
        "hevc": ["-c:v", "libx265", "-preset", "medium", "-crf", str(crf)],
        "h265": ["-c:v", "libx265", "-preset", "medium", "-crf", str(crf)],
        "mpeg4": ["-c:v", "mpeg4", "-qscale:v", "2"],
        "prores": ["-c:v", "prores_ks"],
        "prores_ks": ["-c:v", "prores_ks"],
    }

    if codec_name not in encoder_map:
        raise RuntimeError(
            f"Unsupported source codec '{codec_name or 'unknown'}' for thumbnail appending without re-encode."
        )

    still_filters = [
        f"scale={info.width}:{info.height}",
        f"fps={fps:.6f}",
    ]
    if pix_fmt:
        still_filters.append(f"format={pix_fmt}")
    if sar:
        still_filters.append(f"setsar={sar}")
    still_filter = ",".join(still_filters)

    timescale = 0
    if info.time_base_num == 1 and info.time_base_den > 0:
        timescale = info.time_base_den  # match the source track tick rate so concat stays in sync

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        source_video_only = tmp_root / f"source_video{suffix}"
        still_clip = tmp_root / f"still{suffix}"
        concat_file = tmp_root / "concat.txt"
        video_concat = tmp_root / f"concat_video{suffix}"
        source_audio = tmp_root / "source_audio.mka"

        run_capture(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(mp4_path),
                "-map",
                "0:v:0",
                "-c",
                "copy",
                str(source_video_only),
            ]
        )

        if info.has_audio:
            run_capture(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(mp4_path),
                    "-map",
                    "0:a:0",
                    "-c",
                    "copy",
                    str(source_audio),
                ]
            )

        still_cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(png_path),
            "-vf",
            still_filter,
            "-t",
            f"{duration:.6f}",
            "-r",
            f"{fps:.6f}",
            "-an",
            "-pix_fmt",
            pix_fmt,
        ]
        still_cmd.extend(encoder_map[codec_name])
        if codec_name in {"h264", "hevc", "h265"}:
            gop = max(1, int(round(fps * duration)))
            still_cmd.extend(["-g", str(gop), "-keyint_min", "1", "-sc_threshold", "0"])
            if codec_name in {"hevc", "h265"}:
                still_cmd.extend(["-x265-params", f"keyint={gop}:min-keyint=1:scenecut=0"])
            else:
                still_cmd.extend(["-x264-params", f"keyint={gop}:min-keyint=1:scenecut=0"])
        if codec_name.startswith("prores"):
            still_cmd.extend(["-profile:v", "3"])
        if timescale:
            still_cmd.extend(["-video_track_timescale", str(timescale)])
        still_cmd.extend(["-movflags", "+faststart", str(still_clip)])
        run_capture(still_cmd)

        def escape_concat_path(path: Path) -> str:
            return str(path).replace("'", "'\\''")

        concat_file.write_text(
            "\n".join(
                [
                    f"file '{escape_concat_path(source_video_only)}'",
                    f"file '{escape_concat_path(still_clip)}'",
                ]
            )
            + "\n"
        )

        # Final concat keeps the original stream untouched and simply appends the
        # freshly encoded still segment.
        run_capture(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(video_concat),
            ]
        )

        final_tmp = video_concat
        if info.has_audio and source_audio.exists():
            muxed = tmp_root / f"muxed{suffix}"
            run_capture(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_concat),
                    "-i",
                    str(source_audio),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(muxed),
                ]
            )
            final_tmp = muxed

        out_path.parent.mkdir(parents=True, exist_ok=True)
        final_tmp.replace(out_path)


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
        description="Append a PNG still to the end of an MP4/MOV (video-only, default 0.3s) without re-encoding the source clip.",
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
        help="CRF quality used for encoding the still clip when h264/hevc (default: 18)",
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