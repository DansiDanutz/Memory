#!/usr/bin/env python3
"""
MD Agent - Memory Document Processing Agent
Processes transcript files and categorizes memories using AI
Similar to Circleback functionality
"""

import os
import sys
import json
import logging
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI
import anthropic

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Memory:
    """Represents a categorized memory"""
    content: str
    category: str
    timestamp: datetime
    tags: List[str]
    importance: int
    source: str
    context: Optional[str] = None
    related_memories: Optional[List[str]] = None

class MDAgent:
    """
    Memory Document Agent for processing conversation transcripts
    and categorizing them into organized memory files
    """
    
    # Memory categories based on content type
    CATEGORIES = {
        'personal': {
            'file': 'personal.md',
            'keywords': ['feel', 'think', 'prefer', 'like', 'love', 'hate', 'hobby', 'interest'],
            'description': 'Private thoughts, feelings, preferences, and personal experiences'
        },
        'shared': {
            'file': 'shared.md',
            'keywords': ['together', 'we', 'our', 'meeting', 'event', 'attended', 'visited'],
            'description': 'Joint experiences, shared activities, and mutual memories'
        },
        'important_dates': {
            'file': 'important_dates.md',
            'keywords': ['birthday', 'anniversary', 'deadline', 'appointment', 'schedule'],
            'description': 'Birthdays, anniversaries, and significant dates'
        },
        'notes': {
            'file': 'notes.md',
            'keywords': ['reminder', 'todo', 'task', 'note', 'remember', 'don\'t forget'],
            'description': 'Reminders, tasks, quick notes, and action items'
        },
        'voice': {
            'file': 'voice.md',
            'keywords': ['voice', 'audio', 'recording', 'said', 'told', 'mentioned'],
            'description': 'Voice message references and audio content'
        },
        'media': {
            'file': 'media.md',
            'keywords': ['photo', 'image', 'video', 'document', 'file', 'attachment'],
            'description': 'Photos, documents, and media references'
        },
        'professional': {
            'file': 'professional.md',
            'keywords': ['work', 'job', 'project', 'client', 'business', 'career', 'office'],
            'description': 'Work-related topics, projects, and professional matters'
        },
        'confidential': {
            'file': 'confidential.md',
            'keywords': ['private', 'secret', 'confidential', 'sensitive', 'password'],
            'description': 'Sensitive information requiring special handling'
        }
    }
    
    def __init__(self, base_dir: str = 'data/memories', use_anthropic: bool = False):
        """
        Initialize the MD Agent
        
        Args:
            base_dir: Base directory for memory storage
            use_anthropic: Use Anthropic Claude instead of OpenAI
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize AI clients
        self.use_anthropic = use_anthropic
        if use_anthropic:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.ai_client = anthropic.Anthropic(api_key=api_key)
                self.ai_enabled = True
            else:
                logger.warning("Anthropic API key not found")
                self.ai_enabled = False
        else:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.ai_client = OpenAI(api_key=api_key)
                self.ai_enabled = True
            else:
                logger.warning("OpenAI API key not found")
                self.ai_enabled = False
        
        # Processing statistics
        self.stats = {
            'processed': 0,
            'categorized': 0,
            'errors': 0,
            'last_run': None
        }
        
        logger.info(f"📚 MD Agent initialized - AI: {'Anthropic' if use_anthropic else 'OpenAI'}")
    
    async def process_all_transcripts(self) -> Dict[str, Any]:
        """
        Process all transcript files for all contacts
        
        Returns:
            Processing results summary
        """
        results = {
            'contacts_processed': 0,
            'memories_created': 0,
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Find all contact directories
        contact_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        for contact_dir in contact_dirs:
            try:
                contact_id = contact_dir.name
                logger.info(f"Processing contact: {contact_id}")
                
                # Process transcript file for this contact
                contact_results = await self.process_contact_transcript(contact_id)
                
                results['contacts_processed'] += 1
                results['memories_created'] += contact_results.get('memories_created', 0)
                
            except Exception as e:
                error_msg = f"Error processing {contact_id}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        self.stats['last_run'] = datetime.now()
        return results
    
    async def process_contact_transcript(self, contact_id: str) -> Dict[str, Any]:
        """
        Process transcript file for a specific contact
        
        Args:
            contact_id: Contact identifier
            
        Returns:
            Processing results for this contact
        """
        contact_dir = self.base_dir / contact_id
        transcript_file = contact_dir / 'transcripts.md'
        
        results = {
            'contact_id': contact_id,
            'memories_created': 0,
            'categories_updated': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Check if transcript file exists
        if not transcript_file.exists():
            logger.info(f"No transcript file found for {contact_id}")
            return results
        
        # Read transcript content
        transcript_content = transcript_file.read_text(encoding='utf-8')
        
        # Check if there's content to process
        if not transcript_content.strip() or 'Awaiting Analysis' not in transcript_content:
            logger.info(f"No new content in transcript for {contact_id}")
            return results
        
        # Parse conversations from transcript
        conversations = self.parse_transcript(transcript_content)
        
        if not conversations:
            logger.info(f"No conversations found in transcript for {contact_id}")
            return results
        
        # Process each conversation
        for conv in conversations:
            try:
                # Analyze and categorize using AI
                memories = await self.analyze_conversation(conv, contact_id)
                
                # Store memories in appropriate category files
                for memory in memories:
                    await self.store_memory(contact_id, memory)
                    results['memories_created'] += 1
                    
                    if memory.category not in results['categories_updated']:
                        results['categories_updated'].append(memory.category)
                
                self.stats['processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing conversation: {e}")
                self.stats['errors'] += 1
        
        # Clear transcript file after successful processing
        await self.clear_transcript(contact_id)
        
        return results
    
    def parse_transcript(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse transcript content to extract conversations
        
        Args:
            content: Raw transcript content
            
        Returns:
            List of parsed conversations
        """
        conversations = []
        
        # Pattern to match conversation entries
        pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (Incoming Message|Outgoing Response)\n```\n(.*?)\n```'
        
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            timestamp_str, direction, message = match
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
            conversations.append({
                'timestamp': timestamp,
                'direction': direction,
                'message': message.strip(),
                'raw': f"[{timestamp_str}] {direction}\n{message}"
            })
        
        return conversations
    
    async def analyze_conversation(
        self,
        conversation: Dict[str, Any],
        contact_id: str
    ) -> List[Memory]:
        """
        Analyze a conversation and extract categorized memories
        
        Args:
            conversation: Parsed conversation data
            contact_id: Contact identifier
            
        Returns:
            List of extracted memories
        """
        memories = []
        message = conversation['message']
        timestamp = conversation['timestamp']
        
        if not self.ai_enabled:
            # Fallback to basic categorization
            category = self.basic_categorize(message)
            memory = Memory(
                content=message,
                category=category,
                timestamp=timestamp,
                tags=self.extract_tags(message),
                importance=5,
                source='transcript',
                context=conversation['direction']
            )
            memories.append(memory)
            return memories
        
        # Use AI for advanced analysis
        try:
            if self.use_anthropic:
                analysis = await self.analyze_with_anthropic(message, contact_id)
            else:
                analysis = await self.analyze_with_openai(message, contact_id)
            
            # Create memories from AI analysis
            for item in analysis.get('memories', []):
                memory = Memory(
                    content=item.get('content', message),
                    category=item.get('category', 'notes'),
                    timestamp=timestamp,
                    tags=item.get('tags', []),
                    importance=item.get('importance', 5),
                    source='transcript',
                    context=item.get('context', conversation['direction'])
                )
                memories.append(memory)
                self.stats['categorized'] += 1
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Fallback to basic categorization
            category = self.basic_categorize(message)
            memory = Memory(
                content=message,
                category=category,
                timestamp=timestamp,
                tags=self.extract_tags(message),
                importance=5,
                source='transcript',
                context=conversation['direction']
            )
            memories.append(memory)
        
        return memories
    
    async def analyze_with_openai(
        self,
        message: str,
        contact_id: str
    ) -> Dict[str, Any]:
        """
        Analyze message using OpenAI GPT
        
        Args:
            message: Message content
            contact_id: Contact identifier
            
        Returns:
            Analysis results
        """
        prompt = f"""
        Analyze this conversation message and extract memories to categorize.
        
        Message: "{message}"
        Contact: {contact_id}
        
        Categories available:
        - personal: Private thoughts, feelings, preferences
        - shared: Joint experiences, activities done together
        - important_dates: Birthdays, anniversaries, deadlines
        - notes: Reminders, tasks, quick notes
        - voice: Voice message references
        - media: Photos, documents mentioned
        - professional: Work-related topics
        - confidential: Sensitive information
        
        Return a JSON object with:
        {{
            "memories": [
                {{
                    "content": "extracted memory content",
                    "category": "category name",
                    "tags": ["tag1", "tag2"],
                    "importance": 1-10,
                    "context": "additional context"
                }}
            ]
        }}
        """
        
        response = await asyncio.to_thread(
            self.ai_client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a memory categorization assistant. Extract and categorize important information from conversations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except:
            # Fallback if JSON parsing fails
            return {
                "memories": [{
                    "content": message,
                    "category": "notes",
                    "tags": [],
                    "importance": 5,
                    "context": "Auto-categorized"
                }]
            }
    
    async def analyze_with_anthropic(
        self,
        message: str,
        contact_id: str
    ) -> Dict[str, Any]:
        """
        Analyze message using Anthropic Claude
        
        Args:
            message: Message content
            contact_id: Contact identifier
            
        Returns:
            Analysis results
        """
        prompt = f"""
        Analyze this conversation message and extract memories to categorize.
        
        Message: "{message}"
        Contact: {contact_id}
        
        Categories available:
        - personal: Private thoughts, feelings, preferences
        - shared: Joint experiences, activities done together
        - important_dates: Birthdays, anniversaries, deadlines
        - notes: Reminders, tasks, quick notes
        - voice: Voice message references
        - media: Photos, documents mentioned
        - professional: Work-related topics
        - confidential: Sensitive information
        
        Return a JSON object with:
        {{
            "memories": [
                {{
                    "content": "extracted memory content",
                    "category": "category name",
                    "tags": ["tag1", "tag2"],
                    "importance": 1-10,
                    "context": "additional context"
                }}
            ]
        }}
        """
        
        response = await asyncio.to_thread(
            self.ai_client.messages.create,
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0.7,
            system="You are a memory categorization assistant. Extract and categorize important information from conversations.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            result = json.loads(response.content[0].text)
            return result
        except:
            # Fallback if JSON parsing fails
            return {
                "memories": [{
                    "content": message,
                    "category": "notes",
                    "tags": [],
                    "importance": 5,
                    "context": "Auto-categorized"
                }]
            }
    
    def basic_categorize(self, content: str) -> str:
        """
        Basic keyword-based categorization fallback
        
        Args:
            content: Content to categorize
            
        Returns:
            Category name
        """
        content_lower = content.lower()
        
        # Check each category's keywords
        for category, config in self.CATEGORIES.items():
            for keyword in config['keywords']:
                if keyword in content_lower:
                    return category
        
        # Default to notes
        return 'notes'
    
    def extract_tags(self, content: str) -> List[str]:
        """
        Extract tags from content
        
        Args:
            content: Content to extract tags from
            
        Returns:
            List of tags
        """
        tags = []
        content_lower = content.lower()
        
        # Common tags to look for
        tag_keywords = {
            'urgent': ['urgent', 'asap', 'immediately'],
            'important': ['important', 'critical', 'vital'],
            'work': ['work', 'job', 'office', 'project'],
            'personal': ['personal', 'private', 'family'],
            'reminder': ['remember', 'remind', 'don\'t forget'],
            'meeting': ['meeting', 'appointment', 'schedule']
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                tags.append(tag)
        
        return tags
    
    async def store_memory(self, contact_id: str, memory: Memory) -> None:
        """
        Store a memory in the appropriate category file
        
        Args:
            contact_id: Contact identifier
            memory: Memory to store
        """
        contact_dir = self.base_dir / contact_id
        contact_dir.mkdir(parents=True, exist_ok=True)
        
        # Get category file
        category_config = self.CATEGORIES.get(memory.category, self.CATEGORIES['notes'])
        category_file = contact_dir / category_config['file']
        
        # Create file if it doesn't exist
        if not category_file.exists():
            header = f"""# {memory.category.replace('_', ' ').title()}

## {category_config['description']}

> This file contains {memory.category} memories for contact {contact_id}

---

### Contact Information
- **Contact ID:** {contact_id}
- **Last Updated:** {datetime.now().strftime('%B %d, %Y')}

---

## Memories

"""
            category_file.write_text(header, encoding='utf-8')
        
        # Read existing content
        existing_content = category_file.read_text(encoding='utf-8')
        
        # Format memory entry
        entry = f"""
### 📝 {memory.timestamp.strftime('%Y-%m-%d %H:%M')}
**Content:** {memory.content}
**Importance:** {'⭐' * memory.importance}
**Tags:** {', '.join(memory.tags) if memory.tags else 'None'}
**Source:** {memory.source}
{f'**Context:** {memory.context}' if memory.context else ''}

---
"""
        
        # Append memory to file
        updated_content = existing_content + entry
        category_file.write_text(updated_content, encoding='utf-8')
        
        logger.info(f"Stored memory in {memory.category} for {contact_id}")
    
    async def clear_transcript(self, contact_id: str) -> None:
        """
        Clear transcript file after processing
        
        Args:
            contact_id: Contact identifier
        """
        contact_dir = self.base_dir / contact_id
        transcript_file = contact_dir / 'transcripts.md'
        
        if transcript_file.exists():
            # Create empty transcript with header
            empty_content = f"""# Transcripts

## Raw Conversation Data

> This file contains raw conversation data awaiting analysis and categorization.
> The MD Agent processes this data and distributes it to appropriate categories.

---

### Status: Inbox

**Last Updated:** {datetime.now().strftime('%B %d, %Y')}
**Processing Status:** Awaiting Analysis
**Contact ID:** {contact_id}

---

## Conversation Log

<!-- New conversations will appear here -->

---

## Processing Queue

- [ ] Analyze conversation context
- [ ] Extract memory points
- [ ] Categorize information
- [ ] Distribute to appropriate files

---

## Metadata

- **Entry Count:** 0
- **Awaiting Processing:** 0
- **Last Process Run:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Priority:** Normal
"""
            
            transcript_file.write_text(empty_content, encoding='utf-8')
            logger.info(f"Cleared transcript for {contact_id}")
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics
        
        Returns:
            Statistics dictionary
        """
        return {
            'total_processed': self.stats['processed'],
            'total_categorized': self.stats['categorized'],
            'total_errors': self.stats['errors'],
            'last_run': self.stats['last_run'].isoformat() if self.stats['last_run'] else None,
            'ai_enabled': self.ai_enabled,
            'ai_provider': 'Anthropic' if self.use_anthropic else 'OpenAI'
        }

async def main():
    """Main function for testing"""
    # Initialize MD Agent
    agent = MDAgent(use_anthropic=False)  # Use OpenAI by default
    
    # Process all transcripts
    results = await agent.process_all_transcripts()
    
    # Print results
    print(json.dumps(results, indent=2))
    
    # Get statistics
    stats = await agent.get_processing_stats()
    print("\nProcessing Statistics:")
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    asyncio.run(main())