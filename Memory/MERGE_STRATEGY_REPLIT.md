# 🔄 Safe Merge Strategy: Local → Replit

## Current Situation

### What's in Replit (Original)
- Basic Memory Bot with WhatsApp
- Azure Speech integration
- Simple Claude integration
- Basic PostgreSQL setup
- Running on port 5000

### What's New Here (Local)
- 40+ new files
- Gamified voice avatar system
- ElevenLabs agent integration
- Contact slots reward system
- MCP server for MD files
- Complete dashboard

## Step-by-Step Merge Process

### Phase 1: Prepare Local Changes

#### 1.1 Commit Everything Locally
```bash
# In your local Cursor/terminal
cd C:\Users\dansi\Desktop\Memory

# Check status
git status

# Add all new files
git add Memory/*.py Memory/*.md Memory/voice_services/

# Commit with detailed message
git commit -m "Major Update: Gamified Voice Avatar System with ElevenLabs

- Added gamification system (5 invites = 1 contact slot + voice avatar)
- Integrated ElevenLabs Conversational AI (Memo agent)
- Created voice services (ElevenLabs, Coqui, Fish Audio)
- Implemented contact-based permission scoring
- Added MCP server for MD file access
- Created invitation tracking dashboard
- WhatsApp invitation integration
- 40+ new files with complete documentation"
```

#### 1.2 Push to GitHub
```bash
# Push your changes
git push origin master
```

### Phase 2: Backup Replit (IMPORTANT!)

#### 2.1 In Replit Console
```bash
# Create backup branch
git checkout -b backup-before-merge
git add .
git commit -m "Backup: Before major merge"
git push origin backup-before-merge

# Return to master
git checkout master
```

#### 2.2 Download Replit Database
```bash
# Export current data if needed
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Phase 3: Merge in Replit

#### 3.1 Pull New Changes
```bash
# In Replit console
git fetch origin master

# Check what's coming
git log HEAD..origin/master --oneline

# Merge carefully
git pull origin master
```

#### 3.2 Handle Conflicts (if any)

**Expected Conflicts:**
1. `Memory/app/main.py` - We modified to load .env
2. `Memory/requirements.txt` - We added dependencies

**Resolution Strategy:**
```python
# For main.py - KEEP BOTH changes
# Our version adds:
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# For requirements.txt - MERGE additions
# Add these lines:
firecrawl-py==4.3.6
nest-asyncio==1.6.0
elevenlabs  # If not already there
```

### Phase 4: Update Replit Environment

#### 4.1 Add New Secrets in Replit
Go to Replit Secrets tab and add:
```
ELEVENLABS_API_KEY = sk_7052aea282a47c77461bda1a518f35e7c9048abe8e5b0444
FIRECRAWL_API_KEY = fc-ff01af8ec2ee46cfa56ed8d8f5adfea0
ANTHROPIC_API_KEY = (same as CLAUDE_API_KEY)
```

#### 4.2 Install New Dependencies
```bash
# In Replit Shell
pip install -r Memory/requirements.txt

# Or manually if needed:
pip install firecrawl-py==4.3.6
pip install nest-asyncio==1.6.0
pip install elevenlabs
pip install python-dotenv
```

### Phase 5: Database Updates

#### 5.1 Create New Tables
```python
# In Replit Shell
cd Memory
python

# Run this Python code
from database_models import init_database
engine, Session = init_database()
print("Database tables created successfully!")
exit()
```

### Phase 6: Test Core Functionality

#### 6.1 Test Existing Features (Should Still Work)
```bash
# Test WhatsApp webhook
curl -X GET https://your-replit-url.repl.co/webhook

# Test health endpoint
curl https://your-replit-url.repl.co/health
```

#### 6.2 Test New Features
```python
# In Replit console
python

# Test imports
from gamified_voice_avatar import GamifiedVoiceAvatarSystem
from voice_avatar_system import VoiceAvatarSystem
from memo_md_mcp_server import MemoMDFilesMCPServer

