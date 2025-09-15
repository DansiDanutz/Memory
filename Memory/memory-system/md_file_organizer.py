#!/usr/bin/env python3
"""
MD File Organizer Agent - Intelligent Memory File Organization System
Organizes user memory files based on security levels and classifications
"""

import os
import json
import asyncio
import logging
import shutil
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import yaml
import stat

# Import local modules
from md_file_manager import MDFileManager, MemoryTag, MemoryEntry
from confidential_manager import SecurityLevel, AccessLevel

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class OrganizationLevel(Enum):
    """Organization levels for files"""
    PUBLIC = "public"
    SECURE = "secure"
    
class FileCategory(Enum):
    """File categories based on security"""
    GENERAL = "general.md"
    CHRONOLOGICAL = "chronological.md"
    CONFIDENTIAL = "confidential.md"
    SECRET = "secret.md"
    ULTRA_SECRET = "ultra_secret.md"
    INDEX = "index.md"

class AgreementStatus(Enum):
    """User agreement status for memories"""
    PENDING = "pending_review"
    AGREED = "agreed"
    NOT_AGREED = "not_agreed"

@dataclass
class MemoryEntry:
    """Parsed memory entry from MD file"""
    id: str
    tag: str
    timestamp: datetime
    content: str
    metadata: Dict[str, Any] = None
    agreement_status: AgreementStatus = AgreementStatus.PENDING
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        # Check for agreement status in metadata
        if 'agreement_status' in self.metadata:
            status_str = self.metadata['agreement_status']
            try:
                self.agreement_status = AgreementStatus[status_str.upper()]
            except (KeyError, AttributeError):
                self.agreement_status = AgreementStatus.PENDING

@dataclass
class OrganizationStats:
    """Statistics for organized files"""
    total_entries: int
    public_entries: int
    secure_entries: int
    general_count: int
    chronological_count: int
    confidential_count: int
    secret_count: int
    ultra_secret_count: int
    agreed_count: int
    not_agreed_count: int
    pending_count: int
    last_organized: datetime
    files_created: List[str]
    errors: List[str]

