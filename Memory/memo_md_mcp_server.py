"""
Memo MD Files MCP Server
========================
Gives ElevenLabs Memo agent access to all MD files
This allows Memo to understand everything about the project and user's knowledge
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
from dataclasses import dataclass
import glob
import re
from dotenv import load_dotenv

load_dotenv()


@dataclass
class MDFileIndex:
    """Index of all MD files for quick access"""
    path: str
    title: str
    category: str
    last_modified: datetime
    size: int
    summary: str
    tags: List[str]


class MemoMDFilesMCPServer:
    """
    MCP Server that gives Memo agent access to ALL MD files
    This is the KEY to making Memo understand everything
    """

    def __init__(self, base_paths: List[str] = None):
        """
        Initialize with paths to scan for MD files

        Args:
            base_paths: List of directories to scan for MD files
        """
        self.base_paths = base_paths or [
            "C:\\Users\\dansi\\Desktop\\Memory\\Memory",  # Your Memory Bot directory
            "C:\\Users\\dansi\\Documents",  # User documents
            "C:\\Users\\dansi\\Desktop",  # Desktop files
        ]

        self.md_files_index: Dict[str, MDFileIndex] = {}
        self.api_key = os.getenv("ELEVENLABS_API_KEY")

        # Index all MD files on startup
        self.index_all_md_files()

        print(f"[OK] Memo MCP Server initialized")
        print(f"[INFO] Found {len(self.md_files_index)} MD files")
        print(f"[IMPORTANT] Memo can now access all documentation!")

    def index_all_md_files(self):
        """
        Index all MD files in the specified paths
        This gives Memo complete knowledge of the system
        """
        for base_path in self.base_paths:
            if not os.path.exists(base_path):
                continue

            # Find all MD files recursively
            pattern = os.path.join(base_path, "**", "*.md")
            md_files = glob.glob(pattern, recursive=True)

            for file_path in md_files:
                try:
                    # Get file info
                    stat = os.stat(file_path)

                    # Read first 500 chars for summary
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        summary = content[:500].replace('\n', ' ')

                    # Extract title from content or filename
                    title = self._extract_title(content, file_path)

                    # Categorize based on path and content
                    category = self._categorize_md_file(file_path, content)

                    # Extract tags from content
                    tags = self._extract_tags(content)

                    # Create index entry
                    self.md_files_index[file_path] = MDFileIndex(
                        path=file_path,
                        title=title,
                        category=category,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        size=stat.st_size,
                        summary=summary,
                        tags=tags
                    )

                except Exception as e:
                    print(f"[WARNING] Could not index {file_path}: {e}")

        print(f"[INDEX] Categories found: {self._get_categories_summary()}")

    def _extract_title(self, content: str, file_path: str) -> str:
        """Extract title from MD content or use filename"""
        # Look for # Title at the beginning
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1)

        # Use filename without extension
        return Path(file_path).stem.replace('_', ' ').title()

    def _categorize_md_file(self, file_path: str, content: str) -> str:
        """Categorize MD file based on path and content"""
        path_lower = file_path.lower()
        content_lower = content.lower()

        # Check for specific categories
        if 'voice' in path_lower or 'elevenlabs' in path_lower or 'tts' in content_lower:
            return "voice_system"
        elif 'gamif' in path_lower or 'invitation' in path_lower or 'reward' in content_lower:
            return "gamification"
        elif 'whatsapp' in path_lower or 'message' in content_lower:
            return "messaging"
        elif 'api' in path_lower or 'endpoint' in content_lower:
            return "api_documentation"
        elif 'database' in path_lower or 'model' in content_lower:
            return "database"
        elif 'analysis' in path_lower or 'circleback' in path_lower:
            return "analysis"
        elif 'setup' in path_lower or 'install' in path_lower or 'config' in content_lower:
            return "setup_guide"
        elif 'agent' in path_lower or 'mcp' in path_lower:
            return "agent_system"
        else:
            return "documentation"

    def _extract_tags(self, content: str) -> List[str]:
        """Extract relevant tags from content"""
        tags = []

        # Common technical terms to look for
        tech_terms = [
            'elevenlabs', 'whatsapp', 'voice', 'avatar', 'memory', 'api',
            'database', 'postgresql', 'redis', 'azure', 'claude', 'openai',
            'mcp', 'agent', 'gamification', 'invitation', 'fastapi', 'python'
        ]

        content_lower = content.lower()
        for term in tech_terms:
            if term in content_lower:
                tags.append(term)

        return tags[:10]  # Limit to 10 tags

    def _get_categories_summary(self) -> Dict[str, int]:
        """Get summary of categories"""
        categories = {}
        for file_info in self.md_files_index.values():
            categories[file_info.category] = categories.get(file_info.category, 0) + 1
        return categories

    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Define MCP tools that Memo can use to access MD files
        These are CRITICAL for Memo to understand the system
        """
        return [
            {
                "name": "read_md_file",
                "description": "Read any MD file to understand documentation, setup, or system details",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the MD file (can be partial, will search)"
                        },
                        "search_query": {
                            "type": "string",
                            "description": "Optional search within the file"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "search_all_md_files",
                "description": "Search across ALL MD files to find information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to find in MD files"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["voice_system", "gamification", "messaging", "api_documentation",
                                    "database", "analysis", "setup_guide", "agent_system", "documentation"],
                            "description": "Optional category filter"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 5,
                            "description": "Max number of results"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "list_md_files",
                "description": "List all available MD files by category",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category"
                        },
                        "recent": {
                            "type": "boolean",
                            "description": "Sort by most recent"
                        }
                    }
                }
            },
            {
                "name": "get_system_overview",
                "description": "Get complete overview of the Memory Bot system from MD files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "include_technical": {
                            "type": "boolean",
                            "default": true,
                            "description": "Include technical implementation details"
                        }
                    }
                }
            },
            {
                "name": "find_implementation_details",
                "description": "Find specific implementation details from code and documentation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "feature": {
                            "type": "string",
                            "description": "Feature to find implementation for"
                        },
                        "include_code": {
                            "type": "boolean",
                            "default": true,
                            "description": "Include code snippets"
                        }
                    },
                    "required": ["feature"]
                }
            },
            {
                "name": "update_md_file",
                "description": "Update or append to an MD file with new information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to MD file to update"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to add or update"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["append", "replace", "insert"],
                            "default": "append",
                            "description": "How to update the file"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "create_md_documentation",
                "description": "Create new MD documentation file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Document title"
                        },
                        "content": {
                            "type": "string",
                            "description": "Document content"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category for the document"
                        },
                        "file_name": {
                            "type": "string",
                            "description": "File name (without .md extension)"
                        }
                    },
                    "required": ["title", "content", "file_name"]
                }
            }
        ]

    async def handle_tool_request(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle tool requests from Memo agent
        This is where Memo gets its knowledge!
        """
        try:
            if tool_name == "read_md_file":
                return await self._read_md_file(parameters)

            elif tool_name == "search_all_md_files":
                return await self._search_all_md_files(parameters)

            elif tool_name == "list_md_files":
                return await self._list_md_files(parameters)

            elif tool_name == "get_system_overview":
                return await self._get_system_overview(parameters)

            elif tool_name == "find_implementation_details":
                return await self._find_implementation_details(parameters)

            elif tool_name == "update_md_file":
                return await self._update_md_file(parameters)

            elif tool_name == "create_md_documentation":
                return await self._create_md_documentation(parameters)

            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _read_md_file(self, params: Dict) -> Dict:
        """Read specific MD file"""
        file_path = params["file_path"]
        search_query = params.get("search_query")

        # Find file (support partial paths)
        found_file = None
        for indexed_path in self.md_files_index.keys():
            if file_path in indexed_path or Path(indexed_path).name == file_path:
                found_file = indexed_path
                break

        if not found_file:
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        # Read file content
        try:
            with open(found_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Search within file if query provided
            if search_query:
                lines = content.split('\n')
                matching_lines = []
                for i, line in enumerate(lines):
                    if search_query.lower() in line.lower():
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 3)
                        context = '\n'.join(lines[context_start:context_end])
                        matching_lines.append({
                            "line_number": i + 1,
                            "context": context
                        })

                return {
                    "success": True,
                    "file_path": found_file,
                    "title": self.md_files_index[found_file].title,
                    "category": self.md_files_index[found_file].category,
                    "search_results": matching_lines,
                    "total_matches": len(matching_lines)
                }

            return {
                "success": True,
                "file_path": found_file,
                "title": self.md_files_index[found_file].title,
                "category": self.md_files_index[found_file].category,
                "content": content,
                "size": len(content),
                "tags": self.md_files_index[found_file].tags
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading file: {e}"
            }

    async def _search_all_md_files(self, params: Dict) -> Dict:
        """Search across all MD files"""
        query = params["query"].lower()
        category = params.get("category")
        limit = params.get("limit", 5)

        results = []

        for file_path, file_info in self.md_files_index.items():
            # Filter by category if specified
            if category and file_info.category != category:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if query in content.lower():
                    # Find specific matches
                    lines = content.split('\n')
                    matches = []
                    for i, line in enumerate(lines):
                        if query in line.lower():
                            matches.append({
                                "line": i + 1,
                                "text": line.strip()[:200]  # First 200 chars
                            })

                    results.append({
                        "file": file_path,
                        "title": file_info.title,
                        "category": file_info.category,
                        "matches": matches[:3],  # First 3 matches
                        "total_matches": len(matches)
                    })

                    if len(results) >= limit:
                        break

            except Exception as e:
                continue

        return {
            "success": True,
            "query": params["query"],
            "results_count": len(results),
            "results": results
        }

    async def _list_md_files(self, params: Dict) -> Dict:
        """List all MD files"""
        category = params.get("category")
        recent = params.get("recent", False)

        files = []
        for file_path, file_info in self.md_files_index.items():
            if category and file_info.category != category:
                continue

            files.append({
                "path": file_path,
                "title": file_info.title,
                "category": file_info.category,
                "size": file_info.size,
                "modified": file_info.last_modified.isoformat(),
                "summary": file_info.summary[:100],
                "tags": file_info.tags
            })

        # Sort by recent if requested
        if recent:
            files.sort(key=lambda x: x["modified"], reverse=True)

        return {
            "success": True,
            "total_files": len(files),
            "files": files,
            "categories": self._get_categories_summary()
        }

    async def _get_system_overview(self, params: Dict) -> Dict:
        """Get complete system overview from MD files"""
        include_technical = params.get("include_technical", True)

        overview = {
            "system_name": "Memory Bot with Gamified Voice Avatars",
            "total_documentation_files": len(self.md_files_index),
            "categories": self._get_categories_summary(),
            "key_features": [],
            "technical_stack": [],
            "implementation_status": []
        }

        # Extract key information from specific files
        key_files = [
            "CIRCLEBACK_COMPLETE_ANALYSIS.md",
            "VOICE_CLONING_SOLUTION.md",
            "gamified_voice_avatar.py",
            "setup_elevenlabs_agent.md"
        ]

        for file_name in key_files:
            for file_path, file_info in self.md_files_index.items():
                if file_name in file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(2000)  # First 2000 chars

                            # Extract features
                            if "feature" in content.lower():
                                features = re.findall(r'[-•]\s*(.+)', content)
                                overview["key_features"].extend(features[:5])

                    except:
                        continue

        if include_technical:
            overview["technical_details"] = {
                "voice_services": ["ElevenLabs", "Coqui TTS", "Fish Audio"],
                "databases": ["PostgreSQL", "Redis"],
                "apis": ["WhatsApp", "FastAPI", "WebSocket"],
                "ai_models": ["Claude", "GPT-4", "Azure Speech"]
            }

        return {
            "success": True,
            "overview": overview,
            "message": "Complete system overview compiled from MD files"
        }

    async def _find_implementation_details(self, params: Dict) -> Dict:
        """Find implementation details for a feature"""
        feature = params["feature"].lower()
        include_code = params.get("include_code", True)

        details = {
            "feature": params["feature"],
            "documentation_files": [],
            "code_files": [],
            "implementation_steps": []
        }

        # Search for feature in MD files
        for file_path, file_info in self.md_files_index.items():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if feature in content.lower():
                    details["documentation_files"].append({
                        "file": file_info.title,
                        "path": file_path,
                        "relevance": content.lower().count(feature)
                    })

                    # Extract implementation steps if present
                    if "implement" in content.lower():
                        steps = re.findall(r'\d+\.\s+(.+)', content)
                        details["implementation_steps"].extend(steps[:5])

            except:
                continue

        # Sort by relevance
        details["documentation_files"].sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "success": True,
            "feature": params["feature"],
            "details": details,
            "files_found": len(details["documentation_files"])
        }

    async def _update_md_file(self, params: Dict) -> Dict:
        """Update MD file"""
        file_path = params["file_path"]
        content = params["content"]
        mode = params.get("mode", "append")

        # Find file
        found_file = None
        for indexed_path in self.md_files_index.keys():
            if file_path in indexed_path:
                found_file = indexed_path
                break

        if not found_file:
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        try:
            if mode == "append":
                with open(found_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n\n{content}")
            elif mode == "replace":
                with open(found_file, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Re-index the file
            self.index_all_md_files()

            return {
                "success": True,
                "file_path": found_file,
                "mode": mode,
                "message": f"File updated successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating file: {e}"
            }

    async def _create_md_documentation(self, params: Dict) -> Dict:
        """Create new MD documentation"""
        title = params["title"]
        content = params["content"]
        file_name = params["file_name"]
        category = params.get("category", "documentation")

        # Ensure .md extension
        if not file_name.endswith('.md'):
            file_name += '.md'

        # Create in first base path
        file_path = os.path.join(self.base_paths[0], file_name)

        try:
            # Create MD content with proper formatting
            full_content = f"""# {title}

*Generated by Memo Agent - {datetime.now().strftime('%Y-%m-%d %H:%M')}*

---

{content}

---

*Category: {category}*
"""

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            # Re-index files
            self.index_all_md_files()

            return {
                "success": True,
                "file_path": file_path,
                "message": f"Documentation created: {title}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating file: {e}"
            }


class MemoAgentConfigurator:
    """
    Configure ElevenLabs Memo agent with MD file access
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.mcp_server = MemoMDFilesMCPServer()

        print(f"[CRITICAL] Configuring Memo agent with MD file access")
        print(f"[IMPORTANT] This gives Memo complete system knowledge!")

    async def configure_memo_with_md_access(self) -> Dict[str, Any]:
        """
        Configure Memo agent with full MD file access
        This is the KEY configuration!
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }

            # Create comprehensive prompt with MD context
            system_prompt = f"""
You are Memo, an intelligent assistant with COMPLETE access to all project documentation through MD files.

YOU HAVE ACCESS TO:
- {len(self.mcp_server.md_files_index)} MD documentation files
- Complete Memory Bot system documentation
- Voice avatar implementation details
- Gamification system specifications
- API documentation
- Database schemas
- All setup guides and configurations

YOUR CAPABILITIES:
1. READ any MD file to understand the system
2. SEARCH across all documentation
3. FIND implementation details
4. UPDATE documentation as needed
5. CREATE new documentation

AVAILABLE DOCUMENTATION CATEGORIES:
{json.dumps(self.mcp_server._get_categories_summary(), indent=2)}

KEY FILES YOU SHOULD KNOW:
- CIRCLEBACK_COMPLETE_ANALYSIS.md - Complete analysis of meeting transcription
- VOICE_CLONING_SOLUTION.md - Voice avatar implementation
- gamified_contact_slots.py - Contact slots gamification
- setup_elevenlabs_agent.md - Your own setup guide
- All API and database documentation

When users ask questions:
1. First search relevant MD files
2. Read complete documentation
3. Provide accurate answers based on actual documentation
4. Reference specific files when answering

You ARE the Memory Bot system expert because you have access to ALL documentation!
"""

            payload = {
                "agent_id": self.agent_id,
                "configuration": {
                    "name": "Memo - Memory Bot Expert",
                    "system_prompt": system_prompt,
                    "first_message": "Hello! I'm Memo, your Memory Bot assistant. I have complete access to all documentation and can help you with anything about the system. What would you like to know?",
                    "knowledge_base": {
                        "description": f"Access to {len(self.mcp_server.md_files_index)} MD files",
                        "categories": list(self.mcp_server._get_categories_summary().keys())
                    }
                },
                "mcp_configuration": {
                    "enabled": True,
                    "server_url": "http://localhost:3000/mcp",
                    "tools": self.mcp_server.get_mcp_tools(),
                    "approval_mode": "auto",  # Auto-approve MD file reads
                    "context": {
                        "total_files": len(self.mcp_server.md_files_index),
                        "base_paths": self.mcp_server.base_paths
                    }
                }
            }

            async with session.post(
                f"https://api.elevenlabs.io/v1/convai/agents/{self.agent_id}/configure",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    return {
                        "success": True,
                        "message": "Memo configured with MD file access!",
                        "capabilities": [
                            f"Read {len(self.mcp_server.md_files_index)} MD files",
                            "Search all documentation",
                            "Find implementation details",
                            "Update documentation",
                            "Answer any question about Memory Bot"
                        ]
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": error
                    }

    async def start_mcp_server_for_memo(self, port: int = 3000):
        """Start MCP server for Memo's MD file access"""
        from aiohttp import web

        app = web.Application()

        async def handle_mcp_request(request):
            """Handle MCP requests from Memo"""
            data = await request.json()

            tool_name = data.get("tool")
            parameters = data.get("parameters", {})

            # Log what Memo is accessing
            print(f"[MEMO] Using tool: {tool_name}")
            if tool_name == "read_md_file":
                print(f"[MEMO] Reading: {parameters.get('file_path')}")
            elif tool_name == "search_all_md_files":
                print(f"[MEMO] Searching for: {parameters.get('query')}")

            result = await self.mcp_server.handle_tool_request(
                tool_name,
                parameters
            )

            return web.json_response(result)

        # Routes
        app.router.add_post('/mcp', handle_mcp_request)
        app.router.add_get('/health', lambda r: web.json_response({"status": "healthy"}))

        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()

        print(f"[OK] MCP Server running for Memo at http://localhost:{port}")
        print(f"[CRITICAL] Memo now has access to ALL MD files!")
        print(f"[INFO] Memo can answer ANYTHING about Memory Bot!")

        # Keep running
        while True:
            await asyncio.sleep(3600)


# Demo
async def demo():
    """Setup Memo with MD file access"""
    print("=" * 70)
    print("MEMO AGENT - MD FILES CONFIGURATION")
    print("=" * 70)

    # Your agent ID from ElevenLabs
    AGENT_ID = "agt_xxxxxxxxxxxxx"  # Replace with your actual agent ID

    configurator = MemoAgentConfigurator(AGENT_ID)

    # Configure Memo
    print("\n1. Configuring Memo with MD file access...")
    result = await configurator.configure_memo_with_md_access()
    print(f"Result: {result}")

    # Start MCP server
    print("\n2. Starting MCP server for MD file access...")
    print("\nMemo can now:")
    print("  ✓ Read all MD documentation files")
    print("  ✓ Search across all documentation")
    print("  ✓ Find any implementation detail")
    print("  ✓ Answer questions about Memory Bot")
    print("  ✓ Update and create documentation")
    print("\nMemo IS the Memory Bot expert!")

    await configurator.start_mcp_server_for_memo()


if __name__ == "__main__":
    asyncio.run(demo())