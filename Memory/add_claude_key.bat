@echo off
echo.
echo ========================================
echo CLAUDE API KEY SETUP
echo ========================================
echo.
echo This will add your Claude API key to line 24 of the .env file
echo.
set /p CLAUDE_KEY="Paste your Claude API key (starts with sk-ant-): "

if "%CLAUDE_KEY%"=="" (
    echo.
    echo ERROR: No key entered. Exiting...
    pause
    exit /b 1
)

echo.
echo Updating .env file...
powershell -NoProfile -Command "(Get-Content .env -Raw) -replace 'CLAUDE_API_KEY=your_claude_api_key_here', 'CLAUDE_API_KEY=%CLAUDE_KEY%' | Set-Content .env -NoNewline"

echo.
echo ========================================
echo SUCCESS! Claude API key has been added.
echo ========================================
echo.
echo To start the server, run:
echo python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
echo.
echo Access dashboard at: http://localhost:8080/dashboard
echo.
pause