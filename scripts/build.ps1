$ErrorActionPreference = "Stop"

python -m pip install -e ".[dev,gui]"
python -m PyInstaller --clean --noconfirm v2s.spec
python -m PyInstaller --clean --noconfirm v2s-gui.spec
Write-Host "Build complete. Binaries are in dist/v2s.exe and dist/v2s-gui.exe"
