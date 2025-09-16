"""
Test script for the prompt generator (without API key)
Shows how to use the prompt templates
"""

from prompt_generator import PromptTemplates
import json
from datetime import datetime


def test_templates():
    """Test the pre-built templates"""

    print("=" * 60)
    print("PROMPT GENERATOR TEMPLATES TEST")
    print("=" * 60)

    # Test memory storage template
    print("\n1. MEMORY STORAGE TEMPLATE:")
    print("-" * 40)
    storage_template = PromptTemplates.memory_storage_template()
    print(storage_template)

    # Example of filling the template
    print("\n   Example with filled values:")
    print("-" * 40)
    filled_storage = storage_template.format(
        user_input="Meeting with Sarah at 2pm tomorrow about project budget",
        memory_type="appointment",
        timestamp=datetime.now().isoformat()
    )
    print(filled_storage)

    # Test memory recall template
    print("\n2. MEMORY RECALL TEMPLATE:")
    print("-" * 40)
    recall_template = PromptTemplates.memory_recall_template()
    print(recall_template)

    # Test WhatsApp format template
    print("\n3. WHATSAPP FORMAT TEMPLATE:")
    print("-" * 40)
    whatsapp_template = PromptTemplates.whatsapp_format_template()
    print(whatsapp_template)

    print("\n" + "=" * 60)
    print("To use the API-based prompt generator, add your")
    print("ANTHROPIC_API_KEY to the .env file:")
    print("ANTHROPIC_API_KEY=your-key-here")
    print("=" * 60)


def example_api_usage():
    """Show how to use the API-based generator (code example only)"""

    print("\n" + "=" * 60)
    print("API USAGE EXAMPLE (Code Only)")
    print("=" * 60)

    example_code = """
# Once you have your API key in .env:

from prompt_generator import PromptGenerator

# Initialize the generator
generator = PromptGenerator()

# Generate a memory prompt
prompt = generator.generate_memory_prompt(
    task="Help user remember important dates and appointments",
    context={"user_timezone": "EST", "reminder_style": "friendly"}
)

# Generate a conversation prompt
conv_prompt = generator.generate_conversation_prompt(
    user_input="What's on my schedule today?",
    conversation_history=[
        {"role": "user", "content": "I have a dentist appointment at 3pm"},
        {"role": "assistant", "content": "Noted your dentist appointment at 3pm"}
    ],
    user_profile={"name": "John", "preferences": {"notification": "30min_before"}}
)

# Generate a voice-optimized prompt
voice_prompt = generator.generate_voice_prompt(
    audio_context="User asking about weather",
    language="en"
)

# Optimize an existing prompt
optimized = generator.optimize_existing_prompt(
    current_prompt="Tell me about the weather",
    improvement_goals=["Add personality", "Include temperature units", "Be more specific"]
)
"""
    print(example_code)


if __name__ == "__main__":
    test_templates()
    example_api_usage()