from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from typing import Callable, Optional

from .ffmpeg import filter_escape, probe_duration, run_ffmpeg
from .subtitles import to_ass


class BurnError(RuntimeError):
    pass


def burn_subtitles(
    video: str | Path,
    subtitle: str | Path,
    output: str | Path,
    *,
    mode: str = "hard",
    language: str = "und",
    ffmpeg: Optional[str | Path] = None,
    video_codec: str = "libx264",
    crf: int = 18,
    preset: str = "medium",
    progress: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    video = Path(video)
    subtitle = Path(subtitle)
    output = Path(output)

    if not video.is_file():
        raise BurnError(f"video not found: {video}")
    if not subtitle.is_file():
        raise BurnError(f"subtitle not found: {subtitle}")
    if output.resolve() == video.resolve():
        raise BurnError("refusing to overwrite the input video")

    output.parent.mkdir(parents=True, exist_ok=True)
    if mode == "hard":
        _burn_hard(video, subtitle, output, ffmpeg, video_codec, crf, preset, progress, cancel_event)
        return
    if mode == "soft":
        _burn_soft(video, subtitle, output, ffmpeg, language, cancel_event)
        return
    raise BurnError(f"unknown burn mode: {mode}")


def _burn_hard(
    video: Path,
    subtitle: Path,
    output: Path,
    ffmpeg: Optional[str | Path],
    video_codec: str,
    crf: int,
    preset: str,
    progress: Optional[Callable[[float], None]],
    cancel_event: Optional[threading.Event],
) -> None:
    with tempfile.TemporaryDirectory(prefix="v2s-") as tmp:
        ass_path = Path(tmp) / "subs.ass"
        to_ass(subtitle, ass_path)
        duration = probe_duration(video, ffmpeg=ffmpeg)
        args = [
            "-y",
            "-i",
            str(video),
            "-vf",
            f"subtitles={filter_escape(ass_path)}",
            "-c:v",
            video_codec,
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(output),
        ]
        run_ffmpeg(
            args,
            ffmpeg=ffmpeg,
            progress=progress,
            duration=duration,
            cancel_event=cancel_event,
        )


def _burn_soft(
    video: Path,
    subtitle: Path,
    output: Path,
    ffmpeg: Optional[str | Path],
    language: str,
    cancel_event: Optional[threading.Event],
) -> None:
    suffix = output.suffix.lower()
    args = [
        "-y",
        "-i",
        str(video),
        "-i",
        str(subtitle),
        "-map",
        "0:v",
        "-map",
        "0:a?",
        "-map",
        "1:0",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-metadata:s:s:0",
        f"language={language}",
    ]
    if suffix in {".mp4", ".m4v", ".mov"}:
        args.extend(["-c:s", "mov_text"])
    elif suffix == ".webm":
        args.extend(["-c:s", "webvtt"])
    args.append(str(output))
    run_ffmpeg(args, ffmpeg=ffmpeg, cancel_event=cancel_event)
