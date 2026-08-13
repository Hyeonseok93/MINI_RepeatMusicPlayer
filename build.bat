@echo off
setlocal enabledelayedexpansion

REM ========================================================
REM MINI Repeat Music Player - Single Executable Optimized Build
REM ========================================================

set APP_NAME=RepeatMusicPlayer
set ENTRY=RepeatMusicPlayerApp.py
set ICON=assets\app.ico
set SPLASH_IMG=assets\app.png

REM Terminate any running instance of the app before build/move
taskkill /F /IM "%APP_NAME%.exe" >nul 2>&1

echo [1/4] Clean existing build artifacts...
if exist build rmdir /S /Q build >nul 2>&1
if exist dist rmdir /S /Q dist >nul 2>&1
if exist %APP_NAME%.spec del /F /Q %APP_NAME%.spec >nul 2>&1

echo [2/4] Setup isolated virtual environment (.venv)...
if not exist .venv (
    py -3 -m venv .venv
)
call .venv\Scripts\activate.bat

echo [3/4] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [4/4] Building optimized single executable (%APP_NAME%.exe)...

set "ICONOPT="
set "DATAOPT="
if exist "%ICON%" (
  set "ICONOPT=--icon=%ICON%"
)
if exist "assets" (
  set "DATAOPT=--add-data=assets;assets"
)

set "SPLASHOPT="
if exist "%SPLASH_IMG%" (
  set "SPLASHOPT=--splash=%SPLASH_IMG%"
)

REM Massively optimize startup and size: --onefile, --noupx, --optimize=2 and excluding heavy unused Qt modules
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --name "%APP_NAME%" ^
  --onefile ^
  --noupx ^
  --windowed ^
  --optimize=2 ^
  --exclude-module PySide6.QtWebEngineCore ^
  --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.Qt3DRender ^
  --exclude-module PySide6.QtQuick ^
  --exclude-module PySide6.QtQml ^
  --exclude-module PySide6.QtPdf ^
  --exclude-module PySide6.QtSql ^
  --exclude-module PySide6.QtSensors ^
  --exclude-module PySide6.QtVirtualKeyboard ^
  --exclude-module PySide6.QtSpatialAudio ^
  --exclude-module tkinter ^
  --exclude-module unittest ^
  %SPLASHOPT% ^
  %ICONOPT% ^
  %DATAOPT% ^
  "%ENTRY%"

echo.
if exist "dist\%APP_NAME%.exe" (
  REM Terminate running app if user opened it during build
  taskkill /F /IM "%APP_NAME%.exe" >nul 2>&1

  REM Delete existing root exe / folder if present
  if exist "%APP_NAME%" rmdir /S /Q "%APP_NAME%" >nul 2>&1
  if exist "%APP_NAME%.exe" del /F /Q "%APP_NAME%.exe" >nul 2>&1

  REM Move executable to project root and clean dist/build/.venv temporary folders
  move /Y "dist\%APP_NAME%.exe" "%APP_NAME%.exe" >nul 2>&1
  if exist dist rmdir /S /Q dist >nul 2>&1
  if exist build rmdir /S /Q build >nul 2>&1
  if exist %APP_NAME%.spec del /F /Q %APP_NAME%.spec >nul 2>&1
  for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

  call .venv\Scripts\deactivate.bat >nul 2>&1
  if exist .venv rmdir /S /Q .venv >nul 2>&1

  if exist "%APP_NAME%.exe" (
    echo ========================================================
    echo  [SUCCESS] Portable executable generated: %APP_NAME%.exe
    echo ========================================================
  ) else (
    echo [ERROR] Failed to move %APP_NAME%.exe to root directory.
  )
) else (
    echo [ERROR] Build failed. Check the error log above.
    call .venv\Scripts\deactivate.bat >nul 2>&1
    if exist .venv rmdir /S /Q .venv >nul 2>&1
)

echo Press any key to continue...
pause >nul
