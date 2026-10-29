@echo off
"%~dp0..\..\.venv\Scripts\python.exe" -B "%~dp0widget.py" --snapshot
if errorlevel 1 pause
