@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m venv .venv
) else (
  python -m venv .venv
)
if errorlevel 1 goto :error

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install --upgrade pip
if errorlevel 1 goto :error

pip install -r requirements.txt
if errorlevel 1 goto :error

python -m playwright install chromium
if errorlevel 1 goto :error

echo Setup completed. Start app with start.bat
pause
exit /b 0

:error
echo Setup failed. Please check Python installation and network access.
pause
exit /b 1
