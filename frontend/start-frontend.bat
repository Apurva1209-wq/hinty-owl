@echo off
cd /d "%~dp0"
echo ===== Hinty Frontend =====
echo Open http://localhost:5500 in your browser (keep this window open)
start "" http://localhost:5500
python -m http.server 5500
pause
