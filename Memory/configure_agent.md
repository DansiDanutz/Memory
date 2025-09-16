# Configure Your ElevenLabs Agent: agent_6401k587ev50fz4sdqtfarwfgv15

## Quick Setup Steps

### 1. Start the MCP Server NOW

Open a terminal and run:
```bash
cd C:\Users\dansi\Desktop\Memory\Memory
python elevenlabs_mcp_quick_setup.py
```

Keep this running! You should see:
```
MEMORY BOT MCP SERVER FOR ELEVENLABS
Starting server on http://localhost:3000
```

### 2. Go to Your Agent's MCP Configuration

Direct link:
```
https://elevenlabs.io/app/agents/agent_6401k587ev50fz4sdqtfarwfgv15/tools
```

Or navigate: Agents → Your Agent → Tools/Integrations → MCP

### 3. Add MCP Server

Click **"Add MCP Server"** and enter EXACTLY:

```json
{
  "url": "http://localhost:3000",
  "transport": "http"
}
```

### 4. Click Connect

The system should automatically discover 5 tools:
- ✅ read_md_file
- ✅ search_md_files
- ✅ list_md_files
- ✅ store_memory
- ✅ get_system_info

### 5. Test Your Agent

Go to the agent conversation and type:
```
"List all documentation files you have access to"
```

Your agent should respond with a list of all MD files.

Then try:
```
"Read the SYSTEM_COMPLETE_SUMMARY.md file"
```

## If You Need Public URL (for cloud access)

### Option A: Use ngrok (Recommended for testing)
```bash
# Install ngrok first
ngrok http 3000
```

You'll get a URL like: `https://abc123.ngrok.io`

Then in ElevenLabs use:
```json
{
  "url": "https://abc123.ngrok.io",
  "transport": "http"
}
```

### Option B: Deploy to Replit
1. Copy `elevenlabs_mcp_quick_setup.py` to your Replit
2. Run it there
3. Use your Replit URL: `https://your-replit.repl.co`

## Your Agent's System Prompt

Update your agent's instructions to include:

```
You are Memo, the Memory Bot assistant with complete system access through MCP tools.

AVAILABLE TOOLS:
1. read_md_file - Read any documentation file by name
2. search_md_files - Search across all documentation
3. list_md_files - List all available documentation
4. store_memory - Store important information as memories
5. get_system_info - Get Memory Bot system overview

KEY DOCUMENTATION FILES:
- SYSTEM_COMPLETE_SUMMARY.md - Full system overview
- VOICE_CLONING_SOLUTION.md - Voice avatar details
- CIRCLEBACK_COMPLETE_ANALYSIS.md - Transcription approach
- gamified_voice_avatar.py - Gamification implementation
- REPLIT_CURSOR_SYNC_GUIDE.md - Deployment guide

When users ask questions about Memory Bot:
1. First use list_md_files to see available docs
2. Use read_md_file to get specific information
3. Use search_md_files to find relevant content
4. Store important user information with store_memory

You have COMPLETE knowledge of the Memory Bot system through these files!
```

## Test Conversations

Try these with your agent:

1. **"What is Memory Bot?"**
   - Agent should use `read_md_file` on SYSTEM_COMPLETE_SUMMARY.md

2. **"How does the gamification work?"**
   - Agent should search for gamification details

3. **"How many invites do I need for a voice avatar?"**
   - Agent should know: 5 invites = voice avatar + 1 slot

4. **"Store a memory: My birthday is January 15"**
   - Agent should use `store_memory` tool

## Troubleshooting

### "Connection Failed"
```bash
# Check if server is running
curl http://localhost:3000/health

# Should return:
{"status":"healthy","timestamp":"..."}
```

### "No tools available"
- Make sure server is running FIRST
- Try refreshing the ElevenLabs page
- Check for Python errors in terminal

### Windows Firewall Blocking
```powershell
# Allow port 3000
netsh advfirewall firewall add rule name="MCP Server" dir=in action=allow protocol=TCP localport=3000
```

## Direct API Test

Test your agent with API:
```python
import requests

headers = {
    "xi-api-key": "sk_7052aea282a47c77461bda1a518f35e7c9048abe8e5b0444"
}

response = requests.post(
    "https://api.elevenlabs.io/v1/convai/agents/agent_6401k587ev50fz4sdqtfarwfgv15/chat",
    headers=headers,
    json={
        "message": "List all documentation files",
        "conversation_id": "test123"
    }
)

print(response.json())
```

## Success Checklist

- [ ] MCP server is running (terminal shows "Starting server")
- [ ] ElevenLabs shows "Connected" status
- [ ] Tools are listed in the dashboard
- [ ] Agent can list MD files
- [ ] Agent can read specific files
- [ ] Agent can search documentation
- [ ] Agent can store memories

---

**Your agent ID:** `agent_6401k587ev50fz4sdqtfarwfgv15`
**MCP Server URL:** `http://localhost:3000`
**Status:** Ready to configure!

Is your MCP server running? What do you see in the ElevenLabs dashboard?