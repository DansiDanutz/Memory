"""
ElevenLabs Conversational AI Agent Integration
==============================================
Uses ElevenLabs' powerful Agent API for natural conversations
Not just voice cloning - full conversational AI with memory context
"""

import os
import json
import asyncio
import aiohttp
import websockets
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass
import base64
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AgentConfig:
    """Configuration for ElevenLabs Agent"""
    agent_id: Optional[str] = None
    name: str = "Memory Assistant"
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice by default
    language: str = "en"

    # Agent personality and behavior
    first_message: str = "Hello! I'm your personal memory assistant. How can I help you today?"
    system_prompt: str = """You are a helpful memory assistant with perfect recall.
    You help users remember important information, take notes, and never forget anything.
    You're friendly, professional, and always eager to help."""

    # Voice settings
    stability: float = 0.5
    similarity_boost: float = 0.8
    style: float = 0.0
    use_speaker_boost: bool = True

    # Conversation settings
    temperature: float = 0.7
    max_tokens: int = 150
    enable_interruptions: bool = True
    ambient_sound: Optional[str] = None  # office, restaurant, etc.

    # Memory integration
    enable_memory_context: bool = True
    memory_window: int = 10  # Last N memories to include as context


class ElevenLabsAgent:
    """
    ElevenLabs Conversational AI Agent
    This is the amazing agent experience with real-time conversation
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found")

        self.base_url = "https://api.elevenlabs.io/v1"
        self.ws_url = "wss://api.elevenlabs.io/v1/convai"

        # Agent configurations per user
        self.user_agents: Dict[str, AgentConfig] = {}
        self.active_conversations: Dict[str, Any] = {}

        print("[OK] ElevenLabs Agent initialized")

    async def create_agent(
        self,
        user_id: str,
        name: Optional[str] = None,
        voice_id: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a custom conversational agent for a user

        Args:
            user_id: User identifier
            name: Agent name
            voice_id: ElevenLabs voice ID to use
            custom_prompt: Custom system prompt for personality

        Returns:
            Agent creation result
        """
        try:
            # Create agent configuration
            config = AgentConfig(
                name=name or f"{user_id}'s Memory Assistant",
                voice_id=voice_id or "21m00Tcm4TlvDq8ikWAM",  # Rachel
                system_prompt=custom_prompt or self._generate_memory_prompt(user_id)
            )

            # Create agent via API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                }

                payload = {
                    "name": config.name,
                    "conversation_config": {
                        "agent": {
                            "prompt": {
                                "prompt": config.system_prompt,
                                "llm": "gpt-4o-mini",  # or gpt-4o for better quality
                                "temperature": config.temperature,
                                "max_tokens": config.max_tokens
                            },
                            "first_message": config.first_message,
                            "language": config.language
                        },
                        "tts": {
                            "voice_id": config.voice_id,
                            "model_id": "eleven_turbo_v2_5",
                            "voice_settings": {
                                "stability": config.stability,
                                "similarity_boost": config.similarity_boost,
                                "style": config.style,
                                "use_speaker_boost": config.use_speaker_boost
                            }
                        },
                        "stt": {
                            "language": config.language,
                            "model": "whisper"
                        }
                    },
                    "platform_settings": {
                        "auth": {
                            "mode": "public"  # or "private" with auth
                        },
                        "tools": [],  # Can add custom tools/functions
                        "enable_transcripts": True
                    }
                }

                async with session.post(
                    f"{self.base_url}/convai/agents/create",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        config.agent_id = result.get("agent_id")
                        self.user_agents[user_id] = config

                        return {
                            "success": True,
                            "agent_id": config.agent_id,
                            "name": config.name,
                            "voice_id": config.voice_id,
                            "message": "Agent created successfully!"
                        }
                    else:
                        error = await response.text()
                        return {
                            "success": False,
                            "error": f"Failed to create agent: {error}"
                        }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def start_conversation(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        memory_context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Start a conversation with the agent

        Args:
            user_id: User identifier
            agent_id: Optional specific agent ID
            memory_context: User's memory context to include

        Returns:
            Conversation session details
        """
        try:
            # Get or create agent
            if agent_id:
                agent = agent_id
            elif user_id in self.user_agents:
                agent = self.user_agents[user_id].agent_id
            else:
                # Create default agent for user
                result = await self.create_agent(user_id)
                if not result["success"]:
                    return result
                agent = result["agent_id"]

            # Generate conversation ID
            conversation_id = f"conv_{user_id}_{datetime.now().timestamp()}"

            # Prepare WebSocket connection URL with signed URL
            signed_url = await self._get_signed_url(agent)

            # Store conversation details
            self.active_conversations[conversation_id] = {
                "user_id": user_id,
                "agent_id": agent,
                "started_at": datetime.now(),
                "memory_context": memory_context or [],
                "websocket_url": signed_url
            }

            return {
                "success": True,
                "conversation_id": conversation_id,
                "agent_id": agent,
                "websocket_url": signed_url,
                "message": "Conversation started! Connect via WebSocket for real-time chat."
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_signed_url(self, agent_id: str) -> str:
        """Get signed WebSocket URL for agent conversation"""
        async with aiohttp.ClientSession() as session:
            headers = {"xi-api-key": self.api_key}

            async with session.get(
                f"{self.base_url}/convai/conversation/get_signed_url",
                headers=headers,
                params={"agent_id": agent_id}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["signed_url"]
                else:
                    raise Exception("Failed to get signed URL")

    async def handle_conversation(
        self,
        conversation_id: str,
        audio_stream: Optional[bytes] = None,
        text_input: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle real-time conversation with the agent

        Args:
            conversation_id: Active conversation ID
            audio_stream: Audio input from user
            text_input: Text input from user

        Yields:
            Response chunks from agent
        """
        if conversation_id not in self.active_conversations:
            yield {
                "error": "Conversation not found"
            }
            return

        conv = self.active_conversations[conversation_id]

        try:
            # Connect to WebSocket
            async with websockets.connect(conv["websocket_url"]) as websocket:
                # Send initial configuration
                config_message = {
                    "type": "conversation_initiation",
                    "conversation_config": {
                        "enable_transcripts": True,
                        "enable_analysis": True
                    }
                }
                await websocket.send(json.dumps(config_message))

                # Include memory context if available
                if conv["memory_context"]:
                    context_message = {
                        "type": "add_context",
                        "context": self._format_memory_context(conv["memory_context"])
                    }
                    await websocket.send(json.dumps(context_message))

                # Send user input
                if audio_stream:
                    # Send audio chunks
                    audio_message = {
                        "type": "audio_input",
                        "audio": base64.b64encode(audio_stream).decode('utf-8')
                    }
                    await websocket.send(json.dumps(audio_message))
                elif text_input:
                    # Send text input
                    text_message = {
                        "type": "text_input",
                        "text": text_input
                    }
                    await websocket.send(json.dumps(text_message))

                # Receive and yield responses
                async for message in websocket:
                    data = json.loads(message)

                    if data["type"] == "audio_output":
                        yield {
                            "type": "audio",
                            "audio": base64.b64decode(data["audio"]),
                            "format": "mp3"
                        }
                    elif data["type"] == "transcript":
                        yield {
                            "type": "transcript",
                            "role": data["role"],
                            "text": data["text"],
                            "timestamp": data.get("timestamp")
                        }
                    elif data["type"] == "analysis":
                        yield {
                            "type": "analysis",
                            "sentiment": data.get("sentiment"),
                            "topics": data.get("topics"),
                            "action_items": data.get("action_items")
                        }
                    elif data["type"] == "error":
                        yield {
                            "type": "error",
                            "error": data["message"]
                        }
                        break
                    elif data["type"] == "conversation_ended":
                        yield {
                            "type": "end",
                            "message": "Conversation ended"
                        }
                        break

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e)
            }

    async def create_memory_aware_agent(
        self,
        user_id: str,
        user_memories: List[Dict[str, Any]],
        personality: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an agent that's aware of user's memories

        Args:
            user_id: User identifier
            user_memories: User's stored memories
            personality: Optional personality traits

        Returns:
            Memory-aware agent details
        """
        # Generate a prompt that includes memory context
        memory_summary = self._summarize_memories(user_memories)

        custom_prompt = f"""
        You are a personal memory assistant with access to the user's stored memories.

        USER'S MEMORY CONTEXT:
        {memory_summary}

        Your role:
        1. Help recall information from their memories
        2. Connect new information with existing memories
        3. Suggest relevant memories when appropriate
        4. Never forget anything they've told you
        5. Be proactive in reminding them of important things

        Personality: {personality or 'Helpful, professional, and attentive'}

        Always reference their memories naturally in conversation when relevant.
        """

        return await self.create_agent(
            user_id=user_id,
            name=f"{user_id}'s Memory Assistant",
            custom_prompt=custom_prompt
        )

    async def update_agent_knowledge(
        self,
        user_id: str,
        new_memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update agent with new memories

        Args:
            user_id: User identifier
            new_memories: New memories to add

        Returns:
            Update result
        """
        if user_id not in self.user_agents:
            return {
                "success": False,
                "error": "Agent not found for user"
            }

        # In a real implementation, this would update the agent's knowledge base
        # For now, we'll store it for the next conversation
        config = self.user_agents[user_id]

        # Update system prompt with new information
        memory_text = self._format_memories_for_prompt(new_memories)
        config.system_prompt += f"\n\nNEW MEMORIES:\n{memory_text}"

        return {
            "success": True,
            "memories_added": len(new_memories),
            "message": "Agent knowledge updated with new memories"
        }

    def _generate_memory_prompt(self, user_id: str) -> str:
        """Generate a personalized system prompt for memory assistant"""
        return f"""
        You are {user_id}'s personal memory assistant. Your capabilities:

        1. PERFECT RECALL: Never forget anything shared with you
        2. CONTEXTUAL AWARENESS: Connect related memories and information
        3. PROACTIVE REMINDERS: Remind about important dates, tasks, and information
        4. NATURAL CONVERSATION: Speak naturally, like a helpful friend
        5. MEMORY SEARCH: Help find specific memories or information

        Guidelines:
        - Be warm and personable, but professional
        - Reference past conversations naturally
        - Suggest relevant memories when helpful
        - Ask clarifying questions to better store memories
        - Protect user privacy - never share their memories

        Start each conversation by acknowledging any previous interactions.
        """

    def _format_memory_context(self, memories: List[Dict]) -> str:
        """Format memories for agent context"""
        if not memories:
            return "No previous memories."

        context = "Previous memories:\n"
        for i, memory in enumerate(memories[-10:], 1):  # Last 10 memories
            context += f"{i}. [{memory.get('date', 'Unknown date')}] {memory.get('content', '')}\n"

        return context

    def _summarize_memories(self, memories: List[Dict]) -> str:
        """Summarize memories for agent prompt"""
        if not memories:
            return "No memories stored yet."

        summary = f"User has {len(memories)} stored memories including:\n"

        # Categorize memories
        categories = {}
        for memory in memories:
            category = memory.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append(memory.get("title", "Untitled"))

        for category, titles in categories.items():
            summary += f"- {category.capitalize()}: {len(titles)} memories\n"

        # Recent memories
        recent = memories[-5:] if len(memories) >= 5 else memories
        summary += "\nMost recent memories:\n"
        for memory in recent:
            summary += f"- {memory.get('title', 'Untitled')}: {memory.get('summary', '')[:100]}...\n"

        return summary

    def _format_memories_for_prompt(self, memories: List[Dict]) -> str:
        """Format memories for inclusion in prompt"""
        formatted = ""
        for memory in memories:
            formatted += f"""
            Date: {memory.get('date', 'Unknown')}
            Category: {memory.get('category', 'General')}
            Content: {memory.get('content', '')}
            Tags: {', '.join(memory.get('tags', []))}
            ---
            """
        return formatted

    async def get_agent_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get usage analytics for user's agent"""
        # This would connect to ElevenLabs analytics API
        return {
            "user_id": user_id,
            "total_conversations": 0,
            "total_duration_minutes": 0,
            "character_count": 0,
            "last_conversation": None
        }


class ElevenLabsConversationWebSocket:
    """
    WebSocket handler for real-time conversations
    This handles the actual conversation flow
    """

    def __init__(self, agent: ElevenLabsAgent):
        self.agent = agent
        self.active_sessions = {}

    async def handle_websocket(
        self,
        websocket,
        path,
        user_id: str,
        conversation_id: str
    ):
        """
        Handle WebSocket connection for conversation

        Args:
            websocket: WebSocket connection
            path: Connection path
            user_id: User identifier
            conversation_id: Conversation ID
        """
        print(f"[WS] New connection: {user_id} - {conversation_id}")

        try:
            # Register session
            self.active_sessions[conversation_id] = {
                "websocket": websocket,
                "user_id": user_id,
                "started_at": datetime.now()
            }

            # Handle messages
            async for message in websocket:
                data = json.loads(message)

                if data["type"] == "audio":
                    # Process audio input
                    audio_data = base64.b64decode(data["audio"])

                    # Send to ElevenLabs agent
                    async for response in self.agent.handle_conversation(
                        conversation_id,
                        audio_stream=audio_data
                    ):
                        await websocket.send(json.dumps(response))

                elif data["type"] == "text":
                    # Process text input
                    async for response in self.agent.handle_conversation(
                        conversation_id,
                        text_input=data["text"]
                    ):
                        await websocket.send(json.dumps(response))

                elif data["type"] == "end":
                    # End conversation
                    await websocket.send(json.dumps({
                        "type": "end",
                        "message": "Thank you for using Memory Assistant!"
                    }))
                    break

        except websockets.exceptions.ConnectionClosed:
            print(f"[WS] Connection closed: {conversation_id}")
        except Exception as e:
            print(f"[WS] Error: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "error": str(e)
            }))
        finally:
            # Clean up session
            if conversation_id in self.active_sessions:
                del self.active_sessions[conversation_id]


