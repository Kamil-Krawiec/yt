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

def ensure_tools() -> None:
    """Ensure ffmpeg and ffprobe are available on PATH."""
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(f"Missing required tools: {', '.join(missing)}")

def _h264_level_to_str(level_val) -> str | None:
    """
    Convert ffprobe's numeric level (e.g. 41) or string ('4.1') to ffmpeg-expected string ('4.1').
    Returns None if cannot interpret.
    """
    if level_val is None:
        return None
    s = str(level_val).strip()
    # Already like '4.1'
    try:
        float(s)
        if "." in s:
            return s
    except Exception:
        pass
    # Numeric like '41' -> '4.1', '40' -> '4.0'
    if s.isdigit():
        if len(s) == 2:
            return f"{s[0]}.{s[1]}"
        elif len(s) == 1:
            return f"{s}.0"
    return None


def _fraction_to_float(value: str | None) -> float | None:
    """Convert ffprobe fraction strings (e.g. '30000/1001') to floats."""
    if not value or value in {"0/0", "N/A", "nan", "inf", "-inf"}:
        return None
    if "/" in value:
        num, den = value.split("/", 1)
        try:
            num_f = float(num)
            den_f = float(den)
        except ValueError:
            return None
        if den_f == 0:
            return None
        return num_f / den_f
    try:
        return float(value)
    except ValueError:
        return None


def _is_reasonable_fps(value: float | None) -> bool:
    """Heuristic guardrail for fps values that are usable for concat copy."""
    return value is not None and 1.0 <= value <= 360.0

_PROFILE_MAP = {
    "high": "high",
    "main": "main",
    "baseline": "baseline",
    "constrained baseline": "constrained_baseline",
}

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
            "stream=width,height,duration,avg_frame_rate,r_frame_rate,nb_frames",
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
    duration = None
    duration_field = stream.get("duration")
    if duration_field and duration_field not in {"N/A", "nan"}:
        try:
            duration = float(duration_field)
        except ValueError:
            duration = None

    if duration is None or duration <= 0:
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

    fps_candidates: list[float | None] = []
    for key in ("avg_frame_rate", "r_frame_rate"):
        fps_candidates.append(_fraction_to_float(stream.get(key)))

    nb_frames = None
    nb_frames_raw = stream.get("nb_frames")
    if nb_frames_raw and nb_frames_raw not in {"N/A", "nan"}:
        try:
            nb_frames = float(nb_frames_raw)
        except ValueError:
            nb_frames = None

    if nb_frames and nb_frames > 0 and duration and duration > 0:
        fps_candidates.append(nb_frames / duration)

    fps = 30.0
    valid_candidates = [val for val in fps_candidates if val and val > 0]

    for candidate in valid_candidates:
        if _is_reasonable_fps(candidate):
            fps = candidate
            break
    else:
        for candidate in valid_candidates:
            if candidate >= 1.0:
                fps = min(candidate, 360.0)
                break
        else:
            if valid_candidates:
                fps = 30.0

    if duration and duration < 1.0 and fps < 1.0:
        fps = 30.0

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

def _encode_still_clip(
    png_path: Path,
    still_path: Path,
    *,
    width: int,
    height: int,
    fps: float,
    v_pix_fmt: str,
    v_profile: str | None,
    v_level: str | None,
    colorspace: dict[str, str],
    has_audio: bool,
    a_sample_rate: int | None,
    a_channel_layout: str | None,
    crf: int,
    duration: float,
    audio_bitrate: str,
) -> None:
    # Build video filter: scale/pad to exact WxH, keep aspect, set SAR, pixel format & colors
    vf = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        "pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black".format(w=width, h=height),
        "setsar=1",
        f"fps={fps:.6f}",
        f"format={v_pix_fmt}",
    ]
    vf = ",".join(vf)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(png_path),
    ]

    # Add a short silent audio only if the input had audio (to keep stream layout identical)
    if has_audio:
        sr = a_sample_rate or 48000
        cl = a_channel_layout or "stereo"
        cmd += ["-f", "lavfi", "-t", f"{duration}", "-i", f"anullsrc=channel_layout={cl}:sample_rate={sr}"]

    cmd += [
        "-t", f"{duration}",
        "-vf", vf,
        "-r", f"{fps:.6f}",
        "-c:v", "libx264",
        "-pix_fmt", v_pix_fmt,
        "-preset", "veryslow",
        "-tune", "stillimage",
        "-crf", str(crf),
    ]

    # Match profile/level if known (helps concat copy)
    if v_profile:
        cmd += ["-profile:v", v_profile]
    if v_level:
        cmd += ["-level:v", v_level]

    # Color tags (bt709, etc.) – improves matching
    if colorspace.get("space"):
        cmd += ["-colorspace", colorspace["space"]]
    if colorspace.get("trc"):
        cmd += ["-color_trc", colorspace["trc"]]
    if colorspace.get("primaries"):
        cmd += ["-color_primaries", colorspace["primaries"]]

    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", audio_bitrate, "-shortest"]
    else:
        cmd += ["-an"]

    cmd += ["-movflags", "+faststart", str(still_path)]
    run_capture(cmd)


