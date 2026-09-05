from click.testing import CliRunner

from v2s.cli import cli


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "transcribe" in result.output
    assert "burn" in result.output
    assert "run" in result.output
    assert "gui" in result.output


def test_transcribe_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["transcribe", "--help"])
    assert result.exit_code == 0
    assert "--translate" in result.output
    assert "--burn-mode" not in result.output


def test_run_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "--burn-mode" in result.output
    assert "--translate" in result.output


def test_gui_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["gui", "--help"])
    assert result.exit_code == 0
    assert "Open the desktop GUI" in result.output


def test_model_list_shows_urls():
    runner = CliRunner()
    result = runner.invoke(cli, ["model", "list"])
    assert result.exit_code == 0
    assert "small" in result.output
    assert "huggingface.co/Systran/faster-whisper-small" in result.output


def test_lang_option_changes_output_language():
    runner = CliRunner()
    result = runner.invoke(cli, ["--lang", "zh", "model", "list"])
    assert result.exit_code == 0
    assert "名称" in result.output
