@echo off
chcp 65001 >nul 2>&1
:: VoiceMeeter Toggle - PyInstaller build script
:: Generates a standalone .exe, requires Python + dependencies installed

cd /d "%~dp0"

echo [*] Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [!] Installing PyInstaller...
    python -m pip install pyinstaller
)

echo [*] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [*] Building VoiceMeeterToggle.exe...
pyinstaller --onefile --windowed --name "VoiceMeeterToggle" ^
    --hidden-import=comtypes.stream ^
    --hidden-import=voicemeeterlib ^
    --hidden-import=sounddevice ^
    --hidden-import=soundfile ^
    --hidden-import=pydub ^
    --hidden-import=keyboard ^
    --hidden-import=_cffi_backend ^
    --add-data "settings.py;." ^
    --add-data "snapshot.py;." ^
    --collect-all sounddevice ^
    --collect-all soundfile ^
    main.py

if %errorLevel% NEQ 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [OK] Build complete!
echo      Output: dist\VoiceMeeterToggle.exe
echo.
echo [NOTE] To use this .exe you need:
echo        - VoiceMeeter installed and running
echo        - ffmpeg in PATH (for MP3 playback)
echo        - Run as Administrator (for device switching)
pause
