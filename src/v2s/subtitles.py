from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Sequence

from .transcribe import Segment


def _format_timestamp(seconds: float, *, separator: str) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    if separator == ",":
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def save_subtitles(
    segments: Sequence[Segment],
    output: str | Path,
    output_format: Optional[str] = None,
) -> None:
    output = Path(output)
    fmt = (output_format or output.suffix.lstrip(".")).lower()

    if fmt == "json":
        payload = {
            "segments": [
                {"start": segment.start, "end": segment.end, "text": segment.text}
                for segment in segments
            ]
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if fmt == "txt":
        output.write_text("\n\n".join(segment.text for segment in segments), encoding="utf-8")
        return

    if fmt == "srt":
        lines: list[str] = []
        for index, segment in enumerate(segments, start=1):
            lines.extend(
                [
                    str(index),
                    f"{_format_timestamp(segment.start, separator=',')} --> "
                    f"{_format_timestamp(segment.end, separator=',')}",
                    segment.text,
                    "",
                ]
            )
        output.write_text("\n".join(lines), encoding="utf-8")
        return

    if fmt == "vtt":
        lines = ["WEBVTT", ""]
        for index, segment in enumerate(segments, start=1):
            lines.extend(
                [
                    f"{_format_timestamp(segment.start, separator='.')} --> "
                    f"{_format_timestamp(segment.end, separator='.')}",
                    segment.text,
                    "",
                ]
            )
        output.write_text("\n".join(lines), encoding="utf-8")
        return

    if fmt in ("ass", "ssa"):
        from pysubs2 import SSAEvent, SSAFile

        subs = SSAFile()
        for segment in segments:
            subs.events.append(
                SSAEvent(
                    start=int(round(segment.start * 1000)),
                    end=int(round(segment.end * 1000)),
                    text=segment.text,
                )
            )
        subs.save(str(output))
        return

    raise ValueError(f"unsupported subtitle format: {fmt}")


def to_ass(subtitle_path: str | Path, ass_path: str | Path) -> None:
    import pysubs2

    subs = pysubs2.load(str(subtitle_path))
    style = subs.styles.get("Default")
    if style is None:
        style = pysubs2.SSAStyle()
        subs.styles["Default"] = style
    style.fontname = "Arial"
    style.fontsize = 20
    style.outline = 2
    style.shadow = 1
    style.marginv = 30
    subs.save(str(ass_path))
