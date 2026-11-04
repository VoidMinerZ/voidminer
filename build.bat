@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
if not exist ".venv\Scripts\python.exe" ( %PY% -m venv .venv )
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller || (echo Install failed & pause & exit /b 1)
echo ok> ".venv\.deps_ok"
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name "VoidMiner Client" ^
  --icon assets\icon.ico --add-data "assets;assets" ^
  --collect-all customtkinter --collect-all minecraft_launcher_lib ^
  --hidden-import keyring.backends.Windows main.py || (echo Build failed & pause & exit /b 1)
echo.
echo Done: dist\VoidMiner Client\VoidMiner Client.exe
pause
endlocal
