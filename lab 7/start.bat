@echo off
cd /d "%~dp0"
echo Starting Smart Game Store. Keep this window open.
echo Browser address: http://127.0.0.1:5000
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py --open-browser
) else if exist ".venv\bin\python.exe" (
  ".venv\bin\python.exe" app.py --open-browser
) else (
  python app.py --open-browser
)
pause
