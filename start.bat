@echo off
title Indian Airfare Price Index (APIx) Launcher
color 0A

echo ===============================================================================
echo                INDIAN AIRFARE PRICE INDEX (APIx) - SIH 2026
echo         Statistical Price Index aligned with MoSPI CPI 2024 (2024 = 100)
echo ===============================================================================
echo.

cd /d "%~dp0"

echo [1/3] Configuring environment paths...
set PYTHONPATH=%CD%;%CD%\apps\scraper\src;%CD%\apps\api\src

echo [2/3] Starting FastAPI Backend on http://localhost:8000 ...
start "APIx Backend (FastAPI)" cmd /k "title APIx Backend API && cd /d ""%~dp0"" && set PYTHONPATH=%CD%;%CD%\apps\scraper\src;%CD%\apps\api\src && python -m uvicorn apps.api.src.main:app --host 0.0.0.0 --port 8000 --reload"

echo [3/3] Starting Vite React Frontend on http://localhost:5173 ...
start "APIx Frontend (Vite React)" cmd /k "title APIx Frontend Dashboard && cd /d ""%~dp0\web"" && npm run dev"

echo.
echo Waiting 4 seconds for local servers to initialize...
timeout /t 4 /nobreak >nul

echo Opening APIx Dashboard in default browser...
start http://localhost:5173

echo.
echo ===============================================================================
echo   APIx Services Successfully Launched:
echo   - Frontend Dashboard: http://localhost:5173
echo   - Backend API Docs:   http://localhost:8000/docs
echo   - Quality Metrics:    http://localhost:8000/api/v1/quality-metrics
echo   - Airfare Index API:  http://localhost:8000/api/v1/airfare-index
echo ===============================================================================
echo Press any key to exit this launcher window (services will keep running)...
pause >nul
