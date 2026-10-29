@echo off
"%~dp0..\..\.venv\Scripts\python.exe" -B "%~dp0widget.py"
if errorlevel 1 pause
