@echo off
setlocal

where python3 >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=python3"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PYTHON=python"
  ) else (
    echo Error: python not found. Install Python and retry.
    exit /b 1
  )
)

"%PYTHON%" "%~dp0yt-archive.py" %*
