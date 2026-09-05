from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import commands, i18n, models
from .ffmpeg import CancelError


STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f6f7f9;
    color: #1f2328;
    font-size: 13px;
}
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #d8dce3;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #334155;
}
QLineEdit, QComboBox, QSpinBox {
    padding: 5px 8px;
    border: 1px solid #c7cdd6;
    border-radius: 4px;
    background-color: #ffffff;
    selection-background-color: #bfdbfe;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #2563eb;
}
QPushButton {
    padding: 6px 14px;
    border: 1px solid #c7cdd6;
    border-radius: 4px;
    background-color: #ffffff;
}
QPushButton:hover {
    background-color: #eef2f7;
}
QPushButton:disabled {
    color: #9aa3af;
    background-color: #e9ebef;
}
QPushButton#primary {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    border: none;
}
QPushButton#primary:hover {
    background-color: #1d4ed8;
}
QPushButton#danger {
    color: #b91c1c;
}
QProgressBar {
    border: 1px solid #c7cdd6;
    border-radius: 4px;
    background-color: #e9ebef;
    text-align: center;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 3px;
}
QPlainTextEdit {
    border: 1px solid #c7cdd6;
    border-radius: 4px;
    background-color: #ffffff;
    font-family: Consolas, Menlo, monospace;
    font-size: 12px;
}
QCheckBox {
    spacing: 6px;
}
"""


class TaskThread(QThread):
    progress_changed = Signal(float)
    status_changed = Signal(str)
    log_written = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, options: commands.RunOptions, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.options = options
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        env_backup: dict[str, str] = {}
        try:
            if self.options.translation_provider == "openai":
                for env_name, value in (
                    ("OPENAI_API_KEY", self.options.openai_api_key),
                    ("OPENAI_BASE_URL", self.options.openai_base_url),
                    ("V2S_OPENAI_MODEL", self.options.openai_model),
                ):
                    if value:
                        env_backup[env_name] = os.environ.get(env_name, "")
                        os.environ[env_name] = value
            self._run_task()
        except CancelError:
            self.status_changed.emit(i18n.t("gui.cancelled"))
            self.log_written.emit(i18n.t("gui.cancelled"))
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            for env_name, original in env_backup.items():
                if original:
                    os.environ[env_name] = original
                else:
                    os.environ.pop(env_name, None)

    def _run_task(self) -> None:
        self.status_changed.emit(i18n.t("status_preparing"))
        subtitle_path, video_path = commands.run_pipeline_command(
            self.options,
            status=self._on_status,
            progress=self._on_progress,
            cancel=self._cancel,
        )
        self._on_progress(1.0)
        self.status_changed.emit(i18n.t("status_done"))
        result = str(subtitle_path)
        if video_path is not None:
            result += f"\n{video_path}"
        self.succeeded.emit(result)

    def _on_status(self, message: str) -> None:
        self.status_changed.emit(message)
        self.log_written.emit(message)

    def _on_progress(self, fraction: float) -> None:
        self.progress_changed.emit(max(0.0, min(1.0, fraction)))


class ModelDownloadThread(QThread):
    status_changed = Signal(str)
    log_written = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        model_name: str,
        download_root: Optional[Path],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.model_name = model_name
        self.download_root = download_root

    def run(self) -> None:
        try:
            info = models.get_model_info(self.model_name)
            if info is None:
                raise ValueError(i18n.t("unknown_model", name=self.model_name))
            self.status_changed.emit(
                i18n.t("model_downloading", name=info.name, url=info.repo_url)
            )
            self.log_written.emit(i18n.t("model_repo", url=info.repo_url))
            path = models.download_model(info.name, download_root=self.download_root)
            self.log_written.emit(i18n.t("model_directory", path=path))
            self.succeeded.emit(i18n.t("model_downloaded", name=info.name))
        except Exception as exc:
            self.failed.emit(str(exc))


class V2sWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._thread: Optional[TaskThread] = None
        self._download_thread: Optional[ModelDownloadThread] = None
        self.resize(1020, 860)
        self.setAcceptDrops(True)
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        self.setCentralWidget(scroll)

        root = QVBoxLayout(container)
        root.setContentsMargins(18, 14, 18, 18)
        root.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 700; color: #1e3a8a;")
        self.tagline_label = QLabel()
        self.tagline_label.setStyleSheet("color: #64748b; font-size: 13px;")
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("中文", "zh")
        self.language_combo.setCurrentIndex(
            0 if i18n.current_language() == "en" else 1
        )
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        header.addWidget(self.title_label)
        header.addWidget(self.tagline_label)
        header.addStretch(1)
        self.language_header_label = QLabel()
        header.addWidget(self.language_header_label)
        header.addWidget(self.language_combo)
        root.addLayout(header)

        root.addWidget(self._build_input_group())
        root.addWidget(self._build_whisper_group())
        root.addWidget(self._build_translation_group())
        root.addWidget(self._build_encode_group())
        root.addWidget(self._build_ffmpeg_group())
        root.addWidget(self._build_progress_group())
        self._retranslate()
        self._provider_changed()
        self._mode_changed()

    def _build_input_group(self) -> QGroupBox:
        self.input_group = QGroupBox()
        grid = QGridLayout(self.input_group)
        grid.setVerticalSpacing(8)

        self.video_label = QLabel()
        self.video_line = QLineEdit()
        browse_video = QPushButton()
        browse_video.clicked.connect(self._browse_video)

        self.output_label = QLabel()
        self.output_dir_line = QLineEdit()
        browse_output = QPushButton()
        browse_output.clicked.connect(self._browse_output)

        self.task_label = QLabel()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("", "video")
        self.mode_combo.addItem("", "subs")
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)

        self.sub_mode_label = QLabel()
        self.burn_combo = QComboBox()
        self.burn_combo.addItem("", "hard")
        self.burn_combo.addItem("", "soft")

        self.format_label = QLabel()
        self.subtitle_format_combo = QComboBox()
        for item in ("srt", "vtt", "ass", "json", "txt"):
            self.subtitle_format_combo.addItem(item)

        self.browse_file_button = browse_video
        self.browse_dir_button = browse_output

        grid.addWidget(self.video_label, 0, 0)
        grid.addWidget(self.video_line, 0, 1)
        grid.addWidget(browse_video, 0, 2)
        grid.addWidget(self.output_label, 1, 0)
        grid.addWidget(self.output_dir_line, 1, 1)
        grid.addWidget(browse_output, 1, 2)
        grid.addWidget(self.task_label, 2, 0)
        grid.addWidget(self.mode_combo, 2, 1)
        grid.addWidget(self.sub_mode_label, 3, 0)
        grid.addWidget(self.burn_combo, 3, 1)
        grid.addWidget(self.format_label, 4, 0)
        grid.addWidget(self.subtitle_format_combo, 4, 1)
        return self.input_group

    def _build_whisper_group(self) -> QGroupBox:
        self.whisper_group = QGroupBox()
        form = QFormLayout(self.whisper_group)
        form.setVerticalSpacing(8)

        self.model_label = QLabel()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        for item in ("tiny", "base", "small", "medium", "large-v3", "large-v3-turbo", "distil-large-v3"):
            self.model_combo.addItem(item)
        self.model_combo.setCurrentText("small")

        self.language_label = QLabel()
        self.language_combo_values = QComboBox()
        self.language_combo_values.setEditable(True)
        for item in ("auto", "en", "zh", "ja", "ko", "fr", "de", "es", "ru", "pt", "it"):
            self.language_combo_values.addItem(item)

        self.device_label = QLabel()
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu", "cuda"])
        self.compute_label = QLabel()
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["default", "int8", "float16"])
        self.beam_label = QLabel()
        self.beam_spin = QSpinBox()
        self.beam_spin.setRange(1, 20)
        self.beam_spin.setValue(5)
        self.vad_check = QCheckBox()
        self.vad_check.setChecked(True)
        self.word_check = QCheckBox()
        self.prompt_label = QLabel()
        self.prompt_line = QLineEdit()

        self.model_dir_label = QLabel()
        self.model_dir_line = QLineEdit()
        browse_model_dir = QPushButton()
        browse_model_dir.clicked.connect(self._browse_model_dir)
        model_dir_row = QHBoxLayout()
        model_dir_row.addWidget(self.model_dir_line, 1)
        model_dir_row.addWidget(browse_model_dir)

        self.download_model_button = QPushButton()
        self.download_model_button.clicked.connect(self._download_model)

        form.addRow(self.model_label, self.model_combo)
        form.addRow(self.language_label, self.language_combo_values)
        form.addRow(self.device_label, self.device_combo)
        form.addRow(self.compute_label, self.compute_combo)
        form.addRow(self.beam_label, self.beam_spin)
        form.addRow(self.vad_check)
        form.addRow(self.word_check)
        form.addRow(self.prompt_label, self.prompt_line)
        form.addRow(self.model_dir_label, model_dir_row)
        form.addRow(self.download_model_button)
        return self.whisper_group

    def _build_translation_group(self) -> QGroupBox:
        self.translation_group = QGroupBox()
        grid = QGridLayout(self.translation_group)
        grid.setVerticalSpacing(8)

        self.provider_label = QLabel()
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("", None)
        self.provider_combo.addItem("", "google")
        self.provider_combo.addItem("", "openai")
        self.provider_combo.currentIndexChanged.connect(self._provider_changed)

        self.target_label = QLabel()
        self.target_language_combo = QComboBox()
        self.target_language_combo.setEditable(True)
        for item in ("zh", "en", "ja", "ko", "fr", "de", "es", "ru", "pt", "it"):
            self.target_language_combo.addItem(item)

        self.api_key_label = QLabel()
        self.openai_key_line = QLineEdit()
        self.openai_key_line.setEchoMode(QLineEdit.Password)
        self.base_url_label = QLabel()
        self.openai_base_line = QLineEdit()
        self.openai_model_label = QLabel()
        self.openai_model_line = QLineEdit()

        grid.addWidget(self.provider_label, 0, 0)
        grid.addWidget(self.provider_combo, 0, 1, 1, 2)
        grid.addWidget(self.target_label, 1, 0)
        grid.addWidget(self.target_language_combo, 1, 1, 1, 2)
        grid.addWidget(self.api_key_label, 2, 0)
        grid.addWidget(self.openai_key_line, 2, 1, 1, 2)
        grid.addWidget(self.base_url_label, 3, 0)
        grid.addWidget(self.openai_base_line, 3, 1, 1, 2)
        grid.addWidget(self.openai_model_label, 4, 0)
        grid.addWidget(self.openai_model_line, 4, 1, 1, 2)
        self._openai_widgets = (
            self.openai_key_line,
            self.openai_base_line,
            self.openai_model_line,
        )
        return self.translation_group

    def _build_encode_group(self) -> QGroupBox:
        self.encode_group = QGroupBox()
        form = QFormLayout(self.encode_group)
        form.setVerticalSpacing(8)

        self.codec_label = QLabel()
        self.codec_combo = QComboBox()
        self.codec_combo.setEditable(True)
        for item in ("libx264", "libx265", "libsvtav1"):
            self.codec_combo.addItem(item)
        self.preset_label = QLabel()
        self.preset_combo = QComboBox()
        for item in ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"):
            self.preset_combo.addItem(item)
        self.preset_combo.setCurrentText("medium")
        self.crf_label = QLabel()
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(18)
        self.subtitle_lang_label = QLabel()
        self.subtitle_language_line = QLineEdit("und")

        form.addRow(self.codec_label, self.codec_combo)
        form.addRow(self.preset_label, self.preset_combo)
        form.addRow(self.crf_label, self.crf_spin)
        form.addRow(self.subtitle_lang_label, self.subtitle_language_line)
        return self.encode_group

    def _build_ffmpeg_group(self) -> QGroupBox:
        self.ffmpeg_group = QGroupBox()
        vbox = QVBoxLayout(self.ffmpeg_group)
        row = QHBoxLayout()

        self.ffmpeg_line = QLineEdit()
        browse = QPushButton()
        browse.clicked.connect(self._browse_ffmpeg)
        detect = QPushButton()
        detect.clicked.connect(self._detect_ffmpeg)
        self.ffmpeg_hint = QLabel()
        self.ffmpeg_hint.setStyleSheet("color: #64748b;")
        self.keep_temp_check = QCheckBox()

        row.addWidget(self.ffmpeg_line, 1)
        row.addWidget(browse)
        row.addWidget(detect)
        hint_row = QHBoxLayout()
        hint_row.addWidget(self.ffmpeg_hint, 1)
        hint_row.addWidget(self.keep_temp_check)
        vbox.addLayout(row)
        vbox.addLayout(hint_row)
        self.browse_ffmpeg_button = browse
        self.detect_ffmpeg_button = detect
        return self.ffmpeg_group

    def _build_progress_group(self) -> QGroupBox:
        self.run_group = QGroupBox()
        layout = QVBoxLayout(self.run_group)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-weight: 600; color: #334155;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumBlockCount(1000)
        self.log_edit.setMinimumHeight(120)

        button_row = QHBoxLayout()
        self.start_button = QPushButton()
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self._start)
        self.cancel_button = QPushButton()
        self.cancel_button.setObjectName("danger")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        self.open_button = QPushButton()
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_output)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.cancel_button)
        button_row.addStretch(1)
        button_row.addWidget(self.open_button)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_edit)
        layout.addLayout(button_row)
        return self.run_group

    def _retranslate(self) -> None:
        self.setWindowTitle(i18n.t("gui.title"))
        self.title_label.setText(i18n.t("gui.title"))
        self.tagline_label.setText(i18n.t("gui.tagline"))
        self.language_header_label.setText(i18n.t("language"))
        self.input_group.setTitle(i18n.t("gui.input_output"))
        self.video_label.setText(i18n.t("gui.video"))
        self.video_line.setPlaceholderText(i18n.t("gui.video_placeholder"))
        self.browse_file_button.setText(i18n.t("gui.browse_file"))
        self.output_label.setText(i18n.t("gui.output_dir"))
        self.output_dir_line.setPlaceholderText(i18n.t("gui.output_placeholder"))
        self.browse_dir_button.setText(i18n.t("gui.browse_dir"))
        self.task_label.setText(i18n.t("gui.task_mode"))
        self.mode_combo.setItemText(0, i18n.t("gui.video_mode"))
        self.mode_combo.setItemText(1, i18n.t("gui.subs_only"))
        self.sub_mode_label.setText(i18n.t("gui.subtitle_mode"))
        self.burn_combo.setItemText(0, i18n.t("gui.hard"))
        self.burn_combo.setItemText(1, i18n.t("gui.soft"))
        self.format_label.setText(i18n.t("gui.format"))

        self.whisper_group.setTitle(i18n.t("gui.whisper"))
        self.model_label.setText(i18n.t("gui.model"))
        self.language_label.setText(i18n.t("gui.source_language"))
        self.device_label.setText(i18n.t("gui.device"))
        self.compute_label.setText(i18n.t("gui.compute_type"))
        self.beam_label.setText(i18n.t("gui.beam_size"))
        self.vad_check.setText(i18n.t("gui.vad"))
        self.word_check.setText(i18n.t("gui.word_ts"))
        self.prompt_label.setText(i18n.t("gui.prompt"))
        self.prompt_line.setPlaceholderText(i18n.t("gui.prompt_placeholder"))
        self.model_dir_label.setText(i18n.t("gui.model_dir"))
        self.model_dir_line.setPlaceholderText(i18n.t("gui.model_dir_placeholder"))
        self.download_model_button.setText(i18n.t("gui.download_model"))

        self.translation_group.setTitle(i18n.t("gui.translation"))
        self.provider_label.setText(i18n.t("gui.provider"))
        self.provider_combo.setItemText(0, i18n.t("gui.provider_none"))
        self.provider_combo.setItemText(1, i18n.t("gui.provider_google"))
        self.provider_combo.setItemText(2, i18n.t("gui.provider_openai"))
        self.target_label.setText(i18n.t("gui.target_language"))
        self.api_key_label.setText(i18n.t("gui.api_key"))
        self.openai_key_line.setPlaceholderText(i18n.t("gui.api_key_placeholder"))
        self.base_url_label.setText(i18n.t("gui.base_url"))
        self.openai_base_line.setPlaceholderText(i18n.t("gui.base_url_placeholder"))
        self.openai_model_label.setText(i18n.t("gui.model"))
        self.openai_model_line.setPlaceholderText(i18n.t("gui.model_placeholder"))

        self.encode_group.setTitle(i18n.t("gui.encode"))
        self.codec_label.setText(i18n.t("gui.codec"))
        self.preset_label.setText(i18n.t("gui.preset"))
        self.crf_label.setText(i18n.t("gui.crf"))
        self.subtitle_lang_label.setText(i18n.t("gui.subtitle_language"))

        self.ffmpeg_group.setTitle(i18n.t("gui.ffmpeg"))
        self.ffmpeg_line.setPlaceholderText(i18n.t("gui.ffmpeg_placeholder"))
        self.browse_ffmpeg_button.setText(i18n.t("gui.browse_file"))
        self.detect_ffmpeg_button.setText(i18n.t("gui.detect"))
        self.ffmpeg_hint.setText(i18n.t("gui.ffmpeg_hint"))
        self.keep_temp_check.setText(i18n.t("gui.keep_temp"))

        self.run_group.setTitle(i18n.t("gui.run"))
        self.status_label.setText(i18n.t("gui.status_idle"))
        self.start_button.setText(i18n.t("gui.start"))
        self.cancel_button.setText(i18n.t("gui.cancel"))
        self.open_button.setText(i18n.t("gui.open_output"))

    def _language_changed(self) -> None:
        i18n.set_language(self.language_combo.currentData())
        self._retranslate()

    def _mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        self.burn_combo.setEnabled(mode == "video")
        self.encode_group.setEnabled(mode == "video")

    def _provider_changed(self) -> None:
        enabled = self.provider_combo.currentData() == "openai"
        for widget in self._openai_widgets:
            widget.setEnabled(enabled)

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            i18n.t("gui.choose_video"),
            "",
            i18n.t("gui.video_filter"),
        )
        if path:
            self.video_line.setText(path)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, i18n.t("gui.choose_output"))
        if path:
            self.output_dir_line.setText(path)

    def _browse_model_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, i18n.t("gui.choose_model_dir"))
        if path:
            self.model_dir_line.setText(path)

    def _browse_ffmpeg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            i18n.t("gui.choose_ffmpeg"),
            "",
            i18n.t("gui.ffmpeg_filter"),
        )
        if path:
            self.ffmpeg_line.setText(path)

    def _detect_ffmpeg(self) -> None:
        try:
            from .ffmpeg import resolve_ffmpeg

            path = resolve_ffmpeg(None)
            self.ffmpeg_line.setText(path)
            self.ffmpeg_hint.setText(f"{i18n.t('gui.ffmpeg_hint')}: {path}")
        except Exception as exc:
            self.ffmpeg_hint.setText(f"{i18n.t('gui.ffmpeg_hint')}: {exc}")

    def _start(self) -> None:
        try:
            options = self._collect_options()
        except ValueError as exc:
            QMessageBox.warning(self, i18n.t("gui.param_incomplete"), str(exc))
            return

        self.progress_bar.setValue(0)
        self.log_edit.clear()
        self.status_label.setText(i18n.t("gui.status_preparing"))
        self._thread = TaskThread(options, self)
        self._thread.progress_changed.connect(self._on_progress)
        self._thread.status_changed.connect(self._on_status)
        self._thread.log_written.connect(self._append_log)
        self._thread.succeeded.connect(self._on_succeeded)
        self._thread.failed.connect(self._on_failed)
        self._thread.cancelled.connect(self._on_cancelled)
        self._thread.finished.connect(self._thread.deleteLater)
        self._set_busy(True)
        self._thread.start()

    def _collect_options(self) -> commands.RunOptions:
        video_text = self.video_line.text().strip()
        if not video_text:
            raise ValueError(i18n.t("gui.no_video"))
        video = Path(video_text)
        if not video.is_file():
            raise ValueError(i18n.t("gui.video_not_found", path=video))

        output_text = self.output_dir_line.text().strip()
        output_dir = Path(output_text) if output_text else video.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        task_mode = self.mode_combo.currentData()
        provider = self.provider_combo.currentData()
        source = self.language_combo_values.currentText().strip().lower()
        if source in {"", "auto"}:
            source = None
        target = self.target_language_combo.currentText().strip().lower()
        if not provider:
            target = None

        model_dir_text = self.model_dir_line.text().strip()
        ffmpeg_text = self.ffmpeg_line.text().strip()
        burn_mode = "none" if task_mode == "subs" else self.burn_combo.currentData()
        stem = video.stem
        language_suffix = f".{target}" if target else ""
        subtitle_output = output_dir / f"{stem}{language_suffix}.{self.subtitle_format_combo.currentText()}"
        video_output = None
        if task_mode == "video":
            video_output = output_dir / f"{stem}.v2s{video.suffix or '.mp4'}"
        return commands.RunOptions(
            video=video,
            video_output=video_output,
            subtitle_output=subtitle_output,
            burn_mode=burn_mode,
            subtitle_language=self.subtitle_language_line.text().strip() or "und",
            video_codec=self.codec_combo.currentText().strip() or "libx264",
            crf=self.crf_spin.value(),
            preset=self.preset_combo.currentText(),
            subtitle_format=self.subtitle_format_combo.currentText(),
            model=self.model_combo.currentText().strip() or "small",
            language=source,
            translate_language=target,
            translation_provider=provider,
            device=self.device_combo.currentText(),
            compute_type=self.compute_combo.currentText(),
            beam_size=self.beam_spin.value(),
            vad_filter=self.vad_check.isChecked(),
            word_timestamps=self.word_check.isChecked(),
            initial_prompt=self.prompt_line.text().strip() or None,
            model_dir=Path(model_dir_text) if model_dir_text else None,
            openai_api_key=self.openai_key_line.text().strip(),
            openai_base_url=self.openai_base_line.text().strip(),
            openai_model=self.openai_model_line.text().strip(),
            ffmpeg=Path(ffmpeg_text) if ffmpeg_text else None,
            keep_temp=self.keep_temp_check.isChecked(),
        )

    def _set_busy(self, busy: bool) -> None:
        self.start_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.open_button.setEnabled(not busy)

    def _cancel(self) -> None:
        if self._thread is not None:
            self.cancel_button.setEnabled(False)
            self.status_label.setText(i18n.t("gui.cancelling"))
            self._thread.cancel()

    def _download_model(self) -> None:
        if self._download_thread is not None and self._download_thread.isRunning():
            return
        name = self.model_combo.currentText().strip()
        info = models.get_model_info(name)
        if info is None:
            QMessageBox.warning(
                self,
                i18n.t("gui.param_incomplete"),
                i18n.t(
                    "gui.unknown_model",
                    name=name,
                    models=", ".join(models.MODELS),
                ),
            )
            return
        model_dir_text = self.model_dir_line.text().strip()
        model_dir = Path(model_dir_text) if model_dir_text else None
        self._download_thread = ModelDownloadThread(info.name, model_dir, self)
        self._download_thread.status_changed.connect(self._on_status)
        self._download_thread.log_written.connect(self._append_log)
        self._download_thread.succeeded.connect(self._on_model_downloaded)
        self._download_thread.failed.connect(self._on_model_download_failed)
        self._download_thread.finished.connect(self._download_thread.deleteLater)
        self.download_model_button.setEnabled(False)
        self._download_thread.start()

    def _on_model_downloaded(self, text: str) -> None:
        self.download_model_button.setEnabled(True)
        self._append_log(text)
        QMessageBox.information(self, i18n.t("gui.download_done"), text)

    def _on_model_download_failed(self, message: str) -> None:
        self.download_model_button.setEnabled(True)
        self._append_log(f"{i18n.t('error_prefix')}: {message}")
        QMessageBox.critical(self, i18n.t("gui.download_failed"), message)

    def _on_progress(self, ratio: float) -> None:
        self.progress_bar.setValue(round(ratio * 100))

    def _on_status(self, text: str) -> None:
        self.status_label.setText(text)
        self._append_log(text)

    def _append_log(self, text: str) -> None:
        self.log_edit.appendPlainText(text)

    def _on_succeeded(self, text: str) -> None:
        self._set_busy(False)
        self.status_label.setText(i18n.t("gui.status_done"))
        QMessageBox.information(
            self,
            i18n.t("gui.task_done"),
            i18n.t("gui.output_files", files=text),
        )

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        self.status_label.setText(i18n.t("gui.status_failed"))
        self._append_log(f"{i18n.t('error_prefix')}: {message}")
        QMessageBox.critical(self, i18n.t("gui.task_failed"), message)

    def _on_cancelled(self) -> None:
        self._set_busy(False)

    def _open_output(self) -> None:
        path = self.output_dir_line.text().strip()
        if not path:
            video = Path(self.video_line.text().strip())
            path = str(video.parent) if video.is_file() else ""
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if path.is_file():
            self.video_line.setText(str(path))
            event.acceptProposedAction()

    def closeEvent(self, event) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.cancel()
            if not self._thread.wait(10000):
                event.ignore()
                return
        if self._download_thread is not None and self._download_thread.isRunning():
            if not self._download_thread.wait(10000):
                event.ignore()
                return
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("v2s")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    window = V2sWindow()
    window.show()
    sys.exit(app.exec())
