from v2s import i18n


def test_english_default():
    i18n.set_language("en")
    assert i18n.t("gui.start") == "Start"
    assert i18n.t("model_name") == "Name"


def test_chinese_translations():
    i18n.set_language("zh")
    assert i18n.t("gui.start") == "开始"
    assert i18n.t("saved_subtitles", path="a.srt") == "字幕已保存: a.srt"


def test_formatted_message():
    i18n.set_language("en")
    text = i18n.t("summary", language="en", duration=1.5, count=2)
    assert "Duration: 1.5s" in text
    assert "Segments: 2" in text


def test_unknown_key_uses_key():
    i18n.set_language("en")
    assert i18n.t("does.not.exist") == "does.not.exist"

