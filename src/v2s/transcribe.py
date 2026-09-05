from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Callable, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .ffmpeg import CancelError, extract_audio


class TranscriptionError(RuntimeError):
    pass


@dataclass
class Segment:
    start: float
    end: float
    text: str


def transcribe_media(
    source: str | Path,
    audio_target: str | Path,
    *,
    model_name: str = "small",
    language: Optional[str] = None,
    device: str = "auto",
    compute_type: str = "default",
    beam_size: int = 5,
    vad_filter: bool = True,
    word_timestamps: bool = False,
    initial_prompt: Optional[str] = None,
    model_dir: Optional[Path] = None,
    ffmpeg: Optional[str | Path] = None,
    console: Optional[Console] = None,
    progress_callback: Optional[Callable[[float, float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> tuple[list[Segment], str, float]:
    extract_audio(source, audio_target, ffmpeg=ffmpeg, cancel_event=cancel_event)

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise TranscriptionError(
            "faster-whisper is not installed. Run: pip install v2s"
        ) from exc

    try:
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            download_root=str(model_dir) if model_dir else None,
        )
    except Exception as exc:
        raise TranscriptionError(f"unable to load Whisper model {model_name!r}: {exc}") from exc

    try:
        segments_iter, info = model.transcribe(
            str(audio_target),
            language=language,
            task="transcribe",
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=word_timestamps,
            initial_prompt=initial_prompt,
        )
    except Exception as exc:
        raise TranscriptionError(f"transcription failed: {exc}") from exc

    duration = float(getattr(info, "duration", 0.0) or 0.0)
    detected = str(getattr(info, "language", "unknown") or "unknown")
    segments: list[Segment] = []

    def append_segment(segment) -> None:
        text = (segment.text or "").strip()
        if text:
            segments.append(
                Segment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=text,
                )
            )

    if progress_callback is not None:
        for segment in segments_iter:
            if cancel_event is not None and cancel_event.is_set():
                raise CancelError("transcription cancelled")
            append_segment(segment)
            if duration:
                progress_callback(min(float(segment.end), duration), duration)
    else:
        progress_columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed:0.1f}/{task.total:0.1f}s"),
            TimeElapsedColumn(),
        ]
        with Progress(*progress_columns, console=console) as progress:
            task = progress.add_task("Transcribing", total=duration or 1)
            for segment in segments_iter:
                if cancel_event is not None and cancel_event.is_set():
                    raise CancelError("transcription cancelled")
                append_segment(segment)
                if duration:
                    progress.update(task, completed=min(float(segment.end), duration))
                else:
                    progress.advance(task)

    return segments, detected, duration
