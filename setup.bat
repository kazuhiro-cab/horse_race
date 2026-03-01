@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0.venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto :error
)

call "%~dp0.venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install --upgrade pip
if errorlevel 1 goto :error

pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :error

python -m playwright install chromium
if errorlevel 1 goto :error

echo Setup complete. Start the app with start.bat
pause
exit /b 0

:error
echo Setup failed. Check Python, network, and permissions.
pause
exit /b 1