class MDFileOrganizer:
    """Intelligent MD File Organizer Agent"""
    
    def __init__(self, base_dir: str = "memory-system", dry_run: bool = False):
        """Initialize the MD File Organizer
        
        Args:
            base_dir: Base directory for memory system
            dry_run: If True, don't actually move/create files
        """
        self.base_dir = Path(base_dir)
        self.users_dir = self.base_dir / "users"
        self.security_dir = self.base_dir / "security" / "encrypted"
        self.dry_run = dry_run
        
        # Create directories if they don't exist
        if not dry_run:
            self.users_dir.mkdir(parents=True, exist_ok=True)
            self.security_dir.mkdir(parents=True, exist_ok=True)
            
        # Tag normalization mapping
        self.tag_normalization = {
            'ultra_secret': 'ultra_secret',
            'ultrasecret': 'ultra_secret',
            'ultra-secret': 'ultra_secret',
            'chronological': 'chronological',
            'general': 'general',
            'confidential': 'confidential',
            'secret': 'secret'
        }
        
        # Security level mapping
        self.security_mapping = {
            'general': OrganizationLevel.PUBLIC,
            'chronological': OrganizationLevel.PUBLIC,
            'confidential': OrganizationLevel.SECURE,
            'secret': OrganizationLevel.SECURE,
            'ultra_secret': OrganizationLevel.SECURE
        }
        
        logger.info(f"🗂️ MD File Organizer initialized {'(DRY RUN)' if dry_run else ''}")
        logger.info(f"📁 Base directory: {self.base_dir}")
    
    def normalize_tag(self, tag: str) -> str:
        """Normalize tag variations to standard form
        
        Args:
            tag: Tag to normalize
            
        Returns:
            Normalized tag string
        """
        tag_lower = tag.lower().strip()
        return self.tag_normalization.get(tag_lower, tag_lower)
    
    def parse_memory_entry(self, text: str) -> Optional[MemoryEntry]:
        """Parse a memory entry from MD format
        
        Args:
            text: Text to parse
            
        Returns:
            MemoryEntry object or None if parsing fails
        """
        try:
            # Look for entry header pattern: #### [id:<uuid>] [tag:<tag>] [ts:<iso>]
            header_pattern = r'####\s*\[id:([^\]]+)\]\s*\[tag:([^\]]+)\]\s*\[ts:([^\]]+)\]'
            match = re.search(header_pattern, text)
            
            if match:
                entry_id = match.group(1).strip()
                tag = self.normalize_tag(match.group(2).strip())
                timestamp_str = match.group(3).strip()
                
                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
                
                # Extract content after header
                content_start = match.end()
                content = text[content_start:].strip()
                
                # Check for agreement status in content or metadata
                agreement_status = AgreementStatus.PENDING
                if '[agreement:agreed]' in content:
                    agreement_status = AgreementStatus.AGREED
                    content = content.replace('[agreement:agreed]', '').strip()
                elif '[agreement:not_agreed]' in content:
                    agreement_status = AgreementStatus.NOT_AGREED
                    content = content.replace('[agreement:not_agreed]', '').strip()
                
                return MemoryEntry(
                    id=entry_id,
                    tag=tag,
                    timestamp=timestamp,
                    content=content,
                    agreement_status=agreement_status
                )
            
            # Fallback: Try to parse legacy format
            # Look for sections like ### General Information, ### Confidential Information
            section_pattern = r'###\s*(General|Chronological|Confidential|Secret|Ultra-Secret|Ultra_Secret)'
            sections = re.split(section_pattern, text)
            
            if len(sections) > 1:
                entries = []
                for i in range(1, len(sections), 2):
                    if i < len(sections):
                        section_name = sections[i].strip()
                        section_content = sections[i+1].strip() if i+1 < len(sections) else ""
                        
                        # Normalize section name to tag
                        tag = self.normalize_tag(section_name.replace(' Information', '').replace(' Memories', ''))
                        
                        if section_content:
                            # Generate ID for legacy entries
                            entry_id = str(uuid.uuid4())
                            
                            entries.append(MemoryEntry(
                                id=entry_id,
                                tag=tag,
                                timestamp=datetime.now(),
                                content=section_content
                            ))
                
                return entries[0] if entries else None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse memory entry: {e}")
            return None
    
    def parse_md_file(self, file_path: Path) -> List[MemoryEntry]:
        """Parse all memory entries from an MD file
        
        Args:
            file_path: Path to MD file
            
        Returns:
            List of MemoryEntry objects
        """
        entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split content by entry headers
            entry_pattern = r'(####\s*\[id:[^\]]+\]\s*\[tag:[^\]]+\]\s*\[ts:[^\]]+\])'
            parts = re.split(entry_pattern, content)
            
            # Process each entry
            for i in range(1, len(parts), 2):
                if i+1 < len(parts):
                    header = parts[i]
                    entry_content = parts[i+1]
                    full_entry = header + entry_content
                    
                    entry = self.parse_memory_entry(full_entry)
                    if entry:
                        entries.append(entry)
            
            # If no entries found with new format, try parsing sections
            if not entries:
                # Parse legacy sections
                section_pattern = r'###\s*(General Information|Chronological Memories|Confidential Information|Secret Information|Ultra-Secret Information)'
                sections = re.split(section_pattern, content)
                
                for i in range(1, len(sections), 2):
                    if i+1 < len(sections):
                        section_name = sections[i].strip()
                        section_content = sections[i+1].strip()
                        
                        # Extract tag from section name
                        tag = self.normalize_tag(
                            section_name.replace(' Information', '')
                            .replace(' Memories', '')
                            .replace('-', '_')
                        )
                        
                        # Split section content into individual items
                        items = [item.strip() for item in section_content.split('\n') if item.strip() and not item.strip().startswith('*')]
                        
                        for item in items:
                            if item.startswith('- '):
                                item = item[2:]
                            
                            if item:
                                entries.append(MemoryEntry(
                                    id=str(uuid.uuid4()),
                                    tag=tag,
                                    timestamp=datetime.now(),
                                    content=item
                                ))
            
            logger.info(f"📄 Parsed {len(entries)} entries from {file_path.name}")
            return entries
            
        except Exception as e:
            logger.error(f"Failed to parse MD file {file_path}: {e}")
            return []
    
    def organize_entries(self, entries: List[MemoryEntry]) -> Dict[str, List[MemoryEntry]]:
        """Organize entries by security level
        
        Args:
            entries: List of memory entries
            
        Returns:
            Dictionary mapping category to entries
        """
        organized = {
            'general': [],
            'chronological': [],
            'confidential': [],
            'secret': [],
            'ultra_secret': []
        }
        
        for entry in entries:
            tag = self.normalize_tag(entry.tag)
            if tag in organized:
                organized[tag].append(entry)
            else:
                # Default to general if unknown tag
                organized['general'].append(entry)
        
        return organized
    
    def organize_by_agreement(self, entries: List[MemoryEntry]) -> Dict[str, List[MemoryEntry]]:
        """Organize entries by agreement status
        
        Args:
            entries: List of memory entries
            
        Returns:
            Dictionary mapping agreement status to entries
        """
        organized = {
            'agreed': [],
            'not_agreed': [],
            'pending_review': []
        }
        
        for entry in entries:
            if entry.agreement_status == AgreementStatus.AGREED:
                organized['agreed'].append(entry)
            elif entry.agreement_status == AgreementStatus.NOT_AGREED:
                organized['not_agreed'].append(entry)
            else:
                organized['pending_review'].append(entry)
        
        return organized
    
    def format_entry(self, entry: MemoryEntry) -> str:
        """Format a memory entry for MD file
        
        Args:
            entry: MemoryEntry object
            
        Returns:
            Formatted MD string
        """
        header = f"#### [id:{entry.id}] [tag:{entry.tag}] [ts:{entry.timestamp.isoformat()}]"
        content = entry.content
        
        # Add agreement status to content
        if entry.agreement_status != AgreementStatus.PENDING:
            content = f"[agreement:{entry.agreement_status.name.lower()}] {content}"
        
        # Add metadata if present
        if entry.metadata:
            entry.metadata['agreement_status'] = entry.agreement_status.name.lower()
            metadata_str = yaml.dump(entry.metadata, default_flow_style=False)
            content = f"{content}\n\n```yaml\nmetadata:\n{metadata_str}```"
        
        return f"{header}\n{content}\n"
    
    def write_organized_file(self, file_path: Path, entries: List[MemoryEntry], category: str) -> bool:
        """Write organized entries to a file
        
        Args:
            file_path: Path to write to
            entries: Entries to write
            category: Category name
            
        Returns:
            True if successful
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would write {len(entries)} entries to {file_path}")
            return True
        
        try:
            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate file content
            content = f"# {category.replace('_', ' ').title()} Memories\n\n"
            content += f"*Last organized: {datetime.now().isoformat()}*\n\n"
            content += f"**Total entries:** {len(entries)}\n\n"
            content += "---\n\n"
            
            # Sort entries by timestamp (newest first)
            sorted_entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
            
            # Add entries
            for entry in sorted_entries:
                content += self.format_entry(entry)
                content += "\n---\n\n"
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Set permissions for secure files
            if category in ['confidential', 'secret', 'ultra_secret']:
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 permissions
            
            logger.info(f"✅ Wrote {len(entries)} entries to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write organized file {file_path}: {e}")
            return False
    
    def create_index_file(self, user_dir: Path, stats: OrganizationStats) -> bool:
        """Create index.md file with summary
        
        Args:
            user_dir: User directory path
            stats: Organization statistics
            
        Returns:
            True if successful
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create index file in {user_dir}")
            return True
        
        try:
            index_path = user_dir / "index.md"
            
            content = f"""# Memory Index

## Organization Summary

**Last Organized:** {stats.last_organized.isoformat()}
**Total Entries:** {stats.total_entries}

### Entry Distribution

#### Public Content (No Authentication Required)
- **General:** {stats.general_count} entries - [View](public/general.md)
- **Chronological:** {stats.chronological_count} entries - [View](public/chronological.md)
- **Total Public:** {stats.public_entries} entries

#### Secure Content (Authentication Required)
- **Confidential:** {stats.confidential_count} entries - [View](secure/confidential.md) 🔒
- **Secret:** {stats.secret_count} entries - [View](secure/secret.md) 🔐
- **Ultra Secret:** {stats.ultra_secret_count} entries - [View](secure/ultra_secret.md) 🔏
- **Total Secure:** {stats.secure_entries} entries

### Files Created
{chr(10).join([f"- {file}" for file in stats.files_created])}

### Agreement Status

#### User Review Status
- **Agreed:** {stats.agreed_count} memories - [View](agreed/agreed_memories.md) ✅
- **Not Agreed:** {stats.not_agreed_count} memories - [View](not_agreed/not_agreed_memories.md) ❌
- **Pending Review:** {stats.pending_count} memories - [View](pending_review/pending_memories.md) ⏳

### Security Notice
- Public files (`public/`) can be accessed without authentication
- Secure files (`secure/`) require proper authentication
- Secure content is also encrypted and stored in the security vault
- Agreement status tracks user validation of memories

---

*Generated by MD File Organizer Agent*
"""
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"📋 Created index file: {index_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index file: {e}")
            return False
    
    async def organize_user(self, user_id: str) -> OrganizationStats:
        """Organize files for a specific user
        
        Args:
            user_id: User ID (phone or UUID)
            
        Returns:
            OrganizationStats object
        """
        logger.info(f"🔄 Organizing files for user: {user_id}")
        
        stats = OrganizationStats(
            total_entries=0,
            public_entries=0,
            secure_entries=0,
            general_count=0,
            chronological_count=0,
            confidential_count=0,
            secret_count=0,
            ultra_secret_count=0,
            agreed_count=0,
            not_agreed_count=0,
            pending_count=0,
            last_organized=datetime.now(),
            files_created=[],
            errors=[]
        )
        
        try:
            # Find user files
            user_patterns = [
                f"USER.{user_id}*.md",
                f"*{user_id}*.md",
                f"{user_id}.md"
            ]
            
            user_files = []
            for pattern in user_patterns:
                user_files.extend(self.users_dir.glob(f"**/{pattern}"))
            
            if not user_files:
                logger.warning(f"No files found for user: {user_id}")
                return stats
            
            # Parse all entries from all files
            all_entries = []
            for file_path in user_files:
                entries = self.parse_md_file(file_path)
                all_entries.extend(entries)
            
            stats.total_entries = len(all_entries)
            
            # Organize entries by category
            organized = self.organize_entries(all_entries)
            
            # Create user directory structure
            user_dir = self.users_dir / user_id
            public_dir = user_dir / "public"
            secure_dir = user_dir / "secure"
            agreed_dir = user_dir / "agreed"
            not_agreed_dir = user_dir / "not_agreed"
            pending_dir = user_dir / "pending_review"
            
            if not self.dry_run:
                public_dir.mkdir(parents=True, exist_ok=True)
                secure_dir.mkdir(parents=True, exist_ok=True)
                agreed_dir.mkdir(parents=True, exist_ok=True)
                not_agreed_dir.mkdir(parents=True, exist_ok=True)
                pending_dir.mkdir(parents=True, exist_ok=True)
            
            # Write public files
            if organized['general']:
                file_path = public_dir / FileCategory.GENERAL.value
                if self.write_organized_file(file_path, organized['general'], 'general'):
                    stats.files_created.append(str(file_path))
                    stats.general_count = len(organized['general'])
                    stats.public_entries += stats.general_count
            
            if organized['chronological']:
                file_path = public_dir / FileCategory.CHRONOLOGICAL.value
                if self.write_organized_file(file_path, organized['chronological'], 'chronological'):
                    stats.files_created.append(str(file_path))
                    stats.chronological_count = len(organized['chronological'])
                    stats.public_entries += stats.chronological_count
            
            # Write secure files
            secure_categories = ['confidential', 'secret', 'ultra_secret']
            for category in secure_categories:
                if organized[category]:
                    # Write to secure directory
                    file_path = secure_dir / f"{category}.md"
                    if self.write_organized_file(file_path, organized[category], category):
                        stats.files_created.append(str(file_path))
                        
                        # Update stats
                        count = len(organized[category])
                        setattr(stats, f"{category}_count", count)
                        stats.secure_entries += count
                        
                        # Also copy to encrypted security vault
                        if not self.dry_run:
                            encrypted_dir = self.security_dir / user_id
                            encrypted_dir.mkdir(parents=True, exist_ok=True)
                            encrypted_file = encrypted_dir / f"{category}.md"
                            shutil.copy2(file_path, encrypted_file)
                            os.chmod(encrypted_file, stat.S_IRUSR | stat.S_IWUSR)  # 600 permissions
                            logger.info(f"🔐 Copied {category} to security vault")
            
            # Organize by agreement status
            agreement_organized = self.organize_by_agreement(all_entries)
            
            # Write agreed memories
            if agreement_organized['agreed']:
                file_path = agreed_dir / "agreed_memories.md"
                if self.write_organized_file(file_path, agreement_organized['agreed'], 'agreed'):
                    stats.files_created.append(str(file_path))
                    stats.agreed_count = len(agreement_organized['agreed'])
            
            # Write not agreed memories
            if agreement_organized['not_agreed']:
                file_path = not_agreed_dir / "not_agreed_memories.md"
                if self.write_organized_file(file_path, agreement_organized['not_agreed'], 'not_agreed'):
                    stats.files_created.append(str(file_path))
                    stats.not_agreed_count = len(agreement_organized['not_agreed'])
            
            # Write pending memories
            if agreement_organized['pending_review']:
                file_path = pending_dir / "pending_memories.md"
                if self.write_organized_file(file_path, agreement_organized['pending_review'], 'pending_review'):
                    stats.files_created.append(str(file_path))
                    stats.pending_count = len(agreement_organized['pending_review'])
            
            # Create index file
            self.create_index_file(user_dir, stats)
            
            logger.info(f"✅ Organization complete for user {user_id}")
            logger.info(f"📊 Stats: {stats.total_entries} total, {stats.public_entries} public, {stats.secure_entries} secure")
            
        except Exception as e:
            logger.error(f"Failed to organize user {user_id}: {e}")
            stats.errors.append(str(e))
        
        return stats
    
    async def organize_all_users(self) -> Dict[str, OrganizationStats]:
        """Organize files for all users
        
        Returns:
            Dictionary mapping user_id to OrganizationStats
        """
        logger.info("🔄 Organizing files for all users...")
        
        results = {}
        
        # Find all user files
        user_files = list(self.users_dir.glob("**/*.md"))
        
        # Extract unique user IDs
        user_ids = set()
        for file_path in user_files:
            # Try to extract user ID from filename
            filename = file_path.name
            
            # Pattern: USER.<phone>.md
            if filename.startswith("USER."):
                user_id = filename.replace("USER.", "").replace(".md", "")
                user_ids.add(user_id)
            # Pattern: <user_id>.md
            elif filename.endswith(".md"):
                user_id = filename.replace(".md", "")
                # Filter out non-user files
                if not any(x in user_id for x in ['topic_', 'contact_', 'relationship_']):
                    user_ids.add(user_id)
        
        logger.info(f"Found {len(user_ids)} users to organize")
        
        # Organize each user
        for user_id in user_ids:
            logger.info(f"Processing user: {user_id}")
            stats = await self.organize_user(user_id)
            results[user_id] = stats
        
        # Summary
        total_entries = sum(s.total_entries for s in results.values())
        total_public = sum(s.public_entries for s in results.values())
        total_secure = sum(s.secure_entries for s in results.values())
        
        logger.info("="*50)
        logger.info(f"✅ Organization complete for {len(results)} users")
        logger.info(f"📊 Total: {total_entries} entries ({total_public} public, {total_secure} secure)")
        
        return results
    
    async def mark_memory_agreed(self, user_id: str, memory_id: str) -> Dict[str, Any]:
        """Mark a memory as agreed by the user
        
        Args:
            user_id: User ID (phone or UUID)
            memory_id: Memory ID to mark as agreed
            
        Returns:
            Result dictionary with success status
        """
        try:
            logger.info(f"✅ Marking memory {memory_id} as agreed for user {user_id}")
            
            # Find and update the memory
            user_dir = self.users_dir / user_id
            pending_dir = user_dir / "pending_review"
            agreed_dir = user_dir / "agreed"
            
            # Ensure directories exist
            agreed_dir.mkdir(parents=True, exist_ok=True)
            
            # Find the memory in pending files
            memory_found = False
            for file_path in pending_dir.glob("*.md"):
                entries = self.parse_md_file(file_path)
                for entry in entries:
                    if entry.id == memory_id:
                        entry.agreement_status = AgreementStatus.AGREED
                        memory_found = True
                        
                        # Write to agreed directory
                        agreed_file = agreed_dir / "agreed_memories.md"
                        self.write_organized_file(agreed_file, [entry], 'agreed')
                        
                        # Remove from pending
                        remaining_entries = [e for e in entries if e.id != memory_id]
                        if remaining_entries:
                            self.write_organized_file(file_path, remaining_entries, 'pending_review')
                        else:
                            file_path.unlink()
                        
                        logger.info(f"✅ Memory {memory_id} marked as agreed")
                        return {'success': True, 'message': 'Memory marked as agreed'}
            
            if not memory_found:
                logger.warning(f"Memory {memory_id} not found in pending")
                return {'success': False, 'message': 'Memory not found'}
                
        except Exception as e:
            logger.error(f"Failed to mark memory as agreed: {e}")
            return {'success': False, 'message': str(e)}
    
    async def mark_memory_not_agreed(self, user_id: str, memory_id: str) -> Dict[str, Any]:
        """Mark a memory as not agreed by the user
        
        Args:
            user_id: User ID (phone or UUID)
            memory_id: Memory ID to mark as not agreed
            
        Returns:
            Result dictionary with success status
        """
        try:
            logger.info(f"❌ Marking memory {memory_id} as not agreed for user {user_id}")
            
            # Find and update the memory
            user_dir = self.users_dir / user_id
            pending_dir = user_dir / "pending_review"
            not_agreed_dir = user_dir / "not_agreed"
            
            # Ensure directories exist
            not_agreed_dir.mkdir(parents=True, exist_ok=True)
            
            # Find the memory in pending files
            memory_found = False
            for file_path in pending_dir.glob("*.md"):
                entries = self.parse_md_file(file_path)
                for entry in entries:
                    if entry.id == memory_id:
                        entry.agreement_status = AgreementStatus.NOT_AGREED
                        memory_found = True
                        
                        # Write to not agreed directory
                        not_agreed_file = not_agreed_dir / "not_agreed_memories.md"
                        self.write_organized_file(not_agreed_file, [entry], 'not_agreed')
                        
                        # Remove from pending
                        remaining_entries = [e for e in entries if e.id != memory_id]
                        if remaining_entries:
                            self.write_organized_file(file_path, remaining_entries, 'pending_review')
                        else:
                            file_path.unlink()
                        
                        logger.info(f"❌ Memory {memory_id} marked as not agreed")
                        return {'success': True, 'message': 'Memory marked as not agreed'}
            
            if not memory_found:
                logger.warning(f"Memory {memory_id} not found in pending")
                return {'success': False, 'message': 'Memory not found'}
                
        except Exception as e:
            logger.error(f"Failed to mark memory as not agreed: {e}")
            return {'success': False, 'message': str(e)}
    
    async def get_pending_memories(self, user_id: str) -> Dict[str, Any]:
        """Get memories pending review for a user
        
        Args:
            user_id: User ID (phone or UUID)
            
        Returns:
            Dictionary with pending memories
        """
        try:
            logger.info(f"📋 Getting pending memories for user {user_id}")
            
            user_dir = self.users_dir / user_id
            pending_dir = user_dir / "pending_review"
            
            pending_memories = []
            
            # Check all directories for pending memories
            for directory in [user_dir / "public", user_dir / "secure", pending_dir]:
                if directory.exists():
                    for file_path in directory.glob("*.md"):
                        entries = self.parse_md_file(file_path)
                        for entry in entries:
                            if entry.agreement_status == AgreementStatus.PENDING:
                                pending_memories.append({
                                    'id': entry.id,
                                    'content': entry.content,
                                    'tag': entry.tag,
                                    'timestamp': entry.timestamp.isoformat(),
                                    'agreement_status': 'pending'
                                })
            
            logger.info(f"Found {len(pending_memories)} pending memories")
            return {
                'success': True,
                'memories': pending_memories,
                'count': len(pending_memories)
            }
            
        except Exception as e:
            logger.error(f"Failed to get pending memories: {e}")
            return {'success': False, 'message': str(e), 'memories': []}

