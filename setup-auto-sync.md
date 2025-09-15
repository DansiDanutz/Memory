# Auto-Sync Setup Guide

## Method 1: Windows Task Scheduler (Recommended)

1. Open Task Scheduler (Win+R, type `taskschd.msc`)
2. Click "Create Basic Task"
3. Name: "Memory App Git Sync"
4. Trigger: Daily (then modify to run every hour)
5. Action: Start a program
6. Program: `powershell.exe`
7. Arguments: `-ExecutionPolicy Bypass -File "C:\Users\dansi\Desktop\Memory\auto-sync.ps1"`
8. Finish and edit to run every hour

## Method 2: Run sync script manually
Double-click `auto-sync.bat` whenever you want to sync

## Method 3: Git hooks (auto-commit on file changes)
Create `.git/hooks/post-commit`:
```bash
#!/bin/sh
git push origin master
```

## Method 4: Use file watcher tools
- **For Windows**: Use WatchMan or FileSystemWatcher
- **For Replit**: Already has auto-save, just need periodic push

## Method 5: VS Code Extension
Install "Git Auto Commit" extension in VS Code for automatic commits

## For Replit Side:
Add to replit.nix or .replit file:
```bash
# Auto sync every 30 minutes
while true; do
  git add . && git commit -m "Auto-sync from Replit" && git push
  sleep 1800
done &
```