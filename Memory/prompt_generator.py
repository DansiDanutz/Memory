"""
Anthropic Prompt Generator for Memory Bot
Generates optimized prompts for various memory-related tasks
"""

import os
import json
from typing import List, Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class PromptGenerator:
    """Generate optimized prompts using Claude API"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY or CLAUDE_API_KEY environment variable.")
        try:
            self.client = Anthropic(api_key=self.api_key)
        except TypeError:
            # Fallback for older versions
            import anthropic
            self.client = anthropic.Client(api_key=self.api_key)

    def generate_memory_prompt(self, task: str, context: Optional[Dict] = None) -> str:
        """Generate a prompt optimized for memory-related tasks"""

        meta_prompt = f"""You are an expert prompt engineer. Create a detailed, production-ready prompt for a memory assistant bot.

Task: {task}

The prompt should be optimized for:
1. Memory recall and storage
2. Conversational context retention
3. WhatsApp message formatting
4. Voice interaction support

{f"Additional Context: {json.dumps(context, indent=2)}" if context else ""}

Format the prompt with:
- Clear role definition
- Structured instructions using XML tags
- Variable placeholders in {{brackets}}
- Memory-specific guidelines
- Response format specifications

Return ONLY the generated prompt, no explanations."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.7,
            messages=[{"role": "user", "content": meta_prompt}]
        )

        return response.content[0].text

    def generate_conversation_prompt(self,
                                   user_input: str,
                                   conversation_history: List[Dict],
                                   user_profile: Optional[Dict] = None) -> str:
        """Generate a context-aware conversation prompt"""

        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_history[-5:]  # Last 5 messages
        ])

        meta_prompt = f"""Create an optimized prompt for continuing this conversation:

<conversation_history>
{history_text}
</conversation_history>

<current_input>
{user_input}
</current_input>

{f"<user_profile>{json.dumps(user_profile, indent=2)}</user_profile>" if user_profile else ""}

Generate a prompt that:
1. Maintains conversation continuity
2. References relevant past context
3. Provides personalized responses
4. Handles the current query effectively

Return ONLY the generated prompt."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0.5,
            messages=[{"role": "user", "content": meta_prompt}]
        )

        return response.content[0].text

    def generate_voice_prompt(self, audio_context: str, language: str = "en") -> str:
        """Generate prompts optimized for voice interactions"""

        meta_prompt = f"""Create a prompt for processing voice input with these characteristics:

Audio Context: {audio_context}
Language: {language}

The prompt should:
1. Handle speech recognition uncertainties
2. Provide natural voice-friendly responses
3. Use appropriate prosody markers
4. Support Azure Speech synthesis format
5. Be concise for voice output

Return ONLY the generated prompt."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.6,
            messages=[{"role": "user", "content": meta_prompt}]
        )

        return response.content[0].text

    def optimize_existing_prompt(self, current_prompt: str, improvement_goals: List[str]) -> str:
        """Optimize an existing prompt based on specific goals"""

        goals_text = "\n".join([f"- {goal}" for goal in improvement_goals])

        meta_prompt = f"""Improve this existing prompt:

<current_prompt>
{current_prompt}
</current_prompt>

<improvement_goals>
{goals_text}
</improvement_goals>

Apply these optimization techniques:
1. Add chain-of-thought reasoning where appropriate
2. Use XML tags for better structure
3. Include relevant examples
4. Clarify ambiguous instructions
5. Add output format specifications

Return ONLY the optimized prompt."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.5,
            messages=[{"role": "user", "content": meta_prompt}]
        )

        return response.content[0].text


class PromptTemplates:
    """Pre-built prompt templates for common memory bot tasks"""

    @staticmethod
    def memory_storage_template() -> str:
        return """<role>You are a Memory Assistant that helps users store and recall information.</role>

<instructions>
1. Extract key information from: {user_input}
2. Categorize as: {memory_type}
3. Add metadata: timestamp, tags, importance
4. Store in format suitable for later retrieval
</instructions>

<memory_format>
- Title: Brief description
- Content: Full information
- Tags: [relevant, searchable, tags]
- Importance: 1-5 scale
- Timestamp: {timestamp}
</memory_format>

<response>Confirm storage with summary</response>"""

    @staticmethod
    def memory_recall_template() -> str:
        return """<role>You are retrieving memories based on user query.</role>

<query>{user_query}</query>

<available_memories>
{memory_list}
</available_memories>

<instructions>
1. Find most relevant memories matching the query
2. Rank by relevance and recency
3. Present in conversational format
4. Include context if needed
</instructions>

<response_format>
- Start with most relevant memory
- Provide supporting details
- Mention related memories if helpful
</response_format>"""

    @staticmethod
    def whatsapp_format_template() -> str:
        return """<role>Format response for WhatsApp message.</role>

<content>{message_content}</content>

<formatting_rules>
- Use *bold* for emphasis
- Use _italic_ for secondary info
- Keep paragraphs short (2-3 lines)
- Use emojis sparingly and appropriately
- Maximum 1000 characters
</formatting_rules>

<output>WhatsApp-formatted message</output>"""


if __name__ == "__main__":
    # Example usage
    generator = PromptGenerator()

    # Test memory prompt generation
    print("Generating memory storage prompt...")
    prompt = generator.generate_memory_prompt(
        task="Store user's daily schedule and remind them of appointments",
        context={"user_timezone": "UTC", "notification_preference": "30min_before"}
    )
    print(f"Generated Prompt:\n{prompt}\n")

    # Test conversation prompt
    print("\nGenerating conversation prompt...")
    conv_prompt = generator.generate_conversation_prompt(
        user_input="What did I tell you about my meeting tomorrow?",
        conversation_history=[
            {"role": "user", "content": "I have a meeting with John at 3pm tomorrow"},
            {"role": "assistant", "content": "I've noted your meeting with John at 3pm tomorrow."}
        ]
    )
    print(f"Generated Conversation Prompt:\n{conv_prompt}\n")

    # Use pre-built template
    print("\nUsing pre-built template:")
    template = PromptTemplates.memory_storage_template()
    print(f"Template:\n{template}")