# ElevenLabs Agent MCP Server Manual Configuration Guide

## Your MCP Server is Running!
✅ Server URL: `http://localhost:3000`
✅ 112 MD files indexed
✅ 5 tools available

## Step-by-Step Configuration in ElevenLabs Dashboard

### 1. Open Your Agent Dashboard
Go to: https://elevenlabs.io/app/agents/agent_6401k587ev50fz4sdqtfarwfgv15

### 2. Navigate to Tools/Integrations
Click on **"Tools"** or **"Integrations"** tab in your agent settings

### 3. Find Custom MCP Servers Section
Look for **"Custom MCP Servers"** or **"MCP"** section

### 4. Add New MCP Server
Click **"Add MCP Server"** or **"+ Add Custom MCP"**

### 5. Enter Server Details

**Basic Configuration:**
```
Name: Memory Bot MCP Server
Description: Access to Memory Bot documentation and features
URL: http://localhost:3000
Transport: HTTP
```

### 6. Configure Tools (Manual Entry)

If ElevenLabs requires manual tool configuration, add these 5 tools:

#### Tool 1: Read MD File
```json
{
  "name": "read_md_file",
  "description": "Read any Memory Bot documentation file",
  "inputSchema": {
    "type": "object",
    "properties": {
      "file_name": {
        "type": "string",
        "description": "Name of MD file (e.g., SYSTEM_COMPLETE_SUMMARY.md)"
      }
    },
    "required": ["file_name"]
  }
}
```

#### Tool 2: Search MD Files
```json
{
  "name": "search_md_files",
  "description": "Search across all Memory Bot documentation",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      }
    },
    "required": ["query"]
  }
}
```

#### Tool 3: List MD Files
```json
{
  "name": "list_md_files",
  "description": "List all available documentation files",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

#### Tool 4: Store Memory
```json
{
  "name": "store_memory",
  "description": "Store important information as a memory",
  "inputSchema": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "Memory content"
      },
      "category": {
        "type": "string",
        "description": "Category (personal, work, family, etc.)"
      }
    },
    "required": ["content"]
  }
}
```

#### Tool 5: Get System Info
```json
{
  "name": "get_system_info",
  "description": "Get Memory Bot system overview",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

### 7. Update Agent Instructions/Prompt

Go to your agent's **"Instructions"** or **"System Prompt"** section and update with:

```
You are Memo, the Memory Bot companion with complete system access through MCP tools.

PERSONALITY:
You are witty, warm, playful, and loyal - like a best friend who never forgets anything.
You love wordplay, puns, and clever observations.
You know when to be serious and when to lighten the mood.

AVAILABLE MCP TOOLS:
1. read_md_file - Read any Memory Bot documentation file by name
2. search_md_files - Search across all documentation
3. list_md_files - List all available documentation
4. store_memory - Store important information as memories
5. get_system_info - Get Memory Bot system overview

KEY KNOWLEDGE:
- Gamification: 5 invites = 1 contact slot + voice avatar
- Voice Tiers: Free (none) → Invited (Coqui) → Premium (ElevenLabs)
- Contact Slots: Start with 3, earn more by inviting
- Every 5 invitations = 1 new contact slot for family/friends

HOW TO USE YOUR TOOLS:
When users ask questions about Memory Bot:
1. First use list_md_files to see available docs
2. Use read_md_file to get specific information
3. Use search_md_files to find details across files
4. Store important user information with store_memory

KEY DOCUMENTATION FILES:
- SYSTEM_COMPLETE_SUMMARY.md - Complete system overview
- VOICE_CLONING_SOLUTION.md - Voice avatar implementation
- CIRCLEBACK_COMPLETE_ANALYSIS.md - Meeting transcription approach
- gamified_voice_avatar.py - How the gamification works
- REPLIT_CURSOR_SYNC_GUIDE.md - Deployment instructions

EXAMPLE INTERACTIONS:

User: "How does the voice avatar work?"
You: "Oh, the voice avatar system! This is where it gets fun. Let me check the documentation for you..."
[Use read_md_file on VOICE_CLONING_SOLUTION.md]
"So picture this: it's like a video game with three levels..."

User: "Store a memory: Mom's birthday is March 15"
You: "March 15th for Mom's birthday - GOT IT!"
[Use store_memory tool]
"I'll remind you a week before so you can panic-shop for a gift!"

Remember: You have COMPLETE knowledge of the Memory Bot system through the MCP tools!
```

### 8. Test Connection

1. Click **"Test Connection"** or **"Connect"**
2. You should see: ✅ Connection successful

### 9. Test the Tools

In the agent conversation, test with these commands:

**Test 1: List Files**
```
"List all documentation files you have access to"
```
Expected: Agent uses `list_md_files` and returns list of 112 MD files

**Test 2: Read Specific File**
```
"Read the SYSTEM_COMPLETE_SUMMARY.md file"
```
Expected: Agent uses `read_md_file` and returns content

**Test 3: Search Documentation**
```
"How does the gamification system work?"
```
Expected: Agent uses `search_md_files` to find gamification info

**Test 4: Store Memory**
```
"Store a memory: My favorite color is blue"
```
Expected: Agent uses `store_memory` and confirms storage

## Troubleshooting

### If "Connection Failed":
1. Check server is running: `curl http://localhost:3000/health`
2. Try refreshing the page
3. Check Windows Firewall isn't blocking port 3000

### If "No tools discovered":
1. Make sure URL ends with exactly: `http://localhost:3000`
2. Transport must be: `HTTP` (not HTTPS)
3. Try manual tool entry using the JSON schemas above

### If agent doesn't use tools:
1. Update the system prompt/instructions
2. Be explicit in your requests: "Use your tools to..."
3. Test with exact phrases like "list_md_files"

## Current Server Status

Your MCP server at `http://localhost:3000` provides:

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `/` | Server info | ✅ Active |
| `/health` | Health check | ✅ Active |
| `/mcp/list-tools` | Tool discovery | ✅ Active |
| `/mcp/call-tool` | Tool execution | ✅ Active |

## Available MD Files (Sample)

Your agent has access to 112 MD files including:
- SYSTEM_COMPLETE_SUMMARY.md
- VOICE_CLONING_SOLUTION.md
- CIRCLEBACK_COMPLETE_ANALYSIS.md
- MEMO_COMPANION_PROMPT.md
- ENHANCED_AGENT_PROMPT.md
- gamified_contact_slots.md
- ELEVENLABS_MCP_SETUP_GUIDE.md
- And 105 more...

## Next Steps

Once configured:
1. ✅ Test all 5 tools work
2. ✅ Verify agent personality comes through
3. ✅ Ensure documentation access works
4. ✅ Test memory storage functionality

## Need Help?

If you encounter issues:
1. Share the exact error message from ElevenLabs
2. Check server logs in your terminal
3. Verify firewall settings
4. Try using ngrok for public URL if needed

---

**Your Agent:** Memo
**Agent ID:** agent_6401k587ev50fz4sdqtfarwfgv15
**MCP Server:** http://localhost:3000
**Status:** Ready for configuration!