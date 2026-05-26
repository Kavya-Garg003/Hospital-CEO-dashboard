@echo off
REM ============================================================
REM  Aarogya Hospital CEO Dashboard — ONE-CLICK STARTUP
REM  Starts: Frontend (Vite) + Backend (FastAPI) + opens browser
REM ============================================================
echo.
echo  ============================================================
echo   Aarogya Hospital CEO Dashboard
echo   Starting all services...
echo  ============================================================
echo.

REM Check if .env exists
if not exist "backend\.env" (
    echo  [!] backend\.env not found. Copying template...
    copy "backend\.env.template" "backend\.env"
    echo  [!] IMPORTANT: Edit backend\.env and set your ENCRYPTION_KEY and ANTHROPIC_API_KEY
    echo.
)

if not exist "frontend\.env.local" (
    copy "frontend\.env.template" "frontend\.env.local"
)

REM Start backend in a new window
echo  [1/3] Starting FastAPI backend on http://localhost:8000 ...
start "Hospital Backend" cmd /k "cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait 3 seconds for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend in a new window
echo  [2/3] Starting Vite frontend on http://localhost:3000 ...
start "Hospital Frontend" cmd /k "cd frontend && npm run dev"

REM Wait 3 seconds for frontend to start
timeout /t 3 /nobreak > nul

REM Open browser
echo  [3/3] Opening dashboard in browser...
start http://localhost:5173

echo.
echo  ============================================================
echo   Dashboard is running!
echo   Frontend:  http://localhost:5173
echo   API:       http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   CEO Login: ceo / Aarogya@2024
echo  ============================================================
echo.
echo  Press Ctrl+C in each window to stop services.
pause
