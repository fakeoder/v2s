# v2s

v2s is a cross-platform video subtitle tool. It transcribes video speech with `faster-whisper`, optionally translates subtitles into a target language, and can re-encode or mux subtitles into a new video with `ffmpeg`.

The CLI is the primary interface. The desktop GUI is a wrapper around the same command layer.

## Features

- Whisper transcription via `faster-whisper`
- Subtitle formats: SRT, VTT, ASS, JSON, TXT
- Translation: Google Translate or OpenAI-compatible API
- Video output: hard subtitles (re-encode) or soft subtitle track (mux)
- One-command pipeline: `v2s run`
- Desktop GUI with English and Chinese UI
- Packaged software contains no models; models are downloaded on demand
- Cross-platform builds for Windows, Linux, and macOS

## Install

Python 3.9+:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e .
```

GUI extra:

```bash
python -m pip install -e ".[gui]"
```

ffmpeg is resolved from `PATH`, then `FFMPEG_BIN`, then the bundled `imageio-ffmpeg` binary.

## Language

Default UI language is English. Set `--lang` for a single command:

```bash
v2s --lang zh transcribe demo.mp4
```

Or set `V2S_LANG`:

```bash
export V2S_LANG=zh
```

Supported in v1: `en`, `zh`.

## Models

Models are not bundled with the package. Users choose and download them on demand.

List models and default download URLs:

```bash
v2s model list
```

Download a model:

```bash
v2s model download small
```

Download into a custom cache directory, then point `--model-dir` at it:

```bash
v2s model download small --dir ./models
v2s transcribe demo.mp4 --model small --model-dir ./models
```

Default model addresses (Hugging Face):

| Name | Approx. size | Default URL |
| --- | --- | --- |
| tiny | 75 MB | https://huggingface.co/Systran/faster-whisper-tiny |
| base | 145 MB | https://huggingface.co/Systran/faster-whisper-base |
| small | 484 MB | https://huggingface.co/Systran/faster-whisper-small |
| medium | 1.5 GB | https://huggingface.co/Systran/faster-whisper-medium |
| large-v2 | 3.1 GB | https://huggingface.co/Systran/faster-whisper-large-v2 |
| large-v3 | 3.1 GB | https://huggingface.co/Systran/faster-whisper-large-v3 |
| large-v3-turbo | 1.6 GB | https://huggingface.co/Systran/faster-whisper-large-v3-turbo |
| distil-large-v3 | 1.6 GB | https://huggingface.co/Systran/faster-whisper-distil-large-v3 |

China mirror:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## CLI Usage

Transcribe:

```bash
v2s transcribe demo.mp4 -m small
```

Transcribe and translate:

```bash
v2s transcribe demo.mp4 -l en -t zh --translation-provider google
```

OpenAI-compatible translation:

```bash
export OPENAI_API_KEY=sk-...
v2s transcribe demo.mp4 -t zh --translation-provider openai
```

Burn an existing subtitle (hard):

```bash
v2s burn demo.mp4 -s demo.zh.srt --mode hard
```

Mux a soft subtitle track:

```bash
v2s burn demo.mp4 -s demo.zh.srt --mode soft --language zh
```

Full pipeline: transcribe, translate, and burn:

```bash
v2s run demo.mp4 -t zh --burn-mode hard
```

Subtitles only:

```bash
v2s run demo.mp4 --burn-mode none
```

## GUI

```bash
v2s gui
```

Or launch the packaged `v2s-gui` executable. The GUI supports:

- Drag and drop or file picker for videos
- Task mode: subtitles only, or subtitles plus video
- Whisper, translation, ffmpeg, and encode settings
- On-demand model download
- Live progress, logs, and cancel
- English / 中文 language switch

## Build

Install dev and GUI dependencies:

```bash
python -m pip install -e ".[dev,gui]"
python -m pytest
```

Linux / macOS:

```bash
./scripts/build.sh
```

Windows PowerShell:

```powershell
.\scripts\build.ps1
```

Artifacts in `dist/`: `v2s` / `v2s.exe` for CLI, and `v2s-gui` / `v2s-gui.exe` for GUI. GitHub Actions builds all three OSes and attaches them to tagged releases.

The packaged binaries contain only the software. Whisper model weights, translation API keys, and video data are never bundled.

## Notes

- Hard subtitle mode requires ffmpeg with libass.
- Soft subtitles: MP4/MOV use `mov_text`, MKV copies the stream, WebM uses WebVTT.
- Unsigned macOS builds may require right-click open or `xattr -dr com.apple.quarantine`.

## License

MIT