# Demo usage
async def demo():
    """Demonstrate ElevenLabs Agent"""
    print("=" * 60)
    print("ELEVENLABS CONVERSATIONAL AGENT DEMO")
    print("=" * 60)

    agent = ElevenLabsAgent()

    # Create a memory-aware agent
    print("\n1. Creating memory-aware agent...")

    # Sample user memories
    user_memories = [
        {
            "date": "2024-01-15",
            "category": "work",
            "title": "Important project deadline",
            "content": "Project X deadline is February 1st",
            "tags": ["work", "deadline", "project"]
        },
        {
            "date": "2024-01-10",
            "category": "personal",
            "title": "Mom's birthday",
            "content": "Mom's birthday is January 25th, she likes roses",
            "tags": ["family", "birthday", "reminder"]
        }
    ]

    result = await agent.create_memory_aware_agent(
        user_id="demo_user",
        user_memories=user_memories,
        personality="Friendly, attentive, and proactive"
    )
    print(f"Agent created: {result}")

    # Start a conversation
    print("\n2. Starting conversation...")
    conversation = await agent.start_conversation(
        user_id="demo_user",
        memory_context=user_memories
    )
    print(f"Conversation started: {conversation}")

    # Simulate text interaction
    print("\n3. Sending message...")
    print("User: 'What important things do I have coming up?'")

    # The agent would respond with awareness of the memories
    print("Agent: Based on your memories, you have two important items:")
    print("  1. Your mom's birthday is on January 25th - she likes roses!")
    print("  2. Project X deadline on February 1st")
    print("  Would you like me to help you prepare for either of these?")


if __name__ == "__main__":
    asyncio.run(demo())