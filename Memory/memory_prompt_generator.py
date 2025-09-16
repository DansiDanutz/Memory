"""
Memory Bot Prompt Generator
Integrated with your existing Memory system
"""

import os
import json
import httpx
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class MemoryPromptGenerator:
    """Generate optimized prompts for Memory Bot operations"""

    def __init__(self):
        """Initialize with API credentials"""
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        self.use_api = bool(self.api_key)

        if self.use_api:
            self.base_url = "https://api.anthropic.com/v1/messages"
            self.headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

    def _api_call(self, prompt: str, max_tokens: int = 1500) -> str:
        """Make API call to generate prompt"""
        if not self.use_api:
            return "API not configured. Using templates instead."

        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            with httpx.Client() as client:
                response = client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()["content"][0]["text"]
        except Exception as e:
            return f"Error: {str(e)}"

    def generate_memory_storage_prompt(self,
                                      user_input: str,
                                      memory_type: str = "general") -> str:
        """Generate prompt for storing memories"""

        if self.use_api:
            meta_prompt = f"""Create a prompt for storing this memory:
Input: {user_input}
Type: {memory_type}

The prompt should extract and structure:
- Key information
- Relevant tags
- Importance level
- Temporal context

Return ONLY the storage prompt."""

            result = self._api_call(meta_prompt)
            if not result.startswith("Error"):
                return result

        # Fallback template
        return f"""<memory_storage>
<input>{user_input}</input>
<type>{memory_type}</type>
<timestamp>{datetime.now().isoformat()}</timestamp>

<instructions>
1. Extract main subject/topic
2. Identify key details (who, what, when, where)
3. Generate 3-5 searchable tags
4. Assess importance (1-5 scale)
5. Note any deadlines or time-sensitive info
</instructions>

<output_format>
Title: [Brief descriptive title]
Content: [Full information preserved]
Tags: [tag1, tag2, tag3]
Importance: [1-5]
Deadline: [if applicable]
Related: [connections to other memories]
</output_format>
</memory_storage>"""

    def generate_memory_recall_prompt(self,
                                     query: str,
                                     available_memories: List[str]) -> str:
        """Generate prompt for recalling memories"""

        memory_summary = "\n".join(available_memories[:10])  # Limit to 10 for context

        if self.use_api:
            meta_prompt = f"""Create a prompt for retrieving memories:
Query: {query}
Available memories preview: {memory_summary}

The prompt should:
- Find most relevant memories
- Rank by relevance
- Present naturally

Return ONLY the recall prompt."""

            result = self._api_call(meta_prompt)
            if not result.startswith("Error"):
                return result

        # Fallback template
        return f"""<memory_recall>
<query>{query}</query>

<available_memories>
{memory_summary}
</available_memories>

<instructions>
1. Identify memories matching the query
2. Score each by relevance (0-10)
3. Include partial matches if highly relevant
4. Consider temporal context
5. Group related memories
</instructions>

<response_format>
Most relevant memory:
[Primary memory content]

Related memories:
[Additional relevant information]

Context:
[Any helpful background or connections]
</response_format>
</memory_recall>"""

    def generate_conversation_prompt(self,
                                    user_message: str,
                                    history: List[Dict],
                                    user_profile: Optional[Dict] = None) -> str:
        """Generate conversation continuation prompt"""

        recent_history = history[-5:] if history else []
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history])

        if self.use_api:
            meta_prompt = f"""Create a conversation prompt:
Current message: {user_message}
History: {history_text}
Profile: {json.dumps(user_profile) if user_profile else 'None'}

Generate a prompt for natural continuation.

Return ONLY the conversation prompt."""

            result = self._api_call(meta_prompt)
            if not result.startswith("Error"):
                return result

        # Fallback template
        return f"""<conversation>
<context>
{history_text}
</context>

<current_message>{user_message}</current_message>

{"<user_profile>" + json.dumps(user_profile, indent=2) + "</user_profile>" if user_profile else ""}

<instructions>
1. Maintain conversation continuity
2. Reference relevant past context naturally
3. Match the user's tone and style
4. Provide helpful, specific responses
5. Remember discussed topics and preferences
</instructions>

<response_guidelines>
- Be conversational but informative
- Keep responses concise unless detail is needed
- Use appropriate formatting for readability
- Include relevant memories if available
</response_guidelines>
</conversation>"""

    def generate_whatsapp_prompt(self, content: str) -> str:
        """Generate WhatsApp-formatted response prompt"""

        return f"""<whatsapp_format>
<content>{content}</content>

<formatting_rules>
- Use *bold* for emphasis (sparingly)
- Use _italic_ for secondary information
- Keep paragraphs to 2-3 lines max
- Use line breaks for readability
- Limit to 1000 characters
- Use emojis appropriately but sparingly
- Number lists with 1. 2. 3. format
</formatting_rules>

<output>WhatsApp-ready message</output>
</whatsapp_format>"""

    def generate_voice_prompt(self,
                            audio_context: str,
                            language: str = "en") -> str:
        """Generate voice interaction prompt"""

        return f"""<voice_interaction>
<audio_context>{audio_context}</audio_context>
<language>{language}</language>

<requirements>
1. Natural, conversational tone
2. Short, clear sentences
3. Avoid complex punctuation
4. Use speech-friendly vocabulary
5. Include prosody hints for Azure TTS
</requirements>

<azure_speech_format>
- Use SSML tags for emphasis
- Keep responses under 30 seconds when spoken
- Add pauses with commas
- Avoid abbreviations
</azure_speech_format>

<response>Voice-optimized response</response>
</voice_interaction>"""


def example_usage():
    """Show how to use the generator"""

    generator = MemoryPromptGenerator()

    # Example 1: Storage prompt
    storage_prompt = generator.generate_memory_storage_prompt(
        user_input="Meeting with John tomorrow at 3pm about project budget",
        memory_type="appointment"
    )
    print("Storage Prompt Generated:")
    print(storage_prompt[:300] + "...\n")

    # Example 2: Recall prompt
    recall_prompt = generator.generate_memory_recall_prompt(
        query="What meetings do I have?",
        available_memories=["Meeting with John at 3pm", "Dentist at 5pm Monday"]
    )
    print("Recall Prompt Generated:")
    print(recall_prompt[:300] + "...\n")

    # Example 3: WhatsApp formatting
    wa_prompt = generator.generate_whatsapp_prompt(
        content="Your meeting with John is tomorrow at 3pm. Don't forget the budget report!"
    )
    print("WhatsApp Prompt Generated:")
    print(wa_prompt[:300] + "...")


if __name__ == "__main__":
    print("=" * 60)
    print("MEMORY BOT PROMPT GENERATOR")
    print("=" * 60)
    print()
    example_usage()