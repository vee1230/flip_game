@echo off
echo ============================================================
echo  Memory Match Puzzle — Python FastAPI Backend
echo ============================================================
echo  API  : http://localhost:8000
echo  Docs : http://localhost:8000/docs
echo ============================================================
echo.

cd /d %~dp0

:: Install / upgrade dependencies silently
echo [SETUP] Checking dependencies...
pip install -r requirements.txt -q

:: Train ML models if the trained folder is missing or empty
if not exist "ml\trained\difficulty_model.pkl" (
    echo [ML] No trained models found. Training now...
    python -m ml.trainer
    echo [ML] Training complete!
    echo.
) else (
    echo [ML] Trained models found. Skipping training.
    echo.
)

echo [SERVER] Starting FastAPI server...
echo Press Ctrl+C to stop.
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
