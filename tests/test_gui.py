import os
import sys

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from v2s import i18n
from v2s.gui import V2sWindow
from v2s.gui_app import ensure_standard_streams


def test_windowed_stdio_guard_replaces_missing_streams():
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = None
    sys.stderr = None
    try:
        ensure_standard_streams()
        assert sys.stdout is not None
        assert sys.stderr is not None
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def test_gui_window_constructs():
    i18n.set_language("en")
    app = QApplication.instance() or QApplication([])
    window = V2sWindow()
    assert window.windowTitle() == i18n.t("gui.title")
    assert window.video_label.text() == i18n.t("gui.video")
    assert window.start_button.text() == i18n.t("gui.start")
    assert window.download_model_button.text() == i18n.t("gui.download_model")
    assert window.mode_combo.itemText(0) == i18n.t("gui.video_mode")
    assert window.language_combo.currentData() == "en"
    window.close()
    app.processEvents()


def test_gui_language_switch_retranslates():
    i18n.set_language("zh")
    app = QApplication.instance() or QApplication([])
    window = V2sWindow()
    assert window.video_label.text() == i18n.t("gui.video")
    assert window.start_button.text() == i18n.t("gui.start")
    window.language_combo.setCurrentIndex(0)
    assert i18n.current_language() == "en"
    assert window.video_label.text() == i18n.t("gui.video")
    assert window.start_button.text() == i18n.t("gui.start")
    window.close()
    app.processEvents()
