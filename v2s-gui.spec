# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.datastruct import TOC

datas = []
binaries = []
hiddenimports = []

for package in (
    "PySide6",
    "av",
    "ctranslate2",
    "deep_translator",
    "faster_whisper",
    "huggingface_hub",
    "imageio_ffmpeg",
    "pysubs2",
    "rich",
    "shiboken6",
    "tokenizers",
):
    try:
        package_datas, package_binaries, package_hiddenimports = collect_all(package)
    except Exception:
        continue
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports


def keep_binary(entry):
    source = entry[1]
    return not (
        isinstance(source, str)
        and "codex-runtimes" in source.lower().replace("\\", "/")
    )


binaries = [entry for entry in binaries if keep_binary(entry)]

a = Analysis(
    ["src/v2s/gui_app.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.binaries = TOC(entry for entry in a.binaries if keep_binary(entry))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="v2s-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
