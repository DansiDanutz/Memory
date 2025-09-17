#!/usr/bin/env python3
"""
MemoApp Branding Module
Contains all branding, messages, and UI text for the WhatsApp Memory Bot
"""

AGENT_NAME = "Memo"
TAGLINE = "Your Personal Memory Guardian"
VERSION = "1.0.0"

# Welcome Messages
WELCOME_MESSAGE = f"""
🧠 Welcome to *{AGENT_NAME}* - {TAGLINE}

I'm your personal AI memory assistant that securely stores and organizes your memories across 5 intelligent categories.

*Available Commands:*
• Send any text message to save a memory
• Send a voice message (10+ words) to authenticate
• `help:` - Show all commands
• `search: [query]` - Search your memories
• `today:` - View today's memories
• `categories:` - Show memory categories
• `stats:` - View your memory statistics
• `enroll:` - Set up voice authentication

*Memory Categories:*
📅 CHRONOLOGICAL - Events & appointments
📝 GENERAL - Facts & preferences  
🔒 CONFIDENTIAL - Private information
🔐 SECRET - Sensitive data (auth required)
⚡ ULTRA_SECRET - Critical info (auth required)

Start by sending me any memory you'd like to save!
""".strip()

# Alias for backward compatibility
WELCOME = WELCOME_MESSAGE

FIRST_TIME_MESSAGE = f"""
👋 Hello! I'm {AGENT_NAME}, your personal AI memory assistant.

I notice this is your first time here. Let me help you get started:

1️⃣ *Save a memory* - Just send me any text
2️⃣ *Voice authentication* - Send a 10+ word voice message to access secret memories
3️⃣ *Search anytime* - Use `search:` to find any memory

Your memories are encrypted and organized automatically. 

What would you like to remember today?
""".strip()

# Command Help Messages
HELP_MESSAGE = f"""
📚 *{AGENT_NAME} Commands*

*Basic Commands:*
• `help:` - Show this help message
• `start:` - Show welcome message
• `about:` - Learn about {AGENT_NAME}
• `status:` - Check authentication & session status
• `whoami:` - View your profile & tenant info

*Memory Management:*
• `search: [query]` - Search all memories
• `search: [query] [category]` - Search in specific category
• `search: dept:[name]` - Search memories by department
• `search: tenant:[name]` - Search memories by tenant
• `today:` - Show today's memories
• `yesterday:` - Show yesterday's memories
• `recent:` - Show last 10 memories
• `categories:` - List all categories with descriptions
• `stats:` - View memory statistics

*Voice Authentication:*
• `enroll:` - Set up voice passphrase (10+ words)
• `verify:` - Verify voice enrollment status
• `auth:` or `authenticate:` - Start authentication
• `logout:` - End current session
• Send voice message to authenticate

*Administrative:*
• `audit:` - View audit logs (admin only)

*Examples:*
• `search: meeting` - Find all meetings
• `search: doctor SECRET` - Search secret medical memories
• `search: dept:engineering` - Search engineering dept memories
• `search: tenant:acme` - Search ACME Corp memories
• `today: CHRONOLOGICAL` - Today's timeline events

*Categories:*
📅 *CHRONOLOGICAL* - Timeline events, appointments
📝 *GENERAL* - Facts, preferences, everyday info
🔒 *CONFIDENTIAL* - Private information
🔐 *SECRET* - Sensitive data (voice auth required)
⚡ *ULTRA_SECRET* - Critical info (voice auth required)

Type any message to save it as a memory!
""".strip()

ABOUT_MESSAGE = f"""
🧠 *About {AGENT_NAME} v{VERSION}*

{AGENT_NAME} is an advanced AI memory management system that helps you:

✅ Store memories securely with encryption
✅ Organize automatically into 5 categories
✅ Search instantly across all memories
✅ Protect sensitive data with voice authentication
✅ Access memories anytime via WhatsApp

*Security Features:*
• 🔐 End-to-end encryption for secret memories
• 🎤 Voice authentication (10+ word passphrase)
• ⏱️ 10-minute session timeout
• 📊 Audit logging for all access

*AI Features:*
• 🤖 Automatic categorization
• 🔍 Semantic search
• 📅 Timeline organization
• 🎯 Context-aware responses

Developed with ❤️ for secure memory management.
""".strip()

