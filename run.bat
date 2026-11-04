@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version >nul 2>nul || (echo Python 3.10+ not found. Install it from python.org and tick "Add Python to PATH". & pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY% -m venv .venv || (echo Failed to create venv & pause & exit /b 1)
)
if not exist ".venv\.deps_ok" (
  echo Installing dependencies ^(first run only^)...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo Dependency install failed & pause & exit /b 1)
  echo ok> ".venv\.deps_ok"
)
start "" ".venv\Scripts\pythonw.exe" main.py
endlocal
