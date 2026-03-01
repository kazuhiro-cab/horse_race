@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0.venv\Scripts\activate.bat" (
  echo .venv not found. Run setup.bat first.
  pause
  exit /b 1
)

call "%~dp0.venv\Scripts\activate.bat"
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo PySide6 is missing. Installing requirements...
  pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
  )
)

python -m app.gui.main_window
if errorlevel 1 (
  echo Application exited with error.
)
pause
