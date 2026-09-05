from __future__ import annotations

import os
from typing import Optional


DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "zh")


MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "app.title": "v2s - Video to Subtitles & Burn",
        "app.tagline": "Transcribe, translate, and burn subtitles into video.",
        "extracting_audio": "Extracting audio with ffmpeg...",
        "transcribing": "Transcribing with Whisper...",
        "summary": "Source: {language} | Duration: {duration:.1f}s | Segments: {count}",
        "translating_to": "Translating into {language}...",
        "translation_skipped": "Output language matches source; skipping translation.",
        "burning": "Burning subtitles into video...",
        "muxing": "Muxing subtitle track...",
        "saving_subtitle": "Saving subtitles...",
        "saved_subtitles": "Saved subtitles: {path}",
        "saved_video": "Saved video: {path}",
        "unknown_model": "Unknown model '{name}'. Run 'v2s model list' to see available models.",
        "model_list_title": "Available faster-whisper models",
        "model_name": "Name",
        "model_size": "Approx. size",
        "model_url": "Default download URL",
        "model_note": "Note",
        "model_downloading": "Downloading model {name} from {url}...",
        "model_downloaded": "Model downloaded: {name}",
        "model_directory": "Model directory: {path}",
        "model_repo": "Repo URL: {url}",
        "mirror_hint": "For users in China: set HF_ENDPOINT=https://hf-mirror.com before downloading.",
        "model_dir_default": "Default Hugging Face cache",
        "output_must_differ": "Output path must differ from the input video.",
        "error_prefix": "Error",
        "language": "Language",
        "gui.language_en": "English",
        "gui.language_zh": "中文",
        "gui.title": "v2s - Video to Subtitles & Burn",
        "gui.tagline": "Transcribe, translate, and burn subtitles into video.",
        "gui.input_output": "Input & Output",
        "gui.video": "Video",
        "gui.video_placeholder": "Select or drop a video file",
        "gui.output_dir": "Output directory",
        "gui.output_placeholder": "Empty uses the video directory",
        "gui.task_mode": "Task",
        "gui.video_mode": "Subtitles + video",
        "gui.subs_only": "Subtitles only",
        "gui.subtitle_mode": "Embed mode",
        "gui.hard": "Hard subtitles (burn)",
        "gui.soft": "Soft subtitles (track)",
        "gui.format": "Subtitle format",
        "gui.browse_file": "Browse file",
        "gui.browse_dir": "Browse dir",
        "gui.whisper": "Whisper",
        "gui.model": "Model",
        "gui.source_language": "Source language",
        "gui.device": "Device",
        "gui.compute_type": "Compute type",
        "gui.beam_size": "Beam size",
        "gui.vad": "Use VAD to filter non-speech",
        "gui.word_ts": "Word-level timestamps",
        "gui.prompt": "Initial prompt",
        "gui.prompt_placeholder": "Optional context, e.g. topic",
        "gui.model_dir": "Model directory",
        "gui.model_dir_placeholder": "Empty uses default cache",
        "gui.download_model": "Download selected model",
        "gui.translation": "Translation",
        "gui.provider": "Provider",
        "gui.provider_none": "None",
        "gui.provider_google": "Google Translate",
        "gui.provider_openai": "OpenAI compatible API",
        "gui.target_language": "Target language",
        "gui.api_key": "API key",
        "gui.api_key_placeholder": "sk-... or compatible service key",
        "gui.base_url": "Base URL",
        "gui.base_url_placeholder": "https://api.openai.com/v1",
        "gui.model_placeholder": "gpt-4o-mini",
        "gui.encode": "Video encoding",
        "gui.codec": "Video codec",
        "gui.preset": "Preset",
        "gui.crf": "CRF",
        "gui.subtitle_language": "Subtitle track language",
        "gui.ffmpeg": "ffmpeg",
        "gui.ffmpeg_placeholder": "Empty auto-detects ffmpeg",
        "gui.detect": "Detect",
        "gui.ffmpeg_hint": "Auto: PATH first, then bundled imageio-ffmpeg",
        "gui.ffmpeg_found": "Detected ffmpeg: {path}",
        "gui.ffmpeg_not_found": "ffmpeg not found: {error}",
        "gui.keep_temp": "Keep temporary audio",
        "gui.run": "Run",
        "gui.status_idle": "Waiting for task",
        "gui.status_preparing": "Preparing...",
        "gui.start": "Start",
        "gui.cancel": "Cancel",
        "gui.open_output": "Open output dir",
        "gui.cancelling": "Cancelling...",
        "gui.status_done": "Done",
        "gui.status_failed": "Failed",
        "gui.cancelled": "Cancelled",
        "gui.choose_video": "Choose video",
        "gui.video_filter": "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts);;All files (*)",
        "gui.choose_output": "Choose output directory",
        "gui.choose_model_dir": "Choose model directory",
        "gui.choose_ffmpeg": "Choose ffmpeg",
        "gui.ffmpeg_filter": "ffmpeg (*.exe);;All files (*)",
        "gui.param_incomplete": "Incomplete settings",
        "gui.no_video": "Choose a video file first.",
        "gui.video_not_found": "Video file does not exist: {path}",
        "gui.unknown_model": "Unknown model: {name}\nAvailable: {models}",
        "gui.download_done": "Download finished",
        "gui.download_failed": "Download failed",
        "gui.task_done": "Done",
        "gui.task_failed": "Task failed",
        "gui.output_files": "Output files:\n{files}",
    },
    "zh": {
        "app.title": "v2s - 视频转字幕与压制",
        "app.tagline": "转写、翻译并把字幕压制进视频。",
        "extracting_audio": "正在用 ffmpeg 提取音频...",
        "transcribing": "正在使用 Whisper 转写...",
        "summary": "源语言: {language} | 时长: {duration:.1f}s | 片段: {count}",
        "translating_to": "正在翻译为 {language}...",
        "translation_skipped": "目标语言与源语言相同，跳过翻译。",
        "burning": "正在把字幕烧录进视频...",
        "muxing": "正在封装字幕轨...",
        "saving_subtitle": "正在保存字幕...",
        "saved_subtitles": "字幕已保存: {path}",
        "saved_video": "视频已保存: {path}",
        "unknown_model": "未知模型 '{name}'。运行 'v2s model list' 查看可用模型。",
        "model_list_title": "可用的 faster-whisper 模型",
        "model_name": "名称",
        "model_size": "约大小",
        "model_url": "默认下载地址",
        "model_note": "备注",
        "model_downloading": "正在从 {url} 下载模型 {name}...",
        "model_downloaded": "模型已下载: {name}",
        "model_directory": "模型目录: {path}",
        "model_repo": "仓库地址: {url}",
        "mirror_hint": "国内用户可先设置 HF_ENDPOINT=https://hf-mirror.com 再下载。",
        "model_dir_default": "默认 Hugging Face 缓存",
        "output_must_differ": "输出路径不能与输入视频相同。",
        "error_prefix": "错误",
        "language": "语言",
        "gui.language_en": "English",
        "gui.language_zh": "中文",
        "gui.title": "v2s - 视频转字幕与压制",
        "gui.tagline": "转写、翻译并把字幕压制进视频。",
        "gui.input_output": "输入与输出",
        "gui.video": "视频",
        "gui.video_placeholder": "选择或拖入视频文件",
        "gui.output_dir": "输出目录",
        "gui.output_placeholder": "留空则输出到视频所在目录",
        "gui.task_mode": "任务模式",
        "gui.video_mode": "字幕 + 视频",
        "gui.subs_only": "仅字幕",
        "gui.subtitle_mode": "字幕方式",
        "gui.hard": "硬字幕（烧录）",
        "gui.soft": "软字幕（字幕轨）",
        "gui.format": "字幕格式",
        "gui.browse_file": "浏览文件",
        "gui.browse_dir": "选择目录",
        "gui.whisper": "Whisper 转写",
        "gui.model": "模型",
        "gui.source_language": "源语言",
        "gui.device": "设备",
        "gui.compute_type": "计算类型",
        "gui.beam_size": "Beam size",
        "gui.vad": "启用 VAD 过滤非语音",
        "gui.word_ts": "词级时间戳",
        "gui.prompt": "初始提示",
        "gui.prompt_placeholder": "可选上下文提示",
        "gui.model_dir": "模型目录",
        "gui.model_dir_placeholder": "留空使用默认缓存",
        "gui.download_model": "下载所选模型",
        "gui.translation": "翻译",
        "gui.provider": "翻译通道",
        "gui.provider_none": "不翻译",
        "gui.provider_google": "Google 翻译",
        "gui.provider_openai": "OpenAI 兼容 API",
        "gui.target_language": "目标语言",
        "gui.api_key": "API Key",
        "gui.api_key_placeholder": "sk-... 或兼容服务 Key",
        "gui.base_url": "Base URL",
        "gui.base_url_placeholder": "https://api.openai.com/v1",
        "gui.model_placeholder": "gpt-4o-mini",
        "gui.encode": "视频压制",
        "gui.codec": "视频编码器",
        "gui.preset": "预设",
        "gui.crf": "CRF",
        "gui.subtitle_language": "字幕轨语言",
        "gui.ffmpeg": "ffmpeg",
        "gui.ffmpeg_placeholder": "留空自动检测 ffmpeg",
        "gui.detect": "检测",
        "gui.ffmpeg_hint": "自动：优先 PATH，其次内置 imageio-ffmpeg",
        "gui.ffmpeg_found": "检测到 ffmpeg: {path}",
        "gui.ffmpeg_not_found": "未找到 ffmpeg: {error}",
        "gui.keep_temp": "保留临时音频",
        "gui.run": "运行",
        "gui.status_idle": "等待任务",
        "gui.status_preparing": "正在准备...",
        "gui.start": "开始",
        "gui.cancel": "取消",
        "gui.open_output": "打开输出目录",
        "gui.cancelling": "正在取消...",
        "gui.status_done": "完成",
        "gui.status_failed": "失败",
        "gui.cancelled": "已取消",
        "gui.choose_video": "选择视频",
        "gui.video_filter": "视频文件 (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts);;所有文件 (*)",
        "gui.choose_output": "选择输出目录",
        "gui.choose_model_dir": "选择模型目录",
        "gui.choose_ffmpeg": "选择 ffmpeg",
        "gui.ffmpeg_filter": "ffmpeg (*.exe);;所有文件 (*)",
        "gui.param_incomplete": "参数不完整",
        "gui.no_video": "请先选择视频文件。",
        "gui.video_not_found": "视频文件不存在：{path}",
        "gui.unknown_model": "未知模型：{name}\n可用模型：{models}",
        "gui.download_done": "下载完成",
        "gui.download_failed": "下载失败",
        "gui.task_done": "完成",
        "gui.task_failed": "任务失败",
        "gui.output_files": "输出文件：\n{files}",
    },
}


_current_language: Optional[str] = None


def detect_language() -> str:
    override = os.environ.get("V2S_LANG", "").strip().lower()
    if override in SUPPORTED_LANGUAGES:
        return override
    locale_name = os.environ.get("LANG") or os.environ.get("LC_ALL") or ""
    if locale_name.lower().startswith("zh"):
        return "zh"
    return DEFAULT_LANGUAGE


def set_language(language: Optional[str] = None) -> str:
    global _current_language
    if language in SUPPORTED_LANGUAGES:
        _current_language = language
    else:
        _current_language = detect_language()
    return _current_language


def current_language() -> str:
    if _current_language is None:
        set_language(None)
    assert _current_language is not None
    return _current_language


def t(key: str, **kwargs) -> str:
    language = current_language()
    text = MESSAGES.get(language, MESSAGES[DEFAULT_LANGUAGE]).get(key)
    if text is None:
        text = MESSAGES[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text