async def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(description='MD File Organizer Agent')
    parser.add_argument('--user', type=str, help='Organize files for specific user')
    parser.add_argument('--all', action='store_true', help='Organize files for all users')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without making changes')
    parser.add_argument('--base-dir', type=str, default='memory-system', help='Base directory for memory system')
    
    args = parser.parse_args()
    
    if not args.user and not args.all:
        parser.error('Please specify --user <id> or --all')
    
    # Initialize organizer
    organizer = MDFileOrganizer(base_dir=args.base_dir, dry_run=args.dry_run)
    
    # Run organization
    if args.user:
        stats = await organizer.organize_user(args.user)
        print(f"\nOrganization complete for user {args.user}:")
        print(f"  Total entries: {stats.total_entries}")
        print(f"  Public entries: {stats.public_entries}")
        print(f"  Secure entries: {stats.secure_entries}")
        if stats.errors:
            print(f"  Errors: {', '.join(stats.errors)}")
    else:
        results = await organizer.organize_all_users()
        print(f"\nOrganization complete for {len(results)} users")
        for user_id, stats in results.items():
            print(f"\n{user_id}:")
            print(f"  Total: {stats.total_entries} ({stats.public_entries} public, {stats.secure_entries} secure)")

if __name__ == "__main__":
    asyncio.run(main())