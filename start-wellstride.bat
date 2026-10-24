@echo off
REM Starts everything for local development: Docker, MongoDB, backend, frontend, then opens the app.
REM Usage: double-click, or run  start-wellstride.bat        (add "clear" to clear the Expo cache: start-wellstride.bat clear)
setlocal
set ROOT=%~dp0
set EXPO_FLAGS=--web
if /I "%1"=="clear" set EXPO_FLAGS=--web --clear

echo [1/5] Checking Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
  echo Docker is not running. Starting Docker Desktop, please wait...
  start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
)
:waitdocker
docker info >nul 2>&1
if %errorlevel% neq 0 (
  timeout /t 5 /nobreak >nul
  goto waitdocker
)
echo Docker is running.

echo [2/5] Starting MongoDB...
docker start nutrimitra-mongo
if %errorlevel% neq 0 (
  echo Could not start the nutrimitra-mongo container. Run "docker ps -a" to check it exists.
  pause
  exit /b 1
)

echo [3/5] Starting backend (new window)...
start "Wellstride Backend" cmd /k "cd /d %ROOT%backend && .venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8001"

echo [4/5] Starting frontend (new window)...
start "Wellstride Frontend" cmd /k "cd /d %ROOT%frontend && set CI=1&& npx expo start %EXPO_FLAGS%"

echo [5/5] Waiting for the backend and the app, then opening the browser...
:waitbackend
curl -s -o nul http://localhost:8001/api/
if %errorlevel% neq 0 (
  timeout /t 3 /nobreak >nul
  goto waitbackend
)
echo Backend is up.
:waitfrontend
curl -s -o nul http://localhost:8081
if %errorlevel% neq 0 (
  timeout /t 5 /nobreak >nul
  goto waitfrontend
)
start "" http://localhost:8081
echo Done. Close the two Wellstride windows (or run stop-wellstride.bat) when finished.
endlocal