def _concat_copy(input_mp4: Path, still_mp4: Path, out_path: Path) -> None:
    # Concat demuxer requires a list file; -c copy avoids re-encoding
    with tempfile.TemporaryDirectory() as td:
        lst = Path(td) / "list.txt"
        lst.write_text(f"file '{input_mp4.resolve()}'\nfile '{still_mp4.resolve()}'\n", encoding="utf-8")
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out_path)]
        run_capture(cmd)

def append_thumbnail(
    mp4_path: Path,
    png_path: Path,
    out_path: Path,
    *,
    duration: float = 0.3,
    crf: int = 18,
    audio_bitrate: str = "192k",
    allow_copy_concat: bool = True,
) -> None:
    if not mp4_path.exists():
        raise FileNotFoundError(f"Input video not found: {mp4_path}")
    if not png_path.exists():
        raise FileNotFoundError(f"Thumbnail PNG not found: {png_path}")

    info = ffprobe_props(mp4_path)

    # Extra probe to decide if we can "copy-concat" (no re-encode of the main file)
    vmeta = run_json([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=codec_name,pix_fmt,profile,level,color_space,color_transfer,color_primaries,sample_aspect_ratio",
        "-of","json", str(mp4_path)
    ])
    ameta = run_json([
        "ffprobe","-v","error","-select_streams","a:0",
        "-show_entries","stream=codec_name,channel_layout,sample_rate",
        "-of","json", str(mp4_path)
    ])

    vstream = (vmeta.get("streams") or [{}])[0]
    astream = (ameta.get("streams") or [{}])[0] if info.has_audio else {}

    vcodec = vstream.get("codec_name")
    v_pix_fmt = vstream.get("pix_fmt", "yuv420p")
    _vp_raw = (vstream.get("profile") or "").strip().lower()
    v_profile = _PROFILE_MAP.get(_vp_raw) if _vp_raw else None
    v_level = _h264_level_to_str(vstream.get("level"))
    colors = {
        "space": vstream.get("color_space"),
        "trc": vstream.get("color_transfer"),
        "primaries": vstream.get("color_primaries"),
    }

    acodec = astream.get("codec_name")
    a_sr = int(astream.get("sample_rate")) if astream.get("sample_rate") else None
    a_cl = astream.get("channel_layout")

    # We can try concat-copy if video is H.264 and (no audio or AAC audio)
    can_concat_copy = (
        allow_copy_concat
        and (vcodec == "h264")
        and (not info.has_audio or acodec == "aac")
    )

    if can_concat_copy:
        with tempfile.TemporaryDirectory() as td:
            still_mp4 = Path(td) / "still.mp4"
            # Encode ONLY the 0.3 s tail with matching parameters
            _encode_still_clip(
                png_path, still_mp4,
                width=info.width, height=info.height, fps=info.fps,
                v_pix_fmt=v_pix_fmt, v_profile=v_profile, v_level=v_level,
                colorspace=colors,
                has_audio=info.has_audio, a_sample_rate=a_sr, a_channel_layout=a_cl,
                crf=crf, duration=duration, audio_bitrate=audio_bitrate,
            )
            try:
                _concat_copy(mp4_path, still_mp4, out_path)
                return  # success, no re-encode of main video/audio
            except CommandError:
                # fall back to full re-encode path below
                pass

    # Fallback: original filter_complex path (re-encodes the whole file)
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
    filter_graph = ";".join([v0_chain, a0_chain, still_chain, a1_chain, "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"])

    cmd = [
        "ffmpeg","-y",
        "-i", str(mp4_path),
        "-loop","1","-t", f"{duration}","-i", str(png_path),
        "-filter_complex", filter_graph,
        "-map","[v]","-map","[a]",
        "-c:v","libx264","-pix_fmt","yuv420p","-profile:v","high","-level","4.1",
        "-crf", str(crf), "-preset","medium",
        "-c:a","aac","-b:a", audio_bitrate,
        "-movflags","+faststart",
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
    parser.add_argument(
        "--no-copy-concat",
        action="store_true",
        help="Force full re-encode fallback (disable concat demuxer fast-path).",
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

    ensure_tools()

    if args.pair:
        mp4 = args.pair
        png = args.pair.with_suffix(".png")
    else:
        if not args.video or not args.thumb:
            sys.exit("When using -v/--video you must also pass -t/--thumb.")
        mp4 = args.video
        png = args.thumb

    output = args.out or (Path.cwd() / f"{mp4.stem}_thumb{mp4.suffix}")

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
                allow_copy_concat=not args.no_copy_concat,
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
            allow_copy_concat=not args.no_copy_concat,
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
