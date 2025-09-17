"""
MCP Server for MD Files
Model Context Protocol server for exposing MD files to AI agents
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import asyncio
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class MDFile:
    """Represents an MD file with metadata"""
    path: str
    category: str
    content: str
    hash: str
    size: int
    created_at: str
    modified_at: str
    metadata: Dict[str, Any]

class MemoMDMCPServer:
    """
    MCP Server for MD file access and management
    Provides structured access to memory MD files for AI agents
    """
    
    def __init__(self, base_path: str = "app/memory-system"):
        """Initialize MCP server"""
        self.base_path = Path(base_path)
        self.file_cache = {}
        self.category_index = {}
        
        # Security levels for categories
        self.security_levels = {
            "GENERAL": 0,
            "CHRONOLOGICAL": 1,
            "CONFIDENTIAL": 2,
            "SECRET": 3,
            "ULTRA_SECRET": 4
        }
        
        # Initialize file index
        self._build_index()
        
        logger.info(f"✅ MCP Server initialized with base path: {self.base_path}")
    
    def _build_index(self):
        """Build index of all MD files"""
        self.category_index = {
            "GENERAL": [],
            "CHRONOLOGICAL": [],
            "CONFIDENTIAL": [],
            "SECRET": [],
            "ULTRA_SECRET": []
        }
        
        # Scan for MD files
        for category in self.category_index.keys():
            category_path = self.base_path / "users"
            if category_path.exists():
                # Find all category directories
                for user_dir in category_path.iterdir():
                    if user_dir.is_dir():
                        cat_dir = user_dir / category
                        if cat_dir.exists():
                            for md_file in cat_dir.glob("*.md"):
                                file_info = self._get_file_info(md_file)
                                self.category_index[category].append(file_info)
        
        logger.info(f"Indexed {sum(len(files) for files in self.category_index.values())} MD files")
    
    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get file information and metadata"""
        stat = file_path.stat()
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
        
        # Extract category from path
        parts = file_path.parts
        category = "GENERAL"
        for part in parts:
            if part in self.security_levels:
                category = part
                break
        
        return {
            "path": str(file_path),
            "name": file_path.name,
            "category": category,
            "size": stat.st_size,
            "hash": file_hash,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    
    async def list_files(
        self,
        category: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List available MD files
        
        Args:
            category: Filter by category
            user_id: Filter by user ID
            
        Returns:
            List of file metadata
        """
        files = []
        
        if category and category in self.category_index:
            files = self.category_index[category]
        else:
            # Get all files
            for cat_files in self.category_index.values():
                files.extend(cat_files)
        
        # Filter by user if specified
        if user_id:
            files = [f for f in files if user_id in f["path"]]
        
        return files
    
    async def read_file(
        self,
        file_path: str,
        auth_level: int = 0
    ) -> Tuple[bool, Optional[MDFile]]:
        """
        Read an MD file with security check
        
        Args:
            file_path: Path to the file
            auth_level: Authentication level of requester
            
        Returns:
            (success, MDFile or None)
        """
        try:
            path = Path(file_path)
            
            # Security check - determine required level
            required_level = 0
            for category, level in self.security_levels.items():
                if category in file_path:
                    required_level = level
                    break
            
            if auth_level < required_level:
                logger.warning(f"Access denied to {file_path}: auth_level {auth_level} < required {required_level}")
                return False, None
            
            # Check cache
            if file_path in self.file_cache:
                cache_entry = self.file_cache[file_path]
                # Check if file has been modified
                stat = path.stat()
                if cache_entry["modified_at"] == datetime.fromtimestamp(stat.st_mtime).isoformat():
                    return True, cache_entry["content"]
            
            # Read file
            if not path.exists():
                return False, None
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse metadata from content
            metadata = self._extract_metadata(content)
            
            # Get file info
            file_info = self._get_file_info(path)
            
            # Create MDFile object
            md_file = MDFile(
                path=str(path),
                category=file_info["category"],
                content=content,
                hash=file_info["hash"],
                size=file_info["size"],
                created_at=file_info["created_at"],
                modified_at=file_info["modified_at"],
                metadata=metadata
            )
            
            # Cache the file
            self.file_cache[file_path] = {
                "content": md_file,
                "modified_at": file_info["modified_at"]
            }
            
            return True, md_file
            
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return False, None
    
    async def write_file(
        self,
        file_path: str,
        content: str,
        auth_level: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Write or update an MD file
        
        Args:
            file_path: Path to write to
            content: File content
            auth_level: Authentication level of requester
            metadata: Optional metadata to embed
            
        Returns:
            (success, message)
        """
        try:
            path = Path(file_path)
            
            # Security check
            required_level = 0
            for category, level in self.security_levels.items():
                if category in file_path:
                    required_level = level
                    break
            
            if auth_level < required_level:
                return False, f"Insufficient permissions (need level {required_level})"
            
            # Create directory if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add metadata to content
            if metadata:
                content = self._embed_metadata(content, metadata)
            
            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update index
            file_info = self._get_file_info(path)
            category = file_info["category"]
            
            # Remove old entry if exists
            self.category_index[category] = [
                f for f in self.category_index[category]
                if f["path"] != str(path)
            ]
            
            # Add new entry
            self.category_index[category].append(file_info)
            
            # Clear cache
            if file_path in self.file_cache:
                del self.file_cache[file_path]
            
            logger.info(f"Wrote file {file_path}")
            return True, "File written successfully"
            
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return False, str(e)
    
    async def search_files(
        self,
        query: str,
        category: Optional[str] = None,
        auth_level: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search MD files for content
        
        Args:
            query: Search query
            category: Limit to specific category
            auth_level: Authentication level
            
        Returns:
            List of matching files with snippets
        """
        results = []
        query_lower = query.lower()
        
        # Get files to search
        files = await self.list_files(category)
        
        for file_info in files:
            # Check permissions
            required_level = self.security_levels.get(file_info["category"], 0)
            if auth_level < required_level:
                continue
            
            # Read file
            success, md_file = await self.read_file(file_info["path"], auth_level)
            if not success or not md_file:
                continue
            
            # Search content
            content_lower = md_file.content.lower()
            if query_lower in content_lower:
                # Find snippet
                idx = content_lower.find(query_lower)
                start = max(0, idx - 50)
                end = min(len(md_file.content), idx + len(query) + 50)
                snippet = md_file.content[start:end]
                
                if start > 0:
                    snippet = "..." + snippet
                if end < len(md_file.content):
                    snippet = snippet + "..."
                
                results.append({
                    "file": file_info,
                    "snippet": snippet,
                    "match_count": content_lower.count(query_lower)
                })
        
        # Sort by match count
        results.sort(key=lambda x: x["match_count"], reverse=True)
        
        return results
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from MD file content"""
        metadata = {}
        
        # Look for YAML front matter
        if content.startswith("---"):
            try:
                end_idx = content.find("---", 3)
                if end_idx > 0:
                    import yaml
                    front_matter = content[3:end_idx]
                    metadata = yaml.safe_load(front_matter) or {}
            except:
                pass
        
        # Look for metadata comments
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith("<!-- ") and ":" in line:
                try:
                    key_value = line[5:-4].strip()  # Remove <!-- and -->
                    key, value = key_value.split(":", 1)
                    metadata[key.strip()] = value.strip()
                except:
                    pass
        
        return metadata
    
    def _embed_metadata(self, content: str, metadata: Dict[str, Any]) -> str:
        """Embed metadata in MD file content"""
        # Add as YAML front matter
        import yaml
        front_matter = yaml.dump(metadata, default_flow_style=False)
        
        # Check if content already has front matter
        if content.startswith("---"):
            # Replace existing
            end_idx = content.find("---", 3)
            if end_idx > 0:
                content = content[end_idx + 3:].lstrip()
        
        return f"---\n{front_matter}---\n\n{content}"
    
    async def get_category_stats(self, auth_level: int = 0) -> Dict[str, Any]:
        """Get statistics about MD files by category"""
        stats = {}
        
        for category, level in self.security_levels.items():
            if auth_level >= level:
                files = self.category_index.get(category, [])
                total_size = sum(f["size"] for f in files)
                
                stats[category] = {
                    "count": len(files),
                    "total_size": total_size,
                    "average_size": total_size / len(files) if files else 0,
                    "security_level": level
                }
        
        return stats
    
    async def export_category(
        self,
        category: str,
        auth_level: int = 0,
        format: str = "json"
    ) -> Tuple[bool, Any]:
        """
        Export all files in a category
        
        Args:
            category: Category to export
            auth_level: Authentication level
            format: Export format (json, zip, tar)
            
        Returns:
            (success, exported data or path)
        """
        # Check permissions
        required_level = self.security_levels.get(category, 0)
        if auth_level < required_level:
            return False, "Insufficient permissions"
        
        files = self.category_index.get(category, [])
        
        if format == "json":
            # Export as JSON
            export_data = []
            for file_info in files:
                success, md_file = await self.read_file(file_info["path"], auth_level)
                if success and md_file:
                    export_data.append(asdict(md_file))
            
            return True, export_data
        
        elif format in ["zip", "tar"]:
            # Create archive
            import tempfile
            import shutil
            
            temp_dir = tempfile.mkdtemp()
            archive_path = f"{temp_dir}/{category}_export.{format}"
            
            try:
                if format == "zip":
                    import zipfile
                    with zipfile.ZipFile(archive_path, 'w') as zf:
                        for file_info in files:
                            zf.write(file_info["path"], arcname=Path(file_info["path"]).name)
                else:  # tar
                    import tarfile
                    with tarfile.open(archive_path, 'w:gz') as tf:
                        for file_info in files:
                            tf.add(file_info["path"], arcname=Path(file_info["path"]).name)
                
                return True, archive_path
                
            except Exception as e:
                logger.error(f"Failed to create archive: {e}")
                return False, str(e)
        
        else:
            return False, f"Unsupported format: {format}"
    
    async def sync_with_database(self):
        """Sync MD files with database entries"""
        # This would sync with the main memory storage system
        # Implementation would depend on the database structure
        pass
    
    def get_mcp_manifest(self) -> Dict[str, Any]:
        """Get MCP manifest for agent discovery"""
        return {
            "name": "memo-md-server",
            "version": "1.0.0",
            "description": "MCP server for accessing memory MD files",
            "capabilities": {
                "list_files": True,
                "read_file": True,
                "write_file": True,
                "search": True,
                "export": True,
                "categories": list(self.security_levels.keys())
            },
            "security": {
                "levels": self.security_levels,
                "authentication": "required"
            },
            "endpoints": {
                "list": "/mcp/files/list",
                "read": "/mcp/files/read",
                "write": "/mcp/files/write",
                "search": "/mcp/files/search",
                "stats": "/mcp/files/stats",
                "export": "/mcp/files/export"
            }
        }

# Singleton instance
_mcp_server = None

def get_mcp_server() -> MemoMDMCPServer:
    """Get singleton MCP server instance"""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MemoMDMCPServer()
    return _mcp_server