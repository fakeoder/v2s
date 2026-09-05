from __future__ import annotations

import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from . import i18n, models
from .burn import burn_subtitles
from .ffmpeg import probe_duration
from .subtitles import save_subtitles
from .transcribe import Segment, transcribe_media
from .translate import translate_segments


StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[float], None]
CancelEvent = threading.Event


@dataclass
class TranscribeOptions:
    input: Path
    output: Path
    output_format: str = "srt"
    model: str = "small"
    language: Optional[str] = None
    translate_language: Optional[str] = None
    translation_provider: str = "google"
    device: str = "auto"
    compute_type: str = "default"
    beam_size: int = 5
    vad_filter: bool = True
    word_timestamps: bool = False
    initial_prompt: Optional[str] = None
    model_dir: Optional[Path] = None
    ffmpeg: Optional[Path] = None
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    keep_temp: bool = False


@dataclass
class BurnOptions:
    video: Path
    subtitle: Path
    output: Path
    mode: str = "hard"
    language: str = "und"
    video_codec: str = "libx264"
    crf: int = 18
    preset: str = "medium"
    ffmpeg: Optional[Path] = None


@dataclass
class RunOptions:
    video: Path
    video_output: Optional[Path] = None
    subtitle_output: Optional[Path] = None
    burn_mode: str = "hard"
    subtitle_language: str = "und"
    video_codec: str = "libx264"
    crf: int = 18
    preset: str = "medium"
    subtitle_format: str = "srt"
    model: str = "small"
    language: Optional[str] = None
    translate_language: Optional[str] = None
    translation_provider: str = "google"
    device: str = "auto"
    compute_type: str = "default"
    beam_size: int = 5
    vad_filter: bool = True
    word_timestamps: bool = False
    initial_prompt: Optional[str] = None
    model_dir: Optional[Path] = None
    ffmpeg: Optional[Path] = None
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    keep_temp: bool = False


def _emit(status: Optional[StatusCallback], key: str, **kwargs) -> None:
    if status is not None:
        status(i18n.t(key, **kwargs))


def _temp_dir(keep: bool):
    directory = Path(tempfile.mkdtemp(prefix="v2s-"))
    try:
        yield directory
    finally:
        if not keep:
            shutil.rmtree(directory, ignore_errors=True)


def _to_frac_progress(
    progress: Optional[ProgressCallback],
) -> Optional[Callable[[float, float], None]]:
    if progress is None:
        return None

    def update(completed: float, total: float) -> None:
        progress(min(1.0, completed / total) if total else 0.0)

    return update


def _transcribe(
    *,
    source: Path,
    audio: Path,
    model: str,
    language: Optional[str],
    device: str,
    compute_type: str,
    beam_size: int,
    vad_filter: bool,
    word_timestamps: bool,
    initial_prompt: Optional[str],
    model_dir: Optional[Path],
    ffmpeg: Optional[Path],
    status: Optional[StatusCallback],
    progress: Optional[ProgressCallback],
    cancel: Optional[CancelEvent],
    console: Optional[Console],
) -> tuple[list[Segment], str, float]:
    models.ensure_model_known(model)
    _emit(status, "extracting_audio")
    _emit(status, "transcribing")
    segments, detected, duration = transcribe_media(
        source,
        audio,
        model_name=model,
        language=language,
        device=device,
        compute_type=compute_type,
        beam_size=beam_size,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps,
        initial_prompt=initial_prompt,
        model_dir=model_dir,
        ffmpeg=ffmpeg,
        console=console,
        progress_callback=_to_frac_progress(progress),
        cancel_event=cancel,
    )
    _emit(
        status,
        "summary",
        language=detected,
        duration=duration,
        count=len(segments),
    )
    return segments, detected, duration


def _translate(
    segments: list[Segment],
    detected: str,
    target_language: Optional[str],
    provider: str,
    status: Optional[StatusCallback],
    progress: Optional[ProgressCallback],
    cancel: Optional[CancelEvent],
) -> list[Segment]:
    if not target_language:
        return segments
    if detected.lower() == target_language.lower():
        _emit(status, "translation_skipped")
        return segments
    _emit(status, "translating_to", language=target_language)
    return translate_segments(
        segments,
        target_language,
        source_language=detected,
        provider=provider,
        progress_callback=_to_frac_progress(progress),
        cancel_event=cancel,
    )


