@echo off
setlocal
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo Virtual environment not found. Run setup.bat first.
  pause
  exit /b 1
)
python -m app.gui.main_window
pause
