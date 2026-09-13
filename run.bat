@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Сначала запусти install.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m streamlit run app.py
pause
