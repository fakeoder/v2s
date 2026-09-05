from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__, commands, i18n, models
from .burn import BurnError
from .ffmpeg import FFmpegError
from .transcribe import TranscriptionError
from .translate import TranslationError

console = Console(highlight=False)


def _transcribe_options(func):
    func = click.option(
        "--format",
        "-f",
        "output_format",
        type=click.Choice(["srt", "vtt", "ass", "json", "txt"]),
        default="srt",
        show_default=True,
        help="Subtitle output format.",
    )(func)
    func = click.option(
        "-m",
        "--model",
        default="small",
        show_default=True,
        help="Whisper model: tiny/base/small/medium/large-v3/distil-large-v3 or a local path.",
    )(func)
    func = click.option(
        "-l",
        "--language",
        default="auto",
        show_default=True,
        help="Source language code (en, zh, ja, ...); auto detects.",
    )(func)
    func = click.option(
        "-t",
        "--translate",
        "translate_language",
        default=None,
        help="Translate subtitles to this language code.",
    )(func)
    func = click.option(
        "--translation-provider",
        type=click.Choice(["google", "openai"]),
        default="google",
        show_default=True,
        help="Translation backend.",
    )(func)
    func = click.option(
        "--device",
        type=click.Choice(["auto", "cpu", "cuda"]),
        default="auto",
        show_default=True,
        help="Device used by faster-whisper.",
    )(func)
    func = click.option(
        "--compute-type",
        default="default",
        show_default=True,
        help="Whisper compute type: default/int8/float16.",
    )(func)
    func = click.option("--beam-size", default=5, show_default=True)(func)
    func = click.option(
        "--vad-filter/--no-vad-filter",
        default=True,
        show_default=True,
        help="Filter non-speech segments before transcription.",
    )(func)
    func = click.option(
        "--word-timestamps/--no-word-timestamps",
        default=False,
        show_default=True,
        help="Enable word-level timestamps.",
    )(func)
    func = click.option("--initial-prompt", default=None, help="Guiding prompt for Whisper.")(func)
    func = click.option(
        "--model-dir",
        default=None,
        type=click.Path(file_okay=False, path_type=Path),
        help="Directory used to cache/download Whisper models.",
    )(func)
    func = click.option(
        "--ffmpeg",
        "ffmpeg_path",
        default=None,
        type=click.Path(exists=True, path_type=Path),
        help="Path to an ffmpeg executable.",
    )(func)
    func = click.option("--keep-temp", is_flag=True, help="Keep temporary extracted audio.")(func)
    return func


def _status(message: str) -> None:
    console.print(message)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--lang",
    "language",
    type=click.Choice(["en", "zh"]),
    default=None,
    help="UI language: en or zh (default from V2S_LANG or system locale).",
)
@click.version_option(__version__, prog_name="v2s")
def cli(language):
    """v2s: video to subtitles, translation, and subtitle burn-in."""
    i18n.set_language(language)


@cli.command("transcribe")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output", required=False, type=click.Path(path_type=Path))
@_transcribe_options
def transcribe_cmd(
    input,
    output,
    output_format,
    model,
    language,
    translate_language,
    translation_provider,
    device,
    compute_type,
    beam_size,
    vad_filter,
    word_timestamps,
    initial_prompt,
    model_dir,
    ffmpeg_path,
    keep_temp,
):
    """Transcribe a video and write subtitles."""
    if output is None:
        output = input.with_suffix("." + output_format)
    source_language = None if language.lower() in {"", "auto"} else language.lower()
    opts = commands.TranscribeOptions(
        input=input,
        output=output,
        output_format=output_format,
        model=model,
        language=source_language,
        translate_language=translate_language,
        translation_provider=translation_provider,
        device=device,
        compute_type=compute_type,
        beam_size=beam_size,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps,
        initial_prompt=initial_prompt,
        model_dir=model_dir,
        ffmpeg=ffmpeg_path,
        keep_temp=keep_temp,
    )
    result = commands.transcribe_command(opts, status=_status, console=console)
    console.print(i18n.t("saved_subtitles", path=result))


@cli.command("burn")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-s",
    "--subtitle",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Subtitle file to embed.",
)
@click.option("-o", "--output", default=None, type=click.Path(path_type=Path), help="Output video.")
@click.option(
    "--mode",
    type=click.Choice(["hard", "soft"]),
    default="hard",
    show_default=True,
    help="hard burns text into frames; soft muxes a subtitle track.",
)
@click.option("--language", default="und", show_default=True, help="Language tag for soft subtitles.")
@click.option("--video-codec", default="libx264", show_default=True, help="Encoder for hard burn mode.")
@click.option("--crf", default=18, show_default=True, help="Video quality for hard burn mode.")
@click.option("--preset", default="medium", show_default=True, help="x264 preset for hard burn mode.")
@click.option("--ffmpeg", "ffmpeg_path", default=None, type=click.Path(exists=True, path_type=Path))
def burn_cmd(input, subtitle, output, mode, language, video_codec, crf, preset, ffmpeg_path):
    """Embed an existing subtitle into a video."""
    if output is None:
        output = input.with_name(f"{input.stem}.v2s{input.suffix or '.mp4'}")
    opts = commands.BurnOptions(
        video=input,
        subtitle=subtitle,
        output=output,
        mode=mode,
        language=language,
        video_codec=video_codec,
        crf=crf,
        preset=preset,
        ffmpeg=ffmpeg_path,
    )
    result = commands.burn_command(opts, status=_status, console=console)
    console.print(i18n.t("saved_video", path=result))