def _burn(
    video: Path,
    subtitle: Path,
    output: Path,
    *,
    mode: str,
    language: str,
    video_codec: str,
    crf: int,
    preset: str,
    ffmpeg: Optional[Path],
    status: Optional[StatusCallback],
    progress: Optional[ProgressCallback],
    cancel: Optional[CancelEvent],
    console: Optional[Console],
) -> None:
    if mode != "hard":
        _emit(status, "muxing")
        burn_subtitles(
            video,
            subtitle,
            output,
            mode=mode,
            language=language,
            ffmpeg=ffmpeg,
            cancel_event=cancel,
        )
        return

    duration = probe_duration(video, ffmpeg=ffmpeg)
    if progress is not None:
        _emit(status, "burning")
        burn_subtitles(
            video,
            subtitle,
            output,
            mode=mode,
            language=language,
            ffmpeg=ffmpeg,
            video_codec=video_codec,
            crf=crf,
            preset=preset,
            progress=progress,
            cancel_event=cancel,
        )
        return

    if console is not None:
        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed:0.1f}/{task.total:0.1f}s"),
            TimeElapsedColumn(),
        ]
        with Progress(*columns, console=console) as console_progress:
            task = console_progress.add_task(
                i18n.t("burning"),
                total=duration or 1,
            )
            burn_subtitles(
                video,
                subtitle,
                output,
                mode=mode,
                language=language,
                ffmpeg=ffmpeg,
                video_codec=video_codec,
                crf=crf,
                preset=preset,
                progress=lambda ratio: console_progress.update(
                    task,
                    completed=(ratio * (duration or 1)),
                ),
                cancel_event=cancel,
            )
        return

    _emit(status, "burning")
    burn_subtitles(
        video,
        subtitle,
        output,
        mode=mode,
        language=language,
        ffmpeg=ffmpeg,
        video_codec=video_codec,
        crf=crf,
        preset=preset,
        cancel_event=cancel,
    )


def transcribe_command(
    opts: TranscribeOptions,
    *,
    status: Optional[StatusCallback] = None,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelEvent] = None,
    console: Optional[Console] = None,
) -> Path:
    if opts.output.resolve() == opts.input.resolve():
        raise ValueError(i18n.t("output_must_differ"))

    with _temp_dir(opts.keep_temp) as tmp:
        audio = tmp / "audio.wav"
        segments, detected, duration = _transcribe(
            source=opts.input,
            audio=audio,
            model=opts.model,
            language=opts.language,
            device=opts.device,
            compute_type=opts.compute_type,
            beam_size=opts.beam_size,
            vad_filter=opts.vad_filter,
            word_timestamps=opts.word_timestamps,
            initial_prompt=opts.initial_prompt,
            model_dir=opts.model_dir,
            ffmpeg=opts.ffmpeg,
            status=status,
            progress=progress,
            cancel=cancel,
            console=console,
        )
        segments = _translate(
            segments,
            detected,
            opts.translate_language,
            opts.translation_provider,
            status,
            progress,
            cancel,
        )
        _emit(status, "saving_subtitle")
        save_subtitles(segments, opts.output, opts.output_format)
    return opts.output


def burn_command(
    opts: BurnOptions,
    *,
    status: Optional[StatusCallback] = None,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelEvent] = None,
    console: Optional[Console] = None,
) -> Path:
    _burn(
        opts.video,
        opts.subtitle,
        opts.output,
        mode=opts.mode,
        language=opts.language,
        video_codec=opts.video_codec,
        crf=opts.crf,
        preset=opts.preset,
        ffmpeg=opts.ffmpeg,
        status=status,
        progress=progress,
        cancel=cancel,
        console=console,
    )
    return opts.output


def run_pipeline_command(
    opts: RunOptions,
    *,
    status: Optional[StatusCallback] = None,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelEvent] = None,
    console: Optional[Console] = None,
) -> tuple[Path, Optional[Path]]:
    if opts.subtitle_output is None:
        stem = opts.video.stem
        if opts.translate_language:
            stem = f"{stem}.{opts.translate_language}"
        subtitle_output = opts.video.with_name(f"{stem}.{opts.subtitle_format}")
    else:
        subtitle_output = opts.subtitle_output

    video_output: Optional[Path] = None
    if opts.burn_mode != "none":
        if opts.video_output is None:
            video_output = opts.video.with_name(
                f"{opts.video.stem}.v2s{opts.video.suffix or '.mp4'}"
            )
        else:
            video_output = opts.video_output
        if video_output.resolve() == opts.video.resolve():
            raise ValueError(i18n.t("output_must_differ"))

    with _temp_dir(opts.keep_temp) as tmp:
        audio = tmp / "audio.wav"
        segments, detected, duration = _transcribe(
            source=opts.video,
            audio=audio,
            model=opts.model,
            language=opts.language,
            device=opts.device,
            compute_type=opts.compute_type,
            beam_size=opts.beam_size,
            vad_filter=opts.vad_filter,
            word_timestamps=opts.word_timestamps,
            initial_prompt=opts.initial_prompt,
            model_dir=opts.model_dir,
            ffmpeg=opts.ffmpeg,
            status=status,
            progress=progress,
            cancel=cancel,
            console=console,
        )
        segments = _translate(
            segments,
            detected,
            opts.translate_language,
            opts.translation_provider,
            status,
            progress,
            cancel,
        )
        _emit(status, "saving_subtitle")
        save_subtitles(segments, subtitle_output, opts.subtitle_format)
        if video_output is not None:
            _burn(
                opts.video,
                subtitle_output,
                video_output,
                mode=opts.burn_mode,
                language=opts.subtitle_language,
                video_codec=opts.video_codec,
                crf=opts.crf,
                preset=opts.preset,
                ffmpeg=opts.ffmpeg,
                status=status,
                progress=progress,
                cancel=cancel,
                console=console,
            )
    return subtitle_output, video_output
