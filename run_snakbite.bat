@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creating the Snakbite virtual environment...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)
if not exist .venv\Scripts\python.exe (
  echo Python could not create a virtual environment. Install Python 3.10+ and enable Add Python to PATH.
  pause
  exit /b 1
)
echo Installing or updating project dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your internet connection and README troubleshooting.
  pause
  exit /b 1
)
echo Starting Snakbite. Keep this window open; press Ctrl+C to stop.
.venv\Scripts\python.exe -m streamlit run app.py
if errorlevel 1 pause
