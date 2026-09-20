@echo off
setlocal

:: ── APIx Launcher ──────────────────────────────────────────────────────────
:: Starts the FastAPI backend (port 8000) and the Vite frontend (port 5173),
:: then opens the dashboard in the default browser.
:: Run this file from the apix\ directory.

title APIx – Airfare Price Index

:: Change to the directory where this batch file lives
cd /d "%~dp0"

echo.
echo  ============================================
echo   APIx – Airfare Price Index
echo  ============================================
echo.

:: ── Check Python is available ───────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] python not found. Please activate your virtual environment first.
    pause
    exit /b 1
)

:: ── Check Node / npm are available ─────────────────────────────────────────
where npm >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] npm not found. Please install Node.js.
    pause
    exit /b 1
)

:: ── Start FastAPI backend in a new window ───────────────────────────────────
echo  Starting backend on http://localhost:8000 ...
start "APIx Backend" cmd /k "cd /d "%~dp0" && uvicorn apix.api:app --reload --host 0.0.0.0 --port 8000"

:: Give uvicorn a moment to bind the port
timeout /t 3 /nobreak >nul

:: ── Start Vite frontend in a new window ────────────────────────────────────
echo  Starting frontend on http://localhost:5173 ...
start "APIx Frontend" cmd /k "cd /d "%~dp0web" && npm run dev"

:: Give Vite a moment to compile
timeout /t 4 /nobreak >nul

:: ── Open dashboard in default browser ──────────────────────────────────────
echo  Opening dashboard in default browser...
start "" "http://localhost:5173"

echo.
echo  Both servers are running.
echo   Backend  ^>  http://localhost:8000  (API docs: /docs)
echo   Frontend ^>  http://localhost:5173
echo.
echo  Close the Backend and Frontend windows to stop the servers.
echo.

endlocal
