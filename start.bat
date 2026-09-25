@echo off
title India Airfare Price Index Launcher

echo ========================================================
echo   India Airfare Price Index - Starting Application...
echo ========================================================
echo.

set PYTHONPATH=%~dp0apps\scraper\src

echo [1/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "API Server" /min cmd /c "set PYTHONPATH=%~dp0apps\scraper\src&& python -m uvicorn apps.api.src.main:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting Web Server on http://127.0.0.1:8080 ...
start "Web Server" /min cmd /c "python -m http.server 8080 --directory web"

echo [3/3] Waiting for servers to initialize...
ping 127.0.0.1 -n 3 >nul

echo Launching application in default browser...
start http://localhost:8080/index.html

echo.
echo ========================================================
echo   Application successfully started!
echo   - Web Dashboard: http://localhost:8080/index.html
echo   - API Endpoint:  http://127.0.0.1:8000/api/observations
echo ========================================================
echo.
