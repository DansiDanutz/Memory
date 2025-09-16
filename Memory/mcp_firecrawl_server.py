"""
MCP (Model Context Protocol) Server for Firecrawl
Provides web scraping capabilities to LLMs via MCP
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

load_dotenv()


class FirecrawlMCPServer:
    """MCP Server implementation for Firecrawl"""

    def __init__(self):
        """Initialize MCP server with Firecrawl"""
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        self.name = "firecrawl-mcp"
        self.version = "1.0.0"
        self.description = "Web scraping and content extraction via Firecrawl"

        if self.api_key and self.api_key != "your_firecrawl_api_key_here":
            self.client = FirecrawlApp(api_key=self.api_key)
            self.initialized = True
        else:
            self.client = None
            self.initialized = False

    def get_capabilities(self) -> Dict[str, Any]:
        """Return MCP server capabilities"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "functions": [
                {
                    "name": "scrape_url",
                    "description": "Scrape content from a single URL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to scrape"
                            },
                            "formats": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Output formats (markdown, html, text)",
                                "default": ["markdown"]
                            }
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "crawl_website",
                    "description": "Crawl multiple pages from a website",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Starting URL for crawl"
                            },
                            "max_pages": {
                                "type": "integer",
                                "description": "Maximum pages to crawl",
                                "default": 10
                            }
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "search_and_scrape",
                    "description": "Search web and scrape top results",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results to scrape",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "extract_structured",
                    "description": "Extract structured data using schema",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to extract from"
                            },
                            "schema": {
                                "type": "object",
                                "description": "JSON schema for extraction"
                            }
                        },
                        "required": ["url", "schema"]
                    }
                }
            ]
        }

    async def handle_function(self, function_name: str, parameters: Dict) -> Dict[str, Any]:
        """Handle MCP function calls"""

        if not self.initialized:
            return {
                "error": "Firecrawl not initialized. Please configure API key.",
                "help": "Set FIRECRAWL_API_KEY in .env file"
            }

        try:
            if function_name == "scrape_url":
                return await self._scrape_url(
                    parameters.get("url"),
                    parameters.get("formats", ["markdown"])
                )

            elif function_name == "crawl_website":
                return await self._crawl_website(
                    parameters.get("url"),
                    parameters.get("max_pages", 10)
                )

            elif function_name == "search_and_scrape":
                return await self._search_and_scrape(
                    parameters.get("query"),
                    parameters.get("num_results", 5)
                )

            elif function_name == "extract_structured":
                return await self._extract_structured(
                    parameters.get("url"),
                    parameters.get("schema")
                )

            else:
                return {"error": f"Unknown function: {function_name}"}

        except Exception as e:
            return {"error": str(e)}

    async def _scrape_url(self, url: str, formats: List[str]) -> Dict:
        """Scrape single URL"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.client.scrape_url(
                url,
                params={'formats': formats}
            )
        )

        return {
            "url": url,
            "title": result.get("metadata", {}).get("title"),
            "content": result.get("markdown", result.get("content")),
            "metadata": result.get("metadata"),
            "success": True
        }

    async def _crawl_website(self, url: str, max_pages: int) -> Dict:
        """Crawl website"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.client.crawl_url(
                url,
                params={'limit': max_pages}
            )
        )

        pages = []
        for page in result:
            pages.append({
                "url": page.get("url"),
                "title": page.get("metadata", {}).get("title"),
                "content": page.get("markdown", "")[:500]  # Truncate for response
            })

        return {
            "start_url": url,
            "pages_crawled": len(pages),
            "pages": pages,
            "success": True
        }

    async def _search_and_scrape(self, query: str, num_results: int) -> Dict:
        """Search and scrape results"""
        loop = asyncio.get_event_loop()
        search_results = await loop.run_in_executor(
            None,
            lambda: self.client.search(query, params={'limit': num_results})
        )

        scraped_results = []
        for result in search_results:
            scraped = await self._scrape_url(result.get("url"), ["markdown"])
            scraped["search_ranking"] = len(scraped_results) + 1
            scraped_results.append(scraped)

        return {
            "query": query,
            "num_results": len(scraped_results),
            "results": scraped_results,
            "success": True
        }

    async def _extract_structured(self, url: str, schema: Dict) -> Dict:
        """Extract structured data"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.client.scrape_url(
                url,
                params={
                    'extract': {
                        'schema': schema
                    }
                }
            )
        )

        return {
            "url": url,
            "extracted": result.get("extract"),
            "success": True
        }


class MCPConfig:
    """MCP Configuration for Memory Bot"""

    @staticmethod
    def generate_config() -> Dict:
        """Generate MCP configuration file"""
        return {
            "mcpServers": {
                "firecrawl": {
                    "command": "python",
                    "args": ["mcp_firecrawl_server.py"],
                    "env": {
                        "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", "")
                    },
                    "description": "Web scraping and content extraction"
                }
            },
            "settings": {
                "enabled": True,
                "auto_start": True,
                "log_level": "info"
            }
        }

    @staticmethod
    def save_config(path: str = "mcp_config.json"):
        """Save MCP configuration to file"""
        config = MCPConfig.generate_config()
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"[OK] MCP configuration saved to {path}")


async def test_server():
    """Test MCP server functionality"""
    print("=" * 60)
    print("TESTING MCP FIRECRAWL SERVER")
    print("=" * 60)

    server = FirecrawlMCPServer()

    # Show capabilities
    print("\nServer Capabilities:")
    print("-" * 40)
    capabilities = server.get_capabilities()
    print(f"Name: {capabilities['name']}")
    print(f"Version: {capabilities['version']}")
    print(f"Functions: {len(capabilities['functions'])} available")
    for func in capabilities['functions']:
        print(f"  - {func['name']}: {func['description']}")

    # Test if configured
    if server.initialized:
        print("\n[OK] Server initialized with API key")

        # Test scraping
        print("\nTesting scrape_url function...")
        result = await server.handle_function(
            "scrape_url",
            {"url": "https://example.com", "formats": ["markdown"]}
        )
        print(f"Result: {json.dumps(result, indent=2)[:200]}...")
    else:
        print("\n[WARNING] Server not initialized - API key needed")
        print("To configure:")
        print("1. Get API key from https://www.firecrawl.dev/")
        print("2. Add to .env: FIRECRAWL_API_KEY=your_key")

    # Save configuration
    print("\nSaving MCP configuration...")
    MCPConfig.save_config("mcp_config.json")


if __name__ == "__main__":
    asyncio.run(test_server())