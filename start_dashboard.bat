@echo off
REM Windows batch script to start the dashboard
REM This script activates the virtual environment and starts Streamlit

echo Starting AI Cost Optimizer Dashboard...

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Dependencies not installed!
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Start Streamlit dashboard
echo Starting dashboard...
streamlit run src/dashboard.py

pause

