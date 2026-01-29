@echo off
echo Starting OCR System...
pause

echo Checking Python...
python --version
if %errorlevel% neq 0 (
    echo Python not found! Please install Python.
    pause
    exit /b
)

echo Installing requirements...
pip install -r requirements.txt

echo Starting App...
echo Opening browser...
start http://localhost:8501
python -m streamlit run app.py --server.address 0.0.0.0 --server.headless true

pause
