@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
py -3.11 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3.11"
if not defined PYTHON_CMD (
  python -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
  echo [ERROR] Python 3.11 x64 or python.exe not found.
  pause
  exit /b 1
)

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>nul
  if errorlevel 1 rmdir /s /q ".venv"
)
if not exist ".venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 exit /b 1
)

if not exist ".venv\.runtime_ready" (
  "%VENV_PYTHON%" -m pip install -r requirements-runtime.txt
  if errorlevel 1 exit /b 1
  > ".venv\.runtime_ready" echo PySide6=6.11.2
)

"%VENV_PYTHON%" -c "import sys; assert sys.version_info[:2] == (3, 11); import PySide6; import PySide6.QtCore; import bleak; from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager; assert PySide6.__version__ == '6.11.2'"
if errorlevel 1 (
  "%VENV_PYTHON%" -m pip install --force-reinstall -r requirements-runtime.txt
  if errorlevel 1 exit /b 1
  > ".venv\.runtime_ready" echo PySide6=6.11.2
)

"%VENV_PYTHON%" src\main.py --demo
endlocal
