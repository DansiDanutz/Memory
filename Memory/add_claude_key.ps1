# PowerShell script to add Claude API key

Write-Host ""
Write-Host "Claude API Key Setup" -ForegroundColor Cyan
Write-Host "=" * 50
Write-Host ""

$claudeKey = Read-Host "Please paste your Claude API key (starts with sk-ant-)"

if ($claudeKey) {
    $envFile = ".env"
    
    if (Test-Path $envFile) {
        # Read the file
        $content = Get-Content $envFile -Raw
        
        # Replace the Claude API key line
        $content = $content -replace 'CLAUDE_API_KEY=your_claude_api_key_here', "CLAUDE_API_KEY=$claudeKey"
        
        # Write back to file
        $content | Set-Content $envFile -NoNewline
        
        Write-Host ""
        Write-Host "SUCCESS: Claude API key has been added to .env file!" -ForegroundColor Green
        Write-Host ""
        Write-Host "To start the server, run:" -ForegroundColor Yellow
        Write-Host "python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"
    } else {
        Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    }
} else {
    Write-Host "No key entered. No changes made." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")