# Category Descriptions
CATEGORY_DESCRIPTIONS = {
    "CHRONOLOGICAL": "📅 Timeline events, appointments, dates, schedules, and time-sensitive information",
    "GENERAL": "📝 General facts, preferences, hobbies, interests, and everyday information",
    "CONFIDENTIAL": "🔒 Private information like passwords, PINs, account numbers (basic encryption)",
    "SECRET": "🔐 Sensitive data like medical records, financial info (requires voice auth)",
    "ULTRA_SECRET": "⚡ Critical information like legal documents, emergency data (requires voice auth)"
}

# Response Messages
MEMORY_SAVED_MESSAGE = """✅ Memory saved successfully!
Category: *{category}*
ID: `{memory_id}`
{auth_note}"""

AUTH_REQUIRED_MESSAGE = """🔐 This appears to be *{category}* information.

Please send a voice message with your passphrase (10+ words) to authenticate and access secret memories.

Haven't enrolled yet? Use `enroll:` to set up voice authentication."""

SEARCH_RESULTS_HEADER = """🔍 *Search Results for "{query}"*
Found {count} memories:

"""

NO_RESULTS_MESSAGE = """❌ No memories found for "{query}".

Try:
• Using different keywords
• Checking a specific category
• Using `recent:` to see latest memories"""

SESSION_EXPIRED_MESSAGE = """⏱️ Your authentication session has expired.

Please send your voice passphrase again to access secret memories."""

ENROLLMENT_PROMPT = """🎤 *Voice Enrollment*

To set up voice authentication, please:

1. Send a voice message with your passphrase
2. Use at least 10 words
3. Speak clearly and naturally
4. Remember this phrase - you'll need it to access secret memories

*Example passphrase:*
"The quick brown fox jumps over the lazy dog in the morning sunshine"

Send your voice message now to continue..."""

# Error Messages
ERROR_MESSAGES = {
    "INVALID_COMMAND": "❌ Invalid command. Use `/help` to see available commands.",
    "AUDIO_DOWNLOAD_FAILED": "❌ Failed to download audio. Please try again.",
    "TRANSCRIPTION_FAILED": "❌ Could not understand audio. Please speak clearly.",
    "AUTHENTICATION_FAILED": "❌ Authentication failed. Please check your passphrase.",
    "STORAGE_ERROR": "❌ Failed to save memory. Please try again.",
    "SEARCH_ERROR": "❌ Search failed. Please try again.",
    "SESSION_ERROR": "❌ Session error. Please authenticate again.",
    "GENERAL_ERROR": "❌ An error occurred. Please try again or contact support."
}

# Success Messages
SUCCESS_MESSAGES = {
    "AUTH_SUCCESS": f"✅ Authentication successful! Your session is valid for 10 minutes.\n\nYou can now access SECRET and ULTRA_SECRET memories.",
    "ENROLLMENT_SUCCESS": "✅ Voice passphrase enrolled successfully!\n\nYou can now use this passphrase to access secret memories.",
    "LOGOUT_SUCCESS": "👋 Logged out successfully. Your secret memories are now locked.",
    "DELETE_SUCCESS": "🗑️ Memory deleted successfully.",
    "UPDATE_SUCCESS": "✏️ Memory updated successfully."
}

# Footer Messages
FOOTER_HINT = f"\n\n💡 _Tip: Use `help:` to see all commands_"
FOOTER_SECURE = f"\n\n🔒 _MemoApp - Your memories are encrypted and secure_"

def format_memory_display(memory: dict) -> str:
    """Format a memory for display"""
    return f"""
📌 *Memory [{memory.get('id', 'unknown')}]*
📅 {memory.get('timestamp', 'Unknown time')}
📁 {memory.get('category', 'GENERAL')}

{memory.get('content', 'No content')}
"""

def format_stats_display(stats: dict) -> str:
    """Format statistics for display"""
    total = stats.get('total', 0)
    by_category = stats.get('by_category', {})
    
    category_lines = []
    for cat, count in by_category.items():
        emoji = {
            'CHRONOLOGICAL': '📅',
            'GENERAL': '📝',
            'CONFIDENTIAL': '🔒',
            'SECRET': '🔐',
            'ULTRA_SECRET': '⚡'
        }.get(cat, '📝')
        category_lines.append(f"{emoji} {cat}: {count}")
    
    return f"""
📊 *Your Memory Statistics*

Total Memories: *{total}*
First Memory: {stats.get('first_memory', 'N/A')}
Last Memory: {stats.get('last_memory', 'N/A')}

*By Category:*
{chr(10).join(category_lines)}

Active Sessions: {stats.get('active_sessions', 0)}
Voice Enrolled: {'✅ Yes' if stats.get('voice_enrolled') else '❌ No'}
"""