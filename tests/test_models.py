import pytest

from v2s import models


def test_model_registry_has_repo_ids():
    assert models.get_model_info("small").repo_id == "Systran/faster-whisper-small"
    assert models.get_model_info("large-v3-turbo").repo_url


def test_all_models_expose_download_urls():
    for info in models.MODELS.values():
        assert info.repo_url.startswith("https://")
        assert "/resolve/main/model.bin" in info.model_file_url


def test_unknown_model_fails():
    from v2s import i18n

    i18n.set_language("en")
    with pytest.raises(ValueError):
        models.ensure_model_known("not-a-model")