print("✅ All imports successful!")
exit()
```

### Phase 7: Start Additional Services

#### 7.1 Main App (Already Running)
```bash
# Should auto-restart with new code
# Check Replit logs for any errors
```

#### 7.2 Start MCP Server (New Terminal)
```bash
# Open new Replit Shell tab
cd Memory
python memo_md_mcp_server.py
```

#### 7.3 Optional: Dashboard (Another Terminal)
```bash
# Open another Replit Shell tab
cd Memory
python invitation_dashboard.py --port 8001
```

## Rollback Plan (If Something Goes Wrong)

### Quick Rollback
```bash
# In Replit
git reset --hard HEAD~1  # Undo merge
git push --force origin master

# Or switch to backup
git checkout backup-before-merge
```

### Full Restore
```bash
# Restore database
psql $DATABASE_URL < backup_20250916.sql

# Reinstall original dependencies
pip install -r Memory/requirements.txt.backup
```

## Verification Checklist

After merge, verify:

- [ ] **Existing Features Still Work**
  - [ ] WhatsApp messages received
  - [ ] Azure Speech working
  - [ ] Claude responses working
  - [ ] Database connections OK

- [ ] **New Features Available**
  - [ ] Can import gamification modules
  - [ ] Voice services initialized
  - [ ] Dashboard accessible
  - [ ] API endpoints responding

- [ ] **Environment Variables Set**
  - [ ] ELEVENLABS_API_KEY present
  - [ ] FIRECRAWL_API_KEY present
  - [ ] All original keys still working

- [ ] **No Errors in Logs**
  - [ ] Main app running clean
  - [ ] No import errors
  - [ ] No database errors

## Common Issues & Solutions

### Issue 1: Import Errors
```python
# If you see: ModuleNotFoundError: No module named 'voice_services'
# Solution:
import sys
sys.path.append('/home/runner/YourReplitName/Memory')
```

### Issue 2: Database Connection
```python
# If database errors occur
# Check DATABASE_URL in Replit Secrets
# Ensure it matches format:
postgresql://user:password@host:port/database
```

### Issue 3: Port Conflicts
```bash
# If port 5000 is taken
# Modify in main.py:
uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
```

### Issue 4: Memory Issues
```bash
# If Replit runs out of memory
# Restart the Repl
# Consider upgrading Replit plan
```

## Testing Complete Integration

### 1. Test User Registration
```bash
curl -X POST https://your-replit-url.repl.co/users/register \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "phone_number": "+1234567890"}'
```

### 2. Test Invitation Generation
```bash
curl -X POST https://your-replit-url.repl.co/invitations/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'
```

### 3. Test Voice Avatar
```bash
curl -X POST https://your-replit-url.repl.co/voice/avatar/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "audio_samples": ["base64_audio_data"]}'
```

## Success Indicators

✅ **Merge Successful When:**
1. Main app starts without errors
2. All imports work
3. Database has new tables
4. API endpoints respond
5. WhatsApp still receives messages
6. No error logs in console

## Final Steps

1. **Update Webhook URL** (if changed):
   - Go to Meta Developer Console
   - Update webhook to new Replit URL

2. **Test End-to-End**:
   - Send WhatsApp message
   - Check response
   - Try invitation flow
   - Test voice features

3. **Monitor for 24 Hours**:
   - Check logs regularly
   - Monitor memory usage
   - Watch for any errors

## Support

If issues arise:
1. Check this guide's troubleshooting
2. Review error logs carefully
3. Rollback if critical issues
4. Test in phases, not all at once

---

## Summary

**Safe Merge = Backup → Pull → Test → Verify**

The key is to:
1. Always backup first
2. Merge incrementally
3. Test each component
4. Have a rollback plan
5. Monitor after deployment

---

*Good luck with the merge! The new features will transform your Memory Bot!* 🚀