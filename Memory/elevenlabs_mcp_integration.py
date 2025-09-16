"""
ElevenLabs MCP Integration for Memory Bot
=========================================
Connects Memory Bot to ElevenLabs Conversational AI via Model Context Protocol
Your agent already understands the Memo app requirements from the prompt
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class MemoryBotMCPConfig:
    """Configuration for Memory Bot MCP server"""
    server_url: str = "http://localhost:3000"  # Your MCP server
    agent_id: str = ""  # Your ElevenLabs agent ID
    api_key: str = ""

    # Memory Bot specific settings
    enable_voice_memory: bool = True
    enable_whatsapp_sync: bool = True
    enable_contact_sharing: bool = True
    enable_invitation_system: bool = True


class MemoryBotMCPServer:
    """
    MCP Server for Memory Bot
    Provides tools and context to ElevenLabs agent
    """

    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.tools = self._define_memory_tools()
        self.active_sessions = {}

        print("[OK] Memory Bot MCP Server initialized")
        print("[INFO] Agent knows your Memo app requirements from prompt")

    def _define_memory_tools(self) -> List[Dict[str, Any]]:
        """
        Define Memory Bot specific tools for the agent
        These match what you described in the agent prompt
        """
        return [
            {
                "name": "store_memory",
                "description": "Store a new memory in the user's personal memory bank",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The memory content to store"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["personal", "work", "family", "health", "financial", "ideas", "learning"],
                            "description": "Category of the memory"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for easier retrieval"
                        },
                        "importance": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                            "description": "Importance level (1-5)"
                        },
                        "reminder_date": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Optional reminder date"
                        }
                    },
                    "required": ["content", "category"]
                }
            },
            {
                "name": "search_memories",
                "description": "Search and retrieve memories based on query",
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
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "set_reminder",
                "description": "Set a reminder for the user",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Reminder message"
                        },
                        "datetime": {
                            "type": "string",
                            "format": "date-time",
                            "description": "When to remind"
                        },
                        "recurring": {
                            "type": "string",
                            "enum": ["none", "daily", "weekly", "monthly", "yearly"],
                            "description": "Recurrence pattern"
                        },
                        "notification_channels": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["whatsapp", "voice", "email"]
                            }
                        }
                    },
                    "required": ["message", "datetime"]
                }
            },
            {
                "name": "share_memory_with_contact",
                "description": "Share a memory with a contact (family/friend)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "ID of memory to share"
                        },
                        "contact_name": {
                            "type": "string",
                            "description": "Name of contact to share with"
                        },
                        "permission": {
                            "type": "string",
                            "enum": ["view", "edit"],
                            "description": "Permission level"
                        }
                    },
                    "required": ["memory_id", "contact_name"]
                }
            },
            {
                "name": "analyze_memory_patterns",
                "description": "Analyze patterns in user's memories",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {
                            "type": "string",
                            "enum": ["mood", "productivity", "health", "relationships", "habits"],
                            "description": "Type of analysis"
                        },
                        "time_period": {
                            "type": "string",
                            "enum": ["week", "month", "quarter", "year"],
                            "description": "Time period to analyze"
                        }
                    },
                    "required": ["analysis_type"]
                }
            },
            {
                "name": "create_memory_summary",
                "description": "Create a summary of memories for a time period",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Summary period"
                        },
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Categories to include"
                        },
                        "send_to_contacts": {
                            "type": "boolean",
                            "description": "Share with selected contacts"
                        }
                    },
                    "required": ["period"]
                }
            },
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
            },
            {
                "name": "check_invitation_progress",
                "description": "Check user's invitation progress for rewards",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "include_details": {
                            "type": "boolean",
                            "description": "Include detailed breakdown"
                        }
                    }
                }
            },
            {
                "name": "send_whatsapp_memory",
                "description": "Send a memory via WhatsApp",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "memory_content": {
                            "type": "string",
                            "description": "Memory to send"
                        },
                        "recipient": {
                            "type": "string",
                            "description": "WhatsApp contact or group"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["text", "voice", "image"],
                            "description": "Format to send"
                        }
                    },
                    "required": ["memory_content"]
                }
            },
            {
                "name": "transcribe_voice_memory",
                "description": "Transcribe a voice message into a memory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "audio_url": {
                            "type": "string",
                            "description": "URL of audio to transcribe"
                        },
                        "auto_categorize": {
                            "type": "boolean",
                            "description": "Automatically categorize the memory"
                        }
                    },
                    "required": ["audio_url"]
                }
            }
        ]

    async def handle_tool_request(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle tool requests from ElevenLabs agent

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            user_context: User context including ID, memories, etc.

        Returns:
            Tool execution result
        """
        user_id = user_context.get("user_id")

        try:
            if tool_name == "store_memory":
                return await self._store_memory(user_id, parameters)

            elif tool_name == "search_memories":
                return await self._search_memories(user_id, parameters)

            elif tool_name == "set_reminder":
                return await self._set_reminder(user_id, parameters)

            elif tool_name == "share_memory_with_contact":
                return await self._share_memory(user_id, parameters)

            elif tool_name == "analyze_memory_patterns":
                return await self._analyze_patterns(user_id, parameters)

            elif tool_name == "create_memory_summary":
                return await self._create_summary(user_id, parameters)

            elif tool_name == "manage_contact_slots":
                return await self._manage_contacts(user_id, parameters)

            elif tool_name == "check_invitation_progress":
                return await self._check_invitations(user_id, parameters)

            elif tool_name == "send_whatsapp_memory":
                return await self._send_whatsapp(user_id, parameters)

            elif tool_name == "transcribe_voice_memory":
                return await self._transcribe_voice(user_id, parameters)

            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _store_memory(self, user_id: str, params: Dict) -> Dict:
        """Store a new memory"""
        # Connect to your database
        memory = {
            "id": f"mem_{datetime.now().timestamp()}",
            "user_id": user_id,
            "content": params["content"],
            "category": params["category"],
            "tags": params.get("tags", []),
            "importance": params.get("importance", 3),
            "created_at": datetime.now().isoformat(),
            "reminder_date": params.get("reminder_date")
        }

        # Store in database (implementation depends on your setup)
        # await database.store_memory(memory)

        return {
            "success": True,
            "memory_id": memory["id"],
            "message": f"Memory stored in {params['category']} category"
        }

    async def _search_memories(self, user_id: str, params: Dict) -> Dict:
        """Search user's memories"""
        # Search implementation
        # results = await database.search_memories(user_id, params["query"])

        # Mock results for demo
        results = [
            {
                "id": "mem_1",
                "content": "Project deadline next Friday",
                "category": "work",
                "date": "2024-01-20",
                "relevance": 0.95
            },
            {
                "id": "mem_2",
                "content": "Mom's birthday on January 25th",
                "category": "family",
                "date": "2024-01-15",
                "relevance": 0.85
            }
        ]

        return {
            "success": True,
            "count": len(results),
            "memories": results
        }

    async def _set_reminder(self, user_id: str, params: Dict) -> Dict:
        """Set a reminder"""
        reminder = {
            "id": f"rem_{datetime.now().timestamp()}",
            "user_id": user_id,
            "message": params["message"],
            "datetime": params["datetime"],
            "recurring": params.get("recurring", "none"),
            "channels": params.get("notification_channels", ["whatsapp"])
        }

        # Schedule reminder
        # await scheduler.add_reminder(reminder)

        return {
            "success": True,
            "reminder_id": reminder["id"],
            "scheduled_for": params["datetime"],
            "message": "Reminder set successfully"
        }

    async def _share_memory(self, user_id: str, params: Dict) -> Dict:
        """Share memory with contact"""
        # Implementation for sharing
        return {
            "success": True,
            "shared_with": params["contact_name"],
            "permission": params.get("permission", "view"),
            "message": f"Memory shared with {params['contact_name']}"
        }

    async def _analyze_patterns(self, user_id: str, params: Dict) -> Dict:
        """Analyze memory patterns"""
        analysis_type = params["analysis_type"]
        period = params.get("time_period", "month")

        # Mock analysis results
        insights = {
            "mood": {
                "trend": "improving",
                "positive_days": 18,
                "negative_days": 5,
                "neutral_days": 7,
                "recommendation": "Your mood has been improving! Keep up the positive activities."
            },
            "productivity": {
                "peak_hours": "9-11 AM",
                "tasks_completed": 45,
                "average_per_day": 1.5,
                "recommendation": "You're most productive in the morning. Schedule important tasks then."
            }
        }

        return {
            "success": True,
            "analysis_type": analysis_type,
            "period": period,
            "insights": insights.get(analysis_type, {})
        }

    async def _create_summary(self, user_id: str, params: Dict) -> Dict:
        """Create memory summary"""
        period = params["period"]

        summary = {
            "period": period,
            "total_memories": 42,
            "top_categories": ["work", "family", "health"],
            "key_events": [
                "Completed Project X",
                "Family reunion planning",
                "Started new exercise routine"
            ],
            "upcoming_reminders": 5
        }

        return {
            "success": True,
            "summary": summary,
            "message": f"{period.capitalize()} summary created"
        }

    async def _manage_contacts(self, user_id: str, params: Dict) -> Dict:
        """Manage contact slots"""
        action = params["action"]

        if action == "list":
            contacts = [
                {"name": "Mom", "relationship": "family", "slot": 1},
                {"name": "Dad", "relationship": "family", "slot": 2},
                {"name": "Best Friend", "relationship": "friend", "slot": 3}
            ]
            return {
                "success": True,
                "contacts": contacts,
                "available_slots": 2,
                "total_slots": 5
            }

        return {
            "success": True,
            "action": action,
            "message": f"Contact {action} completed"
        }

    async def _check_invitations(self, user_id: str, params: Dict) -> Dict:
        """Check invitation progress"""
        return {
            "success": True,
            "invitations_sent": 3,
            "successful_invites": 2,
            "slots_earned": 0,
            "next_reward_in": 3,
            "message": "Invite 3 more friends to earn a contact slot!"
        }

    async def _send_whatsapp(self, user_id: str, params: Dict) -> Dict:
        """Send memory via WhatsApp"""
        # WhatsApp integration
        return {
            "success": True,
            "sent_to": params.get("recipient", "self"),
            "format": params.get("format", "text"),
            "message": "Memory sent via WhatsApp"
        }

    async def _transcribe_voice(self, user_id: str, params: Dict) -> Dict:
        """Transcribe voice to memory"""
        # Use Azure Speech or ElevenLabs transcription
        return {
            "success": True,
            "transcription": "This is the transcribed text from voice",
            "auto_categorized": params.get("auto_categorize", False),
            "category": "personal" if params.get("auto_categorize") else None
        }


