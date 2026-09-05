#!/usr/bin/env bash
set -euo pipefail

python -m pip install -e ".[dev,gui]"
python -m PyInstaller --clean --noconfirm v2s.spec
python -m PyInstaller --clean --noconfirm v2s-gui.spec
echo "Build complete. Binaries are in dist/v2s and dist/v2s-gui"
