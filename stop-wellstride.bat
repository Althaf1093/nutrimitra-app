@echo off
REM Stops the backend and frontend (by window and by port) and the MongoDB container.
taskkill /FI "WINDOWTITLE eq Wellstride Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Wellstride Frontend*" /T /F >nul 2>&1
call "%~dp0free-ports.bat"
docker stop nutrimitra-mongo
echo Stopped.
