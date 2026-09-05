from __future__ import annotations

import os
import re
import threading
from typing import Callable, Optional, Sequence

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .ffmpeg import CancelError
from .transcribe import Segment


class TranslationError(RuntimeError):
    pass


_MARKED_LINE_RE = re.compile(r"^\s*(\d+)\s*[|:]\s*(.*)$")


def parse_marked_lines(content: str) -> dict[int, str]:
    parsed: dict[int, str] = {}
    for line in content.splitlines():
        match = _MARKED_LINE_RE.match(line)
        if match:
            parsed[int(match.group(1))] = match.group(2).strip()
    return parsed


def translate_segments(
    segments: Sequence[Segment],
    target_language: str,
    *,
    source_language: Optional[str] = None,
    provider: str = "google",
    console: Optional[Console] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> list[Segment]:
    if provider == "google":
        return _translate_google(
            segments,
            target_language,
            source_language,
            console,
            progress_callback,
            cancel_event,
        )
    if provider == "openai":
        return _translate_openai(
            segments,
            target_language,
            source_language,
            console,
            progress_callback,
            cancel_event,
        )
    raise TranslationError(f"unknown translation provider: {provider}")


def _translate_google(
    segments: Sequence[Segment],
    target_language: str,
    source_language: Optional[str],
    console: Optional[Console],
    progress_callback: Optional[Callable[[int, int], None]],
    cancel_event: Optional[threading.Event],
) -> list[Segment]:
    try:
        from deep_translator import GoogleTranslator
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise TranslationError(
            "deep-translator is not installed; use --translation-provider openai "
            "or install v2s with translation support."
        ) from exc

    translator = GoogleTranslator(source=source_language or "auto", target=target_language)
    translated: list[Segment] = []
    if progress_callback is not None:
        for index, segment in enumerate(segments):
            if cancel_event is not None and cancel_event.is_set():
                raise CancelError("translation cancelled")
            text = " ".join(segment.text.splitlines()).strip()
            try:
                output = translator.translate(text) if text else ""
            except Exception as exc:
                raise TranslationError(
                    f"Google translation failed on segment at {segment.start:.2f}s: {exc}"
                ) from exc
            translated.append(
                Segment(segment.start, segment.end, (output or text).strip())
            )
            progress_callback(index + 1, len(segments))
        return translated

    columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ]
    with Progress(*columns, console=console) as progress:
        task = progress.add_task("Translating (Google)", total=len(segments))
        for index, segment in enumerate(segments):
            if cancel_event is not None and cancel_event.is_set():
                raise CancelError("translation cancelled")
            text = " ".join(segment.text.splitlines()).strip()
            try:
                output = translator.translate(text) if text else ""
            except Exception as exc:
                raise TranslationError(
                    f"Google translation failed on segment at {segment.start:.2f}s: {exc}"
                ) from exc
            translated.append(
                Segment(segment.start, segment.end, (output or text).strip())
            )
            progress.update(task, completed=index + 1)
    return translated


def _translate_openai(
    segments: Sequence[Segment],
    target_language: str,
    source_language: Optional[str],
    console: Optional[Console],
    progress_callback: Optional[Callable[[int, int], None]],
    cancel_event: Optional[threading.Event],
) -> list[Segment]:
    import requests

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("V2S_OPENAI_API_KEY")
    if not api_key:
        raise TranslationError(
            "OPENAI_API_KEY is not set; required for --translation-provider openai"
        )

    base_url = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("V2S_OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).rstrip("/")
    model = os.environ.get("V2S_OPENAI_MODEL", "gpt-4o-mini")
    batch_size = 20

    translated: list[Segment] = []

    def translate_batch(start: int) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise CancelError("translation cancelled")
        batch = segments[start : start + batch_size]
        numbered = "\n".join(
            f"{index + 1}|{' '.join(segment.text.splitlines())}"
            for index, segment in enumerate(batch)
        )
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a subtitle translator. Translate the numbered subtitle "
                    f"lines from {source_language or 'the detected source language'} "
                    f"into {target_language}. Respond only with the translated lines, "
                    "one per line, preserving the N| prefix. Do not add explanations."
                ),
            },
            {"role": "user", "content": numbered},
        ]
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0,
                },
                timeout=120,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            raise TranslationError(f"OpenAI translation failed: {exc}") from exc

        parsed = parse_marked_lines(content)
        for index, segment in enumerate(batch):
            text = parsed.get(index + 1) or segment.text
            translated.append(Segment(segment.start, segment.end, text))

    if progress_callback is not None:
        for start in range(0, len(segments), batch_size):
            translate_batch(start)
            progress_callback(min(start + batch_size, len(segments)), len(segments))
        return translated

    columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ]
    with Progress(*columns, console=console) as progress:
        task = progress.add_task("Translating (OpenAI)", total=len(segments))
        for start in range(0, len(segments), batch_size):
            translate_batch(start)
            progress.update(
                task,
                completed=start + min(batch_size, len(segments) - start),
            )
    return translated
