"""
Working Prompt Generator for Memory Bot
Uses direct API calls without proxies
"""

import os
import json
import httpx
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class WorkingPromptGenerator:
    """Generate prompts using direct Anthropic API calls"""

    def __init__(self):
        """Initialize with API key from environment"""
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Set ANTHROPIC_API_KEY or CLAUDE_API_KEY in .env")

        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

    def generate_prompt(self, task: str, context: Optional[Dict] = None) -> str:
        """Generate an optimized prompt for any task"""

        meta_prompt = f"""You are an expert prompt engineer. Create a detailed, production-ready prompt.

Task: {task}

{f"Context: {json.dumps(context, indent=2)}" if context else ""}

Requirements:
- Clear instructions
- Structured format
- Variable placeholders in {{brackets}}
- Specific output format

Return ONLY the generated prompt, no explanations."""

        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": meta_prompt}]
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
                result = response.json()
                return result["content"][0]["text"]
        except Exception as e:
            return f"Error generating prompt: {str(e)}"

    def generate_memory_prompt(self, task: str) -> str:
        """Generate memory-specific prompt"""
        return self.generate_prompt(
            task=f"Memory assistant task: {task}",
            context={"type": "memory_bot", "features": ["storage", "recall", "voice"]}
        )


# Pre-built templates (no API needed)
class Templates:
    """Ready-to-use prompt templates"""

    @staticmethod
    def conversation_starter():
        return """You are a helpful Memory Assistant.

Current conversation: {conversation_history}
User message: {user_input}

Instructions:
1. Respond naturally and helpfully
2. Reference relevant past context
3. Keep response concise
4. Format for {output_format}

Response:"""

    @staticmethod
    def memory_storage():
        return """Store this information:

Input: {user_input}
Type: {memory_type}
Timestamp: {timestamp}

Format as:
- Title: [brief description]
- Tags: [searchable keywords]
- Content: [full information]
- Priority: [1-5]

Confirm storage with summary."""

    @staticmethod
    def memory_recall():
        return """Find memories matching: {query}

Available memories:
{memory_list}

Return most relevant memories, sorted by relevance.
Include context and related information."""


def test_generator():
    """Test the generator"""
    print("=" * 60)
    print("TESTING PROMPT GENERATOR")
    print("=" * 60)

    # Test templates (always works)
    print("\n1. TESTING TEMPLATES (No API Required):")
    print("-" * 40)
    template = Templates.conversation_starter()
    print("Conversation Template:")
    print(template[:200] + "...")

    # Test API if available
    print("\n2. TESTING API GENERATOR:")
    print("-" * 40)
    try:
        gen = WorkingPromptGenerator()
        print("[OK] Generator initialized with API key")

        # Generate a simple prompt
        prompt = gen.generate_prompt(
            task="Help user track daily tasks",
            context={"format": "checklist"}
        )

        if not prompt.startswith("Error"):
            print("[OK] Successfully generated prompt:")
            print(prompt[:300] + "..." if len(prompt) > 300 else prompt)
        else:
            print(f"[ERROR] {prompt}")
    except ValueError as e:
        print(f"[INFO] {e}")
        print("Use templates instead, or add API key to .env")


if __name__ == "__main__":
    test_generator()