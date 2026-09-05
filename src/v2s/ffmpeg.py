from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Iterable, Optional

try:
    import imageio_ffmpeg
except Exception:  # pragma: no cover - optional dependency
    imageio_ffmpeg = None


class FFmpegError(RuntimeError):
    pass


class CancelError(RuntimeError):
    pass


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_PROGRESS_KEYS = {
    "bitrate",
    "drop_frames",
    "dup_frames",
    "frame",
    "fps",
    "out_time",
    "out_time_ms",
    "out_time_us",
    "progress",
    "speed",
    "total_size",
}


def resolve_ffmpeg(explicit: Optional[str | Path] = None) -> str:
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise FFmpegError(f"ffmpeg executable not found: {path}")
        return str(path)

    found = shutil.which("ffmpeg")
    if found:
        return found

    env_path = os.environ.get("FFMPEG_BIN")
    if env_path and Path(env_path).is_file():
        return env_path

    if imageio_ffmpeg is not None:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

    raise FFmpegError(
        "ffmpeg not found. Install ffmpeg on PATH, set FFMPEG_BIN, "
        "or make sure the imageio-ffmpeg dependency is installed."
    )


def run_ffmpeg(
    args: Iterable[str],
    *,
    ffmpeg: Optional[str | Path] = None,
    progress: Optional[Callable[[float], None]] = None,
    duration: Optional[float] = None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    exe = resolve_ffmpeg(ffmpeg)
    cmd = [exe, "-hide_banner", "-nostdin", *[str(item) for item in args]]
    if progress is not None:
        cmd.extend(["-progress", "pipe:1"])

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail: list[str] = []
    assert proc.stdout is not None
    for raw in proc.stdout:
        if cancel_event is not None and cancel_event.is_set():
            proc.terminate()
            break
        line = raw.rstrip()
        if progress is not None and "out_time_ms=" in line:
            try:
                out_ms = int(line.split("=", 1)[1].strip())
                if duration:
                    progress(min(1.0, out_ms / 1_000_000 / duration))
            except ValueError:
                pass
        elif line.strip():
            key = line.split("=", 1)[0].strip()
            if key not in _PROGRESS_KEYS:
                tail.append(line)
        if len(tail) > 40:
            tail = tail[-40:]

    code = proc.wait()
    if cancel_event is not None and cancel_event.is_set():
        raise CancelError("ffmpeg cancelled")
    if code:
        raise FFmpegError("ffmpeg failed:\n" + "\n".join(tail[-20:]))


def extract_audio(
    source: str | Path,
    target: str | Path,
    *,
    ffmpeg: Optional[str | Path] = None,
    progress: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        ffmpeg=ffmpeg,
        progress=progress,
        cancel_event=cancel_event,
    )


def probe_duration(
    media: str | Path,
    *,
    ffmpeg: Optional[str | Path] = None,
) -> Optional[float]:
    exe = resolve_ffmpeg(ffmpeg)
    result = subprocess.run(
        [exe, "-hide_banner", "-i", str(media)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    match = _DURATION_RE.search(result.stdout)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def filter_escape(path: str | Path) -> str:
    text = str(path)
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
