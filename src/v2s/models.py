from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import i18n


@dataclass(frozen=True)
class ModelInfo:
    name: str
    repo_id: str
    size_hint: str
    note: str = ""

    @property
    def repo_url(self) -> str:
        endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
        return f"{endpoint}/{self.repo_id}"

    @property
    def model_file_url(self) -> str:
        return f"{self.repo_url}/resolve/main/model.bin"


MODELS: dict[str, ModelInfo] = {
    "tiny": ModelInfo("tiny", "Systran/faster-whisper-tiny", "~75 MB"),
    "tiny.en": ModelInfo("tiny.en", "Systran/faster-whisper-tiny.en", "~75 MB", "English only"),
    "base": ModelInfo("base", "Systran/faster-whisper-base", "~145 MB"),
    "base.en": ModelInfo("base.en", "Systran/faster-whisper-base.en", "~145 MB", "English only"),
    "small": ModelInfo("small", "Systran/faster-whisper-small", "~484 MB"),
    "small.en": ModelInfo("small.en", "Systran/faster-whisper-small.en", "~484 MB", "English only"),
    "medium": ModelInfo("medium", "Systran/faster-whisper-medium", "~1.5 GB"),
    "medium.en": ModelInfo("medium.en", "Systran/faster-whisper-medium.en", "~1.5 GB", "English only"),
    "large-v1": ModelInfo("large-v1", "Systran/faster-whisper-large-v1", "~3.1 GB"),
    "large-v2": ModelInfo("large-v2", "Systran/faster-whisper-large-v2", "~3.1 GB"),
    "large-v3": ModelInfo("large-v3", "Systran/faster-whisper-large-v3", "~3.1 GB"),
    "large-v3-turbo": ModelInfo(
        "large-v3-turbo",
        "Systran/faster-whisper-large-v3-turbo",
        "~1.6 GB",
        "Faster; recommended for daily use",
    ),
    "distil-large-v3": ModelInfo(
        "distil-large-v3",
        "Systran/faster-whisper-distil-large-v3",
        "~1.6 GB",
        "Distilled model; faster",
    ),
    "distil-medium.en": ModelInfo(
        "distil-medium.en",
        "Systran/faster-whisper-distil-medium.en",
        "~1.5 GB",
        "English-only distilled model",
    ),
    "distil-small.en": ModelInfo(
        "distil-small.en",
        "Systran/faster-whisper-distil-small.en",
        "~484 MB",
        "English-only distilled model",
    ),
}


def get_model_info(name: str) -> Optional[ModelInfo]:
    key = name.strip().lower()
    return MODELS.get(key)


def default_model_dir() -> Path:
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        base = Path(hf_home)
    else:
        base = Path.home() / ".cache" / "huggingface"
    return base / "hub"


def ensure_model_known(name: str) -> None:
    if get_model_info(name) is not None:
        return
    path = Path(name)
    if path.exists() or "/" in name or "\\" in name:
        return
    raise ValueError(i18n.t("unknown_model", name=name))


def download_model(
    name: str,
    *,
    download_root: Optional[Path] = None,
) -> Path:
    info = get_model_info(name)
    if info is None:
        raise ValueError(i18n.t("unknown_model", name=name))

    from huggingface_hub import snapshot_download

    kwargs = {}
    if download_root is not None:
        download_root.mkdir(parents=True, exist_ok=True)
        kwargs["cache_dir"] = str(download_root)
    return Path(snapshot_download(repo_id=info.repo_id, **kwargs))
