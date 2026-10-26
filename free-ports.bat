@echo off
REM Frees the Wellstride ports (8001 backend, 8081 frontend): kills whatever listens there, with its child processes,
REM and repeats until nothing does. Called by start-wellstride.bat and stop-wellstride.bat.
setlocal enabledelayedexpansion
set BUSY=0
for %%P in (8001 8081) do (
  call :free %%P
)
exit /b %BUSY%

:free
set /a tries=0
:again
set found=
for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%1 .*LISTENING"') do (
  set found=1
  taskkill /F /T /PID %%A >nul 2>&1
)
if defined found (
  set /a tries+=1
  if !tries! geq 15 (
    echo Port %1 is still in use after 15 tries. Close the program using it and run again.
    set BUSY=1
    exit /b 1
  )
  ping -n 2 127.0.0.1 >nul
  goto again
)
echo Port %1 is free.
exit /b 0
