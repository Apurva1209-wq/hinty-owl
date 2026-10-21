@echo off
cd /d "%~dp0"
echo ===== Hinty Backend =====
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt -q
if "%GEMINI_API_KEY%"=="" set /p GEMINI_API_KEY=Paste your Gemini API key (or press Enter to skip): 
if "%GROQ_API_KEY%"=="" set /p GROQ_API_KEY=Paste your Groq API key (or press Enter to skip): 
echo.
echo Starting backend at http://127.0.0.1:5000  (keep this window open)
python app.py
pause
