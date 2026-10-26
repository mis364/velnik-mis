@echo off
cd /d "%~dp0"
set "PYTHON="
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\.local\bin\python3.14.exe" set "PYTHON=%USERPROFILE%\.local\bin\python3.14.exe"
if not defined PYTHON (
  where python >nul 2>&1
  if not errorlevel 1 set "PYTHON=python"
)
if not defined PYTHON (
  echo Python was not found. Install Python 3.10 or newer and reopen this window.
  echo The launcher also checks %%USERPROFILE%%\.local\bin\python3.14.exe.
  pause
  exit /b 1
)
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Creating the Sales MIS virtual environment...
  "%PYTHON%" -m venv "%~dp0.venv"
  if errorlevel 1 (
    echo Could not create the Python virtual environment.
    pause
    exit /b 1
  )
)
set "PYTHON=%~dp0.venv\Scripts\python.exe"
"%PYTHON%" -c "import pandas, openpyxl; assert tuple(map(int, pandas.__version__.split('.')[:2])) >= (2, 0); assert tuple(map(int, openpyxl.__version__.split('.')[:2])) >= (3, 1)" >nul 2>&1
if errorlevel 1 (
  echo Installing missing Sales MIS dependencies...
  "%PYTHON%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Could not install the required Python packages.
    pause
    exit /b 1
  )
)
"%PYTHON%" app.py
pause
