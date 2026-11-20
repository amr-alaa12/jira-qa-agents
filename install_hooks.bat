@echo off
echo ========================================================
echo Installing Git Pre-Push Hook for Jira QA Agents...
echo ========================================================
python scripts\install_hooks.py
if %ERRORLEVEL% NEQ 0 (
    echo Trying with virtual environment python...
    .\.venv\Scripts\python.exe scripts\install_hooks.py
)
echo.
pause
