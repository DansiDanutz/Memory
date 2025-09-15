# PowerShell auto-sync script
Set-Location "C:\Users\dansi\Desktop\Memory"

# Check if there are changes
$status = git status --porcelain

if ($status) {
    git add .
    git commit -m "Auto-sync: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    git push origin master
    Write-Host "✓ Synced at $(Get-Date)" -ForegroundColor Green
} else {
    Write-Host "No changes to sync" -ForegroundColor Yellow
}