@cli.command("run")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--video-output",
    default=None,
    type=click.Path(path_type=Path),
    help="Output video; only used when --burn-mode is not none.",
)
@click.option(
    "-s",
    "--subtitle-output",
    default=None,
    type=click.Path(path_type=Path),
    help="Subtitle file path.",
)
@click.option(
    "--burn-mode",
    type=click.Choice(["hard", "soft", "none"]),
    default="hard",
    show_default=True,
    help="hard burns text, soft muxes a subtitle track, none writes subtitles only.",
)
@click.option(
    "--subtitle-language",
    default="und",
    show_default=True,
    help="Language tag for soft subtitle streams.",
)
@click.option("--video-codec", default="libx264", show_default=True)
@click.option("--crf", default=18, show_default=True)
@click.option("--preset", default="medium", show_default=True)
@_transcribe_options
def run_cmd(
    input,
    video_output,
    subtitle_output,
    burn_mode,
    subtitle_language,
    video_codec,
    crf,
    preset,
    output_format,
    model,
    language,
    translate_language,
    translation_provider,
    device,
    compute_type,
    beam_size,
    vad_filter,
    word_timestamps,
    initial_prompt,
    model_dir,
    ffmpeg_path,
    keep_temp,
):
    """Transcribe, optionally translate, then embed subtitles in one pass."""
    source_language = None if language.lower() in {"", "auto"} else language.lower()
    opts = commands.RunOptions(
        video=input,
        video_output=video_output,
        subtitle_output=subtitle_output,
        burn_mode=burn_mode,
        subtitle_language=subtitle_language,
        video_codec=video_codec,
        crf=crf,
        preset=preset,
        subtitle_format=output_format,
        model=model,
        language=source_language,
        translate_language=translate_language,
        translation_provider=translation_provider,
        device=device,
        compute_type=compute_type,
        beam_size=beam_size,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps,
        initial_prompt=initial_prompt,
        model_dir=model_dir,
        ffmpeg=ffmpeg_path,
        keep_temp=keep_temp,
    )
    subtitle_path, video_path = commands.run_pipeline_command(
        opts,
        status=_status,
        console=console,
    )
    console.print(i18n.t("saved_subtitles", path=subtitle_path))
    if video_path is not None:
        console.print(i18n.t("saved_video", path=video_path))


@cli.group("model")
def model_cmd():
    """Manage downloadable Whisper models."""


@model_cmd.command("list")
def model_list_cmd():
    """List available models and their default download URLs."""
    table = Table(title=i18n.t("model_list_title"))
    table.add_column(i18n.t("model_name"), no_wrap=True)
    table.add_column(i18n.t("model_size"))
    table.add_column(i18n.t("model_url"))
    table.add_column(i18n.t("model_note"))
    for info in models.MODELS.values():
        table.add_row(info.name, info.size_hint, info.repo_url, info.note)
    console.print(table)
    console.print(i18n.t("mirror_hint"))


@model_cmd.command("download")
@click.argument("name")
@click.option(
    "--dir",
    "model_dir",
    default=None,
    type=click.Path(file_okay=False, path_type=Path),
    help="Model cache directory; matches --model-dir.",
)
def model_download_cmd(name, model_dir):
    """Download a model by name into the default cache or --dir."""
    info = models.get_model_info(name)
    if info is None:
        raise click.ClickException(i18n.t("unknown_model", name=name))
    console.print(
        i18n.t("model_downloading", name=info.name, url=info.repo_url)
    )
    try:
        path = models.download_model(info.name, download_root=model_dir)
    except Exception as exc:
        raise click.ClickException(f"Download failed: {exc}") from exc
    console.print(i18n.t("model_downloaded", name=info.name))
    console.print(i18n.t("model_directory", path=path))
    console.print(i18n.t("model_repo", url=info.repo_url))


@cli.command("gui")
def gui_cmd():
    """Open the desktop GUI."""
    try:
        from v2s.gui import main as gui_main
    except ImportError as exc:
        raise click.ClickException(
            "GUI dependencies are not installed. Run: pip install 'v2s[gui]'"
        ) from exc
    gui_main()


def main() -> None:
    try:
        cli(prog_name="v2s")
    except (BurnError, FFmpegError, TranscriptionError, TranslationError, ValueError) as exc:
        console.print(f"[bold red]{i18n.t('error_prefix')}:[/] {exc}")
        raise SystemExit(1) from exc
    except click.ClickException:
        raise
