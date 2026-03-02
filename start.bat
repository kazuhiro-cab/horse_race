@echo off
setlocal
cd /d "%~dp0"

echo [keiba-predictor] startup script

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "VENV_ACT=%~dp0.venv\Scripts\activate.bat"

if not exist "%VENV_PY%" (
  echo .venv not found. Run setup.bat first.
  pause
  exit /b 1
)

if not exist "%VENV_ACT%" (
  echo activate.bat not found in .venv. Run setup.bat again.
  pause
  exit /b 1
)

call "%VENV_ACT%"
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

"%VENV_PY%" -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo PySide6 is missing. Installing requirements...
  "%VENV_PY%" -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
  )
)

set "LOG_FILE=%~dp0start_error.log"
if exist "%LOG_FILE%" del /q "%LOG_FILE%"

echo Launching app window...
"%VENV_PY%" -m app 1>"%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo Application exited with error.
  if exist "%LOG_FILE%" (
    echo --- error log ---
    type "%LOG_FILE%"
    echo ---------------
  )
) else (
  if exist "%LOG_FILE%" del /q "%LOG_FILE%"
)

pause
