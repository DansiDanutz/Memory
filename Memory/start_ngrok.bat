@echo off
echo ============================================================
echo STARTING NGROK TUNNEL FOR MCP SERVER
echo ============================================================
echo.
echo Configuring ngrok with auth token...
C:\ngrok\ngrok.exe config add-authtoken [YOUR_NGROK_AUTH_TOKEN]
echo.
echo Starting ngrok tunnel on port 3000...
echo.
echo IMPORTANT: Copy the HTTPS URL that appears below!
echo Look for: https://[random-string].ngrok-free.app
echo.
echo ============================================================
C:\ngrok\ngrok.exe http 3000