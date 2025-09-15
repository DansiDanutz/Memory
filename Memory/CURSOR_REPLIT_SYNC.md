# Cursor ↔ Replit Synchronization Guide

## Overview
This guide shows you how to keep your Memory App project synchronized between Cursor IDE and Replit, ensuring seamless development across both platforms.

## Method 1: Git Repository Sync (Recommended)

### 1.1 Setup Git Repository
```bash
# In Cursor (local)
cd Memory
git init
git add .
git commit -m "Initial Memory App with Claude integration"

# Create repository on GitHub/GitLab
git remote add origin https://github.com/yourusername/memory-app.git
git push -u origin main
```

### 1.2 Connect Replit to Git
1. In Replit, create new Repl
2. Choose "Import from GitHub"
3. Enter your repository URL
4. Replit will automatically sync with your repo

### 1.3 Two-Way Sync Workflow
```bash
# Push changes from Cursor to Replit
git add .
git commit -m "Updated Claude integration"
git push origin main

# In Replit: Pull latest changes
git pull origin main
```

## Method 2: Replit Desktop App Integration

### 2.1 Install Replit Desktop
1. Download from [Replit Desktop](https://replit.com/desktop)
2. Install and login to your account
3. Your Repls appear as local folders

### 2.2 Open in Cursor
```bash
# Replit Desktop creates local folders at:
# Windows: C:\Users\[username]\Replit\[repl-name]
# Mac: ~/Replit/[repl-name]

# Open in Cursor
cursor "C:\Users\dansi\Replit\memory-app"
```

### 2.3 Auto-Sync Benefits
- Real-time synchronization
- Work offline in Cursor
- Changes sync when online
- No manual git commands needed

## Method 3: VS Code Extension + Cursor

### 3.1 Install Replit Extension
Since Cursor is VS Code-based, you can use the Replit extension:

1. Open Cursor
2. Go to Extensions (Ctrl+Shift+X)
3. Search "Replit"
4. Install "Replit" extension
5. Login with your Replit credentials

### 3.2 Direct Repl Access
- Browse your Repls in Cursor sidebar
- Edit files directly
- Run code in integrated terminal
- Auto-sync enabled

## Method 4: Cloud Storage Sync

### 4.1 Using OneDrive/Google Drive
```bash
# Move project to cloud folder
mv Memory "C:\Users\dansi\OneDrive\Projects\Memory"

# Create symlink in original location
mklink /D "C:\Users\dansi\Desktop\Memory" "C:\Users\dansi\OneDrive\Projects\Memory"
```

### 4.2 Replit Cloud Storage
1. In Replit, enable "Always On" for your Repl
2. Use Replit's file sync API
3. Set up webhook for automatic updates

## Method 5: Advanced Sync with GitHub Actions

### 5.1 Create Sync Workflow
Create `.github/workflows/sync-replit.yml`:

```yaml
name: Sync to Replit
on:
  push:
    branches: [ main ]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to Replit
      env:
        REPLIT_TOKEN: ${{ secrets.REPLIT_TOKEN }}
      run: |
        curl -X POST \
          -H "Authorization: Bearer $REPLIT_TOKEN" \
          -H "Content-Type: application/json" \
          -d '{"repl_id": "your-repl-id"}' \
          https://replit.com/api/repls/pull
```

### 5.2 Automatic Deployment
- Every git push triggers Replit update
- Zero manual intervention
- Maintains deployment history

## Method 6: Real-Time Collaboration

### 6.1 Replit Multiplayer
1. In Replit, click "Share"
2. Enable "Anyone with link can edit"
3. Share link with team members
4. Multiple people can code simultaneously

### 6.2 Cursor Live Share (Alternative)
1. Install Live Share extension in Cursor
2. Start collaboration session
3. Share session link
4. Real-time collaborative editing

## Recommended Workflow for Memory App

### Daily Development Cycle
```bash
# Morning: Start in Cursor
git pull origin main  # Get latest changes

# Work on features locally in Cursor
# Test with Claude Code extension
# Make commits as you go

# Afternoon: Test in Replit
git push origin main  # Push to repository
# Replit auto-pulls changes
# Test deployment and live endpoints

# Evening: Final sync
git push origin main  # Ensure everything is synced
```

### Project Structure Sync
```
Memory/
├── app/                    # Core application
│   ├── claude_service.py   # Syncs to both platforms
│   ├── claude_router.py    # Syncs to both platforms
│   └── main.py            # Syncs to both platforms
├── requirements.txt        # Platform-specific versions
├── .replit                # Replit-specific config
├── main.py                # Replit entry point
├── CURSOR_REPLIT_SYNC.md  # This guide
└── REPLIT_CLAUDE_SETUP.md # Replit setup guide
```

## Platform-Specific Configurations

### 6.1 Cursor-Specific Files
Create `.cursor/` directory:
```
.cursor/
├── settings.json          # Cursor IDE settings
├── extensions.json        # Recommended extensions
└── launch.json           # Debug configurations
```

### 6.2 Replit-Specific Files
```
.replit                    # Replit configuration
replit.nix                # Nix environment
main.py                   # Replit entry point
```

### 6.3 Shared Configuration
```
.env.example              # Environment template
.gitignore               # Ignore platform-specific files
requirements.txt         # Shared dependencies
```

## Sync Automation Scripts

### 7.1 PowerShell Sync Script (Windows)
Create `sync-to-replit.ps1`:
```powershell
#!/usr/bin/env powershell
# Sync Memory App to Replit

Write-Host "🔄 Syncing Memory App to Replit..." -ForegroundColor Green

# Add all changes
git add .

# Commit with timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
git commit -m "Auto-sync from Cursor - $timestamp"

# Push to repository
git push origin main

Write-Host "✅ Sync completed!" -ForegroundColor Green
Write-Host "🚀 Check your Replit for updates" -ForegroundColor Yellow
```

### 7.2 Bash Sync Script (Cross-platform)
Create `sync-to-replit.sh`:
```bash
#!/bin/bash
# Sync Memory App to Replit

echo "🔄 Syncing Memory App to Replit..."

# Add all changes
git add .

# Commit with timestamp
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
git commit -m "Auto-sync from Cursor - $timestamp"

# Push to repository
git push origin main

echo "✅ Sync completed!"
echo "🚀 Check your Replit for updates"
```

## Environment Synchronization

### 8.1 Environment Variables
Create `sync-env.py`:
```python
#!/usr/bin/env python3
"""
Sync environment variables between Cursor and Replit
"""

import os
import requests
import json

def sync_env_to_replit():
    """Sync local .env to Replit secrets"""
    
    # Read local .env file
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    
    # Sync to Replit (requires Replit API token)
    replit_token = os.getenv('REPLIT_TOKEN')
    repl_id = os.getenv('REPL_ID')
    
    if replit_token and repl_id:
        for key, value in env_vars.items():
            # Update Replit secret
            response = requests.post(
                f'https://replit.com/api/repls/{repl_id}/secrets',
                headers={'Authorization': f'Bearer {replit_token}'},
                json={'key': key, 'value': value}
            )
            print(f"{'✅' if response.ok else '❌'} {key}")
    
    print("🔄 Environment sync completed!")

if __name__ == "__main__":
    sync_env_to_replit()
```

## Troubleshooting Sync Issues

### 9.1 Common Problems

**Git conflicts:**
```bash
# Reset to remote state
git fetch origin
git reset --hard origin/main
```

**Replit not updating:**
```bash
# Force pull in Replit console
git fetch --all
git reset --hard origin/main
```

**File permission issues:**
```bash
# Fix permissions
chmod +x sync-to-replit.sh
```

### 9.2 Debug Commands
```bash
# Check git status
git status
git log --oneline -5

# Check Replit connection
curl -H "Authorization: Bearer $REPLIT_TOKEN" \
     https://replit.com/api/user

# Test Claude integration
python -c "from app.claude_service import claude_service; print(claude_service.is_available())"
```

## Best Practices

### 10.1 Development Workflow
1. **Code in Cursor** - Use Claude Code extension for AI assistance
2. **Test locally** - Run FastAPI server locally
3. **Commit frequently** - Small, focused commits
4. **Sync to Replit** - Test in production environment
5. **Deploy from Replit** - Use Replit's deployment features

### 10.2 File Management
- Keep platform-specific files separate
- Use `.gitignore` for local-only files
- Sync shared configuration files
- Maintain separate environment files

### 10.3 Security
- Never commit API keys to git
- Use environment variables for secrets
- Keep Replit secrets separate from local .env
- Regularly rotate API keys

## Conclusion

You now have multiple ways to sync between Cursor and Replit:

✅ **Git Repository Sync** - Most reliable and professional
✅ **Replit Desktop App** - Easiest for beginners  
✅ **VS Code Extension** - Direct integration
✅ **Cloud Storage** - Simple file-based sync
✅ **GitHub Actions** - Automated deployment
✅ **Real-time Collaboration** - Team development

Choose the method that best fits your workflow. For the Memory App project, I recommend starting with **Git Repository Sync** as it's the most professional and gives you full version control.

Happy syncing! 🚀
