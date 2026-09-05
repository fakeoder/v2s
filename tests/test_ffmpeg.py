from v2s.ffmpeg import filter_escape


def test_filter_escape_windows_path():
    escaped = filter_escape(r"C:\Users\name\Temp\subs.ass")
    assert "\\:" in escaped
    assert "\\\\" in escaped


def test_filter_escape_simple_path():
    escaped = filter_escape("/tmp/subs.ass")
    assert escaped == "/tmp/subs.ass"