class ElevenLabsMCPConnector:
    """
    Connects Memory Bot to ElevenLabs agent via MCP
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.mcp_server = MemoryBotMCPServer()

        print(f"[OK] Connected to ElevenLabs agent: {agent_id}")
        print("[INFO] Agent understands Memo app from your prompt")

    async def configure_agent_with_mcp(self) -> Dict[str, Any]:
        """
        Configure ElevenLabs agent with Memory Bot MCP tools
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }

            payload = {
                "agent_id": self.agent_id,
                "mcp_configuration": {
                    "server_url": "http://localhost:3000/mcp",
                    "transport": "http",
                    "tools": self.mcp_server.tools,
                    "approval_mode": "fine_grained",  # Control which tools need approval
                    "auto_approve": [
                        "search_memories",
                        "check_invitation_progress"
                    ],
                    "require_approval": [
                        "share_memory_with_contact",
                        "send_whatsapp_memory"
                    ]
                }
            }

            async with session.post(
                f"https://api.elevenlabs.io/v1/convai/agents/{self.agent_id}/mcp",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    return {
                        "success": True,
                        "message": "MCP tools configured for agent",
                        "tools_count": len(self.mcp_server.tools)
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": error
                    }

    async def start_mcp_server(self, port: int = 3000):
        """
        Start the MCP server for tool requests
        """
        from aiohttp import web

        app = web.Application()

        async def handle_mcp_request(request):
            """Handle MCP tool requests from ElevenLabs agent"""
            data = await request.json()

            tool_name = data.get("tool")
            parameters = data.get("parameters", {})
            user_context = data.get("context", {})

            result = await self.mcp_server.handle_tool_request(
                tool_name,
                parameters,
                user_context
            )

            return web.json_response(result)

        async def handle_health(request):
            """Health check endpoint"""
            return web.json_response({
                "status": "healthy",
                "tools_available": len(self.mcp_server.tools),
                "agent_id": self.agent_id
            })

        # Routes
        app.router.add_post('/mcp', handle_mcp_request)
        app.router.add_get('/health', handle_health)

        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()

        print(f"[OK] MCP Server running on http://localhost:{port}")
        print(f"[INFO] ElevenLabs agent can now use Memory Bot tools")

        # Keep server running
        while True:
            await asyncio.sleep(3600)


# Demo usage
async def demo():
    """Demo the MCP integration"""
    print("=" * 60)
    print("MEMORY BOT + ELEVENLABS MCP INTEGRATION")
    print("=" * 60)

    # Your ElevenLabs agent ID (get from dashboard)
    AGENT_ID = "agt_xxxxxxxxxxxxx"  # Replace with your agent ID

    # Initialize connector
    connector = ElevenLabsMCPConnector(AGENT_ID)

    # Configure agent with MCP tools
    print("\n1. Configuring agent with Memory Bot tools...")
    result = await connector.configure_agent_with_mcp()
    print(f"Configuration: {result}")

    # Start MCP server
    print("\n2. Starting MCP server...")
    print("Your ElevenLabs agent can now:")
    print("  - Store and retrieve memories")
    print("  - Set reminders")
    print("  - Share memories with contacts")
    print("  - Analyze memory patterns")
    print("  - Send via WhatsApp")
    print("  - Manage contact slots")
    print("\nThe agent already knows what Memo app does from your prompt!")

    # Start server (this will run indefinitely)
    await connector.start_mcp_server()


if __name__ == "__main__":
    asyncio.run(demo())