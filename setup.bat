@echo off
cd /d %~dp0
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
playwright install chromium
echo セットアップ完了。start.bat でアプリを起動してください。
pause
