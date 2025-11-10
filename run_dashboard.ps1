# PowerShell script to run the dashboard
cd D:\Optimization

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
.venv\Scripts\Activate.ps1

# Run Streamlit dashboard
Write-Host "Starting Streamlit dashboard..." -ForegroundColor Green
Write-Host "Dashboard will be available at: http://localhost:8501" -ForegroundColor Yellow
Write-Host ""
streamlit run src/dashboard.py

