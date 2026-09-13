@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   ELIZA BETT MUSIC LAB 11.2
echo   Starting Music AI Workstation...
echo ========================================

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python environment not found.
  echo Run install.bat first.
  pause
  exit /b 1
)

if not exist "ai-engineer-ui\node_modules" (
  echo [INFO] Frontend dependencies not found. Installing...
  cd ai-engineer-ui
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
  cd ..
)

echo [1/3] Starting backend...
start "Eliza Bett Music Lab - Backend" cmd /k "cd /d "%~dp0" && .venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo [2/3] Starting frontend...
start "Eliza Bett Music Lab - Frontend" cmd /k "cd /d "%~dp0ai-engineer-ui" && npm run dev -- --host 127.0.0.1"

timeout /t 4 /nobreak >nul

echo [3/3] Opening Eliza Bett Music Lab...
start "" "http://127.0.0.1:5173/"

echo.
echo Eliza Bett Music Lab is starting.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
echo.
echo You can close this window. Keep the Backend and Frontend windows running.
timeout /t 5 /nobreak >nul
exit /b 0
