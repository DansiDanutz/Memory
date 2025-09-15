# WhatsApp Bot Features & Commands Documentation

## Overview
The Memory App WhatsApp Bot provides a comprehensive interface for memory storage, retrieval, and management through WhatsApp messaging. It supports text commands, voice notes, images, and implements advanced features like voice authentication and AI-powered memory categorization.

## Table of Contents
1. [Core Features](#core-features)
2. [Command Reference](#command-reference)
3. [Voice Features](#voice-features)
4. [Message Monitoring](#message-monitoring)
5. [Contact Profiles](#contact-profiles)
6. [Secret Memories](#secret-memories)
7. [Daily Reviews](#daily-reviews)
8. [Premium Features](#premium-features)
9. [Group Chat Support](#group-chat-support)
10. [Examples](#examples)

## Core Features

### 🎯 Three Diamond Features
1. **Voice-Activated Memory Storage** - Store memories via voice notes with automatic transcription
2. **AI Call Handling** - Intelligent responses and memory retrieval during voice calls
3. **Daily Summaries** - Automated daily memory reviews with user approval workflow

### 📱 Supported Message Types
- **Text Messages** - Commands and memory content
- **Voice Notes** - Automatic transcription and voice authentication
- **Images** - Visual memory storage with AI description
- **Documents** - PDF and text file processing
- **Location** - Geographic memory tagging

## Command Reference

### Basic Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show all available commands | `/help` |
| `/enroll [name]` | Start voice enrollment process | `/enroll John Doe` |
| `/status` | Check account status and credits | `/status` |
| `/memories` | List recent memories | `/memories` |
| `/search [query]` | Search memories | `/search birthday party` |

### Memory Management

| Command | Description | Example |
|---------|-------------|---------|
| `/store [content]` | Store a new memory | `/store Met Sarah at coffee shop today` |
| `/memory [number]` | Retrieve specific memory | `/memory 1001` |
| `/edit [number] [new content]` | Edit existing memory | `/edit 1001 Met Sarah at Starbucks` |
| `/delete [number]` | Delete a memory | `/delete 1001` |
| `/category [name]` | List memories by category | `/category work` |

### Voice Authentication Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/enroll [name]` | Start voice enrollment (3 samples) | `/enroll Jane Smith` |
| `/verify` | Test voice authentication | Send voice note after command |
| `/reset_voice` | Reset voice profile | `/reset_voice` |
| `/voice_status` | Check voice auth status | `/voice_status` |

### Contact Management

| Command | Description | Example |
|---------|-------------|---------|
| `/contact add [phone] [name]` | Add contact profile | `/contact add +1234567890 Mom` |
| `/contact list` | List all contacts | `/contact list` |
| `/contact [name]` | View contact details | `/contact Mom` |
| `/relationship [contact] [type]` | Set relationship | `/relationship Mom mother` |

### Secret Memory Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/secret [content]` | Store secret memory | `/secret Bank PIN is 1234` |
| `/secrets list` | List secret memories (titles only) | `/secrets list` |
| `/secret [id]` | Retrieve secret (requires auth) | `/secret sec_123` |
| `/secret delete [id]` | Delete secret memory | `/secret delete sec_123` |

### Daily Review Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/daily_review` | Get today's memory summary | `/daily_review` |
| `/keep_[id]` | Keep memory in review | `/keep_mem_123` |
| `/delete_[id]` | Delete memory in review | `/delete_mem_123` |
| `/modify_[id] [content]` | Modify memory in review | `/modify_mem_123 Updated content` |
| `/review_history` | View past reviews | `/review_history` |

### Subscription & Premium

| Command | Description | Example |
|---------|-------------|---------|
| `/subscribe [plan]` | Subscribe to plan | `/subscribe pro` |
| `/plans` | View available plans | `/plans` |
| `/billing` | Check billing status | `/billing` |
| `/credits` | Check memory credits | `/credits` |
| `/upgrade` | Upgrade subscription | `/upgrade` |

## Voice Features

### Voice Note Processing
Send a voice note to automatically:
1. **Transcribe** - Convert speech to text using OpenAI Whisper
2. **Authenticate** - Verify speaker identity
3. **Categorize** - AI determines memory category
4. **Store** - Save as timestamped memory

### Voice Commands in Voice Notes
Say these phrases in voice notes:
- "Mother" or "Mom" - Access family memories
- "Work" or "Office" - Access work memories  
- "Secret" or "Private" - Access secret memories
- "Memory [number]" - Retrieve specific memory
- "Delete memory [number]" - Delete specific memory
- "Today's memories" - Get today's summary

### Voice Enrollment Process
1. Send `/enroll Your Name`
2. Record 3 voice samples when prompted:
   - Sample 1: "My name is [Your Name] and I authorize memory access"
   - Sample 2: "Memory access authentication for [Your Name]"
   - Sample 3: "Voice enrollment sample three for secure access"
3. System creates unique voice profile
4. Future access requires voice match

### Voice Authentication Security
- **Confidence Threshold**: 85% match required
- **Challenge Questions**: Asked if 70-85% match
- **Anti-Spoofing**: Detects recorded/synthetic voices
- **Liveness Detection**: Random phrase challenges
- **Session Management**: 24-hour voice sessions

## Message Monitoring

### Automatic Conversation Monitoring
The bot monitors conversations and:
- **Buffers Messages** - Collects ongoing conversations
- **Summarizes** - Creates AI summaries every 10 messages
- **Stores** - Saves important conversations as memories
- **Notifies** - Alerts about significant topics

### Keywords Triggering Monitoring
Messages containing these trigger enhanced monitoring:
- Important dates/events
- Financial information
- Health-related topics
- Relationship mentions
- Work commitments
- Travel plans

### Privacy Controls
- `/monitoring off` - Disable monitoring
- `/monitoring on` - Enable monitoring
- `/monitoring status` - Check status
- `/monitoring exclude [contact]` - Exclude contact

## Contact Profiles

### Profile Information Stored
- **Basic Info**: Name, phone, email
- **Relationship**: Type (family, friend, work)
- **Interaction History**: Message count, last contact
- **Memory Association**: Linked memories
- **Trust Level**: For secret sharing
- **Preferences**: Communication preferences

### Relationship Types
- `mother`, `father`, `sibling`, `child`
- `spouse`, `partner`, `friend`, `best_friend`
- `colleague`, `boss`, `client`, `mentor`
- `doctor`, `lawyer`, `service`, `other`

### Contact-Based Features
- **Shared Memories** - Memories involving contact
- **Conversation History** - Past interactions
- **Important Dates** - Birthdays, anniversaries
- **Auto-Categorization** - Based on relationship

## Secret Memories

### Security Levels
1. **Standard** - Basic encryption
2. **Confidential** - Additional authentication required
3. **Ultra Secret** - Voice + challenge required

### Secret Memory Features
- **Encryption** - AES-256 encryption
- **Access Logs** - Track who accessed when
- **Time Locks** - Can't access for X hours
- **Self-Destruct** - Auto-delete after time/views
- **Inheritance** - Transfer on inactivity

### Examples of Secret Memories
- Passwords and PINs
- Medical information
- Financial details
- Personal thoughts
- Surprise plans
- Legal documents

## Daily Reviews

### Review Process
Every day at configured time (default 9 PM):
1. **Summary Generation** - AI summarizes day's memories
2. **Notification** - WhatsApp message with summary
3. **Review Options** - Keep, modify, or delete each
4. **Categorization** - AI suggests categories
5. **Insights** - Patterns and suggestions

### Review Actions
- **Keep** - Preserve memory as-is
- **Modify** - Edit before keeping
- **Delete** - Remove memory
- **Merge** - Combine related memories
- **Categorize** - Assign/change category

### Customization Options
- `/review_time [HH:MM]` - Set review time
- `/review_frequency [daily|weekly]` - Set frequency
- `/review_categories [list]` - Categories to review
- `/review_ai [on|off]` - AI suggestions

## Premium Features

### Subscription Tiers

#### 🆓 Free Plan
- 100 memories/month
- Basic categories
- Text commands only
- Daily reviews

#### 💼 Basic ($9.99/month)
- 500 memories/month
- Voice authentication
- Contact profiles
- Message monitoring
- Priority support

#### 🌟 Pro ($19.99/month)
- 2000 memories/month
- Secret memories
- Advanced AI features
- Custom categories
- API access
- Voice cloning (beta)

#### 👑 Elite ($39.99/month)
- Unlimited memories
- All Pro features
- Custom AI training
- White-label options
- Dedicated support
- Early access features

### Premium-Only Commands
| Command | Required Plan | Description |
|---------|---------------|-------------|
| `/voice_clone` | Pro | Clone your voice for AI responses |
| `/ai_avatar` | Pro | Create AI avatar personality |
| `/analytics` | Pro | Advanced memory analytics |
| `/export` | Basic | Export all memories |
| `/api_key` | Pro | Generate API access key |
| `/family_share` | Elite | Share with family members |

## Group Chat Support

### Group Features
- **Shared Memories** - Group memory pool
- **Collaborative Reviews** - Group daily summaries
- **Permissions** - Admin/member roles
- **Privacy** - Individual vs shared memories

### Group Commands
| Command | Description |
|---------|-------------|
| `/group create [name]` | Create memory group |
| `/group add [phone]` | Add member to group |
| `/group memories` | View group memories |
| `/group review` | Start group review |
| `/group leave` | Leave memory group |

### Group Permissions
- **Admin** - All commands, manage members
- **Contributor** - Add/edit memories
- **Viewer** - Read-only access
- **Guest** - Temporary access

## Examples

### Example 1: First Time Setup
```
User: /enroll John Smith
Bot: 🎤 Welcome John Smith! Let's set up voice authentication.
     Please send a voice note saying:
     "My name is John Smith and I authorize memory access"

[User sends voice note]

Bot: ✅ Sample 1/3 recorded. Now please say:
     "Memory access authentication for John Smith"

[User sends voice note]

Bot: ✅ Sample 2/3 recorded. Finally, please say:
     "Voice enrollment sample three for secure access"

[User sends voice note]

Bot: 🎉 Voice enrollment complete!
     📋 Free Plan - 100 memories/month
     💳 Credits: 100/100 memories
     🎤 Voice authentication enabled!
```

### Example 2: Storing Memory via Voice
```
[User sends voice note: "Had an amazing dinner with Sarah at La Bernardin. 
The tasting menu was incredible, especially the langoustine course."]

Bot: 🔓 Voice authenticated: John Smith
     📝 Memory stored as #1042
     📁 Category: Social
     🏷️ Tags: #dinner #friends #restaurant
     💬 "Had an amazing dinner with Sarah at La Bernardin..."
```

### Example 3: Daily Review
```
Bot: 📊 Daily Memory Review - September 13, 2025
     
     You created 5 memories today:
     
     1️⃣ Memory #1042 (Social)
     "Dinner with Sarah at La Bernardin"
     Actions: /keep_1042 | /delete_1042 | /modify_1042
     
     2️⃣ Memory #1043 (Work)
     "Completed project presentation"
     Actions: /keep_1043 | /delete_1043 | /modify_1043
     
     📈 Insights: You had 2 social and 3 work memories today.
     💡 Suggestion: Consider adding a personal/health memory.
```

### Example 4: Secret Memory Storage
```
User: /secret My investment account password is TR@d3r2025!
Bot: 🔒 Secret memory stored (ID: sec_789)
     🔐 Encryption: AES-256
     ⏰ Access locked for 1 hour
     🔑 Voice authentication required for retrieval
     
     To retrieve: /secret sec_789 (requires voice auth)
```

### Example 5: Contact-Based Memory
```
User: /contact add +1234567890 Mom
Bot: ✅ Contact added: Mom

User: Had lunch with Mom at her favorite restaurant
Bot: 📝 Memory #1044 stored
     👥 Linked to contact: Mom
     📁 Category: Family
     🔗 This is your 15th memory with Mom
```

### Example 6: Message Monitoring Alert
```
Bot: 📬 Conversation Summary (Auto-generated)
     
     Thread with "David" - 12 messages:
     • Discussed project deadline (Sept 20)
     • Agreed on budget: $15,000
     • Meeting scheduled: Tuesday 3 PM
     
     Would you like to save this summary?
     Reply: YES to save | NO to discard
```

## Error Messages & Troubleshooting

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Voice authentication failed" | Voice doesn't match profile | Re-enroll or try again clearly |
| "Memory limit reached" | Monthly quota exceeded | Upgrade plan or wait for reset |
| "Contact not found" | Unknown contact referenced | Add contact first |
| "Invalid command" | Command syntax error | Check command format |
| "Network error" | Connection issue | Retry after few seconds |
| "Transcription failed" | Audio quality issue | Send clearer voice note |

### Troubleshooting Tips

1. **Voice Issues**
   - Speak clearly and slowly
   - Minimize background noise
   - Use consistent device/microphone
   - Re-enroll if persistent issues

2. **Command Issues**
   - Check exact command syntax
   - Ensure proper spacing
   - Use lowercase for commands
   - Include required parameters

3. **Syncing Issues**
   - Check internet connection
   - Verify WhatsApp connected
   - Restart app if needed
   - Contact support if persists

## Best Practices

### For Optimal Experience
1. **Categorize Memories** - Use consistent categories
2. **Regular Reviews** - Process daily summaries
3. **Voice Training** - Complete all 3 samples clearly
4. **Contact Profiles** - Maintain updated contacts
5. **Security** - Use secrets for sensitive data
6. **Backups** - Regularly export memories

### Privacy & Security
1. Enable two-factor authentication on WhatsApp
2. Use voice auth for sensitive memories
3. Regularly review access logs
4. Set appropriate secret levels
5. Configure inheritance settings
6. Limit group memory sharing

### Memory Organization
1. Use descriptive memory content
2. Include relevant dates/times
3. Tag people involved
4. Specify locations when relevant
5. Add context for future reference
6. Review and clean up regularly

## Integration with Other Platforms

The Memory App also integrates with:
- **Telegram** - @MemoryAppBot
- **Twilio** - Voice calls and SMS
- **Web Interface** - Browser access
- **API** - Developer integration
- **Mobile Apps** - iOS/Android (coming soon)

Cross-platform features:
- Synchronized memories
- Unified contact profiles
- Shared authentication
- Consistent commands
- Real-time updates

## Support & Resources

### Getting Help
- Send `/support [issue]` - Create support ticket
- Send `/docs` - Get documentation links
- Send `/video` - Watch tutorial videos
- Send `/faq` - Common questions

### Community
- WhatsApp Group: [Join Link]
- Telegram Channel: @MemoryAppNews
- Discord: [Server Link]
- Reddit: r/MemoryApp

### Developer Resources
- API Documentation: [API Docs]
- GitHub: [Repository]
- NPM Package: @memoryapp/sdk
- Python Package: pip install memoryapp

---

For setup instructions, see [WHATSAPP_SETUP_GUIDE.md](WHATSAPP_SETUP_GUIDE.md)