# ElevenLabs MCP Server Configuration Guide

## Step-by-Step Setup in ElevenLabs Dashboard

### 1. Navigate to MCP Configuration

In your ElevenLabs dashboard, go to:
- **Agents** → **Your Agent** → **Tools** or **MCP Servers**
- Or direct URL: `https://elevenlabs.io/app/agents/[YOUR_AGENT_ID]/mcp`

### 2. Add New MCP Server

Click **"Add MCP Server"** or **"Configure MCP"** and fill in:

#### **Basic Configuration:**

```json
{
  "name": "Memory Bot MCP Server",
  "description": "Provides Memory Bot tools and MD file access",
  "transport": "http",
  "server_url": "http://localhost:3000/mcp"
}
```

**IMPORTANT:** If your MCP server is hosted:
- Local development: `http://localhost:3000/mcp`
- Replit: `https://your-replit-name.repl.co/mcp`
- Production: `https://your-domain.com/mcp`

### 3. Configure Tools

In the **Tools** section, add these tools one by one:

#### **Tool 1: Read MD File**
```json
{
  "name": "read_md_file",
  "description": "Read any MD file to understand documentation",
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path": {
        "type": "string",
        "description": "Path to the MD file"
      },
      "search_query": {
        "type": "string",
        "description": "Optional search within file"
      }
    },
    "required": ["file_path"]
  }
}
```

#### **Tool 2: Search All MD Files**
```json
{
  "name": "search_all_md_files",
  "description": "Search across ALL MD files to find information",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "category": {
        "type": "string",
        "enum": ["voice_system", "gamification", "messaging", "api_documentation", "database", "analysis", "setup_guide", "agent_system", "documentation"],
        "description": "Optional category filter"
      },
      "limit": {
        "type": "integer",
        "default": 5,
        "description": "Max results"
      }
    },
    "required": ["query"]
  }
}
```

#### **Tool 3: Store Memory**
```json
{
  "name": "store_memory",
  "description": "Store a new memory in the user's memory bank",
  "input_schema": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "Memory content to store"
      },
      "category": {
        "type": "string",
        "enum": ["personal", "work", "family", "health", "financial", "ideas", "learning"],
        "description": "Category of the memory"
      },
      "tags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Tags for retrieval"
      },
      "importance": {
        "type": "integer",
        "minimum": 1,
        "maximum": 5,
        "description": "Importance level"
      }
    },
    "required": ["content", "category"]
  }
}
```

#### **Tool 4: Search Memories**
```json
{
  "name": "search_memories",
  "description": "Search and retrieve user memories",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "category": {
        "type": "string",
        "description": "Filter by category"
      },
      "date_range": {
        "type": "object",
        "properties": {
          "start": {"type": "string", "format": "date"},
          "end": {"type": "string", "format": "date"}
        }
      }
    },
    "required": ["query"]
  }
}
```

#### **Tool 5: Manage Contact Slots**
```json
{
  "name": "manage_contact_slots",
  "description": "Manage contact slots for memory sharing",
  "input_schema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["add", "remove", "update", "list"],
        "description": "Action to perform"
      },
      "contact_info": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "phone": {"type": "string"},
          "relationship": {"type": "string"}
        }
      }
    },
    "required": ["action"]
  }
}
```

### 4. Set Approval Mode

In **Security Settings**:

```json
{
  "approval_mode": "fine_grained",
  "auto_approve": [
    "read_md_file",
    "search_all_md_files",
    "search_memories"
  ],
  "require_approval": [
    "store_memory",
    "manage_contact_slots"
  ]
}
```

### 5. Configure Authentication (if needed)

If your MCP server requires authentication:

```json
{
  "auth": {
    "type": "bearer",
    "token": "YOUR_MCP_SERVER_TOKEN"
  }
}
```

Or for API key:

```json
{
  "auth": {
    "type": "api_key",
    "header": "X-API-Key",
    "value": "YOUR_API_KEY"
  }
}
```

### 6. Start Your MCP Server

Before testing, make sure your MCP server is running:

```bash
# In your local terminal or Replit
cd Memory
python memo_md_mcp_server.py

# You should see:
# [OK] MCP Server running on http://localhost:3000
# [INFO] Found XX MD files
```

### 7. Test the Connection

In ElevenLabs dashboard:

1. Click **"Test Connection"**
2. You should see: ✅ Connection successful

If it fails, check:
- Is your MCP server running?
- Is the URL correct?
- Are there any firewall issues?

### 8. Test Individual Tools

Click on each tool and test:

**Test "read_md_file":**
```json
{
  "file_path": "SYSTEM_COMPLETE_SUMMARY.md"
}
```

**Test "search_all_md_files":**
```json
{
  "query": "voice avatar"
}
```

### 9. Update Agent System Prompt

In the **Agent Settings**, update the system prompt to include:

```
You have access to a Memory Bot MCP server with the following capabilities:

1. MD FILE ACCESS: You can read and search all documentation files
2. MEMORY MANAGEMENT: You can store and retrieve user memories
3. CONTACT MANAGEMENT: You can manage contact slots for memory sharing

Available MD files include:
- System documentation
- Voice avatar implementation
- Gamification details
- API documentation
- Setup guides

When users ask questions:
1. First search relevant MD files for accurate information
2. Store important information as memories
3. Retrieve relevant memories when needed

You ARE the Memory Bot expert with complete system knowledge.
```

### 10. Environment Variables for Your MCP Server

Make sure your `memo_md_mcp_server.py` has access to:

```env
# In your .env file
ELEVENLABS_API_KEY=sk_[your_key]
MCP_SERVER_PORT=3000
MCP_BASE_PATHS=C:\Users\dansi\Desktop\Memory\Memory
```

## Troubleshooting

### Issue: "Connection Failed"
```bash
# Check if server is running
curl http://localhost:3000/health

# Should return:
{"status": "healthy", "tools_available": 7}
```

### Issue: "Tool not found"
- Verify tool name matches exactly
- Check JSON schema is valid
- Ensure tool is registered in your MCP server

### Issue: "Permission denied"
- Check approval settings
- Verify authentication if configured
- Check file permissions on MD files

### Issue: "No response from tools"
```python
# Test your MCP server directly
import requests

response = requests.post(
    "http://localhost:3000/mcp",
    json={
        "tool": "list_md_files",
        "parameters": {}
    }
)
print(response.json())
```

## For Production Deployment

1. **Deploy MCP Server**:
   - Host on cloud service (AWS, Google Cloud, etc.)
   - Or use Replit with always-on

2. **Update URL**:
   ```json
   {
     "server_url": "https://your-production-url.com/mcp"
   }
   ```

3. **Add SSL/TLS**:
   - Use HTTPS for production
   - Configure SSL certificate

4. **Add Rate Limiting**:
   ```python
   # In your MCP server
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=get_remote_address)
   ```

## Quick Checklist

- [ ] MCP server is running (`python memo_md_mcp_server.py`)
- [ ] Server URL is correct in ElevenLabs
- [ ] All tools are configured with correct schemas
- [ ] Approval settings are configured
- [ ] Test connection is successful
- [ ] Individual tools are tested
- [ ] Agent system prompt is updated
- [ ] MD files are accessible to the server

## Expected Result

When properly configured, your Memo agent will be able to:
1. Answer any question about Memory Bot by reading MD files
2. Store and retrieve user memories
3. Manage contact slots
4. Understand the entire system architecture
5. Provide context-aware responses based on user permissions

---

**Need Help?**

If you see any error in the ElevenLabs dashboard, please share:
1. The exact error message
2. Which step you're on
3. Your server URL configuration

Then I can provide specific troubleshooting steps!