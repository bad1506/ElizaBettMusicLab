@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%..\.venv\Scripts\python.exe" if not exist "%ROOT%.venv\Scripts\python.exe" (
  echo [ERROR] Python .venv not found.
  pause
  exit /b 1
)
if exist "%ROOT%requirements.txt" (
  if exist "%ROOT%..\.venv\Scripts\python.exe" "%ROOT%..\.venv\Scripts\python.exe" -m pip install -r "%ROOT%requirements.txt"
  if exist "%ROOT%.venv\Scripts\python.exe" "%ROOT%.venv\Scripts\python.exe" -m pip install -r "%ROOT%requirements.txt"
)
cd /d "%ROOT%ai-engineer-ui"
call npm install --no-audit --no-fund
if errorlevel 1 echo [WARNING] Frontend dependency installation failed.
echo.
echo Installation finished. Run run_lab.bat
pause
