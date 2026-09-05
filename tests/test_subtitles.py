import json

import pysubs2

from v2s.subtitles import save_subtitles
from v2s.transcribe import Segment


def test_write_srt(tmp_path):
    segments = [Segment(0.0, 1.5, "Hello"), Segment(1.5, 3.0, "World")]
    output = tmp_path / "demo.srt"

    save_subtitles(segments, output)

    text = output.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,500" in text
    assert "Hello" in text

    subs = pysubs2.load(str(output))
    assert len(subs.events) == 2
    assert subs.events[1].text == "World"


def test_write_vtt_and_txt(tmp_path):
    segments = [Segment(0.0, 1.0, "One")]
    vtt = tmp_path / "demo.vtt"
    txt = tmp_path / "demo.txt"

    save_subtitles(segments, vtt)
    save_subtitles(segments, txt, "txt")

    assert "WEBVTT" in vtt.read_text(encoding="utf-8")
    assert txt.read_text(encoding="utf-8") == "One"


def test_write_json(tmp_path):
    segments = [Segment(0.0, 1.0, "One")]
    output = tmp_path / "demo.json"

    save_subtitles(segments, output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["segments"][0]["text"] == "One"

