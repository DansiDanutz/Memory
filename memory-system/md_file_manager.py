#!/usr/bin/env python3
"""
MD File Manager - Advanced Memory File Management System
Handles creation, updating, and organization of user memory files
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
import hashlib
import re
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles
import yaml

logger = logging.getLogger(__name__)

class MemoryTag(Enum):
    """Memory classification tags"""
    CHRONOLOGICAL = "chronological"
    GENERAL = "general"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    ULTRA_SECRET = "ultrasecret"

class FileType(Enum):
    """Types of memory files"""
    USER = "user"
    CONTACT = "contact"
    RELATIONSHIP = "relationship"
    TOPIC = "topic"
    DAILY_DIGEST = "daily_digest"

@dataclass
class MemoryEntry:
    """Represents a single memory entry"""
    id: str
    timestamp: datetime
    content: str
    tag: MemoryTag
    source: str  # phone_number or contact name
    context: Optional[str] = None
    related_entries: List[str] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.related_entries is None:
            self.related_entries = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class UserProfile:
    """User profile structure"""
    phone_number: str
    name: Optional[str] = None
    created_at: datetime = None
    last_updated: datetime = None
    preferences: Dict[str, Any] = None
    contacts: List[str] = None
    security_level: str = "standard"
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.preferences is None:
            self.preferences = {}
        if self.contacts is None:
            self.contacts = []

class MDFileManager:
    """Advanced MD File Manager for memory system"""
    
    def __init__(self, base_dir: str = "users", encryption_key: Optional[str] = None):
        """Initialize the MD File Manager"""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.users_dir = self.base_dir / "profiles"
        self.contacts_dir = self.base_dir / "contacts"
        self.relationships_dir = self.base_dir / "relationships"
        self.topics_dir = self.base_dir / "topics"
        self.digests_dir = self.base_dir / "daily_digests"
        
        for directory in [self.users_dir, self.contacts_dir, self.relationships_dir, 
                         self.topics_dir, self.digests_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.encryption_key = encryption_key
        self.file_locks = {}  # For concurrent access control
        
        # Memory entry cache for performance
        self.entry_cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(minutes=30)
        
        logger.info(f"🗂️ MD File Manager initialized with base directory: {self.base_dir}")
    
    def _generate_entry_id(self, content: str, timestamp: datetime) -> str:
        """Generate unique ID for memory entry using UUID format"""
        import uuid
        # Generate a proper UUID for database compatibility
        return str(uuid.uuid4())
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for safe file system usage"""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized.lower()
    
    def _get_user_file_path(self, phone_number: str) -> Path:
        """Get the file path for a user's main memory file"""
        sanitized_phone = self._sanitize_filename(phone_number)
        return self.users_dir / f"USER.{sanitized_phone}.md"
    
    def _get_contact_file_path(self, contact_name: str) -> Path:
        """Get the file path for a contact's memory file"""
        sanitized_name = self._sanitize_filename(contact_name)
        return self.contacts_dir / f"{sanitized_name}.md"
    
    def _get_relationship_file_path(self, user_phone: str, contact_name: str) -> Path:
        """Get the file path for a relationship memory file"""
        sanitized_phone = self._sanitize_filename(user_phone)
        sanitized_name = self._sanitize_filename(contact_name)
        return self.relationships_dir / f"{sanitized_phone}_{sanitized_name}.md"
    
    def _get_topic_file_path(self, topic: str) -> Path:
        """Get the file path for a topic memory file"""
        sanitized_topic = self._sanitize_filename(topic)
        return self.topics_dir / f"topic_{sanitized_topic}.md"
    
    async def create_user_file(self, phone_number: str, name: Optional[str] = None, 
                              initial_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new user memory file"""
        try:
            file_path = self._get_user_file_path(phone_number)
            
            # Check if file already exists
            if file_path.exists():
                logger.warning(f"User file already exists: {phone_number}")
                return {
                    'success': False,
                    'message': 'User file already exists',
                    'file_path': str(file_path)
                }
            
            # Create user profile
            profile = UserProfile(
                phone_number=phone_number,
                name=name,
                created_at=datetime.now(),
                preferences=initial_data or {}
            )
            
            # Create initial file content
            content = self._generate_user_file_content(profile)
            
            # Write file
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            logger.info(f"✅ Created user file: {phone_number}")
            
            return {
                'success': True,
                'message': 'User file created successfully',
                'file_path': str(file_path),
                'profile': asdict(profile)
            }
            
        except Exception as e:
            logger.error(f"Failed to create user file for {phone_number}: {e}")
            return {
                'success': False,
                'message': f'Failed to create user file: {str(e)}',
                'error': str(e)
            }
    
    def _generate_user_file_content(self, profile: UserProfile) -> str:
        """Generate initial content for user memory file"""
        content = f"""# USER {profile.phone_number}

## Profile
- **Created:** {profile.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Name:** {profile.name or 'Not provided'}
- **Phone:** {profile.phone_number}
- **Security Level:** {profile.security_level}
- **Last Updated:** {profile.last_updated.strftime('%Y-%m-%d %H:%M:%S')}

## Preferences
```yaml
{yaml.dump(profile.preferences, default_flow_style=False)}
```

## Contacts
{chr(10).join([f"- {contact}" for contact in profile.contacts]) if profile.contacts else "- No contacts added yet"}

---

## Memory Entries

### Chronological Memories
*Timeline of events and conversations*

### General Information
*Facts, preferences, and general knowledge*

### Confidential Information
*Private information requiring standard security*

### Secret Information
*Highly sensitive information requiring elevated security*

### Ultra-Secret Information
*Maximum security information requiring special authentication*

---

*File created by Memory System Phase 2 - MD File Manager*
"""
        return content
    
    async def create_contact_file(self, contact_name: str, user_phone: str, 
                                 initial_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new contact memory file"""
        try:
            file_path = self._get_contact_file_path(contact_name)
            
            if file_path.exists():
                logger.info(f"Contact file already exists: {contact_name}")
                return {
                    'success': True,
                    'message': 'Contact file already exists',
                    'file_path': str(file_path)
                }
            
            # Create initial content
            content = f"""# Contact: {contact_name}

## Profile
- **Name:** {contact_name}
- **Associated User:** {user_phone}
- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Information
{yaml.dump(initial_info or {}, default_flow_style=False)}

## Conversation History

### Recent Interactions
*Most recent conversations and interactions*

### Important Information
*Key facts and details about this contact*

### Relationship Context
*Nature of relationship and interaction patterns*

---

*Contact file created by Memory System Phase 2*
"""
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            logger.info(f"✅ Created contact file: {contact_name}")
            
            return {
                'success': True,
                'message': 'Contact file created successfully',
                'file_path': str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to create contact file for {contact_name}: {e}")
            return {
                'success': False,
                'message': f'Failed to create contact file: {str(e)}',
                'error': str(e)
            }
    
    async def update_file(self, phone_number: str, message: str, tag: MemoryTag, 
                         source: str, context: Optional[str] = None,
                         related_contacts: Optional[List[str]] = None) -> Dict[str, Any]:
        """Update memory files with new information"""
        try:
            # Create memory entry
            entry = MemoryEntry(
                id=self._generate_entry_id(message, datetime.now()),
                timestamp=datetime.now(),
                content=message,
                tag=tag,
                source=source,
                context=context,
                confidence_score=1.0
            )
            
            # Files to update
            files_updated = []
            
            # 1. Update user's main file
            user_result = await self._update_user_file(phone_number, entry)
            if user_result['success']:
                files_updated.append(user_result['file_path'])
            
            # 2. Update contact files if related contacts are mentioned
            if related_contacts:
                for contact in related_contacts:
                    # Ensure contact file exists
                    await self.create_contact_file(contact, phone_number)
                    
                    # Update contact file
                    contact_result = await self._update_contact_file(contact, entry, phone_number)
                    if contact_result['success']:
                        files_updated.append(contact_result['file_path'])
                    
                    # Update relationship file
                    relationship_result = await self._update_relationship_file(
                        phone_number, contact, entry
                    )
                    if relationship_result['success']:
                        files_updated.append(relationship_result['file_path'])
            
            # 3. Update topic files if applicable
            topics = self._extract_topics(message)
            for topic in topics:
                topic_result = await self._update_topic_file(topic, entry, phone_number)
                if topic_result['success']:
                    files_updated.append(topic_result['file_path'])
            
            logger.info(f"📝 Updated {len(files_updated)} files for entry: {entry.id}")
            
            return {
                'success': True,
                'message': f'Updated {len(files_updated)} files successfully',
                'entry_id': entry.id,
                'files_updated': files_updated,
                'entry': asdict(entry)
            }
            
        except Exception as e:
            logger.error(f"Failed to update files: {e}")
            return {
                'success': False,
                'message': f'Failed to update files: {str(e)}',
                'error': str(e)
            }
    
    async def _update_user_file(self, phone_number: str, entry: MemoryEntry) -> Dict[str, Any]:
        """Update user's main memory file"""
        try:
            file_path = self._get_user_file_path(phone_number)
            
            # Ensure file exists
            if not file_path.exists():
                await self.create_user_file(phone_number)
            
            # Read current content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Generate entry markdown
            entry_md = self._generate_entry_markdown(entry)
            
            # Find appropriate section based on tag
            section_map = {
                MemoryTag.CHRONOLOGICAL: "### Chronological Memories",
                MemoryTag.GENERAL: "### General Information",
                MemoryTag.CONFIDENTIAL: "### Confidential Information",
                MemoryTag.SECRET: "### Secret Information",
                MemoryTag.ULTRA_SECRET: "### Ultra-Secret Information"
            }
            
            section_header = section_map[entry.tag]
            
            # Insert entry in appropriate section
            if section_header in content:
                # Find the section and add entry
                lines = content.split('\n')
                section_index = -1
                
                for i, line in enumerate(lines):
                    if line.strip() == section_header:
                        section_index = i
                        break
                
                if section_index != -1:
                    # Find next section or end of file
                    insert_index = len(lines)
                    for i in range(section_index + 1, len(lines)):
                        if lines[i].startswith('###') or lines[i].startswith('---'):
                            insert_index = i
                            break
                    
                    # Insert entry
                    lines.insert(insert_index, entry_md)
                    lines.insert(insert_index + 1, "")
                    content = '\n'.join(lines)
            else:
                # Append to end of file
                content += f"\n\n{section_header}\n{entry_md}\n"
            
            # Update last modified timestamp
            content = re.sub(
                r'(\*\*Last Updated:\*\*) [^\n]+',
                f'\\1 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                content
            )
            
            # Write updated content
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return {
                'success': True,
                'file_path': str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to update user file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _update_contact_file(self, contact_name: str, entry: MemoryEntry, 
                                  user_phone: str) -> Dict[str, Any]:
        """Update contact's memory file"""
        try:
            file_path = self._get_contact_file_path(contact_name)
            
            # Read current content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Generate entry markdown
            entry_md = self._generate_entry_markdown(entry, include_source=True)
            
            # Add to Recent Interactions section
            if "### Recent Interactions" in content:
                content = content.replace(
                    "### Recent Interactions\n*Most recent conversations and interactions*",
                    f"### Recent Interactions\n*Most recent conversations and interactions*\n\n{entry_md}"
                )
            else:
                content += f"\n\n### Recent Interactions\n{entry_md}\n"
            
            # Update last modified
            content = re.sub(
                r'(\*\*Last Updated:\*\*) [^\n]+',
                f'\\1 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                content
            )
            
            # Write updated content
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return {
                'success': True,
                'file_path': str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to update contact file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _update_relationship_file(self, user_phone: str, contact_name: str, 
                                       entry: MemoryEntry) -> Dict[str, Any]:
        """Update relationship memory file"""
        try:
            file_path = self._get_relationship_file_path(user_phone, contact_name)
            
            # Create file if it doesn't exist
            if not file_path.exists():
                content = f"""# Relationship: {user_phone} ↔ {contact_name}

## Relationship Profile
- **User:** {user_phone}
- **Contact:** {contact_name}
- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Interaction History

"""
            else:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
            
            # Generate entry markdown
            entry_md = self._generate_entry_markdown(entry, include_source=True)
            
            # Add to Interaction History
            if "## Interaction History" in content:
                content = content.replace(
                    "## Interaction History\n",
                    f"## Interaction History\n\n{entry_md}\n"
                )
            else:
                content += f"\n\n## Interaction History\n{entry_md}\n"
            
            # Update last modified
            content = re.sub(
                r'(\*\*Last Updated:\*\*) [^\n]+',
                f'\\1 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                content
            )
            
            # Write updated content
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return {
                'success': True,
                'file_path': str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to update relationship file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _update_topic_file(self, topic: str, entry: MemoryEntry, 
                                user_phone: str) -> Dict[str, Any]:
        """Update topic memory file"""
        try:
            file_path = self._get_topic_file_path(topic)
            
            # Create file if it doesn't exist
            if not file_path.exists():
                content = f"""# Topic: {topic.title()}

## Topic Information
- **Topic:** {topic.title()}
- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Related Entries

"""
            else:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
            
            # Generate entry markdown
            entry_md = self._generate_entry_markdown(entry, include_source=True)
            
            # Add to Related Entries
            if "## Related Entries" in content:
                content = content.replace(
                    "## Related Entries\n",
                    f"## Related Entries\n\n{entry_md}\n"
                )
            else:
                content += f"\n\n## Related Entries\n{entry_md}\n"
            
            # Write updated content
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return {
                'success': True,
                'file_path': str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to update topic file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_entry_markdown(self, entry: MemoryEntry, include_source: bool = False) -> str:
        """Generate markdown for a memory entry"""
        timestamp_str = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        md = f"""#### {entry.id}
**Time:** {timestamp_str}  
**Tag:** `#{entry.tag.value}`  
"""
        
        if include_source:
            md += f"**Source:** {entry.source}  \n"
        
        if entry.context:
            md += f"**Context:** {entry.context}  \n"
        
        md += f"**Confidence:** {entry.confidence_score:.2f}  \n\n"
        md += f"{entry.content}\n"
        
        if entry.related_entries:
            md += f"\n*Related: {', '.join(entry.related_entries)}*\n"
        
        return md
    
    def _extract_topics(self, message: str) -> List[str]:
        """Extract topics from message content"""
        # Simple topic extraction - can be enhanced with NLP
        topics = []
        
        # Common topic keywords
        topic_keywords = {
            'work': ['work', 'job', 'office', 'meeting', 'project', 'boss', 'colleague'],
            'family': ['family', 'mom', 'dad', 'mother', 'father', 'sister', 'brother', 'wife', 'husband'],
            'health': ['doctor', 'hospital', 'medicine', 'health', 'sick', 'appointment'],
            'finance': ['money', 'bank', 'payment', 'salary', 'investment', 'budget'],
            'travel': ['travel', 'trip', 'vacation', 'flight', 'hotel', 'visit'],
            'food': ['restaurant', 'dinner', 'lunch', 'breakfast', 'cooking', 'recipe'],
            'shopping': ['buy', 'purchase', 'shopping', 'store', 'mall', 'online']
        }
        
        message_lower = message.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    async def get_user_memories(self, phone_number: str, tag: Optional[MemoryTag] = None,
                               limit: int = 50) -> Dict[str, Any]:
        """Retrieve user memories with optional filtering"""
        try:
            file_path = self._get_user_file_path(phone_number)
            
            if not file_path.exists():
                return {
                    'success': False,
                    'message': 'User file not found'
                }
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Parse memories from content
            memories = self._parse_memories_from_content(content, tag, limit)
            
            return {
                'success': True,
                'memories': memories,
                'count': len(memories)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user memories: {e}")
            return {
                'success': False,
                'message': f'Failed to retrieve memories: {str(e)}',
                'error': str(e)
            }
    
    def _parse_memories_from_content(self, content: str, tag: Optional[MemoryTag] = None,
                                   limit: int = 50) -> List[Dict[str, Any]]:
        """Parse memory entries from file content"""
        memories = []
        lines = content.split('\n')
        
        current_entry = None
        in_entry = False
        
        for line in lines:
            if line.startswith('#### mem_'):
                # Start of new entry
                if current_entry:
                    memories.append(current_entry)
                
                current_entry = {
                    'id': line[4:].strip(),
                    'content': '',
                    'metadata': {}
                }
                in_entry = True
                
            elif in_entry and line.startswith('**'):
                # Metadata line
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.replace('**', '').strip().lower()
                    value = value.strip()
                    current_entry['metadata'][key] = value
                    
            elif in_entry and line.strip() and not line.startswith('*'):
                # Content line
                current_entry['content'] += line + '\n'
                
            elif in_entry and (line.startswith('####') or line.startswith('###')):
                # End of entry
                if current_entry:
                    memories.append(current_entry)
                    current_entry = None
                in_entry = False
        
        # Add last entry if exists
        if current_entry:
            memories.append(current_entry)
        
        # Filter by tag if specified
        if tag:
            memories = [m for m in memories if m.get('metadata', {}).get('tag') == f'#{tag.value}']
        
        # Sort by timestamp (newest first) and limit
        memories.sort(key=lambda x: x.get('metadata', {}).get('time', ''), reverse=True)
        
        return memories[:limit]
    
    async def search_memories(self, phone_number: str, query: str, 
                             tag: Optional[MemoryTag] = None) -> Dict[str, Any]:
        """Search memories by content"""
        try:
            memories_result = await self.get_user_memories(phone_number, tag)
            
            if not memories_result['success']:
                return memories_result
            
            memories = memories_result['memories']
            query_lower = query.lower()
            
            # Simple text search - can be enhanced with semantic search
            matching_memories = []
            for memory in memories:
                content = memory.get('content', '').lower()
                if query_lower in content:
                    # Calculate relevance score
                    score = content.count(query_lower) / len(content.split())
                    memory['relevance_score'] = score
                    matching_memories.append(memory)
            
            # Sort by relevance
            matching_memories.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            return {
                'success': True,
                'memories': matching_memories,
                'count': len(matching_memories),
                'query': query
            }
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return {
                'success': False,
                'message': f'Failed to search memories: {str(e)}',
                'error': str(e)
            }
    
    async def get_file_stats(self, phone_number: str) -> Dict[str, Any]:
        """Get statistics about user's memory files"""
        try:
            stats = {
                'user_file_exists': False,
                'contact_files': 0,
                'relationship_files': 0,
                'topic_files': 0,
                'total_entries': 0,
                'entries_by_tag': {},
                'file_sizes': {},
                'last_updated': None
            }
            
            # Check user file
            user_file = self._get_user_file_path(phone_number)
            if user_file.exists():
                stats['user_file_exists'] = True
                stats['file_sizes']['user'] = user_file.stat().st_size
                stats['last_updated'] = datetime.fromtimestamp(user_file.stat().st_mtime)
                
                # Count entries in user file
                memories = await self.get_user_memories(phone_number)
                if memories['success']:
                    stats['total_entries'] = memories['count']
                    
                    # Count by tag
                    for memory in memories['memories']:
                        tag = memory.get('metadata', {}).get('tag', 'unknown')
                        stats['entries_by_tag'][tag] = stats['entries_by_tag'].get(tag, 0) + 1
            
            # Count contact files
            sanitized_phone = self._sanitize_filename(phone_number)
            for file_path in self.contacts_dir.glob("*.md"):
                stats['contact_files'] += 1
            
            # Count relationship files
            for file_path in self.relationships_dir.glob(f"{sanitized_phone}_*.md"):
                stats['relationship_files'] += 1
            
            # Count topic files
            stats['topic_files'] = len(list(self.topics_dir.glob("*.md")))
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get file stats: {e}")
            return {
                'success': False,
                'message': f'Failed to get file stats: {str(e)}',
                'error': str(e)
            }

# Example usage and testing
async def main():
    """Test the MD File Manager"""
    manager = MDFileManager()
    
    # Test user creation
    result = await manager.create_user_file(
        phone_number="+1234567890",
        name="John Doe",
        initial_data={"timezone": "UTC", "language": "en"}
    )
    print("User creation:", result)
    
    # Test memory update
    result = await manager.update_file(
        phone_number="+1234567890",
        message="Remember to call mom about dinner plans for Sunday",
        tag=MemoryTag.CHRONOLOGICAL,
        source="+1234567890",
        context="Family planning",
        related_contacts=["Mom"]
    )
    print("Memory update:", result)
    
    # Test memory retrieval
    result = await manager.get_user_memories("+1234567890")
    print("Memory retrieval:", result)
    
    # Test search
    result = await manager.search_memories("+1234567890", "dinner")
    print("Memory search:", result)
    
    # Test stats
    result = await manager.get_file_stats("+1234567890")
    print("File stats:", result)

if __name__ == "__main__":
    asyncio.run(main())

