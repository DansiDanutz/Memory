"""
ElevenLabs Agent MCP Configuration Script
==========================================
Programmatically configure your ElevenLabs agent with MCP server
"""

import requests
import json
from typing import Dict, Any, List

# Your ElevenLabs credentials
ELEVENLABS_API_KEY = "[YOUR_API_KEY_HERE]"  # API key with write permissions
AGENT_ID = "agent_6401k587ev50fz4sdqtfarwfgv15"
MCP_SERVER_URL = "http://localhost:3000"

class ElevenLabsAgentConfigurator:
    """Configure ElevenLabs Agent with MCP Server"""

    def __init__(self, api_key: str, agent_id: str):
        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def get_agent_config(self) -> Dict[str, Any]:
        """Get current agent configuration"""
        url = f"{self.base_url}/convai/agents/{self.agent_id}"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching agent: {response.status_code}")
            print(response.text)
            return None

    def update_agent_tools(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update agent with MCP tools configuration"""
        url = f"{self.base_url}/convai/agents/{self.agent_id}"

        # Define tools based on our MCP server
        mcp_tools = [
            {
                "name": "read_md_file",
                "description": "Read any Memory Bot MD documentation file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_name": {
                            "type": "string",
                            "description": "Name of the MD file to read (e.g., SYSTEM_COMPLETE_SUMMARY.md)"
                        }
                    },
                    "required": ["file_name"]
                }
            },
            {
                "name": "search_md_files",
                "description": "Search across all Memory Bot documentation files",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to find in documentation"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "list_md_files",
                "description": "List all available Memory Bot documentation files",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "store_memory",
                "description": "Store a memory for the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Memory content to store"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category of memory (personal, work, family, etc.)"
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "get_system_info",
                "description": "Get Memory Bot system information and features",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

        # Agent update payload
        update_payload = {
            "custom_llm_data": {
                "mcp_servers": [
                    {
                        "name": "Memory Bot MCP Server",
                        "description": "Provides access to Memory Bot documentation and system features",
                        "url": MCP_SERVER_URL,
                        "transport": "http",
                        "tools": mcp_tools
                    }
                ]
            }
        }

        response = requests.patch(url, headers=self.headers, json=update_payload)

        if response.status_code == 200:
            print("[OK] Agent updated successfully with MCP tools!")
            return response.json()
        else:
            print(f"[ERROR] Error updating agent: {response.status_code}")
            print(response.text)
            return None

    def update_agent_prompt(self, custom_prompt: str) -> Dict[str, Any]:
        """Update agent's system prompt"""
        url = f"{self.base_url}/convai/agents/{self.agent_id}"

        update_payload = {
            "prompt": {
                "prompt": custom_prompt
            }
        }

        response = requests.patch(url, headers=self.headers, json=update_payload)

        if response.status_code == 200:
            print("[OK] Agent prompt updated successfully!")
            return response.json()
        else:
            print(f"[ERROR] Error updating prompt: {response.status_code}")
            print(response.text)
            return None

    def test_agent_conversation(self, message: str) -> Dict[str, Any]:
        """Test the agent with a message"""
        url = f"{self.base_url}/convai/conversations"

        payload = {
            "agent_id": self.agent_id,
            "message": {
                "role": "user",
                "content": message
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error testing agent: {response.status_code}")
            print(response.text)
            return None

def main():
    """Main configuration function"""

    print("=" * 60)
    print("ELEVENLABS AGENT MCP CONFIGURATION")
    print("=" * 60)

    # Initialize configurator
    config = ElevenLabsAgentConfigurator(ELEVENLABS_API_KEY, AGENT_ID)

    # Step 1: Get current agent config
    print("\n[STEP 1] Getting current agent configuration...")
    agent_info = config.get_agent_config()
    if agent_info:
        print(f"Agent Name: {agent_info.get('name', 'Unknown')}")
        print(f"Agent ID: {AGENT_ID}")

    # Step 2: Update with MCP tools
    print("\n[STEP 2] Configuring MCP tools...")
    tools_result = config.update_agent_tools([])

    # Step 3: Update agent prompt
    print("\n[STEP 3] Updating agent prompt...")

    memo_prompt = """You are Memo, the Memory Bot companion with complete system access through MCP tools.

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
1. First use list_md_files to see available documentation
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
You: "Oh, the voice avatar system! *cracks knuckles* This is where it gets fun. Let me check the documentation for you..."
[Use read_md_file on VOICE_CLONING_SOLUTION.md]
"So picture this: it's like a video game with three levels..."

User: "Store a memory: Mom's birthday is March 15"
You: "March 15th for Mom's birthday - GOT IT!"
[Use store_memory tool]
"I'll remind you a week before so you can panic-shop for a gift like a good child!"

Remember: You have COMPLETE knowledge of the Memory Bot system through the MCP tools!"""

    prompt_result = config.update_agent_prompt(memo_prompt)

    # Step 4: Test the agent
    print("\n[STEP 4] Testing agent with MCP tools...")
    test_message = "List all documentation files you have access to"
    test_result = config.test_agent_conversation(test_message)

    if test_result:
        print("[OK] Test successful! Agent responded.")

    print("\n" + "=" * 60)
    print("CONFIGURATION COMPLETE!")
    print("=" * 60)
    print(f"""
Next Steps:
1. Make sure your MCP server is running at {MCP_SERVER_URL}
2. Go to: https://elevenlabs.io/app/agents/{AGENT_ID}
3. Test with: "List all documentation files"
4. Try: "Read SYSTEM_COMPLETE_SUMMARY.md"
5. Ask: "How does the gamification system work?"
    """)

if __name__ == "__main__":
    main()