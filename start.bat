@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run setup.bat first.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo PySide6 is not installed. Installing requirements...
  pip install -r requirements.txt
  if errorlevel 1 (
    echo Failed to install requirements. Check network/proxy settings.
    pause
    exit /b 1
  )
)

python -m app.gui.main_window
if errorlevel 1 (
  echo Application exited with error.
)
pause
